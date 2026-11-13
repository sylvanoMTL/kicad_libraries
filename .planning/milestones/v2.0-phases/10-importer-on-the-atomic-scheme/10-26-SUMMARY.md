---
phase: 10-importer-on-the-atomic-scheme
plan: 26
subsystem: importer
tags: [footprint-family, rank, tie-agreement, gap-closure, CR-01, D-28]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "plan 10-23 generated text and family source, plan 10-25 footprint index rank()"
provides:
  - "_agreed_family_texts in planner.py: an official footprint supplies the package family only when every footprint at the top rank score names the same family"
  - "rank(limit=None) returns every scored footprint"
  - "Family tests on synthetic stock trees and on the installed KiCad 10 footprints"
affects: [10-28 disposition, 10-VERIFICATION re-run]

actuals:
  tokens: 14000
  tasks: 2
  commits: 3
plan_head_before: 7f4271db36102d446842307b8e6bd888c2ef9bac
plan_head_after: ebc1f45d3346ba8e1d23953af37dc7b33a2154f8

tech-stack:
  added: []
  patterns:
    - "Tied rank() matches supply a derived fact only when they all agree; alphabetical tie order never decides"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/footprint_index.py
    - tests/test_generated_text.py
    - tests/README.md

key-decisions:
  - "Owner decision 2026-10-28: tied matches supply the family only when they all agree"
  - "A tied footprint that names no family counts as disagreeing"
  - "On KiCad 10, SOT-23-5 gets no family (owner confirmed 2026-10-28)"

requirements-completed: [FLD-03, FLD-01]

coverage:
  - id: D1
    description: "A vendor code whose leading letters tie official footprints of different families gets no family; the installed footprint carries the no-folder description and tags"
    requirement: FLD-03
    verification:
      - kind: unit
        ref: "tests/test_generated_text.py#test_an_ambiguous_package_code_supplies_no_family"
        status: pass
    human_judgment: false
  - id: D2
    description: "A single top match, a unique full-code match and tied footprints that agree still supply their family; a tie holding a footprint with no family, a lower-case code and an empty folder supply none"
    requirement: FLD-03
    verification:
      - kind: unit
        ref: "tests/test_generated_text.py#test_a_single_leading_letters_match_supplies_its_family"
        status: pass
      - kind: unit
        ref: "tests/test_generated_text.py#test_a_unique_full_code_match_supplies_its_family"
        status: pass
      - kind: unit
        ref: "tests/test_generated_text.py#test_a_tie_that_agrees_supplies_the_family"
        status: pass
      - kind: unit
        ref: "tests/test_generated_text.py#test_a_tie_with_a_footprint_naming_no_family_supplies_no_family"
        status: pass
      - kind: unit
        ref: "tests/test_generated_text.py#test_a_lower_case_code_ties_the_same_footprints"
        status: pass
      - kind: unit
        ref: "tests/test_generated_text.py#test_an_empty_kicad_footprints_folder_supplies_no_family"
        status: pass
    human_judgment: false
  - id: D3
    description: "Against the installed KiCad 10 footprints SOIC127P600X175-8N, LQFP48 and SOT-23-5 get no family, and the CSD sentence of UAT check 3 is unchanged"
    requirement: FLD-01
    verification:
      - kind: integration
        ref: "tests/test_generated_text.py#test_kicad_footprints_give_no_family_to_an_ambiguous_code"
        status: pass
      - kind: integration
        ref: "tests/test_generated_text.py#test_kicad_footprints_give_no_family_to_sot_23_5"
        status: pass
      - kind: integration
        ref: "tests/test_generated_text.py#test_kicad_footprints_keep_the_csd_sentence"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-28
status: complete
---

# Phase 10 Plan 26: Tied official footprints supply the family only when they agree Summary

**Closes CR-01: `_agreed_family_texts` takes the package family from official KiCad footprints only when every footprint at the top rank score names the same family, so rank()'s alphabetical tie order can no longer write SOIC-20 or LQFP-100 into a part.**

## Performance

- **Duration:** about 25 min
- **Started:** 2026-10-28T11:00Z (approx.)
- **Completed:** 2026-10-28T11:25Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `build_plan` asks `rank(footprint_index, package_code=code, limit=None)`, keeps the entries at the top score (30 or more) and reads each one's family as `package_family([*footprint_texts(index, link), name])`, the formula the official-link branch uses. It passes the first entry's texts to `footprint_facts` only when all tied entries give the same family. It stops at the first entry that differs, so a large tie is cheap (T-10-50).
- `rank()` accepts `limit: int | None`; the body, scores, tie order and default limit are unchanged (2 lines added, 1 deleted in `footprint_index.py`).
- Eleven new test cases (10 test functions) pin the rule both ways on synthetic stock trees and on the installed KiCad 10 footprints. `tests/test_generated_text.py` went from 18 to 30 passing tests; none skipped on the workstation.

## Task Commits

