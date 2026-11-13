---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 09
subsystem: import-dialog
tags: [pyside6, qthread, probe, cancel, reprobe, close-lock]
status: complete

requires:
  - phase: 11-commit-gate-and-commit-panel-fixes
    provides: "CommitPanel.begin_reprobe / committed() (11-04); probe_commit(cancelled=...) (11-06)"
provides:
  - "The read-only probe holds no Close lock and is cancelled cooperatively on close (IN-02, REV-11)"
  - "A refused or failed commit is followed by a fresh probe that keeps the typed message and parent choice (REV-10, D-11)"
  - "Install Part carries the primary button style (UI-02, D-19)"
affects: [11-10]

actuals:
  tokens: 14000
  tasks: 2
  commits: 2

plan_head_before: de28376b44fdf00a3f020cacfbaabab03354cff5
plan_head_after: 5943033a47729c8838686b4332447c2660920cd4

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_import_dialog.py
    - tests/test_main_window_import.py
    - tests/test_help_dialog.py

key-decisions:
  - "Probe worker is tracked in _probe_worker (not _git_worker); is_committing() now means Switch to main or Commit only"
  - "A newer probe replaces _probe_cancels with its own Event after setting the older ones, so the list never grows"
  - "open_path is also refused while a probe runs (it was refused before through is_committing)"
  - "main_window.closeEvent needed no change: it only consults is_installing and is_committing"

requirements-completed: [REV-10, REV-11, UI-02]
---

# Phase 11 Plan 09: Close during the probe, re-probe after refusal Summary

The import dialog no longer locks Close while the read-only commit check runs, cancels that check through a `threading.Event` on close, drops results from superseded probes, and re-probes after every outcome the panel does not count as committed.

## What was built

- Task 1 (`df84c7b`): `_probe_worker`, `_probe_cancels`, `is_probing()`. `_start_probe(*, reprobe=False)` spawns `core.probe_commit(cp, cancelled=ev.is_set)` without calling `_set_git_worker`, so Close stays enabled. `_on_probe_done` / `_on_probe_failed` drop any result whose worker is not the current probe. Commit and Switch requests are refused while a probe runs. `_shutdown` sets every probe Event before waiting for workers. Existing `is_committing()` waits in tests that meant "the probe finished" now use `is_probing()`.
- Task 2 (`5943033`): `_on_commit_done` calls `_start_probe(reprobe=True)` when `not panel.committed()` (covers a failed parent-only bump); `_on_switch_done` re-probes with `reprobe=True` so the message survives; `Install Part` uses `PRIMARY_BUTTON_QSS`; the Help Commit section says Commit or Switch to main keep the windows open and the first check does not.

## Tests added

`test_close_during_probe_cancels_and_closes`, `test_close_button_enabled_while_probing` (esc, reject, button), `test_stale_probe_result_is_dropped`, `test_main_window_closes_while_probe_runs`, `test_refusal_reprobes_and_keeps_input`, `test_refusal_reprobe_replaced_by_own_refusal`, `test_parent_only_failure_reprobes_in_dialog`, `test_switch_reprobe_keeps_message`, `test_install_button_primary`, Help text assertions. Run: `tests/test_import_dialog.py tests/test_help_dialog.py tests/test_main_window_import.py tests/test_commit_panel.py` gave 287 passed.

## Deviations from Plan

- **[Rule 3 - Blocking] open_path guard:** added `or self.is_probing()` so a new package cannot open under a running probe (previously guarded by `is_committing()`).
- `test_close_button_enabled_while_probing` is parametrized instead of looping inside one test (the second dialog in one test never finished installing).

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

Commits `df84c7b` and `5943033` exist on the branch; the five modified files are committed.
