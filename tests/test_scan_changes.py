"""What the scan marks as new or changed in a git-backed Custom/ (SCAN-02): by content, never by formatting."""

import ast
import shutil
import subprocess
from pathlib import Path

from customfixtures import ATOMIC_LIBRARIES, atomic_lib, atomic_part, write_atomic_custom, write_atomic_files
from gitfixtures import GitRepos, clone_parent_without_submodule, make_superproject, requires_git
from installfixtures import vendor_footprint

from kicad_lib_manager import changes, gitops
from kicad_lib_manager.library_scanner import scan_all
from kicad_lib_manager.models import ChangedFootprint, Issue, ScanResult, Severity, SymbolEntry

pytestmark = requires_git

CHANGE_CODES = {
    "scan.changes_skipped",
    "scan.symbol_new",
    "scan.symbol_changed",
    "scan.footprint_new",
    "scan.footprint_changed",
}
CONNECTOR = "Custom/Symbols/Atomic_Connector.kicad_sym"
LEGACY = "Custom/Symbols/Connector_Legacy.kicad_sym"
FOOTPRINTS = "Custom/Footprints/Atomic_Footprints.pretty"
USB_DESCRIPTION = b"Test part USB4105-GF-A"
SINCE = "since the last Custom commit"


def _populate(custom: Path) -> None:
    write_atomic_files(custom)
    (custom / ".gitignore").write_bytes(b"*.bak\n")


def _repos(tmp_path: Path, **options) -> GitRepos:
    return make_superproject(tmp_path / "git", populate=_populate, **options)


def _scan(repos: GitRepos, tmp_path: Path) -> ScanResult:
    # An explicit folder, so no test reads the machine's KiCad install
    return scan_all(repos.parent, kicad_fp_dir=tmp_path / "no_kicad")


def _change_lines(result: ScanResult) -> list[Issue]:
    return [i for i in result.issues if i.code in CHANGE_CODES]


def _lib(result: ScanResult, nickname: str):
    return next(lib for lib in result.symbol_libs if lib.nickname == nickname)


def _statuses(result: ScanResult, nickname: str) -> dict[str, str | None]:
    return {entry.name: entry.status for entry in _lib(result, nickname).symbols}


def _marked(result: ScanResult, nickname: str) -> dict[str, str]:
    return {name: status for name, status in _statuses(result, nickname).items() if status}


def _footprint_changes(result: ScanResult, nickname: str = "Atomic_Footprints") -> list[ChangedFootprint]:
    return next(lib for lib in result.footprint_libs if lib.nickname == nickname).changed


def _edit(path: Path, old: bytes, new: bytes) -> None:
    data = path.read_bytes()
    assert old in data
    path.write_bytes(data.replace(old, new))


def _edit_usb_description(repos: GitRepos) -> None:
    _edit(repos.parent / CONNECTOR, USB_DESCRIPTION, b"Edited by hand in KiCad")


def _git_says_modified(repos: GitRepos, name: str) -> bool:
    return name in repos.git(repos.custom, "status", "--porcelain")


def _connector_library():
    library = ATOMIC_LIBRARIES[0]
    assert library.name == "Atomic_Connector"
    return library


# -- the symbols of a git-backed Custom ----------------------------------------------------------------


def test_a_clean_tree_marks_nothing(tmp_path):
    repos = _repos(tmp_path)

    result = _scan(repos, tmp_path)

    assert _change_lines(result) == []
    statuses = _statuses(result, "Atomic_Connector")
    assert statuses and set(statuses.values()) == {None}


def test_one_edited_symbol_is_marked_changed_with_one_log_line(tmp_path):
    repos = _repos(tmp_path)
    _edit_usb_description(repos)

    result = _scan(repos, tmp_path)

    assert _marked(result, "Atomic_Connector") == {"USB4105-GF-A": "changed"}
    assert [(i.code, i.severity, i.text) for i in _change_lines(result)] == [
        ("scan.symbol_changed", Severity.INFO, f"Symbol Atomic_Connector / USB4105-GF-A: changed {SINCE}")
    ]


def test_an_appended_symbol_is_new(tmp_path):
    repos = _repos(tmp_path)
    library = _connector_library()
    (repos.parent / CONNECTOR).write_bytes(atomic_lib(library.symbols + (atomic_part("NEW-PART"),)))

    result = _scan(repos, tmp_path)

    assert _marked(result, "Atomic_Connector") == {"NEW-PART": "new"}
    assert [(i.code, i.text) for i in _change_lines(result)] == [
        ("scan.symbol_new", f"Symbol Atomic_Connector / NEW-PART: new {SINCE}")
    ]


