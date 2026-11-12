---
phase: 10-importer-on-the-atomic-scheme
plan: 14
subsystem: importer
tags: [kicad, footprint, token-stream, planner, conflicts]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "10-12 shared Atomic_Footprints.pretty; 10-13 one footprint per part"
provides:
  - "Token-stream footprint identity: a footprint equal in tokens to the shared one is reused, not written and not a conflict"
  - "Rename suggestion <FP>_<MPN>, then <FP>_<MPN>_<n> when taken"
  - "Footprint conflict text and an Overwrite warning that name every other Custom/ part linking the footprint"
affects: [10-importer-on-the-atomic-scheme, preview, import-dialog]

plan_head_before: 935c5f82a8e8ae346ae7097b0d30e5c4ca5c12da
plan_head_after: a682c71a470e1c04b6a018b0af6c8200f5eb4c48

actuals:
  tokens: 5500
  tasks: 2
  commits: 5

tech-stack:
  added: []
  patterns:
    - "A _FileSpec compares planned and existing content through a (name, path, digest) callable, so a spec can fall back to a parsed compare"
    - "Conflict text gets an optional linked_by clause from the spec; the dependent-part scan runs lazily and once per name"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/planner.py
    - tests/test_shared_footprints.py
    - tests/test_install_plan.py
    - tests/test_import_dialog.py

key-decisions:
  - "Reuse is reported for any footprint that needs no write (exact bytes or equal tokens), through a _Decision.reused flag and one INFO issue"
  - "The linking scan skips only the symbol being installed under its default name; it reads Custom/Symbols only (WurthElektronik and KiCad cannot link Atomic_Footprints)"

requirements-completed: [LIB-06]

coverage:
  - id: D1
    description: "A footprint equal to the shared one by token stream (layout, indentation, line endings ignored) is reused with no write, no conflict, and an install.footprint_reused info issue"
    requirement: LIB-06
    verification:
      - kind: unit
        ref: "tests/test_shared_footprints.py#test_tracer_the_same_footprint_in_another_format_is_reused"
        status: pass
    human_judgment: false
  - id: D2
    description: "A different footprint gets the Overwrite / Rename / Skip conflict with Rename pre-filled as <FP>_<MPN>, then <FP>_<MPN>_<n>"
    requirement: LIB-06
    verification:
      - kind: unit
        ref: "tests/test_shared_footprints.py#test_tracer_a_different_footprint_offers_the_part_number_as_its_new_name"
        status: pass
      - kind: unit
        ref: "tests/test_shared_footprints.py#test_the_rename_suggestion_moves_on_when_the_part_number_name_is_taken"
        status: pass
    human_judgment: false
  - id: D3
    description: "The conflict text and the Overwrite warning name every other linking part as '<symbol> (<library>)', cut at 20 names, excluding the part being installed"
    requirement: LIB-06
    verification:
      - kind: unit
        ref: "tests/test_shared_footprints.py#test_the_conflict_names_every_other_part_linking_the_footprint"
        status: pass
      - kind: unit
        ref: "tests/test_shared_footprints.py#test_overwrite_warns_with_the_parts_it_changes"
        status: pass
      - kind: unit
        ref: "tests/test_shared_footprints.py#test_more_than_twenty_linking_parts_are_cut_short"
        status: pass
    human_judgment: false
  - id: D4
    description: "3D model conflicts keep their byte comparison and <stem>_<n><ext> suggestion"
    requirement: LIB-06
    verification:
      - kind: unit
        ref: "tests/test_shared_footprints.py#test_a_model_conflict_still_suggests_the_next_numbered_name"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 14: Shared footprint clash rules Summary

**The shared Atomic_Footprints library now reuses a footprint equal by token stream, offers `<FP>_<MPN>` as the rename for a real clash, and names every other part that links the footprint before an Overwrite.**

## Performance

