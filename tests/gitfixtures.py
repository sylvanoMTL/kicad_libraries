"""Throwaway git repositories for the Phase 6 commit step (plain helper module, not collected).

make_superproject builds, under one folder, two bare remotes, a parent repo and a Custom
submodule that mirror the real layout (Custom/ is a submodule of the parent). Every repo gets
repo-local identity, signing and line-ending config, because the app's run_git removes
GIT_CONFIG_GLOBAL and GIT_CONFIG_NOSYSTEM from its environment: only repo-local config keeps
the tests independent of the machine they run on.
"""

import hashlib
import os
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest
from zipfixtures import CURRENT_CUSTOM_FOOTPRINT_LIBS, CURRENT_CUSTOM_SYMBOL_LIBS, symbol_lib

from kicad_lib_manager.importer.commit_plan import CommitFile, CommitPlan

GIT = shutil.which("git")
requires_git = pytest.mark.skipif(GIT is None, reason="git is not on PATH")


@dataclass
class GitRepos:
    root: Path
    parent: Path
    custom: Path
    custom_remote: Path
    parent_remote: Path
    env: dict

    def git(self, cwd: Path, *args: str, check: bool = True, input=None) -> str:
        """Run git in cwd with the isolated environment and return stdout; raise on a failure when check is set."""
        if isinstance(input, str):
            input = input.encode("utf-8")
        run = subprocess.run(
            [GIT, "-c", "protocol.file.allow=always", *args],
            cwd=cwd,
            env=self.env,
            capture_output=True,
            input=input,
            timeout=120,
        )
        out = run.stdout.decode("utf-8", errors="replace")
        if check and run.returncode != 0:
            err = run.stderr.decode("utf-8", errors="replace")
            raise AssertionError(f"git {' '.join(args)} failed in {cwd} (exit {run.returncode}): {err}")
        return out


def populate_custom(custom: Path) -> None:
    """Write the current Custom/ library names: symbol libraries, footprint folders and an empty model folder."""
    (custom / "Symbols").mkdir(parents=True, exist_ok=True)
    for name in CURRENT_CUSTOM_SYMBOL_LIBS:
        (custom / "Symbols" / f"{name}.kicad_sym").write_bytes(symbol_lib((name,)))
    # git drops empty folders, and the planner refuses a Custom without Symbols/ and Footprints/
    for name in CURRENT_CUSTOM_FOOTPRINT_LIBS:
        pretty = custom / "Footprints" / f"{name}.pretty"
        pretty.mkdir(parents=True, exist_ok=True)
        (pretty / ".gitkeep").write_bytes(b"")
    (custom / "3DModels").mkdir(parents=True, exist_ok=True)
    (custom / "3DModels" / ".gitkeep").write_bytes(b"")
    (custom / ".gitignore").write_bytes(b"*.bak\n*.tmp\n")


def _local_config(repos: GitRepos, repo: Path, autocrlf: bool) -> None:
    for key, value in (
        ("user.name", "Fixture User"),
        ("user.email", "fixture@example.invalid"),
        ("commit.gpgsign", "false"),
        ("core.autocrlf", "true" if autocrlf else "false"),
    ):
        repos.git(repo, "config", key, value)
    hooks = Path(repos.git(repo, "rev-parse", "--git-path", "hooks").strip())
    if not hooks.is_absolute():
        hooks = repo / hooks
    repos.git(repo, "config", "core.hooksPath", hooks.resolve().as_posix())


def _repos(root: Path) -> GitRepos:
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=str(root / "gitconfig"), GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")
    return GitRepos(
        root=root,
        parent=root / "parent",
        custom=root / "parent" / "Custom",
        custom_remote=root / "custom_remote.git",
        parent_remote=root / "parent_remote.git",
        env=env,
    )


