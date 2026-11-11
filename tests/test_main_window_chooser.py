"""Offscreen MainWindow tests for the "Set Up KiCad Chooser..." menu action (TBL-02, D-17).

Own fixture (tests do not import from other test modules): isolated QSettings, patched
REPO_ROOT / load_kicad_fp_dir / scan_all / kicad_running, and sync_kicad_chooser wrapped
to run against a synthetic KiCad config tree and backup folder in tmp_path, never the
owner's real %APPDATA% KiCad config.
"""

import json
import threading
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QMessageBox

from kicad_lib_manager import kicad_setup, main_window, settings
from kicad_lib_manager.library_scanner import ConfirmAnswer
from kicad_lib_manager.models import ScanResult


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path / "qsettings"),
    )
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


def _owner_session():
    return {"pinned_symbol_libs": [], "pinned_fp_libs": [], "remember_open_files": False}


def _owner_lib_tree():
    return {
        "columns": ["Item", "Description", "MANUFACTURER"],
        "column_widths": {"Item": 225, "Description": 445, "MANUFACTURER": 339},
    }


def _write_json(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_tables(dest: Path, sym_entries, fp_entries):
    dest.mkdir(parents=True, exist_ok=True)

    def _lines(entries):
        return "\n".join(
            f'  (lib (name "{n}")(type "KiCad")(uri "u")(options "")(descr ""))'
            for n in entries
        )

    (dest / "sym-lib-table").write_text(
        f"(sym_lib_table\n{_lines(sym_entries)}\n)\n", encoding="utf-8"
    )
    (dest / "fp-lib-table").write_text(
        f"(fp_lib_table\n{_lines(fp_entries)}\n)\n", encoding="utf-8"
    )


@pytest.fixture
def make_window(qtbot, monkeypatch, tmp_path):
    def make(sym_entries=("Atomic_Connector",), fp_entries=("Atomic_Footprints",), wait=True,
             no_dest=False):
        repo = tmp_path / "repo"
        repo.mkdir(parents=True, exist_ok=True)
        fp_dir = tmp_path / "kicad_fp"
        fp_dir.mkdir(exist_ok=True)

        # The Destination box defaults to REPO_ROOT when no history exists (D-18), so the
        # tables live directly in repo
        if not no_dest:
            _write_tables(repo, list(sym_entries), list(fp_entries))

        config_base = tmp_path / "kicad_cfg"
        repo_str = str(repo).replace("\\", "/")
        _write_json(config_base / "10.0" / "kicad_common.json", {
            "session": _owner_session(),
            "environment": {"vars": {"KICAD_LIB_GITHUB": repo_str}},
        })
        _write_json(config_base / "10.0" / "eeschema.json", {"lib_tree": _owner_lib_tree()})
        make.config_base = config_base
        make.backup_root = tmp_path / "backups"
        make.repo = repo

        def fake_scan(root, progress=None, kicad_fp_dir=None, *, skip=None, checking=None):
            return ScanResult()

        def fake_chooser(repo_root, dest_tables, **kwargs):
            kwargs.setdefault("running", lambda: [])
            return kicad_setup.sync_kicad_chooser(
                repo_root, dest_tables, **kwargs,
                config_base=config_base, backup_root=make.backup_root,
            )

        monkeypatch.setattr(main_window, "REPO_ROOT", repo)
        monkeypatch.setattr(main_window, "load_kicad_fp_dir", lambda: fp_dir)
        monkeypatch.setattr(main_window, "scan_all", fake_scan)
        monkeypatch.setattr(main_window, "sync_kicad_chooser", fake_chooser)
        w = main_window.MainWindow()
        qtbot.addWidget(w)
        if no_dest:
            w._dest_combo.setEditText("")
        if wait:
            qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
        return w

    make.repo = None
    make.config_base = None
    make.backup_root = None

    # Patched at fixture level so no test can block on a real modal dialog;
    # tests set make.answer to choose the reply and read make.questions for the calls
    def fake_question(window, *args):
        make.questions.append((window, *args))
        return make.answer

    monkeypatch.setattr(main_window.MainWindow, "_question", fake_question)
    make.answer = QMessageBox.StandardButton.Yes
    make.questions = []

    # The KiCad-open check runs on a worker thread: record where it ran and what it found.
    # make.running is the answer; make.running_queue (if not empty) gives one answer per check.
    make.running = []
    make.running_queue = []
    make.check_threads = []

    def fake_running():
        make.check_threads.append(threading.get_ident())
        if make.running_queue:
            return list(make.running_queue.pop(0))
        return list(make.running)

    # The chooser's KiCad-open dialog is replaced the same way as the Yes/No question, so no
    # test blocks on a real modal dialog
    make.kicad_answers = []
    make.kicad_calls = []

    def fake_ask_chooser_kicad_open(self, lines, names):
        make.kicad_calls.append((list(lines), list(names)))
        if make.kicad_answers:
            return make.kicad_answers.pop(0)
        return ConfirmAnswer.DECLINE

    monkeypatch.setattr(main_window, "kicad_running", fake_running)
    monkeypatch.setattr(main_window.MainWindow, "_ask_chooser_kicad_open", fake_ask_chooser_kicad_open)
    return make


def settle(qtbot, w):
    """Wait until the off-thread KiCad check and the chooser confirm are done."""
    qtbot.waitUntil(lambda: not w._chooser_busy, timeout=5000)


def test_setup_chooser_confirmed_writes_both_files(qtbot, make_window):
    w = make_window()
    make_window.answer = QMessageBox.StandardButton.Yes

    w._act_setup_chooser.trigger()
    settle(qtbot, w)

    common = json.loads(
        (make_window.config_base / "10.0" / "kicad_common.json").read_text(encoding="utf-8")
    )
    assert common["session"]["pinned_symbol_libs"] == ["Atomic_Connector"]
    assert common["session"]["pinned_fp_libs"] == ["Atomic_Footprints"]

    eeschema = json.loads(
        (make_window.config_base / "10.0" / "eeschema.json").read_text(encoding="utf-8")
    )
    assert "MPN" in eeschema["lib_tree"]["columns"]
    assert "Manufacturer" in eeschema["lib_tree"]["columns"]
    assert "MANUFACTURER" not in eeschema["lib_tree"]["columns"]

    assert len(make_window.questions) == 1
    _window, title, text = make_window.questions[0][0], make_window.questions[0][1], make_window.questions[0][2]
    assert title == "Set up KiCad's chooser?"
    for label in ("Pinned symbol libraries", "Pinned footprint libraries", "Symbol chooser columns"):
        assert label in text

    # The KiCad-open check ran off the GUI thread (REV-04 discipline)
    assert make_window.check_threads
    assert all(ident != threading.get_ident() for ident in make_window.check_threads)

    log_text = w._log._text.toPlainText()
    assert "Updated KiCad's settings file" in log_text
    assert "Updated KiCad's schematic editor settings" in log_text


def test_setup_chooser_menu_entry(qtbot, make_window):
    w = make_window()

    file_menu = w.menuBar().actions()[0].menu()
    assert w._act_setup_chooser in file_menu.actions()
    assert w._act_setup_chooser.text() == "Set Up KiCad &Chooser..."
    assert w._act_setup_chooser.shortcut() == QKeySequence("Ctrl+Shift+K")
    assert w._act_setup_chooser.toolTip() == (
        "Pin the Atomic_ libraries and show the MPN and Manufacturer columns in "
        "KiCad's symbol chooser"
    )

    w._set_scan_running(True)
    assert not w._act_setup_chooser.isEnabled()
    w._set_scan_running(False)
    assert w._act_setup_chooser.isEnabled()
