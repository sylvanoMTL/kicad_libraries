"""The Import Part dialog (Phase 5): open a package, preview the real plan, install that plan.

One window-modal dialog with a Start, an Edit and a Result page. Every slow call of the import
core (open_package, detect_candidate, build_plan, apply_plan) runs on a TaskWorker thread and the
dialog only renders results, so the GUI never blocks (Phase 4 D-03).

Three rules shape this module:
- PREV-07: the preview shows one InstallPlan and Install applies exactly that object. Rebuilds are
  serialised (one build_plan at a time, the latest request wins) and carry a generation number, so
  a result older than the newest request is dropped and a stale plan can never be installed.
- WR-04: the dialog owns the opened Package. It closes it only after every open and build worker
  has ended, and it refuses to close at all while the install worker runs.
- Nothing is written before Install Part. Opening and rebuilding are read-only.
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QStandardPaths, QThread, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QColor, QResizeEvent, QShowEvent
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QListView, QListWidget, QListWidgetItem, QProgressBar, QPushButton, QScrollArea, QSizePolicy,
    QSplitter, QStackedWidget, QVBoxLayout, QWidget,
)

from ..importer.applier import apply_plan
from ..importer.candidate import ImportCandidate
from ..importer.detect import detect_candidate
from ..importer.downloads import age_text, newest_zip
from ..importer.form import FieldDefaults, FormValues, build_options
from ..importer.layout import RepoLayout, list_existing_libraries
from ..importer.package import Package, open_package
from ..importer.plan import InstallOptions, InstallPlan, InstallResult, Resolution, ToolContext
from ..importer.planner import build_plan, detect_tools
from ..importer.preview import file_counts, preview_sections
from ..importer.suggest import LibrarySuggestion, suggest_library
from ..kicad_process import kicad_running
from ..models import Issue, Severity
from ..settings import load_import_dir, save_import_dir
from .preview_tree import PreviewTree
from .theme import AMBER, ERROR, HEADING_PT, MUTED, SP_LG, SP_MD, SP_XL

_SEVERITY_GLYPH = {Severity.ERROR: "✖", Severity.WARNING: "⚠"}
_SEVERITY_COLOR = {Severity.ERROR: ERROR, Severity.WARNING: AMBER}
_ISSUE_LIST_MAX_HEIGHT = 160
_NOTHING_FOUND = "No KiCad symbol or footprint was found in this package."
_CLOSING_REFUSED = "Pick another file."
_CLOSING_EMPTY = "Check that you downloaded the KiCad format, then pick another file."
_DEBOUNCE_MS = 300  # text edits rebuild this long after the last keystroke (D-06)
_CHECKLIST_ROWS = 6  # footprint rows shown before the list scrolls
_LINKED_SUFFIX = "  (linked)"
_NO_MODEL = "No model"

# Vendor names of the adapters (importer/adapters) as shown in the package header
_VENDOR_LABELS = {"UltraLibrarian": "Ultra Librarian", "Loose": "Loose files", "Unknown": "Unknown vendor"}


def vendor_label(vendor: str) -> str:
    """The display name of an adapter's vendor; an unmapped name is shown as it is."""
    return _VENDOR_LABELS.get(vendor, vendor)

_START_BODY = (
    "Open a .zip from Ultra Librarian, SnapEDA or SamacSys, or a folder of KiCad files. "
    "Nothing is written until you click Install Part."
)


def default_downloads_dir() -> Path | None:
    """The user's Downloads folder: the Qt standard location, else ~/Downloads, else None."""
    for text in QStandardPaths.standardLocations(QStandardPaths.StandardLocation.DownloadLocation):
        if text and Path(text).is_dir():
            return Path(text)
    fallback = Path.home() / "Downloads"
    return fallback if fallback.is_dir() else None


