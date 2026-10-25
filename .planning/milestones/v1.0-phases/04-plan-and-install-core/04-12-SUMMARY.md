---
phase: 04-plan-and-install-core
plan: 12
subsystem: importer
tags: [planner, candidate, install-options, issues, gap-closure, tdd]

requires:
  - phase: 04-plan-and-install-core
    provides: build_plan / apply_plan / InstallOptions (plans 04-01 to 04-10)
provides:
  - detect_candidate folds Package.issues into ImportCandidate.issues (package first, de-duplicated)
  - InstallOptions treats blank text overrides as not set (None)
affects: [04-13, phase-05-preview-form]

actuals:
  tokens: 9000
  tasks: 2
  commits: 4
plan_head_before: 9c5c47f5bb733a43459a4f4be52ed97bc9508f43
plan_head_after: bebcbe8feefcb600de36f16c955d8cf301184276
commits: 4

tech-stack:
  added: []
  patterns:
    - "ImportCandidate.issues is the single carrier of every intake Issue; build_plan(package_issues=) is an optional extra input"
    - "Frozen option dataclass normalises caller text in __post_init__ via object.__setattr__"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/detect.py
    - kicad_lib_manager/importer/candidate.py
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/plan.py
    - tests/test_install_plan.py
    - tests/test_install_e2e.py

key-decisions:
  - "Package.issues are folded into the candidate inside detect_candidate; the list returned beside the candidate stays detection-only so no caller sees an Issue twice (WR-03)"
  - "Blank (empty or whitespace-only) Value/Datasheet/Description/Manufacturer/MPN means not set; no clear sentinel in Phase 4 (WR-05, user decision 2026-10-20)"

requirements-completed: []  # INTK-08 and INST-04 await phase re-verification; nothing marked complete by this plan

coverage:
  - id: D1
    description: "A package-level Issue (depth-limit WARNING, ignored-members INFO) reaches plan.issues and InstallResult.issues with no caller forwarding"
    requirement: INTK-08
    verification:
      - kind: e2e
        ref: "tests/test_install_e2e.py#test_package_issue_reaches_install_result_from_a_folder"
        status: pass
      - kind: e2e
        ref: "tests/test_install_e2e.py#test_package_issue_reaches_install_result_from_a_zip"
        status: pass
      - kind: unit
        ref: "tests/test_install_plan.py#test_candidate_carries_package_issues"
        status: pass
    human_judgment: false
  - id: D2
    description: "A blank override in InstallOptions keeps the vendor Value, Datasheet, MPN, Manufacturer and the <MPN> model file name"
    requirement: INST-04
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_blank_options_mean_not_set"
        status: pass
      - kind: unit
        ref: "tests/test_install_plan.py#test_blank_option_keeps_ul_vendor_values[empty]"
        status: pass
      - kind: unit
        ref: "tests/test_install_plan.py#test_blank_option_keeps_ul_vendor_values[spaces]"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-10-20
status: complete
---

# Phase 4 Plan 12: Package Issues and Blank Options Summary

**detect_candidate now carries Package.issues into ImportCandidate.issues so intake warnings reach InstallResult.issues unforwarded, and a blank InstallOptions text field means "not set" so vendor Value/Datasheet/MPN/Manufacturer survive an untouched form.**

INTK-08 and INST-04 await phase re-verification; no requirement is marked complete here.

## Performance

- **Duration:** about 20 min
- **Started:** 2026-10-20T10:35:00Z (approx)
- **Completed:** 2026-10-20T10:52:12Z
- **Tasks:** 2
- **Files modified:** 6 (4 source, 2 test)

## Accomplishments

- WR-03: `detect_candidate` replaces the candidate's `issues` with `dict.fromkeys((*package.issues, *candidate.issues))`. Order is package Issues, unknown-vendor note, locate Issues, each once. The second return value (detection Issues) is unchanged. `build_plan` keeps `package_issues=` as an optional extra and already de-duplicates, so passing both is harmless.
- WR-05: `InstallOptions.__post_init__` turns an empty or whitespace-only `value`, `datasheet`, `description`, `manufacturer`, `mpn` into None (`_TEXT_OVERRIDES`). Text is kept exactly as typed otherwise; `library`, `symbol`, `model`, `footprints` and `footprint_names` are untouched. planner.py needed no code change for this.
- Proven end to end: a folder package one level too deep gives a WARNING `intake.depth_limit` that appears once in `plan.issues` and `result.issues`; the UL zip's INFO `intake.ignored_members` does the same. On the UL sample, all-blank options (empty and spaces) give `plan.ops` identical to unset options, model file `CSD85301Q2.stp`, and no added description property.

