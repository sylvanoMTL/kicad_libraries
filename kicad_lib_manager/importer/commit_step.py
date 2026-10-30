"""The commit step after an install (Phase 6): probe the git state, then commit the part (GIT-01, GIT-02).

Qt-free. Both entry points run on a worker thread and return plain dataclasses with Issues; every
git call goes through gitops, which holds no way to reach another repository. The commit is
path-limited (`commit --only` with the listed files), so unrelated changes stay exactly as they were.
"""

import hashlib
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .. import gitops
from ..gitops import GitContext, GitRun
from ..models import Issue, Severity
from .commit_plan import CommitPlan, changed_since_install, parent_message, pre_install_bytes, subject_of
from .content import ContentText, binary_text, diff_text


@dataclass(frozen=True)
class CommitProbe:
    """What the probe found. state: "ready" | "unavailable" | "refused" | "offer_switch"."""

    state: str
    reason: str = ""
    branch: str | None = None
    head: str = ""
    not_main: bool = False
    main_ref: str | None = None
    main_ahead: int = 0
    parent_dir: Path | None = None
    parent_ok: bool = False
    parent_reason: str = ""
    parent_branch: str | None = None
    gitlink_old: str | None = None
    earlier: tuple[tuple[str, str], ...] = ()
    earlier_listed: bool = True
    dirty_before: frozenset[str] = frozenset()
    other_changes: int = 0
    issues: tuple[Issue, ...] = ()


@dataclass(frozen=True)
class CommitOutcome:
    custom_commit: str | None = None
    custom_branch: str | None = None
    custom_upstream: str | None = None
    custom_ahead: int | None = None
    parent_commit: str | None = None
    parent_branch: str | None = None
    parent_upstream: str | None = None
    parent_ahead: int | None = None
    parent_message: str = ""
    manual_command: str = ""
    output: str = ""
    issues: tuple[Issue, ...] = ()

    @property
    def committed(self) -> bool:
        return self.custom_commit is not None

    @property
    def failed(self) -> bool:
        return any(issue.severity is Severity.ERROR for issue in self.issues)


def _context(cplan: CommitPlan, git: GitContext | None) -> GitContext | Issue:
    if git is not None:
        return git
    found = gitops.find_git(cplan.repo_root)
    return found if isinstance(found, Issue) else GitContext(found)


def _same_dir(a: Path, b: Path) -> bool:
    return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))


def _probe_issue(state: str, reason: str) -> Issue:
    if state == "refused":
        return Issue(Severity.WARNING, "commit.refused", f"Commit refused: {reason}")
    return Issue(Severity.WARNING, "commit.unavailable", f"Commit unavailable: {reason}")


def _unavailable(state: str, reason: str) -> CommitProbe:
    return CommitProbe(state=state, reason=reason, issues=(_probe_issue(state, reason),))


_LOCAL_MAIN = "refs/heads/main"
_ORIGIN_MAIN = "refs/remotes/origin/main"


def _detached_state(ctx: GitContext, cplan: CommitPlan, short: str) -> tuple[str, str, str | None, int]:
    """Decide what a detached Custom HEAD allows: (state, reason, main ref, commits main is ahead).

    A plain switch to main is offered only when main contains HEAD (D-15). A local main that does not
    contain it while origin/main does is refused: committing there would move the parent's gitlink backwards.
    """
    custom = cplan.custom_dir
    ref = gitops.main_ref(ctx, custom)
    if ref is None:
        return "refused", "Custom has no main branch (neither main nor origin/main exists)", None, 0
    if gitops.is_ancestor(ctx, custom, "HEAD", ref) is True:
        ahead = gitops.count_commits(ctx, custom, f"HEAD..{ref}") or 0
        where = "main" if ref == _LOCAL_MAIN else "origin/main"
        reason = (
            f"Custom is on a detached HEAD at {short} that is on {where}'s history. "
            f"main is {ahead} commit{'s' if ahead != 1 else ''} ahead."
        )
        if ref != _LOCAL_MAIN:
            reason += " Switching creates a local main that tracks origin/main."
        return "offer_switch", reason, ref, ahead
    if (
        ref == _LOCAL_MAIN
        and gitops.has_ref(ctx, custom, _ORIGIN_MAIN)
        and gitops.is_ancestor(ctx, custom, "HEAD", _ORIGIN_MAIN) is True
    ):
        reason = (
            f"Custom's local main is behind origin/main and does not contain the checked-out commit {short}. "
            "Update local main first, then commit the imported files by hand. Nothing was switched or committed."
        )
        return "refused", reason, ref, 0
    reason = f"Custom is on a detached HEAD at {short} that is not on main's history. Nothing was switched or committed."
    return "refused", reason, ref, 0


