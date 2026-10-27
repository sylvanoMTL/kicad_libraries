"""Field cleanup of the incoming symbol for every vendor (Phase 7, D-05 to D-09).

Duplicate Manufacturer/MPN aliases and placeholder-valued fields are dropped, description whitespace is
collapsed, and every rename, drop and clean is a FieldChange on the plan and a "Field changes" preview
row. The tests run on synthetic packages in a synthetic Custom/ under tmp_path, with ToolContext() and no
kicad-cli, because kicad-cli 10 trims descriptions itself and would hide the rule under test.
"""

import dataclasses
from contextlib import contextmanager
from pathlib import Path

from installfixtures import ATOMIC_PROPS, UL_DESCRIPTION, vendor_footprint, vendor_symbol_lib
from vendorfixtures import (
    SNAPEDA_DESCRIPTION,
    SNAPEDA_DESCRIPTION_RAW,
    SNAPEDA_MANUFACTURER,
    SNAPEDA_MPN,
    SNAPEDA_SYMBOL,
    snapeda_zip,
)
from zipfixtures import (
    CURRENT_ATOMIC_FOOTPRINT_LIBS,
    CURRENT_ATOMIC_SYMBOL_LIBS,
    STEP_BYTES,
    footprint_library_for,
    make_zip,
    symbol_lib,
    write_custom_layout,
)

from kicad_lib_manager.importer import fieldrules, form
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.plan import FieldChange, InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.importer.preview import preview_sections
from kicad_lib_manager.kicad_files import (
    find_property,
    find_symbol,
    list_properties,
    parse_bytes,
    property_insert_edit,
    remove_property_edit,
)
from kicad_lib_manager.models import Issue, Severity
from kicad_lib_manager.sexpr import apply_edits

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPEDA_LIBRARY = "Atomic_Connector"
UL_LIBRARY = "Atomic_Battery_Management"
VENDOR = "PART"
LIBRARY = "Atomic_Analog"
# The SnapEDA sample has no Datasheet; an install of it carries one so the part passes the atomic rule (D-21)
SNAPEDA_DATASHEET = ATOMIC_PROPS["Datasheet"]


def _snapeda_layout(tmp_path):
    write_custom_layout(tmp_path / "repo", CURRENT_ATOMIC_SYMBOL_LIBS, CURRENT_ATOMIC_FOOTPRINT_LIBS)
    return RepoLayout.for_repo(tmp_path / "repo")


def _library_layout(tmp_path):
    write_custom_layout(tmp_path / "repo", [LIBRARY], [footprint_library_for(LIBRARY)])
    return RepoLayout.for_repo(tmp_path / "repo")


@contextmanager
def _open_snapeda(tmp_path):
    zip_path = snapeda_zip(tmp_path / "src" / f"{SNAPEDA_SYMBOL}.zip", with_model=True)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield package, candidate


@contextmanager
def _open_vendor(tmp_path, symbol, model="part.step"):
    """Open a one-symbol vendor zip (symbol PART, footprint FP, a STEP model); yields (package, candidate)."""
    members = [("part.kicad_sym", symbol), ("FP.kicad_mod", vendor_footprint("FP")), (model, STEP_BYTES)]
    (tmp_path / "src").mkdir(exist_ok=True)
    zip_path = make_zip(tmp_path / "src" / "pkg.zip", members)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield package, candidate


def _plan_vendor(tmp_path, props=None, **kwargs):
    layout = _library_layout(tmp_path)
    props = dict(props or {})
    # A Description makes the part pass the atomic rule (D-21); a test about a description field brings its own
    if not {"Description", "ki_description"} & set(props):
        props["Description"] = ATOMIC_PROPS["Description"]
    with _open_vendor(tmp_path, vendor_symbol_lib(VENDOR, props=props, **kwargs)) as (_, candidate):
        return build_plan(candidate, InstallOptions(library=LIBRARY), layout, ToolContext()), candidate


def _op(plan, kind):
    return next(op for op in plan.ops if op.kind == kind)


