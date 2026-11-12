---
phase: 04-plan-and-install-core
plan: 03
subsystem: importer
tags: [kicad-cli, subprocess, tempfile, memoisation, load-gate, pytest]

requires:
  - phase: 03-package-intake
    provides: kicad_files.parse_bytes / file_version, models.Issue, tests/zipfixtures UL sample
provides:
  - "kicad_lib_manager/importer/kicad_cli.py: locate_kicad_cli, stock_symbols_dir, run_cli, upgrade_symbol_text, clear_cache, load_gate"
  - "tests/fakecli.py FakeCli scripted runner for kicad-cli"
  - "pytest marker kicad_cli for tests that need the real binary"
  - "Issue codes install.cli_failed and install.cli_gate_failed"
affects: [04-06 normalisation, 04-07 apply_plan load gate, 04-01 layering ALLOWED entry]

actuals:
  tokens: 8800
  tasks: 2
  commits: 4
plan_head_before: fc65f8464a3757c4ce792c2566d614ccc9c4e229
plan_head_after: 6f8db5213eb4367d4a2206f918ae4b9cc2b1e238

tech-stack:
  added: []
  patterns:
    - "Injectable runner (subprocess.run signature) for every external process, with a scripted FakeCli in tests"
    - "Every CLI input/output in a fresh tempfile.mkdtemp folder outside the repo, removed in finally"
    - "Failures returned as Issue / list[Issue], never raised"

key-files:
  created:
    - kicad_lib_manager/importer/kicad_cli.py
    - tests/fakecli.py
    - tests/test_kicad_cli.py
  modified:
    - pyproject.toml

key-decisions:
  - "upgrade_symbol_text takes an extra keyword-only name label so the rejection ERROR can name the symbol (the plan signature had no name parameter)"
  - "load_gate refuses library and footprint names that are not plain file stems (separators, drive colon, dot-only, empty) before staging anything"
  - "Gate output files are named <library>.upgraded.kicad_sym so output and input paths can never collide, even for a library called 'out'"
  - "load_gate collects both the symbol and footprint failures instead of stopping at the first"

patterns-established:
  - "FakeCli mode list: a list of modes is consumed one per call (last repeats), used to script merged-fails / original-loads blame runs"
  - "FakeCli answers exit 4 when -o already exists, so tests prove the fresh-output rule"

requirements-completed: [INST-06]

coverage:
  - id: D1
    description: "kicad-cli is located (explicit, install next to footprints folder, PATH) and run with list argv, timeout and hidden window; timeout/OSError become ERROR Issues"
    requirement: INST-06
    verification:
      - kind: unit
        ref: "tests/test_kicad_cli.py#test_locate_* / test_run_cli_*"
        status: pass
    human_judgment: false
  - id: D2
    description: "Symbol normalisation through sym upgrade on a temp copy, memoised by input hash, exe signature and runner"
    requirement: INST-06
    verification:
      - kind: unit
        ref: "tests/test_kicad_cli.py#test_upgrade_*"
        status: pass
      - kind: integration
        ref: "tests/test_kicad_cli.py#test_real_cli_upgrades_ul_symbol_deterministically"
        status: pass
    human_judgment: false
  - id: D3
    description: "D-03 load gate on a merged symbol library copy and a footprint staging folder, with blame re-run on the original"
    requirement: INST-06
    verification:
      - kind: unit
        ref: "tests/test_kicad_cli.py#test_gate_*"
        status: pass
      - kind: integration
        ref: "tests/test_kicad_cli.py#test_real_cli_gate_rejects_sub_symbols_left_with_the_old_name"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-10-19
status: complete
---

# Phase 4 Plan 03: kicad-cli runner, memoised symbol upgrade and D-03 load gate Summary

**One injectable `kicad_cli` module that locates kicad-cli, runs `sym upgrade`/`fp upgrade` only on temp staging copies, memoises symbol normalisation, and provides the D-03 load gate, proven against both a scripted FakeCli and the real kicad-cli 9.0.9.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-19T22:27:09Z
- **Completed:** 2026-10-19T22:33:00Z
- **Tasks:** 2
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments

- `locate_kicad_cli` / `stock_symbols_dir` / `run_cli`: explicit path, then `<kicad_fp_dir>.parents[2]/bin/kicad-cli[.exe]`, then `shutil.which`; list argv, `capture_output`, `errors="replace"`, 60 s timeout, `CREATE_NO_WINDOW`; timeout and `OSError` come back as ERROR `install.cli_failed`.
- `upgrade_symbol_text`: `sym upgrade --force -o <fresh> <in.kicad_sym>` in a fresh temp folder, returns `SymbolUpgrade(text, version, changed)`; exit 0 with no output file is "already current" (`changed=False`); results memoised (32 entries) by sha256 of the input, exe path, exe size and mtime, and runner; failures are never cached.
- `load_gate`: symbol check on `<tmp>/merged/<library>.kicad_sym`, footprint check on `<tmp>/stage.pretty` holding only the incoming footprints, all outputs discarded; failures give ERROR `install.cli_gate_failed` with the CLI text and the file named; a symbol failure with `original_symbol_lib` re-runs on the original and says whether the target already failed before the merge.
- Real-CLI tests (3, marker `kicad_cli`, run on this machine, none skipped): the UL symbol upgrades to `(version 20241209)` identically across two real runs; the UL symbol and footprint pass the gate; a UL symbol whose top-level name was changed but whose `_1_1`/`_2_1` sub-symbols were left stale is rejected (exit 2).

## Task Commits

