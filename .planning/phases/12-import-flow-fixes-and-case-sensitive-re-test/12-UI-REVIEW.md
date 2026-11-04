---
phase: "12"
slug: "import-flow-fixes-and-case-sensitive-re-test"
audited: "2026-11-04"
baseline: "abstract 6-pillar standards (no UI-SPEC.md); owner plain-language rule; UI-01 theme-token rule"
method: "static code review of the Qt widgets and the merged diff 5e0bb07..130c3b8 (plans 12-15 to 12-20); plan and summary cross-check; no offscreen render; no tests run; GUI not launched"
overall_score: 17
supersedes: "12-UI-REVIEW.md of 2026-11-04 (re-audit 2, 17/24, plans 12-01 to 12-14)"
---

# Phase 12 — UI Review (re-audit 3, gap-closure plans 12-15 to 12-20 included)

Audited 2026-11-04 by gsd-ui-auditor, covering plans 12-01 to 12-20. This pass adds the six gap-closure plans merged in commits 5e0bb07..130c3b8:

- **12-15 (G-12-12):** Cancel sits at the end of the Browse row on the start page (`_start_buttons`, `_start_cancel_btn`, import_dialog.py:784-794); the start window is 640 px wide and as tall as its content (`_START_WIDTH`, `_start_size`, import_dialog.py:83, 604-618); one constant-height slot holds the Downloads line and the reading box (`_offer_slot`, import_dialog.py:768-778); the start window refits when the issue list shows or clears.
- **12-16 (G-12-21):** a per-source skip of the 3D model path check in the scanner (`scan_all(skip=, checking=)`, `models_skipped_issue`, library_scanner.py:558-621); the saved scan keeps skipped sources and says so when reused (scan_cache.py:586-600, saved-scan format 2).
- **12-17 (G-12-21):** a Skip button on the Loading Libraries window (`ScanProgressDialog`, widgets/scan_progress.py, window-modal, Escape and the title-bar X are inert until the scan ends); skip-aware "No warnings in the checks that ran." line (main_window.py:646-650); Help Repository Scan text (help_dialog.py:126-136).
- **12-18 (G-12-22):** one shared, parentless, non-modal User Guide owned by the main window (`_guide_window`, `show_guide`, main_window.py:1349-1366); the import window receives it through `show_guide=` (import_dialog.py:449, 673-674); `centre_window` placement (import_dialog.py).
- **12-19 (G-12-23):** the guide remembers the owner's last place under `help/last_topic` (`load_help_topic` / `save_help_topic`, settings.py; `show_remembered`, help_dialog.py).
- **12-20 (G-12-22):** main-window dialogs are window-modal (`_question` at main_window.py:1136-1141, Restore Backup at 1301, About at 1381, KiCad-open box at 1177); Help says the User Guide is its own window (help_dialog.py:247, 460).

Overall **17/24**, unchanged from the 2026-11-04 re-audit 2. The six gap-closure plans are closed in code and their summaries report the tests passing, and they improve Experience Design, but no scored pillar moved. The reasons: the three top fixes from re-audit 2 are still open in the code (verified below), the new Skip copy repeats the jargon the owner rule forbids, and the owner's real 100% and 200% display checks for 12-13, 12-14 and 12-19 are still not done. No pillar scored 1 and no BLOCKER was found: a user can still finish an import, skip a slow 3D check, and reach the guide.

