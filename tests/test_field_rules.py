"""The rules that decide a written symbol's fields, one section per rule (Phase 10, D-22 and following).

Value rule: every symbol the install writes gets Value equal to its own final MPN. Manufacturer rule: the
Manufacturer is the canonical table spelling, taken from the vendor, the owner or the datasheet link's
company domain. The rules sit in the planner, so the form defaults, the preview and the dialog show what
the plan writes, and no caller can set another Value. The tests run on synthetic packages in a synthetic Custom/ under tmp_path with
ToolContext() and no kicad-cli.
"""

import dataclasses
from contextlib import contextmanager
from pathlib import Path

import pytest
from installfixtures import extends_pair, vendor_footprint, vendor_symbol_lib
from PySide6.QtCore import QSettings, Qt
from zipfixtures import (
    STEP_BYTES,
    footprint_library_for,
    make_zip,
    write_custom_layout,
)

from kicad_lib_manager import settings
from kicad_lib_manager.importer import form
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.plan import FieldChange, InstallOptions, Resolution, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.importer.preview import preview_sections
from kicad_lib_manager.kicad_files import find_property, find_symbol, parse_bytes
from kicad_lib_manager.models import Issue
from kicad_lib_manager.widgets.import_dialog import ImportCore, ImportDialog

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY = "Atomic_Analog"
VENDOR = "PART"


def _layout(tmp_path):
    write_custom_layout(tmp_path / "repo", [LIBRARY], [footprint_library_for(LIBRARY)])
    return RepoLayout.for_repo(tmp_path / "repo")


@contextmanager
def _open_vendor(tmp_path, symbol):
    """Open a one-symbol vendor zip (symbol bytes given, footprint FP, a STEP model); yields the candidate."""
    members = [("part.kicad_sym", symbol), ("FP.kicad_mod", vendor_footprint("FP")), ("part.step", STEP_BYTES)]
    (tmp_path / "src").mkdir(exist_ok=True)
    zip_path = make_zip(tmp_path / "src" / "pkg.zip", members)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield candidate


def _plan(tmp_path, data, **options):
    layout = _layout(tmp_path)
    with _open_vendor(tmp_path, data) as candidate:
        plan = build_plan(candidate, InstallOptions(library=LIBRARY, **options), layout, ToolContext())
        assert not plan.blocked, [i.text for i in plan.issues]
        return plan, candidate


def _symbol_value(plan, name, field="Value"):
    op = next(op for op in plan.ops if op.kind == "symbol_lib")
    loaded = parse_bytes(op.data, "lib")
    assert not isinstance(loaded, Issue), loaded
    symbol = find_symbol(loaded.root, name)
    assert symbol is not None, name
    prop = find_property(symbol.node, field)
    return None if prop is None else prop.value


def _sets(plan, field="Value"):
    """The set changes of one field; the Value section looks at Value only, since a ti.com link also finds a Manufacturer."""
    return [c for c in plan.field_changes if c.action == "set" and c.field == field]


# -- Value follows the MPN (D-22) ---------------------------------------------------------------------


def test_value_follows_mpn_and_is_listed(tmp_path):
    symbol = vendor_symbol_lib(VENDOR, value="10k", props={"MPN": "PART-1"})
    plan, _ = _plan(tmp_path, symbol)
    assert _symbol_value(plan, VENDOR) == "PART-1"
    assert _sets(plan) == [FieldChange(VENDOR, "set", "Value", "10k", "PART-1", "follows_mpn")]


def test_set_value_row_in_the_preview(tmp_path):
    symbol = vendor_symbol_lib(VENDOR, value="10k", props={"MPN": "PART-1"})
    plan, candidate = _plan(tmp_path, symbol)
    options = InstallOptions(library=LIBRARY)
    section = next(s for s in preview_sections(plan, candidate, options) if s.name == "Field changes")
    assert {row.text: row.detail for row in section.rows}["Set Value"] == "10k → PART-1: follows the MPN"


def test_preview_words_for_every_set_reason(tmp_path):
    symbol = vendor_symbol_lib(VENDOR, value="10k", props={"MPN": "PART-1"})
    plan, candidate = _plan(tmp_path, symbol)
    changes = tuple(FieldChange(VENDOR, "set", "Thing", "a", "b", reason) for reason in
                    ("follows_mpn", "canonical", "datasheet_host"))
    forced = dataclasses.replace(plan, field_changes=changes)
    section = next(s for s in preview_sections(forced, candidate, InstallOptions(library=LIBRARY)) if s.name == "Field changes")
    assert [row.detail for row in section.rows] == [
        "a → b: follows the MPN",
        "a → b: canonical spelling",
        "a → b: found from the datasheet link",
    ]


