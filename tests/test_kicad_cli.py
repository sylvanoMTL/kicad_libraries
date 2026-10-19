"""kicad_cli: locating and running kicad-cli with a scripted fake runner (plan 04-03).

The default suite never starts a process. Tests marked ``kicad_cli`` use the real binary
and skip when it is absent.
"""

import subprocess

import pytest
from fakecli import FakeCli

from kicad_lib_manager.importer import kicad_cli
from kicad_lib_manager.importer.kicad_cli import (
    DEFAULT_TIMEOUT,
    CliRun,
    locate_kicad_cli,
    run_cli,
    stock_symbols_dir,
)
from kicad_lib_manager.models import Issue, Severity


def _install(tmp_path, exe_name):
    """Build <tmp>/9.0/{bin/<exe_name>, share/kicad/footprints, share/kicad/symbols}."""
    root = tmp_path / "9.0"
    (root / "bin").mkdir(parents=True)
    exe = root / "bin" / exe_name
    exe.write_bytes(b"")
    fp_dir = root / "share" / "kicad" / "footprints"
    fp_dir.mkdir(parents=True)
    return exe, fp_dir


def _no_which(name):
    return None


# -- locate_kicad_cli ----------------------------------------------------------


def test_locate_prefers_explicit_file(tmp_path):
    exe, fp_dir = _install(tmp_path, "kicad-cli.exe")
    mine = tmp_path / "mine.exe"
    mine.write_bytes(b"")
    found = locate_kicad_cli(mine, fp_dir, platform="win32", which=lambda n: str(exe))
    assert found == mine


def test_locate_missing_explicit_with_nothing_else_is_none(tmp_path):
    assert locate_kicad_cli(tmp_path / "nope.exe", which=_no_which) is None


def test_locate_missing_explicit_falls_through_to_install(tmp_path):
    exe, fp_dir = _install(tmp_path, "kicad-cli.exe")
    found = locate_kicad_cli(tmp_path / "nope.exe", fp_dir, platform="win32", which=_no_which)
    assert found == exe


def test_locate_windows_install_next_to_footprints(tmp_path):
    exe, fp_dir = _install(tmp_path, "kicad-cli.exe")
    assert locate_kicad_cli(kicad_fp_dir=fp_dir, platform="win32", which=_no_which) == exe


def test_locate_linux_install_has_no_exe_suffix(tmp_path):
    exe, fp_dir = _install(tmp_path, "kicad-cli")
    assert locate_kicad_cli(kicad_fp_dir=fp_dir, platform="linux", which=_no_which) == exe
    # The windows branch looks for the .exe name, which is absent here
    assert locate_kicad_cli(kicad_fp_dir=fp_dir, platform="win32", which=_no_which) is None


def test_locate_falls_back_to_path_lookup(tmp_path):
    seen = []

    def which(name):
        seen.append(name)
        return str(tmp_path / "somewhere" / "kicad-cli")

    found = locate_kicad_cli(platform="linux", which=which)
    assert found == tmp_path / "somewhere" / "kicad-cli"
    assert seen == ["kicad-cli"]


def test_locate_short_footprint_path_does_not_raise(tmp_path):
    assert locate_kicad_cli(kicad_fp_dir=tmp_path.parents[-1], which=_no_which) is None


def test_locate_nothing_found_is_none():
    assert locate_kicad_cli(which=_no_which) is None


# -- stock_symbols_dir ---------------------------------------------------------


def test_stock_symbols_dir_is_sibling_of_footprints(tmp_path):
    _, fp_dir = _install(tmp_path, "kicad-cli.exe")
    symbols = fp_dir.parent / "symbols"
    symbols.mkdir()
    assert stock_symbols_dir(fp_dir) == symbols


def test_stock_symbols_dir_none_when_folder_missing(tmp_path):
    _, fp_dir = _install(tmp_path, "kicad-cli.exe")
    assert stock_symbols_dir(fp_dir) is None
    assert stock_symbols_dir(None) is None


# -- run_cli -------------------------------------------------------------------


