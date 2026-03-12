from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QDialogButtonBox, QFileDialog,
)

from ..table_generator import list_backup_pairs


class BackupDialog(QDialog):
    def __init__(self, default_folder: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Restore Backup")
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)

        self.selected_backup_num: int | None = None
        self.selected_folder: Path | None = None

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
        self._pairs: list[tuple[int, Path | None, Path | None]] = []

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
        self._pairs.clear()
        folder = Path(self._folder_edit.text())
        if folder.exists():
            self._pairs = list_backup_pairs(folder)
            for num, sym_path, fp_path in self._pairs:
                parts = []
                if sym_path:
                    parts.append("sym-lib-table")
                if fp_path:
                    parts.append("fp-lib-table")
                label = f"Backup #{num}  —  {' + '.join(parts)}"
                self._list.addItem(label)

        if not self._pairs:
            self._list.addItem("(No backups found)")

    def _on_selection_changed(self, row: int):
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            0 <= row < len(self._pairs)
        )

    def _on_accept(self):
        row = self._list.currentRow()
        if 0 <= row < len(self._pairs):
            self.selected_backup_num = self._pairs[row][0]
            self.selected_folder = Path(self._folder_edit.text())
            self.accept()
