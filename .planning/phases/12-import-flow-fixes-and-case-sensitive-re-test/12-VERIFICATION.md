---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
verified: 2026-11-04T12:00:00Z
status: human_needed
score: 8/8 must-haves verified
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
  - kicad_lib_manager/importer/applier.py
  - kicad_lib_manager/importer/kicad_cli.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/preview.py
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/table_generator.py
  - kicad_lib_manager/widgets/backup_dialog.py
  - kicad_lib_manager/widgets/conflict_row.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - kicad_lib_manager/widgets/theme.py
  - tests/casefixtures.py
  - tests/conftest.py
  - tests/test_case_sensitive_install.py
  - tests/test_generated_text.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_official_footprint.py
  - tests/test_plain_names.py
covered_digest: "v3:sha256:cfc45b880dc8cb7d7db39d04028a6522466265515972511332b6a379a5373fc9"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 6/6
  gaps_closed:
    - "G-12-10 the import window has a Cancel on the start page and fits the free area of its screen (plan 12-13)"
    - "G-12-11 the User Guide menu is numbered, lists each page's sections, and click scrolls to the heading (plan 12-14)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "G-12-10 / plan 12-13 D2, real Windows display at 100% and again at 200% scale: note `git -C Custom status --short`, run `.\\env\\Scripts\\python.exe kicad_lib_manager.py`, press Ctrl+I, then open `downloaded_examples\\ul_CSD85301Q2.zip` and pick an Atomic_ library, press 'Choose another package...', then Cancel"
    expected: "Start page window is small (about 640x440) and fully on screen above the taskbar, Cancel at its bottom right. After a package opens the window grows, stays above the taskbar, and Install Part and Cancel show at its bottom right. 'Choose another package...' shrinks it again. Cancel closes it. `git -C Custom status --short` is unchanged. Text sharp and not clipped at 200%"
    why_human: "Tests model 200% as a 960x492 free area in logical pixels on the offscreen platform. Real DPI scaling, the real taskbar, real fonts and the first-show centring on a real window manager cannot be reproduced offscreen"
  - test: "G-12-11 / plan 12-14 D5, real Windows display at 100% and 200%: press F1 in the main window; click '4 ... Importing Parts' (shown as 4.4), then Conflicts; close; press Ctrl+I then Help and F1 in the import window"
    expected: "The User Guide lies fully on screen with its Close button visible. Menu reads '1 Overview', '2 Getting Started' and so on, the page heading carries the same number. 'Importing Parts' opens its ten sections numbered from 4.4.1; Conflicts (4.4.7 today, the owner's example said 4.4.8) scrolls the page to the Conflicts heading. From the import window the guide opens on Importing Parts. Headings look as before (same size and colours)"
    why_human: "Real-window look, sharpness at 200%, and menu feel. Tests assert structure, numbers, scroll offsets and sizes, not appearance"
  - test: "UAT 10(a-e) toolbar Help in the real import window (carried from the previous report; G-12-9 appearance)"
    expected: "Toolbar row with the help icon and 'Help' at the top of every page; Help or F1 opens the User Guide on Importing Parts; both windows take input; cancelling the import window closes the guide; row not clipped, no stray gap"
    why_human: "Nobody has seen the toolbar drawn with real fonts. This is combined with the two checks above in one pass"
  - test: "UAT 3 (blocked by the worktree guard): from the main checkout change CUSTOM_3DMODEL_DIR in KiCad, leave KiCad open, press Generate Tables"
    expected: "Dialog 'KiCad is open' with Retry (default), Change anyway, Not now. Retry after closing KiCad leads to the Yes/No question. Not now writes nothing"
    why_human: "Needs a live KiCad process and a modal dialog; the tests replace kicad_running"
  - test: "UAT 4 (skipped by owner): Finishing strip during a real kicad-cli rebuild"
    expected: "Dialog greys out with 'Finishing the preview...', window stays live, slow note after 10 s, no hang"
    why_human: "Real timing; covered only by gated stand-in workers. The owner chose to skip the manual check"
---

# Phase 12: Import Flow Fixes and Case-Sensitive Re-test Verification Report

