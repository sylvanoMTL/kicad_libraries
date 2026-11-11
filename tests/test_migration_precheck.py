"""check_custom and ensure_tag, the migration's pre-write gate (Phase 13, MIG-01, D-02).

Every repo here is a throwaway superproject built by gitfixtures.make_superproject under
tmp_path; the live Custom/ is never touched.
"""

import subprocess
from pathlib import Path

import pytest
from gitfixtures import GIT, commit_file, detach, make_superproject, requires_git, start_merge_conflict

from kicad_lib_manager.gitops import GitContext, create_tag, tag_commit
from kicad_lib_manager.importer.migration.precheck import PRE_ATOMIC_TAG, check_custom, ensure_tag
from kicad_lib_manager.models import Severity

UNTRACKED_SYMBOL = "Symbols/Atomic_Transistor_FET_NEW.kicad_sym"
UNTRACKED_FOOTPRINT = "Footprints/Atomic_Footprints.pretty/DQK0006B.kicad_mod"


def _fake_git(responses, *, default=(1, b"", b"")):
    """A git runner answering by the longest matching prefix of argv[6:] (the subcommand and its args).

    responses maps a tuple prefix to (returncode, stdout, stderr); an unmatched call gets default
    (a failure), so a check this test does not expect to run never looks like a false success.
    """
    calls = []

    def runner(argv, **kwargs):
        calls.append(list(argv))
        rest = tuple(argv[6:])
        for key in sorted(responses, key=len, reverse=True):
            if rest[: len(key)] == key:
                returncode, out, err = responses[key]
                return subprocess.CompletedProcess(argv, returncode, out, err)
        returncode, out, err = default
        return subprocess.CompletedProcess(argv, returncode, out, err)

    return runner, calls


@requires_git
def test_uncommitted_files_refuse_by_name(tmp_path):
    repos = make_superproject(tmp_path / "git")
    (repos.custom / UNTRACKED_SYMBOL).write_bytes(b"(kicad_symbol_lib)\n")
    (repos.custom / UNTRACKED_FOOTPRINT).write_bytes(b'(footprint "DQK0006B")\n')
    ctx = GitContext(Path(GIT))

    result = check_custom(repos.custom, repos.parent, git=ctx)

    assert result.ok is False
    assert result.tag_action == ""
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.severity is Severity.ERROR
    assert issue.code == "migration.uncommitted"
    expected_listing = "\n".join(sorted((UNTRACKED_SYMBOL, UNTRACKED_FOOTPRINT)))
    assert expected_listing in issue.text
    assert tag_commit(ctx, repos.custom, PRE_ATOMIC_TAG) is None


@requires_git
def test_clean_custom_is_tagged_at_head(tmp_path):
    repos = make_superproject(tmp_path / "git")
    ctx = GitContext(Path(GIT))
    head = repos.git(repos.custom, "rev-parse", "HEAD").strip()

    result = check_custom(repos.custom, repos.parent, git=ctx)

    assert result.ok is True
    assert result.tag_action == "create"
    assert result.head == head

    issues = ensure_tag(repos.custom, repos.parent, git=ctx)

    assert len(issues) == 1
    assert issues[0].severity is Severity.INFO
    assert issues[0].code == "migration.tagged"
    short = repos.git(repos.custom, "rev-parse", "--short", "HEAD").strip()
    assert short in issues[0].text

    tagged = repos.git(repos.custom, "rev-parse", f"{PRE_ATOMIC_TAG}^{{commit}}").strip()
    assert tagged == head


@requires_git
def test_ignored_bak_does_not_refuse(tmp_path):
    repos = make_superproject(tmp_path / "git")
    (repos.custom / "Symbols" / "IC_X.bak").write_bytes(b"old\n")
    ctx = GitContext(Path(GIT))

    result = check_custom(repos.custom, repos.parent, git=ctx)

    assert result.ok is True


@requires_git
def test_tag_at_head_is_reused(tmp_path):
    repos = make_superproject(tmp_path / "git")
    ctx = GitContext(Path(GIT))

    first = ensure_tag(repos.custom, repos.parent, git=ctx)
    assert first[0].code == "migration.tagged"

    second = ensure_tag(repos.custom, repos.parent, git=ctx)

    assert len(second) == 1
    assert second[0].severity is Severity.INFO
    assert second[0].code == "migration.tag_reused"
    tags = [line for line in repos.git(repos.custom, "tag", "--list", PRE_ATOMIC_TAG).strip().splitlines() if line]
    assert tags == [PRE_ATOMIC_TAG]


