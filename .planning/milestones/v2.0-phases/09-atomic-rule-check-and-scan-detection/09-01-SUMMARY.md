---
phase: 09-atomic-rule-check-and-scan-detection
plan: 01
subsystem: manufacturers
tags: [python, manufacturer-table, aliases, folding, layering]

requires:
  - phase: 07-importer-fields
    provides: importer.suggest MANUFACTURER_ALIASES and manufacturer_token (v1.0 token map)
provides:
  - kicad_lib_manager/manufacturers.py, the one Qt-free canonical manufacturer table (Manufacturer, MANUFACTURERS, CORPORATE_WORDS, fold, lookup, ManufacturerMatch, token_map)
  - importer.suggest.MANUFACTURER_ALIASES and _CORPORATE_WORDS derived from the table
  - tests/test_manufacturers.py (FLD-02 fold, lookup, uniqueness, acquired-brand tests)
affects: [09-03 atomic check, 10 importer, 13 migration]

actuals:
  tokens: 6200
  tasks: 2
  commits: 2
plan_head_before: 45caf99bddaf5a8c864dbe8263c194d45e93a850
plan_head_after: 7f991d3625340d38358c275a4d4753a526e685e0

tech-stack:
  added: []
  patterns:
    - "Stdlib-only leaf module holding a frozen-dataclass table, validated at import by an index builder that raises on key collisions"
    - "Legacy map demoted to a view derived from the canonical table, pinned by an equality test"

key-files:
  created:
    - kicad_lib_manager/manufacturers.py
    - tests/test_manufacturers.py
  modified:
    - kicad_lib_manager/importer/suggest.py
    - tests/test_layering.py
    - tests/test_importer_layering.py

key-decisions:
  - "Murata and TDK seeded as 'Murata' and 'TDK' (not named in D-07); flagged for owner confirmation before Phase 10 writes them"
  - "token and owner fields kept on Manufacturer: token only for importer.suggest until Phase 10 (LIB-04), owner informational (D-08)"

patterns-established:
  - "One canonical table, many views: derive legacy maps with token_map() rather than keeping a second literal"

requirements-completed: [FLD-02]

coverage:
  - id: D1
    description: "manufacturers.lookup resolves every Custom/ spelling to one canonical entry and distinguishes the exact canonical spelling from alias, case and suffix variants"
    requirement: FLD-02
    verification:
      - kind: unit
        ref: "tests/test_manufacturers.py#test_every_custom_spelling_resolves_to_its_canonical_entry"
        status: pass
      - kind: unit
        ref: "tests/test_manufacturers.py#test_exact_is_true_only_for_the_identical_canonical_spelling"
        status: pass
    human_judgment: false
  - id: D2
    description: "Acquired brands (Maxim Integrated, Linear Technology, InvenSense) keep their own canonical name with the owner recorded"
    requirement: FLD-02
    verification:
      - kind: unit
        ref: "tests/test_manufacturers.py#test_acquired_brand_keeps_its_own_name_and_records_its_owner"
        status: pass
    human_judgment: false
  - id: D3
    description: "suggest.MANUFACTURER_ALIASES is derived from the table and still maps every v1.0 key to the same token"
    requirement: FLD-02
    verification:
      - kind: unit
        ref: "tests/test_manufacturers.py#test_suggest_aliases_are_derived_from_the_table"
        status: pass
      - kind: unit
        ref: "tests/test_naming_suggest.py (50 tests, unchanged)"
        status: pass
    human_judgment: false
  - id: D4
    description: "A table edit that puts two companies on one folded key fails at import"
    requirement: FLD-02
    verification:
      - kind: unit
        ref: "tests/test_manufacturers.py#test_index_rejects_two_entries_that_fold_to_one_key"
        status: pass
    human_judgment: false
  - id: D5
    description: "Canonical spellings for Murata and TDK, which D-07 does not name, match what the owner wants written into committed parts"
    verification: []
    human_judgment: true
    rationale: "A naming choice only the owner can confirm; costly to change once Phase 10 writes parts"

duration: 14min
completed: 2026-10-26
status: complete
---

# Phase 9 Plan 01: Canonical Manufacturer Table Summary

