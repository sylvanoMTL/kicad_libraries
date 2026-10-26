"""Fixes from the atomic check, previewed before anything is written (the PROJECT safety rule).

A FixSpec from the scan says what to change; build_preview turns the ticked specs into the exact before
and after text of every affected file from a fresh read, and apply_preview writes exactly those texts,
each file backed up first and replaced atomically. A file that changed after its preview was built is
never overwritten. Nothing here commits and nothing outside Custom/ is ever written.
"""

import difflib
import hashlib
import os
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

from . import fsutil, kicad_files
from . import kicad_process
from .atomic_check import CUSTOM_MODEL_PREFIX, FILL_KINDS, SAFE_FIX_KINDS, datasheet_problem, effective_mpn
from .importer import fieldrules
from .importer import package as _intake
from .importer.package import MAX_KICAD_TEXT_BYTES, MAX_KICAD_TEXT_NODES, open_model_source
from .models import FixSpec, Issue, Severity
from .sexpr import Edit, SexprError, apply_edits, parse

_CUSTOM = "Custom"
_FOOTPRINT_DIR = "Custom/Footprints"
_MODEL_DIR = "Custom/3DModels"
_MIB = 1024 * 1024
_ONE_MODEL = "pick a file or a zip holding exactly one 3D model"
_MODEL_SUFFIXES = (".step", ".stp", ".wrl")
_UNSAFE_NAME_RE = re.compile(r'[\x00-\x1f<>:"/\\|?*]')
_RESERVED_NAMES = frozenset({"con", "prn", "aux", "nul", *(f"com{n}" for n in range(1, 10)), *(f"lpt{n}" for n in range(1, 10))})
_HASH_CHUNK = 65536
_GROUP_NAMES = {"mpn": fieldrules.MPN_FIELDS, "manufacturer": fieldrules.MANUFACTURER_FIELDS}


@dataclass
class FileChange:
    """One file a fix batch changes or adds.

    old_text is None and new_bytes is set for a copied 3D model; base_sha256 is the SHA-256 of the file's
    bytes at preview time (None for a new file). bom says whether new_text is written with a UTF-8 BOM.
    """

    path: Path
    rel_path: str
    old_text: str | None
    new_text: str | None
    new_bytes: bytes | None
    base_sha256: str | None
    bom: bool
    specs: list[FixSpec] = field(default_factory=list)


@dataclass
class FixPreview:
    repo_root: Path
    changes: list[FileChange] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    kicad_running: list[str] = field(default_factory=list)


@dataclass
class ApplyResult:
    ok: bool
    issues: list[Issue] = field(default_factory=list)
    backup_dir: Path | None = None


def _err(code: str, text: str) -> Issue:
    return Issue(Severity.ERROR, code, text)


def _info(code: str, text: str) -> Issue:
    return Issue(Severity.INFO, code, text)


def _size_text(limit: int) -> str:
    return f"{limit // _MIB} MiB" if limit >= _MIB and limit % _MIB == 0 else f"{limit} bytes"


def _spec_key(spec: FixSpec) -> tuple:
    """Two specs with this key in common are the same fix; the label is only for display."""
    return (spec.kind, spec.rel_path, spec.symbol, tuple(sorted(spec.params.items())))


def _inside(repo_root: Path, rel_path: str, area: str) -> Path | None:
    """Return the resolved path of rel_path when it lies strictly inside repo_root/area, else None.

    An absolute path, a drive, a ".." segment and a link that leads out of the area are all refused.
    """
    if not rel_path:
        return None
    posix, windows = PurePosixPath(rel_path), PureWindowsPath(rel_path)
    if posix.is_absolute() or windows.is_absolute() or windows.drive or windows.root:
        return None
    if ".." in posix.parts or ".." in windows.parts:
        return None
    try:
        base = (repo_root / area).resolve()
        target = (repo_root / rel_path).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    if target == base or not target.is_relative_to(base):
        return None
    return target


def _outside(rel_path: str) -> Issue:
    return _err("atomic.path_outside_custom", f"Not changed: {rel_path} is outside Custom/")


