---
phase: 13-atomic-migration-and-kicad-setup
plan: 05
subsystem: migration
tags: [migration, atomic-libraries, inventory, kicad-sym, fixtures, s-expression]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "importer/migration package (precheck.py, PRE_ATOMIC_TAG, ensure_tag) and layering registrations for every planned importer.migration.* module (13-03)"
provides:
  - "importer/migration/plan.py: the migration contract (PartChoice, MigrationChoices, PlanContext, MigrationOp, PartPlan, LeftoverRow, FamilyRow, MigrationPlan, PartKey, OP_KINDS, FOOTPRINT_TARGETS, MAP_FILE), fixed before any planner, draft or window code"
  - "importer/migration/inventory.py: read_inventory (every Custom part, footprint, model and .bak, bounded by the importer's size/node caps) and migration_reason (the D-13 Migrate-menu enable check)"
  - "tests/migrationfixtures.py: the rich synthetic v1 Custom (mixed symbol format versions, SnapEDA alias fields, a shared footprint, a two-model footprint, board features, .bak files) that plans 13-06..13-16 build their tests on"
  - "importer/planner.py's symbol editing helpers promoted to public names (edit_symbol, SymbolFields, unit_text, SymbolSource, existing_source, new_source), reusable by the migration without cross-module private imports"
affects: ["13-06..13-16 (every later migration plan builds inside importer/migration/ against plan.py's contract and reads via inventory.py)"]

actuals:
  tokens: 13056
  tasks: 2
  commits: 2
  plan_head_before: 7b4b331a6d823ca4f1bf5fcecbb7e87c94a870f6
  plan_head_after: 6b79d0cba90324eeadddb2f04c4294b1e71d385f

tech-stack:
  added: []
  patterns:
    - "Migration contract as frozen dataclasses mirroring importer/plan.py's InstallPlan shape, fixed interface-first so parallel-wave plans never edit it"
    - "Bounded read+parse helper (open().read(cap+1) then kicad_files.parse_bytes(..., max_nodes=...)) reused for the inventory, since kicad_files.load() itself applies neither the byte nor the node cap"
    - "Listing helpers skip symlinks and junctions before descending a folder (T-13-14), matching importer/applier.py's existing junction-skip idiom"

key-files:
  created:
    - kicad_lib_manager/importer/migration/plan.py
    - kicad_lib_manager/importer/migration/inventory.py
    - tests/migrationfixtures.py
    - tests/test_migration_inventory.py
  modified:
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/form.py

key-decisions:
  - "inventory.py never imports importer.stems (outside its ALLOWED import set from plan 13-03): the shared footprint library name is a local constant, ATOMIC_PREFIX + \"Footprints\", instead"
  - "A symbol's Footprint field resolves to a Custom footprint by exact (library, file-name) match only; an official-KiCad-style link (Package_TO_SOT_SMD:SOT-23-5, modelled by the IMU-style fixture part) simply finds no match, with no special-casing needed"
  - "Model paths are matched only against the exact Custom/3DModels listing (never a path built from file text), so a model reference naming a file that is not there, or that uses another path variable, is silently excluded from InventoryFootprint.models rather than guessed at"

patterns-established:
  - "importer/migration/*.py stays inside the plan-13-03-registered ALLOWED import set per module; a new module's imports are checked against tests/test_importer_layering.py before any code is written, not after"

requirements-completed: [MIG-02, MIG-03]

coverage:
  - id: D1
    description: "The migration contract (MigrationPlan and its parts) exists, and the inventory read side lists every existing part, footprint, model and .bak of a rich synthetic v1 Custom, with the D-13 enable rule as a listing-only function"
    requirement: MIG-02
    verification:
      - kind: unit
        ref: "tests/test_migration_inventory.py#test_inventory_lists_every_part"
        status: pass
      - kind: unit
        ref: "tests/test_migration_inventory.py#test_inventory_links_footprints_and_models"
        status: pass
      - kind: unit
        ref: "tests/test_migration_inventory.py#test_inventory_lists_bak_files"
        status: pass
      - kind: unit
        ref: "tests/test_migration_inventory.py#test_migration_reason"
        status: pass
      - kind: unit
        ref: "tests/test_migration_inventory.py#test_inventory_reports_unreadable_library"
        status: pass
    human_judgment: false
  - id: D2
    description: "The importer's symbol editing helpers (edit_symbol, SymbolFields, unit_text, SymbolSource, existing_source, new_source) are public names with unchanged behaviour, so the migration can import them instead of importer private names"
    requirement: MIG-03
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py"
        status: pass
      - kind: unit
        ref: "tests/test_importer_layering.py"
        status: pass
      - kind: unit
        ref: "tests/test_import_form.py"
        status: pass
      - kind: unit
        ref: "tests/test_generated_text.py"
        status: pass
    human_judgment: false

