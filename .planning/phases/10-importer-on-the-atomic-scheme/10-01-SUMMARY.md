---
phase: 10-importer-on-the-atomic-scheme
plan: 01
subsystem: importer
tags: [atomic-scheme, library-naming, kicad-stems, layering-guard]

requires:
  - phase: 09-atomic-check
    provides: atomic_check.ATOMIC_PREFIX, the canonical manufacturer table
provides:
  - "importer.stems: the one Qt-free name rule of the Atomic_ scheme (KICAD10_STEMS, EXCLUDED_STEMS, SHARED_FOOTPRINT_LIBRARY, installed_stems, allowed_stems, NameVerdict, name_verdict)"
  - "Forward layering registrations in tests/test_importer_layering.py for every Phase 10 importer module"
affects: [10-02, 10-03, 10-04, 10-05, 10-06, 10-15, 10-17, 10-18]

actuals:
  tokens: 14000
  tasks: 2
  commits: 3

plan_head_before: 1db839994d9eca570bde31eb0595160af4b2209e
plan_head_after: 2a08ba0b1f661bd200bdfe0b0fdc15b18f361aa6

tech-stack:
  added: []
  patterns:
    - "Leaf module with import-time validation (casefold-unique snapshot, excluded subset of snapshot)"
    - "Verdict dataclass carrying the corrected name, a note and one plain-language reason"

key-files:
  created:
    - kicad_lib_manager/importer/stems.py
    - tests/test_stems.py
  modified:
    - tests/test_importer_layering.py

key-decisions:
  - "Installed stems are accepted only when they match [A-Za-z0-9_-]+, so a file name with a dot, space or path character can never become an allowed library name (T-10-01)"
  - "An installed stem that differs from a snapshot stem only by case replaces the snapshot spelling; the installed set never removes a snapshot stem (A9)"
  - "Refusal reasons are literal prose with Atomic_ written out so the acceptance grep and the owner-facing text stay identical; the prefix constant is still imported from atomic_check and drives matching"

patterns-established:
  - "name_verdict checks in a fixed order: blank, exact, case-only, bare stem, Atomic_ with excluded rest, Atomic_ with any other rest, everything else"

requirements-completed: [LIB-05]

coverage:
  - id: D1
    description: "Only Atomic_ plus an allowed KiCad stem is accepted; bare stems, invented tokens, excluded stems, dotted names and v1 names each get their own plain refusal"
    requirement: LIB-05
    verification:
      - kind: unit
        ref: "tests/test_stems.py#test_refusal_reason"
        status: pass
      - kind: unit
        ref: "tests/test_stems.py#test_allowed_names_pass"
        status: pass
    human_judgment: false
  - id: D2
    description: "A letter-case difference is refused with the official spelling and the note 'Spelling corrected to <name>'"
    requirement: LIB-05
    verification:
      - kind: unit
        ref: "tests/test_stems.py#test_case_only_difference_is_corrected_with_official_spelling"
        status: pass
    human_judgment: false
  - id: D3
    description: "Allowed set is the KiCad 10 snapshot unioned with an installed symbols folder; snapshot is 223 unique stems and the live KiCad 10 folder contains all of them"
    requirement: LIB-05
    verification:
      - kind: unit
        ref: "tests/test_stems.py#test_snapshot_has_223_unique_stems_under_casefold"
        status: pass
      - kind: unit
        ref: "tests/test_stems.py#test_installed_case_spelling_replaces_the_snapshot_spelling"
        status: pass
      - kind: integration
        ref: "tests/test_stems.py#test_snapshot_matches_the_installed_kicad_10"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every Phase 10 importer module is registered in the layering guard before it exists"
    verification:
      - kind: unit
        ref: "tests/test_importer_layering.py"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 01: Atomic_ name rule Summary

