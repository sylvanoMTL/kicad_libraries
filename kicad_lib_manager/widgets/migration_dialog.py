"""The migration window: refusal page, grouped part list, detail pane, strip and Run gating (MIG-01, MIG-02).

Every slow call (git, kicad-cli, the sibling/footprint index, planning, hashing) runs off the GUI
thread on a TaskWorker (reused from import_dialog), tagged with a generation number so only the
latest rebuild result is ever shown - an edit while a rebuild runs supersedes it instead of racing
it onto the screen (D-15). Plans 13-15 and 13-16 extend this file with the footprint/model/family
controls, the Files tab, Run itself and the commit step; this plan only enables the Run button.
"""

import dataclasses
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPlainTextEdit, QPushButton, QScrollArea, QSplitter, QStackedWidget, QTabWidget,
    QToolBar, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

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
    MigrationPlan,
    PartChoice,
    PartKey,
    PartPlan,
    PlanContext,
)
from ..importer.migration.planner import build_migration_plan, prepare_context
from ..importer.migration.precheck import check_custom
from ..importer.planner import detect_tools
from ..kicad_process import kicad_running
from ..models import Issue
from ..settings import migration_draft_file
from .import_dialog import TaskWorker, fit_window
from .theme import AMBER, AMBER_TINT, FIELD_FRAME_QSS, MUTED, PRIMARY_BUTTON_QSS

WINDOW_TITLE = "Migrate to Atomic Libraries"
RUN_TEXT = "Run Migration"
CHECK_AGAIN_TEXT = "Check again"
UNDECIDED_GROUP = "Choose a library"
CHANGED_MARK = "changed since the draft"
PASS_MARK = "✓"
_REBUILD_DELAY_MS = 300
_DRAFT_DELAY_MS = 800

_HELP_TEXT = "Help"
_CLOSE_TEXT = "Close"
_WINDOW_SIZE = QSize(1040, 700)


def _plural(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def _check_plan(plan: MigrationPlan, inventory: Inventory, kicad_fp_dir: Path | None) -> GateOutcome:
    """Build the plan's own end-state context, then judge it; the window never builds AtomicContext itself."""
    ctx = end_state_context(plan, inventory, kicad_fp_dir)
    return _gate_check_plan(plan, inventory, ctx)


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
        # importer.layout.RepoLayout is built straight from repo_root; avoids a second constructor arg
        from ..importer.layout import RepoLayout

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
        self._closing = False
        self._pending_result: int | None = None

        self._rebuild_timer = QTimer(self)
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.setInterval(_REBUILD_DELAY_MS)
        self._rebuild_timer.timeout.connect(self._start_rebuild)

        outer = QVBoxLayout(self)
        self._build_toolbar(outer)
        self._stack = QStackedWidget()
        outer.addWidget(self._stack)

        self._checking_page = self._build_checking_page()
        self._refusal_page = self._build_refusal_page()
        self._loading_page = self._build_loading_page()
        self._edit_page = self._build_edit_page()
        for page in (self._checking_page, self._refusal_page, self._loading_page, self._edit_page):
            self._stack.addWidget(page)
        self._stack.setCurrentWidget(self._checking_page)

        self.resize(_WINDOW_SIZE)
        fit_window(self, _WINDOW_SIZE)
        QTimer.singleShot(0, self._start_check)

    # -- status --------------------------------------------------------------

    def is_running(self) -> bool:
        """True while Run itself is applying the migration (plan 13-16 fills this in)."""
        return False

    def is_committing(self) -> bool:
        """True while the parent commit runs (plan 13-16 fills this in)."""
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

    def _build_edit_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)

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
        self._tabs.addTab(self._part_tab, "Part")
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

        self._library_combo = QComboBox()
        self._library_combo.setEditable(True)
        self._library_combo.lineEdit().textEdited.connect(self._on_library_edited)
        form.addRow("Library", self._framed(self._library_combo, "library"))

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

        scroll.setWidget(inner)
        outer.addWidget(scroll)
        return page

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

    def _on_field_edited(self, name: str, text: str):
        if self._current_key is None:
            return
        self._update_choice(self._current_key, **{name: text})

    def _on_library_edited(self, text: str):
        self._on_field_edited("library", text)

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

    def _display_part(self, part: PartPlan):
        self._current_key = part.key
        choice = self._choices.parts.get(part.key, PartChoice())
        raw = self._raw_fields.get(part.key, {})

        self._library_combo.blockSignals(True)
        library_text = choice.library if choice.library is not None else (
            part.target_library or (part.suggestion.name if part.suggestion is not None else "")
        )
        self._library_combo.setEditText(library_text)
        self._library_combo.blockSignals(False)

        self._symbol_name_edit.blockSignals(True)
        self._symbol_name_edit.setText(part.new_name)
        self._symbol_name_edit.blockSignals(False)

        text_values = {
            "mpn": part.mpn,
            "manufacturer": choice.manufacturer if choice.manufacturer is not None else (
                raw.get("Manufacturer") or raw.get("MF") or ""
            ),
            "datasheet": choice.datasheet if choice.datasheet is not None else raw.get("Datasheet", ""),
            "description": choice.description if choice.description is not None else raw.get("Description", ""),
        }
        for name, value in text_values.items():
            edit = self._field_edits[name]
            edit.blockSignals(True)
            edit.setText(value)
            edit.blockSignals(False)

        self._value_edit.setText(part.mpn)

    # -- showing pages ---------------------------------------------------------

    def _show_page(self, page: QWidget):
        self._stack.setCurrentWidget(page)

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
