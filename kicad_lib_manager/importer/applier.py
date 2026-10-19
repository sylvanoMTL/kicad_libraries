"""Carry out an InstallPlan as one transaction: back up, write in order, verify, undo on any failure (D-18, D-19).

fsutil and verify are called through their module attributes so tests can inject a failure
at any write (the same seam table_generator.write_tables uses).
"""

import hashlib
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from .. import fsutil
from ..models import Issue, Severity
from . import verify
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


def _undo(undo: list[tuple[str, Path, bytes | None]], backup_dir: Path | None) -> list[Issue]:
    """Reverse the writes made so far; keep going past a failed step and report every leftover."""
    leftovers: list[Issue] = []
    where = f" (backups are in {backup_dir})" if backup_dir is not None else ""
    for kind, path, pre_image in reversed(undo):
        try:
            if kind == "mkdir":
                path.rmdir()
            elif pre_image is None:
                path.unlink(missing_ok=True)
            else:
                problem = fsutil.atomic_write_bytes(path, pre_image)
                if problem is not None:
                    leftovers.append(_err("install.rollback_failed", f"Could not restore {path}: {problem.text}{where}"))
        except OSError as e:
            leftovers.append(_err("install.rollback_failed", f"Could not undo {path}: {e.strerror or e}{where}"))
    return leftovers


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
    if not plan.ops:
        return _result(plan, True, [*plan.issues, Issue(Severity.INFO, "install.nothing_to_do", "Everything is already installed")])

    # Preconditions: nothing is written until every one of these holds
    custom = plan.layout.custom_dir.resolve()
    sources: dict[int, bytes] = {}
    pre_images: dict[int, bytes | None] = {}
    for index, op in enumerate(plan.ops):
        if not op.path.resolve().is_relative_to(custom):
            return _result(plan, False, [_err("install.path_outside_custom", f"{op.path} is outside {custom}")])
        if op.source is not None:
            try:
                data = op.source.path.read_bytes()
            except OSError as e:
                return _result(plan, False, [_err("install.source_gone", f"Could not read {op.source.member}: {e.strerror or e}")])
            if hashlib.sha256(data).hexdigest() != op.source.sha256:
                return _result(plan, False, [_err("install.source_changed", f"{op.source.member} changed after the package was opened")])
            sources[index] = data
        if op.kind == "mkdir":
            continue
        if op.base_sha256 is None:
            if op.path.exists():
                return _result(plan, False, [_err("install.stale_plan", f"{op.path.name} appeared after the plan was made; rebuild the plan")])
            pre_images[index] = None
        else:
            try:
                current = op.path.read_bytes()
            except OSError as e:
                return _result(plan, False, [_err("install.stale_plan", f"Could not read {op.path.name}: {e.strerror or e}")])
            if hashlib.sha256(current).hexdigest() != op.base_sha256:
                return _result(plan, False, [_err("install.stale_plan", f"{op.path.name} changed after the plan was made; rebuild the plan")])
            pre_images[index] = current

    # Back up every existing file the install changes, before the first write
    backup_dir: Path | None = None
    if any(op.base_sha256 is not None for op in plan.ops):
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", plan.library)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        root = backup_root if backup_root is not None else fsutil.default_backup_dir()
        backup_dir = root / "installs" / f"{stamp}_{safe}"
        for op in plan.ops:
            if op.base_sha256 is None:
                continue
            saved = fsutil.backup_file(op.path, backup_dir)
            if isinstance(saved, Issue):
                return _result(plan, False, [saved])

    # Writes in plan order; an entry reaches the undo list only after its write succeeded
    undo: list[tuple[str, Path, bytes | None]] = []
    touched: list[Path] = []
    failures: list[Issue] = []
    total = len(plan.ops)
    for index, op in enumerate(plan.ops):
        if progress is not None:
            progress(f"Writing {op.path.name}", index, total)
        problem = _write(op, sources.get(index), undo, touched, pre_images.get(index))
        if problem is not None:
            failures.append(problem)
            break
    if not failures:
        failures.extend(i for i in verify.verify_install(plan) if i.severity is Severity.ERROR)
    if failures:
        leftovers = _undo(undo, backup_dir)
        return _result(
            plan,
            False,
            [*failures, _err("install.rolled_back", "The install failed and every change was undone"), *leftovers],
            backup_dir=backup_dir,
        )

    issues = [*plan.issues]
    if plan.tools.kicad_cli is None:
        issues.append(Issue(Severity.INFO, "install.cli_not_found", "kicad-cli was not found, so the KiCad load check was skipped"))
    issues.append(Issue(Severity.SUCCESS, "install.done", f"Installed {plan.symbol_name} into {plan.library}"))
    return _result(plan, True, issues, touched=touched, backup_dir=backup_dir)


def _write(
    op: FileOp,
    source_bytes: bytes | None,
    undo: list[tuple[str, Path, bytes | None]],
    touched: list[Path],
    pre_image: bytes | None,
) -> Issue | None:
    """Perform one op and record how to undo it; return an Issue when it failed."""
    if op.kind == "mkdir":
        try:
            op.path.mkdir()
        except OSError as e:
            return _err("fs.write_failed", f"Could not create {op.path.name}: {e.strerror or e}")
        undo.append(("mkdir", op.path, None))
        return None
    data = source_bytes if source_bytes is not None else op.data
    problem = fsutil.atomic_write_bytes(op.path, data)
    if problem is not None:
        return problem
    # The pre-image goes back under the spelling the file had on disk
    undo.append(("file", op.listed_path or op.path, pre_image))
    touched.append(op.path)
    return None
