"""Carry out a MigrationPlan as one transaction: back up, write in order, undo on any failure (D-04).

Mirrors importer/applier.py's _Undo/_rollback pattern with the migration's extra op kinds (mkdir,
rmdir); only public names of that module are read, never imported. 13-13 hardens this further
(a preflight containment check, backup pruning).
"""

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from ... import fsutil
from ...models import Issue, Severity
from .plan import MigrationPlan

MIGRATION_BACKUPS = "migrations"


@dataclass(frozen=True)
class MigrationResult:
    """What apply_migration did: ok, every Issue, the files written and deleted, and their sha256."""

    ok: bool
    issues: tuple[Issue, ...]
    written: tuple[str, ...]
    deleted: tuple[str, ...]
    backup_dir: Path | None
    plan: MigrationPlan
    sha256: dict[str, str]


class _Undo(NamedTuple):
    kind: str  # "mkdir" | "write" | "delete" | "rmdir"
    path: Path
    pre_image: bytes | None


def _err(code: str, text: str) -> Issue:
    return Issue(Severity.ERROR, code, text)


def _notify(progress: Callable | None, message: str, current: int, total: int) -> None:
    if progress is None:
        return
    try:
        progress(message, current, total)
    except Exception:
        pass


def _rollback(undo: list[_Undo]) -> list[Issue]:
    """Reverse the transaction's steps in reverse order; keep going past a failed step (D-04)."""
    leftovers: list[Issue] = []
    for step in reversed(undo):
        try:
            if step.kind == "mkdir":
                step.path.rmdir()
            elif step.kind == "rmdir":
                step.path.mkdir()
            elif step.kind == "write":
                if step.pre_image is None:
                    step.path.unlink(missing_ok=True)
                else:
                    problem = fsutil.atomic_write_bytes(step.path, step.pre_image)
                    if problem is not None:
                        leftovers.append(_err("migration.rollback_failed", f"{step.path} could not be restored ({problem.text})"))
            elif step.kind == "delete":
                problem = fsutil.atomic_write_bytes(step.path, step.pre_image or b"")
                if problem is not None:
                    leftovers.append(_err("migration.rollback_failed", f"{step.path} could not be restored ({problem.text})"))
        except FileNotFoundError:
            continue
        except OSError as e:
            leftovers.append(_err("migration.rollback_failed", f"{step.path} could not be restored ({e.strerror or e})"))
    return leftovers


def _backup_folder(root: Path) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    return root / MIGRATION_BACKUPS / stamp


def _failed(plan: MigrationPlan, issues: list[Issue], undo: list[_Undo], backup_dir: Path | None) -> MigrationResult:
    leftovers = _rollback(undo)
    return MigrationResult(False, (*issues, *leftovers), (), (), backup_dir, plan, {})


def apply_migration(
    plan: MigrationPlan,
    *,
    backup_root: Path | None = None,
    progress: Callable | None = None,
    before_first_write: Callable[[], list[Issue]] | None = None,
) -> MigrationResult:
    """Write plan.ops in order; any failure restores every file and folder the migration touched."""
    if before_first_write is not None:
        pre_issues = before_first_write()
        if pre_issues:
            return MigrationResult(False, tuple(pre_issues), (), (), None, plan, {})

    backup_dir = _backup_folder(backup_root if backup_root is not None else fsutil.default_backup_dir())
    undo: list[_Undo] = []
    written: list[str] = []
    deleted: list[str] = []
    sha: dict[str, str] = {}
    total = len(plan.ops)

    try:
        for index, op in enumerate(plan.ops):
            _notify(progress, f"{op.kind} {op.rel}", index, total)
            if op.kind == "mkdir":
                op.path.mkdir(parents=True, exist_ok=True)
                undo.append(_Undo("mkdir", op.path, None))
            elif op.kind == "write":
                pre_image = op.path.read_bytes() if op.path.exists() else None
                if pre_image is not None:
                    saved = fsutil.backup_file(op.path, backup_dir)
                    if isinstance(saved, Issue):
                        return _failed(plan, [saved], undo, backup_dir)
                data = op.data if op.data is not None else b""
                problem = fsutil.atomic_write_bytes(op.path, data)
                if problem is not None:
                    return _failed(plan, [problem], undo, backup_dir)
                undo.append(_Undo("write", op.path, pre_image))
                written.append(op.rel)
                sha[op.rel] = hashlib.sha256(data).hexdigest()
            elif op.kind == "delete":
                pre_image = op.path.read_bytes()
                saved = fsutil.backup_file(op.path, backup_dir)
                if isinstance(saved, Issue):
                    return _failed(plan, [saved], undo, backup_dir)
                op.path.unlink()
                undo.append(_Undo("delete", op.path, pre_image))
                deleted.append(op.rel)
            elif op.kind == "rmdir":
                op.path.rmdir()
                undo.append(_Undo("rmdir", op.path, None))
            else:
                return _failed(plan, [_err("migration.unknown_op", f"Unknown operation kind {op.kind!r}")], undo, backup_dir)
    except BaseException as error:
        leftovers = _rollback(undo)
        if not isinstance(error, Exception):
            raise
        issue = _err("migration.unexpected", f"The migration stopped unexpectedly ({type(error).__name__}: {error})")
        return MigrationResult(False, (issue, *leftovers), (), (), backup_dir, plan, {})

    return MigrationResult(True, (), tuple(written), tuple(deleted), backup_dir, plan, sha)
