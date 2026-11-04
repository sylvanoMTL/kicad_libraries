"""Offscreen MainWindow tests for the import entry point and the post-install rescan (plan 05-01).

The harness mirrors tests/test_main_window.py (fixtures cannot be imported across test
modules): QSettings goes into tmp_path and scan, KiCad detection, REPO_ROOT and the KiCad
config writer are replaced before the window exists.
"""

import os
import threading
import types
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData, QPoint, QPointF, QSettings, Qt, QUrl
from PySide6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QKeySequence
from PySide6.QtWidgets import QMessageBox
from zipfixtures import footprint_library_for

from kicad_lib_manager import library_scanner, main_window, settings
from kicad_lib_manager.library_scanner import ConfirmAnswer
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.plan import InstallResult, ToolContext
from kicad_lib_manager.importer.planner import build_plan as real_build_plan
from kicad_lib_manager.models import (
    FootprintLibrary, Issue, ScanResult, Severity, SymbolLibrary,
)
from kicad_lib_manager.widgets import theme
from kicad_lib_manager.widgets.import_dialog import ImportCore, ImportDialog

LIB = "Atomic_Battery_Management"
FP_LIB = footprint_library_for(LIB)
SYM_REL = f"Custom/Symbols/{LIB}.kicad_sym"
FP_REL = f"Custom/Footprints/{FP_LIB}.pretty"
USB_LIB = "Atomic_Connector"
USB_FP_LIB = footprint_library_for(USB_LIB)
USB_SYM_REL = f"Custom/Symbols/{USB_LIB}.kicad_sym"
USB_FP_REL = f"Custom/Footprints/{USB_FP_LIB}.pretty"
FFC_LIB = "Atomic_Connector_Audio"
FFC_FP_LIB = footprint_library_for(FFC_LIB)
FFC_SYM_REL = f"Custom/Symbols/{FFC_LIB}.kicad_sym"
FFC_FP_REL = f"Custom/Footprints/{FFC_FP_LIB}.pretty"
NEW_LIB = "Atomic_Sensor_Temperature"
NEW_FP_LIB = footprint_library_for(NEW_LIB)
NEW_SYM_REL = f"Custom/Symbols/{NEW_LIB}.kicad_sym"
NEW_FP_REL = f"Custom/Footprints/{NEW_FP_LIB}.pretty"
NO_DEST = "No destination folder set; library tables not changed"


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
    def make(results, repo=None, wait=True):
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

        config_base = tmp_path / "kicad_cfg"
        config_base.mkdir(exist_ok=True)
        config_file = config_base / "10.0" / "kicad_common.json"
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


def scan_with(*, selected_usb=False, with_installed=True, peer=None, selected_peer=False,
              lib=LIB, with_ffc=False) -> ScanResult:
    """A scan holding the USB connector library and (optionally) the installed library, with an optional same-nickname peer."""
    symbols = [SymbolLibrary(USB_LIB, USB_SYM_REL, "Custom")]
    footprints = [FootprintLibrary(USB_FP_LIB, USB_FP_REL, "Custom")]

    def footprint_lib(nickname: str, rel_path: str) -> FootprintLibrary:
        """Every Custom symbol library shares Atomic_Footprints, so a scan lists that one folder once."""
        known = next((f for f in footprints if f.rel_path == rel_path), None)
        if known is None:
            known = FootprintLibrary(nickname, rel_path, "Custom")
            footprints.append(known)
        return known

    if with_ffc:
        symbols.append(SymbolLibrary(FFC_LIB, FFC_SYM_REL, "Custom"))
        footprint_lib(FFC_FP_LIB, FFC_FP_REL)
    if with_installed:
        sym = SymbolLibrary(lib, f"Custom/Symbols/{lib}.kicad_sym", "Custom")
        fp = footprint_lib(footprint_library_for(lib), f"Custom/Footprints/{footprint_library_for(lib)}.pretty")
        symbols.append(sym)
        if peer is not None:
            peer_sym = SymbolLibrary(LIB, f"{peer}/Symbols/{LIB}.kicad_sym", peer)
            peer_fp = FootprintLibrary(FP_LIB, f"{peer}/Footprints/{FP_LIB}.pretty", peer)
            sym.collision_peers = [peer_sym.rel_path]
            fp.collision_peers = [peer_fp.rel_path]
            peer_sym.collision_peers = [sym.rel_path]
            peer_fp.collision_peers = [fp.rel_path]
            peer_sym.selected = peer_fp.selected = selected_peer
            symbols.append(peer_sym)
            footprints.append(peer_fp)
    symbols[0].selected = footprints[0].selected = selected_usb
    return ScanResult(symbol_libs=symbols, footprint_libs=footprints)


def stub_plan(
    repo: Path,
    library: str = LIB,
    new_library: bool = False,
    *,
    new_symbol_lib: bool | None = None,
    new_footprint_lib: bool | None = None,
    footprint_library: str | None = None,
    pretty: str | None = None,
):
    """A stand-in plan; footprint_library names the footprint library, pretty the .pretty folder the plan writes."""
    layout = RepoLayout.for_repo(repo)
    footprint_library = footprint_library or footprint_library_for(library)
    return types.SimpleNamespace(
        symbol_name="CSD85301Q2",
        library=library,
        new_symbol_lib=new_library if new_symbol_lib is None else new_symbol_lib,
        new_footprint_lib=new_library if new_footprint_lib is None else new_footprint_lib,
        footprint_library=footprint_library,
        symbol_lib_path=layout.symbols_dir / f"{library}.kicad_sym",
        pretty_path=layout.footprints_dir / f"{pretty or footprint_library}.pretty",
        layout=layout,
    )


def install_result() -> InstallResult:
    return InstallResult(ok=True, library=LIB, new_library=False, touched=(), issues=())


def selected(result: ScanResult, rel_path: str) -> bool:
    libs = [*result.symbol_libs, *result.footprint_libs]
    return next(lib for lib in libs if lib.rel_path == rel_path).selected


def test_import_action_first_in_file_menu(make_window):
    w = make_window([scan_with()])
    file_menu = w.menuBar().actions()[0].menu()
    first, second = file_menu.actions()[:2]
    assert first.text() == "&Import Part..."
    assert first.shortcut() == QKeySequence("Ctrl+I")
    assert first.statusTip() == "Import a vendor package (.zip or folder) into Custom/"
    assert first is w._act_import
    assert second.isSeparator()


def test_import_action_disabled_during_scan(qtbot, make_window):
    gate = threading.Event()

    def blocked():
        assert gate.wait(10)
        return scan_with()

    try:
        w = make_window([blocked], wait=False)
        assert w._worker is not None
        assert not w._act_import.isEnabled()
    finally:
        gate.set()
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    assert w._act_import.isEnabled()


