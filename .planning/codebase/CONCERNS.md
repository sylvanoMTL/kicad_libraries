---
last_mapped_commit: 3353ce8161c4870e85b50fc8d607d41bb942c796
last_mapped_at: 2026-10-18
---
# Codebase Concerns

**Analysis Date:** 2026-10-18

Scope: `kicad_lib_manager/` (package), `kicad_lib_manager.py` (GUI entry point), `generate_lib_tables.py` (CLI). Library submodules (`Custom/`, `WurthElektronik/`) and `downloaded_examples/` were excluded by request.

## Tech Debt

**Duplicated table generation logic (GUI vs CLI):**
- Issue: `generate_lib_tables.py` re-implements library discovery and table formatting (`find_symbol_libs`, `find_footprint_libs`, `generate_sym_lib_table`, `generate_fp_lib_table`) instead of reusing `kicad_lib_manager/library_scanner.py` and `kicad_lib_manager/table_generator.py`. The two paths have already diverged (see Fragile Areas and Security).
- Files: `generate_lib_tables.py:30-72`, `kicad_lib_manager/table_generator.py:101-132`, `kicad_lib_manager/library_scanner.py:150-184`
- Impact: Fixes applied to one path (merge, backup, skip-dirs, collision checks) silently do not apply to the other.
- Fix approach: Make the CLI a thin wrapper that calls `scan_all` and `write_tables` (with a `--no-gui` flag), or delete the CLI if the GUI is the supported path (CLAUDE.md already describes it as "legacy, GUI preferred").

**Duplicated "existing tables" logging and destination-history update:**
- Issue: `_check_existing_tables` (`main_window.py:246-259`) and `_on_dest_changed` (`main_window.py:450-463`) contain the same loop. The "save destination to history and repopulate combo" block is repeated three times (`main_window.py:400-405`, `440-447`, plus `_populate_dest_combo` at `193-202`).
- Files: `kicad_lib_manager/main_window.py`
- Impact: Drift risk; any change must be made in several places.
- Fix approach: Extract `_refresh_dest_combo(history)` and `_log_existing_tables(dest)`.

**Dead code:**
- Issue: `list_backups` (`kicad_lib_manager/table_generator.py:212-219`) and `restore_backup` (`table_generator.py:245-259`) are never called. Only `restore_backup_pair` is used by the GUI.
- Files: `kicad_lib_manager/table_generator.py`
- Impact: Misleading surface area; `restore_backup` also has a different semantic (single file) than the paired restore.
- Fix approach: Delete both, or wire them up and remove `restore_backup_pair` duplication.

**Hard-coded version and metadata:**
- Issue: About dialog hard-codes `v1.0` and a GitHub URL (`main_window.py:479-483`). The Windows default folder `C:/Program Files` is hard-coded in two dialogs (`main_window.py:230`, `422`) and in `library_scanner.py:93`.
- Files: `kicad_lib_manager/main_window.py`, `kicad_lib_manager/library_scanner.py`
- Impact: Version string drifts from releases; non-Windows users get Windows-only defaults.
- Fix approach: Single `__version__` constant; platform-specific default paths in one helper.

**No dependency manifest and no tests:**
- Issue: No `requirements.txt`, `pyproject.toml`, or `tests/` directory exists. PySide6 is installed unpinned (CLAUDE.md: `pip install PySide6`). The code uses `list[str] | None` and `Path | None` syntax, which requires Python 3.10+, and this is not documented in the repo.
- Files: repository root (absence), `kicad_lib_manager/table_generator.py:64`, `kicad_lib_manager/library_scanner.py:16`
- Impact: Environment drift between machines; regressions in parser and merge logic are not caught.
- Fix approach: Add `requirements.txt` with a pinned PySide6 range and a `python_requires >= 3.10` note; add a `tests/` suite (see Test Coverage Gaps).

## Known Bugs

