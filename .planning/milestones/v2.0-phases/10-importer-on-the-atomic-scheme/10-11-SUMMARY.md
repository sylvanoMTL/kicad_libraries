---
phase: 10-importer-on-the-atomic-scheme
plan: 11
subsystem: importer
tags: [footprint-link, lib-table, post-install, atomic-scheme]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "Atomic_ name rule first in build_plan (plan 10-10); footprint_library_for test helper (plan 10-02)"
provides:
  - "InstallPlan.footprint_library and InstallPlan.footprint_link, read by verify, preview, commit message and import dialog"
  - "add_library_entries(dest, *, symbol=None, footprint=None) with one nickname per table"
  - "_PostInstall with separate symbol and footprint nicknames and a repo-only rule for fp-lib-table"
affects: [10-12 shared Atomic_Footprints library, 10-14]

actuals:
  tokens: 21000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Every consumer names the footprint library through plan.footprint_link, never plan.library"
    - "Table step takes (nickname, rel_path) pairs and touches only what is requested"

key-files:
  created:
    - tests/test_shared_footprints.py
  modified:
    - kicad_lib_manager/importer/plan.py
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/verify.py
    - kicad_lib_manager/importer/commit_plan.py
    - kicad_lib_manager/importer/preview.py
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/table_generator.py
    - kicad_lib_manager/main_window.py
    - tests/test_table_add_entries.py
    - tests/test_main_window_import.py
    - tests/test_commit_plan.py
    - tests/test_install_verify.py
    - tests/test_install_apply.py

key-decisions:
  - "Until plan 10-12 the planner sets footprint_library to the symbol library (None when the chosen symbol is kept with Skip), so no install, preview, verify or commit text changes"
  - "A footprint library is added to fp-lib-table only when it equals the plan's pretty_path folder name; one outside the repo never is (D-16)"
  - "The Library tables status row now shows the combined 'Added <sym> to sym-lib-table and <fp> to fp-lib-table' text from the Issue itself, and 'Not needed: existing libraries' when neither library is new"

requirements-completed: [LIB-06]

coverage:
  - id: D1
    description: "InstallPlan carries footprint_library and footprint_link; verify, the preview Footprint row, the commit message and the import dialog field all read footprint_link"
    requirement: LIB-06
    verification:
      - kind: unit
        ref: "tests/test_shared_footprints.py#test_footprint_link_runs_from_the_plan_to_every_consumer"
        status: pass
      - kind: unit
        ref: "tests/test_shared_footprints.py#test_verify_expects_the_plans_footprint_link"
        status: pass
      - kind: unit
        ref: "tests/test_shared_footprints.py#test_a_kept_symbol_links_no_footprint"
        status: pass
    human_judgment: false
  - id: D2
    description: "add_library_entries adds only the requested symbol and footprint entries, each under its own nickname, keeping every other byte and reporting external clashes"
    requirement: LIB-06
    verification:
      - kind: unit
        ref: "tests/test_table_add_entries.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Post-install step writes the symbol nickname to sym-lib-table when new and the footprint nickname to fp-lib-table only when new and in the repo"
    requirement: LIB-06
    verification:
      - kind: unit
        ref: "tests/test_main_window_import.py#test_tables_new_symbol_and_new_footprint_library_use_their_own_names"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_tables_only_the_footprint_library_is_new"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_tables_a_footprint_library_outside_the_repo_gets_no_fp_entry"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-10-27
plan_head_before: bfdd1601e63047845e7dc5cec2e313697918cdeb
plan_head_after: 4d16fa5dcf7c5dacc2a948b8c41975618dc88305
commits: 2
status: complete
---

# Phase 10 Plan 11: Separate symbol and footprint library names Summary

**InstallPlan now carries footprint_library/footprint_link that verify, preview, commit message and dialog read, and add_library_entries takes a symbol nickname and a footprint nickname separately, so plan 10-12 can move footprints to Atomic_Footprints by changing only the planner's choice.**

## Performance

- **Duration:** about 45 min (the not-wurth suite alone takes about 9 min)
- **Completed:** 2026-10-27
- **Tasks:** 2
- **Files modified:** 14 (one new)

