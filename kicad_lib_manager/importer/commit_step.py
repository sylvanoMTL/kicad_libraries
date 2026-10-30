"""The commit step after an install (Phase 6): probe the git state, then commit the part (GIT-01, GIT-02).

Qt-free. Both entry points run on a worker thread and return plain dataclasses with Issues; every
git call goes through gitops, which holds no way to reach another repository. The commit is
path-limited (`commit --only` with the listed files), so unrelated changes stay exactly as they were.
"""

import hashlib
import os
import shlex
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

from .. import gitops
from ..gitops import GitContext, GitRun
from ..models import Issue, Severity
from . import commit_gate
from .commit_gate import CANCELLED, GateResult, failure_lines, gate_issues, refusal_summary
from .commit_plan import (
    NOTE_ADDED,
    CommitPlan,
    changed_since_install,
    file_sha256,
    parent_message,
    pre_install_bytes,
    rebaseline,
    subject_of,
    with_added_files,
)
from .content import MAX_READ, ContentText, binary_text, diff_text


@dataclass(frozen=True)
class CommitProbe:
    """What the probe found. state: "ready" | "gated" | "unavailable" | "refused" | "offer_switch".

    "gated" means Custom could be committed to, but a planned file changed after the install (stale names
    them): the panel asks for Check again before anything else.
    """

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
    stale: tuple[str, ...] = ()  # display paths of planned files that changed after the install (D-08, D-09)
    identical: frozenset[str] = frozenset()  # planned rels whose bytes already equal HEAD (D-13)
    all_identical: bool = False  # every planned file equals HEAD: no Custom commit is possible (D-14)
    gate: GateResult | None = None  # what the atomic gate found; set for every probe that could commit (GIT-06)


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
    manual_label: str = ""  # the words shown before manual_command: which shell it is written for
    output: str = ""
    issues: tuple[Issue, ...] = ()
    parent_only: bool = False  # the D-14 bump: Custom already held the files, only the parent gitlink was committed

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
        return (
            "git does not know who you are: set user.name and user.email, or "
            "GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL, GIT_COMMITTER_NAME and GIT_COMMITTER_EMAIL"
        )
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


ALREADY_IN_HEAD = "Already identical to HEAD, not in the commit: "


def _identical_to_head(ctx: GitContext, cplan: CommitPlan, cancelled: Callable[[], bool] | None = None) -> frozenset[str]:
    """The planned files whose bytes on disk equal what HEAD would put in the work tree (D-13).

    head_blob applies git's filters, so a clean CRLF file under autocrlf matches. Stops early and returns
    what is known once cancelled() is True.
    """
    found = set()
    for file in cplan.files:
        if cancelled is not None and cancelled():
            break
        digest = file_sha256(file.path)
        blob = gitops.head_blob(ctx, cplan.custom_dir, file.rel) if digest is not None else None
        if blob is not None and hashlib.sha256(blob).hexdigest() == digest:
            found.add(file.rel)
    return frozenset(found)


def _is_cancelled(cancelled: Callable[[], bool] | None) -> bool:
    return cancelled is not None and bool(cancelled())


def stale_text(stale: tuple[str, ...]) -> str:
    """The plain-language reason for files that changed after the install (D-08, D-09)."""
    return (
        f"{', '.join(stale)} changed after the install or the last check (for example, edited in KiCad). "
        "Click Check again to use the current content."
    )


def _dirty_before(ctx: GitContext, cplan: CommitPlan, cancelled: Callable[[], bool] | None = None) -> frozenset[str]:
    """Files the install changed that already differed from HEAD, or were not in HEAD, before it ran (D-09).

    base_sha256 None means the install created the file: never dirty. Otherwise the hash of what HEAD
    would put in the work tree is compared with the content the install replaced. Stops early and
    returns what is known once cancelled() is True.
    """
    dirty = set()
    for file in cplan.files:
        if _is_cancelled(cancelled):
            break
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


