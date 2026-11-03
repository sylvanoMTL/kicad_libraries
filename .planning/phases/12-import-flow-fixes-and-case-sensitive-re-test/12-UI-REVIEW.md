---
phase: "12"
slug: "import-flow-fixes-and-case-sensitive-re-test"
audited: "2026-11-03"
baseline: "abstract 6-pillar standards (no UI-SPEC.md); owner plain-language rule; UI-01 theme-token rule"
method: "static code review of the Qt widgets, plus one offscreen render of the import window start page and the Help window (no glyph font in the offscreen platform, so text shows as boxes; layout only)"
overall_score: 17
supersedes: "12-UI-REVIEW.md of 2026-11-02 (17/24, pre gap plan 12-12)"
---

# Phase 12 — UI Review (re-audit)

Audited 2026-11-03 by gsd-ui-auditor, covering plans 12-01 to 12-12, including the 12-12 toolbar Help (G-12-9) and the Help text changes. Overall **17/24**, unchanged from the previous review. No pillar scored 1 and no BLOCKER was found. The toolbar work (12-12) and the Finishing / KiCad-open / Cancel work moved behaviour forward, but the same copy and token gaps remain, so the score does not rise.

| Pillar | Score | Notes |
|--------|-------|-------|
| Copywriting | 2/4 | Raw file and table names still appear in Help, a badge and status tooltips (Top Fix 1). The new toolbar, Cancel and Finishing text is plain. |
| Visuals | 3/4 | Toolbar sits above the page stack with icon and "Help" beside it, and the layout is clean. Glyphs could not be checked in the offscreen render. |
| Color | 3/4 | Theme tokens are used in the new Help CSS, conflict rows and the Finishing strip. `PRIMARY_BUTTON_QSS` (theme.py:28-31) still uses literal colours. |
| Typography | 3/4 | Help uses the pt scale. The body still names the font family "Segoe UI" (help_dialog.py:18), and the log panel hardcodes Consolas 9 (log_panel.py:31). |
| Spacing | 3/4 | Help uses `SP_*`. Literal paddings remain in theme.py:30, import_dialog.py:1526/1529 and conflict_row.py:36-37. |
| Experience Design | 3/4 | Help is reachable from every page and state (tests), Cancel and Finishing exist, and the KiCad-open box has three answers. Real kicad-cli timing and the real KiCad-open box are not yet seen by the owner. |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **Raw file and table names in user-facing text** — The owner rule is plain words, and the guard test only catches `kicad-cli` and `kicad_common.json`, so these pass unnoticed. Affected: the new-library badge "new - creates .kicad_sym" (`kicad_lib_manager/importer/form.py:83`); Help text naming `sym-lib-table`, `fp-lib-table`, `.kicad_sym`, `.kicad_mod`, `.pretty`, `.step` (`help_dialog.py` lines 48, 110, 111, 115, 191, 192, 233, 258, 375, 389); status tooltips and status tips naming the table files (`main_window.py:247-255`). Fix: rewrite as "a new library creates only its symbol file", "KiCad library tables", and "the library table entries". Extend `tests/test_plain_names.py` `SEARCH_TOKENS` with `.kicad_sym`, `.kicad_mod`, `sym-lib-table`, `fp-lib-table`, `.pretty` (keeping the allowlist approach). The user impact is a non-technical reader meeting names the app never asks them to find.

2. **Shared button and badge literals outside the token set** — `PRIMARY_BUTTON_QSS` (`theme.py:28-31`) hardcodes `#0078D4`, `white`, `padding: 8px 16px`, `#E1E1E1`, `#595959`. It is used by the install, generate, atomic-check and commit buttons (`import_dialog.py:840`, `main_window.py:358`, `atomic_check_dialog.py:104/326`, `commit_panel.py:254`). The badge at `import_dialog.py:1526/1529` hardcodes `padding: 4px 8px`. Fix: build the QSS from `ACCENT`, `SURFACE_BASE`, `MUTED`, a new disabled-fill token and `SP_SM`/`SP_MD`. Replace the badge padding with `SP_XS`/`SP_SM`. Replace `log_panel.py:12` `#000000` with a token and move Consolas 9 to `MONO_FAMILY`/`MONO_PT`.

