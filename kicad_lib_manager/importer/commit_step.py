"""The commit step after an install (Phase 6): probe the git state, then commit the part (GIT-01, GIT-02).

Qt-free. Both entry points run on a worker thread and return plain dataclasses with Issues; every
git call goes through gitops, which holds no way to reach another repository. The commit is
path-limited (`commit --only` with the listed files), so unrelated changes stay exactly as they were.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .. import gitops
from ..gitops import GitContext, GitRun
from ..models import Issue, Severity
from .commit_plan import CommitPlan, parent_message, subject_of


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


def probe_commit(cplan: CommitPlan, *, git: GitContext | None = None) -> CommitProbe:
    """Read the git state of Custom and the parent repo; nothing is changed."""
    ctx = _context(cplan, git)
    if isinstance(ctx, Issue):
        return _unavailable("unavailable", ctx.text)
    errors = [issue for issue in cplan.issues if issue.severity is Severity.ERROR]
    if errors:
        return _unavailable("unavailable", errors[0].text)
    custom = cplan.custom_dir
    top = gitops.show_toplevel(ctx, custom)
    if top is None or not _same_dir(top, custom):
        return _unavailable("unavailable", "Custom is not a git work tree")
    branch = gitops.current_branch(ctx, custom)
    head = gitops.head_commit(ctx, custom) or ""
    if branch is None:
        short = gitops.short_hash(ctx, custom) or head[:7] or "unknown"
        state, reason, ref, ahead = _detached_state(ctx, cplan, short)
        issues = (_probe_issue(state, reason),) if state == "refused" else ()
        return CommitProbe(state=state, reason=reason, head=head, main_ref=ref, main_ahead=ahead, issues=issues)

    parent_ok, parent_reason, parent_branch, gitlink_old = False, "", None, None
    parent_top = gitops.show_toplevel(ctx, cplan.repo_root)
    if parent_top is None or not _same_dir(parent_top, cplan.repo_root):
        parent_reason = f"no parent git repository at {cplan.repo_root}"
    else:
        parent_branch = gitops.current_branch(ctx, cplan.repo_root)
        if parent_branch is None:
            parent_reason = "the parent repo is on a detached HEAD"
        else:
            parent_ok = True
            gitlink_old = gitops.committed_gitlink(ctx, cplan.repo_root, cplan.custom_rel)
    return CommitProbe(
        state="ready",
        branch=branch,
        head=head,
        not_main=branch != "main",  # a named branch is committed on as it is (D-14)
        parent_dir=cplan.repo_root,
        parent_ok=parent_ok,
        parent_reason=parent_reason,
        parent_branch=parent_branch,
        gitlink_old=gitlink_old,
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

    A failed parent commit keeps the Custom commit (D-03); nothing is retried and nothing is pushed.
    expected_branch is the branch the probe saw; the refusals that use it come with plan 06-07.
    """
    ctx = _context(cplan, git)
    if isinstance(ctx, Issue):
        return _failed("commit.custom_failed", f"Commit unavailable: {ctx.text}")
    step = progress or (lambda *args: None)
    custom = cplan.custom_dir
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
            output = added.text if isinstance(added, Issue) else added.output
            return _failed(
                "commit.custom_failed",
                f"Commit in Custom failed ({_exit_text(added)}); nothing was committed\n{output}",
                output,
            )
    run = gitops.commit_paths(ctx, custom, message, rels)
    if _run_failed(run):
        if new:
            gitops.unstage(ctx, custom, new)
        output = run.text if isinstance(run, Issue) else run.output
        return _failed(
            "commit.custom_failed",
            f"Commit in Custom failed ({_exit_text(run)}); nothing was committed\n{output}",
            output,
        )

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
    if not bump_parent:
        return CommitOutcome(issues=tuple(issues), **fields)

    step("Committing Custom ref in parent...", 1, 2)
    parent = cplan.repo_root
    old = gitops.committed_gitlink(ctx, parent, cplan.custom_rel)
    new_head = gitops.head_commit(ctx, custom) or ""
    commits = gitops.log_range(ctx, custom, old, new_head) if old else []
    text = parent_message(
        subject_of(message), cplan.custom_rel, old, new_head, commits or [], listed=commits is not None
    )
    fields["parent_message"] = text
    parent_run = gitops.commit_gitlink(ctx, parent, text, cplan.custom_rel)
    if _run_failed(parent_run):
        subject = text.splitlines()[0].replace('"', '\\"')
        manual = f'git -C "{parent.as_posix()}" commit -m "{subject}" -- {cplan.custom_rel}'
        output = parent_run.text if isinstance(parent_run, Issue) else parent_run.output
        issues.append(Issue(
            Severity.ERROR, "commit.parent_failed",
            f"The Custom commit {short} was kept, but the parent commit failed ({_exit_text(parent_run)}).\n"
            f"{output}\nFinish it by hand: {manual}",
        ))
        return CommitOutcome(manual_command=manual, output=output, issues=tuple(issues), **fields)

    parent_short = gitops.short_hash(ctx, parent) or "?"
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