**External table entries silently dropped on regeneration:**
- Symptoms: Entries in an existing `sym-lib-table` or `fp-lib-table` that do not match the exact regex are not carried over into the regenerated file, with no warning. The log then reports `preserved N external` counting only the matched entries.
- Files: `kicad_lib_manager/table_generator.py:11-17` (regex), `table_generator.py:20-42` (`parse_lib_table`), `table_generator.py:71-98` (`_merge_table`), `table_generator.py:201-203` (log text)
- Trigger: An external entry whose fields are in a different order, omit `(options ...)` or `(descr ...)`, contain extra whitespace or line breaks between tokens, include an escaped quote in `descr`, or use a `type` other than `KiCad` (for example `Legacy`). KiCad itself writes these files with its own formatting, so a table saved by KiCad is not guaranteed to match.
- Workaround: Keep a copy of the table before generating; backups are created automatically (see Fragile Areas for backup behavior).
- Severity: High. The tool advertises "external entries will be preserved", which is not guaranteed.
- Fix approach: Parse the s-expression properly (small tokenizer for balanced parentheses and quoted strings), keep unknown entries verbatim by span, and emit a warning for any top-level child that cannot be classified.

**Unhandled file-system errors during Generate:**
- Symptoms: If `sym-lib-table` or `fp-lib-table` is locked (KiCad open with the file), read-only, or the destination disappears, `write_tables` raises an uncaught `OSError` inside a Qt slot. The partially executed handler leaves the UI state inconsistent (no history update, no path sync) and the error appears as an unhandled exception rather than a log entry.
- Files: `kicad_lib_manager/main_window.py:358-405` (`_on_generate`), `kicad_lib_manager/table_generator.py:170-209` (`write_tables`), `table_generator.py:150-167` (`backup_existing` uses `shutil.copy2`)
- Trigger: Generate while KiCad holds the destination file, or with a read-only destination.
- Workaround: None in the UI.
- Fix approach: Wrap `write_tables` and `sync_kicad_path_vars` in try/except `OSError` in `_on_generate` and log an error per file.

**Rescan or path change while a scan is running:**
- Symptoms: `_on_rescan` and `_on_set_kicad_path` call `_start_scan()` without checking whether `self._worker` is still running. `_start_scan` overwrites `self._worker` with a new `ScanWorker`. The previous `QThread` object may be garbage-collected while still running, which Qt reports as "QThread: Destroyed while thread is still running" and can abort the process.
- Files: `kicad_lib_manager/main_window.py:276-280` (`_start_scan`), `main_window.py:407-410` (`_on_rescan`), `main_window.py:421-435` (`_on_set_kicad_path`), `main_window.py:308-309` and `355-356` (wait/None handling)
- Trigger: Press Ctrl+Shift+R twice quickly, or change the KiCad path during a scan.
- Workaround: Wait for the progress dialog to close.
- Fix approach: Guard `_start_scan` with `if self._worker and self._worker.isRunning(): return` (or disable the actions while scanning), and keep the thread reference until `finished`.

**Rescan resets the user's in-progress selection:**
- Symptoms: `_apply_existing_selection` only sets `selected = True` for libraries present in the destination tables. Any library the user checked but has not generated yet is lost after Rescan. Libraries the user unchecked that are still in the table remain checked again.
- Files: `kicad_lib_manager/main_window.py:311-350`, `main_window.py:407-410`
- Trigger: Check libraries, then press Rescan or Ctrl+Shift+R before generating.
- Workaround: Generate before rescanning.
- Fix approach: Re-apply the previous `selected` set by `(source, nickname)` after the scan rather than reloading from the tables.

**Nickname collisions across sources:**
- Symptoms: Two libraries with the same `.kicad_sym` or `.pretty` stem in different sources (for example `Custom/` and `WurthElektronik/`) collide. `_fp_items` is keyed only by nickname, so the second item overwrites the first and one footprint library can no longer be synchronized. Pre-selection and cross-reference also match by nickname only.
- Files: `kicad_lib_manager/widgets/library_table.py:58`, `library_table.py:134`, `library_table.py:186-190`; `kicad_lib_manager/main_window.py:335-343`; `kicad_lib_manager/library_scanner.py:210-217`
- Trigger: Same library stem in two source folders. Not observed in the current tree, but nothing prevents it.
- Workaround: Rename one library.
- Fix approach: Key on `(source, nickname)` or on `rel_path` everywhere; warn at scan time on duplicate nicknames. Note that the generated `(name ...)` in the table must also be unique, so the collision must be reported, not just avoided in the UI.

