---
phase: 10-importer-on-the-atomic-scheme
plan: 20
subsystem: testing
tags: [tests, atomic-gate, dialog, fixtures, install]
requires:
  - phase: 10-19
    provides: UL_DESCRIPTION, ATOMIC_PROPS and extends_pair(props=...)
provides:
  - set_library(dialog, name, activate=True, fill=True) types the Description a user would
  - fill_description / type_description / ul_dialog(fill=...) helpers in tests/test_import_dialog.py
  - gate-ready parts in the dialog, preview, shared-footprint, single-footprint, field-rule, atomic-target and real-sample tests
affects: [10-21, 10-22]
tech-stack:
  added: []
  patterns: ["a test changes its part (fields, STEP model), never what it asserts", "a dialog test types the Description the owner types, then waits for the plan that follows"]
key-files:
  created: []
  modified:
    - tests/test_import_dialog.py
    - tests/test_import_preview.py
    - tests/test_real_vendor_samples.py
    - tests/test_shared_footprints.py
    - tests/test_single_footprint.py
    - tests/test_field_rules.py
    - tests/test_atomic_targets.py
key-decisions:
  - "Dialog tests type UL_DESCRIPTION through key presses (QTest), so the field counts as edited and a rebuild follows, exactly as for the owner"
  - "test_field_rules._plan takes gate_errors for the tests whose subject is a missing Manufacturer or Datasheet; it allows only those install.atomic codes and still asserts no other error"
  - "Tests that count builds (gated, flaky, overlap) count the one extra build the typed Description causes"
requirements-completed: [LIB-07]
duration: 135 min
completed: 2026-10-27
status: complete
commits: 2
plan_head_before: 6c1175b302bc0a3e46256fda55ad9c7125a38b44
plan_head_after: 0142fa1024ed8b8922aaae2041c7013e3355a813
actuals:
  tokens: 6000
  tasks: 2
  commits: 2
---

# Phase 10 Plan 20: Gate-ready dialog, preview and Phase 10 tests Summary

The dialog, preview, shared-footprint, single-footprint, field-rule, atomic-target and real-sample tests now install atomic parts, and `set_library(..., fill=True)` types the Description a user would, so plan 10-21 can add the gate on a green suite.

## What changed

- `tests/test_import_dialog.py`: `set_library(dialog, name, activate=True, fill=True)` types `UL_DESCRIPTION` into an empty Description field by key presses. New helpers `type_description` and `fill_description(qtbot, dialog)` (types, then waits for the plan that follows). `ul_dialog(..., fill=True)`, `make_install_dialog` and `clash_dialog` fill the Description; `wait_plan` also waits for `not dialog._dirty`. `multi_zip` and the picker zips carry `ATOMIC_PROPS`. `write_clashes` writes an existing footprint that links a model on disk (`${CUSTOM_3DMODEL_DIR}/other.step`). The SnapEDA add-model tracer types the Datasheet its download lacks. Direct `ImportDialog` tests (commit end to end, git-state) and the re-open tests fill the Description after re-opening.
- `tests/test_import_preview.py`: `_ul_plan` defaults `description=UL_DESCRIPTION`; `_members` carries `ATOMIC_PROPS` and a STEP model (`models=()` for the no-model subjects and the kept-symbol test); the Format cases get a Description and a model; `_conflict_plan` keeps an existing footprint that links a model in `3DModels`.
- `tests/test_shared_footprints.py`, `tests/test_atomic_targets.py`: every UL install passes `description=UL_DESCRIPTION`.
- `tests/test_single_footprint.py`: `_open` carries `ATOMIC_PROPS` and a STEP model.
- `tests/test_field_rules.py`: `_plan` gives the typed Description by default and takes `gate_errors`; the extends pair uses `extends_pair(props=ATOMIC_PROPS)`.
- `tests/test_real_vendor_samples.py`: the SnapEDA install with a separate model types a `gct.co` Datasheet (`GCT_DATASHEET`).
- `tests/test_main_window_import.py`, `tests/test_commit_step.py`, `tests/test_kicad_cli.py`: no change. They plan no part through `build_plan` (window, git and kicad-cli tests with fakes or fixtures).

## Verification

How "holds with the gate" was checked: a scratch copy of the 10-21 gate (`incoming_context` + `incoming_issues` added to `build_plan`, never committed, reverted with `git checkout -- kicad_lib_manager`) was run over the ten files, first as a probe and then as a real gate. Under it the only failures are the three tests named below; every other test passes, and every dialog Install click is on an atomic part. On today's planner (no gate) the ten files give 453 passed, 0 skipped.

