"""Help dialog content tests (plan 05-08): import flow page, Collision status, shortcuts."""

import html as html_module
import re
import types
from pathlib import Path

import pytest
import shiboken6

from PySide6.QtCore import QRect, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QAbstractButton, QDialogButtonBox, QLabel, QPushButton, QTextBrowser, QTreeWidgetItem, QWidget,
)

from zipfixtures import footprint_library_for

from kicad_lib_manager import settings
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


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    """The guide now saves the owner's place; no test here may write the real settings.ini (T-12-50)."""
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path / "qsettings"),
    )
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


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
    for claim in (
        "cancel", "next to", "browse zip...", "browse folder...", "without importing", "nothing is written",
        "bottom right", "install part",
    ):
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


@pytest.mark.parametrize("rendered", [False, True], ids=["raw_page", "rendered_page"])
def test_help_headings_keep_their_sizes(qtbot, rendered):
    browser = QTextBrowser()
    qtbot.addWidget(browser)
    browser.setHtml(help_dialog.render_page("importing") if rendered else HELP_PAGES["importing"])

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

    # no topic and nothing saved: Overview, the first topic
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

    # a page key still selects the page item, and a section key opens its page at that heading (plan 12-14)
    assert dialog.show_topic("importing") is True
    assert dialog._toc.currentItem().data(0, Qt.ItemDataRole.UserRole) == "importing"
    sectioned = HelpDialog(topic="importing#conflicts")
    qtbot.addWidget(sectioned)
    assert sectioned._toc.currentItem().data(0, Qt.ItemDataRole.UserRole) == "importing#conflicts"
    assert _headings(sectioned._browser, 2)[0][1] == "4.4 Importing Parts"
    sectioned.show()
    qtbot.waitExposed(sectioned)
    qtbot.waitUntil(lambda: _heading_is_in_view(sectioned._browser, "4.4.7 Conflicts"), timeout=5000)
    assert sectioned._browser.verticalScrollBar().value() > 0


def test_help_names_the_toolbar_help():
    start = _section("Start")
    for text in (
        "toolbar", import_dialog.HELP_ACTION_TEXT, "F1", "every step", "stays open",
        "its own window", "beside the main window", "when the import window closes",
    ):
        assert text in start, text
    shortcuts = _page_text("shortcuts")
    for text in ("F1", "User Guide", "import window", "Importing Parts", "toolbar", "its own window"):
        assert text in shortcuts, text
    for key in ("importing", "shortcuts"):
        assert "HELP_ACTION_TEXT" not in _page_text(key)
        assert "HELP_ACTION_TEXT" not in HELP_PAGES[key]


# -- Numbered menu with the pages' sections (plan 12-14, G-12-11) ---------------------------------------------

MENU_NUMBERS = {
    "overview": "1", "_getting_started": "2", "requirements": "2.1", "how_to_run": "2.2",
    "_on_launch": "3", "kicad_detection": "3.1", "repo_scan": "3.2",
    "_how_to_use": "4", "library_tree": "4.1", "selecting": "4.2", "generating": "4.3", "importing": "4.4",
    "restoring": "4.5", "filter": "5", "shortcuts": "6", "roadmap": "7",
}
IMPORTING_SECTIONS = [
    "Start", "Items", "Target library", "Footprint", "Fields", "Atomic check", "Conflicts",
    "Install and result", "Commit", "Library tables",
]


def _headings(browser: QTextBrowser, level: int) -> list[tuple]:
    """(block, text) of every heading block of this level on the shown page, in page order."""
    found = []
    block = browser.document().firstBlock()
    while block.isValid():
        if block.blockFormat().headingLevel() == level:
            found.append((block, block.text()))
        block = block.next()
    return found


def _heading_is_in_view(browser: QTextBrowser, text: str) -> bool:
    for block, shown in _headings(browser, 3):
        if shown == text:
            top = browser.document().documentLayout().blockBoundingRect(block).top() - browser.verticalScrollBar().value()
            return -1 < top < browser.viewport().height()  # the scroll value is whole pixels, the heading top is not
    return False


def _page_items(dialog: HelpDialog) -> list[QTreeWidgetItem]:
    """Every menu item that shows a whole page, in menu order."""
    items, stack = [], [dialog._toc.topLevelItem(i) for i in range(dialog._toc.topLevelItemCount())]
    while stack:
        item = stack.pop(0)
        if item.data(0, Qt.ItemDataRole.UserRole) in HELP_PAGES:
            items.append(item)
        for i in range(item.childCount()):
            if "#" not in item.child(i).data(0, Qt.ItemDataRole.UserRole):
                stack.append(item.child(i))
    return items


