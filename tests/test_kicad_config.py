"""KiCad version selection and kicad_common.json sync on synthetic trees.

Nothing here touches the owner's real %APPDATA% KiCad config or the real
app-data backup folder: every call passes config_base, backup_root and running.
"""

import json
import os
import stat
from pathlib import Path

import pytest

from kicad_lib_manager import fsutil, library_scanner
from kicad_lib_manager.models import Severity
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


# -- Task 2: backed-up, verified, atomic kicad_common.json sync (D-13..D-15) ------

NON_ASCII_KEY = "Pr\u00e9f\u00e9rences \u00e9l\u00e9ments"


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "my repo"
    path.mkdir()
    return path


@pytest.fixture
def cfg(tmp_path):
    base = tmp_path / "kicad_cfg"
    base.mkdir()
    return base


@pytest.fixture
def backups(tmp_path):
    return tmp_path / "backups"


def _desired(repo):
    repo_str = str(repo).replace("\\", "/")
    return {
        "KICAD_LIB_GITHUB": repo_str,
        "CUSTOM_3DMODEL_DIR": f"{repo_str}/Custom/3DModels",
    }


def _dump(obj):
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def _write_config(base, version, obj, *, crlf=False, bom=False):
    folder = base / version
    folder.mkdir(parents=True, exist_ok=True)
    text = _dump(obj)
    if crlf:
        text = text.replace("\n", "\r\n")
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    path = folder / "kicad_common.json"
    path.write_bytes(data)
    return path


def _sync(repo, cfg, backups, running=lambda: []):
    return library_scanner.sync_kicad_path_vars(
        repo, config_base=cfg, backup_root=backups, running=running
    )


def _codes(issues):
    return [i.code for i in issues]


def _by_code(issues, code):
    return [i for i in issues if i.code == code]


def _null_vars_config():
    return {
        "appearance": {NON_ASCII_KEY: "caf\u00e9"},
        "environment": {"vars": None},
        "system": {"language": "Default"},
    }


def _backup_dir(backups, version="10.0"):
    return backups / "kicad_common" / version


def test_null_vars_is_rewritten_with_only_vars_changed(repo, cfg, backups):
    original = _null_vars_config()
    path = _write_config(cfg, "10.0", original)
    original_bytes = path.read_bytes()

    issues = _sync(repo, cfg, backups)

    expected = json.loads(json.dumps(original))
    expected["environment"]["vars"] = _desired(repo)
    assert path.read_bytes() == _dump(expected).encode("utf-8")
    (written,) = _by_code(issues, "config.written")
    assert written.severity is Severity.SUCCESS
    assert (_backup_dir(backups) / "kicad_common.json_backup_1").read_bytes() == original_bytes


def test_populated_vars_keep_other_entries_and_report_update(repo, cfg, backups):
    original = {"environment": {"vars": {"WE_3DMODEL_DIR": "D:/we", "KICAD_LIB_GITHUB": "C:/old"}}}
    path = _write_config(cfg, "10.0", original)

    issues = _sync(repo, cfg, backups)

    vars_ = json.loads(path.read_text(encoding="utf-8"))["environment"]["vars"]
    assert vars_["WE_3DMODEL_DIR"] == "D:/we"
    assert vars_["KICAD_LIB_GITHUB"] == _desired(repo)["KICAD_LIB_GITHUB"]
    (updated,) = [i for i in issues if "updated:" in i.text]
    assert "C:/old" in updated.text and _desired(repo)["KICAD_LIB_GITHUB"] in updated.text


def test_environment_without_vars_key_gets_vars(repo, cfg, backups):
    path = _write_config(cfg, "10.0", {"system": {"a": 1}})
    _sync(repo, cfg, backups)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["system"] == {"a": 1}
    assert data["environment"]["vars"] == _desired(repo)


