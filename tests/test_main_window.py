"""Offscreen MainWindow tests.

The harness never touches the owner's machine: QSettings is redirected into
tmp_path and scan, KiCad detection, REPO_ROOT and the KiCad config writer are
replaced before the window exists.
"""

import copy
import json
import os
import stat
import threading
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QMessageBox

from kicad_lib_manager import library_scanner, main_window, settings
from kicad_lib_manager.library_scanner import ConfirmAnswer
from kicad_lib_manager.widgets.log_panel import COLORS
from kicad_lib_manager.models import (
    FootprintLibrary, FootprintRef, Issue, ScanResult, Severity, SymbolEntry, SymbolLibrary,
    Violation,
)


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path / "qsettings"),
    )
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


@pytest.fixture
def make_window(qtbot, monkeypatch, tmp_path):
    def make(results, repo=None, empty_config=False, wait=True):
        repo = Path(repo) if repo is not None else tmp_path / "repo"
        repo.mkdir(parents=True, exist_ok=True)
        fp_dir = tmp_path / "kicad_fp"
        fp_dir.mkdir(exist_ok=True)
        queue = list(results)
        calls = []

        def fake_scan(root, progress=None, kicad_fp_dir=None, *, skip=None, checking=None):
            calls.append((root, kicad_fp_dir))
            # A gated item reads the hooks to play the part of the real scan
            make.hooks = (skip, checking)
            item = queue.pop(0) if len(queue) > 1 else queue[0]
            return item() if callable(item) else item

        # The real sync runs, but only against a synthetic KiCad tree and backup folder in tmp_path
        config_base = tmp_path / "kicad_cfg"
        config_base.mkdir(exist_ok=True)
        config_file = config_base / "10.0" / "kicad_common.json"
        if not empty_config:
            config_file.parent.mkdir(exist_ok=True)
            config_file.write_text('{"environment": {"vars": null}}\n', encoding="utf-8")

        # A caller passing config_base or backup_root itself makes a duplicate-keyword
        # TypeError here, so nothing can reach the real KiCad config. The window passes its
        # own running (the names its worker found); a direct call gets "KiCad is closed".
        def fake_sync(repo_root, **kwargs):
            kwargs.setdefault("running", lambda: [])
            return library_scanner.sync_kicad_path_vars(
                repo_root,
                **kwargs,
                config_base=config_base,
                backup_root=tmp_path / "backups",
            )

        monkeypatch.setattr(main_window, "REPO_ROOT", repo)
        monkeypatch.setattr(main_window, "load_kicad_fp_dir", lambda: fp_dir)
        monkeypatch.setattr(main_window, "scan_all", fake_scan)
        monkeypatch.setattr(main_window, "sync_kicad_path_vars", fake_sync)
        make.calls = calls
        make.repo = repo
        make.config_file = config_file
        w = main_window.MainWindow()
        qtbot.addWidget(w)
        if wait:
            qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
        return w

    make.calls = []
    make.repo = None
    make.hooks = None

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

    # The KiCad-open dialog is replaced the same way as the Yes/No question, so no test blocks
    make.kicad_answers = []
    make.kicad_calls = []

    def fake_ask_kicad_open(self, changes, names):
        make.kicad_calls.append((changes, list(names)))
        if make.kicad_answers:
            return make.kicad_answers.pop(0)
        return ConfirmAnswer.DECLINE

    monkeypatch.setattr(main_window, "kicad_running", fake_running)
    monkeypatch.setattr(main_window.MainWindow, "_ask_kicad_open", fake_ask_kicad_open)
    return make


def settle(qtbot, w):
    """Wait until the off-thread KiCad check and the path-variable question are done."""
    qtbot.waitUntil(lambda: not w._path_var_busy, timeout=5000)


def test_generate_splices_table_and_logs_issues(qtbot, make_window):
    scan = ScanResult(
        symbol_libs=[SymbolLibrary("New", "Custom/Symbols/New.kicad_sym", "Custom")],
        footprint_libs=[FootprintLibrary("NewFP", "Custom/Footprints/NewFP.pretty", "Custom")],
    )
    w = make_window([scan])
    repo = make_window.repo

    original = (
        b"(sym_lib_table\r\n"
        b"  (version 7)\r\n"
        b'  (lib (name "Ext")(type "KiCad")(uri "C:/libs/Ext.kicad_sym")'
        b'(options "")(descr "hand made"))\r\n'
        b'  (lib (name "Old")(type "KiCad")'
        b'(uri "${KICAD_LIB_GITHUB}/Custom/Symbols/Old.kicad_sym")'
        b'(options "")(descr ""))\r\n'
        b")\r\n"
    )
    (repo / "sym-lib-table").write_bytes(original)

    scan.symbol_libs[0].selected = True
    scan.footprint_libs[0].selected = True
    w._on_generate()
    settle(qtbot, w)

    data = (repo / "sym-lib-table").read_bytes()
    assert b"  (version 7)\r\n" in data
    assert (
        b'  (lib (name "Ext")(type "KiCad")(uri "C:/libs/Ext.kicad_sym")'
        b'(options "")(descr "hand made"))\r\n'
    ) in data
    assert b"Old.kicad_sym" not in data
    assert (
        b'(lib (name "New")(type "KiCad")'
        b'(uri "${KICAD_LIB_GITHUB}/Custom/Symbols/New.kicad_sym")'
        b'(options "")(descr "Custom: New"))'
    ) in data
    assert b"\n" not in data.replace(b"\r\n", b"")

    assert (repo / "sym-lib-table_backup_1").read_bytes() == original
    fp_data = (repo / "fp-lib-table").read_bytes()
    assert b'(name "NewFP")' in fp_data

    log_text = w._log._text.toPlainText()
    assert "Written sym-lib-table" in log_text
    assert "Written fp-lib-table" in log_text
    assert "#007700" in w._log._text.toHtml()


def test_generate_writes_atomic_description(qtbot, make_window):
    """TBL-01/D-20: Generate reads KiCad's stock description for an Atomic_ stem."""
    scan = ScanResult(
        symbol_libs=[SymbolLibrary(
            "Atomic_Connector", "Custom/Symbols/Atomic_Connector.kicad_sym", "Custom",
            selected=True,
        )],
        footprint_libs=[],
    )
    w = make_window([scan])
    repo = make_window.repo

    template = w._kicad_fp_dir.parent / "template" / "sym-lib-table"
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text(
        "(sym_lib_table\n"
        '  (lib (name "Connector")(type "KiCad")(uri "x")(options "")'
        '(descr "Connector symbols (Examples: USB)"))\n'
        ")\n",
        encoding="utf-8",
    )

    w._on_generate()
    settle(qtbot, w)

    data = (repo / "sym-lib-table").read_text(encoding="utf-8")
    assert '(descr "Atomic parts: Connector symbols (Examples: USB)")' in data


def _managed_table(tag, entries):
    lines = [f"({tag}", "  (version 7)"]
    for name, rel in entries:
        lines.append(
            f'  (lib (name "{name}")(type "KiCad")'
            f'(uri "${{KICAD_LIB_GITHUB}}/{rel}")(options "")(descr ""))'
        )
    lines.append(")")
    return ("\n".join(lines) + "\n").encode("utf-8")


def test_startup_preselection_matches_by_rel_path_not_nickname(make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sym-lib-table").write_bytes(
        _managed_table("sym_lib_table", [("Same", "Custom/Symbols/Same.kicad_sym")])
    )
    (repo / "fp-lib-table").write_bytes(
        _managed_table("fp_lib_table", [("Solo", "Custom/Footprints/Solo.pretty")])
    )
    scan = ScanResult(
        symbol_libs=[
            SymbolLibrary(
                "Same", "Custom/Symbols/Same.kicad_sym", "Custom",
                footprint_refs=[FootprintRef("Solo", "X", True)],
            ),
            SymbolLibrary(
                "Same", "WurthElektronik/KiCad-Library/symbols/Same.kicad_sym",
                "WurthElektronik",
            ),
        ],
        footprint_libs=[FootprintLibrary("Solo", "Custom/Footprints/Solo.pretty", "Custom")],
    )

    w = make_window([scan], repo=repo)

    custom_same, wurth_same = w._scan_result.symbol_libs
    assert custom_same.selected is True
    assert wurth_same.selected is False
    assert w._scan_result.footprint_libs[0].selected is True


def test_destination_change_only_logs_and_never_on_keystrokes(make_window, tmp_path):
    scan = ScanResult(
        symbol_libs=[SymbolLibrary("A", "Custom/Symbols/A.kicad_sym", "Custom", selected=True)],
        footprint_libs=[FootprintLibrary("B", "Custom/Footprints/B.pretty", "Custom")],
    )
    w = make_window([scan])
    other = tmp_path / "other"
    other.mkdir()
    (other / "sym-lib-table").write_bytes(
        _managed_table("sym_lib_table", [("A", "Custom/Symbols/A.kicad_sym")])
    )
    marker = f"Existing sym-lib-table found at {other}"

    w._dest_combo.setEditText(str(other))
    assert marker not in w._log._text.toPlainText()

    w._dest_combo.lineEdit().editingFinished.emit()
    assert w._log._text.toPlainText().count(marker) == 1
    assert [lib.selected for lib in scan.symbol_libs] == [True]
    assert [lib.selected for lib in scan.footprint_libs] == [False]


NO_DEST = "No destination folder set; library tables not changed"


