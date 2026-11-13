---
phase: 10-importer-on-the-atomic-scheme
plan: 27
subsystem: importer-keywords
tags: [keywords, can-bus, wr-02, gap-closure, tdd]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "generate_keywords and INTERFACE_WORDS (10-04), planner keyword wiring (10-23, 10-25)"
provides:
  - "CAN keyword only from the upper-case whole word CAN or a CAN companion phrase (WR-02 closed)"
  - "CASED_INTERFACE_WORDS and _cased_matched in keywords.py"
affects: [10-28 review disposition (WR-02 Source cell)]

actuals:
  tokens: 4200
  tasks: 2
  commits: 3

plan_head_before: 7f4271db36102d446842307b8e6bd888c2ef9bac
plan_head_after: da613e9588fb6e0c43088584888389dbf2a7857d

tech-stack:
  added: []
  patterns:
    - "Exact-case whole-word match against the original text for interface words that are also English words"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/keywords.py
    - tests/test_keywords.py

key-decisions:
  - "SPI, UART and BLE stay on the any-case match: planner's judgement (Flagged Assumptions of 10-27-PLAN.md), not an owner decision"
  - "All-caps prose such as 'YOU CAN USE IT' still gives CAN: residual the owner accepted on 2026-10-28 ('Accept and record it'), pinned by test_all_caps_can_gives_the_can_keyword"

requirements-completed: [FLD-01]

coverage:
  - id: D1
    description: "The English word 'can' in lower or mixed case gives no CAN keyword, from generate_keywords through a planned install of the CSD sample"
    requirement: FLD-01
    verification:
      - kind: unit
        ref: "tests/test_keywords.py#test_the_english_word_can_gives_no_can_keyword"
        status: pass
      - kind: integration
        ref: "tests/test_keywords.py#test_a_planned_install_writes_can_only_for_a_can_bus_part"
        status: pass
      - kind: unit
        ref: "tests/test_keywords.py#test_ordinary_can_gives_no_can_keyword"
        status: pass
    human_judgment: false
  - id: D2
    description: "A real CAN-bus text gives CAN exactly once in every common spelling; the all-caps prose residual and SPI/UART/BLE any-case behaviour are pinned"
    requirement: FLD-01
    verification:
      - kind: unit
        ref: "tests/test_keywords.py#test_can_bus_text_gives_the_can_keyword_once"
        status: pass
      - kind: unit
        ref: "tests/test_keywords.py#test_all_caps_can_gives_the_can_keyword"
        status: pass
      - kind: unit
        ref: "tests/test_keywords.py#test_spi_uart_and_ble_still_match_in_any_case"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-10-28
status: complete
---

# Phase 10 Plan 27: CAN keyword false positive (WR-02) Summary

**CAN is now generated only from the upper-case whole word CAN or a CAN companion phrase (can bus, canbus, can fd, canfd, can transceiver, can controller), so "You can use it" no longer writes a permanent wrong CAN keyword into the symbol.**

## Performance

- **Duration:** about 15 min
- **Tasks:** 2 (tracer + auto, both TDD)
- **Files modified:** 2

## Accomplishments

- `INTERFACE_WORDS` lost its bare-word `("can", "CAN")` entry; six CAN companion phrases (any case) took its place.
- New `CASED_INTERFACE_WORDS` (`("CAN", "CAN")`) matched by the new `_cased_matched` helper against the original-case text, whole words only ("CAN-FD" and "(CAN)" give CAN; "can", "Can", "cannot", "scan" do not). `generate_keywords` adds its result right after the casefolded interface words; the final de-duplication keeps CAN once.
- Tests: 22 new cases in `tests/test_keywords.py` (39 -> 63 tests), including an end-to-end `build_plan` check on the CSD sample through the `atomic_custom` fixture (no write outside tmp_path).

## Task Commits

1. **Task 1 RED:** `a4e93d6` (test) - two failing tests, failing on the CAN-absent assertions
2. **Task 1 GREEN:** `f35486b` (feat) - **the commit that changed keywords.py; plan 10-28 cites it in 10-REVIEW-DISPOSITION.md**
3. **Task 2:** `da613e9` (test) - spelling matrix, all-caps residual, SPI/UART/BLE, vocabulary rule

## TDD

- **RED:** `test_the_english_word_can_gives_no_can_keyword` failed on `assert "CAN" not in [..., 'USB', 'CAN']`; `test_a_planned_install_writes_can_only_for_a_can_bus_part` failed on `assert "can" not in [... casefolded keywords]`. Both are assertion failures on the planned behaviour (semantic assessment: target tests executed, failed for the intended reason, no import or fixture fault). pytest output is not a format the `tdd-red-evidence` classifier supports, so no classifier record was produced; the assessment above stands alone.
- **GREEN:** the keywords.py change above; 41 tests in the file pass.
- **Task 2:** its rows passed on first run, because Task 1's mechanisms already satisfy them; no keywords.py change was needed and no new RED commit exists for it (the plan says to fix only if a row fails). `test_all_caps_can_gives_the_can_keyword` is documented to pass before and after Task 1.
- No REFACTOR commit.

## Notes for plan 10-28 (WR-02 Source cell)

- SPI, UART and BLE were left on the any-case match by the **planner's judgement** (Flagged Assumptions of 10-27-PLAN.md), **not by an owner decision**. A lower-case "spi", "uart" or "ble" in ordinary text still gives its keyword. Pinned by `test_spi_uart_and_ble_still_match_in_any_case`.
- All-caps prose such as "YOU CAN USE IT" still gives CAN. This is a residual the **owner accepted on 2026-10-28 ("Accept and record it")**, pinned by `test_all_caps_can_gives_the_can_keyword`.
- One-token spellings without a companion phrase ("CAN2.0B", "CANopen") give no CAN; recorded in the plan's Flagged Assumptions.

## Decisions Made

None beyond the plan; both notes above follow the plan.

## Deviations from Plan

None - plan executed exactly as written. (Process note: a first edit wrote `"\n"` instead of `"\\n"` in `_cased_matched`; caught before the GREEN commit and corrected, so the committed code matches `_phrase_text`'s literal backslash-n handling.)

## Issues Encountered

None. `Custom/` and `WurthElektronik/` submodules are not checked out in this worktree; the new tests use the synthetic `atomic_custom` fixture and are unaffected.

## Verification

- `pytest tests/test_keywords.py tests/test_importer_layering.py tests/test_layering.py -q`: 92 passed.
- `pytest tests/test_keywords.py -q`: 63 passed; `-k "can or spi"`: 24 passed.
- Acceptance greps: `CASED_INTERFACE_WORDS` 1 line, `_cased_matched(CASED_INTERFACE_WORDS` 1 line, bare-word entry 0, `"CAN")` on 7 lines, `("spi", "SPI")` 1 line.
- The combined `-m "not wurth"` gate runs in plan 10-28 Task 3.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- keywords.py and test_keywords.py exist and are committed; commits a4e93d6, f35486b, da613e9 are ancestors of HEAD.
