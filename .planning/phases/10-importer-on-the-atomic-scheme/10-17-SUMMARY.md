---
phase: 10-importer-on-the-atomic-scheme
plan: 17
subsystem: importer
tags: [manufacturer, canonical-spelling, datasheet-host, planner, form-defaults, pytest]

requires:
  - phase: 10-04
    provides: manufacturers table (lookup, by_host, hosts per company)
  - phase: 10-16
    provides: FieldChange "set" with reasons canonical and datasheet_host, preview wording, tests/test_field_rules.py
provides:
  - manufacturers.canonical(value)
  - suggest.manufacturer_from_datasheet(datasheet) -> (canonical name, aggregator host)
  - planner Manufacturer role in canonical spelling, host-inferred Manufacturer, Issue code naming.aggregator_host
  - form.field_defaults mirroring the planner for Manufacturer
affects: [10-18 token cleanup, 10-21 install gate, 10-25 help text]

actuals:
  tokens: 6000
  tasks: 3
  commits: 7
plan_head_before: 7f773daa8d898368c3b265627da26e777023d37a
plan_head_after: 1f0ed260668cb1863bc7f7b1f7e2c7e4eb0b42e5

tech-stack:
  added: []
  patterns:
    - "role() in planner._edit_symbol takes a spell callable and an inferred flag; a changed spelling or an inferred value is one set FieldChange, listed after the rename of the same property"

key-files:
  created: []
  modified:
    - kicad_lib_manager/manufacturers.py
    - kicad_lib_manager/importer/suggest.py
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/form.py
    - tests/test_field_rules.py
    - tests/test_install_e2e.py
    - tests/test_install_options_clear.py
    - tests/test_install_plan.py
    - tests/test_import_form.py
    - tests/test_import_dialog.py
    - tests/test_field_cleanup.py
    - tests/test_vendor_install.py
    - tests/test_import_preview.py
    - tests/test_samacsys_adapter.py
    - tests/test_shared_footprints.py
    - tests/test_real_vendor_samples.py

key-decisions:
  - "A cleared Datasheet does not stop the Manufacturer being found: the planner uses the typed link, else the vendor's link (keeps test_cleared_datasheet_writes_empty_property valid)"
  - "A typed Manufacturer is also written canonically (typing TI installs Texas Instruments)"
  - "The aggregator note is an INFO issue naming the full host (for example www.digikey.com) next to the existing missing-manufacturer WARNING"

requirements-completed: [LIB-07]

coverage:
  - id: D1
    description: "Manufacturer is written in the canonical table spelling (vendor or typed alias TI becomes Texas Instruments) and listed as 'TI -> Texas Instruments: canonical spelling'"
    requirement: LIB-07
    verification:
      - kind: unit
        ref: "tests/test_field_rules.py#test_a_vendor_alias_is_written_in_the_canonical_spelling"
        status: pass
      - kind: unit
        ref: "tests/test_field_rules.py#test_canonical_manufacturer_row_in_the_preview"
        status: pass
    human_judgment: false
  - id: D2
    description: "With no Manufacturer the planner takes it from the datasheet link's registered domain (ti.com, maximintegrated.com, analog.com), listed as 'found from the datasheet link'"
    requirement: LIB-07
    verification:
      - kind: unit
        ref: "tests/test_field_rules.py#test_the_datasheet_link_names_the_manufacturer"
        status: pass
    human_judgment: false
  - id: D3
    description: "A distributor or library site is never used and gives the INFO line naming.aggregator_host; unknown names kept as typed; cleared names written empty with no inference and no warning"
    requirement: LIB-07
    verification:
      - kind: unit
        ref: "tests/test_field_rules.py#test_a_distributor_link_is_never_used"
        status: pass
      - kind: unit
        ref: "tests/test_field_rules.py#test_a_name_that_is_not_in_the_table_is_kept_as_typed"
        status: pass
      - kind: unit
        ref: "tests/test_field_rules.py#test_a_cleared_manufacturer_is_written_empty_without_inference_or_warning"
        status: pass
    human_judgment: false
  - id: D4
    description: "form.field_defaults mirrors the planner and the dialog shows the canonical Manufacturer"
    requirement: LIB-07
    verification:
      - kind: unit
        ref: "tests/test_import_form.py#test_field_defaults_equivalence"
        status: pass
      - kind: unit
        ref: "tests/test_field_rules.py#test_dialog_shows_the_canonical_manufacturer"
        status: pass
    human_judgment: false

duration: 75min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 17: Manufacturer is canonical Summary

**Manufacturer is always written in the manufacturer table's spelling, taken from the vendor, the owner or the datasheet link's company domain, with distributor links refused and every change shown in the preview.**

## Performance

- **Duration:** about 75 min
- **Completed:** 2026-10-27
- **Tasks:** 3
- **Files modified:** 15

## Accomplishments

