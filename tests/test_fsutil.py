import os
import stat
import sys
import threading

import pytest

from kicad_lib_manager import fsutil
from kicad_lib_manager.fsutil import atomic_write_bytes, encode_source
from kicad_lib_manager.models import Issue, Severity


def _no_sleep(_seconds):
    pass


class _SleepRecorder:
    def __init__(self):
        self.calls = []

    def __call__(self, seconds):
        self.calls.append(seconds)


@pytest.fixture
def target(tmp_path):
    path = tmp_path / "sym-lib-table"
    path.write_bytes(b"original\r\n")
    return path


def _only(tmp_path, *names):
    assert sorted(os.listdir(tmp_path)) == sorted(names)


# -- Task 1: atomic write failure matrix (D-05) --------------------------------


def test_success_replaces_existing_target_and_leaves_no_temp(tmp_path, target):
    result = atomic_write_bytes(target, b"new content", sleep=_no_sleep)
    assert result is None
    assert target.read_bytes() == b"new content"
    _only(tmp_path, target.name)


def test_success_creates_missing_target(tmp_path):
    path = tmp_path / "fp-lib-table"
    assert atomic_write_bytes(path, b"fresh", sleep=_no_sleep) is None
    assert path.read_bytes() == b"fresh"
    _only(tmp_path, path.name)


def test_positional_call_stays_compatible(tmp_path, target):
    # Plan 01 callers pass only (path, data)
    assert atomic_write_bytes(target, b"x") is None
    assert target.read_bytes() == b"x"


def test_read_only_target_returns_issue_without_retry(tmp_path, target):
    recorder = _SleepRecorder()
    os.chmod(target, stat.S_IREAD)
    try:
        result = atomic_write_bytes(target, b"new", sleep=recorder)
        assert isinstance(result, Issue)
        assert result.severity is Severity.ERROR
        assert result.code == "fs.read_only"
        assert result.text.startswith(f"Could not write {target.name}: file is read-only")
        assert recorder.calls == []
        assert target.read_bytes() == b"original\r\n"
        _only(tmp_path, target.name)
    finally:
        os.chmod(target, stat.S_IREAD | stat.S_IWRITE)


@pytest.mark.skipif(sys.platform != "win32", reason="held-open handles block os.replace only on win32")
def test_held_open_target_returns_locked_issue_after_retries(tmp_path, target):
    recorder = _SleepRecorder()
    delays = (0.01, 0.02, 0.03)
    with open(target, "rb"):
        result = atomic_write_bytes(target, b"new", retry_delays=delays, sleep=recorder)
    assert isinstance(result, Issue)
    assert result.severity is Severity.ERROR
    assert result.code == "fs.locked"
    assert result.text == f"Could not write {target.name}: file is in use"
    assert recorder.calls == list(delays)
    assert target.read_bytes() == b"original\r\n"
    _only(tmp_path, target.name)


def test_permission_error_on_replace_gives_locked_after_all_delays(tmp_path, target, monkeypatch):
    recorder = _SleepRecorder()
    delays = (0.01, 0.02, 0.03, 0.04)

    def always_denied(src, dst):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(fsutil.os, "replace", always_denied)
    result = atomic_write_bytes(target, b"new", retry_delays=delays, sleep=recorder)
    assert isinstance(result, Issue)
    assert result.code == "fs.locked"
    assert result.text.startswith("Could not write")
    assert len(recorder.calls) == len(delays)
    assert target.read_bytes() == b"original\r\n"
    _only(tmp_path, target.name)


def test_lock_released_mid_retry_window_succeeds(tmp_path, target, monkeypatch):
    real_replace = os.replace
    attempts = []

    def flaky(src, dst):
        attempts.append(1)
        if len(attempts) <= 2:
            raise PermissionError(13, "Access is denied")
        return real_replace(src, dst)

    monkeypatch.setattr(fsutil.os, "replace", flaky)
    recorder = _SleepRecorder()
    result = atomic_write_bytes(target, b"new", retry_delays=(0.01, 0.02, 0.03), sleep=recorder)
    assert result is None
    assert target.read_bytes() == b"new"
    assert len(recorder.calls) == 2
    _only(tmp_path, target.name)


def test_default_retry_window_is_about_one_second():
    assert 0.9 <= sum(fsutil._RETRY_DELAYS) <= 1.1