| Pillar | Score | Notes |
|--------|-------|-------|
| Copywriting | 2/4 | Raw file and table names still appear in Help, the new-library badge and status tips (Top Fix 1). The new Skip copy adds "3D model paths" in the button tooltip, the scan log line and the saved-scan note. The owner rule still applies to these. |
| Visuals | 3/4 | The Loading Libraries window is a clear, small dialog with one Skip button and a progress bar. The start page keeps Cancel at the end of the Browse row. The numbered three-level guide menu is clear. The 26-row menu is still tight at 200% (carried warning). |
| Color | 3/4 | New code reads tokens (`SURFACE`, `ACCENT`, `AMBER`). The shared `PRIMARY_BUTTON_QSS`, the library badge and the log panel still use literals (Top Fix 2). |
| Typography | 3/4 | Help headings keep `DISPLAY_PT`/`HEADING_PT`. `"Segoe UI"` is still named in the Help body (help_dialog.py:23) and `QFont("Consolas", 9)` still ignores `MONO_FAMILY`/`MONO_PT` (log_panel.py:31). |
| Spacing | 3/4 | New code uses `SP_*` tokens and computed window heights. Literal paddings remain in `theme.py:29`, `import_dialog.py:1671/1674` and `conflict_row.py:37`. |
| Experience Design | 3/4 | Real gains: Skip works per source and is never a silent click; Escape and the title-bar X are inert on the scan window until the scan ends; the guide stays usable beside the main-window dialogs; the guide reopens the owner's place. Held at 3 because the owner's 100%/200% checks (12-13 T3, 12-14 T3, 12-19 D4) are not done, UAT 3 is blocked, and the Help CSS still declares rules Qt does not paint (Top Fix 3). |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **Raw file and table names, and jargon, in user-facing text** — The owner rule is plain words. The guard test `tests/test_plain_names.py:14` still checks only `kicad-cli` and `kicad_common.json` (the file is unchanged in 12-15..12-20), so these pass unnoticed. Affected: the new-library badge `NEW_LIBRARY_BADGE = "new - creates .kicad_sym"` (`kicad_lib_manager/importer/form.py:83`); Help text naming `sym-lib-table`, `fp-lib-table`, `.pretty`, `.kicad_sym`, `.kicad_mod`, `.step` (`help_dialog.py` lines 53, 115, 116, 120, 206, 207, 255, 280, 397, 411); status tips and tooltips naming the table files (`main_window.py:265-273`). New in this pass: "3D model paths" in the Skip tooltip (`widgets/scan_progress.py:65`), the scan log line (`library_scanner.py:621-630`) and the saved-scan note (`scan_cache.py:600`). Fix: "a new library creates only its symbol file", "KiCad library tables", "the library table entries", "the 3D model files" (or "the 3D model check") in place of "3D model paths", and keep `.step` only where the file picker needs it. Extend `SEARCH_TOKENS` in `tests/test_plain_names.py` with `.kicad_sym`, `.kicad_mod`, `.pretty`, `sym-lib-table`, `fp-lib-table`, keeping the allowlist approach. User impact: a non-technical reader meets names and terms the app never asks them to know.

2. **Shared button, badge and log literals outside the token set** — `PRIMARY_BUTTON_QSS` (`theme.py:28-31`) hardcodes `#0078D4`, `white`, `padding: 8px 16px`, `#E1E1E1`, `#595959`; it is used by the install, generate, atomic-check and commit buttons. The badge at `import_dialog.py:1671` and `:1674` hardcodes `padding: 4px 8px`. `log_panel.py:12` hardcodes `"#000000"` and `log_panel.py:31` uses `QFont("Consolas", 9)`. `help_dialog.py:23` names `"Segoe UI", Arial`. Fix: build the QSS from `ACCENT`, `SURFACE_BASE`, `MUTED` and a disabled-fill token, with `SP_SM`/`SP_MD`; replace the badge padding with `SP_XS`/`SP_SM`; move `#000000` to a token; use `MONO_FAMILY`/`MONO_PT`; use the application font in the Help body. User impact: small, but the brand colour and the mono log font can drift from the token set without anyone noticing.

