"""Vendor packages installed into a synthetic Custom/ (D-03): intake, plan, preview, apply and commit message.

Every test builds its own Custom/ under ``tmp_path`` and its own vendor zip from ``vendorfixtures``.
No test reads the owner's real ``Custom/`` tree or a real vendor download.
"""

import dataclasses
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path

import installfixtures as inst
import pytest
import zipfixtures as zf
from vendorfixtures import (
    SAMACSYS_FOOTPRINT,
    SAMACSYS_MANUFACTURER,
    SAMACSYS_MPN,
    SAMACSYS_PART,
    SAMACSYS_ZIP_NAME,
    SNAPEDA_DESCRIPTION,
    SNAPEDA_FOOTPRINT,
    SNAPEDA_MANUFACTURER,
    SNAPEDA_MPN,
    SNAPEDA_SYMBOL,
    samacsys_zip,
    snapeda_zip,
)
from zipfixtures import CURRENT_CUSTOM_FOOTPRINT_LIBS, CURRENT_CUSTOM_SYMBOL_LIBS, write_custom_layout

from kicad_lib_manager import fsutil
from kicad_lib_manager.importer import kicad_cli
from kicad_lib_manager.importer.adapters.snapeda import SNAPEDA_RULES
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.candidate import ExistingLibrary
from kicad_lib_manager.importer.commit_plan import build_commit_plan, default_message
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.fieldrules import GENERIC_RULES
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, FieldChange, InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.importer.preview import preview_sections
from kicad_lib_manager.importer.suggest import suggest_library
from kicad_lib_manager.kicad_files import (
    find_models,
    find_property,
    find_symbol,
    footprint_name,
    list_properties,
    load,
    parse_bytes,
    remove_property_edit,
)
from kicad_lib_manager.models import Issue, Severity
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


# -- both vendors install like the UL sample (ROADMAP Phase 7 success criterion 3, D-03, D-04, D-10, D-15) ---


@dataclasses.dataclass(frozen=True)
class Case:
    """One synthetic vendor part and what its install must produce."""

    vendor: str
    build: Callable[[Path], Path]
    library: str
    symbol: str
    footprint: str
    model_file: str | None


CASES = {
    "snapeda": Case(
        "SnapEDA",
        lambda tmp: snapeda_zip(tmp / "src" / f"{SNAPEDA_SYMBOL}.zip"),
        LIBRARY,
        SNAPEDA_SYMBOL,
        SNAPEDA_FOOTPRINT,
        None,
    ),
    "snapeda_with_model": Case(
        "SnapEDA",
        lambda tmp: snapeda_zip(tmp / "src" / f"{SNAPEDA_SYMBOL}.zip", with_model=True),
        LIBRARY,
        SNAPEDA_SYMBOL,
        SNAPEDA_FOOTPRINT,
        f"{SNAPEDA_MPN}.step",
    ),
    "samacsys": Case(
        "SamacSys",
        lambda tmp: samacsys_zip(tmp / "src" / SAMACSYS_ZIP_NAME),
        "PowerSupply_DCDC_RECOM",
        SAMACSYS_PART,
        SAMACSYS_FOOTPRINT,
        "PSU7-0505S_Q1.stp",
    ),
}
by_case = pytest.mark.parametrize("case", CASES.values(), ids=list(CASES))
NO_CLI = ToolContext()


