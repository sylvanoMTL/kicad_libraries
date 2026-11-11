---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
reviewed: 2026-11-11T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - CLAUDE.md
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/models.py
  - kicad_lib_manager/scan_cache.py
  - kicad_lib_manager/settings.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - kicad_lib_manager/widgets/scan_progress.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_main_window.py
  - tests/test_main_window_import.py
  - tests/test_scan_cache.py
  - tests/test_scan_skip.py
findings:
  critical: 0
  warning: 5
  info: 7
  total: 12
status: issues_found
---

# Phase 12: Code Review Report (incremental reviews of plans 12-15..12-20 and gap plan 12-21)

**Reviewed:** 2026-11-11
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

This report keeps every finding from the earlier review of plans 12-15..12-20 (WR-06..WR-08, IN-07..IN-11, unchanged below) and adds the findings for gap plan 12-21 (`git diff 2bdb16a..HEAD` over `CLAUDE.md`, `main_window.py`, `widgets/help_dialog.py`, `tests/test_help_dialog.py`, `tests/test_main_window.py`): the User Guide reopening on the chosen section with its heading at the top, the asked-topic flag used by the main-window Help, the left-button hold on the guide menu, and the `_MenuSelectionDelegate` selected-row painter.

No structural findings (fallow) were supplied for this run.

Plan 12-21 review result: no crash or data-loss defect. The targeted tests pass (16 new help-dialog tests, 17 guide/help main-window tests, run offscreen with the venv python). The hold logic is sound for the paths I traced: the viewport filter sees the press before the view selects, a release always clears the hold, and a hide, a key press or a lost button state all end it. The `_quiet` counter still keeps programmatic moves out of the saved place. The two new warnings are about the asked-topic flag being a proxy for "the owner is not on their own place" rather than a comparison of places, so the behaviour documented in CLAUDE.md and the Help text is not exactly what the code does.

Earlier findings (WR-06..WR-08, IN-07..IN-11) are carried forward unchanged; I did not re-verify them against HEAD in this pass except that WR-06 remains relevant (show_guide still has no un-minimize step).

## Warnings

### WR-06: Help or F1 does not bring back a minimized User Guide

**File:** `kicad_lib_manager/main_window.py:1369-1374`
**Issue:** `show_guide` ends with `guide.show(); guide.raise_(); guide.activateWindow()`. For a guide that is already visible but minimized, `show()` returns early because the widget is already shown, and `raise_()` / `activateWindow()` do not restore a minimized top-level window on Windows. The guide is now a parentless window with its own taskbar button, so minimizing it is an ordinary action. After that, F1 or Help > User Guide appears to do nothing, and the import window's Help button (which routes through the same method) does nothing either. Previously the guide was a modal child, so this state could not arise. No test covers it (the new tests only close the guide). Verify on Windows; this was reasoned from Qt behaviour, not reproduced offscreen.
**Fix:**
```python
guide.show()
if guide.isMinimized():
    guide.setWindowState(guide.windowState() & ~Qt.WindowState.WindowMinimized)
guide.raise_()
guide.activateWindow()
```
Add a test that minimizes the guide, calls `show_guide()` and asserts `not guide.isMinimized()`. (Note for plan 12-21: the un-minimize call is programmatic, so the resulting show event may be non-spontaneous and then runs the new `_show_current_heading` in `HelpDialog.showEvent`, which is acceptable because the guide is being brought back on purpose.)

### WR-07: Source name goes unescaped into the Skip button text and tooltip

