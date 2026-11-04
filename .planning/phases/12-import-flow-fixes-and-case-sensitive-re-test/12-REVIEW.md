---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
reviewed: 2026-11-04T00:00:00Z
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
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# Phase 12: Code Review Report (incremental review of plans 12-15..12-20)

**Reviewed:** 2026-11-04
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Scope: `git diff 7fb8034 HEAD` for the gap-closure plans 12-15..12-20: the start-window refit and shared offer slot in `import_dialog.py`, the per-source Skip of the 3D model path check (`library_scanner.py`, `models.py`, `scan_cache.py`, `widgets/scan_progress.py`, `main_window.py`), the shared parentless User Guide that remembers the owner's place (`main_window.py`, `help_dialog.py`, `settings.py`), the window-modal main-window questions, the Help text and the tests.

No structural findings (fallow) were supplied for this run.

I traced the skip path end to end and found no correctness defect in it:
- `_check_model_files` drops the lines of a skipped source even when they were found before the answer.
- `scan_all` records `skipped_sources` and `models_unchecked`, and never drops a library or a footprint link.
- `rescan_library` removes a rescanned library from the unchecked record and rebuilds or removes the skip line, and the line stays after the last 3D path line.
- `load_fresh` never presents a skipped scan as complete.
- The format bump to 2 retires old saved scans.
- The new import-closure code signature (`_scan_code_files`) follows relative imports at any depth, and falls back to `""` (never fresh) on a syntax or read error.
- The saved-scan decoder treats the new keys as untrusted data.
- The `_quiet` counter in `HelpDialog` keeps program-driven moves out of the saved place, including the group-header redirect.
- The window-modal `_question` and KiCad-open boxes default to No/Not now.

Remaining defects are one real UX bug (a minimized guide is not brought back), unescaped source names in the Skip button, one test that does not exercise what its name says, and maintainability items.

## Warnings

### WR-01: Help or F1 does not bring back a minimized User Guide

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
Add a test that minimizes the guide, calls `show_guide()` and asserts `not guide.isMinimized()`.

### WR-02: Source name goes unescaped into the Skip button text and tooltip

**File:** `kicad_lib_manager/widgets/scan_progress.py:62-67` (and `:90`)
**Issue:** `self.skip_button.setText(f"Skip {source}")` and the tooltip use the raw top-level folder name. A `QPushButton` treats `&` as a mnemonic marker, so a source folder named `R&D` shows `Skip RD` with an underlined `D` and an Alt+D shortcut. Qt's tooltip auto-detects rich text, so a folder name containing `<...>` would be rendered as markup. The progress label next to it is deliberately `PlainText` (line 31), so the button and tooltip are inconsistent with the file's own plain-text rule. The source is not trusted: it is the first path segment of any `.kicad_mod` found anywhere in the scanned repo, including loose files at the repo root, where `_determine_source` returns the file name itself (for example `Skip Foo.kicad_mod`).
**Fix:** Escape for display and keep the raw value in `_source`:
```python
shown = source.replace("&", "&&")
self.skip_button.setText(f"Skip {shown}")
self.skip_button.setToolTip(Qt.convertFromPlainText(...))  # or wrap the whole tooltip in <p> with html.escape(source)
```
Apply the same escaping to the "Skipping ..." text at line 90.

### WR-03: Test named for a late Skip click never exercises the late-click path

**File:** `tests/test_main_window.py:1517-1553`
**Issue:** `test_a_skip_click_after_the_check_ended_logs_no_skip` claims to cover a Skip click that arrives after the scan stopped asking about that source. The fake scan ignores the hook `skip` entirely and returns `_wurth_scan_result([])` unconditionally. The final assertion `w._scan_result.skipped_sources == []` and the "no skip line" assertion therefore hold by construction and would still pass if `request_skip` wrongly marked the source as skipped. The click also happens while the fake scan is still inside its `checking("WurthElektronik")` window (it waits on `clicked`), so it is a normal in-check click, not a late one. The real late-click behaviour (a request the scan never reads again, so the result carries no skip) is therefore unproven. The sibling test `test_loading_dialog_skips_the_source_being_checked` is similarly shallow: its fake scan returns a hard-coded skipped result regardless of what `skip()` returned, so only the hook plumbing (`answers == [True]`) is checked.
**Fix:** Make the fake scan consult the hook and build its result from the answer, for example call `skip("WurthElektronik")` only before `checking(None)` and never afterward, then drive a click after `checking(None)` is sent. Better, drive the real `scan_all` on the synthetic Würth repo (as `test_generate_after_a_skip_removes_no_entry` already does) with a gated `checking` callback.

