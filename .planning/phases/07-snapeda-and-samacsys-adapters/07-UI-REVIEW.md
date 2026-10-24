# Phase 07 — UI Review (re-audit after gap closure 07-07 and 07-08)

**Audited:** 2026-10-24
**Baseline:** Abstract 6-pillar standards (no UI-SPEC.md for this phase). Intended behaviour taken from 07-CONTEXT.md, 07-07-PLAN.md, 07-08-PLAN.md and their SUMMARY files. Previous review (2026-10-23) findings carried forward and re-checked.
**Screenshots:** not captured (PySide6 desktop app; no dev server on localhost; code-only audit of the Import dialog model row, note, busy guards and help text)
**Interaction captures:** off (`workflow.ui_interaction_capture` is false). Experience Design findings below are code-derived, not from a driven session.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | New model-row copy is specific ("holds no 3D model (.step, .stp or .wrl)", "Reading X..."); help text says "checked like a package", which is vague; carried-forward Drop/Clean/Rename wording still unclear |
| 2. Visuals | 3/4 | Muted/amber note hierarchy is consistent and the button sits under the row; removal rows in Field changes still carry no tone |
| 3. Color | 3/4 | New note uses theme tokens only (AMBER, MUTED); contrast on white is adequate; no new hard-coded hex; removal rows still get no warning tone |
| 4. Typography | 3/4 | Note inherits the default label font; no new sizes or weights introduced; consistent with the other hint labels |
| 5. Spacing | 3/4 | New model-slot layout uses a literal `setSpacing(4)` although SP_XS/SP_SM tokens are already imported in the same file; the row height change on label-to-combo is unverified without a screenshot |
| 6. Experience Design | 2/4 | Install blocking and busy guards are sound and tested; but a failed read after Change... writes an amber note and ERROR log into the new import, the read shows no progress and no feedback to assistive tech, and the vendor-data removal rules are unchanged |

**Overall: 17/24**

No pillar scored 1, so no BLOCKER-class pillar failure. Every pillar below 4 has at least one WARNING finding. The G-07-2 flow itself is covered by integration tests, but the owner's real-file UAT (UAT test 2) has not been run, so the end-to-end result on real USB4145 files is unverified.

---

## Top 3 Priority Fixes

1. **A model read that fails after Change... or a new open paints an amber note and an ERROR into the new import** — the user sees "Import step failed" in a fresh package they never attached to, and the log attributes it to the wrong part — in `kicad_lib_manager/widgets/import_dialog.py` `_on_model_failed` (lines 1689-1696) there is no session check, unlike `_on_model_attached` (line 1657). Fix: capture `session` in `_start_model_attach` and pass it through the `failed` lambda (`worker.failed.connect(lambda text, w=worker, s=session: self._on_model_failed(w, text, s))`); in `_on_model_failed`, after `_end_model_worker`, return early when `s != self._session`, and keep the `_closing` check.

2. **The "Reading X..." note is static and not announced** — a multi-megabyte zip gives no sign of progress, and the note, the only refusal feedback, has no accessible name, unlike the other status labels (`_install_step`, `_strip`, `_install_bar` all call `setAccessibleName`) — in `import_dialog.py` `_start_model_attach` (lines 1616-1638) the worker's `progress` signal is never connected (compare `_on_open_progress`, line 1040). Fix: `worker.progress.connect(lambda msg, cur, tot: self._set_model_note(f"Reading {path.name}: {msg}", tone="muted"))`, and call `self._model_note.setAccessibleName("3D model status")` in `_build_model_row` (line 1416 area).

3. **Vendor-data removals look like routine rows, and the SnapEDA purchase-url drop still rests on an unverified assumption** (carried forward, still valid) — a user can approve a plan that silently drops a SnapEDA `purchase-url` or a duplicate Manufacturer alias — in `kicad_lib_manager/importer/preview.py` `_field_changes_section` (lines 271-282) set `tone="warning"` on `action == "drop"` rows (the `_TONE_COLORS` map in `widgets/preview_tree.py` already has `warning`); in `kicad_lib_manager/importer/adapters/snapeda.py` line 19 verify "purchase-url" against `downloaded_examples/` or remove it from `GENERIC_VOLATILE + (...)` until confirmed.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

**New in 07-07/07-08 (checked):**
- `import_dialog.py:75` `ADD_MODEL_TEXT = "Add 3D model..."`: action label with the correct ellipsis; the same constant feeds the help page (`help_dialog.py:224`), so button and help cannot drift.
- `import_dialog.py:1633`: "Reading {file name}..." while a read runs. Clear and names the source.
- `import_dialog.py:1407-1413` / `attach_models` (`importer/adapters/base.py` ~line 409): "{source} holds no usable 3D model" and `intake.no_model_in_source` text "holds no 3D model (.step, .stp or .wrl)". Specific and actionable.
- `help_dialog.py:224-227`: "SnapEDA ships the 3D model as a separate download..." is accurate and names the accepted types. Weakness: "The added model is checked like a package" is internal jargon; a user does not know what "checked like a package" means. Suggested: "The file is checked for a real STEP or VRML model before it is added."
- Success has no in-row confirmation. The note hides and the combo or label changes to the file name; the only other confirmation is an INFO `intake.model_attached` in the log. Acceptable, but a user who was already on a combo may not notice the selection moved.

