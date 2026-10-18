"""D-16 regression: the GUI library scan must never see tests/ (fixtures live there)."""

from pathlib import Path

from kicad_lib_manager import library_scanner
from kicad_lib_manager.library_scanner import (
    SKIP_DIRS,
    check_3d_model_paths,
    find_footprint_libs,
    find_symbol_libs,
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


def test_tests_in_skip_dirs():
    assert "tests" in SKIP_DIRS
    assert "tests" in library_scanner.SKIP_DIRS


def test_synthetic_repo_ignores_tests_tree(tmp_path):
    _build_repo(tmp_path)

    sym_libs = find_symbol_libs(tmp_path)
    assert [lib.nickname for lib in sym_libs] == ["A"]
    assert {lib.source for lib in sym_libs} == {"Custom"}

    fp_libs = find_footprint_libs(tmp_path)
    assert [lib.nickname for lib in fp_libs] == ["F"]

    messages = check_3d_model_paths(tmp_path)
    assert not [m for m in messages if m.startswith("[tests/")]


def test_real_repo_has_no_tests_source():
    for lib in find_symbol_libs(REPO_ROOT):
        assert lib.source != "tests"
    for lib in find_footprint_libs(REPO_ROOT):
        assert lib.source != "tests"
    messages = check_3d_model_paths(REPO_ROOT)
    assert not [m for m in messages if m.startswith("[tests/")]
