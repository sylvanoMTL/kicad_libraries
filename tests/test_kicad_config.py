"""KiCad version selection and kicad_common.json sync on synthetic trees.

Nothing here touches the owner's real %APPDATA% KiCad config or the real
app-data backup folder: every call passes config_base, backup_root and running.
"""

from pathlib import Path

import pytest

from kicad_lib_manager import library_scanner
from kicad_lib_manager.library_scanner import (
    find_kicad_config_dir,
    find_kicad_footprint_dir,
    newest_version_dirs,
    parse_version,
)


# -- Task 1: numeric version selection (D-12, HARD-04) ---------------------------


def test_parse_version_reads_dotted_integers():
    assert parse_version("10.0") == (10, 0)
    assert parse_version("9.0.1") == (9, 0, 1)


@pytest.mark.parametrize("name", ["10.0-rc1", "kicad-extras", "", "v9"])
def test_parse_version_rejects_other_names(name):
    assert parse_version(name) is None


def _make_versions(base: Path, *names: str) -> None:
    for name in names:
        (base / name).mkdir(parents=True)


def test_newest_version_dirs_orders_numerically_and_skips_files(tmp_path):
    _make_versions(tmp_path, "7.0", "8.0", "9.0", "10.0", "kicad-extras")
    (tmp_path / "11.0").write_text("not a directory")
    assert [p.name for p in newest_version_dirs(tmp_path)] == ["10.0", "9.0", "8.0", "7.0"]


def test_newest_version_dirs_of_missing_parent_is_empty(tmp_path):
    assert newest_version_dirs(tmp_path / "nope") == []


def test_config_dir_prefers_ten_over_nine(tmp_path):
    _make_versions(tmp_path, "9.0", "10.0")
    assert find_kicad_config_dir(base=tmp_path) == tmp_path / "10.0"


def test_config_dir_missing_base_is_none(tmp_path):
    assert find_kicad_config_dir(base=tmp_path / "nope") is None


def test_config_dir_with_only_non_numeric_folders_is_none(tmp_path):
    _make_versions(tmp_path, "kicad-extras", "10.0-rc1")
    assert find_kicad_config_dir(base=tmp_path) is None


def _footprints(prog: Path, version: str) -> Path:
    fp = prog / version / "share" / "kicad" / "footprints"
    fp.mkdir(parents=True)
    return fp


def test_footprint_dir_prefers_ten_over_nine_on_windows(tmp_path):
    _footprints(tmp_path, "9.0")
    ten = _footprints(tmp_path, "10.0")
    assert find_kicad_footprint_dir(base=tmp_path, platform="win32") == ten


def test_footprint_dir_falls_back_when_newest_lacks_footprints(tmp_path):
    nine = _footprints(tmp_path, "9.0")
    (tmp_path / "10.0").mkdir()
    assert find_kicad_footprint_dir(base=tmp_path, platform="win32") == nine


def test_footprint_dir_on_linux_uses_base_footprints(tmp_path):
    (tmp_path / "footprints").mkdir()
    assert find_kicad_footprint_dir(base=tmp_path, platform="linux") == tmp_path / "footprints"


def test_footprint_dir_missing_base_is_none(tmp_path):
    assert find_kicad_footprint_dir(base=tmp_path / "nope", platform="win32") is None
