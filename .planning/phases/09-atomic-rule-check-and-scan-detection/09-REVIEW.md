---
phase: 09-atomic-rule-check-and-scan-detection
reviewed: 2026-10-26T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/library_table.py
  - tests/test_atomic_uat.py
  - tests/test_help_dialog.py
  - tests/test_library_table_atomic.py
  - tests/test_main_window.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 9: Code Review Report (incremental, gap-closure plan 09-09)

**Reviewed:** 2026-10-26
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Incremental review of the changes since `4178a6f` (plan 09-09: problem and note rows under symbol rows,
full-width spanning, double-click on a problem row, help text, and the `_edit_first_symbol` UAT helper).

The change is small and sound. Checked and found correct:

- Problem and note rows are non-checkable, so `_on_sym_item_changed` ignores them through the existing
  `item.parent() is not None` guard. `_set_all_check_state` only walks group and library rows, so
  Select All / Deselect All cannot touch the new rows.
- Tooltips on the new rows go through `_rich_tip` (`html.escape`), so vendor text is not read as markup.
  The row text itself is a plain `QTreeWidgetItem` text, not rich text.
- `setFirstColumnSpanned` is called only after the library item is attached to its group, which Qt requires.
  `_span_problem_rows` is the only caller path, and `populate` rebuilds the trees, so no spanned state goes stale.
- The double-click handler resolves a `Violation` or `Finding` row to its parent symbol, and
  `_on_symbol_activated` receives the same `(rel_path, name)` as for a symbol-row double-click.
- `_make_symbol_row` has no callers besides `_populate_trees`, so the new `info_icon` parameter breaks nothing.
- `_edit_first_symbol` uses `kicad_files` helpers that all exist with the signatures used. It mirrors
  `atomic_fixes._insert_property` and keeps the file's EOL and BOM (the CRLF test confirms it).
- Tests run clean: 54 selected tests in `test_library_table_atomic.py`, `test_help_dialog.py` and
  `test_main_window.py` pass, and the 4 `edit_first_symbol` tests in `test_atomic_uat.py` pass.
  The live-Custom scratch test `test_uat_atomic_scratch` was not run, to keep the owner's checkout untouched.

No critical issues. One behavioural warning and three minor items follow.

## Warnings

### WR-01: Double-clicking a part both opens the check dialog and toggles the part's expansion

**File:** `kicad_lib_manager/widgets/library_table.py:91` (connection), `:373-389` (handler)
**Issue:** Symbol rows used to be leaf rows. They now have children whenever the symbol has violations or
findings, and `QTreeView.expandsOnDoubleClick` is left at its default (true). I confirmed this with a probe on a
real mouse double-click: the click on an amber part emits `symbol_activated` and also expands the row
(`expanded after True`). So the main gesture the help page advertises ("double-click the part") now
expands or collapses the part at the same time as the modal-style dialog opens. If the user cancels the dialog
they find the row toggled. The new tests emit `itemDoubleClicked` directly, so they cannot catch this.
**Fix:** Turn off the built-in toggle on the symbol tree, because the arrow and the context menu
(Expand All / Collapse All) already provide expansion:
```python
self._sym_tree.setExpandsOnDoubleClick(False)
```
Library and group rows then also stop toggling on double-click, so if that matters, keep the default and
instead toggle only for rows that do not emit. Add a test using `QTest.mouseDClick` on the viewport
asserting `isExpanded()` is unchanged.

## Info

### IN-01: Expansion state is lost on every rescan

**File:** `kicad_lib_manager/widgets/library_table.py:110-196`
**Issue:** `_populate_trees` clears and rebuilds both trees, and symbol rows now always start collapsed. After
the user applies a fix in the Check Atomic Parts dialog (`_on_atomic_fixes_applied` calls `_start_scan`), every
part they had expanded to read its problems collapses again. This was already true for library rows, but the
third level makes it more visible when working through several failing parts.
**Fix:** Optional. Before `clear()`, record the `rel_path` (and symbol names) of expanded rows and re-expand
them after the rebuild. Skip if the owner is happy with the collapsed start.

### IN-02: Libraries that only have notes stay collapsed, so their note rows are hidden

**File:** `kicad_lib_manager/widgets/library_table.py:195`
**Issue:** `if any(e.failing or e.status for e in lib.symbols)` does not consider `e.findings`. A library
whose parts have only notes (leftover price data, unknown manufacturer) and no violations or status stays
collapsed, although the help page now tells the user that notes are shown as rows. The tooltip, log and
dialog still show them, so nothing is lost. This condition predates the plan.
**Fix:** If notes should be discoverable without opening the library, add `or e.findings` to the condition.

### IN-03: UAT helper copies the property-insert sequence from a private function

**File:** `tests/test_atomic_uat.py:143-155`
**Issue:** The `else` branch repeats the body of `atomic_fixes._insert_property` (version, next id, hidden
template, new or synthesized property text, insert edit), and the comment admits it is a copy because the
original is private. If `_insert_property` changes (for example id handling for a new KiCad format), the
scratch helper drifts silently and the UAT fixture no longer matches what the app writes. The tests cover the
current behaviour only.
**Fix:** Import `atomic_fixes._insert_property` in the test helper and call it with `extra_ids={}`, or make it a
public function. Either removes the duplicated sequence.

---

_Reviewed: 2026-10-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
