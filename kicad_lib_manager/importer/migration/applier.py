"""Carry out a MigrationPlan as one transaction: back up, write in order, undo on any failure (D-04).

Mirrors importer/applier.py's _Undo/_rollback pattern with the migration's extra op kinds (mkdir,
rmdir), and reuses importer/applier.py's prune_install_backups directly rather than duplicating it
(only its public name is read, never its private helpers). Order: preflight (containment, link
refusal, staleness, name clashes, case twins) -> the KiCad load gate -> before_first_write (the
pre-atomic tag) -> backups of every file about to be replaced or deleted -> the ops themselves,
each re-checked against what the transaction itself has written so far -> a post-write verify ->
pruning of old migration backups. Any ERROR after the first write rolls back every step already
taken, in reverse order. 13-13 Task 3 completes the rollback: a locked delete's retry window, a
non-empty folder kept instead of torn down, and every leftover reported with the backup folder.
"""

import hashlib
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

from ... import fsutil, kicad_files
from ...models import Issue, Severity
from .. import applier as install_applier
from ..kicad_cli import load_gate
from ..plan import ToolContext
from .plan import MigrationOp, MigrationPlan

MIGRATION_BACKUPS = "migrations"
MIGRATION_BACKUPS_KEPT = 10
# Sums to about 1 s: the same retry window fsutil.atomic_write_bytes gives a locked write (D-05)
_DELETE_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.3, 0.35)
_DELETE_RETRY_S = sum(_DELETE_RETRY_DELAYS)


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


def _rollback(undo: list[_Undo], backup_dir: Path | None) -> list[Issue]:
    """Reverse the transaction's steps in reverse order; keep going past a failed step (D-04).

    A leftover names backup_dir so the owner can restore the file by hand from the app-data copy
    (every replaced/deleted file was backed up there before the first write, see _backup_all).
    """
    leftovers: list[Issue] = []
    where = f"; see the backup folder at {backup_dir}" if backup_dir is not None else ""
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
                        leftovers.append(_err("migration.rollback_incomplete", f"{step.path} could not be restored ({problem.text}){where}"))
            elif step.kind == "delete":
                problem = fsutil.atomic_write_bytes(step.path, step.pre_image or b"")
                if problem is not None:
                    leftovers.append(_err("migration.rollback_incomplete", f"{step.path} could not be restored ({problem.text}){where}"))
        except FileNotFoundError:
            continue
        except OSError as e:
            leftovers.append(_err("migration.rollback_incomplete", f"{step.path} could not be restored ({e.strerror or e}){where}"))
    return leftovers


def _backup_folder(root: Path) -> Path:
    """migrations/<stamp>[-N]_migration: the trailing _migration makes this a prune_install_backups candidate."""
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    migrations = root / MIGRATION_BACKUPS
    number = 1
    while True:
        suffix = "" if number == 1 else f"-{number}"
        folder = migrations / f"{stamp}{suffix}_migration"
        if not folder.exists():
            return folder
        number += 1


def _rolled_back_summary(undo: list[_Undo], leftovers: list[Issue]) -> list[Issue]:
    """An INFO migration.rolled_back once anything was actually undone; silent when undo is empty."""
    if not undo:
        return []
    summary = "some files could not be restored" if leftovers else "every change was undone"
    return [Issue(Severity.INFO, "migration.rolled_back", f"The migration failed; {summary}.")]


def _failed(plan: MigrationPlan, issues: list[Issue], undo: list[_Undo], backup_dir: Path | None) -> MigrationResult:
    leftovers = _rollback(undo, backup_dir)
    summary = _rolled_back_summary(undo, leftovers)
    return MigrationResult(False, (*issues, *summary, *leftovers), (), (), backup_dir, plan, {})


# -- preflight: containment, links, staleness, name clashes, case twins (P-11, T-13-30, T-13-31) --


def _lexical(path: Path) -> Path:
    """path with "." and ".." segments collapsed, but no symlink or junction followed.

    Containment must be judged on the path the plan names, not where a link happens to point: a
    write reached through a symlinked .pretty folder is still nominally under Custom, and gets its
    own, more specific migration.link_refused rather than being folded into outside_custom.
    """
    return Path(os.path.normpath(str(path)))