def _preexisting(
    ctx: GitContext, cplan: CommitPlan, head: str, cancelled: Callable[[], bool] | None = None
) -> dict | None:
    """The probe fields about the parent repo and about what was already there before the import.

    None when cancelled() turned True: the caller then reports the probe as cancelled.
    """
    parent_ok, parent_reason, parent_branch, gitlink_old = _parent_state(ctx, cplan)
    if _is_cancelled(cancelled):
        return None
    others, issues = _other_changes(ctx, cplan)
    if _is_cancelled(cancelled):
        return None
    earlier, listed = _earlier(ctx, cplan, gitlink_old, head)
    if _is_cancelled(cancelled):
        return None
    dirty = _dirty_before(ctx, cplan, cancelled)
    if _is_cancelled(cancelled):
        return None
    identical = _identical_to_head(ctx, cplan, cancelled)
    if _is_cancelled(cancelled):
        return None
    return dict(
        parent_dir=cplan.repo_root,
        parent_ok=parent_ok,
        parent_reason=parent_reason,
        parent_branch=parent_branch,
        gitlink_old=gitlink_old,
        earlier=earlier,
        earlier_listed=listed,
        dirty_before=dirty,
        other_changes=others,
        issues=issues,
        stale=changed_since_install(cplan),
        identical=identical,
        all_identical=bool(cplan.files) and identical == {f.rel for f in cplan.files},
    )


