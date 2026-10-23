"""SamacSys / Component Search Engine recognition, part_info.txt and the other-CAD summary (INTK-04, D-11 to D-16).

Every test runs on a synthetic zip from vendorfixtures, which reproduces the real layout; the real
download is exercised by tests/test_real_vendor_samples.py where it is present.
"""

from pathlib import Path

from vendorfixtures import (
    SAMACSYS_FOOTPRINT,
    SAMACSYS_MANUFACTURER,
    SAMACSYS_MPN,
    SAMACSYS_OTHER_CAD,
    SAMACSYS_PART,
    SAMACSYS_PART_INFO,
    SAMACSYS_ZIP_NAME,
    samacsys_members,
    samacsys_symbol,
    samacsys_zip,
    snapeda_members,
)
from zipfixtures import (
    CURRENT_CUSTOM_FOOTPRINT_LIBS,
    CURRENT_CUSTOM_SYMBOL_LIBS,
    footprint,
    make_zip,
    symbol_lib,
    write_custom_layout,
)

from kicad_lib_manager.importer import package as package_module
from kicad_lib_manager.importer.adapters.base import PartHints
from kicad_lib_manager.importer.adapters.samacsys import SAMACSYS_RULES, SamacSysAdapter, parse_part_info, part_hints
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.form import field_defaults
from kicad_lib_manager.importer.layout import RepoLayout, list_existing_libraries
from kicad_lib_manager.importer.package import Package, open_package
from kicad_lib_manager.importer.plan import InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.importer.suggest import suggest_library
from kicad_lib_manager.kicad_files import find_property, find_symbol, parse_bytes
from kicad_lib_manager.models import Issue, Severity

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
GENERIC = [("a.kicad_sym", symbol_lib(("A",))), ("b.kicad_mod", footprint("B"))]


def _codes(issues, code):
    return [i for i in issues if i.code == code]


def _open_full(tmp_path, **kwargs):
    return open_package(samacsys_zip(tmp_path / "src" / SAMACSYS_ZIP_NAME, **kwargs), REPO_ROOT)


# -- recognition (D-14, D-15) ----------------------------------------------------------------------


def test_samacsys_full_zip_recognised(tmp_path):
    with _open_full(tmp_path) as package:
        candidate, issues = detect_candidate(package)
        staged = sorted(p.name for p in package.staging_dir.iterdir())
    assert candidate is not None
    assert candidate.vendor == "SamacSys"
    assert candidate.confidence == 1.0
    assert candidate.field_rules == SAMACSYS_RULES
    assert [s.name for s in candidate.symbols] == [SAMACSYS_PART]
    assert [f.name for f in candidate.footprints] == [SAMACSYS_FOOTPRINT]
    assert candidate.footprints[0].root_head == "module"
    assert [m.filename for m in candidate.models] == [f"{SAMACSYS_PART}.stp"]
    assert not _codes(candidate.issues, "intake.unknown_vendor")
    legacy = _codes(candidate.issues, "intake.legacy_ignored")
    assert len(legacy) == 1 and legacy[0].severity is Severity.INFO
    for name in (f"{SAMACSYS_PART}.lib", f"{SAMACSYS_PART}.dcm", f"{SAMACSYS_PART}.mod", f"CADSTAR/{SAMACSYS_PART}.lib"):
        assert name in legacy[0].text
    fp_syntax = _codes(candidate.issues, "intake.legacy_footprint_syntax")
    assert len(fp_syntax) == 1 and fp_syntax[0].severity is Severity.WARNING
    assert not [i for i in candidate.issues if i.severity is Severity.ERROR]
    assert not [i for i in issues if i.severity is Severity.ERROR]
    assert all(name.startswith(("sym_", "fp_", "model_")) for name in staged)
    assert len(staged) == 3


def test_samacsys_markers_only(tmp_path):
    members = [
        *GENERIC,
        ("license.txt", b"licensed by SamacSys Ltd\r\n"),
        ("part_info.txt", b"Manufacturer=Acme\r\nPartNumber=A-1\r\n"),
    ]
    zip_path = make_zip(tmp_path / "pkg.zip", members)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
    assert candidate is not None
    assert candidate.vendor == "SamacSys"
    assert candidate.confidence == 0.5


