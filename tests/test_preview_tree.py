"""PreviewTree rendering (plan 05-06, D-07): colours, glyphs, Heading headers, stable rebuilds, copy, activation."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication, QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractItemView

from kicad_lib_manager.importer.preview import PreviewRow, PreviewSection
from kicad_lib_manager.widgets import theme
from kicad_lib_manager.widgets.preview_tree import PreviewTree


def _file(text, detail, glyph, tone):
    return PreviewRow(text=text, detail=detail, glyph=glyph, tone=tone, kind="file")


def _sections():
    files = PreviewSection("Files", (
        _file("+ Custom/3DModels/A.stp", "new, 1.0 KiB", "+", "success"),
        _file("~ Custom/Symbols/L.kicad_sym", "modified", "~", "default"),
        _file("= Custom/Footprints/L.pretty/FP.kicad_mod", "unchanged", "=", "muted"),
    ))
    issues = PreviewSection("Issues", (
        PreviewRow(text="✖ bad", glyph="✖", tone="error", kind="issue"),
        PreviewRow(text="⚠ careful", glyph="⚠", tone="warning", kind="issue"),
    ))
    return (files, issues)


def _many(name, count):
    return PreviewSection(name, tuple(
        PreviewRow(text=f"+ row {i}", detail="new", glyph="+", tone="success", kind="file") for i in range(count)
    ))


@pytest.fixture
def tree(qtbot):
    widget = PreviewTree()
    qtbot.addWidget(widget)
    return widget


def _child(tree, section, index):
    return tree.topLevelItem(section).child(index)


def _color(item, column=0):
    return item.foreground(column).color().name().upper()


def test_render_headers_and_tones(tree):
    tree.render(_sections())
    assert [tree.topLevelItem(i).text(0) for i in range(tree.topLevelItemCount())] == ["Files (3)", "Issues (2)"]

    for i in range(tree.topLevelItemCount()):
        header = tree.topLevelItem(i)
        for column in (0, 1):
            assert header.background(column).color().name().upper() == QColor(theme.SURFACE_HEADER).name().upper()
        assert header.font(0).bold()
        assert header.font(0).pointSize() == theme.HEADING_PT

    new, modified, same = (_child(tree, 0, i) for i in range(3))
    assert _color(new) == theme.SUCCESS and new.font(0).bold()
    assert modified.font(0).bold()
    assert _color(same) == theme.MUTED and not same.font(0).bold()
    error, warning = (_child(tree, 1, i) for i in range(2))
    assert _color(error) == theme.ERROR
    assert _color(warning) == theme.AMBER
    # Plain text: markup in a vendor name is never interpreted
    assert new.text(0) == "+ Custom/3DModels/A.stp" and new.text(1) == "new, 1.0 KiB"


def test_conflict_choice_is_amber_bold_in_the_detail_column(tree):
    conflicts = PreviewSection("Conflicts", (
        PreviewRow(text="footprint FP", detail="Needs a choice", tone="warning", kind="conflict", key="k"),
        PreviewRow(text="symbol S", detail="Overwrite", kind="conflict", key="s"),
    ))
    tree.render((conflicts,))
    open_row, settled = _child(tree, 0, 0), _child(tree, 0, 1)
    assert _color(open_row, 1) == theme.AMBER and open_row.font(1).bold()
    assert not settled.font(1).bold()


def test_rewrite_detail_is_monospace(tree):
    rewrites = PreviewSection("Path rewrites", (
        PreviewRow(text="Footprint", detail="(none) → L:FP", kind="rewrite"),
    ))
    tree.render((rewrites,))
    item = _child(tree, 0, 0)
    assert item.font(1).family() == theme.MONO_FAMILY
    assert item.font(0).family() != theme.MONO_FAMILY


def test_render_restores_expand_and_scroll(qtbot, tree):
    tree.resize(520, 240)
    tree.show()
    qtbot.waitExposed(tree)
    tree.render((_many("Files", 120), _many("Issues", 40)))
    tree.topLevelItem(1).setExpanded(False)
    bar = tree.verticalScrollBar()
    assert bar.maximum() > 60
    bar.setValue(60)

    tree.render((_many("Files", 120), _many("Conflicts", 3), _many("Issues", 40)))
    assert tree.topLevelItem(0).isExpanded()
    assert tree.topLevelItem(1).text(0) == "Conflicts (3)" and tree.topLevelItem(1).isExpanded()
    assert not tree.topLevelItem(2).isExpanded()
    assert bar.value() == 60

    # A shorter tree clamps the restored value to the new maximum
    tree.render((_many("Files", 2),))
    assert bar.value() <= bar.maximum()


def test_tree_no_horizontal_scroll_and_elide(tree):
    tree.render(_sections())
    assert tree.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert tree.textElideMode() == Qt.TextElideMode.ElideMiddle
    assert tree.alternatingRowColors()
    assert tree.wordWrap()
    assert [tree.headerItem().text(i) for i in range(2)] == ["Item", "Detail"]
    for section in range(tree.topLevelItemCount()):
        for index in range(tree.topLevelItem(section).childCount()):
            row = _child(tree, section, index)
            assert row.toolTip(0) == row.text(0)
            assert row.toolTip(1) == row.text(1)


def test_ctrl_c_copies_row(tree):
    tree.render(_sections())
    tree.show()
    row = _child(tree, 0, 0)
    tree.setCurrentItem(row)
    QGuiApplication.clipboard().setText("")
    QTest.keySequence(tree, QKeySequence(QKeySequence.StandardKey.Copy))
    assert QGuiApplication.clipboard().text() == "+ Custom/3DModels/A.stp\tnew, 1.0 KiB"


def test_row_activated_on_double_click_and_enter(tree):
    tree.render(_sections())
    tree.show()
    seen = []
    tree.row_activated.connect(seen.append)

    row = _child(tree, 0, 1)
    tree.itemDoubleClicked.emit(row, 0)
    assert len(seen) == 1 and seen[0].text == "~ Custom/Symbols/L.kicad_sym"

    tree.itemDoubleClicked.emit(tree.topLevelItem(0), 0)
    assert len(seen) == 1

    seen.clear()
    tree.setCurrentItem(_child(tree, 1, 0))
    QTest.keyClick(tree, Qt.Key.Key_Return)
    assert [r.text for r in seen] == ["✖ bad"]

    seen.clear()
    tree.setCurrentItem(tree.topLevelItem(1))
    QTest.keyClick(tree, Qt.Key.Key_Return)
    assert seen == []


def test_tree_rows_are_not_editable(tree):
    tree.render(_sections())
    assert tree.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
