"""kicad_cli: locating and running kicad-cli with a scripted fake runner (plan 04-03).

The default suite never starts a process. Tests marked ``kicad_cli`` use the real binary
and skip when it is absent.
"""

import subprocess
import tempfile
import zipfile
from pathlib import Path

import pytest
from fakecli import FakeCli
from zipfixtures import REPO_ROOT, UL_FOOTPRINT_MEMBER, UL_SYMBOL_MEMBER, UL_ZIP

from kicad_lib_manager import library_scanner
from kicad_lib_manager.importer import kicad_cli
from kicad_lib_manager.importer.kicad_cli import (
    DEFAULT_TIMEOUT,
    CliRun,
    SymbolUpgrade,
    clear_cache,
    load_gate,
    locate_kicad_cli,
    run_cli,
    stock_symbols_dir,
    upgrade_symbol_text,
)
from kicad_lib_manager.models import Issue, Severity

EXE = Path("kicad-cli-for-tests.exe")
SYM = '(kicad_symbol_lib (version 20211014) (generator test)\r\n  (symbol "A"))\r\n'
SYM_UP = SYM.replace("20211014", "20241209")
FP_A = b'(footprint "FP_A" (version 20211014))\n'
FP_B = b'(footprint "FP_B" (version 20211014))\n'


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_cache()
    yield
    clear_cache()


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


def test_fake_answers_exit_4_when_the_output_exists(tmp_path):
    src = tmp_path / "in.kicad_sym"
    src.write_bytes(b"(kicad_symbol_lib (version 1))")
    out = tmp_path / "out.kicad_sym"
    out.write_bytes(b"old")
    result = FakeCli()(["k", "sym", "upgrade", "-o", str(out), str(src)], timeout=1)
    assert result.returncode == 4
    assert out.read_bytes() == b"old"


# -- upgrade_symbol_text -------------------------------------------------------


def _record_temp_folders(monkeypatch):
    made = []
    real = tempfile.mkdtemp

    def recording(*args, **kwargs):
        path = real(*args, **kwargs)
        made.append(Path(path))
        return path

    monkeypatch.setattr(kicad_cli.tempfile, "mkdtemp", recording)
    return made


def test_upgrade_returns_output_text_and_version():
    fake = FakeCli()
    result = upgrade_symbol_text(EXE, SYM, runner=fake)
    assert result == SymbolUpgrade(text=SYM_UP, version=20241209, changed=True)


def test_upgrade_argv_has_fresh_output_and_kicad_sym_input():
    fake = FakeCli()
    result = upgrade_symbol_text(EXE, SYM, runner=fake)
    # FakeCli answers exit 4 when -o already exists, so a SymbolUpgrade proves it was fresh
    assert isinstance(result, SymbolUpgrade)
    argv = fake.calls[0]
    assert argv[1:5] == ["sym", "upgrade", "--force", "-o"]
    out, inp = Path(argv[5]), Path(argv[6])
    assert inp.suffix == ".kicad_sym"
    assert out.is_absolute() and inp.is_absolute()
    assert fake.inputs[0] == {inp.name: SYM.encode("utf-8")}
    assert REPO_ROOT not in out.resolve().parents


def test_upgrade_is_memoised_per_input_and_runner():
    fake = FakeCli()
    first = upgrade_symbol_text(EXE, SYM, runner=fake)
    second = upgrade_symbol_text(EXE, SYM, runner=fake)
    assert second == first
    assert len(fake.calls) == 1
    # A different input misses the cache
    upgrade_symbol_text(EXE, SYM + " ", runner=fake)
    assert len(fake.calls) == 2


def test_clear_cache_forces_a_new_run():
    fake = FakeCli()
    upgrade_symbol_text(EXE, SYM, runner=fake)
    clear_cache()
    upgrade_symbol_text(EXE, SYM, runner=fake)
    assert len(fake.calls) == 2


def test_different_runner_object_misses_the_cache():
    one, other = FakeCli(), FakeCli()
    upgrade_symbol_text(EXE, SYM, runner=one)
    upgrade_symbol_text(EXE, SYM, runner=other)
    assert len(one.calls) == 1
    assert len(other.calls) == 1