**Carried forward (still valid):**
- `preview.py:271-282`: Drop detail reads `"<old> → (removed): <reason>"`, but Clean rows never show the reason (`whitespace`), and Rename rows render as `"Rename MF"` with detail `"→ Manufacturer"`, a different grammar from the Renames section's `"old → new"`.
- `preview.py:274`: `_DROP_REASON.get(change.reason, change.reason)` falls back to the internal code.
- `importer/adapters/samacsys.py:120`: "Not imported: other-CAD folders {names} ({n} files)" is specific; fine.

### Pillar 2: Visuals (3/4)

- `import_dialog.py:1395-1422`: the model row is a `QVBoxLayout` with label or combo, then the button, then the note. Placement under the row mirrors "Make linked" and avoids the 364 px pane overflow the 07-07 deviation fixed. Good hierarchy: the attached model name is primary, the action secondary, the note tertiary.
- Note tones are used consistently with the rest of the dialog: muted for in-progress and duplicate, amber for refusal and worker failure (same amber as the install-blocked strip). Good.
- Label-to-combo transition (`_refresh_model_row`, line 1437) swaps the widget at index 0. A combo is taller than a label, so the form below the row shifts by a few pixels after the first attach. Not verifiable without a screenshot; flagged as unverified.
- Carried forward: `preview.py:282` gives removal rows no tone and `kind="rewrite"`, the same kind as path rewrites, so a dropped field looks like a repointed path. No visual focal point for the destructive part of the plan.

### Pillar 3: Color (3/4)

- New code uses theme tokens only: `import_dialog.py:1433` `f"color: {AMBER if tone == 'amber' else MUTED};"`. No new hex literal.
- Contrast on a white background (computed from the token values in `widgets/theme.py:4` and `:12`): AMBER `#8A5200` is about 6.4:1, MUTED `#595959` about 7.0:1. Both meet WCAG AA for normal text.
- Amber is used for three meanings now: refusal note text (`_set_model_note`), the Install-blocked strip (`AMBER_TINT` background, line 2224), and the `import.step_failed` note. Consistent with the existing warning tone, but a refusal and a blocked install share one colour family; acceptable.
- Carried forward: no warning tone on Drop rows (`preview.py:282`), so removals of vendor data use the default colour and 60/30/10 emphasis cannot be assessed for that section.

### Pillar 4: Typography (3/4)

- `_model_note` (`import_dialog.py:1416-1419`) has no explicit font; it inherits the application default, the same as the other hint labels in this dialog. No new sizes or weights introduced by 07-07/07-08.
- `_set_model_note` sets text with `PlainText` format (line 1417), so a file name containing markup is shown literally (T-07-30 satisfied, covered by `test_add_model_note_is_plain_text`).
- Carried forward: Field changes values use the mono `rewrite` kind (`preview_tree.py`), consistent with Path rewrites. No change.

### Pillar 5: Spacing (3/4)

- `import_dialog.py:1401`: `lay.setSpacing(4)` is a literal. The same file already imports `SP_XS` and `SP_SM` from `widgets/theme` (line 63). The spacing scale is bypassed for the new row. Fix: `lay.setSpacing(SP_XS)` (or the token closest to 4 px).
- `import_dialog.py:1398-1401`: margins are literal `0`, which matches the other rows; fine.
- Row geometry for a long refused-file message in the note is covered only by word wrap (`setWordWrap(True)`), not by a geometry test on the note itself. The existing `test_fields_long_text_geometry` covers the label/combo, not the note.
- No screenshot: the label-to-combo height change and the note's wrap at 364 px are unverified.

### Pillar 6: Experience Design (2/4)

**Positives (verified in code and tests):**
- Install is blocked as Updating while a model is read: `import_dialog.py:2112-2118` counts `_model_worker` in `_updating()`, and `_start_model_attach` calls `_update_install_state()` right after the worker is set (line 1635). Test: `test_add_model_blocks_install_while_reading`.
- Busy guards: `_model_busy()` (line 1593) covers closing, no candidate, open, model, install and commit jobs. The button is disabled during those jobs (`_sync_add_model_button`, line 1645).
- Stale result guard on success: `_on_model_attached` (line 1651-1668) closes and drops a result after Change..., a new open, or an install. Test: `test_add_model_result_after_change_is_dropped`.
- Refusals leave the candidate and row unchanged, and the staging folder is removed. Tests: `test_add_model_refusal_shows_note`, `test_add_model_duplicate_is_noted`.

