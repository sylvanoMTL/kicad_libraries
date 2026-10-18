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
    assert fsutil.atomic_write_text(path,"café\r\n", bom=True, sleep=_no_sleep) is None
    assert path.read_bytes() == encode_source("café\r\n", True)
    _only(tmp_path, path.name)
