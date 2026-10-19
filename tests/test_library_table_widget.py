import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

from kicad_lib_manager.models import FootprintLibrary, FootprintRef, ScanResult, SymbolLibrary
from kicad_lib_manager.widgets.library_table import LibraryTableWidget

SYM_C = "Custom/Symbols/Sym_C.kicad_sym"
SYM_W = "WurthElektronik/KiCad-Library/symbols/Sym_W.kicad_sym"
FP_C = "Custom/Footprints/FP_C.pretty"
FP_W = "WurthElektronik/KiCad-Library/footprints/FP_W.pretty"
SAME_FP_C = "Custom/Footprints/Same.pretty"
SAME_FP_W = "WurthElektronik/KiCad-Library/footprints/Same.pretty"


@pytest.fixture
def scan():
    return ScanResult(
        symbol_libs=[
            SymbolLibrary(
                "Sym_C", SYM_C, "Custom",
                footprint_refs=[FootprintRef("FP_C", "A", True)],
            ),
            SymbolLibrary(
                "Sym_W", SYM_W, "WurthElektronik",
                footprint_refs=[FootprintRef("FP_W", "B", True)],
            ),
        ],
        footprint_libs=[
            FootprintLibrary("FP_C", FP_C, "Custom"),
            FootprintLibrary("FP_W", FP_W, "WurthElektronik"),
        ],
    )


# Private widget access lives in these two helpers so a change of keying adapts one place
def _sym_item(widget, rel_path):
    return widget._sym_items[rel_path]


def _fp_item(widget, rel_path):
    return widget._fp_items[rel_path]


@pytest.fixture
def widget(qtbot, scan):
    w = LibraryTableWidget()
    qtbot.addWidget(w)
    w.populate(scan)
    return w


def _make_widget(qtbot, scan):
    w = LibraryTableWidget()
    qtbot.addWidget(w)
    w.populate(scan)
    return w


def test_platform_is_offscreen(qapp):
    assert QGuiApplication.platformName() == "offscreen"


def test_toggle_symbol_selects_and_deselects_its_footprint(widget, scan):
    fp_c = scan.footprint_libs[0]
    _sym_item(widget, SYM_C).setCheckState(0, Qt.CheckState.Checked)
    assert fp_c.selected is True
    assert _fp_item(widget, FP_C).checkState(0) == Qt.CheckState.Checked

    _sym_item(widget, SYM_C).setCheckState(0, Qt.CheckState.Unchecked)
    assert fp_c.selected is False
    assert _fp_item(widget, FP_C).checkState(0) == Qt.CheckState.Unchecked


def test_toggle_is_scoped_per_source(widget, scan):
    sym_c, sym_w = scan.symbol_libs
    fp_c, fp_w = scan.footprint_libs

    # Wurth symbol on
    _sym_item(widget, SYM_W).setCheckState(0, Qt.CheckState.Checked)
    assert (sym_w.selected, fp_w.selected, fp_c.selected) == (True, True, False)

    # Custom symbol on
    _sym_item(widget, SYM_C).setCheckState(0, Qt.CheckState.Checked)
    assert (fp_c.selected, fp_w.selected) == (True, True)

    # Custom symbol off leaves the Wurth footprint alone
    _sym_item(widget, SYM_C).setCheckState(0, Qt.CheckState.Unchecked)
    assert (fp_c.selected, fp_w.selected) == (False, True)
    assert _fp_item(widget, FP_W).checkState(0) == Qt.CheckState.Checked


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


# ── rel_path keying, populate without re-sync, source-scoped sync (D-02, HARD-07) ──


def _same_fp_scan():
    """Footprint 'Same' exists in both sources; each source also has an own footprint."""
    return ScanResult(
        symbol_libs=[
            SymbolLibrary(
                "Sym_C", SYM_C, "Custom",
                footprint_refs=[FootprintRef("Same", "A", True)],
            ),
            SymbolLibrary(
                "Sym_W", SYM_W, "WurthElektronik",
                footprint_refs=[FootprintRef("FP_W", "B", True)],
            ),
        ],
        footprint_libs=[
            FootprintLibrary("Same", SAME_FP_C, "Custom"),
            FootprintLibrary("FP_W", FP_W, "WurthElektronik"),
            FootprintLibrary("Same", SAME_FP_W, "WurthElektronik"),
        ],
    )


