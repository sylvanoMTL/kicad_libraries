---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 03
subsystem: library-tables
tags: [kicad, lib-table, sexpr, pyside6, pytest]

requires:
  - phase: 05-import-ui-and-post-install
    provides: add_library_entries, the post-install table step and its Result rows
provides:
  - "Post-install table step says 'already listed' only for a real path match (case-folded on Windows)"
  - "Stale tool-owned entry repointed after a backup; live clash and hand entry warned about and left byte-identical"
  - "Installs into an existing library follow the same rules and never add an entry"
affects: [12-import-flow-fixes, verify-work, case-sensitive re-test]

actuals:
  tokens: 14000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "One outcome per nickname by precedence: match, live tool-owned, hand-added, stale tool-owned repoint"
    - "Keyword test seams (fold=, add_missing=) on the table helpers, like platform= elsewhere"

key-files:
  created: []
  modified:
    - kicad_lib_manager/table_generator.py
    - kicad_lib_manager/main_window.py
    - tests/test_table_add_entries.py
    - tests/test_main_window_import.py

key-decisions:
  - "Existence of a tool-owned entry's target is checked against the app's own checkout (repo_root=REPO_ROOT), the same one the install used"
  - "A repoint edits only the URI token node (sexpr Edit + quote), so every other byte of the table is kept"
  - "The Result row is SUCCESS for a repoint, WARNING for any clash, INFO otherwise"

patterns-established:
  - "Existing-library installs call add_library_entries(add_missing=False) and only table.not_listed keeps the Generate hint"

requirements-completed: [REV-01]

coverage:
  - id: D1
    description: "A stale tool-owned table entry is repointed with a backup and an Updated row; matching entries are listed (case-folded on Windows)"
    requirement: REV-01
    verification:
      - kind: unit
        ref: "tests/test_table_add_entries.py#test_stale_managed_entry_is_repointed"
        status: pass
      - kind: unit
        ref: "tests/test_table_add_entries.py#test_matching_entry_ignores_case_when_folding"
        status: pass
      - kind: integration
        ref: "tests/test_main_window_import.py#test_tables_new_library_repoints_a_stale_entry"
        status: pass
    human_judgment: false
  - id: D2
    description: "A live clash and a hand-added entry leave the table untouched and warn in plain language"
    requirement: REV-01
    verification:
      - kind: unit
        ref: "tests/test_table_add_entries.py#test_live_managed_entry_warns_and_keeps_table"
        status: pass
      - kind: unit
        ref: "tests/test_table_add_entries.py#test_hand_entry_is_never_edited_even_when_stale"
        status: pass
    human_judgment: false
  - id: D3
    description: "Installs into an existing library repoint or warn the same way and never add an entry"
    requirement: REV-01
    verification:
      - kind: integration
        ref: "tests/test_main_window_import.py#test_tables_existing_library_repoints_a_stale_entry"
        status: pass
      - kind: integration
        ref: "tests/test_main_window_import.py#test_tables_existing_library_live_clash_warns"
        status: pass
      - kind: unit
        ref: "tests/test_table_add_entries.py#test_existing_library_never_adds_an_entry"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-11-01
status: complete
commits: 3
plan_head_before: a03faf412e01d4fde7367bb567e2dd0bac18c828
plan_head_after: 8923b4d01fc219abc47f768307af6fc038ed79db
---

# Phase 12 Plan 03: Post-install table step (REV-01) Summary

**The post-install table step now reports "already listed" only when the tool-owned entry points at the installed library, repoints stale entries after a backup, and warns (without writing) on live clashes and hand-added entries, for new and existing libraries alike.**

## Performance

- **Duration:** about 25 min
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files modified:** 4

## Accomplishments

- `table_generator._same_rel` compares repo-relative paths ignoring slash direction and a trailing slash, and letter case only when folding (default on Windows).
- `_add_entry` decides one outcome per nickname by precedence (match, live tool-owned, hand-added, stale tool-owned repoint) and returns `added`, `listed`, `updated`, `skipped` or `missing`. A repoint edits only the URI token, backs the table up first and writes atomically.
- `add_library_entries` takes `repo_root`, `add_missing` and `fold`; new issue codes `table.entry_updated` (SUCCESS), `table.path_clash` (WARNING), `table.not_listed` (INFO); the hand-entry clash text is reworded to the plain-language D-05 sentence.
- `_finish_post_install`: the new-library branch passes `repo_root=REPO_ROOT`; the existing-library branch now calls `add_library_entries(..., add_missing=False)`, keeps the Generate hint only for `table.not_listed`, sets the tables row for a repoint or a clash, and offers the path variables after a table write. `_tables_outcome` knows the new codes (SUCCESS on a repoint, WARNING on any warning).

## Task Commits

1. **Task 1 (tracer): stale repoint and live clash from a new-library install** - `f031b18` (feat)
2. **Task 2 RED: failing tests for hand entries and existing-library installs** - `2e55bd1` (test)
3. **Task 2 GREEN: existing-library installs follow the same rules** - `8923b4d` (feat)

## TDD Gate Compliance (Task 2)

- RED: `test_hand_entry_is_never_edited_even_when_stale`, `test_tables_existing_library_repoints_a_stale_entry` and `test_tables_existing_library_live_clash_warns` failed on the planned assertions (old wording of the hand-entry warning; existing-library branch still using the old table_info loop and so neither repointing nor warning). Command: `pytest tests/test_table_add_entries.py tests/test_main_window_import.py`, result `3 failed, 69 passed`. Semantic assessment: each target ran and failed on the planned behaviour, not on setup or import errors. The other new tests (precedence, `add_missing=False`, shared footprint repoint) were already green because Task 1, the tracer, implemented the core; they pin that behaviour. The `gsd_run check tdd-red-evidence` classifier was not run (pytest is not a supported report format).
- GREEN: all target tests pass; REFACTOR: none needed.

## Verification

`pytest tests/test_table_add_entries.py tests/test_main_window_import.py tests/test_write_tables.py tests/test_table_merge.py tests/test_layering.py -q` gave 134 passed. Layering holds (no new import in `table_generator`). The full suite was not run (orchestrator runs it after the wave merge). No tests were skipped for missing submodules.

## Deviations from Plan

None - plan executed as written. In Task 1 the hand-entry warning text was deliberately left in its old wording and reworded in Task 2, as the plan splits it.

## Known Stubs

None.

## Threat Flags

None. Mitigations T-12-05 to T-12-07 are covered: only tool-owned stale entries are repointed, the new URI goes through `sexpr.quote`, and every repoint logs `table.backed_up` and `table.entry_updated`.

## Self-Check: PASSED

- Files modified exist; commits f031b18, 2e55bd1 and 8923b4d are on the branch.
