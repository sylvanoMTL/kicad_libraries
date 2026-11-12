---
phase: 03-package-intake-and-naming
plan: 06
subsystem: importer
tags: [naming, suggestion, manufacturer, vocabulary, layout, stdlib]

requires:
  - phase: 03-package-intake-and-naming
    provides: "03-01 suggest.py tracer (suggest_library, placeholder_tokens), 03-02 zipfixtures synthetic Custom/ layout, 03-05 naming.sanitize_name and case_clash"
provides:
  - "importer/layout.py: RepoLayout and fresh, read-only, uncached Custom/ listings (symbols, footprints, 3D models, union with has_symbols/has_footprints)"
  - "Full D-02 manufacturer chain: alias table, host table, aggregator deny-list, low-confidence guesses"
  - "D-01 SubCategory from the existing Custom/ vocabulary (whole-token match, verbatim library spelling)"
  - "D-03 ranked alternatives (max 5, deterministic), matches_existing = exact equality"
  - "D-04 placeholder_tokens contract documented for Phases 4 and 5"
affects: [04-install-planner, 05-import-dialog]

actuals:
  tokens: 21000
  tasks: 2
  commits: 4
plan_head_before: bce329ae46b61858b754d393ea3c42d9d07f0cbc
plan_head_after: 1a7d28f4b8c9acab018ae6b6418602e65c703ced

tech-stack:
  added: []
  patterns:
    - "Naming helpers take plain strings so an edited name needs no suggestion object (assumption-delta: promote the chosen name)"
    - "Listings re-read the disk on every call and only iterdir/rglob/is_file/is_dir"

key-files:
  created:
    - kicad_lib_manager/importer/layout.py
    - tests/test_naming_suggest.py
  modified:
    - kicad_lib_manager/importer/suggest.py

key-decisions:
  - "Mapped tokens are tried in D-02 order (property alias, then host table) before any unmapped guess, so MF 'Texas Instr.' with a ti.com datasheet gives the confident TI"
  - "SubCategory is copied verbatim in the matched library's spelling; Type and Manufacturer keep canonical tokens, so an existing ic_battery_charger_ti yields IC_battery_charger_TI plus a case_clash warning and matches_existing False"
  - "Host-guess label keeps only [a-z0-9] so a guess can never add an extra '_' token to the library name"
  - "Low-confidence message lists each unsure token with its source, e.g. 'Acme (property), SubCategory (placeholder)'"

patterns-established:
  - "Vocabulary match uses whole tokens of description + keywords + Value after collapsing literal backslash-n escapes, NFKD and casefold"
  - "Ranking: 3 x same manufacturer + 2 x same Type + shared middle tokens, score > 0, sorted by (-score, casefolded name), the primary is never replaced"

requirements-completed: [LIB-01]

coverage:
  - id: D1
    description: "Fresh read-only Custom/ listing (layout.py) that never creates anything and returns [] when Custom/ is missing"
    requirement: LIB-01
    verification:
      - kind: unit
        ref: "tests/test_naming_suggest.py#test_layout_lists_fresh"
        status: pass
      - kind: unit
        ref: "tests/test_naming_suggest.py#test_layout_missing_custom_and_read_only"
        status: pass
    human_judgment: false
  - id: D2
    description: "Manufacturer token chain: alias, host table, aggregator deny-list with INFO, guesses, placeholder"
    requirement: LIB-01
    verification:
      - kind: unit
        ref: "tests/test_naming_suggest.py#test_manufacturer_token_aliases"
        status: pass
      - kind: unit
        ref: "tests/test_naming_suggest.py#test_manufacturer_hosts"
        status: pass
      - kind: unit
        ref: "tests/test_naming_suggest.py#test_manufacturer_aggregator_ignored"
        status: pass
    human_judgment: false
  - id: D3
    description: "SubCategory from existing vocabulary, ranked alternatives, UL sample gives IC_SubCategory_TI at low confidence with IC_Battery_Charger_TI first"
    requirement: LIB-01
    verification:
      - kind: unit
        ref: "tests/test_naming_suggest.py#test_suggest_ul_sample_with_layout"
        status: pass
      - kind: unit
        ref: "tests/test_naming_suggest.py#test_suggest_vocab_full_match"
        status: pass
      - kind: unit
        ref: "tests/test_naming_suggest.py#test_suggest_ranking_cap_and_determinism"
        status: pass
    human_judgment: false
  - id: D4
    description: "D-04 placeholder contract works on a user-edited plain string"
    requirement: LIB-01
    verification:
      - kind: unit
        ref: "tests/test_naming_suggest.py#test_placeholder_contract_on_edited_name"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live Custom/ smoke test (UL sample against the real submodule)"
    requirement: LIB-01
    verification:
      - kind: unit
        ref: "tests/test_naming_suggest.py#test_suggest_live_custom"
        status: unknown
    human_judgment: false

duration: 25min
completed: 2026-10-19
status: complete
---

# Phase 3 Plan 06: Library-name suggestion Summary

**Complete `<Type>_<SubCategory>_<Manufacturer>` suggestion: fresh read-only `Custom/` listing, alias/host/aggregator manufacturer chain, whole-token SubCategory vocabulary with verbatim library spelling, ranked alternatives and the D-04 placeholder contract.**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-10-19T14:24:53Z
- **Tasks:** 2 (both TDD, 4 commits)
- **Files modified:** 3 (1 new module, 1 new test file, 1 extended module)

## Accomplishments

