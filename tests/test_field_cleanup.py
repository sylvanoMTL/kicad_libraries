"""Field cleanup of the incoming symbol for every vendor (Phase 7, D-05 to D-09).

Duplicate Manufacturer/MPN aliases and placeholder-valued fields are dropped, description whitespace is
collapsed, and every rename, drop and clean is a FieldChange on the plan and a "Field changes" preview
row. The tests run on synthetic packages in a synthetic Custom/ under tmp_path, with ToolContext() and no
kicad-cli, because kicad-cli 10 trims descriptions itself and would hide the rule under test.
"""

from contextlib import contextmanager
from pathlib import Path

from installfixtures import vendor_footprint, vendor_symbol_lib
from vendorfixtures import SNAPEDA_MANUFACTURER, SNAPEDA_MPN, SNAPEDA_SYMBOL, snapeda_zip
from zipfixtures import (
    CURRENT_CUSTOM_FOOTPRINT_LIBS,
    CURRENT_CUSTOM_SYMBOL_LIBS,
    STEP_BYTES,
    make_zip,
    symbol_lib,
    write_custom_layout,
)

from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer import fieldrules
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
from kicad_lib_manager.models import Issue
from kicad_lib_manager.sexpr import apply_edits

REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPEDA_LIBRARY = "Connector_USB_GCT"
VENDOR = "PART"
LIBRARY = "IC_Test_TI"


def _snapeda_layout(tmp_path):
    write_custom_layout(tmp_path / "repo", CURRENT_CUSTOM_SYMBOL_LIBS, CURRENT_CUSTOM_FOOTPRINT_LIBS)
    return RepoLayout.for_repo(tmp_path / "repo")


def _library_layout(tmp_path):
    write_custom_layout(tmp_path / "repo", [LIBRARY], [LIBRARY])
    return RepoLayout.for_repo(tmp_path / "repo")


@contextmanager
def _open_snapeda(tmp_path):
    zip_path = snapeda_zip(tmp_path / "src" / f"{SNAPEDA_SYMBOL}.zip", with_model=True)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield package, candidate


@contextmanager
def _open_vendor(tmp_path, symbol):
    """Open a one-symbol vendor zip (symbol PART, footprint FP, a STEP model); yields (package, candidate)."""
    members = [("part.kicad_sym", symbol), ("FP.kicad_mod", vendor_footprint("FP")), ("part.step", STEP_BYTES)]
    (tmp_path / "src").mkdir(exist_ok=True)
    zip_path = make_zip(tmp_path / "src" / "pkg.zip", members)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield package, candidate


def _plan_vendor(tmp_path, props=None, **kwargs):
    layout = _library_layout(tmp_path)
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
]


def _snapeda_changes():
    s = SNAPEDA_SYMBOL
    return [
        FieldChange(s, "rename", "MF", "", "Manufacturer", "alias"),
        FieldChange(s, "drop", "Package", "None", "", "placeholder"),
        FieldChange(s, "drop", "Price", "None", "", "volatile"),
        FieldChange(
            s, "drop", "Check_prices", "https://www.snapeda.com/parts/USBC4242-01-0099-A/prices/", "", "volatile"
        ),
        FieldChange(s, "rename", "MP", "", "MPN", "alias"),
        FieldChange(s, "drop", "MANUFACTURER", "GCT", "", "duplicate"),
        FieldChange(s, "drop", "Availability", "In Stock", "", "volatile"),
        FieldChange(s, "drop", "SNAPEDA_PN", SNAPEDA_MPN, "", "duplicate"),
    ]


def test_snapeda_symbol_cleaned(tmp_path):
    layout = _snapeda_layout(tmp_path)
    with _open_snapeda(tmp_path) as (_, candidate):
        plan = build_plan(candidate, InstallOptions(library=SNAPEDA_LIBRARY), layout, ToolContext())
        assert not plan.blocked, [i.text for i in plan.issues]
        symbol = _symbol_in(plan, SNAPEDA_SYMBOL)
        assert _property_names(symbol) == SNAPEDA_NAMES
        assert find_property(symbol.node, "Manufacturer").value == SNAPEDA_MANUFACTURER
        assert find_property(symbol.node, "MPN").value == SNAPEDA_MPN
        assert list(plan.field_changes) == _snapeda_changes()


def test_field_change_rows(tmp_path):
    layout = _snapeda_layout(tmp_path)
    with _open_snapeda(tmp_path) as (_, candidate):
        options = InstallOptions(library=SNAPEDA_LIBRARY)
        plan = build_plan(candidate, options, layout, ToolContext())
        section = next(s for s in preview_sections(plan, candidate, options) if s.name == "Field changes")
        assert len(section.rows) == len(plan.field_changes)
        by_text = {row.text: row.detail for row in section.rows}
        assert by_text["Rename MF"] == "→ Manufacturer"
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
    assert not plan.blocked, [i.text for i in plan.issues]
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
    write_custom_layout(tmp_path / "repo", ["IC_Battery_Charger_TI"], ["IC_Battery_Charger_TI"])
    layout = RepoLayout.for_repo(tmp_path / "repo")
    plan = build_plan(candidate, InstallOptions(library="IC_Battery_Charger_TI"), layout, ToolContext())
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
    assert _value_of(plan, "Manufacturer") == "TI"
    assert "install.manufacturer_missing" not in [i.code for i in plan.issues]

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
        plan = build_plan(candidate, InstallOptions(library=SNAPEDA_LIBRARY), layout, ToolContext())
        assert not plan.blocked, [i.text for i in plan.issues]
        assert _block(_op(plan, "symbol_lib").data, "OLD_PART") == old_block
        assert {c.symbol for c in plan.field_changes} == {SNAPEDA_SYMBOL}
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
