---
phase: 08-test-isolation-and-kicad-10
plan: 04
subsystem: testing
tags: [pytest, kicad-cli-10, test-isolation, version-scenarios, uat-hook]

requires:
  - phase: 08-test-isolation-and-kicad-10
    provides: "kicad_cli_path / real_tools gate and 20251024 target_lib (08-01); synthetic_custom, customfixtures constants and the live-Custom/ session guard (08-02)"
provides:
  - "VER-01 scenario target_20241209_as_is_with_warning: 20241209 target on kicad-cli 10 installs as-is with one D-01 warning, unchanged header and vendor block, clean load gate"
  - "tests/test_install_e2e.py fully on synthetic_custom; no read of the live Custom/ left in the file"
  - "KiCad 10 retargets of the older-incoming, new-library and second-install real-binary tests"
  - "test_uat_scratch_install retargeted at a synthetic 20241209 scratch library built outside the repository"
affects: [08-06, phase-10]

plan_head_before: 6fa6944abd96ac00811c549ab96a487820c3258b
plan_head_after: 217be843383e43a9e59d4cf99218c708d7460544

actuals:
  tokens: 7000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Real-binary scenarios keyed by name in _SCENARIOS, each followed by the real load gate"
    - "Manual hook builds its scratch Custom/ from the synthetic writer, never from the checkout"

key-files:
  created: []
  modified:
    - tests/test_install_e2e.py

key-decisions:
  - "VER-01 header check compares the header slice only (bytes before the first symbol), since the whole file grows by the new block"
  - "The scenario also asserts the load gate returns no issues at all (stricter than the runner's no-ERROR check)"
  - "The incoming-newer scenario uses vendor_symbol_lib(\"MMC5983MA\", version=20241209) so no live or synthetic library bytes are read"

requirements-completed: [VER-01, TEST-02, TEST-01]

coverage:
  - id: D1
    description: "A 20241209 target on kicad-cli 10 takes the as-is-with-warning row: one install.version_mismatch WARNING naming 20211014, 20241209 and 20251024, header unchanged, vendor block (with ids) unchanged, load gate clean"
    requirement: VER-01
    verification:
      - kind: integration
        ref: "tests/test_install_e2e.py::test_cli_version_scenarios[target_20241209_as_is_with_warning]"
        status: pass
    human_judgment: false
  - id: D2
    description: "The real-binary scenarios expect KiCad 10: older incoming normalised into the 20251024 library, new library gets (version 20251024) and generator_version 10.0, second install is a no-op, incoming-newer is refused from a synthetic vendor symbol"
    requirement: TEST-02
    verification:
      - kind: integration
        ref: "pytest tests/test_install_e2e.py -m kicad_cli (8 passed, no skips)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every writing test in the file uses the synthetic Custom/; test_ul_symbol_added_others_identical and test_sc4_fail_on_each_write[3] pass"
    requirement: TEST-01
    verification:
      - kind: unit
        ref: "pytest tests/test_install_e2e.py (27 passed, 1 skipped)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Owner opens the scratch 20241209 library in KiCad 10's Symbol Editor and places CSD85301Q2 (D-08 manual half)"
    requirement: VER-01
    verification: []
    human_judgment: true
    rationale: "Needs the KiCad 10 GUI (Symbol Editor and schematic placement); handled by plan 08-06 / /gsd-verify-work 8 through the KICAD_IMPORT_UAT_DIR hook"

duration: 20min
completed: 2026-10-25
status: complete
---

# Phase 8 Plan 04: VER-01 row, KiCad 10 retargets and synthetic UAT hook Summary

**tests/test_install_e2e.py now runs entirely on the synthetic Custom/, asserts the 20241209-target as-is-with-warning row on kicad-cli 10.0.7, expects KiCad 10 in every real-binary scenario, and builds its manual scratch install from the synthetic writer.**

## Performance

- **Duration:** about 20 min
- **Tasks:** 3 (1 tracer, 2 auto)
- **Files modified:** 1
- **Commits:** 3

## Accomplishments

