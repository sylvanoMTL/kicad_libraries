---
phase: 13-atomic-migration-and-kicad-setup
plan: 07
subsystem: kicad-config
tags: [kicad, qt, menu-action, chooser, pins, help-docs]

# Dependency graph
requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "kicad_setup.sync_kicad_chooser (plan 13-02) and the REV-05 config-write contract this action calls"
provides:
  - "MainWindow._act_setup_chooser (Ctrl+Shift+K) and the full off-thread KiCad-open/Retry/busy/close flow around sync_kicad_chooser (TBL-02)"
  - "_kicad_open_box(changes, names, *, intro=None, lines=None, outro=None) -- keyword-only overrides reused by the chooser confirm; today's path-variable text is the unchanged default"
  - "User Guide: Generating Tables page explains Set Up KiCad Chooser in its own section; Keyboard Shortcuts lists Ctrl+Shift+K"
affects: ["13-16 (migration Result view Set Up KiCad Chooser button reuses _on_setup_chooser via a signal)"]

# Actuals (#2632)
actuals:
  tokens: 6967
  tasks: 2
  commits: 3
  plan_head_before: 7b4b331a6d823ca4f1bf5fcecbb7e87c94a870f6
  plan_head_after: a38cd80d65aa8339cdc0e7866265c3e4eb6426f8

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Chooser setup copies the path-variable off-thread check/confirm/close shape exactly (_start_chooser_check/_on_chooser_check/_on_chooser_check_finished mirror _start_path_var_check/_on_path_var_check/_on_path_var_check_finished; closeEvent defers the same way for both)"
    - "_kicad_open_box grew keyword-only intro/lines/outro instead of a second dialog builder, so the chooser's three-button KiCad-open dialog and the existing path-variable one share one implementation; defaults reproduce the path-variable text byte for byte"

key-files:
  created:
    - tests/test_main_window_chooser.py
  modified:
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_help_dialog.py

key-decisions:
  - "Task 1 (tracer) shipped a self-contained _ask_chooser_kicad_open stub so the end-to-end confirmed-write slice worked and was verified before any expansion; Task 2 (tdd) then gave _kicad_open_box its keyword-only parameters and rewired _ask_chooser_kicad_open to delegate to it, removing the duplicate dialog-building code. This two-step construction is captured as separate commits (tracer verify -> RED -> GREEN) matching the plan's own task split."
  - "No REFACTOR commit for Task 2: after the GREEN step _ask_chooser_kicad_open and _ask_kicad_open both delegate cleanly to the one _kicad_open_box, so no further cleanup was needed."

requirements-completed: [TBL-02]

coverage:
  - id: D1
    description: "Set Up KiCad Chooser... (Ctrl+Shift+K) runs the off-thread KiCad-open check, then one window-modal confirm listing every old -> new value, then the write"
    requirement: TBL-02
    verification:
      - kind: unit
        ref: "tests/test_main_window_chooser.py#test_setup_chooser_confirmed_writes_both_files"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_chooser.py#test_setup_chooser_menu_entry"
        status: pass
    human_judgment: false
  - id: D2
    description: "With KiCad open the confirm names the open programs and offers Retry (default)/Change anyway/Not now; Retry checks again; nothing is written without Yes or Change anyway"
    requirement: TBL-02
    verification:
      - kind: unit
        ref: "tests/test_main_window_chooser.py#test_chooser_kicad_open_change_anyway_writes"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_chooser.py#test_chooser_retry_then_closed_asks_yes_no"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_chooser.py#test_chooser_not_now_writes_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_chooser.py#test_chooser_box_texts"
        status: pass
    human_judgment: false
  - id: D3
    description: "The pins are read from the tables in the Destination folder; an empty Destination box reads/writes nothing and the log says so"
    requirement: TBL-02
    verification:
      - kind: unit
        ref: "tests/test_main_window_chooser.py#test_no_destination_writes_nothing"
        status: pass
    human_judgment: false
  - id: D4
    description: "A second click while a check runs starts nothing, and closing the main window during the check waits for it without blocking the GUI thread"
    requirement: TBL-02
    verification:
      - kind: unit
        ref: "tests/test_main_window_chooser.py#test_second_click_starts_no_second_check"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_chooser.py#test_close_waits_for_chooser_check"
        status: pass
    human_judgment: false
  - id: D5
    description: "The path-variable dialogs keep their exact texts; the chooser has its own plain-language title and wording"
    requirement: TBL-02
    verification:
      - kind: unit
        ref: "tests/test_main_window.py#test_kicad_open_box_texts_and_buttons"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_chooser.py#test_chooser_box_texts"
        status: pass
    human_judgment: false
  - id: D6
    description: "The User Guide's Generating Tables page explains Set Up KiCad Chooser in a section of its own, and the Keyboard Shortcuts page lists Ctrl+Shift+K"
    requirement: TBL-02
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_generating_page_explains_the_chooser"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_shortcuts_complete"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_outline_numbers_follow_the_menu_order"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 07: KiCad Chooser Menu Action Summary

