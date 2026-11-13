"""Phase 13 whole-fixture end-to-end test (13-20): the services of plans 13-05..13-13 migrate the

whole synthetic v1 Custom to zero violations and one Custom commit plus the parent ref, against
real git, without the window (MIG-01, MIG-03, MIG-04, MIG-05, D-04). This is the acceptance check
of D-04's success definition: no v1-named library left, each part where the preview showed it,
zero violations on the next scan.

One throwaway superproject per test (migrationfixtures.make_v1_superproject, built on
gitfixtures.make_superproject); the live Custom/ is never touched — every repo is built under
tmp_path and the session guard _live_custom_untouched stays in force.
"""

from dataclasses import replace
from pathlib import Path

from fakecli import FakeCli
from gitfixtures import GIT, requires_git
from installfixtures import V10_VERSION
from customfixtures import OFFICIAL_FOOTPRINT, OFFICIAL_LIBRARY
from migrationfixtures import (
    BOARD_FEATURES,
    EXPECTED_TARGETS,
    IMU_LIBRARY,
    SHARED_FOOTPRINTS,
    make_v1_superproject,
    write_v1_stock,
)
from zipfixtures import STEP_BYTES

from kicad_lib_manager.gitops import GitContext
from kicad_lib_manager.importer import commit_step, stems
from kicad_lib_manager.importer.layout import RepoLayout
from kicad_lib_manager.importer.migration.applier import apply_migration
from kicad_lib_manager.importer.migration.commitplan import build_migration_commit_plan
from kicad_lib_manager.importer.migration.gate import TARGET_LIBRARY, check_plan, end_state_context
from kicad_lib_manager.importer.migration.inventory import read_inventory
from kicad_lib_manager.importer.migration.plan import MigrationChoices, PartChoice
from kicad_lib_manager.importer.migration.planner import build_migration_plan, prepare_context
from kicad_lib_manager.importer.migration.precheck import PRE_ATOMIC_TAG, ensure_tag
from kicad_lib_manager.importer.plan import ToolContext
from kicad_lib_manager.library_scanner import scan_all

TODAY = "2026-11-11"
# Enough passes for every part (14) to clear every rule (up to 7) one StripLine at a time, plus slack.
MAX_FILL_PASSES = 40


def _part_by_key(inventory, key):
    return next(part for part in inventory.parts if part.key == key)


def _footprint_by_link(inventory, link):
    """The InventoryFootprint a symbol's Footprint field names, or None (unresolved or outside Custom)."""
    if not link or ":" not in link:
        return None
    library, _, name = link.partition(":")
    return next((fp for fp in inventory.footprints if fp.library == library and fp.name == name), None)


def _apply_fix(line, choices, inventory, model_dir):
    """One StripLine fixed from its own target and key, taken straight from the gate (D-15).

    Returns an updated MigrationChoices, or None when this line names no part key or a target this
    generic fill does not (yet) know how to answer -- the caller treats that as "could not fix".
    """
    if line.key is None or line.target is None:
        return None
    part = _part_by_key(inventory, line.key)
    parts = dict(choices.parts)
    existing = parts.get(line.key, PartChoice())

    if line.target == TARGET_LIBRARY:
        value = EXPECTED_TARGETS.get(line.key)
        if not value:
            return None
        parts[line.key] = replace(existing, library=value)
    elif line.target == "mpn":
        # The strip's own part names the orderable number (D-06); this test stands in with the
        # part's own original name, which the fixture already keeps unique per part.
        parts[line.key] = replace(existing, mpn=part.name)
    elif line.target == "manufacturer":
        parts[line.key] = replace(existing, manufacturer="Global Connector Technology")
    elif line.target == "datasheet":
        parts[line.key] = replace(existing, datasheet=f"https://example.com/{part.name}.pdf")
    elif line.target == "description":
        parts[line.key] = replace(existing, description=f"Migrated test part {part.name}")
    elif line.target == "footprint_name":
        # The symbol carries no Footprint field at all (no vendor footprint to move): link KiCad's
        # own stock footprint instead, the same "official" choice D-08 offers in the real window.
        parts[line.key] = replace(
            existing, footprint_target="official", official_footprint=f"{OFFICIAL_LIBRARY}:{OFFICIAL_FOOTPRINT}"
        )
    elif line.target == "model":
        # The footprint the failing symbol links; a model source is only read from the footprint's
        # own FIRST shared linker (footprints.plan_footprints), so it is set there, not on line.key.
        fp = _footprint_by_link(inventory, part.footprint)
        if fp is None or not fp.linked_by:
            return None
        first_key = min(fp.linked_by)
        model_path = model_dir / f"{fp.library}-{fp.name}.step"
        if not model_path.exists():
            model_path.write_bytes(STEP_BYTES)
        first_existing = parts.get(first_key, PartChoice())
        parts[first_key] = replace(first_existing, model_source=str(model_path))
    else:
        return None
    return replace(choices, parts=parts)


