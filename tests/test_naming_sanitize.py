"""Name sanitising for the importer: D-15 pipeline, D-16 case clashes, LIB-03 hostile and empty names."""

from pathlib import Path

import pytest

from kicad_lib_manager import kicad_files
from kicad_lib_manager.importer.naming import (
    MAX_NAME_LEN,
    PLACEHOLDER_NAME,
    case_clash,
    sanitize_filename,
    sanitize_name,
)
from kicad_lib_manager.models import Issue, Severity

REPO_ROOT = Path(__file__).resolve().parent.parent
BS = chr(92)

# Non-ASCII inputs are built with escapes so this file stays ASCII.
EXAMPLES = [
    ("CON", "CON_"),
    ("con", "con_"),
    ("NUL.foo", "NUL_.foo"),
    ("COM1", "COM1_"),
    ("COM¹", "COM1_"),
    ("LPT9", "LPT9_"),
    ("a/b", "a_b"),
    ("a:b", "a_b"),
    ("a" + BS + "b", "a_b"),
    ("../../x", "x"),
    ("µF cap", "uF_cap"),
    ("10Ω", "10Ohm"),
    ("10Ω", "10Ohm"),
    ("25°C", "25degC"),
    ("café", "cafe"),
    ("S3G-E3/57T", "S3G-E3_57T"),
    ("(x)", "x"),
    ("CONIN$", "CONIN"),
    ("x" * 80, "x" * 64),
]

# Names present in Custom/ today; none may change (success criterion 5).
EXISTING_NAMES = sorted(
    set(
        [
            # symbol libraries
            "Connector_FFC_GCT",
            "Connector_MicroSD_GCT",
            "Connector_USB_GCT",
            "IC_Battery_Charger_TI",
            "IC_Battery_Fuel_Gauge_ADI",
            "IC_Button_Controller_ADI",
            "IC_IMU_TDK",
            "IC_Magnetometer_Memsic",
            "IC_Wireless_BLE_uBlox",
            "Oscillator_TCXO_Abracon",
            # footprint libraries (the same without IC_IMU_TDK)
            "Connector_FFC_GCT",
            "Connector_MicroSD_GCT",
            "Connector_USB_GCT",
            "IC_Battery_Charger_TI",
            "IC_Battery_Fuel_Gauge_ADI",
            "IC_Button_Controller_ADI",
            "IC_Magnetometer_Memsic",
            "IC_Wireless_BLE_uBlox",
            "Oscillator_TCXO_Abracon",
            # footprint names
            "GCT_FFC2A32-06-T",
            "GCT_MEM2085-00-115-00-A_REV0.2",
            "GCT_USB4056-03-A_REVA2",
            "GCT_USB4730-GF-A_REVA",
            "GCT_USB4745-03-A_REVA",
            "IC_BQ25180YBGR",
            "BGA8N40P2X4_93X167X69N",
            "SON50P200X200X80-9N",
            "DFN-8_DDB",
            "TSOT-23_TS8",
            "PQFN50P300X300X100-16N",
            "XCVR_NORA-W106-00B",
            "ATX-14",
            "ATXK-H14",
            # symbol names
            "FFC2A32-06-T",
            "MEM2085-00-115-00-A_REV0.2",
            "USB4056-03-A_REVA2",
            "USB4730-GF-A_REVA",
            "USB4745-03-A_REVA",
            "BQ25180YBGR",
            "MAX17048G",
            "MAX17048X",
            "LTC2954",
            "LTC2954-1-DFN8",
            "LTC2954-1-TSOT-23",
            "LTC2954-2-DFN8",
            "LTC2954-2-TSOT-23",
            "ICM-42688-P",
            "MMC5983MA",
            "NORA-W106-00B",
            "NORA-W106-10B",
            "ATXK-H14",
        ]
    )
)


def _codes(result):
    return [i.code for i in result.issues]


def _by_code(result, code):
    return [i for i in result.issues if i.code == code]


