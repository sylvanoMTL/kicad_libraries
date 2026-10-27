"""The gate's reasons in the reason strip: a plain sentence, the control that fixes it, live clearing (D-25, LIB-07).

The form rows run without Qt on a fake plan; the dialog rows open the real UL sample or a synthetic package.
"""

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtTest import QTest
from test_import_dialog import core_with, frame_blocked, set_library, strip_links, wait_plan
from test_import_form import ERR, fake_plan, pairs, status

from kicad_lib_manager import settings
from kicad_lib_manager.importer.form import blocking_reasons
from kicad_lib_manager.models import Issue
from kicad_lib_manager.widgets.import_dialog import ImportDialog

REPO_ROOT = Path(__file__).resolve().parent.parent
UL_ZIP = REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"
LIBRARY = "Atomic_Battery_Management"


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qsettings"))
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


def atomic(rule: str, text: str) -> Issue:
    return Issue(ERR, f"install.atomic.{rule}", text)


# -- the tracer: "Type a Description" from the gate to a click that focuses the field --------------------


def test_a_missing_description_reads_type_a_description_and_clears_with_the_text():
    plan = fake_plan(issues=(atomic("description", "no description"),))

    assert pairs(blocking_reasons(status(), plan)) == [("Type a Description", "description")]
    assert pairs(blocking_reasons(status(description_text="x"), plan)) == []


def test_clicking_the_description_reason_focuses_the_field_and_typing_lifts_the_block(qtbot, atomic_custom, tmp_path):
    dialog = ImportDialog(atomic_custom.repo_root, atomic_custom, core=core_with(), backup_root=tmp_path / "backups")
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.open_path(UL_ZIP)
    wait_plan(qtbot, dialog)
    set_library(dialog, LIBRARY, fill=False)
    wait_plan(qtbot, dialog)

    links = strip_links(dialog)
    assert "Type a Description" in links
    assert not dialog._install_btn.isEnabled()
    assert frame_blocked(dialog, "description")

    dialog._on_reason_link(links["Type a Description"])
    assert dialog._field_edits["description"].hasFocus()

    # keyClicks types into the focused field; the reason and the frame go before the rebuild answers
    QTest.keyClicks(dialog._field_edits["description"], "Dual N-channel MOSFET")
    assert "Type a Description" not in strip_links(dialog)
    assert not frame_blocked(dialog, "description")
    qtbot.waitUntil(lambda: dialog._install_btn.isEnabled(), timeout=30000)
    assert dialog._install_btn.isEnabled()
