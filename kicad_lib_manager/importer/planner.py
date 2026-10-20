"""Turn an ImportCandidate plus the caller's choices into an InstallPlan (Phase 4).

build_plan reads and decides; it never writes. The plan holds the final bytes of every file
to create or change, so apply_plan only has to write them.
"""

import hashlib
import os
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

from .. import fsutil
from ..kicad_files import (
    LoadedFile,
    SymbolRef,
    block_text,
    description_field_name,
    extends_name,
    file_kind,
    file_version,
    find_models,
    find_property,
    find_symbol,
    find_symbols,
    footprint_name,
    footprint_name_edit,
    footprint_value_edits,
    hidden_template,
    model_insert_edit,
    new_property_text,
    next_property_id,
    parse_bytes,
    property_insert_edit,
    rename_property_edit,
    rename_symbol_edits,
    replace_exact_tokens,
    retarget_model,
    set_property_edit,
    symbol_insert_before_edit,
    symbol_insert_edit,
    symbol_replace_edit,
    symbol_unit,
    synth_property_text,
    unit_library_text,
)
from ..models import Issue, Severity
from ..sexpr import Edit, Node, apply_edits, parse
from . import kicad_cli
from . import package as _package
from .adapters.base import MANUFACTURER_FIELDS, MPN_FIELDS
from .candidate import FootprintItem, ImportCandidate, ModelItem, SymbolItem
from .layout import RepoLayout, list_footprint_libs, list_model_files, list_symbol_libs
from .naming import MAX_NAME_LEN, NameResult, case_clash, sanitize_filename, sanitize_name
from .package import PackageFile
from .plan import (
    MODEL_DIR_VAR,
    Conflict,
    FileOp,
    InstallOptions,
    InstallPlan,
    Rename,
    Resolution,
    ToolContext,
)
from .suggest import manufacturer_choice, placeholder_tokens

_LISTED_NAMES = 20


def _err(code: str, text: str) -> Issue:
    return Issue(Severity.ERROR, code, text)


def _name_list(names: list[str]) -> str:
    shown = ", ".join(names[:_LISTED_NAMES])
    extra = len(names) - _LISTED_NAMES
    return f"{shown}, and {extra} more" if extra > 0 else shown


def _read_vendor(pf: PackageFile) -> bytes | Issue:
    """Read a staged symbol or footprint file under the text cap and check it still matches its intake hash (WR-04)."""
    cap = min(_package.MAX_KICAD_TEXT_BYTES, _package.MAX_MEMBER_BYTES)
    try:
        with open(pf.path, "rb") as handle:
            data = handle.read(cap + 1)
    except OSError as e:
        # The staged copy is gone, usually because the Package was closed
        return _err("install.source_gone", f"{pf.member} is no longer available ({e.strerror or e}); open the package again")
    if len(data) > cap:
        return _err("install.source_unreadable", f"{pf.member} is larger than {cap} bytes, the limit for one KiCad file")
    if hashlib.sha256(data).hexdigest() != pf.sha256:
        return _err("install.source_changed", f"{pf.member} changed after the package was opened; open the package again")
    return data


def _parse_vendor(pf: PackageFile) -> LoadedFile | Issue:
    data = _read_vendor(pf)
    if isinstance(data, Issue):
        return data
    try:
        loaded = parse_bytes(data, pf.member, max_nodes=_package.MAX_KICAD_TEXT_NODES)
    except MemoryError:
        return _err("install.source_unreadable", f"Not enough memory to read {pf.member}")
    if isinstance(loaded, Issue):
        return _err("install.source_unreadable", loaded.text)
    return loaded


@dataclass(frozen=True)
class _Fields:
    """What one symbol of the incoming unit is given (D-11 to D-15)."""

    footprint: str
    filters: str
    # Used when the symbol carries no value of its own; written always when forced (the caller typed it)
    manufacturer: str
    manufacturer_forced: bool
    # Caller overrides; they apply to the chosen symbol only
    mpn: str | None = None
    value: str | None = None
    datasheet: str | None = None
    description: str | None = None


def _edit_symbol(
    work: LoadedFile, ref: SymbolRef, new_name: str, fields: _Fields, version: int | None
) -> tuple[list[Edit], str]:
    """The span edits that turn one vendor symbol into its installed form, and the MPN it ends up with.

    Every property receives at most one edit, computed from its final value. New properties are
    hidden copies of an existing hidden one in the style of `version`.
    """
    text, eol, node = work.source.text, work.source.eol, ref.node
    edits: list[Edit] = []
    inserts: list[str] = []
    template = hidden_template(node)
    next_id = next_property_id(node)

    def add(name: str, value: str) -> None:
        nonlocal next_id
        if template is not None:
            inserts.append(new_property_text(text, template, name, value, next_id, version=version))
        else:
            inserts.append(synth_property_text(name, value, version=version, next_id=next_id))
        if next_id is not None:
            next_id += 1

    def put(name: str, value: str) -> None:
        found = find_property(node, name)
        if found is None:
            add(name, value)
        elif found.value != value:
            edits.append(set_property_edit(found, value))

    def role(name: str, aliases: tuple[str, ...], override: str | None, fallback: str) -> str:
        """Make `name` exist (D-12): keep the exact property, else rename the first vendor alias in place, else add it."""
        present = [p for p in (find_property(node, alias) for alias in aliases) if p is not None]
        vendor_value = next((p.value for p in present if p.value), "")
        value = override if override is not None else (vendor_value or fallback)
        exact = find_property(node, name)
        target = exact or next((p for p in present if p.value), present[0] if present else None)
        if target is None:
            add(name, value)
            return value
        if target is not exact:
            edits.append(rename_property_edit(target, name))
        if target.value != value:
            edits.append(set_property_edit(target, value))
        return value

    def retoken(name: str) -> None:
        found = find_property(node, name)
        if found is not None:
            changed = replace_exact_tokens(found.value, ref.name, new_name)
            if changed != found.value:
                edits.append(set_property_edit(found, changed))

    put("Footprint", fields.footprint)
    put("ki_fp_filters", fields.filters)
    forced = fields.manufacturer if fields.manufacturer_forced else None
    role("Manufacturer", MANUFACTURER_FIELDS, forced, fields.manufacturer)
    mpn = role("MPN", MPN_FIELDS, fields.mpn, ref.name)
    if fields.value is not None:
        put("Value", fields.value)
    elif new_name != ref.name:
        retoken("Value")
    if new_name != ref.name:
        retoken("ki_keywords")
    if fields.datasheet is not None:
        put("Datasheet", fields.datasheet)
    if fields.description is not None:
        put(description_field_name(node, version), fields.description)
    for block in inserts:
        # Zero-width inserts at one position keep their list order
        edits.append(property_insert_edit(text, node, block, eol))
    return edits, mpn


