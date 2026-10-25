---
phase: 07-snapeda-and-samacsys-adapters
plan: 07
subsystem: importer
tags: [snapeda, 3d-model, intake, import-dialog, pyside6, gap-closure]

requires:
  - phase: 03-import-core
    provides: "open_package hostile-zip refusals and caps, ModelItem, build_plan / apply_plan contract"
  - phase: 05-import-dialog
    provides: "ImportDialog, TaskWorker, ImportCore"
provides:
  - "open_model_source: model-only zip intake and bare .step/.stp/.wrl read in place"
  - "attach_models: merge a second source's magic-checked models into an ImportCandidate"
  - "Add 3D model... button on the Import dialog 3D model row"
  - "synthetic SnapEDA model download fixture (snapeda_model_zip)"
affects: [07-08, 07-09]

actuals:
  tokens: 15000
  tasks: 3
  commits: 5

plan_head_before: 1135ce8f10bf8147d513a56488433640efe02fd0
plan_head_after: 7bf21bd8df281247e396906d3bf7b00c81a3bd3d

tech-stack:
  added: []
  patterns:
    - "second intake source: a kinds filter on _open_zip/_stage_zip instead of a parallel zip reader"
    - "module-level _lstat indirection so tests stub one name, never the os module"
    - "model packages held by the dialog until Change.../close, so rebuilds and apply_plan can still read them"

key-files:
  created:
    - tests/test_model_source.py
    - tests/test_model_attach.py
  modified:
    - kicad_lib_manager/importer/package.py
    - kicad_lib_manager/importer/adapters/base.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/vendorfixtures.py
    - tests/test_import_dialog.py

key-decisions:
  - "open_package unchanged: the new keyword-only kinds filter defaults to None (all stage kinds)"
  - "Per-package byte budget for each model source, accepted as T-07-26"
  - "attach_models sits in adapters/base.py beside locate so the same _check_model magic check is used with no private name crossing modules"
  - "Add 3D model... button sits under the model label/combo (vertical slot), not beside it"

requirements-completed: [FMT2-02, INTK-03]

coverage:
  - id: D1
    description: "A SnapEDA CAD zip plus a separately downloaded model zip installs a model linked as ${CUSTOM_3DMODEL_DIR}/<MPN>.stp through the real dialog"
    requirement: FMT2-02
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_tracer_snapeda_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "open_model_source stages only models from a zip with every Phase 3 refusal, and reads a bare model in place behind link, handle and size checks"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_model_source.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "attach_models attaches only magic-valid, non-duplicate models with unique filenames; the attached model installs, re-plans as a no-op, and is refused cleanly when its source changed or closed"
    requirement: FMT2-02
    verification:
      - kind: unit
        ref: "tests/test_model_attach.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Add 3D model... button placement and feel in the dialog (the visible failure note is added by plan 07-08)"
    verification: []
    human_judgment: true
    rationale: "Layout and ergonomics of the new button are a visual judgment; the UAT retest of G-07-2 covers it"

duration: resumed after an authentication cut-off
completed: 2026-10-23
status: complete
---

# Phase 7 Plan 07: Separate SnapEDA 3D model Summary

**A separately downloaded SnapEDA model (bare .stp/.step/.wrl or a zip holding one) can be added to an open import via "Add 3D model..." and installs as `Custom/3DModels/<MPN>.stp` linked as `${CUSTOM_3DMODEL_DIR}/<MPN>.stp`, with the plan contract untouched.**

## Performance

- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 7 (2 new test modules)
- **Commits:** 5 task commits plus this metadata commit

## Accomplishments