def test_already_correct_writes_nothing_and_makes_no_backup(repo, cfg, backups):
    path = _write_config(cfg, "10.0", {"environment": {"vars": _desired(repo)}})
    before = path.read_bytes()
    mtime = path.stat().st_mtime_ns

    issues = _sync(repo, cfg, backups)

    assert _codes(issues) == ["config.var_ok", "config.var_ok"]
    assert all(i.severity is Severity.INFO for i in issues)
    assert path.read_bytes() == before
    assert path.stat().st_mtime_ns == mtime
    assert not (backups / "kicad_common").exists()


def test_crlf_file_stays_crlf(repo, cfg, backups):
    path = _write_config(cfg, "10.0", _null_vars_config(), crlf=True)
    _sync(repo, cfg, backups)
    data = path.read_bytes()
    assert b"\r\n" in data
    assert b"\n" not in data.replace(b"\r\n", b"")


def test_bom_file_keeps_its_bom(repo, cfg, backups):
    path = _write_config(cfg, "10.0", _null_vars_config(), bom=True)
    _sync(repo, cfg, backups)
    data = path.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf")
    assert json.loads(data[3:].decode("utf-8"))["environment"]["vars"] == _desired(repo)


def _assert_untouched(path, before, backups):
    assert path.read_bytes() == before
    assert not (backups / "kicad_common").exists()


def test_invalid_json_is_an_error_and_writes_nothing(repo, cfg, backups):
    path = cfg / "10.0" / "kicad_common.json"
    path.parent.mkdir()
    path.write_bytes(b'{"environment": ')
    issues = _sync(repo, cfg, backups)
    (bad,) = issues
    assert bad.code == "config.bad_json" and bad.severity is Severity.ERROR
    _assert_untouched(path, b'{"environment": ', backups)


@pytest.mark.parametrize(
    "obj",
    [{"environment": []}, {"environment": {"vars": "x"}}, ["not", "an", "object"]],
)
def test_wrong_shape_is_an_error_and_writes_nothing(repo, cfg, backups, obj):
    path = _write_config(cfg, "10.0", obj)
    before = path.read_bytes()
    issues = _sync(repo, cfg, backups)
    (bad,) = issues
    assert bad.code == "config.bad_shape" and bad.severity is Severity.ERROR
    _assert_untouched(path, before, backups)


def test_newest_dir_without_config_warns_and_leaves_older_version_alone(repo, cfg, backups):
    older = _write_config(cfg, "9.0", _null_vars_config())
    before = older.read_bytes()
    (cfg / "10.0").mkdir()
    issues = _sync(repo, cfg, backups)
    (warn,) = issues
    assert warn.code == "config.not_found" and warn.severity is Severity.WARNING
    assert "10.0" in warn.text
    _assert_untouched(older, before, backups)


def test_only_the_newest_version_is_written(repo, cfg, backups):
    nine = _write_config(cfg, "9.0", _null_vars_config())
    ten = _write_config(cfg, "10.0", _null_vars_config())
    nine_before = nine.read_bytes()
    _sync(repo, cfg, backups)
    assert nine.read_bytes() == nine_before
    assert json.loads(ten.read_text(encoding="utf-8"))["environment"]["vars"] == _desired(repo)


def test_no_config_directory_at_all_warns(repo, cfg, backups):
    issues = _sync(repo, cfg, backups)
    (warn,) = issues
    assert warn.code == "config.dir_not_found" and warn.severity is Severity.WARNING
    assert warn.text.startswith("Could not find KiCad config directory")


def test_invalid_utf8_gives_bad_encoding_and_no_write(repo, cfg, backups):
    path = cfg / "10.0" / "kicad_common.json"
    path.parent.mkdir()
    path.write_bytes(b'{"a": "\xff\xfe"}')
    issues = _sync(repo, cfg, backups)
    (bad,) = issues
    assert bad.code == "fs.bad_encoding"
    _assert_untouched(path, b'{"a": "\xff\xfe"}', backups)


