---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 12
subsystem: ui
tags: [pyside6, qtoolbar, qaction, help, import-dialog, user-guide]

requires:
  - phase: 12-import-flow-fixes-and-case-sensitive-re-test
    provides: the import window, its Finishing state and the User Guide pages (plans 12-01 to 12-11)
provides:
  - a toolbar at the top of the import window, shared by the start, edit and result pages, with a Help action (F1)
  - HelpDialog(topic=...) and HelpDialog.show_topic(key)
  - Help pages that name the toolbar Help and F1 in plain words
affects: [phase 12 UAT re-check of test 9(d), help_dialog, import_dialog]

actuals:
  tokens: 5300
  tasks: 3
  commits: 6
plan_head_before: 0508e25afd1d286e6a0caa59577480ae881b13d4
plan_head_after: a3feb88fb57be6c6a5f3612a23321f15f57323ed

tech-stack:
  added: []
  patterns:
    - "QToolBar in the dialog's outer layout above the page stack, so one toolbar serves every page and stays live while the stack is disabled"
    - "Non-modal child window parented to a window-modal dialog is not blocked by it; one instance is kept and reused, closed by _shutdown"
    - "Function-level import to avoid the help_dialog <-> import_dialog circular import"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_import_dialog.py
    - tests/test_help_dialog.py

key-decisions:
  - "Help opens with show() (never exec()) as a child of the import window, so both windows take input and a close that waits in Finishing still runs"
  - "F1 is the Help action's own shortcut; no separate QShortcut, because two bindings of one key in a window are ambiguous"
  - "_shutdown swaps self._help_dialog to None before closing it, so every exit path closes the guide and a second _shutdown finds nothing"

patterns-established:
  - "Click-through-the-window-system tests: QTest.mouseClick on windowHandle() proves a window is not blocked by a modal one"

requirements-completed: [UI-01]

coverage:
  - id: D1
    description: "The import window has a toolbar with Help (F1) above the page stack, visible on the start, edit and result pages; it opens the User Guide on Importing Parts and the import window stays open"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_toolbar_help_opens_importing_page"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_f1_opens_help_from_the_start_page"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_help_reachable_on_edit_and_result_pages"
        status: pass
    human_judgment: false
  - id: D2
    description: "Help works while the preview rebuilds, in Finishing, while installing and while committing, writes nothing, and the guide closes with the import window"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_help_works_while_installing"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_help_works_while_committing"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_help_works_while_finishing_and_closes_with_the_dialog"
        status: pass
    human_judgment: false
  - id: D3
    description: "Both windows take real clicks while the guide is open (the guide is not modal)"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_import_window_takes_input_while_help_is_open"
        status: pass
    human_judgment: false
  - id: D4
    description: "HelpDialog opens on a given topic, falls back to Overview for none or an unknown key; the main window's Help is unchanged"
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_dialog_opens_on_a_given_topic"
        status: pass
    human_judgment: false
  - id: D5
    description: "Importing Parts (Start) and Keyboard Shortcuts say the import window's toolbar has Help and that F1 there opens Importing Parts"
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_names_the_toolbar_help"
        status: pass
    human_judgment: false
  - id: D6
    description: "The toolbar looks right (icon, text beside it, spacing) in the real window"
    verification: []
    human_judgment: true
    rationale: "Visual fit of a standard platform icon next to the text is not asserted by any test; the owner re-checks UAT test 9(d)"

duration: about 35 min (suite 14 min 39 s)
completed: 2026-11-03
status: complete
---

# Phase 12 Plan 12: Toolbar Help in the import window Summary

**A Help action (F1) on a new toolbar at the top of the import window opens the User Guide on Importing Parts from every page and in every state, as a non-modal window that closes with the import window.**

## Performance

- **Duration:** about 35 min (suite 14 min 39 s)
- **Tasks:** 3 (all TDD, 6 commits)
- **Files modified:** 4 (2 source, 2 test)

## Accomplishments

