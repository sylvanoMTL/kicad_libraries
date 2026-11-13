---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 12
subsystem: git-commit-step
tags: [check-again, linked-files, commit-gate, d-10]

requires:
  - phase: 11-commit-gate-and-commit-panel-fixes
    provides: "11-08 recheck_commit (rebaseline, probe); 11-03 with_added_files and CommitFile.note/base_sha256; 11-02/11-05 commit_gate helpers"
provides:
  - "commit_gate.linked_custom_files(ctx, cplan, kicad_fp_dir, *, cancelled=None) -> ((Custom-relative rel, kind), ...) of the footprints and 3D models a committed part links"
  - "recheck_commit adds those files a fix created or changed (note 'added') between rebaseline and the probe"
  - "WARNING commit.recheck_failed on the returned probe when git cannot say which files are tracked"
affects: [11-10 panel, 11-11 dialog, 11-13 dialog]

plan_head_before: 447234416164cea1d8a2776a7a46318711277ede
plan_head_after: 9e1466e88acf58a6dbb7cf31e42caa5e30ad2bac

actuals:
  tokens: 9000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Models map to 3DModels/<name> only when <name> is an exact entry of the Custom/3DModels listing; no path is built from model text"
    - "Check again stays read-only: it reads files and git state and rebuilds the plan in memory"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/commit_gate.py
    - kicad_lib_manager/importer/commit_step.py
    - tests/test_commit_gate.py
    - tests/test_commit_step.py

key-decisions:
  - "A tracked linked model is never added (only footprints are compared with HEAD), so a changed tracked model stays a plain change to commit by the user"
  - "A linked file that is tracked in the index but absent from HEAD is added with no base, like an untracked one"
  - "The footprint set covers the plan's committed footprints plus the Custom footprints that the new or changed symbols of any committed .kicad_sym point at"

requirements-completed: [GIT-06]

coverage:
  - id: D1
    description: "A model the 3D fill-in copied into Custom/3DModels, named by a footprint a committed part links, joins the commit list with note 'added' and no base hash, and the next Commit commits it with the part"
    requirement: GIT-06
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_recheck_adds_untracked_linked_model"
        status: pass
    human_judgment: false
  - id: D2
    description: "A tracked footprint a committed part links that differs from HEAD joins with note 'added' and base_sha256 equal to the HEAD blob's hash"
    requirement: GIT-06
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_recheck_adds_modified_tracked_footprint"
        status: pass
    human_judgment: false
  - id: D3
    description: "Untracked files no committed part links never enter the plan; the other-changes count still counts them; tracked unchanged footprints stay out"
    requirement: GIT-06
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_recheck_leaves_unrelated_untracked_files_out"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_recheck_leaves_tracked_unchanged_footprint_out"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_recheck_adds_nothing_when_no_part_links_a_model"
        status: pass
    human_judgment: false
  - id: D4
    description: "A model is added only when its name is an exact entry of the Custom/3DModels listing: '..' segments, missing names, wrong-case names and other path variables add nothing"
    requirement: GIT-06
    verification:
      - kind: integration
        ref: "tests/test_commit_gate.py#test_linked_custom_files_never_builds_a_path_from_model_text"
        status: pass
      - kind: integration
        ref: "tests/test_commit_gate.py#test_linked_custom_files_footprint_and_model"
        status: pass
    human_judgment: false
  - id: D5
    description: "Check again writes nothing; when git cannot list tracked files nothing is added and a WARNING commit.recheck_failed is attached"
    requirement: GIT-06
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_recheck_writes_nothing"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_recheck_with_a_failing_file_list_adds_a_warning"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-10-30
status: complete
---

# Phase 11 Plan 12: Check again takes the files a fix created Summary

**`recheck_commit` now adds the untracked models and footprints a committed part links, and the tracked footprints that differ from HEAD (with the HEAD hash as base), so a commit never leaves a part pointing at an uncommitted file, while unrelated files stay out.**

## Performance

- **Duration:** about 70 min (most of it the git-heavy test files, about 8 min for `tests/test_commit_step.py`)
- **Tasks:** 2
- **Files modified:** 4 (2 source, 2 test)

## Accomplishments