def _symbol_in(plan, name=VENDOR):
    loaded = parse_bytes(_op(plan, "symbol_lib").data, "lib")
    assert not isinstance(loaded, Issue), loaded
    symbol = find_symbol(loaded.root, name)
    assert symbol is not None
    return symbol


def _property_names(symbol):
    return [p.name for p in list_properties(symbol.node)]


def _value_of(plan, name, symbol_name=VENDOR):
    prop = find_property(_symbol_in(plan, symbol_name).node, name)
    return None if prop is None else prop.value


def _drops(plan):
    return [(c.field, c.reason) for c in plan.field_changes if c.action == "drop"]


# -- the SnapEDA part, all rules together ----------------------------------------------------------

SNAPEDA_NAMES = [
    "Reference",
    "Value",
    "Footprint",
    "Manufacturer",
    "MAXIMUM_PACKAGE_HEIGHT",
    "STANDARD",
    "PARTREV",
    "SnapEDA_Link",
    "MPN",
    "Description",
    "ki_fp_filters",
    "Datasheet",
    # The SnapEDA symbol had no keywords, so the generated ones are added after its last property (plan 10-23)
    "ki_keywords",
]
SNAPEDA_FOOTPRINT = "GCT_USBC4242-01-0099-A_REVB1"
SNAPEDA_KEYWORDS = "Connector receptacle USB-C USB GCT_USBC4242-01-0099-A_REVB1 GCT Global"


def _snapeda_changes():
    s = SNAPEDA_SYMBOL
    return [
        FieldChange(s, "set", "Value", s, SNAPEDA_MPN, "follows_mpn"),
        FieldChange(s, "rename", "MF", "", "Manufacturer", "alias"),
        FieldChange(s, "drop", "Package", "None", "", "placeholder"),
        FieldChange(s, "drop", "Price", "None", "", "volatile"),
        FieldChange(
            s, "drop", "Check_prices", "https://www.snapeda.com/parts/USBC4242-01-0099-A/prices/", "", "volatile"
        ),
        FieldChange(s, "rename", "MP", "", "MPN", "alias"),
        FieldChange(s, "clean", "Description", SNAPEDA_DESCRIPTION_RAW, SNAPEDA_DESCRIPTION, "whitespace"),
        FieldChange(s, "drop", "MANUFACTURER", "GCT", "", "duplicate"),
        FieldChange(s, "drop", "Availability", "In Stock", "", "volatile"),
        FieldChange(s, "drop", "SNAPEDA_PN", SNAPEDA_MPN, "", "duplicate"),
        # The generated text (plan 10-23): the symbol's keywords, then the footprint's description and tags
        FieldChange(s, "set", "ki_keywords", "", SNAPEDA_KEYWORDS, "generated"),
        FieldChange(
            SNAPEDA_FOOTPRINT, "set", "Footprint description", "",
            f"1.5 mm pitch, GCT {SNAPEDA_FOOTPRINT}", "generated", scope="footprint",
        ),
        FieldChange(
            SNAPEDA_FOOTPRINT, "set", "Footprint tags", "", f"{SNAPEDA_FOOTPRINT} P1.5mm", "generated", scope="footprint"
        ),
    ]


def test_snapeda_symbol_cleaned(tmp_path):
    layout = _snapeda_layout(tmp_path)
    with _open_snapeda(tmp_path) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library=SNAPEDA_LIBRARY, datasheet=SNAPEDA_DATASHEET), layout, ToolContext())
        assert not plan.blocked, [i.text for i in plan.issues]
        symbol = _symbol_in(plan, SNAPEDA_SYMBOL)
        assert _property_names(symbol) == SNAPEDA_NAMES
        assert find_property(symbol.node, "Manufacturer").value == SNAPEDA_MANUFACTURER
        assert find_property(symbol.node, "MPN").value == SNAPEDA_MPN
        assert find_property(symbol.node, "Description").value == SNAPEDA_DESCRIPTION
        assert list(plan.field_changes) == _snapeda_changes()