3. **Help rules that Qt does not paint, and the owner's visual check is still open** — `h2 { border-bottom }` (help_dialog.py:20), `pre { border-left }` (line 25) and the `.hint` left bar (line 33) are declared but not drawn by Qt rich text (noted in 12-02). The stated design intent is therefore not delivered. Fix: either drop those declarations so the CSS matches the render, or draw the accent rule with a `QFrame`. Then have the owner check the toolbar, Finishing strip and KiCad-open box in a running window (UAT items already open in 12-02, 12-05, 12-06, 12-12). This is the only check that can confirm glyph-level look.

---

## Warnings (non-blocking)

- Result-row and log copy still names the table file (Result rows "Not added to <file>", "Updated: X in <file> now points at ..."; `main_window.py:436, 737, 891`). CONTEXT "Specific Ideas" omits the file name.
- The help CSS body still hardcodes `"Segoe UI", Arial` (help_dialog.py:18); the UI-01 rule covers colours and sizes, so this is a token gap rather than a breach.
- The import-dialog file filter reads `3D models (*.step *.stp *.wrl *.zip)` (import_dialog.py:2139). This is a standard dialog filter, so it is acceptable, but it is a raw extension list.
- The offscreen render proves layout only: text shows as empty glyph boxes because the test platform has no font. Typography and visual weight are therefore unverified by render.
- The guard test `tests/test_plain_names.py` passed on the merged package (per 12-11), so the current gap is the guard's narrow token list, not a failing test.

---

## Detailed Findings

### Pillar 1: Copywriting (2/4)

- Passes: the new toolbar text "Help" with tooltip "Open the User Guide on the Importing Parts page (F1). This window stays open." (`import_dialog.py:89`); Cancel tooltip; "Finishing the preview..." and the slow note "The KiCad command-line tool is slow to respond (it gives up after 60 s)" (`import_dialog.py:116-119`); "Choose another package..." (`import_dialog.py:87`); required-field hints "Required - enter a Datasheet link" etc. (`_REQUIRED_HINTS`, `import_dialog.py:95`).
- Gaps: badge `NEW_LIBRARY_BADGE = "new - creates .kicad_sym"` (`importer/form.py:83`); Help text listed in Top Fix 1; main window tooltips `main_window.py:247, 248, 254, 255`. The 12-10 and 12-11 changes removed `kicad-cli` and `kicad_common.json` from user text, which is the part of the rule the guard tests.

### Pillar 2: Visuals (3/4)

- Toolbar construction is clean (`import_dialog.py:528-546`): a `QToolBar` with `ToolButtonTextBesideIcon`, non-movable, no stylesheet, the standard help icon, and "Help" beside it. It sits above `self._stack` (`import_dialog.py:506`), so every page shares it. The offscreen render confirms it appears at the top left with the icon and label on one line.
- Focal point: the start page shows a heading, a note and two buttons with no visible emphasis on the primary action. The render cannot confirm weight because glyphs are missing.
- Help window: a two-level TOC on the left, a body on the right, one button at the bottom right. The render shows a clear structure.

### Pillar 3: Color (3/4)

- Token use is good in the new code: conflict rows and the Help stylesheet read from `theme.py`; `SURFACE_BASE` is defined (`theme.py:15`); the Finishing strip uses `SURFACE` and `BORDER` (`import_dialog.py:567`).
- Gaps: `PRIMARY_BUTTON_QSS` literals (`theme.py:28-31`); `log_panel.py:12` `"#000000"`; the badge uses tokens for colour but a literal border width and padding. The primary-button style is applied to four different buttons across dialogs, so the accent appears on more than one action per view.