- `commit_gate.linked_custom_files` collects the Custom footprints a commit links (the plan's own plus those the new or changed symbols of any committed `.kicad_sym` resolve to) and the models they name with the `${CUSTOM_3DMODEL_DIR}/` prefix. A model counts only as an exact entry of the `Custom/3DModels` listing, so `..`, wrong-case names and other variables yield nothing.
- `recheck_commit` calls it between `rebaseline` and the probe. Untracked linked files join with no base. A tracked linked footprint joins when it differs from HEAD, with `base_sha256` = hash of the HEAD blob. A tracked model or unchanged footprint never joins.
- When `gitops.tracked_paths` fails, nothing is added and the returned probe carries a WARNING `commit.recheck_failed`.

## Task Commits

1. **Task 1: a model the 3D fill-in copied joins the commit (tracer)** - `c29bfbd` (feat)
2. **Task 2: tracked footprints that differ from HEAD join; unrelated files stay out** - RED `3cdc2a3` (test), GREEN `9e1466e` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `kicad_lib_manager/importer/commit_gate.py` - `linked_custom_files`, `_custom_model_names`
- `kicad_lib_manager/importer/commit_step.py` - `_with_linked_files`, used by `recheck_commit`; `replace` and `with_added_files` imports
- `tests/test_commit_gate.py` - three `linked_custom_files` tests
- `tests/test_commit_step.py` - seven recheck tests for the added files; imports `vendor_footprint`, `STEP_BYTES`, `Issue`

## Decisions Made

See `key-decisions` above.

## Deviations from Plan

None - plan executed as written. Extra tests beyond the plan's list (`test_recheck_adds_nothing_when_no_part_links_a_model`, `test_recheck_leaves_tracked_unchanged_footprint_out`, `test_recheck_with_a_failing_file_list_adds_a_warning`, two more `linked_custom_files` tests) cover the "never added" cases and the warning the plan names.

## Issues Encountered

None. The plan-commit ledger file under the worktree's git dir could not be written (the sandbox refused the path), so `plan_head_before` is the base from the spawn-time check, `447234416164cea1d8a2776a7a46318711277ede`; `git rev-list --count` from it gives 3.

## Threat Flags

None. T-11-19 mitigated: only files a committed part links are added, models must match the exact `Custom/3DModels` listing (`test_linked_custom_files_never_builds_a_path_from_model_text`), and unrelated untracked files stay out (`test_recheck_leaves_unrelated_untracked_files_out`). `test_recheck_writes_nothing` still passes, so nothing is staged or written.

## Known Stubs

None. `import_dialog.py` and the panel do not yet mark the added files; plans 11-10, 11-11 and 11-13 own that (the files already carry note "added").

## TDD Gate Compliance

Task 1 is a tracer (single feat commit; its automated verify was re-run end to end before expansion: 13 passed). Task 2: RED `3cdc2a3` (`test_recheck_adds_modified_tracked_footprint` failed with `StopIteration` looking for the footprint in the new plan, `test_recheck_with_a_failing_file_list_adds_a_warning` failed on `assert 0 == 1` warnings; both targets executed and failed on the planned behavior, not on setup or import), then GREEN `9e1466e` (122 passed in `tests/test_commit_step.py`). The machine RED classifier (`gsd_run check tdd-red-evidence`) was not run: `gsd_run` is not available in this worktree.

## Verification

- `tests/test_commit_step.py`: 122 passed.
- `tests/test_commit_gate.py tests/test_commit_plan.py tests/test_importer_layering.py tests/test_layering.py`: 94 passed.
- `tests/test_gitops.py`: 32 passed.
- Not run here (the orchestrator runs the full suite after merge): `tests/test_commit_panel.py`, `tests/test_import_dialog.py`.
- `grep -n "def linked_custom_files"` finds one line in `commit_gate.py`; `grep -n "with_added_files("` finds one call in `commit_step.py`; `grep -n "commit.recheck_failed"` finds the warning.

## Next Phase Readiness

Plans 11-10, 11-11 and 11-13 can list and mark the files `recheck_commit` adds (note "added", `CommitFile.base_sha256` None for new files) and show them with `changed_diff`.

## Self-Check: PASSED

- `kicad_lib_manager/importer/commit_gate.py` contains `def linked_custom_files`; `kicad_lib_manager/importer/commit_step.py` contains `def _with_linked_files`.
- Commits `c29bfbd`, `3cdc2a3`, `9e1466e` are ancestors of HEAD.

---
*Phase: 11-commit-gate-and-commit-panel-fixes*
*Completed: 2026-10-30*