def test_fsync_failure_returns_write_failed(tmp_path, target, monkeypatch):
    def broken_fsync(fd):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(fsutil.os, "fsync", broken_fsync)
    result = atomic_write_bytes(target, b"new", sleep=_no_sleep)
    assert isinstance(result, Issue)
    assert result.severity is Severity.ERROR
    assert result.code == "fs.write_failed"
    assert result.text.startswith("Could not write")
    assert target.read_bytes() == b"original\r\n"
    _only(tmp_path, target.name)


def test_missing_parent_directory_returns_issue_and_creates_nothing(tmp_path):
    path = tmp_path / "missing" / "sym-lib-table"
    result = atomic_write_bytes(path, b"x", sleep=_no_sleep)
    assert isinstance(result, Issue)
    assert result.severity is Severity.ERROR
    assert result.code == "fs.write_failed"
    assert result.text.startswith("Could not write")
    _only(tmp_path)


def test_concurrent_writers_leave_one_complete_payload(tmp_path, target):
    payload_a = b"A" * 65536
    payload_b = b"B" * 65536
    results = []
    errors = []

    def worker(payload):
        try:
            for _ in range(20):
                results.append(
                    atomic_write_bytes(target, payload, retry_delays=(0.01,) * 5)
                )
        except BaseException as e:  # a raise from the writer is the failure under test
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(p,)) for p in (payload_a, payload_b)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    assert len(results) == 40
    for r in results:
        assert r is None or (isinstance(r, Issue) and r.code == "fs.locked")
    assert target.read_bytes() in (payload_a, payload_b)
    assert not [n for n in os.listdir(tmp_path) if n.endswith(".tmp")]
    _only(tmp_path, target.name)


def test_atomic_write_text_matches_encode_source(tmp_path):
    path = tmp_path / "out.kicad_sym"
    assert fsutil.atomic_write_text(path, "café\r\n", bom=True, sleep=_no_sleep) is None
    assert path.read_bytes() == encode_source("café\r\n", True)
    _only(tmp_path, path.name)


def test_atomic_write_text_unencodable_returns_bad_encoding(tmp_path):
    path = tmp_path / "out.kicad_sym"
    result = fsutil.atomic_write_text(path, "bad \udcff", sleep=_no_sleep)
    assert isinstance(result, Issue)
    assert result.severity is Severity.ERROR
    assert result.code == "fs.bad_encoding"
    assert result.text.startswith(f"Could not write {path.name}")
    _only(tmp_path)


def test_atomic_write_bytes_folder_target_is_not_a_file(tmp_path):
    folder = tmp_path / "d"
    folder.mkdir()
    recorder = _SleepRecorder()
    result = atomic_write_bytes(folder, b"x", sleep=recorder)
    assert isinstance(result, Issue)
    assert result.severity is Severity.ERROR
    assert result.code == "fs.not_a_file"
    assert result.text.startswith(f"Could not write {folder.name}")
    assert recorder.calls == []
    _only(tmp_path, "d")


def test_atomic_write_bytes_read_only_after_retries_is_read_only(tmp_path, target, monkeypatch):
    def deny_and_lock_down(src, dst):
        os.chmod(dst, stat.S_IREAD)
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(fsutil.os, "replace", deny_and_lock_down)
    try:
        result = atomic_write_bytes(target, b"new", retry_delays=(0.0,), sleep=_no_sleep)
        assert isinstance(result, Issue)
        assert result.severity is Severity.ERROR
        assert result.code == "fs.read_only"
        assert result.text == f"Could not write {target.name}: file is read-only"
        assert target.read_bytes() == b"original\r\n"
        _only(tmp_path, target.name)
    finally:
        os.chmod(target, stat.S_IREAD | stat.S_IWRITE)


# -- Task 2: backups, default dir, EOL/BOM/encoding (D-06, D-09, D-10, D-11) ----


def test_backup_file_numbers_like_table_generator(tmp_path):
    src = tmp_path / "sym-lib-table"
    src.write_bytes(b"data")
    first = fsutil.backup_file(src, src.parent)
    assert first == tmp_path / "sym-lib-table_backup_1"
    second = fsutil.backup_file(src, src.parent)
    assert second == tmp_path / "sym-lib-table_backup_2"


def test_backup_file_gaps_continue_after_highest(tmp_path):
    (tmp_path / "fp-lib-table").write_bytes(b"data")
    (tmp_path / "fp-lib-table_backup_1").write_bytes(b"old")
    (tmp_path / "fp-lib-table_backup_3").write_bytes(b"old")
    result = fsutil.backup_file(tmp_path / "fp-lib-table", tmp_path)
    assert result.name == "fp-lib-table_backup_4"


