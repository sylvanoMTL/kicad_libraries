---
phase: 07-snapeda-and-samacsys-adapters
plan: 08
subsystem: import-dialog
tags: [snapeda, 3d-model, import-dialog, pyside6, gap-closure, tdd]

requires:
  - phase: 07-snapeda-and-samacsys-adapters
    provides: "plan 07-07: open_model_source, attach_models, the Add 3D model... tracer and the stale-attach guard"
provides:
  - "Add 3D model... works from every model-row state and selects the attached model"
  - "Plain-text note under the model row: muted for reading and duplicates, amber for refusals and worker failures"
  - "Install is blocked as Updating while a model is read; the button follows every open, model, install and git job"
  - "Model packages stay open until apply_plan returns and are released exactly once on Change..., a new open or close"
  - "Importing Parts help page describes the button, tied to one ADD_MODEL_TEXT constant"
affects: [07-09]

actuals:
  tokens: 7800
  tasks: 3
  commits: 5

plan_head_before: 44a76584162baab6bcdac79d28804e3257a19d56
plan_head_after: 6f2c015dfc7633ad38727e0070bbb52fc559c68d

tech-stack:
  added: []
  patterns:
    - "model worker counted by _updating(), so blocking_reasons reports Updating without a new reason type"
    - "_sync_add_model_button() as the single place that decides the button state"
    - "_shutdown nulls worker.value after closing an unhandled outcome package, so a package is closed once"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_import_dialog.py
    - tests/test_help_dialog.py

key-decisions:
  - "The note lives in the existing _model_slot layout under the button, not in a new wrapper layout"
  - "_on_model_attached returns without closing when the dialog is closing; _shutdown owns that package, so it closes once"
  - "help_dialog imports ADD_MODEL_TEXT from import_dialog (no import cycle: import_dialog never imports help_dialog)"

requirements-completed: [FMT2-02, INTK-03]

coverage:
  - id: D1
    description: "Add 3D model... is on every model-row state, selects the attached model, lists clashes with a suffix, and keeps every user edit with no call to _populate_items or _reload_symbol_defaults"
    requirement: FMT2-02
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_button_on_every_row_state"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_keeps_edits"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_clash_listed_with_suffix"
        status: pass
    human_judgment: false
  - id: D2
    description: "A refused, empty or duplicate model source leaves the candidate unchanged and shows its reason as plain text in an amber or muted note and in the log; the refused staging folder is removed"
    requirement: INTK-03
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_refusal_shows_note"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_note_is_plain_text"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_duplicate_is_noted"
        status: pass
    human_judgment: false
  - id: D3
    description: "Install is blocked as Updating while a model is read; the button is off during any other job; a late model result after Change... or during close is released and never attached; attached packages live until apply_plan returns"
    requirement: FMT2-02
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_blocks_install_while_reading"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_result_after_change_is_dropped"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_close_while_reading_closes_package"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_package_open_until_install_ends"
        status: pass
    human_judgment: false
  - id: D4
    description: "The help page names Add 3D model..., the accepted file types and SnapEDA's separate download, checked against the dialog's own constant"
    requirement: FMT2-02
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_import_page_describes_add_model"
        status: pass
    human_judgment: false
  - id: D5
    description: "Owner UAT on the real USB4145 files (UAT test 2, G-07-2): the note's look, the combo, the preview and the KiCad Footprint Editor resolving the model"
    verification: []
    human_judgment: true
    rationale: "Layout of the note under the button and the final model link in KiCad are visual and tool-specific judgments; the plan's human-check lists the steps"

duration: about 40 min
completed: 2026-10-24
status: complete
---

# Phase 7 Plan 08: Add 3D model... dialog behaviour Summary

**Add 3D model... now works from every row state without touching the user's edits, shows refusals and duplicates in a plain-text note, blocks Install while a model is read, and releases every model package exactly when it must; the help page documents it.**

## Performance

- **Tasks:** 3 (2 TDD, 1 auto)
- **Files modified:** 4 (no new files)
- **Commits:** 5 task commits plus this metadata commit
- **Diff size:** about 510 lines added (424 in the dialog tests)

## Accomplishments

