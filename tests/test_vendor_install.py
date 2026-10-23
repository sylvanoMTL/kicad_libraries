"""Vendor packages installed into a synthetic Custom/ (D-03): intake, plan, preview, apply and commit message.

Every test builds its own Custom/ under ``tmp_path`` and its own vendor zip from ``vendorfixtures``.
No test reads the owner's real ``Custom/`` tree or a real vendor download.
"""

import dataclasses
from contextlib import contextmanager
from pathlib import Path

import installfixtures as inst
import zipfixtures as zf
from vendorfixtures import (
    SNAPEDA_FOOTPRINT,
    SNAPEDA_MANUFACTURER,
    SNAPEDA_MPN,
    SNAPEDA_SYMBOL,
    snapeda_zip,
)
from zipfixtures import CURRENT_CUSTOM_FOOTPRINT_LIBS, CURRENT_CUSTOM_SYMBOL_LIBS, write_custom_layout

from kicad_lib_manager.importer.adapters.snapeda import SNAPEDA_RULES
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.commit_plan import build_commit_plan, default_message
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.fieldrules import GENERIC_RULES
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
    remove_property_edit,
)
from kicad_lib_manager.models import Issue
from kicad_lib_manager.sexpr import apply_edits

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY = "Connector_USB_GCT"


def _snapeda_layout(tmp_path):
    """A synthetic Custom/ holding the current library names, built under tmp_path only (D-03)."""
    write_custom_layout(tmp_path / "repo", CURRENT_CUSTOM_SYMBOL_LIBS, CURRENT_CUSTOM_FOOTPRINT_LIBS)
    return RepoLayout.for_repo(tmp_path / "repo")


@contextmanager
def _open_snapeda(tmp_path, **members_kwargs):
    """Open a synthetic SnapEDA zip, yielding (package, candidate); the package stays open for apply_plan."""
    zip_path = snapeda_zip(tmp_path / "src" / f"{SNAPEDA_SYMBOL}.zip", **members_kwargs)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield package, candidate


def _plan_snapeda(candidate, layout, **options):
    """Plan the candidate into Connector_USB_GCT with no external tools (ToolContext())."""
    chosen = InstallOptions(library=LIBRARY, **options)
    return build_plan(candidate, chosen, layout, ToolContext()), chosen


def _symbol_in(data, name=SNAPEDA_SYMBOL):
    loaded = parse_bytes(data, "lib")
    assert not isinstance(loaded, Issue), loaded
    symbol = find_symbol(loaded.root, name)
    assert symbol is not None
    return symbol


def _op(plan, kind):
    return next(op for op in plan.ops if op.kind == kind)


def test_tracer_snapeda_end_to_end(tmp_path):
    layout = _snapeda_layout(tmp_path)
    with _open_snapeda(tmp_path) as (package, candidate):
        assert candidate.vendor == "SnapEDA"
        assert candidate.confidence >= 0.7
        assert "intake.unknown_vendor" not in [i.code for i in candidate.issues]

        plan, options = _plan_snapeda(candidate, layout)
        assert not plan.blocked, [i.text for i in plan.issues]
        assert plan.vendor == "SnapEDA"
        sections = preview_sections(plan, candidate, options)
        assert sections[0].name == "Files"

        symbol = _symbol_in(_op(plan, "symbol_lib").data)
        assert find_property(symbol.node, "Footprint").value == f"{LIBRARY}:{SNAPEDA_FOOTPRINT}"
        assert find_property(symbol.node, "Manufacturer").value == SNAPEDA_MANUFACTURER
        assert find_property(symbol.node, "MPN").value == SNAPEDA_MPN
        assert find_property(symbol.node, "SnapEDA_Link") is not None
        assert find_property(symbol.node, "MAXIMUM_PACKAGE_HEIGHT") is not None
        assert "install.no_model" in [i.code for i in plan.issues]

        result = apply_plan(plan, backup_root=tmp_path / "bk")
        assert result.ok, [i.text for i in result.issues]

        installed = layout.symbols_dir / f"{LIBRARY}.kicad_sym"
        assert installed.read_bytes() == _op(plan, "symbol_lib").data
        assert (layout.footprints_dir / f"{LIBRARY}.pretty" / f"{SNAPEDA_FOOTPRINT}.kicad_mod").is_file()

        message = default_message(build_commit_plan(result, plan, vendor_label=plan.vendor))
        assert "Import-Vendor: SnapEDA" in message.splitlines()


# -- field rules and volatile drops (D-05, D-09) ---------------------------------------------------

VOLATILE_FIELDS = ("Price", "Check_prices", "Availability")


def _property_names(symbol):
    return [p.name for p in list_properties(symbol.node)]


def test_snapeda_volatile_fields_dropped(tmp_path):
    layout = _snapeda_layout(tmp_path)
    with _open_snapeda(tmp_path) as (package, candidate):
        assert candidate.field_rules == SNAPEDA_RULES

        plan, _ = _plan_snapeda(candidate, layout)
        assert not plan.blocked, [i.text for i in plan.issues]

        drops = [c for c in plan.field_changes if c.reason == "volatile"]
        assert [c.field for c in drops] == list(VOLATILE_FIELDS)
        assert all(c.symbol == SNAPEDA_SYMBOL and c.action == "drop" for c in drops)
        assert drops[0].old == "None"

        symbol = _symbol_in(_op(plan, "symbol_lib").data)
        names = _property_names(symbol)
        for dropped in VOLATILE_FIELDS:
            assert dropped not in names
        assert find_property(symbol.node, "SnapEDA_Link") is not None
        assert find_property(symbol.node, "MAXIMUM_PACKAGE_HEIGHT") is not None
        assert find_property(symbol.node, "Manufacturer").value == SNAPEDA_MANUFACTURER
        assert find_property(symbol.node, "MPN").value == SNAPEDA_MPN

        result = apply_plan(plan, backup_root=tmp_path / "bk")
        assert result.ok, [i.text for i in result.issues]
        installed = (layout.symbols_dir / f"{LIBRARY}.kicad_sym").read_bytes()
        assert installed == _op(plan, "symbol_lib").data
        reread = _symbol_in(installed)
        assert not set(VOLATILE_FIELDS) & set(_property_names(reread))
        assert find_property(reread.node, "SnapEDA_Link") is not None


