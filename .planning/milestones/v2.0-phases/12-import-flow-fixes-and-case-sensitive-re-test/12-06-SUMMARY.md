---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 06
subsystem: kicad-config
tags: [kicad, kicad_common, pyside6, qthread, pytest-qt]

requires:
  - phase: 12-import-flow-fixes-and-case-sensitive-re-test
    provides: "12-03 post-install table step and 12-04 blank-Destination guard (call sites of _sync_path_vars)"
provides:
  - "ConfirmAnswer (WRITE / DECLINE / RETRY) and a sync that asks running() before the confirm"
  - "Off-thread KiCad-open check in MainWindow before the path-variable dialog, after Generate and after an install"
  - "Three-button KiCad-open dialog (Retry, Change anyway, Not now) and a Retry loop"
  - "Confirmed write merged into kicad_common.json as it is now (re-read, re-plan, bounded to three passes)"
  - "conftest teardown that joins QThread children of registered widgets"
affects: [13-TBL-02, verify-work, case-sensitive re-test]

actuals:
  tokens: 34000
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "A confirm callback may answer True/False or a ConfirmAnswer; the sync normalises both"
    - "Re-read after the question, plan again on the fresh content, loop at most _PATH_VAR_PASSES times"
    - "A worker's result is handled on the GUI thread through bound-method slots; a close during the check is deferred, not waited on"

key-files:
  created: []
  modified:
    - kicad_lib_manager/library_scanner.py
    - kicad_lib_manager/main_window.py
    - tests/conftest.py
    - tests/test_kicad_config.py
    - tests/test_main_window.py
    - tests/test_main_window_import.py

key-decisions:
  - "The worker result goes to a bound-method slot and a failed check goes to its own slot (_on_path_var_check_failed), so neither can run the modal dialog on the worker thread; the finished handler follows the import dialog's lambda precedent (verified in a scratch run that it runs on the GUI thread)"
  - "A bad re-read returns only the read Issue (not the earlier 'already set' lines), and the unstable-file warning returns alone, so the log never mixes stale and fresh state"
  - "The unstable-file test varies KICAD_LIB_GITHUB by trailing slashes of the same checkout, so the fresh refusal check does not fire before the pass cap is reached"
  - "Gated test fakes must be released in the test body (try/finally): the conftest join runs before fixture finalizers"

patterns-established:
  - "make_window fixtures carry make.running / make.running_queue / make.kicad_answers / make.kicad_calls / make.check_threads and a settle(qtbot, w) helper"

requirements-completed: [REV-05]

coverage:
  - id: D1
    description: "KiCad-open check runs on a worker thread before the confirm dialog, after Generate and after an install; a second Generate starts no second check"
    requirement: REV-05
    verification:
      - kind: integration
        ref: "tests/test_main_window.py#test_generate_with_kicad_open_change_anyway_writes_and_warns"
        status: pass
      - kind: integration
        ref: "tests/test_main_window_import.py#test_post_install_check_runs_off_gui_thread"
        status: pass
      - kind: integration
        ref: "tests/test_main_window.py#test_second_generate_starts_no_second_check"
        status: pass
    human_judgment: false
  - id: D2
    description: "With KiCad open the dialog offers Retry / Change anyway / Not now; Retry checks again, Change anyway writes and warns, Not now writes nothing"
    requirement: REV-05
    verification:
      - kind: integration
        ref: "tests/test_main_window.py#test_kicad_open_retry_then_closed_asks_yes_no"
        status: pass
      - kind: integration
        ref: "tests/test_main_window.py#test_kicad_open_retry_still_open_asks_again"
        status: pass
      - kind: integration
        ref: "tests/test_main_window.py#test_kicad_open_not_now_writes_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_main_window.py#test_kicad_open_box_texts_and_buttons"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_config.py#test_retry_answer_writes_nothing"
        status: pass
    human_judgment: true
    rationale: "The real modal dialog (wording, button look, default focus) is replaced by a fake in the suite; the owner should see it once with KiCad open"
  - id: D3
    description: "The confirmed write merges the two variables into the file as it is after the dialog, asks again when the needed change moved, writes nothing when none is left, aborts on bad JSON and stops after three passes"
    requirement: REV-05
    verification:
      - kind: unit
        ref: "tests/test_kicad_config.py#test_confirmed_write_keeps_settings_saved_meanwhile"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_config.py#test_changed_list_asks_again"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_config.py#test_no_change_left_writes_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_config.py#test_bad_json_on_reread_aborts"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_config.py#test_unstable_file_stops_after_three_passes"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_config.py#test_running_is_checked_before_confirm"
        status: pass
    human_judgment: false
  - id: D4
    description: "Closing the main window while the check runs returns at once, keeps the window, asks nothing and closes by itself afterwards; test teardown joins running QThread children"
    requirement: REV-05
    verification:
      - kind: integration
        ref: "tests/test_main_window.py#test_close_waits_for_check_without_blocking"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-11-01
