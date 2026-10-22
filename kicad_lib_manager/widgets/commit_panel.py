"""The commit panel of the Result view (Phase 6, D-01): branch, files, message, parent checkbox, Commit.

The panel owns layout and state only; it never starts git. It emits commit_requested and the dialog
runs the job. Every string that comes from git, a package or an Issue is shown as plain text.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QLabel, QListWidgetItem, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from ..importer.commit_plan import CommitPlan, default_message
from ..importer.commit_step import CommitOutcome, CommitProbe
from ..models import Severity
from . import theme
from .import_result import _FilesList, _heading, _plain_label

_FILES_ROWS = 6  # rows shown before the file list scrolls
_MESSAGE_LINES = 7
_PARENT_TEXT = "Also commit the Custom ref in the parent repo"
_STATES = (
    "probing", "unavailable", "refused", "offer_switch", "switching", "ready", "committing", "done", "failed"
)
_LINE_COLORS = {Severity.SUCCESS: theme.SUCCESS, Severity.ERROR: theme.ERROR}


class CommitPanel(QWidget):
    """State machine: probing, then unavailable | refused | offer_switch | ready, then committing, then done | failed."""

    commit_requested = Signal(str, bool)  # the message, whether to commit the Custom ref in the parent too
    switch_requested = Signal()
    file_activated = Signal(str)  # CommitFile.rel

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "probing"
        self._committed = False
        self._plan: CommitPlan | None = None
        self._probe: CommitProbe | None = None
        self._outcome_labels: list[QLabel] = []

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(theme.SP_SM)
        lay.addWidget(_heading("Commit"))

        self._branch_label = _plain_label()
        lay.addWidget(self._branch_label)
        self._parent_label = _plain_label()
        self._parent_label.hide()
        lay.addWidget(self._parent_label)
        self._status = _plain_label()
        lay.addWidget(self._status)

        self._files_heading = _heading("Files to commit (0)")
        lay.addWidget(self._files_heading)
        self._files_list = _FilesList()
        self._files_list.setAccessibleName("Files to commit")
        self._files_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._files_list.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self._files_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._files_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._files_list.itemActivated.connect(self._on_item_activated)
        lay.addWidget(self._files_list)

        self._message = QPlainTextEdit()
        self._message.setAccessibleName("Commit message")
        self._message.setTabChangesFocus(True)
        self._message.setMinimumHeight(self._message.fontMetrics().lineSpacing() * _MESSAGE_LINES)
        self._message.textChanged.connect(self._sync_buttons)
        lay.addWidget(self._message)

        self._parent_check = QCheckBox(_PARENT_TEXT)
        self._parent_check.setChecked(True)
        lay.addWidget(self._parent_check)
        self._parent_reason = _plain_label()
        self._parent_reason.setStyleSheet(f"color: {theme.AMBER};")
        self._parent_reason.hide()
        lay.addWidget(self._parent_reason)

        self.commit_button = QPushButton("Commit")
        # Enter inside the panel must never commit (PROJECT.md Safety, RESEARCH Pitfall 9)
        self.commit_button.setAutoDefault(False)
        self.commit_button.setDefault(False)
        self.commit_button.clicked.connect(self._on_commit_clicked)
        lay.addWidget(self.commit_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self._step = _plain_label()
        self._step.setStyleSheet(f"color: {theme.MUTED};")
        self._step.hide()
        lay.addWidget(self._step)
        self._outcome_layout = QVBoxLayout()
        self._outcome_layout.setSpacing(theme.SP_XS)
        lay.addLayout(self._outcome_layout)

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
        """The outcome lines shown after a commit, in order."""
        return [label.text() for label in self._outcome_labels]

    def show_plan(self, cplan: CommitPlan):
        """Fill the file list and pre-fill the message (D-18); the panel waits for the probe."""
        self._plan = cplan
        files = self._files_list
        files.clear()
        for commit_file in cplan.files:
            item = QListWidgetItem(commit_file.display)
            item.setToolTip(commit_file.display)
            item.setData(Qt.ItemDataRole.UserRole, commit_file.rel)
            files.addItem(item)
        self._files_heading.setText(f"Files to commit ({files.count()})")
        row = files.sizeHintForRow(0) if files.count() else files.fontMetrics().height() + 8
        files.setFixedHeight(row * min(max(files.count(), 1), _FILES_ROWS) + 2 * files.frameWidth())
        self._message.setPlainText(default_message(cplan))
        self._branch_label.setText("Custom branch: checking...")
        self._set_state("probing")

    def apply_probe(self, probe: CommitProbe):
        """Switch to the probe's state and show what it found."""
        self._probe = probe
        if probe.branch:
            self._branch_label.setText(f"Custom branch: {probe.branch}")
        elif probe.state != "ready":
            self._branch_label.setText("Custom branch: not available")
        if probe.parent_dir is not None:
            where = probe.parent_dir.as_posix()
            self._parent_label.setText(
                f"Parent repo: {where} ({probe.parent_branch})" if probe.parent_branch else f"Parent repo: {where}"
            )
            self._parent_label.show()
        else:
            self._parent_label.hide()
        if probe.parent_ok:
            self._parent_check.setText(f"{_PARENT_TEXT} ({probe.parent_branch})".replace("&", "&&"))
            self._parent_check.setChecked(True)
            self._parent_reason.hide()
        else:
            self._parent_check.setText(_PARENT_TEXT)
            self._parent_check.setChecked(False)
            if probe.state == "ready":
                self._parent_reason.setText(f"Parent commit unavailable: {probe.parent_reason}")
                self._parent_reason.show()
        prefix = {"unavailable": "Commit unavailable: ", "refused": "Commit refused: "}.get(probe.state, "")
        self._status.setText(f"{prefix}{probe.reason}" if probe.state != "ready" else "")
        self._set_state(probe.state)

    def set_committing(self):
        self._step.setText("Committing...")
        self._set_state("committing")

    def set_step(self, text: str):
        if self._state == "committing":
            self._step.setText(text)

    def show_outcome(self, outcome: CommitOutcome):
        """Show what the commit did: done, failed after a partial success (D-03), or back to ready after a refusal."""
        for label in self._outcome_labels:
            self._outcome_layout.removeWidget(label)
            label.hide()
            label.setParent(None)
            label.deleteLater()
        self._outcome_labels = []
        for issue in outcome.issues:
            if issue.severity not in (Severity.SUCCESS, Severity.INFO, Severity.ERROR):
                continue
            label = _plain_label()
            label.setText(issue.text)
            color = _LINE_COLORS.get(issue.severity)
            label.setStyleSheet(f"color: {color};" if color else "")
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._outcome_labels.append(label)
            self._outcome_layout.addWidget(label)
        self._committed = outcome.committed
        if outcome.committed:
            self._set_state("failed" if outcome.failed else "done")
        else:
            self._set_state("ready")

    # -- internals -------------------------------------------------------------------------------

    def _set_state(self, state: str):
        self._state = state
        ready = state == "ready"
        self._message.setReadOnly(not ready)
        self._parent_check.setEnabled(ready and self._probe is not None and self._probe.parent_ok)
        self._step.setVisible(state == "committing")
        if state == "probing":
            self._status.setText("Checking Custom and the parent repo...")
        shows_status = state in ("probing", "unavailable", "refused", "offer_switch")
        self._status.setVisible(shows_status and bool(self._status.text()))
        self._sync_buttons()

    def _sync_buttons(self):
        """Commit is enabled only in the ready state and only with a non-blank message (D-20)."""
        self.commit_button.setEnabled(self._state == "ready" and bool(self._message.toPlainText().strip()))

    def _on_commit_clicked(self):
        if self._state == "ready" and self.commit_button.isEnabled():
            self.commit_requested.emit(self._message.toPlainText(), self.bump_parent())

    def _on_item_activated(self, item: QListWidgetItem):
        rel = item.data(Qt.ItemDataRole.UserRole)
        if rel is not None:
            self.file_activated.emit(rel)