def test_cache_is_capped():
    fake = FakeCli()
    for n in range(40):
        upgrade_symbol_text(EXE, SYM + " " * n, runner=fake)
    assert len(fake.calls) == 40
    # The newest entry is still cached, the oldest was evicted
    upgrade_symbol_text(EXE, SYM + " " * 39, runner=fake)
    assert len(fake.calls) == 40
    upgrade_symbol_text(EXE, SYM, runner=fake)
    assert len(fake.calls) == 41


def test_upgrade_exit_zero_without_output_means_unchanged():
    fake = FakeCli({"sym upgrade": "not_updated"})
    result = upgrade_symbol_text(EXE, SYM, runner=fake)
    assert result == SymbolUpgrade(text=SYM, version=20211014, changed=False)


def test_upgrade_rejection_is_an_error_naming_the_symbol():
    fake = FakeCli({"sym upgrade": "reject"})
    result = upgrade_symbol_text(EXE, SYM, name="CSD85301Q2", runner=fake)
    assert isinstance(result, Issue)
    assert result.severity is Severity.ERROR
    assert result.code == "install.cli_gate_failed"
    assert "CSD85301Q2" in result.text
    assert "Unable to load library" in result.text


def test_upgrade_failure_is_never_cached():
    fake = FakeCli({"sym upgrade": ["reject", "upgrade"]})
    assert isinstance(upgrade_symbol_text(EXE, SYM, runner=fake), Issue)
    assert isinstance(upgrade_symbol_text(EXE, SYM, runner=fake), SymbolUpgrade)
    assert len(fake.calls) == 2


def test_upgrade_unable_to_load_with_exit_zero_is_still_a_failure():
    def runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 0, "Unable to load library", "")

    result = upgrade_symbol_text(EXE, SYM, runner=runner)
    assert isinstance(result, Issue)
    assert result.code == "install.cli_gate_failed"


def test_upgrade_uses_stdout_when_stderr_is_empty():
    def runner(argv, **kwargs):
        return subprocess.CompletedProcess(argv, 5, "odd message", "")

    result = upgrade_symbol_text(EXE, SYM, runner=runner)
    assert isinstance(result, Issue)
    assert "odd message" in result.text
    assert "5" in result.text


def test_upgrade_timeout_passes_through_as_cli_failed():
    result = upgrade_symbol_text(EXE, SYM, runner=FakeCli({"sym upgrade": "timeout"}))
    assert isinstance(result, Issue)
    assert result.code == "install.cli_failed"


def test_upgrade_removes_its_temp_folder(monkeypatch):
    made = _record_temp_folders(monkeypatch)
    upgrade_symbol_text(EXE, SYM, runner=FakeCli())
    upgrade_symbol_text(EXE, SYM + "x", runner=FakeCli({"sym upgrade": "reject"}))
    upgrade_symbol_text(EXE, SYM + "y", runner=FakeCli({"sym upgrade": "timeout"}))
    assert len(made) == 3
    assert not any(p.exists() for p in made)


# -- load_gate -----------------------------------------------------------------


def test_gate_checks_staging_copies_outside_the_repo():
    fake = FakeCli()
    issues = load_gate(
        EXE,
        library="IC_Test_TI",
        symbol_lib=SYM.encode("utf-8"),
        footprints=[("FP_A", FP_A), ("FP_B", FP_B)],
        runner=fake,
    )
    assert issues == []
    sym_call, fp_call = fake.calls
    assert sym_call[1:5] == ["sym", "upgrade", "--force", "-o"]
    assert Path(sym_call[-1]).name == "IC_Test_TI.kicad_sym"
    assert Path(sym_call[5]).parent == Path(sym_call[-1]).parent
    assert fake.inputs[0] == {"IC_Test_TI.kicad_sym": SYM.encode("utf-8")}
    assert fp_call[1:5] == ["fp", "upgrade", "--force", "-o"]
    assert Path(fp_call[-1]).name == "stage.pretty"
    assert fake.inputs[1] == {"FP_A.kicad_mod": FP_A, "FP_B.kicad_mod": FP_B}
    for call in fake.calls:
        paths = [Path(a) for a in call[1:] if Path(a).is_absolute()]
        assert paths
        assert all(REPO_ROOT not in p.resolve().parents for p in paths)