status: complete
commits: 5
plan_head_before: 4eed4afce6a441e879a7668c95722ed39159850f
plan_head_after: 4d5ae07649d0e34c6d0d6d4792a61698b7a01b28
---

# Phase 12 Plan 06: KiCad-open check before the confirm, and a write that keeps KiCad's own saves (REV-05) Summary

**The path-variable change now checks for a running KiCad on a worker thread before the dialog, offers Retry / Change anyway / Not now when KiCad is open, and writes the two variables onto kicad_common.json as it is after the dialog, so settings KiCad saved meanwhile survive.**

## Performance

- **Duration:** about 55 min
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 6

## Accomplishments

- `library_scanner.ConfirmAnswer` (WRITE, DECLINE, RETRY); `True`/`False` still mean write/decline. `sync_kicad_path_vars` calls `running()` once before the confirm, returns `config.retry` (INFO) for RETRY before any backup, and rewords the `config.kicad_running` WARNING to "KiCad is open (a, b); it may undo these paths when it exits. If they revert, close KiCad and press Generate Tables."
- `_read_config` and `_plan_changes` helpers, and a loop capped by `_PATH_VAR_PASSES = 3`: after a positive answer the file is read again, the change list re-planned and the refusal re-checked on the fresh vars; a moved list asks again, an empty one writes nothing, invalid JSON or a bad shape aborts, three unstable passes give `config.keeps_changing`. The only-vars check, backup and atomic write run on the fresh parse.
- `MainWindow._sync_path_vars` starts a `TaskWorker` around `kicad_running` (one at a time via `_path_var_busy`); `_on_path_var_check` runs the sync with the found names, the Yes/No question is unchanged when KiCad is closed and `_kicad_open_box` / `_ask_kicad_open` give the three-button dialog when it is open. Retry starts the check again.
- `closeEvent` defers while a check runs (`_close_after_check`, `event.ignore()`), and the finished handler closes the window by itself.
- `tests/conftest.py` `pytest_runtest_teardown` (tryfirst wrapper) joins every `QThread` child of the registered widgets before pytest-qt closes them.

## Task Commits

1. **Task 1 (tracer): off-thread check, KiCad-open dialog, Change anyway writes** - `6eeb0c3` (feat)
2. **Task 2 RED: failing tests for the re-read merge** - `32447f4` (test)
3. **Task 2 GREEN: confirmed write merges into the file as it is now** - `de85c3f` (feat)
4. **Task 3 RED: failing tests for Retry, close during the check** - `edeff53` (test)
5. **Task 3 GREEN: Retry loop and deferred close** - `4d5ae07` (feat)

## TDD Gate Compliance

