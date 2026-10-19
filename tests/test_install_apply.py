"""apply_plan as a transaction: preconditions, the kicad-cli load gate, backups, rollback and the fault matrix (Phase 4, plan 07).

Plans come from build_plan over the custom_copy / ul_package fixtures (a tmp_path copy of Custom/),
or are built by hand over a synthetic Custom/ tree. Nothing here writes the real Custom/ folder or
the owner's app-data backup folder: every install gets backup_root under tmp_path.
"""

import dataclasses
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fakecli import FakeCli
from installfixtures import V6_VERSION, target_lib, vendor_footprint, vendor_symbol_lib
from zipfixtures import STEP_BYTES, write_custom_layout

from kicad_lib_manager.importer import applier
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, FileOp, InstallOptions, InstallPlan, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.models import Issue, Severity

UL_LIBRARY = "IC_Battery_Charger_TI"
LIB = "IC_Test_TI"
EXE = Path("kicad-cli-for-tests.exe")


def _codes(issues) -> list[str]:
    return [i.code for i in issues]


def _errors(issues) -> list[Issue]:
    return [i for i in issues if i.severity is Severity.ERROR]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _with_cli(plan: InstallPlan, fake: FakeCli) -> InstallPlan:
    """The same plan with a scripted kicad-cli attached after it was built."""
    return dataclasses.replace(plan, tools=ToolContext(kicad_cli=EXE, cli_runner=fake))


def _ul_plan(custom_copy, ul_package) -> InstallPlan:
    _, candidate = ul_package
    plan = build_plan(candidate, InstallOptions(library=UL_LIBRARY), custom_copy)
    assert not plan.blocked, plan.issues
    return plan


def _hand_plan(layout: RepoLayout, *, new_library: bool, **fields) -> InstallPlan:
    """A consistent plan that installs PART/FP/X.stp into LIB and passes verify_install.

    new_library True: mkdir, model, footprint, symbol_lib with no base. False: the same
    files into an existing pair, the symbol library carrying the hash of what is on disk.
    """
    sym = vendor_symbol_lib("PART", footprint_field=f"{LIB}:FP")
    footprint = vendor_footprint("FP", model=f"{MODEL_DIR_VAR}/X.stp")
    sym_path = layout.symbols_dir / f"{LIB}.kicad_sym"
    pretty = layout.footprints_dir / f"{LIB}.pretty"
    ops: list[FileOp] = []
    base = None
    if new_library:
        ops.append(FileOp("mkdir", pretty))
    else:
        existing = target_lib(V6_VERSION, ("EXISTING_A",))
        sym_path.write_bytes(existing)
        pretty.mkdir()
        base = _sha(existing)
    ops.append(FileOp("model", layout.models_dir / "X.stp", data=STEP_BYTES))
    ops.append(FileOp("footprint", pretty / "FP.kicad_mod", data=footprint))
    ops.append(FileOp("symbol_lib", sym_path, data=sym, base_sha256=base))
    values = dict(
        vendor="Ultra Librarian",
        source=layout.repo_root / "pkg.zip",
        layout=layout,
        tools=ToolContext(),
        library=LIB,
        new_symbol_lib=new_library,
        new_footprint_lib=new_library,
        symbol_names=("PART",),
        footprint_names=("FP",),
        linked_footprint="FP",
        model_file="X.stp",
        source_version=V6_VERSION,
        target_version=V6_VERSION,
        normalised=False,
        ops=tuple(ops),
        conflicts=(),
        renames=(),
        issues=(),
    )
    values.update(fields)
    return InstallPlan(**values)


@pytest.fixture
def hand_layout(tmp_path) -> RepoLayout:
    write_custom_layout(tmp_path, [], [])
    return RepoLayout.for_repo(tmp_path)


# -- D-03 load gate at apply time ---------------------------------------------------------


def test_gate_rejects_before_any_write(custom_copy, ul_package, tmp_path, snapshot):
    plan = _with_cli(_ul_plan(custom_copy, ul_package), FakeCli({"sym upgrade": "reject"}))
    before = snapshot(custom_copy.custom_dir)

    result = apply_plan(plan, backup_root=tmp_path / "bk")

    assert not result.ok
    assert "install.cli_gate_failed" in _codes(_errors(result.issues))
    assert snapshot(custom_copy.custom_dir) == before
    assert not (tmp_path / "bk").exists()
    assert result.backup_dir is None


