---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
verified: 2026-11-04T18:00:00Z
status: human_needed
score: 12/12 must-haves verified
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
covered_digest: "v3:sha256:6506fe784a7f4991768126b989c89469eb66f2e8a6fc8cc3737a2f6611e709d1"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 8/8
  gaps_closed:
    - "G-12-12 start page is compact: Cancel shares the Browse row, window is 640 wide and as tall as its content (plan 12-15)"
    - "G-12-21 Loading Libraries window has a per-source Skip for the 3D model path check, honest saved scan, narrowed code signature, weighted progress (plans 12-16, 12-17)"
    - "G-12-22 one shared, parentless, non-modal User Guide usable beside the main window, the import window and its dialogs; main-window dialogs made window-modal (plans 12-18, 12-20)"
    - "G-12-23 the User Guide remembers the owner's last page or section (plan 12-19)"
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "WR-06: Help or F1 does not restore a minimized User Guide (show()/raise_()/activateWindow() do not un-minimize on Windows); reasoned from Qt behaviour, not reproduced"
    category: other
    reason: "Raised by 12-REVIEW.md, disposition open. The guide is now a parentless window with its own taskbar button, so minimizing is ordinary. Resolve by the review's two-line fix plus a test, or confirm on a real Windows display (human item 4)"
    evidence_status: "none provided (no failing test)"
  - finding: "WR-07: source folder name goes unescaped into the Skip button text and tooltip ('&' becomes a mnemonic, '<..>' renders as markup)"
    category: other
    reason: "12-REVIEW.md, disposition open. Only reachable with a source folder name containing & or <; the shipped sources are Custom and WurthElektronik"
    evidence_status: "none provided (no failing test)"
  - finding: "WR-08: test_a_skip_click_after_the_check_ended_logs_no_skip and test_loading_dialog_skips_the_source_being_checked use a fake scan that ignores the skip hook, so the late-click path is not proven by that test"
    category: other
    reason: "12-REVIEW.md, disposition open. The invariant itself is enforced in code (skipped set is filled only when skip() answered True, library_scanner.py:576-580) and the real scan_all is driven in test_generate_after_a_skip_removes_no_entry and tests/test_scan_skip.py"
    evidence_status: "code reading supports the invariant; the named test is shallow"
