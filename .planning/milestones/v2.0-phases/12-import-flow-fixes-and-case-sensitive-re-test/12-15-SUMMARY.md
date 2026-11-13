---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 15
subsystem: ui
tags: [pyside6, qt-layout, import-dialog, help, gap-closure]

requires:
  - phase: 12-import-flow-fixes-and-case-sensitive-re-test
    provides: "plan 12-13 fit_window / _show_page sizing; plan 12-14 Help window"
provides:
  - "Cancel at the end of the Browse row on the import start page (_start_buttons)"
  - "_START_WIDTH and _start_size(): start window 640 wide and as tall as its content"
  - "_offer_slot: one constant-height slot for the Downloads line and the reading box"
  - "start window refit when the issue list shows or clears"
  - "Help sentence naming where Cancel sits on the start and editing steps"
affects: [12-16, 12-17, 12-18, 12-19, 12-20, verify-work]

actuals:
  tokens: 14000
  tasks: 3
  commits: 6
plan_head_before: 808df98ae5bfb9f44588de1e60e234987d1543ac
plan_head_after: eb24aec

tech-stack:
  added: []
  patterns:
    - "Start size computed from layout().totalHeightForWidth(640), never a fixed height"
    - "Nested layout caches reset inside-out (column, page, stack, dialog) before reading a size after show/hide"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_import_dialog.py
    - tests/test_help_dialog.py

key-decisions:
  - "Issue list minimum height lowered to 112 px (new _ISSUE_LIST_MIN_HEIGHT) so 20+ issues fit a Full HD 200% screen; maximum stays 160"
  - "_start_size() resets the nested layout caches itself, so callers get the current content height right after a block is shown or hidden"

requirements-completed: [UI-01]

duration: 40min
completed: 2026-11-04
status: complete
---

# Phase 12 Plan 15: Cancel on the Browse row, content-height start window Summary

**Import start page: Cancel moved onto the Browse row, window sized from its layout at width 640 (about 296 px tall offscreen instead of the fixed 440), one shared slot for the Downloads line and reading box, and a refit when the issue list shows or clears.**

## Performance

- **Duration:** about 40 min
- **Completed:** 2026-11-04T16:47Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- G-12-12 closed: Cancel is the last item of `_start_buttons` (Browse zip..., Browse folder..., stretch, Cancel); the separate bottom row and `_start_bottom` are gone. `clicked` is still connected to `reject` only, so D-06 and D-10 are untouched.
- `_START_SIZE` (640x440) replaced by `_START_WIDTH = 640` and `_start_size()`; the window is applied at construction, at first show, on re-entering the start page, and after the issue list shows or clears, always through `fit_window`.
- `_offer_slot` (QGridLayout, both widgets in cell 0,0, `retainSizeWhenHidden`) keeps the start window the same height before and after the Downloads lookup and while a package is read.
- Help (Importing Parts, Start) says Cancel sits next to Browse zip... and Browse folder..., and at the bottom right of the editing step, right of Install Part.

## Task Commits

1. **Task 1 (tracer): Cancel on the Browse row, content-height start window** - RED `ea3a754` (test), GREEN `c77698a` (feat)
2. **Task 2: shared offer slot, refit on issues** - RED `9c718da` (test), GREEN `1bf8c92` (feat)
3. **Task 3: Help names where Cancel sits** - RED `5d2fff5` (test), GREEN `eb24aec` (feat)

No refactor commits. **Plan metadata:** docs commit follows this file.

## TDD Gate Compliance

Each task has a `test(12-15)` commit before its `feat(12-15)` commit. RED evidence (semantic assessment): Task 1 tests failed with `AttributeError` for the planned interface (`_start_buttons`, `_start_size`), which is the contract the tests pin; Task 2 `_offer_slot` test failed on the missing slot, and the refit test failed on `dialog.size() == compact` after `_hide_issue_box` (452 px kept, expected 296); Task 3 failed on the assertion `'next to' in section`. No unexpected green. `gsd_run check tdd-red-evidence` was not run: pytest's plain console output is not one of its supported report formats and the plan is `type: execute`.

## Files Created/Modified

