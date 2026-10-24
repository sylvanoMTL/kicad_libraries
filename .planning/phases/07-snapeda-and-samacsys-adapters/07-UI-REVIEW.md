# Phase 07 — UI Review (re-audit after gap closure 07-10 to 07-13)

**Audited:** 2026-10-24
**Baseline:** 05-UI-SPEC.md (Import dialog contract), as amended 2026-10-24 for UAT gaps G-07-5 (model row), G-07-7 (preview columns), G-07-8 (blocking strip). Intended behaviour also from 07-10..07-13 PLAN and SUMMARY files.
**Screenshots:** not captured (PySide6 desktop app; there is no web dev server to reach on localhost:3000/5173/8080). Code-only audit of `widgets/import_dialog.py`, `widgets/preview_tree.py`, `widgets/theme.py`, `importer/form.py`.
**Interaction captures:** off (`workflow.ui_interaction_capture` is false). Experience Design findings are code-derived, not from a driven session.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Blocked-reason copy stacks prefixes: a model read failure reads `Error: Import step failed: RuntimeError: ...` in the strip; the Remove tooltip and the `Error:` reason are otherwise clear |
| 2. Visuals | 3/4 | Red model note plus Remove sits under the 3D model row with clear hierarchy; the note QLabel has no accessible name, so the red refusal is not exposed to assistive tech |
| 3. Color | 3/4 | Error note uses `theme.ERROR` (#CC0000) and the strip uses `AMBER_TINT`; all from tokens; only hard-coded hex left in scope is `#FFFFFF` in `conflict_row.py` (out of this gap set) |
| 4. Typography | 3/4 | Note and strip inherit default label font; no new sizes or weights introduced |
| 5. Spacing | 3/4 | Preview columns honour 120 px minimum and the 55% initial Item share; new model-row code uses literal `setSpacing(4)`/`(8)` alongside `SP_XS`/`SP_SM` tokens already imported in the same file |
| 6. Experience Design | 2/4 | Blocking flow works (red note, Install blocked, Remove recovers), but the preview Detail column sets `setWordWrap(True)` so it wraps instead of eliding as the contract says, and the blocking strip clips at 3 lines with no ellipsis |

**Overall: 17/24**

No pillar scored 1 and no finding was found that stops the blocked-install-then-Remove task, so there are no BLOCKERs from static analysis. Every pillar below 4 has at least one WARNING. The gap-closure behaviour is covered by integration tests (07-13 coverage D1-D4); the visual judgement (D5, UAT test 5) has not been run.

---

## Gap-Closure Items Checked

| Item | Status | Evidence |
|------|--------|----------|
| Red model-row error note and Remove button | Implemented | `import_dialog.py` `_show_rejection` (~1473), `_set_model_note(tone="error")` uses `ERROR`; Remove hidden unless a rejection is held; `remove.setEnabled(not self._model_busy())` |
| Blocking `Error:` strip reason targeting Remove | Implemented | `importer/form.py` lines 174-175 add `Reason("Error: {model_error}", "model")`; `_reason_targets["model"] = remove` |
| Preview columns: Item interactive, Detail stretched, 120 px min | Implemented, with a contract gap on Detail | `preview_tree.py` lines 34-35 and 63-74 (`MIN_COLUMN_WIDTH = 120`, `ITEM_SHARE = 0.55`); `setWordWrap(True)` at line 40 conflicts with the elide requirement (see Experience Design) |
| Rich-text strip tooltip with `STRIP_LINK_HINT` | Implemented | `import_dialog.py` lines 88-90 and 2306-2315: every reason `html.escape`d, leading `<p>` for rich tooltip, hint appended |
| Scoped `QLabel#installStrip` stylesheet | Implemented | `_set_strip` (line ~2255) wraps style in `QLabel#installStrip { ... }`, so tooltip is not tinted |

---

## Top 3 Priority Fixes

1. **Blocked Detail column wraps instead of eliding** — the contract requires Detail to elide in the middle with the full text in the tooltip, but `PreviewTree` calls `setWordWrap(True)` (`widgets/preview_tree.py` line 40). In Qt, wrapped item text is not elided, so long conflict or path Detail text grows the row height instead of truncating, and the 120 px floor on Detail is not what keeps the layout tidy. Fix: set `self.setWordWrap(False)` and keep `setTextElideMode(ElideMiddle)`, or, if wrapping is wanted, update the contract (05-UI-SPEC.md, Preview row) and the E9 overflow row to match. Confirm with one screenshot of a long Detail string at 900 px.

2. **Model read failure reads as a doubled error prefix** — `importer/form.py` line 175 prefixes `Error: ` onto `model_error`, which for a read failure already carries `Import step failed: RuntimeError: disk on fire` (07-13 SUMMARY, key decision 2). The strip therefore shows `Error: Import step failed: RuntimeError: disk on fire` to the user. Fix: in `form.py`, strip the `Import step failed: ` prefix for the blocking reason only (keep the log text unchanged), or use a reason text of `Error: {plain message}` built from the exception, not from the logged Issue text.

3. **Refusal note and blocking strip are not exposed to assistive tech; strip overflow has no ellipsis** — the model note `QLabel` created in `_make_model_widget` (`widgets/import_dialog.py` ~line 1439) has no `setAccessibleName`, unlike every other status label in the dialog (`Install status`, `Install step`, `Install progress`). Separately, the blocking strip (`_strip`, line ~618) is a rich-text `QLabel` capped by `setMaximumHeight(3 lines)`; a QLabel clips without an ellipsis, so the contract's "wraps to at most 3 lines, then elides" is not met and a 4th reason line is cut off silently (the tooltip still lists every reason). Fix: add `self._model_note.setAccessibleName("3D model status")`; for the strip, either shorten the rendered reasons or accept the clip and document it in the spec.

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

- Good: the reason list is specific (`Error: ...`, `Updating preview...`, `Install is blocked:`), the Remove tooltip states the outcome (`Clear the rejected file. Nothing from it was attached.`), and the accessible name is explicit (`Remove the rejected 3D model file`).
- WARNING: doubled prefix in the blocked reason `Error: Import step failed: RuntimeError: disk on fire` (`importer/form.py` lines 173-175 combined with `import_dialog.py` line 1091 and 07-13 SUMMARY decision 2). Reads as a technical log line in the strip, not user copy.
- Carried forward: `Drop`/`Clean`/`Rename` wording in the removal rows is still unclear (previous review).

### Pillar 2: Visuals (3/4)

- Good: the red note sits directly under the 3D model combo and above the Remove button; the amber field frame (`FIELD_FRAME_QSS`, `blocked="true"`) marks the blocked target, so the note, button and frame form a clear group.
- WARNING: `_make_model_widget` note (~line 1439-1441) has `setWordWrap(True)` and `setTextFormat(PlainText)` but no `setAccessibleName`. The red refusal is the only feedback for a rejected model file, so a screen-reader user gets no announced refusal.
- Carried forward: removal rows in Field changes still carry no tone.

### Pillar 3: Color (3/4)

- Good: model note colour is `ERROR` (#CC0000) or `MUTED`, both in `widgets/theme.py`; strip background is `AMBER_TINT` (#FFF8E1), link colour `LINK` set via palette; no new hex literals in the 07-10..07-13 code.
- Contrast: #CC0000 on white is roughly 5.9:1, adequate for the note text.
- Note: `conflict_row.py` lines 35-38 hard-code `#FFFFFF` and `#FFFFFF`-style checked text, not a theme token. Outside this gap set but a token gap.

### Pillar 4: Typography (3/4)

- No new font sizes or weights in 07-10..07-13. The note and strip inherit the default label font and the blocked strip uses bold only through the link colour. The section heading (`HEADING_PT`) and display (`DISPLAY_PT`) tokens are used where they were before.

### Pillar 5: Spacing (3/4)

- Good: `MIN_COLUMN_WIDTH = 120` and `ITEM_SHARE = 0.55` are named constants; the strip uses `SP_SM` (8 px) padding via `setContentsMargins(SP_SM, ...)`.
- WARNING: the surrounding dialog mixes literal `8`/`16` with the `SP_*` tokens (`import_dialog.py` lines 376-377, 462, 472, 501, 511, 542-547, 614, 854 use literals; 625, 637, 670-673 use tokens) in the same file. Consistency with the spacing scale is incomplete.

### Pillar 6: Experience Design (2/4)

- Good: Install is blocked while the model source is held (`_update_install_state`, `ready` requires no reasons); Remove is disabled while a read is in progress (`remove.setEnabled(not self._model_busy())`); a stale read failure is only logged; Remove and Change... clear the held rejection (07-13 decisions).
- WARNING (contract mismatch): Detail elide. `preview_tree.py` line 40 sets `setWordWrap(True)` while the contract (05-UI-SPEC.md E9 overflow row, and the amended Preview paragraph) says Detail elides in the middle. Code-derived; confirm visually.
- WARNING: blocking strip overflow. `_strip` has `setMaximumHeight(3 * lineSpacing + 2 * SP_SM)` and rich text, so a long reason list is clipped at the third line with no `…`. The tooltip carries the full list, but the strip gives no visible cue that more reasons exist.
- WARNING: a model read has no progress feedback. `_start_model_attach` does not connect the worker `progress` signal, so the `Reading ...` note is static for the whole read (carried forward from the previous review; still open).
- Not a registry-style risk: no third-party UI blocks were added in this phase.

---

## Files Audited

- `kicad_lib_manager/widgets/import_dialog.py` (strip, tooltip, model row, `_show_rejection`, `_set_strip`, `_update_install_state`, `_render_strip`)
- `kicad_lib_manager/widgets/preview_tree.py` (column setup, `_apply_initial_width`, `_clamp_item_width`, `render`)
- `kicad_lib_manager/widgets/theme.py` (token source)
- `kicad_lib_manager/importer/form.py` (`blocking_reasons`, `BUILD_FAILED_REASON`, `UPDATING_REASON`)
- `kicad_lib_manager/widgets/conflict_row.py` (hex literals only)
- `.planning/phases/05-import-ui-and-post-install/05-UI-SPEC.md` (contract, amended lines ~315, ~353, ~511, ~517)
- `.planning/phases/07-snapeda-and-samacsys-adapters/07-10..07-13-SUMMARY.md`
- `.planning/phases/07-snapeda-and-samacsys-adapters/07-UI-REVIEW.md` (previous review, carried forward)