@pytest.mark.parametrize("blank", ["", "  "], ids=["empty", "spaces"])
def test_generate_blank_destination_writes_nothing(make_window, tmp_path, monkeypatch, blank):
    w = make_window([_new_lib_scan()])
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    history_before = settings.load_dest_history()
    w._dest_combo.setEditText(blank)

    w._on_generate()

    assert os.listdir(cwd) == []
    assert NO_DEST in w._log._text.toPlainText()
    assert make_window.questions == []
    assert not (tmp_path / "backups").exists()
    history = settings.load_dest_history()
    assert history == history_before
    assert not any(not entry.strip() for entry in history)


@pytest.mark.parametrize("blank", ["", "   "], ids=["empty", "spaces"])
def test_blank_destination_never_reads_the_working_directory(
    qtbot, make_window, tmp_path, monkeypatch, blank
):
    scan = ScanResult(
        symbol_libs=[SymbolLibrary("A", "Custom/Symbols/A.kicad_sym", "Custom")],
        footprint_libs=[FootprintLibrary("B", "Custom/Footprints/B.pretty", "Custom")],
    )
    w = make_window([scan])
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "sym-lib-table").write_bytes(
        _managed_table("sym_lib_table", [("A", "Custom/Symbols/A.kicad_sym")])
    )
    monkeypatch.chdir(cwd)
    w._dest_combo.setEditText(blank)
    before = w._log._text.toPlainText()

    w._log_existing_tables(w._dest_path())
    w._on_dest_changed()
    w._apply_existing_selection(scan)
    w._on_rescan()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    assert w._dest_path() is None
    assert "Existing sym-lib-table found" not in w._log._text.toPlainText()[len(before):]
    assert "Pre-selected" not in w._log._text.toPlainText()[len(before):]
    assert [lib.selected for lib in scan.symbol_libs] == [False]
    assert [lib.selected for lib in scan.footprint_libs] == [False]
    assert sorted(os.listdir(cwd)) == ["sym-lib-table"]


def _new_lib_scan():
    return ScanResult(
        symbol_libs=[SymbolLibrary("New", "Custom/Symbols/New.kicad_sym", "Custom", selected=True)],
        footprint_libs=[
            FootprintLibrary("NewFP", "Custom/Footprints/NewFP.pretty", "Custom", selected=True)
        ],
    )


def test_generate_with_read_only_sym_table_logs_one_error_and_finishes(
    make_window, qtbot
):
    w = make_window([_new_lib_scan()])
    repo = make_window.repo
    sym_table = repo / "sym-lib-table"
    # The table lacks "New", so the regenerated text differs and a write is attempted
    sym_table.write_bytes(_managed_table("sym_lib_table", []))
    os.chmod(sym_table, stat.S_IREAD)
    try:
        with qtbot.captureExceptions() as exceptions:
            w._on_generate()
            settle(qtbot, w)
        assert exceptions == []
    finally:
        os.chmod(sym_table, stat.S_IREAD | stat.S_IWRITE)

    lines = w._log._text.toPlainText().splitlines()
    assert len([ln for ln in lines if "Could not write sym-lib-table" in ln]) == 1
    assert (repo / "fp-lib-table").exists()
    config = json.loads(make_window.config_file.read_text(encoding="utf-8"))
    assert config["environment"]["vars"]["KICAD_LIB_GITHUB"] == str(repo).replace("\\", "/")
    assert any("Updated" in ln for ln in lines)
    assert w._dest_combo.itemText(0) == str(repo)


def test_generate_declined_leaves_kicad_config_untouched(qtbot, make_window, tmp_path):
    make_window.answer = QMessageBox.StandardButton.No
    w = make_window([_new_lib_scan()])
    repo = make_window.repo
    config_before = make_window.config_file.read_bytes()

    w._on_generate()
    settle(qtbot, w)

    assert (repo / "sym-lib-table").exists()
    assert (repo / "fp-lib-table").exists()
    assert len(make_window.questions) == 1
    assert make_window.config_file.read_bytes() == config_before
    assert not (tmp_path / "backups").exists()
    assert "KiCad path variables left unchanged" in w._log._text.toPlainText()


def test_generate_from_worktree_refuses_without_asking(qtbot, make_window, tmp_path):
    w = make_window([_new_lib_scan()])
    repo = make_window.repo
    (repo / ".git").write_text("gitdir: elsewhere\n")
    config_before = make_window.config_file.read_bytes()

    w._on_generate()
    settle(qtbot, w)

    assert make_window.questions == []
    assert make_window.config_file.read_bytes() == config_before
    assert not (tmp_path / "backups").exists()
    assert (repo / "sym-lib-table").exists()
    assert (repo / "fp-lib-table").exists()
    html = w._log._text.toHtml()
    line = next(ln for ln in html.splitlines() if "git worktree" in ln)
    assert COLORS["warning"].lower() in line.lower()


def test_generate_confirmed_shows_old_and_new_values(qtbot, make_window):
    w = make_window([_new_lib_scan()])
    repo_str = str(make_window.repo).replace("\\", "/")

    w._on_generate()
    settle(qtbot, w)

    (args,) = make_window.questions
    assert args[0] is w
    assert f"KICAD_LIB_GITHUB: (not set) -> {repo_str}" in args[2]
    assert f"CUSTOM_3DMODEL_DIR: (not set) -> {repo_str}/Custom/3DModels" in args[2]
    assert args[4] == QMessageBox.StandardButton.No
    config = json.loads(make_window.config_file.read_text(encoding="utf-8"))
    assert config["environment"]["vars"]["KICAD_LIB_GITHUB"] == repo_str


def test_generate_without_kicad_config_warns_and_still_writes_both_tables(qtbot, make_window):
    w = make_window([_new_lib_scan()], empty_config=True)
    repo = make_window.repo

    w._on_generate()
    settle(qtbot, w)

    text = w._log._text.toPlainText()
    assert text.count("Could not find KiCad config directory") == 1
    html = w._log._text.toHtml()
    line = next(ln for ln in html.splitlines() if "Could not find KiCad config directory" in ln)
    assert COLORS["warning"].lower() in line.lower()
    assert (repo / "sym-lib-table").exists()
    assert (repo / "fp-lib-table").exists()


def test_generate_with_kicad_open_change_anyway_writes_and_warns(qtbot, make_window):
    make_window.running = ["eeschema", "kicad"]
    make_window.kicad_answers = [ConfirmAnswer.WRITE]
    w = make_window([_new_lib_scan()])
    repo_str = str(make_window.repo).replace("\\", "/")

    w._on_generate()
    settle(qtbot, w)

    config = json.loads(make_window.config_file.read_text(encoding="utf-8"))
    assert config["environment"]["vars"]["KICAD_LIB_GITHUB"] == repo_str
    assert config["environment"]["vars"]["CUSTOM_3DMODEL_DIR"] == f"{repo_str}/Custom/3DModels"
    lines = [ln for ln in w._log._text.toPlainText().splitlines() if "(eeschema, kicad)" in ln]
    assert len(lines) == 1
    assert "eeschema, kicad" in lines[0]
    ((changes, names),) = make_window.kicad_calls
    assert names == ["eeschema", "kicad"]
    assert [var for var, _old, _new in changes] == ["KICAD_LIB_GITHUB", "CUSTOM_3DMODEL_DIR"]
    assert make_window.questions == []
    assert len(make_window.check_threads) == 1
    assert make_window.check_threads[0] != threading.main_thread().ident


def _kicad_open_text(w):
    return w._log._text.toPlainText()


def test_kicad_open_retry_then_closed_asks_yes_no(qtbot, make_window):
    make_window.running_queue = [["kicad"], []]
    make_window.kicad_answers = [ConfirmAnswer.RETRY]
    w = make_window([_new_lib_scan()])
    repo_str = str(make_window.repo).replace("\\", "/")

    w._on_generate()
    settle(qtbot, w)

    assert len(make_window.kicad_calls) == 1
    assert len(make_window.questions) == 1
    assert len(make_window.check_threads) == 2
    config = json.loads(make_window.config_file.read_text(encoding="utf-8"))
    assert config["environment"]["vars"]["KICAD_LIB_GITHUB"] == repo_str
    assert "KiCad is open" not in _kicad_open_text(w)


def test_kicad_open_retry_still_open_asks_again(qtbot, make_window):
    make_window.running = ["kicad"]
    make_window.kicad_answers = [ConfirmAnswer.RETRY, ConfirmAnswer.DECLINE]
    w = make_window([_new_lib_scan()])
    config_before = make_window.config_file.read_bytes()

    w._on_generate()
    settle(qtbot, w)

    assert len(make_window.kicad_calls) == 2
    assert make_window.questions == []
    assert make_window.config_file.read_bytes() == config_before
    assert "KiCad path variables left unchanged (change declined)" in _kicad_open_text(w)


def test_kicad_open_not_now_writes_nothing(qtbot, make_window, tmp_path):
    make_window.running = ["kicad"]
    make_window.kicad_answers = [ConfirmAnswer.DECLINE]
    w = make_window([_new_lib_scan()])
    config_before = make_window.config_file.read_bytes()

    w._on_generate()
    settle(qtbot, w)

    assert len(make_window.kicad_calls) == 1
    assert make_window.config_file.read_bytes() == config_before
    assert not (tmp_path / "backups").exists()


def test_second_generate_starts_no_second_check(qtbot, make_window, monkeypatch):
    w = make_window([_new_lib_scan()])
    gate = threading.Event()

    def gated_running():
        make_window.check_threads.append(threading.get_ident())
        gate.wait(5)
        return []

    monkeypatch.setattr(main_window, "kicad_running", gated_running)
    try:
        w._on_generate()
        w._on_generate()
    finally:
        gate.set()
    settle(qtbot, w)

    assert len(make_window.check_threads) == 1
    assert len(make_window.questions) == 1


