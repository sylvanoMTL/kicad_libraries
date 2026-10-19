---
phase: 02-hardening-existing-code
reviewed: 2026-10-19T00:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - CLAUDE.md
  - README.md
  - kicad_lib_manager/fsutil.py
  - kicad_lib_manager/kicad_files.py
  - kicad_lib_manager/kicad_process.py
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/models.py
  - kicad_lib_manager/table_generator.py
  - kicad_lib_manager/widgets/library_table.py
  - kicad_lib_manager/widgets/log_panel.py
  - tests/test_edits.py
  - tests/test_fsutil.py
  - tests/test_kicad_config.py
  - tests/test_kicad_files.py
  - tests/test_kicad_process.py
  - tests/test_layering.py
  - tests/test_library_table_widget.py
  - tests/test_log_panel.py
  - tests/test_main_window.py
  - tests/test_scanner_issues.py
  - tests/test_scanner_skip_dirs.py
  - tests/test_table_merge.py
  - tests/test_write_tables.py
findings:
  critical: 0
  warning: 7
  info: 4
  total: 11
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-10-19
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Summary

The hardening work is solid. The atomic-write, backup, byte-preserving table-merge and KiCad-config paths are carefully built, and I could not find a data-corruption or security bug in them. The 553 existing tests pass (3 skipped because the Wurth submodule is not checked out). I also probed `_merge_table` with single-line tables, tables whose closing paren shares a line with an entry, empty tables, external clashes and mixed ownership. Each probe produced valid, minimal splices.

The remaining defects are at the edges between the GUI and the new services:

- An empty destination path silently becomes the current working directory.
- A missing submodule makes the merge delete that submodule's managed entries.
- A symbol library that cannot be read is reported as healthy.
- One log message mislabels what happened.
- The GUI thread blocks on subprocess and file work.

No security vulnerabilities were found. There is no shell use, `subprocess` gets an absolute executable and list arguments, log output is HTML-escaped, and temp files use exclusive create.

No structural findings (fallow) were provided for this review.

## Warnings

### WR-01: Empty destination text resolves to the current working directory

**File:** `kicad_lib_manager/main_window.py:517` (also `:81`, `:458`, `:552`, `:592`, `:596`)
**Issue:** `Path(self._dest_combo.currentText())` is used everywhere without checking for empty text. The combo is editable, so the user can clear it. `Path("")` is `Path(".")`, which exists, so `_on_generate` passes its `dest.exists()` guard and calls `write_tables(Path(""), ...)`. That writes `sym-lib-table`, `fp-lib-table` and their `_backup_N` files into whatever directory the process was launched from. It also stores `""` in the destination history via `add_dest_to_history`. `_apply_existing_selection` and `_log_existing_tables` likewise read tables from the CWD. I confirmed `Path("").exists()` is `True`. A path to a regular file is also accepted by `exists()` and only fails later inside `write_tables`.
**Fix:**
```python
def _dest_path(self) -> Path | None:
    text = self._dest_combo.currentText().strip()
    return Path(text) if text else None

# in _on_generate
dest = self._dest_path()
if dest is None or not dest.is_dir():
    self._log.log(f"Destination folder does not exist: {dest or '(empty)'}", "error")
    return
```
Use the same helper in `_apply_existing_selection`, `_log_existing_tables` and `_on_rescan`.

### WR-02: Unreadable symbol library is silently treated as having no footprint references

**File:** `kicad_lib_manager/library_scanner.py:340-343`
**Issue:** `_parse_footprint_refs` returns an empty list on `OSError` or `UnicodeDecodeError` and emits no `Issue`. A corrupt or non-UTF-8 `.kicad_sym` therefore shows as status "OK" in the tree, and its linked footprints are never selected. This is inconsistent with `check_3d_model_paths`, which reports `scan.unreadable` for the same failure on `.kicad_mod` files. It also bypasses the strict decoder (`fsutil.decode_source`) that the rest of the phase introduced. The footprint extraction is a regex over the raw text, while the sexpr parser and `find_property` exist for the same job.
**Fix:** Have `find_symbol_libs` read through `kicad_files.load()` or `fsutil.read_source()`. On an `Issue`, append a `scan.unreadable` WARNING and keep the library in the list, as `check_3d_model_paths` does. Plumb the issues out through `scan_all`.

### WR-03: A missing or uninitialised submodule makes Generate delete its managed entries

**File:** `kicad_lib_manager/table_generator.py:154-165`
**Issue:** Every managed entry whose repo-relative tail is not in the freshly scanned `rel_path` set is removed as "stale". If a submodule is not checked out (for example after a fresh clone, a failed `git submodule update`, or a branch switch), none of its libraries are scanned. Generate then strips all of its managed entries from both tables. A one-line warning per entry is logged and the backup keeps the old content, but the destructive default is easy to trigger. The "(the backup still has it)" message is the only safety net.
**Fix:** Before removing, check whether the entry's source directory (the first path segment of the tail) exists and has any scanned library. If the directory is absent or empty, keep the entry and warn instead of removing it. Alternatively, ask the user to confirm removals when more than N entries would go.

### WR-04: External-clash casualties are reported as "Removed (deselected)"

