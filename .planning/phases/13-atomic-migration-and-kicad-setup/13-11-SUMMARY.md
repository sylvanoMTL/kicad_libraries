---
phase: 13-atomic-migration-and-kicad-setup
plan: 11
subsystem: importer
tags: [migration, atomic-check, kicad-cli, sexpr, families, derived-symbols]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "plan 13-06's migration contract (planner.py, symbols.py call sites, tests/migrationfixtures.py) with families.py left as a deliberate stub"
provides:
  - "families.py complete: find_families groups parts by (target, family prefix) and marks graphics-identical members as derived; derived_edits renders a member's own block into the (extends parent) form"
affects: [13-13, 13-14]

actuals:
  tokens: 5962
  tasks: 2
  commits: 2
  plan_head_before: f4d420948be3dc49328bf83823b58f3e7dbd8018
  plan_head_after: 477580fa6df1c8ec97293d2403404ef6286fc715

tech-stack:
  added: []
  patterns:
    - "Graphics identity for D-06: token_stream of every non-property child, unit sub-symbol names reduced to their trailing _<unit>_<style> suffix so a name-only difference still compares equal"
    - "Family grouping key is (target library, first family_prefixes() entry of the part's MPN or name) - scoping to target means two identical members in different target libraries are never a family"

key-files:
  created:
    - tests/test_migration_families.py
  modified:
    - kicad_lib_manager/importer/migration/families.py

key-decisions:
  - "find_families reuses InventoryPart.extends (already kicad_files.extends_name(ref.node) from read_inventory) instead of re-deriving it, so a part that already extends another in its own source is recognised without a second parse"
  - "Only the group's first member (by sorted (rel_path, name)) is ever compared as the parent; other members are never cross-compared against each other, exactly as the plan's action text specifies - a family with two distinct graphics variants only merges the sub-group that happens to match the globally-first member"
  - "A parent whose own source already extends another symbol takes its whole group out of family consideration (no promotion of the next member to parent); no test requires the alternative and the simpler rule is what the plan's action text describes"
  - "test_derived_members_pass_the_gate uses its own small two-part fixture (complete Manufacturer/Datasheet/Description and a linked 3D model) rather than migrationfixtures' LTC2954 fixture, because that fixture's footprints intentionally carry no 3D model (exercised by other tests) and PartChoice.model_source/model_name are not yet wired into footprints.py (13-10's scope) - there is no way to attach a model to the LTC2954 fixture's footprints via the current pipeline"

requirements-completed: [MIG-02, MIG-03]

coverage:
  - id: D1
    description: "Members of one variant family (same target, same first family prefix) whose graphics and pins are identical become derived (extends) symbols of the first member, one FamilyRow per match; a member differing by one pin stays standalone"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_families.py#test_identical_members_become_derived"
        status: pass
    human_judgment: false
  - id: D2
    description: "After build_migration_plan, the written library holds the parent first; applying derived_edits to a derived member produces (extends parent) plus its own properties, no unit sub-symbol, and its own MPN/Value/Footprint values intact"
    requirement: "MIG-03"
    verification:
      - kind: integration
        ref: "tests/test_migration_families.py#test_derived_block_shape"
        status: pass
    human_judgment: false
  - id: D3
    description: "A derived member with complete fields passes gate.check_plan on its own fields, exactly like a standalone part"
    requirement: "MIG-03"
    verification:
      - kind: integration
        ref: "tests/test_migration_families.py#test_derived_members_pass_the_gate"
        status: pass
    human_judgment: false
  - id: D4
    description: "PartChoice.derive=False keeps a graphically-identical member out of derived while still recording its FamilyRow; two identical members in different target libraries are never a family; a lone family-prefix member gets no row; a difference in pin number, pin position or a graphic line breaks identity, a name-only difference does not"
    verification:
      - kind: unit
        ref: "tests/test_migration_families.py#test_untick_keeps_member_standalone"
        status: pass
      - kind: unit
        ref: "tests/test_migration_families.py#test_members_in_different_libraries_are_not_a_family"
        status: pass
      - kind: unit
        ref: "tests/test_migration_families.py#test_name_only_difference_is_identical"
        status: pass
      - kind: unit
        ref: "tests/test_migration_families.py#test_single_member_has_no_family"
        status: pass
    human_judgment: false
  - id: D5
    description: "A planned library with a parent and two derived members loads cleanly in the real KiCad 10 command-line tool"
    verification:
      - kind: integration
        ref: "tests/test_migration_families.py#test_real_kicad_loads_derived_library"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 11: Variant families become derived symbols (D-06) Summary