def _link_on_path(path: Path, custom_dir: Path) -> bool:
    """True when any folder from custom_dir down to path's own parent is a symlink or junction."""
    is_junction = getattr(os.path, "isjunction", lambda p: False)
    try:
        rel_parts = path.parent.relative_to(custom_dir).parts
    except ValueError:
        return False  # already reported by the containment check
    current = custom_dir
    for part in rel_parts:
        current = current / part
        if current.is_symlink() or is_junction(current):
            return True
    return False


def _listed_names(folder: Path) -> list[str] | None:
    try:
        return os.listdir(folder)
    except OSError:
        return None


def _footprint_block_hash(path: Path) -> str | None:
    """The sha256 of just the footprint's own block text, matching migration.inventory's
    InventoryFootprint.sha256 (block_text excludes the file's leading/trailing whitespace, so this
    is NOT the same as the whole file's hash); None when the file cannot be parsed."""
    loaded = kicad_files.load(path)
    if isinstance(loaded, Issue):
        return None
    ref = kicad_files.footprint_name(loaded.root)
    if ref is None:
        return None
    block = kicad_files.block_text(loaded.source.text, ref.node)
    return hashlib.sha256(block.encode("utf-8")).hexdigest()


def _hash_for(kind: str, original_suffix: str, content_path: Path) -> str | None:
    """The hash comparable to a {kind} op's base_sha256, read from content_path.

    A deleted .kicad_mod's base_sha256 comes from migration.inventory's InventoryFootprint.sha256,
    the footprint's own block-text hash, not the whole file's (footprints.py reuses it verbatim).
    Every other producer (symbols.py's library deletes, planner.py's .bak deletes, every write's
    pre-existing-target check) hashes the whole file, so that is the default here.

    original_suffix is the op's OWN path suffix, not content_path's: _backup_all re-checks the
    backup copy (named "<name>_backup_<N>", whose own .suffix is no longer ".kicad_mod") for
    identical content, and the block/whole-file choice must still be made from the original name.
    """
    if kind == "delete" and original_suffix.casefold() == ".kicad_mod":
        block_hash = _footprint_block_hash(content_path)
        if block_hash is not None:
            return block_hash
    try:
        return hashlib.sha256(content_path.read_bytes()).hexdigest()
    except OSError:
        return None


def _current_hash(op: MigrationOp) -> str | None:
    return _hash_for(op.kind, op.path.suffix, op.path)


def _preflight(plan: MigrationPlan) -> list[Issue]:
    """Every problem that must stop the migration before a single byte is touched."""
    custom_dir = plan.layout.custom_dir
    custom_norm = _lexical(custom_dir)

    issues = [
        _err("migration.outside_custom", f"{op.rel} is outside Custom; nothing was written")
        for op in plan.ops
        if not _lexical(op.path).is_relative_to(custom_norm)
    ]
    if issues:
        return issues

    issues = [
        _err("migration.link_refused", f"{op.rel} is reached through a symlink or junction; nothing was written")
        for op in plan.ops
        if op.kind in ("write", "delete") and _link_on_path(op.path, custom_dir)
    ]
    if issues:
        return issues

    # A write and a delete that resolve to the same file by different spellings (a planner bug, P-08):
    # checked before staleness/name-taken so this specific defect gets its own, more useful code.
    writes = {str(op.path).casefold(): op for op in plan.ops if op.kind == "write"}
    deletes = {str(op.path).casefold(): op for op in plan.ops if op.kind == "delete"}
    issues = [
        _err(
            "migration.case_twin",
            f"{writes[key].rel} and {deletes[key].rel} refer to the same file under different spellings; nothing was written",
        )
        for key in writes
        if key in deletes and str(writes[key].path) != str(deletes[key].path)
    ]
    if issues:
        return issues

    # Two write ops aimed at one path (a planner bug, MIG-03, gap CR-01): refused before the first
    # byte, so a future recurrence cannot destroy a file by silently overwriting it twice. Checked
    # before staleness/name-taken for the same reason case_twin is placed here -- this is the more
    # useful, specific code. Byte content is irrelevant: two writes for one path are a defect
    # whether the bytes match or not.
    write_paths: dict[str, MigrationOp] = {}
    duplicate_ops: dict[str, MigrationOp] = {}
    for op in plan.ops:
        if op.kind != "write":
            continue
        key = str(op.path).casefold()
        if key in write_paths:
            duplicate_ops[key] = op
        else:
            write_paths[key] = op
    issues = [
        _err(
            "migration.duplicate_write",
            f"{duplicate_ops[key].rel} has two writes queued for one file; nothing was written",
        )
        for key in sorted(duplicate_ops)
    ]
    if issues:
        return issues

    issues = []
    for op in plan.ops:
        if op.kind not in ("write", "delete") or op.base_sha256 is None:
            continue
        current = _current_hash(op)
        if current is None:
            issues.append(_err("migration.stale", f"{op.rel} could not be read. Close and open the migration again to plan with the current files."))
        elif current != op.base_sha256:
            issues.append(_err("migration.stale", f"{op.rel} changed after the preview. Close and open the migration again to plan with the current files."))
    if issues:
        return issues

    for op in plan.ops:
        if op.kind != "write" or op.base_sha256 is not None:
            continue
        names = _listed_names(op.path.parent)
        if names is not None and any(name.casefold() == op.path.name.casefold() for name in names):
            issues.append(_err("migration.name_taken", f"{op.rel} already exists; close and open the migration again"))
    return issues


