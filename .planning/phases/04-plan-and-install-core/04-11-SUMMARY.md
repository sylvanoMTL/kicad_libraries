---
phase: 04-plan-and-install-core
plan: 11
subsystem: importer
tags: [rollback, exception-safety, transaction, backups, utc, pytest]

requires:
  - phase: 04-plan-and-install-core
    provides: "apply_plan transaction, _rollback, prune_install_backups (plan 04-07)"
provides:
  - "Exception-safe apply_plan: any Exception inside the install is undone and reported as ERROR install.unexpected; interrupts roll back then propagate"
  - "Guarded progress callback: a raising callback becomes one WARNING install.progress_failed and the install carries on"
  - "prune_install_backups(..., exclude=) and a UTC backup stamp, so the running install's backup folder is never pruned"
affects: [04-12, 04-13, phase-05-gui-install]

actuals:
  tokens: 5460        # chars/4 over the realized diff (21838 chars, git diff 9c5c47f..HEAD before this SUMMARY)
  tasks: 3
  commits: 6
plan_head_before: 9c5c47f5bb733a43459a4f4be52ed97bc9508f43
plan_head_after: 727db69788e4f030285240eaf461be8b9d3969bb

tech-stack:
  added: []
  patterns:
    - "Mutable _Transaction holder recorded by the writing code so an outer BaseException guard can undo from outside"
    - "Rollback runs at most once (_rollback_once sets rolled_back before restoring)"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/applier.py
    - tests/test_install_apply.py

key-decisions:
  - "Exceptions return Issue values (install.unexpected), BaseException-only signals re-raise after rollback, keeping the importer's never-raise-to-callers convention"
  - "Progress callback failures are absorbed (callback disabled for the run, one WARNING) rather than aborting the install"
  - "The excluded (running) backup folder counts toward the ten kept: it plus the newest nine others"

patterns-established:
  - "Per-step Exception catch in _rollback so one failing undo step never abandons the rest"

requirements-completed: []  # INST-07 and INST-08 await phase re-verification (commit 7921587 reverted a premature Complete)

coverage:
  - id: D1
    description: "An Exception anywhere inside the install transaction is undone and reported as install.unexpected; an interrupt is undone and re-raised"
    requirement: INST-07
    verification:
      - kind: unit
        ref: "tests/test_install_apply.py#test_rollback_unexpected_error_in_a_write"
        status: pass
      - kind: unit
        ref: "tests/test_install_apply.py#test_rollback_interrupt_in_a_write_is_reraised"
        status: pass
      - kind: unit
        ref: "tests/test_install_apply.py#test_rollback_unexpected_error_in_verify"
        status: pass
      - kind: unit
        ref: "tests/test_install_apply.py#test_rollback_interrupt_in_verify_is_reraised"
        status: pass
      - kind: unit
        ref: "tests/test_install_apply.py#test_unexpected_error_before_any_write"
        status: pass
      - kind: unit
        ref: "tests/test_install_apply.py#test_rollback_interrupt_in_progress_is_reraised"
        status: pass
    human_judgment: false
  - id: D2
    description: "A raising progress callback cannot abort the install; folder-resolve OSError and rollback-step Exceptions become Issues"
    requirement: INST-08
    verification:
      - kind: unit
        ref: "tests/test_install_apply.py#test_progress_error_does_not_abort_the_install"
        status: pass
      - kind: unit
        ref: "tests/test_install_apply.py#test_make_folders_resolve_error_is_an_issue"
        status: pass
      - kind: unit
        ref: "tests/test_install_apply.py#test_rollback_step_error_is_reported"
        status: pass
    human_judgment: false
  - id: D3
    description: "The running install's backup folder is never pruned and new backup stamps are UTC"
    verification:
      - kind: unit
        ref: "tests/test_install_apply.py#test_prune_never_deletes_the_new_backup_folder"
        status: pass
      - kind: unit
        ref: "tests/test_install_apply.py#test_prune_exclude_counts_toward_keep"
        status: pass
      - kind: unit
        ref: "tests/test_install_apply.py#test_prune_exclude_absent_changes_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_install_apply.py#test_backup_stamp_is_utc"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-10-20
status: complete
---

# Phase 4 Plan 11: Exception-safe install transaction Summary

**apply_plan now undoes every write and reports ERROR install.unexpected when any Exception escapes the install (write, verify, gate, folder creation, rollback step), re-raises interrupts only after rolling back, absorbs a raising progress callback as a WARNING, and never prunes (UTC-stamped) its own backup folder.**

INST-07 and INST-08 await phase re-verification; no requirement is marked complete by this plan.

## Performance

- **Duration:** 6 min
- **Started:** 2026-10-20T10:45:00Z
- **Completed:** 2026-10-20T10:51:03Z
- **Tasks:** 3 (Task 1 tracer, Tasks 2 and 3 TDD)
- **Files modified:** 2

## Accomplishments

