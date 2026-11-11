"""The migration window: refusal page, grouped part list, detail pane, strip and Run gating (MIG-01, MIG-02).

Every slow call (git, kicad-cli, the sibling/footprint index, planning, hashing) runs off the GUI
thread on a TaskWorker (reused from import_dialog), tagged with a generation number so only the
latest rebuild result is ever shown - an edit while a rebuild runs supersedes it instead of racing
it onto the screen (D-15). Plans 13-15 and 13-16 extend this file with the footprint/model/family
controls, the Files tab, Run itself and the commit step; this plan only enables the Run button.
"""

import dataclasses
import hashlib
import html
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QRadioButton,
    QScrollArea, QSplitter, QStackedWidget, QTabWidget, QToolBar, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget,
)

from ..importer.content import ContentText, MAX_READ, binary_text, cap_lines, decode_text, diff_text, sha256_file
from ..importer.footprint_index import build_index
from ..importer.form import FIELD_LABELS, TEXT_LABELS, library_badge
from ..importer.layout import RepoLayout
from ..importer.migration.applier import MigrationResult, apply_migration
from ..importer.migration.draft import (
    LoadedDraft,
    changed_parts,
    clear_draft,
    fingerprints,
    load_draft,
    save_draft,
)
from ..importer.migration.gate import GateOutcome, StripLine, check_plan as _gate_check_plan, end_state_context
from ..importer.migration.inventory import Inventory, read_inventory
from ..importer.migration.plan import (
    MigrationChoices,
    MigrationOp,
    MigrationPlan,
    PartChoice,
    PartKey,
    PartPlan,
    PlanContext,
)
from ..importer.migration.planner import build_migration_plan, prepare_context
from ..importer.migration.precheck import check_custom, ensure_tag
from ..importer.plan import FieldChange, Resolution
from ..importer.planner import detect_tools
from ..importer.preview import PreviewRow, PreviewSection
from ..importer.stems import name_verdict
from ..importer.suggest import existing_libraries, suggestion_text
from ..kicad_process import kicad_running
from ..kicad_setup import checkout_mismatch, wrong_checkout_refusal
from ..library_scanner import ConfirmAnswer
from ..models import Issue, Severity
from ..settings import migration_draft_file
from .conflict_row import ConflictRow
from .content_view import ContentViewDialog
from .import_dialog import ADD_MODEL_TEXT, OFFICIAL_FOOTPRINT_TEXT, TaskWorker, fit_window, official_candidates
from .preview_tree import PreviewTree
from .theme import AMBER, AMBER_TINT, ERROR, ERROR_TINT, FIELD_FRAME_QSS, MUTED, PRIMARY_BUTTON_QSS

WINDOW_TITLE = "Migrate to Atomic Libraries"
RUN_TEXT = "Run Migration"
CHECK_AGAIN_TEXT = "Check again"
UNDECIDED_GROUP = "Choose a library"
CHANGED_MARK = "changed since the draft"
PASS_MARK = "✓"
_REBUILD_DELAY_MS = 300
_DRAFT_DELAY_MS = 800

MOVE_FOOTPRINT_TEXT = "Move into Atomic_Footprints"
DERIVE_TEXT = "Make it a derived symbol of {parent}"
FILES_TAB_TEXT = "Files"
LEFTOVERS_TEXT = "Leftover files (ticked ones are deleted)"
PART_TAB_TEXT = "Part"
# Duplicated from import_dialog._OFFICIAL_HINT (private there): the two windows show the same hint
# text but never import a leading-underscore name across modules.
_OFFICIAL_HINT = "KiCad's own footprints are never changed"
_MODEL_EXTS = (".step", ".stp", ".wrl")
_DELETED_HEADER = "Deleted by the migration."
_FOLDER_REMOVED = "Folder removed."
_WRITE_SECTION = "Write"
_MOVE_SECTION = "Move or rename"
_DELETE_SECTION = "Delete"
_RMDIR_SECTION = "Remove folder"

_HELP_TEXT = "Help"
_CLOSE_TEXT = "Close"
_WINDOW_SIZE = QSize(1040, 700)

RUN_REFUSAL_ACTION = "The migration cannot run"
_RUN_FAILED_TITLE = "Migration failed"
_RUN_FAILED_NOT_RESTORED_TITLE = "Migration failed; not everything could be restored"
_RUN_FAILED_RETRY = "Every file was restored."
_KICAD_OPEN_RUN_TEXT = (
    "It may hold the old libraries open; a locked file stops the migration and everything is "
    "restored. Close KiCad, then press Retry."
)
_WRONG_CHECKOUT_RUN_TEXT = "Running it here would rewrite a copy KiCad does not read."


def _plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def _plain_field(name: str) -> str:
    """A field name in words, never the raw ki_ form (D-09, P-14)."""
    lowered = name.lower()
    if lowered in FIELD_LABELS:
        return FIELD_LABELS[lowered]
    if lowered.startswith("ki_"):
        return lowered[3:].replace("_", " ")
    return name


def _field_change_text(change: FieldChange) -> str:
    """One field_changes row in plain words: 'Removed MF', 'Value: old -> new' style (D-09)."""
    label = _plain_field(change.field)
    if change.action == "drop":
        return f"Removed {label}"
    if change.action == "rename":
        return f"Renamed {label} to {_plain_field(change.new)}"
    return f"{label}: {change.old} -> {change.new}"


def _check_plan(plan: MigrationPlan, inventory: Inventory, kicad_fp_dir: Path | None) -> GateOutcome:
    """Build the plan's own end-state context, then judge it; the window never builds AtomicContext itself."""
    ctx = end_state_context(plan, inventory, kicad_fp_dir)
    return _gate_check_plan(plan, inventory, ctx)


def _pick_model_file(parent) -> str:
    """The default pick_model_file: a plain file dialog filtered to the model extensions (D-09, D-15).

    Tests replace this field with a fake so no test ever opens a real system dialog.
    """
    path, _selected_filter = QFileDialog.getOpenFileName(
        parent, "Add 3D model", str(Path.home()), "3D models (*.step *.stp *.wrl)"
    )
    return path


def _ask_kicad_open(parent, names) -> ConfirmAnswer:
    """The default ask_kicad_open: Retry (default) / Run anyway / Cancel (P-13, MIG-01).

    Tests replace this field with a fake so no test ever opens a real modal dialog.
    """
    box = QMessageBox(parent)
    box.setWindowModality(Qt.WindowModality.WindowModal)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle("KiCad is open")
    box.setText(f"KiCad is open ({', '.join(names)}). {_KICAD_OPEN_RUN_TEXT}")
    retry = box.addButton("Retry", QMessageBox.ButtonRole.AcceptRole)
    anyway = box.addButton("Run anyway", QMessageBox.ButtonRole.DestructiveRole)
    cancel = box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(retry)
    box.setEscapeButton(cancel)
    box.exec()
    clicked = box.clickedButton()
    if clicked is retry:
        return ConfirmAnswer.RETRY
    if clicked is anyway:
        return ConfirmAnswer.WRITE
    return ConfirmAnswer.DECLINE


