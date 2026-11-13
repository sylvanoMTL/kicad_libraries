---
phase: 09-atomic-rule-check-and-scan-detection
plan: 07
subsystem: ui
tags: [pyside6, qdialog, qtreewidget, atomic-check, fix-preview, help]

requires:
  - phase: 09-atomic-rule-check-and-scan-detection
    provides: "09-02 symbol_activated signal and result contract; 09-06 complete_fill, build_preview, preview_text, apply_preview"
provides:
  - "kicad_lib_manager/widgets/atomic_check_dialog.py: AtomicCheckDialog (applied, issues_logged signals; checked_specs(); problems page, fill-in inputs, preview/apply page)"
  - "File > Check Atomic Parts... (Ctrl+Shift+A) and double-click on a marked symbol row open the dialog on the last scan; an applied fix logs one line per written file and starts one rescan"
  - "Help: Ctrl+Shift+A shortcut row and an Atomic parts section on the Library Tree page"
  - "tests/test_atomic_dialog.py (16 tests), 6 atomic tests in tests/test_main_window.py, 2 in tests/test_help_dialog.py"
affects: [09-08, phase-10 install gating, phase-13 migration]

actuals:
  tokens: 9500
  tasks: 3
  commits: 5
plan_head_before: 0752bb2923a767d21d3d74511c06eff6fc184a79
plan_head_after: 845f4599c4e79c09d38e673cf1f31fb061aa9224

tech-stack:
  added: []
  patterns:
    - "Dialog works only from the ScanResult it is given and never scans or runs the check; files are written solely by apply_preview from the preview page's Apply button"
    - "Inputs for fill-ins are item widgets in column 1 of the violation row; each input is run through complete_fill and replaces that row's single input-made fix row (or a reason note)"
    - "Dialog opened with open() and cleaned up in a finished handler (same pattern as the import dialog); closeEvent rejects it"

key-files:
  created:
    - kicad_lib_manager/widgets/atomic_check_dialog.py
    - tests/test_atomic_dialog.py
  modified:
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_main_window.py
    - tests/test_help_dialog.py

key-decisions:
  - "Button counts are singular for one: 'Preview & apply 1 fix' and 'Apply 1 file change' (the plan wording is the plural form)"
  - "A blank typed or cleared input removes the row without a reason note; a reason note appears only for non-blank invalid text"
  - "A preview's own INFO skips and ERROR refusals are shown beside the preview; only an Apply refusal is also emitted through issues_logged"
  - "The summary line counts violations plus findings as problems"

patterns-established:
  - "Check dialog contract for later phases: AtomicCheckDialog(scan_result, repo_root, focus=, backup_root=, running=, pick_model=) with applied(list[Issue]) and issues_logged(list[Issue])"

requirements-completed: [SCAN-03, SCAN-01]

