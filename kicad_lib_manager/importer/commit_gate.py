"""The atomic gate of the commit step (Phase 11, GIT-06; D-01..D-05).

Decides which parts being committed break the atomic rule. It judges the symbols of every committed
Atomic_ .kicad_sym that are new or differ from Custom's HEAD, with the unchanged atomic_check.check_symbol,
and lists each broken rule as a blocking failure naming the library, the part and the rule. Qt-free: it
reads the work tree and HEAD only and writes nothing.

A committed footprint or 3D model can break parts whose library is not in the commit (D-04). Every Atomic_
symbol that links a committed footprint, or a footprint that names a committed model, is checked in the
work tree and again in a HEAD view in which the committed footprints hold their HEAD bytes (or are absent
when new). Only a violation the HEAD view does not have blocks; one present in both views is an older
failure (D-02). Model existence is read from the work tree in both views (RESEARCH A4), so a committed
model file can never make a part fail by itself: committing a file never removes one. The symbols that
link a committed model are still checked, and their failures are listed as older.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .. import changes, gitops, kicad_files
from ..atomic_check import CUSTOM_MODEL_PREFIX, AtomicContext, FootprintTarget, check_symbol, is_atomic
from ..gitops import GitContext
from ..models import Issue, ScanResult, Severity, SymbolEntry, SymbolLibrary, Violation
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


def _footprint_text(ref: kicad_files.SymbolRef, index: dict[str, kicad_files.SymbolRef]) -> str:
    """The Footprint value a symbol uses: its own, else the nearest extends ancestor that declares one."""
    seen = {ref.name}
    current: kicad_files.SymbolRef | None = ref
    while current is not None:
        prop = kicad_files.find_property(current.node, "Footprint")
        if prop is not None:
            return prop.value
        parent = kicad_files.extends_name(current.node)
        if parent is None or parent in seen:
            return ""
        seen.add(parent)
        current = index.get(parent)
    return ""


def _footprint_models(path: Path, cache: dict[Path, tuple[str, ...]]) -> tuple[str, ...]:
    """The model paths of one footprint file; empty when it cannot be read. Read once per path, capped."""
    found = cache.get(path)
    if found is None:
        root, _ = _read_library(path)
        named = kicad_files.footprint_name(root) if root is not None else None
        found = tuple(model.path for model in kicad_files.find_models(named.node)) if named is not None else ()
        cache[path] = found
    return found


def _introduced(work: list[Violation], head: list[Violation]) -> tuple[list[Violation], list[Violation]]:
    """Split the work-view violations into (blocking, old): old ones also exist, same rule and text, in the HEAD view."""
    before = {(v.rule, v.text) for v in head}
    blocking = [v for v in work if (v.rule, v.text) not in before]
    old = [v for v in work if (v.rule, v.text) in before]
    return blocking, old


def _head_view_context(
    ctx: GitContext, cplan: CommitPlan, kicad_fp_dir: Path | None, committed_footprints: dict[str, str]
) -> AtomicContext:
    """The check context as HEAD saw the footprints: committed ones hold their HEAD bytes, new ones are absent.

    committed_footprints maps a Library:Footprint link to its path relative to Custom. Model existence is
    still read from the work tree (RESEARCH A4).
    """
    planned: dict[str, tuple[str, bytes]] = {}
    absent: set[str] = set()
    for link, rel in committed_footprints.items():
        data = gitops.head_blob(ctx, cplan.custom_dir, rel)
        if data is None:
            absent.add(link)
        else:
            planned[link] = (f"{cplan.custom_rel}/{rel}", data)
    base = incoming_context(cplan.repo_root, cplan.custom_dir / "Footprints", kicad_fp_dir, planned_footprints=planned)

    def resolve(text: str) -> FootprintTarget:
        if text in absent:
            library, _, name = text.partition(":")
            return FootprintTarget(text, library, name, None, None, f'footprint "{name}" is not in library "{library}"')
        return base.resolve_footprint(text)

    return AtomicContext(resolve, base.model_problems)


def _committed_footprints(cplan: CommitPlan) -> dict[str, str]:
    """Each committed Footprints/<Lib>.pretty/<Name>.kicad_mod as {"Lib:Name": path relative to Custom}."""
    found: dict[str, str] = {}
    for cfile in cplan.files:
        parts = PurePosixPath(cfile.rel).parts
        if cfile.kind != "footprint" or len(parts) != 3 or parts[0] != "Footprints":
            continue
        pretty, mod = parts[1], parts[2]
        if pretty.endswith(".pretty") and mod.endswith(".kicad_mod"):
            found[f"{pretty[: -len('.pretty')]}:{mod[: -len('.kicad_mod')]}"] = cfile.rel
    return found


def _committed_models(cplan: CommitPlan) -> frozenset[str]:
    """The committed 3D model files as names relative to 3DModels/."""
    prefix = "3DModels/"
    return frozenset(c.rel[len(prefix):] for c in cplan.files if c.kind == "model" and c.rel.startswith(prefix))


def _atomic_symbol_files(custom_dir: Path) -> list[str]:
    """File names of the Atomic_ symbol libraries under Custom/Symbols, in name order."""
    try:
        names = sorted(os.listdir(custom_dir / "Symbols"))
    except OSError:
        return []
    return [name for name in names if name.endswith(".kicad_sym") and is_atomic(name[: -len(".kicad_sym")])]


def _check_linked_symbols(
    ctx: GitContext,
    cplan: CommitPlan,
    kicad_fp_dir: Path | None,
    work: AtomicContext,
    footprints: dict[str, str],
    models: frozenset[str],
    committed: dict[str, tuple[kicad_files.Node | None, set[str]]],
    cancelled: Callable[[], bool] | None,
    blocking: list[AtomicFailure],
    old: list[AtomicFailure],
    notes: list[str],
    entries: list[tuple[str, str, SymbolEntry]],
) -> bool:
    """Judge the symbols that link a committed footprint or model (D-04); True when the check was cancelled.

    A symbol that fails in the work tree has its violations split against the HEAD view: the ones HEAD
    did not have block, the rest are old. Changed symbols of committed libraries were judged already.
    """
    linked_rels = {f"{cplan.custom_rel}/{rel}" for rel in footprints.values()}
    head: AtomicContext | None = None
    model_cache: dict[Path, tuple[str, ...]] = {}
    for file_name in _atomic_symbol_files(cplan.custom_dir):
        if cancelled is not None and cancelled():
            return True
        library = file_name[: -len(".kicad_sym")]
        known = committed.get(file_name.casefold())
        judged: set[str] = set()
        if known is not None:
            root, judged = known
        else:
            root, why = _read_library(cplan.custom_dir / "Symbols" / file_name)
            if root is None:
                notes.append(f"Could not check the parts of {library} that link the committed files ({why})")
        if root is None:
            continue
        rel_path = f"{cplan.custom_rel}/Symbols/{file_name}"
        index: dict[str, kicad_files.SymbolRef] = {}
        for ref in kicad_files.find_symbols(root):
            index.setdefault(ref.name, ref)
        for name, ref in index.items():
            if name in judged:
                continue
            target = work.resolve_footprint(_footprint_text(ref, index))
            if target.problem is not None:
                continue
            linked = target.rel_path in linked_rels
            if not linked and models and target.rel_path is not None and target.path is not None:
                names = _footprint_models(target.path, model_cache)
                linked = any(p.startswith(CUSTOM_MODEL_PREFIX) and p[len(CUSTOM_MODEL_PREFIX):] in models for p in names)
            if not linked:
                continue
            entry = check_symbol(root, name, rel_path=rel_path, fixable=True, ctx=work)
            if not entry.violations:
                continue
            if head is None:
                head = _head_view_context(ctx, cplan, kicad_fp_dir, footprints)
            before = check_symbol(root, name, rel_path=rel_path, fixable=False, ctx=head)
            introduced, older = _introduced(entry.violations, before.violations)
            listed = any(f.rel_path == rel_path and f.part == name for f in old)
            if listed and not introduced:
                continue  # an unchanged symbol of a committed library, already listed as old
            # An unchanged symbol of a committed library listed as old is moved, not listed twice
            old[:] = [f for f in old if (f.rel_path, f.part) != (rel_path, name)]
            entries[:] = [e for e in entries if (e[1], e[2].name) != (rel_path, name)]
            blocking.extend(AtomicFailure(library, rel_path, name, v.rule, v.text) for v in introduced)
            old.extend(AtomicFailure(library, rel_path, name, v.rule, v.text) for v in older)
            entries.append((library, rel_path, entry))
    return False


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
    library that cannot be read refuses the commit rather than passing it. A committed footprint or
    3D model also judges the symbols that link it, in any Atomic_ library (D-04).
    """
    context = incoming_context(cplan.repo_root, cplan.custom_dir / "Footprints", kicad_fp_dir)
    blocking: list[AtomicFailure] = []
    old: list[AtomicFailure] = []
    problems: list[str] = []
    notes: list[str] = []
    entries: list[tuple[str, str, SymbolEntry]] = []
    # file name (casefolded) -> (parsed root or None, names judged as changed) of each committed library
    committed: dict[str, tuple[kicad_files.Node | None, set[str]]] = {}
    for cfile in cplan.files:
        library = PurePosixPath(cfile.rel).stem
        if cfile.kind != "symbol_lib" or not is_atomic(library):
            continue
        if cancelled is not None and cancelled():
            return GateResult(problems=(CANCELLED,))
        root, why = _read_library(cplan.custom_dir / cfile.rel)
        key = PurePosixPath(cfile.rel).name.casefold()
        committed[key] = (root, set())
        if root is None:
            problems.append(f"{library}: the library could not be checked ({why})")
            continue
        rel_path = f"{cplan.custom_rel}/{cfile.rel}"
        judged = _with_changed_parents(root, changes.symbol_changes(ctx, cplan.custom_dir, cfile.rel, root))
        committed[key] = (root, judged)
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

    footprints = _committed_footprints(cplan)
    models = _committed_models(cplan)
    if footprints or models:
        if _check_linked_symbols(
            ctx, cplan, kicad_fp_dir, context, footprints, models, committed, cancelled, blocking, old, notes, entries
        ):
            return GateResult(problems=(CANCELLED,))
    return GateResult(
        blocking=tuple(blocking), old=tuple(old), problems=tuple(problems), entries=tuple(entries), notes=tuple(notes)
    )


