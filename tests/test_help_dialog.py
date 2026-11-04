"""Help dialog content tests (plan 05-08): import flow page, Collision status, shortcuts."""

import html as html_module
import re
import types
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractButton, QLabel, QPushButton, QTextBrowser, QTreeWidgetItem

from zipfixtures import footprint_library_for

from kicad_lib_manager.importer.commit_gate import AtomicFailure, GateResult
from kicad_lib_manager.importer.commit_plan import CommitFile, CommitPlan
from kicad_lib_manager.importer.commit_step import CommitProbe
from kicad_lib_manager.importer.plan import Conflict, InstallResult
from kicad_lib_manager.widgets import import_dialog
from kicad_lib_manager.widgets.commit_panel import _ADDED_MARK, _CHANGED_MARK, CommitPanel
from kicad_lib_manager.widgets.conflict_row import ConflictRow
from kicad_lib_manager.widgets.help_dialog import HELP_PAGES, TOC_STRUCTURE, HelpDialog
from kicad_lib_manager.widgets.import_result import ImportResultView
from kicad_lib_manager.widgets import conflict_row, help_dialog, theme
from kicad_lib_manager.widgets.conflict_row import _button_qss
from kicad_lib_manager.widgets.theme import (
    ACCENT, AMBER, DISPLAY_PT, ERROR, HEADING_PT, MONO_FAMILY, MONO_PT, SURFACE_BASE,
)

# The Atomic_ install target the stub results below name
LIBRARY = "Atomic_Analog"


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
        ("Ctrl+Shift+A", "Check Atomic Parts"),
    ):
        assert shortcut in page, shortcut
        assert action in page, action


def test_help_library_tree_explains_the_atomic_marks():
    raw = HELP_PAGES["library_tree"]
    page = _page_text("library_tree")
    assert "Atomic parts" in page
    for text in (
        "Atomic_", "amber", "tooltip", "New", "Changed", "last Custom commit",
        "double-click", "Ctrl+Shift+A", "Check Atomic Parts",
        "one row for each problem", "one row for each note", "problem row",
    ):
        assert text in page, text
    assert AMBER in raw and ACCENT in raw
    assert "ki_" not in page.casefold()
    assert "#CC7700" not in raw


def _page_text(key: str) -> str:
    """A help page as the reader sees it: tags removed, entities decoded, whitespace collapsed."""
    text = html_module.unescape(re.sub(r"<[^>]+>", "", HELP_PAGES[key]))
    return re.sub(r"\s+", " ", text)