def _unit_text(vendor: LoadedFile, unit: list[SymbolRef]) -> str:
    """The vendor file cut down to the unit and ordered parent first, whatever order the vendor wrote.

    KiCad refuses a library that places a derived symbol before its parent (spike S8), and
    kicad-cli would fail on the unit text for that reason before any later step could fix it.
    """
    text = unit_library_text(vendor, keep={ref.name for ref in unit})
    if len(unit) < 2:
        return text
    present = find_symbols(parse(text))
    wanted = [ref.name for ref in unit]
    if [ref.name for ref in present] == wanted:
        return text
    blocks = {ref.name: text[ref.node.start:ref.node.end] for ref in present}
    gap = text[present[0].node.end:present[1].node.start]
    return text[:present[0].node.start] + gap.join(blocks[name] for name in wanted) + text[present[-1].node.end:]


def _resolves_in_library(path: str) -> bool:
    """True for a model path that starts with a path variable other than the project folder (KiCad resolves it everywhere)."""
    return path.startswith("${") and not path.startswith("${KIPRJMOD}")


def _listing(folder: Path) -> list[str]:
    """Exact-case names in a folder; a missing folder lists nothing."""
    try:
        return os.listdir(folder)
    except OSError:
        return []


def detect_tools(
    kicad_fp_dir: Path | None,
    *,
    explicit_cli: Path | None = None,
    runner: Callable | None = None,
) -> ToolContext:
    """Find kicad-cli and KiCad's stock symbols folder from the footprints folder the app detected."""
    return ToolContext(
        kicad_cli=kicad_cli.locate_kicad_cli(explicit_cli, kicad_fp_dir),
        cli_runner=runner,
        kicad_symbols_dir=kicad_cli.stock_symbols_dir(kicad_fp_dir),
    )


@dataclass(frozen=True)
class _SymbolSource:
    """The file the chosen symbol's block is taken from, and the format version of that text (D-01)."""

    loaded: LoadedFile
    normalised: bool
    version: int | None


def _loaded_text(text: str, bom: bool, name: str, code: str) -> LoadedFile | Issue:
    """Parse symbol text that was derived from a vendor file or produced by kicad-cli."""
    loaded = parse_bytes(fsutil.encode_source(text, bom), name, max_nodes=_package.MAX_KICAD_TEXT_NODES)
    if isinstance(loaded, Issue):
        return _err(code, loaded.text)
    return loaded


def _broken_parent(root: Node, name: str) -> str:
    """The first symbol of name's extends chain that is missing from the file (or repeats, for a loop)."""
    seen: set[str] = set()
    current = name
    while current not in seen:
        seen.add(current)
        ref = find_symbol(root, current)
        if ref is None:
            return current
        parent = extends_name(ref.node)
        if parent is None:
            break
        current = parent
    return current


def _existing_source(
    vendor: LoadedFile,
    unit_text: str,
    name: str,
    library: str,
    target_version: int | None,
    tools: ToolContext,
) -> tuple[_SymbolSource | None, list[Issue]]:
    """Apply the D-01 table for a symbol going into an existing library.

    Returns the source of the block to splice, or None with an ERROR in the issues.
    """
    incoming = file_version(vendor.root)
    as_is = _SymbolSource(vendor, False, incoming)
    if incoming is None or target_version is None:
        unread = "the incoming symbol" if incoming is None else library
        return as_is, [Issue(
            Severity.WARNING,
            "install.version_unknown",
            f"The format version of {unread} could not be read, so {name} is merged unchanged",
        )]
    if incoming == target_version:
        return as_is, []
    if incoming > target_version:
        return None, [_err(
            "install.version_newer_than_target",
            f"{name} is format {incoming} but {library} is {target_version}; "
            f"open {library} in KiCad's Symbol Editor and save it, then import again",
        )]
    both = f"{name} is format {incoming} but {library} is {target_version}"
    if tools.kicad_cli is None:
        return as_is, [
            Issue(Severity.WARNING, "install.version_mismatch", f"{both}; kicad-cli was not found, so {name} is merged unchanged"),
            _cli_not_found(),
        ]
    result = kicad_cli.upgrade_symbol_text(
        tools.kicad_cli, unit_text, name=name, runner=tools.cli_runner, timeout=tools.cli_timeout
    )
    if isinstance(result, Issue):
        return None, [result]
    if result.version == target_version:
        loaded = _loaded_text(result.text, False, "the kicad-cli output", "install.cli_gate_failed")
        if isinstance(loaded, Issue):
            return None, [loaded]
        return _SymbolSource(loaded, True, target_version), []
    written = "an unreadable format" if result.version is None else f"format {result.version}"
    return as_is, [Issue(
        Severity.WARNING,
        "install.version_mismatch",
        f"{both}; kicad-cli would write {written}, so {name} is merged unchanged",
    )]