def test_samacsys_not_claimed_elsewhere(tmp_path):
    from kicad_lib_manager.importer.adapters.snapeda import SnapEDAAdapter

    adapter = SamacSysAdapter()
    with open_package(UL_ZIP, REPO_ROOT) as package:
        assert adapter.detect(package) is None
    snap = make_zip(tmp_path / "snap.zip", snapeda_members())
    with open_package(snap, REPO_ROOT) as package:
        assert adapter.detect(package) is None
        assert SnapEDAAdapter().detect(package) is not None
        candidate, _ = detect_candidate(package)
    assert candidate is not None and candidate.vendor == "SnapEDA"
    generic = make_zip(tmp_path / "generic.zip", GENERIC)
    with open_package(generic, REPO_ROOT) as package:
        assert adapter.detect(package) is None
        candidate, _ = detect_candidate(package)
    assert candidate is not None and candidate.vendor == "Unknown"


def test_samacsys_detect_survives_hand_built_package(tmp_path):
    package = Package(source=tmp_path / "x.zip", kind="zip")
    assert SamacSysAdapter().detect(package) is None


# -- D-16: the other-CAD folders become one line --------------------------------------------------------


def test_folder_summary_replaces_list(tmp_path):
    with _open_full(tmp_path) as package:
        candidate, _ = detect_candidate(package)
        notes = _codes(package.issues, "intake.ignored_members")
        ignored = list(package.ignored)
    assert candidate is not None
    assert len(notes) == 1
    assert notes[0].severity is Severity.INFO
    names = ", ".join(SAMACSYS_OTHER_CAD[:6])
    assert notes[0].text == f"Not imported: other-CAD folders {names}, ... ({len(candidate.ignored)} files)"
    assert candidate.ignored == tuple(ignored)
    for folder in SAMACSYS_OTHER_CAD:
        assert any(f"/{folder}/" in member for member in candidate.ignored)
    assert _codes(candidate.issues, "intake.ignored_members") == notes


def test_folder_summary_leaves_other_vendors_alone(tmp_path):
    snap = make_zip(tmp_path / "snap.zip", snapeda_members())
    with open_package(snap, REPO_ROOT) as package:
        detect_candidate(package)
        notes = _codes(package.issues, "intake.ignored_members")
    assert len(notes) == 1
    assert notes[0].text.startswith("Not imported from snap.zip:")
    with open_package(UL_ZIP, REPO_ROOT) as package:
        detect_candidate(package)
        notes = _codes(package.issues, "intake.ignored_members")
    assert len(notes) == 1
    assert notes[0].text.startswith("Not imported from ")


def test_detect_twice_keeps_one_summary(tmp_path):
    with _open_full(tmp_path) as package:
        first, _ = detect_candidate(package)
        second, _ = detect_candidate(package)
        notes = _codes(package.issues, "intake.ignored_members")
    assert first == second
    assert len(notes) == 1


# -- D-13: part_info.txt is parsed in memory, bounded ----------------------------------------------------


def test_part_info_parse_caps():
    lines = [f"Key{i}=value{i}" for i in range(120)]
    parsed = parse_part_info("\r\n".join(lines))
    assert len(parsed) == 100
    assert "key99" in parsed and "key100" not in parsed

    parsed = parse_part_info("A=b=c\nno equals here\n" + "k" * 41 + "=long key\nVal=x\x00y\tz\x07\nBig=" + "v" * 500 + "\n")
    assert parsed["a"] == "b=c"
    assert "no equals here" not in parsed
    assert "k" * 41 not in parsed
    assert parsed["val"] == "xyz"
    assert parsed["big"] == "v" * 200
    assert parse_part_info("Key=First\r\nKEY=Second\r\n") == {"key": "First"}
    assert parse_part_info("") == {}


def test_part_info_malformed_is_info(tmp_path):
    zip_path = samacsys_zip(tmp_path / "src" / SAMACSYS_ZIP_NAME, part_info=b"nothing useful here\r\njust prose\r\n")
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
    assert candidate is not None
    assert candidate.vendor == "SamacSys"
    notes = _codes(candidate.issues, "intake.part_info_ignored")
    assert len(notes) == 1 and notes[0].severity is Severity.INFO
    assert not [i for i in candidate.issues if i.severity is Severity.ERROR]


def test_part_info_oversized_is_skipped(tmp_path, monkeypatch):
    zip_path = samacsys_zip(tmp_path / "src" / SAMACSYS_ZIP_NAME)
    monkeypatch.setattr(package_module, "MAX_MARKER_BYTES", len(SAMACSYS_PART_INFO) - 1)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        skipped = _codes(package.issues, "intake.marker_skipped")
    assert candidate is not None
    assert candidate.vendor == "SamacSys"
    assert skipped and all(i.severity is Severity.INFO for i in skipped)
    assert not [i for i in candidate.issues if i.severity is Severity.ERROR]


