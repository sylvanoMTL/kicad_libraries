"""commit_step against real git: the detached-HEAD policy and the switch to main (Phase 6, GIT-03, D-14, D-15).

Each test builds a throwaway superproject (two bare remotes, a parent, a Custom submodule) and
puts Custom in the state under test. Nothing here touches the real repository.
"""

import dataclasses
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from customfixtures import atomic_lib, atomic_part, digest_custom, write_atomic_files
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
    populate_custom,
    requires_git,
    start_merge_conflict,
    write_hook,
)
from installfixtures import vendor_footprint
from zipfixtures import STEP_BYTES, footprint_library_for

from kicad_lib_manager import gitops
from kicad_lib_manager.gitops import GitContext
from kicad_lib_manager.importer import commit_plan, commit_step
from kicad_lib_manager.importer.commit_plan import NEW_PLACEHOLDER, default_message, parent_preview, subject_of
from kicad_lib_manager.models import Severity

LIB = "Atomic_Battery_Management"
FFC_LIB = "Atomic_Connector_Audio"
USB_LIB = "Atomic_Connector"
FP_NEW = f"Footprints/{footprint_library_for(LIB)}.pretty/FP1.kicad_mod"
SYM_FFC = f"Symbols/{FFC_LIB}.kicad_sym"
SYM_USB = f"Symbols/{USB_LIB}.kicad_sym"
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


def _no_gitlink_ctx():
    """A context whose ls-tree answers exit 0 with nothing, so the parent seems to record no Custom gitlink."""

    def runner(argv, **kwargs):
        if "ls-tree" in argv:
            return subprocess.CompletedProcess(argv, 0, stdout=b"", stderr=b"")
        return subprocess.run(argv, **kwargs)

    return GitContext(Path(GIT), runner)


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
    assert probe.reason == IDENTITY_REASON
    assert _issue_triples(probe) == _unavailable_issue(probe.reason)


@requires_git
def test_probe_identity_known_by_default(tmp_path):
    repos = make_superproject(tmp_path / "git")

    assert commit_step.probe_commit(_plan(repos), git=_ctx()).state == "ready"


IDENTITY_REASON = (
    "git does not know who you are: set user.name and user.email, or "
    "GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL, GIT_COMMITTER_NAME and GIT_COMMITTER_EMAIL"
)
_IDENTITY_VARS = (
    "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE",
    "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "GIT_COMMITTER_DATE",
)  # fmt: skip
_ENV_AUTHOR = {"GIT_AUTHOR_NAME": "Env Author", "GIT_AUTHOR_EMAIL": "author@example.invalid"}
_ENV_COMMITTER = {"GIT_COMMITTER_NAME": "Env Committer", "GIT_COMMITTER_EMAIL": "committer@example.invalid"}


def _isolate_identity(monkeypatch, repos, home):
    """No identity in any config: the repo-local one is removed, HOME is empty and the variables are unset."""
    home.mkdir(parents=True, exist_ok=True)
    repos.git(repos.custom, "config", "--unset", "user.name")
    repos.git(repos.custom, "config", "--unset", "user.email")
    repos.git(repos.custom, "config", "user.useConfigOnly", "true")
    for name in ("HOME", "USERPROFILE", "XDG_CONFIG_HOME"):
        monkeypatch.setenv(name, str(home))
    monkeypatch.delenv("EMAIL", raising=False)
    for name in _IDENTITY_VARS:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)


@requires_git
def test_probe_identity_message_names_variables(tmp_path, monkeypatch):
    repos = make_superproject(tmp_path / "git")
    _isolate_identity(monkeypatch, repos, tmp_path / "home")

    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "unavailable"
    assert probe.reason == IDENTITY_REASON
    assert "GIT_AUTHOR_NAME" in probe.reason and "user.name" in probe.reason


@requires_git
def test_env_identity_probe_and_commit(tmp_path, monkeypatch):
    repos = make_superproject(tmp_path / "git")
    _isolate_identity(monkeypatch, repos, tmp_path / "home")
    for name, value in {**_ENV_AUTHOR, **_ENV_COMMITTER}.items():
        monkeypatch.setenv(name, value)
    plan = _plan(repos)

    probe = commit_step.probe_commit(plan, git=_ctx())
    outcome = commit_step.run_commit(plan, MESSAGE, True, git=_ctx())

    assert probe.state == "ready", probe.reason
    assert not outcome.failed, outcome.issues
    assert outcome.custom_commit is not None and outcome.parent_commit is not None
    assert repos.git(repos.custom, "log", "-1", "--format=%an <%ae>").strip() == "Env Author <author@example.invalid>"
    assert repos.git(repos.parent, "log", "-1", "--format=%an <%ae>").strip() == "Env Author <author@example.invalid>"


