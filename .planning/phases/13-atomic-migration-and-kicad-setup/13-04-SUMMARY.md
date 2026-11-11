---
phase: 13-atomic-migration-and-kicad-setup
plan: 04
subsystem: importer
tags: [git, commit, atomic-check, migration, kicad]

requires:
  - phase: 11-commit-gate-and-panel
    provides: CommitPlan/CommitFile, commit_gate.run_gate, commit_step.probe_commit/run_commit/pre_import_diff/changed_diff, widgets/commit_panel.CommitPanel
provides:
  - CommitFile.deleted and CommitPlan.message on the Phase 11 commit plan
  - commit_gate.run_gate (and its linked-file helpers) skip deleted files instead of trying to read them
  - commit_step.pre_import_diff/changed_diff show a plain "deleted" view instead of reading a missing file
  - widgets/commit_panel.CommitPanel marks a deleted row "(deleted)" with its own tooltip, never amber
  - tests/test_commit_deletions.py: a fast real-git suite proving the migration-shaped commit shape
affects: [13-13-migration-commit-plan-builder]

actuals:
  tokens: 5800
  tasks: 2
  commits: 2
  plan_head_before: 69225c3c71fb944af6e1fcfb3d5410318027d8b1
  plan_head_after: 1a7e9ab54a5ec388fd7ab7318310b2a17cfcb5f3

tech-stack:
  added: []
  patterns:
    - "CommitFile.deleted is checked first, before the kind/is_atomic filters, in every commit_gate loop that reads a file from the work tree"
    - "A plan-supplied CommitPlan.message is an unconditional override: default_message returns it verbatim with no sanitising or trailers"

key-files:
  created:
    - tests/test_commit_deletions.py
  modified:
    - kicad_lib_manager/importer/commit_plan.py
    - kicad_lib_manager/importer/commit_gate.py
    - kicad_lib_manager/importer/commit_step.py
    - kicad_lib_manager/widgets/commit_panel.py
    - tests/test_commit_plan.py
    - tests/test_commit_panel.py

key-decisions:
  - "commit_step.py needed no production-code change for Task 1 (RESEARCH F-06's own conclusion): run_commit and _precheck already treat a deleted tracked path correctly once commit_gate stops refusing it. The tracer test proves this by reverting the commit_gate.py fix and confirming the probe flips from 'ready' to 'gated' (P-04) — the only production change Task 1 needed was in commit_plan.py and commit_gate.py."
  - "A deleted row stays double-click-activatable in the commit panel (added to _activatable in _mark_files) even though it is never marked amber, so pre_import_diff/changed_diff's DELETED_TEXT is reachable from the UI, not just from direct calls."

requirements-completed: [MIG-04]

coverage:
  - id: D1
    description: "One Custom commit holds a deletion, a moved footprint and new files, with a plan-supplied message, and the parent ref commit follows"
    requirement: MIG-04
    verification:
      - kind: integration
        ref: "tests/test_commit_deletions.py#test_migration_shaped_commit_records_deletions_and_moves"
        status: pass
    human_judgment: false
  - id: D2
    description: "A deleted file is fresh while absent and stale once it reappears; rebaseline leaves a deleted entry unchanged"
    requirement: MIG-04
    verification:
      - kind: unit
        ref: "tests/test_commit_plan.py#test_deleted_file_is_fresh_while_absent"
        status: pass
      - kind: unit
        ref: "tests/test_commit_plan.py#test_reappeared_deleted_file_is_stale"
        status: pass
    human_judgment: false
  - id: D3
    description: "The commit gate never reads a deleted file; an emptied and deleted Atomic_ library no longer refuses the commit as unreadable (P-04)"
    requirement: MIG-04
    verification:
      - kind: integration
        ref: "tests/test_commit_deletions.py#test_migration_shaped_commit_records_deletions_and_moves"
        status: pass
    human_judgment: false
  - id: D4
    description: "A plan-supplied commit message replaces the importer's default message"
    requirement: MIG-04
    verification:
      - kind: unit
        ref: "tests/test_commit_plan.py#test_plan_message_overrides_default"
        status: pass
    human_judgment: false
  - id: D5
    description: "The commit panel lists a deleted file as '<path> (deleted)' with its own tooltip, keeps that text across a probe, and double-clicking it shows the deleted-file text"
    requirement: MIG-04
    verification:
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_marks_deleted_rows"
        status: pass
      - kind: unit
        ref: "tests/test_commit_deletions.py#test_deleted_views"
        status: pass
    human_judgment: false
  - id: D6
    description: "A commit whose files differ from HEAD only by deletions is still committed, never refused as 'Custom already holds these files'"
    requirement: MIG-04
    verification:
      - kind: integration
        ref: "tests/test_commit_deletions.py#test_deleted_only_commit_is_committed"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 04: Deleted files in the commit plan, gate, step and panel Summary

**The Phase 11 commit plan, gate, step and panel now accept `CommitFile.deleted` and a plan-supplied `CommitPlan.message`, so a migration-shaped commit can hold deletions, a moved footprint and new files as one Custom commit without the gate misreading a removed Atomic_ library as unreadable.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-11-11T14:20:00Z (approx.)
- **Completed:** 2026-11-11T15:15:00Z (approx.)
- **Tasks:** 2 completed
- **Files modified:** 7 (4 production, 3 test; 1 new test file)

