---
phase: 05-import-ui-and-post-install
plan: 02
subsystem: importer-core
tags: [install-options, planner, wr-02, d-13, tdd]
requires: []
provides:
  - "InstallOptions.cleared: opt-in explicit-empty for value/datasheet/description/manufacturer/mpn"
  - "install.empty_required, install.symbols_dir_missing, install.footprints_dir_missing Issue codes"
affects: [05-07 fields UI]
tech-stack:
  added: []
  patterns: ["opt-in tri-state via a cleared frozenset beside the None-means-not-set rule"]
key-files:
  created:
    - tests/test_install_options_clear.py
  modified:
    - kicad_lib_manager/importer/plan.py
    - kicad_lib_manager/importer/planner.py
    - tests/test_install_plan.py
key-decisions:
  - "Emptied Datasheet is written as an empty value, not '~' (literal D-13); owner confirms KiCad loads it in the 05-11 UAT"
  - "UL-sample clear tests use a synthetic Custom layout (write_custom_layout) instead of custom_copy, so they never skip when the Custom submodule is absent"
requirements-completed: [PREV-04]
status: complete
duration: 25 min
completed: 2026-10-22
actuals:
  tokens: 9000
  tasks: 2
  commits: 4
plan_head_before: 543f75e8d932da33cca1d1a4a942e1e9fa127343
plan_head_after: 69a660fbcba80e378442143b6df13b5ba5cc3c48
coverage:
  - deliverable: "InstallOptions.cleared explicit-empty rule"
    human_judgment: false
    verification:
      - {kind: test, ref: "tests/test_install_options_clear.py#test_cleared_options_store_empty", status: pass}
  - deliverable: "Cleared Datasheet/Manufacturer/Description installed as empty properties; no manufacturer inference"
    human_judgment: false
    verification:
      - {kind: test, ref: "tests/test_install_options_clear.py#test_cleared_manufacturer_skips_inference", status: pass}
      - {kind: test, ref: "tests/test_install_options_clear.py#test_cleared_datasheet_writes_empty_property", status: pass}
      - {kind: test, ref: "tests/test_install_options_clear.py#test_cleared_description_creates_empty_property", status: pass}
  - deliverable: "Empty Value or MPN refused with install.empty_required"
    human_judgment: false
    verification:
      - {kind: test, ref: "tests/test_install_options_clear.py#test_cleared_mpn_refused", status: pass}
      - {kind: test, ref: "tests/test_install_options_clear.py#test_cleared_value_refused", status: pass}
  - deliverable: "WR-02 early refusal when Custom/Symbols or Custom/Footprints is missing"
    human_judgment: false
    verification:
      - {kind: test, ref: "tests/test_install_plan.py#test_new_library_refused_when_symbols_missing", status: pass}
      - {kind: test, ref: "tests/test_install_plan.py#test_new_library_refused_when_footprints_missing", status: pass}
  - deliverable: "Empty Datasheet loads correctly in KiCad"
    human_judgment: true
    rationale: "Needs KiCad to open the library; planned for the 05-11 UAT"
---

# Phase 5 Plan 02: Explicit field clear and WR-02 refusals Summary

`InstallOptions.cleared` lets a caller install an explicitly empty Datasheet, Description or Manufacturer (D-13), the planner refuses an empty Value or MPN, and creating a library while Custom/Symbols or Custom/Footprints is missing now fails early with a precise ERROR (WR-02).

## What was built

- **plan.py**: `cleared: frozenset[str] = frozenset()` on `InstallOptions`. A cleared field that is None or blank is stored as `""`; a blank field not in `cleared` still becomes None (WR-05 unchanged); text is kept byte-for-byte. An unknown name in `cleared` raises `ValueError`.
- **planner.py**:
  - `install.empty_required` refusal for a cleared Value or MPN (blocked plan, no ops), placed after the case-twin check and before `_select`, so the model file name can never fall back to the symbol name.
  - A cleared Manufacturer (`options.manufacturer == ""`) skips `manufacturer_choice` inference and the `install.manufacturer_missing` warning; `_edit_symbol` writes the empty property unchanged (no `_edit_symbol` change was needed).
  - WR-02: `install.symbols_dir_missing` and `install.footprints_dir_missing` with the UI-SPEC wording, raised before any file is read or written.
