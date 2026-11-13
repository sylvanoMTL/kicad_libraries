---
phase: 10-importer-on-the-atomic-scheme
plan: 13
subsystem: importer
tags: [kicad, footprints, atomic-scheme, planner, preview, pyside6, pytest]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "Shared Atomic_Footprints library, Atomic_Footprints:<FP> links, no pair completion (10-12)"
provides:
  - "InstallOptions.footprint (one vendor footprint) replaces footprints; InstallPlan.unused_footprints lists the rest"
  - "A 'Not used' preview section (row kind unused, tone muted) after Field changes"
  - "A single-choice footprint combo in the dialog (_fp_combo, _on_footprint_changed) in place of the checklist and Make linked"
  - "FormValues.footprint; FormStatus and the reasons lose the several-footprints checklist state"
affects: [10-14, 10-15, commit message, official-footprint picker]

actuals:
  tokens: 30000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "build_plan keeps single-element footprint lists internally; only _select and the plan record change shape"
    - "Footprints the part does not use are plan data (unused_footprints), never file ops"

key-files:
  created:
    - tests/test_single_footprint.py
  modified:
    - kicad_lib_manager/importer/plan.py
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/preview.py
    - kicad_lib_manager/importer/form.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_install_plan.py
    - tests/test_import_form.py
    - tests/test_import_dialog.py
    - tests/test_atomic_targets.py

key-decisions:
  - "The footprint row of the dialog's item picker keeps the short label 'Footprint' (accessible name 'Vendor footprint' on the combo): a longer row label widened the left pane past its viewport and failed two geometry tests"
  - "build_options names the edited footprint name against values.footprint, falling back to the linked_vendor argument"
  - "A package with several footprints and no choice is refused at plan level (install.choice_required, target footprints); the dialog combo always holds a choice, so the dialog itself never raises that reason"

patterns-established:
  - "Not used section: one muted row per unused footprint, 'footprint, not installed: one footprint per part'"

requirements-completed: [LIB-06]

duration: 75min
completed: 2026-10-27
status: complete
plan_head_before: 96b9e81b9e4fa9a30a6d09d2566d1c82d8ebaae2
plan_head_after: f043555f94fdffa49507bab7d9635509eca438d6
commits: 3

coverage:
  - id: D1
    description: "An atomic part installs exactly one footprint: the chosen vendor footprint is the only one written; several footprints with no choice is refused with install.choice_required naming them"
    requirement: LIB-06
    verification:
      - kind: unit
        ref: "tests/test_single_footprint.py#test_chosen_footprint_alone_is_planned_and_the_rest_are_not_used"
        status: pass
      - kind: unit
        ref: "tests/test_single_footprint.py#test_several_footprints_without_a_choice_is_refused"
        status: pass
      - kind: unit
        ref: "tests/test_install_plan.py#test_several_footprints_only_the_chosen_one_is_installed_and_filtered"
        status: pass
    human_judgment: false
  - id: D2
    description: "Unused footprints are listed in InstallPlan.unused_footprints and shown in a 'Not used' preview section; none is written"
    requirement: LIB-06
    verification:
      - kind: unit
        ref: "tests/test_single_footprint.py#test_chosen_footprint_alone_is_planned_and_the_rest_are_not_used"
        status: pass
      - kind: unit
        ref: "tests/test_single_footprint.py#test_single_footprint_package_has_nothing_unused"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Footprint field and ki_fp_filters name only the chosen footprint, and the 3D model is linked from it"
    requirement: LIB-06
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_several_footprints_the_chosen_one_carries_the_model"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_footprint_field_and_filters_follow_the_chosen_footprint"
        status: pass
    human_judgment: false
  - id: D4
    description: "The dialog's footprint choice is a single-choice combo; picking another footprint rebuilds the plan and resets the editable footprint name to that footprint's vendor name; the checklist, Make linked and the 'Select at least one footprint' reason are gone"
    requirement: LIB-06
    verification:
      - kind: unit
        ref: "tests/test_single_footprint.py#test_dialog_combo_lists_the_footprints_and_choosing_one_links_it"
        status: pass
      - kind: unit
        ref: "tests/test_single_footprint.py#test_dialog_footprint_name_follows_the_choice_and_an_edit_survives_a_rebuild"
        status: pass
      - kind: unit
        ref: "tests/test_single_footprint.py#test_dialog_has_no_footprint_checklist_and_no_select_one_reason"
        status: pass
    human_judgment: false
  - id: D5
    description: "How the single-choice footprint row, its combo and the Not used rows look and read in the real dialog"
    verification: []
    human_judgment: true
    rationale: "Layout and wording quality are visual; only geometry (no horizontal overflow) is asserted by tests"
---

# Phase 10 Plan 13: Single-Choice Footprint Summary

**An atomic part now installs exactly one vendor footprint, picked from a single-choice combo in the import dialog; the other footprints in the package are listed under a "Not used" preview section and never written.**

## Performance

- **Duration:** about 75 min
- **Tasks:** 3 (one tracer, two auto)
- **Files modified:** 10 (1 created)
- **Suite:** `-m "not wurth"`: 2623 passed, 30 skipped (all skips are the usual absent-sample or absent-Custom ones); after the 3 geometry failures below were fixed, the dialog, main-window and single-footprint files were re-run green (222 passed)

## Accomplishments