def _read_capped(path: Path, rel_path: str) -> bytes | Issue:
    """Read a KiCad file whole, refusing one above MAX_KICAD_TEXT_BYTES; read at call time so a test can patch it."""
    limit = MAX_KICAD_TEXT_BYTES
    too_large = _err("atomic.file_too_large", f"Not changed: {rel_path} is larger than {_size_text(limit)}")
    try:
        if path.stat().st_size > limit:
            return too_large
        with open(path, "rb") as handle:
            data = handle.read(limit + 1)
    except OSError as e:
        return _err("atomic.file_unreadable", f"Not changed: {rel_path} could not be read ({e.strerror or e})")
    return too_large if len(data) > limit else data


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(_HASH_CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


class _Notes:
    """Collects the INFO and ERROR lines of one preview."""

    def __init__(self, issues: list[Issue]):
        self.issues = issues

    def skip(self, spec: FixSpec, why: str) -> None:
        self.issues.append(_info("atomic.fix_skipped", f'Skipped "{spec.label}" for {spec.symbol or spec.rel_path}: {why}'))

    def unknown(self, spec: FixSpec, why: str) -> None:
        self.issues.append(_err("atomic.fix_unknown", f'Not changed: "{spec.label}" {why}'))

    def incomplete(self, spec: FixSpec, why: str) -> None:
        self.issues.append(_err("atomic.fix_incomplete", f'Not changed: "{spec.label}" {why}'))


def _insert_property(text: str, loaded: kicad_files.LoadedFile, ref: kicad_files.SymbolRef, name: str, value: str, extra_ids: dict[str, int]) -> Edit:
    """Return the edit that adds a hidden property after the symbol's last one; ids stay unique within one batch."""
    base = kicad_files.next_property_id(ref.node)
    bump = extra_ids.get(ref.name, 0)
    extra_ids[ref.name] = bump + 1
    next_id = None if base is None else base + bump
    version = kicad_files.file_version(loaded.root)
    template = kicad_files.hidden_template(ref.node)
    if template is not None:
        block = kicad_files.new_property_text(text, template, name, value, next_id, version=version)
    else:
        block = kicad_files.synth_property_text(name, value, version=version, next_id=next_id)
    return kicad_files.property_insert_edit(text, ref.node, block, loaded.source.eol)


def _set_or_insert(
    text: str, loaded: kicad_files.LoadedFile, ref: kicad_files.SymbolRef, names: Sequence[str], value: str,
    extra_ids: dict[str, int], *, insert_as: str | None = None,
) -> list[Edit] | None:
    """Set the first existing property of names, or add insert_as (default names[0]) when none exists.

    None means the property already holds value.
    """
    for name in names:
        prop = kicad_files.find_property(ref.node, name)
        if prop is not None:
            return None if prop.value == value else [kicad_files.set_property_edit(prop, value)]
    return [_insert_property(text, loaded, ref, insert_as or names[0], value, extra_ids)]


def _group_of(names: Sequence[str]) -> str:
    return "MPN" if names[0] == fieldrules.MPN_FIELDS[0] else "Manufacturer"


def _symbol_edits(
    spec: FixSpec, text: str, loaded: kicad_files.LoadedFile, ref: kicad_files.SymbolRef, extra_ids: dict[str, int], notes: _Notes
) -> list[Edit]:
    """Resolve one symbol fix into span edits against the parse of text; an empty list means nothing to do."""
    params, node = spec.params, ref.node
    kind = spec.kind
    if kind == "value_to_mpn":
        value = params.get("value", "")
        if params.get("property", "Value") != "Value":
            notes.unknown(spec, "does not name the Value field")
            return []
        mpn = effective_mpn(node)
        if mpn is None or mpn != value:
            notes.skip(spec, "its MPN changed since the check; check again")
            return []
        edits = _set_or_insert(text, loaded, ref, ("Value",), value, extra_ids)
        if edits is None:
            notes.skip(spec, "Value is already right")
            return []
        return edits
    if kind == "rename_alias":
        old, new = params.get("property", ""), params.get("new_name", "")
        group = next((names for names in _GROUP_NAMES.values() if old in names), None)
        if group is None or new != group[0] or old == new:
            notes.unknown(spec, "is not a rename of an MPN or Manufacturer alias")
            return []
        prop = kicad_files.find_property(node, old)
        if prop is None:
            notes.skip(spec, f'there is no "{old}" field any more')
            return []
        if kicad_files.find_property(node, new) is not None:
            notes.skip(spec, f'it already has a "{new}" field')
            return []
        return [kicad_files.rename_property_edit(prop, new)]
    if kind == "canonical_manufacturer":
        name, value = params.get("property", ""), params.get("value", "").strip()
        if name not in fieldrules.MANUFACTURER_FIELDS or not value:
            notes.unknown(spec, "does not name a Manufacturer field and its table spelling")
            return []
        prop = kicad_files.find_property(node, name)
        if prop is None:
            notes.skip(spec, f'there is no "{name}" field any more')
            return []
        if prop.value == value:
            notes.skip(spec, "the manufacturer is already written that way")
            return []
        return [kicad_files.set_property_edit(prop, value)]
    if kind == "merge_alias":
        names = _GROUP_NAMES.get(params.get("group", ""))
        if names is None:
            notes.unknown(spec, "does not name the MPN or Manufacturer fields")
            return []
        value = params.get("value", "").strip()
        if not value:
            notes.incomplete(spec, "needs the value to keep first")
            return []
        members = [p for p in kicad_files.list_properties(node) if p.name in names]
        keep = next((p for p in members if p.name == params.get("keep")), None)
        if keep is None:
            notes.skip(spec, "the field to keep is gone")
            return []
        # The kept field takes the canonical name, otherwise a kept alias such as MF fails the rule again
        edits = []
        if keep.name != names[0]:
            edits.append(kicad_files.rename_property_edit(keep, names[0]))
        if keep.value != value:
            edits.append(kicad_files.set_property_edit(keep, value))
        edits.extend(kicad_files.remove_property_edit(text, p) for p in members if p.node is not keep.node)
        if not edits:
            notes.skip(spec, f"there is already one {_group_of(names)} field with that value")
        return edits
    if kind == "remove_leftover":
        name = params.get("property", "")
        if not fieldrules.is_volatile(name) or fieldrules.is_protected(name):
            notes.unknown(spec, "is not a leftover price or stock field")
            return []
        prop = kicad_files.find_property(node, name)
        if prop is None:
            notes.skip(spec, f'there is no "{name}" field any more')
            return []
        return [kicad_files.remove_property_edit(text, prop)]
    if kind == "fill_datasheet":
        value = params.get("value", "").strip()
        if not value:
            notes.incomplete(spec, "needs a datasheet link or file path first")
            return []
        problem = datasheet_problem(value)
        if problem is not None:
            notes.incomplete(spec, f"cannot be used: {problem}")
            return []
        edits = _set_or_insert(text, loaded, ref, ("Datasheet",), value, extra_ids)
        if edits is None:
            notes.skip(spec, "the datasheet is already that")
            return []
        return edits
    if kind == "fill_description":
        value = fieldrules.clean_description(params.get("value", ""))
        if not value:
            notes.incomplete(spec, "needs a description first")
            return []
        wanted = params.get("property", "")
        names = tuple(dict.fromkeys(n for n in (wanted, *fieldrules.DESCRIPTION_FIELDS) if n in fieldrules.DESCRIPTION_FIELDS))
        # An existing Description or ki_description is set; a new one is named by the file's own format
        field_name = kicad_files.description_field_name(ref.node, kicad_files.file_version(loaded.root))
        edits = _set_or_insert(text, loaded, ref, names, value, extra_ids, insert_as=field_name)
        if edits is None:
            notes.skip(spec, "the description is already that")
            return []
        return edits
    notes.unknown(spec, "is not a fix this tool can make")
    return []


def _splice(text: str, edits: list[Edit], rel_path: str, issues: list[Issue]) -> str | None:
    """Apply edits in a fixed order; None, with an ERROR, when two of them touch the same span or the result will not load."""
    ordered = sorted(set(edits), key=lambda e: (e.start, e.end, e.text))
    try:
        new_text = apply_edits(text, ordered)
    except ValueError:
        issues.append(_err(
            "atomic.fix_conflict",
            f"Not changed: {rel_path}: two of the ticked fixes change the same field; untick one of them",
        ))
        return None
    try:
        parse(new_text, max_nodes=MAX_KICAD_TEXT_NODES)
    except SexprError as e:
        issues.append(_err("atomic.fix_broke_file", f"Not changed: {rel_path}: the fixed file would not load ({e})"))
        return None
    return new_text


@dataclass
class _Group:
    path: Path
    rel_path: str
    specs: list[FixSpec] = field(default_factory=list)


def _load(group: _Group, issues: list[Issue]) -> tuple[bytes, kicad_files.LoadedFile] | None:
    data = _read_capped(group.path, group.rel_path)
    if isinstance(data, Issue):
        issues.append(data)
        return None
    loaded = kicad_files.parse_bytes(data, group.path.name, max_nodes=MAX_KICAD_TEXT_NODES)
    if isinstance(loaded, Issue):
        issues.append(loaded)
        return None
    return data, loaded


def _file_change(group: _Group, data: bytes, loaded: kicad_files.LoadedFile, new_text: str) -> FileChange | None:
    if new_text == loaded.source.text:
        return None
    return FileChange(
        group.path, group.rel_path, loaded.source.text, new_text, None, hashlib.sha256(data).hexdigest(),
        loaded.source.bom, list(group.specs),
    )


def _symbol_file(group: _Group, issues: list[Issue]) -> FileChange | None:
    notes = _Notes(issues)
    read = _load(group, issues)
    if read is None:
        return None
    data, loaded = read
    text = loaded.source.text
    edits: list[Edit] = []
    extra_ids: dict[str, int] = {}
    for spec in group.specs:
        ref = kicad_files.find_symbol(loaded.root, spec.symbol)
        if ref is None:
            notes.skip(spec, "the symbol is not in the file any more")
            continue
        edits.extend(_symbol_edits(spec, text, loaded, ref, extra_ids, notes))
    if not edits:
        return None
    new_text = _splice(text, edits, group.rel_path, issues)
    return None if new_text is None else _file_change(group, data, loaded, new_text)


def _custom_model_names(model_dir: Path) -> frozenset[str]:
    """Exact relative names of every file under Custom/3DModels, as the disk spells them."""
    try:
        return frozenset(p.relative_to(model_dir).as_posix() for p in model_dir.rglob("*") if p.is_file())
    except OSError:
        return frozenset()


def _model_name_problem(name: str) -> str | None:
    stem, dot, _ = name.rpartition(".")
    if not name or name in (".", "..") or _UNSAFE_NAME_RE.search(name) or name != name.strip() or name.endswith("."):
        return f'"{name}" is not a usable file name'
    if not name.casefold().endswith(_MODEL_SUFFIXES) or not dot or stem.casefold() in _RESERVED_NAMES:
        return f'"{name}" is not a usable 3D model file name'
    return None


def _open_model(spec: FixSpec, repo_root: Path, issues: list[Issue]) -> tuple[str, bytes] | None:
    """Open the picked model through the importer's intake checks and return (file name, bytes), or None with ERRORs."""
    source = spec.params.get("source", "")
    if not source.strip():
        issues.append(_err("atomic.fix_incomplete", f'Not changed: "{spec.label}" needs a 3D model file first'))
        return None
    package = open_model_source(Path(source), repo_root)
    try:
        if package.refused:
            issues.extend(i for i in package.issues if i.severity is Severity.ERROR)
            return None
        issues.extend(i for i in package.issues if i.severity is not Severity.ERROR)
        if len(package.files) != 1 or package.files[0].kind != "model":
            issues.append(_err("atomic.fix_incomplete", f"Not changed: {Path(source).name}: {_ONE_MODEL}"))
            return None
        entry = package.files[0]
        name = PurePosixPath(entry.member.replace("\\", "/")).name
        problem = _model_name_problem(name)
        if problem is not None:
            issues.append(_err("atomic.model_name_invalid", f"Not changed: {problem}; rename the file and choose it again"))
            return None
        # The size cap is read from the module at call time, like the intake does
        limit = _intake.MAX_MEMBER_BYTES
        try:
            with open(entry.path, "rb") as handle:
                data = handle.read(limit + 1)
        except OSError as e:
            issues.append(_err("atomic.file_unreadable", f"Not changed: {name} could not be read ({e.strerror or e})"))
            return None
        if len(data) > limit or hashlib.sha256(data).hexdigest() != entry.sha256:
            issues.append(_err("atomic.model_changed", f"Not changed: {name} changed while it was read; choose it again"))
            return None
        return name, data
    finally:
        package.close()


def _model_target(model_dir: Path, name: str, data: bytes) -> tuple[str, bool] | Issue:
    """Return (the name to link, True when it must be copied), or an ERROR when another file holds the name.

    A file of that name (casefolded) with the same SHA-256 is reused under its on-disk spelling.
    """
    try:
        listed = os.listdir(model_dir)
    except OSError:
        listed = []
    twins = sorted((n for n in listed if n.casefold() == name.casefold()), key=lambda n: (n != name, n))
    if not twins:
        return name, True
    digest = hashlib.sha256(data).hexdigest()
    for twin in twins:
        try:
            same = (model_dir / twin).is_file() and _file_sha256(model_dir / twin) == digest
        except OSError:
            same = False
        if same:
            return twin, False
    return _err(
        "atomic.model_name_taken",
        f'A different 3D model named "{name}" is already in Custom/3DModels; rename the file and choose it again',
    )


def _footprint_file(
    group: _Group, repo_root: Path, models: dict[str, FileChange], issues: list[Issue]
) -> list[FileChange]:
    """Resolve the attach_model fixes of one footprint file; returns the model copies first, then the footprint edit."""
    notes = _Notes(issues)
    read = _load(group, issues)
    if read is None:
        return []
    data, loaded = read
    text = loaded.source.text
    named = kicad_files.footprint_name(loaded.root)
    if named is None:
        issues.append(_err("atomic.fix_unknown", f"Not changed: {group.rel_path} has no footprint in it"))
        return []
    model_dir = repo_root / _MODEL_DIR
    listed = _custom_model_names(model_dir)
    edits: list[Edit] = []
    pending: list[FileChange] = []
    for spec in group.specs:
        picked = _open_model(spec, repo_root, issues)
        if picked is None:
            continue
        name, bytes_ = picked
        target = _model_target(model_dir, name, bytes_)
        if isinstance(target, Issue):
            issues.append(target)
            continue
        link_name, copy = target
        refs = kicad_files.find_models(named.node)
        broken = next(
            (r for r in refs if not (r.path.startswith(CUSTOM_MODEL_PREFIX) and r.path[len(CUSTOM_MODEL_PREFIX):] in listed)),
            None,
        )
        if refs and broken is None:
            notes.skip(spec, "the footprint's 3D model already resolves")
            continue
        link = CUSTOM_MODEL_PREFIX + link_name
        edits.append(
            kicad_files.retarget_model(broken, link) if broken is not None
            else kicad_files.model_insert_edit(text, named.node, link, loaded.source.eol)
        )
        if copy:
            pending.append(FileChange(
                model_dir / link_name, f"{_MODEL_DIR}/{link_name}", None, None, bytes_, None, False, [spec],
            ))
    if not edits and not pending:
        return []
    new_text = _splice(text, edits, group.rel_path, issues) if edits else text
    if new_text is None:
        return []
    out: list[FileChange] = []
    for change in pending:
        key = change.rel_path.casefold()
        seen = models.get(key)
        if seen is None:
            models[key] = change
            out.append(change)
        elif seen.new_bytes != change.new_bytes:
            issues.append(_err(
                "atomic.model_name_taken",
                f'A different 3D model named "{change.path.name}" is already chosen for another footprint; rename the file and choose it again',
            ))
            return []
        else:
            seen.specs.extend(change.specs)
    footprint = _file_change(group, data, loaded, new_text)
    if footprint is not None:
        out.append(footprint)
    return out


def _sorted_specs(specs: list[FixSpec]) -> list[FixSpec]:
    return sorted(specs, key=lambda s: (s.symbol, s.kind, tuple(sorted(s.params.items()))))


def build_preview(
    repo_root: Path, specs: Sequence[FixSpec], *, running: Callable[[], list[str]] | None = None
) -> FixPreview:
    """Turn ticked fixes into the exact before and after text of each affected file, reading every file fresh.

    Nothing is written. A fix that no longer applies is skipped with an INFO line; a refused fix, such as one
    outside Custom/, comes back as an ERROR and changes nothing.
    """
    repo_root = Path(repo_root)
    issues: list[Issue] = []
    groups: dict[str, _Group] = {}
    seen: set[tuple] = set()
    for spec in specs:
        key = _spec_key(spec)
        if key in seen:
            continue
        seen.add(key)
        if spec.kind not in SAFE_FIX_KINDS and spec.kind not in FILL_KINDS:
            issues.append(_err("atomic.fix_unknown", f'Not changed: "{spec.label}" is not a fix this tool can make'))
            continue
        if spec.kind == "attach_model":
            footprint = spec.params.get("footprint", "")
            path = _inside(repo_root, footprint, _FOOTPRINT_DIR)
            if path is None or _inside(repo_root, spec.rel_path, _FOOTPRINT_DIR) != path or path.suffix != ".kicad_mod":
                issues.append(_outside(footprint or spec.rel_path))
                continue
            rel_path = footprint
        else:
            path = _inside(repo_root, spec.rel_path, _CUSTOM)
            if path is None or path.suffix != ".kicad_sym":
                issues.append(_outside(spec.rel_path))
                continue
            rel_path = spec.rel_path
        group = groups.setdefault(os.path.normcase(str(path)), _Group(path, rel_path))
        group.specs.append(spec)
    models: dict[str, FileChange] = {}
    copies: list[FileChange] = []
    edited: list[FileChange] = []
    for group in sorted(groups.values(), key=lambda g: g.rel_path):
        group.specs = _sorted_specs(group.specs)
        if group.path.suffix == ".kicad_mod":
            for change in _footprint_file(group, repo_root, models, issues):
                (copies if change.new_bytes is not None else edited).append(change)
        else:
            change = _symbol_file(group, issues)
            if change is not None:
                edited.append(change)
    return FixPreview(repo_root, copies + edited, issues, (running or kicad_process.kicad_running)())


def preview_text(change: FileChange) -> str:
    """Return the change as a short before and after listing with one line of context."""
    if change.new_bytes is not None or change.old_text is None or change.new_text is None:
        return f"New file {change.rel_path} ({len(change.new_bytes or b'')} bytes)"
    lines = difflib.unified_diff(
        change.old_text.splitlines(), (change.new_text or "").splitlines(),
        fromfile=f"before: {change.rel_path}", tofile=f"after: {change.rel_path}", n=1, lineterm="",
    )
    return "\n".join(lines)


def default_fix_backup_dir(root: Path | None = None, *, now: datetime | None = None) -> Path:
    """Return a new backup folder for one fix batch, under atomic_fixes so the table Restore dialog never lists it."""
    base = (fsutil.default_backup_dir() if root is None else Path(root)) / "atomic_fixes"
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    folder = base / stamp
    number = 2
    while folder.exists():
        folder = base / f"{stamp}-{number}"
        number += 1
    return folder


def _stale(change: FileChange) -> Issue:
    return _err("atomic.stale_file", f"{change.rel_path} changed after the preview was built; preview again")


def _name_appeared(change: FileChange) -> bool:
    try:
        return any(n.casefold() == change.path.name.casefold() for n in os.listdir(change.path.parent))
    except OSError:
        return False


def _write(change: FileChange) -> Issue | None:
    """Write one change; an exception becomes an Issue like a failed write does."""
    try:
        if change.new_bytes is not None:
            change.path.parent.mkdir(parents=True, exist_ok=True)
            return fsutil.atomic_write_bytes(change.path, change.new_bytes)
        return fsutil.atomic_write_text(change.path, change.new_text or "", bom=change.bom)
    except Exception as e:
        return _err("atomic.write_failed", f"Could not write {change.path.name}: {type(e).__name__}: {e}")


def _roll_back(written: list[FileChange], originals: dict[Path, bytes], backup_dir: Path) -> list[Issue]:
    """Undo the writes in reverse order, going on past a step that fails."""
    leftovers: list[Issue] = []
    for change in reversed(written):
        try:
            if change.new_bytes is not None:
                change.path.unlink(missing_ok=True)
                continue
            problem = fsutil.atomic_write_bytes(change.path, originals[change.path])
        except Exception as e:
            problem = _err("atomic.write_failed", f"{type(e).__name__}: {e}")
        if problem is not None:
            leftovers.append(_err(
                "atomic.rollback_failed",
                f"{change.rel_path} could not be restored; the original is in {backup_dir}",
            ))
    return leftovers


def apply_preview(preview: FixPreview, *, backup_root: Path | None = None) -> ApplyResult:
    """Write exactly the previewed texts, each existing file backed up first and replaced atomically.

    The whole batch is refused, writing nothing, when any file differs from what the preview read or a new
    model name has appeared. A failed write restores every file already written and removes any copied model.
    """
    if not preview.changes:
        return ApplyResult(False, [_info("atomic.nothing_to_apply", "There is nothing to apply")])
    originals: dict[Path, bytes] = {}
    for change in preview.changes:
        if _inside(preview.repo_root, change.rel_path, _CUSTOM) is None:
            return ApplyResult(False, [_outside(change.rel_path)])
        if change.base_sha256 is None:
            if _name_appeared(change):
                return ApplyResult(False, [_stale(change)])
            continue
        try:
            data = change.path.read_bytes()
        except OSError:
            return ApplyResult(False, [_stale(change)])
        if hashlib.sha256(data).hexdigest() != change.base_sha256:
            return ApplyResult(False, [_stale(change)])
        originals[change.path] = data
    backup_dir = default_fix_backup_dir(backup_root)
    for change in preview.changes:
        if change.path in originals:
            made = fsutil.backup_file(change.path, backup_dir)
            if isinstance(made, Issue):
                return ApplyResult(False, [made], backup_dir)
    written: list[FileChange] = []
    for change in preview.changes:
        problem = _write(change)
        if problem is not None:
            issues = [_err("atomic.write_failed", f"{problem.text}; no fix was kept")]
            issues.extend(_roll_back(written, originals, backup_dir))
            return ApplyResult(False, issues, backup_dir)
        written.append(change)
    done = [
        Issue(Severity.SUCCESS, "atomic.fixed", f"Added {c.rel_path}" if c.new_bytes is not None else f"Fixed {c.rel_path} (backup in {backup_dir})")
        for c in preview.changes
    ]
    return ApplyResult(True, done, backup_dir)


def complete_fill(spec: FixSpec, value: str) -> FixSpec | str:
    """Turn a fill template and the typed or picked input into a fix, or return the plain reason it cannot be used."""
    if spec.kind == "fill_datasheet":
        problem = datasheet_problem(value)
        if problem is not None:
            return problem
        stored = value.strip()
        label = f'Datasheet → "{stored}"'
    elif spec.kind == "fill_description":
        stored = fieldrules.clean_description(value)
        if not stored:
            return "Type a description first"
        label = f'Description → "{stored}"'
    elif spec.kind == "merge_alias":
        stored = value.strip()
        if not stored:
            return "Pick the value to keep first"
        group = "MPN" if spec.params.get("group") == "mpn" else "manufacturer"
        label = f'Keep "{stored}" as the only {group} value'
    elif spec.kind == "attach_model":
        if not value.strip():
            return "Choose a 3D model file first"
        stored = value
        label = f'3D model → "{PureWindowsPath(value).name}"'
    else:
        return spec
    key = "source" if spec.kind == "attach_model" else "value"
    return replace(spec, label=label, params={**spec.params, key: stored})