def test_field_change_rows(tmp_path):
    layout = _snapeda_layout(tmp_path)
    with _open_snapeda(tmp_path) as (_, candidate):
        options = InstallOptions(library=SNAPEDA_LIBRARY, datasheet=SNAPEDA_DATASHEET)
        plan = build_plan(candidate, options, layout, ToolContext())
        section = next(s for s in preview_sections(plan, candidate, options) if s.name == "Field changes")
        assert len(section.rows) == len(plan.field_changes)
        by_text = {row.text: row.detail for row in section.rows}
        assert by_text["Rename MF"] == "→ Manufacturer"
        assert by_text["Set Value"] == f"{SNAPEDA_SYMBOL} → {SNAPEDA_MPN}: follows the MPN"
        assert by_text["Drop MANUFACTURER"] == "GCT → (removed): duplicate Manufacturer/MPN alias"
        assert by_text["Drop Package"] == "None → (removed): empty or placeholder value"


# -- duplicate aliases (D-08) -----------------------------------------------------------------------


def test_duplicate_aliases_dropped(tmp_path):
    props = {"MF": "Acme Corp", "MANUFACTURER": "ACME", "MP": "A-1", "MANUFACTURER_PART_NUMBER": "A-1"}
    plan, _ = _plan_vendor(tmp_path, props)
    assert not plan.blocked, [i.text for i in plan.issues]
    names = _property_names(_symbol_in(plan))
    assert (_value_of(plan, "Manufacturer"), _value_of(plan, "MPN")) == ("Acme Corp", "A-1")
    assert "MANUFACTURER" not in names and "MANUFACTURER_PART_NUMBER" not in names
    assert "MF" not in names and "MP" not in names
    assert _drops(plan) == [("MANUFACTURER", "duplicate"), ("MANUFACTURER_PART_NUMBER", "duplicate")]


# -- placeholder values (D-06) ----------------------------------------------------------------------


def test_placeholder_vendor_fields_dropped(tmp_path):
    props = {"Package": "None", "Height": "", "Note": " N/A ", "Grade": "Automotive"}
    plan, _ = _plan_vendor(tmp_path, props)
    assert not plan.blocked, [i.text for i in plan.issues]
    assert _drops(plan) == [("Package", "placeholder"), ("Height", "placeholder"), ("Note", "placeholder")]
    names = _property_names(_symbol_in(plan))
    assert "Grade" in names
    assert not {"Package", "Height", "Note"} & set(names)


def test_protected_fields_never_dropped(tmp_path):
    plan, _ = _plan_vendor(tmp_path, {"Description": "", "ki_description": ""}, datasheet="", keywords="")
    # The empty fields are kept, and the atomic gate refuses the part for them (D-21)
    gate = [i.code for i in plan.issues if i.severity is Severity.ERROR]
    assert gate == ["install.atomic.manufacturer", "install.atomic.datasheet", "install.atomic.description"]
    assert plan.blocked
    names = _property_names(_symbol_in(plan))
    for kept in ("Datasheet", "Description", "ki_description", "ki_keywords", "ki_locked", "ki_fp_filters"):
        assert kept in names, names
    assert not [c for c in plan.field_changes if c.action == "drop"]


def test_protection_and_placeholder_rules():
    for name in ("Reference", "Value", "Footprint", "Datasheet", "Description", "ki_locked", "KI_Anything"):
        assert fieldrules.is_protected(name)
    assert not fieldrules.is_protected("Package") and not fieldrules.is_protected("MF")
    for value in ("", "  ", "None", "none", " N/A ", "n/a"):
        assert fieldrules.is_placeholder(value)
    assert not fieldrules.is_placeholder("0") and not fieldrules.is_placeholder("Nonesuch")


def test_ul_property_list_unchanged_by_cleanup(ul_package, tmp_path):
    _, candidate = ul_package
    write_custom_layout(tmp_path / "repo", [UL_LIBRARY], [footprint_library_for(UL_LIBRARY)])
    layout = RepoLayout.for_repo(tmp_path / "repo")
    plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY, description=UL_DESCRIPTION), layout, ToolContext())
    assert not plan.blocked, [i.text for i in plan.issues]
    assert "ki_locked" in _property_names(_symbol_in(plan, "CSD85301Q2"))
    assert not [c for c in plan.field_changes if c.action == "drop"]


