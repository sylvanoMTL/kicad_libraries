"""The single KiCad 10 gate every real-binary test goes through (TEST-02, D-05).

This is a plain helper module, not a test module: it has no ``test_`` prefix, so
pytest does not collect it. Test modules import it with ``from clifixtures import
...``, like ``zipfixtures``. Nothing here starts a process at import time.

Real kicad-cli output depends on the KiCad version (the symbol format number and the
generator version change between majors), so a real-binary test only runs against the
major version in KICAD_MAJOR. Any other binary, or none at all, skips with a stated
reason. The gate never guesses a version and never falls back to another install.
"""

import functools
import re
from collections.abc import Callable
from pathlib import Path

from kicad_lib_manager.importer import kicad_cli
from kicad_lib_manager.library_scanner import find_kicad_footprint_dir
from kicad_lib_manager.models import Issue

KICAD_MAJOR = 10
KICAD_SYMBOL_FORMAT = 20251024  # what kicad-cli 10 writes into a .kicad_sym header
KICAD_GENERATOR_VERSION = "10.0"
VERSION_TIMEOUT = 30.0

_VERSION_RE = re.compile(r"\s*(\d+)\.(\d+)")


def check_kicad_cli(exe: Path | None, *, runner: Callable | None = None) -> tuple[Path | None, str]:
    """Return (exe, "") when exe reports kicad-cli KICAD_MAJOR, else (None, the reason to skip)."""
    if exe is None:
        return None, f"kicad-cli not found (these tests need KiCad {KICAD_MAJOR})"
    result = kicad_cli.run_cli(exe, ["version"], runner=runner, timeout=VERSION_TIMEOUT)
    if isinstance(result, Issue):
        return None, f"could not run kicad-cli version at {exe}: {result.text}"
    if result.returncode != 0:
        detail = f"exit {result.returncode}"
        if result.stderr.strip():
            detail += f": {result.stderr.strip()}"
        return None, f"could not run kicad-cli version at {exe}: {detail}"
    match = _VERSION_RE.match(result.stdout)
    if match and int(match.group(1)) == KICAD_MAJOR:
        return exe, ""
    lines = result.stdout.strip().splitlines()
    found = lines[0].strip() if lines else "an unreadable version"
    return None, f"needs kicad-cli {KICAD_MAJOR}, found {found} at {exe}"


@functools.cache
def located_kicad_cli() -> tuple[Path | None, str]:
    """Locate kicad-cli as the app does (newest install first) and gate it; probed once per session."""
    exe = kicad_cli.locate_kicad_cli(kicad_fp_dir=find_kicad_footprint_dir())
    return check_kicad_cli(exe)
