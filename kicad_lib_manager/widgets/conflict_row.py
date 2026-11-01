"""One row per install conflict (Phase 5, PREV-05, D-12): Overwrite, Rename or Skip, never decided for the user.

The row holds the user's choice for one Conflict.key and tells the dialog about it with signals; the
dialog keeps the choices (by key, D-14a) and rebuilds the plan. There is no bulk control anywhere: a
row starts with no button checked, so every conflict needs its own click.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontMetrics, QKeyEvent, QMouseEvent, QResizeEvent
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QVBoxLayout,
)

from ..importer.form import kind_label
from ..importer.plan import Conflict, Resolution
from .theme import (
    ACCENT, AMBER, BORDER, ERROR, FIELD_FRAME_QSS, MUTED, SP_SM, SP_XS, SUCCESS, SURFACE, SURFACE_BASE,
    SURFACE_HEADER,
)

NEEDS_CHOICE = "Needs a choice"
_ACTIONS = ("overwrite", "rename", "skip")
_BUTTON_TEXT = {"overwrite": "Overwrite", "rename": "Rename", "skip": "Skip"}
_CHECKED_FILL = {"overwrite": ERROR, "rename": ACCENT, "skip": ACCENT}
_RENAME_MIN_WIDTH = 160
_BUTTON_PAD = 12
_ROW_QSS = "\n".join([
    f"QFrame#conflictRow {{ background-color: {SURFACE}; border: 1px solid {BORDER}; border-left: 4px solid {AMBER}; }}",
    f'QFrame#conflictRow[resolved="true"] {{ border-left: 4px solid {SUCCESS}; }}',
    f"QFrame#conflictRow:focus {{ background-color: {SURFACE_HEADER}; }}",
])


def _button_qss(fill: str) -> str:
    return "\n".join([
        f"QPushButton {{ background-color: {SURFACE_BASE}; border: 1px solid {BORDER}; border-radius: 2px; "
        f"padding: 4px {_BUTTON_PAD}px; min-height: 16px; }}",
        f"QPushButton:checked {{ background-color: {fill}; border-color: {fill}; color: {SURFACE_BASE}; "
        "font-weight: bold; }",
    ])


class _ElidedLabel(QLabel):
    """One-line plain-text label that elides the middle of its text to the room it gets; the tooltip keeps all of it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextFormat(Qt.TextFormat.PlainText)
        # Ignored: a long name must never widen the pane, it is cut in the middle instead
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._full = ""

    def set_full_text(self, text: str):
        self._full = text
        self.setToolTip(text)
        self._refresh()

    def full_text(self) -> str:
        return self._full

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        width = self.contentsRect().width()
        shown = self._full
        # width < 40: not laid out yet; show everything and elide on the first real resize
        if width >= 40 and self.fontMetrics().horizontalAdvance(self._full) > width:
            shown = self.fontMetrics().elidedText(self._full, Qt.TextElideMode.ElideMiddle, width)
        if self.text() != shown:
            self.setText(shown)