def test_post_install_select_checks_installed_library(qtbot, make_window):
    first = scan_with(selected_usb=True)
    second = scan_with()
    w = make_window([first, second])
    # the user keeps the USB connector library checked in the GUI
    for lib in (*w._scan_result.symbol_libs, *w._scan_result.footprint_libs):
        lib.selected = lib.rel_path in (USB_SYM_REL, USB_FP_REL)
    before = len(make_window.calls)

    w._on_import_installed(install_result(), stub_plan(make_window.repo))
    assert w._worker is not None  # the scan starts at once (the fake scan itself runs on the worker)
    assert w._progress is None
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    assert len(make_window.calls) == before + 1
    result = w._scan_result
    assert selected(result, SYM_REL)
    assert selected(result, FP_REL)
    assert selected(result, USB_SYM_REL)
    assert selected(result, USB_FP_REL)
    assert w._pending_post_install is None
    item = w._tree._sym_items[SYM_REL]
    assert item.checkState(0) == Qt.CheckState.Checked


def test_post_install_select_waits_for_running_scan(qtbot, make_window):
    gate = threading.Event()
    running = scan_with()

    def blocked():
        assert gate.wait(10)
        return running

    final = scan_with()
    w = make_window([scan_with(), blocked, final])
    try:
        w._on_rescan()
        qtbot.waitUntil(lambda: len(make_window.calls) == 2, timeout=5000)
        assert w._worker is not None

        w._on_import_installed(install_result(), stub_plan(make_window.repo))
        assert len(make_window.calls) == 2  # no second scan while one runs
    finally:
        gate.set()
    qtbot.waitUntil(lambda: len(make_window.calls) == 3 and w._worker is None, timeout=5000)
    qtbot.wait(200)
    assert len(make_window.calls) == 3  # exactly one post-install scan
    assert not selected(running, SYM_REL)  # the scan that was already running did not apply it
    assert selected(final, SYM_REL)
    assert selected(final, FP_REL)


def test_post_install_select_unchecks_peer(qtbot, make_window):
    peer = "WurthElektronik"
    first = scan_with(peer=peer, selected_peer=True)
    second = scan_with(peer=peer, selected_peer=True)
    w = make_window([first, second])
    w._on_import_installed(install_result(), stub_plan(make_window.repo))
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    result = w._scan_result
    peer_sym = f"{peer}/Symbols/{LIB}.kicad_sym"
    peer_fp = f"{peer}/Footprints/{FP_LIB}.pretty"
    assert selected(result, SYM_REL)
    assert selected(result, FP_REL)
    assert not selected(result, peer_sym)
    assert not selected(result, peer_fp)
    log = w._log._text.toPlainText()
    assert f"Unchecked {peer_sym}: {LIB} was just installed and has the same nickname" in log


def test_post_install_select_missing_library(qtbot, make_window):
    first = scan_with(selected_usb=True, with_installed=False)
    second = scan_with(selected_usb=True, with_installed=False)
    w = make_window([first, second])
    w._on_import_installed(install_result(), stub_plan(make_window.repo))
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    result = w._scan_result
    assert [lib.rel_path for lib in result.symbol_libs if lib.selected] == [USB_SYM_REL]
    assert [lib.rel_path for lib in result.footprint_libs if lib.selected] == [USB_FP_REL]
    assert w._pending_post_install is None


def test_import_dialog_opens_window_modal(qtbot, make_window, tmp_path, monkeypatch):
    w = make_window([scan_with()])
    installed_calls = []
    monkeypatch.setattr(w, "_on_import_installed", lambda *args: installed_calls.append(args))
    package = tmp_path / "missing.zip"

    w._open_import(package)
    dialog = w._import_dialog
    assert isinstance(dialog, ImportDialog)
    assert dialog.windowModality() == Qt.WindowModality.WindowModal
    assert dialog.parent() is w

    dialog.installed.emit("result", "plan")
    assert installed_calls == [("result", "plan")]
    dialog.issues_logged.emit([Issue(Severity.WARNING, "x.y", "dialog says hello")])
    assert "dialog says hello" in w._log._text.toPlainText()

    w._open_import(package)  # a second open while one is showing creates nothing
    assert w._import_dialog is dialog

    dialog.reject()
    assert w._import_dialog is None


def test_main_window_rescans_after_import_dialog_fixes(qtbot, make_window, tmp_path, monkeypatch):
    backup_root = tmp_path / "atomic_backups"
    monkeypatch.setattr(main_window, "ATOMIC_BACKUP_ROOT", backup_root)
    w = make_window([scan_with()])
    scans: list[int] = []
    monkeypatch.setattr(w, "_start_scan", lambda *args, **kwargs: scans.append(1))

    w._open_import(tmp_path / "missing.zip")
    dialog = w._import_dialog
    assert isinstance(dialog, ImportDialog)
    assert dialog._atomic_backup_root == backup_root

    dialog.atomic_fixes_applied.emit([Issue(Severity.SUCCESS, "atomic.fixed", "fixed from the import dialog")])
    assert "fixed from the import dialog" in w._log._text.toPlainText()
    assert scans == [1]

    dialog.reject()
    assert w._import_dialog is None


# -- tables after the post-install rescan (plan 05-04, D-16, D-17) ---------------------------

def _managed(nick: str, rel: str) -> str:
    return (
        f'  (lib (name "{nick}")(type "KiCad")(uri "${{KICAD_LIB_GITHUB}}/{rel}")'
        f'(options "")(descr ""))\n'
    )


EXT_SYM = '  (lib (name "Ext")(type "KiCad")(uri "C:/ext/Ext.kicad_sym")(options "")(descr ""))\n'
EXT_FP = '  (lib (name "ExtFP")(type "KiCad")(uri "C:/ext/ExtFP.pretty")(options "")(descr ""))\n'


def write_tables_in(repo: Path, sym_entries: str, fp_entries: str) -> tuple[bytes, bytes]:
    sym = f"(sym_lib_table\n  (version 7)\n{sym_entries})\n".encode("utf-8")
    fp = f"(fp_lib_table\n  (version 7)\n{fp_entries})\n".encode("utf-8")
    (repo / "sym-lib-table").write_bytes(sym)
    (repo / "fp-lib-table").write_bytes(fp)
    return sym, fp


def usb_tables(repo: Path, extra_sym: str = "", extra_fp: str = "", *, shared_listed: bool = True) -> tuple[bytes, bytes]:
    """Tables listing the USB symbol library; shared_listed=False leaves Atomic_Footprints out, so the first install adds it."""
    shared_entry = _managed(USB_FP_LIB, USB_FP_REL) if shared_listed else ""
    return write_tables_in(
        repo,
        EXT_SYM + _managed(USB_LIB, USB_SYM_REL) + extra_sym,
        EXT_FP + shared_entry + extra_fp,
    )


