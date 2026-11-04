---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 18
subsystem: ui
tags: [user-guide, help, non-modal, parentless-window, import-window, G-12-22]
requires:
  - phase: 12-15
    provides: "import window start page with Cancel; HelpDialog fit_window"
  - phase: 12-17
    provides: "ScanProgressDialog and the main-window scan hooks"
provides:
  - "MainWindow.show_guide(topic=None) and _guide_window(): one shared, parentless, non-modal User Guide"
  - "ImportDialog(show_guide=...) hook; parentless fallback guide that outlives the import window"
  - "centre_window(window, over) in widgets/import_dialog.py"
  - "tests helpers click_guide_row, guide_key, click_in_window, guide_windows (plan 12-20 reuses them)"
affects: [12-19, 12-20]
tech-stack:
  added: []
  patterns:
    - "A parentless QDialog escapes every window-modal dialog; the owner (main window) keeps one reference and closes it with itself"
    - "A widget receives a callable from the main window instead of importing it"
key-files:
  created: []
  modified:
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_main_window.py
    - tests/test_main_window_import.py
    - tests/test_import_dialog.py
key-decisions:
  - "Guide placement is done by a new centre_window helper in import_dialog.py (beside fit_window) and applied twice: before the first show and again after it, because fit_window's showEvent pass assumes a 16x40 frame and shifts the window up and left when the real frame is smaller"
  - "The helper lives in import_dialog.py, not main_window.py, so the test suite's autouse screen_area patch applies to it"
  - "Help tests in tests/test_main_window_import.py import their helpers from tests/test_main_window.py instead of copying them"
requirements-completed: [UI-01]
duration: 20 min
completed: 2026-11-04
status: complete
commits: 4
plan_head_before: d1e46bd873c87cf7aa79c8b418d1710ad199ec9d
plan_head_after: b6267952ec826cc57574566d0104b81d9cbb737a
actuals:
  tokens: 14000
  tasks: 2
  commits: 4
coverage:
  - id: D1
    description: "Help > User Guide and F1 in the main window show one shared parentless non-modal guide, reused on every later click or F1"
    requirement: UI-01
    verification:
      - {kind: unit, ref: "tests/test_main_window.py#test_main_window_help_opens_one_shared_non_modal_guide", status: pass}
    human_judgment: false
  - id: D2
    description: "The main window and the open guide both take window-system clicks"
    requirement: UI-01
    verification:
      - {kind: integration, ref: "tests/test_main_window.py#test_main_window_and_guide_both_take_clicks", status: pass}
    human_judgment: false
  - id: D3
    description: "Closing the main window closes the guide; a refused close leaves it open"
    requirement: UI-01
    verification:
      - {kind: unit, ref: "tests/test_main_window.py#test_closing_the_main_window_closes_the_guide", status: pass}
      - {kind: unit, ref: "tests/test_main_window.py#test_a_refused_close_keeps_the_guide", status: pass}
    human_judgment: false
  - id: D4
    description: "The guide first shows centred over the main window and inside the screen's free area"
    requirement: UI-01
    verification:
      - {kind: unit, ref: "tests/test_main_window.py#test_guide_first_shows_over_the_main_window", status: pass}
    human_judgment: false
  - id: D5
    description: "The import window's Help and F1 show the same shared guide on Importing Parts and create no guide of their own"
    requirement: UI-01
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_import_window_with_a_guide_hook_creates_no_guide", status: pass}
      - {kind: integration, ref: "tests/test_main_window_import.py#test_import_help_uses_the_shared_guide", status: pass}
    human_judgment: false
  - id: D6
    description: "The guide takes clicks beside the import window, a content view and Check Atomic Parts while the main window stays locked; it stays open after the import window closes"
    requirement: UI-01
    verification:
      - {kind: integration, ref: "tests/test_main_window_import.py#test_guide_takes_clicks_beside_the_import_window_and_its_dialogs", status: pass}
      - {kind: integration, ref: "tests/test_main_window_import.py#test_guide_stays_open_after_the_import_window_closes", status: pass}
    human_judgment: false
  - id: D7
    description: "The import window on its own opens a parentless guide that outlives it (existing Help tests updated)"
    requirement: UI-01
    verification:
      - {kind: integration, ref: "tests/test_import_dialog.py#test_toolbar_help_opens_importing_page", status: pass}
      - {kind: integration, ref: "tests/test_import_dialog.py#test_help_works_while_finishing_and_outlives_the_dialog", status: pass}
    human_judgment: false
  - id: D8
    description: "The guide looks and behaves right beside the real windows on a real desktop (stacking order, focus, placement on multiple monitors)"
    verification: []
    human_judgment: true
    rationale: "Offscreen Qt has no real window manager; stacking, focus hand-over and monitor placement are only seen on the owner's desktop (UAT test 22)"
