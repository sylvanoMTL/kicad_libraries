---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 07
subsystem: importer
tags: [import-dialog, finishing-state, close, qthread, main-window, REV-04]
requires:
  - phase: 12-import-flow-fixes-and-case-sensitive-re-test
    provides: "12-05 Finishing state and _end_finishing in _shutdown; 12-06 deferred main-window close while the KiCad-open check runs"
provides:
  - "Closing the import dialog by any route returns at once; the dialog enters Finishing and closes by itself after the last worker ended"
  - "Closing the main window while the dialog finishes is deferred; the window closes by itself after the dialog"
  - "Escape does nothing while Finishing; Cancel ends a pending close, emits leave_cancelled and probes the commit step again"
  - "_shutdown joins no worker: the GUI thread never waits unbounded on close"
affects: [verify-work, owner UAT of the close paths]
actuals:
  tokens: 14000
  tasks: 2
  commits: 3
tech-stack:
  added: []
  patterns:
    - "A deferred close is a bound method run from the last worker's finished handler (super() works; never a lambda)"
    - "A pending close drops the probe and KiCad-notice results like a finished close, and Cancel restores them by probing again"
key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/main_window.py
    - tests/test_import_dialog.py
    - tests/test_main_window_import.py
key-decisions:
  - "The commit probe is cancelled when a close starts (Task 1, not Task 2): without it the old probe-close tests would have waited out the full probe, so the tracer needed it to stay green"
  - "A pending close drops the probe result and the KiCad-running notice (_close_pending), as the old _closing flag did after the join; the probe is restarted on Cancel, the notice is best-effort and is not restored"
  - "The open Check Atomic Parts dialog stays open while a close waits and is rejected by _shutdown when the close completes (probe cancelled, so at most one git call)"
requirements-completed: [REV-04]
status: complete
commits: 3
plan_head_before: 3fbb4e9a07b23d2c98784476995bf4ee363bb9bd
plan_head_after: 4fe8eca5d80a9891e27e8dbe0836f469161ad3c4
duration: 50 min
completed: 2026-11-01
coverage:
  - id: D1
    description: "Closing the dialog while a build runs returns at once, shows Finishing and closes the package only after the build ended"
    requirement: REV-04
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_close_finishes_after_build_and_closes_package"
        status: pass
  - id: D2
    description: "Closing the main window while the dialog builds is deferred and completes by itself; Cancel drops it"
    requirement: REV-04
    verification:
      - kind: integration
        ref: "tests/test_main_window_import.py#test_main_window_close_waits_for_dialog_build"
        status: pass
      - kind: integration
        ref: "tests/test_main_window_import.py#test_main_window_close_cancelled_with_dialog"
        status: pass
  - id: D3
    description: "Escape does nothing while Finishing; X upgrades a pending Change... to a close; Cancel keeps the dialog open"
    requirement: REV-04
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_escape_does_nothing_while_finishing"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_x_upgrades_pending_change_to_close"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_cancel_close_keeps_dialog_open"
        status: pass
  - id: D4
    description: "A close during the KiCad check or the commit probe finishes by itself; the probe is cancelled and is run again when the close is cancelled"
    requirement: REV-04
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_close_while_kicad_check_runs"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_close_during_probe_cancels_and_closes"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_cancelled_close_reprobes"
        status: pass
  - id: D5
    description: "The Finishing strip on a close reads clearly and the window feels live (wording, wait cursor)"
    requirement: REV-04
    human_judgment: true
    rationale: "Appearance and feel are not asserted by any test"
---

# Phase 12 Plan 07: Close through Finishing, no GUI-thread join (REV-04) Summary

Closing the import dialog (Close, X, Escape outside Finishing, reject from the main window) or the main window while a worker runs now returns at once: the dialog shows the Finishing strip and closes by itself after the last worker ended, and the main window follows it. `_shutdown` no longer joins any worker.

## Accomplishments

- `import_dialog.py`: `_busy_for(kind, exclude)` ("close" counts every running worker, "change"/"open" the builds), `_finish_close(r)`, `_upgrade_to_close(r)` (close wins over a pending Change... or open), `_cancel_probe_for_close()` with `_probe_cancelled_by_close`, `leave_cancelled` signal, `_close_pending()`. `done`, `closeEvent` defer through Finishing; `keyPressEvent` swallows Escape while Finishing; `_shutdown` lost its unbounded join and its docstring says it runs only from `_finish_close`. The only `.wait(` left is the 2 s bound in `_reap`.
- `main_window.py`: `QTimer` import, `_close_after_dialog`, `_on_dialog_leave_cancelled`; `closeEvent` ignores the close when the dialog is finishing after `reject()`; `_on_import_dialog_finished` re-closes the window with `QTimer.singleShot(0, self.close)`. It composes with the 12-06 deferral: the re-close finds a running KiCad check and defers again through `_close_after_check`.
- Tests: `test_close_waits_and_closes_package` became `test_close_finishes_after_build_and_closes_package` (no elapsed-time assertion); probe, add-model and open-check-dialog close tests wait for the dialog to become invisible; 6 new dialog tests and 3 new window tests; stand-in dialogs gained `is_finishing`.

