"""The atomic-check UAT setup (D-25): a throwaway repo copy made from the owner's real parts plus the synthetic Atomic_ cases.

The live Custom/ holds no Atomic_ library until Phase 13, so the full Phase 9 behaviour (marks, highlights, the
check dialog, every fix kind) can only be seen on a scratch copy. ``build_atomic_uat`` reads ``source_custom`` and
writes only under ``dest``. The automated tests prove it on the synthetic Custom/; the opt-in test builds it from
the live Custom/ (read only) for the owner to open in the app.
"""

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from customfixtures import (
    ATOMIC_FOOTPRINTS,
    atomic_lib,
    atomic_part,
    digest_custom,
    digest_tree,
    write_atomic_files,
    write_fake_kicad,
    write_synthetic_custom,
)
from gitfixtures import GIT, requires_git

from kicad_lib_manager import fsutil, kicad_files, sexpr
from kicad_lib_manager.atomic_check import ATOMIC_PREFIX, ATOMIC_RULES, SAFE_FIX_KINDS
from kicad_lib_manager.atomic_fixes import build_preview
from kicad_lib_manager.library_scanner import scan_all
from kicad_lib_manager.models import ChangedFootprint, Issue, Severity

REPO_ROOT = Path(__file__).resolve().parent.parent
UAT_MARKER = ".atomic_uat_scratch"
# (source library stem, Atomic_ name it gets in the scratch copy); a stem missing from the source is replaced
REAL_PARTS = (("Connector_FFC_GCT", "Atomic_Connector_FFC-FPC"), ("IC_Battery_Charger_TI", "Atomic_Battery_Management"))
EDITED_DATASHEET = "https://example.com/uat-edit.pdf"
EDITED_DESCRIPTION = "UAT edit: description changed"
NEW_FOOTPRINT = "NEW-UAT"
_GIT_TIMEOUT = 120


def _is_link(path: Path) -> bool:
    """True for a symbolic link and, where Python can tell, a junction."""
    junction = getattr(path, "is_junction", None)
    return path.is_symlink() or bool(junction and junction())


def _inside_or_equal(path: Path, folder: Path) -> bool:
    return path == folder or folder in path.parents


def _remove_tree(folder: Path) -> None:
    """Remove folder, clearing the read-only flag git puts on its object files (Windows refuses to delete them)."""

    def clear(function, name, _error):
        os.chmod(name, stat.S_IWRITE)
        function(name)

    if sys.version_info >= (3, 12):
        shutil.rmtree(folder, onexc=clear)
    else:
        shutil.rmtree(folder, onerror=clear)


def _isolated_env(dest: Path) -> dict:
    """The environment gitfixtures builds: no GIT_* variables, an empty global config, no system config, no prompts."""
    config = dest / ".atomic_uat_gitconfig"
    config.write_bytes(b"")
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=str(config), GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")
    return env


def _git(custom: Path, env: dict, *args: str) -> None:
    """Run git in the scratch Custom/ with identity, signing and autocrlf given on the command line."""
    command = [
        GIT,
        "-c", "user.name=UAT",
        "-c", "user.email=uat@example.invalid",
        "-c", "commit.gpgsign=false",
        "-c", "core.autocrlf=false",
        "-c", "init.defaultBranch=main",
        *args,
    ]
    run = subprocess.run(command, cwd=custom, env=env, capture_output=True, timeout=_GIT_TIMEOUT)
    if run.returncode != 0:
        detail = run.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(args)} failed in {custom} (exit {run.returncode}): {detail}")


def _check_destination(dest: Path, scratch: Path, source: Path, app_root: Path) -> None:
    """Refuse every destination that could reach the repository, the source or a folder this helper did not make."""
    assert not _inside_or_equal(dest, app_root) and not _inside_or_equal(app_root, dest), (
        f"{dest} must lie outside the repository {app_root}"
    )
    assert not _inside_or_equal(scratch, source) and not _inside_or_equal(source, scratch), (
        f"{scratch} and the source {source} must not contain each other"
    )
    assert not _is_link(scratch), f"{scratch} is a link"
    if scratch.exists() and not (scratch / UAT_MARKER).is_file():
        raise AssertionError(f"{scratch} exists and was not made by this helper; remove it yourself")


def _source_stems(symbols_dir: Path) -> list[str]:
    return sorted(path.stem for path in symbols_dir.glob("*.kicad_sym"))