@pytest.mark.parametrize(("raw", "expected"), EXAMPLES)
def test_sanitize_examples(raw, expected):
    result = sanitize_name(raw)
    assert result.sanitized == expected
    assert result.original == raw
    assert result.changed is (raw != expected)


def test_sanitize_issue_codes():
    con = sanitize_name("CON")
    reserved = _by_code(con, "naming.reserved")
    assert [i.severity for i in reserved] == [Severity.WARNING]
    assert [i.severity for i in _by_code(con, "naming.changed")] == [Severity.INFO]

    long = sanitize_name("x" * 80)
    assert [i.severity for i in _by_code(long, "naming.truncated")] == [Severity.WARNING]
    assert len(long.sanitized) == MAX_NAME_LEN

    for raw in ("", ".."):
        empty = sanitize_name(raw)
        assert empty.sanitized == PLACEHOLDER_NAME
        assert [i.severity for i in _by_code(empty, "naming.empty")] == [Severity.ERROR]

    clean = sanitize_name("IC_LDO_TI")
    assert clean.issues == ()
    assert clean.changed is False


def test_sanitize_changed_text_names_both():
    result = sanitize_name("a/b:c")
    (changed,) = _by_code(result, "naming.changed")
    assert repr("a/b:c") in changed.text
    assert repr("a_b_c") in changed.text


@pytest.mark.parametrize("raw", ["", "..", "___", "カタカナ"])
def test_sanitize_empty_inputs(raw):
    result = sanitize_name(raw)
    assert result.sanitized == "Unnamed"
    errors = [i for i in result.issues if i.severity is Severity.ERROR]
    assert [i.code for i in errors] == ["naming.empty"]


def test_sanitize_ascii_and_cap():
    for raw, _ in EXAMPLES:
        result = sanitize_name(raw)
        assert result.sanitized.isascii()
        assert len(result.sanitized) <= MAX_NAME_LEN
    assert sanitize_name("abcdefghijkl", max_len=10).sanitized == "abcdefghij"


def test_sanitize_reserved_after_cap():
    result = sanitize_name("CON." + "a" * 70)
    assert result.sanitized.startswith("CON_.")
    assert len(result.sanitized) == MAX_NAME_LEN
    assert "naming.reserved" in _codes(result)
    assert "naming.truncated" in _codes(result)


def test_sanitize_idempotent():
    for raw, _ in EXAMPLES:
        once = sanitize_name(raw)
        assert sanitize_name(once.sanitized).sanitized == once.sanitized


def test_sanitize_existing_names_unchanged():
    assert len(EXISTING_NAMES) >= 40
    for name in EXISTING_NAMES:
        result = sanitize_name(name)
        assert result.changed is False, name
        assert result.issues == (), name


def test_sanitize_live_custom_names_unchanged():
    custom = REPO_ROOT / "Custom"
    if not (custom / "Symbols").is_dir():
        pytest.skip("Custom submodule not checked out (git submodule update --init Custom)")
    names = []
    for sym in (custom / "Symbols").glob("*.kicad_sym"):
        names.append(sym.stem)
        loaded = kicad_files.load(sym)
        if not isinstance(loaded, Issue):
            names.extend(ref.name for ref in kicad_files.find_symbols(loaded.root))
    for pretty in (custom / "Footprints").glob("*.pretty"):
        names.append(pretty.stem)
        names.extend(mod.stem for mod in pretty.glob("*.kicad_mod"))
    assert names
    for name in names:
        result = sanitize_name(name)
        assert result.changed is False, name
        assert result.issues == (), name


# -- sanitize_filename (D-15, stem only) and case_clash (D-16) ----------------

FILENAME_EXAMPLES = [
    ("DLV0006A.stp", "DLV0006A.stp"),
    ("MEM2085-00-115-00-A_revA.STEP", "MEM2085-00-115-00-A_revA.STEP"),
    ("my part (v2).STEP", "my_part_v2.STEP"),
    ("CON.step", "CON_.step"),
    ("a/b.Kicad_Mod", "a_b.Kicad_Mod"),
    ("foo.txt", "foo.txt"),
    ("MEM2085-00-115-00-A_REV0.2", "MEM2085-00-115-00-A_REV0.2"),
    ("x.kicad_sym", "x.kicad_sym"),
    (".step", "Unnamed.step"),
    ("   .stp", "Unnamed.stp"),
]

