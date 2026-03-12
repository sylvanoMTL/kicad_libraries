from datetime import datetime

from PySide6.QtWidgets import QVBoxLayout, QWidget, QTextEdit, QLabel
from PySide6.QtGui import QFont


COLORS = {
    "info": "#000000",
    "warning": "#CC7700",
    "error": "#CC0000",
    "success": "#007700",
}


class LogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel("Log")
        label.setStyleSheet("font-weight: bold;")
        layout.addWidget(label)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setFont(QFont("Consolas", 9))
        self._text.setMaximumHeight(180)
        layout.addWidget(self._text)

    def log(self, message: str, level: str = "info"):
        color = COLORS.get(level, COLORS["info"])
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._text.append(
            f'<span style="color:{color}">[{timestamp}] {message}</span>'
        )

    def clear(self):
        self._text.clear()
