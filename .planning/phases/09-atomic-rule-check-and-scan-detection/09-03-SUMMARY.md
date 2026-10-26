---
phase: 09-atomic-rule-check-and-scan-detection
plan: 03
subsystem: atomic-check
tags: [python, atomic-rules, kicad-sym, fix-specs, derived-symbols, scan]

requires:
  - phase: 09-atomic-rule-check-and-scan-detection
    provides: "09-01 manufacturers.lookup/fold; 09-02 FixSpec, Violation, Finding, SymbolEntry, SymbolLibrary.atomic/symbols/check_problem"
provides:
  - "kicad_lib_manager/atomic_check.py: ATOMIC_PREFIX, ATOMIC_RULES, SAFE_FIX_KINDS, FILL_KINDS, is_atomic, datasheet_problem, effective_mpn, check_symbol, check_libraries"
  - "scan_all runs the check on every scan and attaches one SymbolEntry per top-level symbol of every Atomic_ library"
  - "Issue codes atomic.mpn, atomic.manufacturer, atomic.value, atomic.datasheet, atomic.description, atomic.leftover, atomic.unknown_manufacturer, atomic.unreadable, atomic.summary"
  - "tests/customfixtures.py atomic inventory: AtomicSymbol, AtomicLibrary, atomic_part, atomic_lib, ATOMIC_LIBRARIES, ATOMIC_EXPECTED, write_atomic_files, write_atomic_custom"
affects: [09-04 footprint and 3D rules, 09-06 fix engine, phase-10 install gating, phase-11 commit gate, phase-13 migration]

actuals:
  tokens: 16000
  tasks: 3
  commits: 5
plan_head_before: 4a2d4c464d204e9397723de2ecd1bb0868cefb64
plan_head_after: 8033af0e6ba1ac59120f7e6944499b27e0b753f6

tech-stack:
  added: []
  patterns:
    - "One Qt-free rule check read by scan, install, commit gate and migration; reads text only, writes nothing"
    - "Property-group ownership: MPN and Value on the symbol itself, Manufacturer/Datasheet/Description from the nearest declaring ancestor"
    - "Fix specs are semantic (kind + params) and attached only for source Custom; resolved to edits later"

key-files:
  created:
    - kicad_lib_manager/atomic_check.py
    - tests/test_atomic_check.py
    - tests/test_atomic_scan.py
  modified:
    - kicad_lib_manager/library_scanner.py
    - tests/customfixtures.py
    - tests/test_layering.py

key-decisions:
  - "merge_alias params stay exactly {group, keep, value} as planned; the fix engine (09-06) must rename the kept property to the canonical group name (MPN or Manufacturer), otherwise a kept alias such as MF would fail the rule again after the merge"
  - "Choices are only attached for fixable (Custom) libraries; outside Custom a violation carries no fixes, no fill and no choices"
  - "Merge and choice values are whitespace-stripped; effective_mpn returns the stored value unstripped so the Value rule compares identical strings"
  - "A lone alias field next to a blank canonical field is fixed by merge_alias instead of rename_alias, because a rename would create two fields with the canonical name"
  - "The note for an unknown manufacturer is attached only to the symbol that holds the Manufacturer field, not to children that inherit it"

patterns-established:
  - "check_libraries(repo_root, sym_libs, fp_libs, kicad_fp_dir) is the stable entry point; fp_libs and kicad_fp_dir are accepted now so 09-04 adds Footprint and 3D rules without a signature change"

requirements-completed: [ATOM-01, ATOM-02, ATOM-03, FLD-02, SCAN-01]

