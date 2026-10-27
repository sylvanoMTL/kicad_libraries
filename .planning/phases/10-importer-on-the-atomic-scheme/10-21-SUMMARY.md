---
phase: 10-importer-on-the-atomic-scheme
plan: 21
subsystem: importer
tags: [atomic-gate, planner, install, tests]
requires:
  - phase: 10-06
    provides: incoming_context / incoming_issues (the Phase 9 check on planned bytes)
  - phase: 10-19
    provides: gate-ready install-path tests
  - phase: 10-20
    provides: gate-ready dialog, preview and Phase 10 tests
provides:
  - build_plan runs the atomic check on the planned symbol, footprint and model; each broken rule is an ERROR install.atomic.<rule>
  - a part without a 3D model, or with the model declined, is blocked (no install-anyway)
  - tests/test_install_gate.py (14 tests)
affects: [10-22]
tech-stack:
  added: []
  patterns: ["gate judges planned bytes: a decision that writes, or an open conflict, counts as planned; reused and kept files count as on disk"]
key-files:
  created:
    - tests/test_install_gate.py
  modified:
    - kicad_lib_manager/importer/planner.py
    - tests/test_commit_plan.py
    - tests/test_customfixtures.py
    - tests/test_field_cleanup.py
    - tests/test_field_rules.py
    - tests/test_import_dialog.py
    - tests/test_import_form.py
    - tests/test_import_preview.py
    - tests/test_install_e2e.py
    - tests/test_install_options_clear.py
    - tests/test_install_plan.py
    - tests/test_model_attach.py
    - tests/test_real_vendor_samples.py
    - tests/test_vendor_install.py
key-decisions:
  - "The gate runs once, after the symbol states and file decisions are final, over the symbols whose state is new, overwrite or open; a kept or identical symbol gets no check"
  - "An open (unresolved) footprint or model conflict is judged on the planned bytes, so the plan lists the conflict and any atomic ERROR together"
  - "install.no_model and install.manufacturer_missing WARNINGs are removed; install.model_declined INFO is kept"
requirements-completed: [LIB-07]
duration: 150 min
completed: 2026-10-27
status: complete
commits: 3
plan_head_before: 6fc57c6d569200978ab82434b1727dd1cfb2d12a
plan_head_after: 269c2daffdab5ca0e6c7df2499288bd18df72776
actuals:
  tokens: 30000
  tasks: 3
  commits: 3
---

# Phase 10 Plan 21: The install gate Summary

build_plan now runs the unchanged Phase 9 atomic check on the part as it would be installed (planned symbol bytes, linked footprint planned or reused, model planned or on disk), so a part that fails any atomic rule, including a missing 3D model, gives a blocked plan that apply_plan refuses before writing.

## What changed

- `kicad_lib_manager/importer/planner.py`: after the symbol states, file decisions and bytes are final, `incoming_context(...)` + `incoming_issues(edited.root, written, rel_path=..., ctx=...)` add one ERROR `install.atomic.<rule>` per broken rule (INFO `install.atomic_note.*` for notes). `planned_footprints` holds the linked footprint's op path and bytes (or, for an open conflict, the bytes it would write); `planned_models` holds the model name when its decision writes or is open. The `install.no_model` and `install.manufacturer_missing` WARNINGs are gone.
- `tests/test_install_gate.py` (new, 14 tests): the tracer (UL CSD85301Q2 blocked by exactly `install.atomic.description`, installs with a Description and `atomic_check.check_libraries` then finds it passing; dialog keeps Install off with "no description" until the Description is typed), and each rule through the gate: model missing, model declined (keeps `install.model_declined`), datasheet, description, manufacturer, reused footprint and model on disk, open footprint conflict judged on planned bytes, extends parent named as "PARENT_X: no description", skipped symbol not checked, unknown manufacturer is an INFO note.
- Existing tests: every test whose subject is a missing field or model now asserts the gate error and a blocked plan; none was weakened (see deviations for the ones that changed their part).

