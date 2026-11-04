---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
reviewed: 2026-11-04T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - tests/conftest.py
  - tests/test_generated_text.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_official_footprint.py
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 12: Code Review Report (incremental, plans 12-13 and 12-14)

**Reviewed:** 2026-11-04
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Incremental review of `git diff 3bd328bd..HEAD`: the start-page Cancel, `fit_window` / `_show_page`
sizing, the small start page (plan 12-13), and the numbered User Guide menu, section anchors, menu
fold/scroll behaviour and guide fit (plan 12-14). No `.planning` or `kicad_lib_manager` file was changed
by this review.

I traced: `_show_page` through every call site (init, reading, failure, edit, result, change package);
`fit_window` / `_fit_size` / `_place_inside` for a hidden window, a visible window and a window larger
than the screen; `help_outline` / `page_sections` / `render_page` consistency (the `next(sections)` pairing
in `render_page` always matches `page_sections`, because both use `_H3_RE` over the same text); and the
fold logic in `_sync_expansion` (only pages with sections are touched; groups have `page is None` and are left
alone). I found no correctness bug that loses data or breaks the stated behaviour. The new tests cover
duplicate-anchor and anchor-charset invariants, numbering, scroll-into-view, fold state and three screen
models, so the unchecked edges are mostly interaction polish. Remaining items are below. Findings already
in 12-REVIEW-DISPOSITION.md are not repeated, except where the new code widens one.

## Warnings

### WR-01: Start page adds a third "Cancel" button, and two opposite ones can be visible together (widens IN-01)

**File:** `kicad_lib_manager/widgets/import_dialog.py:772-775` (with the finish strip at `:668-670`)
**Issue:** `_start_cancel_btn` ("Cancel", closes the window) stays enabled while the window is Finishing.
The finish strip is parented to the shared `outer` layout, so it is visible above the start page and has its
own "Cancel" (`_finish_cancel`, which aborts the pending close). The test
`test_start_page_cancel_while_reading_waits_then_closes` confirms the start Cancel is clickable during
Finishing. A user who has pressed the bottom-right Cancel and sees the strip then has two buttons with the
same label and opposite meaning on one screen. A second click on the bottom one only runs `_upgrade_to_close`,
so nothing is lost, but the label gives no way to tell which one keeps the window. IN-01 recorded the
edit-page duplicate; this makes the same state reachable on the start page, which is where a user is most
likely to press Cancel during a slow read.
**Fix:** Disable `_start_cancel_btn` (and the edit page's) while `self._finishing` is set, or relabel the
strip's button "Keep open" / "Don't close". Smallest change: in the code that shows the strip, add
`self._start_cancel_btn.setEnabled(False)` and re-enable it where the strip is hidden; add one assertion to
the existing Cancel-while-reading test.

## Info

### IN-01: Re-clicking the current section re-scrolls with the mouse only

**File:** `kicad_lib_manager/widgets/help_dialog.py:667-671`
**Issue:** The "click the current section again" fix is wired to `itemClicked`, which only fires for the
mouse. Keyboard users who press Enter or Space on the selected section after scrolling away get nothing,
because `currentItemChanged` does not fire for the current item. The feature is described as "re-click
scrolls to a section", so this is consistent, but it is the same keyboard-reachability gap as the dispositioned
IN-04.
**Fix:** Also connect `self._toc.itemActivated` to `_on_item_clicked` (same handler, same guard).

### IN-02: `_edit_size` comment says a user resize updates it; only leaving the page does

**File:** `kicad_lib_manager/widgets/import_dialog.py:555` and `:605`
**Issue:** The comment reads "the user's resize updates it", but there is no resize hook: the value is only
refreshed in `_show_page` when the window leaves the edit or result page. A consequence is that it records the
screen-capped size. On a 200% screen the window is held to about 944x452; leaving the page then overwrites a
larger preferred size (say 1200x760) with the capped one, and moving the window to a bigger monitor does not
get the larger size back. This is acceptable behaviour but the comment overstates it.
**Fix:** Reword the comment ("saved when the window leaves the edit page"), or keep the user's wanted size
separately from the capped size by only saving when `self.size()` differs from the last size `fit_window` set.

### IN-03: Duplicate `<h3>` labels within one page are only caught by a test

**File:** `kicad_lib_manager/widgets/help_dialog.py:526-532, 534-540`
**Issue:** `help_outline` keys a section as `f"{key}#{anchor}"` and `HelpDialog._entries` is a dict. Two `<h3>`
headings that slug to the same anchor on one page would collapse to one menu row, while `render_page` would
still number both headings in the page, so menu and page numbers would disagree and both anchors would share a
name. `test_every_page_heading_is_in_the_menu_under_its_page` guards this today, so it is a latent
maintenance trap, not a live bug.
**Fix:** In `page_sections`, assert or de-duplicate (`-2` suffix) the anchor when it repeats.

### IN-04: The screen-area fixture silently does nothing if the module is not yet imported

**File:** `tests/conftest.py:41-54`
**Issue:** `_desktop_screen_area` looks up `sys.modules.get("kicad_lib_manager.widgets.import_dialog")` and
returns quietly when it is missing. Every current module that opens the dialog imports it at the top, so
collection loads it first and the patch applies. A future test that imports the dialog only inside a test body
would run against the 800x800 offscreen screen with no failure, only different window sizes (the
1100x720 assertions would fail far from the cause).
**Fix:** Nothing needed now. If it bites, import the module inside the fixture only when
`"PySide6" in sys.modules`, or document the top-level import requirement in the fixture docstring.

---

_Reviewed: 2026-11-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
