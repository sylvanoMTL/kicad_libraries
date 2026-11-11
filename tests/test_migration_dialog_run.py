"""The migration window, part 3: Run, the failure and Result views, and the commit step (Phase 13 Plan 16).

Every test uses a fake MigrationCore (dataclasses.replace) with small hand-built Inventory /
MigrationPlan / GateOutcome / MigrationResult values; the live Custom/ is never read, and no test
ever opens a real modal dialog or a real git repository.
"""

from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from kicad_lib_manager.importer.migration.applier import MigrationResult
from kicad_lib_manager.importer.migration.gate import GateOutcome
from kicad_lib_manager.importer.migration.inventory import Inventory
from kicad_lib_manager.importer.migration.plan import MigrationPlan, PartPlan
from kicad_lib_manager.importer.migration.precheck import Precheck
from kicad_lib_manager.importer.plan import PartText, ToolContext
from kicad_lib_manager.kicad_setup import CheckoutMismatch, wrong_checkout_refusal
from kicad_lib_manager.library_scanner import ConfirmAnswer
from kicad_lib_manager.models import Issue, Severity
from kicad_lib_manager.widgets.migration_dialog import (
    MigrationCore,
    MigrationDialog,
    RUN_REFUSAL_ACTION,
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


def _part(key, source_library, target_library, new_name, *, mpn=None) -> PartPlan:
    return PartPlan(
        key=key,
        source_library=source_library,
        target_library=target_library,
        suggestion=None,
        old_name=key[1],
        new_name=new_name,
        mpn=mpn or new_name,
        parent=None,
        footprint_old="",
        footprint_new="",
        footprint_target="shared",
        model_files=(),
        field_changes=(),
        generated_text=PartText(),
        part_text=PartText(),
        issues=(),
    )


def _plan_for(inventory, parts=()) -> MigrationPlan:
    return MigrationPlan(
        layout=inventory.layout,
        parts=tuple(parts),
        ops=(),
        library_map=(),
        symbol_renames=(),
        footprint_links=(),
        model_renames=(),
        leftovers=(),
        families=(),
        conflicts=(),
        removed_libraries=(),
        bak_files=(),
        map_text="Old -> New\nFoo -> Atomic_Connector\n",
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
        "checkout_mismatch": lambda repo_root: None,
        "kicad_running": lambda: [],
        "ask_kicad_open": lambda parent, names: ConfirmAnswer.DECLINE,
        "ensure_tag": lambda custom_dir, repo_root: [],
        "apply": lambda plan, **kw: MigrationResult(True, (), (), (), None, plan, {}),
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


# -- Task 1: Run itself -------------------------------------------------------------------------


def test_run_applies_on_a_worker_with_tag_first(qtbot, make_dialog, tmp_path):
    import threading

    part_a = _part(KEY_A, "Lib", "Atomic_Connector", "P1")
    calls = {"ensure_tag": 0, "apply": 0}
    gate = threading.Event()

    def fake_ensure_tag(custom_dir, repo_root):
        calls["ensure_tag"] += 1
        return [Issue(Severity.INFO, "migration.tagged", "Tagged Custom as pre-atomic at abc1234")]

    def fake_apply(plan, *, backup_root=None, progress=None, before_first_write=None, tools=None):
        calls["apply"] += 1
        pre_issues = before_first_write() if before_first_write is not None else []
        assert any(i.code == "migration.tagged" for i in pre_issues)
        if progress is not None:
            progress("Writing files...", 1, 2)
        gate.wait(5)  # held open so the test can observe the running page before it completes
        return MigrationResult(True, tuple(pre_issues), ("x",), (), None, plan, {})

    core = core_with(
        tmp_path,
        build_plan=lambda inventory, choices, ctx: _plan_for(inventory, (part_a,)),
        check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {}),
        ensure_tag=fake_ensure_tag,
        apply=fake_apply,
    )
    dialog = make_dialog(core)
    dialog.show()
    qtbot.waitUntil(lambda: dialog._run_btn.isEnabled())

    dialog._run_btn.click()
    qtbot.waitUntil(lambda: dialog._stack.currentWidget() is dialog._running_page)
    assert dialog.is_running()
    qtbot.waitUntil(lambda: dialog._running_label.text() == "Writing files...")

    dialog.close()
    assert dialog.isVisible()  # a close attempt is ignored while Run is active

    gate.set()
    qtbot.waitUntil(lambda: calls["apply"] == 1 and not dialog.is_running())
    assert calls["ensure_tag"] == 1


def test_wrong_checkout_refuses_run(qtbot, make_dialog, tmp_path):
    part_a = _part(KEY_A, "Lib", "Atomic_Connector", "P1")
    mismatch = CheckoutMismatch("C:/Git_Repo_Clones/Kicad_Libraries-importer", "C:/Git_Repo_Clones/Kicad_Libraries")
    calls = {"kicad_running": 0, "ensure_tag": 0, "apply": 0}

    def fake_kicad_running():
        calls["kicad_running"] += 1
        return []

    def fake_ensure_tag(custom_dir, repo_root):
        calls["ensure_tag"] += 1
        return []

    def fake_apply(plan, **kw):
        calls["apply"] += 1
        return MigrationResult(True, (), (), (), None, plan, {})

    core = core_with(
        tmp_path,
        build_plan=lambda inventory, choices, ctx: _plan_for(inventory, (part_a,)),
        check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {}),
        checkout_mismatch=lambda repo_root: mismatch,
        kicad_running=fake_kicad_running,
        ensure_tag=fake_ensure_tag,
        apply=fake_apply,
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._run_btn.isEnabled())

    dialog._run_btn.click()
    qtbot.waitUntil(lambda: not dialog._run_failure_banner.isHidden())
    text = dialog._run_failure_body.toPlainText()
    assert wrong_checkout_refusal(mismatch, RUN_REFUSAL_ACTION) in text
    assert "Running it here would rewrite a copy KiCad does not read." in text

    qtbot.wait(50)
    assert calls["kicad_running"] == 0
    assert calls["ensure_tag"] == 0
    assert calls["apply"] == 0
    assert dialog._stack.currentWidget() is dialog._edit_page
    assert dialog._run_btn.isEnabled()
    assert not dialog.is_running()

    # None (no mismatch) runs normally: a second dialog with checkout_mismatch returning None
    apply_calls = []
    core2 = core_with(
        tmp_path,
        build_plan=lambda inventory, choices, ctx: _plan_for(inventory, (part_a,)),
        check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {}),
        checkout_mismatch=lambda repo_root: None,
        apply=lambda plan, **kw: apply_calls.append(1) or MigrationResult(True, (), (), (), None, plan, {}),
    )
    dialog2 = make_dialog(core2)
    qtbot.waitUntil(lambda: dialog2._run_btn.isEnabled())
    dialog2._run_btn.click()
    qtbot.waitUntil(lambda: len(apply_calls) == 1)


