"""The commit panel of the Result view (Phase 6, D-01): branch, files, message, parent checkbox, Commit.

The panel owns layout and state only; it never starts git. It emits commit_requested, switch_requested
and file_activated, and the dialog runs the jobs. Every string that comes from git, a package or an
Issue is shown as plain text.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPlainTextEdit,
    QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from ..importer.commit_plan import CommitPlan, default_message, parent_preview, subject_of
from ..importer.commit_step import CommitOutcome, CommitProbe
from ..models import Issue, Severity
from . import theme
from .import_result import ElidedLabel, _heading, _plain_label

_FILES_ROWS = 6  # rows shown before the file list scrolls
_MESSAGE_LINES = 7
_PREVIEW_LINES = 5
_OUTPUT_LINES = 8  # lines of git output shown before the box scrolls
_EARLIER_SHOWN = 10  # earlier Custom commits listed before "...and k more"
_PARENT_TEXT = "Also commit the Custom ref in the parent repo"
_COMMITTED_CUSTOM_ONLY = "Committed in Custom only"  # the button text after a partial result (D-17)
_WARNING_NOISE = "warning: in the working copy of"  # line-ending notices git prints for every file (Pitfall 6)
_STATES = (
    "probing", "unavailable", "refused", "offer_switch", "switching", "ready", "committing", "done", "failed"
)
_GLYPHS = {Severity.SUCCESS: "✓ ", Severity.ERROR: "✖ ", Severity.WARNING: "⚠ "}
_STRIP_PREFIX = {"unavailable": "Commit unavailable: ", "refused": "Commit refused: "}
_DIRTY_HINT = (
    "⚠ Amber files also contain uncommitted changes made before this import. "
    "They are committed too; double-click one to see them."
)


class _CommitFilesList(QListWidget):
    """The fixed list of files to commit. Enter activates the current row and stops there.

    A stock list view ignores Enter after activating, which would hand it to the dialog's default button.
    """

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self.currentItem()
            if item is not None:
                self.itemActivated.emit(item)
            event.accept()
            return
        super().keyPressEvent(event)


def _wrapped_label() -> QLabel:
    """A plain wrapped label that never widens the layout it sits in."""
    label = _plain_label()
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    return label


def _muted_label() -> QLabel:
    label = _wrapped_label()
    label.setStyleSheet(f"color: {theme.MUTED};")
    return label


def _amber_label() -> QLabel:
    label = _wrapped_label()
    label.setStyleSheet(f"color: {theme.AMBER};")
    return label


def _mono_font() -> QFont:
    font = QFont(theme.MONO_FAMILY, theme.MONO_PT)
    font.setStyleHint(QFont.StyleHint.Monospace)
    return font


def _lines_height(box: QPlainTextEdit, lines: int) -> int:
    """The height of a plain-text box that shows `lines` lines, with its frame, margins and scroll bar."""
    metrics = box.fontMetrics()
    margins = int(box.document().documentMargin()) * 2
    return metrics.lineSpacing() * lines + margins + 2 * box.frameWidth() + box.horizontalScrollBar().sizeHint().height()


def _outcome_tint(severities) -> str | None:
    """The background of the outcome strip: set by its strongest line (D-18)."""
    if Severity.ERROR in severities:
        return theme.ERROR_TINT
    if Severity.WARNING in severities:
        return theme.AMBER_TINT
    if Severity.SUCCESS in severities:
        return theme.SUCCESS_TINT
    return None


def _readonly_box(lines: int) -> QPlainTextEdit:
    box = QPlainTextEdit()
    box.setReadOnly(True)
    box.setFont(_mono_font())
    box.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
    box.setTabChangesFocus(True)
    box.setFixedHeight(_lines_height(box, lines))
    return box


class CommitPanel(QWidget):
    """State machine: probing, then unavailable | refused | offer_switch | ready, then committing, then done | failed.

    offer_switch goes through switching and back to probing (the dialog probes again) or to offer_switch
    again when the switch failed. An outcome with nothing committed goes to probing and keeps its refusal
    text on top: the dialog probes again, and only a fresh probe can enable Commit once more (D-11).
    """

    commit_requested = Signal(str, bool)  # the message, whether to commit the Custom ref in the parent too
    switch_requested = Signal()
    file_activated = Signal(str)  # CommitFile.rel of a file that had changes before the import

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "probing"
        self._committed = False
        self._plan: CommitPlan | None = None
        self._probe: CommitProbe | None = None
        self._outcome_labels: list[QLabel] = []
        self._outcome_severities: list[Severity] = []
        self._pending_refusal: tuple[Issue, ...] = ()  # shown again on top of the next probe (D-11)
        self._parent_wanted: bool | None = None  # the user's parent choice; None until the first probe
        self._updating = False  # True while the panel itself changes the parent box

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(theme.SP_SM)
        lay.addWidget(_heading("Commit"))

        self._branch_label = _wrapped_label()
        lay.addWidget(self._branch_label)
        self._parent_label = ElidedLabel(mode=Qt.TextElideMode.ElideMiddle, full_tooltip=True)
        self._parent_label.hide()
        lay.addWidget(self._parent_label)

        strip_row = QHBoxLayout()
        strip_row.setSpacing(theme.SP_SM)
        self._strip = _wrapped_label()
        strip_row.addWidget(self._strip, 1)
        self._switch_button = QPushButton("Switch to main")
        self._switch_button.setAutoDefault(False)
        self._switch_button.setDefault(False)
        self._switch_button.clicked.connect(self._on_switch_clicked)
        self._switch_button.hide()
        strip_row.addWidget(self._switch_button, 0, Qt.AlignmentFlag.AlignTop)
        lay.addLayout(strip_row)

        self._files_heading = _heading("Files to commit (0)")
        lay.addWidget(self._files_heading)
        self._files_list = _CommitFilesList()
        self._files_list.setAccessibleName("Files to commit")
        self._files_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._files_list.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self._files_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._files_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._files_list.itemActivated.connect(self._on_item_activated)
        lay.addWidget(self._files_list)
        self._dirty_hint = _amber_label()
        self._dirty_hint.setText(_DIRTY_HINT)
        self._dirty_hint.hide()
        lay.addWidget(self._dirty_hint)
        self._other_label = _muted_label()
        self._other_label.hide()
        lay.addWidget(self._other_label)

        lay.addWidget(_heading("Message"))
        self._message = QPlainTextEdit()
        self._message.setAccessibleName("Commit message")
        self._message.setTabChangesFocus(True)
        self._message.setMinimumHeight(self._message.fontMetrics().lineSpacing() * _MESSAGE_LINES)
        lay.addWidget(self._message)

        self._parent_check = QCheckBox(_PARENT_TEXT)
        self._parent_check.setChecked(True)
        # a long branch name must not widen the Result view; the tooltip keeps the full text
        self._parent_check.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        lay.addWidget(self._parent_check)
        self._parent_reason = _amber_label()
        self._parent_reason.hide()
        lay.addWidget(self._parent_reason)
        self._earlier_label = _muted_label()
        self._earlier_label.hide()
        lay.addWidget(self._earlier_label)
        self._preview_heading = _muted_label()
        self._preview_heading.setText("Parent commit message (generated)")
        self._preview_heading.hide()
        lay.addWidget(self._preview_heading)
        self._parent_preview = _readonly_box(_PREVIEW_LINES)
        self._parent_preview.setAccessibleName("Parent commit message")
        self._parent_preview.setStyleSheet(f"color: {theme.MUTED};")
        self._parent_preview.hide()
        lay.addWidget(self._parent_preview)

        self._blank_label = _amber_label()
        self._blank_label.setText("Enter a commit message")
        self._blank_label.hide()
        lay.addWidget(self._blank_label)
        self.commit_button = QPushButton("Commit")
        # Enter inside the panel must never commit (PROJECT.md Safety, RESEARCH Pitfall 9)
        self.commit_button.setAutoDefault(False)
        self.commit_button.setDefault(False)
        self.commit_button.setStyleSheet(theme.PRIMARY_BUTTON_QSS)  # the one primary action here (D-19)
        self.commit_button.clicked.connect(self._on_commit_clicked)
        lay.addWidget(self.commit_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self._step_row = QWidget()
        step_lay = QHBoxLayout(self._step_row)
        step_lay.setContentsMargins(0, 0, 0, 0)
        step_lay.setSpacing(theme.SP_SM)
        self._step = _muted_label()
        step_lay.addWidget(self._step, 1)
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setTextVisible(False)
        self._progress.setFixedSize(theme.SP_XL * 8, theme.SP_MD)
        step_lay.addWidget(self._progress, 0)
        self._step_row.hide()
        lay.addWidget(self._step_row)

        # one strip holds every outcome line; its tint follows the strongest line (D-18)
        self._outcome_frame = QFrame()
        self._outcome_frame.setObjectName("outcomeStrip")
        self._outcome_layout = QVBoxLayout(self._outcome_frame)
        self._outcome_layout.setContentsMargins(0, 0, 0, 0)
        self._outcome_layout.setSpacing(theme.SP_XS)
        self._outcome_frame.hide()
        lay.addWidget(self._outcome_frame)
        self._manual_label = _plain_label()
        self._manual_label.setFont(_mono_font())
        self._manual_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._manual_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._manual_label.hide()
        lay.addWidget(self._manual_label)
        self._output = _readonly_box(_OUTPUT_LINES)
        self._output.setAccessibleName("Git output")
        self._output.hide()
        lay.addWidget(self._output)

        self._message.textChanged.connect(self._refresh_parent_and_commit)
        self._parent_check.toggled.connect(self._on_parent_toggled)
        self._parent_check.toggled.connect(self._refresh_parent_and_commit)
        self._set_state("probing")

    # -- state API -------------------------------------------------------------------------------

    def state(self) -> str:
        return self._state

    def message(self) -> str:
        return self._message.toPlainText()

    def bump_parent(self) -> bool:
        return self._parent_check.isEnabled() and self._parent_check.isChecked()

    def committed(self) -> bool:
        return self._committed

    def outcome_lines(self) -> list[str]:
        """The outcome lines shown after a commit (or a failed switch), in order."""
        return [label.text() for label in self._outcome_labels]

    def show_plan(self, cplan: CommitPlan):
        """Fill the file list and pre-fill the message (D-18); the panel waits for the probe."""
        self._plan = cplan
        self._probe = None
        self._parent_wanted = None
        self._pending_refusal = ()
        self._fill_files(cplan)
        self._dirty_hint.hide()
        self._other_label.hide()
        self._message.setPlainText(default_message(cplan))
        self._branch_label.setText("Custom branch: checking...")
        self._branch_label.setStyleSheet("")
        self._clear_outcome()
        self._set_state("probing")

    def begin_reprobe(self, cplan: CommitPlan | None = None):
        """Wait for a fresh probe without losing the message, the parent choice or a pending refusal (D-11).

        With a new plan only the file list is refreshed.
        """
        if cplan is not None:
            self._plan = cplan
            self._fill_files(cplan)
        self._probe = None
        self._branch_label.setText("Custom branch: checking...")
        self._branch_label.setStyleSheet("")
        self._clear_outcome()
        self._render_issues(self._pending_refusal)
        self._set_state("probing")

    def _fill_files(self, cplan: CommitPlan):
        """The file rows, their heading and the list height."""
        files = self._files_list
        files.clear()
        for commit_file in cplan.files:
            item = QListWidgetItem(commit_file.display)
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)  # read-only, no check boxes
            item.setToolTip(commit_file.display)
            item.setData(Qt.ItemDataRole.UserRole, commit_file.rel)
            files.addItem(item)
        self._files_heading.setText(f"Files to commit ({files.count()})")
        row = files.sizeHintForRow(0) if files.count() else files.fontMetrics().height() + theme.SP_SM
        files.setFixedHeight(row * min(max(files.count(), 1), _FILES_ROWS) + 2 * files.frameWidth())

    def apply_probe(self, probe: CommitProbe):
        """Switch to the probe's state and show what it found."""
        self._probe = probe
        self._clear_outcome()
        if probe.state in ("refused", "unavailable"):
            self._pending_refusal = ()  # the probe's own reason replaces the old refusal
        else:
            self._render_issues(self._pending_refusal)
        self._show_custom_line(probe)
        if probe.parent_dir is not None:
            where = probe.parent_dir.as_posix()
            self._parent_label.set_full_text(
                f"Parent repo: {where} ({probe.parent_branch})" if probe.parent_branch else f"Parent repo: {where}"
            )
            self._parent_label.show()
        else:
            self._parent_label.hide()
        # the box is ticked on the first probe only; later probes keep the user's choice (REV-11)
        self._updating = True
        try:
            if probe.parent_ok:
                self._parent_check.setText(f"{_PARENT_TEXT} ({probe.parent_branch})".replace("&", "&&"))
                self._parent_check.setToolTip(f"{_PARENT_TEXT} ({probe.parent_branch})")
                if self._parent_wanted is None:
                    self._parent_wanted = True
                self._parent_check.setChecked(self._parent_wanted)
            else:
                self._parent_check.setText(_PARENT_TEXT)
                self._parent_check.setToolTip("")
                self._parent_check.setChecked(False)
        finally:
            self._updating = False
        if probe.state == "ready" and not probe.parent_ok:
            self._parent_reason.setText(f"Parent commit unavailable: {probe.parent_reason}")
            self._parent_reason.show()
        else:
            self._parent_reason.hide()
        self._mark_dirty_files(probe)
        count = probe.other_changes
        if count > 0:
            if count == 1:
                self._other_label.setText("1 other change in Custom stays uncommitted")
            else:
                self._other_label.setText(f"{count} other changes in Custom stay uncommitted")
        self._other_label.setVisible(count > 0)
        self._set_state(probe.state)

    def set_switching(self):
        """The dialog is switching Custom to main: the button is locked until the result comes back."""
        self._set_state("switching")

    def show_switch_failed(self, text: str):
        """Back to the offer after a failed switch: git's first line as the error, the rest in the output box."""
        lines = text.splitlines() or [text]
        self._clear_outcome()
        self._add_outcome_line(f"✖ {lines[0]}", theme.ERROR, Severity.ERROR)
        self._set_output(lines[1:])
        self._set_state("offer_switch")

    def set_committing(self):
        self._step.setText("Committing...")
        self._set_state("committing")

    def set_step(self, text: str):
        if self._state == "committing":
            self._step.setText(text)

    def show_outcome(self, outcome: CommitOutcome):
        """Show what the commit did: done, failed after a partial success (D-03), or waiting for a fresh probe."""
        self._clear_outcome()
        extra = self._render_issues(outcome.issues)
        output = outcome.output.splitlines()
        if not output:
            output = [line for line in extra if not line.startswith("Finish it by hand:")]
        self._set_output(output)
        self._committed = outcome.committed
        if outcome.committed and outcome.failed and outcome.manual_command:
            self._manual_label.setText(f"Finish it by hand: {outcome.manual_command}")
            self._manual_label.show()
        if outcome.committed:
            self._pending_refusal = ()
            self._set_state("failed" if outcome.failed else "done")
        else:
            # nothing was committed: never show a stale "ready"; the dialog probes again (D-11, REV-10)
            self._pending_refusal = tuple(outcome.issues)
            self._set_state("probing")

    # -- internals -------------------------------------------------------------------------------

    def _render_issues(self, issues) -> list[str]:
        """Outcome lines for issues; returns the detail lines of error issues, for the output box."""
        extra: list[str] = []
        for issue in issues:
            line = self._issue_line(issue)
            if line is None:
                continue
            text, color = line
            first, *rest = text.splitlines() or [""]
            if issue.severity is Severity.ERROR:
                extra.extend(rest)
                text = first
            self._add_outcome_line(f"{_GLYPHS.get(issue.severity, '')}{text}", color, issue.severity)
        return extra

    @staticmethod
    def _issue_line(issue: Issue):
        """(text, colour) of one outcome line, or None for a severity the panel does not show."""
        if issue.severity is Severity.SUCCESS:
            return issue.text, theme.SUCCESS
        if issue.severity is Severity.ERROR:
            return issue.text, theme.ERROR
        if issue.severity is Severity.WARNING:
            return issue.text, theme.AMBER
        if issue.severity is Severity.INFO:
            return issue.text, None
        return None

    def _add_outcome_line(self, text: str, color: str | None, severity: Severity):
        label = _wrapped_label()
        label.setText(text)
        label.setStyleSheet(f"color: {color};" if color else "")
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._outcome_labels.append(label)
        self._outcome_severities.append(severity)
        self._outcome_layout.addWidget(label)
        self._tint_outcome_frame()

    def _tint_outcome_frame(self):
        """Show the strip with the tint of its strongest line. The object-name selector keeps the labels unstyled."""
        tint = _outcome_tint(self._outcome_severities)
        if tint:
            self._outcome_frame.setStyleSheet(
                f"QFrame#outcomeStrip {{ background-color: {tint}; padding: {theme.SP_SM}px; }}"
            )
        else:
            self._outcome_frame.setStyleSheet("")
        self._outcome_frame.setVisible(bool(self._outcome_labels))

    def _clear_outcome(self):
        for label in self._outcome_labels:
            self._outcome_layout.removeWidget(label)
            label.hide()
            label.setParent(None)
            label.deleteLater()
        self._outcome_labels = []
        self._outcome_severities = []
        self._tint_outcome_frame()
        self._manual_label.hide()
        self._manual_label.setText("")
        self._set_output([])

    def _set_output(self, lines):
        """Git's output in the read-only box; the line-ending notices git prints for every file are left out."""
        kept = [line for line in lines if not line.startswith(_WARNING_NOISE)]
        self._output.setPlainText("\n".join(kept))
        self._output.setVisible(bool(kept))

    def _show_custom_line(self, probe: CommitProbe):
        label = self._branch_label
        if probe.branch:
            if probe.not_main:
                label.setText(f"Custom branch: {probe.branch} (not main)")
                label.setStyleSheet(f"color: {theme.AMBER};")
            else:
                label.setText(f"Custom branch: {probe.branch}")
                label.setStyleSheet("")
        elif probe.head or (probe.state in ("offer_switch", "refused") and "detached" in probe.reason.lower()):
            label.setText(f"Custom: detached HEAD at {probe.head[:7]}" if probe.head else "Custom: detached HEAD")
            label.setStyleSheet("")
        else:
            label.setText("Custom branch: not available")
            label.setStyleSheet("")

    def _mark_dirty_files(self, probe: CommitProbe):
        """Rows that had changes before the import show in amber; every other row is reset to plain."""
        any_dirty = False
        files = self._files_list
        for row in range(files.count()):
            item = files.item(row)
            rel = item.data(Qt.ItemDataRole.UserRole)
            display = self._plan.files[row].display if self._plan is not None and row < len(self._plan.files) else item.text()
            if rel in probe.dirty_before:
                any_dirty = True
                item.setText(f"⚠ {display}")
                item.setForeground(QBrush(QColor(theme.AMBER)))
                item.setToolTip(
                    f"{display} also contains uncommitted changes made before this import. "
                    "It is committed too; double-click to see them."
                )
            else:
                item.setText(display)
                item.setData(Qt.ItemDataRole.ForegroundRole, None)
                item.setToolTip(display)
        self._dirty_hint.setVisible(any_dirty)

    def _apply_strip(self):
        """The strip text and look for the current state; the Switch to main button sits beside it."""
        state, probe = self._state, self._probe
        reason = probe.reason if probe is not None else ""
        if state == "probing":
            text, alert = "Checking Custom and the parent repo...", False
        elif state == "switching":
            text, alert = "Switching Custom to main...", False
        elif state in _STRIP_PREFIX:
            text, alert = f"⚠ {_STRIP_PREFIX[state]}{reason}", True
        elif state == "offer_switch":
            text, alert = f"⚠ {reason} Switch to main before committing.".replace("  ", " "), True
        else:
            self._strip.hide()
            return
        self._strip.setText(text)
        if alert:
            self._strip.setStyleSheet(
                f"background-color: {theme.AMBER_TINT}; color: {theme.AMBER}; padding: {theme.SP_SM}px;"
            )
        else:
            self._strip.setStyleSheet(f"color: {theme.MUTED};")
        self._strip.show()

    def _set_state(self, state: str):
        self._state = state
        ready = state == "ready"
        self._message.setReadOnly(not ready)
        self._parent_check.setEnabled(ready and self._probe is not None and self._probe.parent_ok)
        self._switch_button.setVisible(state in ("offer_switch", "switching"))
        self._switch_button.setEnabled(state == "offer_switch")
        self._step_row.setVisible(state == "committing")
        self.commit_button.setText(
            {"committing": "Committing...", "done": "Committed", "failed": _COMMITTED_CUSTOM_ONLY}.get(state, "Commit")
        )
        self._apply_strip()
        self._refresh_parent_and_commit()

    def _refresh_parent_and_commit(self):
        """Rebuild what depends on the message and the checkbox: the parent preview, the blank line, Commit (D-19, D-20)."""
        probe, cplan = self._probe, self._plan
        locked_in = self._state in ("committing", "done", "failed")  # keep the layout steady once git has started
        show_parent = (
            probe is not None and cplan is not None and self._parent_check.isChecked()
            and (self._parent_check.isEnabled() or locked_in)
        )
        if show_parent:
            self._earlier_label.setText(self._earlier_text(probe))
            preview = parent_preview(
                subject_of(self._message.toPlainText()), cplan.custom_rel, probe.gitlink_old, probe.earlier,
                listed=probe.earlier_listed,
            )
            if self._parent_preview.toPlainText() != preview:
                self._parent_preview.setPlainText(preview)
        self._earlier_label.setVisible(show_parent and bool(self._earlier_label.text()))
        self._preview_heading.setVisible(show_parent)
        self._parent_preview.setVisible(show_parent)
        blank = not self._message.toPlainText().strip()
        self._blank_label.setVisible(self._state == "ready" and blank)
        self.commit_button.setEnabled(self._state == "ready" and not blank)

    @staticmethod
    def _earlier_text(probe: CommitProbe) -> str:
        """The D-13 block: the earlier Custom commits the parent bump also carries, capped at ten lines."""
        earlier = probe.earlier
        if not probe.earlier_listed:
            if probe.gitlink_old:
                return f"The earlier Custom commits since {probe.gitlink_old[:7]} could not be listed."
            return ""
        if not earlier:
            return ""
        noun = "commit" if len(earlier) == 1 else "commits"
        lines = [f"Parent bump also includes {len(earlier)} earlier Custom {noun}:"]
        lines.extend(f"- {short} {text}" for short, text in earlier[:_EARLIER_SHOWN])
        if len(earlier) > _EARLIER_SHOWN:
            lines.append(f"…and {len(earlier) - _EARLIER_SHOWN} more")
        return "\n".join(lines)

    def _on_parent_toggled(self, checked: bool):
        if not self._updating and self._parent_check.isEnabled():
            self._parent_wanted = checked

    def _on_commit_clicked(self):
        if self._state == "ready" and self.commit_button.isEnabled():
            self._pending_refusal = ()
            self.commit_requested.emit(self._message.toPlainText(), self.bump_parent())

    def _on_switch_clicked(self):
        if self._state == "offer_switch":
            self._pending_refusal = ()
            self.switch_requested.emit()

    def _on_item_activated(self, item: QListWidgetItem):
        rel = item.data(Qt.ItemDataRole.UserRole)
        if rel is not None and self._probe is not None and rel in self._probe.dirty_before:
            self.file_activated.emit(rel)

