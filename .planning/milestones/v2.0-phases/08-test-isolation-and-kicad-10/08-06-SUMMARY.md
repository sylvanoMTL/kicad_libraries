---
phase: 08-test-isolation-and-kicad-10
plan: 06
subsystem: testing
tags: [pytest, test-isolation, wurth-corpus, kicad-cli-10, uat]

requires:
  - phase: 08-test-isolation-and-kicad-10
    provides: "synthetic_custom, session guard (08-02); migrated test files (08-03..08-05); VER-01 scenario (08-04)"
provides:
  - "tests/conftest.py without the live-copy fixture; nothing in the suite copies the live Custom/"
  - "Proof that the formerly live-dependent tests pass in a repository copy with no Custom/ folder"
  - "WurthElektronik checked out at its pinned commit; its corpus runs on the workstation"
  - "Wurth parse budget sized per file from measured data"
  - "tests/README.md: run commands, live-Custom/ rule, expected-skip table, conditional skips, read-only health checks, Wurth timing"
  - "Bare pytest green: 8063 passed, 3 skipped (all documented)"
  - "08-UAT.md with the VER-01 automated pass and the owner's Symbol Editor check pending"
affects: [verify-work-8, phase-10, phase-13]

plan_head_before: 9fee9fad1ac877ea8e2a994a2dc9a61a02abd3d5
plan_head_after: f326a3379db666e02f92a2f1f0aa399427b8138a

actuals:
  tokens: 9000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Per-file parse budget: max(60 s, 0.05 s x files), measured numbers in a comment above it"
    - "Skip table in tests/README.md mirrors the messages printed by pytest -rs"

key-files:
  created:
    - tests/README.md
    - .planning/phases/08-test-isolation-and-kicad-10/08-UAT.md
  modified:
    - tests/conftest.py
    - tests/test_roundtrip_corpus.py
    - .planning/PROJECT.md
    - .planning/milestones/v1.0-phases/04-plan-and-install-core/04-UAT.md

key-decisions:
  - "Wurth parse budget changed to max(60 s, 0.05 s per file): 6034 files parsed in 69.5 s, over the fixed 60 s"
  - "Records claim only the automated KiCad 10 result; the Symbol Editor check stays pending in 08-UAT.md test 2"

requirements-completed: [TEST-03, TEST-01, VER-01]

coverage:
  - id: D1
    description: "No test copies the live Custom/; the live-copy fixture is gone and the formerly live-dependent tests pass in a repository copy with no Custom/ folder"
    requirement: TEST-01
    verification:
      - kind: integration
        ref: "scratch copy without Custom/: 523 passed, 1 skipped (KICAD_IMPORT_UAT_DIR hook)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Bare pytest on the workstation reports 0 failed and 0 errors; the only skips are the two symlink skips and the KICAD_IMPORT_UAT_DIR skip, each documented in tests/README.md"
    requirement: TEST-03
    verification:
      - kind: e2e
        ref: "env/Scripts/python.exe -m pytest (8063 passed, 3 skipped in 17 min 53 s)"
        status: pass
    human_judgment: false
  - id: D3
    description: "WurthElektronik is checked out at 2e6e51b and its round-trip and stress tests run (6034 files)"
    requirement: TEST-03
    verification:
      - kind: integration
        ref: "pytest -m wurth: 6035 passed after the budget change (parse budget test re-run alone: 1 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "08-UAT.md records the VER-01 automated pass (test 1) and the owner's KiCad 10 Symbol Editor check as pending (test 2); 04-UAT.md and PROJECT.md point to it"
    requirement: VER-01
    verification:
      - kind: other
        ref: "grep checks from the plan's Task 3 verify block"
        status: pass
    human_judgment: true
    rationale: "The Symbol Editor check needs the KiCad 10 GUI and the owner's answer through /gsd-verify-work 8"

duration: 70min
completed: 2026-10-25
status: complete
---

# Phase 8 Plan 06: Live-copy removal, Wurth corpus, README and VER-01 records Summary

**The live-copy fixture is gone, the suite passes with no Custom/ at all, the Wurth corpus runs at its pinned commit under a per-file parse budget, bare pytest is green (8063 passed, 3 documented skips), and 08-UAT.md holds the VER-01 automated pass plus the owner's Symbol Editor check as the one pending test.**

## Performance

- **Duration:** about 70 min (mostly test runs: 2.5 min scratch copy, 8 min quick run, 8.75 min Wurth run, 18 min full run)
- **Started:** 2026-10-25T18:05Z (approx.)
- **Completed:** 2026-10-25T19:25Z (approx.)
- **Tasks:** 3 (1 tracer, 2 auto)
- **Files modified:** 6

## Accomplishments