- **Task 2 RED:** `pytest tests/test_kicad_config.py`, result `6 failed, 49 passed`. Failing on the planned assertions: reworded warning text, `session` key lost (stale copy written), second confirm not called, a write happened though nothing was left to change, no `config.bad_json` on the re-read, one confirm call instead of three. Semantic assessment: each target ran and failed on the intended behaviour, not on setup or import. `test_running_is_checked_before_confirm` and `test_retry_answer_writes_nothing` were already green because the tracer (Task 1) implemented that order and the RETRY return; they pin it. The `gsd_run check tdd-red-evidence` classifier was not run (pytest is not a supported report format).
- **Task 2 GREEN:** `pytest tests/test_kicad_config.py tests/test_kicad_process.py tests/test_layering.py` gave 77 passed.
- **Task 3 RED:** `pytest tests/test_main_window.py tests/test_main_window_import.py -k "..."`, result `4 failed, 49 passed`. Three failed on the planned assertions (Retry did not check again so no Yes/No question followed; Retry then Decline asked once instead of twice; a close during the check closed the window instead of deferring). The fourth, `test_kicad_open_box_texts_and_buttons`, failed on the test's own assumption that `QMessageBox.buttons()` keeps insertion order (the platform orders by role); that was fixed in the test before the RED commit. The second-generate, not-now, off-thread-install tests were already green from Task 1 (the busy guard and the dialog were part of the tracer).
- **Task 3 GREEN:** the selection gave `53 passed`. REFACTOR: none needed.

## Verification

- `pytest tests/test_kicad_config.py tests/test_kicad_process.py tests/test_main_window.py tests/test_main_window_import.py tests/test_layering.py tests/test_import_dialog.py -q`: 400 passed (144 s). `tests/test_import_dialog.py` and `tests/test_main_window_import.py` ran to completion with the new teardown, so it neither hangs nor breaks them.
- All acceptance greps hold: `class ConfirmAnswer`, `_ask_kicad_open`, `_kicad_open_box`, `TaskWorker(`, `kwargs.setdefault("running"` in both fixtures, `tryfirst=True`, `_PATH_VAR_PASSES`, `_read_config`, `config.keeps_changing`, `config.retry`, `_close_after_check` (set in `closeEvent`, read in the finished handler); "Close KiCad and press Generate again" count is 0.
- The full suite was not run (orchestrator runs it after the wave merge). No test was skipped for a missing submodule in the files run.

## Deviations from Plan

None - plan executed as written. Notes on judgment calls, none changing the plan's behaviour:

- The plan's `test_unstable_file_stops_after_three_passes` varies `KICAD_LIB_GITHUB`; a different checkout path would be refused by the fresh refusal check before the third pass, so the test varies the number of trailing slashes of the same checkout instead (same normalised path, never equal to the wanted string).
- The failed-check path goes through a small slot `_on_path_var_check_failed` rather than a lambda, so the modal dialog can never run on the worker thread.
- `test_kicad_open_box_texts_and_buttons` compares buttons by text, because Qt orders `buttons()` by role.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. T-12-14 (re-read before write; `test_confirmed_write_keeps_settings_saved_meanwhile`), T-12-15 (RETRY/DECLINE return before any backup; `test_retry_answer_writes_nothing`, `test_changed_list_asks_again`), T-12-16 (worker thread, deferred close; `test_post_install_check_runs_off_gui_thread`, `test_close_waits_for_check_without_blocking`) and T-12-17 (`test_bad_json_on_reread_aborts`) are implemented and tested.

## Notes for the orchestrator and verify-work

- A gated fake worker in a test must be released inside the test body: the conftest join runs before fixture finalizers and waits up to 60 s per thread.
- The real KiCad-open dialog was never shown (fakes replace it); the owner should see it once with KiCad running (button look, default Retry, wording).

## Self-Check: PASSED

- Modified files exist; commits 6eeb0c3, 32447f4, de85c3f, edeff53 and 4d5ae07 are on the branch (`git rev-list --count 4eed4af..HEAD` gave 5 before this summary).