def _custom_unavailable(ctx: GitContext, cplan: CommitPlan) -> str | None:
    """Why Custom cannot be committed to at all, or None. The first failing check decides (D-05, D-16)."""
    version = gitops.git_version(ctx)
    if version is None:
        return "git did not report its version"
    if version < gitops.MIN_GIT_VERSION:
        needed = ".".join(str(part) for part in gitops.MIN_GIT_VERSION)
        return f"git {needed} or newer is needed (found {'.'.join(str(part) for part in version)})"
    errors = [issue for issue in cplan.issues if issue.severity is Severity.ERROR]
    if errors:
        return errors[0].text
    custom = cplan.custom_dir
    top = gitops.show_toplevel(ctx, custom)
    # an uninitialised submodule folder resolves to the parent repo, which must never be committed to (T-06-07)
    if top is None or not _same_dir(top, custom):
        return "Custom is not a git work tree"
    busy = gitops.busy_operation(ctx, custom)
    if busy:
        return f"{busy} is in progress in Custom"
    if not gitops.identity_known(ctx, custom):
        return "git does not know who you are: set user.name and user.email"
    return None


def _parent_state(ctx: GitContext, cplan: CommitPlan) -> tuple[bool, str, str | None, str | None]:
    """(parent_ok, reason, branch, committed Custom gitlink): what the parent repo allows; it never blocks Custom (D-16)."""
    root = cplan.repo_root
    top = gitops.show_toplevel(ctx, root)
    if top is None or not _same_dir(top, root):
        return False, f"no parent git repository at {root.as_posix()}", None, None
    branch = gitops.current_branch(ctx, root)
    busy = gitops.busy_operation(ctx, root)
    if busy:
        return False, f"{busy} is in progress in the parent repo", branch, None
    if branch is None:
        return False, "the parent repo is on a detached HEAD", None, None
    return True, "", branch, gitops.committed_gitlink(ctx, root, cplan.custom_rel)


def _dirty_before(ctx: GitContext, cplan: CommitPlan) -> frozenset[str]:
    """Files the install changed that already differed from HEAD, or were not in HEAD, before it ran (D-09).

    base_sha256 None means the install created the file: never dirty. Otherwise the hash of what HEAD
    would put in the work tree is compared with the content the install replaced.
    """
    dirty = set()
    for file in cplan.files:
        if file.base_sha256 is None:
            continue
        blob = gitops.head_blob(ctx, cplan.custom_dir, file.rel)
        if blob is None or hashlib.sha256(blob).hexdigest() != file.base_sha256:
            dirty.add(file.rel)
    return frozenset(dirty)


def _other_changes(ctx: GitContext, cplan: CommitPlan) -> tuple[int, tuple[Issue, ...]]:
    """How many changed or untracked files in Custom are not part of the commit (D-10)."""
    entries = gitops.status_entries(ctx, cplan.custom_dir)
    if isinstance(entries, Issue):
        text = f"Could not count the other changes in Custom: {entries.text}"
        return 0, (Issue(Severity.WARNING, "commit.status_failed", text),)
    touched = {file.rel.casefold() for file in cplan.files}
    return sum(1 for path in entries if path.casefold() not in touched), ()


def _earlier(
    ctx: GitContext, cplan: CommitPlan, gitlink_old: str | None, head: str
) -> tuple[tuple[tuple[str, str], ...], bool]:
    """(Custom commits from the parent's committed gitlink to Custom's HEAD, oldest first; whether they could be listed)."""
    if gitlink_old is None:
        return (), True  # no earlier gitlink: nothing is earlier, and nothing failed to list (REV-07)
    if not head:
        return (), False
    if gitlink_old == head:
        return (), True
    pairs = gitops.log_range(ctx, cplan.custom_dir, gitlink_old, "HEAD")
    return (tuple(pairs), True) if pairs is not None else ((), False)


