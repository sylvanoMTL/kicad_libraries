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

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QListWidget, QProgressBar,
    QPushButton, QScrollArea, QSplitter, QStackedWidget, QVBoxLayout, QWidget,
)

from ..importer.applier import apply_plan
from ..importer.candidate import ImportCandidate
from ..importer.detect import detect_candidate
from ..importer.layout import RepoLayout, list_existing_libraries
from ..importer.package import Package, open_package
from ..importer.plan import InstallOptions, InstallPlan, InstallResult, ToolContext
from ..importer.planner import build_plan, detect_tools
from ..importer.preview import file_counts, preview_sections
from ..importer.suggest import LibrarySuggestion, suggest_library
from ..kicad_process import kicad_running
from ..models import Issue, Severity
from .preview_tree import PreviewTree

_SEVERITY_GLYPH = {Severity.ERROR: "✖", Severity.WARNING: "⚠"}


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
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(8)
        heading = QLabel("Choose a part package")
        font = heading.font()
        font.setBold(True)
        heading.setFont(font)
        lay.addWidget(heading)

        self._reading_label = QLabel("Reading package...")
        self._reading_bar = QProgressBar()
        self._reading_bar.setRange(0, 0)
        lay.addWidget(self._reading_label)
        lay.addWidget(self._reading_bar)

        self._browse_btn = QPushButton("Browse zip...")
        self._browse_btn.clicked.connect(self._on_browse)
        row = QHBoxLayout()
        row.addWidget(self._browse_btn)
        row.addStretch()
        lay.addLayout(row)

        self._start_issues = QLabel()
        self._start_issues.setTextFormat(Qt.TextFormat.PlainText)
        self._start_issues.setWordWrap(True)
        self._start_issues.hide()
        lay.addWidget(self._start_issues)
        lay.addStretch()

        self._set_reading(False)
        self._start_page = page
        self._stack.addWidget(page)

    def _build_edit_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        self._package_label = QLabel()
        lay.addWidget(self._package_label)

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
        left_lay.addWidget(self._heading("Target library"))
        self._library_combo = QComboBox()
        self._library_combo.setEditable(True)
        self._library_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._library_combo.setAccessibleName("Target library")
        # Not currentTextChanged: that fires on every keystroke of a typed name
        self._library_combo.textActivated.connect(self._on_library_activated)
        self._library_combo.lineEdit().editingFinished.connect(self._on_library_edited)
        left_lay.addWidget(self._library_combo)
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
        self._reading_label.setVisible(reading)
        self._reading_bar.setVisible(reading)
        self._browse_btn.setEnabled(not reading)

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open part package", "", "Zip packages (*.zip)"
        )
        if path:
            self.open_path(Path(path))

    def open_path(self, path: Path):
        """Open a zip or folder on a worker; the dialog owns the resulting Package."""
        if self._closing or self._open_worker is not None:
            return
        if self._building is not None:
            self._building.wait()  # WR-04: never close the package under a running build
        self._discard_package()
        self._reset_edit_state()
        self._start_issues.hide()
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
        self._show_start_issues([issue])

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
            self._discard_package()
            self._show_start_issues(issues)
            return
        self._candidate = candidate
        self._tools = outcome.tools
        self._suggestion = outcome.suggestion
        self._existing = outcome.existing
        self.setWindowTitle(f"Import Part - {package.source.name}")
        self._package_label.setText(f"Package: {package.source.name}")
        self._fill_library_combo()
        self._preview_stack.setCurrentWidget(self._building_page)
        self._stack.setCurrentWidget(self._edit_page)
        self._request_rebuild()

    def _show_start_issues(self, issues: list[Issue]):
        lines = [
            f"{_SEVERITY_GLYPH[i.severity]} {i.text}"
            for i in issues
            if i.severity in _SEVERITY_GLYPH
        ]
        if not lines:
            lines = ["No KiCad symbol or footprint was found in this package."]
        self._start_issues.setText("\n".join(lines))
        self._start_issues.show()
        self._set_reading(False)
        self._stack.setCurrentWidget(self._start_page)

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
        self._candidate = None
        self._suggestion = None
        self._tools = None
        self._queued = None
        self._plan = None
        self._plan_gen = -1
        self._plan_options = None
        self._build_failed = False
        self._install_failure = ""
        self._preview.render(())
        self._preview_stack.setCurrentWidget(self._building_page)
        self._update_install_state()

    def _snapshot_options(self) -> InstallOptions:
        candidate = self._candidate
        return InstallOptions(
            library=self._library_combo.currentText().strip(),
            symbol=candidate.symbols[0].name,
            footprints=tuple(f.name for f in candidate.footprints),
            model=candidate.models[0].filename if candidate.models else None,
        )

    def _on_library_activated(self, _text: str = ""):
        self._request_rebuild()

    def _on_library_edited(self):
        # editingFinished also fires on plain focus loss; only a changed name needs a rebuild
        if self._candidate is not None and (
            self._library_combo.currentText().strip() != self._last_requested_library
        ):
            self._request_rebuild()

    def _request_rebuild(self):
        """Ask for a plan for the current choices; at most one build runs and the latest request wins."""
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
            self._preview.render(preview_sections(plan, self._candidate, worker.options))
            self._preview_stack.setCurrentWidget(self._preview)
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
        return self._building is not None or self._queued is not None

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
        self._left_scroll.setEnabled(True)
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

    # -- lifetime (WR-04) ---------------------------------------------------------

    def _discard_package(self):
        package, self._package = self._package, None
        if package is not None:
            package.close()

    def _shutdown(self):
        """Wait for every open and build worker, then close the package; idempotent."""
        self._closing = True
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
