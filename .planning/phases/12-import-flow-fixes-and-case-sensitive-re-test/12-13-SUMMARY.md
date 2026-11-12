---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 13
subsystem: ui
tags: [pyside6, qt, import-dialog, window-sizing, high-dpi, help]

requires:
  - phase: 12-import-flow-fixes-and-case-sensitive-re-test
    provides: "Plan 12-09 edit-page Cancel (G-12-6), plan 12-12 Help toolbar action (G-12-9), D-06 and D-10 close rules"
provides:
  - "Cancel on the import start page (_start_cancel_btn), wired to reject()"
  - "screen_area seam, fit_window (public, shared with the User Guide window in 12-14), _fit_size, _place_inside"
  - "Start page opens small (640x440); the window grows to the edit size (1100x720, screen-bounded) and shrinks back"
  - "Autouse conftest default: the import window sizes itself for a Full HD 100% desktop in tests"
affects: [12-14, user-guide-window, phase-12-verification]

actuals:
  tokens: 28000
  tasks: 3
  commits: 6
plan_head_before: 6af55c8a08de6fede919d84441cac1a4de080425
plan_head_after: 609adddd6ea41bc57e2655d0558fec183deb38d9
commits: 6

tech-stack:
  added: []
  patterns:
    - "Module-level screen_area(widget) seam so tests model 100% and 200% display scale in logical pixels"
    - "Every stack page switch goes through _show_page, which syncs size policies and fits the window"
    - "Hidden pages get the Ignored size policy so they drop out of a QStackedWidget minimum"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/conftest.py
    - tests/test_import_dialog.py
    - tests/test_help_dialog.py
    - tests/test_generated_text.py
    - tests/test_official_footprint.py

key-decisions:
  - "The start Cancel only calls reject(), so done() keeps all close rules (waits in Finishing while any worker runs, refuses during install or commit); no new close logic"
  - "Fixed 900x600 minimum removed; the layout minimum applies, so a 200% screen is not pushed off"
  - "The conftest screen default patches nothing unless the import dialog module is already loaded, so Qt-free tests stay Qt-free"
  - "A hidden window is sized but never moved, so Qt still centres the dialog over the main window on first show"

patterns-established:
  - "fit_window(window, wanted): size a top-level window inside the free area of its screen, reused by plan 12-14"

requirements-completed: [REV-04, UI-01]

coverage:
  - id: D1
    description: "Start page has a Cancel at its bottom right that closes the window, writes nothing, and waits in Finishing while a package is read"
    requirement: REV-04
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_start_page_cancel_closes_without_writing"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_start_page_cancel_while_reading_waits_then_closes"
        status: pass
    human_judgment: false
  - id: D2
    description: "The whole import window lies inside the free area of its screen at 100% and 200% display scale, with Install Part and Cancel visible"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_window_fits_the_screen"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_fit_size_and_place_inside"
        status: pass
    human_judgment: true
    rationale: "Automated tests model 200% in logical pixels on the offscreen platform; the real Windows 200% display and taskbar need a human look (plan human-check)"
  - id: D3
    description: "Start page opens small, the window grows for the edit page, shrinks back, and the result page keeps its size and has Close"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_start_page_opens_small"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_window_grows_for_the_edit_page_and_shrinks_back"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_result_page_keeps_the_size_and_has_close"
        status: pass
    human_judgment: false
  - id: D4
    description: "Help Importing Parts, Start section, names the start page Cancel and the window size in plain words"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_names_the_start_page_cancel"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_says_the_window_fits_the_screen"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-11-04
status: complete
---

# Phase 12 Plan 13: Import window Cancel and screen fit Summary

**Start-page Cancel plus a screen-fitted import window that opens small (640x440), grows to the edit size bounded by the free screen area, and shrinks back, via a patchable `screen_area` seam shared with the User Guide window.**

## Performance

- **Duration:** about 45 min
- **Tasks:** 3
- **Files modified:** 7
- **Plan-level test run:** 490 passed, 1 skipped in 225.73 s (3 min 45 s) across the eleven files the plan names. The one skip is `tests/test_gate_reasons.py:241` (`downloaded_examples/ul_ATXK-H14-D-32-768KHZ-E50-T3.zip` not present in the worktree), an expected skip.

## Accomplishments

