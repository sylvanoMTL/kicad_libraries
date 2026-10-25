---
phase: 02-hardening-existing-code
plan: 03
subsystem: table-generation
tags: [kicad, lib-table, s-expression, splice-merge, atomic-write, backup]

requires:
  - phase: 02-hardening-existing-code
    provides: "02-01 splice merge (_merge_table, _whole_line, _entry_text) and Issue routing; 02-08 fsutil.backup_file(number=) and fs.bad_encoding guard"
provides:
  - "Classified table merge: every non-managed child kept byte-identical, unusual children warned (D-07), external clashes (D-03), stale vs deselected managed entries (D-08), dropped managed flags, duplicate selected nicknames refused"
  - "Token-kind guard (WR-01) and value-less field routing (IN-04) in kicad_files"
  - "Independent per-table writes with one shared backup number per Generate and per Restore, and table.unchanged detection"
affects: [02-04, 02-05, 02-06, 02-07, 02-09, phase-03-importer]

actuals:
  tokens: 21000
  tasks: 2
  commits: 4

plan_head_before: 107cae314ac58f8cfb40e799a59bd19c024ee0cd
plan_head_after: 293e942513a9e0622c856a0018524723a5ffb3c3
commits: 4

tech-stack:
  added: []
  patterns:
    - "Classify-then-splice: every table child is classified (managed / external / unclassifiable) and only managed node spans are edited"
    - "One backup number N computed once per operation and passed to fsutil.backup_file(number=N) for every file touched"
    - "Failure matrix tests patch fsutil.os.replace and fsutil.atomic_write_bytes (zero-delay retries) instead of waiting for the real lock window"

key-files:
  created: []
  modified:
    - kicad_lib_manager/table_generator.py
    - kicad_lib_manager/kicad_files.py
    - tests/test_table_merge.py
    - tests/test_kicad_files.py
    - tests/test_write_tables.py

key-decisions:
  - "D-06 applied literally for managed flags (OQ1/A5): regenerated managed entries lose (disabled)/(hidden)/unknown fields, made visible by a table.managed_flags_dropped WARNING"
  - "Preserved count (OQ2) = external entries + unclassifiable entries + warned non-version children; (version ...) is never counted"
  - "A managed entry is 'stale' when its URI tail matches no scanned library rel_path; only deselected-but-existing libraries go to result.removed (table.removed INFO)"
  - "Issues from the merge (warnings) are also reported on a table.unchanged run, so unusual children stay visible"
  - "Duplicate-nickname check runs before anything else, including for a fresh or missing table file"

patterns-established:
  - "Merge returns MergeResult | Issue; an Issue means refuse (no backup, no write) and the other table still proceeds"

requirements-completed: [HARD-01, HARD-02, HARD-06]