def test_a_renamed_symbol_is_new_under_its_new_name(tmp_path):
    repos = _repos(tmp_path)
    # The symbol name and its unit names both carry the old name
    _edit(repos.parent / CONNECTOR, b'(symbol "USB4105-GF-A', b'(symbol "USB4105-RENAMED')

    result = _scan(repos, tmp_path)

    assert _marked(result, "Atomic_Connector") == {"USB4105-RENAMED": "new"}
    assert "USB4105-GF-A" not in _statuses(result, "Atomic_Connector")


def test_every_symbol_of_an_untracked_library_file_is_new_in_file_order(tmp_path):
    repos = _repos(tmp_path)
    new_lib = repos.parent / "Custom" / "Symbols" / "Atomic_New.kicad_sym"
    new_lib.write_bytes(atomic_lib((atomic_part("NEW-1"), atomic_part("NEW-2"))))

    result = _scan(repos, tmp_path)

    assert list(_statuses(result, "Atomic_New").items()) == [("NEW-1", "new"), ("NEW-2", "new")]
    assert [i.text for i in _change_lines(result)] == [
        f"Symbol Atomic_New / NEW-1: new {SINCE}",
        f"Symbol Atomic_New / NEW-2: new {SINCE}",
    ]


# -- formatting is never a change (D-21) ---------------------------------------------------------------


def test_replacing_every_tab_with_two_spaces_marks_nothing(tmp_path):
    repos = _repos(tmp_path)
    _edit(repos.parent / CONNECTOR, b"\t", b"  ")
    assert _git_says_modified(repos, "Atomic_Connector.kicad_sym")

    result = _scan(repos, tmp_path)

    assert _change_lines(result) == []
    assert _marked(result, "Atomic_Connector") == {}


def test_replacing_every_line_feed_with_crlf_marks_nothing(tmp_path):
    repos = _repos(tmp_path)
    _edit(repos.parent / CONNECTOR, b"\n", b"\r\n")
    assert _git_says_modified(repos, "Atomic_Connector.kicad_sym")

    result = _scan(repos, tmp_path)

    assert _change_lines(result) == []
    assert _marked(result, "Atomic_Connector") == {}


def test_a_checkout_with_autocrlf_and_no_edits_marks_nothing(tmp_path):
    repos = _repos(tmp_path, autocrlf=True)
    assert b"\r\n" in (repos.parent / CONNECTOR).read_bytes()

    result = _scan(repos, tmp_path)

    assert _change_lines(result) == []
    assert _marked(result, "Atomic_Connector") == {}


def test_an_edit_in_a_checkout_with_autocrlf_is_still_found(tmp_path):
    repos = _repos(tmp_path, autocrlf=True)
    _edit_usb_description(repos)

    result = _scan(repos, tmp_path)

    assert _marked(result, "Atomic_Connector") == {"USB4105-GF-A": "changed"}


# -- libraries without the Atomic_ prefix (D-02) -------------------------------------------------------


def test_an_edit_in_a_library_without_the_prefix_gives_only_the_changed_row(tmp_path):
    repos = _repos(tmp_path)
    _edit(repos.parent / LEGACY, b"Test part LEGACY-1", b"Edited by hand in KiCad")

    result = _scan(repos, tmp_path)

    legacy = _lib(result, "Connector_Legacy")
    assert legacy.atomic is False
    assert legacy.symbols == [SymbolEntry("LEGACY-1", status="changed")]
    assert [i.text for i in _change_lines(result)] == [f"Symbol Connector_Legacy / LEGACY-1: changed {SINCE}"]


def test_nothing_outside_custom_is_ever_marked(tmp_path):
    repos = _repos(tmp_path)
    wurth = repos.parent / "WurthElektronik" / "KiCad-Library"
    (wurth / "symbols").mkdir(parents=True)
    (wurth / "symbols" / "WE-Connectors.kicad_sym").write_bytes(atomic_lib((atomic_part("WE-1"),)))
    (wurth / "footprints" / "WE-Connectors.pretty").mkdir(parents=True)
    (wurth / "footprints" / "WE-Connectors.pretty" / "WE-1.kicad_mod").write_bytes(vendor_footprint("WE-1"))

    result = _scan(repos, tmp_path)

    assert _lib(result, "WE-Connectors").symbols == []
    assert _footprint_changes(result, "WE-Connectors") == []
    assert _change_lines(result) == []