def _click_row(dialog: HelpDialog, item: QTreeWidgetItem) -> None:
    toc = dialog._toc
    toc.scrollToItem(item)
    QTest.mouseClick(toc.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, toc.visualItemRect(item).center())


def _current_key(dialog: HelpDialog) -> str:
    return dialog._toc.currentItem().data(0, Qt.ItemDataRole.UserRole)


def test_section_anchor_keeps_only_letters_digits_and_single_hyphens():
    assert help_dialog.section_anchor("Install and result") == "install-and-result"
    assert help_dialog.section_anchor("  Per-source scoping! ") == "per-source-scoping"
    assert help_dialog.section_anchor("Atomic  check") == "atomic-check"
    assert help_dialog.page_sections("filter") == [("how-it-works", "How it works"), ("per-source-scoping", "Per-source scoping")]


def test_help_outline_numbers_follow_the_menu_order():
    outline = help_dialog.help_outline()
    numbers = {entry.key: entry.number for entry in outline}
    assert {key: numbers[key] for key in MENU_NUMBERS} == MENU_NUMBERS
    importing = [entry for entry in outline if entry.parent == "importing"]
    assert [entry.text for entry in importing] == [f"4.4.{i} {name}" for i, name in enumerate(IMPORTING_SECTIONS, 1)]
    assert numbers["importing#conflicts"] == "4.4.7"
    assert [entry.text for entry in outline if entry.parent == "filter"] == ["5.1 How it works", "5.2 Per-source scoping"]
    assert sum(1 for entry in outline if entry.anchor is not None) == 20
    first = outline[0]
    assert (first.key, first.text, first.parent, first.page, first.anchor) == ("overview", "1 Overview", None, "overview", None)
    group = next(entry for entry in outline if entry.key == "_how_to_use")
    assert group.text == "4 How to Use" and group.page is None


def test_every_page_heading_is_in_the_menu_under_its_page(qtbot):
    dialog = HelpDialog()
    qtbot.addWidget(dialog)
    outline_keys = [entry.key for entry in help_dialog.help_outline()]
    for key, raw in HELP_PAGES.items():
        assert outline_keys.count(key) == 1, key
        item = _find_item(dialog, key)
        number = item.text(0).split(" ", 1)[0]
        labels = re.findall(r"<h3>(.*?)</h3>", raw, re.S)
        assert raw.count("<h3") == len(labels), f"{key} has an h3 that is not a bare <h3> tag"
        assert [item.child(i).text(0) for i in range(item.childCount())] == [
            f"{number}.{n} {html_module.unescape(label)}" for n, label in enumerate(labels, 1)
        ]
        anchors = []
        for i in range(item.childCount()):
            page_key, _, anchor = item.child(i).data(0, Qt.ItemDataRole.UserRole).partition("#")
            assert page_key == key
            assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", anchor), anchor
            anchors.append(anchor)
        assert len(set(anchors)) == len(anchors), key


def test_page_headings_carry_the_menu_numbers(qtbot):
    dialog = HelpDialog()
    qtbot.addWidget(dialog)
    for item in _page_items(dialog):
        dialog._toc.setCurrentItem(item)
        assert _headings(dialog._browser, 2)[0][1] == item.text(0)
        assert [text for _block, text in _headings(dialog._browser, 3)] == [item.child(i).text(0) for i in range(item.childCount())]


def test_clicking_a_section_scrolls_to_its_heading(qtbot):
    dialog = HelpDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    browser = dialog._browser
    for page in _page_items(dialog):
        for i in range(page.childCount()):
            section = page.child(i)
            dialog._toc.setCurrentItem(section)
            assert _headings(browser, 2)[0][1] == page.text(0)
            qtbot.waitUntil(lambda: _heading_is_in_view(browser, section.text(0)), timeout=5000)
    dialog.show_topic("importing#conflicts")
    qtbot.waitUntil(lambda: browser.verticalScrollBar().value() > 0, timeout=5000)
    assert _heading_is_in_view(browser, "4.4.7 Conflicts")

    _click_row(dialog, _find_item(dialog, "importing#commit"))
    qtbot.waitUntil(lambda: _current_key(dialog) == "importing#commit", timeout=5000)
    qtbot.waitUntil(lambda: _heading_is_in_view(browser, "4.4.9 Commit"), timeout=5000)


