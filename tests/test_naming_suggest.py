"""Library-name suggestion: fresh Custom/ listing, manufacturer chain, vocabulary, ranking (D-01..D-04, LIB-01)."""

from pathlib import Path

import pytest
from zipfixtures import (
    CURRENT_CUSTOM_FOOTPRINT_LIBS,
    CURRENT_CUSTOM_SYMBOL_LIBS,
    symbol_lib,
    write_custom_layout,
)

from kicad_lib_manager.importer.candidate import ExistingLibrary, PartMeta
from kicad_lib_manager.importer.layout import (
    RepoLayout,
    list_existing_libraries,
    list_footprint_libs,
    list_model_files,
    list_symbol_libs,
)
from kicad_lib_manager.importer.suggest import (
    TokenChoice,
    is_aggregator_host,
    manufacturer_choice,
    manufacturer_token,
    suggest_library,
)
from kicad_lib_manager.models import Severity

PLACEHOLDER_MFR = TokenChoice("Manufacturer", "placeholder", False)


def _current_layout(tmp_path: Path) -> RepoLayout:
    root = write_custom_layout(tmp_path, CURRENT_CUSTOM_SYMBOL_LIBS, CURRENT_CUSTOM_FOOTPRINT_LIBS)
    return RepoLayout.for_repo(root)


def _existing(tmp_path: Path) -> list[ExistingLibrary]:
    return list_existing_libraries(_current_layout(tmp_path))


def _snapshot(root: Path) -> list[tuple[str, bool]]:
    return sorted((p.relative_to(root).as_posix(), p.is_dir()) for p in root.rglob("*"))


def _codes(suggestion) -> set[tuple[Severity, str]]:
    return {(i.severity, i.code) for i in suggestion.issues}


# -- Task 1: fresh Custom/ listing (D-03) ------------------------------------------------


def test_layout_lists_fresh(tmp_path):
    layout = _current_layout(tmp_path)
    libs = list_existing_libraries(layout)
    expected = sorted(CURRENT_CUSTOM_SYMBOL_LIBS, key=lambda n: (n.casefold(), n))
    assert [lib.name for lib in libs] == expected
    assert len(libs) == 10
    by_name = {lib.name: lib for lib in libs}
    assert by_name["IC_IMU_TDK"] == ExistingLibrary("IC_IMU_TDK", True, False)
    assert all(
        lib.has_symbols and lib.has_footprints for name, lib in by_name.items() if name != "IC_IMU_TDK"
    )
    # Stray files are not libraries
    (layout.symbols_dir / "readme.txt").write_text("x", encoding="utf-8")
    (layout.footprints_dir / "x.kicad_mod").write_text("x", encoding="utf-8")
    assert len(list_existing_libraries(layout)) == 10
    # A library added between two calls shows up on the second (never cached)
    (layout.symbols_dir / "IC_LDO_TI.kicad_sym").write_bytes(symbol_lib(("IC_LDO_TI",)))
    after = list_existing_libraries(layout)
    assert len(after) == 11
    assert ExistingLibrary("IC_LDO_TI", True, False) in after


def test_layout_missing_custom_and_read_only(tmp_path):
    missing = RepoLayout.for_repo(tmp_path / "none")
    assert list_symbol_libs(missing) == []
    assert list_footprint_libs(missing) == []
    assert list_model_files(missing) == []
    assert list_existing_libraries(missing) == []
    assert not (tmp_path / "none").exists()
    layout = _current_layout(tmp_path / "repo")
    before = _snapshot(tmp_path)
    list_symbol_libs(layout)
    list_footprint_libs(layout)
    list_model_files(layout)
    list_existing_libraries(layout)
    assert _snapshot(tmp_path) == before


def test_layout_folders_follow_the_custom_convention(tmp_path):
    layout = RepoLayout.for_repo(tmp_path)
    assert layout.repo_root == tmp_path
    assert layout.custom_dir == tmp_path / "Custom"
    assert layout.symbols_dir == tmp_path / "Custom" / "Symbols"
    assert layout.footprints_dir == tmp_path / "Custom" / "Footprints"
    assert layout.models_dir == tmp_path / "Custom" / "3DModels"