**`families.py` complete: `find_families` groups parts by target library and MPN/name family prefix, marking graphics-identical members (unit sub-symbol names reduced to their unit/style suffix, properties excluded) as derived symbols of the group's first member; `derived_edits` renders a derived member's own parsed block into the `(extends "<parent>")` form KiCad's own libraries use, verified against the real KiCad 10 command-line tool.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-11-11
- **Completed:** 2026-11-11
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `find_families` groups `Inventory` parts by `(target_library, first family_prefixes() entry of the part's MPN or name)` and, within each group sorted by `(rel_path, name)`, compares every other member's `_graphics_stream` against the first member's; an equal stream yields a `FamilyRow` and, when the owner's `PartChoice.derive` is true (the default), a `derived[member] = parent` entry
- `_graphics_stream` builds `sexpr.token_stream` tuples of every non-property child of a symbol, reducing a unit sub-symbol's own name token to just its trailing `_<unit>_<style>` suffix so two members differing only by their own name (and so their sub-symbols' names) still compare equal; any other difference - a pin number, a pin position, a graphic line, a flag - breaks the match
- `derived_edits` replaces the span from a symbol's name token to the end of its block with `(extends "<parent_name>")` followed by its own `(property ...)` children and, when present, its `(embedded_fonts ...)` child, each on its own line at the file's own indentation and EOL - matching the shape of KiCad 10's own `Regulator_Linear.kicad_sym`
- A part that already extends another symbol in its own source (`InventoryPart.extends`, already computed by `read_inventory`) is never treated as a parent or a member, without a second parse
- Nine tests in `tests/test_migration_families.py` cover identical-member detection, the derived block shape (applied to a real `build_migration_plan` output), gate interaction on complete fields, the per-member untick, the one-library-per-family rule, three distinct kinds of "not identical" (pin number, pin position, graphic line) against the "name-only" identical case, the single-member edge, and a real KiCad 10 load of a parent plus two derived members

## Task Commits

1. **Task 1: Identical family members plan as derived symbols and pass the gate (tracer)** - `ffafa4f` (feat) - `find_families`, `_family_key`, `_graphics_stream`, `derived_edits`, and the three tracer behaviour tests
2. **Task 2: Untick, edge families and a real KiCad load (tdd)** - `477580f` (test) - the five edge-case and real-tool tests; no feat/GREEN commit follows (see TDD Gate Compliance below)

**Plan metadata:** commit pending (this SUMMARY)

## Files Created/Modified

- `kicad_lib_manager/importer/migration/families.py` - `find_families`, `_family_key`, `_graphics_stream`, `_loaded`, `derived_edits`, `_indent` (was a deliberate stub from plan 13-06)
- `tests/test_migration_families.py` - new, nine tests covering both tasks' behaviour

## Decisions Made

