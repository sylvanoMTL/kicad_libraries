---
phase: 10-importer-on-the-atomic-scheme
plan: 19
subsystem: testing
tags: [tests, atomic-gate, fixtures, install]
requires:
  - phase: 10-17
    provides: canonical Manufacturer and ti.com host inference
provides:
  - UL_DESCRIPTION and ATOMIC_PROPS in tests/installfixtures.py
  - extends_pair(props=...) for atomic parent/child test parts
  - install-path tests that install atomic parts, valid with and without the plan 10-21 gate
affects: [10-20, 10-21]
tech-stack:
  added: []
  patterns: ["a test changes its part (fields, STEP model), never what it asserts"]
key-files:
  created: []
  modified:
    - tests/installfixtures.py
    - tests/test_install_e2e.py
    - tests/test_install_plan.py
    - tests/test_install_apply.py
    - tests/test_install_options_clear.py
    - tests/test_vendor_install.py
    - tests/test_field_cleanup.py
    - tests/test_model_attach.py
key-decisions:
  - "Tests whose subject is a missing field or model keep their part; plan 10-21 rewrites them"
  - "test_vendor_install: the model-less SnapEDA case stays only where no model is the subject; noop, rollback and kicad-cli tests run on the modelled cases"
requirements-completed: [LIB-07]
duration: 70 min
completed: 2026-10-27
status: complete
commits: 2
plan_head_before: 2b82cea4d71cc44949b3f7dd10f2dafeacf6c034
plan_head_after: ad4d7baaf7ea4e656cd7f3334d8cab4366c95344
actuals:
  tokens: 14000
  tasks: 2
  commits: 2
---

# Phase 10 Plan 19: Gate-ready install-path tests Summary

Install-path tests now install parts that pass the atomic rule (Description, Manufacturer, Datasheet, STEP model), so the plan 10-21 gate can land on a green suite.

## What changed

- `tests/installfixtures.py`: `UL_DESCRIPTION = "Dual N-channel MOSFET, 30 V"`, `ATOMIC_PROPS` (Texas Instruments, "Test part", ti.com Datasheet), and an optional `props` argument on `extends_pair` (default output unchanged).
- UL-sample installs (e2e, plan, apply, options-clear, vendor) pass `description=UL_DESCRIPTION`; the e2e tests also assert the written Description (`Description` or `ki_description` by format).
- Synthetic symbols: `_members` in test_install_plan carries `ATOMIC_PROPS` and a STEP model by default (`models=()` for no-model subjects); `_vendor` symbols carry a Description; unit tests use `extends_pair(..., props=ATOMIC_PROPS)`.
- SnapEDA installs pass a Datasheet (`ATOMIC_PROPS["Datasheet"]`); the field-cleanup expected property list gains `Datasheet` at the end because the option adds the property. The e2e pin-pad package gets a STEP member.
- test_install_verify.py and zipfixtures.py needed no change: verify tests use hand-built plans that bypass build_plan and the gate.

## Verification

- A scratch probe (not committed) wrapped `build_plan` and ran the unchanged Phase 10 check (`incoming_issues`) on every unblocked plan in the ten files. Remaining flagged plans are only tests whose subject is a missing model, a stale or extra model path, a declined or skipped footprint or model, a blank or cleared field, a skipped parent symbol, or a missing manufacturer.
- `pytest -m "not wurth" -q -rs`: 2747 passed, 31 skipped (Custom submodule absent, licence-restricted samples absent). 0 failed.

## For plan 10-21 (tests that still install a non-atomic part by design)

test_install_e2e `test_sc2_no_model_package`; test_install_plan `test_choice_required_for_two_models_and_no_model_installs_without`, `test_no_model_in_package_warns`, `test_blank_option_keeps_ul_vendor_values`, `test_fields_manufacturer_missing_warns`, `test_no_model_package`, `test_no_model_declined`, `test_no_model_stale_vendor_path[*]`, `test_model_extra_blocks_warn`, `test_resolution_skip_footprint`, `test_resolution_skip_parent_symbol_keeps_the_child_linked`; test_install_options_clear `test_cleared_description_creates_empty_property`, plus the cleared datasheet/manufacturer tests; test_field_cleanup `test_protected_fields_never_dropped`; test_vendor_install `test_tracer_snapeda_end_to_end`, `test_vendor_install_links_like_ul[snapeda]`.

## Deviations from Plan

**1. [Rule 3 - Blocking] test_install_verify.py and zipfixtures.py left unchanged.** Their installs are hand-built plans, never planned by build_plan, so the gate cannot affect them.

**2. [Scope] test_vendor_install parametrisation.** noop, rollback and kicad-cli load tests moved from all three cases to the two cases whose part carries a model (`by_modelled_case`); the model-less SnapEDA case remains for the tests about having no model. This changes the part, not any assertion.

**3. [Scope] extends_pair gained an optional `props` argument** in tests/installfixtures.py so parent/child test parts can be atomic; the default output is byte-identical.

Total deviations: 3, none affecting product code.

## Known Stubs

None.

## Self-Check: PASSED

- tests/installfixtures.py has UL_DESCRIPTION and ATOMIC_PROPS; grep acceptance checks pass (e2e UL_DESCRIPTION count 9; five files list).
- Commits b826b82 and ad4d7ba exist on the branch; no product code changed.