class ConflictRow(QFrame):
    """Three manually exclusive toggles for one conflict, a rename field and a one-line hint.

    Signals: choice_changed(key, Resolution | None) when the user picks an action (the checked button
    clicked again changes nothing); rename_edited(key, text) while the user types a new name;
    activated(key) on a double click, or Enter or Space on the focused row (opens the content view).
    Programmatic updates (set_resolution, update_conflict) never emit.
    """

    choice_changed = Signal(str, object)
    rename_edited = Signal(str, str)
    activated = Signal(str)

    def __init__(self, conflict: Conflict, parent=None):
        super().__init__(parent)
        self._conflict = conflict
        self._action: str | None = None
        self._touched = False  # the user typed in the rename field
        self._suggested = conflict.suggested_name
        self.setObjectName("conflictRow")
        self.setStyleSheet(_ROW_QSS)
        self.setProperty("resolved", False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(SP_SM, SP_SM, SP_SM, SP_SM)
        lay.setSpacing(SP_XS)

        # Line 1: kind (bold), name and where it lives (elided), and the marker while undecided
        line1 = QHBoxLayout()
        line1.setSpacing(SP_SM)
        self._kind_label = QLabel()
        self._kind_label.setTextFormat(Qt.TextFormat.PlainText)
        bold = self._kind_label.font()
        bold.setBold(True)
        self._kind_label.setFont(bold)
        line1.addWidget(self._kind_label)
        self._title_label = _ElidedLabel()
        line1.addWidget(self._title_label, 1)
        self._needs_label = QLabel(NEEDS_CHOICE)
        self._needs_label.setTextFormat(Qt.TextFormat.PlainText)
        self._needs_label.setFont(bold)
        self._needs_label.setStyleSheet(f"color: {AMBER};")
        line1.addWidget(self._needs_label)
        lay.addLayout(line1)

        # Line 2: the three toggles, kept exclusive by hand so the checked one can stay checked
        line2 = QHBoxLayout()
        line2.setSpacing(SP_SM)
        self._group = QButtonGroup(self)
        self._group.setExclusive(False)
        self._buttons: dict[str, QPushButton] = {}
        bold_metrics = QFontMetrics(QFont(bold))
        for action in _ACTIONS:
            button = QPushButton(_BUTTON_TEXT[action])
            button.setCheckable(True)
            button.setAutoDefault(False)
            button.setDefault(False)
            button.setStyleSheet(_button_qss(_CHECKED_FILL[action]))
            # Reserve the bold width, so checking a button does not move its neighbours
            button.setMinimumWidth(bold_metrics.horizontalAdvance(_BUTTON_TEXT[action]) + 2 * _BUTTON_PAD + 4)
            button.clicked.connect(lambda _checked=False, a=action: self._on_click(a))
            self._group.addButton(button)
            self._buttons[action] = button
            line2.addWidget(button)
        line2.addStretch(1)
        self._overwrite_btn = self._buttons["overwrite"]
        self._rename_btn = self._buttons["rename"]
        self._skip_btn = self._buttons["skip"]
        lay.addLayout(line2)

        # The rename field sits on its own line: beside the buttons it would be wider than the left pane
        self._rename_frame = QFrame()
        self._rename_frame.setObjectName("fieldFrame")
        self._rename_frame.setStyleSheet(FIELD_FRAME_QSS)
        self._rename_frame.setProperty("blocked", False)
        frame_lay = QVBoxLayout(self._rename_frame)
        frame_lay.setContentsMargins(0, 0, 0, 0)
        frame_lay.setSpacing(0)
        self._rename_edit = QLineEdit()
        self._rename_edit.setMinimumWidth(_RENAME_MIN_WIDTH)
        self._rename_edit.setMinimumHeight(28)
        self._rename_edit.textEdited.connect(self._on_rename_edited)
        self._rename_edit.textChanged.connect(lambda _text: self._refresh_hint())
        frame_lay.addWidget(self._rename_edit)
        self._rename_frame.hide()
        lay.addWidget(self._rename_frame)

        # Line 3: what the chosen action will do
        self._hint_label = QLabel()
        self._hint_label.setTextFormat(Qt.TextFormat.PlainText)
        self._hint_label.setWordWrap(True)
        self._hint_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._hint_label.hide()
        lay.addWidget(self._hint_label)

        self._rename_edit.setText(self._suggested)
        self._show_conflict()
        self._refresh()

    # -- the conflict ---------------------------------------------------------------------------

    @property
    def key(self) -> str:
        return self._conflict.key

    @property
    def overwrite_button(self) -> QPushButton:
        return self._overwrite_btn

    @property
    def rename_edit(self) -> QLineEdit:
        return self._rename_edit

    @property
    def rename_frame(self) -> QFrame:
        return self._rename_frame

    def update_conflict(self, conflict: Conflict):
        """The same conflict from a newer plan: refresh the texts; a name the user typed is kept."""
        self._conflict = conflict
        if not self._touched:
            self._suggested = conflict.suggested_name
            if self._action != "rename":
                self._set_rename_text(self._suggested)
        self._show_conflict()
        self._refresh_hint()

    def _show_conflict(self):
        conflict = self._conflict
        kind = kind_label(conflict.kind)
        self._kind_label.setText(kind)
        self._title_label.set_full_text(f"{conflict.name} — {conflict.existing}")
        self.setAccessibleName(f"Conflict: {kind} {conflict.name}")
        for action, button in self._buttons.items():
            button.setAccessibleName(f"{_BUTTON_TEXT[action]} {kind} {conflict.name}")
        self._rename_edit.setAccessibleName(f"New name for {kind} {conflict.name}")

    # -- the choice -----------------------------------------------------------------------------

    def current_resolution(self) -> Resolution | None:
        if self._action is None:
            return None
        if self._action == "rename":
            return Resolution("rename", self._rename_edit.text())
        return Resolution(self._action)

    def set_resolution(self, resolution: Resolution | None):
        """Show a choice the dialog holds; nothing is emitted."""
        self._action = resolution.action if resolution is not None and resolution.action in _ACTIONS else None
        if self._action == "rename" and resolution.rename_to is not None:
            self._set_rename_text(resolution.rename_to)
        self._refresh()

    def _on_click(self, action: str):
        if action == self._action:
            self._sync_buttons()  # the checked button was toggled off by the click: put it back
            return
        self._action = action
        if action == "rename" and not self._touched:
            self._set_rename_text(self._suggested)
        self._refresh()
        self.choice_changed.emit(self.key, self.current_resolution())

    def _on_rename_edited(self, text: str):
        self._touched = True
        self.rename_edited.emit(self.key, text)

    def _set_rename_text(self, text: str):
        if self._rename_edit.text() == text:
            return  # setText would move the cursor
        self._rename_edit.blockSignals(True)
        try:
            self._rename_edit.setText(text)
        finally:
            self._rename_edit.blockSignals(False)
        self._refresh_hint()

    # -- looks ----------------------------------------------------------------------------------

    def _sync_buttons(self):
        for action, button in self._buttons.items():
            button.blockSignals(True)
            try:
                button.setChecked(action == self._action)
            finally:
                button.blockSignals(False)

    def _refresh(self):
        self._sync_buttons()
        renaming = self._action == "rename"
        self._rename_frame.setVisible(renaming)
        self._needs_label.setVisible(self._action is None)
        self._refresh_hint()
        # The bar is green once the conflict is settled; a Rename still without a name is not settled
        blank_rename = renaming and not self._rename_edit.text().strip()
        resolved = self._action is not None and not blank_rename
        if bool(self.property("resolved")) != resolved:
            self.setProperty("resolved", resolved)
            self.style().unpolish(self)
            self.style().polish(self)

    def _refresh_hint(self):
        action = self._action
        label = self._hint_label
        label.setVisible(action is not None)
        if action is None:
            return
        kind = kind_label(self._conflict.kind)
        if action == "overwrite":
            text = f"Overwrite - replace the existing {kind} with the incoming one (a backup is kept)"
        elif action == "rename":
            name = self._rename_edit.text().strip()
            text = (
                f"Rename - install as {name} and leave the existing {kind} untouched"
                if name
                else f"Rename - enter the name to install the {kind} as; the existing {kind} stays untouched"
            )
        else:
            text = f"Skip - keep the existing {kind} and link it"
        label.setText(text)
        label.setStyleSheet(f"color: {ERROR if action == 'overwrite' else MUTED};")

    # -- activation -----------------------------------------------------------------------------

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.activated.emit(self.key)
        event.accept()

    def keyPressEvent(self, event: QKeyEvent):
        # Only when the row itself has focus: a child that ignores Enter must not open the view
        if self.hasFocus() and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.activated.emit(self.key)
            event.accept()
            return
        super().keyPressEvent(event)