**Phase Goal:** The import dialog, the post-install table step and the `kicad_common.json` write behave correctly in the cases the v1.0 reviews left open. The Help dialog follows the theme, and case-twin rollback is proven on a case-sensitive folder.
**Verified:** 2026-11-04
**Status:** human_needed
**Re-verification:** Yes, after gap-closure plans 12-13 (G-12-10) and 12-14 (G-12-11), merged at HEAD 048e1a6. The previous report (2026-11-03, covering 12-01..12-12) is replaced and now covers all 14 plans. Code for 12-01..12-12 was not re-read in depth: only regression-checked (targeted tests re-run, the orchestrator's full suite at HEAD is green). 12-13 and 12-14 were read and tested in full.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | "Already listed" only when the managed entry points at that library; empty Destination writes no table, never in the working directory | VERIFIED | Unchanged by 12-13/12-14 (neither touches table_generator.py, library_scanner.py or main_window.py; the only main_window.py line referencing the guide is still `HelpDialog(parent=self).exec()` at 1308). Covered by the full suite at 048e1a6 (9321 passed) |
| 2 | One-off conflict build never runs during Install; window responsive while kicad-cli works | VERIFIED (live timing is a human item) | Finishing state unchanged. 12-13 routes the start Cancel through `reject()` so the Finishing rules apply; `test_start_page_cancel_while_reading_waits_then_closes` passes (re-run here) |
| 3 | KiCad-running confirm says so before writing; confirmed write starts from current content | VERIFIED (real dialog is a human item) | Unchanged since previous report; full suite green |
| 4 | Help dialog and conflict rows use theme tokens only (no colour literal, no `#FFFFFF`, no px font size) | VERIFIED | `help_dialog.py` CSS: grep finds `px` only in margin/padding/border values, every `font-size` is `{..._PT}pt`; no hex literal. 12-14 adds numbers and empty anchors only, no CSS change. `test_help_css_uses_theme_tokens_only`, `test_rendered_headings_keep_their_look[importing|filter]` pass (re-run here, 43 passed) |
| 5 | Case-twin rollback proven on a case-sensitive folder | VERIFIED | `tests/test_case_sensitive_install.py` re-run here with `-rs`: no skips, passes (inside the 43 passed) |

### Gap-closure truths

| Gap | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| G-12-10 | Start page has a Cancel at its bottom right wired to `reject()`; no new close logic | VERIFIED | import_dialog.py:772-775: `QPushButton("Cancel")`, tooltip "Close without importing. Nothing is written.", `clicked.connect(self.reject)`, added to a stretch-then-button row `_start_bottom` on the page's outer layout. Enabled while reading (`_set_reading` untouched). `test_start_page_cancel_closes_without_writing` and `..._while_reading_waits_then_closes` pass |
| G-12-10 | The window opens small (640x440), grows to the edit size bounded by the screen, shrinks back on Choose another package..., result page keeps its size | VERIFIED | `_START_SIZE = QSize(640, 440)` (82), `_EDIT_SIZE = QSize(1100, 720)` (81), `self.resize(_START_SIZE)` (554), fixed `setMinimumSize` gone (grep: only a comment mentions it). `_show_page` (596-614) is the only `_stack.setCurrentWidget` call (grep, line 607) and is used at all six switch points (567, 1435, 1535, 1562, 3107, 3476); it stores the edit size on leaving edit/result, fits `_edit_size` on entering edit and `_START_SIZE` on entering start. `_sync_page_policies` gives hidden pages Ignored so the start minimum drops. `test_start_page_opens_small` (100%/200%), `test_window_grows_for_the_edit_page_and_shrinks_back`, `test_result_page_keeps_the_size_and_has_close` pass |
| G-12-10 | Whole window (frame + bottom row) lies inside the screen's free area at 100%, 200% and the owner's screen | VERIFIED in model, HUMAN for real display | `screen_area` (143), `_fit_size` (152), `_place_inside` (160), public `fit_window` (174): bounded by free area less frame, never below the layout minimum, moved inside only when visible (first-show centring kept); `showEvent` calls `_fit_to_screen(self.size())` (1338). `test_fit_size_and_place_inside`, `test_window_fits_the_screen[3 areas]`, `test_window_fits_the_screen_on_first_show`, `test_screen_area_reads_the_widget_screen` pass. See human item 1 |
| G-12-10 | Conftest default screen does not hide the real code | VERIFIED | `_desktop_screen_area` autouse fixture (conftest.py:41-53) patches only when the import module is already in `sys.modules`; no module-level PySide6 import in conftest; the real function is separately tested by `test_screen_area_reads_the_widget_screen` |
| G-12-10 | Help names the start Cancel and the window size in plain words | VERIFIED | help_dialog.py:226-229 ("bottom right", "without importing", "opens small", "grows", "fit your screen"). `test_help_names_the_start_page_cancel`, `test_help_says_the_window_fits_the_screen` pass |
| G-12-11 | Menu numbered from order (groups/pages 1..7, 4.4, sections 4.4.n), numbers rendered not typed | VERIFIED | `help_outline()` (help_dialog.py:529-543) numbers TOC_STRUCTURE depth first and appends sections as `<page>#<anchor>`; `render_page` (546-561) prefixes the `<h2>` and each `<h3>` with the outline number and an empty `<a name=...></a>` placed before the text (not a wrapper). HELP_PAGES/TOC_STRUCTURE unchanged. `test_help_outline_numbers_follow_the_menu_order`, `test_numbers_are_rendered_not_typed` pass |
| G-12-11 | Each page's `<h3>` headings are the menu's third level, derived from the page text; page headings carry the same numbers | VERIFIED | `page_sections` reads `_H3_RE` over HELP_PAGES (single source); `_build_toc` builds items only from `help_outline()`. `test_every_page_heading_is_in_the_menu_under_its_page`, `test_page_headings_carry_the_menu_numbers` pass |
| G-12-11 | Click on a section shows its page and scrolls to the heading; clicking the selected section again scrolls back | VERIFIED | `_on_topic_selected` (638-655): loads `render_page` when the page differs, then `scrollToAnchor(entry.anchor)`; `itemClicked` -> `_on_item_clicked` (666-670) re-scrolls when the item is already current. `test_clicking_a_section_scrolls_to_its_heading` (all 20 sections, real mouse click on Commit), `test_clicking_the_selected_section_again_scrolls_back`, `test_clicking_a_page_below_the_open_one_selects_it` pass |
| G-12-11 | Menu opens the shown page's sections, folds the others, groups stay open | VERIFIED | `_sync_expansion` (657-664) with `QTimer.singleShot(0, ...)` deferral after mouse selection (documented deviation: folding under a pressed button cleared the selection). `test_menu_expands_the_shown_page_only` passes |
| G-12-11 | `HelpDialog(topic='importing')` and the main window's Help still work; a section key opens that section | VERIFIED | `__init__(parent=None, *, topic=None)`, `show_topic` walks all levels and falls back to the first item; callers unchanged: main_window.py:1308 `HelpDialog(parent=self).exec()`, import_dialog.py:644 `HelpDialog(topic=_HELP_TOPIC, parent=self)`. `test_help_dialog_opens_on_a_given_topic` and the import-window Help tests (toolbar, F1, every page, installing, committing, finishing, real clicks) pass |
| G-12-11 | The User Guide window lies inside the screen's free area at 100% and 200% with Close visible | VERIFIED in model, HUMAN for real display | `HelpDialog.showEvent` (602-605) calls `fit_window(self, self.size())`; `fit_window` imported at module level from `.import_dialog` (line 13, no circular import because import_dialog imports help_dialog only inside `_on_help`). `test_help_dialog_fits_the_screen` and `test_help_window_fits_the_screen[100%/200% x toolbar/f1]` pass. See human item 2 |
| G-12-9, G-12-5..8 | Toolbar Help/F1, plain names, Cancel, required hints, "Choose another package..." | VERIFIED (no regression) | `test_plain_names.py` and the import-window Help tests re-run and pass; code paths untouched apart from `_show_page` |

**Score:** 8/8 truths verified (5 roadmap success criteria plus the G-12-9, G-12-10 and G-12-11 gap-closure contracts, counting 12-13 and 12-14 as one truth each beyond the earlier six); 0 present-but-behavior-unverified. Status is `human_needed` solely for the real-display checks below.

### Required Artifacts

| Artifact | Status | Details |
| -------- | ------ | ------- |
| `widgets/import_dialog.py` `screen_area`, `fit_window`, `_fit_size`, `_place_inside`, `_show_page`, `_sync_page_policies`, `_start_cancel_btn`, size constants | VERIFIED | present, substantive, wired (lines above) |
| `widgets/help_dialog.py` `HelpEntry`, `section_anchor`, `page_sections`, `help_outline`, `render_page`, `showEvent`, `_sync_expansion`, `_on_item_clicked` | VERIFIED | present, substantive, wired; `scrollToAnchor(` at 653 and 670, `itemClicked` connected at 583, `fit_window(self, self.size())` at 605 |
| `tests/conftest.py` `_desktop_screen_area` | VERIFIED | lines 41-53 |
| New tests named in the plans (11 for 12-13, 14 for 12-14) | VERIFIED | names collected and passing; see spot-checks |
| 12-01..12-12 artifacts | VERIFIED | previous report; unchanged |

### Key Link Verification

| From | To | Status |
| ---- | -- | ------ |
| `_start_cancel_btn.clicked` -> `self.reject` | WIRED (774) |
| `_show_page` -> `_fit_to_screen` -> `fit_window` -> `screen_area` | WIRED (611-614, 583-584, 180) |
| All page switches -> `_show_page` | WIRED (six call sites; single `setCurrentWidget` on the stack) |
| `help_outline()` -> `_build_toc` / `render_page` / `_entries` | WIRED (570, 625, 552) |
| `_on_topic_selected` -> `scrollToAnchor` | WIRED (653) |
| `HelpDialog.showEvent` -> `fit_window` | WIRED (605, import at 13) |
| `ImportDialog._on_help` -> `HelpDialog(topic=...)`; `MainWindow._on_help` -> `HelpDialog(parent=self).exec()` | UNCHANGED |

### Data-Flow Trace (Level 4)

Menu text, numbers and anchors flow from the static HELP_PAGES/TOC_STRUCTURE through `help_outline()`; no dynamic user data. Window sizes flow from `QScreen.availableGeometry()` via `screen_area` (real function tested against the widget's screen). FLOWING.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Help guide, plain-name guard, case-twin rollback | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py tests/test_plain_names.py tests/test_case_sensitive_install.py -q -rs` | 43 passed, no skips, 5.96 s | PASS |
| Start Cancel, fit/placement, small start, grow/shrink, result page, guide fit, toolbar Help, F1, input while Help open, Cancel | `pytest tests/test_import_dialog.py -q -rs -k "start_page_cancel or fit_size or fits_the_screen or screen_area or start_page_opens_small or grows_for_the_edit or result_page_keeps or help_window_fits or toolbar_help or f1_opens or help_reachable or help_works or takes_input_while_help or cancel_button"` | 27 passed, 221 deselected, 74 s | PASS |
| Full suite at HEAD 048e1a6 (orchestrator evidence, not re-run) | `pytest -q` | 9321 passed, 4 skipped (environment-only), 0 failed, 22 min | PASS (reported) |

### Probe Execution

No `probe-*.sh` declared or found. SKIPPED.

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
| ----------- | ------------ | ------ | -------- |
| VER-02 | 12-01 | SATISFIED | SC5, tests re-run, no skips |
| UI-01 | 12-02, 12-12, 12-13, 12-14 | SATISFIED | SC4; 12-13/12-14 add no colour literal or px font size; screen fit and numbered headings keep the look |
| REV-01 | 12-03, 12-08 | SATISFIED | SC1 |
| REV-02 | 12-04, 12-08 | SATISFIED | SC1 |
| REV-03 | 12-05, 12-08 | SATISFIED | SC2 |
| REV-04 | 12-05, 12-07, 12-08, 12-09, 12-11, 12-13 | SATISFIED | SC2 (live timing pending, human item 5) |
| REV-05 | 12-06, 12-08, 12-10 | SATISFIED | SC3 (live dialog pending, human item 4) |

All seven phase IDs appear in PLAN frontmatter `requirements:` (12-01..12-14, grepped) and in REQUIREMENTS.md (lines 88, 92-96, 106). No orphaned requirements.

**Bookkeeping, not a goal gap:** REQUIREMENTS.md still shows all seven as `[ ]` / "Pending" (lines 88-96, 106, 169-181). ROADMAP.md line 33 shows Phase 12 unchecked and line 257 still says "2 gap-closure plans pending: 12-13, 12-14" although both plan boxes (287-288) are checked. 12-UAT.md records G-12-10 and G-12-11 as `status: failed`; set them resolved only after human items 1 and 2 pass. The orchestrator owns these edits.

### Anti-Patterns Found

No TBD/FIXME/XXX/TODO/HACK in import_dialog.py, help_dialog.py or conftest.py. No stubs or hollow props in the new code.

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `import_dialog.py` | 192-193 | Only one blank line between `fit_window` and `_START_BODY` | Info | Style only |
| `help_dialog.py` | 666-670 | `_on_item_clicked` re-scrolls only for section items; re-clicking the already-selected page item does not scroll the page back to the top | Info | Outside the plan's contract (the plan only requires section re-click); no goal impact |

12-REVIEW.md: 0 critical, 1 warning (WR-02, carried, guarded by `test_required_field_hints_match_the_atomic_strip`), 4 info; 12-SECURITY.md: verified, 0 open threats at plan 12-12. 12-13/12-14 introduce threats T-12-32..37; each has a named passing test (see above); the anchors come only from `section_anchor` (a-z, 0-9, hyphen).

### Prohibitions

- Test-tier, 12-13: start Cancel never bypasses close rules (only `reject()`, existing `test_close_refused_while_installing` / `test_cancel_button_during_build_enters_finishing` pass inside the `cancel_button` selection; the six narrow-window tests were reordered and pass; real `screen_area` tested separately; user text plain: tooltip and Help sentences contain no identifiers). All wired to named, passing tests.
- Test-tier, 12-14: HELP_PAGES/TOC_STRUCTURE stay unnumbered (`test_numbers_are_rendered_not_typed`), anchors are empty named anchors before the text (`test_rendered_headings_keep_their_look`), no caller change (grep above). Passing.
- Judgment-tier (12-08), "User-facing text must not use raw KiCad field names or code identifiers": new texts read "Cancel", "Nothing is written", "opens small", "fit your screen", "User Guide". Mechanical verdict: satisfied. Plain-language judgment of the wording stays with the owner.

### Human Verification Required

1. **Real Windows display at 100% and 200%, import window (G-12-10, plan 12-13 D2).** Test: note `git -C Custom status --short`; run `.\env\Scripts\python.exe kicad_lib_manager.py`; Ctrl+I; look at the start page; open `downloaded_examples\ul_CSD85301Q2.zip`, pick an Atomic_ library; press "Choose another package..."; press Cancel; repeat at the other scale. Expected: small start window fully above the taskbar with Cancel at the bottom right; edit window grows, stays above the taskbar, Install Part and Cancel visible; shrinks back; Cancel closes; `Custom` status unchanged; text sharp. Why human: real DPI, taskbar and fonts cannot be reproduced offscreen.
2. **Real Windows display at 100% and 200%, User Guide (G-12-11, plan 12-14 D5).** Test: F1 in the main window; click Importing Parts and Conflicts; then Ctrl+I, Help and F1 in the import window; repeat at the other scale. Expected: guide fully on screen with Close visible; numbered menu and matching page headings; sections listed and scroll on click; guide opens on Importing Parts from the import window; headings look as before. Why human: appearance, sharpness, menu feel.
3. **Toolbar and Help in the real import window (UAT 10, G-12-9 appearance).** Folded into checks 1 and 2: toolbar row not clipped, Help and F1 behave, guide closes with the import window.
4. **UAT 3 live KiCad-open dialog** from the main checkout. Why human: live KiCad process and modal dialog.
5. **UAT 4 (owner skipped)**: Finishing strip with a real kicad-cli rebuild. Why human: real timing.

### Gaps Summary

No gaps. G-12-10 and G-12-11 are closed in code and by targeted tests that were re-run here (43 + 27 passed, no skips), plus the orchestrator's full-suite run at HEAD 048e1a6 (9321 passed, 0 failed). Status is `human_needed` because the real-display behaviour at 100% and 200% scale (the owner's actual complaint in both gaps), toolbar appearance, the live KiCad-open dialog and the live rebuild cannot be confirmed programmatically. After items 1 and 2 pass, mark G-12-10 and G-12-11 resolved in 12-UAT.md and flip REQUIREMENTS.md / ROADMAP.md.

---

_Verified: 2026-11-04_
_Verifier: Claude (gsd-verifier)_
