"""The Phase 11 commit gate (GIT-06): which parts being committed break the atomic rule.

Every repo is a throwaway superproject under tmp_path; the live Custom/ is never read or written. The
gate is run with no KiCad folder, so the result never depends on the workstation's KiCad install.
"""

from pathlib import Path

from customfixtures import atomic_lib, atomic_part, write_atomic_files
from gitfixtures import GIT, GitRepos, commit_file, import_files, make_superproject, populate_custom, requires_git

from kicad_lib_manager import changes
from kicad_lib_manager.importer.commit_gate import run_gate
from kicad_lib_manager.gitops import GitContext
from kicad_lib_manager.models import STATUS_CHANGED, STATUS_NEW

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