def test_run_cli_passes_list_argv_and_safe_flags(tmp_path):
    exe = tmp_path / "kicad-cli.exe"
    fake = FakeCli({"sym upgrade": "not_updated"})
    result = run_cli(exe, ["sym", "upgrade", str(tmp_path / "in.kicad_sym")], runner=fake)
    assert isinstance(result, CliRun)
    argv = fake.calls[0]
    assert isinstance(argv, list)
    assert argv[0] == str(exe)
    assert argv[1:3] == ["sym", "upgrade"]
    kwargs = fake.kwargs[0]
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert kwargs["errors"] == "replace"
    assert kwargs["timeout"] == DEFAULT_TIMEOUT
    assert kwargs["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0)
    assert "shell" not in kwargs


def test_run_cli_returns_output_for_any_exit_code(tmp_path):
    exe = tmp_path / "kicad-cli"
    for mode, code in (("not_updated", 0), ("reject", 2), ("missing", 3), ("conflict", 4)):
        fake = FakeCli({"sym upgrade": mode})
        result = run_cli(exe, ["sym", "upgrade", "x.kicad_sym"], runner=fake)
        assert isinstance(result, CliRun)
        assert result.returncode == code


def test_run_cli_carries_stdout_and_stderr(tmp_path):
    fake = FakeCli({"sym upgrade": "reject"})
    result = run_cli(tmp_path / "k", ["sym", "upgrade", "x.kicad_sym"], runner=fake)
    assert result.stderr == "Unable to load library"
    assert result.stdout == ""


def test_run_cli_custom_timeout_is_passed(tmp_path):
    fake = FakeCli({"sym upgrade": "not_updated"})
    run_cli(tmp_path / "k", ["sym", "upgrade", "x.kicad_sym"], runner=fake, timeout=7.5)
    assert fake.kwargs[0]["timeout"] == 7.5


def test_run_cli_timeout_becomes_error_issue(tmp_path):
    fake = FakeCli({"sym upgrade": "timeout"})
    result = run_cli(tmp_path / "k", ["sym", "upgrade", "x.kicad_sym"], runner=fake, timeout=12)
    assert isinstance(result, Issue)
    assert result.severity is Severity.ERROR
    assert result.code == "install.cli_failed"
    assert "timed out after 12 s" in result.text


def test_run_cli_oserror_becomes_error_issue(tmp_path):
    fake = FakeCli({"sym upgrade": "oserror"})
    result = run_cli(tmp_path / "k", ["sym", "upgrade", "x.kicad_sym"], runner=fake)
    assert isinstance(result, Issue)
    assert result.code == "install.cli_failed"
    assert "No such file" in result.text


def test_run_cli_defaults_to_subprocess_run(tmp_path, monkeypatch):
    seen = {}

    def fake_run(argv, **kwargs):
        seen["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, "out", "")

    monkeypatch.setattr(kicad_cli.subprocess, "run", fake_run)
    result = run_cli(tmp_path / "k", ["fp", "upgrade", "d"])
    assert result == CliRun(0, "out", "")
    assert seen["argv"][1:] == ["fp", "upgrade", "d"]


# -- FakeCli itself ------------------------------------------------------------


def test_fake_upgrade_copies_input_with_new_version(tmp_path):
    src = tmp_path / "in.kicad_sym"
    src.write_bytes(b"(kicad_symbol_lib (version 20211014) (x (version 5)))")
    out = tmp_path / "out.kicad_sym"
    fake = FakeCli(output_version=20241209)
    result = fake(["k", "sym", "upgrade", "--force", "-o", str(out), str(src)], timeout=1)
    assert result.returncode == 0
    assert out.read_bytes() == b"(kicad_symbol_lib (version 20241209) (x (version 5)))"
    assert fake.inputs == [{"in.kicad_sym": src.read_bytes()}]


def test_fake_upgrade_of_folder_creates_folder(tmp_path):
    stage = tmp_path / "stage.pretty"
    stage.mkdir()
    (stage / "A.kicad_mod").write_bytes(b"(footprint \"A\" (version 1))")
    out = tmp_path / "out.pretty"
    fake = FakeCli(output_version=20241229)
    fake(["k", "fp", "upgrade", "--force", "-o", str(out), str(stage)], timeout=1)
    assert (out / "A.kicad_mod").read_bytes() == b"(footprint \"A\" (version 20241229))"
    assert fake.inputs[0].keys() == {"A.kicad_mod"}


def test_fake_mode_list_is_consumed_in_order(tmp_path):
    fake = FakeCli({"sym upgrade": ["reject", "not_updated"]})
    src = tmp_path / "in.kicad_sym"
    src.write_bytes(b"x")
    argv = ["k", "sym", "upgrade", str(src)]
    codes = [fake(argv, timeout=1).returncode for _ in range(3)]
    assert codes == [2, 0, 0]
    assert len(fake.calls) == 3