def test_close_waits_for_check_without_blocking(qtbot, make_window, monkeypatch):
    w = make_window([_new_lib_scan()])
    w.show()
    gate = threading.Event()

    def gated_running():
        gate.wait(5)
        return []

    monkeypatch.setattr(main_window, "kicad_running", gated_running)
    try:
        w._on_generate()
        w.close()
        # The check is still held: the window stays, nothing was asked
        assert w.isVisible()
        assert make_window.questions == []
    finally:
        gate.set()
    qtbot.waitUntil(lambda: not w.isVisible(), timeout=5000)

    assert make_window.questions == []
    assert make_window.kicad_calls == []


def test_kicad_open_box_texts_and_buttons(make_window):
    w = make_window([_new_lib_scan()])
    changes = [
        ("KICAD_LIB_GITHUB", None, "C:/repo"),
        ("CUSTOM_3DMODEL_DIR", "D:/old", "C:/repo/Custom/3DModels"),
    ]

    box, answers = w._kicad_open_box(changes, ["eeschema", "kicad"])

    text = box.text()
    assert "KiCad is open (eeschema, kicad)" in text
    assert "Close KiCad, then press Retry" in text
    assert "These KiCad path variables in KiCad's settings file would change:" in text
    assert "kicad_common" not in text
    assert "KICAD_LIB_GITHUB: (not set) -> C:/repo" in text
    assert "CUSTOM_3DMODEL_DIR: D:/old -> C:/repo/Custom/3DModels" in text
    # The platform orders the buttons by role, so compare by text
    assert {b.text() for b in box.buttons()} == {"Retry", "Change anyway", "Not now"}
    assert box.defaultButton().text() == "Retry"
    assert {b.text(): answer for b, answer in answers.items()} == {
        "Retry": ConfirmAnswer.RETRY,
        "Change anyway": ConfirmAnswer.WRITE,
        "Not now": ConfirmAnswer.DECLINE,
    }
    assert box.escapeButton().text() == "Not now"
    # Window-modal: it blocks the main window only, so the User Guide stays usable (G-12-22)
    assert box.windowModality() == Qt.WindowModality.WindowModal


def test_path_var_question_names_the_settings_file(make_window):
    w = make_window([_new_lib_scan()])
    make_window.questions.clear()
    make_window.answer = QMessageBox.StandardButton.No

    assert w._confirm_path_var_changes([("KICAD_LIB_GITHUB", None, "C:/repo")]) is False

    text = make_window.questions[-1][2]
    assert "These KiCad path variables in KiCad's settings file would change:" in text
    assert "KICAD_LIB_GITHUB: (not set) -> C:/repo" in text
    assert "kicad_common" not in text


# ── Scan funnel and busy guard (HARD-05) ──────────────────────────────────


def _gated(result, gate):
    """A fake scan that blocks until gate is set (5 s cap so a broken guard fails)."""
    def run():
        gate.wait(5)
        return result
    return run


def _raising(message):
    def run():
        raise RuntimeError(message)
    return run


def _scan_controls(w):
    return [
        w._act_rescan, w._act_set_kicad_path, w._act_generate,
        w._rescan_btn, w._generate_btn,
    ]


def _log_text(w):
    return w._log._text.toPlainText()


def test_busy_rescans_are_dropped_and_controls_disabled(make_window, qtbot):
    gate = threading.Event()
    w = make_window([_gated(ScanResult(), gate)], wait=False)
    calls = make_window.calls
    try:
        qtbot.waitUntil(lambda: len(calls) == 1, timeout=5000)
        assert not any(c.isEnabled() for c in _scan_controls(w))

        w._on_rescan()
        w._on_rescan()

        assert len(calls) == 1
        assert _log_text(w).count("already running") == 2
    finally:
        gate.set()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    assert all(c.isEnabled() for c in _scan_controls(w))
    # Dropped requests are never replayed after the scan ends
    qtbot.wait(100)
    assert len(calls) == 1


def test_busy_state_clears_then_one_rescan_starts_exactly_one_scan(make_window, qtbot):
    gate = threading.Event()
    w = make_window([_gated(ScanResult(), gate)], wait=False)
    calls = make_window.calls
    gate.set()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    assert len(calls) == 1

    w._on_rescan()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    assert len(calls) == 2


def test_busy_set_kicad_path_opens_no_dialog_and_starts_no_scan(
    make_window, qtbot, monkeypatch
):
    gate = threading.Event()
    w = make_window([_gated(ScanResult(), gate)], wait=False)
    calls = make_window.calls
    dialogs = []
    monkeypatch.setattr(
        main_window.QFileDialog, "getExistingDirectory",
        lambda *a, **k: dialogs.append(a) or "",
    )
    try:
        qtbot.waitUntil(lambda: len(calls) == 1, timeout=5000)
        w._on_set_kicad_path()
        assert dialogs == []
        assert len(calls) == 1
        assert "already running" in _log_text(w)
    finally:
        gate.set()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)


def test_scan_error_clears_busy_state(make_window, qtbot):
    w = make_window([ScanResult(), _raising("boom")])

    w._on_rescan()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    assert "Scan error: boom" in _log_text(w)
    assert all(c.isEnabled() for c in _scan_controls(w))


def test_busy_state_clears_after_empty_scan_result(make_window):
    w = make_window([ScanResult()])

    assert "Found 0 symbol libraries" in _log_text(w)
    assert w._worker is None
    assert all(c.isEnabled() for c in _scan_controls(w))


def test_rescan_with_populate_raising_still_clears_busy_state(
    make_window, qtbot, monkeypatch
):
    w = make_window([ScanResult()])

    def boom(_result):
        raise RuntimeError("populate boom")

    monkeypatch.setattr(w._tree, "populate", boom)
    with qtbot.captureExceptions() as exceptions:
        w._on_rescan()
        qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    assert any("populate boom" in str(exc[1]) for exc in exceptions)
    assert all(c.isEnabled() for c in _scan_controls(w))


def test_scan_issue_is_logged_in_its_severity_colour(make_window):
    scan = ScanResult(issues=[Issue(Severity.WARNING, "scan.test", "[x] warn")])

    w = make_window([scan])

    assert "[x] warn" in _log_text(w)
    assert "No warnings." not in _log_text(w)
    html = w._log._text.toHtml()
    line = next(ln for ln in html.splitlines() if "[x] warn" in ln)
    assert COLORS["warning"].lower() in line.lower()


def test_close_while_scanning_waits_for_worker(make_window):
    gate = threading.Event()
    w = make_window([_gated(ScanResult(), gate)], wait=False)
    worker = w._worker
    timer = threading.Timer(0.2, gate.set)
    timer.start()
    try:
        w.close()
        assert not worker.isRunning()
    finally:
        gate.set()
        timer.cancel()
        worker.wait(5000)


# ── Selection policy: startup pre-selection vs rescan re-apply (D-01, D-04, D-05) ──

WURTH_SYM = "WurthElektronik/KiCad-Library/symbols/{}.kicad_sym"
WURTH_FP = "WurthElektronik/KiCad-Library/footprints/{}.pretty"


def _sym(nickname, source="Custom", refs=(), peers=(), selected=False):
    base = "Custom/Symbols/{}.kicad_sym" if source == "Custom" else WURTH_SYM
    return SymbolLibrary(
        nickname, base.format(nickname), source,
        footprint_refs=[FootprintRef(*r) for r in refs],
        selected=selected, collision_peers=list(peers),
    )


def _fp(nickname, source="Custom", peers=(), selected=False):
    base = "Custom/Footprints/{}.pretty" if source == "Custom" else WURTH_FP
    return FootprintLibrary(
        nickname, base.format(nickname), source,
        selected=selected, collision_peers=list(peers),
    )


def _write_tables(dest, sym_paths=None, fp_paths=None):
    """Write managed sym-lib-table / fp-lib-table files holding the given rel_paths."""
    for file_name, tag, paths in (
        ("sym-lib-table", "sym_lib_table", sym_paths),
        ("fp-lib-table", "fp_lib_table", fp_paths),
    ):
        if paths is None:
            continue
        entries = [(Path(p).stem, p) for p in paths]
        (dest / file_name).write_bytes(_managed_table(tag, entries))


def _selected(libs):
    return {lib.rel_path for lib in libs if lib.selected}


def _rescan_and_wait(w, qtbot):
    w._on_rescan()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)


def _assert_one_selected_per_nickname(w):
    for libs in (w._scan_result.symbol_libs, w._scan_result.footprint_libs):
        by_nickname = {}
        for lib in libs:
            if lib.selected:
                by_nickname.setdefault(lib.nickname, []).append(lib.rel_path)
        assert all(len(paths) == 1 for paths in by_nickname.values()), by_nickname


def _check(item, on=True):
    item.setCheckState(
        0, Qt.CheckState.Checked if on else Qt.CheckState.Unchecked
    )


def test_startup_preselects_tables_including_unreferenced_footprint(
    make_window, tmp_path
):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_tables(repo, ["Custom/Symbols/S.kicad_sym"], ["Custom/Footprints/Solo.pretty"])

    w = make_window([ScanResult(symbol_libs=[_sym("S")], footprint_libs=[_fp("Solo")])], repo=repo)

    assert _selected(w._scan_result.symbol_libs) == {"Custom/Symbols/S.kicad_sym"}
    assert _selected(w._scan_result.footprint_libs) == {"Custom/Footprints/Solo.pretty"}
    solo_item = w._tree._fp_items["Custom/Footprints/Solo.pretty"]
    assert solo_item.checkState(0) == Qt.CheckState.Checked
    _assert_one_selected_per_nickname(w)


