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

import functools
import html
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QStandardPaths, QThread, QTimer, Signal
from PySide6.QtGui import (
    QAction, QCloseEvent, QColor, QCursor, QFont, QGuiApplication, QKeyEvent, QKeySequence, QPalette, QResizeEvent,
    QShortcut, QShowEvent,
)
from PySide6.QtWidgets import (
    QAbstractItemView, QButtonGroup, QComboBox, QCompleter, QDialog, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QPlainTextEdit, QProgressBar,
    QPushButton, QRadioButton, QScrollArea, QSizePolicy, QSplitter, QStackedWidget, QStyle, QToolBar, QToolButton,
    QVBoxLayout, QWidget,
)

from ..importer.adapters.base import attach_models
from ..importer.applier import apply_plan
from ..importer.candidate import ImportCandidate
from ..importer.commit_gate import scan_result_for
from ..importer.commit_plan import CommitPlan, build_commit_plan
from ..importer.commit_step import (
    CommitOutcome, CommitProbe, SwitchOutcome, changed_diff, combined_view, pre_import_diff, probe_commit,
    recheck_commit, run_commit, switch_to_main,
)
from ..importer.content import ContentText, op_content, unchanged_content
from ..importer.detect import detect_candidate
from ..importer.downloads import age_text, newest_zip
from ..importer.footprint_index import build_index, rank, rank_with_pads
from ..importer.form import (
    FIELD_LABELS, FIELD_NAMES, TEXT_LABELS, TEXT_NAMES, UPDATING_REASON, FieldDefaults, FormStatus, FormValues,
    Reason, blocking_reasons, build_options, carry_resolutions, field_defaults, kind_label, library_badge,
    noop_text, ready_text,
)
from ..importer.layout import RepoLayout, list_symbol_libs
from ..importer.package import MAX_KICAD_TEXT_BYTES, MAX_KICAD_TEXT_NODES, Package, open_model_source, open_package
from ..importer.plan import Conflict, InstallOptions, InstallPlan, InstallResult, PartText, Resolution, ToolContext
from ..importer.planner import build_plan, detect_tools
from ..importer.preview import file_counts, preview_sections
from ..importer.siblings import SiblingIndex, own_index, pick, stock_index
from ..importer.stems import ATOMIC_PREFIX, allowed_stems, name_verdict
from ..importer.suggest import LibrarySuggestion, existing_libraries, suggest_library, suggestion_text
from ..importer.verify import footprint_pad_numbers
from ..kicad_files import footprint_name, parse_bytes
from ..kicad_process import kicad_running
from ..models import Issue, Severity
from ..settings import load_import_dir, save_import_dir
from .atomic_check_dialog import AtomicCheckDialog
from .commit_panel import CommitPanel
from .conflict_row import ConflictRow
from .content_view import ContentViewDialog
from .import_result import ElidedLabel, ImportResultView
from .preview_tree import PreviewTree
from .theme import (
    AMBER, AMBER_TINT, BORDER, DISPLAY_PT, ERROR, ERROR_TINT, FIELD_FRAME_QSS, HEADING_PT, LINK, MONO_FAMILY,
    MONO_PT, MUTED, PRIMARY_BUTTON_QSS, SP_LG, SP_MD, SP_SM, SP_XL, SP_XS, SUCCESS, SURFACE,
)

_SEVERITY_GLYPH = {Severity.ERROR: "✖", Severity.WARNING: "⚠"}
_SEVERITY_COLOR = {Severity.ERROR: ERROR, Severity.WARNING: AMBER}
_ISSUE_LIST_MAX_HEIGHT = 160
_NOTHING_FOUND = "No KiCad symbol or footprint was found in this package."
_CLOSING_REFUSED = "Pick another file."
_CLOSING_EMPTY = "Check that you downloaded the KiCad format, then pick another file."
_NO_MODEL = "No model"
ADD_MODEL_TEXT = "Add 3D model..."  # public: the help page names the button with this text
REMOVE_MODEL_TEXT = "Remove"  # public: the help page names the button with this text
CHANGE_PACKAGE_TEXT = "Choose another package..."  # public: the help page names the button with this text
HELP_ACTION_TEXT = "Help"  # public: the help page names the action with this text
_HELP_TIP = "Open the User Guide on the Importing Parts page (F1). This window stays open."
_HELP_TOPIC = "importing"  # the User Guide's key for the Importing Parts page
_CHANGE_PACKAGE_TIP = (
    "Close this package and pick another package. Your edits to it are dropped; nothing has been written."
)
# Mirror the atomic strip sentences in importer/form.py: every Atomic_ library needs all three fields
_REQUIRED_HINTS = {
    "datasheet": "Required - enter a Datasheet link",
    "description": "Required - type a Description",
    "manufacturer": "Required - enter the Manufacturer",
}
_REGENERATE = "Regenerate"
_TEXT_TIPS = {
    "keywords": "Words KiCad's symbol chooser searches. The vendor's words come first, then the generated ones.",
    "fp_description": "The sentence KiCad shows for the footprint. It replaces the vendor's.",
    "fp_tags": "Words KiCad's footprint chooser searches. The vendor's tags come first, then the generated ones.",
}
_VALUE_TIP = "Value follows the MPN"
VENDOR_FOOTPRINT_TEXT = "Install the vendor footprint into Atomic_Footprints"  # public: the help page names the choice
OFFICIAL_FOOTPRINT_TEXT = "Use an official KiCad footprint"  # public: the help page names the choice
_OFFICIAL_HINT = "KiCad's own footprints are never changed"
_OFFICIAL_MODEL_NOTE = "KiCad's own 3D model is used"
_OFFICIAL_UNAVAILABLE = "KiCad's footprints were not found"
_OFFICIAL_READING = "Reading KiCad's footprints..."
_OFFICIAL_PLACEHOLDER = "Type to filter KiCad's footprints"
_OFFICIAL_POPUP_WIDTH = 420
_NO_FOOTPRINT_FIELD = "(none)"
_LIBRARY_PLACEHOLDER = "Pick a library, or type Atomic_ and a KiCad library name"
_BUSY_DELAY_MS = 150  # the busy strip shows only if a rebuild takes longer than this (no flicker)
FINISHING_TEXT = "Finishing the preview..."  # public: the tests and the help page name the strip with this text
SLOW_CLI_TEXT = "The KiCad command-line tool is slow to respond (it gives up after 60 s)"  # public, same reason
_SLOW_NOTE_MS = 10_000  # the Finishing strip adds the slow note after this long (D-07)
_FAILURE_LINES = 6  # reason lines shown in the failure banner before its body scrolls
_FAILED_RESTORED = "Install failed. Every file was restored."
_FAILED_NOT_RESTORED = "Install failed and some files could not be restored."
_FAILED_PLAIN = "Install failed."
_FAILED_RETRY = "Fix the problem and click Install Part again."
# Last line of the blocked strip's tooltip; public so the tests and the UI spec use one string (G-07-8)
STRIP_LINK_HINT = (
    "Click a reason to jump to the control that fixes it. A reason about the whole plan jumps to the preview."
)

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


def incoming_op(plan: InstallPlan, conflict: Conflict):
    """The planned write that carries the incoming side of a conflict, or None when the plan has none.

    A plan holds this op only once the conflict is settled with Overwrite (RESEARCH Pitfall 2): the
    footprint op named after the conflict, the model op, or the symbol library op (whole file).
    """
    if conflict.kind == "symbol":
        return next((op for op in plan.ops if op.kind == "symbol_lib"), None)
    if conflict.kind == "footprint":
        # An overwrite writes the spelling already on disk while the conflict keeps the vendor name (D-14)
        wanted = f"{conflict.name}.kicad_mod".casefold()
        return next((op for op in plan.ops if op.kind == "footprint" and op.path.name.casefold() == wanted), None)
    if conflict.kind == "model":
        return next((op for op in plan.ops if op.kind == "model" and op.path.name == plan.model_file), None)
    return None


def _vendor_pads(path: Path | None) -> set[str]:
    """The pad numbers of a staged vendor footprint, read under the usual size and node caps; none when unreadable."""
    if path is None:
        return set()
    try:
        with open(path, "rb") as handle:
            data = handle.read(MAX_KICAD_TEXT_BYTES + 1)
        if len(data) > MAX_KICAD_TEXT_BYTES:
            return set()
        loaded = parse_bytes(data, path.name, max_nodes=MAX_KICAD_TEXT_NODES)
    except (OSError, MemoryError):
        return set()
    ref = None if isinstance(loaded, Issue) else footprint_name(loaded.root)
    return footprint_pad_numbers(ref.node) if ref is not None else set()


def _sibling_links(stock: SiblingIndex | None, part: str) -> dict[str, int]:
    """Each footprint that a stock sibling of the part links, with the weight 1 (the vote's own prefix step decides who a sibling is).

    A footprint counts once however many siblings link it: on KiCad 10 sixty-three of the seventy-five CSD siblings
    link TDSON-8-1, and a count would let that popular package outrank the one whose name matches the vendor
    package code and whose pads fit.
    """
    if stock is None or not part:
        return {}
    prefix = pick(stock, part).prefix
    return {entry.footprint: 1 for entry in stock.matches(prefix) if entry.footprint} if prefix else {}


def official_candidates(
    footprint_index: Callable,
    folder: Path,
    *,
    package_code: str,
    vendor_path: Path | None,
    stock: SiblingIndex | None,
    part: str,
    progress: Callable | None = None,
) -> list[str]:
    """Every footprint link of KiCad's folder for the picker: the best matches first, then the rest in name order (D-16).

    The best matches are ranked by the vendor package code and the links of the part's siblings, then raised when
    their pads fit the vendor footprint's pads. Only KiCad's own folder is listed, never a library of the repo.
    """
    index = footprint_index(folder, progress)
    ranked = rank(index, package_code=package_code, linked=_sibling_links(stock, part))
    ranked = rank_with_pads(index, ranked, _vendor_pads(vendor_path))
    best = [item.link for item in ranked]
    listed = set(best)
    rest = sorted((link for link in index.links() if link not in listed), key=lambda link: (link.casefold(), link))
    return [*best, *rest]


class _OfferLabel(QLabel):
    """One-line plain-text label that elides the middle of a name to fit its width (UI E3/overflow)."""

    def __init__(self, parent=None, *, expanding: bool = False):
        super().__init__(parent)
        self.setTextFormat(Qt.TextFormat.PlainText)
        # Ignored suits a label that sits in a stretching box layout. A form field must ask for the
        # room (Expanding) yet still shrink to nothing, so a long name never widens the pane.
        self._expanding = expanding
        horizontal = QSizePolicy.Policy.Expanding if expanding else QSizePolicy.Policy.Ignored
        self.setSizePolicy(horizontal, QSizePolicy.Policy.Preferred)
        self._parts: tuple[str, str, str] | None = None

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        return QSize(0, hint.height()) if self._expanding else hint

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
    open_model_source: Callable = open_model_source
    attach_models: Callable = attach_models
    detect_candidate: Callable = detect_candidate
    detect_tools: Callable = detect_tools
    build_plan: Callable = build_plan
    apply_plan: Callable = apply_plan
    kicad_running: Callable = kicad_running
    list_symbol_libs: Callable = list_symbol_libs
    own_index: Callable = own_index
    stock_index: Callable = stock_index
    suggest_library: Callable = suggest_library
    downloads_dir: Callable = default_downloads_dir
    op_content: Callable = op_content
    unchanged_content: Callable = unchanged_content
    probe_commit: Callable = probe_commit
    recheck_commit: Callable = recheck_commit
    run_commit: Callable = run_commit
    switch_to_main: Callable = switch_to_main
    pre_import_diff: Callable = pre_import_diff
    changed_diff: Callable = changed_diff
    footprint_index: Callable = build_index


@dataclass(frozen=True)
class OpenOutcome:
    """What the open worker hands to the GUI thread; the dialog owns the package from then on."""

    package: Package
    candidate: ImportCandidate | None
    detect_issues: tuple
    tools: ToolContext | None
    suggestion: LibrarySuggestion | None
    existing: tuple
    # KiCad's stock symbols, kept so the official footprint list can count the links of the part's siblings
    stock: SiblingIndex | None = None


@dataclass(frozen=True)
class ModelOutcome:
    """What the Add 3D model... worker hands to the GUI thread; the dialog owns the model package from then on."""

    package: Package
    candidate: ImportCandidate | None
    issues: tuple
    session: int


@dataclass(frozen=True)
class RejectedModel:
    """An unusable 3D model source the dialog holds so that it blocks Install (G-07-5).

    Only the source's file name and its first ERROR are kept; the rejected package itself is already closed.
    """

    source: str
    issue: Issue


