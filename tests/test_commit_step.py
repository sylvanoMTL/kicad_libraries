"""commit_step against real git: the detached-HEAD policy and the switch to main (Phase 6, GIT-03, D-14, D-15).

Each test builds a throwaway superproject (two bare remotes, a parent, a Custom submodule) and
puts Custom in the state under test. Nothing here touches the real repository.
"""

import subprocess
from pathlib import Path

from gitfixtures import (
    GIT,
    advance_remote_main,
    commit_file,
    delete_local_branch,
    detach,
    import_files,
    make_superproject,
    requires_git,
)

from kicad_lib_manager.gitops import GitContext
from kicad_lib_manager.importer import commit_step
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