- `ImportDialog._build_toolbar` puts a `QToolBar` first in the dialog's outer layout, above the page stack, so the start, edit and result pages share it. Its only action is Help (standard help icon, text beside it, tooltip, F1). No stylesheet, no colour literal.
- `_on_help` creates `HelpDialog(topic="importing", parent=self)` once, shows it with `show()` (never `exec()`), and reuses it on later Help or F1 presses (`show_topic` moves it back to Importing Parts). Because it is a child of the window-modal import dialog, both windows take input.
- `_shutdown` closes the guide, so Cancel, Escape, X, the result page's Close and a close that waited in Finishing all take it along.
- `HelpDialog(parent=None, *, topic=None)` and `HelpDialog.show_topic(key) -> bool`; the main window's `HelpDialog(parent=self).exec()` is unchanged and still opens on Overview.
- The Importing Parts (Start) page and the Keyboard Shortcuts F1 row name the toolbar Help and F1 in plain words, inserted through the `HELP_ACTION_TEXT` constant.

## Task Commits

1. **Task 1: Toolbar Help opens Importing Parts (tracer)**
   - RED `ff9587b` (test): `test_help_dialog_opens_on_a_given_topic` (TypeError, unknown `topic`), `test_toolbar_help_opens_importing_page` and `test_f1_opens_help_from_the_start_page` (AttributeError on the missing toolbar / `_help_dialog`)
   - GREEN `fdaa572` (feat)
2. **Task 2: Every page, every state, lifecycle**
   - RED `3f10f64` (test): five new tests; the two Task 1 tests that matched the filter still passed, the five new ones failed on `assert not help_window.isVisible()` (the guide outlived the import window)
   - GREEN `7fbe05a` (feat): `_shutdown` closes the guide
3. **Task 3: Help text**
   - RED `959d58f` (test): `test_help_names_the_toolbar_help` failed on the missing word "Help" in the Start section
   - GREEN `a3feb88` (feat)

**Plan metadata:** the docs commit that adds this file.

## TDD Gate Compliance

All three tasks have a `test(12-12)` commit before the `feat(12-12)` commit. No REFACTOR commit was needed. RED evidence was read by hand from pytest output (no `tdd-red-evidence` classifier record was produced); each RED failure was on the planned behaviour (missing keyword, missing attribute, or the guide staying visible), not on a collection or import error.

## Modal experiment (Task 2)

With `self._help_dialog.setModal(True)` added before `show()` (local only, never committed), `test_import_window_takes_input_while_help_is_open` failed on its `assert not help_window.isModal()` line. To prove the real-click part has teeth on its own, the three modality asserts were also removed temporarily: the test then passed the Help-window click and failed at the Cancel click (`waitUntil(not dialog.isVisible())` timed out after 30 s, the import window stayed visible because the window system dropped the click). Both edits were reverted (`git checkout` of the test file, source edit undone). Check: `grep -v '^[[:space:]]*#' kicad_lib_manager/widgets/import_dialog.py | grep -c "setModal"` prints 0.

## Verification

- Task 1 verify: 6 passed. Task 2 verify: 14 passed. Plan-level run (`test_help_dialog.py`, `test_import_dialog.py`, `test_plain_names.py`, `test_main_window_import.py`): 312 passed in 2 min 35 s.
- Gap-closure gate `-m "not wurth"`: 3179 passed, 33 skipped, 3 deselected in 879.30 s (14 min 39 s). Every skip is one the README lists: Custom and Wurth submodules not checked out in the worktree, licence-restricted vendor samples absent, two symlink skips, the two UAT-dir skips. No other skip.
- Acceptance greps: one `QToolBar()`, `_build_toolbar(outer)` (line 506) before `outer.addWidget(self._stack)` (line 507), one indented `from .help_dialog import HelpDialog`, main window call unchanged, `+ HELP_ACTION_TEXT` count 2.

## Decisions Made

- Non-modal `show()` for the guide, parented to the import dialog (plan choice, confirmed by the real-click test).
- Help has no enable or disable logic: it is outside `_stack`, `_left_scroll` and `_header_row`, which Finishing and the install lock disable.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Working copies in this repo are CRLF while the index is LF, so source edits were made with a small script that preserves CRLF (the `Edit` tool would not match multi-line strings). `git diff` shows only the intended lines.

## Known Stubs

None.

## Threat Flags

None. `_on_help` only creates or shows a read-only window (T-12-29, T-12-30 mitigations proven by the install, commit and Finishing tests).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- UAT test 9(d) can be re-checked: Help on the import window's toolbar and F1 are reachable from the start, edit and result pages.

## Self-Check: PASSED

Four modified files exist; six task commits (ff9587b, fdaa572, 3f10f64, 7fbe05a, 959d58f, a3feb88) are ancestors of HEAD; measured commits = 6.
