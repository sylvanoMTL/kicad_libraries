---
phase: 08-test-isolation-and-kicad-10
plan: 05
subsystem: testing
tags: [pytest, kicad-cli-10, fixtures, test-isolation, planner]

requires:
  - phase: 08-test-isolation-and-kicad-10
    provides: "08-01 KiCad 10 gate (real_tools / kicad_cli_path) and 20251024 target_lib; 08-02 synthetic_custom fixture and live Custom/ guard"
provides:
  - "tests/test_install_plan.py real-binary tests on the shared real_tools gate with KiCad 10 expectations"
  - "No module-local kicad-cli lookup or real_tools copy in test_install_plan.py, test_vendor_install.py, test_real_vendor_samples.py"
  - "test_install_plan.py UL-plan tests on synthetic_custom; no read or copy of the live Custom/"
affects: [08-06]

plan_head_before: 6fa6944abd96ac00811c549ab96a487820c3258b
plan_head_after: 03a1c7c2636549dd29f819cecd3089219a3b443f

actuals:
  tokens: 4000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Real-binary tests take the shared real_tools fixture; they skip with a stated reason unless kicad-cli is major 10"

key-files:
  created: []
  modified:
    - tests/test_install_plan.py
    - tests/test_vendor_install.py
    - tests/test_real_vendor_samples.py

key-decisions:
  - "Fake-runner tests keep V9 (20241209) targets and FakeCli(output_version=V9); only the four real-binary tests moved to KICAD_SYMBOL_FORMAT (D-06, D-07)"
  - "The live Custom/Footprints snapshot in test_library_pair_completed_pretty_missing was dropped; the 08-02 session guard supersedes it"

requirements-completed: [TEST-02, TEST-01]

coverage:
  - id: D1
    description: "The four real-binary tests in test_install_plan.py (five test items) pass on kicad-cli 10.0.7 against 20251024 targets and the (version 20251024) / (generator_version \"10.0\") header"
    requirement: TEST-02
    verification:
      - kind: integration
        ref: "pytest tests/test_install_plan.py -m kicad_cli (5 passed, 0 skipped)"
        status: pass
    human_judgment: false
  - id: D2
    description: "No test module keeps its own kicad-cli lookup; all real-binary tests get the binary from the shared gate"
    requirement: TEST-02
    verification:
      - kind: integration
        ref: "pytest tests/test_vendor_install.py tests/test_real_vendor_samples.py -m kicad_cli -rs (3 passed, 2 skipped for absent licence-restricted samples, no skip mentions kicad-cli)"
        status: pass
    human_judgment: false
  - id: D3
    description: "test_install_plan.py UL-plan tests run on the synthetic Custom/; test_model_changed_after_plan_is_refused_by_apply passes"
    requirement: TEST-01
    verification:
      - kind: integration
        ref: "pytest tests/test_install_plan.py (137 passed)"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-10-25
status: complete
---

# Phase 8 Plan 05: Real-binary planner tests on KiCad 10 and synthetic Custom/ Summary

**The four real-binary planner tests now expect KiCad 10 (20251024, generator_version "10.0") through the shared gate, the last two module-local kicad-cli lookups are gone, and every Ultra Librarian plan test in test_install_plan.py runs on the code-built synthetic Custom/.**

## Performance

- **Duration:** about 10 min
- **Tasks:** 2 (1 tracer, 1 auto)
- **Files modified:** 3 (0 created, 3 modified)
- **Commits:** 2 task commits

## Accomplishments

- `tests/test_install_plan.py`: the `_real_tools()` helper is deleted. `test_version_real_cli_into_20251024` (renamed from `..._20241209`), `test_library_real_cli_new_header`, `test_unit_real_cli_loads_in_kicad` (2 parametrised items) and `test_noop_second_plan_after_normalised_apply` take the shared `real_tools` fixture and build targets with `KICAD_SYMBOL_FORMAT`. The header test asserts `f"(version {KICAD_SYMBOL_FORMAT})"` and `f'(generator_version "{KICAD_GENERATOR_VERSION}")'`. The unused `find_kicad_footprint_dir` import was removed.
- `tests/test_vendor_install.py`, `tests/test_real_vendor_samples.py`: module-local `real_tools` fixtures deleted along with their now-unused `detect_tools` / `find_kicad_footprint_dir` imports; the shared conftest fixture (gated on kicad-cli 10) is used. No assertion changed.
- `tests/test_install_plan.py`: all 35 `custom_copy` uses became `synthetic_custom`; `test_library_pair_completed_pretty_missing` lost its live `Custom/Footprints` snapshot and `snapshot` parameter (the 08-02 session guard covers it), and its comment now says the synthetic IMU library has no `.pretty` by construction.
- RESEARCH Assumption A6 holds: `test_unit_real_cli_loads_in_kicad` passes on a 20251024 target.

