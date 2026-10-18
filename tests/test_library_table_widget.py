import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from kicad_lib_manager.models import FootprintLibrary, FootprintRef, ScanResult, SymbolLibrary
from kicad_lib_manager.widgets.library_table import LibraryTableWidget


@pytest.fixture
def scan():
    return ScanResult(
        symbol_libs=[
            SymbolLibrary(
                "Sym_C", "Custom/Symbols/Sym_C.kicad_sym", "Custom",
                footprint_refs=[FootprintRef("FP_C", "A", True)],
            ),
            SymbolLibrary(
                "Sym_W", "WurthElektronik/KiCad-Library/symbols/Sym_W.kicad_sym",
                "WurthElektronik",
                footprint_refs=[FootprintRef("FP_W", "B", True)],
            ),
        ],
        footprint_libs=[
            FootprintLibrary("FP_C", "Custom/Footprints/FP_C.pretty", "Custom"),
            FootprintLibrary(
                "FP_W", "WurthElektronik/KiCad-Library/footprints/FP_W.pretty",
                "WurthElektronik",
            ),
        ],
    )


# Private widget access lives in these two helpers so Phase 2 adapts one place
def _sym_item(widget, source_idx, child_idx=0):
    # Sources are sorted: Custom=0, WurthElektronik=1
    return widget._sym_tree.topLevelItem(source_idx).child(child_idx)


def _fp_item(widget, nickname):
    return widget._fp_items[nickname]


@pytest.fixture
def widget(qtbot, scan):
    w = LibraryTableWidget()
    qtbot.addWidget(w)
    w.populate(scan)
    return w


def test_platform_is_offscreen(qapp):
    assert QGuiApplication.platformName() == "offscreen"


def test_toggle_symbol_selects_and_deselects_its_footprint(widget, scan):
    fp_c = scan.footprint_libs[0]
    _sym_item(widget, 0).setCheckState(0, Qt.CheckState.Checked)
    assert fp_c.selected is True
    assert _fp_item(widget, "FP_C").checkState(0) == Qt.CheckState.Checked

    _sym_item(widget, 0).setCheckState(0, Qt.CheckState.Unchecked)
    assert fp_c.selected is False
    assert _fp_item(widget, "FP_C").checkState(0) == Qt.CheckState.Unchecked


def test_toggle_is_scoped_per_source(widget, scan):
    sym_c, sym_w = scan.symbol_libs
    fp_c, fp_w = scan.footprint_libs

    # Wurth symbol on
    _sym_item(widget, 1).setCheckState(0, Qt.CheckState.Checked)
    assert (sym_w.selected, fp_w.selected, fp_c.selected) == (True, True, False)

    # Custom symbol on
    _sym_item(widget, 0).setCheckState(0, Qt.CheckState.Checked)
    assert (fp_c.selected, fp_w.selected) == (True, True)

    # Custom symbol off leaves the Wurth footprint alone
    _sym_item(widget, 0).setCheckState(0, Qt.CheckState.Unchecked)
    assert (fp_c.selected, fp_w.selected) == (False, True)
    assert _fp_item(widget, "FP_W").checkState(0) == Qt.CheckState.Checked


def test_group_header_selects_only_its_source(widget, scan):
    sym_c, sym_w = scan.symbol_libs
    fp_c, fp_w = scan.footprint_libs

    widget._sym_tree.topLevelItem(0).setCheckState(0, Qt.CheckState.Checked)

    assert (sym_c.selected, fp_c.selected) == (True, True)
    assert (sym_w.selected, fp_w.selected) == (False, False)


def test_select_all_then_deselect_all(widget, scan):
    libs = [*scan.symbol_libs, *scan.footprint_libs]

    widget.select_all()
    assert all(lib.selected for lib in libs)

    widget.deselect_all()
    assert not any(lib.selected for lib in libs)
