"""commit_step against real git: the detached-HEAD policy and the switch to main (Phase 6, GIT-03, D-14, D-15).

Each test builds a throwaway superproject (two bare remotes, a parent, a Custom submodule) and
puts Custom in the state under test. Nothing here touches the real repository.
"""

import dataclasses
import hashlib
import subprocess
from pathlib import Path

import pytest
from gitfixtures import (
    GIT,
    advance_remote_main,
    clone_parent_without_submodule,
    commit_file,
    delete_local_branch,
    detach,
    git_path,
    import_files,
    make_superproject,
    make_worktree,
    requires_git,
    start_merge_conflict,
    write_hook,
)

from kicad_lib_manager import gitops
from kicad_lib_manager.gitops import GitContext
from kicad_lib_manager.importer import commit_step
from kicad_lib_manager.importer.commit_plan import default_message, subject_of
from kicad_lib_manager.models import Severity

FP_NEW = "Footprints/IC_Battery_Charger_TI.pretty/FP1.kicad_mod"
SYM_FFC = "Symbols/Connector_FFC_GCT.kicad_sym"
SYM_USB = "Symbols/Connector_USB_GCT.kicad_sym"
STALE_REASON = (
    "Custom's local main is behind origin/main and does not contain the checked-out commit {short}. "
    "Update local main first, then commit the imported files by hand. Nothing was switched or committed."
)


def _ctx():
    return GitContext(Path(GIT))