coverage:
  - id: D1
    description: "Every scan checks every symbol of every library whose nickname starts with Atomic_ (exact, case-sensitive) and attaches entries in file order; other libraries (Wurth, legacy, prefix variants) are never judged"
    requirement: "SCAN-01"
    verification:
      - kind: integration
        ref: "tests/test_atomic_scan.py#test_every_atomic_library_has_its_symbols_in_file_order_with_the_expected_rules"
        status: pass
      - kind: integration
        ref: "tests/test_atomic_scan.py#test_a_library_without_the_exact_prefix_is_never_judged"
        status: pass
    human_judgment: false
  - id: D2
    description: "Each broken rule is one WARNING line '<library> / <symbol>: <reason>' in the fixed rule order, followed by one atomic.summary line with failing symbols and problem count"
    requirement: "ATOM-01"
    verification:
      - kind: integration
        ref: "tests/test_atomic_scan.py#test_each_broken_rule_is_one_warning_with_library_symbol_and_reason"
        status: pass
      - kind: integration
        ref: "tests/test_atomic_scan.py#test_the_summary_line_is_last_and_counts_symbols_and_problems"
        status: pass
    human_judgment: false
  - id: D3
    description: "MPN, Manufacturer, Value, Datasheet and Description rules report plain reasons; aliases carry their canonical name from the manufacturer table; safe fixes and fill templates exist only for Custom"
    requirement: "FLD-02"
    verification:
      - kind: unit
        ref: "tests/test_atomic_check.py (46 tests selected by -k 'datasheet or mpn or manufacturer or value or leftover')"
        status: pass
      - kind: integration
        ref: "tests/test_atomic_scan.py#test_a_library_outside_custom_is_judged_but_gets_no_fix_and_no_fill"
        status: pass
    human_judgment: false
  - id: D4
    description: "Derived symbols are judged on their own fields (own MPN required, absent Manufacturer/Datasheet/Description taken from the nearest ancestor, inherited fixes target the parent, missing parent stated)"
    requirement: "ATOM-02"
    verification:
      - kind: unit
        ref: "tests/test_atomic_check.py (10 tests selected by -k derived)"
        status: pass
      - kind: integration
        ref: "tests/test_atomic_scan.py#test_a_derived_symbol_is_judged_in_the_scan_on_its_own_fields"
        status: pass
    human_judgment: false
  - id: D5
    description: "Price and stock leftovers and unknown manufacturers are INFO findings that never fail a symbol"
    requirement: "ATOM-01"
    verification:
      - kind: unit
        ref: "tests/test_atomic_check.py#test_price_and_stock_leftovers_are_findings_with_a_remove_fix_and_never_fail_the_symbol"
        status: pass
      - kind: unit
        ref: "tests/test_atomic_check.py#test_manufacturer_not_in_the_table_passes_with_a_finding_and_no_fix"
        status: pass
    human_judgment: false
  - id: D6
    description: "The scan only reads: a digest of the test tree is identical before and after; an unreadable library becomes check_problem and one atomic.unreadable warning while the rest is still checked"
    requirement: "ATOM-01"
    verification:
      - kind: integration
        ref: "tests/test_atomic_scan.py#test_the_scan_changes_nothing_on_disk"
        status: pass
      - kind: integration
        ref: "tests/test_atomic_scan.py#test_an_unreadable_library_is_reported_and_the_others_are_still_checked"
        status: pass
    human_judgment: false
  - id: D7
    description: "Fixture libraries are libraries KiCad 10 loads (real kicad-cli 10 upgrade of every library except the deliberately orphaned one)"
    verification:
      - kind: integration
        ref: "tests/test_atomic_scan.py#test_kicad_cli_loads_every_fixture_library"
        status: pass
    human_judgment: false
  - id: D8
    description: "Wording of the reasons ('no MPN of its own (the parent's MPN does not count)', 'MPN is stored as \"MP\", not as \"MPN\"') reads well to the owner"
    verification: []
    human_judgment: true
    rationale: "Plain-language quality is a judgement about the owner's own vocabulary; tests pin the text, not whether it is clear"

duration: 10min
completed: 2026-10-26
status: complete
---

# Phase 9 Plan 03: Atomic rule check on every scan Summary

**Qt-free atomic_check.py that checks every symbol of every Atomic_ library on each scan (MPN, Manufacturer with the manufacturer table, Value, Datasheet, Description, derived-symbol inheritance), attaches SymbolEntry results with safe-fix and fill specs for Custom only, and logs one WARNING per broken rule plus a summary line**

## Performance

- **Duration:** about 10 min
- **Started:** 2026-10-26T12:34:55Z
- **Completed:** 2026-10-26T12:44:13Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 6 (3 created: atomic_check.py, two test modules)

## Accomplishments

- `check_libraries` runs inside `scan_all` (progress "Checking atomic parts..." at 96, signature unchanged), sets `SymbolLibrary.atomic`, `symbols` and `check_problem`, and returns the log issues; no Atomic_ library means no `atomic.*` issue at all.
- Rules in the fixed order mpn, manufacturer, (footprint), value, datasheet, description, (model_3d): every reason is plain language, aliases are shown with the canonical name from `manufacturers.lookup`, and safe fixes (`value_to_mpn`, `rename_alias`, `canonical_manufacturer`, `merge_alias`, `remove_leftover`) plus fill templates (`fill_datasheet`, `fill_description`) are attached only for libraries under Custom/.
- Derived symbols: own MPN and Value required; absent Manufacturer, Datasheet and Description come from the nearest declaring ancestor, with ` (inherited from "<parent>")` and fixes aimed at the parent; a missing parent is stated and the child is still checked; child-before-parent order and extends loops give the same results.
- Synthetic fixture inventory (22 symbols over 9 Atomic_ and prefix-variant libraries) with `ATOMIC_EXPECTED`, written by `write_atomic_custom`, validated against the real kicad-cli 10 (9 libraries load).

## Task Commits

