"""Scripted stand-in for subprocess.run that behaves like kicad-cli (plan 04-03).

This is a plain helper module, not a test module: it has no ``test_`` prefix, so pytest
does not collect it. Tests import it with ``from fakecli import FakeCli``. It touches
only the paths the caller passes in ``-o`` and never starts a process.

``modes`` maps a subcommand pair ("sym upgrade", "fp upgrade") to a mode name, or to a
list of mode names consumed one per call (the last one repeats). Modes follow the spike
results in 04-RESEARCH.md: upgrade, not_updated, reject, missing, conflict, timeout,
oserror. A pair that is not in ``modes`` upgrades.

``on_call`` is an optional hook called with the argv list (as strings) on every call, right after
the call is recorded and before the inputs are captured. It lets a test change the tree while the
gate runs (another process editing a file during the install).
"""

import re
import subprocess
from collections.abc import Callable
from pathlib import Path

_VERSION_RE = re.compile(rb"\(version \d+\)")

# mode -> (exit code, stdout, stderr)
_RESULTS = {
    "upgrade": (0, "Saving symbol library in updated format", ""),
    "not_updated": (0, "Symbol library was not updated", ""),
    "reject": (2, "", "Unable to load library"),
    "missing": (3, "", "Symbol library does not exist or is not accessible"),
    "conflict": (4, "", "Output path must not conflict with existing path"),
}


class FakeCli:
    def __init__(
        self,
        modes: dict[str, str | list[str]] | None = None,
        output_version: int = 20241209,
        on_call: Callable[[list[str]], None] | None = None,
    ):
        self.modes = dict(modes or {})
        self.output_version = output_version
        self.on_call = on_call
        self.calls: list[list[str]] = []
        self.kwargs: list[dict] = []
        # File name -> bytes of every input, captured at call time (callers delete their temp folder)
        self.inputs: list[dict[str, bytes]] = []
        self._used: dict[str, int] = {}

    def _mode_for(self, key: str) -> str:
        mode = self.modes.get(key, "upgrade")
        if isinstance(mode, str):
            return mode
        index = self._used.get(key, 0)
        self._used[key] = index + 1
        return mode[min(index, len(mode) - 1)]

    def _bump(self, data: bytes) -> bytes:
        return _VERSION_RE.sub(f"(version {self.output_version})".encode(), data, count=1)

    def __call__(self, argv, **kwargs):
        argv = [str(a) for a in argv]
        self.calls.append(argv)
        self.kwargs.append(kwargs)
        if self.on_call is not None:
            self.on_call(argv)
        args = argv[1:]
        key = " ".join(args[:2])
        source = Path(args[-1])
        if source.is_dir():
            self.inputs.append({p.name: p.read_bytes() for p in sorted(source.iterdir()) if p.is_file()})
        elif source.is_file():
            self.inputs.append({source.name: source.read_bytes()})
        else:
            self.inputs.append({})
        mode = self._mode_for(key)
        if mode == "timeout":
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        if mode == "oserror":
            raise FileNotFoundError(2, "No such file")
        code, stdout, stderr = _RESULTS[mode]
        if mode == "upgrade":
            target = Path(args[args.index("-o") + 1])
            if target.exists():
                code, stdout, stderr = _RESULTS["conflict"]
            elif source.is_dir():
                target.mkdir()
                for item in sorted(source.iterdir()):
                    if item.is_file():
                        (target / item.name).write_bytes(self._bump(item.read_bytes()))
            else:
                target.write_bytes(self._bump(source.read_bytes()))
        return subprocess.CompletedProcess(argv, code, stdout, stderr)

