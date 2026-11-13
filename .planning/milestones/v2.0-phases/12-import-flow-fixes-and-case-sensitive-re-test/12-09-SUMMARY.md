---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 09
subsystem: ui
tags: [pyside6, import-dialog, help, uat-gap-closure]

requires:
  - phase: 12-import-flow-fixes-and-case-sensitive-re-test
    provides: Finishing state (D-06) and the install/commit close refusal that Cancel reuses via reject()
provides:
  - Cancel button to the right of Install Part (reject path, greyed out during install and commit)
  - Required-field hints for Datasheet, Description and Manufacturer that match the atomic strip
  - Header button "Choose another package..." with a tooltip, public CHANGE_PACKAGE_TEXT constant
  - Help page "Importing Parts" updated for all three
affects: [12-10, 12-11, import dialog help text]

actuals:
  tokens: 9500
  tasks: 3
  commits: 6

plan_head_before: 458317feb681679ec2fbf47036f09787126fc146
plan_head_after: 9a46916b0f81c288c22b5c41b4a7890cee7f7fd3

tech-stack:
  added: []
  patterns:
    - "Button that must never act mid-write is synced by a _sync_*_button() method called from each worker-state setter"
    - "Help text inserts button labels by concatenating public constants from import_dialog"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_import_dialog.py
    - tests/test_help_dialog.py

key-decisions:
  - "Cancel is connected to self.reject, so Finishing (D-06) and the install/commit refusal in done() are reused with no new close logic"
  - "The required-field hints are static (_REQUIRED_HINTS), because every Atomic_ library needs all three fields and only Atomic_ targets are accepted"
  - "Help does not rewrite the Finishing paragraph beyond swapping the button label; plan 12-11 edits its last sentence"

patterns-established:
  - "_sync_cancel_button() is called at the end of _set_install_ui and in _set_git_worker"

requirements-completed: [REV-04]

coverage:
  - id: D1
    description: "Cancel to the right of Install Part closes the window without installing or writing; greyed out while an install or commit runs, enabled again after a failed install; during a rebuild it enters Finishing like the window X"
    requirement: REV-04
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_cancel_button_closes_without_installing"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_cancel_button_disabled_while_installing"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_cancel_button_enabled_again_after_failed_install"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_cancel_button_during_build_enters_finishing"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_commit_close_button_disabled_while_git_runs"
        status: pass
    human_judgment: false
  - id: D2
    description: "Datasheet, Description and Manufacturer hints read 'Required - ...' in the words of the atomic strip; Help says the three fields are required"
    requirement: REV-04
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_required_field_hints_match_the_atomic_strip"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_import_page_explains_fields_and_the_install_gate"
        status: pass
    human_judgment: false
  - id: D3
    description: "Header button reads 'Choose another package...' with a tooltip saying edits are dropped and nothing is written; Help names it in Start and in Install and result"
    requirement: REV-04
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_change_button_says_it_picks_another_package"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_names_choose_another_package"
        status: pass
    human_judgment: false
  - id: D4
    description: "UAT tests 6, 7 and 8 read well to the owner in the running window (placement, wording, visual weight of Cancel)"
    verification: []
    human_judgment: true
    rationale: "Button placement and wording adequacy are visual judgments no test asserts"

duration: 25min
completed: 2026-11-02
status: complete
---

# Phase 12 Plan 09: Import window Cancel, required hints and Choose another package Summary

**Cancel button beside Install Part (reusing reject(), greyed out while installing or committing), "Required - ..." hints matching the atomic strip, and a "Choose another package..." header button with tooltip, with Help and tests updated.**

## Performance

- **Duration:** about 25 min
- **Completed:** 2026-11-02
- **Tasks:** 3 (all TDD: RED test commit, then GREEN feature commit)
- **Files modified:** 4

## Accomplishments

