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
from ..models import Issue, ScanResult, Severity, SymbolEntry, SymbolLibrary
from .commit_plan import CommitPlan
from .incoming import incoming_context
from .package import MAX_KICAD_TEXT_BYTES, MAX_KICAD_TEXT_NODES

CANCELLED = "The check was cancelled"
_MIB = 1024 * 1024


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


def _read_library(path: Path) -> tuple[kicad_files.Node | None, str]:
    """Return (parsed root, ""), or (None, why the committed library could not be checked)."""
    try:
        if path.stat().st_size > MAX_KICAD_TEXT_BYTES:
            return None, f"the file is larger than {MAX_KICAD_TEXT_BYTES // _MIB} MiB"
        data = path.read_bytes()
    except OSError as e:
        return None, f"the file could not be read ({e.strerror or e})"
    loaded = kicad_files.parse_bytes(data, path.name, max_nodes=MAX_KICAD_TEXT_NODES)
    if isinstance(loaded, Issue):
        return None, loaded.text
    return loaded.root, ""


def _with_changed_parents(root: kicad_files.Node, changed: dict[str, str]) -> set[str]:
    """The names of the changed symbols plus every symbol whose extends chain reaches one (RESEARCH Pitfall 4)."""
    index: dict[str, kicad_files.SymbolRef] = {}
    for ref in kicad_files.find_symbols(root):
        index.setdefault(ref.name, ref)
    judged = set(changed)
    for name, ref in index.items():
        seen = {name}
        parent = kicad_files.extends_name(ref.node)
        while parent is not None and parent not in seen:
            if parent in judged:
                judged.add(name)
                break
            seen.add(parent)
            found = index.get(parent)
            parent = kicad_files.extends_name(found.node) if found is not None else None
    return judged


def run_gate(
    ctx: GitContext,
    cplan: CommitPlan,
    kicad_fp_dir: Path | None,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> GateResult:
    """Judge every symbol of each committed Atomic_ library with the unchanged atomic rules.

    A symbol that is new, differs from HEAD, or extends one that does is judged as changed and its
    broken rules block (D-01, D-05); an unchanged symbol that fails is only noted (D-02). A committed
    library that cannot be read refuses the commit rather than passing it.
    """
    context = incoming_context(cplan.repo_root, cplan.custom_dir / "Footprints", kicad_fp_dir)
    blocking: list[AtomicFailure] = []
    old: list[AtomicFailure] = []
    problems: list[str] = []
    entries: list[tuple[str, str, SymbolEntry]] = []
    for cfile in cplan.files:
        library = PurePosixPath(cfile.rel).stem
        if cfile.kind != "symbol_lib" or not is_atomic(library):
            continue
        if cancelled is not None and cancelled():
            return GateResult(problems=(CANCELLED,))
        root, why = _read_library(cplan.custom_dir / cfile.rel)
        if root is None:
            problems.append(f"{library}: the library could not be checked ({why})")
            continue
        rel_path = f"{cplan.custom_rel}/{cfile.rel}"
        judged = _with_changed_parents(root, changes.symbol_changes(ctx, cplan.custom_dir, cfile.rel, root))
        seen: set[str] = set()
        for ref in kicad_files.find_symbols(root):
            if ref.name in seen:
                continue
            seen.add(ref.name)
            entry = check_symbol(root, ref.name, rel_path=rel_path, fixable=True, ctx=context)
            if not entry.violations:
                continue
            (blocking if ref.name in judged else old).extend(_failures(library, rel_path, entry))
            entries.append((library, rel_path, entry))
    return GateResult(
        blocking=tuple(blocking), old=tuple(old), problems=tuple(problems), entries=tuple(entries)
    )


def _plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def refusal_summary(gate: GateResult) -> str:
    """The strip text of a refused commit: how many parts break the rule and how many libraries were not checked."""
    if not gate.refused:
        return ""
    parts: list[str] = []
    broken = len({(f.library, f.part) for f in gate.blocking})
    if broken:
        parts.append(f"{broken} part breaks the atomic rule" if broken == 1 else f"{broken} parts break the atomic rule")
    if gate.problems:
        parts.append(f"{_plural(len(gate.problems), 'library', 'libraries')} could not be checked")
    return "; ".join(parts)


def _line(failure: AtomicFailure) -> str:
    return f"{failure.library} / {failure.part}: {failure.text}"


def failure_lines(gate: GateResult) -> list[str]:
    """One "Library / Part: reason" line per broken rule, then the libraries that could not be checked (D-06)."""
    return [*(_line(f) for f in gate.blocking), *gate.problems]


def old_notes(gate: GateResult) -> list[str]:
    """One note per library that holds parts which already failed before this import (D-02)."""
    counts: dict[str, set[str]] = {}
    for failure in gate.old:
        counts.setdefault(failure.library, set()).add(failure.part)
    return [
        f"{library} also holds {_plural(len(parts), 'part', 'parts')} that already failed before this import"
        for library, parts in counts.items()
    ]


def gate_issues(gate: GateResult) -> list[Issue]:
    """The log lines of the gate, in the Phase 9 D-05 shape: blocking, old, unreadable, then notes."""
    issues = [Issue(Severity.ERROR, f"commit.atomic.{f.rule}", _line(f)) for f in gate.blocking]
    issues.extend(Issue(Severity.WARNING, f"commit.atomic_old.{f.rule}", _line(f)) for f in gate.old)
    issues.extend(Issue(Severity.ERROR, "commit.atomic_unreadable", problem) for problem in gate.problems)
    issues.extend(Issue(Severity.INFO, "commit.atomic_note", note) for note in gate.notes)
    return issues


def scan_result_for(gate: GateResult) -> ScanResult:
    """A ScanResult holding the failing symbols, so the Check Atomic Parts dialog can show and fix them (D-07)."""
    libraries: dict[str, SymbolLibrary] = {}
    for library, rel_path, entry in gate.entries:
        lib = libraries.get(rel_path)
        if lib is None:
            lib = libraries[rel_path] = SymbolLibrary(nickname=library, rel_path=rel_path, source="Custom", atomic=True)
        lib.symbols.append(entry)
    return ScanResult(symbol_libs=list(libraries.values()))
