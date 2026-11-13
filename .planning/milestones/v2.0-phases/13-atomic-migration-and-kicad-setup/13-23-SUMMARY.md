---
phase: 13-atomic-migration-and-kicad-setup
plan: 23
subsystem: migration-window
tags: [pyside6, python-3.11, annotations, qcombobox, regression-gate, gap-closure]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: the migration window (plans 13-14 to 13-16)
provides:
  - migration_dialog imports on Python 3.10-3.13 (CommitPlan and CommitProbe bound at module level)
  - a 3.14 regression gate that reads every annotation and parses every module with the 3.10 grammar
  - a library picked from the Library dropdown list is recorded as the owner's choice
affects: [13-24, 13-25, 13-26, 13-27, 13-28]

actuals:
  tokens: 2600
  tasks: 2
  commits: 4
plan_head_before: 32f33940f3e6a0dc91cce3859cd7c9cb2295e2b3
plan_head_after: 5ec193bbee48a3fc1815752cbb33f2f2933e90a5

tech-stack:
  added: []
  patterns:
    - "Read annotations with inspect.get_annotations (eval_str=False) on the 3.14 suite to catch names that break import on 3.10-3.13"
    - "One slot (_on_library_activated) delegates to _on_library_edited so typing and picking share one path"

key-files:
  created:
    - tests/test_annotations_resolve.py
  modified:
    - kicad_lib_manager/widgets/migration_dialog.py
    - tests/test_migration_dialog.py

key-decisions:
  - "textActivated alone covers every user activation of the Library combo; currentTextChanged is not connected because it also fires on programmatic changes"
  - "No exemption list and no eval_str=True in the annotation gate: modules with from __future__ import annotations keep deliberate string hints"

requirements-completed: [MIG-02]

coverage:
  - id: D1
    description: "migration_dialog binds CommitPlan and CommitProbe, so the app imports on Python 3.10-3.13 (G-13-1-a)"
    requirement: MIG-02
    verification:
      - kind: unit
        ref: "tests/test_annotations_resolve.py#test_every_annotation_resolves"
        status: pass
      - kind: unit
        ref: "tests/test_annotations_resolve.py#test_every_module_imports"
        status: pass
    human_judgment: true
    rationale: "The suite only runs on 3.14; the owner starts the app on the Python 3.11 venv at the end-of-phase check (plan 13-28)"
  - id: D2
    description: "A Python 3.10 grammar and annotation-resolution gate over every module and the root launcher"
    requirement: MIG-02
    verification:
      - kind: unit
        ref: "tests/test_annotations_resolve.py#test_every_module_parses_as_python_3_10"
        status: pass
    human_judgment: false
  - id: D3
    description: "A library picked from the Library dropdown list (or a confirmed suggestion) reaches the plan, the badge and the draft (G-13-1-h)"
    requirement: MIG-02
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_library_picked_from_the_list_is_recorded"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-11-13
status: complete
---

# Phase 13 Plan 23: Python 3.11 start-up and dropdown library pick Summary

**Migration window imports CommitPlan and CommitProbe so the app starts on Python 3.10-3.13, a 3.14 annotation gate guards the class of defect, and a library picked from the Library dropdown list is recorded through the same path as typing.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-11-13T09:09:41Z
- **Completed:** 2026-11-13T09:12:27Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 3 (1 created)

## Accomplishments

- G-13-1-a: `from ..importer.commit_plan import CommitPlan` and `CommitProbe` in the `..importer.commit_step` import; `migration_dialog`, `help_dialog` and `main_window` no longer raise `NameError` on 3.10-3.13.
- New gate `tests/test_annotations_resolve.py`: `test_every_module_imports`, `test_every_annotation_resolves` (reads annotations of every function, class and member; asserts at least 2000 objects examined) and `test_every_module_parses_as_python_3_10` (ast `feature_version=(3, 10)` on every module and the root launcher).
- G-13-1-h: `_library_combo.textActivated` connects to the new `_on_library_activated`, which returns when no part is displayed or the recorded library already equals the text, and otherwise calls `_on_library_edited`.

## TDD record

### Task 1 (tracer)

- **RED:** `tests/test_annotations_resolve.py` committed in 7536013. Run before the import fix, `test_every_annotation_resolves` failed (1 failed, 2 passed) naming exactly two objects:
  - `kicad_lib_manager.widgets.migration_dialog._CommitStepHost._on_probe_done: name 'CommitProbe' is not defined`
  - `kicad_lib_manager.widgets.migration_dialog._CommitStepHost.start: name 'CommitPlan' is not defined`
  Semantic assessment: the target test executed and failed on the planned assertion (unbound annotation names), the package was imported from the worktree, and nothing else was flagged.
- **GREEN:** b93afc4 adds the two imports. The verify command passed: 107 passed (above the 107 required).
- **Tracer gate:** the tracer `<verify>` is automated-only and was re-run end to end after the commit (107 passed) before expanding to Task 2.

### Task 2

- **RED:** d67c5c7. `test_library_picked_from_the_list_is_recorded` failed with `KeyError` on `dialog._choices.parts[KEY_A]` after `textActivated` was emitted (no slot connected, so the pick was never recorded). Semantic assessment: the failure is on the planned assertion; the refill guard assertions before it passed.
- **GREEN:** 5ec193b connects the signal and adds the slot. The verify command passed: 119 passed; `tests/test_migration_dialog.py` alone 16 passed (the plan requires at least 16).
- **REFACTOR:** none.

## Task Commits

1. Task 1 RED: 7536013 `test(13-23)` add failing annotation, import and 3.10 grammar gate
2. Task 1 GREEN: b93afc4 `fix(13-23)` import CommitPlan and CommitProbe in the migration window
3. Task 2 RED: d67c5c7 `test(13-23)` add failing test for a library picked from the dropdown list
4. Task 2 GREEN: 5ec193b `fix(13-23)` record a library picked from the migration window's dropdown list

## Files Created/Modified

- `tests/test_annotations_resolve.py` - import, annotation and Python 3.10 grammar gate over the package.
- `kicad_lib_manager/widgets/migration_dialog.py` - the two imports, the `textActivated` connection and `_on_library_activated`.
- `tests/test_migration_dialog.py` - `test_library_picked_from_the_list_is_recorded` and the `library_badge` import.

## Decisions Made

- `textActivated` only (not `currentTextChanged`): it fires for every user activation including Return in the line edit and never for `clear`/`addItems`/`setEditText` in `_display_part`.
- The annotation gate has no exemption list and uses `eval_str=False`, as the plan's scope note requires.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The 3.11 start-up itself is not run here (this plan never runs anything from the main checkout); it is the owner's end-of-phase check in plan 13-28 Task 2.

## Known Stubs

None.

## Threat Flags

None. No new network, auth or file-access surface; the new tests import modules and build dialogs under `tmp_path` with fake cores and never touch the live `Custom/` or the owner's KiCad configuration.

## Next Phase Readiness

Plan 13-26 can rely on a list pick recording the library choice. The full suite was not run (plan 13-28 owns it); only the named test files ran: 119 passed.

## Self-Check: PASSED

- FOUND: tests/test_annotations_resolve.py
- FOUND commits: 7536013, b93afc4, d67c5c7, 5ec193b
- Acceptance greps: the commit_plan import, `CommitProbe,` in the commit_step import, 3 test defs and `feature_version=(3, 10)` in the gate file, the `textActivated.connect` line, `def _on_library_activated` and the new test all found.
