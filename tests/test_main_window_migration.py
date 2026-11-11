"""Offscreen MainWindow tests for wiring the migration window into the menu (D-13, D-24).

Own fixture (tests do not import from other test modules): isolated QSettings, patched
REPO_ROOT / load_kicad_fp_dir / scan_all / kicad_running / sync_kicad_path_vars (same
isolation as tests/test_main_window.py), plus a real Custom/Symbols folder so
migration_reason() finds (or does not find) something to migrate, and MigrationDialog
replaced by a lightweight fake that records its construction and connections instead of
reading a real inventory or opening a real Qt window -- migration_dialog.py's own
behavior is covered by tests/test_migration_dialog*.py.
"""

import threading
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QDialog, QMessageBox

from kicad_lib_manager import kicad_setup, library_scanner, main_window, settings
from kicad_lib_manager.library_scanner import ConfirmAnswer
from kicad_lib_manager.models import FootprintLibrary, ScanResult, SymbolLibrary


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path / "qsettings"),
    )
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


class FakeMigrationDialog(QDialog):
    """Stands in for the real MigrationDialog: records construction/connections only.

    migration_dialog.py's own behavior (the preview, Run, the Result view) is tested in
    tests/test_migration_dialog*.py; these tests only need the signals and status methods
    the main window wires against.
    """

    help_requested = Signal()
    migrated = Signal(object)
    generate_requested = Signal()
    setup_chooser_requested = Signal()
    issues_logged = Signal(list)
    atomic_check_requested = Signal(str, str)

    instances: list["FakeMigrationDialog"] = []

    def __init__(self, repo_root, kicad_fp_dir, *, core=None, parent=None):
        super().__init__(parent)
        self.repo_root = repo_root
        self.kicad_fp_dir = kicad_fp_dir
        self.core = core
        self._running = False
        self._committing = False
        self.opened = False
        FakeMigrationDialog.instances.append(self)

    def is_running(self) -> bool:
        return self._running

    def is_committing(self) -> bool:
        return self._committing

    def is_busy(self) -> bool:
        return self._running or self._committing

    def open(self):
        self.opened = True
        super().open()


@pytest.fixture(autouse=True)
def _reset_fake_dialogs():
    FakeMigrationDialog.instances = []
    yield
    FakeMigrationDialog.instances = []


@pytest.fixture
def make_window(qtbot, monkeypatch, tmp_path):
    def make(
        results, repo=None, wait=True,
        symbols=("IC_LDO_TI",), pretty_dirs=(), bak_files=(),
    ):
        repo = Path(repo) if repo is not None else tmp_path / "repo"
        repo.mkdir(parents=True, exist_ok=True)
        fp_dir = tmp_path / "kicad_fp"
        fp_dir.mkdir(exist_ok=True)

        custom_symbols = repo / "Custom" / "Symbols"
        custom_footprints = repo / "Custom" / "Footprints"
        custom_symbols.mkdir(parents=True, exist_ok=True)
        custom_footprints.mkdir(parents=True, exist_ok=True)
        # Real files on disk, so migration_reason() finds (or does not find) something to
        # migrate exactly as it would in the real repo (D-13); listing-only, so an empty
        # .kicad_sym stub is enough
        for stem in symbols:
            (custom_symbols / f"{stem}.kicad_sym").write_text(
                "(kicad_symbol_lib)\n", encoding="utf-8"
            )
        for stem in pretty_dirs:
            (custom_footprints / f"{stem}.pretty").mkdir(parents=True, exist_ok=True)
        for name in bak_files:
            (custom_symbols / name).write_text("", encoding="utf-8")

        queue = list(results)

        def fake_scan(root, progress=None, kicad_fp_dir=None, *, skip=None, checking=None):
            item = queue.pop(0) if len(queue) > 1 else queue[0]
            return item() if callable(item) else item

        # The real sync runs, but only against a synthetic KiCad tree and backup folder in tmp_path
        config_base = tmp_path / "kicad_cfg"
        config_base.mkdir(exist_ok=True)

        def fake_sync(repo_root, **kwargs):
            kwargs.setdefault("running", lambda: [])
            return library_scanner.sync_kicad_path_vars(
                repo_root, **kwargs, config_base=config_base, backup_root=tmp_path / "backups",
            )

        def fake_chooser(repo_root, dest_tables, **kwargs):
            kwargs.setdefault("running", lambda: [])
            return kicad_setup.sync_kicad_chooser(
                repo_root, dest_tables, **kwargs,
                config_base=config_base, backup_root=tmp_path / "backups",
            )

        monkeypatch.setattr(main_window, "REPO_ROOT", repo)
        # D-26: the checkout check must never read the owner's real %APPDATA% KiCad config
        monkeypatch.setattr(main_window, "CHECKOUT_CONFIG_BASE", config_base)
        monkeypatch.setattr(main_window, "load_kicad_fp_dir", lambda: fp_dir)
        monkeypatch.setattr(main_window, "scan_all", fake_scan)
        monkeypatch.setattr(main_window, "sync_kicad_path_vars", fake_sync)
        monkeypatch.setattr(main_window, "sync_kicad_chooser", fake_chooser)
        monkeypatch.setattr(main_window, "MigrationDialog", FakeMigrationDialog)
        make.repo = repo
        make.config_base = config_base
        w = main_window.MainWindow()
        qtbot.addWidget(w)
        if wait:
            qtbot.waitUntil(lambda: w._worker is None, timeout=5000)
        return w

    make.repo = None
    make.config_base = None

    # Patched at fixture level so no test can block on a real modal dialog
    def fake_question(window, *args):
        make.questions.append((window, *args))
        return make.answer

    monkeypatch.setattr(main_window.MainWindow, "_question", fake_question)
    make.answer = QMessageBox.StandardButton.Yes
    make.questions = []

    make.running = []

    def fake_running():
        return list(make.running)

    def fake_ask_kicad_open(self, changes, names):
        return ConfirmAnswer.DECLINE

    monkeypatch.setattr(main_window, "kicad_running", fake_running)
    monkeypatch.setattr(main_window.MainWindow, "_ask_kicad_open", fake_ask_kicad_open)
    return make


