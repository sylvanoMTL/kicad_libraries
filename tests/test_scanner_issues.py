"""Scan Issue tests: nickname collision pass (D-01, HARD-08) and 3D model-path rules (D-18, D-19)."""

from pathlib import Path

import pytest

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


# ── 3D model-path rules (D-18, D-19) ────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
CUSTOM_SKIP = "Custom submodule not checked out (git submodule update --init Custom)"
WURTH_SKIP = (
    "WurthElektronik submodule not checked out "
    "(git submodule update --init WurthElektronik/KiCad-Library)"
)

_CUSTOM_FP = "Custom/Footprints/F.pretty"
_WURTH_FP = "WurthElektronik/KiCad-Library/fp/W.pretty"

# The five footprints D-16 lists; plan 02-07 rewrites them, so the live check allows a subset
_D16_FILES = {
    "Custom/Footprints/Connector_USB_GCT.pretty/GCT_USB4730-GF-A_REVA.kicad_mod",
    "Custom/Footprints/IC_Battery_Fuel_Gauge_ADI.pretty/BGA8N40P2X4_93X167X69N.kicad_mod",
    "Custom/Footprints/IC_Battery_Fuel_Gauge_ADI.pretty/SON50P200X200X80-9N.kicad_mod",
    "Custom/Footprints/IC_Button_Controller_ADI.pretty/DFN-8_DDB.kicad_mod",
    "Custom/Footprints/IC_Button_Controller_ADI.pretty/TSOT-23_TS8.kicad_mod",
}


def _write_mod(root: Path, folder: str, name: str, *model_paths: str) -> str:
    """Write a footprint with the given model paths; return its repo-relative path."""
    models = "".join(f'  (model "{p}")\n' for p in model_paths)
    path = root / folder / f"{name}.kicad_mod"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(f'(footprint "{name}"\n{models})\n'.encode("utf-8"))
    return path.relative_to(root).as_posix()


def _write_model_file(root: Path, rel: str) -> None:
    path = root / "Custom" / "3DModels" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"ISO-10303-21;\n")


def test_custom_model_kiprjmod_path_gives_model_var(tmp_path):
    rel = _write_mod(tmp_path, _CUSTOM_FP, "a", "${KIPRJMOD}/Custom/3DModels/a.step")
    issues = library_scanner.check_3d_model_paths(tmp_path)
    assert len(issues) == 1
    assert issues[0].severity is Severity.WARNING
    assert issues[0].code == "scan.model_var"
    assert issues[0].text.startswith(f"[{rel}] ")
    assert "${KIPRJMOD}/Custom/3DModels/a.step" in issues[0].text


def test_custom_model_absolute_path_gives_model_var(tmp_path):
    _write_mod(tmp_path, _CUSTOM_FP, "e", "C:/abs/e.step")
    issues = library_scanner.check_3d_model_paths(tmp_path)
    assert [i.code for i in issues] == ["scan.model_var"]


def test_custom_model_present_is_quiet(tmp_path):
    _write_mod(tmp_path, _CUSTOM_FP, "b", "${CUSTOM_3DMODEL_DIR}/b.step")
    _write_model_file(tmp_path, "b.step")
    assert library_scanner.check_3d_model_paths(tmp_path) == []


def test_custom_model_case_mismatch_gives_model_missing(tmp_path):
    rel = _write_mod(tmp_path, _CUSTOM_FP, "c", "${CUSTOM_3DMODEL_DIR}/c.STEP")
    _write_model_file(tmp_path, "c.step")
    issues = library_scanner.check_3d_model_paths(tmp_path)
    assert len(issues) == 1
    assert issues[0].severity is Severity.WARNING
    assert issues[0].code == "scan.model_missing"
    assert issues[0].text.startswith(f"[{rel}] ")
    assert "c.STEP" in issues[0].text


def test_custom_model_in_subfolder_is_quiet(tmp_path):
    _write_mod(tmp_path, _CUSTOM_FP, "d", "${CUSTOM_3DMODEL_DIR}/sub/d.stp")
    _write_model_file(tmp_path, "sub/d.stp")
    assert library_scanner.check_3d_model_paths(tmp_path) == []


def test_custom_footprint_with_one_good_one_missing_model_gives_one_issue(tmp_path):
    _write_mod(
        tmp_path, _CUSTOM_FP, "g",
        "${CUSTOM_3DMODEL_DIR}/good.step", "${CUSTOM_3DMODEL_DIR}/gone.step",
    )
    _write_model_file(tmp_path, "good.step")
    issues = library_scanner.check_3d_model_paths(tmp_path)
    assert [i.code for i in issues] == ["scan.model_missing"]
    assert "gone.step" in issues[0].text