def _selection_scan_one():
    return ScanResult(
        symbol_libs=[_sym("S"), _sym("S2"), _sym("Gone")],
        footprint_libs=[_fp("Solo2")],
    )


def _selection_scan_two():
    return ScanResult(
        symbol_libs=[_sym("S"), _sym("S2"), _sym("New")],
        footprint_libs=[_fp("Solo2")],
    )


def test_rescan_keeps_selection_by_rel_path_and_ignores_tables(
    make_window, qtbot, tmp_path
):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_tables(
        repo, ["Custom/Symbols/S.kicad_sym", "Custom/Symbols/Gone.kicad_sym"], []
    )
    w = make_window([_selection_scan_one, _selection_scan_two], repo=repo)
    assert _selected(w._scan_result.symbol_libs) == {
        "Custom/Symbols/S.kicad_sym", "Custom/Symbols/Gone.kicad_sym",
    }

    _check(w._tree._sym_items["Custom/Symbols/S2.kicad_sym"])
    _check(w._tree._sym_items["Custom/Symbols/S.kicad_sym"], on=False)
    _check(w._tree._fp_items["Custom/Footprints/Solo2.pretty"])
    # A changed table must not matter any more: it would select New if consulted
    _write_tables(
        repo, ["Custom/Symbols/New.kicad_sym"], ["Custom/Footprints/Other.pretty"]
    )

    _rescan_and_wait(w, qtbot)

    result = w._scan_result
    assert _selected(result.symbol_libs) == {"Custom/Symbols/S2.kicad_sym"}
    assert _selected(result.footprint_libs) == {"Custom/Footprints/Solo2.pretty"}
    new_item = w._tree._sym_items["Custom/Symbols/New.kicad_sym"]
    assert new_item.checkState(0) == Qt.CheckState.Unchecked
    text = _log_text(w)
    assert "Kept 2 selections" in text
    dropped = next(ln for ln in text.splitlines() if "Dropped 1 selections" in ln)
    assert "Custom/Symbols/Gone.kicad_sym" in dropped
    _assert_one_selected_per_nickname(w)


def _collision_scan():
    custom_path = "Custom/Symbols/Same.kicad_sym"
    wurth_path = WURTH_SYM.format("Same")
    return ScanResult(symbol_libs=[
        _sym("Same", peers=[wurth_path]),
        _sym("Same", source="WurthElektronik", peers=[custom_path]),
    ])


def test_rescan_keeps_the_chosen_collision_peer(make_window, qtbot):
    w = make_window([_collision_scan])
    wurth_path = WURTH_SYM.format("Same")
    assert _selected(w._scan_result.symbol_libs) == set()

    _check(w._tree._sym_items[wurth_path])
    _rescan_and_wait(w, qtbot)

    assert _selected(w._scan_result.symbol_libs) == {wurth_path}
    assert w._tree._sym_items[wurth_path].checkState(0) == Qt.CheckState.Checked
    custom_item = w._tree._sym_items["Custom/Symbols/Same.kicad_sym"]
    assert custom_item.checkState(0) == Qt.CheckState.Unchecked
    _assert_one_selected_per_nickname(w)


def test_set_kicad_path_rescan_reapplies_selection(
    make_window, qtbot, monkeypatch, tmp_path
):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_tables(repo, ["Custom/Symbols/S.kicad_sym"], [])
    folder = tmp_path / "new_kicad_fp"
    folder.mkdir()
    monkeypatch.setattr(
        main_window.QFileDialog, "getExistingDirectory", lambda *a, **k: str(folder)
    )
    w = make_window([_selection_scan_one, _selection_scan_two], repo=repo)
    _check(w._tree._sym_items["Custom/Symbols/S2.kicad_sym"])
    _check(w._tree._sym_items["Custom/Symbols/S.kicad_sym"], on=False)

    w._on_set_kicad_path()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    assert make_window.calls[-1][1] == folder
    assert _selected(w._scan_result.symbol_libs) == {"Custom/Symbols/S2.kicad_sym"}
    _assert_one_selected_per_nickname(w)


def _both_peers_in_tables_scan():
    same_c, same_w = "Custom/Symbols/Same.kicad_sym", WURTH_SYM.format("Same")
    dup_c, dup_w = "Custom/Footprints/Dup.pretty", WURTH_FP.format("Dup")
    return ScanResult(
        symbol_libs=[
            _sym("Same", peers=[same_w]),
            _sym("Same", source="WurthElektronik", peers=[same_c]),
        ],
        footprint_libs=[
            _fp("Dup", peers=[dup_w]),
            _fp("Dup", source="WurthElektronik", peers=[dup_c]),
        ],
    )


def test_startup_collision_trim_keeps_one_peer_and_warns_once_per_group(
    make_window, tmp_path
):
    repo = tmp_path / "repo"
    repo.mkdir()
    same_c, same_w = "Custom/Symbols/Same.kicad_sym", WURTH_SYM.format("Same")
    dup_c, dup_w = "Custom/Footprints/Dup.pretty", WURTH_FP.format("Dup")
    # A table written before Phase 2 can hold both peers under one nickname
    (repo / "sym-lib-table").write_bytes(
        _managed_table("sym_lib_table", [("Same", same_c), ("Same", same_w)])
    )
    (repo / "fp-lib-table").write_bytes(
        _managed_table("fp_lib_table", [("Dup", dup_c), ("Dup", dup_w)])
    )

    w = make_window([_both_peers_in_tables_scan], repo=repo)

    assert _selected(w._scan_result.symbol_libs) == {same_c}
    assert _selected(w._scan_result.footprint_libs) == {dup_c}
    assert w._tree._sym_items[same_w].checkState(0) == Qt.CheckState.Unchecked
    assert w._tree._fp_items[dup_w].checkState(0) == Qt.CheckState.Unchecked
    lines = [
        ln for ln in _log_text(w).splitlines() if "only one library per nickname" in ln
    ]
    assert len(lines) == 2
    html_lines = [
        ln for ln in w._log._text.toHtml().splitlines()
        if "only one library per nickname" in ln
    ]
    assert len(html_lines) == 2
    assert all(COLORS["warning"].lower() in ln.lower() for ln in html_lines)
    _assert_one_selected_per_nickname(w)


def _linked_scan():
    fp_c, fp_w = "Custom/Footprints/FpLib.pretty", WURTH_FP.format("FpLib")
    return ScanResult(
        symbol_libs=[_sym("S", refs=[("FpLib", "X", True)])],
        footprint_libs=[
            _fp("FpLib", peers=[fp_w]),
            _fp("FpLib", source="WurthElektronik", peers=[fp_c]),
            _fp("Solo"),
        ],
    )


def test_startup_selects_footprints_linked_to_preselected_symbols_then_rescan_keeps_flags(
    make_window, qtbot, tmp_path
):
    repo = tmp_path / "repo"
    repo.mkdir()
    fp_c, fp_w = "Custom/Footprints/FpLib.pretty", WURTH_FP.format("FpLib")
    solo = "Custom/Footprints/Solo.pretty"
    _write_tables(repo, ["Custom/Symbols/S.kicad_sym"], [solo])

    w = make_window([_linked_scan, _linked_scan], repo=repo)

    assert _selected(w._scan_result.footprint_libs) == {fp_c, solo}
    assert w._tree._fp_items[fp_c].checkState(0) == Qt.CheckState.Checked
    assert w._tree._fp_items[fp_w].checkState(0) == Qt.CheckState.Unchecked
    assert "linked to the pre-selected symbols" in _log_text(w)
    _assert_one_selected_per_nickname(w)

    # HARD-07: after a rescan the user's footprint flags are kept as they are
    _check(w._tree._fp_items[fp_c], on=False)
    _rescan_and_wait(w, qtbot)

    assert _selected(w._scan_result.symbol_libs) == {"Custom/Symbols/S.kicad_sym"}
    assert _selected(w._scan_result.footprint_libs) == {solo}
    _assert_one_selected_per_nickname(w)