class ImportDialog(QDialog):
    """Window-modal import dialog. Emits installed(InstallResult, InstallPlan) after a successful install."""

    installed = Signal(object, object)
    issues_logged = Signal(object)  # list[Issue]; the main window routes them to the log
    leave_cancelled = Signal()  # Cancel ended a pending Change..., open or close
    atomic_fixes_applied = Signal(object)  # list[Issue]; fixes written from the commit panel's check dialog

    def __init__(
        self,
        repo_root: Path,
        layout: RepoLayout,
        *,
        kicad_fp_dir: Path | None = None,
        package_path: Path | None = None,
        core: ImportCore | None = None,
        backup_root: Path | None = None,
        atomic_backup_root: Path | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._repo_root = Path(repo_root)
        self._repo_layout = layout
        self._kicad_fp_dir = kicad_fp_dir
        self._core = core or ImportCore()
        self._backup_root = backup_root
        # Where the Check Atomic Parts dialog keeps the backups of the fixes it applies; None = its own default
        self._atomic_backup_root = atomic_backup_root
        self._atomic_dialog: AtomicCheckDialog | None = None
        self._help_dialog: QDialog | None = None  # the User Guide window this import window opened

        # Public: the successful InstallResult. Shadows QDialog.result() on this instance (by design).
        self.result: InstallResult | None = None
        # Public: the plan that produced result (Phase 6 reads both to commit the installed part)
        self.result_plan: InstallPlan | None = None

        self._package: Package | None = None
        self._candidate: ImportCandidate | None = None
        self._tools: ToolContext | None = None
        self._suggestion: LibrarySuggestion | None = None
        self._existing: tuple = ()
        self._note_for = ""  # the corrected name the spelling note is about; "" when the note is hidden
        self._typed = ""  # the library text as the owner typed it, until editing ends

        # Rebuild coordinator (PREV-07): serialised builds, the latest request wins. A one-off build
        # (the incoming side of a conflict, D-08) shares the queue: never two build_plan calls at once.
        self._gen = 0
        self._building: TaskWorker | None = None
        self._queued: InstallOptions | None = None
        self._oneoff: TaskWorker | None = None
        self._oneoff_jobs: list[tuple[int, InstallOptions, Callable]] = []
        self._session = 0  # counts the opened packages; a one-off or content result of an older one is dropped
        self._content_views: list[ContentViewDialog] = []
        self._plan: InstallPlan | None = None
        self._plan_gen = -1
        self._plan_options: InstallOptions | None = None
        self._build_failed = False

        # Left-pane choices (plan 05-07). The item controls exist only for the package that is open.
        self._symbol_combo: QComboBox | None = None
        self._symbol_label: _OfferLabel | None = None
        self._fp_combo: QComboBox | None = None
        self._fp_label: _OfferLabel | None = None
        self._model_combo: QComboBox | None = None
        self._model_label: _OfferLabel | None = None
        # Add 3D model... (G-07-2): second-source packages stay open until Change..., a new open or close,
        # because an attached model's file is read again by every rebuild and by apply_plan (WR-04)
        self._model_packages: list[Package] = []
        self._model_worker: TaskWorker | None = None
        self._add_model_btn: QPushButton | None = None
        self._model_slot: QVBoxLayout | None = None
        self._model_note: QLabel | None = None
        # G-07-5: an unusable model source blocks Install until Remove (or, in 07-13, a usable attach)
        self._model_rejection: RejectedModel | None = None
        self._remove_model_btn: QPushButton | None = None
        self._extends_note: QLabel | None = None
        self._linked_fp: str | None = None  # vendor name of the linked footprint
        self._defaults = FieldDefaults()
        self._edited: set[str] = set()  # field names the user changed; only these reach the planner
        # The generated texts (keywords, footprint description and tags) the user typed over; the others follow the plan
        self._texts_edited: set[str] = set()
        self._fp_name_edited = False
        # Conflict choices by Conflict.key (D-14a): pruned to the keys of each accepted plan
        self._resolutions: dict[str, Resolution] = {}
        self._conflict_rows: dict[str, ConflictRow] = {}
        # Blocked-field highlight (D-09): a reason's target names the control to focus and its amber frame.
        # Keys: "library", "footprint_name", "footprints", the field names, and per conflict row
        # "conflict:{key}" (the Overwrite button) and "rename:{key}" (the rename field), removed with the row.
        self._reason_targets: dict[str, QWidget] = {}
        self._field_frames: dict[str, QFrame] = {}
        self._strip_reasons: list[Reason] = []  # the reasons the strip links point at
        self._first_plan_seen = False
        self._syncing = False  # True while the dialog sets control values itself
        self._dirty = False  # a text edit waits for its debounce, so the plan on screen is not current
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)  # D-06: the quiet period after the last keystroke, in ms
        self._debounce.timeout.connect(self._on_debounce)
        # The Updating indicator (D-06): the label shows at once, the busy strip only after a delay
        self._updating_shown = False
        self._busy_timer = QTimer(self)
        self._busy_timer.setSingleShot(True)
        self._busy_timer.setInterval(_BUSY_DELAY_MS)
        self._busy_timer.timeout.connect(self._on_busy_timeout)

        # The official footprint choice (D-16): the stock symbols for the sibling count, the picker's list (built once
        # per package on the first switch) and the worker that builds it
        self._stock: SiblingIndex | None = None
        self._official_links: list[str] | None = None
        self._official_worker: TaskWorker | None = None

        self._workers: list[TaskWorker] = []
        self._open_worker: TaskWorker | None = None
        self._install_worker: TaskWorker | None = None
        # The Phase 6 commit step: one panel per installed part and at most one git worker at a time
        self._commit_panel: CommitPanel | None = None
        self._commit_plan: CommitPlan | None = None
        self._commit_probe: CommitProbe | None = None
        self._git_worker: TaskWorker | None = None  # Switch to main or Commit only; the probe never locks Close (IN-02)
        self._probe_worker: TaskWorker | None = None
        self._probe_cancels: list[threading.Event] = []
        self._probe_cancelled_by_close = False  # a close stopped the probe; Cancel of that close probes again
        self._close_had_focus = False  # Close held the focus when a git job disabled it
        self._not_committed_logged = False  # the D-02 line is logged once per dialog
        self._closing = False
        # The Finishing state (D-06): Change... or an open asked for while a build runs waits here, with the
        # window live, and runs from the last relevant worker's finished handler (_try_finish)
        self._finishing = False
        self._pending: Callable[[], None] | None = None
        self._pending_kind: str | None = None  # "change", "open" or "close"
        self._slow_timer = QTimer(self)
        self._slow_timer.setSingleShot(True)
        self._slow_timer.timeout.connect(self._on_slow_timeout)

        self.setWindowTitle("Import Part")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(1100, 720)
        self.setMinimumSize(900, 600)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(8)
        self._stack = QStackedWidget()
        self._build_toolbar(outer)
        outer.addWidget(self._stack)
        self._build_finish_strip(outer)
        self._build_start_page()
        self._build_edit_page()
        self._build_result_page()
        self._stack.setCurrentWidget(self._start_page)

        # Enter inside a line edit must never install: no button is a default or auto-default (D-10).
        # Ctrl+Return is the keyboard way to Install, and only when Install is enabled (T-05-29).
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
            button.setDefault(False)
        self._install_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self._install_shortcut.activated.connect(self._on_install_shortcut)

        self._update_install_state()
        if package_path is not None:
            QTimer.singleShot(0, lambda: self.open_path(Path(package_path)))

    # -- pages ------------------------------------------------------------------

    def _build_toolbar(self, outer: QVBoxLayout):
        """The toolbar above the page stack, shared by every page; Help is its only action (G-12-9)."""
        toolbar = QToolBar()
        toolbar.setAccessibleName("Import window toolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        # F1 is this action's own shortcut: a second binding of one key in a window makes both ambiguous
        action = QAction(HELP_ACTION_TEXT, self)
        action.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton))
        action.setToolTip(_HELP_TIP)
        action.setShortcut(QKeySequence("F1"))
        action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        action.triggered.connect(self._on_help)
        toolbar.addAction(action)
        self._toolbar = toolbar
        self._help_action = action
        outer.addWidget(toolbar)

    def _on_help(self):
        """Show the User Guide on Importing Parts, non-modal, and reuse the one window (G-12-9)."""
        if self._closing:
            return
        # help_dialog imports this module's texts, so a module-level import would be circular
        from .help_dialog import HelpDialog

        if self._help_dialog is None:
            # A child of this window-modal dialog is not blocked by it; a window parented to the main window would be
            self._help_dialog = HelpDialog(topic=_HELP_TOPIC, parent=self)
        else:
            self._help_dialog.show_topic(_HELP_TOPIC)
        self._help_dialog.show()
        self._help_dialog.raise_()
        self._help_dialog.activateWindow()

    def _build_finish_strip(self, outer: QVBoxLayout):
        """The Finishing strip (D-06, D-07), beside the stack so Cancel stays enabled while the stack is off."""
        strip = QFrame()
        strip.setObjectName("finishStrip")
        strip.setStyleSheet(f"QFrame#finishStrip {{ background-color: {SURFACE}; border: 1px solid {BORDER}; }}")
        row = QHBoxLayout(strip)
        row.setContentsMargins(SP_SM, SP_SM, SP_SM, SP_SM)
        row.setSpacing(SP_SM)
        self._finish_label = QLabel(FINISHING_TEXT)
        self._finish_label.setTextFormat(Qt.TextFormat.PlainText)
        row.addWidget(self._finish_label)
        self._finish_slow = QLabel(SLOW_CLI_TEXT)
        self._finish_slow.setTextFormat(Qt.TextFormat.PlainText)
        self._finish_slow.setStyleSheet(f"color: {MUTED};")
        self._finish_slow.hide()
        row.addWidget(self._finish_slow)
        row.addStretch(1)
        self._finish_cancel = QPushButton("Cancel")
        self._finish_cancel.clicked.connect(self._on_finish_cancel)
        row.addWidget(self._finish_cancel)
        strip.hide()
        self._finish_strip = strip
        outer.addWidget(strip)

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

        # The failure banner of a rolled-back install sits above everything else (D-15)
        self._build_failure_banner(lay)

        # Package header: name (bold), vendor (muted), Change... on the right, over a 1px line.
        # In its own widget so an install can lock the whole row (D-10).
        self._header_row = QWidget()
        header = QHBoxLayout(self._header_row)
        header.setContentsMargins(0, 0, 0, 0)
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
        self._change_btn = QPushButton(CHANGE_PACKAGE_TEXT)
        self._change_btn.setToolTip(_CHANGE_PACKAGE_TIP)
        self._change_btn.clicked.connect(self._on_change)
        header.addWidget(self._change_btn)
        lay.addWidget(self._header_row)
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
        self._build_library_section(left_lay)
        left_lay.addSpacing(SP_MD)
        self._build_footprint_section(left_lay)
        left_lay.addSpacing(SP_MD)
        self._build_fields_section(left_lay)
        left_lay.addSpacing(SP_MD)
        self._build_conflicts_section(left_lay)
        left_lay.addStretch()
        self._left_scroll.setWidget(left)
        self._left_scroll.setMinimumWidth(380)
        splitter.addWidget(self._left_scroll)

        # Right: the live preview
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(8)
        title_row = QHBoxLayout()
        title_row.setSpacing(SP_SM)
        title_row.addWidget(self._heading("Preview"))
        self._updating_label = QLabel("Updating...")
        self._updating_label.setTextFormat(Qt.TextFormat.PlainText)
        self._updating_label.setStyleSheet(f"color: {AMBER};")
        self._updating_label.hide()
        title_row.addWidget(self._updating_label)
        title_row.addStretch(1)
        right_lay.addLayout(title_row)
        # A 4 px indeterminate strip that keeps its room when hidden, so the tree does not jump
        self._busy_bar = QProgressBar()
        self._busy_bar.setRange(0, 0)
        self._busy_bar.setTextVisible(False)
        self._busy_bar.setFixedHeight(4)
        self._busy_bar.setAccessibleName("Preview is updating")
        policy = self._busy_bar.sizePolicy()
        policy.setRetainSizeWhenHidden(True)
        self._busy_bar.setSizePolicy(policy)
        self._busy_bar.hide()
        right_lay.addWidget(self._busy_bar)
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
        self._preview.row_activated.connect(self._on_preview_row_activated)
        self._preview_stack.addWidget(building)
        self._preview_stack.addWidget(self._preview)
        right_lay.addWidget(self._preview_stack, stretch=1)
        right.setMinimumWidth(400)
        splitter.addWidget(right)
        splitter.setSizes([440, 660])
        lay.addWidget(splitter, stretch=1)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        # The strip is rich text only while it lists blocking reasons (every string escaped, internal
        # reason: links only); a status line is plain text. 8 px padding, at most 3 lines (D-09).
        self._strip = QLabel()
        self._strip.setObjectName("installStrip")
        self._strip.setTextFormat(Qt.TextFormat.PlainText)
        self._strip.setWordWrap(True)
        self._strip.setOpenExternalLinks(False)
        self._strip.setTextInteractionFlags(
            Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.LinksAccessibleByKeyboard
        )
        self._strip.setContentsMargins(SP_SM, SP_SM, SP_SM, SP_SM)
        self._strip.setMaximumHeight(3 * self._strip.fontMetrics().lineSpacing() + 2 * SP_SM)
        self._strip.setAccessibleName("Install status")
        palette = self._strip.palette()
        palette.setColor(QPalette.ColorRole.Link, QColor(LINK))
        self._strip.setPalette(palette)
        self._strip.linkActivated.connect(self._on_reason_link)
        bottom.addWidget(self._strip, stretch=1)
        # While installing the strip is replaced by the step text and a determinate bar (D-10)
        self._install_row = QWidget()
        install_lay = QHBoxLayout(self._install_row)
        install_lay.setContentsMargins(0, 0, 0, 0)
        install_lay.setSpacing(SP_SM)
        self._install_step = ElidedLabel()
        self._install_step.setStyleSheet(f"color: {MUTED};")
        self._install_step.setAccessibleName("Install step")
        install_lay.addWidget(self._install_step, stretch=1)
        self._install_bar = QProgressBar()
        self._install_bar.setRange(0, 100)
        self._install_bar.setTextVisible(False)
        self._install_bar.setFixedSize(240, 16)
        self._install_bar.setAccessibleName("Install progress")
        install_lay.addWidget(self._install_bar)
        self._install_row.hide()
        bottom.addWidget(self._install_row, stretch=1)
        self._install_btn = QPushButton("Install Part")
        self._install_btn.setStyleSheet(PRIMARY_BUTTON_QSS)  # the main action of each view looks the same (D-19)
        self._install_btn.setMinimumWidth(112)
        self._install_btn.clicked.connect(self._on_install_clicked)
        bottom.addWidget(self._install_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        # Cancel closes the window through the same path as the window's X, so Finishing and the
        # install/commit refusal in done() are reused (G-12-6)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setToolTip("Close without installing. Nothing is written.")
        self._cancel_btn.clicked.connect(self.reject)
        bottom.addWidget(self._cancel_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(bottom)

        self._edit_page = page
        self._stack.addWidget(page)

    def _build_failure_banner(self, page_layout: QVBoxLayout):
        """The banner of a failed install (D-15): tinted, with a 2 px left bar, a title, the reasons and a dismiss button.

        The reasons are plain text in a read-only editor that is at most six lines tall and scrolls beyond that.
        """
        banner = QFrame()
        banner.setObjectName("failureBanner")
        banner.setStyleSheet(
            f"QFrame#failureBanner {{ background-color: {ERROR_TINT}; border-left: 2px solid {ERROR}; }}"
        )
        outer = QHBoxLayout(banner)
        outer.setContentsMargins(SP_MD, SP_SM, SP_SM, SP_SM)
        outer.setSpacing(SP_SM)
        column = QVBoxLayout()
        column.setSpacing(SP_XS)
        title = QLabel()
        title.setTextFormat(Qt.TextFormat.PlainText)
        title.setWordWrap(True)
        font = title.font()
        font.setPointSize(DISPLAY_PT)
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet(f"color: {ERROR};")
        column.addWidget(title)
        body = QPlainTextEdit()
        body.setReadOnly(True)
        body.setFrameShape(QFrame.Shape.NoFrame)
        body.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        body.setStyleSheet("QPlainTextEdit { background: transparent; }")
        body.setAccessibleName("Install failure reasons")
        column.addWidget(body)
        outer.addLayout(column, stretch=1)
        dismiss = QToolButton()
        dismiss.setText("✕")
        dismiss.setAccessibleName("Dismiss failure message")
        dismiss.setToolTip("Dismiss")
        dismiss.setAutoRaise(True)
        dismiss.clicked.connect(banner.hide)
        outer.addWidget(dismiss, alignment=Qt.AlignmentFlag.AlignTop)
        banner.hide()
        page_layout.addWidget(banner)
        self._failure_banner, self._failure_title, self._failure_body = banner, title, body

    def _show_failure(self, issues, backup_dir: Path | None, *, title: str | None = None):
        """Show why an install failed: every ERROR text on its own line, then the closing line (D-15).

        A rollback that could not restore a file changes the title and points at the backup folder.
        """
        restore_failed = any(issue.code == "install.rollback_failed" for issue in issues)
        if title is None:
            title = _FAILED_NOT_RESTORED if restore_failed else _FAILED_RESTORED
        closing = _FAILED_RETRY
        if restore_failed and backup_dir is not None:
            closing = f"The original files are in {backup_dir}."
        lines = [issue.text for issue in issues if issue.severity is Severity.ERROR]
        self._failure_title.setText(title)
        self._failure_body.setPlainText("\n".join([*lines, closing]))
        self._failure_banner.show()
        self._edit_page.layout().activate()
        self._fit_failure_body()
        self._failure_body.verticalScrollBar().setValue(0)
        QTimer.singleShot(0, self._fit_failure_body)  # once the banner has its real width

    def _fit_failure_body(self):
        """Size the reasons box to its wrapped text, at most _FAILURE_LINES lines; beyond that it scrolls."""
        body = self._failure_body
        if self._closing or not self._failure_banner.isVisible():
            return
        metrics = body.fontMetrics()
        margins = 2 * body.frameWidth() + 2 * int(body.document().documentMargin())
        width = max(body.width() - margins, 40)
        flags = Qt.TextFlag.TextWordWrap.value
        lines = 0
        for part in body.toPlainText().split("\n"):
            height = metrics.boundingRect(0, 0, width, 100000, flags, part or " ").height()
            lines += max(1, round(height / metrics.lineSpacing()))
        body.setFixedHeight(min(lines, _FAILURE_LINES) * metrics.lineSpacing() + margins)

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._fit_failure_body()

    def _build_result_page(self):
        """The Result view replaces the Edit page in place after a successful install (D-15)."""
        view = ImportResultView()
        view.close_button.clicked.connect(self.accept)
        view.file_activated.connect(self._on_written_file_activated)
        self._result_view = view
        self._result_page = view
        self._stack.addWidget(view)

    @staticmethod
    def _heading(text: str) -> QLabel:
        label = QLabel(text)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        return label

    def _framed(self, widget: QWidget, key: str) -> QFrame:
        """Wrap a blockable control in a QFrame#fieldFrame and register it under a reason target (D-09).

        A border stylesheet on a QLineEdit or QComboBox itself would drop the native look, so the amber
        border sits on the frame. The frame reserves its 2 px border at all times (transparent until
        the "blocked" property is set), so the layout does not move when the highlight appears.
        """
        frame = QFrame()
        frame.setObjectName("fieldFrame")
        frame.setStyleSheet(FIELD_FRAME_QSS)
        frame.setProperty("blocked", False)
        frame_lay = QVBoxLayout(frame)
        frame_lay.setContentsMargins(0, 0, 0, 0)
        frame_lay.setSpacing(0)
        frame_lay.addWidget(widget)
        self._field_frames[key] = frame
        self._reason_targets[key] = widget
        return frame

    @staticmethod
    def _restore_button(accessible: str) -> QToolButton:
        """The 24x24 glyph button that puts a default back; its tooltip is set when the default is known."""
        button = QToolButton()
        button.setText("↺")
        button.setFixedSize(24, 24)
        button.setAccessibleName(accessible)
        button.setEnabled(False)
        return button

    @staticmethod
    def _aligned_row(widget: QWidget) -> QWidget:
        """Wrap a widget so it ends where a line edit followed by a restore button ends."""
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(widget, 1)
        lay.addSpacing(24 + SP_XS)
        return row

    def _build_library_section(self, left_lay: QVBoxLayout):
        """The editable library combo with its existing/new badge and the spelling note (D-05, D-11, D-12)."""
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        # Typing filters the list by substring, ignoring case. The popup only offers names; the typed text
        # stays as typed until editing finishes, when a wrong letter case is corrected (D-11)
        completer = QCompleter(combo.model(), combo)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(12)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        combo.setAccessibleName("Target library")
        # Picking from the list rebuilds at once; typing waits for the quiet period (D-06). Not
        # currentTextChanged for the rebuild: that fires on every keystroke of a typed name. A pick from
        # the completer popup is connected as well, because the combo may not report it (RESEARCH A10)
        combo.textActivated.connect(self._on_library_activated)
        completer.activated[str].connect(self._on_library_activated)
        line = combo.lineEdit()
        line.setPlaceholderText(_LIBRARY_PLACEHOLDER)
        line.textEdited.connect(self._on_library_text_edited)
        line.textChanged.connect(self._refresh_library_labels)
        line.editingFinished.connect(self._on_library_editing_finished)
        self._library_combo = combo

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SP_SM)
        row.addWidget(self._framed(combo, "library"), 1)
        self._library_badge = QLabel()
        self._library_badge.setTextFormat(Qt.TextFormat.PlainText)
        # Wraps at its spaces when the pane is narrow, so the combo keeps room and the badge is never cut
        self._library_badge.setWordWrap(True)
        self._library_badge.setAccessibleName("Library status")
        self._library_badge.hide()
        row.addWidget(self._library_badge)
        left_lay.addLayout(row)

        # Plain text under the field: "Spelling corrected to <name>" (D-11)
        self._library_note = QLabel()
        self._library_note.setTextFormat(Qt.TextFormat.PlainText)
        self._library_note.setWordWrap(True)
        self._library_note.setStyleSheet(f"color: {MUTED};")
        self._library_note.setAccessibleName("Library note")
        self._library_note.hide()
        left_lay.addWidget(self._library_note)

    def _build_footprint_section(self, left_lay: QVBoxLayout):
        """The footprint choice (D-16) and name (D-14, PREV-02): the name is pre-filled with the linked footprint's sanitised vendor name."""
        left_lay.addWidget(self._heading("Footprint"))
        self._build_destination_choice(left_lay)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        row = QWidget()
        row_lay = QHBoxLayout(row)
        row_lay.setContentsMargins(0, 0, 0, 0)
        row_lay.setSpacing(SP_XS)
        self._fp_name_edit = QLineEdit()
        self._fp_name_edit.setAccessibleName("Footprint name")
        self._fp_name_edit.setMinimumHeight(28)
        self._fp_name_edit.textEdited.connect(self._on_fp_name_edited)
        row_lay.addWidget(self._framed(self._fp_name_edit, "footprint_name"), 1)
        self._fp_name_restore = self._restore_button("Restore default footprint name")
        self._fp_name_restore.clicked.connect(self._on_fp_name_restore)
        row_lay.addWidget(self._fp_name_restore)
        form.addRow("Name", row)
        self._fp_name_hint = QLabel()
        self._fp_name_hint.setTextFormat(Qt.TextFormat.PlainText)
        self._fp_name_hint.setWordWrap(True)
        self._fp_name_hint.setStyleSheet(f"color: {MUTED};")
        self._fp_name_hint.hide()
        form.addRow(self._fp_name_hint)
        left_lay.addLayout(form)

    def _build_destination_choice(self, left_lay: QVBoxLayout):
        """Two radio buttons (vendor footprint or an official KiCad one) and, for the official one, the filterable picker."""
        self._fp_vendor_radio = QRadioButton(VENDOR_FOOTPRINT_TEXT)
        self._fp_official_radio = QRadioButton(OFFICIAL_FOOTPRINT_TEXT)
        self._fp_vendor_radio.setChecked(True)
        self._fp_target_group = QButtonGroup(self)
        self._fp_target_group.addButton(self._fp_vendor_radio)
        self._fp_target_group.addButton(self._fp_official_radio)
        for radio in (self._fp_vendor_radio, self._fp_official_radio):
            # A long label shrinks with the pane instead of widening it
            radio.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            left_lay.addWidget(radio)
        self._fp_official_radio.toggled.connect(self._on_fp_target_toggled)
        # Why the official choice is off (no KiCad install found)
        self._official_note = QLabel()
        self._official_note.setTextFormat(Qt.TextFormat.PlainText)
        self._official_note.setWordWrap(True)
        self._official_note.setStyleSheet(f"color: {MUTED};")
        self._official_note.hide()
        left_lay.addWidget(self._official_note)

        box = QWidget()
        box_lay = QVBoxLayout(box)
        box_lay.setContentsMargins(0, 0, 0, 0)
        box_lay.setSpacing(4)
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        # Typing filters KiCad's footprints by substring, ignoring case; a pick rebuilds at once, typing waits
        completer = QCompleter(combo.model(), combo)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        combo.setCompleter(completer)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(12)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        combo.setAccessibleName("Official footprint")
        combo.view().setMinimumWidth(_OFFICIAL_POPUP_WIDTH)
        combo.textActivated.connect(self._on_official_activated)
        completer.activated[str].connect(self._on_official_activated)
        combo.lineEdit().setPlaceholderText(_OFFICIAL_PLACEHOLDER)
        combo.lineEdit().textEdited.connect(self._on_official_text_edited)
        self._official_combo = combo
        box_lay.addWidget(self._framed(combo, "official_footprint"))
        self._official_status = QLabel()
        self._official_status.setTextFormat(Qt.TextFormat.PlainText)
        self._official_status.setWordWrap(True)
        self._official_status.setStyleSheet(f"color: {MUTED};")
        self._official_status.hide()
        box_lay.addWidget(self._official_status)
        hint = QLabel(_OFFICIAL_HINT)
        hint.setTextFormat(Qt.TextFormat.PlainText)
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {MUTED};")
        box_lay.addWidget(hint)
        box.hide()
        self._official_box = box
        left_lay.addWidget(box)

    def _build_fields_section(self, left_lay: QVBoxLayout):
        """Symbol, the read-only Footprint field, then the five editable fields with their restore buttons."""
        left_lay.addWidget(self._heading("Fields"))
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # The two read-only rows keep the right edge of the editable ones: a spacer stands for the ↺ button
        self._symbol_name_label = _OfferLabel(expanding=True)
        form.addRow("Symbol", self._aligned_row(self._symbol_name_label))

        # Read-only: the text always comes from the latest accepted plan, never from the inputs (PREV-03)
        self._fp_field = QLineEdit()
        self._fp_field.setReadOnly(True)
        self._fp_field.setFont(QFont(MONO_FAMILY, MONO_PT))
        self._fp_field.setAccessibleName("Footprint")
        self._fp_field.setMinimumHeight(28)
        # In a frame too, so it lines up with the editable rows (it is never blocked)
        form.addRow("Footprint", self._aligned_row(self._framed(self._fp_field, "footprint_field")))

        self._field_edits: dict[str, QLineEdit] = {}
        self._field_restore: dict[str, QToolButton] = {}
        for name in FIELD_NAMES:
            label = FIELD_LABELS[name]
            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(SP_XS)
            edit = QLineEdit()
            edit.setAccessibleName(label)
            edit.setMinimumHeight(28)
            if name in ("datasheet", "description", "manufacturer"):
                edit.setPlaceholderText(_REQUIRED_HINTS[name])
            if name == "mpn":
                edit.setToolTip("MPN names the 3D model file")
            if name == "value":
                # D-22: Value is always the MPN, so it is shown but never typed into
                edit.setReadOnly(True)
                edit.setToolTip(_VALUE_TIP)
            edit.textEdited.connect(lambda text, n=name: self._on_field_edited(n, text))
            restore = self._restore_button(f"Restore default {label}")
            restore.clicked.connect(lambda _checked=False, n=name: self._restore_field(n))
            # All five sit in a frame so the rows line up; only Value and MPN can be blocked
            row_lay.addWidget(self._framed(edit, name), 1)
            row_lay.addWidget(restore)
            form.addRow(label, row)
            self._field_edits[name] = edit
            self._field_restore[name] = restore
        # The generated texts: the plan's text until typed over, each with a button that returns to the generated one (D-30)
        self._text_edits: dict[str, QLineEdit] = {}
        self._text_regenerate: dict[str, QToolButton] = {}
        for name in TEXT_NAMES:
            label = TEXT_LABELS[name]
            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(SP_XS)
            edit = QLineEdit()
            edit.setAccessibleName(label)
            edit.setMinimumHeight(28)
            edit.setToolTip(_TEXT_TIPS[name])
            edit.textEdited.connect(lambda text, n=name: self._on_text_edited(n, text))
            # The same 24 px glyph button as the restore buttons: a word would widen the left pane past its viewport
            regenerate = self._restore_button(f"{_REGENERATE} {label}")
            regenerate.setText("↻")
            regenerate.setToolTip(f"{_REGENERATE}: write the generated {label.lower()} again")
            regenerate.clicked.connect(lambda _checked=False, n=name: self._regenerate_text(n))
            row_lay.addWidget(self._framed(edit, name), 1)
            row_lay.addWidget(regenerate)
            form.addRow(label, row)
            self._text_edits[name] = edit
            self._text_regenerate[name] = regenerate
        left_lay.addLayout(form)

    def _build_conflicts_section(self, left_lay: QVBoxLayout):
        """The Conflicts section (D-12): last in the left pane, hidden until the plan has a conflict."""
        box = QWidget()
        box_lay = QVBoxLayout(box)
        box_lay.setContentsMargins(0, 0, 0, 0)
        box_lay.setSpacing(SP_SM)
        box_lay.addWidget(self._heading("Conflicts"))
        self._conflicts_layout = QVBoxLayout()
        self._conflicts_layout.setContentsMargins(0, 0, 0, 0)
        self._conflicts_layout.setSpacing(SP_SM)
        box_lay.addLayout(self._conflicts_layout)
        box.hide()
        self._conflicts_box = box
        left_lay.addWidget(box)

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
        """Open a zip or folder on a worker; the dialog owns the resulting Package.

        A running build is not waited for on the GUI thread: the dialog enters Finishing and the open runs
        when the build has ended (D-06), so the old package closes only after it (WR-04).
        """
        if (
            self._closing or self._finishing or self._open_worker is not None or self.is_installing()
            or self.is_committing() or self.is_probing()
        ):
            return
        if self._busy_builds():
            self._enter_finishing("open", functools.partial(self._do_open, path))
            return
        self._do_open(path)

    def _do_open(self, path: Path):
        """The open after the builds have ended: discard the old package, reset, read the new one."""
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
                tools = suggestion = stock = None
                existing: tuple = ()
                if candidate is not None:
                    tools = core.detect_tools(fp_dir)
                    allowed = tools.allowed_stems or None
                    existing = tuple(existing_libraries(core.list_symbol_libs(layout), allowed))
                    if candidate.symbols:
                        # The sibling indexes are built here, never on the GUI thread (T-10-21)
                        own = core.own_index(layout.symbols_dir, allowed)
                        if tools.kicad_symbols_dir is not None:
                            stock = core.stock_index(tools.kicad_symbols_dir, progress)
                        suggestion = core.suggest_library(
                            candidate.symbols[0].meta, own=own, stock=stock, allowed=allowed
                        )
            except BaseException:
                package.close()
                raise
            return OpenOutcome(package, candidate, tuple(detect_issues), tools, suggestion, existing, stock)

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
        # QThread.finished arrives just before the thread ends, so this only joins a thread whose work has
        # returned; the bound keeps the GUI thread from ever waiting on a build (owner answer 2026-11-01, D-06)
        worker.wait(2000)
        if not isinstance(worker.value, (OpenOutcome, ModelOutcome)):
            worker.value = None
        self._try_finish(exclude=worker)

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
        self._stock = outcome.stock
        self.setWindowTitle(f"Import Part - {package.source.name}")
        if outcome.suggestion is not None and outcome.suggestion.issues:
            self.issues_logged.emit(list(outcome.suggestion.issues))
        self._package_label.setText(f"Package: {package.source.name}")
        self._vendor_label.setText(vendor_label(candidate.vendor))
        self._fill_library_combo()
        self._populate_items()
        self._sync_official_availability()
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

    def _allowed(self) -> frozenset[str] | None:
        """The stems the open tools allow, or None for the built-in snapshot."""
        return (self._tools.allowed_stems or None) if self._tools is not None else None

    def _fill_library_combo(self):
        """Pre-fill with the suggestion; the list holds the owner's Atomic_ libraries, a divider, then every allowed name (D-12, D-13)."""
        suggestion = self._suggestion
        combo = self._library_combo
        existing = [str(name) for name in self._existing]
        listed = set(existing)
        stems = self._allowed() or allowed_stems()
        others = sorted((ATOMIC_PREFIX + stem for stem in stems if ATOMIC_PREFIX + stem not in listed), key=str.casefold)
        combo.blockSignals(True)
        try:
            combo.clear()
            combo.addItems(existing)
            if existing and others:
                combo.insertSeparator(combo.count())
            combo.addItems(others)
            combo.setCurrentIndex(-1)
            combo.setEditText(suggestion.name if suggestion is not None else "")
        finally:
            combo.blockSignals(False)
        # The popup shows every full name even when the closed combo is narrower
        combo.view().setMinimumWidth(combo.view().sizeHintForColumn(0) + 32)
        self._typed = ""
        self._hide_library_note()
        self._refresh_library_labels()

    def _clear_library_section(self):
        """Forget the library list, the typed name, the badge and the note (a new or discarded package)."""
        self._existing = ()
        combo = self._library_combo
        combo.blockSignals(True)
        try:
            combo.clear()
            combo.setEditText("")
        finally:
            combo.blockSignals(False)
        self._typed = ""
        self._hide_library_note()
        self._refresh_library_labels()

    def _hide_library_note(self):
        self._note_for = ""
        self._library_note.hide()
        self._library_note.setText("")

    def _refresh_library_labels(self, _text: str = ""):
        """Badge, note and tooltip follow the typed name against the library list, at every keystroke.

        The badge reads "existing", "new - creates .kicad_sym" or nothing for a name the rule refuses
        (form.library_badge). The tooltip holds the reason for the suggestion while the field still
        holds the suggested name (D-06); it is html-escaped text, never raw (T-10-20).
        """
        name = self._library_combo.currentText()
        badge = library_badge(name, self._existing, self._allowed())
        self._library_badge.setVisible(bool(badge))
        self._library_badge.setText(badge)
        if badge == "existing":
            self._library_badge.setStyleSheet(f"border: 1px solid {BORDER}; padding: 4px 8px; color: {SUCCESS};")
        else:
            self._library_badge.setStyleSheet(
                f"border: 1px solid {BORDER}; padding: 4px 8px; font-weight: bold;"
            )
        suggestion = self._suggestion
        tip = suggestion_text(suggestion) if suggestion is not None and suggestion.name == name and name else ""
        self._library_combo.setToolTip(f"<p>{html.escape(tip)}</p>" if tip else "")
        if self._note_for and name != self._note_for:
            self._hide_library_note()

    def _correct_library_spelling(self) -> bool:
        """Use the official spelling of a name that differs from an allowed one only by letter case, and say so (D-11).

        The combo already swaps typed text for the list entry that matches it ignoring case when editing
        ends, so the typed text (kept in _typed) is what shows the owner's spelling was off.
        """
        text = self._library_combo.currentText()
        typed, self._typed = self._typed, ""
        verdict = name_verdict(text, self._allowed())
        if not verdict.ok and verdict.note and verdict.name != text:
            official = verdict.name
        elif verdict.ok and typed and typed != text and typed.casefold() == text.casefold():
            official = text
        else:
            return False
        if official != text:
            self._library_combo.setEditText(official)
        self._refresh_library_labels()
        self._note_for = official
        self._library_note.setText(f"Spelling corrected to {official}")
        self._library_note.show()
        return True

    # -- the rebuild coordinator (PREV-07, D-06) -------------------------------

    def is_finishing(self) -> bool:
        """True while a Change... or an open waits for a running build to end (D-06)."""
        return self._finishing

    def _busy_builds(self, exclude: TaskWorker | None = None) -> list[TaskWorker]:
        """The rebuild and one-off workers that still run, except exclude (the worker being reaped)."""
        return [w for w in (self._building, self._oneoff) if w is not None and w is not exclude]

    def _busy_for(self, kind: str, exclude: TaskWorker | None = None) -> list[TaskWorker]:
        """The workers a pending request of this kind waits for, except exclude (the worker being reaped).

        A close waits for every running worker, because the package they read is closed with the dialog;
        Change... and an open wait for the builds only (D-06).
        """
        if kind == "close":
            return [w for w in self._workers if w is not exclude and w.isRunning()]
        return self._busy_builds(exclude)

    def _enter_finishing(self, kind: str, action: Callable[[], None]):
        """Grey the dialog out and wait for the running build; action runs by itself when it has ended (D-06).

        The GUI thread never joins the build: the window keeps processing events, and kicad-cli is never
        killed. Its own timeout ends a slow call (D-07).
        """
        self._finishing = True
        self._pending = action
        self._pending_kind = kind
        self._stack.setEnabled(False)
        self._finish_label.setText(FINISHING_TEXT)
        self._finish_slow.setText(SLOW_CLI_TEXT)
        self._finish_slow.hide()
        self._finish_strip.show()
        QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        self._slow_timer.start(_SLOW_NOTE_MS)

    def _end_finishing(self):
        """The exact inverse of _enter_finishing; a no-op when not Finishing, so the cursor calls stay paired."""
        if not self._finishing:
            return
        self._finishing = False
        self._pending = None
        self._pending_kind = None
        self._slow_timer.stop()
        self._finish_strip.hide()
        self._finish_slow.hide()
        self._stack.setEnabled(True)
        QGuiApplication.restoreOverrideCursor()

    def _close_pending(self) -> bool:
        """True while a close waits for the workers: their results are dropped like at a finished close."""
        return self._finishing and self._pending_kind == "close"

    def _on_slow_timeout(self):
        if self._finishing:
            self._finish_slow.show()

    def _try_finish(self, exclude: TaskWorker | None = None):
        """Run the pending action once no relevant worker runs; called from every worker's finished handler."""
        if not self._finishing or self._closing or self._busy_for(self._pending_kind, exclude):
            return
        action = self._pending
        self._end_finishing()  # first, so the action sees a live dialog
        if action is not None:
            action()

    def _on_finish_cancel(self):
        """Drop the pending action and restore the dialog; held builds resume. kicad-cli is never killed (D-07)."""
        if not self._finishing:
            return
        kind = self._pending_kind
        self._end_finishing()
        self.leave_cancelled.emit()
        self._pump_builds()
        self._update_install_state()
        if kind == "close" and self._probe_cancelled_by_close:
            # The close stopped the commit probe: the panel gets a fresh one (D-07, T-12-21). The cancelled
            # probe's late result is dropped by the generation check.
            self._probe_cancelled_by_close = False
            self._start_probe(reprobe=True)

    def _reset_edit_state(self):
        self._gen += 1
        self._session += 1
        self._oneoff_jobs.clear()
        self._debounce.stop()
        self._dirty = False
        self._candidate = None
        self._suggestion = None
        self._clear_library_section()
        self._tools = None
        self._queued = None
        self._plan = None
        self._plan_gen = -1
        self._plan_options = None
        self._build_failed = False
        self._failure_banner.hide()
        self._first_plan_seen = False
        self._defaults = FieldDefaults()
        self._clear_conflicts()
        self._clear_items()
        self._reset_official_choice()
        self._preview.render(())
        self._preview_stack.setCurrentWidget(self._building_page)
        self._update_install_state()

    def _snapshot_options(self) -> InstallOptions:
        return build_options(self._form_values(), self._defaults, self._linked_fp)

    def _form_values(self) -> FormValues:
        """Read the controls: item choices as vendor names, one footprint (D-14)."""
        candidate = self._candidate
        symbol: str | None = None
        if self._symbol_combo is not None:
            symbol = self._symbol_combo.currentData()
        elif candidate.symbols:
            symbol = candidate.symbols[0].name

        footprint: str | None = None
        if self._fp_combo is not None:
            footprint = self._fp_combo.currentData()
        elif candidate.footprints:
            footprint = candidate.footprints[0].name

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
            footprint=footprint,
            model=model,
            no_model=no_model,
            footprint_name=self._fp_name_edit.text() if self._fp_name_edited else None,
            fields={name: self._field_edits[name].text() for name in FIELD_NAMES if name in self._edited},
            resolutions=dict(self._resolutions),
            texts={name: self._text_edits[name].text() for name in TEXT_NAMES if name in self._texts_edited},
            related_stems=self._suggestion.related_stems if self._suggestion is not None else (),
            footprint_target="official" if self._official_checked() else "shared",
            official_footprint=self._official_combo.currentText() if self._official_checked() else None,
        )

    # -- the item picker (INTK-07, D-04) -------------------------------------------

    def _clear_items(self):
        self._symbol_combo = self._model_combo = None
        self._symbol_label = self._fp_label = self._model_label = None
        self._fp_combo = None
        self._add_model_btn = self._model_slot = self._model_note = None
        self._remove_model_btn = None
        self._model_rejection = None
        # The footprint combo and its frame are deleted with their row
        self._field_frames.pop("footprints", None)
        self._reason_targets.pop("footprints", None)
        self._reason_targets.pop("model", None)
        self._reason_targets.pop("model_rejected", None)
        self._field_frames.pop("model", None)
        self._extends_note = None
        self._linked_fp = None
        while self._items_form.rowCount():
            self._items_form.removeRow(0)
        self._clear_form()

    def _clear_form(self):
        """Forget every edit and empty the footprint and field controls (a new or discarded package)."""
        self._edited.clear()
        self._texts_edited.clear()
        self._fp_name_edited = False
        self._defaults = FieldDefaults()
        self._set_text_edits(PartText())
        self._fp_name_edit.blockSignals(True)
        try:
            self._fp_name_edit.clear()
        finally:
            self._fp_name_edit.blockSignals(False)
        self._fp_name_edit.setEnabled(False)
        self._fp_name_restore.setEnabled(False)
        self._fp_name_hint.hide()
        self._set_field_texts()
        self._symbol_name_label.set_plain("")
        self._symbol_name_label.setToolTip("")
        self._fp_field.clear()
        self._fp_field.setStyleSheet("")

    @staticmethod
    def _item_label(name: str, *, missing: bool = False) -> "_OfferLabel":
        """A one-line plain label for a single item: the name elides in the middle, the tooltip holds it all."""
        label = _OfferLabel(expanding=True)
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
        """Build the Items controls for the open package: one item is a label, several a combo."""
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

        # Footprint: one per part (D-14); the chosen one carries the model and names the symbol's Footprint field
        footprints = [f.name for f in candidate.footprints]
        if len(footprints) > 1:
            combo = self._item_combo(footprints, "Vendor footprint")
            combo.currentIndexChanged.connect(self._on_footprint_changed)
            self._fp_combo = combo
            form.addRow("Footprint", self._framed(combo, "footprints"))
            self._linked_fp = footprints[0]
        elif footprints:
            self._fp_label = self._item_label(footprints[0])
            form.addRow("Footprint", self._fp_label)
            self._linked_fp = footprints[0]
        else:
            self._fp_label = self._item_label("No footprint in this package", missing=True)
            form.addRow("Footprint", self._fp_label)

        # 3D model: several give a combo that ends with "No model"; Add 3D model... sits under it
        form.addRow("3D model", self._build_model_row())

        self._reset_fp_name()
        self._reload_symbol_defaults()
        self._set_tab_order()

    def _make_model_widget(self) -> QWidget:
        """The label (none or one model) or combo (several, ending with "No model") for the candidate's models."""
        models = [m.filename for m in self._candidate.models]
        self._model_combo = self._model_label = None
        if len(models) > 1:
            combo = self._item_combo([*models, _NO_MODEL], "3D model")
            combo.setItemData(len(models), None)
            combo.setItemData(len(models), _NO_MODEL, Qt.ItemDataRole.ToolTipRole)
            self._model_combo = combo
            return combo
        if models:
            self._model_label = self._item_label(models[0])
            return self._model_label
        self._model_label = self._item_label("No 3D model in this package", missing=True)
        return self._model_label

    def _build_model_row(self) -> QWidget:
        """The 3D model row: the label or combo, then the Add 3D model... button (G-07-2)."""
        # The button sits under the label or combo: beside it, the row would not fit a narrow pane
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self._model_slot = lay
        widget = self._make_model_widget()
        lay.addWidget(widget)
        if self._model_combo is not None:
            self._model_combo.currentIndexChanged.connect(self._on_model_changed)
        button = QPushButton(ADD_MODEL_TEXT)
        button.setAutoDefault(False)
        button.setDefault(False)
        button.clicked.connect(self._on_add_model)
        button.setEnabled(not self._model_busy())
        # Framed so a missing model turns the visible button amber and a click on the reason lands on it (D-25)
        lay.addWidget(self._framed(button, "model"), alignment=Qt.AlignmentFlag.AlignLeft)
        self._add_model_btn = button
        # Why the last attach found nothing (or that it is still reading). File names and Issue texts come
        # from the downloaded source, so the label never reads them as markup (T-07-30)
        note = QLabel()
        note.setTextFormat(Qt.TextFormat.PlainText)
        note.setWordWrap(True)
        note.hide()
        lay.addWidget(note)
        self._model_note = note
        # Clears a rejected source (G-07-5); shown only while one is held. The tooltip is static text:
        # a file name from the download must never reach a tooltip, which auto-detects rich text (T-07-34)
        remove = QPushButton(REMOVE_MODEL_TEXT)
        remove.setAutoDefault(False)
        remove.setDefault(False)
        remove.setAccessibleName("Remove the rejected 3D model file")
        remove.setToolTip("Clear the rejected file. Nothing from it was attached.")
        remove.setEnabled(not self._model_busy())
        remove.clicked.connect(self._on_remove_model)
        remove.hide()
        lay.addWidget(remove, alignment=Qt.AlignmentFlag.AlignLeft)
        self._remove_model_btn = remove
        self._reason_targets["model_rejected"] = remove
        return host

    def _set_model_note(self, text: str, *, tone: str):
        """Show text under the 3D model row in the muted or red error tone, or hide the note (tone "hidden")."""
        note = self._model_note
        if note is None:
            return
        if tone == "hidden" or not text:
            note.hide()
            note.setText("")
            return
        note.setStyleSheet(f"color: {ERROR if tone == 'error' else MUTED};")
        note.setText(text)
        note.show()

    def _show_rejection(self):
        """Show the held rejected source as the red note with Remove; with none held, hide both."""
        rejection = self._model_rejection
        if rejection is None:
            self._set_model_note("", tone="hidden")
        else:
            self._set_model_note(rejection.issue.text, tone="error")
        button = self._remove_model_btn
        if button is not None:
            button.setVisible(rejection is not None)

    def _refresh_model_row(self, select: str | None = None):
        """Rebuild only the label or combo of the 3D model row after an attach.

        It never calls _populate_items, _clear_items, _clear_form, _reload_symbol_defaults or
        _reset_fp_name: those wipe the user's edits.
        """
        lay = self._model_slot
        if lay is None or self._candidate is None:
            return
        old = lay.itemAt(0).widget()
        lay.removeWidget(old)
        old.deleteLater()
        widget = self._make_model_widget()
        lay.insertWidget(0, widget)
        combo = self._model_combo
        if combo is not None:
            if select is not None:
                index = combo.findData(select)
                if index >= 0:
                    combo.blockSignals(True)
                    try:
                        combo.setCurrentIndex(index)
                        combo.setToolTip(combo.currentText())
                    finally:
                        combo.blockSignals(False)
            combo.currentIndexChanged.connect(self._on_model_changed)
        self._set_tab_order()

    def _set_tab_order(self):
        """Items come after the page's widgets in creation order, so chain the whole left pane by hand."""
        chain: list[QWidget] = [self._change_btn]
        for widget in (
            self._symbol_combo,
            self._fp_combo,
            self._model_combo,
            self._add_model_btn,
            self._remove_model_btn,
        ):
            if widget is not None:
                chain.append(widget)
        chain += [self._library_combo, self._fp_vendor_radio, self._fp_official_radio, self._official_combo]
        chain += [self._fp_name_edit, self._fp_name_restore, self._fp_field]
        for name in FIELD_NAMES:
            chain += [self._field_edits[name], self._field_restore[name]]
        for name in TEXT_NAMES:
            chain += [self._text_edits[name], self._text_regenerate[name]]
        for first, second in zip(chain, chain[1:]):
            QWidget.setTabOrder(first, second)

    def _set_linked(self, name: str | None):
        """Change which footprint is linked; its name field starts again from that footprint's default (D-14b)."""
        if name != self._linked_fp:
            self._linked_fp = name
            self._reset_fp_name()

    def _on_footprint_changed(self, _index: int = -1):
        """Another footprint chosen: it becomes the linked one and its name field starts again from its vendor name (D-14, D-20)."""
        combo = self._fp_combo
        if combo is None or self._candidate is None:
            return
        combo.setToolTip(combo.currentText())
        self._set_linked(combo.currentData())
        # Another footprint: its description and tags start again from the generated text
        self._texts_edited.difference_update(("fp_description", "fp_tags"))
        self._request_rebuild()

    def _on_symbol_changed(self, _index: int = -1):
        combo = self._symbol_combo
        if combo is None or self._candidate is None:
            return
        combo.setToolTip(combo.currentText())
        self._reload_symbol_defaults()  # another symbol: every field starts from its own defaults
        self._request_rebuild()

    def _on_model_changed(self, _index: int = -1):
        combo = self._model_combo
        if combo is None or self._candidate is None:
            return
        combo.setToolTip(combo.currentText())
        self._request_rebuild()

    # -- the official footprint choice (LIB-06, D-16 to D-18) -------------------------------------

    def _official_checked(self) -> bool:
        return self._fp_official_radio.isChecked()

    def _reset_official_choice(self):
        """Back to the vendor footprint with an empty picker (a new or discarded package)."""
        self._official_links = None
        self._official_worker = None
        self._stock = None
        for widget in (self._fp_official_radio, self._fp_vendor_radio, self._official_combo):
            widget.blockSignals(True)
        try:
            self._fp_vendor_radio.setChecked(True)
            self._official_combo.clear()
            self._official_combo.setEditText("")
        finally:
            for widget in (self._fp_official_radio, self._fp_vendor_radio, self._official_combo):
                widget.blockSignals(False)
        self._official_status.hide()
        self._sync_official_availability()
        self._apply_target_ui()

    def _sync_official_availability(self):
        """The official choice needs KiCad's footprints folder; without it the radio button is off and says why."""
        folder = self._tools.kicad_footprints_dir if self._tools is not None else None
        available = folder is not None or self._tools is None
        self._fp_official_radio.setEnabled(available)
        self._fp_official_radio.setToolTip("" if available else _OFFICIAL_UNAVAILABLE)
        self._official_note.setText("" if available else _OFFICIAL_UNAVAILABLE)
        self._official_note.setVisible(not available)

    def _apply_target_ui(self):
        """Show the picker and switch off the controls an official footprint makes meaningless (D-17, D-29)."""
        official = self._official_checked()
        self._official_box.setVisible(official)
        item = self._linked_item()
        self._fp_name_edit.setEnabled(item is not None and not official)
        if official:
            self._fp_name_restore.setEnabled(False)
        for name in ("fp_description", "fp_tags"):
            self._text_edits[name].setEnabled(not official)
            self._update_text_regenerate(name)
        self._sync_add_model_button()
        if official:
            self._set_model_note(_OFFICIAL_MODEL_NOTE, tone="muted")
        else:
            self._show_rejection()
        self._set_tab_order()

    def _on_fp_target_toggled(self, _checked: bool):
        """The destination changed: the vendor footprint name and the generated texts start again, and the plan is rebuilt."""
        if self._candidate is None:
            return
        # An official footprint is never edited, so a typed footprint text has nothing to apply to
        self._texts_edited.difference_update(("fp_description", "fp_tags"))
        self._reset_fp_name()
        self._apply_target_ui()
        if self._official_checked() and self._official_links is None and self._official_worker is None:
            self._start_official_list()
        self._request_rebuild()

    def _start_official_list(self):
        """Build the picker's list on a worker: KiCad's footprints ranked for this package, then all the others (D-16)."""
        folder = self._tools.kicad_footprints_dir if self._tools is not None else None
        chosen = self._chosen_symbol_name()
        if folder is None or self._closing or self._candidate is None or chosen is None:
            return
        core, stock, session = self._core, self._stock, self._session
        meta = next(s for s in self._candidate.symbols if s.name == chosen).meta
        part = meta.mpn or meta.symbol_name
        item = self._linked_item()
        code = item.name if item is not None else ""
        vendor_path = item.file.path if item is not None else None

        def task(progress):
            return official_candidates(
                core.footprint_index, folder, package_code=code, vendor_path=vendor_path, stock=stock, part=part,
                progress=progress,
            )

        worker = self._spawn(task)
        self._official_worker = worker
        self._official_status.setText(_OFFICIAL_READING)
        self._official_status.show()
        worker.result.connect(lambda links, w=worker, n=session: self._on_official_ready(w, n, links))
        worker.failed.connect(lambda text, w=worker, n=session: self._on_official_failed(w, n, text))
        worker.start()

    def _on_official_ready(self, worker: TaskWorker, session: int, links: list[str]):
        if self._official_worker is worker:
            self._official_worker = None
        if self._closing or session != self._session:
            return
        self._official_links = links
        combo = self._official_combo
        typed = combo.currentText()
        combo.blockSignals(True)
        try:
            combo.clear()
            combo.addItems(links)
            # The list picks nothing: the owner chooses (D-16)
            combo.setCurrentIndex(-1)
            combo.setEditText(typed)
        finally:
            combo.blockSignals(False)
        self._official_status.hide()

    def _on_official_failed(self, worker: TaskWorker, session: int, text: str):
        if self._official_worker is worker:
            self._official_worker = None
        if self._closing or session != self._session:
            return
        issue = Issue(Severity.ERROR, "import.step_failed", f"Import step failed: {text}")
        self.issues_logged.emit([issue])
        self._official_status.setText(f"KiCad's footprints could not be listed: {text}")
        self._official_status.show()

    def _on_official_activated(self, _text: str = ""):
        """A footprint picked from the list: no quiet period, the pending typing timer is superseded."""
        self._request_rebuild()

    def _on_official_text_edited(self, _text: str):
        if self._candidate is not None:
            self._mark_dirty()

    # -- Add 3D model... (G-07-2): a second intake source for a separately downloaded model ---------

    def _model_busy(self) -> bool:
        return (
            self._closing
            or self._candidate is None
            or self._open_worker is not None
            or self._model_worker is not None
            or self.is_installing()
            or self.is_committing()
        )

    def _on_add_model(self):
        if self._model_busy() or self._official_checked():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Add 3D model",
            str(self._browse_start_dir()),
            "3D models (*.step *.stp *.wrl *.zip)",
        )
        if path:
            save_import_dir(Path(path).parent)
            self._start_model_attach(Path(path))

    def _start_model_attach(self, path: Path):
        """Open the picked model source and attach its models to the open candidate, on one worker."""
        if self._model_busy():
            return
        core, repo_root, candidate, session = self._core, self._repo_root, self._candidate, self._session

        def task(progress):
            package = core.open_model_source(path, repo_root, progress)
            try:
                attached, issues = core.attach_models(candidate, package)
            except BaseException:
                package.close()
                raise
            return ModelOutcome(package, attached, tuple(issues), session)

        worker = self._spawn(task)
        self._model_worker = worker
        self._set_model_note(f"Reading {path.name}...", tone="muted")
        # Install is blocked as "Updating" until the plan that shows the model is current (T-07-29)
        self._update_install_state()
        worker.result.connect(lambda outcome, w=worker: self._on_model_attached(w, outcome))
        # The session and file name are bound now: a failure that arrives after Change... or a new open
        # belongs to a package that is gone and must not block the next one (T-07-36)
        worker.failed.connect(
            lambda text, w=worker, s=session, n=path.name: self._on_model_failed(w, text, s, n)
        )
        worker.start()

    def _end_model_worker(self, worker: TaskWorker):
        if self._model_worker is worker:
            self._model_worker = None
        self._sync_add_model_button()

    def _sync_add_model_button(self):
        """Add 3D model... is on only while a package is open and no open, model, install or git job runs."""
        button = self._add_model_btn
        if button is not None:
            # An official footprint brings KiCad's own 3D model, so no vendor model is added (D-17)
            button.setEnabled(not self._model_busy() and not self._official_checked())
        remove = self._remove_model_btn
        if remove is not None:
            remove.setEnabled(not self._model_busy())

    def _on_remove_model(self):
        """Clear the rejected source. It never detaches a model that was attached successfully (G-07-5)."""
        if self._model_busy():
            return
        self._model_rejection = None
        self._show_rejection()
        self._update_install_state()
        # The focus must not stay on the button that just hid itself
        if self._add_model_btn is not None:
            self._add_model_btn.setFocus(Qt.FocusReason.OtherFocusReason)

    def _on_model_attached(self, worker: TaskWorker, outcome: ModelOutcome):
        if self._closing:
            return  # _shutdown closes the package of an outcome that was not handled (T-07-27)
        worker.value = None  # handled here, so _shutdown does not close the package a second time
        self._end_model_worker(worker)
        stale = (
            outcome.session != self._session
            or self._candidate is None
            or self.is_installing()
            or self._stack.currentWidget() is not self._edit_page
        )
        if stale:
            # Change..., a new open or an install came first: the package is released and never attached (T-07-28)
            outcome.package.close()
            if outcome.session == self._session:
                self._show_rejection()  # drops "Reading..."; a held rejection stays shown
                self._update_install_state()
            return
        self.issues_logged.emit(list(outcome.issues))
        if outcome.candidate is None:
            # Nothing was attached: the candidate, the row and the generation stay as they were
            outcome.package.close()
            errors = [i for i in outcome.issues if i.severity is Severity.ERROR]
            if errors:
                # An unusable source blocks Install until the user removes it (G-07-5)
                self._model_rejection = RejectedModel(outcome.package.source.name, errors[0])
                self._show_rejection()
            elif self._model_rejection is not None:
                # An INFO duplicate attaches nothing: it goes to the log and the held rejection stays (G-07-5)
                self._show_rejection()
            elif outcome.issues:
                self._set_model_note(outcome.issues[0].text, tone="muted")
            else:
                self._set_model_note("", tone="hidden")
            self._update_install_state()
            return
        # A usable attach clears a held rejection: the note, Remove and the Error reason go (G-07-5)
        self._model_rejection = None
        self._show_rejection()
        self._model_packages.append(outcome.package)
        added = [m for m in outcome.candidate.models if m not in self._candidate.models]
        self._candidate = outcome.candidate
        self._refresh_model_row(select=added[0].filename if added else None)
        self._request_rebuild()

    def _on_model_failed(self, worker: TaskWorker, text: str, session: int, source: str):
        self._end_model_worker(worker)
        if self._closing:
            return
        issue = Issue(Severity.ERROR, "import.step_failed", f"Import step failed: {text}")
        self.issues_logged.emit([issue])
        if session != self._session or self._candidate is None:
            # Change... or a new open came first: the failure is only logged and never blocks the next package
            self._update_install_state()
            return
        # A read that failed is held like any other rejected source, so Install stays blocked (G-07-5)
        self._model_rejection = RejectedModel(source, issue)
        self._show_rejection()
        self._update_install_state()

    # -- conflicts: one row per conflict, choices kept by key (PREV-05, D-12, D-14a) ----------------

    def _sync_conflicts(self, plan: InstallPlan):
        """Show the accepted plan's conflicts: prune the choices to its keys, update rows in place by key.

        A row that stays keeps its widgets, so focus and typed rename text survive the rebuild. A key
        that vanished takes its row and choice with it; a new key starts unresolved.
        """
        self._resolutions = carry_resolutions(self._resolutions, plan)
        wanted = [conflict.key for conflict in plan.conflicts]
        for key in [key for key in self._conflict_rows if key not in wanted]:
            self._remove_conflict_row(key)
        for index, conflict in enumerate(plan.conflicts):
            row = self._conflict_rows.get(conflict.key)
            if row is None:
                row = self._add_conflict_row(conflict)
            else:
                row.update_conflict(conflict)
            resolution = self._resolutions.get(conflict.key)
            if row.current_resolution() != resolution:
                row.set_resolution(resolution)
            if self._conflicts_layout.indexOf(row) != index:
                self._conflicts_layout.removeWidget(row)
                self._conflicts_layout.insertWidget(index, row)
        self._conflicts_box.setVisible(bool(wanted))

    def _add_conflict_row(self, conflict: Conflict) -> ConflictRow:
        key = conflict.key
        row = ConflictRow(conflict)
        row.choice_changed.connect(self._on_conflict_choice)
        row.rename_edited.connect(self._on_conflict_rename)
        row.activated.connect(self._open_conflict_view)
        self._conflict_rows[key] = row
        self._conflicts_layout.addWidget(row)
        self._reason_targets[f"conflict:{key}"] = row.overwrite_button
        self._reason_targets[f"rename:{key}"] = row.rename_edit
        self._field_frames[f"rename:{key}"] = row.rename_frame
        return row

    def _remove_conflict_row(self, key: str):
        row = self._conflict_rows.pop(key)
        for target in (f"conflict:{key}", f"rename:{key}"):
            self._reason_targets.pop(target, None)
            self._field_frames.pop(target, None)
        self._conflicts_layout.removeWidget(row)
        row.hide()
        row.setParent(None)
        row.deleteLater()

    def _clear_conflicts(self):
        """Forget every conflict row and choice (a new or discarded package)."""
        for key in list(self._conflict_rows):
            self._remove_conflict_row(key)
        self._resolutions = {}
        self._conflicts_box.hide()

    def _on_conflict_choice(self, key: str, resolution: Resolution | None):
        """A button was picked: keep the choice and rebuild at once (it supersedes any typing timer)."""
        if resolution is None:
            self._resolutions.pop(key, None)
        else:
            self._resolutions[key] = resolution
        self._request_rebuild()

    def _on_conflict_rename(self, key: str, text: str):
        """The rename field was typed in: the text goes to the planner exactly as typed, after the quiet period."""
        self._resolutions[key] = Resolution("rename", text)
        self._mark_dirty()

    # -- the content view (D-08): read-only text of what a file write or an overwrite changes -----

    def _on_preview_row_activated(self, row):
        """A preview row was double-clicked or entered: open the content view of its file or conflict."""
        plan = self._plan
        if plan is None or self._candidate is None or self._closing:
            return
        if row.kind == "conflict":
            self._open_conflict_view(row.key)
            return
        if row.kind != "file":
            return
        core, repo_root = self._core, self._repo_root
        if row.op_index is not None:
            if row.op_index >= len(plan.ops):
                return
            op = plan.ops[row.op_index]
            self._run_content(lambda: core.op_content(op, repo_root))
        elif row.path is not None:
            path = row.path
            self._run_content(lambda: core.unchanged_content(path, repo_root))

    def _open_conflict_view(self, key: str):
        """Show the existing item against the incoming one for a conflict (D-08).

        The incoming bytes are on the plan only after Overwrite. An undecided conflict gets a one-off
        build_plan with Overwrite for that key, on the shared build queue; its plan is only read for the
        op and never replaces the plan on screen (RESEARCH Pitfall 2).
        """
        plan = self._plan
        if plan is None or self._candidate is None or self._closing:
            return
        conflict = next((c for c in plan.conflicts if c.key == key), None)
        if conflict is None:
            return
        core, repo_root = self._core, self._repo_root
        if conflict.resolution is not None and conflict.resolution.action == "overwrite":
            op = incoming_op(plan, conflict)
            if op is not None:
                self._run_content(lambda: core.op_content(op, repo_root, conflict=True))
                return
        # Queued even while an install runs: _pump_builds holds every job until the install ends, so no
        # one-off build reads the files while the install writes them (D-08, 05-REVIEW WR-03)
        options = self._snapshot_options()
        options = replace(options, resolutions={**options.resolutions, key: Resolution("overwrite")})
        self._oneoff_jobs.append(
            (self._session, options, lambda built, error: self._on_conflict_built(conflict, built, error))
        )
        self._pump_builds()

    def _on_conflict_built(self, conflict: Conflict, built: InstallPlan | None, error: str):
        """The one-off plan is here: find the incoming op and show it, or show why there is none."""
        core, repo_root = self._core, self._repo_root
        op = incoming_op(built, conflict) if built is not None else None
        if op is not None:
            self._run_content(lambda: core.op_content(op, repo_root, conflict=True))
            return
        if built is None:
            body = f"The incoming {kind_label(conflict.kind)} could not be built: {error}"
        else:
            errors = [i.text for i in built.issues if i.severity is Severity.ERROR]
            body = errors[0] if errors else f"The incoming {kind_label(conflict.kind)} is not part of the plan."
        title = f"{conflict.name} - existing vs incoming"
        self._show_content(ContentText(title=title, header=conflict.existing, body=body, kind="error"))

    def _run_content(self, build: Callable[[], ContentText]):
        """Build a ContentText on a worker (hashing and diffing never run on the GUI thread), then show it."""
        session = self._session
        worker = self._spawn(lambda progress: build())
        worker.result.connect(lambda content, w=worker: self._on_content_ready(session, content))
        worker.failed.connect(lambda text, w=worker: self._on_content_failed(session, text))
        worker.start()

    def _on_content_ready(self, session: int, content: ContentText):
        if not self._closing and session == self._session:
            self._show_content(content)

    def _on_content_failed(self, session: int, text: str):
        if self._closing or session != self._session:
            return
        self.issues_logged.emit([Issue(Severity.ERROR, "import.step_failed", f"Import step failed: {text}")])
        self._show_content(ContentText(
            title="Content view", header="", body=f"Could not build the view: {text}", kind="error"
        ))

    def _show_content(self, content: ContentText):
        view = ContentViewDialog(content, parent=self)
        self._content_views.append(view)
        view.finished.connect(lambda _result=0, v=view: self._on_view_closed(v))
        view.open()

    def _on_view_closed(self, view: ContentViewDialog):
        if view in self._content_views:
            self._content_views.remove(view)
        view.deleteLater()

    def _show_plan_in_form(self, plan: InstallPlan):
        """Show what the accepted plan says: the extends note, the symbol name, the fields and the Footprint field."""
        note = self._extends_note
        if note is not None:
            parents = plan.symbol_names[:-1]
            note.setText(f"extends parent {', '.join(parents)} is included automatically" if parents else "")
            note.setVisible(bool(parents))
        # The fields show what this plan writes: the defaults follow the final symbol name (PREV-04)
        chosen = self._chosen_symbol_name()
        if chosen is not None and plan.symbol_name:
            self._defaults = field_defaults(self._candidate, chosen, final_name=plan.symbol_name)
            self._set_field_texts()
            self._show_symbol_name(chosen, plan.symbol_name)
        # D-30: the texts the plan writes; a row the user typed over keeps its text
        self._set_text_edits(plan.part_text)
        for name in TEXT_NAMES:
            self._update_text_regenerate(name, plan)
        # PREV-03: read from the plan, never computed from the inputs
        if plan.footprint_link is None or not plan.symbol_names:
            self._fp_field.setText(_NO_FOOTPRINT_FIELD)
            self._fp_field.setStyleSheet(f"color: {MUTED};")
        else:
            self._fp_field.setText(plan.footprint_link)
            self._fp_field.setStyleSheet("")

    # -- footprint name and field text (D-13, D-14, PREV-02, PREV-04) ---------------

    def _chosen_symbol_name(self) -> str | None:
        """The vendor name of the symbol the controls select."""
        if self._candidate is None or not self._candidate.symbols:
            return None
        if self._symbol_combo is not None:
            return self._symbol_combo.currentData()
        return self._candidate.symbols[0].name

    def _show_symbol_name(self, vendor: str, final: str):
        text = final if vendor == final else f"{vendor} → {final}"
        self._symbol_name_label.set_parts("", text, "")
        self._symbol_name_label.setToolTip(text)

    def _reload_symbol_defaults(self):
        """A symbol was opened or picked: reload every field from its defaults and forget the field edits."""
        chosen = self._chosen_symbol_name()
        self._edited.clear()
        if chosen is None:
            self._defaults = FieldDefaults()
            self._set_field_texts()
            return
        self._texts_edited.discard("keywords")
        item = next(s for s in self._candidate.symbols if s.name == chosen)
        final = item.name_check.sanitized  # until a plan says otherwise (a conflict Rename)
        self._defaults = field_defaults(self._candidate, chosen, final_name=final)
        self._set_field_texts()
        self._show_symbol_name(chosen, final)

    def _mirror_value(self):
        """Value shows the MPN field's text, whatever it is now (D-22); it has no restore button to use."""
        edit = self._field_edits["value"]
        edit.blockSignals(True)
        try:
            edit.setText(self._field_edits["mpn"].text())
            edit.setCursorPosition(0)
        finally:
            edit.blockSignals(False)

    def _set_field_texts(self):
        """Put the defaults into every field that was not edited; edited fields keep their text."""
        for name, edit in self._field_edits.items():
            if name == "value":
                continue
            if name not in self._edited:
                edit.blockSignals(True)
                try:
                    edit.setText(self._defaults.get(name))
                    edit.setCursorPosition(0)
                finally:
                    edit.blockSignals(False)
            self._update_field_restore(name)
        self._mirror_value()
        self._update_field_restore("value")

    def _update_field_restore(self, name: str):
        button = self._field_restore[name]
        if name == "value":
            button.setEnabled(False)
            button.setToolTip(_VALUE_TIP)
            return
        default = self._defaults.get(name)
        button.setEnabled(self._field_edits[name].text() != default)
        button.setToolTip(f"Restore default: {default}")

    def _on_field_edited(self, name: str, text: str):
        """User typing only (textEdited): remember the edit and wait for the quiet period."""
        if name == "value":
            return
        if name == "mpn":
            self._mirror_value()
        if text == self._defaults.get(name):
            self._edited.discard(name)  # typed back to the default: the planner decides again
        else:
            self._edited.add(name)
        self._update_field_restore(name)
        self._mark_dirty()

    # -- the generated texts (D-30) --------------------------------------------------

    def _set_text_edits(self, text: PartText):
        """Put the plan's text into every generated-text row the user did not type over."""
        for name in TEXT_NAMES:
            if name in self._texts_edited:
                continue
            edit = self._text_edits[name]
            edit.blockSignals(True)
            try:
                edit.setText(getattr(text, name))
                edit.setCursorPosition(0)
            finally:
                edit.blockSignals(False)

    def _update_text_regenerate(self, name: str, plan: InstallPlan | None = None):
        """Regenerate works while the row holds text other than the generated one."""
        plan = plan if plan is not None else self._plan
        generated = getattr(plan.generated_text, name) if plan is not None else ""
        # The footprint's texts are never written for an official footprint, so they are not regenerated either
        frozen = self._official_checked() and name in ("fp_description", "fp_tags")
        self._text_regenerate[name].setEnabled(
            not frozen and name in self._texts_edited and self._text_edits[name].text() != generated
        )

    def _on_text_edited(self, name: str, text: str):
        """User typing only (textEdited): the row is theirs from now on, and the plan is rebuilt after the quiet period."""
        generated = getattr(self._plan.generated_text, name) if self._plan is not None else None
        if text == generated:
            self._texts_edited.discard(name)  # typed back to the generated text: the planner decides again
        else:
            self._texts_edited.add(name)
        self._update_text_regenerate(name)
        self._mark_dirty()

    def _regenerate_text(self, name: str):
        """Forget the typed text of one row: the generated text comes back with the next plan."""
        self._texts_edited.discard(name)
        if self._plan is not None:
            edit = self._text_edits[name]
            edit.blockSignals(True)
            try:
                edit.setText(getattr(self._plan.generated_text, name))
                edit.setCursorPosition(0)
            finally:
                edit.blockSignals(False)
        self._update_text_regenerate(name)
        self._request_rebuild()

    def _restore_field(self, name: str):
        if name == "value":
            return
        self._edited.discard(name)
        edit = self._field_edits[name]
        edit.blockSignals(True)
        try:
            edit.setText(self._defaults.get(name))
            edit.setCursorPosition(0)
        finally:
            edit.blockSignals(False)
        if name == "mpn":
            self._mirror_value()
        self._update_field_restore(name)
        self._request_rebuild()

    def _linked_item(self):
        """The candidate footprint that is linked, or None."""
        if self._candidate is None or self._linked_fp is None:
            return None
        return next((f for f in self._candidate.footprints if f.name == self._linked_fp), None)

    def _reset_fp_name(self):
        """Start the Name field again from the linked footprint's sanitised vendor name (D-14b)."""
        item = self._linked_item()
        self._fp_name_edited = False
        self._fp_name_edit.blockSignals(True)
        try:
            self._fp_name_edit.setText(item.name_check.sanitized if item is not None else "")
            self._fp_name_edit.setCursorPosition(0)
        finally:
            self._fp_name_edit.blockSignals(False)
        self._fp_name_edit.setEnabled(item is not None and not self._official_checked())
        self._fp_name_restore.setEnabled(False)
        differs = item is not None and item.name != item.name_check.sanitized
        self._fp_name_hint.setText(f"Vendor name: {item.name}" if differs else "")
        self._fp_name_hint.setVisible(differs)

    def _on_fp_name_edited(self, text: str):
        item = self._linked_item()
        default = item.name_check.sanitized if item is not None else ""
        self._fp_name_edited = text != default
        self._fp_name_restore.setEnabled(self._fp_name_edited)
        self._mark_dirty()

    def _on_fp_name_restore(self):
        self._reset_fp_name()
        self._request_rebuild()

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
        """A library picked from the list: no quiet period, the pending typing timer is superseded."""
        self._correct_library_spelling()
        self._refresh_library_labels()
        self._request_rebuild()

    def _on_library_editing_finished(self):
        """Editing the library name ended: a wrong letter case becomes the official spelling and the plan follows (D-11)."""
        if self._candidate is not None and self._correct_library_spelling():
            self._request_rebuild()

    def _on_library_text_edited(self, text: str):
        """User typing in the library name (textEdited): the labels already follow; the rebuild waits 300 ms."""
        self._typed = text
        self._hide_library_note()
        if self._candidate is not None:
            self._mark_dirty()

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
        if self._building is not None or self._oneoff is not None or self._finishing or self.is_installing():
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
        """Common tail of a build result or failure: free the slot and run the next queued build."""
        if self._building is worker:
            self._building = None
        self._pump_builds()

    def _pump_builds(self):
        """Start the next queued build when none runs: the latest rebuild first, then one-off jobs in order."""
        if (
            self._closing or self._finishing or self.is_installing()
            or self._building is not None or self._oneoff is not None
        ):
            # While Finishing nothing starts, so a queued build cannot restart kicad-cli and prolong the wait;
            # while installing nothing starts, so no build reads the library the install writes (D-08)
            return
        if self._queued is not None:
            options, self._queued = self._queued, None
            self._start_build(options)
            return
        while self._oneoff_jobs:
            session, options, on_result = self._oneoff_jobs.pop(0)
            if session == self._session:  # a job of a package that was changed meanwhile is dropped
                self._start_oneoff(session, options, on_result)
                return

    def _start_oneoff(self, session: int, options: InstallOptions, on_result: Callable):
        core, candidate, layout, tools = self._core, self._candidate, self._repo_layout, self._tools
        worker = self._spawn(lambda progress: core.build_plan(candidate, options, layout, tools))
        self._oneoff = worker
        worker.result.connect(lambda plan, w=worker: self._on_oneoff_done(w, session, on_result, plan, ""))
        worker.failed.connect(lambda text, w=worker: self._on_oneoff_done(w, session, on_result, None, text))
        worker.start()
        self._update_install_state()  # a running one-off counts as updating: Install greys out at once (D-08)

    def _on_oneoff_done(self, worker: TaskWorker, session: int, on_result: Callable, plan, error: str):
        """A one-off build ended. Its plan goes only to on_result: never to self._plan, _plan_gen or _gen."""
        if self._oneoff is worker:
            self._oneoff = None
        if not self._closing:
            if plan is None:
                self.issues_logged.emit([Issue(Severity.ERROR, "import.step_failed", f"Import step failed: {error}")])
            if session == self._session and not self._finishing:  # no content view opens over a pending action
                on_result(plan, error)
            self._pump_builds()
            self._update_install_state()

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
            self._sync_conflicts(plan)
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
        # A model being read counts too: the preview does not show it yet, so nothing may install from it.
        # So does a one-off conflict build: it reads the target library, which Install is about to write (D-08)
        return (
            self._building is not None
            or self._oneoff is not None
            or self._queued is not None
            or self._dirty
            or self._model_worker is not None
        )

    def _sync_updating(self):
        """Show "Updating..." beside the Preview title while a rebuild is pending; the busy strip joins after 150 ms.

        Only while the previous tree is on screen: the first build has its own Building page.
        """
        active = (
            self._candidate is not None
            and not self._closing
            and not self.is_installing()
            and self._updating()
            and self._preview_stack.currentWidget() is self._preview
        )
        if active and not self._updating_shown:
            self._updating_shown = True
            self._updating_label.show()
            self._busy_timer.start()
        elif not active and self._updating_shown:
            self._updating_shown = False
            self._busy_timer.stop()
            self._updating_label.hide()
            self._busy_bar.hide()

    def _on_busy_timeout(self):
        if self._updating_shown:
            self._busy_bar.show()

    def _form_status(self) -> FormStatus:
        """The controls as blocking_reasons reads them. "Updating" means a rebuild is dirty, running, queued or lost."""
        plan = self._plan
        current = plan is not None and self._plan_gen == self._gen
        return FormStatus(
            updating=self._updating() or (not current and not self._build_failed),
            build_failed=self._build_failed,
            library=self._library_combo.currentText(),
            mpn_text=self._field_edits["mpn"].text(),
            resolutions=dict(self._resolutions),
            # An official footprint uses none of the vendor models, so a rejected one does not block
            model_error=(
                self._model_rejection.issue.text
                if self._model_rejection is not None and not self._official_checked()
                else ""
            ),
            allowed=self._tools.allowed_stems if self._tools is not None else frozenset(),
            datasheet_text=self._field_edits["datasheet"].text(),
            description_text=self._field_edits["description"].text(),
            manufacturer_text=self._field_edits["manufacturer"].text(),
        )

    def _set_strip(self, text: str, *, rich: bool = False, style: str = "", tooltip: str = ""):
        """Set the strip's format first, then its text (a status line is plain, the reason list is rich).

        The style is wrapped in a QLabel#installStrip rule: Qt styles a QToolTip with the stylesheet of the
        widget it is shown for, so a selector-less declaration would tint the strip's tooltip too.
        """
        strip = self._strip
        strip.setTextFormat(Qt.TextFormat.RichText if rich else Qt.TextFormat.PlainText)
        strip.setStyleSheet(f"QLabel#installStrip {{ {style} }}" if style else "")
        strip.setText(text)
        strip.setToolTip(tooltip)

    def _update_install_state(self):
        self._sync_updating()
        self._sync_add_model_button()
        if self.is_installing():
            return
        plan = self._plan
        current = plan is not None and self._plan_gen == self._gen
        shown = plan if current else None
        reasons: list[Reason] = []
        detail: list[Reason] = []
        if self._candidate is not None:
            status = self._form_status()
            reasons = blocking_reasons(status, shown)
            # The amber frames follow the live text, so they hold while a rebuild catches up
            detail = blocking_reasons(replace(status, updating=False), shown) if status.updating else reasons
        self._apply_blocked_frames({r.target for r in detail})
        ready = (
            self._candidate is not None
            and current
            and not reasons
            and not plan.blocked
            and not plan.is_noop
        )
        self._install_btn.setText("Install Part")
        self._install_btn.setEnabled(bool(ready))
        # The choices wait for the first plan; a failed first build must not lock the user out
        self._left_scroll.setEnabled(self._first_plan_seen or self._build_failed)
        self._change_btn.setEnabled(True)
        self._render_strip(reasons, plan if current else None)

    def _apply_blocked_frames(self, targets: set[str]):
        """Turn each field frame amber while a reason targets it; re-polish so the stylesheet applies."""
        for key, frame in self._field_frames.items():
            blocked = key in targets
            if bool(frame.property("blocked")) != blocked:
                frame.setProperty("blocked", blocked)
                frame.style().unpolish(frame)
                frame.style().polish(frame)

    def _render_strip(self, reasons: list[Reason], plan: InstallPlan | None):
        """The bottom-left line: why Install is off (links), or the ready or no-op line (D-09)."""
        self._strip_reasons = reasons
        if self._candidate is None or plan is None and not reasons:
            self._set_strip("")
        elif reasons and reasons[0].text == UPDATING_REASON:
            self._set_strip(UPDATING_REASON, style=f"color: {MUTED};")
        elif reasons:
            links = " · ".join(
                f'<a href="reason:{i}" style="color:{LINK}">{html.escape(reason.text)}</a>'
                for i, reason in enumerate(reasons)
            )
            # The leading <p> makes the tooltip rich text for any reason count, so a single escaped reason
            # decodes instead of showing &amp; literally. Every string is escaped; no link markup (T-07-39).
            tooltip = (
                "<p>" + "<br>".join(html.escape(reason.text) for reason in reasons)
                + "</p><p><i>" + html.escape(STRIP_LINK_HINT) + "</i></p>"
            )
            self._set_strip(
                f"⚠ Install is blocked: {links}", rich=True, style=f"background-color: {AMBER_TINT};", tooltip=tooltip
            )
        elif plan.is_noop:
            self._set_strip(noop_text(plan.library), style=f"color: {MUTED};")
        else:
            counts = file_counts(plan, self._candidate, self._plan_options)
            self._set_strip(ready_text(counts), style=f"color: {SUCCESS};")

    def _on_reason_link(self, href: str):
        """A reason in the strip was clicked: focus the control that fixes it and scroll it into view."""
        prefix = "reason:"
        if not href.startswith(prefix) or not href[len(prefix):].isdigit():
            return  # only this dialog's own links do anything (T-05-27)
        index = int(href[len(prefix):])
        if index >= len(self._strip_reasons):
            return
        target = self._strip_reasons[index].target
        widget = self._preview if target == "plan" else self._reason_targets.get(target)
        if widget is None:
            return
        widget.setFocus(Qt.FocusReason.OtherFocusReason)
        left = self._left_scroll.widget()
        if left is not None and left.isAncestorOf(widget):
            self._left_scroll.ensureWidgetVisible(widget)

    def _on_install_shortcut(self):
        """Ctrl+Return: Install, but only when the button is enabled (it checks that itself)."""
        if self._stack.currentWidget() is self._edit_page:
            self._on_install_clicked()

    # -- install ------------------------------------------------------------------

    def _on_install_clicked(self):
        if not self._install_btn.isEnabled() or self.is_installing() or self._plan is None:
            return
        plan = self._plan  # the rendered object, never a rebuilt copy (PREV-07)
        core, backup_root = self._core, self._backup_root
        self._failure_banner.hide()
        # The worker gets the plan captured above and never reads self._plan from its thread (WR-04).
        # Besides, the inputs are locked and a build result is not accepted until the install ends
        # (_on_build_result).
        worker = self._spawn(
            lambda progress, p=plan: core.apply_plan(p, backup_root=backup_root, progress=progress)
        )
        self._install_worker = worker
        self._install_step.set_full_text("Installing...")
        self._install_bar.setValue(0)
        self._set_install_ui(True)
        worker.progress.connect(self._on_install_progress)
        worker.result.connect(lambda result, w=worker, p=plan: self._on_install_done(w, p, result))
        worker.failed.connect(lambda text, w=worker: self._on_install_failed(w, text))
        worker.start()

    def _set_install_ui(self, installing: bool):
        """Lock or unlock the inputs for an install (D-10); the preview tree stays usable either way."""
        self._left_scroll.setEnabled(not installing)
        self._header_row.setEnabled(not installing)
        self._strip.setVisible(not installing)
        self._install_row.setVisible(installing)
        self._sync_add_model_button()
        if installing:
            self._install_btn.setEnabled(False)
            self._install_btn.setText("Installing...")
        self._sync_cancel_button()

    def _sync_cancel_button(self):
        """Cancel works only while nothing is written: an install or a commit cannot be cancelled (D-10, D-07)."""
        self._cancel_btn.setEnabled(not self.is_installing() and not self.is_committing())

    def _on_install_progress(self, message: str, current: int, total: int):
        """A step of the install. A callback that stops arriving leaves the last text and value in place."""
        if self.is_installing():
            self._install_step.set_full_text(message)
            self._install_bar.setValue(max(0, min(100, int(current * 100 / max(total, 1)))))

    def _on_install_done(self, worker: TaskWorker, plan: InstallPlan, result: InstallResult):
        if self._install_worker is worker:
            self._install_worker = None
        self._install_bar.setValue(100)  # apply_plan's step index never reaches the total
        self._set_install_ui(False)
        self.issues_logged.emit(list(result.issues))
        if result.ok:
            # The Result page replaced the preview, so a conflict view held during the install would be stale
            # (the owner-approved refinement of D-08). A rebuild asked for meanwhile is dropped for the same
            # reason: it would refresh a preview that is gone. That second drop is not named in the refinement.
            self._oneoff_jobs.clear()
            self._queued = None
            self.result = result
            self.result_plan = plan
            self._show_result(plan, result)
            self.installed.emit(result, plan)
            self._pump_builds()  # nothing is held now, so this starts nothing
            return
        self._show_failure(result.issues, result.backup_dir)
        self._pump_builds()  # the jobs held during the install start now, in the order they were asked for
        # Files on disk may have changed: rebuild so a retry cannot hit the stale-plan guard
        self._request_rebuild()

    def _on_install_failed(self, worker: TaskWorker, text: str):
        if self._install_worker is worker:
            self._install_worker = None
        self._set_install_ui(False)
        issue = Issue(Severity.ERROR, "import.step_failed", f"Import step failed: {text}")
        self.issues_logged.emit([issue])
        # The worker itself broke, so nothing says every file was restored
        self._show_failure([issue], None, title=_FAILED_PLAIN)
        self._pump_builds()  # the jobs held during the install start now (05-REVIEW WR-03)
        self._request_rebuild()

    def _show_result(self, plan: InstallPlan, result: InstallResult):
        view = self._result_view
        view.show_result(result, plan, self._repo_root)
        self._stack.setCurrentWidget(view)
        # Close is the default button on this page only (Enter closes it; the Edit page has none)
        view.close_button.setAutoDefault(True)
        view.close_button.setDefault(True)
        view.close_button.setFocus()
        self._start_kicad_check(result.library)
        self._start_commit_step(plan, result)

    # -- commit step (Phase 6): nothing is committed before the user clicks Commit ---------------------

    def is_committing(self) -> bool:
        """True while Switch to main or Commit runs; the dialog cannot close then (D-07).

        The read-only probe never blocks closing: it is cancelled and waited for on close (IN-02).
        """
        return self._git_worker is not None

    def is_probing(self) -> bool:
        """True while the read-only probe of the commit step runs."""
        return self._probe_worker is not None

    def _set_git_worker(self, worker: TaskWorker | None):
        """Record the running git job, or None when it ended; Close is disabled while one runs (D-07).

        Qt moves the focus off a button when it is disabled, and Close starts out as the Result page's
        focus, so when Close held the focus it gets it back once git is idle again.
        """
        self._git_worker = worker
        self._sync_add_model_button()
        self._sync_cancel_button()
        button = self._result_view.close_button
        busy = worker is not None
        if busy == (not button.isEnabled()):
            return
        if busy:
            self._close_had_focus = button.hasFocus()
            button.setEnabled(False)
            return
        button.setEnabled(True)
        if self._close_had_focus:
            button.setFocus()
        self._close_had_focus = False

    def _start_commit_step(self, plan: InstallPlan, result: InstallResult):
        """Show the commit panel for the part that was just installed and probe git for it (D-01, D-08)."""
        self._commit_panel = self._commit_plan = self._commit_probe = None
        if not result.ok or plan.is_noop or not result.touched:
            return
        cplan = build_commit_plan(result, plan, vendor_label=vendor_label(result.vendor))
        panel = CommitPanel()
        panel.commit_requested.connect(self._on_commit_requested)
        panel.switch_requested.connect(self._on_switch_requested)
        panel.file_activated.connect(self._on_commit_file_activated)
        panel.check_again_requested.connect(self._on_check_again)
        panel.open_check_requested.connect(self._on_open_atomic_check)
        self._commit_panel, self._commit_plan = panel, cplan
        self._result_view.set_commit_panel(panel)
        self._start_probe()

    def _begin_probe_generation(self) -> threading.Event:
        """A newer probe or check supersedes every older one: their Events are set, the new one is returned (T-11-22)."""
        for older in self._probe_cancels:
            older.set()
        event = threading.Event()
        self._probe_cancels = [event]  # the older ones are set already; _shutdown sets the live one
        self._commit_probe = None
        return event

    def _start_probe(self, *, reprobe: bool = False):
        """Probe git for the current commit plan; runs again after a switch or a refusal (D-15, D-11).

        The probe takes no Close lock. A newer probe supersedes an older one: the older Event is set
        and its result is dropped when it arrives (generation check, T-11-22).
        """
        panel, cplan = self._commit_panel, self._commit_plan
        if panel is None or cplan is None or self._closing:
            return
        event = self._begin_probe_generation()
        if reprobe:
            panel.begin_reprobe()
        else:
            panel.show_plan(cplan)
        core, fp_dir = self._core, self._kicad_fp_dir
        worker = self._spawn(
            lambda progress, cp=cplan, ev=event: core.probe_commit(cp, kicad_fp_dir=fp_dir, cancelled=ev.is_set)
        )
        self._probe_worker = worker
        worker.result.connect(lambda probe, w=worker: self._on_probe_done(w, probe))
        worker.failed.connect(lambda text, w=worker: self._on_probe_failed(w, text))
        worker.start()

    def _on_probe_done(self, worker: TaskWorker, probe: CommitProbe):
        if worker is not self._probe_worker:
            return  # a superseded probe
        self._probe_worker = None
        self._apply_probe_result(probe)

    def _apply_probe_result(self, probe: CommitProbe):
        """Show a probe that is still current: the panel takes it and its issues go to the log."""
        if self._closing or self._close_pending() or self._commit_panel is None:
            return
        self._commit_probe = probe
        self._commit_panel.apply_probe(probe)
        if probe.issues:
            self.issues_logged.emit(list(probe.issues))

    def _on_probe_failed(self, worker: TaskWorker, text: str):
        if worker is not self._probe_worker:
            return
        self._probe_worker = None
        if self._closing or self._commit_panel is None:
            return
        issue = Issue(Severity.ERROR, "commit.step_failed", f"Commit step failed: {text}")
        self.issues_logged.emit([issue])
        self._commit_panel.apply_probe(CommitProbe(state="unavailable", reason=text))

    def _on_check_again(self):
        """Check again (D-08): take the files as they are now and probe the new plan; it never commits.

        The check only reads, so it takes no Close lock. A running probe or check does not stop it: it
        supersedes that one exactly as _start_probe does and the older result is dropped (IN-03). It is
        refused only while a Switch to main or Commit runs. The plan it returns replaces the dialog's plan.
        """
        panel, cplan = self._commit_panel, self._commit_plan
        if self._closing or self._git_worker is not None:
            return
        if panel is None or cplan is None:
            return
        event = self._begin_probe_generation()
        panel.begin_reprobe()
        core, fp_dir = self._core, self._kicad_fp_dir
        worker = self._spawn(
            lambda progress, cp=cplan, ev=event: core.recheck_commit(cp, kicad_fp_dir=fp_dir, cancelled=ev.is_set)
        )
        self._probe_worker = worker
        worker.result.connect(lambda result, w=worker: self._on_recheck_done(w, result))
        worker.failed.connect(lambda text, w=worker: self._on_probe_failed(w, text))
        worker.start()

    def _on_recheck_done(self, worker: TaskWorker, result: tuple):
        if worker is not self._probe_worker:
            return  # a superseded check
        self._probe_worker = None
        if self._closing or self._commit_panel is None:
            return
        new_plan, probe = result
        self._commit_plan = new_plan
        self._commit_panel.begin_reprobe(new_plan)  # the file list now shows the re-read files
        self._apply_probe_result(probe)

    def _on_open_atomic_check(self, rel_path: str, name: str):
        """Open Check Atomic Parts over this dialog, on the parts the commit check refused (D-07)."""
        if self._closing:
            return
        if self._atomic_dialog is not None:
            self._atomic_dialog.raise_()
            self._atomic_dialog.activateWindow()
            return
        probe = self._commit_probe
        if probe is None or probe.gate is None:
            return
        dialog = AtomicCheckDialog(
            scan_result_for(probe.gate),
            self._repo_root,
            focus=(rel_path, name),
            backup_root=self._atomic_backup_root,
            parent=self,
        )
        dialog.issues_logged.connect(self.issues_logged.emit)
        dialog.applied.connect(self._on_atomic_fixes_applied)
        dialog.finished.connect(self._on_atomic_dialog_finished)
        self._atomic_dialog = dialog
        dialog.open()

    def _on_atomic_fixes_applied(self, issues):
        """Fixes were written from the check dialog: the main window logs and rescans, then the commit is re-checked.

        Only the read-only re-check starts here; a commit always needs its own click (T-11-25).
        """
        self.atomic_fixes_applied.emit(list(issues))
        self._on_check_again()

    def _on_atomic_dialog_finished(self, _result: int):
        dialog, self._atomic_dialog = self._atomic_dialog, None
        if dialog is not None:
            dialog.deleteLater()

    def _on_switch_requested(self):
        """Switch Custom to main on a worker (D-15); only the click on Switch to main gets here."""
        panel, cplan = self._commit_panel, self._commit_plan
        if self._git_worker is not None or self._probe_worker is not None or self._closing or panel is None or cplan is None:
            return
        core = self._core
        panel.set_switching()
        worker = self._spawn(lambda progress, cp=cplan: core.switch_to_main(cp))
        self._set_git_worker(worker)
        worker.result.connect(lambda outcome, w=worker: self._on_switch_done(w, outcome))
        worker.failed.connect(lambda text, w=worker: self._on_switch_failed(w, text))
        worker.start()

    def _on_switch_done(self, worker: TaskWorker, outcome: SwitchOutcome):
        if self._git_worker is worker:
            self._set_git_worker(None)
        if self._closing or self._commit_panel is None:
            return
        self.issues_logged.emit(list(outcome.issues))
        if outcome.ok:
            self._start_probe(reprobe=True)  # the user's message and parent choice stay
            return
        texts = [i.text for i in outcome.issues if i.severity is Severity.ERROR] or [i.text for i in outcome.issues]
        self._commit_panel.show_switch_failed(texts[0] if texts else "git could not switch Custom to main")

    def _on_switch_failed(self, worker: TaskWorker, text: str):
        if self._git_worker is worker:
            self._set_git_worker(None)
        if self._closing or self._commit_panel is None:
            return
        issue = Issue(Severity.ERROR, "commit.step_failed", f"Commit step failed: {text}")
        self.issues_logged.emit([issue])
        self._commit_panel.show_switch_failed(issue.text)

    def _on_commit_file_activated(self, rel: str):
        """An amber file was opened (D-08, D-09, WR-02).

        A file that changed since the install, or that a fix added, shows what it held then against now.
        If it also held changes before this import, one view shows that after it (both are built on one
        worker). Any other amber file shows HEAD against what it held before this import.
        """
        cplan, probe = self._commit_plan, self._commit_probe
        if cplan is None or self._closing:
            return
        core = self._core
        cfile = next((f for f in cplan.files if f.rel == rel), None)
        stale = probe.stale if probe is not None else ()
        marked = cfile is not None and bool(cfile.note or cfile.display in stale)
        dirty = probe is not None and rel in probe.dirty_before
        if marked and dirty:
            self._run_content(
                lambda cp=cplan, r=rel: combined_view(core.changed_diff(cp, r), core.pre_import_diff(cp, r))
            )
        elif marked:
            self._run_content(lambda cp=cplan, r=rel: core.changed_diff(cp, r))
        else:
            self._run_content(lambda cp=cplan, r=rel: core.pre_import_diff(cp, r))

    def _on_commit_requested(self, message: str, bump_parent: bool):
        panel, cplan, probe = self._commit_panel, self._commit_plan, self._commit_probe
        if self._git_worker is not None or self._probe_worker is not None:
            return
        if self._closing or panel is None or cplan is None or probe is None:
            return
        core, fp_dir = self._core, self._kicad_fp_dir
        panel.set_committing()
        # The message goes through exactly as typed (D-20); expected_branch is the branch the probe showed
        worker = self._spawn(
            lambda progress, cp=cplan, m=message, b=bump_parent, br=probe.branch: core.run_commit(
                cp, m, b, expected_branch=br, progress=progress, kicad_fp_dir=fp_dir
            )
        )
        self._set_git_worker(worker)
        worker.progress.connect(self._on_commit_progress)
        worker.result.connect(lambda outcome, w=worker: self._on_commit_done(w, outcome))
        worker.failed.connect(lambda text, w=worker: self._on_commit_failed(w, text))
        worker.start()

    def _on_commit_progress(self, message: str, current: int, total: int):
        if self._commit_panel is not None and self.is_committing():
            self._commit_panel.set_step(message)

    def _on_commit_done(self, worker: TaskWorker, outcome: CommitOutcome):
        if self._git_worker is worker:
            self._set_git_worker(None)
        if self._closing or self._commit_panel is None:
            return
        self._commit_panel.show_outcome(outcome)
        if outcome.issues:
            self.issues_logged.emit(list(outcome.issues))
        # The panel waits for a probe whenever it does not count the outcome as committed (REV-10, D-11):
        # the fresh probe's branch then reaches the next run_commit through _on_commit_requested
        if not self._commit_panel.committed():
            self._start_probe(reprobe=True)

    def _on_commit_failed(self, worker: TaskWorker, text: str):
        issue = Issue(Severity.ERROR, "commit.step_failed", f"Commit step failed: {text}")
        self._on_commit_done(worker, CommitOutcome(issues=(issue,)))

    def _log_not_committed(self):
        """D-02: the user closes the Result view without a Custom commit; one WARNING, no question asked.

        D-14: nothing is left uncommitted when Custom already holds every file; a parent-only bump with a
        parent commit already counts as committed in the panel.
        """
        panel = self._commit_panel
        if panel is None or panel.committed() or self._not_committed_logged:
            return
        if self._commit_probe is not None and self._commit_probe.all_identical:
            return
        self._not_committed_logged = True
        text = "Not committed — commit manually: the imported files stay as uncommitted changes in Custom."
        self.issues_logged.emit([Issue(Severity.WARNING, "commit.not_committed", text)])

    def set_post_install_status(self, row: str, text: str, severity: Severity):
        """Set a status row of the Result view: library_list, tables or generate_hint (D-16, D-17)."""
        self._result_view.set_status(row, text, severity)

    def _start_kicad_check(self, library: str):
        """Look for a running KiCad off the GUI thread; the notice is a best-effort hint (POST-05, D-18)."""
        core = self._core
        worker = self._spawn(lambda progress: core.kicad_running())
        worker.result.connect(lambda names, lib=library: self._on_kicad_running(lib, names))
        worker.failed.connect(lambda text: None)  # a failed check shows nothing and logs nothing
        worker.start()

    def _on_kicad_running(self, library: str, names):
        if self._closing or self._close_pending() or not names:
            return
        text = f"KiCad is running. Reopen KiCad's Symbol and Footprint editors to see {library}."
        self._result_view.set_kicad_running(text)
        self.issues_logged.emit([Issue(Severity.WARNING, "import.kicad_running", text)])

    def _on_written_file_activated(self, path: Path):
        """A Files written row was opened: show what the install wrote, read-only, in the content view (D-15)."""
        plan = self.result_plan
        if plan is None or self._closing:
            return
        op = next((candidate for candidate in plan.ops if candidate.path == path), None)
        if op is None:
            return
        core, repo_root = self._core, self._repo_root
        try:
            rel = path.relative_to(repo_root).as_posix()
        except ValueError:
            rel = path.as_posix()
        # base_sha256 None reads as "a new file": the text the install wrote, or the size and hash of a model
        written = replace(op, base_sha256=None)

        def build() -> ContentText:
            return replace(core.op_content(written, repo_root), title=f"{rel} - written")

        self._run_content(build)

    # -- Change... (D-02): back to the Start page, nothing is asked ------------------

    def _on_change(self):
        """Discard this package and every edit made to it; nothing has been written, so no question.

        A running build is no longer waited for on the GUI thread: the dialog enters Finishing and Change
        runs when the build has ended (D-06), so the package is closed only after it (WR-04).
        _reset_edit_state bumps the generation, so a build result still queued for this package is dropped
        when it arrives.
        """
        if self.is_installing() or self._closing or self._finishing or self._open_worker is not None:
            return
        if self._busy_builds():
            self._enter_finishing("change", self._do_change)
            return
        self._do_change()

    def _do_change(self):
        """Change... after the builds have ended: today's body (the package closes only now, WR-04)."""
        self._building = None
        self._oneoff = None
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
        # Attached model packages are released with the main package: Change..., a new open and close
        models, self._model_packages = self._model_packages, []
        for model_package in models:
            model_package.close()

    def _shutdown(self):
        """Close the package and release everything the dialog holds; idempotent.

        It runs only from _finish_close, which the Finishing gate calls once no worker runs, so no worker is
        joined here and the GUI thread never waits (D-06, T-12-18).
        """
        self._closing = True
        self._end_finishing()  # a pending Change or open is dropped and the wait cursor restored
        for event in self._probe_cancels:
            event.set()
        atomic, self._atomic_dialog = self._atomic_dialog, None
        if atomic is not None:
            atomic.reject()  # a check dialog open over this one closes with it
        self._debounce.stop()
        self._busy_timer.stop()
        self._oneoff_jobs.clear()
        for view in list(self._content_views):
            view.close()
        guide, self._help_dialog = self._help_dialog, None
        if guide is not None:
            guide.close()  # the User Guide this window opened never outlives it
        for worker in list(self._workers):
            value = worker.value
            if isinstance(value, (OpenOutcome, ModelOutcome)):
                value.package.close()  # an open or an attach that finished while closing
                worker.value = None  # released once: a second _shutdown or a queued result finds nothing
        self._discard_package()

    def _finish_close(self, r: int):
        """The close itself, after the last worker has stopped. A method (not a lambda) so super() works when deferred."""
        self._log_not_committed()
        self._shutdown()
        super().done(r)

    def _cancel_probe_for_close(self):
        """Stop the read-only commit probe between git calls, so Finishing lasts at most one git call (IN-02)."""
        if self._probe_worker is None:
            return
        for event in self._probe_cancels:
            event.set()
        self._probe_cancelled_by_close = True

    def _upgrade_to_close(self, r: int):
        """A close asked for while Finishing wins over a pending Change... or open (owner answer 2026-11-01)."""
        self._pending_kind = "close"
        self._pending = functools.partial(self._finish_close, r)
        self._cancel_probe_for_close()
        self._try_finish()

    def done(self, r: int):
        # An install cannot be cancelled: closing waits until it ends (D-10, T-05-33); the same holds
        # for a git job, which may run a slow hook (D-07)
        if self.is_installing() or self.is_committing():
            return
        if self._finishing:
            self._upgrade_to_close(r)
            return
        if self._busy_for("close"):
            # Running workers are not joined on the GUI thread: Finishing, then the close by itself (D-06)
            self._enter_finishing("close", functools.partial(self._finish_close, r))
            self._cancel_probe_for_close()
            return
        self._finish_close(r)

    def keyPressEvent(self, event: QKeyEvent):
        if (self.is_installing() or self.is_committing() or self._finishing) and event.key() == Qt.Key.Key_Escape:
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent):
        if self.is_installing() or self.is_committing():
            event.ignore()
            return
        if self._finishing or self._busy_for("close"):
            # done() defers the close; super().closeEvent would call reject again
            self.done(QDialog.DialogCode.Rejected)
            event.ignore()
            return
        self._log_not_committed()
        self._shutdown()
        super().closeEvent(event)
