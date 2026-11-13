"""Loading Libraries window: scan progress plus a Skip button for one source's 3D model path check (G-12-21).

Qt's own progress dialog hides itself when its button is clicked, so it cannot offer a Skip that
lets the scan go on. This small dialog shows the progress, offers Skip while a source's symbols
are read and while its 3D model paths are checked (a Skip pressed early is an advance skip of that
check), remembers every source asked for, and closes only when the window that owns it says the
scan is over.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
)

from .theme import SP_MD, SP_SM

_MIN_WIDTH = 420


class ScanProgressDialog(QDialog):
    skip_requested = Signal(str)  # the source whose 3D model path check should stop

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Loading Libraries")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(_MIN_WIDTH)
        self._finished = False
        self._source: str | None = None
        self._requested: set[str] = set()

        self._label = QLabel("Scanning libraries...")
        self._label.setTextFormat(Qt.TextFormat.PlainText)
        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)

        self.skip_button = QPushButton("Skip")
        self.skip_button.setAutoDefault(False)
        self.skip_button.setDefault(False)
        self._show_idle()
        self.skip_button.clicked.connect(self._on_skip_clicked)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.skip_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SP_MD, SP_MD, SP_MD, SP_MD)
        layout.setSpacing(SP_SM)
        layout.addWidget(self._label)
        layout.addWidget(self._bar)
        layout.addLayout(buttons)

    def set_progress(self, text: str, value: int):
        self._label.setText(text)
        self._bar.setValue(value)

    def set_skippable(self, source: str | None):
        """Offer Skip for source, or switch it off; a source already asked for keeps its 'Skipping' text."""
        self._source = source
        if source is None:
            self._show_idle()
            return
        self.skip_button.setToolTip(
            f"Stop checking the 3D model paths of {source}, now or when the scan reaches them. "
            "Its libraries are still listed, and Rescan checks them again."
        )
        if source in self._requested:
            self.skip_button.setText(f"Skipping {source}...")
            self.skip_button.setEnabled(False)
            return
        self.skip_button.setText(f"Skip {source}")
        self.skip_button.setEnabled(True)

    def finish(self):
        """The scan is over: from now on the dialog may close."""
        self._finished = True
        self.close()

    def reject(self):
        # Escape and the title-bar X both end here; the scan cannot be cancelled
        if self._finished:
            super().reject()

    def _show_idle(self):
        self.skip_button.setText("Skip")
        self.skip_button.setToolTip(
            "Skip is offered once the scan starts reading a library source."
        )
        self.skip_button.setEnabled(False)

    def _on_skip_clicked(self):
        source = self._source
        if source is None:
            return
        self._requested.add(source)
        self.skip_button.setText(f"Skipping {source}...")
        self.skip_button.setEnabled(False)
        self.skip_requested.emit(source)
