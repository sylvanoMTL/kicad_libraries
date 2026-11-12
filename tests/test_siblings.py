"""Sibling index and family vote (LIB-04): the stock KiCad tree and the owner's Atomic_ libraries vote a part into a library."""

import os

import pytest

from customfixtures import atomic_lib, atomic_part
from kicad_lib_manager.importer.kicad_cli import stock_symbols_dir
from kicad_lib_manager.importer.siblings import (
    EMPTY_INDEX,
    SiblingEntry,
    SiblingIndex,
    SiblingPick,
    family_prefixes,
    own_index,
    pick,
    read_library,
    stock_index,
)
from kicad_lib_manager.library_scanner import find_kicad_footprint_dir
from stockfixtures import write_stock_sample


def test_csd_part_votes_into_transistor_fet_from_the_stock_tree(tmp_path):
    symbols_dir, _ = write_stock_sample(tmp_path)

    result = pick(stock_index(symbols_dir), "CSD85301Q2")

    # power's CSDPWR never votes; the Diode count stays as an alternative
    assert result == SiblingPick("Transistor_FET", "CSD", (("Transistor_FET", 3), ("Diode", 1)))


def test_csd_part_votes_into_transistor_fet_from_the_owners_atomic_libraries(tmp_path):
    symbols = tmp_path / "Custom" / "Symbols"
    symbols.mkdir(parents=True)
    (symbols / "Atomic_Transistor_FET.kicad_sym").write_bytes(atomic_lib((atomic_part("CSD99999"),)))
    # A v1 name and a hand-made Atomic_ library hold CSD parts too; neither may vote
    (symbols / "IC_PowerManagementMosfet_TI.kicad_sym").write_bytes(atomic_lib((atomic_part("CSD11111"),)))
    (symbols / "Atomic_MyStuff.kicad_sym").write_bytes(atomic_lib((atomic_part("CSD22222"),)))

    result = pick(own_index(symbols), "CSD85301Q2")

    assert result == SiblingPick("Transistor_FET", "CSD", (("Transistor_FET", 1),))


# -- family prefixes (D-02) ---------------------------------------------------


@pytest.mark.parametrize(
    ("part", "expected"),
    [
        ("CSD85301Q2", ["CSD85301", "CSD8", "CSD"]),
        ("USB4145-03-0170-C", ["USB4145", "USB4", "USB"]),
        ("ATXK-H14-D-32.768KHZ-E50-T3", ["ATXK"]),
        ("MAX4238", ["MAX4238", "MAX4", "MAX"]),
        ("csd85301q2", ["csd85301", "csd8", "csd"]),
        ("RS3-1212S/H3", []),
        ("R-78E5.0", []),
        ("LM7805", []),
        ("ab", []),
        ("", []),
        ("1234", []),
    ],
)
def test_family_prefixes_follow_the_digit_run_then_the_first_digit_then_the_letters(part, expected):
    assert family_prefixes(part) == expected


# -- the vote (D-03) ----------------------------------------------------------


def test_a_family_spread_over_libraries_is_reported_with_every_count_in_order(tmp_path):
    index = stock_index(write_stock_sample(tmp_path)[0])

    result = pick(index, "USB9999")

    assert result == SiblingPick(
        "Connector", "USB", (("Connector", 3), ("Interface_USB", 1), ("Power_Protection", 1))
    )


def test_the_first_prefix_step_with_any_sibling_decides(tmp_path):
    index = stock_index(write_stock_sample(tmp_path)[0])

    result = pick(index, "USB4145-03-0170-C")

    # USB4 already finds the three Connector parts, so the shorter USB step is never reached
    assert result == SiblingPick("Connector", "USB4", (("Connector", 3),))


def test_a_split_family_has_no_winner_and_keeps_the_counts(tmp_path):
    index = stock_index(write_stock_sample(tmp_path)[0])

    result = pick(index, "MAX4999")

    assert result == SiblingPick(
        None, "MAX4", (("Amplifier_Operational", 1), ("Analog_Switch", 1), ("Interface_UART", 1))
    )


def test_an_exact_half_is_not_a_majority():
    index = SiblingIndex((SiblingEntry("Diode", "ZZZ1", ""), SiblingEntry("Device", "ZZZ2", "")))

    assert pick(index, "ZZZ9").stem is None


def test_a_part_number_with_too_few_letters_gets_no_lookup(tmp_path):
    index = stock_index(write_stock_sample(tmp_path)[0])

    assert pick(index, "RS3-1212S/H3") == SiblingPick(None, "", ())
    assert pick(index, "R-78E5.0") == SiblingPick(None, "", ())