def test_menu_expands_the_shown_page_only(qtbot):
    dialog = HelpDialog(topic="importing")
    qtbot.addWidget(dialog)
    paged = ("importing", "generating", "library_tree", "kicad_detection", "filter")
    groups = ("_getting_started", "_on_launch", "_how_to_use")

    def expanded() -> dict[str, bool]:
        return {key: _find_item(dialog, key).isExpanded() for key in paged}

    assert expanded() == {"importing": True, "generating": False, "library_tree": False, "kicad_detection": False, "filter": False}
    assert all(_find_item(dialog, key).isExpanded() for key in groups)

    assert dialog.show_topic("generating") is True
    assert expanded() == {"importing": False, "generating": True, "library_tree": False, "kicad_detection": False, "filter": False}
    assert dialog.show_topic("filter#how-it-works") is True
    assert expanded() == {"importing": False, "generating": False, "library_tree": False, "kicad_detection": False, "filter": True}
    assert all(_find_item(dialog, key).isExpanded() for key in groups)


def test_clicking_a_page_below_the_open_one_selects_it(qtbot):
    # The click folds the open page's sections, which moves the rows under the mouse; the new page stays selected
    dialog = HelpDialog(topic="importing")
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    _click_row(dialog, _find_item(dialog, "shortcuts"))
    qtbot.waitUntil(lambda: not _find_item(dialog, "importing").isExpanded(), timeout=5000)
    assert _current_key(dialog) == "shortcuts"
    assert "Keyboard Shortcuts" in dialog._browser.toPlainText()


def test_clicking_the_selected_section_again_scrolls_back(qtbot):
    dialog = HelpDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    browser = dialog._browser
    dialog.show_topic("importing#conflicts")
    qtbot.waitUntil(lambda: _heading_is_in_view(browser, "4.4.7 Conflicts"), timeout=5000)

    browser.verticalScrollBar().setValue(0)
    assert not _heading_is_in_view(browser, "4.4.7 Conflicts")
    _click_row(dialog, _find_item(dialog, "importing#conflicts"))
    assert _current_key(dialog) == "importing#conflicts"
    qtbot.waitUntil(lambda: _heading_is_in_view(browser, "4.4.7 Conflicts"), timeout=5000)


def test_help_dialog_fits_the_screen(qtbot, monkeypatch):
    area = QRect(0, 0, 960, 492)  # Full HD at 200%
    monkeypatch.setattr(import_dialog, "screen_area", lambda widget: area)
    dialog = HelpDialog()  # the way the main window opens it, with no parent
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    assert area.contains(dialog.frameGeometry())
    assert dialog.height() <= 452


def test_numbers_are_rendered_not_typed():
    for key, page in HELP_PAGES.items():
        assert re.search(r"<h[23]>\s*\d", page) is None, key
    for _key, label, children in TOC_STRUCTURE:
        assert not label[:1].isdigit()
        assert not any(child_label[:1].isdigit() for _child_key, child_label in children)
    rendered = help_dialog.render_page("importing")
    assert "<h2>4.4 Importing Parts</h2>" in rendered
    assert '<h3><a name="conflicts"></a>4.4.7 Conflicts</h3>' in rendered
    assert "<h3>Conflicts</h3>" in HELP_PAGES["importing"]
    assert help_dialog.render_page("importing") == rendered


def _heading_looks(browser: QTextBrowser, level: int) -> list[set[tuple]]:
    """For each heading block of this level, the (point size, foreground) of every fragment in it."""
    looks = []
    for block, _text in _headings(browser, level):
        looks.append({
            (fmt.fontPointSize(), fmt.foreground().style(), fmt.foreground().color().name().upper())
            for fmt in (fragment.fragment().charFormat() for fragment in block)
        })
    return looks


@pytest.mark.parametrize("key", ["importing", "filter"])
def test_rendered_headings_keep_their_look(qtbot, key):
    raw, rendered = QTextBrowser(), QTextBrowser()
    for browser in (raw, rendered):
        qtbot.addWidget(browser)
    raw.setHtml(HELP_PAGES[key])
    rendered.setHtml(help_dialog.render_page(key))
    for level in (2, 3):
        assert _heading_looks(raw, level), f"no level {level} heading on the {key} page"
        assert _heading_looks(rendered, level) == _heading_looks(raw, level)
    # an anchor that took the link style would show the accent colour in a section heading
    for look in _heading_looks(rendered, 3):
        assert all(colour != ACCENT.upper() for _size, _style, colour in look)


