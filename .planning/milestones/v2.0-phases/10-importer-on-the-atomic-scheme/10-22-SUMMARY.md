---
phase: 10-importer-on-the-atomic-scheme
plan: 22
subsystem: importer
tags: [atomic-gate, reason-strip, dialog, plain-language]
requires:
  - phase: 10-21
    provides: install.atomic.<rule> ERROR Issues on the plan (the gate)
  - phase: 10-13
    provides: dialog reason strip, field frames and reason targets
provides:
  - atomic_reason(issue): one plain sentence and one target per broken atomic rule
  - live clearing of a reason from the Description, Manufacturer, Datasheet and MPN field texts
  - the Add 3D model... button framed under key model; the Remove button under model_rejected
  - tests/test_gate_reasons.py (23 tests)
affects: []
tech-stack:
  added: []
  patterns: ["a plan ERROR is dropped as stale when the live field text already fixes it (same hook as the blank-MPN and blank-rename reasons)"]
key-files:
  created:
    - tests/test_gate_reasons.py
  modified:
    - kicad_lib_manager/importer/form.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_import_form.py
    - tests/test_install_gate.py
key-decisions:
  - "A parent failure is told from a text that holds a colon by the rule's own wordings (a table of starts per rule), so the sentence for the parent's text is reused: '<parent> (parent symbol): <sentence>', target plan"
  - "A 'no MPN' gate error is always dropped in blocking_reasons: a blank MPN field has its own reason beside it, and a filled one is fixed live"
  - "Raw KiCad field names (ki_*) inside fallback texts are replaced by words (ki_fp_filters reads fp filters), so no reason holds one"
requirements-completed: [LIB-07]
duration: 70 min
completed: 2026-10-27
status: complete
commits: 2
plan_head_before: 0d1a1089e0843417e543c2d7f7917049ff963cd9
plan_head_after: 832b54543b702c9a9410ef3e2d386eb11a21b210
actuals:
  tokens: 14000
  tasks: 2
  commits: 2
---

# Phase 10 Plan 22: Gate reasons in the reason strip Summary

Each atomic failure is now one plain, clickable sentence in the reason strip ("Type a Description", "Enter a Datasheet link", "3D model: ... Use Add 3D model...") that focuses the field that fixes it, turns that field amber, and clears while the owner types.

## What changed

- `kicad_lib_manager/importer/form.py`: `ATOMIC_TARGETS`, `atomic_reason(issue)`, three new `FormStatus` texts (`datasheet_text`, `description_text`, `manufacturer_text`). `blocking_reasons` routes `install.atomic.*` ERRORs through `atomic_reason` (no "Error: " prefix) and drops one as stale when the live field already fixes it (description or manufacturer filled, `datasheet_problem` is None, MPN present). The INFO `install.atomic_note.*` never becomes a reason. A rejected 3D model source keeps its "Error: ..." text but now targets `model_rejected`.
- `kicad_lib_manager/widgets/import_dialog.py`: `_form_status` passes the three field texts; `_build_model_row` frames the Add 3D model... button under key `model` (frame and focus target are the visible button); Remove is registered as `model_rejected`; `_clear_items` pops both keys and the frame.
- Tests: new `tests/test_gate_reasons.py` (23 tests: tracer, each rule's sentence and target, ordering, parent, live clearing, ki_ and "Error:" sweep over 32 texts, model button focus and amber frame, manufacturer and datasheet click-type-clear, markup escaping through the strip). `test_import_form.py` rejected-model target migrated; `test_install_gate.py` strip text now "Type a Description".

## Verification

- `pytest tests/test_gate_reasons.py -q`: 23 passed.
- `pytest tests/test_gate_reasons.py tests/test_import_form.py tests/test_import_dialog.py tests/test_install_gate.py -q`: all passed.
- `pytest -m "not wurth" -q -rs`: 2822 passed, 13 skipped (Custom submodule absent, symlink privilege), 0 failed.

## Deviations from Plan

None - plan executed exactly as written. Notes:

- Task 1 is a tracer, and the implementation landed before its tests in the same commit (no separate RED commit; Task 2 is `tdd="true"` but its tests passed on first run for the same reason, so there is no RED commit for it).
- The plan's `test_import_dialog.py` edit was not needed: its rejected-model tests drive the Remove button through `_remove_model_btn`, which still holds under `model_rejected`.
- While a rebuild is pending the strip shows only "Updating preview...", so the immediate clearing is asserted on the amber frame (via the `detail` reasons) and the strip text is checked after the rebuild.

## Known Stubs

None.

## Threat Flags

None. T-10-27: the strip escapes every reason text in its own links (tested with a model name holding `<b>` markup, strip and tooltip). T-10-28: a reason dropped live only hides text; Install stays off while the form is updating and enables only on a current, unblocked plan.

## Self-Check: PASSED

- `def atomic_reason(issue: Issue) -> Reason` and `"Type a Description"` in `kicad_lib_manager/importer/form.py`; `model_rejected` in `import_dialog.py`.
- Commits 323bb93 and 832b545 exist on the branch.
- `tests/test_gate_reasons.py` exists.