# -- footprints (D-04) ---------------------------------------------------------------------------------


def test_an_edited_footprint_is_changed_and_logged(tmp_path):
    repos = _repos(tmp_path)
    _edit(repos.parent / FOOTPRINTS / "GENERIC-2PIN.kicad_mod", b"(attr smd)", b"(attr through_hole)")

    result = _scan(repos, tmp_path)

    assert _footprint_changes(result) == [ChangedFootprint("GENERIC-2PIN", "changed")]
    assert [(i.code, i.text) for i in _change_lines(result)] == [
        ("scan.footprint_changed", f"Footprint Atomic_Footprints / GENERIC-2PIN: changed {SINCE}")
    ]


def test_an_added_footprint_is_new(tmp_path):
    repos = _repos(tmp_path)
    (repos.parent / FOOTPRINTS / "NEW-FP.kicad_mod").write_bytes(vendor_footprint("NEW-FP"))

    result = _scan(repos, tmp_path)

    assert _footprint_changes(result) == [ChangedFootprint("NEW-FP", "new")]
    assert [(i.code, i.text) for i in _change_lines(result)] == [
        ("scan.footprint_new", f"Footprint Atomic_Footprints / NEW-FP: new {SINCE}")
    ]


def test_changed_footprints_are_sorted_by_name_ignoring_case(tmp_path):
    repos = _repos(tmp_path)
    for name in ("Zed-FP", "alpha-fp"):
        (repos.parent / FOOTPRINTS / f"{name}.kicad_mod").write_bytes(vendor_footprint(name))
    _edit(repos.parent / FOOTPRINTS / "GENERIC-2PIN.kicad_mod", b"(attr smd)", b"(attr through_hole)")

    result = _scan(repos, tmp_path)

    assert _footprint_changes(result) == [
        ChangedFootprint("alpha-fp", "new"),
        ChangedFootprint("GENERIC-2PIN", "changed"),
        ChangedFootprint("Zed-FP", "new"),
    ]
    assert [i.text.split(":")[0] for i in _change_lines(result)] == [
        "Footprint Atomic_Footprints / alpha-fp",
        "Footprint Atomic_Footprints / GENERIC-2PIN",
        "Footprint Atomic_Footprints / Zed-FP",
    ]


def test_a_footprint_that_only_changed_its_line_endings_marks_nothing(tmp_path):
    repos = _repos(tmp_path)
    path = repos.parent / FOOTPRINTS / "GENERIC-2PIN.kicad_mod"
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    assert _git_says_modified(repos, "GENERIC-2PIN.kicad_mod")

    result = _scan(repos, tmp_path)

    assert _footprint_changes(result) == []
    assert _change_lines(result) == []


# -- deleted files, and every way the highlight is skipped ---------------------------------------------


def test_a_deleted_library_file_gives_no_error_and_no_entry(tmp_path):
    repos = _repos(tmp_path)
    (repos.parent / "Custom" / "Symbols" / "Atomic_Regulator.kicad_sym").unlink()

    result = _scan(repos, tmp_path)

    assert "Atomic_Regulator" not in {lib.nickname for lib in result.symbol_libs}
    assert _change_lines(result) == []


def test_missing_git_skips_the_highlight_with_one_line_and_keeps_the_atomic_check(tmp_path, monkeypatch):
    repos = _repos(tmp_path)
    _edit_usb_description(repos)
    monkeypatch.setattr(shutil, "which", lambda *args, **kwargs: None)

    result = _scan(repos, tmp_path)

    assert [(i.code, i.severity, i.text) for i in _change_lines(result)] == [
        ("scan.changes_skipped", Severity.INFO, "Change highlight skipped: git was not found on PATH")
    ]
    assert "atomic.summary" in [i.code for i in result.issues]
    assert _marked(result, "Atomic_Connector") == {}


def test_a_custom_that_is_not_a_git_checkout_skips_the_highlight_with_one_line(tmp_path):
    write_atomic_custom(tmp_path / "plain")

    result = scan_all(tmp_path / "plain", kicad_fp_dir=tmp_path / "no_kicad")

    assert [(i.code, i.text) for i in _change_lines(result)] == [
        ("scan.changes_skipped", "Change highlight skipped: Custom is not a git checkout")
    ]
    assert "atomic.summary" in [i.code for i in result.issues]


