"""gitops guards (Phase 6, GIT-05): the run_git choke point never reaches a remote and never runs a destructive command.

Pure tests use a recording runner and start no process. The one real-git test builds a throwaway
superproject and checks that a full probe plus commit changes no remote ref.
"""

import ast
import inspect
import subprocess
from pathlib import Path

import pytest
from gitfixtures import GIT, import_files, make_superproject, remote_refs, requires_git

from kicad_lib_manager import gitops
from kicad_lib_manager.gitops import ALLOWED_SUBCOMMANDS, GitContext, find_git, run_git, upstream_ahead
from kicad_lib_manager.importer.commit_plan import default_message
from kicad_lib_manager.importer.commit_step import probe_commit, run_commit
from kicad_lib_manager.models import Issue, Severity

PACKAGE = Path(gitops.__file__).resolve().parent

# The subcommand set fixed by plan 06-01; widening it is a deliberate, reviewed act
EXPECTED_ALLOWED = {
    "--version", "rev-parse", "symbolic-ref", "status", "merge-base", "rev-list", "log", "ls-tree",
    "cat-file", "var", "add", "reset", "switch", "commit", "ls-files", "diff-tree", "check-ignore",
}
# Subcommands that talk to a remote, rewrite history, move refs or discard work
FORBIDDEN_SUBCOMMANDS = (
    "push", "fetch", "pull", "ls-remote", "remote", "config", "stash", "clean", "checkout", "restore",
    "rebase", "merge", "am", "cherry-pick", "gc", "prune", "update-ref", "worktree", "submodule",
)
REMOTE_SUBCOMMANDS = ("push", "fetch", "pull", "ls-remote", "remote")
FORBIDDEN_CONSTANTS = {
    "push", "fetch", "pull", "ls-remote", "remote", "stash", "clean", "checkout", "restore", "rebase",
    "--no-verify", "--force", "-f", "--amend", "--hard", "--no-gpg-sign", "-a", "-A", "--all",
}
GIT_MODULES = (
    "gitops.py",
    "importer/commit_step.py",
    "importer/commit_plan.py",
    "widgets/commit_panel.py",
    "widgets/import_dialog.py",
)
REPO = Path("repo-for-tests")


def _recorder(returncode=0, stdout=b"", stderr=b""):
    """A stand-in for subprocess.run that records every call and returns a canned result."""
    calls = []

    def runner(argv, **kwargs):
        calls.append((list(argv), kwargs))
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)

    return runner, calls


# -- the allow-list ------------------------------------------------------------


def test_allow_list_is_exact_and_safe():
    assert set(ALLOWED_SUBCOMMANDS) == EXPECTED_ALLOWED
    assert not set(ALLOWED_SUBCOMMANDS) & set(FORBIDDEN_SUBCOMMANDS)


@pytest.mark.parametrize("subcommand", FORBIDDEN_SUBCOMMANDS)
def test_run_git_rejects_unlisted_subcommand(subcommand):
    runner, calls = _recorder()
    with pytest.raises(ValueError):
        run_git(GitContext(Path("git"), runner), REPO, subcommand)
    assert calls == []


def test_run_git_rejects_empty_argv():
    runner, calls = _recorder()
    with pytest.raises(ValueError):
        run_git(GitContext(Path("git"), runner), REPO)
    assert calls == []


# -- argv, environment and failure shape ---------------------------------------


