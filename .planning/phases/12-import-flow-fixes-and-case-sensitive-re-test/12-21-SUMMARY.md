---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 21
subsystem: ui
tags: [pyside6, user-guide, help-dialog, qtreewidget, event-filter, item-delegate]
gap_ids: [G-12-27]

requires:
  - phase: 12-19
    provides: remembered guide place, show_remembered, raise-only rule for a visible guide
  - phase: 12-20
    provides: the shared, parentless User Guide window
provides:
  - "Guide reopens on the chosen section with its heading at the top (reused, fresh, narrowed by fit_window)"
  - "Main-window Help or F1 on a guide still on an asked topic goes back to the owner's place"
  - "A held left click on the guide menu selects and saves the pressed row; folding waits for the release"
  - "Selected menu row drawn in the accent colour by a row painter, no stylesheet on the menu"
affects: [12-UAT re-check of test 27]

actuals:
  tokens: 31000
  tasks: 3
  commits: 6

plan_head_before: 98a2099269868708debbf8a5d32a135a2eaed866
plan_head_after: 03502524fe9ee8aa6886b1f322ffd1e1736197b8

tech-stack:
  added: []
  patterns:
    - "HelpDialog._show_current_heading: one helper that scrolls to the current entry's heading, never selects or saves"
    - "Left-button hold on a menu viewport tracked by an event filter, ended by release, hide, key press or a live QGuiApplication.mouseButtons() check"
    - "Selected-row look through a QStyledItemDelegate with theme tokens, never a stylesheet"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/help_dialog.py
    - kicad_lib_manager/main_window.py
    - tests/test_help_dialog.py
    - tests/test_main_window.py
    - CLAUDE.md

key-decisions:
  - "show_guide goes back to the owner's place when the guide is hidden OR still shows a topic a caller asked for; a visible guide on the owner's own place is only raised (narrows plan 12-19's raise-only rule)"
  - "Held-click fix keeps Qt's normal drag behaviour and only delays the fold until the left release; the hold cannot outlive the button"
  - "Selected row painted by an item delegate, not a stylesheet, so the menu's arrows and indentation stay with the style"

patterns-established:
  - "Tests that press a menu row first let the fold queued by opening the topic run (qtbot.wait(50)), because QTest mouse events process events and fire a stale zero timer"

requirements-completed: [UI-01]

coverage:
  - id: D1
    description: "A reused guide reopened with Close or Escape (also after the import window's Help) brings the chosen section's heading back, and show_topic on the shown topic does too."
    requirement: UI-01
    verification:
      - kind: integration
        ref: "tests/test_main_window.py#test_main_window_help_brings_the_section_heading_back"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_reopened_guide_brings_the_section_heading_back"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_show_topic_on_the_shown_topic_brings_its_heading_back"
        status: pass
    human_judgment: false
  - id: D6
    description: "Main-window Help on a guide still open on a topic the import window asked for goes back to the owner's section with that row selected and its heading at the top; a visible guide on the owner's own place is only raised and its page does not move."
    requirement: UI-01
    verification:
      - kind: integration
        ref: "tests/test_main_window.py#test_main_window_help_brings_the_section_heading_back"
        status: pass
      - kind: integration
        ref: "tests/test_main_window.py#test_main_window_help_on_a_visible_guide_only_raises"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_asked_topic_lasts_until_the_owner_moves"
        status: pass
    human_judgment: false
  - id: D2
    description: "A fresh guide narrowed by fit_window still shows the saved heading at the top."
    requirement: UI-01
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_fresh_guide_shows_the_saved_heading_after_fit_window_narrows"
        status: pass
    human_judgment: false
  - id: D3
    description: "A held left click selects and saves the pressed row and the menu folds after the release; only the left button holds the menu, and a lost release (also with Qt still reporting the button down), a key press on the menu or a closed guide never leaves it waiting."
    requirement: UI-01
    verification:
      - kind: automated_ui
        ref: "tests/test_help_dialog.py#test_held_press_on_a_page_row_selects_that_row"
        status: pass
      - kind: automated_ui
        ref: "tests/test_help_dialog.py#test_only_a_left_press_holds_the_menu"
        status: pass
      - kind: automated_ui
        ref: "tests/test_help_dialog.py#test_keyboard_move_after_a_lost_release_still_folds"
        status: pass
    human_judgment: false
  - id: D4
    description: "The selected menu row uses the accent fill and white text from theme tokens, the menu keeps its expand arrows and indentation (no stylesheet on it), and the Help F1 row and CLAUDE.md say where the guide reopens."
    requirement: UI-01
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_menu_selected_row_stands_out"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_menu_keeps_its_arrows_and_indentation"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_says_the_guide_reopens_where_you_left_it"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_css_uses_theme_tokens_only"
        status: pass
    human_judgment: false
  - id: D5
    description: "The reopened place and the selected-row look are right on the real desktop at 100% and 200% with real mouse input (UAT test 27 re-check)."
    requirement: UI-01
    verification: []
    human_judgment: true
    rationale: "Offscreen Qt has no real mouse, no windows11 style and no display scaling. Of the page-row half of the owner report (row 4.4 selected on reopen) only the guide-left-open path is reproduced (D6). The step-1 order from the UAT note (Close, then F1) has no reproduced mechanism and no RED test, so the owner's run is its only gate. The trace fallback is blocking: if the row 4.4 still shows where Conflicts is expected, G-12-27 stays failed."