human_verification:
  - test: "G-12-12 / plan 12-15, real Windows display at 100% and 200% scale: run `.\\env\\Scripts\\python.exe kicad_lib_manager.py`, press Ctrl+I; look at the start page; open `downloaded_examples\\ul_CSD85301Q2.zip` and pick an Atomic_ library; press 'Choose another package...'; then Cancel. Note `git -C Custom status --short` first and compare after"
    expected: "Start window is about 640 wide and only as tall as its content, with Browse zip..., Browse folder... and Cancel in one row (Cancel at the right end) and no empty band below. The window does not change size when the Downloads line appears or while a package is read. After a package opens the window grows and stays above the taskbar; 'Choose another package...' returns it to the compact size; Cancel closes; `Custom` status unchanged. Text sharp and not clipped at 200%"
    why_human: "Tests model the screens as logical free areas offscreen. Real DPI scaling, real taskbar, fonts and the first-show placement cannot be reproduced headless. The owner's UAT 12 run at 200% was still open"
  - test: "G-12-11 / plan 12-14 at 200% (UAT 13, 200% look still open): F1, click '4.4 Importing Parts', click its Conflicts section, then Ctrl+I, Help and F1 in the import window"
    expected: "Guide fully on screen with Close visible; numbers match the menu; section click scrolls to the heading; text sharp and not cut off"
    why_human: "Look and sharpness at 200%"
  - test: "G-12-21 / plans 12-16, 12-17, real startup with a real Wurth library: delete the saved scan (%APPDATA%/KiCadExtLibManager/scan_cache/) or edit a scan module so the full scan runs; while 'Loading Libraries' shows 'Checking 3D paths', click 'Skip WurthElektronik'. Close the app, start it again, then press Rescan"
    expected: "Button reads 'Skip WurthElektronik' during the 3D check, 'Skipping WurthElektronik...' after the click, window closes by itself, Escape and X do nothing while loading. The log has the single line '3D model paths of WurthElektronik were not checked: skipped while the libraries loaded. Rescan checks them.' and does not say 'No warnings.'. Both trees still list every WurthElektronik library; Generate Tables removes no Wurth entry. The next start shows the saved scan with the note that the 3D model paths were skipped in that scan; Rescan does the full check and the note disappears. Startup is noticeably faster"
    why_human: "Real timing against 5645 Wurth footprints and a real loading window; tests use a synthetic Wurth repo and fake workers for the GUI clicks"
  - test: "G-12-22 / plans 12-18, 12-20, real display: press F1 in the main window, leave the guide open, click in the main window, Generate Tables, open About and Restore Backup, trigger a rescan, press Ctrl+I and use Help in the import window, open a content view and Check Atomic Parts; then close the import window and the main window. Also minimize the guide and press F1 again (WR-06)"
    expected: "The guide is a separate window with its own taskbar button, scrolls and changes page while the main window, About, Restore Backup, the KiCad questions, the Loading Libraries window, the import window and its content view / Check Atomic Parts are open. A second F1 reuses the same window. The main window stays locked while the import window is open (design kept). System file pickers may block the guide (owner-approved exclusion). The guide stays open after the import window closes and closes with the main window. A minimized guide comes back on F1 (review WR-06 predicts it does not on Windows)"
    why_human: "Window-system modality, focus and taskbar behaviour on real Windows; tests use offscreen QWindow clicks"
  - test: "G-12-23 / plan 12-19, real app: in the guide browse to 4.4 Importing Parts > Conflicts, close with Close, press F1; repeat closing with Escape; restart the app and press F1; open the guide from the import window Help"
    expected: "F1 and a restarted app reopen on Importing Parts with its sections expanded, other pages folded, 4.4.7 Conflicts selected and in view. The import window's Help always opens Importing Parts and does not overwrite the remembered place"
    why_human: "Real restart and the scroll position in a shown window; the tests cover the saved key and selection, the owner said exact pixel scroll does not matter"
  - test: "UAT 10(a-e) toolbar Help in the real import window (carried; G-12-9 appearance)"
    expected: "Toolbar row with the help icon and 'Help' at the top of every page; Help or F1 opens the User Guide on Importing Parts; both windows take input; row not clipped, no stray gap. Note: since plan 12-18 the guide no longer closes with the import window (owner decision G-12-22), so the old expectation 'cancelling the import window closes the guide' is replaced by 'the guide stays open'"
    why_human: "Nobody has seen the toolbar drawn with real fonts"
  - test: "UAT 3 (blocked by the worktree guard): from the main checkout change CUSTOM_3DMODEL_DIR in KiCad, leave KiCad open, press Generate Tables"
    expected: "Dialog 'KiCad is open' with Retry (default), Change anyway, Not now. Retry after closing KiCad leads to the Yes/No question. Not now writes nothing. The dialog is now window-modal: the guide stays usable while it is open"
    why_human: "Needs a live KiCad process and a modal dialog; the tests replace kicad_running"
  - test: "UAT 4 (skipped by owner): Finishing strip during a real kicad-cli rebuild"
    expected: "Dialog greys out with 'Finishing the preview...', window stays live, slow note after 10 s, no hang"
    why_human: "Real timing; covered only by gated stand-in workers. The owner chose to skip the manual check"
---

# Phase 12: Import Flow Fixes and Case-Sensitive Re-test Verification Report