coverage:
  - id: D1
    description: "Non-managed lib-table children (external entries, unknown lists, bare atoms, version, EOL) stay byte-identical; unusual ones warn with line number and are counted in preserved"
    requirement: HARD-01
    verification:
      - kind: unit
        ref: "tests/test_table_merge.py#test_unclassifiable_children_are_kept_byte_identical_and_each_warned"
        status: pass
      - kind: unit
        ref: "tests/test_table_merge.py#test_version_child_is_not_warned_about_and_not_counted"
        status: pass
    human_judgment: false
  - id: D2
    description: "External nickname clash, stale managed entry, deselected entry, dropped managed flags and duplicate selected nicknames are each reported with their own Issue code"
    requirement: HARD-01
    verification:
      - kind: unit
        ref: "tests/test_table_merge.py#test_selected_nickname_clashing_with_an_external_entry_is_not_written"
        status: pass
      - kind: unit
        ref: "tests/test_table_merge.py#test_stale_managed_entry_warns_and_deselected_one_is_listed_as_removed"
        status: pass
      - kind: unit
        ref: "tests/test_table_merge.py#test_regenerated_managed_entries_that_carried_flags_warn_naming_them"
        status: pass
      - kind: unit
        ref: "tests/test_table_merge.py#test_two_selected_libraries_with_one_nickname_are_refused_naming_both_paths"
        status: pass
    human_judgment: false
  - id: D3
    description: "Generated values containing a quote or backslash round-trip, external escapes are never re-emitted"
    requirement: HARD-06
    verification:
      - kind: unit
        ref: "tests/test_table_merge.py#test_generated_values_with_quote_and_backslash_round_trip_and_external_bytes_stay"
        status: pass
    human_judgment: false
  - id: D4
    description: "Read-only, locked, backup-failure and interrupted-replace writes each give exactly one Issue for that table while the other table is still written"
    requirement: HARD-02
    verification:
      - kind: unit
        ref: "tests/test_write_tables.py#test_read_only_sym_table_gives_one_error_and_fp_table_is_still_written"
        status: pass
      - kind: unit
        ref: "tests/test_write_tables.py#test_locked_fp_table_gives_one_error_and_sym_table_is_still_written"
        status: pass
      - kind: unit
        ref: "tests/test_write_tables.py#test_backup_failure_blocks_only_that_table"
        status: pass
      - kind: unit
        ref: "tests/test_write_tables.py#test_interrupted_replace_keeps_the_table_and_the_backup_made_before_it"
        status: pass
    human_judgment: false
  - id: D5
    description: "Both tables of one Generate and both safety copies of one Restore share one backup number so list_backup_pairs pairs them; unchanged tables are not backed up or rewritten"
    requirement: HARD-02
    verification:
      - kind: unit
        ref: "tests/test_write_tables.py#test_both_tables_of_one_generate_share_the_next_backup_number"
        status: pass
      - kind: unit
        ref: "tests/test_write_tables.py#test_restore_makes_both_safety_copies_on_one_shared_number"
        status: pass
      - kind: unit
        ref: "tests/test_write_tables.py#test_unchanged_table_is_neither_backed_up_nor_rewritten"
        status: pass
    human_judgment: false
  - id: D6
    description: "Two app instances generating into the same destination at once each leave a complete table (atomic same-directory replace, last writer wins)"
    requirement: HARD-02
    verification: []
    human_judgment: true
    rationale: "Declared as a backstop truth in the plan: relies on fsutil's atomic replace (covered by 02-08 tests); a real two-process race is not asserted here"

duration: 7min
completed: 2026-10-19
status: complete
---

# Phase 2 Plan 03: Hardened Lib-Table Merge and Independent Writes Summary

**Lib-table regeneration now classifies every child (keeping anything unusual byte-identical with a warning), reports clashes, stale and dropped-flag entries, refuses duplicate nicknames, and writes the two tables independently under one shared backup number.**

## Performance

- **Duration:** 7 min
- **Started:** 2026-10-19T08:46:53Z
- **Completed:** 2026-10-19T08:54:00Z
- **Tasks:** 2 (TDD: RED then GREEN each)
- **Files modified:** 5

## Accomplishments
- `_merge_table` classifies each child as managed, external or unclassifiable. Unclassifiable entries and unknown children are kept verbatim with one `table.unclassified` WARNING giving their line; `(version ...)` is neither warned nor counted.
- `table.external_clash`, `table.stale_managed`, `table.managed_flags_dropped` and `table.duplicate_nickname` added; deselected-but-existing managed entries keep the single `table.removed` INFO.
- `kicad_files`: `_is_token` guard for `find_symbols`/`find_property` (WR-01) and value-less or non-token known fields now land in `extras`, never `flags` (IN-04).
- `write_tables` computes one backup number from both tables, skips unchanged tables (`table.unchanged`), and keeps every failure to one Issue for that file; `restore_backup_pair` uses the same shared number for both safety copies.
- `backup_existing` and the `shutil` import deleted; all writes go through `fsutil`.

## Task Commits

