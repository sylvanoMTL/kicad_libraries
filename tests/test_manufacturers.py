"""Canonical manufacturer table: folding, lookup, uniqueness and the derived importer token map (FLD-02, D-07..D-10)."""

from kicad_lib_manager import manufacturers
from kicad_lib_manager.importer.suggest import MANUFACTURER_ALIASES, manufacturer_token

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