- `find_families` reuses `InventoryPart.extends` instead of re-parsing a symbol's own `extends` child, since `read_inventory` already computed it via `kicad_files.extends_name`
- Only the group's globally-first member is ever used as the comparison parent; other members are compared only against it, never against each other - matching the plan's action text literally. In the full migration fixture this means a family with two distinct graphics sub-groups (e.g. LTC2954's 2-pin DFN8 pair and 3-pin TSOT-23 pair) only merges the sub-group that happens to include the group's first member; the other sub-group stays standalone even though its two members are identical to each other. No test in this plan's `<behavior>` list requires the alternative (cross-comparing every pair), and the simpler rule is what Task 1's action text describes
- A parent whose own source already extends another symbol takes its whole group out of consideration rather than promoting the next member to parent - simpler, and untested either way by this plan's required behavior
- `test_derived_members_pass_the_gate` builds its own small two-part fixture instead of reusing `migrationfixtures`' LTC2954 library, because that library's footprints intentionally have no 3D model (exercised by other, unrelated tests) and the current `footprints.py` pipeline does not yet read `PartChoice.model_source`/`model_name` (left to plan 13-10's scope per its own module boundary) - there is no way to attach a model to the LTC2954 fixture's footprints today

## Deviations from Plan

None - plan executed exactly as written for this plan's own two files (`families.py`, `tests/test_migration_families.py`).

## Issues Encountered

**`symbols.py` does not yet call `derived_edits` (out of this plan's scope).** The plan's `<interfaces>` section states that `symbols.plan_symbols` already calls `families.derived_edits` for every derived member ("call site from plan 13-06"), but inspection of the current `kicad_lib_manager/importer/migration/symbols.py` shows no such call: `plan_symbols` only reads `families.derived.get(part.key)` to set `PartPlan.parent` as metadata. The written symbol library therefore still holds every migrated part as a full standalone copy (unit sub-symbols and all), regardless of whether `find_families` marked it derived.

This plan's dispatch explicitly scoped me to `families.py` and `tests/test_migration_families.py` only, with an instruction to record any needed sibling-module change here rather than edit it. `test_derived_block_shape` proves `derived_edits` produces the correct shape by applying it manually to a real `build_migration_plan` write-op's output (parent + member, both still full copies) and reparsing the result - this is the faithful test of the function's contract, but it does not change what the real pipeline writes to disk today.

**Follow-up needed:** a future plan should add, inside `symbols.plan_symbols`, a call to `families.derived_edits(work_or_edited, placed_ref, parent_new_name)` for every part whose key is in `families.derived`, applying the returned edit before (or instead of) splicing the part's block into the assembled library text, and verify `test_migration_e2e.py` and any new family-aware e2e test still pass. Candidates: 13-13 (`applier.py`/`commitplan.py`, not `symbols.py` either) or a dedicated small follow-up plan touching `symbols.py` directly.

## TDD Gate Compliance

Task 2 carries `tdd="true"`. Per `git log`:

| Gate | Commit | Pattern | Status |
|------|--------|---------|--------|
| RED | - | `test(13-11): ...` | Present as a commit (`477580f`), but **not a RED failure** - see below |
| GREEN | - | `feat(13-11): ...` | Absent - no implementation change was needed |
| REFACTOR | - | `refactor(13-11): ...` | Not applicable |

**Why there is no RED/GREEN split for Task 2.** Task 1's `find_families` was designed and implemented as one coherent function in the Task 1 commit (`ffafa4f`), and its grouping key already includes the target library (so cross-library matches are structurally impossible), its per-member comparison already reads `choices.parts.get(member.key, PartChoice()).derive` (so untick is already honored), and its `len(members) < 2: continue` guard already excludes single-member groups. These are not special cases bolted on afterward; they are direct, load-bearing parts of Task 1's grouping and comparison logic (documented in Task 1's `<action>` text itself: "within a group sorted by key, the first member is the parent"; derive is read "per member" from the start).

When I wrote Task 2's five tests against this already-complete implementation, all five passed on the first run - there was no failing RED state to commit. This is exactly the scenario `tdd.md`'s Error Handling section names explicitly: *"Test doesn't fail in RED phase: Feature may already exist - investigate."* I investigated (re-reading `find_families`' grouping/comparison logic against each of Task 2's five behaviors) and confirmed the feature already existed correctly, rather than fabricating a temporary regression to manufacture a RED commit. The `test(13-11): ...` commit here is real (it adds five new tests, all passing), but it is not preceded by a failure and is not followed by a GREEN implementation commit, because none was needed.

The one test with materially new content, `test_real_kicad_loads_derived_library`, exercises `derived_edits` (already complete from Task 1) against the real KiCad 10 binary rather than `FakeCli`; it also passed immediately (confirmed via `pytest -m kicad_cli`, 1 passed, not skipped).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `families.py` is complete and matches the final entry signatures from plan 13-06: `find_families(inventory, choices, *, targets, mpns) -> FamiliesOutcome`, `derived_edits(loaded, ref, parent_name) -> list[Edit]`
- `tests/test_migration_e2e.py` (8 tests) and `tests/test_importer_layering.py` (14 tests) still pass unchanged
- Blocker for a future plan (not this one): wire `symbols.plan_symbols` to call `derived_edits` for every part in `families.derived`, so the migration actually writes the shortened `(extends ...)` form to disk instead of a full standalone copy - see Issues Encountered above

## Self-Check: PASSED
