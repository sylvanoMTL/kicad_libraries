---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 04
subsystem: main-window
tags: [pyside6, destination, working-directory, pytest, backup-dialog]

requires:
  - phase: 12-import-flow-fixes-and-case-sensitive-re-test
    provides: "12-03 post-install table step (_finish_post_install, _tables_outcome)"
provides:
  - "MainWindow._dest_path(): blank or whitespace Destination means no destination"
  - "Post-install step, Generate, startup/Rescan/Browse/typing never read or write tables in the working directory when the Destination is blank"
  - "BackupDialog._folder(): a blank backup folder lists and restores nothing"
affects: [12-verify, case-sensitive re-test]

actuals:
  tokens: 12000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "One helper turns a folder box into Path | None; every caller stops on None before any table read or write"

key-files:
  created:
    - tests/test_backup_dialog.py
  modified:
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/widgets/backup_dialog.py
    - tests/test_main_window.py
    - tests/test_main_window_import.py
    - .gitignore

key-decisions:
  - "Generate and the post-install step log the same plain warning (_NO_DEST_TEXT) at warning level; the post-install tables row is amber (WARNING) for new and existing libraries"
  - "A non-blank text naming a missing folder keeps today's ERROR; a typed relative path such as '.' is the user's explicit choice and is not refused"
  - "BackupDialog keeps its texts unchanged; a blank folder just shows the existing '(No backups found)' item"

patterns-established:
  - "Tests for blank-folder behaviour run with monkeypatch.chdir to an empty tmp folder and assert it stays empty"

requirements-completed: [REV-02]

coverage:
  - id: D1
    description: "Blank or whitespace Destination after an install writes no table, logs the no-destination warning and shows an amber tables row, new and existing library"
    requirement: REV-02
    verification:
      - kind: integration
        ref: "tests/test_main_window_import.py#test_tables_blank_destination_writes_nothing"
        status: pass
    human_judgment: false
  - id: D2
    description: "Generate Tables, startup pre-selection, Rescan, Browse and typing never touch the working directory when the Destination is blank; no blank history entry"
    requirement: REV-02
    verification:
      - kind: integration
        ref: "tests/test_main_window.py#test_generate_blank_destination_writes_nothing"
        status: pass
      - kind: integration
        ref: "tests/test_main_window.py#test_blank_destination_never_reads_the_working_directory"
        status: pass
    human_judgment: false
  - id: D3
    description: "Restore Backup dialog with a blank folder lists no backups from the working directory and cannot restore into it"
    requirement: REV-02
    verification:
      - kind: unit
        ref: "tests/test_backup_dialog.py#test_blank_folder_lists_nothing_from_the_working_directory"
        status: pass
      - kind: unit
        ref: "tests/test_backup_dialog.py#test_blank_folder_cannot_restore"
        status: pass
      - kind: unit
        ref: "tests/test_backup_dialog.py#test_folder_with_backups_lists_them_and_restores"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-11-01
status: complete
commits: 3
plan_head_before: eefa94b248c426f300decc590825a0c67220a516
plan_head_after: 973eabab16507c23a3a5c2cffa9998a7f57de3be
---

# Phase 12 Plan 04: Blank Destination guard (REV-02) Summary

**A blank or whitespace Destination box now means "no destination": `MainWindow._dest_path()` returns None, every caller stops before reading or writing a table, and the Restore Backup dialog treats a blank folder the same way, so nothing lands in the process working directory.**

## Performance

- **Duration:** about 20 min
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files modified:** 6 (1 created)

## Accomplishments

- `_NO_DEST_TEXT` and `MainWindow._dest_path()` added; `_log_existing_tables` accepts `Path | None`.
- `_finish_post_install` checks the helper first: logs the warning, sets an amber "tables" row, returns before any table write or path-variable question, for new and existing libraries.
- `_on_generate` logs the same warning and returns before `write_tables`, `_sync_path_vars()` and the history update. `__init__`, `_apply_existing_selection`, `_on_rescan`, `_on_dest_changed`, `_on_browse_dest` and `_on_restore_backup` all use the helper; no `Path(self._dest_combo.currentText())` is left.
- `BackupDialog._folder()` added; `_scan` and `_on_accept` use it and the constructor scans only for a non-blank default folder.

## Task Commits

1. **Task 1 (tracer): blank Destination after an install writes nothing** - `6348bc3` (feat)
2. **Task 2 RED: failing tests for Generate and the backup dialog** - `4271f89` (test)
3. **Task 2 GREEN: every other Destination use and the Restore Backup dialog** - `973eaba` (feat)

## TDD Gate Compliance (Task 2)

- RED: command `pytest tests/test_main_window.py tests/test_backup_dialog.py -k "blank or folder_with_backups"`, result `6 failed, 3 passed`. Failing on planned assertions: Generate wrote `sym-lib-table`/`fp-lib-table` into the working directory and did not log the warning; `_log_existing_tables`/`_on_dest_changed`/pre-selection read the working directory ("Existing sym-lib-table found at ."); `BackupDialog` listed `sym-lib-table_backup_1` from the working directory and set `selected_folder` to `.` or `'   '`. Semantic assessment: each target ran and failed on the behaviour the plan describes, not on setup or import errors. The `spaces` variants of the two read tests passed before the fix, because on Windows a path of only spaces does not exist; the `empty` variants carry the discriminating case, which is why both were parametrised over `""` and `"   "`. The `gsd_run check tdd-red-evidence` classifier was not run (pytest is not a supported report format).
- GREEN: `pytest tests/test_main_window.py tests/test_main_window_import.py tests/test_backup_dialog.py tests/test_table_add_entries.py` gave 128 passed; `tests/test_layering.py` 15 passed. REFACTOR: none needed.

## Verification

Targeted files only (the orchestrator runs the per-wave set after merge). No tests were skipped for missing submodules.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `.gitignore` pattern `*_backup_*` ignored `tests/test_backup_dialog.py`**
- **Found during:** Task 2 RED commit (`git add` refused the new test module the plan names)
- **Issue:** The "Backup files" pattern matches the file name `test_backup_dialog.py`.
- **Fix:** Added `!tests/test_backup_dialog.py` under the pattern, with a one-line comment.
- **Files modified:** `.gitignore`
- **Commit:** `4271f89`

**2. [Test shape] Blank text parametrised over `""` and spaces**
- The plan's backup and read tests name only `"   "`, which does not hit the working directory on Windows. The tests are parametrised over `""` and `"   "` so they fail without the fix. Added no production behaviour.

## Known Stubs

None.

## Threat Flags

None. Mitigations T-12-08 (blank text returns None; callers stop before any table access, tests run under `monkeypatch.chdir` to an empty folder) and T-12-09 (`BackupDialog._folder()`, `test_blank_folder_cannot_restore`) are implemented and tested.

## Self-Check: PASSED

- `tests/test_backup_dialog.py` exists and is tracked; commits 6348bc3, 4271f89 and 973eaba are on the branch.
