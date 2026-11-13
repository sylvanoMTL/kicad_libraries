---
phase: 10-importer-on-the-atomic-scheme
plan: 12
subsystem: importer
tags: [kicad, footprints, atomic-scheme, planner, pytest]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "InstallPlan.footprint_library / footprint_link and the two-nickname table step (10-11), stems.SHARED_FOOTPRINT_LIBRARY (10-01), footprint_library_for test helper (10-02)"
provides:
  - "Every imported footprint installs into Custom/Footprints/Atomic_Footprints.pretty and the symbol's Footprint field reads Atomic_Footprints:<FP>"
  - "A new Atomic_ symbol library writes only its .kicad_sym; no <library>.pretty and no pair-completion warning"
  - "mkdir of Atomic_Footprints.pretty only on first use; case twin of the shared folder refused with install.library_case_clash"
  - "InstallPlan.pretty_path is the shared folder; InstallPlan.new_library means a new symbol library"
affects: [10-13, 10-14, 10-15, table step, preview, commit message]

actuals:
  tokens: 36000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "One shared footprint folder: footprint conflict key is footprint:Atomic_Footprints:<name>, the same item for every symbol library"
    - "Test scans list the shared Atomic_Footprints folder once (dedupe by rel_path)"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/plan.py
    - kicad_lib_manager/importer/planner.py
    - tests/zipfixtures.py
    - tests/test_shared_footprints.py
    - tests/test_install_plan.py
    - tests/test_install_e2e.py
    - tests/test_import_preview.py
    - tests/test_import_dialog.py
    - tests/test_main_window_import.py

key-decisions:
  - "The symbol case-twin check compares only symbol libraries; a separate refusal covers a footprint folder that differs from Atomic_Footprints only by letter case"
  - "The footprint conflict key uses the shared name, so a footprint overwrite/rename choice carries over when the user switches symbol library (same footprint item)"
  - "The missing-folder refusal names the library it would create: the symbol library for Custom/Symbols, Atomic_Footprints for Custom/Footprints"

patterns-established:
  - "Tests that need Atomic_Footprints absent from the fp table use usb_tables(..., shared_listed=False)"

requirements-completed: [LIB-06]

duration: 55min
completed: 2026-10-27
status: complete
plan_head_before: 71408efe95de0ebde11224c194df344f3204b05e
plan_head_after: 875d506afb1f3aace4c105b2da7a1c758f19a076
---

# Phase 10 Plan 12: Shared Atomic_Footprints Library Summary

**Footprints now always install into the shared Atomic_Footprints.pretty and link as Atomic_Footprints:<FP>; a new symbol library comes alone with no matching .pretty and no pair warning.**

## Performance

