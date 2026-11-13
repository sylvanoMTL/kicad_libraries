---
phase: 10-importer-on-the-atomic-scheme
plan: 02
subsystem: testing
tags: [pytest, fixtures, synthetic-custom, atomic-naming]

requires:
  - phase: 09-atomic-library-check
    provides: atomic fixture inventory in tests/customfixtures.py
provides:
  - atomic_custom fixture (synthetic Custom/ with Atomic_ install targets)
  - footprint_library_for routing helper for install-target footprint locations
  - CURRENT_ATOMIC_SYMBOL_LIBS / CURRENT_ATOMIC_FOOTPRINT_LIBS
  - write_synthetic_custom(root, naming="v1"|"atomic")
affects: [10-07, 10-08, 10-09, 10-10, 10-12, 13]

actuals:
  tokens: 9000
  tasks: 2
  commits: 2
plan_head_before: 1db839994d9eca570bde31eb0595160af4b2209e
plan_head_after: f62e92eaf963bd7291284a83b372d2e534b56e32

tech-stack:
  added: []
  patterns:
    - "Tests name an install target's footprint library only through footprint_library_for, so plan 10-12 changes one rule"
    - "Default synthetic_custom keeps the v1 live-tree mirror; atomic_custom is opt-in"

key-files:
  created: []
  modified:
    - tests/zipfixtures.py
    - tests/customfixtures.py
    - tests/conftest.py
    - tests/test_customfixtures.py
    - tests/test_zipfixtures.py
    - tests/test_install_e2e.py

key-decisions:
  - "Name constants (BATTERY_CHARGER and friends) now hold the Atomic_ targets; v1 names live in SyntheticLibrary.v1_name and V1_* constants"
  - "footprint_library_for returns the library itself until plan 10-12 switches it to the shared Atomic_Footprints"

requirements-completed: [LIB-05, LIB-06]

coverage:
  - id: D1
    description: "write_synthetic_custom keeps the v1 tree by default, writes Atomic_ names with naming='atomic', and rejects any other naming"
    requirement: LIB-05
    verification:
      - kind: unit
        ref: "tests/test_customfixtures.py#test_naming_v1_writes_exactly_the_v1_names"
        status: pass
      - kind: unit
        ref: "tests/test_customfixtures.py#test_naming_atomic_writes_the_atomic_names"
        status: pass
      - kind: unit
        ref: "tests/test_customfixtures.py#test_naming_other_raises"
        status: pass
    human_judgment: false
  - id: D2
    description: "An Atomic_ install target plans end to end through build_plan with its footprint location and Footprint field taken from footprint_library_for"
    requirement: LIB-06
    verification:
      - kind: integration
        ref: "tests/test_customfixtures.py#test_atomic_install_target_plans_through_footprint_library_for"
        status: pass
    human_judgment: false
  - id: D3
    description: "CURRENT_ATOMIC_SYMBOL_LIBS and CURRENT_ATOMIC_FOOTPRINT_LIBS beside the unchanged v1 CURRENT_CUSTOM_* mirrors"
    requirement: LIB-05
    verification:
      - kind: unit
        ref: "tests/test_zipfixtures.py#test_current_atomic_lists"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 02: Atomic_ test fixtures Summary

**An `atomic_custom` synthetic Custom/ with Atomic_ install targets beside the unchanged v1 tree, and one `footprint_library_for` helper that plan 10-12 can switch to the shared Atomic_Footprints.**

## Performance

- **Duration:** about 35 min (dominated by two test runs, the full suite takes 10 min)
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- `write_synthetic_custom(root, *, naming="v1")` writes today's v1 tree by default and the Atomic_ names with `naming="atomic"`; footprints go to `footprint_library_for(library).pretty`; any other value raises ValueError.
- `atomic_custom` fixture in `tests/conftest.py`; `synthetic_custom` and the session guard are untouched.
- Tracer test plans an install into `Atomic_Battery_Management` through `build_plan` and checks the footprint path and the symbol's Footprint field against `footprint_library_for`.
- `CURRENT_ATOMIC_SYMBOL_LIBS` (nine Phase 13 targets) and `CURRENT_ATOMIC_FOOTPRINT_LIBS` added without pinning any value of `footprint_library_for`.
- `-m "not wurth"` suite: 2316 passed, 26 skipped (Custom submodule and licence-restricted samples absent in the worktree).

## Task Commits

1. **Task 1: tracer, atomic_custom, footprint_library_for** - `b1b34ac` (feat)
2. **Task 2: Atomic_ layout constants and naming tests** - `f62e92e` (test)

**Plan metadata:** committed with this summary (docs)

## Files Created/Modified
- `tests/zipfixtures.py` - `footprint_library_for`, `CURRENT_ATOMIC_SYMBOL_LIBS`, `CURRENT_ATOMIC_FOOTPRINT_LIBS`
- `tests/customfixtures.py` - `v1_name` field, `V1_*` constants, `V1_LIBRARY_NAMES`, naming switch in `write_synthetic_custom`, Atomic_ name constants
- `tests/conftest.py` - `atomic_custom` fixture
- `tests/test_customfixtures.py` - v1 assertions moved to `v1_name`, tracer test, naming tests
- `tests/test_zipfixtures.py` - Atomic_ list tests, twice-named footprint library test
- `tests/test_install_e2e.py` - switched to the `V1_POWER_MOSFET` / `V1_WIRELESS` constants (see deviation)

## Decisions Made
- Added individual `V1_BATTERY_CHARGER`, `V1_IMU`, `V1_MAGNETOMETER`, `V1_POWER_MOSFET`, `V1_WIRELESS` constants next to the Atomic_ ones, so v1-tree tests name their library without indexing a tuple.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] test_install_e2e.py used the retargeted constants against the v1 tree**
- **Found during:** Task 1
- **Issue:** The plan retargets `POWER_MOSFET` and `WIRELESS` to Atomic_ names, but `tests/test_install_e2e.py` (not in the plan's file list) installs into the default v1 tree with them. It would have failed wherever the real tools run, breaking "no test result changes".
- **Fix:** Replaced those names with `V1_POWER_MOSFET` and `V1_WIRELESS` in that file (13 lines); behaviour is identical.
- **Files modified:** tests/test_install_e2e.py
- **Verification:** `tests/test_install_e2e.py` 90 passed with the customfixtures and zipfixtures tests; full not-wurth suite green.
- **Committed in:** b1b34ac

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Needed to keep the suite green; one file touched beyond the plan's list of five.

## Issues Encountered
- The `git -C Custom status` acceptance check cannot run in the worktree because the Custom submodule is not checked out; the session guard in conftest (untouched) covers it, and the orchestrator's post-merge run in the main checkout covers the live tree.
- Plan-level ledger file for commit counting was not created before the first commit; the base was taken from the spawn HEAD (1db8399), so `commits: 2` is still measured with `git rev-list --count`.

## Known Stubs
None.

## Threat Flags
None. The fixtures write only under tmp_path; a test asserts nothing is written outside the root (T-10-04).

## Next Phase Readiness
Plans 10-07 to 10-09 can move install tests to `atomic_custom` and route footprint locations through `footprint_library_for`; plan 10-12 changes that one function together with the planner.

## Self-Check: PASSED
