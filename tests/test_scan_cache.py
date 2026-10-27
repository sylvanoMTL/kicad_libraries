"""The saved scan: round trip, freshness fingerprint, fallback notes, atomic save (O-01 to O-06)."""

import json
import os
import shutil
from pathlib import Path

import pytest
from customfixtures import (
    ATOMIC_LIBRARIES,
    atomic_lib,
    atomic_part,
    write_atomic_custom,
    write_atomic_files,
    write_fake_kicad,
)
from gitfixtures import commit_file, make_superproject, requires_git
from installfixtures import vendor_footprint

from kicad_lib_manager import scan_cache
from kicad_lib_manager.library_scanner import _collect_files, find_footprint_libs, find_symbol_libs, scan_all
from kicad_lib_manager.models import Severity

NO_CHANGE = "Showing the saved scan from"
FALLBACK = "scanning the whole repository."
CONNECTOR = "Custom/Symbols/Atomic_Connector.kicad_sym"


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    write_atomic_custom(root)
    return root


@pytest.fixture
def kicad(tmp_path):
    footprints, _models = write_fake_kicad(tmp_path)
    return footprints


@pytest.fixture
def cache_file(tmp_path):
    return tmp_path / "state" / "scan_cache" / "abc.json"


def _saved(repo, kicad, cache_file):
    """Scan, save and return the scan result."""
    fp = scan_cache.fingerprint(repo, kicad)
    result = scan_all(repo, kicad_fp_dir=kicad)
    assert scan_cache.save(cache_file, repo, kicad, fp, result) is None
    return result


def _bump(path: Path, seconds: int = 5) -> None:
    info = path.stat()
    os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + seconds * 1_000_000_000))


def _rewrite(cache_file: Path, edit) -> None:
    payload = json.loads(cache_file.read_text(encoding="utf-8"))
    edit(payload)
    cache_file.write_text(json.dumps(payload), encoding="utf-8")


# ── encode and decode ────────────────────────────────────────────────

def test_round_trip_keeps_every_field_and_drops_selection(repo, kicad):
    result = scan_all(repo, kicad_fp_dir=kicad)
    result.symbol_libs[0].selected = True
    result.footprint_libs[0].selected = True
    assert any(e.violations for lib in result.symbol_libs for e in lib.symbols)
    assert any(e.violations and any(v.fixes or v.fill for v in e.violations)
               for lib in result.symbol_libs for e in lib.symbols)

    data = json.loads(json.dumps(scan_cache.encode_result(result)))
    back = scan_cache.decode_result(data)

    result.symbol_libs[0].selected = False
    result.footprint_libs[0].selected = False
    assert back == result
    assert all(not lib.selected for lib in back.symbol_libs + back.footprint_libs)
    assert any(lib.collision_peers for lib in back.footprint_libs)


def test_round_trip_keeps_change_marks(tmp_path):
    from kicad_lib_manager.models import (
        ChangedFootprint, FootprintLibrary, ScanResult, SymbolEntry, SymbolLibrary,
    )
    result = ScanResult(
        symbol_libs=[SymbolLibrary("A", "Custom/A.kicad_sym", "Custom", symbols=[
            SymbolEntry("S", extends="P", status="new")])],
        footprint_libs=[FootprintLibrary("B", "Custom/B.pretty", "Custom", changed=[
            ChangedFootprint("F", "changed")])],
    )
    assert scan_cache.decode_result(json.loads(json.dumps(scan_cache.encode_result(result)))) == result


@pytest.mark.parametrize("edit", [
    lambda d: d["symbol_libs"][0].pop("nickname"),
    lambda d: d["symbol_libs"][0].update(nickname=5),
    lambda d: d["issues"].append(["loud", "x", "y"]),
    lambda d: d["issues"].append(["info", "x"]),
    lambda d: d["symbol_libs"][0].update(atomic="yes"),
    lambda d: d["footprint_libs"][0].update(changed=[["F", "gone"]]),
    lambda d: d.update(issues="none"),
])
def test_decode_rejects_odd_data(repo, kicad, edit):
    data = json.loads(json.dumps(scan_cache.encode_result(scan_all(repo, kicad_fp_dir=kicad))))
    edit(data)
    with pytest.raises((ValueError, TypeError, KeyError)):
        scan_cache.decode_result(data)


# ── fingerprint ──────────────────────────────────────────────────────