## TDD Gate Compliance

- **Task 1 RED** (`f9d0cc5`): three new tests failed on the intended assertion (package Issue missing from `candidate.issues`, `plan.issues`, `result.issues`); the existing `test_package_issues_come_first_then_candidate_issues` passed. Semantic assessment: failures were assertion failures on the planned behaviour, not import/fixture errors.
- **Task 1 GREEN** (`d33fa20`): all four named tests pass; the Phase 3 detection tests plus layering test pass (133 passed, 1 skipped for a Windows symlink privilege).
- **Task 2 RED** (`6ce4d2a`): all three tests failed on the planned assertions (fields stayed `""`, UL ops differed, whitespace blank blocked the plan with `install.invalid_name`).
- **Task 2 GREEN** (`bebcbe8`): the three tests pass.
- No REFACTOR commit was needed.
- The RED evidence classifier (`gsd_run check tdd-red-evidence`) was not run; RED was judged by reading the pytest assertion output directly.

## Task Commits

1. **Task 1 (tracer): package Issues reach InstallResult** - `f9d0cc5` (test), `d33fa20` (feat)
2. **Task 2: blank options mean not set** - `6ce4d2a` (test), `bebcbe8` (feat)

**Plan metadata:** committed separately as `docs(04-12): complete package-issues and blank-options plan`.

## Files Created/Modified

- `kicad_lib_manager/importer/detect.py` - folds `package.issues` into the candidate, documents the ordering
- `kicad_lib_manager/importer/candidate.py` - `ImportCandidate` docstring stating the issues contract (WR-03)
- `kicad_lib_manager/importer/planner.py` - `build_plan` docstring and WR-03 comment only; no code change
- `kicad_lib_manager/importer/plan.py` - `_TEXT_OVERRIDES`, `InstallOptions.__post_init__`, docstring
- `tests/test_install_plan.py` - `test_candidate_carries_package_issues`, `test_blank_options_mean_not_set`, `test_blank_option_keeps_ul_vendor_values[empty|spaces]`
- `tests/test_install_e2e.py` - the folder and zip e2e proofs; imports `MAX_FOLDER_DEPTH`

## Decisions Made

- Fold package Issues into the candidate in `detect_candidate` rather than require callers to forward them; keep the `package_issues` keyword for extra Issues.
- Blank text means "not set" with no sentinel (user decision 2026-10-20, "Blank = not set; defer clear").

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The worktree has no `Custom/` submodule contents, so the e2e tests and `custom_copy` tests would skip. To get real proof, I temporarily copied `Symbols/`, `Footprints/` and `3DModels/` from the main checkout (read-only source) into the worktree's `Custom/`, ran the full suite there, then deleted the copy. Result: `1327 passed, 5 skipped` (skips: manual UAT env var, Windows symlink privilege, three WurthElektronik submodule tests). `git status` was clean before and after. The orchestrator should still run the full suite on the merged tree.
- Sibling plan 04-11 owns `applier.py` and `tests/test_install_apply.py`; neither was touched. The full suite run here used the pre-04-11 applier.

## Deferred to Phase 5

User decision of 2026-10-20: **"Blank = not set; defer clear."**

- In Phase 4 an empty or whitespace-only Value, Datasheet, Description, Manufacturer or MPN means "not set, keep the vendor value". There is no clear sentinel.
- PREV-04 lets the user edit these fields in the preview, and emptying a field is an edit, so PREV-04 can ask for an explicit "clear this field" outcome where the installed property ends up empty. That outcome is a Phase 5 preview decision.
- Reason: Phase 5 owns the form and its design of how vendor values are shown (a clear control, a tri-state field, or a pre-filled field the user empties), and an untouched Qt line edit returns `""`, which must mean not set.
- Until Phase 5 decides, a deliberate blank edit installs the vendor value. This is the recorded outcome (threat T-04-41, transferred), not an accident.

## Known Stubs

None.

## Threat Flags

None. No new network, auth, file-access or schema surface.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 04-13 can record review dispositions for WR-03 and WR-05 once 04-11 has also landed.
- Phase 5 planning must pick up the "clear this field" decision above.

## Self-Check: PASSED

- Files modified exist: detect.py, candidate.py, planner.py, plan.py, test_install_plan.py, test_install_e2e.py (all present).
- Commits `f9d0cc5`, `d33fa20`, `6ce4d2a`, `bebcbe8` are ancestors of HEAD.
- Named verify tests and the full suite passed (with a temporary Custom/ copy, since removed).

---
*Phase: 04-plan-and-install-core*
*Completed: 2026-10-20*