def test_help_repo_scan_explains_skip_and_the_saved_scan():
    page = _page_text("repo_scan")

    for text in (
        "saved scan", "no library file changed", "Rescan", "Loading Libraries", "Skip",
        "3D model paths", "still listed", "Generate Tables",
    ):
        assert text in page, text
    assert "<h3" not in HELP_PAGES["repo_scan"]


# -- The guide remembers the owner's place (plan 12-19, G-12-23) ------------------------------------------------


def _expanded_page_keys(dialog: HelpDialog) -> set[str]:
    """The keys of the page items that show their sections."""
    return {
        item.data(0, Qt.ItemDataRole.UserRole)
        for item in _page_items(dialog)
        if item.childCount() > 0 and item.isExpanded()
    }


def test_help_topic_settings_round_trip():
    assert settings.load_help_topic() is None
    settings.save_help_topic("importing#conflicts")
    assert settings.load_help_topic() == "importing#conflicts"
    # the stored value is untrusted: anything but a non-empty text reads as nothing saved
    for odd in ("", 7, ["a"]):
        settings.get_settings().setValue("help/last_topic", odd)
        assert settings.load_help_topic() is None, odd


@pytest.mark.parametrize("how", ["close", "escape", "parent deleted"])
def test_owner_choice_is_remembered_after_close_escape_and_parent_deleted(qtbot, how):
    parent = QWidget() if how == "parent deleted" else None
    dialog = HelpDialog(parent)
    if parent is None:
        qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)

    _click_row(dialog, _find_item(dialog, "importing#conflicts"))
    qtbot.waitUntil(lambda: _current_key(dialog) == "importing#conflicts", timeout=5000)

    if how == "close":
        dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Close).click()
        assert not dialog.isVisible()
    elif how == "escape":
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
        assert not dialog.isVisible()
    else:
        shiboken6.delete(parent)
        assert not shiboken6.isValid(dialog)

    reopened = HelpDialog()
    qtbot.addWidget(reopened)
    reopened.show()
    qtbot.waitExposed(reopened)
    assert _current_key(reopened) == "importing#conflicts"
    assert reopened._toc.currentItem().isSelected()
    # the node's page is open, every other page with sections is folded
    assert _expanded_page_keys(reopened) == {"importing"}
    qtbot.waitUntil(lambda: _heading_is_in_view(reopened._browser, "4.4.7 Conflicts"), timeout=5000)


def test_saved_place_survives_a_restart(qtbot):
    settings.save_help_topic("filter#per-source-scoping")
    dialog = HelpDialog()
    qtbot.addWidget(dialog)
    assert _current_key(dialog) == "filter#per-source-scoping"
    assert _expanded_page_keys(dialog) == {"filter"}
    assert "5 Footprint Filter" in dialog._browser.toPlainText()
    dialog.show()
    qtbot.waitExposed(dialog)
    qtbot.waitUntil(lambda: _heading_is_in_view(dialog._browser, "5.2 Per-source scoping"), timeout=5000)


def test_an_explicit_topic_wins_and_is_not_remembered(qtbot):
    settings.save_help_topic("filter")
    dialog = HelpDialog(topic="importing")
    qtbot.addWidget(dialog)
    assert _current_key(dialog) == "importing"
    assert settings.load_help_topic() == "filter"

    # a program-driven move on an open guide is not the owner's either
    assert dialog.show_topic("shortcuts") is True
    assert _current_key(dialog) == "shortcuts"
    assert settings.load_help_topic() == "filter"

    later = HelpDialog()
    qtbot.addWidget(later)
    assert _current_key(later) == "filter"
    assert settings.load_help_topic() == "filter"

    # the owner's own click is remembered
    dialog.show()
    qtbot.waitExposed(dialog)
    _click_row(dialog, _find_item(dialog, "generating"))
    qtbot.waitUntil(lambda: _current_key(dialog) == "generating", timeout=5000)
    assert settings.load_help_topic() == "generating"


@pytest.mark.parametrize("saved, opens", [
    ("importing#no-such-heading", "importing"),
    ("no_such_page", "overview"),
    ("_how_to_use", "library_tree"),  # a group opens its first page
    ("", "overview"),  # empty reads as nothing saved
])
def test_stale_saved_places_fall_back(qtbot, saved, opens):
    settings.get_settings().setValue("help/last_topic", saved)
    dialog = HelpDialog()
    qtbot.addWidget(dialog)
    assert _current_key(dialog) == opens
    # the fallback itself is not an owner move: the odd value stays as it was
    assert settings.get_settings().value("help/last_topic", "") == saved
    assert dialog._browser.toPlainText().strip() != ""


