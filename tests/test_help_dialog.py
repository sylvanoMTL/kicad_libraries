"""Help dialog content tests (plan 05-08): import flow page, Collision status, shortcuts."""

import html as html_module
import re
import types

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QTreeWidgetItem

from kicad_lib_manager.importer.plan import Conflict, InstallResult
from kicad_lib_manager.widgets.conflict_row import ConflictRow
from kicad_lib_manager.widgets.help_dialog import HELP_PAGES, TOC_STRUCTURE, HelpDialog
from kicad_lib_manager.widgets.import_result import ImportResultView
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


def _page_text(key: str) -> str:
    """A help page as the reader sees it: tags removed, entities decoded, whitespace collapsed."""
    text = html_module.unescape(re.sub(r"<[^>]+>", "", HELP_PAGES[key]))
    return re.sub(r"\s+", " ", text)


def test_help_import_page_matches_finished_flow(qtbot, tmp_path):
    page = _page_text("importing")

    # every resolution button a real conflict row shows is named on the page
    row = ConflictRow(Conflict(
        key="footprint:IC_Test_TI:fp", kind="footprint", name="FP",
        existing="IC_Test_TI.pretty already holds a different FP.kicad_mod", suggested_name="FP_1",
    ))
    qtbot.addWidget(row)
    buttons = [b.text() for b in row.findChildren(QPushButton) if b.isCheckable()]
    assert sorted(buttons) == ["Overwrite", "Rename", "Skip"]
    for text in buttons:
        assert text in page, text

    # every section label a real Result view shows is named on the page
    view = ImportResultView()
    qtbot.addWidget(view)
    result = InstallResult(
        ok=True, library="IC_Test_TI", new_library=False,
        touched=(tmp_path / "Custom" / "Symbols" / "IC_Test_TI.kicad_sym", tmp_path / "Custom" / "3DModels" / "x.stp"),
        issues=(), backup_dir=tmp_path / "bk",
    )
    view.show_result(result, types.SimpleNamespace(symbol_name="X", library="IC_Test_TI"), tmp_path)
    shown = [w.text() for w in view.findChildren(QLabel)] + [w.text() for w in view.findChildren(QPushButton)]
    for label in ("Warnings", "Library list", "Library tables", "Files written", "Backup folder", "Open folder"):
        assert any(text.startswith(label) for text in shown), f"the view no longer shows {label!r}"
        assert label in page, label


def test_help_import_page_failure_and_tables_claims():
    page = _page_text("importing").lower()
    for claim in (
        "every file is restored",  # a failed install
        "click install part again",
        "there is no overwrite-all",
        "reopen kicad's symbol and footprint editors",
        "no warnings",
        "is added to sym-lib-table and fp-lib-table",
        "missing from the tables shows a hint to press generate tables",
        "cannot be closed or cancelled",
        "keeps a backup of the replaced file",
    ):
        assert claim in page, claim


def test_help_dialog_opens_importing_page(qtbot):
    dialog = HelpDialog()
    qtbot.addWidget(dialog)
    dialog._toc.setCurrentItem(_find_item(dialog, "importing"))
    assert "Importing Parts" in dialog._browser.toPlainText()
    assert "Install Part" in dialog._browser.toPlainText()
