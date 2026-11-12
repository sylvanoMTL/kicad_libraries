"""Qt-free text for the content view (Phase 5, D-08): a planned file as text, a unified diff or a binary summary.

Everything is bounded: texts and diffs are cut at MAX_LINES lines or MAX_BYTES bytes (T-05-19), an
existing file is read at most MAX_READ bytes, and a model or other binary file is never decoded, only
sized and hashed in chunks. Hashing a large STEP file is slow, so a caller runs these functions on a
worker thread, never on the GUI thread.
"""

import difflib
import hashlib
from dataclasses import dataclass
from pathlib import Path

from .plan import FileOp

MAX_LINES = 5000
MAX_BYTES = 512 * 1024
MAX_READ = 8 * 1024 * 1024
_CHUNK = 1024 * 1024
_UNCHANGED_TEXT = "This file is unchanged by the install."


@dataclass(frozen=True)
class ContentText:
    """What the content view shows. kind: text | diff | binary | unchanged | error."""

    title: str
    header: str
    body: str
    kind: str


# -- helpers ------------------------------------------------------------------------------------


def decode_text(data: bytes) -> str:
    """Planned or current file bytes as text: UTF-8, BOM stripped, undecodable bytes replaced."""
    return data.decode("utf-8-sig", errors="replace")


def cap_lines(lines: list[str]) -> list[str]:
    """Keep the lines that fit MAX_LINES lines and MAX_BYTES UTF-8 bytes; mark a cut with a closing line."""
    size = 0
    for kept, line in enumerate(lines):
        size += len(line.encode("utf-8")) + 1
        if kept >= MAX_LINES or size > MAX_BYTES:
            return [*lines[:kept], f"Diff truncated: showing the first {kept} of {len(lines)} lines."]
    return list(lines)


def diff_text(old: bytes, new: bytes, old_label: str, new_label: str) -> str:
    """Unified diff of two files with 3 lines of context, cut by cap_lines."""
    diff = difflib.unified_diff(
        decode_text(old).splitlines(), decode_text(new).splitlines(), old_label, new_label, lineterm="", n=3
    )
    return "\n".join(cap_lines(list(diff)))


def sha256_file(path: Path) -> tuple[int, str]:
    """Size and SHA-256 of a file, read in 1 MiB chunks; raises OSError for the caller."""
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        while chunk := handle.read(_CHUNK):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _kib(size: int) -> str:
    return f"{size / 1024:.1f} KiB"


def binary_text(name: str, size: int, sha: str, existing: tuple[int, str] | None = None) -> str:
    """Name, size and SHA-256 of a binary file; a modified one shows the existing file as well."""
    if existing is None:
        return f"{name}\nSize: {_kib(size)}\nSHA-256: {sha}"
    return (
        f"{name}\n\nExisting\nSize: {_kib(existing[0])}\nSHA-256: {existing[1]}"
        f"\n\nPlanned\nSize: {_kib(size)}\nSHA-256: {sha}"
    )


def _rel(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _read_capped(path: Path) -> bytes:
    with open(path, "rb") as handle:
        data = handle.read(MAX_READ + 1)
    if len(data) > MAX_READ:
        limit = f"{MAX_READ // _CHUNK} MiB" if MAX_READ >= _CHUNK else f"{MAX_READ} bytes"
        raise OSError(f"the file is larger than {limit}")
    return data


def _failure(title: str, rel: str, reason: str) -> ContentText:
    return ContentText(title=title, header=rel, body=f"Could not read {rel}: {reason}.", kind="error")


def _reason(error: OSError) -> str:
    return error.strerror or str(error)


# -- content builders -----------------------------------------------------------------------------


def unchanged_content(path: Path, repo_root: Path) -> ContentText:
    rel = _rel(path, repo_root)
    return ContentText(title=f"{rel} - unchanged", header=rel, body=_UNCHANGED_TEXT, kind="unchanged")


def op_content(op: FileOp, repo_root: Path, *, conflict: bool = False) -> ContentText:
    """The content view text of one planned write: new text, a diff against the current file, or a binary summary."""
    rel = _rel(op.path, repo_root)
    new = op.base_sha256 is None
    suffix = " - existing vs incoming" if conflict else (" - new file" if new else " - changes")
    title = f"{rel}{suffix}"
    current = op.listed_path or op.path
    if op.kind == "mkdir":
        return ContentText(title, rel, f"{rel}/ is a new folder created by the install.", "text")
    if op.kind == "model":
        if op.source is None:
            return _failure(title, rel, "the plan holds no source file for it")
        existing = None
        if not new:
            try:
                existing = sha256_file(current)
            except OSError as e:
                return _failure(title, rel, _reason(e))
        body = binary_text(op.path.name, op.source.size, op.source.sha256, existing)
        return ContentText(title, rel, body, "binary")
    if op.data is None:
        return _failure(title, rel, "the plan holds no text for it")
    if new:
        lines = decode_text(op.data).splitlines()
        return ContentText(title, rel, "\n".join(cap_lines(lines)), "text")
    try:
        old = _read_capped(current)
    except OSError as e:
        return _failure(title, rel, _reason(e))
    if old == op.data:
        return ContentText(f"{rel} - unchanged", rel, _UNCHANGED_TEXT, "unchanged")
    labels = ("existing", "incoming") if conflict else ("current", "planned")
    body = diff_text(old, op.data, f"{rel} ({labels[0]})", f"{rel} ({labels[1]})")
    return ContentText(title, rel, body, "diff")
