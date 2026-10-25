---
phase: 07-snapeda-and-samacsys-adapters
plan: 02
subsystem: importer
tags: [kicad, snapeda, field-rules, preview, planner, tdd]

requires:
  - phase: 07-snapeda-and-samacsys-adapters
    provides: "plan 07-01 tracer: SnapEDAAdapter, vendorfixtures, test_vendor_install helpers"
provides:
  - "importer/fieldrules.py leaf: FieldRules, GENERIC_RULES, GENERIC_VOLATILE, is_volatile, alias tuples"
  - "SNAPEDA_RULES carried Detection.rules -> ImportCandidate.field_rules"
  - "FieldChange and InstallPlan.field_changes"
  - "kicad_files.list_properties and remove_property_edit"
  - "the Field changes preview section with fixed drop/clean/rename row formats"
affects: [07-03, 07-04, 07-05, 07-06]

actuals:
  tokens: 11000
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "per-adapter FieldRules travel on the candidate; the planner never looks them up from an adapter"
    - "every dropped property is a FieldChange on the plan and a preview row before anything is written"

key-files:
  created:
    - kicad_lib_manager/importer/fieldrules.py
  modified:
    - kicad_lib_manager/kicad_files.py
    - kicad_lib_manager/importer/plan.py
    - kicad_lib_manager/importer/candidate.py
    - kicad_lib_manager/importer/adapters/base.py
    - kicad_lib_manager/importer/adapters/snapeda.py
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/preview.py
    - tests/test_vendor_install.py

key-decisions:
  - "Field cleanup runs in planner._edit_symbol on the post-kicad-cli text; the rules come from candidate.field_rules"
  - "fieldrules.py imports nothing from the package; the alias tuples moved there and stay importable from adapters.base"
  - "A field change is listed only for a symbol the install writes or may write (new, overwrite, open); kept and identical symbols list none"
  - "purchase-url is in SNAPEDA_RULES.volatile (flagged assumption, owner to confirm)"

patterns-established:
  - "Drop tests assert subsets filtered by reason so later plans can add drops, cleans and renames without editing them"

requirements-completed: [INTK-03]

coverage:
  - id: D1
    description: "A SnapEDA part's Price, Check_prices and Availability are dropped from the installed symbol, identifiers kept, and each drop recorded as a FieldChange"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_vendor_install.py#test_snapeda_volatile_fields_dropped"
        status: pass
    human_judgment: false
  - id: D2
    description: "UL, Loose and Unknown candidates carry GENERIC_RULES and plan with no field changes"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_vendor_install.py#test_generic_rules_for_other_vendors"
        status: pass
    human_judgment: false
  - id: D3
    description: "remove_property_edit removes one property block span-exactly and keeps LF and CRLF line endings"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_vendor_install.py#test_remove_property_edit_basic"
        status: pass
    human_judgment: false
  - id: D4
    description: "The Field changes preview section lists every drop after Path rewrites, with fixed row formats, hidden when empty"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_vendor_install.py#test_field_changes_section"
        status: pass
      - kind: unit
        ref: "tests/test_vendor_install.py#test_field_change_row_format"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-10-23
status: complete
plan_head_before: 4e88be2c88424cce2302be6867def5d02ae8ab11
plan_head_after: 906cfc0757a363ba0f5a95a7dadb9fd2225b1a2e
---

# Phase 7 Plan 02: Volatile field drops and the Field changes preview Summary

**SnapEDA Price, Check_prices and Availability are removed from the installed symbol by span-exact edits, carried as FieldChange rows on the plan and listed in a new "Field changes" preview section, via per-adapter FieldRules that travel on the candidate**

## Performance

- **Duration:** 14 min
- **Started:** 2026-10-23T10:59:17Z
- **Completed:** 2026-10-23T11:13:04Z
- **Tasks:** 2
- **Files modified:** 9 (1 created, 8 modified)

## Accomplishments

- `FieldRules` / `GENERIC_RULES` / `is_volatile` live in a Qt-free leaf `importer/fieldrules.py`; `SNAPEDA_RULES` adds `purchase-url` to the volatile list and `SNAPEDA_PN` to the MPN aliases, and reaches the candidate through `Detection.rules` and `locate`.
- `build_plan` drops each volatile property of the incoming symbol (Price, Check_prices, Availability for the synthetic part) in property order, records a `FieldChange(action="drop", reason="volatile")` per drop, and `apply_plan` writes exactly the previewed bytes; SnapEDA_Link, MAXIMUM_PACKAGE_HEIGHT, Manufacturer and MPN stay.
- `preview_sections` shows a "Field changes" section directly after "Path rewrites" with the row format for drops, cleans and renames fixed for plan 07-03; plans without field changes show no such section.
- UL, Loose and Unknown candidates carry `GENERIC_RULES` and plan unchanged.

