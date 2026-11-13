---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 20
subsystem: ui
tags: [user-guide, help, window-modal, qmessagebox, main-window, G-12-22]
requires:
  - phase: 12-18
    provides: "one shared, parentless, non-modal User Guide and the click helpers in tests/test_main_window.py"
  - phase: 12-19
    provides: "the guide remembers its place"
provides:
  - "MainWindow._question: a window-modal Yes/No question"
  - "Window-modal KiCad-open box, Restore Backup dialog and About box"
  - "Help text: the User Guide is its own window beside the other windows"
affects: []
tech-stack:
  added: []
  patterns:
    - "A main-window dialog is WindowModal and keeps its blocking exec(); a parentless window stays usable beside it"
key-files:
  created: []
  modified:
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_main_window.py
    - tests/test_main_window_import.py
    - tests/test_help_dialog.py
key-decisions:
  - "QMessageBox is application-modal by default (its constructor sets it), so each of the four dialogs sets WindowModal explicitly before exec()"
  - "_question returns the standard button of the clicked button, and the default when none was clicked (Escape)"
  - "Both test fixtures patch MainWindow._question with fake_question(window, *args), so the existing tests reading make_window.questions pass unchanged"
requirements-completed: [UI-01]
duration: 25 min
completed: 2026-11-04
status: complete
commits: 4
plan_head_before: 31990679ee7fedd06386e35a3c28568b8105ba81
plan_head_after: 21730f9ff4571ca2f50ce2907eec35b5d54f2565
actuals:
  tokens: 5000
  tasks: 2
  commits: 4
coverage:
  - id: D1
    description: "The path-variable question, KiCad-open box, Restore Backup and About block only the main window; the User Guide still changes page while each is open"
    requirement: UI-01
    verification:
      - {kind: integration, ref: "tests/test_main_window.py#test_main_window_dialogs_are_window_modal_and_leave_the_guide_usable", status: pass}
      - {kind: unit, ref: "tests/test_main_window.py#test_kicad_open_box_texts_and_buttons", status: pass}
    human_judgment: false
  - id: D2
    description: "The guide takes clicks while the Loading Libraries window is open"
    requirement: UI-01
    verification:
      - {kind: integration, ref: "tests/test_main_window.py#test_guide_takes_clicks_while_the_libraries_load", status: pass}
    human_judgment: false
  - id: D3
    description: "Every question keeps its title, text, buttons and default; callers' flows are unchanged"
    requirement: UI-01
    verification:
      - {kind: integration, ref: "tests/test_main_window.py#test_generate_confirmed_shows_old_and_new_values", status: pass}
      - {kind: integration, ref: "tests/test_main_window.py#test_path_var_question_names_the_settings_file", status: pass}
    human_judgment: false
  - id: D4
    description: "Help (Importing Parts > Start and the F1 row) says the User Guide is its own window beside the main window and the import window, also when the import window closes"
    requirement: UI-01
    verification:
      - {kind: unit, ref: "tests/test_help_dialog.py#test_help_names_the_toolbar_help", status: pass}
    human_judgment: false
  - id: D5
    description: "On a real desktop the guide stays usable beside About, the import window, a content view and the Loading Libraries window, at 100% and 200% display scale"
    verification: []
    human_judgment: true
    rationale: "Offscreen Qt has no real window manager or display scaling; the plan's human-check covers it (UAT test 22)"
---

# Phase 12 Plan 20: The main window's dialogs no longer block the User Guide Summary

The path-variable question (new `MainWindow._question`), the KiCad-open box, Restore Backup and About are now window-modal to the main window, so the shared User Guide still scrolls and changes page while any of them is open, and Help says in plain words that the guide is its own window beside the others.

Start commit: 31990679ee7fedd06386e35a3c28568b8105ba81

## Performance

- **Duration:** about 25 min
- **Started:** 2026-11-04T18:00Z
- **Completed:** 2026-11-04T18:25Z
- **Tasks:** 2
- **Files modified:** 5 (none created)

## Accomplishments

- `MainWindow._question(title, text, buttons, default)` builds a `QMessageBox` with the Question icon and the main window as parent, sets the default button and `WindowModal`, runs a blocking `exec()` and returns the clicked standard button (the default when none was clicked). `_confirm_path_var_changes` calls it with the same title, text, buttons and default as before; the static `QMessageBox.question` call is gone.
- `_kicad_open_box`, `_on_restore_backup` (the `BackupDialog`) and `_on_about` set `WindowModal` and keep their blocking `exec()`, so no caller's flow or answer handling changed.
- `test_main_window_dialogs_are_window_modal_and_leave_the_guide_usable` (four cases) opens each dialog with a timer probe that finds `QApplication.activeModalWidget()`, checks it is `WindowModal` with the main window as parent, clicks a guide row through the window system and sees the guide change page, then closes the dialog.
- `test_guide_takes_clicks_while_the_libraries_load` pins that the already window-modal Loading Libraries window (plan 12-17) does not block the guide.
- Help: the Importing Parts Start paragraph and the F1 row of Keyboard Shortcuts say the User Guide is its own window, stays open beside the main window and the import window, and stays open when the import window closes. No heading was added.