**One Qt-free manufacturer table (12 companies with aliases, library token and owner) with fold/lookup/token_map, and importer.suggest's token map now derived from it so the two lists cannot drift**

## Performance

- **Duration:** 14 min
- **Tasks:** 2
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments
- `kicad_lib_manager/manufacturers.py` holds `Manufacturer`, `MANUFACTURERS`, `CORPORATE_WORDS`, `fold`, `_index`, `lookup`, `ManufacturerMatch` and `token_map`; it imports only `re`, `unicodedata` and `dataclasses`.
- `lookup('GCT')` returns "Global Connector Technology" with `exact` False; the canonical spelling returns `exact` True. Every spelling found in Custom/ resolves to exactly one entry.
- Acquired brands keep their own name (Maxim Integrated, Linear Technology, InvenSense) with `owner` recorded; they never resolve to the owner.
- `suggest.MANUFACTURER_ALIASES = token_map()` and `_CORPORATE_WORDS = CORPORATE_WORDS`; the 50 existing `test_naming_suggest.py` tests pass unchanged and a test pins all 20 v1.0 keys.
- `_BY_FOLDED = _index(MANUFACTURERS)` runs at import, so a colliding table edit fails immediately (T-09-01).

## Task Commits

1. **Task 1: Manufacturer table as a leaf module, wired through suggest** - `8f7f4f5` (feat, tracer)
2. **Task 2: Folding, lookup, uniqueness and acquired-brand rules pinned by tests** - `7f991d3` (test)

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified
- `kicad_lib_manager/manufacturers.py` - the canonical table and its fold/lookup/token_map helpers
- `kicad_lib_manager/importer/suggest.py` - map and corporate words derived from the table
- `tests/test_manufacturers.py` - V1_ALIASES, tracer tests and the 9 behaviour tests (11 test functions, 31 cases)
- `tests/test_layering.py` - `manufacturers` registered in ALLOWED and `_CODE` (Qt-free import check)
- `tests/test_importer_layering.py` - `manufacturers` allowed for `importer.suggest`

## Decisions Made
- Murata and TDK seeded as "Murata" and "TDK" per the plan's flagged assumption. Flagged for the owner to confirm before Phase 10 writes them; no Custom/ part uses either today.
- `Manufacturer.token` is kept only so `suggest` keeps working until Phase 10 drops it (LIB-04); `owner` is informational and never changes the Manufacturer field (D-08).

## Deviations from Plan

None - plan executed exactly as written.

## TDD Gate Compliance

Task 2 is marked `tdd="true"`, but the implementation it tests (`fold`, `_index`, `lookup`, `token_map`) was already committed by the Task 1 tracer, as the plan's own Task 1 action specifies. A strict RED commit was therefore not possible: the new behaviour tests passed on first run (31 passed), which tdd.md calls "unexpected green". This is by plan design (Task 2 action: "fix manufacturers.py only if a case fails"). To confirm the tests are not vacuous, I mutated `lookup` so `exact` was always True; `test_exact_is_true_only_for_the_identical_canonical_spelling` failed as expected, and the file was then restored with `git checkout -- <file>`. Commit order is `feat(09-01)` then `test(09-01)`; no `refactor(09-01)` commit was needed.

## Issues Encountered
None. `Custom/` and `WurthElektronik/KiCad-Library` are not checked out in this worktree; none of this plan's tests depend on them, and `git status --short Custom` shows no change.

## Known Stubs
None.

## Threat Flags
None. No new network, auth, file-access or schema surface; T-09-01 and T-09-02 mitigations are implemented and tested.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 09-03 (atomic check) can import `lookup` and read `exact` to report alias variants with their canonical name.
- Open item for the owner: confirm the "Murata" and "TDK" canonical spellings before Phase 10.

## Self-Check: PASSED

- FOUND: kicad_lib_manager/manufacturers.py, tests/test_manufacturers.py
- FOUND commits: 8f7f4f5, 7f991d3
- `pytest tests/test_manufacturers.py tests/test_naming_suggest.py tests/test_layering.py tests/test_importer_layering.py` - 106 passed

---
*Phase: 09-atomic-rule-check-and-scan-detection*
*Completed: 2026-10-26*
