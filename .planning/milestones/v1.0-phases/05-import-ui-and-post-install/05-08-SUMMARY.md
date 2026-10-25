---
phase: 05-import-ui-and-post-install
plan: 08
subsystem: ui
tags: [pyside6, drag-and-drop, qmainwindow, help-dialog, tdd]

requires:
  - phase: 05-import-ui-and-post-install
    provides: "05-01 _open_import and _act_import, 05-03 theme.PRIMARY_BUTTON_QSS and AMBER, 05-04 post-install flow"
provides:
  - "Drop of one .zip or folder onto the main window opens the Import Part dialog (UX-01)"
  - "Import Part... toolbar button and a busy state covering every import entry point"
  - "Generate Tables button on the shared primary style"
  - "Importing Parts help page, Collision status text, Ctrl+I and Ctrl+Shift+R shortcuts"
affects: [05-11 (Task 3 re-checks the Importing Parts page against the finished widgets)]

actuals:
  tokens: 9500
  tasks: 2
  commits: 4

plan_head_before: 6ec6b1bc8cd7bb9f256b50da1b5261df2088bd7e
plan_head_after: ca0d3d64d1b0849f702b6a1683aff529eeff111b

tech-stack:
  added: []
  patterns:
    - "Single _import_busy() predicate shared by drag-enter, drag-move, drop and _open_import"
    - "Drag/drop tests build QDropEvent/QDragEnterEvent offscreen and call the handlers directly"

key-files:
  created:
    - tests/test_help_dialog.py
  modified:
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_main_window_import.py

key-decisions:
  - "The busy refusal (event.ignore plus the 3 s status-bar line) lives in one helper, _refuse_busy_drag, used by both dragEnterEvent and dropEvent so the drop re-check cannot drift from the enter check"
  - "dragMoveEvent applies the same accept/ignore rule but shows no message, as the UI-SPEC says"
  - "A non-local URL is refused with the same 'not a .zip file or a folder' line, using QUrl.fileName() as the base name"

patterns-established:
  - "Refusals of a drop go to the log panel at warning level, never a QMessageBox"

requirements-completed: [UX-01]

coverage:
  - id: D1
    description: "Dropping one local .zip (any case) or one folder opens the import dialog with that package; several paths, a wrong type or a non-local URL are refused with the exact UI-SPEC warning lines"
    requirement: UX-01
    verification:
      - kind: unit
        ref: "tests/test_main_window_import.py#test_drop_one_zip_opens_dialog"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_drop_several_paths_refused"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_drop_wrong_type_refused"
        status: pass
    human_judgment: false
  - id: D2
    description: "Drag and drop and every import entry point are refused while a scan runs or the import dialog is open; Select All and Deselect All join the busy controls"
    requirement: UX-01
    verification:
      - kind: unit
        ref: "tests/test_main_window_import.py#test_drop_refused_while_busy"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_drag_enter_accepts_urls_when_idle"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_busy_state_controls"
        status: pass
    human_judgment: false
  - id: D3
    description: "Import Part... is the first toolbar widget followed by 16 px spacing; Generate Tables uses theme.PRIMARY_BUTTON_QSS"
    verification:
      - kind: unit
        ref: "tests/test_main_window_import.py#test_toolbar_import_button_first"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_generate_button_primary_style"
        status: pass
    human_judgment: true
    rationale: "The 28 px height and the greyed disabled look are visual; tests assert the stylesheet identity only"
  - id: D4
    description: "Help documents the import flow, the Collision status with the AMBER span, Ctrl+I and Ctrl+Shift+R"
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_import_page"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_library_tree_collision_and_amber"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_shortcuts_complete"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_dialog_opens_importing_page"
        status: pass
    human_judgment: true
    rationale: "Wording accuracy against the not-yet-built conflict rows and result view is checked by plan 05-11 Task 3"

duration: 12min
completed: 2026-10-22
status: complete
---

# Phase 5 Plan 08: Drop-to-import, busy state and import help Summary

**Drag and drop of one zip or folder onto the main window opens the Import Part dialog, with exact refusal lines, a scan-aware busy state across every import entry point, and a new Importing Parts help page.**

## Performance

- **Duration:** about 12 min
- **Started:** 2026-10-22T10:15Z
- **Completed:** 2026-10-22T10:27Z
- **Tasks:** 2 (TDD: 2 RED commits, 2 GREEN commits)
- **Files modified:** 4 (1 created)