duration: 55min
completed: 2026-11-11
status: complete
---

# Phase 12 Plan 21: Guide reopens on the chosen section Summary

**The User Guide now reopens with the chosen section's heading at the top (reused, fresh or narrowed), main-window Help brings the owner's place back even over a guide the import window left on Importing Parts, and a held left click on the menu selects the pressed row because folding waits for the release.**

## Performance

- **Duration:** about 55 min (plus a 17 min full-suite run)
- **Tasks:** 3 (Task 1 tracer, Tasks 2 and 3 TDD)
- **Files modified:** 5
- **Commits:** 6 (three RED test commits, three GREEN commits)

## Status of the gap

**G-12-27 and UAT test 27 stay failed, awaiting the owner's re-check.** Nothing here (12-UAT.md, STATE.md, ROADMAP, this summary) marks them resolved from automated results. The owner's re-check is the Task 3 human check (steps 1 to 6, plus 5b and 5c, at 100% and 200%).

**Blocking fallback.** If at a step that expects 4.4.7 Conflicts (2, 3, 5, 5b, 6) the guide shows the row "4.4 Importing Parts" selected or the page top, the gap stays failed and D5 is not passed. The owner then closes the app, runs `.\env\Scripts\python.exe .claude\debug\guide_trace.py` from the repo root in place of `kicad_lib_manager.py`, repeats steps 1, 2 and 6 with a screenshot at each check, and returns `.claude\debug\guide_trace.log` with the screenshots for a new debug round before any further fix. The tracer is kept untracked at `C:\Git_Repo_Clones\Kicad_Libraries-importer\.claude\debug\guide_trace.py` (present, git-ignored; `git ls-files -- '*guide_trace*'` prints nothing). The step-1 order (Close, then F1) has no reproduced mechanism and no RED test, so this check is its only gate. If the owner prefers the guide to stay on Importing Parts at step 5b, that is a behaviour change, not a failure of the fix.

## Accomplishments

- `HelpDialog._show_current_heading` scrolls a section to its anchor and a page to its title. It is called from `show_topic` (also when the item is already current) and from every non-spontaneous `showEvent`, at once and on the next event-loop turn, after `fit_window`.
- Asked-topic flag: `show_topic` sets it, `show_remembered` and the owner's own saved move clear it, `shows_asked_topic()` reads it. `MainWindow.show_guide` sends a hidden guide, or a visible one still on an asked topic, back through `show_remembered`; a visible guide on the owner's own place is only raised.
- Held left click: an event filter on the menu viewport and the menu tracks a left press; `_on_topic_selected` defers the fold until the left release, only while Qt still reports the left button down. The hold ends on the left release, on hide or close, on a key press on the menu, and whenever a move arrives with the button reported up.
- `_MenuSelectionDelegate` paints the selected row with the accent fill and white text from theme tokens. No stylesheet is set anywhere in `help_dialog.py`.
- The Keyboard Shortcuts F1 row and the CLAUDE.md User Guide bullet say the main window brings the guide back to the last chosen place, scrolled to that heading, also while still open, and that a guide already open there is only brought to the front.

