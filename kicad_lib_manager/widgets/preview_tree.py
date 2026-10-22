from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QGuiApplication, QKeySequence
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTreeWidget, QTreeWidgetItem

from ..importer.preview import PreviewRow, PreviewSection
from . import theme

_TONE_COLORS = {
    "success": theme.SUCCESS,
    "muted": theme.MUTED,
    "warning": theme.AMBER,
    "error": theme.ERROR,
}
_NEEDS_CHOICE = "Needs a choice"


class PreviewTree(QTreeWidget):
    """Sectioned tree of the plan preview: one Heading header per section, one child per row."""

    row_activated = Signal(object)  # PreviewRow of a non-header row, on double click or Enter

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHeaderLabels(["Item", "Detail"])
        header = self.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(True)
        self.setWordWrap(True)
        self.setUniformRowHeights(False)
        self.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.itemDoubleClicked.connect(self._on_double_clicked)
        self._sections: tuple[PreviewSection, ...] = ()

    @property
    def sections(self) -> tuple[PreviewSection, ...]:
        return self._sections

    # -- rendering ---------------------------------------------------------------------------

    def render(self, sections: tuple[PreviewSection, ...]) -> None:
        """Replace the tree contents; section expand state and the vertical scroll position are kept (D-06)."""
        self._sections = tuple(sections)
        # Section headers keep their bare name in UserRole, so the state is keyed by name and not by the counted title
        expanded = {
            self.topLevelItem(i).data(0, Qt.ItemDataRole.UserRole): self.topLevelItem(i).isExpanded()
            for i in range(self.topLevelItemCount())
        }
        bar = self.verticalScrollBar()
        scroll = bar.value()
        self.setUpdatesEnabled(False)
        try:
            self.clear()
            heading = QFont(self.font())
            heading.setPointSize(theme.HEADING_PT)
            heading.setBold(True)
            background = QBrush(QColor(theme.SURFACE_HEADER))
            for section in self._sections:
                header = QTreeWidgetItem([section.title])
                header.setData(0, Qt.ItemDataRole.UserRole, section.name)
                header.setFont(0, heading)
                header.setBackground(0, background)
                header.setBackground(1, background)
                self.addTopLevelItem(header)
                for row in section.rows:
                    header.addChild(self._row_item(row))
                header.setExpanded(expanded.get(section.name, True))
            self.doItemsLayout()
            bar.setValue(min(scroll, bar.maximum()))
        finally:
            self.setUpdatesEnabled(True)

    def _row_item(self, row: PreviewRow) -> QTreeWidgetItem:
        # Plain item text: QTreeWidgetItem never interprets markup
        item = QTreeWidgetItem([row.text, row.detail])
        item.setData(0, Qt.ItemDataRole.UserRole, row)
        item.setToolTip(0, row.text)
        item.setToolTip(1, row.detail)
        color = _TONE_COLORS.get(row.tone)
        needs_choice = row.detail == _NEEDS_CHOICE
        if color is not None:
            # The tone of a conflict row belongs to its choice, the item keeps the default colour
            for column in ((1,) if needs_choice else (0, 1)):
                item.setForeground(column, QBrush(QColor(color)))
        if row.kind == "file" and row.glyph in ("+", "~"):
            bold = QFont(self.font())
            bold.setBold(True)
            item.setFont(0, bold)
            item.setFont(1, bold)
        if needs_choice:
            bold = QFont(self.font())
            bold.setBold(True)
            item.setFont(1, bold)
        if row.kind == "rewrite":
            item.setFont(1, QFont(theme.MONO_FAMILY, theme.MONO_PT))
        return item

    # -- activation and copy -------------------------------------------------------------------------

    def _row_of(self, item: QTreeWidgetItem | None) -> PreviewRow | None:
        if item is None or item.parent() is None:
            return None
        row = item.data(0, Qt.ItemDataRole.UserRole)
        return row if isinstance(row, PreviewRow) else None

    def _on_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        row = self._row_of(item)
        if row is not None:
            self.row_activated.emit(row)

    def keyPressEvent(self, event) -> None:
        item = self.currentItem()
        if event.matches(QKeySequence.StandardKey.Copy):
            if item is not None:
                QGuiApplication.clipboard().setText(f"{item.text(0)}\t{item.text(1)}")
            event.accept()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            row = self._row_of(item)
            if row is not None:
                self.row_activated.emit(row)
                event.accept()
                return
        super().keyPressEvent(event)