### Pillar 4: Typography (3/4)

- Help uses `DISPLAY_PT` (h2), `HEADING_PT` (h3) and `MONO_PT` (code), with `MONO_FAMILY` (`help_dialog.py:21-26`). Import dialog headings use `HEADING_PT` and `DISPLAY_PT` (`import_dialog.py:607, 874`).
- Gaps: body font family "Segoe UI" (`help_dialog.py:18`); `QFont("Consolas", 9)` in `log_panel.py:31` ignores the tokens. Font weights in use are bold only, which is acceptable.

### Pillar 5: Spacing (3/4)

- Help and the toolbar use `SP_*`. Conflict-row buttons use `_BUTTON_PAD` with `padding: 4px` (`conflict_row.py:36-37`).
- Literal values: `PRIMARY_BUTTON_QSS` `padding: 8px 16px` (`theme.py:29`); badge `padding: 4px 8px` (`import_dialog.py:1526, 1529`); Help `padding: 0px` on code (`help_dialog.py:23`), acceptable because it is zero. Helper `SP_XS` = 4 matches the literal, so the fix is mechanical.

### Pillar 6: Experience Design (3/4)

- Covered by tests: Help is reachable from start, edit and result pages and during rebuild, Finishing, install and commit (`test_import_dialog.py` per 12-12); the Help window is non-modal and the import window stays usable; Cancel closes without installing; Install is disabled during a one-off build (D-08); the close during Finishing waits and closes by itself (12-07); a blank Destination writes nothing (12-04); the KiCad-open dialog offers Retry, Change anyway, Not now (12-06).
- Gaps: the real kicad-cli wait (12-08 check 1-3) and the real KiCad-open box (12-06) are owner checks that have not been done. The Help text has raw file names (Pillar 1), which affects comprehension for a new user even though the flow works.
- Registry audit: not applicable (no shadcn components.json in this project).

---

## Comparison with the 2026-11-02 review

| Item | 2026-11-02 | 2026-11-03 |
|------|-----------|-----------|
| Overall | 17/24 | 17/24 |
| Help toolbar / F1 | absent (UAT 9(d) failed) | present, tested on every page and state |
| Raw names | flagged in help_dialog, importer/form, main_window, library_scanner, table_generator | narrowed: `kicad-cli` / `kicad_common.json` removed (guard test); `.kicad_sym`, table file names remain |
| Button QSS literals | flagged | still present (`theme.py:28-31`) |
| Help dead CSS | not flagged | new Top Fix 3 (border rules not rendered by Qt) |

---

## Files Audited

- `.planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/` summaries 12-01 to 12-12, plans 12-12 (and skimmed 12-01 to 12-11), 12-CONTEXT.md, previous 12-UI-REVIEW.md
- `kicad_lib_manager/widgets/import_dialog.py` (toolbar 506, 528-546; text constants 85-120; badge 1515-1530; button QSS 840; strip 567)
- `kicad_lib_manager/widgets/help_dialog.py` (CSS 16-34; HELP_PAGES 44-260; raw names 48-389)
- `kicad_lib_manager/widgets/theme.py` (full file)
- `kicad_lib_manager/widgets/conflict_row.py` (28-37)
- `kicad_lib_manager/widgets/log_panel.py` (12, 31)
- `kicad_lib_manager/widgets/atomic_check_dialog.py`, `commit_panel.py` (PRIMARY_BUTTON_QSS users)
- `kicad_lib_manager/importer/form.py` (83)
- `kicad_lib_manager/main_window.py` (247-255, 358, 436, 737, 891)
- `tests/test_plain_names.py` (guard token list)
- Offscreen render (scratchpad, not in the repo; no dev server, so no `.planning/ui-reviews` captures and no gitignore step): `import_start.png`, `help_importing.png`

Screenshots: not captured as dev-server captures (desktop app). Offscreen render used for layout only.
Interaction captures: off (`interaction_capture: false`).