def _plan_and_gate(inventory, choices, ctx, kicad_fp_dir):
    plan = build_migration_plan(inventory, choices, ctx)
    atomic_ctx = end_state_context(plan, inventory, kicad_fp_dir)
    outcome = check_plan(plan, inventory, atomic_ctx)
    return plan, outcome


@requires_git
def test_whole_v1_custom_migrates_to_zero_violations(tmp_path):
    repos = make_v1_superproject(tmp_path)
    custom = repos.custom
    repo_root = repos.parent
    git_ctx = GitContext(Path(GIT))
    old_head = repos.git(custom, "rev-parse", "HEAD").strip()

    stock_symbols_dir, stock_footprints_dir = write_v1_stock(tmp_path)
    model_dir = tmp_path / "added_models"
    model_dir.mkdir(parents=True, exist_ok=True)

    layout = RepoLayout.for_repo(repo_root)
    inventory = read_inventory(layout)
    tools = ToolContext(
        kicad_cli=Path("kicad-cli"),
        cli_runner=FakeCli(output_version=V10_VERSION),
        kicad_symbols_dir=stock_symbols_dir,
        # Mirror detect_tools(): an empty allowed set would filter every suggestion out (see
        # test_migration_symbols._tools), and this test is about the suggestion placing the IMU
        allowed_stems=stems.allowed_stems(stems.installed_stems(stock_symbols_dir)),
    )
    ctx = prepare_context(inventory, tools, stock_footprints_dir, today=TODAY)

    # The IMU-style part's ICM- sibling vote lands it in Atomic_Sensor_Motion with no owner choice
    # (gap G-13-1-f). Every gap -- the LTC2954 orderable MPNs, the missing datasheets/descriptions/
    # libraries, the model-less footprints -- is filled generically below, straight from what the
    # gate itself reports.
    imu_key = (f"Custom/Symbols/{IMU_LIBRARY}.kicad_sym", "ICM-42688-P")
    choices = MigrationChoices()

    plan = outcome = None
    for _ in range(MAX_FILL_PASSES):
        plan, outcome = _plan_and_gate(inventory, choices, ctx, stock_footprints_dir)
        if outcome.run_enabled:
            break
        changed = False
        for line in outcome.lines:
            fixed = _apply_fix(line, choices, inventory, model_dir)
            if fixed is not None:
                choices = fixed
                changed = True
        assert changed, f"gate reported lines a pass could not fix (D-15): {outcome.lines}"
    assert outcome is not None and outcome.run_enabled, outcome.lines if outcome else "never ran"
    imu_plan = next(part for part in plan.parts if part.key == imu_key)
    assert imu_plan.target_library == "Atomic_Sensor_Motion"

    result = apply_migration(
        plan,
        backup_root=tmp_path / "backups",
        tools=tools,
        before_first_write=lambda: ensure_tag(custom, repo_root, git=git_ctx),
    )
    assert result.ok, result.issues

    tagged_at = repos.git(custom, "rev-parse", PRE_ATOMIC_TAG).strip()
    assert tagged_at == old_head

    scan_result = scan_all(repo_root, kicad_fp_dir=stock_footprints_dir)

    custom_sym_libs = [lib for lib in scan_result.symbol_libs if lib.source == "Custom"]
    assert custom_sym_libs
    for lib in custom_sym_libs:
        assert lib.nickname.startswith("Atomic_"), lib.nickname

    custom_fp_libs = [lib for lib in scan_result.footprint_libs if lib.source == "Custom"]
    assert custom_fp_libs
    for lib in custom_fp_libs:
        assert lib.nickname == SHARED_FOOTPRINTS, lib.nickname

    for lib in scan_result.symbol_libs:
        if not lib.atomic:
            continue
        for entry in lib.symbols:
            assert not entry.violations, (lib.nickname, entry.name, entry.violations)

    assert not list((custom / "Symbols").glob("*.bak"))

    for rel in BOARD_FEATURES:
        name = Path(rel).name
        assert (custom / "Footprints" / f"{SHARED_FOOTPRINTS}.pretty" / name).exists(), name

    cplan = build_migration_commit_plan(result, plan, today=TODAY)
    probe = commit_step.probe_commit(cplan, git=git_ctx, kicad_fp_dir=stock_footprints_dir)
    assert probe.state == "ready", (
        probe.state, probe.reason,
        probe.gate.blocking if probe.gate else None,
        probe.gate.problems if probe.gate else None,
    )
    assert probe.gate is not None and not probe.gate.refused

    commit_outcome = commit_step.run_commit(
        cplan, cplan.message, True, git=git_ctx, kicad_fp_dir=stock_footprints_dir
    )
    assert commit_outcome.custom_commit is not None, commit_outcome.issues
    assert commit_outcome.parent_commit is not None, commit_outcome.issues

    commit_count = repos.git(custom, "rev-list", "--count", f"{old_head}..HEAD").strip()
    assert commit_count == "1"

    stat_output = repos.git(custom, "show", "--stat", "HEAD")
    assert "MIGRATION-ATOMIC.md" in stat_output

    parent_log = repos.git(repos.parent, "log", "-1", "--format=%s").strip()
    assert "Custom" in parent_log
