---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
reviewed: 2026-11-03T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 12: Code Review Report (gap plan 12-12, toolbar Help, G-12-9)

**Reviewed:** 2026-11-03
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Incremental review of `git diff e86c92f..HEAD` for the four files changed by plan 12-12: the toolbar
Help action in the import window, `HelpDialog(topic=...)` / `show_topic`, the shutdown hook that closes
the guide, the help-text updates, and the new tests.

The new code is sound. Traced and found correct:

- `_build_toolbar` is called before `outer.addWidget(self._stack)`, so the toolbar is item 0 and sits
  outside `_stack`. Finishing disables only `_stack`, so Help stays usable there (and the tests pin it).
- The F1 binding lives only on the `QAction` (WindowShortcut). The window's other `QShortcut` is
  `Ctrl+Return`, so there is no ambiguous second F1 binding.
- `_on_help` returns when `_closing`, creates the `HelpDialog` once as a child of the import dialog
  (so a window-modal parent does not block it) and reuses it afterwards. The deferred import avoids the
  `help_dialog` / `import_dialog` circular import.
- `_shutdown` swaps `_help_dialog` to `None` before closing it, so the call is idempotent, and `_shutdown`
  runs only from `_finish_close` / `closeEvent`, after the Finishing gate. The guide never outlives the
  import window.
- `HelpDialog.__init__` connects `currentItemChanged` before calling `show_topic`, so the page renders for
  the requested topic. An unknown key falls back to the first topic. `show_topic` returns `False` and
  changes nothing for an unknown key. The existing call `HelpDialog(parent=self)` in `main_window.py` is
  unaffected, because `topic` is keyword-only.
- No dialog-level stylesheet is set on `ImportDialog`, so the child guide window does not inherit odd
  styling.

No bugs or security problems were found in the new change. The one new item is a small accessibility gap
(IN-04). The earlier findings in these four files are re-verified as still present and carried forward
with their original IDs. WR-01 (`library_scanner.py`) is outside this scope and was not re-checked here;
it stays tracked in `12-REVIEW-DISPOSITION.md`.

## Warnings

### WR-02: The three required-field hints duplicate the atomic-strip sentences instead of deriving from them

**File:** `kicad_lib_manager/widgets/import_dialog.py:95-98`, `kicad_lib_manager/importer/form.py:151-158`
**Issue:** Still present. `_REQUIRED_HINTS` ("Required - enter a Datasheet link", "Required - type a
Description", "Required - enter the Manufacturer") is a separate literal from `_ATOMIC_SENTENCES`
("Enter a Datasheet link", "Type a Description", "Enter the Manufacturer"). Nothing ties them together.
`test_required_field_hints_match_the_atomic_strip` (`tests/test_import_dialog.py:1257-1271`) compares the
strip text and hint only for Description (`endswith("type a description")`), so the Datasheet and
Manufacturer hints can drift from their strip sentence unnoticed.
**Fix:** Build the hints from the shared sentences defined once in `form.py`:
```python
_REQUIRED_HINTS = {name: f"Required - {s[0].lower()}{s[1:]}" for name, s in REQUIRED_SENTENCES.items()}
```
or loop the test over all three fields: empty each field, wait for the plan, and assert the strip text
ends with the hint after "Required - ".

## Info

### IN-01: Two buttons labelled "Cancel" and the help text uses the word for both

**File:** `kicad_lib_manager/widgets/help_dialog.py:321-331`
**Issue:** Still present. "Install and result" says `Cancel` (Edit page) closes the dialog, then
"`Cancel` to stay where you are" (the Finishing strip) a few lines later. A reader who has not seen the
strip can take the second for the first, which has the opposite effect.
**Fix:** Name the strip's button where it is first introduced ("the Cancel button in the Finishing
strip"), or rename one of the two.

### IN-02: Cancel (and Install Part) are missing from the hand-built tab order

**File:** `kicad_lib_manager/widgets/import_dialog.py:1941-1960`
**Issue:** Still present. `_set_tab_order` chains the header button through the last text Regenerate
button and leaves `_install_btn` and `_cancel_btn` to the default creation order. No test pins that
Cancel follows Install.
**Fix:** Append `self._install_btn, self._cancel_btn` to `chain`, or add a test that tabs from Install
and expects Cancel.

### IN-03: `test_install_progress_and_lock` assertion was weakened

**File:** `tests/test_import_dialog.py:2767-2768`
**Issue:** Still present. The check that no Cancel button is visible during an install became "no Cancel
button is visible and enabled", so a stray visible Finishing-strip Cancel next to the greyed Edit-page
one is no longer detected. `test_cancel_button_disabled_while_installing` covers only the disabled
state.
**Fix:** Also assert `not dialog._finish_cancel.isVisible()` in this test.

### IN-04: The toolbar Help button cannot be reached with Tab; F1 is the only keyboard path

**File:** `kicad_lib_manager/widgets/import_dialog.py:528-544`
**Issue:** New in plan 12-12. `QToolBar` creates its tool buttons with `Qt.FocusPolicy.NoFocus`
(verified offscreen: the `Help` `QToolButton` reports `NoFocus`). A keyboard-only user therefore cannot
Tab to or Space-activate the button; F1 works, but nothing in the tab order shows that Help exists. The
tooltip and the toolbar's accessible name help screen-reader users only partly. This is minor for a
single-user tool that documents F1 in the Shortcuts page and the tooltip.
**Fix:** Optional. Set a focus policy on the button (`toolbar.widgetForAction(action).setFocusPolicy(Qt.FocusPolicy.TabFocus)`)
and add it to `_set_tab_order`, or accept the F1-only path and say so in the help text.

---

_Reviewed: 2026-11-03_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
