---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 14
subsystem: ui
tags: [pyside6, qt, help-dialog, user-guide, toc, anchors, window-sizing]

requires:
  - phase: 12-import-flow-fixes-and-case-sensitive-re-test
    provides: "Plan 12-13 fit_window and screen_area seam; plan 12-12 import-window Help action"
provides:
  - "help_outline, HelpEntry, section_anchor, page_sections, render_page in help_dialog.py"
  - "A three-level numbered User Guide menu (groups, pages, sections) derived from the pages' own h3 headings"
  - "Section keys '<page>#<anchor>' accepted by HelpDialog(topic=...) and show_topic"
  - "The User Guide window bounded by the screen's free area on every show"
affects: [phase-12-verification, user-guide]

actuals:
  tokens: 6000
  tasks: 3
  commits: 5
plan_head_before: 1ae8caa1f81b049a31cc147e01b51bc0d0fb74b0
plan_head_after: eeb0f32bb036baa414e6c2f6d52c6e4a9ea6104e
commits: 5

tech-stack:
  added: []
  patterns:
    - "Numbers and anchors computed at render time from menu order; HELP_PAGES and TOC_STRUCTURE stay unnumbered sources"
    - "Empty named anchor placed before the heading text, never wrapped around it (a wrapper takes the link colour)"
    - "Menu row folding that follows a mouse selection waits for the event loop (QTimer.singleShot with a context object)"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_help_dialog.py
    - tests/test_import_dialog.py

key-decisions:
  - "Section key is '<page key>#<anchor>'; anchor is the heading in lower case with runs of other characters turned into one hyphen"
  - "The menu opens only the shown page's sections; groups stay open"
  - "Folding is deferred to the event loop when a page is chosen, but applied at once by show_topic, so a mouse click keeps its selection and programmatic opens stay synchronous"
  - "The guide fits the screen through showEvent calling fit_window(self, self.size()); no caller changed"

patterns-established:
  - "help_outline() is the single source of menu text, numbers and keys; the dialog, render_page and tests all read it"

requirements-completed: [UI-01]

coverage:
  - id: D1
    description: "The User Guide menu numbers every entry from its place (1, 4.4, 4.4.7) and lists each page's h3 sections under that page, derived from the page text"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_outline_numbers_follow_the_menu_order"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_every_page_heading_is_in_the_menu_under_its_page"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_numbers_are_rendered_not_typed"
        status: pass
    human_judgment: false
  - id: D2
    description: "Page and section headings show the same number as the menu; clicking a section scrolls to its heading, and clicking the selected section again scrolls back"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_page_headings_carry_the_menu_numbers"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_clicking_a_section_scrolls_to_its_heading"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_clicking_the_selected_section_again_scrolls_back"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_clicking_a_page_below_the_open_one_selects_it"
        status: pass
    human_judgment: false
  - id: D3
    description: "The menu opens the shown page's sections and folds the others; page, section and group keys still open from the main window, the import window Help and F1"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_menu_expands_the_shown_page_only"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_dialog_opens_on_a_given_topic"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_toolbar_help_opens_importing_page"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_import_window_takes_input_while_help_is_open"
        status: pass
    human_judgment: false
  - id: D4
    description: "Numbered headings keep their size and colour; theme tokens only, no colour literal, no px font size"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_rendered_headings_keep_their_look"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_headings_keep_their_sizes"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_css_uses_theme_tokens_only"
        status: pass
    human_judgment: false
  - id: D5
    description: "The User Guide window lies inside the free screen area at 100% and 200% display scale with its Close button visible, from the import window (Help, F1) and from the main window"
    requirement: UI-01
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_help_window_fits_the_screen"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_dialog_fits_the_screen"
        status: pass
    human_judgment: true
    rationale: "Tests model 200% in logical pixels on the offscreen platform; the real Windows 100% and 200% display, taskbar and sharp text need a human look (plan human-check)"

duration: 50min
completed: 2026-11-04
status: complete
---

# Phase 12 Plan 14: User Guide numbered menu with page sections Summary

**The User Guide menu now numbers groups, pages and sections from their order (1, 4.4, 4.4.7), lists each page's h3 headings under that page, scrolls to a section on click, follows the shown page, and fits the screen via plan 12-13's `fit_window`.**

## Performance

- **Duration:** about 50 min
- **Tasks:** 3
- **Files modified:** 3
- **Plan-level test run:** 343 passed in 178.89 s (2 min 59 s) across `tests/test_help_dialog.py`, `tests/test_import_dialog.py`, `tests/test_plain_names.py`, `tests/test_main_window_import.py`. No failures, no skips.

## Accomplishments

- G-12-11 closed in code. `help_outline()` walks `TOC_STRUCTURE` and adds each page's sections, read from the page's own bare `<h3>` headings, as a third menu level. There are 20 section entries, keyed `<page>#<anchor>`.
- `render_page(key)` puts the menu number before the page title and before each section heading (`4.4 Importing Parts`, `4.4.7 Conflicts`) and an empty named anchor before the heading text. `HELP_PAGES` and `TOC_STRUCTURE` stay unnumbered, so all existing `_section`-based claim tests are untouched.
- Clicking a section shows its page and scrolls to the heading with `scrollToAnchor`; clicking the selected section again scrolls back (`itemClicked` handler).
- The menu opens the shown page's sections and folds the other pages' sections; the three groups stay open. The import window's Help still opens Importing Parts, the main window's Help still opens Overview, and a section key opens that section.
- `HelpDialog.showEvent` calls `fit_window(self, self.size())`, so the guide is bounded by the free screen area and moved inside it however it is opened. Neither caller changed.
- The "Conflicts" section is numbered 4.4.7 from its place in the page, not the owner's example 4.4.8, as the plan states.

