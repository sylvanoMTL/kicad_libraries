---
phase: 13-atomic-migration-and-kicad-setup
plan: 20
subsystem: importer
tags: [migration, testing, atomic-check, gate, applier, commit-step, real-git]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "plan 13-06's migration.planner/gate.py skeleton, plan 13-09's symbols.py, plan 13-10's footprints.py, plan 13-11's families.py, plan 13-12's gate.py/mapfile.py, plan 13-13's applier.py/commitplan.py, plan 13-04's commit_step.py, tests/migrationfixtures.py (the rich v1 Custom fixture) and tests/gitfixtures.py"
provides:
  - "tests/test_migration_full.py: the phase's one whole-fixture end-to-end test, the acceptance check of D-04's success definition (no v1-named library left, each part where the preview showed it, zero violations on the next scan) and of MIG-03/MIG-04 at service level"
affects: []

actuals:
  tokens: 2402
  tasks: 1
  commits: 1
  plan_head_before: 7f3d06a76c6676c697ab36917d263823f72a1b06
  plan_head_after: e797d5d16fd2c70ff4dee528cc2adad343d76c9d

tech-stack:
  added: []
  patterns:
    - "A gate-driven fill loop: rather than hand-enumerate every gap the fixture's 14 parts need, the test loops build_migration_plan -> end_state_context -> check_plan, and for each returned StripLine derives the fix purely from its own (key, target) pair -- library from the EXPECTED_TARGETS test-expectation map, mpn/manufacturer/datasheet/description synthesized per part, footprint_name via the official-footprint choice when the symbol carries no Footprint field at all, and model via the footprint's own first linking key (migration/footprints.py only reads model_source off that key). The loop fails loudly if a pass makes no progress, proving the strip names everything Run needs (D-15) without the test silently guessing."
    - "The one deliberate exception to that generic loop is proactive: the IMU-style part's sibling vote mis-suggests the valid-but-wrong Atomic_Timer, which never produces a StripLine (a wrong-but-non-blank library is never 'undecided'), so the test sets its PartChoice.library to Atomic_Sensor_Motion before the first gate run, exactly matching the 13-CONTEXT 'Research defaults' note that this correction is the owner's, not the engine's."

key-files:
  created:
    - tests/test_migration_full.py
  modified: []

key-decisions:
  - "Two symbols (MAX17048G, MAX17048X) in the fixture carry no Footprint field at all (no vendor footprint to move), so the atomic gate's footprint-link violation (target 'footprint_name') cannot be fixed by renaming a footprint -- the fill instead sets footprint_target='official' with official_footprint=Package_TO_SOT_SMD:SOT-23-5 (the fake stock footprint write_fake_kicad already provides), the same 'use an official KiCad footprint' choice D-08 offers in the real window."
  - "A footprint shared by two symbols (e.g. DFN-8_DDB linked by both LTC2954-1-DFN8 and LTC2954-2-DFN8) reports a 'model' StripLine against each linking symbol independently, but migration/footprints.py only ever reads PartChoice.model_source off the footprint's smallest linking key. The fix handler resolves the failing symbol's Footprint field back to its InventoryFootprint, takes min(fp.linked_by), and writes the added 3D model source there -- idempotent across repeated StripLines for the same footprint."

requirements-completed: [MIG-01, MIG-03, MIG-04, MIG-05]

coverage:
  - id: D1
    description: "The whole synthetic v1 Custom (14 parts across 7 v1 libraries, 2 .bak files, 2 board-feature footprints) migrates through the phase's services directly (planner, gate, applier, commitplan) to zero atomic violations and one Custom commit plus the parent ref, against real git"
    requirement: "MIG-01"
    verification:
      - kind: integration
        ref: "tests/test_migration_full.py#test_whole_v1_custom_migrates_to_zero_violations"
        status: pass
    human_judgment: false
  - id: D2
    description: "check_plan's gate reaches run_enabled (no StripLine left) once every gap is filled purely from the strip's own target and key, proving the strip names everything Run needs (D-15)"
    requirement: "MIG-03"
    verification:
      - kind: integration
        ref: "tests/test_migration_full.py#test_whole_v1_custom_migrates_to_zero_violations"
        status: pass
    human_judgment: false
  - id: D3
    description: "apply_migration tags Custom pre-atomic before the first write, writes every op, and build_migration_commit_plan -> probe_commit -> run_commit(bump_parent=True) commits once in Custom (holding MIGRATION-ATOMIC.md) and once in the parent"
    requirement: "MIG-04"
    verification:
      - kind: integration
        ref: "tests/test_migration_full.py#test_whole_v1_custom_migrates_to_zero_violations"
        status: pass
    human_judgment: false
  - id: D4
    description: "After the migration, scan_all reports no Custom symbol library without the Atomic_ prefix, no Custom footprint library other than Atomic_Footprints, zero atomic violations in any Atomic_ library, no .bak left, and both board-feature footprints still present under Atomic_Footprints.pretty"
    requirement: "MIG-05"
    verification:
      - kind: integration
        ref: "tests/test_migration_full.py#test_whole_v1_custom_migrates_to_zero_violations"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 20: Whole v1 Custom migration proof Summary

