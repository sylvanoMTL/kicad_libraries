"""Generated keywords, footprint description and footprint tags, from the planner to the installed files and the dialog (plan 10-23).

The Ultra Librarian CSD85301Q2 sample is the subject: its footprint DQK0006B has tags "CSD85301Q2 " and no
description, and KiCad's own Package_SON:Texas_DQK (a synthetic stand-in under tmp_path) names the family.
Every install goes into an isolated Custom/ built in code.
"""

from dataclasses import replace
from pathlib import Path

import pytest
from customfixtures import ABSENT_LIBRARY
from installfixtures import UL_DESCRIPTION
from PySide6.QtCore import QSettings
from stockfixtures import write_stock_sample

from kicad_lib_manager import settings
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.footprint_text import vendor_texts
from kicad_lib_manager.importer.plan import InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.kicad_files import find_property, find_symbol, footprint_name, load
from kicad_lib_manager.widgets.import_dialog import ImportCore, ImportDialog

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
LIBRARY = ABSENT_LIBRARY  # Atomic_Transistor_FET, absent from the atomic_custom layout
SYMBOL = "CSD85301Q2"
FOOTPRINT = "DQK0006B"
SENTENCE = "WSON-6 2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B"


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qsettings"))
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


@pytest.fixture
def stock_footprints(tmp_path) -> Path:
    """KiCad's footprints folder as the synthetic stock tree holds it (Package_SON:Texas_DQK names the WSON-6 family)."""
    return write_stock_sample(tmp_path / "stock")[1]


def plan_for(candidate, layout, tools=ToolContext(), **options):
    options.setdefault("description", UL_DESCRIPTION)
    return build_plan(candidate, InstallOptions(library=LIBRARY, **options), layout, tools)


def installed_texts(layout) -> tuple[str, str, str]:
    """The keywords of the installed symbol and the description and tags of the installed footprint."""
    library = load(layout.symbols_dir / f"{LIBRARY}.kicad_sym")
    keywords = find_property(find_symbol(library.root, SYMBOL).node, "ki_keywords").value
    pretty = next(layout.footprints_dir.glob("*.pretty"))
    footprint = footprint_name(load(pretty / f"{FOOTPRINT}.kicad_mod").root)
    description, tags = vendor_texts(footprint.node)
    return keywords, description, tags


# -- the tracer: the CSD sample end to end -------------------------------------------------------------


def test_csd_part_text_is_generated_from_the_package_and_kicads_footprint(atomic_custom, ul_package, stock_footprints):
    _, candidate = ul_package
    plan = plan_for(candidate, atomic_custom, ToolContext(kicad_footprints_dir=stock_footprints))
    assert not plan.blocked, plan.issues
    text = plan.part_text
    assert text.fp_description == SENTENCE
    tags = text.fp_tags.split()
    assert tags[0] == SYMBOL  # the vendor's own tag stays first
    assert {"WSON-6", FOOTPRINT, "P0.65mm"} <= set(tags)
    words = text.keywords.split()
    assert {"Transistor", "FET", "TI", "Texas"} <= set(words)
    assert text == plan.generated_text  # nothing was typed over


def test_installed_files_hold_exactly_the_planned_text(atomic_custom, ul_package, stock_footprints, tmp_path):
    _, candidate = ul_package
    plan = plan_for(candidate, atomic_custom, ToolContext(kicad_footprints_dir=stock_footprints))
    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues
    keywords, description, tags = installed_texts(atomic_custom)
    assert (keywords, description, tags) == (
        plan.part_text.keywords,
        plan.part_text.fp_description,
        plan.part_text.fp_tags,
    )


# -- the dialog shows the same three texts -------------------------------------------------------------


def core_with(**changes) -> ImportCore:
    from kicad_lib_manager.importer.commit_step import CommitProbe

    fields = {
        "detect_tools": lambda kicad_fp_dir: ToolContext(),
        "kicad_running": lambda: [],
        "probe_commit": lambda cplan, **kwargs: CommitProbe(state="unavailable", reason="git is not used by this test"),
        **changes,
    }
    return replace(ImportCore(), **fields)


@pytest.fixture
def make_dialog(qtbot, atomic_custom, tmp_path):
    def make(tools: ToolContext = ToolContext()) -> ImportDialog:
        dialog = ImportDialog(
            atomic_custom.repo_root,
            atomic_custom,
            core=core_with(detect_tools=lambda kicad_fp_dir: tools),
            backup_root=tmp_path / "backups",
        )
        qtbot.addWidget(dialog)
        dialog.open_path(UL_ZIP)
        return dialog

    return make


