"""The only module that starts a git process (Phase 6, GIT-05).

Every git call goes through run_git: a fixed argv shape, no shell, no inherited GIT_* variable except the author and committer identity
and a subcommand allow-list that holds nothing which talks to another repository.
Hooks always run and --no-verify is never passed (D-06). Decisions use exit codes and plumbing
output, never stderr text. Qt-free; imports only models.
"""

import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .models import Issue, Severity

ALLOWED_SUBCOMMANDS = frozenset({
    "--version", "rev-parse", "symbolic-ref", "status", "merge-base", "rev-list", "log", "ls-tree",
    "cat-file", "var", "add", "reset", "switch", "commit", "ls-files", "diff-tree", "check-ignore",
})
DEFAULT_TIMEOUT = 30.0
COMMIT_TIMEOUT = 300.0  # hooks can be slow
MIN_GIT_VERSION = (2, 25)  # --pathspec-from-file; assumed to appear in 2.25 (RESEARCH A4), so older git is refused
# (marker under the git directory, label) in the order they are checked; --git-path finds each one in a linked worktree
_BUSY_MARKERS = (
    ("MERGE_HEAD", "a merge"),
    ("rebase-merge", "a rebase"),
    ("rebase-apply", "a rebase"),
    ("CHERRY_PICK_HEAD", "a cherry-pick"),
    ("REVERT_HEAD", "a revert"),
    ("BISECT_LOG", "a bisect"),
)
_VERSION_RE = re.compile(r"git version (\d+(?:\.\d+)*)")
# the only GIT_* variables handed on from the user's session: the ones git-commit documents as its identity inputs
_IDENTITY_VARS = (
    "GIT_AUTHOR_NAME",
    "GIT_AUTHOR_EMAIL",
    "GIT_AUTHOR_DATE",
    "GIT_COMMITTER_NAME",
    "GIT_COMMITTER_EMAIL",
    "GIT_COMMITTER_DATE",
)


@dataclass(frozen=True)
class GitContext:
    """The git executable to run and, for tests, a stand-in for subprocess.run."""

    exe: Path
    runner: Callable | None = None


@dataclass(frozen=True)
class GitRun:
    returncode: int
    stdout: str
    stderr: str
    raw: bytes = b""  # the undecoded stdout

    @property
    def output(self) -> str:
        """Stdout and stderr together; hook output arrives on stderr."""
        return "\n".join(part for part in (self.stdout.strip(), self.stderr.strip()) if part)


def find_git(repo_root: Path, *, which: Callable[[str], str | None] | None = None) -> Path | Issue:
    """Resolve git once; a git found inside the repository is refused, never run."""
    found = (which or shutil.which)("git")  # looked up per call, so a test can replace shutil.which
    if not found:
        return Issue(Severity.WARNING, "git.not_found", "git was not found on PATH")
    path = Path(found).resolve()
    root = Path(repo_root).resolve()
    if path == root or root in path.parents:
        return Issue(
            Severity.WARNING, "git.inside_repo", f"the git found on PATH is inside the repository ({path}); it is not run"
        )
    return path


