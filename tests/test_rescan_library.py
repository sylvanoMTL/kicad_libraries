"""Rescanning one library gives what a full scan gives (O-07), and falls back to a full scan when it cannot (O-10)."""

import copy
import shutil
from pathlib import Path

import pytest
from customfixtures import (
    ATOMIC_LIBRARIES,
    atomic_lib,
    atomic_part,
    write_atomic_custom,
    write_atomic_files,
    write_fake_kicad,
)
from gitfixtures import make_superproject, requires_git
from installfixtures import vendor_footprint

from kicad_lib_manager import atomic_check, changes, library_scanner
from kicad_lib_manager.library_scanner import LibraryRescan, rescan_library, scan_all
from kicad_lib_manager.models import Issue, ScanResult, Severity, SymbolLibrary

CONNECTOR = "Custom/Symbols/Atomic_Connector.kicad_sym"
FOOTPRINTS = "Custom/Footprints/Atomic_Footprints.pretty"
MODEL_PREFIX = "${CUSTOM_3DMODEL_DIR}"


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    write_atomic_custom(root)
    return root


@pytest.fixture
def kicad(tmp_path):
    footprints, _models = write_fake_kicad(tmp_path)
    return footprints


def _key(issue: Issue):
    return (issue.severity.value, issue.code, issue.text)


def _assert_same_as_full_scan(rescan, full: ScanResult) -> None:
    assert isinstance(rescan, LibraryRescan), rescan
    assert rescan.result.symbol_libs == full.symbol_libs
    assert rescan.result.footprint_libs == full.footprint_libs
    assert sorted(rescan.result.issues, key=_key) == sorted(full.issues, key=_key)


def _edit_connector(root: Path) -> None:
    symbols = next(lib.symbols for lib in ATOMIC_LIBRARIES if lib.name == "Atomic_Connector")
    extra = (atomic_part("NEW-BAD", drop=("MPN",)), atomic_part("NEW-GOOD"))
    (root / CONNECTOR).write_bytes(atomic_lib(symbols[:5] + extra))


def _break_footprint_model(root: Path) -> None:
    (root / FOOTPRINTS / "GENERIC-2PIN.kicad_mod").write_bytes(
        vendor_footprint("GENERIC-2PIN", models=(f"{MODEL_PREFIX}/gone.step",))
    )


# ── Equal to a full scan ─────────────────────────────────────────────

def test_symbol_library_rescan_equals_a_full_scan(repo, kicad):
    before = scan_all(repo, kicad_fp_dir=kicad)
    _edit_connector(repo)

    rescan = rescan_library(repo, before, "symbol", CONNECTOR, kicad)

    _assert_same_as_full_scan(rescan, scan_all(repo, kicad_fp_dir=kicad))
    assert rescan.rechecked == []
    assert any("NEW-BAD" in issue.text for issue in rescan.issues)
    assert all(issue.text.startswith("Atomic_Connector") or "Atomic_Connector" in issue.text
               for issue in rescan.issues)


def test_footprint_library_rescan_equals_a_full_scan_and_rechecks_linked_symbols(repo, kicad):
    before = scan_all(repo, kicad_fp_dir=kicad)
    _break_footprint_model(repo)

    rescan = rescan_library(repo, before, "footprint", FOOTPRINTS, kicad)

    full = scan_all(repo, kicad_fp_dir=kicad)
    _assert_same_as_full_scan(rescan, full)
    assert "Atomic_Connector" in rescan.rechecked
    assert all(name.startswith("Atomic_") for name in rescan.rechecked)
    assert any(issue.code == "scan.model_missing" and "gone.step" in issue.text for issue in rescan.issues)
    assert any(issue.code == "atomic.model_3d" for issue in rescan.result.issues)


def test_unchanged_library_gives_the_same_result(repo, kicad):
    before = scan_all(repo, kicad_fp_dir=kicad)
    for kind, rel in (("symbol", CONNECTOR), ("footprint", FOOTPRINTS)):
        rescan = rescan_library(repo, before, kind, rel, kicad)
        _assert_same_as_full_scan(rescan, before)


