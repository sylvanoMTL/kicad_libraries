from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QDialogButtonBox, QFileDialog,
)

from ..table_generator import list_backups


class BackupDialog(QDialog):
    def __init__(self, default_folder: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Restore Backup")
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)

        self.selected_backup: Path | None = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Select folder to scan for backups:"))

        folder_row = QHBoxLayout()
        self._folder_edit = QLineEdit(default_folder)
        folder_row.addWidget(self._folder_edit)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        scan_btn = QPushButton("Scan for backups")
        scan_btn.clicked.connect(self._scan)
        layout.addWidget(scan_btn)

        self._list = QListWidget()
        layout.addWidget(self._list)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Restore")
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

        self._list.currentRowChanged.connect(self._on_selection_changed)
        self._backups: list[Path] = []

        if default_folder:
            self._scan()

    def _browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select backup folder", self._folder_edit.text()
        )
        if folder:
            self._folder_edit.setText(folder)
            self._scan()

    def _scan(self):
        self._list.clear()
        self._backups.clear()
        folder = Path(self._folder_edit.text())
        if folder.exists():
            self._backups = list_backups(folder)
            for backup in self._backups:
                self._list.addItem(backup.name)

        if not self._backups:
            self._list.addItem("(No backups found)")

    def _on_selection_changed(self, row: int):
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            0 <= row < len(self._backups)
        )

    def _on_accept(self):
        row = self._list.currentRow()
        if 0 <= row < len(self._backups):
            self.selected_backup = self._backups[row]
            self.accept()