- **Duration:** about 55 min (most of it waiting on the 10-minute suite)
- **Completed:** 2026-10-27T12:23Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- planner: `pretty`, `pretty_exists`, the first render link, the footprint conflict key, the symbol `link` and `InstallPlan.footprint_library` all use the shared library; the pair-completion warning block is gone; the folder-missing refusal names Atomic_Footprints for Custom/Footprints; a folder that differs from Atomic_Footprints only by case is refused with `install.library_case_clash`.
- plan: `pretty_path` is the shared folder; `new_library` is the new-symbol-library state (the shared folder's own state stays in `new_footprint_lib`).
- `zipfixtures.footprint_library_for` returns "Atomic_Footprints", so tests routed through it in 10-07 to 10-09 followed without edits.
- Tracer (CSD85301Q2 into new Atomic_Transistor_FET) planned, applied and verified end to end: mkdir of Atomic_Footprints.pretty, the footprint in it, only `Atomic_Transistor_FET.kicad_sym` for the symbol side, link `Atomic_Footprints:DQK0006B`, `verify_install` clean.
- Rules tested: case-twin refusal text, missing-folder wording, no mkdir when the shared folder exists, a second new library reuses the first install's folder, an existing symbol library with no footprint folder installs with one mkdir and no warning.
- Full `-m "not wurth"` suite: 2634 passed, 13 skipped (Custom submodule absent in the worktree, two symlink privilege skips), 0 failed.

## Task Commits

1. **Task 1: tracer, planner/plan switch, helper switch** - `e768740` (feat)
2. **Task 2: shared-library rules, LIB-02 tests and outcome-changing tests** - `875d506` (test)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `kicad_lib_manager/importer/planner.py` - shared destination, no pair completion, shared-library case-twin refusal
- `kicad_lib_manager/importer/plan.py` - `pretty_path` of the shared folder, `new_library` as new symbol library
- `tests/zipfixtures.py` - `footprint_library_for` returns the shared library
- `tests/test_shared_footprints.py` - tracer and rule tests
- `tests/test_install_plan.py` - LIB-02 tests rewritten (a new symbol library creates only its .kicad_sym)
- `tests/test_install_e2e.py` - new-library, header and CLI-version scenarios without the pair warning
- `tests/test_import_preview.py`, `tests/test_import_dialog.py` - no folder row when the shared folder exists; shared-folder mkdir row tested on its own; conflict choice follows the shared footprint key
- `tests/test_main_window_import.py` - scan fixture lists the shared folder once; table tests state whether Atomic_Footprints is already listed

## Decisions Made

See key-decisions. The conflict key change is a deliberate consequence of D-15: with one shared folder a clashing footprint is the same item whichever symbol library is picked, so its resolution carries over; the symbol conflict key still includes the symbol library.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in tests] Files outside the plan's list needed the same treatment**
- **Found during:** Task 2 (full suite run)
- **Issue:** `tests/test_main_window_import.py` (flagged by the 10-09 notes, not in this plan's file list) failed in 10 tests because USB, FFC and installed footprint libraries now map to one nickname and the fp table already listed Atomic_Footprints.
- **Fix:** scan fixture dedupes footprint libraries by rel_path; `usb_tables(shared_listed=False)` models "first use"; one new test covers "already listed, only the symbol is added"; expectations otherwise unchanged in intent.
- **Files modified:** tests/test_main_window_import.py
- **Committed in:** 875d506

**2. [Rule 1 - Test rewritten for new semantics] test_conflict_choice_carried_by_key**
- **Found during:** Task 2
- **Issue:** The test asserted that a footprint choice does not move to another symbol library; with the shared folder the footprint is one item, so the choice now carries.
- **Fix:** the test asserts the carry-over instead, keeping the rename/restore part of the flow.
- **Files modified:** tests/test_import_dialog.py
- **Committed in:** 875d506

---

**Total deviations:** 2 auto-fixed (test-side only). **Impact on plan:** no production-code scope beyond the plan.

## Issues Encountered

- Several test files are CRLF; scripted edits had to preserve line endings (one edit initially broke a string literal and was fixed before commit).
- The plan's acceptance check `git -C Custom status --short` could not be run: the Custom submodule is not checked out in the worktree. No test or tool wrote to it (the suite's guard covers the orchestrator checkout).
- The plan commit ledger file was not created at the first commit (a compound git command was refused), so `commits:` was measured as `git rev-list --count 71408ef..HEAD` before the SUMMARY commit (2).

## Known Stubs

None.

## Threat Flags

None. T-10-14 (shared folder tampering) is mitigated as planned: an existing footprint of the same name is still a Conflict needing Overwrite, Rename or Skip, and the case-twin refusal keeps one folder per name.

## User Setup Required

None.

## Next Phase Readiness

Ready for 10-13. Known follow-ups per the plan: the "new" badge text and the picker's library list are plan 10-15; the linking-symbols warning is plan 10-14. The orchestrator's post-merge run in the main checkout covers the Custom-dependent tests that skip here.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*

## Self-Check: PASSED

- Files exist: plan.py, planner.py, zipfixtures.py, test_shared_footprints.py, this SUMMARY.
- Commits e768740 and 875d506 are ancestors of HEAD.
- Acceptance: pair_completed absent from planner.py (non-comment) and test_install_plan.py; SHARED_FOOTPRINT_LIBRARY appears 6 times in planner.py; `return "Atomic_Footprints"` once in zipfixtures.py; CURRENT_ATOMIC_FOOTPRINT_LIBS prints ('Atomic_Footprints',).
