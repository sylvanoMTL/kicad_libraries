"""Carry out an InstallPlan as one transaction: back up, write in order, verify, undo on any failure (D-18, D-19).

fsutil and verify are called through their module attributes so tests can inject a failure
at any write (the same seam table_generator.write_tables uses).
"""

import hashlib
import os
import re
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

from .. import fsutil
from ..models import Issue, Severity
from . import kicad_cli, verify
from .plan import FileOp, InstallPlan, InstallResult


def _err(code: str, text: str) -> Issue:
    return Issue(Severity.ERROR, code, text)


def _result(plan: InstallPlan, ok: bool, issues, touched=(), backup_dir=None) -> InstallResult:
    return InstallResult(
        ok=ok,
        library=plan.library,
        new_library=plan.new_library,
        touched=tuple(touched),
        issues=tuple(issues),
        backup_dir=backup_dir,
        vendor=plan.vendor,
        source=plan.source,
    )


INSTALL_BACKUPS_KEPT = 10
_BACKUP_FOLDER_RE = re.compile(r"(\d{8})-(\d{6})(?:-(\d+))?_.+")


class _Undo(NamedTuple):
    """How to reverse one step: restore is the on-disk spelling, written is what the install wrote."""

    kind: str  # "file" | "mkdir"
    restore: Path
    written: Path
    pre_image: bytes | None


def _rollback_failed(text: str) -> Issue:
    return _err("install.rollback_failed", text)


def _drop_twin(step: _Undo) -> None:
    """After a restore, remove the file written under another spelling when both spellings now coexist."""
    if step.written.name == step.restore.name:
        return
    names = os.listdir(step.written.parent)
    if step.written.name in names and step.restore.name in names:
        step.written.unlink()


def _rollback(undo: list[_Undo], backup_dir: Path | None) -> list[Issue]:
    """Reverse the writes in reverse order; keep going past a failed step and report every leftover (INST-07)."""
    leftovers: list[Issue] = []
    where = f"; the original is in {backup_dir}" if backup_dir is not None else ""
    # Several writes to one path restore once, from the earliest pre-image
    first: dict[str, _Undo] = {}
    for step in undo:
        if step.kind == "file":
            first.setdefault(str(step.restore).casefold(), step)
    for step in reversed(undo):
        if step.kind == "file" and first[str(step.restore).casefold()] is not step:
            continue
        try:
            if step.kind == "mkdir":
                step.written.rmdir()
            elif step.pre_image is None:
                step.written.unlink(missing_ok=True)
            else:
                problem = fsutil.atomic_write_bytes(step.restore, step.pre_image)
                if problem is not None:
                    leftovers.append(_rollback_failed(f"{step.restore} could not be restored ({problem.text}){where}"))
                _drop_twin(step)
        except FileNotFoundError:
            continue
        except OSError as e:
            what = "restored" if step.pre_image is not None else "removed"
            leftovers.append(_rollback_failed(f"{step.written} could not be {what} ({e.strerror or e}){where}"))
    return leftovers


def prune_install_backups(installs_dir: Path, keep: int = INSTALL_BACKUPS_KEPT) -> list[Issue]:
    """Keep the newest `keep` install backup folders and delete the rest (D-19).

    Only direct child folders named <YYYYmmdd>-<HHMMSS>[-<n>]_<library> are candidates, and a
    link whose target lies elsewhere is never followed; anything else in installs_dir is left alone.
    """
    try:
        root = installs_dir.resolve()
        children = list(installs_dir.iterdir())
    except OSError as e:
        return [Issue(Severity.WARNING, "install.backup_prune_failed", f"Could not list the install backups in {installs_dir}: {e.strerror or e}")]
    is_junction = getattr(os.path, "isjunction", lambda path: False)
    found = []
    for child in children:
        match = _BACKUP_FOLDER_RE.fullmatch(child.name)
        if match is None:
            continue
        try:
            if child.is_symlink() or is_junction(child) or not child.is_dir() or child.resolve().parent != root:
                continue
        except OSError:
            continue
        # A suffix-less name is the first of its second, so -2 is newer than none
        found.append(((match[1], match[2], int(match[3] or 1), child.name), child))
    found.sort(key=lambda item: item[0], reverse=True)
    issues: list[Issue] = []
    for _, child in found[max(keep, 0):]:
        try:
            shutil.rmtree(child)
        except OSError as e:
            issues.append(Issue(Severity.WARNING, "install.backup_prune_failed", f"Could not delete the old install backup {child.name}: {e.strerror or e}"))
    return issues


