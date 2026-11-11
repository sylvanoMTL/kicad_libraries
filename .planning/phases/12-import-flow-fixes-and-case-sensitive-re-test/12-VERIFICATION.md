---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
verified: 2026-11-11T12:00:00Z
status: human_needed
score: 12/13 must-haves verified
covered_files:
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-01-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-01-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-02-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-02-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-03-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-03-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-04-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-04-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-05-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-05-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-06-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-06-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-07-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-07-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-08-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-08-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-09-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-09-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-10-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-10-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-11-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-11-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-12-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-12-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-13-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-13-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-14-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-14-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-15-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-15-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-16-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-16-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-17-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-17-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-18-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-18-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-19-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-19-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-20-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-20-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-21-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-21-SUMMARY.md
  - CLAUDE.md
  - kicad_lib_manager/importer/applier.py
  - kicad_lib_manager/importer/kicad_cli.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/preview.py
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/models.py
  - kicad_lib_manager/scan_cache.py
  - kicad_lib_manager/settings.py
  - kicad_lib_manager/table_generator.py
  - kicad_lib_manager/widgets/backup_dialog.py
  - kicad_lib_manager/widgets/conflict_row.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - kicad_lib_manager/widgets/scan_progress.py
  - kicad_lib_manager/widgets/theme.py
  - tests/casefixtures.py
  - tests/conftest.py
  - tests/test_case_sensitive_install.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_main_window.py
  - tests/test_main_window_import.py
  - tests/test_scan_cache.py
  - tests/test_scan_skip.py
covered_digest: "v3:sha256:8a58e57d6cfdb44e4c709a55349f5944b279ba33373d42a7edbd4d6f4f80618d"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 12/12
  gaps_closed: []
  gaps_remaining:
    - "G-12-27 (UAT test 27) stays failed in 12-UAT.md until the owner's re-check; code and tests for it are present and green, but the owner's step-1 report (Close, then F1) was never reproduced"
  regressions: []
advisory:
  - finding: "WR-09 (12-REVIEW.md, open): shows_asked_topic() is a flag, not a comparison with the saved place. If the topic a caller asked for equals the owner's saved place (import window Help opens 'importing' while 'importing' is saved), main-window F1 on the visible guide runs show_remembered() and scrolls a page entry to its top, contradicting the 'only brought to the front' wording in CLAUDE.md, the Help F1 row and the show_guide docstring"
    category: other
    reason: "Read in the code (main_window.py:1368, help_dialog.py:699-742); not covered by any test and not run here. It is an edge of the 12-21 'owner's own place is only raised' truth, not the UAT 27 scenario. Resolve with the review's place comparison plus a test, or accept"
    evidence_status: "code reading only (no failing test)"
  - finding: "WR-10 (12-REVIEW.md, open): clicking the already-current asked row neither saves nor clears the asked-topic flag, so the next main-window F1 moves the owner to the previously saved place"
    category: other
    reason: "Predates 12-21 for the missing save; the flag part is new. Same area as WR-09; fix in _on_item_clicked per the review"
    evidence_status: "code reading only (no failing test)"
  - finding: "WR-06: Help or F1 does not restore a minimized User Guide"
    category: other
    reason: "12-REVIEW.md, disposition open; reasoned from Qt behaviour, human item 4"
    evidence_status: "none provided (no failing test)"
  - finding: "WR-07: source folder name goes unescaped into the Skip button text and tooltip"
    category: other
    reason: "12-REVIEW.md, disposition open; only reachable with '&' or '<' in a source folder name"
    evidence_status: "none provided (no failing test)"
  - finding: "WR-08: late-Skip-click test uses a fake scan that ignores the skip hook"
    category: other
    reason: "12-REVIEW.md, disposition open; the invariant is enforced in library_scanner.py and the real scan_all is driven in other tests"
    evidence_status: "code reading supports the invariant; the named test is shallow"