def _is_model_rel(rel: str) -> bool:
    return rel.lower().endswith(_MODEL_EXTS)


def _read_capped(path: Path) -> bytes:
    """Read at most content.MAX_READ + 1 bytes, raising OSError past the cap (never a partial file, T-13-36)."""
    with open(path, "rb") as handle:
        data = handle.read(MAX_READ + 1)
    if len(data) > MAX_READ:
        raise OSError(f"the file is larger than {MAX_READ} bytes")
    return data


def op_content(op: MigrationOp, repo_root: Path) -> ContentText:
    """Qt-free text for one planned MigrationOp (D-15, T-13-36): a diff, new text, a binary summary, or the
    deleted/removed text.

    A model (.step/.stp/.wrl) is only ever sized and hashed, never decoded; every disk read is capped by
    content.MAX_READ. Always run on a worker thread - hashing a large STEP file is slow.
    """
    rel = op.rel
    path = repo_root / rel
    if op.kind == "rmdir":
        return ContentText(title=f"{rel} - removed", header=rel, body=_FOLDER_REMOVED, kind="text")
    if op.kind == "delete":
        if _is_model_rel(rel):
            try:
                size, sha = sha256_file(path)
                body = f"{_DELETED_HEADER}\n\n{binary_text(Path(rel).name, size, sha)}"
            except OSError:
                body = _DELETED_HEADER
            return ContentText(title=f"{rel} - deleted", header=rel, body=body, kind="binary")
        try:
            data = _read_capped(path)
        except OSError:
            data = b""
        body = f"{_DELETED_HEADER}\n\n{decode_text(data)}"
        return ContentText(title=f"{rel} - deleted", header=rel, body=body, kind="text")
    # write (new or modified)
    data = op.data or b""
    if _is_model_rel(rel):
        sha = hashlib.sha256(data).hexdigest()
        existing = None
        if op.base_sha256 is not None:
            try:
                existing = sha256_file(path)
            except OSError:
                existing = None
        suffix = " - new" if op.base_sha256 is None else " - changes"
        body = binary_text(Path(rel).name, len(data), sha, existing)
        return ContentText(title=f"{rel}{suffix}", header=rel, body=body, kind="binary")
    if op.base_sha256 is None:
        body = "\n".join(cap_lines(decode_text(data).splitlines()))
        return ContentText(title=f"{rel} - new file", header=rel, body=body, kind="text")
    try:
        old = _read_capped(path)
    except OSError as e:
        return ContentText(
            title=f"{rel} - changes", header=rel, body=f"Could not read {rel}: {e.strerror or e}.", kind="error",
        )
    if old == data:
        return ContentText(title=f"{rel} - unchanged", header=rel, body="This file is unchanged.", kind="unchanged")
    body = diff_text(old, data, f"{rel} (current)", f"{rel} (planned)")
    return ContentText(title=f"{rel} - changes", header=rel, body=body, kind="diff")


@dataclass(frozen=True)
class MigrationCore:
    """The migration functions the dialog calls; tests replace single fields with fakes."""

    check_custom: object = check_custom
    read_inventory: object = read_inventory
    detect_tools: object = detect_tools
    prepare_context: object = prepare_context
    build_plan: object = build_migration_plan
    check_plan: object = _check_plan
    fingerprints: object = fingerprints
    load_draft: object = load_draft
    save_draft: object = save_draft
    clear_draft: object = clear_draft
    changed_parts: object = changed_parts
    draft_file: object = migration_draft_file
    kicad_running: object = kicad_running
    footprint_index: object = build_index
    official_candidates: object = official_candidates
    op_content: object = op_content
    pick_model_file: object = _pick_model_file
    apply: object = apply_migration
    ensure_tag: object = ensure_tag
    checkout_mismatch: object = checkout_mismatch
    ask_kicad_open: object = _ask_kicad_open


@dataclass(frozen=True)
class _LoadOutcome:
    """What the load worker hands to the GUI thread: the inventory, the plan context and the draft."""

    inventory: Inventory
    ctx: PlanContext
    prints: dict
    loaded: "LoadedDraft | Issue"


