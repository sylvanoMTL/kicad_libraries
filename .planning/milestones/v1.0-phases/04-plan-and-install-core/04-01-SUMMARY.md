---
phase: 04-plan-and-install-core
plan: 01
subsystem: importer
tags: [kicad, s-expression, install-plan, transaction, rollback, pytest]

requires:
  - phase: 01-foundation
    provides: sexpr span splices, fsutil atomic writes and backups, kicad_files read side
  - phase: 03-package-intake-and-naming
    provides: ImportCandidate, naming.sanitize_*, suggest.placeholder_tokens, RepoLayout
provides:
  - "kicad_files write side: footprint name/value edits, model block insert, property clone, symbol splice"
  - "importer.plan contract: ToolContext, Resolution, InstallOptions, FileOp, Conflict, Rename, InstallPlan, InstallResult"
  - "build_plan with the Phase 3 D-04 placeholder refusal, D-17 item choice, WR-04 and WR-05"
  - "apply_plan: path containment, source hash check, app-data backup, ordered atomic writes, verify, undo"
  - "verify_install hard checks read back from disk with exact-case listings"
  - "tests/conftest.py fixtures custom_copy, ul_package, snapshot"
affects: [04-02, 04-03, 04-04, 04-05, 04-06, 04-07, 04-08, 04-09, 04-10, 05-preview-and-install-ui, 06-git-and-registration]

actuals:
  tokens: 15800
  tasks: 2
  commits: 3

plan_head_before: fc65f8464a3757c4ce792c2566d614ccc9c4e229
plan_head_after: 3483d0d6132e819cf2562ae8ec3a4bbf63b05f0e

tech-stack:
  added: []
  patterns:
    - "Plan carries final bytes plus base_sha256; apply is a dumb ordered write loop"
    - "fsutil and verify are called as module attributes in applier (fault-injection seam)"
    - "Symbol and footprint changes are Edit splices on the vendor text, applied once with apply_edits"
    - "Refusals are ERROR Issues on a blocked plan with no ops; nothing is raised"

key-files:
  created:
    - kicad_lib_manager/importer/plan.py
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/applier.py
    - kicad_lib_manager/importer/verify.py
    - tests/test_install_e2e.py
    - tests/test_install_plan.py
  modified:
    - kicad_lib_manager/kicad_files.py
    - tests/conftest.py
    - tests/test_importer_layering.py

key-decisions:
  - "Property roles follow D-12: an existing Manufacturer/MPN is kept, the first vendor alias (MF, MP, ...) is renamed in place, otherwise a hidden property is cloned from Datasheet/Footprint/ki_fp_filters/ki_keywords"
  - "Several chosen footprints are supported now (D-17): the first is linked, all go into ki_fp_filters space-joined, the model attaches to the first"
  - "Temporary refusals with their own codes (install.library_not_found, install.version_unsupported, install.rename_unsupported, install.extends_unsupported) mark exactly what later plans widen"
  - "apply_plan also checks base_sha256 and 'must not exist' just before writing (install.stale_plan)"
  - "InstallPlan.symbol_name returns an empty string on a refused plan with no symbol names"

patterns-established:
  - "Tracer first: one real path through every layer, then refusals as a TDD task"
  - "Backups go to <backup_root>/installs/<timestamp>_<library>/<file>_backup_<N>"

requirements-completed: [INST-01, INST-03, INST-04, INST-05, INST-08]

coverage:
  - id: D1
    description: "UL sample installs into a tmp copy of IC_Battery_Charger_TI; removing the inserted segment restores the original bytes exactly"
    requirement: INST-01
    verification:
      - kind: e2e
        ref: "tests/test_install_e2e.py#test_ul_symbol_added_others_identical"
        status: pass
    human_judgment: false
  - id: D2
    description: "Installed footprint name, value text, file stem, symbol Footprint field and ki_fp_filters agree"
    requirement: INST-03
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_footprint_consistency_default_names"
        status: pass
      - kind: e2e
        ref: "tests/test_install_e2e.py#test_ul_symbol_added_others_identical"
        status: pass
    human_judgment: false
  - id: D3
    description: "STEP copied to Custom/3DModels/<MPN>.stp with the staged file's SHA-256"
    requirement: INST-04
    verification:
      - kind: e2e
        ref: "tests/test_install_e2e.py#test_ul_symbol_added_others_identical"
        status: pass
    human_judgment: false
  - id: D4
    description: "Footprint carries one model block ${CUSTOM_3DMODEL_DIR}/<file>; tab-indented footprints get tab-indented blocks"
    requirement: INST-05
    verification:
      - kind: e2e
        ref: "tests/test_install_e2e.py#test_ul_symbol_added_others_identical"
        status: pass
      - kind: unit
        ref: "tests/test_install_plan.py#test_model_block_follows_tab_indentation"
        status: pass
    human_judgment: false
  - id: D5
    description: "apply_plan verifies from disk (re-parse, symbol once, link resolves, model listed) and undoes on failure"
    requirement: INST-08
    verification:
      - kind: e2e
        ref: "tests/test_install_e2e.py#test_ul_symbol_added_others_identical"
        status: pass
    human_judgment: true
    rationale: "Rollback on a failing write or failing verify is implemented but its fault-injection tests belong to plan 04-10; only the success path and the pre-write refusals are asserted here"
  - id: D6
    description: "Refusals: placeholder library, no symbol, no footprint, choice required, unknown item, source gone/changed, package issues in the plan; blocked plans write nothing"
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py (15 tests selected by -k placeholder/no_symbol/no_footprint/choice/unknown/source_*/package_issues/footprint_consistency/blocked)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-10-19
status: complete
---