# -- the KiCad load gate (D-03) ------------------------------------------------------------------


def _as_load_failed(issue: Issue) -> Issue:
    if issue.severity is Severity.ERROR:
        return Issue(Severity.ERROR, "migration.load_failed", issue.text)
    return issue


def _load_gate(plan: MigrationPlan, tools: ToolContext | None) -> list[Issue]:
    """Ask kicad-cli whether the written symbol libraries and footprints will load; writes nothing."""
    if tools is None or tools.kicad_cli is None:
        return []
    issues: list[Issue] = []
    for op in plan.ops:
        if op.kind == "write" and op.path.suffix == ".kicad_sym" and op.data is not None:
            found = load_gate(
                tools.kicad_cli,
                library=op.path.stem,
                symbol_lib=op.data,
                footprints=(),
                runner=tools.cli_runner,
                timeout=tools.cli_timeout,
            )
            issues.extend(_as_load_failed(i) for i in found)
    footprints = [
        (op.path.stem, op.data)
        for op in plan.ops
        if op.kind == "write" and op.path.suffix == ".kicad_mod" and op.data is not None
    ]
    if footprints:
        found = load_gate(
            tools.kicad_cli,
            library="",
            symbol_lib=None,
            footprints=footprints,
            runner=tools.cli_runner,
            timeout=tools.cli_timeout,
        )
        issues.extend(_as_load_failed(i) for i in found)
    return issues


# -- backups of every file this transaction will replace or delete (D-19) ------------------------


def _backup_all(plan: MigrationPlan, backup_dir: Path) -> list[Issue]:
    issues: list[Issue] = []
    for op in plan.ops:
        if op.kind == "write" and op.base_sha256 is not None:
            saved = fsutil.backup_file(op.path, backup_dir)
            if isinstance(saved, Issue):
                issues.append(_err("migration.backup_failed", saved.text))
                continue
            copy_hash = _hash_for(op.kind, op.path.suffix, saved)
            if copy_hash is None:
                issues.append(_err("migration.backup_failed", f"Could not read back the backup of {op.path.name}"))
            elif copy_hash != op.base_sha256:
                issues.append(_err("migration.stale", f"{op.rel} changed after the preview. Close and open the migration again to plan with the current files."))
        elif op.kind == "delete":
            saved = fsutil.backup_file(op.path, backup_dir)
            if isinstance(saved, Issue):
                issues.append(_err("migration.backup_failed", saved.text))
                continue
            if op.base_sha256 is not None:
                copy_hash = _hash_for(op.kind, op.path.suffix, saved)
                if copy_hash is None:
                    issues.append(_err("migration.backup_failed", f"Could not read back the backup of {op.path.name}"))
                elif copy_hash != op.base_sha256:
                    issues.append(_err("migration.stale", f"{op.rel} changed after the preview. Close and open the migration again to plan with the current files."))
    return issues


# -- freshness re-check right before each op touches it (RESEARCH P-11) --------------------------


