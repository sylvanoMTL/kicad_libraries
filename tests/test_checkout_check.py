"""The D-26 wrong-checkout check: compares the app's repo folder with the folder
KiCad's KICAD_LIB_GITHUB names, read from the newest kicad_common.json.

Nothing here touches the owner's real %APPDATA% KiCad config: every call passes
config_base. Used by Generate Tables, Install Part, the migration and the chooser.
"""

import json
from pathlib import Path

import pytest

from kicad_lib_manager import kicad_setup
from kicad_lib_manager.models import Severity


def _dump(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def _write_common(cfg, version, obj):
    folder = cfg / version
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "kicad_common.json"
    path.write_text(_dump(obj), encoding="utf-8")
    return path


def _vars_config(value):
    return {"environment": {"vars": {"KICAD_LIB_GITHUB": value} if value is not None else None}}


def test_mismatch_names_both_folders(tmp_path):
    cfg = tmp_path / "cfg"
    repo = tmp_path / "repo"
    other = tmp_path / "other"
    _write_common(cfg, "10.0", _vars_config(str(other)))

    mismatch = kicad_setup.checkout_mismatch(repo, config_base=cfg)

    assert mismatch is not None
    assert mismatch.app_folder == str(repo).replace("\\", "/")
    assert mismatch.kicad_folder == str(other).replace("\\", "/")


def test_same_checkout_is_none(tmp_path):
    cfg = tmp_path / "cfg"
    repo = tmp_path / "repo"
    repo.mkdir()
    spelled = str(repo).replace("/", "\\") + "\\"
    if __import__("sys").platform == "win32":
        spelled = spelled.upper()
    _write_common(cfg, "10.0", _vars_config(spelled))

    assert kicad_setup.checkout_mismatch(repo, config_base=cfg) is None


def test_absent_config_folder_is_none(tmp_path):
    cfg = tmp_path / "cfg"
    repo = tmp_path / "repo"
    assert kicad_setup.checkout_mismatch(repo, config_base=cfg) is None


def test_absent_kicad_common_file_is_none(tmp_path):
    cfg = tmp_path / "cfg"
    repo = tmp_path / "repo"
    (cfg / "10.0").mkdir(parents=True)
    assert kicad_setup.checkout_mismatch(repo, config_base=cfg) is None


def test_absent_vars_key_is_none(tmp_path):
    cfg = tmp_path / "cfg"
    repo = tmp_path / "repo"
    _write_common(cfg, "10.0", {"system": {"a": 1}})
    assert kicad_setup.checkout_mismatch(repo, config_base=cfg) is None


def test_null_vars_is_none(tmp_path):
    cfg = tmp_path / "cfg"
    repo = tmp_path / "repo"
    _write_common(cfg, "10.0", {"environment": {"vars": None}})
    assert kicad_setup.checkout_mismatch(repo, config_base=cfg) is None


def test_blank_value_is_none(tmp_path):
    cfg = tmp_path / "cfg"
    repo = tmp_path / "repo"
    _write_common(cfg, "10.0", _vars_config("   "))
    assert kicad_setup.checkout_mismatch(repo, config_base=cfg) is None


def test_non_string_value_is_none(tmp_path):
    cfg = tmp_path / "cfg"
    repo = tmp_path / "repo"
    _write_common(cfg, "10.0", {"environment": {"vars": {"KICAD_LIB_GITHUB": 123}}})
    assert kicad_setup.checkout_mismatch(repo, config_base=cfg) is None


def test_invalid_json_is_none(tmp_path):
    cfg = tmp_path / "cfg"
    repo = tmp_path / "repo"
    path = cfg / "10.0" / "kicad_common.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(b'{"environment": ')
    assert kicad_setup.checkout_mismatch(repo, config_base=cfg) is None


def test_newest_version_wins(tmp_path):
    cfg = tmp_path / "cfg"
    repo = tmp_path / "repo"
    other = tmp_path / "other"
    _write_common(cfg, "9.0", _vars_config(str(repo)))
    _write_common(cfg, "10.0", _vars_config(str(other)))

    mismatch = kicad_setup.checkout_mismatch(repo, config_base=cfg)

    assert mismatch is not None
    assert mismatch.kicad_folder == str(other).replace("\\", "/")


def test_warning_text(tmp_path):
    cfg = tmp_path / "cfg"
    repo = tmp_path / "repo"
    other = tmp_path / "other"
    mismatch = kicad_setup.wrong_checkout(repo, str(other))

    text = kicad_setup.wrong_checkout_warning(mismatch)

    assert str(repo).replace("\\", "/") in text
    assert str(other).replace("\\", "/") in text
    assert "push them from here, then pull there" in text
    assert "will not see the new libraries or parts" in text