## Info

### IN-01: Loose footprint files in a skipped source can only be cleared by a full Rescan, and this path is untested

**File:** `kicad_lib_manager/library_scanner.py:659-667`, `kicad_lib_manager/library_scanner.py:948-960`
**Issue:** `_unchecked_models` adds loose `.kicad_mod` files (those in no `.pretty` library) of a skipped source to `models_unchecked`. `rescan_library` only removes `rel_path` of a library, so those entries can never leave the record through "Rescan this library". The skip line and the saved-scan note then stay until a full Rescan, even when every library of that source was rescanned. That is truthful, but the line text ("except A, B (rescanned since)") gives no hint of what remains. No test creates a loose footprint file in a skipped source, so the `not any(rel.startswith(...))` branch is unexercised.
**Fix:** Add a scan-skip test with a loose `.kicad_mod` in the skipped source and assert `models_unchecked` contains it. Optionally mention "and loose footprint files" in the line when only loose entries remain.

### IN-02: One ScanProgressDialog is created per scan and never released

**File:** `kicad_lib_manager/main_window.py:498`, `kicad_lib_manager/main_window.py:613`, `kicad_lib_manager/widgets/scan_progress.py:70-73`
**Issue:** `ScanProgressDialog(parent=self)` is made for every scan with progress, and `finish()` only closes it. It stays a child of the main window and `self._progress` keeps pointing at the closed dialog until the next scan resets it. Each Rescan, Atomic fix rescan or KiCad-path rescan therefore leaves one dead child widget behind for the life of the window.
**Fix:** In `finish()` call `self.deleteLater()` after `close()`, and set `self._progress = None` in `_on_scan_finished` and `_on_scan_error` after `finish()`.

### IN-03: The import window's own-guide fallback now outlives the window it was opened from

**File:** `kicad_lib_manager/widgets/import_dialog.py:677-689`
**Issue:** When `show_guide` is not given (standalone use and most of the dialog tests), the dialog still creates a parentless `HelpDialog`, and the cleanup that closed it was removed. The guide stays visible after the dialog closes and, being parentless, can keep a standalone process alive. The tests were changed to assert this (`help_window.isVisible()` after the dialog closes), so it is intended, but `MainWindow` always passes `show_guide`, so this branch is unreachable in the app and is a second implementation of the guide lifetime that can drift.
**Fix:** Remove the fallback and require `show_guide` (the dialog tests can pass a stub), or close the fallback guide in the dialog's cleanup as before.

### IN-04: "Stays open beside the other windows" is only true for the dialogs that were made window-modal

**File:** `CLAUDE.md:62`, `kicad_lib_manager/widgets/help_dialog.py` (shortcuts row), `kicad_lib_manager/main_window.py:425`, `:1312`, `:1327`
**Issue:** Plan 12-20 made the path questions, the KiCad-open box, Restore Backup and About window-modal. The folder pickers (`QFileDialog.getExistingDirectory` for the KiCad footprints folder and the destination folder, and the import window's pickers) are still static application-modal dialogs, and none of the new tests covers them. The Help text and project notes say the guide stays open beside the other windows without that exception. This is a documentation overclaim, not a crash.
**Fix:** Either word the claim as "beside the main window and the import window" or make the pickers window-modal (construct a `QFileDialog`, call `setWindowModality(WindowModal)` and `open()`).

### IN-05: Test coupling and brittle negative assertions

**File:** `tests/test_main_window_import.py:1399`, `tests/test_scan_cache.py:427`
**Issue:** `test_main_window_import.py` imports an autouse fixture and four helpers from `test_main_window`, which ties the two modules together at collection time. `test_code_signature_covers_the_scan_modules_only` asserts that `importer/planner.py` is not in the scan's closure. That fixes a negative fact about today's import graph, so a legitimate future `atomic_check` import of the planner (which should then be hashed) would fail the test.
**Fix:** Move the guide helpers and the `_close_guides` fixture to a shared `tests/guidefixtures.py` (the repo already uses `*fixtures.py` modules). In the signature test assert only the positive set and the widgets/main-window exclusions.

---

_Reviewed: 2026-11-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
