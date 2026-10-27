"""Tests on the owner's local vendor downloads (D-02), run automatically when the zip is present.

The vendor zips in downloaded_examples/ are licence-restricted and never committed (D-01); the
folder is git-ignored apart from the Ultra Librarian sample. A test skips by file name when its
zip is absent, so a fresh clone stays green without any environment variable. The zips are only
read, through open_package, which stages outside the repo.
"""

import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest
from gitfixtures import GIT, requires_git
from zipfixtures import (
    CURRENT_ATOMIC_FOOTPRINT_LIBS,
    CURRENT_ATOMIC_SYMBOL_LIBS,
    footprint_library_for,
    write_custom_layout,
)

from kicad_lib_manager.importer import kicad_cli
from kicad_lib_manager.importer.adapters.base import attach_models
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.kicad_cli import stock_symbols_dir
from kicad_lib_manager.importer.package import open_model_source, open_package
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.importer.siblings import stock_index
from kicad_lib_manager.importer.suggest import suggest_library, suggestion_text
from kicad_lib_manager.library_scanner import find_kicad_footprint_dir
from kicad_lib_manager.kicad_files import find_models, find_symbol, footprint_name, list_properties, load
from kicad_lib_manager.models import Issue, Severity

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = REPO_ROOT / "downloaded_examples"
REAL_SNAPEDA = SAMPLES / "USB4145-03-0170-C_REVA2.zip"
REAL_SAMACSYS = SAMPLES / "LIB_RS3-1212S_H3.zip"
REAL_SNAPEDA_MODEL = SAMPLES / "194150990-659-usb4145-03-0170-c.zip"
# Install targets, both entries of CURRENT_ATOMIC_SYMBOL_LIBS (D-08)
SNAPEDA_LIBRARY = "Atomic_Connector"
SAMACSYS_LIBRARY = "Atomic_Converter_DCDC_Isolated"

_SNAPEDA_SKIP = "downloaded_examples/USB4145-03-0170-C_REVA2.zip not present (licence-restricted SnapEDA sample, kept local)"
requires_snapeda = pytest.mark.skipif(not REAL_SNAPEDA.exists(), reason=_SNAPEDA_SKIP)
_SAMACSYS_SKIP = "downloaded_examples/LIB_RS3-1212S_H3.zip not present (licence-restricted SamacSys sample, kept local)"
requires_samacsys = pytest.mark.skipif(not REAL_SAMACSYS.exists(), reason=_SAMACSYS_SKIP)
_SNAPEDA_MODEL_SKIP = (
    "downloaded_examples/194150990-659-usb4145-03-0170-c.zip not present "
    "(licence-restricted SnapEDA 3D model download, kept local)"
)
requires_snapeda_model = pytest.mark.skipif(not REAL_SNAPEDA_MODEL.exists(), reason=_SNAPEDA_MODEL_SKIP)
NO_CLI = ToolContext()


@pytest.fixture
def staging_root(tmp_path, monkeypatch):
    """Point tempfile at a fresh folder so the staging folder can be listed."""
    folder = tmp_path / "tmp"
    folder.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(folder))
    return folder


@requires_snapeda
def test_real_snapeda_recognised(staging_root):
    with open_package(REAL_SNAPEDA, REPO_ROOT) as package:
        assert package.refused is False
        assert "how-to-import.htm" in package.markers
        staged = sorted(p.name for p in package.staging_dir.iterdir())
        assert staged and all(re.fullmatch(r"(sym|fp)_\d{3}\.kicad_(sym|mod)", n) for n in staged)
        candidate, _ = detect_candidate(package)
    assert candidate is not None
    assert candidate.vendor == "SnapEDA"
    assert candidate.confidence == 1.0
    assert [s.name for s in candidate.symbols] == ["USB4145-03-0170-C_REVA2"]
    assert [f.name for f in candidate.footprints] == ["GCT_USB4145-03-0170-C_REVA2"]
    assert candidate.models == ()
    codes = [i.code for i in candidate.issues]
    assert "intake.no_model" in codes
    assert "intake.unknown_vendor" not in codes


