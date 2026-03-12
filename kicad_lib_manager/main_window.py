from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QFileDialog, QMessageBox,
    QProgressDialog,
)
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QAction, QKeySequence

from .library_scanner import scan_all, find_kicad_footprint_dir
from .table_generator import write_tables, restore_backup_pair
from .models import ScanResult
from .widgets.library_table import LibraryTableWidget
from .widgets.log_panel import LogPanel
from .widgets.backup_dialog import BackupDialog

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
        self.setWindowTitle("KiCad Library Manager")
        self.resize(1100, 750)

        self._scan_result: ScanResult | None = None
        self._worker: ScanWorker | None = None
        self._kicad_fp_dir: Path | None = None
        self._build_menu()
        self._build_ui()
        self.statusBar()  # Enable status bar for menu hints

        # Detect KiCad installation, then start scan
        self._detect_kicad()
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

        about_action = QAction("&About", self)
        about_action.setToolTip("About KiCad Library Manager")
        about_action.setStatusTip("About KiCad Library Manager")
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
        self._dest_edit = QLineEdit(str(REPO_ROOT))
        self._dest_edit.setMinimumWidth(300)
        toolbar.addWidget(self._dest_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse_dest)
        toolbar.addWidget(browse_btn)

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

    def _detect_kicad(self):
        self._kicad_fp_dir = find_kicad_footprint_dir()
        if self._kicad_fp_dir:
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

        self._tree.populate(result)

        for warning in result.warnings:
            self._log.log(warning, "warning")

        if not result.warnings:
            self._log.log("No warnings.", "success")

        self._worker.wait()
        self._worker = None

    def _on_scan_error(self, error_msg: str):
        self._progress.close()
        self._log.log(f"Scan error: {error_msg}", "error")
        self._worker.wait()
        self._worker = None

    def _on_generate(self):
        if not self._scan_result:
            self._log.log("No scan results available. Please wait for scan.", "error")
            return

        dest = Path(self._dest_edit.text())
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

        messages = write_tables(
            dest, self._scan_result.symbol_libs, self._scan_result.footprint_libs
        )
        for msg in messages:
            self._log.log(msg, "success")

    def _on_restore_backup(self):
        dialog = BackupDialog(self._dest_edit.text(), parent=self)
        if dialog.exec() and dialog.selected_backup_num is not None:
            messages = restore_backup_pair(
                dialog.selected_folder, dialog.selected_backup_num
            )
            for msg in messages:
                self._log.log(msg, "success")

    def _on_set_kicad_path(self):
        current = str(self._kicad_fp_dir) if self._kicad_fp_dir else "C:/Program Files"
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select KiCad footprints folder",
            current,
        )
        if folder:
            self._kicad_fp_dir = Path(folder)
            self._log.log(
                f"KiCad footprints set to: {self._kicad_fp_dir}", "success"
            )
            self._log.log("Rescanning with updated KiCad path...", "info")
            self._start_scan()

    def _on_browse_dest(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select destination folder", self._dest_edit.text()
        )
        if folder:
            self._dest_edit.setText(folder)

    def _on_select_all(self):
        self._tree.select_all()

    def _on_deselect_all(self):
        self._tree.deselect_all()

    def _on_about(self):
        about = QMessageBox(self)
        about.setWindowTitle("About KiCad Library Manager")
        about.setTextFormat(Qt.TextFormat.RichText)
        about.setText(
            "<h3>KiCad Library Manager v1.0</h3>"
            "<p>Scan and manage KiCad symbol and footprint libraries.<br>"
            "Generate library tables for use in KiCad projects.</p>"
            '<p>Repository: <a href="https://github.com/sylvanoMTL/kicad_libraries">'
            "github.com/sylvanoMTL/kicad_libraries</a></p>"
        )
        about.exec()