def test_generic_volatile_for_unknown_vendor(tmp_path):
    props = {
        "Price": "1.20",
        "Mouser Price/Stock": "https://example.invalid/p",
        "Stock Code": "SC-1",
        "Mouser Part Number": "123-ABC",
    }
    plan, _ = _plan_vendor(tmp_path, props)
    assert not plan.blocked, [i.text for i in plan.issues]
    assert _drops(plan) == [("Price", "volatile"), ("Mouser Price/Stock", "volatile")]
    names = _property_names(_symbol_in(plan))
    assert "Stock Code" in names and "Mouser Part Number" in names


def test_placeholder_alias_is_absent(tmp_path):
    plan, candidate = _plan_vendor(tmp_path, {"MF": "N/A"})
    assert not plan.blocked, [i.text for i in plan.issues]
    assert candidate.symbols[0].meta.manufacturer == ""
    assert _value_of(plan, "Manufacturer") == "Texas Instruments"
    assert "install.atomic.manufacturer" not in [i.code for i in plan.issues]

    second = tmp_path / "second"
    second.mkdir()
    plan, _ = _plan_vendor(second, {"MF": "None", "MANUFACTURER": "Acme"})
    assert not plan.blocked, [i.text for i in plan.issues]
    assert _value_of(plan, "Manufacturer") == "Acme"
    names = _property_names(_symbol_in(plan))
    assert "MF" not in names and "MANUFACTURER" not in names
    assert ("MF", "duplicate") in _drops(plan)


# -- the library is never touched (T-07-08) ---------------------------------------------------------


def test_cleanup_never_touches_existing_symbols(tmp_path):
    layout = _snapeda_layout(tmp_path)
    target = layout.symbols_dir / f"{SNAPEDA_LIBRARY}.kicad_sym"
    old = symbol_lib(("OLD_PART",), props={"Price": "1.00", "MANUFACTURER": "X", "Package": "None"})
    target.write_bytes(old)
    old_block = _block(old, "OLD_PART")
    with _open_snapeda(tmp_path) as (package, candidate):
        plan = build_plan(candidate, InstallOptions(library=SNAPEDA_LIBRARY, datasheet=SNAPEDA_DATASHEET), layout, ToolContext())
        assert not plan.blocked, [i.text for i in plan.issues]
        assert _block(_op(plan, "symbol_lib").data, "OLD_PART") == old_block
        # Only the incoming symbol and its footprint list changes; OLD_PART is untouched
        assert {c.symbol for c in plan.field_changes if c.scope == "symbol"} == {SNAPEDA_SYMBOL}
        assert {c.symbol for c in plan.field_changes if c.scope == "footprint"} == {SNAPEDA_FOOTPRINT}
        result = apply_plan(plan, backup_root=tmp_path / "bk")
        assert result.ok, [i.text for i in result.issues]
    assert _block(target.read_bytes(), "OLD_PART") == old_block


def _block(data, name):
    loaded = parse_bytes(data, "lib")
    ref = find_symbol(loaded.root, name)
    return loaded.source.text[ref.node.start : ref.node.end]


# -- remove_property_edit edges ---------------------------------------------------------------------


def test_remove_property_edit_edges():
    lf = symbol_lib((VENDOR,), props={"A": "1", "B": "2", "C": "3"})
    loaded = parse_bytes(lf, "lib")
    node = find_symbol(loaded.root, VENDOR).node
    props = {p.name: p for p in list_properties(node)}
    text = loaded.source.text

    # The last property removed together with a zero-width insert at its end
    insert = property_insert_edit(text, node, '(property "D" "4" (at 0 0 0))', "\n")
    out = apply_edits(text, [remove_property_edit(text, props["C"]), insert])
    names = _property_names(find_symbol(parse_bytes(out.encode(), "lib").root, VENDOR))
    assert names == ["Reference", "Value", "A", "B", "D"]

    # Two adjacent properties removed
    out = apply_edits(text, [remove_property_edit(text, props["A"]), remove_property_edit(text, props["B"])])
    names = _property_names(find_symbol(parse_bytes(out.encode(), "lib").root, VENDOR))
    assert names == ["Reference", "Value", "C"]

    crlf = vendor_symbol_lib(VENDOR, props={"A": "1", "B": "2"})
    loaded = parse_bytes(crlf, "lib")
    node = find_symbol(loaded.root, VENDOR).node
    text = loaded.source.text
    prop = next(p for p in list_properties(node) if p.name == "A")
    out = apply_edits(text, [remove_property_edit(text, prop)])
    assert out.count("\r\n") == out.count("\n")


