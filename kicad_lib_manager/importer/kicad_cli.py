"""Run kicad-cli on staging copies for symbol normalisation and the load gate (D-01, D-03).

Stdlib only. No shell is used.
"""

import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..models import Issue, Severity

DEFAULT_TIMEOUT = 60.0


@dataclass(frozen=True)
class CliRun:
    returncode: int
    stdout: str
    stderr: str


def locate_kicad_cli(
    explicit: Path | None = None,
    kicad_fp_dir: Path | None = None,
    *,
    platform: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> Path | None:
    """Find kicad-cli: an explicit file, the install holding kicad_fp_dir, then PATH."""
    platform = sys.platform if platform is None else platform
    if explicit is not None and explicit.is_file():
        return explicit
    if kicad_fp_dir is not None:
        # <KiCad>/<ver>/share/kicad/footprints, so parents[2] is <KiCad>/<ver>
        parents = kicad_fp_dir.parents
        if len(parents) > 2:
            name = "kicad-cli.exe" if platform == "win32" else "kicad-cli"
            candidate = parents[2] / "bin" / name
            if candidate.is_file():
                return candidate
    found = which("kicad-cli")
    return Path(found) if found else None


def stock_symbols_dir(kicad_fp_dir: Path | None) -> Path | None:
    """KiCad's stock symbols folder, the sibling of its footprints folder, when it exists."""
    if kicad_fp_dir is None:
        return None
    symbols = kicad_fp_dir.parent / "symbols"
    return symbols if symbols.is_dir() else None


def run_cli(
    exe: Path,
    args: Sequence[str],
    *,
    runner: Callable | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> CliRun | Issue:
    """Run kicad-cli once; any exit code comes back as a CliRun, a timeout or OS error as an Issue."""
    run = runner or subprocess.run
    try:
        result = run(
            [str(exe), *args],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        return Issue(Severity.ERROR, "install.cli_failed", f"kicad-cli timed out after {timeout:g} s")
    except OSError as e:
        return Issue(Severity.ERROR, "install.cli_failed", f"Could not run kicad-cli: {e.strerror or e}")
    return CliRun(result.returncode, result.stdout or "", result.stderr or "")