def log_text(w) -> str:
    return w._log._text.toPlainText()


def deselect_all_but_ffc(w):
    """The user's ungenerated selection: only the audio connector library is checked."""
    for lib in (*w._scan_result.symbol_libs, *w._scan_result.footprint_libs):
        lib.selected = lib.rel_path in (FFC_SYM_REL, FFC_FP_REL)


def test_tables_new_library_add_only(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo, shared_listed=False)
    first = scan_with(with_installed=False, with_ffc=True)
    second = scan_with(lib=NEW_LIB, with_ffc=True)
    w = make_window([first, second], repo=repo)
    deselect_all_but_ffc(w)
    config_before = make_window.config_file.read_text(encoding="utf-8")

    w._on_import_installed(install_result(), stub_plan(repo, NEW_LIB, new_library=True))
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    sym_line = _managed(NEW_LIB, NEW_SYM_REL).encode("utf-8")
    fp_line = _managed(NEW_FP_LIB, NEW_FP_REL).encode("utf-8")
    sym_new = (repo / "sym-lib-table").read_bytes()
    fp_new = (repo / "fp-lib-table").read_bytes()
    assert sym_new == old_sym[:-2] + sym_line + b")\n"
    assert fp_new == old_fp[:-2] + fp_line + b")\n"
    assert FFC_LIB.encode() not in sym_new
    assert make_window.config_file.read_text(encoding="utf-8") != config_before
    assert "KICAD_LIB_GITHUB" in make_window.config_file.read_text(encoding="utf-8")
    # the post-install path asks through the same helper as Generate
    assert len(make_window.questions) == 1
    assert f"Added {NEW_LIB} to sym-lib-table and {NEW_FP_LIB} to fp-lib-table" in log_text(w)
    assert w._pending_post_install is None
    # the ungenerated selection is still only in the GUI
    assert selected(w._scan_result, FFC_SYM_REL)


def test_tables_new_library_declined_keeps_kicad_config(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo, shared_listed=False)
    first = scan_with(with_installed=False, with_ffc=True)
    second = scan_with(lib=NEW_LIB, with_ffc=True)
    make_window.answer = QMessageBox.StandardButton.No
    w = make_window([first, second], repo=repo)
    deselect_all_but_ffc(w)
    config_before = make_window.config_file.read_bytes()

    w._on_import_installed(install_result(), stub_plan(repo, NEW_LIB, new_library=True))
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    sym_line = _managed(NEW_LIB, NEW_SYM_REL).encode("utf-8")
    fp_line = _managed(NEW_FP_LIB, NEW_FP_REL).encode("utf-8")
    assert (repo / "sym-lib-table").read_bytes() == old_sym[:-2] + sym_line + b")\n"
    assert (repo / "fp-lib-table").read_bytes() == old_fp[:-2] + fp_line + b")\n"
    assert make_window.config_file.read_bytes() == config_before
    assert not (tmp_path / "backups").exists()
    assert len(make_window.questions) == 1
    assert "KiCad path variables left unchanged" in log_text(w)


def test_tables_new_library_repoints_a_stale_entry(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, _ = usb_tables(repo, _managed(NEW_LIB, "Custom/Symbols/Gone.kicad_sym"))
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)

    dialog, _ = run_install(qtbot, w, repo, NEW_LIB, True)

    sym_new = (repo / "sym-lib-table").read_bytes()
    assert sym_new == old_sym.replace(b"Custom/Symbols/Gone.kicad_sym", NEW_SYM_REL.encode())
    assert (repo / "sym-lib-table_backup_1").read_bytes() == old_sym
    updated = f"Updated: {NEW_LIB} in sym-lib-table now points at {NEW_SYM_REL}"
    assert updated in log_text(w)
    text, severity = dialog.rows["tables"]
    assert updated in text
    assert severity is Severity.SUCCESS


def test_tables_new_library_live_clash_warns(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    other = f"WurthElektronik/KiCad-Library/Symbols/{NEW_LIB}.kicad_sym"
    (repo / other).parent.mkdir(parents=True)
    (repo / other).write_text("(kicad_symbol_lib)", encoding="utf-8")
    old_sym, _ = usb_tables(repo, _managed(NEW_LIB, other))
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)

    dialog, _ = run_install(qtbot, w, repo, NEW_LIB, True)

    assert (repo / "sym-lib-table").read_bytes() == old_sym
    assert not (repo / "sym-lib-table_backup_1").exists()
    clash = (
        f"Not added to sym-lib-table: the name {NEW_LIB} already points at {other}; "
        "KiCad still loads that library. Rename one of them."
    )
    assert clash in log_text(w)
    text, severity = dialog.rows["tables"]
    assert clash in text
    assert severity is Severity.WARNING


def test_tables_existing_library_not_in_tables_warns(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo)
    w = make_window([scan_with(with_installed=False), scan_with()], repo=repo)
    config_before = make_window.config_file.read_bytes()

    w._on_import_installed(install_result(), stub_plan(repo))
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    assert (repo / "sym-lib-table").read_bytes() == old_sym
    assert (repo / "fp-lib-table").read_bytes() == old_fp
    assert not list(repo.glob("*_backup_*"))
    assert f"{LIB} is not in the library tables. Press Generate Tables to add it." in log_text(w)
    assert make_window.config_file.read_bytes() == config_before


def test_tables_existing_library_listed_no_warning(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo, _managed(LIB, SYM_REL))
    w = make_window([scan_with(with_installed=False), scan_with()], repo=repo)

    w._on_import_installed(install_result(), stub_plan(repo))
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    assert (repo / "sym-lib-table").read_bytes() == old_sym
    assert (repo / "fp-lib-table").read_bytes() == old_fp
    assert not list(repo.glob("*_backup_*"))
    assert "is not in the library tables" not in log_text(w)


def test_tables_existing_library_repoints_a_stale_entry(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo, _managed(LIB, "Custom/Symbols/Gone.kicad_sym"))
    w = make_window([scan_with(with_installed=False), scan_with()], repo=repo)

    dialog, _ = run_install(qtbot, w, repo, LIB, False)

    assert (repo / "sym-lib-table").read_bytes() == old_sym.replace(
        b"Custom/Symbols/Gone.kicad_sym", SYM_REL.encode()
    )
    assert (repo / "fp-lib-table").read_bytes() == old_fp
    assert (repo / "sym-lib-table_backup_1").read_bytes() == old_sym
    updated = f"Updated: {LIB} in sym-lib-table now points at {SYM_REL}"
    assert updated in log_text(w)
    text, severity = dialog.rows["tables"]
    assert updated in text
    assert severity is Severity.SUCCESS
    assert "generate_hint" not in dialog.rows
    assert "is not in the library tables" not in log_text(w)