## Task Commits

1. Task 1 (tracer): `47921e1` feat(12-07): closing the dialog or the window during a build finishes by itself
2. Task 2 RED: `260e979` test(12-07): failing tests for Escape, X, Cancel and the probe during a Finishing close
3. Task 2 GREEN: `4fe8eca` feat(12-07): Cancel of a close, the commit probe restarts, and the window forgets its close

## TDD Gate Compliance

Task 1 is a tracer (code and tests in one commit). Task 2 has the test commit before the feat commit.

- RED, Task 2: 4 of the 6 new tests failed on the planned assertions: `test_cancel_close_keeps_dialog_open` (no `leave_cancelled` signal), `test_close_while_kicad_check_runs` (the KiCad-running warning was logged during the close), `test_cancelled_close_reprobes` (the probe was never run a second time, `waitUntil` timed out), `test_main_window_close_cancelled_with_dialog` (`_close_after_dialog` still set after Cancel). `test_escape_does_nothing_while_finishing` and `test_x_upgrades_pending_change_to_close` already passed because the tracer implemented the Escape guard and the close-wins upgrade; they are regression coverage, not RED. `gsd_run check tdd-red-evidence` was not run (pytest has no supported report format); the semantic check was made by reading each failure.
- GREEN: the 6 new tests pass; the Task 2 selection gave 44 passed.

## Verification

- Task 1 selection (`close or finishing or change`): 34 passed.
- Task 2 selection (`close or finishing or escape or cancel or probe or kicad_running or add_model_close`): 44 passed.
- Whole `tests/test_import_dialog.py`: 219 passed in 136 s, no process abort. Whole `tests/test_main_window_import.py` and `tests/test_main_window.py`: 111 passed.
- Acceptance greps: non-comment `.wait()` count in `import_dialog.py` is 0; `def _finish_close` and `_enter_finishing("close"` found; `time.monotonic() - started >= 0.2` count 0; `leave_cancelled` appears as signal, emit and connection; `self._finishing` is used inside `keyPressEvent`.
- Full suite not run (orchestrator). The Custom and Wuerth submodules are absent in this worktree; no targeted test depended on them, so nothing was skipped for that reason.
- No failures outside this plan's tests, so nothing to route to other plans.

## Deviations from Plan

**1. [Rule 3 - Blocking] Probe cancel moved into Task 1**
- **Issue:** with `_shutdown` no longer joining, the probe must be cancelled when the close starts, or the existing probe-close tests wait out the whole probe. The plan placed `_cancel_probe_for_close` in Task 2, but Task 1's verify selection (`-k close`) includes those tests.
- **Fix:** `_cancel_probe_for_close` and the flag were added in Task 1; the re-probe on Cancel stayed in Task 2.
- **Commit:** 47921e1

**2. [Rule 2 - Correctness] Pending close drops probe and KiCad-notice results**
- **Issue:** the plan requires the KiCad notice "never shown" after a close, but `_closing` is deliberately not set on entering Finishing, so the result handler would show the notice and log a warning for a dialog that is closing (the old join-then-`_closing` order dropped them). The same held for the cancelled probe's result.
- **Fix:** `_close_pending()` guards `_on_kicad_running` and `_apply_probe_result`; Cancel restarts the probe, which restores the panel.
- **Commit:** 4fe8eca

**3. [Bookkeeping] Plan ledger file not written**
- The harness blocks writes into the shared git directory; the base `3fbb4e9` (verified at start) was used, and `git rev-list --count 3fbb4e9..HEAD` is 3 before this SUMMARY commit.

**Total deviations:** 3. **Impact:** none on the planned behaviour.

## Notes for the orchestrator, verify-work and the owner

- Old blocking-close tests listed in the plan were all rewritten; the open-check-dialog test shows that the Check Atomic Parts dialog stays open while a close waits (at most one git call) and closes with the dialog.
- The scan worker join in `MainWindow.closeEvent` (`self._worker.wait()`) is unchanged: outside REV-04 per the plan's edge note.
- Owner UAT: open Import Part, load a package, press Close right after an edit (while "Updating..." shows). The dialog should grey out under a wait cursor with the Finishing strip and close by itself; Escape must do nothing while the strip shows; Cancel brings the preview back. Close the main window the same way: it should stay until the dialog finished, then close.

## Known Stubs

None.

## Threat Flags

None. T-12-18 (no unbounded join: grep prints 0), T-12-19 and T-12-20 (`_finish_close` runs only with no running worker; `test_close_finishes_after_build_and_closes_package` asserts the package closes after the build end) and T-12-21 (`test_cancelled_close_reprobes`) are covered.

## Self-Check: PASSED

- `kicad_lib_manager/widgets/import_dialog.py`, `kicad_lib_manager/main_window.py`, `tests/test_import_dialog.py` and `tests/test_main_window_import.py` carry the changes; commits 47921e1, 260e979 and 4fe8eca are on the branch.