**"Set Up KiCad Chooser..." (Ctrl+Shift+K) now runs the off-thread KiCad-open check, one confirmed Yes/No (or Retry/Change anyway/Not now) dialog, and the two-file write from plan 13-02's `sync_kicad_chooser`, with its own User Guide section.**

## Performance

- **Duration:** 45 min
- **Tasks:** 2 completed
- **Files created:** 1 (`tests/test_main_window_chooser.py`)
- **Files modified:** 3 (`kicad_lib_manager/main_window.py`, `kicad_lib_manager/widgets/help_dialog.py`, `tests/test_help_dialog.py`)

## Accomplishments

- `_act_setup_chooser` (File menu, `Ctrl+Shift+K`) runs `_on_setup_chooser`, which checks `kicad_running()` off the GUI thread via a `TaskWorker` (mirroring `_start_path_var_check`), then calls `kicad_setup.sync_kicad_chooser` with a `confirm` wired to a window-modal dialog.
- `_confirm_chooser_changes` shows either a plain Yes/No question ("Set up KiCad's chooser?", listing every "Pinned symbol libraries" / "Pinned footprint libraries" / "Symbol chooser columns" old -> new line) or, when KiCad is open, the three-button Retry/Change anyway/Not now dialog via `_ask_chooser_kicad_open`.
- `_kicad_open_box` grew keyword-only `intro`, `lines`, `outro` parameters whose defaults reproduce today's path-variable dialog text byte for byte; `_ask_chooser_kicad_open` and `_ask_kicad_open` both delegate to it, so there is one dialog builder for both confirms.
- An empty Destination box logs `_NO_DEST_CHOOSER_TEXT` ("No destination folder set; KiCad's chooser not set up") and starts no check; a second click while a check runs is a no-op; closing the main window during the check defers via `_close_after_chooser` the same way `_close_after_check` defers for the path-variable check.
- The User Guide's Generating Tables page documents "Set Up KiCad Chooser" in its own `<h3>KiCad chooser</h3>` section (pins, MPN/Manufacturer columns, Retry/Change anyway/Not now, the worktree/other-checkout refusal, idempotence); Keyboard Shortcuts lists `Ctrl+Shift+K` after `Ctrl+Shift+A`.

## Task Commits

Each task was committed atomically; Task 2 (`tdd="true"`) followed RED -> GREEN (no REFACTOR commit needed):

1. **Task 1: The menu action checks for KiCad off-thread, asks once, and writes both files (tracer)** - `dd13f58` (feat)
2. **Task 2a: RED - failing tests for the keyword KiCad-open box and chooser help docs** - `e5d0fbc` (test)
2. **Task 2b: GREEN - keyword `_kicad_open_box`, rewired confirm, and the User Guide section** - `a38cd80` (feat)

## Files Created/Modified

- `kicad_lib_manager/main_window.py` - `SETUP_CHOOSER_TEXT`, `_NO_DEST_CHOOSER_TEXT` constants; `_act_setup_chooser` wired into `_build_menu` and `_set_scan_running`; `_chooser_busy`/`_chooser_check`/`_chooser_workers`/`_close_after_chooser` state; `_on_setup_chooser`, `_start_chooser_check`, `_on_chooser_check_failed`, `_on_chooser_check`, `_on_chooser_check_finished`, `_chooser_lines` (static), `_confirm_chooser_changes`, `_ask_chooser_kicad_open`; `_kicad_open_box` keyword-only `intro`/`lines`/`outro`; `closeEvent` defers while `_chooser_check` is running.
- `kicad_lib_manager/widgets/help_dialog.py` - `<h3>KiCad chooser</h3>` section at the end of `HELP_PAGES["generating"]`; `Ctrl+Shift+K` row in `HELP_PAGES["shortcuts"]` after the `Ctrl+Shift+A` row.
- `tests/test_main_window_chooser.py` (new) - own fixture (isolated QSettings, patched `REPO_ROOT`/`load_kicad_fp_dir`/`scan_all`/`kicad_running`, `sync_kicad_chooser` wrapped with a tmp `config_base`/`backup_root`, patched `_question` and `_ask_chooser_kicad_open`); 10 behavior tests covering the menu entry, confirmed write, KiCad-open Change-anyway/Retry/Not-now, dialog texts, busy guard, close-during-check, and no-destination.
- `tests/test_help_dialog.py` - `test_help_shortcuts_complete` and the outline anchor count (`20` -> `21`) updated; new `test_help_generating_page_explains_the_chooser`.