def test_tables_existing_library_live_clash_warns(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    other = f"WurthElektronik/KiCad-Library/Symbols/{LIB}.kicad_sym"
    (repo / other).parent.mkdir(parents=True)
    (repo / other).write_text("(kicad_symbol_lib)", encoding="utf-8")
    old_sym, old_fp = usb_tables(repo, _managed(LIB, other))
    w = make_window([scan_with(with_installed=False), scan_with()], repo=repo)

    dialog, _ = run_install(qtbot, w, repo, LIB, False)

    assert (repo / "sym-lib-table").read_bytes() == old_sym
    assert (repo / "fp-lib-table").read_bytes() == old_fp
    assert not list(repo.glob("*_backup_*"))
    clash = (
        f"Not added to sym-lib-table: the name {LIB} already points at {other}; "
        "KiCad still loads that library. Rename one of them."
    )
    assert clash in log_text(w)
    text, severity = dialog.rows["tables"]
    assert clash in text
    assert severity is Severity.WARNING


def test_tables_written_even_when_rescan_fails(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo, shared_listed=False)

    def failing():
        raise RuntimeError("scan boom")

    w = make_window([scan_with(with_installed=False, with_ffc=True), failing], repo=repo)
    deselect_all_but_ffc(w)
    before = w._scan_result

    w._on_import_installed(install_result(), stub_plan(repo, NEW_LIB, new_library=True))
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    assert "Scan error: scan boom" in log_text(w)
    assert (repo / "sym-lib-table").read_bytes() == (
        old_sym[:-2] + _managed(NEW_LIB, NEW_SYM_REL).encode("utf-8") + b")\n"
    )
    assert (repo / "fp-lib-table").read_bytes() == (
        old_fp[:-2] + _managed(NEW_FP_LIB, NEW_FP_REL).encode("utf-8") + b")\n"
    )
    assert w._scan_result is before
    assert selected(w._scan_result, FFC_SYM_REL)
    assert not selected(w._scan_result, USB_SYM_REL)
    assert w._pending_post_install is None


def test_post_install_reveal_current_rows(qtbot, make_window):
    w = make_window([scan_with(with_installed=False), scan_with()])

    w._on_import_installed(install_result(), stub_plan(make_window.repo))
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    assert w._tree._sym_tree.currentItem() is w._tree._sym_items[SYM_REL]
    assert w._tree._fp_tree.currentItem() is w._tree._fp_items[FP_REL]
    assert w._tree._sym_items[SYM_REL].parent().isExpanded()
    assert w._tree._fp_items[FP_REL].parent().isExpanded()


def test_tables_missing_destination_logs_error(qtbot, make_window, tmp_path):
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)])
    gone = tmp_path / "gone"
    w._dest_combo.setCurrentText(str(gone))

    w._on_import_installed(install_result(), stub_plan(make_window.repo, NEW_LIB, new_library=True))
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    assert f"Destination folder does not exist: {gone}" in log_text(w)
    assert not gone.exists()
    assert w._pending_post_install is None


@pytest.mark.parametrize("new_library", [True, False], ids=["new_library", "existing_library"])
@pytest.mark.parametrize("blank", ["", "   "], ids=["empty", "spaces"])
def test_tables_blank_destination_writes_nothing(
    qtbot, make_window, tmp_path, monkeypatch, new_library, blank
):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo, shared_listed=False)
    lib = NEW_LIB if new_library else LIB
    w = make_window([scan_with(with_installed=False), scan_with(lib=lib)], repo=repo)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    w._dest_combo.setCurrentText(blank)
    questions_before = len(make_window.questions)

    dialog, _ = run_install(qtbot, w, repo, lib, new_library)

    assert os.listdir(cwd) == []
    assert (repo / "sym-lib-table").read_bytes() == old_sym
    assert (repo / "fp-lib-table").read_bytes() == old_fp
    assert not list(repo.glob("*_backup_*"))
    assert NO_DEST in log_text(w)
    assert dialog.rows["tables"] == (NO_DEST, Severity.WARNING)
    assert w._pending_post_install is None
    assert len(make_window.questions) == questions_before


# -- drag and drop, toolbar button and busy state (plan 05-08, UX-01, D-03, D-19) -------------

BUSY_TEXT = "Import is unavailable while a scan is running."


def _mime(*paths) -> QMimeData:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    return mime