def _env() -> dict[str, str]:
    """The app's environment: the author and committer identity is kept, every other GIT_* variable is stripped."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    # a stray GIT_DIR or GIT_INDEX_FILE would redirect every call, so only the identity comes back
    env.update({k.upper(): v for k, v in os.environ.items() if k.upper() in _IDENTITY_VARS})
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "GIT_EDITOR": "true", "LC_ALL": "C"})
    return env


def _text(data) -> str:
    if data is None:
        return ""
    return data.decode("utf-8", errors="replace") if isinstance(data, bytes) else str(data)


def run_git(
    ctx: GitContext,
    repo: Path,
    *args: str,
    stdin_data: bytes | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    literal: bool = True,
) -> GitRun | Issue:
    """Run one git command in repo; any exit code comes back as a GitRun, a timeout or OS error as an Issue.

    Pathspecs are literal unless literal is False; check-ignore rejects the literal magic, so it alone
    turns it off (it takes plain paths on stdin).
    Raises ValueError, before anything starts, for a subcommand outside ALLOWED_SUBCOMMANDS.
    """
    if not args or args[0] not in ALLOWED_SUBCOMMANDS:
        raise ValueError(f"git {args[0] if args else ''} is not allowed")
    pathspecs = "--literal-pathspecs" if literal else "--no-literal-pathspecs"
    argv = [str(ctx.exe), pathspecs, "-c", "core.quotepath=false", "-C", str(repo), *args]
    run = ctx.runner or subprocess.run
    options = {"input": stdin_data} if stdin_data is not None else {"stdin": subprocess.DEVNULL}
    try:
        done = run(
            argv,
            capture_output=True,
            env=_env(),
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            **options,
        )
    except subprocess.TimeoutExpired:
        return Issue(Severity.ERROR, "git.timeout", f"git {args[0]} did not finish within {timeout:g} s")
    except OSError as e:
        return Issue(Severity.ERROR, "git.not_run", f"Could not run git: {e.strerror or e}")
    raw = done.stdout if isinstance(done.stdout, bytes) else _text(done.stdout).encode("utf-8")
    return GitRun(done.returncode, _text(done.stdout), _text(done.stderr), raw)


# -- read-only primitives: each returns None (or an Issue) on failure and never raises ---------------


def _ok(run: GitRun | Issue) -> bool:
    return isinstance(run, GitRun) and run.returncode == 0


def git_version(ctx: GitContext) -> tuple[int, ...] | None:
    """The leading numbers of `git --version` ("git version 2.49.0.windows.1" gives (2, 49, 0)); None when unreadable."""
    run = run_git(ctx, Path("."), "--version")
    found = _VERSION_RE.search(run.stdout) if _ok(run) else None
    return tuple(int(part) for part in found.group(1).split(".")) if found else None


def busy_operation(ctx: GitContext, repo: Path) -> str | None:
    """"a merge", "a rebase", "a cherry-pick", "a revert" or "a bisect" when one is in progress in repo, else None.

    Each marker's place comes from `rev-parse --git-path`, so it is found when the git directory
    is private to a linked worktree (.git/worktrees/<wt>/modules/Custom) and not under repo/.git.
    """
    for marker, label in _BUSY_MARKERS:
        run = run_git(ctx, repo, "rev-parse", "--git-path", marker)
        if not _ok(run) or not run.stdout.strip():
            continue
        path = Path(run.stdout.strip())
        if (path if path.is_absolute() else Path(repo) / path).exists():
            return label
    return None


def identity_known(ctx: GitContext, repo: Path) -> bool:
    """True when git knows both the author and the committer (from config or the GIT_AUTHOR_*/GIT_COMMITTER_* variables)."""
    return _ok(run_git(ctx, repo, "var", "GIT_AUTHOR_IDENT")) and _ok(run_git(ctx, repo, "var", "GIT_COMMITTER_IDENT"))


def show_toplevel(ctx: GitContext, path: Path) -> Path | None:
    run = run_git(ctx, path, "rev-parse", "--show-toplevel")
    return Path(run.stdout.strip()) if _ok(run) and run.stdout.strip() else None


def current_branch(ctx: GitContext, repo: Path) -> str | None:
    """The checked-out branch name; None for a detached HEAD (symbolic-ref exits 1)."""
    run = run_git(ctx, repo, "symbolic-ref", "-q", "--short", "HEAD")
    return run.stdout.strip() or None if _ok(run) else None


def head_commit(ctx: GitContext, repo: Path) -> str | None:
    run = run_git(ctx, repo, "rev-parse", "-q", "--verify", "HEAD")
    return run.stdout.strip() or None if _ok(run) else None


def short_hash(ctx: GitContext, repo: Path, rev: str = "HEAD") -> str | None:
    run = run_git(ctx, repo, "rev-parse", "--short", rev)
    return run.stdout.strip() or None if _ok(run) else None


def has_ref(ctx: GitContext, repo: Path, ref: str) -> bool:
    """True when ref names a commit; the exit code decides."""
    return _ok(run_git(ctx, repo, "rev-parse", "-q", "--verify", f"{ref}^{{commit}}"))


def main_ref(ctx: GitContext, repo: Path) -> str | None:
    """The ref that stands for main: the local branch when it exists, else origin/main, else None."""
    for ref in ("refs/heads/main", "refs/remotes/origin/main"):
        if has_ref(ctx, repo, ref):
            return ref
    return None


def is_ancestor(ctx: GitContext, repo: Path, ancestor: str, descendant: str) -> bool | None:
    """Whether ancestor is reachable from descendant (merge-base exits 0 or 1); None when git cannot tell."""
    run = run_git(ctx, repo, "merge-base", "--is-ancestor", ancestor, descendant)
    if isinstance(run, Issue) or run.returncode not in (0, 1):
        return None
    return run.returncode == 0


def count_commits(ctx: GitContext, repo: Path, revs: str) -> int | None:
    """How many commits `revs` selects (for example "HEAD..main"); None when git cannot count them."""
    run = run_git(ctx, repo, "rev-list", "--count", revs)
    try:
        return int(run.stdout.strip()) if _ok(run) else None
    except ValueError:
        return None


def committed_gitlink(ctx: GitContext, parent: Path, rel: str) -> str | None:
    """The commit the parent's HEAD records for the submodule at rel; None when HEAD has no such entry."""
    run = run_git(ctx, parent, "ls-tree", "-z", "HEAD", "--", rel)
    if not _ok(run):
        return None
    meta = run.stdout.split("\0", 1)[0].partition("\t")[0].split()
    return meta[2] if len(meta) == 3 and meta[1] == "commit" else None


