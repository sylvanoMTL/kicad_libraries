---
phase: 08-test-isolation-and-kicad-10
plan: 02
subsystem: testing
tags: [pytest, fixtures, kicad-cli-10, test-isolation, write-guard]

requires:
  - phase: 08-test-isolation-and-kicad-10
    provides: "tests/clifixtures.py KiCad 10 gate (kicad_cli_path fixture) and the 20251024 house style in installfixtures.target_lib"
provides:
  - "tests/customfixtures.py: write_synthetic_custom(root), SYNTHETIC_LIBRARIES inventory, name constants, digest and guard helpers"
  - "synthetic_custom conftest fixture: RepoLayout over an isolated Custom/ built in code, no copy of the checkout"
  - "_live_custom_untouched session guard: a pytest run that changes the live Custom/ fails with the changed paths"
affects: [08-03, 08-04, 08-05, 08-06, phase-10 Atomic_ libraries]

plan_head_before: 117153e0cc4bb36f6c1b11fff13e97b2bbd6f085
plan_head_after: 55fc72359377fc11992fe2b5319fe01402a493b1

actuals:
  tokens: 11000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Format-mirror test tree built from byte builders under tmp_path, never copied from the checkout"
    - "Generator-style guard (yield from guard_custom(...)) so a session fixture and a subprocess test share one implementation"

key-files:
  created:
    - tests/customfixtures.py
    - tests/test_customfixtures.py
  modified:
    - tests/conftest.py
    - tests/test_commit_plan.py

key-decisions:
  - "SYNTHETIC_LIBRARIES is the single inventory source; Phase 10 appends Atomic_ libraries to it"
  - "digest_custom also records the three watched top-level folders as 'Symbols/' etc., so a deleted or newly created top-level folder is reported"
  - "pytest.fail(..., pytrace=False) in the guard teardown keeps the report to the changed-path message"
  - "The old custom_copy fixture is left in place (plan 08-06 removes it once every user has moved)"

requirements-completed: [TEST-01, TEST-03]

coverage:
  - id: D1
    description: "Synthetic Custom/ written in code: four symbol format versions, v1 library names, IMU without .pretty, IC_MOSFET_Dual_TI absent, no Ultra Librarian sample part anywhere"
    requirement: TEST-01
    verification:
      - kind: unit
        ref: "tests/test_customfixtures.py (13 tests, e.g. test_all_four_format_versions_are_present, test_ul_sample_part_is_absent_by_construction)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every synthetic symbol library and footprint loads in real kicad-cli 10 with no issues"
    requirement: TEST-01
    verification:
      - kind: integration
        ref: "tests/test_customfixtures.py::test_every_synthetic_library_loads_in_kicad_cli"
        status: pass
    human_judgment: false
  - id: D3
    description: "test_build_from_real_ul_plan runs on the synthetic Custom/ whatever the live Custom/ holds"
    requirement: TEST-01
    verification:
      - kind: unit
        ref: "tests/test_commit_plan.py::test_build_from_real_ul_plan"
        status: pass
    human_judgment: false
  - id: D4
    description: "A pytest run that changes the live Custom/Symbols, Footprints or 3DModels exits non-zero and names the changed paths"
    requirement: TEST-03
    verification:
      - kind: integration
        ref: "tests/test_customfixtures.py::test_guard_failure_fails_the_run (subprocess pytest)"
        status: pass
      - kind: integration
        ref: "tests/test_customfixtures.py::test_guard_quiet_run_passes (subprocess pytest)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-25
status: complete
---

# Phase 8 Plan 02: Synthetic Custom/ and live write-protect guard Summary

**A code-built format-mirror Custom/ (four symbol format versions, v1 names, no Ultra Librarian part) exposed as `synthetic_custom`, plus a session guard that fails any pytest run that changes the live Custom/, with the failure path proven through a subprocess.**

## Performance

- **Duration:** about 25 min
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 4 (2 created, 2 modified)
- **Commits:** 4 task commits (feat, test, test, feat)

## Accomplishments

- `tests/customfixtures.py` writes five libraries under any root: IC_Battery_Charger_TI (20211014, 2 symbols, 2 footprints, 1 model), IC_IMU_TDK (20231120, symbols only, no `.pretty`), IC_Magnetometer_Memsic and IC_PowerManagementMosfet_TI (20241209), IC_Wireless_BLE_uBlox (20251024). The names `CSD85301Q2`, `DQK0006B`, `DLV0006A` appear nowhere in paths or content, and `IC_MOSFET_Dual_TI` does not exist.
- `synthetic_custom` returns the same `RepoLayout` type the live-copy fixture returned. `test_commit_plan.py::test_build_from_real_ul_plan` now uses it, so it no longer depends on the owner's parts (all 27 tests in that module pass).
- All five synthetic libraries and their footprints load in the real kicad-cli 10 with no issues.
- `_live_custom_untouched` (session, autouse) digests Symbols, Footprints and 3DModels of the live `Custom/` before and after the run and calls `pytest.fail("the test run changed the live Custom/ folder: ...")` listing the first ten changed paths. Two subprocess tests prove a touching run exits non-zero with the path named and a quiet run exits 0 (Assumption A5 proven, not assumed).
- `snapshot` now returns `customfixtures.digest_tree`, the shared body.

## Task Commits

