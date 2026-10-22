---
phase: 05-import-ui-and-post-install
plan: 04
subsystem: ui
tags: [kicad, lib-table, add-only, post-install, pyside6]

requires:
  - phase: 05-import-ui-and-post-install
    provides: "05-01 post-install rescan (_PostInstall, _apply_post_install_selection); 05-03 LibraryTableWidget.reveal"
  - phase: 04-install
    provides: "fsutil.backup_file / atomic_write_text, sexpr.apply_edits, kicad_files.lib_table"
provides:
  - "table_generator.add_library_entries: add-only insertion of one library's managed entries into both lib tables"
  - "MainWindow._finish_post_install: reveal, add-only tables plus path-variable sync for a new library, Generate hint for an existing one"
affects: [05-11, phase-06-commit]

plan_head_before: 42286cae6dd079828e37ea4a5ff9d6b9be6ab0c4
plan_head_after: ea3b0b02f4905174fa0f25a0ff52385192b60b6d

actuals:
  tokens: 30000
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Add-only table edit: one zero-width Edit before the closing paren, every other byte untouched"
    - "Post-install tail step runs on both scan success and scan error because its input is the plan, not the scan"

key-files:
  created:
    - tests/test_table_add_entries.py
  modified:
    - kicad_lib_manager/table_generator.py
    - kicad_lib_manager/main_window.py
    - tests/test_main_window_import.py

key-decisions:
  - "Insertion branch of _merge_table moved into _insert_before_close and shared by add_library_entries, so Generate and the import use one placement rule"
  - "A blank existing table is backed up and rewritten from the Generate template; a missing table is created without a backup"
  - "A table that fails to load while checking an existing library counts as not listed, so the Generate hint is shown after the load Issue"
  - "_finish_post_install owns clearing _pending_post_install (callers no longer do)"

patterns-established:
  - "Issue outcome per table (added / listed / skipped) rolled into one summary Issue or per-table lines"

requirements-completed: [POST-02, POST-01]

coverage:
  - id: D1
    description: "add_library_entries adds exactly one managed entry per table and keeps every other byte (CRLF and LF, external, flagged managed, unclassified items)"
    requirement: POST-02
    verification:
      - kind: unit
        ref: "tests/test_table_add_entries.py#test_add_entries_keeps_every_other_byte"
        status: pass
      - kind: unit
        ref: "tests/test_table_add_entries.py#test_add_entries_quotes_values"
        status: pass
    human_judgment: false
  - id: D2
    description: "Idempotent, shared backup number, missing tables created, external clash kept, missing destination refused, read-only table reported"
    requirement: POST-02
    verification:
      - kind: unit
        ref: "tests/test_table_add_entries.py#test_add_entries_idempotent"
        status: pass
      - kind: unit
        ref: "tests/test_table_add_entries.py#test_add_entries_summary_added"
        status: pass
      - kind: unit
        ref: "tests/test_table_add_entries.py#test_add_entries_creates_missing_tables"
        status: pass
      - kind: unit
        ref: "tests/test_table_add_entries.py#test_add_entries_external_clash"
        status: pass
      - kind: unit
        ref: "tests/test_table_add_entries.py#test_add_entries_missing_destination"
        status: pass
      - kind: unit
        ref: "tests/test_table_add_entries.py#test_add_entries_read_only_table"
        status: pass
    human_judgment: false
  - id: D3
    description: "After an install that created a library, only its entries are added to the destination tables (ungenerated selection not written) and the path variables are synced, even when the rescan fails"
    requirement: POST-02
    verification:
      - kind: unit
        ref: "tests/test_main_window_import.py#test_tables_new_library_add_only"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_tables_written_even_when_rescan_fails"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_tables_missing_destination_logs_error"
        status: pass
    human_judgment: false
  - id: D4
    description: "An existing library absent from the tables gets the Generate hint and nothing is written; the installed rows are revealed in both trees"
    requirement: POST-01
    verification:
      - kind: unit
        ref: "tests/test_main_window_import.py#test_tables_existing_library_not_in_tables_warns"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_tables_existing_library_listed_no_warning"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_post_install_reveal_current_rows"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-10-22
status: complete
---

# Phase 5 Plan 04: Add-only library tables after install Summary

**`add_library_entries` inserts one managed entry per lib table without touching any other byte, and `MainWindow._finish_post_install` uses it (plus the path-variable sync) for a newly created library, hints "Press Generate Tables" for an existing one that is unlisted, and reveals the installed rows in both trees.**

## Performance