- `kicad_lib_manager/widgets/import_dialog.py` - `_START_WIDTH`, `_start_size()`, `_start_buttons` with Cancel, `_offer_slot`, `_ISSUE_LIST_MIN_HEIGHT`, refit in `_show_start_issues` / `_hide_issue_box`, start size in `__init__`, `_show_page`, `showEvent`
- `kicad_lib_manager/widgets/help_dialog.py` - Start section Cancel paragraph
- `tests/test_import_dialog.py` - new: `test_start_page_cancel_shares_the_browse_row`, `test_start_page_is_as_tall_as_its_content` (100% and 200%), `test_start_page_keeps_its_height_when_the_offer_arrives`, `test_start_issues_refit_the_window`; updated: cancel, opens-small and grows-and-shrinks tests
- `tests/test_help_dialog.py` - `test_help_names_the_start_page_cancel` extended

## Decisions Made

- Lower bound for the issue list set separately from its cap (see deviation 1).
- `_start_size()` owns the cache reset (see deviation 2) rather than each caller.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Issue list minimum kept the 20-issue state off a Full HD 200% screen**
- **Found during:** Task 2 (`test_start_issues_refit_the_window`)
- **Issue:** `setMinimumHeight(min(160, wanted))` made the layout minimum 464 px, so with a real 32 px title frame the window (496 px) was taller than the 492 px free area; `fit_window` never goes below the layout minimum, so the refit alone could not satisfy the plan's "stays inside a Full HD 200% screen".
- **Fix:** New `_ISSUE_LIST_MIN_HEIGHT = 112` used for the minimum; the maximum stays 160 (existing test pins it). At 100% the list still shows at 160 because the window is sized from the hint.
- **Files modified:** `kicad_lib_manager/widgets/import_dialog.py`
- **Verification:** `test_start_issues_refit_the_window` passes (frame inside DESKTOP_200).
- **Committed in:** `1bf8c92`

**2. [Rule 3 - Blocking] Stale nested layout caches after hiding a block**
- **Found during:** Task 2
- **Issue:** after `_issue_box.hide()` the dialog's `totalHeightForWidth` and `minimumSizeHint` kept the issue-state value (522 / 446) even after processing events, so the cleared state was not refit (probe in the scratchpad; show worked, hide did not).
- **Fix:** `_start_size()` invalidates and activates the column, page, stack and dialog layouts inside-out before measuring.
- **Files modified:** `kicad_lib_manager/widgets/import_dialog.py`
- **Verification:** the hide half of `test_start_issues_refit_the_window` (back to the compact size) and the Task 1 height tests pass.
- **Committed in:** `1bf8c92`

**3. [Test adjustment] Issue-refit test compares with the screen-bounded size**
- The plan wrote `dialog.size() == dialog._start_size()` for the many-issues state. At 200% the wanted height (about 506) exceeds the screen bound, so the test compares against `_fit_size(...)` of the same inputs instead; the contained-frame claim is kept.

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking), 1 test adjustment
**Impact on plan:** both fixes were needed for the plan's own claims (refit works, 200% screen holds); no scope creep.

## Issues Encountered

- The Bash harness refused compound git commands in the worktree, so the per-plan commit ledger file under the git dir was not written; the base (`808df98`) and the measured commit count (6) come from `git log 808df98..HEAD`.
- Plan-level check (`tests/test_import_dialog.py tests/test_help_dialog.py tests/test_plain_names.py tests/test_main_window_import.py`): **348 passed**, 4 pre-existing deprecation warnings, 199.5 s (3 min 19 s). The full suite was not run (phase-level gate).
- The `<human-check>` of Task 3 (100% and 200% Windows scale, run the real app, `git -C Custom status`) was not run by the executor; it needs a human at the real display.

## Known Stubs

None.

## Threat Flags

None. T-12-38 mitigated: every start size goes through `fit_window`; covered by `test_start_issues_refit_the_window` and `test_start_page_is_as_tall_as_its_content`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plans 12-16 onward touch other files. Remaining for this gap: the human check at 100% and 200% scale.

## Self-Check: PASSED

- Files modified exist: import_dialog.py, help_dialog.py, test_import_dialog.py, test_help_dialog.py (all in the six commits).
- Commits `ea3a754 c77698a 9c718da 1bf8c92 5d2fff5 eb24aec` are on the branch.
- Acceptance greps: `^_START_WIDTH = 640` one line, `def _start_size` one line, no `_START_SIZE` in code, `_start_cancel_btn.clicked.connect(self.reject)` one line, `setRetainSizeWhenHidden(True)` two lines, `self._offer_slot` present, `next to <b>Browse zip...</b>` one line.

---
*Phase: 12-import-flow-fixes-and-case-sensitive-re-test*
*Completed: 2026-11-04*