def settle(qtbot, w):
    """Wait until the scan and the off-thread KiCad check / path-variable question are done."""
    qtbot.waitUntil(lambda: w._worker is None and not w._path_var_busy, timeout=5000)


def _managed_table(tag, entries):
    lines = [f"({tag}", "  (version 7)"]
    for name, rel in entries:
        lines.append(
            f'  (lib (name "{name}")(type "KiCad")'
            f'(uri "${{KICAD_LIB_GITHUB}}/{rel}")(options "")(descr ""))'
        )
    lines.append(")")
    return ("\n".join(lines) + "\n").encode("utf-8")


def _v1_result():
    sym = SymbolLibrary(
        nickname="IC_LDO_TI", rel_path="Custom/Symbols/IC_LDO_TI.kicad_sym",
        source="Custom", selected=True,
    )
    fp = FootprintLibrary(
        nickname="IC_LDO_TI", rel_path="Custom/Footprints/IC_LDO_TI.pretty",
        source="Custom", selected=True,
    )
    return ScanResult(symbol_libs=[sym], footprint_libs=[fp])


def _atomic_result():
    sym1 = SymbolLibrary(
        nickname="Atomic_Connector", rel_path="Custom/Symbols/Atomic_Connector.kicad_sym",
        source="Custom",
    )
    sym2 = SymbolLibrary(
        nickname="Atomic_LED", rel_path="Custom/Symbols/Atomic_LED.kicad_sym",
        source="Custom",
    )
    fp_lib = FootprintLibrary(
        nickname="Atomic_Footprints", rel_path="Custom/Footprints/Atomic_Footprints.pretty",
        source="Custom",
    )
    return ScanResult(symbol_libs=[sym1, sym2], footprint_libs=[fp_lib])


# -- Task 1: migrate, rescan, Generate: the new Atomic_ libraries reach the tables -----------
# (D-13, D-24, P-01)


def test_generate_after_migration_keeps_atomic_libraries(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sym-lib-table").write_bytes(
        _managed_table("sym_lib_table", [("IC_LDO_TI", "Custom/Symbols/IC_LDO_TI.kicad_sym")])
    )
    (repo / "fp-lib-table").write_bytes(
        _managed_table("fp_lib_table", [("IC_LDO_TI", "Custom/Footprints/IC_LDO_TI.pretty")])
    )

    w = make_window([_v1_result(), _atomic_result()], repo=repo)

    assert {lib.rel_path for lib in w._scan_result.symbol_libs if lib.selected} == {
        "Custom/Symbols/IC_LDO_TI.kicad_sym",
    }

    w._open_migration()
    assert len(FakeMigrationDialog.instances) == 1
    dialog = FakeMigrationDialog.instances[0]
    assert dialog.opened
    assert dialog.repo_root == repo

    dialog.migrated.emit(object())
    qtbot.waitUntil(lambda: w._worker is None, timeout=5000)

    assert {lib.rel_path for lib in w._scan_result.symbol_libs if lib.selected} == {
        "Custom/Symbols/Atomic_Connector.kicad_sym", "Custom/Symbols/Atomic_LED.kicad_sym",
    }
    assert {lib.rel_path for lib in w._scan_result.footprint_libs if lib.selected} == {
        "Custom/Footprints/Atomic_Footprints.pretty",
    }
    log_text = w._log._text.toPlainText()
    assert "Selected 3 Atomic_ libraries for Generate Tables" in log_text

    dialog.generate_requested.emit()
    settle(qtbot, w)

    sym_table = (repo / "sym-lib-table").read_text(encoding="utf-8")
    fp_table = (repo / "fp-lib-table").read_text(encoding="utf-8")
    assert '(lib (name "Atomic_Connector")' in sym_table
    assert '(lib (name "Atomic_LED")' in sym_table
    assert "IC_LDO_TI" not in sym_table
    assert '(lib (name "Atomic_Footprints")' in fp_table
    assert "IC_LDO_TI" not in fp_table

    log_text = w._log._text.toPlainText()
    assert "removed stale entry 'IC_LDO_TI'" in log_text
    assert (
        "The old library names were removed from the tables; KiCad projects that used "
        "them need the relink steps in MIGRATION-ATOMIC.md"
    ) in log_text