- **Tests**: `tests/test_install_options_clear.py` (9 tests) and 3 WR-02 tests in `tests/test_install_plan.py` (append-only; the WR-05 tests are untouched).

## TDD record

- RED 1 (e8bf22f): 8 of 9 new tests failed with `TypeError: unexpected keyword argument 'cleared'`, the planned missing feature. `test_override_text_written_exactly` already passed (existing behaviour, pinned as a regression guard).
- GREEN 1 (29f5b7b): plan.py and planner.py changes, 9 passed.
- RED 2 (357582d): the two WR-02 refusal tests failed on `assert plan.blocked` (plan was not refused); the unaffected-library test passed.
- GREEN 2 (69a660f): early refusal, 3 passed.
- No refactor commit.

## Commits

- e8bf22f test(05-02): add failing tests for explicit field clear (D-13)
- 29f5b7b feat(05-02): explicit clear for InstallOptions fields (D-13)
- 357582d test(05-02): add failing tests for WR-02 library creation refusals
- 69a660f feat(05-02): refuse library creation when Custom folders are missing (WR-02)

## Deviations from Plan

**1. [Test design] UL-sample clear tests use a synthetic layout, not `custom_copy`**
- **Found during:** Task 1
- **Issue:** the plan wrote these tests against `custom_copy`, which skips whenever the Custom submodule is not checked out (always, in a worktree).
- **Fix:** a local `ul_layout` fixture builds `Custom/{Symbols,Footprints,3DModels}` with an empty `IC_Battery_Charger_TI` pair via `write_custom_layout`, so the tests run everywhere and never skip. The vendor values asserted (Value, MPN, Manufacturer "TI", model `CSD85301Q2.stp`) come from the UL sample, not the target, so coverage is the same.
- **Files:** tests/test_install_options_clear.py
- **Commit:** e8bf22f

**2. [Naming] key_links pattern `symbols_dir\.is_dir\(\)`** is not matched literally: the two folder checks share one loop over `(exists, folder, code)` tuples and call `folder.is_dir()`. Behaviour is as specified.

**Total deviations:** 2 (both cosmetic). **Impact:** none on behaviour.

## Verification results

- `tests/test_install_options_clear.py`: 9 passed, 0 skipped.
- `tests/test_install_plan.py tests/test_install_e2e.py tests/test_install_apply.py tests/test_importer_layering.py`: all new and WR-05 tests pass; 52 skipped in the plan/e2e/apply/clear run (all "Custom submodule not checked out"; the orchestrator must re-run on the merged tree with the submodule).
- Full suite in the worktree: 1263 passed, 66 skipped, 4 failed.

## Deferred Issues (pre-existing, out of scope)

Four tests that call the real `kicad-cli` fail in this environment because KiCad 10 is installed and writes symbol format 20251024 where the tests expect 20241209 output. None touches the code changed here:
- tests/test_install_plan.py::test_version_real_cli_into_20241209
- tests/test_install_plan.py::test_library_real_cli_new_header
- tests/test_install_plan.py::test_noop_second_plan_after_normalised_apply
- tests/test_kicad_cli.py::test_real_cli_upgrades_ul_symbol_deterministically

## Known Stubs

None.

## Threat Flags

None. T-05-06, T-05-07 and T-05-08 are mitigated by `test_cleared_manufacturer_skips_inference`, `test_cleared_mpn_refused` and the WR-02 tests.

## Self-Check: PASSED

- tests/test_install_options_clear.py, plan.py and planner.py changes present; commits e8bf22f, 29f5b7b, 357582d, 69a660f are ancestors of HEAD.
- `git diff` of tests/test_install_plan.py shows additions only (0 removed lines).
