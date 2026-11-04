import threading
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QFileDialog, QMessageBox,
)
from PySide6.QtCore import QThread, QTimer, Signal, Qt
from PySide6.QtGui import QAction, QKeySequence, QCloseEvent

from . import scan_cache
from .importer.layout import RepoLayout
from .kicad_process import kicad_running
from .library_scanner import (
    ConfirmAnswer, LibraryRescan, find_kicad_footprint_dir, rescan_library, scan_all,
    sync_kicad_path_vars,
)
from .table_generator import (
    add_library_entries, write_tables, restore_backup_pair, table_info, TableInfo,
)
from .models import Issue, ScanResult, Severity
from .settings import (
    load_kicad_fp_dir, save_kicad_fp_dir,
    load_dest_history, add_dest_to_history,
    load_window_geometry, save_window_geometry, scan_cache_file,
)
from .widgets.library_table import LibraryTableWidget
from .widgets.log_panel import LogPanel
from .widgets.scan_progress import ScanProgressDialog
from .widgets.atomic_check_dialog import AtomicCheckDialog
from .widgets.backup_dialog import BackupDialog
from .widgets.help_dialog import HelpDialog
from .widgets.import_dialog import ImportCore, ImportDialog, TaskWorker, centre_window
from .widgets.theme import PRIMARY_BUTTON_QSS

APP_TITLE = "KiCad External Lib Manager"
REPO_ROOT = Path(__file__).parent.parent.resolve()

# Test seams (monkeypatched like REPO_ROOT): None means the real import core and backup folder
IMPORT_CORE: ImportCore | None = None
IMPORT_BACKUP_ROOT: Path | None = None
ATOMIC_BACKUP_ROOT: Path | None = None

# Shown when the Destination box is blank: Path("") would be the working directory (REV-02)
_NO_DEST_TEXT = "No destination folder set; library tables not changed"


def _selected_count(result: ScanResult) -> int:
    return (
        sum(1 for lib in result.symbol_libs if lib.selected)
        + sum(1 for lib in result.footprint_libs if lib.selected)
    )


@dataclass
class _PostInstall:
    """What the next scan must select once an install has finished (POST-01)."""

    library: str
    symbol: str
    sym_rel_path: str
    new_symbol_lib: bool
    footprint_library: str | None
    fp_rel_path: str | None
    new_footprint_lib: bool
    scan_started: bool = False

    @property
    def new_library(self) -> bool:
        return self.new_symbol_lib or self.new_footprint_lib