def test_generate_requested_during_rescan_waits(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sym-lib-table").write_bytes(
        _managed_table("sym_lib_table", [("IC_LDO_TI", "Custom/Symbols/IC_LDO_TI.kicad_sym")])
    )
    (repo / "fp-lib-table").write_bytes(
        _managed_table("fp_lib_table", [("IC_LDO_TI", "Custom/Footprints/IC_LDO_TI.pretty")])
    )

    gate = threading.Event()

    def atomic_result_gated():
        gate.wait(5)
        return _atomic_result()

    w = make_window([_v1_result(), atomic_result_gated], repo=repo)

    w._open_migration()
    dialog = FakeMigrationDialog.instances[0]

    dialog.migrated.emit(object())
    qtbot.waitUntil(lambda: w._worker is not None, timeout=5000)

    dialog.generate_requested.emit()
    log_text = w._log._text.toPlainText()
    assert "Generate Tables runs when the rescan finishes" in log_text
    # Not written yet: the rescan (and the selection it carries) has not finished
    assert '(lib (name "Atomic_Connector")' not in (
        repo / "sym-lib-table"
    ).read_text(encoding="utf-8")

    gate.set()
    settle(qtbot, w)

    sym_table = (repo / "sym-lib-table").read_text(encoding="utf-8")
    assert '(lib (name "Atomic_Connector")' in sym_table
    # Generate ran exactly once after the scan finished (one "Generating tables" line)
    log_text = w._log._text.toPlainText()
    assert log_text.count("Generating tables (") == 1


# -- Task 2: enable rule, exclusion with the importer, chooser hand-off, closing -------------
# (D-13, D-17)


def test_migrate_enabled_only_with_v1_libraries(qtbot, make_window, tmp_path):
    w1 = make_window([ScanResult()], repo=tmp_path / "repo1", symbols=("IC_LDO_TI",))
    assert w1._act_migrate.isEnabled()

    w2 = make_window(
        [ScanResult()], repo=tmp_path / "repo2",
        symbols=("Atomic_Connector",), pretty_dirs=("Atomic_Footprints",),
    )
    assert not w2._act_migrate.isEnabled()
    assert w2._act_migrate.toolTip() == main_window._NOTHING_TO_MIGRATE
    assert w2._act_migrate.statusTip() == main_window._NOTHING_TO_MIGRATE

    w3 = make_window(
        [ScanResult()], repo=tmp_path / "repo3",
        symbols=("Atomic_Connector",), pretty_dirs=("Atomic_Footprints",),
        bak_files=("Old.bak",),
    )
    assert w3._act_migrate.isEnabled()

    w3._set_scan_running(True)
    assert not w3._act_migrate.isEnabled()
    w3._set_scan_running(False)
    assert w3._act_migrate.isEnabled()


def test_import_and_migration_exclude_each_other(qtbot, make_window):
    w = make_window([ScanResult()])

    w._open_migration()
    assert len(FakeMigrationDialog.instances) == 1
    dialog = FakeMigrationDialog.instances[0]

    w._open_import()
    assert w._import_dialog is None
    assert "Close the migration window before importing." in w._log._text.toPlainText()

    dialog.reject()
    qtbot.waitUntil(lambda: w._migration_dialog is None, timeout=5000)

    w._import_dialog = object()  # simulate the import dialog being open
    try:
        w._open_migration()
        assert len(FakeMigrationDialog.instances) == 1  # no second dialog was created
        assert "Close the import window before migrating." in w._log._text.toPlainText()
    finally:
        w._import_dialog = None


def test_chooser_button_runs_the_menu_action(qtbot, make_window, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sym-lib-table").write_bytes(_managed_table("sym_lib_table", []))
    (repo / "fp-lib-table").write_bytes(_managed_table("fp_lib_table", []))
    w = make_window([ScanResult()], repo=repo)

    w._open_migration()
    dialog = FakeMigrationDialog.instances[0]

    dialog.setup_chooser_requested.emit()
    assert w._chooser_busy
    qtbot.waitUntil(lambda: not w._chooser_busy, timeout=5000)


def test_close_blocked_while_migration_runs(qtbot, make_window):
    w = make_window([ScanResult()])
    w._open_migration()
    dialog = FakeMigrationDialog.instances[0]
    dialog._running = True

    event = QCloseEvent()
    w.closeEvent(event)
    assert not event.isAccepted()
    assert w._migration_dialog is dialog

    dialog._running = False
    event2 = QCloseEvent()
    w.closeEvent(event2)
    assert event2.isAccepted()
    assert w._migration_dialog is None
