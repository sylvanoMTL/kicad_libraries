"""Category map: a part with no sibling is placed by its vendor category, words or a reference letter (D-04, LIB-04)."""

from pathlib import Path

import pytest

from kicad_lib_manager.importer.candidate import PartMeta
from kicad_lib_manager.importer.categories import classify
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.package import open_package

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_SAMACSYS = REPO_ROOT / "downloaded_examples" / "LIB_RS3-1212S_H3.zip"
_SAMACSYS_SKIP = "downloaded_examples/LIB_RS3-1212S_H3.zip not present (licence-restricted SamacSys sample, kept local)"
requires_samacsys = pytest.mark.skipif(not REAL_SAMACSYS.exists(), reason=_SAMACSYS_SKIP)


# -- tracer: the RECOM isolated module (ROADMAP criterion 1) -------------------------------------------


def test_isolated_dcdc_module_is_placed_by_vendor_category_and_description():
    meta = PartMeta(
        "RS3-1212S_H3",
        reference="PS",
        description="Isolated DC/DC Converters 3W 12Vin 12Vout",
        category="Power Supply",
    )
    match = classify(meta)
    assert match.stem == "Converter_DCDC_Isolated"
    assert match.source == "vendor"
    assert match.detail == "the vendor category Power Supply and the description"


@requires_samacsys
def test_real_samacsys_download_is_placed_in_converter_dcdc_isolated():
    with open_package(REAL_SAMACSYS, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
    assert candidate is not None
    match = classify(candidate.symbols[0].meta)
    assert match.stem == "Converter_DCDC_Isolated"
    assert match.source == "vendor"
