"""Offscreen MainWindow tests for the import entry point and the post-install rescan (plan 05-01).

The harness mirrors tests/test_main_window.py (fixtures cannot be imported across test
modules): QSettings goes into tmp_path and scan, KiCad detection, REPO_ROOT and the KiCad
config writer are replaced before the window exists.
"""

import threading
import types
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QKeySequence

from kicad_lib_manager import library_scanner, main_window, settings
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.plan import InstallResult
from kicad_lib_manager.models import (
    FootprintLibrary, Issue, ScanResult, Severity, SymbolLibrary,
)
from kicad_lib_manager.widgets.import_dialog import ImportDialog

LIB = "IC_Battery_Charger_TI"
SYM_REL = f"Custom/Symbols/{LIB}.kicad_sym"
FP_REL = f"Custom/Footprints/{LIB}.pretty"
USB_SYM_REL = "Custom/Symbols/Connector_USB_GCT.kicad_sym"
USB_FP_REL = "Custom/Footprints/Connector_USB_GCT.pretty"


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

        def fake_scan(root, progress=None, kicad_fp_dir=None):
            calls.append((root, kicad_fp_dir))
            item = queue.pop(0) if len(queue) > 1 else queue[0]
            return item() if callable(item) else item

        config_base = tmp_path / "kicad_cfg"
        config_base.mkdir(exist_ok=True)
        config_file = config_base / "10.0" / "kicad_common.json"
        config_file.parent.mkdir(exist_ok=True)
        config_file.write_text('{"environment": {"vars": null}}\n', encoding="utf-8")

        def fake_sync(repo_root):
            return library_scanner.sync_kicad_path_vars(
                repo_root,
                config_base=config_base,
                backup_root=tmp_path / "backups",
                running=lambda: [],
            )

        monkeypatch.setattr(main_window, "REPO_ROOT", repo)
        monkeypatch.setattr(main_window, "load_kicad_fp_dir", lambda: fp_dir)
        monkeypatch.setattr(main_window, "scan_all", fake_scan)
        monkeypatch.setattr(main_window, "sync_kicad_path_vars", fake_sync)
        make.calls = calls
        make.repo = repo
        w = main_window.MainWindow()
        qtbot.addWidget(w)
        if wait:
            qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
        return w

    make.calls = []
    make.repo = None
    return make


def scan_with(*, selected_usb=False, with_installed=True, peer=None, selected_peer=False) -> ScanResult:
    """A scan holding Connector_USB_GCT and (optionally) the installed library, with an optional same-nickname peer."""
    symbols = [SymbolLibrary("Connector_USB_GCT", USB_SYM_REL, "Custom")]
    footprints = [FootprintLibrary("Connector_USB_GCT", USB_FP_REL, "Custom")]
    if with_installed:
        sym = SymbolLibrary(LIB, SYM_REL, "Custom")
        fp = FootprintLibrary(LIB, FP_REL, "Custom")
        symbols.append(sym)
        footprints.append(fp)
        if peer is not None:
            peer_sym = SymbolLibrary(LIB, f"{peer}/Symbols/{LIB}.kicad_sym", peer)
            peer_fp = FootprintLibrary(LIB, f"{peer}/Footprints/{LIB}.pretty", peer)
            sym.collision_peers = [peer_sym.rel_path]
            fp.collision_peers = [peer_fp.rel_path]
            peer_sym.collision_peers = [sym.rel_path]
            peer_fp.collision_peers = [fp.rel_path]
            peer_sym.selected = peer_fp.selected = selected_peer
            symbols.append(peer_sym)
            footprints.append(peer_fp)
    symbols[0].selected = footprints[0].selected = selected_usb
    return ScanResult(symbol_libs=symbols, footprint_libs=footprints)


def stub_plan(repo: Path):
    layout = RepoLayout.for_repo(repo)
    return types.SimpleNamespace(
        symbol_name="CSD85301Q2",
        library=LIB,
        new_library=False,
        symbol_lib_path=layout.symbols_dir / f"{LIB}.kicad_sym",
        pretty_path=layout.footprints_dir / f"{LIB}.pretty",
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
    # the user keeps Connector_USB_GCT checked in the GUI
    for lib in (*w._scan_result.symbol_libs, *w._scan_result.footprint_libs):
        lib.selected = lib.rel_path in (USB_SYM_REL, USB_FP_REL)
    before = len(make_window.calls)

    w._on_import_installed(install_result(), stub_plan(make_window.repo))
    assert len(make_window.calls) == before + 1
    assert w._progress is None
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

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

    result = w._scan_result
    peer_sym = f"{peer}/Symbols/{LIB}.kicad_sym"
    peer_fp = f"{peer}/Footprints/{LIB}.pretty"
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