class ScanWorker(QThread):
    progress = Signal(str, int)  # message, percentage
    finished = Signal(object)    # ScanResult
    error = Signal(str)
    note = Signal(object)        # Issue about the saved scan
    checking = Signal(object)    # source whose 3D model paths are checked now, or None

    def __init__(self, repo_root: Path, kicad_fp_dir: Path | None = None, *,
                 cache_file: Path | None = None, reuse_cache: bool = False):
        super().__init__()
        self._repo_root = repo_root
        self._kicad_fp_dir = kicad_fp_dir
        self._cache_file = cache_file
        self._reuse_cache = reuse_cache
        # Sources whose 3D model path check the user asked to stop; written by the GUI
        # thread, read by this thread once per file
        self._skip_lock = threading.Lock()
        self._skip_sources: set[str] = set()

    def request_skip(self, source: str):
        """GUI thread: the scan stops that source's 3D model path check."""
        with self._skip_lock:
            self._skip_sources.add(source)

    def _skip_requested(self, source: str) -> bool:
        with self._skip_lock:
            return source in self._skip_sources

    def run(self):
        try:
            def on_progress(msg: str, current: int, total: int):
                pct = int(current / max(total, 1) * 100)
                self.progress.emit(msg, pct)

            fingerprint = None
            if self._cache_file is not None:
                # Cache problems never stop the scan: this is the thread boundary (O-04)
                if self._reuse_cache:
                    self.progress.emit("Checking for library changes...", 0)
                    try:
                        check = scan_cache.load_fresh(
                            self._cache_file, self._repo_root, self._kicad_fp_dir
                        )
                    except Exception:
                        check = scan_cache.CacheCheck(None, Issue(
                            Severity.INFO, "cache.unreadable",
                            "The saved scan could not be read; scanning the whole repository.",
                        ))
                    self.note.emit(check.note)
                    if check.result is not None:
                        self.finished.emit(check.result)
                        return
                    fingerprint = check.fingerprint
                # Taken before scan_all reads any file, so an edit during the scan shows as stale
                if fingerprint is None:
                    try:
                        fingerprint = scan_cache.fingerprint(self._repo_root, self._kicad_fp_dir)
                    except Exception:
                        fingerprint = None

            result = scan_all(self._repo_root, progress=on_progress,
                              kicad_fp_dir=self._kicad_fp_dir,
                              skip=self._skip_requested, checking=self.checking.emit)

            if self._cache_file is not None:
                # Before finished: the GUI has not yet touched the selected flags
                try:
                    failure = scan_cache.save(
                        self._cache_file, self._repo_root, self._kicad_fp_dir, fingerprint, result
                    )
                except Exception as e:
                    failure = Issue(
                        Severity.WARNING, "cache.save_failed",
                        f"Could not save this scan for the next start: {e}",
                    )
                if failure is not None:
                    self.note.emit(failure)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class LibraryRescanWorker(QThread):
    """Rescan one library off the GUI thread and refresh its part of the saved scan (O-07 to O-09)."""
    finished = Signal(object)  # LibraryRescan, or None when only a full scan is right
    note = Signal(object)      # Issue to log
    error = Signal(str)

    def __init__(self, repo_root: Path, kicad_fp_dir: Path | None, previous: ScanResult,
                 kind: str, rel_path: str, *, cache_file: Path | None = None):
        super().__init__()
        self._repo_root = repo_root
        self._kicad_fp_dir = kicad_fp_dir
        self._previous = previous
        self._kind = kind
        self._rel_path = rel_path
        self._cache_file = cache_file

    def run(self):
        try:
            entries = None
            if self._cache_file is not None:
                # Stats first, before the library is read, so an edit during the rescan shows as stale
                try:
                    entries = scan_cache.library_entries(self._repo_root, self._kind, self._rel_path)
                except Exception:
                    entries = None
            outcome = rescan_library(
                self._repo_root, self._previous, self._kind, self._rel_path, self._kicad_fp_dir
            )
            if isinstance(outcome, Issue):
                self.note.emit(outcome)
                self.finished.emit(None)
                return
            if self._cache_file is not None:
                try:
                    failure = scan_cache.update_library(
                        self._cache_file, self._repo_root, self._kicad_fp_dir, outcome.result,
                        self._kind, self._rel_path, entries,
                    )
                except Exception:
                    failure = Issue(
                        Severity.INFO, "cache.not_updated",
                        "The saved scan was not updated, so the next start scans the whole repository.",
                    )
                if failure is not None:
                    self.note.emit(failure)
            self.finished.emit(outcome)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1100, 750)

        # Restore saved window geometry
        geometry = load_window_geometry()
        if geometry:
            self.restoreGeometry(geometry)

        self._scan_result: ScanResult | None = None
        self._worker: QThread | None = None
        # (kind, nickname) of the library rescan in flight, for its one log line
        self._rescan_label: tuple[str, str] | None = None
        # Armed once here; _finish_scan consumes it after the first scan ends,
        # however that scan ended. Only that scan pre-selects from the tables.
        self._startup_pending = True
        self._kicad_fp_dir: Path | None = None
        self._progress: ScanProgressDialog | None = None
        self._import_dialog: ImportDialog | None = None
        # The one User Guide window: parentless, so no window-modal dialog of this app blocks it (G-12-22)
        self._guide: HelpDialog | None = None
        self._atomic_dialog: AtomicCheckDialog | None = None
        self._pending_post_install: _PostInstall | None = None
        # The KiCad-open check runs on a worker before the path-variable confirm (REV-05):
        # one check at a time, and a close during it waits for it instead of blocking
        self._path_var_busy = False
        self._path_var_check: TaskWorker | None = None
        self._path_var_workers: list[TaskWorker] = []
        self._close_after_check = False
        self._close_after_dialog = False  # the import dialog is finishing: close this window after it
        self.setAcceptDrops(True)
        self._build_menu()
        self._build_ui()
        self.statusBar()  # Enable status bar for menu hints

        # Detect KiCad installation, then start scan
        self._detect_kicad()
        self._log_existing_tables(self._dest_path())
        # Reuse the saved scan when no library file changed (O-01)
        self._start_scan(reuse_cache=True)

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        # Kept as attributes: _set_scan_running toggles them while a scan runs
        self._act_import = QAction("&Import Part...", self)
        self._act_import.setShortcut(QKeySequence("Ctrl+I"))
        self._act_import.setToolTip("Import a vendor package (.zip or folder) into Custom/")
        self._act_import.setStatusTip("Import a vendor package (.zip or folder) into Custom/")
        self._act_import.triggered.connect(lambda: self._open_import())
        file_menu.addAction(self._act_import)
        file_menu.addSeparator()

        self._act_generate = QAction("&Generate Tables", self)
        self._act_generate.setShortcut(QKeySequence("Ctrl+G"))
        self._act_generate.setToolTip("Generate sym-lib-table and fp-lib-table from selected libraries")
        self._act_generate.setStatusTip("Generate sym-lib-table and fp-lib-table from selected libraries")
        self._act_generate.triggered.connect(self._on_generate)
        file_menu.addAction(self._act_generate)

        self._act_restore = QAction("&Restore Backup...", self)
        self._act_restore.setShortcut(QKeySequence("Ctrl+R"))
        self._act_restore.setToolTip("Restore a previous sym-lib-table / fp-lib-table backup pair")
        self._act_restore.setStatusTip("Restore a previous sym-lib-table / fp-lib-table backup pair")
        self._act_restore.triggered.connect(self._on_restore_backup)
        file_menu.addAction(self._act_restore)

        self._act_rescan = QAction("Re&scan Libraries", self)
        self._act_rescan.setShortcut(QKeySequence("Ctrl+Shift+R"))
        self._act_rescan.setToolTip("Rescan the repository for symbol and footprint libraries")
        self._act_rescan.setStatusTip("Rescan the repository for symbol and footprint libraries")
        self._act_rescan.triggered.connect(self._on_rescan)
        file_menu.addAction(self._act_rescan)

        self._act_check_atomic = QAction("Check &Atomic Parts...", self)
        self._act_check_atomic.setShortcut(QKeySequence("Ctrl+Shift+A"))
        self._act_check_atomic.setToolTip(
            "List the atomic rule problems found by the last scan and fix the safe ones"
        )
        self._act_check_atomic.setStatusTip(
            "List the atomic rule problems found by the last scan and fix the safe ones"
        )
        self._act_check_atomic.triggered.connect(lambda: self._open_atomic_check())
        file_menu.addAction(self._act_check_atomic)

        self._act_set_kicad_path = QAction("Set KiCad &Footprint Path...", self)
        self._act_set_kicad_path.setShortcut(QKeySequence("Ctrl+K"))
        self._act_set_kicad_path.setToolTip("Set KiCad default footprint library folder for cross-referencing")
        self._act_set_kicad_path.setStatusTip("Set KiCad default footprint library folder for cross-referencing")
        self._act_set_kicad_path.triggered.connect(self._on_set_kicad_path)
        file_menu.addAction(self._act_set_kicad_path)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.setToolTip("Close the application")
        exit_action.setStatusTip("Close the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Ensure menu is wide enough and shows tooltips
        file_menu.setMinimumWidth(350)
        file_menu.setToolTipsVisible(True)

        help_menu = menubar.addMenu("&Help")

        help_action = QAction("&User Guide", self)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.setToolTip(f"How to use the {APP_TITLE}")
        help_action.setStatusTip(f"How to use the {APP_TITLE}")
        help_action.triggered.connect(self._on_help)
        help_menu.addAction(help_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.setToolTip(f"About {APP_TITLE}")
        about_action.setStatusTip(f"About {APP_TITLE}")
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Toolbar row
        toolbar = QHBoxLayout()

        self._import_btn = QPushButton("Import Part...")
        self._import_btn.setToolTip("Import a vendor package (Ctrl+I)")
        self._import_btn.clicked.connect(lambda: self._open_import())
        toolbar.addWidget(self._import_btn)
        toolbar.addSpacing(16)

        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.clicked.connect(self._on_select_all)
        toolbar.addWidget(self._select_all_btn)

        self._deselect_all_btn = QPushButton("Deselect All")
        self._deselect_all_btn.clicked.connect(self._on_deselect_all)
        toolbar.addWidget(self._deselect_all_btn)

        toolbar.addStretch()

        toolbar.addWidget(QLabel("Destination:"))
        self._dest_combo = QComboBox()
        self._dest_combo.setEditable(True)
        self._dest_combo.setMinimumWidth(300)
        self._populate_dest_combo()
        # Not currentTextChanged: that fires on every keystroke of a typed path
        self._dest_combo.textActivated.connect(self._on_dest_changed)
        self._dest_combo.lineEdit().editingFinished.connect(self._on_dest_changed)
        toolbar.addWidget(self._dest_combo)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_dest)
        toolbar.addWidget(browse_btn)

        self._rescan_btn = QPushButton("Rescan")
        self._rescan_btn.setToolTip("Rescan repository for libraries (Ctrl+Shift+R)")
        self._rescan_btn.clicked.connect(self._on_rescan)
        toolbar.addWidget(self._rescan_btn)

        self._generate_btn = QPushButton("Generate Tables")
        self._generate_btn.setStyleSheet(PRIMARY_BUTTON_QSS)
        self._generate_btn.clicked.connect(self._on_generate)
        toolbar.addWidget(self._generate_btn)

        layout.addLayout(toolbar)

        # Library tree
        self._tree = LibraryTableWidget()
        self._tree.symbol_activated.connect(self._on_symbol_activated)
        self._tree.library_rescan_requested.connect(self._on_library_rescan_requested)
        layout.addWidget(self._tree, stretch=1)

        # Log panel
        self._log = LogPanel()
        layout.addWidget(self._log)

    def _populate_dest_combo(self):
        self._dest_combo.blockSignals(True)
        self._dest_combo.clear()
        history = load_dest_history()
        if history:
            self._dest_combo.addItems(history)
        else:
            self._dest_combo.addItem(str(REPO_ROOT))
        self._dest_combo.setCurrentIndex(0)
        self._dest_combo.blockSignals(False)

    def _detect_kicad(self):
        # Try saved path first
        saved = load_kicad_fp_dir()
        if saved:
            self._kicad_fp_dir = saved
            self._log.log(
                f"KiCad footprints (saved): {self._kicad_fp_dir}", "success"
            )
            return

        # Try auto-detection
        self._kicad_fp_dir = find_kicad_footprint_dir()
        if self._kicad_fp_dir:
            save_kicad_fp_dir(self._kicad_fp_dir)
            self._log.log(
                f"KiCad footprints detected: {self._kicad_fp_dir}",
                "success",
            )
        else:
            self._log.log(
                "KiCad installation not found automatically.", "warning"
            )
            folder = QFileDialog.getExistingDirectory(
                self,
                "Select KiCad footprints folder "
                "(e.g. C:/Program Files/KiCad/9.0/share/kicad/footprints)",
                "C:/Program Files",
            )
            if folder:
                self._kicad_fp_dir = Path(folder)
                save_kicad_fp_dir(self._kicad_fp_dir)
                self._log.log(
                    f"KiCad footprints set to: {self._kicad_fp_dir}",
                    "success",
                )
            else:
                self._log.log(
                    "No KiCad footprint path selected. "
                    "Default library cross-references will show as warnings.",
                    "warning",
                )

    def _dest_path(self) -> Path | None:
        """The Destination box as a folder; None when it is blank (Path("") is the working directory)."""
        text = self._dest_combo.currentText().strip()
        return Path(text) if text else None

    def _log_existing_tables(self, dest: Path | None):
        """Log which table files exist at the destination; never touches selection."""
        if dest is None or not dest.is_dir():
            return
        for name in ("sym-lib-table", "fp-lib-table"):
            info = table_info(dest / name)
            if info is None:
                continue
            if isinstance(info, Issue):
                self._log.log_issue(info)
                continue
            self._log.log(
                f"Existing {name} found at {dest} ({info.entry_count} entries, "
                f"{len(info.managed)} managed) - external entries will be "
                "preserved on generate",
                "info",
            )

    def _set_scan_running(self, running: bool):
        """Disable the controls that must not act while a scan is in flight."""
        for control in (
            self._rescan_btn, self._act_rescan, self._act_set_kicad_path,
            self._act_generate, self._generate_btn, self._act_import,
            self._import_btn, self._select_all_btn, self._deselect_all_btn,
            self._act_check_atomic,
        ):
            control.setEnabled(not running)
        self._tree.set_library_rescan_enabled(not running)

    def _start_scan(self, show_progress: bool = True, reuse_cache: bool = False):
        """Start a scan; every scan request must go through here.

        show_progress=False runs the scan quietly (no Loading Libraries window); only the
        post-install rescan uses it, so the trees update behind the import dialog.
        reuse_cache=True (app start only) shows the saved scan when no library file
        changed; every other scan is a full scan, and every full scan saves its result.

        Refuses while a worker exists, because a disabled control does not stop a
        programmatic caller (the post-import rescan included). The guard keys on
        the worker reference, not on the thread's running state: the custom
        finished signal fires while run() has not returned yet.
        """
        if self._worker is not None:
            self._log.log("A scan is already running; request ignored.", "info")
            return

        self._set_scan_running(True)
        if show_progress:
            self._progress = ScanProgressDialog(parent=self)
            self._progress.skip_requested.connect(self._on_skip_requested)
            self._progress.set_progress("Scanning libraries...", 0)
            self._progress.show()
        else:
            self._progress = None
        if self._pending_post_install is not None:
            self._pending_post_install.scan_started = True

        self._log.log(
            "Checking for library changes since the saved scan..." if reuse_cache
            else "Scanning repository...",
            "info",
        )

        self._worker = ScanWorker(
            REPO_ROOT, self._kicad_fp_dir,
            cache_file=scan_cache_file(REPO_ROOT), reuse_cache=reuse_cache,
        )
        self._worker.progress.connect(self._on_scan_progress)
        self._worker.checking.connect(self._on_scan_checking)
        self._worker.note.connect(self._log.log_issue)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.error.connect(self._on_scan_error)
        self._worker.start()

    def _on_scan_progress(self, message: str, percentage: int):
        if self._progress is not None:
            self._progress.set_progress(message, min(percentage, 99))

    def _on_scan_checking(self, source: str | None):
        if self._progress is not None:
            self._progress.set_skippable(source)

    def _on_skip_requested(self, source: str):
        """Forward the Skip click to the running scan.

        Writes no log line: the click can arrive after the scan asked about that source's last
        file, so the one skip line comes from the finished scan's own result.
        """
        if isinstance(self._worker, ScanWorker):
            self._worker.request_skip(source)

    def _on_library_rescan_requested(self, kind: str, rel_path: str):
        """Rescan one library from the right-click menu; same busy guard as _start_scan (O-09)."""
        if self._worker is not None:
            self._log.log("A scan is already running; request ignored.", "info")
            return
        if self._scan_result is None:
            self._log.log("No scan result yet; rescan first.", "info")
            return
        libs = self._scan_result.symbol_libs if kind == "symbol" else self._scan_result.footprint_libs
        nickname = next((lib.nickname for lib in libs if lib.rel_path == rel_path), rel_path)
        self._set_scan_running(True)
        self._progress = None
        self._rescan_label = (kind, nickname)
        self.statusBar().showMessage(f"Rescanning {nickname}...")

        self._worker = LibraryRescanWorker(
            REPO_ROOT, self._kicad_fp_dir, self._scan_result, kind, rel_path,
            cache_file=scan_cache_file(REPO_ROOT),
        )
        self._worker.note.connect(self._log.log_issue)
        self._worker.finished.connect(self._on_library_rescanned)
        self._worker.error.connect(self._on_scan_error)
        self._worker.start()

    def _on_library_rescanned(self, outcome: LibraryRescan | None):
        try:
            self.statusBar().clearMessage()
            if outcome is not None:
                # The live check boxes win over the worker's snapshot of them (O-08)
                self._copy_selection(self._scan_result, outcome.result)
                self._log_issues(self._trim_collided_selection(outcome.result))
                self._scan_result = outcome.result
                self._tree.populate(outcome.result)
                self._log_library_rescanned(outcome)
        finally:
            self._finish_scan()
            if outcome is None and self._worker is None:
                # Only a full scan is right here (O-10); the reason was logged already
                self._start_scan()

    def _log_library_rescanned(self, outcome: LibraryRescan):
        kind, nickname = self._rescan_label or ("symbol", "library")
        text = f"Rescanned {kind} library {nickname}"
        count = len(outcome.rechecked)
        if count:
            text += (
                f" (and re-checked {count} linked atomic symbol "
                f"{'library' if count == 1 else 'libraries'})"
            )
        warnings = sum(
            1 for issue in outcome.issues if issue.severity in (Severity.WARNING, Severity.ERROR)
        )
        if warnings == 0:
            self._log.log(f"{text}: no warnings", "success")
        else:
            self._log.log(f"{text}: {warnings} warning{'' if warnings == 1 else 's'}", "warning")

    def _finish_scan(self):
        """Release the worker and re-enable the controls; always runs after a scan."""
        self._startup_pending = False
        if self._worker is not None:
            self._worker.wait()
            self._worker = None
        self._set_scan_running(False)
        pending = self._pending_post_install
        if pending is not None and not pending.scan_started:
            # An install finished while another scan ran; scan again now, quietly
            self._start_scan(show_progress=False)

    def _on_scan_finished(self, result: ScanResult):
        try:
            if self._progress is not None:
                self._progress.finish()
            startup = self._startup_pending
            previous = self._scan_result
            self._scan_result = result

            sym_count = len(result.symbol_libs)
            fp_count = len(result.footprint_libs)
            self._log.log(
                f"Found {sym_count} symbol libraries, {fp_count} footprint libraries.",
                "success",
            )

            if startup:
                # Only the first scan reads the tables (D-05)
                self._apply_existing_selection(result)
            else:
                self._reapply_selection(previous, result)
            self._log_issues(self._trim_collided_selection(result))
            if startup:
                # Peers are settled, so linked footprints can be added safely
                self._select_linked_footprints(result)
            pending = self._pending_post_install
            if pending is not None and pending.scan_started:
                self._apply_post_install_selection(result, pending)

            self._tree.populate(result)
            if pending is not None and pending.scan_started:
                self._finish_post_install(result)

            self._log_issues(result.issues)

            if not any(
                i.severity in (Severity.WARNING, Severity.ERROR) for i in result.issues
            ):
                self._log.log(
                    "No warnings in the checks that ran." if result.skipped_sources
                    else "No warnings.",
                    "success",
                )
        finally:
            self._finish_scan()

    @staticmethod
    def _copy_selection(previous: ScanResult | None, result: ScanResult) -> set[str]:
        """Copy the selected flags of previous onto result by rel_path; return the rel_paths that vanished.

        New libraries start unchecked. Without a previous result nothing is kept.
        """
        keep_sym: set[str] = set()
        keep_fp: set[str] = set()
        if previous is not None:
            keep_sym = {lib.rel_path for lib in previous.symbol_libs if lib.selected}
            keep_fp = {lib.rel_path for lib in previous.footprint_libs if lib.selected}

        for lib in result.symbol_libs:
            lib.selected = lib.rel_path in keep_sym
        for lib in result.footprint_libs:
            lib.selected = lib.rel_path in keep_fp

        return (
            (keep_sym - {lib.rel_path for lib in result.symbol_libs})
            | (keep_fp - {lib.rel_path for lib in result.footprint_libs})
        )

    def _reapply_selection(self, previous: ScanResult | None, result: ScanResult):
        """Carry the user's selection over to a fresh scan, keyed by rel_path.

        New libraries start unchecked and vanished ones drop out. Without a
        previous result (rescan after a failed startup scan) nothing is kept.
        """
        missing = self._copy_selection(previous, result)
        kept = _selected_count(result)
        self._log.log(f"Kept {kept} selections after rescan", "info")
        if missing:
            self._log.log(
                f"Dropped {len(missing)} selections for libraries no longer found: "
                f"{', '.join(sorted(missing))}",
                "info",
            )

    def _trim_collided_selection(self, result: ScanResult) -> list[Issue]:
        """Keep at most one selected library per nickname (D-01).

        The selected peer whose rel_path sorts first stays, the others are
        unchecked. Never changes a nickname and never selects anything.
        """
        issues: list[Issue] = []
        for kind, libs in (
            ("Symbol", result.symbol_libs), ("Footprint", result.footprint_libs),
        ):
            by_path = {lib.rel_path: lib for lib in libs}
            ordered = sorted(libs, key=lambda item: item.rel_path)
            was_selected: dict[str, list[str]] = {}
            for lib in ordered:
                if lib.selected and lib.collision_peers:
                    was_selected.setdefault(lib.nickname, []).append(lib.rel_path)
            for lib in ordered:
                if lib.selected and any(
                    by_path[peer].selected and peer < lib.rel_path
                    for peer in lib.collision_peers if peer in by_path
                ):
                    lib.selected = False
            for nickname, paths in sorted(was_selected.items()):
                if len(paths) > 1:
                    issues.append(Issue(
                        Severity.WARNING,
                        "selection.collision_trimmed",
                        f"[{nickname}] {kind} libraries {', '.join(paths)} were all "
                        f"selected; kept {paths[0]} and unchecked the rest "
                        "(only one library per nickname can be selected)",
                    ))
        return issues

    def _select_linked_footprints(self, result: ScanResult) -> int:
        """Select the footprint libraries referenced by selected symbols, per source.

        Startup only, and additive: a footprint the tables selected stays selected.
        """
        fp_by_path = {lib.rel_path: lib for lib in result.footprint_libs}
        added = 0
        for source in sorted({lib.source for lib in result.symbol_libs}):
            needed = {
                ref.library_name
                for sym in result.symbol_libs
                if sym.source == source and sym.selected
                for ref in sym.footprint_refs
            }
            for fp in sorted(result.footprint_libs, key=lambda item: item.rel_path):
                if fp.source != source or fp.selected or fp.nickname not in needed:
                    continue
                if any(
                    fp_by_path[peer].selected
                    for peer in fp.collision_peers if peer in fp_by_path
                ):
                    continue
                fp.selected = True
                added += 1
        if added:
            self._log.log(
                f"Selected {added} footprint libraries linked to the pre-selected symbols",
                "info",
            )
        return added

    def _apply_existing_selection(self, result: ScanResult):
        """Pre-select libraries already in the destination tables; first scan only (D-05)."""
        dest = self._dest_path()
        if dest is None or not dest.is_dir():
            return

        # Collect the repo-relative paths of managed entries (identity is rel_path)
        managed: dict[str, frozenset[str]] = {}
        for name in ("sym-lib-table", "fp-lib-table"):
            info = table_info(dest / name)
            if isinstance(info, Issue):
                self._log.log_issue(info)
            elif isinstance(info, TableInfo):
                managed[name] = info.managed
        sym_paths = managed.get("sym-lib-table", frozenset())
        fp_paths = managed.get("fp-lib-table", frozenset())

        if not sym_paths and not fp_paths:
            return

        selected_sym = 0
        for lib in result.symbol_libs:
            if lib.rel_path in sym_paths:
                lib.selected = True
                selected_sym += 1

        selected_fp = 0
        for lib in result.footprint_libs:
            if lib.rel_path in fp_paths:
                lib.selected = True
                selected_fp += 1

        self._log.log(
            f"Pre-selected {selected_sym} symbol and {selected_fp} footprint "
            f"libraries from existing tables at {dest}",
            "info",
        )

    def _on_scan_error(self, error_msg: str):
        try:
            if self._progress is not None:
                self._progress.finish()
            self._log.log(f"Scan error: {error_msg}", "error")
            if self._startup_pending:
                self._log.log(
                    "Startup scan failed, so nothing was pre-selected from the "
                    "destination tables; a Rescan starts with every library unchecked "
                    "(restart the app to pre-select from the tables).",
                    "info",
                )
            pending = self._pending_post_install
            if pending is not None and pending.scan_started:
                self._finish_post_install(None)
        finally:
            self._finish_scan()

    def _apply_post_install_selection(self, result: ScanResult, pending: _PostInstall):
        """Check the freshly installed library in the new scan result (POST-01, D-16).

        Matches by rel_path only. A selected same-nickname peer elsewhere is unchecked so
        one library per nickname stays selected. A library the scan does not list is skipped.
        """
        for libs, rel_path in (
            (result.symbol_libs, pending.sym_rel_path),
            (result.footprint_libs, pending.fp_rel_path),
        ):
            if rel_path is None:
                continue
            by_path = {lib.rel_path: lib for lib in libs}
            lib = by_path.get(rel_path)
            if lib is None:
                continue
            lib.selected = True
            for peer_path in lib.collision_peers:
                peer = by_path.get(peer_path)
                if peer is not None and peer.selected:
                    peer.selected = False
                    self._log.log(
                        f"Unchecked {peer.rel_path}: {pending.library} was just installed "
                        "and has the same nickname",
                        "info",
                    )

    def _finish_post_install(self, result: ScanResult | None):
        """Last post-install step: reveal the library, then tables or a Generate hint.

        Runs after the selection step, whether the rescan succeeded (result) or failed
        (None): the table entries come from the install plan, not from the scan. Only the
        installed library's own entries are written, never the tree's ungenerated
        selection (D-17), so write_tables is deliberately not used here.
        """
        pending, self._pending_post_install = self._pending_post_install, None
        if pending is None:
            return
        library = pending.library

        # The Result view's rows follow each step (D-16); the dialog may already be closed
        if result is None:
            self._set_import_status("library_list", "Rescan failed - see the log", Severity.ERROR)
        else:
            self._tree.reveal(pending.sym_rel_path, pending.fp_rel_path)
            if any(lib.rel_path == pending.sym_rel_path for lib in result.symbol_libs):
                self._set_import_status("library_list", f"Updated; {library} is selected", Severity.SUCCESS)
            else:
                self._set_import_status(
                    "library_list", f"Updated; {library} was not found in the scan", Severity.WARNING
                )

        dest = self._dest_path()
        if dest is None:
            self._log.log(_NO_DEST_TEXT, "warning")
            self._set_import_status("tables", _NO_DEST_TEXT, Severity.WARNING)
            return
        if not dest.is_dir():
            self._log.log(f"Destination folder does not exist: {dest}", "error")
            if pending.new_library:
                self._set_import_status(
                    "tables", f"Destination folder does not exist: {dest}", Severity.ERROR
                )
            return

        if pending.new_library:
            # The footprint library's entry is offered whenever it is a folder of this repo, new or not,
            # so a shared Atomic_Footprints missing from fp-lib-table is added (WR-05); add_library_entries
            # leaves a table that already lists it unchanged
            issues = add_library_entries(
                dest,
                symbol=(library, pending.sym_rel_path) if pending.new_symbol_lib else None,
                footprint=(
                    (pending.footprint_library, pending.fp_rel_path)
                    if pending.footprint_library and pending.fp_rel_path
                    else None
                ),
                repo_root=REPO_ROOT,
            )
            self._log_issues(issues)
            text, severity = self._tables_outcome(issues)
            self._set_import_status("tables", text, severity)
            # Same rule as Generate: the path variables are offered for change after every
            # table write, never written silently
            self._sync_path_vars()
            return

        # The libraries the tables must list: the symbol library, and the footprint library when
        # it is a folder of this repo (one outside the repo is never in fp-lib-table, D-16).
        # An existing library is never added here (D-04): a stale entry is repointed, a clash is
        # warned about, and a library the tables lack keeps the Generate hint. An unreadable
        # table now shows its read error in the tables row instead of the Generate hint.
        issues = add_library_entries(
            dest,
            symbol=(library, pending.sym_rel_path),
            footprint=(
                (pending.footprint_library, pending.fp_rel_path)
                if pending.footprint_library and pending.fp_rel_path
                else None
            ),
            repo_root=REPO_ROOT,
            add_missing=False,
        )
        not_listed = {issue.text for issue in issues if issue.code == "table.not_listed"}
        missing = [
            name for name, table in (
                (library, "sym-lib-table"), (pending.footprint_library, "fp-lib-table"),
            )
            if f"{table} does not list {name}" in not_listed
        ]
        self._log_issues([issue for issue in issues if issue.code != "table.not_listed"])
        if any(
            issue.severity is Severity.ERROR
            or issue.code in ("table.entry_updated", "table.path_clash", "table.external_clash")
            for issue in issues
        ):
            text, severity = self._tables_outcome(issues)
            self._set_import_status("tables", text, severity)
        if any(issue.code == "table.entry_updated" for issue in issues):
            self._sync_path_vars()
        if missing:
            names = " and ".join(dict.fromkeys(missing))
            two = len(set(missing)) > 1
            hint = (
                f"{names} {'are' if two else 'is'} not in the library tables. "
                f"Press Generate Tables to add {'them' if two else 'it'}."
            )
            self._log_issues([Issue(Severity.WARNING, "import.not_in_tables", hint)])
            self._set_import_status("generate_hint", f"⚠ {hint}", Severity.WARNING)

    def _set_import_status(self, row: str, text: str, severity: Severity):
        """Update a status row of the Result view; nothing happens once the dialog is closed."""
        dialog = self._import_dialog
        if dialog is not None:
            dialog.set_post_install_status(row, text, severity)

    @staticmethod
    def _tables_outcome(issues: list[Issue]) -> tuple[str, Severity]:
        """The Library tables row of the Result view, from the Issues of add_library_entries (D-17).

        Used for a new library and, when a table was repointed or a name clashed, for an
        existing one. A clash makes the row a warning; a repoint makes it a success.
        """
        errors = [issue for issue in issues if issue.severity is Severity.ERROR]
        if errors:
            return errors[0].text, Severity.ERROR
        for issue in issues:
            if issue.code == "table.entries_added":
                return issue.text, Severity.SUCCESS
        warned = any(issue.severity is Severity.WARNING for issue in issues)
        parts = [
            issue.text for issue in issues
            if issue.code in (
                "table.entry_added", "table.entry_updated", "table.already_listed",
                "table.path_clash", "table.external_clash",
            )
        ]
        text = "; ".join(parts) or "Library tables checked"
        if warned:
            return text, Severity.WARNING
        if any(issue.code == "table.entry_updated" for issue in issues):
            return text, Severity.SUCCESS
        return text, Severity.INFO

    def _import_busy(self) -> bool:
        """True while a scan runs or the import dialog is open (D-19)."""
        return self._worker is not None or self._import_dialog is not None

    def _refuse_busy_drag(self, event) -> bool:
        """Ignore a drag or drop while busy and say why; True when refused."""
        if not self._import_busy():
            return False
        event.ignore()
        self.statusBar().showMessage("Import is unavailable while a scan is running.", 3000)
        return True

    def dragEnterEvent(self, event):
        if self._refuse_busy_drag(event):
            return
        # Accept any URL drag so dropEvent can explain a refusal
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._import_busy() or not event.mimeData().hasUrls():
            event.ignore()
        else:
            event.acceptProposedAction()

    def dropEvent(self, event):
        # A scan can start between dragEnterEvent and the drop
        if self._refuse_busy_drag(event):
            return
        urls = event.mimeData().urls()
        if len(urls) != 1:
            self._log.log(
                "Drop ignored: drop one .zip file or one folder at a time.", "warning"
            )
            event.ignore()
            return
        url = urls[0]
        if not url.isLocalFile():
            self._log.log(
                f"Drop ignored: '{url.fileName()}' is not a .zip file or a folder.",
                "warning",
            )
            event.ignore()
            return
        path = Path(url.toLocalFile())
        if path.is_dir() or (path.is_file() and path.suffix.casefold() == ".zip"):
            event.acceptProposedAction()
            self._open_import(path)
            return
        self._log.log(
            f"Drop ignored: '{path.name}' is not a .zip file or a folder.", "warning"
        )
        event.ignore()

    def _open_import(self, path: Path | None = None):
        """Open the Import Part dialog, optionally with a package already chosen."""
        if self._import_busy():
            return
        dialog = ImportDialog(
            REPO_ROOT,
            RepoLayout.for_repo(REPO_ROOT),
            kicad_fp_dir=self._kicad_fp_dir,
            package_path=path,
            core=IMPORT_CORE,
            backup_root=IMPORT_BACKUP_ROOT,
            atomic_backup_root=ATOMIC_BACKUP_ROOT,
            parent=self,
        )
        dialog.installed.connect(self._on_import_installed)
        dialog.issues_logged.connect(self._log_issues)
        dialog.atomic_fixes_applied.connect(self._on_atomic_fixes_applied)
        dialog.finished.connect(self._on_import_dialog_finished)
        dialog.leave_cancelled.connect(self._on_dialog_leave_cancelled)
        self._import_dialog = dialog
        dialog.open()

    def _on_dialog_leave_cancelled(self):
        """Cancel in the dialog's Finishing strip: this window forgets its own pending close too."""
        self._close_after_dialog = False

    def _on_import_dialog_finished(self, _result: int):
        dialog, self._import_dialog = self._import_dialog, None
        if dialog is not None:
            dialog.deleteLater()
        if self._close_after_dialog:
            self._close_after_dialog = False
            QTimer.singleShot(0, self.close)

    def _open_atomic_check(self, focus: tuple[str, str] | None = None):
        """Open Check Atomic Parts on the last scan; it never scans or checks on the GUI thread (D-12)."""
        if self._worker is not None:
            self._log.log("A scan is already running; request ignored.", "info")
            return
        if self._atomic_dialog is not None:
            self._atomic_dialog.raise_()
            self._atomic_dialog.activateWindow()
            return
        if self._scan_result is None:
            self._log.log("No scan result yet; rescan first.", "info")
            return
        dialog = AtomicCheckDialog(
            self._scan_result,
            REPO_ROOT,
            focus=focus,
            backup_root=ATOMIC_BACKUP_ROOT,
            parent=self,
        )
        dialog.applied.connect(self._on_atomic_fixes_applied)
        dialog.issues_logged.connect(self._log_issues)
        dialog.finished.connect(self._on_atomic_dialog_finished)
        self._atomic_dialog = dialog
        dialog.open()

    def _on_symbol_activated(self, rel_path: str, name: str):
        """A marked symbol row was double-clicked in the tree: open the check on that symbol."""
        self._open_atomic_check(focus=(rel_path, name))

    def _on_atomic_fixes_applied(self, issues: list[Issue]):
        """Fixes were written: log them, then rescan so the fixed problems are gone."""
        self._log_issues(issues)
        self._start_scan()

    def _on_atomic_dialog_finished(self, _result: int):
        dialog, self._atomic_dialog = self._atomic_dialog, None
        if dialog is not None:
            dialog.deleteLater()

    def _on_import_installed(self, result, plan):
        """An install finished: rescan quietly and select the installed library."""
        root = plan.layout.repo_root
        # The footprint library is a repo folder only when it is the .pretty the plan writes; one
        # outside the repo (an official KiCad library) is never added to fp-lib-table (D-16)
        in_repo = plan.footprint_library is not None and plan.footprint_library == plan.pretty_path.stem
        self._pending_post_install = _PostInstall(
            library=plan.library,
            symbol=plan.symbol_name,
            sym_rel_path=plan.symbol_lib_path.relative_to(root).as_posix(),
            new_symbol_lib=plan.new_symbol_lib,
            footprint_library=plan.footprint_library if in_repo else None,
            fp_rel_path=plan.pretty_path.relative_to(root).as_posix() if in_repo else None,
            new_footprint_lib=plan.new_footprint_lib and in_repo,
        )
        self.statusBar().showMessage(f"Installed {plan.symbol_name} into {result.library}", 5000)
        self._set_import_status("library_list", "Rescanning...", Severity.INFO)
        if self._pending_post_install.new_library:
            self._set_import_status("tables", "Updating...", Severity.INFO)
        else:
            self._set_import_status("tables", "Not needed: existing libraries", Severity.INFO)
        if self._worker is None:
            self._start_scan(show_progress=False)
        # else: _finish_scan starts the post-install scan when the running one ends

    def _log_issues(self, issues: list[Issue]):
        for issue in issues:
            self._log.log_issue(issue)

    # Intentional exception to the convention that QMessageBox is only used for About:
    # the owner requires an explicit confirmation before KiCad's global settings change
    # (PROJECT.md Safety constraint: no write without a preview first). With KiCad open the
    # same confirmation is a three-button variant (Retry, Change anyway, Not now).
    def _confirm_path_var_changes(self, changes, names=()):
        if names:
            return self._ask_kicad_open(changes, names)
        lines = [
            f"{var}: {old if old else '(not set)'} -> {new}" for var, old, new in changes
        ]
        text = (
            "These KiCad path variables in KiCad's settings file would change:\n\n"
            + "\n".join(lines)
            + "\n\nKiCad loads its libraries from these paths after a restart. Change them?"
        )
        answer = QMessageBox.question(
            self,
            "Change KiCad path variables?",
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def _kicad_open_box(self, changes, names) -> tuple[QMessageBox, dict]:
        """The dialog for a change while KiCad is open, and the answer each button gives."""
        lines = [
            f"{var}: {old if old else '(not set)'} -> {new}" for var, old, new in changes
        ]
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("KiCad is open")
        box.setText(
            f"KiCad is open ({', '.join(names)}). These KiCad path variables in "
            "KiCad's settings file would change:\n\n"
            + "\n".join(lines)
            + "\n\nKiCad may undo them when it exits. Close KiCad, then press Retry."
        )
        retry = box.addButton("Retry", QMessageBox.ButtonRole.AcceptRole)
        anyway = box.addButton("Change anyway", QMessageBox.ButtonRole.DestructiveRole)
        not_now = box.addButton("Not now", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(retry)
        box.setEscapeButton(not_now)
        return box, {
            retry: ConfirmAnswer.RETRY,
            anyway: ConfirmAnswer.WRITE,
            not_now: ConfirmAnswer.DECLINE,
        }

    def _ask_kicad_open(self, changes, names) -> ConfirmAnswer:
        box, answers = self._kicad_open_box(changes, names)
        box.exec()
        return answers.get(box.clickedButton(), ConfirmAnswer.DECLINE)

    def _sync_path_vars(self):
        """Offer the KiCad path variable change: check for a running KiCad first, off the GUI thread."""
        if self._path_var_busy:
            return
        self._path_var_busy = True
        self._start_path_var_check()

    def _start_path_var_check(self):
        # kicad_running is looked up at call time so tests can replace the module attribute
        worker = TaskWorker(lambda progress: kicad_running(), parent=self)
        # Finished threads are never deleteLater'd, same rule as the import dialog's _reap
        self._path_var_workers.append(worker)
        self._path_var_check = worker
        worker.result.connect(self._on_path_var_check)
        worker.failed.connect(self._on_path_var_check_failed)
        worker.finished.connect(lambda w=worker: self._on_path_var_check_finished(w))
        worker.start()

    def _on_path_var_check_failed(self, text):
        # A failed check counts as KiCad closed, like kicad_running itself
        self._on_path_var_check([])

    def _on_path_var_check(self, names):
        if self._close_after_check:
            self._path_var_busy = False
            return
        names = list(names)
        issues = sync_kicad_path_vars(
            REPO_ROOT,
            running=lambda: names,
            confirm=lambda changes: self._confirm_path_var_changes(changes, names),
        )
        self._log_issues(issues)
        if any(issue.code == "config.retry" for issue in issues):
            # Retry: look again; with KiCad closed the normal Yes/No question follows, so
            # nothing is written without a confirm. _path_var_busy stays set meanwhile.
            self._start_path_var_check()
            return
        self._path_var_busy = False

    def _on_path_var_check_finished(self, worker):
        # QThread.finished arrives just before the thread ends, so this only joins a thread
        # whose work has returned
        worker.wait(2000)
        if self._path_var_check is worker:
            self._path_var_check = None
        if self._close_after_check and self._path_var_check is None:
            self.close()

    def _on_generate(self):
        if not self._scan_result:
            self._log.log("No scan results available. Please wait for scan.", "error")
            return

        dest = self._dest_path()
        if dest is None:
            self._log.log(_NO_DEST_TEXT, "warning")
            return
        if not dest.exists():
            self._log.log(f"Destination folder does not exist: {dest}", "error")
            return

        sym_selected = [lib for lib in self._scan_result.symbol_libs if lib.selected]
        fp_selected = [lib for lib in self._scan_result.footprint_libs if lib.selected]

        if not sym_selected and not fp_selected:
            self._log.log("No libraries selected.", "warning")
            return

        self._log.log(
            f"Generating tables ({len(sym_selected)} symbols, "
            f"{len(fp_selected)} footprints)...",
            "info",
        )

        self._log_issues(write_tables(
            dest, self._scan_result.symbol_libs, self._scan_result.footprint_libs
        ))

        # Offer KiCad path variable changes (never written silently), independent of
        # how the table writes went
        self._sync_path_vars()

        # Save destination to history
        history = add_dest_to_history(str(dest))
        self._dest_combo.blockSignals(True)
        self._dest_combo.clear()
        self._dest_combo.addItems(history)
        self._dest_combo.setCurrentIndex(0)
        self._dest_combo.blockSignals(False)

    def _on_rescan(self):
        self._log.log("Rescanning repository...", "info")
        self._log_existing_tables(self._dest_path())
        self._start_scan()

    def _on_restore_backup(self):
        dest = self._dest_path()
        dialog = BackupDialog(str(dest) if dest is not None else "", parent=self)
        if dialog.exec() and dialog.selected_backup_num is not None:
            self._log_issues(restore_backup_pair(
                dialog.selected_folder, dialog.selected_backup_num
            ))

    def _on_set_kicad_path(self):
        if self._worker is not None:
            self._log.log("A scan is already running; request ignored.", "info")
            return
        current = str(self._kicad_fp_dir) if self._kicad_fp_dir else "C:/Program Files"
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select KiCad footprints folder",
            current,
        )
        if folder:
            self._kicad_fp_dir = Path(folder)
            save_kicad_fp_dir(self._kicad_fp_dir)
            self._log.log(
                f"KiCad footprints set to: {self._kicad_fp_dir}", "success"
            )
            self._log.log("Rescanning with updated KiCad path...", "info")
            self._start_scan()

    def _on_browse_dest(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select destination folder", self._dest_combo.currentText().strip()
        )
        if folder:
            history = add_dest_to_history(folder)
            self._dest_combo.blockSignals(True)
            self._dest_combo.clear()
            self._dest_combo.addItems(history)
            self._dest_combo.setCurrentIndex(0)
            self._dest_combo.blockSignals(False)
            self._log_existing_tables(self._dest_path())

    def _on_dest_changed(self, *_args):
        """Destination picked or typed: only report which tables exist there."""
        self._log_existing_tables(self._dest_path())

    def _on_select_all(self):
        self._tree.select_all()

    def _on_deselect_all(self):
        self._tree.deselect_all()

    def _guide_window(self) -> HelpDialog:
        """The one User Guide window, built on first use and centred over this window before its first show."""
        if self._guide is None:
            self._guide = HelpDialog()  # no parent: a parent would let a window-modal dialog block it
            centre_window(self._guide, self)
        return self._guide

    def show_guide(self, topic: str | None = None):
        """Show the shared User Guide, on this topic when one is given; the same window every time."""
        first = self._guide is None
        guide = self._guide_window()
        if topic is not None:
            guide.show_topic(topic)
        guide.show()
        if first:
            # The frame is only known once shown, so centre again (inside the free area)
            centre_window(self._guide, self)
        guide.raise_()
        guide.activateWindow()

    def _on_help(self):
        self.show_guide()

    def _on_about(self):
        about = QMessageBox(self)
        about.setWindowTitle(f"About {APP_TITLE}")
        about.setTextFormat(Qt.TextFormat.RichText)
        about.setText(
            f"<h3>{APP_TITLE} v1.0</h3>"
            "<p>Scan and manage KiCad symbol and footprint libraries.<br>"
            "Generate library tables for use in KiCad projects.</p>"
            '<p>Repository: <a href="https://github.com/sylvanoMTL/kicad_libraries">'
            "github.com/sylvanoMTL/kicad_libraries</a></p>"
        )
        about.exec()

    def closeEvent(self, event: QCloseEvent):
        # An install or a git job cannot be interrupted: the window stays until it ends
        # (D-07, D-10, T-05-33, T-06-24)
        dialog = self._import_dialog
        if dialog is not None:
            if dialog.is_installing() or dialog.is_committing():
                event.ignore()
                return
            # The dialog closes at once when idle, otherwise after its workers end (it shows it is
            # finishing); this window then closes by itself (D-06)
            dialog.reject()
            if dialog.is_finishing():
                self._close_after_dialog = True
                event.ignore()
                return
        # The KiCad-open check runs on a worker: the window never waits for it here. The
        # finished handler closes the window once the check is over (T-12-16)
        if self._path_var_check is not None:
            self._close_after_check = True
            event.ignore()
            return
        # The check dialog only holds the last scan result, so closing it loses nothing
        if self._atomic_dialog is not None:
            self._atomic_dialog.reject()
        # Never destroy a running QThread
        if self._worker is not None:
            self._worker.wait()
        # A visible parentless window would keep the app running after this one closes
        if self._guide is not None:
            self._guide.close()
        save_window_geometry(self.saveGeometry())
        super().closeEvent(event)
