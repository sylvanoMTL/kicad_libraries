---
phase: 10-importer-on-the-atomic-scheme
plan: 18
subsystem: importer
tags: [manufacturers, suggest, cleanup, tests]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "10-17 manufacturers.canonical and suggest.manufacturer_from_datasheet; planner and form no longer call the token helpers"
provides:
  - "Manufacturer table without the v1.0 token field or token_map()"
  - "suggest.py without TokenChoice, manufacturer_token, manufacturer_choice, HOST_TOKENS, MANUFACTURER_ALIASES, _CORPORATE_WORDS"
  - "Tests on the one remaining datasheet-to-manufacturer path"
affects: [phase-10 verification, LIB-04]

actuals:
  tokens: 9000
  tasks: 2
  commits: 2
plan_head_before: 2b82cea4d71cc44949b3f7dd10f2dafeacf6c034
plan_head_after: 36afe6b2ab902a47bea32da7f9607ffc8d18976e

tech-stack:
  added: []
  patterns:
    - "Manufacturer entries are written with keyword fields (aliases=, owner=, hosts=)"
    - "Token-is-gone checks scan dir() for the word instead of spelling removed names, so a repo-wide grep for them stays empty"

key-files:
  created: []
  modified:
    - kicad_lib_manager/manufacturers.py
    - kicad_lib_manager/importer/suggest.py
    - tests/test_manufacturers.py
    - tests/test_naming_suggest.py

key-decisions:
  - "The token-is-gone tests check dir() for names containing 'token' or 'choice' rather than naming the removed helpers, so the plan's repo-wide grep acceptance criteria hold"

patterns-established:
  - "One datasheet-to-manufacturer path: suggest.manufacturer_from_datasheet (D-23)"

requirements-completed: [LIB-04]

coverage:
  - id: D1
    description: "Manufacturer table has no token field and no token_map; entries use keyword fields"
    requirement: LIB-04
    verification:
      - kind: unit
        ref: "tests/test_manufacturers.py#test_the_v1_library_token_is_gone"
        status: pass
    human_judgment: false
  - id: D2
    description: "suggest.py has none of the v1.0 token helpers and nothing in the app or tests imports a removed name"
    requirement: LIB-04
    verification:
      - kind: unit
        ref: "tests/test_naming_suggest.py#test_manufacturer_from_datasheet_is_the_only_datasheet_to_manufacturer_path"
        status: pass
      - kind: other
        ref: "grep -rn --include=*.py -E 'manufacturer_choice|manufacturer_token|token_map|HOST_TOKENS|MANUFACTURER_ALIASES|TokenChoice' kicad_lib_manager tests (prints nothing)"
        status: pass
    human_judgment: false
  - id: D3
    description: "manufacturer_from_datasheet, datasheet_host, registered_domain, is_aggregator_host and canonical are tested directly"
    requirement: LIB-04
    verification:
      - kind: unit
        ref: "tests/test_naming_suggest.py#test_manufacturer_from_datasheet"
        status: pass
      - kind: unit
        ref: "tests/test_manufacturers.py#test_canonical_gives_the_table_name_or_the_value_unchanged"
        status: pass
    human_judgment: false
  - id: D4
    description: "The not-wurth suite is green"
    verification:
      - kind: integration
        ref: "pytest -m 'not wurth' -q (2770 passed, 31 skipped, 0 failed)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 18: Remove the v1.0 manufacturer token code Summary

**The v1.0 manufacturer token (field, token_map and all suggest.py token helpers) is deleted; manufacturer_from_datasheet is the only datasheet-to-manufacturer path and the tests now exercise it.**

## Performance

