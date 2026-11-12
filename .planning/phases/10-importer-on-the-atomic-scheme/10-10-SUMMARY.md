---
phase: 10-importer-on-the-atomic-scheme
plan: 10
subsystem: importer
tags: [atomic-naming, build_plan, name-rule, form, pyside6]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "stems.name_verdict / allowed_stems / installed_stems (10-01), Atomic_ fixtures (10-02), migrated tests (10-07 to 10-09)"
provides:
  - "build_plan refuses every library name name_verdict refuses (install.invalid_library, plain reason, no ops)"
  - "ToolContext.allowed_stems and ToolContext.kicad_footprints_dir, filled by detect_tools"
  - "FormStatus.allowed and a verdict-based library reason in blocking_reasons"
  - "tests/test_atomic_targets.py"
affects: [10-11, 10-12, 10-15]

actuals:
  tokens: 26000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "build_plan is the authority for the name rule, the form only explains it with the same verdict text"

key-files:
  created:
    - tests/test_atomic_targets.py
  modified:
    - kicad_lib_manager/importer/plan.py
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/form.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_install_plan.py
    - tests/test_import_form.py
    - tests/test_import_dialog.py

key-decisions:
  - "A case variant such as atomic_transistor_fet is refused by the verdict, never installed under a different spelling; the case-clash check now only fires for an allowed name with a lower-case twin already on disk"
  - "The install.placeholder_library code is no longer produced; the dead branch in form._issue_target was removed"

requirements-completed: [LIB-05]

coverage:
  - id: D1
    description: "build_plan refuses any non-Atomic_ or invented library name with the verdict's plain reason and no file operations; Atomic_Transistor_FET builds"
    requirement: LIB-05
    verification:
      - kind: unit
        ref: "tests/test_atomic_targets.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "An existing v1 library and a case variant are refused like any other non-Atomic_ name"
    requirement: LIB-05
    verification:
      - kind: unit
        ref: "tests/test_atomic_targets.py#test_an_existing_v1_library_is_refused_like_any_other_name"
        status: pass
    human_judgment: false
  - id: D3
    description: "ToolContext carries allowed_stems and kicad_footprints_dir, filled by detect_tools"
    requirement: LIB-05
    verification:
      - kind: unit
        ref: "tests/test_atomic_targets.py#test_detect_tools_fills_the_footprints_folder_and_the_allowed_stems"
        status: pass
    human_judgment: false
  - id: D4
    description: "The form's library reason is the verdict reason (target library) and the duplicate plan error is not listed twice; the dialog passes the detected tools' allowed stems"
    requirement: LIB-05
    verification:
      - kind: unit
        ref: "tests/test_atomic_targets.py, tests/test_import_form.py, tests/test_import_dialog.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "The not-wurth suite is green on the name rule"
    verification:
      - kind: integration
        ref: "pytest -m 'not wurth' -q: 2595 passed, 30 skipped"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-10-27
status: complete
plan_head_before: d571953dcd7f486e088bfdb665bd4095e06fc84e
commits: 2
---

# Phase 10 Plan 10: Name rule in build_plan and the form Summary

**build_plan is now the authority for the Atomic_ name rule: any name the verdict refuses (bare KiCad name, v1 name, case variant, empty) stops the plan with the verdict's plain reason before anything is read, and the form shows the same sentence against the library field.**

## Performance

- **Duration:** about 40 min (most of it the 9 min full-suite run)
- **Tasks:** 2
- **Files modified:** 8 (1 created)

## Accomplishments
- `build_plan` replaced the placeholder and sanitize refusals with one `stems.name_verdict(library, tools.allowed_stems or None)` check; the refusal is `install.invalid_library` carrying the verdict reason, with no ops, so `apply_plan` refuses it too (T-10-03).
- `ToolContext` gained `kicad_footprints_dir` and `allowed_stems`; `detect_tools` fills them from the detected KiCad footprints folder (installed symbol stems unioned with the KiCad 10 snapshot; empty means the snapshot).
- `FormStatus.allowed` was added; `blocking_reasons` gives one `Reason(verdict.reason, "library")` and treats the planner's `install.invalid_library` as explained, so it is not listed twice. The dialog passes the detected tools' allowed stems.
- `tests/test_atomic_targets.py` (17 tests) covers refusal through build_plan, the Atomic_Transistor_FET success path, every synthetic v1 library name, the case variant, the form reason and dedup, `detect_tools`, and that every Atomic_ constant in `customfixtures.py` / `zipfixtures.py` passes the verdict.
- The tests that used a refused name on purpose now assert the name rule (see Task Commits).