def _drop_event(mime: QMimeData) -> QDropEvent:
    event = QDropEvent(
        QPointF(10, 10), Qt.DropAction.CopyAction, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    event.setAccepted(False)
    return event


def _enter_event(mime: QMimeData) -> QDragEnterEvent:
    event = QDragEnterEvent(
        QPoint(10, 10), Qt.DropAction.CopyAction, mime,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    )
    event.setAccepted(False)
    return event


@pytest.fixture
def opened(monkeypatch):
    """Record the path each _open_import call receives."""
    calls = []
    monkeypatch.setattr(
        main_window.MainWindow, "_open_import", lambda self, path=None: calls.append(path)
    )
    return calls


def test_drop_one_zip_opens_dialog(make_window, opened, tmp_path):
    w = make_window([scan_with()])
    zip_path = tmp_path / "Part.ZIP"
    zip_path.write_bytes(b"PK")
    mime = _mime(zip_path)
    event = _drop_event(mime)
    w.dropEvent(event)
    assert opened == [zip_path]
    assert event.isAccepted()

    folder = tmp_path / "vendor_folder"
    folder.mkdir()
    mime2 = _mime(folder)
    w.dropEvent(_drop_event(mime2))
    assert opened == [zip_path, folder]


def test_drop_several_paths_refused(make_window, opened, tmp_path):
    w = make_window([scan_with()])
    one = tmp_path / "a.zip"
    two = tmp_path / "b.zip"
    one.write_bytes(b"PK")
    two.write_bytes(b"PK")
    mime = _mime(one, two)
    event = _drop_event(mime)
    w.dropEvent(event)
    assert opened == []
    assert not event.isAccepted()
    log = w._log._text.toPlainText()
    assert "Drop ignored: drop one .zip file or one folder at a time." in log
    assert theme.AMBER.lower() in w._log._text.toHtml().lower()  # logged at warning level


def test_drop_wrong_type_refused(make_window, opened, tmp_path):
    w = make_window([scan_with()])
    deep = tmp_path / "some" / "very" / "long" / "folder"
    deep.mkdir(parents=True)
    notes = deep / "notes.txt"
    notes.write_text("x", encoding="utf-8")
    mime = _mime(notes)
    event = _drop_event(mime)
    w.dropEvent(event)
    assert opened == []
    assert not event.isAccepted()
    log = w._log._text.toPlainText()
    assert "Drop ignored: 'notes.txt' is not a .zip file or a folder." in log
    assert "very" not in log  # base name only


def test_drop_refused_while_busy(make_window, opened, tmp_path):
    w = make_window([scan_with()])
    zip_path = tmp_path / "Part.zip"
    zip_path.write_bytes(b"PK")
    mime = _mime(zip_path)

    w._worker = object()  # a scan is running
    try:
        enter = _enter_event(mime)
        w.dragEnterEvent(enter)
        assert not enter.isAccepted()
        assert w.statusBar().currentMessage() == BUSY_TEXT
        w.statusBar().clearMessage()
        drop = _drop_event(mime)
        w.dropEvent(drop)
        assert not drop.isAccepted()
        assert w.statusBar().currentMessage() == BUSY_TEXT
    finally:
        w._worker = None

    w.statusBar().clearMessage()
    w._import_dialog = object()  # the import dialog is open
    try:
        enter = _enter_event(mime)
        w.dragEnterEvent(enter)
        assert not enter.isAccepted()
        assert w.statusBar().currentMessage() == BUSY_TEXT
        drop = _drop_event(mime)
        w.dropEvent(drop)
        assert not drop.isAccepted()
    finally:
        w._import_dialog = None
    assert opened == []


def test_drag_enter_accepts_urls_when_idle(make_window, tmp_path):
    w = make_window([scan_with()])
    zip_path = tmp_path / "Part.zip"
    zip_path.write_bytes(b"PK")
    with_urls = _mime(zip_path)
    enter = _enter_event(with_urls)
    w.dragEnterEvent(enter)
    assert enter.isAccepted()

    text_only = QMimeData()
    text_only.setText("hello")
    enter = _enter_event(text_only)
    w.dragEnterEvent(enter)
    assert not enter.isAccepted()


def test_busy_state_controls(qtbot, make_window):
    w = make_window([scan_with()])
    controls = (
        w._act_import, w._import_btn, w._select_all_btn, w._deselect_all_btn,
        w._rescan_btn, w._act_rescan, w._act_set_kicad_path, w._act_generate,
        w._generate_btn,
    )
    w._set_scan_running(True)
    assert [c.isEnabled() for c in controls] == [False] * len(controls)
    w._set_scan_running(False)
    assert [c.isEnabled() for c in controls] == [True] * len(controls)


def test_toolbar_import_button_first(qtbot, make_window, monkeypatch):
    w = make_window([scan_with()])
    toolbar = w.centralWidget().layout().itemAt(0).layout()
    assert toolbar.itemAt(0).widget() is w._import_btn
    assert w._import_btn.text() == "Import Part..."
    assert w._import_btn.toolTip() == "Import a vendor package (Ctrl+I)"
    assert toolbar.itemAt(1).spacerItem() is not None
    assert toolbar.itemAt(1).spacerItem().sizeHint().width() == 16
    assert toolbar.itemAt(2).widget() is w._select_all_btn
    assert w._import_btn.styleSheet() == ""

    calls = []
    monkeypatch.setattr(w, "_open_import", lambda *args: calls.append(args))
    w._import_btn.click()
    assert calls == [()]


def test_generate_button_primary_style(make_window):
    w = make_window([scan_with()])
    assert w._generate_btn.styleSheet() == theme.PRIMARY_BUTTON_QSS


# -- plan 05-11 Task 1: the main window cannot close an installing dialog (D-10, T-05-33) -------------

def test_main_window_close_ignored_while_installing(make_window):
    w = make_window([scan_with()])
    w._import_dialog = types.SimpleNamespace(
        is_installing=lambda: True, is_finishing=lambda: False, reject=lambda: pytest.fail("rejected")
    )
    try:
        event = QCloseEvent()
        w.closeEvent(event)
        assert not event.isAccepted()
    finally:
        w._import_dialog = None


# -- plan 06-06 Task 1: nor can it close a dialog that runs a git job (D-07, T-06-24) -----------------

def test_main_window_close_ignored_while_committing(make_window):
    w = make_window([scan_with()])
    w._import_dialog = types.SimpleNamespace(
        is_installing=lambda: False,
        is_committing=lambda: True,
        is_finishing=lambda: False,
        reject=lambda: pytest.fail("rejected"),
    )
    try:
        event = QCloseEvent()
        w.closeEvent(event)
        assert not event.isAccepted()
    finally:
        w._import_dialog = None


# -- plan 11-09 Task 1: the read-only probe does not keep the window open (IN-02) ---------------------

def test_main_window_closes_while_probe_runs(make_window):
    w = make_window([scan_with()])
    rejected = []
    w._import_dialog = types.SimpleNamespace(
        is_installing=lambda: False,
        is_committing=lambda: False,
        is_probing=lambda: True,
        is_finishing=lambda: False,
        reject=lambda: rejected.append(True),
    )
    try:
        event = QCloseEvent()
        w.closeEvent(event)
        assert event.isAccepted()
        assert rejected == [True]
    finally:
        w._import_dialog = None


# -- plan 05-11 Task 2: the status rows of the Result view (POST-01, POST-02, D-16, D-17) ----------------

class RecordingDialog:
    """Stands in for the import dialog: records the post-install status rows the main window sets."""

    def __init__(self):
        self.calls = []

    def is_installing(self):
        return False

    def is_committing(self):
        return False

    def is_probing(self):
        return False

    def is_finishing(self):
        return False

    def reject(self):
        pass

    def set_post_install_status(self, row, text, severity):
        self.calls.append((row, text, severity))

    @property
    def rows(self):
        return {row: (text, severity) for row, text, severity in self.calls}


def installed_for(lib: str, new_library: bool) -> InstallResult:
    return InstallResult(ok=True, library=lib, new_library=new_library, touched=(), issues=())


def run_install(qtbot, w, repo, lib, new_library, **plan_options):
    """Report an install to the window with a recording dialog; return the dialog and the rows seen at once."""
    dialog = RecordingDialog()
    w._import_dialog = dialog
    try:
        w._on_import_installed(
            installed_for(lib, new_library), stub_plan(repo, lib, new_library=new_library, **plan_options)
        )
        at_once = dict(dialog.rows)
        qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
        settle(qtbot, w)
    finally:
        w._import_dialog = None
    return dialog, at_once


def test_status_rows_new_library_settle(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    usb_tables(repo, shared_listed=False)
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)

    dialog, at_once = run_install(qtbot, w, repo, NEW_LIB, True)

    assert at_once == {
        "library_list": ("Rescanning...", Severity.INFO),
        "tables": ("Updating...", Severity.INFO),
    }
    assert dialog.rows == {
        "library_list": (f"Updated; {NEW_LIB} is selected", Severity.SUCCESS),
        "tables": (f"Added {NEW_LIB} to sym-lib-table and {NEW_FP_LIB} to fp-lib-table", Severity.SUCCESS),
    }
    assert w.statusBar().currentMessage() == f"Installed CSD85301Q2 into {NEW_LIB}"


def test_post_install_check_runs_off_gui_thread(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    usb_tables(repo, shared_listed=False)
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)

    run_install(qtbot, w, repo, NEW_LIB, True)

    assert len(make_window.check_threads) == 1
    assert make_window.check_threads[0] != threading.main_thread().ident


def test_status_rows_existing_library_hint(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    usb_tables(repo)
    w = make_window([scan_with(with_installed=False), scan_with()], repo=repo)

    dialog, at_once = run_install(qtbot, w, repo, LIB, False)

    assert at_once == {
        "library_list": ("Rescanning...", Severity.INFO),
        "tables": ("Not needed: existing libraries", Severity.INFO),
    }
    assert dialog.rows == {
        "library_list": (f"Updated; {LIB} is selected", Severity.SUCCESS),
        "tables": ("Not needed: existing libraries", Severity.INFO),
        "generate_hint": (
            f"⚠ {LIB} is not in the library tables. Press Generate Tables to add it.", Severity.WARNING,
        ),
    }


def test_status_rows_existing_library_listed_has_no_hint(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    usb_tables(repo, _managed(LIB, SYM_REL), _managed(FP_LIB, FP_REL))
    w = make_window([scan_with(with_installed=False), scan_with()], repo=repo)

    dialog, _ = run_install(qtbot, w, repo, LIB, False)

    assert "generate_hint" not in dialog.rows
    assert dialog.rows["tables"] == ("Not needed: existing libraries", Severity.INFO)


def test_status_rows_new_library_already_listed(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    usb_tables(repo, _managed(NEW_LIB, NEW_SYM_REL), _managed(NEW_FP_LIB, NEW_FP_REL))
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)

    dialog, _ = run_install(qtbot, w, repo, NEW_LIB, True)

    assert dialog.rows["tables"] == (f"sym-lib-table already lists {NEW_LIB}; not changed; fp-lib-table already lists {NEW_FP_LIB}; not changed", Severity.INFO)


def test_status_rows_library_not_in_scan(qtbot, make_window, tmp_path):
    w = make_window([scan_with(with_installed=False), scan_with(with_installed=False)])

    dialog, _ = run_install(qtbot, w, make_window.repo, LIB, False)

    assert dialog.rows["library_list"] == (f"Updated; {LIB} was not found in the scan", Severity.WARNING)


def test_status_rows_rescan_failed_and_table_error(qtbot, make_window, tmp_path):
    import os
    import stat

    repo = tmp_path / "repo"
    repo.mkdir()
    usb_tables(repo)

    def failing():
        raise RuntimeError("scan boom")

    w = make_window([scan_with(with_installed=False), failing], repo=repo)
    os.chmod(repo / "sym-lib-table", stat.S_IREAD)
    try:
        dialog, _ = run_install(qtbot, w, repo, NEW_LIB, True)
    finally:
        os.chmod(repo / "sym-lib-table", stat.S_IREAD | stat.S_IWRITE)

    assert dialog.rows["library_list"] == ("Rescan failed - see the log", Severity.ERROR)
    text, severity = dialog.rows["tables"]
    assert severity is Severity.ERROR
    assert not text.startswith("Added")
    assert text in log_text(w)  # the same failure line is in the log


def test_status_rows_destination_missing(qtbot, make_window, tmp_path):
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)])
    gone = tmp_path / "gone"
    w._dest_combo.setCurrentText(str(gone))

    dialog, _ = run_install(qtbot, w, make_window.repo, NEW_LIB, True)

    assert dialog.rows["tables"] == (f"Destination folder does not exist: {gone}", Severity.ERROR)


