---
phase: 10-importer-on-the-atomic-scheme
plan: 04
subsystem: importer
tags: [category-map, keywords, manufacturers, kicad-atomic, tdd]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "importer.stems.allowed_stems() (plan 10-01), the one name rule and KiCad 10 stem snapshot"
provides:
  - "importer.categories: classify(meta, allowed) places a part with no sibling by vendor category, words or an unambiguous reference letter"
  - "importer.keywords: generate_keywords, merge_words, manufacturer_words, split_words and the curated word tables"
  - "manufacturers.Manufacturer.hosts and by_host(domain): datasheet domain to canonical manufacturer"
affects: [10-15 suggest rewrite, 10-17 planner (is_aggregator_host guard), 10-18 token removal, 10-23 keyword writing]

actuals:
  tokens: 16500
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Ordered first-match rule table with a runner-up list (CategoryRule, RULES)"
    - "Whole-phrase matching on blank-padded folded text (' dc dc ')"
    - "Table-owned domain index built at import that raises ValueError on a clash (_index_hosts)"

key-files:
  created:
    - kicad_lib_manager/importer/categories.py
    - kicad_lib_manager/importer/keywords.py
    - tests/test_categories.py
    - tests/test_keywords.py
  modified:
    - kicad_lib_manager/manufacturers.py
    - tests/test_manufacturers.py

key-decisions:
  - "Only the reference letters K, SW, TR, M, JP and J place a part; U, Q, D, X, Y, P never do (RESEARCH A3, A4)"
  - "No rule or vendor key maps to Crystal; a bare crystal description is left unplaced (RESEARCH Pitfall 4)"
  - "by_host matches an exact registered domain only; subdomains, paths and aggregator sites give None (T-10-07)"
  - "Acquired brands keep their own name; the owner appears only as extra keyword words (Maxim -> ADI, Analog)"
  - "runner_up lists the stems of every other RULES entry that also matched, in rule order"

patterns-established:
  - "Pure vocabulary modules import only candidate/stems or manufacturers, matching the ALLOWED layering entries already registered"

requirements-completed: [LIB-04, FLD-01]

coverage:
  - id: D1
    description: "A part with no sibling is placed by vendor category, description words or an unambiguous reference letter; RS3-1212S/H3 goes to Converter_DCDC_Isolated, ATXK-H14 is not placed"
    requirement: LIB-04
    verification:
      - kind: unit
        ref: "tests/test_categories.py#test_isolated_dcdc_module_is_placed_by_vendor_category_and_description"
        status: pass
      - kind: integration
        ref: "tests/test_categories.py#test_real_samacsys_download_is_placed_in_converter_dcdc_isolated"
        status: pass
      - kind: unit
        ref: "tests/test_categories.py#test_classify_cases"
        status: pass
      - kind: unit
        ref: "tests/test_categories.py#test_every_rule_target_is_an_allowed_stem"
        status: pass
    human_judgment: false
  - id: D2
    description: "Datasheet domains of the canonical manufacturer table with by_host; Maxim stays Maxim Integrated, unknown or empty gives None"
    requirement: LIB-04
    verification:
      - kind: unit
        ref: "tests/test_manufacturers.py#test_by_host_names_the_company_that_owns_the_domain"
        status: pass
      - kind: unit
        ref: "tests/test_manufacturers.py#test_host_index_rejects_two_entries_that_share_a_domain"
        status: pass
    human_judgment: false
  - id: D3
    description: "Keywords are generated as single words from stem, function, interface, package, manufacturer and parent brand, MPN and runner-up words, and merged after the vendor's words"
    requirement: FLD-01
    verification:
      - kind: unit
        ref: "tests/test_keywords.py#test_csd_case_gives_stem_package_manufacturer_and_related_words"
        status: pass
      - kind: unit
        ref: "tests/test_keywords.py#test_rs3_case_gives_stem_function_package_manufacturer_mpn_and_category_words"
        status: pass
      - kind: unit
        ref: "tests/test_keywords.py#test_no_item_holds_whitespace_or_an_equals_sign"
        status: pass
      - kind: unit
        ref: "tests/test_keywords.py#test_merge_words_keeps_vendor_words_first_and_adds_new_generated_words"
        status: pass
    human_judgment: false
  - id: D4
    description: "Curated function and interface vocabulary gives useful chooser search words (quality, never blocking)"
    verification: []
    human_judgment: true
    rationale: "Keyword usefulness in the KiCad 10 chooser is a judgment call; the tables are short and curated (RESEARCH A12)"

plan_head_before: b4f956441ef5cab68b1bc6efe104c5a92c09da70
plan_head_after: a1ef8ff33c94ea1722e5f2fca3e844a7e5ea4d74

duration: 25min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 04: Vocabulary Summary

**Category map that files RS3-1212S/H3 into Converter_DCDC_Isolated from its SamacSys category and description, a single-word keyword generator and vendor merge, and datasheet domains with `by_host` on the canonical manufacturer table**

## Performance

- **Duration:** about 25 min
- **Completed:** 2026-10-27T10:03:11Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 6 (4 created, 2 modified)

## Accomplishments

