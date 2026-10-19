"""apply_plan as a transaction: preconditions, the kicad-cli load gate, backups, rollback and the fault matrix (Phase 4, plan 07).

Plans come from build_plan over the custom_copy / ul_package fixtures (a tmp_path copy of Custom/),
or are built by hand over a synthetic Custom/ tree. Nothing here writes the real Custom/ folder or
the owner's app-data backup folder: every install gets backup_root under tmp_path.
"""

import dataclasses
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fakecli import FakeCli
from installfixtures import V6_VERSION, target_lib, vendor_footprint, vendor_symbol_lib
from zipfixtures import STEP_BYTES, write_custom_layout

from kicad_lib_manager import fsutil
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
    _link_dir(link, outside)
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


# -- helpers for the transaction tests ---------------------------------------------------


def _flaky_writes(monkeypatch, fail_on: int) -> dict:
    """Make the fail_on-th forward atomic write return an Issue; later calls (the undo) are real."""
    real = fsutil.atomic_write_bytes
    state = {"calls": 0, "failed": False, "paths": []}

    def flaky(path, data, **kwargs):
        if not state["failed"]:
            state["calls"] += 1
            state["paths"].append(path)
            if state["calls"] == fail_on:
                state["failed"] = True
                return Issue(Severity.ERROR, "fs.write_failed", "injected")
        return real(path, data, **kwargs)

    monkeypatch.setattr(fsutil, "atomic_write_bytes", flaky)
    return state


def _stamp_folder(installs: Path, stamp: str, library: str = "IC_Old_TI") -> Path:
    folder = installs / f"{stamp}_{library}"
    folder.mkdir(parents=True)
    (folder / "x.kicad_sym_backup_1").write_bytes(b"old")
    return folder


def _link_dir(link: Path, target: Path) -> None:
    """Make link a directory link to target (symlink, or a junction on Windows); skip when neither works."""
    try:
        os.symlink(target, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        made = (
            sys.platform == "win32"
            and subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True).returncode == 0
        )
        if not made:
            pytest.skip("directory links are not available here")


# -- D-19 backups --------------------------------------------------------------------------


def test_backup_folder_named_and_contains_preimage(custom_copy, ul_package, tmp_path):
    plan = _ul_plan(custom_copy, ul_package)
    original = plan.symbol_lib_path.read_bytes()

    result = apply_plan(plan, backup_root=tmp_path / "bk")

    assert result.ok, result.issues
    assert result.backup_dir.parent == tmp_path / "bk" / "installs"
    assert re.fullmatch(rf"\d{{8}}-\d{{6}}(-\d+)?_{UL_LIBRARY}", result.backup_dir.name)
    assert (result.backup_dir / f"{UL_LIBRARY}.kicad_sym_backup_1").read_bytes() == original
    assert [p.name for p in result.backup_dir.iterdir()] == [f"{UL_LIBRARY}.kicad_sym_backup_1"]


def test_backup_not_created_for_create_only_plan(hand_layout):
    plan = _hand_plan(hand_layout, new_library=True)

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")

    assert result.ok, result.issues
    assert result.backup_dir is None
    assert not (hand_layout.repo_root / "bk").exists()


def test_backup_folder_name_gets_a_suffix_when_taken(hand_layout, monkeypatch):
    monkeypatch.setattr(applier.time, "strftime", lambda fmt, *a: "20260101-120000")
    installs = hand_layout.repo_root / "bk" / "installs"
    _stamp_folder(installs, "20260101-120000", LIB)
    _stamp_folder(installs, "20260101-120000-2", LIB)
    plan = _hand_plan(hand_layout, new_library=False)

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")

    assert result.ok, result.issues
    assert result.backup_dir.name == f"20260101-120000-3_{LIB}"


def test_prune_keeps_newest_ten(tmp_path):
    installs = tmp_path / "installs"
    for day in range(1, 13):
        _stamp_folder(installs, f"202601{day:02d}-101010")
    _stamp_folder(installs, "20260105-101010-2")
    (installs / "notes").mkdir()
    (installs / "20260101-000000_a_file").write_bytes(b"not a folder")

    issues = applier.prune_install_backups(installs)

    assert issues == []
    names = sorted(p.name for p in installs.iterdir())
    folders = [n for n in names if n[:2] == "20" and (installs / n).is_dir()]
    assert len(folders) == 10
    assert "20260101-101010_IC_Old_TI" not in names and "20260102-101010_IC_Old_TI" not in names
    # the suffixed folder of the same second is newer than the plain one
    assert "20260105-101010-2_IC_Old_TI" in names
    assert "notes" in names and "20260101-000000_a_file" in names


