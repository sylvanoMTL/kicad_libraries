import pytest
from PySide6.QtCore import Qt

from kicad_lib_manager.models import (
    STATUS_CHANGED, STATUS_NEW, ChangedFootprint, Finding, FootprintLibrary, FootprintRef,
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


# ── Task 2: New and Changed highlights, combined status, auto-expand ──

SYM_CUSTOM = "Custom/Symbols/Plain.kicad_sym"
FP_CUSTOM = "Custom/Footprints/Plain.pretty"


def _widget(qtbot, scan):
    w = LibraryTableWidget()
    qtbot.addWidget(w)
    w.populate(scan)
    return w


def test_changed_symbol_is_accent_with_changed_status_and_tooltip(qtbot):
    scan = ScanResult(symbol_libs=[SymbolLibrary(
        "Plain", SYM_CUSTOM, "Custom", symbols=[SymbolEntry("S1", status=STATUS_CHANGED)])])
    w = _widget(qtbot, scan)
    (row,) = _children(_lib_item(w, SYM_CUSTOM))
    assert row.text(3) == "Changed"
    assert all(_colour(row, c) == theme.ACCENT.lower() for c in range(row.columnCount()))
    assert "Changed since the last Custom commit" in row.toolTip(0)
    assert "Changed since the last Custom commit" in row.toolTip(3)


def test_new_symbol_is_accent_with_new_status_and_tooltip(qtbot):
    scan = ScanResult(symbol_libs=[SymbolLibrary(
        "Plain", SYM_CUSTOM, "Custom", symbols=[SymbolEntry("S1", status=STATUS_NEW)])])
    w = _widget(qtbot, scan)
    (row,) = _children(_lib_item(w, SYM_CUSTOM))
    assert row.text(3) == "New"
    assert _colour(row) == theme.ACCENT.lower()
    assert "New since the last Custom commit" in row.toolTip(3)


def test_failing_and_changed_symbol_is_one_amber_row_with_both_facts(qtbot):
    entry = SymbolEntry("S1", status=STATUS_CHANGED, violations=[V_FOOTPRINT, V_DESCRIPTION])
    scan = ScanResult(symbol_libs=[SymbolLibrary(
        "Atomic_Test", ATOMIC, "Custom", atomic=True, symbols=[entry])])
    w = _widget(qtbot, scan)
    rows = _children(_lib_item(w))
    assert len(rows) == 1
    row = rows[0]
    assert row.text(3) == "Changed \u00b7 2 rules"
    assert not row.icon(3).isNull()
    assert _colour(row) == theme.AMBER.lower()
    tip = row.toolTip(0)
    assert V_FOOTPRINT.text in tip and V_DESCRIPTION.text in tip
    assert "Changed since the last Custom commit" in tip


def test_non_atomic_library_shows_only_its_changed_entries(qtbot):
    scan = ScanResult(symbol_libs=[SymbolLibrary(
        "Plain", SYM_CUSTOM, "Custom", footprint_refs=[FootprintRef("Plain", "A", True)],
        symbols=[SymbolEntry("S1", status=STATUS_NEW)])])
    w = _widget(qtbot, scan)
    item = _lib_item(w, SYM_CUSTOM)
    assert [r.text(0) for r in _children(item)] == ["S1"]
    assert item.text(3) == "OK"


def test_changed_footprints_get_child_rows_in_order(qtbot):
    scan = ScanResult(footprint_libs=[FootprintLibrary(
        "Plain", FP_CUSTOM, "Custom",
        changed=[ChangedFootprint("A", STATUS_NEW), ChangedFootprint("B", STATUS_CHANGED)])])
    w = _widget(qtbot, scan)
    item = w._fp_items[FP_CUSTOM]
    rows = _children(item)
    assert [(r.text(0), r.text(2)) for r in rows] == [("A", "New"), ("B", "Changed")]
    for row in rows:
        assert not (row.flags() & Qt.ItemFlag.ItemIsUserCheckable)
        assert row.data(0, Qt.ItemDataRole.CheckStateRole) is None
        assert all(_colour(row, c) == theme.ACCENT.lower() for c in range(row.columnCount()))
    assert item.text(2) == "OK"


def test_only_libraries_with_something_to_show_are_expanded(qtbot):
    scan = ScanResult(
        symbol_libs=[
            SymbolLibrary("Atomic_Bad", "Custom/Symbols/Atomic_Bad.kicad_sym", "Custom",
                          atomic=True, symbols=[SymbolEntry("S", violations=[V_KEYWORDS])]),
            SymbolLibrary("Atomic_Clean", "Custom/Symbols/Atomic_Clean.kicad_sym", "Custom",
                          atomic=True, symbols=[SymbolEntry("S")]),
            SymbolLibrary("Plain", SYM_CUSTOM, "Custom", symbols=[SymbolEntry("S", status=STATUS_NEW)]),
        ],
        footprint_libs=[
            FootprintLibrary("Plain", FP_CUSTOM, "Custom", changed=[ChangedFootprint("A", STATUS_NEW)]),
            FootprintLibrary("Quiet", "Custom/Footprints/Quiet.pretty", "Custom"),
        ],
    )
    w = _widget(qtbot, scan)
    sym = w._sym_items
    assert sym["Custom/Symbols/Atomic_Bad.kicad_sym"].isExpanded()
    assert not sym["Custom/Symbols/Atomic_Clean.kicad_sym"].isExpanded()
    assert sym[SYM_CUSTOM].isExpanded()
    assert w._fp_items[FP_CUSTOM].isExpanded()
    assert not w._fp_items["Custom/Footprints/Quiet.pretty"].isExpanded()
    assert w._sym_tree.topLevelItem(0).isExpanded()
    assert w._fp_tree.topLevelItem(0).isExpanded()


def test_expand_all_and_collapse_all_reach_child_rows(qtbot):
    scan = ScanResult(symbol_libs=[SymbolLibrary(
        "Atomic_Clean", ATOMIC, "Custom", atomic=True, symbols=[SymbolEntry("S")])])
    w = _widget(qtbot, scan)
    item = _lib_item(w)
    assert not item.isExpanded()
    w._sym_tree.expandAll()
    assert item.isExpanded()
    w._sym_tree.collapseAll()
    assert not item.isExpanded()


def test_atomic_library_without_symbols_says_no_symbols(qtbot):
    scan = ScanResult(symbol_libs=[SymbolLibrary("Atomic_Test", ATOMIC, "Custom", atomic=True)])
    w = _widget(qtbot, scan)
    item = _lib_item(w)
    assert item.text(3) == "No symbols"
    assert item.childCount() == 0


def test_library_that_could_not_be_checked_says_so_with_the_reason(qtbot):
    scan = ScanResult(symbol_libs=[SymbolLibrary(
        "Atomic_Test", ATOMIC, "Custom", atomic=True,
        check_problem="the library file could not be read")])
    w = _widget(qtbot, scan)
    item = _lib_item(w)
    assert item.text(3) == "Could not check"
    assert not item.icon(3).isNull()
    assert _colour(item) == theme.AMBER.lower()
    assert "the library file could not be read" in item.toolTip(3)
    assert item.childCount() == 0


def test_finding_only_entry_is_ok_and_shows_the_finding(qtbot):
    entry = SymbolEntry("S1", findings=[Finding("leftover", "Leftover price data is present")])
    scan = ScanResult(symbol_libs=[SymbolLibrary(
        "Atomic_Test", ATOMIC, "Custom", atomic=True, symbols=[entry])])
    w = _widget(qtbot, scan)
    (row,) = _children(_lib_item(w))
    assert row.text(3) == "OK"
    assert "Leftover price data is present" in row.toolTip(0)
    assert _lib_item(w).isExpanded() is False


def test_scan_text_in_tooltips_is_escaped(qtbot):
    evil = Violation("r", "Bad <b>x</b> value")
    entry = SymbolEntry("<b>x</b>", violations=[evil], findings=[Finding("k", "<i>note</i>")])
    scan = ScanResult(symbol_libs=[SymbolLibrary(
        "Atomic_Test", ATOMIC, "Custom", atomic=True, symbols=[entry])])
    w = _widget(qtbot, scan)
    (row,) = _children(_lib_item(w))
    tip = row.toolTip(0)
    assert "&lt;b&gt;x&lt;/b&gt;" in tip
    assert "&lt;i&gt;note&lt;/i&gt;" in tip
    assert "<b>" not in tip and "<i>" not in tip


def test_no_internal_field_names_in_tree_text_or_tooltips(qtbot):
    scan = ScanResult(
        symbol_libs=[SymbolLibrary(
            "Atomic_Test", ATOMIC, "Custom", atomic=True,
            symbols=[SymbolEntry("A", status=STATUS_CHANGED, violations=[V_DESCRIPTION]),
                     SymbolEntry("B", status=STATUS_NEW)])],
        footprint_libs=[FootprintLibrary(
            "Plain", FP_CUSTOM, "Custom", changed=[ChangedFootprint("F", STATUS_NEW)])],
    )
    w = _widget(qtbot, scan)
    assert "ki_" not in _all_tip_text(w)


# ── Task 3: selection safety and the symbol_activated signal ──

FP_REF = "Custom/Footprints/Atomic_Test.pretty"


def _selection_scan():
    sym = SymbolLibrary(
        "Atomic_Test", ATOMIC, "Custom", atomic=True,
        footprint_refs=[FootprintRef("Atomic_Test", "A", True)], symbols=_symbols())
    fp = FootprintLibrary("Atomic_Test", FP_REF, "Custom")
    return ScanResult(symbol_libs=[sym], footprint_libs=[fp])


def _checks(scan):
    return [lib.selected for lib in (*scan.symbol_libs, *scan.footprint_libs)]


def test_child_row_has_no_check_state_and_is_not_checkable(qtbot):
    w = _widget(qtbot, _selection_scan())
    for row in _children(_lib_item(w)):
        assert row.data(0, Qt.ItemDataRole.CheckStateRole) is None
        assert not (row.flags() & Qt.ItemFlag.ItemIsUserCheckable)


def test_selection_is_unchanged_when_a_child_row_changes(qtbot):
    scan = _selection_scan()
    w = _widget(qtbot, scan)
    fp_item = w._fp_items[FP_REF]
    # A footprint the user ticked by hand; no selected symbol asks for it
    fp_item.setCheckState(0, Qt.CheckState.Checked)
    before = (_checks(scan), fp_item.checkState(0))
    assert before[0] == [False, True]

    row = _children(_lib_item(w))[1]
    # A symbol named like its source used to reach the source-wide footprint recalculation
    row.setText(0, "Custom")
    row.setText(3, "something else")
    row.setIcon(3, w.style().standardIcon(w.style().StandardPixmap.SP_MessageBoxWarning))
    row.setData(0, Qt.ItemDataRole.UserRole, row.data(0, Qt.ItemDataRole.UserRole))

    assert (_checks(scan), fp_item.checkState(0)) == before


def test_selection_of_a_library_with_child_rows_still_syncs_footprints(qtbot):
    scan = _selection_scan()
    w = _widget(qtbot, scan)
    _lib_item(w).setCheckState(0, Qt.CheckState.Checked)
    assert _checks(scan) == [True, True]
    assert w._fp_items[FP_REF].checkState(0) == Qt.CheckState.Checked
    _lib_item(w).setCheckState(0, Qt.CheckState.Unchecked)
    assert _checks(scan) == [False, False]


def test_select_all_and_deselect_all_act_on_library_rows_only(qtbot):
    scan = _selection_scan()
    w = _widget(qtbot, scan)
    w.select_all()
    assert _checks(scan) == [True, True]
    for row in _children(_lib_item(w)):
        assert row.data(0, Qt.ItemDataRole.CheckStateRole) is None
    w.deselect_all()
    assert _checks(scan) == [False, False]
    for row in _children(_lib_item(w)):
        assert row.data(0, Qt.ItemDataRole.CheckStateRole) is None


def _activate(w, item):
    w._sym_tree.itemDoubleClicked.emit(item, 0)


def test_double_click_on_a_row_with_rule_problems_emits_symbol_activated(qtbot):
    w = _widget(qtbot, _selection_scan())
    _, two, _ = _children(_lib_item(w))
    with qtbot.waitSignal(w.symbol_activated, timeout=1000) as blocker:
        _activate(w, two)
    assert blocker.args == [ATOMIC, "TWO_BAD"]


def test_double_click_on_a_row_with_only_findings_emits_symbol_activated(qtbot):
    entry = SymbolEntry("S1", findings=[Finding("leftover", "Leftover price data is present")])
    scan = ScanResult(symbol_libs=[SymbolLibrary(
        "Atomic_Test", ATOMIC, "Custom", atomic=True, symbols=[entry])])
    w = _widget(qtbot, scan)
    (row,) = _children(_lib_item(w))
    with qtbot.waitSignal(w.symbol_activated, timeout=1000) as blocker:
        _activate(w, row)
    assert blocker.args == [ATOMIC, "S1"]


def test_double_click_on_ok_changed_only_library_and_footprint_rows_emits_nothing(qtbot):
    scan = _selection_scan()
    scan.symbol_libs[0].symbols.append(SymbolEntry("CHANGED_ONLY", status=STATUS_CHANGED))
    scan.footprint_libs[0].changed.append(ChangedFootprint("A", STATUS_NEW))
    w = _widget(qtbot, scan)
    ok, _, _, changed_only = _children(_lib_item(w))
    fp_row = w._fp_items[FP_REF].child(0)
    with qtbot.assertNotEmitted(w.symbol_activated):
        _activate(w, ok)
        _activate(w, changed_only)
        _activate(w, _lib_item(w))
        _activate(w, w._sym_tree.topLevelItem(0))
        w._fp_tree.itemDoubleClicked.emit(fp_row, 0)
        w._fp_tree.itemDoubleClicked.emit(w._fp_items[FP_REF], 0)
