"""Detect running KiCad editors so a config write can warn about them (D-15).

Stdlib only. No shell is used and a failure to list processes is silent.
"""

import csv
import io
import os
import subprocess
import sys
from pathlib import Path

# Exact image names; kicad-cli is deliberately absent because it never rewrites the config
_KICAD_PROCESSES = frozenset(
    {"kicad", "eeschema", "pcbnew", "pl_editor", "gerbview", "pcb_calculator"}
)


def kicad_running(*, platform: str | None = None) -> list[str]:
    """Names of running KiCad processes; empty when none or when detection fails."""
    platform = sys.platform if platform is None else platform
    try:
        if platform == "win32":
            exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "tasklist.exe"
            result = subprocess.run(
                [str(exe), "/NH", "/FO", "CSV"],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            names = [row[0] for row in csv.reader(io.StringIO(result.stdout)) if row]
        else:
            result = subprocess.run(
                ["ps", "-A", "-o", "comm="],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=5,
            )
            names = [
                Path(line.strip()).name
                for line in result.stdout.splitlines()
                if line.strip()
            ]
    except (OSError, subprocess.SubprocessError):
        return []
    found = {
        n for n in (name.lower().removesuffix(".exe") for name in names)
        if n in _KICAD_PROCESSES
    }
    return sorted(found)
