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
from kicad_lib_manager.importer.migration.plan import (
    FamilyRow,
    MigrationOp,
    MigrationPlan,
    PartPlan,
)
from kicad_lib_manager.importer.migration.precheck import Precheck
from kicad_lib_manager.importer.plan import Conflict, PartText, Resolution, ToolContext
from kicad_lib_manager.models import Issue, Severity
from kicad_lib_manager.widgets.migration_dialog import (
    ADD_MODEL_TEXT,
    DERIVE_TEXT,
    MigrationCore,
    MigrationDialog,
    MOVE_FOOTPRINT_TEXT,
    OFFICIAL_FOOTPRINT_TEXT,
    _REBUILD_DELAY_MS,
)

KEY_A = ("Custom/Symbols/Connector_USB_GCT.kicad_sym", "USB1")
KEY_B = ("Custom/Symbols/Connector_USB_GCT.kicad_sym", "USB2")


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


def _plan_for(inventory, parts=(), ops=(), conflicts=(), families=(), leftovers=()) -> MigrationPlan:
    return MigrationPlan(
        layout=inventory.layout,
        parts=tuple(parts),
        ops=tuple(ops),
        library_map=(),
        symbol_renames=(),
        footprint_links=(),
        model_renames=(),
        leftovers=tuple(leftovers),
        families=tuple(families),
        conflicts=tuple(conflicts),
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


# -- Task 2: model row, Add 3D model, clash rows and the derive box (D-06, D-07, D-09) -----------


def test_model_row_lists_files_and_renames(qtbot, make_dialog, tmp_path):
    part_a = _part(KEY_A, "Lib", "Atomic_Connector", "P1", model_files=("P1.step",))
    part_b = _part(KEY_B, "Lib", "Atomic_Connector", "P2", model_files=("P2_a.step", "P2_b.step"))
    captured = {}

    def fake_build_plan(inventory, choices, ctx):
        captured["choices"] = choices
        return _plan_for(inventory, (part_a, part_b))

    core = core_with(
        tmp_path, build_plan=fake_build_plan, check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {})
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._current_key == KEY_A)

    assert dialog._model_name_edit.text() == "P1.step"
    dialog._model_name_edit.setText("P1_renamed.step")
    dialog._model_name_edit.textEdited.emit("P1_renamed.step")
    qtbot.waitUntil(lambda: captured.get("choices") is not None and KEY_A in captured["choices"].parts)
    assert captured["choices"].parts[KEY_A].model_name == "P1_renamed.step"

    dialog._select_part(KEY_B)
    qtbot.waitUntil(lambda: dialog._current_key == KEY_B)
    items = [dialog._model_list.item(i).text() for i in range(dialog._model_list.count())]
    assert items == ["P2_a.step", "P2_b.step"]


def test_add_model_sets_source(qtbot, make_dialog, tmp_path):
    part_a = _part(KEY_A, "Lib", "Atomic_Connector", "P1", model_files=())
    captured = {}

    def fake_build_plan(inventory, choices, ctx):
        captured["choices"] = choices
        return _plan_for(inventory, (part_a,))

    core = core_with(
        tmp_path,
        build_plan=fake_build_plan,
        check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {}),
        pick_model_file=lambda parent: str(tmp_path / "picked.step"),
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._current_key == KEY_A)

    assert dialog._add_model_btn.text() == ADD_MODEL_TEXT
    dialog._add_model_btn.click()
    qtbot.waitUntil(
        lambda: captured.get("choices") is not None
        and captured["choices"].parts.get(KEY_A) is not None
        and captured["choices"].parts[KEY_A].model_source == str(tmp_path / "picked.step")
    )

    captured.clear()
    dialog._remove_model_btn.click()
    qtbot.waitUntil(
        lambda: captured.get("choices") is not None and captured["choices"].parts[KEY_A].model_source is None
    )


def test_clash_row_resolution_reaches_plan(qtbot, make_dialog, tmp_path):
    part_a = _part(
        KEY_A, "Lib", "Atomic_Connector", "P1",
        footprint_old="Lib:FP1", footprint_new="Atomic_Footprints:FP1",
    )
    conflict = Conflict(
        key="footprint:FP1", kind="footprint", name="FP1",
        existing="Atomic_Footprints already holds FP1.kicad_mod with different content",
        suggested_name="FP1_P1",
    )
    captured = {}

    def fake_build_plan(inventory, choices, ctx):
        captured["choices"] = choices
        return _plan_for(inventory, (part_a,), conflicts=(conflict,))

    core = core_with(
        tmp_path, build_plan=fake_build_plan, check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {})
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._current_key == KEY_A)

    row = dialog._conflict_rows["footprint:FP1"]
    assert row.rename_edit.text() == "FP1_P1"

    row.overwrite_button.click()
    qtbot.waitUntil(
        lambda: captured.get("choices") is not None
        and captured["choices"].resolutions.get("footprint:FP1") is not None
        and captured["choices"].resolutions["footprint:FP1"].action == "overwrite"
    )

    strip_target = dialog._targets.get("conflict:footprint:FP1")
    assert strip_target is row.overwrite_button


def test_derive_box(qtbot, make_dialog, tmp_path):
    part_a = _part(KEY_A, "Lib", "Atomic_Connector", "P1")
    part_b = _part(KEY_B, "Lib", "Atomic_Connector", "P2")
    family = FamilyRow(parent=KEY_A, member=KEY_B, derive=True)
    captured = {}

    def fake_build_plan(inventory, choices, ctx):
        captured["choices"] = choices
        return _plan_for(inventory, (part_a, part_b), families=(family,))

    core = core_with(
        tmp_path, build_plan=fake_build_plan, check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {})
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._current_key == KEY_A)
    assert dialog._derive_check.isHidden()

    dialog._select_part(KEY_B)
    qtbot.waitUntil(lambda: dialog._current_key == KEY_B)
    assert not dialog._derive_check.isHidden()
    assert dialog._derive_check.text() == DERIVE_TEXT.format(parent="P1")
    assert dialog._derive_check.isChecked()

    dialog._derive_check.setChecked(False)
    dialog._derive_check.toggled.emit(False)
    qtbot.waitUntil(
        lambda: captured.get("choices") is not None and captured["choices"].parts.get(KEY_B) is not None
        and captured["choices"].parts[KEY_B].derive is False
    )
