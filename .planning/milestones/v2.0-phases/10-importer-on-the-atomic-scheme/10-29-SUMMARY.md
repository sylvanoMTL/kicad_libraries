---
phase: 10-importer-on-the-atomic-scheme
plan: 29
subsystem: importer
tags: [footprint-family, pad-count, kicad-footprints, d-28, wr-06, g-10-1]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "10-26 agreement rule for the package family, 10-28 footprint index and pad_numbers"
provides:
  - "A leading-letters-only tie supplies a package family only from official footprints within one distinct pad of the vendor footprint (G-10-1, WR-06)"
  - "Public FULL_CODE_SCORE in footprint_index"
  - "Pad-aware vendor fixtures and family tests, including the installed KiCad 10 footprints"
affects: [10-30, verify-work, uat-test-1]

actuals:
  tokens: 14000
  tasks: 2
  commits: 3
plan_head_before: 43ddd1669661d7e61306c5c90fbb15a239a00762
plan_head_after: 180da6e53080351432c6265300e23cfbffccff47

tech-stack:
  added: []
  patterns:
    - "Size filter below FULL_CODE_SCORE only; full-code ties are never pad-filtered"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/footprint_index.py
    - tests/test_generated_text.py
    - .planning/phases/10-importer-on-the-atomic-scheme/10-REVIEW-DISPOSITION.md

key-decisions:
  - "Owner decision 2026-10-29: fix WR-06 with the pad-count filter, in the symmetric within-one-pad form (not the stricter exposed-pad variant)"
  - "Official footprints whose pads cannot be read are excluded from a leading-letters tie"
  - "Vendor pad count is len(footprint_pad_numbers(fp_refs[0].node)), distinct numbers, never FootprintFacts.pads"

requirements-completed: [FLD-03, FLD-01]

coverage:
  - id: D1
    description: "A 6-pad vendor footprint (SON50P150X150X60-6N, SON65P200X200X80-6N) tied on two SON-8 footprints gets no SON-8 in description, tags or keywords, and the installed Atomic_Footprints file carries the no-folder text"
    requirement: FLD-03
    verification:
      - kind: unit
        ref: "tests/test_generated_text.py#test_a_six_pad_part_takes_no_family_from_a_son_8_tie"
        status: pass
      - kind: unit
        ref: "tests/test_generated_text.py#test_kicad_footprints_give_no_family_to_a_six_pad_son"
        status: pass
    human_judgment: false
  - id: D2
    description: "The within-one-pad boundaries (5 and 11 pads no family; 7, 8, 10 pads SON-8), size-fit families (SOIC-8, LQFP-48 with 48 pads), and full-code ties not filtered (SOT-23-5)"
    requirement: FLD-01
    verification:
      - kind: unit
        ref: "tests/test_generated_text.py#test_a_leading_letters_tie_counts_only_footprints_within_one_pad"
        status: pass
      - kind: unit
        ref: "tests/test_generated_text.py#test_a_tie_that_agrees_supplies_the_family"
        status: pass
      - kind: unit
        ref: "tests/test_generated_text.py#test_kicad_footprints_give_a_48_pad_lqfp48_its_family"
        status: pass
    human_judgment: false
  - id: D3
    description: "The CSD part keeps 'WSON-6 2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B' and the no-family branches (disagreement, socket) still reach their own branch"
    verification:
      - kind: unit
        ref: "tests/test_generated_text.py#test_kicad_footprints_keep_the_csd_sentence"
        status: pass
      - kind: unit
        ref: "tests/test_generated_text.py#test_an_ambiguous_package_code_supplies_no_family"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-29
status: complete
---

# Phase 10 Plan 29: Pad-count filter for the package family Summary

**A leading-letters-only footprint tie now supplies a package family only from official KiCad footprints within one distinct pad of the vendor footprint, so 6-pin SON parts no longer get "SON-8" written into their description, tags and keywords.**

## Performance

