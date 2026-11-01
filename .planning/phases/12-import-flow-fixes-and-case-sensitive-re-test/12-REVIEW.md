---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
reviewed: 2026-11-01T00:00:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - .gitignore
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/table_generator.py
  - kicad_lib_manager/widgets/backup_dialog.py
  - kicad_lib_manager/widgets/conflict_row.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - kicad_lib_manager/widgets/theme.py
  - tests/README.md
  - tests/casefixtures.py
  - tests/conftest.py
  - tests/test_backup_dialog.py
  - tests/test_case_sensitive_install.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_install_plan.py
  - tests/test_kicad_config.py
  - tests/test_main_window.py
  - tests/test_main_window_import.py
  - tests/test_table_add_entries.py
findings:
  critical: 0
  warning: 5
  info: 6
  total: 11
status: issues_found
---

# Phase 12: Code Review Report

**Reviewed:** 2026-11-01
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Summary

I reviewed the Phase 12 diff (`59006ff..HEAD`) of every listed file. For the Finishing state in `import_dialog.py` I traced the signal order, the deferred-close gate, the Cancel path and the probe-cancel flag. For `main_window.py` I traced the off-thread KiCad-open check and the deferred close. I also traced the re-read-and-merge write in `library_scanner.py` and the repoint/clash rules in `table_generator.py`.

No Critical issues. The core thread design holds up:
- `finished` is queued behind `result`, so `_try_finish` always sees up-to-date `_building` / `_oneoff` slots.
- `_reap` joins the finishing thread with a bounded wait before the gate opens, so a dialog is not `deleteLater`'d under a running worker.
- Lambda connections to `QThread.finished` run on the GUI thread. I checked this empirically with PySide6 6.12 in a throwaway script.
- Finishing/Cancel keep the override cursor paired.
- Close-over-change/open upgrade is consistent, and Cancel after a close re-probes the commit panel.

The remaining issues are robustness gaps in the new main-window path-variable flow, a residual lost-update window in the `kicad_common.json` write, and several plain-language violations in new text.

## Warnings

### WR-01: An exception in the path-variable check leaves `_path_var_busy` set for the whole session

**File:** `kicad_lib_manager/main_window.py:1183-1199` (and `1161-1166`)
**Issue:** `_sync_path_vars` sets `_path_var_busy = True`. It is only cleared at the end of `_on_path_var_check`, on the normal return path or when `_close_after_check` is set. `_on_path_var_check` runs `sync_kicad_path_vars` (file reads, JSON parse, config-dir discovery, backup, atomic write), `_log_issues` and a modal `QMessageBox.exec`. If any of these raises, for example a `PermissionError` from the config-dir scan, the slot aborts with the flag still True. Every later Generate or post-install repoint then returns at `if self._path_var_busy: return`, with no log line. The path-variable sync is dead until restart, and the owner is never told.
**Fix:**
```python
def _on_path_var_check(self, names):
    retry = False
    try:
        if self._close_after_check:
            return
        names = list(names)
        issues = sync_kicad_path_vars(REPO_ROOT, running=lambda: names,
                                      confirm=lambda c: self._confirm_path_var_changes(c, names))
        self._log_issues(issues)
        retry = any(i.code == "config.retry" for i in issues)
    except Exception as e:  # slot boundary: never leave the busy flag set
        self._log.log(f"Could not update KiCad's path settings: {e}", "error")
    finally:
        if not retry:
            self._path_var_busy = False
    if retry:
        self._start_path_var_check()
```

### WR-02: A lost-update window remains in the `kicad_common.json` write

**File:** `kicad_lib_manager/library_scanner.py:329-355`
**Issue:** The re-read after the confirm closes the long window, since the owner may read the dialog for minutes. A second, smaller window remains between that re-read (`_read_config`, around line 306) and `fsutil.atomic_write_text` (line 355). In between the code runs `deepcopy`, `json.dumps`, `_only_vars_changed` and `fsutil.backup_file`, which is a file copy plus a directory listing for pruning. The write replaces the whole file from the text read before the backup. Anything KiCad saves in that interval is silently lost. This is the situation the "KiCad is open" flow was built for: with KiCad open, "Change anyway" is exactly when KiCad may be saving.
**Fix:** Take the backup before the final read, or re-read just before the replace and compare. For example, call `fsutil.read_source(config_file)` immediately before `atomic_write_text`. If its `.text` differs from `src.text`, loop back to the merge pass instead of writing. The merge is only the two `environment.vars` keys, so a retry is cheap.

### WR-03: `_close_after_check` is a latch that is never cleared

**File:** `kicad_lib_manager/main_window.py:1339-1343` (set), `1183-1186` (consumer)
**Issue:** The flag is set when a close arrives during the KiCad-open check, and nothing ever resets it. If the deferred `self.close()` from `_on_path_var_check_finished` is itself vetoed, for example because `closeEvent` ignores the close while the dialog is installing, the window stays open and the flag stays True. From then on `_on_path_var_check` returns immediately for every later Generate or post-install repoint. No dialog is shown and nothing is logged, and `_path_var_busy` is cleared, so the sync looks as if it worked. `_close_after_dialog` has the matching reset (`leave_cancelled`); this flag has none.
**Fix:** Clear `_close_after_check` at the top of `closeEvent` when the close is allowed to proceed. Also clear it whenever `closeEvent` takes an `event.ignore()` path that is not the check deferral. Alternatively, have the finished handler do `self._close_after_check = False` before calling `self.close()`, and re-set it only if `closeEvent` defers again.