## Task Commits

1. **Task 1 (tracer): main-window Help brings back the chosen section and heading**
   - RED `ae9fc15` test(12-21)
   - GREEN `14a9f7f` feat(12-21)
2. **Task 2: a held left click selects the pressed row**
   - RED `afbf3be` test(12-21)
   - GREEN `da9e7f2` fix(12-21)
3. **Task 3: selected row look, Help wording, CLAUDE.md**
   - RED `c60fe99` test(12-21)
   - GREEN `0350252` feat(12-21)

**Plan metadata:** the SUMMARY commit that follows (docs).

Tracer feedback gate (interactive, `end-of-phase`, automated-only verify): the Task 1 verify was re-run after the GREEN commit (131 passed) and the slice was verified end to end before Tasks 2 and 3 expanded.

## RED evidence (semantic assessment)

**Task 1.** Nine of ten new or changed cases failed for the planned reasons; one passed as predicted.
- `test_asked_topic_lasts_until_the_owner_moves`, updated `test_main_window_help_on_a_visible_guide_only_raises`: `AttributeError: 'HelpDialog' object has no attribute 'shows_asked_topic'` (the planned "method does not exist yet").
- `test_reopened_guide_brings_the_section_heading_back[close]` and `[escape]`: `waitUntil` timed out on the final heading-near-top check (the planned heading failure). Their `_selected_keys == ["importing#conflicts"]` check is a **pin**, predicted to pass, not counted as RED.
- `test_show_topic_on_the_shown_topic_brings_its_heading_back` and `test_fresh_guide_shows_the_saved_heading_after_fit_window_narrows`: `waitUntil` timeout on the heading-near-top check (planned).
- `test_main_window_help_brings_the_section_heading_back[close]` and `[escape]`: timeout on the heading check (planned).
- `test_main_window_help_brings_the_section_heading_back[import help, guide left open]`: `assert 'importing' == 'importing#conflicts'` on the key check. This is the owner's exact picture (row 4.4 selected, page top, saved key importing#conflicts) and the only real RED for the page-row half. Its selection check follows the key check and is RED by the same cause.
- `[import help between]` **passed today** (the page change re-renders). It is a regression pin, not RED.

**Task 2.** `test_held_press_on_a_page_row_selects_that_row` (4 cases) failed on `assert _find_item(dialog, open_page).isExpanded()`: the open page folded under the held button (planned). `test_only_a_left_press_holds_the_menu` failed with `AttributeError: ... '_menu_held'` (planned). `test_keyboard_move_after_a_lost_release_still_folds` passed in all three cases on the old code, as the plan predicts, and guards the new hold.

**Task 3.** `test_menu_selected_row_stands_out` failed on the missing `_MenuSelectionDelegate` (planned); `test_help_says_the_guide_reopens_where_you_left_it` failed on the missing sentence (planned); `test_menu_keeps_its_arrows_and_indentation` passed on the old code and guards the change.

## Files Created/Modified

- `kicad_lib_manager/widgets/help_dialog.py` - heading helper, asked-topic flag, left-button hold filter, hideEvent, selected-row delegate, F1 sentence
- `kicad_lib_manager/main_window.py` - `show_guide` condition and docstring only
- `tests/test_help_dialog.py` - `_heading_near_top` helper and the new guide tests
- `tests/test_main_window.py` - end-to-end reopen test (four cases) and the updated visible-guide test
- `CLAUDE.md` - User Guide bullet wording

## Decisions Made