# -- The guide brings the chosen heading back (plan 12-21, G-12-27) --------------------------------------------


def _heading_near_top(browser: QTextBrowser, text: str) -> bool:
    """True when the level-3 heading is scrolled to, near the top of the view, not merely on screen."""
    for block, shown in _headings(browser, 3):
        if shown == text:
            top = browser.document().documentLayout().blockBoundingRect(block).top() - browser.verticalScrollBar().value()
            return -1 < top < browser.viewport().height() / 4
    return False


def _selected_keys(dialog: HelpDialog) -> list[str]:
    return [item.data(0, Qt.ItemDataRole.UserRole) for item in dialog._toc.selectedItems()]


def test_asked_topic_lasts_until_the_owner_moves(qtbot):
    dialog = HelpDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    assert dialog.shows_asked_topic() is False

    assert dialog.show_topic("importing") is True
    assert dialog.shows_asked_topic() is True
    dialog.show_remembered()
    assert dialog.shows_asked_topic() is False

    assert dialog.show_topic("importing") is True
    _click_row(dialog, _find_item(dialog, "generating"))
    qtbot.waitUntil(lambda: _current_key(dialog) == "generating", timeout=5000)
    assert dialog.shows_asked_topic() is False
    assert settings.load_help_topic() == "generating"

    dialog.show_remembered()
    assert dialog.show_topic("no_such_page") is False
    assert dialog.shows_asked_topic() is False


@pytest.mark.parametrize("how", ["close", "escape"])
def test_reopened_guide_brings_the_section_heading_back(qtbot, how):
    dialog = HelpDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    _click_row(dialog, _find_item(dialog, "importing#conflicts"))
    qtbot.waitUntil(lambda: _current_key(dialog) == "importing#conflicts", timeout=5000)
    qtbot.waitUntil(lambda: _heading_near_top(dialog._browser, "4.4.7 Conflicts"), timeout=5000)

    dialog._browser.verticalScrollBar().setValue(0)
    assert not _heading_is_in_view(dialog._browser, "4.4.7 Conflicts")

    if how == "close":
        dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Close).click()
    else:
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
    assert not dialog.isVisible()

    # what MainWindow.show_guide does with a hidden guide
    dialog.show_remembered()
    dialog.show()
    qtbot.waitExposed(dialog)
    assert _current_key(dialog) == "importing#conflicts"
    assert _selected_keys(dialog) == ["importing#conflicts"]  # a pin: the page row is not the selected one
    assert _expanded_page_keys(dialog) == {"importing"}
    assert settings.load_help_topic() == "importing#conflicts"
    qtbot.waitUntil(lambda: _heading_near_top(dialog._browser, "4.4.7 Conflicts"), timeout=5000)


def test_show_topic_on_the_shown_topic_brings_its_heading_back(qtbot):
    dialog = HelpDialog(topic="importing#conflicts")
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    qtbot.waitUntil(lambda: _heading_near_top(dialog._browser, "4.4.7 Conflicts"), timeout=5000)

    dialog._browser.verticalScrollBar().setValue(0)
    assert dialog.show_topic("importing#conflicts") is True
    qtbot.waitUntil(lambda: _heading_near_top(dialog._browser, "4.4.7 Conflicts"), timeout=5000)

    assert dialog.show_topic("importing") is True
    bar = dialog._browser.verticalScrollBar()
    bar.setValue(bar.maximum())
    assert bar.value() > 0
    assert dialog.show_topic("importing") is True
    qtbot.waitUntil(lambda: bar.value() == 0, timeout=5000)

    assert settings.load_help_topic() is None  # programmatic moves save nothing


def test_fresh_guide_shows_the_saved_heading_after_fit_window_narrows(qtbot, monkeypatch):
    # 860 px plus the frame no longer fits, so fit_window narrows the guide after the page was laid out
    monkeypatch.setattr(import_dialog, "screen_area", lambda widget: QRect(0, 0, 800, 800))
    settings.save_help_topic("importing#conflicts")
    dialog = HelpDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    assert dialog.width() < 860
    assert _current_key(dialog) == "importing#conflicts"
    assert _selected_keys(dialog) == ["importing#conflicts"]
    qtbot.waitUntil(lambda: _heading_near_top(dialog._browser, "4.4.7 Conflicts"), timeout=5000)
