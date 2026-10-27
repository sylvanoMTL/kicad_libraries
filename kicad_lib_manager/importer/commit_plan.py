"""What the commit step will commit and say (Phase 6): the file list and the commit messages.

Pure: no git, no Qt. The plan is derived from the install that just happened (D-08, D-11a) and the
messages follow the D-18 layout, so the panel and the tests share one source of truth.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..models import Issue, Severity
from .plan import InstallPlan, InstallResult

NEW_PLACEHOLDER = "<new commit>"  # stands for the Custom commit that does not exist yet (RESEARCH Pattern 5)
# Controls (C0, DEL, C1) plus the Unicode line and paragraph separators, which str.splitlines treats as breaks
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f\N{LINE SEPARATOR}\N{PARAGRAPH SEPARATOR}]")


@dataclass(frozen=True)
class CommitFile:
    """One file of the commit: the install wrote exactly expected_sha256 into it (D-11)."""

    rel: str  # posix path relative to custom_dir: the string handed to git
    display: str  # posix path relative to repo_root, shown in the panel
    path: Path
    kind: str
    expected_sha256: str
    base_sha256: str | None  # the content before the install; None when the install created the file


@dataclass(frozen=True)
class CommitPlan:
    repo_root: Path
    custom_dir: Path
    custom_rel: str  # custom_dir relative to repo_root, posix ("Custom"): the parent pathspec (D-17)
    files: tuple[CommitFile, ...]
    library: str
    new_library: bool
    symbol: str
    footprint: str | None  # "{library}:{footprint}"
    model: str | None
    vendor: str  # display label
    package: str | None  # base name of the package, never its full path
    date: str  # YYYY-MM-DD
    overwrite: bool
    backup_dir: Path | None
    issues: tuple[Issue, ...]


def sanitize_line(text: str) -> str:
    """One line of plain text: control characters become spaces, runs of spaces collapse."""
    return re.sub(r" +", " ", _CONTROL_RE.sub(" ", text)).strip()


def _posix_relative(path: Path, base: Path) -> str | None:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return None


def _listed_name(folder: Path, name: str) -> str:
    """The spelling of `name` inside `folder` as the folder lists it: exact match, else case-insensitive, else `name`."""
    try:
        names = sorted(entry.name for entry in folder.iterdir())
    except OSError:
        return name
    if name in names:
        return name
    folded = name.casefold()
    return next((candidate for candidate in names if candidate.casefold() == folded), name)


def _disk_spelling(path: Path, custom_dir: Path) -> Path:
    """The path under its on-disk spelling (RESEARCH Pitfall 2).

    A case-insensitive volume keeps whatever case the file was first written with, and git matches
    a pathspec exactly, so every component below custom_dir is looked up in its folder.
    """
    try:
        parts = path.relative_to(custom_dir).parts
    except ValueError:
        return path.parent / _listed_name(path.parent, path.name)
    current = custom_dir
    for part in parts:
        current = current / _listed_name(current, part)
    return current


def build_commit_plan(
    result: InstallResult, plan: InstallPlan, *, vendor_label: str, today: date | None = None
) -> CommitPlan:
    """The files the install wrote (never folders) and the facts the messages need."""
    repo_root, custom_dir = Path(plan.layout.repo_root), Path(plan.layout.custom_dir)
    custom_rel = _posix_relative(custom_dir, repo_root) or custom_dir.name
    custom_real = custom_dir.resolve()
    ops = {op.path: op for op in plan.ops}
    files: list[CommitFile] = []
    issues: list[Issue] = []
    seen: set[Path] = set()
    seen_rel: set[str] = set()
    for path in result.touched:
        path = Path(path)
        if path in seen:
            continue
        seen.add(path)
        op = ops.get(path)
        if (op is not None and op.kind == "mkdir") or path.is_dir():
            continue
        shown = _posix_relative(path, repo_root) or path.as_posix()
        if op is None:
            issues.append(Issue(Severity.ERROR, "commit.unknown_file", f"{shown} was written but is not part of the install plan"))
            continue
        spelled = _disk_spelling(op.listed_path if op.listed_path is not None else path, custom_dir)
        resolved = spelled.resolve()
        if not resolved.is_relative_to(custom_real):
            issues.append(Issue(Severity.ERROR, "commit.outside_custom", f"{shown} is outside {custom_rel}; it is not committed"))
            continue
        if op.data is not None:
            expected = hashlib.sha256(op.data).hexdigest()
        elif op.source is not None:
            expected = op.source.sha256
        else:
            issues.append(Issue(Severity.ERROR, "commit.unknown_file", f"{shown} has no recorded content"))
            continue
        rel = _posix_relative(spelled, custom_dir) or resolved.relative_to(custom_real).as_posix()
        if rel in seen_rel:
            continue
        seen_rel.add(rel)
        display = _posix_relative(spelled, repo_root) or spelled.as_posix()
        files.append(CommitFile(rel, display, path, op.kind, expected, op.base_sha256))
    files.sort(key=lambda f: (f.display.casefold(), f.display))
    overwrite = any(
        c.kind == "symbol" and c.resolution is not None and c.resolution.action == "overwrite"
        for c in plan.conflicts
    )
    return CommitPlan(
        repo_root=repo_root,
        custom_dir=custom_dir,
        custom_rel=custom_rel,
        files=tuple(files),
        library=result.library,
        new_library=result.new_library,
        symbol=plan.symbol_name,
        footprint=plan.footprint_link,
        model=plan.model_file,
        vendor=vendor_label or "Unknown vendor",
        package=result.source.name if result.source is not None else None,
        date=(today or date.today()).isoformat(),
        overwrite=overwrite,
        backup_dir=result.backup_dir,
        issues=tuple(issues),
    )


def _sha256_of(path: Path) -> str | None:
    """Hex digest of a file read in 1 MiB chunks; None when it cannot be read."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def changed_since_install(cplan: CommitPlan) -> tuple[str, ...]:
    """Display paths, in plan order, of the planned files that are missing or no longer hold what the install wrote (D-11)."""
    return tuple(f.display for f in cplan.files if _sha256_of(f.path) != f.expected_sha256)