- Gap 1 (CR-01) closed: `apply_plan` wraps the transaction in `try/except BaseException`, using a `_Transaction` holder that the writing code fills (undo list, touched files, backup dir). An `Exception` returns `install.unexpected` (naming the exception type) followed by `install.rolled_back` when anything had been written; `KeyboardInterrupt`/`SystemExit` roll back and re-raise unchanged.
- A raising progress callback is dropped for the rest of the run and recorded once as WARNING `install.progress_failed`; the install completes and verifies. The callback still receives `(f"Writing {name}", index, total)` once per op.
- `_make_folders` turns an `OSError` from `Path.resolve()` into `fs.write_failed`; `_rollback` reports any `Exception` in an undo step as `install.rollback_failed` and keeps undoing the remaining steps.
- WR-01 closed: `prune_install_backups(..., exclude=)` keeps the running install's folder (counted toward the ten kept) and `_backup_folder` stamps in UTC.

## Test Counts

- **BASE** (Task 1 step 0, `tests/test_install_apply.py --collect-only`): 48 tests collected, same as the plan's measurement.
- **Final** collected count of `tests/test_install_apply.py`: 61 (BASE + 13 new tests).
- Worktree run of `tests/test_install_apply.py`: 50 passed, 11 skipped. Full suite in this worktree: 1246 passed, 61 skipped.
- Skips are the `Custom` / `WurthElektronik/KiCad-Library` submodules not being checked out in the worktree (custom_copy based tests, including the 11 skipped in test_install_apply.py: the fault matrix `existing-*`, locked target `existing`, backup failure, success touched order and the gate/stale/source tests built from `custom_copy` and `ul_package`). Expected; the orchestrator runs the full suite on the merged tree.
- `git status --porcelain Custom` prints nothing.

## Task Commits

1. **Task 1: tracer, exception during a write rolls back (CR-01)**
   - `9a42656` test(04-11): failing tests for exception safety in apply_plan writes (RED)
   - `4a57d26` feat(04-11): roll back and report install.unexpected when the transaction raises (GREEN)
2. **Task 2: every other raise site**
   - `5dc3b12` test(04-11): failing tests for progress, folder-resolve and rollback-step errors (RED)
   - `f864988` feat(04-11): guard progress callback, folder resolve and rollback steps against exceptions (GREEN)
3. **Task 3: running backup folder never pruned, UTC stamp (WR-01)**
   - `6e6d92d` test(04-11): failing tests for the running install's backup folder and UTC stamp (RED)
   - `727db69` fix(04-11): never prune the running install's backup folder; stamp backups in UTC (GREEN)

**Plan metadata:** the docs commit that carries this SUMMARY (docs: complete plan). The `commits: 6` above counts the six task commits and excludes it.

## TDD Gate Compliance

Each task has a `test(04-11)` RED commit before its implementation commit. In Task 2 four of the seven new tests (verify, interrupt-in-verify, gate, interrupt-in-progress) already passed after Task 1 because its guard covers those raise sites; this is what the plan predicted ("no code change beyond Task 1 is needed for them; the tests above prove it"). The other three failed for the intended reason (a progress `RuntimeError` aborted the install, `Path.resolve` `OSError` escaped, a non-`OSError` in a rollback step escaped).

## Files Created/Modified

- `kicad_lib_manager/importer/applier.py` - `_Transaction`, `_transaction`, `_rollback_once`, `_notify`, guard in `apply_plan`, per-step `Exception` catch in `_rollback`, resolve guards in `_make_folders`, `prune_install_backups(..., exclude=)`, UTC `_backup_folder`
- `tests/test_install_apply.py` - `_raising_writes` helper and 13 tests (sections "exception safety (CR-01)" and "the running install's backup folder (WR-01)"); added `import time`

## Decisions Made

- Followed the plan as specified. The interrupt path re-raises with a bare `raise` after `_rollback_once`, so the original traceback is preserved.

## Deviations from Plan

None - plan executed exactly as written.

## Accepted limitations

- **T-04-40:** a `KeyboardInterrupt` or `SystemExit` that lands inside `_rollback` itself stops the restore part-way with no retry, because `_rollback_once` sets `rolled_back` before restoring. After this plan every `Exception` in a rollback step is caught per step, so only a BaseException-only signal (a second Ctrl+C, the process exiting) can cause it. Recovery is the app-data backup folder (it holds every pre-image) plus `git status` in `Custom` (D-19). Documented in a comment above `_rollback_once`.
- **T-04-33:** an interrupt landing between a successful atomic replace and its undo entry leaves a whole file whose pre-image is in the backup folder (same recovery path).

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None - no new network, auth or trust-boundary surface; the work reduces the tampering risks T-04-29 to T-04-32.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 04-13 can build on the `_Transaction` holder for gap 2 (CR-02).
- INST-07 and INST-08 await phase re-verification; nothing was marked complete here and `.planning/REQUIREMENTS.md`, STATE.md and ROADMAP.md were left untouched for the orchestrator.

## Self-Check: PASSED

- `kicad_lib_manager/importer/applier.py` and `tests/test_install_apply.py` exist and contain the symbols named in the plan's acceptance criteria.
- Commits 9a42656, 4a57d26, 5dc3b12, f864988, 6e6d92d, 727db69 are ancestors of HEAD.

---
*Phase: 04-plan-and-install-core*
*Completed: 2026-10-20*
