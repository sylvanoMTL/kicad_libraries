import copy
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Callable

from . import fsutil
from .kicad_process import kicad_running
from .models import (
    FootprintLibrary,
    FootprintRef,
    Issue,
    ScanResult,
    Severity,
    SymbolLibrary,
)

FOOTPRINT_RE = re.compile(r'\(property\s+"Footprint"\s+"([^"]*)"')
MODEL_RE = re.compile(r'\(model\s+"([^"]*)"')

# downloaded_examples holds vendor packages kept for the importer; never a library source
SKIP_DIRS = {
    "env", "venv", ".venv", ".git", ".claude", "__pycache__", "tests",
    "downloaded_examples",
}


_VERSION_RE = re.compile(r"[0-9]+(?:\.[0-9]+)*")


def parse_version(name: str) -> tuple[int, ...] | None:
    """Parse a dotted-integer folder name such as "10.0"; anything else gives None."""
    if not _VERSION_RE.fullmatch(name):
        return None
    return tuple(int(part) for part in name.split("."))


def newest_version_dirs(parent: Path) -> list[Path]:
    """Version-named subfolders of parent, newest first by numeric order."""
    try:
        found = [
            (version, d.name, d)
            for d in parent.iterdir()
            if (version := parse_version(d.name)) is not None and d.is_dir()
        ]
    except OSError:
        return []
    found.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [d for _, _, d in found]


def find_kicad_config_dir(base: Path | None = None) -> Path | None:
    """Find the newest KiCad user config directory (numeric version order)."""
    if base is None:
        if sys.platform == "win32":
            appdata = os.environ.get("APPDATA")
            if not appdata:
                return None
            base = Path(appdata) / "kicad"
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Preferences" / "kicad"
        else:
            base = Path.home() / ".config" / "kicad"

    versions = newest_version_dirs(base)
    return versions[0] if versions else None


_KICAD_COMMON_BACKUPS_KEPT = 10


def _only_vars_changed(before: dict, after: dict, desired: dict[str, str]) -> bool:
    """True when after equals before with just the desired variables set in environment.vars."""
    expected = copy.deepcopy(before)
    env = expected.setdefault("environment", {})
    env["vars"] = {**(env.get("vars") or {}), **desired}
    return after == expected


def _prune_backups(backup_dir: Path, name: str, keep: int) -> list[Issue]:
    """Delete all but the newest `keep` numbered backups of name; failures only warn."""
    pattern = re.compile(re.escape(name) + r"_backup_(\d+)$")
    try:
        numbered = [
            (int(m.group(1)), backup_dir / entry)
            for entry in os.listdir(backup_dir)
            if (m := pattern.match(entry))
        ]
    except OSError:
        return []
    numbered.sort(key=lambda item: item[0], reverse=True)
    issues = []
    for _, path in numbered[keep:]:
        try:
            try:
                path.unlink()
            except PermissionError:
                # A read-only old backup (Windows) cannot be deleted until the bit is cleared
                os.chmod(path, stat.S_IREAD | stat.S_IWRITE)
                path.unlink()
        except OSError as e:
            issues.append(Issue(
                Severity.WARNING,
                "config.prune_failed",
                f"Could not remove old backup {path.name}: {e.strerror or e}",
            ))
    return issues