- **Duration:** about 25 min (most of it the 8m45s full suite run)
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `manufacturers.py`: removed the `token` field of `Manufacturer` and `token_map()`; every `MANUFACTURERS` entry is now written with keyword fields. The module still imports only the standard library, so `tests/test_layering.py` is unchanged.
- `importer/suggest.py`: removed `TokenChoice`, `manufacturer_token`, `manufacturer_choice`, `HOST_TOKENS`, `MANUFACTURER_ALIASES` and `_CORPORATE_WORDS`, plus the now-unused `re` and `unicodedata` imports. The module docstring no longer mentions the removed helpers. Kept: `AGGREGATOR_DOMAINS`, `_SLD_LABELS`, `datasheet_host`, `registered_domain`, `is_aggregator_host`, `manufacturer_from_datasheet`.
- `tests/test_manufacturers.py`: dropped the token tests and the V1_ALIASES table, kept the fold, lookup, owner, hosts and index tests, added canonical rows (alias to table name, unknown value unchanged, empty stays empty) and a test that no token name or field is left.
- `tests/test_naming_suggest.py`: replaced the token and host-token tests with `manufacturer_from_datasheet` tests (ti.com, maximintegrated.com, linear.com, tdk.com, gct.co, digikey and snapeda links, "~", empty, file and malformed links) and direct tests for `datasheet_host`, `registered_domain` and `is_aggregator_host`; every layout test is untouched.
- Repo-wide grep for the removed names over `kicad_lib_manager`, `tests` and the root scripts prints nothing. `-m "not wurth"` run: 2770 passed, 31 skipped (submodules and licence-restricted samples absent in the worktree), 0 failed.

## Task Commits

1. **Task 1: token code removed from the table and suggest.py** - `bf1e7e4` (refactor)
2. **Task 2: datasheet-host tests on manufacturer_from_datasheet** - `36afe6b` (test)

**Plan metadata:** committed after this file (docs: complete plan)

## Files Created/Modified

- `kicad_lib_manager/manufacturers.py` - Manufacturer without token; no token_map
- `kicad_lib_manager/importer/suggest.py` - v1 token helpers removed, docstring updated
- `tests/test_manufacturers.py` - token tests removed, canonical and token-is-gone tests added
- `tests/test_naming_suggest.py` - tests moved to manufacturer_from_datasheet and the host helpers

## Decisions Made

- The token-is-gone checks scan `dir()` for names containing "token" (and "choice" for suggest) instead of spelling the removed names. Task 1 asks for a test that `token_map` is absent while Task 2's acceptance grep over `tests/` requires the removed names to appear nowhere; the `dir()` scan satisfies both and is broader than a single-name check.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Wrong expectation in my own new test**
- **Found during:** Task 2
- **Issue:** `test_datasheet_host` expected `E2E.TI.COM` for `https://E2E.TI.COM:443/a`, but `urlsplit().hostname` lowercases.
- **Fix:** expectation changed to `e2e.ti.com`.
- **Files modified:** tests/test_naming_suggest.py
- **Committed in:** 36afe6b

**2. [Plan conflict, resolved] Task 1 token-gone test vs Task 2 acceptance grep**
- See Decisions Made. No other file outside the plan's list used a removed name, so no further edits were needed.

---

**Total deviations:** 1 auto-fixed (test expectation), 1 plan-wording conflict resolved.
**Impact on plan:** none on scope.

## Issues Encountered

- Task 1's commit leaves `tests/test_naming_suggest.py` importing removed names until Task 2's commit lands; the plan's Task 1 verify does not run that file, and Task 2 fixes it. The wave gate ran after both commits.
- The first background full-suite launch failed because of a relative redirect path; it was rerun with an absolute path.

## Known Stubs

None.

## Threat Flags

None. T-10-40 mitigated: one inference path (guarded against aggregator hosts) remains, and the repo-wide grep and layering tests show nothing imports the removed names.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

LIB-04 token cleanup is done. The manufacturer table and suggest.py now carry only the Atomic_ scheme code and the D-23 datasheet path.

## Self-Check: PASSED

- Files modified exist; commits `bf1e7e4` and `36afe6b` are on this branch.
- Acceptance greps return 0 / nothing; `pytest -m "not wurth"`: 2770 passed, 0 failed.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*