def test_previous_is_never_mutated_and_selection_is_snapshotted(repo, kicad):
    before = scan_all(repo, kicad_fp_dir=kicad)
    next(lib for lib in before.symbol_libs if lib.rel_path == CONNECTOR).selected = True
    snapshot = copy.deepcopy(before)
    _edit_connector(repo)

    rescan = rescan_library(repo, before, "symbol", CONNECTOR, kicad)
    _break_footprint_model(repo)
    rescan_library(repo, before, "footprint", FOOTPRINTS, kicad)

    assert before == snapshot
    merged = next(lib for lib in rescan.result.symbol_libs if lib.rel_path == CONNECTOR)
    assert merged.selected is True
    assert merged is not next(lib for lib in before.symbol_libs if lib.rel_path == CONNECTOR)


_FAMILY = {
    "scan.nickname_collision": 0,
    "scan.footprint_lib_missing": 1,
    "scan.unreadable": 2, "scan.model_var": 2, "scan.model_missing": 2, "scan.model_absolute": 2,
    "atomic.summary": 4,
    "scan.symbol_new": 5, "scan.symbol_changed": 5, "scan.footprint_new": 5,
    "scan.footprint_changed": 5, "scan.changes_skipped": 5,
}


def _family(issue: Issue) -> int:
    return _FAMILY.get(issue.code, 3)


def test_issue_order_follows_the_families_of_a_full_scan(repo, kicad):
    before = scan_all(repo, kicad_fp_dir=kicad)
    _edit_connector(repo)
    _break_footprint_model(repo)

    for kind, rel in (("symbol", CONNECTOR), ("footprint", FOOTPRINTS)):
        result = rescan_library(repo, before, kind, rel, kicad).result
        families = [_family(issue) for issue in result.issues]
        assert families == sorted(families)
        assert families.count(4) == 1
    full_families = [_family(issue) for issue in scan_all(repo, kicad_fp_dir=kicad).issues]
    assert full_families == sorted(full_families)


# ── Fall back to a full scan ─────────────────────────────────────────

def _assert_full_needed(outcome, text: str) -> None:
    assert isinstance(outcome, Issue)
    assert outcome.code == "rescan.full_needed"
    assert outcome.severity is Severity.INFO
    assert outcome.text == text


def test_shared_nickname_needs_a_full_scan(repo, kicad):
    before = scan_all(repo, kicad_fp_dir=kicad)
    snapshot = copy.deepcopy(before)
    _assert_full_needed(
        rescan_library(repo, before, "footprint", "Custom/Footprints/Dup_Footprints.pretty", kicad),
        "Dup_Footprints shares its name with another library; running a full rescan instead.",
    )
    assert before == snapshot


def test_deleted_symbol_file_needs_a_full_scan(repo, kicad):
    before = scan_all(repo, kicad_fp_dir=kicad)
    (repo / CONNECTOR).unlink()
    _assert_full_needed(
        rescan_library(repo, before, "symbol", CONNECTOR, kicad),
        f"Atomic_Connector is no longer at {CONNECTOR} (deleted or renamed); running a full rescan instead.",
    )


def test_renamed_footprint_folder_needs_a_full_scan(repo, kicad):
    before = scan_all(repo, kicad_fp_dir=kicad)
    shutil.move(str(repo / FOOTPRINTS), str(repo / "Custom/Footprints/Renamed.pretty"))
    _assert_full_needed(
        rescan_library(repo, before, "footprint", FOOTPRINTS, kicad),
        f"Atomic_Footprints is no longer at {FOOTPRINTS} (deleted or renamed); running a full rescan instead.",
    )


def test_library_not_in_the_scan_needs_a_full_scan(repo, kicad):
    before = scan_all(repo, kicad_fp_dir=kicad)
    _assert_full_needed(
        rescan_library(repo, before, "symbol", "Custom/Symbols/Never.kicad_sym", kicad),
        "Custom/Symbols/Never.kicad_sym is not in the last scan; running a full rescan instead.",
    )
    _assert_full_needed(
        rescan_library(repo, before, "other", CONNECTOR, kicad),
        f"{CONNECTOR} is not in the last scan; running a full rescan instead.",
    )


def test_a_linked_atomic_library_that_is_gone_needs_a_full_scan(repo, kicad):
    before = scan_all(repo, kicad_fp_dir=kicad)
    (repo / "Custom/Symbols/Atomic_Regulator.kicad_sym").unlink()
    # Atomic_Regulator links Atomic_Footprints, so its files cannot be re-read
    outcome = rescan_library(repo, before, "footprint", FOOTPRINTS, kicad)
    _assert_full_needed(
        outcome,
        "Atomic_Regulator is no longer at Custom/Symbols/Atomic_Regulator.kicad_sym "
        "(deleted or renamed); running a full rescan instead.",
    )


