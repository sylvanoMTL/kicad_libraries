---
phase: quick-261027-gg7
plan: 01
subsystem: scanner / main window
tags: [scan-cache, startup, rescan-library, pyside6]
requires: [SCAN-01, SCAN-02]
provides:
  - kicad_lib_manager/scan_cache.py (Qt-free saved scan: fingerprint, encode/decode, load_fresh, save, library_entries, update_library)
  - settings.scan_cache_file(repo_root)
  - library_scanner.rescan_library / LibraryRescan, atomic_check.summary_line
  - "Rescan this library" right-click entry, LibraryRescanWorker
affects: [main_window startup scan, library tree context menu]
key-files:
  created:
    - kicad_lib_manager/scan_cache.py
    - tests/test_scan_cache.py
    - tests/test_rescan_library.py
  modified:
    - kicad_lib_manager/settings.py
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/library_scanner.py
    - kicad_lib_manager/atomic_check.py
    - kicad_lib_manager/widgets/library_table.py
    - tests/test_main_window.py
    - tests/test_library_table_widget.py
    - tests/test_layering.py
    - CLAUDE.md
decisions:
  - "Saved scan stored as <settings.ini folder>/scan_cache/<16 hex of sha256(normcase(resolved repo root))>.json, never in the repo"
  - "A library whose file was deleted or renamed, or that shares its nickname, falls back to a full scan (O-10)"
  - "update_library refreshes only the rescanned library's fingerprint keys, so any other change still forces a full scan at the next start"
status: complete
commits: 3
plan_head_before: 1133305697b291c9ac546f00d87afc44b827595d
plan_head_after: 92b4a4429767e7b72286e17335ca00080a2ff5ff
actuals:
  tokens: 60000
  tasks: 3
  commits: 3
metrics:
  completed: 2026-10-27
---

# Phase quick-261027-gg7 Plan 01: Reuse the last scan at startup Summary

The app now shows the last saved scan at startup when a cheap stat walk finds no changed library file, and a right-click "Rescan this library" re-reads one library off the GUI thread and merges it into the current scan and the saved scan.

## What was built

**Task 1 (tracer), commit 427a8e2.** `kicad_lib_manager/scan_cache.py` (stdlib only, registered in `tests/test_layering.py`):
- `fingerprint` is a stat walk (mtime_ns and size, no parsing).
- `encode_result` / `decode_result` use plain JSON with a strict decode and never save `selected`.
- `load_fresh` returns the saved result or one plain note per fallback case.
- `save` writes atomically through `fsutil` and turns any failure into one WARNING.
- `ScanWorker` takes `cache_file` and `reuse_cache`. At startup it logs "Showing the saved scan from <date time>: no library file changed since then. Use Rescan for a full scan." and skips `scan_all`. Every full scan saves a fresh result before `finished` is emitted.
- `MainWindow.__init__` starts with `reuse_cache=True`. Rescan, Set KiCad Footprint Path, the rescan after atomic fixes and the quiet post-install rescan stay full scans.

**Task 2, commit befd8e5.**
- `library_scanner.rescan_library` and `LibraryRescan`.
- `_check_model_files` is now shared with `check_3d_model_paths`.
- `atomic_check.summary_line`.
- `scan_cache.library_entries` and `update_library`; both were already written in Task 1, and their tests are in `tests/test_scan_cache.py`.
- A footprint library rescan also re-checks the Atomic_ symbol libraries linking to it.
- Tests prove the merged result equals a new full scan, both on the plain fixture and on a git-backed Custom.

**Task 3, commit 92b4a44.**
- `LibraryTableWidget._build_context_menu`, `library_rescan_requested` and `set_library_rescan_enabled`.
- `LibraryRescanWorker`, `_on_library_rescan_requested`, `_on_library_rescanned` and `_copy_selection` in `main_window.py`.
- CLAUDE.md GUI notes.

## Cache file location

`%APPDATA%/KiCadExtLibManager/scan_cache/<16 hex>.json` on Windows. It sits beside `settings.ini`, with one file per repository folder (a worktree gets its own). Never inside the repository or `Custom/`.

## Fingerprint contents

- mtime_ns and size of every `.kicad_sym` and `.kicad_mod` file.
- Every file under `Custom/3DModels/` and every `.gitignore` under `Custom/`.
- The list of `.pretty` folders.
- The Custom git HEAD (and the commit it names), read from the git files with no subprocess.
- The resolved KiCad footprint folder, its own mtime and the mtime of its sibling `3dmodels` folder.
- A sha256 over the app's own `.py` files, so cached atomic verdicts never outlive a rule change.
- The top-level `SKIP_DIRS` are skipped like the scanner does.

## O-10 fallback choice

A library whose file or folder was deleted or renamed since the last scan falls back to a full scan, because a rename also creates a new library that only a full scan can find. A library that shares its nickname with another library also falls back, because its log lines cannot be told apart by name. A footprint rescan whose per-file change line could be owned by two Custom footprint libraries falls back too.

## Deviations from Plan

None - plan executed as written. Small implementation choices:
- `scan_cache.save` keeps the `kicad_fp_dir` parameter the plan names, though the folder is already part of the fingerprint it receives.
- `LibraryRescan.issues` leaves out the "whole change check skipped" line, since it belongs to no library.

## Verification

- `tests/test_scan_cache.py`, `tests/test_rescan_library.py`, `tests/test_main_window.py`, `tests/test_main_window_import.py` (run, not edited), `tests/test_library_table_widget.py`, `tests/test_layering.py`, `tests/test_atomic_scan.py`, `tests/test_scanner_issues.py`, `tests/test_scan_changes.py`, `tests/test_atomic_check.py`: all pass.
- Full `-m "not wurth"` suite: 2682 passed, 30 skipped (submodule and downloaded sample dependent), 3 deselected.
- Scope: `git diff --name-only` over the three commits lists only plan files; none of the Phase 10 locked files.

## Known Stubs

None.

## Threat Flags

None. The new reads (git HEAD, ref and packed-refs text files under `Custom/.git`) are covered by T-gg7-05; the ref name must start with `refs/` and has no `..` part.

## Follow-ups

- Describe the saved scan and "Rescan this library" on the User Guide page (`kicad_lib_manager/widgets/help_dialog.py`) once Phase 10 has finished with that file.

## Human check (owner)

Setup (PowerShell, repo root):
1. `.\env\Scripts\python.exe kicad_lib_manager.py`, wait for the first full scan (progress dialog "Loading Libraries"), then close the app.

Checks:
1. Start the app again. The trees fill almost at once, and the log shows "Showing the saved scan from <date time>: no library file changed since then. Use Rescan for a full scan.". The same libraries are ticked as before.
2. In KiCad Symbol Editor, change one field of a symbol in a Custom library and save. Restart the app: the log shows "1 library file changed since the saved scan; scanning the whole repository." and the progress dialog runs.
3. Right-click a library name in the Symbols tree. The menu shows Expand All, Collapse All and Rescan this library. Click Rescan this library: within a few seconds the log shows "Rescanned symbol library <name>: ..." and no check box changed.
4. Right-click a Custom footprint library in the Footprints tree, then Rescan this library: the log shows "Rescanned footprint library <name>: ...".
5. Right-click the bold "Custom" source row: there is no Rescan this library entry.
6. Press Rescan: the full progress dialog runs, as before.

## Self-Check: PASSED

Created files exist (`scan_cache.py`, `test_scan_cache.py`, `test_rescan_library.py`); commits 427a8e2, befd8e5 and 92b4a44 are ancestors of HEAD.
