"""Tests on the owner's local vendor downloads (D-02), run automatically when the zip is present.

The vendor zips in downloaded_examples/ are licence-restricted and never committed (D-01); the
folder is git-ignored apart from the Ultra Librarian sample. A test skips by file name when its
zip is absent, so a fresh clone stays green without any environment variable. The zips are only
read, through open_package, which stages outside the repo.
"""

import re
import subprocess
import tempfile
from pathlib import Path

import pytest
from gitfixtures import GIT, requires_git
from zipfixtures import CURRENT_CUSTOM_FOOTPRINT_LIBS, CURRENT_CUSTOM_SYMBOL_LIBS

from kicad_lib_manager.importer.candidate import ExistingLibrary
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.suggest import suggest_library

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = REPO_ROOT / "downloaded_examples"
REAL_SNAPEDA = SAMPLES / "USB4145-03-0170-C_REVA2.zip"
REAL_SAMACSYS = SAMPLES / "LIB_RS3-1212S_H3.zip"

requires_snapeda = pytest.mark.skipif(
    not REAL_SNAPEDA.exists(),
    reason="downloaded_examples/USB4145-03-0170-C_REVA2.zip not present (licence-restricted SnapEDA sample, kept local)",
)
requires_samacsys = pytest.mark.skipif(
    not REAL_SAMACSYS.exists(),
    reason="downloaded_examples/LIB_RS3-1212S_H3.zip not present (licence-restricted SamacSys sample, kept local)",
)


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
    existing = [
        ExistingLibrary(name, name in CURRENT_CUSTOM_SYMBOL_LIBS, name in CURRENT_CUSTOM_FOOTPRINT_LIBS)
        for name in CURRENT_CUSTOM_SYMBOL_LIBS
    ]
    with open_package(REAL_SNAPEDA, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
    assert candidate is not None
    suggestion = suggest_library(candidate.symbols[0].meta, existing)
    assert suggestion.name == "Connector_USB_GCT"


def _check_ignore(relative: str) -> int:
    return subprocess.run(
        [GIT, "check-ignore", "-q", relative], cwd=REPO_ROOT, capture_output=True, check=False
    ).returncode


@requires_git
def test_vendor_zips_stay_local():
    assert _check_ignore("downloaded_examples/USB4145-03-0170-C_REVA2.zip") == 0
    assert _check_ignore("downloaded_examples/LIB_RS3-1212S_H3.zip") == 0
    assert _check_ignore("downloaded_examples/ul_CSD85301Q2.zip") == 1
    listed = subprocess.run(
        [GIT, "ls-files", "downloaded_examples"], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.split()
    assert listed == ["downloaded_examples/ul_CSD85301Q2.zip"]
