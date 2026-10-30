---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 06
subsystem: importer-commit
tags: [git, commit-step, probe, timeout, identical-files, qt-free]

requires:
  - phase: 11-commit-gate-and-commit-panel-fixes
    provides: "commit_gate.CANCELLED / GateResult (11-02); changed_since_install, file_sha256, _parent_text, commit_parent_ref(parent_only) (11-03)"
provides:
  - "run_commit reports a commit that git finished late (timeout or failure after HEAD moved) as a commit, with no unstage and no parent bump"
  - "files identical to HEAD are an INFO line, never a missing-file ERROR; an all-identical plan refuses or bumps only the parent"
  - "CommitProbe.stale / identical / all_identical / gate, state 'gated', probe_commit(cancelled=...)"
affects: [11-07, 11-08, 11-09, 11-10]

actuals:
  tokens: 7000
  tasks: 3
  commits: 5

plan_head_before: a51c2b6a65223307f2e01a72695bcc7e2e743599
plan_head_after: ab0dc315635ffe091f355d7474b2ddad16520230

tech-stack:
  added: []
  patterns:
    - "HEAD is read before and after a failed git write; a moved HEAD means the write happened"
    - "Identity to HEAD is proven by sha256 of the work-tree bytes against `cat-file --filters` output"
    - "A cancel callable is checked between git steps; a private None return from _preexisting carries the cancel up"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/commit_step.py
    - tests/test_commit_step.py

key-decisions:
  - "Slow-hook test uses timeout=2 and a 5 s hook (plan said 1 and 3) so the commit itself cannot be the slow part"
  - "OQ5: a parent-only bump leaves committed False and sets parent_only True"
  - "The stale check moved into the probe as state 'gated' (OQ3); _precheck keeps its own stale refusal"
  - "_preexisting returns None on cancel, and probe_commit turns that into the 'The check was cancelled' unavailable state"

requirements-completed: [REV-06, REV-09, REV-10, REV-11, GIT-06]

coverage:
  - id: D1
    description: "A commit that git finishes after the timeout (or fails after HEAD moved) is reported as committed with a warning, nothing is unstaged, and the parent bump is left to the user with the manual command"
    requirement: REV-06
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_commit_timeout_after_head_moved_reports_commit"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_commit_slow_post_commit_hook_reports_commit"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_commit_timeout_reported"
        status: pass
    human_judgment: false
  - id: D2
    description: "A planned file identical to HEAD is an INFO line; an all-identical plan refuses without the parent option and makes a parent-only bump with it"
    requirement: REV-09
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_identical_planned_file_is_info_and_parent_bumps"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_all_identical_without_parent_refuses"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_all_identical_parent_only_bump"
        status: pass
    human_judgment: false
  - id: D3
    description: "The probe names stale and identical files before any click and stops between git calls when cancelled"
    requirement: REV-10
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_stale_file_is_gated"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_reports_identical_files"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_cancelled_returns_unavailable"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-10-30
status: complete
---

# Phase 11 Plan 06: Late commits, identical files and probe fields Summary

**`run_commit` now reports what git really did in Custom (a late commit is a commit, an unchanged file is not "missing", an all-unchanged plan bumps only the parent), and `probe_commit` returns stale, identical and gated state and can be cancelled between git calls.**

## Performance

- **Duration:** about 70 min
- **Completed:** 2026-10-30
- **Tasks:** 3 (Task 1 tracer, Tasks 2 and 3 TDD)
- **Files modified:** 2

## Accomplishments

