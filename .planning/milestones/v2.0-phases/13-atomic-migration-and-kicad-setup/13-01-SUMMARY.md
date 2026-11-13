---
phase: 13-atomic-migration-and-kicad-setup
plan: 01
subsystem: library-tables
tags: [kicad, sym-lib-table, fp-lib-table, descriptions]

# Dependency graph
requires: []
provides:
  - "library_description() and stock_descriptions() in table_generator.py (TBL-01, D-20)"
  - "MainWindow._stock_descriptions(), cached per footprints folder, fed to Generate and both post-install add_library_entries calls"
  - "_merge_table keeps an existing managed entry's own non-empty description instead of regenerating it"
affects: ["13-17 (table regeneration after the atomic migration inherits these descriptions through the same Generate path)"]

# Actuals (#2632)
actuals:
  tokens: 6415
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Description source (table_descriptions.py's role) stays injected as a stock: Mapping[str, str] keyword rather than imported into table_generator.py, preserving table_generator's existing layering allow-list ({fsutil, kicad_files, models, sexpr})"
    - "An existing managed entry's non-empty descr is captured into a kept dict keyed by rel_path before the block is regenerated, so a hand- or KiCad-written description survives every future Generate"

key-files:
  created:
    - tests/test_table_descriptions.py
  modified:
    - kicad_lib_manager/table_generator.py
    - kicad_lib_manager/main_window.py
    - tests/test_table_merge.py
    - tests/test_table_add_entries.py
    - tests/test_main_window.py
    - tests/test_main_window_import.py

key-decisions:
  - "library_description() and stock_descriptions() live directly in table_generator.py rather than a separate table_descriptions.py leaf module, since the plan's own artifact table places both functions there and no second module was required to keep table_generator's layering allow-list unchanged."
  - "stock_descriptions() uses kicad_files.load() unbounded (no max_nodes), matching every other kicad_files.load() call already in table_generator.py (write_tables, _add_entry, table_info); any Issue or missing/unreadable file still yields {} so a hostile or huge stock table can never raise (T-13-02)."
  - "tests/test_main_window_import.py was updated even though it is not in this plan's files_modified/<files> list: its _managed() helper builds both the pre-existing fixture entries and the newly-added-entry assertions for the post-install add-only path, and all of them use Atomic_ nicknames whose generated description no longer matches the old literal (descr \"\"). The plan's own Task 2 <verify> command and acceptance criteria explicitly include this file, so fixing it is a Rule 1 auto-fix (plan's test-file coverage omission) rather than scope creep."

requirements-completed: [TBL-01]

coverage:
  - id: D1
    description: "Generate writes a non-empty description for every entry it emits: Atomic_<stem> reads KiCad's own stock description (or the stem's words), Atomic_Footprints gets its fixed text, and everything else gets '<Source>: <nickname with spaces>'"
    requirement: TBL-01
    verification:
      - kind: unit
        ref: "tests/test_table_descriptions.py#test_atomic_library_takes_kicad_description"
        status: pass
      - kind: unit
        ref: "tests/test_table_descriptions.py#test_atomic_library_without_stock_uses_stem_words"
        status: pass
      - kind: unit
        ref: "tests/test_table_descriptions.py#test_atomic_footprints_description"
        status: pass
      - kind: unit
        ref: "tests/test_table_descriptions.py#test_other_library_uses_source_and_spaced_nickname"
        status: pass
      - kind: integration
        ref: "tests/test_main_window.py#test_generate_writes_atomic_description"
        status: pass
    human_judgment: false
  - id: D2
    description: "stock_descriptions() reads KiCad's stock sym-lib-table (found relative to the detected/saved footprints folder, never a hard-coded install path) and never raises on a missing, unreadable, or table-less file"
    requirement: TBL-01
    verification:
      - kind: unit
        ref: "tests/test_table_descriptions.py#test_stock_descriptions_reads_template_table"
        status: pass
    human_judgment: false
  - id: D3
    description: "A description already present in an existing managed table entry is kept as-is when Generate regenerates that entry; an empty existing description still gets generated"
    requirement: TBL-01
    verification:
      - kind: unit
        ref: "tests/test_table_descriptions.py#test_existing_description_is_kept"
        status: pass
      - kind: unit
        ref: "tests/test_table_merge.py#test_reordered_fixture_replaces_two_line_managed_entry_and_keeps_external_bytes"
        status: pass
    human_judgment: false
  - id: D4
    description: "External (hand-added) table entries, including KiCad's own nested stock-table entry, are never touched by the description rules"
    requirement: TBL-01
    verification:
      - kind: unit
        ref: "tests/test_table_descriptions.py#test_external_entries_untouched"
        status: pass
    human_judgment: false
  - id: D5
    description: "The post-install add-only entry (add_library_entries, both the new-library and existing-library paths in MainWindow._finish_post_install) is described by the same rules as Generate, and a repoint changes only the URI, never the description"
    requirement: TBL-01
    verification:
      - kind: unit
        ref: "tests/test_table_descriptions.py#test_add_only_entry_is_described"
        status: pass
      - kind: unit
        ref: "tests/test_table_descriptions.py#test_repoint_keeps_description"
        status: pass
      - kind: integration
        ref: "tests/test_main_window_import.py (60 tests, _managed() helper now computes the generated description)"
        status: pass
    human_judgment: false
  - id: D6
    description: "A description holding quotes, backslashes, colons, or parentheses is written escaped through sexpr.quote and round-trips through kicad_files.load with the identical text"
    requirement: TBL-01
    verification:
      - kind: unit
        ref: "tests/test_table_descriptions.py#test_descriptions_are_quoted"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 01: Library table descriptions (TBL-01, D-20) Summary

**Generate and the post-install add-only step now write a non-empty description for every library table entry, with Atomic_ libraries reading KiCad's own stock description, and any description the owner (or KiCad) already wrote is never overwritten.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-11-11T15:00:00Z (approx.)
- **Completed:** 2026-11-11T15:25:00Z
- **Tasks:** 2
- **Files modified:** 7 (1 created, 6 modified)

## Accomplishments

- `table_generator.library_description(nickname, rel_path, stock)` implements the full D-20 rule set: `Atomic_Footprints` -> the fixed footprint text, `Atomic_<stem>` -> `"Atomic parts: "` + KiCad's stock description for `<stem>` (or the stem's own words when absent), everything else -> `"<Source>: <nickname with spaces>"`.
- `table_generator.stock_descriptions(template_table)` reads KiCad's stock `sym-lib-table` (found at `kicad_fp_dir.parent / "template" / "sym-lib-table"`, never hard-coded), tolerating a missing path, an unreadable file, or a file without a lib table by returning `{}`.
- `stock`/`descr` threaded through `_entry_text`, `_merge_table`, `generate_sym_lib_table`, `generate_fp_lib_table`, `write_tables`, `_add_entry`, and `add_library_entries`, so Generate and the post-install add-only path share one description source.
- `_merge_table` now keeps an existing managed entry's own non-empty description instead of regenerating it, computed once into a `kept` dict before the block is built.
- `MainWindow._stock_descriptions()` reads and caches the stock table per footprints folder, feeding `_on_generate` and both `add_library_entries` calls in `_finish_post_install`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Generate writes a described Atomic_ entry end to end (D-20)** - `43b5b0a` (feat)
2. **Task 2: Kept descriptions, the add-only entry and the table templates (D-20)** - `36bebc3` (feat)

