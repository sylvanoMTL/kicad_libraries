"""Task 2/3 (13-13): the migration transaction is safe before, during and after its ops (MIG-03).

Every Custom/ here is a hand-built tree under tmp_path, assembled directly from MigrationOp
values rather than through the planner, so each test isolates one applier behavior. The live
Custom/ is never touched.
"""

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from customfixtures import digest_tree
from fakecli import FakeCli

from kicad_lib_manager import fsutil
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.migration import applier as applier_module
from kicad_lib_manager.importer.migration.applier import apply_migration
from kicad_lib_manager.importer.migration.plan import MigrationOp, MigrationPlan
from kicad_lib_manager.importer.plan import ToolContext
from kicad_lib_manager.models import Issue, Severity

# The backup-pruning limit this applier module is specified to use (migration/applier.py
# MIGRATION_BACKUPS_KEPT); kept as a literal here so this test module can import and collect
# against the pre-Task-2 applier.py, whose RED run must fail on behavior, not on import.
_MIGRATION_BACKUPS_KEPT = 10


def _plan(layout: RepoLayout, ops: tuple[MigrationOp, ...], *, bak_files: tuple[str, ...] = ()) -> MigrationPlan:
    return MigrationPlan(
        layout=layout,
        parts=(),
        ops=ops,
        library_map=(),
        symbol_renames=(),
        footprint_links=(),
        model_renames=(),
        leftovers=(),
        families=(),
        conflicts=(),
        removed_libraries=(),
        bak_files=bak_files,
        map_text="",
        issues=(),
    )


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# -- containment, links, staleness, name clashes (preflight) -------------------------------------


def test_op_outside_custom_is_refused(tmp_path):
    layout = RepoLayout.for_repo(tmp_path)
    layout.custom_dir.mkdir(parents=True, exist_ok=True)
    outside = tmp_path / "sym-lib-table"
    op = MigrationOp("write", outside, "sym-lib-table", data=b"not Custom's", base_sha256=None)
    plan = _plan(layout, (op,))
    called: list[int] = []

    result = apply_migration(
        plan, backup_root=tmp_path / "backups", before_first_write=lambda: called.append(1) or []
    )

    assert result.ok is False
    assert any(i.code == "migration.outside_custom" for i in result.issues)
    assert called == []
    assert not outside.exists()


def test_junction_or_symlink_is_refused(tmp_path):
    layout = RepoLayout.for_repo(tmp_path)
    layout.footprints_dir.mkdir(parents=True, exist_ok=True)
    target = tmp_path / "elsewhere"
    target.mkdir()
    link = layout.footprints_dir / "Atomic_Footprints.pretty"
    try:
        os.symlink(target, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        made = (
            sys.platform == "win32"
            and subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True
            ).returncode
            == 0
        )
        if not made:
            pytest.skip("directory links are not available here")

    op = MigrationOp(
        "write",
        link / "FP1.kicad_mod",
        "Custom/Footprints/Atomic_Footprints.pretty/FP1.kicad_mod",
        data=b"planned",
        base_sha256=None,
    )
    plan = _plan(layout, (op,))

    result = apply_migration(plan, backup_root=tmp_path / "backups")

    assert result.ok is False
    assert any(i.code == "migration.link_refused" for i in result.issues)
    assert not (target / "FP1.kicad_mod").exists()


