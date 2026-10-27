"""One footprint per atomic part (Phase 10, D-14): the plan, the preview and the dialog choose a single vendor footprint.

A package that holds several footprints installs only the chosen one into Atomic_Footprints, links it
from the symbol, and lists the others as "Not used". Several footprints with no choice is refused.
"""

from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from test_import_dialog import (
    multi_zip,
    no_git_commit,
    no_git_probe,
    recording_build,
    set_library,
    wait_current,
)
from zipfixtures import STEP_BYTES, footprint, footprint_library_for, make_zip, symbol_lib, write_custom_layout

from kicad_lib_manager import settings
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.plan import InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.importer.preview import preview_sections
from kicad_lib_manager.kicad_files import find_property, find_symbol, parse_bytes
from kicad_lib_manager.models import Severity
from kicad_lib_manager.widgets.import_dialog import ImportCore, ImportDialog

REPO_ROOT = Path(__file__).resolve().parent.parent
LIBRARY = "Atomic_Analog"
SHARED = footprint_library_for(LIBRARY)
DATASHEET = {"Datasheet": "https://example.com/part"}


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qsettings"))
    assert tmp_path.resolve() in Path(settings.get_settings().fileName()).resolve().parents


@pytest.fixture
def layout(tmp_path):
    write_custom_layout(tmp_path / "repo", [LIBRARY], [SHARED])
    return RepoLayout.for_repo(tmp_path / "repo")


@contextmanager
def _open(tmp_path, footprints=("F1", "F2", "F3"), models=()):
    members = [("part.kicad_sym", symbol_lib(("PART",), props=DATASHEET))]
    members += [(f"{name}.kicad_mod", footprint(name)) for name in footprints]
    members += [(name, STEP_BYTES) for name in models]
    src = tmp_path / "src"
    src.mkdir(exist_ok=True)
    with open_package(make_zip(src / "pkg.zip", members), REPO_ROOT) as package:
        candidate, _ = detect_candidate(package)
        assert candidate is not None
        yield candidate


def _codes(plan):
    return [i.code for i in plan.issues if i.severity is Severity.ERROR]


def test_chosen_footprint_alone_is_planned_and_the_rest_are_not_used(layout, tmp_path):
    with _open(tmp_path) as candidate:
        options = InstallOptions(library=LIBRARY, footprint="F2")
        plan = build_plan(candidate, options, layout)
        assert not plan.blocked, plan.issues
        assert plan.footprint_names == ("F2",)
        assert plan.footprint_link == f"{SHARED}:F2"
        assert plan.unused_footprints == ("F1", "F3")
        sections = {s.name: s for s in preview_sections(plan, candidate, options)}
        assert sections["Not used"].title == "Not used (2)"
        assert [row.text for row in sections["Not used"].rows] == ["F1", "F3"]
        assert all(row.kind == "unused" and row.tone == "muted" for row in sections["Not used"].rows)
        result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues
    pretty = layout.footprints_dir / f"{SHARED}.pretty"
    assert sorted(p.name for p in pretty.iterdir()) == ["F2.kicad_mod"]
    library = parse_bytes((layout.symbols_dir / f"{LIBRARY}.kicad_sym").read_bytes(), "lib")
    symbol = find_symbol(library.root, "PART")
    assert find_property(symbol.node, "Footprint").value == f"{SHARED}:F2"
    assert find_property(symbol.node, "ki_fp_filters").value == "F2"


def test_single_footprint_package_has_nothing_unused(layout, tmp_path):
    with _open(tmp_path, footprints=("ONLY",)) as candidate:
        options = InstallOptions(library=LIBRARY)
        plan = build_plan(candidate, options, layout)
        names = [s.name for s in preview_sections(plan, candidate, options)]
    assert not plan.blocked, plan.issues
    assert plan.unused_footprints == ()
    assert "Not used" not in names


def test_several_footprints_without_a_choice_is_refused(layout, tmp_path):
    with _open(tmp_path) as candidate:
        plan = build_plan(candidate, InstallOptions(library=LIBRARY), layout)
    assert plan.blocked and not plan.ops
    assert _codes(plan) == ["install.choice_required"]
    text = next(i.text for i in plan.issues if i.code == "install.choice_required")
    assert "F1" in text and "F2" in text and "F3" in text
    assert plan.unused_footprints == ()


def test_unknown_footprint_is_refused(layout, tmp_path):
    with _open(tmp_path) as candidate:
        plan = build_plan(candidate, InstallOptions(library=LIBRARY, footprint="NOPE"), layout)
    assert _codes(plan) == ["install.unknown_item"]
    assert not plan.ops


def test_the_model_links_from_the_chosen_footprint_only(layout, tmp_path):
    with _open(tmp_path, models=("m.step",)) as candidate:
        plan = build_plan(candidate, InstallOptions(library=LIBRARY, footprint="F3"), layout)
    assert not plan.blocked, plan.issues
    assert [op.path.name for op in plan.ops if op.kind == "footprint"] == ["F3.kicad_mod"]
    assert plan.model_file == "PART.step"


# -- the dialog ---------------------------------------------------------------------------------------


@pytest.fixture
def recorded():
    return []


@pytest.fixture
def make_dialog(qtbot, layout, recorded):
    def make(package: Path) -> ImportDialog:
        fields = {
            "detect_tools": lambda kicad_fp_dir: ToolContext(),
            "downloads_dir": lambda: None,
            "build_plan": recording_build(recorded),
            "kicad_running": lambda: [],
            "probe_commit": no_git_probe,
            "run_commit": no_git_commit,
        }
        dialog = ImportDialog(layout.repo_root, layout, core=replace(ImportCore(), **fields))
        qtbot.addWidget(dialog)
        dialog.show()
        dialog.open_path(package)
        return dialog

    return make


def test_dialog_combo_lists_the_footprints_and_choosing_one_links_it(qtbot, make_dialog, recorded, tmp_path):
    dialog = make_dialog(multi_zip(tmp_path))
    wait_current(qtbot, dialog)
    combo = dialog._fp_combo
    assert combo is not None
    assert [combo.itemText(i) for i in range(combo.count())] == ["F1", "F2", "F3"]
    assert recorded[-1].footprint == "F1"

    set_library(dialog, LIBRARY)
    wait_current(qtbot, dialog)
    assert dialog._fp_field.text() == f"{SHARED}:F1"

    combo.setCurrentIndex(2)
    wait_current(qtbot, dialog)
    assert recorded[-1].footprint == "F3"
    assert dialog._fp_field.text() == f"{SHARED}:F3"
    assert dialog._plan.unused_footprints == ("F1", "F2")
