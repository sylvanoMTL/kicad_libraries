"""Unit tests of the KiCad 10 gate's skip reasons (TEST-02, D-05); no test starts a process."""

import subprocess
from pathlib import Path

from clifixtures import check_kicad_cli

EXE = Path("kicad-cli-for-tests.exe")


def _runner(code: int, stdout: str, stderr: str = ""):
    """A fake subprocess.run answering every call with the given exit code and output."""
    calls: list[list[str]] = []

    def run(argv, **kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, code, stdout, stderr)

    run.calls = calls
    return run


def test_no_kicad_cli_found_says_so_and_names_the_needed_version():
    exe, reason = check_kicad_cli(None)
    assert exe is None
    assert "not found" in reason
    assert "10" in reason


def test_kicad_cli_10_is_accepted_with_an_empty_reason():
    runner = _runner(0, "10.0.7\n")
    assert check_kicad_cli(EXE, runner=runner) == (EXE, "")
    # The probe runs the version subcommand as a plain argv list (no shell)
    assert runner.calls[0][-1] == "version"
    assert runner.calls[0][0] == str(EXE)


def test_kicad_cli_9_is_refused_and_the_found_version_is_named():
    exe, reason = check_kicad_cli(EXE, runner=_runner(0, "9.0.9\n"))
    assert exe is None
    assert "needs kicad-cli 10" in reason
    assert "9.0.9" in reason


def test_kicad_cli_11_is_refused_and_the_found_version_is_named():
    exe, reason = check_kicad_cli(EXE, runner=_runner(0, "11.0.0\n"))
    assert exe is None
    assert "needs kicad-cli 10" in reason
    assert "11.0.0" in reason


def test_unparsable_version_output_is_refused():
    exe, reason = check_kicad_cli(EXE, runner=_runner(0, "garbage"))
    assert exe is None
    assert "needs kicad-cli 10" in reason
    assert "garbage" in reason


def test_blank_version_output_is_refused_as_unreadable():
    exe, reason = check_kicad_cli(EXE, runner=_runner(0, ""))
    assert exe is None
    assert "needs kicad-cli 10" in reason
    assert "an unreadable version" in reason


def test_a_version_command_that_exits_non_zero_is_not_runnable():
    exe, reason = check_kicad_cli(EXE, runner=_runner(1, "10.0.7\n", "boom"))
    assert exe is None
    assert "could not run kicad-cli version" in reason
    assert "exit 1" in reason
    assert "boom" in reason


def test_a_runner_that_cannot_start_the_binary_is_not_runnable():
    def run(argv, **kwargs):
        raise OSError("denied")

    exe, reason = check_kicad_cli(EXE, runner=run)
    assert exe is None
    assert "could not run kicad-cli version" in reason
    assert "denied" in reason


def test_a_version_probe_that_times_out_is_not_runnable():
    def run(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 30)

    exe, reason = check_kicad_cli(EXE, runner=run)
    assert exe is None
    assert "could not run kicad-cli version" in reason
