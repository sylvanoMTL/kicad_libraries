"""The remembered import folder (plan 05-05, UX-02): import/last_dir through settings.py."""

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from kicad_lib_manager import settings


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path / "qsettings"),
    )
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents


def test_nothing_stored_gives_none():
    assert settings.load_import_dir() is None


def test_import_dir_round_trip(tmp_path):
    folder = tmp_path / "packages"
    folder.mkdir()
    settings.save_import_dir(folder)
    assert settings.load_import_dir() == folder


def test_deleted_import_dir_gives_none(tmp_path):
    folder = tmp_path / "packages"
    folder.mkdir()
    settings.save_import_dir(folder)
    folder.rmdir()
    assert settings.load_import_dir() is None


def test_stored_file_is_not_a_folder(tmp_path):
    a_file = tmp_path / "not_a_folder.zip"
    a_file.write_bytes(b"PK")
    settings.save_import_dir(a_file)
    assert settings.load_import_dir() is None


def test_import_dir_uses_the_import_group_key(tmp_path):
    settings.save_import_dir(tmp_path)
    assert settings.get_settings().value("import/last_dir") == str(tmp_path)