def _still_fresh(op: MigrationOp, expected: dict[str, str | None]) -> Issue | None:
    """None when op.path is still what this transaction expects: absent, or the hash it last saw.

    A hash already in expected is always a whole-file hash: this transaction's own write branch
    records it that way. One not yet in expected is op.base_sha256, whose convention is
    kind-and-suffix dependent (see _hash_for) -- so which hash function applies depends on which
    source the value came from, not on op alone.
    """
    key = str(op.path).casefold()
    from_cache = key in expected
    want = expected[key] if from_cache else op.base_sha256
    if want is None:
        names = _listed_names(op.path.parent)
        if names is not None and any(name.casefold() == op.path.name.casefold() for name in names):
            return _err("migration.name_taken", f"{op.rel} appeared on disk while the migration was running; close and open the migration again")
        return None
    if from_cache:
        try:
            current = hashlib.sha256(op.path.read_bytes()).hexdigest()
        except OSError:
            current = None
    else:
        current = _current_hash(op)
    if current is None or current != want:
        return _err("migration.stale", f"{op.rel} changed on disk while the migration was running. Close and open the migration again to plan with the current files.")
    return None


# -- deleting a locked file: a short retry window before giving up (P-13, D-05) -------------------


def _delete_with_retry(path: Path) -> Issue | None:
    """Unlink path; a PermissionError (another process holds the file) retries for about 1s."""
    for delay in _DELETE_RETRY_DELAYS:
        try:
            path.unlink()
            return None
        except FileNotFoundError:
            return None
        except PermissionError:
            time.sleep(delay)
    try:
        path.unlink()
        return None
    except FileNotFoundError:
        return None
    except PermissionError as e:
        return _err("migration.locked", f"{path.name} is in use and could not be deleted ({e.strerror or e})")


# -- a non-empty folder a planned rmdir cannot remove is kept, never torn down (P-11) --------------


def _rmdir_or_keep(path: Path, rel: str) -> tuple[bool, Issue | None]:
    """(removed, warning): a folder that is not empty is kept in place, never recursively deleted.

    Emptiness is checked by listing first, not by catching rmdir's OSError: that error does not
    reliably distinguish "not empty" (kept, a WARNING, migration still succeeds) from any other
    OS-level failure (a real problem that must roll back the whole transaction), so only the
    FileNotFoundError race is swallowed here -- everything else propagates.
    """
    try:
        remaining = sorted(os.listdir(path))
    except FileNotFoundError:
        return True, None
    if remaining:
        names = ", ".join(remaining)
        return False, Issue(Severity.WARNING, "migration.folder_kept", f"{rel} still holds {names}; it was left in place")
    try:
        path.rmdir()
    except FileNotFoundError:
        pass
    return True, None


# -- post-write verification (RESEARCH Pattern 2) -------------------------------------------------


