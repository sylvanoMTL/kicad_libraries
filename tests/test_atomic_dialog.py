"""Check Atomic Parts dialog over a synthetic Atomic_ tree (SCAN-03).

Every test writes only into tmp_path trees; none touches the real Custom/.
"""

from dataclasses import dataclass
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QLabel, QLineEdit, QPushButton

from customfixtures import write_atomic_custom, write_fake_kicad
from kicad_lib_manager import atomic_check, library_scanner
from kicad_lib_manager.library_scanner import scan_all
from kicad_lib_manager.models import FixSpec, ScanResult, Severity, SymbolEntry, SymbolLibrary
from kicad_lib_manager.widgets import atomic_check_dialog
from kicad_lib_manager.widgets.atomic_check_dialog import AtomicCheckDialog
from zipfixtures import STEP_BYTES

SYMBOL_REL = "Custom/Symbols/Atomic_Connector.kicad_sym"
ROLE = Qt.ItemDataRole.UserRole
NO_PROBLEMS = "No atomic rule problems in the last scan."


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


# ── fill-ins, value choice, selection controls, focus, empty state, warnings ──────────────


def _problem_items(dialog, symbol):
    """The violation and finding rows of one symbol, in order."""
    row = _symbol_row(dialog, symbol)
    return [row.child(i) for i in range(row.childCount())]


def _fill_item(dialog, symbol):
    return _problem_items(dialog, symbol)[0]


def _result_rows(item):
    """The rows under a problem row as (column 0 text, column 1 text, checked or None for a note)."""
    rows = []
    for i in range(item.childCount()):
        child = item.child(i)
        is_fix = isinstance(child.data(0, ROLE), FixSpec)
        checked = child.checkState(0) == Qt.CheckState.Checked if is_fix else None
        rows.append((child.text(0), child.text(1), checked))
    return rows


def _type(dialog, item, text):
    edit = dialog._problems.itemWidget(item, 1)
    assert isinstance(edit, QLineEdit)
    edit.setText(text)
    edit.editingFinished.emit()


def test_every_violation_and_every_finding_is_listed_once(setup):
    dialog = setup.make()

    listed = []
    for i in range(dialog._problems.topLevelItemCount()):
        row = dialog._problems.topLevelItem(i)
        listed += [row.child(j).text(0) for j in range(row.childCount())]
    entries = [entry for lib in setup.result.symbol_libs for entry in lib.symbols]
    expected = [v.text for e in entries for v in e.violations] + [f.text for e in entries for f in e.findings]

    assert sorted(listed) == sorted(expected)
    assert sum(len(e.violations) for e in entries) > 20
    assert sum(len(e.findings) for e in entries) == 4


def test_a_violation_with_no_fix_and_no_fill_says_so(setup):
    dialog = setup.make()

    rows = {
        dialog._problems.topLevelItem(i).text(0): dialog._problems.topLevelItem(i)
        for i in range(dialog._problems.topLevelItemCount())
    }
    assert rows["Atomic_Elsewhere / ELSEWHERE-1"].child(0).text(1) == "No one-click fix"


def test_deselect_all_and_select_all_move_every_fix_row(setup):
    dialog = setup.make()
    total = len(dialog.checked_specs())
    assert total > 5
    assert dialog._preview_btn.text() == f"Preview & apply {total} fixes"

    dialog._deselect_all_btn.click()

    assert dialog.checked_specs() == []
    assert dialog._preview_btn.text() == "Preview & apply 0 fixes"
    assert not dialog._preview_btn.isEnabled()

    dialog._select_all_btn.click()

    assert len(dialog.checked_specs()) == total
    assert dialog._preview_btn.isEnabled()


