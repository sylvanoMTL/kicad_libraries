---
phase: 13-atomic-migration-and-kicad-setup
plan: 26
subsystem: migration-gate-and-window
tags: [gate, strip-line, library-basis, weak-suggestion, migration-dialog, help, gap-closure]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "13-23 Library combo textActivated list pick; 13-25 LibrarySuggestion.weak"
provides:
  - PartPlan.library_basis ("chosen", "suggested", "guessed", "")
  - a blocking, plain, Library-targeted strip line for a guessed library
  - "library to check" / "suggested library" marks in the part list, a visible suggestion note, alternatives in the Library dropdown
  - User Guide and CLAUDE.md text for all of it
affects: [13-28]

actuals:
  tokens: 14000
  tasks: 3
  commits: 5

plan_head_before: 5849ba01f258ed71b7c51d5dbd4fc91c6867025a
plan_head_after: f5308ca7ab875d210333c6333e4b0ec10106118e

tech-stack:
  added: []
  patterns:
    - "a defaulted last field on a frozen PartPlan carries provenance (library_basis) from planner to gate and window"
    - "plain-text QLabel note under a field, colour from theme tokens"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/migration/plan.py
    - kicad_lib_manager/importer/migration/symbols.py
    - kicad_lib_manager/importer/migration/gate.py
    - kicad_lib_manager/widgets/migration_dialog.py
    - kicad_lib_manager/widgets/help_dialog.py
    - CLAUDE.md
    - tests/test_migration_gate.py
    - tests/test_migration_dialog.py
    - tests/test_help_dialog.py

key-decisions:
  - "A guessed library is a blocking strip line (not a non-blocking note), as stated in the plan; a confident suggestion never blocks"
  - "The guess line has sequence 0 and does not stop the part's own error and atomic-rule lines"
  - "The dropdown offers alternatives and the suggestion name filtered through the name rule; the badge keeps counting only planned libraries, so an alternative still reads as new"

requirements-completed: [MIG-02, DOC-01]

duration: 35min
completed: 2026-11-13
status: complete
---

# Phase 13 Plan 26: Visible, blocking guessed libraries Summary

**A weak, unconfirmed library suggestion now blocks Run with a plain Library-targeted strip line, is marked "library to check" in the part list with an amber reason note, and the right library is one dropdown pick away (closes the visibility half of gap G-13-1-f).**

## Accomplishments

- `PartPlan.library_basis` set by `_library_basis(choice, suggestion, target)` at both construction sites: owner choice or typed name is `chosen`, a strong suggestion `suggested`, a weak one `guessed`, no library `""`.
- `gate.check_plan` appends `GUESSED_LIBRARY_TEXT` (target `library`) for a `guessed` part; any recorded library, even the same one, clears it. Part errors and atomic-rule lines still follow. The whole v1 fixture with KiCad 10 stock still reaches an empty strip (IMU is `suggested`, `Atomic_Sensor_Motion`).
- Migration window: `GUESS_MARK` and `SUGGESTED_MARK` in each part's status, a plain-text `_suggestion_note` (amber "Only a guess: ... Pick a library from the list, or type one, to confirm it."; muted reason for a confident suggestion; hidden for an owner choice), and the dropdown also lists the suggestion's alternatives that pass the name rule. The badge still uses the planned names only.
- User Guide Migrating and Importing pages, plus the CLAUDE.md Migrate bullet, describe the marks, the strip line and the description outranking a weak vote.

## TDD record

- **Task 1 RED (36d30b4):** 4 target tests failed on the planned behaviour (`PartPlan` has no `library_basis`, no `GUESSED_LIBRARY_TEXT`, no guess line); the preconditions inside them (IMU suggestion weak, target `Atomic_Timer`) held. Semantic assessment: each test reached its planned assertion or attribute; no collection, import or fixture fault (the constant is read through the module so the file still collects).
- **Task 1 GREEN (30f53df):** 78 passed across the six verify files, none skipped.
- **Task 2 RED (99bd80b):** 4 target tests failed (missing `GUESS_MARK` / `_suggestion_note` / alternatives); 16 existing passed. Constants are read through the module for the same collection reason.
- **Task 2 GREEN (6c2a606):** 43 passed across the five verify files (test_migration_dialog.py now 20 tests).
- **Task 3 (f5308ca):** `type="auto"` without tdd; tests and text committed together; 72 passed.
- `gsd_run check tdd-red-evidence` is unavailable in this worktree (no `.claude/gsd-core`), so RED evidence was inspected by hand from pytest output.
- No REFACTOR commit.

## Task Commits

1. Task 1 RED: `36d30b4` test(13-26)
2. Task 1 GREEN: `30f53df` feat(13-26)
3. Task 2 RED: `99bd80b` test(13-26)
4. Task 2 GREEN: `6c2a606` feat(13-26)
5. Task 3: `f5308ca` docs(13-26)

## Verification

Plan-level command over 13 files: 193 passed. No pytest process left running.

## Deviations from Plan

None - plan executed exactly as written. (The plan's "10 tests in test_migration_gate.py" holds: 6 existing + 4 new.)

## Known Stubs

None.

## Threat Flags

None. T-13-69 (blocking guess line), T-13-70 (PlainText note), T-13-71 (badge counts planned libraries only), T-13-72 (fixtures under tmp_path) mitigated and tested. No test touched the live `Custom/` or KiCad config.

## Next

Plan 13-28 runs the whole suite once on the merged code.

## Self-Check: PASSED

- Modified files exist and the verify runs pass; commits 36d30b4, 30f53df, 99bd80b, 6c2a606, f5308ca are on this branch.