- `layout.py`: frozen `RepoLayout.for_repo`, `list_symbol_libs`, `list_footprint_libs`, `list_model_files`, `list_existing_libraries`; sorted by `(casefold, name)`, no caching, no writes, `[]` for a missing `Custom/` (T-03-25/26).
- `suggest.py` manufacturer chain: `MANUFACTURER_ALIASES`, `_CORPORATE_WORDS`, `AGGREGATOR_DOMAINS`, `manufacturer_token`, `is_aggregator_host`, completed `manufacturer_choice`; distributor hosts never become a manufacturer and add INFO `naming.aggregator_host` (T-03-23); malformed URLs never raise (T-03-24).
- SubCategory vocabulary (`_part_tokens`, `_parse_library`, `_subcategory`) with the spelling rule in its docstring; `USB4056-03-A` never matches `USB`; unknown Reference prefix takes Type from the vocabulary (source `vocab`, not confident).
- Ranked alternatives (`_rank`, `MAX_ALTERNATIVES = 5`); the UL sample gives `IC_SubCategory_TI`, low confidence, `("SubCategory",)`, alternatives `IC_Battery_Charger_TI` (5, shared `("IC","TI")`), then four at score 2. Also confirmed by hand against the real read-only `Custom/` (listing and result identical).
- `suggest_library` now passes the name through `sanitize_name` and `case_clash`; issue order is aggregator INFO, sanitize issues, case-clash warnings, `naming.low_confidence`, `naming.placeholder`.

## Task Commits

1. **Task 1 RED:** `a09fd55` (test) - layout and manufacturer tests (fails at collection: `importer.layout` missing)
2. **Task 1 GREEN:** `d5b1eb1` (feat) - layout.py and manufacturer chain
3. **Task 2 RED:** `855183b` (test) - vocabulary, ranking, sanitise and contract tests (12 assertion failures)
4. **Task 2 GREEN:** `1a7d28f` (feat) - vocabulary, ranking, sanitise pass, D-04 docs

**Plan metadata:** committed separately (docs: complete plan).

## TDD Notes

- Task 1 RED fails with `ModuleNotFoundError` at collection because `layout.py` is a brand-new module; the target tests (new-API behaviour) could not be collected until it existed. Semantic assessment: failure is exactly the planned missing API, not a fixture or syntax fault. Task 2 RED is a clean assertion failure (12 failed, 32 passed, 1 skipped).
- No REFACTOR commit was needed.

## Files Created/Modified

- `kicad_lib_manager/importer/layout.py` - `RepoLayout` and fresh Custom/ listings (imports only `.candidate`).
- `kicad_lib_manager/importer/suggest.py` - manufacturer chain, vocabulary, ranking, sanitise pass, D-04 docstrings.
- `tests/test_naming_suggest.py` - 45 tests (44 pass, 1 live skip) covering layout, manufacturer, vocabulary, ranking, sanitise and the contract.

## Decisions Made

See `key-decisions`. In short: mapped tokens beat unmapped guesses regardless of source; the vocabulary spelling rule; host-guess labels are reduced to alphanumerics so a guess stays one token.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Host guess could inject an extra name token**
- **Found during:** Task 2 (design of the sanitise pass)
- **Issue:** The plan's host guess only removed hyphens; a host label containing `_` would add a spurious token to the library name that `sanitize_name` leaves alone.
- **Fix:** The label is reduced with `re.sub(r"[^a-z0-9]", "", ...)` before capitalising.
- **Files modified:** `kicad_lib_manager/importer/suggest.py`
- **Committed in:** `1a7d28f`

**2. [Rule 1 - Interface] Issue text field is `text`, not `message`**
- **Found during:** Task 2 test writing; tests use `Issue.text`. No code impact.

---

**Total deviations:** 1 auto-fix (Rule 2), 1 test-only note
**Impact on plan:** None on scope.

## Issues Encountered

- Plan Task 2 acceptance said "at least 18 passed" for the new test file; 44 pass (live test skipped because `Custom/` is not checked out in the worktree).
- Test counts: new file 44 passed / 1 skipped; full suite in the worktree 714 passed, 11 skipped (baseline before this plan 670 passed, 10 skipped). Submodule-dependent tests skip by design; the orchestrator should re-run in the main checkout, where `test_suggest_live_custom` runs.

## Follow-ups (outside this plan's files)

- ROADMAP.md already carries the D-04 contract under Phases 4 and 5 (lines 126 and 143); nothing to add.
- `tests/test_importer_layering.py` needed no change: `importer.layout` and `importer.suggest` were already registered in ALLOWED and still pass.

## Known Stubs

None. (Placeholder tokens in suggested names are the designed D-04 behaviour, not stubs.)

## Threat Flags

None. No new network, auth or file-write surface; listings are read-only.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 4/5 can call `list_existing_libraries(RepoLayout.for_repo(repo_root))`, `suggest_library(meta, existing)`, and `placeholder_tokens`, `sanitize_name`, `case_clash` on any user-edited library name.

## Self-Check: PASSED

- `kicad_lib_manager/importer/layout.py`, `tests/test_naming_suggest.py`, `kicad_lib_manager/importer/suggest.py` exist.
- Commits `a09fd55`, `d5b1eb1`, `855183b`, `1a7d28f` are ancestors of HEAD.
- `pytest -q` in the worktree: 714 passed, 11 skipped; `git status --porcelain -- Custom` empty.

---
*Phase: 03-package-intake-and-naming*
*Completed: 2026-10-19*
