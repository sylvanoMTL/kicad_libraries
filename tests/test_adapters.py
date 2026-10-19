"""Importer intake on the Ultra Librarian sample: D-01, D-02, D-04, D-07, D-09, INTK-02."""

import hashlib
import zipfile
from pathlib import Path

from zipfixtures import STEP_BYTES, VRML_BYTES, footprint, make_zip, symbol_lib

from kicad_lib_manager.importer import package as package_module
from kicad_lib_manager.importer.adapters.base import Detection, locate
from kicad_lib_manager.importer.detect import ADAPTERS, detect_candidate
from kicad_lib_manager.importer.package import Package, PackageFile, open_package
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


# -- plan 03-04 task 1: content checks, versions, all items (D-13, D-18) ----------


def _detect_zip(tmp_path, members, name="pkg.zip"):
    """Open a synthetic zip, detect it and return (candidate, issues, staged member names)."""
    zip_path = make_zip(tmp_path / name, members)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, issues = detect_candidate(package)
        staged = [pf.member for pf in package.files]
    return candidate, issues, staged


def _codes(issues, code):
    return [i for i in issues if i.code == code]


GOOD_PAIR = [("good.kicad_sym", symbol_lib(("GOOD",))), ("good.kicad_mod", footprint("GOODFP"))]