def test_kicad_open_asks_before_run(qtbot, make_dialog, tmp_path):
    part_a = _part(KEY_A, "Lib", "Atomic_Connector", "P1")

    def plan_core(**overrides):
        return core_with(
            tmp_path,
            build_plan=lambda inventory, choices, ctx: _plan_for(inventory, (part_a,)),
            check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {}),
            ensure_tag=lambda custom_dir, repo_root: [],
            **overrides,
        )

    # -- Cancel: writes nothing --
    ask_calls: list = []
    apply_calls: list = []

    def ask_cancel(parent, names):
        ask_calls.append(list(names))
        return ConfirmAnswer.DECLINE

    core = plan_core(
        kicad_running=lambda: ["kicad"],
        ask_kicad_open=ask_cancel,
        apply=lambda plan, **kw: apply_calls.append(1) or MigrationResult(True, (), (), (), None, plan, {}),
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._run_btn.isEnabled())
    dialog._run_btn.click()
    qtbot.waitUntil(lambda: len(ask_calls) == 1)
    assert ask_calls[0] == ["kicad"]
    qtbot.wait(50)
    assert apply_calls == []
    assert not dialog.is_running()

    # -- Retry: checks again --
    running_calls = {"n": 0}
    ask_calls2: list = []
    apply_calls2: list = []

    def kicad_running_retry():
        running_calls["n"] += 1
        return ["kicad"] if running_calls["n"] == 1 else []

    def ask_retry(parent, names):
        ask_calls2.append(list(names))
        return ConfirmAnswer.RETRY

    core2 = plan_core(
        kicad_running=kicad_running_retry,
        ask_kicad_open=ask_retry,
        apply=lambda plan, **kw: apply_calls2.append(1) or MigrationResult(True, (), (), (), None, plan, {}),
    )
    dialog2 = make_dialog(core2)
    qtbot.waitUntil(lambda: dialog2._run_btn.isEnabled())
    dialog2._run_btn.click()
    qtbot.waitUntil(lambda: len(apply_calls2) == 1)
    assert running_calls["n"] == 2
    assert len(ask_calls2) == 1

    # -- Run anyway: applies --
    ask_calls3: list = []
    apply_calls3: list = []

    def ask_anyway(parent, names):
        ask_calls3.append(list(names))
        return ConfirmAnswer.WRITE

    core3 = plan_core(
        kicad_running=lambda: ["kicad"],
        ask_kicad_open=ask_anyway,
        apply=lambda plan, **kw: apply_calls3.append(1) or MigrationResult(True, (), (), (), None, plan, {}),
    )
    dialog3 = make_dialog(core3)
    qtbot.waitUntil(lambda: dialog3._run_btn.isEnabled())
    dialog3._run_btn.click()
    qtbot.waitUntil(lambda: len(apply_calls3) == 1)
    assert len(ask_calls3) == 1