def test_prune_orders_suffixed_folders_after_plain_ones(tmp_path):
    installs = tmp_path / "installs"
    _stamp_folder(installs, "20260101-101010")
    _stamp_folder(installs, "20260101-101010-2")

    assert applier.prune_install_backups(installs, keep=1) == []

    assert [p.name for p in installs.iterdir()] == ["20260101-101010-2_IC_Old_TI"]


def test_prune_never_follows_a_link(tmp_path):
    installs = tmp_path / "installs"
    installs.mkdir()
    outside = tmp_path / "precious"
    outside.mkdir()
    (outside / "keep.txt").write_bytes(b"keep")
    _link_dir(installs / "20250101-000000_IC_Old_TI", outside)
    _stamp_folder(installs, "20260101-101010")

    applier.prune_install_backups(installs, keep=1)

    assert (outside / "keep.txt").read_bytes() == b"keep"


def test_prune_after_an_install_bounds_the_folder(hand_layout):
    installs = hand_layout.repo_root / "bk" / "installs"
    for day in range(1, 13):
        _stamp_folder(installs, f"202501{day:02d}-101010")
    plan = _hand_plan(hand_layout, new_library=False)

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")

    assert result.ok, result.issues
    folders = sorted(p.name for p in installs.iterdir())
    assert len(folders) == applier.INSTALL_BACKUPS_KEPT == 10
    assert result.backup_dir.name in folders
    assert "20250101-101010_IC_Old_TI" not in folders


def test_prune_failure_warns(hand_layout, monkeypatch):
    installs = hand_layout.repo_root / "bk" / "installs"
    for day in range(1, 13):
        _stamp_folder(installs, f"202501{day:02d}-101010")

    def refuse(path, *args, **kwargs):
        raise OSError(13, "in use")

    monkeypatch.setattr(applier.shutil, "rmtree", refuse)
    plan = _hand_plan(hand_layout, new_library=False)

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")

    assert result.ok, result.issues
    warnings = [i for i in result.issues if i.code == "install.backup_prune_failed"]
    assert warnings and all(w.severity is Severity.WARNING for w in warnings)


# -- verification results (cross-plan finding from 04-05) ------------------------------------


def test_success_keeps_the_soft_verify_warnings(hand_layout):
    # symbol pins are 1 and 2; the footprint has pad 3 as well
    fp = vendor_footprint("FP", pads=("1", "2", "3"), model=f"{MODEL_DIR_VAR}/X.stp")
    other = hand_layout.symbols_dir / "IC_Other_TI.kicad_sym"
    other.write_bytes(target_lib(V6_VERSION, ("PART",)))
    plan = _hand_plan(hand_layout, new_library=True)
    plan = dataclasses.replace(
        plan,
        ops=tuple(dataclasses.replace(op, data=fp) if op.kind == "footprint" else op for op in plan.ops),
    )

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")

    assert result.ok, result.issues
    codes = _codes(result.issues)
    assert "verify.pin_pad_mismatch" in codes and "verify.name_elsewhere" in codes
    assert codes[-1] == "install.done"
    assert all(i.severity is not Severity.ERROR for i in result.issues)


def test_progress_is_called_once_per_write(hand_layout):
    plan = _hand_plan(hand_layout, new_library=True)
    seen = []

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk", progress=lambda *a: seen.append(a))

    assert result.ok, result.issues
    assert seen == [(f"Writing {op.path.name}", n, len(plan.ops)) for n, op in enumerate(plan.ops)]


# -- D-18 folders and rollback -----------------------------------------------------------------


def test_mkdir_then_rollback_removes_folder(hand_layout, snapshot, monkeypatch):
    plan = _hand_plan(hand_layout, new_library=True)
    before = snapshot(hand_layout.custom_dir)
    _flaky_writes(monkeypatch, fail_on=3)  # model, footprint, then the symbol library fails

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")

    assert not result.ok
    assert _codes(_errors(result.issues)) == ["fs.write_failed", "install.rolled_back"]
    assert not (hand_layout.footprints_dir / f"{LIB}.pretty").exists()
    assert snapshot(hand_layout.custom_dir) == before