---

# Phase 12 Plan 18: One shared, free-floating User Guide Summary

The User Guide is now one parentless, non-modal window owned by the main window: Help and F1 in the main window and in the import window show and raise the same object, it takes clicks beside the import window and its content view and Check Atomic Parts dialogs, it outlives the import window, and it closes with the main window.

Start commit: d1e46bd873c87cf7aa79c8b418d1710ad199ec9d

## Performance

- **Duration:** about 20 min
- **Started:** 2026-11-04T17:12:36Z
- **Completed:** 2026-11-04T17:31Z
- **Tasks:** 2
- **Files modified:** 5 (none created)

## Accomplishments

- `MainWindow._guide`, `_guide_window()` and `show_guide(topic=None)`: the guide is built once with no parent, shown, raised and activated on every call; `_on_help` calls `show_guide()` and never runs a blocking exec again.
- `closeEvent` closes the guide after every refusal branch and before saving geometry, so a refused close (install, commit, KiCad check, import window finishing) leaves it open.
- `ImportDialog(show_guide=...)`: with the hook, Help and F1 call `self._show_guide("importing")` and nothing else; without it, a parentless fallback guide is kept in `_help_dialog` and `_shutdown` no longer closes it. `MainWindow._open_import` passes `show_guide=self.show_guide`; no widget imports `main_window`.
- The import window stays window-modal over the main window (owner decision): `test_guide_takes_clicks_beside_the_import_window_and_its_dialogs` shows a main-window click is dropped while a guide-row click lands.
- `centre_window(window, over)` places the guide centred over the main window before the first show and again after it, kept inside the free area.

## Task Commits

| Task | Phase | Commit |
| ---- | ----- | ------ |
| 1 (tracer) | RED | 3363445 test(12-18): failing tests for one shared non-modal User Guide on the main window |
| 1 (tracer) | GREEN | 5d40259 feat(12-18): one shared, parentless, non-modal User Guide on the main window |
| 2 | RED | 8bd0cdb test(12-18): failing tests for the shared guide beside the import window |
| 2 | GREEN | b626795 feat(12-18): the import window shows the shared User Guide, which outlives it |

**Plan metadata:** the docs commit that adds this SUMMARY.

## Files Created/Modified

- `kicad_lib_manager/main_window.py` - shared guide (`_guide`, `_guide_window`, `show_guide`), `_on_help`, `closeEvent`, `show_guide` passed to the import window.
- `kicad_lib_manager/widgets/import_dialog.py` - `show_guide` keyword, `_on_help` through the hook or a parentless fallback, `_shutdown` leaves the guide open, `centre_window`.
- `tests/test_main_window.py` - five guide tests, the autouse guide cleanup fixture and the helpers `click_guide_row`, `guide_key`, `click_in_window`, `guide_windows`, `help_menu_action`.
- `tests/test_main_window_import.py` - the three import-window guide tests (helpers imported from `test_main_window`).
- `tests/test_import_dialog.py` - hook test, autouse guide cleanup fixture, and the standalone Help tests now expect a parentless guide that survives the import window.

## Decisions Made

- `centre_window` lives next to `fit_window` in `import_dialog.py`: the suite's autouse `screen_area` patch only reaches that module, and `fit_window` is already documented there as shared with the guide.
- The guide is centred twice. `fit_window` (run from `HelpDialog.showEvent`) pads the frame to at least 16x40 before the OS frame is known, so it nudges a first-shown window up and left by the padding difference (about 6 and 18 px offscreen, near zero on Windows where the real frame is about that size). The second pass after `show()` uses the real frame, so the centre is exact within a pixel.
- `fit_window` itself is left as is (out of scope; it is the shared 12-14 helper and its tests pass).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Guide missed the main-window centre by 4-6 px / 16 px**
- **Found during:** Task 1 (`test_guide_first_shows_over_the_main_window`)
- **Issue:** Placing the frame before the first show and trusting `showEvent`'s `fit_window` left the guide off-centre, because `fit_window` assumes a 16x40 frame and re-centres on that padded size.
- **Fix:** New `centre_window` helper, applied before and after the first `show()`.
- **Files modified:** kicad_lib_manager/main_window.py, kicad_lib_manager/widgets/import_dialog.py
- **Verification:** the placement test passes; `tests/test_import_dialog.py` guide-fit tests (`test_help_window_fits_the_screen`) still pass
- **Committed in:** 5d40259

