---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 17
subsystem: ui
tags: [scan, skip, progress-dialog, saved-scan, help, G-12-21]
requires:
  - phase: 12-16
    provides: "scan_all(skip=, checking=), ScanResult.skipped_sources, models_skipped_issue, saved-scan format 2 and the reuse note"
provides:
  - "ScanProgressDialog: Loading Libraries window with a Skip button that names the source"
  - "ScanWorker.request_skip (lock-guarded) and the checking signal"
  - "Skip-aware no-warnings line"
  - "Help Repository Scan and CLAUDE.md text on Skip and the saved scan"
affects: [12-18, 12-19, 12-20]
tech-stack:
  added: []
  patterns: ["own QDialog where Qt's progress dialog hides on button click", "the log line comes from the scan result, never from the click"]
key-files:
  created: [kicad_lib_manager/widgets/scan_progress.py]
  modified:
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/widgets/help_dialog.py
    - CLAUDE.md
    - tests/test_main_window.py
    - tests/test_main_window_import.py
    - tests/test_help_dialog.py
key-decisions:
  - "The Skip click writes no log line; the one skip line is the scan result's own issue, so the log, the button and the result agree"
  - "ScanProgressDialog replaces QProgressDialog: reject() is inert until finish(), so Escape and the title-bar X do nothing"
  - "After a click the button reads 'Skipping <source>...' only until the scan's next report replaces it"
requirements-completed: [UI-01]
status: complete
duration: 30 min
completed: 2026-11-04
commits: 5
plan_head_before: 2713fd3cc8e2e14220864371ddcffef20ce0046f
plan_head_after: 22a6113abbd7311548a73fcd25ad95ef85298543
actuals:
  tokens: 22000
  tasks: 3
  commits: 5
coverage:
  - id: D1
    description: "Loading Libraries window has a Skip button naming the source being checked, enabled only during that check"
    requirement: UI-01
    verification:
      - {kind: unit, ref: "tests/test_main_window.py#test_scan_progress_dialog_skip_button_follows_the_source", status: pass}
      - {kind: integration, ref: "tests/test_main_window.py#test_loading_dialog_skips_the_source_being_checked", status: pass}
    human_judgment: false
  - id: D2
    description: "A click after the source's check ended logs no skip and the button never keeps claiming one"
    requirement: UI-01
    verification:
      - {kind: integration, ref: "tests/test_main_window.py#test_a_skip_click_after_the_check_ended_logs_no_skip", status: pass}
    human_judgment: false
  - id: D3
    description: "Escape and the title-bar X do nothing on the Loading Libraries window"
    requirement: UI-01
    verification:
      - {kind: unit, ref: "tests/test_main_window.py#test_scan_progress_dialog_ignores_escape_and_close", status: pass}
    human_judgment: false
  - id: D4
    description: "Generate Tables after a skipped scan removes no WurthElektronik entry"
    requirement: UI-01
    verification:
      - {kind: integration, ref: "tests/test_main_window.py#test_generate_after_a_skip_removes_no_entry", status: pass}
    human_judgment: false
  - id: D5
    description: "A skipped scan is saved and the next start says so; a full Rescan clears the note"
    requirement: UI-01
    verification:
      - {kind: integration, ref: "tests/test_main_window.py#test_skipped_scan_is_saved_and_the_next_start_says_so", status: pass}
    human_judgment: false
  - id: D6
    description: "Help Repository Scan and CLAUDE.md explain Skip and the saved scan in plain words"
    requirement: UI-01
    verification:
      - {kind: unit, ref: "tests/test_help_dialog.py#test_help_repo_scan_explains_skip_and_the_saved_scan", status: pass}
    human_judgment: false
  - id: D7
    description: "The window looks right at 100% and 200% display scale: bar rises once, button text sharp and not cut off"
    verification: []
    human_judgment: true
    rationale: "Visual layout and DPI rendering of a real window; the plan's human-check covers it and no automated test asserts it"
---

# Phase 12 Plan 17: Skip button on the Loading Libraries window Summary

The Loading Libraries window is now a `ScanProgressDialog` with a Skip button that reads "Skip WurthElektronik" while that source's 3D model paths are checked, asks the running `ScanWorker` through a lock-guarded request to stop that check, and leaves the log line to the scan result so the log, the button and the saved scan agree.

## Performance

- **Duration:** about 30 min
- **Completed:** 2026-11-04
- **Tasks:** 3
- **Files modified:** 7 (1 created)

## Accomplishments