- G-12-6: `_cancel_btn` sits right after Install Part in the bottom row, tooltip "Close without installing. Nothing is written.", clicked connected to `reject()`. `_sync_cancel_button()` greys it out while `is_installing()` or `is_committing()`, called from `_set_install_ui` and `_set_git_worker`. During a rebuild it enters Finishing exactly like the window X. It is not a default or auto-default button.
- G-12-7: `_BLANK_FIELD_HINT` is gone. `_REQUIRED_HINTS` gives "Required - enter a Datasheet link", "Required - type a Description" and "Required - enter the Manufacturer". Help's Fields section says the three are required and that Install Part stays blocked while one is empty.
- G-12-8: public `CHANGE_PACKAGE_TEXT = "Choose another package..."` and `_CHANGE_PACKAGE_TIP` on the header button. Help's Start section gains a paragraph about it and the Finishing paragraph names it through the constant.

## Task Commits

1. **Task 1: Cancel beside Install Part (G-12-6)** - `fe47328` (test, RED), `0868291` (feat, GREEN)
2. **Task 2: Required-field hints (G-12-7)** - `7edd5a0` (test, RED), `d8e61c3` (feat, GREEN)
3. **Task 3: Choose another package (G-12-8)** - `8c0166c` (test, RED), `9a46916` (feat, GREEN)

**Plan metadata:** committed with this SUMMARY (docs: complete plan).

## Files Created/Modified

- `kicad_lib_manager/widgets/import_dialog.py` - Cancel button and sync, `_REQUIRED_HINTS`, `CHANGE_PACKAGE_TEXT`, `_CHANGE_PACKAGE_TIP`
- `kicad_lib_manager/widgets/help_dialog.py` - Cancel, required-field and Choose another package sentences
- `tests/test_import_dialog.py` - five new tests plus updated `test_install_progress_and_lock`, `test_commit_close_button_disabled_while_git_runs`, `test_fields_clear_and_restore`
- `tests/test_help_dialog.py` - `test_help_names_the_cancel_button`, `test_help_names_choose_another_package`, extended `test_help_import_page_explains_fields_and_the_install_gate`

## TDD Gate Compliance

Each task has a `test(12-09)` RED commit before its `feat(12-09)` GREEN commit. RED evidence: Task 1 failed with `AttributeError: 'ImportDialog' object has no attribute '_cancel_btn'` in `test_cancel_button_closes_without_installing`; Task 2 failed on the old placeholder/Help text in `test_required_field_hints_match_the_atomic_strip`, `test_fields_clear_and_restore` and `test_help_import_page_explains_fields_and_the_install_gate`; Task 3 failed with `AttributeError` for the missing `CHANGE_PACKAGE_TEXT`. Semantic assessment: each failure was the planned missing behaviour, not a collection or fixture fault. No REFACTOR commits were needed.

## Decisions Made

- Cancel reuses `reject()` so no new close logic exists; the existing `done()` refusal and Finishing path cover installs, commits and rebuilds.
- Added `test_cancel_button_enabled_again_after_failed_install` as its own test (the plan listed it as a second case of the disabled test), so each test checks one concept.
- Extended the existing Help fields test instead of adding a separate one, as the plan's behavior block describes.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The first Bash commands that combined several git calls were refused by the worktree guard; they were split into separate commands.

## Verification

- Task 1 targeted run: 12 passed. Task 2: 4 passed. Task 3: 14 passed.
- Plan-level run `tests/test_import_dialog.py tests/test_help_dialog.py tests/test_generated_text.py`: 285 passed in 154 s.
- Acceptance greps: `_cancel_btn.clicked.connect(self.reject)` found once; `_sync_cancel_button()` appears 2 times; `written blank` 0 in both files; `_REQUIRED_HINTS[` found; `QPushButton("Change` 0; `<b>Change...</b>` 0; `+ CHANGE_PACKAGE_TEXT` 2.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for plans 12-10 and 12-11 (12-11 edits the last sentence of the Finishing paragraph and runs the full-suite gap-closure gate). UAT tests 6, 7 and 8 should be re-checked by the owner in the running window.

---
*Phase: 12-import-flow-fixes-and-case-sensitive-re-test*
*Completed: 2026-11-02*

## Self-Check: PASSED

- Modified files exist: import_dialog.py, help_dialog.py, test_import_dialog.py, test_help_dialog.py (FOUND).
- Commits fe47328, 0868291, 7edd5a0, d8e61c3, 8c0166c, 9a46916 are ancestors of HEAD (FOUND).