def test_run_git_argv_and_env(monkeypatch):
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.setenv(name, "elsewhere")
    runner, calls = _recorder(stdout=b"ok\n")
    result = run_git(GitContext(Path("git"), runner), REPO, "status", "--porcelain")

    assert not isinstance(result, Issue) and result.returncode == 0
    ((argv, kwargs),) = calls
    assert argv[1:6] == ["--literal-pathspecs", "-c", "core.quotepath=false", "-C", str(REPO)]
    assert argv[6] == "status"
    env = kwargs["env"]
    assert not {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"} & set(env)
    assert env["GIT_TERMINAL_PROMPT"] == "0" and env["GIT_OPTIONAL_LOCKS"] == "0"
    assert not kwargs.get("shell")
    assert kwargs["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0)


def test_run_git_strips_every_git_variable_regardless_of_case(monkeypatch):
    _clear_identity(monkeypatch)  # a developer's own identity variables must not change the result
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "elsewhere")
    monkeypatch.setenv("git_ceiling_directories", "elsewhere")
    runner, calls = _recorder()
    run_git(GitContext(Path("git"), runner), REPO, "--version")
    git_keys = {key for key in calls[0][1]["env"] if key.upper().startswith("GIT_")}
    assert git_keys == {"GIT_TERMINAL_PROMPT", "GIT_OPTIONAL_LOCKS", "GIT_EDITOR"}


def test_run_git_keeps_only_identity_variables(monkeypatch):
    _clear_identity(monkeypatch)
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_PARAMETERS"):
        monkeypatch.setenv(name, "elsewhere")
    for name in IDENTITY_NAMES:  # the four name and email variables and both DATE variables
        monkeypatch.setenv(name, f"value of {name}")
    runner, calls = _recorder()
    run_git(GitContext(Path("git"), runner), REPO, "--version")
    env = calls[0][1]["env"]
    git_keys = {key for key in env if key.upper().startswith("GIT_")}
    assert git_keys == {*KEPT_IDENTITY_NAMES, "GIT_TERMINAL_PROMPT", "GIT_OPTIONAL_LOCKS", "GIT_EDITOR"}
    assert all(env[name] == f"value of {name}" for name in KEPT_IDENTITY_NAMES)


def test_run_git_has_no_input_keyword():
    for function in (gitops.run_git, gitops._commit_with_message):
        parameters = inspect.signature(function).parameters
        assert "stdin_data" in parameters and "input" not in parameters, function.__name__


def test_run_git_timeout_and_oserror_become_issues():
    def times_out(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, 1)

    def cannot_start(argv, **kwargs):
        raise OSError(2, "No such file or directory")

    timed = run_git(GitContext(Path("git"), times_out), REPO, "status")
    missing = run_git(GitContext(Path("git"), cannot_start), REPO, "status")

    assert isinstance(timed, Issue) and timed.code == "git.timeout" and timed.severity is Severity.ERROR
    assert isinstance(missing, Issue) and missing.code == "git.not_run" and missing.severity is Severity.ERROR


def test_find_git_refuses_inside_repo(tmp_path):
    repo = tmp_path / "repo"
    inside = repo / "tools" / "git.exe"
    outside = tmp_path / "bin" / "git.exe"

    none = find_git(repo, which=lambda name: None)
    refused = find_git(repo, which=lambda name: str(inside))
    found = find_git(repo, which=lambda name: str(outside))

    assert isinstance(none, Issue) and none.code == "git.not_found"
    assert isinstance(refused, Issue) and refused.code == "git.inside_repo"
    assert found == outside.resolve()


# -- source-level guards -------------------------------------------------------


def test_git_modules_hold_no_remote_or_destructive_argument():
    for name in GIT_MODULES:
        tree = ast.parse((PACKAGE / name).read_text(encoding="utf-8"))
        found = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in FORBIDDEN_CONSTANTS
        }
        assert not found, f"{name} holds a forbidden git argument: {sorted(found)}"


def test_only_known_modules_import_subprocess():
    importers = set()
    for path in PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names = [node.module.split(".")[0]]
            if "subprocess" in names:
                importers.add(path.relative_to(PACKAGE).as_posix())
    assert importers == {"gitops.py", "kicad_process.py", "importer/kicad_cli.py"}


# -- a whole commit, against real git ------------------------------------------


IDENTITY_NAMES = (
    "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_AUTHOR_DATE",
    "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL", "GIT_COMMITTER_DATE",
)  # fmt: skip
KEPT_IDENTITY_NAMES = (
    "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL",
)  # fmt: skip
ENV_IDENTITY = {
    "GIT_AUTHOR_NAME": "Env Author",
    "GIT_AUTHOR_EMAIL": "author@example.invalid",
    "GIT_COMMITTER_NAME": "Env Committer",
    "GIT_COMMITTER_EMAIL": "committer@example.invalid",
}
ATOMIC_FP = "Footprints/Atomic_Footprints.pretty/ENV1.kicad_mod"


def _clear_identity(monkeypatch):
    for name in IDENTITY_NAMES:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)


def _isolate_identity(monkeypatch, repos, home):
    """Leave no identity in any config: the repo-local one is removed, HOME is empty and the variables are unset."""
    home.mkdir(parents=True, exist_ok=True)
    repos.git(repos.custom, "config", "--unset", "user.name")
    repos.git(repos.custom, "config", "--unset", "user.email")
    repos.git(repos.custom, "config", "user.useConfigOnly", "true")
    for name in ("HOME", "USERPROFILE", "XDG_CONFIG_HOME"):
        monkeypatch.setenv(name, str(home))
    monkeypatch.delenv("EMAIL", raising=False)
    _clear_identity(monkeypatch)


def _set_identity(monkeypatch, **values):
    for name, value in values.items():
        monkeypatch.setenv(name, value)