def test_help_import_page_matches_finished_flow(qtbot, tmp_path):
    page = _page_text("importing")

    # every resolution button a real conflict row shows is named on the page
    row = ConflictRow(Conflict(
        key=f"footprint:{footprint_library_for(LIBRARY)}:fp", kind="footprint", name="FP",
        existing=f"{footprint_library_for(LIBRARY)}.pretty already holds a different FP.kicad_mod", suggested_name="FP_1",
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
        ok=True, library=LIBRARY, new_library=False,
        touched=(tmp_path / "Custom" / "Symbols" / f"{LIBRARY}.kicad_sym", tmp_path / "Custom" / "3DModels" / "x.stp"),
        issues=(), backup_dir=tmp_path / "bk",
    )
    view.show_result(result, types.SimpleNamespace(symbol_name="X", library=LIBRARY), tmp_path)
    shown = [w.text() for w in view.findChildren(QLabel)] + [w.text() for w in view.findChildren(QPushButton)]
    for label in ("Warnings", "Library list", "Library tables", "Files written", "Backup folder", "Open folder"):
        assert any(text.startswith(label) for text in shown), f"the view no longer shows {label!r}"
        assert label in page, label


def _section(heading: str) -> str:
    """One h3 section of the importing page as the reader sees it."""
    raw = HELP_PAGES["importing"]
    start = raw.index(f"<h3>{heading}</h3>")
    end = raw.find("<h3>", start + 1)
    text = html_module.unescape(re.sub(r"<[^>]+>", "", raw[start:end if end != -1 else len(raw)]))
    return re.sub(r"\s+", " ", text)


def test_help_names_the_cancel_button():
    section = _section("Install and result").casefold()
    for claim in ("cancel", "without installing", "greyed out", "cannot be closed or cancelled", "press cancel to stay"):
        assert claim in section, claim


def test_help_names_the_start_page_cancel():
    section = _section("Start").casefold()
    for claim in ("cancel", "bottom right", "without importing", "nothing is written"):
        assert claim in section, claim


def test_help_says_the_window_fits_the_screen():
    section = _section("Start")
    for claim in ("opens small", "grows", "fit your screen"):
        assert claim in section, claim


def test_help_names_choose_another_package():
    label = import_dialog.CHANGE_PACKAGE_TEXT
    assert label == "Choose another package..."
    for heading in ("Start", "Install and result"):
        assert label in _section(heading), heading
    page = _page_text("importing")
    assert "CHANGE_PACKAGE_TEXT" not in page
    assert "Change..." not in page


def test_help_import_page_describes_add_model():
    page = _page_text("importing")
    assert import_dialog.ADD_MODEL_TEXT in page
    for text in (".zip", ".step", ".stp", ".wrl"):
        assert text in page, text
    items = _section("Items")
    assert "SnapEDA" in items
    assert import_dialog.ADD_MODEL_TEXT in items


def test_help_import_page_describes_rejected_model():
    items = _section("Items")
    assert import_dialog.REMOVE_MODEL_TEXT in items
    assert "red" in items
    assert "Install Part stays blocked" in items
    assert import_dialog.ADD_MODEL_TEXT in items


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


def test_help_describes_phase_12_behaviour():
    generating = _page_text("generating").lower()
    for claim in (
        "checks whether kicad is open", "retry", "change anyway", "not now", "only these two paths",
        "empty destination",
    ):
        assert claim in generating, claim

    importing = _page_text("importing").lower()
    for claim in (
        import_dialog.FINISHING_TEXT.lower(), "press cancel to stay",
        "points at a library that no longer exists", "added by hand", "empty destination",
        "install part waits", "the kicad command-line tool is slow to respond",
    ):
        assert claim in importing, claim

    # the new sentences stay in plain words: no raw field names, program names or file names (owner preference)
    for key in ("generating", "importing"):
        text = _page_text(key).casefold()
        assert "ki_" not in text, key
        assert "kicad-cli" not in text, key
        assert "kicad_common" not in text, key


def _panel_texts(panel) -> list[str]:
    return [w.text() for w in panel.findChildren(QLabel)] + [w.text() for w in panel.findChildren(QAbstractButton)]


def _commit_plan(tmp_path) -> CommitPlan:
    """A small CommitPlan, in the shape of make_cplan in tests/test_commit_panel.py."""
    rels = (
        (f"Symbols/{LIBRARY}.kicad_sym", "symbol"),
        (f"Footprints/{footprint_library_for(LIBRARY)}.pretty/FP_X.kicad_mod", "footprint"),
        ("3DModels/x.step", "model"),
    )
    files = tuple(
        CommitFile(rel, f"Custom/{rel}", tmp_path / "Custom" / rel, kind, "0" * 64, None) for rel, kind in rels
    )
    return CommitPlan(
        repo_root=tmp_path, custom_dir=tmp_path / "Custom", custom_rel="Custom", files=files,
        library=LIBRARY, new_library=False, symbol="PartX", footprint=f"{footprint_library_for(LIBRARY)}:FP_X", model="x.step",
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

    # the atomic refusal and its recovery: the page uses the words of a gated panel's buttons
    panel.apply_probe(CommitProbe(
        state="gated", reason="1 part breaks the atomic rule.", branch="main", parent_dir=tmp_path,
        gate=GateResult(blocking=(AtomicFailure(LIBRARY, f"Custom/Symbols/{LIBRARY}.kicad_sym", "P1", "mpn", "no MPN"),)),
    ))
    assert panel.state() == "gated"
    gated_buttons = [w.text() for w in panel.findChildren(QPushButton)]
    for label in ("Check again", "Open Check Atomic Parts…"):
        assert label in gated_buttons, f"the gated panel no longer shows {label!r}"
        assert label in page, label
    assert "atomic rule" in page
    assert _CHANGED_MARK in page and _ADDED_MARK in page

    # the section sits right after "Install and result" and before "Library tables"
    raw = HELP_PAGES["importing"]
    assert raw.index("<h3>Install and result</h3>") < raw.index("<h3>Commit</h3>") < raw.index("<h3>Library tables</h3>")

    lowered = page.lower()
    for claim in ("never pushed", "hooks", "detached", "uncommitted"):
        assert claim in lowered, claim

    # Commit and Switch to main keep the window open; the first check does not (IN-02)
    assert "cannot be closed" in page
    assert "while the first check runs" in page
    assert "While git runs" not in page

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


def test_help_import_page_sections_follow_the_flow():
    raw = HELP_PAGES["importing"]
    order = ["Items", "Target library", "Footprint", "Fields", "Atomic check", "Conflicts", "Install and result"]
    positions = [raw.index(f"<h3>{name}</h3>") for name in order]
    assert positions == sorted(positions)
    for name in order:
        assert raw.count(f"<h3>{name}</h3>") == 1, name


def test_help_import_page_explains_the_atomic_scheme():
    page = _page_text("importing")
    target = _section("Target library")
    for text in ("Atomic_Transistor_FET", "Atomic_", "tooltip", "similar parts", "Atomic_TI", "letter case", ".kicad_sym"):
        assert text in target, text
    assert "Atomic_Footprints" in page
    footprint = _section("Footprint")
    for text in (
        "Atomic_Footprints", import_dialog.OFFICIAL_FOOTPRINT_TEXT, import_dialog.VENDOR_FOOTPRINT_TEXT,
        "official KiCad footprint", "Not used", "never changed", "Overwrite", "Rename", "Skip", "reused",
    ):
        assert text in footprint, text
    assert "official KiCad footprint" in page
    items = _section("Items")
    assert "Not used" in items and "only the one you pick" in items


def test_help_import_page_explains_fields_and_the_install_gate():
    fields = _section("Fields")
    for text in ("Value always equals the MPN", "Texas Instruments", "Regenerate", "Keywords", "Footprint description",
                 "Footprint tags", "MPN cannot be empty", "required", "Datasheet", "Description", "Manufacturer"):
        assert text in fields, text
    assert "blank" not in fields.casefold()  # the three fields are required, never written blank
    gate = _section("Atomic check")
    for text in ("Install Part", "blocked", "MPN", "Manufacturer", "Datasheet", "Description", "3D model", "Click a problem",
                 import_dialog.ADD_MODEL_TEXT, "official KiCad footprint"):
        assert text in gate, text


def test_help_import_page_uses_plain_words():
    raw = HELP_PAGES["importing"]
    page = _page_text("importing")
    for banned in ("SubCategory", "Make linked", "ki_", "install.atomic", "<Type>"):
        assert banned not in page, banned
    assert "ki_" not in raw
    # the old generic-word rule is gone: no sentence about name parts
    assert "generic words" not in page


def test_help_css_uses_theme_tokens_only():
    css = help_dialog.CSS
    colours = {v.upper() for k, v in vars(theme).items() if k.isupper() and isinstance(v, str) and v.startswith("#")}
    found = re.findall(r"#[0-9A-Fa-f]{3,8}\b", css)
    assert found, "the stylesheet no longer carries any colour"
    for literal in found:
        assert literal.upper() in colours, literal
    assert re.search(r"font-size:\s*\d+px", css) is None
    for text in (f"{DISPLAY_PT}pt", f"{HEADING_PT}pt", f"{MONO_PT}pt", MONO_FAMILY):
        assert text in css, text
    assert "border-radius" not in css
    # the source holds no colour literal either: the stylesheet is built from the constants
    source = Path(help_dialog.__file__).read_text(encoding="utf-8")
    assert re.findall(r"#[0-9A-Fa-f]{3,8}\b", source) == []


def test_help_headings_keep_their_sizes(qtbot):
    browser = QTextBrowser()
    qtbot.addWidget(browser)
    browser.setHtml(HELP_PAGES["importing"])

    def first_size(level: int) -> float:
        block = browser.document().firstBlock()
        while block.isValid():
            if block.blockFormat().headingLevel() == level:
                return next(iter(block)).fragment().charFormat().fontPointSize()
            block = block.next()
        raise AssertionError(f"no level {level} heading on the page")

    assert first_size(2) == DISPLAY_PT
    assert first_size(3) == HEADING_PT
    mono = set()
    block = browser.document().firstBlock()
    while block.isValid():
        for fragment in block:
            fmt = fragment.fragment().charFormat()
            if MONO_FAMILY in fmt.fontFamilies():
                mono.add(fmt.fontPointSize())
        block = block.next()
    assert mono, "no code or pre text on the page"
    assert mono == {float(MONO_PT)}


def test_conflict_row_styles_use_theme_tokens():
    text = Path(conflict_row.__file__).read_text(encoding="utf-8")
    assert re.findall(r"#[0-9A-Fa-f]{3,8}\b", text) == []
    qss = _button_qss(ERROR)
    assert f"background-color: {SURFACE_BASE}" in qss
    assert f"color: {SURFACE_BASE}" in qss
    assert re.fullmatch(r"#FFFFFF", theme.SURFACE_BASE)


def test_help_dialog_opens_on_a_given_topic(qtbot):
    dialog = HelpDialog(topic="importing")
    qtbot.addWidget(dialog)
    assert dialog._toc.currentItem().data(0, Qt.ItemDataRole.UserRole) == "importing"
    assert "Importing Parts" in dialog._browser.toPlainText()

    # no topic: the first topic, as before
    default = HelpDialog()
    qtbot.addWidget(default)
    assert default._toc.currentItem() is default._toc.topLevelItem(0)
    assert default._toc.currentItem().data(0, Qt.ItemDataRole.UserRole) == "overview"
    assert "Overview" in default._browser.toPlainText()

    # an unknown key raises nothing and opens on Overview
    unknown = HelpDialog(topic="no_such_page")
    qtbot.addWidget(unknown)
    assert unknown._toc.currentItem().data(0, Qt.ItemDataRole.UserRole) == "overview"

    # an open dialog moves to another topic, or stays put when the key is unknown
    assert dialog.show_topic("shortcuts") is True
    assert dialog._toc.currentItem().data(0, Qt.ItemDataRole.UserRole) == "shortcuts"
    assert "Keyboard Shortcuts" in dialog._browser.toPlainText()
    before = dialog._toc.currentItem()
    assert dialog.show_topic("no_such_page") is False
    assert dialog._toc.currentItem() is before


def test_help_names_the_toolbar_help():
    start = _section("Start")
    for text in ("toolbar", import_dialog.HELP_ACTION_TEXT, "F1", "every step", "stays open"):
        assert text in start, text
    shortcuts = _page_text("shortcuts")
    for text in ("F1", "User Guide", "import window", "Importing Parts", "toolbar"):
        assert text in shortcuts, text
    for key in ("importing", "shortcuts"):
        assert "HELP_ACTION_TEXT" not in _page_text(key)
        assert "HELP_ACTION_TEXT" not in HELP_PAGES[key]