@requires_snapeda
def test_real_snapeda_suggestion(staging_root):
    with open_package(REAL_SNAPEDA, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
    assert candidate is not None
    suggestion = suggest_library(candidate.symbols[0].meta, stock=None)
    assert suggestion.name == "Atomic_Connector"


def _check_ignore(relative: str) -> int:
    return subprocess.run(
        [GIT, "check-ignore", "-q", relative], cwd=REPO_ROOT, capture_output=True, check=False
    ).returncode


@requires_git
def test_vendor_zips_stay_local():
    assert _check_ignore("downloaded_examples/USB4145-03-0170-C_REVA2.zip") == 0
    assert _check_ignore("downloaded_examples/LIB_RS3-1212S_H3.zip") == 0
    assert _check_ignore("downloaded_examples/194150990-659-usb4145-03-0170-c.zip") == 0
    assert _check_ignore("downloaded_examples/ul_CSD85301Q2.zip") == 1
    listed = subprocess.run(
        [GIT, "ls-files", "downloaded_examples"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    assert listed == ["downloaded_examples/ul_CSD85301Q2.zip"]


# -- the real SamacSys download (D-02, D-11, D-16) ---------------------------------------------------------


@requires_samacsys
def test_real_samacsys_recognised(staging_root):
    with open_package(REAL_SAMACSYS, REPO_ROOT) as package:
        assert package.refused is False
        candidate, _ = detect_candidate(package)
        notes = [i for i in package.issues if i.code == "intake.ignored_members"]
    assert candidate is not None
    assert candidate.vendor == "SamacSys"
    assert candidate.confidence == 1.0
    assert [s.name for s in candidate.symbols] == ["RS3-1212S_H3"]
    assert [f.name for f in candidate.footprints] == ["RS3"]
    assert candidate.footprints[0].root_head == "module"
    assert [m.filename for m in candidate.models] == ["RS3-1212S_H3.stp"]

    by_code = {}
    for issue in candidate.issues:
        by_code.setdefault(issue.code, []).append(issue)
    assert "intake.unknown_vendor" not in by_code
    assert [i.severity for i in by_code["intake.legacy_ignored"]] == [Severity.INFO]
    assert [i.severity for i in by_code["intake.legacy_footprint_syntax"]] == [Severity.WARNING]
    assert not [i for i in candidate.issues if i.severity is Severity.ERROR]
    assert sorted(candidate.legacy_ignored) == sorted(
        [
            "RS3-1212S_H3/KiCad/RS3-1212S_H3.lib",
            "RS3-1212S_H3/KiCad/RS3-1212S_H3.dcm",
            "RS3-1212S_H3/KiCad/RS3-1212S_H3.mod",
            "RS3-1212S_H3/CADSTAR/RS3-1212S_H3.lib",
        ]
    )

    assert len(notes) == 1
    assert notes[0].text.startswith("Not imported: other-CAD folders ")
    assert notes[0].text.endswith("(62 files)")
    assert len(candidate.ignored) == 62


@requires_samacsys
def test_real_samacsys_suggestion(staging_root):
    with open_package(REAL_SAMACSYS, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
    assert candidate is not None
    meta = candidate.symbols[0].meta
    assert meta.manufacturer == "RECOM Power"
    assert meta.mpn == "RS3-1212S/H3"
    assert meta.category == "Power Supply"
    suggestion = suggest_library(meta, stock=None)
    assert suggestion.name == "Atomic_Converter_DCDC_Isolated"
    assert suggestion.source == "category"


# -- the suggestion on the real downloads with a real KiCad 10 (LIB-04, ROADMAP criterion 1) ---------------

REAL_UL_CSD = SAMPLES / "ul_CSD85301Q2.zip"
REAL_UL_ATXK = SAMPLES / "ul_ATXK-H14-D-32-768KHZ-E50-T3.zip"
_LIVE_SYMBOLS = stock_symbols_dir(find_kicad_footprint_dir())
_LIVE_IS_KICAD_10 = _LIVE_SYMBOLS is not None and (_LIVE_SYMBOLS / "Converter_DCDC_Isolated.kicad_sym").is_file()
requires_kicad_10 = pytest.mark.skipif(
    not _LIVE_IS_KICAD_10, reason="no KiCad 10 install with a stock symbols folder"
)


def _first_meta(zip_path):
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
    assert candidate is not None
    return candidate.symbols[0].meta


@requires_kicad_10
@pytest.mark.skipif(not REAL_UL_CSD.exists(), reason="downloaded_examples/ul_CSD85301Q2.zip not present")
def test_real_ultra_suggestion_from_kicad_10(staging_root):
    suggestion = suggest_library(_first_meta(REAL_UL_CSD), stock=stock_index(_LIVE_SYMBOLS))
    assert suggestion.name == "Atomic_Transistor_FET"
    assert suggestion.source == "stock"
    assert suggestion_text(suggestion) == (
        "Suggested from 75 similar parts in KiCad's Transistor_FET. Other matches: Diode (2)."
    )


@requires_kicad_10
@pytest.mark.skipif(not REAL_UL_ATXK.exists(), reason="downloaded_examples/ul_ATXK-H14-D-32-768KHZ-E50-T3.zip not present")
def test_real_ultra_oscillator_is_left_for_the_owner(staging_root):
    suggestion = suggest_library(_first_meta(REAL_UL_ATXK), stock=stock_index(_LIVE_SYMBOLS))
    assert suggestion.name == ""
    assert suggestion.source == "ask"


# -- the real downloads installed into a synthetic Custom/ (D-03) ------------------------------------------


@contextmanager
def _installed(zip_path, library, tmp_path, tools=NO_CLI):
    """Install a real zip into a synthetic Custom/ built under tmp_path; yield (layout, plan, result)."""
    write_custom_layout(tmp_path / "repo", CURRENT_ATOMIC_SYMBOL_LIBS, CURRENT_ATOMIC_FOOTPRINT_LIBS)
    layout = RepoLayout.for_repo(tmp_path / "repo")
    with open_package(zip_path, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        plan = build_plan(candidate, InstallOptions(library=library), layout, tools)
        assert not plan.blocked, [i.text for i in plan.issues]
        yield layout, plan, apply_plan(plan, backup_root=tmp_path / "bk")


def _symbol_values(layout, library, name):
    loaded = load(layout.symbols_dir / f"{library}.kicad_sym")
    assert not isinstance(loaded, Issue), loaded
    symbol = find_symbol(loaded.root, name)
    assert symbol is not None
    return {p.name: p.value for p in list_properties(symbol.node)}


def _errors(issues):
    return [i for i in issues if i.severity is Severity.ERROR]


@requires_snapeda
def test_real_snapeda_installs(staging_root, tmp_path):
    library = SNAPEDA_LIBRARY
    with _installed(REAL_SNAPEDA, library, tmp_path) as (layout, plan, result):
        assert result.ok, [i.text for i in result.issues]
        issues = [*plan.issues, *result.issues]
        values = _symbol_values(layout, library, "USB4145-03-0170-C_REVA2")
    assert values["Footprint"] == f"{footprint_library_for(library)}:GCT_USB4145-03-0170-C_REVA2"
    assert values["Value"] == "USB4145-03-0170-C"  # Value is the MPN, not the symbol name (D-22)
    assert values["Manufacturer"] == "Global Connector Technology"
    assert values["MPN"] == "USB4145-03-0170-C"
    assert values["Description"] == "Type C USB 2.0 Connector"
    for gone in ("MANUFACTURER", "SNAPEDA_PN", "Price", "Check_prices", "Availability", "Package"):
        assert gone not in values, gone
    assert [i.severity for i in plan.issues if i.code == "install.no_model"] == [Severity.WARNING]
    assert "verify.pin_pad_mismatch" not in [i.code for i in issues]
    assert not _errors(issues)


# -- the real SnapEDA 3D model download, the second file of the two-file delivery (G-07-2, D-02) ----------


@requires_snapeda_model
def test_real_snapeda_model_zip_opens(staging_root):
    with open_model_source(REAL_SNAPEDA_MODEL, REPO_ROOT) as package:
        assert package.refused is False
        assert package.kind == "zip"
        assert [f.member for f in package.files] == ["usb4145-03-0170-c.stp"]
        model = package.files[0]
        assert model.kind == "model"
        assert model.staged is True
        assert model.size == 2443718
        staging = package.staging_dir
        assert staging is not None
        assert model.path.is_relative_to(staging)
        assert staging.is_relative_to(staging_root)
        assert not staging.is_relative_to(REPO_ROOT)
        with model.path.open("rb") as handle:
            assert handle.read(len(b"ISO-10303-21;")) == b"ISO-10303-21;"
        assert package.ignored == ["usb4145-03-0170-c.txt"]
    assert not staging.exists()


@requires_snapeda
@requires_snapeda_model
def test_real_snapeda_installs_with_separate_model(staging_root, tmp_path):
    library = SNAPEDA_LIBRARY
    write_custom_layout(tmp_path / "repo", CURRENT_ATOMIC_SYMBOL_LIBS, CURRENT_ATOMIC_FOOTPRINT_LIBS)
    layout = RepoLayout.for_repo(tmp_path / "repo")
    # Both packages stay open until apply_plan has returned: the plan reads the staged model from the second one.
    with (
        open_package(REAL_SNAPEDA, REPO_ROOT) as package,
        open_model_source(REAL_SNAPEDA_MODEL, REPO_ROOT) as model_package,
    ):
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        attached, _ = attach_models(candidate, model_package)
        assert attached is not None
        plan = build_plan(attached, InstallOptions(library=library), layout, NO_CLI)
        assert not plan.blocked, [i.text for i in plan.issues]
        result = apply_plan(plan, backup_root=tmp_path / "bk")
        assert result.ok, [i.text for i in result.issues]
        issues = [*plan.issues, *result.issues]
        values = _symbol_values(layout, library, "USB4145-03-0170-C_REVA2")
        installed = layout.footprints_dir / f"{footprint_library_for(library)}.pretty" / "GCT_USB4145-03-0170-C_REVA2.kicad_mod"
        footprint = load(installed)
        model_file = layout.models_dir / "USB4145-03-0170-C.stp"
        model_size = model_file.stat().st_size
    assert plan.model_file == "USB4145-03-0170-C.stp"
    codes = [i.code for i in issues]
    assert "intake.model_attached" in codes
    assert "intake.no_model" not in codes
    assert "install.no_model" not in codes
    assert model_size == 2443718
    assert [m.path for m in find_models(footprint_name(footprint.root).node)] == [
        f"{MODEL_DIR_VAR}/USB4145-03-0170-C.stp"
    ]
    assert values["Footprint"] == f"{footprint_library_for(library)}:GCT_USB4145-03-0170-C_REVA2"
    assert not _errors(issues)


@requires_samacsys
def test_real_samacsys_installs(staging_root, tmp_path):
    library = SAMACSYS_LIBRARY
    with _installed(REAL_SAMACSYS, library, tmp_path) as (layout, plan, result):
        assert result.ok, [i.text for i in result.issues]
        issues = [*plan.issues, *result.issues]
        values = _symbol_values(layout, library, "RS3-1212S_H3")
        footprint = load(layout.footprints_dir / f"{footprint_library_for(library)}.pretty" / "RS3.kicad_mod")
        assert (layout.models_dir / "RS3-1212S_H3.stp").is_file()
    assert [m.path for m in find_models(footprint_name(footprint.root).node)] == [f"{MODEL_DIR_VAR}/RS3-1212S_H3.stp"]
    assert values["Footprint"] == f"{footprint_library_for(library)}:RS3"
    # part_info.txt says "RECOM Power"; the symbol is written in the canonical spelling (D-23)
    assert values["Manufacturer"] == "RECOM"
    assert values["MPN"] == "RS3-1212S/H3"
    assert "Mouser Part Number" in values
    for gone in ("Mouser Price/Stock", "Arrow Price/Stock", "Height", "Arrow Part Number"):
        assert gone not in values, gone
    assert not _errors(issues)


@pytest.mark.kicad_cli
@pytest.mark.parametrize(
    ("zip_path", "library", "footprint"),
    [
        pytest.param(
            REAL_SNAPEDA, SNAPEDA_LIBRARY, "GCT_USB4145-03-0170-C_REVA2", id="snapeda", marks=requires_snapeda
        ),
        pytest.param(REAL_SAMACSYS, SAMACSYS_LIBRARY, "RS3", id="samacsys", marks=requires_samacsys),
    ],
)
def test_real_vendor_installs_load_in_kicad(
    staging_root, tmp_path, real_tools, kicad_cli_path, zip_path, library, footprint
):
    with _installed(zip_path, library, tmp_path, tools=real_tools) as (layout, _, result):
        assert result.ok, [i.text for i in result.issues]
        fp_path = layout.footprints_dir / f"{footprint_library_for(library)}.pretty" / f"{footprint}.kicad_mod"
        fp_bytes = fp_path.read_bytes()
        symbol_lib = (layout.symbols_dir / f"{library}.kicad_sym").read_bytes()
        issues = kicad_cli.load_gate(
            kicad_cli_path, library=library, symbol_lib=symbol_lib, footprints=[(footprint, fp_bytes)]
        )
    assert _errors(issues) == [], issues
