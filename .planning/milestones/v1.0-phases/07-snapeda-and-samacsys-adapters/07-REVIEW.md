---
phase: 07-snapeda-and-samacsys-adapters
reviewed: 2026-10-24T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - kicad_lib_manager/importer/adapters/base.py
  - kicad_lib_manager/importer/form.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - kicad_lib_manager/widgets/preview_tree.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_import_form.py
  - tests/test_model_attach.py
  - tests/test_preview_tree.py
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 07: Code Review Report (gap closure 07-10..07-13)

**Reviewed:** 2026-10-24
**Depth:** standard (incremental: `git diff b405591 HEAD`, with surrounding code read for context)
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Scope was the changes for G-07-5 (a rejected 3D model source blocks Install), G-07-7 (PreviewTree column widths) and G-07-8 (strip tooltip and its stylesheet scoping).

The logic is sound. I traced these paths and found no defect:

- **`attach_models` reject-whole path:** it returns `[*problems, error]`, so the summary ERROR is the only ERROR and `errors[0]` in the dialog is the right text. A duplicate counts as passing, and the all-bad case keeps the old `intake.no_model_in_source` wording.
- **`_model_rejection` lifecycle:** it is cleared in `_clear_items` (reached only from `_reset_edit_state` and `_populate_items`) and on a usable attach. It is held on a duplicate-only attach. The stale-session path leaves a held rejection alone.
- **`_on_model_failed`:** the session and file name are bound at spawn time, so a late failure from a replaced package is only logged.
- **Untrusted text:** the note label is `PlainText`. The strip reasons are `html.escape`d. The Remove tooltip is static.
- **`PreviewTree` clamp:** it cannot recurse unboundedly, because the second `setColumnWidth` is a no-op once the width is at or below the limit. `render()` never touches widths. I ran an offscreen check that confirmed rows stay single-line and the Detail text clips and elides.

I ran the five changed test modules with `QT_QPA_PLATFORM=offscreen`. 235 passed and 2 failed. The failures are covered in WR-01.

## Warnings

### WR-01: End-to-end dialog tests assert against the live `Custom/` checkout and now fail

**File:** `tests/test_import_dialog.py:108` and `tests/test_import_dialog.py:370`
**Issue:**
- `test_tracer_ul_import_end_to_end` and `test_preview_sections_follow_plan_ops` fail.
- Both expect `+ Custom/3DModels/CSD85301Q2.stp`, but the plan now yields `= Custom/3DModels/CSD85301Q2.stp`.
- The cause is the `custom_copy` fixture (`tests/conftest.py:79`). It copies the real `Custom/{Symbols,Footprints,3DModels}`, and that submodule now already contains `CSD85301Q2.stp` (the part was imported for real).
- The expected rows therefore depend on mutable personal data. The same coupling will break these tests whenever the owner imports another part into `Custom`.
- This is test reliability, not a regression from 07-10..07-13. The gap-closure tests that build their own packages are unaffected. These two tests do cover the Install path that the new rejection logic gates, though, so they should be green before sign-off.

**Fix:**
- Make the fixture hermetic: seed `tmp_path/repo/Custom` from a committed fixture library under `tests/` rather than `REPO_ROOT / "Custom"`.
- Or have the tracer tests delete `CSD85301Q2.stp` and its `.kicad_mod` and symbol from the copy before asserting `+`.

### WR-02: Untrusted download text still reaches rich-text-autodetecting tooltips

**File:** `kicad_lib_manager/widgets/preview_tree.py:~121-122` (`_row_item`), and `kicad_lib_manager/widgets/import_dialog.py:1503` (`combo.setToolTip(combo.currentText())`)
**Issue:**
- The new code documents the invariant that "a file name from the download must never reach a tooltip, which auto-detects rich text (T-07-34)".
- `PreviewTree._row_item` does `item.setToolTip(0, row.text)` and `item.setToolTip(1, row.detail)`. The model combo does `setToolTip(combo.currentText())`.
- Detail text carries vendor-supplied field values (descriptions, datasheet strings, MPN). Row text carries file names.
- A value such as `<b>x</b>` or an unmatched `<` sequence is rendered as markup in the tooltip instead of shown literally. This is the same class of problem G-07-8 fixed for the strip.
- Pre-existing and low impact: Qt tooltips do not fetch remote resources. It is still inconsistent with the stated mitigation, and `&amp;`-style text will show decoded or garbled.

**Fix:** Route all vendor-derived tooltip text through one helper that escapes it and forces rich text, as `_render_strip` does:
```python
def plain_tooltip(text: str) -> str:
    return "<p>" + html.escape(text) + "</p>" if text else ""
```
Then use `item.setToolTip(0, plain_tooltip(row.text))` and the same in the other places.

## Info

### IN-01: `RejectedModel.source` is stored but never read by production code

**File:** `kicad_lib_manager/widgets/import_dialog.py:252-259`, `1746`, `1777`
**Issue:**
- `RejectedModel.source` is populated at both construction sites (the second one is why `_on_model_failed` gained a `source` parameter and a `n=path.name` default-arg capture).
- Only `tests/test_import_dialog.py` reads it. Production uses only `.issue`.
- This is dead plumbing, unless a later plan (07-13) uses it, so confirm that before it ships.

**Fix:** Either drop the field and the extra parameter, or use it, for example in the Remove button's accessible description.

### IN-02: `sectionResized` is connected before the state it reads exists, and `setWordWrap(True)` is a no-op

**File:** `kicad_lib_manager/widgets/preview_tree.py:44-47`, `37`
**Issue:**
- `header.sectionResized.connect(self._on_section_resized)` runs before `self._item_width_set` is assigned. `_clamp_item_width` reads that attribute. No signal fires in between today, but any future header change inserted before line 47 would raise `AttributeError`.
- Separately, the class docstring says Detail "fills the rest of the tree and elides", but `setWordWrap(True)` is still set. I confirmed offscreen that rows stay single-line, so the call has no effect and is misleading.

**Fix:** Assign `self._sections` and `self._item_width_set` before connecting the signal. Drop `setWordWrap(True)`, or comment why it stays.

---

_Reviewed: 2026-10-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