**Findings:**
- WARNING (stale failure leaks into a new session): `import_dialog.py:1689-1696` `_on_model_failed` has no session comparison and no install guard. After Change... and a new open, a failed read from the old session calls `_set_model_note` on the new candidate's row (the note widget is recreated by `_build_model_row`) and logs `import.step_failed` into the new import's log. Reproducible by reasoning from the code; no test covers a failure after Change..., and `test_add_model_worker_failure_logged` runs in one session only.
- WARNING (no progress, no cancel): `_start_model_attach` (line 1616-1638) never connects `worker.progress`, although the TaskWorker supports it and the open path uses `_on_open_progress` (line 1040). The user sees one static "Reading X..." line for the whole read. The read is capped by the 07-07 byte budget, so it is bounded, but there is still no cancel and no progress.
- WARNING (refusal feedback not announced): `_model_note` (line 1416) never receives `setAccessibleName` or an accessible description; every other status label in the dialog does (`_strip` line 607, `_install_step` line 620, `_install_bar` line 626). The amber refusal reason is therefore visible only to sighted users.
- WARNING (partial success is silent): a duplicate attach is noted, but a successful attach that adds a second model to a part that already has one only changes the combo selection; there is no note. The `intake.model_attached` INFO goes to the log only.
- WARNING (carried forward, still valid): SnapEDA `purchase-url` is in `GENERIC_VOLATILE + ("purchase-url",)` at `importer/adapters/snapeda.py:19-21` with the comment "flagged assumption". The rule removes user-visible data from the preview on an unverified premise. Highest-consequence UX risk in the phase; the rule is not yet confirmed against a real SnapEDA sample.
- WARNING (carried forward, still valid): `snapeda.py:39` uses literal `points += 5` while `SNAPEDA_CLAIM_POINTS = 5` (line 17) exists. Not visual, but the claim threshold can desynchronise.
- Carried forward: `preview.py:282` removal rows have no tone or severity. The user approves the whole plan, and a dropped vendor field is easy to miss.
- Carried forward, INFO: `samacsys.py:120` "Not imported: other-CAD folders ..." is INFO and offers no action; acceptable, but the log does not say files were skipped rather than failed.
- Not verified: keyboard focus after an attach (the button is kept across `_refresh_model_row`, so focus should survive, but no driven session confirms it); the owner's real-file UAT (UAT test 2, G-07-2) on `USB4145-03-0170-C_REVA2.zip` plus its model zip is still pending.

**Positive (carried forward):** the planner exposes every change in the preview before install (`planner.py:139-146`, `plan.py:114-127`), and the no-write-without-preview rule holds.

---

## Previous Review Status

| Previous finding | Status now |
|------------------|------------|
| Drop rows get no warning tone (preview.py) | Still valid |
| SnapEDA purchase-url rule is an unverified assumption (snapeda.py:19) | Still valid |
| Literal `points += 5` in snapeda.py:39 | Still valid |
| Clean rows hide their reason; Rename rows show no old-to-new mapping | Still valid |
| SamacSys "Not imported" notice is INFO and non-actionable | Still valid (acceptable) |
| No keyboard/focus check of the Field changes section | Still not verified |

---

## Registry Safety

Not applicable. `components.json` is not present for this project; no shadcn registry is in use.

---

## Files Audited

- `.planning/phases/07-snapeda-and-samacsys-adapters/07-07-PLAN.md`, `07-08-PLAN.md`, `07-07-SUMMARY.md`, `07-08-SUMMARY.md`, `07-UI-REVIEW.md` (previous review)
- `kicad_lib_manager/widgets/import_dialog.py` (lines 60-80, 302-310, 1245-1475, 1591-1700, 2112-2230, 2283-2344; model-row, note, attach and busy-guard code)
- `kicad_lib_manager/widgets/help_dialog.py` (lines 218-232, Importing Parts page)
- `kicad_lib_manager/widgets/theme.py` (AMBER, AMBER_TINT, MUTED tokens)
- `kicad_lib_manager/importer/adapters/base.py` (`attach_models` return rules, lines ~360-411)
- `kicad_lib_manager/importer/preview.py` (Field changes section, lines 250-310)
- `kicad_lib_manager/importer/adapters/snapeda.py` (lines 15-50)
- `kicad_lib_manager/importer/adapters/samacsys.py` (line 120)
- `kicad_lib_manager/widgets/preview_tree.py` (tone map, rewrite kind)

Not re-read in this pass (relied on SUMMARY files and the previous review): `kicad_lib_manager/importer/package.py` (`open_model_source`), `tests/test_import_dialog.py` (add_model tests were confirmed present by name only: 16 `test_add_model_*` functions), `tests/test_help_dialog.py`.

No source files were modified.
