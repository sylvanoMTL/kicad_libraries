---
phase: 10-importer-on-the-atomic-scheme
plan: 06
subsystem: importer
tags: [atomic-check, kicad, install-gate, python]

requires:
  - phase: 09
    provides: atomic_check.check_symbol, ATOMIC_RULES and repo_context (the one atomic rule set)
  - phase: 10-01
    provides: importer layering registration for importer.incoming
provides:
  - "repo_context(..., *, planned_footprints, planned_models): the Phase 9 check sees a footprint and 3D models a plan is about to write"
  - "importer/incoming.py: incoming_context and incoming_issues (coded ERROR and INFO Issues for the planner and form)"
affects: [10-planner, 10-form, install-gate]

actuals:
  tokens: 9000
  tasks: 2
  commits: 2
plan_head_before: b4f956441ef5cab68b1bc6efe104c5a92c09da70
plan_head_after: 36c75de

tech-stack:
  added: []
  patterns:
    - "Planned bytes keyed by exact link; a planned link or model counts only on an exact match"
    - "Immutable MappingProxyType default for the planned_footprints keyword"

key-files:
  created:
    - kicad_lib_manager/importer/incoming.py
    - tests/test_incoming_check.py
  modified:
    - kicad_lib_manager/atomic_check.py

key-decisions:
  - "Planned footprint bytes go through the same size cap and parse path as disk files, with the verdict cache keyed by the planned path"
  - "incoming_issues emits each name's errors then its notes in name order; only the last name (the part itself) has no prefix"

requirements-completed: [LIB-07]

coverage:
  - id: D1
    description: "repo_context judges a planned footprint and planned model names as if already written, with exact-name matching, and behaves as in Phase 9 when called without them"
    requirement: LIB-07
    verification:
      - kind: unit
        ref: "tests/test_incoming_check.py#test_a_planned_part_with_its_planned_footprint_and_model_passes"
        status: pass
      - kind: unit
        ref: "tests/test_atomic_check.py tests/test_atomic_scan.py tests/test_atomic_fixes.py (unchanged, 0 failed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "incoming_issues returns one coded ERROR per broken rule in rule order, INFO notes for unknown manufacturers, and parent names prefixed"
    requirement: LIB-07
    verification:
      - kind: unit
        ref: "tests/test_incoming_check.py#test_a_part_failing_several_rules_gives_one_error_each_in_rule_order"
        status: pass
      - kind: unit
        ref: "tests/test_incoming_check.py#test_a_child_without_its_own_mpn_is_named_last_and_its_parent_is_prefixed"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 06: Incoming atomic check Summary

**The unchanged Phase 9 atomic check now judges a part from the footprint and 3D model bytes a plan carries, via `repo_context(planned_footprints, planned_models)` and a Qt-free `importer/incoming.py` that returns coded `install.atomic.<rule>` ERRORs and `install.atomic_note.<kind>` INFOs.**

## Performance

- **Duration:** about 20 min
- **Tasks:** 2
- **Files modified:** 3 (1 modified, 2 created)

## Accomplishments

- `repo_context` takes keyword-only `planned_footprints` (link to repo-relative path and bytes) and `planned_models` (exact file names). A planned link resolves before the on-disk listing, its model is judged from the planned bytes under the same size and node caps, and `custom_model_names()` is the on-disk set unioned with the planned names. Called without them it behaves exactly as before.
- `importer/incoming.py` adds `incoming_context` (footprint libraries from the exact `.pretty` names in Custom/Footprints plus KiCad's) and `incoming_issues` (runs `check_symbol(..., fixable=False)` per name; parent names prefixed, the last name unprefixed).
- 18 tests pin the tracer (pass with planned model, exactly one `model_3d` error without), each rule's text, rule order, the unknown-manufacturer note, parent ordering, the official KiCad footprint with its `${KICAD10_3DMODEL_DIR}` model, an existing shared footprint, and exact-case matching of planned links and models.

## Task Commits

1. **Task 1: tracer (planned part, footprint and model pass the unchanged check)** - `f32d480` (feat)
2. **Task 2: every rule, the parent symbol, the official and the shared footprint** - `36c75de` (test)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `kicad_lib_manager/atomic_check.py` - `repo_context` planned footprint/model extension (stdlib imports only: `Collection`, `Mapping`, `MappingProxyType`)
- `kicad_lib_manager/importer/incoming.py` - `incoming_context`, `incoming_issues`
- `tests/test_incoming_check.py` - the incoming check on planned bytes, rule by rule

## Decisions Made

- The tracer was verified end to end with the targeted suite (`test_incoming_check`, `test_atomic_check`, `test_atomic_scan`, `test_layering`, `test_importer_layering`: 170 passed) before expanding.
- `incoming_issues` orders output per name (errors, then notes), so a parent's issues come before the child's.

## Deviations from Plan

None - plan executed exactly as written.

Note on Task 2 (`tdd="true"`): the behavior rows were all already satisfied by Task 1, because `incoming_issues` reuses the unchanged `check_symbol`. The tests were green on first run, so there is no separate RED commit and no GREEN `feat` commit for Task 2, and the plan is `type: execute`, not `type: tdd`. The tests assert exact codes and texts (not just counts), so they fail if the reuse is broken or the exact-name rules are loosened.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. T-10-12 (exact-match planned entries) and T-10-13 (size cap on planned bytes, verdicts cached by path) are implemented as planned; the case-mismatch tests pin T-10-12.

## Self-Check: PASSED

- `kicad_lib_manager/importer/incoming.py`, `tests/test_incoming_check.py` exist; `f32d480` and `36c75de` are ancestors of HEAD.
- `tests/test_incoming_check.py tests/test_atomic_check.py tests/test_atomic_scan.py tests/test_atomic_fixes.py tests/test_layering.py tests/test_importer_layering.py`: 240 passed. The full `-m "not wurth"` suite is left to the orchestrator's post-merge run.