human_verification:
  - test: "G-12-27 / UAT test 27 / plan 12-21 Task 3 human-check, real Windows desktop at 100% and again at 200% (steps 1 to 6, plus 5b and 5c): .\\env\\Scripts\\python.exe kicad_lib_manager.py. (1) F1, click 4.4 Importing Parts, then 4.4.7 Conflicts, scroll the page to its top, Close. (2) F1. (3) scroll to top, Escape, F1. (4) click 4.3 Generating Tables, press on 4.4 Importing Parts, hold about a second, release, then click 4.4.7 Conflicts. (5) Ctrl+I, Help in the import window, Cancel, close the guide, F1. (5b) Ctrl+I, Help again, Cancel, leave the guide open, F1. (5c) scroll the Conflicts page down a little, click the main window, F1 again. (6) close the app, start it, F1. At 200% repeat 1, 2 and 6"
    expected: "At steps 2, 3, 5, 5b and 6 the guide shows 4.4.7 Conflicts as the selected row (white text on a blue fill; a hovered row only gets a faint grey), Importing Parts opened out, other pages folded, the Conflicts heading at the top of the page. Step 4: 4.4 Importing Parts is the selected row, not one of its sections. Step 5 shows 4.4 Importing Parts from the import window's Help. Step 5c: the guide comes to the front and the page does not move. The small expand arrows and the indentation still show. Selected row and heading visible and not cut off at 200%"
    why_human: "The owner's complaint (page row 4.4 selected on reopen) was not reproduced for the step-1 order (Close, then F1) in 7 full-app runs; only the guide-left-open path (step 5b) has a RED-then-GREEN test. Offscreen Qt has no real mouse press timing, no windows11 style and no display scaling. Plan 12-21 makes this re-check the gate, so G-12-27 and test 27 must not be marked resolved from automated results. Blocking fallback: if the row 4.4 or the page top shows at a step that expects Conflicts, the gap stays failed; the owner runs .\\env\\Scripts\\python.exe .claude\\debug\\guide_trace.py (present, git-ignored) in place of kicad_lib_manager.py, repeats steps 1, 2 and 6 with a screenshot at each, and returns .claude\\debug\\guide_trace.log for a new debug round"
  - test: "G-12-12 / plan 12-15, real Windows display at 100% and 200%: Ctrl+I, look at the start page; open downloaded_examples\\ul_CSD85301Q2.zip and pick an Atomic_ library; 'Choose another package...'; Cancel. Note git -C Custom status --short first and compare after"
    expected: "Start window about 640 wide and only as tall as its content, Browse zip..., Browse folder... and Cancel in one row, no empty band, no size change when the Downloads line appears or a package is read; the window grows above the taskbar for the edit page and 'Choose another package...' returns it to compact; Custom status unchanged; text sharp at 200%"
    why_human: "Real DPI scaling, taskbar, fonts and first-show placement cannot be reproduced headless; the owner's 200% run of UAT 12 was still open"
  - test: "G-12-11 / plan 12-14 at 200% (UAT 13 200% look): F1, '4.4 Importing Parts', its Conflicts section, then Ctrl+I, Help and F1 in the import window"
    expected: "Guide fully on screen with Close visible; numbers match the menu; section click scrolls to the heading; text sharp"
    why_human: "Look and sharpness at 200%"
  - test: "G-12-21 / plans 12-16, 12-17, real startup with the real Wurth library: delete %APPDATA%/KiCadExtLibManager/scan_cache/ so the full scan runs; while 'Loading Libraries' shows 'Checking 3D paths' click 'Skip WurthElektronik'; close and restart; press Rescan"
    expected: "Button 'Skip WurthElektronik' then 'Skipping WurthElektronik...', window closes by itself, Escape and X do nothing while loading; one plain log line that the 3D paths were not checked and no 'No warnings.'; both trees list every Wurth library, Generate Tables removes no Wurth entry; next start shows the saved scan with the skip note; Rescan does the full check and the note disappears; startup noticeably faster"
    why_human: "Real 60+ s timing against 5645 Wurth footprints and a real loading window; tests use a synthetic Wurth repo and fake workers for the GUI clicks"
  - test: "G-12-22 / plans 12-18, 12-20, real display: F1, leave the guide open, click in the main window, Generate Tables, About, Restore Backup, Rescan, Ctrl+I and Help in the import window, content view, Check Atomic Parts; close the import window, then the main window. Also minimize the guide and press F1 again (WR-06)"
    expected: "The guide is its own window with its own taskbar button, scrolls and changes page while every one of those windows is open; a second F1 reuses it; the main window stays locked while the import window is open; system file pickers may block it (owner-approved exclusion); the guide stays open after the import window closes and closes with the main window; a minimized guide comes back on F1 (WR-06 predicts it does not)"
    why_human: "Window-system modality, focus and taskbar behaviour on real Windows; tests use offscreen QWindow clicks"
  - test: "UAT 10(a-e) toolbar Help in the real import window (carried; G-12-9 appearance)"
    expected: "Toolbar row with the help icon and 'Help' at the top of every page; Help or F1 opens the User Guide on Importing Parts; both windows take input; row not clipped. The guide stays open when the import window closes (owner decision G-12-22)"
    why_human: "Nobody has seen the toolbar drawn with real fonts"
  - test: "UAT 3 (blocked by the worktree guard): from the main checkout change CUSTOM_3DMODEL_DIR in KiCad, leave KiCad open, press Generate Tables"
    expected: "Dialog 'KiCad is open' with Retry (default), Change anyway, Not now; Retry after closing KiCad leads to the Yes/No question; Not now writes nothing; the dialog is window-modal so the guide stays usable"
    why_human: "Needs a live KiCad process and a modal dialog; tests replace kicad_running"
  - test: "UAT 4 (skipped by owner): Finishing strip during a real kicad-cli rebuild"
    expected: "Dialog greys out with 'Finishing the preview...', window stays live, slow note after 10 s, no hang"
    why_human: "Real timing; covered only by gated stand-in workers"