**File:** `kicad_lib_manager/widgets/scan_progress.py:62-67` (and `:90`)
**Issue:** `self.skip_button.setText(f"Skip {source}")` and the tooltip use the raw top-level folder name. A `QPushButton` treats `&` as a mnemonic marker, so a source folder named `R&D` shows `Skip RD` with an underlined `D` and an Alt+D shortcut. Qt's tooltip auto-detects rich text, so a folder name containing `<...>` would be rendered as markup. The progress label next to it is deliberately `PlainText` (line 31), so the button and tooltip are inconsistent with the file's own plain-text rule. The source is not trusted: it is the first path segment of any `.kicad_mod` found anywhere in the scanned repo, including loose files at the repo root, where `_determine_source` returns the file name itself (for example `Skip Foo.kicad_mod`).
**Fix:** Escape for display and keep the raw value in `_source`:
```python
shown = source.replace("&", "&&")
self.skip_button.setText(f"Skip {shown}")
self.skip_button.setToolTip(Qt.convertFromPlainText(...))  # or wrap the whole tooltip in <p> with html.escape(source)
```
Apply the same escaping to the "Skipping ..." text at line 90.

### WR-08: Test named for a late Skip click never exercises the late-click path

**File:** `tests/test_main_window.py:1517-1553`
**Issue:** `test_a_skip_click_after_the_check_ended_logs_no_skip` claims to cover a Skip click that arrives after the scan stopped asking about that source. The fake scan ignores the hook `skip` entirely and returns `_wurth_scan_result([])` unconditionally. The final assertion `w._scan_result.skipped_sources == []` and the "no skip line" assertion therefore hold by construction and would still pass if `request_skip` wrongly marked the source as skipped. The click also happens while the fake scan is still inside its `checking("WurthElektronik")` window (it waits on `clicked`), so it is a normal in-check click, not a late one. The real late-click behaviour (a request the scan never reads again, so the result carries no skip) is therefore unproven. The sibling test `test_loading_dialog_skips_the_source_being_checked` is similarly shallow: its fake scan returns a hard-coded skipped result regardless of what `skip()` returned, so only the hook plumbing (`answers == [True]`) is checked.
**Fix:** Make the fake scan consult the hook and build its result from the answer, for example call `skip("WurthElektronik")` only before `checking(None)` and never afterward, then drive a click after `checking(None)` is sent. Better, drive the real `scan_all` on the synthetic Würth repo (as `test_generate_after_a_skip_removes_no_entry` already does) with a gated `checking` callback.

### WR-09: Main-window Help scrolls a visible guide back to the heading when the asked topic is the owner's own place, contradicting the documented "only brought to the front"

**File:** `kicad_lib_manager/main_window.py:1368-1370`, `kicad_lib_manager/widgets/help_dialog.py:707-711`, `:736-742`; text in `CLAUDE.md:62` and the `shortcuts` help row (`help_dialog.py:~482`)
**Issue:** `show_guide(None)` decides with `guide.shows_asked_topic()`, a flag that is True from the moment `show_topic` runs until the owner moves in the menu. It never compares the shown key with the saved key. Trace: the owner last chose "Importing Parts" (`importing`, saved). The import window's Help calls `show_guide("importing")`, so the flag is True, though the guide is on exactly the remembered place. The owner reads down the page. F1 from the main window then takes the `shows_asked_topic()` branch, runs `show_remembered()` -> `show_topic("importing")` -> `_show_current_heading()`, and for a page entry (`anchor is None`) sets the scrollbar to 0. The page jumps to the top. CLAUDE.md and the Help text both promise: "If it is already open on that place, it is only brought to the front", and the `show_guide` docstring says a visible guide on the owner's own place is only raised. The same jump happens for a section anchor (it re-anchors, discarding any scroll below the heading). No test covers an asked topic equal to the saved key.
**Fix:** Compare places instead of (or as well as) trusting the flag, for example in `show_guide`:
```python
elif not first and (not guide.isVisible() or (guide.shows_asked_topic() and guide.current_key() != load_help_topic())):
    guide.show_remembered()
```
or make `HelpDialog.show_remembered` return early (clearing `_on_asked_topic`) when the visible current key already equals the saved key. Add a test: save `importing`, `show_guide("importing")`, scroll down, `show_guide()`, assert the scroll value is unchanged.