def sync_kicad_path_vars(
    repo_root: Path,
    *,
    config_base: Path | None = None,
    backup_root: Path | None = None,
    running: Callable[[], list[str]] | None = None,
) -> list[Issue]:
    """Set KICAD_LIB_GITHUB and CUSTOM_3DMODEL_DIR in the newest kicad_common.json.

    The file is backed up first, re-parsed to prove only environment.vars changed,
    then replaced atomically. Older KiCad versions are never touched.
    """
    config_dir = find_kicad_config_dir(config_base)
    if not config_dir:
        return [Issue(
            Severity.WARNING,
            "config.dir_not_found",
            "Could not find KiCad config directory; path variables were not set",
        )]

    config_file = config_dir / "kicad_common.json"
    if not config_file.exists():
        return [Issue(
            Severity.WARNING,
            "config.not_found",
            f"KiCad config not found: {config_file} "
            f"(start and close KiCad {config_dir.name} once, then Generate again)",
        )]

    src = fsutil.read_source(config_file)
    if isinstance(src, Issue):
        return [src]
    try:
        config = json.loads(src.text)
    except json.JSONDecodeError as e:
        return [Issue(
            Severity.ERROR,
            "config.bad_json",
            f"Could not read {config_file.name}: invalid JSON at line {e.lineno}, "
            f"col {e.colno}; nothing was written",
        )]

    # KiCad 7 and 8 write "vars": null, so None counts as an empty object
    bad_shape = not isinstance(config, dict)
    env = {} if bad_shape else config.get("environment", {})
    bad_shape = bad_shape or not isinstance(env, dict)
    old_vars = {} if bad_shape else env.get("vars")
    if old_vars is None:
        old_vars = {}
    bad_shape = bad_shape or not isinstance(old_vars, dict)
    if bad_shape:
        return [Issue(
            Severity.ERROR,
            "config.bad_shape",
            f"{config_file.name} has an unexpected structure "
            f"(environment.vars is not an object); nothing was written",
        )]

    repo_str = str(repo_root).replace("\\", "/")
    desired = {
        "KICAD_LIB_GITHUB": repo_str,
        "CUSTOM_3DMODEL_DIR": f"{repo_str}/Custom/3DModels",
    }

    issues: list[Issue] = []
    set_issues: list[Issue] = []
    for key, value in desired.items():
        old = old_vars.get(key)
        if old == value:
            issues.append(Issue(
                Severity.INFO, "config.var_ok", f"KiCad path '{key}' already set correctly"
            ))
        elif old is None:
            set_issues.append(Issue(
                Severity.SUCCESS, "config.var_set", f"KiCad path '{key}' set to: {value}"
            ))
        else:
            set_issues.append(Issue(
                Severity.SUCCESS,
                "config.var_set",
                f"KiCad path '{key}' updated: {old} -> {value}",
            ))
    if not set_issues:
        return issues

    new_config = copy.deepcopy(config)
    new_config.setdefault("environment", {})["vars"] = {**old_vars, **desired}
    new_text = json.dumps(new_config, indent=2, ensure_ascii=False) + "\n"
    if not _only_vars_changed(config, json.loads(new_text), desired):
        return issues + [Issue(
            Severity.ERROR,
            "config.verify_failed",
            f"Did not write {config_file.name}: the new content would change "
            f"more than environment.vars",
        )]
    new_text = fsutil.normalize_eol(new_text, src.eol)

    names = (running or kicad_running)()
    if names:
        issues.append(Issue(
            Severity.WARNING,
            "config.kicad_running",
            f"KiCad appears to be running ({', '.join(names)}); it may overwrite these "
            f"path variables when it exits. Close KiCad and press Generate again.",
        ))

    backup_dir = (backup_root or fsutil.default_backup_dir()) / "kicad_common" / config_dir.name
    backup = fsutil.backup_file(config_file, backup_dir)
    if isinstance(backup, Issue):
        return issues + [backup]
    issues.append(Issue(
        Severity.INFO, "config.backed_up", f"Backed up {config_file.name} to {backup}"
    ))

    failure = fsutil.atomic_write_text(config_file, new_text, bom=src.bom)
    if failure is not None:
        return issues + [failure]

    issues.extend(set_issues)
    issues.append(Issue(
        Severity.SUCCESS, "config.written", f"Updated {config_file} (restart KiCad to apply)"
    ))
    issues.extend(_prune_backups(
        backup_dir, config_file.name, keep=_KICAD_COMMON_BACKUPS_KEPT
    ))
    return issues


def find_kicad_footprint_dir(base: Path | None = None, *,
                             platform: str | None = None) -> Path | None:
    """Auto-detect KiCad's default footprint library directory."""
    platform = sys.platform if platform is None else platform
    if base is None:
        if platform == "win32":
            base = Path("C:/Program Files/KiCad")
        elif platform == "darwin":
            base = Path("/Applications/KiCad")
        else:
            base = Path("/usr/share/kicad")

    if not base.exists():
        return None

    # Newest version first (e.g., 10.0 before 9.0)
    if platform == "win32":
        for v in newest_version_dirs(base):
            fp_dir = v / "share" / "kicad" / "footprints"
            if fp_dir.is_dir():
                return fp_dir
    else:
        fp_dir = base / "footprints"
        if fp_dir.is_dir():
            return fp_dir

    return None


def get_kicad_default_fp_nicknames(kicad_fp_dir: Path | None = None) -> set[str]:
    """Return the set of footprint library nicknames from KiCad's default install."""
    fp_dir = kicad_fp_dir or find_kicad_footprint_dir()
    if not fp_dir or not fp_dir.is_dir():
        return set()
    return {
        d.stem for d in fp_dir.iterdir()
        if d.is_dir() and d.suffix == ".pretty"
    }


def _determine_source(rel_path: str) -> str:
    parts = rel_path.split("/")
    if parts:
        return parts[0]
    return "Unknown"


def _in_skip_dir(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).parts
    return rel[0] in SKIP_DIRS if rel else False


def _collect_files(root: Path, pattern: str) -> list[Path]:
    return sorted(
        f for f in root.rglob(pattern)
        if not _in_skip_dir(f, root)
    )


def find_symbol_libs(root: Path, progress: Callable | None = None) -> list[SymbolLibrary]:
    sym_files = _collect_files(root, "*.kicad_sym")
    libs = []
    for i, f in enumerate(sym_files):
        if progress:
            progress(f"Parsing symbol: {f.stem}", i, len(sym_files))
        rel = f.relative_to(root).as_posix()
        source = _determine_source(rel)
        fp_refs = _parse_footprint_refs(f)
        libs.append(SymbolLibrary(
            nickname=f.stem,
            rel_path=rel,
            source=source,
            footprint_refs=fp_refs,
        ))
    return libs


