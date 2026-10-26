"""Check Atomic Parts dialog over a synthetic Atomic_ tree (SCAN-03).

Every test writes only into tmp_path trees; none touches the real Custom/.
"""

from dataclasses import dataclass
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from customfixtures import write_atomic_custom, write_fake_kicad
from kicad_lib_manager.library_scanner import scan_all
from kicad_lib_manager.models import FixSpec, Severity
from kicad_lib_manager.widgets.atomic_check_dialog import AtomicCheckDialog

SYMBOL_REL = "Custom/Symbols/Atomic_Connector.kicad_sym"
ROLE = Qt.ItemDataRole.UserRole


@dataclass
class Setup:
    root: Path
    result: object
    backup: Path
    make: object


def _no_kicad() -> list[str]:
    return []


@pytest.fixture
def setup(qtbot, tmp_path):
    root = tmp_path / "repo"
    write_atomic_custom(root)
    footprints, _ = write_fake_kicad(tmp_path)
    result = scan_all(root, kicad_fp_dir=footprints)

    def make(**kwargs) -> AtomicCheckDialog:
        kwargs.setdefault("backup_root", tmp_path / "bk")
        kwargs.setdefault("running", _no_kicad)
        dialog = AtomicCheckDialog(kwargs.pop("result", result), root, **kwargs)
        qtbot.addWidget(dialog)
        return dialog

    return Setup(root, result, tmp_path / "bk", make)


def _symbol_row(dialog, name):
    tree = dialog._problems
    for i in range(tree.topLevelItemCount()):
        item = tree.topLevelItem(i)
        if item.data(0, ROLE) == (SYMBOL_REL, name):
            return item
    raise AssertionError(f"no row for {name}")


def _fix_rows(symbol_row):
    rows = []
    for j in range(symbol_row.childCount()):
        problem = symbol_row.child(j)
        for k in range(problem.childCount()):
            if isinstance(problem.child(k).data(0, ROLE), FixSpec):
                rows.append(problem.child(k))
    return rows


def test_one_ticked_fix_goes_through_preview_and_apply(setup, qtbot):
    dialog = setup.make()
    row = _fix_rows(_symbol_row(dialog, "FFC-0.5-20"))[0]
    spec = row.data(0, ROLE)
    assert spec.kind == "value_to_mpn"
    assert row.checkState(0) == Qt.CheckState.Checked

    dialog._deselect_all_btn.click()
    row.setCheckState(0, Qt.CheckState.Checked)
    assert dialog.checked_specs() == [spec]
    dialog._preview_btn.click()

    assert dialog._stack.currentIndex() == 1
    text = dialog._preview_text.toPlainText()
    assert "FFC20" in text and "FH12-20S-0.5SH" in text
    before = (setup.root / SYMBOL_REL).read_text(encoding="utf-8")
    assert '(property "Value" "FFC20"' in before

    with qtbot.waitSignal(dialog.applied) as blocker:
        dialog._apply_btn.click()

    issues = blocker.args[0]
    assert [(i.code, i.severity) for i in issues] == [("atomic.fixed", Severity.SUCCESS)]
    after = (setup.root / SYMBOL_REL).read_text(encoding="utf-8")
    assert '(property "Value" "FH12-20S-0.5SH"' in after
    assert dialog.result() == QDialog.DialogCode.Accepted