- **Model row.** A `QLabel` note (`_model_note`, PlainText, word wrap, hidden by default, reset in `_clear_items`) sits under the button. `_set_model_note(text, tone=...)` takes `hidden`, `muted` or `amber`. "Reading X..." is muted, a refusal shows its first ERROR in amber, a duplicate its INFO in muted, a worker failure the `import.step_failed` text in amber. A refused or duplicate attach never touches the candidate, the row or the generation counter.
- **Busy guards.** `_updating()` also counts `_model_worker`, so `blocking_reasons` reports `UPDATING_REASON` and Install stays off until the plan that shows the model is current (T-07-29). `_sync_add_model_button()` decides the button from `_model_busy()` (closing, no candidate, open, model, install or git job) and is called from `_update_install_state`, `_set_install_ui`, `_set_git_worker` and the model worker start/end.
- **Lifetime.** Attached packages are closed only by `_discard_package` (Change..., a new open, close), never during an install, so `apply_plan` still reads them (WR-04). A model read that ends during close is closed once by `_shutdown`; the queued result slot returns without a second close. A result after Change... is closed and dropped (T-07-28).
- **Help page.** `ADD_MODEL_TEXT = "Add 3D model..."` is the button text and the help page text (one constant). The Items section explains SnapEDA's separate download and the `.step`, `.stp`, `.wrl` or `.zip` input, and that the preview shows the model before anything is written.
- Most of the row-state and edit-preservation behaviour was already correct after 07-07; the tests for it are regression guards (see TDD below).

## TDD Gate Compliance

RED evidence was captured as JUnit XML from pytest and classified with `gsd check tdd-red-evidence`; every verdict is `RED_EVIDENCE_OK`.

- **Task 1 RED (`d6bf2c2`):** 4 of the 7 new `test_add_model_*` tests fail (`test_add_model_to_part_with_model_selects_it`, `..._refusal_shows_note`, `..._note_is_plain_text`, `..._duplicate_is_noted`), all with `AttributeError: no attribute '_model_note'`. Classified target: `test_add_model_refusal_shows_note`. Semantic assessment: the target executed and failed because the planned note did not exist yet; no setup, import or fixture fault. `test_add_model_button_on_every_row_state`, `..._clash_listed_with_suffix`, `..._keeps_edits` and the tracer passed at RED because 07-07 already built that behaviour; they are regression guards, not new behaviour.
- **Task 1 GREEN (`0d64c8b`):** 8 `add_model` tests pass (7 new plus the 07-07 tracer).
- **Task 2 RED (`9ebaea1`):** 2 of 8 new tests fail: `test_add_model_blocks_install_while_reading` (`assert not dialog._install_btn.isEnabled()` while the read is held) and `test_add_model_close_while_reading_closes_package` (`['close', 'close'] != ['close']`). Both classified `RED_EVIDENCE_OK`. Semantic assessment: both ran and failed on the planned assertion for the intended reason. The other six (Change... drop, package open until install, change closes package, disabled while installing, off GUI thread, worker failure) passed at RED because 07-07's stale-attach guard and lifetime handling already satisfied them.
- **Task 2 GREEN (`8a4430d`):** 16 `add_model` tests pass.
- Task 3 is `type="auto"` (no RED). No REFACTOR commits.

## Task Commits

1. **Task 1: model row note and edit-keeping tests** - `d6bf2c2` (test), `0d64c8b` (feat)
2. **Task 2: busy guards and package lifetime** - `9ebaea1` (test), `8a4430d` (feat)
3. **Task 3: help page and ADD_MODEL_TEXT** - `6f2c015` (docs)

**Plan metadata:** the commit that adds this file (docs).

## Files Created/Modified

- `kicad_lib_manager/widgets/import_dialog.py` - `_model_note`, `_set_model_note`, `_sync_add_model_button`, model worker counted in `_updating()`, closing-aware `_on_model_attached`, `_shutdown` nulls handled worker values, `ADD_MODEL_TEXT`
- `kicad_lib_manager/widgets/help_dialog.py` - Items paragraph for Add 3D model...
- `tests/test_import_dialog.py` - 15 new `test_add_model_*` tests (7 in Task 1, 8 in Task 2), 16 with the 07-07 tracer; helpers `pick_model`, `attach_model`, `bare_model`, `model_zip`, `gated_model_source`)
- `tests/test_help_dialog.py` - `test_help_import_page_describes_add_model`