@requires_git
def test_commit_with_identity_from_environment_only(tmp_path, monkeypatch):
    repos = make_superproject(tmp_path / "git")
    _isolate_identity(monkeypatch, repos, tmp_path / "home")
    ctx = GitContext(Path(GIT))
    import_files(repos, {ATOMIC_FP: b'(footprint "ENV1")\n'})
    assert gitops.add_intent(ctx, repos.custom, [ATOMIC_FP]).returncode == 0  # commit --only knows new files by intent

    refused = gitops.commit_paths(ctx, repos.custom, "Env identity", [ATOMIC_FP])
    assert isinstance(refused, Issue) or refused.returncode != 0, "no identity anywhere, so the commit must fail"

    _set_identity(monkeypatch, **ENV_IDENTITY)
    done = gitops.commit_paths(ctx, repos.custom, "Env identity", [ATOMIC_FP])

    assert not isinstance(done, Issue) and done.returncode == 0, getattr(done, "output", done)
    line = repos.git(repos.custom, "log", "-1", "--format=%an <%ae>|%cn <%ce>").strip()
    assert line == "Env Author <author@example.invalid>|Env Committer <committer@example.invalid>"


@requires_git
def test_commit_ignores_exported_dates(tmp_path, monkeypatch):
    repos = make_superproject(tmp_path / "git")
    _isolate_identity(monkeypatch, repos, tmp_path / "home")
    ctx = GitContext(Path(GIT))
    import_files(repos, {ATOMIC_FP: b'(footprint "ENV1")\n'})
    assert gitops.add_intent(ctx, repos.custom, [ATOMIC_FP]).returncode == 0

    _set_identity(monkeypatch, **ENV_IDENTITY)
    _set_identity(monkeypatch, GIT_AUTHOR_DATE="2001-02-03T04:05:06+0000", GIT_COMMITTER_DATE="2001-02-03T04:05:06+0000")
    done = gitops.commit_paths(ctx, repos.custom, "Env identity", [ATOMIC_FP])

    assert not isinstance(done, Issue) and done.returncode == 0, getattr(done, "output", done)
    line = repos.git(
        repos.custom, "log", "-1", "--format=%an <%ae>|%cn <%ce>|%ad|%cd", "--date=format:%Y"
    ).strip()
    identity, author_year, committer_year = line.rsplit("|", 2)
    assert identity == "Env Author <author@example.invalid>|Env Committer <committer@example.invalid>"
    assert author_year != "2001" and committer_year != "2001", line


@requires_git
def test_identity_known_needs_author_and_committer(tmp_path, monkeypatch):
    repos = make_superproject(tmp_path / "git")
    _isolate_identity(monkeypatch, repos, tmp_path / "home")
    ctx = GitContext(Path(GIT))
    committer = {k: v for k, v in ENV_IDENTITY.items() if k.startswith("GIT_COMMITTER")}
    author = {k: v for k, v in ENV_IDENTITY.items() if k.startswith("GIT_AUTHOR")}

    assert gitops.identity_known(ctx, repos.custom) is False

    _set_identity(monkeypatch, **committer)
    assert gitops.identity_known(ctx, repos.custom) is False  # committer alone is not enough

    _clear_identity(monkeypatch)
    _set_identity(monkeypatch, **author)
    assert gitops.identity_known(ctx, repos.custom) is False  # nor is the author alone

    _set_identity(monkeypatch, **committer)
    assert gitops.identity_known(ctx, repos.custom) is True


@requires_git
def test_full_commit_never_contacts_a_remote(tmp_path):
    repos = make_superproject(tmp_path / "git")
    symbols = "Symbols/IC_Battery_Charger_TI.kicad_sym"
    cplan = import_files(
        repos,
        {
            symbols: (repos.custom / symbols).read_bytes() + b"; edited by the import\n",
            "Footprints/IC_Battery_Charger_TI.pretty/FP1.kicad_mod": b'(footprint "FP1")\n',
        },
    )
    calls = []

    def runner(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.run(argv, **kwargs)

    ctx = GitContext(Path(GIT), runner)
    refs = remote_refs(repos)

    probe = probe_commit(cplan, git=ctx)
    outcome = run_commit(cplan, default_message(cplan), True, git=ctx)

    assert probe.state == "ready"
    assert outcome.committed and outcome.parent_commit is not None and not outcome.failed
    assert calls, "the runner recorded nothing, so the test proved nothing"
    for argv in calls:
        assert argv[6] in ALLOWED_SUBCOMMANDS, argv
        assert not set(argv[6:]) & set(REMOTE_SUBCOMMANDS), argv
    assert remote_refs(repos) == refs
    assert upstream_ahead(ctx, repos.custom) == ("origin/main", 1)
    assert upstream_ahead(ctx, repos.parent) == ("origin/main", 1)