def test_field_defaults_value_is_the_mpn_default(tmp_path):
    symbol = vendor_symbol_lib(VENDOR, value="10k", props={"MPN": "PART-1"})
    _, candidate = _plan(tmp_path, symbol)
    defaults = form.field_defaults(candidate, VENDOR)
    assert (defaults.value, defaults.mpn) == ("PART-1", "PART-1")


def test_field_defaults_value_falls_back_to_the_symbol_name(tmp_path):
    symbol = vendor_symbol_lib(VENDOR, value="10k")
    plan, candidate = _plan(tmp_path, symbol)
    defaults = form.field_defaults(candidate, VENDOR)
    assert defaults.value == defaults.mpn == VENDOR
    assert _symbol_value(plan, VENDOR) == VENDOR


# -- parents, typed MPNs, renames, and the removed override -------------------------------------------


def test_each_symbol_of_an_extends_pair_follows_its_own_mpn(tmp_path):
    pair = extends_pair().replace(b'"Value" "PARENT_X"', b'"Value" "10k"').replace(b'"Value" "CHILD_Y"', b'"Value" "20k"')
    plan, _ = _plan(tmp_path, pair, symbol="CHILD_Y")
    assert plan.symbol_names == ("PARENT_X", "CHILD_Y")
    assert _sets(plan) == [
        FieldChange("PARENT_X", "set", "Value", "10k", "PARENT_X", "follows_mpn"),
        FieldChange("CHILD_Y", "set", "Value", "20k", "CHILD_Y", "follows_mpn"),
    ]
    for name in plan.symbol_names:
        assert _symbol_value(plan, name) == _symbol_value(plan, name, "MPN") == name


def test_a_typed_mpn_drives_the_value(tmp_path):
    symbol = vendor_symbol_lib(VENDOR, value="10k", props={"MPN": "PART-1"})
    plan, _ = _plan(tmp_path, symbol, mpn="NEW-1")
    assert _symbol_value(plan, VENDOR, "MPN") == "NEW-1"
    assert _symbol_value(plan, VENDOR) == "NEW-1"
    assert _sets(plan) == [FieldChange(VENDOR, "set", "Value", "10k", "NEW-1", "follows_mpn")]


def test_a_renamed_symbol_gets_its_mpn_not_the_retokened_value(tmp_path):
    symbol = vendor_symbol_lib(VENDOR, value=VENDOR, props={"MPN": "PART-1"})
    layout = _layout(tmp_path)
    # The library already holds a different symbol of the same name, so the install must rename the incoming one
    other = vendor_symbol_lib(VENDOR, props={"MPN": "OTHER-9"})
    (layout.symbols_dir / f"{LIBRARY}.kicad_sym").write_bytes(other)
    with _open_vendor(tmp_path, symbol) as candidate:
        first = build_plan(candidate, InstallOptions(library=LIBRARY), layout, ToolContext())
        conflict = next(c for c in first.conflicts if c.kind == "symbol")
        options = InstallOptions(library=LIBRARY, resolutions={conflict.key: Resolution("rename", "PART_B")})
        plan = build_plan(candidate, options, layout, ToolContext())
        assert not plan.blocked, [i.text for i in plan.issues]
    assert plan.symbol_name == "PART_B"
    assert _symbol_value(plan, "PART_B") == "PART-1"
    assert _symbol_value(plan, "PART_B", "MPN") == "PART-1"


def test_a_value_already_equal_to_the_mpn_gets_no_set_change(tmp_path):
    symbol = vendor_symbol_lib(VENDOR, value="PART-1", props={"MPN": "PART-1"})
    plan, _ = _plan(tmp_path, symbol)
    assert _symbol_value(plan, VENDOR) == "PART-1"
    assert _sets(plan) == []


def test_install_options_has_no_value_override():
    with pytest.raises(TypeError):
        InstallOptions(library=LIBRARY, value="x")  # type: ignore[call-arg]
    with pytest.raises(ValueError):
        InstallOptions(library=LIBRARY, cleared=frozenset({"value"}))


def test_build_options_never_passes_a_value():
    values = form.FormValues(
        library=LIBRARY, symbol=None, footprint=None, model=None, no_model=False, footprint_name=None,
        fields={"value": "typed", "mpn": "M-1"},
    )
    options = form.build_options(values, form.FieldDefaults(value="V", mpn="P"))
    assert options.mpn == "M-1"
    assert not hasattr(options, "value")


# -- the dialog: Value is read-only and mirrors the MPN -----------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qsettings"))
    assert tmp_path.resolve() in Path(settings.get_settings().fileName()).resolve().parents


