---
phase: 10-importer-on-the-atomic-scheme
plan: 09
subsystem: testing
tags: [pytest, atomic-naming, footprint-library-for, git-fixtures, import-dialog]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: atomic_custom fixture, footprint_library_for helper, CURRENT_ATOMIC_* lists (plan 10-02)
provides:
  - scratch Custom/ git repositories that hold Atomic_ install targets beside the v1 mirror
  - commit, preview, form, dialog and main-window import tests installing into Atomic_ libraries
  - every footprint location of an install target in these tests routed through footprint_library_for
affects: [10-10, 10-12, 10-15, 13]

actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: b4f956441ef5cab68b1bc6efe104c5a92c09da70
plan_head_after: fe52b8083707a41486b92ec4f359663e61c0481b

tech-stack:
  added: []
  patterns:
    - "Layouts that model the live tree hold the v1 mirror and the Atomic_ targets side by side, so v1 on-purpose tests and Atomic_ install tests share one fixture"
    - "A test names an install target's footprint library only as footprint_library_for(target), usually through a module constant (FP_LIB, USB_FP_LIB)"

key-files:
  created: []
  modified:
    - tests/gitfixtures.py
    - tests/test_commit_plan.py
    - tests/test_commit_step.py
    - tests/test_import_preview.py
    - tests/test_import_form.py
    - tests/test_import_dialog.py
    - tests/test_main_window_import.py

key-decisions:
  - "Scratch Custom/ and the dialog item_layout keep the v1 libraries and add the Atomic_ ones, so the placeholder, case-twin, token-line and v1 alternatives tests (plans 10-10, 10-15) stay untouched and green"
  - "Atomic_Connector_Audio, Atomic_Sensor_Energy and Atomic_Power_Supervisor are added to the scratch layouts because the commit and conflict tests edit those libraries in place"
  - "In item_layout the motion sensor keeps a symbol library with no footprint folder, as its v1 twin has"

patterns-established:
  - "Module constants LIB / FP_LIB, USB_LIB / USB_FP_LIB, NEW_LIB / NEW_FP_LIB per test file, so one helper change moves every footprint expectation"

requirements-completed: [LIB-05, LIB-06]

coverage:
  - id: D1
    description: "Commit plan and commit step tests install into an Atomic_ library of a scratch Custom/ git repository, with footprint paths and links from footprint_library_for"
    requirement: LIB-05
    verification:
      - kind: integration
        ref: "tests/test_commit_plan.py tests/test_commit_step.py tests/test_gitops.py (122 passed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Preview, form, import dialog and main-window import tests use Atomic_ install targets; on-purpose v1, placeholder and invalid-name tests are untouched"
    requirement: LIB-05
    verification:
      - kind: integration
        ref: "tests/test_import_preview.py tests/test_import_form.py tests/test_import_dialog.py tests/test_main_window_import.py (20 + 28 + 174 + 34 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Footprint locations of install targets in these seven files go through footprint_library_for, so plan 10-12 changes one function"
    requirement: LIB-06
    verification:
      - kind: other
        ref: "grep: no Atomic_<name>.pretty literal in the six test files; footprint_library_for( appears 7 times in test_import_dialog.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "The not-wurth suite is green after the migration"
    verification:
      - kind: integration
        ref: "pytest -m 'not wurth' -q: 2355 passed, 26 skipped"
        status: pass
    human_judgment: false

duration: 75min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 09: Import tests on Atomic_ targets Summary

**The commit, preview, form, dialog and main-window import tests now install into Atomic_ libraries (scratch Custom/ repositories hold them beside the v1 mirror), and every footprint location of an install target comes from `footprint_library_for`.**

## Performance