- `open_model_source(path, repo_root, progress)` in `package.py`: a `.zip` goes through the existing `_open_zip` with a new keyword-only `kinds` filter, so only `.step/.stp/.wrl` are staged and everything else is listed in one "Not imported from ..." INFO; a zip with no model is refused (`intake.no_model_in_source`) and its staging folder removed. A bare model file is read in place after a no-follow `_lstat` (module-level indirection), refusing symlinks, junctions and reparse points (`intake.link_refused`), folders and other suffixes (`intake.unsupported`), oversize files (`intake.too_large`, also on real counted bytes), and a handle whose `(st_dev, st_ino)` differs from the lstat result.
- `attach_models(candidate, model_package)` in `adapters/base.py`: runs the same `_check_model` magic check as `locate`, skips a model whose SHA-256 is already on the candidate (INFO `intake.model_already_present`), renames casefolded filename clashes to `<stem>_<n><ext>`, drops `intake.no_model`, adds INFO `intake.model_attached` naming only file names, and never mutates its input.
- Import dialog: an "Add 3D model..." button on the 3D model row runs `open_model_source` + `attach_models` on a `TaskWorker`, refreshes only the model label/combo (no edit state wiped), rebuilds the plan, and keeps attached packages open until Change.../a new open/close.
- Frozen contract verified: `plan.py`, `planner.py`, `applier.py`, `commit_plan.py`, `preview.py`, `candidate.py` are byte-identical to `c2b75c8`.

## TDD Gate Compliance

Task 2 and Task 3 each have a RED commit before the GREEN commit. RED evidence was classified with `gsd check tdd-red-evidence` (JUnit XML from pytest), verdict `RED_EVIDENCE_OK`.

- Task 2 RED (`1c7ce7c`): 7 failing tests, all the bare-file branch (`test_bare_model_read_in_place` x3, `..._reparse_point_refused`, `..._handle_mismatch_refused`, `..._oversize_refused`, `..._grown_after_listing_refused`), each returning `intake.unsupported` where the planned code was expected. Semantic assessment: target ran and failed on the planned assertion for the intended reason. The model-zip tests already passed at RED, because the tracer (Task 1) had implemented the zip branch by reusing `_open_zip`; they are regression guards, not new behaviour.
- Task 2 GREEN (`d09e830`).
- Task 3 RED (`09ef7ed`): 2 failing tests, `test_attach_filename_clash` and `test_attach_duplicate_sha`. Semantic assessment: both fail because the rules did not exist yet (attached with the same name / attached a duplicate). The other attach/install tests passed at RED because the happy path came from Task 1 and the plan contract already supports an attached model.
- Task 3 GREEN (`7bf21bd`).
- No REFACTOR commit.

## Task Commits

1. **Task 1: tracer, SnapEDA CAD zip + separate model zip -> Add 3D model... -> Install** - `0c9cd0b` (feat)
2. **Task 2: bare model file and hostile-zip coverage** - `1c7ce7c` (test), `d09e830` (feat)
3. **Task 3: attach_models clash and duplicate rules** - `09ef7ed` (test), `7bf21bd` (feat)

**Plan metadata:** the commit that adds this file (docs).

## Files Created/Modified

- `kicad_lib_manager/importer/package.py` - `open_model_source`, `_open_model_file`, `_narrow`, `kinds` filter, `_lstat`, `MODEL_SOURCE_KINDS`
- `kicad_lib_manager/importer/adapters/base.py` - `attach_models`, `_unique_name`
- `kicad_lib_manager/widgets/import_dialog.py` - `ImportCore` fields, `ModelOutcome`, model row builder/refresh, attach worker handlers, model package lifetime
- `tests/vendorfixtures.py` - `snapeda_model_members`, `snapeda_model_zip`, `SNAPEDA_MODEL_*` constants (synthetic only)
- `tests/test_import_dialog.py` - `test_add_model_tracer_snapeda_end_to_end`
- `tests/test_model_source.py`, `tests/test_model_attach.py` - new suites

## Decisions Made