- New `kicad_lib_manager/widgets/scan_progress.py`: label, 0-100 bar, `skip_button`, `skip_requested` signal, `set_progress`, `set_skippable`, `finish`. `reject()` is inert until `finish()`, so Escape and the title-bar X do nothing. It imports only PySide6 and the theme.
- `ScanWorker` gained `checking = Signal(object)`, `request_skip(source)` and a private `_skip_requested(source)` behind a `threading.Lock`, and passes `skip=` and `checking=` to `scan_all`. `MainWindow` connects the dialog's `skip_requested` to `_on_skip_requested`, which forwards to the worker and writes no log line, and `checking` to `_on_scan_checking`.
- After a skip the end-of-scan line is "No warnings in the checks that ran."; "No warnings." is logged only when `skipped_sources` is empty. The rule applies to a reused saved scan too.
- Qt's progress dialog class is named nowhere in `main_window.py` any more (code, annotation or docstring).
- Both `make_window` fixtures accept `*, skip=None, checking=None` and store them as `make.hooks`.
- Help "Repository Scan" (no new heading, outline still 20 sections) and CLAUDE.md "GUI Behavior" explain the saved scan and Skip.

## Task Commits

| Task | Phase | Commit |
| ---- | ----- | ------ |
| 1 (tracer) | RED | 3602a4f test(12-17): failing tests for the Skip button on the Loading Libraries window |
| 1 (tracer) | GREEN | 5428cac feat(12-17): Skip button on the Loading Libraries window |
| 2 | tests only | d15ed3e test(12-17): a skip removes no table entry and the saved skipped scan says so |
| 3 | RED | 6e752e4 test(12-17): failing test for the Repository Scan Help page on Skip and the saved scan |
| 3 | GREEN | 22a6113 feat(12-17): Help and CLAUDE.md explain Skip and the saved scan |

## TDD Gate Compliance

- Task 1: RED commit precedes GREEN. RED evidence (semantic assessment; I did not run `gsd_run check tdd-red-evidence`, since pytest plain output is not a supported report format): the four new tests failed on `ModuleNotFoundError: kicad_lib_manager.widgets.scan_progress` and, for the two window tests, `AttributeError: 'QProgressDialog' object has no attribute 'skip_button'`, which is the planned missing behavior. After GREEN, one test still failed on my own test slip (`Issue` has `.text`, not `.message`); corrected in the same GREEN commit.
- Task 2: no GREEN commit needed. Both tests passed at once, as the plan allows, because Task 1 and plan 12-16 already provide the behaviour (the skip-aware no-warnings rule covers a reused result). Committed as `test(...)`.
- Task 3: RED failed on the planned assertion (`saved scan` missing from the page), then GREEN. No REFACTOR commit.

## Verification

- Task 1 selection: 60 passed (both main-window files).
- Task 2 selection: 19 passed.
- Plan-level run (`tests/test_main_window.py tests/test_main_window_import.py tests/test_help_dialog.py tests/test_plain_names.py tests/test_scan_skip.py tests/test_scan_cache.py tests/test_layering.py tests/test_importer_layering.py -m "not wurth"`): 250 passed in 40 s, run in the foreground.
- Acceptance greps: `class ScanProgressDialog` and `def request_skip` each found once; zero non-comment `QProgressDialog` lines in `main_window.py`; no `main_window` in `scan_progress.py`; `Loading Libraries` found in CLAUDE.md.
- The full suite was not run (orchestrator's post-merge gate). The `<human-check>` of Task 3 (real window at 100% and 200% display scale, startup Skip, next-start note, Rescan) was not run: this is a headless executor. It is the open item for UAT.

## Deviations from Plan

None - plan executed exactly as written. The edit scripts initially normalised line endings of CRLF files; I restored CRLF so each commit diff holds only the intended lines.

## Issues Encountered

- In the saved-scan test the first scan's library files must exist before the window starts (the saved scan's fingerprint is taken before the scan reads), so the skipped result is built eagerly rather than lazily inside the fake scan. Test-only.

## Known Stubs

None.

## Threat Flags

None. T-12-43 (lock-guarded request, queued signal), T-12-44 (real `scan_all` with a skip, Generate keeps both Würth entries) and T-12-45 (skip-aware line, no log line from the click) are covered by the tests named in the plan.

## Next Phase Readiness

The human-check in Task 3 (visual: bar rises once, button text at 100% and 200% scale, Escape inert) remains for UAT.

## Self-Check: PASSED

Files exist: kicad_lib_manager/widgets/scan_progress.py, main_window.py, help_dialog.py, tests/test_main_window.py, tests/test_help_dialog.py. Commits 3602a4f, 5428cac, d15ed3e, 6e752e4, 22a6113 are on the branch.
