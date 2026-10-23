---
phase: 07-snapeda-and-samacsys-adapters
plan: 03
subsystem: importer
tags: [kicad, field-rules, planner, form, preview, tdd]

requires:
  - phase: 07-snapeda-and-samacsys-adapters
    provides: "plan 07-02: FieldRules, FieldChange, list_properties/remove_property_edit, the Field changes preview section"
provides:
  - "fieldrules.PLACEHOLDER_VALUES, STANDARD_FIELDS, is_placeholder, is_protected, clean_description"
  - "planner._edit_symbol cleanup for every vendor: duplicate alias drops, placeholder drops, Description/ki_description whitespace collapse, rename/drop/clean FieldChanges in property order"
  - "part_meta skips placeholder Manufacturer and MPN values"
  - "_Fields.mpn_default: candidate meta.mpn is the MPN fallback before the symbol name"
  - "form.field_defaults returns the cleaned Description"
affects: [07-04, 07-05, 07-06]

actuals:
  tokens: 14000
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "field changes are collected with the property position and sorted at the end, so renames, drops and cleans list in property order"
    - "a placeholder alias value counts as absent in both part_meta and the planner's role()"

key-files:
  created:
    - tests/test_field_cleanup.py
  modified:
    - kicad_lib_manager/importer/fieldrules.py
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/form.py
    - kicad_lib_manager/importer/adapters/base.py
    - tests/test_install_plan.py
    - tests/test_import_form.py

key-decisions:
  - "D-07 is applied in the planner and in form.field_defaults, not in part_meta (keeps the raw description for the 8 MiB cap test); the equivalence test proves form and planner agree"
  - "ki_* protection is wider than D-06's literal list: every ki_ name is kept, so ki_locked survives"
  - "A value overwritten in place on an exact Manufacturer/MPN property is not a separate row; those two fields are editable in the dialog already"

patterns-established:
  - "Drop/clean/rename tests compare the planned property list with plan.field_changes"

requirements-completed: [INTK-03, INTK-04]

coverage:
  - id: D1
    description: "Duplicate Manufacturer/MPN aliases are removed from the incoming symbol for every vendor; the SnapEDA part keeps Manufacturer (renamed MF) and MPN (renamed MP)"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_field_cleanup.py#test_snapeda_symbol_cleaned"
        status: pass
      - kind: unit
        ref: "tests/test_field_cleanup.py#test_duplicate_aliases_dropped"
        status: pass
    human_judgment: false
  - id: D2
    description: "Placeholder-valued vendor fields are dropped; Reference, Value, Footprint, Datasheet, Description and every ki_* property never are"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_field_cleanup.py#test_placeholder_vendor_fields_dropped"
        status: pass
      - kind: unit
        ref: "tests/test_field_cleanup.py#test_protected_fields_never_dropped"
        status: pass
      - kind: unit
        ref: "tests/test_field_cleanup.py#test_ul_property_list_unchanged_by_cleanup"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every rename, drop and clean is a FieldChange in property order and a Field changes preview row"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_field_cleanup.py#test_field_change_rows"
        status: pass
      - kind: unit
        ref: "tests/test_field_cleanup.py#test_description_whitespace_collapsed"
        status: pass
    human_judgment: false
  - id: D4
    description: "Descriptions are collapsed unless the caller typed one, and the form default equals what the planner writes for ul, aliases, inferred, renamed, snapeda and placeholder_mf"
    requirement: INTK-04
    verification:
      - kind: unit
        ref: "tests/test_import_form.py#test_field_defaults_equivalence"
        status: pass
      - kind: unit
        ref: "tests/test_field_cleanup.py#test_description_override_not_cleaned"
        status: pass
      - kind: unit
        ref: "tests/test_field_cleanup.py#test_ki_description_collapsed"
        status: pass
    human_judgment: false
  - id: D5
    description: "A placeholder alias counts as absent (MF N/A installs the inferred Manufacturer) and a metadata MPN is what both the planner and the form use"
    requirement: INTK-04
    verification:
      - kind: unit
        ref: "tests/test_field_cleanup.py#test_placeholder_alias_is_absent"
        status: pass
      - kind: unit
        ref: "tests/test_field_cleanup.py#test_mpn_fallback_is_meta_mpn"
        status: pass
    human_judgment: false
  - id: D6
    description: "Cleanup edits only the incoming unit; existing Custom/ symbols stay byte-identical"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_field_cleanup.py#test_cleanup_never_touches_existing_symbols"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-10-23
status: complete
plan_head_before: 6ef29c31aa1c205e3178d10edd3c3983c49aab40
plan_head_after: c9dc888bf7fade1320babf0ca2a46bbbffa194fd
---

# Phase 7 Plan 03: Field cleanup for every vendor Summary

**Duplicate Manufacturer/MPN aliases, placeholder-valued fields and description whitespace are cleaned from every vendor's incoming symbol in `planner._edit_symbol`, each change listed as a FieldChange and a "Field changes" preview row, with KiCad's standard and ki_* fields protected and the form defaults kept equal to the planner output**

## Performance

- **Duration:** 13 min
- **Started:** 2026-10-23T11:20:00Z
- **Completed:** 2026-10-23T11:33:39Z
- **Tasks:** 2
- **Files modified:** 7 (1 created, 6 modified)

## Accomplishments