def test_samacsys_symbol_helper_omits_fields():
    assert b"Manufacturer_Name" not in samacsys_symbol(omit=("Manufacturer_Name",))
    assert b"Extra One" in samacsys_symbol(extra=(("Extra One", "x"),))
    assert samacsys_members(part_info=None)[2][0] != f"{SAMACSYS_PART}/part_info.txt"


# -- part_info.txt feeds the suggestion and the fields (D-11, D-12) ------------------------------------------

LIBRARY = "PowerSupply_DCDC_RECOM"


def _layout(root, symbol_libs=CURRENT_CUSTOM_SYMBOL_LIBS, footprint_libs=CURRENT_CUSTOM_FOOTPRINT_LIBS):
    write_custom_layout(root / "repo", symbol_libs, footprint_libs)
    return RepoLayout.for_repo(root / "repo")


def test_samacsys_suggestion(tmp_path):
    existing = list_existing_libraries(_layout(tmp_path))
    with _open_full(tmp_path) as package:
        candidate, _ = detect_candidate(package)
    assert candidate is not None
    suggestion = suggest_library(candidate.symbols[0].meta, existing)
    assert suggestion.name == "PowerSupply_SubCategory_RECOM"
    assert suggestion.placeholders == ("SubCategory",)
    assert suggestion.type.source == "part_info"
    assert suggestion.manufacturer.token == "RECOM"


def test_part_info_fills_missing_fields(tmp_path):
    symbol = samacsys_symbol(omit=("Manufacturer_Name", "Manufacturer_Part_Number"))
    layout = _layout(tmp_path / "lib", [LIBRARY], [LIBRARY])
    zip_path = samacsys_zip(tmp_path / "src" / SAMACSYS_ZIP_NAME, symbol=symbol)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        meta = candidate.symbols[0].meta
        assert (meta.manufacturer, meta.mpn, meta.category) == (SAMACSYS_MANUFACTURER, SAMACSYS_MPN, "Power Supply")
        plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout, ToolContext())
        loaded = parse_bytes(next(op for op in plan.ops if op.kind == "symbol_lib").data, "lib")
        assert not isinstance(loaded, Issue)
        installed = find_symbol(loaded.root, SAMACSYS_PART)
        assert installed is not None
        assert find_property(installed.node, "Manufacturer").value == SAMACSYS_MANUFACTURER
        assert find_property(installed.node, "MPN").value == SAMACSYS_MPN
        assert plan.model_file == f"{SAMACSYS_PART}.stp"
        defaults = field_defaults(candidate, SAMACSYS_PART)
        assert (defaults.manufacturer, defaults.mpn) == (SAMACSYS_MANUFACTURER, SAMACSYS_MPN)


def test_symbol_fields_win_over_part_info(tmp_path):
    symbol = samacsys_symbol(
        omit=("Manufacturer_Name", "Manufacturer_Part_Number"),
        extra=(("MF", "Other Corp"), ("MPN", "MY-1")),
    )
    zip_path = samacsys_zip(tmp_path / "src" / SAMACSYS_ZIP_NAME, symbol=symbol)
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
    assert candidate is not None
    meta = candidate.symbols[0].meta
    assert (meta.manufacturer, meta.mpn) == ("Other Corp", "MY-1")
    assert meta.category == "Power Supply"


def test_mpn_hint_needs_one_symbol(tmp_path):
    symbol = symbol_lib(("PSU_A", "PSU_B"))
    zip_path = make_zip(tmp_path / "pkg.zip", samacsys_members(symbol=symbol))
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
    assert candidate is not None
    assert candidate.vendor == "SamacSys"
    assert [s.name for s in candidate.symbols] == ["PSU_A", "PSU_B"]
    for item in candidate.symbols:
        assert item.meta.mpn == ""
        assert item.meta.manufacturer == SAMACSYS_MANUFACTURER
        assert item.meta.category == "Power Supply"


def test_part_hints_none_when_empty():
    assert part_hints({}) is None
    assert part_hints({"version": "1"}) is None
    assert part_hints({"partcategory": "Power Supply"}) == PartHints(category="Power Supply")