1. **Task 1: Classify every table child (D-03, D-06..D-10, WR-01, IN-04)**
   - RED `4e7d96b` (test) - 11 new assertions failing on the planned behaviour
   - GREEN `d38e20c` (feat)
2. **Task 2: Independent per-table writes with one shared backup number (HARD-02)**
   - RED `91afe45` (test) - 5 failing (shared number x3, unchanged, leftover `backup_existing`)
   - GREEN `293e942` (feat)

**Plan metadata:** committed separately (docs: complete plan).

## TDD Gate Compliance

Both tasks have a `test(02-03)` commit preceding the matching `feat(02-03)` commit. RED semantic assessment: every failing test failed on an assertion for the planned behaviour (missing warnings, unexpected extra removed names, `'' is None`, absent shared-number backups); no collection or import errors. Characterisation tests that already passed against the 02-01 mechanics (escaping round-trip, adjacency, ordering, failure matrix for read-only/locked/interrupted/backup failure, restore with a locked table) are kept as regression guards. The `gsd_run check tdd-red-evidence` classifier was not run (tdd_mode not enabled for this dispatch).

## Files Created/Modified
- `kicad_lib_manager/table_generator.py` - classification, D-03/D-07/D-08 handling, shared backup numbering, unchanged detection
- `kicad_lib_manager/kicad_files.py` - `_is_token`, token-guarded `find_symbols`/`find_property`, `_lib_entry` field routing
- `tests/test_table_merge.py` - 15 new classification, refusal, escaping, adjacency and ordering tests
- `tests/test_kicad_files.py` - 5 new token-guard and routing tests
- `tests/test_write_tables.py` - failure matrix, shared backup number, unchanged, restore failures

## Decisions Made
See `key-decisions` above. OQ1/A5 and OQ2 resolved as the plan stated; no change to the plan's approach.

## Deviations from Plan

None - plan executed exactly as written. Test fixes made while writing GREEN (my own test omitted a scanned library, so a stale warning appeared) were corrections to RED-phase test data, not behaviour changes.

## Issues Encountered
- Fixtures cannot be edited (frozen), so new table cases are bytes/str literals inside tests as the plan required.
- The Bash heredoc layer collapsed `\\` to `\` in test source; the affected test line was re-applied through the Edit tool.
- The plan-head ledger file under the shared git dir could not be written (tool refused the compound git command), so `plan_head_before` was taken from the dispatch base SHA, which equals the worktree HEAD at start.

## Known Stubs

None.

## Threat Flags

None - no new network, auth or trust-boundary surface; T-02-07..T-02-10 mitigations are implemented and tested.

## Verification Results

- `pytest -q`: 382 passed, 7 skipped (baseline in this worktree 351 passed, 7 skipped; submodule-dependent tests skip by design).
- `-k "unclassified or clash or stale or flags or refus or duplicate or escap or adjacen or empty or order"`: 13 passed.
- `-k "read_only or locked or backup or interrupt or shared or unchanged or restore"` on `tests/test_write_tables.py`: 13 passed; slowest test 0.15 s.
- `grep` acceptance checks for `_is_token`, the five new Issue codes, `_next_backup_number`, `table.unchanged` all present; `.write_text(`/`shutil.copy2` absent from `table_generator.py`; `backup_existing` and `shutil` no longer attributes of the module.
- No `*_backup_*` file left outside `tmp_path` (git status clean of backups).

## Next Phase Readiness
- Table generation is lossless and per-file safe; downstream plans can rely on `table.*` Issue codes and `MergeResult.issues`.
- Remaining Phase 2 plans are unaffected; the importer phase can reuse `_merge_table`/`write_tables` unchanged.

## Self-Check: PASSED

- Files modified exist: table_generator.py, kicad_files.py, test_table_merge.py, test_kicad_files.py, test_write_tables.py.
- Commits `4e7d96b`, `d38e20c`, `91afe45`, `293e942` are ancestors of HEAD.

---
*Phase: 02-hardening-existing-code*
*Completed: 2026-10-19*
