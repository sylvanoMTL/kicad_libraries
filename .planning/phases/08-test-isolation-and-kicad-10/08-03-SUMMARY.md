---
phase: 08-test-isolation-and-kicad-10
plan: 03
subsystem: testing
tags: [pytest, fixtures, test-isolation, synthetic-custom]

requires:
  - phase: 08-test-isolation-and-kicad-10
    provides: "synthetic_custom fixture and customfixtures.write_synthetic_custom (plan 08-02)"
provides:
  - "Dialog, preview, install-transaction and ranking tests run on the synthetic Custom/, not the live tree"
affects: [08-06]

plan_head_before: 6fa6944abd96ac00811c549ab96a487820c3258b
plan_head_after: 9fc30284a237ce47d4fdefe31efb6fb1d5d3352a

actuals:
  tokens: 6000
  tasks: 2
  commits: 2

key-files:
  created: []
  modified:
    - tests/test_import_dialog.py
    - tests/test_import_preview.py
    - tests/test_install_apply.py
    - tests/test_naming_suggest.py

key-decisions:
  - "Pure fixture rename; no assertion changed, no skip or xfail added"

requirements-completed: [TEST-01]

duration: 15min
completed: 2026-10-25
status: complete
---

# Phase 8 Plan 03: Dialog, preview, install and ranking tests on the synthetic Custom/ Summary

**Four test files moved from the live-tree copy fixture to `synthetic_custom`; the 10 formerly failing tests now pass whatever the live Custom/ holds, and the ranking test no longer depends on the live library list.**

## Accomplishments

- `test_import_dialog.py` (13 uses) and `test_import_preview.py` (3 uses): `make_dialog`, `test_tracer_ul_import_end_to_end`, `test_tracer_nothing_written_before_install`, `test_preview_sections_follow_plan_ops` and `test_rows_reimport_into_the_real_custom_library` use `synthetic_custom`. The preview test comment now names the synthetic Custom/.
- `test_install_apply.py` (32 uses incl. `request.getfixturevalue("synthetic_custom")`): the seven formerly failing tests pass (`stale_plan_ul_target_edited_during_gate`, `source_changed_at_apply`, `source_gone_at_apply`, `rollback_fail_on_nth_write[existing-1/2/3]`, `success_touched_order`; the `-k` selection ran 10 passed, 0 skipped). Module docstring updated.
- `test_naming_suggest.py`: `test_suggest_live_custom` renamed to `test_suggest_synthetic_custom(synthetic_custom)`, submodule skip removed, ranking computed from `list_existing_libraries(synthetic_custom)`. Both assertions unchanged and pass (`IC_SubCategory_TI`, `alternatives[0] == IC_Battery_Charger_TI`).

## Task Commits

1. **Task 1 (tracer): dialog and preview installs on synthetic Custom/** - `e9d7261`
2. **Task 2: install-transaction and ranking tests on synthetic Custom/** - `9fc3028`

## Findings

The ranking assertion held as written for the five synthetic libraries, so `suggest.py`'s ranking rule was not consulted and no expected value changed (no Assumption A4 deviation). `REPO_ROOT`, `RepoLayout` and `pytest` remain in use in `test_naming_suggest.py`, so no import was removed.

## Deviations from Plan

None - plan executed exactly as written. No application code under `kicad_lib_manager/` changed.

## Verification

- `pytest tests/test_import_dialog.py tests/test_import_preview.py tests/test_install_apply.py tests/test_naming_suggest.py -q`: 310 passed, 0 skipped, in a worktree with no Custom/ checked out.
- The three Task 1 named tests: 3 passed.
- `grep custom_copy` over the four files: no output. The assertion-line diff check against the plan's base prints nothing.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- Commits e9d7261 and 9fc3028 are ancestors of HEAD; the four modified test files exist.