@contextmanager
def _open_case(case, tmp_path):
    """Yield (layout, candidate) for the case's synthetic zip and a synthetic Custom/; the package stays open (WR-04)."""
    layout = _snapeda_layout(tmp_path)
    with open_package(case.build(tmp_path), REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        assert candidate.vendor == case.vendor
        yield layout, candidate


@contextmanager
def _install_case(case, tmp_path, tools=NO_CLI):
    """Plan and apply the case; yield (layout, candidate, plan, result) with the package still open."""
    with _open_case(case, tmp_path) as (layout, candidate):
        plan = build_plan(candidate, InstallOptions(library=case.library), layout, tools)
        assert not plan.blocked, [i.text for i in plan.issues]
        yield layout, candidate, plan, apply_plan(plan, backup_root=tmp_path / "bk")


def _installed_symbol(layout, case):
    data = (layout.symbols_dir / f"{case.library}.kicad_sym").read_bytes()
    return _symbol_in(data, case.symbol)


def _installed_footprint(layout, case):
    path = layout.footprints_dir / f"{case.library}.pretty" / f"{case.footprint}.kicad_mod"
    return path, footprint_name(load(path).root)


def _errors(issues):
    return [i for i in issues if i.severity is Severity.ERROR]


@by_case
def test_vendor_install_links_like_ul(case, tmp_path):
    with _install_case(case, tmp_path) as (layout, _, plan, result):
        assert result.ok, [i.text for i in result.issues]
        issues = [*plan.issues, *result.issues]
        assert not _errors(issues)
        assert "verify.pin_pad_mismatch" not in [i.code for i in issues]

        symbol = _installed_symbol(layout, case)
        assert find_property(symbol.node, "Footprint").value == f"{case.library}:{case.footprint}"

        _, footprint = _installed_footprint(layout, case)
        models = [m.path for m in find_models(footprint.node)]
        model_dir = layout.models_dir
        if case.model_file is None:
            assert models == []
            assert [i.severity for i in plan.issues if i.code == "install.no_model"] == [Severity.WARNING]
            assert not model_dir.exists() or not list(model_dir.iterdir())
        else:
            assert models == [f"{MODEL_DIR_VAR}/{case.model_file}"]
            assert (model_dir / case.model_file).read_bytes().startswith(b"ISO-10303-21;")
            assert "install.no_model" not in [i.code for i in plan.issues]

        for op in plan.ops:
            if op.kind in ("symbol_lib", "footprint"):
                assert op.path.read_bytes() == op.data


def _values(symbol):
    return {p.name: p.value for p in list_properties(symbol.node)}


@pytest.mark.parametrize("name", ["snapeda", "samacsys"])
def test_vendor_field_outcomes(name, tmp_path):
    case = CASES[name]
    with _install_case(case, tmp_path) as (layout, _, _, result):
        assert result.ok, [i.text for i in result.issues]
        values = _values(_installed_symbol(layout, case))
    assert values["Value"] == case.symbol
    if name == "snapeda":
        assert values["Manufacturer"] == "Global Connector Technology" == SNAPEDA_MANUFACTURER
        assert values["MPN"] == "USBC4242-01-0099-A" == SNAPEDA_MPN
        assert values["Description"] == "USB Type-C receptacle, 16 pins" == SNAPEDA_DESCRIPTION
        assert values["STANDARD"] == "Manufacturer Recommendations"
        assert values["PARTREV"] == "B1"
        assert values["MAXIMUM_PACKAGE_HEIGHT"] == "3.2mm"
        assert values["SnapEDA_Link"].startswith("https://www.snapeda.com/parts/")
        gone = ("MANUFACTURER", "SNAPEDA_PN", "Price", "Check_prices", "Availability", "Package", "MF", "MP")
    else:
        assert values["Manufacturer"] == "RECOM Power" == SAMACSYS_MANUFACTURER
        assert values["MPN"] == "PSU7-0505S/Q1" == SAMACSYS_MPN
        assert values["Mouser Part Number"] == "919-PSU7-0505S/Q1"
        assert values["ki_description"] == "Isolated DC/DC converter 1W, 5V in, 5V out"
        gone = (
            "Mouser Price/Stock",
            "Arrow Price/Stock",
            "Height",
            "Arrow Part Number",
            "Manufacturer_Name",
            "Manufacturer_Part_Number",
        )
    for field in gone:
        assert field not in values, field


@by_case
def test_vendor_reinstall_is_noop(case, tmp_path, snapshot):
    with _install_case(case, tmp_path) as (layout, candidate, _, result):
        assert result.ok, [i.text for i in result.issues]
        after_first = snapshot(layout.custom_dir)
        again = build_plan(candidate, InstallOptions(library=case.library), layout, NO_CLI)
        assert again.is_noop
        assert again.field_changes == ()
        assert again.conflicts == ()
        second = apply_plan(again, backup_root=tmp_path / "bk")
        assert second.ok and second.touched == ()
        assert snapshot(layout.custom_dir) == after_first


@by_case
def test_vendor_install_rolls_back_on_failed_write(case, tmp_path, snapshot, monkeypatch):
    with _open_case(case, tmp_path) as (layout, candidate):
        plan = build_plan(candidate, InstallOptions(library=case.library), layout, NO_CLI)
        assert not plan.blocked, [i.text for i in plan.issues]
        last = len([op for op in plan.ops if op.kind != "mkdir"])
        assert last >= 2
        before = snapshot(layout.custom_dir)

        real = fsutil.atomic_write_bytes
        state = {"calls": 0, "failed": False}

        def flaky(path, data, **kwargs):
            if not state["failed"]:
                state["calls"] += 1
                if state["calls"] == last:
                    state["failed"] = True
                    return Issue(Severity.ERROR, "fs.write_failed", "injected")
            return real(path, data, **kwargs)

        monkeypatch.setattr(fsutil, "atomic_write_bytes", flaky)
        result = apply_plan(plan, backup_root=tmp_path / "bk")

        assert state["failed"] and not result.ok
        assert [i.code for i in _errors(result.issues)] == ["fs.write_failed", "install.rolled_back"]
        assert snapshot(layout.custom_dir) == before
        assert not list(layout.custom_dir.rglob("*.tmp"))


@pytest.mark.parametrize("vendor", ["SnapEDA", "SamacSys"])
def test_vendor_commit_trailer(vendor, tmp_path):
    case = CASES["snapeda" if vendor == "SnapEDA" else "samacsys"]
    with _install_case(case, tmp_path) as (_, _, plan, result):
        assert result.ok, [i.text for i in result.issues]
        message = default_message(build_commit_plan(result, plan, vendor_label=plan.vendor))
    assert f"Import-Vendor: {vendor}" in message.splitlines()


def test_vendor_suggestion_snapeda(tmp_path):
    existing = [
        ExistingLibrary(name, name in CURRENT_CUSTOM_SYMBOL_LIBS, name in CURRENT_CUSTOM_FOOTPRINT_LIBS)
        for name in CURRENT_CUSTOM_SYMBOL_LIBS
    ]
    with _open_case(CASES["snapeda"], tmp_path) as (_, candidate):
        suggestion = suggest_library(candidate.symbols[0].meta, existing)
    assert suggestion.name == LIBRARY


def _load_issues(exe, layout, case):
    """Run the real load check on the library and footprint now on disk; no format number is asserted (D-04)."""
    fp_path, _ = _installed_footprint(layout, case)
    symbol_lib = (layout.symbols_dir / f"{case.library}.kicad_sym").read_bytes()
    return kicad_cli.load_gate(
        exe, library=case.library, symbol_lib=symbol_lib, footprints=[(case.footprint, fp_path.read_bytes())]
    )


@pytest.mark.kicad_cli
@by_case
def test_vendor_installs_load_in_kicad(case, tmp_path, real_tools, kicad_cli_path):
    with _install_case(case, tmp_path, tools=real_tools) as (layout, _, _, result):
        assert result.ok, [i.text for i in result.issues]
        assert "install.cli_not_found" not in [i.code for i in result.issues]
        issues = _load_issues(kicad_cli_path, layout, case)
    assert _errors(issues) == [], issues
