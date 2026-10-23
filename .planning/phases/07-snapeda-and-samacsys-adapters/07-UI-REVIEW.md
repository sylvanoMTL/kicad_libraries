# Phase 07 — UI Review

**Audited:** 2026-10-23
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md exists for this phase; 07-CONTEXT.md and the 07-0x PLAN/SUMMARY files were used for intended wording and behaviour)
**Screenshots:** not captured (PySide6 desktop app, no dev server on localhost; code-only audit of the import preview and log wording)
**Interaction captures:** off (`workflow.ui_interaction_capture` is false; the Experience Design pillar is scored from code, not from a driven session)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Verbs Drop / Clean / Rename are clear, but Clean rows hide their reason and Rename rows do not show the old-to-new mapping |
| 2. Visuals | 3/4 | Field changes share the "rewrite" kind with Path rewrites and render in the default tone, so removals do not stand out |
| 3. Color | 3/4 | Phase 07 adds no hard-coded colours; removals of vendor data get no warning tone |
| 4. Typography | 3/4 | Values use the mono rewrite font consistently; no new sizes or weights introduced by phase 07 |
| 5. Spacing | 3/4 | No layout code changed in phase 07; not verified visually (no screenshot), so this score is a code-only estimate |
| 6. Experience Design | 2/4 | Data removal rules (SnapEDA purchase-url, duplicate aliases) are shown after the fact with no severity and one rule is an admitted assumption; the SamacSys "Not imported" notice is INFO-level and non-actionable |

**Overall: 17/24**

No pillar scored 1, so there are no BLOCKER findings. Every pillar below 4 has at least one WARNING finding.

---

## Top 3 Priority Fixes

1. **Removals of vendor data look like routine rows** — a user can approve a plan that silently drops a SnapEDA `purchase-url` or a duplicate Manufacturer alias without noticing — give Drop rows a warning tone: in `kicad_lib_manager/importer/preview.py` `_field_changes_section`, set a tone on `PreviewRow` for `action == "drop"` (the `_TONE_COLORS` map in `kicad_lib_manager/widgets/preview_tree.py` already has `warning`).
2. **The SnapEDA `purchase-url` drop rests on an unverified assumption** — the rule is labelled "flagged assumption" in `kicad_lib_manager/importer/adapters/snapeda.py` line 19 and removes user-visible data — verify the rule against the real sample in `downloaded_examples/` before shipping, or drop it from `SNAPEDA_RULES` until it is confirmed.
3. **Field-change rows do not say what changed in plain terms** — "Clean Description" shows old and new values but not that the reason was whitespace collapse, and "Rename MF" shows only "→ Manufacturer" with no alias context — in `preview.py` `_field_changes_section`, render clean rows as `"<field>: whitespace collapsed"` detail and rename rows as `text=f"{change.field} → {change.new}"` with detail `"alias renamed"`, and map unknown reason codes through a label instead of falling back to the raw code.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

- `kicad_lib_manager/importer/preview.py:272-283`: Drop, Clean and Rename labels are plain and match the phase wording. Drop detail reads `"<old> → (removed): <reason>"` with reasons from `_DROP_REASON` (volatile, placeholder, duplicate). Good.
- `preview.py:278-281`: a Clean row's reason (`whitespace`) is never shown. The user sees "Clean Description" with two values and must infer the cause.
- `preview.py:279-281`: a Rename row is rendered as `text="Rename MF"` with detail `"→ Manufacturer"`. The alias origin and the "alias" reason are dropped; the row reads differently from the Renames section's `"old → new"` form, so the two sections use different grammar for the same kind of change.
- `preview.py:274`: `_DROP_REASON.get(change.reason, change.reason)` falls back to the raw internal code if a new reason is added. No current reason is missing, so this is a latent issue, not a visible one.
- `kicad_lib_manager/importer/samacsys.py:120`: `"Not imported: other-CAD folders {names} ({n} files)"` is clear and specific. Good.
- Vendor labels: `widgets/import_dialog.py:86` maps only `UltraLibrarian`, `Loose`, `Unknown`. `SnapEDA` and `SamacSys` pass through unchanged, which gives the intended labels. The import dialog text (line 94) and help text (`widgets/help_dialog.py:212`) both name "SnapEDA" and "SamacSys" consistently.

