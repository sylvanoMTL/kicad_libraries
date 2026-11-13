---
phase: 13-atomic-migration-and-kicad-setup
plan: 24
subsystem: scan-progress
tags: [pyside6, scan, skip, loading-libraries, gap-closure]
requires:
  - phase: 12-import-flow-fixes-and-case-sensitive-re-test
    provides: "Skip button and ScanWorker sticky per-source skip set (plan 12-17, G-12-21)"
provides:
  - "find_symbol_libs(root, progress=None, *, checking=None) reports each source as its first symbol file is reached"
  - "Loading Libraries window offers Skip <source> while the symbols are read; an early click skips that source's 3D model path check only"
  - "ScanProgressDialog remembers requested sources and shows Skipping <source>... instead of offering the skip twice"
affects: [13-28]
gap_ids: [G-13-1-b]
requirements-completed: [MIG-04, DOC-01]
actuals:
  tokens: 9000
  tasks: 2
  commits: 3
plan_head_before: 32f33940f3e6a0dc91cce3859cd7c9cb2295e2b3
plan_head_after: f52abdddf0573d335f3d9fc6add279be1f563422
tech-stack:
  added: []
  patterns:
    - "reporting-only callable passed to the symbol parse: it never consults skip, so a skip cannot drop a library or footprint link"
key-files:
  created: []
  modified:
    - kicad_lib_manager/library_scanner.py
    - kicad_lib_manager/widgets/scan_progress.py
    - kicad_lib_manager/widgets/help_dialog.py
    - CLAUDE.md
    - tests/test_scan_skip.py
    - tests/test_main_window.py
    - tests/test_help_dialog.py
    - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-UAT.md
key-decisions:
  - "Skip is offered from the symbol parse as an advance skip of the 3D model path check; the symbol parse is never skipped (amends the 2026-11-04 owner decision, recorded in 12-UAT.md)"
duration: 25min
completed: 2026-11-13
status: complete
coverage:
  - id: D1
    description: "Skip <source> is offered while the symbols are read, and an early click skips only that source's 3D model path check"
    requirement: MIG-04
    verification:
      - kind: unit
        ref: "tests/test_scan_skip.py#test_a_skip_requested_while_symbols_are_read_is_honoured"
        status: pass
      - kind: integration
        ref: "tests/test_main_window.py#test_skip_is_offered_while_symbols_are_read"
        status: pass
    human_judgment: false
  - id: D2
    description: "A skip never drops a library or footprint link; the skip is logged once from the scan result"
    requirement: MIG-04
    verification:
      - kind: unit
        ref: "tests/test_scan_skip.py#test_skip_keeps_every_library_and_link"
        status: pass
      - kind: integration
        ref: "tests/test_main_window.py#test_generate_after_a_skip_removes_no_entry"
        status: pass
    human_judgment: false
  - id: D3
    description: "User Guide, CLAUDE.md and the 12-UAT.md decision record describe the early Skip"
    requirement: DOC-01
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_repo_scan_explains_skip_and_the_saved_scan"
        status: pass
    human_judgment: false
  - id: D4
    description: "Skip is really enabled during 'Parsing symbol' on the owner's checkout"
    verification: []
    human_judgment: true
    rationale: "Live check on the owner's checkout; planned in plan 13-28 Task 2 human-check"
---

# Phase 13 Plan 24: Early Skip While Symbols Are Read Summary

**Loading Libraries now offers Skip <source> from the first symbol file of a source: `find_symbol_libs` reports sources through a reporting-only `checking` callable, and the dialog remembers a requested skip so the sticky skip set skips that source's 3D model path check the moment it starts, while every symbol library and footprint link is still read.**

## Performance

- **Duration:** about 25 min
- **Tasks:** 2 (Task 1 tracer, TDD: RED then GREEN; Task 2 docs)
- **Files modified:** 8

## Accomplishments

- `find_symbol_libs` gets a keyword-only `checking` callable, called when the source changes; it never consults `skip`, so no library or link is dropped (T-13-61). `scan_all` passes `checking` to it and its docstring states the new contract. `skip(` is still called only inside `_check_model_files`.
- `ScanProgressDialog._requested` remembers clicked sources: `set_skippable` shows `Skipping <source>...` (disabled) for a requested source and `Skip <source>` for another. New idle and per-source tooltips.
- New regression tests at scanner level (`test_a_skip_requested_while_symbols_are_read_is_honoured`) and window level (`test_skip_is_offered_while_symbols_are_read`); `test_scan_without_skip_is_unchanged` and the dialog test updated to the new report sequence and texts.
- User Guide Repository Scan page, the CLAUDE.md Loading Libraries bullet, and the G-12-21 owner-decision line in 12-UAT.md (amended 2026-11-12 by plan 13-24) describe the early Skip.

## Task Commits

1. Task 1 RED: `aa78f42` test(13-24) - new and updated tests, 4 failing on the old code
2. Task 1 GREEN: `cf3dfb3` feat(13-24) - scanner reporting, dialog memory, new tooltips
3. Task 2: docs(13-24) commit `f52abdd` - guide, CLAUDE.md, 12-UAT.md

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan expectation] Report sequence includes the `Other` source**
- **Found during:** Task 1 RED
- **Issue:** The plan expected `["Custom", "WurthElektronik", "Custom", "WurthElektronik", None]`, but the `two_sources` fixture (via `write_atomic_custom`) also contains an `Other` source (the duplicate-footprint-nickname case) with both symbol and footprint files. The plan itself said to confirm the sequence against the fixture.
- **Fix:** Asserted `["Custom", "Other", WURTH, "Custom", "Other", WURTH, None]`, measured on the fixture.
- **Files modified:** tests/test_scan_skip.py
- **Commit:** aa78f42

**Total deviations:** 1 (test expectation corrected to the fixture). **Impact:** none on behaviour.

## Known Stubs

None.

## Threat Flags

None. The change adds no new boundary; T-13-61 to T-13-64 mitigations hold (tests use tmp_path fixtures only, the real Custom/ and WurthElektronik are untouched).

## Verification

`pytest tests/test_scan_skip.py tests/test_main_window.py tests/test_scan_cache.py tests/test_scanner_skip_dirs.py tests/test_help_dialog.py tests/test_docs_atomic.py -q`: 225 passed. The whole suite was not run (plan 13-28 runs it once). The live check on the owner's checkout is in plan 13-28 Task 2.

## Self-Check: PASSED

All modified files exist; commits `aa78f42`, `cf3dfb3` and `f52abdd` are in HEAD history.