**Restore overwrites current tables without confirmation:**
- Symptoms: Choosing a backup and pressing Restore immediately copies the backup over `sym-lib-table` / `fp-lib-table`. A safety backup of the current file is created, but the user gets no confirmation prompt and no indication of where the safety backup went beyond a log line.
- Files: `kicad_lib_manager/main_window.py:412-419`, `kicad_lib_manager/widgets/backup_dialog.py:86-91`, `kicad_lib_manager/table_generator.py:262-274`
- Trigger: Accidental Ctrl+R followed by Enter.
- Workaround: Undo by restoring the newest backup, which the tool created.
- Fix approach: Add a `QMessageBox.question` confirmation that names the backup number and the target folder.

## Security Considerations

**Writes to KiCad's global configuration file are not atomic and race with KiCad:**
- Risk: `sync_kicad_path_vars` reads `kicad_common.json`, mutates it in memory, and writes the whole file back with `write_text`. A crash or power loss mid-write truncates KiCad's main settings file. If KiCad is running it may also overwrite the change on exit, so the environment variables are lost without notice. The write is not preceded by a backup.
- Files: `kicad_lib_manager/library_scanner.py:38-87`, specifically `library_scanner.py:78-80`
- Current mitigation: JSON parse failure is caught and reported (`library_scanner.py:48-51`); `OSError` on write is caught (`library_scanner.py:84-85`).
- Recommendations: Back up `kicad_common.json` before writing (same numbering scheme as the tables), write to a temp file in the same directory and `os.replace` it, and warn the user to close KiCad before writing. Do not rewrite unrelated keys; only set `environment.vars`.

**Non-atomic writes of the library tables:**
- Risk: `write_tables` writes `sym-lib-table` and `fp-lib-table` directly with `write_text` (`table_generator.py:198`). A crash mid-write leaves a truncated table, and the backup is the only recovery path.
- Files: `kicad_lib_manager/table_generator.py:191-198`
- Current mitigation: Backup copy is created before each write (`table_generator.py:195-196`).
- Recommendations: Write to `<name>.tmp` and `os.replace`.

**Unescaped values in generated s-expressions:**
- Risk: `_format_entry` interpolates `name`, `uri`, `options`, and `descr` into quoted strings without escaping (`table_generator.py:50-56`). A value containing `"` or a backslash produces an invalid table that KiCad rejects. Current inputs come from file stems and fixed paths, so the practical risk is low, but the external `descr` values read back from existing tables are re-emitted verbatim (`table_generator.py:89`) and are trusted.
- Files: `kicad_lib_manager/table_generator.py:50-56`, `table_generator.py:88-90`
- Current mitigation: None.
- Recommendations: Escape `\` and `"` in all generated fields.

**Writing into any user-selected folder:**
- Risk: The destination is any folder the user picks or types into an editable combo box (`main_window.py:159-163`). The restore dialog also accepts any folder and copies `*_backup_N` files from it into the destination (`backup_dialog.py:66-68`, `table_generator.py:262-274`). There is no check that the folder is a KiCad configuration directory.
- Files: `kicad_lib_manager/main_window.py:193-202`, `kicad_lib_manager/table_generator.py:262-274`
- Current mitigation: Destination must exist (`main_window.py:364-366`).
- Recommendations: Warn when the destination has no `kicad_pro`/`kicad_common.json` sibling or is not one of the known KiCad config paths; require the backup file name to match the base file name exactly (already enforced by pattern, but the folder is not validated).

**No secrets handling concerns found:**
- Risk: None identified. The package reads no credentials and no `.env` files; `settings.py` stores only window geometry, the KiCad footprint path, and destination history via `QSettings`.
- Files: `kicad_lib_manager/settings.py`

## Performance Bottlenecks

