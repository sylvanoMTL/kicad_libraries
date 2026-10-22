"""Help dialog content tests (plan 05-08): import flow page, Collision status, shortcuts."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem

from kicad_lib_manager.widgets.help_dialog import HELP_PAGES, TOC_STRUCTURE, HelpDialog
from kicad_lib_manager.widgets.theme import AMBER


def _find_item(dialog: HelpDialog, key: str) -> QTreeWidgetItem:
    stack = [dialog._toc.topLevelItem(i) for i in range(dialog._toc.topLevelItemCount())]
    while stack:
        item = stack.pop()
        if item.data(0, Qt.ItemDataRole.UserRole) == key:
            return item
        stack.extend(item.child(i) for i in range(item.childCount()))
    raise AssertionError(f"no TOC item for {key}")


def test_help_import_page():
    page = HELP_PAGES["importing"]
    for text in (
        "Importing Parts", "Import Part...", "Ctrl+I", "Install Part",
        "Overwrite", "Rename", "Skip", "sym-lib-table", "fp-lib-table",
    ):
        assert text in page, text
    assert "zip" in page and "folder" in page
    assert "without changing" in page  # add-only table update
    how_to_use = next(children for key, _label, children in TOC_STRUCTURE if key == "_how_to_use")
    assert ("importing", "Importing Parts") in how_to_use
    assert how_to_use.index(("importing", "Importing Parts")) > how_to_use.index(
        ("generating", "Generating Tables")
    )


def test_help_library_tree_collision_and_amber():
    page = HELP_PAGES["library_tree"]
    assert "Collision" in page
    assert AMBER in page
    assert "#CC7700" not in page


def test_help_shortcuts_complete():
    page = HELP_PAGES["shortcuts"]
    for shortcut, action in (
        ("Ctrl+I", "Import Part"), ("Ctrl+Shift+R", "Rescan Libraries"),
        ("Ctrl+G", "Generate Tables"), ("Ctrl+R", "Restore Backup"),
        ("Ctrl+K", "Set KiCad Footprint Path"), ("Ctrl+Q", "Exit"), ("F1", "User Guide"),
    ):
        assert shortcut in page, shortcut
        assert action in page, action


def test_help_dialog_opens_importing_page(qtbot):
    dialog = HelpDialog()
    qtbot.addWidget(dialog)
    dialog._toc.setCurrentItem(_find_item(dialog, "importing"))
    assert "Importing Parts" in dialog._browser.toPlainText()
    assert "Install Part" in dialog._browser.toPlainText()