**A real throwaway git superproject with the full synthetic v1 Custom (14 parts, 7 v1 libraries, 2 `.bak` files, 2 board-feature footprints) is driven through the phase's migration services end to end -- gate-filled generically from each StripLine's own target -- to zero atomic violations and one Custom commit plus the parent ref.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-11-11
- **Completed:** 2026-11-11
- **Tasks:** 1 completed
- **Files modified:** 1 (new test file)

## Accomplishments

- `tests/test_migration_full.py` drives `planner.prepare_context` / `build_migration_plan`, `gate.end_state_context` / `check_plan`, `applier.apply_migration`, and `commitplan.build_migration_commit_plan` directly against the rich v1 Custom fixture (`migrationfixtures.make_v1_superproject` + `write_v1_stock`), with no window in between.
- A generic fill loop reads `check_plan`'s `StripLine`s and answers each one purely from its own `(key, target)` pair: `library` from the `EXPECTED_TARGETS` test-expectation map, `mpn`/`manufacturer`/`datasheet`/`description` synthesized per part, `footprint_name` via an official-footprint choice for the two symbols with no Footprint field at all, and `model` via the failing symbol's own footprint resolved back to its first linking key. The loop asserts progress every pass, proving the gate names everything Run needs (D-15) instead of the test pre-guessing the fixture's gaps.
- One proactive override (the IMU-style part's library, corrected from the engine's valid-but-wrong `Atomic_Timer` mis-suggestion to `Atomic_Sensor_Motion`) is set before the loop starts, matching the 13-CONTEXT "Research defaults" note that this correction belongs to the owner, not the gate.
- After `apply_migration` succeeds and tags `Custom` `pre-atomic` at the pre-migration HEAD, `scan_all` on the real post-migration tree confirms every Custom symbol library is `Atomic_`-prefixed, the only Custom footprint library left is `Atomic_Footprints`, every `Atomic_` library's checked symbols carry zero violations, no `.bak` remains, and both board-feature footprints (`USB-A-PCB`, `TESTPOINT-1`) are still present under `Atomic_Footprints.pretty`.
- `build_migration_commit_plan` hands off to the unchanged Phase 11 `commit_step.probe_commit` / `run_commit(bump_parent=True)`: one Custom commit (verified via `git show --stat HEAD` to hold `MIGRATION-ATOMIC.md`, and via `git rev-list --count` to be exactly one commit past the pre-migration HEAD) plus one parent-repo gitlink commit.

## Task Commits

1. **Task 1: The whole v1 Custom migrates and commits end to end (MIG-01, MIG-03, MIG-04, MIG-05, D-04)** - `e797d5d` (test)

**Plan metadata:** committed together with this SUMMARY (see Self-Check below for the commit hash).

## Files Created/Modified

- `tests/test_migration_full.py` - the phase's one whole-fixture end-to-end test (`test_whole_v1_custom_migrates_to_zero_violations`, `requires_git`)

## Decisions Made

See frontmatter `key-decisions`: the official-footprint fallback for symbols with no Footprint field at all (MAX17048G/X), and resolving a shared footprint's "model" StripLine back to its first linking key before setting `model_source`.

## Deviations from Plan

None - plan executed exactly as written. The task's own `<behavior>` spec anticipated exactly the two gaps the test discovered at runtime (a model-less footprint needing a model source, and gate-reported gaps needing per-field fills); working out the `footprint_name` and shared-footprint `model` cases followed directly from reading the already-merged `footprints.py`/`gate.py` modules (plans 13-10, 13-06/13-12), not from any bug in them.

## Issues Encountered

None. The merged pipeline (planner, gate, applier, commitplan, the post-7f3d06a `plan_symbols` extends fix) worked end to end on the first full run once the fill loop correctly handled the official-footprint and shared-footprint-model cases; no service module needed a change.

## Known Stubs

None.

## Threat Flags

None — the only new surface is a test file building every repo under `tmp_path` via `gitfixtures.make_superproject`; it never reads or writes the owner's live `Custom/` (this plan's own `<threat_model>` T-13-46, mitigated by `tmp_path` construction and the suite-wide `_live_custom_untouched` guard, which stays in force and was not touched).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The services of plans 13-05 through 13-13 are now proven together against the full fixture, against real git, satisfying this phase's MIG-01/MIG-03/MIG-04/MIG-05 at the service level. The window (plan 13-14/13-15, `widgets/migration_dialog.py`) is the remaining consumer; this plan's test does not touch it.
- `tests/test_migration_full.py` is intentionally the only place the slow real-git whole-fixture path runs per task; the phase gate (plan 13-18) runs it again as part of the full suite.
- No blockers.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: tests/test_migration_full.py
- FOUND: commit e797d5d (Task 1)
- `grep -n "scan_all(" tests/test_migration_full.py` -> found (line 170)
- `grep -n "before_first_write=" tests/test_migration_full.py` -> found (line 163)
- `python -m pytest tests/test_migration_full.py -q` -> 1 passed (run twice, no flakiness observed)
- `python -m pytest tests/test_migration_full.py tests/test_migration_commit.py tests/test_migration_apply.py tests/test_migration_symbols.py tests/test_migration_footprints.py tests/test_migration_families.py tests/test_migration_gate.py -q` -> 62 passed