### WR-04: New user-facing text uses file names and tool names (owner preference: plain language)

**File:** `kicad_lib_manager/widgets/import_dialog.py:107`, `kicad_lib_manager/widgets/help_dialog.py:320-321`, `kicad_lib_manager/library_scanner.py:323`, `kicad_lib_manager/main_window.py:1140`
**Issue:** New Phase 12 text names code or tool identifiers:
- `SLOW_CLI_TEXT` = "kicad-cli is slow to respond (it gives up after 60 s)", and the matching Help sentence "kicad-cli is slow to respond; kicad-cli gives up after 60 seconds".
- The log warning "kicad_common.json kept changing while you were asked".
- The "KiCad is open" dialog body "These KiCad path variables in kicad_common.json would change".

This conflicts with the stored preference of no jargon or raw field and file names in user-facing text.
**Fix:** Use wording such as "KiCad's converter is slow to respond (it gives up after 60 seconds)", "KiCad's settings file kept changing while you were asked; nothing was written", and "These KiCad path settings would change". Update the matching assertions in the tests.

### WR-05: The "library missing from the tables" decision is derived by matching message text

**File:** `kicad_lib_manager/main_window.py:888-894`
**Issue:** `missing` is built by testing `f"{table} does not list {name}" in not_listed`, where `not_listed` is a set of `Issue.text` strings. The producing text lives in `table_generator.add_library_entries` (`f"{filename} does not list {nickname}"`). The two sites are coupled by an English sentence, so rewording either message (for example a WR-04 plain-language edit) silently makes `missing` empty. The "Press Generate Tables" hint then disappears and no test of the main window fails unless it asserts that exact text. `Issue` has a `code` but no structured payload.
**Fix:** Have `add_library_entries` report the outcome in a structured way, for example a second return value or a small result dataclass listing `(table_filename, nickname, outcome)`. Alternatively, add a `target` or `nickname` field to `Issue`. Then build `missing` from that data instead of from the message text.

## Info

### IN-01: A second `_sync_path_vars` while one is in flight is dropped without a log line

**File:** `kicad_lib_manager/main_window.py:1161-1166`
**Issue:** `if self._path_var_busy: return` gives no feedback. If the owner presses Generate while the KiCad-open check or its dialog is still active, or an install finishes mid-check, the request is lost. The Generate log has already said tables were written and the owner sees no path-variable result.
**Fix:** Log an info line such as "KiCad path check already running" so the owner knows the request was not forgotten.

### IN-02: `closeEvent` still joins the scan worker without a bound

**File:** `kicad_lib_manager/main_window.py:1349` (and `578`)
**Issue:** `self._worker.wait()` has no timeout, on the GUI thread, in `closeEvent`. Phase 12 removed the other unbounded GUI-thread joins. A long repository scan therefore freezes the window on close. Pre-existing, but the function was reworked in this phase around the same principle.
**Fix:** Apply the same deferral used for the path-variable check: ignore the close, set a flag, and close from the worker's `finished` handler. Alternatively, accept the join and note it as an intentional exception.

### IN-03: `_same_rel` folds case only on Windows, so a case-insensitive macOS volume reports a false clash

**File:** `kicad_lib_manager/table_generator.py:303-317`
**Issue:** `fold=None` means `os.name == "nt"`. On default macOS (APFS, case-insensitive) a table entry differing from the new path only by letter case compares as different. The `(repo_root / tail).exists()` check then sees the same file and reports `table.path_clash` ("Rename one of them") instead of "already listed". This only affects the case-twin scenario Phase 12 targets, on a platform the project says to keep working.
**Fix:** Decide `fold` from the real file system, for example by testing whether `(repo_root / rel).exists()` also holds for the case-swapped spelling, or by checking `Path.samefile`.

### IN-04: A conflict-compare request is silently dropped if the dialog is Finishing when its build ends

**File:** `kicad_lib_manager/widgets/import_dialog.py:2669`
**Issue:** `on_result(plan, error)` is skipped when `_finishing`. If the owner then presses Cancel on the Finishing strip (the dialog stays open), the compare they asked for never appears and nothing says so. It is an edge case, but the one-off job is lost.
**Fix:** On Cancel, re-queue the dropped job, or log "Comparison cancelled" when the on_result is skipped.

### IN-05: Restore with a blank folder box does nothing and gives no feedback

**File:** `kicad_lib_manager/widgets/backup_dialog.py:91-94`
**Issue:** After a scan the owner clears the folder box. Restore stays enabled because the list still holds the old rows, and `_on_accept` returns silently when `_folder()` is None. Nothing happens and the dialog stays open. The same path can restore the list's backup number against a folder the owner typed after scanning, a mismatch that already existed before Phase 12.
**Fix:** On a blank folder, either clear the list and disable Restore (call `_scan()`), or show a short label such as "Enter a backup folder". Optionally remember the folder that was actually scanned and use that for `selected_folder`.

### IN-06: The Qt teardown hook can hide a hung worker for 60 s per widget

**File:** `tests/conftest.py:36`
**Issue:** `thread.wait(60000)` joins every `QThread` child of each registered widget. A test that leaves a gated worker running stalls 60 s per thread and then passes (or crashes at destruction) instead of failing clearly. The hook also relies on pytest-qt's undocumented `item.qt_widgets` attribute, which is present in the installed version.
**Fix:** If `wait` returns False, `pytest.fail(...)` naming the thread so the leak is visible. Add a comment pinning the pytest-qt version this relies on.

---

_Reviewed: 2026-11-01_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