EXISTING_MODEL_FILES = [
    "BGA8N40P2X4_93X167X69N.step",
    "BQ25180YBGR.step",
    "FFC2A32-06-T.step",
    "LTC2954CTS8.step",
    "LTC2954IDDB.step",
    "MAX17048G_T10.step",
    "MEM2085-00-115-00-A_revA.STEP",
    "MMC5983MA.step",
    "NORA-W106-00B.step",
    "NORA-W106-10B.step",
    "USB4056-03-A_REVA2.step",
    "USB4730-GF-A_REVA.step",
    "USB4745-03-A.stp",
]


@pytest.mark.parametrize(("raw", "expected"), FILENAME_EXAMPLES)
def test_filename_examples(raw, expected):
    result = sanitize_filename(raw)
    assert result.sanitized == expected
    assert result.original == raw


def test_filename_issue_codes():
    reserved = sanitize_filename("CON.step")
    assert "naming.reserved" in _codes(reserved)
    changed = _by_code(reserved, "naming.changed")
    assert len(changed) == 1
    assert repr("CON.step") in changed[0].text
    assert repr("CON_.step") in changed[0].text
    assert sanitize_filename("DLV0006A.stp").issues == ()
    assert sanitize_filename("foo.txt").issues == ()


@pytest.mark.parametrize("raw", [".step", "   .stp"])
def test_filename_empty_stem(raw):
    result = sanitize_filename(raw)
    assert result.sanitized.startswith(PLACEHOLDER_NAME + ".")
    errors = [i for i in result.issues if i.severity is Severity.ERROR]
    assert [i.code for i in errors] == ["naming.empty"]


def test_filename_original_kept():
    result = sanitize_filename("my part (v2).STEP")
    assert result.original == "my part (v2).STEP"
    assert result.sanitized == "my_part_v2.STEP"
    assert result.changed is True


def test_filename_whole_name_without_listed_extension():
    # os.path.splitext would split MEM2085-...-A_REV0.2 at ".2"; the whole name is sanitised instead
    result = sanitize_filename("a b.2")
    assert result.sanitized == "a_b.2"
    assert sanitize_filename("NUL.tar.gz").sanitized == "NUL_.tar.gz"


def test_filename_custom_extensions():
    result = sanitize_filename("a b.dat", extensions=(".dat",))
    assert result.sanitized == "a_b.dat"


def test_filename_existing_models_unchanged():
    for name in EXISTING_MODEL_FILES:
        result = sanitize_filename(name)
        assert result.changed is False, name
        assert result.issues == (), name
    models = REPO_ROOT / "Custom" / "3DModels"
    if models.is_dir():
        for path in models.iterdir():
            if path.is_file():
                result = sanitize_filename(path.name)
                assert result.changed is False, path.name
                assert result.issues == (), path.name


def test_filename_idempotent():
    for raw, _ in FILENAME_EXAMPLES:
        once = sanitize_filename(raw)
        assert sanitize_filename(once.sanitized).sanitized == once.sanitized


def test_case_clash():
    found = case_clash("ic_ldo_ti", ["IC_LDO_TI", "IC_LDO_ADI"])
    assert len(found) == 1
    assert found[0].code == "naming.case_clash"
    assert found[0].severity is Severity.WARNING
    assert "ic_ldo_ti" in found[0].text
    assert "IC_LDO_TI" in found[0].text
    assert case_clash("IC_LDO_TI", ["IC_LDO_TI"]) == []
    assert case_clash("IC_LDO_TI", ["Other"]) == []


def test_case_clash_casefold_and_each_existing_name():
    assert len(case_clash("Straße", ["STRASSE"])) == 1
    assert len(case_clash("a", ["A", "A"])) == 2
