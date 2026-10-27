"""Linking an official KiCad footprint instead of installing the vendor one (plan 10-24, LIB-06, D-16 to D-18, D-29).

Every install goes into an isolated Custom/ built in code, and KiCad's footprints folder is a stand-in built under
tmp_path (write_fake_kicad holds Package_TO_SOT_SMD:SOT-23-5 with five pads and its model; write_stock_sample
holds the CSD family's Package_SON:Texas_DQK). Nothing here writes into the live Custom/ or a real KiCad install.
"""

import threading
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest
from customfixtures import (
    ABSENT_LIBRARY,
    OFFICIAL_FOOTPRINT,
    OFFICIAL_LIBRARY,
    write_fake_kicad,
)
from installfixtures import ATOMIC_PROPS, vendor_footprint, vendor_symbol_lib
from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtWidgets import QLabel, QWidget
from stockfixtures import write_stock_sample
from zipfixtures import STEP_BYTES, make_zip

from kicad_lib_manager import settings
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.footprint_index import build_index
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.plan import InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.importer.preview import preview_sections
from kicad_lib_manager.importer.verify import verify_install
from kicad_lib_manager.kicad_files import find_property, find_symbol, load
from kicad_lib_manager.models import Severity
from kicad_lib_manager.widgets.import_dialog import (
    OFFICIAL_FOOTPRINT_TEXT,
    VENDOR_FOOTPRINT_TEXT,
    ImportCore,
    ImportDialog,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ABSENT_LIBRARY  # Atomic_Transistor_FET, absent from the atomic_custom layout
OFFICIAL_LINK = f"{OFFICIAL_LIBRARY}:{OFFICIAL_FOOTPRINT}"
SYMBOL = "PART"


@contextmanager
def synthetic_package(tmp_path, *, footprint_pads=("1", "2"), footprints=("FP",), models=("FP.step",)):
    """Open a synthetic package: the symbol PART (pins 1 and 2), vendor footprints with the given pads and STEP models."""
    members = [("part.kicad_sym", vendor_symbol_lib(SYMBOL, props=ATOMIC_PROPS))]
    members += [(f"{name}.kicad_mod", vendor_footprint(name, pads=footprint_pads)) for name in footprints]
    members += [(name, STEP_BYTES) for name in models]
    source = tmp_path / "src"
    source.mkdir(exist_ok=True)
    with open_package(make_zip(source / "pkg.zip", members), REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield package, candidate


def official_options(link: str | None = OFFICIAL_LINK, **changes) -> InstallOptions:
    return InstallOptions(library=LIBRARY, footprint_target="official", official_footprint=link, **changes)


def codes(plan, severity: Severity) -> list[str]:
    return [issue.code for issue in plan.issues if issue.severity is severity]


# -- the tracer: a part linked to Package_TO_SOT_SMD:SOT-23-5, planned, gated, applied, verified and shown --------


def test_a_part_links_the_official_footprint_end_to_end(atomic_custom, tmp_path):
    footprints, _ = write_fake_kicad(tmp_path)
    tools = ToolContext(kicad_footprints_dir=footprints)
    with synthetic_package(tmp_path) as (_, candidate):
        plan = build_plan(candidate, official_options(), atomic_custom, tools)
        assert not plan.blocked, plan.issues
        # Only the symbol library is written: no footprint, no model and no Atomic_Footprints folder
        assert [op.kind for op in plan.ops] == ["symbol_lib"]
        assert plan.footprint_link == OFFICIAL_LINK
        assert plan.footprint_library == OFFICIAL_LIBRARY
        assert plan.footprint_names == ()
        assert plan.model_file is None
        assert plan.unused_footprints == ("FP",)
        assert plan.unused_models == ("FP.step",)
        assert not [code for code in codes(plan, Severity.ERROR) if code.startswith("install.atomic")]
        # The pads differ from the symbol's pins and from the vendor footprint, which is a warning and nothing more
        warnings = codes(plan, Severity.WARNING)
        assert "verify.pin_pad_mismatch" in warnings
        assert "install.pad_mismatch" in warnings
        mismatch = next(issue for issue in plan.issues if issue.code == "install.pad_mismatch")
        assert mismatch.text == f"{OFFICIAL_LINK} has different pads from the vendor footprint FP: extra 3, 4, 5"
        sections = {section.name: section for section in preview_sections(plan, candidate, official_options())}
        assert [row.detail for row in sections["Not used"].rows] == [
            "footprint, not installed: an official KiCad footprint is used",
            "3D model, not installed: KiCad's own 3D model is used",
        ]
        result = apply_plan(plan, backup_root=tmp_path / "backups")
        assert result.ok, result.issues
    assert [issue for issue in verify_install(plan) if issue.severity is Severity.ERROR] == []
    library = load(plan.symbol_lib_path)
    assert find_property(find_symbol(library.root, SYMBOL).node, "Footprint").value == OFFICIAL_LINK
    assert not (atomic_custom.footprints_dir / "Atomic_Footprints.pretty" / "FP.kicad_mod").exists()
    assert not (atomic_custom.models_dir / "PART.step").exists()


# -- the dialog: the destination choice and the ranked, filterable picker ----------------------------------

UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
TEXAS = "Package_SON:Texas_DQK"
SOT = "Package_TO_SOT_SMD:SOT-23-5"
VENDOR_FOOTPRINT = "DQK0006B"


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qsettings"))
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


@pytest.fixture
def stock_tools(tmp_path) -> ToolContext:
    """KiCad's stock symbols and footprints as the synthetic sample holds them (the CSD siblings link Package_SON:Texas_DQK)."""
    symbols, footprints = write_stock_sample(tmp_path / "stock")
    return ToolContext(kicad_symbols_dir=symbols, kicad_footprints_dir=footprints)


def core_with(tools: ToolContext, **changes) -> ImportCore:
    from kicad_lib_manager.importer.commit_step import CommitProbe

    fields = {
        "detect_tools": lambda kicad_fp_dir: tools,
        "kicad_running": lambda: [],
        "probe_commit": lambda cplan, **kwargs: CommitProbe(state="unavailable", reason="git is not used by this test"),
        **changes,
    }
    return replace(ImportCore(), **fields)


@pytest.fixture
def make_dialog(qtbot, atomic_custom, tmp_path):
    def make(tools: ToolContext, *, show: bool = False, **changes) -> ImportDialog:
        dialog = ImportDialog(
            atomic_custom.repo_root,
            atomic_custom,
            core=core_with(tools, **changes),
            backup_root=tmp_path / "backups",
        )
        qtbot.addWidget(dialog)
        if show:
            dialog.show()
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


def choose_official(qtbot, dialog: ImportDialog) -> None:
    """Switch to the official choice and wait for the picker's list and the plan that follows."""
    wait_current(qtbot, dialog)
    dialog._fp_official_radio.setChecked(True)
    qtbot.waitUntil(lambda: dialog._official_links is not None, timeout=30000)
    wait_current(qtbot, dialog)


def completions(dialog: ImportDialog, prefix: str) -> list[str]:
    """What the picker's completer offers for a typed prefix."""
    completer = dialog._official_combo.completer()
    completer.setCompletionPrefix(prefix)
    names = []
    for row in range(completer.completionCount()):
        completer.setCurrentRow(row)
        names.append(completer.currentCompletion())
    return names


def pick_official(qtbot, dialog: ImportDialog, link: str) -> None:
    dialog._official_combo.setEditText(link)
    dialog._official_combo.textActivated.emit(link)
    wait_current(qtbot, dialog)


def test_the_picker_lists_kicads_footprints_with_the_best_match_first_and_picks_nothing(qtbot, make_dialog, stock_tools):
    dialog = make_dialog(stock_tools)
    wait_current(qtbot, dialog)
    assert dialog._fp_vendor_radio.text() == VENDOR_FOOTPRINT_TEXT == "Install the vendor footprint into Atomic_Footprints"
    assert dialog._fp_official_radio.text() == OFFICIAL_FOOTPRINT_TEXT == "Use an official KiCad footprint"
    assert dialog._fp_vendor_radio.isChecked() and dialog._official_box.isHidden()
    choose_official(qtbot, dialog)
    combo = dialog._official_combo
    assert not dialog._official_box.isHidden()
    assert combo.itemText(0) == TEXAS
    assert {combo.itemText(i) for i in range(combo.count())} == {TEXAS, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm", SOT}
    assert combo.currentIndex() == -1 and combo.currentText() == ""
    # Nothing is picked yet, so the plan asks for a pick and points at the picker
    errors = [issue.code for issue in dialog._plan.issues if issue.severity is Severity.ERROR]
    assert errors == ["install.official_missing"]
    assert [(reason.text, reason.target) for reason in dialog._strip_reasons][:1] == [
        ("Pick an official KiCad footprint", "official_footprint")
    ]
    assert dialog._reason_targets["official_footprint"] is combo


def test_the_list_is_built_off_the_gui_thread(qtbot, make_dialog, stock_tools):
    threads: list[threading.Thread] = []

    def index_on_a_worker(folder, progress=None):
        threads.append(threading.current_thread())
        return build_index(folder, progress)

    dialog = make_dialog(stock_tools, footprint_index=index_on_a_worker)
    choose_official(qtbot, dialog)
    assert threads and all(thread is not threading.main_thread() for thread in threads)


def test_typing_filters_the_list_by_substring_ignoring_case(qtbot, make_dialog, stock_tools):
    dialog = make_dialog(stock_tools)
    choose_official(qtbot, dialog)
    assert completions(dialog, "sot") == [SOT]
    assert completions(dialog, "SOIC") == ["Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"]
    assert sorted(completions(dialog, "package_s")) == sorted([TEXAS, "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"])
    completer = dialog._official_combo.completer()
    assert completer.filterMode() == Qt.MatchFlag.MatchContains
    assert completer.caseSensitivity() == Qt.CaseSensitivity.CaseInsensitive


def test_a_pick_shows_the_official_link_in_the_footprint_field(qtbot, make_dialog, stock_tools):
    dialog = make_dialog(stock_tools)
    choose_official(qtbot, dialog)
    pick_official(qtbot, dialog, SOT)
    assert dialog._fp_field.text() == SOT
    assert dialog._fp_field.isReadOnly()
    assert dialog._plan.footprint_link == SOT
    assert dialog._plan.unused_footprints == (VENDOR_FOOTPRINT,)
    assert not [op for op in dialog._plan.ops if op.kind in ("footprint", "model", "mkdir")]


def test_an_official_footprint_switches_off_what_it_makes_meaningless(qtbot, make_dialog, stock_tools):
    dialog = make_dialog(stock_tools)
    wait_current(qtbot, dialog)
    assert dialog._fp_name_edit.isEnabled() and dialog._add_model_btn.isEnabled()
    choose_official(qtbot, dialog)
    assert not dialog._fp_name_edit.isEnabled()
    for name in ("fp_description", "fp_tags"):
        assert not dialog._text_edits[name].isEnabled()
        assert not dialog._text_regenerate[name].isEnabled()
        assert dialog._text_edits[name].text() == ""
    assert dialog._text_edits["keywords"].isEnabled()
    assert not dialog._add_model_btn.isEnabled()
    assert dialog._model_note.text() == "KiCad's own 3D model is used"
    hints = [label.text() for label in dialog._official_box.findChildren(QLabel)]
    assert "KiCad's own footprints are never changed" in hints


def test_switching_back_restores_the_vendor_footprint_name_and_the_generated_texts(qtbot, make_dialog, stock_tools):
    dialog = make_dialog(stock_tools)
    wait_current(qtbot, dialog)
    edits = dialog._text_edits
    before = (dialog._fp_name_edit.text(), edits["fp_description"].text(), edits["fp_tags"].text())
    assert before[0] == VENDOR_FOOTPRINT and before[1].startswith("WSON-6")
    choose_official(qtbot, dialog)
    pick_official(qtbot, dialog, TEXAS)
    dialog._fp_vendor_radio.setChecked(True)
    wait_current(qtbot, dialog)
    assert dialog._official_box.isHidden()
    assert dialog._fp_name_edit.isEnabled() and dialog._add_model_btn.isEnabled()
    assert (dialog._fp_name_edit.text(), edits["fp_description"].text(), edits["fp_tags"].text()) == before
    assert dialog._fp_field.text() == f"Atomic_Footprints:{VENDOR_FOOTPRINT}"
    assert dialog._plan.footprint_target == "shared"
    assert dialog._model_note.isHidden()


def test_without_a_kicad_install_the_official_choice_is_off_and_says_why(qtbot, make_dialog):
    dialog = make_dialog(ToolContext())
    wait_current(qtbot, dialog)
    assert not dialog._fp_official_radio.isEnabled()
    assert dialog._fp_official_radio.toolTip() == "KiCad's footprints were not found"
    assert dialog._official_note.text() == "KiCad's footprints were not found"
    assert dialog._fp_vendor_radio.isChecked()


def test_a_new_package_goes_back_to_the_vendor_footprint(qtbot, make_dialog, stock_tools):
    dialog = make_dialog(stock_tools)
    choose_official(qtbot, dialog)
    dialog.open_path(UL_ZIP)
    wait_current(qtbot, dialog)
    assert dialog._fp_vendor_radio.isChecked()
    assert dialog._official_links is None
    assert dialog._official_combo.count() == 0


def test_the_destination_choice_and_picker_fit_the_left_pane(qtbot, make_dialog, stock_tools):
    dialog = make_dialog(stock_tools, show=True)
    dialog.resize(900, 600)
    wait_current(qtbot, dialog)
    choose_official(qtbot, dialog)
    pick_official(qtbot, dialog, TEXAS)
    qtbot.wait(50)
    scroll = dialog._left_scroll
    viewport = scroll.viewport()
    left = scroll.widget()
    assert not scroll.horizontalScrollBar().isVisible()
    assert left.width() <= viewport.width()
    for widget in left.findChildren(QWidget):
        if widget.isVisible():
            right = widget.mapTo(left, QPoint(widget.width(), 0)).x()
            assert right <= viewport.width(), (widget, right, viewport.width())
    assert dialog._fp_official_radio.isVisible() and dialog._official_combo.isVisible()