def test_gate_runs_on_planned_bytes(custom_copy, ul_package, tmp_path):
    plan = _ul_plan(custom_copy, ul_package)
    fake = FakeCli()
    result = apply_plan(_with_cli(plan, fake), backup_root=tmp_path / "bk")

    assert result.ok, result.issues
    assert [c[1:3] for c in fake.calls] == [["sym", "upgrade"], ["fp", "upgrade"]]
    symbol_op = next(op for op in plan.ops if op.kind == "symbol_lib")
    footprint_op = next(op for op in plan.ops if op.kind == "footprint")
    assert fake.inputs[0] == {f"{UL_LIBRARY}.kicad_sym": symbol_op.data}
    assert fake.inputs[1] == {footprint_op.path.name: footprint_op.data}


def test_gate_blames_merge_or_target_with_the_original_bytes(custom_copy, ul_package, tmp_path):
    plan = _ul_plan(custom_copy, ul_package)
    fake = FakeCli({"sym upgrade": ["reject", "upgrade"]})

    issues = applier.run_load_gate(_with_cli(plan, fake))

    (issue,) = _errors(issues)
    assert issue.code == "install.cli_gate_failed"
    assert "the merged part is the cause" in issue.text
    original = plan.symbol_lib_path.read_bytes()
    assert fake.inputs[1] == {f"{UL_LIBRARY}.kicad_sym": original}


def test_gate_standalone_writes_nothing(custom_copy, ul_package, tmp_path, snapshot):
    plan = _ul_plan(custom_copy, ul_package)
    before = snapshot(custom_copy.custom_dir)

    assert applier.run_load_gate(_with_cli(plan, FakeCli())) == []
    assert _errors(applier.run_load_gate(_with_cli(plan, FakeCli({"fp upgrade": "reject"}))))
    assert snapshot(custom_copy.custom_dir) == before


def test_gate_skipped_without_cli(custom_copy, ul_package, tmp_path):
    plan = _ul_plan(custom_copy, ul_package)
    assert plan.tools.kicad_cli is None

    result = apply_plan(plan, backup_root=tmp_path / "bk")

    assert result.ok, result.issues
    assert _codes(result.issues).count("install.cli_not_found") == 1
    assert _codes(result.issues)[-1] == "install.done"


def test_gate_cli_note_emitted_once_when_the_planner_already_added_it(hand_layout):
    note = Issue(Severity.INFO, "install.cli_not_found", "kicad-cli was not found")
    plan = _hand_plan(hand_layout, new_library=True, issues=(note,))

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")

    assert result.ok, result.issues
    assert _codes(result.issues).count("install.cli_not_found") == 1


def test_gate_not_run_for_a_model_only_plan(hand_layout):
    fake = FakeCli()
    plan = _hand_plan(hand_layout, new_library=True)
    model_only = dataclasses.replace(
        plan, ops=tuple(op for op in plan.ops if op.kind == "model"), tools=ToolContext(kicad_cli=EXE, cli_runner=fake)
    )

    assert applier.run_load_gate(model_only) == []
    assert fake.calls == []


# -- stale plan (T-04-18) -----------------------------------------------------------------


def test_stale_plan_target_changed(custom_copy, ul_package, tmp_path, snapshot):
    plan = _ul_plan(custom_copy, ul_package)
    plan.symbol_lib_path.write_bytes(plan.symbol_lib_path.read_bytes() + b"\n")
    before = snapshot(custom_copy.custom_dir)

    result = apply_plan(plan, backup_root=tmp_path / "bk")

    assert not result.ok
    stale = [i for i in _errors(result.issues) if i.code == "install.stale_plan"]
    assert stale and plan.symbol_lib_path.name in stale[0].text and "rebuild" in stale[0].text
    assert snapshot(custom_copy.custom_dir) == before
    assert not (tmp_path / "bk").exists()


@pytest.mark.parametrize("name", ["DQK0006B.kicad_mod", "dqk0006b.KICAD_MOD"])
def test_stale_plan_created_path_exists(custom_copy, ul_package, tmp_path, snapshot, name):
    plan = _ul_plan(custom_copy, ul_package)
    (plan.pretty_path / name).write_bytes(b"(footprint)")
    before = snapshot(custom_copy.custom_dir)

    result = apply_plan(plan, backup_root=tmp_path / "bk")

    assert not result.ok
    assert "install.stale_plan" in _codes(_errors(result.issues))
    assert snapshot(custom_copy.custom_dir) == before