coverage:
  - id: D1
    description: "The menu action and a double-click on a marked symbol open the dialog on the last scan, with that symbol current; no re-check happens on the GUI thread"
    requirement: "SCAN-03"
    verification:
      - kind: integration
        ref: "tests/test_main_window.py#test_atomic_action_opens_dialog_and_apply_rescans"
        status: pass
      - kind: integration
        ref: "tests/test_main_window.py#test_atomic_symbol_activated_opens_dialog_with_that_symbol_current"
        status: pass
      - kind: unit
        ref: "tests/test_atomic_dialog.py#test_the_dialog_never_scans_or_runs_the_check"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every violation and finding is listed once; safe fixes are ticked rows with Select All and Deselect All and a live 'Preview & apply N fixes' count"
    requirement: "SCAN-03"
    verification:
      - kind: unit
        ref: "tests/test_atomic_dialog.py#test_every_violation_and_every_finding_is_listed_once"
        status: pass
      - kind: unit
        ref: "tests/test_atomic_dialog.py#test_deselect_all_and_select_all_move_every_fix_row"
        status: pass
    human_judgment: false
  - id: D3
    description: "Typed Datasheet and Description, a picked 3D model and a value choice between disagreeing duplicates are validated like the scan and become one ticked fix row"
    requirement: "SCAN-03"
    verification:
      - kind: unit
        ref: "tests/test_atomic_dialog.py (-k 'typed or picked or disagreeing')"
        status: pass
    human_judgment: false
  - id: D4
    description: "Only the Apply button on the preview page writes; a file changed after the preview is refused, shown in the dialog and logged; the KiCad-running warning shows only while KiCad runs"
    requirement: "SCAN-03"
    verification:
      - kind: unit
        ref: "tests/test_atomic_dialog.py#test_preview_never_applies_and_only_the_apply_button_does"
        status: pass
      - kind: unit
        ref: "tests/test_atomic_dialog.py#test_a_file_changed_after_the_preview_is_refused_and_left_alone"
        status: pass
      - kind: unit
        ref: "tests/test_atomic_dialog.py#test_the_running_warning_shows_only_while_kicad_runs"
        status: pass
    human_judgment: false
  - id: D5
    description: "The action is disabled while a scan runs, a second request opens no second dialog, closing the window rejects the dialog; Help lists the shortcut and explains the marks"
    requirement: "SCAN-01"
    verification:
      - kind: integration
        ref: "tests/test_main_window.py (-k atomic, 6 tests)"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_library_tree_explains_the_atomic_marks"
        status: pass
    human_judgment: false
  - id: D6
    description: "Layout, wording and feel of the dialog in the real window (tree column widths, fill-in widgets, preview page, amber warning) and of the Help section"
    verification: []
    human_judgment: true
    rationale: "Offscreen tests assert rows, texts, states and signals, not whether the dialog reads well or the inputs are easy to hit"

duration: 9min
completed: 2026-10-26
status: complete
---

# Phase 9 Plan 07: Check Atomic Parts dialog Summary

**Check Atomic Parts dialog (Ctrl+Shift+A or double-click on a marked symbol) that lists every problem of the last scan with ticked safe fixes, fill-ins for Datasheet, Description and 3D model, a value choice for conflicting duplicates, a before/after preview with a KiCad-running warning, and an Apply that writes only from the preview page and triggers one rescan**

## Performance

- **Duration:** 9 min
- **Started:** 2026-10-26T13:58:44Z
- **Completed:** 2026-10-26T14:07:40Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 6 (2 created: atomic_check_dialog.py, test_atomic_dialog.py)

## Accomplishments

- `AtomicCheckDialog` builds a two-column tree from the last `ScanResult` only: one row per symbol with problems (amber when failing), a row per violation and finding, a ticked fix row per `FixSpec`, and "No one-click fix" where nothing is offered. Select All, Deselect All and a live "Preview & apply N fixes" button.
- Fill-ins: a line edit for Datasheet and Description, a "Choose 3D model..." button, and a "Pick the value to keep" combo for disagreeing duplicates. Each input goes through `complete_fill`; a valid value becomes the one ticked fix row of that problem (replaced, never doubled), an invalid one shows the plain reason.
- Preview page shows the exact before/after text of every file, the amber KiCad-running warning only while KiCad runs, and the preview's own notes. Apply is the only caller of `apply_preview`; success emits `applied`, closes the dialog and the main window logs one line per file and rescans once; a refusal (for example a file changed after the preview) is shown in the dialog and emitted for the log with nothing written.
- Main window: menu action with Ctrl+Shift+A, `symbol_activated` wiring, disabled while a scan runs, one dialog at a time, rejected on close. Help lists the shortcut and has an "Atomic parts" section built from the theme constants.

## Task Commits

1. **Task 1: menu action, dialog, one fix to rescan (tracer)** - `5195823` (feat)
2. **Task 2 RED: fill-ins, value choice, focus, empty state tests** - `6975b47` (test)
3. **Task 2 GREEN: fill-in inputs, value choice, focus, empty state** - `58b9742` (feat)
4. **Task 3 RED: double-click, scan disabling, close and Help tests** - `74c25a4` (test)
5. **Task 3 GREEN: tree double-click, scan disabling, close handling, Help** - `845f459` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified

- `kicad_lib_manager/widgets/atomic_check_dialog.py` - the dialog (new)
- `kicad_lib_manager/main_window.py` - `ATOMIC_BACKUP_ROOT` seam, `_act_check_atomic`, `_open_atomic_check`, `_on_atomic_fixes_applied`, `_on_atomic_dialog_finished`, `_on_symbol_activated`, close handling
- `kicad_lib_manager/widgets/help_dialog.py` - shortcut row and Atomic parts section
- `tests/test_atomic_dialog.py` - 16 dialog tests over a synthetic Atomic_ tree in tmp_path (new)
- `tests/test_main_window.py` - 6 atomic tests; `tests/test_help_dialog.py` - shortcut and Library Tree tests

## Decisions Made

See `key-decisions`. Singular wording for one fix or one file change is the only visible deviation from the plan's literal strings.

## Deviations from Plan

None - plan executed exactly as written, apart from the singular wording noted under Decisions Made (no behaviour or contract changed).

**Total deviations:** 0 auto-fixed
**Impact on plan:** None.

## TDD Gate Compliance

Task 1 is a tracer (one production commit with its tests), carved to its own scope so Task 2 has an honest RED.

- **Task 2 RED (`6975b47`):** 6 of 15 tests failed on planned assertions: `isinstance(None, QLineEdit/QPushButton/QComboBox)` for the missing input widgets, `currentItem()` None for focus, and no empty-state label. The 9 tests for behaviour Task 1 already had (listing, Select/Deselect All, running label, stale refusal, preview-never-applies, no scan, plain wording) passed and act as guards. Semantic assessment: the target tests executed and failed on the intended missing behaviour, not on import or fixture faults. The `check tdd-red-evidence` classifier was not run (plain pytest output is not a supported format).
- **Task 3 RED (`74c25a4`):** 5 of 7 new tests failed on planned assertions (dialog not opened by the signal, action still enabled during a scan, dialog not cleared on close, shortcut and Library Tree text missing). The no-scan-result and second-open tests already held after Task 1 and are guards. Semantic assessment: failures are the planned assertions.
- No REFACTOR commit was needed.

## Issues Encountered

- `Custom/` and `WurthElektronik/KiCad-Library` are not checked out in this worktree; every dialog test writes only into tmp_path trees and none touches a real Custom/.
- The plan's acceptance grep for `Ctrl+Shift+A` in `help_dialog.py` expects one line; it prints two, because the plan also asks the Library Tree text to name the shortcut. Both are intended.
- Verification run: `tests/test_main_window.py tests/test_help_dialog.py tests/test_atomic_dialog.py tests/test_library_table_atomic.py tests/test_library_table_widget.py` gave 116 passed; `-k atomic` on test_main_window gave 6 passed; `tests/test_layering.py tests/test_importer_layering.py tests/test_main_window_import.py tests/test_atomic_fixes.py tests/test_atomic_scan.py` gave 145 passed. The full `-m "not wurth"` suite is left to the orchestrator's post-merge gate.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. T-09-18 (only the preview page's Apply calls `apply_preview`, tested by recording calls), T-09-19 (running warning on the preview page, stale refusal tested), T-09-20 (summary, reason, running and issue labels are `PlainText`; rows are plain items), T-09-21 (typed Datasheet goes through `complete_fill` and `datasheet_problem`, never fetched) are implemented and tested.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 09-08 can drive the dialog contract above if its UAT needs it; the dialog takes `backup_root`, `running` and `pick_model` seams for tests.
- Open for the owner (coverage D6): how the dialog and the Help section look and read in the real window.

## Self-Check: PASSED

- FOUND: kicad_lib_manager/widgets/atomic_check_dialog.py, tests/test_atomic_dialog.py, main_window.py and help_dialog.py changes
- FOUND commits: 5195823, 6975b47, 58b9742, 74c25a4, 845f459
- Targeted pytest sets above passed

---
*Phase: 09-atomic-rule-check-and-scan-detection*
*Completed: 2026-10-26*
