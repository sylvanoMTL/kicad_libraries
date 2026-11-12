---
phase: 02-hardening-existing-code
plan: 01
subsystem: table-generation
tags: [kicad, lib-table, sexpr, splice-merge, atomic-write, pyside6, pytest-qt]

requires:
  - phase: 01-foundation
    provides: sexpr (Edit/apply_edits/quote), fsutil (atomic_write_*, backup_file), kicad_files (load, lib_table_entries), models (Issue, Severity)
provides:
  - Lossless span-splice merge of sym-lib-table / fp-lib-table (external entries, (version 7), EOL and BOM kept byte-identical)
  - write_tables and restore_backup_pair returning list[Issue], never raising
  - kicad_files.LibTable accessor and lib_table()
  - table_generator.table_info / TableInfo lossless reader (replaces the regex reader)
  - LogPanel.log_issue with HTML-escaped log lines
  - MainWindow._log_issues, _log_existing_tables and rel_path-based startup pre-selection
  - Offscreen MainWindow test harness (isolated QSettings, injected scan and config sync)
affects: [02-02, 02-03, 02-04, 02-06, 02-08, 02-09, phase-5-post-install]

actuals:
  tokens: 21000
  tasks: 2
  commits: 3

plan_head_before: 17aa9b845d1ce5eee2f720b478d038b077daa927
plan_head_after: 302d349f429f97b684fffd16fcfe808a57cd3745

tech-stack:
  added: []
  patterns:
    - "Span-splice merge: classify children of the parsed table node, delete only managed spans, insert one generated block, apply with sexpr.apply_edits"
    - "Service functions return list[Issue]; MainWindow routes each through LogPanel.log_issue with issue.severity.value (no substring severity)"
    - "Per-table independent load -> merge -> backup -> atomic write; any failing step is one Issue and skips only that table"

key-files:
  created:
    - tests/test_main_window.py
    - tests/test_table_merge.py
    - tests/test_write_tables.py
  modified:
    - kicad_lib_manager/kicad_files.py
    - kicad_lib_manager/table_generator.py
    - kicad_lib_manager/widgets/log_panel.py
    - kicad_lib_manager/main_window.py

key-decisions:
  - "Managed-entry identity is the URI tail after ${KICAD_LIB_GITHUB}/ (rel_path), never the nickname"
  - "Destination combo reports tables on textActivated / editingFinished only; selection is never touched by a destination change"
  - "backup_existing and the shutil import stay in table_generator until plan 02-03 deletes them (tests/test_fsutil.py still imports backup_existing)"

patterns-established:
  - "MainWindow tests use make_window factory: QSettings redirected into tmp_path, REPO_ROOT / load_kicad_fp_dir / scan_all / sync_kicad_path_vars monkeypatched"
  - "Tables with an unparseable or unrecognised root are never backed up or written; the load Issue (with line/col) is logged"

requirements-completed: [HARD-01, HARD-02, HARD-06]

duration: 25min
completed: 2026-10-19
status: complete
---

# Phase 2 Plan 01: Lossless table generation and Issue-routed table/restore output Summary

**Generate now splices only the managed entries of sym-lib-table / fp-lib-table (hand-made entries, `(version 7)`, CRLF and BOM untouched), quotes every generated value, backs up and writes atomically, and logs table and restore results as coloured Issues instead of substring-classified strings.**

## Performance

- **Duration:** about 25 min
- **Started:** 2026-10-19T08:18:00Z (approx.)
- **Completed:** 2026-10-19T08:43:12Z
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files modified:** 7 (4 source, 3 new test files)

