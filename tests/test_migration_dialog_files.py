"""The migration window, part 2: footprint/model/clash/derive controls and the Files tab (Phase 13 Plan 15).

Every test uses a fake MigrationCore (dataclasses.replace) with small hand-built Inventory /
MigrationPlan / GateOutcome values; the live Custom/ is never read. The fake_core fixture is
copied from tests/test_migration_dialog.py (tests do not import each other).
"""

from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt

from kicad_lib_manager.importer.migration.inventory import Inventory
from kicad_lib_manager.importer.migration.gate import GateOutcome
from kicad_lib_manager.importer.migration.plan import MigrationOp, MigrationPlan, PartPlan
from kicad_lib_manager.importer.migration.precheck import Precheck
from kicad_lib_manager.importer.plan import PartText, ToolContext
from kicad_lib_manager.models import Issue, Severity
from kicad_lib_manager.widgets.migration_dialog import (
    ADD_MODEL_TEXT,
    MigrationCore,
    MigrationDialog,
    MOVE_FOOTPRINT_TEXT,
    OFFICIAL_FOOTPRINT_TEXT,
    _REBUILD_DELAY_MS,
)

KEY_A = ("Custom/Symbols/Connector_USB_GCT.kicad_sym", "USB1")


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path / "qsettings"),
    )


def _empty_inventory(layout) -> Inventory:
    return Inventory(
        layout=layout, parts=(), footprints=(), models=(), model_linkers={}, bak_files=(),
        symbol_libraries=(), footprint_libraries=(), issues=(),
    )


def _part(
    key, source_library, target_library, new_name, *, mpn=None, footprint_old="", footprint_new="",
    footprint_target="shared", model_files=(), issues=(),
) -> PartPlan:
    return PartPlan(
        key=key,
        source_library=source_library,
        target_library=target_library,
        suggestion=None,
        old_name=key[1],
        new_name=new_name,
        mpn=mpn or new_name,
        parent=None,
        footprint_old=footprint_old,
        footprint_new=footprint_new,
        footprint_target=footprint_target,
        model_files=model_files,
        field_changes=(),
        generated_text=PartText(),
        part_text=PartText(),
        issues=issues,
    )


def _plan_for(inventory, parts=(), ops=()) -> MigrationPlan:
    return MigrationPlan(
        layout=inventory.layout,
        parts=tuple(parts),
        ops=tuple(ops),
        library_map=(),
        symbol_renames=(),
        footprint_links=(),
        model_renames=(),
        leftovers=(),
        families=(),
        conflicts=(),
        removed_libraries=(),
        bak_files=(),
        map_text="",
        issues=(),
    )


def core_with(tmp_path: Path, **changes) -> MigrationCore:
    fields = {
        "check_custom": lambda custom_dir, repo_root: Precheck(True, (), "head", "main", ""),
        "read_inventory": lambda layout: _empty_inventory(layout),
        "detect_tools": lambda kicad_fp_dir: ToolContext(),
        "prepare_context": lambda inventory, tools, kicad_fp_dir, progress=None: "ctx",
        "build_plan": lambda inventory, choices, ctx: _plan_for(inventory),
        "check_plan": lambda plan, inventory, kicad_fp_dir: GateOutcome((), {}),
        "fingerprints": lambda inventory: {},
        "load_draft": lambda path, repo_root: Issue(Severity.INFO, "draft.none", "No saved migration draft yet."),
        "draft_file": lambda repo_root: tmp_path / "draft.json",
        **changes,
    }
    return replace(MigrationCore(), **fields)


@pytest.fixture
def make_dialog(qtbot, tmp_path):
    def make(core: MigrationCore | None = None) -> MigrationDialog:
        dialog = MigrationDialog(tmp_path, None, core=core or core_with(tmp_path))
        qtbot.addWidget(dialog)
        return dialog

    return make


# -- Task 1: official footprint switch (D-08) -----------------------------------------------


