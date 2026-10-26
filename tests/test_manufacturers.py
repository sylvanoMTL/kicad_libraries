"""Canonical manufacturer table: folding, lookup, uniqueness and the derived importer token map (FLD-02, D-07..D-10)."""

import pytest

from kicad_lib_manager import manufacturers
from kicad_lib_manager.importer.suggest import MANUFACTURER_ALIASES, manufacturer_token
from kicad_lib_manager.manufacturers import Manufacturer

# The v1.0 literal mapping from importer.suggest, copied so the derived map is pinned against it (D-09)
V1_ALIASES = {
    "texasinstruments": "TI",
    "ti": "TI",
    "analogdevices": "ADI",
    "adi": "ADI",
    "maximintegrated": "ADI",
    "maxim": "ADI",
    "lineartechnology": "ADI",
    "linear": "ADI",
    "tdk": "TDK",
    "invensense": "TDK",
    "tdkinvensense": "TDK",
    "murata": "Murata",
    "muratamanufacturing": "Murata",
    "gct": "GCT",
    "globalconnectortechnology": "GCT",
    "memsic": "Memsic",
    "ublox": "uBlox",
    "abracon": "Abracon",
    "recom": "RECOM",
    "recompower": "RECOM",
}


def test_suggest_aliases_are_derived_from_the_table():
    assert MANUFACTURER_ALIASES == manufacturers.token_map()
    for key, token in V1_ALIASES.items():
        assert MANUFACTURER_ALIASES[key] == token


def test_manufacturer_token_reads_the_table():
    for value, token in (("Memsic Inc.", "Memsic"), ("U-BLOX", "uBlox"), ("RECOM Power", "RECOM")):
        choice = manufacturer_token(value)
        assert choice.token == token
        assert choice.source == "name_alias"


# ── Folding (FLD-02, D-10) ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("text", "folded"),
    [
        ("U-BLOX", "ublox"),
        ("uBlox", "ublox"),
        ("u-blox", "ublox"),
        ("Memsic Inc.", "memsic"),
        ("RECOM Power", "recompower"),
        ("Würth Elektronik GmbH", "wurthelektronik"),
        ("", ""),
        (" Inc. ", ""),
    ],
)
def test_fold_reduces_spellings_to_letters_and_digits(text, folded):
    assert manufacturers.fold(text) == folded


# ── Lookup (FLD-02, D-07, D-10) ──────────────────────────────────────────────


@pytest.mark.parametrize(
    ("spelling", "canonical"),
    [
        ("GCT", "Global Connector Technology"),
        ("Global Connector Technology", "Global Connector Technology"),
        ("Texas Instruments", "Texas Instruments"),
        ("TI", "Texas Instruments"),
        ("Memsic Inc.", "Memsic"),
        ("U-BLOX", "u-blox"),
        ("Abracon", "Abracon"),
        ("RECOM Power", "RECOM"),
    ],
)
def test_every_custom_spelling_resolves_to_its_canonical_entry(spelling, canonical):
    match = manufacturers.lookup(spelling)
    assert match is not None
    assert match.entry.name == canonical


def test_exact_is_true_only_for_the_identical_canonical_spelling():
    assert manufacturers.lookup("Global Connector Technology").exact is True
    # alias, case variant and suffix variant are all found but not exact
    assert manufacturers.lookup("GCT").exact is False
    assert manufacturers.lookup("texas instruments").exact is False
    assert manufacturers.lookup("Texas Instruments Inc.").exact is False


@pytest.mark.parametrize("value", ["Hirose", "", "   ", "Ltd."])
def test_unknown_and_empty_values_are_not_found(value):
    assert manufacturers.lookup(value) is None


# ── Acquired brands keep their own name (D-08) ───────────────────────────────


@pytest.mark.parametrize(
    ("spelling", "name", "owner"),
    [
        ("Maxim Integrated", "Maxim Integrated", "Analog Devices"),
        ("Linear Technology", "Linear Technology", "Analog Devices"),
        ("InvenSense", "InvenSense", "TDK"),
        ("TDK InvenSense", "InvenSense", "TDK"),
    ],
)
def test_acquired_brand_keeps_its_own_name_and_records_its_owner(spelling, name, owner):
    match = manufacturers.lookup(spelling)
    assert match is not None
    assert match.entry.name == name
    assert match.entry.owner == owner


def test_owner_itself_is_a_separate_entry():
    assert manufacturers.lookup("TDK").entry.name == "TDK"
    assert manufacturers.lookup("Analog Devices").entry.name == "Analog Devices"


# ── Uniqueness of folded keys (D-10, T-09-01) ────────────────────────────────


def test_index_rejects_two_entries_that_fold_to_one_key():
    clash = (Manufacturer("A Co", ("X",)), Manufacturer("B", ("x",)))
    with pytest.raises(ValueError):
        manufacturers._index(clash)


def test_shipped_table_builds_and_every_name_maps_to_itself():
    index = manufacturers._index(manufacturers.MANUFACTURERS)
    for entry in manufacturers.MANUFACTURERS:
        assert index[manufacturers.fold(entry.name)] is entry


def test_entry_names_are_non_empty_unique_and_carry_no_corporate_word():
    names = [entry.name for entry in manufacturers.MANUFACTURERS]
    assert all(names)
    assert len(set(names)) == len(names)
    for name in names:
        words = name.casefold().replace("-", " ").split()
        assert not set(words) & manufacturers.CORPORATE_WORDS, name