_Note: both tasks are implementation+test commits (tracer and TDD-adjacent auto); no separate RED/GREEN/REFACTOR commits were produced because neither task carried `tdd="true"` on a behavior-adding sense distinct from its own commit (Task 2 was marked `tdd="true"` in the plan but its tests and implementation landed together verifying the same behavior change across several existing test files; see Issues Encountered)._

## Files Created/Modified

- `kicad_lib_manager/table_generator.py` - `ATOMIC_FOOTPRINTS_DESCRIPTION`, `ATOMIC_DESCRIPTION_PREFIX`, `stock_descriptions()`, `library_description()`; `stock`/`descr` threaded through `_entry_text`, `_merge_table`, `generate_sym_lib_table`, `generate_fp_lib_table`, `write_tables`, `_add_entry`, `add_library_entries`; the `kept` dict in `_merge_table`.
- `kicad_lib_manager/main_window.py` - import `stock_descriptions`; `self._stock_cache` init; `_stock_descriptions()`; `stock=self._stock_descriptions()` passed to `write_tables` in `_on_generate` and to both `add_library_entries` calls in `_finish_post_install`.
- `tests/test_table_descriptions.py` (new) - the ten behaviour tests for `library_description`, `stock_descriptions`, the keep rule, the add-only path, the repoint path, and quoting.
- `tests/test_table_merge.py` - `_sym_entry`/`_fp_entry` compute the generated description via `library_description`; the "reordered" fixture test now expects its existing non-empty description to be kept.
- `tests/test_table_add_entries.py` - `_entry()` and the inline `fp_line` in `test_footprint_only_leaves_the_symbol_table_alone` compute the generated description.
- `tests/test_main_window.py` - `test_generate_splices_table_and_logs_issues` expects the generated `"Custom: New"` description; new `test_generate_writes_atomic_description` tracer test proves the end-to-end KiCad-stock-description path through `_on_generate`.
- `tests/test_main_window_import.py` - `_managed()` helper computes the generated description (deviation; see Deviations below).