- `kinds` is keyword-only with default `None`, so `open_package` is behaviourally unchanged.
- Each model source gets its own budget and staging folder (T-07-26, accepted).
- The dialog keeps a list of model packages and never closes one before Change.../a new open/close, because a rebuild or `apply_plan` may still read it (WR-04).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Add 3D model... button beside the combo broke the left-pane geometry**
- **Found during:** Task 1, running the full dialog suite
- **Issue:** The plan's horizontal row (label/combo + button in a `QHBoxLayout`) made the row 396 px wide at the test font, wider than the 364 px viewport. `test_fields_long_text_geometry` failed (`524 <= 364`). This was a regression from my change, not a pre-existing failure; it passed on the base.
- **Fix:** The model slot is a `QVBoxLayout`; the button sits under the label/combo, left-aligned, like "Make linked". `_model_slot` is therefore a `QVBoxLayout`, not the plan's `QHBoxLayout`.
- **Files modified:** `kicad_lib_manager/widgets/import_dialog.py`
- **Verification:** dialog suite 136 passed, 9 skipped (excluding the two documented Custom-dependent ids)
- **Committed in:** `0c9cd0b`

**2. [Rule 2 - Missing critical] Stale-attach guard**
- **Found during:** Task 1
- **Issue:** An attach result arriving after Change..., a new open, an install, or when the Result page is shown would otherwise attach to the wrong or finished import.
- **Fix:** `_on_model_attached` closes the package and returns when closing, the session changed, no candidate is open, an install runs, or the Edit page is not current. `_shutdown` also closes an unhandled `ModelOutcome` package, and `_reap` keeps a `ModelOutcome` value for that.
- **Committed in:** `0c9cd0b`

**Total deviations:** 2 (1 bug, 1 missing critical). **Impact:** no scope change.

## Issues Encountered

- Session was cut off by an authentication error after Task 1's commit and resumed. The "one failure in the dialog suite" seen just before the cut-off was deviation 1 above (my own regression, already fixed in `0c9cd0b`); it is not pre-existing.
- Pre-existing, unrelated failures in this worktree (real `kicad-cli` KiCad 10 writes symbol format 20251024 where tests expect 20241209): `tests/test_install_plan.py::test_version_real_cli_into_20241209`, `::test_library_real_cli_new_header`, `::test_noop_second_plan_after_normalised_apply`, and `tests/test_kicad_cli.py::test_real_cli_upgrades_ul_symbol_deterministically`. Full suite: 4 failed, 1822 passed, 90 skipped. Baseline of the touched suites before any edit: 300 passed, 12 skipped.
- Skips here: tests that need the `Custom` submodule (empty in the worktree) and `test_bare_model_symlink_refused` (symlink privilege not held on this Windows account; the reparse-bit and handle-mismatch tests cover the same refusal without privileges).
- The plan's `<verify>` for the symlink test names `pkg._lstat` in a count grep; the tests patch it as `monkeypatch.setattr(pkg, "_lstat", ...)`, so the string `pkg._lstat` occurs only in the module docstring. The intent (no patch of the os module, `_lstat` indirection present) holds.

## Known Stubs

None. Plan 07-08 adds the visible note when an attach finds nothing usable; for now such a result is only logged through `issues_logged` (noted in the code).

## Threat Flags

None beyond the plan's threat model (T-07-20..T-07-26 mitigated or accepted as written).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for plan 07-08 (visible attach-failure note) and 07-09 (docs: PROJECT.md Out of Scope and REQUIREMENTS FMT2-02). UAT test 2 (G-07-2) should be re-run by the owner with a real SnapEDA CAD zip plus its model download.

## Self-Check: PASSED

- Created files exist: `tests/test_model_source.py`, `tests/test_model_attach.py`, this SUMMARY.
- Commits present on this branch: `0c9cd0b`, `1c7ce7c`, `d09e830`, `09ef7ed`, `7bf21bd`.
- Frozen-contract `git diff --quiet c2b75c8 -- <six modules>` exits 0.

---
*Phase: 07-snapeda-and-samacsys-adapters*
*Completed: 2026-10-23*