class _OfferLabel(QLabel):
    """One-line plain-text label that elides the middle of a name to fit its width (UI E3/overflow)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._parts: tuple[str, str, str] | None = None

    def set_parts(self, prefix: str, name: str, suffix: str):
        self._parts = (prefix, name, suffix)
        self._refresh()

    def set_plain(self, text: str):
        self._parts = None
        self.setText(text)

    def full_text(self) -> str:
        """The text before eliding."""
        return "".join(self._parts) if self._parts is not None else self.text()

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        if self._parts is None:
            return
        prefix, name, suffix = self._parts
        full = prefix + name + suffix
        metrics = self.fontMetrics()
        width = self.contentsRect().width()
        shown = full
        # width < 40: not laid out yet; show everything and elide on the first real resize
        if width >= 40 and metrics.horizontalAdvance(full) > width:
            room = width - metrics.horizontalAdvance(prefix) - metrics.horizontalAdvance(suffix)
            shown = prefix + metrics.elidedText(
                name, Qt.TextElideMode.ElideMiddle, max(room, metrics.horizontalAdvance("…"))
            ) + suffix
        if self.text() != shown:
            self.setText(shown)


class TaskWorker(QThread):
    """Run one callable off the GUI thread and report its result with queued signals.

    The signals are named result/failed, not finished: a custom finished signal shadows
    QThread.finished. fn receives progress.emit, so a progress callback only ever emits.
    """

    progress = Signal(str, int, int)
    result = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable, parent=None, tag=None):
        super().__init__(parent)
        self._fn = fn
        self.tag = tag
        self.value = None  # the fn result, kept so a close can still release a Package it holds

    def run(self):
        try:
            self.value = self._fn(self.progress.emit)
            self.result.emit(self.value)
        except Exception as e:  # thread boundary only
            self.failed.emit(f"{type(e).__name__}: {e}")


@dataclass(frozen=True)
class ImportCore:
    """The import core functions the dialog calls; tests replace single fields with fakes."""

    open_package: Callable = open_package
    detect_candidate: Callable = detect_candidate
    detect_tools: Callable = detect_tools
    build_plan: Callable = build_plan
    apply_plan: Callable = apply_plan
    kicad_running: Callable = kicad_running
    list_existing_libraries: Callable = list_existing_libraries
    suggest_library: Callable = suggest_library
    downloads_dir: Callable = default_downloads_dir


@dataclass(frozen=True)
class OpenOutcome:
    """What the open worker hands to the GUI thread; the dialog owns the package from then on."""

    package: Package
    candidate: ImportCandidate | None
    detect_issues: tuple
    tools: ToolContext | None
    suggestion: LibrarySuggestion | None
    existing: tuple


class ImportDialog(QDialog):
    """Window-modal import dialog. Emits installed(InstallResult, InstallPlan) after a successful install."""

    installed = Signal(object, object)
    issues_logged = Signal(object)  # list[Issue]; the main window routes them to the log

    def __init__(
        self,
        repo_root: Path,
        layout: RepoLayout,
        *,
        kicad_fp_dir: Path | None = None,
        package_path: Path | None = None,
        core: ImportCore | None = None,
        backup_root: Path | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._repo_root = Path(repo_root)
        self._repo_layout = layout
        self._kicad_fp_dir = kicad_fp_dir
        self._core = core or ImportCore()
        self._backup_root = backup_root

        # Public: the successful InstallResult. Shadows QDialog.result() on this instance (by design).
        self.result: InstallResult | None = None

        self._package: Package | None = None
        self._candidate: ImportCandidate | None = None
        self._tools: ToolContext | None = None
        self._suggestion: LibrarySuggestion | None = None
        self._existing: tuple = ()

        # Rebuild coordinator (PREV-07): serialised builds, the latest request wins
        self._gen = 0
        self._building: TaskWorker | None = None
        self._queued: InstallOptions | None = None
        self._plan: InstallPlan | None = None
        self._plan_gen = -1
        self._plan_options: InstallOptions | None = None
        self._build_failed = False
        self._last_requested_library = ""
        self._install_failure = ""

        # Left-pane choices (plan 05-07). The item controls exist only for the package that is open.
        self._symbol_combo: QComboBox | None = None
        self._symbol_label: _OfferLabel | None = None
        self._fp_list: QListWidget | None = None
        self._fp_label: _OfferLabel | None = None
        self._make_linked_btn: QPushButton | None = None
        self._model_combo: QComboBox | None = None
        self._model_label: _OfferLabel | None = None
        self._extends_note: QLabel | None = None
        self._linked_fp: str | None = None  # vendor name of the linked footprint
        self._defaults = FieldDefaults()
        self._resolutions: dict[str, Resolution] = {}  # conflict choices; plan 05-10 fills them
        self._first_plan_seen = False
        self._syncing = False  # True while the dialog sets control values itself
        self._dirty = False  # a text edit waits for its debounce, so the plan on screen is not current
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._on_debounce)

        self._workers: list[TaskWorker] = []
        self._open_worker: TaskWorker | None = None
        self._install_worker: TaskWorker | None = None
        self._closing = False

        self.setWindowTitle("Import Part")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(1100, 720)
        self.setMinimumSize(900, 600)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(8)
        self._stack = QStackedWidget()
        outer.addWidget(self._stack)
        self._build_start_page()
        self._build_edit_page()
        self._build_result_page()
        self._stack.setCurrentWidget(self._start_page)

        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
            button.setDefault(False)

        self._update_install_state()
        if package_path is not None:
            QTimer.singleShot(0, lambda: self.open_path(Path(package_path)))

    # -- pages ------------------------------------------------------------------

    def _build_start_page(self):
        """A centred column (max 560 wide, 32 px top inset, 24 px between blocks), UI-SPEC start step."""
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, SP_XL, 0, 0)
        row = QHBoxLayout()
        row.addStretch(1)
        column = QWidget()
        column.setMaximumWidth(560)
        lay = QVBoxLayout(column)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(SP_LG)
        row.addWidget(column, 100)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(1)
        self._start_column = column

        self._start_heading = QLabel("Choose a part package")
        font = self._start_heading.font()
        font.setPointSize(HEADING_PT)
        font.setBold(True)
        self._start_heading.setFont(font)
        lay.addWidget(self._start_heading)

        self._start_body = QLabel(_START_BODY)
        self._start_body.setTextFormat(Qt.TextFormat.PlainText)
        self._start_body.setWordWrap(True)
        lay.addWidget(self._start_body)

        # The Downloads offer; replaced by the reading box while a package is read
        self._offer_ready = False
        self._offer_requested = False
        self._offer_folder: Path | None = None
        self._offer_path: Path | None = None
        self._offer_row = QWidget()
        offer_lay = QHBoxLayout(self._offer_row)
        offer_lay.setContentsMargins(0, 0, 0, 0)
        offer_lay.setSpacing(8)
        self._offer_label = _OfferLabel()
        offer_lay.addWidget(self._offer_label, 1)
        self._offer_open_btn = QPushButton("Open")
        self._offer_open_btn.clicked.connect(self._on_offer_open)
        offer_lay.addWidget(self._offer_open_btn)
        lay.addWidget(self._offer_row)

        self._reading_box = QWidget()
        reading_lay = QVBoxLayout(self._reading_box)
        reading_lay.setContentsMargins(0, 0, 0, 0)
        reading_lay.setSpacing(8)
        self._reading_label = QLabel("Reading package...")
        self._reading_label.setTextFormat(Qt.TextFormat.PlainText)
        self._reading_bar = QProgressBar()
        self._reading_bar.setRange(0, 0)
        reading_lay.addWidget(self._reading_label)
        reading_lay.addWidget(self._reading_bar)
        lay.addWidget(self._reading_box)

        self._browse_btn = QPushButton("Browse zip...")
        self._browse_btn.clicked.connect(self._on_browse)
        self._browse_folder_btn = QPushButton("Browse folder...")
        self._browse_folder_btn.clicked.connect(self._on_browse_folder)
        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self._browse_btn)
        buttons.addWidget(self._browse_folder_btn)
        buttons.addStretch()
        lay.addLayout(buttons)

        # Shown only after a refused or empty package: the error state of the Start page (D-05)
        self._issue_box = QWidget()
        issue_lay = QVBoxLayout(self._issue_box)
        issue_lay.setContentsMargins(0, 0, 0, 0)
        issue_lay.setSpacing(8)
        self._issue_heading = self._heading("This package can't be imported")
        issue_lay.addWidget(self._issue_heading)
        self._issue_list = QListWidget()
        self._issue_list.setMaximumHeight(_ISSUE_LIST_MAX_HEIGHT)
        self._issue_list.setWordWrap(True)
        self._issue_list.setTextElideMode(Qt.TextElideMode.ElideNone)
        self._issue_list.setResizeMode(QListView.ResizeMode.Adjust)
        self._issue_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._issue_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._issue_list.setAccessibleName("Package issues")
        issue_lay.addWidget(self._issue_list)
        self._issue_closing = QLabel()
        self._issue_closing.setTextFormat(Qt.TextFormat.PlainText)
        self._issue_closing.setWordWrap(True)
        self._issue_closing.setStyleSheet(f"color: {MUTED};")
        issue_lay.addWidget(self._issue_closing)
        self._issue_box.hide()
        lay.addWidget(self._issue_box)

        self._set_reading(False)
        self._start_page = page
        self._stack.addWidget(page)
        self._browse_btn.setFocus()

    def _build_edit_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        # Package header: name (bold), vendor (muted), Change... on the right, over a 1px line
        header = QHBoxLayout()
        header.setSpacing(8)
        self._package_label = QLabel()
        self._package_label.setTextFormat(Qt.TextFormat.PlainText)
        font = self._package_label.font()
        font.setBold(True)
        self._package_label.setFont(font)
        header.addWidget(self._package_label)
        self._vendor_label = QLabel()
        self._vendor_label.setTextFormat(Qt.TextFormat.PlainText)
        self._vendor_label.setStyleSheet(f"color: {MUTED};")
        header.addWidget(self._vendor_label)
        header.addStretch(1)
        self._change_btn = QPushButton("Change...")
        self._change_btn.clicked.connect(self._on_change)
        header.addWidget(self._change_btn)
        lay.addLayout(header)
        rule = QFrame()
        rule.setFrameShape(QFrame.Shape.HLine)
        rule.setFixedHeight(1)
        lay.addWidget(rule)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left: choices, scrolling vertically
        self._left_scroll = QScrollArea()
        self._left_scroll.setWidgetResizable(True)
        self._left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(8)
        left_lay.addWidget(self._heading("Items"))
        self._items_host = QWidget()
        self._items_form = QFormLayout(self._items_host)
        self._items_form.setContentsMargins(0, 0, 0, 0)
        self._items_form.setSpacing(8)
        self._items_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self._items_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        left_lay.addWidget(self._items_host)
        left_lay.addSpacing(SP_MD)
        left_lay.addWidget(self._heading("Target library"))
        self._library_combo = QComboBox()
        self._library_combo.setEditable(True)
        self._library_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._library_combo.setAccessibleName("Target library")
        # Not currentTextChanged: that fires on every keystroke of a typed name
        self._library_combo.textActivated.connect(self._on_library_activated)
        self._library_combo.lineEdit().editingFinished.connect(self._on_library_edited)
        left_lay.addWidget(self._library_combo)
        left_lay.addSpacing(SP_MD)
        left_lay.addStretch()
        self._left_scroll.setWidget(left)
        self._left_scroll.setMinimumWidth(380)
        splitter.addWidget(self._left_scroll)

        # Right: the live preview
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(8)
        right_lay.addWidget(self._heading("Preview"))
        self._preview_stack = QStackedWidget()
        building = QWidget()
        building_lay = QVBoxLayout(building)
        building_lay.addStretch()
        building_label = QLabel("Building preview...")
        building_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        building_bar = QProgressBar()
        building_bar.setRange(0, 0)
        building_lay.addWidget(building_label)
        building_lay.addWidget(building_bar)
        building_lay.addStretch()
        self._building_page = building
        self._preview = PreviewTree()
        self._preview_stack.addWidget(building)
        self._preview_stack.addWidget(self._preview)
        right_lay.addWidget(self._preview_stack, stretch=1)
        right.setMinimumWidth(400)
        splitter.addWidget(right)
        splitter.setSizes([440, 660])
        lay.addWidget(splitter, stretch=1)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self._strip = QLabel()
        self._strip.setTextFormat(Qt.TextFormat.PlainText)
        self._strip.setWordWrap(True)
        bottom.addWidget(self._strip, stretch=1)
        self._install_btn = QPushButton("Install Part")
        self._install_btn.setMinimumWidth(112)
        self._install_btn.clicked.connect(self._on_install_clicked)
        bottom.addWidget(self._install_btn)
        lay.addLayout(bottom)

        self._edit_page = page
        self._stack.addWidget(page)

    def _build_result_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(8)
        self._banner = QLabel()
        self._banner.setTextFormat(Qt.TextFormat.PlainText)
        font = self._banner.font()
        font.setBold(True)
        font.setPointSize(12)
        self._banner.setFont(font)
        lay.addWidget(self._banner)
        lay.addWidget(self._heading("Files written"))
        self._result_list = QListWidget()
        lay.addWidget(self._result_list, stretch=1)
        close_row = QHBoxLayout()
        close_row.addStretch()
        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.accept)
        close_row.addWidget(self._close_btn)
        lay.addLayout(close_row)
        self._result_page = page
        self._stack.addWidget(page)

    @staticmethod
    def _heading(text: str) -> QLabel:
        label = QLabel(text)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        return label

    # -- opening a package ------------------------------------------------------

    def _set_reading(self, reading: bool):
        self._reading_box.setVisible(reading)
        self._offer_row.setVisible(not reading and self._offer_ready)
        self._browse_btn.setEnabled(not reading)
        self._browse_folder_btn.setEnabled(not reading)
        self._offer_open_btn.setEnabled(not reading)

    # -- the Downloads offer (D-02): listed only, opened by an explicit click --------

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        if not self._offer_requested:
            self._offer_requested = True
            self._browse_btn.setFocus()
            # After the dialog is shown: a OneDrive-redirected Downloads folder can be slow to list
            QTimer.singleShot(0, self._start_offer_lookup)

    def _start_offer_lookup(self):
        if self._closing:
            return
        core = self._core

        def task(progress):
            folder = core.downloads_dir()
            return folder, (newest_zip(folder) if folder is not None else None)

        worker = self._spawn(task)
        worker.result.connect(lambda value, w=worker: self._on_offer_found(*value))
        worker.failed.connect(lambda text, w=worker: self._on_offer_found(None, None))
        worker.start()

    def _on_offer_found(self, folder: Path | None, newest: tuple[Path, float] | None):
        if self._closing:
            return
        self._offer_ready = True
        self._offer_folder = folder
        self._offer_path = None
        self._offer_label.setToolTip("")
        self._offer_label.setStyleSheet("")
        self._offer_open_btn.hide()
        if folder is None:
            self._offer_label.set_plain("Downloads folder not found.")
        elif newest is None:
            self._offer_label.set_plain("No .zip files found in your Downloads folder.")
            self._offer_label.setStyleSheet(f"color: {MUTED};")
        else:
            path, mtime = newest
            self._offer_path = path
            self._offer_label.set_parts(
                "Newest in Downloads: ", path.name, f" ({age_text(time.time() - mtime)})"
            )
            self._offer_label.setToolTip(str(path))
            self._offer_open_btn.show()
        self._offer_row.setVisible(self._open_worker is None)

    def _on_offer_open(self):
        if self._offer_path is not None:
            self.open_path(self._offer_path)

    def _browse_start_dir(self) -> Path:
        """Where a file dialog opens: the last import folder, else Downloads, else the home folder."""
        saved = load_import_dir()
        if saved is not None:
            return saved
        downloads = self._offer_folder if self._offer_ready else self._core.downloads_dir()
        return downloads if downloads is not None else Path.home()

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open part package", str(self._browse_start_dir()), "Zip packages (*.zip)"
        )
        if path:
            self._pick(Path(path))

    def _on_browse_folder(self):
        path = QFileDialog.getExistingDirectory(
            self, "Open folder of KiCad files", str(self._browse_start_dir())
        )
        if path:
            self._pick(Path(path))

    def _pick(self, path: Path):
        """A file or folder the user chose: remember where it came from, then open it."""
        save_import_dir(path.parent)
        self.open_path(path)

    def open_path(self, path: Path):
        """Open a zip or folder on a worker; the dialog owns the resulting Package."""
        if self._closing or self._open_worker is not None:
            return
        if self._building is not None:
            self._building.wait()  # WR-04: never close the package under a running build
        self._discard_package()
        self._reset_edit_state()
        self._hide_issue_box()
        self._reading_label.setText("Reading package...")
        self._set_reading(True)
        self._stack.setCurrentWidget(self._start_page)
        core, repo_root, layout, fp_dir = self._core, self._repo_root, self._repo_layout, self._kicad_fp_dir

        def task(progress):
            package = core.open_package(path, repo_root, progress)
            try:
                candidate, detect_issues = core.detect_candidate(package)
                tools = suggestion = None
                existing: tuple = ()
                if candidate is not None:
                    tools = core.detect_tools(fp_dir)
                    existing = tuple(core.list_existing_libraries(layout))
                    if candidate.symbols:
                        suggestion = core.suggest_library(candidate.symbols[0].meta, existing)
            except BaseException:
                package.close()
                raise
            return OpenOutcome(package, candidate, tuple(detect_issues), tools, suggestion, existing)

        worker = self._spawn(task)
        self._open_worker = worker
        worker.progress.connect(self._on_open_progress)
        worker.result.connect(lambda outcome, w=worker: self._on_opened(w, outcome))
        worker.failed.connect(lambda text, w=worker: self._on_open_failed(w, text))
        worker.start()

    def _spawn(self, fn: Callable, tag=None) -> TaskWorker:
        """Create a worker owned by the dialog; it stays referenced until QThread.finished."""
        worker = TaskWorker(fn, parent=self, tag=tag)
        self._workers.append(worker)
        worker.finished.connect(lambda w=worker: self._reap(w))
        return worker

    def _reap(self, worker: TaskWorker):
        """Release a finished worker's result.

        The worker object itself stays until the dialog (its parent) is destroyed: calling
        deleteLater on a finished install worker crashed the process (access violation), so the
        finished threads are never deleted early.
        """
        worker.wait()
        if not isinstance(worker.value, OpenOutcome):
            worker.value = None

    def _on_open_progress(self, message: str, current: int, total: int):
        self._reading_label.setText(message)

    def _on_open_failed(self, worker: TaskWorker, text: str):
        if self._open_worker is worker:
            self._open_worker = None
        if self._closing:
            return
        issue = Issue(Severity.ERROR, "import.step_failed", f"Import step failed: {text}")
        self.issues_logged.emit([issue])
        self._show_start_issues([issue], refused=True)

    def _on_opened(self, worker: TaskWorker, outcome: OpenOutcome):
        if self._open_worker is worker:
            self._open_worker = None
        package = outcome.package
        worker.value = None  # handled here, so _shutdown does not close the package a second time
        if self._closing:
            package.close()
            return
        self._package = package
        issues = list(dict.fromkeys([*package.issues, *outcome.detect_issues]))
        self.issues_logged.emit(issues)
        candidate = outcome.candidate
        if package.refused or candidate is None or not candidate.symbols:
            # WR-06: package.issues are shown and logged even when detection found nothing.
            # "Refused" also covers a detection ERROR (a KiCad 5-only package): there is no
            # point in checking the download format then, only in picking another file.
            refused = package.refused or any(i.severity is Severity.ERROR for i in issues)
            self._discard_package()
            self._show_start_issues(issues, refused)
            return
        self._candidate = candidate
        self._tools = outcome.tools
        self._suggestion = outcome.suggestion
        self._existing = outcome.existing
        self.setWindowTitle(f"Import Part - {package.source.name}")
        self._package_label.setText(f"Package: {package.source.name}")
        self._vendor_label.setText(vendor_label(candidate.vendor))
        self._fill_library_combo()
        self._populate_items()
        self._preview_stack.setCurrentWidget(self._building_page)
        self._stack.setCurrentWidget(self._edit_page)
        self._request_rebuild()

    def _hide_issue_box(self):
        self._issue_box.hide()
        self._issue_list.clear()

    def _show_start_issues(self, issues: list[Issue], refused: bool):
        """Fill the Start page's error state: ERROR and WARNING rows, then the closing line.

        Rows are QListWidgetItem text, which is plain: no markup from a package is interpreted.
        """
        self._issue_list.clear()
        shown = [i for i in issues if i.severity in _SEVERITY_GLYPH]
        for issue in shown:
            item = QListWidgetItem(f"{_SEVERITY_GLYPH[issue.severity]} {issue.text}")
            item.setForeground(QColor(_SEVERITY_COLOR[issue.severity]))
            self._issue_list.addItem(item)
        if not shown:
            self._issue_list.addItem(QListWidgetItem(_NOTHING_FOUND))
        self._issue_closing.setText(_CLOSING_REFUSED if refused else _CLOSING_EMPTY)
        # Few rows need less than the 160 px cap; many rows scroll inside it
        row = max(self._issue_list.sizeHintForRow(0), self._issue_list.fontMetrics().height() + 8)
        wanted = row * self._issue_list.count() + 2 * self._issue_list.frameWidth() + 4
        self._issue_list.setMinimumHeight(min(_ISSUE_LIST_MAX_HEIGHT, wanted))
        self._issue_box.show()
        self._set_reading(False)
        self._stack.setCurrentWidget(self._start_page)
        self._browse_btn.setFocus()

    def _fill_library_combo(self):
        suggestion = self._suggestion
        names = [suggestion.name, *(a.name for a in suggestion.alternatives)]
        names.extend(lib.name for lib in self._existing)
        unique = list(dict.fromkeys(names))
        self._library_combo.blockSignals(True)
        try:
            self._library_combo.clear()
            self._library_combo.addItems(unique)
            self._library_combo.setCurrentIndex(0)
            self._library_combo.setEditText(suggestion.name)
        finally:
            self._library_combo.blockSignals(False)

    # -- the rebuild coordinator (PREV-07, D-06) -------------------------------

    def _reset_edit_state(self):
        self._gen += 1
        self._debounce.stop()
        self._dirty = False
        self._candidate = None
        self._suggestion = None
        self._tools = None
        self._queued = None
        self._plan = None
        self._plan_gen = -1
        self._plan_options = None
        self._build_failed = False
        self._install_failure = ""
        self._first_plan_seen = False
        self._defaults = FieldDefaults()
        self._resolutions = {}
        self._clear_items()
        self._preview.render(())
        self._preview_stack.setCurrentWidget(self._building_page)
        self._update_install_state()

    def _snapshot_options(self) -> InstallOptions:
        return build_options(self._form_values(), self._defaults, self._linked_fp)

    def _form_values(self) -> FormValues:
        """Read the controls: item choices as vendor names, the linked footprint first (IN-04)."""
        candidate = self._candidate
        symbol: str | None = None
        if self._symbol_combo is not None:
            symbol = self._symbol_combo.currentData()
        elif candidate.symbols:
            symbol = candidate.symbols[0].name

        footprints: tuple[str, ...] = ()
        if self._fp_list is not None:
            checked = self._checked_footprints()
            rest = [name for name in checked if name != self._linked_fp]
            footprints = (*([self._linked_fp] if self._linked_fp in checked else []), *rest)
        elif candidate.footprints:
            footprints = (candidate.footprints[0].name,)

        model: str | None = None
        no_model = False
        if self._model_combo is not None:
            if self._model_combo.currentIndex() == self._model_combo.count() - 1:
                no_model = True  # the final "No model" entry
            else:
                model = self._model_combo.currentData()
        elif candidate.models:
            model = candidate.models[0].filename
        return FormValues(
            library=self._library_combo.currentText(),
            symbol=symbol,
            footprints=footprints,
            model=model,
            no_model=no_model,
            footprint_name=None,
            fields={},
            resolutions=dict(self._resolutions),
        )

    # -- the item picker (INTK-07, D-04) -------------------------------------------

    def _clear_items(self):
        self._symbol_combo = self._model_combo = None
        self._symbol_label = self._fp_label = self._model_label = None
        self._fp_list = self._make_linked_btn = None
        self._extends_note = None
        self._linked_fp = None
        while self._items_form.rowCount():
            self._items_form.removeRow(0)

    @staticmethod
    def _item_label(name: str, *, missing: bool = False) -> "_OfferLabel":
        """A one-line plain label for a single item: the name elides in the middle, the tooltip holds it all."""
        label = _OfferLabel()
        if missing:
            label.set_plain(name)
            label.setStyleSheet(f"color: {AMBER};")
        else:
            label.set_parts("", name, "")
            label.setToolTip(name)
        return label

    @staticmethod
    def _item_combo(names: list[str], accessible: str) -> QComboBox:
        combo = QComboBox()
        combo.setAccessibleName(accessible)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(12)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for index, name in enumerate(names):
            combo.addItem(name, name)
            combo.setItemData(index, name, Qt.ItemDataRole.ToolTipRole)
        # The popup shows every full name even when the closed combo is narrower
        combo.view().setMinimumWidth(combo.view().sizeHintForColumn(0) + 32)
        combo.setToolTip(names[0] if names else "")
        return combo

    def _populate_items(self):
        """Build the Items controls for the open package: one item is a label, several a combo or checklist."""
        candidate = self._candidate
        self._clear_items()
        form = self._items_form

        # Symbol, with the note under it for a symbol that extends a parent
        symbol_box = QWidget()
        symbol_lay = QVBoxLayout(symbol_box)
        symbol_lay.setContentsMargins(0, 0, 0, 0)
        symbol_lay.setSpacing(4)
        if len(candidate.symbols) > 1:
            combo = self._item_combo([s.name for s in candidate.symbols], "Symbol")
            combo.currentIndexChanged.connect(self._on_symbol_changed)
            self._symbol_combo = combo
            symbol_lay.addWidget(combo)
        else:
            name = candidate.symbols[0].name if candidate.symbols else ""
            self._symbol_label = self._item_label(name)
            symbol_lay.addWidget(self._symbol_label)
        note = QLabel()
        note.setTextFormat(Qt.TextFormat.PlainText)
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {MUTED};")
        note.hide()
        self._extends_note = note
        symbol_lay.addWidget(note)
        form.addRow("Symbol", symbol_box)

        # Footprints: the linked one carries the model and names the symbol's Footprint field
        footprints = [f.name for f in candidate.footprints]
        if len(footprints) > 1:
            form.addRow("Footprints", self._build_footprint_list(footprints))
            self._linked_fp = footprints[0]
            self._render_footprint_list()
        elif footprints:
            self._fp_label = self._item_label(footprints[0])
            form.addRow("Footprints", self._fp_label)
            self._linked_fp = footprints[0]
        else:
            self._fp_label = self._item_label("No footprint in this package", missing=True)
            form.addRow("Footprints", self._fp_label)

        # 3D model: several give a combo that ends with "No model"
        models = [m.filename for m in candidate.models]
        if len(models) > 1:
            combo = self._item_combo([*models, _NO_MODEL], "3D model")
            combo.setItemData(len(models), None)
            combo.setItemData(len(models), _NO_MODEL, Qt.ItemDataRole.ToolTipRole)
            combo.currentIndexChanged.connect(self._on_model_changed)
            self._model_combo = combo
            form.addRow("3D model", combo)
        elif models:
            self._model_label = self._item_label(models[0])
            form.addRow("3D model", self._model_label)
        else:
            self._model_label = self._item_label("No 3D model in this package", missing=True)
            form.addRow("3D model", self._model_label)

    def _build_footprint_list(self, names: list[str]) -> QWidget:
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lst = QListWidget()
        lst.setAccessibleName("Footprints")
        lst.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lst.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        lst.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        lst.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for name in names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(Qt.ItemDataRole.UserRole, name)
            item.setToolTip(name)
            lst.addItem(item)
        # At most six rows tall, then the list scrolls vertically
        row = lst.sizeHintForRow(0)
        lst.setFixedHeight(row * min(len(names), _CHECKLIST_ROWS) + 2 * lst.frameWidth())
        lay.addWidget(lst)
        button = QPushButton("Make linked")
        button.setAutoDefault(False)
        button.setDefault(False)
        button.setEnabled(False)
        button.clicked.connect(self._on_make_linked)
        lay.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
        lst.itemChanged.connect(self._on_footprint_item_changed)
        lst.currentRowChanged.connect(self._update_make_linked)
        self._fp_list = lst
        self._make_linked_btn = button
        return host

    def _checked_footprints(self) -> list[str]:
        lst = self._fp_list
        return [
            lst.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(lst.count())
            if lst.item(i).checkState() == Qt.CheckState.Checked
        ]

    def _render_footprint_list(self):
        """Mark the linked row: bold with the suffix. Programmatic, so item signals are blocked."""
        lst = self._fp_list
        if lst is None:
            return
        lst.blockSignals(True)
        try:
            for i in range(lst.count()):
                item = lst.item(i)
                name = item.data(Qt.ItemDataRole.UserRole)
                linked = name == self._linked_fp and item.checkState() == Qt.CheckState.Checked
                item.setText(name + (_LINKED_SUFFIX if linked else ""))
                font = item.font()
                font.setBold(linked)
                item.setFont(font)
        finally:
            lst.blockSignals(False)
        self._update_make_linked()

    def _update_make_linked(self, _row: int = -1):
        lst, button = self._fp_list, self._make_linked_btn
        if lst is None or button is None:
            return
        item = lst.currentItem()
        button.setEnabled(
            item is not None
            and item.checkState() == Qt.CheckState.Checked
            and item.data(Qt.ItemDataRole.UserRole) != self._linked_fp
        )

    def _on_footprint_item_changed(self, _item: QListWidgetItem):
        if self._candidate is None or self._fp_list is None:
            return
        # Unchecking the linked row hands "linked" to the first row still checked
        checked = self._checked_footprints()
        if self._linked_fp not in checked:
            self._set_linked(checked[0] if checked else None)
        self._render_footprint_list()
        self._request_rebuild()

    def _on_make_linked(self):
        lst = self._fp_list
        item = lst.currentItem() if lst is not None else None
        if item is None or item.checkState() != Qt.CheckState.Checked:
            return
        self._set_linked(item.data(Qt.ItemDataRole.UserRole))
        self._render_footprint_list()
        self._request_rebuild()

    def _set_linked(self, name: str | None):
        self._linked_fp = name

    def _on_symbol_changed(self, _index: int = -1):
        combo = self._symbol_combo
        if combo is None or self._candidate is None:
            return
        combo.setToolTip(combo.currentText())
        self._request_rebuild()

    def _on_model_changed(self, _index: int = -1):
        combo = self._model_combo
        if combo is None or self._candidate is None:
            return
        combo.setToolTip(combo.currentText())
        self._request_rebuild()

    def _show_plan_in_form(self, plan: InstallPlan):
        """Show what the accepted plan says: the extends note under the symbol."""
        note = self._extends_note
        if note is not None:
            parents = plan.symbol_names[:-1]
            note.setText(f"extends parent {', '.join(parents)} is included automatically" if parents else "")
            note.setVisible(bool(parents))

    # -- text edits: a quiet period before the rebuild (D-06) ----------------------

    def _mark_dirty(self):
        """A text field changed: Install is off from the first keystroke, the rebuild follows after 300 ms."""
        self._dirty = True
        self._debounce.start()
        self._update_install_state()

    def _on_debounce(self):
        if self._dirty:
            self._request_rebuild()

    def _on_library_activated(self, _text: str = ""):
        self._request_rebuild()

    def _on_library_edited(self):
        # editingFinished also fires on plain focus loss; only a changed name needs a rebuild
        if self._candidate is not None and (
            self._library_combo.currentText().strip() != self._last_requested_library
        ):
            self._request_rebuild()

    def _request_rebuild(self):
        """Ask for a plan for the current choices; at most one build runs and the latest request wins.

        A pending text-edit debounce is superseded: this request already carries those edits.
        """
        self._debounce.stop()
        self._dirty = False
        if self._candidate is None or self._closing:
            return
        self._gen += 1
        options = self._snapshot_options()
        self._last_requested_library = options.library
        if self._building is not None:
            self._queued = options
        else:
            self._start_build(options)
        self._update_install_state()

    def _start_build(self, options: InstallOptions):
        core, candidate, layout, tools = self._core, self._candidate, self._repo_layout, self._tools
        worker = self._spawn(
            lambda progress: core.build_plan(candidate, options, layout, tools), tag=self._gen
        )
        worker.options = options
        self._building = worker
        worker.result.connect(lambda plan, w=worker: self._on_build_result(w, plan))
        worker.failed.connect(lambda text, w=worker: self._on_build_failed(w, text))
        worker.start()

    def _build_ended(self, worker: TaskWorker):
        """Common tail of a build result or failure: free the slot and run the queued request."""
        if self._building is worker:
            self._building = None
        if self._queued is not None and not self._closing:
            options, self._queued = self._queued, None
            self._start_build(options)

    def _on_build_result(self, worker: TaskWorker, plan: InstallPlan):
        if self._closing:
            if self._building is worker:
                self._building = None
            return
        if worker.tag == self._gen and not self.is_installing():
            self._plan = plan
            self._plan_gen = worker.tag
            self._plan_options = worker.options
            self._build_failed = False
            self._first_plan_seen = True
            self._preview.render(preview_sections(plan, self._candidate, worker.options))
            self._preview_stack.setCurrentWidget(self._preview)
            self._show_plan_in_form(plan)
        # else: a newer request exists; this result is stale and dropped untouched
        self._build_ended(worker)
        self._update_install_state()

    def _on_build_failed(self, worker: TaskWorker, text: str):
        if self._closing:
            if self._building is worker:
                self._building = None
            return
        self.issues_logged.emit(
            [Issue(Severity.ERROR, "import.step_failed", f"Import step failed: {text}")]
        )
        if worker.tag == self._gen:
            self._build_failed = True
        self._build_ended(worker)
        self._update_install_state()

    # -- install gating and status ----------------------------------------------

    def is_installing(self) -> bool:
        return self._install_worker is not None

    def _updating(self) -> bool:
        return self._building is not None or self._queued is not None or self._dirty

    def _update_install_state(self):
        if self.is_installing():
            return
        plan = self._plan
        current = plan is not None and self._plan_gen == self._gen
        ready = (
            current
            and not self._updating()
            and not self._build_failed
            and not plan.blocked
            and not plan.is_noop
        )
        self._install_btn.setText("Install Part")
        self._install_btn.setEnabled(bool(ready))
        # The choices wait for the first plan; a failed first build must not lock the user out
        self._left_scroll.setEnabled(self._first_plan_seen or self._build_failed)
        self._change_btn.setEnabled(True)
        prefix = f"{self._install_failure}  " if self._install_failure else ""
        self._strip.setText(prefix + self._status_text(plan, current))

    def _status_text(self, plan: InstallPlan | None, current: bool) -> str:
        if self._candidate is None:
            return ""
        if self._updating():
            return "Updating preview..."
        if self._build_failed:
            return "⚠ Install is blocked: Error: Preview could not be built - see the log"
        if not current:
            return "Updating preview..."
        if plan.blocked:
            reasons = [i.text for i in plan.issues if i.severity is Severity.ERROR]
            reasons += [
                f"Choose Overwrite, Rename or Skip for {c.kind} {c.name}"
                for c in plan.unresolved_conflicts
            ]
            return "⚠ Install is blocked: " + " · ".join(reasons)
        if plan.is_noop:
            return f"Nothing to install: this part is already in {plan.library}."
        counts = file_counts(plan, self._candidate, self._plan_options)
        return (
            f"✓ Ready to install: {counts.new} new, {counts.modified} modified, "
            f"{counts.unchanged} unchanged files"
        )

    # -- install ------------------------------------------------------------------

    def _on_install_clicked(self):
        if not self._install_btn.isEnabled() or self.is_installing() or self._plan is None:
            return
        plan = self._plan  # the rendered object, never a rebuilt copy (PREV-07)
        core, backup_root = self._core, self._backup_root
        self._install_failure = ""
        # self._plan cannot change while installing: the inputs are locked and a build result is
        # not accepted until the install ends (_on_build_result)
        worker = self._spawn(
            lambda progress: core.apply_plan(self._plan, backup_root=backup_root, progress=progress)
        )
        self._install_worker = worker
        self._left_scroll.setEnabled(False)
        self._change_btn.setEnabled(False)
        self._install_btn.setEnabled(False)
        self._install_btn.setText("Installing...")
        self._strip.setText("Installing...")
        worker.progress.connect(self._on_install_progress)
        worker.result.connect(lambda result, w=worker, p=plan: self._on_install_done(w, p, result))
        worker.failed.connect(lambda text, w=worker: self._on_install_failed(w, text))
        worker.start()

    def _on_install_progress(self, message: str, current: int, total: int):
        if self.is_installing():
            self._strip.setText(message)

    def _on_install_done(self, worker: TaskWorker, plan: InstallPlan, result: InstallResult):
        if self._install_worker is worker:
            self._install_worker = None
        self.issues_logged.emit(list(result.issues))
        if result.ok:
            self.result = result
            self._show_result(plan, result)
            self.installed.emit(result, plan)
            return
        errors = [i.text for i in result.issues if i.severity is Severity.ERROR]
        self._install_failure = "Install failed: " + " · ".join(errors) if errors else "Install failed."
        # Files on disk may have changed: rebuild so a retry cannot hit the stale-plan guard
        self._request_rebuild()

    def _on_install_failed(self, worker: TaskWorker, text: str):
        if self._install_worker is worker:
            self._install_worker = None
        issue = Issue(Severity.ERROR, "import.step_failed", f"Import step failed: {text}")
        self.issues_logged.emit([issue])
        self._install_failure = f"Install failed: {text}"
        self._request_rebuild()

    def _show_result(self, plan: InstallPlan, result: InstallResult):
        self._banner.setText(f"✓ Installed {plan.symbol_name} into {result.library}")
        self._result_list.clear()
        for path in result.touched:
            try:
                shown = Path(path).relative_to(self._repo_root).as_posix()
            except ValueError:
                shown = Path(path).as_posix()
            self._result_list.addItem(shown)
        self._stack.setCurrentWidget(self._result_page)
        self._close_btn.setAutoDefault(True)
        self._close_btn.setDefault(True)

    # -- Change... (D-02): back to the Start page, nothing is asked ------------------

    def _on_change(self):
        """Discard this package and every edit made to it; nothing has been written, so no question.

        A running build is waited for, then the package is closed (WR-04). _reset_edit_state bumps
        the generation, so a build result still queued for this package is dropped when it arrives.
        """
        if self.is_installing() or self._closing or self._open_worker is not None:
            return
        building = self._building
        if building is not None:
            building.wait()
        self._building = None
        self._discard_package()
        self._reset_edit_state()
        self.setWindowTitle("Import Part")
        self._package_label.clear()
        self._vendor_label.clear()
        self._hide_issue_box()
        self._set_reading(False)
        self._stack.setCurrentWidget(self._start_page)
        self._browse_btn.setFocus()

    # -- lifetime (WR-04) ---------------------------------------------------------

    def _discard_package(self):
        package, self._package = self._package, None
        if package is not None:
            package.close()

    def _shutdown(self):
        """Wait for every open and build worker, then close the package; idempotent."""
        self._closing = True
        self._debounce.stop()
        for worker in list(self._workers):
            worker.wait()
        for worker in list(self._workers):
            value = worker.value
            if isinstance(value, OpenOutcome):
                value.package.close()  # an open that finished while closing
        self._discard_package()

    def done(self, r: int):
        if self.is_installing():
            return
        self._shutdown()
        super().done(r)

    def closeEvent(self, event: QCloseEvent):
        if self.is_installing():
            event.ignore()
            return
        self._shutdown()
        super().closeEvent(event)