def tracked_paths(ctx: GitContext, repo: Path, rels) -> set[str] | Issue:
    """Which of rels git already tracks."""
    rels = list(rels)
    if not rels:
        return set()
    run = run_git(ctx, repo, "ls-files", "-z", "--", *rels)
    if isinstance(run, Issue):
        return run
    if run.returncode != 0:
        return Issue(Severity.ERROR, "git.failed", f"git ls-files failed (git exit {run.returncode})\n{run.output}")
    return {name for name in run.stdout.split("\0") if name}


def ignored_paths(ctx: GitContext, repo: Path, rels) -> list[str] | Issue:
    """Which of rels (untracked paths) the repo's ignore rules cover; check-ignore exits 0 when some match, 1 when none."""
    rels = list(rels)
    if not rels:
        return []
    # --no-index: rels are untracked, and without it git glob-matches each name against the index first
    run = run_git(ctx, repo, "check-ignore", "--no-index", "-z", "--stdin", stdin_data=_nul_paths(rels), literal=False)
    if isinstance(run, Issue):
        return run
    if run.returncode == 1:
        return []
    if run.returncode != 0:
        return Issue(Severity.ERROR, "git.failed", f"git check-ignore failed (git exit {run.returncode})\n{run.output}")
    return [name for name in run.stdout.split("\0") if name]


def head_blob(ctx: GitContext, repo: Path, rel: str) -> bytes | None:
    """What HEAD holds for rel, as the work tree would have it (`cat-file --filters`); None when HEAD lacks the path.

    The smudge filter is applied, so a clean file under core.autocrlf=true hashes the same as its CRLF
    work-tree copy, which the raw blob would not.
    """
    run = run_git(ctx, repo, "cat-file", "--filters", f"HEAD:{rel}")
    return run.raw if _ok(run) else None


