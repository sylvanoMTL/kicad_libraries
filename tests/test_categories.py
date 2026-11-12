"""Category map: a part with no sibling is placed by its vendor category, words or a reference letter (D-04, LIB-04)."""

from pathlib import Path

import pytest

from kicad_lib_manager.importer.candidate import PartMeta
from kicad_lib_manager.importer.categories import REFERENCE_STEMS, RULES, VENDOR_STEMS, classify
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.stems import allowed_stems

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


# -- cases (D-04, RESEARCH A3, A4, Pitfall 4) ----------------------------------------------------------


@pytest.mark.parametrize(
    ("meta", "stem", "source", "detail"),
    [
        (PartMeta("A", reference="Q"), None, "", ""),
        (
            PartMeta("A", reference="Q", description="Dual N-Channel MOSFET"),
            "Transistor_FET",
            "words",
            "the description",
        ),
        # ATXK-H14: a bare X, no category, no description
        (PartMeta("ATXK-H14", reference="X"), None, "", ""),
        (PartMeta("A", reference="Y"), None, "", ""),
        (PartMeta("A", reference="U"), None, "", ""),
        (PartMeta("A", reference="U3"), None, "", ""),
        (PartMeta("A", reference="D1"), None, "", ""),
        (PartMeta("A", reference="J"), "Connector", "reference", "the reference J"),
        (PartMeta("A", reference="SW1"), "Switch", "reference", "the reference SW"),
        (PartMeta("A", reference="JP2"), "Jumper", "reference", "the reference JP"),
        (PartMeta("A", reference="K1"), "Relay", "reference", "the reference K"),
        (PartMeta("A", reference="tr1"), "Transformer", "reference", "the reference TR"),
        (PartMeta("A", reference="M1"), "Motor", "reference", "the reference M"),
        (PartMeta("A", reference="MH1"), None, "", ""),
        (
            PartMeta("A", reference="J", description="USB-C receptacle, 16 pins"),
            "Connector",
            "words",
            "the description",
        ),
        (PartMeta("A", description="32.768 kHz crystal"), None, "", ""),
        (PartMeta("A", reference="Y", description="32.768 kHz crystal"), None, "", ""),
        (PartMeta("A", category="Connectors"), "Connector", "vendor", "the vendor category Connectors"),
        (PartMeta("A", category="Integrated Circuits"), None, "", ""),
        (PartMeta("A", category="Crystals"), None, "", ""),
        (
            PartMeta("A", description="3-axis magnetometer, I2C and SPI"),
            "Sensor_Magnetic",
            "words",
            "the description",
        ),
        (PartMeta("A", description="AC/DC converter 5V"), "Converter_ACDC", "words", "the description"),
        (
            PartMeta("A", description="Isolated 5V DC-DC module"),
            "Converter_DCDC_Isolated",
            "words",
            "the description",
        ),
    ],
)
def test_classify_cases(meta, stem, source, detail):
    match = classify(meta)
    assert (match.stem, match.source, match.detail) == (stem, source, detail)


def test_the_words_come_before_the_reference_letter():
    match = classify(PartMeta("A", reference="J", description="Schottky diode"))
    assert match.stem == "Diode"
    assert match.source == "words"


def test_snapeda_part_without_category_falls_through_to_words_and_reference():
    # PartMeta.category is empty for SnapEDA (RESEARCH Open Question 7)
    words = PartMeta("A", reference="U1", description="Low dropout regulator 3.3V")
    assert classify(words).stem == "Regulator_Linear"
    assert classify(PartMeta("A", reference="J1")).stem == "Connector"


def test_runner_up_lists_the_other_stems_that_also_matched():
    match = classify(PartMeta("A", description="Isolated DC/DC", category="Power Supply"))
    assert match.stem == "Converter_DCDC_Isolated"
    assert "Converter_DCDC" in match.runner_up
    assert match.stem not in match.runner_up
    both = classify(PartMeta("A", description="Schottky diode in a MOSFET"))
    assert both.stem == "Transistor_FET"
    assert "Diode" in both.runner_up


def test_runner_up_is_empty_when_one_rule_matches():
    assert classify(PartMeta("A", description="Schottky diode")).runner_up == ()
    assert classify(PartMeta("A")).runner_up == ()


def test_a_stem_missing_from_the_allowed_set_is_skipped():
    meta = PartMeta("A", reference="Q", description="Dual N-Channel MOSFET")
    assert classify(meta, allowed=frozenset({"Diode"})).stem is None
    pair = PartMeta("A", description="Isolated DC/DC", category="Power Supply")
    assert classify(pair, allowed=frozenset({"Converter_DCDC"})).stem == "Converter_DCDC"


def test_phrase_words_match_whole_words_only():
    # "Converters" is not the whole word "converter"
    assert classify(PartMeta("A", category="Power Supply", description="Converters")).stem is None
    assert classify(PartMeta("A", description="Gold plated")).stem is None


def test_every_rule_target_is_an_allowed_stem():
    allowed = allowed_stems()
    targets = {rule.stem for rule in RULES} | set(VENDOR_STEMS.values()) | set(REFERENCE_STEMS.values())
    assert targets <= allowed
    assert "Crystal" not in targets


def test_only_unambiguous_reference_letters_place_a_part():
    assert set(REFERENCE_STEMS) == {"K", "SW", "TR", "M", "JP", "J"}


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="blanks"),
        pytest.param("!!! ??? ---", id="punctuation"),
        pytest.param("x" * 100_000, id="very-long"),
        pytest.param("é" * 50, id="combining-marks"),
        pytest.param("\\n\\n", id="backslash-n"),
        pytest.param("Ünïcödé ß \u0000 ퟿", id="odd-characters"),
        pytest.param("dc dc " * 5000, id="repeated-phrase"),
    ],
)
def test_classify_never_raises_on_odd_text(text):
    meta = PartMeta("A", reference=text, description=text, keywords=text, category=text)
    match = classify(meta)
    assert match.stem is None or match.stem in allowed_stems()