### Pillar 2: Visuals (3/4)

- `preview.py:362-368`: the section is hidden when empty (Files is always shown). Good hierarchy.
- `preview.py:298` (`kind="rewrite"`): Field changes reuse the same kind as Path rewrites. `preview_tree.py:99-100` gives both a monospace value column, so the two sections look alike even though one removes data and the other only repoints paths.
- Drop rows carry no tone, so a removal row looks identical to a clean row. There is no visual focal point for the destructive part of the plan.

### Pillar 3: Color (3/4)

- Phase 07 adds no literal hex colours in the importer or preview code; colour comes from `widgets/theme.py` through `_TONE_COLORS` (`preview_tree.py:8-13`).
- The only tone applied in the Field changes section is the default. Drop rows could use the existing `warning` tone (AMBER) to separate removals from cleanups. Not applied, so 60/30/10 emphasis cannot be assessed for this section.
- `importer/samacsys.py:120` uses `Severity.INFO`, which maps to black text in `widgets/log_panel.py:12`. Acceptable for an informational line.

### Pillar 4: Typography (3/4)

- Values in the Field changes section use `theme.MONO_FAMILY` / `MONO_PT` via the `rewrite` kind (`preview_tree.py:99-100`), consistent with Path rewrites.
- No new font sizes or weights are introduced in phase 07 code. Font-size/weight grep was not run against the whole `src` tree (the project has no `src/` directory; the GUI lives in `kicad_lib_manager/`), so this is limited to the phase surface.

### Pillar 5: Spacing (3/4)

- No spacing or layout code changed in phase 07 according to the 07-0x SUMMARY files. Score reflects the absence of new layout risk, not a measured pass. A screenshot of the preview with a SnapEDA package would be needed to confirm row heights and truncation with long values (`_shown` cuts at 60 characters, `preview.py:257-262`).

### Pillar 6: Experience Design (2/4)

- WARNING: destructive changes are shown only as rows. There is no confirmation step specific to dropped vendor data; the user approves the whole plan. Combined with finding 1 in Pillar 2, a removal is easy to miss.
- WARNING: `kicad_lib_manager/importer/adapters/snapeda.py:19` sets `purchase-url` as volatile with the comment "flagged assumption". The rule deletes a field from user data on an unverified premise. This is the most consequential UX risk in the phase.
- WARNING: `kicad_lib_manager/importer/adapters/snapeda.py:40` uses a literal `points += 5` while the constant `SNAPEDA_CLAIM_POINTS` exists. Not a visual defect, but it makes the claim threshold easy to desynchronise.
- INFO-level notice: `samacsys.py:120` "Not imported: other-CAD folders ..." is logged at INFO and offers no action. Acceptable, but the user cannot tell from the log that files were skipped rather than failing.
- Positive: the planner exposes every change in the preview before install (`planner.py:139-146`, `plan.py:114-127`), so the no-write-without-preview rule is respected.
- Not verified: keyboard and focus behaviour of the new Field changes section (no driven session).

---

## Registry Safety

Not applicable. `components.json` is not present for this project; no shadcn registry is in use.

---

## Files Audited

- `.planning/phases/07-snapeda-and-samacsys-adapters/07-CONTEXT.md`
- `.planning/phases/07-snapeda-and-samacsys-adapters/07-01-SUMMARY.md` to `07-06-SUMMARY.md` (scanned for UI-facing claims)
- `kicad_lib_manager/importer/preview.py`
- `kicad_lib_manager/importer/plan.py`
- `kicad_lib_manager/importer/planner.py` (lines 131-250)
- `kicad_lib_manager/importer/fieldrules.py`
- `kicad_lib_manager/importer/adapters/snapeda.py`
- `kicad_lib_manager/importer/adapters/samacsys.py` (lines 90-135)
- `kicad_lib_manager/widgets/preview_tree.py`
- `kicad_lib_manager/widgets/import_dialog.py` (vendor labels, issue box, log routing)
- `kicad_lib_manager/widgets/log_panel.py`
- `kicad_lib_manager/widgets/help_dialog.py` (vendor wording)
- `kicad_lib_manager/models.py` (Severity)
- `kicad_lib_manager/main_window.py` (`_log_issues`)

No source files were modified.
