---
phase: 13-atomic-migration-and-kicad-setup
plan: 06
subsystem: importer
tags: [migration, atomic-check, kicad-cli, sexpr, applier, tdd]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "plan 13-05's migration contract (plan.py, inventory.py, tests/migrationfixtures.py) and the importer's now-public edit_symbol/unit_text/new_source/existing_source"
provides:
  - "The complete Atomic_ migration architecture: inventory -> plan -> end-state gate -> transaction -> zero violations"
  - "Final entry signatures for every migration module (planner, symbols, footprints, families, gate, mapfile, applier) that plans 13-09..13-13 deepen in parallel"
affects: [13-07, 13-08, 13-09, 13-10, 13-11, 13-12, 13-13, 13-14]

actuals:
  tokens: 14800
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Plan in memory, judge the planned end state (never the disk), apply as one reversible transaction"
    - "MigrationOp kinds mkdir/write/delete/rmdir, stable-sorted by kind, with reverse rollback on any failure"
    - "AtomicContext built over a plan's planned writes/deletes via atomic_check.repo_context's planned_footprints/planned_models seam"

key-files:
  created:
    - kicad_lib_manager/importer/migration/planner.py
    - kicad_lib_manager/importer/migration/symbols.py
    - kicad_lib_manager/importer/migration/footprints.py
    - kicad_lib_manager/importer/migration/families.py
    - kicad_lib_manager/importer/migration/gate.py
    - kicad_lib_manager/importer/migration/mapfile.py
    - kicad_lib_manager/importer/migration/applier.py
    - tests/test_migration_e2e.py
  modified: []

key-decisions:
  - "end_state_context always treats every non-Atomic_Footprints Custom footprint library as unresolvable (fp_libs=[] to atomic_check.repo_context), matching the architecture's intent that a complete migration leaves no v1 .pretty folder; only the planned Atomic_Footprints writes and untouched Atomic_Footprints entries resolve"
  - "Model file paths inside a moved footprint are left unedited in this plan (no 3D-model rename op): the footprint keeps its existing stem and its model reference, so the file on disk stays resolvable without a 3DModels write"
  - "importer.migration.symbols cannot import importer.migration.footprints per tests/test_importer_layering.py's ALLOWED registry, so the `footprints` parameter of plan_symbols is annotated under `from __future__ import annotations` without a runtime import"
  - "SHARED_FOOTPRINT_LIBRARY is read from .inventory (allowed for both footprints.py and gate.py) rather than importer.stems (not allowed for either), since inventory.py already defines the same constant"

patterns-established:
  - "A migration module's ALLOWED import set in tests/test_importer_layering.py is load-bearing and pre-registered by plan 13-03; check it before adding an import, not after a test failure"

requirements-completed: [MIG-02, MIG-03, MIG-05]

coverage:
  - id: D1
    description: "One complete v1 part plans, gates, applies and re-checks with zero atomic violations end to end"
    requirement: "MIG-02"
    verification:
      - kind: integration
        ref: "tests/test_migration_e2e.py#test_one_part_migrates_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "The Run gate judges the planned end state, not the disk: a footprint the plan deletes fails the gate even though the file still exists"
    requirement: "MIG-03"
    verification:
      - kind: integration
        ref: "tests/test_migration_e2e.py#test_gate_judges_the_end_state"
        status: pass
    human_judgment: false
  - id: D3
    description: "A part whose library is undecided blocks Run with a strip line targeting the library control"
    verification:
      - kind: integration
        ref: "tests/test_migration_e2e.py#test_undecided_library_blocks_run"
        status: pass
    human_judgment: false
  - id: D4
    description: "Any failure during apply rolls back every write, delete and folder change already made, in reverse order, byte-identical to before"
    requirement: "MIG-03"
    verification:
      - kind: integration
        ref: "tests/test_migration_e2e.py#test_apply_rolls_back_on_failure"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every planned operation stays inside Custom/"
    verification:
      - kind: unit
        ref: "tests/test_migration_e2e.py#test_plan_never_leaves_custom"
        status: pass
    human_judgment: false
  - id: D6
    description: "Several parts from mixed-format v1 libraries merge into one normalised Atomic_ library; a footprint shared by several parts moves once"
    requirement: "MIG-03"
    verification:
      - kind: integration
        ref: "tests/test_migration_e2e.py#test_two_libraries_merge_into_one_atomic_library"
        status: pass
    human_judgment: false
  - id: D7
    description: "Custom/MIGRATION-ATOMIC.md records the library map, symbol renames, footprint links and the three relink steps; an existing file is kept below this run's section"
    requirement: "MIG-05"
    verification:
      - kind: integration
        ref: "tests/test_migration_e2e.py#test_map_file_lists_the_changes"
        status: pass
    human_judgment: false
  - id: D8
    description: "A v1 library can be split: its parts land in different Atomic_ libraries and library_map records every pair"
    verification:
      - kind: integration
        ref: "tests/test_migration_e2e.py#test_split_library_keeps_the_staying_part"
        status: pass
    human_judgment: false

