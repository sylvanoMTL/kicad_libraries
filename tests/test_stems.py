"""The one name rule of the Atomic_ scheme: stems snapshot, installed union and the verdict (LIB-05, D-07..D-13)."""

import re

import pytest

from kicad_lib_manager import library_scanner
from kicad_lib_manager.importer import stems as stems_module
from kicad_lib_manager.importer.kicad_cli import stock_symbols_dir
from kicad_lib_manager.importer.naming import MAX_NAME_LEN
from kicad_lib_manager.importer.stems import (
    EXCLUDED_STEMS,
    KICAD10_STEMS,
    SHARED_FOOTPRINT_LIBRARY,
    allowed_stems,
    installed_stems,
    name_verdict,
)

EXAMPLE = "Atomic_Transistor_FET"
NOT_A_NAME = "is not a library name: after Atomic_ comes a KiCad library name, such as Atomic_Transistor_FET"
NOT_FOLLOWING = "does not follow the naming: use Atomic_ and a KiCad library name, such as Atomic_Transistor_FET"


def test_installed_folder_to_allowed_set_to_verdict(tmp_path):
    folder = tmp_path / "symbols"
    folder.mkdir()
    (folder / "Transistor_FET.kicad_sym").write_text("", encoding="utf-8")
    (folder / "Brand_New_Stem.kicad_sym").write_text("", encoding="utf-8")
    (folder / "Simulation_SPICE.sp").write_text("", encoding="utf-8")

    stems = allowed_stems(installed_stems(folder))

    assert "Transistor_FET" in stems
    assert "Brand_New_Stem" in stems
    assert "Simulation_SPICE" not in stems
    assert name_verdict("Atomic_Brand_New_Stem", stems).ok is True
    corrected = name_verdict("atomic_transistor_fet")
    assert corrected.ok is False
    assert corrected.name == "Atomic_Transistor_FET"
    assert corrected.note == "Spelling corrected to Atomic_Transistor_FET"


# -- verdict table -------------------------------------------------------------

REFUSALS = [
    pytest.param("", "Pick or type a library name", id="empty"),
    pytest.param("   ", "Pick or type a library name", id="blank"),
    pytest.param(
        "Transistor_FET",
        f"Transistor_FET is the name of a KiCad library; use {EXAMPLE}",
        id="bare-official-stem",
    ),
    pytest.param(
        "power", "power is a KiCad library that is not for parts; pick another library", id="bare-excluded-power"
    ),
    pytest.param(
        "Graphic", "Graphic is a KiCad library that is not for parts; pick another library", id="bare-excluded-graphic"
    ),
    pytest.param(
        "Atomic_power", "Atomic_power cannot be used: power is not a library for parts", id="excluded-power"
    ),
    pytest.param(
        "Atomic_Simulation_SPICE",
        "Atomic_Simulation_SPICE cannot be used: Simulation_SPICE is not a library for parts",
        id="excluded-spice",
    ),
    pytest.param(
        "Atomic_Connector_Generic",
        "Atomic_Connector_Generic cannot be used: Connector_Generic is not a library for parts",
        id="excluded-generic",
    ),
    pytest.param("Atomic_TI", f"Atomic_TI {NOT_A_NAME}", id="invented-manufacturer"),
    pytest.param("Atomic_Connector_GCT", f"Atomic_Connector_GCT {NOT_A_NAME}", id="invented-connector"),
    pytest.param("Atomic_MyStuff", f"Atomic_MyStuff {NOT_A_NAME}", id="invented-word"),
    pytest.param("Atomic_Simulation_SPICE.sp", f"Atomic_Simulation_SPICE.sp {NOT_A_NAME}", id="dotted"),
    pytest.param("IC_Battery_Charger_TI", f"IC_Battery_Charger_TI {NOT_FOLLOWING}", id="v1-ic"),
    pytest.param("Connector_USB_GCT", f"Connector_USB_GCT {NOT_FOLLOWING}", id="v1-connector"),
    pytest.param("PowerSupply_SubCategory_RECOM", f"PowerSupply_SubCategory_RECOM {NOT_FOLLOWING}", id="v1-recom"),
]


@pytest.mark.parametrize(("text", "reason"), REFUSALS)
def test_refusal_reason(text, reason):
    verdict = name_verdict(text)
    assert verdict.ok is False
    assert verdict.reason == reason
    assert verdict.note == ""


@pytest.mark.parametrize(
    "name",
    [
        "Atomic_MCU_Espressif",
        "Atomic_MCU_ST_STM32F4",
        "Atomic_Device",
        "Atomic_Auxiliary_Items",
        "Atomic_Jumper",
        "Atomic_Mechanical",
        "Atomic_Converter_DCDC_Isolated",
    ],
)
def test_allowed_names_pass(name):
    verdict = name_verdict(name)
    assert verdict.ok is True
    assert verdict.name == name
    assert verdict.reason == ""