1. **Task 1: Synthetic Custom/, `synthetic_custom`, proven on test_build_from_real_ul_plan** - `f1f039a` (feat, tracer)
2. **Task 2: Contract tests for the synthetic Custom/** - `bebdca4` (test)
3. **Task 3 RED: failing tests for the guard** - `e2a612f` (test)
4. **Task 3 GREEN: guard implementation and session fixture** - `55fc723` (feat)

**Plan metadata:** committed separately as `docs(08-02)` (this SUMMARY).

## Files Created/Modified

- `tests/customfixtures.py` - synthetic Custom/ writer, inventory and constants, digest and guard helpers
- `tests/test_customfixtures.py` - 22 tests: 13 contract tests (one marked `kicad_cli`), digest and change tests, subprocess guard tests
- `tests/conftest.py` - `synthetic_custom`, `_live_custom_untouched`, `snapshot` delegating to `digest_tree`; unused `hashlib` import dropped
- `tests/test_commit_plan.py` - `test_build_from_real_ul_plan` on `synthetic_custom`

## Decisions Made

- `SYNTHETIC_LIBRARIES` is the one inventory; later phases append to it rather than add a second list.
- `digest_custom` records the watched top-level folders themselves (`Symbols/`, `Footprints/`, `3DModels/`) so deleting or creating one of them is reported.
- The old `custom_copy` fixture stays until plan 08-06.

## TDD Gate Compliance

- **Task 1 (tracer):** committed as `feat` with its own verify (`tests/test_commit_plan.py`, 27 passed, no skips).
- **Task 2:** the tests exercise code written in the Task 1 tracer, so there is no RED phase for them; they were green on the first run (after fixing one test bug: `footprint_name` returns a `NameRef`, so the test compares `.name`). Committed as `test(08-02)` only. No implementation commit follows it because none was needed. This is an expected consequence of the plan placing the implementation in the tracer task.
- **Task 3:** RED commit `e2a612f`: 9 target tests failed. Semantic assessment of the RED evidence: six failed with `ImportError: cannot import name 'digest_tree' / 'digest_custom' / 'custom_changes' / 'guard_custom'` (the planned functions did not exist), and the two subprocess tests failed because the child process could not import `guard_custom` (exit code 4). These are import-level failures of the missing feature, not assertion failures on behaviour, so the strict INVALID_RED classifier (`gsd check tdd-red-evidence`) was not run: the repo does not enable `workflow.tdd_mode`, and no unittest/TAP/JUnit report in a supported format was captured. GREEN commit `55fc723`: all 22 tests in the module pass. No REFACTOR commit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Renamed a guard test so the plan's `-k guard` check reports exactly "2 passed"**
- **Found during:** Task 3 verification
- **Issue:** the extra test for the absent/empty Custom/ case was named `test_guard_does_nothing_...`, so `-k guard` selected 3 tests and the plan's check ("summary line has 2 passed") would read "3 passed".
- **Fix:** renamed it `test_watching_an_absent_or_empty_custom_is_a_no_op`; the two named guard tests are the only `-k guard` matches.
- **Files modified:** tests/test_customfixtures.py
- **Committed in:** 55fc723

**2. [Rule 1 - Bug] Contract test compared a NameRef to a string**
- **Found during:** Task 2
- **Fix:** compare `footprint_name(root).name`.
- **Committed in:** bebdca4

---

**Total deviations:** 2 auto-fixed (both test-code defects found by the first run). **Impact on plan:** none. No application code under `kicad_lib_manager/` was changed.

## Issues Encountered

- A full-suite run in this worktree (`-x`) stopped at `tests/test_install_plan.py::test_version_real_cli_into_20241209` after 750 passed and 60 skipped. This is one of the 6 pre-existing KiCad 9 expectation failures named in the dispatch (fixed by plans 08-03..08-05), not caused by this plan. A full unstopped run was not repeated.
- Tests backed by the live `Custom/` skip in this worktree with "Custom submodule not checked out"; expected. The new guard is a no-op here (Custom/ is empty). The guard's absent/empty case is covered by `test_watching_an_absent_or_empty_custom_is_a_no_op`, and the failing and quiet cases by tmp_path trees. The guard has not been exercised against the real checkout's `Custom/` (about 20 MB, 1.6 s hash per run); the orchestrator's post-merge full run will do that.
- `git status` warns about LF-to-CRLF conversion on the new files (the repo's autocrlf setting); harmless.

## Known Stubs

None.

## Threat Flags

None. The guard subprocess test writes only under `tmp_path` and runs the child with `-p no:cacheprovider` (T-08-03, T-08-04 mitigated as planned).

## Next Phase Readiness

- Plans 08-03..08-06 can switch their `custom_copy` tests to `synthetic_custom`; `custom_copy` is still defined and untouched.
- Library-name constants (`BATTERY_CHARGER`, `POWER_MOSFET`, `WIRELESS`, `ABSENT_LIBRARY`, ...) are importable from `customfixtures`.

## Self-Check: PASSED

- tests/customfixtures.py, tests/test_customfixtures.py found; commits f1f039a, bebdca4, e2a612f, 55fc723 are ancestors of HEAD.
- `pytest tests/test_customfixtures.py tests/test_commit_plan.py tests/test_installfixtures.py -q`: 100 passed, no skips.
- `pytest tests/test_customfixtures.py -m kicad_cli -q`: 1 passed, no skip. `-k guard`: 2 passed.

---
*Phase: 08-test-isolation-and-kicad-10*
*Completed: 2026-10-25*
