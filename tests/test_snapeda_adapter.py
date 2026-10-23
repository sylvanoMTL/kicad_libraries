"""SnapEDA recognition from the staged symbol (INTK-03, D-14, D-15)."""

from pathlib import Path

from vendorfixtures import SNAPEDA_SYMBOL, snapeda_members
from zipfixtures import footprint, make_zip, symbol_lib

from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.package import Package, PackageFile, open_package

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"


def test_snapeda_renamed_two_file_zip_recognised(tmp_path):
    zip_path = make_zip(tmp_path / "part.zip", snapeda_members(how_to=False))
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
    assert candidate is not None
    assert candidate.vendor == "SnapEDA"
    # 5 points for the property marker plus 2 for snapeda.com
    assert candidate.confidence == 0.7
    assert [s.name for s in candidate.symbols] == [SNAPEDA_SYMBOL]


def test_snapeda_not_claimed_elsewhere(tmp_path):
    from kicad_lib_manager.importer.adapters.snapeda import SnapEDAAdapter

    adapter = SnapEDAAdapter()
    with open_package(UL_ZIP, REPO_ROOT) as package:
        assert adapter.detect(package) is None

    generic = make_zip(tmp_path / "generic.zip", [("a.kicad_sym", symbol_lib(("A",))), ("b.kicad_mod", footprint("B"))])
    with open_package(generic, REPO_ROOT) as package:
        assert adapter.detect(package) is None
        candidate, _ = detect_candidate(package)
    assert candidate is not None
    assert candidate.vendor == "Unknown"


def test_snapeda_detect_survives_unreadable_symbol(tmp_path):
    from kicad_lib_manager.importer.adapters.snapeda import SnapEDAAdapter

    package = Package(
        source=tmp_path / "x.zip",
        kind="zip",
        files=[PackageFile("a.kicad_sym", tmp_path / "missing.kicad_sym", "symbol", 1, "0" * 64, True)],
    )
    assert SnapEDAAdapter().detect(package) is None
