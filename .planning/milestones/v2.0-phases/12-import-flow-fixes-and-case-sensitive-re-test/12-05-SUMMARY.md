---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 05
subsystem: importer
tags: [import-dialog, finishing-state, qthread, rebuild-coordinator, REV-03, REV-04]
requires:
  - phase: 12-import-flow-fixes-and-case-sensitive-re-test
    provides: "12-01 conflict-view lookup for case twins (import_dialog.py base)"
provides:
  - "Finishing state: Change... or an open during a build greys the dialog, shows a strip with Cancel, and runs by itself when the build ends"
  - "bounded _reap join (2 s) and no unbounded GUI-thread wait before Change/open"
  - "one-off conflict builds and Install never overlap (REV-03)"
affects: [12-07 closing (extends the Finishing state with a close kind), import dialog tests]
actuals:
  tokens: 7500
  tasks: 3
  commits: 5
tech-stack:
  added: []
  patterns: ["deferred action run from QThread.finished via _reap/_try_finish", "paired setOverrideCursor/restoreOverrideCursor in _enter_finishing/_end_finishing"]
key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_import_dialog.py
key-decisions:
  - "A rebuild asked for during a successful install is dropped (self._queued = None), as the held one-off views are: the Result page replaced the preview it would refresh. The owner-approved Refinement of D-08 names held one-off builds only, so this second drop is reported here for the owner to see."
  - "_shutdown calls _end_finishing() so a close during Finishing drops the pending action and restores the wait cursor; plan 12-07 builds the proper close handling on top."
requirements-completed: [REV-03, REV-04]
status: complete
commits: 5
plan_head_before: eefa94b248c426f300decc590825a0c67220a516
plan_head_after: a67a055bd52451d84c64f0442ee9a15b5f519005
duration: 55 min
completed: 2026-11-01
coverage:
  - id: D1
    description: "Change... during a rebuild enters Finishing (strip, wait cursor, disabled stack) and completes by itself after the build ended; the package closes after the build"
    requirement: REV-04
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_change_waits_for_build_without_blocking"
        status: pass
    human_judgment: false
  - id: D2
    description: "The GUI thread never joins a worker without a timeout of at most 2000 ms during Change"
    requirement: REV-04
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_change_never_waits_unbounded"
        status: pass
    human_judgment: false
  - id: D3
    description: "Opening another package during a build waits in Finishing and opens by itself"
    requirement: REV-04
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_open_during_build_opens_after_it_ends"
        status: pass
    human_judgment: false
  - id: D4
    description: "Cancel restores the dialog; the slow-kicad-cli note appears after the delay; the event loop keeps running; no build starts while Finishing"
    requirement: REV-04
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_finishing_cancel_restores_the_dialog"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_finishing_shows_slow_note"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_finishing_keeps_the_event_loop_running"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_no_build_starts_while_finishing"
        status: pass
    human_judgment: false
  - id: D5
    description: "Install is disabled while a one-off conflict build runs; a one-off asked for during an install runs after a failure and is dropped after a success"
    requirement: REV-03
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_install_disabled_while_oneoff_runs"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_oneoff_held_during_install_runs_after_failure"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_oneoff_held_during_install_dropped_after_success"
        status: pass
    human_judgment: false
  - id: D6
    description: "The Finishing strip looks right and reads clearly (wording, spacing, wait cursor)"
    requirement: REV-04
    human_judgment: true
    rationale: "Appearance and feel of the strip are not asserted by any test"
---

# Phase 12 Plan 05: Finishing state and build/Install separation Summary

Change... and opening a package no longer join a running build on the GUI thread: the dialog greys out under a wait cursor with a "Finishing the preview..." strip (Cancel, plus a slow-kicad-cli note after 10 s) and runs the request by itself from the last worker's finished handler. A one-off conflict build now counts as updating (Install greys out) and is held while an install runs.

## Accomplishments

- Finishing state in `import_dialog.py`: constants `FINISHING_TEXT`, `SLOW_CLI_TEXT`, `_SLOW_NOTE_MS`; `finishStrip` frame beside the page stack (so Cancel stays enabled while the stack is off); `is_finishing`, `_busy_builds`, `_enter_finishing`, `_end_finishing` (cursor calls always paired), `_try_finish`, `_on_finish_cancel`, `_on_slow_timeout`.
- `_on_change` / `open_path` split into guard + `_do_change` / `_do_open`; the helper that joined the builds on the GUI thread is removed. `_reap` joins a finished thread for at most 2 s and then runs `_try_finish(exclude=worker)`.
- `_pump_builds` and `_request_rebuild` hold while Finishing or installing; `_on_oneoff_done` skips its content view while Finishing. kicad-cli is never killed.
- `_updating()` counts a running one-off; `_start_oneoff` refreshes the Install state at once; a conflict view asked for during an install is queued, not refused. After a failed install `_pump_builds()` runs before the retry rebuild; after a successful one the held one-off jobs and any queued rebuild are dropped.
- 10 new tests (7 Finishing, 3 one-off/Install), all passing.

