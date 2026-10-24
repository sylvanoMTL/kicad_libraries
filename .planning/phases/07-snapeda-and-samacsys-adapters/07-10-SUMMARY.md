---
phase: 07-snapeda-and-samacsys-adapters
plan: 10
subsystem: ui
tags: [pyside6, import-dialog, form-rules, gap-closure, 3d-model]

requires:
  - phase: 07-snapeda-and-samacsys-adapters
    provides: "Add 3D model... (07-08), attach_models intake.no_model_in_source ERROR"
provides:
  - "FormStatus.model_error and the 'model' blocking reason (Error: <text>, target model)"
  - "Dialog rejected-source state (RejectedModel), red plain-text note, Remove button, REMOVE_MODEL_TEXT"
affects: [07-13, help page, 07-UAT test 5]

actuals:
  tokens: 14000
  tasks: 1
  commits: 1
plan_head_before: 8d3a88281bfa51d01eb87451f4e8f86f7c99beb8
plan_head_after: ac0edd941ed57b89c6a2fe4dee1a267319502276

tech-stack:
  added: []
  patterns:
    - "Dialog-held rejection routed through FormStatus so blocking_reasons owns the Install gate"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/form.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_import_form.py
    - tests/test_import_dialog.py

key-decisions:
  - "The rejected package is still closed at once; the dialog keeps only the source file name and its first ERROR Issue"
  - "The 'model' reason target is the Remove button; no amber frame, theme.py unchanged"
  - "Success and stale branches of _on_model_attached call _show_rejection() instead of hiding the note, so a held rejection stays displayed until 07-13 decides how a usable attach clears it"

patterns-established:
  - "Static tooltip on controls near untrusted names (T-07-34)"

requirements-completed: [FMT2-02, INTK-03]

coverage:
  - id: D1
    description: "An unusable bare 3D model source shows a red plain-text note and an 'Error: ...' strip reason, and Install is disabled"
    requirement: "FMT2-02"
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_rejection_blocks_install"
        status: pass
      - kind: unit
        ref: "tests/test_import_form.py#test_blocking_reasons_model_error"
        status: pass
    human_judgment: false
  - id: D2
    description: "Remove clears only the rejected source; Install returns to the plan state and Add 3D model... stays enabled"
    requirement: "INTK-03"
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_rejection_blocks_install"
        status: pass
    human_judgment: false
  - id: D3
    description: "The note colour reads as an error in the real dialog (red, legible on the theme)"
    verification: []
    human_judgment: true
    rationale: "Colour legibility is a visual judgment; tests only assert that theme.ERROR is in the stylesheet"

duration: 25min
completed: 2026-10-24
status: complete
---

# Phase 7 Plan 10: Unusable 3D model source blocks Install Summary

**An unusable model source (empty or renamed bare file, zip with no model, any intake refusal) is now a held rejection shown as a red plain-text note under the 3D model row and as an "Error: ..." strip reason that blocks Install until the Remove button clears it.**

## Performance

- **Duration:** 25 min
- **Tasks:** 1 (tracer)
- **Files modified:** 4

## Accomplishments
- `FormStatus.model_error` plus a `"model"` Reason placed right after the build-failure or plan-error block in `blocking_reasons`; Updating still returns alone.
- `RejectedModel` dialog state, `_show_rejection()`, a Remove button (`REMOVE_MODEL_TEXT`, hidden unless a rejection is held, disabled while busy, static tooltip, in the tab order) and the "model" reason target that focuses it.
- The amber model-note tone is gone; the note tones are now hidden, muted and error (theme.ERROR, PlainText).
- Tracer test `test_add_model_rejection_blocks_install` drives the real dialog, `open_model_source` and `attach_models` with an empty `dummy_CAD_FILE.step` (UAT test 5), then Remove.

## Task Commits

1. **Task 1: unusable bare model file blocks Install in red, Remove unblocks it** - `ac0edd9` (feat)

## Files Created/Modified
- `kicad_lib_manager/importer/form.py` - `model_error` field, "model" target, blocking reason
- `kicad_lib_manager/widgets/import_dialog.py` - `REMOVE_MODEL_TEXT`, `RejectedModel`, rejection state, Remove button, error tone, `_on_remove_model`
- `tests/test_import_form.py` - `test_blocking_reasons_model_error`
- `tests/test_import_dialog.py` - tracer test; refusal, plain-text and worker-failure tests moved to the new design

## Decisions Made
- A successful attach (and a stale outcome) now re-renders the held rejection via `_show_rejection()` rather than hiding the note, so the note, Remove and the strip reason cannot disagree. Whether a usable attach clears the rejection is left to 07-13 as planned.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale "Reading..." handling would hide a held rejection's note**
- **Found during:** Task 1
- **Issue:** The success and stale branches of `_on_model_attached` hid the note unconditionally, which would leave Remove and the blocking reason with no note.
- **Fix:** Both branches call `_show_rejection()`, which hides the note only when nothing is held.
- **Files modified:** kicad_lib_manager/widgets/import_dialog.py
- **Committed in:** ac0edd9

**2. [Test adjustment] Tracer waits for the plan after Remove**
- **Found during:** Task 1
- **Issue:** Moving focus off the editable library combo (Remove takes focus from the strip link, then Add takes it back) fires the combo's `activated` handler, which requests one rebuild (existing behavior), so Install is briefly "Updating".
- **Fix:** The test calls `wait_current` before asserting Install is enabled again. No product change.
- **Files modified:** tests/test_import_dialog.py
- **Committed in:** ac0edd9

---

**Total deviations:** 1 auto-fixed (Rule 1), 1 test adjustment
**Impact on plan:** None on scope.

## Issues Encountered
- The working tree uses CRLF (autocrlf, index is LF) although the plan says LF; edits were kept CRLF so the diff stays clean.
- Case for 07-13: in the INFO-only (duplicate) branch the muted note still replaces a held rejection's note while the rejection and Remove remain. 07-13 owns the clears and resets.
- Verification run: the plan's targeted tests pass (6 passed); the broader command in `<verification>` gave 220 passed, 10 skipped (Custom submodule absent, symlink privilege). The full-suite phase gate (about 6 minutes) was not run in this worktree; the orchestrator owns it.

## Known Stubs
None.

## Threat Flags
None. T-07-33, T-07-34 and T-07-37 mitigations are in place and tested (blocking via `model_error`, PlainText note and escaped strip, static Remove tooltip, package closed at once).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
Ready for 07-13 (other rejection rules, clears and resets, help and doc rewording).

---
*Phase: 07-snapeda-and-samacsys-adapters*
*Completed: 2026-10-24*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/importer/form.py, kicad_lib_manager/widgets/import_dialog.py, tests/test_import_form.py, tests/test_import_dialog.py
- FOUND commit: ac0edd9