- `pytest tests/test_import_dialog.py tests/test_import_preview.py tests/test_main_window_import.py tests/test_commit_step.py tests/test_real_vendor_samples.py tests/test_kicad_cli.py tests/test_shared_footprints.py tests/test_single_footprint.py tests/test_field_rules.py tests/test_atomic_targets.py -q -rs`: 453 passed.
- Full `pytest -m "not wurth" -q -rs`: 2785 passed, 13 skipped (Custom submodule absent, symlink privilege, UAT scratch dirs), 0 failed.
- `pytest -m kicad_cli -q -rs`: 33 passed, 0 failed (installs still load in kicad-cli 10).
- The three licence-restricted vendor zips were copied from the orchestrator checkout into the gitignored `downloaded_examples/` of this worktree for the run; nothing under it is committed.

## For plan 10-21 (tests that cannot hold under the gate, by design)

- `tests/test_import_dialog.py::test_fields_clear_and_restore`: asserts "a blank Datasheet installs"; the gate blocks it (`install.atomic.datasheet`). Subject is a cleared field, so 10-21 rewrites that line.
- `tests/test_real_vendor_samples.py::test_real_snapeda_installs` and `::test_real_vendor_installs_load_in_kicad[snapeda]`: the USB4145 download has no Datasheet and no model; the plan said to leave them for blocked-plan assertions.
- `tests/test_import_preview.py::test_issue_rows_no_model_warning` asserts the `install.no_model` text that 10-21 retires; it is not on 10-21's file list, so 10-21 must edit it (and `test_rows_new_library_without_model_has_no_model_row`, `test_rewrites_without_model_have_no_model_row`, which keep a model-less part on purpose and still pass under the gate).
- `tests/test_field_rules.py`: five tests pass `gate_errors=("install.atomic.manufacturer",)` or `("install.atomic.datasheet",)` (distributor link, unlisted domain, cleared Manufacturer twice, cleared Datasheet). Under today's planner they see no error; 10-21 can tighten `_plan` to expect exactly those codes.
- `tests/test_import_dialog.py` tests that keep a part without a model or with a missing field on purpose (`test_footprint_name_default_and_vendor_hint` odd zip, `test_fields_symbol_label_shows_rename`, `test_picker_*`, `test_debounce_single_rebuild`) never click Install, so they pass under the gate unchanged.

## Deviations from Plan

**1. [Scope] A kept part in two tests changed.** `test_conflict_rows_details` and the dialog `write_clashes` helper wrote an existing footprint linking a bare `old.step` / `other.step`; the gate counts that as a missing model when the footprint is kept (Skip). The existing footprint now links `${CUSTOM_3DMODEL_DIR}/<file>` and the file is written to `3DModels`. The conflict, rename and skip assertions are unchanged.

**2. [Scope] Build counters.** `test_updating_label_and_busy_strip`, `test_updating_reason_replaces_the_others`, `test_build_failure_reason_and_retry`, `test_rebuild_failure_keeps_tree_and_logs`, `test_one_build_at_a_time` and `test_builds_never_overlap` gate or fail the Nth build; the Description typed by the helper adds one build before the test's own, so N moved up by one. No assertion about what the build does changed.

**3. [Scope] `test_import_preview.test_sections_order_and_empty_hidden`** uses a model already named `PART.step`, so the Renames section stays hidden as the test asserts; `test_fields_start_with_what_the_plan_writes` uses `fill=False` because it asserts the sample's own empty Description default; `test_supersede_discards_stale_result` fills with `fill=False` in the loop and types the Description once the builds are done.

**4. [Scope] `test_ctrl_return_and_no_default_buttons`** types a ti.com datasheet link instead of `example.com`, so the part still agrees with its Manufacturer; the point of the step (an edit that leaves Install pending) is unchanged.

Total deviations: 4, all test-only, none changing an assertion's meaning.

## Known Stubs

None.

## Threat Flags

None. All writes stay under `tmp_path`; the Custom submodule is absent in the worktree, so `git -C Custom status` could not be compared here (the session guard in the suite fails a run that changes a live Custom/).

## Self-Check: PASSED

- `def set_library(dialog: ImportDialog, name: str, activate: bool = True, fill: bool = True)` is at tests/test_import_dialog.py line 114; `UL_DESCRIPTION` appears in that file.
- Commits 042cbcc and 0142fa1 exist on the branch; no product code changed (`git checkout -- kicad_lib_manager` reverted the scratch gate; `git status` listed only test files).