def test_locate_versions_on_ul():
    with open_package(UL_ZIP, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
    assert candidate.symbols[0].format_version == 20211014
    assert candidate.footprints[0].format_version == 20211014
    assert candidate.footprints[0].root_head == "footprint"
    assert candidate.footprints[0].has_embedded_files is False


def test_locate_all_items(tmp_path):
    members = [
        ("a.kicad_sym", symbol_lib(("A", "B"))),
        ("b.kicad_sym", symbol_lib(("C",))),
        ("f1.kicad_mod", footprint("F1")),
        ("f2.kicad_mod", footprint("F2")),
        ("m1.step", STEP_BYTES),
        ("m2.wrl", VRML_BYTES),
    ]
    candidate, issues, _ = _detect_zip(tmp_path, members)
    assert [s.name for s in candidate.symbols] == ["A", "B", "C"]
    assert [f.name for f in candidate.footprints] == ["F1", "F2"]
    assert [m.filename for m in candidate.models] == ["m1.step", "m2.wrl"]
    assert not _errors(issues)


def test_locate_content_mismatch(tmp_path):
    members = GOOD_PAIR + [
        ("bad1.kicad_sym", footprint("NOTSYM")),
        ("bad2.kicad_mod", symbol_lib(("NOTFP",))),
        ("bad3.kicad_sym", symbol_lib(())),
        ("bad4.step", b"hello"),
        ("bad5.wrl", STEP_BYTES),
        ("bad6.kicad_sym", b"(kicad_symbol_lib \xff\xfe)"),
        ("bad7.kicad_mod", b'(footprint "x" (layer'),
    ]
    candidate, issues, staged = _detect_zip(tmp_path, members)
    assert len(staged) == 9
    mismatches = _codes(issues, "intake.content_mismatch")
    assert len(mismatches) == 5
    assert all(i.severity is Severity.WARNING for i in mismatches)
    for member in ("bad1.kicad_sym", "bad2.kicad_mod", "bad3.kicad_sym", "bad4.step", "bad5.wrl"):
        assert len([i for i in mismatches if member in i.text]) == 1, member
    unreadable = _codes(issues, "intake.unreadable_file")
    assert len(unreadable) == 2
    assert all(i.severity is Severity.WARNING for i in unreadable)
    for member in ("bad6.kicad_sym", "bad7.kicad_mod"):
        assert len([i for i in unreadable if member in i.text]) == 1, member
    assert [s.name for s in candidate.symbols] == ["GOOD"]
    assert [f.name for f in candidate.footprints] == ["GOODFP"]
    assert candidate.models == ()


def test_locate_step_with_bom_and_whitespace(tmp_path):
    members = GOOD_PAIR + [("part.stp", b"\xef\xbb\xbf\r\n  " + STEP_BYTES)]
    candidate, issues, _ = _detect_zip(tmp_path, members)
    assert [m.filename for m in candidate.models] == ["part.stp"]
    assert not _codes(issues, "intake.content_mismatch")


def test_locate_legacy_module_syntax(tmp_path):
    members = [
        ("s.kicad_sym", symbol_lib(("S",))),
        ("old.kicad_mod", footprint("OLD", head="module", version=None)),
    ]
    candidate, issues, _ = _detect_zip(tmp_path, members)
    assert [f.name for f in candidate.footprints] == ["OLD"]
    assert candidate.footprints[0].root_head == "module"
    assert candidate.footprints[0].format_version is None
    notes = _codes(issues, "intake.legacy_footprint_syntax")
    assert len(notes) == 1
    assert notes[0].severity is Severity.WARNING
    assert "old.kicad_mod" in notes[0].text


def test_locate_embedded_files_flag(tmp_path):
    embedded = (
        b'(footprint "EMB" (version 20211014) (layer "F.Cu")\n'
        b'  (embedded_files (file (name "x.step") (type model))))\n'
    )
    nested = b'(footprint "NEST" (version 20211014) (layer "F.Cu") (group (embedded_files)))\n'
    members = [
        ("s.kicad_sym", symbol_lib(("S",))),
        ("emb.kicad_mod", embedded),
        ("nest.kicad_mod", nested),
        ("plain.kicad_mod", footprint("PLAIN")),
    ]
    candidate, _, _ = _detect_zip(tmp_path, members)
    flags = {f.name: f.has_embedded_files for f in candidate.footprints}
    assert flags == {"EMB": True, "NEST": False, "PLAIN": False}


def test_locate_part_meta_fields(tmp_path):
    members = [
        ("a.kicad_sym", symbol_lib(("A",), props={"Description": "Buck", "MF": "Texas Instruments", "MP": "TPS1"})),
        ("b.kicad_sym", symbol_lib(("B",), props={"ki_description": "Only ki"})),
        ("c.kicad_sym", symbol_lib(("C",), props={"MF": "Short", "Manufacturer": "Long"})),
        ("f.kicad_mod", footprint("F")),
    ]
    candidate, _, _ = _detect_zip(tmp_path, members)
    a, b, c = (s.meta for s in candidate.symbols)
    assert (a.description, a.manufacturer, a.mpn) == ("Buck", "Texas Instruments", "TPS1")
    assert b.description == "Only ki"
    assert c.manufacturer == "Long"


def test_locate_oversize_file_skipped(tmp_path, monkeypatch):
    folder = tmp_path / "loose"
    folder.mkdir()
    fp_path = folder / "small.kicad_mod"
    fp_path.write_bytes(footprint("SMALL"))
    sym_path = folder / "big.kicad_sym"
    sym_path.write_bytes(symbol_lib(("BIG",), props={"Description": "x" * 4000}))
    fp_size, sym_size = fp_path.stat().st_size, sym_path.stat().st_size
    assert fp_size < sym_size
    monkeypatch.setattr(package_module, "MAX_MEMBER_BYTES", (fp_size + sym_size) // 2)
    package = Package(
        source=folder,
        kind="folder",
        names=["small.kicad_mod", "big.kicad_sym"],
        files=[
            PackageFile("small.kicad_mod", fp_path, "footprint", fp_size, "0" * 64, False),
            PackageFile("big.kicad_sym", sym_path, "symbol", sym_size, "0" * 64, False),
        ],
    )
    candidate, issues = locate(package, Detection("Loose", 0.3))
    skipped = _codes(issues, "intake.unreadable_file")
    assert len(skipped) == 1
    assert skipped[0].severity is Severity.WARNING
    assert "big.kicad_sym" in skipped[0].text
    assert candidate.symbols == ()
    assert [f.name for f in candidate.footprints] == ["SMALL"]


def test_locate_casefolded_markers(tmp_path):
    members = [
        ("KICADV6/2020-01-01_00-00-00.KICAD_SYM", symbol_lib(("Part_Ω",))),
        ("KICADV6/FOOTPRINTS.PRETTY/X.KICAD_MOD", footprint("X")),
        ("importguides.HTML", b"<html></html>"),
    ]
    candidate, _, staged = _detect_zip(tmp_path, members)
    assert candidate.vendor == "UltraLibrarian"
    assert len(staged) == 2
    assert [s.name for s in candidate.symbols] == ["Part_Ω"]
    assert [f.name for f in candidate.footprints] == ["X"]