- `InstallOptions.footprint` replaces `footprints`. `planner._select` returns the named footprint, else the only one, else `install.choice_required` naming the candidates; an unknown name is `install.unknown_item`. `build_plan` records every other package footprint in `InstallPlan.unused_footprints`, so no unused footprint can reach a file op (T-10-16).
- `preview.py` gets a "Not used" section after Field changes, one muted `unused` row per footprint ("footprint, not installed: one footprint per part"). Rows are plain text (T-10-17).
- The dialog shows a single-choice combo (`_fp_combo`) when the package holds several footprints. `_on_footprint_changed` links the choice, resets the footprint name to that footprint's vendor name (still editable, D-20) and rebuilds. The checklist, Make linked, "(linked)" suffix and their handlers are deleted.
- `FormValues.footprint` replaces `footprints`; `FormStatus` loses `several_footprints` and `footprints_checked`; the "Select at least one footprint" reason is gone. `install.choice_required` about footprints still targets "footprints" (now the combo).
- New `tests/test_single_footprint.py` (9 tests, plan to dialog) and the multi-footprint tests of the suite rewritten to single choice.

## Task Commits

1. **Task 1: tracer, F2 of three footprints from combo to Not used rows** - `fef1fb1` (feat)
2. **Task 2: checklist code, FormStatus fields and reason removed** - `0f0c674` (refactor)
3. **Task 3: multi-footprint tests rewritten across the suite** - `f043555` (test)

**Plan metadata:** committed separately with this SUMMARY (docs).

## Files Created/Modified

- `kicad_lib_manager/importer/plan.py` - `InstallOptions.footprint`, `InstallPlan.unused_footprints`
- `kicad_lib_manager/importer/planner.py` - single-footprint `_select`; `unused_footprints` on the plan
- `kicad_lib_manager/importer/preview.py` - `_unused_section`, `unused` row kind
- `kicad_lib_manager/importer/form.py` - `FormValues.footprint`, `build_options`, trimmed `FormStatus` and reasons
- `kicad_lib_manager/widgets/import_dialog.py` - `_fp_combo`, `_on_footprint_changed`, checklist removed
- `tests/test_single_footprint.py` - new single-choice tests
- `tests/test_install_plan.py`, `tests/test_import_form.py`, `tests/test_import_dialog.py`, `tests/test_atomic_targets.py` - migrated

## Decisions Made

- Keep the item-picker row label "Footprint" (combo accessible name "Vendor footprint"). A first attempt labelled the row "Vendor footprint"; that widened the left pane (398 px against a 364 px viewport) and failed two geometry tests, so it was reverted.
- `build_options` keys the edited footprint name on `values.footprint` and falls back to the `linked_vendor` argument, so existing callers keep working.
- `install.choice_required` for footprints stays a plan-level refusal (target "footprints"); the dialog cannot reach it because the combo always holds a choice.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Row label widened the left pane**
- **Found during:** Task 3 (full-suite run)
- **Issue:** The "Vendor footprint" row label made `test_fields_long_text_geometry` and `test_library_long_name_geometry` fail (left pane wider than its viewport).
- **Fix:** Row label back to "Footprint"; the combo keeps the accessible name "Vendor footprint" so it differs from the read-only Footprint field's accessible name.
- **Files modified:** `kicad_lib_manager/widgets/import_dialog.py`
- **Verification:** both geometry tests pass
- **Committed in:** `f043555`

**2. [Rule 1 - Test needs the new contract] Conflict overflow test assumed three footprint conflicts**
- **Found during:** Task 3
- **Issue:** `test_conflicts_overflow_geometry` seeded three existing footprints and expected three conflict rows; one footprint now yields one footprint conflict.
- **Fix:** Seeded one existing footprint and one existing model file (the two conflicts a single footprint can produce); the vertical-scroll and no-horizontal-overflow assertions are unchanged and still pass.
- **Files modified:** `tests/test_import_dialog.py`
- **Committed in:** `f043555`

**3. [Plan wording] Acceptance grep for `footprints=(` is not literally 0**
- The plan's acceptance criterion greps the four test files for `footprints=(`. The remaining hits are the `multi_zip(...)` and `_members(...)` test-helper keyword (package contents), not `InstallOptions`. `grep -c "InstallOptions(.*footprints=("` is 0 in all eight listed test files. No code change needed.

---

**Total deviations:** 2 auto-fixed (both Rule 1), 1 plan-wording note
**Impact on plan:** None on scope.

## Issues Encountered

None beyond the deviations. The full `-m "not wurth"` run takes about 10 minutes; the worktree lacks the Custom submodule and licence-restricted samples, so those tests skip here and are covered by the orchestrator's post-merge run.

## Known Stubs

None.

## Threat Flags

None. The plan's threat register (T-10-16, T-10-17) is mitigated and tested: one footprint op at most, unknown name refused, unused footprints only listed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for 10-14. The plan now carries `unused_footprints`, which the official-footprint option (D-16, D-17) can extend with the vendor footprint and STEP when an official footprint is chosen.

## Self-Check: PASSED

- `tests/test_single_footprint.py` and this SUMMARY exist; commits `fef1fb1`, `0f0c674`, `f043555` are on the branch.
- `tests/test_single_footprint.py`: 9 passed.
- `-m "not wurth"`: 2623 passed, 3 failed before the Task 3 fixes; the three failures were re-run and pass.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*
