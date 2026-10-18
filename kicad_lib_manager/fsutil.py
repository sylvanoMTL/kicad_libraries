import os
import time
import uuid
from collections.abc import Callable
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