- `fieldrules.py` gains `PLACEHOLDER_VALUES`, `STANDARD_FIELDS`, `is_placeholder`, `is_protected` (standard fields and every `ki_*` name) and `clean_description`.
- `_edit_symbol` treats a placeholder alias as absent, records the alias rename, drops every other present alias as `duplicate`, then drops volatile properties and placeholder-valued ones (never protected ones), and collapses Description / ki_description whitespace unless the caller typed the field. All changes are sorted by property position. The synthetic SnapEDA part ends with Reference, Value, Footprint, Manufacturer, MAXIMUM_PACKAGE_HEIGHT, STANDARD, PARTREV, SnapEDA_Link, MPN, Description, ki_fp_filters.
- `part_meta` skips placeholder Manufacturer and MPN values (Description and the rest keep the raw value); `_Fields.mpn_default` makes `meta.mpn` the MPN fallback before the symbol name, so a metadata-supplied MPN drives the symbol, the 3D model file name and the form.
- `form.field_defaults` returns the cleaned Description; `test_field_defaults_equivalence` now also covers `snapeda` and `placeholder_mf`.

## Task Commits

1. **Task 1 RED:** `476bf46` (test) - failing tests for alias/placeholder cleanup and the re-baselined exact-Manufacturer test
2. **Task 1 GREEN:** `cda9cf5` (feat) - fieldrules helpers, planner role()/walk, placeholder-aware part_meta
3. **Task 2 RED:** `615e42d` (test) - failing tests for description cleanup, meta MPN fallback and the two new equivalence cases
4. **Task 2 GREEN:** `c9dc888` (feat) - clean_description, planner description cleanup and mpn_default, form default

**Plan metadata:** committed with this SUMMARY (docs: complete plan).

## TDD Gate Compliance

- **RED (Task 1):** `476bf46`. Genuine assertion-level failures on the target tests (7 failed, 5 passed): e.g. property list stopped at `Package` instead of `STANDARD`, `KeyError: 'Rename MF'`, `assert 'N/A' == ''`, and `names.count("MANUFACTURER") == 0` false. The helper imports of `is_placeholder`/`is_protected` are done through the `fieldrules` module inside one test, so the module collected and only that test failed with `AttributeError`. Semantic assessment: each failing test fails on the planned behaviour. `test_protected_fields_never_dropped`, `test_cleanup_never_touches_existing_symbols` and `test_remove_property_edit_edges` passed at RED on purpose: they guard behaviour that must not change.
- **RED (Task 2):** `615e42d`. 5 failed, 37 passed: `test_snapeda_symbol_cleaned` and `test_description_whitespace_collapsed` (raw description still present), `test_ki_description_collapsed`, `test_mpn_fallback_is_meta_mpn` (`'PART' == 'HINT-9'`) and the `snapeda` equivalence case (`description` differs). `placeholder_mf` and `test_description_override_not_cleaned` passed at RED as guards.
- **GREEN:** `cda9cf5`, `c9dc888`. Target tests passed after each.
- **REFACTOR:** none needed.

## Files Created/Modified

- `kicad_lib_manager/importer/fieldrules.py` - placeholder/protected/description helpers
- `kicad_lib_manager/importer/planner.py` - cleanup steps and FieldChange records in `_edit_symbol`; `mpn_default`
- `kicad_lib_manager/importer/form.py` - cleaned Description default, docstring
- `kicad_lib_manager/importer/adapters/base.py` - `_first(..., skip_placeholders=False)` used for Manufacturer and MPN
- `tests/test_field_cleanup.py` - 15 new tests
- `tests/test_install_plan.py` - `test_fields_exact_manufacturer_kept` re-baselined (D-08)
- `tests/test_import_form.py` - equivalence cases `snapeda` and `placeholder_mf`

## Decisions Made

- Followed the plan as specified (see key-decisions). The re-baselined existing test is `tests/test_install_plan.py::test_fields_exact_manufacturer_kept`; no other existing test changed outcome.

## Deviations from Plan

None - plan executed exactly as written. Two test-only notes: the plan lists fourteen tests while the file holds fifteen (an extra `test_protection_and_placeholder_rules` unit test of the two predicates), and the `fieldrules` predicates are imported inside that test through the module so the RED run did not fail at collection.

## Issues Encountered

- The full suite shows exactly the four known pre-existing KiCad 10 failures (`test_version_real_cli_into_20241209`, `test_library_real_cli_new_header`, `test_noop_second_plan_after_normalised_apply`, `test_real_cli_upgrades_ul_symbol_deterministically`); 1733 passed, 79 skipped (Custom/ and WurthElektronik submodules and the symlink test skip in this worktree; the orchestrator re-runs them in the main checkout).

## Known Stubs

None.

## Threat Flags

None. The surface touched is span edits on the staged incoming unit, covered by T-07-05 (protected fields), T-07-06 (every change is a preview row), T-07-07 (placeholder aliases count as absent) and T-07-08 (existing library symbols byte-identical).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 07-04 to 07-06 can rely on `plan.field_changes` listing renames, drops and cleans for every vendor, and on `candidate.symbols[i].meta.mpn` (e.g. a part_info hint) driving the MPN and the model file name.
- Re-importing a SnapEDA part installed before this phase now renders a cleaned block and shows as a symbol conflict (RESEARCH Open Question 5); expected.

## Self-Check: PASSED

- Files exist: tests/test_field_cleanup.py, fieldrules.py, planner.py, form.py, adapters/base.py, test_install_plan.py, test_import_form.py
- Commits exist: 476bf46, cda9cf5, 615e42d, c9dc888 (ancestors of HEAD)
- Both task verify commands exit 0; dialog tests pass; the full suite shows only the four known baseline failures.

---
*Phase: 07-snapeda-and-samacsys-adapters*
*Completed: 2026-10-23*
