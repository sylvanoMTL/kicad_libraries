---
phase: 05-import-ui-and-post-install
reviewed: 2026-10-22T00:00:00Z
depth: standard
files_reviewed: 35
files_reviewed_list:
  - kicad_lib_manager/importer/content.py
  - kicad_lib_manager/importer/downloads.py
  - kicad_lib_manager/importer/form.py
  - kicad_lib_manager/importer/plan.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/preview.py
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/settings.py
  - kicad_lib_manager/table_generator.py
  - kicad_lib_manager/widgets/conflict_row.py
  - kicad_lib_manager/widgets/content_view.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - kicad_lib_manager/widgets/import_result.py
  - kicad_lib_manager/widgets/library_table.py
  - kicad_lib_manager/widgets/log_panel.py
  - kicad_lib_manager/widgets/preview_tree.py
  - kicad_lib_manager/widgets/theme.py
  - tests/test_help_dialog.py
  - tests/test_import_content.py
  - tests/test_import_dialog.py
  - tests/test_import_downloads.py
  - tests/test_import_form.py
  - tests/test_import_preview.py
  - tests/test_importer_layering.py
  - tests/test_install_options_clear.py
  - tests/test_install_plan.py
  - tests/test_library_table_widget.py
  - tests/test_main_window.py
  - tests/test_main_window_import.py
  - tests/test_preview_tree.py
  - tests/test_settings_import.py
  - tests/test_table_add_entries.py
  - tests/test_kicad_config.py
findings:
  critical: 0
  warning: 6
  info: 8
  total: 14
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-10-22
**Depth:** standard
**Files Reviewed:** 35
**Status:** issues_found

## Summary

The Phase 5 import UI is carefully built. I found no blocker. The preview-equals-install contract (generation numbers, serialised builds, stale-plan drop) holds on every path I traced. Package-derived strings are escaped or shown as plain text in the strip, log panel, token line, failure banner and content view. Test isolation is solid: QSettings, KiCad config, backups and REPO_ROOT are all redirected into `tmp_path`.

I ran the 16 phase-5 test modules: 532 passed and 3 failed. The 3 failures are the known kicad-cli version tests in `tests/test_install_plan.py`, so they are not findings.

**Quick task 261022-gnn (path variables), explicit verification:**

- `sync_kicad_path_vars` (`library_scanner.py:144`) is the only code path that writes `kicad_common.json`. I grepped for `kicad_common`, `sync_kicad_path_vars` and `atomic_write` across the package. The only caller is `MainWindow._sync_path_vars` (`main_window.py:805-809`), which always passes `confirm=self._confirm_path_var_changes`.
- `_sync_path_vars` is reached from `_on_generate` and from `_finish_post_install`, in the new-library branch only.
- `confirm=None` writes nothing and returns `config.confirm_required` (`library_scanner.py:240-245`).
- The refusal runs at lines 237-239. It is evaluated after the read-only parse and before `confirm`, before the `kicad_running` probe, before `backup_file` (274-280) and before `atomic_write_text` (282). A refusal therefore never creates a backup or a write.
- A declined confirmation returns before the backup as well (246-251).
- The worktree test (`(repo_root / ".git").is_file()`) and the other-checkout test (`_norm_path` comparison) are correct for Windows spellings.
- Only the write-ordering and TOCTOU subtleties in WR-06 remain.

## Warnings

### WR-01: `add_library_entries` reports "already listed" when the managed entry points at a different library

**File:** `kicad_lib_manager/table_generator.py:339-343` (consumed at `kicad_lib_manager/main_window.py:672-673`)
**Issue:** `_add_entry` returns `"listed"` as soon as a managed entry (URI contains `${KICAD_LIB_GITHUB}/`) has the same nickname. It does not compare the entry's repo path with the library just installed. I reproduced this with a table holding `IC_X -> WurthElektronik/Symbols/IC_X.kicad_sym` and installing `Custom/Symbols/IC_X`. The result was `table.already_listed: Library tables not changed: IC_X was already listed`.

