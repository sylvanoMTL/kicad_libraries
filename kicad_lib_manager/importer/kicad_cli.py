"""Run kicad-cli on staging copies for symbol normalisation and the load gate (D-01, D-03).

Stdlib only. No shell is used.
"""

import hashlib
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..kicad_files import LoadedFile, file_version, parse_bytes
from ..models import Issue, Severity

DEFAULT_TIMEOUT = 60.0
_CACHE_MAX = 32
_TEMP_PREFIX = "kicad_cli_"


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


@dataclass(frozen=True)
class SymbolUpgrade:
    text: str
    version: int | None
    changed: bool


_cache: OrderedDict[tuple, SymbolUpgrade] = OrderedDict()


def clear_cache() -> None:
    """Forget every memoised symbol upgrade."""
    _cache.clear()


def _cache_key(exe: Path, data: bytes, runner: Callable | None) -> tuple | None:
    """Key on the input, the binary (path, size, mtime) and the runner; None if unhashable."""
    try:
        stat = exe.stat()
        signature = (stat.st_size, stat.st_mtime_ns)
    except OSError:
        signature = None
    key = (hashlib.sha256(data).hexdigest(), str(exe), signature, runner)
    try:
        hash(key)
    except TypeError:
        return None
    return key


def _failed(run: CliRun) -> bool:
    return run.returncode != 0 or "Unable to load" in run.stdout or "Unable to load" in run.stderr


def _detail(run: CliRun) -> str:
    """Exit code plus the CLI's own message, which is on stderr only for real failures."""
    message = run.stderr.strip() or run.stdout.strip() or "no message"
    return f"exit {run.returncode}: {message}"


def _plain_name(name: str) -> bool:
    """True for a bare file stem: no separators, no drive, no dot-only names."""
    return bool(name) and name not in (".", "..") and not any(c in name for c in "/\\:\0")


def _gate_failed(text: str) -> Issue:
    return Issue(Severity.ERROR, "install.cli_gate_failed", text)


def upgrade_symbol_text(
    exe: Path,
    text: str,
    *,
    name: str | None = None,
    runner: Callable | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> SymbolUpgrade | Issue:
    """Normalise a symbol library to the installed KiCad's format (D-01); successes are memoised.

    name only labels the error message. The input and output live in a fresh temp folder.
    """
    data = text.encode("utf-8")
    key = _cache_key(exe, data, runner)
    if key is not None and key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    label = name or "the incoming symbol"
    try:
        tmp = Path(tempfile.mkdtemp(prefix=_TEMP_PREFIX))
    except OSError as e:
        return Issue(Severity.ERROR, "install.cli_failed", f"Could not create a temp folder: {e.strerror or e}")
    try:
        source = tmp / "in.kicad_sym"
        target = tmp / "out.kicad_sym"
        source.write_bytes(data)
        run = run_cli(
            exe,
            ["sym", "upgrade", "--force", "-o", str(target), str(source)],
            runner=runner,
            timeout=timeout,
        )
        if isinstance(run, Issue):
            return run
        if _failed(run):
            return _gate_failed(f"kicad-cli could not load {label} ({_detail(run)})")
        if target.is_file():
            parsed = parse_bytes(target.read_bytes(), "the kicad-cli output")
            if isinstance(parsed, Issue):
                return _gate_failed(f"kicad-cli wrote output for {label} that could not be read: {parsed.text}")
            result = SymbolUpgrade(parsed.source.text, file_version(parsed.root), True)
        else:
            # Exit 0 and no output file: KiCad judged the input already current
            original = parse_bytes(data, "the incoming symbol")
            version = file_version(original.root) if isinstance(original, LoadedFile) else None
            result = SymbolUpgrade(text, version, False)
    except OSError as e:
        return Issue(Severity.ERROR, "install.cli_failed", f"Could not stage {label} for kicad-cli: {e.strerror or e}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if key is not None:
        _cache[key] = result
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
    return result


def _check_symbol(
    exe: Path,
    folder: Path,
    library: str,
    data: bytes,
    runner: Callable | None,
    timeout: float,
) -> CliRun | Issue:
    """Run sym upgrade --force on one library copy inside folder; the output is never kept."""
    folder.mkdir()
    source = folder / f"{library}.kicad_sym"
    # Always a longer name than source, so the two paths can never be the same
    target = folder / f"{library}.upgraded.kicad_sym"
    source.write_bytes(data)
    return run_cli(
        exe,
        ["sym", "upgrade", "--force", "-o", str(target), str(source)],
        runner=runner,
        timeout=timeout,
    )


def load_gate(
    exe: Path,
    *,
    library: str,
    symbol_lib: bytes | None,
    footprints: Sequence[tuple[str, bytes]],
    original_symbol_lib: bytes | None = None,
    runner: Callable | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> list[Issue]:
    """Prove KiCad can load the would-be library and footprints, before anything is written (D-03).

    The merged symbol library is upgraded from a temp copy; the incoming footprints are
    upgraded from a staging folder holding only them. Every output is discarded: footprints
    are checked, never replaced (D-02). With original_symbol_lib, a symbol failure is
    re-checked on the unmerged library to say whether the merge or the target is to blame.
    """
    issues: list[Issue] = []
    if symbol_lib is not None and not _plain_name(library):
        issues.append(_gate_failed(f"Cannot check the library: {library!r} is not a plain file name"))
    for fp_name, _ in footprints:
        if not _plain_name(fp_name):
            issues.append(_gate_failed(f"Cannot check the footprint: {fp_name!r} is not a plain file name"))
    if issues or (symbol_lib is None and not footprints):
        return issues
    try:
        tmp = Path(tempfile.mkdtemp(prefix=_TEMP_PREFIX))
    except OSError as e:
        return [Issue(Severity.ERROR, "install.cli_failed", f"Could not create a temp folder: {e.strerror or e}")]
    try:
        if symbol_lib is not None:
            run = _check_symbol(exe, tmp / "merged", library, symbol_lib, runner, timeout)
            if isinstance(run, Issue):
                issues.append(run)
            elif _failed(run):
                text = f"kicad-cli could not load the merged symbol library {library}.kicad_sym ({_detail(run)})"
                if original_symbol_lib is not None:
                    blame = _check_symbol(exe, tmp / "original", library, original_symbol_lib, runner, timeout)
                    if isinstance(blame, CliRun):
                        if _failed(blame):
                            text += "; the target library already fails to load in KiCad before the merge"
                        else:
                            text += "; the target library loads on its own, so the merged part is the cause"
                issues.append(_gate_failed(text))
        if footprints:
            stage = tmp / "stage.pretty"
            stage.mkdir()
            for fp_name, fp_data in footprints:
                (stage / f"{fp_name}.kicad_mod").write_bytes(fp_data)
            run = run_cli(
                exe,
                ["fp", "upgrade", "--force", "-o", str(tmp / "out.pretty"), str(stage)],
                runner=runner,
                timeout=timeout,
            )
            if isinstance(run, Issue):
                issues.append(run)
            elif _failed(run):
                names = ", ".join(fp_name for fp_name, _ in footprints)
                issues.append(
                    _gate_failed(f"kicad-cli could not load the incoming footprint(s) {names} ({_detail(run)})")
                )
    except OSError as e:
        issues.append(Issue(Severity.ERROR, "install.cli_failed", f"Could not stage files for kicad-cli: {e.strerror or e}"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return issues
