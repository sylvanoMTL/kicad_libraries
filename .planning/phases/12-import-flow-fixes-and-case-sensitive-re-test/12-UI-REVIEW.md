---
phase: "12"
slug: "import-flow-fixes-and-case-sensitive-re-test"
audited: "2026-11-04"
baseline: "abstract 6-pillar standards (no UI-SPEC.md); owner plain-language rule; UI-01 theme-token rule"
method: "static code review of the Qt widgets and their merged diff (5e0bb07 range, plans 12-13 and 12-14); no offscreen render in this pass; no tests run"
overall_score: 17
supersedes: "12-UI-REVIEW.md of 2026-11-03 (17/24, plans 12-01 to 12-12)"
---

# Phase 12 — UI Review (re-audit 2, gap-closure plans included)

Audited 2026-11-04 by gsd-ui-auditor, covering plans 12-01 to 12-14. This pass adds the two gap-closure plans merged in commits 81b7065 to 5e0bb07:

- **12-13 (G-12-10):** Cancel on the import start page (`_start_cancel_btn`, import_dialog.py:772-775); the import window is fitted to the free screen area (`screen_area`, `_fit_size`, `_place_inside`, `fit_window`, import_dialog.py:143-190); the start page opens at 640x440, the edit page grows to 1100x720 bounded by the screen, and `_show_page` is the single page switch.
- **12-14 (G-12-11):** the User Guide menu is numbered and lists each page's `<h3>` sections under the page (`help_outline`, `page_sections`, `render_page`, `section_anchor`); clicking a section scrolls to its heading; the menu follows the shown page; the guide window is fitted to the screen in `HelpDialog.showEvent`.

Overall **17/24**, unchanged from 2026-11-03. Both gap-closure items are closed in code and covered by tests the summaries report as passing. The score does not rise because the owner's real 100% and 200% checks for 12-13 and 12-14 have not been done, the three top fixes from the previous review are still open, and two UAT items remain open. No pillar scored 1, and no BLOCKER was found: no defect in the merged code stops a user from finishing an import.

| Pillar | Score | Notes |
|--------|-------|-------|
| Copywriting | 2/4 | Raw file and table names still appear in Help, the new-library badge and status tooltips (Top Fix 1). The new Cancel, Start and menu text is plain. The `kicad-cli` / `kicad_common.json` strings are fixed in user text, as G-12-5 asked. |
| Visuals | 3/4 | The start page is small with Cancel at the bottom right; the edit page keeps Install Part and Cancel; the numbered three-level menu gives a clear hierarchy. The 26-row menu scrolls inside the 452 px window at 200% (warning). |
| Color | 3/4 | Help and the new code read theme tokens. `PRIMARY_BUTTON_QSS` (`theme.py:28-31`) and the badge still use literals (Top Fix 2). |
| Typography | 3/4 | Help headings keep their sizes; numbered headings render at the same size and colour. `"Segoe UI"` is still named in the Help CSS (help_dialog.py:22) and Consolas 9 is hardcoded in the log panel (log_panel.py:31). |
| Spacing | 3/4 | The new start bottom row and the window sizes use named constants. Literal paddings remain in `theme.py:29`, import_dialog.py:1625/1628 and conflict_row.py:37. |
| Experience Design | 3/4 | The start Cancel calls `reject()`, so the D-06 wait and the D-10 refusals still apply. The window fits 100% and 200% in tests. The guide fits the screen and keeps a Close button. Owner human checks for 12-13 and 12-14 are pending, and UAT 3 is blocked (worktree guard). |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **Raw file and table names in user-facing text** — The owner rule is plain words. The guard test `tests/test_plain_names.py:14` checks only `kicad-cli` and `kicad_common.json`, so these pass unnoticed. Affected: the new-library badge `NEW_LIBRARY_BADGE = "new - creates .kicad_sym"` (`kicad_lib_manager/importer/form.py:83`); Help text naming `sym-lib-table`, `fp-lib-table`, `.pretty`, `.kicad_sym`, `.kicad_mod`, `.step` (`help_dialog.py` lines 52, 114, 115, 119, 195, 196, 241, 266, 383, 397); status tooltips and status tips naming the table files (`main_window.py:247-255`). Fix: "a new library creates only its symbol file", "KiCad library tables", "the library table entries", "the 3D model file (.step)" kept only where the file picker needs it. Extend `SEARCH_TOKENS` in `tests/test_plain_names.py` with `.kicad_sym`, `.kicad_mod`, `.pretty`, `sym-lib-table`, `fp-lib-table`, keeping the allowlist approach. User impact: a non-technical reader meets names the app never asks them to find.