---

# Phase 12: Import Flow Fixes and Case-Sensitive Re-test Verification Report

**Phase Goal:** The import dialog, the post-install table step and the `kicad_common.json` write behave correctly in the cases the v1.0 reviews left open. The Help dialog follows the theme, and case-twin rollback is proven on a case-sensitive folder.
**Verified:** 2026-11-11
**Status:** human_needed
**Re-verification:** Yes, after gap-closure plan 12-21 (G-12-27, UAT test 27), merged at 90c2db9. The previous report (12-01..12-20, human_needed, 12/12) is replaced. Code from 12-01..12-20 was regression-checked only (targeted tests re-run, plus the orchestrator's full runs at HEAD); 12-21 was read in the code and its named tests collected and run here. No source file under `kicad_lib_manager/` or `tests/` differs from the merge commit (`git status` shows only `.planning/state.json`, the `Custom` submodule pointer, `milestone.lock` and `uv.lock`).

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | "Already listed" only when the managed entry points at that library; empty Destination writes no table, never in the working directory | VERIFIED | Unchanged since the previous report; `table_generator.py` and the post-install path are not touched by 12-21 (diff of 12-21 is `help_dialog.py`, one condition in `main_window.py`, two test files, CLAUDE.md). Covered by tests/test_main_window_import.py in the orchestrator's green full run (3366 passed, 0 failed at HEAD) |
| 2 | One-off conflict build never runs during Install; window responsive while kicad-cli works | VERIFIED (live timing is human item 8) | Untouched by 12-21; same full-suite evidence |
| 3 | KiCad-running confirm says so before writing; confirmed write starts from current content | VERIFIED (real dialog is human item 7) | Untouched by 12-21; same full-suite evidence |
| 4 | Help dialog and conflict rows use theme tokens only | VERIFIED | `help_dialog.py` carries only the token-built page CSS (lines 26-40 interpolate `LINK`, `ACCENT`, `SP_*`, `BORDER` etc.); the new `_MenuSelectionDelegate` uses `QColor(ACCENT)` and `QColor(SURFACE_BASE)` only; grep for a `#RRGGBB` literal in `help_dialog.py` finds none; `test_help_css_uses_theme_tokens_only` passes (99 passed run) |
| 5 | Case-twin rollback proven on a case-sensitive folder | VERIFIED | `tests/test_case_sensitive_install.py` re-run here with `-rs`: passes, no skips (inside the 99 passed) |

### Gap-closure truths (UAT)

| Gap | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| G-12-9..12-23 | Toolbar Help/F1, start Cancel and compact start page, numbered menu, Skip for the 3D check, shared parentless guide, remembered place | VERIFIED (no regression) | Verified in the previous report; the 12-21 diff touches `help_dialog.py` and `show_guide` only. `tests/test_help_dialog.py` (61 incl. all 12-14, 12-19 tests), `test_layering.py`, `test_importer_layering.py`, `test_plain_names.py`, `test_case_sensitive_install.py` pass: 99 passed. Orchestrator full suite at HEAD: `-m "not wurth"` 3366 passed, 4 expected skips, 0 failed (1115 s); `-m wurth` 6036 passed (316 s) |
| G-12-27 D1 | A reused guide reopened with Close or Escape (also after the import window's Help) brings the chosen section heading to the top; asking the guide for the topic it already shows does too | VERIFIED | `_show_current_heading()` (help_dialog.py:712-723) scrolls a section to its anchor and a page to 0, never selects or saves. Called from `show_topic` after `setCurrentItem` (line 741, also when the item is already current) and from every non-spontaneous `showEvent` at once and on the next event-loop turn (663-664) after `fit_window`. Tests located and passing: `test_main_window_help_brings_the_section_heading_back[close, escape, import help between, import help guide left open]`, `test_reopened_guide_brings_the_section_heading_back[close, escape]`, `test_show_topic_on_the_shown_topic_brings_its_heading_back` |
| G-12-27 D2 | A fresh guide narrowed by `fit_window` still shows the saved heading | VERIFIED | `showEvent` re-runs the heading helper after `fit_window`; `test_fresh_guide_shows_the_saved_heading_after_fit_window_narrows` passes |
| G-12-27 D6 | Main-window Help on a visible guide still on a topic a caller asked for goes back to the owner's section with that row alone selected; a visible guide on the owner's own place is only raised, page not moved; the flag never saves | VERIFIED (edge case WR-09 noted) | `_on_asked_topic` set in `show_topic` (742), cleared in `show_remembered` (706) and in the owner-move save (786); `shows_asked_topic()` (708); `main_window.py:1368` `elif not first and (not guide.isVisible() or guide.shows_asked_topic()): guide.show_remembered()`. One non-comment `save_help_topic(` call and zero `load_help_topic` in `main_window.py` (grep). `test_main_window_help_brings_the_section_heading_back[import help, guide left open]`, `test_main_window_help_on_a_visible_guide_only_raises`, `test_asked_topic_lasts_until_the_owner_moves` pass. WR-09: when the asked topic equals the saved place the flag is still True and a page entry scrolls to its top, contradicting "only brought to the front"; read in the code, no test, advisory |
| G-12-27 D3 | A held left press selects and saves the pressed row; the menu folds only after the release; only the left button holds; the hold ends on left release, hide, key press, or a move with the left button reported up | VERIFIED | `eventFilter` on the menu viewport and the menu (help_dialog.py:675-697, `installEventFilter` twice at 625-626) sets `_menu_held` on a left press or double-click only, clears it on left release and schedules the fold after it, clears it on `KeyPress`; `hideEvent` (666-673) ends it; `_on_topic_selected` (790-794) defers only while `_menu_held` and `QGuiApplication.mouseButtons() & LeftButton`, else folds at once. The filter never consumes an event (ends in `super().eventFilter`). `test_held_press_on_a_page_row_selects_that_row` (4 cases), `test_only_a_left_press_holds_the_menu`, `test_keyboard_move_after_a_lost_release_still_folds` (3 cases) pass |
| G-12-27 D4 | Selected menu row in the accent fill with white text from theme tokens by the menu's row painter; no stylesheet on the menu or the guide; Help F1 row and CLAUDE.md say where the guide reopens | VERIFIED (look on the real desktop is human item 1) | `_MenuSelectionDelegate` (help_dialog.py:47-61), `setItemDelegate` once (620). Non-comment `setStyleSheet` count in `help_dialog.py`: 0. `test_menu_selected_row_stands_out`, `test_menu_keeps_its_arrows_and_indentation`, `test_help_says_the_guide_reopens_where_you_left_it` pass. CLAUDE.md User Guide bullet greps for 'scrolled to its heading', 'also while it is still open', 'only brought to the front' each print 1 |
| G-12-27 / UAT 27 | After the owner chooses 4.4.7 Conflicts and closes the guide, Help or F1 shows 4.4.7 Conflicts selected with its heading at the top, also on the real desktop at 100% and 200% | UNCERTAIN (human decision requested) | The owner's report (row 4.4 selected, page top, with `settings.ini` `last_topic=importing#conflicts`) was inconclusive in the debug session (7 full-app runs, not reproduced). Only two confirmed defects (D1, D3) and one reproduced path (guide left open after the import window's Help, now RED-then-GREEN) are fixed. The step-1 order (Close, then F1) has no reproduced mechanism and no RED test; the Close and Escape cases pin the selection and pass already. 12-UAT.md still records G-12-27 `status: failed` (line 491-496). Plan 12-21 names the owner's re-check as the gate and forbids marking it resolved from automated results. Not FAILED: the implementation is present, wired and tested; not VERIFIED: the owner-observed behaviour is unconfirmed |

**Score:** 12/13 truths verified (5 roadmap success criteria, the earlier gap-closure contracts counted as in the previous report, plus G-12-27 D1, D2, D3, D4, D6 counted together as the automated half); 1 UNCERTAIN (G-12-27 page-row half, human gate); 0 present-but-behavior-unverified. `human_needed` because the owner's re-check of test 27 and the real-display items below cannot be confirmed headless.

### Deferred Items

None. Later phase 13 (atomic migration, KiCad setup) does not cover guide behaviour.

### Advisory (New Scope, Unevidenced)

| # | Finding | Category | Why Advisory |
|---|---------|----------|--------------|
| 1 | WR-09 visible guide on an asked topic equal to the saved place scrolls to the heading, contradicting "only brought to the front" | other | code reading, no failing test; edge of the D6 truth, not the UAT 27 scenario |
| 2 | WR-10 clicking the already-current asked row neither saves nor clears the asked-topic flag | other | code reading, no failing test; the missing save predates 12-21 |
| 3 | WR-06 minimized guide not restored by F1 | other | reasoned from Qt behaviour, not reproduced (human item 5) |
| 4 | WR-07 unescaped source name in Skip button text | other | only reachable with `&` or `<` in a source folder name |
| 5 | WR-08 late-click test uses a fake scan | other | invariant enforced in `library_scanner.py`, covered by real `scan_all` tests |

12-REVIEW.md: 0 critical, 5 warnings (WR-06..WR-10, all `open` in 12-REVIEW-DISPOSITION.md), info IN-07..IN-13. WR-09 and WR-10 sit in the area the owner is about to re-check; if the owner sees F1 jump a page in step 5c-style flows, those are the first places to look. 12-SECURITY.md: threats closed. 12-VALIDATION.md and 12-UI-REVIEW.md advisory.

### Required Artifacts

| Artifact | Status | Details |
| -------- | ------ | ------- |
| `kicad_lib_manager/widgets/help_dialog.py` `_show_current_heading`, `shows_asked_topic`, `_on_asked_topic`, `eventFilter`, `hideEvent`, `_MenuSelectionDelegate` | VERIFIED | present, substantive (real scroll, flag, filter, painter), wired (show_topic, showEvent, `__init__`, `_on_topic_selected`) |
| `kicad_lib_manager/main_window.py` `show_guide` condition | VERIFIED | line 1368 contains `shows_asked_topic()`; docstring matches |
| `tests/test_help_dialog.py`, `tests/test_main_window.py` named tests | VERIFIED | all ten help_dialog tests and both main-window tests located by grep; collection shows `[close]`, `[escape]`, `[import help between]`, `[import help, guide left open]` parameter sets |
| `CLAUDE.md` User Guide bullet | VERIFIED | three scoped greps each print 1 |
| Tracer `.claude/debug/guide_trace.py` | VERIFIED | file exists, `git check-ignore` confirms ignored, `git ls-files -- '*guide_trace*'` prints nothing |
| Earlier artifacts (scan_progress.py, scan_cache.py FORMAT 2, settings help helpers, etc.) | VERIFIED | unchanged since the previous report; regression-checked by tests |

### Key Link Verification

| From | To | Status |
| ---- | -- | ------ |
| `HelpDialog.showEvent` -> `_show_current_heading` (after `fit_window`, at once and next turn) | WIRED (663-664) |
| `HelpDialog.show_topic` -> `_show_current_heading` (also when already current) | WIRED (741) |
| menu viewport release -> `_sync_expansion` after the view handled it | WIRED (684-686) |
| `_on_topic_selected` -> `QGuiApplication.mouseButtons()` live check | WIRED (790); `from PySide6.QtGui import QGuiApplication` present |
| menu key press -> ends hold, schedules fold | WIRED (688-693) |
| `HelpDialog.__init__` -> `_MenuSelectionDelegate` via `setItemDelegate` | WIRED (619-620) |
| `hideEvent` -> ends hold, runs a waiting fold | WIRED (666-673) |
| `MainWindow.show_guide` -> `show_remembered()` for hidden or asked-topic guide | WIRED (main_window.py:1368-1369) |
| `_on_topic_selected` owner-move save -> `_on_asked_topic = False` | WIRED (785-786) |

### Data-Flow Trace (Level 4)

Owner click -> `currentItemChanged` -> `_on_topic_selected` -> `save_help_topic(entry.key)` -> QSettings -> `show_remembered` -> `load_help_topic` -> `show_topic` -> `_show_current_heading` -> `QTextBrowser.scrollToAnchor`. FLOWING (the main-window end-to-end test reads `settings.load_help_topic()` and the browser's heading position after a reopen; the restart test reads through a fresh settings object). The scroll uses `entry.anchor` of an outline entry found by key lookup, never the saved text (T-12-51).

### Behavioral Spot-Checks (run here with `env/Scripts/python.exe`, targeted files only)

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Guide reopen, asked topic, held press, selected row, Help wording, theme tokens, layering, plain names, case-twin rollback | `pytest tests/test_help_dialog.py tests/test_case_sensitive_install.py tests/test_layering.py tests/test_importer_layering.py tests/test_plain_names.py -q -rs -m "not wurth"` | 99 passed, 6.4 s, no skips | PASS |
| Main-window Help end to end (four reopen cases, visible-guide raise-only, shared guide, window-modal dialogs) | `pytest tests/test_main_window.py -q -rs -k "guide or help"` | 17 passed, 2.2 s | PASS |
| Full suite at HEAD (orchestrator evidence, not re-run; code unchanged since 90c2db9) | `pytest -m "not wurth"` and `pytest -m wurth` | 3366 passed, 4 expected skips, 0 failed (1115 s); 6036 passed (316 s) | PASS (reported) |

### Probe Execution

No `probe-*.sh` declared or found. SKIPPED.

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
| ----------- | ------------ | ------ | -------- |
| VER-02 | 12-01 | SATISFIED | SC5; case-sensitive tests re-run, no skips |
| UI-01 | 12-02, 12-12..12-21 | SATISFIED for code and tests; owner re-check of UAT 27 pending | SC4; theme-token guard passes; 12-21 declares `requirements: [UI-01]`. The guide look and reopen behaviour on the real desktop is the human gate |
| REV-01 | 12-03, 12-08 | SATISFIED | SC1 |
| REV-02 | 12-04, 12-08 | SATISFIED | SC1 |
| REV-03 | 12-05, 12-08 | SATISFIED | SC2 |
| REV-04 | 12-05, 12-07, 12-08, 12-09, 12-11, 12-13 | SATISFIED | SC2 (live timing pending, human item 8) |
| REV-05 | 12-06, 12-08, 12-10 | SATISFIED | SC3 (live dialog pending, human item 7) |

All seven phase IDs appear in PLAN frontmatter `requirements:` (grepped across 12-01..12-21) and in REQUIREMENTS.md (lines 88, 92-96, 106; traceability rows 169-174, 181). No orphaned requirements.

**Bookkeeping, not a goal gap (orchestrator owns these edits):** REQUIREMENTS.md still shows all seven as `[ ]` / Pending. ROADMAP.md line 33 shows Phase 12 unchecked and line 257 still says "1 gap-closure plan pending: 12-21". 12-UAT.md header is `status: diagnosed` with G-12-27 `status: failed`; leave G-12-27 failed until the owner's re-check passes (plan 12-21 forbids resolving it from automated results).

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX` marker in `help_dialog.py` or `main_window.py` additions of 12-21 (the only hex-looking matches are CSS built from theme tokens). No stubs or hollow props in the new code.

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `main_window.py` / `help_dialog.py` | 1368; 699-742 | Asked-topic flag not compared with the saved place (WR-09, open) | Warning | A visible guide whose asked topic equals the saved place jumps to the heading on F1, against the documented "only brought to the front" |
| `help_dialog.py` | 786, 843-847 | Clicking the already-current asked row does not clear the flag or save (WR-10, open) | Warning | Next F1 may move the owner to the earlier saved place |
| `main_window.py` | 1369-1374 | Minimized guide not restored (WR-06, open) | Warning | F1 may appear to do nothing |
| `widgets/scan_progress.py` | 62-67, 90 | Source name unescaped (WR-07, open) | Warning | Not reachable with shipped sources |
| `tests/test_main_window.py` | 1517-1553 | Shallow late-Skip test (WR-08, open) | Warning | Invariant covered elsewhere |
| `help_dialog.py` | 688-693 | Any key press, including a bare modifier, ends the hold mid-drag (IN-12) | Info | Rare |

### Prohibitions

- Test-tier, 12-21: no colour literal or px font size in `help_dialog.py`: `test_help_css_uses_theme_tokens_only` passes. Resolved.
- Test-tier, 12-21: no stylesheet in `help_dialog.py`: non-comment `setStyleSheet` count 0; `test_menu_keeps_its_arrows_and_indentation` passes. Resolved.
- Test-tier, 12-21: only one save, no settings read in `main_window.py`: non-comment `save_help_topic(` count 1, `load_help_topic` count in `main_window.py` 0; `test_an_explicit_topic_wins_and_is_not_remembered` passes. Resolved.
- Test-tier, 12-21: tracer not in the repo: `git ls-files -- '*guide_trace*'` prints nothing, `git check-ignore -q .claude/debug/guide_trace.py` exits 0. Resolved.
- Judgment-tier (carried): user-facing text uses no raw KiCad field names or code identifiers. The new Help F1 sentence and CLAUDE.md wording ("page or section you last chose", "scrolled to that heading", "brought to the front") are plain. Mechanical verdict: satisfied; wording judgment stays with the owner (non-authoritative).

### Human Verification Required

1. **G-12-27 / UAT test 27 owner re-check (the gate for this plan).** Steps 1 to 6 plus 5b and 5c at 100%, then 1, 2 and 6 at 200%, as in the frontmatter. Expected: 4.4.7 Conflicts selected (blue fill, white text), Importing Parts open, heading at the top, arrows and indentation intact, step 5c page not moving. Why human: the owner's step-1 report was never reproduced and has no RED test. If the row 4.4 or the page top still shows where Conflicts is expected, G-12-27 stays failed; the owner runs `.claude\debug\guide_trace.py` and returns `guide_trace.log` with screenshots for a new debug round. Also confirm step 5b's behaviour (guide goes back to Conflicts) is wanted; if not, that is a behaviour change, not a failure.
2. **G-12-12 real display at 100% and 200%** (compact start page, Cancel in the Browse row, no size jump).
3. **User Guide at 200%** (UAT 13 remainder).
4. **G-12-21 live Skip against the real Wurth library** (timing, log line, trees, Generate Tables, restart note, Rescan).
5. **G-12-22 guide beside every window on real Windows, including a minimized guide (WR-06).**
6. **Toolbar and Help in the real import window** (UAT 10 appearance).
7. **UAT 3 live KiCad-open dialog** from the main checkout.
8. **UAT 4 (owner skipped)**: Finishing strip with a real kicad-cli rebuild.

### Gaps Summary

No code gaps. All five ROADMAP success criteria are verified, and plan 12-21's implementation is present, substantive, wired and backed by named tests that were located and re-run here (99 + 17 passed) plus the orchestrator's green full runs at HEAD (3366 and 6036 passed, 0 failed). The phase is not `passed` because G-12-27 (UAT test 27) remains `failed` in 12-UAT.md: the owner's exact report was not reproduced for the Close-then-F1 order, the plan makes the owner's real-desktop re-check the gate, and the seven real-display items carried from earlier rounds are still open. Two open review warnings (WR-09, WR-10) concern the new asked-topic flag; fixing them before the owner's pass would remove the most likely source of a surprising F1 in step 5b/5c. After the owner's re-check passes, mark G-12-27 and the other failed UAT gaps resolved in 12-UAT.md and flip REQUIREMENTS.md and ROADMAP.md.

---

_Verified: 2026-11-11_
_Verifier: Claude (gsd-verifier)_
