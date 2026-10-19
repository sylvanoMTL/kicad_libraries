"""Turn an ImportCandidate plus the caller's choices into an InstallPlan (Phase 4).

build_plan reads and decides; it never writes. The plan holds the final bytes of every file
to create or change, so apply_plan only has to write them.
"""

import hashlib
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .. import fsutil
from ..kicad_files import (
    LoadedFile,
    PropertyRef,
    extends_name,
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
    symbol_unit,
    unit_library_text,
)
from ..models import Issue, Severity
from ..sexpr import Edit, Node, apply_edits, parse, quote
from . import kicad_cli
from . import package as _package
from .adapters.base import MANUFACTURER_FIELDS, MPN_FIELDS
from .candidate import FootprintItem, ImportCandidate, ModelItem, SymbolItem
from .layout import RepoLayout, list_footprint_libs, list_symbol_libs
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
from .suggest import manufacturer_choice, placeholder_tokens

# Hidden vendor properties to clone when a new property has to be added (D-13)
_TEMPLATE_PROPERTIES = ("Datasheet", "Footprint", "ki_fp_filters", "ki_keywords")
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


def _loaded_text(text: str, bom: bool, name: str) -> LoadedFile | Issue:
    """Parse symbol text that was derived from a vendor file or produced by kicad-cli."""
    loaded = parse_bytes(fsutil.encode_source(text, bom), name, max_nodes=_package.MAX_KICAD_TEXT_NODES)
    if isinstance(loaded, Issue):
        return _err("install.cli_gate_failed", loaded.text)
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
        loaded = _loaded_text(result.text, False, "the kicad-cli output")
        if isinstance(loaded, Issue):
            return None, [loaded]
        return _SymbolSource(loaded, True, target_version), []
    written = "an unreadable format" if result.version is None else f"format {result.version}"
    return as_is, [Issue(
        Severity.WARNING,
        "install.version_mismatch",
        f"{both}; kicad-cli would write {written}, so {name} is merged unchanged",
    )]


def _cli_not_found() -> Issue:
    return Issue(
        Severity.INFO,
        "install.cli_not_found",
        "kicad-cli not found; the incoming symbol is merged without normalisation and the KiCad load check is skipped",
    )


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
    if sanitize_name(library).sanitized != library:
        return refuse(_err("install.bad_library_name", f"{library!r} is not a valid library name"))
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
    if len(unit) > 1:
        return refuse(_err("install.extends_unsupported", f"{sym_item.name} extends another symbol, which cannot be installed yet"))

    step("Planning names", 3)
    sym_name = sym_item.name_check.sanitized
    if sym_name != sym_item.name:
        return refuse(_err("install.rename_unsupported", f"The symbol name {sym_item.name!r} would be renamed to {sym_name!r}, which cannot be installed yet"))

    # D-01: the vendor text is normalised once, on the unrenamed unit, so later edits never re-run kicad-cli
    unit_text = unit_library_text(vendor_sym, keep={ref.name for ref in unit})
    source, version_issues = _existing_source(vendor_sym, unit_text, sym_item.name, library, file_version(target.root), tools)
    issues.extend(version_issues)
    if source is None:
        return refuse()
    source_ref = find_symbol(source.loaded.root, sym_item.name)
    if source_ref is None:
        return refuse(_err("install.cli_gate_failed", f"kicad-cli output no longer holds the symbol {sym_item.name}"))
    source_version = file_version(vendor_sym.root)
    target_version = file_version(target.root)

    fp_names = tuple(item.name_check.sanitized for item in fp_items)
    if len({name.casefold() for name in fp_names}) != len(fp_names):
        return refuse(_err("install.duplicate_name", f"Two chosen footprints would both be installed under one name: {_name_list(list(fp_names))}"))
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
    else:
        issues.append(Issue(Severity.WARNING, "install.no_model", "No 3D model will be installed"))

    step("Editing the symbol", 4)
    eol = source.loaded.source.eol
    block = source.loaded.source.text[source_ref.node.start:source_ref.node.end]
    editor = _SymbolEditor(block, parse(block).children[0], eol)
    edit_problems = [
        # D-17: the first footprint is linked; D-15: every installed footprint is a filter
        editor.set_or_add("Footprint", f"{library}:{fp_names[0]}"),
        editor.set_or_add("ki_fp_filters", " ".join(fp_names)),
        editor.role("Manufacturer", MANUFACTURER_FIELDS, manufacturer),
        editor.role("MPN", MPN_FIELDS, mpn),
    ]
    failed = [p for p in edit_problems if p is not None]
    if failed:
        return refuse(*failed)
    new_block = editor.result()
    sym_text = apply_edits(target.source.text, [symbol_insert_edit(target, new_block)])
    sym_bytes = fsutil.encode_source(sym_text, target.source.bom)

    fp_bytes: list[bytes] = []
    for index, (fp_item, vendor_fp, fp_name) in enumerate(zip(fp_items, vendor_fps, fp_names)):
        fp_ref = footprint_name(vendor_fp.root)
        if fp_ref is None:
            return refuse(_err("install.source_unreadable", f"{fp_item.file.member} is not a KiCad footprint"))
        fp_edits = [footprint_name_edit(fp_ref, fp_name), *footprint_value_edits(fp_ref.node, fp_name)]
        # The model belongs to the linked (first) footprint
        if model_file is not None and index == 0:
            model_path = f"{MODEL_DIR_VAR}/{model_file}"
            existing = find_models(fp_ref.node)
            if existing:
                fp_edits.append(retarget_model(existing[0], model_path))
            else:
                fp_edits.append(model_insert_edit(vendor_fp.source.text, fp_ref.node, model_path, vendor_fp.source.eol))
        fp_bytes.append(fsutil.encode_source(apply_edits(vendor_fp.source.text, fp_edits), vendor_fp.source.bom))

    step("Checking for conflicts", 5)
    conflicts: list[Conflict] = []
    if find_symbol(target.root, sym_name) is not None:
        conflicts.append(Conflict(
            key=f"symbol:{library}:{sym_name}",
            kind="symbol",
            name=sym_name,
            existing=f"{sym_path.name} already holds a symbol named {sym_name}",
        ))
    listed = [name.casefold() for name in _listing(pretty)]
    for fp_name in fp_names:
        if f"{fp_name}.kicad_mod".casefold() in listed:
            conflicts.append(Conflict(
                key=f"footprint:{library}:{fp_name.casefold()}",
                kind="footprint",
                name=fp_name,
                existing=f"{pretty.name} already holds {fp_name}.kicad_mod",
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
    for fp_name, data in zip(fp_names, fp_bytes):
        ops.append(FileOp("footprint", pretty / f"{fp_name}.kicad_mod", data=data))
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
        footprint_names=fp_names,
        linked_footprint=fp_names[0],
        model_file=model_file,
        source_version=source_version,
        target_version=target_version,
        normalised=source.normalised,
        ops=tuple(ops),
        conflicts=tuple(conflicts),
        renames=(),
        issues=tuple(issues),
    )
