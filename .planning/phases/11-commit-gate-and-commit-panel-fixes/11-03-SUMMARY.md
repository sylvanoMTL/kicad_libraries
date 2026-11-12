---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 03
subsystem: importer-commit
tags: [git, commit-message, dataclasses, python]

requires:
  - phase: 06-commit-step
    provides: parent_message / parent_preview / commit_parent_ref (D-18, D-19)
provides:
  - one parent_message builder serving the preview and the committed text (REV-07, D-15)
  - parent_only_preview for a bump with no new Custom commit
  - CommitFile.note / CommitFile.installed, file_sha256, rebaseline, with_added_files (data side of D-08, D-10)
affects: [11-06, 11-08, 11-10]

actuals:
  tokens: 14000
  tasks: 2
  commits: 3

plan_head_before: 74718e640c9693b992064bfb5b218a5048d94360
plan_head_after: 919dcfa44f8abdc226eb38e2d8319740c53d0d16

tech-stack:
  added: []
  patterns:
    - "One message builder behind preview and commit; the caller supplies the new commit's short hash and the full list of commit lines"
    - "Frozen-dataclass plan operations return a new CommitPlan via dataclasses.replace; new fields come last with defaults"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/commit_plan.py
    - kicad_lib_manager/importer/commit_step.py
    - tests/test_commit_plan.py
    - tests/test_commit_step.py

key-decisions:
  - "No previous gitlink: the new Custom commit's own line is listed, matching the gitlink-present case (research OQ4)"
  - "rebaseline stores the new hash in expected_sha256 and keeps the install-time bytes in installed (D-08 storage choice)"
  - "with_added_files uses the on-disk spelling of the added path, like build_commit_plan, so a pathspec matches on case-insensitive volumes"

requirements-completed: [REV-07, GIT-06]

coverage:
  - id: D1
    description: "Parent-message preview with <new commit> replaced by the real short hash equals the committed parent message, with and without a previous Custom gitlink"
    requirement: REV-07
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_parent_preview_equals_committed_message"
        status: pass
    human_judgment: false
  - id: D2
    description: "CommitPlan can be re-baselined to current file content and take extra Custom files marked as added, without mutation"
    requirement: GIT-06
    verification:
      - kind: unit
        ref: "tests/test_commit_plan.py#test_rebaseline_takes_current_bytes"
        status: pass
      - kind: unit
        ref: "tests/test_commit_plan.py#test_with_added_files_marks_and_sorts"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-10-30
status: complete
---

# Phase 11 Plan 03: Preview Equals Committed Message and CommitPlan Data Operations Summary

**One `parent_message` builder (with `_parent_text` and a corrected `_earlier`) makes the parent-message preview exactly the committed text with and without a previous gitlink, and `CommitPlan` gains `rebaseline` and `with_added_files` for Check again.**

## Performance

- **Duration:** about 30 min
- **Tasks:** 2 (Task 1 tracer, Task 2 TDD)
- **Files modified:** 4

## Accomplishments

- REV-07 closed: `test_parent_preview_equals_committed_message` (gitlink and no_gitlink) proves against real git that the preview with the placeholder replaced by the real short hash equals `outcome.parent_message` and the parent HEAD's body.
- With no previous gitlink the preview and commit list only the new commit's own line, never "could not be listed", never an empty hash.
- `CommitFile` gains trailing defaulted `note` and `installed`; `file_sha256` is public; `rebaseline` and `with_added_files` return new plans and never mutate.
- `with_added_files` refuses paths outside Custom with an ERROR `commit.outside_custom` issue (T-11-07); every message line still passes `sanitize_line` (T-11-06).

## Task Commits

1. **Task 1: Preview equals the committed parent message (REV-07)** - `120714d` (feat)
2. **Task 2 RED: failing tests for note, rebaseline, with_added_files** - `75163d7` (test)
3. **Task 2 GREEN: implementation** - `919dcfa` (feat)

## TDD Gate Compliance

Task 2 followed RED then GREEN. RED: 9 target tests failed in `tests/test_commit_plan.py` with `AttributeError` for the missing `rebaseline` / `with_added_files` / `NOTE_*` and missing `note` / `installed` fields; semantic assessment: each failure is the planned absence of the feature, not a collection or fixture fault (the other 32 tests in the file were collected and not run by the filter). GREEN: 41 passed in the file. No REFACTOR commit was needed. Task 1 was a tracer (tests and implementation committed together).

## Files Created/Modified

- `kicad_lib_manager/importer/commit_plan.py` - `parent_message(new_short)` builder, `parent_only_preview`, `CommitFile.note/installed`, `NOTE_*`, `file_sha256`, `rebaseline`, `with_added_files`
- `kicad_lib_manager/importer/commit_step.py` - `_earlier` returns `((), True)` for no gitlink; `_parent_text`; `commit_parent_ref(..., parent_only=)`
- `tests/test_commit_plan.py` - builder, preview and plan-operation tests
- `tests/test_commit_step.py` - preview-equals-committed test, `_earlier` test

## Decisions Made

See key-decisions above; all were the plan's recorded discretion choices.

## Deviations from Plan

None - plan executed exactly as written.

The plan's wave check lists `tests/test_commit_gate.py`, which does not exist yet (a later plan creates it). It was left out of the run; the other six files passed (191 passed). The per-plan ledger file for the commit-count base could not be written inside the sandbox, so `plan_head_before` is the asserted worktree base `74718e6`; `git rev-list --count 74718e6..HEAD` is 3.

## Known Stubs

None.

## Threat Flags

None.

## Issues Encountered

An early scripted edit converted line endings and broke the test files; they were restored with `git checkout` and re-patched before any commit. No commit contains the damage.

## Self-Check: PASSED

- `kicad_lib_manager/importer/commit_plan.py` has `def file_sha256`, `def rebaseline`, `def with_added_files`, `NOTE_CHANGED = `, `NOTE_ADDED = `.
- `kicad_lib_manager/importer/commit_step.py` has `def _parent_text` and its call inside `commit_parent_ref`.
- Commits `120714d`, `75163d7`, `919dcfa` exist on the worktree branch.
- `-k parent_preview_equals_committed_message` runs 2 tests, both passed.