- `manufacturers.canonical(value)` and `suggest.manufacturer_from_datasheet(datasheet)` added; the planner and `form.field_defaults` both use them, so the dialog shows what the plan writes.
- The planner's Manufacturer role writes the canonical spelling (typed or vendor, including a renamed alias such as MF) and lists it as a `set` field change with reason `canonical`; a Manufacturer found from the datasheet link is listed with reason `datasheet_host`.
- A distributor or library host never names a company: it gives an INFO `naming.aggregator_host` line plus the existing missing-manufacturer WARNING. Unknown names stay exactly as given. A cleared Manufacturer is written empty with no inference and no warning.
- Manufacturer expectations migrated across 12 test files (TI to Texas Instruments, ADI to Analog Devices, RECOM Power to RECOM).

## Task Commits

1. **Task 1 (tracer): canonical Manufacturer from planner to dialog** - `0e2e5e2` (feat)
2. **Task 2 (tdd): rename-order fix** - `0a02842` (fix); **RED** `f45020d` (test); **GREEN** `704ccc3` (feat)
3. **Task 3: suite migration** - `8e9af61` (fix, cleared Datasheet), `9c9e55d` (test), `1f0ed26` (test, real SamacSys sample)

**Verification:** `pytest -m "not wurth"` in the worktree: 2750 passed, 31 skipped (Custom submodule and licence-restricted samples absent). With the real samples copied in, test_real_vendor_samples, test_vendor_install, test_vendorfixtures, test_install_e2e and the adapter tests pass.

**Plan metadata:** the docs commit that adds this summary.

## TDD Gate Compliance

- RED: `f45020d` adds the Manufacturer rule rows. One test failed on the planned assertion: `test_a_distributor_link_is_never_used` (`len(aggregator) == 1`, got 0) because the INFO line did not exist yet. Semantic assessment: the target test ran and failed on the intended assertion for the intended reason. The suite's pytest output is not one of the formats `gsd_run check tdd-red-evidence` accepts, so the classifier was not run; the assessment is by inspection of the real failure output.
- GREEN: `704ccc3` adds the INFO line; the same test and all 26 others pass.
- REFACTOR: none needed.

## Deviations from Plan

**1. [Order] Aggregator INFO line moved from Task 1 to Task 2**
- Task 1's tracer shipped canonical spelling and host inference but not the INFO line; Task 2's GREEN commit added it, so the TDD task has a real RED. The end state matches the plan.

**2. [Rule 1 - Bug] Renamed alias listed after its canonical change**
- Found during Task 2 tests: the canonical `set` change sorted before the `rename` of the same property. Fixed in `role()` so the rename comes first. Commit `0a02842`.

**3. [Rule 1 - Bug] Cleared Datasheet lost the Manufacturer**
- Found during Task 3 (`test_cleared_datasheet_writes_empty_property`): using `options.datasheet if not None` made a cleared Datasheet remove the Manufacturer inference. The planner now uses `options.datasheet or meta.datasheet`. Test added. Commit `8e9af61`.

**4. [Scope] Tests outside the plan's file list fixed**
- `tests/test_import_preview.py` (section order gains "Field changes"), `tests/test_samacsys_adapter.py` (RECOM Power installs as RECOM) and `tests/test_shared_footprints.py` (conflict edit now swaps a name that is not in the table), as the plan's Task 3 allows. Commit `9c9e55d`.
- `tests/test_real_vendor_samples.py`: the real SamacSys package (part_info.txt "RECOM Power") now installs as RECOM. This test skips in the worktree, so the licence-restricted samples were copied (gitignored, not committed) from the orchestrator checkout to verify it; the real SnapEDA sample already expected "Global Connector Technology". Commit `1f0ed26`.

**5. [Test helper] `_sets` in tests/test_field_rules.py takes a field**
- The Value section now filters on Value, because a ti.com link in the default fixture also finds a Manufacturer.

**Total deviations:** 5 (2 bugs, 3 test or ordering adjustments). **Impact:** none on the intended behavior.

## Issues Encountered

None beyond the deviations above. `help_dialog.py`, `tests/test_layering.py` and `tests/test_importer_layering.py` were not touched; both layering suites pass.

## Known Stubs

None.

## Threat Flags

None. T-10-23 is mitigated: only registered domains listed in the table name a company, aggregator hosts give the INFO line, an unlisted domain infers nothing (tested with ti.com, maximintegrated.com, analog.com, digikey.com and an unlisted domain).

## Next Phase Readiness

`manufacturer_choice`, `manufacturer_token`, `HOST_TOKENS` and `TokenChoice` in `suggest.py` are no longer called by the planner or the form; plan 10-18 deletes them with their tests.

## Self-Check: PASSED

All 15 modified files exist; commits 0e2e5e2, 0a02842, f45020d, 704ccc3, 8e9af61, 9c9e55d, 1f0ed26 are ancestors of HEAD; acceptance greps (`def canonical`, `manufacturer_from_datasheet(` in planner and form, `"canonical"` and `naming.aggregator_host` in planner) all match.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*
