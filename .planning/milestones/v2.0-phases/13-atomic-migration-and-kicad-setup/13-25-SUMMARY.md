---
phase: 13-atomic-migration-and-kicad-setup
plan: 25
subsystem: importer-suggestion
tags: [siblings, family-vote, suggest-library, categories, sensor-motion, gap-closure]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: suggest_library own -> stock -> category -> ask order (D-01), family_prefixes / pick
  - phase: 13-atomic-migration-and-kicad-setup
    provides: migration planner that copies suggestion.name into the target library (MIG-02)
provides:
  - separator-aware family_prefixes (ICM-42688-P -> ICM-42688, ICM-4, ICM-, ICM)
  - SiblingPick.weak and LibrarySuggestion.weak (consumed by plan 13-26)
  - a weak vote yields to the part's own description
  - Sensor_Motion category rule widened with motion words and placed before Sensor_Magnetic
affects: [13-26, 13-28]

actuals:
  tokens: 14000
  tasks: 3
  commits: 4

plan_head_before: 32f33940f3e6a0dc91cce3859cd7c9cb2295e2b3
plan_head_after: 07bc6b2d89337043445ca34a3067c6f4297dceaf

tech-stack:
  added: []
  patterns:
    - "weak as a read-only property on the frozen SiblingPick (equality in tests unchanged) and a defaulted last field on LibrarySuggestion"
    - "one from_vote helper routes both decided votes (own, stock) through the description check"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/siblings.py
    - kicad_lib_manager/importer/suggest.py
    - kicad_lib_manager/importer/categories.py
    - tests/test_siblings.py
    - tests/test_suggest_atomic.py
    - tests/test_categories.py
    - tests/migrationfixtures.py
    - tests/test_migration_symbols.py
    - tests/test_migration_full.py

key-decisions:
  - "A single - or _ between the leading letters and the first digit run stays in the prefix steps; a separator followed by a letter adds no step, so every pre-existing prefix expectation is unchanged"
  - "weak = decided vote on the bare letters, or won with under three quarters of the siblings at its step (top*4 < total*3)"
  - "A weak own vote is still returned before the stock lookup (Phase 10 D-01 order); it is only checked against classify"
  - "Both vote and category results still pass through the allowed-stems filter (LIB-04)"

patterns-established:
  - "Stock fixtures for the migration mirror KiCad 10's real names (Timer ICM7xxx decoys + Sensor_Motion ICM-2xxxx)"

requirements-completed: [MIG-02]

duration: 25min
completed: 2026-11-13
status: complete
---

# Phase 13 Plan 25: Separator-aware family vote and weak-vote description check Summary

**ICM-42688-P now votes 2 of 2 into KiCad's Sensor_Motion at the `ICM-` step instead of 4 to 2 into Timer on the bare letters, and any coarse or close vote is flagged `weak` and overruled by the part's own description (closes the matching half of gap G-13-1-f).**

## Performance

- **Duration:** about 25 min
- **Completed:** 2026-11-13
- **Tasks:** 3 (Task 3 changed no file)
- **Files modified:** 9

## Accomplishments

- `family_prefixes` keeps the `-` or `_` before the first digit run: `ICM-42688-P` yields `ICM-42688`, `ICM-4`, `ICM-`, `ICM`; `ATXK-H14-...`, `USB4145-03-0170-C`, `RS3-1212S/H3`, `CSD85301Q2` yield what they yielded before.
- `SiblingPick.weak` property (letters-only prefix, or winner under three quarters of the siblings; an undecided pick is never weak).
- `LibrarySuggestion.weak` (last field, defaulted) and `suggest_library`'s `from_vote` helper: a weak decided vote is checked once against `classify`. A different stem wins as source `category` with the vote's winner kept as an alternative; the same stem keeps the vote and clears `weak`; no stem keeps the vote and sets `weak=True`. Strong votes return exactly as before. Own then stock then category then ask order and every reason text are unchanged.
- Sensor_Motion rule gains `6 axis`, `9 axis`, `motion sensor`, `motion tracking`, `motiontracking`, `inertial` and now precedes Sensor_Magnetic, so a 9-axis IMU naming its magnetometer is a motion sensor while "3-axis magnetometer" stays Sensor_Magnetic. "3 axis" and "mems" were deliberately not added.
- `write_v1_stock` now mirrors KiCad 10 (Timer ICM7209/7555xB/7555xP/7556 plus Sensor_Motion ICM-20602/ICM-20948); the whole-v1 migration test starts from `MigrationChoices()` and asserts the IMU's `PartPlan.target_library == "Atomic_Sensor_Motion"`.