def test_status_rows_skipped_after_dialog_closed(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    usb_tables(repo, shared_listed=False)
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)
    dialog = RecordingDialog()
    w._import_dialog = dialog
    w._on_import_installed(installed_for(NEW_LIB, True), stub_plan(repo, NEW_LIB, new_library=True))
    w._import_dialog = None  # the dialog is closed before the rescan ends
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    assert set(dialog.rows) == {"library_list", "tables"}
    assert dialog.rows["library_list"] == ("Rescanning...", Severity.INFO)  # nothing was set after the close
    assert f"Added {NEW_LIB} to sym-lib-table and {NEW_FP_LIB} to fp-lib-table" in log_text(w)  # the steps still ran
    assert w._pending_post_install is None


def test_post_install_steps_never_run_git(qtbot, make_window, tmp_path, monkeypatch):
    import subprocess

    calls = []
    real_run, real_popen = subprocess.run, subprocess.Popen

    def run(args, *a, **kw):
        calls.append(args)
        return real_run(args, *a, **kw)

    class Popen(real_popen):
        def __init__(self, args, *a, **kw):
            calls.append(args)
            super().__init__(args, *a, **kw)

    repo = tmp_path / "repo"
    repo.mkdir()
    usb_tables(repo)
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(subprocess, "Popen", Popen)

    run_install(qtbot, w, repo, NEW_LIB, True)

    names = [Path(str(a[0] if isinstance(a, (list, tuple)) else a).split()[0]).name.lower() for a in calls]
    assert not [n for n in names if "git" in n], names


def test_main_window_close_closes_idle_dialog_first(qtbot, make_window, tmp_path):
    w = make_window([scan_with()])
    w._open_import()
    dialog = w._import_dialog
    assert isinstance(dialog, ImportDialog)
    order = []
    real_reject = dialog.reject
    dialog.reject = lambda: (order.append("dialog"), real_reject())
    real_save = main_window.save_window_geometry
    main_window.save_window_geometry = lambda geometry: (order.append("geometry"), real_save(geometry))
    try:
        event = QCloseEvent()
        w.closeEvent(event)
    finally:
        main_window.save_window_geometry = real_save
    assert event.isAccepted()
    assert order == ["dialog", "geometry"]
    assert w._import_dialog is None
    assert dialog._closing


# -- Phase 12 plan 12-07: closing the window while the dialog still builds (D-06, REV-04) -------------------

UL_ZIP = Path(__file__).resolve().parent.parent / "downloaded_examples" / "ul_CSD85301Q2.zip"


