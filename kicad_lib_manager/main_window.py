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
from .models import Issue, ScanResult
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

        gen_action = QAction("&Generate Tables", self)
        gen_action.setShortcut(QKeySequence("Ctrl+G"))
        gen_action.setToolTip("Generate sym-lib-table and fp-lib-table from selected libraries")
        gen_action.setStatusTip("Generate sym-lib-table and fp-lib-table from selected libraries")
        gen_action.triggered.connect(self._on_generate)
        file_menu.addAction(gen_action)

        restore_action = QAction("&Restore Backup...", self)
        restore_action.setShortcut(QKeySequence("Ctrl+R"))
        restore_action.setToolTip("Restore a previous sym-lib-table / fp-lib-table backup pair")
        restore_action.setStatusTip("Restore a previous sym-lib-table / fp-lib-table backup pair")
        restore_action.triggered.connect(self._on_restore_backup)
        file_menu.addAction(restore_action)

        rescan_action = QAction("Re&scan Libraries", self)
        rescan_action.setShortcut(QKeySequence("Ctrl+Shift+R"))
        rescan_action.setToolTip("Rescan the repository for symbol and footprint libraries")
        rescan_action.setStatusTip("Rescan the repository for symbol and footprint libraries")
        rescan_action.triggered.connect(self._on_rescan)
        file_menu.addAction(rescan_action)

        kicad_action = QAction("Set KiCad &Footprint Path...", self)
        kicad_action.setShortcut(QKeySequence("Ctrl+K"))
        kicad_action.setToolTip("Set KiCad default footprint library folder for cross-referencing")
        kicad_action.setStatusTip("Set KiCad default footprint library folder for cross-referencing")
        kicad_action.triggered.connect(self._on_set_kicad_path)
        file_menu.addAction(kicad_action)

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

        rescan_btn = QPushButton("Rescan")
        rescan_btn.setToolTip("Rescan repository for libraries (Ctrl+Shift+R)")
        rescan_btn.clicked.connect(self._on_rescan)
        toolbar.addWidget(rescan_btn)

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

    def _start_scan(self):
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

    def _on_scan_finished(self, result: ScanResult):
        self._progress.setValue(100)
        self._scan_result = result

        sym_count = len(result.symbol_libs)
        fp_count = len(result.footprint_libs)
        self._log.log(
            f"Found {sym_count} symbol libraries, {fp_count} footprint libraries.",
            "success",
        )

        # Pre-select libraries that exist in the current table files
        self._apply_existing_selection(result)

        self._tree.populate(result)

        for warning in result.warnings:
            self._log.log(warning, "warning")

        if not result.warnings:
            self._log.log("No warnings.", "success")

        self._worker.wait()
        self._worker = None

    def _apply_existing_selection(self, result: ScanResult):
        """Pre-select libraries that are already present in the destination tables."""
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
        self._progress.close()
        self._log.log(f"Scan error: {error_msg}", "error")
        self._worker.wait()
        self._worker = None

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

        # Sync KiCad path variables
        path_msgs = sync_kicad_path_vars(REPO_ROOT)
        for msg in path_msgs:
            if "Failed" in msg or "Could not" in msg or "not found" in msg:
                self._log.log(msg, "warning")
            else:
                self._log.log(msg, "success")

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
        save_window_geometry(self.saveGeometry())
        super().closeEvent(event)
