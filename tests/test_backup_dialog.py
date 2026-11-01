"""Offscreen tests for the Restore Backup dialog; the dialog reads no settings."""

import pytest
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from kicad_lib_manager.widgets.backup_dialog import BackupDialog

NO_BACKUPS = "(No backups found)"


def _items(dialog: BackupDialog) -> list[str]:
    return [dialog._list.item(i).text() for i in range(dialog._list.count())]


def _restore_enabled(dialog: BackupDialog) -> bool:
    return dialog._buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()


def _cwd_with_backup(tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "sym-lib-table_backup_1").write_text("(sym_lib_table)\n", encoding="utf-8")
    monkeypatch.chdir(cwd)
    return cwd


@pytest.mark.parametrize("blank", ["", "   "], ids=["empty", "spaces"])
def test_blank_folder_lists_nothing_from_the_working_directory(qtbot, tmp_path, monkeypatch, blank):
    _cwd_with_backup(tmp_path, monkeypatch)

    dialog = BackupDialog(blank)
    qtbot.addWidget(dialog)

    assert dialog._pairs == []
    assert not _restore_enabled(dialog)

    dialog._scan()

    assert dialog._pairs == []
    assert _items(dialog) == [NO_BACKUPS]
    assert not _restore_enabled(dialog)


@pytest.mark.parametrize("blank", ["", "   "], ids=["empty", "spaces"])
def test_blank_folder_cannot_restore(qtbot, tmp_path, monkeypatch, blank):
    folder = tmp_path / "tables"
    folder.mkdir()
    (folder / "sym-lib-table_backup_1").write_text("(sym_lib_table)\n", encoding="utf-8")
    _cwd_with_backup(tmp_path, monkeypatch)
    dialog = BackupDialog(str(folder))
    qtbot.addWidget(dialog)
    dialog._list.setCurrentRow(0)
    assert _restore_enabled(dialog)

    dialog._folder_edit.setText(blank)
    dialog._on_accept()

    assert dialog.selected_folder is None
    assert dialog.selected_backup_num is None
    assert dialog.result() != QDialog.DialogCode.Accepted


def test_folder_with_backups_lists_them_and_restores(qtbot, tmp_path):
    folder = tmp_path / "tables"
    folder.mkdir()
    (folder / "sym-lib-table_backup_2").write_text("(sym_lib_table)\n", encoding="utf-8")
    (folder / "fp-lib-table_backup_2").write_text("(fp_lib_table)\n", encoding="utf-8")

    dialog = BackupDialog(str(folder))
    qtbot.addWidget(dialog)

    assert _items(dialog) == ["Backup #2  —  sym-lib-table + fp-lib-table"]
    dialog._list.setCurrentRow(0)
    assert _restore_enabled(dialog)

    dialog._on_accept()

    assert dialog.selected_backup_num == 2
    assert dialog.selected_folder == folder
    assert dialog.result() == QDialog.DialogCode.Accepted