def test_fingerprint_records_exactly_the_scanner_inputs(repo, kicad):
    for skipped in ("env", "tests", "downloaded_examples"):
        (repo / skipped).mkdir()
        (repo / skipped / "X.kicad_sym").write_bytes(b"(kicad_symbol_lib)")
    (repo / "Custom" / "tests").mkdir()
    (repo / "Custom" / "tests" / "Inner.kicad_sym").write_bytes(b"(kicad_symbol_lib)")

    fp = scan_cache.fingerprint(repo, kicad)

    sym_keys = {k for k in fp["files"] if k.endswith(".kicad_sym")}
    assert sym_keys == {lib.rel_path for lib in find_symbol_libs(repo)}
    assert "Custom/tests/Inner.kicad_sym" in sym_keys
    assert not any(k.startswith(("env/", "tests/", "downloaded_examples/")) for k in fp["files"])
    assert set(fp["folders"]) == {lib.rel_path for lib in find_footprint_libs(repo)}
    mod_keys = {k for k in fp["files"] if k.endswith(".kicad_mod")}
    assert mod_keys == {f.relative_to(repo).as_posix() for f in _collect_files(repo, "*.kicad_mod")}
    assert any(k.startswith("Custom/3DModels/") for k in fp["files"])
    assert fp["complete"] is True
    assert json.loads(json.dumps(fp)) == fp


def test_fingerprint_changes_for_every_scanner_input(repo, kicad):
    base = scan_cache.fingerprint(repo, kicad)
    sym = repo / CONNECTOR

    _bump(sym)
    after_edit = scan_cache.fingerprint(repo, kicad)
    assert after_edit != base

    mod = repo / "Custom/Footprints/Atomic_Footprints.pretty/Extra.kicad_mod"
    mod.write_bytes(vendor_footprint("Extra"))
    after_add = scan_cache.fingerprint(repo, kicad)
    assert after_add != after_edit
    mod.unlink()
    assert scan_cache.fingerprint(repo, kicad)["files"] == after_edit["files"]

    (repo / "Custom" / "Footprints" / "Empty.pretty").mkdir()
    after_folder = scan_cache.fingerprint(repo, kicad)
    assert "Custom/Footprints/Empty.pretty" in after_folder["folders"]

    (repo / "Custom" / "3DModels" / "new.step").write_bytes(b"x")
    after_model = scan_cache.fingerprint(repo, kicad)
    assert after_model["files"] != after_folder["files"]

    (repo / "Custom" / ".gitignore").write_bytes(b"*.bak\n")
    assert scan_cache.fingerprint(repo, kicad)["files"] != after_model["files"]


def test_fingerprint_ignores_unrelated_files(repo, kicad):
    base = scan_cache.fingerprint(repo, kicad)
    (repo / "README.md").write_text("hello")
    (repo / "env").mkdir()
    (repo / "env" / "thing.kicad_mod").write_bytes(b"x")
    (repo / "Other" / "notes.txt").write_text("hello")
    assert scan_cache.fingerprint(repo, kicad) == base


def test_fingerprint_reads_the_kicad_folder(repo, kicad, tmp_path):
    fp = scan_cache.fingerprint(repo, kicad)
    assert fp["kicad"][0] == str(kicad)
    assert fp["kicad"][1] is not None and fp["kicad"][2] is not None
    other = scan_cache.fingerprint(repo, tmp_path / "nowhere")
    assert other["kicad"] == [str(tmp_path / "nowhere"), None, None]


@requires_git
def test_custom_git_part_follows_commits_not_pack_refs(tmp_path):
    repos = make_superproject(tmp_path / "git", populate=write_atomic_files)
    kicad = tmp_path / "no_kicad"
    detached = scan_cache.fingerprint(repos.parent, kicad)["custom_git"]
    assert detached and detached != "none"

    commit_file(repos, repos.custom, "Symbols/Extra.txt", b"x", "Add a file")
    committed = scan_cache.fingerprint(repos.parent, kicad)["custom_git"]
    assert committed != detached

    repos.git(repos.custom, "checkout", "-b", "feature")
    commit_file(repos, repos.custom, "Symbols/More.txt", b"y", "More")
    on_branch = scan_cache.fingerprint(repos.parent, kicad)["custom_git"]
    assert on_branch.startswith("ref: refs/heads/feature|")
    repos.git(repos.custom, "pack-refs", "--all")
    assert scan_cache.fingerprint(repos.parent, kicad)["custom_git"] == on_branch