def _preexisting(ctx: GitContext, cplan: CommitPlan, head: str) -> dict:
    """The probe fields about the parent repo and about what was already there before the import."""
    parent_ok, parent_reason, parent_branch, gitlink_old = _parent_state(ctx, cplan)
    others, issues = _other_changes(ctx, cplan)
    earlier, listed = _earlier(ctx, cplan, gitlink_old, head)
    return dict(
        parent_dir=cplan.repo_root,
        parent_ok=parent_ok,
        parent_reason=parent_reason,
        parent_branch=parent_branch,
        gitlink_old=gitlink_old,
        earlier=earlier,
        earlier_listed=listed,
        dirty_before=_dirty_before(ctx, cplan),
        other_changes=others,
        issues=issues,
    )


def probe_commit(cplan: CommitPlan, *, git: GitContext | None = None) -> CommitProbe:
    """Read the git state of Custom and the parent repo; nothing is changed."""
    ctx = _context(cplan, git)
    if isinstance(ctx, Issue):
        return _unavailable("unavailable", ctx.text)
    reason = _custom_unavailable(ctx, cplan)
    if reason:
        return _unavailable("unavailable", reason)
    custom = cplan.custom_dir
    branch = gitops.current_branch(ctx, custom)
    head = gitops.head_commit(ctx, custom) or ""
    if branch is None:
        short = gitops.short_hash(ctx, custom) or head[:7] or "unknown"
        state, reason, ref, ahead = _detached_state(ctx, cplan, short)
        if state == "refused":
            return CommitProbe(
                state=state, reason=reason, head=head, main_ref=ref, main_ahead=ahead,
                issues=(_probe_issue(state, reason),),
            )
        return CommitProbe(
            state=state, reason=reason, head=head, main_ref=ref, main_ahead=ahead, **_preexisting(ctx, cplan, head)
        )

    return CommitProbe(
        state="ready",
        branch=branch,
        head=head,
        not_main=branch != "main",  # a named branch is committed on as it is (D-14)
        **_preexisting(ctx, cplan, head),
    )


@dataclass(frozen=True)
class SwitchOutcome:
    ok: bool
    issues: tuple[Issue, ...] = ()
    output: str = ""


def switch_to_main(cplan: CommitPlan, *, git: GitContext | None = None) -> SwitchOutcome:
    """Switch a detached Custom to main with a plain `git switch main`; the user's changes come along (D-15).

    Nothing is stashed, reset or forced. Git refuses when the switch would overwrite local changes; that
    refusal is reported as it is and HEAD, the index and the work tree stay as they were.
    """
    ctx = _context(cplan, git)
    if isinstance(ctx, Issue):
        return SwitchOutcome(False, (_probe_issue("unavailable", ctx.text),))
    custom = cplan.custom_dir
    branch = gitops.current_branch(ctx, custom)
    if branch is not None:
        return SwitchOutcome(False, (_probe_issue("refused", f"Custom is on branch {branch}, not a detached HEAD"),))
    head = gitops.head_commit(ctx, custom) or ""
    short = gitops.short_hash(ctx, custom) or head[:7] or "unknown"
    state, reason, _, _ = _detached_state(ctx, cplan, short)
    if state != "offer_switch":
        return SwitchOutcome(False, (_probe_issue("refused", reason),))
    run = gitops.switch_branch(ctx, custom, "main")
    output = run.text if isinstance(run, Issue) else run.output
    if _run_failed(run):
        text = f"git refused to switch Custom to main; nothing was committed\n{output}"
        return SwitchOutcome(False, (Issue(Severity.ERROR, "commit.switch_failed", text),), output)
    return SwitchOutcome(True, (Issue(Severity.SUCCESS, "commit.switched", "Switched Custom to main"),), output)


def _failed(code: str, text: str, output: str = "") -> CommitOutcome:
    return CommitOutcome(output=output, issues=(Issue(Severity.ERROR, code, text),))


def _not_pushed(upstream: tuple[str, int] | None, where: str, branch: str) -> Issue:
    if upstream is None:
        return Issue(Severity.INFO, "commit.not_pushed", f"Not pushed — {branch} in {where} has no upstream")
    name, ahead = upstream
    plural = "s" if ahead != 1 else ""
    return Issue(
        Severity.INFO, "commit.not_pushed",
        f"Not pushed — {where} is {ahead} commit{plural} ahead of {name} (as last fetched)",
    )