**Phase Goal:** The import dialog, the post-install table step and the `kicad_common.json` write behave correctly in the cases the v1.0 reviews left open. The Help dialog follows the theme, and case-twin rollback is proven on a case-sensitive folder.
**Verified:** 2026-11-04
**Status:** human_needed
**Re-verification:** Yes, after gap-closure plans 12-15..12-20 (UAT gaps G-12-12, G-12-21, G-12-22, G-12-23), merged at 130c3b8. The previous report (covering 12-01..12-14) is replaced and now covers all 20 plans. Code for 12-01..12-14 was only regression-checked (targeted tests re-run, orchestrator full suite green at 130c3b8). 12-15..12-20 were read in the code and their named tests collected and run here.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | "Already listed" only when the managed entry points at that library; empty Destination writes no table, never in the working directory | VERIFIED | `table_generator.py` and the post-install path are not in the diff of 12-15..12-20 for those functions; `main_window.py` changes are limited to the guide, scan dialog and dialog modality. Covered by tests/test_main_window_import.py (134 passed here with test_main_window.py) and the orchestrator's full suite (9382 passed at 130c3b8) |
| 2 | One-off conflict build never runs during Install; window responsive while kicad-cli works | VERIFIED (live timing is human item 8) | Finishing logic untouched by 12-15; start Cancel still calls `reject()` only (`import_dialog.py:792`); `test_start_page_cancel_while_reading_waits_then_closes` and the `cancel_button` tests pass in the 44-test import-dialog selection |
| 3 | KiCad-running confirm says so before writing; confirmed write starts from current content | VERIFIED (real dialog is human item 7) | 12-20 only changes modality: `_kicad_open_box` keeps title "KiCad is open", Retry/Change anyway/Not now, default Retry (`main_window.py:1170-1196`); `_confirm_path_var_changes` keeps text, buttons and default through `_question` (1136-1167). `test_kicad_open_box_texts_and_buttons` and the existing path-variable tests pass (test_main_window*.py 134 passed) |
| 4 | Help dialog and conflict rows use theme tokens only | VERIFIED | grep for `#hex` literals and `font-size:..px` in `help_dialog.py`, `scan_progress.py`, `conflict_row.py`: no match. `test_help_css_uses_theme_tokens_only` passes inside test_help_dialog.py (168 passed across the batch). `scan_progress.py` imports spacing from `.theme` only |
| 5 | Case-twin rollback proven on a case-sensitive folder | VERIFIED | `tests/test_case_sensitive_install.py` re-run with `-rs`: passes, no skips (inside the 168 passed) |

### Gap-closure truths (UAT)