def _new_source(
    vendor: LoadedFile,
    unit_text: str,
    name: str,
    tools: ToolContext,
) -> tuple[_SymbolSource | None, list[Issue]]:
    """The whole new .kicad_sym of a library that does not exist yet, holding only the chosen unit (D-04).

    With kicad-cli the header is the installed KiCad's own; without it the vendor file's header is
    kept so the version and the content agree.
    """
    if tools.kicad_cli is None:
        loaded = _loaded_text(unit_text, vendor.source.bom, "the incoming symbol", "install.source_unreadable")
        if isinstance(loaded, Issue):
            return None, [loaded]
        return _SymbolSource(loaded, False, file_version(vendor.root)), [_cli_not_found()]
    result = kicad_cli.upgrade_symbol_text(
        tools.kicad_cli, unit_text, name=name, runner=tools.cli_runner, timeout=tools.cli_timeout
    )
    if isinstance(result, Issue):
        return None, [result]
    loaded = _loaded_text(result.text, False, "the kicad-cli output", "install.cli_gate_failed")
    if isinstance(loaded, Issue):
        return None, [loaded]
    return _SymbolSource(loaded, result.changed, result.version), []


def _cli_not_found() -> Issue:
    return Issue(
        Severity.INFO,
        "install.cli_not_found",
        "kicad-cli not found; the incoming symbol is merged without normalisation and the KiCad load check is skipped",
    )


def suggest_free_name(base: str, taken: Collection[str], *, suffix: str = "", casefold: bool) -> str:
    """The first free `<base>_<n><suffix>` for n = 2, 3, ..., cleaned like any other name (D-06).

    Files compare ignoring letter case (casefold=True), symbol names compare exactly. The base is
    cut, never the number, when the name would pass the length limit.
    """
    used = {name.casefold() for name in taken} if casefold else set(taken)
    candidate = ""
    for n in range(2, len(used) + 3):
        tail = f"_{n}"
        stem = base[: max(1, MAX_NAME_LEN - len(tail))] + tail
        candidate = sanitize_filename(stem + suffix).sanitized if suffix else sanitize_name(stem).sanitized
        if (candidate.casefold() if casefold else candidate) not in used:
            break
    return candidate


def _digest(path: Path) -> str | None:
    """SHA-256 of a file read in chunks; None when it cannot be read."""
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


_FOOTPRINT_SUFFIX = ".kicad_mod"
_MODEL_EXTENSIONS = (".step", ".stp", ".wrl")


def _footprint_files(pretty: Path) -> tuple[str, ...]:
    """Exact-case names of the .kicad_mod files directly in a .pretty folder."""
    return tuple(sorted(
        name for name in _listing(pretty) if name.casefold().endswith(_FOOTPRINT_SUFFIX) and (pretty / name).is_file()
    ))


@dataclass(frozen=True)
class _FileSpec:
    """One footprint or model file the install wants to put somewhere, and how to compare it with what is there."""

    kind: str  # "footprint" | "model"
    folder: Path
    where: str  # shown in the conflict text
    files: tuple[str, ...]  # exact-case file names already in folder
    default: str  # the name the plan would use; every conflict key is built from it
    file_of: Callable[[str], str]  # name -> file name
    identity_of: Callable[[str], str]  # file name -> name
    same: Callable[[str, str], bool]  # (name, sha256 of the existing file) -> planned content equals it
    make_op: Callable[[str, Path | None, str | None], FileOp]  # (name, existing file, its sha256) -> the write
    sanitise: Callable[[str], NameResult]
    suggest: Callable[[], str]


@dataclass(frozen=True)
class _Decision:
    """What happens to one file: the name it is used under, the write if any, its conflict and notes."""

    name: str
    op: FileOp | None = None
    conflict: Conflict | None = None
    issues: tuple[Issue, ...] = ()
    kept: bool = False  # skip: the existing file is used as it is


def _find_hit(spec: _FileSpec, wanted: str) -> str | None:
    """The listed file named wanted, else one that differs from it only by letter case."""
    return next((f for f in spec.files if f == wanted), None) or next(
        (f for f in spec.files if f.casefold() == wanted.casefold()), None
    )


def _rename_file(spec: _FileSpec, conflict: Conflict, resolution: Resolution) -> _Decision:
    """Carry out a rename resolution (D-06): the caller's name or the suggestion, cleaned and checked for a new clash."""
    chosen = resolution.rename_to if resolution.rename_to is not None else conflict.suggested_name
    checked = spec.sanitise(chosen)
    if any(i.code == "naming.empty" for i in checked.issues):
        return _Decision(spec.default, conflict=conflict, issues=(
            _err("install.bad_rename", f"{conflict.key}: {chosen!r} has no usable characters; enter another name"),
        ))
    notes = [i for i in checked.issues if i.severity is not Severity.ERROR] if resolution.rename_to is not None else []
    name = checked.sanitized
    wanted = spec.file_of(name)
    hit = _find_hit(spec, wanted)
    if hit is None:
        return _Decision(name, op=spec.make_op(name, None, None), conflict=conflict, issues=tuple(notes))
    digest = _digest(spec.folder / hit)
    if digest is None:
        return _Decision(name, conflict=conflict, issues=(_err("install.target_unreadable", f"Could not read {hit} in {spec.where}"),))
    if hit == wanted and spec.same(name, digest):
        # Repeating the same rename finds the earlier result already in place
        return _Decision(name, conflict=conflict, issues=tuple(notes))
    return _Decision(name, conflict=conflict, issues=(
        *notes,
        _err("install.bad_rename", f"{conflict.key}: {spec.where} already holds {hit}, so {wanted} is not free; enter another name"),
    ))