duration: 50min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 05: Migration contract, v1 Custom inventory and public symbol helpers Summary

**`importer/migration/plan.py` (the frozen migration contract), `importer/migration/inventory.py` (read_inventory/migration_reason over a rich synthetic v1 Custom), and the importer's symbol-editing helpers promoted from private to public names for migration reuse.**

## Performance

- **Duration:** 50 min
- **Started:** 2026-11-11T15:35:00Z (approximate)
- **Completed:** 2026-11-11T16:25:32Z
- **Tasks:** 2 completed
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments

- `importer/migration/plan.py`: eight frozen dataclasses (`PartChoice`, `MigrationChoices`, `PlanContext`, `MigrationOp`, `PartPlan`, `LeftoverRow`, `FamilyRow`, `MigrationPlan`) plus the `PartKey` type alias and `OP_KINDS`/`FOOTPRINT_TARGETS`/`MAP_FILE` constants — the single contract every later Phase 13 plan builds against
- `importer/migration/inventory.py`: `read_inventory` parses every `.kicad_sym`, `.kicad_mod` and 3D model under `Custom/` (skipping symlinks/junctions, bounded by the importer's `MAX_KICAD_TEXT_BYTES`/`MAX_KICAD_TEXT_NODES` caps), resolving each symbol's `Footprint` field against the Custom footprints by exact library+file-name and each footprint's `${CUSTOM_3DMODEL_DIR}/...` model paths against the exact 3DModels listing; `migration_reason` is a listing-only function for the Migrate menu's D-13 enable check
- `tests/migrationfixtures.py`: a rich synthetic v1 Custom spanning all four live symbol format versions (20211014/20231120/20241209/20251024, all forced CRLF), with a revision-suffixed USB connector pair, an LTC2954-style family sharing two footprints across four parts, a fuel-gauge pair with only a `Value`, a SnapEDA-style FFC part carrying `MF`/`MP`/price/vendor-URL leftovers and a raw-newline description, an IMU part already linking an official KiCad footprint, an `Atomic_Oscillator` part, an oscillator part whose footprint has no model, a radio-module pair sharing one footprint with two byte-identical model blocks, two `.bak` files and two unlinked board-feature footprints — built entirely from existing `installfixtures`/`zipfixtures`/`stockfixtures`/`customfixtures` builders, never from the live `Custom/`
- `importer/planner.py`: `_Fields` → `SymbolFields`, `_edit_symbol` → `edit_symbol`, `_unit_text` → `unit_text`, `_SymbolSource` → `SymbolSource`, `_existing_source` → `existing_source`, `_new_source` → `new_source` at all 19 definitions and uses, with docstrings noting the Atomic_ migration as a caller; `importer/form.py`'s one docstring mention updated to `planner.edit_symbol`

## Task Commits

Each task was committed atomically:

1. **Task 1: The inventory of a rich v1 Custom lists every part, footprint, model and backup (MIG-02, D-03, D-04, D-13, D-21)** - `a60cd44` (feat)
2. **Task 2: Make the importer's symbol helpers public (behaviour-neutral)** - `6b79d0c` (refactor)

**Plan metadata:** committed together with this SUMMARY (worktree mode excludes STATE.md/ROADMAP.md; the orchestrator updates those centrally after merge).

## Files Created/Modified

- `kicad_lib_manager/importer/migration/plan.py` - the migration contract: eight frozen dataclasses, `PartKey`, `OP_KINDS`, `FOOTPRINT_TARGETS`, `MAP_FILE`
- `kicad_lib_manager/importer/migration/inventory.py` - `InventoryPart`, `InventoryFootprint`, `Inventory`, `read_inventory`, `migration_reason`
- `tests/migrationfixtures.py` - `write_v1_custom`, `write_v1_stock`, `make_v1_superproject`, `PART_NAMES`, `V1_LIBRARIES`, `BAK_FILES`, `BOARD_FEATURES`, `EXPECTED_TARGETS`
- `tests/test_migration_inventory.py` - the five behaviour tests
- `kicad_lib_manager/importer/planner.py` - six names promoted public; `build_plan`'s local `unit_text` variable renamed to `unit_source_text` (see Deviations)
- `kicad_lib_manager/importer/form.py` - one docstring reference updated

## Decisions Made

- `inventory.py` resolves footprint links by exact `(library, file-name)` match only — an official-KiCad-style `Footprint` field (e.g. `Package_TO_SOT_SMD:SOT-23-5`) simply finds no match among the Custom footprints, with no special-casing required
- Model paths are matched only against the exact `Custom/3DModels` listing; a model reference naming a file that isn't there, or using a different path variable, is silently excluded from `InventoryFootprint.models` rather than guessed at
- `inventory.py` imports strictly within the ALLOWED set plan 13-03 already registered for it in `tests/test_importer_layering.py`; the shared footprint library name is a local `ATOMIC_PREFIX + "Footprints"` constant rather than an `importer.stems` import

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `build_plan`'s local `unit_text` variable shadowed the newly public `unit_text` function**

- **Found during:** Task 2 (promoting `_unit_text` to `unit_text`)
- **Issue:** `build_plan` (in `planner.py`, the only caller of the renamed function outside its own definition) had a line `unit_text = _unit_text(vendor_sym, unit)`. Once `_unit_text` became the public `unit_text`, this line became `unit_text = unit_text(vendor_sym, unit)` — a self-referential local assignment. Because Python treats any name assigned anywhere in a function as local for that function's whole scope, the right-hand `unit_text(...)` call would resolve to the not-yet-assigned local variable instead of the module-level function, raising `UnboundLocalError` on every call to `build_plan` (i.e. on every import).
- **Fix:** Renamed the local variable to `unit_source_text` at its one assignment and its two uses (the `existing_source`/`new_source` calls immediately below it). A code comment at the assignment explains why the name differs from the parameter name used by `existing_source`/`new_source`.
- **Files modified:** `kicad_lib_manager/importer/planner.py`
- **Verification:** `pytest tests/test_install_plan.py tests/test_install_apply.py tests/test_install_e2e.py tests/test_install_gate.py tests/test_install_options_clear.py tests/test_case_sensitive_install.py tests/test_vendor_install.py tests/test_importer_layering.py tests/test_import_form.py tests/test_generated_text.py -q` — 364 passed, 1 skipped (opt-in UAT path)
- **Committed in:** `6b79d0c` (part of the Task 2 commit — the rename and its necessary fix are one behaviour-neutral change)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug, introduced by the rename itself and caught before any test ran against it).
**Impact on plan:** Required for the rename to be behaviour-neutral as the plan specifies; no scope creep. Every acceptance criterion and the full `test_install_*` suite pass unchanged.

## Issues Encountered

None beyond the deviation above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `importer/migration/plan.py` and `inventory.py` are ready for the planner, gate, applier, draft and window plans (13-06..13-16): the contract's shape and the read side are fixed and tested.
- `tests/migrationfixtures.py` gives every later migration test the same rich v1 Custom, with `PART_NAMES`, `V1_LIBRARIES`, `BAK_FILES`, `BOARD_FEATURES` and `EXPECTED_TARGETS` ready to import; `write_v1_stock` and `make_v1_superproject` are written to spec but exercised only by future plans' tests, not by this plan's own five tests.
- The importer's symbol editing helpers are importable by public name from `importer.planner`; no alias remains under the old private names anywhere in the repo.
- No blockers.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/importer/migration/plan.py
- FOUND: kicad_lib_manager/importer/migration/inventory.py
- FOUND: tests/migrationfixtures.py
- FOUND: tests/test_migration_inventory.py
- FOUND: commit a60cd44 (Task 1)
- FOUND: commit 6b79d0c (Task 2)
- `pytest tests/test_migration_inventory.py tests/test_importer_layering.py tests/test_install_plan.py tests/test_import_form.py tests/test_generated_text.py -q` -> 229 passed
