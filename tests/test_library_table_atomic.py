import pytest
from PySide6.QtCore import Qt

from kicad_lib_manager.models import (
    ScanResult, SymbolEntry, SymbolLibrary, Violation,
)
from kicad_lib_manager.widgets import theme
from kicad_lib_manager.widgets.library_table import LibraryTableWidget

ATOMIC = "Custom/Symbols/Atomic_Test.kicad_sym"

V_FOOTPRINT = Violation("footprint", "The footprint is not linked to the library")
V_DESCRIPTION = Violation("description", "The description is empty")
V_KEYWORDS = Violation("keywords", "Search keywords are missing")


def _symbols():
    return [
        SymbolEntry("OK_PART"),
        SymbolEntry("TWO_BAD", violations=[V_FOOTPRINT, V_DESCRIPTION]),
        SymbolEntry("ONE_BAD", violations=[V_KEYWORDS]),
    ]


@pytest.fixture
def scan():
    return ScanResult(
        symbol_libs=[SymbolLibrary("Atomic_Test", ATOMIC, "Custom", atomic=True, symbols=_symbols())],
    )


@pytest.fixture
def widget(qtbot, scan):
    w = LibraryTableWidget()
    qtbot.addWidget(w)
    w.populate(scan)
    return w


def _lib_item(widget, rel_path=ATOMIC):
    return widget._sym_items[rel_path]


def _children(item):
    return [item.child(i) for i in range(item.childCount())]


def _colour(item, col=0):
    return item.foreground(col).color().name().lower()


def _all_tip_text(widget):
    """Every text and tooltip of every row in both trees."""
    texts = []
    for tree in (widget._sym_tree, widget._fp_tree):
        stack = [tree.topLevelItem(i) for i in range(tree.topLevelItemCount())]
        while stack:
            item = stack.pop()
            for col in range(item.columnCount()):
                texts.append(item.text(col))
                texts.append(item.toolTip(col))
            stack.extend(_children(item))
    return "\n".join(texts)


# ── tracer: failing symbol rows and the library count ──

def test_symbol_child_rows_follow_library_order_and_have_no_checkbox(widget):
    rows = _children(_lib_item(widget))
    assert [r.text(0) for r in rows] == ["OK_PART", "TWO_BAD", "ONE_BAD"]
    for row in rows:
        assert row.data(0, Qt.ItemDataRole.CheckStateRole) is None
        assert not (row.flags() & Qt.ItemFlag.ItemIsUserCheckable)


def test_failing_rows_are_amber_with_warning_icon_and_a_rule_count(widget):
    ok, two, one = _children(_lib_item(widget))
    assert (ok.text(3), two.text(3), one.text(3)) == ("OK", "2 rules", "1 rule")
    for row in (two, one):
        assert not row.icon(3).isNull()
        assert all(_colour(row, c) == theme.AMBER.lower() for c in range(row.columnCount()))
    assert ok.icon(3).isNull()


def test_failing_row_tooltip_lists_every_broken_rule_on_its_own_line(widget):
    _, two, _ = _children(_lib_item(widget))
    for col in (0, 3):
        tip = two.toolTip(col)
        assert V_FOOTPRINT.text in tip and V_DESCRIPTION.text in tip
        assert tip.count("<br>") == 1


def test_library_status_counts_failing_symbols(widget):
    item = _lib_item(widget)
    assert item.text(3) == "2 of 3 fail"
    assert not item.icon(3).isNull()
    assert _colour(item) == theme.AMBER.lower()
    assert item.toolTip(3) == "2 of 3 symbols fail the atomic check"


def test_collision_keeps_precedence_over_the_failing_count(qtbot):
    other = "Custom/Other/Atomic_Test.kicad_sym"
    scan = ScanResult(symbol_libs=[
        SymbolLibrary("Atomic_Test", ATOMIC, "Custom", collision_peers=[other],
                      atomic=True, symbols=_symbols()),
        SymbolLibrary("Atomic_Test", other, "Custom", collision_peers=[ATOMIC]),
    ])
    w = LibraryTableWidget()
    qtbot.addWidget(w)
    w.populate(scan)
    item = _lib_item(w)
    assert item.text(3) == "Collision"
    assert "2 of 3 symbols fail the atomic check" in item.toolTip(3)
