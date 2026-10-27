"""The install gate: build_plan runs the atomic check on the part as it would be installed (LIB-07, D-21, D-24).

Every install targets an isolated Custom/ built in code or a tmp_path folder. A broken rule is an ERROR
install.atomic.<rule> on the plan, so the plan is blocked and apply_plan refuses it before any write.
"""

from pathlib import Path

import pytest
from customfixtures import ABSENT_LIBRARY
from installfixtures import ATOMIC_PROPS, UL_DESCRIPTION, extends_pair, vendor_footprint
from PySide6.QtCore import QSettings
from test_import_dialog import core_with, set_library, type_description, wait_plan
from zipfixtures import STEP_BYTES, footprint, make_zip, symbol_lib

from kicad_lib_manager import atomic_check, settings
from kicad_lib_manager.importer.applier import apply_plan
from kicad_lib_manager.importer.detect import detect_candidate
from kicad_lib_manager.importer.package import open_package
from kicad_lib_manager.importer.plan import InstallOptions, ToolContext
from kicad_lib_manager.importer.planner import build_plan
from kicad_lib_manager.models import FootprintLibrary, Severity, SymbolLibrary
from kicad_lib_manager.widgets.import_dialog import ImportDialog

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
LIBRARY = ABSENT_LIBRARY


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qsettings"))
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


def _atomic_errors(plan) -> list[str]:
    return [i.code for i in plan.issues if i.severity is Severity.ERROR and i.code.startswith("install.atomic.")]


def _errors(plan) -> list[str]:
    return [i.code for i in plan.issues if i.severity is Severity.ERROR]


def _snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


# -- the tracer: the UL sample blocked on its missing Description, installed once one is typed -----------


def test_the_ul_sample_without_a_description_is_blocked_by_that_rule_alone(ul_package, synthetic_custom, tmp_path):
    _package, candidate = ul_package
    before = _snapshot(synthetic_custom.repo_root)

    plan = build_plan(candidate, InstallOptions(library=LIBRARY), synthetic_custom, ToolContext())

    assert _errors(plan) == ["install.atomic.description"]
    assert plan.blocked
    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert not result.ok
    assert _snapshot(synthetic_custom.repo_root) == before


def test_the_ul_sample_with_a_description_installs_and_the_scan_agrees(ul_package, synthetic_custom, tmp_path):
    _package, candidate = ul_package

    plan = build_plan(
        candidate, InstallOptions(library=LIBRARY, description=UL_DESCRIPTION), synthetic_custom, ToolContext()
    )

    assert _atomic_errors(plan) == []
    assert not plan.blocked, plan.issues
    result = apply_plan(plan, backup_root=tmp_path / "bk")
    assert result.ok, result.issues

    # The next scan's check, run over what was installed, finds nothing wrong with the part (gate and scan agree)
    repo = synthetic_custom.repo_root
    sym_libs = [SymbolLibrary(LIBRARY, f"Custom/Symbols/{LIBRARY}.kicad_sym", "Custom")]
    fp_libs = [
        FootprintLibrary(p.name[: -len(".pretty")], f"Custom/Footprints/{p.name}", "Custom")
        for p in sorted(synthetic_custom.footprints_dir.glob("*.pretty"))
    ]
    atomic_check.check_libraries(repo, sym_libs, fp_libs, None)
    entries = {entry.name: entry for entry in sym_libs[0].symbols}
    assert not entries["CSD85301Q2"].failing, entries["CSD85301Q2"].violations


def test_the_dialog_blocks_install_until_the_description_is_typed(qtbot, atomic_custom, tmp_path):
    dialog = ImportDialog(atomic_custom.repo_root, atomic_custom, core=core_with(), backup_root=tmp_path / "backups")
    qtbot.addWidget(dialog)
    dialog.open_path(UL_ZIP)
    wait_plan(qtbot, dialog)

    set_library(dialog, LIBRARY, fill=False)
    wait_plan(qtbot, dialog)
    assert not dialog._install_btn.isEnabled()
    assert "no description" in dialog._strip.text()

    type_description(dialog)
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    wait_plan(qtbot, dialog)
    assert dialog._install_btn.isEnabled()