- REV-06 / D-12: `run_commit` reads HEAD before `commit_paths` and again after any failure. A moved HEAD returns `_unfinished_outcome`: custom commit hash, branch and upstream filled, WARNING `commit.custom_unfinished` ("Committed <hash> in Custom, but git did not finish in time (a hook or signing step may still be running)" for a timeout, "... reported a failure afterwards (...)" otherwise), no unstage, no second git write, and with the parent option the parent message, manual command and WARNING `commit.parent_not_started`. An unchanged HEAD keeps the old "nothing was committed" path and the unstage.
- REV-09 / D-13: `_identical_to_head` hashes the work-tree bytes against `head_blob`. A planned file proven equal to HEAD becomes INFO `commit.already_in_head` ("Already identical to HEAD, not in the commit: <files>") and the parent bump goes ahead; extra files or files missing for any other reason still raise `commit.unexpected_files`.
- D-14 / OQ5: when every planned file equals HEAD, `run_commit` refuses with `commit.nothing_to_commit` ("Not committed: Custom already holds these files.") or, with the parent option, runs the new `_parent_step(parent_only=True)`; `CommitOutcome.parent_only` is True, `committed` stays False.
- `_parent_step` and `_manual_parent_command` extracted from `run_commit` (plan 11-07 rewrites only the quoting in the latter).
- Probe: `CommitProbe.stale`, `identical`, `all_identical`, `gate`; state "gated" with `stale_text(stale)` when a planned file changed after the install; `probe_commit(cplan, cancelled=...)` checks the callable after `_context`, `_custom_unavailable`, the branch/HEAD reads and between each read in `_preexisting`, and returns "unavailable" / "The check was cancelled".

## Task Commits

1. **Task 1: late commit reported as a commit (tracer)** - `c4f8331` (feat)
2. **Task 2: identical files, all-identical, parent-only (TDD)**
   - RED `c8b42d4` (test): four tests failed on the planned assertions (missing-file ERROR instead of INFO, `commit.custom_failed` instead of `commit.nothing_to_commit`, no `parent_only`)
   - GREEN `504fb37` (feat)
3. **Task 3: probe fields and cancel hook (TDD)**
   - RED `3a2c03e` (test): 10 tests failed (`AttributeError` for the new probe fields, `TypeError` for the `cancelled` keyword, state "ready" instead of "gated")
   - GREEN `ab0dc31` (feat)

## TDD Gate Compliance

Tasks 2 and 3 have RED then GREEN commits in order, no REFACTOR commits. RED for Task 2: the targets ran and failed on the planned behavior (git reported "nothing to commit" or the committed-files compare raised the missing-file ERROR), not on collection or fixture faults. RED for Task 3: failures are the planned absence of the fields and keyword and one assertion on state "gated". Task 1 is a tracer; tests and implementation share one commit.

## Files Created/Modified

- `kicad_lib_manager/importer/commit_step.py` - HEAD-moved outcome, identical handling, `_parent_step`, probe fields, cancel hook, `stale_text`
- `tests/test_commit_step.py` - 17 new tests (late-timeout wrapped runner and real slow hook, identical, all-identical, parent-only and its failure text, stale gated, identical probe on autocrlf True/False, three cancel variants)

## Decisions Made

- The real slow-hook test forces `timeout=2` and the hook sleeps 5 s (plan: 1 and 3), so a slow `git commit` start-up cannot make the test flaky; the commit still outlives the timeout.
- `_preexisting` returns `None` on cancel instead of raising; the probe maps it to the cancelled "unavailable" result.
- `_precheck` keeps its own `commit.stale_file` refusal; plan 11-08 is the place that reuses `stale_text` there.

## Deviations from Plan

None - plan executed exactly as written, apart from the extra tests (parent-only failure text, cancel between reads, no-stale ready probe, no-parent late timeout) and the timing constants noted above.

## Issues Encountered

None. The per-plan commit ledger could not be written inside the sandbox, so `plan_head_before` is the asserted worktree base `a51c2b6`; `git rev-list --count a51c2b6..HEAD` is 5.

## Verification

- `tests/test_commit_step.py tests/test_commit_plan.py tests/test_gitops.py tests/test_importer_layering.py`: 173 passed.
- `tests/test_commit_panel.py tests/test_commit_gate.py tests/test_layering.py`: 64 passed (the existing panel treats "gated" as not ready until plan 11-08).

## Known Stubs

None. `CommitProbe.gate` defaults to None on purpose: plan 11-08 fills it.

## Threat Flags

None. T-11-12, T-11-13 and T-11-14 are mitigated as planned.

## Self-Check: PASSED

- `kicad_lib_manager/importer/commit_step.py` has `def _identical_to_head`, `def _unfinished_outcome`, `def _manual_parent_command`, `def _parent_step`, `before = gitops.head_commit`.
- `tests/test_commit_step.py` has `def test_commit_timeout_after_head_moved_reports_commit`.
- Commits `c4f8331`, `c8b42d4`, `504fb37`, `3a2c03e`, `ab0dc31` are on the worktree branch.