def _verify(plan: MigrationPlan, written: list[str], deleted: list[str], removed_dirs: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    by_rel = {op.rel: op for op in plan.ops}
    for rel in written:
        op = by_rel[rel]
        expected = op.data if op.data is not None else b""
        try:
            current = op.path.read_bytes()
        except OSError as e:
            issues.append(_err("migration.verify_failed", f"{rel} could not be read back after writing ({e.strerror or e})"))
            continue
        if current != expected:
            issues.append(_err("migration.verify_failed", f"{rel} does not hold the planned content after writing"))
    for rel in deleted:
        op = by_rel[rel]
        if op.path.exists():
            issues.append(_err("migration.verify_failed", f"{rel} still exists after the migration deleted it"))
    for rel in removed_dirs:
        op = by_rel[rel]
        if op.path.exists():
            issues.append(_err("migration.verify_failed", f"{rel} still exists after the migration removed it"))
    return issues


def apply_migration(
    plan: MigrationPlan,
    *,
    backup_root: Path | None = None,
    progress: Callable | None = None,
    before_first_write: Callable[[], list[Issue]] | None = None,
    tools: ToolContext | None = None,
) -> MigrationResult:
    """Write plan.ops in order; any failure restores every file and folder the migration touched.

    Order: preflight -> the KiCad load gate -> before_first_write (the pre-atomic tag) -> backups
    of every file about to be replaced or deleted -> the ops, each re-checked right before it runs
    -> a post-write verify -> pruning of old migration backups.
    """
    preflight_issues = _preflight(plan)
    if preflight_issues:
        return MigrationResult(False, tuple(preflight_issues), (), (), None, plan, {})

    gate_issues = _load_gate(plan, tools)
    rejected = [i for i in gate_issues if i.severity is Severity.ERROR]
    if rejected:
        return MigrationResult(False, tuple(rejected), (), (), None, plan, {})

    extra_issues: list[Issue] = [i for i in gate_issues if i.severity is not Severity.ERROR]
    if before_first_write is not None:
        pre_issues = before_first_write()
        blocking = [i for i in pre_issues if i.severity is Severity.ERROR]
        if blocking:
            return MigrationResult(False, tuple(blocking), (), (), None, plan, {})
        # Non-ERROR issues (e.g. precheck.ensure_tag's INFO "tagged"/"tag_reused") are informational
        # and carry through to the final result instead of being discarded or mistaken for a refusal.
        extra_issues.extend(pre_issues)

    backup_root = backup_root if backup_root is not None else fsutil.default_backup_dir()
    backup_dir = _backup_folder(backup_root)

    backup_issues = _backup_all(plan, backup_dir)
    if backup_issues:
        return MigrationResult(False, tuple(backup_issues), (), (), backup_dir, plan, {})

    undo: list[_Undo] = []
    written: list[str] = []
    deleted: list[str] = []
    removed_dirs: list[str] = []
    kept_issues: list[Issue] = []
    sha: dict[str, str] = {}
    expected: dict[str, str | None] = {}
    total = len(plan.ops)

    try:
        for index, op in enumerate(plan.ops):
            _notify(progress, f"{op.kind} {op.rel}", index, total)
            if op.kind in ("write", "delete"):
                stale = _still_fresh(op, expected)
                if stale is not None:
                    return _failed(plan, [stale], undo, backup_dir)
            if op.kind == "mkdir":
                op.path.mkdir(parents=True, exist_ok=True)
                undo.append(_Undo("mkdir", op.path, None))
            elif op.kind == "write":
                pre_image = op.path.read_bytes() if op.path.exists() else None
                data = op.data if op.data is not None else b""
                problem = fsutil.atomic_write_bytes(op.path, data)
                if problem is not None:
                    return _failed(plan, [problem], undo, backup_dir)
                undo.append(_Undo("write", op.path, pre_image))
                written.append(op.rel)
                digest = hashlib.sha256(data).hexdigest()
                sha[op.rel] = digest
                expected[str(op.path).casefold()] = digest
            elif op.kind == "delete":
                # Already backed up above (_backup_all), before the first write of this transaction.
                pre_image = op.path.read_bytes()
                problem = _delete_with_retry(op.path)
                if problem is not None:
                    return _failed(plan, [problem], undo, backup_dir)
                undo.append(_Undo("delete", op.path, pre_image))
                deleted.append(op.rel)
                expected[str(op.path).casefold()] = None
            elif op.kind == "rmdir":
                removed, kept = _rmdir_or_keep(op.path, op.rel)
                if removed:
                    undo.append(_Undo("rmdir", op.path, None))
                    removed_dirs.append(op.rel)
                else:
                    kept_issues.append(kept)
            else:
                return _failed(plan, [_err("migration.unknown_op", f"Unknown operation kind {op.kind!r}")], undo, backup_dir)
    except BaseException as error:
        leftovers = _rollback(undo, backup_dir)
        if not isinstance(error, Exception):
            raise
        issue = _err("migration.unexpected", f"The migration stopped unexpectedly ({type(error).__name__}: {error})")
        summary = _rolled_back_summary(undo, leftovers)
        return MigrationResult(False, (issue, *summary, *leftovers), (), (), backup_dir, plan, {})

    verify_issues = _verify(plan, written, deleted, removed_dirs)
    if verify_issues:
        return _failed(plan, verify_issues, undo, backup_dir)

    prune_issues = install_applier.prune_install_backups(
        backup_dir.parent, keep=MIGRATION_BACKUPS_KEPT, exclude=backup_dir
    )
    n_parts = len(plan.parts)
    n_libs = len({p.target_library for p in plan.parts if p.target_library})
    done = Issue(Severity.SUCCESS, "migration.done", f"Migrated {n_parts} parts into {n_libs} Atomic_ libraries")
    issues = (*extra_issues, *kept_issues, *prune_issues, done)
    return MigrationResult(True, issues, tuple(written), tuple(deleted), backup_dir, plan, sha)