- `classify` reads, in order, a vendor category together with description words, the vendor category alone, description words alone, then a reference letter from K, SW, TR, M, JP, J. A real SamacSys download (RS3-1212S/H3) and a synthetic part both give Converter_DCDC_Isolated with source "vendor". ATXK-H14 (bare X) and U, Q, D, Y references are never placed.
- Every rule target is checked against `allowed_stems()`; a missing stem is skipped, and no rule names Crystal.
- `generate_keywords` reproduces the CSD85301Q2 and RS3 cases from the plan exactly, filters whitespace, `=` and junk words, and de-duplicates ignoring case; `merge_words` keeps vendor words first.
- `Manufacturer.hosts` and `by_host` map exact registered domains to the canonical entry (maximintegrated.com is Maxim Integrated, never Analog Devices); a shared domain raises ValueError at import.

## Task Commits

1. **Task 1: RS3-1212S/H3 to Converter_DCDC_Isolated (tracer)** - `b8c2873` (feat)
2. **Task 2: category cases, allowed-stem self-check, manufacturer domains** - RED `b91eb62` (test), GREEN `f0d7cd2` (feat)
3. **Task 3: keyword generation and vendor merge** - RED `c2c0752` (test), GREEN `a1ef8ff` (feat)

**Plan metadata:** the docs commit that adds this SUMMARY.

## Tracer Gate

Task 1 `<verify>` is automated-only; re-run after the commit and passed (16 passed including the real SamacSys sample, copied locally from the orchestrator checkout and kept gitignored). Logged "Tracer verified end-to-end, expanding" and continued.

## TDD Gate Compliance

- **Task 2 RED:** `tests/test_manufacturers.py` host tests failed with `TypeError: Manufacturer.__init__() got an unexpected keyword argument 'hosts'` and `AttributeError ... no attribute 'hosts'` (23 failed): the planned feature was absent, so the failure is on the intended behavior. Semantic assessment: valid. The category rows added in the same RED commit passed on arrival because `classify` already existed from the tracer commit; they pin the Task 2 behavior list against regressions rather than drive new code.
- **Task 2 GREEN:** `f0d7cd2`, 96 passed in test_categories + test_manufacturers.
- **Task 3 RED:** with a stub `keywords.py` kept out of the commit, 26 tests failed on assertions of the planned behavior (empty lists and strings instead of the expected words), 13 trivially-empty cases passed. The stub was not committed; the RED commit holds the test file only. Semantic assessment: valid.
- **Task 3 GREEN:** `a1ef8ff`, all of test_keywords plus layering pass (53 passed).
- No REFACTOR commit was needed. The `gsd_run check tdd-red-evidence` classifier was not run: pytest's report is not one of its supported formats and `workflow.tdd_mode` was not set for this run, so RED was assessed by inspection as the reference allows.

## Files Created/Modified

- `kicad_lib_manager/importer/categories.py` - `CategoryRule`, `RULES`, `VENDOR_STEMS`, `REFERENCE_STEMS`, `CategoryMatch`, `part_text`, `classify`
- `kicad_lib_manager/importer/keywords.py` - `JUNK_WORDS`, `FUNCTION_WORDS`, `INTERFACE_WORDS`, `split_words`, `manufacturer_words`, `generate_keywords`, `merge_words`
- `kicad_lib_manager/manufacturers.py` - `Manufacturer.hosts`, `_index_hosts`, `by_host` (token and `token_map` unchanged)
- `tests/test_categories.py`, `tests/test_keywords.py` - new; `tests/test_manufacturers.py` - host tests added

## Decisions Made

- `by_host("www.ti.com")` and `by_host("ti.com/x")` give None: callers pass a registered domain, and exact matching keeps T-10-07 simple.
- `part_text` covers description, keywords and category (not the symbol value), as the plan states, so a model number in the value never decides a library.
- `runner_up` is built from the RULES table only, so a vendor-map or reference winner still lists the word rules that also matched.

## Deviations from Plan

None - plan executed exactly as written. (`tests/test_importer_layering.py` and `tests/test_layering.py` already registered `importer.categories` and `importer.keywords`, so neither file was touched.)

**Total deviations:** 0.

## Issues Encountered

- Parametrized tests with a 100k-character or NUL-containing value produced unusable test ids and collection errors; fixed with explicit `pytest.param(..., id=...)`.
- The worktree has no `downloaded_examples/`; the SamacSys zip was copied from the orchestrator checkout (gitignored, not committed) so the real-download test ran instead of skipping.

## Known Stubs

None.

## Threat Flags

None. Mitigations for T-10-07 (exact registered domains only, None for unknown) and T-10-08 (single words without blanks or `=`) are implemented and tested.

## Verification

- `pytest tests/test_categories.py tests/test_keywords.py tests/test_manufacturers.py tests/test_importer_layering.py tests/test_layering.py -q`: 163 passed.
- Neighbouring suites that touch the changed table (`test_atomic_check`, `test_naming_suggest`, `test_import_form`, `test_atomic_scan`, `test_real_vendor_samples`): 223 passed, 6 skipped (SnapEDA samples absent).
- The full `-m "not wurth"` suite is left to the orchestrator's post-merge run, as instructed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The planner, suggest rewrite and field-writing plans can call `classify`, `generate_keywords`/`merge_words` and `by_host` directly. Plan 10-17 must keep the aggregator-host guard from `suggest.py` before calling `by_host`.

## Self-Check: PASSED

- Files exist: categories.py, keywords.py, test_categories.py, test_keywords.py, manufacturers.py (verified by test import).
- Commits `b8c2873`, `b91eb62`, `f0d7cd2`, `c2c0752`, `a1ef8ff` are ancestors of HEAD.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*
