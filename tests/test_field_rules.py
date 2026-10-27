"""The rules that decide a written symbol's fields, one section per rule (Phase 10, D-22 and following).

Value rule: every symbol the install writes gets Value equal to its own final MPN. The rule sits in the
planner, so the form defaults, the preview and the dialog show what the plan writes, and no caller can
set another Value. The tests run on synthetic packages in a synthetic Custom/ under tmp_path with
ToolContext() and no kicad-cli.
"""

import dataclasses
from contextlib import contextmanager
from pathlib import Path

import pytest
from installfixtures import vendor_footprint, vendor_symbol_lib
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
from kicad_lib_manager.importer.plan import FieldChange, InstallOptions, ToolContext
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


def _sets(plan):
    return [c for c in plan.field_changes if c.action == "set"]


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