### WR-10: Clicking the already-current asked row is neither saved nor clears the asked-topic flag, so the next Help pulls the owner to a different place

**File:** `kicad_lib_manager/widgets/help_dialog.py:786-789` and `:843-847` (`_on_item_clicked`)
**Issue:** The flag is cleared, and the place saved, only in `_on_topic_selected`, which runs on `currentItemChanged`. When the guide shows an asked topic (for example `importing` from the import window's Help) and the owner clicks that same menu row to say "this is the place I want", no `currentItemChanged` fires: `_on_asked_topic` stays True and `save_help_topic` is not called (this part predates 12-21; the flag part is new). The owner has chosen the place but the guide still treats it as caller-driven, so a later F1 from the main window runs `show_remembered()` and moves them to the previously saved, different place, losing the page they just chose. `_on_item_clicked` already receives this exact event (it re-scrolls the section) but ignores the owner's intent.
**Fix:** In `_on_item_clicked`, when `item is self._toc.currentItem()` and the entry has a page, save it and clear the flag:
```python
if item is self._toc.currentItem() and entry is not None and entry.page is not None and not self._quiet:
    save_help_topic(entry.key)
    self._on_asked_topic = False
```
Add a test: open with `topic="importing"`, click the `importing` row, assert `settings.load_help_topic() == "importing"` and `not shows_asked_topic()`.

## Info

### IN-07: Loose footprint files in a skipped source can only be cleared by a full Rescan, and this path is untested

**File:** `kicad_lib_manager/library_scanner.py:659-667`, `kicad_lib_manager/library_scanner.py:948-960`
**Issue:** `_unchecked_models` adds loose `.kicad_mod` files (those in no `.pretty` library) of a skipped source to `models_unchecked`. `rescan_library` only removes `rel_path` of a library, so those entries can never leave the record through "Rescan this library". The skip line and the saved-scan note then stay until a full Rescan, even when every library of that source was rescanned. That is truthful, but the line text ("except A, B (rescanned since)") gives no hint of what remains. No test creates a loose footprint file in a skipped source, so the `not any(rel.startswith(...))` branch is unexercised.
**Fix:** Add a scan-skip test with a loose `.kicad_mod` in the skipped source and assert `models_unchecked` contains it. Optionally mention "and loose footprint files" in the line when only loose entries remain.

### IN-08: One ScanProgressDialog is created per scan and never released

**File:** `kicad_lib_manager/main_window.py:498`, `kicad_lib_manager/main_window.py:613`, `kicad_lib_manager/widgets/scan_progress.py:70-73`
**Issue:** `ScanProgressDialog(parent=self)` is made for every scan with progress, and `finish()` only closes it. It stays a child of the main window and `self._progress` keeps pointing at the closed dialog until the next scan resets it. Each Rescan, Atomic fix rescan or KiCad-path rescan therefore leaves one dead child widget behind for the life of the window.
**Fix:** In `finish()` call `self.deleteLater()` after `close()`, and set `self._progress = None` in `_on_scan_finished` and `_on_scan_error` after `finish()`.

### IN-09: The import window's own-guide fallback now outlives the window it was opened from

**File:** `kicad_lib_manager/widgets/import_dialog.py:677-689`
**Issue:** When `show_guide` is not given (standalone use and most of the dialog tests), the dialog still creates a parentless `HelpDialog`, and the cleanup that closed it was removed. The guide stays visible after the dialog closes and, being parentless, can keep a standalone process alive. The tests were changed to assert this (`help_window.isVisible()` after the dialog closes), so it is intended, but `MainWindow` always passes `show_guide`, so this branch is unreachable in the app and is a second implementation of the guide lifetime that can drift.
**Fix:** Remove the fallback and require `show_guide` (the dialog tests can pass a stub), or close the fallback guide in the dialog's cleanup as before.

### IN-10: "Stays open beside the other windows" is only true for the dialogs that were made window-modal

**File:** `CLAUDE.md:62`, `kicad_lib_manager/widgets/help_dialog.py` (shortcuts row), `kicad_lib_manager/main_window.py:425`, `:1312`, `:1327`
**Issue:** Plan 12-20 made the path questions, the KiCad-open box, Restore Backup and About window-modal. The folder pickers (`QFileDialog.getExistingDirectory` for the KiCad footprints folder and the destination folder, and the import window's pickers) are still static application-modal dialogs, and none of the new tests covers them. The Help text and project notes say the guide stays open beside the other windows without that exception. This is a documentation overclaim, not a crash.
**Fix:** Either word the claim as "beside the main window and the import window" or make the pickers window-modal (construct a `QFileDialog`, call `setWindowModality(WindowModal)` and `open()`).

### IN-11: Test coupling and brittle negative assertions

**File:** `tests/test_main_window_import.py:1399`, `tests/test_scan_cache.py:427`
**Issue:** `test_main_window_import.py` imports an autouse fixture and four helpers from `test_main_window`, which ties the two modules together at collection time. `test_code_signature_covers_the_scan_modules_only` asserts that `importer/planner.py` is not in the scan's closure. That fixes a negative fact about today's import graph, so a legitimate future `atomic_check` import of the planner (which should then be hashed) would fail the test.
**Fix:** Move the guide helpers and the `_close_guides` fixture to a shared `tests/guidefixtures.py` (the repo already uses `*fixtures.py` modules). In the signature test assert only the positive set and the widgets/main-window exclusions.

### IN-12: Any key press on the menu ends the hold mid-drag, including bare modifier keys

**File:** `kicad_lib_manager/widgets/help_dialog.py:684-690` (the `KeyPress` branch of `eventFilter`)
**Issue:** The branch clears `_menu_held` and queues the deferred fold on every `KeyPress` delivered to the tree, to recover from a release that never arrived. A Shift, Ctrl or Alt press (or auto-repeat of any key) while the left button is genuinely held, for example Shift pressed during a drag-select, also ends the hold. The fold then runs with the button still down, which is the exact "rows move under a pressed mouse button, wrong row saved" case the hold exists to prevent. The lost-release recovery is already covered by `QGuiApplication.mouseButtons()` in `_on_topic_selected` and by `hideEvent`.
**Fix:** Ignore the key when the left button is really down, and ignore modifier-only keys:
```python
elif watched is self._toc and kind == QEvent.Type.KeyPress and not (QGuiApplication.mouseButtons() & Qt.MouseButton.LeftButton):
```
Add a test pressing and releasing Shift between mouse press and release.

### IN-13: Selected-row delegate depends on `option.widget` and on the click-through tests rely on sleeps

**File:** `kicad_lib_manager/widgets/help_dialog.py:52-61`, `tests/test_help_dialog.py` (`_shown_dialog`, `test_held_press_on_a_page_row_selects_that_row`), `tests/test_main_window.py:1670`
**Issue:** (1) `_MenuSelectionDelegate.paint` calls `opt.widget.style()`; `option.widget` is set by the view, but `QStyleOptionViewItem.widget` is `None` if the delegate is ever painted with a bare option (a unit test, a future `QListView` reuse), which raises `AttributeError` inside a paint event. Use `(opt.widget.style() if opt.widget else QApplication.style())`. (2) The new tests use fixed `qtbot.wait(50/150)` sleeps to let queued zero-timer folds run, which can be flaky on a loaded CI machine; wait on a condition (`qtbot.waitUntil`) where one exists. (3) `tests/test_main_window.py` now imports `_heading_near_top` from `test_help_dialog`, adding a second cross-test-module dependency of the kind already noted in IN-11; the helper belongs in the shared `tests/guidefixtures.py` suggested there.
**Fix:** As listed per sub-point; none is a runtime defect in the app today.

---

_Reviewed: 2026-11-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
