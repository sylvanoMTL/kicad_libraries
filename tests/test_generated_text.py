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
