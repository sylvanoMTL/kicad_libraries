import os
import re
import shutil
import sys
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from .models import Issue, Severity

_BOM = b"\xef\xbb\xbf"
# Sums to 1.0 s: D-05 asks for a retry window of about one second
_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.3, 0.35)


@dataclass(frozen=True)
class SourceText:
    text: str  # BOM removed, newlines untranslated
    bom: bool
    eol: str
    mixed_eol: bool
    issues: tuple[Issue, ...] = ()


def decode_source(data: bytes, name: str) -> SourceText | Issue:
    """Decode bytes as strict UTF-8, remembering the BOM and dominant line ending."""
    bom = data.startswith(_BOM)
    if bom:
        data = data[len(_BOM):]
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as e:
        return Issue(
            Severity.ERROR,
            "fs.bad_encoding",
            f"Could not read {name}: not valid UTF-8 (byte {e.start})",
        )

    crlf = text.count("\r\n")
    lf = text.count("\n") - crlf
    cr = text.count("\r") - crlf
    # Ties and files without line endings default to LF, KiCad's native output
    eol = "\r\n" if crlf > lf else "\n"
    mixed = (crlf > 0 and lf > 0) or cr > 0
    issues = ()
    if mixed:
        issues = (Issue(
            Severity.WARNING,
            "fs.mixed_eol",
            f"{name} has mixed line endings (CRLF and LF); they are kept as they are",
        ),)
    return SourceText(text, bom, eol, mixed, issues)


def read_source(path: Path) -> SourceText | Issue:
    """Read a KiCad file as bytes and decode it."""
    try:
        data = path.read_bytes()
    except OSError as e:
        return Issue(
            Severity.ERROR,
            "fs.read_failed",
            f"Could not read {path.name}: {e.strerror or e}",
        )
    return decode_source(data, path.name)


def encode_source(text: str, bom: bool) -> bytes:
    """Encode text as UTF-8, restoring the BOM when the source had one."""
    data = text.encode("utf-8")
    return _BOM + data if bom else data


def atomic_write_bytes(
    path: Path,
    data: bytes,
    *,
    retry_delays: tuple[float, ...] = _RETRY_DELAYS,
    sleep: Callable[[float], None] = time.sleep,
) -> Issue | None:
    """Replace path with data via a same-directory temp file; return an Issue on failure."""
    # A read-only target never becomes writable by waiting, so fail before any retry
    if path.exists() and not os.access(path, os.W_OK):
        return Issue(
            Severity.ERROR,
            "fs.read_only",
            f"Could not write {path.name}: file is read-only",
        )
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    created = False
    try:
        # Exclusive create; not an auto-deleting temp file, which cannot be renamed over a target on Windows
        with open(tmp, "xb") as f:
            created = True
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        # A PermissionError here is a lock held by another process (antivirus, KiCad); retry briefly
        for delay in retry_delays:
            try:
                os.replace(tmp, path)
                return None
            except PermissionError:
                sleep(delay)
        try:
            os.replace(tmp, path)
            return None
        except PermissionError:
            return Issue(
                Severity.ERROR,
                "fs.locked",
                f"Could not write {path.name}: file is in use",
            )
    except OSError as e:
        return Issue(
            Severity.ERROR,
            "fs.write_failed",
            f"Could not write {path.name}: {e.strerror or e}",
        )
    finally:
        if created:
            try:
                tmp.unlink()
            except OSError:
                pass  # already replaced, or unremovable


def atomic_write_text(
    path: Path,
    text: str,
    *,
    bom: bool = False,
    retry_delays: tuple[float, ...] = _RETRY_DELAYS,
    sleep: Callable[[float], None] = time.sleep,
) -> Issue | None:
    """Encode text with encode_source and write it atomically."""
    return atomic_write_bytes(
        path, encode_source(text, bom), retry_delays=retry_delays, sleep=sleep
    )


def backup_file(path: Path, backup_dir: Path) -> Path | Issue:
    """Copy path to backup_dir as <name>_backup_<N>, the scheme the Restore dialog lists."""
    pattern = re.compile(re.escape(path.name) + r"_backup_(\d+)$")
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        max_num = 0
        for name in os.listdir(backup_dir):
            m = pattern.match(name)
            if m:
                max_num = max(max_num, int(m.group(1)))
        number = max_num + 1
        with open(path, "rb") as src:
            while True:
                # Exclusive create so a concurrent backup never overwrites another one
                try:
                    dst_file = open(backup_dir / f"{path.name}_backup_{number}", "xb")
                except FileExistsError:
                    number += 1
                    continue
                break
            backup_path = backup_dir / f"{path.name}_backup_{number}"
            try:
                with dst_file:
                    shutil.copyfileobj(src, dst_file)
            except OSError:
                # Never leave a truncated backup that the Restore dialog would offer
                backup_path.unlink(missing_ok=True)
                raise
        shutil.copystat(path, backup_path)
        return backup_path
    except OSError as e:
        return Issue(
            Severity.ERROR,
            "fs.backup_failed",
            f"Could not back up {path.name}: {e.strerror or e}",
        )


def default_backup_dir(
    *,
    platform: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Per-user backup folder outside the repo; never created here and never imports Qt."""
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    if platform == "win32":
        base = Path(environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "KiCadExtLibManager" / "backups"


def normalize_eol(text: str, eol: str) -> str:
    """Convert every line ending in text to eol (the target file's dominant style)."""
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", eol)