| Gap | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| G-12-12 | Cancel shares the Browse zip.../Browse folder... row at its right end, no separate bottom row | VERIFIED | `import_dialog.py:785-794`: `_start_buttons` QHBoxLayout holds Browse zip, Browse folder, `addStretch(1)`, `_start_cancel_btn` (clicked -> `self.reject`). `_start_bottom` no longer exists (grep: no match). `test_start_page_cancel_shares_the_browse_row` passes |
| G-12-12 | Start page 640 wide and exactly as tall as its content (no empty band); refits when the issue list shows/clears | VERIFIED in model, HUMAN for real display | `_START_WIDTH = 640` (83); `_start_size()` (604-618) invalidates/activates the nested layouts then uses `totalHeightForWidth(640)`, never below `minimumSizeHint`; used in `_show_page` (648), `showEvent` (1381), `_hide_issue_box` (1585), `_show_start_issues` (1608). `test_start_page_is_as_tall_as_its_content` (100%/200%), `test_start_issues_refit_the_window` pass. The leftover `outer.addStretch(1)` (727) cannot create a band because the height is computed from the content |
| G-12-12 | Downloads line and reading box share one constant-height slot | VERIFIED | `_offer_slot` QGridLayout with `setRetainSizeWhenHidden(True)` on both members (770-778). `test_start_page_keeps_its_height_when_the_offer_arrives` passes |
| G-12-12 | Choose another package... returns to the compact size; edit size remembered; Help names where Cancel sits | VERIFIED | `_show_page` branch for the start page uses `_start_size()`; `test_window_grows_for_the_edit_page_and_shrinks_back` and `test_help_names_the_start_page_cancel` pass |
| G-12-21 | Loading Libraries window has a Skip button naming the source, enabled only while a source's 3D check runs, never closable by Escape/X | VERIFIED | New `widgets/scan_progress.py` `ScanProgressDialog`: `set_skippable(source)` -> "Skip <source>" enabled; idle -> "Skip" disabled; click -> "Skipping <source>..." and `skip_requested`; `reject()` is a no-op until `finish()`. `main_window.py` creates it in `_start_scan` (498), wires `checking` -> `_on_scan_checking` (518) and `skip_requested` -> `_on_skip_requested` (499) -> `ScanWorker.request_skip` (lock-guarded set, 93-99) -> `scan_all(skip=self._skip_requested, checking=self.checking.emit)` (136). Tests in test_main_window.py pass |
| G-12-21 | A skip stops only that source's 3D path check, drops no library or link, logs one plain line, claims no 'No warnings.' | VERIFIED | `_check_model_files` (library_scanner.py:553-615): the `skipped` set is filled only when `skip(source)` answered True, remaining files of the source are not read and its earlier lines are filtered out of the return value (615); `scan_all` still lists libraries and reads links, records `skipped_sources` and `models_unchecked` (705-730) and appends the exact line (621-632). main_window.py:648 prints "No warnings in the checks that ran." after a skip. tests/test_scan_skip.py (skipped lines, keep every library and link, unchanged scan without skip, rescan-library record, progress 0..100) all pass; `test_generate_after_a_skip_removes_no_entry` drives the real `scan_all` and passes |
| G-12-21 | Skipped scan is saved with skipped sources, reuse note says so, old format re-scans, code signature narrowed | VERIFIED | `scan_cache.py`: `FORMAT = 2` (38) with `skipped_sources`/`models_unchecked` encoded (432-445), skip reuse note (591-594), `_scan_code_files` follows package-internal imports from `library_scanner.py` and `scan_cache.py` only (206-242), `_code_signature_of` hashes that closure (245-255). `test_skipped_scan_round_trips`, `test_reuse_note_names_the_skipped_sources`, `test_format_1_saved_scan_is_a_different_version`, `test_code_signature_covers_the_scan_modules_only`, `test_code_signature_follows_scan_code_edits`, `test_skipped_scan_is_saved_and_the_next_start_says_so` pass. Layering: library_scanner and scan_cache import no Qt (`tests/test_layering.py` passes) |
| G-12-21 | Help 'Repository Scan' and CLAUDE.md explain Skip and the saved scan | VERIFIED | help_dialog.py:130-134 (Skip, the logged source, the saved scan); CLAUDE.md:55. `test_help_repo_scan_explains_skip_and_the_saved_scan` passes |
| G-12-22 | One shared, parentless, non-modal User Guide for Help menu and F1, reused on every call | VERIFIED | `main_window.py:1349-1377`: `_guide_window()` builds `HelpDialog()` with no parent and centres it; `show_guide(topic=None)` shows, raises, activates the same instance; `_on_help` no longer calls `exec()`. `test_main_window_help_opens_one_shared_non_modal_guide` and `test_main_window_and_guide_both_take_clicks` pass |
| G-12-22 | Import window Help/F1 use the shared guide via an injected callable, never own or close it; guide survives the import window; closes with the main window; refused close keeps it | VERIFIED | `ImportDialog(show_guide=...)` (import_dialog.py:449, 462), `_on_help` calls `self._show_guide(_HELP_TOPIC)` (673-674); `main_window.py:1045` passes `show_guide=self.show_guide`; no widget imports main_window (grep). `closeEvent` closes the guide only after every refusal branch (1421-1422). Tests `test_import_help_uses_the_shared_guide`, `test_import_window_with_a_guide_hook_creates_no_guide`, `test_guide_takes_clicks_beside_the_import_window_and_its_dialogs`, `test_guide_stays_open_after_the_import_window_closes`, `test_closing_the_main_window_closes_the_guide`, `test_a_refused_close_keeps_the_guide`, `test_guide_first_shows_over_the_main_window` pass |
| G-12-22 | Main-window dialogs (path question, KiCad-open box, Restore Backup, About) and the Loading Libraries window block only the main window; guide stays usable | VERIFIED | `_question` (1136-1146) and the KiCad-open box (1177), `BackupDialog` (1301) and About (1381) all call `setWindowModality(WindowModal)` and keep their blocking `exec()`; `ScanProgressDialog` is WindowModal with the main window as parent. `test_main_window_dialogs_are_window_modal_and_leave_the_guide_usable` (four cases) and `test_guide_takes_clicks_while_the_libraries_load` pass. System file pickers are intentionally left application-modal (owner-approved exclusion in 12-UAT.md; not a gap) |
| G-12-23 | Guide remembers the owner's last page or section across close, Esc, deleted parent and restart; explicit topics win and are not remembered; stale values fall back | VERIFIED | `settings.py:72-81` `load_help_topic`/`save_help_topic` ("help/last_topic", non-text or empty reads None). `help_dialog.py`: `__init__` calls `show_remembered()` only when no topic is given (610-619); `show_topic` and `show_remembered` run quiet so nothing programmatic is saved (630-658); `_on_topic_selected` saves `entry.key` for every owner move, not in closeEvent (695-696); fallback key -> page part -> first item (630-638). `test_owner_choice_is_remembered_after_close_escape_and_parent_deleted`, `test_saved_place_survives_a_restart`, `test_an_explicit_topic_wins_and_is_not_remembered`, `test_stale_saved_places_fall_back`, `test_import_help_keeps_opening_importing_parts_with_a_saved_place`, `test_main_window_help_reopens_the_owner_choice`, `test_main_window_help_on_a_visible_guide_only_raises`, `test_main_window_help_after_restart_opens_the_saved_place` pass. `show_guide` (1356-1374) restores only on a hidden, already-built guide; a new one restores itself in `__init__` |
| G-12-9..11 | Toolbar Help/F1, start Cancel, screen fit, numbered menu (earlier gap closures) | VERIFIED (no regression) | `test_help_dialog.py` (menu numbers, scroll, fit), `test_plain_names.py` and the 44-test import-dialog selection re-run and pass. Two assertions changed by design: the guide now outlives the import window (G-12-22) |