duration: 50min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 06: One v1 part migrates end to end; several parts merge into one Atomic_ library Summary

**The Atomic_ migration architecture proven in code: a MigrationPlan built in memory, judged against its own planned end state via atomic_check.check_symbol, applied as one reversible mkdir/write/delete/rmdir transaction, with every migration module's final entry signature in place for plans 13-09..13-13 to deepen in parallel.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-11-11
- **Tasks:** 2
- **Files created:** 8

## Accomplishments

- `planner.py`'s `build_migration_plan` orchestrates `symbols.plan_symbols`, `footprints.plan_footprints`, `families.find_families` and `mapfile.map_text` in the fixed order the RESEARCH recommended, producing one `MigrationPlan` with every op sorted mkdir/write/delete/rmdir
- `gate.py`'s `end_state_context` builds an `AtomicContext` over the plan's own planned writes and deletes (never the disk), so `check_plan` fails a part whose footprint the transaction deletes even though the old file is still on disk
- `applier.py`'s `apply_migration` writes a plan's ops as one transaction with app-data backups and reverse rollback (mkdir -> rmdir, write -> restore/remove, delete -> restore) on any `BaseException`
- `symbols.py`'s `plan_symbols` normalises each part's unit with the importer's own `new_source`/`existing_source`, edits it with `edit_symbol`, and either starts a new target library or splices additional parts into it with `symbol_insert_edit` — several parts from different v1 libraries, in different KiCad formats, land in one normalised Atomic_ library in source order
- `footprints.py`'s `plan_footprints` moves a Custom footprint into `Atomic_Footprints.pretty` once per footprint however many parts link it, and rmdirs a v1 `.pretty` folder once every footprint it held has moved
- `mapfile.py`'s `map_text` writes `Custom/MIGRATION-ATOMIC.md` with the library map, symbol renames, footprint links, 3D-model renames and the three KiCad relink steps, prepending each run above an "Earlier migrations" section holding the previous file's text
- `families.py` is a deliberate stub (`find_families` returns no families, `derived_edits` returns no edits) for plan 13-11 to fill

## Task Commits

TDD gate sequence for Task 2 (`tdd="true"`), with Task 1 (`type="tracer"`) committed first as a single tracer commit:

1. **Task 1: tracer — one v1 part migrates end to end** - `22f584a` (feat) — all seven migration modules with a one-part-per-target `plan_symbols`/`plan_footprints`, plus the five tracer behaviour tests
2. **Task 2 RED** - `8430c8b` (test) — three new behaviour tests for merging and splitting mixed-format libraries; `test_two_libraries_merge_into_one_atomic_library` fails on `assert ['PARTB1'] == ['PARTA1', 'PARTA2', 'PARTB1']` against the Task 1 tracer's implementation
3. **Task 2 GREEN** - `f77adb7` (feat) — `plan_symbols` splices every part into the assembled library instead of keeping only the last one; all eight behaviour tests pass

**Plan metadata:** commit pending (this SUMMARY)

## Files Created/Modified

- `kicad_lib_manager/importer/migration/planner.py` - `part_meta`, `prepare_context`, `build_migration_plan`
- `kicad_lib_manager/importer/migration/symbols.py` - `MIGRATION_RULES`, `SymbolsOutcome`, `target_libraries`, `part_mpns`, `plan_symbols`
- `kicad_lib_manager/importer/migration/footprints.py` - `FootprintsOutcome`, `plan_footprints`
- `kicad_lib_manager/importer/migration/families.py` - `FamiliesOutcome`, `find_families`, `derived_edits` (stubs; 13-11 fills them)
- `kicad_lib_manager/importer/migration/gate.py` - `StripLine`, `GateOutcome`, `end_state_context`, `check_plan`
- `kicad_lib_manager/importer/migration/mapfile.py` - `RELINK_STEPS`, `map_text`
- `kicad_lib_manager/importer/migration/applier.py` - `MigrationResult`, `apply_migration`, `MIGRATION_BACKUPS`
- `tests/test_migration_e2e.py` - the phase tracer's eight behaviour tests

