"""Scan Issue tests: nickname collision pass (D-01, HARD-08).

Plan 02-05 appends the 3D model-path tests to this file.
"""

from pathlib import Path

from kicad_lib_manager import library_scanner
from kicad_lib_manager.library_scanner import scan_all
from kicad_lib_manager.models import (
    FootprintLibrary,
    Issue,
    Severity,
    SymbolLibrary,
)


def _sym(nickname: str, rel_path: str) -> SymbolLibrary:
    return SymbolLibrary(nickname, rel_path, rel_path.split("/")[0])


def _fp(nickname: str, rel_path: str) -> FootprintLibrary:
    return FootprintLibrary(nickname, rel_path, rel_path.split("/")[0])


_CUSTOM_SAME = "Custom/Symbols/Same.kicad_sym"
_WURTH_SAME = "WurthElektronik/KiCad-Library/symbols/Same.kicad_sym"


def test_symbol_collision_across_sources():
    a, b = _sym("Same", _CUSTOM_SAME), _sym("Same", _WURTH_SAME)
    issues = library_scanner.find_nickname_collisions([a, b], [])
    assert len(issues) == 1
    issue = issues[0]
    assert isinstance(issue, Issue)
    assert issue.severity is Severity.WARNING
    assert issue.code == "scan.nickname_collision"
    assert "Symbol" in issue.text
    assert _CUSTOM_SAME in issue.text and _WURTH_SAME in issue.text
    assert a.collision_peers == [_WURTH_SAME]
    assert b.collision_peers == [_CUSTOM_SAME]


def test_footprint_collision_is_separate_issue():
    a = _fp("Same", "Custom/Footprints/Same.pretty")
    b = _fp("Same", "WurthElektronik/KiCad-Library/fp/Same.pretty")
    issues = library_scanner.find_nickname_collisions([], [a, b])
    assert len(issues) == 1
    assert issues[0].code == "scan.nickname_collision"
    assert "Footprint" in issues[0].text
    assert a.collision_peers == [b.rel_path]
    assert b.collision_peers == [a.rel_path]


def test_symbol_and_footprint_with_same_nickname_do_not_collide():
    sym = _sym("Same", _CUSTOM_SAME)
    fp = _fp("Same", "Custom/Footprints/Same.pretty")
    assert library_scanner.find_nickname_collisions([sym], [fp]) == []
    assert sym.collision_peers == []
    assert fp.collision_peers == []


def test_same_source_different_folders_collide():
    a = _sym("A", "Custom/Symbols/A.kicad_sym")
    b = _sym("A", "Custom/Other/A.kicad_sym")
    issues = library_scanner.find_nickname_collisions([a, b], [])
    assert len(issues) == 1
    assert a.collision_peers == ["Custom/Other/A.kicad_sym"]
    assert b.collision_peers == ["Custom/Symbols/A.kicad_sym"]


def test_three_way_collision_one_issue_sorted_peers():
    paths = ["Custom/Z/A.kicad_sym", "Custom/B/A.kicad_sym", "Custom/M/A.kicad_sym"]
    libs = [_sym("A", p) for p in paths]
    issues = library_scanner.find_nickname_collisions(libs, [])
    assert len(issues) == 1
    for lib in libs:
        assert lib.collision_peers == sorted(p for p in paths if p != lib.rel_path)
        assert len(lib.collision_peers) == 2


def test_no_collision_returns_nothing_and_clears_stale_peers():
    a = _sym("A", "Custom/Symbols/A.kicad_sym")
    b = _sym("B", "Custom/Symbols/B.kicad_sym")
    a.collision_peers = ["stale/path"]
    f = _fp("F", "Custom/Footprints/F.pretty")
    f.collision_peers = ["stale/path"]
    assert library_scanner.find_nickname_collisions([a, b], [f]) == []
    assert a.collision_peers == [] and b.collision_peers == []
    assert f.collision_peers == []


def test_collision_pass_is_idempotent():
    a, b = _sym("Same", _CUSTOM_SAME), _sym("Same", _WURTH_SAME)
    first = library_scanner.find_nickname_collisions([a, b], [])
    second = library_scanner.find_nickname_collisions([a, b], [])
    assert first == second
    assert a.collision_peers == [_WURTH_SAME]
    assert b.collision_peers == [_CUSTOM_SAME]


def test_collision_pass_never_changes_nickname():
    a, b = _sym("Same", _CUSTOM_SAME), _sym("Same", _WURTH_SAME)
    library_scanner.find_nickname_collisions([a, b], [])
    assert a.nickname == "Same" and b.nickname == "Same"


def test_scan_all_reports_collision_first(tmp_path: Path):
    for rel in (_CUSTOM_SAME, _WURTH_SAME):
        f = tmp_path / rel
        f.parent.mkdir(parents=True)
        f.write_bytes(b"(kicad_symbol_lib)\n")
    result = scan_all(tmp_path, kicad_fp_dir=tmp_path / "no_such_dir")
    assert len(result.symbol_libs) == 2
    assert {lib.rel_path for lib in result.symbol_libs} == {_CUSTOM_SAME, _WURTH_SAME}
    for lib in result.symbol_libs:
        assert len(lib.collision_peers) == 1
        assert lib.collision_peers[0] != lib.rel_path
    collisions = [i for i in result.issues if i.code == "scan.nickname_collision"]
    assert len(collisions) == 1
    assert result.issues[0].code == "scan.nickname_collision"