1. **Task 1 RED:** `5290186` (test) - marker, FakeCli, locate/run tests against a NotImplementedError stub
1. **Task 1 GREEN:** `1956895` (feat) - locate_kicad_cli, stock_symbols_dir, run_cli
2. **Task 2 RED:** `102a515` (test) - upgrade/gate/real-CLI tests against stubs
2. **Task 2 GREEN:** `6f8db52` (feat) - upgrade_symbol_text, clear_cache, load_gate

**Plan metadata:** committed separately as `docs(04-03)` (this SUMMARY).

## Files Created/Modified

- `kicad_lib_manager/importer/kicad_cli.py` - the module; imports only `..models` and `..kicad_files`
- `tests/fakecli.py` - `FakeCli` (modes: upgrade, not_updated, reject, missing, conflict, timeout, oserror; records calls, kwargs, input bytes)
- `tests/test_kicad_cli.py` - 56 tests (53 fake-runner, 3 real-CLI)
- `pyproject.toml` - `kicad_cli` marker

## TDD Gate Compliance

The plan is `type: execute` with `tdd="true"` tasks, so the plan-level gate sequence is not enforced, but each task still has a RED `test(04-03)` commit before its GREEN `feat(04-03)` commit.

- **RED evidence, task 1:** `pytest tests/test_kicad_cli.py -k "locate or stock or run_cli or fake"` gave 17 failed, 3 passed (the 3 passing are the FakeCli self-tests, which exercise the helper only). Every failure was `NotImplementedError` raised from the stubbed target functions. Semantic assessment: the target behaviors executed and failed because the implementation did not exist; no import, collection or fixture error. The stub module exists only so the failure is on the behavior and not on a missing module (an import error would be INVALID_RED).
- **RED evidence, task 2:** 35 failed, 21 passed; every failure was `NotImplementedError` from `upgrade_symbol_text` / `load_gate` (`clear_cache` was a no-op stub so the autouse fixture did not turn task-1 tests into setup errors). Same assessment.
- **GREEN:** 56 passed, 0 skipped.
- No REFACTOR commit was needed.

## Decisions Made

- `upgrade_symbol_text` gained a keyword-only `name` label, used only in the error text, because the plan required the ERROR to "name the symbol" but gave the function no name parameter.
- `load_gate` validates `library` and footprint names as plain file stems before staging (defence in depth for T-04-08, because those names become file names inside the staging folder).
- Gate output paths derive from the input name (`<library>.upgraded.kicad_sym`) so input and output can never be the same path.
- `load_gate` reports both the symbol and footprint failures, rather than stopping at the first.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Plain-name check on staged file names**
- **Found during:** Task 2 (load_gate)
- **Issue:** `library` and footprint names are written as file names under the temp folder; a name containing a separator or `..` could escape the staging folder, which T-04-08 says must never touch anything outside the temp folder.
- **Fix:** `_plain_name` check; unsafe names give ERROR `install.cli_gate_failed` and no process is started. Covered by `test_gate_refuses_names_that_could_leave_the_staging_folder` (5 cases).
- **Files modified:** `kicad_lib_manager/importer/kicad_cli.py`, `tests/test_kicad_cli.py`
- **Commit:** `6f8db52`

**2. [Rule 2 - Missing critical functionality] OSError handling around staging writes**
- **Found during:** Task 2
- **Issue:** `mkdtemp`, `write_bytes` and `read_bytes` can raise `OSError` (disk full, locked temp folder); the project convention is to return Issues, not raise.
- **Fix:** both functions catch `OSError` and return ERROR `install.cli_failed`; the temp folder is still removed in `finally`.
- **Commit:** `6f8db52`

**3. [Plan signature extension] `name` keyword on `upgrade_symbol_text`** - see Decisions Made.

**Total deviations:** 2 auto-fixed (Rule 2) plus 1 additive signature keyword. **Impact:** none on the interface the later plans use; `name` is optional.

## Verification

- `pytest tests/test_kicad_cli.py -x -q -rs`: 56 passed, 0 skipped.
- `pytest tests/test_kicad_cli.py -m kicad_cli -rs`: 3 passed, 0 skipped. `-m "not kicad_cli"`: 53 passed.
- `pytest -q --ignore=tests/test_importer_layering.py`: 909 passed, 14 skipped (pre-existing submodule skips).
- `grep -c "shell=True"` on the module: 0. Relative imports: `..kicad_files`, `..models` only.
- `git status --porcelain` after the run: clean (no CLI output left in the repo).
- `tests/test_importer_layering.py::test_importer_modules_follow_layering` currently FAILS with `importer.kicad_cli: not registered in ALLOWED`. This is expected and by plan: plan 04-01 adds the `"importer.kicad_cli": {"models", "kicad_files"}` entry in the same wave, and the wave-1 merge runs that test.

## Known Stubs

None.

## Threat Flags

None. The new surface (an external process launched with fixed subcommands on temp copies) is the one in the plan's threat model (T-04-06 to T-04-09); all four mitigations are implemented and tested.

## Issues Encountered

None.

## Next Phase Readiness

Plans 04-06 (symbol normalisation via `upgrade_symbol_text`) and 04-07 (`load_gate` as the last `apply_plan` precondition) can import this module. The orchestrator must make sure the wave merge includes 04-01's `ALLOWED["importer.kicad_cli"]` entry (`{"models", "kicad_files"}`).

## Self-Check: PASSED

- Files exist: `kicad_lib_manager/importer/kicad_cli.py`, `tests/fakecli.py`, `tests/test_kicad_cli.py`, `pyproject.toml` marker line.
- Commits present on the branch: `5290186`, `1956895`, `102a515`, `6f8db52`.