def test_a_plain_custom_folder_inside_a_git_repository_is_not_a_checkout_either(tmp_path):
    repos = _repos(tmp_path)
    clone = clone_parent_without_submodule(repos)
    write_atomic_files(clone / "Custom")

    result = scan_all(clone, kicad_fp_dir=tmp_path / "no_kicad")

    assert [i.text for i in _change_lines(result)] == ["Change highlight skipped: Custom is not a git checkout"]


def test_a_failing_git_status_skips_the_highlight_with_its_first_line(tmp_path, monkeypatch):
    repos = _repos(tmp_path)
    failure = Issue(Severity.ERROR, "git.failed", "git status failed (git exit 128)\nfatal: something else")
    monkeypatch.setattr(gitops, "status_entries", lambda ctx, repo: failure)

    result = _scan(repos, tmp_path)

    assert [(i.code, i.text) for i in _change_lines(result)] == [
        ("scan.changes_skipped", "Change highlight skipped: git status failed (git exit 128)")
    ]


def test_a_tree_whose_only_library_is_outside_custom_gives_no_skip_line(tmp_path):
    folder = tmp_path / "tree" / "WurthElektronik" / "KiCad-Library" / "symbols"
    folder.mkdir(parents=True)
    (folder / "WE-Connectors.kicad_sym").write_bytes(atomic_lib((atomic_part("WE-1"),)))

    result = scan_all(tmp_path / "tree", kicad_fp_dir=tmp_path / "no_kicad")

    assert _change_lines(result) == []


def test_a_library_over_the_size_cap_is_skipped_with_one_line_and_no_status(tmp_path, monkeypatch):
    repos = _repos(tmp_path)
    _edit_usb_description(repos)
    monkeypatch.setattr(changes, "MAX_KICAD_TEXT_BYTES", 100)

    result = _scan(repos, tmp_path)

    lines = _change_lines(result)
    assert len(lines) == 1
    assert lines[0].code == "scan.changes_skipped"
    assert lines[0].severity is Severity.INFO
    assert lines[0].text.startswith("Change highlight skipped for Atomic_Connector.kicad_sym")
    assert _marked(result, "Atomic_Connector") == {}


# -- git is only read ----------------------------------------------------------------------------------


def _git_calls(monkeypatch) -> list[str]:
    """Record the git subcommand of every subprocess.run from now on."""
    calls: list[str] = []
    real = subprocess.run

    def counting(argv, *args, **kwargs):
        # run_git builds: exe, --literal-pathspecs, -c, core.quotepath=false, -C, <repo>, <subcommand>, ...
        calls.append(argv[6])
        return real(argv, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", counting)
    return calls


def test_a_clean_custom_costs_one_status_call_and_reads_no_head_version(tmp_path, monkeypatch):
    repos = _repos(tmp_path)
    calls = _git_calls(monkeypatch)

    _scan(repos, tmp_path)

    assert calls.count("status") == 1
    assert "cat-file" not in calls


def test_head_versions_are_read_only_for_files_git_reports_as_changed(tmp_path, monkeypatch):
    repos = _repos(tmp_path)
    _edit_usb_description(repos)
    calls = _git_calls(monkeypatch)

    _scan(repos, tmp_path)

    assert calls.count("status") == 1
    assert calls.count("cat-file") == 1


def test_the_scan_leaves_the_git_state_of_custom_alone(tmp_path):
    repos = _repos(tmp_path)
    _edit_usb_description(repos)
    (repos.parent / FOOTPRINTS / "NEW-FP.kicad_mod").write_bytes(vendor_footprint("NEW-FP"))
    state = ("status", "--porcelain=v1", "--untracked-files=all"), ("rev-parse", "HEAD"), ("ls-files", "--stage")
    before = [repos.git(repos.custom, *args) for args in state]

    _scan(repos, tmp_path)

    assert [repos.git(repos.custom, *args) for args in state] == before


def test_changes_calls_only_the_read_only_git_functions():
    tree = ast.parse(Path(changes.__file__).read_text(encoding="utf-8"))
    used = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "gitops"
    }
    assert used <= {"find_git", "show_toplevel", "status_entries", "head_blob", "GitContext"}
    assert {"find_git", "show_toplevel", "status_entries", "head_blob"} <= used