**Full-text reads of every symbol and footprint file on each scan:**
- Problem: `_parse_footprint_refs` reads each `.kicad_sym` fully (`library_scanner.py:191`), and `check_3d_model_paths` reads each `.kicad_mod` fully (`library_scanner.py:237`). Both run on every Rescan across the whole repository, including the large WurthElektronik submodule.
- Files: `kicad_lib_manager/library_scanner.py:187-204`, `library_scanner.py:230-250`, `library_scanner.py:253-275`
- Cause: No caching; full-file regex over text for each file; `_collect_files` uses `rglob` and filters afterwards (`library_scanner.py:143-147`).
- Improvement path: Cache results keyed by path and `mtime`; reuse the `.kicad_sym` content for footprint-ref parsing rather than re-reading; skip skip-dirs during traversal instead of after (`os.walk` with pruning).

**Synchronous footprint re-sync on every symbol toggle:**
- Problem: Each `itemChanged` on a symbol calls `_sync_footprint_selection`, which rebuilds the needed set by iterating every symbol and every footprint ref, then iterates all footprint items. Group toggles fire one signal per child, so toggling a group with many children runs the full sync many times.
- Files: `kicad_lib_manager/widgets/library_table.py:145-169`, `library_table.py:171-192`, `library_table.py:207-237`
- Cause: No batching; `_updating` guard is not set during group-to-child propagation (`library_table.py:155-159`).
- Improvement path: Compute the needed set once per change, and wrap group propagation in `blockSignals` followed by one sync.

## Fragile Areas

**Regex-based parsing of KiCad s-expressions:**
- Files: `kicad_lib_manager/table_generator.py:11-17`, `kicad_lib_manager/library_scanner.py:10-11`
- Why fragile: `FOOTPRINT_RE` and `MODEL_RE` match the first occurrence of a pattern in raw text and do not understand nesting. A `(property "Footprint" ...)` inside a nested sub-symbol or a multi-line value is handled incorrectly, and the `_LIB_ENTRY_RE` requirement of exact token adjacency is the root cause of the dropped-entry bug above.
- Safe modification: Add fixture files covering each KiCad table variant before changing the regexes; prefer a small s-expression tokenizer.
- Test coverage: None.

**Footprint checkboxes are overwritten by symbol state:**
- Files: `kicad_lib_manager/widgets/library_table.py:171-192`, `library_table.py:194-199`
- Why fragile: Footprint items are user-checkable and `_on_fp_item_changed` records the change, but any later symbol toggle recomputes every footprint from the symbol set and silently discards manual footprint selections. Users can select a footprint, see it check, then lose it.
- Safe modification: Either make footprint checkboxes read-only (`setFlags` without `ItemIsUserCheckable`) or store a manual override set and merge it in `_sync_footprint_selection`.
- Test coverage: None.

**Log level inferred from message text:**
- Files: `kicad_lib_manager/main_window.py:384-389`, `main_window.py:393-397`
- Why fragile: Severity is chosen by substring matching (`"removed" in msg`, `"Failed" in msg`, `"not found" in msg`). Any library or path containing those words is misclassified, and wording changes in `table_generator.py` or `library_scanner.py` silently change colors.
- Safe modification: Return structured results (level, message) from `write_tables` and `sync_kicad_path_vars`.
- Test coverage: None.

**Lexical version sorting of KiCad installation directories:**
- Files: `kicad_lib_manager/library_scanner.py:31-35` (config dir), `library_scanner.py:103-111` (footprint dir)
- Why fragile: Directory names are sorted as strings with `reverse=True`. `"9.0"` sorts after `"10.0"`, so with KiCad 9 and 10 installed side by side (or any future 10.x), the wrong version is selected and the wrong `kicad_common.json` is modified.
- Safe modification: Sort by parsed `tuple(int(p) for p in name.split("."))` and ignore non-numeric names.
- Test coverage: None.

**Backup numbering and retention:**
- Files: `kicad_lib_manager/table_generator.py:150-167` (`backup_existing`), `table_generator.py:212-242` (listing)
- Why fragile: Every Generate creates two new backup files (`*_backup_N`) and nothing prunes them. Numbering is `max + 1` over the directory listing, so deleting the highest-numbered backup causes the next backup to reuse its number, which can confuse a user who is comparing backups by number. Backups also are not paired with the generation that created them, so the paired restore can pick sym and fp from different runs when one side was missing.
- Safe modification: Record a timestamp or generation ID in the backup name; add a retention limit.
- Test coverage: None.