3. **Dead Help CSS and the owner's real-display checks are still open** — The CSS declares `h2 { border-bottom }` (help_dialog.py:25), `pre { border-left }` (line 30) and the `.hint` left bar (line 38). Qt rich text does not draw them, so the declarations are dead (noted in 12-02, accepted in UAT 2). Fix: drop them, or draw the accent rule with a `QFrame`. Then the owner runs the human checks from 12-13 Task 3, 12-14 Task 3 and 12-19 D4 at 100% and 200% scale (import window fit and Cancel placement, guide menu numbering and scroll, remembered place visible with the selected row and heading in view, Loading Libraries Skip button text fits). These are the only checks that confirm real taskbar, glyph and scale behaviour; the tests model 200% in logical pixels.

---

## Status of the earlier findings (2026-11-04 re-audit 2)

| Earlier item | Status 2026-11-04 (re-audit 3) | Evidence |
|--------------|-------------------------------|----------|
| Top Fix 1: raw names in Help, badge, tooltips | Open | help_dialog.py 53-411, form.py:83, main_window.py:265-273 unchanged; `tests/test_plain_names.py` unchanged in 5e0bb07..130c3b8 |
| Top Fix 2: button QSS and badge literals | Open | theme.py:29-31, import_dialog.py:1671/1674, log_panel.py:12/31, conflict_row.py:37 |
| Top Fix 3: Help rules not painted; owner visual check | Open (dead CSS present at lines 25, 30, 38); owner checks not done for 12-13, 12-14, 12-19 | help_dialog.py CSS block |
| Warning: result rows and log copy name the table file | Open | main_window.py:265-273, 454, 765 |
| Warning: help CSS body "Segoe UI" | Open | help_dialog.py:23 |
| Warning: import file filter lists raw extensions | Unchanged, acceptable | standard dialog filter |
| Warning: offscreen render shows no glyphs | Unchanged | no render in this pass |
| Warning: guard test narrow | Open | tests/test_plain_names.py:14 |
| G-12-5 (kicad-cli / kicad_common.json in user text) | Closed in user text | unchanged from re-audit 2 |
| G-12-10 (start Cancel, window too big) | Closed in code (12-13, extended by 12-15); owner check pending | import_dialog.py:784-794, 604-618 |
| G-12-11 (numbered menu with sections) | Closed in code; owner check pending | help_dialog.py outline and section code |
| G-12-12 (Cancel on Browse row, content-height start window, one offer slot) | Closed in code (12-15); owner check pending | import_dialog.py:768-794, `_start_size` |
| G-12-21 (skip 3D path check; Skip button; saved scan says so) | Closed in code (12-16, 12-17); owner check pending | library_scanner.py:558-621, scan_progress.py, scan_cache.py:586-600 |
| G-12-22 (one shared, non-modal guide; main-window dialogs window-modal) | Closed in code (12-18, 12-20) | main_window.py:1136-1141, 1349-1366, 1381; help_dialog.py:247 |
| G-12-23 (guide remembers the owner's place) | Closed in code (12-19); 100%/200% look not checked | settings.py `help/last_topic`; main_window.py `show_guide` |

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

- Passes: the start-page Cancel tooltip "Close without importing. Nothing is written." (import_dialog.py:791); the Help Repository Scan text on Skip is in plain sentences (help_dialog.py:129-136); the Skip button names the source in plain words ("Skip WurthElektronik"); the skipped-scan no-warnings line "No warnings in the checks that ran." (main_window.py:648) is plain; the guide title "User Guide" is plain.
- Gaps (new this pass):
  - "3D model paths" is repeated in the Skip tooltip (`scan_progress.py:65`), the scan log line (`library_scanner.py:621-630`) and the saved-scan note (`scan_cache.py:600`). It is more technical than "3D model files" and the owner rule asks for plain words.
  - The saved-scan note "Showing the saved scan from ..." uses the phrase "saved scan" (scan_cache.py:587). It is understandable, but the Help page and the log use the same term, so this is acceptable as long as the Help definition stays.
- Gaps (carried): the raw-name list in Top Fix 1 is unchanged; the guard test would not catch it.
- Score held at 2.

### Pillar 2: Visuals (3/4)

- Loading Libraries window: one progress bar, one label, one Skip button right-aligned, minimum width 420 (scan_progress.py:19, 26-43). The button is disabled after a click and reads "Skipping ..." until the next report. Clear focal point.
- Start page: the Browse row now ends with Cancel, so the primary Browse actions and Cancel sit on one line; the window is as tall as its content (`_start_size`).
- The User Guide: a three-level menu (groups, pages, sections) with numbers from the order; the page headings carry the same numbers; the menu follows the shown page; the guide is its own window beside the main window.
- Warning (carried): at 200% the guide is about 452 px tall and the menu has 26 rows, so the menu scrolls inside a short window. Re-check after the owner's 200% check.
- Warning (new, minor): the Skip button text "Skipping WurthElektronik..." stays until the next progress report. If a report is slow, the window shows "Skipping ..." for longer than the action takes. Not a blocker; a clearer state would be the label reverting when the check ends.

### Pillar 3: Color (3/4)

- Token use is good in the new code: `scan_progress.py` has no colour literals; the Help CSS reads `LINK`, `ACCENT`, `SURFACE`, `SURFACE_HEADER`, `BORDER`, `AMBER`, `AMBER_TINT` (help_dialog.py:21-39).
- Gaps (carried): `PRIMARY_BUTTON_QSS` (`theme.py:28-31`) literals on four or more buttons; the library badge uses tokens for colour but `padding: 4px 8px` literal (`import_dialog.py:1671, 1674`); `log_panel.py:12` `"#000000"`.
- The accent still appears on more than one primary action per view (install, generate, commit).

### Pillar 4: Typography (3/4)

- Help headings keep `DISPLAY_PT` and `HEADING_PT`; numbered headings render at the same size (12-14 Task 3 checks, passing in the 12-14 summary).
- Gaps (carried): the Help body names `"Segoe UI", Arial` (help_dialog.py:23) instead of the application font; `QFont("Consolas", 9)` (log_panel.py:31) ignores `MONO_FAMILY`/`MONO_PT`. Font weights in use are bold only, which is acceptable.

### Pillar 5: Spacing (3/4)

- New code uses the scale: `SP_MD` and `SP_SM` on the Loading Libraries window (scan_progress.py:46-47); `SP_MD`, `SP_SM`, `SP_XS` in Help; window sizes are named constants (`_START_WIDTH`, `_START_SIZE`, `_EDIT_SIZE`, `_FRAME_ALLOWANCE`, import_dialog.py:81-83).
- Literal values remain: `PRIMARY_BUTTON_QSS` `padding: 8px 16px` (`theme.py:29`); badge `padding: 4px 8px` (`import_dialog.py:1671, 1674`); conflict buttons `padding: 4px` (`conflict_row.py:37`); the start Browse row uses a literal `setSpacing(8)` (import_dialog.py:786), which should be `SP_SM`.
- The issue-list minimum (`_ISSUE_LIST_MIN_HEIGHT`, 112 px) is a documented fit for a Full HD 200% screen; acceptable.

### Pillar 6: Experience Design (3/4)

- Skip: per-source, enabled only during that source's 3D path check (scan_progress.py:70-91); the scan result, not the click, writes the one log line, so the log, the button and the saved scan agree (12-17 decision). The saved scan is marked, and the next start says so until a Rescan (scan_cache.py:586-600).
- Loading window: Escape and the title-bar X do nothing until `finish()` (scan_progress.py:96-100); the scan cannot be cancelled, which is the intended rule.
- Guide: one shared window, parentless, so window-modal dialogs do not block it (main_window.py:1349-1355); centred over the main window and kept inside the free area (`centre_window`); reopens the owner's last place, and only the owner's own moves are saved (quiet counter, 12-19); Close, Escape and a deleted parent do not lose the place.
- Main-window dialogs are window-modal, so the guide stays usable beside them (`_question`, Restore Backup, About, KiCad-open box).
- Start Cancel calls `reject()`, so the D-06 wait and the D-10 refusals still apply.
- Gaps:
  - The owner's 100% and 200% checks for 12-13 T3, 12-14 T3 and 12-19 D4 are not done. The 12-19 summary records D4 with no automated or human verification entry.
  - UAT 3 (KiCad-open question) is blocked by the worktree guard; re-test from the main checkout. This pass did not re-read the whole 12-UAT.md; only its last section was checked.
  - Help text still uses raw names (Pillar 1).
  - Tests for the new behaviour are reported as passing in the summaries; they were not re-run in this pass (no tests were run, per the audit constraints).
- Registry audit: not applicable (no shadcn `components.json` in this project).

---

## Comparison with the 2026-11-04 re-audit 2

| Item | Re-audit 2 (2026-11-04) | Re-audit 3 (2026-11-04) |
|------|-------------------------|-------------------------|
| Overall | 17/24 | 17/24 |
| Start page Cancel | at the bottom right | at the end of the Browse row (12-15); tooltip plain |
| Start window height | fixed-size start window, fitted to the screen | as tall as its content, refit on issue change (12-15) |
| Scan 3D path check | always runs; no way to stop it | Skip button per source; skipped scan saved and labelled (12-16, 12-17) |
| Loading window | Qt progress dialog | own dialog; Escape and X inert until the scan ends (12-17) |
| Guide and dialogs | guide blocked by window-modal dialogs | one shared guide beside window-modal dialogs (12-18, 12-20) |
| Guide place | always the first page | reopens the owner's last place (12-19) |
| Raw names | unchanged (help, badge, tooltips) | unchanged; "3D model paths" added in new Skip copy |
| Button QSS literals | flagged | unchanged |
| Help dead CSS | Top Fix 3 | unchanged (lines 25, 30, 38) |

---

## Files Audited

- `.planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/`: 12-15-SUMMARY.md to 12-20-SUMMARY.md, 12-15-PLAN.md to 12-20-PLAN.md, 12-CONTEXT.md, 12-UAT.md (last section), previous 12-UI-REVIEW.md
- `git log --oneline 5e0bb07..130c3b8` and `git diff 5e0bb07..130c3b8 -- kicad_lib_manager/` (read-only), plus targeted greps for literals and raw names in the new code
- `kicad_lib_manager/widgets/scan_progress.py` (full: Skip button, Escape/X handling, idle and skipping states)
- `kicad_lib_manager/widgets/import_dialog.py` (81-83, 449-462, 570, 604-618, 673-674, 768-794, 1671-1674)
- `kicad_lib_manager/widgets/help_dialog.py` (21-38 CSS, 53-411 raw names, 126-136 Skip text, 247, 460, 580 `HelpDialog`)
- `kicad_lib_manager/widgets/theme.py` (full file), `log_panel.py` (12, 31), `conflict_row.py` (37)
- `kicad_lib_manager/library_scanner.py` (558-630 skip and skipped-issue code)
- `kicad_lib_manager/scan_cache.py` (586-600 reuse note)
- `kicad_lib_manager/main_window.py` (265-273, 454, 496-501, 646-650, 765, 1037-1045, 1136-1141, 1177, 1301, 1349-1381)
- `kicad_lib_manager/importer/form.py` (83)
- `kicad_lib_manager/settings.py` (help/last_topic, from the 12-19 summary; not re-read in full)
- `tests/test_plain_names.py` (line 14 guard list, unchanged)

Screenshots: not captured. The app is a desktop GUI with no dev server, so no `.planning/ui-reviews` captures and no gitignore step were needed. No offscreen render was done; layout claims come from the plans and summaries, and the owner's human checks remain the only proof of real glyph and scale behaviour.
Interaction captures: off (`interaction_capture: false`).
