from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QFileDialog, QMessageBox,
    QProgressDialog,
)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QAction, QKeySequence, QCloseEvent

from .library_scanner import scan_all, find_kicad_footprint_dir, sync_kicad_path_vars
from .table_generator import write_tables, restore_backup_pair, table_info, TableInfo
from .models import Issue, ScanResult, Severity
from .settings import (
    load_kicad_fp_dir, save_kicad_fp_dir,
    load_dest_history, add_dest_to_history,
    load_window_geometry, save_window_geometry,
)
from .widgets.library_table import LibraryTableWidget
from .widgets.log_panel import LogPanel
from .widgets.backup_dialog import BackupDialog
from .widgets.help_dialog import HelpDialog

APP_TITLE = "KiCad External Lib Manager"
REPO_ROOT = Path(__file__).parent.parent.resolve()


def _selected_count(result: ScanResult) -> int:
    return (
        sum(1 for lib in result.symbol_libs if lib.selected)
        + sum(1 for lib in result.footprint_libs if lib.selected)
    )


class ScanWorker(QThread):
    progress = Signal(str, int)  # message, percentage
    finished = Signal(object)    # ScanResult
    error = Signal(str)

    def __init__(self, repo_root: Path, kicad_fp_dir: Path | None = None):
        super().__init__()
        self._repo_root = repo_root
        self._kicad_fp_dir = kicad_fp_dir

    def run(self):
        try:
            def on_progress(msg: str, current: int, total: int):
                pct = int(current / max(total, 1) * 100)
                self.progress.emit(msg, pct)

            result = scan_all(self._repo_root, progress=on_progress,
                              kicad_fp_dir=self._kicad_fp_dir)
            self.finished.emit(result)
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
        self._worker: ScanWorker | None = None
        # Armed once here; _finish_scan consumes it after the first scan ends,
        # however that scan ended. Only that scan pre-selects from the tables.
        self._startup_pending = True
        self._kicad_fp_dir: Path | None = None
        self._build_menu()
        self._build_ui()
        self.statusBar()  # Enable status bar for menu hints

        # Detect KiCad installation, then start scan
        self._detect_kicad()
        self._log_existing_tables(Path(self._dest_combo.currentText()))
        self._start_scan()

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        # Kept as attributes: _set_scan_running toggles them while a scan runs
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
        self._generate_btn.setStyleSheet(
            "QPushButton { background-color: #0078D4; color: white; "
            "padding: 6px 16px; font-weight: bold; }"
        )
        self._generate_btn.clicked.connect(self._on_generate)
        toolbar.addWidget(self._generate_btn)

        layout.addLayout(toolbar)

        # Library tree
        self._tree = LibraryTableWidget()
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

    def _log_existing_tables(self, dest: Path):
        """Log which table files exist at the destination; never touches selection."""
        if not dest.is_dir():
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
            self._act_generate, self._generate_btn,
        ):
            control.setEnabled(not running)

    def _start_scan(self):
        """Start a scan; every scan request must go through here.

        Refuses while a worker exists, because a disabled control does not stop a
        programmatic caller (the post-import rescan included). The guard keys on
        the worker reference, not on the thread's running state: the custom
        finished signal fires while run() has not returned yet.
        """
        if self._worker is not None:
            self._log.log("A scan is already running; request ignored.", "info")
            return

        self._set_scan_running(True)
        self._progress = QProgressDialog(
            "Scanning libraries...", None, 0, 100, self
        )
        self._progress.setWindowTitle("Loading Libraries")
        self._progress.setWindowModality(Qt.WindowModality.WindowModal)
        self._progress.setMinimumDuration(0)
        self._progress.setAutoClose(True)
        self._progress.setAutoReset(True)
        self._progress.setCancelButton(None)
        self._progress.setValue(0)
        self._progress.show()

        self._log.log("Scanning repository...", "info")

        self._worker = ScanWorker(REPO_ROOT, self._kicad_fp_dir)
        self._worker.progress.connect(self._on_scan_progress)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.error.connect(self._on_scan_error)
        self._worker.start()

    def _on_scan_progress(self, message: str, percentage: int):
        self._progress.setLabelText(message)
        self._progress.setValue(min(percentage, 99))

    def _finish_scan(self):
        """Release the worker and re-enable the controls; always runs after a scan."""
        self._startup_pending = False
        if self._worker is not None:
            self._worker.wait()
            self._worker = None
        self._set_scan_running(False)

    def _on_scan_finished(self, result: ScanResult):
        try:
            self._progress.setValue(100)
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

            self._tree.populate(result)

            self._log_issues(result.issues)

            if not any(
                i.severity in (Severity.WARNING, Severity.ERROR) for i in result.issues
            ):
                self._log.log("No warnings.", "success")
        finally:
            self._finish_scan()

    def _reapply_selection(self, previous: ScanResult | None, result: ScanResult):
        """Carry the user's selection over to a fresh scan, keyed by rel_path.

        New libraries start unchecked and vanished ones drop out. Without a
        previous result (rescan after a failed startup scan) nothing is kept.
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

        kept = _selected_count(result)
        self._log.log(f"Kept {kept} selections after rescan", "info")
        missing = (
            (keep_sym - {lib.rel_path for lib in result.symbol_libs})
            | (keep_fp - {lib.rel_path for lib in result.footprint_libs})
        )
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
        dest = Path(self._dest_combo.currentText())
        if not dest.is_dir():
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
            self._progress.close()
            self._log.log(f"Scan error: {error_msg}", "error")
            if self._startup_pending:
                self._log.log(
                    "Startup scan failed, so nothing was pre-selected from the "
                    "destination tables; a Rescan starts with every library unchecked "
                    "(restart the app to pre-select from the tables).",
                    "info",
                )
        finally:
            self._finish_scan()

    def _log_issues(self, issues: list[Issue]):
        for issue in issues:
            self._log.log_issue(issue)

    def _on_generate(self):
        if not self._scan_result:
            self._log.log("No scan results available. Please wait for scan.", "error")
            return

        dest = Path(self._dest_combo.currentText())
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

        # Sync KiCad path variables, independent of how the table writes went
        self._log_issues(sync_kicad_path_vars(REPO_ROOT))

        # Save destination to history
        history = add_dest_to_history(str(dest))
        self._dest_combo.blockSignals(True)
        self._dest_combo.clear()
        self._dest_combo.addItems(history)
        self._dest_combo.setCurrentIndex(0)
        self._dest_combo.blockSignals(False)

    def _on_rescan(self):
        self._log.log("Rescanning repository...", "info")
        self._log_existing_tables(Path(self._dest_combo.currentText()))
        self._start_scan()

    def _on_restore_backup(self):
        dialog = BackupDialog(self._dest_combo.currentText(), parent=self)
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
            self, "Select destination folder", self._dest_combo.currentText()
        )
        if folder:
            history = add_dest_to_history(folder)
            self._dest_combo.blockSignals(True)
            self._dest_combo.clear()
            self._dest_combo.addItems(history)
            self._dest_combo.setCurrentIndex(0)
            self._dest_combo.blockSignals(False)
            self._log_existing_tables(Path(self._dest_combo.currentText()))

    def _on_dest_changed(self, *_args):
        """Destination picked or typed: only report which tables exist there."""
        self._log_existing_tables(Path(self._dest_combo.currentText()))

    def _on_select_all(self):
        self._tree.select_all()

    def _on_deselect_all(self):
        self._tree.deselect_all()

    def _on_help(self):
        HelpDialog(parent=self).exec()

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
        # Never destroy a running QThread
        if self._worker is not None:
            self._worker.wait()
        save_window_geometry(self.saveGeometry())
        super().closeEvent(event)
