"""The Phase 11 commit gate (GIT-06): which parts being committed break the atomic rule.

Every repo is a throwaway superproject under tmp_path; the live Custom/ is never read or written. The
gate is run with no KiCad folder, so the result never depends on the workstation's KiCad install.
"""

from pathlib import Path

from customfixtures import atomic_lib, atomic_part, write_atomic_files
from gitfixtures import GIT, GitRepos, commit_file, import_files, make_superproject, populate_custom, requires_git

from kicad_lib_manager import changes
from kicad_lib_manager.gitops import GitContext
from kicad_lib_manager.importer import commit_gate
from kicad_lib_manager.importer.commit_gate import CANCELLED, AtomicFailure, GateResult, run_gate
from kicad_lib_manager.models import STATUS_CHANGED, STATUS_NEW, Severity

pytestmark = requires_git

LIBRARY = "Atomic_Gate_Test"
REL = f"Symbols/{LIBRARY}.kicad_sym"
REPO_REL = f"Custom/{REL}"


def _populate_atomic(custom: Path) -> None:
    populate_custom(custom)
    write_atomic_files(custom)


def _repos(tmp_path: Path) -> GitRepos:
    return make_superproject(tmp_path / "git", populate=_populate_atomic)


def _ctx() -> GitContext:
    return GitContext(Path(GIT))


def test_gate_blocks_a_failing_new_part(tmp_path):
    repos = _repos(tmp_path)
    good = atomic_part("PASSING-1")
    commit_file(repos, repos.custom, REL, atomic_lib((good,)), "Add the passing part")
    bad = atomic_part("LIS3MDL", drop=("Datasheet",))
    cplan = import_files(repos, {REL: atomic_lib((good, bad))}, library=LIBRARY, symbol="LIS3MDL")

    gate = run_gate(_ctx(), cplan, None)

    assert [(f.library, f.rel_path, f.part, f.rule) for f in gate.blocking] == [
        (LIBRARY, REPO_REL, "LIS3MDL", "datasheet")
    ]
    assert gate.refused is True
    assert gate.old == ()


def test_symbol_changes_matches_scan_marks(tmp_path):
    repos = _repos(tmp_path)
    ctx = _ctx()
    first, second = atomic_part("AAA-1"), atomic_part("BBB-2")

    # A file HEAD lacks: every symbol is new
    path = repos.custom / REL
    path.write_bytes(atomic_lib((first, second)))
    loaded = changes._read_current(path)[0]
    assert changes.symbol_changes(ctx, repos.custom, REL, loaded) == {"AAA-1": STATUS_NEW, "BBB-2": STATUS_NEW}

    # HEAD's copy does not parse: every symbol counts as changed
    commit_file(repos, repos.custom, REL, b"(kicad_symbol_lib (version", "Commit a broken library")
    path.write_bytes(atomic_lib((first, second)))
    loaded = changes._read_current(path)[0]
    assert changes.symbol_changes(ctx, repos.custom, REL, loaded) == {
        "AAA-1": STATUS_CHANGED,
        "BBB-2": STATUS_CHANGED,
    }

    # A parsable HEAD: only the new or changed names, in file order; whitespace and line endings do not count
    commit_file(repos, repos.custom, REL, atomic_lib((first, second)), "Commit both parts")
    edited = atomic_part("AAA-1", replace={"Description": "A new description"})
    added = atomic_part("CCC-3")
    path.write_bytes(atomic_lib((edited, second, added), eol="\r\n"))
    loaded = changes._read_current(path)[0]
    assert changes.symbol_changes(ctx, repos.custom, REL, loaded) == {"AAA-1": STATUS_CHANGED, "CCC-3": STATUS_NEW}


def _failure(library: str, part: str, rule: str, text: str) -> AtomicFailure:
    return AtomicFailure(library, f"Custom/Symbols/{library}.kicad_sym", part, rule, text)


def test_gate_old_failure_does_not_block(tmp_path):
    repos = _repos(tmp_path)
    failing = atomic_part("OLD-1", drop=("Datasheet",))
    commit_file(repos, repos.custom, REL, atomic_lib((failing,)), "Add a part that already fails")
    cplan = import_files(repos, {REL: atomic_lib((failing, atomic_part("NEW-Q")))}, library=LIBRARY)

    gate = run_gate(_ctx(), cplan, None)

    assert gate.blocking == ()
    assert gate.refused is False
    assert [(f.part, f.rule) for f in gate.old] == [("OLD-1", "datasheet")]
    assert [entry.name for _, _, entry in gate.entries] == ["OLD-1"]
    assert commit_gate.old_notes(gate) == [f"{LIBRARY} also holds 1 part that already failed before this import"]


def test_gate_blocks_a_failing_pre_import_edit(tmp_path):
    repos = _repos(tmp_path)
    commit_file(repos, repos.custom, REL, atomic_lib((atomic_part("EDIT-P"),)), "Add a passing part")
    edited = atomic_part("EDIT-P", drop=("Datasheet",))
    cplan = import_files(repos, {REL: atomic_lib((edited, atomic_part("NEW-Q")))}, library=LIBRARY)

    gate = run_gate(_ctx(), cplan, None)

    assert [(f.part, f.rule) for f in gate.blocking] == [("EDIT-P", "datasheet")]
    assert gate.old == ()


def test_gate_judges_derived_child_of_changed_parent(tmp_path):
    repos = _repos(tmp_path)
    child = atomic_part("CHILD-1", drop=("Datasheet",), extends="PARENT-1")
    commit_file(
        repos, repos.custom, REL, atomic_lib((atomic_part("PARENT-1"), child)), "Add a parent and a derived part"
    )
    parent = atomic_part("PARENT-1", drop=("Datasheet",))
    cplan = import_files(repos, {REL: atomic_lib((parent, child))}, library=LIBRARY)

    gate = run_gate(_ctx(), cplan, None)

    assert sorted((f.part, f.rule) for f in gate.blocking) == [("CHILD-1", "datasheet"), ("PARENT-1", "datasheet")]
    assert gate.old == ()


