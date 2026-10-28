"""Keyword generation and the vendor merge: single words, KiCad 10 chooser search (FLD-01, D-26, D-27)."""

import pytest
from customfixtures import ABSENT_LIBRARY

from kicad_lib_manager.importer.keywords import (
    CASED_INTERFACE_WORDS,
    FUNCTION_WORDS,
    INTERFACE_WORDS,
    JUNK_WORDS,
    generate_keywords,
    manufacturer_words,
    merge_words,
    split_words,
)
from kicad_lib_manager.importer.plan import InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan


def _generate(**overrides):
    values = {
        "library": "Atomic_Transistor_FET",
        "description": "",
        "category": "",
        "package_words": [],
        "manufacturer": "",
        "mpn": "",
        "symbol_name": "PART",
    }
    values.update(overrides)
    return generate_keywords(**values)


# -- split_words and merge_words (D-27) ----------------------------------------------------------------


def test_split_words_splits_on_blanks_commas_and_semicolons_and_strips_brackets():
    assert split_words("power  MOSFET, dual;N-channel (DC/DC)") == ["power", "MOSFET", "dual", "N-channel", "DC/DC"]


@pytest.mark.parametrize("text", ["", "   ", ",;", "()"])
def test_split_words_gives_nothing_for_blank_text(text):
    assert split_words(text) == []


def test_split_words_strips_quotes():
    assert split_words("'quoted' \"double\"") == ["quoted", "double"]


def test_merge_words_keeps_vendor_words_first_and_adds_new_generated_words():
    assert merge_words("power MOSFET digikey", ["mosfet", "TI", "power"]) == "power MOSFET TI"


def test_merge_words_with_no_vendor_words_uses_the_generated_ones():
    assert merge_words("", ["TI", "Texas"]) == "TI Texas"


def test_merge_words_drops_junk_and_keeps_the_rest_of_the_vendor_text():
    assert merge_words("price 1.23 stock", []) == "1.23"


def test_merge_words_ignores_case_when_matching_and_repeats_in_generated():
    assert merge_words("Texas", ["texas", "TI", "ti"]) == "Texas TI"


# -- manufacturer_words (D-26) -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "words"),
    [
        ("Texas Instruments", ["TI", "Texas"]),
        ("TI", ["TI", "Texas"]),
        ("Maxim Integrated", ["Maxim", "ADI", "Analog"]),
        ("Linear Technology", ["Linear", "ADI", "Analog"]),
        ("InvenSense", ["InvenSense", "TDK"]),
        ("RECOM Power", ["RECOM"]),
        ("Unknown Corp", ["Unknown"]),
        ("", []),
        ("   ", []),
    ],
)
def test_manufacturer_words(name, words):
    assert manufacturer_words(name) == words


def test_manufacturer_words_names_the_parent_brand_of_an_acquired_maker():
    assert {"ADI", "Analog"} <= set(manufacturer_words("Maxim Integrated"))


# -- generate_keywords (FLD-01, D-26) ------------------------------------------------------------------


def test_csd_case_gives_stem_package_manufacturer_and_related_words():
    words = generate_keywords(
        library="Atomic_Transistor_FET",
        description="",
        category="",
        package_words=["WSON-6", "DQK0006B"],
        manufacturer="Texas Instruments",
        mpn="CSD85301Q2",
        symbol_name="CSD85301Q2",
        related=["Diode"],
    )
    assert words == ["Transistor", "FET", "WSON-6", "DQK0006B", "TI", "Texas", "Diode"]


def test_rs3_case_gives_stem_function_package_manufacturer_mpn_and_category_words():
    words = generate_keywords(
        library="Atomic_Converter_DCDC_Isolated",
        description="Isolated DC/DC Converters 3W",
        category="Power Supply",
        package_words=["RS3"],
        manufacturer="RECOM",
        mpn="RS3-1212S/H3",
        symbol_name="RS3-1212S_H3",
        related=["Converter_DCDC"],
    )
    # The stem's "Isolated" wins over the description's "isolated"; "Converters" is not the whole word "converter"
    assert words == ["Converter", "DCDC", "Isolated", "DC-DC", "RS3", "RECOM", "RS3-1212S/H3", "Power", "Supply"]


def test_interface_words_come_from_the_description():
    words = _generate(description="3-axis magnetometer, I2C and SPI")
    assert "magnetometer" in words
    assert "I2C" in words
    assert "SPI" in words


def test_function_words_match_whole_phrases_only():
    assert "converter" in _generate(description="DC/DC converter")
    assert "converter" not in _generate(description="converters")
    assert "N-channel" in _generate(description="Dual N-Channel MOSFET")
    assert "MOSFET" in _generate(description="mosfet")
    assert "USB-C" in _generate(description="Type-C receptacle")


def test_no_item_holds_whitespace_or_an_equals_sign():
    words = _generate(
        description="Vout=12V Vin=5V 3.3 V regulator",
        category="Vout=12 power supply",
        package_words=["SOT 23", "a=b", "QFN-8"],
        manufacturer="Unknown Corp",
    )
    assert "QFN-8" in words
    for word in words:
        assert not any(c.isspace() for c in word), word
        assert "=" not in word, word
    assert "Vout=12V" not in words
    assert "Vout=12" not in words


def test_no_item_is_a_junk_word():
    words = _generate(
        description="price stock digikey",
        category="Mouser Price",
        package_words=["Stock", "SOT-23"],
        mpn="LCSC",
    )
    assert "SOT-23" in words
    assert not {word.casefold() for word in words} & JUNK_WORDS