def find_footprint_libs(root: Path, progress: Callable | None = None) -> list[FootprintLibrary]:
    pretty_dirs = sorted(
        d for d in root.rglob("*.pretty")
        if d.is_dir() and not _in_skip_dir(d, root)
    )
    libs = []
    for i, d in enumerate(pretty_dirs):
        if progress:
            progress(f"Scanning footprint: {d.stem}", i, len(pretty_dirs))
        rel = d.relative_to(root).as_posix()
        source = _determine_source(rel)
        libs.append(FootprintLibrary(
            nickname=d.stem,
            rel_path=rel,
            source=source,
        ))
    return libs


def _parse_footprint_refs(sym_file: Path) -> list[FootprintRef]:
    refs = []
    seen = set()
    try:
        text = sym_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return refs

    for match in FOOTPRINT_RE.finditer(text):
        value = match.group(1).strip()
        if not value or ":" not in value:
            continue
        lib_name, fp_name = value.split(":", 1)
        key = (lib_name, fp_name)
        if key not in seen:
            seen.add(key)
            refs.append(FootprintRef(library_name=lib_name, footprint_name=fp_name))
    return refs


def _collide(libs: list, kind: str) -> list[Issue]:
    """Fill collision_peers for one library kind and return one Issue per shared nickname."""
    for lib in libs:
        lib.collision_peers = []
    groups: dict[str, list] = {}
    for lib in libs:
        groups.setdefault(lib.nickname, []).append(lib)

    issues = []
    for nickname, group in groups.items():
        if len(group) < 2:
            continue
        rel_paths = sorted(lib.rel_path for lib in group)
        for lib in group:
            lib.collision_peers = [p for p in rel_paths if p != lib.rel_path]
        issues.append(Issue(
            Severity.WARNING,
            "scan.nickname_collision",
            f"[{nickname}] {kind} library nickname is used by "
            f"{', '.join(rel_paths)}; only one of them can be selected",
        ))
    return issues


def find_nickname_collisions(sym_libs: list[SymbolLibrary],
                             fp_libs: list[FootprintLibrary]) -> list[Issue]:
    """Report nicknames shared within symbols or within footprints and record peers.

    Symbols and footprints are checked separately. Nicknames are never changed.
    """
    return _collide(sym_libs, "Symbol") + _collide(fp_libs, "Footprint")


def cross_reference(sym_libs: list[SymbolLibrary],
                    fp_libs: list[FootprintLibrary],
                    kicad_fp_dir: Path | None = None) -> list[Issue]:
    fp_nicknames = {lib.nickname for lib in fp_libs}
    kicad_defaults = get_kicad_default_fp_nicknames(kicad_fp_dir)
    issues = []

    for sym in sym_libs:
        for ref in sym.footprint_refs:
            if ref.library_name in fp_nicknames:
                ref.found_in_repo = True
            elif ref.library_name in kicad_defaults:
                ref.found_in_repo = True  # Available in KiCad's default libraries
            else:
                ref.found_in_repo = False
                issues.append(Issue(
                    Severity.WARNING,
                    "scan.footprint_lib_missing",
                    f"[{sym.nickname}] Footprint library '{ref.library_name}' "
                    f"not found in repo or KiCad defaults "
                    f"(referenced by {ref.footprint_name})",
                ))
    return issues


def check_3d_model_paths(root: Path, progress: Callable | None = None) -> list[Issue]:
    mod_files = _collect_files(root, "*.kicad_mod")
    issues = []
    for i, mod_file in enumerate(mod_files):
        if progress:
            progress(f"Checking 3D paths: {mod_file.stem}", i, len(mod_files))
        try:
            text = mod_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        rel = mod_file.relative_to(root).as_posix()
        for match in MODEL_RE.finditer(text):
            path = match.group(1)
            if path.startswith("${"):
                continue
            if "/" in path or "\\" in path:
                issues.append(Issue(
                    Severity.WARNING,
                    "scan.model_absolute",
                    f"[{rel}] Absolute/non-variable 3D model path: {path}",
                ))
    return issues


def scan_all(repo_root: Path, progress: Callable | None = None,
             kicad_fp_dir: Path | None = None) -> ScanResult:
    if progress:
        progress("Discovering files...", 0, 100)

    fp_libs = find_footprint_libs(repo_root, progress)
    sym_libs = find_symbol_libs(repo_root, progress)

    if progress:
        progress("Cross-referencing...", 95, 100)
    issues = find_nickname_collisions(sym_libs, fp_libs)
    issues.extend(cross_reference(sym_libs, fp_libs, kicad_fp_dir))
    issues.extend(check_3d_model_paths(repo_root, progress))

    if progress:
        progress("Done", 100, 100)

    return ScanResult(
        symbol_libs=sym_libs,
        footprint_libs=fp_libs,
        issues=issues,
    )
