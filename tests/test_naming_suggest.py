"""Library-name suggestion: fresh Custom/ listing, manufacturer chain, vocabulary, ranking (D-01..D-04, LIB-01)."""

from pathlib import Path

import pytest
from zipfixtures import (
    CURRENT_CUSTOM_FOOTPRINT_LIBS,
    CURRENT_CUSTOM_SYMBOL_LIBS,
    REPO_ROOT,
    UL_ZIP,
    symbol_lib,
    write_custom_layout,
)

from kicad_lib_manager.importer import suggest as suggest_mod
from kicad_lib_manager.importer.candidate import ExistingLibrary, PartMeta
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.layout import (
    RepoLayout,
    list_existing_libraries,
    list_footprint_libs,
    list_model_files,
    list_symbol_libs,
)
from kicad_lib_manager.importer.naming import sanitize_name
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.suggest import (
    TokenChoice,
    is_aggregator_host,
    manufacturer_choice,
    manufacturer_token,
    placeholder_tokens,
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


# -- Task 2: SubCategory vocabulary, ranking, sanitise pass, D-04 contract ---------------------

UL_ALTERNATIVES = [
    "IC_Battery_Charger_TI",
    "IC_Battery_Fuel_Gauge_ADI",
    "IC_Button_Controller_ADI",
    "IC_IMU_TDK",
    "IC_Magnetometer_Memsic",
]
CHARGER_META = PartMeta(
    "X",
    reference="U",
    description="Single-cell Li-Ion battery charger with power path",
    datasheet="https://www.ti.com/x",
)


def _ul_meta() -> PartMeta:
    with open_package(UL_ZIP, REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        return candidate.symbols[0].meta


def _suggest(meta, existing=()):
    """Suggest and check that the produced name is already sanitised (every suggestion in this file)."""
    suggestion = suggest_library(meta, existing)
    assert sanitize_name(suggestion.name).changed is False
    return suggestion


def _libs(*names):
    return [ExistingLibrary(name, True, True) for name in names]


def test_suggest_ul_sample_with_layout(tmp_path):
    suggestion = _suggest(_ul_meta(), _existing(tmp_path))
    assert suggestion.name == "IC_SubCategory_TI"
    assert suggestion.confidence == "low"
    assert suggestion.placeholders == ("SubCategory",)
    assert suggestion.matches_existing is False
    assert [a.name for a in suggestion.alternatives] == UL_ALTERNATIVES
    first = suggestion.alternatives[0]
    assert first.score == 5
    assert first.shared_tokens == ("IC", "TI")
    assert [a.score for a in suggestion.alternatives[1:]] == [2, 2, 2, 2]
    assert first.has_symbols and first.has_footprints
    assert suggestion.alternatives[3].name == "IC_IMU_TDK"
    assert suggestion.alternatives[3].has_footprints is False
    assert (Severity.WARNING, "naming.placeholder") in _codes(suggestion)


def test_suggest_vocab_full_match(tmp_path):
    suggestion = _suggest(CHARGER_META, _existing(tmp_path))
    assert suggestion.name == "IC_Battery_Charger_TI"
    assert suggestion.confidence == "high"
    assert suggestion.placeholders == ()
    assert suggestion.matches_existing is True
    assert suggestion.subcategory == TokenChoice("Battery_Charger", "vocab", True)
    codes = {code for _, code in _codes(suggestion)}
    assert "naming.placeholder" not in codes
    assert "naming.low_confidence" not in codes
    # The matched library is also the first alternative, with its shared tokens in name order
    top = suggestion.alternatives[0]
    assert (top.name, top.score) == ("IC_Battery_Charger_TI", 7)
    assert top.shared_tokens == ("IC", "Battery", "Charger", "TI")


def test_suggest_vocab_whole_tokens_only(tmp_path):
    existing = _existing(tmp_path)
    part_number = PartMeta("X", reference="J", value="USB4056-03-A", datasheet="https://www.gct.co/x")
    assert _suggest(part_number, existing).name == "Connector_SubCategory_GCT"
    described = PartMeta(
        "X",
        reference="J",
        value="USB4056-03-A",
        description="USB Type-C receptacle",
        datasheet="https://www.gct.co/x",
    )
    assert _suggest(described, existing).name == "Connector_USB_GCT"


def test_suggest_vocab_prefers_more_tokens(tmp_path):
    meta = PartMeta("X", reference="U", description="battery fuel gauge and charger")
    suggestion = _suggest(meta, _existing(tmp_path))
    assert suggestion.subcategory == TokenChoice("Battery_Fuel_Gauge", "vocab", True)


def test_suggest_vocab_literal_newline_escapes(tmp_path):
    # A literal backslash followed by n, as stored in the existing Custom/ descriptions
    meta = PartMeta("X", reference="U", description="Fuel\\nGauge   for battery")
    suggestion = _suggest(meta, _existing(tmp_path))
    assert suggestion.subcategory == TokenChoice("Battery_Fuel_Gauge", "vocab", True)


def test_suggest_unknown_reference_takes_type_from_vocab(tmp_path):
    meta = PartMeta("X", reference="", description="3-axis magnetometer", datasheet="https://www.memsic.com/x")
    suggestion = _suggest(meta, _existing(tmp_path))
    assert suggestion.name == "IC_Magnetometer_Memsic"
    assert suggestion.type == TokenChoice("IC", "vocab", False)
    assert suggestion.confidence == "low"
    assert suggestion.matches_existing is True
    assert (Severity.WARNING, "naming.low_confidence") in _codes(suggestion)


def test_suggest_known_reference_limits_vocab_to_its_type(tmp_path):
    # "Magnetometer" is an IC library; a connector part never borrows it
    meta = PartMeta("X", reference="J", description="3-axis magnetometer")
    suggestion = _suggest(meta, _existing(tmp_path))
    assert suggestion.name == "Connector_SubCategory_Manufacturer"


def test_suggest_all_placeholders():
    suggestion = _suggest(PartMeta(symbol_name="X"), ())
    assert suggestion.name == "Type_SubCategory_Manufacturer"
    assert suggestion.placeholders == ("Type", "SubCategory", "Manufacturer")
    assert suggestion.confidence == "low"
    assert suggestion.alternatives == ()
    assert suggestion.matches_existing is False


def test_suggest_guess_warns_low_confidence():
    meta = PartMeta("X", reference="U", manufacturer="Acme Widgets")
    suggestion = _suggest(meta, ())
    assert suggestion.name == "IC_SubCategory_Acme"
    assert suggestion.confidence == "low"
    warning = next(i for i in suggestion.issues if i.code == "naming.low_confidence")
    assert warning.severity is Severity.WARNING
    assert "Acme (property)" in warning.text
    assert "SubCategory (placeholder)" in warning.text


def test_suggest_issue_order():
    meta = PartMeta("X", reference="U", datasheet="https://www.snapeda.com/x")
    codes = [i.code for i in _suggest(meta, ()).issues]
    assert codes == ["naming.aggregator_host", "naming.low_confidence", "naming.placeholder"]


def test_suggest_ranking_cap_and_determinism():
    names = [
        "IC_Alpha_TI",
        "IC_bravo_TI",
        "IC_Charlie_TI",
        "IC_delta_TI",
        "IC_Echo_TI",
        "IC_foxtrot_TI",
        "IC_Golf_TI",
        "IC_hotel_TI",
    ]
    meta = PartMeta("X", reference="U", datasheet="https://www.ti.com/x")
    first = _suggest(meta, _libs(*reversed(names)))
    second = _suggest(meta, _libs(*names))
    assert [a.name for a in first.alternatives] == [
        "IC_Alpha_TI",
        "IC_bravo_TI",
        "IC_Charlie_TI",
        "IC_delta_TI",
        "IC_Echo_TI",
    ]
    assert len(first.alternatives) == 5
    assert all(a.score == 5 for a in first.alternatives)
    assert first == second
    assert suggest_library(meta, _libs(*names)) == second
    assert suggest_mod.MAX_ALTERNATIVES == 5


def test_suggest_ranking_scores_follow_the_formula():
    meta = PartMeta("X", reference="U", description="fuel gauge", datasheet="https://www.ti.com/x")
    existing = _libs("IC_Fuel_Gauge_ADI", "IC_Other_TI", "Connector_Fuel_TI", "Connector_USB_GCT")
    ranked = {a.name: a.score for a in _suggest(meta, existing).alternatives}
    # type 2 + shared 2 / mfr 3 + type 2 / mfr 3 + shared 1; Connector_USB_GCT scores 0 and is dropped
    assert ranked == {"IC_Fuel_Gauge_ADI": 4, "IC_Other_TI": 5, "Connector_Fuel_TI": 4}


def test_suggest_case_clash_and_exact_match():
    suggestion = _suggest(CHARGER_META, _libs("ic_battery_charger_ti"))
    assert suggestion.name == "IC_battery_charger_TI"
    assert suggestion.subcategory == TokenChoice("battery_charger", "vocab", True)
    assert suggestion.type == TokenChoice("IC", "reference", True)
    assert suggestion.manufacturer == TokenChoice("TI", "host_table", True)
    assert suggestion.matches_existing is False
    clash = [i for i in suggestion.issues if i.code == "naming.case_clash"]
    assert len(clash) == 1
    assert clash[0].severity is Severity.WARNING
    assert "IC_battery_charger_TI" in clash[0].text
    assert "ic_battery_charger_ti" in clash[0].text


def test_suggest_exact_match_with_guessed_manufacturer():
    meta = PartMeta("X", reference="U", manufacturer="Würth Elektronik", description="battery charger")
    suggestion = _suggest(meta, _libs("IC_Battery_Charger_Wurth"))
    assert suggestion.name == "IC_Battery_Charger_Wurth"
    assert suggestion.matches_existing is True
    assert suggestion.confidence == "low"


def test_suggest_sanitize_issues_are_reported():
    # An odd vocabulary Type is sanitised and the change is listed among the issues
    meta = PartMeta("X", reference="", description="3-axis magnetometer", datasheet="https://www.memsic.com/x")
    suggestion = _suggest(meta, _libs("I C_Magnetometer_Memsic"))
    assert suggestion.name == "I_C_Magnetometer_Memsic"
    assert any(i.code == "naming.changed" and i.severity is Severity.INFO for i in suggestion.issues)


def test_suggest_never_raises_on_odd_input():
    odd = PartMeta(
        "X",
        reference="#PWR",
        value="~",
        datasheet="http://[bad",
        description="\\n\\n   µΩ",
        keywords="\x00",
        manufacturer="  ",
    )
    assert _suggest(odd, ()).name == "Type_SubCategory_Manufacturer"


def test_placeholder_contract_on_edited_name(tmp_path):
    # D-04: Phases 4 and 5 call these on a plain edited string, with no suggestion object
    assert placeholder_tokens("Transistor_MOSFET_TI") == []
    assert sanitize_name("Transistor_MOSFET_TI").changed is False
    suggestion = _suggest(_ul_meta(), _existing(tmp_path))
    assert placeholder_tokens(suggestion.name) == ["SubCategory"]
    assert placeholder_tokens("Type_SubCategory_Manufacturer") == ["Type", "SubCategory", "Manufacturer"]


def test_suggest_live_custom():
    if not (REPO_ROOT / "Custom" / "Symbols").is_dir():
        pytest.skip("Custom submodule not checked out (git submodule update --init Custom)")
    suggestion = _suggest(_ul_meta(), list_existing_libraries(RepoLayout.for_repo(REPO_ROOT)))
    assert suggestion.name == "IC_SubCategory_TI"
    assert suggestion.alternatives[0].name == "IC_Battery_Charger_TI"