**2. [Rule 3 - Blocking] Screen area helper must be called inside import_dialog**
- **Found during:** Task 1
- **Issue:** a `screen_area` imported into `main_window` was not patched by the suite's autouse 1920x1032 fixture and read the 800x800 offscreen screen.
- **Fix:** the clamp lives in `centre_window` in `import_dialog.py` (same cause as above, same commit).
- **Committed in:** 5d40259

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** The plan's "moved before first show, fit_window keeps it inside" is realised with one extra post-show centring call; behaviour matches the must-haves.

## Owner-approved exclusion

The system file pickers (Browse zip..., Browse folder..., Add 3D model..., Browse... for the destination, Set KiCad Footprint Path, the backup folder and the model picker of Check Atomic Parts) are left exactly as they were. Qt's static file pickers are application-modal, so they block the User Guide while one is open. This is an owner decision, not a planner choice: 12-UAT.md Owner Decisions, "G-12-22 (approved exclusion, asked after plan check)", commit d2c45a7, where the owner chose "No, pickers may block" over converting them to Qt window-modal pickers. No picker is converted in this plan or in plan 12-20. Check: `git diff d1e46bd873c87cf7aa79c8b418d1710ad199ec9d -- kicad_lib_manager` contains no added or removed line mentioning `QFileDialog` (count 0).

## TDD Gate Compliance

- Task 1: RED commit 3363445 precedes GREEN 5d40259. RED evidence (semantic assessment; `gsd_run check tdd-red-evidence` not run, since plain pytest output is not a supported report format): with a helper plugin that turns the old blocking `HelpDialog.exec()` into an assertion error (the unpatched run hung in the modal exec, which is the planned missing behavior), all five tests failed on `AttributeError: 'MainWindow' object has no attribute '_guide'`.
- Task 2: RED commit 8bd0cdb precedes GREEN b626795. RED: the hook test failed with `TypeError: ImportDialog.__init__() got an unexpected keyword argument 'show_guide'`; the six updated standalone Help tests failed on `assert help_window.isVisible()` (the old code closed the guide with the import window); the three main-window tests failed with `w._guide is None` because the import window built its own guide.

## Verification

- Task 1: `pytest tests/test_main_window.py -q -k "guide or close"` - 10 passed.
- Task 2 selection: `pytest tests/test_import_dialog.py tests/test_main_window_import.py -k "help or guide or f1 or toolbar or window_modal" -m "not wurth"` - 17 passed.
- Plan-level: `pytest tests/test_main_window.py tests/test_main_window_import.py tests/test_import_dialog.py tests/test_plain_names.py tests/test_importer_layering.py -q -m "not wurth"` - 395 passed in 190 s (3:10), run in the background because the foreground wait exceeded the tool limit.
- Acceptance greps: `show_guide=self.show_guide` found once, `self._show_guide(_HELP_TOPIC)` found once, `HelpDialog(parent=self)` and `HelpDialog(topic=_HELP_TOPIC, parent=self)` count 0, no `main_window` mention in `import_dialog.py`, no picker line in the diff.

## Issues Encountered

- The unpatched RED run of Task 1 hung in the old modal exec; I stopped that one test process by its PID and used a small plugin (scratchpad) for the RED evidence.
- No known stubs. No new network, auth or file-access surface (threat flags: none).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 12-19 can add the remembered place to `show_guide`'s no-topic path. Plan 12-20 makes the main window's own dialogs window-modal, proves the guide beside the Loading Libraries window and updates the Help text; it can import `click_guide_row`, `guide_key` and `_close_guides` from `tests/test_main_window.py`.

---
*Phase: 12-import-flow-fixes-and-case-sensitive-re-test*
*Completed: 2026-11-04*

## Self-Check: PASSED

- Modified files exist; commits 3363445, 5d40259, 8bd0cdb and b626795 are ancestors of HEAD.
