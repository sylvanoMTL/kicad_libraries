---
phase: 07-snapeda-and-samacsys-adapters
reviewed: 2026-10-24T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - kicad_lib_manager/importer/adapters/base.py
  - kicad_lib_manager/importer/package.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_model_attach.py
  - tests/test_model_source.py
  - tests/test_real_vendor_samples.py
  - tests/test_vendorfixtures.py
  - tests/vendorfixtures.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 7: Code Review Report (incremental, gap closure 07-07..07-09)

**Reviewed:** 2026-10-24
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

This is an incremental review of the changes since diff_base `10b62efa` (gap-closure plans 07-07..07-09, G-07-2): `open_model_source`, `attach_models`, the dialog's "Add 3D model..." flow, the help page text and the real-sample tests. The earlier report covered plans 07-01..07-06; its disposition lives in `07-REVIEW-DISPOSITION.md`, and this file replaces that report.

The new core is sound. `open_model_source` does an lstat no-follow check, then an fstat identity check on the opened handle, and counts the real bytes read. `attach_models` is non-mutating and dedupes by SHA-256. It renames clashes in sequence so a renamed name cannot collide with a later one. The applier still re-verifies each source's SHA-256 before it writes (`applier.py:297-303`), so a bare model that is read in place and changes after the preview is refused. Package lifetimes are handled with care in the normal paths (Change, close, install).

One real defect remains in the dialog's stale-result handling, which I reproduced (WR-01). The test suite also still fails 2 tests in this checkout because of the live-Custom coupling already open as WR-01 of the first review.

Run: `tests/test_model_attach.py`, `test_model_source.py`, `test_help_dialog.py`, `test_import_dialog.py`, `test_real_vendor_samples.py` and `test_vendorfixtures.py` give 218 passed, 1 skipped (no symlink privilege) and 2 failed (WR-03).

## Warnings

### WR-01: A model result that arrives for an older package leaves Install stuck on "Updating preview..."

**File:** `kicad_lib_manager/widgets/import_dialog.py:1656-1667` (with `_updating()` at `:2113-2119` and `_end_model_worker` at `:1585-1588`)
**Issue:** `_model_worker is not None` now counts as "updating", so Install is blocked while a model is being read. In `_on_model_attached` the stale branch only calls `_update_install_state()` when `outcome.session == self._session`. `_end_model_worker` only re-syncs the Add button, not the strip or Install.

Sequence:
1. Open package A, click Add 3D model..., and let the read be slow.
2. Click Change... and open package B.
3. B's plan is built while A's model worker is still running. `_model_worker` is non-None, so Install stays blocked as "Updating".
4. A's worker finishes. The result is stale because the session differs, so it is closed and dropped, and nothing refreshes the install state.

I reproduced this with the dialog test harness, using `gated_model_source`, Change..., `open_path(UL_ZIP)`, then releasing the gate. After the worker was gone, the strip still read "Updating preview..." and `_install_btn` was disabled. It recovers only when the user edits a field and triggers another rebuild. `test_add_model_result_after_change_is_dropped` stops at the Start page and never opens a second package, so it does not cover this.

**Fix:** Refresh the install state on every exit of the handler once the worker is cleared. Do it in `_end_model_worker` so it also covers `_on_model_failed`.
```python
def _end_model_worker(self, worker):
    if self._model_worker is worker:
        self._model_worker = None
    self._sync_add_model_button()
    if not self._closing:
        self._update_install_state()
```
Alternatively, drop the `if outcome.session == self._session` guard around `_update_install_state()` in the stale branch. Add a test: add a model, Change..., open a package, release the gate, and assert Install becomes enabled.

### WR-02: A failed model read for an older package writes its error onto the current package's model row

**File:** `kicad_lib_manager/widgets/import_dialog.py:1634-1641`
**Issue:** `_on_model_failed` has no session or staleness check, unlike `_on_model_attached`. If the worker of package A raises after the user has moved on (Change... and then a new open), the amber "Import step failed" note is placed on `self._model_note` of package B. The failure is also emitted to the log as if it belonged to the open part. The `ModelOutcome` carries `session`, but the failure path has no equivalent. The session is only available in the closure of `_start_model_attach`.
**Fix:** Capture `session = self._session` in `_start_model_attach` and pass it to the failure lambda. In the handler, log the issue but skip `_set_model_note` when `session != self._session`. Call `_update_install_state()` in both cases (see WR-01).
```python
worker.failed.connect(lambda text, w=worker, s=session: self._on_model_failed(w, text, s))
...
def _on_model_failed(self, worker, text, session):
    self._end_model_worker(worker)
    if self._closing:
        return
    issue = Issue(Severity.ERROR, "import.step_failed", f"Import step failed: {text}")
    self.issues_logged.emit([issue])
    if session == self._session:
        self._set_model_note(issue.text, tone="amber")
    self._update_install_state()
```

### WR-03: Two dialog tests fail whenever the live `Custom/` checkout already holds the UL sample part (carry-over of first-review WR-01)

**File:** `tests/test_import_dialog.py:99-110` (`test_tracer_ul_import_end_to_end`) and `:357` (`test_preview_sections_follow_plan_ops`); fixture at `tests/conftest.py:79-89`
**Issue:** `custom_copy` copies the owner's real `Custom/Symbols|Footprints|3DModels`. `Custom/3DModels/CSD85301Q2.stp` is already committed there (submodule commit `eecac22`). The plan therefore shows `= Custom/3DModels/CSD85301Q2.stp` where the tests expect `+ ...`, and both tests fail. They are in a file this gap closure edited, so the suite is not green. The first review's WR-01 reported 21 such failures; the gap-closure tests themselves use synthetic layouts (`item_layout`, `write_custom_layout`) and avoid this, but the older tests still depend on the owner's data.
**Fix:** Build `custom_copy` from `write_custom_layout(..., CURRENT_CUSTOM_SYMBOL_LIBS, CURRENT_CUSTOM_FOOTPRINT_LIBS)` as the new tests do. Alternatively, have it remove the UL sample's model and footprint from the copy. Do not read the live submodule.

## Info

### IN-01: `help_dialog` now imports the whole import dialog module for one string constant

**File:** `kicad_lib_manager/widgets/help_dialog.py:7`
**Issue:** `from .import_dialog import ADD_MODEL_TEXT` makes the help widget load `import_dialog` and the entire importer core when it is imported. This breaks the "widgets depend only on models and table_generator" layering in the project notes. It also risks a cycle if the import dialog ever links to a help page. The only reason is to keep the button text and the help text in sync.
**Fix:** Move `ADD_MODEL_TEXT` to a small leaf module, for example `widgets/theme.py` or a new `widgets/texts.py`, and import it from both widgets. `tests/test_help_dialog.py` can keep asserting against the constant.

### IN-02: `open_model_source` puts the full path into its `intake.not_found` text, unlike the "file names only" rule `attach_models` states

**File:** `kicad_lib_manager/importer/package.py:140-143` (rule stated at `adapters/base.py:41-43`)
**Issue:** The `attach_models` docstring promises that Issue texts use file names only, never a folder. The not-found Issue from `open_model_source` is `f"Could not open {path}: ..."`. It carries the full picked path into the model note under the row and into the log panel, while the sibling `unreadable_source` and `link_refused` branches use `path.name`. `open_package` has the same wording, so this is a consistency point and not a new leak. The file comes from a file dialog, so the not-found branch is only reachable through a race.
**Fix:** Use `path.name` here, or state in the docstring that the not-found text is the one exception.

---

_Reviewed: 2026-10-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