def _exit_text(run: GitRun | Issue) -> str:
    return run.text if isinstance(run, Issue) else f"git exit {run.returncode}"


def _run_failed(run: GitRun | Issue) -> bool:
    return isinstance(run, Issue) or run.returncode != 0


def _precheck(ctx: GitContext, cplan: CommitPlan, expected_branch: str | None, bump_parent: bool) -> Issue | None:
    """The first reason the commit must not start, or None. Reads only; nothing is written (D-11, D-16).

    Everything the probe saw is checked again here, because the Result view can stay open while the
    files or either repo change.
    """
    errors = [issue for issue in cplan.issues if issue.severity is Severity.ERROR]
    if errors:
        return errors[0]
    stale = changed_since_install(cplan)
    if stale:
        plural = "s" if len(stale) != 1 else ""
        return Issue(
            Severity.ERROR, "commit.stale_file",
            f"Not committed: {', '.join(stale)} changed after the install (for example, edited in KiCad). "
            f"Check the file{plural} and commit by hand.",
        )
    reason = _custom_unavailable(ctx, cplan)
    if reason:
        return Issue(Severity.ERROR, "commit.refused", f"Not committed: {reason}")
    custom = cplan.custom_dir
    branch = gitops.current_branch(ctx, custom)
    if branch is None:
        return Issue(Severity.ERROR, "commit.refused", "Not committed: Custom is on a detached HEAD.")
    if expected_branch is not None and branch != expected_branch:
        return Issue(
            Severity.ERROR, "commit.branch_changed",
            f"Custom's branch changed from {expected_branch} to {branch} since the check; nothing was committed",
        )
    if bump_parent:
        parent_ok, parent_reason, _, _ = _parent_state(ctx, cplan)
        if not parent_ok:
            return Issue(
                Severity.ERROR, "commit.parent_unavailable",
                f"Not committed: {parent_reason}. Untick the parent option to commit in Custom only.",
            )
    rels = [f.rel for f in cplan.files]
    tracked = gitops.tracked_paths(ctx, custom, rels)
    if isinstance(tracked, Issue):
        return Issue(Severity.ERROR, "commit.custom_failed", f"Commit in Custom failed: {tracked.text}; nothing was committed")
    ignored = gitops.ignored_paths(ctx, custom, [rel for rel in rels if rel not in tracked])
    if isinstance(ignored, Issue):
        return Issue(Severity.ERROR, "commit.custom_failed", f"Commit in Custom failed: {ignored.text}; nothing was committed")
    if ignored:  # never added with a force flag (RESEARCH Pitfall 4)
        verb = "is" if len(ignored) == 1 else "are"
        return Issue(Severity.ERROR, "commit.ignored", f"Not committed: {', '.join(ignored)} {verb} ignored by Custom's .gitignore.")
    return None


def _custom_failure(run: GitRun | Issue, *, committing: bool) -> CommitOutcome:
    """The ERROR outcome of a rejected Custom write; hook output arrives on stderr and is kept whole (Pitfall 6)."""
    output = run.text if isinstance(run, Issue) else run.output
    if committing and isinstance(run, Issue) and run.code == "git.timeout":
        text = (
            f"Commit in Custom did not finish within {gitops.COMMIT_TIMEOUT:g} s "
            "(check for a stuck hook or a leftover index.lock); nothing was committed."
        )
    else:
        text = f"Commit in Custom failed ({_exit_text(run)}); nothing was committed\n{output}"
    return _failed("commit.custom_failed", text, output)


def _parent_text(
    ctx: GitContext, cplan: CommitPlan, subject: str, old: str | None, new: str, *, parent_only: bool = False
) -> str:
    """The parent message for the bump from old to new, built through the one parent_message builder (D-15).

    The new Custom commit's own line carries the app's subject (RESEARCH Pitfall 7); every other line is
    git's. With parent_only there is no new Custom commit, so all lines are git's own.
    """
    custom = cplan.custom_dir
    if old:
        found = gitops.log_range(ctx, custom, old, new)
        listed, pairs = found is not None, list(found or [])
    else:
        listed, pairs = True, []  # nothing earlier exists, so nothing can fail to list
    if parent_only:
        return parent_message(
            subject, cplan.custom_rel, old, pairs[-1][0] if pairs else new[:7], pairs, listed=listed
        )
    tip = pairs[-1][0] if pairs else (gitops.short_hash(ctx, custom, new) or new[:7])
    return parent_message(subject, cplan.custom_rel, old, tip, [*pairs[:-1], (tip, subject)], listed=listed)