def test_case_only_difference_is_corrected_with_official_spelling():
    verdict = name_verdict("ATOMIC_mcu_espressif")
    assert verdict.ok is False
    assert verdict.name == "Atomic_MCU_Espressif"
    assert verdict.note == "Spelling corrected to Atomic_MCU_Espressif"
    assert verdict.reason == "ATOMIC_mcu_espressif is spelled differently from the KiCad library name; use Atomic_MCU_Espressif"


def test_excluded_name_with_wrong_case_names_the_official_stem():
    verdict = name_verdict("atomic_POWER")
    assert verdict.ok is False
    assert verdict.reason == "atomic_POWER cannot be used: power is not a library for parts"


def test_reasons_and_notes_are_one_plain_line():
    samples = [text for text, _reason in (p.values for p in REFUSALS)] + ["atomic_transistor_fet"]
    for text in samples:
        verdict = name_verdict(text)
        for line in (verdict.reason, verdict.note):
            assert "\n" not in line and "\r" not in line
            assert "ki_" not in line.replace(text, "").casefold()


# -- snapshot integrity --------------------------------------------------------


def test_snapshot_has_223_unique_stems_under_casefold():
    assert len(KICAD10_STEMS) == 223
    assert len({stem.casefold() for stem in KICAD10_STEMS}) == 223


def test_excluded_stems_are_in_the_snapshot():
    assert len(EXCLUDED_STEMS) == 6
    assert EXCLUDED_STEMS <= KICAD10_STEMS


def test_default_allowed_set_has_217_stems_and_fits_the_name_limit():
    allowed = allowed_stems()
    assert len(allowed) == 217
    assert allowed == KICAD10_STEMS - EXCLUDED_STEMS
    assert max(len("Atomic_" + stem) for stem in allowed) <= MAX_NAME_LEN


def test_shared_footprint_library_name():
    assert SHARED_FOOTPRINT_LIBRARY == "Atomic_Footprints"


def test_prefix_comes_from_atomic_check():
    from kicad_lib_manager import atomic_check

    assert stems_module.ATOMIC_PREFIX is atomic_check.ATOMIC_PREFIX


# -- installed union -----------------------------------------------------------


def test_installed_case_spelling_replaces_the_snapshot_spelling():
    allowed = allowed_stems(["Sensor_motion"])
    assert "Sensor_motion" in allowed
    assert "Sensor_Motion" not in allowed
    assert len(allowed) == 217


def test_installed_folder_never_removes_a_snapshot_stem():
    allowed = allowed_stems(["Only_One"])
    assert "Only_One" in allowed
    assert KICAD10_STEMS - EXCLUDED_STEMS <= allowed


def test_installed_excluded_stem_stays_excluded():
    allowed = allowed_stems(["power", "POWER", "Graphic"])
    assert not {"power", "POWER", "Graphic"} & allowed


def test_installed_stems_lists_only_symbol_files(tmp_path):
    for name in ("A_One.kicad_sym", "B_Two.kicad_sym", "C_Three.sp", "notes.txt", "D.Four.kicad_sym"):
        (tmp_path / name).write_text("", encoding="utf-8")
    assert installed_stems(tmp_path) == frozenset({"A_One", "B_Two"})


def test_installed_stems_of_missing_or_absent_folder_is_empty(tmp_path):
    assert installed_stems(None) == frozenset()
    assert installed_stems(tmp_path / "no_such_folder") == frozenset()


def test_installed_stem_with_a_path_character_never_becomes_allowed():
    allowed = allowed_stems(["../Escape", "Has Space", "Dot.Name"])
    assert not any(re.search(r"[./ ]", stem) for stem in allowed)


def test_new_installed_stem_is_accepted_by_the_verdict():
    allowed = allowed_stems(["Brand_New_Stem"])
    assert name_verdict("Atomic_Brand_New_Stem", allowed).ok is True
    assert name_verdict("Atomic_Brand_New_Stem").ok is False


# -- live KiCad ----------------------------------------------------------------


def test_snapshot_matches_the_installed_kicad_10():
    fp_dir = library_scanner.find_kicad_footprint_dir()
    folder = stock_symbols_dir(fp_dir)
    if folder is None:
        pytest.skip("no KiCad install with a stock symbols folder")
    installed = installed_stems(folder)
    if "Converter_DCDC_Isolated" not in installed:
        pytest.skip("installed KiCad is not version 10")
    assert KICAD10_STEMS <= installed
