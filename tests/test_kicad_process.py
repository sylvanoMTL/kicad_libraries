"""kicad_running() with subprocess.run replaced; no real process list is read."""

import subprocess
from types import SimpleNamespace

import pytest

from kicad_lib_manager import kicad_process
from kicad_lib_manager.kicad_process import kicad_running


def _fake_run(stdout, calls=None):
    def run(args, **kwargs):
        if calls is not None:
            calls.append((args, kwargs))
        return SimpleNamespace(stdout=stdout, returncode=0)

    return run


_CSV = (
    '"System","4","Services","0","144 K"\r\n'
    '"kicad.exe","1234","Console","1","200,000 K"\r\n'
    '"eeschema.exe","2345","Console","1","100,000 K"\r\n'
    '"notepad.exe","3456","Console","1","10,000 K"\r\n'
)


def test_windows_rows_give_sorted_kicad_names(monkeypatch):
    monkeypatch.setattr(kicad_process.subprocess, "run", _fake_run(_CSV))
    assert kicad_running(platform="win32") == ["eeschema", "kicad"]


def test_kicad_cli_alone_is_not_an_editor(monkeypatch):
    out = '"kicad-cli.exe","99","Console","1","1 K"\r\n'
    monkeypatch.setattr(kicad_process.subprocess, "run", _fake_run(out))
    assert kicad_running(platform="win32") == []


def test_no_tasks_info_line_gives_empty_list(monkeypatch):
    out = "INFO: No tasks are running which match the specified criteria.\r\n"
    monkeypatch.setattr(kicad_process.subprocess, "run", _fake_run(out))
    assert kicad_running(platform="win32") == []


@pytest.mark.parametrize(
    "error",
    [OSError("no tasklist"), subprocess.TimeoutExpired("tasklist", 5)],
)
def test_failure_to_list_processes_is_silent(monkeypatch, error):
    def boom(args, **kwargs):
        raise error

    monkeypatch.setattr(kicad_process.subprocess, "run", boom)
    assert kicad_running(platform="win32") == []
    assert kicad_running(platform="linux") == []


def test_windows_call_is_absolute_list_without_shell(monkeypatch):
    calls = []
    monkeypatch.setenv("SystemRoot", r"C:\Windows")
    monkeypatch.setattr(kicad_process.subprocess, "run", _fake_run(_CSV, calls))
    kicad_running(platform="win32")
    (args, kwargs), = calls
    assert isinstance(args, list)
    exe = args[0].replace("\\", "/")
    assert exe.endswith("System32/tasklist.exe")
    assert exe.startswith("C:/Windows")
    assert args[1:] == ["/NH", "/FO", "CSV"]
    assert kwargs.get("timeout")
    assert not kwargs.get("shell")


def test_posix_parses_ps_output(monkeypatch):
    calls = []
    out = "/usr/bin/pcbnew\nbash\nkicad-cli\n"
    monkeypatch.setattr(kicad_process.subprocess, "run", _fake_run(out, calls))
    assert kicad_running(platform="linux") == ["pcbnew"]
    (args, kwargs), = calls
    assert args == ["ps", "-A", "-o", "comm="]
    assert not kwargs.get("shell")