def test_generic_rules_for_other_vendors(ul_package, tmp_path):
    _, candidate = ul_package
    assert candidate.field_rules == GENERIC_RULES
    assert GENERIC_RULES.manufacturer_aliases == ("Manufacturer", "MF", "MANUFACTURER", "Manufacturer_Name")
    assert GENERIC_RULES.mpn_aliases == ("MPN", "MP", "Manufacturer_Part_Number", "MANUFACTURER_PART_NUMBER")

    write_custom_layout(tmp_path / "repo", ["IC_Battery_Charger_TI"], ["IC_Battery_Charger_TI"])
    layout = RepoLayout.for_repo(tmp_path / "repo")
    plan = build_plan(candidate, InstallOptions(library="IC_Battery_Charger_TI"), layout, ToolContext())
    assert not plan.blocked, [i.text for i in plan.issues]
    assert plan.field_changes == ()


def _names_of(data, symbol_name):
    loaded = parse_bytes(data, "lib")
    assert not isinstance(loaded, Issue), loaded
    return loaded, _property_names(find_symbol(loaded.root, symbol_name))


def _without(data, symbol_name, prop_name):
    loaded, names = _names_of(data, symbol_name)
    props = list_properties(find_symbol(loaded.root, symbol_name).node)
    prop = next(p for p in props if p.name == prop_name)
    return apply_edits(loaded.source.text, [remove_property_edit(loaded.source.text, prop)]), names


def test_remove_property_edit_basic():
    lf = zf.symbol_lib(("PART",), props={"Price": "1", "Stock": "9"})
    text, before = _without(lf, "PART", "Price")
    loaded, after = _names_of(text.encode("utf-8"), "PART")
    assert after == [n for n in before if n != "Price"]
    assert "\r" not in text and "\n\n" not in text
    assert loaded.source.eol == "\n"

    crlf = inst.vendor_symbol_lib("PART", props={"Price": "1", "Stock": "9"})
    text, before = _without(crlf, "PART", "Price")
    loaded, after = _names_of(text.encode("utf-8"), "PART")
    assert after == [n for n in before if n != "Price"]
    assert loaded.source.eol == "\r\n"
    assert text.count("\r\n") == text.count("\n")
    assert "\r\n\r\n" not in text


# -- the Field changes preview section (D-09, PREV-07) ----------------------------------------------


def _field_rows(sections):
    return next((s for s in sections if s.name == "Field changes"), None)


def test_field_changes_section(ul_package, tmp_path):
    layout = _snapeda_layout(tmp_path)
    with _open_snapeda(tmp_path) as (package, candidate):
        plan, options = _plan_snapeda(candidate, layout)
        sections = preview_sections(plan, candidate, options)
        names = [s.name for s in sections]
        assert names.index("Field changes") == names.index("Path rewrites") + 1

        section = _field_rows(sections)
        assert len(section.rows) == len(plan.field_changes)
        by_text = {row.text: row for row in section.rows}
        assert by_text["Drop Price"].detail == "None → (removed): price or stock data goes stale"
        assert "Drop Check_prices" in by_text
        assert "Drop Availability" in by_text
        assert all(row.kind == "rewrite" and row.tone == "default" for row in section.rows)

    _, ul_candidate = ul_package
    write_custom_layout(tmp_path / "ul", ["IC_Battery_Charger_TI"], ["IC_Battery_Charger_TI"])
    ul_options = InstallOptions(library="IC_Battery_Charger_TI")
    ul_plan = build_plan(ul_candidate, ul_options, RepoLayout.for_repo(tmp_path / "ul"), ToolContext())
    assert _field_rows(preview_sections(ul_plan, ul_candidate, ul_options)) is None


def test_field_change_row_format(tmp_path):
    layout = _snapeda_layout(tmp_path)
    with _open_snapeda(tmp_path) as (package, candidate):
        plan, options = _plan_snapeda(candidate, layout)
        note = "a" * 30 + "\n" + "b" * 10 + "\t" + "c" * 28
        assert len(note) == 70
        changes = (
            FieldChange("A", "drop", "Note", note, "", "placeholder"),
            FieldChange("A", "drop", "Height", "", "", "placeholder"),
            FieldChange("B", "clean", "Description", "x  y", "x y", "whitespace"),
            FieldChange("B", "rename", "MF", "", "Manufacturer", "alias"),
        )
        rows = _field_rows(preview_sections(dataclasses.replace(plan, field_changes=changes), candidate, options)).rows
        escaped = note.replace("\n", "\\n").replace("\t", "\\t")
        assert [(r.text, r.detail) for r in rows] == [
            ("A: Drop Note", escaped[:57] + "... → (removed): empty or placeholder value"),
            ("A: Drop Height", "(empty) → (removed): empty or placeholder value"),
            ("B: Clean Description", "x  y → x y"),
            ("B: Rename MF", "→ Manufacturer"),
        ]

        single = dataclasses.replace(plan, field_changes=changes[:1])
        only = _field_rows(preview_sections(single, candidate, options)).rows
        assert [r.text for r in only] == ["Drop Note"]
