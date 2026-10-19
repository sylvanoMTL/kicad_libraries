---
phase: 03-package-intake-and-naming
plan: 05
subsystem: importer-naming
tags: [unicodedata, sanitiser, windows-reserved-names, tdd]

requires:
  - phase: 03-package-intake-and-naming
    provides: "plan 03-01 candidate items and importer package; plan 03-02 zipfixtures builders and layering guard"
provides:
  - "importer/naming.py: sanitize_name, sanitize_filename, case_clash, NameResult and the naming.* Issue codes"
  - "name_check properties on SymbolItem, FootprintItem and ModelItem (sanitised name beside the vendor original)"
affects: [03-06 suggest_library, phase-04 install, phase-05 preview]

actuals:
  tokens: 9000
  tasks: 3
  commits: 6

tech-stack:
  added: []
  patterns:
    - "Pure frozen-result sanitisers returning NameResult(original, sanitized, issues); no module state"
    - "Read-only derived properties on frozen item dataclasses instead of stored fields"

key-files:
  created:
    - kicad_lib_manager/importer/naming.py
    - tests/test_naming_sanitize.py
    - tests/test_candidate_names.py
  modified:
    - kicad_lib_manager/importer/candidate.py

key-decisions:
  - "Reserved-stem underscore is only trimmed back to max_len when the rename overflows; an unconditional strip would remove the appended underscore"
  - "sanitize_filename drops the stem's naming.changed Issue and rebuilds it with the full file names"
  - "name_check stays a computed property (no dataclass field) so equality and zip/folder parity checks are unaffected"

requirements-completed: [LIB-03]

coverage:
  - id: D1
    description: "sanitize_name applies the D-15 pipeline (transliteration, NFKD, unsafe characters to underscore, collapse, strip, 64 cap, reserved Windows stems, Unnamed placeholder) and reports naming.changed / truncated / reserved / empty"
    requirement: "LIB-03"
    verification:
      - kind: unit
        ref: "tests/test_naming_sanitize.py#test_sanitize_examples,test_sanitize_issue_codes,test_sanitize_empty_inputs,test_sanitize_reserved_after_cap,test_sanitize_idempotent"
        status: pass
    human_judgment: false
  - id: D2
    description: "All 51 frozen existing Custom/ names and the 13 existing 3D-model file names pass through unchanged with no Issue"
    requirement: "LIB-03"
    verification:
      - kind: unit
        ref: "tests/test_naming_sanitize.py#test_sanitize_existing_names_unchanged,test_filename_existing_models_unchanged"
        status: pass
    human_judgment: false
  - id: D3
    description: "sanitize_filename sanitises only the stem before a listed extension and keeps the extension exactly; case_clash warns once per existing name that differs only by case (casefold)"
    requirement: "LIB-03"
    verification:
      - kind: unit
        ref: "tests/test_naming_sanitize.py#test_filename_examples,test_filename_empty_stem,test_case_clash,test_case_clash_casefold_and_each_existing_name"
        status: pass
    human_judgment: false
  - id: D4
    description: "Candidate symbols, footprints and models report their sanitised name beside the verbatim vendor name (success criterion 5)"
    requirement: "LIB-03"
    verification:
      - kind: unit
        ref: "tests/test_candidate_names.py#test_candidate_names_ul,test_candidate_names_hostile,test_candidate_names_follow_the_item"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live Custom/ names (symbols, footprints, 3D models) pass through unchanged"
    verification: []
    human_judgment: true
    rationale: "The live Custom/ tests skip in this worktree because the submodule is not checked out; they must be run on the merged main checkout"

duration: 20min
completed: 2026-10-19
status: complete
commits: 6
plan_head_before: af7bf2b412306a4fa45362d8ec697436e091d872
plan_head_after: 45d4919d736b98cfdcbcc86ae6aad8bbf5dc762d
---

# Phase 3 Plan 05: Name Sanitiser and Candidate name_check Summary

**One pure, stdlib-only sanitiser (`sanitize_name`, `sanitize_filename`, `case_clash`) that turns hostile, reserved, unicode and overlong names into safe ASCII, reports both names and every change, leaves all current Custom/ names untouched, and is exposed on every candidate symbol, footprint and model as `name_check`**

## Performance

- **Duration:** about 20 min
- **Completed:** 2026-10-19
- **Tasks:** 3 (6 commits: RED and GREEN for each)
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments

- `sanitize_name` follows D-15 in order: fixed transliteration (micro/mu to u, Ohm/Omega to Ohm, degree to deg, o-slash, sharp s, ae ligatures) before and after NFKD with combining marks dropped, unsafe characters to `_`, collapse, strip `_. `, 64-character cap, Windows reserved stem gets `_` before the first dot (`NUL.foo` -> `NUL_.foo`), empty -> `Unnamed`. Issues: `naming.changed` (INFO), `naming.truncated` and `naming.reserved` (WARNING), `naming.empty` (ERROR). All 19 plan examples hold; output is pure ASCII and idempotent.
- `sanitize_filename` sanitises only the stem before a listed extension (longest match first, matched case-insensitively, kept as written); names without a listed extension are sanitised whole and `os.path.splitext` is never used.
- `case_clash` returns one `naming.case_clash` WARNING per existing name that differs only by `str.casefold` (D-16); exact equality gives none.
- `SymbolItem.name_check` and `FootprintItem.name_check` return `sanitize_name(self.name)`; `ModelItem.name_check` returns `sanitize_filename(self.filename)`. `name` and `filename` stay verbatim; no dataclass field was added.