def _build(root: Path, autocrlf: bool, populate) -> GitRepos:
    """Create the remotes, the parent clone and the initialised Custom submodule; Custom stays detached."""
    crlf = "true" if autocrlf else "false"
    (root / "gitconfig").write_text(
        "[user]\n\tname = Fixture User\n\temail = fixture@example.invalid\n"
        "[init]\n\tdefaultBranch = main\n"
        f"[commit]\n\tgpgsign = false\n[core]\n\tautocrlf = {crlf}\n",
        encoding="utf-8",
    )
    repos = _repos(root)
    for remote in (repos.custom_remote, repos.parent_remote):
        repos.git(root, "init", "--bare", "-b", "main", str(remote))

    seed_custom = root / "seed_custom"
    repos.git(root, "clone", str(repos.custom_remote), str(seed_custom))
    populate(seed_custom)
    repos.git(seed_custom, "add", "-A")
    repos.git(seed_custom, "commit", "-m", "Seed Custom")
    repos.git(seed_custom, "push", "origin", "HEAD:main")

    seed_parent = root / "seed_parent"
    repos.git(root, "clone", str(repos.parent_remote), str(seed_parent))
    (seed_parent / "README.md").write_text("Parent fixture\n", encoding="utf-8")
    repos.git(seed_parent, "add", "README.md")
    repos.git(seed_parent, "submodule", "add", repos.custom_remote.as_posix(), "Custom")
    repos.git(seed_parent, "commit", "-m", "Add Custom")
    repos.git(seed_parent, "push", "origin", "HEAD:main")

    repos.git(root, "clone", str(repos.parent_remote), str(repos.parent))
    repos.git(repos.parent, "submodule", "update", "--init")
    for repo in (repos.parent, repos.custom):
        _local_config(repos, repo, autocrlf)
    return repos


_templates: dict[bool, Path] = {}


def _template(autocrlf: bool) -> Path:
    """A built superproject kept for the whole test session; building one takes several seconds."""
    if autocrlf not in _templates:
        folder = Path(tempfile.mkdtemp(prefix="gitfixture_template_"))
        _build(folder, autocrlf, populate_custom)
        _templates[autocrlf] = folder
    return _templates[autocrlf]


def make_superproject(
    root: Path, *, custom_branch: str | None = "main", autocrlf: bool = False, populate=populate_custom
) -> GitRepos:
    """Build the bare remotes, the parent repo and its Custom submodule under root.

    custom_branch is the branch Custom is switched to; None leaves the detached HEAD that
    `submodule update` produces. The default populate is built once per session and copied;
    after the copy every absolute path in the repo config is pointed at the copy.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if populate is populate_custom:
        shutil.copytree(_template(autocrlf), root, dirs_exist_ok=True, ignore=shutil.ignore_patterns("seed_*"))
        repos = _repos(root)
        repos.git(repos.parent, "config", "remote.origin.url", repos.parent_remote.as_posix())
        repos.git(repos.parent, "config", "submodule.Custom.url", repos.custom_remote.as_posix())
        repos.git(repos.custom, "config", "remote.origin.url", repos.custom_remote.as_posix())
        for repo in (repos.parent, repos.custom):
            _local_config(repos, repo, autocrlf)
    else:
        repos = _build(root, autocrlf, populate)
    if custom_branch is not None:
        repos.git(repos.custom, "switch", custom_branch)
    return repos


def remote_refs(repos: GitRepos) -> dict[str, str]:
    """Every ref of both bare remotes as {"custom:<ref>": sha, "parent:<ref>": sha}."""
    found: dict[str, str] = {}
    for label, remote in (("custom", repos.custom_remote), ("parent", repos.parent_remote)):
        out = repos.git(remote, "for-each-ref", "--format=%(refname) %(objectname)")
        for line in out.splitlines():
            ref, _, sha = line.partition(" ")
            found[f"{label}:{ref}"] = sha
    return found


def _kind_of(rel: str) -> str:
    """The install op kind for a Custom-relative path."""
    if rel.startswith("Symbols/"):
        return "symbol_lib"
    if rel.startswith("3DModels/"):
        return "model"
    return "footprint"


def import_files(
    repos: GitRepos,
    files: Mapping[str, bytes],
    *,
    library: str = "IC_Battery_Charger_TI",
    symbol: str = "PART1",
    vendor: str = "Ultra Librarian",
    package: str = "ul_PART1.zip",
    new_library: bool = False,
) -> CommitPlan:
    """Stand in for an install: write files (Custom-relative posix path -> bytes) and return their CommitPlan.

    base_sha256 is the hash of what was on disk before (None for a new file), expected_sha256 the
    hash of what was written, exactly as the real install records them.
    """
    commit_files = []
    for rel, data in files.items():
        path = repos.custom / rel
        base = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        commit_files.append(
            CommitFile(rel, f"Custom/{rel}", path, _kind_of(rel), hashlib.sha256(data).hexdigest(), base)
        )
    return CommitPlan(
        repo_root=repos.parent,
        custom_dir=repos.custom,
        custom_rel="Custom",
        files=tuple(commit_files),
        library=library,
        new_library=new_library,
        symbol=symbol,
        footprint=f"{library}:FP1",
        model=None,
        vendor=vendor,
        package=package,
        date="2026-10-22",
        overwrite=False,
        backup_dir=None,
        issues=(),
    )