def _decide_file(spec: _FileSpec, key: str, resolution: Resolution | None) -> _Decision:
    """Settle one file against the folder: nothing to do (D-07), a plain write, or a Conflict (D-05, D-10)."""
    wanted = spec.file_of(spec.default)
    hit = _find_hit(spec, wanted)
    if hit is None:
        return _Decision(spec.default, op=spec.make_op(spec.default, None, None))
    existing = spec.folder / hit
    digest = _digest(existing)
    if digest is None:
        return _Decision(spec.default, issues=(_err("install.target_unreadable", f"Could not read {hit} in {spec.where}"),))
    if hit == wanted and spec.same(spec.default, digest):
        return _Decision(spec.default)
    text = (
        f"{spec.where} already holds {hit}, which differs from {wanted} only by letter case"
        if hit != wanted
        else f"{spec.where} already holds a different {hit}"
    )
    conflict = Conflict(key=key, kind=spec.kind, name=spec.default, existing=text, suggested_name=spec.suggest())
    if resolution is None:
        return _Decision(spec.default, conflict=conflict)
    resolved = replace(conflict, resolution=resolution)
    if resolution.action == "overwrite":
        # The write replaces the file on disk under whatever spelling it has now (Pitfall 12)
        return _Decision(spec.default, op=spec.make_op(spec.default, existing, digest), conflict=resolved)
    if resolution.action == "skip":
        return _Decision(spec.identity_of(hit), conflict=resolved, kept=True)
    return _rename_file(spec, resolved, resolution)


@dataclass(frozen=True)
class _SymState:
    """What happens to one symbol of the unit; kind is new, identical, overwrite, skip, open (unresolved) or error."""

    vendor: str
    final: str
    kind: str


def _select(
    candidate: ImportCandidate, options: InstallOptions
) -> tuple[SymbolItem | None, list[FootprintItem], ModelItem | None, list[Issue]]:
    """Apply D-17: one symbol, one or more footprints, zero or one model; the caller decides among several."""
    problems: list[Issue] = []

    symbol: SymbolItem | None = None
    if not candidate.symbols:
        problems.append(_err("install.no_symbol", "The package holds no symbol to install"))
    elif options.symbol is not None:
        symbol = next((s for s in candidate.symbols if s.name == options.symbol), None)
        if symbol is None:
            problems.append(_err("install.unknown_item", f"The package has no symbol named {options.symbol}"))
    elif len(candidate.symbols) == 1:
        symbol = candidate.symbols[0]
    else:
        names = _name_list([s.name for s in candidate.symbols])
        problems.append(_err("install.choice_required", f"The package holds several symbols; choose one of: {names}"))

    footprints: list[FootprintItem] = []
    if not candidate.footprints:
        problems.append(_err("install.no_footprint", "The package holds no footprint to install"))
    elif options.footprints:
        for wanted in dict.fromkeys(options.footprints):
            found = next((f for f in candidate.footprints if f.name == wanted), None)
            if found is None:
                problems.append(_err("install.unknown_item", f"The package has no footprint named {wanted}"))
            else:
                footprints.append(found)
    elif len(candidate.footprints) == 1:
        footprints = [candidate.footprints[0]]
    else:
        names = _name_list([f.name for f in candidate.footprints])
        problems.append(_err("install.choice_required", f"The package holds several footprints; choose from: {names}"))

    model: ModelItem | None = None
    if options.no_model:
        pass
    elif options.model is not None:
        model = next((m for m in candidate.models if m.filename == options.model), None)
        if model is None:
            problems.append(_err("install.unknown_item", f"The package has no 3D model named {options.model}"))
    elif len(candidate.models) == 1:
        model = candidate.models[0]
    elif len(candidate.models) > 1:
        names = _name_list([m.filename for m in candidate.models])
        problems.append(_err("install.choice_required", f"The package holds several 3D models; choose one of: {names}, or none"))
    return symbol, footprints, model, problems


def _refused(
    candidate: ImportCandidate,
    options: InstallOptions,
    layout: RepoLayout,
    tools: ToolContext,
    issues: list[Issue],
) -> InstallPlan:
    """A blocked plan with no operations."""
    return InstallPlan(
        vendor=candidate.vendor,
        source=candidate.source,
        layout=layout,
        tools=tools,
        library=options.library,
        new_symbol_lib=False,
        new_footprint_lib=False,
        symbol_names=(),
        footprint_names=(),
        linked_footprint=None,
        model_file=None,
        source_version=None,
        target_version=None,
        normalised=False,
        ops=(),
        conflicts=(),
        renames=(),
        issues=tuple(issues),
    )