- `_scenario_target_20241209_as_is` (key `target_20241209_as_is_with_warning`): installs the UL sample into synthetic `IC_PowerManagementMosfet_TI` (20241209). Asserts `normalised is False`, `target_version == 20241209`, exactly one `install.version_mismatch` WARNING whose text names 20211014, 20241209 and 20251024, header bytes identical with `(version 20241209)`, vendor block still carrying `(id `, and `_written_gate_issues(...) == []`.
- Whole file moved from `custom_copy` to `synthetic_custom` (39 uses). Removed the module-scoped `_real_custom_untouched` fixture, the live-tree snapshot lines in `test_ul_symbol_added_others_identical`, and the module-local `real_tools` copy (the conftest one is used). The five previously failing tests in this file now pass: `test_ul_symbol_added_others_identical`, `test_sc4_fail_on_each_write[3]`, the older-incoming and new-library scenarios, and the second-install no-op.
- KiCad 10 retargets: older-incoming installs into `WIRELESS` (20251024), new library header expects `(version 20251024)` and `(generator_version "10.0")` through the clifixtures constants, second install uses `WIRELESS`, incoming-newer builds `vendor_symbol_lib("MMC5983MA", version=20241209)`.
- `test_uat_scratch_install(ul_package, real_tools)` writes the synthetic Custom/ under `KICAD_IMPORT_UAT_DIR`, installs into the 20241209 library with kicad-cli 10, checks one mismatch warning and an unchanged `(version 20241209)` header. T-04-28 location asserts and the link check are kept; nothing reads the checkout's Custom/.

## Task Commits

1. **Task 1: VER-01 row on the synthetic Custom/** - `1abe87b` (feat, tracer)
2. **Task 2: KiCad 10 scenario retargets** - `ddf9336` (test)
3. **Task 3: synthetic UAT hook** - `217be84` (test)

## Verification

- `pytest "tests/test_install_e2e.py::test_cli_version_scenarios[target_20241209_as_is_with_warning]"`: 1 passed.
- `pytest tests/test_install_e2e.py -m kicad_cli`: 8 passed, no skips.
- `pytest tests/test_install_e2e.py -q -rs`: 27 passed, 1 skipped (only the KICAD_IMPORT_UAT_DIR hook).
- `pytest tests/test_install_e2e.py -m "not kicad_cli"`: 19 passed, 1 skipped.
- `git diff --stat 12e05e3 -- kicad_lib_manager`: empty (no application changes).
- Acceptance greps from the plan all hold (no `custom_copy`, `_real_custom_untouched`, `real_before`, `copytree`, `generator_version "9.0"`; one `target_version == 20241209`, inside the VER-01 row).
- Ran with the orchestrator checkout's interpreter against this worktree's code.

## Deviations from Plan

None - plan executed exactly as written. The manual UAT hook itself was not run (the dispatch forbids setting `KICAD_IMPORT_UAT_DIR`); its calls are the same ones the VER-01 scenario already exercises, and the owner's run is plan 08-06's job.

## Carry to Phase 10

After the normalised install of the UL sample into the 20251024 library `IC_Wireless_BLE_uBlox`, kicad-cli 10 rewrote the symbol in full KiCad 10 shape, but the app-added Manufacturer and MPN properties are the one-line KiCad 8/9 form with `hide` inside `effects`:

```
(property "Manufacturer" "TI" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
(property "MPN" "CSD85301Q2" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
```

KiCad 10 loads this (the kicad-cli load gate is clean), but the other properties in the same block use the multi-line shape with `(show_name no)`, `(do_not_autoplace no)` and `(hide yes)` as a sibling of `effects`. No assertion was added and no app code changed; Phase 10 may want to align the shape.

## Issues Encountered

None. The worktree has no `Custom/` checkout and none of this file's tests needed it.

## Known Stubs

None.

## Threat Flags

None. The hook still refuses a folder inside or containing the repository and a linked `uat/Custom`; kicad-cli is reached only through the shared `real_tools` gate (major 10 only).

## Self-Check: PASSED

- tests/test_install_e2e.py present; commits 1abe87b, ddf9336, 217be84 are ancestors of HEAD.
