"""What the scan marks as new or changed in a git-backed Custom/ (SCAN-02): by content, never by formatting."""

from pathlib import Path

import pytest
from customfixtures import write_atomic_files
from gitfixtures import GitRepos, make_superproject, requires_git

from kicad_lib_manager.library_scanner import scan_all
from kicad_lib_manager.models import Issue, ScanResult

pytestmark = requires_git

CHANGE_CODES = {
    "scan.changes_skipped",
    "scan.symbol_new",
    "scan.symbol_changed",
    "scan.footprint_new",
    "scan.footprint_changed",
}
CONNECTOR = "Custom/Symbols/Atomic_Connector.kicad_sym"
USB_DESCRIPTION = b"Test part USB4105-GF-A"


def _populate(custom: Path) -> None:
    write_atomic_files(custom)
    (custom / ".gitignore").write_bytes(b"*.bak\n")


def _repos(tmp_path: Path, **options) -> GitRepos:
    return make_superproject(tmp_path / "git", populate=_populate, **options)


def _scan(repos: GitRepos, tmp_path: Path) -> ScanResult:
    # An explicit folder, so no test reads the machine's KiCad install
    return scan_all(repos.parent, kicad_fp_dir=tmp_path / "no_kicad")


def _change_lines(result: ScanResult) -> list[Issue]:
    return [i for i in result.issues if i.code in CHANGE_CODES]


def _statuses(result: ScanResult, nickname: str) -> dict[str, str | None]:
    lib = next(lib for lib in result.symbol_libs if lib.nickname == nickname)
    return {entry.name: entry.status for entry in lib.symbols}


def _edit(path: Path, old: bytes, new: bytes) -> None:
    data = path.read_bytes()
    assert old in data
    path.write_bytes(data.replace(old, new))


def test_a_clean_tree_marks_nothing(tmp_path):
    repos = _repos(tmp_path)

    result = _scan(repos, tmp_path)

    assert _change_lines(result) == []
    statuses = _statuses(result, "Atomic_Connector")
    assert statuses and set(statuses.values()) == {None}


def test_one_edited_symbol_is_marked_changed_with_one_log_line(tmp_path):
    repos = _repos(tmp_path)
    _edit(repos.parent / CONNECTOR, USB_DESCRIPTION, b"Edited by hand in KiCad")

    result = _scan(repos, tmp_path)

    statuses = _statuses(result, "Atomic_Connector")
    assert statuses.pop("USB4105-GF-A") == "changed"
    assert set(statuses.values()) == {None}
    lines = _change_lines(result)
    assert [(i.code, i.text) for i in lines] == [
        ("scan.symbol_changed", "Symbol Atomic_Connector / USB4105-GF-A: changed since the last Custom commit")
    ]