`_tables_outcome` then shows "Not changed: IC_X was already in the tables" in the Result view. In fact the installed Custom library was not added, and KiCad keeps loading the other library under that nickname. The same happens with a stale entry for a moved library. The scanner already reports nickname collisions, but the Result view contradicts it and tells the user nothing needs doing.
**Fix:** Compare the URI tail with the expected `rel_path` and report a mismatch as a warning, not as `"listed"`:
```python
for entry in table.entries:
    if entry.name != nickname:
        continue
    if _is_managed(entry) and _tail(entry) == rel_path:
        return "listed"
    issues.append(Issue(
        Severity.WARNING,
        "table.external_clash" if not _is_managed(entry) else "table.path_clash",
        f"{filename}: '{nickname}' already points at {entry.uri}; kept it and did not add {uri}",
    ))
    return "skipped"
```
`_tables_outcome` already turns a warning into a WARNING row.

### WR-02: Post-install table write goes to the process working directory when the Destination box is empty

**File:** `kicad_lib_manager/main_window.py:619-638` (same pattern at 816-817 and 293-295)
**Issue:** `dest = Path(self._dest_combo.currentText())` yields `Path('.')` for an empty or whitespace string, and `Path('.').is_dir()` is True. The `dest.is_dir()` guard therefore passes, and `add_library_entries` creates or edits `sym-lib-table` and `fp-lib-table` in the CWD, with backups beside them. `_on_generate` has the same flaw (`dest.exists()`). Phase 5 extends it to a write that happens without the user pressing Generate, as the automatic table update after every new-library install. The combo is editable, so clearing it is easy.
**Fix:** Add a helper that rejects blank text and use it in all three places:
```python
def _dest_path(self) -> Path | None:
    text = self._dest_combo.currentText().strip()
    return Path(text) if text else None
```
Then, in `_finish_post_install`, treat `None` like a missing folder and log "Destination folder is empty".

### WR-03: A one-off conflict build can overlap Install, although the code says it cannot

**File:** `kicad_lib_manager/widgets/import_dialog.py:1892-1894`, `:1821-1833`, `:1588-1589`
**Issue:** The comment at 1588 says "no one-off build reads the files while the install writes them". That is only enforced when a job is queued. `_updating()` does not count `self._oneoff`. When a rebuild ends, `_build_ended` calls `_pump_builds`, which immediately starts a queued one-off job. The same slot then runs `_update_install_state`, which sees "not updating" and enables Install while the one-off `build_plan` is still reading the target library. A click in that window runs `apply_plan` against files that the one-off is hashing and reading.

Jobs left in `_oneoff_jobs` also start during an install, because `_pump_builds` does not check `is_installing()`. The effect is a torn read in the "existing vs incoming" view (wrong content) or a spurious `install.target_unreadable` Issue sent to the log. Nothing is corrupted, but the documented invariant is false.
**Fix:** Count the one-off in `_updating()` and hold jobs while installing:
```python
def _updating(self) -> bool:
    return (self._building is not None or self._oneoff is not None
            or self._queued is not None or self._dirty)

def _pump_builds(self):
    if self._closing or self.is_installing() or self._building is not None or self._oneoff is not None:
        return
    ...
```
Call `_pump_builds()` from `_on_install_done` and `_on_install_failed` so held jobs resume.

### WR-04: Install worker reads `self._plan` from the worker thread; `open_path` has no install guard

**File:** `kicad_lib_manager/widgets/import_dialog.py:2038` and `:972-975`
**Issue:** `_on_install_clicked` captures `plan = self._plan` "the rendered object, never a rebuilt copy (PREV-07)". The worker lambda ignores it and reads `self._plan` when the thread runs: `lambda progress: core.apply_plan(self._plan, ...)`.

