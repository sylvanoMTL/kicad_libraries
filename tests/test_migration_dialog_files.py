"""The migration window, part 2: footprint/model/clash/derive controls and the Files tab (Phase 13 Plan 15).

Every test uses a fake MigrationCore (dataclasses.replace) with small hand-built Inventory /
MigrationPlan / GateOutcome values; the live Custom/ is never read. The fake_core fixture is
copied from tests/test_migration_dialog.py (tests do not import each other).
"""

import threading
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt

from kicad_lib_manager.importer.migration.inventory import Inventory
from kicad_lib_manager.importer.migration.gate import GateOutcome
from kicad_lib_manager.importer.migration.plan import (
    FamilyRow,
    LeftoverRow,
    MigrationOp,
    MigrationPlan,
    PartPlan,
)
from kicad_lib_manager.importer.migration.precheck import Precheck
from kicad_lib_manager.importer.plan import Conflict, PartText, Resolution, ToolContext
from kicad_lib_manager.models import Issue, Severity
import kicad_lib_manager.widgets.migration_dialog as migration_dialog_module
from kicad_lib_manager.widgets.migration_dialog import (
    ADD_MODEL_TEXT,
    DERIVE_TEXT,
    MigrationCore,
    MigrationDialog,
    MOVE_FOOTPRINT_TEXT,
    OFFICIAL_FOOTPRINT_TEXT,
    op_content,
    _REBUILD_DELAY_MS,
)

KEY_A = ("Custom/Symbols/Connector_USB_GCT.kicad_sym", "USB1")
KEY_B = ("Custom/Symbols/Connector_USB_GCT.kicad_sym", "USB2")


class _FakeSignal:
    """A no-op Signal stand-in for the fake ContentViewDialog used by the off-thread test."""

    def connect(self, *args, **kwargs):
        pass


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


# -- Task 3: the Files tab, every operation with its diff, and the leftover rows (D-10, D-15, D-21) --


def test_files_tab_sections(qtbot, make_dialog, tmp_path):
    ops = (
        MigrationOp(
            "write", tmp_path / "Custom/Symbols/Atomic_Connector.kicad_sym",
            "Custom/Symbols/Atomic_Connector.kicad_sym", data=b"sym", base_sha256=None,
        ),
        MigrationOp(
            "write", tmp_path / "Custom/3DModels/P1.step", "Custom/3DModels/P1.step",
            data=b"model-bytes", base_sha256=None, source_rel="Custom/3DModels/P1_old.step",
        ),
        MigrationOp(
            "delete", tmp_path / "Custom/3DModels/P1_old.step", "Custom/3DModels/P1_old.step", base_sha256="abc",
        ),
        MigrationOp(
            "delete", tmp_path / "Custom/Footprints/LibOld.pretty/FP1.kicad_mod.bak",
            "Custom/Footprints/LibOld.pretty/FP1.kicad_mod.bak", base_sha256="def",
        ),
        MigrationOp("rmdir", tmp_path / "Custom/Footprints/LibOld.pretty", "Custom/Footprints/LibOld.pretty"),
    )
    core = core_with(
        tmp_path,
        build_plan=lambda inventory, choices, ctx: _plan_for(inventory, ops=ops),
        check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {}),
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._plan is not None)

    sections = {section.name: section for section in dialog._files_tree.sections}
    assert set(sections) == {"Write", "Move or rename", "Delete", "Remove folder"}
    assert sections["Write"].title == "Write (1)"
    assert sections["Write"].rows[0].text == "Custom/Symbols/Atomic_Connector.kicad_sym"
    assert sections["Move or rename"].title == "Move or rename (1)"
    assert sections["Move or rename"].rows[0].text == "Custom/3DModels/P1_old.step → Custom/3DModels/P1.step"
    assert sections["Delete"].title == "Delete (1)"
    assert sections["Delete"].rows[0].text == "Custom/Footprints/LibOld.pretty/FP1.kicad_mod.bak"
    assert sections["Remove folder"].title == "Remove folder (1)"
    assert sections["Remove folder"].rows[0].text == "Custom/Footprints/LibOld.pretty"