def test_backup_file_number_starts_at_given_n(tmp_path):
    src = tmp_path / "sym-lib-table"
    src.write_bytes(b"data")
    (tmp_path / "sym-lib-table_backup_1").write_bytes(b"old")
    result = fsutil.backup_file(src, tmp_path, number=5)
    assert result == tmp_path / "sym-lib-table_backup_5"
    assert result.read_bytes() == b"data"


def test_backup_file_number_skips_existing(tmp_path):
    src = tmp_path / "sym-lib-table"
    src.write_bytes(b"new")
    (tmp_path / "sym-lib-table_backup_5").write_bytes(b"taken")
    result = fsutil.backup_file(src, tmp_path, number=5)
    assert result == tmp_path / "sym-lib-table_backup_6"
    assert (tmp_path / "sym-lib-table_backup_5").read_bytes() == b"taken"


def test_backup_file_copystat_failure_still_returns_backup(tmp_path, monkeypatch):
    src = tmp_path / "sym-lib-table"
    src.write_bytes(b"payload")

    def broken_copystat(a, b):
        raise OSError(1, "metadata not supported")

    monkeypatch.setattr(fsutil.shutil, "copystat", broken_copystat)
    result = fsutil.backup_file(src, tmp_path / "backups")
    assert not isinstance(result, Issue)
    assert result.read_bytes() == b"payload"


def test_backup_file_of_read_only_source_is_writable(tmp_path):
    src = tmp_path / "sym-lib-table"
    src.write_bytes(b"payload")
    os.chmod(src, stat.S_IREAD)
    try:
        result = fsutil.backup_file(src, tmp_path / "backups")
        assert not isinstance(result, Issue)
        assert os.access(result, os.W_OK)
        assert result.read_bytes() == b"payload"
    finally:
        os.chmod(src, stat.S_IREAD | stat.S_IWRITE)


def test_backup_file_copies_bytes_and_creates_backup_dir(tmp_path):
    src = tmp_path / "sym-lib-table"
    payload = b"\xef\xbb\xbfline\r\nline\n\x00\xff"
    src.write_bytes(payload)
    backup_dir = tmp_path / "nested" / "backups"
    result = fsutil.backup_file(src, backup_dir)
    assert result == backup_dir / "sym-lib-table_backup_1"
    assert result.read_bytes() == payload
    assert src.read_bytes() == payload


def test_backup_file_missing_source_returns_issue(tmp_path):
    result = fsutil.backup_file(tmp_path / "nope", tmp_path / "backups")
    assert isinstance(result, Issue)
    assert result.severity is Severity.ERROR
    assert result.code == "fs.backup_failed"
    assert result.text.startswith("Could not back up")


def test_backup_file_skips_a_name_taken_after_listing(tmp_path, monkeypatch):
    src = tmp_path / "sym-lib-table"
    src.write_bytes(b"new")
    (tmp_path / "sym-lib-table_backup_1").write_bytes(b"taken")
    # A stale listing makes the computed name collide on exclusive create
    monkeypatch.setattr(fsutil.os, "listdir", lambda p: [])
    result = fsutil.backup_file(src, tmp_path)
    assert result == tmp_path / "sym-lib-table_backup_2"
    assert (tmp_path / "sym-lib-table_backup_1").read_bytes() == b"taken"
    assert result.read_bytes() == b"new"


def test_default_backup_dir_win32_uses_localappdata(tmp_path):
    result = fsutil.default_backup_dir(platform="win32", environ={"LOCALAPPDATA": str(tmp_path)})
    assert result == tmp_path / "KiCadExtLibManager" / "backups"
    assert not result.exists()


def test_default_backup_dir_win32_without_localappdata_falls_back_to_home(tmp_path, monkeypatch):
    monkeypatch.setattr(fsutil.Path, "home", lambda: tmp_path)
    result = fsutil.default_backup_dir(platform="win32", environ={})
    assert result == tmp_path / "AppData" / "Local" / "KiCadExtLibManager" / "backups"
    assert not result.exists()


def test_default_backup_dir_darwin(tmp_path, monkeypatch):
    monkeypatch.setattr(fsutil.Path, "home", lambda: tmp_path)
    result = fsutil.default_backup_dir(platform="darwin", environ={})
    assert result == tmp_path / "Library" / "Application Support" / "KiCadExtLibManager" / "backups"
    assert not result.exists()


