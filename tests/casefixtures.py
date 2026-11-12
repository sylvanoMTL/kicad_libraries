"""A real case-sensitive folder for the VER-02 tests (Phase 12, D-13).

Windows 11 can switch one NTFS folder to case-sensitive with ``fsutil file setCaseSensitiveInfo``
(no admin rights needed on a folder the user owns). Linux folders are case-sensitive already.
A case-insensitive macOS volume cannot be switched, so there the tests skip with a stated reason.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

_SKIP = "could not make a case-sensitive folder:"


def case_sensitive_dir(path: Path) -> Path:
    """Create path as a new, empty, case-sensitive folder and return it; skip the test when that is not possible.

    The case flag is set before any child exists (Windows refuses it on a folder that holds files).
    A probe file proves the result: the folder must not show CaseProbe under the name caseprobe.
    """
    path.mkdir(parents=True, exist_ok=False)
    if sys.platform == "win32":
        tool = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "fsutil.exe"
        try:
            done = subprocess.run(
                [str(tool), "file", "setCaseSensitiveInfo", str(path), "enable"],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError) as e:
            pytest.skip(f"{_SKIP} {type(e).__name__}: {e}")
        if done.returncode != 0:
            detail = (done.stdout + done.stderr).strip() or f"exit code {done.returncode}"
            pytest.skip(f"{_SKIP} fsutil failed: {detail}")
    probe = path / "CaseProbe"
    try:
        probe.write_bytes(b"")
        folded_visible = (path / "caseprobe").exists()
    except OSError as e:
        pytest.skip(f"{_SKIP} the probe file could not be written ({e})")
    finally:
        probe.unlink(missing_ok=True)
    if folded_visible:
        pytest.skip(f"{_SKIP} this folder ignores letter case")
    return path
