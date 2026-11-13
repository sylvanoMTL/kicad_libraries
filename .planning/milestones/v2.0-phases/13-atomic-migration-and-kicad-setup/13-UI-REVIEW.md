# Phase 13 — UI Review

**Audited:** 2026-11-13
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md for this phase), plus the project plain-language rule (CLAUDE.md / user memory: no jargon or raw field names in user-facing text)
**Screenshots:** not captured (PySide6 desktop app, no dev server or URL; code-only audit)
**Interaction captures:** off (workflow.ui_interaction_capture is false)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Plain-language helper maps raw `ki_` fields to words, but the User Guide still shows `sym-lib-table` / `fp-lib-table` file names and the chooser warning uses "Schematic Editor" |
| 2. Visuals | 2/4 | Icon-only dismiss button (✕) and the migration/scan dialogs set no accessible names (0 `setAccessibleName` calls in migration_dialog.py and scan_progress.py) |
| 3. Color | 3/4 | Colors are centralised in theme.py (16 hex values, none in the dialogs); 60/30/10 distribution cannot be verified without a render |
| 4. Typography | 3/4 | No hardcoded font sizes or weights in the phase's widgets; text inherits the Qt default, so hierarchy relies on the stylesheet in theme.py and is unverified |
| 5. Spacing | 2/4 | No spacing or layout pass was made on the new windows; score is capped until a render or layout review confirms it |
| 6. Experience Design | 3/4 | Loading, failure, disabled-until-ready, and confirmation states are present; gaps in Skip-button feedback and accessible names |

**Overall: 16/24**

---

## Top 3 Priority Fixes

1. **Icon-only controls have no accessible name** — screen readers and keyboard users get an unnamed "✕" button — Add `setAccessibleName("Dismiss")` (plus `setAccessibleName` on the Skip button and the migration Run/Close buttons where the label is not self-describing) at `kicad_lib_manager/widgets/migration_dialog.py:685` and in `kicad_lib_manager/widgets/scan_progress.py`.
2. **User Guide exposes raw KiCad file names to the owner's plain-language rule** — the guide reads as technical reference rather than task instructions — Keep the file names only once, in parentheses, and describe the action in words ("KiCad's library list files") at `kicad_lib_manager/widgets/help_dialog.py:77`, `:233`, `:452`, `:540`.
3. **Layout of the new windows was never checked** — the migration window, Loading Libraries window, and Pin confirmation could clip or misalign at 1440x900 and at small sizes, and no evidence exists either way — Run the app once and capture the migration window (Result view included), the Loading Libraries window, and the Pin confirmation, then check padding and button rows. Re-score Spacing after that.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

- Good: `kicad_lib_manager/widgets/migration_dialog.py:139-143` converts raw `ki_` field keys into words (D-09, P-14). All label and status text uses `setTextFormat(Qt.TextFormat.PlainText)`, so markup cannot leak into the UI.
- Good: specific action labels ("Run Migration", "Check Again", "Regenerate", "Add model"), and the Pin action text is reused by name at `migration_dialog.py:121-122`.
- Gap (jargon): `kicad_lib_manager/widgets/help_dialog.py:77`, `:233-234`, `:452`, `:540` expose `sym-lib-table`, `fp-lib-table`, and `sym-lib-table_backup_1` as the main vocabulary of the guide.
- Gap (jargon): `kicad_lib_manager/kicad_setup.py:462` says "start and close the Schematic Editor once to add the MPN and Manufacturer columns". "Schematic Editor" is KiCad's internal app name; a plain phrase such as "open KiCad's symbol editor once" would be clearer.
- Gap: `main_window.py:297-390` menu tooltips and status tips repeat file names (`sym-lib-table and fp-lib-table`) and the "Custom/" folder name in the same plain-but-technical register.

### Pillar 2: Visuals (2/4)

- Gap: `migration_dialog.py:685-686` icon-only dismiss button `"✕"` has a tooltip ("Dismiss") but no accessible name.
- Gap: `migration_dialog.py` has 0 `setAccessibleName` calls; `scan_progress.py` has 0; `main_window.py` has 1. The phase's new windows therefore expose no names to assistive tech.
- Gap: the Skip button label changes to "Skip {source}" / "Skipping {source}..." (`scan_progress.py:70-98`). The label is useful, but the tooltip is the only description of what Skip does.
- Good: a clear focal action per view (Run Migration, Generate Tables) is set through the shared primary-button style in the Import dialog; the migration window groups the part list, failure strip, and draft in separate labelled regions.

### Pillar 3: Color (3/4)

- Good: `kicad_lib_manager/widgets/theme.py` holds all 16 hex values; the phase's widgets contain zero hardcoded hex colors.
- Gap: the failure strip and amber warnings (migration and Wrong checkout) rely on color plus text. Text is present, so this is not a defect, but no contrast check was made against the dark/light theme.
- Unverified: the 60/30/10 distribution and accent-usage limits cannot be verified statically; a render is needed.

### Pillar 4: Typography (3/4)

- No `font-size` or `pointSize` overrides in the phase's widgets. Hierarchy comes from the shared stylesheet and the default Qt font.
- Hierarchy is carried by `QLabel` titles (`migration_dialog.py:671-672`, `RESULT_TITLE` at `:1722-1723`); no weight or size variation beyond that was found.
- Unverified: rendered sizes and weights.

### Pillar 5: Spacing (2/4)

- No spacing audit was performed on the new windows, and no layout render exists. The score is held at 2 until a render confirms the layouts.
- The migration window (part list, strip, draft, Result view) and the Loading Libraries window are dense multi-row layouts; these are the most likely places for clipping at small window sizes.

### Pillar 6: Experience Design (3/4)

- Good: loading states are explicit ("Reading Custom...", "Checking Custom for uncommitted changes...", "Starting the migration..."), and failure states have their own title and text (`migration_dialog.py:1696`).
- Good: Run Migration is disabled until the failure strip is empty (`migration_dialog.py:732`, `:1216`), which matches the spec.
- Good: the Pin action declines cleanly with a logged message ("change declined", `kicad_setup.py:506`) and refuses from a worktree or wrong checkout (D-26).
- Good: Skip disables itself while a source is being skipped (`scan_progress.py:71`, `:91`, `:99`).
- Gap: the Skip button shows "Skipping {source}..." but stays disabled-looking with no progress indication of when the check will end.
- Gap: the Result view's Generate Tables outcome appears under the buttons only (`migration_dialog.py:1779-1824`); it is easy to miss.

---

## Files Audited

- kicad_lib_manager/widgets/migration_dialog.py
- kicad_lib_manager/widgets/scan_progress.py
- kicad_lib_manager/widgets/help_dialog.py
- kicad_lib_manager/widgets/theme.py
- kicad_lib_manager/main_window.py
- kicad_lib_manager/kicad_setup.py
- kicad_lib_manager/widgets/import_dialog.py (accessibility count only)
- Phase 13 SUMMARY/PLAN/CONTEXT files were not read in full (summaries total about 395 KB); findings are from the code.