def commit_files(ctx: GitContext, repo: Path, rev: str = "HEAD") -> list[str] | None:
    """The paths a commit changed (`diff-tree --root`, NUL-separated and unquoted); None when git cannot list them."""
    run = run_git(ctx, repo, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-z", rev)
    if not _ok(run):
        return None
    return [name for name in run.raw.decode("utf-8", errors="replace").split("\0") if name]


def status_entries(ctx: GitContext, repo: Path) -> list[str] | Issue:
    """The path of every changed or untracked file (`status --porcelain=v1 -z -uall`), each counted once.

    A rename or copy entry is followed by its source path in the next NUL field; it is skipped, so the
    entry counts once under its new path.
    """
    run = run_git(ctx, repo, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if isinstance(run, Issue):
        return run
    if run.returncode != 0:
        return Issue(Severity.ERROR, "git.failed", f"git status failed (git exit {run.returncode})\n{run.output}")
    fields = run.stdout.split("\0")
    paths, index = [], 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if len(entry) < 4:  # the empty field after the last NUL
            continue
        if entry[0] in "RC" or entry[1] in "RC":
            index += 1
        paths.append(entry[3:])
    return paths


def log_range(ctx: GitContext, repo: Path, old: str, new: str) -> list[tuple[str, str]] | None:
    """(short hash, subject) of the commits in old..new, oldest first; None when git cannot list them."""
    run = run_git(ctx, repo, "log", "--reverse", "--format=%h%x09%s", f"{old}..{new}")
    if not _ok(run):
        return None
    pairs = []
    for line in run.stdout.splitlines():
        short, _, subject = line.partition("\t")
        if short:
            pairs.append((short, subject))
    return pairs


def upstream_ahead(ctx: GitContext, repo: Path) -> tuple[str, int] | None:
    """(upstream name, commits HEAD is ahead of it according to the local tracking ref); None without an upstream."""
    name = run_git(ctx, repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if not _ok(name) or not name.stdout.strip():
        return None
    count = run_git(ctx, repo, "rev-list", "--count", "@{u}..HEAD")
    if not _ok(count):
        return None
    try:
        return name.stdout.strip(), int(count.stdout.strip())
    except ValueError:
        return None


# -- writes: only the listed paths, nothing else ----------------------------------------------------


def switch_branch(ctx: GitContext, repo: Path, name: str) -> GitRun | Issue:
    """A plain `git switch name`: local changes come along, and git itself refuses a conflict.

    A success also writes to stderr, so callers use the exit code only. Never forced, merged or discarded.
    """
    return run_git(ctx, repo, "switch", name)


def _nul_paths(rels) -> bytes:
    return b"".join(rel.encode("utf-8") + b"\0" for rel in rels)


def add_intent(ctx: GitContext, repo: Path, rels) -> GitRun | Issue:
    """Record intent-to-add for new files, so `commit --only` knows them."""
    return run_git(
        ctx, repo, "add", "-N", "--pathspec-from-file=-", "--pathspec-file-nul", stdin_data=_nul_paths(rels)
    )


def unstage(ctx: GitContext, repo: Path, rels) -> GitRun | Issue:
    """Undo an intent-to-add for exactly these paths; the files on disk are untouched."""
    return run_git(
        ctx, repo, "reset", "-q", "--pathspec-from-file=-", "--pathspec-file-nul", stdin_data=_nul_paths(rels)
    )


def _commit_with_message(
    ctx: GitContext, repo: Path, message: str, args: tuple[str, ...], stdin_data: bytes | None, timeout: float
) -> GitRun | Issue:
    """Run `git commit -F <message file> <args>`; the message goes through a temp file outside the repo."""
    try:
        with tempfile.NamedTemporaryFile("wb", suffix=".txt", delete=False) as handle:
            handle.write(message.encode("utf-8"))
            name = handle.name
    except OSError as e:
        return Issue(Severity.ERROR, "git.not_run", f"Could not write the commit message: {e.strerror or e}")
    try:
        return run_git(ctx, repo, "commit", "--only", "-F", name, *args, stdin_data=stdin_data, timeout=timeout)
    finally:
        try:
            os.unlink(name)
        except OSError:
            pass


def commit_paths(
    ctx: GitContext, repo: Path, message: str, rels, *, timeout: float = COMMIT_TIMEOUT
) -> GitRun | Issue:
    """Commit exactly rels from the working tree; other staged or changed files stay as they are."""
    return _commit_with_message(
        ctx, repo, message, ("--pathspec-from-file=-", "--pathspec-file-nul"), _nul_paths(rels), timeout
    )


def commit_gitlink(
    ctx: GitContext, parent: Path, message: str, rel: str, *, timeout: float = COMMIT_TIMEOUT
) -> GitRun | Issue:
    """Commit only the submodule entry at rel in the parent repo."""
    return _commit_with_message(ctx, parent, message, ("--", rel), None, timeout)