def commit_parent_ref(
    ctx: GitContext, cplan: CommitPlan, subject: str, *, parent_only: bool = False
) -> tuple[str | None, str, GitRun | Issue | None, tuple[Issue, ...]]:
    """Commit only the Custom gitlink in the parent repo, after Custom's own commit exists.

    Returns (short parent hash, final message, failing run, issues). The message is built here, from
    the gitlink the parent committed before and Custom's HEAD now, so it lists every Custom commit
    the bump covers, the earlier ones included (D-13). When the parent already points at Custom's
    HEAD no commit is made and an INFO issue says so (RESEARCH Pitfall 12). The gitlink is read with
    ls-tree, never parsed from diff output (Pitfall 13).
    """
    parent, custom = cplan.repo_root, cplan.custom_dir
    old = gitops.committed_gitlink(ctx, parent, cplan.custom_rel)
    new = gitops.head_commit(ctx, custom) or ""
    if old is not None and old == new:
        text = f"The parent repo already points at Custom {new[:7]}; no parent commit was needed"
        return None, "", None, (Issue(Severity.INFO, "commit.parent_skipped", text),)
    message = _parent_text(ctx, cplan, subject, old, new, parent_only=parent_only)
    run = gitops.commit_gitlink(ctx, parent, message, cplan.custom_rel)
    if _run_failed(run):
        return None, message, run, ()
    return gitops.short_hash(ctx, parent) or "?", message, None, ()


def pre_import_diff(cplan: CommitPlan, rel: str, *, git: GitContext | None = None) -> ContentText:
    """The D-09 view of one file: what HEAD holds against what the work tree held before the import.

    The pre-import side is the Phase 4 backup copy whose hash is base_sha256. Reads files and runs
    read-only git only.
    """
    cfile = next((f for f in cplan.files if f.rel == rel), None)
    if cfile is None:
        return ContentText(f"{rel} - HEAD vs before this import", rel, f"{rel} is not part of this commit.", "error")
    shown = cfile.display
    title = f"{shown} - HEAD vs before this import"
    if cfile.base_sha256 is None:
        return ContentText(title, shown, "This file did not exist before this import.", "text")
    pre = pre_install_bytes(cfile, cplan.backup_dir)
    if pre is None:
        where = str(cplan.backup_dir) if cplan.backup_dir is not None else "(no backup folder was recorded)"
        return ContentText(title, shown, f"The copy from before this import was not found in {where}.", "error")
    ctx = _context(cplan, git)
    if isinstance(ctx, Issue):
        return ContentText(title, shown, f"Could not read HEAD: {ctx.text}.", "error")
    head = gitops.head_blob(ctx, cplan.custom_dir, rel)
    if head is not None and head == pre:
        return ContentText(title, shown, "The file matched HEAD before this import.", "unchanged")
    if cfile.kind == "model":
        before = binary_text(f"{shown} (before this import)", len(pre), hashlib.sha256(pre).hexdigest())
        if head is None:
            return ContentText(title, shown, f"{shown} (not in HEAD)\n\n{before}", "binary")
        at_head = binary_text(f"{shown} (HEAD)", len(head), hashlib.sha256(head).hexdigest())
        return ContentText(title, shown, f"{at_head}\n\n{before}", "binary")
    old_label = f"{shown} (HEAD)" if head is not None else f"{shown} (not in HEAD)"
    body = diff_text(head or b"", pre, old_label, f"{shown} (before this import)")
    return ContentText(title, shown, body, "diff")