- **Duration:** about 45 min
- **Completed:** 2026-10-27
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- `_FileSpec.same` takes `(name, existing path, sha256)`; the footprint spec accepts equal bytes, else compares `sexpr.token_stream` of both parsed files (size and node caps, any failure means not equal). Reformatted copies (LF vs CRLF, tabs vs spaces) are reused with no op and no conflict, with an INFO `install.footprint_reused`.
- The footprint rename suggestion is `<FP>_<MPN>` (for CSD85301Q2: `DQK0006B_CSD85301Q2`), falling back to the next free `<FP>_<MPN>_<n>`.
- `_linking_symbols(layout, link, *, skip)` reads Custom/Symbols with a bytes prefilter on the quoted link, parses only matching files under the caps, and returns `<symbol> (<library>)`. The conflict text ends with `; it is linked by N other part(s): ...`, and an Overwrite adds WARNING `install.footprint_shared`. Lists are cut at 20 with `, and <n> more`.
- 3D model conflicts are unchanged.

## Task Commits

1. **Task 1 (tracer): reuse and `<FP>_<MPN>` rename** - RED `8e09bae` (test), GREEN `8fdb744` (feat)
2. **Task 2 (tdd): linking parts named on conflict and Overwrite** - RED `7fb0b22` (test), GREEN `bb194a4` (feat), expectations `a682c71` (test)

**Plan metadata:** the docs commit that adds this file.

## TDD Gate Compliance

Task 2 followed RED then GREEN. RED: five of nine new tests failed on the planned assertion (conflict text lacked the linking clause, no `install.footprint_shared` issue); the other four describe behaviour that already held (plain text with no linker, rename moving on when taken, model suggestion, no warning while unresolved) and passed at once. Semantic assessment: the failing tests ran the target code and failed on the planned text, not on setup errors. Task 1's tracer tests were committed failing first as well (reused footprint produced a blocking conflict; suggestion was `DQK0006B_2`).

## Files Created/Modified
- `kicad_lib_manager/importer/planner.py` - token-stream footprint identity, `_suggest_footprint_rename`, `_linking_symbols`, conflict clause and Overwrite warning
- `tests/test_shared_footprints.py` - 11 new D-19 tests (22 in the file)
- `tests/test_install_plan.py` - footprint rename expectations now `FP_PART` / `FP_PART_2`
- `tests/test_import_dialog.py` - rename suggestion now `DQK0006B_CSD85301Q2`

## Decisions Made
- A footprint that needs no write reports `install.footprint_reused`, whether the match is by bytes or by tokens.
- The linking scan skips the symbol being installed under its default name; the scan covers Custom/Symbols only, as the plan assumed.

## Deviations from Plan

**1. [Rule 1 - Bug in plan input] Tracer reformat step adapted**
- **Found during:** Task 1
- **Issue:** the plan asks to replace LF with CRLF and tabs with two spaces in the installed footprint; the installed UL footprint already uses CRLF and two-space indents, so that edit changed nothing.
- **Fix:** the test reformats the other way (CRLF to LF, each two-space indent to a tab), which is still a layout-only change.
- **Files modified:** tests/test_shared_footprints.py
- **Committed in:** 8e09bae

**2. [Rule 1 - Test expectation] v1.0 rename expectations updated**
- **Found during:** Task 2 wave run
- **Fix:** `FP_2` became `FP_PART` in `test_conflict_suggested_names` and `test_resolution_rename_footprint_uses_the_suggestion`; the taken-name case now pre-creates `fp_part.kicad_mod` and expects `FP_PART_2`; `DQK0006B_2` became `DQK0006B_CSD85301Q2` in the dialog test (the plan named these updates).
- **Committed in:** a682c71

**Total deviations:** 2 (one test input adapted, one planned expectation update). **Impact:** none on behaviour.

## Issues Encountered
- The plan's file list names tests/test_install_apply.py and tests/test_import_preview.py; neither held a changed expectation (their FP_2 uses are caller-typed rename names), so they are untouched.
- Known limit: if the incoming symbol is renamed to another name, an existing symbol of the original name that links the footprint is not listed (it is skipped as "the part being installed").

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
Clash rules for the shared library are in place; the dialog shows the longer conflict text as is.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*

## Self-Check: PASSED

- planner.py, test_shared_footprints.py, test_install_plan.py, test_import_dialog.py exist and carry the changes
- Commits 8e09bae, 8fdb744, 7fb0b22, bb194a4, a682c71 are on this branch
- `pytest -m "not wurth"`: 2712 passed, 30 skipped, 0 failed; `tests/test_shared_footprints.py`: 22 passed
- Acceptance greps: token_stream( , install.footprint_reused, install.footprint_shared, def _linking_symbols( each print a line in planner.py