def test_source_changed_after_preview_is_refused(tmp_path):
    layout = RepoLayout.for_repo(tmp_path)
    layout.symbols_dir.mkdir(parents=True, exist_ok=True)

    stale_file = layout.symbols_dir / "ToDelete.kicad_sym"
    stale_file.write_bytes(b"original")
    original_hash = _sha(b"original")
    stale_file.write_bytes(b"changed after the preview")
    delete_op = MigrationOp("delete", stale_file, "Custom/Symbols/ToDelete.kicad_sym", base_sha256=original_hash)
    stale_plan = _plan(layout, (delete_op,))

    stale_result = apply_migration(stale_plan, backup_root=tmp_path / "backups")

    assert stale_result.ok is False
    stale_issue = next(i for i in stale_result.issues if i.code == "migration.stale")
    assert "ToDelete.kicad_sym" in stale_issue.text
    assert "open the migration again" in stale_issue.text
    assert stale_file.read_bytes() == b"changed after the preview"

    appeared = layout.symbols_dir / "Appeared.kicad_sym"
    appeared.write_bytes(b"surprise file on disk")
    write_op = MigrationOp("write", appeared, "Custom/Symbols/Appeared.kicad_sym", data=b"planned", base_sha256=None)
    taken_plan = _plan(layout, (write_op,))

    taken_result = apply_migration(taken_plan, backup_root=tmp_path / "backups")

    assert taken_result.ok is False
    assert any(i.code == "migration.name_taken" for i in taken_result.issues)
    assert appeared.read_bytes() == b"surprise file on disk"


def test_case_twin_plan_is_refused(tmp_path):
    layout = RepoLayout.for_repo(tmp_path)
    layout.models_dir.mkdir(parents=True, exist_ok=True)
    existing = layout.models_dir / "A.STEP"
    existing.write_bytes(b"old-step")
    write_op = MigrationOp(
        "write", layout.models_dir / "a.step", "Custom/3DModels/a.step", data=b"new-step", base_sha256=None
    )
    delete_op = MigrationOp(
        "delete", existing, "Custom/3DModels/A.STEP", base_sha256=_sha(b"old-step")
    )
    plan = _plan(layout, (write_op, delete_op))

    result = apply_migration(plan, backup_root=tmp_path / "backups")

    assert result.ok is False
    assert any(i.code == "migration.case_twin" for i in result.issues)
    assert existing.read_bytes() == b"old-step"


def test_duplicate_write_plan_is_refused(tmp_path):
    """Gap CR-01 (13-21): two write ops aimed at one path are refused before the first byte, whatever
    planner bug produced the pair -- this is the structural backstop, never an owner-facing path."""
    layout = RepoLayout.for_repo(tmp_path)
    layout.models_dir.mkdir(parents=True, exist_ok=True)
    old1 = layout.models_dir / "OLD1.step"
    old2 = layout.models_dir / "OLD2.step"
    old1.write_bytes(b"model-one")
    old2.write_bytes(b"model-two")
    target = layout.models_dir / "COLLIDE.step"

    write_op1 = MigrationOp("write", target, "Custom/3DModels/COLLIDE.step", data=b"model-one", base_sha256=None)
    delete_op1 = MigrationOp("delete", old1, "Custom/3DModels/OLD1.step", base_sha256=_sha(b"model-one"))
    write_op2 = MigrationOp("write", target, "Custom/3DModels/COLLIDE.step", data=b"model-two", base_sha256=None)
    delete_op2 = MigrationOp("delete", old2, "Custom/3DModels/OLD2.step", base_sha256=_sha(b"model-two"))
    plan = _plan(layout, (write_op1, delete_op1, write_op2, delete_op2))

    result = apply_migration(plan, backup_root=tmp_path / "backups")

    assert result.ok is False
    dup_issues = [i for i in result.issues if i.code == "migration.duplicate_write"]
    assert len(dup_issues) == 1
    assert "COLLIDE.step" in dup_issues[0].text
    assert "nothing was written" in dup_issues[0].text
    # WR-01: the message names both colliding ops, not only the later one.
    assert "OLD1.step" in dup_issues[0].text or "OLD2.step" in dup_issues[0].text
    assert old1.read_bytes() == b"model-one"
    assert old2.read_bytes() == b"model-two"
    assert not target.exists()