## Task Commits

1. **Task 1 RED:** `f20ee63` (test) - failing sanitize_name tests with signature-only stubs
2. **Task 1 GREEN:** `6509abe` (feat) - sanitize_name D-15 pipeline
3. **Task 2 RED:** `7219706` (test) - failing sanitize_filename and case_clash tests
4. **Task 2 GREEN:** `b768091` (feat) - sanitize_filename and case_clash
5. **Task 3 RED:** `a861832` (test) - failing candidate name_check tests
6. **Task 3 GREEN:** `45d4919` (feat) - name_check properties on the three item classes

**Plan metadata:** committed with this SUMMARY (docs).

## TDD Gate Compliance

- **Task 1 RED:** `naming.py` stubs (identity results) were committed with the tests so the tests fail on planned assertions (27 failed, 2 passed on stubs: the idempotence and unchanged-existing-names tests trivially hold on an identity stub). A run without the module would fail at import, which is INVALID_RED. Semantic assessment: failures are assertion mismatches such as `'CON.aaa...' startswith 'CON_.'`.
- **Task 2 RED:** 13 failed against the stubs for `sanitize_filename` and `case_clash` (assertions such as `assert 0 == 1`).
- **Task 3 RED:** 3 failed with `AttributeError: 'SymbolItem' object has no attribute 'name_check'` after the package opened and candidate detection ran, so each test reached its target line; the missing property is the planned behavior.
- **GREEN:** each task's GREEN commit passes its tests and the full suite. REFACTOR: none needed.
- `workflow.tdd_mode` is not enabled, so `check tdd-red-evidence` was not run.

## Files Created/Modified

- `kicad_lib_manager/importer/naming.py` - sanitiser, `NameResult`, constants, `case_clash` (imports only `..models` and stdlib)
- `tests/test_naming_sanitize.py` - example table, issue codes, empty inputs, cap, idempotence, existing names, filename and case-clash tests
- `kicad_lib_manager/importer/candidate.py` - three `name_check` properties and one import
- `tests/test_candidate_names.py` - UL, hostile-name and follow-the-item tests

## Decisions Made

- See key-decisions in the frontmatter. The reserved-stem fix was found during GREEN: stripping `_` after the rename removed the underscore just added, so the strip only runs when the rename overflows `max_len`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Signature-only stubs in the Task 1 RED commit**
- **Found during:** Task 1 (RED)
- **Issue:** With no `naming.py`, the new tests fail at import, which tdd.md classes as INVALID_RED (same situation as plan 03-01 Task 2).
- **Fix:** Committed identity stubs for `sanitize_name`, `sanitize_filename` and `case_clash` with the RED tests; GREEN commits replaced them.
- **Files modified:** kicad_lib_manager/importer/naming.py
- **Committed in:** f20ee63

**Total deviations:** 1 auto-fixed (process only). **Impact on plan:** none on behavior.

No change was needed in sibling files (`adapters/base.py`, `detect.py`, `package.py`, `kicad_files.py`). The hostile-name test relies on the generic fallback of `detect_candidate` (unclaimed packages get vendor `Unknown`), which exists in the current `detect.py`; it should keep working after plan 03-04 changes `detect.py`/`locate`, but the combined post-merge run should confirm it.

## Issues Encountered

The sandbox rejects compound shell commands in the worktree, so git and pytest commands were run as separate plain calls.

## Test Results

Main checkout interpreter by absolute path, from the worktree root:
- `tests/test_candidate_names.py tests/test_naming_sanitize.py tests/test_adapters.py tests/test_importer_layering.py`: 75 passed, 1 skipped.
- Full suite: **602 passed, 10 skipped.** Skips are submodule-dependent (`Custom/` and `WurthElektronik/KiCad-Library` not checked out), including `test_sanitize_live_custom_names_unchanged`; `test_filename_existing_models_unchanged` runs its frozen list and skips only the live `Custom/3DModels` part.
- `tests/test_importer_layering.py` real-module tests ran (not skipped) and pass with `naming.py` and the new `from .naming import ...` in `candidate.py`.
- `git status --porcelain -- Custom` printed nothing.

## Known Stubs

None.

## Threat Flags

None. T-03-19 to T-03-22 and T-03-33 are mitigated as planned (single safe path component, reserved-stem underscore, ASCII-only output, 64-character cap, `name_check` on every item); Phase 4 still checks containment at write time.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03-06 `suggest_library` can call `sanitize_name` for library names and `case_clash` against existing libraries; Phases 4 and 5 can default to `item.name_check.sanitized` and show both names.
- After merging with plans 03-03 and 03-04, run the full suite plus the live `Custom/` tests on a checkout that has the submodule.

## Self-Check: PASSED

- `kicad_lib_manager/importer/naming.py`, `tests/test_naming_sanitize.py`, `tests/test_candidate_names.py`: FOUND
- `def name_check` appears 3 times in `candidate.py`
- Commits `f20ee63`, `6509abe`, `7219706`, `b768091`, `a861832`, `45d4919`: FOUND on this branch

---
*Phase: 03-package-intake-and-naming*
*Completed: 2026-10-19*