def test_startup_scan_error_then_rescan_starts_unchecked(make_window, qtbot, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_tables(repo, ["Custom/Symbols/S.kicad_sym"], ["Custom/Footprints/Solo.pretty"])

    def fresh():
        return ScanResult(
            symbol_libs=[_sym("S", refs=[("FpLib", "X", True)])],
            footprint_libs=[_fp("FpLib"), _fp("Solo")],
        )

    w = make_window([_raising("boom"), fresh], repo=repo)

    text = _log_text(w)
    assert "Scan error: boom" in text
    marker = "nothing was pre-selected from the destination tables"
    assert len([ln for ln in text.splitlines() if marker in ln]) == 1
    assert w._startup_pending is False
    assert w._scan_result is None

    _rescan_and_wait(w, qtbot)

    result = w._scan_result
    assert [lib.selected for lib in result.symbol_libs] == [False]
    assert [lib.selected for lib in result.footprint_libs] == [False, False]
    for item in list(w._tree._sym_items.values()) + list(w._tree._fp_items.values()):
        assert item.checkState(0) == Qt.CheckState.Unchecked
    text = _log_text(w)
    assert "Kept 0 selections after rescan" in text
    assert "linked to the pre-selected symbols" not in text


def test_startup_finish_raising_consumes_startup_flag(make_window, qtbot, monkeypatch):
    gate = threading.Event()
    w = make_window([_gated(ScanResult(), gate)], wait=False)
    assert w._startup_pending is True

    def boom(_result):
        raise RuntimeError("populate boom")

    with monkeypatch.context() as patch:
        patch.setattr(w._tree, "populate", boom)
        with qtbot.captureExceptions() as exceptions:
            gate.set()
            qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    assert exceptions
    assert w._startup_pending is False

    calls = []
    with monkeypatch.context() as patch:
        patch.setattr(w, "_apply_existing_selection", lambda r: calls.append("apply"))
        patch.setattr(w, "_select_linked_footprints", lambda r: calls.append("linked"))
        _rescan_and_wait(w, qtbot)
    assert calls == []


# ── Check Atomic Parts (SCAN-03) ──────────────────────────────────────────

ATOMIC_REL = "Custom/Symbols/Atomic_Connector.kicad_sym"


def _atomic_scan():
    """A scan whose Atomic_ library holds one failing symbol and one that passes."""
    failing = SymbolEntry("FFC-0.5-20", violations=[Violation("value", "Value is not the part number")])
    library = SymbolLibrary(
        "Atomic_Connector", ATOMIC_REL, "Custom", atomic=True,
        symbols=[failing, SymbolEntry("USB4105-GF-A")],
    )
    return ScanResult(symbol_libs=[library])


def test_atomic_action_opens_dialog_and_apply_rescans(make_window, qtbot):
    w = make_window([_atomic_scan()])
    assert w._atomic_dialog is None

    w._act_check_atomic.trigger()

    dialog = w._atomic_dialog
    assert dialog is not None
    assert w._act_check_atomic.shortcut().toString() == "Ctrl+Shift+A"
    calls_before = len(make_window.calls)

    dialog.applied.emit([Issue(Severity.SUCCESS, "atomic.fixed", "Fixed Custom/Symbols/X.kicad_sym")])
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    assert "Fixed Custom/Symbols/X.kicad_sym" in _log_text(w)
    assert len(make_window.calls) == calls_before + 1
    dialog.reject()


def test_atomic_symbol_activated_opens_dialog_with_that_symbol_current(make_window):
    w = make_window([_atomic_scan()])

    w._tree.symbol_activated.emit(ATOMIC_REL, "FFC-0.5-20")

    dialog = w._atomic_dialog
    assert dialog is not None
    assert dialog._problems.currentItem().text(0) == "Atomic_Connector / FFC-0.5-20"
    dialog.reject()


def test_atomic_problem_row_double_click_opens_dialog_on_its_symbol(make_window):
    w = make_window([_atomic_scan()])
    lib_item = w._tree._sym_items[ATOMIC_REL]
    symbol_row = next(
        lib_item.child(i) for i in range(lib_item.childCount())
        if lib_item.child(i).text(0) == "FFC-0.5-20"
    )
    problem_row = symbol_row.child(0)
    assert problem_row.text(0) == "Value is not the part number"

    w._tree._sym_tree.itemDoubleClicked.emit(problem_row, 0)

    dialog = w._atomic_dialog
    assert dialog is not None
    assert dialog._problems.currentItem().text(0) == "Atomic_Connector / FFC-0.5-20"
    dialog.reject()


def test_atomic_action_is_disabled_while_a_scan_runs(make_window, qtbot):
    gate = threading.Event()
    w = make_window([_gated(_atomic_scan(), gate)], wait=False)
    try:
        qtbot.waitUntil(lambda: len(make_window.calls) == 1, timeout=5000)
        assert not w._act_check_atomic.isEnabled()
    finally:
        gate.set()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    assert w._act_check_atomic.isEnabled()


def test_atomic_check_without_a_scan_result_logs_and_opens_nothing(make_window):
    w = make_window([_raising("boom")])
    assert w._scan_result is None

    w._open_atomic_check()

    assert w._atomic_dialog is None
    assert "No scan result yet; rescan first." in _log_text(w)


def test_atomic_second_open_request_opens_no_second_dialog(make_window):
    w = make_window([_atomic_scan()])
    w._open_atomic_check()
    first = w._atomic_dialog

    w._open_atomic_check()
    w._tree.symbol_activated.emit(ATOMIC_REL, "FFC-0.5-20")

    assert w._atomic_dialog is first
    first.reject()
    assert w._atomic_dialog is None


def test_atomic_dialog_is_rejected_when_the_window_closes(make_window):
    w = make_window([_atomic_scan()])
    w._open_atomic_check()
    dialog = w._atomic_dialog
    assert dialog is not None

    assert w.close() is True

    assert w._atomic_dialog is None
    assert dialog.result() == dialog.DialogCode.Rejected


# ── Saved scan reused at startup (quick 261027-gg7) ───────────────────────

SAVED_SYM = "Custom/Symbols/A.kicad_sym"
SAVED_FP = "Custom/Footprints/B.pretty"
SAVED_NOTE = "Showing the saved scan from"


def _disk_scan(repo):
    """A fake scan whose libraries really exist under repo, so the saved scan can be checked."""
    (repo / SAVED_SYM).parent.mkdir(parents=True, exist_ok=True)
    if not (repo / SAVED_SYM).exists():  # never touch an existing file: its mtime is what the saved scan checks
        (repo / SAVED_SYM).write_text("(kicad_symbol_lib)", encoding="utf-8")
    (repo / SAVED_FP).mkdir(parents=True, exist_ok=True)
    return ScanResult(
        symbol_libs=[
            SymbolLibrary("A", SAVED_SYM, "Custom", footprint_refs=[FootprintRef("B", "X", True)]),
        ],
        footprint_libs=[FootprintLibrary("B", SAVED_FP, "Custom")],
    )


def _first_start(make_window, repo):
    """Start once so the full scan saves its result; returns the window."""
    return make_window([_disk_scan(repo)], repo=repo)


def test_second_start_reuses_the_saved_scan_without_scanning(make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    first = _first_start(make_window, repo)
    assert len(make_window.calls) == 1
    cache = settings.scan_cache_file(repo)
    assert cache.is_file()
    assert repo.resolve() not in cache.resolve().parents
    assert "No saved scan yet; scanning the whole repository." in _log_text(first)
    first.close()
    _write_tables(repo, [SAVED_SYM])

    second = make_window([_disk_scan(repo)], repo=repo)

    assert make_window.calls == [], _log_text(second)
    text = _log_text(second)
    assert SAVED_NOTE in text
    assert "no library file changed since then. Use Rescan for a full scan." in text
    assert "Scanning repository..." not in text
    assert [lib.rel_path for lib in second._scan_result.symbol_libs] == [SAVED_SYM]
    assert [lib.rel_path for lib in second._scan_result.footprint_libs] == [SAVED_FP]
    # Selection comes from the destination tables, never from the saved scan
    assert _selected(second._scan_result.symbol_libs) == {SAVED_SYM}
    assert _selected(second._scan_result.footprint_libs) == {SAVED_FP}


def test_an_edited_library_file_runs_the_full_scan_and_says_so(make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _first_start(make_window, repo).close()
    sym = repo / SAVED_SYM
    info = sym.stat()
    os.utime(sym, ns=(info.st_atime_ns, info.st_mtime_ns + 5_000_000_000))

    second = make_window([_disk_scan(repo)], repo=repo)

    assert len(make_window.calls) == 1
    text = _log_text(second)
    assert "1 library file changed since the saved scan; scanning the whole repository." in text
    assert SAVED_NOTE not in text


def test_a_corrupt_saved_scan_runs_the_full_scan_without_crashing(make_window, tmp_path, qtbot):
    repo = tmp_path / "repo"
    repo.mkdir()
    _first_start(make_window, repo).close()
    settings.scan_cache_file(repo).write_text("{ this is not json", encoding="utf-8")

    with qtbot.captureExceptions() as exceptions:
        second = make_window([_disk_scan(repo)], repo=repo)

    assert exceptions == []
    assert len(make_window.calls) == 1
    assert "The saved scan could not be read; scanning the whole repository." in _log_text(second)
    # The full scan saved a good file again
    third = make_window([_disk_scan(repo)], repo=repo)
    assert make_window.calls == []
    assert SAVED_NOTE in _log_text(third)


def test_rescan_after_a_reused_start_is_a_full_scan_that_rewrites_the_saved_scan(
    make_window, tmp_path, qtbot
):
    repo = tmp_path / "repo"
    repo.mkdir()
    _first_start(make_window, repo).close()
    second = make_window([_disk_scan(repo)], repo=repo)
    assert make_window.calls == [], _log_text(second)
    cache = settings.scan_cache_file(repo)
    os.utime(cache, ns=(1_000_000_000, 1_000_000_000))

    _rescan_and_wait(second, qtbot)

    assert len(make_window.calls) == 1
    assert cache.stat().st_mtime_ns > 2_000_000_000
    assert "Scanning repository..." in _log_text(second)


def test_failed_cache_save_warns_and_still_shows_the_scan(make_window, tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    cache = settings.scan_cache_file(repo)
    cache.mkdir(parents=True)  # a folder where the file must go

    w = make_window([_disk_scan(repo)], repo=repo)

    assert [lib.rel_path for lib in w._scan_result.symbol_libs] == [SAVED_SYM]
    assert "Could not save this scan for the next start" in _log_text(w)


# ── Rescan this library (quick 261027-gg7) ────────────────────────────────

def _fake_rescan(monkeypatch, *, warnings=0, rechecked=(), outcome=None, record=None):
    """Replace main_window.rescan_library; returns the calls list."""
    calls = []

    def fake(root, previous, kind, rel_path, kicad_fp_dir=None):
        calls.append((root, kind, rel_path))
        if record is not None:
            record.append(previous)
        if outcome is not None:
            return outcome
        merged = copy.deepcopy(previous)
        for lib in merged.symbol_libs:
            lib.selected = False  # a stale snapshot: the live check boxes must win
            lib.footprint_refs = [FootprintRef("B", "Changed", True)]
        issues = [Issue(Severity.WARNING, "atomic.x", f"warning {i}") for i in range(warnings)]
        return library_scanner.LibraryRescan(merged, issues, list(rechecked))

    monkeypatch.setattr(main_window, "rescan_library", fake)
    return calls


def _rescan_and_finish(w, qtbot, kind="symbol", rel=SAVED_SYM):
    w._tree.library_rescan_requested.emit(kind, rel)
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)


def test_library_rescan_runs_in_a_worker_and_keeps_the_check_boxes(make_window, qtbot, monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    w = _first_start(make_window, repo)
    calls = _fake_rescan(monkeypatch, warnings=2)
    w._scan_result.symbol_libs[0].selected = True
    sym_item = w._tree._sym_items[SAVED_SYM]
    sym_item.setCheckState(0, Qt.CheckState.Checked)
    before = len(make_window.calls)

    _rescan_and_finish(w, qtbot)

    assert len(calls) == 1 and calls[0][1:] == ("symbol", SAVED_SYM)
    assert len(make_window.calls) == before  # no full scan
    assert w._scan_result.symbol_libs[0].footprint_refs[0].footprint_name == "Changed"
    assert w._scan_result.symbol_libs[0].selected is True
    assert w._tree._sym_items[SAVED_SYM].checkState(0) == Qt.CheckState.Checked
    text = _log_text(w)
    assert text.count("Rescanned symbol library A: 2 warnings") == 1
    assert w._worker is None and w._rescan_btn.isEnabled()


def test_library_rescan_log_wording(make_window, qtbot, monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    w = _first_start(make_window, repo)

    _fake_rescan(monkeypatch)
    _rescan_and_finish(w, qtbot)
    assert "Rescanned symbol library A: no warnings" in _log_text(w)

    _fake_rescan(monkeypatch, warnings=1)
    _rescan_and_finish(w, qtbot)
    assert "Rescanned symbol library A: 1 warning\n" in _log_text(w) + "\n"

    _fake_rescan(monkeypatch, rechecked=["Atomic_X"])
    _rescan_and_finish(w, qtbot, "footprint", SAVED_FP)
    assert (
        "Rescanned footprint library B (and re-checked 1 linked atomic symbol library): no warnings"
        in _log_text(w)
    )

    _fake_rescan(monkeypatch, rechecked=["Atomic_X", "Atomic_Y"])
    _rescan_and_finish(w, qtbot, "footprint", SAVED_FP)
    assert "(and re-checked 2 linked atomic symbol libraries)" in _log_text(w)


def test_library_rescan_is_refused_and_disabled_while_a_scan_runs(make_window, qtbot, monkeypatch):
    gate = threading.Event()
    calls = _fake_rescan(monkeypatch)
    w = make_window([_gated(ScanResult(), gate)], wait=False)
    try:
        qtbot.waitUntil(lambda: len(make_window.calls) == 1, timeout=5000)
        action = w._tree._build_context_menu(w._tree._sym_tree, None).actions()
        assert [a.text() for a in action] == ["Expand All", "Collapse All"]
        assert w._tree._library_rescan_enabled is False

        w._tree.library_rescan_requested.emit("symbol", SAVED_SYM)

        assert _log_text(w).count("A scan is already running; request ignored.") == 1
        assert calls == []
    finally:
        gate.set()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    assert w._tree._library_rescan_enabled is True


def test_library_rescan_without_a_scan_result_says_so(make_window, monkeypatch):
    calls = _fake_rescan(monkeypatch)
    w = make_window([_raising("boom")])
    assert w._scan_result is None

    w._on_library_rescan_requested("symbol", SAVED_SYM)

    assert "No scan result yet; rescan first." in _log_text(w)
    assert calls == [] and w._worker is None


def test_library_that_needs_a_full_scan_logs_why_then_runs_one(make_window, qtbot, monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    w = _first_start(make_window, repo)
    reason = "A is no longer at x (deleted or renamed); running a full rescan instead."
    _fake_rescan(monkeypatch, outcome=Issue(Severity.INFO, "rescan.full_needed", reason))
    before = len(make_window.calls)

    _rescan_and_finish(w, qtbot)
    qtbot.waitUntil(lambda: len(make_window.calls) == before + 1 and w._worker is None, timeout=5000)

    text = _log_text(w)
    assert text.count(reason) == 1
    assert text.index(reason) < text.rindex("Scanning repository...")


def test_library_rescan_error_clears_the_busy_state(make_window, qtbot, monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    w = _first_start(make_window, repo)

    def boom(*args, **kwargs):
        raise RuntimeError("disk gone")

    monkeypatch.setattr(main_window, "rescan_library", boom)
    _rescan_and_finish(w, qtbot)

    assert "Scan error: disk gone" in _log_text(w)
    assert w._rescan_btn.isEnabled()


def test_library_rescan_updates_the_saved_scan(make_window, qtbot, monkeypatch, tmp_path):
    from kicad_lib_manager import scan_cache

    repo = tmp_path / "repo"
    repo.mkdir()
    w = _first_start(make_window, repo)
    _fake_rescan(monkeypatch)
    sym = repo / SAVED_SYM
    sym.write_text("(kicad_symbol_lib (edited))", encoding="utf-8")
    cache = settings.scan_cache_file(repo)
    # Before the rescan the edited file makes the saved scan stale
    assert scan_cache.load_fresh(cache, repo, make_window.calls[0][1]).note.code == "cache.stale"

    _rescan_and_finish(w, qtbot)

    check = scan_cache.load_fresh(cache, repo, make_window.calls[0][1])
    assert check.note.code == "cache.reused"
    assert check.result.symbol_libs[0].footprint_refs[0].footprint_name == "Changed"
    assert check.result.symbol_libs[0].selected is False


# ── Skip on the Loading Libraries window (plan 12-17, G-12-21) ─────────────

SKIP_TIP = (
    "Stop checking the 3D model paths of WurthElektronik. "
    "Its libraries are still listed, and Rescan checks them again."
)


def test_scan_progress_dialog_skip_button_follows_the_source(qtbot):
    from kicad_lib_manager.widgets.scan_progress import ScanProgressDialog

    dialog = ScanProgressDialog()
    qtbot.addWidget(dialog)
    button = dialog.skip_button
    assert dialog.windowTitle() == "Loading Libraries"
    assert button.text() == "Skip"
    assert not button.isEnabled()
    assert not button.isDefault() and not button.autoDefault()

    emitted = []
    dialog.skip_requested.connect(emitted.append)
    dialog.set_skippable("WurthElektronik")
    assert button.text() == "Skip WurthElektronik"
    assert button.isEnabled()
    assert button.toolTip() == SKIP_TIP

    button.click()
    button.click()
    assert emitted == ["WurthElektronik"]
    assert button.text() == "Skipping WurthElektronik..."
    assert not button.isEnabled()

    dialog.set_skippable(None)
    assert button.text() == "Skip"
    assert not button.isEnabled()

    dialog.set_progress("Checking 3D paths: X", 42)
    assert dialog._label.text() == "Checking 3D paths: X"
    assert dialog._bar.value() == 42


def test_scan_progress_dialog_ignores_escape_and_close(qtbot):
    from PySide6.QtTest import QTest
    from kicad_lib_manager.widgets.scan_progress import ScanProgressDialog

    dialog = ScanProgressDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    dialog.close()
    assert dialog.isVisible()

    dialog.finish()
    assert not dialog.isVisible()


def _wurth_scan_result(skipped):
    return ScanResult(
        symbol_libs=[
            _sym("WE_S", "WurthElektronik", refs=[("WE_F", "X", True)]),
        ],
        footprint_libs=[_fp("WE_F", "WurthElektronik")],
        skipped_sources=list(skipped),
        issues=[library_scanner.models_skipped_issue(skipped)] if skipped else [],
    )


def _skip_line():
    return library_scanner.models_skipped_issue(["WurthElektronik"]).text


def test_loading_dialog_skips_the_source_being_checked(make_window, qtbot):
    answers = []

    def scan():
        skip, checking = make_window.hooks
        checking("WurthElektronik")
        for _ in range(500):
            if skip("WurthElektronik"):
                break
            threading.Event().wait(0.01)
        answers.append(skip("WurthElektronik"))
        checking(None)
        return _wurth_scan_result(["WurthElektronik"])

    w = make_window([scan], wait=False)
    qtbot.waitUntil(lambda: w._progress is not None
                    and w._progress.skip_button.text() == "Skip WurthElektronik"
                    and w._progress.skip_button.isEnabled(), timeout=5000)
    w._progress.skip_button.click()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    assert answers == [True]
    lines = _log_text(w).splitlines()
    assert sum(1 for line in lines if _skip_line() in line) == 1
    assert any("No warnings in the checks that ran." in line for line in lines)
    assert not any(line.strip().endswith("No warnings.") for line in lines)
    assert not any("Skipping" in line for line in lines)
    assert not w._progress.isVisible()
    assert [lib.nickname for lib in w._scan_result.symbol_libs] == ["WE_S"]
    assert [lib.nickname for lib in w._scan_result.footprint_libs] == ["WE_F"]


def test_a_skip_click_after_the_check_ended_logs_no_skip(make_window, qtbot):
    clicked = threading.Event()
    release = threading.Event()

    def scan():
        _skip, checking = make_window.hooks
        checking("WurthElektronik")
        clicked.wait(5)
        checking(None)
        release.wait(5)
        return _wurth_scan_result([])

    w = make_window([scan], wait=False)
    try:
        qtbot.waitUntil(lambda: w._progress is not None
                        and w._progress.skip_button.text() == "Skip WurthElektronik"
                        and w._progress.skip_button.isEnabled(), timeout=5000)
        button = w._progress.skip_button
        button.click()
        assert button.text() == "Skipping WurthElektronik..."
        assert not button.isEnabled()
        clicked.set()
        qtbot.waitUntil(lambda: button.text() == "Skip" and not button.isEnabled(),
                        timeout=5000)
    finally:
        clicked.set()
        release.set()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    text = _log_text(w)
    assert "Skipping" not in text and "were not checked" not in text
    assert "No warnings." in text
    assert w._scan_result.skipped_sources == []


# ── A skipped scan: Generate Tables and the saved scan (plan 12-17, G-12-21) ──

_WE_ROOT = "WurthElektronik/KiCad-Library"
_WE_SKIP_SYM = f"{_WE_ROOT}/symbols/WE_Test.kicad_sym"
_WE_SKIP_FP = f"{_WE_ROOT}/footprints/WE_Test.pretty"
_WE_SKIP_SYMBOL_TEXT = (
    '(kicad_symbol_lib (version 20231120) (generator "test")\n'
    '  (symbol "WE_SYM" (property "Reference" "U" (at 0 0 0))\n'
    '    (property "Footprint" "WE_Test:WE_FP_A" (at 0 0 0)))\n'
    ")\n"
)


def _synthetic_repo_with_wurth(tmp_path):
    """Custom (atomic fixture) plus one hand-written WurthElektronik library pair; the real submodule is never read."""
    from customfixtures import write_atomic_custom, write_fake_kicad

    repo = tmp_path / "repo"
    repo.mkdir()
    write_atomic_custom(repo)
    symbols = repo / _WE_ROOT / "symbols"
    symbols.mkdir(parents=True, exist_ok=True)
    (symbols / "WE_Test.kicad_sym").write_text(_WE_SKIP_SYMBOL_TEXT, encoding="utf-8")
    pretty = repo / _WE_SKIP_FP
    pretty.mkdir(parents=True, exist_ok=True)
    (pretty / "WE_FP_A.kicad_mod").write_text(
        '(footprint "WE_FP_A"\n  (model "C:/models/a.step")\n)\n', encoding="utf-8"
    )
    footprints, _models = write_fake_kicad(tmp_path)
    return repo, footprints


def test_generate_after_a_skip_removes_no_entry(make_window, qtbot, tmp_path):
    repo, fp_dir = _synthetic_repo_with_wurth(tmp_path)
    full = library_scanner.scan_all(repo, kicad_fp_dir=fp_dir)
    custom_sym = next(lib for lib in full.symbol_libs if lib.source == "Custom")
    custom_fp = next(lib for lib in full.footprint_libs if lib.source == "Custom")
    _write_tables(
        repo, [custom_sym.rel_path, _WE_SKIP_SYM], [custom_fp.rel_path, _WE_SKIP_FP]
    )

    def scan():
        _skip, checking = make_window.hooks
        return library_scanner.scan_all(
            repo, kicad_fp_dir=fp_dir, skip=lambda source: source == "WurthElektronik",
            checking=checking,
        )

    w = make_window([scan], repo=repo)

    result = w._scan_result
    assert result.skipped_sources == ["WurthElektronik"]
    assert {_WE_SKIP_SYM} <= _selected(result.symbol_libs)
    assert {_WE_SKIP_FP} <= _selected(result.footprint_libs)
    we_sym = next(lib for lib in result.symbol_libs if lib.rel_path == _WE_SKIP_SYM)
    assert [(r.library_name, r.footprint_name) for r in we_sym.footprint_refs] == [
        ("WE_Test", "WE_FP_A")
    ]

    w._on_generate()
    settle(qtbot, w)

    sym_table = (repo / "sym-lib-table").read_text(encoding="utf-8")
    fp_table = (repo / "fp-lib-table").read_text(encoding="utf-8")
    assert f"${{KICAD_LIB_GITHUB}}/{_WE_SKIP_SYM}" in sym_table
    assert f"${{KICAD_LIB_GITHUB}}/{_WE_SKIP_FP}" in fp_table
    assert 'name "WE_Test"' in sym_table and 'name "WE_Test"' in fp_table
    assert not any("removed" in line for line in _log_text(w).splitlines())


def test_skipped_scan_is_saved_and_the_next_start_says_so(make_window, tmp_path, qtbot):
    repo = tmp_path / "repo"
    repo.mkdir()
    skip_line = library_scanner.models_skipped_issue(["WurthElektronik"]).text
    note = ("The 3D model paths of WurthElektronik were skipped in that scan; "
            "use Rescan for a full scan.")

    # Built before the window exists: the library files must be there when the saved scan is taken
    skipped = replace(
        _disk_scan(repo), skipped_sources=["WurthElektronik"],
        issues=[library_scanner.models_skipped_issue(["WurthElektronik"])],
    )

    first = make_window([skipped], repo=repo)
    assert "No warnings in the checks that ran." in _log_text(first)
    first.close()

    second = make_window([_disk_scan(repo)], repo=repo)
    assert make_window.calls == [], _log_text(second)
    text = _log_text(second)
    assert SAVED_NOTE in text
    assert note in text
    assert skip_line in text
    assert not any(line.strip().endswith("No warnings.") for line in text.splitlines())
    assert second._scan_result.skipped_sources == ["WurthElektronik"]

    _rescan_and_wait(second, qtbot)
    assert len(make_window.calls) == 1
    second.close()

    third = make_window([_disk_scan(repo)], repo=repo)
    assert make_window.calls == []
    text = _log_text(third)
    assert SAVED_NOTE in text
    assert "were skipped" not in text
    assert third._scan_result.skipped_sources == []


# -- the shared, parentless User Guide (plan 12-18, G-12-22) -----------------------------------------

import types  # noqa: E402

from PySide6.QtCore import QRect  # noqa: E402
from PySide6.QtGui import QCloseEvent  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from kicad_lib_manager.widgets.help_dialog import HelpDialog  # noqa: E402
from test_help_dialog import _heading_near_top  # noqa: E402


@pytest.fixture(autouse=True)
def _close_guides():
    """The guide is a parentless top-level window: close and release every one a test left behind."""
    yield
    for widget in QApplication.topLevelWidgets():
        if isinstance(widget, HelpDialog):
            widget.close()
            widget.deleteLater()


def guide_windows() -> list[HelpDialog]:
    return [widget for widget in QApplication.topLevelWidgets() if isinstance(widget, HelpDialog)]


def guide_key(guide: HelpDialog) -> str:
    return guide._toc.currentItem().data(0, Qt.ItemDataRole.UserRole)


def click_guide_row(guide: HelpDialog, key: str) -> None:
    """Click the guide's menu row with this key through the window system, which drops a click aimed at a blocked window."""
    stack = [guide._toc.topLevelItem(i) for i in range(guide._toc.topLevelItemCount())]
    while stack:
        item = stack.pop(0)
        if item.data(0, Qt.ItemDataRole.UserRole) == key:
            break
        stack.extend(item.child(i) for i in range(item.childCount()))
    else:
        raise AssertionError(f"no User Guide topic {key!r}")
    toc = guide._toc
    toc.scrollToItem(item)
    point = toc.viewport().mapTo(guide, toc.visualItemRect(item).center())
    QTest.mouseClick(guide.windowHandle(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)


def click_in_window(window, button) -> None:
    """Click a button of a window through the window system."""
    point = button.mapTo(window, button.rect().center())
    QTest.mouseClick(window.windowHandle(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)


def help_menu_action(w):
    (action,) = [a for a in w.findChildren(type(w.menuBar().actions()[0])) if a.text() == "&User Guide"]
    return action


def test_main_window_help_opens_one_shared_non_modal_guide(qtbot, make_window):
    w = make_window([ScanResult()])
    w.show()
    before = len(guide_windows())
    help_menu_action(w).trigger()
    guide = w._guide
    assert isinstance(guide, HelpDialog) and guide.isVisible()
    assert guide.parent() is None
    assert guide.windowModality() == Qt.WindowModality.NonModal
    assert not guide.isModal()
    assert guide.windowHandle().transientParent() is None
    assert QApplication.activeModalWidget() is not guide
    assert len(guide_windows()) == before + 1

    w.activateWindow()
    qtbot.waitUntil(w.isActiveWindow, timeout=5000)
    qtbot.keyClick(w, Qt.Key.Key_F1)
    assert w._guide is guide and guide.isVisible()

    guide.close()
    assert not guide.isVisible()
    help_menu_action(w).trigger()
    assert w._guide is guide and guide.isVisible()
    assert len(guide_windows()) == before + 1


def test_main_window_and_guide_both_take_clicks(qtbot, make_window):
    w = make_window([ScanResult()])
    w.show()
    qtbot.waitExposed(w)
    help_menu_action(w).trigger()
    guide = w._guide
    qtbot.waitExposed(guide)

    clicks = []
    w._select_all_btn.clicked.connect(lambda: clicks.append(True))
    click_in_window(w, w._select_all_btn)
    assert clicks == [True]

    click_guide_row(guide, "shortcuts")
    qtbot.waitUntil(lambda: guide_key(guide) == "shortcuts", timeout=5000)
    assert "Keyboard Shortcuts" in guide._browser.toPlainText()


def test_closing_the_main_window_closes_the_guide(qtbot, make_window):
    w = make_window([ScanResult()])
    w.show()
    help_menu_action(w).trigger()
    guide = w._guide
    assert guide.isVisible()
    w.close()
    assert not guide.isVisible()


def test_a_refused_close_keeps_the_guide(qtbot, make_window):
    w = make_window([ScanResult()])
    w.show()
    help_menu_action(w).trigger()
    guide = w._guide
    w._import_dialog = types.SimpleNamespace(
        is_installing=lambda: True, is_finishing=lambda: False, reject=lambda: pytest.fail("rejected")
    )
    try:
        event = QCloseEvent()
        w.closeEvent(event)
        assert not event.isAccepted()
        assert guide.isVisible()
        assert not w.close()
        assert guide.isVisible()
    finally:
        w._import_dialog = None
    w.close()
    assert not guide.isVisible()


def test_guide_first_shows_over_the_main_window(qtbot, make_window):
    w = make_window([ScanResult()])
    w.show()
    w.resize(1100, 750)
    w.move(300, 200)
    qtbot.waitExposed(w)
    help_menu_action(w).trigger()
    guide = w._guide
    qtbot.waitExposed(guide)
    here, there = w.frameGeometry().center(), guide.frameGeometry().center()
    assert abs(here.x() - there.x()) <= 2 and abs(here.y() - there.y()) <= 2, (here, there)
    assert QRect(0, 0, 1920, 1032).contains(guide.frameGeometry())


# -- Help and F1 reopen the owner's place in the guide (plan 12-19, G-12-23) ----------------------------


def test_main_window_help_reopens_the_owner_choice(qtbot, make_window):
    w = make_window([ScanResult()])
    w.show()
    qtbot.waitExposed(w)
    help_menu_action(w).trigger()
    guide = w._guide
    qtbot.waitExposed(guide)
    click_guide_row(guide, "generating")
    qtbot.waitUntil(lambda: guide_key(guide) == "generating", timeout=5000)
    assert settings.load_help_topic() == "generating"

    # what the import window does: a given topic, which is not the owner's move
    w.show_guide("importing")
    assert guide_key(guide) == "importing"
    assert settings.load_help_topic() == "generating"

    guide.close()
    assert not guide.isVisible()
    help_menu_action(w).trigger()
    assert w._guide is guide and guide.isVisible()
    assert guide_key(guide) == "generating"
    assert settings.load_help_topic() == "generating"


def test_main_window_help_on_a_visible_guide_only_raises(qtbot, make_window):
    w = make_window([ScanResult()])
    w.show()
    qtbot.waitExposed(w)
    help_menu_action(w).trigger()
    guide = w._guide
    qtbot.waitExposed(guide)
    click_guide_row(guide, "importing#conflicts")
    qtbot.waitUntil(lambda: guide_key(guide) == "importing#conflicts", timeout=5000)
    qtbot.waitUntil(lambda: _heading_near_top(guide._browser, "4.4.7 Conflicts"), timeout=5000)
    bar = guide._browser.verticalScrollBar()
    # reading further down; half way, because the browser re-estimates its page height as it lays the page out
    # and a value at the maximum is clamped when that maximum shrinks
    bar.setValue(bar.maximum() // 2)
    held = bar.value()
    assert held > 0

    w.activateWindow()
    qtbot.waitUntil(w.isActiveWindow, timeout=5000)
    help_menu_action(w).trigger()
    assert w._guide is guide and guide.isVisible()
    assert guide_key(guide) == "importing#conflicts"
    assert not guide.shows_asked_topic()
    qtbot.wait(50)  # one more event-loop turn
    assert bar.value() == held  # a page being read is not pulled away
    qtbot.waitUntil(guide.isActiveWindow, timeout=5000)


def test_main_window_help_after_restart_opens_the_saved_place(qtbot, make_window):
    settings.save_help_topic("restoring")
    w = make_window([ScanResult()])
    w.show()
    help_menu_action(w).trigger()
    assert w._guide.isVisible()
    assert guide_key(w._guide) == "restoring"
    assert settings.load_help_topic() == "restoring"


# -- plan 12-21, G-12-27: Help brings back the chosen section and its heading ------------------------------


@pytest.mark.parametrize("how", ["close", "escape", "import help between", "import help, guide left open"])
def test_main_window_help_brings_the_section_heading_back(qtbot, make_window, how):
    w = make_window([ScanResult()])
    w.show()
    qtbot.waitExposed(w)
    help_menu_action(w).trigger()
    guide = w._guide
    qtbot.waitExposed(guide)

    click_guide_row(guide, "importing#conflicts")
    qtbot.waitUntil(lambda: guide_key(guide) == "importing#conflicts", timeout=5000)
    qtbot.waitUntil(lambda: _heading_near_top(guide._browser, "4.4.7 Conflicts"), timeout=5000)
    guide._browser.verticalScrollBar().setValue(0)

    if how.startswith("import help"):
        w.show_guide("importing")  # what the import window's Help does
        assert guide_key(guide) == "importing"

    if how == "import help, guide left open":
        assert guide.isVisible()
        w.activateWindow()  # as after Cancel in the import window
        qtbot.waitUntil(w.isActiveWindow, timeout=5000)
    else:
        if how == "escape":
            QTest.keyClick(guide, Qt.Key.Key_Escape)
        else:
            guide.close()
        assert not guide.isVisible()

    help_menu_action(w).trigger()
    assert w._guide is guide and guide.isVisible()
    assert guide_key(guide) == "importing#conflicts"
    selected = [i.data(0, Qt.ItemDataRole.UserRole) for i in guide._toc.selectedItems()]
    assert selected == ["importing#conflicts"]  # the page row 4.4 is not the selected one
    assert settings.load_help_topic() == "importing#conflicts"
    qtbot.waitUntil(lambda: _heading_near_top(guide._browser, "4.4.7 Conflicts"), timeout=5000)
    if how == "import help, guide left open":
        qtbot.waitUntil(guide.isActiveWindow, timeout=5000)


# -- the main window's own dialogs leave the guide usable (plan 12-20, G-12-22) ----------------------

from PySide6.QtCore import QTimer  # noqa: E402

# Captured at import, before any fixture replaces it: the real window-modal Yes/No question
REAL_QUESTION = main_window.MainWindow.__dict__.get("_question")

_YES_NO = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
_PATH_CHANGES = [("KICAD_LIB_GITHUB", None, "C:/repo")]


def _run_dialog_beside_the_guide(qtbot, w, guide, open_dialog):
    """Open a main-window dialog, click a guide row while it is open, then close it.

    Returns what the probe saw and what the opening call returned.
    """
    seen = {}

    def probe():
        box = QApplication.activeModalWidget()
        try:
            seen["box"] = box
            if box is not None:
                seen["modality"] = box.windowModality()
                seen["parent"] = box.parent()
                click_guide_row(guide, "shortcuts")
                qtbot.waitUntil(lambda: guide_key(guide) == "shortcuts", timeout=2000)
        except Exception as error:  # reported after the dialog is closed, so a failure cannot hang
            seen["error"] = error
        finally:
            if box is not None:
                box.reject()

    # Safety net: a dialog that never reports must not hang the run
    QTimer.singleShot(10000, lambda: QApplication.activeModalWidget() and QApplication.activeModalWidget().reject())
    QTimer.singleShot(50, probe)
    seen["result"] = open_dialog()
    return seen


@pytest.mark.parametrize("case", ["path question", "kicad open", "restore backup", "about"])
def test_main_window_dialogs_are_window_modal_and_leave_the_guide_usable(qtbot, make_window, case):
    w = make_window([ScanResult()])
    w.show()
    qtbot.waitExposed(w)
    w.show_guide("generating")
    guide = w._guide
    qtbot.waitExposed(guide)
    assert guide_key(guide) == "generating"

    if case == "path question":
        assert REAL_QUESTION is not None, "MainWindow._question is missing"

    def kicad_open():
        box, answers = w._kicad_open_box(_PATH_CHANGES, ["kicad"])
        box.exec()
        return answers.get(box.clickedButton(), ConfirmAnswer.DECLINE)

    openers = {
        "path question": lambda: REAL_QUESTION(
            w, "Change KiCad path variables?", "Text", _YES_NO, QMessageBox.StandardButton.No
        ),
        "kicad open": kicad_open,
        "restore backup": w._on_restore_backup,
        "about": w._on_about,
    }

    seen = _run_dialog_beside_the_guide(qtbot, w, guide, openers[case])

    assert seen.get("box") is not None, "no dialog was open"
    assert seen["modality"] == Qt.WindowModality.WindowModal
    assert seen["parent"] is w
    assert "error" not in seen, seen.get("error")
    assert guide_key(guide) == "shortcuts"
    if case == "path question":
        assert seen["result"] == QMessageBox.StandardButton.No  # closed unanswered: the default
    if case == "kicad open":
        assert seen["result"] == ConfirmAnswer.DECLINE  # Escape is Not now


def test_guide_takes_clicks_while_the_libraries_load(qtbot, make_window):
    gate = threading.Event()
    w = make_window([ScanResult(), _gated(ScanResult(), gate)])
    w.show()
    qtbot.waitExposed(w)
    w.show_guide("generating")
    guide = w._guide
    qtbot.waitExposed(guide)
    try:
        w._on_rescan()
        qtbot.waitUntil(lambda: w._progress is not None and w._progress.isVisible(), timeout=5000)
        assert w._progress.windowTitle() == "Loading Libraries"

        click_guide_row(guide, "shortcuts")
        qtbot.waitUntil(lambda: guide_key(guide) == "shortcuts", timeout=5000)
    finally:
        gate.set()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