def test_custom_model_without_3dmodels_folder_is_missing(tmp_path):
    _write_mod(tmp_path, _CUSTOM_FP, "n", "${CUSTOM_3DMODEL_DIR}/n.step")
    issues = library_scanner.check_3d_model_paths(tmp_path)
    assert [i.code for i in issues] == ["scan.model_missing"]


@pytest.mark.parametrize(
    "path",
    ["${WE_3DMODEL_DIR}/w.step", "${KICAD9_3DMODEL_DIR}/x.step", "w.step"],
    ids=["we-var", "kicad-var", "bare-name"],
)
def test_other_source_model_paths_stay_quiet(tmp_path, path):
    _write_mod(tmp_path, _WURTH_FP, "w", path)
    assert library_scanner.check_3d_model_paths(tmp_path) == []


def test_other_source_absolute_model_gives_model_absolute(tmp_path):
    rel = _write_mod(tmp_path, _WURTH_FP, "w", "C:/abs/w.step")
    issues = library_scanner.check_3d_model_paths(tmp_path)
    assert len(issues) == 1
    assert issues[0].severity is Severity.WARNING
    assert issues[0].code == "scan.model_absolute"
    assert issues[0].text.startswith(f"[{rel}] ")


def test_unreadable_footprint_warns_and_scan_continues(tmp_path):
    bad = tmp_path / _CUSTOM_FP / "bad.kicad_mod"
    bad.parent.mkdir(parents=True)
    bad.write_bytes(b'(footprint "bad"\n  (model "x.step"\n')
    rel_ok = _write_mod(tmp_path, _CUSTOM_FP, "ok", "${KIPRJMOD}/ok.step")

    issues = library_scanner.check_3d_model_paths(tmp_path)

    unreadable = [i for i in issues if i.code == "scan.unreadable"]
    assert len(unreadable) == 1
    assert unreadable[0].severity is Severity.WARNING
    assert unreadable[0].text.startswith(f"[{_CUSTOM_FP}/bad.kicad_mod] ")
    assert [i.code for i in issues if i.text.startswith(f"[{rel_ok}] ")] == ["scan.model_var"]


def test_footprint_without_models_gives_nothing(tmp_path):
    _write_mod(tmp_path, _CUSTOM_FP, "none")
    assert library_scanner.check_3d_model_paths(tmp_path) == []


def test_model_issue_text_starts_with_repo_relative_path(tmp_path):
    rels = [
        _write_mod(tmp_path, _CUSTOM_FP, "a", "${KIPRJMOD}/a.step"),
        _write_mod(tmp_path, _CUSTOM_FP, "b", "${CUSTOM_3DMODEL_DIR}/b.step"),
        _write_mod(tmp_path, _WURTH_FP, "w", "D:/abs/w.step"),
    ]
    issues = library_scanner.check_3d_model_paths(tmp_path)
    assert len(issues) == 3
    for issue in issues:
        assert any(issue.text.startswith(f"[{rel}] ") for rel in rels)


def test_scan_all_includes_model_issues(tmp_path):
    _write_mod(tmp_path, _CUSTOM_FP, "a", "${KIPRJMOD}/a.step")
    result = scan_all(tmp_path, kicad_fp_dir=tmp_path / "no_such_dir")
    assert [i.code for i in result.issues] == ["scan.model_var"]


def test_scanner_no_longer_exposes_model_regex():
    assert not hasattr(library_scanner, "MODEL_RE")
    assert library_scanner.CUSTOM_MODEL_PREFIX == "${CUSTOM_3DMODEL_DIR}/"


def test_live_custom_model_findings_are_only_the_d16_var_warnings():
    if not (REPO_ROOT / "Custom" / "Footprints").is_dir():
        pytest.skip(CUSTOM_SKIP)
    issues = library_scanner.check_3d_model_paths(REPO_ROOT)
    custom = [i for i in issues if i.text.startswith("[Custom/")]
    assert {i.code for i in custom} <= {"scan.model_var"}
    assert not [i for i in issues if i.code == "scan.model_missing"]
    files = {i.text[1:i.text.index("] ")] for i in custom}
    assert files <= _D16_FILES


@pytest.mark.wurth
def test_wurth_model_paths_stay_quiet():
    wurth = REPO_ROOT / "WurthElektronik"
    if not any(wurth.rglob("*.kicad_mod")):
        pytest.skip(WURTH_SKIP)
    issues = library_scanner.check_3d_model_paths(REPO_ROOT)
    wurth_issues = [i for i in issues if i.text.startswith("[WurthElektronik/")]
    assert not [i for i in wurth_issues if i.code in ("scan.model_var", "scan.model_missing")]
    assert not [i for i in wurth_issues if "${WE_3DMODEL_DIR}" in i.text]