def test_failed_run_shows_reasons_and_rebuilds(qtbot, make_dialog, tmp_path):
    part_a = _part(KEY_A, "Lib", "Atomic_Connector", "P1")
    load_calls = {"n": 0}

    def fake_read_inventory(layout):
        load_calls["n"] += 1
        return _empty_inventory(layout)

    issue1 = Issue(Severity.ERROR, "migration.outside_custom", "oops1 is outside Custom; nothing was written")
    issue2 = Issue(Severity.ERROR, "migration.outside_custom", "oops2 is outside Custom; nothing was written")
    rolled_back = Issue(Severity.INFO, "migration.rolled_back", "The migration failed; every change was undone.")

    def fake_apply(plan, **kw):
        return MigrationResult(False, (issue1, issue2, rolled_back), (), (), None, plan, {})

    core = core_with(
        tmp_path,
        read_inventory=fake_read_inventory,
        build_plan=lambda inventory, choices, ctx: _plan_for(inventory, (part_a,)),
        check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {}),
        apply=fake_apply,
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._run_btn.isEnabled())
    assert load_calls["n"] == 1

    dialog._run_btn.click()
    qtbot.waitUntil(lambda: not dialog._run_failure_banner.isHidden())
    text = dialog._run_failure_body.toPlainText()
    assert issue1.text in text
    assert issue2.text in text
    assert "Every file was restored." in text

    qtbot.waitUntil(lambda: dialog._stack.currentWidget() is dialog._edit_page)
    qtbot.waitUntil(lambda: load_calls["n"] == 2)

    # migration.rollback_incomplete: the banner names the backup folder
    backup_dir = tmp_path / "backup"
    incomplete = Issue(
        Severity.ERROR, "migration.rollback_incomplete",
        f"file.txt could not be restored (reason); see the backup folder at {backup_dir}",
    )

    def fake_apply2(plan, **kw):
        return MigrationResult(False, (issue1, incomplete), (), (), backup_dir, plan, {})

    core2 = core_with(
        tmp_path,
        build_plan=lambda inventory, choices, ctx: _plan_for(inventory, (part_a,)),
        check_plan=lambda plan, inventory, kicad_fp_dir: GateOutcome((), {}),
        apply=fake_apply2,
    )
    dialog2 = make_dialog(core2)
    qtbot.waitUntil(lambda: dialog2._run_btn.isEnabled())
    dialog2._run_btn.click()
    qtbot.waitUntil(lambda: not dialog2._run_failure_banner.isHidden())
    text2 = dialog2._run_failure_body.toPlainText()
    assert incomplete.text in text2
    assert str(backup_dir) in text2