## Decisions Made

- The note was placed in the existing `_model_slot` `QVBoxLayout` (label or combo, button, note) instead of wrapping that layout in another one; `_refresh_model_row` keeps replacing item 0.
- `_on_model_attached` returns early when the dialog is closing. `_shutdown` has already waited for the worker and closes the unhandled package, and now sets `worker.value = None`, which makes the release happen once even if `_shutdown` runs twice.
- `help_dialog` imports `ADD_MODEL_TEXT` from `import_dialog` (no cycle). The existing "no subprocess in import-flow modules" test is unaffected.
- A model worker that outlives Change... still counts in `_updating()` until its result arrives (it then drops it). Accepted: transient, and it can only delay Install on the next package until the old read ends.

## Deviations from Plan

None - plan executed exactly as written. (The plan's `_updating()` line `_model_worker is not None` and the `_sync_add_model_button` wiring follow the plan; the extra `_set_install_ui` and `_set_git_worker` calls only keep the button state correct when those jobs start and end.)

**Total deviations:** 0. **Impact on plan:** none.

## Issues Encountered

- The Edit tool rewrote the CRLF files with LF line endings once; every file was normalised back to CRLF before committing (diffs are line-sized, no whole-file churn).
- Baseline before the first edit: `tests/test_import_dialog.py` + `tests/test_help_dialog.py` = 143 passed, 9 skipped (the two Custom-dependent ids deselected).
- Full suite after the last commit: **4 failed, 1838 passed, 90 skipped**. The 4 failures are the known base failures, all real `kicad-cli` KiCad 10 writing symbol format 20251024 where tests expect 20241209: `test_install_plan.py::test_version_real_cli_into_20241209`, `::test_library_real_cli_new_header`, `::test_noop_second_plan_after_normalised_apply`, `test_kicad_cli.py::test_real_cli_upgrades_ul_symbol_deterministically`. The other Phase 7 baseline ids that read the real `Custom/` tree skip in this worktree (the submodule is not initialised here).
- The worktree's `Custom` submodule is empty, so `test_tracer_ul_import_end_to_end` and `test_preview_sections_follow_plan_ops` were deselected in the targeted runs.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. T-07-27, T-07-28, T-07-29 and T-07-30 are mitigated and each has its test (`test_add_model_close_while_reading_closes_package` / `..._package_open_until_install_ends`, `..._result_after_change_is_dropped`, `..._blocks_install_while_reading`, `..._note_is_plain_text`).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for plan 07-09 (docs, parallel). Owner UAT (UAT test 2, G-07-2) is the remaining human check: open `downloaded_examples/USB4145-03-0170-C_REVA2.zip` in Import Part..., click Add 3D model..., pick `downloaded_examples/194150990-659-usb4145-03-0170-c.zip`. Expected: the 3D model row shows `usb4145-03-0170-c.stp`, the preview lists `Custom/3DModels/USB4145-03-0170-C.stp` with no "no 3D model found" warning, and after Install into `Connector_USB_GCT` the footprint's model resolves through `${CUSTOM_3DMODEL_DIR}/USB4145-03-0170-C.stp` in KiCad's Footprint Editor. Those two real files are not in this worktree's `downloaded_examples/`, so this check stays with the owner.

## Self-Check: PASSED

- Modified files exist: `kicad_lib_manager/widgets/import_dialog.py`, `kicad_lib_manager/widgets/help_dialog.py`, `tests/test_import_dialog.py`, `tests/test_help_dialog.py`, this SUMMARY.
- Commits on this branch: `d6bf2c2`, `0d64c8b`, `9ebaea1`, `8a4430d`, `6f2c015`.
- `git rev-list --count 44a7658..HEAD` = 5 task commits (before this metadata commit).
- Full suite: only the 4 known base failures.

---
*Phase: 07-snapeda-and-samacsys-adapters*
*Completed: 2026-10-24*