# ── Small contracts ──────────────────────────────────────────────────

def test_summary_line_matches_the_scan_summary(repo, kicad):
    full = scan_all(repo, kicad_fp_dir=kicad)
    summaries = [i for i in full.issues if i.code == "atomic.summary"]
    assert len(summaries) == 1
    assert atomic_check.summary_line(full.symbol_libs) == summaries[0]
    assert atomic_check.summary_line([]) is None
    assert atomic_check.summary_line([SymbolLibrary("Plain", "Custom/Plain.kicad_sym", "Custom")]) is None


def test_skip_prefix_matches_changes_module():
    line = changes._skipped_for(Path("x.kicad_sym"), "r")
    assert line.text == library_scanner._SKIP_FOR + "x.kicad_sym: r"
    assert line.code == "scan.changes_skipped"


def test_check_3d_model_paths_still_reports_every_footprint(repo):
    lines = library_scanner.check_3d_model_paths(repo)
    assert any(line.code == "scan.model_missing" for line in lines)


# ── With a git-backed Custom ─────────────────────────────────────────

@pytest.fixture
def git_repo(tmp_path):
    repos = make_superproject(tmp_path / "git", populate=write_atomic_files)
    return repos.parent, tmp_path / "no_kicad"


@requires_git
def test_change_marks_equal_a_full_scan_for_a_symbol_and_a_footprint(git_repo):
    root, kicad = git_repo
    before = scan_all(root, kicad_fp_dir=kicad)
    path = root / CONNECTOR
    path.write_bytes(path.read_bytes().replace(b"Test part USB4105-GF-A", b"Edited by hand"))

    rescan = rescan_library(root, before, "symbol", CONNECTOR, kicad)

    full = scan_all(root, kicad_fp_dir=kicad)
    _assert_same_as_full_scan(rescan, full)
    assert any(issue.code == "scan.symbol_changed" for issue in rescan.issues)

    mod = root / FOOTPRINTS / "GENERIC-2PIN.kicad_mod"
    mod.write_bytes(vendor_footprint("GENERIC-2PIN", models=(f"{MODEL_PREFIX}/GENERIC-2PIN.step", )) + b"\n")
    new_mod = root / FOOTPRINTS / "Brand-New.kicad_mod"
    new_mod.write_bytes(vendor_footprint("Brand-New"))

    second = rescan_library(root, rescan.result, "footprint", FOOTPRINTS, kicad)

    _assert_same_as_full_scan(second, scan_all(root, kicad_fp_dir=kicad))
    assert any(issue.code == "scan.footprint_new" for issue in second.issues)
    changed = next(lib for lib in second.result.footprint_libs if lib.rel_path == FOOTPRINTS).changed
    assert [c.name for c in changed] == sorted((c.name for c in changed), key=str.casefold)


@requires_git
def test_a_skip_line_for_a_file_only_this_library_has_is_replaced(git_repo):
    root, kicad = git_repo
    pretty = root / "Custom/Footprints/Solo_Garbage.pretty"
    pretty.mkdir()
    (pretty / "Only-Here.kicad_mod").write_bytes(b"(footprint \"x\" (unclosed")
    before = scan_all(root, kicad_fp_dir=kicad)
    assert any(i.code == "scan.changes_skipped" and "Only-Here.kicad_mod" in i.text for i in before.issues)
    (pretty / "Only-Here.kicad_mod").write_bytes(vendor_footprint("Only-Here"))

    rescan = rescan_library(root, before, "footprint", "Custom/Footprints/Solo_Garbage.pretty", kicad)

    _assert_same_as_full_scan(rescan, scan_all(root, kicad_fp_dir=kicad))
    assert not any("Only-Here.kicad_mod" in i.text and i.code == "scan.changes_skipped"
                   for i in rescan.result.issues)


@requires_git
def test_a_skip_line_that_two_libraries_could_own_needs_a_full_scan(git_repo):
    root, kicad = git_repo
    for name in ("Twin_A", "Twin_B"):
        pretty = root / "Custom/Footprints" / f"{name}.pretty"
        pretty.mkdir()
        (pretty / "Same.kicad_mod").write_bytes(b"(footprint \"x\" (unclosed")
    before = scan_all(root, kicad_fp_dir=kicad)

    _assert_full_needed(
        rescan_library(root, before, "footprint", "Custom/Footprints/Twin_A.pretty", kicad),
        "The change check for Same.kicad_mod cannot be matched to one library; "
        "running a full rescan instead.",
    )