def test_verification_failure_aborts_before_backup_and_write(repo, cfg, backups, monkeypatch):
    path = _write_config(cfg, "10.0", _null_vars_config())
    before = path.read_bytes()
    monkeypatch.setattr(library_scanner, "_only_vars_changed", lambda *a: False)
    issues = _sync(repo, cfg, backups)
    (bad,) = issues
    assert bad.code == "config.verify_failed" and bad.severity is Severity.ERROR
    _assert_untouched(path, before, backups)


def test_running_kicad_warns_but_still_writes(repo, cfg, backups):
    path = _write_config(cfg, "10.0", _null_vars_config())
    issues = _sync(repo, cfg, backups, running=lambda: ["eeschema", "kicad"])
    (warn,) = _by_code(issues, "config.kicad_running")
    assert warn.severity is Severity.WARNING
    assert "eeschema" in warn.text and "kicad" in warn.text
    assert _by_code(issues, "config.written")
    assert json.loads(path.read_text(encoding="utf-8"))["environment"]["vars"] == _desired(repo)


def test_read_only_config_returns_issue_and_keeps_bytes(repo, cfg, backups):
    path = _write_config(cfg, "10.0", _null_vars_config())
    before = path.read_bytes()
    os.chmod(path, stat.S_IREAD)
    try:
        issues = _sync(repo, cfg, backups)
    finally:
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
    assert "fs.read_only" in _codes(issues)
    assert not _by_code(issues, "config.written")
    assert path.read_bytes() == before


def test_locked_config_returns_issue_and_keeps_bytes(repo, cfg, backups, monkeypatch):
    path = _write_config(cfg, "10.0", _null_vars_config())
    before = path.read_bytes()

    def denied(src, dst):
        raise PermissionError(13, "Access is denied")

    real_write = fsutil.atomic_write_text
    monkeypatch.setattr(fsutil.os, "replace", denied)
    monkeypatch.setattr(
        fsutil, "atomic_write_text",
        lambda p, t, **kw: real_write(p, t, retry_delays=(0.0,), sleep=lambda s: None, **kw),
    )
    issues = _sync(repo, cfg, backups)
    assert "fs.locked" in _codes(issues)
    assert not _by_code(issues, "config.written")
    assert path.read_bytes() == before


def test_unusable_backup_root_blocks_the_write(repo, cfg, tmp_path):
    path = _write_config(cfg, "10.0", _null_vars_config())
    before = path.read_bytes()
    not_a_folder = tmp_path / "backups_is_a_file"
    not_a_folder.write_text("x")
    issues = _sync(repo, cfg, not_a_folder)
    assert "fs.backup_failed" in _codes(issues)
    assert not _by_code(issues, "config.written")
    assert path.read_bytes() == before


def _seed_backups(backups, numbers, version="10.0"):
    folder = _backup_dir(backups, version)
    folder.mkdir(parents=True)
    for n in numbers:
        (folder / f"kicad_common.json_backup_{n}").write_text(str(n))
    return folder


def test_only_newest_ten_backups_are_kept_by_number(repo, cfg, backups):
    _write_config(cfg, "10.0", _null_vars_config())
    folder = _seed_backups(backups, range(1, 13))
    os.chmod(folder / "kicad_common.json_backup_2", stat.S_IREAD)

    issues = _sync(repo, cfg, backups)

    kept = sorted(int(p.name.rsplit("_", 1)[1]) for p in folder.iterdir())
    assert kept == list(range(4, 14))
    assert not _by_code(issues, "config.prune_failed")


def test_unremovable_old_backup_warns_without_failing_the_sync(repo, cfg, backups, monkeypatch):
    _write_config(cfg, "10.0", _null_vars_config())
    _seed_backups(backups, range(1, 13))
    real_unlink = Path.unlink

    def picky(self, *args, **kwargs):
        if self.name == "kicad_common.json_backup_1":
            raise PermissionError(13, "Access is denied")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", picky)
    issues = _sync(repo, cfg, backups)
    assert _by_code(issues, "config.written")
    (warn,) = _by_code(issues, "config.prune_failed")
    assert warn.severity is Severity.WARNING
    assert "kicad_common.json_backup_1" in warn.text