def test_stale_plan_new_library_folder_appeared(hand_layout):
    plan = _hand_plan(hand_layout, new_library=True)
    (hand_layout.footprints_dir / f"{LIB}.pretty").mkdir()

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")

    assert not result.ok
    assert "install.stale_plan" in _codes(_errors(result.issues))
    assert not (hand_layout.models_dir / "X.stp").exists()


def test_stale_plan_target_deleted(hand_layout):
    plan = _hand_plan(hand_layout, new_library=False)
    plan.symbol_lib_path.unlink()

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")

    assert not result.ok
    assert "install.stale_plan" in _codes(_errors(result.issues))


# -- the staged source (WR-04) -----------------------------------------------------------


def test_source_changed_at_apply(custom_copy, ul_package, tmp_path, snapshot):
    _, candidate = ul_package
    plan = _ul_plan(custom_copy, ul_package)
    model = candidate.models[0].file.path
    original = model.read_bytes()
    model.write_bytes(original + b" ")
    before = snapshot(custom_copy.custom_dir)
    try:
        result = apply_plan(plan, backup_root=tmp_path / "bk")
    finally:
        model.write_bytes(original)

    assert not result.ok
    assert "install.source_changed" in _codes(_errors(result.issues))
    assert snapshot(custom_copy.custom_dir) == before
    assert not (tmp_path / "bk").exists()


def test_source_gone_at_apply(custom_copy, ul_package, tmp_path, snapshot):
    _, candidate = ul_package
    plan = _ul_plan(custom_copy, ul_package)
    model = candidate.models[0].file.path
    original = model.read_bytes()
    model.unlink()
    before = snapshot(custom_copy.custom_dir)
    try:
        result = apply_plan(plan, backup_root=tmp_path / "bk")
    finally:
        model.write_bytes(original)

    assert not result.ok
    assert "install.source_gone" in _codes(_errors(result.issues))
    assert snapshot(custom_copy.custom_dir) == before


# -- containment (T-04-19) ---------------------------------------------------------------


def test_path_outside_custom(hand_layout, tmp_path):
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    plan = _hand_plan(hand_layout, new_library=True)
    escaped = dataclasses.replace(plan, ops=(*plan.ops, FileOp("model", outside / "X.stp", data=STEP_BYTES)))

    result = apply_plan(escaped, backup_root=tmp_path / "bk")

    assert not result.ok
    assert "install.path_outside_custom" in _codes(_errors(result.issues))
    assert list(outside.iterdir()) == []
    assert not (hand_layout.footprints_dir / f"{LIB}.pretty").exists()
    assert not (tmp_path / "bk").exists()


def test_path_outside_custom_through_a_link(hand_layout, tmp_path):
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    link = hand_layout.custom_dir / "3DModels" / "linked"
    try:
        os.symlink(outside, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        # Windows without developer mode: a junction needs no privilege
        made = sys.platform == "win32" and subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True
        ).returncode == 0
        if not made:
            pytest.skip("directory links are not available here")
    plan = _hand_plan(hand_layout, new_library=True)
    escaped = dataclasses.replace(plan, ops=(FileOp("model", link / "X.stp", data=STEP_BYTES),))

    result = apply_plan(escaped, backup_root=tmp_path / "bk")

    assert not result.ok
    assert "install.path_outside_custom" in _codes(_errors(result.issues))
    assert list(outside.iterdir()) == []


# -- empty plan (INST-07 edge) -----------------------------------------------------------


def test_noop_plan_writes_nothing_and_runs_no_gate(hand_layout, snapshot):
    fake = FakeCli()
    plan = dataclasses.replace(_hand_plan(hand_layout, new_library=True), ops=(), tools=ToolContext(kicad_cli=EXE, cli_runner=fake))
    before = snapshot(hand_layout.custom_dir)

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")

    assert result.ok and result.touched == ()
    assert "install.nothing_to_do" in _codes(result.issues)
    assert result.backup_dir is None
    assert fake.calls == []
    assert snapshot(hand_layout.custom_dir) == before
    assert not (hand_layout.repo_root / "bk").exists()


def test_blocked_plan_is_refused_before_noop(hand_layout):
    boom = Issue(Severity.ERROR, "install.no_symbol", "nothing to install")
    plan = dataclasses.replace(_hand_plan(hand_layout, new_library=True), ops=(), issues=(boom,))

    result = apply_plan(plan)

    assert not result.ok and "install.nothing_to_do" not in _codes(result.issues)