def _backup_folder(root: Path, library: str) -> Path:
    """installs/<timestamp>_<library>, with -2, -3 ... after the timestamp when the name is taken."""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", library)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    installs = root / "installs"
    number = 1
    while True:
        suffix = "" if number == 1 else f"-{number}"
        folder = installs / f"{stamp}{suffix}_{safe}"
        if not folder.exists():
            return folder
        number += 1


def _name_taken(path: Path) -> bool:
    """True when path, or a name differing from it only by letter case, is in its parent folder (exact-case listing)."""
    try:
        names = os.listdir(path.parent)
    except OSError:
        return False
    wanted = path.name.casefold()
    return any(name.casefold() == wanted for name in names)


def _current_bytes(op: FileOp) -> bytes | Issue:
    """The bytes on disk at the spelling the plan was built from."""
    path = op.listed_path or op.path
    try:
        return path.read_bytes()
    except OSError as e:
        return _err("install.stale_plan", f"Could not read {path.name}: {e.strerror or e}; rebuild the plan")


def _gate(plan: InstallPlan, original_symbol_lib: bytes | None) -> list[Issue]:
    exe = plan.tools.kicad_cli
    if exe is None:
        return [Issue(Severity.INFO, "install.cli_not_found", "kicad-cli was not found, so the KiCad load check was skipped")]
    symbol_op = next((op for op in plan.ops if op.kind == "symbol_lib"), None)
    footprints = [(op.path.stem, op.data) for op in plan.ops if op.kind == "footprint" and op.data is not None]
    if symbol_op is None and not footprints:
        return []
    return kicad_cli.load_gate(
        exe,
        library=plan.library,
        symbol_lib=symbol_op.data if symbol_op is not None else None,
        footprints=footprints,
        original_symbol_lib=original_symbol_lib if symbol_op is not None and symbol_op.base_sha256 is not None else None,
        runner=plan.tools.cli_runner,
        timeout=plan.tools.cli_timeout,
    )


def run_load_gate(plan: InstallPlan) -> list[Issue]:
    """Ask kicad-cli whether KiCad can load the planned symbol library and footprints; writes nothing (D-03).

    Without kicad-cli the result is one INFO install.cli_not_found. Any ERROR means KiCad rejected the result.
    """
    original = None
    symbol_op = next((op for op in plan.ops if op.kind == "symbol_lib" and op.base_sha256 is not None), None)
    if symbol_op is not None and plan.tools.kicad_cli is not None:
        current = _current_bytes(symbol_op)
        original = current if isinstance(current, bytes) else None
    return _gate(plan, original)


def _preflight(plan: InstallPlan) -> tuple[list[Issue], dict[int, bytes], dict[int, bytes | None]]:
    """Check containment, freshness and the staged sources; return the issues, source bytes and pre-images.

    Each pass reports every problem it finds, and a failing pass stops the next one, so the
    caller sees the cheapest explanation first and nothing has been written.
    """
    custom = plan.layout.custom_dir.resolve()
    issues: list[Issue] = []
    for op in plan.ops:
        for path in {op.path, op.listed_path or op.path}:
            if not path.resolve().is_relative_to(custom):
                issues.append(_err("install.path_outside_custom", f"{path} is outside {custom}"))
    if issues:
        return issues, {}, {}

    pre_images: dict[int, bytes | None] = {}
    for index, op in enumerate(plan.ops):
        if op.base_sha256 is None:
            if _name_taken(op.path):
                issues.append(_err("install.stale_plan", f"{op.path.name} appeared after the preview was built; rebuild the plan"))
            pre_images[index] = None
            continue
        current = _current_bytes(op)
        if isinstance(current, Issue):
            issues.append(current)
        elif hashlib.sha256(current).hexdigest() != op.base_sha256:
            issues.append(_err("install.stale_plan", f"{op.path.name} changed on disk after the preview was built; rebuild the plan"))
        else:
            pre_images[index] = current
    if issues:
        return issues, {}, {}

    sources: dict[int, bytes] = {}
    for index, op in enumerate(plan.ops):
        if op.source is None:
            continue
        try:
            data = op.source.path.read_bytes()
        except OSError as e:
            issues.append(_err("install.source_gone", f"Could not read {op.source.member}: {e.strerror or e}"))
            continue
        if hashlib.sha256(data).hexdigest() != op.source.sha256:
            issues.append(_err("install.source_changed", f"{op.source.member} changed after the package was opened"))
            continue
        sources[index] = data
    return issues, sources, pre_images