## Decisions Made

- Task 1 shipped a self-contained `_ask_chooser_kicad_open` (its own inline `QMessageBox` construction) so the tracer's end-to-end confirmed-write slice could be verified before any expansion, per the tracer feedback gate. Task 2 then gave `_kicad_open_box` its keyword-only parameters and rewired `_ask_chooser_kicad_open` to delegate to it, deleting the duplicate dialog code — the plan's own two-task split maps directly onto this tracer-then-expand shape.
- `_confirm_chooser_changes`'s plain-Yes/No path reuses `_question` (the sanctioned exception already documented above `_confirm_path_var_changes`); the comment above that method was extended to name the chooser confirm as the same sanctioned exception rather than duplicating the rationale.
- The Destination box's default value (`REPO_ROOT` when no history exists) was used directly in the test fixture instead of calling `_dest_combo.setEditText`, since `_write_tables` can simply write into the same tmp `repo` directory that `REPO_ROOT` is patched to.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` and `<behavior>` specifications were implemented as described. Task 2's TDD cycle surfaced that several of its own behavior tests (`test_chooser_kicad_open_change_anyway_writes`, `test_chooser_retry_then_closed_asks_yes_no`, `test_chooser_not_now_writes_nothing`, `test_second_click_starts_no_second_check`, `test_close_waits_for_chooser_check`, `test_no_destination_writes_nothing`) already passed against Task 1's generic worker/busy/close implementation and its test-fixture patch of `_ask_chooser_kicad_open` — this is expected (Task 1 deliberately implemented the full generic flow as a tracer), not a plan gap. The 4 tests that did fail for the right reason before Task 2's GREEN commit (`test_chooser_box_texts`, `test_help_shortcuts_complete`, `test_help_generating_page_explains_the_chooser`, `test_help_outline_numbers_follow_the_menu_order`) are exactly the behavior Task 2's `<action>` describes (the keyword `_kicad_open_box` and the help docs).

## TDD Gate Compliance

| Task | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| 2 (keyword KiCad-open box, chooser confirm rewire, User Guide) | ✓ `e5d0fbc` (4/10 new/changed assertions failing for the right reason: `TypeError` on the unexpected `intro` keyword, and three missing-help-content `AssertionError`s) | ✓ `a38cd80` (178/178 pass across the plan's full verification command) | - (no refactor needed; `_ask_chooser_kicad_open`/`_ask_kicad_open` both already delegate cleanly to `_kicad_open_box`) | Pass |

Note: this plan's frontmatter carries `type: execute`, not `type: tdd`, so the machine-validated RED-evidence gate (`gsd_run check tdd-red-evidence`) and `workflow.tdd_mode` plan-level enforcement were not active (`workflow.tdd_mode` is absent from `.planning/config.json`, consistent with plan 13-02's own note). The RED -> GREEN discipline above was still followed in full for the `tdd="true"` task per the executor's per-task instruction. The other 6 new/updated tests in the RED commit already passed before the GREEN commit (see Deviations) because Task 1's tracer implementation already covered that generic behavior; this is disclosed rather than treated as additional RED evidence.

## Issues Encountered

None beyond the note above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- TBL-02 is fully wired into the app: one confirmed menu action sets up KiCad 10's chooser, with the same KiCad-open/refusal/backup behaviour as the path-variable sync.
- `_on_setup_chooser` is ready for plan 13-16's migration Result view "Set Up KiCad Chooser" button to call through a signal, as noted in this plan's objective.
- The full plan-level `<verification>` command passed (178 tests: `test_main_window_chooser.py`, `test_main_window.py`, `test_help_dialog.py`, `test_plain_names.py`, `test_kicad_setup.py`). `test_layering.py` and `test_main_window_import.py` were also re-run as a broader regression check (80 tests, all passing) since `main_window.py` and `help_dialog.py` both changed; this was not required by this plan's own done-criteria and is not blocking.
- No blockers for the next plan in this phase.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: tests/test_main_window_chooser.py
- FOUND: kicad_lib_manager/main_window.py
- FOUND: kicad_lib_manager/widgets/help_dialog.py
- FOUND commit: dd13f58 (Task 1)
- FOUND commit: e5d0fbc (Task 2 RED)
- FOUND commit: a38cd80 (Task 2 GREEN)
- Plan-level `<verification>` command (178 tests: test_main_window_chooser.py, test_main_window.py, test_help_dialog.py, test_plain_names.py, test_kicad_setup.py) re-run: PASSED
- Both tasks' acceptance-criteria greps: PASSED
- `requirements.ready-ids` for TBL-02: 0/1 ready (blocked by sibling plan 13-18, which has no SUMMARY yet) -- REQUIREMENTS.md correctly left unmarked