**One Qt-free `name_verdict` decides every library name as Atomic_ plus an allowed KiCad 10 stem (223-stem snapshot unioned with an installed KiCad), with a plain one-line reason for every refusal and forward layering registrations for all Phase 10 importer modules.**

## Performance

- **Duration:** about 25 min
- **Tasks:** 2 (one tracer, one TDD)
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- `kicad_lib_manager/importer/stems.py`: `KICAD10_STEMS` (223, copied from RESEARCH Appendix A by script, not retyped), `EXCLUDED_STEMS` (6), `SHARED_FOOTPRINT_LIBRARY = "Atomic_Footprints"`, `installed_stems`, `allowed_stems` (217 by default), `NameVerdict`, `name_verdict`. Import-time checks raise `ValueError` if two snapshot stems fold together or an excluded stem is missing from the snapshot.
- Verdicts: exact name passes; case-only difference refused with the official name and the note "Spelling corrected to <name>"; bare stem, excluded stem (bare and with prefix), invented token, dotted name, v1 name and blank each get their own sentence.
- `tests/test_importer_layering.py`: ALLOWED keys for `importer.stems`, `siblings`, `footprint_index`, `categories`, `keywords`, `footprint_text`, `incoming`, and extended `plan`, `suggest`, `planner`, `form` entries, so the wave-2 plans add their modules without touching that file.
- The live comparison against the installed KiCad 10 ran and passed (every snapshot stem is installed).

## Task Commits

1. **Task 1: Installed KiCad stems to the allowed set to one verdict (tracer)** - `0542c5b` (feat)
2. **Task 2 RED: failing tests for every refusal reason** - `c482d92` (test)
3. **Task 2 GREEN: every refusal gets its own reason** - `2a08ba0` (feat)

REFACTOR: none needed.

**Plan metadata:** the docs commit that adds this SUMMARY.

## TDD Gate Compliance

- **RED:** `tests/test_stems.py` with the tracer's stub reason ("... is not an allowed library name") returned for all non-tracer refusals. 14 tests failed on the planned assertion (`verdict.reason == <expected sentence>`): 13 `test_refusal_reason` cases plus `test_excluded_name_with_wrong_case_names_the_official_stem`; 25 passed. Semantic assessment: each failure is an `AssertionError` on the reason text for the intended input, not an import, collection or fixture fault. This plan is `type: execute` (not `type: tdd`), so the `tdd-red-evidence` classifier was not required; the pytest output was inspected directly.
- **GREEN:** the full reason chain in `name_verdict`; `tests/test_stems.py`, `tests/test_layering.py`, `tests/test_importer_layering.py` give 67 passed.
- **REFACTOR:** none.

## Decisions Made

- Installed stems are filtered to `[A-Za-z0-9_-]+` (T-10-01 hardening beyond the plan text): a file such as `D.Four.kicad_sym` never yields an allowed name.
- Surrounding whitespace is not stripped: `"Atomic_Device "` is refused as "not a library name"; only a blank text gets "Pick or type a library name".
- Prose in reasons writes `Atomic_` literally (the plan's acceptance grep requires the literal sentence); matching uses the imported `ATOMIC_PREFIX`.

## Deviations from Plan

None - plan executed exactly as written. The tracer commit ships `name_verdict` with the plan's "every other input gives ok False for now" stub reason, and Task 2 replaces it.

## Issues Encountered

None. The licence-restricted vendor samples and the `Custom/` submodule are absent in this worktree; this plan's tests do not need them.

## Known Stubs

None.

## Threat Flags

None. T-10-01 is mitigated by the allow-list plus the safe-character filter on installed stems; T-10-02 accepted (file names only).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plans that create the other Phase 10 importer modules can add them without editing the layering guard. `name_verdict` and `SHARED_FOOTPRINT_LIBRARY` are ready for `suggest`, `plan`, `planner` and the form.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/importer/stems.py, tests/test_stems.py, tests/test_importer_layering.py
- FOUND commits: 0542c5b, c482d92, 2a08ba0