## Accomplishments
- UX-01: `setAcceptDrops(True)` with `dragEnterEvent`, `dragMoveEvent` and `dropEvent`. One local `.zip` (suffix compared case-insensitively) or one folder calls `self._open_import(path)`, the same entry the menu uses.
- Refusals are logged at warning level with the UI-SPEC copy: several paths, wrong type (base name only), non-local URL. While busy the event is ignored and the status bar shows "Import is unavailable while a scan is running." for 3 s; `dropEvent` re-checks because a scan can start between enter and drop.
- Toolbar "Import Part..." button first, 16 px spacing, tooltip "Import a vendor package (Ctrl+I)", not accent-styled.
- `_set_scan_running` also toggles the Import button, Select All and Deselect All (02-UI-REVIEW leftover). `_open_import` now uses the shared `_import_busy()`.
- Generate Tables uses `theme.PRIMARY_BUTTON_QSS` (the inline `padding: 6px 16px` style is gone).
- Help: new "Importing Parts" page (Start, Items, Target library, Fields, Conflicts, Install and result, Library tables) after Generating Tables in the TOC; Status bullet lists Collision; the warning span uses `AMBER` and the word "amber" (the `#CC7700` is gone); shortcut table lists Ctrl+I and Ctrl+Shift+R.

## Task Commits

1. **Task 1 RED:** `f6a5a6d` (test) - 8 failing tests for drop, toolbar button, busy state, primary style
2. **Task 1 GREEN:** `c03a931` (feat) - drop handlers, Import button, extended busy controls, shared primary style
3. **Task 2 RED:** `4464071` (test) - 4 failing help tests (KeyError 'importing', missing Ctrl+I, etc.)
4. **Task 2 GREEN:** `ca0d3d6` (feat) - help pages, TOC entry, shortcuts, AMBER span

**Plan metadata:** committed with this SUMMARY (docs: complete plan)

## Files Created/Modified
- `kicad_lib_manager/main_window.py` - drop and drag handlers, `_import_busy`, `_refuse_busy_drag`, `_import_btn`, extended `_set_scan_running`, `PRIMARY_BUTTON_QSS`
- `kicad_lib_manager/widgets/help_dialog.py` - `HELP_PAGES["importing"]`, TOC entry, Collision, AMBER, shortcuts
- `tests/test_main_window_import.py` - 8 new tests plus `_mime`, `_drop_event`, `_enter_event` helpers and an `opened` fixture
- `tests/test_help_dialog.py` - new, 4 tests

## Decisions Made
- One shared helper for the busy refusal, so the enter and drop checks cannot diverge.
- RESEARCH assumption A2 is confirmed: `QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)` works as written in PySide6 6.12, and `w.dropEvent(event)` can be called directly. `QDragEnterEvent(QPoint(10, 10), CopyAction, mime, LeftButton, NoModifier)` also works but PySide6 prints a DeprecationWarning for the `QPoint` constructor (4 warnings in the suite, harmless). Tests call `event.setAccepted(False)` before the handler because a fresh event starts accepted, and keep the `QMimeData` alive in a local because the event does not own it.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Full suite on the worktree: 1392 passed, 78 skipped, 4 failed. The 4 failures are the known baseline KiCad 10 symbol-format failures (`test_install_plan.py::test_version_real_cli_into_20241209`, `::test_library_real_cli_new_header`, `::test_noop_second_plan_after_normalised_apply`, `tests/test_kicad_cli.py::test_real_cli_upgrades_ul_symbol_deterministically`); they are unrelated to this plan. The `test_install_e2e.py` baseline cases did not fail here (skipped without the Custom submodule).
- Skips (78) are the submodule-dependent tests (Custom and WurthElektronik not checked out in a worktree) plus one symlink-privilege skip. All tests added by this plan build their own synthetic layout and run in a worktree.
- The test `make_window` fixture patches `main_window.scan_all`, so the drop tests ran against a real `MainWindow` offscreen; `_open_import` was monkeypatched to record the path in the drop tests (as the plan specified).

## Known Stubs

None. The "Importing Parts" help sections for Conflicts, Install and result and Library tables describe widgets built in plans 05-10 and 05-11 from the CONTEXT/UI-SPEC decisions; plan 05-11 Task 3 re-verifies them (planned, not a stub).

## Threat Flags

None. T-05-24 and T-05-25 are mitigated as planned (single local zip/folder only; busy re-check on drop; tests above).

## Next Phase Readiness
- Plan 05-11 Task 3 should compare the "Importing Parts" page with the finished ConflictRow and ImportResultView.
- Not touched: `widgets/import_dialog.py`, `importer/form.py` (plan 05-07).

## Self-Check: PASSED

- Files exist: main_window.py, help_dialog.py, tests/test_main_window_import.py, tests/test_help_dialog.py
- Commits exist: f6a5a6d, c03a931, 4464071, ca0d3d6
- Acceptance greps: no `padding: 6px 16px` and no `CC7700` outside comments; all required strings present
- `pytest tests/test_main_window.py tests/test_main_window_import.py tests/test_help_dialog.py`: all pass

---
*Phase: 05-import-ui-and-post-install*
*Completed: 2026-10-22*
