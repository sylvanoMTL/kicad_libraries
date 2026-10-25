---
phase: 08-test-isolation-and-kicad-10
plan: 01
subsystem: testing
tags: [pytest, kicad-cli, kicad-10, fixtures, sexpr]

requires:
  - phase: 04-install
    provides: installfixtures byte builders and the kicad_cli wrapper (run_cli, locate_kicad_cli)
provides:
  - tests/clifixtures.py single KiCad 10 gate (check_kicad_cli, cached located_kicad_cli) with stated skip reasons
  - conftest kicad_cli_path (gate-backed) and shared real_tools fixtures
  - target_lib(20251024) KiCad 10 house style, proven a fixed point of real kicad-cli 10
affects: [08-02, 08-03, 08-04, 08-05, 08-06]

plan_head_before: 5fd6d265350a6c0a2a7cd383cd5105c369442510
plan_head_after: 203d0c73f68326fe9559f5fd8aed6304d19f7dde

actuals:
  tokens: 9000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "One cached gate decides 'is this kicad-cli major 10' and returns (exe, reason); fixtures skip with the reason"
    - "Byte builders are checked once against real kicad-cli output as a fixed point (line endings normalised)"

key-files:
  created:
    - tests/clifixtures.py
    - tests/test_clifixtures.py
  modified:
    - tests/conftest.py
    - tests/test_kicad_cli.py
    - tests/installfixtures.py
    - tests/test_installfixtures.py
    - pyproject.toml

key-decisions:
  - "Gate probes `kicad-cli version` through the app's own run_cli (argv list, no shell, 30 s timeout) and never falls back to another install"
  - "Fake-runner constants in test_kicad_cli.py (20241209) left untouched per D-07; only real-binary tests use the 20251024 constant"
  - "KiCad 10 builder is a separate branch with its own helpers, not the 8/9 helpers with a bumped number"

patterns-established:
  - "Real-binary tests take kicad_cli_path from conftest; module-local real_exe fixtures are gone"

requirements-completed: [TEST-02, TEST-01]

coverage:
  - id: D1
    description: "Every real-binary test gets kicad-cli through one gate that skips with a stated reason unless the major version is 10"
    requirement: TEST-02
    verification:
      - kind: unit
        ref: "tests/test_clifixtures.py (9 tests: not found, 10 ok, 9, 11, unparsable, blank, non-zero exit, OSError, timeout)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The three real-binary tests in tests/test_kicad_cli.py pass against kicad-cli 10.0.7 and expect format 20251024"
    requirement: TEST-02
    verification:
      - kind: integration
        ref: "pytest tests/test_kicad_cli.py -m kicad_cli (3 passed)"
        status: pass
    human_judgment: false
  - id: D3
    description: "target_lib(20251024) is a fixed point of real kicad-cli 10 sym upgrade --force"
    requirement: TEST-01
    verification:
      - kind: integration
        ref: "tests/test_installfixtures.py#test_target_lib_20251024_is_what_kicad_10_writes"
        status: pass
      - kind: unit
        ref: "tests/test_installfixtures.py#test_target_lib_20251024_carries_the_kicad_10_symbol_children"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-10-25
status: complete
---

# Phase 8 Plan 01: KiCad 10 gate and 20251024 target-library builder Summary

**One cached kicad-cli major-10 gate with stated skip reasons now backs every real-binary test, and `target_lib(20251024)` reproduces what kicad-cli 10.0.7 writes byte for byte.**

## Performance

- **Duration:** about 15 min
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments

- `tests/clifixtures.py`: `check_kicad_cli(exe, *, runner=None)` returns `(exe, "")` only for major 10, else `(None, reason)` with distinct reasons for not found, not runnable (Issue, non-zero exit, OSError, timeout), and a wrong or unparsable version. `located_kicad_cli()` is `functools.cache`d, locates the binary as the app does, and probes once per session.
- `tests/conftest.py`: `kicad_cli_path` skips with the gate's reason; new shared `real_tools` fixture. Module-local `real_tools` copies elsewhere still override it until plans 08-04 and 08-05.
- `tests/test_kicad_cli.py`: `real_exe` removed; the three `kicad_cli` tests use `kicad_cli_path`; the deterministic-upgrade test expects `KICAD_SYMBOL_FORMAT` (20251024). Fake-runner tests and `SYM_UP` untouched.
- `tests/installfixtures.py`: `V10_VERSION = 20251024` and a KiCad 10 branch of `target_lib` (`_v10_property`, `_v10_pin`, `_v10_symbol`), documented as a third house style. The real-binary check passed on the first run with the RESEARCH Pattern 4 shape, so no shape difference needed recording.
- `pyproject.toml`: `kicad_cli` marker text names kicad-cli 10.

## Task Commits

1. **Task 1: One KiCad 10 gate, wired through test_kicad_cli.py** - `2b3ac5e` (feat)
2. **Task 2: Unit tests for every gate reason, marker text** - `bc39092` (test)
3. **Task 3: 20251024 house style in target_lib**
   - RED: `6ba2f35` (test)
   - GREEN: `203d0c7` (feat)

**Plan metadata:** the docs(08-01) commit that adds this file.

## TDD notes

- Task 3 followed RED/GREEN: the RED commit fails at collection with `ImportError: cannot import name 'V10_VERSION' from 'installfixtures'`. This is a load failure rather than an assertion failure on the target test, so it is weak RED evidence by the strict #3770 rule; it does show the feature was absent. After GREEN, one of my own assertions needed a fix (Node atoms have `head None`), then all 51 tests in the module passed.
- Task 2 had no separate RED: its unit tests exercise `check_kicad_cli`, which the tracer task (Task 1) had already implemented, so the tests were green on first run. Flagged here as a deviation from strict TDD ordering that the plan itself imposed (the tracer has to land the gate first).

## Verification

- `pytest tests/test_kicad_cli.py tests/test_clifixtures.py tests/test_installfixtures.py tests/test_manifests.py -q`: 119 passed, no skips.
- `pytest -m kicad_cli tests/test_kicad_cli.py tests/test_installfixtures.py -q`: 4 passed.
- `git diff --stat 12e05e3 -- kicad_lib_manager`: empty (no application changes).
- Run with the orchestrator checkout's interpreter against this worktree's code (`C:/Git_Repo_Clones/Kicad_Libraries-importer/env/Scripts/python.exe`).

## Deviations from Plan

None - plan executed exactly as written. Small notes: the gate imports `Issue` from `kicad_lib_manager.models` instead of via `kicad_cli.Issue` (same class, cleaner import), and the plan's "no skipped" checks held because kicad-cli 10.0.7 is installed here.

## Issues Encountered

None. The worktree has no `Custom/` checkout; none of this plan's tests need it. Failures outside this plan's files (the 14 `Custom/`-sample failures and the other KiCad 9 real-binary tests) were not touched and belong to plans 08-02 to 08-06.

## Known Stubs

None.

## Threat Flags

None. The gate runs only `kicad-cli version` via `run_cli` (argv list, no shell, 30 s timeout) on a binary found by the app's `locate_kicad_cli`.

## Next Phase Readiness

Plan 08-02 can build the synthetic `Custom/` on `target_lib(20251024)`, and plans 08-04 and 08-05 can delete their module-local `real_tools` copies and rely on the shared fixture.

## Self-Check: PASSED

- Created files present: tests/clifixtures.py, tests/test_clifixtures.py
- Commits present: 2b3ac5e, bc39092, 6ba2f35, 203d0c7 (all ancestors of HEAD)