def test_gate_skips_footprint_step_without_footprints():
    fake = FakeCli()
    assert load_gate(EXE, library="L", symbol_lib=SYM.encode(), footprints=(), runner=fake) == []
    assert [c[1] for c in fake.calls] == ["sym"]


def test_gate_skips_symbol_step_without_symbol_library():
    fake = FakeCli()
    assert load_gate(EXE, library="L", symbol_lib=None, footprints=[("FP_A", FP_A)], runner=fake) == []
    assert [c[1] for c in fake.calls] == ["fp"]


def test_gate_with_nothing_to_check_runs_nothing():
    fake = FakeCli()
    assert load_gate(EXE, library="L", symbol_lib=None, footprints=(), runner=fake) == []
    assert fake.calls == []


def test_gate_symbol_failure_names_library_and_quotes_cli():
    fake = FakeCli({"sym upgrade": "reject"})
    issues = load_gate(EXE, library="IC_Test_TI", symbol_lib=SYM.encode(), footprints=(), runner=fake)
    assert len(issues) == 1
    assert issues[0].severity is Severity.ERROR
    assert issues[0].code == "install.cli_gate_failed"
    assert "the merged symbol library IC_Test_TI.kicad_sym" in issues[0].text
    assert "Unable to load library" in issues[0].text


def test_gate_footprint_failure_names_the_incoming_footprints():
    fake = FakeCli({"fp upgrade": "reject"})
    issues = load_gate(
        EXE,
        library="L",
        symbol_lib=None,
        footprints=[("FP_A", FP_A), ("FP_B", FP_B)],
        runner=fake,
    )
    assert len(issues) == 1
    assert issues[0].code == "install.cli_gate_failed"
    assert "the incoming footprint(s) FP_A, FP_B" in issues[0].text
    assert "Unable to load library" in issues[0].text


def test_gate_reports_both_failures():
    fake = FakeCli({"sym upgrade": "reject", "fp upgrade": "reject"})
    issues = load_gate(
        EXE, library="L", symbol_lib=SYM.encode(), footprints=[("FP_A", FP_A)], runner=fake
    )
    assert len(issues) == 2
    assert all(i.code == "install.cli_gate_failed" for i in issues)


def test_gate_nonzero_exit_without_load_message_still_fails():
    fake = FakeCli({"sym upgrade": "missing"})
    issues = load_gate(EXE, library="L", symbol_lib=SYM.encode(), footprints=(), runner=fake)
    assert [i.code for i in issues] == ["install.cli_gate_failed"]
    assert "does not exist" in issues[0].text


def test_gate_blames_the_merge_when_the_original_loads():
    fake = FakeCli({"sym upgrade": ["reject", "upgrade"]})
    issues = load_gate(
        EXE,
        library="L",
        symbol_lib=SYM.encode(),
        footprints=(),
        original_symbol_lib=b"(kicad_symbol_lib (version 20241209))",
        runner=fake,
    )
    assert len(issues) == 1
    assert "the target library loads on its own, so the merged part is the cause" in issues[0].text
    assert len(fake.calls) == 2


def test_gate_blames_the_target_when_the_original_also_fails():
    fake = FakeCli({"sym upgrade": ["reject", "reject"]})
    issues = load_gate(
        EXE,
        library="L",
        symbol_lib=SYM.encode(),
        footprints=(),
        original_symbol_lib=b"(kicad_symbol_lib (version 20241209))",
        runner=fake,
    )
    assert len(issues) == 1
    assert "the target library already fails to load in KiCad before the merge" in issues[0].text
    assert fake.inputs[1] == {"L.kicad_sym": b"(kicad_symbol_lib (version 20241209))"}


def test_gate_without_original_does_not_re_run():
    fake = FakeCli({"sym upgrade": "reject"})
    issues = load_gate(EXE, library="L", symbol_lib=SYM.encode(), footprints=(), runner=fake)
    assert len(fake.calls) == 1
    assert "target library" not in issues[0].text