def build_plan(
    candidate: ImportCandidate,
    options: InstallOptions,
    layout: RepoLayout,
    tools: ToolContext = ToolContext(),
    *,
    package_issues: Sequence[Issue] = (),
    progress: Callable | None = None,
) -> InstallPlan:
    """Plan installing one candidate into the library options.library; never raises for expected failures.

    Every refusal is an ERROR Issue on a blocked plan with no operations. The Package that
    produced the candidate must stay open until apply_plan returns: the vendor files are read
    here and the model is read again when the plan is applied (WR-04).
    """
    # WR-05: package and candidate Issues lead the plan's Issues, an exact duplicate appearing once
    issues: list[Issue] = list(dict.fromkeys([*package_issues, *candidate.issues]))

    def refuse(*problems: Issue) -> InstallPlan:
        return _refused(candidate, options, layout, tools, [*issues, *problems])

    def step(message: str, current: int) -> None:
        if progress is not None:
            progress(message, current, 5)

    library = options.library
    # Phase 3 D-04: a library name that still holds a placeholder token is never installed into
    tokens = placeholder_tokens(library)
    if tokens:
        return refuse(_err(
            "install.placeholder_library",
            f"Library name {library} still contains the placeholder token(s) {', '.join(tokens)}; edit it before installing",
        ))
    clean = sanitize_name(library).sanitized
    if not library or clean != library:
        hint = "enter a library name such as Type_SubCategory_Manufacturer" if not library else f"use {clean!r}"
        return refuse(_err("install.invalid_library", f"{library!r} is not a valid library name; {hint}"))
    # D-10: a name that differs from a library on disk only by letter case is a second library on Linux and the same one on Windows
    sym_libs = list_symbol_libs(layout)
    pretty_libs = list_footprint_libs(layout)
    twins = [name for name in dict.fromkeys([*sym_libs, *pretty_libs]) if name != library and name.casefold() == library.casefold()]
    if twins:
        return refuse(_err(
            "install.library_case_clash",
            f"{library} differs from the existing library {twins[0]} only by letter case; use {twins[0]} or pick another name",
        ))
    sym_item, fp_items, model_item, problems = _select(candidate, options)
    if problems or sym_item is None:
        return refuse(*problems)

    step("Reading the package", 1)
    vendor_sym = _parse_vendor(sym_item.file)
    if isinstance(vendor_sym, Issue):
        return refuse(vendor_sym)
    vendor_fps: list[LoadedFile] = []
    for fp_item in fp_items:
        loaded_fp = _parse_vendor(fp_item.file)
        if isinstance(loaded_fp, Issue):
            return refuse(loaded_fp)
        vendor_fps.append(loaded_fp)

    step("Reading the target library", 2)
    sym_path = layout.symbols_dir / f"{library}.kicad_sym"
    pretty = layout.footprints_dir / f"{library}.pretty"
    sym_exists = library in sym_libs
    pretty_exists = library in pretty_libs
    target: LoadedFile | None = None
    target_bytes = b""
    if sym_exists:
        try:
            target_bytes = sym_path.read_bytes()
        except OSError as e:
            return refuse(_err("install.target_unreadable", f"Could not read {sym_path.name}: {e.strerror or e}"))
        parsed = parse_bytes(target_bytes, sym_path.name)
        if isinstance(parsed, Issue):
            return refuse(parsed)
        if file_kind(parsed.root) != "kicad_symbol_lib":
            return refuse(_err("install.target_unreadable", f"{sym_path.name} is not a KiCad symbol library"))
        target = parsed
    if sym_exists != pretty_exists:
        # LIB-02: a library is always a symbol and footprint pair, so the missing half is created by this install
        created = f"{library}.pretty" if sym_exists else f"{library}.kicad_sym"
        issues.append(Issue(
            Severity.WARNING,
            "install.pair_completed",
            f"{created} does not exist yet and is created with this install, so {library} becomes a complete symbol and footprint pair",
        ))

    vendor_ref = find_symbol(vendor_sym.root, sym_item.name)
    if vendor_ref is None:
        return refuse(_err("install.source_unreadable", f"{sym_item.file.member} no longer holds the symbol {sym_item.name}"))
    unit = symbol_unit(vendor_sym.root, sym_item.name)
    if unit is None:
        missing = _broken_parent(vendor_sym.root, sym_item.name)
        return refuse(_err(
            "install.extends_parent_missing",
            f"{sym_item.name} extends {missing}, which {sym_item.file.member} does not hold; the parent symbol must be in the same file",
        ))

    step("Planning names", 3)
    new_names: dict[str, str] = {}
    for ref in unit:
        checked = sanitize_name(ref.name)
        if any(i.code == "naming.empty" for i in checked.issues):
            return refuse(_err("install.invalid_name", f"The symbol name {ref.name!r} has no usable characters, so it cannot be installed"))
        new_names[ref.name] = checked.sanitized
    default_symbols = tuple(new_names[ref.name] for ref in unit)
    if len({name.casefold() for name in default_symbols}) != len(default_symbols):
        return refuse(_err("install.duplicate_name", f"Two symbols of {sym_item.name} would both be installed under one name: {_name_list(list(default_symbols))}"))

    # D-14: a caller footprint name is sanitised like a vendor name and drives every place the name appears
    fp_names_list: list[str] = []
    for fp_item in fp_items:
        wanted = options.footprint_names.get(fp_item.name)
        checked = fp_item.name_check if wanted is None else sanitize_name(wanted)
        if any(i.code == "naming.empty" for i in checked.issues):
            shown = fp_item.name if wanted is None else wanted
            return refuse(_err("install.invalid_name", f"The footprint name {shown!r} has no usable characters; enter another name"))
        if wanted is not None:
            issues.extend(i for i in checked.issues if i.severity is not Severity.ERROR)
        fp_names_list.append(checked.sanitized)
    fp_names = tuple(fp_names_list)
    if len({name.casefold() for name in fp_names}) != len(fp_names):
        return refuse(_err("install.duplicate_name", f"Two chosen footprints would both be installed under one name: {_name_list(list(fp_names))}"))
    fp_refs = []
    for fp_item, vendor_fp in zip(fp_items, vendor_fps):
        fp_ref = footprint_name(vendor_fp.root)
        if fp_ref is None:
            return refuse(_err("install.source_unreadable", f"{fp_item.file.member} is not a KiCad footprint"))
        fp_refs.append(fp_ref)

    # D-01: the vendor text is normalised once, on the unrenamed unit, so later edits never re-run kicad-cli
    unit_text = _unit_text(vendor_sym, unit)
    if target is not None:
        source, version_issues = _existing_source(vendor_sym, unit_text, sym_item.name, library, file_version(target.root), tools)
    else:
        source, version_issues = _new_source(vendor_sym, unit_text, sym_item.name, tools)
    issues.extend(version_issues)
    if source is None:
        return refuse()
    source_unit = symbol_unit(source.loaded.root, sym_item.name)
    if source_unit is None:
        return refuse(_err("install.cli_gate_failed", f"kicad-cli output no longer holds the symbol {sym_item.name}"))
    source_version = file_version(vendor_sym.root)
    target_version = file_version(target.root) if target is not None else source.version

    step("Editing the symbol", 4)
    # Edits run on a text holding only the incoming unit, so nothing outside it can be touched
    cut = unit_library_text(source.loaded, keep={ref.name for ref in source_unit})
    if cut == source.loaded.source.text:
        work = source.loaded
    else:
        parsed_cut = _loaded_text(cut, source.loaded.source.bom, "the incoming symbol", "install.source_unreadable")
        if isinstance(parsed_cut, Issue):
            return refuse(parsed_cut)
        work = parsed_cut
    work_unit = symbol_unit(work.root, sym_item.name)
    if work_unit is None:
        return refuse(_err("install.source_unreadable", f"{sym_item.file.member} no longer holds the symbol {sym_item.name}"))
    # New properties follow the format of the block they join, which is the target's own format whenever the two agree
    style = source.version if source.version is not None else target_version

    meta = sym_item.meta
    manufacturer = options.manufacturer if options.manufacturer is not None else meta.manufacturer
    if not manufacturer:
        choice = manufacturer_choice(meta)
        if choice.source != "placeholder":
            manufacturer = choice.token
        else:
            issues.append(Issue(Severity.WARNING, "install.manufacturer_missing", "No manufacturer was found; the Manufacturer property is empty"))
    base_fields = _Fields(
        footprint="",
        filters="",
        manufacturer=manufacturer,
        manufacturer_forced=options.manufacturer is not None,
    )
    renders: dict[tuple, tuple[LoadedFile, dict[str, str], str] | Issue] = {}

    def render_symbols(names: dict[str, str], link: str, filters: str) -> tuple[LoadedFile, dict[str, str], str] | Issue:
        """The unit edited under the given final names and footprint link: (text, block per final name, final MPN)."""
        memo = (tuple(names.items()), link, filters)
        if memo in renders:
            return renders[memo]
        fields = replace(base_fields, footprint=link, filters=filters)
        chosen_fields = replace(
            fields, mpn=options.mpn, value=options.value, datasheet=options.datasheet, description=options.description
        )
        all_edits: list[Edit] = []
        final_mpn = ""
        for ref in work_unit:
            is_chosen = ref is work_unit[-1]
            symbol_edits, mpn = _edit_symbol(work, ref, names[ref.name], chosen_fields if is_chosen else fields, style)
            all_edits.extend(symbol_edits)
            all_edits.extend(rename_symbol_edits(work.root, ref.name, names[ref.name]))
            if is_chosen:
                final_mpn = mpn
        edited = _loaded_text(apply_edits(work.source.text, all_edits), work.source.bom, "the edited symbol", "install.source_unreadable")
        if isinstance(edited, Issue):
            renders[memo] = edited
            return edited
        placed = {ref.name: ref for ref in find_symbols(edited.root)}
        blocks = {name: edited.source.text[placed[name].node.start:placed[name].node.end] for name in names.values()}
        renders[memo] = (edited, blocks, final_mpn)
        return renders[memo]

    first = render_symbols(new_names, f"{library}:{fp_names[0]}", " ".join(fp_names))
    if isinstance(first, Issue):
        return refuse(first)
    final_mpn = first[2]

    model_file: str | None = None
    if model_item is not None:
        suffix = PurePosixPath(model_item.filename).suffix
        named = sanitize_filename((final_mpn or sym_item.name) + suffix)
        if any(i.code == "naming.empty" for i in named.issues):
            return refuse(_err("install.invalid_name", f"The part number {final_mpn!r} has no usable characters for a 3D model file name; enter another"))
        model_file = named.sanitized
    elif candidate.models and options.no_model:
        listed = _name_list([m.filename for m in candidate.models])
        issues.append(Issue(Severity.INFO, "install.model_declined", f"The 3D model {listed} is not installed because it was declined"))
    else:
        issues.append(Issue(
            Severity.WARNING,
            "install.no_model",
            f"No 3D model found in {candidate.source.name}; the footprint installs without one",
        ))

    step("Checking for conflicts", 5)
    resolutions = options.resolutions

    bad_actions: dict[str, Issue] = {}

    def resolution_for(key: str) -> Resolution | None:
        found = resolutions.get(key)
        if found is not None and found.action not in ("overwrite", "rename", "skip"):
            bad_actions[key] = _err("install.bad_resolution", f"{key}: {found.action!r} is not overwrite, rename or skip")
            return None
        return found

    # The model comes first: its name goes into the first footprint, and the footprint's bytes decide its own conflict
    model_dec: _Decision | None = None
    if model_item is not None and model_file is not None:
        model_suffix = PurePosixPath(model_file).suffix
        model_stem = model_file[: len(model_file) - len(model_suffix)]
        model_item_file = model_item.file
        model_dir = layout.models_dir
        model_files = tuple(name for name in list_model_files(layout) if "/" not in name)
        model_extensions = (*_MODEL_EXTENSIONS, *([model_suffix.casefold()] if model_suffix else []))

        def model_sanitise(wanted: str) -> NameResult:
            """A renamed model keeps a 3D model extension: the original one is added when the new name has none."""
            return sanitize_filename(wanted if wanted.casefold().endswith(model_extensions) else wanted + model_suffix)

        def make_model_op(name: str, existing: Path | None, digest: str | None) -> FileOp:
            return FileOp(
                "model",
                model_dir / name,
                source=model_item_file,
                base_sha256=digest,
                listed_path=existing if existing is not None and existing.name != name else None,
            )

        model_dec = _decide_file(
            _FileSpec(
                kind="model",
                folder=model_dir,
                where=model_dir.name,
                files=model_files,
                default=model_file,
                file_of=lambda name: name,
                identity_of=lambda name: name,
                same=lambda name, digest: digest == model_item_file.sha256,
                make_op=make_model_op,
                sanitise=model_sanitise,
                suggest=lambda: suggest_free_name(model_stem, model_files, suffix=model_suffix, casefold=True),
            ),
            f"model:{model_file.casefold()}",
            resolution_for(f"model:{model_file.casefold()}"),
        )

    model_link = model_dec.name if model_dec is not None else None
    pretty_files = _footprint_files(pretty)
    fp_taken = [name[: -len(_FOOTPRINT_SUFFIX)] for name in pretty_files]

    def render_fp(index: int, name: str) -> tuple[bytes, list[Issue]]:
        """The vendor footprint under a final name; the first footprint carries the model link."""
        fp_ref, vendor_fp = fp_refs[index], vendor_fps[index]
        notes: list[Issue] = []
        fp_edits = [footprint_name_edit(fp_ref, name), *footprint_value_edits(fp_ref.node, name)]
        existing = find_models(fp_ref.node)
        # The model belongs to the linked (first) footprint
        if model_link is not None and index == 0:
            model_path = f"{MODEL_DIR_VAR}/{model_link}"
            if existing:
                fp_edits.append(retarget_model(existing[0], model_path))
                if len(existing) > 1:
                    notes.append(Issue(
                        Severity.WARNING,
                        "install.extra_models",
                        f"{name} has {len(existing)} 3D model blocks; the first now links {model_link} and the other {len(existing) - 1} are left unchanged",
                    ))
            else:
                fp_edits.append(model_insert_edit(vendor_fp.source.text, fp_ref.node, model_path, vendor_fp.source.eol))
        else:
            # Vendor model paths are never edited; one that cannot resolve from this library is reported
            stale = next((m.path for m in existing if not _resolves_in_library(m.path)), None)
            if stale is not None:
                notes.append(Issue(
                    Severity.WARNING,
                    "install.stale_model_path",
                    f"{name} links the 3D model {stale!r}, which will not resolve from this library; the path is left unchanged",
                ))
        if fp_items[index].has_embedded_files:
            notes.append(Issue(
                Severity.WARNING,
                "install.embedded_files",
                f"{name} contains embedded files; they are kept exactly as they are",
            ))
        return fsutil.encode_source(apply_edits(vendor_fp.source.text, fp_edits), vendor_fp.source.bom), notes

    def footprint_spec(index: int) -> _FileSpec:
        default = fp_names[index]

        def make_fp_op(name: str, existing: Path | None, digest: str | None) -> FileOp:
            return FileOp(
                "footprint",
                pretty / f"{name}{_FOOTPRINT_SUFFIX}",
                data=render_fp(index, name)[0],
                base_sha256=digest,
                listed_path=existing if existing is not None and existing.name != f"{name}{_FOOTPRINT_SUFFIX}" else None,
            )

        return _FileSpec(
            kind="footprint",
            folder=pretty,
            where=pretty.name,
            files=pretty_files,
            default=default,
            file_of=lambda name: f"{name}{_FOOTPRINT_SUFFIX}",
            identity_of=lambda name: name[: -len(_FOOTPRINT_SUFFIX)],
            same=lambda name, digest: hashlib.sha256(render_fp(index, name)[0]).hexdigest() == digest,
            make_op=make_fp_op,
            sanitise=sanitize_name,
            suggest=lambda: suggest_free_name(default, [*fp_taken, *fp_names], casefold=True),
        )

    fp_decisions = [
        _decide_file(
            footprint_spec(index),
            f"footprint:{library}:{name.casefold()}",
            resolution_for(f"footprint:{library}:{name.casefold()}"),
        )
        for index, name in enumerate(fp_names)
    ]
    for decision in fp_decisions:
        issues.extend(decision.issues)
    if fp_decisions[0].kept and model_dec is not None:
        # The kept footprint does not link the incoming model, so copying it would leave a stray file (D-09)
        issues.append(Issue(
            Severity.INFO,
            "install.model_not_attached",
            f"The 3D model {model_dec.name} is not installed: the existing footprint {fp_decisions[0].name} is kept and does not link it",
        ))
        model_dec = None
    if model_dec is not None:
        issues.extend(model_dec.issues)
    final_fps = tuple(d.name for d in fp_decisions)
    if len({name.casefold() for name in final_fps}) != len(final_fps):
        issues.append(_err("install.duplicate_name", f"Two chosen footprints would both end up under one name: {_name_list(list(final_fps))}"))
    linked = final_fps[0]
    for index, decision in enumerate(fp_decisions):
        if not decision.kept:
            issues.extend(render_fp(index, decision.name)[1])

    # The symbol is judged last: its Footprint field and filters carry the footprint names that survived
    link = f"{library}:{linked}"
    filters = " ".join(final_fps)
    existing_syms = {} if target is None else {ref.name: ref for ref in find_symbols(target.root)}

    def plain(text: str) -> str:
        return fsutil.normalize_eol(text, "\n")

    # A rename changes the block other members are compared with, so the unit is judged again until no rename is left to apply
    renamed: dict[str, str] = {}
    rename_notes: dict[str, list[Issue]] = {}
    known_conflicts: dict[str, Conflict] = {}
    for _ in range(len(unit) + 1):
        names = {vendor: renamed.get(vendor, default) for vendor, default in new_names.items()}
        rendered = render_symbols(names, link, filters)
        if isinstance(rendered, Issue):
            return refuse(rendered)
        edited, blocks, _mpn = rendered
        sym_notes: list[Issue] = []
        states: list[_SymState] = []
        again = False
        for ref in unit:
            default, final = new_names[ref.name], names[ref.name]
            present = existing_syms.get(final)
            if present is None or target is None:
                states.append(_SymState(ref.name, final, "new"))
                continue
            if plain(block_text(target.source.text, present.node)) == plain(blocks[final]):
                states.append(_SymState(ref.name, final, "identical"))
                continue
            if final != default:
                sym_notes.append(_err("install.bad_rename", f"{final} cannot be used: {library} already has a different {final}; enter another name"))
                states.append(_SymState(ref.name, final, "error"))
                continue
            key = f"symbol:{library}:{default}"
            taken = [*existing_syms, *(new_names[r.name] for r in unit if r is not ref)]
            conflict = Conflict(
                key=key,
                kind="symbol",
                name=default,
                existing=f"{library} already has a different {default}",
                suggested_name=suggest_free_name(default, taken, casefold=False),
            )
            res = resolution_for(key)
            known_conflicts[default] = replace(conflict, resolution=res)
            if res is None:
                states.append(_SymState(ref.name, final, "open"))
            elif res.action == "rename":
                chosen = res.rename_to if res.rename_to is not None else conflict.suggested_name
                checked = sanitize_name(chosen)
                if any(i.code == "naming.empty" for i in checked.issues):
                    sym_notes.append(_err("install.bad_rename", f"{key}: {chosen!r} has no usable characters; enter another name"))
                    states.append(_SymState(ref.name, final, "error"))
                else:
                    renamed[ref.name] = checked.sanitized
                    rename_notes[ref.name] = (
                        [i for i in checked.issues if i.severity is not Severity.ERROR] if res.rename_to is not None else []
                    )
                    again = True
                    states.append(_SymState(ref.name, final, "error"))
            else:
                states.append(_SymState(ref.name, final, res.action))
        if not again:
            break
    issues.extend(bad_actions.values())
    for notes in rename_notes.values():
        issues.extend(notes)
    issues.extend(sym_notes)
    final_symbols = tuple(names[ref.name] for ref in unit)
    if len({name.casefold() for name in final_symbols}) != len(final_symbols):
        issues.append(_err("install.duplicate_name", f"Two symbols of {sym_item.name} would both end up under one name: {_name_list(list(final_symbols))}"))
    for state in states:
        if state.kind == "new":
            issues.extend(case_clash(state.final, existing_syms))
        elif state.kind == "skip":
            issues.append(Issue(
                Severity.WARNING,
                "install.symbol_kept",
                f"The existing {state.final} in {library} is kept; its Footprint field was not changed to {link}",
            ))

    sym_edits: list[Edit] = []
    if target is not None:
        for index, state in enumerate(states):
            if state.kind == "overwrite":
                # D-08: the new block takes the old block's place, so the library keeps its order
                sym_edits.append(symbol_replace_edit(target, existing_syms[state.final], blocks[state.final]))
            elif state.kind == "new":
                # A derived symbol must stay behind its parent: a new parent goes in front of an existing descendant
                behind = [existing_syms[s.final] for s in states[index + 1 :] if s.final in existing_syms]
                if behind:
                    sym_edits.append(symbol_insert_before_edit(target, min(behind, key=lambda r: r.node.start), blocks[state.final]))
                else:
                    sym_edits.append(symbol_insert_edit(target, blocks[state.final]))
    if target is not None:
        sym_bytes = fsutil.encode_source(apply_edits(target.source.text, sym_edits), target.source.bom)
    else:
        # A new library is the normalised unit file with the edited symbols, already in parent-first order
        sym_bytes = fsutil.encode_source(edited.source.text, edited.source.bom)

    # A conflict stays listed while it needs a decision or was settled by one; an item that matches by now has none
    conflicts = [
        known_conflicts[new_names[state.vendor]]
        for state in states
        if new_names[state.vendor] in known_conflicts
        and (state.final != new_names[state.vendor] or state.kind not in ("new", "identical"))
    ]
    conflicts.extend(d.conflict for d in fp_decisions if d.conflict is not None)
    if model_dec is not None and model_dec.conflict is not None:
        conflicts.append(model_dec.conflict)

    ops: list[FileOp] = []
    if not pretty_exists:
        ops.append(FileOp("mkdir", pretty))
    if model_dec is not None and model_dec.op is not None:
        if not layout.models_dir.is_dir():
            ops.append(FileOp("mkdir", layout.models_dir))
        ops.append(model_dec.op)
    ops.extend(d.op for d in fp_decisions if d.op is not None)
    if target is None or sym_edits:
        base = hashlib.sha256(target_bytes).hexdigest() if target is not None else None
        ops.append(FileOp("symbol_lib", sym_path, data=sym_bytes, base_sha256=base))

    sym_renames = [Rename("symbol", ref.name, names[ref.name]) for ref in unit if names[ref.name] != ref.name]
    fp_renames = [
        Rename("footprint", fp_item.name, decision.name)
        for fp_item, decision in zip(fp_items, fp_decisions)
        if decision.name != fp_item.name and not decision.kept
    ]
    model_renames = (
        [Rename("model", model_file, model_dec.name)]
        if model_dec is not None and model_file is not None and model_dec.name != model_file and not model_dec.kept
        else []
    )
    return InstallPlan(
        vendor=candidate.vendor,
        source=candidate.source,
        layout=layout,
        tools=tools,
        library=library,
        new_symbol_lib=not sym_exists,
        new_footprint_lib=not pretty_exists,
        symbol_names=final_symbols,
        footprint_names=final_fps,
        # A kept chosen symbol still has whatever Footprint field it had, so this install links nothing
        linked_footprint=None if states[-1].kind == "skip" else linked,
        model_file=model_dec.name if model_dec is not None else None,
        source_version=source_version,
        target_version=target_version,
        normalised=source.normalised,
        ops=tuple(ops),
        conflicts=tuple(conflicts),
        renames=(*sym_renames, *fp_renames, *model_renames),
        issues=tuple(issues),
    )