def test_a_typed_datasheet_is_checked_like_the_scan_and_becomes_one_fix_row(setup):
    dialog = setup.make()
    item = _fill_item(dialog, "DS-EMPTY")
    before = len(dialog.checked_specs())

    _type(dialog, item, "see website")

    assert not [row for row in _result_rows(item) if row[2] is not None]
    assert any("Datasheet is not a link or file path" in row[1] for row in _result_rows(item))
    assert len(dialog.checked_specs()) == before

    _type(dialog, item, "https://example.com/ds.pdf")

    assert _result_rows(item) == [('Datasheet → "https://example.com/ds.pdf"', "", True)]
    assert len(dialog.checked_specs()) == before + 1
    assert dialog._preview_btn.text() == f"Preview & apply {before + 1} fixes"

    _type(dialog, item, "https://example.com/other.pdf")

    assert _result_rows(item) == [('Datasheet → "https://example.com/other.pdf"', "", True)]
    assert len(dialog.checked_specs()) == before + 1

    _type(dialog, item, "")

    assert _result_rows(item) == []
    assert len(dialog.checked_specs()) == before


def test_a_typed_datasheet_is_previewed_and_written(setup, qtbot):
    dialog = setup.make()
    item = _fill_item(dialog, "DS-EMPTY")
    dialog._deselect_all_btn.click()
    _type(dialog, item, "https://example.com/ds.pdf")

    dialog._preview_btn.click()

    assert "https://example.com/ds.pdf" in dialog._preview_text.toPlainText()
    with qtbot.waitSignal(dialog.applied):
        dialog._apply_btn.click()
    assert '"https://example.com/ds.pdf"' in (setup.root / SYMBOL_REL).read_text(encoding="utf-8")


def test_a_typed_description_becomes_a_fix_row_and_blank_text_adds_none(setup):
    dialog = setup.make()
    item = _fill_item(dialog, "DESC-EMPTY")

    _type(dialog, item, "   ")
    assert _result_rows(item) == []

    _type(dialog, item, "Two row FFC connector")
    assert _result_rows(item) == [('Description → "Two row FFC connector"', "", True)]


def test_a_picked_3d_model_becomes_a_fix_row_and_cancelling_adds_nothing(setup, tmp_path):
    model = tmp_path / "picked.step"
    model.write_bytes(STEP_BYTES)
    picks = []
    answer = [model]

    def pick(parent):
        picks.append(parent)
        return answer[0]

    dialog = setup.make(pick_model=pick)
    item = _fill_item(dialog, "MODEL-MISSING")
    button = dialog._problems.itemWidget(item, 1)
    assert isinstance(button, QPushButton) and button.text() == "Choose 3D model..."

    button.click()

    assert picks == [dialog]
    assert _result_rows(item) == [('3D model → "picked.step"', "", True)]
    spec = item.child(0).data(0, ROLE)
    assert spec in dialog.checked_specs()
    assert spec.kind == "attach_model" and spec.params["source"] == str(model)

    answer[0] = None
    other = _fill_item(dialog, "MODEL-NONE")
    dialog._problems.itemWidget(other, 1).click()
    assert _result_rows(other) == []


def test_disagreeing_duplicate_values_offer_a_choice_of_the_values(setup):
    dialog = setup.make()
    item = _fill_item(dialog, "MFR-DUP-BAD")
    combo = dialog._problems.itemWidget(item, 1)
    assert isinstance(combo, QComboBox)
    assert [combo.itemText(i) for i in range(combo.count())] == [
        "Pick the value to keep", "Global Connector Technology", "Molex",
    ]
    assert _result_rows(item) == []

    combo.setCurrentIndex(2)

    rows = _result_rows(item)
    assert len(rows) == 1 and rows[0][2] is True and "Molex" in rows[0][0]
    spec = item.child(0).data(0, ROLE)
    assert spec in dialog.checked_specs()
    assert spec.kind == "merge_alias" and spec.params["value"] == "Molex"

    combo.setCurrentIndex(0)
    assert _result_rows(item) == []