Today the attribute cannot change during an install, because `_on_build_result` drops results while installing and `_on_change` is guarded. But `open_path` is public and its only guards are `_closing` and `_open_worker`. It calls `_reset_edit_state`, which sets `self._plan = None`, and `_discard_package`, which closes the package that `apply_plan` reads the model from (WR-04 in the module docstring). Any future caller of `open_path` during an install would make the worker call `apply_plan(None)` or install a different plan than the one previewed.
**Fix:**
```python
worker = self._spawn(lambda progress, p=plan: core.apply_plan(p, backup_root=backup_root, progress=progress))
```
Also add `or self.is_installing()` to the first guard of `open_path`.

### WR-05: GUI thread blocks on worker `wait()` for as long as a kicad-cli call (up to 60 s)

**File:** `kicad_lib_manager/widgets/import_dialog.py:1160-1164` (`_wait_builds`, used at 976 and 2151) and `:2171-2185` (`_shutdown`, via `done()`)
**Issue:** The module contract is "the GUI never blocks" (Phase 4 D-03). Pressing Change..., opening another package, or closing the dialog while a rebuild runs calls `worker.wait()` on the GUI thread. A rebuild includes `kicad_cli.upgrade_symbol_text` with `cli_timeout = 60.0`, so a hung kicad-cli freezes the whole application for up to a minute. `_shutdown` also waits on every open and content worker.

The wait is there to protect the package lifetime, which is a valid reason. The cost is a hard UI freeze with no feedback.
**Fix:** Set a "closing" flag first, disable the dialog and show "Finishing..." (a wait cursor), then close the package from a `QThread.finished` handler once the last worker ends. Or keep the wait and cap it, refusing to discard the package while a build runs, with a status message.

### WR-06: `kicad_common.json` write: stale content after the confirm dialog, and a KiCad-running check that does not gate the write

**File:** `kicad_lib_manager/library_scanner.py:246-282`
**Issue:** This does not break the "never silently" rule; the confirmation is intact. It concerns the quality of the write once confirmed:

1. `new_config` is built from `config`, which was read before `confirm()` ran. `confirm` shows a modal dialog and can stay open for a long time. The file is not re-read afterwards. If KiCad rewrote it meanwhile (common, since KiCad saves on exit), the write replaces those changes with the stale copy plus the new vars. The backup, taken after the confirm, holds KiCad's newer file, so nothing is lost permanently, but the live file silently loses the newer settings.
2. `kicad_running()` is evaluated only after the confirm, so the dialog cannot warn the user. The result is only a WARNING issue, and the write proceeds anyway. The text says "Close KiCad and press Generate again", but the file is already written. On the post-install path (`_finish_post_install` -> `_sync_path_vars`) "press Generate" is also the wrong advice.
3. `kicad_running` shells out to `tasklist` (5 s timeout) on the GUI thread, inside `_on_scan_finished` on the post-install path.

**Fix:** After a positive confirm, re-read the file with `fsutil.read_source` and abort with an Issue if the bytes differ from the first read. Ideally run `running()` before `confirm` and pass the names into the dialog text. Reword the warning to "KiCad is running; it may overwrite these variables when it exits. Close KiCad and re-run this change if they revert."

## Info

### IN-01: Invisible character as a source literal

**File:** `kicad_lib_manager/widgets/import_dialog.py:73`
**Issue:** `_ZWSP` is assigned a literal U+200B character in the source. It is invisible in editors and diffs, and the review hook flagged it.
**Fix:** Use the Python escape sequence for U+200B (backslash, u, 2, 0, 0, b) in the string literal instead of the raw character.

### IN-02: Three near-identical elided-label classes

