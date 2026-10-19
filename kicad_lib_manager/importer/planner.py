"""Turn an ImportCandidate plus the caller's choices into an InstallPlan (Phase 4).

build_plan reads and decides; it never writes. The plan holds the final bytes of every file
to create or change, so apply_plan only has to write them.
"""

import hashlib
import os
from collections.abc import Callable, Sequence
from pathlib import Path, PurePosixPath

from .. import fsutil
from ..kicad_files import (
    LoadedFile,
    PropertyRef,
    file_kind,
    file_version,
    find_models,
    find_property,
    find_symbol,
    footprint_name,
    footprint_name_edit,
    footprint_value_edits,
    model_insert_edit,
    new_property_text,
    next_property_id,
    parse_bytes,
    property_insert_edit,
    retarget_model,
    set_property_edit,
    symbol_insert_edit,
)
from ..models import Issue, Severity
from ..sexpr import Edit, Node, apply_edits, parse, quote
from . import package as _package
from .adapters.base import MANUFACTURER_FIELDS, MPN_FIELDS
from .candidate import FootprintItem, ImportCandidate, ModelItem, SymbolItem
from .layout import RepoLayout
from .naming import sanitize_filename, sanitize_name
from .package import PackageFile
from .plan import (
    MODEL_DIR_VAR,
    Conflict,
    FileOp,
    InstallOptions,
    InstallPlan,
    ToolContext,
)
from .suggest import manufacturer_choice

# Hidden vendor properties to clone when a new property has to be added (D-13)
_TEMPLATE_PROPERTIES = ("Datasheet", "Footprint", "ki_fp_filters", "ki_keywords")


def _err(code: str, text: str) -> Issue:
    return Issue(Severity.ERROR, code, text)


def _read_vendor(pf: PackageFile) -> bytes | Issue:
    """Read a staged symbol or footprint file under the text cap and check it still matches its intake hash."""
    cap = min(_package.MAX_KICAD_TEXT_BYTES, _package.MAX_MEMBER_BYTES)
    try:
        with open(pf.path, "rb") as handle:
            data = handle.read(cap + 1)
    except OSError as e:
        return _err("install.source_unreadable", f"Could not read {pf.member}: {e.strerror or e}")
    if len(data) > cap:
        return _err("install.source_unreadable", f"{pf.member} is larger than {cap} bytes, the limit for one KiCad file")
    if hashlib.sha256(data).hexdigest() != pf.sha256:
        return _err("install.source_unreadable", f"{pf.member} changed after the package was opened")
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


class _SymbolEditor:
    """Collects the span edits for one vendor symbol block, parsed from the block's own text."""

    def __init__(self, block: str, node: Node, eol: str):
        self.block = block
        self.node = node
        self.eol = eol
        self.edits: list[Edit] = []
        self._inserts: list[str] = []
        self._next_id = next_property_id(node)
        self._template: PropertyRef | None = None
        for name in _TEMPLATE_PROPERTIES:
            self._template = find_property(node, name)
            if self._template is not None:
                break

    def add(self, name: str, value: str) -> Issue | None:
        """Add a hidden property cloned from an existing one."""
        if self._template is None:
            return _err("install.no_property_template", f"The symbol has no property to copy the layout of {name} from")
        self._inserts.append(new_property_text(self.block, self._template, name, value, self._next_id))
        if self._next_id is not None:
            self._next_id += 1
        return None

    def set_or_add(self, name: str, value: str) -> Issue | None:
        found = find_property(self.node, name)
        if found is not None:
            self.edits.append(set_property_edit(found, value))
            return None
        return self.add(name, value)

    def role(self, name: str, aliases: tuple[str, ...], fallback: str) -> Issue | None:
        """Make sure property `name` exists: keep it, rename the first vendor alias in place (D-12), or add it."""
        for alias in aliases:
            found = find_property(self.node, alias)
            if found is not None and found.value:
                if alias != name:
                    self.edits.append(Edit(found.name_node.start, found.name_node.end, quote(name)))
                return None
        return self.set_or_add(name, fallback)

    def result(self) -> str:
        edits = list(self.edits)
        for block in self._inserts:
            # Zero-width inserts at one position keep their list order
            edits.append(property_insert_edit(self.block, self.node, block, self.eol))
        return apply_edits(self.block, edits)