def test_default_backup_dir_linux_prefers_xdg_data_home(tmp_path, monkeypatch):
    monkeypatch.setattr(fsutil.Path, "home", lambda: tmp_path / "home")
    xdg = tmp_path / "xdg"
    with_xdg = fsutil.default_backup_dir(platform="linux", environ={"XDG_DATA_HOME": str(xdg)})
    assert with_xdg == xdg / "KiCadExtLibManager" / "backups"
    without = fsutil.default_backup_dir(platform="linux", environ={})
    assert without == tmp_path / "home" / ".local" / "share" / "KiCadExtLibManager" / "backups"
    assert not with_xdg.exists() and not without.exists()


def test_default_backup_dir_is_outside_the_repo(repo_root):
    result = fsutil.default_backup_dir()
    assert repo_root not in result.parents


_EOL_BODIES = {
    "lf": b"(a)\n(b)\n",
    "crlf": b"(a)\r\n(b)\r\n",
    "mixed": b"(a)\r\n(b)\r\n(c)\n",
    "lone_cr": b"(a)\r(b)\r",
    "none": b"(a)",
}


@pytest.mark.parametrize("bom", [False, True], ids=["nobom", "bom"])
@pytest.mark.parametrize("body", sorted(_EOL_BODIES))
def test_decode_encode_is_byte_identical(body, bom):
    data = (b"\xef\xbb\xbf" if bom else b"") + _EOL_BODIES[body]
    decoded = fsutil.decode_source(data, "x.kicad_sym")
    assert isinstance(decoded, fsutil.SourceText)
    assert decoded.bom is bom
    assert encode_source(decoded.text, decoded.bom) == data


@pytest.mark.parametrize(
    ("data", "eol", "mixed"),
    [
        (b"a\r\nb\r\nc\n", "\r\n", True),
        (b"a\r\nb\r\n", "\r\n", False),
        (b"a\nb\n", "\n", False),
        (b"a\r\nb\n", "\n", True),
        (b"abc", "\n", False),
        (b"a\rb\n", "\n", True),
    ],
    ids=["crlf_majority", "crlf", "lf", "tie", "no_eol", "bare_cr"],
)
def test_eol_detection(data, eol, mixed):
    decoded = fsutil.decode_source(data, "x")
    assert decoded.eol == eol
    assert decoded.mixed_eol is mixed


def test_mixed_file_yields_exactly_one_warning_naming_the_file():
    decoded = fsutil.decode_source(b"a\r\nb\n", "my_lib.kicad_sym")
    warnings = [i for i in decoded.issues if i.code == "fs.mixed_eol"]
    assert len(warnings) == 1
    assert warnings[0].severity is Severity.WARNING
    assert "my_lib.kicad_sym" in warnings[0].text
    clean = fsutil.decode_source(b"a\r\nb\r\n", "my_lib.kicad_sym")
    assert clean.issues == ()


@pytest.mark.parametrize(
    ("data", "present", "absent", "phrase"),
    [
        (b"a\rb\rc\n", ("LF", "CR"), ("CRLF",), "LF and CR"),
        (b"a\r\nb\n", ("CRLF", "LF"), (), "CRLF and LF"),
        (b"(a)\r(b)\r", ("bare CR",), ("CRLF", "mixed"), "bare CR"),
        (b"a\r\nb\nc\rd", ("CRLF", "LF", "CR"), (), "CRLF, LF and CR"),
    ],
    ids=["lf_and_cr", "crlf_and_lf", "only_cr", "all_three"],
)
def test_mixed_eol_text_names_present_endings(data, present, absent, phrase):
    decoded = fsutil.decode_source(data, "x.kicad_sym")
    (warning,) = [i for i in decoded.issues if i.code == "fs.mixed_eol"]
    assert warning.severity is Severity.WARNING
    assert phrase in warning.text
    for word in present:
        assert word in warning.text
    for word in absent:
        assert word not in warning.text


def test_invalid_utf8_yields_only_an_issue():
    result = fsutil.decode_source(b"\xff\xfe(a)", "bad.kicad_sym")
    assert isinstance(result, Issue)
    assert not isinstance(result, fsutil.SourceText)
    assert result.severity is Severity.ERROR
    assert result.code == "fs.bad_encoding"


def test_read_source_missing_path_gives_read_failed(tmp_path):
    result = fsutil.read_source(tmp_path / "missing.kicad_sym")
    assert isinstance(result, Issue)
    assert result.severity is Severity.ERROR
    assert result.code == "fs.read_failed"


def test_normalize_eol_converts_every_style():
    mixed = "a\r\nb\nc\rd"
    assert fsutil.normalize_eol(mixed, "\r\n") == "a\r\nb\r\nc\r\nd"
    assert fsutil.normalize_eol(mixed, "\n") == "a\nb\nc\nd"