# -- descriptions (D-07) and the MPN fallback (Pattern 4) --------------------------------------------


def test_description_whitespace_collapsed(tmp_path):
    layout = _snapeda_layout(tmp_path)
    with _open_snapeda(tmp_path) as (_, candidate):
        options = InstallOptions(library=SNAPEDA_LIBRARY, datasheet=SNAPEDA_DATASHEET)
        plan = build_plan(candidate, options, layout, ToolContext())
        assert not plan.blocked, [i.text for i in plan.issues]
        assert _value_of(plan, "Description", SNAPEDA_SYMBOL) == SNAPEDA_DESCRIPTION
        clean = FieldChange(SNAPEDA_SYMBOL, "clean", "Description", SNAPEDA_DESCRIPTION_RAW, SNAPEDA_DESCRIPTION, "whitespace")
        changes = list(plan.field_changes)
        assert clean in changes
        assert changes.index(FieldChange(SNAPEDA_SYMBOL, "rename", "MP", "", "MPN", "alias")) + 1 == changes.index(clean)
        assert changes[changes.index(clean) + 1].field == "MANUFACTURER"
        section = next(s for s in preview_sections(plan, candidate, options) if s.name == "Field changes")
        row = next(r for r in section.rows if r.text == "Clean Description")
        assert row.detail.endswith("→ USB Type-C receptacle, 16 pins")
        assert "\\n" in row.detail and "\n" not in row.detail


def test_ki_description_collapsed(tmp_path):
    plan, _ = _plan_vendor(tmp_path, {"ki_description": "  two   spaces "})
    assert not plan.blocked, [i.text for i in plan.issues]
    assert _value_of(plan, "ki_description") == "two spaces"
    assert FieldChange(VENDOR, "clean", "ki_description", "  two   spaces ", "two spaces", "whitespace") in plan.field_changes


def test_description_override_not_cleaned(tmp_path):
    layout = _snapeda_layout(tmp_path)
    with _open_snapeda(tmp_path) as (_, candidate):
        options = InstallOptions(library=SNAPEDA_LIBRARY, datasheet=SNAPEDA_DATASHEET, description="Typed  text")
        plan = build_plan(candidate, options, layout, ToolContext())
        assert not plan.blocked, [i.text for i in plan.issues]
        assert _value_of(plan, "Description", SNAPEDA_SYMBOL) == "Typed  text"
        assert not [c for c in plan.field_changes if c.field == "Description"]


def test_mpn_fallback_is_meta_mpn(tmp_path):
    layout = _library_layout(tmp_path)
    symbol = vendor_symbol_lib(VENDOR, props={"Description": ATOMIC_PROPS["Description"]})
    with _open_vendor(tmp_path, symbol, model="part.stp") as (_, candidate):
        item = candidate.symbols[0]
        hinted = dataclasses.replace(candidate, symbols=(dataclasses.replace(item, meta=dataclasses.replace(item.meta, mpn="HINT-9")),))
        plan = build_plan(hinted, InstallOptions(library=LIBRARY), layout, ToolContext())
        assert not plan.blocked, [i.text for i in plan.issues]
        assert _value_of(plan, "MPN") == "HINT-9"
        assert plan.model_file == "HINT-9.stp"
        assert form.field_defaults(hinted, VENDOR).mpn == "HINT-9"
        # Without a hint the vendor symbol name stays the fallback
        plain = build_plan(candidate, InstallOptions(library=LIBRARY), layout, ToolContext())
        assert _value_of(plain, "MPN") == VENDOR