def test_rename_overwrite_plan_is_refused(tmp_path):
    """MIG-03 (13-22): a rename write op whose target would overwrite bytes no delete op removes is
    refused before the first byte, whichever planner path produced it (gap CR-01's second round)."""
    layout = RepoLayout.for_repo(tmp_path)
    layout.models_dir.mkdir(parents=True, exist_ok=True)
    taken = layout.models_dir / "TAKEN.STEP"
    taken.write_bytes(b"unrelated")
    old1 = layout.models_dir / "OLD1.step"
    old1.write_bytes(b"renamed")

    write_op = MigrationOp(
        "write",
        layout.models_dir / "taken.step",
        "Custom/3DModels/taken.step",
        data=b"renamed",
        base_sha256=_sha(b"unrelated"),
        source_rel="Custom/3DModels/OLD1.step",
    )
    delete_op = MigrationOp(
        "delete", old1, "Custom/3DModels/OLD1.step", base_sha256=_sha(b"renamed")
    )
    plan = _plan(layout, (write_op, delete_op))

    result = apply_migration(plan, backup_root=tmp_path / "backups")

    assert result.ok is False
    overwrite_issues = [i for i in result.issues if i.code == "migration.rename_would_overwrite"]
    assert len(overwrite_issues) == 1
    assert "Custom/3DModels/taken.step" in overwrite_issues[0].text
    assert "nothing was written" in overwrite_issues[0].text
    assert taken.read_bytes() == b"unrelated"
    backups_dir = tmp_path / "backups" / "migrations"
    assert not backups_dir.exists() or list(backups_dir.iterdir()) == []


# -- the load gate --------------------------------------------------------------------------------


def test_load_gate_failure_writes_nothing(tmp_path):
    layout = RepoLayout.for_repo(tmp_path)
    layout.symbols_dir.mkdir(parents=True, exist_ok=True)
    write_op = MigrationOp(
        "write",
        layout.symbols_dir / "Atomic_X.kicad_sym",
        "Custom/Symbols/Atomic_X.kicad_sym",
        data=b"(kicad_symbol_lib (version 20251024) (generator kicad_symbol_editor))\n",
        base_sha256=None,
    )
    plan = _plan(layout, (write_op,))
    tools = ToolContext(kicad_cli=Path("kicad-cli"), cli_runner=FakeCli(modes={"sym upgrade": "reject"}))
    before = digest_tree(layout.custom_dir)
    called: list[int] = []

    result = apply_migration(
        plan,
        backup_root=tmp_path / "backups",
        tools=tools,
        before_first_write=lambda: called.append(1) or [],
    )

    assert result.ok is False
    assert any(i.code == "migration.load_failed" for i in result.issues)
    assert called == []  # the load gate runs before before_first_write; it never got there
    assert digest_tree(layout.custom_dir) == before
    backups_dir = tmp_path / "backups" / "migrations"
    assert not backups_dir.exists() or list(backups_dir.iterdir()) == []


# -- backups ---------------------------------------------------------------------------------------


def test_backups_hold_every_replaced_and_deleted_file(tmp_path):
    layout = RepoLayout.for_repo(tmp_path)
    layout.symbols_dir.mkdir(parents=True, exist_ok=True)
    old_lib = layout.symbols_dir / "OldLib.kicad_sym"
    old_lib.write_bytes(b"old-lib-content")
    bak_file = layout.symbols_dir / "OldLib.bak"
    bak_file.write_bytes(b"bak-content")
    replace_target = layout.symbols_dir / "Atomic_X.kicad_sym"
    replace_target.write_bytes(b"replace-me")

    write_op = MigrationOp(
        "write",
        replace_target,
        "Custom/Symbols/Atomic_X.kicad_sym",
        data=b"new-content",
        base_sha256=_sha(b"replace-me"),
    )
    delete_lib_op = MigrationOp(
        "delete", old_lib, "Custom/Symbols/OldLib.kicad_sym", base_sha256=_sha(b"old-lib-content")
    )
    delete_bak_op = MigrationOp(
        "delete", bak_file, "Custom/Symbols/OldLib.bak", base_sha256=_sha(b"bak-content")
    )
    plan = _plan(
        layout, (write_op, delete_lib_op, delete_bak_op), bak_files=("Custom/Symbols/OldLib.bak",)
    )
    backup_root = tmp_path / "backups"

    result = apply_migration(plan, backup_root=backup_root)

    assert result.ok, result.issues
    backup_contents = {p.read_bytes() for p in result.backup_dir.iterdir() if p.is_file()}
    assert b"replace-me" in backup_contents
    assert b"old-lib-content" in backup_contents
    assert b"bak-content" in backup_contents

    migrations_root = backup_root / "migrations"
    for day in range(1, 11):
        folder = migrations_root / f"202601{day:02d}-000000_migration"
        folder.mkdir()
        (folder / "placeholder").write_bytes(b"x")
    assert len(list(migrations_root.iterdir())) == 11  # the real one above, plus 10 seeded older ones

    write_op2 = MigrationOp(
        "write",
        replace_target,
        "Custom/Symbols/Atomic_X.kicad_sym",
        data=b"newer-content",
        base_sha256=_sha(b"new-content"),
    )
    plan2 = _plan(layout, (write_op2,))

    result2 = apply_migration(plan2, backup_root=backup_root)

    assert result2.ok, result2.issues
    assert len(list(migrations_root.iterdir())) == _MIGRATION_BACKUPS_KEPT