# Phase 4 Plan 01: Install tracer and plan contract Summary

**The Ultra Librarian CSD85301Q2 sample now installs end to end into a copy of `IC_Battery_Charger_TI` through `build_plan`, `apply_plan` and `verify_install`: the library header and every other symbol stay byte-identical, the footprint, `Footprint` field, `ki_fp_filters` and `${CUSTOM_3DMODEL_DIR}` model link agree, and hidden `Manufacturer`/`MPN` properties are cloned in.**

## Performance

- **Duration:** about 20 min
- **Started:** 2026-10-19T22:27:41Z
- **Completed:** 2026-10-19T22:38Z
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files modified:** 9 (6 created, 3 modified)

## Accomplishments

- Tracer slice through every layer: `kicad_files` write helpers, the frozen plan contract, `build_plan`, `apply_plan` (path containment, source hash check, app-data backup, ordered atomic writes, verify, undo) and `verify_install`.
- Contract that Phases 5 and 6 and plans 04-02 to 04-10 build on: `InstallPlan`/`InstallOptions`/`FileOp`/`Conflict`/`Resolution`/`ToolContext`/`InstallResult` in `importer/plan.py`.
- Refusal rules as blocked plans with specific codes (`install.placeholder_library`, `install.no_symbol`, `install.no_footprint`, `install.choice_required`, `install.unknown_item`, `install.source_gone`, `install.source_changed`); `apply_plan` never writes a blocked plan.
- Layering guard registered for all five new importer modules, so parallel plans do not edit it; the three shared fixtures (`custom_copy`, `ul_package`, `snapshot`) are in `tests/conftest.py`.

## Task Commits

1. **Task 1: tracer, UL sample into an equal-version Custom/ library copy** - `f5a9448` (feat)
2. **Task 2 RED: failing refusal and contract tests** - `3393d34` (test)
3. **Task 2 GREEN: refusals in build_plan** - `3483d0d` (feat)

**Plan metadata:** the docs commit that carries this SUMMARY, STATE.md, ROADMAP.md and REQUIREMENTS.md.

## TDD Gate Compliance (Task 2)

- **RED:** `tests/test_install_plan.py` committed with 15 failing and 5 passing tests. Every failure is an assertion on the planned behavior, for example `['install.unsupported_candidate'] == ['install.choice_required']`, `'install.source_gone' in ['install.source_unreadable']` and `plan.issues[1:] != candidate.issues` (no de-duplication yet). No collection error, fixture crash or import error. The five that already passed (`test_footprint_consistency_default_names`, both conflict tests, `test_blocked_plan_is_never_applied_even_when_ops_exist`, `test_model_changed_after_plan_is_refused_by_apply`) test behavior the tracer already delivered (conflicts, consistency, apply-time hash check); that is expected, not an unexpected green. Semantic assessment: RED was valid. Evidence was inspected by hand from the pytest output because pytest's console format is not one of the formats the `tdd-red-evidence` classifier reads.
- **GREEN:** the same file passes (22 tests after two helper tests were added in the GREEN commit); full suite 932 passed, 4 skipped.
- **REFACTOR:** none needed.

## Files Created/Modified