**Scan results are shared by mutable reference:**
- Files: `kicad_lib_manager/widgets/library_table.py:69-70`, `kicad_lib_manager/main_window.py:288-298`
- Why fragile: `LibraryTableWidget` stores the same `SymbolLibrary` and `FootprintLibrary` objects as `MainWindow._scan_result`, and `selected` is mutated from the UI. `_on_generate` reads that mutated state. Any future code that rescans or reads `ScanResult` in another thread would see races.
- Safe modification: Keep selection state in a separate model and pass copies to `write_tables`.
- Test coverage: None.

## Scaling Limits

**Scan scope is the whole repository tree:**
- Current capacity: Scans every `.kicad_sym`, `.pretty`, and `.kicad_mod` under the repo root, including submodules and any untracked folders such as `downloaded_examples/`.
- Limit: Scan time and log noise grow with every added library. Untracked, unrelated libraries are picked up automatically, which can add libraries to the generated tables without the user intending it.
- Scaling path: Restrict discovery to submodule paths listed in `.gitmodules` plus explicitly tracked folders, or add an include list in settings.

## Dependencies at Risk

**PySide6 (unpinned):**
- Risk: No version constraint anywhere in the repo. Qt 6 API details used here (for example `QThread` signal behavior, `Qt.CheckState` enum access, `StandardPixmap` lookup through `self.style()`) can change between PySide6 releases.
- Impact: Silent behavior change or startup failure after a `pip install -U`.
- Migration plan: Pin a tested PySide6 minor version in `requirements.txt`.

## Missing Critical Features

**No dry-run or diff preview before writing tables:**
- Problem: Generate writes immediately after the log summary. The user cannot see which entries will be added, removed, or preserved before the file changes.
- Blocks: Safe review of large selection changes; confidence in the merge logic described above.

**No validation that generated tables load in KiCad:**
- Problem: The tool never parses its own output or checks it against the format KiCad expects.
- Blocks: Early detection of the escaping and merge issues in Security Considerations.

## Test Coverage Gaps

**Entire package is untested:**
- What's not tested: All of `kicad_lib_manager/`, `generate_lib_tables.py`, and `kicad_lib_manager.py`. No `tests/` directory exists.
- Files: `kicad_lib_manager/table_generator.py`, `kicad_lib_manager/library_scanner.py`, `kicad_lib_manager/widgets/library_table.py`
- Risk: Merge logic (`_merge_table`, `_LIB_ENTRY_RE`), backup numbering, version selection, and footprint sync can regress without notice.
- Priority: High

**Highest-value first tests:**
- `parse_lib_table` / `_merge_table` against a KiCad-generated table with varied formatting (reordered fields, missing `descr`, multi-line entries). Expected: no external entry is lost.
- `find_kicad_config_dir` and `find_kicad_footprint_dir` with directories `9.0` and `10.0` present. Expected: `10.0` selected.
- `backup_existing` / `list_backup_pairs` numbering across gaps.
- `_sync_footprint_selection` with two sources sharing a nickname.
- Priority: High for the first two, Medium for the others.

**GUI behavior is untested:**
- What's not tested: Rescan during a running scan, selection persistence across rescan, restore flow.
- Files: `kicad_lib_manager/main_window.py`, `kicad_lib_manager/widgets/library_table.py`, `kicad_lib_manager/widgets/backup_dialog.py`
- Risk: The threading and selection bugs above are only reproducible manually.
- Priority: Medium. Pytest-qt on the widget classes would be sufficient.

**Help content not verified:**
- What's not tested: `kicad_lib_manager/widgets/help_dialog.py` (360 lines of static help text) was not checked against current shortcuts or behavior during this audit.
- Risk: Help text may describe behavior that has changed.
- Priority: Low.

---

*Concerns audit: 2026-10-18*