def test_custom_git_state_rejects_unsafe_refs(tmp_path):
    custom = tmp_path / "Custom"
    (custom / ".git").mkdir(parents=True)
    (custom / ".git" / "HEAD").write_text("ref: refs/../../escape\n")
    assert scan_cache._custom_git_state(custom) is None
    (custom / ".git" / "HEAD").write_text("ref: heads/main\n")
    assert scan_cache._custom_git_state(custom) is None
    (custom / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
    assert scan_cache._custom_git_state(custom) == "ref: refs/heads/main|"
    assert scan_cache._custom_git_state(tmp_path / "Missing") == "none"


# ── load_fresh ───────────────────────────────────────────────────────

def test_unchanged_repo_reuses_the_saved_result(repo, kicad, cache_file):
    result = _saved(repo, kicad, cache_file)

    check = scan_cache.load_fresh(cache_file, repo, kicad)

    assert check.result == result
    assert check.note.code == "cache.reused"
    assert check.note.severity is Severity.INFO
    assert check.note.text.startswith(NO_CHANGE)
    assert "no library file changed since then. Use Rescan for a full scan." in check.note.text
    assert check.fingerprint is not None


def test_missing_file(repo, kicad, cache_file):
    check = scan_cache.load_fresh(cache_file, repo, kicad)
    assert check.result is None
    assert check.note.code == "cache.missing"
    assert check.note.text == f"No saved scan yet; {FALLBACK}"


@pytest.mark.parametrize("text", ["{not json", "[]", "null", '{"format": 1}', "\x00\x01"])
def test_garbage_is_unreadable(repo, kicad, cache_file, text):
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text(text, encoding="utf-8")
    check = scan_cache.load_fresh(cache_file, repo, kicad)
    assert check.result is None
    assert check.note.code == "cache.unreadable"
    assert check.note.text == f"The saved scan could not be read; {FALLBACK}"


def test_invalid_utf8_is_unreadable(repo, kicad, cache_file):
    cache_file.parent.mkdir(parents=True)
    cache_file.write_bytes(b"\xff\xfe\x00{")
    assert scan_cache.load_fresh(cache_file, repo, kicad).note.code == "cache.unreadable"


def test_oversized_file_is_unreadable(repo, kicad, cache_file, monkeypatch):
    _saved(repo, kicad, cache_file)
    monkeypatch.setattr(scan_cache, "MAX_CACHE_BYTES", 10)
    check = scan_cache.load_fresh(cache_file, repo, kicad)
    assert check.result is None
    assert check.note.code == "cache.unreadable"


def test_bad_saved_time_is_unreadable(repo, kicad, cache_file):
    _saved(repo, kicad, cache_file)
    _rewrite(cache_file, lambda p: p.update(saved_at="yesterday"))
    assert scan_cache.load_fresh(cache_file, repo, kicad).note.code == "cache.unreadable"


def test_wrong_format_and_other_code_are_a_different_version(repo, kicad, cache_file, monkeypatch):
    _saved(repo, kicad, cache_file)
    text = f"The saved scan was made by a different version of this app; {FALLBACK}"

    _rewrite(cache_file, lambda p: p.update(format=99))
    check = scan_cache.load_fresh(cache_file, repo, kicad)
    assert (check.result, check.note.code, check.note.text) == (None, "cache.other_version", text)

    _saved(repo, kicad, cache_file)
    monkeypatch.setattr(scan_cache, "_code_signature", lambda: "different")
    check = scan_cache.load_fresh(cache_file, repo, kicad)
    assert (check.result, check.note.code, check.note.text) == (None, "cache.other_version", text)

    monkeypatch.setattr(scan_cache, "_code_signature", lambda: "")
    assert scan_cache.load_fresh(cache_file, repo, kicad).note.code == "cache.other_version"


def test_another_repo_root(repo, kicad, cache_file, tmp_path):
    _saved(repo, kicad, cache_file)
    other = tmp_path / "other"
    shutil.copytree(repo, other)
    check = scan_cache.load_fresh(cache_file, other, kicad)
    assert check.result is None
    assert check.note.code == "cache.other_copy"
    assert check.note.text == f"The saved scan belongs to another copy of the repository; {FALLBACK}"


def test_other_kicad_folder(repo, kicad, cache_file, tmp_path):
    _saved(repo, kicad, cache_file)
    check = scan_cache.load_fresh(cache_file, repo, tmp_path / "other_kicad")
    assert check.result is None
    assert check.note.code == "cache.kicad_changed"
    assert check.note.text == f"The KiCad footprint folder changed since the saved scan; {FALLBACK}"


def test_one_and_many_edited_files(repo, kicad, cache_file):
    _saved(repo, kicad, cache_file)
    _bump(repo / CONNECTOR)
    check = scan_cache.load_fresh(cache_file, repo, kicad)
    assert check.result is None
    assert check.note.code == "cache.stale"
    assert check.note.text == f"1 library file changed since the saved scan; {FALLBACK}"
    assert check.fingerprint is not None

    _bump(repo / "Custom/Symbols/Atomic_Empty.kicad_sym")
    _bump(repo / "Custom/Symbols/Atomic_Regulator.kicad_sym")
    check = scan_cache.load_fresh(cache_file, repo, kicad)
    assert check.note.text == f"3 library files changed since the saved scan; {FALLBACK}"


def test_added_and_removed_folder_and_model_count(repo, kicad, cache_file):
    _saved(repo, kicad, cache_file)
    (repo / "Custom" / "Footprints" / "Empty.pretty").mkdir()
    assert "1 library file changed" in scan_cache.load_fresh(cache_file, repo, kicad).note.text
    (repo / "Custom" / "Footprints" / "Empty.pretty").rmdir()
    (repo / "Custom" / "3DModels" / "z.step").write_bytes(b"1")
    assert "1 library file changed" in scan_cache.load_fresh(cache_file, repo, kicad).note.text


@requires_git
def test_a_custom_commit_forces_a_full_scan(tmp_path):
    repos = make_superproject(tmp_path / "git", populate=write_atomic_files)
    kicad = tmp_path / "no_kicad"
    cache_file = tmp_path / "cache.json"
    fp = scan_cache.fingerprint(repos.parent, kicad)
    result = scan_all(repos.parent, kicad_fp_dir=kicad)
    assert scan_cache.save(cache_file, repos.parent, kicad, fp, result) is None
    assert scan_cache.load_fresh(cache_file, repos.parent, kicad).note.code == "cache.reused"

    commit_file(repos, repos.custom, "Notes.txt", b"x", "Commit that touches no library file")

    check = scan_cache.load_fresh(cache_file, repos.parent, kicad)
    assert check.result is None
    assert check.note.code == "cache.custom_commit"
    assert check.note.text == (
        "The Custom library was committed or switched to another version since the "
        f"saved scan; {FALLBACK}"
    )


def test_incomplete_fingerprint_is_never_fresh(repo, kicad, cache_file):
    _saved(repo, kicad, cache_file)
    _rewrite(cache_file, lambda p: p["fingerprint"].update(complete=False))
    check = scan_cache.load_fresh(cache_file, repo, kicad)
    assert check.result is None
    assert check.note.code == "cache.incomplete"
    assert check.note.text == f"Could not check every library file for changes; {FALLBACK}"


def test_library_the_freshness_check_did_not_see(repo, kicad, cache_file):
    _saved(repo, kicad, cache_file)

    def add_ghost(payload):
        payload["result"]["symbol_libs"][0]["rel_path"] = "Custom/Symbols/Ghost.kicad_sym"

    _rewrite(cache_file, add_ghost)
    check = scan_cache.load_fresh(cache_file, repo, kicad)
    assert check.result is None
    assert check.note.code == "cache.unreadable"


def test_decode_failure_is_unreadable(repo, kicad, cache_file):
    _saved(repo, kicad, cache_file)
    _rewrite(cache_file, lambda p: p["result"]["issues"].append(["loud", "x", "y"]))
    assert scan_cache.load_fresh(cache_file, repo, kicad).note.code == "cache.unreadable"


# ── save ─────────────────────────────────────────────────────────────

def test_save_into_a_folder_warns_and_raises_nothing(repo, kicad, tmp_path):
    target = tmp_path / "is_a_folder"
    target.mkdir()
    fp = scan_cache.fingerprint(repo, kicad)
    issue = scan_cache.save(target, repo, kicad, fp, scan_all(repo, kicad_fp_dir=kicad))
    assert issue is not None
    assert issue.severity is Severity.WARNING
    assert issue.code == "cache.save_failed"
    assert issue.text.startswith("Could not save this scan for the next start: ")


def test_save_without_fingerprint_warns(repo, kicad, cache_file):
    issue = scan_cache.save(cache_file, repo, kicad, None, scan_all(repo, kicad_fp_dir=kicad))
    assert issue.code == "cache.save_failed"
    assert "the library files could not be listed" in issue.text
    assert not cache_file.exists()


def test_save_leaves_no_temp_file_and_no_selection(repo, kicad, cache_file):
    result = scan_all(repo, kicad_fp_dir=kicad)
    result.symbol_libs[0].selected = True
    assert scan_cache.save(cache_file, repo, kicad, scan_cache.fingerprint(repo, kicad), result) is None
    assert [p.name for p in cache_file.parent.iterdir()] == [cache_file.name]
    assert '"selected"' not in cache_file.read_text(encoding="utf-8")


def test_code_signature_is_stable_and_hex():
    first = scan_cache._code_signature()
    assert first == scan_cache._code_signature()
    assert len(first) == 64


# ── update_library ───────────────────────────────────────────────────

def _edit_connector(repo):
    path = repo / CONNECTOR
    symbols = next(lib.symbols for lib in ATOMIC_LIBRARIES if lib.name == "Atomic_Connector")
    path.write_bytes(atomic_lib(symbols + (atomic_part("NEW-ONE"),)))
    return path


def test_update_library_refreshes_only_that_librarys_keys(repo, kicad, cache_file):
    _saved(repo, kicad, cache_file)
    _edit_connector(repo)
    entries = scan_cache.library_entries(repo, scan_cache.KIND_SYMBOL, CONNECTOR)
    assert entries["complete"] is True and list(entries["files"]) == [CONNECTOR]
    new_result = scan_all(repo, kicad_fp_dir=kicad)

    note = scan_cache.update_library(
        cache_file, repo, kicad, new_result, scan_cache.KIND_SYMBOL, CONNECTOR, entries
    )

    assert note is None
    check = scan_cache.load_fresh(cache_file, repo, kicad)
    assert check.note.code == "cache.reused"
    assert check.result == new_result
    assert any(e.name == "NEW-ONE" for lib in check.result.symbol_libs for e in lib.symbols)


def test_update_library_keeps_other_changes_stale(repo, kicad, cache_file):
    _saved(repo, kicad, cache_file)
    _edit_connector(repo)
    _bump(repo / "Custom/Symbols/Atomic_Empty.kicad_sym")
    entries = scan_cache.library_entries(repo, scan_cache.KIND_SYMBOL, CONNECTOR)

    assert scan_cache.update_library(
        cache_file, repo, kicad, scan_all(repo, kicad_fp_dir=kicad),
        scan_cache.KIND_SYMBOL, CONNECTOR, entries,
    ) is None

    check = scan_cache.load_fresh(cache_file, repo, kicad)
    assert check.result is None
    assert check.note.code == "cache.stale"
    assert "1 library file changed" in check.note.text


def test_update_footprint_library_replaces_its_folder_keys(repo, kicad, cache_file):
    rel = "Custom/Footprints/Atomic_Footprints.pretty"
    _saved(repo, kicad, cache_file)
    (repo / rel / "Brand_New.kicad_mod").write_bytes(vendor_footprint("Brand_New"))
    (repo / rel / "GENERIC-2PIN.kicad_mod").unlink()
    entries = scan_cache.library_entries(repo, scan_cache.KIND_FOOTPRINT, rel)
    assert rel in entries["folders"]
    assert f"{rel}/Brand_New.kicad_mod" in entries["files"]
    assert f"{rel}/GENERIC-2PIN.kicad_mod" not in entries["files"]

    assert scan_cache.update_library(
        cache_file, repo, kicad, scan_all(repo, kicad_fp_dir=kicad),
        scan_cache.KIND_FOOTPRINT, rel, entries,
    ) is None

    assert scan_cache.load_fresh(cache_file, repo, kicad).note.code == "cache.reused"


def test_update_library_without_a_saved_scan_writes_nothing(repo, kicad, cache_file):
    entries = scan_cache.library_entries(repo, scan_cache.KIND_SYMBOL, CONNECTOR)
    note = scan_cache.update_library(
        cache_file, repo, kicad, scan_all(repo, kicad_fp_dir=kicad),
        scan_cache.KIND_SYMBOL, CONNECTOR, entries,
    )
    assert note.code == "cache.not_updated"
    assert note.text == "The saved scan was not updated, so the next start scans the whole repository."
    assert not cache_file.exists()


def test_update_library_with_incomplete_entries_writes_nothing(repo, kicad, cache_file):
    _saved(repo, kicad, cache_file)
    before = cache_file.read_bytes()
    entries = scan_cache.library_entries(repo, scan_cache.KIND_SYMBOL, "Custom/Symbols/Gone.kicad_sym")
    assert entries["complete"] is False
    note = scan_cache.update_library(
        cache_file, repo, kicad, scan_all(repo, kicad_fp_dir=kicad),
        scan_cache.KIND_SYMBOL, "Custom/Symbols/Gone.kicad_sym", entries,
    )
    assert note.code == "cache.not_updated"
    assert cache_file.read_bytes() == before
    assert scan_cache.update_library(
        cache_file, repo, kicad, scan_all(repo, kicad_fp_dir=kicad),
        scan_cache.KIND_SYMBOL, CONNECTOR, None,
    ).code == "cache.not_updated"