## Task Commits

1. Task 1 (tracer): `bdc926f` feat(12-05): Change... during a build enters Finishing instead of waiting on the GUI thread
2. Task 2 RED: `d782186` test(12-05): failing open-during-build test plus Cancel, slow note and held-build tests
3. Task 2 GREEN: `c001679` feat(12-05): opening a package during a build enters Finishing
4. Task 3 RED: `20eacca` test(12-05): failing tests for one-off builds against Install
5. Task 3 GREEN: `a67a055` feat(12-05): Install and one-off conflict builds never overlap

## Verification

- Task 1 selection (`change or close_waits or builds_never_overlap or one_build`): 15 passed.
- Task 2 selection (`finishing or open_during or open_path or change`): 19 passed.
- Task 3 selection (`oneoff or conflict or install`): 46 passed after the Cancel-test fix below.
- Plan selection (`change or finishing or open or oneoff or conflict or install or build`): 77 passed in 61 s.
- Whole `tests/test_import_dialog.py`: 214 passed in 144 s. The full suite was not run (the orchestrator runs it after the wave).
- Acceptance greps: `def is_finishing`, `def _try_finish`, `wait(2000)` and `_try_finish(exclude=worker)` found; `_wait_builds` count 0; non-comment `.wait()` count 1 (the close-time join in `_shutdown`, which plan 12-07 replaces); `self._oneoff is not None` is inside `_updating`; the `self.is_installing()` guard is in `_pump_builds`.
- The Custom and Würth submodules are absent in this worktree; no targeted test depended on them.

## TDD Gate Compliance

Task 1 is a tracer (implementation and its two tests in one commit, as for an auto task). Tasks 2 and 3 have test commits before their feat commits.

- RED, Task 2: `test_open_during_build_opens_after_it_ends` failed at `assert dialog.is_finishing()` (open_path still joined the gated build on the GUI thread for about 30 s). The other four Task 2 tests passed already because Cancel, the slow note, the event loop and the held-build rule were built with Task 1's Finishing machinery; they are regression coverage, not RED.
- RED, Task 3: all three tests failed on the planned assertion (Install enabled during a one-off; the job not queued during an install; a rebuild asked for during an install started at once, 4 builds instead of 3). `gsd_run check tdd-red-evidence` was not run (no record file was produced); the semantic check was made by reading each failure.

## Decisions Made

- Dropped rebuild after a successful install: the plan wrote `self._queued = None` on success. The owner-approved "Refinement of D-08" names held one-off builds only; the rebuild drop follows from the same reason (the Result page replaced the preview). Reported here so the owner sees it.
- `_shutdown` calls `_end_finishing()` so closing the dialog during Finishing drops the pending action and restores the cursor. Plan 12-07 owns the real close-while-Finishing behaviour.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test conflict] The "no Cancel button while installing" check saw the hidden Finishing Cancel**
- **Found during:** Task 3 verification run
- **Issue:** `test_install_progress_and_lock` asserted that no `QPushButton` in the dialog is named "Cancel". The plan's Finishing strip adds one (hidden unless Finishing).
- **Fix:** the check now looks for a visible Cancel button, which keeps its intent (an install cannot be cancelled).
- **Files modified:** tests/test_import_dialog.py
- **Commit:** a67a055

**2. [Rule 3 - Blocking] Plan ledger file not written**
- The harness refused a write into the shared git directory, so the on-disk ledger of protocol 0c was not created. The base `eefa94b` (verified at start) was used for the measured commit count: `git rev-list --count eefa94b..HEAD` = 5 before this SUMMARY commit.

**Total deviations:** 2 (1 test fix, 1 bookkeeping). **Impact:** none on behaviour.

## Owner UAT

Open Import Part, load a package, and press Change... right after an edit (while "Updating..." shows). The dialog should grey out under a wait cursor with "Finishing the preview..." and a Cancel button, then land on the Start page by itself. Cancel should bring the preview back untouched. The 10 s slow-kicad-cli note only appears when kicad-cli is genuinely slow.

## Known Stubs

None.

## Threat Flags

None. No new network, auth, file-access or trust-boundary surface; T-12-10 to T-12-13 are covered by `test_change_never_waits_unbounded`, `test_change_waits_for_build_without_blocking`, `test_install_disabled_while_oneoff_runs`, `test_oneoff_held_during_install_runs_after_failure` and the kept never-deleteLater rule in `_reap`.

## Self-Check: PASSED

- `kicad_lib_manager/widgets/import_dialog.py` and `tests/test_import_dialog.py` exist and carry the changes; commits bdc926f, d782186, c001679, 20eacca and a67a055 are on the branch.