def test_file_row_opens_diff_off_thread(qtbot, make_dialog, tmp_path, monkeypatch):
    lib_path = tmp_path / "Custom/Symbols/Atomic_Connector.kicad_sym"
    lib_path.parent.mkdir(parents=True, exist_ok=True)
    lib_path.write_text("old content\n")

    op = MigrationOp(
        "write", lib_path, "Custom/Symbols/Atomic_Connector.kicad_sym", data=b"new content\n", base_sha256="deadbeef",
    )
    main_thread = threading.get_ident()
    seen_thread = {}
    recorded = {}

    def spy_op_content(op_, repo_root):
        seen_thread["thread"] = threading.get_ident()
        return op_content(op_, repo_root)

    class FakeContentViewDialog:
        def __init__(self, content, parent=None):
            recorded["content"] = content
            self.finished = _FakeSignal()

        def open(self):
            recorded["opened"] = True

    monkeypatch.setattr(migration_dialog_module, "ContentViewDialog", FakeContentViewDialog)

    core = core_with(
        tmp_path,
        build_plan=lambda inventory, choices, ctx: _plan_for(inventory, ops=(op,)),
        check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {}),
        op_content=spy_op_content,
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._plan is not None)

    row = dialog._files_tree.sections[0].rows[0]
    dialog._on_file_row(row)
    qtbot.waitUntil(lambda: "content" in recorded)

    assert seen_thread["thread"] != main_thread
    assert recorded["content"].kind == "diff"
    assert "+new content" in recorded["content"].body
    assert "-old content" in recorded["content"].body
    assert recorded.get("opened") is True


def test_op_content_kinds(tmp_path, monkeypatch):
    repo_root = tmp_path

    new_text_op = MigrationOp(
        "write", repo_root / "Custom/Symbols/New.kicad_sym", "Custom/Symbols/New.kicad_sym",
        data=b"(kicad_symbol_lib)\n", base_sha256=None,
    )
    content = op_content(new_text_op, repo_root)
    assert content.kind == "text"
    assert "(kicad_symbol_lib)" in content.body

    existing = repo_root / "Custom/Footprints/Old.pretty/FP.kicad_mod"
    existing.parent.mkdir(parents=True, exist_ok=True)
    existing.write_text("old fp\n")
    delete_op = MigrationOp("delete", existing, "Custom/Footprints/Old.pretty/FP.kicad_mod", base_sha256="x")
    content = op_content(delete_op, repo_root)
    assert content.kind == "text"
    assert content.body.startswith("Deleted by the migration.")

    model_path = repo_root / "Custom/3DModels/P1.step"
    model_op = MigrationOp("write", model_path, "Custom/3DModels/P1.step", data=b"STEP-DATA", base_sha256=None)
    content = op_content(model_op, repo_root)
    assert content.kind == "binary"
    assert "SHA-256" in content.body

    rmdir_path = repo_root / "Custom/Footprints/Old.pretty"
    rmdir_op = MigrationOp("rmdir", rmdir_path, "Custom/Footprints/Old.pretty")
    content = op_content(rmdir_op, repo_root)
    assert content.kind == "text"
    assert content.body == "Folder removed."

    # reads are capped by MAX_READ: a delete whose current content exceeds the cap never crashes
    monkeypatch.setattr(migration_dialog_module, "MAX_READ", 4)
    big = repo_root / "Custom/Footprints/Old.pretty/Big.kicad_mod"
    big.write_text("this file is definitely longer than four bytes")
    capped_op = MigrationOp("delete", big, "Custom/Footprints/Old.pretty/Big.kicad_mod", base_sha256="y")
    content = migration_dialog_module.op_content(capped_op, repo_root)
    assert content.kind == "text"
    assert content.body.startswith("Deleted by the migration.")


def test_leftover_untick_keeps_file(qtbot, make_dialog, tmp_path):
    orphan = LeftoverRow(
        rel="Custom/Footprints/Old.pretty/FP1.kicad_mod", kind="footprint",
        keep=False, default_keep=False, reason="no part links it after the switch",
    )
    board_feature = LeftoverRow(
        rel="Custom/Footprints/Old.pretty/FP2.kicad_mod", kind="footprint",
        keep=True, default_keep=True, reason="no part links it",
    )
    captured = {}

    def fake_build_plan(inventory, choices, ctx):
        captured["choices"] = choices
        keep_a = choices.leftovers.get(orphan.rel, orphan.default_keep)
        ops = () if keep_a else (
            MigrationOp("delete", tmp_path / orphan.rel, orphan.rel, base_sha256="x"),
        )
        rows = (replace(orphan, keep=keep_a), board_feature)
        return _plan_for(inventory, ops=ops, leftovers=rows)

    core = core_with(
        tmp_path, build_plan=fake_build_plan, check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {})
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._plan is not None)

    items = {
        dialog._leftovers_list.item(i).data(Qt.ItemDataRole.UserRole): dialog._leftovers_list.item(i)
        for i in range(dialog._leftovers_list.count())
    }
    assert items[orphan.rel].checkState() == Qt.CheckState.Checked
    assert items[board_feature.rel].checkState() == Qt.CheckState.Unchecked
    assert any(op.rel == orphan.rel for op in dialog._plan.ops)

    items[orphan.rel].setCheckState(Qt.CheckState.Unchecked)
    qtbot.waitUntil(
        lambda: captured.get("choices") is not None and captured["choices"].leftovers.get(orphan.rel) is True
    )
    qtbot.waitUntil(lambda: not any(op.rel == orphan.rel for op in dialog._plan.ops))
