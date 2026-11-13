---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 05
subsystem: importer
tags: [atomic-check, commit-gate, git, footprint, 3d-model, qt-free]

requires:
  - phase: 11-commit-gate-and-commit-panel-fixes
    provides: "11-02 run_gate, GateResult, AtomicFailure for the symbols of committed libraries"
provides:
  - "run_gate judges every Atomic_ symbol that links a committed footprint or a footprint naming a committed 3D model (D-04)"
  - "HEAD-view comparison: only violations the commit introduces block; the rest are old"
affects: [11-06, 11-08]

actuals:
  tokens: 9000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Two-view check: the same unchanged check_symbol runs against the work tree and a HEAD view built from planned_footprints, split by (rule, text)"
    - "Libraries outside the commit can only add an INFO note, never a refusal"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/commit_gate.py
    - tests/test_commit_gate.py

key-decisions:
  - "A committed model file never blocks alone: model existence is read from the work tree in both views, so committing a file cannot remove one (RESEARCH A4); symbols linking it are checked and land in old"
  - "A new committed footprint is absent in the HEAD view and resolves with the same 'is not in library' text HEAD would have given"
  - "An unchanged part of a committed library that the footprint change breaks is moved from old to blocking, not listed twice"

requirements-completed: [GIT-06]

duration: 40min
completed: 2026-10-30
status: complete
plan_head_before: a51c2b6a65223307f2e01a72695bcc7e2e743599
plan_head_after: eb3db13058039aacd757a5975779d97779c510e3
---

# Phase 11 Plan 05: Linked Parts of Committed Footprints and Models Summary

**The commit gate now refuses a shared-footprint overwrite that breaks parts in libraries outside the commit, comparing each linked part against a HEAD view so only newly introduced failures block.**

## Accomplishments

- `run_gate` collects the committed footprints (`Footprints/<Lib>.pretty/<Name>.kicad_mod`) and models (`3DModels/...`). When there are any, it lists the `Atomic_` libraries under `Custom/Symbols`, reusing the roots already parsed for committed libraries and reading the others with the same byte and node caps.
- A symbol is linked when its Footprint (own, or the nearest extends ancestor that declares one) resolves to a committed footprint, or to a Custom footprint that names a committed model. Footprint model lists are read once per path.
- Linked symbols are checked in the work tree and in the HEAD view built by `_head_view_context` (committed footprints hold their HEAD bytes through `planned_footprints`; new ones are absent). `_introduced` splits by `(rule, text)`: new violations block, the rest are old.
- An unreadable `Atomic_` library outside the commit adds an INFO note and is skipped; it never adds to `problems`.
- `cancelled()` is checked before each library of the new pass.

## Task Commits

1. **Task 1: shared footprint overwrite blocks linked parts (tracer)** - `253d153` (feat). Includes the whole linked-symbol pass; tracer `<verify>` re-run: `tests/test_commit_gate.py` 14 passed.
2. **Task 2: old linked failures, new footprints, committed models, unreadable outside libraries** - `eb3db13` (test)

## TDD Gate Compliance

Task 2 has no RED commit and no GREEN commit: its planned behavior (old split, new-footprint handling, model-only commits, unreadable-outside note) was part of the one linked-symbol pass the plan's Task 1 action describes, so all seven Task 2 tests passed on first run. Format-based RED evidence is therefore absent. As a substitute, the tests were checked for discrimination by mutation: making `_introduced` ignore the HEAD view failed `test_gate_linked_failure_already_at_head_is_old`, `test_gate_linked_new_failure_beside_old_one` and `test_gate_committed_model_never_blocks_alone`; the mutation was reverted before the commit.

## Verification

- `tests/test_commit_gate.py tests/test_importer_layering.py`: 35 passed (21 in `test_commit_gate.py`, above the required 18).
- `tests/test_layering.py tests/test_commit_plan.py`: 56 passed.
- The rest of the wave check (`test_commit_step`, `test_gitops`, `test_commit_panel`) belongs to sibling plans and was not run here.
- `grep` finds `_head_view_context`, `_footprint_text` and `_introduced` in `commit_gate.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test populate does not use `write_atomic_files`**
- **Found during:** Task 1
- **Issue:** `_populate_atomic` in the plan 11-02 tests writes the full atomic inventory, whose `Atomic_Connector` parts link `GENERIC-2PIN`; the overwrite test would then block on dozens of parts instead of the single expected one.
- **Fix:** the new tests use `_populate_footprints` (the scratch Custom/ plus `Atomic_Footprints.pretty` with `GENERIC-2PIN`, `NO-MODEL` and one model). The Atomic libraries from `populate_custom` carry no Footprint field, so nothing else links.
- **Files modified:** `tests/test_commit_gate.py`
- **Commit:** `253d153`

**2. [Added test] Moved-not-listed-twice case**
- One extra test, `test_gate_unchanged_part_of_committed_library_broken_by_footprint_blocks_once`, covers the plan's statement that an old-listed part found to be linked is moved. Commit `eb3db13`.

**Total deviations:** 1 auto-fixed (blocking, test fixture), 1 added test. **Impact:** none on behavior.

## Threat Surface

T-11-10 (footprint overwrite) mitigated by `test_gate_blocks_footprint_overwrite_breaking_linked_part`. T-11-11 mitigated: the pass runs only when a footprint or model is committed, reads go through the capped `_read_library`, footprint model lists are cached, `cancelled()` is checked per library. No new surface, no stubs.

## Known Stubs

None.

## Self-Check: PASSED

- `kicad_lib_manager/importer/commit_gate.py` and `tests/test_commit_gate.py` exist and are committed.
- Commits `253d153` and `eb3db13` are on the branch.