def _renamed_parts(stems: list[str]) -> list[tuple[str, str]]:
    """Pair each REAL_PARTS name with a source stem; a missing stem gives way to the first unused source stem."""
    named = {stem for stem, _ in REAL_PARTS}
    used: set[str] = set()
    pairs = []
    for stem, atomic_name in REAL_PARTS:
        chosen = stem if stem in stems else None
        if chosen is None:
            chosen = next((s for s in stems if s not in named and s not in used), None)
        assert chosen is not None, f"the source holds no library to rename to {atomic_name}"
        used.add(chosen)
        pairs.append((chosen, atomic_name))
    return pairs


def _edit_first_symbol(path: Path) -> None:
    """Change the first symbol of a library file, keeping every other byte and the file's encoding.

    Edits the first of Description, ki_description and Datasheet the symbol has (Description is what the owner
    edited by hand in UAT). A symbol with none of them gets a hidden Datasheet instead.
    """
    loaded = kicad_files.load(path)
    assert not isinstance(loaded, Issue), f"could not read {path.name}: {loaded}"
    symbols = kicad_files.find_symbols(loaded.root)
    assert symbols, f"{path.name} holds no symbol"
    ref = symbols[0]
    for name, value in (
        ("Description", EDITED_DESCRIPTION),
        ("ki_description", EDITED_DESCRIPTION),
        ("Datasheet", EDITED_DATASHEET),
    ):
        prop = kicad_files.find_property(ref.node, name)
        if prop is not None:
            edit = kicad_files.set_property_edit(prop, value)
            break
    else:
        # Same insert sequence as atomic_fixes._insert_property, which is private
        version = kicad_files.file_version(loaded.root)
        next_id = kicad_files.next_property_id(ref.node)
        template = kicad_files.hidden_template(ref.node)
        if template is not None:
            block = kicad_files.new_property_text(
                loaded.source.text, template, "Datasheet", EDITED_DATASHEET, next_id, version=version)
        else:
            block = kicad_files.synth_property_text(
                "Datasheet", EDITED_DATASHEET, version=version, next_id=next_id)
        edit = kicad_files.property_insert_edit(loaded.source.text, ref.node, block, loaded.source.eol)
    text = sexpr.apply_edits(loaded.source.text, [edit])
    path.write_bytes(fsutil.encode_source(text, loaded.source.bom))


