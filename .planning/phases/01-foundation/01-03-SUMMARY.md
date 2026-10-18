---
phase: 01-foundation
plan: 03
subsystem: testing
tags: [sexpr, tokenizer, pytest, fuzz, round-trip, splice]

requires:
  - phase: 01-foundation
    provides: "Plan 01 tracer sexpr.py (parse, Node, Edit, apply_edits, quote, unquote, SexprError) and the assert_tiles fixture"
provides:
  - "tests/test_sexpr.py: 81 tests proving tokenizer spans, error positions, hostile-input resistance, the apply_edits splice contract and the quote/unquote escape set independently of any corpus file"
  - "Confirmation that the Plan 01 sexpr.py already satisfies the hardened contract (no source change needed)"
affects: [kicad_files, edits, importer phases 3-7]

actuals:
  tokens: 9500
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Every tokenizer test also asserts assert_tiles plus apply_edits(text, []) == text via a shared _check helper"
    - "Hostile-input tests build their data in memory (100k-deep nesting, ~2 MB library, seeded random.Random(1234) fuzz)"

key-files:
  created:
    - tests/test_sexpr.py
  modified: []

key-decisions:
  - "No change to kicad_lib_manager/sexpr.py: the tracer implementation already met every behaviour in the plan, so the new tests pin it rather than reshape it"

patterns-established:
  - "Seeded generators and in-memory fixtures only; the sexpr suite never reads the Custom submodule or any repo file, so it runs with Custom/ uninitialised"

requirements-completed: [FOUND-03, FOUND-04]

duration: 12min
completed: 2026-10-18
status: complete
plan_head_before: ccda2fd23dfca20abaf95b5ef14cc280900db9c1
plan_head_after: ec1f1773b6b50354e13f747b8b5c87adf9958d72
commits: 2
---

# Phase 1 Plan 03: Hardened S-expression layer Summary

**81-test suite pinning the span-splicing S-expression tokenizer: exact tiling over edge cases and 500-form fuzz, SexprError line/col, 100k-deep and ~2 MB inputs, apply_edits ordering/overlap rules, and the KiCad quote/unquote escape set.**

## Performance

- **Duration:** about 12 min
- **Tasks:** 2
- **Files modified:** 1 (tests/test_sexpr.py created; sexpr.py unchanged)

## Accomplishments
- Tokenizer edge cases (empty, whitespace-only, no trailing newline, `()`, `""`, adjacent forms, exact numeric atoms, NBSP/form-feed/U+2028 inside atoms) all tile exactly and round-trip through `apply_edits(text, [])`.
- `sexpr.unterminated`, `sexpr.unbalanced` and `sexpr.unclosed` report the correct 1-based line and column, including CRLF input (same line numbers as LF).
- 100,000-deep nesting parses without RecursionError with shallow reprs; a ~2 MB generated library parses in well under the 3 s budget (about 0.4 s); 8-thread parsing yields identical span lists; 500-form seeded fuzz tiles and round-trips.
- A negative test proves `assert_tiles` rejects a span shifted by one character, so corpus identity checks are not vacuous.
- `apply_edits` ordering (input order for ties, insert before replace at one offset, touching allowed) and ValueError on overlap or out-of-range edits are pinned.
- `quote`/`unquote` escape set pinned (backslash, quote, LF, CR escaped; TAB raw), including an injection string `") (evil "` that stays a single str token and round-trips.

## Task Commits

1. **Task 1: Tokenizer edge cases, error positions and hostile-input resistance** - `006a2f2` (test)
2. **Task 2: Splice contract and quote/unquote escape set** - `ec1f177` (test)

## Files Created/Modified
- `tests/test_sexpr.py` - tokenizer, error, nesting, fuzz, thread, splice and quoting tests

## Decisions Made
None - followed plan as specified. The plan's "confirm or fix" instruction on sexpr.py resolved to "confirm": no defect was found.

## TDD Gate Compliance

Both tasks were marked `tdd="true"`, but no RED commit exists: the Plan 01 tracer sexpr.py already implemented the full contract, so every new test passed on first valid run (the only failures were two sizing mistakes in my own generated-input tests, fixed before the first commit). The tests are therefore characterisation tests of an existing implementation, committed as `test(01-03)`, and there is no `feat` commit. The tests were not independently mutation-checked against a broken tokenizer in this run; non-vacuity of the tiling checker is covered by the explicit shifted-span negative test.

## Deviations from Plan

None - plan executed exactly as written (aside from the TDD note above, which follows from the implementation already being correct).

## Issues Encountered
- The worktree had no `env/`; created it with `py -3.14 -m venv env` and installed `requirements-dev.txt` (gitignored, never staged).
- Two of my first-draft size assertions (2 MB library, 200 KB thread input) were wrong because the generated symbols were too small; added a filler property and sized the thread test at 200 symbols.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None.

## Next Phase Readiness
- Span correctness is proven independently of the Custom submodule; kicad_files and later importer plans can rely on `parse`/`apply_edits`/`quote`/`unquote` as pinned here.

## Self-Check: PASSED
- tests/test_sexpr.py exists; commits 006a2f2 and ec1f177 are ancestors of HEAD; `pytest tests/test_sexpr.py tests/test_edits.py` gives 82 passed, 1 skipped (Custom submodule absent).

---
*Phase: 01-foundation*
*Completed: 2026-10-18*