def _recording_ctx():
    """A context whose runner records every argv and then runs git for real."""
    calls = []

    def runner(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.run(argv, **kwargs)

    return GitContext(Path(GIT), runner), calls


def _plan(repos):
    return import_files(repos, {FP_NEW: b'(footprint "FP1")\n'})


def _head(repos):
    return repos.git(repos.custom, "rev-parse", "HEAD").strip()


def _short(repos):
    return repos.git(repos.custom, "rev-parse", "--short", "HEAD").strip()


def _branch(repos):
    """The checked-out branch name, or "HEAD" when detached."""
    return repos.git(repos.custom, "rev-parse", "--abbrev-ref", "HEAD").strip()


def _two_commits_on_main(repos):
    commit_file(repos, repos.custom, "main_one.txt", b"one\n", "Main one")
    commit_file(repos, repos.custom, "main_two.txt", b"two\n", "Main two")


# -- named branches ------------------------------------------------------------


@requires_git
def test_probe_on_main_ready(tmp_path):
    repos = make_superproject(tmp_path / "git")
    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "ready"
    assert probe.branch == "main" and probe.not_main is False


@requires_git
def test_probe_other_branch_not_main(tmp_path):
    repos = make_superproject(tmp_path / "git")
    repos.git(repos.custom, "switch", "-c", "feature/y")
    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "ready"
    assert probe.branch == "feature/y" and probe.not_main is True


# -- detached HEAD: when a switch is offered -----------------------------------


@requires_git
def test_probe_detached_on_history_offers_switch(tmp_path):
    repos = make_superproject(tmp_path / "git")
    _two_commits_on_main(repos)
    detach(repos, "main~2")
    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "offer_switch"
    assert probe.main_ref == "refs/heads/main" and probe.main_ahead == 2
    assert probe.branch is None
    assert _short(repos) in probe.reason and "2 commits ahead" in probe.reason
    assert probe.issues == ()


@requires_git
def test_probe_detached_at_main_tip_offers_switch(tmp_path):
    repos = make_superproject(tmp_path / "git")
    detach(repos, "main")
    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "offer_switch"
    assert probe.main_ref == "refs/heads/main" and probe.main_ahead == 0


@requires_git
def test_probe_no_local_main_uses_origin_main(tmp_path):
    repos = make_superproject(tmp_path / "git")
    detach(repos, "main")
    delete_local_branch(repos, "main")
    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "offer_switch"
    assert probe.main_ref == "refs/remotes/origin/main" and probe.main_ahead == 0
    assert "origin/main's history" in probe.reason
    assert "Switching creates a local main that tracks origin/main." in probe.reason


# -- detached HEAD: when it is refused -----------------------------------------


@requires_git
def test_probe_detached_off_history_refused(tmp_path):
    repos = make_superproject(tmp_path / "git")
    detach(repos, "main")
    commit_file(repos, repos.custom, "diverged.txt", b"x\n", "Made on a detached HEAD")
    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "refused"
    assert probe.reason == (
        f"Custom is on a detached HEAD at {_short(repos)} that is not on main's history. "
        "Nothing was switched or committed."
    )
    assert [(i.severity, i.code) for i in probe.issues] == [(Severity.WARNING, "commit.refused")]


@requires_git
def test_probe_stale_local_main_refused(tmp_path):
    repos = make_superproject(tmp_path / "git")
    advance_remote_main(repos)
    detach(repos, "origin/main")
    plan = _plan(repos)
    ctx, calls = _recording_ctx()
    before = _head(repos)

    probe = commit_step.probe_commit(plan, git=ctx)
    switched = commit_step.switch_to_main(plan, git=ctx)

    assert probe.state == "refused"
    assert probe.reason == STALE_REASON.format(short=_short(repos))
    assert [i.code for i in probe.issues] == ["commit.refused"]
    assert switched.ok is False and [i.code for i in switched.issues] == ["commit.refused"]
    assert not [argv for argv in calls if argv[6] == "switch"]
    assert _branch(repos) == "HEAD" and _head(repos) == before


@requires_git
def test_probe_no_main_refused(tmp_path):
    repos = make_superproject(tmp_path / "git", remote_branch="trunk", custom_branch=None)
    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "refused"
    assert probe.reason == "Custom has no main branch (neither main nor origin/main exists)"
    assert [i.code for i in probe.issues] == ["commit.refused"]


# -- switch_to_main ------------------------------------------------------------


@requires_git
def test_switch_to_main_carries_changes(tmp_path):
    repos = make_superproject(tmp_path / "git")
    _two_commits_on_main(repos)
    detach(repos, "main~2")
    (repos.custom / "staged.txt").write_bytes(b"staged\n")
    repos.git(repos.custom, "add", "staged.txt")
    gitignore = repos.custom / ".gitignore"
    gitignore.write_bytes(gitignore.read_bytes() + b"*.log\n")
    (repos.custom / "untracked.txt").write_bytes(b"untracked\n")
    plan = import_files(repos, {FP_NEW: b'(footprint "FP1")\n', SYM_USB: (repos.custom / SYM_USB).read_bytes() + b"; import\n"})
    watched = [".gitignore", "staged.txt", "untracked.txt", FP_NEW, SYM_USB]
    status_before = repos.git(repos.custom, "status", "--porcelain=v1", "-z", "-uall")
    bytes_before = {rel: (repos.custom / rel).read_bytes() for rel in watched}

    outcome = commit_step.switch_to_main(plan, git=_ctx())

    assert outcome.ok is True
    assert [(i.severity, i.code) for i in outcome.issues] == [(Severity.SUCCESS, "commit.switched")]
    assert _branch(repos) == "main"
    assert repos.git(repos.custom, "status", "--porcelain=v1", "-z", "-uall") == status_before
    assert {rel: (repos.custom / rel).read_bytes() for rel in watched} == bytes_before


@requires_git
def test_switch_to_main_creates_tracking_branch(tmp_path):
    repos = make_superproject(tmp_path / "git")
    detach(repos, "main")
    delete_local_branch(repos, "main")
    plan = _plan(repos)

    outcome = commit_step.switch_to_main(plan, git=_ctx())

    assert outcome.ok is True
    assert _branch(repos) == "main"
    assert repos.git(repos.custom, "rev-parse", "--abbrev-ref", "main@{u}").strip() == "origin/main"


@requires_git
def test_switch_conflict_stays_detached(tmp_path):
    repos = make_superproject(tmp_path / "git")
    original = (repos.custom / SYM_FFC).read_bytes()
    main_tip = commit_file(repos, repos.custom, SYM_FFC, original + b"; main edit\n", "Main edits the library")
    detach(repos, "main~1")
    edited = original + b"; import edit\n"
    plan = import_files(repos, {SYM_FFC: edited})
    detached_at = _head(repos)

    outcome = commit_step.switch_to_main(plan, git=_ctx())

    assert outcome.ok is False
    (issue,) = outcome.issues
    assert issue.severity is Severity.ERROR and issue.code == "commit.switch_failed"
    assert "would be overwritten" in issue.text and "nothing was committed" in issue.text
    assert "would be overwritten" in outcome.output
    assert _branch(repos) == "HEAD" and _head(repos) == detached_at
    assert (repos.custom / SYM_FFC).read_bytes() == edited
    assert repos.git(repos.custom, "rev-parse", "main").strip() == main_tip


@requires_git
def test_switch_refuses_when_not_detached(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    ctx, calls = _recording_ctx()

    outcome = commit_step.switch_to_main(plan, git=ctx)

    assert outcome.ok is False and [i.code for i in outcome.issues] == ["commit.refused"]
    assert not [argv for argv in calls if argv[6] == "switch"]
    assert _branch(repos) == "main"


@requires_git
def test_switch_argv_is_plain(tmp_path):
    repos = make_superproject(tmp_path / "git")
    detach(repos, "main")
    plan = _plan(repos)
    ctx, calls = _recording_ctx()

    outcome = commit_step.switch_to_main(plan, git=ctx)

    assert outcome.ok is True
    assert [argv[6:] for argv in calls if argv[6] == "switch"] == [["switch", "main"]]
    assert not {argv[6] for argv in calls} & {"add", "reset", "commit"}


# -- when committing is unavailable (D-05, D-16) -------------------------------


def _answering(canned):
    """A runner that gives chosen subcommands a canned (exit code, stdout) and runs every other one for real."""

    def runner(argv, **kwargs):
        answer = canned.get(argv[6])
        if answer is None:
            return subprocess.run(argv, **kwargs)
        return subprocess.CompletedProcess(argv, answer[0], stdout=answer[1], stderr=b"")

    return GitContext(Path(GIT), runner)


def _unavailable_issue(reason):
    return [(Severity.WARNING, "commit.unavailable", f"Commit unavailable: {reason}")]


def _issue_triples(probe):
    return [(i.severity, i.code, i.text) for i in probe.issues]


@requires_git
def test_probe_git_missing_unavailable(tmp_path, monkeypatch):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    monkeypatch.setattr("kicad_lib_manager.gitops.shutil.which", lambda name: None)

    probe = commit_step.probe_commit(plan)

    assert probe.state == "unavailable"
    assert probe.reason == "git was not found on PATH"
    assert _issue_triples(probe) == _unavailable_issue("git was not found on PATH")


@requires_git
def test_probe_old_git_unavailable(tmp_path):
    repos = make_superproject(tmp_path / "git")
    probe = commit_step.probe_commit(_plan(repos), git=_answering({"--version": (0, b"git version 2.20.1\n")}))

    assert probe.state == "unavailable"
    assert probe.reason == "git 2.25 or newer is needed (found 2.20.1)"
    assert _issue_triples(probe) == _unavailable_issue(probe.reason)


@requires_git
def test_probe_windows_git_version_is_accepted(tmp_path):
    repos = make_superproject(tmp_path / "git")
    ctx = _answering({"--version": (0, b"git version 2.49.0.windows.1\n")})

    assert commit_step.probe_commit(_plan(repos), git=ctx).state == "ready"


@requires_git
def test_probe_uninitialised_custom_unavailable(tmp_path):
    repos = make_superproject(tmp_path / "git")
    clone = clone_parent_without_submodule(repos)
    assert (clone / "Custom").is_dir() and not list((clone / "Custom").iterdir())
    plan = dataclasses.replace(_plan(repos), repo_root=clone, custom_dir=clone / "Custom", files=())
    ctx, calls = _recording_ctx()

    probe = commit_step.probe_commit(plan, git=ctx)

    assert probe.state == "unavailable"
    assert probe.reason == "Custom is not a git work tree"
    assert _issue_triples(probe) == _unavailable_issue(probe.reason)
    assert not {argv[6] for argv in calls} & {"add", "reset", "commit", "switch"}


BUSY_MARKERS = [
    ("MERGE_HEAD", "a merge", False),
    ("rebase-merge", "a rebase", True),
    ("rebase-apply", "a rebase", True),
    ("CHERRY_PICK_HEAD", "a cherry-pick", False),
    ("REVERT_HEAD", "a revert", False),
    ("BISECT_LOG", "a bisect", False),
]


@requires_git
@pytest.mark.parametrize(("marker", "label", "is_dir"), BUSY_MARKERS)
def test_probe_custom_busy_unavailable(tmp_path, marker, label, is_dir):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    target = git_path(repos, repos.custom, marker)
    if is_dir:
        target.mkdir(parents=True)
    else:
        target.write_text(_head(repos) + "\n", encoding="utf-8")

    probe = commit_step.probe_commit(plan, git=_ctx())

    assert probe.state == "unavailable"
    assert probe.reason == f"{label} is in progress in Custom"
    assert _issue_triples(probe) == _unavailable_issue(probe.reason)


@requires_git
def test_probe_custom_real_merge_unavailable(tmp_path):
    repos = make_superproject(tmp_path / "git")
    start_merge_conflict(repos, repos.custom, SYM_FFC)
    assert git_path(repos, repos.custom, "MERGE_HEAD").is_file()

    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "unavailable"
    assert probe.reason == "a merge is in progress in Custom"


@requires_git
def test_probe_identity_unknown_unavailable(tmp_path):
    repos = make_superproject(tmp_path / "git")
    probe = commit_step.probe_commit(_plan(repos), git=_answering({"var": (128, b"")}))

    assert probe.state == "unavailable"
    assert probe.reason == "git does not know who you are: set user.name and user.email"
    assert _issue_triples(probe) == _unavailable_issue(probe.reason)


@requires_git
def test_probe_identity_known_by_default(tmp_path):
    repos = make_superproject(tmp_path / "git")

    assert commit_step.probe_commit(_plan(repos), git=_ctx()).state == "ready"


# -- the parent repo: reported, never blocking the Custom commit (D-16, D-17a) ---


@requires_git
def test_probe_parent_states(tmp_path):
    # (a) Custom cloned into a folder that is not inside any repository
    repos = make_superproject(tmp_path / "git")
    loose = tmp_path / "loose"
    loose.mkdir()
    repos.git(loose, "clone", str(repos.custom_remote), "Custom")
    for key, value in (("user.name", "Fixture User"), ("user.email", "fixture@example.invalid")):
        repos.git(loose / "Custom", "config", key, value)
    plan = dataclasses.replace(_plan(repos), repo_root=loose, custom_dir=loose / "Custom", files=())
    probe = commit_step.probe_commit(plan, git=_ctx())
    assert probe.state == "ready" and probe.branch == "main"
    assert probe.parent_ok is False
    assert probe.parent_reason == f"no parent git repository at {loose.as_posix()}"

    # (b) a detached parent
    repos = make_superproject(tmp_path / "git_b")
    repos.git(repos.parent, "switch", "--detach")
    probe = commit_step.probe_commit(_plan(repos), git=_ctx())
    assert probe.state == "ready" and probe.parent_ok is False
    assert probe.parent_reason == "the parent repo is on a detached HEAD"

    # (c) a merge in the parent
    repos = make_superproject(tmp_path / "git_c")
    start_merge_conflict(repos, repos.parent, "README.md")
    probe = commit_step.probe_commit(_plan(repos), git=_ctx())
    assert probe.state == "ready" and probe.parent_ok is False
    assert probe.parent_reason == "a merge is in progress in the parent repo"


@requires_git
def test_probe_reports_parent_path_and_branch(tmp_path):
    repos = make_superproject(tmp_path / "git")
    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "ready" and probe.parent_ok is True and probe.parent_reason == ""
    assert probe.parent_dir == repos.parent
    assert probe.parent_branch == "main"
    assert probe.gitlink_old == repos.git(repos.parent, "rev-parse", "HEAD:Custom").strip()


@requires_git
def test_probe_and_commit_in_linked_worktree(tmp_path):
    repos = make_superproject(tmp_path / "git")
    wt = make_worktree(repos)
    assert "worktrees" in wt.git(wt.custom, "rev-parse", "--git-dir")
    plan = import_files(wt, {FP_NEW: b'(footprint "FP1")\n'})

    probe = commit_step.probe_commit(plan, git=_ctx())
    assert probe.state == "ready" and probe.branch == "main"
    assert probe.parent_ok is True and probe.parent_dir == wt.parent
    assert probe.parent_branch == "feature/x"

    merge_head = git_path(wt, wt.custom, "MERGE_HEAD")
    assert "worktrees" in merge_head.as_posix()
    merge_head.write_text(wt.git(wt.custom, "rev-parse", "HEAD"), encoding="utf-8")
    busy = commit_step.probe_commit(plan, git=_ctx())
    assert busy.state == "unavailable" and busy.reason == "a merge is in progress in Custom"
    merge_head.unlink()

    outcome = commit_step.run_commit(plan, "Add FP1 to IC_Battery_Charger_TI", True, git=_ctx())

    assert outcome.committed and outcome.parent_commit is not None, outcome.issues
    assert outcome.parent_branch == "feature/x"
    assert wt.git(wt.custom, "show", "--name-only", "--format=", "HEAD").split() == [FP_NEW]
    assert wt.git(wt.parent, "show", "--name-only", "--format=", "HEAD").split() == ["Custom"]
    assert wt.git(wt.parent, "rev-parse", "HEAD:Custom").strip() == wt.git(wt.custom, "rev-parse", "HEAD").strip()
    assert repos.git(repos.parent, "rev-parse", "HEAD").strip() != wt.git(wt.parent, "rev-parse", "HEAD").strip()


# -- what was already there before the import (D-09, D-10, D-13) ---------------

MODEL_OLD = "3DModels/old.step"
KEEP = "3DModels/.gitkeep"


def _edit_in_place(repos, rel, suffix=b"; edited before the import\n"):
    path = repos.custom / rel
    path.write_bytes(path.read_bytes() + suffix)


@requires_git
@pytest.mark.parametrize("autocrlf", [True, False])
def test_dirty_before_flags_preexisting_edit(tmp_path, autocrlf):
    repos = make_superproject(tmp_path / "git", autocrlf=autocrlf)
    _edit_in_place(repos, SYM_FFC)
    plan = import_files(repos, {SYM_FFC: (repos.custom / SYM_FFC).read_bytes() + b"; imported\n"})

    probe = commit_step.probe_commit(plan, git=_ctx())

    assert probe.state == "ready"
    assert probe.dirty_before == frozenset({SYM_FFC})


@requires_git
@pytest.mark.parametrize("autocrlf", [True, False])
def test_dirty_before_clean_file_not_flagged(tmp_path, autocrlf):
    repos = make_superproject(tmp_path / "git", autocrlf=autocrlf)
    plan = import_files(repos, {SYM_FFC: (repos.custom / SYM_FFC).read_bytes() + b"; imported\n"})

    probe = commit_step.probe_commit(plan, git=_ctx())

    assert probe.state == "ready"
    assert probe.dirty_before == frozenset()


@requires_git
def test_dirty_before_preexisting_untracked_flagged(tmp_path):
    repos = make_superproject(tmp_path / "git")
    (repos.custom / MODEL_OLD).write_bytes(b"old model\n")
    plan = import_files(repos, {MODEL_OLD: b"new model\n"})

    probe = commit_step.probe_commit(plan, git=_ctx())

    assert probe.dirty_before == frozenset({MODEL_OLD})


@requires_git
def test_new_file_never_dirty(tmp_path):
    repos = make_superproject(tmp_path / "git")
    (repos.custom / KEEP).unlink()  # HEAD still holds this path, but the install creates the file
    plan = import_files(repos, {KEEP: b"created by the install\n", FP_NEW: b'(footprint "FP1")\n'})
    assert all(f.base_sha256 is None for f in plan.files)

    probe = commit_step.probe_commit(plan, git=_ctx())

    assert probe.dirty_before == frozenset()


@requires_git
def test_other_changes_counts_each_untracked_file(tmp_path):
    repos = make_superproject(tmp_path / "git")
    for name in ("a.txt", "b.txt", "c.txt"):
        (repos.custom / "scratch" / name).parent.mkdir(exist_ok=True)
        (repos.custom / "scratch" / name).write_bytes(b"x\n")
    (repos.custom / "staged.txt").write_bytes(b"staged\n")
    repos.git(repos.custom, "add", "staged.txt")
    _edit_in_place(repos, ".gitignore", b"*.log\n")
    plan = import_files(repos, {FP_NEW: b'(footprint "FP1")\n', SYM_USB: (repos.custom / SYM_USB).read_bytes() + b"; x\n"})

    probe = commit_step.probe_commit(plan, git=_ctx())

    assert probe.other_changes == 5


@requires_git
def test_other_changes_zero_when_only_the_import_changed(tmp_path):
    repos = make_superproject(tmp_path / "git")

    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.other_changes == 0


@requires_git
def test_status_entries_rename_counts_once(tmp_path):
    repos = make_superproject(tmp_path / "git")
    repos.git(repos.custom, "mv", SYM_FFC, "Symbols/Renamed.kicad_sym")
    (repos.custom / "plain.txt").write_bytes(b"x\n")

    entries = gitops.status_entries(_ctx(), repos.custom)

    assert sorted(entries) == ["Symbols/Renamed.kicad_sym", "plain.txt"]


@requires_git
def test_earlier_commits_listed_oldest_first(tmp_path):
    repos = make_superproject(tmp_path / "git")
    first = commit_file(repos, repos.custom, "one.txt", b"1\n", "First")
    second = commit_file(repos, repos.custom, "two.txt", b"2\n", "Second")

    def short(rev):
        return repos.git(repos.custom, "rev-parse", "--short", rev).strip()

    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.earlier == ((short(first), "First"), (short(second), "Second"))
    assert probe.earlier_listed is True


@requires_git
def test_earlier_commits_none_when_gitlink_equals_head(tmp_path):
    repos = make_superproject(tmp_path / "git")

    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.gitlink_old == _head(repos)
    assert probe.earlier == () and probe.earlier_listed is True


@requires_git
def test_earlier_commits_unlisted_when_old_unknown(tmp_path):
    repos = make_superproject(tmp_path / "git")
    unknown = "1" * 40
    repos.git(repos.parent, "update-index", "--cacheinfo", f"160000,{unknown},Custom")
    repos.git(repos.parent, "commit", "-m", "Point Custom at a commit it does not have")

    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "ready" and probe.gitlink_old == unknown
    assert probe.earlier == () and probe.earlier_listed is False


@requires_git
def test_offer_switch_probe_also_reports_preexisting_state(tmp_path):
    repos = make_superproject(tmp_path / "git")
    _two_commits_on_main(repos)
    detach(repos, "main~2")
    (repos.custom / "scratch.txt").write_bytes(b"x\n")

    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "offer_switch"
    assert probe.other_changes == 1
    assert probe.earlier_listed is True and probe.dirty_before == frozenset()


@requires_git
def test_unavailable_probe_leaves_defaults(tmp_path):
    repos = make_superproject(tmp_path / "git")
    probe = commit_step.probe_commit(_plan(repos), git=_answering({"var": (128, b"")}))

    assert probe.state == "unavailable"
    assert probe.dirty_before == frozenset() and probe.other_changes == 0 and probe.earlier == ()


# -- refusals before any git write, and clean failures (D-03, D-06, D-11, D-16) -----------------------

HOOK_REJECT = "#!/bin/sh\necho 'hook says no'\necho 'on stderr' >&2\nexit 1\n"
MESSAGE = "Add FP1 to IC_Battery_Charger_TI"


def _subcommands(calls):
    return [argv[6] for argv in calls]


def _writes(calls):
    return [name for name in _subcommands(calls) if name in ("add", "reset", "commit")]


def _single_error(outcome, code):
    (issue,) = outcome.issues
    assert issue.severity is Severity.ERROR and issue.code == code, issue
    return issue


def _status(repos, repo=None):
    return repos.git(repo or repos.custom, "status", "--porcelain=v1", "-z", "-uall", "--ignored")


@requires_git
def test_run_commit_refuses_stale_file(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    (repos.custom / FP_NEW).write_bytes(b"edited in KiCad after the install\n")
    ctx, calls = _recording_ctx()
    before = _head(repos)

    outcome = commit_step.run_commit(plan, MESSAGE, True, git=ctx)

    assert outcome.custom_commit is None and outcome.failed
    issue = _single_error(outcome, "commit.stale_file")
    assert f"Custom/{FP_NEW}" in issue.text and "changed after the install" in issue.text
    assert _head(repos) == before
    assert _writes(calls) == []


@requires_git
def test_run_commit_refuses_deleted_file(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    (repos.custom / FP_NEW).unlink()

    outcome = commit_step.run_commit(plan, MESSAGE, False, git=_ctx())

    issue = _single_error(outcome, "commit.stale_file")
    assert f"Custom/{FP_NEW}" in issue.text


@requires_git
def test_run_commit_refuses_when_branch_changed(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    repos.git(repos.custom, "switch", "-c", "feature/z")
    ctx, calls = _recording_ctx()
    before = _head(repos)

    outcome = commit_step.run_commit(plan, MESSAGE, False, expected_branch="main", git=ctx)

    issue = _single_error(outcome, "commit.branch_changed")
    assert issue.text == "Custom's branch changed from main to feature/z since the check; nothing was committed"
    assert _head(repos) == before and _writes(calls) == []


@requires_git
def test_run_commit_refuses_detached_at_commit_time(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    detach(repos, "main")
    ctx, calls = _recording_ctx()

    outcome = commit_step.run_commit(plan, MESSAGE, False, expected_branch="main", git=ctx)

    issue = _single_error(outcome, "commit.refused")
    assert issue.text == "Not committed: Custom is on a detached HEAD."
    assert outcome.custom_commit is None and _writes(calls) == []


@requires_git
def test_run_commit_refuses_parent_not_ok_before_commit(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    repos.git(repos.parent, "switch", "--detach")
    ctx, calls = _recording_ctx()
    before = _head(repos)

    outcome = commit_step.run_commit(plan, MESSAGE, True, git=ctx)

    issue = _single_error(outcome, "commit.parent_unavailable")
    assert issue.text == (
        "Not committed: the parent repo is on a detached HEAD. Untick the parent option to commit in Custom only."
    )
    assert _head(repos) == before and _writes(calls) == []
    # the same state does not stop a Custom-only commit
    assert commit_step.run_commit(plan, MESSAGE, False, git=_ctx()).committed


@requires_git
def test_run_commit_refuses_ignored_path(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = import_files(repos, {"3DModels/x.tmp": b"scratch\n"})
    ctx, calls = _recording_ctx()
    status_before = _status(repos)
    before = _head(repos)

    outcome = commit_step.run_commit(plan, MESSAGE, False, git=ctx)

    issue = _single_error(outcome, "commit.ignored")
    assert "3DModels/x.tmp" in issue.text and "ignored by Custom's .gitignore" in issue.text
    assert _head(repos) == before and _writes(calls) == []
    assert _status(repos) == status_before


@requires_git
def test_custom_hook_rejection_undoes_intent(tmp_path):
    repos = make_superproject(tmp_path / "git")
    edited = (repos.custom / SYM_FFC).read_bytes() + b"; imported\n"
    plan = import_files(repos, {FP_NEW: b'(footprint "FP1")\n', SYM_FFC: edited})
    write_hook(repos, repos.custom, "pre-commit", HOOK_REJECT)
    ctx, calls = _recording_ctx()
    before = _head(repos)

    outcome = commit_step.run_commit(plan, MESSAGE, True, git=ctx)

    assert outcome.custom_commit is None and outcome.parent_commit is None
    issue = _single_error(outcome, "commit.custom_failed")
    for text in (issue.text, outcome.output):
        assert "hook says no" in text and "on stderr" in text
    assert _head(repos) == before
    assert f"?? {FP_NEW}" in repos.git(repos.custom, "status", "--porcelain=v1", "-uall").splitlines()
    assert _subcommands(calls).count("commit") == 1


@requires_git
def test_parent_hook_rejection_keeps_custom_commit(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    write_hook(repos, repos.parent, "pre-commit", "#!/bin/sh\necho 'parent hook says no'\nexit 1\n")
    ctx, calls = _recording_ctx()
    custom_before = _head(repos)
    parent_before = repos.git(repos.parent, "rev-parse", "HEAD").strip()

    outcome = commit_step.run_commit(plan, MESSAGE, True, git=ctx)

    assert outcome.custom_commit is not None and _head(repos) != custom_before
    assert outcome.parent_commit is None and repos.git(repos.parent, "rev-parse", "HEAD").strip() == parent_before
    issue = next(i for i in outcome.issues if i.code == "commit.parent_failed")
    assert issue.severity is Severity.ERROR
    assert "was kept" in issue.text and "parent hook says no" in issue.text and "Finish it by hand: git -C" in issue.text
    assert outcome.manual_command.endswith("-- Custom")
    assert outcome.manual_command in issue.text
    first_commit = _subcommands(calls).index("commit")
    assert "reset" not in _subcommands(calls)[first_commit:]


@requires_git
def test_commit_timeout_reported(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    calls = []

    def runner(argv, **kwargs):
        calls.append(list(argv))
        if argv[6] == "commit":
            raise subprocess.TimeoutExpired(argv, kwargs.get("timeout", 0))
        return subprocess.run(argv, **kwargs)

    before = _head(repos)

    outcome = commit_step.run_commit(plan, MESSAGE, True, git=GitContext(Path(GIT), runner))

    issue = _single_error(outcome, "commit.custom_failed")
    assert "did not finish within 300 s" in issue.text
    assert _subcommands(calls).count("commit") == 1 and _subcommands(calls).count("reset") == 1
    assert _head(repos) == before
    assert f"?? {FP_NEW}" in repos.git(repos.custom, "status", "--porcelain=v1", "-uall").splitlines()


@requires_git
def test_index_lock_reported(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    lock = git_path(repos, repos.custom, "index.lock")
    lock.write_bytes(b"")
    ctx, calls = _recording_ctx()
    before = _head(repos)

    outcome = commit_step.run_commit(plan, MESSAGE, False, git=ctx)

    issue = _single_error(outcome, "commit.custom_failed")
    assert "index.lock" in issue.text
    assert _head(repos) == before
    assert [name for name in _subcommands(calls) if name in ("add", "commit")] == ["add"]

    lock.unlink()
    assert commit_step.run_commit(plan, MESSAGE, False, git=_ctx()).committed


# -- exactly the listed files, bystanders untouched, names, messages (GIT-02, GIT-04, D-10, D-13, D-17, D-20) --

EM_DASH = "—"


def _entries(repos, repo, *paths):
    """The `status --porcelain` entries (XY code and path) of the named paths."""
    out = repos.git(repo, "status", "--porcelain=v1", "-z", "-uall")
    return sorted(entry for entry in out.split("\0") if entry[3:] in paths)


def _commit_names(repos, repo):
    return sorted(repos.git(repo, "show", "--name-only", "--format=", "-z", "HEAD").split("\0")[:-1])


def _body(repos, repo):
    return repos.git(repo, "log", "-1", "--format=%B").strip()


@requires_git
def test_commit_only_listed_files_with_bystanders(tmp_path):
    repos = make_superproject(tmp_path / "git")
    (repos.custom / "staged.txt").write_bytes(b"staged\n")
    repos.git(repos.custom, "add", "staged.txt")
    _edit_in_place(repos, SYM_USB)
    (repos.custom / "untracked.txt").write_bytes(b"untracked\n")
    bystanders = ("staged.txt", SYM_USB, "untracked.txt")
    before = _entries(repos, repos.custom, *bystanders)
    assert len(before) == 3
    plan = import_files(repos, {FP_NEW: b'(footprint "FP1")\n', SYM_FFC: (repos.custom / SYM_FFC).read_bytes() + b"; new\n"})

    outcome = commit_step.run_commit(plan, MESSAGE, False, git=_ctx())

    assert outcome.committed, outcome.issues
    assert _commit_names(repos, repos.custom) == sorted([FP_NEW, SYM_FFC])
    assert _entries(repos, repos.custom, *bystanders) == before


@requires_git
def test_parent_commit_only_gitlink_with_bystanders(tmp_path):
    repos = make_superproject(tmp_path / "git")
    (repos.parent / ".planning").mkdir()
    (repos.parent / ".planning" / "p.md").write_bytes(b"plan\n")
    repos.git(repos.parent, "add", ".planning/p.md")
    (repos.parent / "README.md").write_bytes(b"Parent fixture\nedited\n")
    (repos.parent / "notes.txt").write_bytes(b"notes\n")
    bystanders = (".planning/p.md", "README.md", "notes.txt")
    before = _entries(repos, repos.parent, *bystanders)
    assert len(before) == 3

    outcome = commit_step.run_commit(_plan(repos), MESSAGE, True, git=_ctx())

    assert outcome.parent_commit is not None, outcome.issues
    assert _commit_names(repos, repos.parent) == ["Custom"]
    assert _entries(repos, repos.parent, *bystanders) == before
    assert repos.git(repos.parent, "diff", "--cached", "--name-only").split() == [".planning/p.md"]


@requires_git
def test_already_staged_touched_file_committed_from_worktree(tmp_path):
    repos = make_superproject(tmp_path / "git")
    original = (repos.custom / SYM_FFC).read_bytes()
    (repos.custom / SYM_FFC).write_bytes(original + b"; staged earlier\n")
    repos.git(repos.custom, "add", SYM_FFC)
    (repos.custom / "other.txt").write_bytes(b"other\n")
    repos.git(repos.custom, "add", "other.txt")
    written = original + b"; written by the install\n"
    plan = import_files(repos, {SYM_FFC: written})

    outcome = commit_step.run_commit(plan, MESSAGE, False, git=_ctx())

    assert outcome.committed, outcome.issues
    assert gitops.head_blob(_ctx(), repos.custom, SYM_FFC) == written
    assert _entries(repos, repos.custom, SYM_FFC) == []
    assert _entries(repos, repos.custom, "other.txt") == ["A  other.txt"]


@requires_git
def test_single_file_commit(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    assert len(plan.files) == 1

    outcome = commit_step.run_commit(plan, MESSAGE, True, git=_ctx())

    assert outcome.committed and outcome.parent_commit is not None, outcome.issues
    assert _commit_names(repos, repos.custom) == [FP_NEW]
    assert _commit_names(repos, repos.parent) == ["Custom"]


@requires_git
def test_literal_pathspec_brackets(tmp_path):
    repos = make_superproject(tmp_path / "git")
    (repos.custom / "3DModels" / "AB1.step").write_bytes(b"decoy\n")
    plan = import_files(repos, {"3DModels/AB[1].step": b"model\n"})

    outcome = commit_step.run_commit(plan, MESSAGE, False, git=_ctx())

    assert outcome.committed, outcome.issues
    assert _commit_names(repos, repos.custom) == ["3DModels/AB[1].step"]
    assert _entries(repos, repos.custom, "3DModels/AB1.step") == ["?? 3DModels/AB1.step"]


@requires_git
def test_unicode_and_glob_names_committed(tmp_path):
    repos = make_superproject(tmp_path / "git")
    names = ["3DModels/Pièce 1+(a).step", "3DModels/Ω_part{1}.step"]
    plan = import_files(repos, {name: b"model\n" for name in names})

    outcome = commit_step.run_commit(plan, MESSAGE, False, git=_ctx())

    assert outcome.committed, outcome.issues
    assert sorted(gitops.commit_files(_ctx(), repos.custom)) == sorted(names)


@requires_git
def test_message_round_trip_and_trailers(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    message = default_message(plan)

    assert commit_step.run_commit(plan, message, False, git=_ctx()).committed
    assert _body(repos, repos.custom) == message.strip()
    trailers = repos.git(repos.custom, "log", "-1", "--format=%(trailers:only,unfold)").strip().splitlines()
    assert trailers == [
        "Import-Vendor: Ultra Librarian",
        "Import-Package: ul_PART1.zip",
        "Import-Date: 2026-10-22",
    ]

    other = import_files(repos, {"3DModels/m.step": b"model\n"})
    odd = f"Add m {EM_DASH} café\n\n# not a comment\nBody line"
    assert commit_step.run_commit(other, odd, False, git=_ctx()).committed
    assert _body(repos, repos.custom) == odd


@requires_git
def test_user_edited_message_verbatim(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)

    outcome = commit_step.run_commit(plan, "Tidy part\n\nHand-written body", False, git=_ctx())

    assert outcome.committed, outcome.issues
    body = _body(repos, repos.custom)
    assert body == "Tidy part\n\nHand-written body" and "Import-" not in body


@requires_git
def test_post_commit_file_check_reports_mismatch(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)

    def runner(argv, **kwargs):
        done = subprocess.run(argv, **kwargs)
        if argv[6] == "diff-tree":
            return subprocess.CompletedProcess(argv, done.returncode, stdout=done.stdout + b"Symbols/extra.kicad_sym\0", stderr=b"")
        return done

    outcome = commit_step.run_commit(plan, MESSAGE, False, git=GitContext(Path(GIT), runner))

    assert outcome.committed is True and outcome.failed is True
    issue = next(i for i in outcome.issues if i.code == "commit.unexpected_files")
    assert issue.severity is Severity.ERROR
    assert "Symbols/extra.kicad_sym" in issue.text and "was made" in issue.text
    assert outcome.custom_commit in issue.text or _short(repos) in issue.text


@requires_git
def test_parent_step_skipped_when_gitlink_equal(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    parent_before = repos.git(repos.parent, "rev-parse", "HEAD").strip()

    short, text, failure, issues = commit_step.commit_parent_ref(_ctx(), plan, "Subject")

    assert short is None and failure is None
    (issue,) = issues
    assert issue.severity is Severity.INFO and issue.code == "commit.parent_skipped"
    assert issue.text == f"The parent repo already points at Custom {_head(repos)[:7]}; no parent commit was needed"
    assert repos.git(repos.parent, "rev-parse", "HEAD").strip() == parent_before


@requires_git
def test_parent_message_lists_covered_commits(tmp_path):
    repos = make_superproject(tmp_path / "git")
    old = repos.git(repos.parent, "rev-parse", "HEAD:Custom").strip()
    first = commit_file(repos, repos.custom, "one.txt", b"1\n", "First")
    second = commit_file(repos, repos.custom, "two.txt", b"2\n", "Second")
    plan = _plan(repos)
    message = default_message(plan)

    outcome = commit_step.run_commit(plan, message, True, git=_ctx())

    assert outcome.parent_commit is not None, outcome.issues

    def short(rev):
        return repos.git(repos.custom, "rev-parse", "--short", rev).strip()

    subject = subject_of(message)
    assert outcome.parent_message.splitlines() == [
        f"Update Custom: {subject}",
        "",
        f"Custom {old[:7]}..{_head(repos)[:7]}",
        f"- {short(first)} First",
        f"- {short(second)} Second",
        f"- {outcome.custom_commit} {subject}",
    ]
    assert _body(repos, repos.parent) == outcome.parent_message.strip()


@requires_git
def test_ahead_counts_and_not_pushed_lines(tmp_path):
    repos = make_superproject(tmp_path / "git")

    outcome = commit_step.run_commit(_plan(repos), MESSAGE, True, git=_ctx())

    assert outcome.custom_upstream == "origin/main" and outcome.custom_ahead == 1
    assert outcome.parent_upstream == "origin/main" and outcome.parent_ahead == 1
    infos = [i.text for i in outcome.issues if i.severity is Severity.INFO]
    assert infos == [
        f"Not pushed {EM_DASH} Custom is 1 commit ahead of origin/main (as last fetched)",
        f"Not pushed {EM_DASH} the parent repo is 1 commit ahead of origin/main (as last fetched)",
    ]

    other = make_superproject(tmp_path / "git_b")
    other.git(other.custom, "switch", "-c", "feature/z")
    alone = commit_step.run_commit(_plan(other), MESSAGE, False, git=_ctx())
    assert [i.text for i in alone.issues if i.severity is Severity.INFO] == [
        f"Not pushed {EM_DASH} feature/z in Custom has no upstream"
    ]


@requires_git
def test_pre_import_diff_head_vs_backup(tmp_path):
    repos = make_superproject(tmp_path / "git")
    head_bytes = (repos.custom / SYM_FFC).read_bytes()
    first, _, rest = head_bytes.partition(b"\n")
    (repos.custom / SYM_FFC).write_bytes(first + b" ; edited before the import\n" + rest)
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "Connector_FFC_GCT.kicad_sym_backup_1").write_bytes((repos.custom / SYM_FFC).read_bytes())
    plan = import_files(repos, {SYM_FFC: (repos.custom / SYM_FFC).read_bytes() + b"; imported\n"})
    plan = dataclasses.replace(plan, backup_dir=backup)

    content = commit_step.pre_import_diff(plan, SYM_FFC, git=_ctx())

    assert content.kind == "diff"
    assert content.title == f"Custom/{SYM_FFC} - HEAD vs before this import"
    lines = content.body.splitlines()
    assert any(line.startswith("-") and not line.startswith("---") for line in lines)
    assert any(line.startswith("+") and "; edited before the import" in line for line in lines)
    assert not any("; imported" in line for line in lines)

    empty = tmp_path / "empty_backup"
    empty.mkdir()
    missing = commit_step.pre_import_diff(dataclasses.replace(plan, backup_dir=empty), SYM_FFC, git=_ctx())
    assert missing.kind == "error" and str(empty) in missing.body


@requires_git
def test_pre_import_diff_model_is_binary(tmp_path):
    repos = make_superproject(tmp_path / "git")
    commit_file(repos, repos.custom, MODEL_OLD, b"head model\n", "Add a model")
    (repos.custom / MODEL_OLD).write_bytes(b"edited model\n")
    backup = tmp_path / "backup"
    backup.mkdir()
    (backup / "old.step_backup_1").write_bytes(b"edited model\n")
    plan = dataclasses.replace(import_files(repos, {MODEL_OLD: b"imported model\n"}), backup_dir=backup)

    content = commit_step.pre_import_diff(plan, MODEL_OLD, git=_ctx())

    assert content.kind == "binary"
    assert hashlib.sha256(b"head model\n").hexdigest() in content.body
    assert hashlib.sha256(b"edited model\n").hexdigest() in content.body