def test_same_nickname_footprints_get_separate_items(qtbot):
    scan = _same_fp_scan()
    w = _make_widget(qtbot, scan)

    assert len(w._fp_items) == 3
    assert _fp_item(w, SAME_FP_C).text(0) == "Same"
    assert _fp_item(w, SAME_FP_W).text(0) == "Same"
    assert _fp_item(w, SAME_FP_C) is not _fp_item(w, SAME_FP_W)
    # One child under each source group
    assert _fp_item(w, SAME_FP_C).parent().text(0) == "Custom"
    assert _fp_item(w, SAME_FP_W).parent().text(0) == "WurthElektronik"


def test_same_nickname_symbols_get_separate_items(qtbot):
    scan = ScanResult(symbol_libs=[
        SymbolLibrary("Same", "Custom/Symbols/Same.kicad_sym", "Custom"),
        SymbolLibrary("Same", "WurthElektronik/KiCad-Library/symbols/Same.kicad_sym",
                      "WurthElektronik"),
    ])
    w = _make_widget(qtbot, scan)

    assert len(w._sym_items) == 2
    assert _sym_item(w, "Custom/Symbols/Same.kicad_sym").text(0) == "Same"
    assert _sym_item(w, "WurthElektronik/KiCad-Library/symbols/Same.kicad_sym").text(0) == "Same"


def test_populate_keeps_selected_footprint_that_no_symbol_references(qtbot):
    solo = FootprintLibrary("Solo", "Custom/Footprints/Solo.pretty", "Custom", selected=True)
    scan = ScanResult(
        symbol_libs=[
            SymbolLibrary(
                "Sym_C", SYM_C, "Custom", selected=True,
                footprint_refs=[FootprintRef("FP_C", "A", True)],
            ),
        ],
        footprint_libs=[FootprintLibrary("FP_C", FP_C, "Custom"), solo],
    )
    w = _make_widget(qtbot, scan)

    assert _fp_item(w, "Custom/Footprints/Solo.pretty").checkState(0) == Qt.CheckState.Checked
    assert solo.selected is True
    # populate renders flags, it does not derive them: FP_C is referenced by a selected
    # symbol but its own flag was False, so it stays unchecked
    assert _fp_item(w, FP_C).checkState(0) == Qt.CheckState.Unchecked
    assert scan.footprint_libs[0].selected is False


def test_populate_renders_selected_flags_for_symbols(qtbot):
    sym = SymbolLibrary("Sym_C", SYM_C, "Custom", selected=True)
    w = _make_widget(qtbot, ScanResult(symbol_libs=[sym]))

    assert _sym_item(w, SYM_C).checkState(0) == Qt.CheckState.Checked
    assert sym.selected is True


def test_custom_symbol_drives_only_the_custom_footprint_of_the_same_nickname(qtbot):
    scan = _same_fp_scan()
    w = _make_widget(qtbot, scan)
    fp_same_c, _, fp_same_w = scan.footprint_libs

    _sym_item(w, SYM_C).setCheckState(0, Qt.CheckState.Checked)

    assert fp_same_c.selected is True
    assert _fp_item(w, SAME_FP_C).checkState(0) == Qt.CheckState.Checked
    assert fp_same_w.selected is False
    assert _fp_item(w, SAME_FP_W).checkState(0) == Qt.CheckState.Unchecked


def test_wurth_symbol_never_changes_custom_footprints(qtbot):
    scan = _same_fp_scan()
    w = _make_widget(qtbot, scan)
    fp_same_c, fp_w, _ = scan.footprint_libs

    _sym_item(w, SYM_C).setCheckState(0, Qt.CheckState.Checked)
    _sym_item(w, SYM_W).setCheckState(0, Qt.CheckState.Checked)

    assert fp_w.selected is True
    assert fp_same_c.selected is True
    assert _fp_item(w, SAME_FP_C).checkState(0) == Qt.CheckState.Checked


def test_toggling_a_symbol_recomputes_its_source_and_unchecks_standalone_footprint(qtbot):
    # Pins CURRENT behaviour (CONCERNS.md "Footprint checkboxes are overwritten by symbol
    # state"): a symbol toggle recomputes every footprint of its source from the selected
    # symbols, so a footprint selected without any referencing symbol is dropped.
    solo = FootprintLibrary("Solo", "Custom/Footprints/Solo.pretty", "Custom", selected=True)
    scan = ScanResult(
        symbol_libs=[
            SymbolLibrary(
                "Sym_C", SYM_C, "Custom",
                footprint_refs=[FootprintRef("FP_C", "A", True)],
            ),
        ],
        footprint_libs=[FootprintLibrary("FP_C", FP_C, "Custom"), solo],
    )
    w = _make_widget(qtbot, scan)
    assert solo.selected is True

    _sym_item(w, SYM_C).setCheckState(0, Qt.CheckState.Checked)

    assert solo.selected is False
    assert _fp_item(w, "Custom/Footprints/Solo.pretty").checkState(0) == Qt.CheckState.Unchecked
    assert scan.footprint_libs[0].selected is True