def test_dialog_value_is_read_only_and_mirrors_the_mpn(qtbot, atomic_custom, tmp_path):
    symbol = vendor_symbol_lib(VENDOR, value="10k", props={"MPN": "PART-1"})
    (tmp_path / "src").mkdir()
    zip_path = make_zip(
        tmp_path / "src" / "pkg.zip",
        [("part.kicad_sym", symbol), ("FP.kicad_mod", vendor_footprint("FP")), ("part.step", STEP_BYTES)],
    )
    core = dataclasses.replace(
        ImportCore(), detect_tools=lambda kicad_fp_dir: ToolContext(), kicad_running=lambda: [], downloads_dir=lambda: None
    )
    dialog = ImportDialog(atomic_custom.repo_root, atomic_custom, core=core, backup_root=tmp_path / "backups")
    qtbot.addWidget(dialog)
    dialog.open_path(zip_path)
    qtbot.waitUntil(
        lambda: dialog._plan is not None and dialog._plan_gen == dialog._gen and dialog._building is None
        and dialog._queued is None and not dialog._dirty,
        timeout=30000,
    )
    value, mpn = dialog._field_edits["value"], dialog._field_edits["mpn"]
    assert value.isReadOnly()
    assert value.toolTip() == "Value follows the MPN"
    assert value.text() == mpn.text() == "PART-1"
    mpn.setFocus()
    mpn.selectAll()
    qtbot.keyClicks(mpn, "ABC-9")
    assert value.text() == "ABC-9"  # at once, before any rebuild
    assert not dialog._field_restore["value"].isEnabled()
    mpn.selectAll()
    qtbot.keyClick(mpn, Qt.Key.Key_Backspace)
    assert value.text() == ""
    dialog._field_restore["mpn"].click()
    assert value.text() == mpn.text() == "PART-1"


# -- Manufacturer is canonical (D-23) -----------------------------------------------------------------


def _symbol_manufacturer(plan, name=VENDOR):
    return _symbol_value(plan, name, "Manufacturer")


def _open_dialog(qtbot, atomic_custom, tmp_path, symbol):
    (tmp_path / "src").mkdir(exist_ok=True)
    zip_path = make_zip(
        tmp_path / "src" / "pkg.zip",
        [("part.kicad_sym", symbol), ("FP.kicad_mod", vendor_footprint("FP")), ("part.step", STEP_BYTES)],
    )
    core = dataclasses.replace(
        ImportCore(), detect_tools=lambda kicad_fp_dir: ToolContext(), kicad_running=lambda: [], downloads_dir=lambda: None
    )
    dialog = ImportDialog(atomic_custom.repo_root, atomic_custom, core=core, backup_root=tmp_path / "backups")
    qtbot.addWidget(dialog)
    dialog.open_path(zip_path)
    qtbot.waitUntil(
        lambda: dialog._plan is not None and dialog._plan_gen == dialog._gen and dialog._building is None
        and dialog._queued is None and not dialog._dirty,
        timeout=30000,
    )
    return dialog


def test_a_vendor_alias_is_written_in_the_canonical_spelling(tmp_path):
    symbol = vendor_symbol_lib(VENDOR, props={"Manufacturer": "TI"})
    plan, _ = _plan(tmp_path, symbol)
    assert _symbol_manufacturer(plan) == "Texas Instruments"
    assert _sets(plan, "Manufacturer") == [FieldChange(VENDOR, "set", "Manufacturer", "TI", "Texas Instruments", "canonical")]


def test_canonical_manufacturer_row_in_the_preview(tmp_path):
    symbol = vendor_symbol_lib(VENDOR, props={"Manufacturer": "TI"})
    plan, candidate = _plan(tmp_path, symbol)
    section = next(s for s in preview_sections(plan, candidate, InstallOptions(library=LIBRARY)) if s.name == "Field changes")
    assert {row.text: row.detail for row in section.rows}["Set Manufacturer"] == "TI → Texas Instruments: canonical spelling"


def test_field_defaults_manufacturer_is_canonical(tmp_path):
    symbol = vendor_symbol_lib(VENDOR, props={"Manufacturer": "TI"})
    _, candidate = _plan(tmp_path, symbol)
    assert form.field_defaults(candidate, VENDOR).manufacturer == "Texas Instruments"


def test_dialog_shows_the_canonical_manufacturer(qtbot, atomic_custom, tmp_path):
    symbol = vendor_symbol_lib(VENDOR, props={"Manufacturer": "TI"})
    dialog = _open_dialog(qtbot, atomic_custom, tmp_path, symbol)
    assert dialog._field_edits["manufacturer"].text() == "Texas Instruments"


def _plan_for(tmp_path, link, props=None, **options):
    """Plan a vendor symbol whose datasheet link is `link`."""
    symbol = vendor_symbol_lib(VENDOR, datasheet=link, props=props)
    return _plan(tmp_path, symbol, **options)


def _codes(plan):
    return [issue.code for issue in plan.issues]