# -- verify after the ops ---------------------------------------------------------------------------


def test_verify_after_ops(tmp_path, monkeypatch):
    layout = RepoLayout.for_repo(tmp_path)
    layout.symbols_dir.mkdir(parents=True, exist_ok=True)
    target = layout.symbols_dir / "Atomic_X.kicad_sym"
    write_op = MigrationOp(
        "write", target, "Custom/Symbols/Atomic_X.kicad_sym", data=b"planned-content", base_sha256=None
    )
    plan = _plan(layout, (write_op,))

    real_write = fsutil.atomic_write_bytes

    def corrupting(path, data, **kwargs):
        return real_write(path, b"corrupted-instead", **kwargs)

    monkeypatch.setattr(applier_module.fsutil, "atomic_write_bytes", corrupting)

    result = apply_migration(plan, backup_root=tmp_path / "backups")

    assert result.ok is False
    assert any(i.code == "migration.verify_failed" for i in result.issues)
    assert not target.exists()  # rolled back: it did not exist before this transaction


# -- Task 3: rollback of every op kind, interrupts, locked files, kept folders --------------------


@pytest.mark.parametrize("kind", ["mkdir", "write", "delete", "rmdir"])
def test_failure_at_each_op_kind_rolls_back(tmp_path, monkeypatch, kind):
    layout = RepoLayout.for_repo(tmp_path)
    layout.symbols_dir.mkdir(parents=True, exist_ok=True)
    layout.footprints_dir.mkdir(parents=True, exist_ok=True)

    # A benign op that always succeeds first, so every kind under test has at least one earlier op.
    warm_up_target = layout.symbols_dir / "WarmUp.kicad_sym"
    warm_up_op = MigrationOp("write", warm_up_target, "Custom/Symbols/WarmUp.kicad_sym", data=b"warm", base_sha256=None)

    write_target = layout.symbols_dir / "Atomic_X.kicad_sym"
    write_target.write_bytes(b"existing-content")
    write_op = MigrationOp(
        "write", write_target, "Custom/Symbols/Atomic_X.kicad_sym", data=b"new-content", base_sha256=_sha(b"existing-content")
    )

    delete_target = layout.symbols_dir / "OldLib.kicad_sym"
    delete_target.write_bytes(b"old-content")
    delete_op = MigrationOp("delete", delete_target, "Custom/Symbols/OldLib.kicad_sym", base_sha256=_sha(b"old-content"))

    mkdir_target = layout.footprints_dir / "Atomic_Footprints.pretty"
    mkdir_op = MigrationOp("mkdir", mkdir_target, "Custom/Footprints/Atomic_Footprints.pretty")

    rmdir_target = layout.footprints_dir / "ToRemove.pretty"
    rmdir_target.mkdir()
    rmdir_op = MigrationOp("rmdir", rmdir_target, "Custom/Footprints/ToRemove.pretty")

    by_kind = {"mkdir": mkdir_op, "write": write_op, "delete": delete_op, "rmdir": rmdir_op}
    target_op = by_kind[kind]
    plan = _plan(layout, (warm_up_op, target_op))

    before_files = digest_tree(layout.custom_dir)

    if kind == "mkdir":
        real_mkdir = Path.mkdir

        def failing(self, *a, **k):
            if self == mkdir_target:
                raise OSError("simulated mkdir failure")
            return real_mkdir(self, *a, **k)

        monkeypatch.setattr(Path, "mkdir", failing)
    elif kind == "write":
        real_write = fsutil.atomic_write_bytes

        def failing(path, data, **k):
            if path == write_target:
                return Issue(Severity.ERROR, "fs.write_failed", "simulated write failure")
            return real_write(path, data, **k)

        monkeypatch.setattr(applier_module.fsutil, "atomic_write_bytes", failing)
    elif kind == "delete":
        real_unlink = Path.unlink

        def failing(self, *a, **k):
            if self == delete_target:
                raise OSError("simulated delete failure")
            return real_unlink(self, *a, **k)

        monkeypatch.setattr(Path, "unlink", failing)
    else:
        real_rmdir = Path.rmdir

        def failing(self, *a, **k):
            if self == rmdir_target:
                raise OSError("simulated rmdir failure")
            return real_rmdir(self, *a, **k)

        monkeypatch.setattr(Path, "rmdir", failing)

    result = apply_migration(plan, backup_root=tmp_path / "backups")

    assert result.ok is False
    rolled_back = next(i for i in result.issues if i.code == "migration.rolled_back")
    assert rolled_back.severity == Severity.INFO
    after_files = digest_tree(layout.custom_dir)
    assert before_files == after_files