## Task Commits

1. **Task 1 (tracer):** RED `629805d` test(12-20), GREEN `d123d07` feat(12-20)
2. **Task 2:** RED `7cfa6f1` test(12-20), GREEN `21730f9` feat(12-20)

**Plan metadata:** the docs commit that adds this SUMMARY.

## Files Created/Modified

- `kicad_lib_manager/main_window.py` - `_question`, window-modal KiCad-open box, Restore Backup and About.
- `kicad_lib_manager/widgets/help_dialog.py` - the two Help paragraphs.
- `tests/test_main_window.py` - fixture patches `MainWindow._question`; modality test (4 cases), Loading Libraries test, modality line in the KiCad-open box test.
- `tests/test_main_window_import.py` - fixture patches `MainWindow._question`.
- `tests/test_help_dialog.py` - `test_help_names_the_toolbar_help` extended.

## Decisions Made

- Each dialog sets `WindowModal` explicitly: the probe showed `QMessageBox` reports `ApplicationModal` by default, and a plain `exec()` keeps that.
- The `_question` fixture records `(window, *args)`, so `args[0]` is the window, `args[2]` the text and `args[4]` the default, exactly as the existing tests read them.

## Deviations from Plan

None - plan executed exactly as written.

## Owner-approved exclusion

The system file pickers (Browse zip..., Browse folder..., Add 3D model..., Browse... for the destination, Set KiCad Footprint Path, the backup folder and the model picker of Check Atomic Parts) are left application-modal and block the User Guide while one is open. This is an owner decision, not a planner choice: 12-UAT.md Owner Decisions, "G-12-22 (approved exclusion, asked after plan check)", commit d2c45a7, where the owner chose "No, pickers may block" over converting them to Qt window-modal pickers. No picker is converted. Check: `git diff 31990679ee7fedd06386e35a3c28568b8105ba81 -- kicad_lib_manager` contains no added or removed line mentioning `QFileDialog` (count 0).

## TDD Gate Compliance

- Task 1: RED `629805d` precedes GREEN `d123d07`. RED evidence (semantic assessment; `gsd_run check tdd-red-evidence` not run, since plain pytest output is not a supported report format): `test_kicad_open_box_texts_and_buttons` and the "kicad open", "restore backup" and "about" cases failed on `assert ApplicationModal == WindowModal`, the planned missing behavior; the "path question" case failed on `MainWindow._question is missing`. `test_guide_takes_clicks_while_the_libraries_load` passed already in RED, by design: the Loading Libraries window has been window-modal since plan 12-17, so it is a regression pin.
- Task 2: RED `7cfa6f1` precedes GREEN `21730f9`. RED: `test_help_names_the_toolbar_help` failed on `assert 'its own window' in <Start section text>`.

## Verification

- Task 1: `pytest tests/test_main_window.py tests/test_main_window_import.py -q -m "not wurth"` - 134 passed in 12 s.
- Plan-level: `pytest tests/test_main_window.py tests/test_main_window_import.py tests/test_import_dialog.py tests/test_help_dialog.py tests/test_plain_names.py tests/test_importer_layering.py -q -m "not wurth"` - 452 passed in 168 s (2:48), run in the background.
- Acceptance greps: one `def _question`; 4 `WindowModality.WindowModal` lines in main_window.py; 0 non-comment `QMessageBox.question(` lines; 2 `its own window` lines in help_dialog.py; 0 `QFileDialog` lines in the diff against the start commit.
- Step 0c note: the plan's `<automated>` commands name the absolute interpreter `C:/Git_Repo_Clones/Kicad_Libraries-importer/env/Scripts/python.exe` (the worktree has no venv; the orchestrator's instructions require it). It is run from the worktree root and relocates nothing, and `pythonpath = ["."]` makes the tests import the worktree's code.
- The plan's human-check (F1, About, import window, Rescan, 100% and 200% scale) is not run here; it belongs to UAT test 22.

## Issues Encountered

None. No known stubs. No new network, auth or file-access surface (threat flags: none); T-12-48 accepted as planned: the questions stay blocking for the main window with the same defaults, and the guide holds only static help text.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

This is the last plan of 12-15 to 12-20. The phase-level full suite (`pytest -m "not wurth" -q`, 15-27 min) runs once after merge, as the plan's verification note says.

---
*Phase: 12-import-flow-fixes-and-case-sensitive-re-test*
*Completed: 2026-11-04*

## Self-Check: PASSED

- Modified files exist; commits 629805d, d123d07, 7cfa6f1 and 21730f9 are ancestors of HEAD.