def test_repeats_are_dropped_ignoring_case_and_the_first_spelling_stays():
    words = _generate(library="Atomic_Sensor_Magnetic", description="magnetometer", package_words=["MAGNETIC", "magnetometer"])
    folded = [word.casefold() for word in words]
    assert len(folded) == len(set(folded))
    assert "Magnetic" in words
    assert "MAGNETIC" not in words


def test_the_mpn_is_added_only_when_it_is_not_part_of_the_symbol_name():
    assert "ABC123" not in _generate(mpn="ABC123", symbol_name="xx-abc123-yy")
    assert "ABC123" in _generate(mpn="ABC123", symbol_name="PART")
    assert _generate(mpn="", symbol_name="PART") == ["Transistor", "FET"]


def test_the_library_stem_words_drop_the_atomic_prefix():
    assert _generate(library="Atomic_Sensor_Motion")[:2] == ["Sensor", "Motion"]
    assert _generate(library="Atomic_Relay") == ["Relay"]


def test_runner_up_stems_add_their_words():
    words = _generate(related=["Diode", "Converter_DCDC"])
    assert words[-3:] == ["Diode", "Converter", "DCDC"]


def test_a_part_with_no_text_gets_the_stem_words_only():
    assert _generate() == ["Transistor", "FET"]


def test_generation_only_reads_the_manufacturer():
    # The Manufacturer field is the caller's; the words come back as a new list and nothing is rewritten (D-26)
    name = "Maxim Integrated"
    words = _generate(manufacturer=name)
    assert name == "Maxim Integrated"
    assert words[-3:] == ["Maxim", "ADI", "Analog"]


def test_vocabulary_tables_hold_single_words_and_no_junk():
    for _, word in (*FUNCTION_WORDS, *INTERFACE_WORDS, *CASED_INTERFACE_WORDS):
        assert word.split() == [word]
        assert "=" not in word
        assert word.casefold() not in JUNK_WORDS


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("", id="empty"),
        pytest.param("!!! ???", id="punctuation"),
        pytest.param("x" * 50_000, id="very-long"),
        pytest.param("é" * 40, id="combining-marks"),
        pytest.param("\\n\\n", id="backslash-n"),
        pytest.param("Ünï \u0000 ß", id="odd-characters"),
    ],
)
def test_generation_never_raises_on_odd_text(text):
    words = _generate(description=text, category=text, package_words=[text], manufacturer=text, mpn=text)
    for word in words:
        assert word
        assert not any(c.isspace() for c in word)


# -- the English word "can" is not the CAN bus (WR-02) -------------------------------------------------


def test_the_english_word_can_gives_no_can_keyword():
    words = _generate(description="You can use it; USB C receptacle")
    assert "USB" in words
    assert "USB-C" in words
    assert "CAN" not in words


def test_a_planned_install_writes_can_only_for_a_can_bus_part(atomic_custom, ul_package):
    _, candidate = ul_package
    english = build_plan(
        candidate,
        InstallOptions(library=ABSENT_LIBRARY, description="You can use it; USB C receptacle"),
        atomic_custom,
        ToolContext(),
    )
    words = english.part_text.keywords.split()
    assert "USB" in words
    assert "can" not in [word.casefold() for word in words]

    bus = build_plan(
        candidate,
        InstallOptions(library=ABSENT_LIBRARY, description="Isolated CAN transceiver"),
        atomic_custom,
        ToolContext(),
    )
    assert bus.part_text.keywords.split().count("CAN") == 1


@pytest.mark.parametrize(
    ("field", "text"),
    [
        ("description", "You can use it"),
        ("description", "Can be mounted on either side"),
        ("description", "This part can drive 2 A"),
        ("description", "cannot exceed 5 V"),
        ("description", "boundary scan chain"),
        ("category", "can"),
    ],
)
def test_ordinary_can_gives_no_can_keyword(field, text):
    assert "CAN" not in _generate(**{field: text})


@pytest.mark.parametrize(
    ("field", "text"),
    [
        ("description", "Isolated CAN transceiver"),
        ("description", "CAN-FD transceiver"),
        ("description", "High-speed CAN, 5 V"),
        ("description", "Interface (CAN)"),
        ("description", "can bus transceiver"),
        ("description", "Can Bus interface"),
        ("description", "CANbus node"),
        ("description", "canfd controller"),
        ("description", "Can Transceiver 3.3 V"),
        ("description", "CAN bus"),
        ("category", "Interface CAN"),
    ],
)
def test_can_bus_text_gives_the_can_keyword_once(field, text):
    assert _generate(**{field: text}).count("CAN") == 1


def test_all_caps_can_gives_the_can_keyword():
    # Accepted residual (owner decision 2026-10-28): the exact-case rule cannot tell all-caps prose from the bus
    assert _generate(description="YOU CAN USE IT").count("CAN") == 1


@pytest.mark.parametrize(
    ("text", "keywords"),
    [
        ("spi flash", ["SPI"]),
        ("uart bridge", ["UART"]),
        ("ble module", ["BLE"]),
        ("SPI and UART", ["SPI", "UART"]),
    ],
)
def test_spi_uart_and_ble_still_match_in_any_case(text, keywords):
    words = _generate(description=text)
    for keyword in keywords:
        assert keyword in words
