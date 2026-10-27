"""The Atomic_ library suggestion (LIB-04): own siblings, KiCad's siblings, the category map, else ask.

Synthetic stock trees come from stockfixtures, so no test needs the real KiCad install except the
single real-sample test in test_real_vendor_samples.
"""

import html
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from customfixtures import atomic_lib, atomic_part
from kicad_lib_manager import settings
from kicad_lib_manager.importer.candidate import PartMeta
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.plan import ToolContext
from kicad_lib_manager.importer.siblings import own_index, stock_index
from kicad_lib_manager.importer.suggest import (
    Alternative,
    LibrarySuggestion,
    existing_libraries,
    suggest_library,
    suggestion_text,
)
from kicad_lib_manager.widgets.import_dialog import ImportCore, ImportDialog
from stockfixtures import write_stock_sample

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qsettings"))
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


def test_csd_part_is_suggested_from_the_stock_family(tmp_path):
    symbols_dir, _ = write_stock_sample(tmp_path)

    suggestion = suggest_library(PartMeta("CSD85301Q2"), stock=stock_index(symbols_dir))

    assert suggestion.name == "Atomic_Transistor_FET"
    assert suggestion.source == "stock"
    assert suggestion.reason == "Suggested from 3 similar parts in KiCad's Transistor_FET"
    assert suggestion.alternatives == (Alternative("Atomic_Diode", 1),)
    assert suggestion.related_stems == ("Transistor_FET", "Diode")
    assert suggestion.issues == ()
    assert suggestion_text(suggestion) == (
        "Suggested from 3 similar parts in KiCad's Transistor_FET. Other matches: Diode (1)."
    )


@pytest.mark.skipif(not UL_ZIP.is_file(), reason="the licence-restricted Ultra Librarian sample is not present")
def test_opening_csd_in_the_dialog_prefills_the_family_library_with_its_reason(qtbot, tmp_path):
    symbols_dir, _ = write_stock_sample(tmp_path / "stock")
    layout = RepoLayout.for_repo(tmp_path / "repo")
    core = replace(
        ImportCore(),
        detect_tools=lambda kicad_fp_dir: ToolContext(kicad_symbols_dir=symbols_dir),
        kicad_running=lambda: [],
    )
    dialog = ImportDialog(layout.repo_root, layout, core=core, backup_root=tmp_path / "backups")
    qtbot.addWidget(dialog)

    dialog.open_path(UL_ZIP)
    qtbot.waitUntil(lambda: dialog._suggestion is not None, timeout=30000)

    assert dialog._library_combo.currentText() == "Atomic_Transistor_FET"
    assert dialog._suggestion.source == "stock"
    tip = dialog._library_combo.toolTip()
    assert tip == "<p>" + html.escape(suggestion_text(dialog._suggestion)) + "</p>"
    assert html.escape("similar parts in KiCad's Transistor_FET") in tip
    dialog.reject()


# -- the order of the lookups --------------------------------------------------


def _owner_symbols(tmp_path, library: str, *names: str) -> Path:
    symbols = tmp_path / "Custom" / "Symbols"
    symbols.mkdir(parents=True, exist_ok=True)
    (symbols / f"{library}.kicad_sym").write_bytes(atomic_lib(tuple(atomic_part(name) for name in names)))
    return symbols


def test_own_library_beats_the_stock_family(tmp_path):
    symbols_dir, _ = write_stock_sample(tmp_path / "stock")
    own = own_index(_owner_symbols(tmp_path, "Atomic_Power_Management", "CSD99999"))

    suggestion = suggest_library(PartMeta("CSD85301Q2"), own=own, stock=stock_index(symbols_dir))

    assert suggestion.name == "Atomic_Power_Management"
    assert suggestion.source == "own"
    assert suggestion.reason == "Suggested from 1 similar parts in your Atomic_Power_Management"


def test_usb_connector_part_is_suggested_from_stock(tmp_path):
    symbols_dir, _ = write_stock_sample(tmp_path)

    suggestion = suggest_library(PartMeta("USB4145-03-0170-C"), stock=stock_index(symbols_dir))

    assert suggestion.name == "Atomic_Connector"
    assert suggestion.source == "stock"


def test_split_family_falls_to_ask_with_the_counts(tmp_path):
    symbols_dir, _ = write_stock_sample(tmp_path)
    meta = PartMeta("MAX4999", description="op amp")

    suggestion = suggest_library(meta, stock=stock_index(symbols_dir))

    assert suggestion.name == ""
    assert suggestion.source == "ask"
    assert suggestion.alternatives == (
        Alternative("Atomic_Amplifier_Operational", 1),
        Alternative("Atomic_Analog_Switch", 1),
        Alternative("Atomic_Interface_UART", 1),
    )