class MigrationDialog(QDialog):
    """Non-modal migration window. Opens to a refusal page or the grouped, gated part list (D-15, D-25)."""

    help_requested = Signal()
    migrated = Signal(object)
    generate_requested = Signal()
    setup_chooser_requested = Signal()
    issues_logged = Signal(list)
    atomic_check_requested = Signal(str, str)

    def __init__(
        self,
        repo_root: Path,
        kicad_fp_dir: Path | None,
        *,
        core: "MigrationCore | None" = None,
        parent=None,
    ):
        super().__init__(parent)
        self._repo_root = Path(repo_root)
        self._kicad_fp_dir = kicad_fp_dir
        self._core = core or MigrationCore()
        self._layout = RepoLayout.for_repo(self._repo_root)

        self.setWindowTitle(WINDOW_TITLE)

        self._inventory: Inventory | None = None
        self._ctx: PlanContext | None = None
        self._prints: dict[PartKey, str] = {}
        self._raw_fields: dict[PartKey, dict] = {}
        self._choices = MigrationChoices()
        self._changed: frozenset[PartKey] = frozenset()
        self._plan: MigrationPlan | None = None
        self._gate: GateOutcome | None = None
        self._gen = 0
        self._plan_gen = -1
        self._current_key: PartKey | None = None
        self._targets: dict[str, QWidget] = {}
        self._workers: list[TaskWorker] = []
        self._content_views: list[ContentViewDialog] = []
        self._closing = False
        self._pending_result: int | None = None
        self._running = False
        self._run_worker: TaskWorker | None = None

        self._rebuild_timer = QTimer(self)
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.setInterval(_REBUILD_DELAY_MS)
        self._rebuild_timer.timeout.connect(self._start_rebuild)

        self._draft_timer = QTimer(self)
        self._draft_timer.setSingleShot(True)
        self._draft_timer.setInterval(_DRAFT_DELAY_MS)
        self._draft_timer.timeout.connect(self._start_save_draft)

        outer = QVBoxLayout(self)
        self._build_toolbar(outer)
        self._stack = QStackedWidget()
        outer.addWidget(self._stack)

        self._checking_page = self._build_checking_page()
        self._refusal_page = self._build_refusal_page()
        self._loading_page = self._build_loading_page()
        self._edit_page = self._build_edit_page()
        self._running_page = self._build_running_page()
        for page in (
            self._checking_page, self._refusal_page, self._loading_page, self._edit_page,
            self._running_page,
        ):
            self._stack.addWidget(page)
        self._stack.setCurrentWidget(self._checking_page)

        self.resize(_WINDOW_SIZE)
        fit_window(self, _WINDOW_SIZE)
        QTimer.singleShot(0, self._start_check)

    # -- status --------------------------------------------------------------

    def is_running(self) -> bool:
        """True while Run itself is applying the migration (MIG-01, MIG-03)."""
        return self._running

    def is_committing(self) -> bool:
        """True while the parent commit runs (plan 13-16 Task 2 fills this in)."""
        return False

    def is_busy(self) -> bool:
        return self.is_running() or self.is_committing() or any(w.isRunning() for w in self._workers)

    # -- toolbar and pages ----------------------------------------------------

    def _build_toolbar(self, outer: QVBoxLayout):
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        action = QAction(_HELP_TEXT, self)
        action.setShortcut(QKeySequence("F1"))
        action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        action.triggered.connect(self.help_requested.emit)
        toolbar.addAction(action)
        outer.addWidget(toolbar)

    def _build_checking_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        self._checking_label = QLabel("Checking Custom for uncommitted changes...")
        self._checking_label.setTextFormat(Qt.TextFormat.PlainText)
        lay.addWidget(self._checking_label)
        lay.addStretch()
        return page

    def _build_refusal_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        self._refusal_text = QPlainTextEdit()
        self._refusal_text.setReadOnly(True)
        lay.addWidget(self._refusal_text, 1)
        buttons = QHBoxLayout()
        buttons.addStretch()
        self._check_again_btn = QPushButton(CHECK_AGAIN_TEXT)
        self._check_again_btn.clicked.connect(self._start_check)
        buttons.addWidget(self._check_again_btn)
        close_btn = QPushButton(_CLOSE_TEXT)
        close_btn.clicked.connect(self.reject)
        buttons.addWidget(close_btn)
        lay.addLayout(buttons)
        return page

    def _build_loading_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        self._loading_label = QLabel("Reading Custom...")
        self._loading_label.setTextFormat(Qt.TextFormat.PlainText)
        lay.addWidget(self._loading_label)
        lay.addStretch()
        return page

    def _build_running_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        self._running_label = QLabel("Starting the migration...")
        self._running_label.setTextFormat(Qt.TextFormat.PlainText)
        lay.addWidget(self._running_label)
        lay.addStretch()
        return page

    def _build_run_failure_banner(self, lay: QVBoxLayout):
        """A failed Run's reasons, in the same style as the import dialog's failure banner (D-15)."""
        banner = QFrame()
        banner.setObjectName("runFailureBanner")
        banner.setStyleSheet(
            f"QFrame#runFailureBanner {{ background-color: {ERROR_TINT}; border-left: 2px solid {ERROR}; }}"
        )
        outer = QHBoxLayout(banner)
        column = QVBoxLayout()
        title = QLabel()
        title.setTextFormat(Qt.TextFormat.PlainText)
        title.setWordWrap(True)
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet(f"color: {ERROR};")
        column.addWidget(title)
        body = QPlainTextEdit()
        body.setReadOnly(True)
        body.setFrameShape(QFrame.Shape.NoFrame)
        body.setMaximumHeight(120)
        column.addWidget(body)
        outer.addLayout(column, 1)
        dismiss = QPushButton("✕")
        dismiss.setToolTip("Dismiss")
        dismiss.clicked.connect(banner.hide)
        outer.addWidget(dismiss, alignment=Qt.AlignmentFlag.AlignTop)
        banner.hide()
        lay.addWidget(banner)
        self._run_failure_banner, self._run_failure_title, self._run_failure_body = banner, title, body

    def _build_edit_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)

        self._build_run_failure_banner(lay)

        self._strip = QListWidget()
        self._strip.setStyleSheet(f"QListWidget {{ background-color: {AMBER_TINT}; border: none; }}")
        self._strip.itemClicked.connect(self._on_strip_item_clicked)
        self._strip.setVisible(False)
        lay.addWidget(self._strip)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._tree = QTreeWidget()
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(["Part", "Status"])
        self._tree.currentItemChanged.connect(self._on_tree_selection)
        splitter.addWidget(self._tree)

        self._tabs = QTabWidget()
        self._part_tab = self._build_part_tab()
        self._tabs.addTab(self._part_tab, PART_TAB_TEXT)
        self._files_tab = self._build_files_tab()
        self._tabs.addTab(self._files_tab, FILES_TAB_TEXT)
        splitter.addWidget(self._tabs)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        lay.addWidget(splitter, 1)

        bottom = QHBoxLayout()
        self._status_label = QLabel()
        self._status_label.setTextFormat(Qt.TextFormat.PlainText)
        bottom.addWidget(self._status_label, 1)
        self._run_btn = QPushButton(RUN_TEXT)
        self._run_btn.setStyleSheet(PRIMARY_BUTTON_QSS)
        self._run_btn.setEnabled(False)
        self._run_btn.clicked.connect(self._on_run)
        bottom.addWidget(self._run_btn)
        close_btn = QPushButton(_CLOSE_TEXT)
        close_btn.clicked.connect(self.reject)
        bottom.addWidget(close_btn)
        lay.addLayout(bottom)
        return page

    def _framed(self, widget: QWidget, key: str) -> QFrame:
        """Wrap a blockable control in a QFrame#fieldFrame and register it as a strip-click target."""
        frame = QFrame()
        frame.setObjectName("fieldFrame")
        frame.setStyleSheet(FIELD_FRAME_QSS)
        frame.setProperty("blocked", False)
        frame_lay = QVBoxLayout(frame)
        frame_lay.setContentsMargins(0, 0, 0, 0)
        frame_lay.addWidget(widget)
        self._targets[key] = widget
        return frame

    def _build_part_tab(self) -> QWidget:
        """The detail pane (D-15): the minimal fields Task 1 needs; plan 13-14 Task 2 fills it out."""
        page = QWidget()
        outer = QVBoxLayout(page)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self._changed_label = QLabel()
        self._changed_label.setTextFormat(Qt.TextFormat.PlainText)
        self._changed_label.setStyleSheet(f"color: {AMBER}; font-weight: bold;")
        self._changed_label.hide()
        form.addRow(self._changed_label)

        self._library_combo = QComboBox()
        self._library_combo.setEditable(True)
        self._library_combo.lineEdit().textEdited.connect(self._on_library_edited)
        form.addRow("Library", self._framed(self._library_combo, "library"))
        self._library_badge = QLabel()
        self._library_badge.setTextFormat(Qt.TextFormat.PlainText)
        self._library_badge.setStyleSheet(f"color: {MUTED};")
        form.addRow("", self._library_badge)
        self._library_note = QLabel()
        self._library_note.setTextFormat(Qt.TextFormat.PlainText)
        self._library_note.setWordWrap(True)
        self._library_note.setStyleSheet(f"color: {MUTED};")
        self._library_note.hide()
        form.addRow("", self._library_note)

        self._symbol_name_edit = QLineEdit()
        self._symbol_name_edit.textEdited.connect(lambda text: self._on_field_edited("symbol_name", text))
        form.addRow("Symbol name", self._framed(self._symbol_name_edit, "symbol_name"))

        self._field_edits: dict[str, QLineEdit] = {}
        for name, label in (
            ("mpn", "MPN"),
            ("manufacturer", "Manufacturer"),
            ("datasheet", "Datasheet"),
            ("description", "Description"),
        ):
            edit = QLineEdit()
            edit.textEdited.connect(lambda text, n=name: self._on_field_edited(n, text))
            form.addRow(label, self._framed(edit, name))
            self._field_edits[name] = edit

        self._value_edit = QLineEdit()
        self._value_edit.setReadOnly(True)
        self._value_edit.setToolTip("Value follows the MPN")
        form.addRow("Value", self._value_edit)

        self._field_changes_list = QListWidget()
        self._field_changes_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        form.addRow("Field changes", self._field_changes_list)

        self._build_footprint_section(form)
        self._build_model_row(form)
        self._build_conflict_rows_host(form)
        self._build_derive_box(form)

        self._text_edits: dict[str, QPlainTextEdit] = {}
        self._text_regenerate: dict[str, QPushButton] = {}
        for name, label in TEXT_LABELS.items():
            edit = QPlainTextEdit()
            edit.setMaximumHeight(60)
            edit.textChanged.connect(lambda n=name: self._on_text_changed(n))
            row = QWidget()
            row_lay = QHBoxLayout(row)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.addWidget(self._framed(edit, name), 1)
            regenerate = QPushButton("Regenerate")
            regenerate.clicked.connect(lambda _checked=False, n=name: self._on_regenerate(n))
            row_lay.addWidget(regenerate)
            form.addRow(label, row)
            self._text_edits[name] = edit
            self._text_regenerate[name] = regenerate

        scroll.setWidget(inner)
        outer.addWidget(scroll)
        return page

    def _build_footprint_section(self, form: QFormLayout):
        """Move into Atomic_Footprints or switch to an official KiCad footprint (D-08, D-07)."""
        self._fp_move_radio = QRadioButton(MOVE_FOOTPRINT_TEXT)
        self._fp_official_radio = QRadioButton(OFFICIAL_FOOTPRINT_TEXT)
        self._fp_move_radio.setChecked(True)
        self._fp_target_group = QButtonGroup(self)
        self._fp_target_group.addButton(self._fp_move_radio)
        self._fp_target_group.addButton(self._fp_official_radio)
        radios = QWidget()
        radios_lay = QVBoxLayout(radios)
        radios_lay.setContentsMargins(0, 0, 0, 0)
        radios_lay.addWidget(self._fp_move_radio)
        radios_lay.addWidget(self._fp_official_radio)
        form.addRow("Footprint", radios)
        self._fp_official_radio.toggled.connect(self._on_fp_target_toggled)

        self._fp_name_edit = QLineEdit()
        self._fp_name_edit.textEdited.connect(lambda text: self._on_field_edited("footprint_name", text))
        form.addRow("Name", self._framed(self._fp_name_edit, "footprint"))

        box = QWidget()
        box_lay = QVBoxLayout(box)
        box_lay.setContentsMargins(0, 0, 0, 0)
        self._official_combo = QComboBox()
        self._official_combo.setEditable(True)
        self._official_combo.lineEdit().textEdited.connect(self._on_official_text_edited)
        self._official_combo.textActivated.connect(self._on_official_activated)
        box_lay.addWidget(self._official_combo)
        self._pad_warning_label = QLabel()
        self._pad_warning_label.setTextFormat(Qt.TextFormat.PlainText)
        self._pad_warning_label.setWordWrap(True)
        self._pad_warning_label.setStyleSheet(f"color: {AMBER};")
        self._pad_warning_label.hide()
        box_lay.addWidget(self._pad_warning_label)
        self._official_hint_label = QLabel(_OFFICIAL_HINT)
        self._official_hint_label.setTextFormat(Qt.TextFormat.PlainText)
        self._official_hint_label.setWordWrap(True)
        self._official_hint_label.setStyleSheet(f"color: {MUTED};")
        box_lay.addWidget(self._official_hint_label)
        box.hide()
        self._official_box = box
        form.addRow("", box)

    # -- the official-footprint picker (D-08, D-16) ----------------------------

    def _vendor_footprint_path(self, part: PartPlan) -> Path | None:
        """The part's current Custom footprint file, for the pad-fit ranking; None when it cannot be found."""
        library, _sep, name = part.footprint_old.partition(":")
        if not library or not name:
            return None
        path = self._layout.footprints_dir / f"{library}.pretty" / f"{name}.kicad_mod"
        return path if path.exists() else None

    def _start_official_list(self):
        part = self._part_by_key(self._current_key)
        if part is None:
            return
        folder = self._kicad_fp_dir
        core = self._core
        code = part.footprint_old.rpartition(":")[-1]
        vendor_path = self._vendor_footprint_path(part)

        def task(progress):
            return core.official_candidates(
                core.footprint_index, folder, package_code=code, vendor_path=vendor_path,
                stock=getattr(self._ctx, "stock", None), part=part.mpn, progress=progress,
            )

        worker = self._spawn(task)
        worker.result.connect(self._on_official_list_ready)
        worker.start()

    def _on_official_list_ready(self, links: list[str]):
        combo = self._official_combo
        typed = combo.currentText()
        combo.blockSignals(True)
        try:
            combo.clear()
            combo.addItems(links)
            combo.setCurrentIndex(-1)
            combo.setEditText(typed)
        finally:
            combo.blockSignals(False)

    def _on_fp_target_toggled(self, checked: bool):
        if self._current_key is None:
            return
        self._official_box.setVisible(checked)
        if checked:
            self._update_choice(self._current_key, footprint_target="official")
            self._start_official_list()
        else:
            self._update_choice(self._current_key, footprint_target="shared", official_footprint=None)

    def _on_official_activated(self, text: str):
        if self._current_key is None:
            return
        self._update_choice(self._current_key, official_footprint=text)

    def _on_official_text_edited(self, text: str):
        if self._current_key is None:
            return
        self._update_choice(self._current_key, official_footprint=text)

    # -- the 3D model row (D-09, D-15, D-23) -----------------------------------

    def _build_model_row(self, form: QFormLayout):
        """One editable name for a single model, read-only names for several, or Add 3D model... (D-23)."""
        self._model_stack = QStackedWidget()

        self._model_name_edit = QLineEdit()
        self._model_name_edit.textEdited.connect(lambda text: self._on_field_edited("model_name", text))
        self._model_stack.addWidget(self._framed(self._model_name_edit, "model_name"))

        self._model_list = QListWidget()
        self._model_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._model_stack.addWidget(self._model_list)

        add_row = QWidget()
        add_lay = QHBoxLayout(add_row)
        add_lay.setContentsMargins(0, 0, 0, 0)
        self._add_model_btn = QPushButton(ADD_MODEL_TEXT)
        self._add_model_btn.clicked.connect(self._on_pick_model)
        add_lay.addWidget(self._framed(self._add_model_btn, "model"))
        self._remove_model_btn = QPushButton("Remove")
        self._remove_model_btn.clicked.connect(self._on_remove_model)
        add_lay.addWidget(self._remove_model_btn)
        self._model_stack.addWidget(add_row)

        form.addRow("3D model", self._model_stack)

    def _on_pick_model(self):
        if self._current_key is None:
            return
        path = self._core.pick_model_file(self)
        if not path:
            return
        self._update_choice(self._current_key, model_source=path)

    def _on_remove_model(self):
        if self._current_key is None:
            return
        self._update_choice(self._current_key, model_source=None)

    def _display_model(self, part: PartPlan, choice: PartChoice):
        models = part.model_files
        if len(models) == 1:
            self._model_stack.setCurrentIndex(0)
            self._model_name_edit.blockSignals(True)
            default_name = models[0]
            self._model_name_edit.setText(choice.model_name if choice.model_name is not None else default_name)
            self._model_name_edit.blockSignals(False)
            self._targets["model"] = self._model_name_edit
        elif len(models) >= 2:
            self._model_stack.setCurrentIndex(1)
            self._model_list.clear()
            for name in models:
                self._model_list.addItem(name)
            self._targets["model"] = self._model_list
        else:
            self._model_stack.setCurrentIndex(2)
            self._remove_model_btn.setVisible(bool(choice.model_source))
            self._targets["model"] = self._add_model_btn

    # -- the Atomic_Footprints clash rows for the selected part (D-07) ---------

    def _build_conflict_rows_host(self, form: QFormLayout):
        self._conflict_rows_host = QWidget()
        self._conflict_rows_layout = QVBoxLayout(self._conflict_rows_host)
        self._conflict_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._conflict_rows: dict[str, ConflictRow] = {}
        self._conflict_rows_host.hide()
        form.addRow("Clashes", self._conflict_rows_host)

    def _conflicts_for_part(self, part: PartPlan) -> list:
        if self._plan is None:
            return []
        stems = {part.footprint_new.rpartition(":")[-1], part.footprint_old.rpartition(":")[-1]}
        return [c for c in self._plan.conflicts if c.kind == "footprint" and c.name in stems]

    def _display_conflicts(self, part: PartPlan):
        wanted = {c.key: c for c in self._conflicts_for_part(part)}
        for key in [k for k in self._conflict_rows if k not in wanted]:
            self._remove_conflict_row(key)
        for key, conflict in wanted.items():
            row = self._conflict_rows.get(key)
            if row is None:
                row = self._add_conflict_row(conflict)
            else:
                row.update_conflict(conflict)
            resolution = self._choices.resolutions.get(key)
            if row.current_resolution() != resolution:
                row.set_resolution(resolution)
        self._conflict_rows_host.setVisible(bool(wanted))

    def _add_conflict_row(self, conflict) -> ConflictRow:
        key = conflict.key
        row = ConflictRow(conflict)
        row.choice_changed.connect(self._on_conflict_choice)
        row.rename_edited.connect(self._on_conflict_rename)
        self._conflict_rows[key] = row
        self._conflict_rows_layout.addWidget(row)
        self._targets[f"conflict:{key}"] = row.overwrite_button
        self._targets[f"rename:{key}"] = row.rename_edit
        return row

    def _remove_conflict_row(self, key: str):
        row = self._conflict_rows.pop(key)
        for target in (f"conflict:{key}", f"rename:{key}"):
            self._targets.pop(target, None)
        self._conflict_rows_layout.removeWidget(row)
        row.hide()
        row.setParent(None)
        row.deleteLater()

    def _update_resolutions(self, resolutions: dict):
        self._choices = dataclasses.replace(self._choices, resolutions=resolutions)
        self._gen += 1
        self._rebuild_timer.start(_REBUILD_DELAY_MS)
        self._draft_timer.start(_DRAFT_DELAY_MS)

    def _on_conflict_choice(self, key: str, resolution: "Resolution | None"):
        resolutions = dict(self._choices.resolutions)
        if resolution is None:
            resolutions.pop(key, None)
        else:
            resolutions[key] = resolution
        self._update_resolutions(resolutions)

    def _on_conflict_rename(self, key: str, text: str):
        resolutions = dict(self._choices.resolutions)
        resolutions[key] = Resolution("rename", text)
        self._update_resolutions(resolutions)

    # -- the derive-as-family-member check box (D-06) -------------------------

    def _build_derive_box(self, form: QFormLayout):
        self._derive_check = QCheckBox()
        self._derive_check.toggled.connect(self._on_derive_toggled)
        self._derive_check.hide()
        form.addRow("", self._framed(self._derive_check, "derive"))

    def _family_row_for(self, part: PartPlan):
        if self._plan is None:
            return None
        return next((row for row in self._plan.families if row.member == part.key), None)

    def _display_derive(self, part: PartPlan, choice: PartChoice):
        family = self._family_row_for(part)
        if family is None:
            self._derive_check.setVisible(False)
            return
        parent_part = self._part_by_key(family.parent)
        parent_name = parent_part.new_name if parent_part is not None else family.parent[1]
        self._derive_check.setText(DERIVE_TEXT.format(parent=parent_name))
        self._derive_check.setVisible(True)
        self._derive_check.blockSignals(True)
        self._derive_check.setChecked(choice.derive)
        self._derive_check.blockSignals(False)

    def _on_derive_toggled(self, checked: bool):
        if self._current_key is None:
            return
        self._update_choice(self._current_key, derive=checked)

    # -- precheck (MIG-01, D-02) ----------------------------------------------

    def _spawn(self, fn, tag=None) -> TaskWorker:
        worker = TaskWorker(fn, parent=self, tag=tag)
        self._workers.append(worker)
        worker.finished.connect(lambda w=worker: self._reap(w))
        return worker

    def _reap(self, worker: TaskWorker):
        worker.wait(2000)
        if self._closing and not any(w.isRunning() for w in self._workers if w is not worker):
            self._closing = False
            pending = self._pending_result
            self._pending_result = None
            QDialog.done(self, pending if pending is not None else int(QDialog.DialogCode.Rejected))

    def _start_check(self):
        self._show_page(self._checking_page)

        def task(progress):
            return self._core.check_custom(self._layout.custom_dir, self._repo_root)

        worker = self._spawn(task)
        worker.result.connect(self._on_checked)
        worker.start()

    def _on_checked(self, precheck):
        if not precheck.ok:
            text = "\n\n".join(issue.text for issue in precheck.issues)
            self._refusal_text.setPlainText(text)
            self._show_page(self._refusal_page)
            return
        self._start_load()

    # -- loading the inventory, the plan context and the draft (D-14) --------

    def _start_load(self):
        self._show_page(self._loading_page)

        def task(progress):
            inventory = self._core.read_inventory(self._layout)
            tools = self._core.detect_tools(self._kicad_fp_dir)
            ctx = self._core.prepare_context(inventory, tools, self._kicad_fp_dir, progress=progress)
            prints = self._core.fingerprints(inventory)
            loaded = self._core.load_draft(self._core.draft_file(self._repo_root), self._repo_root)
            return _LoadOutcome(inventory, ctx, prints, loaded)

        worker = self._spawn(task)
        worker.progress.connect(self._on_load_progress)
        worker.result.connect(self._on_loaded)
        worker.start()

    def _on_load_progress(self, message: str, current: int, total: int):
        self._loading_label.setText(message)

    def _on_loaded(self, outcome: _LoadOutcome):
        self._inventory = outcome.inventory
        self._ctx = outcome.ctx
        self._prints = outcome.prints
        self._raw_fields = {part.key: part.fields for part in outcome.inventory.parts}
        if isinstance(outcome.loaded, LoadedDraft):
            self._choices = outcome.loaded.choices
            self._changed = self._core.changed_parts(outcome.loaded, self._prints)
        else:
            self._choices = MigrationChoices()
            self._changed = frozenset()
            if outcome.loaded.code != "draft.none":
                self._status_label.setText(outcome.loaded.text)
        self._show_page(self._edit_page)
        self._start_rebuild()

    # -- the rebuild coordinator (D-15): latest edit wins ---------------------

    def _start_rebuild(self):
        gen = self._gen

        def task(progress):
            plan = self._core.build_plan(self._inventory, self._choices, self._ctx)
            outcome = self._core.check_plan(plan, self._inventory, self._kicad_fp_dir)
            return (plan, outcome)

        worker = self._spawn(task, tag=gen)
        worker.result.connect(lambda result, g=gen: self._on_rebuilt(g, result))
        worker.start()

    def _on_rebuilt(self, gen: int, result):
        if gen != self._gen:
            return  # a newer edit has already superseded this result
        self._plan, self._gate = result
        self._plan_gen = gen
        self._populate_tree()
        self._render_strip(self._gate.lines)
        self._files_tree.render(self._files_sections(self._plan))
        self._populate_leftovers(self._plan.leftovers)
        if self._current_key is None and self._plan.parts:
            self._select_part(self._plan.parts[0].key)
        else:
            part = self._part_by_key(self._current_key)
            if part is not None:
                self._display_part(part)
        self._update_run_state()

    def _update_run_state(self):
        ready = self._plan_gen == self._gen and self._gate is not None and self._gate.run_enabled
        self._run_btn.setEnabled(bool(ready))

    def _update_choice(self, key: PartKey, **fields):
        parts = dict(self._choices.parts)
        current = parts.get(key, PartChoice())
        parts[key] = dataclasses.replace(current, **fields)
        self._choices = dataclasses.replace(self._choices, parts=parts)
        self._gen += 1
        self._rebuild_timer.start(_REBUILD_DELAY_MS)
        self._draft_timer.start(_DRAFT_DELAY_MS)

    def _start_save_draft(self):
        choices = self._choices
        prints = self._prints

        def task(progress):
            return self._core.save_draft(self._core.draft_file(self._repo_root), self._repo_root, choices, prints)

        worker = self._spawn(task)
        worker.result.connect(self._on_draft_saved)
        worker.start()

    def _on_draft_saved(self, issue):
        if isinstance(issue, Issue):
            self._status_label.setText(issue.text)

    def _on_field_edited(self, name: str, text: str):
        if self._current_key is None:
            return
        self._update_choice(self._current_key, **{name: text})

    def _on_library_edited(self, text: str):
        self._on_field_edited("library", text)
        allowed = getattr(self._ctx, "allowed", None)
        verdict = name_verdict(text, allowed)
        self._library_note.setText("" if verdict.ok else verdict.reason)
        self._library_note.setVisible(not verdict.ok)
        self._library_badge.setText(library_badge(text, self._library_names(), allowed))

    def _on_text_changed(self, name: str):
        if self._current_key is None:
            return
        edit = self._text_edits[name]
        self._update_choice(self._current_key, **{name: edit.toPlainText()})

    def _on_regenerate(self, name: str):
        if self._current_key is None:
            return
        self._update_choice(self._current_key, **{name: None})

    # -- the part tree, grouped by target library (D-15) ----------------------

    def _part_by_key(self, key: PartKey | None) -> PartPlan | None:
        if self._plan is None or key is None:
            return None
        return next((part for part in self._plan.parts if part.key == key), None)

    def _status_text(self, part: PartPlan) -> str:
        count = self._gate.failing.get(part.key, 0) if self._gate is not None else 0
        bits = [PASS_MARK if count == 0 else _plural(count, "problem", "problems")]
        if part.target_library and part.source_library != part.target_library:
            bits.append(f"from {part.source_library}")
        if part.key in self._changed:
            bits.append(CHANGED_MARK)
        return " · ".join(bits)

    def _populate_tree(self):
        self._tree.blockSignals(True)
        try:
            self._tree.clear()
            groups: dict[str, list[PartPlan]] = {}
            for part in self._plan.parts if self._plan is not None else ():
                groups.setdefault(part.target_library or UNDECIDED_GROUP, []).append(part)
            names = sorted(groups, key=lambda n: (n != UNDECIDED_GROUP, n.casefold(), n))
            for name in names:
                group_item = QTreeWidgetItem([name, ""])
                group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self._tree.addTopLevelItem(group_item)
                for part in sorted(groups[name], key=lambda p: (p.new_name.casefold(), p.new_name)):
                    item = QTreeWidgetItem([part.new_name, self._status_text(part)])
                    item.setData(0, Qt.ItemDataRole.UserRole, part.key)
                    choice = self._choices.parts.get(part.key)
                    override = choice.description if choice is not None else None
                    raw_description = self._raw_fields.get(part.key, {}).get("Description", "")
                    description = override if override is not None else raw_description
                    item.setToolTip(0, html.escape(description))
                    group_item.addChild(item)
            self._tree.expandAll()
        finally:
            self._tree.blockSignals(False)

    def _select_part(self, key: PartKey):
        for i in range(self._tree.topLevelItemCount()):
            group = self._tree.topLevelItem(i)
            for j in range(group.childCount()):
                item = group.child(j)
                if item.data(0, Qt.ItemDataRole.UserRole) == key:
                    self._tree.setCurrentItem(item)
                    return

    def _on_tree_selection(self, current: "QTreeWidgetItem | None", previous):
        if current is None:
            return
        key = current.data(0, Qt.ItemDataRole.UserRole)
        if key is None:
            return  # a group header
        part = self._part_by_key(key)
        if part is not None:
            self._display_part(part)

    # -- the failure strip (D-15, MIG-02) -------------------------------------

    def _render_strip(self, lines: tuple):
        self._strip.clear()
        for line in lines:
            item = QListWidgetItem(line.text)
            item.setData(Qt.ItemDataRole.UserRole, line)
            self._strip.addItem(item)
        self._strip.setVisible(bool(lines))
        if lines:
            row_height = self._strip.sizeHintForRow(0)
            if row_height > 0:
                self._strip.setMaximumHeight(row_height * min(len(lines), 6) + 2 * self._strip.frameWidth())

    def _on_strip_item_clicked(self, item: QListWidgetItem):
        line: StripLine = item.data(Qt.ItemDataRole.UserRole)
        if line.key is not None:
            self._select_part(line.key)
            self._tabs.setCurrentWidget(self._part_tab)
        widget = self._targets.get(line.target) if line.target else None
        if widget is not None:
            widget.setFocus(Qt.FocusReason.OtherFocusReason)

    # -- displaying one part in the detail pane -------------------------------

    def _library_names(self) -> list[str]:
        """The existing Atomic_ libraries of the current plan, for the library picker's list (D-03)."""
        names = {p.target_library for p in (self._plan.parts if self._plan is not None else ()) if p.target_library}
        allowed = getattr(self._ctx, "allowed", None)
        return existing_libraries(names, allowed)

    def _display_part(self, part: PartPlan):
        self._current_key = part.key
        choice = self._choices.parts.get(part.key, PartChoice())
        raw = self._raw_fields.get(part.key, {})
        allowed = getattr(self._ctx, "allowed", None)

        self._changed_label.setText(CHANGED_MARK if part.key in self._changed else "")
        self._changed_label.setVisible(part.key in self._changed)

        self._library_combo.blockSignals(True)
        library_text = choice.library if choice.library is not None else (
            part.target_library or (part.suggestion.name if part.suggestion is not None else "")
        )
        names = self._library_names()
        if part.source_library and part.source_library not in names:
            names = sorted({*names, part.source_library}, key=lambda n: (n.casefold(), n))
        self._library_combo.clear()
        self._library_combo.addItems(names)
        self._library_combo.setEditText(library_text)
        self._library_combo.setToolTip(suggestion_text(part.suggestion) if part.suggestion is not None else "")
        self._library_combo.blockSignals(False)
        verdict = name_verdict(library_text, allowed)
        self._library_note.setText("" if verdict.ok else verdict.reason)
        self._library_note.setVisible(not verdict.ok)
        self._library_badge.setText(library_badge(library_text, names, allowed))

        self._symbol_name_edit.blockSignals(True)
        self._symbol_name_edit.setText(part.new_name)
        self._symbol_name_edit.blockSignals(False)

        description_text = choice.description if choice.description is not None else raw.get("Description", "")
        text_values = {
            "mpn": part.mpn,
            "manufacturer": choice.manufacturer if choice.manufacturer is not None else (
                raw.get("Manufacturer") or raw.get("MF") or ""
            ),
            "datasheet": choice.datasheet if choice.datasheet is not None else raw.get("Datasheet", ""),
            "description": description_text,
        }
        for name, value in text_values.items():
            edit = self._field_edits[name]
            edit.blockSignals(True)
            edit.setText(value)
            edit.blockSignals(False)
        self._field_edits["description"].setToolTip(html.escape(description_text))

        self._value_edit.setText(part.mpn)

        self._field_changes_list.clear()
        for change in part.field_changes:
            self._field_changes_list.addItem(_field_change_text(change))

        self._display_footprint(part, choice)
        self._display_model(part, choice)
        self._display_conflicts(part)
        self._display_derive(part, choice)

        for name in TEXT_LABELS:
            override = choice.keywords if name == "keywords" else (
                choice.fp_description if name == "fp_description" else choice.fp_tags
            )
            generated = getattr(part.generated_text, name)
            edit = self._text_edits[name]
            edit.blockSignals(True)
            edit.setPlainText(override if override is not None else generated)
            edit.blockSignals(False)

    def _display_footprint(self, part: PartPlan, choice: PartChoice):
        """Fill the footprint radios, name and official picker for the selected part (D-07, D-08)."""
        is_official = choice.footprint_target == "official"
        self._fp_move_radio.blockSignals(True)
        self._fp_official_radio.blockSignals(True)
        self._fp_move_radio.setChecked(not is_official)
        self._fp_official_radio.setChecked(is_official)
        self._fp_move_radio.blockSignals(False)
        self._fp_official_radio.blockSignals(False)
        self._official_box.setVisible(is_official)

        self._fp_name_edit.blockSignals(True)
        default_fp_name = (part.footprint_new or part.footprint_old).rpartition(":")[-1]
        self._fp_name_edit.setText(choice.footprint_name if choice.footprint_name is not None else default_fp_name)
        self._fp_name_edit.blockSignals(False)

        self._official_combo.blockSignals(True)
        official_text = choice.official_footprint if choice.official_footprint is not None else (
            part.footprint_new if is_official else ""
        )
        self._official_combo.setEditText(official_text)
        self._official_combo.blockSignals(False)

        pad_warning = next(
            (
                issue.text for issue in part.issues
                if issue.severity is Severity.WARNING and issue.code == "migration.pad_mismatch"
            ),
            None,
        )
        self._pad_warning_label.setText(pad_warning or "")
        self._pad_warning_label.setVisible(bool(pad_warning))

    # -- showing pages ---------------------------------------------------------

    # -- the Files tab: every operation, its diff, and the leftover check boxes (D-10, D-15, D-21) --

    def _build_files_tab(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        self._files_tree = PreviewTree()
        self._files_tree.row_activated.connect(self._on_file_row)
        lay.addWidget(self._files_tree, 2)

        leftovers_label = QLabel(LEFTOVERS_TEXT)
        leftovers_label.setTextFormat(Qt.TextFormat.PlainText)
        lay.addWidget(leftovers_label)
        self._leftovers_list = QListWidget()
        self._leftovers_list.itemChanged.connect(self._on_leftover_changed)
        lay.addWidget(self._leftovers_list, 1)
        return page

    def _files_sections(self, plan: MigrationPlan) -> tuple[PreviewSection, ...]:
        """One row per planned op: a model/footprint rename (write+delete paired by source_rel) is one
        "Move or rename" row; mkdir ops are not shown (not in the must_haves truth's own list)."""
        ops = plan.ops
        delete_index_by_rel = {op.rel: idx for idx, op in enumerate(ops) if op.kind == "delete"}
        paired_delete_indexes: set[int] = set()
        write_rows: list[PreviewRow] = []
        move_rows: list[PreviewRow] = []
        delete_rows: list[PreviewRow] = []
        rmdir_rows: list[PreviewRow] = []
        for index, op in enumerate(ops):
            if op.kind == "write":
                paired_index = delete_index_by_rel.get(op.source_rel) if op.source_rel is not None else None
                if paired_index is not None:
                    paired_delete_indexes.add(paired_index)
                    move_rows.append(PreviewRow(text=f"{op.source_rel} → {op.rel}", kind="file", op_index=index))
                else:
                    write_rows.append(PreviewRow(text=op.rel, kind="file", op_index=index))
            elif op.kind == "delete":
                if index not in paired_delete_indexes:
                    delete_rows.append(PreviewRow(text=op.rel, kind="file", op_index=index))
            elif op.kind == "rmdir":
                rmdir_rows.append(PreviewRow(text=op.rel, kind="file", op_index=index))
        delete_rows = [row for row in delete_rows if row.op_index not in paired_delete_indexes]
        sections = (
            PreviewSection(_WRITE_SECTION, tuple(write_rows)),
            PreviewSection(_MOVE_SECTION, tuple(move_rows)),
            PreviewSection(_DELETE_SECTION, tuple(delete_rows)),
            PreviewSection(_RMDIR_SECTION, tuple(rmdir_rows)),
        )
        return tuple(section for section in sections if section.rows)

    def _on_file_row(self, row: PreviewRow):
        """A Files-tab row was double-clicked or entered: build its ContentText on a worker (T-13-36)."""
        if self._plan is None or row.op_index is None or row.op_index >= len(self._plan.ops):
            return
        op = self._plan.ops[row.op_index]
        repo_root = self._repo_root
        core = self._core

        def task(progress):
            return core.op_content(op, repo_root)

        worker = self._spawn(task)
        worker.result.connect(self._on_file_content_ready)
        worker.start()

    def _on_file_content_ready(self, content: ContentText):
        view = ContentViewDialog(content, parent=self)
        self._content_views.append(view)
        view.finished.connect(lambda _result=0, v=view: self._on_content_view_closed(v))
        view.open()

    def _on_content_view_closed(self, view: ContentViewDialog):
        if view in self._content_views:
            self._content_views.remove(view)

    def _populate_leftovers(self, rows: tuple):
        self._leftovers_list.blockSignals(True)
        try:
            self._leftovers_list.clear()
            for row in rows:
                item = QListWidgetItem(row.rel)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked if row.keep else Qt.CheckState.Checked)
                item.setToolTip(html.escape(row.reason))
                item.setData(Qt.ItemDataRole.UserRole, row.rel)
                self._leftovers_list.addItem(item)
        finally:
            self._leftovers_list.blockSignals(False)

    def _on_leftover_changed(self, item: QListWidgetItem):
        rel = item.data(Qt.ItemDataRole.UserRole)
        if rel is None:
            return
        keep = item.checkState() != Qt.CheckState.Checked
        self._update_leftover(rel, keep)

    def _update_leftover(self, rel: str, keep: bool):
        leftovers = dict(self._choices.leftovers)
        leftovers[rel] = keep
        self._choices = dataclasses.replace(self._choices, leftovers=leftovers)
        self._gen += 1
        self._rebuild_timer.start(_REBUILD_DELAY_MS)
        self._draft_timer.start(_DRAFT_DELAY_MS)

    def _show_page(self, page: QWidget):
        self._stack.setCurrentWidget(page)

    # -- Run itself: wrong-checkout refusal, KiCad-open check, tag and the transaction (MIG-01, MIG-03, D-26) --

    def _on_run(self):
        if not self._run_btn.isEnabled() or self.is_running() or self._plan is None:
            return
        self._run_failure_banner.hide()
        self._running = True
        self._start_checkout_check()

    def _start_checkout_check(self):
        core = self._core
        repo_root = self._repo_root

        def task(progress):
            return core.checkout_mismatch(repo_root)

        worker = self._spawn(task)
        worker.result.connect(self._on_checkout_checked)
        worker.start()

    def _on_checkout_checked(self, mismatch):
        if mismatch is not None:
            text = f"{wrong_checkout_refusal(mismatch, RUN_REFUSAL_ACTION)} {_WRONG_CHECKOUT_RUN_TEXT}"
            self._running = False
            self._show_run_banner(_RUN_FAILED_TITLE, text)
            return
        self._start_kicad_check_for_run()

    def _start_kicad_check_for_run(self):
        core = self._core

        def task(progress):
            return core.kicad_running()

        worker = self._spawn(task)
        worker.result.connect(self._on_run_kicad_checked)
        worker.start()

    def _on_run_kicad_checked(self, names):
        names = list(names)
        if names:
            answer = self._core.ask_kicad_open(self, names)
            if answer is ConfirmAnswer.RETRY:
                self._start_kicad_check_for_run()
                return
            if answer is not ConfirmAnswer.WRITE:
                self._running = False
                return
        self._start_run()

    def _start_run(self):
        self._show_page(self._running_page)
        self._running_label.setText("Starting the migration...")
        core = self._core
        plan = self._plan  # the rendered object, never a rebuilt copy
        layout = self._layout
        repo_root = self._repo_root
        tools = getattr(self._ctx, "tools", None)

        def before_first_write():
            return core.ensure_tag(layout.custom_dir, repo_root)

        def task(progress):
            return core.apply(plan, tools=tools, progress=progress, before_first_write=before_first_write)

        worker = self._spawn(task)
        self._run_worker = worker
        worker.progress.connect(self._on_run_progress)
        worker.result.connect(lambda result, p=plan: self._on_run_done(p, result))
        worker.start()

    def _on_run_progress(self, message: str, current: int, total: int):
        if self.is_running():
            self._running_label.setText(message)

    def _on_run_done(self, plan: MigrationPlan, result: MigrationResult):
        """Task 2 replaces the success branch with the Result view; this tracer just proves the worker chain."""
        self._run_worker = None
        self._running = False
        self.issues_logged.emit(list(result.issues))
        if result.ok:
            self.migrated.emit(result)
            self._show_page(self._edit_page)
            return
        self._show_run_failure(result)
        self._start_load()

    def _show_run_banner(self, title: str, text: str):
        self._run_failure_title.setText(title)
        self._run_failure_body.setPlainText(text)
        self._run_failure_banner.show()
        self._show_page(self._edit_page)

    def _show_run_failure(self, result: MigrationResult):
        """List every reason and say every file was restored, or name the backup folder (MIG-03)."""
        restore_failed = any(issue.code == "migration.rollback_incomplete" for issue in result.issues)
        title = _RUN_FAILED_NOT_RESTORED_TITLE if restore_failed else _RUN_FAILED_TITLE
        closing = _RUN_FAILED_RETRY
        if restore_failed and result.backup_dir is not None:
            closing = f"The original files are in {result.backup_dir}."
        lines = [issue.text for issue in result.issues if issue.severity is Severity.ERROR]
        self._show_run_banner(title, "\n".join([*lines, closing]))

    # -- closing (D-14 Task 3 extends this with the "waits without blocking" rule) --

    def done(self, r: int):
        if self.is_running() or self.is_committing():
            return
        if self._closing:
            return
        if any(w.isRunning() for w in self._workers):
            self._closing = True
            self._pending_result = r
            return
        super().done(r)

    def closeEvent(self, event):
        if self.is_busy():
            event.ignore()
            self.done(int(QDialog.DialogCode.Rejected))
            return
        super().closeEvent(event)