## Decisions Made

- `end_state_context` passes `fp_libs=[]` to `atomic_check.repo_context` unconditionally, so every Custom footprint library other than `Atomic_Footprints` is unresolvable in the planned end state — matching the architecture's "zero v1 libraries left" intent rather than tracking which v1 `.pretty` folders this particular plan happens to remove
- Moved footprints keep their existing model-path text unedited in this plan; renaming a model file to track a renamed footprint is left for a later plan, since nothing in this plan's scope renames a footprint whose model path would then go stale
- `plan_symbols`'s `footprints` parameter is typed under `from __future__ import annotations` without importing `FootprintsOutcome`, because `importer.migration.footprints` is outside `importer.migration.symbols`'s registered import set in `tests/test_importer_layering.py`
- `SHARED_FOOTPRINT_LIBRARY` is imported from `.inventory` (registered for both `footprints.py` and `gate.py`) instead of `importer.stems` (registered for neither), reusing the constant `inventory.py` already defines

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Dropped `importer.package`/`importer.stems` imports that `tests/test_importer_layering.py` forbids for these modules**
- **Found during:** Task 1 (`<verify>` run against `tests/test_importer_layering.py`)
- **Issue:** The first draft of `symbols.py` imported `importer.package` for a node-count cap, and `footprints.py`/`gate.py` imported `importer.stems` for `SHARED_FOOTPRINT_LIBRARY`; the layering guard's `ALLOWED` registry (pre-populated by plan 13-03) forbids both for these three modules
- **Fix:** `symbols.py`'s re-parse of its own already-bounded output no longer caps node count; `footprints.py`/`gate.py` import `SHARED_FOOTPRINT_LIBRARY` from `.inventory`, which already defines it and is registered for both
- **Files modified:** `kicad_lib_manager/importer/migration/symbols.py`, `kicad_lib_manager/importer/migration/footprints.py`, `kicad_lib_manager/importer/migration/gate.py`
- **Verification:** `pytest tests/test_importer_layering.py` passes
- **Committed in:** `22f584a` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking). **Impact on plan:** Required for the plan's own `<verify>` command to pass; no scope creep.

## TDD Gate Compliance

Task 2 (`tdd="true"`) gate sequence, verified against `git log`:

| Gate | Commit | Pattern | Status |
|------|--------|---------|--------|
| RED | `8430c8b` | `test(13-06): ...` | Present — `test_two_libraries_merge_into_one_atomic_library` failed on its planned assertion (`assert ['PARTB1'] == ['PARTA1', 'PARTA2', 'PARTB1']`) against the Task 1 tracer's one-part-per-target `plan_symbols` |
| GREEN | `f77adb7` | `feat(13-06): ...` | Present — all eight tests in `tests/test_migration_e2e.py` pass |
| REFACTOR | — | `refactor(13-06): ...` | Not needed — no cleanup opportunity after GREEN |

**RED evidence caveat:** `gsd_run check tdd-red-evidence` was unavailable in this isolated worktree (no `.claude/gsd-core/` present), so RED was established by running `pytest tests/test_migration_e2e.py` directly and inspecting the failure (captured above) rather than through the machine-validated record pipeline. The failure is a genuine assertion failure on the planned behavior (a list-equality mismatch naming the missing symbols), not a collection error, import error, or unrelated failure — satisfying the gate's semantic-assessment requirement even without the automated record.

**Task 1 note:** Task 1 is `type="tracer"`, not `tdd="true"`; it was committed as a single `feat` commit per the tracer execution rule, and its own `<verify>` command was re-run and passed before Task 2 began (the tracer feedback gate).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Every migration module (`planner`, `symbols`, `footprints`, `families`, `gate`, `mapfile`, `applier`) exists with its final entry signature; plans 13-09 through 13-13 can deepen `symbols.py` (name-clash detection), `footprints.py` (description/tag generation, leftovers, conflicts), `families.py` (derived-symbol decisions), `gate.py` (per-code ordering and targets) and `mapfile.py` (empty-section wording) independently in wave 4
- `applier.py`'s rollback is a local copy of the importer's `_Undo`/`_rollback` pattern with the migration's extra op kinds; 13-13 is expected to harden it with a preflight containment check and backup pruning, matching the importer's own `apply_plan`
- No blockers

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*
