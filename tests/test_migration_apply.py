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