def build_atomic_uat(dest: Path, source_custom: Path, app_root: Path) -> Path:
    """Build the scratch repo for the atomic-check UAT under dest and return its folder (dest / "repo").

    The scratch holds the app code, the source Custom/ libraries with two real libraries renamed to Atomic_ names,
    the synthetic Atomic_ inventory and Custom/ as its own git repo with one baseline commit. After that commit
    one symbol of a real Atomic_ library and one symbol of a library without the prefix are edited (a property
    the symbol already has changes, or a Datasheet is added when it has neither) and one footprint is added, so
    the app shows Changed, Changed and New. source_custom is only read.
    """
    dest, source_custom, app_root = Path(dest).resolve(), Path(source_custom).resolve(), Path(app_root).resolve()
    scratch = dest / "repo"
    _check_destination(dest, scratch, source_custom, app_root)
    if GIT is None:
        raise RuntimeError("git is not on PATH")
    assert (source_custom / "Symbols").is_dir(), f"{source_custom} holds no Symbols folder"

    dest.mkdir(parents=True, exist_ok=True)
    if scratch.exists():
        _remove_tree(scratch)
    scratch.mkdir()
    (scratch / UAT_MARKER).write_text("made by tests/test_atomic_uat.py; safe to delete\n", encoding="utf-8")

    shutil.copytree(app_root / "kicad_lib_manager", scratch / "kicad_lib_manager", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(app_root / "kicad_lib_manager.py", scratch / "kicad_lib_manager.py")

    custom = scratch / "Custom"
    custom.mkdir()
    for name in ("Symbols", "Footprints", "3DModels"):
        if (source_custom / name).is_dir():
            shutil.copytree(source_custom / name, custom / name, ignore=shutil.ignore_patterns("*.bak"))
    symbols_dir = custom / "Symbols"
    renamed = _renamed_parts(_source_stems(symbols_dir))
    for stem, atomic_name in renamed:
        (symbols_dir / f"{stem}.kicad_sym").rename(symbols_dir / f"{atomic_name}.kicad_sym")
    # taken before the synthetic inventory is written, so the edited plain library is one of the owner's parts
    source_plain = [s for s in _source_stems(symbols_dir) if not s.startswith(ATOMIC_PREFIX)]
    assert source_plain, "the source holds no library without the Atomic_ prefix left to edit"
    write_atomic_files(custom)

    env = _isolated_env(dest)
    _git(custom, env, "init")
    _git(custom, env, "add", "-A")
    _git(custom, env, "commit", "-m", "UAT baseline")

    _edit_first_symbol(symbols_dir / f"{renamed[0][1]}.kicad_sym")
    _edit_first_symbol(symbols_dir / f"{source_plain[0]}.kicad_sym")
    pretty = custom / "Footprints" / f"{ATOMIC_FOOTPRINTS}.pretty"
    shutil.copyfile(pretty / "GENERIC-2PIN.kicad_mod", pretty / f"{NEW_FOOTPRINT}.kicad_mod")
    return scratch


def _safe_fixes(result):
    """Every safe fix of the scan: one-click fixes of violations plus the fix of each finding."""
    found = []
    for lib in result.symbol_libs:
        for entry in lib.symbols:
            for violation in entry.violations:
                found.extend(fix for fix in violation.fixes if fix.kind in SAFE_FIX_KINDS)
            found.extend(f.fix for f in entry.findings if f.fix is not None and f.fix.kind in SAFE_FIX_KINDS)
    return found


@requires_git
def test_build_atomic_uat_tree(tmp_path):
    source = write_synthetic_custom(tmp_path / "live").custom_dir
    before = digest_tree(source)

    scratch = build_atomic_uat(tmp_path / "uat", source, REPO_ROOT)

    assert scratch == (tmp_path / "uat" / "repo").resolve()
    assert (scratch / "kicad_lib_manager.py").is_file() and (scratch / UAT_MARKER).is_file()
    assert (scratch / "Custom" / ".git").exists(), "Custom/ must be its own git repo"
    footprints_dir, _ = write_fake_kicad(tmp_path)
    result = scan_all(scratch, kicad_fp_dir=footprints_dir)

    atomic = {lib.nickname: lib for lib in result.symbol_libs if lib.atomic}
    assert "Atomic_Connector_FFC-FPC" in atomic and "Atomic_Battery_Management" in atomic
    # the two renamed libraries came from the source, not from the synthetic inventory
    assert {"IC_IMU_TDK", "IC_Battery_Charger_TI"}.isdisjoint(lib.nickname for lib in result.symbol_libs)
    assert atomic["Atomic_Battery_Management"].symbols and atomic["Atomic_Connector_FFC-FPC"].symbols

    failed_rules = {v.rule for lib in result.symbol_libs for e in lib.symbols for v in e.violations}
    assert failed_rules == set(ATOMIC_RULES)
    assert {fix.kind for fix in _safe_fixes(result)} == set(SAFE_FIX_KINDS)

    changed = [(lib.nickname, e.name) for lib in result.symbol_libs for e in lib.symbols if e.status == "changed"]
    assert sorted(lib.startswith(ATOMIC_PREFIX) for lib, _ in changed) == [False, True], changed
    assert not [e for lib in result.symbol_libs for e in lib.symbols if e.status == "new"]
    footprints = {lib.nickname: lib.changed for lib in result.footprint_libs if lib.changed}
    assert footprints == {ATOMIC_FOOTPRINTS: [ChangedFootprint(NEW_FOOTPRINT, "new")]}

    preview = build_preview(scratch, _safe_fixes(result))
    assert preview.changes, preview.issues
    assert not [i for i in preview.issues if i.severity is Severity.ERROR], preview.issues
    assert digest_tree(source) == before, "the helper wrote into its source"


def test_build_refuses_inside_repo(tmp_path):
    source = write_synthetic_custom(tmp_path / "live").custom_dir
    dest = REPO_ROOT / "zz_uat"
    with pytest.raises(AssertionError):
        build_atomic_uat(dest, source, REPO_ROOT)
    assert not dest.exists()
    # a destination that contains the repository is refused too
    with pytest.raises(AssertionError):
        build_atomic_uat(REPO_ROOT.parent, source, REPO_ROOT)
    assert not (REPO_ROOT.parent / "repo" / UAT_MARKER).exists()


def test_build_refuses_foreign_scratch(tmp_path):
    source = write_synthetic_custom(tmp_path / "live").custom_dir
    foreign = tmp_path / "uat" / "repo"
    foreign.mkdir(parents=True)
    (foreign / "keep.txt").write_text("not yours\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="was not made by this helper"):
        build_atomic_uat(tmp_path / "uat", source, REPO_ROOT)
    assert (foreign / "keep.txt").read_text(encoding="utf-8") == "not yours\n"
    assert not (foreign / UAT_MARKER).exists()


@requires_git
@pytest.mark.skipif(
    not os.environ.get("KICAD_ATOMIC_UAT_DIR"),
    reason="set KICAD_ATOMIC_UAT_DIR to build the atomic-check UAT scratch repo",
)
def test_uat_atomic_scratch():
    """Build the owner's atomic-check UAT scratch repo (D-25) outside the repository; the live Custom/ is only read."""
    live = REPO_ROOT / "Custom"
    if not (live / "Symbols").is_dir():
        pytest.skip("Custom submodule not checked out (git submodule update --init Custom)")
    dest = Path(os.environ["KICAD_ATOMIC_UAT_DIR"]).resolve()
    before = digest_custom(live)

    scratch = build_atomic_uat(dest, live, REPO_ROOT)

    assert digest_custom(live) == before, "the helper changed the live Custom/"
    python = Path("env") / "Scripts" / "python.exe"
    print(f"\nUAT scratch repo: {scratch}")
    print(f"Run the app on it: {python} {scratch / 'kicad_lib_manager.py'}")
    print("Check in the app:")
    print("  1. Atomic_ libraries with problems open to their parts; each part stays collapsed and shows its Status count (for example 'Changed · 3 rules').")
    print("  2. Expand a failing part: one amber row per broken rule and one plain row per note, worded as in the tooltip, the log and the dialog.")
    print("  3. Double-click a problem row: Check Atomic Parts opens on its part.")
    print("  4. One real Atomic_ part and one part of a library without the prefix show Changed, the footprint NEW-UAT shows New.")
    print("  5. Ctrl+Shift+A (or double-click an amber part): apply one fix of each kind, check the preview and the rescan.")
    print("  6. With KiCad open, preview again: the KiCad-running warning is shown.")


# ── the helper edits a property the first symbol has, or adds a Datasheet ──

def _first_symbol(path: Path):
    loaded = kicad_files.load(path)
    assert not isinstance(loaded, Issue), loaded
    return loaded, kicad_files.find_symbols(loaded.root)


def _property_names(symbol) -> list[str]:
    return [c.children[1].text for c in symbol.node.children if c.head == "property"]


def _write_lib(tmp_path: Path, symbols, *, eol: str = "\n") -> Path:
    path = tmp_path / "Lib.kicad_sym"
    path.write_bytes(atomic_lib(symbols, eol=eol))
    return path


def test_edit_first_symbol_edits_description_when_there_is_no_datasheet(tmp_path):
    path = _write_lib(tmp_path, (atomic_part("NO-DS", drop=("Datasheet",)), atomic_part("SECOND")))
    original = path.read_text(encoding="utf-8")

    _edit_first_symbol(path)

    expected = original.replace('"Test part NO-DS"', f'"{EDITED_DESCRIPTION}"', 1)
    assert path.read_text(encoding="utf-8") == expected
    _, symbols = _first_symbol(path)
    assert kicad_files.find_property(symbols[0].node, "Description").value == EDITED_DESCRIPTION
    assert kicad_files.find_property(symbols[0].node, "Datasheet") is None
    assert "Test part SECOND" in path.read_text(encoding="utf-8")


def test_edit_first_symbol_edits_datasheet_when_there_is_no_description(tmp_path):
    path = _write_lib(tmp_path, (atomic_part("NO-DESC", drop=("Description",)),))
    _, before = _first_symbol(path)
    names_before = _property_names(before[0])

    _edit_first_symbol(path)

    _, symbols = _first_symbol(path)
    assert kicad_files.find_property(symbols[0].node, "Datasheet").value == EDITED_DATASHEET
    assert _property_names(symbols[0]) == names_before


def test_edit_first_symbol_adds_a_datasheet_when_it_has_neither(tmp_path):
    path = _write_lib(tmp_path, (atomic_part("BARE", drop=("Datasheet", "Description")),))

    _edit_first_symbol(path)

    _, symbols = _first_symbol(path)
    assert kicad_files.find_property(symbols[0].node, "Datasheet").value == EDITED_DATASHEET


def test_edit_first_symbol_keeps_crlf_line_endings_when_it_adds_a_datasheet(tmp_path):
    path = _write_lib(tmp_path, (atomic_part("BARE", drop=("Datasheet", "Description")),), eol="\r\n")

    _edit_first_symbol(path)

    data = path.read_bytes()
    assert b"\r\n" in data and not re.search(rb"(?<!\r)\n", data)
    _, symbols = _first_symbol(path)
    assert kicad_files.find_property(symbols[0].node, "Datasheet").value == EDITED_DATASHEET