def test_prefix_matching_ignores_case_but_the_stem_keeps_its_spelling(tmp_path):
    index = stock_index(write_stock_sample(tmp_path)[0])

    assert pick(index, "csd85301q2").stem == "Transistor_FET"


# -- reading library bytes ----------------------------------------------------


def test_unit_sub_symbols_are_not_entries():
    data = atomic_lib((atomic_part("CSD16301Q2", replace={"Footprint": "Package_SON:Texas_DQK"}),))
    assert b'"CSD16301Q2_1_1"' in data

    assert read_library(data) == [("CSD16301Q2", "Package_SON:Texas_DQK")]


def test_a_symbol_right_after_a_one_line_header_is_read():
    data = (
        b"(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor) "
        b'(symbol "AAA111" (property "Footprint" "Lib:FP" (at 0 0 0))))'
    )

    assert read_library(data) == [("AAA111", "Lib:FP")]


def test_two_space_indent_and_a_missing_footprint_field_are_read():
    data = (
        b"(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\r\n"
        b'  (symbol "AAA111" (in_bom yes)\r\n    (property "Reference" "U" (id 0) (at 0 0 0))\r\n  )\r\n'
        b'  (symbol "BBB222" (in_bom yes)\r\n    (property "Footprint" "L:F" (id 2) (at 0 0 0))\r\n  )\r\n)\r\n'
    )

    assert read_library(data) == [("AAA111", ""), ("BBB222", "L:F")]


# -- the stock index: exclusions, cache, progress -----------------------------


def test_stock_index_skips_libraries_that_hold_no_parts(tmp_path):
    index = stock_index(write_stock_sample(tmp_path)[0])

    assert "power" not in {entry.library for entry in index.entries}
    assert not index.matches("CSDPWR")


def test_stock_index_carries_each_symbols_footprint_field(tmp_path):
    index = stock_index(write_stock_sample(tmp_path)[0])

    assert [(e.name, e.footprint) for e in index.matches("CSD16301")] == [("CSD16301Q2", "Package_SON:Texas_DQK")]


def test_stock_index_of_no_folder_or_a_missing_folder_is_empty(tmp_path):
    assert stock_index(None) is EMPTY_INDEX
    assert stock_index(tmp_path / "missing") is EMPTY_INDEX


def test_stock_index_is_cached_while_the_folder_is_unchanged(tmp_path):
    symbols_dir = write_stock_sample(tmp_path)[0]

    first = stock_index(symbols_dir)

    assert stock_index(symbols_dir) is first


def test_stock_index_rebuilds_when_a_file_changes(tmp_path):
    symbols_dir = write_stock_sample(tmp_path)[0]
    first = stock_index(symbols_dir)
    target = symbols_dir / "Diode.kicad_sym"
    stat = target.stat()

    os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))

    assert stock_index(symbols_dir) is not first


def test_stock_index_rebuilds_when_a_file_is_added(tmp_path):
    symbols_dir = write_stock_sample(tmp_path)[0]
    first = stock_index(symbols_dir)

    (symbols_dir / "Sensor_Motion.kicad_sym").write_bytes(atomic_lib((atomic_part("ICM-42688-P"),)))

    second = stock_index(symbols_dir)
    assert second is not first
    assert second.matches("ICM-4")


def test_stock_index_reports_progress_once_per_file(tmp_path):
    symbols_dir = write_stock_sample(tmp_path)[0]
    calls = []

    stock_index(symbols_dir, lambda message, current, total: calls.append((current, total)))

    count = len(list(symbols_dir.glob("*.kicad_sym")))
    assert calls == [(n, count) for n in range(1, count + 1)]


# -- the live KiCad 10 counts (RESEARCH, measured on 10.0.7) --------------------

_LIVE_SYMBOLS = stock_symbols_dir(find_kicad_footprint_dir())
_LIVE_IS_KICAD_10 = _LIVE_SYMBOLS is not None and (_LIVE_SYMBOLS / "Converter_DCDC_Isolated.kicad_sym").is_file()


@pytest.mark.skipif(_LIVE_SYMBOLS is None, reason="no KiCad install with a stock symbols folder")
@pytest.mark.skipif(not _LIVE_IS_KICAD_10, reason="installed KiCad is not version 10")
def test_live_kicad_10_votes_csd_into_transistor_fet_and_usb_into_connector():
    index = stock_index(_LIVE_SYMBOLS)

    csd = pick(index, "CSD85301Q2")
    usb = pick(index, "USB4145-03-0170-C")

    assert (csd.stem, csd.prefix) == ("Transistor_FET", "CSD")
    assert csd.counts[:2] == (("Transistor_FET", 75), ("Diode", 2))
    assert usb.stem == "Connector"