def test_updating_flag_is_clear_after_operations(qtbot):
    scan = _same_fp_scan()
    w = _make_widget(qtbot, scan)

    _sym_item(w, SYM_C).setCheckState(0, Qt.CheckState.Checked)
    w.select_all()
    w.deselect_all()

    assert w._updating is False


# ── collision mark and mutual exclusion (D-01, HARD-08) ──

SAME_SYM_C = "Custom/Symbols/Same.kicad_sym"
SAME_SYM_W = "WurthElektronik/KiCad-Library/symbols/Same.kicad_sym"
OWN_SYM_C = "Custom/Symbols/Own_C.kicad_sym"
OWN_SYM_W = "WurthElektronik/KiCad-Library/symbols/Own_W.kicad_sym"
OWN_FP_C = "Custom/Footprints/Own_C.pretty"
OWN_FP_W = "WurthElektronik/KiCad-Library/footprints/Own_W.pretty"


def _collision_scan():
    """Symbols and footprints named 'Same' collide between Custom and WurthElektronik.

    The Wurth 'Own_W' symbol references both its own footprint and 'Same', so the Wurth
    'Same' footprint is wanted by a selected symbol and only the peer rule can hold it back.
    """
    return ScanResult(
        symbol_libs=[
            SymbolLibrary(
                "Same", SAME_SYM_C, "Custom",
                footprint_refs=[FootprintRef("Same", "A", True)],
                collision_peers=[SAME_SYM_W],
            ),
            SymbolLibrary(
                "Own_C", OWN_SYM_C, "Custom",
                footprint_refs=[FootprintRef("Own_C", "A", True)],
            ),
            SymbolLibrary(
                "Same", SAME_SYM_W, "WurthElektronik",
                footprint_refs=[FootprintRef("Same", "A", True)],
                collision_peers=[SAME_SYM_C],
            ),
            SymbolLibrary(
                "Own_W", OWN_SYM_W, "WurthElektronik",
                footprint_refs=[FootprintRef("Own_W", "A", True), FootprintRef("Same", "B", True)],
            ),
        ],
        footprint_libs=[
            FootprintLibrary("Same", SAME_FP_C, "Custom", collision_peers=[SAME_FP_W]),
            FootprintLibrary("Own_C", OWN_FP_C, "Custom"),
            FootprintLibrary("Same", SAME_FP_W, "WurthElektronik", collision_peers=[SAME_FP_C]),
            FootprintLibrary("Own_W", OWN_FP_W, "WurthElektronik"),
        ],
    )


def _lib(scan, rel_path):
    for lib in [*scan.symbol_libs, *scan.footprint_libs]:
        if lib.rel_path == rel_path:
            return lib
    raise KeyError(rel_path)


def _assert_invariants(w, scan):
    """At most one selected per collided pair, no stuck guard, nicknames untouched."""
    assert w._updating is False
    for libs, items in ((scan.symbol_libs, w._sym_items), (scan.footprint_libs, w._fp_items)):
        for lib in libs:
            assert items[lib.rel_path].text(0) == lib.nickname
            for peer in lib.collision_peers:
                assert not (lib.selected and _lib(scan, peer).selected)
            # item state mirrors the model flag
            expected = Qt.CheckState.Checked if lib.selected else Qt.CheckState.Unchecked
            assert items[lib.rel_path].checkState(0) == expected


def test_collided_symbol_is_marked_with_collision_status_and_tooltip(qtbot):
    scan = _collision_scan()
    w = _make_widget(qtbot, scan)

    for rel_path, peer in ((SAME_SYM_C, SAME_SYM_W), (SAME_SYM_W, SAME_SYM_C)):
        item = _sym_item(w, rel_path)
        assert item.text(0) == "Same"
        assert item.text(3) == "Collision"
        assert not item.icon(3).isNull()
        assert peer in item.toolTip(0)
        for col in range(item.columnCount()):
            assert item.foreground(col).color().name().upper() == "#CC7700"

    # A non-collided symbol keeps the normal status
    assert _sym_item(w, OWN_SYM_C).text(3) == "OK"


