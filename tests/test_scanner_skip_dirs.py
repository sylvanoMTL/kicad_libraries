"""D-16 regression: the GUI library scan must never see tests/ (fixtures live there).

IN-03: vendor packages under downloaded_examples/ are skipped the same way.
Scan findings are Issue objects (Phase 1 D-07), not strings.
"""

from pathlib import Path

from kicad_lib_manager import library_scanner
from kicad_lib_manager.library_scanner import (
    SKIP_DIRS,
    check_3d_model_paths,
    find_footprint_libs,
    find_symbol_libs,
    scan_all,
)
from kicad_lib_manager.models import (
    FootprintLibrary,
    Issue,
    ScanResult,
    Severity,
    SymbolLibrary,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

_MOD_WITH_ABSOLUTE_MODEL = (
    b'(footprint "m"\n'
    b'  (model "C:/abs/m.step")\n'
    b")\n"
)


def _build_repo(root: Path) -> None:
    (root / "Custom" / "Symbols").mkdir(parents=True)
    (root / "Custom" / "Symbols" / "A.kicad_sym").write_bytes(b"(kicad_symbol_lib)\n")
    (root / "Custom" / "Footprints" / "F.pretty").mkdir(parents=True)
    fx = root / "tests" / "fixtures"
    (fx / "sexpr").mkdir(parents=True)
    (fx / "sexpr" / "B.kicad_sym").write_bytes(b"(kicad_symbol_lib)\n")
    (fx / "X.pretty").mkdir()
    (fx / "sexpr" / "m.kicad_mod").write_bytes(_MOD_WITH_ABSOLUTE_MODEL)


def _build_repo_with_downloaded_examples(root: Path) -> None:
    (root / "Custom" / "Symbols").mkdir(parents=True)
    (root / "Custom" / "Symbols" / "A.kicad_sym").write_bytes(b"(kicad_symbol_lib)\n")
    pkg = root / "downloaded_examples" / "x"
    (pkg / "footprints.pretty").mkdir(parents=True)
    (pkg / "footprints.pretty" / "a.kicad_mod").write_bytes(_MOD_WITH_ABSOLUTE_MODEL)
    (pkg / "a.kicad_sym").write_bytes(b"(kicad_symbol_lib)\n")


def test_tests_in_skip_dirs():
    assert "tests" in SKIP_DIRS
    assert "tests" in library_scanner.SKIP_DIRS


def test_downloaded_examples_in_skip_dirs():
    assert "downloaded_examples" in SKIP_DIRS


def test_synthetic_repo_ignores_tests_tree(tmp_path):
    _build_repo(tmp_path)

    sym_libs = find_symbol_libs(tmp_path)
    assert [lib.nickname for lib in sym_libs] == ["A"]
    assert {lib.source for lib in sym_libs} == {"Custom"}

    fp_libs = find_footprint_libs(tmp_path)
    assert [lib.nickname for lib in fp_libs] == ["F"]

    issues = check_3d_model_paths(tmp_path)
    assert all(isinstance(i, Issue) for i in issues)
    assert not [i for i in issues if i.text.startswith("[tests/")]


def test_synthetic_repo_ignores_downloaded_examples(tmp_path):
    _build_repo_with_downloaded_examples(tmp_path)

    sym_libs = find_symbol_libs(tmp_path)
    fp_libs = find_footprint_libs(tmp_path)
    assert [lib.nickname for lib in sym_libs] == ["A"]
    assert fp_libs == []
    assert "downloaded_examples" not in {lib.source for lib in sym_libs + fp_libs}

    issues = check_3d_model_paths(tmp_path)
    assert not [i for i in issues if i.text.startswith("[downloaded_examples/")]

    result = scan_all(tmp_path)
    assert not [i for i in result.issues if "downloaded_examples" in i.text]


def test_real_repo_has_no_tests_source():
    for lib in find_symbol_libs(REPO_ROOT):
        assert lib.source != "tests"
    for lib in find_footprint_libs(REPO_ROOT):
        assert lib.source != "tests"
    issues = check_3d_model_paths(REPO_ROOT)
    assert not [i for i in issues if i.text.startswith("[tests/")]


def test_scan_result_carries_issues_not_warnings():
    result = ScanResult()
    assert result.issues == []
    assert not hasattr(result, "warnings")


def test_libraries_default_to_no_collision_peers():
    assert SymbolLibrary("A", "Custom/Symbols/A.kicad_sym", "Custom").collision_peers == []
    assert FootprintLibrary("A", "Custom/Footprints/A.pretty", "Custom").collision_peers == []


def test_model_absolute_issue_shape(tmp_path):
    # Outside Custom/ only absolute paths warn; Custom/ uses scan.model_var (D-18)
    (tmp_path / "WurthElektronik" / "F.pretty").mkdir(parents=True)
    (tmp_path / "WurthElektronik" / "F.pretty" / "m.kicad_mod").write_bytes(
        _MOD_WITH_ABSOLUTE_MODEL
    )
    issues = check_3d_model_paths(tmp_path)
    assert len(issues) == 1
    assert issues[0].severity is Severity.WARNING
    assert issues[0].code == "scan.model_absolute"
    assert issues[0].text.startswith("[WurthElektronik/F.pretty/m.kicad_mod] ")


def test_scan_all_cross_reference_issue(tmp_path):
    (tmp_path / "Custom" / "Symbols").mkdir(parents=True)
    (tmp_path / "Custom" / "Symbols" / "A.kicad_sym").write_text(
        '(kicad_symbol_lib (symbol "s" (property "Footprint" "Nope:FP")))\n',
        encoding="utf-8",
    )
    result = scan_all(tmp_path, kicad_fp_dir=tmp_path / "no_such_dir")
    missing = [i for i in result.issues if i.code == "scan.footprint_lib_missing"]
    assert len(missing) == 1
    assert missing[0].severity is Severity.WARNING
    assert missing[0].text == (
        "[A] Footprint library 'Nope' not found in repo or KiCad defaults "
        "(referenced by FP)"
    )
