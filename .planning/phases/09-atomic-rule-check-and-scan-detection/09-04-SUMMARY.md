---
phase: 09-atomic-rule-check-and-scan-detection
plan: 04
subsystem: atomic-check
tags: [python, atomic-rules, footprint, 3d-model, kicad-mod, scan]

requires:
  - phase: 09-atomic-rule-check-and-scan-detection
    provides: "09-03 atomic_check.py (check_symbol, check_libraries, owner walk, FILL_KINDS incl. attach_model); 09-02 FixSpec, Violation, SymbolEntry"
provides:
  - "kicad_lib_manager/atomic_check.py: CUSTOM_MODEL_PREFIX, FootprintTarget, AtomicContext, repo_context, Footprint rule, 3D model rule"
  - "check_symbol and the per-symbol check take a required ctx: AtomicContext; check_libraries builds one repo_context per scan"
  - "Issue codes atomic.footprint and atomic.model_3d; FixSpec kind attach_model offered as a fill template"
  - "tests/customfixtures.py: write_fake_kicad, Footprint and 3D model inventory cases, ATOMIC_MODEL_FOOTPRINTS, Dup_Footprints twin"
affects: [09-06 fix engine (attach_model, CUSTOM_MODEL_PREFIX), phase-10 install gating (own AtomicContext), phase-11 commit gate, phase-13 migration]

actuals:
  tokens: 21000
  tasks: 2
  commits: 3
plan_head_before: 45f2d6b1ccba68096beb001d3c6ff771edff5010
plan_head_after: f8daaef12ff267c140f10c16321362bb8225e8dd

tech-stack:
  added: []
  patterns:
    - "Resolution through an injected AtomicContext (resolve_footprint, model_problems) so a later phase can check an incoming part against its own tree"
    - "Untrusted names are matched against exact os.listdir results before any path is built; listings and per-footprint verdicts are cached per scan"
    - "A rule that cannot be checked fails with a plain 'Could not check the 3D model: ...' reason, never passes on trust"

key-files:
  created: []
  modified:
    - kicad_lib_manager/atomic_check.py
    - tests/customfixtures.py
    - tests/test_atomic_check.py
    - tests/test_atomic_scan.py

key-decisions:
  - "The checked symbol's own name is the symbol field of the attach_model fill (the footprint file is named by rel_path and params.footprint), even when the Footprint field is inherited from a parent"
  - "A (model ...) path with no variable and not absolute fails with 'Could not check the 3D model: \"<path>\" does not start with a folder variable' (plan was silent on this case)"
  - "Only KICAD<digits>_3DMODEL_DIR is resolved for KiCad models; ${KICAD_3DMODEL_DIR} without digits fails as 'it uses ${...}' (plan D-19 names the numbered form only)"
  - "Identical problems from several model lines are listed once in the joined violation text"

patterns-established:
  - "Footprint and 3D model rules plug into _check_ref via _footprint_violation and _model_violation; the model rule runs only on a resolved FootprintTarget"
  - "Unit tests that are not about footprints use a permissive _anywhere_ctx; footprint and model tests build repo_context over a tmp tree with write_atomic_files and write_fake_kicad"

requirements-completed: [ATOM-01, ATOM-03]