def test_mkdir_creates_missing_parents(tmp_path):
    write_custom_layout(tmp_path, [], [])
    layout = RepoLayout.for_repo(tmp_path)
    layout.footprints_dir.rmdir()
    plan = _hand_plan(layout, new_library=True)

    result = apply_plan(plan, backup_root=tmp_path / "bk")

    assert result.ok, result.issues
    assert (layout.footprints_dir / f"{LIB}.pretty" / "FP.kicad_mod").is_file()
    assert [p.name for p in result.touched] == ["X.stp", "FP.kicad_mod", f"{LIB}.kicad_sym"]


def test_mkdir_missing_parents_are_removed_by_rollback(tmp_path, snapshot, monkeypatch):
    write_custom_layout(tmp_path, [], [])
    layout = RepoLayout.for_repo(tmp_path)
    layout.footprints_dir.rmdir()
    plan = _hand_plan(layout, new_library=True)
    before = snapshot(layout.custom_dir)
    _flaky_writes(monkeypatch, fail_on=2)

    result = apply_plan(plan, backup_root=tmp_path / "bk")

    assert not result.ok
    assert not layout.footprints_dir.exists()
    assert snapshot(layout.custom_dir) == before


def test_rollback_restores_case_twin(hand_layout, snapshot, monkeypatch):
    original = b"original model bytes"
    twin = hand_layout.models_dir / "foo.STEP"
    twin.write_bytes(original)
    plan = _hand_plan(hand_layout, new_library=True)
    overwrite = FileOp(
        "model", hand_layout.models_dir / "Foo.step", data=STEP_BYTES, base_sha256=_sha(original), listed_path=twin
    )
    plan = dataclasses.replace(plan, ops=tuple(overwrite if op.kind == "model" else op for op in plan.ops))
    before = snapshot(hand_layout.custom_dir)
    _flaky_writes(monkeypatch, fail_on=2)  # the model overwrite succeeds, the footprint fails

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")

    assert not result.ok
    spellings = [n for n in os.listdir(hand_layout.models_dir) if n.casefold() == "foo.step"]
    assert spellings == ["foo.STEP"]
    assert twin.read_bytes() == original
    assert snapshot(hand_layout.custom_dir) == before
    assert (result.backup_dir / "foo.STEP_backup_1").read_bytes() == original


def test_rollback_failed_step_continues(hand_layout, monkeypatch):
    plan = _hand_plan(hand_layout, new_library=False)
    original = plan.symbol_lib_path.read_bytes()
    real = fsutil.atomic_write_bytes
    seen = {"sym": 0}

    def write(path, data, **kwargs):
        if path == plan.symbol_lib_path:
            seen["sym"] += 1
            if seen["sym"] == 2:  # the restore, after the forward write
                return Issue(Severity.ERROR, "fs.locked", "injected lock")
        return real(path, data, **kwargs)

    monkeypatch.setattr(fsutil, "atomic_write_bytes", write)
    monkeypatch.setattr(
        applier.verify, "verify_install", lambda p: [Issue(Severity.ERROR, "verify.link_unresolved", "forced")]
    )

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")

    assert not result.ok
    # the undo went on past the failed restore
    assert not (hand_layout.models_dir / "X.stp").exists()
    assert not (hand_layout.footprints_dir / f"{LIB}.pretty" / "FP.kicad_mod").exists()
    left = [i for i in result.issues if i.code == "install.rollback_failed"]
    assert len(left) == 1 and left[0].severity is Severity.ERROR
    assert str(plan.symbol_lib_path) in left[0].text and str(result.backup_dir) in left[0].text
    assert "install.rolled_back" in _codes(result.issues)
    assert (result.backup_dir / f"{LIB}.kicad_sym_backup_1").read_bytes() == original


def test_rollback_on_verify_error(hand_layout, snapshot, monkeypatch):
    plan = _hand_plan(hand_layout, new_library=False)
    before = snapshot(hand_layout.custom_dir)
    monkeypatch.setattr(
        applier.verify, "verify_install", lambda p: [Issue(Severity.ERROR, "verify.symbol_missing", "forced")]
    )

    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")

    assert not result.ok
    assert _codes(_errors(result.issues)) == ["verify.symbol_missing", "install.rolled_back"]
    assert snapshot(hand_layout.custom_dir) == before
    assert result.touched == ()