## Accomplishments
- Tracer: pressing Generate on a CRLF table with `(version 7)`, one external and one managed entry rewrites only the managed line; the backup holds the original bytes; the log shows one green success line per table.
- `_merge_table` places the generated block where the first whole-line managed entry was, or on its own line before the closing paren; all generated values go through `sexpr.quote` and round-trip (a name with `"` and `\` survives).
- An unreadable, unparseable or wrong-root existing table gets no backup and no write; its Issue (with line/col) is logged and the other table is still generated.
- `restore_backup_pair` returns Issues, takes a safety backup of the current table first, writes atomically and reports a read-only target as `fs.read_only` instead of raising.
- Regex reader (`parse_lib_table`, `count_table_entries`, `_LIB_ENTRY_RE`, `list_backups`, `restore_backup`) removed; `table_info` reads counts and managed rel_paths through `kicad_files`.
- Startup pre-selection matches by rel_path (a Wurth `Same` is no longer selected because Custom `Same` is in the table); destination changes only log and no longer fire per keystroke.

## Task Commits

1. **Task 1: End-to-end "Generate keeps the hand-made entry" (tracer)** - `d86f5cb` (feat)
2. **Task 2 RED: failing tests for restore Issues, table_info, rel_path pre-selection** - `0b68be6` (test)
3. **Task 2 GREEN: restore as Issues, table_info, rel_path pre-selection, one destination logger** - `302d349` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## TDD Gate Compliance

- RED: `0b68be6`. 10 tests failed for the intended reasons: `table_info`/`TableInfo` absent (AttributeError in the target tests), `restore_backup_pair` returned `str` instead of Issues (`'str' object has no attribute 'code'`) and raised `PermissionError` on a read-only table, Wurth `Same` was selected by nickname (`assert True is False`), and the destination logged on `setEditText`. Semantic assessment: every failure is on the planned behaviour, none is a collection, import or fixture fault. The pytest report format is not one the `tdd-red-evidence` classifier supports and `workflow.tdd_mode` was not set, so the classifier was not run.
- GREEN: `302d349`, all 21 new tests plus the full suite pass.
- REFACTOR: none needed.

## Files Created/Modified
- `kicad_lib_manager/kicad_files.py` - `LibTable`, `lib_table()`, `_lib_entry()`; `lib_table_entries` rebuilt on top of them
- `kicad_lib_manager/table_generator.py` - `_entry_text`, `_whole_line`, splice `_merge_table`, Issue-returning `write_tables` / `restore_backup_pair`, `TableInfo` / `table_info`
- `kicad_lib_manager/widgets/log_panel.py` - `html.escape` on messages, `log_issue`
- `kicad_lib_manager/main_window.py` - `_log_issues`, `_log_existing_tables`, rel_path pre-selection, new destination signals
- `tests/test_main_window.py` - isolated-QSettings `make_window` harness, tracer, pre-selection and destination tests
- `tests/test_table_merge.py` - merge over the five frozen fixtures, quote round-trip, `lib_table`, `table_info`
- `tests/test_write_tables.py` - `write_tables` and `restore_backup_pair` Issue behaviour

## Decisions Made
- Managed-entry identity is the URI tail (rel_path); the nickname is only the table name.
- `MergeResult.issues` slot exists and is forwarded by `write_tables`, but nothing populates it yet (unclassified-child warnings belong to a later plan).
- `backup_existing` and `import shutil` stay until plan 02-03 removes them, as the plan instructs.

## Deviations from Plan

None - plan executed exactly as written. (Environment note, not a deviation: the plan's `./env/Scripts/python.exe` does not exist in this worktree; the main checkout's venv interpreter was used by absolute path as the dispatch instructions say.)

## Issues Encountered
- The shell guard refuses command substitution around `git`, so the plan-ledger file was written with a literal path; `commits: 3` was measured with `git rev-list --count` from that base.
- Full-suite count in this worktree is 340 passed, 7 skipped (the 353 baseline includes tests that need the uncloned submodules).

## Known Stubs

None.

## Threat Flags

None - no new network, auth or file-access surface beyond the plan's threat model (T-02-01..T-02-04 mitigated: splice-only edits, `html.escape`, isolated test harness, refuse-without-backup on unparseable tables).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plans 02-02 (widget identity), 02-03 (external-clash handling, deletion of `backup_existing`), 02-04 (config sync Issues), 02-06 (startup-only pre-selection) and 02-08 (paired backup numbers) can build on `log_issue`, `_log_issues`, `table_info` and the `make_window` harness.
- Known follow-up from the plan: `write_tables` still numbers sym and fp backups independently (shared number is plan 02-08).

## Self-Check: PASSED

- All seven created/modified files exist on disk.
- Commits `d86f5cb`, `0b68be6` and `302d349` are in `git log` on this branch.
- Full suite: 340 passed, 7 skipped (skips are submodule-dependent tests).

---
*Phase: 02-hardening-existing-code*
*Completed: 2026-10-19*