def gated_dialog_core(monkeypatch, gates, started):
    """Make the window's import core hold its first build_plan call open until a gate is released."""
    from kicad_lib_manager.importer.commit_step import CommitProbe

    def gated_build(candidate, options, layout, tools=ToolContext(), **kwargs):
        gate = threading.Event()
        gates.append(gate)
        started.set()
        assert gate.wait(30)
        return real_build_plan(candidate, options, layout, tools, **kwargs)

    core = replace(
        ImportCore(),
        detect_tools=lambda kicad_fp_dir: ToolContext(),
        kicad_running=lambda: [],
        probe_commit=lambda cplan, **kwargs: CommitProbe(state="unavailable", reason="not used"),
        build_plan=gated_build,
    )
    monkeypatch.setattr(main_window, "IMPORT_CORE", core)


@pytest.fixture
def held_build_window(qtbot, make_window, monkeypatch):
    """A shown window whose import dialog has a build held open; the gates are released at teardown."""
    gates: list[threading.Event] = []
    started = threading.Event()
    gated_dialog_core(monkeypatch, gates, started)
    w = make_window([scan_with()])
    w.show()
    w._open_import(UL_ZIP)
    qtbot.waitUntil(started.is_set, timeout=30000)
    yield w, gates
    for gate in gates:
        gate.set()


def test_main_window_close_waits_for_dialog_build(qtbot, held_build_window):
    w, gates = held_build_window
    dialog = w._import_dialog
    w.close()  # returns at once: the build is still held
    assert not gates[0].is_set()
    assert w.isVisible()
    assert w._import_dialog is dialog and dialog.is_finishing()

    gates[0].set()
    qtbot.waitUntil(lambda: not w.isVisible(), timeout=30000)
    assert w._import_dialog is None


def test_main_window_close_cancelled_with_dialog(qtbot, held_build_window):
    w, gates = held_build_window
    dialog = w._import_dialog
    w.close()
    assert dialog.is_finishing() and w._close_after_dialog

    dialog._finish_cancel.click()  # Cancel drops the window's pending close too
    assert not w._close_after_dialog
    gates[0].set()
    qtbot.waitUntil(
        lambda: dialog._building is None and not any(x.isRunning() for x in dialog._workers), timeout=30000
    )
    qtbot.wait(150)
    assert w.isVisible()
    assert w._import_dialog is dialog

    dialog.reject()  # an idle close of the dialog alone leaves the main window open
    qtbot.waitUntil(lambda: w._import_dialog is None, timeout=30000)
    qtbot.wait(150)
    assert w.isVisible()


# -- two nicknames in the post-install table step (plan 10-11, D-15, D-16) -----------------------

SHARED_FP = "Atomic_Footprints"
SHARED_FP_REL = f"Custom/Footprints/{SHARED_FP}.pretty"


def test_tables_new_symbol_and_new_footprint_library_use_their_own_names(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo, shared_listed=False)
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)

    w._on_import_installed(
        install_result(), stub_plan(repo, NEW_LIB, new_library=True, footprint_library=SHARED_FP)
    )
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    sym_new = (repo / "sym-lib-table").read_bytes()
    fp_new = (repo / "fp-lib-table").read_bytes()
    assert sym_new == old_sym[:-2] + _managed(NEW_LIB, NEW_SYM_REL).encode("utf-8") + b")\n"
    assert fp_new == old_fp[:-2] + _managed(SHARED_FP, SHARED_FP_REL).encode("utf-8") + b")\n"
    assert f"Added {NEW_LIB} to sym-lib-table and {SHARED_FP} to fp-lib-table" in log_text(w)


def test_tables_only_the_footprint_library_is_new(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo, _managed(LIB, SYM_REL), shared_listed=False)
    w = make_window([scan_with(with_installed=False), scan_with()], repo=repo)

    plan = stub_plan(repo, LIB, new_symbol_lib=False, new_footprint_lib=True, footprint_library=SHARED_FP)
    w._on_import_installed(install_result(), plan)
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    assert (repo / "sym-lib-table").read_bytes() == old_sym
    assert (repo / "fp-lib-table").read_bytes() == old_fp[:-2] + _managed(SHARED_FP, SHARED_FP_REL).encode("utf-8") + b")\n"
    assert f"Added {SHARED_FP} to fp-lib-table" in log_text(w)
    assert "is not in the library tables" not in log_text(w)


def test_tables_shared_footprint_library_already_listed_adds_only_the_symbol(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo)
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)

    w._on_import_installed(install_result(), stub_plan(repo, NEW_LIB, new_symbol_lib=True, new_footprint_lib=False))
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    assert (repo / "sym-lib-table").read_bytes() == old_sym[:-2] + _managed(NEW_LIB, NEW_SYM_REL).encode("utf-8") + b")\n"
    assert (repo / "fp-lib-table").read_bytes() == old_fp
    assert f"Added {NEW_LIB} to sym-lib-table" in log_text(w)


def test_tables_a_footprint_library_outside_the_repo_gets_no_fp_entry(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo)
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)

    plan = stub_plan(repo, NEW_LIB, new_library=True, footprint_library="Package_TO_SOT_SMD", pretty=NEW_FP_LIB)
    w._on_import_installed(install_result(), plan)
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    assert (repo / "sym-lib-table").read_bytes() == old_sym[:-2] + _managed(NEW_LIB, NEW_SYM_REL).encode("utf-8") + b")\n"
    assert (repo / "fp-lib-table").read_bytes() == old_fp
    assert b"Package_TO_SOT_SMD" not in (repo / "fp-lib-table").read_bytes()
    assert f"Added {NEW_LIB} to sym-lib-table" in log_text(w)


def test_hint_names_both_libraries_when_neither_is_in_the_tables(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    usb_tables(repo, shared_listed=False)
    w = make_window([scan_with(with_installed=False), scan_with()], repo=repo)

    plan = stub_plan(repo, LIB, new_symbol_lib=False, new_footprint_lib=False, footprint_library=SHARED_FP)
    w._on_import_installed(install_result(), plan)
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    assert f"{LIB} and {SHARED_FP} are not in the library tables. Press Generate Tables to add them." in log_text(w)


def test_tables_an_official_link_into_a_new_symbol_library_adds_only_the_symbol_entry(qtbot, make_window, tmp_path):
    # The part is linked to KiCad's own Package_TO_SOT_SMD, so nothing of Custom/Footprints is written or listed (D-16)
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo, shared_listed=False)
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)

    plan = stub_plan(
        repo, NEW_LIB, new_symbol_lib=True, new_footprint_lib=False, footprint_library="Package_TO_SOT_SMD", pretty=SHARED_FP
    )
    w._on_import_installed(install_result(), plan)
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    assert (repo / "sym-lib-table").read_bytes() == old_sym[:-2] + _managed(NEW_LIB, NEW_SYM_REL).encode("utf-8") + b")\n"
    assert (repo / "fp-lib-table").read_bytes() == old_fp
    assert f"Added {NEW_LIB} to sym-lib-table" in log_text(w)


