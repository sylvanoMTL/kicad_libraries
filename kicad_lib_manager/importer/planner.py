"""Turn an ImportCandidate plus the caller's choices into an InstallPlan (Phase 4).

build_plan reads and decides; it never writes. The plan holds the final bytes of every file
to create or change, so apply_plan only has to write them.
"""

import hashlib
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

from .. import fsutil
from ..kicad_files import (
    LoadedFile,
    SymbolRef,
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
    symbol_insert_edit,
    symbol_unit,
    synth_property_text,
    unit_library_text,
)
from ..models import Issue, Severity
from ..sexpr import Edit, Node, apply_edits
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
    Rename,
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
    if len(unit) > 1:
        return refuse(_err("install.extends_unsupported", f"{sym_item.name} extends another symbol, which cannot be installed yet"))

    step("Planning names", 3)
    sym_renames: list[Rename] = []
    new_names: dict[str, str] = {}
    for ref in unit:
        checked = sanitize_name(ref.name)
        if any(i.code == "naming.empty" for i in checked.issues):
            return refuse(_err("install.invalid_name", f"The symbol name {ref.name!r} has no usable characters, so it cannot be installed"))
        new_names[ref.name] = checked.sanitized
        if checked.sanitized != ref.name:
            sym_renames.append(Rename("symbol", ref.name, checked.sanitized))
    final_symbols = tuple(new_names[ref.name] for ref in unit)
    if len({name.casefold() for name in final_symbols}) != len(final_symbols):
        return refuse(_err("install.duplicate_name", f"Two symbols of {sym_item.name} would both be installed under one name: {_name_list(list(final_symbols))}"))

    # D-14: a caller footprint name is sanitised like a vendor name and drives every place the name appears
    fp_names_list: list[str] = []
    fp_renames: list[Rename] = []
    for fp_item in fp_items:
        wanted = options.footprint_names.get(fp_item.name)
        checked = fp_item.name_check if wanted is None else sanitize_name(wanted)
        if any(i.code == "naming.empty" for i in checked.issues):
            shown = fp_item.name if wanted is None else wanted
            return refuse(_err("install.invalid_name", f"The footprint name {shown!r} has no usable characters; enter another name"))
        if wanted is not None:
            issues.extend(i for i in checked.issues if i.severity is not Severity.ERROR)
        fp_names_list.append(checked.sanitized)
        if checked.sanitized != fp_item.name:
            fp_renames.append(Rename("footprint", fp_item.name, checked.sanitized))
    fp_names = tuple(fp_names_list)
    if len({name.casefold() for name in fp_names}) != len(fp_names):
        return refuse(_err("install.duplicate_name", f"Two chosen footprints would both be installed under one name: {_name_list(list(fp_names))}"))

    # D-01: the vendor text is normalised once, on the unrenamed unit, so later edits never re-run kicad-cli
    unit_text = unit_library_text(vendor_sym, keep={ref.name for ref in unit})
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
        # D-17: the first footprint is linked; D-15: every installed footprint is a filter
        footprint=f"{library}:{fp_names[0]}",
        filters=" ".join(fp_names),
        manufacturer=manufacturer,
        manufacturer_forced=options.manufacturer is not None,
    )
    chosen_fields = replace(
        base_fields, mpn=options.mpn, value=options.value, datasheet=options.datasheet, description=options.description
    )
    all_edits: list[Edit] = []
    final_mpn = ""
    for ref in work_unit:
        is_chosen = ref is work_unit[-1]
        symbol_edits, mpn = _edit_symbol(work, ref, new_names[ref.name], chosen_fields if is_chosen else base_fields, style)
        all_edits.extend(symbol_edits)
        all_edits.extend(rename_symbol_edits(work.root, ref.name, new_names[ref.name]))
        if is_chosen:
            final_mpn = mpn

    model_file: str | None = None
    if model_item is not None:
        suffix = PurePosixPath(model_item.filename).suffix
        named = sanitize_filename((final_mpn or sym_item.name) + suffix)
        if any(i.code == "naming.empty" for i in named.issues):
            return refuse(_err("install.invalid_name", f"The part number {final_mpn!r} has no usable characters for a 3D model file name; enter another"))
        model_file = named.sanitized
    else:
        issues.append(Issue(Severity.WARNING, "install.no_model", "No 3D model will be installed"))

    edited = _loaded_text(apply_edits(work.source.text, all_edits), work.source.bom, "the edited symbol", "install.source_unreadable")
    if isinstance(edited, Issue):
        return refuse(edited)
    placed = {ref.name: ref for ref in find_symbols(edited.root)}
    blocks = [edited.source.text[placed[name].node.start:placed[name].node.end] for name in final_symbols]
    if target is not None:
        # The only change to an existing library is the inserted symbol: its header is never edited
        sym_text = apply_edits(target.source.text, [symbol_insert_edit(target, block) for block in blocks])
        sym_bytes = fsutil.encode_source(sym_text, target.source.bom)
    else:
        # A new library is the normalised unit file with the edited symbol
        sym_bytes = fsutil.encode_source(edited.source.text, edited.source.bom)

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
    for sym_name in final_symbols:
        if target is not None and find_symbol(target.root, sym_name) is not None:
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
    if not pretty_exists:
        ops.append(FileOp("mkdir", pretty))
    if model_item is not None and model_file is not None:
        if not layout.models_dir.is_dir():
            ops.append(FileOp("mkdir", layout.models_dir))
        ops.append(FileOp("model", layout.models_dir / model_file, source=model_item.file))
    for fp_name, data in zip(fp_names, fp_bytes):
        ops.append(FileOp("footprint", pretty / f"{fp_name}.kicad_mod", data=data))
    base = hashlib.sha256(target_bytes).hexdigest() if target is not None else None
    ops.append(FileOp("symbol_lib", sym_path, data=sym_bytes, base_sha256=base))

    return InstallPlan(
        vendor=candidate.vendor,
        source=candidate.source,
        layout=layout,
        tools=tools,
        library=library,
        new_symbol_lib=not sym_exists,
        new_footprint_lib=not pretty_exists,
        symbol_names=final_symbols,
        footprint_names=fp_names,
        linked_footprint=fp_names[0],
        model_file=model_file,
        source_version=source_version,
        target_version=target_version,
        normalised=source.normalised,
        ops=tuple(ops),
        conflicts=tuple(conflicts),
        renames=(*sym_renames, *fp_renames),
        issues=tuple(issues),
    )