coverage:
  - id: D1
    description: "The Footprint rule passes only when the field names exactly one existing Library:Footprint among the repo's footprint libraries (any source) and KiCad's installed footprints, and each failure has its own plain reason"
    requirement: "ATOM-01"
    verification:
      - kind: unit
        ref: "tests/test_atomic_check.py (22 tests selected by -k footprint)"
        status: pass
      - kind: integration
        ref: "tests/test_atomic_scan.py#test_every_atomic_library_has_its_symbols_in_file_order_with_the_expected_rules"
        status: pass
    human_judgment: false
  - id: D2
    description: "Names are compared case-sensitively against directory listings, so a wrong-case footprint or model name fails on Windows too; dotted and separator-bearing text never forms a path"
    requirement: "ATOM-01"
    verification:
      - kind: unit
        ref: "tests/test_atomic_check.py#test_footprint_wrong_case_fails_even_on_a_case_insensitive_disk"
        status: pass
      - kind: unit
        ref: "tests/test_atomic_check.py#test_model_with_the_wrong_case_fails_even_on_a_case_insensitive_disk"
        status: pass
      - kind: unit
        ref: "tests/test_atomic_check.py#test_footprint_text_with_dots_and_separators_never_resolves_to_a_path"
        status: pass
    human_judgment: false
  - id: D3
    description: "The 3D model rule resolves Custom and numbered KiCad model folders, fails when the footprint has no model line, when any line is missing, when another variable is used, and says plainly when KiCad's 3D model folder cannot be found"
    requirement: "ATOM-01"
    verification:
      - kind: unit
        ref: "tests/test_atomic_check.py (27 tests selected by -k model)"
        status: pass
      - kind: integration
        ref: "tests/test_atomic_scan.py#test_a_stock_kicad_footprint_is_unknown_when_the_scan_has_no_kicad_folder"
        status: pass
    human_judgment: false
  - id: D4
    description: "A failing model rule on a Custom symbol with a Custom footprint carries an attach_model fill naming that footprint; no fill for a Wurth or KiCad footprint, a non-fixable library or an unreadable footprint"
    requirement: "ATOM-01"
    verification:
      - kind: unit
        ref: "tests/test_atomic_check.py#test_model_fill_for_a_custom_footprint_names_the_footprint_to_fix"
        status: pass
      - kind: integration
        ref: "tests/test_atomic_scan.py#test_a_custom_footprint_with_a_model_problem_carries_the_fill_that_names_the_footprint"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every Footprint and 3D model case of the fixture inventory produces exactly its ATOMIC_EXPECTED rule set in a scan with the fake KiCad folders; fixture libraries still load in real kicad-cli 10"
    requirement: "ATOM-03"
    verification:
      - kind: integration
        ref: "tests/test_atomic_scan.py#test_every_atomic_library_has_its_symbols_in_file_order_with_the_expected_rules"
        status: pass
      - kind: integration
        ref: "tests/test_atomic_scan.py -m kicad_cli (9 passed)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Wording of the new reasons ('footprint library \"X\" is defined more than once', 'Could not check the 3D model: it uses ${KIPRJMOD}') reads well to the owner"
    verification: []
    human_judgment: true
    rationale: "Plain-language quality is a judgement about the owner's own vocabulary; tests pin the text, not whether it is clear"

duration: 20min
completed: 2026-10-26
status: complete
---

# Phase 9 Plan 04: Footprint and 3D model rules Summary

**atomic_check.py now resolves each Atomic_ symbol's Footprint field to exactly one existing Library:Footprint (repo or KiCad) through an injected AtomicContext and checks every 3D model line of that footprint against Custom/3DModels or KiCad's 3dmodels folder, failing with a plain reason whenever it cannot confirm, and offering an attach_model fill for Custom footprints**

## Performance

- **Duration:** about 20 min
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files modified:** 4 (no new files)

## Accomplishments

- `repo_context(repo_root, fp_libs, kicad_fp_dir)` builds the `AtomicContext` (`resolve_footprint`, `model_problems`) used by `check_libraries`; Phase 10 can pass its own for an incoming part. Footprint names and library names are matched against exact `os.listdir` results before any path is built; listings and per-footprint model verdicts are cached for the scan.
- Footprint rule reasons: `no footprint`, `Footprint "X" does not name a library (expected Library:Footprint)`, `footprint library "L" was not found`, `footprint library "L" is defined more than once` (two repo libraries, or a repo library sharing a KiCad nickname), `footprint "F" is not in library "L"`; an inherited field carries the ` (inherited from "<parent>")` suffix.
- 3D model rule: `${CUSTOM_3DMODEL_DIR}/<rel>` against exact names under Custom/3DModels; `${KICAD<n>_3DMODEL_DIR}/<rel>` walked segment by segment through the 3dmodels folder next to the footprints folder; absolute paths pass only through an exact listing match; other variables, empty/`.`/`..` segments, a footprint with no model line, an unreadable footprint, and an unknown KiCad folder all fail with plain reasons and keep the rule blocking. Several problems are joined into one violation.
- `attach_model` fill (`FixSpec("attach_model", <footprint rel_path>, <symbol>, "Choose a 3D model file", {"footprint": <rel_path>, "source": ""})`) only for a fixable (Custom) symbol whose footprint is under Custom/ and is readable.
- Fixture: `write_fake_kicad(root)`, seven Footprint cases, four model cases, a `Dup_Footprints` twin outside Custom/, and `WRONG-CASE.step`; every symbol of every Atomic_ library is now judged on all seven blocking rules (ATOM-03).