2. **Shared button, badge and log literals outside the token set** — `PRIMARY_BUTTON_QSS` (`theme.py:28-31`) hardcodes `#0078D4`, `white`, `padding: 8px 16px`, `#E1E1E1`, `#595959`. It is used by the install, generate, atomic-check and commit buttons (`import_dialog.py:938`, `main_window.py:358`, `atomic_check_dialog.py:104/326`, `commit_panel.py:254`). The badge at `import_dialog.py:1625/1628` hardcodes `padding: 4px 8px`. Fix: build the QSS from `ACCENT`, `SURFACE_BASE`, `MUTED`, a disabled-fill token and `SP_SM`/`SP_MD`; replace the badge padding with `SP_XS`/`SP_SM`; replace `log_panel.py:12` `#000000` with a token and move `QFont("Consolas", 9)` (log_panel.py:31) to `MONO_FAMILY`/`MONO_PT`; replace `"Segoe UI"` in the Help body (help_dialog.py:22) with the application font.

3. **Help rules Qt does not paint, and the owner's real-display checks are still open** — The CSS declares `h2 { border-bottom }` (help_dialog.py:24), `pre { border-left }` (line 29) and the `.hint` left bar (line 37). Qt rich text does not draw them (noted in 12-02, and the owner accepted that in UAT 2), so the declarations are dead. Fix: drop them, or draw the accent rule with a `QFrame`. Then the owner runs the human checks from 12-13 Task 3 and 12-14 Task 3 at 100% and 200% scale (import window fit, Cancel placement, guide menu numbering, Conflicts scroll, guide on screen). These are the only checks that confirm the real taskbar, glyph and scale behaviour; the tests model 200% in logical pixels.

---

## Status of the earlier findings (2026-11-03 review)