1. **Task 1 (tracer, TDD):** RED `a00009f` (test), GREEN `1276906` (feat). The commit that changed `planner.py` is **`1276906`**; plan 10-28 cites it in 10-REVIEW-DISPOSITION.md.
2. **Task 2 (TDD):** `ebc1f45` (test)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `kicad_lib_manager/importer/planner.py` - `_agreed_family_texts`, `FootprintIndex` import, rewritten `_MIN_FAMILY_SCORE` comment, vendor-footprint branch calls the helper
- `kicad_lib_manager/importer/footprint_index.py` - `rank()` `limit: int | None`, one docstring line
- `tests/test_generated_text.py` - `_vendor_zip(..., footprint=)`, stock-tree and plan-pair helpers, `_LIVE_FP_DIR`, the new tests
- `tests/README.md` - the "No KiCad footprints folder" skip row names `tests/test_generated_text.py`

## TDD Gate Compliance

- **RED (Task 1):** `test_an_ambiguous_package_code_supplies_no_family` failed on the planned assertion (`ambiguous.part_text == bare.part_text`): keywords `'Battery Management SOIC-20 SOIC127P600X175-8N TI Texas'` against `'Battery Management SOIC127P600X175-8N TI Texas'`. Semantic assessment: the target test executed, and it failed for the intended reason (the alphabetically first tied footprint, SOIC-20, supplied its family). The plan type is `execute`, so the `tdd-red-evidence` classifier was not run.
- **GREEN:** the test and the 97 other tests of the five verify files pass at `1276906`.
- **Task 2:** the rule already existed, so these tests were written after it. As a mutation check, with the pre-plan `planner.py` restored temporarily, 6 of them failed (the no-family tie, the lower-case code, the two installed ambiguous codes, the installed SOT-23-5, and the Task 1 test) and 24 passed. This is exactly the split the plan predicted. `planner.py` was then restored to the committed version.

## Owner decision 2026-10-28 (replaces closure contract (a) of 10-VERIFICATION.md)

> **Tied matches supply the family only when they all agree.**

A tie at the top score supplies the family when every tied official footprint names the same family. When they disagree, no family is taken. A single top match supplies its family as before. The rule applies at every score from 30, so the alphabetical tie-break never decides the family. Contract (a) ("score >= 50, or a leading-letters-only match where exactly one footprint holds the top score") is replaced by this rule. Contract (b), the two-SOIC test with no family, is met as written by `test_an_ambiguous_package_code_supplies_no_family`.

### SOT-23-5 on KiCad 10 (owner confirmation 2026-10-28)

On the installed KiCad 10 footprints the tie at 80 is `SOT-23-5` (family SOT-23-5) and `SOT-23-5_HandSoldering`, whose own description names SOT-23 with no pin count. They disagree, so SOT-23-5 gets no family. The owner confirmed this after seeing the measured result. `test_kicad_footprints_give_no_family_to_sot_23_5` passes on the workstation: the part text equals the no-folder text, the footprint description does not start with "SOT-23-5, ", and "SOT-23-5" is still a word of the description, tags and keywords (the vendor code itself).

## Known residual for the owner

A lone leading-letters match with a different pin count still supplies its family, as the owner's single-match rule allows: LQFP48 against a tree whose only LQFP footprint is an LQFP-100 would get LQFP-100. It is not tested. On KiCad 10, LQFP48 ties 36 footprints that disagree, so it gets no family there (pinned by the installed-KiCad test).

## Decisions Made

- A tied footprint that names no family counts as disagreeing (D-28: nothing is guessed). Pinned by `test_a_tie_with_a_footprint_naming_no_family_supplies_no_family`.
- Families are compared as the strings `package_family` returns; no extra normalisation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] RED test applied the plan after closing the package**
- **Found during:** Task 1 (GREEN run)
- **Issue:** `apply_plan` returned not-ok because the vendor package was already closed; the text assertions passed.
- **Fix:** moved the apply call inside the `try`, before `package.close()`, as the other vendor tests do.
- **Files modified:** tests/test_generated_text.py
- **Committed in:** `1276906` (with the GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 test bug). **Impact:** none on the production change. The RED commit therefore holds a version of the test whose apply step was wrong; the assertion that failed in RED was the text equality, which is unchanged.

## Issues Encountered

- A worktree guard refused compound git commands, so they were split into plain calls. A temporary file copied one level above the worktree by mistake was removed immediately; nothing outside the worktree remains.
- `git -C Custom status --porcelain` could not be compared before and after: the `Custom` submodule is not checked out in this worktree. The new tests write only under `tmp_path` and only read the installed KiCad folder.
- Three skips in `tests/test_footprint_text.py` (licence-restricted vendor samples absent) are pre-existing and unrelated.

## Verification

`tests/test_generated_text.py tests/test_footprint_index.py tests/test_footprint_text.py tests/test_importer_layering.py tests/test_atomic_targets.py tests/test_official_footprint.py tests/test_layering.py`: 159 passed, 3 skipped (the pre-existing sample skips). `-k "family or lower_case or csd_sentence"`: 14 passed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for 10-28 (disposition and the combined `-m "not wurth"` gate). Cite `1276906` as the planner.py commit.

## Self-Check: PASSED

- Commits `a00009f`, `1276906`, `ebc1f45` exist on this branch.
- Modified files exist and keep CRLF line endings.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-28*