## Accomplishments

- `CommitFile.deleted: bool = False` and `CommitPlan.message: str | None = None` added; `default_message` returns the plan's own message verbatim when set.
- `changed_since_install` and `rebaseline` treat a deleted file as fresh while absent and stale once it reappears, reusing the existing stale-refusal machinery with no new code path.
- `commit_gate.run_gate`, `linked_custom_files`, `_committed_footprints` and `_committed_models` all skip deleted files before touching the work tree, so an emptied `Atomic_` library that the migration deletes no longer trips "the library could not be checked" (RESEARCH P-04).
- `commit_step.pre_import_diff` and `changed_diff` return a plain `DELETED_TEXT` view for a deleted file instead of trying to read bytes that are gone.
- `widgets/commit_panel.CommitPanel` shows a deleted row as `"<path> (deleted)"` with a "Removed from Custom by this commit" tooltip from `show_plan` onward, and `_mark_files` never overwrites that with the amber changed/added styling — but keeps the row double-click-activatable so the deleted-file content view stays reachable.
- `tests/test_commit_deletions.py`: a new fast real-git test file (one throwaway superproject per test) proving the migration-shaped commit end to end, a deleted-only commit, an ignored-file refusal, and the deleted-file diff views — without running the slow `tests/test_commit_gate.py` / `tests/test_commit_step.py` per task.

## Task Commits

Each task was committed atomically:

1. **Task 1: One Custom commit holds deletions, a moved footprint and new files (MIG-04)** - `80075e6` (feat)
2. **Task 2: Deleted-file freshness, ignored files, diff views and the panel marker** - `1a7e9ab` (feat)

_No separate plan-metadata commit: this plan runs in worktree/parallel mode, so STATE.md/ROADMAP.md are updated centrally by the orchestrator after the wave merges._

## Files Created/Modified

- `kicad_lib_manager/importer/commit_plan.py` - `CommitFile.deleted`, `CommitPlan.message`, deleted-aware `changed_since_install`/`rebaseline`, `default_message` override
- `kicad_lib_manager/importer/commit_gate.py` - deleted files skipped in `run_gate`, `linked_custom_files`, `_committed_footprints`, `_committed_models`
- `kicad_lib_manager/importer/commit_step.py` - `DELETED_TEXT` constant, used at the top of `pre_import_diff` and `changed_diff`
- `kicad_lib_manager/widgets/commit_panel.py` - `_DELETED_MARK`/`_DELETED_TOOLTIP`, deleted-row handling in `_fill_files` and `_mark_files`
- `tests/test_commit_deletions.py` - new: the tracer test, a deleted-only commit, an ignored-file refusal, and the deleted-file diff views (all `requires_git` except the pure diff-view test)
- `tests/test_commit_plan.py` - deleted-file freshness/staleness and `rebaseline`, `CommitPlan.message` override
- `tests/test_commit_panel.py` - deleted-row marker, tooltip and activation surviving a probe

## Decisions Made

- `commit_step.py` production code needed no change for Task 1: the tracer test was verified to actually exercise the P-04 regression by temporarily reverting the `commit_gate.py` fix (via a tagged `git stash`, confirmed and dropped afterward) and observing `probe_commit` flip from `"ready"` to `"gated"`. Only `commit_plan.py` and `commit_gate.py` needed production changes for Task 1, matching RESEARCH F-06's own conclusion that "`run_commit` and `_precheck` need no other change."
- A deleted commit-panel row is kept in `_activatable` (so double-click still emits `file_activated`) even though `_mark_files` otherwise skips it entirely — this is what makes the `must_haves` truth "double-clicking it says the file is deleted by this commit" reachable through the UI signal path, not just through a direct `pre_import_diff`/`changed_diff` call.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The commit plan, gate, step and panel are ready for plan 13-13's migration commit-plan builder to produce a `CommitPlan` with `deleted=True` entries and its own `message`.
- The Phase 11 atomic gate is unchanged for every non-deleted, non-migration commit path; the wave gate (`tests/test_commit_gate.py tests/test_commit_step.py tests/test_commit_gate_panel.py`) was started in the background per the plan's `<verification>` note (it is a once-per-wave check owned by the orchestrator after Wave 1 merges, not a per-plan gate) and had not finished at the time this SUMMARY was written; this plan's own `<verification>` command (`tests/test_commit_plan.py tests/test_commit_deletions.py tests/test_commit_panel.py tests/test_gitops.py`, 157 tests) passed in full.
- No blockers.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/importer/commit_plan.py
- FOUND: kicad_lib_manager/importer/commit_gate.py
- FOUND: kicad_lib_manager/importer/commit_step.py
- FOUND: kicad_lib_manager/widgets/commit_panel.py
- FOUND: tests/test_commit_deletions.py
- FOUND: tests/test_commit_plan.py
- FOUND: tests/test_commit_panel.py
- FOUND commit: 80075e6 (ancestor of HEAD)
- FOUND commit: 1a7e9ab (ancestor of HEAD)
