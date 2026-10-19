"""Carry out an InstallPlan as one transaction: back up, write in order, verify, undo on any failure (D-18, D-19).

fsutil and verify are called through their module attributes so tests can inject a failure
at any write (the same seam table_generator.write_tables uses).
"""

import hashlib
import os
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

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
    warnings: list[Issue] = []
    if not failures:
        checked = verify.verify_install(plan)
        failures.extend(i for i in checked if i.severity is Severity.ERROR)
        warnings = [i for i in checked if i.severity is not Severity.ERROR]
    if failures:
        leftovers = _undo(undo, backup_dir)
        return _result(
            plan,
            False,
            [*failures, _err("install.rolled_back", "The install failed and every change was undone"), *leftovers],
            backup_dir=backup_dir,
        )

    issues = [*plan.issues]
    known = {i.code for i in issues}
    issues.extend(i for i in gate if i.code not in known)
    issues.extend(warnings)
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