**Score:** 12/12 truths verified (5 roadmap success criteria, plus G-12-9/10/11 gap contracts counted as three, plus G-12-12, G-12-21, G-12-22 and G-12-23); 0 present-but-behavior-unverified. Status is `human_needed` only because real-display and real-timing behaviour cannot be confirmed headless (see below).

### Required Artifacts

| Artifact | Status | Details |
| -------- | ------ | ------- |
| `widgets/import_dialog.py` `_START_WIDTH`, `_start_size`, `_start_buttons`, `_offer_slot`, `show_guide` hook | VERIFIED | present, substantive, wired (lines above) |
| `widgets/scan_progress.py` `ScanProgressDialog` | VERIFIED | new file, imports PySide6 and `.theme` only; wired in `main_window._start_scan` |
| `main_window.py` `ScanWorker.request_skip/checking`, `_on_scan_checking`, `_on_skip_requested`, `_guide_window`, `show_guide`, `_question`, `closeEvent` guide close | VERIFIED | present, substantive, wired |
| `library_scanner.py` skip hooks, `models_skipped_issue`, `models_rechecked`, `models.py` `skipped_sources`/`models_unchecked`, `scan_cache.py` FORMAT 2, `_scan_code_files` | VERIFIED | present, substantive, wired; data flows from `ScanResult` to cache and note |
| `settings.py` `load_help_topic`/`save_help_topic`; `help_dialog.py` `show_remembered`, quiet counter | VERIFIED | present, substantive, wired |
| `tests/test_scan_skip.py` and the named tests of 12-15..12-20 | VERIFIED | all 40 named tests located by grep (none missing) and passing |

### Key Link Verification

| From | To | Status |
| ---- | -- | ------ |
| `_show_page` / `showEvent` / `_show_start_issues` -> `_start_size()` -> `_fit_to_screen` | WIRED (648, 1381, 1608) |
| `_start_cancel_btn.clicked` -> `self.reject` | WIRED (792) |
| `ScanProgressDialog.skip_requested` -> `MainWindow._on_skip_requested` -> `ScanWorker.request_skip` | WIRED (499, 532-539, 93) |
| `ScanWorker.run` -> `scan_all(skip=, checking=)` -> `_check_model_files` | WIRED (136; scan_all passes both, 705-708) |
| `scan_all` -> `ScanResult.skipped_sources` -> `scan_cache.save` / `load_fresh` note | WIRED (729-730; 432-445; 591-594) |
| `_code_signature` -> `_scan_code_files` | WIRED (245-262) |
| `_open_import` -> `ImportDialog(show_guide=self.show_guide)` -> `_on_help` -> `_show_guide('importing')` | WIRED (1045; 673-674) |
| `MainWindow.closeEvent` -> `self._guide.close()` after the refusal branches | WIRED (1421-1422) |
| `HelpDialog._on_topic_selected` -> `save_help_topic`; `show_remembered` -> `load_help_topic`; `show_guide` -> `show_remembered` | WIRED (695-696; 632; 1369) |
| `_confirm_path_var_changes` -> `_question` | WIRED (1163) |

### Data-Flow Trace (Level 4)

Skip: the request set on `ScanWorker` -> per-file `skip(source)` answer -> `skipped` set -> `ScanResult.skipped_sources` -> log line, "No warnings in the checks that ran." and saved scan -> next-start reuse note. FLOWING (real `scan_all` driven in `test_generate_after_a_skip_removes_no_entry` and `tests/test_scan_skip.py`). Guide place: owner move -> `save_help_topic` -> QSettings -> `load_help_topic` -> `show_topic`. FLOWING (restart test reads through a fresh settings object).