1. **Task 1: One Atomic_ library checked on every scan (tracer)** - `60fce1f` (feat)
2. **Task 2 RED: failing tests for MPN, Manufacturer, Value, leftovers** - `ee8bb66` (test)
3. **Task 2 GREEN: MPN, Manufacturer and Value rules, leftovers, fix specs** - `a02e022` (feat)
4. **Task 3 RED: failing tests for derived symbols** - `0c11723` (test)
5. **Task 3 GREEN: derived symbols judged on their own fields** - `8033af0` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified

- `kicad_lib_manager/atomic_check.py` - the rule check (new)
- `kicad_lib_manager/library_scanner.py` - `scan_all` calls `check_libraries`
- `tests/customfixtures.py` - atomic inventory, builders and writers
- `tests/test_atomic_check.py` - 62 unit tests (rules, fixes, findings, derived symbols)
- `tests/test_atomic_scan.py` - 27 scan integration tests incl. plain-language guard, ast import guard, kicad-cli load
- `tests/test_layering.py` - `atomic_check` registered in ALLOWED and `_CODE`; `library_scanner` may import it

## Decisions Made

See `key-decisions` in the frontmatter. The one that matters downstream: the fix engine in 09-06 must treat `merge_alias` as "keep this property, give it the canonical group name, set its value, remove the other group fields".

## Deviations from Plan

None - plan executed exactly as written. Two small implementation choices inside the plan's latitude: `check_symbol` walks the extends chain itself instead of calling `kicad_files.symbol_unit` (that function returns None as soon as any ancestor is missing, which would hide a present parent below a missing grandparent), and it shares one name index per library so a large library is not rescanned per symbol.

## TDD Gate Compliance

Task 1 is a tracer (single production commit with its tests). Tasks 2 and 3 have RED then GREEN commits; no REFACTOR commit was needed.

- **Task 2 RED (`ee8bb66`):** 37 of 66 tests failed on assertions for the planned behaviour (for example `[]` where one `mpn` violation was expected, summary counts 4 against 12 expected). The red commit also holds two constants and a one-line `effective_mpn` stub that returns None, added only so the test module could import; without them collection failed with an ImportError, which is INVALID_RED. Semantic assessment: the target tests executed and failed on the intended assertions, not on import or fixture faults. The `check tdd-red-evidence` classifier was not run (plain pytest output is not a format it supports).
- **Task 3 RED (`0c11723`):** 11 of 89 tests failed on assertions (inherited manufacturer text, "no MPN of its own", missing-parent suffix, scan summary counts). Four new derived tests (child-first order, vendor pair order, own blank fields, same MPN as parent) already passed because the Task 2 code judges own properties; they are guards. Semantic assessment: failures are the planned assertions.

## Issues Encountered

None. `Custom/` and `WurthElektronik/KiCad-Library` are not checked out in this worktree, so the two submodule-backed scanner tests skip; the orchestrator's post-merge run covers them. `git status --short Custom` shows no change.

## Known Stubs

None.

## Threat Flags

None. T-09-05 (size and node caps, broken library becomes check_problem), T-09-06 (Datasheet is string-matched only, ast test forbids urllib/http/socket/webbrowser/subprocess) and T-09-07 (no fixes outside Custom, tested on Atomic_Elsewhere) are implemented and tested.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 09-04 adds the Footprint and 3D model rules on the same entry points (`check_libraries(repo_root, sym_libs, fp_libs, kicad_fp_dir)` already accepts the unused arguments); `_check_ref`/`check_symbol` will take the extra inputs and `_scan` in `tests/test_atomic_scan.py` plus `_check` in `tests/test_atomic_check.py` are the single places to adapt.
- Plan 09-06 resolves FixSpec kinds into edits; note the `merge_alias` rename rule above and that `attach_model` is declared in FILL_KINDS but produced only by 09-04.
- Open for the owner: the Murata and TDK canonical spellings (carried from 09-01) and a look at the wording of the new reasons (coverage D8).

## Self-Check: PASSED

- FOUND: kicad_lib_manager/atomic_check.py, tests/test_atomic_check.py, tests/test_atomic_scan.py
- FOUND commits: 60fce1f, ee8bb66, a02e022, 0c11723, 8033af0
- `pytest tests/test_atomic_check.py tests/test_atomic_scan.py tests/test_layering.py tests/test_importer_layering.py tests/test_scanner_issues.py tests/test_scanner_skip_dirs.py tests/test_main_window.py tests/test_customfixtures.py tests/test_models.py` - 208 passed, 2 skipped (submodules absent)
- `pytest tests/test_atomic_scan.py -m kicad_cli` - 9 passed (real kicad-cli 10)

---
*Phase: 09-atomic-rule-check-and-scan-detection*
*Completed: 2026-10-26*
