"""The migration window: refusal, grouped parts, detail pane, strip and Run gating (Phase 13 Plan 14).

Every test uses a fake MigrationCore (dataclasses.replace) with small hand-built Inventory /
MigrationPlan / GateOutcome values; the live Custom/ is never read.
"""

import threading
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from kicad_lib_manager.importer.migration.gate import GateOutcome, StripLine
from kicad_lib_manager.importer.migration.inventory import Inventory
from kicad_lib_manager.importer.migration.plan import MigrationPlan, PartPlan
from kicad_lib_manager.importer.migration.precheck import Precheck
from kicad_lib_manager.importer.plan import PartText, ToolContext
from kicad_lib_manager.models import Issue, Severity
from kicad_lib_manager.widgets.migration_dialog import (
    MigrationCore,
    MigrationDialog,
    PASS_MARK,
    UNDECIDED_GROUP,
    _REBUILD_DELAY_MS,
)

KEY_A = ("Custom/Symbols/Connector_USB_GCT.kicad_sym", "USB1")
KEY_B = ("Custom/Symbols/Connector_USB_GCT.kicad_sym", "USB2")
KEY_C = ("Custom/Symbols/Foo.kicad_sym", "FOO1")


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


def _part(key, source_library, target_library, new_name, *, mpn=None, suggestion=None) -> PartPlan:
    return PartPlan(
        key=key,
        source_library=source_library,
        target_library=target_library,
        suggestion=suggestion,
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


def test_dirty_custom_shows_refusal(qtbot, make_dialog, tmp_path):
    calls = {"read_inventory": 0, "check_custom": 0}
    text = (
        "The migration cannot start: Custom has uncommitted changes. Commit or delete them first, "
        "then open the migration again:\nCustom/Symbols/Foo.kicad_sym\nCustom/Symbols/Bar.kicad_sym"
    )

    def fake_check_custom(custom_dir, repo_root):
        calls["check_custom"] += 1
        return Precheck(False, (Issue(Severity.ERROR, "migration.uncommitted", text),), None, None, "")

    def fake_read_inventory(layout):
        calls["read_inventory"] += 1
        return _empty_inventory(layout)

    core = core_with(tmp_path, check_custom=fake_check_custom, read_inventory=fake_read_inventory)
    dialog = make_dialog(core)

    qtbot.waitUntil(lambda: dialog._stack.currentWidget() is dialog._refusal_page)
    shown = dialog._refusal_text.toPlainText()
    assert "Custom/Symbols/Foo.kicad_sym" in shown
    assert "Custom/Symbols/Bar.kicad_sym" in shown
    assert calls["read_inventory"] == 0

    dialog._check_again_btn.click()
    qtbot.waitUntil(lambda: calls["check_custom"] == 2)


def test_parts_grouped_by_target(qtbot, make_dialog, tmp_path):
    part_a = _part(KEY_A, "Connector_USB_GCT", "Atomic_Connector", "USB1")
    part_b = _part(KEY_B, "Connector_USB_GCT", "Atomic_Connector", "USB2")
    part_c = _part(KEY_C, "Foo", "", "FOO1")
    gate = GateOutcome((StripLine(KEY_A, "USB1: no MPN", "mpn"),), {KEY_A: 1})

    core = core_with(
        tmp_path,
        build_plan=lambda inventory, choices, ctx: _plan_for(inventory, (part_a, part_b, part_c)),
        check_plan=lambda plan, inventory, kicad_fp_dir: gate,
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._tree.topLevelItemCount() == 2)

    group_names = [dialog._tree.topLevelItem(i).text(0) for i in range(2)]
    assert group_names == [UNDECIDED_GROUP, "Atomic_Connector"]

    undecided = dialog._tree.topLevelItem(0)
    assert undecided.childCount() == 1
    assert undecided.child(0).text(0) == "FOO1"

    connector = dialog._tree.topLevelItem(1)
    assert connector.childCount() == 2
    rows = {connector.child(j).text(0): connector.child(j).text(1) for j in range(2)}
    assert "1 problem" in rows["USB1"]
    assert "from Connector_USB_GCT" in rows["USB1"]
    assert rows["USB2"].startswith(PASS_MARK)
    assert "from Connector_USB_GCT" in rows["USB2"]


def test_run_disabled_until_strip_empty(qtbot, make_dialog, tmp_path):
    part_a = _part(KEY_A, "Lib", "Atomic_Connector", "P1")
    gate_blocked = GateOutcome((StripLine(KEY_A, "P1: no MPN", "mpn"),), {KEY_A: 1})
    gate_clear = GateOutcome((), {})
    state = {"gate": gate_blocked}

    core = core_with(
        tmp_path,
        build_plan=lambda inventory, choices, ctx: _plan_for(inventory, (part_a,)),
        check_plan=lambda plan, inventory, kicad_fp_dir: state["gate"],
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._gate is not None)
    assert dialog._strip.count() == 1
    assert not dialog._run_btn.isEnabled()

    state["gate"] = gate_clear
    dialog._update_choice(KEY_A, mpn="NEWMPN")
    qtbot.waitUntil(lambda: dialog._run_btn.isEnabled(), timeout=_REBUILD_DELAY_MS + 5000)
    assert dialog._strip.count() == 0


def test_strip_click_selects_part_and_focuses_field(qtbot, make_dialog, tmp_path):
    part_a = _part(KEY_A, "Lib", "Atomic_Connector", "P1")
    part_b = _part(KEY_B, "Lib", "Atomic_Connector", "P2")
    gate = GateOutcome(
        (
            StripLine(KEY_A, "P1: no datasheet", "datasheet"),
            StripLine(KEY_B, "Choose a library for P2", "library"),
        ),
        {KEY_A: 1, KEY_B: 1},
    )
    core = core_with(
        tmp_path,
        build_plan=lambda inventory, choices, ctx: _plan_for(inventory, (part_a, part_b)),
        check_plan=lambda plan, inventory, kicad_fp_dir: gate,
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._strip.count() == 2)

    dialog._on_strip_item_clicked(dialog._strip.item(0))
    assert dialog._current_key == KEY_A
    assert dialog.focusWidget() is dialog._field_edits["datasheet"]

    dialog._on_strip_item_clicked(dialog._strip.item(1))
    assert dialog._current_key == KEY_B
    assert dialog.focusWidget() is dialog._library_combo


def test_long_work_runs_off_the_gui_thread(qtbot, make_dialog, tmp_path):
    main = threading.get_ident()
    seen: dict[str, int] = {}

    def spy(name, fn):
        def wrapper(*args, **kwargs):
            seen[name] = threading.get_ident()
            return fn(*args, **kwargs)

        return wrapper

    part_a = _part(KEY_A, "Lib", "Atomic_Connector", "P1")

    core = core_with(
        tmp_path,
        check_custom=spy("check_custom", lambda custom_dir, repo_root: Precheck(True, (), "head", "main", "")),
        read_inventory=spy("read_inventory", lambda layout: _empty_inventory(layout)),
        prepare_context=spy("prepare_context", lambda inventory, tools, kicad_fp_dir, progress=None: "ctx"),
        build_plan=spy("build_plan", lambda inventory, choices, ctx: _plan_for(inventory, (part_a,))),
        check_plan=spy("check_plan", lambda plan, inventory, kicad_fp_dir: GateOutcome((), {})),
    )
    dialog = make_dialog(core)
    qtbot.waitUntil(lambda: dialog._run_btn.isEnabled())

    for name in ("check_custom", "read_inventory", "prepare_context", "build_plan", "check_plan"):
        assert name in seen, f"{name} was never called"
        assert seen[name] != main, f"{name} ran on the GUI thread"