def test_tables_new_symbol_library_adds_the_existing_unlisted_footprint_library(qtbot, make_window, tmp_path):
    # WR-05: Atomic_Footprints exists on disk but fp-lib-table does not list it, so the install adds it
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo, shared_listed=False)
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)

    w._on_import_installed(install_result(), stub_plan(repo, NEW_LIB, new_symbol_lib=True, new_footprint_lib=False))
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    assert (repo / "sym-lib-table").read_bytes() == old_sym[:-2] + _managed(NEW_LIB, NEW_SYM_REL).encode("utf-8") + b")\n"
    assert (repo / "fp-lib-table").read_bytes() == old_fp[:-2] + _managed(SHARED_FP, SHARED_FP_REL).encode("utf-8") + b")\n"
    assert f"Added {NEW_LIB} to sym-lib-table and {SHARED_FP} to fp-lib-table" in log_text(w)
    assert "is not in the library tables" not in log_text(w)


def test_tables_new_symbol_library_leaves_a_listed_footprint_library_alone(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_sym, old_fp = usb_tables(repo)
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)

    w._on_import_installed(install_result(), stub_plan(repo, NEW_LIB, new_symbol_lib=True, new_footprint_lib=False))
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
    settle(qtbot, w)

    fp_bytes = (repo / "fp-lib-table").read_bytes()
    assert fp_bytes == old_fp
    assert fp_bytes.decode("utf-8").count(f'(name "{SHARED_FP}")') == 1
    assert not list(repo.glob("fp-lib-table_backup_*"))
    assert (repo / "sym-lib-table").read_bytes() == old_sym[:-2] + _managed(NEW_LIB, NEW_SYM_REL).encode("utf-8") + b")\n"
    assert f"fp-lib-table already lists {SHARED_FP}; not changed" in log_text(w)


def test_status_rows_new_symbol_library_adds_an_unlisted_footprint_library(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    usb_tables(repo, shared_listed=False)
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)

    dialog, at_once = run_install(qtbot, w, repo, NEW_LIB, True, new_footprint_lib=False)

    assert at_once["tables"] == ("Updating...", Severity.INFO)
    assert dialog.rows["tables"] == (
        f"Added {NEW_LIB} to sym-lib-table and {SHARED_FP} to fp-lib-table", Severity.SUCCESS,
    )
    assert "generate_hint" not in dialog.rows


def test_status_rows_new_symbol_library_with_a_listed_footprint_library(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    usb_tables(repo)
    w = make_window([scan_with(with_installed=False), scan_with(lib=NEW_LIB)], repo=repo)

    dialog, _ = run_install(qtbot, w, repo, NEW_LIB, True, new_footprint_lib=False)

    assert dialog.rows["tables"] == (
        f"Added {NEW_LIB} to sym-lib-table; fp-lib-table already lists {SHARED_FP}; not changed", Severity.INFO,
    )
    assert "generate_hint" not in dialog.rows


# -- the shared User Guide beside the import window (plan 12-18, G-12-22) ---------------------------

from PySide6.QtWidgets import QApplication  # noqa: E402
from test_main_window import (  # noqa: E402,F401
    _close_guides,
    click_guide_row,
    click_in_window,
    guide_key,
    guide_windows,
)

from kicad_lib_manager.importer.content import ContentText  # noqa: E402
from kicad_lib_manager.widgets.atomic_check_dialog import AtomicCheckDialog  # noqa: E402
from kicad_lib_manager.widgets.content_view import ContentViewDialog  # noqa: E402


def open_import_window(qtbot, w, tmp_path):
    w.show()
    qtbot.waitExposed(w)
    w._open_import(tmp_path / "missing.zip")
    dialog = w._import_dialog
    qtbot.waitUntil(dialog.isVisible, timeout=5000)
    return dialog


def test_import_help_uses_the_shared_guide(qtbot, make_window, tmp_path):
    w = make_window([scan_with()])
    dialog = open_import_window(qtbot, w, tmp_path)
    assert w._guide is None
    dialog._help_action.trigger()
    guide = w._guide
    assert guide is not None and guide.isVisible()
    assert guide_key(guide) == "importing"
    assert dialog._help_dialog is None
    assert guide not in dialog.findChildren(type(guide))

    guide.show_topic("shortcuts")
    dialog._help_action.trigger()
    assert w._guide is guide and guide_key(guide) == "importing"
    assert len(guide_windows()) == 1
    dialog.reject()


def test_guide_takes_clicks_beside_the_import_window_and_its_dialogs(qtbot, make_window, tmp_path):
    w = make_window([scan_with()])
    dialog = open_import_window(qtbot, w, tmp_path)
    dialog._help_action.trigger()
    guide = w._guide
    qtbot.waitExposed(guide)

    # The main window stays locked while the import window is open; the guide does not
    clicks = []
    w._select_all_btn.clicked.connect(lambda: clicks.append(True))
    click_in_window(w, w._select_all_btn)
    assert clicks == []
    click_guide_row(guide, "shortcuts")
    qtbot.waitUntil(lambda: guide_key(guide) == "shortcuts", timeout=5000)

    view = ContentViewDialog(ContentText(title="View", header="", body="text", kind="error"), parent=dialog)
    view.open()
    qtbot.waitExposed(view)
    assert view.windowModality() == Qt.WindowModality.WindowModal
    click_guide_row(guide, "importing")
    qtbot.waitUntil(lambda: guide_key(guide) == "importing", timeout=5000)
    view.close()

    atomic = AtomicCheckDialog(ScanResult(), tmp_path, parent=dialog)
    atomic.open()
    qtbot.waitExposed(atomic)
    click_guide_row(guide, "shortcuts")
    qtbot.waitUntil(lambda: guide_key(guide) == "shortcuts", timeout=5000)
    assert QApplication.activeModalWidget() is not guide
    atomic.close()
    dialog.reject()


def test_guide_stays_open_after_the_import_window_closes(qtbot, make_window, tmp_path):
    w = make_window([scan_with()])
    dialog = open_import_window(qtbot, w, tmp_path)
    dialog._help_action.trigger()
    guide = w._guide
    qtbot.waitExposed(guide)

    dialog._start_cancel_btn.click()
    qtbot.waitUntil(lambda: w._import_dialog is None, timeout=30000)
    assert w._import_dialog is None
    assert guide.isVisible() and w._guide is guide
    click_guide_row(guide, "shortcuts")
    qtbot.waitUntil(lambda: guide_key(guide) == "shortcuts", timeout=5000)