### Behavioral Spot-Checks (run here with `env/Scripts/python.exe`, targeted files only)

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Skip, saved scan, code signature, progress, guide persistence, help text, layering, plain names, case-twin rollback, rescan-library, settings | `pytest tests/test_scan_skip.py tests/test_scan_cache.py tests/test_help_dialog.py tests/test_layering.py tests/test_importer_layering.py tests/test_plain_names.py tests/test_case_sensitive_install.py tests/test_rescan_library.py tests/test_settings_import.py -q -rs` | 168 passed, no skips, 75 s | PASS |
| Main window: Skip button, shared guide, window-modal dialogs, import window beside the guide, post-install table step | `pytest tests/test_main_window.py tests/test_main_window_import.py -q -rs` | 134 passed, 79 s | PASS |
| Import window: start Cancel in the Browse row, compact height, offer slot, issue refit, grow/shrink, screen fit, Help/F1, guide hook, window-modal | `pytest tests/test_import_dialog.py -q -rs -k "start_page or start_issues or fits_the_screen or fit_size or screen_area or grows_for_the_edit or result_page_keeps or guide or help or f1 or cancel_button or window_modal"` | 44 passed, 211 deselected | PASS |
| Full suite at merge commit 130c3b8 (orchestrator evidence, not re-run) | `pytest -q` | 9382 passed, 4 skipped (environment-only: two UAT scratch-dir tests, two symlink-privilege tests), 0 failed | PASS (reported) |

### Probe Execution

No `probe-*.sh` declared or found. SKIPPED.

### Requirements Coverage

| Requirement | Source Plans | Status | Evidence |
| ----------- | ------------ | ------ | -------- |
| VER-02 | 12-01 | SATISFIED | SC5, case-sensitive tests re-run, no skips |
| UI-01 | 12-02, 12-12..12-20 (and others) | SATISFIED | SC4; no colour literal or px font size in help_dialog.py, scan_progress.py, conflict_row.py; theme-token guard passes |
| REV-01 | 12-03, 12-08 | SATISFIED | SC1 |
| REV-02 | 12-04, 12-08 | SATISFIED | SC1 |
| REV-03 | 12-05, 12-08 | SATISFIED | SC2 |
| REV-04 | 12-05, 12-07, 12-08, 12-09, 12-11, 12-13 | SATISFIED | SC2 (live timing pending, human item 8) |
| REV-05 | 12-06, 12-08, 12-10 | SATISFIED | SC3 (live dialog pending, human item 7) |

All seven phase IDs appear in PLAN frontmatter `requirements:` (grepped across 12-01..12-20; the gap plans 12-15..12-20 each declare `[UI-01]`) and in REQUIREMENTS.md (lines 88, 92-96, 106). No orphaned requirements.

**Bookkeeping, not a goal gap (orchestrator owns these edits):** REQUIREMENTS.md still shows all seven as `[ ]` / "Pending" (lines 88-96, 106, 169-181). ROADMAP.md line 33 shows Phase 12 unchecked and line 257 still says "6 gap-closure plans pending: 12-15 to 12-20". 12-UAT.md records G-12-12, G-12-21, G-12-22 and G-12-23 as `status: failed` and its header as `diagnosed`; set them resolved after the human checks below pass.

### Anti-Patterns Found

No `TBD`/`FIXME`/`XXX` in any file changed by 12-15..12-20 (grep). No stubs or hollow props in the new code.

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `main_window.py` | 1369-1374 | `show()/raise_()/activateWindow()` does not restore a minimized guide (WR-06, open) | Warning | F1/Help may appear to do nothing after the guide was minimized; add `setWindowState(... & ~WindowMinimized)` and a test. Human item 4 |
| `widgets/scan_progress.py` | 62-67, 90 | Source name used raw in button text and tooltip (WR-07, open) | Warning | `&` or `<..>` in a source folder name mis-renders; not reachable with the shipped sources |
| `tests/test_main_window.py` | 1517-1553 | Late Skip click test uses a fake scan that ignores the hook (WR-08, open) | Warning | Test is shallow; invariant is enforced in `_check_model_files` and covered by real `scan_all` tests |
| `widgets/import_dialog.py` | 677-689 | Parentless fallback guide is a second guide lifetime, unreachable from the app (IN-09) | Info | Drift risk only |

12-REVIEW.md (incremental, 12-15..12-20): 0 critical, 3 warnings (WR-06..08, all open in 12-REVIEW-DISPOSITION.md), info IN-07..IN-11. 12-SECURITY.md: 51/51 threats closed. 12-VALIDATION.md: 0 gaps. 12-UI-REVIEW.md: 17/24 (advisory).