- `kicad_lib_manager/kicad_files.py` - write side: `footprint_name_edit`, `footprint_value_edits`, `model_insert_edit`, `set_property_edit`, `next_property_id`, `new_property_text`, `property_insert_edit`, `symbol_insert_edit`
- `kicad_lib_manager/importer/plan.py` - frozen plan and result dataclasses, `MODEL_DIR_VAR`
- `kicad_lib_manager/importer/planner.py` - `build_plan`
- `kicad_lib_manager/importer/applier.py` - `apply_plan`
- `kicad_lib_manager/importer/verify.py` - `verify_install`
- `tests/conftest.py` - `custom_copy`, `ul_package`, `snapshot`
- `tests/test_importer_layering.py` - ALLOWED and CORE_MODULES entries
- `tests/test_install_e2e.py` - tracer test
- `tests/test_install_plan.py` - refusal, contract and helper tests

## Decisions Made

- D-12 property roles are implemented already (keep exact, rename the first vendor alias in place, else clone a hidden property), so a SnapEDA `MF`/`MP` symbol does not end up with duplicates.
- Several chosen footprints work now (D-17): first one linked, all in `ki_fp_filters`, model on the first. The plan only required the choice rule, but the single-footprint assumption would have had to be undone in the next plan.
- Unsupported cases refuse with their own codes instead of guessing, so each later plan removes exactly one refusal.
- `apply_plan` rejects a stale plan (`install.stale_plan`) when a target changed or appeared after planning (research Pitfall 13).
- Backup folder names use a sanitised library name so a hostile library string cannot leave `installs/`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Library name validated against `sanitize_name`**
- **Found during:** Task 1 (build_plan)
- **Issue:** `options.library` is joined into paths (`Symbols/<lib>.kicad_sym`, `<lib>.pretty`) and the threat model T-04-01 relies on sanitised names, but a caller-supplied library string was used as-is.
- **Fix:** ERROR `install.bad_library_name` when `sanitize_name(library).sanitized != library`; the applier's `is_relative_to(custom_dir)` check stays as the second line.
- **Files modified:** `kicad_lib_manager/importer/planner.py`
- **Committed in:** `f5a9448`

**2. [Rule 2 - Missing critical] Stale-plan check and symbol-less tracer guards**
- **Found during:** Task 1 (apply_plan)
- **Issue:** The plan bakes `base_sha256` into ops but the applier text did not say to check it; writing a plan made from an old library would clobber a KiCad edit.
- **Fix:** `install.stale_plan` when a target's current bytes differ from `base_sha256`, or a "must not exist" path now exists; `InstallPlan.symbol_name` returns "" on a refused plan.
- **Files modified:** `kicad_lib_manager/importer/applier.py`, `kicad_lib_manager/importer/plan.py`
- **Committed in:** `f5a9448`

**3. [Rule 2 - Missing critical] Additions beyond the written spec, all needed to avoid wrong output**
- D-12 alias rename and `install.no_property_template` (Task 1): avoids duplicate Manufacturer/MPN and a crash on symbols with no property to clone.
- `install.no_model` WARNING and multi-footprint linking (Task 2): D-17 / INTK-08.
- `install.duplicate_name` when two chosen footprints sanitise to the same name (Task 2).
- **Committed in:** `f5a9448`, `3483d0d`

---

**Total deviations:** 3 auto-fixed groups (all Rule 2). **Impact on plan:** no scope creep into other plans' files; each addition prevents a wrong or unsafe write.

## Not Done Here (owned by later plans)

- New libraries and incomplete pairs (`install.library_not_found`), unequal versions (`install.version_unsupported`), symbol rename (`install.rename_unsupported`), `extends` units (`install.extends_unsupported`), conflict resolutions and identical-item detection (conflicts are always unresolved), the kicad-cli gate (`install.cli_not_found` INFO is added when no CLI is set), fault-injection rollback tests, and pruning old `installs/` backup folders (research Pattern 6 step 2, not in this plan's action text).

## Issues Encountered

- A shell heredoc layer halves doubled backslashes, which produced a syntax error in a Python patch script; the affected lines in `kicad_files.py` were fixed with the Edit tool before the first commit. No lasting effect.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The plan contract, fixtures and layering registration are in place; plans 04-02 onward can widen one layer each without touching `plan.py` or the layering test.
- `git status --porcelain Custom` is empty: every install ran against `tmp_path` copies.

## Known Stubs

None. The `install.*_unsupported` refusals are intentional and listed under "Not Done Here".

## Self-Check: PASSED

All nine key files exist and commits `f5a9448`, `3393d34` and `3483d0d` are ancestors of HEAD. Plan verification: `pytest tests/test_install_e2e.py tests/test_install_plan.py tests/test_importer_layering.py tests/test_layering.py` 46 passed; full suite 932 passed, 4 skipped (909 baseline plus 23 new).

---
*Phase: 04-plan-and-install-core*
*Completed: 2026-10-19*