- Deleted `custom_copy` and the now-unused `shutil` import from `tests/conftest.py`. The three repo-wide greps from the plan are clean (`copytree` remains only in `tests/gitfixtures.py`, the git template).
- Independence proof: the migrated test files (commit plan, import preview, install apply/e2e/plan, import dialog, naming suggest, customfixtures) ran in a `mktemp -d` copy of `tests/`, `kicad_lib_manager/`, `downloaded_examples/` and `pyproject.toml` with no `Custom/` and no `.git`: 523 passed, 1 skipped (the KICAD_IMPORT_UAT_DIR hook).
- Checked out `WurthElektronik/KiCad-Library` at 2e6e51b1bd78f89b31c358214642ba7e795872e0 with `--reference` to the main clone's object store, then repacked and removed the alternates file. `git submodule status` shows the line without a prefix and `git status --short -- WurthElektronik` is empty.
- Measured the Wurth corpus: 6034 files, `test_wurth_corpus_parse_budget` took 69.5 s (71.1 s call time) against the fixed 60 s, so it failed. Replaced with `_WURTH_PARSE_BUDGET_PER_FILE = 0.05` and `budget = max(60.0, 0.05 * len(files))` (about 302 s for this corpus). Re-run alone: 1 passed in 72 s. All 6033 round-trip items and `test_wurth_model_paths_stay_quiet` passed.
- Wrote `tests/README.md`: run commands, the live-`Custom/` rule, the five-row expected-skip table, other conditional skips, the read-only live health checks, and the Wurth timing and budget rule.
- Gate: bare `pytest` reports 8063 passed, 3 skipped in 17 min 53 s, no failures or errors. The skips are the KICAD_IMPORT_UAT_DIR hook (`tests/test_install_e2e.py:580`), `tests/test_model_source.py:201` and `tests/test_package_folder.py:105` (both "symlinks not permitted here: [WinError 1314]"). kicad-cli version captured for the records: 10.0.7.
- Created `08-UAT.md` (test 1 VER-01 automated: pass; test 2 Symbol Editor check: `[pending]`), added the `retest` note and `retested_in` to the archived 04-UAT.md Test 2 (no closed field), and updated the two PROJECT.md Key Decisions rows with automated-only wording.

## Task Commits

1. **Task 1: Remove live-copy fixture, prove independence** - `48e2395` (test)
2. **Task 2: Wurth checkout, per-file budget, tests/README.md** - `6876ac3` (test)
3. **Task 3: Green gate, 08-UAT.md and D-10 records** - `f326a33` (docs)

**Plan metadata:** committed with this SUMMARY (docs: complete plan).

## Files Created/Modified

- `tests/conftest.py` - live-copy fixture and `shutil` import removed
- `tests/test_roundtrip_corpus.py` - `_WURTH_PARSE_BUDGET_PER_FILE` and the per-file budget with measured numbers in a comment
- `tests/README.md` - new suite guide
- `.planning/phases/08-test-isolation-and-kicad-10/08-UAT.md` - UAT file for `/gsd-verify-work 8` to resume
- `.planning/PROJECT.md` - two Key Decisions rows
- `.planning/milestones/v1.0-phases/04-plan-and-install-core/04-UAT.md` - Test 2 retest note and `retested_in`

## Decisions Made

- Budget formula and constant follow the plan exactly; the measured per-file cost (0.012 s) is well under 0.05 s, so the budget is a loose guard, not a tight one. The measured numbers are in the code comment and the README.
- The WurthElektronik gitlink did not move and `kicad_lib_manager/` is unchanged (`git diff --stat 12e05e3 -- kicad_lib_manager` is empty).

## Deviations from Plan

None - plan executed exactly as written. The Task 1 `-m "not wurth"` run happened before the Wurth checkout (2027 passed, 3 skipped, 3 deselected), as the task order requires.

## Issues Encountered

- `tests/conftest.py` has CRLF line endings, so the first scripted edit missed its anchor; redone with CRLF-aware matching.
- VER-01 manual half: pending. The owner's Symbol Editor check is test 2 of `08-UAT.md`; `/gsd-verify-work 8` resumes that file and records the owner's result, which is what closes backlog 999.1.
- Carry-over from 08-04 (not touched here): Phase 10 may want to align the one-line `Manufacturer`/`MPN` property shape that the app adds to a KiCad 10 library.
- The live `Custom/` gitlink shows ` M Custom` from the owner's commit `da070ae`; it was neither staged nor written, and the session guard did not trip in the full run. `git -C Custom status --short` is empty.

## Known Stubs

None.

## Threat Flags

None. The Wurth checkout matches the pinned gitlink (T-08-10), records cite the exact test id and kicad-cli 10.0.7 and were written after the green gate (T-08-11), and no live `Custom/` read or write was added (T-08-12).

## Next Phase Readiness

Phase 8 plans are all done. The phase needs `/gsd-verify-work 8` for the owner's Symbol Editor check (08-UAT.md test 2).

## Self-Check: PASSED

- tests/README.md, 08-UAT.md present; tests/conftest.py has no `custom_copy`.
- Commits 48e2395, 6876ac3, f326a33 are ancestors of HEAD.

---
*Phase: 08-test-isolation-and-kicad-10*
*Completed: 2026-10-25*