| Earlier item | Status 2026-11-04 | Evidence |
|--------------|-------------------|----------|
| Top Fix 1: raw names in Help, badge, tooltips | Open | help_dialog.py 52-397, form.py:83, main_window.py:247-255 still contain them; guard list unchanged |
| Top Fix 2: button QSS and badge literals | Open | theme.py:28-31, import_dialog.py:1625/1628, log_panel.py:12/31 |
| Top Fix 3: Help rules not painted; owner visual check | Open (dead CSS still present); owner visual check partly done | CSS lines 24, 29, 37; UAT 2 passed with the note that rules are not drawn |
| Warning: result rows and log copy name the table file | Open | main_window.py result and log lines not changed in 12-13/12-14 |
| Warning: help CSS body "Segoe UI" | Open | help_dialog.py:22 |
| Warning: import file filter lists raw extensions | Unchanged, acceptable | standard dialog filter |
| Warning: offscreen render shows no glyphs | Unchanged | no render in this pass either |
| Warning: guard test narrow | Open | tests/test_plain_names.py:14 |
| G-12-5 (kicad-cli / kicad_common.json in user text) | Closed in user text | the only remaining hits are docstrings and comments in importer/*.py and import_dialog.py |
| G-12-10 (start Cancel, window too big) | Closed in code; owner check pending | start Cancel import_dialog.py:772-775; fit functions 143-190; `_START_SIZE` and `_EDIT_SIZE` at 81-82; no `setMinimumSize(900` left |
| G-12-11 (numbered menu with sections) | Closed in code; owner check pending | `help_outline`, `page_sections`, `render_page`, `section_anchor`; `_sync_expansion`; `_on_item_clicked` |

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

- Passes: the start-page Cancel tooltip "Close without importing. Nothing is written." (import_dialog.py:773); the Start section sentences about Cancel, the small window and the screen fit (help_dialog.py, Importing Parts, Start); the section menu labels ("4.4.7 Conflicts") are plain; `Choose another package...` and `Help` labels are plain.
- Gaps: the raw-name list in Top Fix 1 is unchanged. The new Help sentences do not add raw names. The G-12-5 strings are gone from user text, which is the part the guard test does not check.
- Score held at 2: the same copy gaps the previous review found are still present, and the guard test would not catch them.

### Pillar 2: Visuals (3/4)

- The start page: heading, body, offer row, Browse buttons and a bottom row with Cancel at the bottom right (import_dialog.py:769-776). The page opens at 640x440; the 20-issue state still fits (layout minimum 416x330, per 12-13).
- The edit page keeps its bottom row with Install Part and Cancel (UAT 6 closed in 12-09).
- The User Guide: a three-level menu (groups, pages, sections) with numbers from the order; the page headings carry the same numbers; the menu follows the shown page. Hierarchy is clear.
- Warning: at 200% the guide is 452 px tall (960x492 logical area less the taskbar and frame). The menu has 26 rows, so the menu scrolls inside a short window. It is usable, but the Close button and the menu are both tight. Consider a smaller row spacing, or let the TOC use a narrower font, after the owner's 200% check.
- Focal point: the start page still has no visual emphasis on Browse zip... versus the other buttons. The render cannot confirm weight.

### Pillar 3: Color (3/4)

- Token use is good in the new code: the Help CSS reads `LINK`, `ACCENT`, `SURFACE`, `SURFACE_HEADER`, `BORDER`, `AMBER`, `AMBER_TINT` (help_dialog.py:21-39); the new Cancel and menu use the default button look.
- Gaps: `PRIMARY_BUTTON_QSS` literals (`theme.py:28-31`) used on four or more buttons; badge colours from tokens but `border: 1px` and `padding: 4px 8px` literal (`import_dialog.py:1625, 1628`); `log_panel.py:12` `"#000000"`. The accent appears on more than one primary action per view (install and generate and commit).

### Pillar 4: Typography (3/4)

- Help headings keep `DISPLAY_PT` and `HEADING_PT`; the numbered headings render at the same size (12-14 Task 3 checks, passing in the 12-14 summary).
- Gaps: the body names `"Segoe UI", Arial` (help_dialog.py:22) instead of the application font; `QFont("Consolas", 9)` (log_panel.py:31) ignores `MONO_FAMILY`/`MONO_PT`. Font weights in use are bold only, which is acceptable.

### Pillar 5: Spacing (3/4)

- New code uses the scale: `SP_MD`, `SP_SM`, `SP_XS` in Help; window sizes are named constants (`_START_SIZE`, `_EDIT_SIZE`, `_FRAME_ALLOWANCE`, import_dialog.py:81-83).
- Literal values remain: `PRIMARY_BUTTON_QSS` `padding: 8px 16px` (`theme.py:29`); badge `padding: 4px 8px` (`import_dialog.py:1625, 1628`); conflict buttons `padding: 4px` (`conflict_row.py:37`); the start bottom row and the frame allowance use literal 8 and `QSize(16, 40)`, which is acceptable as a documented frame estimate.

### Pillar 6: Experience Design (3/4)

- Start Cancel: `clicked` connects to `self.reject` (import_dialog.py:774), so the D-06 Finishing wait and the D-10 refusal during install and commit apply without new close logic.
- Window fit: `fit_window` bounds the window by the free area less the frame allowance, never below the layout minimum, and moves a visible window inside the area. Tests model 100%, 200% and the owner's 1280x672 screen; they are not run in this pass.
- Grow and shrink: `_show_page` is the only page switch; the start page shrinks, the edit page returns to the remembered size, the result page keeps its size.
- Guide: `HelpDialog.showEvent` calls `fit_window`; section keys open the section; re-click scrolls back; the fold waits for the event loop so a mouse click keeps its selection (a deviation the 12-14 summary records, with a regression test).
- Gaps:
  - UAT 3 (KiCad-open question) is blocked: the worktree guard refuses before the dialog; re-test from the main checkout.
  - UAT 4 (real kicad-cli wait) is skipped by the owner.
  - The 12-13 and 12-14 human checks at real 100% and 200% scale are not done (the executors could not change display scale).
  - Help text still uses raw names (Pillar 1).
- Registry audit: not applicable (no shadcn `components.json` in this project).

---

## Comparison with the 2026-11-03 review

| Item | 2026-11-03 | 2026-11-04 |
|------|-----------|-----------|
| Overall | 17/24 | 17/24 |
| Start page Cancel | absent (UAT 10 failed) | present, closes through `reject()`, tested |
| Window size and screen fit | fixed 1100x720, minimum 900x600 | bounded by the free area; start page opens small; guide fitted |
| Menu sections and numbers | absent (UAT 11 failed) | three-level numbered menu derived from page headings |
| Raw names | narrowed to table and extension names | unchanged (help, badge, tooltips) |
| Button QSS literals | flagged | unchanged |
| Help dead CSS | Top Fix 3 | unchanged |

---

## Files Audited

- `.planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/`: 12-13-SUMMARY.md, 12-14-SUMMARY.md, 12-13-PLAN.md, 12-14-PLAN.md, 12-CONTEXT.md, 12-UAT.md, previous 12-UI-REVIEW.md
- `git log --oneline 81b7065~1..5e0bb07` and `git diff 81b7065~1 5e0bb07 -- kicad_lib_manager/` (read-only), plus the added-line scan for literals and raw names
- `kicad_lib_manager/widgets/import_dialog.py` (81-83, 143-190, 540-620, 745-790, 938, 1334-1340, 1625-1628)
- `kicad_lib_manager/widgets/help_dialog.py` (1-39 CSS and tokens; 52-397 raw names; 455-670 outline, render, HelpDialog)
- `kicad_lib_manager/widgets/theme.py` (full file), `conflict_row.py` (28-37), `log_panel.py` (12, 31), `atomic_check_dialog.py` (104, 326), `commit_panel.py` (254)
- `kicad_lib_manager/importer/form.py` (83), `kicad_lib_manager/main_window.py` (247-255, 358)
- `tests/test_plain_names.py` (line 14 guard list)

Screenshots: not captured. The app is a desktop GUI with no dev server, so no `.planning/ui-reviews` captures and no gitignore step were needed. No offscreen render was done in this pass; layout claims come from the plans and summaries, and the owner's human checks remain the only proof of real glyph and scale behaviour.
Interaction captures: off (`interaction_capture: false`).