### Prohibitions

- Test-tier, 12-15: start Cancel calls `reject()` only (`import_dialog.py:792`); the edit page, splitter and bottom row are untouched; `fit_window` stays the only sizing path. Tests pass. Resolved.
- Test-tier, 12-16: library_scanner and scan_cache stay Qt-free (`tests/test_layering.py` passes); a skip never drops a library or link (`test_skip_keeps_every_library_and_link`); the skip line is plain words (exact text asserted). Resolved.
- Test-tier, 12-17: the scan cannot be cancelled, only a source's 3D check skipped; the quiet post-install scan shows no dialog (`self._progress = None` when `show_progress` is false); `scan_progress.py` imports only PySide6 and the theme. Resolved.
- Test-tier, 12-18: the import window stays window-modal over the main window; no widget imports main_window; system file pickers stay application-modal by the owner-approved exclusion (recorded in 12-UAT.md Owner Decisions). Not a gap. Resolved.
- Test-tier, 12-19: persistence goes through `settings.py` helpers only (help_dialog.py imports `load_help_topic`/`save_help_topic`, no QSettings use); tests are isolated from the real settings.ini by the autouse fixture; import Help/F1 keep opening Importing Parts. Resolved.
- Test-tier, 12-20: the four main-window dialogs keep their blocking `exec()` and their text; pickers not converted. Resolved.
- Judgment-tier (12-08, carried): user-facing text must not use raw KiCad field names or code identifiers. New texts ("Skip WurthElektronik", "Loading Libraries", "its own window", "Required - type...") name no identifiers. Mechanical verdict: satisfied; plain-language judgment of the wording stays with the owner (non-authoritative).

### Human Verification Required

1. **G-12-12 / plan 12-15, real Windows display at 100% and 200%.** Start page compact with Browse zip..., Browse folder... and Cancel in one row, no empty band, no size jump when the Downloads line or the reading bar appears; edit page grows above the taskbar; Choose another package... shrinks; Cancel closes; `git -C Custom status --short` unchanged. Why human: real DPI, taskbar and fonts. The owner's 200% run of UAT 12 was still open.
2. **User Guide at 200% (UAT 13 remainder).** F1, 4.4 Importing Parts, Conflicts, then the import window Help and F1. Look and sharpness only.
3. **G-12-21 live Skip against the real Wurth library.** Skip WurthElektronik during "Checking 3D paths"; log line, trees, Generate Tables, restart note, Rescan, startup speed-up. Why human: real 60+ s timing and a real loading window.
4. **G-12-22 guide beside every window on real Windows, including a minimized guide (WR-06).** Main window, About, Restore Backup, KiCad questions, Loading Libraries, import window, content view, Check Atomic Parts; close order; minimize then F1.
5. **G-12-23 persistence in the real app across Close, Escape and a restart.** Selected, expanded node and section in view; import Help keeps opening Importing Parts and leaves the remembered place alone.
6. **Toolbar and Help in the real import window (UAT 10, G-12-9 appearance).** Folded into checks 1 and 4; note the guide now stays open when the import window closes (by owner decision).
7. **UAT 3 live KiCad-open dialog** from the main checkout. Why human: live KiCad process and a modal dialog.
8. **UAT 4 (owner skipped)**: Finishing strip with a real kicad-cli rebuild. Why human: real timing.

### Gaps Summary

No gaps. All five ROADMAP success criteria and the gap-closure contracts for G-12-12, G-12-21, G-12-22 and G-12-23 are present, substantive, wired and backed by named tests that were located and re-run here (168 + 134 + 44 passed, no skips), plus the orchestrator's full-suite run at 130c3b8 (9382 passed, 0 failed). Three open review warnings (WR-06..08) are recorded as advisory items, none contradicts a must-have: WR-06 (minimized guide not restored by F1) is the one most worth fixing before the owner's real-display pass because it touches the G-12-22 "usable beside every window" expectation on Windows. Status is `human_needed` because the owner's actual complaints in these gaps are about real-display look, window-system behaviour and real timing, which cannot be confirmed headless. After the human checks pass, mark G-12-12, G-12-21, G-12-22 and G-12-23 resolved in 12-UAT.md and flip REQUIREMENTS.md and ROADMAP.md.

---

_Verified: 2026-11-04_
_Verifier: Claude (gsd-verifier)_