def test_gate_passing_symbol_never_runs_the_blame_check():
    fake = FakeCli()
    load_gate(
        EXE,
        library="L",
        symbol_lib=SYM.encode(),
        footprints=(),
        original_symbol_lib=b"x",
        runner=fake,
    )
    assert len(fake.calls) == 1


def test_gate_timeout_comes_back_as_cli_failed():
    fake = FakeCli({"sym upgrade": "timeout"})
    issues = load_gate(EXE, library="L", symbol_lib=SYM.encode(), footprints=(), runner=fake)
    assert [i.code for i in issues] == ["install.cli_failed"]


@pytest.mark.parametrize(
    ("library", "footprints"),
    [
        ("..", [("FP_A", FP_A)]),
        ("a/b", [("FP_A", FP_A)]),
        ("L", [("..\\evil", FP_A)]),
        ("L", [("sub/evil", FP_A)]),
        ("L", [("", FP_A)]),
    ],
)
def test_gate_refuses_names_that_could_leave_the_staging_folder(library, footprints):
    fake = FakeCli()
    issues = load_gate(
        EXE, library=library, symbol_lib=SYM.encode(), footprints=footprints, runner=fake
    )
    assert len(issues) == 1
    assert issues[0].severity is Severity.ERROR
    assert issues[0].code == "install.cli_gate_failed"
    assert fake.calls == []


def test_gate_removes_its_temp_folder(monkeypatch):
    made = _record_temp_folders(monkeypatch)
    load_gate(
        EXE, library="L", symbol_lib=SYM.encode(), footprints=[("FP_A", FP_A)], runner=FakeCli()
    )
    load_gate(
        EXE,
        library="L",
        symbol_lib=SYM.encode(),
        footprints=[("FP_A", FP_A)],
        original_symbol_lib=b"x",
        runner=FakeCli({"sym upgrade": "reject", "fp upgrade": "reject"}),
    )
    load_gate(
        EXE,
        library="L",
        symbol_lib=SYM.encode(),
        footprints=(),
        runner=FakeCli({"sym upgrade": "timeout"}),
    )
    assert len(made) == 3
    assert not any(p.exists() for p in made)


# -- real kicad-cli (marked, skipped when the binary is absent) -----------------


@pytest.fixture(scope="module")
def real_exe():
    exe = locate_kicad_cli(kicad_fp_dir=library_scanner.find_kicad_footprint_dir())
    if exe is None:
        pytest.skip("kicad-cli not found")
    return exe


def _ul_member(member: str) -> bytes:
    with zipfile.ZipFile(UL_ZIP) as zf:
        return zf.read(member)


@pytest.mark.kicad_cli
def test_real_cli_upgrades_ul_symbol_deterministically(real_exe):
    text = _ul_member(UL_SYMBOL_MEMBER).decode("utf-8")
    first = upgrade_symbol_text(real_exe, text, name="CSD85301Q2")
    assert isinstance(first, SymbolUpgrade), first
    assert first.version == 20241209
    assert first.changed is True
    assert "(version 20241209)" in first.text
    clear_cache()
    second = upgrade_symbol_text(real_exe, text, name="CSD85301Q2")
    assert second == first


@pytest.mark.kicad_cli
def test_real_cli_gate_accepts_ul_symbol_and_footprint(real_exe):
    issues = load_gate(
        real_exe,
        library="IC_Test_TI",
        symbol_lib=_ul_member(UL_SYMBOL_MEMBER),
        footprints=[("DQK0006B", _ul_member(UL_FOOTPRINT_MEMBER))],
    )
    assert issues == []


@pytest.mark.kicad_cli
def test_real_cli_gate_rejects_sub_symbols_left_with_the_old_name(real_exe):
    text = _ul_member(UL_SYMBOL_MEMBER).decode("utf-8")
    assert '(symbol "CSD85301Q2_1_1"' in text
    half = text.replace('(symbol "CSD85301Q2"', '(symbol "RENAMED_PART"', 1)
    issues = load_gate(
        real_exe, library="IC_Test_TI", symbol_lib=half.encode("utf-8"), footprints=()
    )
    assert [i.code for i in issues] == ["install.cli_gate_failed"]
    assert "Unable to load library" in issues[0].text