def test_the_symbol_given_as_focus_is_the_current_row(setup):
    dialog = setup.make(focus=(SYMBOL_REL, "FFC-0.5-20"))

    assert dialog._problems.currentItem() is _symbol_row(dialog, "FFC-0.5-20")


def test_a_scan_without_problems_says_so_and_cannot_preview(setup):
    clean = ScanResult(symbol_libs=[
        SymbolLibrary(
            "Atomic_Clean", "Custom/Symbols/Atomic_Clean.kicad_sym", "Custom", atomic=True,
            symbols=[SymbolEntry("OK-1")],
        ),
    ])
    dialog = setup.make(result=clean)

    labels = [w for w in dialog.findChildren(QLabel) if w.text() == NO_PROBLEMS]
    assert len(labels) == 1 and not labels[0].isHidden()
    assert dialog._problems.isHidden()
    assert not dialog._preview_btn.isEnabled()


def _preview_with(setup, running):
    dialog = setup.make(running=running)
    dialog._deselect_all_btn.click()
    _fix_rows(_symbol_row(dialog, "FFC-0.5-20"))[0].setCheckState(0, Qt.CheckState.Checked)
    dialog._preview_btn.click()
    return dialog


def test_the_running_warning_shows_only_while_kicad_runs(setup):
    running = _preview_with(setup, lambda: ["kicad.exe"])
    assert not running._running_label.isHidden()
    assert "kicad.exe" in running._running_label.text()

    quiet = _preview_with(setup, lambda: [])
    assert quiet._running_label.isHidden()


def test_a_file_changed_after_the_preview_is_refused_and_left_alone(setup, qtbot):
    dialog = _preview_with(setup, _no_kicad)
    path = setup.root / SYMBOL_REL
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    changed = path.read_bytes()
    applied = []
    dialog.applied.connect(applied.append)

    with qtbot.waitSignal(dialog.issues_logged) as blocker:
        dialog._apply_btn.click()

    assert applied == []
    assert any("changed after the preview was built" in i.text for i in blocker.args[0])
    assert "changed after the preview was built" in dialog._issues_label.text()
    assert not dialog._apply_btn.isEnabled()
    assert path.read_bytes() == changed
    assert dialog.result() != QDialog.DialogCode.Accepted


def test_preview_never_applies_and_only_the_apply_button_does(setup, monkeypatch):
    calls = []
    real = atomic_check_dialog.apply_preview

    def recording(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(atomic_check_dialog, "apply_preview", recording)
    dialog = _preview_with(setup, _no_kicad)

    assert calls == []

    dialog._apply_btn.click()

    assert calls == [1]


def test_the_dialog_never_scans_or_runs_the_check(setup, monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("the dialog must work from the last scan")

    monkeypatch.setattr(atomic_check, "check_libraries", boom)
    monkeypatch.setattr(library_scanner, "scan_all", boom)

    dialog = _preview_with(setup, _no_kicad)
    dialog._apply_btn.click()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert '(property "Value" "FH12-20S-0.5SH"' in (setup.root / SYMBOL_REL).read_text(encoding="utf-8")


def test_no_widget_text_names_a_raw_field(setup):
    dialog = setup.make()
    texts = [w.text() for w in dialog.findChildren(QLabel)] + [w.text() for w in dialog.findChildren(QPushButton)]
    tree = dialog._problems
    for i in range(tree.topLevelItemCount()):
        stack = [tree.topLevelItem(i)]
        while stack:
            item = stack.pop()
            texts += [item.text(0), item.text(1), item.toolTip(0), item.toolTip(1)]
            widget = tree.itemWidget(item, 1)
            if isinstance(widget, QLineEdit):
                texts.append(widget.placeholderText())
            if isinstance(widget, QPushButton):
                texts.append(widget.text())
            if isinstance(widget, QComboBox):
                texts += [widget.itemText(n) for n in range(widget.count())]
            stack.extend(item.child(n) for n in range(item.childCount()))

    assert texts
    assert not [t for t in texts if "ki_" in t.casefold()]