def _listing(folder: Path) -> list[str]:
    """Exact-case names in a folder; a missing folder lists nothing."""
    try:
        return os.listdir(folder)
    except OSError:
        return []


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

    The Package that produced the candidate must stay open until apply_plan returns: the model
    copy reads its bytes from the staged file at apply time.
    """
    issues: list[Issue] = [*package_issues, *candidate.issues]

    def refuse(*problems: Issue) -> InstallPlan:
        return _refused(candidate, options, layout, tools, [*issues, *problems])

    def step(message: str, current: int) -> None:
        if progress is not None:
            progress(message, current, 5)

    library = options.library
    if sanitize_name(library).sanitized != library:
        return refuse(_err("install.bad_library_name", f"{library!r} is not a valid library name"))
    if len(candidate.symbols) != 1 or len(candidate.footprints) != 1 or len(candidate.models) > 1:
        return refuse(_err("install.unsupported_candidate", "Only one symbol, one footprint and at most one model can be installed"))
    sym_item: SymbolItem = candidate.symbols[0]
    fp_item: FootprintItem = candidate.footprints[0]
    model_item: ModelItem | None = candidate.models[0] if candidate.models else None

    step("Reading the package", 1)
    vendor_sym = _parse_vendor(sym_item.file)
    if isinstance(vendor_sym, Issue):
        return refuse(vendor_sym)
    vendor_fp = _parse_vendor(fp_item.file)
    if isinstance(vendor_fp, Issue):
        return refuse(vendor_fp)

    step("Reading the target library", 2)
    sym_path = layout.symbols_dir / f"{library}.kicad_sym"
    pretty = layout.footprints_dir / f"{library}.pretty"
    if not sym_path.is_file() or not pretty.is_dir():
        return refuse(_err("install.library_not_found", f"{library} does not exist in Custom/ as a symbol and footprint library pair"))
    try:
        target_bytes = sym_path.read_bytes()
    except OSError as e:
        return refuse(_err("install.target_unreadable", f"Could not read {sym_path.name}: {e.strerror or e}"))
    target = parse_bytes(target_bytes, sym_path.name)
    if isinstance(target, Issue):
        return refuse(target)
    if file_kind(target.root) != "kicad_symbol_lib":
        return refuse(_err("install.target_unreadable", f"{sym_path.name} is not a KiCad symbol library"))

    source_version = file_version(vendor_sym.root)
    target_version = file_version(target.root)
    if source_version is None or target_version is None or source_version != target_version:
        return refuse(_err(
            "install.version_unsupported",
            f"The symbol has format version {source_version} but {sym_path.name} has {target_version}; only equal versions can be installed yet",
        ))

    vendor_ref = find_symbol(vendor_sym.root, sym_item.name)
    if vendor_ref is None:
        return refuse(_err("install.source_unreadable", f"{sym_item.file.member} no longer holds the symbol {sym_item.name}"))
    if any(child.head == "extends" for child in vendor_ref.node.children):
        return refuse(_err("install.extends_unsupported", f"{sym_item.name} extends another symbol, which cannot be installed yet"))

    step("Planning names", 3)
    sym_name = sym_item.name_check.sanitized
    if sym_name != sym_item.name:
        return refuse(_err("install.rename_unsupported", f"The symbol name {sym_item.name!r} would be renamed to {sym_name!r}, which cannot be installed yet"))
    fp_name = fp_item.name_check.sanitized
    meta = sym_item.meta
    mpn = meta.mpn or sym_item.name
    manufacturer = meta.manufacturer
    if not manufacturer:
        choice = manufacturer_choice(meta)
        if choice.source != "placeholder":
            manufacturer = choice.token
        else:
            issues.append(Issue(Severity.WARNING, "install.manufacturer_missing", "No manufacturer was found; the Manufacturer property is empty"))
    model_file: str | None = None
    if model_item is not None:
        suffix = PurePosixPath(model_item.filename).suffix
        model_file = sanitize_filename(mpn + suffix).sanitized

    step("Editing the symbol", 4)
    eol = vendor_sym.source.eol
    block = vendor_sym.source.text[vendor_ref.node.start:vendor_ref.node.end]
    editor = _SymbolEditor(block, parse(block).children[0], eol)
    problems = [
        editor.set_or_add("Footprint", f"{library}:{fp_name}"),
        editor.set_or_add("ki_fp_filters", fp_name),
        editor.role("Manufacturer", MANUFACTURER_FIELDS, manufacturer),
        editor.role("MPN", MPN_FIELDS, mpn),
    ]
    failed = [p for p in problems if p is not None]
    if failed:
        return refuse(*failed)
    new_block = editor.result()
    sym_text = apply_edits(target.source.text, [symbol_insert_edit(target, new_block)])
    sym_bytes = fsutil.encode_source(sym_text, target.source.bom)

    fp_ref = footprint_name(vendor_fp.root)
    if fp_ref is None:
        return refuse(_err("install.source_unreadable", f"{fp_item.file.member} is not a KiCad footprint"))
    fp_edits = [footprint_name_edit(fp_ref, fp_name), *footprint_value_edits(fp_ref.node, fp_name)]
    if model_file is not None:
        model_path = f"{MODEL_DIR_VAR}/{model_file}"
        existing = find_models(fp_ref.node)
        if existing:
            fp_edits.append(retarget_model(existing[0], model_path))
        else:
            fp_edits.append(model_insert_edit(vendor_fp.source.text, fp_ref.node, model_path, vendor_fp.source.eol))
    fp_bytes = fsutil.encode_source(apply_edits(vendor_fp.source.text, fp_edits), vendor_fp.source.bom)

    step("Checking for conflicts", 5)
    conflicts: list[Conflict] = []
    if find_symbol(target.root, sym_name) is not None:
        conflicts.append(Conflict(
            key=f"symbol:{library}:{sym_name}",
            kind="symbol",
            name=sym_name,
            existing=f"{sym_path.name} already holds a symbol named {sym_name}",
        ))
    fp_file = f"{fp_name}.kicad_mod"
    if any(name.casefold() == fp_file.casefold() for name in _listing(pretty)):
        conflicts.append(Conflict(
            key=f"footprint:{library}:{fp_name.casefold()}",
            kind="footprint",
            name=fp_name,
            existing=f"{pretty.name} already holds {fp_file}",
        ))
    if model_file is not None:
        if any(name.casefold() == model_file.casefold() for name in _listing(layout.models_dir)):
            conflicts.append(Conflict(
                key=f"model:{model_file.casefold()}",
                kind="model",
                name=model_file,
                existing=f"3DModels already holds {model_file}",
            ))

    ops: list[FileOp] = []
    if model_item is not None and model_file is not None:
        if not layout.models_dir.is_dir():
            ops.append(FileOp("mkdir", layout.models_dir))
        ops.append(FileOp("model", layout.models_dir / model_file, source=model_item.file))
    ops.append(FileOp("footprint", pretty / fp_file, data=fp_bytes))
    ops.append(FileOp("symbol_lib", sym_path, data=sym_bytes, base_sha256=hashlib.sha256(target_bytes).hexdigest()))

    return InstallPlan(
        vendor=candidate.vendor,
        source=candidate.source,
        layout=layout,
        tools=tools,
        library=library,
        new_symbol_lib=False,
        new_footprint_lib=False,
        symbol_names=(sym_name,),
        footprint_names=(fp_name,),
        linked_footprint=fp_name,
        model_file=model_file,
        source_version=source_version,
        target_version=target_version,
        normalised=False,
        ops=tuple(ops),
        conflicts=tuple(conflicts),
        renames=(),
        issues=tuple(issues),
    )