@requires_git
def test_probe_with_only_committer_variables_is_unavailable(tmp_path, monkeypatch):
    repos = make_superproject(tmp_path / "git")
    _isolate_identity(monkeypatch, repos, tmp_path / "home")
    for name, value in _ENV_COMMITTER.items():
        monkeypatch.setenv(name, value)

    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "unavailable"
    assert probe.reason == IDENTITY_REASON  # no more "ready" followed by a failed commit


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

    outcome = commit_step.run_commit(plan, f"Add FP1 to {LIB}", True, git=_ctx())

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
    assert probe.stale == () and probe.identical == frozenset() and probe.all_identical is False and probe.gate is None


# -- stale and identical files, and the cancel hook, known before any click (D-08, D-09, D-13, IN-02) -------


@requires_git
def test_probe_stale_file_is_gated(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    (repos.custom / FP_NEW).write_bytes(b"edited in KiCad after the install\n")

    probe = commit_step.probe_commit(plan, git=_ctx())

    assert probe.state == "gated"
    assert probe.stale == (f"Custom/{FP_NEW}",)
    assert probe.branch == "main" and probe.head == _head(repos) and probe.parent_ok
    assert probe.reason == commit_step.stale_text(probe.stale)
    assert f"Custom/{FP_NEW}" in probe.reason and "Click Check again" in probe.reason


@requires_git
def test_probe_unchanged_files_are_not_gated(tmp_path):
    repos = make_superproject(tmp_path / "git")

    probe = commit_step.probe_commit(_plan(repos), git=_ctx())

    assert probe.state == "ready" and probe.stale == ()


@requires_git
@pytest.mark.parametrize("autocrlf", [True, False])
def test_probe_reports_identical_files(tmp_path, autocrlf):
    repos = make_superproject(tmp_path / "git", autocrlf=autocrlf)
    plan = import_files(repos, {FP_NEW: b'(footprint "FP1")\n', SYM_FFC: _same_as_head(repos)})

    probe = commit_step.probe_commit(plan, git=_ctx())

    assert probe.state == "ready"
    assert probe.identical == frozenset({SYM_FFC}) and probe.all_identical is False


@requires_git
@pytest.mark.parametrize("autocrlf", [True, False])
def test_probe_all_identical(tmp_path, autocrlf):
    repos = make_superproject(tmp_path / "git", autocrlf=autocrlf)
    plan = import_files(repos, {SYM_FFC: _same_as_head(repos)})

    probe = commit_step.probe_commit(plan, git=_ctx())

    assert probe.identical == frozenset({SYM_FFC}) and probe.all_identical is True


@requires_git
def test_probe_cancelled_returns_unavailable(tmp_path):
    repos = make_superproject(tmp_path / "git")
    ctx, calls = _recording_ctx()

    probe = commit_step.probe_commit(_plan(repos), git=ctx, cancelled=lambda: True)

    assert probe.state == "unavailable" and probe.reason == "The check was cancelled"
    assert commit_step.CANCELLED_REASON == "The check was cancelled"
    assert not {"status", "cat-file"} & set(_subcommands(calls))


@requires_git
def test_probe_cancelled_after_three_git_calls_stops_early(tmp_path):
    repos = make_superproject(tmp_path / "git")
    ctx, calls = _recording_ctx()

    probe = commit_step.probe_commit(_plan(repos), git=ctx, cancelled=lambda: len(calls) >= 3)

    assert probe.state == "unavailable" and probe.reason == "The check was cancelled"
    assert not {"status", "cat-file"} & set(_subcommands(calls))
    full, full_calls = _recording_ctx()
    assert commit_step.probe_commit(_plan(repos), git=full).state == "ready"
    assert len(calls) < len(full_calls)


@requires_git
def test_probe_cancelled_between_preexisting_reads(tmp_path):
    repos = make_superproject(tmp_path / "git")
    ctx, calls = _recording_ctx()

    probe = commit_step.probe_commit(_plan(repos), git=ctx, cancelled=lambda: "status" in _subcommands(calls))

    assert probe.state == "unavailable" and probe.reason == "The check was cancelled"
    assert "cat-file" not in _subcommands(calls)


# -- refusals before any git write, and clean failures (D-03, D-06, D-11, D-16) -----------------------

HOOK_REJECT = "#!/bin/sh\necho 'hook says no'\necho 'on stderr' >&2\nexit 1\n"
MESSAGE = f"Add FP1 to {LIB}"
_CUSTOM_ARG = "-- 'Custom'" if sys.platform == "win32" else "-- Custom"  # the running platform's quoting


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
    label = commit_step.manual_label()
    assert "was kept" in issue.text and "parent hook says no" in issue.text
    assert f"{label} git -C" in issue.text
    assert outcome.manual_label == label
    assert outcome.manual_command.endswith(_CUSTOM_ARG)
    assert outcome.manual_command in issue.text
    first_commit = _subcommands(calls).index("commit")
    assert "reset" not in _subcommands(calls)[first_commit:]


# -- the "Finish it by hand" command, written for the shell it is pasted into (REV-08, D-16) ----------

_TRICKY_SUBJECT = "Update Custom: it's $x, then a `tick`, a mid\\string and z $(calc)"
_TRICKY_MESSAGE = f"{_TRICKY_SUBJECT}\n\nCustom abc1234..def5678\n- def5678 Add 'P'"


def test_manual_command_powershell_quotes_every_argument():
    parent = Path("C:/Repo O'Neil")

    command = commit_step.manual_command(parent, "Custom", _TRICKY_MESSAGE, windows=True)

    subject = _TRICKY_SUBJECT.replace("'", "''")
    assert command == f"git -C 'C:/Repo O''Neil' commit -m '{subject}' -- 'Custom'"


def test_manual_command_posix_uses_shlex():
    parent = Path("/home/o'neil/Repo")

    command = commit_step.manual_command(parent, "Custom", _TRICKY_MESSAGE, windows=False)

    q = shlex.quote
    assert command == f"git -C {q(parent.as_posix())} commit -m {q(_TRICKY_SUBJECT)} -- {q('Custom')}"
    assert shlex.split(command) == ["git", "-C", parent.as_posix(), "commit", "-m", _TRICKY_SUBJECT, "--", "Custom"]


_DQUOTE_MESSAGE = 'Update Custom: Add "Foo"\n\nCustom abc..def\n- abc Add "Foo"'


def test_manual_command_uses_message_file_for_double_quote(tmp_path):
    parent = Path("C:/Repo")

    command = commit_step.manual_command(parent, "Custom", _DQUOTE_MESSAGE, windows=True, message_dir=tmp_path)

    match = re.fullmatch(r"git -C 'C:/Repo' commit -F '([^']+)' -- 'Custom'", command)
    assert match, command
    written = Path(match.group(1))
    assert "\\" not in match.group(1) and written.suffix == ".txt" and written.parent == tmp_path
    assert written.read_bytes() == _DQUOTE_MESSAGE.encode("utf-8")
    assert '"' not in command


def test_manual_command_uses_message_file_for_trailing_backslash(tmp_path):
    message = "Update Custom: copy to C:\\data\\\n\nbody line"

    command = commit_step.manual_command(Path("C:/Repo"), "Custom", message, windows=True, message_dir=tmp_path)

    assert " -F '" in command and " -m " not in command
    (written,) = tmp_path.iterdir()
    assert written.read_bytes() == message.encode("utf-8")


def test_manual_command_unicode_message_is_written_as_utf8(tmp_path):
    message = 'Update Custom: Add "Zürich" \u2713'

    command = commit_step.manual_command(Path("C:/Repo"), "Custom", message, windows=True, message_dir=tmp_path)

    assert " -F '" in command
    (written,) = tmp_path.iterdir()
    assert written.read_bytes().decode("utf-8") == message


def test_manual_command_posix_never_writes_a_file(tmp_path):
    command = commit_step.manual_command(
        Path("/repo"), "Custom", _DQUOTE_MESSAGE, windows=False, message_dir=tmp_path
    )

    assert " -m " in command and " -F " not in command
    assert shlex.split(command)[5] == 'Update Custom: Add "Foo"'
    assert list(tmp_path.iterdir()) == []


def test_manual_command_falls_back_to_m_form_when_the_file_cannot_be_written(tmp_path):
    missing = tmp_path / "no" / "such" / "folder"

    command = commit_step.manual_command(Path("C:/Repo"), "Custom", _DQUOTE_MESSAGE, windows=True, message_dir=missing)

    assert " -m " in command and " -F " not in command


_ECHO_SCRIPT = (
    "import json, os, sys\n"
    "with open(os.environ['KICAD_ECHO_OUT'], 'w', encoding='utf-8') as handle:\n"
    "    json.dump(sys.argv[1:], handle)\n"
)
_POWERSHELL_SUBJECTS = (
    "Update Custom: it's here",
    "Update Custom: cost $x and $(calc)",
    "Update Custom: a `tick` here",
    "Update Custom: back\\slash in the middle",
    'Update Custom: Add "Foo" part',
    "Update Custom: ends with a slash\\",
    "Update Custom: it\u2019s typographic",
)


@pytest.mark.skipif(
    shutil.which("powershell") is None,
    reason="Windows PowerShell not found (the paste-safety test runs the generated command in it)",
)
@pytest.mark.parametrize("subject", _POWERSHELL_SUBJECTS)
def test_manual_command_survives_real_powershell(subject, tmp_path):
    parent = tmp_path / "parent repo"
    message = f"{subject}\n\nCustom abc1234..def5678\n- def5678 {subject}"
    script = tmp_path / "echo_args.py"
    script.write_text(_ECHO_SCRIPT, encoding="utf-8")
    out = tmp_path / "received.json"
    command = commit_step.manual_command(parent, "Custom", message, windows=True, message_dir=tmp_path)
    assert command.startswith("git ")
    line = f"& {commit_step._ps_quote(sys.executable)} {commit_step._ps_quote(str(script))} {command[len('git '):]}"

    done = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", line],
        env={**os.environ, "KICAD_ECHO_OUT": str(out)},
        capture_output=True, timeout=60,
    )

    assert done.returncode == 0, done.stderr.decode("utf-8", errors="replace")
    received = json.loads(out.read_text(encoding="utf-8"))
    if "-F" in received:
        file = Path(received[received.index("-F") + 1])
        assert received == ["-C", parent.as_posix(), "commit", "-F", file.as_posix(), "--", "Custom"]
        assert file.read_bytes().decode("utf-8") == message
        assert file.parent != parent and not file.is_relative_to(parent)
    else:
        assert received == ["-C", parent.as_posix(), "commit", "-m", subject, "--", "Custom"]