**File:** `kicad_lib_manager/table_generator.py:166-167`, `:289-293`
**Issue:** A managed entry whose library is currently selected but whose nickname clashes with an external entry is dropped without being regenerated. Its tail is in `scanned_paths` but not in `generated_paths`, so it lands in `removed`. The log then says "Removed from sym-lib-table (deselected): A2" for a library the user has selected. I reproduced it with a table holding an external `A` and a managed `A2` pointing at `Custom/A.kicad_sym`: `removed == ['A2']`, alongside the `table.external_clash` issue. The user sees two messages that do not describe the same event.
**Fix:** Track clash-dropped paths separately. For example, only append to `removed` when `tail not in {lib.rel_path for lib in selected}`. For clashed ones, extend the `table.external_clash` message with "and removed the previous managed entry '<name>'".

### WR-05: Restore dialog and `list_backup_pairs` crash on a destination that is a file or unreadable

**File:** `kicad_lib_manager/table_generator.py:306-307`, `kicad_lib_manager/widgets/backup_dialog.py:66-68`
**Issue:** Both guard with `exists()` only. If the destination text points at a file, `folder.iterdir()` raises `NotADirectoryError`. A permission problem raises `PermissionError`. The call comes from the dialog constructor (`_scan` when `default_folder` is non-empty) and from the button slot, so the exception goes uncaught through Qt. For an empty combo, `Path("")` makes the dialog scan the CWD (same root cause as WR-01).
**Fix:** Use `folder.is_dir()` and wrap `iterdir()` in `try/except OSError: return []`. Better, return an `Issue` the dialog can show.

### WR-06: Generate runs process listing, fsync and retry sleeps on the GUI thread

**File:** `kicad_lib_manager/main_window.py:540`, `kicad_lib_manager/library_scanner.py:210-227`, `kicad_lib_manager/kicad_process.py:25-32`
**Issue:** `_on_generate` calls `write_tables` and `sync_kicad_path_vars` synchronously. `kicad_running` shells out to `tasklist.exe` with a 5 s timeout. `atomic_write_bytes` can sleep up to about 1 s per file while retrying a locked target. `fsync` runs on every write. On a slow machine with antivirus, the window freezes for several seconds with no feedback. The project convention (CLAUDE.md, Architecture) is that long-running work goes in a `QThread`. A hang on `tasklist` during a table write delays the write itself.
**Fix:** Move the generate pipeline into a worker, or at least show a busy cursor (`QApplication.setOverrideCursor`) and disable the Generate controls for the duration. Keep `kicad_running` off the GUI thread.

### WR-07: Atomic replace discards symlinks and the original file's permissions

**File:** `kicad_lib_manager/fsutil.py:107-119`
**Issue:** The new content is written to a fresh temp file and `os.replace`d over `path`. If `kicad_common.json` or a lib table is a symlink (common with dotfile managers on the Linux and macOS branches the project says it keeps working), the link is replaced by a regular file and the real target is left stale. On POSIX the replacement also gets default mode and ownership instead of the original's. `copystat` is applied to backups but not to the written file.
**Fix:** Resolve the target first (`path = path.resolve()` when `path.is_symlink()`), create the temp file beside the real file, and on POSIX copy the mode with `shutil.copymode(path, tmp)` before the replace when the target exists.

## Info

### IN-01: Scan progress runs backwards between phases

**File:** `kicad_lib_manager/library_scanner.py:305`, `:326`, `:432`, `:478`
**Issue:** `find_footprint_libs`, `find_symbol_libs` and `check_3d_model_paths` each report `i / total` on their own 0-100 scale. After a "Cross-referencing..." step at 95, the 3D check starts again near 0. `ScanWorker.on_progress` converts that to a percentage, so the progress bar jumps back and forth during a scan. The bar is cosmetic, but it gives a wrong impression of progress.
**Fix:** Map each phase onto a slice of the range (for example 0-30, 30-60, 60-90), or report a phase label with an indeterminate bar.

### IN-02: Unused `pytest` imports

**File:** `tests/test_table_merge.py:5`, `tests/test_write_tables.py:7`
**Issue:** `import pytest` is never referenced in either file (confirmed with an AST scan).
**Fix:** Remove both imports.

### IN-03: CLAUDE.md repository structure omits the new foundation modules

**File:** `CLAUDE.md:8-18`
**Issue:** The structure list names only `main_window`, `library_scanner`, `table_generator`, `models` and the three widgets. It does not mention the modules added in this phase and enforced by `tests/test_layering.py`: `fsutil.py`, `sexpr.py`, `kicad_files.py` and `kicad_process.py`. It also still describes `table_generator.py` as owning backup/restore logic, which is now `fsutil.backup_file`. A future agent following CLAUDE.md will not know the layering rules or where atomic writes live.
**Fix:** Add one line per new module, plus a note on the downward-only import rule and the Qt-free requirement for the foundation layer.

### IN-04: Paired backup numbers can silently diverge if the shared number is already taken

**File:** `kicad_lib_manager/fsutil.py:192-199`, `kicad_lib_manager/table_generator.py:242`, `:272`
**Issue:** `write_tables` computes one `backup_number` and passes it for both tables so Restore treats them as a pair. `backup_file` bumps `number` independently on `FileExistsError`. If another writer takes `sym-lib-table_backup_N` between the number computation and the copy, the sym backup becomes N+1 while fp stays at N. Restore then offers two half-pairs. Only a concurrent writer can trigger this, so it is unlikely for a single-user tool. The returned path is already reported to the user.
**Fix:** Optional: have the caller use the returned `backup.name` number for the second table, or reserve both names before copying.

---

_Reviewed: 2026-10-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