def test_interrupt_rolls_back_and_reraises(tmp_path, monkeypatch):
    layout = RepoLayout.for_repo(tmp_path)
    layout.symbols_dir.mkdir(parents=True, exist_ok=True)
    target_a = layout.symbols_dir / "A.kicad_sym"
    target_a.write_bytes(b"a-original")
    target_b = layout.symbols_dir / "B.kicad_sym"
    target_b.write_bytes(b"b-original")
    op_a = MigrationOp("write", target_a, "Custom/Symbols/A.kicad_sym", data=b"a-new", base_sha256=_sha(b"a-original"))
    op_b = MigrationOp("write", target_b, "Custom/Symbols/B.kicad_sym", data=b"b-new", base_sha256=_sha(b"b-original"))
    plan = _plan(layout, (op_a, op_b))

    before = digest_tree(layout.custom_dir)
    real_write = fsutil.atomic_write_bytes
    calls = {"n": 0}

    def interrupting(path, data, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise KeyboardInterrupt()
        return real_write(path, data, **kwargs)

    monkeypatch.setattr(applier_module.fsutil, "atomic_write_bytes", interrupting)

    with pytest.raises(KeyboardInterrupt):
        apply_migration(plan, backup_root=tmp_path / "backups")

    after = digest_tree(layout.custom_dir)
    assert before == after


def test_locked_file_delete_retries_then_rolls_back(tmp_path, monkeypatch):
    layout = RepoLayout.for_repo(tmp_path)
    layout.symbols_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(applier_module.time, "sleep", lambda s: None)

    # Two PermissionErrors then success: the delete completes.
    retry_target = layout.symbols_dir / "RetryMe.kicad_sym"
    retry_target.write_bytes(b"retry-content")
    retry_op = MigrationOp("delete", retry_target, "Custom/Symbols/RetryMe.kicad_sym", base_sha256=_sha(b"retry-content"))
    retry_plan = _plan(layout, (retry_op,))

    real_unlink = Path.unlink
    retry_calls = {"n": 0}

    def flaky(self, *a, **k):
        if self == retry_target:
            retry_calls["n"] += 1
            if retry_calls["n"] <= 2:
                raise PermissionError(13, "in use")
        return real_unlink(self, *a, **k)

    monkeypatch.setattr(Path, "unlink", flaky)

    retry_result = apply_migration(retry_plan, backup_root=tmp_path / "backups")

    assert retry_result.ok, retry_result.issues
    assert not retry_target.exists()
    assert retry_calls["n"] == 3

    # Always locked: past the retry window, the transaction rolls back with an ERROR naming the file.
    stuck_target = layout.symbols_dir / "StuckLock.kicad_sym"
    stuck_target.write_bytes(b"stuck-content")
    stuck_op = MigrationOp("delete", stuck_target, "Custom/Symbols/StuckLock.kicad_sym", base_sha256=_sha(b"stuck-content"))
    stuck_plan = _plan(layout, (stuck_op,))

    def always_locked(self, *a, **k):
        if self == stuck_target:
            raise PermissionError(13, "in use")
        return real_unlink(self, *a, **k)

    monkeypatch.setattr(Path, "unlink", always_locked)

    stuck_result = apply_migration(stuck_plan, backup_root=tmp_path / "backups")

    assert stuck_result.ok is False
    locked_issue = next(i for i in stuck_result.issues if i.code == "migration.locked")
    assert "StuckLock.kicad_sym" in locked_issue.text
    assert stuck_target.exists()


def test_folder_with_unlisted_file_is_kept(tmp_path):
    layout = RepoLayout.for_repo(tmp_path)
    layout.footprints_dir.mkdir(parents=True, exist_ok=True)
    pretty = layout.footprints_dir / "OldLib.pretty"
    pretty.mkdir()
    (pretty / "notes.txt").write_bytes(b"keep me")
    rmdir_op = MigrationOp("rmdir", pretty, "Custom/Footprints/OldLib.pretty")
    plan = _plan(layout, (rmdir_op,))

    result = apply_migration(plan, backup_root=tmp_path / "backups")

    assert result.ok, result.issues
    assert pretty.is_dir()
    assert (pretty / "notes.txt").read_bytes() == b"keep me"
    kept = next(i for i in result.issues if i.code == "migration.folder_kept")
    assert kept.severity == Severity.WARNING
    assert "notes.txt" in kept.text


def test_rollback_leftover_is_reported(tmp_path, monkeypatch):
    layout = RepoLayout.for_repo(tmp_path)
    layout.symbols_dir.mkdir(parents=True, exist_ok=True)
    layout.footprints_dir.mkdir(parents=True, exist_ok=True)
    target_a = layout.symbols_dir / "A.kicad_sym"
    target_a.write_bytes(b"a-original")
    target_b = layout.symbols_dir / "B.kicad_sym"
    target_b.write_bytes(b"b-original")
    doomed_dir = layout.footprints_dir / "WontMake.pretty"

    op_a = MigrationOp("write", target_a, "Custom/Symbols/A.kicad_sym", data=b"a-new", base_sha256=_sha(b"a-original"))
    op_b = MigrationOp("write", target_b, "Custom/Symbols/B.kicad_sym", data=b"b-new", base_sha256=_sha(b"b-original"))
    op_c = MigrationOp("mkdir", doomed_dir, "Custom/Footprints/WontMake.pretty")
    plan = _plan(layout, (op_a, op_b, op_c))

    real_mkdir = Path.mkdir

    def failing_mkdir(self, *args, **kwargs):
        if self == doomed_dir:
            raise OSError("simulated mkdir failure")
        return real_mkdir(self, *args, **kwargs)

    real_write = fsutil.atomic_write_bytes

    def restore_blocker(path, data, **kwargs):
        if path == target_a and data == b"a-original":
            return Issue(Severity.ERROR, "fs.write_failed", "simulated restore failure")
        return real_write(path, data, **kwargs)

    monkeypatch.setattr(Path, "mkdir", failing_mkdir)
    monkeypatch.setattr(applier_module.fsutil, "atomic_write_bytes", restore_blocker)

    result = apply_migration(plan, backup_root=tmp_path / "backups")

    assert result.ok is False
    leftover = next(i for i in result.issues if i.code == "migration.rollback_incomplete")
    assert "A.kicad_sym" in leftover.text
    assert str(result.backup_dir) in leftover.text
    assert target_b.read_bytes() == b"b-original"
