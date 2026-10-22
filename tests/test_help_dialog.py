"""Help dialog content tests (plan 05-08): import flow page, Collision status, shortcuts."""

import html as html_module
import re
import types

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractButton, QLabel, QPushButton, QTreeWidgetItem

from kicad_lib_manager.importer.commit_plan import CommitFile, CommitPlan
from kicad_lib_manager.importer.commit_step import CommitProbe
from kicad_lib_manager.importer.plan import Conflict, InstallResult
from kicad_lib_manager.widgets.commit_panel import CommitPanel
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


def _panel_texts(panel) -> list[str]:
    return [w.text() for w in panel.findChildren(QLabel)] + [w.text() for w in panel.findChildren(QAbstractButton)]


def _commit_plan(tmp_path) -> CommitPlan:
    """A small CommitPlan, in the shape of make_cplan in tests/test_commit_panel.py."""
    rels = (
        ("Symbols/IC_Test.kicad_sym", "symbol"),
        ("Footprints/IC_Test.pretty/FP_X.kicad_mod", "footprint"),
        ("3DModels/x.step", "model"),
    )
    files = tuple(
        CommitFile(rel, f"Custom/{rel}", tmp_path / "Custom" / rel, kind, "0" * 64, None) for rel, kind in rels
    )
    return CommitPlan(
        repo_root=tmp_path, custom_dir=tmp_path / "Custom", custom_rel="Custom", files=files,
        library="IC_Test", new_library=False, symbol="PartX", footprint="IC_Test:FP_X", model="x.step",
        vendor="Ultra Librarian", package="x.zip", date="2026-01-02", overwrite=False, backup_dir=None,
        issues=(),
    )


def test_help_import_page_describes_commit_step(qtbot, tmp_path):
    page = _page_text("importing")

    # the labels a real panel shows, in the ready state and in the offer-to-switch state, are on the page
    panel = CommitPanel()
    qtbot.addWidget(panel)
    panel.show_plan(_commit_plan(tmp_path))
    panel.apply_probe(CommitProbe(
        state="ready", branch="main", head="abc1234def5678", parent_ok=True, parent_branch="main",
        gitlink_old="1111111aaaa", parent_dir=tmp_path,
    ))
    ready_texts = _panel_texts(panel)
    panel.apply_probe(CommitProbe(
        state="offer_switch", head="abc1234def",
        reason="Custom is on a detached HEAD at abc1234 that is on main's history.",
    ))
    offer_texts = _panel_texts(panel)
    shown = ready_texts + offer_texts
    for label in ("Files to commit", "Also commit the Custom ref in the parent repo", "Switch to main"):
        assert any(text.startswith(label) for text in shown), f"the panel no longer shows {label!r}"
        assert label in page, label
    assert panel.commit_button.text() == "Commit"
    assert "<b>Commit</b>" in HELP_PAGES["importing"]  # the button, named as a button
    assert "<h3>Commit</h3>" in HELP_PAGES["importing"]

    # the section sits right after "Install and result" and before "Library tables"
    raw = HELP_PAGES["importing"]
    assert raw.index("<h3>Install and result</h3>") < raw.index("<h3>Commit</h3>") < raw.index("<h3>Library tables</h3>")

    lowered = page.lower()
    for claim in ("never pushed", "hooks", "detached", "uncommitted"):
        assert claim in lowered, claim

    # static text: no formatted vendor, user or path value (T-06-25)
    section = raw[raw.index("<h3>Commit</h3>"):raw.index("<h3>Library tables</h3>")]
    assert "{" not in section and "%s" not in section
    assert str(tmp_path) not in section and "Ultra Librarian" not in section


def test_help_dialog_opens_importing_page(qtbot):
    dialog = HelpDialog()
    qtbot.addWidget(dialog)
    dialog._toc.setCurrentItem(_find_item(dialog, "importing"))
    assert "Importing Parts" in dialog._browser.toPlainText()
    assert "Install Part" in dialog._browser.toPlainText()
