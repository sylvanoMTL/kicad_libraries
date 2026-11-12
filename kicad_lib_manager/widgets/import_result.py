"""Widgets for the end of an import (Phase 5): the install step text and the Result view.

Every string that comes from a package or an Issue is shown as plain text, never as markup.
"""

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QFont, QKeyEvent, QResizeEvent
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from ..importer.plan import InstallPlan, InstallResult
from ..models import Severity
from . import theme

_FILES_ROWS = 8  # Files written rows shown before the list scrolls
_STATUS_TITLES = {"library_list": "Library list", "tables": "Library tables"}
_HINT_ROWS = ("generate_hint", "checkout_hint")  # standalone lines, hidden until set
_NO_WARNINGS = "No warnings."
_QWIDGETSIZE_MAX = 16777215  # Qt's "no maximum height"


class ElidedLabel(QLabel):
    """One-line plain-text label that elides its text to fit the width; the full text stays available.

    The size policy is Ignored horizontally, so a long text never widens the layout it sits in.
    """

    def __init__(
        self,
        text: str = "",
        parent=None,
        *,
        mode: Qt.TextElideMode = Qt.TextElideMode.ElideRight,
        full_tooltip: bool = False,
    ):
        super().__init__(parent)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._mode = mode
        self._full_tooltip = full_tooltip
        self._full = ""
        self.set_full_text(text)

    def set_full_text(self, text: str):
        self._full = text
        if self._full_tooltip:
            self.setToolTip(text)
        self._refresh()

    def full_text(self) -> str:
        """The text before eliding."""
        return self._full

    def minimumSizeHint(self) -> QSize:
        return QSize(0, super().minimumSizeHint().height())

    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self):
        width = self.contentsRect().width()
        # width < 40: not laid out yet; show everything and elide on the first real resize
        shown = self._full if width < 40 else self.fontMetrics().elidedText(self._full, self._mode, width)
        if self.text() != shown:
            self.setText(shown)


class _FilesList(QListWidget):
    """The Files written list. Enter opens the current file and stops there.

    A stock list view ignores Enter after activating, which hands it to the dialog's default button
    (Close) and would close the Result view as the file opens.
    """

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self.currentItem()
            if item is not None:
                self.itemActivated.emit(item)
            event.accept()
            return
        super().keyPressEvent(event)


def _heading(text: str) -> QLabel:
    label = QLabel(text)
    label.setTextFormat(Qt.TextFormat.PlainText)
    font = label.font()
    font.setBold(True)
    font.setPointSize(theme.HEADING_PT)
    label.setFont(font)
    return label


def _plain_label(*, wrap: bool = True) -> QLabel:
    label = QLabel()
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(wrap)
    return label