## Task Commits

1. **Task 1: Real-binary tests on the shared gate, retargeted at KiCad 10** - `227c278` (test, tracer)
2. **Task 2: UL-plan tests on the synthetic Custom/** - `03a1c7c` (test)

**Plan metadata:** the docs(08-05) commit that adds this file.

## Verification

- `pytest tests/test_install_plan.py -m kicad_cli -q`: 5 passed, no skips.
- `pytest tests/test_vendor_install.py tests/test_real_vendor_samples.py -m kicad_cli -q -rs`: 3 passed, 2 skipped. Both skips are `test_real_vendor_installs_load_in_kicad` cases whose licence-restricted SnapEDA / SamacSys zips are absent from `downloaded_examples/` ("kept local"); neither mentions kicad-cli.
- `pytest tests/test_install_plan.py tests/test_vendor_install.py tests/test_real_vendor_samples.py -q -rs`: 161 passed, 10 skipped. All 10 skips are the same licence-restricted sample files in `test_real_vendor_samples.py`; none mention kicad-cli.
- `pytest` of `test_model_changed_after_plan_is_refused_by_apply` and `test_library_pair_completed_pretty_missing`: 2 passed.
- Acceptance greps: no `_real_tools`, no module-local `def real_tools`, no `generator_version "9.0"`, no V9 `("EXISTING_A",)` target, no `custom_copy` / `real_before`; `V6, V8, V9 = ...` line intact. D-07 check against `12e05e3`: 7 `_target_layout(tmp_path, V9)` and 3 `FakeCli(output_version=V9)` before and after. Rename count: 35 `custom_copy` before, 35 `synthetic_custom` after. Assertion diff against `12e05e3` shows no changed `assert` line outside the rename, snapshot removal and KiCad 10 retargets.
- `git diff --stat 12e05e3 -- kicad_lib_manager`: empty (no application changes).
- Run with the orchestrator checkout's interpreter against this worktree's code.

## Deviations from Plan

None - plan executed exactly as written. Note: the `<verify>` for Task 1 in the plan expects "no skipped" for test_install_plan.py and "no skip reason mentions kicad-cli" for the other two modules; both held.

## Issues Encountered

- The licence-restricted vendor samples are absent from `downloaded_examples/` in this worktree, so 10 tests in `test_real_vendor_samples.py` skip with their own stated reason (including the two real-binary cases). Their kicad-cli 10 path is therefore not exercised here; the orchestrator's post-merge run on the owner's checkout (where the samples live) will cover it. The module-local `real_tools` removal there is covered by the same fixture the three passing `test_vendor_install.py` real-binary cases use.
- git warns about LF-to-CRLF conversion on `tests/test_install_plan.py`; harmless (repo autocrlf).

## Known Stubs

None.

## Threat Flags

None. T-08-08 mitigated: no test module locates kicad-cli on its own; the binary comes from the shared major-10 gate. T-08-09 mitigated: UL-plan tests write to `synthetic_custom` or their own tmp layouts, and the live-tree snapshot is replaced by the session guard.

## Next Phase Readiness

Plan 08-06 can remove the now-unused `custom_copy` fixture from conftest.py as far as this file is concerned (no `custom_copy` use remains in `tests/test_install_plan.py`), and run the repo-wide check that no test module locates kicad-cli itself.

## Self-Check: PASSED

- Modified files present: tests/test_install_plan.py, tests/test_vendor_install.py, tests/test_real_vendor_samples.py
- Commits present: 227c278, 03a1c7c (ancestors of HEAD)
