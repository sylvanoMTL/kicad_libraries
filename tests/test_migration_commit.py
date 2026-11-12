"""Task 1 (13-13): a real migration tagged, applied and committed as one Custom commit plus the

parent ref, through the unchanged Phase 11 commit step (MIG-01, MIG-04). One throwaway
superproject per test (gitfixtures.make_superproject); the live Custom/ is never touched.
"""

from pathlib import Path

from fakecli import FakeCli
from gitfixtures import GIT, commit_file, make_superproject, requires_git
from installfixtures import V10_VERSION, vendor_footprint
from migrationfixtures import _tab_lib, _tab_symbol
from zipfixtures import STEP_BYTES

from kicad_lib_manager.gitops import GitContext
from kicad_lib_manager.importer import commit_step
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.migration.applier import apply_migration
from kicad_lib_manager.importer.migration.commitplan import MIGRATION_SUBJECT, build_migration_commit_plan
from kicad_lib_manager.importer.migration.inventory import read_inventory
from kicad_lib_manager.importer.migration.plan import MigrationChoices, PartChoice
from kicad_lib_manager.importer.migration.planner import build_migration_plan, prepare_context
from kicad_lib_manager.importer.migration.precheck import PRE_ATOMIC_TAG, ensure_tag
from kicad_lib_manager.importer.plan import MODEL_DIR_VAR, ToolContext

TODAY = "2026-11-11"
LIBRARY = "IC_Fuel_Gauge_ADI"
PART = "MAX17048G_T10"
FOOTPRINT = "SON50P200X200X80-9N"
MODEL = "MAX17048G.step"
TARGET = "Atomic_Battery_Management"


def _populate(custom: Path) -> None:
    symbols_dir = custom / "Symbols"
    footprints_dir = custom / "Footprints"
    models_dir = custom / "3DModels"
    for folder in (symbols_dir, footprints_dir, models_dir):
        folder.mkdir(parents=True, exist_ok=True)
    (symbols_dir / f"{LIBRARY}.kicad_sym").write_bytes(
        _tab_lib(
            20241209,
            [
                _tab_symbol(
                    PART,
                    [
                        ("Reference", "U", False),
                        ("Value", PART, False),
                        ("Footprint", f"{LIBRARY}:{FOOTPRINT}", True),
                        (
                            "Datasheet",
                            "https://www.analog.com/media/en/technical-documentation/data-sheets/max17048-max17049.pdf",
                            True,
                        ),
                        ("Description", "1-Cell Fuel Gauge with ModelGauge", True),
                        ("MPN", "MAX17048G", True),
                        ("Manufacturer", "Analog Devices", True),
                    ],
                ),
            ],
        )
    )
    pretty = footprints_dir / f"{LIBRARY}.pretty"
    pretty.mkdir(parents=True, exist_ok=True)
    (pretty / f"{FOOTPRINT}.kicad_mod").write_bytes(
        vendor_footprint(FOOTPRINT, model=f"{MODEL_DIR_VAR}/{MODEL}", eol="\r\n")
    )
    (models_dir / MODEL).write_bytes(STEP_BYTES)
    (custom / ".gitignore").write_bytes(b"*.bak\n")


def _tools(output_version: int = V10_VERSION) -> ToolContext:
    return ToolContext(kicad_cli=Path("kicad-cli"), cli_runner=FakeCli(output_version=output_version))


def _plan_for(layout: RepoLayout, choices: MigrationChoices):
    inventory = read_inventory(layout)
    ctx = prepare_context(inventory, _tools(), None, today=TODAY)
    plan = build_migration_plan(inventory, choices, ctx)
    return inventory, plan


def _digest(root: Path) -> dict[str, str]:
    import hashlib

    found: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            found[rel + "/"] = "dir"
        elif path.is_file():
            found[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


@requires_git
def test_migration_commit_end_to_end(tmp_path):
    repos = make_superproject(tmp_path / "git", populate=_populate)
    custom = repos.custom
    repo_root = repos.parent
    git_ctx = GitContext(Path(GIT))

    old_head = repos.git(custom, "rev-parse", "HEAD").strip()

    # A .bak written after the commit: untracked, ignored, and must never reach the commit plan.
    (custom / "Symbols" / f"{LIBRARY}.bak").write_bytes(b"old revision, kept for reference\r\n")

    layout = RepoLayout.for_repo(repo_root)
    key = (f"Custom/Symbols/{LIBRARY}.kicad_sym", PART)
    choices = MigrationChoices(parts={key: PartChoice(library=TARGET)})
    inventory, plan = _plan_for(layout, choices)

    result = apply_migration(
        plan,
        backup_root=tmp_path / "backups",
        tools=_tools(),
        before_first_write=lambda: ensure_tag(custom, repo_root, git=git_ctx),
    )
    assert result.ok, result.issues

    tagged_at = repos.git(custom, "rev-parse", PRE_ATOMIC_TAG).strip()
    assert tagged_at == old_head

    cplan = build_migration_commit_plan(result, plan, today=TODAY)
    rels = {f.rel for f in cplan.files}
    assert f"Symbols/{TARGET}.kicad_sym" in rels
    assert any(rel.startswith("Footprints/Atomic_Footprints.pretty/") and rel.endswith(".kicad_mod") for rel in rels)
    assert "MIGRATION-ATOMIC.md" in rels
    assert not any(rel.endswith(".bak") for rel in rels)

    deleted = {f.rel for f in cplan.files if f.deleted}
    assert f"Symbols/{LIBRARY}.kicad_sym" in deleted
    assert f"Footprints/{LIBRARY}.pretty/{FOOTPRINT}.kicad_mod" in deleted

    probe = commit_step.probe_commit(cplan, git=git_ctx)
    assert probe.state == "ready", (probe.state, probe.reason, probe.gate.lines if probe.gate else None)
    assert probe.gate is not None and not probe.gate.refused

    outcome = commit_step.run_commit(cplan, cplan.message, True, git=git_ctx)
    assert outcome.custom_commit is not None, outcome.issues
    assert outcome.parent_commit is not None, outcome.issues

    subject = repos.git(custom, "log", "-1", "--format=%s").strip()
    assert subject == MIGRATION_SUBJECT

    committed_files = set(
        repos.git(custom, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()
    )
    assert committed_files == rels

    assert not (custom / "Symbols" / f"{LIBRARY}.bak").exists()
    tracked_bak = repos.git(custom, "ls-files", f"Symbols/{LIBRARY}.bak").strip()
    assert tracked_bak == ""

    parent_log = repos.git(repos.parent, "log", "-1", "--format=%s").strip()
    assert "Custom" in parent_log


@requires_git
def test_refused_tag_writes_nothing(tmp_path):
    repos = make_superproject(tmp_path / "git", populate=_populate)
    custom = repos.custom
    repo_root = repos.parent
    git_ctx = GitContext(Path(GIT))

    repos.git(custom, "tag", PRE_ATOMIC_TAG)
    commit_file(repos, custom, "throwaway.txt", b"x\n", "Another commit")

    layout = RepoLayout.for_repo(repo_root)
    key = (f"Custom/Symbols/{LIBRARY}.kicad_sym", PART)
    choices = MigrationChoices(parts={key: PartChoice(library=TARGET)})
    _, plan = _plan_for(layout, choices)

    before = _digest(custom)

    result = apply_migration(
        plan,
        backup_root=tmp_path / "backups",
        before_first_write=lambda: ensure_tag(custom, repo_root, git=git_ctx),
    )

    assert result.ok is False
    assert any(i.code == "migration.tag_elsewhere" for i in result.issues)
    after = _digest(custom)
    assert before == after