def test_gate_refuses_unreadable_library(tmp_path):
    repos = _repos(tmp_path)
    cplan = import_files(repos, {REL: b"(kicad_symbol_lib (version"}, library=LIBRARY)

    gate = run_gate(_ctx(), cplan, None)

    assert len(gate.problems) == 1
    assert gate.problems[0].startswith(f"{LIBRARY}: the library could not be checked")
    assert gate.blocking == ()
    assert gate.refused is True


def test_gate_skips_non_atomic_library(tmp_path):
    repos = _repos(tmp_path)
    rel = "Symbols/Connector_Gate_Test.kicad_sym"
    bad = atomic_part("LEGACY-NEW", drop=("Datasheet",))
    cplan = import_files(repos, {rel: atomic_lib((bad,))}, library="Connector_Gate_Test")

    assert run_gate(_ctx(), cplan, None) == GateResult()


def test_gate_findings_never_block(tmp_path):
    repos = _repos(tmp_path)
    leftover = atomic_part("PRICED-1", extra=(("Price", "1.20"),))
    cplan = import_files(repos, {REL: atomic_lib((leftover,))}, library=LIBRARY)

    gate = run_gate(_ctx(), cplan, None)

    assert gate.blocking == ()
    assert gate.refused is False


def test_gate_cancelled(tmp_path):
    repos = _repos(tmp_path)
    cplan = import_files(repos, {REL: atomic_lib((atomic_part("ANY-1", drop=("Datasheet",)),))}, library=LIBRARY)

    assert run_gate(_ctx(), cplan, None, cancelled=lambda: True) == GateResult(problems=(CANCELLED,))


def test_gate_texts():
    one_part = GateResult(blocking=(_failure("Atomic_A", "P1", "datasheet", "no datasheet"),))
    assert commit_gate.refusal_summary(one_part) == "1 part breaks the atomic rule"

    gate = GateResult(
        blocking=(
            _failure("Atomic_A", "P1", "datasheet", "no datasheet"),
            _failure("Atomic_A", "P1", "mpn", "no MPN"),
            _failure("Atomic_B", "P2", "description", "no description"),
        ),
        old=(_failure("Atomic_B", "P9", "mpn", "no MPN"), _failure("Atomic_B", "P9", "datasheet", "no datasheet")),
        problems=("Atomic_C: the library could not be checked (the file is damaged)",),
        notes=("Atomic_B also holds 1 part that already failed before this import",),
    )
    assert commit_gate.refusal_summary(gate) == "2 parts break the atomic rule; 1 library could not be checked"
    assert commit_gate.failure_lines(gate) == [
        "Atomic_A / P1: no datasheet",
        "Atomic_A / P1: no MPN",
        "Atomic_B / P2: no description",
        "Atomic_C: the library could not be checked (the file is damaged)",
    ]
    assert commit_gate.old_notes(gate) == ["Atomic_B also holds 1 part that already failed before this import"]
    assert [(i.severity, i.code, i.text) for i in commit_gate.gate_issues(gate)] == [
        (Severity.ERROR, "commit.atomic.datasheet", "Atomic_A / P1: no datasheet"),
        (Severity.ERROR, "commit.atomic.mpn", "Atomic_A / P1: no MPN"),
        (Severity.ERROR, "commit.atomic.description", "Atomic_B / P2: no description"),
        (Severity.WARNING, "commit.atomic_old.mpn", "Atomic_B / P9: no MPN"),
        (Severity.WARNING, "commit.atomic_old.datasheet", "Atomic_B / P9: no datasheet"),
        (Severity.ERROR, "commit.atomic_unreadable", "Atomic_C: the library could not be checked (the file is damaged)"),
        (Severity.INFO, "commit.atomic_note", "Atomic_B also holds 1 part that already failed before this import"),
    ]


def test_gate_texts_for_clean_and_problem_only_results():
    assert commit_gate.refusal_summary(GateResult()) == ""
    assert commit_gate.refusal_summary(GateResult(old=(_failure("Atomic_A", "P1", "mpn", "no MPN"),))) == ""
    assert commit_gate.old_notes(GateResult()) == []
    assert commit_gate.refusal_summary(GateResult(problems=("a", "b"))) == "2 libraries could not be checked"
    plural = GateResult(old=(_failure("Atomic_A", "P1", "mpn", "no MPN"), _failure("Atomic_A", "P2", "mpn", "no MPN")))
    assert commit_gate.old_notes(plural) == ["Atomic_A also holds 2 parts that already failed before this import"]


def test_scan_result_for_feeds_check_dialog(tmp_path):
    repos = _repos(tmp_path)
    cplan = import_files(
        repos, {REL: atomic_lib((atomic_part("SHEET-1", drop=("Datasheet",)),))}, library=LIBRARY
    )
    gate = run_gate(_ctx(), cplan, None)

    scan = commit_gate.scan_result_for(gate)

    assert [(lib.nickname, lib.rel_path, lib.source, lib.atomic) for lib in scan.symbol_libs] == [
        (LIBRARY, REPO_REL, "Custom", True)
    ]
    entries = scan.symbol_libs[0].symbols
    assert [entry.name for entry in entries] == ["SHEET-1"]
    violation = entries[0].violations[0]
    assert violation.rule == "datasheet"
    assert violation.fill is not None and violation.fill.kind == "fill_datasheet"
    failure = gate.first_failure
    assert (scan.symbol_libs[0].rel_path, entries[0].name) == (failure.rel_path, failure.part)