def test_layout_model_files(tmp_path):
    layout = _current_layout(tmp_path)
    (layout.models_dir / "a.step").write_bytes(b"x")
    (layout.models_dir / "sub").mkdir()
    (layout.models_dir / "sub" / "x.step").write_bytes(b"x")
    assert list_model_files(layout) == ["a.step", "sub/x.step"]


# -- Task 1: manufacturer chain (D-02) ----------------------------------------------------


@pytest.mark.parametrize(
    ("value", "token"),
    [
        ("Texas Instruments", "TI"),
        ("TEXAS INSTRUMENTS", "TI"),
        ("texas instruments", "TI"),
        ("Global Connector Technology", "GCT"),
        ("GCT", "GCT"),
        ("Memsic Inc.", "Memsic"),
        ("U-BLOX", "uBlox"),
        ("Analog Devices", "ADI"),
        ("Murata Manufacturing Co., Ltd.", "Murata"),
    ],
)
def test_manufacturer_token_aliases(value, token):
    assert manufacturer_token(value) == TokenChoice(token, "name_alias", True)


def test_manufacturer_token_unmapped_and_empty():
    assert manufacturer_token("Acme Widgets") == TokenChoice("Acme", "property", False)
    assert manufacturer_token("W\u00fcrth Elektronik") == TokenChoice("Wurth", "property", False)
    assert manufacturer_token("") == PLACEHOLDER_MFR
    assert manufacturer_token("Inc.") == PLACEHOLDER_MFR


def test_manufacturer_choice_order():
    ti_sheet = "https://www.ti.com/lit/ds/x.pdf"
    assert manufacturer_choice(PartMeta("X", manufacturer="Analog Devices", datasheet=ti_sheet)) == TokenChoice(
        "ADI", "name_alias", True
    )
    # An unmapped property never beats a mapped host (mapped tokens are tried first)
    assert manufacturer_choice(PartMeta("X", manufacturer="Texas Instr.", datasheet=ti_sheet)) == TokenChoice(
        "TI", "host_table", True
    )
    assert manufacturer_choice(
        PartMeta("X", manufacturer="Acme Widgets", datasheet="https://unknown.example/x.pdf")
    ) == TokenChoice("Acme", "property", False)
    assert manufacturer_choice(
        PartMeta("X", datasheet="https://www.example-parts.com/ds.pdf")
    ) == TokenChoice("Exampleparts", "host_guess", False)


@pytest.mark.parametrize(
    ("datasheet", "expected"),
    [
        ("https://www.ti.com/lit/x", TokenChoice("TI", "host_table", True)),
        ("https://e2e.ti.com/x", TokenChoice("TI", "host_table", True)),
        ("https://E2E.TI.COM:443/a", TokenChoice("TI", "host_table", True)),
        ("https://invensense.tdk.com/x.pdf", TokenChoice("TDK", "host_table", True)),
        ("http://www.gct.co/x", TokenChoice("GCT", "host_table", True)),
        ("https://www.murata.co.jp/x", TokenChoice("Murata", "host_guess", False)),
        ("www.ti.com/lit/x", TokenChoice("TI", "host_table", True)),
        ("", PLACEHOLDER_MFR),
        ("~", PLACEHOLDER_MFR),
        ("file:///C:/x.pdf", PLACEHOLDER_MFR),
        ("http://[bad", PLACEHOLDER_MFR),
    ],
)
def test_manufacturer_hosts(datasheet, expected):
    assert manufacturer_choice(PartMeta("X", datasheet=datasheet)) == expected


def test_manufacturer_aggregator_ignored():
    assert is_aggregator_host("www.snapeda.com")
    assert is_aggregator_host("www.mouser.co.uk")
    assert not is_aggregator_host("www.ti.com")
    meta = PartMeta("X", reference="U", datasheet="https://www.snapeda.com/parts/x/datasheet")
    assert manufacturer_choice(meta) == PLACEHOLDER_MFR
    suggestion = suggest_library(meta)
    assert suggestion.manufacturer == PLACEHOLDER_MFR
    assert (Severity.INFO, "naming.aggregator_host") in _codes(suggestion)
    plain = suggest_library(PartMeta("X", reference="U", datasheet="https://www.ti.com/x"))
    assert (Severity.INFO, "naming.aggregator_host") not in _codes(plain)