## Task Commits

1. **Task 1: Numbered menu with sections and scrolling (tracer)** - RED `8b6ca8b` (test), GREEN `c8add3e` (feat)
2. **Task 2: Menu follows the page, re-click scroll, guide fits the screen** - RED `1f83ce0` (test), GREEN `a9c0697` (feat)
3. **Task 3: Numbered headings keep the theme look** - `eeb0f32` (test; no production change needed)

**Plan metadata:** the SUMMARY commit that follows this file.

## Files Created/Modified

- `kicad_lib_manager/widgets/help_dialog.py` - `HelpEntry`, `section_anchor`, `page_sections`, `help_outline`, `render_page`; `HelpDialog` builds the menu from the outline, handles section items, folds other pages, handles re-clicks, and fits the screen in `showEvent`
- `tests/test_help_dialog.py` - numbering, menu, scrolling, expansion, fit and look tests; the heading-size test now also runs on the rendered page
- `tests/test_import_dialog.py` - the input test scrolls the menu to its row first; new `test_help_window_fits_the_screen` (Help and F1, 100% and 200%)

## Decisions Made

See `key-decisions`. The fold deferral is a deviation (below); everything else followed the plan's "Choices made here".

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Folding menu rows during a mouse press cleared the selection**
- **Found during:** Task 2 (`test_import_window_takes_input_while_help_is_open` failed after the fold was added)
- **Issue:** Choosing a page below the open one (for example Keyboard Shortcuts under the open Importing Parts) folded the open page inside the press handler. The rows moved under the mouse and the tree's current item became none, so the click selected nothing. Probed with a press and release in a bare HelpDialog; the plan's note about `scrollToItem` did not foresee this.
- **Fix:** `_on_topic_selected` now schedules the fold with `QTimer.singleShot(0, self, self._sync_expansion)`; `_sync_expansion` reads the shown page (`self._page_key`), so it is idempotent. `show_topic` also calls it directly, so programmatic opens (and the constructor's topic) are expanded synchronously, as the plan's tests expect. A regression test `test_clicking_a_page_below_the_open_one_selects_it` was added.
- **Files modified:** `kicad_lib_manager/widgets/help_dialog.py`, `tests/test_help_dialog.py`
- **Verification:** probe showed the selection kept across press, event loop and release; the Help and import-window Help tests pass.
- **Committed in:** `a9c0697`

**2. [Rule 1 - Bug, test] Heading-in-view check needed a one-pixel tolerance**
- **Found during:** Task 1 (`test_clicking_a_section_scrolls_to_its_heading`)
- **Issue:** The scroll value is a whole number of pixels, so a heading scrolled to the top reads a top of -0.01 to -0.5. The plan's "at least 0" rejected correct scrolls (probe showed all 20 sections land at the top).
- **Fix:** the helper accepts `-1 < top < viewport height`, with a comment.
- **Files modified:** `tests/test_help_dialog.py`
- **Committed in:** `c8add3e`

---

**Total deviations:** 2 auto-fixed (2 Rule 1)
**Impact on plan:** Both necessary for correctness. No scope creep and no caller change.

## Issues Encountered

None beyond the deviations.

## TDD Gate Compliance

RED commits precede each GREEN commit for Tasks 1 and 2. RED evidence:

- Task 1: all six new tests failed. `section_anchor`, `help_outline` and `render_page` did not exist (AttributeError on the planned seam), and the menu and click tests failed on the missing section rows. Semantic assessment: each failed for the planned reason.
- Task 2: `test_menu_expands_the_shown_page_only`, `test_clicking_the_selected_section_again_scrolls_back`, `test_help_dialog_fits_the_screen` and the two 200% `test_help_window_fits_the_screen` cases failed on the planned assertions (no folding, no re-scroll, a 864x624 frame in a 960x492 area). The extended `test_help_dialog_opens_on_a_given_topic` and the 100% fit cases already passed in RED because section keys work through `show_topic` after Task 1 and 860x620 fits a 1920x1032 area; they assert behaviour the plan keeps.
- Task 3: both checks (`test_rendered_headings_keep_their_look`, the extended size test) passed at once, as the plan allowed, so there was no RED and no feat commit. A probe confirmed the look test fails for a wrapper-style anchor (heading turned `#0078D4`).

No refactor commits were needed.

## User Setup Required

None - no external service configuration required.

## Pending human check

The plan's `<human-check>` (real Windows display at 100% and 200%: F1 guide fully on screen with Close visible, numbered menu, Importing Parts sections, Conflicts scroll, guide opened from the import window) has not been done; an executor cannot change display scale. Steps are in 12-14-PLAN.md Task 3 `<verify>`. Deliverable D5 is marked `human_judgment: true` for this reason.

## Known Stubs

None.

## Threat Flags

None. Anchors come only from static heading text through `section_anchor` (a-z, 0-9, single hyphens); `test_every_page_heading_is_in_the_menu_under_its_page` checks every anchor against `^[a-z0-9]+(-[a-z0-9]+)*$` (T-12-35). The fit test covers T-12-37.

## Next Phase Readiness

The full suite has not been run (phase-level gate after 12-13 and 12-14). The orchestrator owns STATE.md and ROADMAP.md.

## Self-Check: PASSED

- Files exist: help_dialog.py, test_help_dialog.py, test_import_dialog.py
- Commits present: 8b6ca8b, c8add3e, 1f83ce0, a9c0697, eeb0f32

---
*Phase: 12-import-flow-fixes-and-case-sensitive-re-test*
*Completed: 2026-11-04*