def test_manual_label_names_the_shell():
    assert commit_step.manual_label(windows=True) == "Finish it by hand. In PowerShell:"
    assert commit_step.manual_label(windows=False) == "Finish it by hand:"
    assert commit_step.manual_label() == commit_step.manual_label(windows=sys.platform == "win32")


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


def _late_timeout_ctx():
    """A context whose commit runs for real and then reports a timeout, like a hook that outlived the limit."""
    calls = []

    def runner(argv, **kwargs):
        calls.append(list(argv))
        done = subprocess.run(argv, **kwargs)
        if argv[6] == "commit" and "-F" in argv and "--pathspec-from-file=-" in argv:
            raise subprocess.TimeoutExpired(argv, kwargs.get("timeout", 0))
        return done

    return GitContext(Path(GIT), runner), calls


UNFINISHED = "Committed {short} in Custom, but git did not finish in time (a hook or signing step may still be running)"


@requires_git
def test_commit_timeout_after_head_moved_reports_commit(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    ctx, calls = _late_timeout_ctx()
    parent_before = repos.git(repos.parent, "rev-parse", "HEAD").strip()

    outcome = commit_step.run_commit(plan, MESSAGE, True, git=ctx)

    assert outcome.committed and outcome.custom_commit == _short(repos)
    assert not outcome.failed
    (warning,) = [i for i in outcome.issues if i.code == "commit.custom_unfinished"]
    assert warning.severity is Severity.WARNING
    assert warning.text == UNFINISHED.format(short=_short(repos))
    first_commit = _subcommands(calls).index("commit")
    assert "reset" not in _subcommands(calls)[first_commit:]
    assert repos.git(repos.parent, "rev-parse", "HEAD").strip() == parent_before
    assert outcome.parent_commit is None and "commit" not in _subcommands(calls)[first_commit + 1 :]
    assert outcome.manual_command and outcome.manual_command.endswith(_CUSTOM_ARG)
    assert outcome.manual_label == commit_step.manual_label()
    assert outcome.parent_message.startswith("Update Custom: ")
    parent_warning = next(i for i in outcome.issues if i.code == "commit.parent_not_started")
    assert parent_warning.severity is Severity.WARNING
    assert f"{outcome.manual_label} {outcome.manual_command}" in parent_warning.text


@requires_git
def test_commit_timeout_after_head_moved_without_parent(tmp_path):
    repos = make_superproject(tmp_path / "git")
    ctx, _ = _late_timeout_ctx()

    outcome = commit_step.run_commit(_plan(repos), MESSAGE, False, git=ctx)

    assert outcome.committed and not outcome.failed
    assert outcome.manual_command == "" and outcome.parent_message == ""
    assert [i.code for i in outcome.issues if i.severity is Severity.WARNING] == ["commit.custom_unfinished"]


@requires_git
def test_commit_slow_post_commit_hook_reports_commit(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    write_hook(repos, repos.custom, "post-commit", "#!/bin/sh\nsleep 5\n")
    calls = []

    def runner(argv, **kwargs):
        calls.append(list(argv))
        if argv[6] == "commit" and "-F" in argv and "--pathspec-from-file=-" in argv:
            kwargs["timeout"] = 2  # a real timeout while the hook still sleeps
        return subprocess.run(argv, **kwargs)

    before = _head(repos)

    outcome = commit_step.run_commit(plan, MESSAGE, False, git=GitContext(Path(GIT), runner))

    assert _head(repos) != before
    assert outcome.committed and outcome.custom_commit == _short(repos)
    (warning,) = [i for i in outcome.issues if i.code == "commit.custom_unfinished"]
    assert warning.text == UNFINISHED.format(short=_short(repos))
    first_commit = _subcommands(calls).index("commit")
    assert "reset" not in _subcommands(calls)[first_commit:]


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


ALREADY = "Already identical to HEAD, not in the commit: "


def _same_as_head(repos, rel=SYM_FFC):
    """The install rewrote this file with the very bytes HEAD holds."""
    return (repos.custom / rel).read_bytes()


@requires_git
def test_identical_planned_file_is_info_and_parent_bumps(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = import_files(repos, {FP_NEW: b'(footprint "FP1")\n', SYM_FFC: _same_as_head(repos)})

    outcome = commit_step.run_commit(plan, MESSAGE, True, git=_ctx())

    assert not outcome.failed, outcome.issues
    info = next(i for i in outcome.issues if i.code == "commit.already_in_head")
    assert info.severity is Severity.INFO and info.text == ALREADY + f"Custom/{SYM_FFC}"
    assert any(i.code == "commit.custom_done" and i.severity is Severity.SUCCESS for i in outcome.issues)
    assert outcome.committed and outcome.parent_commit is not None and outcome.parent_only is False
    assert repos.git(repos.custom, "show", "--name-only", "--format=", "HEAD").split() == [FP_NEW]


@requires_git
def test_all_identical_without_parent_refuses(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = import_files(repos, {SYM_FFC: _same_as_head(repos)})
    ctx, calls = _recording_ctx()
    before = _head(repos)

    outcome = commit_step.run_commit(plan, MESSAGE, False, git=ctx)

    issue = _single_error(outcome, "commit.nothing_to_commit")
    assert issue.text == "Not committed: Custom already holds these files."
    assert outcome.custom_commit is None and _head(repos) == before
    assert [name for name in _subcommands(calls) if name in ("add", "commit", "reset")] == []


@requires_git
def test_all_identical_parent_only_bump(tmp_path):
    repos = make_superproject(tmp_path / "git")
    old = repos.git(repos.parent, "rev-parse", "HEAD:Custom").strip()
    commit_file(repos, repos.custom, "late.txt", b"late\n", "Late commit")
    plan = import_files(repos, {SYM_FFC: _same_as_head(repos)})
    ctx, calls = _recording_ctx()
    custom_before = _head(repos)

    outcome = commit_step.run_commit(plan, MESSAGE, True, git=ctx)

    assert not outcome.failed, outcome.issues
    assert outcome.parent_only is True and outcome.custom_commit is None and not outcome.committed
    assert outcome.parent_commit is not None
    assert _head(repos) == custom_before
    assert _subcommands(calls).count("commit") == 1 and "add" not in _subcommands(calls)
    assert any(i.code == "commit.already_in_head" and i.severity is Severity.INFO for i in outcome.issues)
    assert outcome.parent_message.splitlines() == [
        f"Update Custom: {MESSAGE}",
        "",
        f"Custom {old[:7]}..{_head(repos)[:7]}",
        f"- {_short(repos)} Late commit",
    ]
    assert _body(repos, repos.parent) == outcome.parent_message.strip()


@requires_git
def test_all_identical_parent_only_failure_has_manual_command(tmp_path):
    repos = make_superproject(tmp_path / "git")
    commit_file(repos, repos.custom, "late.txt", b"late\n", "Late commit")
    plan = import_files(repos, {SYM_FFC: _same_as_head(repos)})
    write_hook(repos, repos.parent, "pre-commit", "#!/bin/sh\necho 'parent hook says no'\nexit 1\n")

    outcome = commit_step.run_commit(plan, MESSAGE, True, git=_ctx())

    issue = next(i for i in outcome.issues if i.code == "commit.parent_failed")
    assert issue.text.startswith("The parent commit failed (") and f"{commit_step.manual_label()} git -C" in issue.text
    assert "was kept" not in issue.text and outcome.parent_only is True
    assert outcome.manual_command.endswith(_CUSTOM_ARG)


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
@pytest.mark.parametrize("gitlink", [True, False], ids=["gitlink", "no_gitlink"])
def test_parent_preview_equals_committed_message(tmp_path, gitlink):
    repos = make_superproject(tmp_path / "git")
    commit_file(repos, repos.custom, "one.txt", b"1\n", "First")
    commit_file(repos, repos.custom, "two.txt", b"2\n", "Second")
    plan = _plan(repos)
    message = default_message(plan)
    ctx = _ctx() if gitlink else _no_gitlink_ctx()

    probe = commit_step.probe_commit(plan, git=ctx)
    preview = parent_preview(
        subject_of(message), "Custom", probe.gitlink_old, probe.earlier, listed=probe.earlier_listed
    )
    outcome = commit_step.run_commit(plan, message, True, git=ctx)

    assert (probe.gitlink_old is not None) is gitlink
    assert outcome.parent_commit is not None, outcome.issues
    assert preview.replace(NEW_PLACEHOLDER, outcome.custom_commit) == outcome.parent_message
    assert _body(repos, repos.parent) == outcome.parent_message.strip()
    assert "could not be listed" not in outcome.parent_message
    assert outcome.parent_message.splitlines()[-1] == f"- {outcome.custom_commit} {subject_of(message)}"


@requires_git
def test_earlier_none_gitlink_is_listed(tmp_path):
    repos = make_superproject(tmp_path / "git")
    head = _head(repos)

    assert commit_step._earlier(_ctx(), _plan(repos), None, head) == ((), True)
    assert commit_step._earlier(_ctx(), _plan(repos), head, "") == ((), False)


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
    (backup / f"{FFC_LIB}.kicad_sym_backup_1").write_bytes((repos.custom / SYM_FFC).read_bytes())
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


# -- the atomic gate in the probe and again at the click (Phase 11, GIT-06, D-03, D-09) ---------------------

GATE_LIB = "Atomic_Gate_Test"
GATE_REL = f"Symbols/{GATE_LIB}.kicad_sym"


def _populate_atomic(custom):
    populate_custom(custom)
    write_atomic_files(custom)


def _atomic_repos(tmp_path):
    return make_superproject(tmp_path / "git", populate=_populate_atomic)


def _gate_plan(repos, *parts, head_parts=None):
    """Commit head_parts as the library's HEAD content, then stand in for an install that wrote parts."""
    if head_parts is not None:
        commit_file(repos, repos.custom, GATE_REL, atomic_lib(head_parts), "Add the first parts")
    return import_files(repos, {GATE_REL: atomic_lib(parts)}, library=GATE_LIB, symbol=parts[-1].name)


@requires_git
def test_probe_gated_and_click_refused_for_failing_part(tmp_path):
    repos = _atomic_repos(tmp_path)
    good = atomic_part("PASSING-1")
    plan = _gate_plan(repos, good, atomic_part("LIS3MDL", drop=("Datasheet",)), head_parts=(good,))
    custom_head, parent_head = _head(repos), repos.git(repos.parent, "rev-parse", "HEAD").strip()

    probe = commit_step.probe_commit(plan, git=_ctx())

    assert probe.state == "gated"
    assert probe.gate is not None and probe.gate.blocking[0].part == "LIS3MDL"
    assert probe.reason.startswith("1 part breaks the atomic rule")
    errors = [issue for issue in probe.issues if issue.severity is Severity.ERROR]
    assert [issue.code for issue in errors] == ["commit.atomic.datasheet"]

    ctx, calls = _recording_ctx()
    outcome = commit_step.run_commit(plan, MESSAGE, True, git=ctx)

    assert outcome.custom_commit is None and outcome.failed
    issue = _single_error(outcome, "commit.atomic")
    assert f"{GATE_LIB} / LIS3MDL: " in issue.text and issue.text.startswith("Not committed: 1 part breaks the atomic rule")
    assert _writes(calls) == []
    assert _head(repos) == custom_head
    assert repos.git(repos.parent, "rev-parse", "HEAD").strip() == parent_head


@requires_git
def test_probe_old_failure_stays_ready_and_commits(tmp_path):
    repos = _atomic_repos(tmp_path)
    old = atomic_part("OLD-1", drop=("Datasheet",))
    plan = _gate_plan(repos, old, atomic_part("NEW-Q"), head_parts=(old,))

    probe = commit_step.probe_commit(plan, git=_ctx())

    assert probe.state == "ready" and probe.gate is not None and probe.gate.refused is False
    warnings = [issue for issue in probe.issues if issue.code.startswith("commit.atomic_old.")]
    assert warnings and all(issue.severity is Severity.WARNING for issue in warnings)
    outcome = commit_step.run_commit(plan, MESSAGE, False, git=_ctx())
    assert outcome.committed and not outcome.failed


@requires_git
def test_precheck_stale_points_to_check_again(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = _plan(repos)
    (repos.custom / FP_NEW).write_bytes(b"edited in KiCad after the install\n")

    outcome = commit_step.run_commit(plan, MESSAGE, True, git=_ctx())

    issue = _single_error(outcome, "commit.stale_file")
    assert "Click Check again" in issue.text and "commit by hand" not in issue.text
    assert f"Custom/{FP_NEW}" in issue.text


# -- Check again: re-baseline the changed files, judge the new content, show what changed (D-08, D-09) ----


def _edited_plan(tmp_path):
    """An atomic superproject whose install wrote one new part; returns (repos, good part, plan)."""
    repos = _atomic_repos(tmp_path)
    good = atomic_part("PASSING-1")
    plan = _gate_plan(repos, good, atomic_part("NEW-A"), head_parts=(good,))
    return repos, good, plan


def _planned(plan, rel=GATE_REL):
    return next(f for f in plan.files if f.rel == rel)


@requires_git
def test_recheck_rebaselines_then_commits(tmp_path):
    repos, good, plan = _edited_plan(tmp_path)
    edited = atomic_lib((good, atomic_part("NEW-B")))
    (repos.custom / GATE_REL).write_bytes(edited)
    ctx = _ctx()
    assert commit_step.probe_commit(plan, git=ctx).state == "gated"

    new_plan, probe = commit_step.recheck_commit(plan, git=ctx)

    changed = _planned(new_plan)
    assert changed.note == "changed" and changed.expected_sha256 == hashlib.sha256(edited).hexdigest()
    assert changed.installed == _planned(plan).installed
    assert probe.state == "ready" and probe.stale == ()
    outcome = commit_step.run_commit(new_plan, MESSAGE, False, git=ctx)
    assert outcome.committed and not outcome.failed
    assert gitops.head_blob(ctx, repos.custom, GATE_REL) == edited


@requires_git
def test_recheck_gate_runs_on_new_content(tmp_path):
    repos, good, plan = _edited_plan(tmp_path)
    (repos.custom / GATE_REL).write_bytes(atomic_lib((good, atomic_part("NEW-B", drop=("Datasheet",)))))

    _, probe = commit_step.recheck_commit(plan, git=_ctx())

    assert probe.state == "gated" and probe.stale == ()
    assert probe.gate is not None and [f.part for f in probe.gate.blocking] == ["NEW-B"]


@requires_git
def test_change_after_recheck_refused_again(tmp_path):
    repos, good, plan = _edited_plan(tmp_path)
    (repos.custom / GATE_REL).write_bytes(atomic_lib((good, atomic_part("NEW-B"))))
    ctx, calls = _recording_ctx()
    new_plan, probe = commit_step.recheck_commit(plan, git=ctx)
    assert probe.state == "ready"

    (repos.custom / GATE_REL).write_bytes(atomic_lib((good, atomic_part("NEW-C"))))
    outcome = commit_step.run_commit(new_plan, MESSAGE, True, git=ctx)

    issue = _single_error(outcome, "commit.stale_file")
    assert "Click Check again" in issue.text
    assert _writes(calls) == []


@requires_git
def test_recheck_writes_nothing(tmp_path):
    repos, good, plan = _edited_plan(tmp_path)
    (repos.custom / GATE_REL).write_bytes(atomic_lib((good, atomic_part("NEW-B"))))
    before = digest_custom(repos.custom)
    heads = (_head(repos), repos.git(repos.parent, "rev-parse", "HEAD").strip())
    ctx, calls = _recording_ctx()

    commit_step.recheck_commit(plan, git=ctx)

    assert not {"add", "reset", "commit", "switch"} & set(_subcommands(calls))
    assert digest_custom(repos.custom) == before
    assert (_head(repos), repos.git(repos.parent, "rev-parse", "HEAD").strip()) == heads


# -- Check again takes the files a fix created that a committed part links (Phase 11, D-10) -----------------

NEWFP_REL = "Footprints/Atomic_Footprints.pretty/NEWFP.kicad_mod"
NEWFP_STEP = "3DModels/NEWFP.step"


def _newfp_plan(repos, *, with_model=True):
    """An install that wrote a part linking the new footprint NEWFP, whose model line names NEWFP.step."""
    good = atomic_part("PASSING-1")
    commit_file(repos, repos.custom, GATE_REL, atomic_lib((good,)), "Add the first parts")
    parts = (good, atomic_part("NEW-A", replace={"Footprint": "Atomic_Footprints:NEWFP"}))
    footprint = vendor_footprint("NEWFP", models=("${CUSTOM_3DMODEL_DIR}/NEWFP.step",) if with_model else ())
    return import_files(repos, {GATE_REL: atomic_lib(parts), NEWFP_REL: footprint}, library=GATE_LIB, symbol="NEW-A")


@requires_git
def test_recheck_adds_untracked_linked_model(tmp_path):
    repos = _atomic_repos(tmp_path)
    plan = _newfp_plan(repos)
    # what the check dialog's 3D fill-in does: copy the .step into Custom
    (repos.custom / NEWFP_STEP).write_bytes(STEP_BYTES)
    ctx = _ctx()

    new_plan, probe = commit_step.recheck_commit(plan, git=ctx)

    model = _planned(new_plan, NEWFP_STEP)
    assert model.note == "added" and model.base_sha256 is None and model.kind == "model"
    assert model.expected_sha256 == hashlib.sha256(STEP_BYTES).hexdigest()
    assert probe.state == "ready", probe.reason
    outcome = commit_step.run_commit(new_plan, MESSAGE, False, git=ctx)
    assert outcome.committed and not outcome.failed
    assert gitops.head_blob(ctx, repos.custom, NEWFP_STEP) == STEP_BYTES
    assert gitops.head_blob(ctx, repos.custom, NEWFP_REL) is not None


@requires_git
def test_recheck_adds_nothing_when_no_part_links_a_model(tmp_path):
    repos = _atomic_repos(tmp_path)
    plan = _newfp_plan(repos, with_model=False)
    (repos.custom / NEWFP_STEP).write_bytes(STEP_BYTES)

    new_plan, _ = commit_step.recheck_commit(plan, git=_ctx())

    assert [f.rel for f in new_plan.files] == [f.rel for f in plan.files]


@requires_git
def test_recheck_leaves_tracked_unchanged_footprint_out(tmp_path):
    _, _, plan = _edited_plan(tmp_path)

    new_plan, _ = commit_step.recheck_commit(plan, git=_ctx())

    assert [f.rel for f in new_plan.files] == [f.rel for f in plan.files]


@requires_git
def test_recheck_leaves_unrelated_untracked_files_out(tmp_path):
    repos, _, plan = _edited_plan(tmp_path)
    before = commit_step.probe_commit(plan, git=_ctx()).other_changes
    (repos.custom / "3DModels" / "OTHER.step").write_bytes(STEP_BYTES)
    (repos.custom / "Footprints" / "Atomic_Footprints.pretty" / "STRAY.kicad_mod").write_bytes(vendor_footprint("STRAY"))

    new_plan, probe = commit_step.recheck_commit(plan, git=_ctx())

    assert [f.rel for f in new_plan.files] == [f.rel for f in plan.files]
    assert probe.other_changes == before + 2


@requires_git
def test_recheck_without_git_returns_the_plan_and_an_unavailable_probe(tmp_path, monkeypatch):
    _, _, plan = _edited_plan(tmp_path)
    monkeypatch.setattr("kicad_lib_manager.gitops.shutil.which", lambda name: None)

    new_plan, probe = commit_step.recheck_commit(plan)

    assert probe.state == "unavailable" and new_plan is plan


@requires_git
def test_changed_diff_text_file(tmp_path):
    repos, good, plan = _edited_plan(tmp_path)
    (repos.custom / GATE_REL).write_bytes(atomic_lib((good, atomic_part("NEW-B"))))
    new_plan, _ = commit_step.recheck_commit(plan, git=_ctx())

    content = commit_step.changed_diff(new_plan, GATE_REL, git=_ctx())

    assert content.kind == "diff"
    assert content.title == f"Custom/{GATE_REL} - as installed vs now"
    lines = content.body.splitlines()
    assert any(line.startswith("+") and "NEW-B" in line for line in lines)
    assert any(line.startswith("-") and "NEW-A" in line for line in lines)


@requires_git
def test_changed_diff_model_is_binary(tmp_path):
    repos = make_superproject(tmp_path / "git")
    plan = import_files(repos, {MODEL_OLD: b"installed model\n"})
    (repos.custom / MODEL_OLD).write_bytes(b"edited model bytes\n")
    new_plan, _ = commit_step.recheck_commit(plan, git=_ctx())

    content = commit_step.changed_diff(new_plan, MODEL_OLD, git=_ctx())

    assert content.kind == "binary"
    assert content.title == f"Custom/{MODEL_OLD} - as installed vs now"
    assert hashlib.sha256(b"edited model bytes\n").hexdigest() in content.body
    assert "KiB" in content.body


@requires_git
def test_changed_diff_added_file_shows_head_against_now(tmp_path):
    repos = _atomic_repos(tmp_path)
    good = atomic_part("PASSING-1")
    plan = _gate_plan(repos, good, atomic_part("NEW-A"), head_parts=(good,))
    other = f"Symbols/{LIB}.kicad_sym"
    head_bytes = (repos.custom / other).read_bytes()
    (repos.custom / other).write_bytes(head_bytes + b"; a fix wrote this\n")
    added = commit_plan.with_added_files(plan, [(other, "symbol_lib", hashlib.sha256(head_bytes).hexdigest())])

    content = commit_step.changed_diff(added, other, git=_ctx())

    assert content.kind == "diff" and content.title == f"Custom/{other} - HEAD vs now"
    assert any(line.startswith("+") and "a fix wrote this" in line for line in content.body.splitlines())


@requires_git
def test_changed_diff_unknown_file_is_an_error(tmp_path):
    _, _, plan = _edited_plan(tmp_path)

    content = commit_step.changed_diff(plan, "Symbols/Nope.kicad_sym", git=_ctx())

    assert content.kind == "error"