class ImportResultView(QWidget):
    """What the dialog shows after a successful install (D-15, D-16, D-18).

    From top to bottom: the success banner, the KiCad-running notice (hidden until the dialog finds
    KiCad running), Warnings, the post-install status rows the main window updates, Files written,
    the backup folder and the commit slot (hidden until the dialog puts the Phase 6 commit panel in it). All of
    that scrolls vertically inside one scroll area, so the commit panel fits at the dialog's minimum size;
    Close stays below the scroll area and is always visible.
    """

    file_activated = Signal(object)  # the absolute Path of a written file, on double click or Enter

    def __init__(self, parent=None):
        super().__init__(parent)
        self._backup_dir: Path | None = None
        self._warning_labels: list[QLabel] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(theme.SP_LG)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(theme.SP_LG)

        self._banner = _plain_label()
        font = self._banner.font()
        font.setBold(True)
        font.setPointSize(theme.DISPLAY_PT)
        self._banner.setFont(font)
        self._banner.setStyleSheet(f"color: {theme.SUCCESS};")
        lay.addWidget(self._banner)

        self._kicad_notice = _plain_label()
        self._kicad_notice.setStyleSheet(
            f"background-color: {theme.AMBER_TINT}; padding: {theme.SP_SM}px;"
        )
        self._kicad_notice.setAccessibleName("KiCad is running")
        self._kicad_notice.hide()
        lay.addWidget(self._kicad_notice)

        warnings = QVBoxLayout()
        warnings.setSpacing(theme.SP_XS)
        self._warnings_heading = _heading("Warnings")
        warnings.addWidget(self._warnings_heading)
        self._warnings_layout = QVBoxLayout()
        self._warnings_layout.setSpacing(theme.SP_XS)
        warnings.addLayout(self._warnings_layout)
        lay.addLayout(warnings)

        status = QVBoxLayout()
        status.setSpacing(theme.SP_XS)
        self._status_labels: dict[str, QLabel] = {}
        for row in ("library_list", "tables", *_HINT_ROWS):
            label = _plain_label()
            self._status_labels[row] = label
            status.addWidget(label)
        for row in _HINT_ROWS:
            self._status_labels[row].hide()
        lay.addLayout(status)

        files = QVBoxLayout()
        files.setSpacing(theme.SP_XS)
        self._files_heading = _heading("Files written (0)")
        files.addWidget(self._files_heading)
        self._files_list = _FilesList()
        self._files_list.setAccessibleName("Files written")
        self._files_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._files_list.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self._files_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._files_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._files_list.itemActivated.connect(self._on_item_activated)
        files.addWidget(self._files_list)
        lay.addLayout(files)

        # Backup folder: shown only when the install replaced an existing file (it made a backup)
        self._backup_row = QWidget()
        backup_lay = QHBoxLayout(self._backup_row)
        backup_lay.setContentsMargins(0, 0, 0, 0)
        backup_lay.setSpacing(theme.SP_SM)
        self._backup_label = ElidedLabel(mode=Qt.TextElideMode.ElideMiddle, full_tooltip=True)
        self._backup_label.setFont(QFont(theme.MONO_FAMILY, theme.MONO_PT))
        self._backup_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._backup_label.setAccessibleName("Backup folder")
        backup_lay.addWidget(self._backup_label, stretch=1)
        self.open_folder_button = QPushButton("Open folder")
        self.open_folder_button.clicked.connect(self._on_open_folder)
        backup_lay.addWidget(self.open_folder_button)
        self._backup_row.hide()
        lay.addWidget(self._backup_row)

        # The Phase 6 commit step lives here: hidden at zero height until set_commit_panel puts a panel in
        self.commit_slot = QWidget()
        self.commit_slot.setObjectName("commitSlot")
        slot_lay = QVBoxLayout(self.commit_slot)
        slot_lay.setContentsMargins(0, 0, 0, 0)
        self._commit_panel: QWidget | None = None
        self.commit_slot.setFixedHeight(0)
        self.commit_slot.hide()
        lay.addWidget(self.commit_slot)

        lay.addStretch(1)
        self._scroll.setWidget(body)
        outer.addWidget(self._scroll, 1)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.close_button = QPushButton("Close")
        buttons.addWidget(self.close_button)
        outer.addLayout(buttons)

        self._set_warnings(())
        self._reset_status()

    # -- filling the view ------------------------------------------------------------------------

    def show_result(self, result: InstallResult, plan: InstallPlan, repo_root: Path):
        """Fill every block from a successful install. The status rows start without a state."""
        self.clear_commit_panel()
        self._banner.setText(f"✓ Installed {plan.symbol_name} into {result.library}")
        self._kicad_notice.hide()
        self._set_warnings(result.issues)
        self._reset_status()
        self._fill_files(result.touched, Path(repo_root))
        self._backup_dir = result.backup_dir
        if result.backup_dir is None:
            self._backup_row.hide()
        else:
            self._backup_label.set_full_text(f"Backup folder: {result.backup_dir}")
            self._backup_row.show()

    def set_commit_panel(self, panel: QWidget):
        """Put the Phase 6 commit panel into the slot and open the slot to its natural height."""
        self.clear_commit_panel()
        self._commit_panel = panel
        self.commit_slot.layout().addWidget(panel)
        self.commit_slot.setMinimumHeight(0)
        self.commit_slot.setMaximumHeight(_QWIDGETSIZE_MAX)
        self.commit_slot.show()

    def clear_commit_panel(self):
        """Remove any panel and collapse the slot again: hidden, zero height (a failed or empty install has none)."""
        panel, self._commit_panel = self._commit_panel, None
        if panel is not None:
            self.commit_slot.layout().removeWidget(panel)
            panel.hide()
            panel.setParent(None)
            panel.deleteLater()
        self.commit_slot.setFixedHeight(0)
        self.commit_slot.hide()

    def _set_warnings(self, issues):
        for label in self._warning_labels:
            self._warnings_layout.removeWidget(label)
            label.hide()
            label.setParent(None)
            label.deleteLater()
        self._warning_labels = []
        shown = [issue for issue in issues if issue.severity in (Severity.WARNING, Severity.ERROR)]
        if not shown:
            label = _plain_label()
            label.setText(_NO_WARNINGS)
            label.setStyleSheet(f"color: {theme.MUTED};")
            self._add_warning(label)
        for issue in shown:
            warning = issue.severity is Severity.WARNING
            label = _plain_label()
            label.setText(f"{'⚠' if warning else '✖'} {issue.text}")
            label.setStyleSheet(f"color: {theme.AMBER if warning else theme.ERROR};")
            self._add_warning(label)

    def _add_warning(self, label: QLabel):
        self._warning_labels.append(label)
        self._warnings_layout.addWidget(label)

    def _reset_status(self):
        for row, title in _STATUS_TITLES.items():
            label = self._status_labels[row]
            label.setText(title)
            label.setStyleSheet("")
        for row in _HINT_ROWS:
            hint = self._status_labels[row]
            hint.setText("")
            hint.hide()

    def _fill_files(self, touched, repo_root: Path):
        files = self._files_list
        files.clear()
        for path in touched:
            try:
                shown = Path(path).relative_to(repo_root).as_posix()
            except ValueError:
                shown = Path(path).as_posix()
            item = QListWidgetItem(shown)
            item.setToolTip(shown)
            item.setData(Qt.ItemDataRole.UserRole, Path(path))
            files.addItem(item)
        self._files_heading.setText(f"Files written ({files.count()})")
        # Up to eight rows tall, then the list scrolls
        row = files.sizeHintForRow(0) if files.count() else files.fontMetrics().height() + 8
        files.setFixedHeight(row * min(max(files.count(), 1), _FILES_ROWS) + 2 * files.frameWidth())

    # -- updates from the dialog and the main window ---------------------------------------------

    def set_kicad_running(self, text: str):
        """Show the notice that KiCad is open and must reopen its editors (POST-05, D-18); the dialog words it."""
        self._kicad_notice.setText(f"⚠ {text}")
        self._kicad_notice.show()

    def set_status(self, row: str, text: str, severity: Severity):
        """Set one post-install status row: library_list, tables, generate_hint, or
        checkout_hint (D-16, D-17, D-26).

        The first two read "{Row title}: {text}"; a hint is a line of its own and appears when set.
        """
        label = self._status_labels[row]
        title = _STATUS_TITLES.get(row)
        label.setText(f"{title}: {text}" if title else text)
        color = {Severity.SUCCESS: theme.SUCCESS, Severity.ERROR: theme.ERROR, Severity.WARNING: theme.AMBER}.get(severity)
        label.setStyleSheet(f"color: {color};" if color else "")
        label.show()

    def status_text(self, row: str) -> str:
        return self._status_labels[row].text()

    # -- actions ---------------------------------------------------------------------------------

    def _on_item_activated(self, item: QListWidgetItem):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path is not None:
            self.file_activated.emit(path)

    def _on_open_folder(self):
        # Only the folder the app made for this install; nothing taken from a package is ever opened (T-05-34)
        if self._backup_dir is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._backup_dir)))