def pre_install_bytes(cfile: CommitFile, backup_dir: Path | None) -> bytes | None:
    """The bytes the file held before the install, from the Phase 4 backup copy whose hash is base_sha256 (D-09).

    Backups are named '{name}_backup_{N}'; same-named files of different folders share the
    folder, so a copy is accepted only when its content matches. None when there is no match.
    """
    if cfile.base_sha256 is None or backup_dir is None:
        return None
    pattern = re.compile(re.escape(cfile.path.name) + r"_backup_(\d+)$")
    try:
        candidates = [(int(m.group(1)), entry) for entry in backup_dir.iterdir() if (m := pattern.fullmatch(entry.name))]
    except OSError:
        return None
    for _, entry in sorted(candidates):
        try:
            data = entry.read_bytes()
        except OSError:
            continue
        if hashlib.sha256(data).hexdigest() == cfile.base_sha256:
            return data
    return None


def default_message(cplan: CommitPlan) -> str:
    """The Custom commit message of D-18: subject, what was installed, then the Import-* trailers."""
    symbol, library = sanitize_line(cplan.symbol), sanitize_line(cplan.library)
    footprint = sanitize_line(cplan.footprint or "")
    model = sanitize_line(cplan.model or "")
    package = sanitize_line(cplan.package or "")  # the base name only: never a path (T-06-18)
    if cplan.overwrite:
        subject = f"Update {symbol} in {library}"
    elif cplan.new_library:
        subject = f"Add {symbol} to new library {library}"
    else:
        subject = f"Add {symbol} to {library}"
    body = []
    if symbol:
        body.append(f"Symbol: {symbol}")
    if footprint:
        body.append(f"Footprint: {footprint}")
    if model:
        body.append(f"3D model: {model}")
    trailers = [f"Import-Vendor: {sanitize_line(cplan.vendor) or 'Unknown vendor'}"]
    if package:
        trailers.append(f"Import-Package: {package}")
    trailers.append(f"Import-Date: {sanitize_line(cplan.date)}")
    paragraphs = [subject, *(["\n".join(body)] if body else []), "\n".join(trailers)]
    return "\n\n".join(paragraphs)


def subject_of(message: str) -> str:
    """The first non-blank line of a message, stripped; "" for a blank message."""
    for line in message.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _short(sha: str | None) -> str:
    if not sha:
        return ""
    return sha if sha == NEW_PLACEHOLDER else sha[:7]


def parent_message(
    subject: str,
    custom_rel: str,
    old: str | None,
    new: str,
    commits,
    *,
    listed: bool = True,
) -> str:
    """The parent repo's message for the Custom bump (D-18): the subject, the range and the commits it covers."""
    lines = [f"Update {custom_rel}: {sanitize_line(subject)}", ""]
    lines.append(f"{custom_rel} {_short(old)}..{_short(new)}" if old else f"{custom_rel} {_short(new)}")
    if listed:
        lines.extend(f"- {short} {sanitize_line(text)}" for short, text in commits)
    else:
        lines.append(f"(the {custom_rel} commits since {_short(old)} could not be listed)")
    return "\n".join(lines)


def parent_preview(subject: str, custom_rel: str, old: str | None, earlier, *, listed: bool = True) -> str:
    """The D-19 preview: the parent message with a placeholder for the Custom commit that is not made yet."""
    commits = [*earlier, (NEW_PLACEHOLDER, subject)]
    return parent_message(subject, custom_rel, old, NEW_PLACEHOLDER, commits, listed=listed)