def run_commit(
    cplan: CommitPlan,
    message: str,
    bump_parent: bool,
    *,
    expected_branch: str | None = None,
    git: GitContext | None = None,
    progress: Callable | None = None,
) -> CommitOutcome:
    """Commit exactly the plan's files in Custom, then (optionally) only the Custom gitlink in the parent.

    Every refusal is decided by _precheck before the first git write. A rejected Custom commit leaves
    HEAD unchanged and undoes the app's own intent-to-add entries; a failed parent commit keeps the
    Custom commit (D-03). Nothing is retried and nothing is pushed.
    expected_branch is the branch the probe saw.
    """
    ctx = _context(cplan, git)
    if isinstance(ctx, Issue):
        return _failed("commit.custom_failed", f"Commit unavailable: {ctx.text}")
    step = progress or (lambda *args: None)
    custom = cplan.custom_dir
    refusal = _precheck(ctx, cplan, expected_branch, bump_parent)
    if refusal is not None:
        return CommitOutcome(issues=(refusal,))
    step("Committing in Custom...", 0, 2)
    rels = [f.rel for f in cplan.files]
    tracked = gitops.tracked_paths(ctx, custom, rels)
    if isinstance(tracked, Issue):
        return _failed("commit.custom_failed", f"Commit in Custom failed: {tracked.text}; nothing was committed")
    new = [rel for rel in rels if rel not in tracked]
    if new:
        added = gitops.add_intent(ctx, custom, new)
        if _run_failed(added):
            gitops.unstage(ctx, custom, new)
            return _custom_failure(added, committing=False)
    run = gitops.commit_paths(ctx, custom, message, rels)
    if _run_failed(run):
        if new:
            gitops.unstage(ctx, custom, new)
        return _custom_failure(run, committing=True)

    short = gitops.short_hash(ctx, custom) or "?"
    branch = gitops.current_branch(ctx, custom) or "HEAD"
    upstream = gitops.upstream_ahead(ctx, custom)
    issues = [
        Issue(Severity.SUCCESS, "commit.custom_done", f"Committed {short} on {branch} in Custom"),
        _not_pushed(upstream, "Custom", branch),
    ]
    fields = {
        "custom_commit": short,
        "custom_branch": branch,
        "custom_upstream": upstream[0] if upstream else None,
        "custom_ahead": upstream[1] if upstream else None,
    }
    # the commit holds exactly the planned files, or the user is told it does not (RESEARCH Pitfall 1)
    planned = set(rels)
    committed_files = gitops.commit_files(ctx, custom)
    if committed_files is not None and set(committed_files) != planned:
        extra, missing = sorted(set(committed_files) - planned), sorted(planned - set(committed_files))
        stop = " The parent repo was not updated." if bump_parent else ""
        issues.append(Issue(
            Severity.ERROR, "commit.unexpected_files",
            f"The Custom commit {short} was made, but its files differ from the list shown: "
            f"{extra} added, {missing} missing.{stop}",
        ))
        return CommitOutcome(issues=tuple(issues), **fields)
    if not bump_parent:
        return CommitOutcome(issues=tuple(issues), **fields)

    step("Committing Custom ref in parent...", 1, 2)
    parent = cplan.repo_root
    parent_short, text, parent_run, parent_issues = commit_parent_ref(ctx, cplan, subject_of(message))
    fields["parent_message"] = text
    issues.extend(parent_issues)
    if parent_run is not None:
        subject = text.splitlines()[0].replace('"', '\\"')
        manual = f'git -C "{parent.as_posix()}" commit -m "{subject}" -- {cplan.custom_rel}'
        output = parent_run.text if isinstance(parent_run, Issue) else parent_run.output
        issues.append(Issue(
            Severity.ERROR, "commit.parent_failed",
            f"The Custom commit {short} was kept, but the parent commit failed ({_exit_text(parent_run)}).\n"
            f"{output}\nFinish it by hand: {manual}",
        ))
        return CommitOutcome(manual_command=manual, output=output, issues=tuple(issues), **fields)
    if parent_short is None:  # the parent already points at Custom's HEAD: nothing to commit (D-13)
        return CommitOutcome(issues=tuple(issues), **fields)

    parent_branch = gitops.current_branch(ctx, parent) or "HEAD"
    parent_upstream = gitops.upstream_ahead(ctx, parent)
    issues.append(Issue(
        Severity.SUCCESS, "commit.parent_done", f"Committed {parent_short} on {parent_branch} in the parent repo"
    ))
    issues.append(_not_pushed(parent_upstream, "the parent repo", parent_branch))
    fields.update(
        parent_commit=parent_short,
        parent_branch=parent_branch,
        parent_upstream=parent_upstream[0] if parent_upstream else None,
        parent_ahead=parent_upstream[1] if parent_upstream else None,
    )
    return CommitOutcome(issues=tuple(issues), **fields)
