"""Precheck before the Atomic_ migration starts writing (Phase 13, MIG-01).

The migration never starts while Custom holds uncommitted work (D-02): check_custom names every
changed or untracked file (never an ignored one, RESEARCH F-09). When Custom is clean it decides
whether the pre-atomic recovery tag needs to be created, is already in place at HEAD, or sits at
another commit (CONTEXT discretion "pre-atomic tag"); ensure_tag re-checks and acts on that
decision right before the first write, because files can change between preview and Run. Qt-free;
imports only gitops and models.
"""

from dataclasses import dataclass
from pathlib import Path

from ...gitops import (
    GitContext,
    MIN_GIT_VERSION,
    busy_operation,
    create_tag,
    current_branch,
    find_git,
    git_version,
    head_commit,
    identity_known,
    short_hash,
    show_toplevel,
    status_entries,
    tag_commit,
)
from ...models import Issue, Severity

PRE_ATOMIC_TAG = "pre-atomic"

_CANNOT_START = "The migration cannot start: "


@dataclass(frozen=True)
class Precheck:
    ok: bool
    issues: tuple[Issue, ...]
    head: str | None
    branch: str | None
    tag_action: str  # "create", "reuse" or ""


def _context(git: GitContext | None, repo_root: Path) -> GitContext | Issue:
    if git is not None:
        return git
    found = find_git(repo_root)
    return found if isinstance(found, Issue) else GitContext(found)


def _same_dir(a: Path, b: Path) -> bool:
    return Path(a).resolve() == Path(b).resolve()


def _refuse(code: str, text: str, head: str | None = None, branch: str | None = None) -> Precheck:
    return Precheck(False, (Issue(Severity.ERROR, code, _CANNOT_START + text),), head, branch, "")


def check_custom(custom_dir: Path, repo_root: Path, *, git: GitContext | None = None) -> Precheck:
    """Whether the migration may start writing to custom_dir, and what the pre-atomic tag needs."""
    ctx = _context(git, repo_root)
    if isinstance(ctx, Issue):
        return Precheck(False, (Issue(Severity.ERROR, "migration.git_unavailable", ctx.text),), None, None, "")

    version = git_version(ctx)
    if version is None or version < MIN_GIT_VERSION:
        needed = ".".join(str(part) for part in MIN_GIT_VERSION)
        found = ".".join(str(part) for part in version) if version else "unknown"
        return _refuse("migration.git_old", f"git {needed} or newer is needed (found {found}).")

    top = show_toplevel(ctx, custom_dir)
    if top is None or not _same_dir(top, custom_dir):
        return _refuse("migration.not_git", "Custom is not a git work tree.")

    busy = busy_operation(ctx, custom_dir)
    if busy:
        return _refuse("migration.busy", f"{busy} is in progress in Custom.")

    if not identity_known(ctx, custom_dir):
        return _refuse(
            "migration.identity",
            "git does not know who you are: set user.name and user.email, or "
            "GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL, GIT_COMMITTER_NAME and GIT_COMMITTER_EMAIL",
        )

    head = head_commit(ctx, custom_dir)
    branch = current_branch(ctx, custom_dir)
    if branch is None:
        return _refuse("migration.detached", "Custom is on a detached HEAD.", head, None)

    changed = status_entries(ctx, custom_dir)
    if isinstance(changed, Issue):
        return Precheck(False, (changed,), head, branch, "")
    if changed:
        listing = "\n".join(sorted(changed))
        text = (
            "Custom has uncommitted changes. Commit or delete them first, then open the migration again:\n"
            + listing
        )
        return Precheck(False, (Issue(Severity.ERROR, "migration.uncommitted", _CANNOT_START + text),), head, branch, "")

    existing = tag_commit(ctx, custom_dir, PRE_ATOMIC_TAG)
    if existing is None:
        tag_action = "create"
    elif existing == head:
        tag_action = "reuse"
    else:
        short = short_hash(ctx, custom_dir, existing) or existing[:7]
        text = (
            f"the tag {PRE_ATOMIC_TAG} already points at {short} (the recovery point of an earlier migration). "
            f"To keep it under another name and free the name, run from the repo root: "
            f"git -C Custom tag {PRE_ATOMIC_TAG}-old {PRE_ATOMIC_TAG}, then git -C Custom tag -d {PRE_ATOMIC_TAG}. "
            "Then open the migration again."
        )
        return Precheck(
            False, (Issue(Severity.ERROR, "migration.tag_elsewhere", _CANNOT_START + text),), head, branch, ""
        )

    return Precheck(True, (), head, branch, tag_action)


def ensure_tag(custom_dir: Path, repo_root: Path, *, git: GitContext | None = None) -> list[Issue]:
    """Create, reuse or refuse the pre-atomic tag; re-checks custom_dir first (files can change between preview and Run)."""
    pre = check_custom(custom_dir, repo_root, git=git)
    if not pre.ok:
        return list(pre.issues)

    ctx = _context(git, repo_root)
    if isinstance(ctx, Issue):
        return [Issue(Severity.ERROR, "migration.git_unavailable", ctx.text)]

    if pre.tag_action == "create":
        result = create_tag(ctx, custom_dir, PRE_ATOMIC_TAG)
        if isinstance(result, Issue) or result.returncode != 0:
            output = result.text if isinstance(result, Issue) else result.output
            text = f"{_CANNOT_START}could not create the {PRE_ATOMIC_TAG} tag ({output})."
            return [Issue(Severity.ERROR, "migration.tag_failed", text)]
        short = short_hash(ctx, custom_dir)
        return [
            Issue(
                Severity.INFO,
                "migration.tagged",
                f"Tagged Custom as {PRE_ATOMIC_TAG} at {short}: everything can be restored from it",
            )
        ]

    if pre.tag_action == "reuse":
        short = short_hash(ctx, custom_dir)
        return [
            Issue(
                Severity.INFO,
                "migration.tag_reused",
                f"Custom is already tagged {PRE_ATOMIC_TAG} at {short}: nothing to do",
            )
        ]

    return []
