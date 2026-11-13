---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 02
subsystem: importer
tags: [atomic-check, commit-gate, git, kicad_sym, qt-free]

requires:
  - phase: 09-atomic-check
    provides: "atomic_check.check_symbol rule engine and the D-21 per-symbol changed compare"
  - phase: 06-commit-step
    provides: "CommitPlan and CommitFile (the files being committed)"
provides:
  - "changes.symbol_changes: the one public copy of the per-symbol new/changed compare"
  - "importer/commit_gate.py: Qt-free run_gate, GateResult, AtomicFailure and the plain-language text builders"
  - "scan_result_for: a ScanResult the Check Atomic Parts dialog can open directly"
affects: [11-05, 11-06, 11-08]

actuals:
  tokens: 6000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Gate reuses the unchanged rule engine and the unchanged D-21 compare; no second copy of either"
    - "Safe default: an unreadable committed Atomic_ library refuses the commit"

key-files:
  created:
    - kicad_lib_manager/importer/commit_gate.py
    - tests/test_commit_gate.py
  modified:
    - kicad_lib_manager/changes.py
    - tests/test_importer_layering.py

key-decisions:
  - "Parts whose extends parent changed are judged as changed (RESEARCH Pitfall 4), by walking the extends chain with a loop guard"
  - "refusal_summary with problems but no blocking parts reads only '1 library could not be checked' instead of '0 parts break the atomic rule'"
  - "Footprints resolve through incoming_context only; the gate builds no path from symbol text"

requirements-completed: [GIT-06]

duration: 45min
completed: 2026-10-30
status: complete
plan_head_before: 74718e640c9693b992064bfb5b218a5048d94360
plan_head_after: 7e9b495d746b60a00f7411ae30d030546ae9deee
---

# Phase 11 Plan 02: Commit Gate Summary

**Qt-free commit gate that judges new or changed parts of committed Atomic_ libraries with the unchanged atomic rules, keeps already-failing parts as a non-blocking note, and refuses on an unreadable library.**

## Performance

- **Duration:** about 45 min
- **Completed:** 2026-10-30
- **Tasks:** 2 (one tracer, one TDD)
- **Files modified:** 4

## Accomplishments

- `changes.symbol_changes(ctx, custom_dir, rel, root)` now holds the per-symbol compare against HEAD; `_mark_symbols` calls it and behaves exactly as before (`tests/test_scan_changes.py` untouched and green).
- `run_gate` lists each broken rule of every new or changed part in a committed `Atomic_` `.kicad_sym` as a blocking `AtomicFailure` (library, repo-relative path, part, rule, text).
- Unchanged parts that already fail go to `GateResult.old` and never block; price or stock leftovers (findings) never block; libraries without the `Atomic_` prefix are never judged.
- A derived part whose parent changed is judged as changed even when its own tokens did not.
- A committed `Atomic_` library that is missing, too large or does not parse adds a `problems` line and makes `refused` True.
- Text builders (`refusal_summary`, `failure_lines`, `old_notes`, `gate_issues`) produce the plain-language strip and log lines; `scan_result_for` builds the `ScanResult` for the Check Atomic Parts dialog, keyed by the same `(rel_path, name)` the dialog uses for focus.

## Task Commits

1. **Task 1: failing new Atomic_ part found end to end (tracer)** - `ac52496` (feat)
2. **Task 2: old failures, derived parts, unreadable libraries, texts, ScanResult (TDD)**
   - RED `f7902fb` (test): `test_gate_old_failure_does_not_block` failed on the planned assertion (`gate.old` was empty)
   - GREEN `7e9b495` (feat)
   - No REFACTOR commit needed

## TDD Gate Compliance

RED then GREEN commits are present in order for Task 2. RED evidence: the target test ran and failed with `AssertionError: assert [] == [('OLD-1', 'datasheet')]` at the `gate.old` assertion, which is the planned behavior and not an import, fixture or syntax fault. The run used `-x`, so it stopped at the first failure; the remaining new tests exercise behavior the Task 1 module did not have (old, derived, unreadable, text builders), and text builders are reached through module attributes so the failures are at call time, not collection. All 12 tests in `tests/test_commit_gate.py` pass after GREEN.

## Files Created/Modified

- `kicad_lib_manager/importer/commit_gate.py` - the gate and its text builders
- `kicad_lib_manager/changes.py` - public `symbol_changes`, `_mark_symbols` rewritten on top of it
- `tests/test_commit_gate.py` - 12 tests on throwaway superprojects
- `tests/test_importer_layering.py` - `importer.commit_gate` registered; `importer.commit_step` may import it

## Decisions Made

- Derived-part detection is a name-based walk over the file's own symbols with a seen-set loop guard, mirroring `atomic_check._chain`.
- A result with only problems (no blocking parts) summarises as the library count alone.
- The cancelled marker is counted as a problem, as specified, so `refusal_summary` reports "1 library could not be checked" for it.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- `tests/test_commit_gate.py tests/test_scan_changes.py tests/test_importer_layering.py tests/test_layering.py`: 67 passed.
- Importing `kicad_lib_manager.importer.commit_gate` in an isolated interpreter leaves `PySide6` out of `sys.modules`.
- `tests/test_commit_gate.py` has no reference to `REPO_ROOT` or the live `Custom/`.
- The wave-level run listed in the plan (`test_commit_plan`, `test_commit_step`, `test_gitops`, `test_commit_panel`) was not run here; it spans files owned by sibling plans in the same wave.

## Threat Surface

T-11-03 (bounded reads: byte cap before reading, node cap when parsing), T-11-04 (unreadable library refuses) and T-11-05 (footprints resolve only through `incoming_context`) are mitigated as planned. No new surface outside the plan's threat model. No stubs.

## Self-Check: PASSED

- `kicad_lib_manager/importer/commit_gate.py`, `tests/test_commit_gate.py`, `kicad_lib_manager/changes.py`, `tests/test_importer_layering.py` exist and are committed.
- Commits `ac52496`, `f7902fb`, `7e9b495` are on the branch.
