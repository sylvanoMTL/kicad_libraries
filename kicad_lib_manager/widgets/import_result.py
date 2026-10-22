"""Widgets for the end of an import (Phase 5): the install step text and the Result view."""

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QLabel, QSizePolicy


class ElidedLabel(QLabel):
    """One-line plain-text label that elides its text to fit the width; the full text stays available.

    The size policy is Ignored horizontally, so a long text never widens the layout it sits in.
    """

    def __init__(self, text: str = "", parent=None, *, mode: Qt.TextElideMode = Qt.TextElideMode.ElideRight):
        super().__init__(parent)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._mode = mode
        self._full = ""
        self.set_full_text(text)

    def set_full_text(self, text: str):
        self._full = text
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