- **Duration:** about 40 min
- **Completed:** 2026-10-22
- **Tasks:** 2 (both TDD), 4 commits (RED and GREEN each)
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- `table_generator.add_library_entries(dest_folder, nickname, sym_rel_path, fp_rel_path)`: refuses a missing destination (`table.dest_missing`), creates a missing table from the Generate template (no backup), skips a table that already lists the nickname, keeps an external clash with a WARNING, backs up existing tables under one shared number, and writes through `atomic_write_text` keeping the BOM. Summary Issues: `table.entries_added`, `table.already_listed`.
- `_insert_before_close(text, table_node, eol, block) -> Edit` extracted from `_merge_table` with identical behaviour (merge and write tests unchanged and green).
- `MainWindow._finish_post_install(result)`: runs after `populate` on a successful post-install scan and from `_on_scan_error` on a failed one; reveals the rows (success only), then either adds the new library's entries and runs `sync_kicad_path_vars(REPO_ROOT)`, or logs `import.not_in_tables` when an existing library is not listed in both tables. `write_tables` is still only called from `_on_generate`.

## TDD Gate Compliance

| Task | RED commit | GREEN commit |
|------|-----------|--------------|
| 1 | 788ae6f `test(05-04)` | 1e49cd9 `feat(05-04)` |
| 2 | 9cad69e `test(05-04)` | ea3b0b0 `feat(05-04)` |

RED evidence: Task 1, all 9 tests failed with `AttributeError: module 'kicad_lib_manager.table_generator' has no attribute 'add_library_entries'` (the planned "function is missing" RED). Task 2, 5 of the 6 new tests failed on their planned assertions (missing Generate hint, tables unchanged, nothing revealed, no destination error); `test_tables_existing_library_listed_no_warning` already passed in RED because it asserts the absence of the new behaviour (a guard against a false warning). Semantic assessment: valid, the targets ran and failed for the intended reason. The classifier (`check tdd-red-evidence`) was not run; pytest console output was inspected by hand.

## Task Commits

1. Task 1 RED: `788ae6f` test(05-04): add failing tests for add-only library table helper
2. Task 1 GREEN: `1e49cd9` feat(05-04): add-only library table helper add_library_entries
3. Task 2 RED: `9cad69e` test(05-04): add failing tests for post-install tables and reveal
4. Task 2 GREEN: `ea3b0b0` feat(05-04): reveal installed library and update tables after post-install rescan

## Files Created/Modified

- `kicad_lib_manager/table_generator.py` - `add_library_entries`, `_add_entry`, `_insert_before_close`
- `kicad_lib_manager/main_window.py` - `_finish_post_install`, wiring in `_on_scan_finished` and `_on_scan_error`
- `tests/test_table_add_entries.py` - 9 helper tests (byte preservation, idempotence, backups, missing tables, clash, destination, read-only, quoting)
- `tests/test_main_window_import.py` - 6 new tests; `scan_with` gained `lib` and `with_ffc`, `stub_plan` gained `library` and `new_library`, the fixture exposes `make.config_file`

## Decisions Made

See `key-decisions` above. One addition beyond the plan text: `test_add_entries_backup_number_continues_past_existing` pins the shared-number rule when older backups exist.

## Deviations from Plan

None - plan executed exactly as written. (The helper's extra private function `_add_entry` is an implementation split of the plan's single function, not a behaviour change.)

## Issues Encountered

- The harness refused compound `git` shell commands, so the plan-head ledger file (protocol 0c) was not written. `plan_head_before` is the known dispatch base `42286cae...` and the commit count was measured with `git rev-list --count` afterwards (4).

## Verification

- Plan verification set (`test_table_add_entries`, `test_table_merge`, `test_write_tables`, `test_main_window`, `test_main_window_import`, `test_layering`, `test_importer_layering`): 113 passed.
- Full suite in the worktree: 1292 passed, 77 skipped, 4 failed. The 4 failures are the known baseline set (`test_install_plan.py::test_version_real_cli_into_20241209`, `::test_library_real_cli_new_header`, `::test_noop_second_plan_after_normalised_apply`, `tests/test_kicad_cli.py::test_real_cli_upgrades_ul_symbol_deterministically`; the other baseline failures listed by the orchestrator are in tests that skip here). The 77 skips are the Custom and WurthElektronik submodules not being checked out, one symlink privilege skip and one UAT env skip; none are in this plan's files.
- `grep -n "write_tables(" kicad_lib_manager/main_window.py` shows only the call in `_on_generate`.
- `git status --porcelain` is clean; tests write only into tmp_path.

## Known Stubs

None.

## Threat Flags

None. T-05-11 to T-05-14 mitigations are in place and tested (add-only insertion, `_entry_text` quoting, reuse of `sync_kicad_path_vars`, missing destination refused).

## Next Phase Readiness

Plan 05-11 can build the Result-view status rows on top of `_finish_post_install`; it currently returns nothing and logs all outcomes as Issues.

## Self-Check: PASSED

- Files exist: `kicad_lib_manager/table_generator.py`, `kicad_lib_manager/main_window.py`, `tests/test_table_add_entries.py`, `tests/test_main_window_import.py`.
- Commits 788ae6f, 1e49cd9, 9cad69e, ea3b0b0 are ancestors of HEAD.