## Verification

- `pytest tests/test_install_gate.py tests/test_incoming_check.py -q`: 32 passed (gate file: 14).
- `pytest -m "not wurth" -q -rs`: 2799 passed, 13 skipped (Custom submodule absent, symlink privilege, two UAT scratch-dir skips), 0 failed.
- `pytest -m kicad_cli -q -rs`: 33 passed, 0 failed (installs still load in kicad-cli 10).
- Licence-restricted vendor zips were copied into this worktree's gitignored `downloaded_examples/` for the run; nothing under it is committed.
- Mutation check: making an open conflict not count as planned made the conflict test fail, so that test is not vacuous.

## TDD note

Task 2 was `tdd="true"`, but the gate wiring landed in the Task 1 tracer commit, so the Task 2 tests passed on first run (no separate RED commit; the fail-fast "unexpected green" case is explained by this). Task 1's tracer tests were run RED first (the Description test failed on the target assertion before the planner change).

## Deviations from Plan

**1. [Rule 3 - Blocking] Files outside the plan's list.** Tests failed under the gate that 10-19 and 10-20 had not made gate-ready. Edited: `tests/test_import_preview.py` (the `install.no_model` row test is now `test_issue_rows_no_model_is_a_blocking_error`, asserting the error row "✖ the footprint has no 3D model"), `tests/test_field_rules.py` (`_plan` now requires exactly the named `gate_errors` and a blocked plan; the three `install.manufacturer_missing` assertions became `install.atomic.manufacturer`), `tests/test_commit_plan.py`, `tests/test_customfixtures.py` and `tests/test_import_form.py` (UL installs now carry `UL_DESCRIPTION`; the field-defaults equivalence cases carry a Description and expect the exact gate errors of the UL case (description) and the SnapEDA case (datasheet)). Commit 269c2da.
**2. [Scope] Tests that kept an assertion's subject but changed their part:** `test_resolution_skip_footprint` (the kept footprint now links a model on disk, so the models folder holds `kept.step`), `test_resolution_skip_parent_symbol_keeps_the_child_linked` (extends pair carries `ATOMIC_PROPS`), `test_tracer_snapeda_end_to_end` (uses the SnapEDA zip with its model), `test_no_model_declined` (UL Description supplied so the model error stands alone), `test_fields_clear_and_restore` (a blank Datasheet now keeps Install off; the Description is typed again after it is emptied so the later Install-enabled checks still hold).
**3. [Scope] Real-sample tests.** `test_real_snapeda_installs` became `test_real_snapeda_alone_is_blocked_by_the_gate_for_its_datasheet_and_model` (blocked by `install.atomic.datasheet` and `install.atomic.model_3d`, values read from the planned symbol bytes); `test_real_vendor_installs_load_in_kicad[snapeda]` installs with the owner's Datasheet link and the separate SnapEDA model download. The model-less SnapEDA case has its own blocked-plan test in `test_vendor_install.py`.
**4. [Scope] `test_resolution_rename_invalid[footprint-*]`** now also lists `install.atomic.model_3d` (the existing footprint left on disk links no model), since the plan is judged on the footprint that stays.

Total deviations: 4, all test-only; product code changed only in `planner.py` as planned.

## Known Stubs

None.

## Threat Flags

None. T-10-25 (blocked plan refused before any write) and T-10-26 (no option bypasses the gate; the declined-model path is blocked) are both covered by tests in `tests/test_install_gate.py`.

## Self-Check: PASSED

- `grep -n "incoming_issues(" planner.py` one line; `"install.no_model"` outside comments: 0; `incoming_context(` one line; `install.atomic.model_3d` in test_install_gate.py: 2, in test_install_plan.py: 8.
- Commits c2a27ee, ac967f8 and 269c2da exist on the branch.
- tests/test_install_gate.py exists.
