import json
import os
import re
import sys
from pathlib import Path
from typing import Callable

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


def find_kicad_config_dir() -> Path | None:
    """Find the latest KiCad user config directory."""
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return None
        base = Path(appdata) / "kicad"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Preferences" / "kicad"
    else:
        base = Path.home() / ".config" / "kicad"

    if not base.is_dir():
        return None

    versions = sorted(
        (d for d in base.iterdir() if d.is_dir()),
        reverse=True,
    )
    return versions[0] if versions else None


def sync_kicad_path_vars(repo_root: Path) -> list[str]:
    """Set KICAD_LIB_GITHUB and CUSTOM_3DMODEL_DIR in kicad_common.json."""
    config_dir = find_kicad_config_dir()
    if not config_dir:
        return ["Could not find KiCad config directory"]

    config_file = config_dir / "kicad_common.json"
    if not config_file.exists():
        return [f"KiCad config not found: {config_file}"]

    try:
        config = json.loads(config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return [f"Failed to read KiCad config: {e}"]

    env = config.setdefault("environment", {})
    env_vars = env.setdefault("vars", {})

    repo_str = str(repo_root).replace("\\", "/")
    desired = {
        "KICAD_LIB_GITHUB": repo_str,
        "CUSTOM_3DMODEL_DIR": f"{repo_str}/Custom/3DModels",
    }

    messages = []
    changed = False
    for key, value in desired.items():
        old = env_vars.get(key)
        if old == value:
            messages.append(f"KiCad path '{key}' already set correctly")
        else:
            env_vars[key] = value
            changed = True
            if old is None:
                messages.append(f"KiCad path '{key}' set to: {value}")
            else:
                messages.append(f"KiCad path '{key}' updated: {old} -> {value}")

    if changed:
        try:
            config_file.write_text(
                json.dumps(config, indent=2) + "\n", encoding="utf-8"
            )
            messages.append(
                f"Updated {config_file} (restart KiCad to apply)"
            )
        except OSError as e:
            messages.append(f"Failed to write KiCad config: {e}")

    return messages


def find_kicad_footprint_dir() -> Path | None:
    """Auto-detect KiCad's default footprint library directory."""
    if sys.platform == "win32":
        base = Path("C:/Program Files/KiCad")
    elif sys.platform == "darwin":
        base = Path("/Applications/KiCad")
    else:
        base = Path("/usr/share/kicad")

    if not base.exists():
        return None

    # Find the latest version directory (e.g., 9.0, 8.0)
    if sys.platform == "win32":
        versions = sorted(
            (d for d in base.iterdir() if d.is_dir()),
            reverse=True,
        )
        for v in versions:
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
    issues = cross_reference(sym_libs, fp_libs, kicad_fp_dir)
    issues.extend(check_3d_model_paths(repo_root, progress))

    if progress:
        progress("Done", 100, 100)

    return ScanResult(
        symbol_libs=sym_libs,
        footprint_libs=fp_libs,
        issues=issues,
    )
