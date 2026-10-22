from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from ..importer.preview import PreviewSection


class PreviewTree(QTreeWidget):
    """Sectioned tree of the plan preview: one bold header per section, one child per row."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(2)
        self.setHeaderLabels(["Item", "Detail"])
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(True)
        self._sections: tuple[PreviewSection, ...] = ()

    @property
    def sections(self) -> tuple[PreviewSection, ...]:
        return self._sections

    def render(self, sections: tuple[PreviewSection, ...]) -> None:
        """Replace the tree contents with the given sections."""
        self._sections = tuple(sections)
        self.clear()
        bold = self.font()
        bold.setBold(True)
        for section in self._sections:
            header = QTreeWidgetItem([section.title])
            header.setFont(0, bold)
            self.addTopLevelItem(header)
            for row in section.rows:
                # Plain item text: QTreeWidgetItem never interprets markup
                child = QTreeWidgetItem([row.text, row.detail])
                child.setData(0, Qt.ItemDataRole.UserRole, row)
                header.addChild(child)
            header.setExpanded(True)
        self.resizeColumnToContents(1)