def test_vendor_category_places_a_part_no_sibling_decides():
    meta = PartMeta(
        "RS3-1212S/H3",
        category="Power Supply",
        description="Isolated DC/DC Converters",
    )

    suggestion = suggest_library(meta, stock=None)

    assert suggestion.name == "Atomic_Converter_DCDC_Isolated"
    assert suggestion.source == "category"
    assert suggestion.reason == "Suggested from the vendor category Power Supply and the description"
    assert suggestion_text(suggestion) == (
        "Suggested from the vendor category Power Supply and the description."
    )


def test_a_part_nothing_places_is_left_for_the_owner():
    suggestion = suggest_library(PartMeta("ATXK-H14-D-32.768KHZ-E50-T3", reference="X"), stock=None)

    assert suggestion.name == ""
    assert suggestion.source == "ask"
    assert suggestion.reason == ""
    assert suggestion_text(suggestion) == ""


def test_without_kicad_the_stock_lookup_is_skipped_with_one_info_line():
    suggestion = suggest_library(PartMeta("CSD85301Q2"), stock=None)

    assert [(i.severity.name, i.code, i.text) for i in suggestion.issues] == [
        (
            "INFO",
            "naming.no_stock_libraries",
            "KiCad's symbol libraries were not found, so similar KiCad parts were not looked up",
        )
    ]
    assert suggestion.name == ""


def test_without_kicad_the_own_lookup_still_runs(tmp_path):
    own = own_index(_owner_symbols(tmp_path, "Atomic_Transistor_FET", "CSD99999"))

    suggestion = suggest_library(PartMeta("CSD85301Q2"), own=own, stock=None)

    assert suggestion.name == "Atomic_Transistor_FET"
    assert suggestion.source == "own"
    assert suggestion.issues == ()


# -- no manufacturer, ever (LIB-04) --------------------------------------------

_ODD_METAS = [
    PartMeta(""),
    PartMeta("12345"),
    PartMeta("TI-PART", manufacturer="Texas Instruments", mpn="TI-PART"),
    PartMeta("GCT-USB", manufacturer="GCT", datasheet="https://gct.co/x.pdf"),
    PartMeta("RECOM-1", manufacturer="RECOM", category="Power Supply"),
    PartMeta("Abracon_X", manufacturer="Abracon", description="TCXO oscillator"),
    PartMeta("X" * 400, description="long " * 200),
]


@pytest.mark.parametrize("meta", _ODD_METAS, ids=range(len(_ODD_METAS)))
def test_a_suggestion_is_empty_or_passes_the_name_rule_and_never_holds_a_manufacturer(meta, tmp_path):
    symbols_dir, _ = write_stock_sample(tmp_path)

    for stock in (None, stock_index(symbols_dir)):
        suggestion = suggest_library(meta, stock=stock)
        assert suggestion.name == "" or existing_libraries([suggestion.name]) == [suggestion.name]
        tokens = suggestion.name.split("_")
        assert not {"TI", "GCT", "RECOM", "Abracon"} & set(tokens)


def test_existing_libraries_keeps_the_names_that_pass_the_rule_sorted():
    names = ["Atomic_Sensor_Motion", "IC_Battery_Charger_TI", "Atomic_MyStuff", "atomic_connector", "Atomic_Battery_Management"]

    assert existing_libraries(names) == ["Atomic_Battery_Management", "Atomic_Sensor_Motion"]


@pytest.mark.parametrize("meta", _ODD_METAS, ids=range(len(_ODD_METAS)))
def test_the_wording_never_names_a_raw_field(meta, tmp_path):
    from kicad_lib_manager.importer.suggest import NO_STOCK_TEXT
    from kicad_lib_manager.widgets import import_dialog

    symbols_dir, _ = write_stock_sample(tmp_path)
    texts = [NO_STOCK_TEXT, import_dialog._LIBRARY_PLACEHOLDER]
    for stock in (None, stock_index(symbols_dir)):
        suggestion = suggest_library(meta, stock=stock)
        texts += [suggestion_text(suggestion), suggestion.reason, *(i.text for i in suggestion.issues)]
    for text in texts:
        assert "ki_" not in text.casefold()


def test_suggestion_text_without_alternatives_ends_with_a_period():
    suggestion = LibrarySuggestion("Atomic_Diode", "own", "Suggested from 2 similar parts in your Atomic_Diode", (), (), ())

    assert suggestion_text(suggestion) == "Suggested from 2 similar parts in your Atomic_Diode."
