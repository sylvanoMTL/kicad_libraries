# Phase 06 - UI Review

**Audited:** 2026-10-23
**Baseline:** abstract 6-pillar standards (no 06-UI-SPEC.md; contract is 06-CONTEXT.md D-01..D-20)
**Screenshots:** not captured (PySide6 desktop app, no dev server; code-only audit)
**Interaction captures:** off (workflow.ui_interaction_capture is false)
**Human evidence cited:** 06-UAT.md, both tests pass (real-repo commit from the Result view; close without commit logs the D-02 line once)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Outcome copy is specific; the button reads "Committed" in the `failed` state (`commit_panel.py:462`) |
| 2. Visuals | 3/4 | Clear headings, amber strip and ⚠ glyph; the Commit button does not use `theme.PRIMARY_BUTTON_QSS` |
| 3. Color | 3/4 | No hard-coded hex; amber is consistent; `ERROR_TINT` / `SUCCESS_TINT` are not used for outcomes |
| 4. Typography | 3/4 | Sizes from theme; `MONO_FAMILY = "Consolas"` has no non-Windows fallback; fit at 900x600 not measured |
| 5. Spacing | 3/4 | `SP_*` scale used for layout; magic numbers at `commit_panel.py:205, 259-260` |
| 6. Experience Design | 2/4 | Good state machine and disabled reasons; open review warnings WR-01, WR-03, WR-05 break recovery paths |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **WR-05: the panel is stuck after a refusal.** `show_outcome()` returns to `ready` with the old probe (`commit_panel.py:347-350`), and the dialog keeps passing `expected_branch` from the stale `_commit_probe` (`import_dialog.py:2217-2236`). If the Custom branch changes, every click fails the same way until the dialog is reopened. Fix: re-run `_start_probe()` after every outcome that did not commit, while keeping the refusal text visible.
2. **WR-01: a timeout is reported as "nothing committed" without checking HEAD** (`commit_step.py:360-370, 467-471`). A slow post-commit hook or GPG step can time out after HEAD has already moved. The user is told nothing was committed, the parent bump is skipped, and a retry fails. Fix: record HEAD before `commit_paths` and compare it afterwards.
3. **WR-03: the "finish it by hand" command is mis-quoted on Windows** (`commit_step.py:506-508`). The `\"` escape is POSIX-only, so the D-03 recovery command breaks in PowerShell or cmd when the subject contains `"`, `$` or a backtick. Fix: quote per platform, or pass the message through a file (`-F`).

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

- Strengths: specific outcome copy, for example "Not pushed — Custom is N commits ahead of origin/main (as last fetched)" (`commit_step.py:299`), "Commit unavailable: <reason>" (`commit_panel.py:32`), "Enter a commit message" (`commit_panel.py:186`), and a clear dirty-file hint (`commit_panel.py:33-36`).
- `commit_panel.py:462` maps the `failed` state to "Committed". In that state Custom was committed but the parent step failed, so the label reads as full success. Use "Committed (parent failed)", or keep "Commit" and let the outcome line explain.
- Minor: D-07 writes "Committing in Custom…" with a Unicode ellipsis. The code uses ASCII "..." (`commit_step.py:456, 501`; `commit_panel.py:318`). The code is consistent but differs from the contract text.

### Pillar 2: Visuals (3/4)

- Strengths: `_heading` sections, an amber ⚠ for dirty files (`commit_panel.py:418`), and an amber alert strip for blocked states (`commit_panel.py:430-452`).
- The Commit button (`commit_panel.py:189-194`) is a plain `QPushButton`. `theme.PRIMARY_BUTTON_QSS` is applied only to Generate (`main_window.py:226`), and Install Part (`import_dialog.py:609`) is also unstyled. The phase's most consequential click has no visual emphasis.

### Pillar 3: Color (3/4)

- Strengths: no hex literals in `commit_panel.py` or `import_result.py`. All colours come from `theme.py`, and amber is used consistently for warnings, "not main" and the parent reason.
- Error and success outcomes are plain coloured text, while amber alerts get a tinted strip. `theme.ERROR_TINT` and `theme.SUCCESS_TINT` are unused here.

### Pillar 4: Typography (3/4)

- Strengths: `HEADING_PT`, `DISPLAY_PT` and `MONO_PT` come from the theme, and paths and git output use monospace (`commit_panel.py:74-77`).
- `MONO_FAMILY = "Consolas"` (`theme.py:23`) has no fallback, although the rest of the app keeps cross-platform branches.
- The 06-01 and 06-03 summaries deferred real-font fit at 900x600 to UAT. 06-UAT.md records a pass with no fit measurement.

### Pillar 5: Spacing (3/4)

- Strengths: `SP_*` spacing (`commit_panel.py:118, 128, 199, 211`). Text-box heights are derived from font metrics (`_lines_height`, `commit_panel.py:80-84`).
- Off-scale numbers remain: `setFixedSize(240, 16)` (line 205), `fontMetrics().height() + 8` (line 259), and the file-list height arithmetic.
- The panel stacks many optional rows, and nothing in the code checks that they fit at the 900x600 minimum.

### Pillar 6: Experience Design (2/4)

- Strengths: explicit state machine (`_STATES`, `commit_panel.py:28-30`); every disabled control has a reason (parent checkbox lines 290-292, blank message line 186, Commit when unavailable); Enter is guarded in the file list (lines 45-52) and Commit is not a default button (lines 191-192); the message is locked while git runs (line 457); Close is blocked during git (`import_dialog.py:2122-2146`); the D-02 "Not committed — commit manually" line is logged on close (`import_dialog.py:2275`).
- Blocking defects: WR-05, WR-01, WR-03 (see Top 3).
- WR-02 (warning): the parent preview (`commit_panel.py:476-479`) and the real parent message (`commit_step.py:192-201, 385-392`) are built on different paths when `gitlink_old` is None. The preview can show text that is never committed (D-19).
- WR-04 (warning): `touched` includes files whose bytes match HEAD. They raise a spurious "missing" ERROR (`commit_step.py:486-497`) and skip the parent bump.
- IN-01 (info): `apply_probe` ticks the parent checkbox again on every probe (`commit_panel.py:285`), which overrides a deliberate untick after "Switch to main".
- IN-02 (info): the read-only probe blocks Close for its whole run, which is up to about 15 git calls at 30 s each.
- The Commit section of the help page (`help_dialog.py:259-279`) is accurate but does not mention that the probe blocks Close.

---

## Code Review Cross-Reference

`06-REVIEW.md` lists 0 critical findings, 5 warnings and 3 info items. All 8 are `open` in `06-REVIEW-DISPOSITION.md`. This audit agrees with WR-01, WR-02, WR-03, WR-05, IN-01 and IN-02. It adds the Visuals, Color, Typography and Spacing findings, which the code review did not cover.

---

## Files Audited

- `kicad_lib_manager/widgets/commit_panel.py`
- `kicad_lib_manager/widgets/import_result.py` (commit slot, lines 111-257)
- `kicad_lib_manager/widgets/import_dialog.py` (commit wiring, lines 2120-2290; Install button at 609)
- `kicad_lib_manager/widgets/help_dialog.py` (Commit section, lines 255-281)
- `kicad_lib_manager/widgets/theme.py`
- `kicad_lib_manager/importer/commit_step.py` (user-facing strings)
- `kicad_lib_manager/main_window.py` (`PRIMARY_BUTTON_QSS` usage at line 226)