def apply_plan(
    plan: InstallPlan,
    *,
    backup_root: Path | None = None,
    progress: Callable | None = None,
) -> InstallResult:
    """Write the plan to disk; any failure restores every file the install touched."""
    if plan.blocked:
        issues = [i for i in plan.issues if i.severity is Severity.ERROR]
        unresolved = plan.unresolved_conflicts
        if unresolved:
            keys = ", ".join(c.key for c in unresolved)
            issues.append(_err("install.conflict_unresolved", f"Unresolved conflicts: {keys}"))
        return _result(plan, False, issues)
    if plan.is_noop:
        return _result(plan, True, [*plan.issues, Issue(Severity.INFO, "install.nothing_to_do", "Everything is already installed")])

    # Cheap preconditions first; nothing is written until every one of them holds
    problems, sources, pre_images = _preflight(plan)
    if problems:
        return _result(plan, False, problems)

    # D-03: KiCad must be able to load the result before the first backup or write
    symbol_index = next((i for i, op in enumerate(plan.ops) if op.kind == "symbol_lib"), None)
    original = pre_images.get(symbol_index) if symbol_index is not None else None
    gate = _gate(plan, original)
    rejected = [i for i in gate if i.severity is Severity.ERROR]
    if rejected:
        return _result(plan, False, rejected)

    # D-19: every existing file the install changes is backed up before the first write
    backup_dir: Path | None = None
    housekeeping: list[Issue] = []
    if any(op.base_sha256 is not None for op in plan.ops):
        root = backup_root if backup_root is not None else fsutil.default_backup_dir()
        backup_dir = _backup_folder(root, plan.library)
        for op in plan.ops:
            if op.base_sha256 is None:
                continue
            saved = fsutil.backup_file(op.listed_path or op.path, backup_dir)
            if isinstance(saved, Issue):
                return _result(plan, False, [saved])
        housekeeping = prune_install_backups(backup_dir.parent)

    # Writes in plan order; an entry reaches the undo list only after its write succeeded
    undo: list[_Undo] = []
    touched: list[Path] = []
    failures: list[Issue] = []
    total = len(plan.ops)
    for index, op in enumerate(plan.ops):
        if progress is not None:
            progress(f"Writing {op.path.name}", index, total)
        problem = _write(plan, op, sources.get(index), undo, touched, pre_images.get(index))
        if problem is not None:
            failures.append(problem)
            break
    warnings: list[Issue] = []
    if not failures:
        checked = verify.verify_install(plan)
        failures.extend(i for i in checked if i.severity is Severity.ERROR)
        warnings = [i for i in checked if i.severity is not Severity.ERROR]
    if failures:
        leftovers = _rollback(undo, backup_dir)
        cause = failures[0].text
        summary = "some files could not be restored" if leftovers else "every change was undone"
        return _result(
            plan,
            False,
            [*failures, _err("install.rolled_back", f"The install failed ({cause}); {summary}"), *leftovers, *housekeeping],
            backup_dir=backup_dir,
        )

    issues = [*plan.issues]
    known = {i.code for i in issues}
    issues.extend(i for i in gate if i.code not in known)
    issues.extend(housekeeping)
    issues.extend(warnings)
    issues.append(Issue(Severity.SUCCESS, "install.done", f"Installed {plan.symbol_name} into {plan.library}"))
    return _result(plan, True, issues, touched=touched, backup_dir=backup_dir)


def _make_folders(plan: InstallPlan, op: FileOp, undo: list[_Undo]) -> Issue | None:
    """Create op.path and any missing parents below Custom/, recording each folder for the rollback."""
    custom = plan.layout.custom_dir.resolve()
    missing: list[Path] = []
    folder = op.path
    while not folder.exists() and folder != folder.parent:
        missing.append(folder)
        folder = folder.parent
    for folder in reversed(missing):
        resolved = folder.resolve()
        if resolved == custom or not resolved.is_relative_to(custom):
            return _err("fs.write_failed", f"Could not create {op.path.name}: {custom} does not exist")
        try:
            folder.mkdir()
        except OSError as e:
            return _err("fs.write_failed", f"Could not create {folder.name}: {e.strerror or e}")
        undo.append(_Undo("mkdir", folder, folder, None))
    return None


def _write(
    plan: InstallPlan,
    op: FileOp,
    source_bytes: bytes | None,
    undo: list[_Undo],
    touched: list[Path],
    pre_image: bytes | None,
) -> Issue | None:
    """Perform one op and record how to undo it; return an Issue when it failed."""
    if op.kind == "mkdir":
        return _make_folders(plan, op, undo)
    data = source_bytes if source_bytes is not None else op.data
    if data is None:
        return _err("fs.write_failed", f"Could not write {op.path.name}: the plan carries no content for it")
    problem = fsutil.atomic_write_bytes(op.path, data)
    if problem is not None:
        return problem
    # The pre-image goes back under the spelling the file had on disk
    undo.append(_Undo("file", op.listed_path or op.path, op.path, pre_image))
    touched.append(op.path)
    return None