- **Duration:** about 25 min
- **Completed:** 2026-10-29
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `_agreed_family_texts(footprint_index, code, vendor_pads)` keeps, below `FULL_CODE_SCORE`, only tied footprints whose `pad_numbers` is readable and within one of the vendor count; the 10-26 agreement rule then runs unchanged on the survivors (D-28: nothing is guessed). Full-code ties (score 50 and up) are not filtered.
- `footprint_index.FULL_CODE_SCORE = _SCORE_FULL_CODE` is public; scores, tie order, `DEFAULT_LIMIT` and `rank()` are unchanged (2 lines added, 0 deleted).
- `build_plan` passes `len(footprint_pad_numbers(fp_refs[0].node))` (distinct vendor pad numbers) at the only call site.
- Tests pin the rule in both directions on synthetic trees and on the installed KiCad 10 footprints (no skips): 40 tests in `tests/test_generated_text.py`, 194 passed across the plan's verify set.
- WR-06 recorded as fixed in `10-REVIEW-DISPOSITION.md` (`open: 7`, `total: 11`, three lines changed).

## Owner decision

2026-10-29, UAT test 1: "fix WR-06 with the pad-count filter", in the symmetric within-one-pad form. The stricter exposed-pad variant was not adopted; the 7-pad and 10-pad rows pin that choice.

## Task Commits

TDD sequence for Task 1, plain tests for Task 2:

1. **Task 1 RED: failing six-pad SON test, pad-aware fixtures** - `32cb9fc` (test)
2. **Task 1 GREEN: pad filter in planner, public FULL_CODE_SCORE** - `29e3834` (feat); this is the commit cited in 10-REVIEW-DISPOSITION.md
3. **Task 2: boundary rows, SOIC_TIE, installed KiCad 10 tests, WR-06 recorded** - `180da6e` (test)

**Plan metadata:** the docs commit carrying this SUMMARY follows (not counted in `commits: 3`).

## TDD Gate Compliance

- **RED:** `test_a_six_pad_part_takes_no_family_from_a_son_8_tie` (both codes) failed on the planned assertion `text == bare.part_text`: keywords read "Battery Management SON-8 SON65P200X200X80-6N TI Texas" against the no-folder text. The target ran and failed for the intended reason, not an import, fixture or collection fault. The format-based `check tdd-red-evidence` classifier was not run: pytest console output is not one of its supported report formats, so the semantic assessment above stands as the RED evidence.
- **GREEN:** same test passes after `29e3834`.
- **REFACTOR:** none needed.
- **Tracer gate:** after Task 1 the verify command was re-run end to end (104 passed, only environmental skips) before expanding to Task 2.

## Measured KiCad 10 effects

- SON50P150X150X60-6N and SON65P200X200X80-6N (6 pads): both SON-8 footprints are dropped by size; they get the no-folder texts, so SON-8 is gone from UAT test 1's reproduction.
- LQFP48 with 48 pads now gets LQFP-48 (three LQFP-48 footprints of 48 and 49 pads survive and agree); LQFP-100 never appears.
- The CSD part is unchanged: DQK0006B keeps "WSON-6 2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B" and the tag WSON-6_2.1x2.1mm_P0.65mm.
- The existing 2-pad SOIC127P600X175-8N, LQFP48 and SOT-23-5 installed-KiCad tests pass unchanged.

## Known gap for the owner (note, not work)

Under the symmetric rule a 6-lead part with an exposed pad (7 distinct pads, IPC -7N) still gets SON-8 from the 8-pad MicroCrystal SON-8 footprint, because a symmetric tolerance cannot tell which side holds the exposed pad. The owner chose this rule on 2026-10-29 over the stricter exposed-pad variant; the 7-pad row pins it.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The acceptance check `git -C Custom status --porcelain` (and the Wurth one) could not be run meaningfully: the submodules are not checked out in this worktree. The tests write only under `tmp_path` and the worktree is clean apart from the intended files, so the live submodules were not touched.
- Skips seen in the wider verify set are environmental only (licence-restricted vendor samples in `downloaded_examples/` absent); no test in `tests/test_generated_text.py` was skipped.

## Known Stubs

None.

## Threat Flags

None. T-10-52 is mitigated as planned (size-mismatched family never written, pinned by the written-file read-back test and the KiCad 10 six-pad test).

## Next Phase Readiness

Ready for 10-30 (G-10-11). The combined `-m "not wurth"` gate runs there after both gap plans.

## Self-Check: PASSED

- Commits `32cb9fc`, `29e3834`, `180da6e` are ancestors of HEAD.
- All four modified files exist and the plan's acceptance greps pass.