**File:** `kicad_lib_manager/widgets/import_dialog.py:119-168` (`_OfferLabel`), `kicad_lib_manager/widgets/conflict_row.py:42-71` (`_ElidedLabel`), `kicad_lib_manager/widgets/import_result.py:24-68` (`ElidedLabel`)
**Issue:** They duplicate the same width-based elide logic, including the `width < 40` heuristic. A fix in one is easy to miss in the others.
**Fix:** Keep `ElidedLabel` in `import_result.py` or move it to `widgets/`, and add a `prefix` and `suffix` option for the Offer label case.

### IN-03: Dead field and unused parameters

**File:** `kicad_lib_manager/main_window.py:49-54` and `kicad_lib_manager/importer/preview.py:329`
**Issue:** `_PostInstall.symbol` is set at line 766 and never read. `file_counts(plan, candidate, options)` ignores `candidate` and `options`.
**Fix:** Drop the field, or use it in the Result row text. Trim the parameters, or document them as reserved.

### IN-04: Truncation wording and an oversized first line in `cap_lines`

**File:** `kicad_lib_manager/importer/content.py:41-48`
**Issue:** `cap_lines` is also used for plain new-file text (line 140), but its closing line always says "Diff truncated". If the very first line alone exceeds `MAX_BYTES`, `kept` is 0 and the view shows only the truncation message, with no content at all.
**Fix:** Take a `noun` argument ("Text" or "Diff"). When `kept == 0`, keep a clipped first line, for example `lines[0][:MAX_BYTES]`.

### IN-05: Worker threads are never released while the dialog lives

**File:** `kicad_lib_manager/widgets/import_dialog.py:1008-1022`
**Issue:** The `_workers` list gets one QThread per rebuild (every debounce), content view, offer lookup and KiCad check, and it is never pruned. The comment explains why `deleteLater` is avoided (an access violation). Each retained object holds only its closure, because `_reap` clears `value`, so the cost is small. Still, a long editing session accumulates hundreds of finished threads.
**Fix:** Remove finished workers from the list in `_reap` (drop the Python reference only, not `deleteLater`), or keep a bounded recent list.

### IN-06: Package-derived names are used in tooltips (Qt rich-text heuristic)

**File:** `kicad_lib_manager/widgets/import_dialog.py:1273`, `:1285`, `:1154`, `:1381-1382`
**Issue:** The rest of the module is careful to show package strings as plain text. Tooltips go through Qt's `mightBeRichText` heuristic. A symbol, footprint or model name that begins with a tag, such as `<b>x</b>` or `<img ...>`, would render as markup. The impact is cosmetic and local, but it is inconsistent with the "never interpreted as markup" claim in the module docs.
**Fix:** Pass tooltips through `html.escape` wrapped in `<span>` or `<pre>`, or prefix the plain text with a leading non-tag character such as a zero-width space.

### IN-07: `self.result` shadows `QDialog.result()`

**File:** `kicad_lib_manager/widgets/import_dialog.py:248-249`
**Issue:** The instance attribute replaces the Qt method on `ImportDialog`. Any generic code (a test helper, Phase 6, a QtTest wait) that calls `dialog.result()` raises `TypeError: 'InstallResult' object is not callable`.
**Fix:** Rename it to `install_result`, which matches the existing `result_plan`, and update the readers (`main_window` and the tests).

### IN-08: Test hygiene

**File:** `tests/test_import_content.py:7` (unused `import pytest`), `tests/test_import_dialog.py:1576` (unused `QApplication` import), and fixed sleeps at `tests/test_import_dialog.py:477, 1290, 1301, 1454, 1466, 1532, 2411, 2662`
**Issue:** Besides the unused imports, the fixed `qtbot.wait(150..450)` calls are timing-dependent: they exercise the 300 ms debounce and the 150 ms busy timer on a loaded CI machine. The risk is flakiness, not a correctness defect.
**Fix:** Remove the unused imports. Where possible, wait on a condition with `qtbot.waitUntil(...)` or on a signal. Keep the timed waits only where the delay itself is under test.

---

_Reviewed: 2026-10-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