- G-12-10 closed in code: the start page has Cancel at the bottom right (tooltip "Close without importing. Nothing is written."), connected to `reject()` so the close rules of D-06 and D-10 apply unchanged.
- `screen_area`, `_fit_size`, `_place_inside` and the public `fit_window` keep the window, title bar and bottom row included, inside the screen's free area. `fit_window` sizes a hidden window without moving it, so first-show centring is kept.
- The start page opens at 640x440 with a minimum that no longer includes the edit page; the edit page grows to the size the user last gave it (initially 1100x720), bounded by the screen; Choose another package... shrinks back; the result page keeps its size and its Close button.
- The fixed 900x600 minimum is gone. An autouse conftest fixture models a Full HD 100% desktop so existing edit-page tests keep 1100x720; the six narrow-window tests were reordered to resize after the edit page shows and still test 900x600.
- Help (Importing Parts, Start) names the Cancel and explains the window size in plain words.

## Task Commits

1. **Task 1: Cancel on the start page** - RED `81b7065` (test), GREEN `3094453` (feat)
2. **Task 2: Fit the window to the free screen area** - RED `e3fd78b` (test), GREEN `9ab3107` (feat)
3. **Task 3: Small start page, grow and shrink** - RED `8074662` (test), GREEN `609addd` (feat)

No refactor commits were needed.

## TDD Gate Compliance

RED commits precede each GREEN commit. RED evidence, by task:

- Task 1: `test_start_page_cancel_*` failed because `_start_cancel_btn` did not exist (AttributeError), and `test_help_names_the_start_page_cancel` failed on the missing word "cancel" in the Start section. Semantic assessment: each failed on the planned assertion for the intended reason.
- Task 2: the six new tests failed because `import_dialog.screen_area`, `_fit_size` and `_place_inside` did not exist. In the RED commit `real_screen_area` was read with `getattr(..., None)` so the module still collected; GREEN changed it to the direct attribute read. Semantic assessment: failures were on missing seams, the planned reason.
- Task 3: `test_start_page_opens_small` (both areas) and `test_window_grows_for_the_edit_page_and_shrinks_back` failed on the size assertion (1200x760 where 640x440 was expected), and the Help test failed on the missing words "opens small". `test_result_page_keeps_the_size_and_has_close` already passed in RED, as it asserts behaviour the plan keeps.

## Files Created/Modified

- `kicad_lib_manager/widgets/import_dialog.py` - start Cancel, `screen_area`, `_fit_size`, `_place_inside`, `fit_window`, `_show_page`, `_sync_page_policies`, `_fit_to_screen`, `_START_SIZE`, `_EDIT_SIZE`, `_FRAME_ALLOWANCE`; first-show fit
- `kicad_lib_manager/widgets/help_dialog.py` - two Start-section sentences
- `tests/conftest.py` - autouse `_desktop_screen_area` fixture
- `tests/test_import_dialog.py` - new tests, helpers, four reordered narrow-window tests
- `tests/test_generated_text.py`, `tests/test_official_footprint.py` - one reordered narrow-window test each
- `tests/test_help_dialog.py` - two Help tests

## Decisions Made

See `key-decisions`. All followed the plan's "Choices made here" section; no new decisions.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The plan-level run exceeded the 180 s foreground window and ran as a background command; it finished green.

## User Setup Required

None - no external service configuration required.

## Pending human check

The plan's `<human-check>` (real Windows 100% and 200% display scale, taskbar) has not been done; an executor cannot change display scale. Steps are in 12-13-PLAN.md Task 3 `<verify>`. Deliverable D2 is marked `human_judgment: true` for this reason.

## Known Stubs

None.

## Next Phase Readiness

Plan 12-14 can import `fit_window` from `kicad_lib_manager.widgets.import_dialog` for the User Guide window. The full suite has not been run (phase-level gate).

## Self-Check: PASSED

- Files exist: import_dialog.py, help_dialog.py, conftest.py, test_import_dialog.py, test_help_dialog.py, test_generated_text.py, test_official_footprint.py
- Commits present: 81b7065, 3094453, e3fd78b, 9ab3107, 8074662, 609addd

---
*Phase: 12-import-flow-fixes-and-case-sensitive-re-test*
*Completed: 2026-11-04*
