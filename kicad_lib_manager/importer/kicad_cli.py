"""Run kicad-cli on staging copies for symbol normalisation and the load gate (D-01, D-03).

Stdlib only. No shell is used.
"""

import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kicad_files import file_version, parse_bytes
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
    raise NotImplementedError


def stock_symbols_dir(kicad_fp_dir: Path | None) -> Path | None:
    raise NotImplementedError


def run_cli(
    exe: Path,
    args: Sequence[str],
    *,
    runner: Callable | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> CliRun | Issue:
    raise NotImplementedError