def test_official_switch_reaches_the_plan(qtbot, make_dialog, tmp_path):
    part_a = _part(
        KEY_A, "Connector_USB_GCT", "Atomic_Connector", "USB1",
        footprint_old="Connector_USB_GCT:USB_Micro-B", footprint_new="Atomic_Footprints:USB_Micro-B_USB1",
    )
    captured = {}
    calls = {"official_candidates": 0}

    def fake_build_plan(inventory, choices, ctx):
        captured["choices"] = choices
        return _plan_for(inventory, (part_a,))

    def fake_official_candidates(footprint_index, folder, *, package_code, vendor_path, stock, part, progress=None):
        calls["official_candidates"] += 1
        return ["Package_TO_SOT_SMD:SOT-23-5", "Package_TO_SOT_SMD:SOT-23"]

    core = core_with(
        tmp_path,
        build_plan=fake_build_plan,
        check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {}),
        official_candidates=fake_official_candidates,
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._current_key == KEY_A)

    assert dialog._fp_move_radio.isChecked()
    assert dialog._official_box.isHidden()

    dialog._fp_official_radio.setChecked(True)
    qtbot.waitUntil(lambda: calls["official_candidates"] >= 1)
    qtbot.waitUntil(lambda: dialog._official_combo.count() == 2)
    assert not dialog._official_box.isHidden()
    assert dialog._official_hint_label.text() == "KiCad's own footprints are never changed"
    assert not dialog._official_hint_label.isHidden()

    dialog._official_combo.setCurrentText("Package_TO_SOT_SMD:SOT-23-5")
    dialog._official_combo.textActivated.emit("Package_TO_SOT_SMD:SOT-23-5")

    qtbot.waitUntil(lambda: captured.get("choices") is not None and KEY_A in captured["choices"].parts)
    choice = captured["choices"].parts[KEY_A]
    assert choice.footprint_target == "official"
    assert choice.official_footprint == "Package_TO_SOT_SMD:SOT-23-5"


def test_pad_mismatch_is_amber_not_blocking(qtbot, make_dialog, tmp_path):
    pad_issue = Issue(Severity.WARNING, "migration.pad_mismatch", "USB1: 2 pads do not match SOT-23-5")
    part_a = _part(
        KEY_A, "Connector_USB_GCT", "Atomic_Connector", "USB1",
        footprint_old="Connector_USB_GCT:USB_Micro-B", footprint_new="Package_TO_SOT_SMD:SOT-23-5",
        footprint_target="official", issues=(pad_issue,),
    )

    core = core_with(
        tmp_path,
        build_plan=lambda inventory, choices, ctx: _plan_for(inventory, (part_a,)),
        check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {}),
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._current_key == KEY_A)

    assert not dialog._pad_warning_label.isHidden()
    assert dialog._pad_warning_label.text() == pad_issue.text
    assert dialog._strip.count() == 0


def test_default_is_move(qtbot, make_dialog, tmp_path):
    part_a = _part(
        KEY_A, "Connector_USB_GCT", "Atomic_Connector", "USB1",
        footprint_old="Connector_USB_GCT:USB_Micro-B", footprint_new="Atomic_Footprints:USB_Micro-B_USB1",
    )
    captured = {}

    def fake_build_plan(inventory, choices, ctx):
        captured["choices"] = choices
        return _plan_for(inventory, (part_a,))

    core = core_with(
        tmp_path, build_plan=fake_build_plan, check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {})
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._current_key == KEY_A)

    assert dialog._fp_move_radio.isChecked()
    assert dialog._fp_move_radio.text() == MOVE_FOOTPRINT_TEXT
    assert dialog._fp_official_radio.text() == OFFICIAL_FOOTPRINT_TEXT
    assert dialog._fp_name_edit.text() == "USB_Micro-B_USB1"

    dialog._fp_name_edit.setText("USB_Micro-B_renamed")
    dialog._fp_name_edit.textEdited.emit("USB_Micro-B_renamed")

    qtbot.waitUntil(lambda: captured.get("choices") is not None and KEY_A in captured["choices"].parts)
    assert captured["choices"].parts[KEY_A].footprint_name == "USB_Micro-B_renamed"
