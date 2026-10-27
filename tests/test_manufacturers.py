"""Canonical manufacturer table: folding, lookup, canonical spelling, datasheet domains and uniqueness (FLD-02, D-07..D-10, D-23)."""

import dataclasses

import pytest

from kicad_lib_manager import manufacturers
from kicad_lib_manager.manufacturers import Manufacturer


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


# ── Datasheet domains (D-23, T-10-07) ────────────────────────────────────────


@pytest.mark.parametrize(
    ("domain", "name"),
    [
        ("ti.com", "Texas Instruments"),
        ("analog.com", "Analog Devices"),
        ("maximintegrated.com", "Maxim Integrated"),
        ("linear.com", "Linear Technology"),
        ("tdk.com", "TDK"),
        ("invensense.com", "InvenSense"),
        ("murata.com", "Murata"),
        ("gct.co", "Global Connector Technology"),
        ("memsic.com", "Memsic"),
        ("u-blox.com", "u-blox"),
        ("abracon.com", "Abracon"),
        ("recom-power.com", "RECOM"),
    ],
)
def test_by_host_names_the_company_that_owns_the_domain(domain, name):
    entry = manufacturers.by_host(domain)
    assert entry is not None
    assert entry.name == name


def test_by_host_never_maps_an_acquired_brand_to_its_owner():
    # Phase 9 D-08: Maxim Integrated stays Maxim Integrated, never Analog Devices
    assert manufacturers.by_host("maximintegrated.com").name == "Maxim Integrated"
    assert manufacturers.by_host("linear.com").name == "Linear Technology"


def test_by_host_ignores_case_and_one_trailing_dot():
    assert manufacturers.by_host("TI.COM").name == "Texas Instruments"
    assert manufacturers.by_host("ti.com.").name == "Texas Instruments"


@pytest.mark.parametrize("domain", ["example.com", "", "   ", ".", "digikey.com", "www.ti.com", "ti.com/x"])
def test_by_host_gives_none_for_an_unknown_or_empty_domain(domain):
    assert manufacturers.by_host(domain) is None


def test_host_index_rejects_two_entries_that_share_a_domain():
    clash = (Manufacturer("A", hosts=("a.com",)), Manufacturer("B", hosts=("A.com",)))
    with pytest.raises(ValueError):
        manufacturers._index_hosts(clash)


def test_every_host_is_lowercase_holds_a_dot_and_no_slash():
    for entry in manufacturers.MANUFACTURERS:
        for host in entry.hosts:
            assert host == host.casefold(), host
            assert "." in host, host
            assert "/" not in host, host


def test_the_v1_library_token_is_gone():
    assert [n for n in dir(manufacturers) if "token" in n.casefold()] == []
    assert "token" not in {f.name for f in dataclasses.fields(Manufacturer)}
    assert not hasattr(manufacturers.lookup("TI").entry, "token")


# ── Canonical spelling (D-23) ────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("TI", "Texas Instruments"),
        ("texas instruments", "Texas Instruments"),
        ("GCT", "Global Connector Technology"),
        ("U-BLOX", "u-blox"),
        ("Maxim", "Maxim Integrated"),
        ("Texas Instruments", "Texas Instruments"),
        ("Hirose", "Hirose"),
        ("  Hirose Electric ", "  Hirose Electric "),
        ("", ""),
    ],
)
def test_canonical_gives_the_table_name_or_the_value_unchanged(value, expected):
    assert manufacturers.canonical(value) == expected


def test_entry_names_are_non_empty_unique_and_carry_no_corporate_word():
    names = [entry.name for entry in manufacturers.MANUFACTURERS]
    assert all(names)
    assert len(set(names)) == len(names)
    for name in names:
        words = name.casefold().replace("-", " ").split()
        assert not set(words) & manufacturers.CORPORATE_WORDS, name
