# Phase 11 - UI Review

**Audited:** 2026-10-30
**Baseline:** abstract 6-pillar standards (no UI-SPEC.md for this phase); the UI-02 items of `06-UI-REVIEW.md` and the D-17..D-20 decisions in `11-CONTEXT.md`
**Screenshots:** not captured (PySide6 desktop app, no dev server or URL; code-only audit)
**Interaction captures:** off (workflow.ui_interaction_capture is false)
**Scope:** `kicad_lib_manager/widgets/commit_panel.py`, `import_dialog.py` (Install button, commit wiring), `help_dialog.py` (Commit section), `theme.py`, `importer/commit_gate.py` (line text only)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Button and outcome copy fixed ("Committed in Custom only"), but jargon remains: "Commit parent ref", "Custom ref", "detached HEAD", "origin/main" |
| 2. Visuals | 3/4 | Commit and Install Part use `PRIMARY_BUTTON_QSS`; gate buttons are secondary; the parent-only button label is not plain |
| 3. Color | 3/4 | Outcome strip tint follows the strongest line (ERROR / AMBER / SUCCESS); `PRIMARY_BUTTON_QSS` repeats hex values instead of using `ACCENT` |
| 4. Typography | 3/4 | `MONO_FAMILY = "Consolas"` still has no fallback (carried over); 900x600 fit still not measured |
| 5. Spacing | 3/4 | `setFixedSize(240, 16)` gone from the commit panel; the Install progress bar at `import_dialog.py:743` keeps the same magic size |
| 6. Experience Design | 3/4 | Refusal, re-probe, Check again, Close-during-probe and IN-01 are wired and tested; no statically provable blocker; the look and the PowerShell paste remain human checks |

**Overall: 18/24**

---

## UI-02 Closure Check (against 06-UI-REVIEW.md)

| 06-UI-REVIEW item | Status | Evidence |
|---|---|---|
| P1: button reads "Committed" in `failed` | Closed | `_COMMITTED_CUSTOM_ONLY = "Committed in Custom only"` (`commit_panel.py:31`, used at `:670`) |
| P1: "Committing in Custom…" with Unicode ellipsis | Open (minor) | Code still uses "Committing..." (`commit_panel.py:` `set_committing`) |
| P2: Commit button not primary | Closed | `self.commit_button.setStyleSheet(theme.PRIMARY_BUTTON_QSS)` (`commit_panel.py:254`) |
| P2: Install Part not primary | Closed | `self._install_btn.setStyleSheet(PRIMARY_BUTTON_QSS)` (`import_dialog.py:749`) |
| P3: `ERROR_TINT` / `SUCCESS_TINT` unused for outcomes | Closed | `_outcome_tint()` (`commit_panel.py:98-106`), applied in `_tint_outcome_frame` (`:510-520`) |
| P4: Consolas without fallback | Open | `theme.py:23` unchanged; `_mono_font()` uses it directly |
| P4: fit at 900x600 not measured | Open | No measurement in any 11-* summary; 11-17 defers panel look to manual check |
| P5: `setFixedSize(240, 16)` in commit panel | Closed | Now `theme.SP_XL * 8`, `theme.SP_MD` (`commit_panel.py:267`) |
| P5: `fontMetrics().height() + 8` in commit panel | Closed | Now `+ theme.SP_SM` (`commit_panel.py:357`) |
| P6: WR-05 panel stuck after refusal | Closed (panel side) | `begin_reprobe`, `_pending_refusal`, `_drop_pending` (`commit_panel.py:` `apply_probe`, `show_outcome`) |
| P6: Help Commit section silent on Close | Closed | Help now says the first check does not lock the windows (`help_dialog.py:` Commit section) |

---

## Top 3 Priority Fixes

1. **Plain-language labels for the parent-only action and the parent checkbox** - a user reads "Commit parent ref" and "Also commit the Custom ref in the parent repo", which breaks the project's plain-language rule - Change `_PARENT_ONLY_LABEL` (`commit_panel.py:36`) to something like "Record new Custom version in parent" and `_PARENT_TEXT` (`commit_panel.py:30`) to "Also record the new Custom version in the parent repo", and mirror both in the Help Commit section (`help_dialog.py:350`).
2. **Replace the Custom-state jargon** - "Custom: detached HEAD at abc1234" (`commit_panel.py:551`), "origin/main" (`help_dialog.py:365`) and "detached HEAD" (`help_dialog.py:363-364`) reach the user - Use "Custom is not on a branch (at abc1234)", "the main branch on GitHub" or "the copy of main on the server", and "not on a branch" in Help.
3. **Remove the duplicated primary-button hex values and the Install bar magic size** - `PRIMARY_BUTTON_QSS` (`theme.py:27-30`) repeats `#0078D4`, `white`, `#E1E1E1`, `#595959` instead of `ACCENT` and `MUTED`, and `import_dialog.py:743` still calls `setFixedSize(240, 16)` in the same Install view - Build the QSS from `ACCENT` and `MUTED`, and size the install bar from `SP_XL * 8` and `SP_MD` as the commit panel now does.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

- Fixed: the partial-result button reads "Committed in Custom only" (`commit_panel.py:31`), the gate lines are plain (`commit_gate.py:494-495` "Library / Part: reason"; reasons such as "no datasheet" in `atomic_check.py:57`), and the refusal strip has a clear prefix (`_STRIP_PREFIX`, `commit_panel.py:` strip table).
- Jargon left in user-facing text, against the project rule:
  - `commit_panel.py:30` "Also commit the Custom ref in the parent repo"
  - `commit_panel.py:36` "Commit parent ref" (button, D-14 discretion label)
  - `commit_panel.py:551` "Custom: detached HEAD at <hash>" and "detached HEAD"
  - `help_dialog.py:350`, `:363-365` ("Custom ref", "detached HEAD", "origin/main")
