"""The atomic gate of the commit step (Phase 11, GIT-06; D-01..D-05).

Decides which parts being committed break the atomic rule. It judges the symbols of every committed
Atomic_ .kicad_sym that are new or differ from Custom's HEAD, with the unchanged atomic_check.check_symbol,
and lists each broken rule as a blocking failure naming the library, the part and the rule. Qt-free: it
reads the work tree and HEAD only and writes nothing.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .. import changes, kicad_files
from ..atomic_check import check_symbol, is_atomic
from ..gitops import GitContext
from ..models import Issue, SymbolEntry
from .commit_plan import CommitPlan
from .incoming import incoming_context
from .package import MAX_KICAD_TEXT_BYTES, MAX_KICAD_TEXT_NODES

CANCELLED = "The check was cancelled"


@dataclass(frozen=True)
class AtomicFailure:
    """One broken atomic rule of one part, in the words the panel shows."""

    library: str
    rel_path: str  # repo-relative posix path of the .kicad_sym
    part: str
    rule: str
    text: str


@dataclass(frozen=True)
class GateResult:
    """What the gate found: blocking failures, older failures, lines that stop the commit, and the entries behind them."""

    blocking: tuple[AtomicFailure, ...] = ()
    old: tuple[AtomicFailure, ...] = ()
    problems: tuple[str, ...] = ()
    entries: tuple[tuple[str, str, SymbolEntry], ...] = ()  # (library, rel_path, entry)
    notes: tuple[str, ...] = ()

    @property
    def refused(self) -> bool:
        """True when the commit must not go ahead: a blocking failure, or a library that could not be checked."""
        return bool(self.blocking or self.problems)

    @property
    def first_failure(self) -> AtomicFailure | None:
        """The failure to focus first: the first blocking one, else the first old one."""
        if self.blocking:
            return self.blocking[0]
        return self.old[0] if self.old else None


def _failures(library: str, rel_path: str, entry: SymbolEntry) -> list[AtomicFailure]:
    return [AtomicFailure(library, rel_path, entry.name, v.rule, v.text) for v in entry.violations]


def run_gate(
    ctx: GitContext,
    cplan: CommitPlan,
    kicad_fp_dir: Path | None,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> GateResult:
    """Judge the new or changed symbols of every committed Atomic_ library with the unchanged atomic rules."""
    context = incoming_context(cplan.repo_root, cplan.custom_dir / "Footprints", kicad_fp_dir)
    blocking: list[AtomicFailure] = []
    entries: list[tuple[str, str, SymbolEntry]] = []
    for cfile in cplan.files:
        library = PurePosixPath(cfile.rel).stem
        if cfile.kind != "symbol_lib" or not is_atomic(library):
            continue
        if cancelled is not None and cancelled():
            return GateResult(problems=(CANCELLED,))
        path = cplan.custom_dir / cfile.rel
        if path.stat().st_size > MAX_KICAD_TEXT_BYTES:
            continue
        loaded = kicad_files.parse_bytes(path.read_bytes(), path.name, max_nodes=MAX_KICAD_TEXT_NODES)
        if isinstance(loaded, Issue):
            continue
        rel_path = f"{cplan.custom_rel}/{cfile.rel}"
        for name in changes.symbol_changes(ctx, cplan.custom_dir, cfile.rel, loaded.root):
            entry = check_symbol(loaded.root, name, rel_path=rel_path, fixable=True, ctx=context)
            if entry.violations:
                blocking.extend(_failures(library, rel_path, entry))
                entries.append((library, rel_path, entry))
    return GateResult(blocking=tuple(blocking), entries=tuple(entries))