@requires_git
def test_tag_elsewhere_refuses_with_commands(tmp_path):
    repos = make_superproject(tmp_path / "git")
    ctx = GitContext(Path(GIT))
    ensure_tag(repos.custom, repos.parent, git=ctx)  # tags the current HEAD
    old_head = repos.git(repos.custom, "rev-parse", "HEAD").strip()
    old_short = repos.git(repos.custom, "rev-parse", "--short", "HEAD").strip()
    commit_file(repos, repos.custom, "Symbols/ANOTHER.kicad_sym", b"(kicad_symbol_lib)\n", "Another commit")

    result = check_custom(repos.custom, repos.parent, git=ctx)

    assert result.ok is False
    assert result.tag_action == ""
    assert len(result.issues) == 1
    issue = result.issues[0]
    assert issue.severity is Severity.ERROR
    assert issue.code == "migration.tag_elsewhere"
    assert old_short in issue.text
    assert "recovery point of an earlier migration" in issue.text
    assert f"git -C Custom tag {PRE_ATOMIC_TAG}-old {PRE_ATOMIC_TAG}" in issue.text
    assert f"git -C Custom tag -d {PRE_ATOMIC_TAG}" in issue.text

    tagged = repos.git(repos.custom, "rev-parse", f"{PRE_ATOMIC_TAG}^{{commit}}").strip()
    assert tagged == old_head


@requires_git
def test_detached_head_refuses(tmp_path):
    repos = make_superproject(tmp_path / "git")
    detach(repos)
    ctx = GitContext(Path(GIT))

    result = check_custom(repos.custom, repos.parent, git=ctx)

    assert result.ok is False
    assert result.tag_action == ""
    assert result.issues[0].code == "migration.detached"


@requires_git
def test_merge_in_progress_refuses(tmp_path):
    repos = make_superproject(tmp_path / "git")
    start_merge_conflict(repos, repos.custom, "Symbols/IC_Battery_Charger_TI.kicad_sym")
    ctx = GitContext(Path(GIT))

    result = check_custom(repos.custom, repos.parent, git=ctx)

    assert result.ok is False
    assert result.tag_action == ""
    assert result.issues[0].code == "migration.busy"


def test_unknown_identity_refuses(tmp_path):
    custom_dir = (tmp_path / "Custom").resolve()
    responses = {
        ("--version",): (0, b"git version 2.49.0\n", b""),
        ("rev-parse", "--show-toplevel"): (0, str(custom_dir).encode() + b"\n", b""),
        ("rev-parse", "--git-path"): (1, b"", b""),  # no busy marker present
        ("var",): (1, b"", b"fatal: no identity\n"),
    }
    runner, calls = _fake_git(responses)
    ctx = GitContext(Path("git"), runner=runner)

    result = check_custom(custom_dir, tmp_path / "parent", git=ctx)

    assert result.ok is False
    assert result.tag_action == ""
    assert result.issues[0].code == "migration.identity"
    assert calls


def test_old_git_refuses(tmp_path):
    responses = {
        ("--version",): (0, b"git version 2.20.0\n", b""),
    }
    runner, calls = _fake_git(responses)
    ctx = GitContext(Path("git"), runner=runner)

    result = check_custom(tmp_path / "Custom", tmp_path / "parent", git=ctx)

    assert result.ok is False
    assert result.tag_action == ""
    assert result.issues[0].code == "migration.git_old"
    assert calls


@requires_git
def test_not_a_work_tree_refuses(tmp_path):
    parent = tmp_path / "parent"
    parent.mkdir()
    custom = parent / "Custom"
    custom.mkdir()
    subprocess.run([GIT, "init", "-b", "main", str(parent)], check=True, capture_output=True)
    ctx = GitContext(Path(GIT))

    result = check_custom(custom, parent, git=ctx)

    assert result.ok is False
    assert result.tag_action == ""
    assert result.issues[0].code == "migration.not_git"


def test_create_tag_rejects_odd_names():
    runner, calls = _fake_git({})
    ctx = GitContext(Path("git"), runner=runner)

    for name in ("-f", "a b", ""):
        with pytest.raises(ValueError):
            create_tag(ctx, Path("Custom"), name)

    assert calls == []