- Plan 12-19's raise-only rule changed for asked topics: a visible guide is now only raised when it shows the owner's own place. A guide still on a topic a caller asked for (the import window's Importing Parts) goes back to the owner's place. This implements owner decision G-12-23.
- Plan 12-19's `test_main_window_help_on_a_visible_guide_only_raises` was updated on purpose, keeping its name: its old setup (an import-window topic on a visible guide) is now the asked-topic case. The new body checks the owner's own place on a visible guide (page not moved, not an asked topic).
- The flag never saves and never reads the saved place; the one `save_help_topic(` call stays in the owner-move save, and `main_window.py` has no `load_help_topic`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in test] Visible-guide test scrolled to the maximum, which the browser later clamps**
- **Found during:** Task 1 (GREEN run)
- **Issue:** the updated `test_main_window_help_on_a_visible_guide_only_raises` set the scroll bar to its maximum (6165). Before Help was triggered and with no show event, the browser re-estimated the page height and the maximum shrank to 5906, clamping the value. The page had not been pulled away; the assertion measured layout drift.
- **Fix:** scroll half way (`maximum() // 2`) and assert it is above 0. Verified with a debug test that no `showEvent` fired and the value only changed with the maximum.
- **Files modified:** tests/test_main_window.py
- **Committed in:** 14a9f7f

**2. [Rule 1 - Bug in test] A stale zero-timer fold fired during the held press**
- **Found during:** Task 2 (GREEN run)
- **Issue:** `QTest.mousePress` processes events, and the fold queued when the dialog opened its topic was still pending, so it ran with the page already switched and folded the open page. This is a test artefact, not product behaviour (a person's press never has such a timer pending).
- **Fix:** `_shown_dialog` waits 50 ms after exposure so the fold queued by opening the topic runs first. Confirmed by tracing: no fold was scheduled by the press itself.
- **Files modified:** tests/test_help_dialog.py
- **Committed in:** da9e7f2

**Total deviations:** 2 auto-fixed (both test-side). **Impact:** none on the product code or scope.

## Prohibition checks (actual outcomes)

- No colour literal or px font size in `help_dialog.py`: `test_help_css_uses_theme_tokens_only` passes.
- No stylesheet: `grep -v '^[[:space:]]*#' help_dialog.py | grep -c "setStyleSheet"` prints 0; `test_menu_keeps_its_arrows_and_indentation` passes.
- Single save: `grep -c "save_help_topic("` (non-comment) prints 1; `load_help_topic` count in `main_window.py` is 0; `test_an_explicit_topic_wins_and_is_not_remembered` passes.
- Tracer not in the repo: `git ls-files -- '*guide_trace*'` prints nothing; `git check-ignore -q .claude/debug/guide_trace.py` exits 0; the file exists in the owner's checkout.

## Verification

- Task 1 and Task 2 commands: tests/test_help_dialog.py and tests/test_main_window.py, 131 passed (Task 1); tests/test_help_dialog.py, 61 passed (Task 2).
- Plan-level six-file run (`test_main_window`, `test_main_window_import`, `test_import_dialog`, `test_help_dialog`, `test_plain_names`, `test_importer_layering`, `-m "not wurth"`): **472 passed, 4 warnings, 2 min 42 s**.
- Full suite (`-m "not wurth"`): **3290 passed, 33 skipped, 3 deselected, 1 failed, 16 min 38 s**.
  - Skips are the expected ones: Custom submodule not checked out, symlinks not permitted on this machine, and licence-restricted vendor samples not present in `downloaded_examples/`.
  - The one failure is `tests/test_official_footprint.py::test_the_destination_choice_and_picker_fit_the_left_pane`, a file this plan did not touch and unrelated to the guide. It passed when run alone and in a full run of its own file (25 passed), so it is an order- or timing-dependent flake in the full run. Not fixed here (out of scope); worth a look by the owner.

## Issues Encountered

- The plan-ledger file for the commit count could not be written from inside the worktree (the harness blocks writes to the shared git directory). The base hash `98a2099` was known from the dispatch, and `commits: 6` was measured with `git rev-list --count 98a2099..HEAD` at SUMMARY time.

## Known Stubs

None.

## Threat Flags

None. The new event filter never consumes an event; the tracer is untracked.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Owner re-check of UAT test 27 is the open gate (see Status of the gap).
- D5 is a human-judgment deliverable and stays unproven until that re-check.

## Self-Check: PASSED

---
*Phase: 12-import-flow-fixes-and-case-sensitive-re-test*
*Completed: 2026-11-11*