def _custom_model_names(custom_dir: Path) -> frozenset[str]:
    """Exact relative names of every file under Custom/3DModels, as the folder lists them."""
    model_dir = custom_dir / "3DModels"
    try:
        return frozenset(p.relative_to(model_dir).as_posix() for p in model_dir.rglob("*") if p.is_file())
    except OSError:
        return frozenset()


def linked_custom_files(
    ctx: GitContext,
    cplan: CommitPlan,
    kicad_fp_dir: Path | None,
    *,
    cancelled: Callable[[], bool] | None = None,
) -> tuple[tuple[str, str], ...]:
    """The Custom footprints and 3D models a committed part links, as (path relative to Custom, kind) pairs (D-10).

    The footprints are the plan's own plus the ones the new or changed symbols of any committed .kicad_sym
    point at in Custom; the models are the ones those footprints name with the ${CUSTOM_3DMODEL_DIR}/ prefix.
    A model counts only when its name is an exact entry of the Custom/3DModels listing, so no path is ever
    built from model text. Footprints come first, then models, each in name order; nothing is read twice.
    """
    context = incoming_context(cplan.repo_root, cplan.custom_dir / "Footprints", kicad_fp_dir)
    prefix = f"{cplan.custom_rel}/"
    footprints = {rel.casefold(): rel for _, rel in sorted(_committed_footprints(cplan).items())}
    for cfile in cplan.files:
        if cfile.kind != "symbol_lib":
            continue
        if cancelled is not None and cancelled():
            return ()
        root, _ = _read_library(cplan.custom_dir / cfile.rel)
        if root is None:
            continue
        index: dict[str, kicad_files.SymbolRef] = {}
        for ref in kicad_files.find_symbols(root):
            index.setdefault(ref.name, ref)
        for name in changes.symbol_changes(ctx, cplan.custom_dir, cfile.rel, root):
            ref = index.get(name)
            if ref is None:
                continue
            target = context.resolve_footprint(_footprint_text(ref, index))
            if target.problem is None and target.rel_path is not None and target.rel_path.startswith(prefix):
                rel = target.rel_path[len(prefix):]
                footprints.setdefault(rel.casefold(), rel)
    names = _custom_model_names(cplan.custom_dir)
    cache: dict[Path, tuple[str, ...]] = {}
    models: dict[str, str] = {}
    for rel in footprints.values():
        for path in _footprint_models(cplan.custom_dir / rel, cache):
            if path.startswith(CUSTOM_MODEL_PREFIX) and path[len(CUSTOM_MODEL_PREFIX):] in names:
                models.setdefault(path[len(CUSTOM_MODEL_PREFIX):].casefold(), f"3DModels/{path[len(CUSTOM_MODEL_PREFIX):]}")
    return (
        *((rel, "footprint") for rel in sorted(footprints.values())),
        *((rel, "model") for _, rel in sorted(models.items())),
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