def wait_current(qtbot, dialog: ImportDialog, timeout: int = 30000) -> None:
    """Wait until the newest request has been built and accepted and nothing is pending."""
    qtbot.waitUntil(
        lambda: dialog._plan is not None
        and dialog._plan_gen == dialog._gen
        and dialog._building is None
        and dialog._queued is None
        and not dialog._dirty,
        timeout=timeout,
    )


def pick_library(qtbot, dialog: ImportDialog, name: str = LIBRARY) -> None:
    wait_current(qtbot, dialog)
    dialog._library_combo.setEditText(name)
    dialog._library_combo.textActivated.emit(name)
    wait_current(qtbot, dialog)


def dialog_texts(dialog: ImportDialog) -> tuple[str, str, str]:
    edits = dialog._text_edits
    return edits["keywords"].text(), edits["fp_description"].text(), edits["fp_tags"].text()


def test_dialog_edits_show_the_plan_text(qtbot, make_dialog, stock_footprints):
    dialog = make_dialog(ToolContext(kicad_footprints_dir=stock_footprints))
    pick_library(qtbot, dialog)
    plan = dialog._plan
    assert plan.part_text.fp_description == SENTENCE
    assert dialog_texts(dialog) == (
        plan.part_text.keywords,
        plan.part_text.fp_description,
        plan.part_text.fp_tags,
    )
    assert all(not button.isEnabled() for button in dialog._text_regenerate.values())


# -- overrides, empty values and the plain-language preview ---------------------------------------------


