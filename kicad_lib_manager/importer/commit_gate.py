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
link a committed model are still checked, and their failures are listed as older. A footprint whose model
lines cannot be read is skipped quietly in that pass, which cannot hide a blocking failure: a model link
only ever yields older failures.

A linked part is found through the footprint file its link resolves to, and check_symbol reads a footprint
file and its 3D models only for a link that resolves, so a part whose link does not resolve reaches no
committed file and its verdict cannot depend on a committed footprint's or model's content. The one case in
which it still names a committed file, a link equal to a committed footprint that cannot be followed in the
work tree (its library name is also a KiCad library, or the footprint folder cannot be listed), is listed
as not checked and does not refuse, because the owner decided refusal only for unreadable libraries.

An Atomic_ library outside the commit that cannot be read, parsed or listed, while the commit holds a
footprint or a 3D model, refuses the commit like an unreadable committed library: its parts may link the
committed files and cannot be judged. This fails closed on purpose; refusing a library that does not use
those files is accepted (WR-03, the owner's decision). With no footprint and no model in the commit the
linked check does not run and no outside library is read.
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
_UNLISTED = "the symbol libraries could not be listed"
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
    """What the gate found: blocking failures, older failures, lines that stop the commit, and the entries behind them.

    problems is the one channel for "some parts could not be checked": every line in it refuses the commit.
    unchecked holds the linked parts that could not be checked against a committed footprint; they never refuse.
    """

    blocking: tuple[AtomicFailure, ...] = ()
    old: tuple[AtomicFailure, ...] = ()
    problems: tuple[str, ...] = ()
    entries: tuple[tuple[str, str, SymbolEntry], ...] = ()  # (library, rel_path, entry)
    unchecked: tuple[str, ...] = ()  # shown in the panel through old_notes, never a refusal

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
    """Each committed Footprints/<Lib>.pretty/<Name>.kicad_mod as {"Lib:Name": path relative to Custom}.

    A deleted footprint is skipped (MIG-04): it is gone from the work tree, so it is never a link target.
    """
    found: dict[str, str] = {}
    for cfile in cplan.files:
        if cfile.deleted:
            continue
        parts = PurePosixPath(cfile.rel).parts
        if cfile.kind != "footprint" or len(parts) != 3 or parts[0] != "Footprints":
            continue
        pretty, mod = parts[1], parts[2]
        if pretty.endswith(".pretty") and mod.endswith(".kicad_mod"):
            found[f"{pretty[: -len('.pretty')]}:{mod[: -len('.kicad_mod')]}"] = cfile.rel
    return found


def _committed_models(cplan: CommitPlan) -> frozenset[str]:
    """The committed 3D model files as names relative to 3DModels/; a deleted model is skipped (MIG-04)."""
    prefix = "3DModels/"
    return frozenset(c.rel[len(prefix):] for c in cplan.files if not c.deleted and c.kind == "model" and c.rel.startswith(prefix))


def _atomic_symbol_files(custom_dir: Path) -> tuple[list[str], str]:
    """File names of the Atomic_ symbol libraries under Custom/Symbols in name order, and why it could not be listed.

    A folder that does not exist has nothing to check: ([], ""). Any other failure gives ([], the reason).
    """
    try:
        names = sorted(os.listdir(custom_dir / "Symbols"))
    except FileNotFoundError:
        return [], ""
    except OSError as e:
        return [], str(e.strerror or e)
    return [name for name in names if name.endswith(".kicad_sym") and is_atomic(name[: -len(".kicad_sym")])], ""


@dataclass(frozen=True)
class _LinkedFindings:
    """What the linked check found, for run_gate to merge: it changes nothing it was given."""

    blocking: tuple[AtomicFailure, ...]
    old: tuple[AtomicFailure, ...]
    entries: tuple[tuple[str, str, SymbolEntry], ...]
    problems: tuple[str, ...]
    # (rel_path, part) pairs a committed library listed as old whose linked check now introduces a failure
    moved: frozenset[tuple[str, str]]
    unchecked: tuple[str, ...] = ()
    cancelled: bool = False


def _move_introduced(
    old: list[AtomicFailure], entries: list[tuple[str, str, SymbolEntry]], moved: frozenset[tuple[str, str]]
) -> tuple[list[AtomicFailure], list[tuple[str, str, SymbolEntry]]]:
    """The old failures and entries without the (rel_path, part) pairs in moved, order kept.

    An unchanged symbol of a committed library that was listed as old and now fails because of a linked
    file is listed once, as blocking; this drops its old listing.
    """
    return (
        [f for f in old if (f.rel_path, f.part) not in moved],
        [e for e in entries if (e[1], e[2].name) not in moved],
    )


def _check_linked_symbols(
    ctx: GitContext,
    cplan: CommitPlan,
    kicad_fp_dir: Path | None,
    work: AtomicContext,
    footprints: dict[str, str],
    models: frozenset[str],
    committed: dict[str, tuple[kicad_files.Node | None, set[str]]],
    listed_old: frozenset[tuple[str, str]],
    cancelled: Callable[[], bool] | None,
) -> _LinkedFindings:
    """Judge the symbols that link a committed footprint or model (D-04).

    A symbol that fails in the work tree has its violations split against the HEAD view: the ones HEAD
    did not have block, the rest are old. Changed symbols of committed libraries were judged already, and
    listed_old holds the (rel_path, part) pairs those libraries listed as old. A library that cannot be
    read, or a Symbols folder that cannot be listed, becomes a problem (fail closed).
    """
    blocking: list[AtomicFailure] = []
    old: list[AtomicFailure] = []
    entries: list[tuple[str, str, SymbolEntry]] = []
    problems: list[str] = []
    unchecked: list[str] = []
    moved: set[tuple[str, str]] = set()
    linked_rels = {f"{cplan.custom_rel}/{rel}" for rel in footprints.values()}
    head: AtomicContext | None = None
    model_cache: dict[Path, tuple[str, ...]] = {}
    file_names, unlisted = _atomic_symbol_files(cplan.custom_dir)
    if unlisted:
        line = (
            f"{cplan.custom_rel}/Symbols: {_UNLISTED} ({unlisted}), "
            "so their parts could not be checked against the committed footprints and 3D models. "
            "Click Check again once the folder can be read."
        )
        return _LinkedFindings((), (), (), (line,), frozenset())
    for file_name in file_names:
        if cancelled is not None and cancelled():
            return _LinkedFindings((), (), (), (), frozenset(), cancelled=True)
        library = file_name[: -len(".kicad_sym")]
        known = committed.get(file_name.casefold())
        judged: set[str] = set()
        if known is not None:
            root, judged = known
        else:
            root, why = _read_library(cplan.custom_dir / "Symbols" / file_name)
            if root is None:
                problems.append(
                    f"{library}: the parts in this library could not be checked against the committed footprints and 3D models ({why}). "
                    "Fix the library file (check that it opens in KiCad), then click Check again."
                )
        if root is None:
            continue
        rel_path = f"{cplan.custom_rel}/Symbols/{file_name}"
        index: dict[str, kicad_files.SymbolRef] = {}
        for ref in kicad_files.find_symbols(root):
            index.setdefault(ref.name, ref)
        for name, ref in index.items():
            if name in judged:
                continue
            text = _footprint_text(ref, index)
            target = work.resolve_footprint(text)
            if target.problem is not None:
                if text in footprints:  # a link to a committed footprint that cannot be followed is shown, not skipped
                    unchecked.append(
                        f"{library} / {name} was not checked against the committed footprint {text} ({target.problem})"
                    )
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
            if (rel_path, name) in listed_old and not introduced:
                continue  # an unchanged symbol of a committed library, already listed as old
            moved.add((rel_path, name))
            blocking.extend(AtomicFailure(library, rel_path, name, v.rule, v.text) for v in introduced)
            old.extend(AtomicFailure(library, rel_path, name, v.rule, v.text) for v in older)
            entries.append((library, rel_path, entry))
    return _LinkedFindings(
        tuple(blocking), tuple(old), tuple(entries), tuple(problems), frozenset(moved), tuple(unchecked)
    )


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
    3D model also judges the symbols that link it, in any Atomic_ library (D-04); an Atomic_ library
    outside the commit that cannot be read, parsed or listed then refuses too (fail closed, WR-03).
    """
    context = incoming_context(cplan.repo_root, cplan.custom_dir / "Footprints", kicad_fp_dir)
    blocking: list[AtomicFailure] = []
    old: list[AtomicFailure] = []
    problems: list[str] = []
    entries: list[tuple[str, str, SymbolEntry]] = []
    # file name (casefolded) -> (parsed root or None, names judged as changed) of each committed library
    committed: dict[str, tuple[kicad_files.Node | None, set[str]]] = {}
    for cfile in cplan.files:
        if cfile.deleted:
            continue  # gone from the work tree by design (MIG-04, P-04): nothing left in it to judge
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

    unchecked: tuple[str, ...] = ()
    footprints = _committed_footprints(cplan)
    models = _committed_models(cplan)
    if footprints or models:
        listed_old = frozenset((f.rel_path, f.part) for f in old)
        linked = _check_linked_symbols(
            ctx, cplan, kicad_fp_dir, context, footprints, models, committed, listed_old, cancelled
        )
        if linked.cancelled:
            return GateResult(problems=(CANCELLED,))
        old, entries = _move_introduced(old, entries, linked.moved)
        blocking.extend(linked.blocking)
        old.extend(linked.old)
        entries.extend(linked.entries)
        problems.extend(linked.problems)
        unchecked = linked.unchecked
    return GateResult(
        blocking=tuple(blocking),
        old=tuple(old),
        problems=tuple(problems),
        entries=tuple(entries),
        unchecked=unchecked,
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
        if cfile.deleted or cfile.kind != "symbol_lib":
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
    """The strip text of a refused commit: how many parts break the rule, how many libraries were not checked.

    A Symbols folder that could not be listed is named as such, never counted as a library.
    """
    if not gate.refused:
        return ""
    parts: list[str] = []
    broken = len({(f.library, f.part) for f in gate.blocking})
    if broken:
        parts.append(f"{broken} part breaks the atomic rule" if broken == 1 else f"{broken} parts break the atomic rule")
    unlisted = sum(1 for problem in gate.problems if _UNLISTED in problem)
    libraries = len(gate.problems) - unlisted
    if libraries:
        parts.append(f"{_plural(libraries, 'library', 'libraries')} could not be checked")
    if unlisted:
        parts.append(_UNLISTED)
    return "; ".join(parts)


def _line(failure: AtomicFailure) -> str:
    return f"{failure.library} / {failure.part}: {failure.text}"


def failure_lines(gate: GateResult) -> list[str]:
    """One "Library / Part: reason" line per broken rule, then the libraries that could not be checked (D-06)."""
    return [*(_line(f) for f in gate.blocking), *gate.problems]


def old_notes(gate: GateResult) -> list[str]:
    """The panel's amber lines, none of which stops the commit.

    First one note per library that holds parts which already failed before this import (D-02), then one
    line per linked part that was not checked against a committed footprint.
    """
    counts: dict[str, set[str]] = {}
    for failure in gate.old:
        counts.setdefault(failure.library, set()).add(failure.part)
    notes = [
        f"{library} also holds {_plural(len(parts), 'part', 'parts')} that already failed before this import"
        for library, parts in counts.items()
    ]
    return [*notes, *gate.unchecked]


def gate_issues(gate: GateResult) -> list[Issue]:
    """The log lines of the gate, in the Phase 9 D-05 shape: blocking, old, parts not checked, then unreadable libraries."""
    issues = [Issue(Severity.ERROR, f"commit.atomic.{f.rule}", _line(f)) for f in gate.blocking]
    issues.extend(Issue(Severity.WARNING, f"commit.atomic_old.{f.rule}", _line(f)) for f in gate.old)
    issues.extend(Issue(Severity.WARNING, "commit.atomic_unchecked", line) for line in gate.unchecked)
    issues.extend(Issue(Severity.ERROR, "commit.atomic_unreadable", problem) for problem in gate.problems)
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