## Accomplishments
- `InstallPlan.footprint_library` and the `footprint_link` property; the planner sets the footprint library to the symbol library (None for a kept symbol), so nothing the owner sees has changed yet.
- verify, the preview's Footprint row, the commit message and the import dialog's footprint field all read `footprint_link`.
- `add_library_entries(dest_folder, *, symbol=None, footprint=None)` adds only the requested entries, with the per-entry messages and the combined `table.entries_added` text when both are added.
- `_PostInstall` has `new_symbol_lib`, `footprint_library`, `fp_rel_path`, `new_footprint_lib`; a footprint library outside the repo is never added to fp-lib-table; the not-in-tables hint names one or two libraries.

## Task Commits

1. **Task 1: footprint_link from the plan to verify, the preview and the commit message** - `5804e69` (feat)
2. **Task 2: two nicknames in the post-install table step** - `4d16fa5` (feat)

## Files Created/Modified
- `kicad_lib_manager/importer/plan.py` - footprint_library field, footprint_link property
- `kicad_lib_manager/importer/planner.py` - sets footprint_library (symbol library for now)
- `kicad_lib_manager/importer/verify.py`, `commit_plan.py`, `preview.py`, `widgets/import_dialog.py` - read footprint_link
- `kicad_lib_manager/table_generator.py` - keyword-only add_library_entries
- `kicad_lib_manager/main_window.py` - _PostInstall and the post-install table step
- `tests/test_shared_footprints.py` - new contract tests (written to also hold after plan 10-12)
- `tests/test_table_add_entries.py`, `tests/test_main_window_import.py` - migrated and extended

## Decisions Made
- Footprint library is added to fp-lib-table only when its name equals the plan's `pretty_path` folder (D-16).
- The Library tables row takes its text from the `table.entries_added` Issue, so the wording follows the table step.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Hand-built InstallPlan in tests lacked footprint_library**
- **Found during:** Task 2 (full not-wurth run)
- **Issue:** `verify_install` now expects `plan.footprint_link`; plans built directly in `tests/test_install_apply.py`, `tests/test_install_verify.py` and `tests/test_commit_plan.py` set `linked_footprint` but not `footprint_library`, so 13 apply tests failed with `verify.link_unresolved` (expected '')
- **Fix:** added `footprint_library=...` to those helpers (the verify and commit_plan helpers in Task 1, the apply helper in Task 2)
- **Files modified:** tests/test_install_apply.py, tests/test_install_verify.py, tests/test_commit_plan.py
- **Verification:** `pytest tests/test_install_apply.py` 66 passed
- **Committed in:** 5804e69 and 4d16fa5

**2. [Rule 2 - Consistency] Import dialog footprint field read plan.library**
- **Found during:** Task 1
- **Issue:** `widgets/import_dialog.py` built the Footprint field text from `plan.library:plan.linked_footprint`, the same one-library assumption (not in the plan's file list)
- **Fix:** it reads `plan.footprint_link`
- **Files modified:** kicad_lib_manager/widgets/import_dialog.py
- **Committed in:** 5804e69

**3. Message wording moved with the new table text (planned migration)**
- `tests/test_main_window_import.py` expectations changed to "Added X to sym-lib-table and Y to fp-lib-table", "Not needed: existing libraries" and the two "already lists" lines; no other test needed a wording change.

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 consistency)
**Impact on plan:** Both necessary for correctness; no scope creep.

## Issues Encountered
- The first full `-m "not wurth"` run reported 13 failures, all in `tests/test_install_apply.py` (deviation 1). After the fix those tests pass (66 passed) and so do the task files and `tests/test_main_window.py`; the whole suite was not run a second time (about 9 minutes). First run otherwise: 2594 passed, 30 skipped (Custom submodule and licence-restricted samples absent in the worktree).
- `downloaded_examples/ul_CSD85301Q2.zip` was copied into the worktree for the tests; it stays gitignored.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
Plan 10-12 can set the planner's `footprint_library` to `Atomic_Footprints` and redefine `pretty_path`/`new_library`; verify, preview, commit text and the table step follow without further edits. `tests/test_shared_footprints.py` already compares against `footprint_link` and `footprint_library_for`.

## Self-Check: PASSED
- Files exist: tests/test_shared_footprints.py, plan.py, table_generator.py, main_window.py
- Commits 5804e69 and 4d16fa5 are on this branch