def test_typed_texts_are_written_exactly(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    plan = plan_for(candidate, atomic_custom, keywords="alpha beta", fp_description="My sentence", fp_tags="x y")
    assert not plan.blocked, plan.issues
    assert plan.part_text.keywords == "alpha beta"
    assert plan.generated_text.keywords != "alpha beta"  # Regenerate has something to return to
    assert apply_plan(plan, backup_root=tmp_path / "bk").ok
    assert installed_texts(atomic_custom) == ("alpha beta", "My sentence", "x y")


def test_empty_texts_are_written_empty(atomic_custom, ul_package, tmp_path):
    _, candidate = ul_package
    plan = plan_for(candidate, atomic_custom, keywords="", fp_description="", fp_tags="")
    assert not plan.blocked, plan.issues
    assert (plan.part_text.keywords, plan.part_text.fp_description, plan.part_text.fp_tags) == ("", "", "")
    assert apply_plan(plan, backup_root=tmp_path / "bk").ok
    assert installed_texts(atomic_custom) == ("", "", "")


def test_quotes_and_backslashes_in_typed_text_do_not_break_the_files(atomic_custom, ul_package, tmp_path):
    # T-10-29: the values go through quote(), so the files still load and the text reads back exactly
    text = 'say "hi" \\ and more'
    _, candidate = ul_package
    plan = plan_for(candidate, atomic_custom, keywords=text, fp_description=text, fp_tags=text)
    assert not plan.blocked, plan.issues
    assert apply_plan(plan, backup_root=tmp_path / "bk").ok
    assert installed_texts(atomic_custom) == (text, text, text)


def test_without_a_kicad_footprints_folder_no_family_is_guessed(atomic_custom, ul_package):
    _, candidate = ul_package
    plan = plan_for(candidate, atomic_custom)
    assert plan.part_text.fp_description == "2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B"
    assert "WSON-6" not in plan.part_text.fp_tags.split()


def test_an_unrelated_official_footprint_supplies_no_family(atomic_custom, ul_package, tmp_path):
    # Package_SO holds only SOIC-8, and the code DQK0006B shares no leading word with it
    from stockfixtures import write_stock_kicad

    _, footprints = write_stock_kicad(
        tmp_path / "other", {}, {"Package_SO": (("SOIC-8_3.9x4.9mm_P1.27mm", ("1", "2"), "", ""),)}
    )
    _, candidate = ul_package
    plan = plan_for(candidate, atomic_custom, ToolContext(kicad_footprints_dir=footprints))
    assert plan.part_text.fp_description == "2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B"


# -- field changes -------------------------------------------------------------------------------------


def _field_rows(plan, candidate, options=None):
    from kicad_lib_manager.importer.preview import preview_sections

    sections = preview_sections(plan, candidate, options or InstallOptions(library=LIBRARY))
    return next(s for s in sections if s.name == "Field changes").rows


def test_field_changes_use_kicads_names_not_raw_ones(atomic_custom, ul_package):
    _, candidate = ul_package
    plan = plan_for(candidate, atomic_custom)
    rows = _field_rows(plan, candidate)
    labels = [row.text for row in rows]
    assert "Set Keywords" in labels
    assert "Set Footprint description" in labels
    assert "Set Footprint tags" in labels
    assert not any("ki_" in row.text or "ki_" in row.detail for row in rows)


def test_footprint_field_changes_are_scoped_to_the_footprint(atomic_custom, ul_package):
    _, candidate = ul_package
    plan = plan_for(candidate, atomic_custom)
    by_field = {change.field: change for change in plan.field_changes}
    assert by_field["Footprint description"].scope == "footprint"
    assert by_field["Footprint description"].symbol == FOOTPRINT
    assert by_field["ki_keywords"].scope == "symbol"
    assert by_field["Footprint tags"].old == "CSD85301Q2 "


# -- a vendor package with its own text -----------------------------------------------------------------

VENDOR = "PART"
EXISTING = "Atomic_Battery_Management"


def _vendor_zip(tmp_path, *, keywords="", descr="", tags=""):
    from installfixtures import ATOMIC_PROPS, vendor_footprint, vendor_symbol_lib
    from zipfixtures import STEP_BYTES, make_zip

    footprint = vendor_footprint("FP")
    extra = (f'  (descr "{descr}")\r\n' if descr else "") + (f'  (tags "{tags}")\r\n' if tags else "")
    footprint = footprint.replace(b'  (layer "F.Cu")\r\n', b'  (layer "F.Cu")\r\n' + extra.encode(), 1)
    symbol = vendor_symbol_lib(VENDOR, keywords=keywords, props=ATOMIC_PROPS)
    (tmp_path / "src").mkdir(exist_ok=True)
    return make_zip(
        tmp_path / "src" / "pkg.zip",
        [("part.kicad_sym", symbol), ("FP.kicad_mod", footprint), ("part.step", STEP_BYTES)],
    )


def _open_vendor(zip_path):
    from kicad_lib_manager.importer.detect import detect_candidate
    from kicad_lib_manager.importer.package import open_package

    package = open_package(zip_path, REPO_ROOT)
    candidate, _ = detect_candidate(package)
    assert candidate is not None
    return package, candidate


def test_a_vendor_description_is_replaced_and_listed(atomic_custom, tmp_path):
    package, candidate = _open_vendor(_vendor_zip(tmp_path, descr="Old sentence"))
    try:
        options = InstallOptions(library=EXISTING)
        plan = build_plan(candidate, options, atomic_custom, ToolContext())
        rows = _field_rows(plan, candidate, options)
    finally:
        package.close()
    row = next(r for r in rows if r.text.endswith("Set Footprint description"))
    assert row.detail == f"Old sentence → {plan.part_text.fp_description}: generated"
    assert "Old sentence" not in plan.part_text.fp_description


def test_vendor_keywords_come_first_and_junk_is_dropped(atomic_custom, tmp_path):
    package, candidate = _open_vendor(_vendor_zip(tmp_path, keywords="power digikey MOSFET"))
    try:
        plan = build_plan(candidate, InstallOptions(library=EXISTING), atomic_custom, ToolContext())
    finally:
        package.close()
    words = plan.part_text.keywords.split()
    assert words[:2] == ["power", "MOSFET"]
    assert "digikey" not in [word.casefold() for word in words]
    assert "Battery" in words  # the generated words follow


def test_a_symbol_renamed_by_a_conflict_keeps_the_vendor_keywords_retokened(atomic_custom, tmp_path):
    from kicad_lib_manager.importer.plan import Resolution

    package, candidate = _open_vendor(_vendor_zip(tmp_path, keywords="PART power"))
    try:
        first = build_plan(candidate, InstallOptions(library=EXISTING), atomic_custom, ToolContext())
        assert apply_plan(first, backup_root=tmp_path / "bk").ok
        # A changed description makes the second install differ from the first, so the symbol conflicts
        options = InstallOptions(
            library=EXISTING,
            description="Another description",
            resolutions={f"symbol:{EXISTING}:{VENDOR}": Resolution("rename")},
        )
        second = build_plan(candidate, options, atomic_custom, ToolContext())
    finally:
        package.close()
    assert second.symbol_name == f"{VENDOR}_2"
    assert second.part_text.keywords.split()[:2] == [f"{VENDOR}_2", "power"]


# -- the dialog: edit, Regenerate, follow the library ---------------------------------------------------


def type_text(dialog: ImportDialog, name: str, text: str) -> None:
    """Type into one generated-text row like the owner: key presses, so it counts as edited."""
    from PySide6.QtTest import QTest

    edit = dialog._text_edits[name]
    edit.setFocus()
    edit.selectAll()
    QTest.keyClicks(edit, text)


def test_an_edited_keywords_row_is_written_and_regenerate_returns_to_the_generated_text(qtbot, make_dialog):
    dialog = make_dialog()
    pick_library(qtbot, dialog)
    generated = dialog._plan.generated_text.keywords
    type_text(dialog, "keywords", "custom words")
    wait_current(qtbot, dialog)
    assert dialog._plan.part_text.keywords == "custom words"
    assert dialog._text_edits["keywords"].text() == "custom words"
    assert dialog._text_regenerate["keywords"].isEnabled()
    assert not dialog._text_regenerate["fp_tags"].isEnabled()
    dialog._text_regenerate["keywords"].click()
    wait_current(qtbot, dialog)
    assert dialog._plan.part_text.keywords == generated
    assert dialog._text_edits["keywords"].text() == generated
    assert not dialog._text_regenerate["keywords"].isEnabled()


def test_an_emptied_row_writes_an_empty_value(qtbot, make_dialog):
    dialog = make_dialog()
    pick_library(qtbot, dialog)
    edit = dialog._text_edits["fp_tags"]
    edit.setFocus()
    edit.selectAll()
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    QTest.keyClick(edit, Qt.Key.Key_Delete)
    wait_current(qtbot, dialog)
    assert dialog._plan.part_text.fp_tags == ""
    assert dialog._text_edits["fp_tags"].text() == ""


def test_an_untouched_row_follows_a_library_change(qtbot, make_dialog):
    dialog = make_dialog()
    pick_library(qtbot, dialog, "Atomic_Transistor_FET")
    before = dialog._text_edits["keywords"].text()
    assert "FET" in before.split()
    type_text(dialog, "fp_tags", "mine")
    wait_current(qtbot, dialog)
    pick_library(qtbot, dialog, "Atomic_Sensor_Temperature")
    after = dialog._text_edits["keywords"].text()
    assert "Temperature" in after.split() and "FET" not in after.split()
    assert dialog._text_edits["fp_tags"].text() == "mine"  # a typed row keeps its text


# -- the real kicad-cli loads what is written -----------------------------------------------------------


@pytest.mark.kicad_cli
def test_cli_loads_the_generated_text(atomic_custom, ul_package, tmp_path, real_tools, kicad_cli_path):
    from kicad_lib_manager.importer import kicad_cli
    from kicad_lib_manager.models import Severity

    _, candidate = ul_package
    plan = plan_for(candidate, atomic_custom, real_tools)
    assert not plan.blocked, plan.issues
    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues
    keywords, description, tags = installed_texts(atomic_custom)
    assert (keywords, description, tags) == (
        plan.part_text.keywords,
        plan.part_text.fp_description,
        plan.part_text.fp_tags,
    )
    footprint_data = (plan.pretty_path / f"{FOOTPRINT}.kicad_mod").read_bytes()
    symbol_lib = (atomic_custom.symbols_dir / f"{LIBRARY}.kicad_sym").read_bytes()
    issues = kicad_cli.load_gate(
        kicad_cli_path, library=LIBRARY, symbol_lib=symbol_lib, footprints=[(FOOTPRINT, footprint_data)]
    )
    assert [i for i in issues if i.severity is Severity.ERROR] == [], issues


def test_text_rows_fit_the_left_pane_and_are_named(qtbot, make_dialog):
    from PySide6.QtCore import QPoint

    dialog = make_dialog()
    dialog.show()
    dialog.resize(900, 600)
    wait_current(qtbot, dialog)
    scroll = dialog._left_scroll
    left = scroll.widget()
    assert not scroll.horizontalScrollBar().isVisible()
    assert left.width() <= scroll.viewport().width()
    labels = {"keywords": "Keywords", "fp_description": "Footprint description", "fp_tags": "Footprint tags"}
    for name, label in labels.items():
        edit, button = dialog._text_edits[name], dialog._text_regenerate[name]
        assert edit.accessibleName() == label
        assert button.accessibleName() == f"Regenerate {label}"
        assert (button.width(), button.height()) == (24, 24)
        assert "ki_" not in edit.toolTip() + button.toolTip()
        # a line edit never overlaps its button, and both stay inside the pane
        assert edit.mapTo(left, QPoint(edit.width(), 0)).x() <= button.mapTo(left, QPoint(0, 0)).x()
        assert button.mapTo(left, QPoint(button.width(), 0)).x() <= scroll.viewport().width()