@pytest.mark.parametrize(
    ("datasheet", "name"),
    [
        ("https://www.ti.com/lit/gpn/part", "Texas Instruments"),
        ("https://www.maximintegrated.com/x.pdf", "Maxim Integrated"),
        ("https://www.analog.com/x", "Analog Devices"),
    ],
)
def test_the_datasheet_link_names_the_manufacturer(tmp_path, datasheet, name):
    plan, candidate = _plan_for(tmp_path, datasheet)
    assert _symbol_manufacturer(plan) == name
    assert _sets(plan, "Manufacturer") == [FieldChange(VENDOR, "set", "Manufacturer", "", name, "datasheet_host")]
    assert "install.manufacturer_missing" not in _codes(plan)
    assert form.field_defaults(candidate, VENDOR).manufacturer == name
    section = next(s for s in preview_sections(plan, candidate, InstallOptions(library=LIBRARY)) if s.name == "Field changes")
    assert {row.text: row.detail for row in section.rows}["Set Manufacturer"] == f"(empty) → {name}: found from the datasheet link"


def test_a_distributor_link_is_never_used(tmp_path):
    plan, candidate = _plan_for(tmp_path, "https://www.digikey.com/x.pdf")
    assert _symbol_manufacturer(plan) == ""
    assert _sets(plan, "Manufacturer") == []
    aggregator = [i for i in plan.issues if i.code == "naming.aggregator_host"]
    assert len(aggregator) == 1
    assert aggregator[0].severity.value == "info"
    assert "www.digikey.com" in aggregator[0].text
    assert "install.manufacturer_missing" in _codes(plan)
    assert form.field_defaults(candidate, VENDOR).manufacturer == ""


def test_an_unlisted_domain_infers_nothing_and_says_nothing_about_a_distributor(tmp_path):
    plan, candidate = _plan_for(tmp_path, "https://www.example-widgets.com/x.pdf")
    assert _symbol_manufacturer(plan) == ""
    assert "naming.aggregator_host" not in _codes(plan)
    assert "install.manufacturer_missing" in _codes(plan)
    assert form.field_defaults(candidate, VENDOR).manufacturer == ""


def test_a_name_that_is_not_in_the_table_is_kept_as_typed(tmp_path):
    plan, candidate = _plan_for(tmp_path, "https://www.ti.com/x", props={"Manufacturer": "Acme Widgets"})
    assert _symbol_manufacturer(plan) == "Acme Widgets"
    assert _sets(plan, "Manufacturer") == []
    assert form.field_defaults(candidate, VENDOR).manufacturer == "Acme Widgets"


def test_a_typed_manufacturer_is_canonical_too(tmp_path):
    plan, _ = _plan_for(tmp_path, "https://www.ti.com/x", props={"Manufacturer": "Acme Widgets"}, manufacturer="ADI")
    assert _symbol_manufacturer(plan) == "Analog Devices"
    assert _sets(plan, "Manufacturer") == [FieldChange(VENDOR, "set", "Manufacturer", "ADI", "Analog Devices", "canonical")]


def test_a_cleared_manufacturer_is_written_empty_without_inference_or_warning(tmp_path):
    plan, _ = _plan_for(tmp_path, "https://www.ti.com/x", manufacturer="", cleared=frozenset({"manufacturer"}))
    assert _symbol_manufacturer(plan) == ""
    assert _sets(plan, "Manufacturer") == []
    assert "install.manufacturer_missing" not in _codes(plan)
    assert "naming.aggregator_host" not in _codes(plan)


def test_a_cleared_manufacturer_on_a_distributor_link_says_nothing(tmp_path):
    plan, _ = _plan_for(tmp_path, "https://www.digikey.com/x", manufacturer="", cleared=frozenset({"manufacturer"}))
    assert _symbol_manufacturer(plan) == ""
    assert "naming.aggregator_host" not in _codes(plan)
    assert "install.manufacturer_missing" not in _codes(plan)


def test_a_typed_datasheet_decides_where_the_manufacturer_is_found(tmp_path):
    plan, _ = _plan_for(tmp_path, "https://www.digikey.com/x", datasheet="https://www.analog.com/y")
    assert _symbol_manufacturer(plan) == "Analog Devices"
    assert "naming.aggregator_host" not in _codes(plan)


def test_a_renamed_alias_is_one_rename_and_one_canonical_set(tmp_path):
    plan, candidate = _plan_for(tmp_path, "https://www.digikey.com/x", props={"MF": "RECOM Power"})
    assert _symbol_manufacturer(plan) == "RECOM"
    assert [(c.action, c.field, c.old, c.new) for c in plan.field_changes if c.field in ("MF", "Manufacturer")] == [
        ("rename", "MF", "", "Manufacturer"),
        ("set", "Manufacturer", "RECOM Power", "RECOM"),
    ]
    assert form.field_defaults(candidate, VENDOR).manufacturer == "RECOM"
