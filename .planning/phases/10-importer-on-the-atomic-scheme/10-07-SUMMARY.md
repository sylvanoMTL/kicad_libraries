---
phase: 10-importer-on-the-atomic-scheme
plan: 07
subsystem: testing
tags: [pytest, atomic-naming, footprint_library_for, install-tests]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "plan 10-02: atomic_custom fixture, footprint_library_for, Atomic_ constants in customfixtures"
provides:
  - "Install-path tests (e2e, plan, apply, options-clear, verify, kicad-cli) targeting Atomic_ libraries"
  - "Every footprint location of an install target in these six files computed through footprint_library_for"
affects: [10-10, 10-12, 10-15]

actuals:
  tokens: 18000
  tasks: 2
  commits: 2
plan_head_before: b4f956441ef5cab68b1bc6efe104c5a92c09da70
plan_head_after: a70336f010a15e37c429cf2d6106efc887c7c38c

tech-stack:
  added: []
  patterns:
    - "Footprint folders, Footprint links, conflict keys and write_custom_layout footprint_libs are built with footprint_library_for(<target>)"
    - "Tests that install into an existing synthetic library use atomic_custom; on-purpose v1/placeholder tests keep synthetic_custom"

key-files:
  created: []
  modified:
    - tests/test_install_e2e.py
    - tests/test_install_plan.py
    - tests/test_install_apply.py
    - tests/test_install_options_clear.py
    - tests/test_install_verify.py
    - tests/test_kicad_cli.py

key-decisions:
  - "IC_Test_TI maps to Atomic_Analog and IC_New_TI to ABSENT_LIBRARY (Atomic_Transistor_FET), per the plan mapping"
  - "Left unchanged on purpose: placeholder test (IC_SubCategory_TI on synthetic_custom), case-twin tests (LIBRARY.lower() with explicit footprint_libs tuples), invalid-name tests, and the non-target names IC_Old_TI (backup stamp folders) and the IC_Other_TI/IC_A_TI style 'elsewhere' symbol libraries in test_install_verify.py"

requirements-completed: [LIB-05, LIB-06]

coverage:
  - id: D1
    description: "The real UL install end to end runs on an Atomic_ target and expects its footprint folder, Footprint link and UAT paths through footprint_library_for"
    requirement: LIB-06
    verification:
      - kind: e2e
        ref: "tests/test_install_e2e.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Planner, apply, verify, options-clear and kicad-cli tests install into Atomic_ targets with footprint locations through footprint_library_for"
    requirement: LIB-05
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py tests/test_install_apply.py tests/test_install_options_clear.py tests/test_install_verify.py tests/test_kicad_cli.py"
        status: pass
      - kind: other
        ref: "pytest -m 'not wurth' -q: 2355 passed, 26 skipped"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 07: Install-path tests on Atomic_ targets Summary

**Six install-path test files now install into Atomic_ libraries and compute every footprint folder, Footprint link and conflict key through `footprint_library_for`, so plans 10-10 and 10-12 can change the name rule and the shared library without editing them.**

## Performance

- **Duration:** about 45 min (the full suite takes about 11.5 min)
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- `tests/test_install_e2e.py`: `LIBRARY` is `BATTERY_CHARGER`, `NEW_LIBRARY` is `ABSENT_LIBRARY`, the version scenarios use `IMU`, `MAGNETOMETER`, `POWER_MOSFET`, `WIRELESS`; every test uses `atomic_custom`; 12 uses of `footprint_library_for`.
- `tests/test_install_plan.py`: `LIBRARY` is `Atomic_Analog`, `UL_LIBRARY` is `BATTERY_CHARGER`, `NEW_LIBRARY` is `ABSENT_LIBRARY`; layouts, pretty folders, Footprint links and `footprint:` conflict keys go through the helper; the IMU pair-completed test uses `IMU`.
- `tests/test_install_apply.py`, `tests/test_install_options_clear.py`, `tests/test_install_verify.py`, `tests/test_kicad_cli.py`: install targets moved and footprint locations routed.
- `pytest -m "not wurth"`: 2355 passed, 26 skipped, 0 failed (Custom submodule and licence-restricted samples absent in the worktree).

## Task Commits

1. **Task 1: end-to-end UL install on an Atomic_ target** - `a2b9e1a` (test)
2. **Task 2: planner, apply, verify, options and kicad-cli tests** - `a70336f` (test)

**Plan metadata:** committed with this summary (docs)

## Files Created/Modified
- `tests/test_install_e2e.py` - Atomic_ targets, `atomic_custom`, helper-built footprint paths and links
- `tests/test_install_plan.py` - same, plus the on-purpose placeholder/case-twin/invalid-name tests left alone
- `tests/test_install_apply.py` - `LIB`/`UL_LIBRARY` on Atomic_ names, hand-plan footprint folder and link through the helper
- `tests/test_install_options_clear.py` - UL target and its layout footprint library
- `tests/test_install_verify.py` - `LIB`, `make_plan` footprint folder and Footprint links through the helper
- `tests/test_kicad_cli.py` - `load_gate` library name moved to `Atomic_Analog` (its `footprints=` arguments stay)

## Decisions Made
See key-decisions. Names left unchanged (backup stamp folders, "elsewhere" symbol libraries in the verify tests) are not install targets, so no rule requires changing them and the acceptance greps do not cover them.

## Deviations from Plan

None - plan executed exactly as written. The line endings of the files (CRLF in the working tree) were preserved.

## Issues Encountered
- The `git -C Custom status --short` acceptance check cannot run here because the Custom submodule is not checked out in the worktree; the conftest session guard and the orchestrator's post-merge run cover it. All writes in these tests stay under tmp_path.
- `test_library_pair_completed_pretty_missing` (IMU has no footprint folder) will need attention in plan 10-12 once footprints live in a shared library that exists; it holds under today's planner.

## Known Stubs
None.

## Threat Flags
None. No new files or surfaces; tests write only under tmp_path (T-10-37).

## Next Phase Readiness
Plan 10-10 can rewrite the placeholder, case-twin and sanitize-refusal tests on the name rule; plan 10-12 can change `footprint_library_for` and the planner together.

## Self-Check: PASSED