def test_collided_footprint_is_marked_with_collision_status_and_tooltip(qtbot):
    scan = _collision_scan()
    w = _make_widget(qtbot, scan)

    for rel_path, peer in ((SAME_FP_C, SAME_FP_W), (SAME_FP_W, SAME_FP_C)):
        item = _fp_item(w, rel_path)
        assert item.text(0) == "Same"
        assert item.text(2) == "Collision"
        assert not item.icon(2).isNull()
        assert peer in item.toolTip(0)
        for col in range(item.columnCount()):
            assert item.foreground(col).color().name().upper() == "#CC7700"

    assert _fp_item(w, OWN_FP_C).text(2) == "OK"


def test_collision_tooltip_also_mentions_missing_footprints(qtbot):
    scan = ScanResult(symbol_libs=[
        SymbolLibrary(
            "Same", SAME_SYM_C, "Custom",
            footprint_refs=[FootprintRef("Gone", "A", False)],
            collision_peers=[SAME_SYM_W],
        ),
        SymbolLibrary("Same", SAME_SYM_W, "WurthElektronik", collision_peers=[SAME_SYM_C]),
    ])
    w = _make_widget(qtbot, scan)

    item = _sym_item(w, SAME_SYM_C)
    assert item.text(3) == "Collision"
    assert "Missing FP" in item.toolTip(0)


def test_checking_a_collided_symbol_unchecks_its_peer(qtbot):
    scan = _collision_scan()
    w = _make_widget(qtbot, scan)
    same_c, same_w = _lib(scan, SAME_SYM_C), _lib(scan, SAME_SYM_W)

    _sym_item(w, SAME_SYM_W).setCheckState(0, Qt.CheckState.Checked)
    assert (same_c.selected, same_w.selected) == (False, True)
    _assert_invariants(w, scan)

    _sym_item(w, SAME_SYM_C).setCheckState(0, Qt.CheckState.Checked)
    assert (same_c.selected, same_w.selected) == (True, False)
    assert _sym_item(w, SAME_SYM_W).checkState(0) == Qt.CheckState.Unchecked
    _assert_invariants(w, scan)

    # and the reverse
    _sym_item(w, SAME_SYM_W).setCheckState(0, Qt.CheckState.Checked)
    assert (same_c.selected, same_w.selected) == (False, True)
    _assert_invariants(w, scan)


def test_checking_a_collided_footprint_unchecks_its_peer(qtbot):
    scan = _collision_scan()
    w = _make_widget(qtbot, scan)
    same_c, same_w = _lib(scan, SAME_FP_C), _lib(scan, SAME_FP_W)

    _fp_item(w, SAME_FP_W).setCheckState(0, Qt.CheckState.Checked)
    _fp_item(w, SAME_FP_C).setCheckState(0, Qt.CheckState.Checked)
    assert (same_c.selected, same_w.selected) == (True, False)
    _assert_invariants(w, scan)

    _fp_item(w, SAME_FP_W).setCheckState(0, Qt.CheckState.Checked)
    assert (same_c.selected, same_w.selected) == (False, True)
    _assert_invariants(w, scan)


def test_checking_group_header_selects_custom_same_and_unchecks_wurth_same(qtbot):
    scan = _collision_scan()
    w = _make_widget(qtbot, scan)
    same_c, same_w = _lib(scan, SAME_SYM_C), _lib(scan, SAME_SYM_W)

    _sym_item(w, SAME_SYM_W).setCheckState(0, Qt.CheckState.Checked)
    w._sym_tree.topLevelItem(0).setCheckState(0, Qt.CheckState.Checked)

    assert (same_c.selected, same_w.selected) == (True, False)
    _assert_invariants(w, scan)


def test_group_header_with_two_same_source_peers_selects_at_most_one(qtbot):
    a, b = "Custom/A/Same.kicad_sym", "Custom/B/Same.kicad_sym"
    scan = ScanResult(symbol_libs=[
        SymbolLibrary("Same", a, "Custom", collision_peers=[b]),
        SymbolLibrary("Same", b, "Custom", collision_peers=[a]),
    ])
    w = _make_widget(qtbot, scan)

    w._sym_tree.topLevelItem(0).setCheckState(0, Qt.CheckState.Checked)

    assert sum(lib.selected for lib in scan.symbol_libs) == 1
    _assert_invariants(w, scan)