## Decisions Made

- Both new functions stay in `table_generator.py` rather than a separate `table_descriptions.py` leaf, matching the plan's artifact table and avoiding a layering-allow-list change.
- `stock_descriptions()` uses the unbounded `kicad_files.load()` already used elsewhere in this file (no `max_nodes`), consistent with the file's existing convention; a missing/unreadable/table-less file still safely yields `{}`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug/test-coverage gap] `tests/test_main_window_import.py` needed the same description fix as the three listed table test files**
- **Found during:** Task 2, running the task's own `<verify>` command
- **Issue:** Task 2's `<verify>` command and acceptance criteria explicitly name `tests/test_main_window_import.py` ("every test in the six files pass"), but the plan's `files_modified`/`<files>` lists only `tests/test_table_merge.py`, `tests/test_table_add_entries.py`, and `tests/test_write_tables.py` as the "three table test files" needing updates. `test_main_window_import.py`'s `_managed()` helper builds every pre-existing and newly-added entry for the post-install add-only path with the same literal `(descr "")`, which the Task 2 change breaks for all `Atomic_*` nicknames used throughout that file (27 test failures).
- **Fix:** Updated `_managed()` to compute the description via `table_generator.library_description(nick, rel, {})`, matching the fix already applied to the analogous helpers in the other three files. All affected nicknames in that file are either `Atomic_*` symbol libraries or `Atomic_Footprints`, so the computed description is independent of the (sometimes stale) `rel` argument passed for repoint-test fixtures, keeping those tests' repoint-only assertions correct.
- **Files modified:** `tests/test_main_window_import.py`
- **Verification:** `pytest tests/test_main_window_import.py -q` -> 60 passed; included in the full Task 2 verify run (218 passed) and the plan-level verification run (233 passed, including `tests/test_layering.py`).
- **Committed in:** `36bebc3` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1, test-coverage gap in the plan's file list vs. its own verify command).
**Impact on plan:** No scope creep — the fix only updates test expectations to match the plan's own specified behavior change (TBL-01/D-20), and is exactly the class of fix Task 2's `<verify>` command already demanded.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- TBL-01 is fully met: Generate and the post-install add-only entry both carry generated or kept descriptions; external entries and repoints are untouched.
- Plan 13-17 (table regeneration after the atomic migration) goes through the same `write_tables`/`add_library_entries` path and inherits these descriptions with no further code change needed.
- No blockers.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: tests/test_table_descriptions.py
- FOUND: kicad_lib_manager/table_generator.py
- FOUND: kicad_lib_manager/main_window.py
- FOUND commit: 43b5b0a (ancestor of HEAD)
- FOUND commit: 36bebc3 (ancestor of HEAD)
- Plan-level verification (`pytest tests/test_table_descriptions.py tests/test_table_merge.py tests/test_table_add_entries.py tests/test_write_tables.py tests/test_main_window.py tests/test_main_window_import.py tests/test_layering.py -q`): 233 passed