- Minor: "Committing..." uses ASCII dots while D-07 specifies an ellipsis (carried over from 06 Pillar 1).

### Pillar 2: Visuals (3/4)

- Fixed: primary Commit (`commit_panel.py:254`) and primary Install Part (`import_dialog.py:749`) share one style, so the main action of each view looks the same (D-19).
- Secondary gate controls ("Open Check Atomic Parts…", "Check again") have no style sheet and are never default (`commit_panel.py:` gate row, `setAutoDefault(False)`), as D-07 requires.
- The "Commit parent ref" button label (see Copywriting) is the one action in the gated/parent-only flow whose text does not say what happens.
- The gate lines (`self._gate_lines`) have no accessible name; the strip and the gate lines are read by screen readers without a role. Minor.

### Pillar 3: Color (3/4)

- Fixed: `_outcome_tint()` picks ERROR_TINT, then AMBER_TINT, then SUCCESS_TINT by the strongest severity (D-18). The object-name selector `QFrame#outcomeStrip` keeps child labels unstyled, so line colours are preserved.
- `theme.PRIMARY_BUTTON_QSS` (`theme.py:27-30`) hard-codes `#0078D4`, `white`, `#E1E1E1` and `#595959`. `theme.py` declares itself the single source (`ACCENT`, `MUTED` already exist). The values match today, but a theme change would miss this button.
- The accent is used by the primary button only in the commit panel; amber is consistent for warnings, the "not main" branch label and the gate strip.

### Pillar 4: Typography (3/4)

- Sizes come from `MONO_PT`, `HEADING_PT` (`theme.py:20-24`) and `_mono_font()` sets a monospace style hint (`commit_panel.py:86-89`).
- Still open from 06 Pillar 4: `MONO_FAMILY = "Consolas"` has no non-Windows fallback. The style hint limits the damage, but the rest of the app keeps cross-platform branches.
- The 900x600 fit of the longer panel (gate lines, old-failure note, changed/added hints, earlier-commit block, preview, output box) is not measured anywhere in the phase.

### Pillar 5: Spacing (3/4)

- Fixed in the commit panel: `files.setFixedHeight(row * min(...) + 2 * frameWidth)` derives from the row size (`commit_panel.py:` `_fill_files`); `setFixedSize(theme.SP_XL * 8, theme.SP_MD)` (`:267`); spacing uses `SP_*` throughout.
- Residual: `commit_panel.py:357` uses `fontMetrics().height() + theme.SP_SM` as the empty-list row height. Acceptable (theme scale plus metrics).
- Residual outside the commit panel but in the same Install view: `import_dialog.py:743` `self._install_bar.setFixedSize(240, 16)` and `import_dialog.py:1348` `+ 8`. Not part of the commit panel, but the same family of defect 06 Pillar 5 named.
- `_PREVIEW_LINES`, `_OUTPUT_LINES`, `_MESSAGE_LINES` are line counts scaled by font metrics (`_lines_height`); good.

### Pillar 6: Experience Design (3/4)

- Verified in code (and covered by tests named in the 11-* summaries):
  - Refusal: Commit disabled, one line per failing part and rule, capped at ten with "...and k more" (`_GATE_LINES_SHOWN`, `_show_gate`).
  - Recovery: "Open Check Atomic Parts…" emits the first failure (`_on_open_check_clicked`, `gate.first_failure`); "Check again" clears the pending refusal and emits (`_on_check_again_clicked`).
  - Re-probe keeps message, parent choice and refusal text (`begin_reprobe`, `_show_pending`); own refusal replaces the pending one (`apply_probe`).
  - IN-01: parent box ticked only on the first probe (`_parent_wanted`); IN-02: probe does not lock Close (11-09).
  - Old failures are notes and never block (`old_notes`, `commit_panel.py` `_old_label`).
  - Outcome after a partial result: "Committed in Custom only" button, ✓/✖ lines and the manual command kept in the outcome strip.
- No statically provable blocker: every disabled control states its reason, and Commit only enables from `ready` with a non-blank message.
- Not verified here: the look of the panel at real fonts and the manual PowerShell paste (11-VERIFICATION human items 1 and 2, pending `/gsd-verify-work`).

---

## Regressions

- None found in the commit panel. The changes are additive: the strip, the tints, the gate rows and the parent-only path do not alter the ready-state layout beyond the new hidden-by-default rows.
- Watch item: the Commit button text is reset in `_set_state` (`commit_panel.py`, `commit_button.setText` map) to "Commit" for non-terminal states, which also covers "gated" and "probing". Correct, but the parent-only "Commit parent ref" is set only in `ready`, so after a refusal it reverts to "Commit" until the next probe; acceptable because Commit is disabled then.

---

## Files Audited

- `kicad_lib_manager/widgets/commit_panel.py` (full)
- `kicad_lib_manager/widgets/theme.py` (full)
- `kicad_lib_manager/widgets/import_dialog.py` (style and sizing lines: 72-73, 724, 743, 749, 1348, 2642-2704)
- `kicad_lib_manager/widgets/help_dialog.py` (Commit section, lines 255-281 and 340-380)
- `kicad_lib_manager/importer/commit_gate.py` (`_line`, `failure_lines`, `old_notes`, `first_failure`)
- `kicad_lib_manager/atomic_check.py` (reason strings, lines 51-66)
- Phase 11 summaries 11-04, 11-09, 11-10, 11-14, 11-17 and 11-CONTEXT.md
- `.planning/milestones/v1.0-phases/06-git-commit-step/06-UI-REVIEW.md` (baseline for the closure table)