## Task Commits

1. **Task 1: Footprint rule through an injected AtomicContext (tracer)** - `128518d` (feat)
2. **Task 2 RED: failing tests for the 3D model rule** - `be0a441` (test)
3. **Task 2 GREEN: 3D model rule with the model fill-in target** - `f8daaef` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified

- `kicad_lib_manager/atomic_check.py` - FootprintTarget, AtomicContext, repo_context, Footprint and 3D model rules, CUSTOM_MODEL_PREFIX
- `tests/customfixtures.py` - write_fake_kicad, Footprint and model inventory cases and ATOMIC_EXPECTED entries
- `tests/test_atomic_check.py` - permissive `_anywhere_ctx` default for the field-rule tests, 22 footprint and 27 model tests (counted by -k), inventory test over a real context
- `tests/test_atomic_scan.py` - `_scan` uses the fake KiCad folders; scan without a KiCad folder; model fill-in in a scan

## Decisions Made

See `key-decisions` in the frontmatter. The one that matters downstream: plan 09-06 resolves `attach_model` from `rel_path`/`params.footprint`; `FixSpec.symbol` is the checked symbol, not the owner of an inherited Footprint field.

## Deviations from Plan

None - plan executed exactly as written. Test-side adjustments inside the plan's latitude: the existing vendor `extends_pair` test now expects `footprint` in its rule list (its child declares an empty Footprint, which the new rule rightly flags), `test_the_inventory_symbols_produce_exactly_their_expected_rule_sets` and the unreadable-library scan test now use a real context / the fake KiCad folders.

## TDD Gate Compliance

Task 1 is a tracer (one production commit with its tests, verify re-run green before Task 2). Task 2 has RED then GREEN; no REFACTOR commit was needed.

- **Task 2 RED (`be0a441`):** 29 tests failed, all on assertions for the planned behaviour (for example `[]` where one `model_3d` violation was expected, summary counts 21 against 25, parse-call list empty against `["FP-T.kicad_mod"]`). No import, collection or fixture errors: the tests import only names that already existed after Task 1. Semantic assessment: the target tests executed and failed because no `model_3d` violation exists yet. The `check tdd-red-evidence` classifier was not run (plain pytest output is not a format it supports).
- **Task 2 GREEN (`f8daaef`):** the same selection passes (177 passed, 2 skipped).

## Issues Encountered

None. `Custom/` and `WurthElektronik/KiCad-Library` are not checked out in this worktree, so the two submodule-backed scanner tests skip; the orchestrator's post-merge run covers them.

## Known Stubs

None.

## Threat Flags

None. T-09-08 (exact listings before any path is built, segment walk, empty/`.`/`..` segments refused, wrong-case and dotted inputs tested) and T-09-09 (size cap before reading, node cap in parse_bytes, listings and verdicts cached, KiCad folders listed only for referenced libraries) are implemented and tested. `atomic_check` still imports no network or process module (ast test passes).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 09-06 can resolve `attach_model` and reuse `CUSTOM_MODEL_PREFIX` from `atomic_check`.
- Phase 10 can pass its own `AtomicContext` (a resolver over the incoming part) to `check_symbol`.
- Open for the owner: wording of the new reasons (coverage D6), and whether `${KICAD_3DMODEL_DIR}` without digits should also resolve (currently fails as "it uses ${KICAD_3DMODEL_DIR}").

## Self-Check: PASSED

- FOUND: kicad_lib_manager/atomic_check.py, tests/customfixtures.py, tests/test_atomic_check.py, tests/test_atomic_scan.py
- FOUND commits: 128518d, be0a441, f8daaef
- `pytest tests/test_atomic_check.py tests/test_atomic_scan.py tests/test_layering.py tests/test_scanner_issues.py` - 177 passed, 2 skipped (submodules absent)
- `pytest tests/test_layering.py tests/test_importer_layering.py tests/test_customfixtures.py tests/test_main_window.py tests/test_models.py tests/test_scanner_skip_dirs.py` - 94 passed
- `pytest tests/test_atomic_scan.py -m kicad_cli` - 9 passed (real kicad-cli 10)

---
*Phase: 09-atomic-rule-check-and-scan-detection*
*Completed: 2026-10-26*