## TDD record

Both tracer/auto tasks ran RED then GREEN with separate commits.

- **Task 1 RED (e84fe3c):** 10 target tests failed on the planned assertions (for example `family_prefixes("ICM-42688-P")` returned `['ICM']`, the stock vote returned Timer, `SiblingPick` has no `weak`). Semantic assessment: each failure was the target test reaching its planned assertion; no collection, import or fixture fault. `test_whole_v1_custom_migrates_to_zero_violations` failed on `'Atomic_Timer' == 'Atomic_Sensor_Motion'` only after the tools in that test were given computed `allowed_stems` (see Deviations).
- **Task 1 GREEN (e59d423):** siblings.py only; the five verify files pass (69 passed, 61 before).
- **Task 2 RED (6f36340):** 6 target tests failed (3 `weak` attribute/assertion failures in test_suggest_atomic, 3 classify rows returning None or Sensor_Magnetic).
- **Task 2 GREEN (07bc6b2):** suggest.py and categories.py; the eight-file verify command passes (184 passed, 12 skipped).
- `gsd_run check tdd-red-evidence` is not available in this worktree (no `.claude/gsd-core`), so the machine classifier was not run; the evidence is the pytest output above, inspected by hand.
- No REFACTOR commit (nothing to clean up).

## Task Commits

1. Task 1 RED: `e84fe3c` test(13-25)
2. Task 1 GREEN: `e59d423` feat(13-25)
3. Task 2 RED: `6f36340` test(13-25)
4. Task 2 GREEN: `07bc6b2` feat(13-25)
5. Task 3: no commit (verification only, nothing to change)

## Importer expectations changed (Task 3)

No importer expectation changed. `tests/test_import_dialog.py`, `tests/test_suggest_atomic.py`, `tests/test_migration_full.py`, `tests/test_migration_dialog.py`, `tests/test_importer_layering.py` pass without edits (313 passed). `test_opening_csd_in_the_dialog_prefills_the_family_library_with_its_reason` was skipped by design (the licensed Ultra Librarian sample is not in the worktree); its assertion path is covered by `test_a_weak_vote_nothing_contradicts_is_kept_and_marked_weak`, where CSD85301Q2 with no description keeps Atomic_Transistor_FET / stock and the same reason text (the CSD vote is on the letters, so it is weak but nothing contradicts it).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in test setup] The whole-v1 migration test never exercised the suggestion**
- **Found during:** Task 1 RED
- **Issue:** `test_whole_v1_custom_migrates_to_zero_violations` built `ToolContext` without `allowed_stems`; the empty default filters every suggestion to "ask", so the old test only passed because the gate's library line was answered from `EXPECTED_TARGETS` by the generic fill loop. With `MigrationChoices()` and no change, the new `Atomic_Sensor_Motion` assertion passed on the old code (not a real RED).
- **Fix:** the test's `ToolContext` now passes `allowed_stems=stems.allowed_stems(stems.installed_stems(stock_symbols_dir))`, mirroring `detect_tools()` and `test_migration_symbols._tools`. The assertion then failed on the old code (`Atomic_Timer`) and passes with the fix.
- **Files modified:** tests/test_migration_full.py
- **Commit:** e84fe3c

**Total deviations:** 1 auto-fixed (test setup). **Impact:** none on production code; the whole-fixture test now really proves the IMU is placed by the suggestion.

## Known Stubs

None.

## Threat Flags

None. T-13-65 and T-13-67 mitigated as planned (separator-aware steps, weak vote checked against the description, both results still through the stems filter; `test_a_suggestion_is_empty_or_passes_the_name_rule_and_never_holds_a_manufacturer` passes). No test reads the live `Custom/`; the live-KiCad 10 test only reads the installed stock symbols and ran (KiCad 10 present).

## Issues Encountered

None. Verification limits: tests that need `downloaded_examples/` samples or the `Custom/` submodule skip in this worktree by design; the orchestrator runs the full suite once after the last wave (plan 13-28).

## Next

Ready for plan 13-26, which builds the visible "check this library" line on `LibrarySuggestion.weak`.

## Self-Check: PASSED

- Modified files exist: siblings.py, suggest.py, categories.py, the six test files (verified by passing test runs).
- Commits exist on this branch: e84fe3c, e59d423, 6f36340, 07bc6b2.