## Task Commits

1. **Task 1: name rule from the verdict through build_plan to the form reason** - `518d869` (feat)
2. **Task 2: refusal tests assert the name rule** - `152eb45` (test)

## Files Created/Modified
- `kicad_lib_manager/importer/plan.py` - `ToolContext.kicad_footprints_dir`, `ToolContext.allowed_stems`
- `kicad_lib_manager/importer/planner.py` - name check in `build_plan`, `detect_tools` fills the new fields, unused `placeholder_tokens` import removed
- `kicad_lib_manager/importer/form.py` - `FormStatus.allowed`, verdict-based library reason, dead placeholder branch removed
- `kicad_lib_manager/widgets/import_dialog.py` - `_form_status` passes `allowed`
- `tests/test_atomic_targets.py` - new
- `tests/test_install_plan.py`, `tests/test_import_form.py`, `tests/test_import_dialog.py` - refusal tests rewritten

## Decisions Made
- Case-clash tests now put a lower-case twin on disk (for example `atomic_analog`) and pass the exact allowed name, since the lower-case request itself is refused by the verdict (plan instruction, D-11).
- Dialog tests that open a SnapEDA package without a suggestion override now pass `suggest_library=_good_suggestion`, because the real suggestion is still a v1 name until plan 10-15.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Two SnapEDA dialog tests needed an allowed suggestion**
- **Found during:** Task 2 (full dialog test run)
- **Issue:** `test_add_model_tracer_snapeda_end_to_end` and `test_preview_columns_fit_at_900_and_1400` opened the dialog with the real (v1-named) suggestion; the plan is now refused, so the model file and the Field changes section were absent. These were targets missed by plans 10-07 to 10-09.
- **Fix:** passed `suggest_library=_good_suggestion` (Atomic_Battery_Management), as the other dialog tests do.
- **Files modified:** tests/test_import_dialog.py
- **Verification:** `pytest tests/test_import_dialog.py` 174 passed; full not-wurth run green
- **Committed in:** 152eb45

**2. [Rule 1 - Cleanup] Removed the dead `install.placeholder_library` branch from `form._issue_target`**
- **Found during:** Task 1
- **Issue:** the planner no longer emits that code, and the plan's acceptance wants no references in the tests
- **Fix:** dropped it from the tuple and updated the `blocking_reasons` docstring
- **Committed in:** 518d869

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 cleanup)
**Impact on plan:** none on scope.

## Issues Encountered
None. The 30 skips in the full run are all environmental (Custom submodule not checked out, licence-restricted vendor samples absent, no symlink privilege, UAT env var) and fall under the worktree notes, not new skips.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Between this plan and plan 10-15 the dialog's pre-filled suggestion is a v1 name and shows the refusal reason (flagged assumption in the plan); the owner types an Atomic_ name meanwhile.
- `git -C Custom status` could not be compared (the submodule is not checked out in this worktree); the suite's live-Custom guard did nothing here and the orchestrator's post-merge run covers it.

## Known Stubs
None.

## Self-Check: PASSED
- tests/test_atomic_targets.py found; commits 518d869 and 152eb45 are ancestors of HEAD
- All acceptance criteria re-run: `stems.name_verdict(library` in planner (1 line), 0 non-comment `placeholder_tokens` in planner, `allowed_stems: frozenset[str] = frozenset()` in plan.py, `allowed=self._tools.allowed_stems` in import_dialog.py, 17 passed in test_atomic_targets.py, 0 `install.placeholder_library` in the two test files
- Wave gate: `pytest -m "not wurth" -q` gave 2595 passed, 30 skipped, 0 failed

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*
