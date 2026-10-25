---
phase: 06-git-commit-step
plan: 06
subsystem: ui
tags: [pyside6, close-guard, help-dialog, git-commit-step]

requires:
  - phase: 06-git-commit-step
    provides: "ImportDialog.is_committing() (06-01) and the finished CommitPanel labels (06-03)"
provides:
  - "MainWindow.closeEvent refuses to close while the Import dialog installs or runs a git job (D-07)"
  - "Commit section of the Importing Parts help page, checked against a real CommitPanel"
affects: [06-08]

actuals:
  tokens: 3200
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Help text checked against labels read from a real widget (extends the Phase 5 help test pattern)"

key-files:
  created: []
  modified:
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_main_window_import.py
    - tests/test_help_dialog.py

key-decisions:
  - "The Commit help section is static text with no formatted value; the test asserts no brace, path or vendor string in the section (T-06-25)"
  - "The Commit button is checked as a button name (<b>Commit</b>) rather than by the bare word, which would match any prose"

requirements-completed: [GIT-01, GIT-05]

coverage:
  - id: D1
    description: "The main window ignores a close request while the Import dialog installs or runs a probe, switch or commit; closing otherwise behaves as before"
    requirement: GIT-01
    verification:
      - kind: unit
        ref: "tests/test_main_window_import.py#test_main_window_close_ignored_while_committing"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_main_window_close_ignored_while_installing"
        status: pass
    human_judgment: false
  - id: D2
    description: "The Importing Parts help page has a Commit section after Install and result that uses the panel's real labels and states: fixed file list, editable message, parent checkbox, amber files, Switch to main, hooks, never pushed, closing without committing"
    requirement: GIT-05
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_import_page_describes_commit_step"
        status: pass
    human_judgment: false
  - id: D3
    description: "The help wording reads clearly and matches what a user sees in the dialog (the test checks labels and key words only)"
    verification: []
    human_judgment: true
    rationale: "Wording quality and accuracy against the wired dialog behaviour (plan 06-08) needs a human read"

duration: 14min
completed: 2026-10-22
status: complete
plan_head_before: b34f2a5b24cbf4e2600eff24fc41b5f86f68a411
plan_head_after: cd4726af0fa6e5be38bda97d4ae8bde9b0a1b4e7
commits: 4
---

# Phase 6 Plan 06: Close Guard and Commit Help Summary

**The main window now refuses to close while the Import dialog runs an install or a git probe, switch or commit, and the Importing Parts help page documents the commit step using the panel's own labels.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-10-22T18:27:51Z
- **Tasks:** 2 (both TDD: RED then GREEN)
- **Files modified:** 4

## Accomplishments

- `MainWindow.closeEvent` calls `event.ignore()` when `dialog.is_installing() or dialog.is_committing()`, before `dialog.reject()` is reached (D-07, T-06-24).
- `HELP_PAGES["importing"]` has a `<h3>Commit</h3>` section between "Install and result" and "Library tables" covering the file list, editable message, parent checkbox, amber files, other changes, Switch to main or refusal, hooks, never pushed, and closing without committing.
- `test_help_import_page_describes_commit_step` builds a real `CommitPanel` in the ready and offer_switch states and requires "Files to commit", "Also commit the Custom ref in the parent repo" and "Switch to main" both in the panel and on the page, so label drift fails the test.

## Task Commits

1. **Task 1 RED:** `9f11502` (test) - close test; `RecordingDialog.is_committing`
2. **Task 1 GREEN:** `78947f0` (feat) - closeEvent guard
3. **Task 2 RED:** `f5ba5f1` (test) - help test against a real panel
4. **Task 2 GREEN:** `cd4726a` (feat) - Commit help section

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `kicad_lib_manager/main_window.py` - closeEvent also refuses on `is_committing()`
- `kicad_lib_manager/widgets/help_dialog.py` - Commit section of the importing page
- `tests/test_main_window_import.py` - `RecordingDialog.is_committing`, `test_main_window_close_ignored_while_committing`
- `tests/test_help_dialog.py` - `test_help_import_page_describes_commit_step` with its own small `CommitPlan` builder

## TDD Gate Compliance

- **Task 1 RED (`9f11502`):** the new test failed because `closeEvent` reached `dialog.reject()` (the stand-in's `pytest.fail("rejected")`), the planned behaviour gap: a dialog that is committing was not respected. The existing installing test still passed. `gsd_run check tdd-red-evidence` was not run (pytest has no supported report format here); the assessment is manual.
- **Task 2 RED (`f5ba5f1`):** after a test-code fix (a `findChildren` call with a tuple), the test failed on `assert "Files to commit" in page` after the panel check passed, which is the planned assertion.
- **GREEN:** both tests pass. No REFACTOR commits.

## Decisions Made

- The Commit button is asserted as `<b>Commit</b>` in the raw page, since the bare word "Commit" appears in any prose.
- The static-text check scans the section for `{`, `%s`, the temp path and the vendor name.

## Deviations from Plan

None - plan executed exactly as written. (One fix inside the new test before its RED commit: `findChildren` does not take a tuple, so a small `_panel_texts` helper was used.)

## Issues Encountered

- The `Custom` and `WurthElektronik` submodules are not checked out in the worktree, so 72 tests skip as expected. `pytest -q -m "not kicad_cli"` gave 1634 passed, 72 skipped, 0 failed. The orchestrator re-runs the full suite in the main checkout.

## Known Stubs

None.

## Threat Flags

None. T-06-24 is mitigated by the close guard and its test; T-06-25 by the static help text and its test.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The help text describes the D-02 log line and the switch round trip before plan 06-08 wires them; 06-08's dialog tests and UAT should confirm the page matches the behaviour.

## Self-Check: PASSED

- Modified files exist: main_window.py, help_dialog.py, test_main_window_import.py, test_help_dialog.py
- Commits 9f11502, 78947f0, f5ba5f1, cd4726a are ancestors of HEAD
- `<h3>Commit</h3>`, `Also commit the Custom ref in the parent repo`, `Files to commit`, `Switch to main` all present in help_dialog.py; `is_committing()` present in closeEvent

---
*Phase: 06-git-commit-step*
*Completed: 2026-10-22*