- **Duration:** about 75 min (two long test runs: 4 min for the commit files, 10 min for the full suite)
- **Completed:** 2026-10-27T10:22:30Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- `tests/gitfixtures.py`: default install target `Atomic_Battery_Management`; the scratch Custom/ it builds also holds the nine Atomic_ libraries plus `Atomic_Connector_Audio`; the commit plan's footprint link is `footprint_library_for(library):FP1`.
- `tests/test_commit_plan.py` and `tests/test_commit_step.py`: install targets, expected staged paths, commit subjects and footprint lines use the Atomic_ names and the helper (`FP_LIB`, `FFC_LIB`, `USB_LIB`); the real Ultra Librarian plan test runs on `atomic_custom`.
- `tests/test_import_preview.py`, `tests/test_import_form.py`: `UL_LIBRARY`, `LIBRARY` / `TEST_LIBRARY`, new-library targets, the badge and the kicad-cli cache steps moved; conflict keys, expected rows and layouts use the helper.
- `tests/test_import_dialog.py`: `LIB`, `OTHER_LIB`, the new-library targets, `make_dialog` (now on `atomic_custom`) and `item_layout` (v1 mirror plus Atomic_ targets) moved; Footprint field, file rows, conflict keys and the SnapEDA connector test use the helper.
- `tests/test_main_window_import.py`: `LIB`, `NEW_LIB`, and the USB / FFC libraries became `Atomic_Battery_Management`, `Atomic_Sensor_Temperature`, `Atomic_Connector` and `Atomic_Connector_Audio`, with footprint folders and table entries from the helper.
- Left alone on purpose: placeholder reason and `IC_SubCategory_TI` tests, case-twin and invalid-name tests, `library_tokens` / token-line / token-hint / v1 alternatives tests and the 60-character geometry name (plans 10-10, 10-15).

## Task Commits

1. **Task 1: install into an Atomic_ library committed in a scratch Custom/ repository** - `fb2ded2` (test)
2. **Task 2: preview, form, dialog and main-window import tests on Atomic_ targets** - `fe52b80` (test)

**Plan metadata:** committed with this summary (docs)

## Files Created/Modified
- `tests/gitfixtures.py` - Atomic_ libraries in the scratch Custom/, default target, helper-based footprint link
- `tests/test_commit_plan.py`, `tests/test_commit_step.py` - Atomic_ targets and `footprint_library_for` paths
- `tests/test_import_preview.py`, `tests/test_import_form.py` - Atomic_ targets, helper-based rows, keys and layouts
- `tests/test_import_dialog.py` - Atomic_ targets, `atomic_custom` dialog, item layout with both naming schemes
- `tests/test_main_window_import.py` - Atomic_ library constants, helper-based footprint folders and table entries

## Decisions Made
- The scratch git Custom/ and the dialog `item_layout` hold the v1 mirror and the Atomic_ libraries together. Plan rule 2 (stay on the v1 tree for tests that model the live tree) and rule 4 (leave the on-purpose v1 tests) would otherwise need a second layout fixture; with one combined layout the untouched tests keep passing unchanged and the Atomic_ install tests find their existing libraries.
- Names not in `CURRENT_ATOMIC_SYMBOL_LIBS` that the mapping requires (`Atomic_Connector_Audio`, `Atomic_Sensor_Energy`, `Atomic_Power_Supervisor`) are added in the test layouts, not in `zipfixtures`, to leave plan 10-02's constants alone.

## Deviations from Plan

None - plan executed exactly as written.

Two shape choices stayed inside the plan's rules and are recorded here: the form file's `test_library_badge` (a pure name test, not a v1 suggestion test) moved to Atomic_ names, and `make_dialog` moved to `atomic_custom` while `item_layout` stayed a hand-built layout extended with the Atomic_ libraries.

## Issues Encountered
- The `git -C Custom status` acceptance check cannot run in the worktree because the Custom submodule is not checked out; the session guard in `tests/conftest.py` covers the live Custom/ (the full run passed it), and the orchestrator's post-merge run in the main checkout covers the live tree.
- The worktree plan ledger file was created before the first commit (base `b4f9564`), so `commits: 2` is measured with `git rev-list --count`.

## Known Stubs
None.

## Threat Flags
None. The commit fixtures still build their repositories in a temporary directory (T-10-39); the dialog and main-window tests write only under `tmp_path`, and the full suite passed the live-Custom guard.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
Plan 10-10 (name rule) and plan 10-15 (suggestion and picker) can rewrite the on-purpose v1 tests, which are untouched here. Plan 10-12 can change `footprint_library_for` and the planner together: the scratch layouts deduplicate footprint libraries, and the only expectations that name a library-specific `.pretty` folder (the new-library `mkdir` rows in `test_import_preview.py` and `test_import_dialog.py`) are the ones plan 10-12 will meet first.

## Self-Check: PASSED

- Commits `fb2ded2` and `fe52b80` exist on this branch.
- Seven modified files present; `grep` finds no `Atomic_<name>.pretty` literal in the six migrated test files.
- `pytest -m "not wurth" -q`: 2355 passed, 26 skipped.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*
