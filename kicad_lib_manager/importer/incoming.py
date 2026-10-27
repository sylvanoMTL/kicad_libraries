"""The Phase 9 atomic check applied to a part before it is written (D-21).

A leaf of the importer: no Qt. It builds the check's context from the footprint and 3D model a plan is
about to write, then runs the unchanged check_symbol on the planned symbol bytes. Nothing is read twice
and nothing is written: Install is blocked on the same rules the scan applies to the finished library.
"""

import os
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path

from .. import kicad_files
from ..atomic_check import AtomicContext, check_symbol, repo_context
from ..models import FootprintLibrary, Issue, Severity

_NO_PLANNED_FOOTPRINTS: Mapping[str, tuple[str, bytes]] = {}


def incoming_context(
    repo_root: Path,
    footprints_dir: Path,
    kicad_fp_dir: Path | None,
    *,
    planned_footprints: Mapping[str, tuple[str, bytes]] = _NO_PLANNED_FOOTPRINTS,
    planned_models: Collection[str] = (),
) -> AtomicContext:
    """Build the check context for an incoming part.

    The footprint libraries are the .pretty folders of Custom/Footprints (footprints_dir) and KiCad's
    installed ones; planned_footprints and planned_models are what the plan is about to write.
    """
    rel = footprints_dir.relative_to(repo_root).as_posix()
    try:
        listed = sorted(os.listdir(footprints_dir))
    except OSError:
        listed = []
    fp_libs = [
        FootprintLibrary(name[: -len(".pretty")], f"{rel}/{name}", "Custom")
        for name in listed
        if name.endswith(".pretty")
    ]
    return repo_context(
        repo_root, fp_libs, kicad_fp_dir, planned_footprints=planned_footprints, planned_models=planned_models
    )


def incoming_issues(root: kicad_files.Node, names: Sequence[str], *, rel_path: str, ctx: AtomicContext) -> list[Issue]:
    """Judge the named symbols of a planned .kicad_sym and return one Issue per broken rule.

    A broken rule is an ERROR install.atomic.<rule>, in the check's rule order; a note about a symbol
    (an unknown manufacturer, leftover price data) is an INFO install.atomic_note.<kind>. The last name
    is the part being installed and its text stands alone; the others (a parent symbol) are prefixed
    with their name.
    """
    issues: list[Issue] = []
    for position, name in enumerate(names):
        prefix = "" if position == len(names) - 1 else f"{name}: "
        entry = check_symbol(root, name, rel_path=rel_path, fixable=False, ctx=ctx)
        for violation in entry.violations:
            issues.append(Issue(Severity.ERROR, f"install.atomic.{violation.rule}", prefix + violation.text))
        for finding in entry.findings:
            issues.append(Issue(Severity.INFO, f"install.atomic_note.{finding.kind}", prefix + finding.text))
    return issues