def test_unchecking_a_symbol_leaves_a_collided_peer_alone(qtbot):
    scan = _collision_scan()
    w = _make_widget(qtbot, scan)

    _sym_item(w, SAME_SYM_C).setCheckState(0, Qt.CheckState.Checked)
    _sym_item(w, SAME_SYM_C).setCheckState(0, Qt.CheckState.Unchecked)

    assert not _lib(scan, SAME_SYM_C).selected
    assert not _lib(scan, SAME_SYM_W).selected
    _assert_invariants(w, scan)


def test_select_all_prefers_custom_for_collided_pairs(qtbot):
    scan = _collision_scan()
    w = _make_widget(qtbot, scan)

    w.select_all()

    assert _lib(scan, SAME_SYM_C).selected is True
    assert _lib(scan, SAME_SYM_W).selected is False
    assert _lib(scan, SAME_FP_C).selected is True
    assert _lib(scan, SAME_FP_W).selected is False
    # every non-collided library is selected
    for rel_path in (OWN_SYM_C, OWN_SYM_W, OWN_FP_C, OWN_FP_W):
        assert _lib(scan, rel_path).selected is True
    _assert_invariants(w, scan)


def test_select_all_twice_gives_the_same_selection(qtbot):
    scan = _collision_scan()
    w = _make_widget(qtbot, scan)

    w.select_all()
    first = [lib.selected for lib in [*scan.symbol_libs, *scan.footprint_libs]]
    w.select_all()
    second = [lib.selected for lib in [*scan.symbol_libs, *scan.footprint_libs]]

    assert first == second
    _assert_invariants(w, scan)


def test_select_all_ignores_a_previously_selected_wurth_peer(qtbot):
    scan = _collision_scan()
    w = _make_widget(qtbot, scan)

    _sym_item(w, SAME_SYM_W).setCheckState(0, Qt.CheckState.Checked)
    w.select_all()

    assert _lib(scan, SAME_SYM_C).selected is True
    assert _lib(scan, SAME_SYM_W).selected is False
    _assert_invariants(w, scan)


def test_deselect_all_clears_everything_after_select_all(qtbot):
    scan = _collision_scan()
    w = _make_widget(qtbot, scan)

    w.select_all()
    w.deselect_all()

    assert not any(lib.selected for lib in [*scan.symbol_libs, *scan.footprint_libs])
    _assert_invariants(w, scan)


def test_selected_wurth_symbol_does_not_check_wurth_footprint_when_custom_peer_selected(qtbot):
    scan = _collision_scan()
    w = _make_widget(qtbot, scan)

    # Custom 'Same' footprint is selected, then a Wurth symbol that references 'Same' is checked
    _fp_item(w, SAME_FP_C).setCheckState(0, Qt.CheckState.Checked)
    _sym_item(w, OWN_SYM_W).setCheckState(0, Qt.CheckState.Checked)

    assert _lib(scan, SAME_FP_C).selected is True
    assert _lib(scan, SAME_FP_W).selected is False
    assert _lib(scan, OWN_FP_W).selected is True
    _assert_invariants(w, scan)


def test_switching_collided_symbol_moves_its_footprint_too(qtbot):
    scan = _collision_scan()
    w = _make_widget(qtbot, scan)

    _sym_item(w, SAME_SYM_W).setCheckState(0, Qt.CheckState.Checked)
    assert _lib(scan, SAME_FP_W).selected is True
    _sym_item(w, SAME_SYM_C).setCheckState(0, Qt.CheckState.Checked)

    # Wurth symbol dropped, so the Wurth footprint is released and the Custom one taken
    assert _lib(scan, SAME_FP_W).selected is False
    assert _lib(scan, SAME_FP_C).selected is True
    _assert_invariants(w, scan)


def test_collision_handling_never_renames_a_library(qtbot):
    scan = _collision_scan()
    w = _make_widget(qtbot, scan)

    w.select_all()
    w.deselect_all()
    _sym_item(w, SAME_SYM_W).setCheckState(0, Qt.CheckState.Checked)

    assert [lib.nickname for lib in scan.symbol_libs] == ["Same", "Own_C", "Same", "Own_W"]
    assert [lib.nickname for lib in scan.footprint_libs] == ["Same", "Own_C", "Same", "Own_W"]
    _assert_invariants(w, scan)