## Task Commits

1. **Task 1 RED:** `5dea71e` (test) - failing tests for volatile drops, generic rules and `remove_property_edit`
2. **Task 1 GREEN:** `12ed1db` (feat) - fieldrules module, rules plumbing, planner drops, `FieldChange`
3. **Task 2 RED:** `387395b` (test) - failing tests for the Field changes section and row format
4. **Task 2 GREEN:** `906cfc0` (feat) - `_field_changes_section` in preview.py

**Plan metadata:** committed with this SUMMARY (docs: complete plan).

## TDD Gate Compliance

- **RED (Task 1):** `5dea71e`. The run failed at collection with `ImportError: cannot import name 'SNAPEDA_RULES'` (the contract modules did not exist). This is the RED the plan itself specified ("module fieldrules missing, Price still present"), but strictly it is a load fault rather than an assertion failure on the target test, so it would classify as INVALID_RED under the tdd.md reference. Semantic assessment: the three target tests exercise names that are created by this plan, so no assertion-level RED was reachable without first adding stubs; GREEN then passed all three.
- **RED (Task 2):** `387395b`. A genuine assertion-level RED: `test_field_changes_section` failed with `ValueError: list.index(x): x not in list` ("Field changes" absent) and `test_field_change_row_format` with `AttributeError: 'NoneType' object has no attribute 'rows'`; the other four tests of the file still passed.
- **GREEN:** `12ed1db`, `906cfc0`. Target tests passed after each.
- **REFACTOR:** none needed.

## Files Created/Modified

- `kicad_lib_manager/importer/fieldrules.py` - field-cleanup rules leaf (new)
- `kicad_lib_manager/kicad_files.py` - `list_properties`, `remove_property_edit`
- `kicad_lib_manager/importer/plan.py` - `FieldChange`, `InstallPlan.field_changes`
- `kicad_lib_manager/importer/candidate.py` - `ImportCandidate.field_rules`
- `kicad_lib_manager/importer/adapters/base.py` - `Detection.rules`, `part_meta(symbol, rules)`, `locate` sets `field_rules`
- `kicad_lib_manager/importer/adapters/snapeda.py` - `SNAPEDA_RULES`, carried on the Detection
- `kicad_lib_manager/importer/planner.py` - `_edit_symbol(..., rules)` returns `(edits, mpn, changes)`; plan lists changes of pending symbols
- `kicad_lib_manager/importer/preview.py` - `_field_changes_section`
- `tests/test_vendor_install.py` - five new tests

## Decisions Made

- Followed the plan as specified (see key-decisions). `adapters/base.py` re-imports the three alias tuples from `fieldrules` so existing imports keep working; no `# noqa` was added (the repo carries none).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The full suite shows exactly the four known pre-existing failures (KiCad 10 symbol format 20251024): `test_version_real_cli_into_20241209`, `test_library_real_cli_new_header`, `test_noop_second_plan_after_normalised_apply`, `test_real_cli_upgrades_ul_symbol_deterministically`. No new failure. Tests needing the `Custom/` submodule skip in this worktree; the orchestrator re-runs them in the main checkout after the merge.

## Known Stubs

None.

## Threat Flags

None. The new surface is span edits on staged text, covered by T-07-03 (one edit per property via the `handled` set, `apply_edits` overlap check, re-parse of the edited unit, and the LF/CRLF test) and T-07-04 (every drop is a preview row before any write).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 07-03 can extend `FieldRules`, `FieldChange` reasons (placeholder, duplicate, whitespace, alias) and the already-implemented clean/rename row formats; the tests assert subsets so they need no edit.
- Flagged assumption for the owner: `purchase-url` is in `SNAPEDA_RULES.volatile`; remove the one tuple entry to keep it.

## Self-Check: PASSED

- Files exist: fieldrules.py, snapeda.py, plan.py, candidate.py, base.py, kicad_files.py, planner.py, preview.py, tests/test_vendor_install.py
- Commits exist: 5dea71e, 12ed1db, 387395b, 906cfc0 (verified ancestors of HEAD)
- Both Task 1 verify commands and the Task 2 verify command exit 0; dialog tests pass; full suite shows only the four known baseline failures; `git status --porcelain Custom downloaded_examples` is empty.

---
*Phase: 07-snapeda-and-samacsys-adapters*
*Completed: 2026-10-23*
