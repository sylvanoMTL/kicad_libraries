"""Importer intake on the Ultra Librarian sample: D-01, D-02, D-04, D-07, D-09, INTK-02."""

import hashlib
import zipfile
from pathlib import Path

from kicad_lib_manager.importer.detect import ADAPTERS, detect_candidate
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.suggest import TokenChoice, placeholder_tokens, suggest_library
from kicad_lib_manager.models import Severity

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
UL_SYMBOL = "KiCADv6/2026-10-18_09-12-49.kicad_sym"
UL_FOOTPRINT = "KiCADv6/footprints.pretty/DQK0006B.kicad_mod"
UL_IGNORED = ["ImportGuides.html", "readme.txt", "KiCADv6/ImportGuide.html"]


def _errors(issues):
    return [i for i in issues if i.severity is Severity.ERROR]


def test_ultra_sample_end_to_end():
    with open_package(UL_ZIP, REPO_ROOT) as package:
        candidate, issues = detect_candidate(package)
        assert candidate is not None
        assert candidate.vendor == "UltraLibrarian"
        assert candidate.confidence == 1.0
        assert [s.name for s in candidate.symbols] == ["CSD85301Q2"]
        assert candidate.symbols[0].file.member == UL_SYMBOL
        assert [f.name for f in candidate.footprints] == ["DQK0006B"]
        assert candidate.footprints[0].file.member == UL_FOOTPRINT
        assert candidate.footprints[0].model_paths == ()
        assert [m.filename for m in candidate.models] == ["DLV0006A.stp"]
        assert candidate.legacy_ignored == ()
        assert not _errors(package.issues)
        assert not _errors(issues)
        assert not _errors(candidate.issues)


def test_ultra_adapter_registry_holds_the_ultra_adapter():
    assert [a.name for a in ADAPTERS] == ["UltraLibrarian"]


def test_ultra_sample_part_meta():
    with open_package(UL_ZIP, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        meta = candidate.symbols[0].meta
    assert meta.symbol_name == "CSD85301Q2"
    assert meta.reference == "U"
    assert meta.value == "CSD85301Q2"
    assert meta.footprint_field == "DQK0006B"
    assert meta.datasheet == "https://www.ti.com/lit/gpn/csd85301q2"
    assert meta.keywords == "CSD85301Q2"
    assert meta.fp_filters == "DQK0006B"
    assert meta.description == ""
    assert meta.manufacturer == ""


def test_ultra_sample_staging():
    with zipfile.ZipFile(UL_ZIP) as zf:
        expected = {name: hashlib.sha256(zf.read(name)).hexdigest() for name in zf.namelist()}
    with open_package(UL_ZIP, REPO_ROOT) as package:
        staging = package.staging_dir
        assert staging is not None and staging.is_dir()
        assert not staging.resolve().is_relative_to(REPO_ROOT.resolve())
        assert len(package.files) == 3
        assert all(pf.staged for pf in package.files)
        assert [pf.kind for pf in package.files] == ["model", "symbol", "footprint"]
        assert [pf.path.name for pf in package.files] == [
            "model_000.stp",
            "sym_001.kicad_sym",
            "fp_002.kicad_mod",
        ]
        for pf in package.files:
            assert pf.path.parent == staging
            assert pf.path.is_file()
            assert pf.sha256 == expected[pf.member]
            assert pf.size == pf.path.stat().st_size
        assert package.ignored == UL_IGNORED
        notes = [i for i in package.issues if i.code == "intake.ignored_members"]
        assert len(notes) == 1
        assert notes[0].severity is Severity.INFO
        assert all(name in notes[0].text for name in UL_IGNORED)
    assert not staging.exists()
    package.close()


def test_ultra_explicit_close():
    package = open_package(UL_ZIP, REPO_ROOT)
    candidate, _ = detect_candidate(package)
    assert candidate is not None
    staging = package.staging_dir
    assert staging is not None and staging.is_dir()
    assert all(pf.path.exists() for pf in package.files)
    package.close()
    assert package.staging_dir is None
    assert not staging.exists()
    package.close()


def test_ultra_progress_calls():
    calls = []
    with open_package(UL_ZIP, REPO_ROOT, progress=lambda *a: calls.append(a)):
        pass
    assert [(i, total) for _, i, total in calls] == [(0, 3), (1, 3), (2, 3)]
    assert all(isinstance(message, str) and message for message, _, _ in calls)


def test_ultra_unsupported_and_missing(tmp_path):
    missing = open_package(tmp_path / "nope.zip", REPO_ROOT)
    assert missing.refused
    assert [(i.severity, i.code) for i in missing.issues] == [(Severity.ERROR, "intake.not_found")]

    text = tmp_path / "notes.txt"
    text.write_text("hello", encoding="utf-8")
    unsupported = open_package(text, REPO_ROOT)
    assert unsupported.refused
    assert [(i.severity, i.code) for i in unsupported.issues] == [(Severity.ERROR, "intake.unsupported")]

    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"\x00\x01random bytes that are not a zip" * 20)
    corrupt = open_package(bad, REPO_ROOT)
    assert corrupt.refused
    assert [(i.severity, i.code) for i in corrupt.issues] == [(Severity.ERROR, "intake.corrupt")]
    for package in (missing, unsupported, corrupt):
        package.close()


def test_ultra_suggestion():
    with open_package(UL_ZIP, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        meta = candidate.symbols[0].meta
    suggestion = suggest_library(meta)
    assert suggestion.name == "IC_SubCategory_TI"
    assert suggestion.confidence == "low"
    assert suggestion.placeholders == ("SubCategory",)
    assert suggestion.type == TokenChoice("IC", "reference", True)
    assert suggestion.manufacturer == TokenChoice("TI", "host_table", True)
    assert suggestion.subcategory.source == "placeholder"
    assert suggestion.alternatives == ()
    assert suggestion.matches_existing is False
    codes = {(i.severity, i.code) for i in suggestion.issues}
    assert (Severity.WARNING, "naming.low_confidence") in codes
    assert (Severity.WARNING, "naming.placeholder") in codes


def test_ultra_placeholder_tokens():
    assert placeholder_tokens("IC_SubCategory_TI") == ["SubCategory"]
    assert placeholder_tokens("Type_SubCategory_Manufacturer") == ["Type", "SubCategory", "Manufacturer"]
    assert placeholder_tokens("Transistor_MOSFET_TI") == []
    assert placeholder_tokens("IC_subcategory_TI") == ["SubCategory"]
    assert placeholder_tokens("Connector_USB_TypeC_GCT") == []