def probe_commit(
    cplan: CommitPlan,
    *,
    git: GitContext | None = None,
    kicad_fp_dir: Path | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> CommitProbe:
    """Read the git state of Custom and the parent repo; nothing is changed.

    cancelled is checked between the git steps, so a closing dialog waits for at most one running git
    call; once it is True the probe returns state "unavailable" with CANCELLED. When Custom is on a
    named branch the atomic gate runs too: a part that breaks the rule makes the state "gated" before
    any click (GIT-06, D-03).
    """
    ctx = _context(cplan, git)
    if isinstance(ctx, Issue):
        return _unavailable("unavailable", ctx.text)
    if _is_cancelled(cancelled):
        return _unavailable("unavailable", CANCELLED)
    reason = _custom_unavailable(ctx, cplan)
    if reason:
        return _unavailable("unavailable", reason)
    if _is_cancelled(cancelled):
        return _unavailable("unavailable", CANCELLED)
    custom = cplan.custom_dir
    branch = gitops.current_branch(ctx, custom)
    head = gitops.head_commit(ctx, custom) or ""
    if _is_cancelled(cancelled):
        return _unavailable("unavailable", CANCELLED)
    if branch is None:
        short = gitops.short_hash(ctx, custom) or head[:7] or "unknown"
        state, reason, ref, ahead = _detached_state(ctx, cplan, short)
        if state == "refused":
            return CommitProbe(
                state=state, reason=reason, head=head, main_ref=ref, main_ahead=ahead,
                issues=(_probe_issue(state, reason),),
            )
        fields = _preexisting(ctx, cplan, head, cancelled)
        if fields is None:
            return _unavailable("unavailable", CANCELLED)
        return CommitProbe(state=state, reason=reason, head=head, main_ref=ref, main_ahead=ahead, **fields)

    fields = _preexisting(ctx, cplan, head, cancelled)
    if fields is None:
        return _unavailable("unavailable", CANCELLED)
    stale = fields["stale"]
    gate = commit_gate.run_gate(ctx, cplan, kicad_fp_dir, cancelled=cancelled)
    if _is_cancelled(cancelled):
        return _unavailable("unavailable", CANCELLED)
    reasons = []
    if gate.refused:
        reasons.append(refusal_summary(gate) + ".")
    if stale:
        reasons.append(stale_text(stale))
    fields["issues"] = (*fields["issues"], *gate_issues(gate))
    return CommitProbe(
        state="gated" if reasons else "ready",  # a stale file or a broken rule is known before any click (D-03, D-08)
        reason=" ".join(reasons),
        branch=branch,
        head=head,
        not_main=branch != "main",  # a named branch is committed on as it is (D-14)
        gate=gate,
        **fields,
    )


def _with_linked_files(
    ctx: GitContext, cplan: CommitPlan, kicad_fp_dir: Path | None, cancelled: Callable[[], bool] | None
) -> tuple[CommitPlan, Issue | None]:
    """The plan plus the Custom files a committed part links that a fix created or changed, each noted "added" (D-10).

    An untracked linked file joins with no base. A tracked linked footprint joins when it differs from
    HEAD, with the HEAD hash as its base, so the commit never leaves the part linking a committed
    footprint that lacks the model (D-10 amendment); a tracked model or an unchanged footprint never does.
    Only files and git state are read; nothing is staged or written. A file no committed part links
    never enters, however untracked it is (Phase 6 D-10). When git cannot say what is tracked, nothing is
    added and the second item is a WARNING commit.recheck_failed.
    """
    known = {cfile.rel.casefold() for cfile in cplan.files}
    pairs = [
        (rel, kind)
        for rel, kind in commit_gate.linked_custom_files(ctx, cplan, kicad_fp_dir, cancelled=cancelled)
        if rel.casefold() not in known and (cplan.custom_dir / rel).is_file()
    ]
    tracked = gitops.tracked_paths(ctx, cplan.custom_dir, [rel for rel, _ in pairs])
    if isinstance(tracked, Issue):
        text = f"Could not look for files added since the install: {tracked.text}"
        return cplan, Issue(Severity.WARNING, "commit.recheck_failed", text)
    added: list[tuple[str, str, str | None]] = []
    for rel, kind in pairs:
        if rel not in tracked:
            added.append((rel, kind, None))
            continue
        if kind != "footprint":
            continue
        head = gitops.head_blob(ctx, cplan.custom_dir, rel)
        now = file_sha256(cplan.custom_dir / rel)
        base = hashlib.sha256(head).hexdigest() if head is not None else None
        if now is not None and base != now:
            added.append((rel, kind, base))
    return (with_added_files(cplan, added) if added else cplan), None


def recheck_commit(
    cplan: CommitPlan,
    *,
    git: GitContext | None = None,
    kicad_fp_dir: Path | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> tuple[CommitPlan, CommitProbe]:
    """Check again: take every planned file as it is now, judge that content, and probe (D-08).

    A file whose bytes changed after the install takes its current hash (note "changed"); the install-time
    bytes stay in `installed`. The returned plan replaces the old one. Nothing is staged, committed or
    written: only files and read-only git are read. The stale rule between this check and the click stays,
    because the click compares each file with the new hash.
    """
    ctx = _context(cplan, git)
    if isinstance(ctx, Issue):
        return cplan, _unavailable("unavailable", ctx.text)
    new, failed = _with_linked_files(ctx, rebaseline(cplan), kicad_fp_dir, cancelled)
    probe = probe_commit(new, git=ctx, kicad_fp_dir=kicad_fp_dir, cancelled=cancelled)
    if failed is not None:
        probe = replace(probe, issues=(*probe.issues, failed))
    return new, probe


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


def _precheck(
    ctx: GitContext,
    cplan: CommitPlan,
    expected_branch: str | None,
    bump_parent: bool,
    kicad_fp_dir: Path | None = None,
) -> Issue | None:
    """The first reason the commit must not start, or None. Reads only; nothing is written (D-11, D-16).

    Everything the probe saw is checked again here, because the Result view can stay open while the
    files or either repo change. That includes the atomic gate (GIT-06, D-03).
    """
    errors = [issue for issue in cplan.issues if issue.severity is Severity.ERROR]
    if errors:
        return errors[0]
    stale = changed_since_install(cplan)
    if stale:
        return Issue(Severity.ERROR, "commit.stale_file", "Not committed: " + stale_text(stale))
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
    gate = commit_gate.run_gate(ctx, cplan, kicad_fp_dir)  # files can change between the probe and the click (D-03)
    if gate.refused:
        lines = "\n".join(failure_lines(gate))
        return Issue(Severity.ERROR, "commit.atomic", f"Not committed: {refusal_summary(gate)}.\n{lines}")
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


MANUAL_LABEL_POWERSHELL = "Finish it by hand. In PowerShell:"
MANUAL_LABEL = "Finish it by hand:"


def _is_windows(windows: bool | None) -> bool:
    return sys.platform == "win32" if windows is None else windows


def manual_label(*, windows: bool | None = None) -> str:
    """The words shown before the manual command: it says which shell the command is written for (D-16)."""
    return MANUAL_LABEL_POWERSHELL if _is_windows(windows) else MANUAL_LABEL


_PS_SINGLE_QUOTES = "'‘’‚‛"  # PowerShell reads the typographic single quotes as quote marks too


def _ps_quote(text: str) -> str:
    """A PowerShell verbatim string: single quotes, each embedded single quote doubled."""
    return "'" + "".join(c + c if c in _PS_SINGLE_QUOTES else c for c in text) + "'"


def manual_command(
    parent: Path, custom_rel: str, message: str, *, windows: bool | None = None, message_dir: Path | None = None
) -> str:
    """The git command that makes the parent commit by hand, written to be pasted into the user's shell (D-16).

    Windows: every argument is a PowerShell single-quoted string, so `$`, `$(...)` and backticks are never
    expanded. Windows PowerShell 5.1 still drops an embedded `"` and lets a trailing `\\` eat the closing
    quote when it builds the child's command line (research experiment E1). A subject with either takes
    the `-F` form: the full message goes to a UTF-8 file outside the repository and the command holds only
    its forward-slash path, so no message text reaches the command line (D-16 amended). Elsewhere
    shlex.quote is safe for every character and the `-m` form is always used. `windows` and `message_dir`
    exist so both branches can be tested on one machine.
    """
    subject = subject_of(message)
    if not _is_windows(windows):
        q = shlex.quote
        return f"git -C {q(parent.as_posix())} commit -m {q(subject)} -- {q(custom_rel)}"
    q = _ps_quote
    head = f"git -C {q(parent.as_posix())} commit"
    if '"' in subject or subject.endswith("\\"):
        name = _write_message_file(message, message_dir)
        if name is not None:
            return f"{head} -F {q(Path(name).as_posix())} -- {q(custom_rel)}"
    return f"{head} -m {q(subject)} -- {q(custom_rel)}"


def _write_message_file(message: str, directory: Path | None) -> str | None:
    """Write the full message (UTF-8) to a new file outside the repository; None when that fails.

    The file is left in place on purpose: the user pastes the command later.
    """
    try:
        fd, name = tempfile.mkstemp(prefix="kicad_parent_message_", suffix=".txt", dir=directory)
    except OSError:
        return None
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(message.encode("utf-8"))
    except OSError:
        return None
    return name


def _custom_fields(short: str, branch: str, upstream: tuple[str, int] | None) -> dict:
    return {
        "custom_commit": short,
        "custom_branch": branch,
        "custom_upstream": upstream[0] if upstream else None,
        "custom_ahead": upstream[1] if upstream else None,
    }


def _unfinished_outcome(
    ctx: GitContext, cplan: CommitPlan, message: str, run: GitRun | Issue, after: str, bump_parent: bool
) -> CommitOutcome:
    """The outcome when git failed or timed out but Custom's HEAD moved: the commit exists and is reported (REV-06, D-12).

    Nothing is unstaged or reset and no second git write starts: a leftover git process may still hold
    index.lock, so the parent bump is left to the user with the manual command.
    """
    custom = cplan.custom_dir
    short = gitops.short_hash(ctx, custom, after) or after[:7]
    branch = gitops.current_branch(ctx, custom) or "HEAD"
    upstream = gitops.upstream_ahead(ctx, custom)
    output = run.text if isinstance(run, Issue) else run.output
    if isinstance(run, Issue) and run.code == "git.timeout":
        text = f"Committed {short} in Custom, but git did not finish in time (a hook or signing step may still be running)"
    else:
        text = f"Committed {short} in Custom, but git reported a failure afterwards ({_exit_text(run)})"
    issues = [Issue(Severity.WARNING, "commit.custom_unfinished", text), _not_pushed(upstream, "Custom", branch)]
    fields = _custom_fields(short, branch, upstream)
    manual = label = ""
    if bump_parent:
        old = gitops.committed_gitlink(ctx, cplan.repo_root, cplan.custom_rel)
        fields["parent_message"] = _parent_text(ctx, cplan, subject_of(message), old, after)
        manual = manual_command(cplan.repo_root, cplan.custom_rel, fields["parent_message"])
        label = manual_label()
        issues.append(Issue(
            Severity.WARNING, "commit.parent_not_started",
            "The parent repo was not updated, because git may still be running in Custom.\n"
            f"{label} {manual}",
        ))
    return CommitOutcome(manual_command=manual, manual_label=label, output=output, issues=tuple(issues), **fields)


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


def _read_now(path: Path) -> bytes:
    """The current bytes of a planned file, refusing anything over the content view's read cap."""
    with open(path, "rb") as handle:
        data = handle.read(MAX_READ + 1)
    if len(data) > MAX_READ:
        raise OSError(f"the file is larger than {MAX_READ // (1024 * 1024)} MiB")
    return data


def changed_diff(cplan: CommitPlan, rel: str, *, git: GitContext | None = None) -> ContentText:
    """The D-08 view of one file Check again took: what the install wrote (or HEAD) against what the file holds now.

    A file a fix added is shown as HEAD against now; any other as installed against now. A 3D model, or a
    file whose installed bytes are not kept, is summarised by size and SHA-256. Reads files and runs
    read-only git only.
    """
    cfile = next((f for f in cplan.files if f.rel == rel), None)
    if cfile is None:
        return ContentText(f"{rel} - as installed vs now", rel, f"{rel} is not part of this commit.", "error")
    shown = cfile.display
    added = cfile.note == NOTE_ADDED
    title = f"{shown} - HEAD vs now" if added else f"{shown} - as installed vs now"
    try:
        current = _read_now(cfile.path)
    except OSError as e:
        return ContentText(title, shown, f"Could not read {shown}: {e.strerror or e}.", "error")
    sha = hashlib.sha256(current).hexdigest()
    now_label = f"{shown} (now)"
    if added:
        ctx = _context(cplan, git)
        if isinstance(ctx, Issue):
            return ContentText(title, shown, f"Could not read HEAD: {ctx.text}.", "error")
        head = gitops.head_blob(ctx, cplan.custom_dir, rel)
        if cfile.kind == "model":
            now = binary_text(now_label, len(current), sha)
            if head is None:
                return ContentText(title, shown, f"{shown} (not in HEAD)\n\n{now}", "binary")
            at_head = binary_text(f"{shown} (HEAD)", len(head), hashlib.sha256(head).hexdigest())
            return ContentText(title, shown, f"{at_head}\n\n{now}", "binary")
        old_label = f"{shown} (HEAD)" if head is not None else f"{shown} (not in HEAD)"
        return ContentText(title, shown, diff_text(head or b"", current, old_label, now_label), "diff")
    if cfile.kind == "model" or cfile.installed is None:
        body = binary_text(now_label, len(current), sha) + "\n\nThe content as installed is not kept for this file."
        return ContentText(title, shown, body, "binary")
    if current == cfile.installed:
        return ContentText(title, shown, "The file still holds what the install wrote.", "unchanged")
    return ContentText(title, shown, diff_text(cfile.installed, current, f"{shown} (as installed)", now_label), "diff")


def combined_view(since_install: ContentText, before_import: ContentText) -> ContentText:
    """One view holding the change since the install and the pre-import change of one file (D-08, D-09, WR-02)."""
    shown = since_install.header or before_import.header
    body = "\n\n".join((since_install.title, since_install.body, before_import.title, before_import.body))
    if "diff" in (since_install.kind, before_import.kind):
        kind = "diff"
    elif since_install.kind == before_import.kind:
        kind = since_install.kind
    else:
        kind = "text"
    return ContentText(f"{shown} - changed since install and before this import", shown, body, kind)


def run_commit(
    cplan: CommitPlan,
    message: str,
    bump_parent: bool,
    *,
    expected_branch: str | None = None,
    git: GitContext | None = None,
    progress: Callable | None = None,
    kicad_fp_dir: Path | None = None,
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
    refusal = _precheck(ctx, cplan, expected_branch, bump_parent, kicad_fp_dir)
    if refusal is not None:
        return CommitOutcome(issues=(refusal,))
    rels = [f.rel for f in cplan.files]
    # decided from the bytes on disk right before the write, so a file edited meanwhile is not mistaken (D-13)
    identical = _identical_to_head(ctx, cplan)
    if rels and identical == set(rels):
        if not bump_parent:
            return _failed("commit.nothing_to_commit", "Not committed: Custom already holds these files.")
        held = Issue(Severity.INFO, "commit.already_in_head", "Nothing to commit in Custom: it already holds these files")
        return _parent_step(ctx, cplan, message, [held], {}, step=step, short="", parent_only=True)
    step("Committing in Custom...", 0, 2)
    tracked = gitops.tracked_paths(ctx, custom, rels)
    if isinstance(tracked, Issue):
        return _failed("commit.custom_failed", f"Commit in Custom failed: {tracked.text}; nothing was committed")
    new = [rel for rel in rels if rel not in tracked]
    if new:
        added = gitops.add_intent(ctx, custom, new)
        if _run_failed(added):
            gitops.unstage(ctx, custom, new)
            return _custom_failure(added, committing=False)
    before = gitops.head_commit(ctx, custom)
    run = gitops.commit_paths(ctx, custom, message, rels)
    if _run_failed(run):
        # git may have made the commit and then failed or timed out (a slow hook or signing step): HEAD tells (D-12)
        after = gitops.head_commit(ctx, custom)
        if after and after != before:
            return _unfinished_outcome(ctx, cplan, message, run, after, bump_parent)
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
    fields = _custom_fields(short, branch, upstream)
    # the commit holds exactly the planned files, or the user is told it does not (RESEARCH Pitfall 1)
    planned = set(rels)
    committed_files = gitops.commit_files(ctx, custom)
    if committed_files is not None and set(committed_files) != planned:
        extra = sorted(set(committed_files) - planned)
        absent = planned - set(committed_files)
        # a planned file proven equal to HEAD is not a missing file: git had nothing to commit for it (D-13)
        already = [f.display for f in cplan.files if f.rel in absent and f.rel in identical]
        real_missing = sorted(absent - identical)
        if already:
            issues.append(Issue(Severity.INFO, "commit.already_in_head", ALREADY_IN_HEAD + ", ".join(already)))
        if extra or real_missing:
            stop = " The parent repo was not updated." if bump_parent else ""
            issues.append(Issue(
                Severity.ERROR, "commit.unexpected_files",
                f"The Custom commit {short} was made, but its files differ from the list shown: "
                f"{extra} added, {real_missing} missing.{stop}",
            ))
            return CommitOutcome(issues=tuple(issues), **fields)
    if not bump_parent:
        return CommitOutcome(issues=tuple(issues), **fields)
    return _parent_step(ctx, cplan, message, issues, fields, step=step, short=short)


def _parent_step(
    ctx: GitContext,
    cplan: CommitPlan,
    message: str,
    issues: list[Issue],
    fields: dict,
    *,
    step: Callable,
    short: str,
    parent_only: bool = False,
) -> CommitOutcome:
    """Commit only the Custom gitlink in the parent and fold the result into the outcome.

    parent_only is the bump with no new Custom commit (D-14, research Open Question 5): `committed`
    stays False because no Custom commit was made, and `parent_only` tells the dialog and the panel what happened.
    """
    step("Committing Custom ref in parent...", 0 if parent_only else 1, 1 if parent_only else 2)
    parent = cplan.repo_root
    parent_short, text, parent_run, parent_issues = commit_parent_ref(
        ctx, cplan, subject_of(message), parent_only=parent_only
    )
    fields["parent_message"] = text
    issues.extend(parent_issues)
    if parent_run is not None:
        manual = manual_command(cplan.repo_root, cplan.custom_rel, text)
        label = manual_label()
        output = parent_run.text if isinstance(parent_run, Issue) else parent_run.output
        what = (
            f"The parent commit failed ({_exit_text(parent_run)})." if parent_only
            else f"The Custom commit {short} was kept, but the parent commit failed ({_exit_text(parent_run)})."
        )
        issues.append(Issue(Severity.ERROR, "commit.parent_failed", f"{what}\n{output}\n{label} {manual}"))
        return CommitOutcome(
            manual_command=manual, manual_label=label, output=output, issues=tuple(issues),
            parent_only=parent_only, **fields,
        )
    if parent_short is None:  # the parent already points at Custom's HEAD: nothing to commit (D-13)
        return CommitOutcome(issues=tuple(issues), parent_only=parent_only, **fields)

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
    return CommitOutcome(issues=tuple(issues), parent_only=parent_only, **fields)
