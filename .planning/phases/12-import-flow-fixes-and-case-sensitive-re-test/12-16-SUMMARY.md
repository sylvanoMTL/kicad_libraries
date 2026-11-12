---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 16
subsystem: scanner
tags: [scan, skip, saved-scan, code-signature, progress, G-12-21]
requires: []
provides:
  - "scan_all(skip=, checking=) with a per-source skip of the 3D model path check"
  - "ScanResult.skipped_sources and ScanResult.models_unchecked"
  - "models_skipped_issue(sources, rechecked) and models_rechecked(result)"
  - "saved scan FORMAT 2 with the skipped sources and an honest reuse note"
  - "narrowed code signature (_scan_code_files, _code_signature_of)"
  - "one 0-100 progress scale for scan_all"
affects: [12-17]
tech-stack:
  added: []
  patterns: ["plain-callable hooks keep the scanner Qt-free", "import closure found with ast instead of a typed file list"]
key-files:
  created: [tests/test_scan_skip.py]
  modified:
    - kicad_lib_manager/library_scanner.py
    - kicad_lib_manager/models.py
    - kicad_lib_manager/scan_cache.py
    - tests/test_scan_cache.py
key-decisions:
  - "The skip unit is the source; a skip removes only that source's 3D model path lines (including ones found before the click) and never a library or link"
  - "models_unchecked records per library what is still unchecked, so a one-library rescan keeps the skip line true"
  - "Saved scan FORMAT 2; a format 1 file runs one full scan"
requirements-completed: [UI-01]
status: complete
duration: 55 min
completed: 2026-11-04
commits: 6
plan_head_before: 808df98ae5bfb9f44588de1e60e234987d1543ac
plan_head_after: bfe59cfc26d129b270ed5b5d0cd4b4bc74b1052b
actuals:
  tokens: 26000
  tasks: 3
  commits: 6
coverage:
  - deliverable: "Skip one source's 3D model path check in scan_all, keeping every library and link"
    verification:
      - {kind: test, ref: "tests/test_scan_skip.py#test_skipped_source_has_no_3d_path_lines", status: pass}
      - {kind: test, ref: "tests/test_scan_skip.py#test_skip_keeps_every_library_and_link", status: pass}
      - {kind: test, ref: "tests/test_scan_skip.py#test_scan_without_skip_is_unchanged", status: pass}
    human_judgment: false
  - deliverable: "One-library rescan keeps the skip line true"
    verification:
      - {kind: test, ref: "tests/test_scan_skip.py#test_library_rescan_keeps_the_skip_line", status: pass}
    human_judgment: false
  - deliverable: "Saved scan keeps the skipped sources and says so when reused"
    verification:
      - {kind: test, ref: "tests/test_scan_cache.py#test_skipped_scan_round_trips", status: pass}
      - {kind: test, ref: "tests/test_scan_cache.py#test_reuse_note_names_the_skipped_sources", status: pass}
      - {kind: test, ref: "tests/test_scan_cache.py#test_format_1_saved_scan_is_a_different_version", status: pass}
    human_judgment: false
  - deliverable: "Narrowed code signature"
    verification:
      - {kind: test, ref: "tests/test_scan_cache.py#test_code_signature_covers_the_scan_modules_only", status: pass}
      - {kind: test, ref: "tests/test_scan_cache.py#test_code_signature_follows_scan_code_edits", status: pass}
    human_judgment: false
  - deliverable: "One progress scale from 0 to 100"
    verification:
      - {kind: test, ref: "tests/test_scan_skip.py#test_progress_rises_from_0_to_100", status: pass}
    human_judgment: false
---

# Phase 12 Plan 16: Skip one source's 3D model path check Summary

scan_all gains plain-callable `skip` and `checking` hooks that stop one source's 3D model path check (WurthElektronik's, the 63 s part of a 70 s scan) without dropping any library or link, record the skip in the result and the format 2 saved scan with an honest reuse note, narrow the saved-scan code signature to the 15 files the scan reads, and report one 0-100 progress scale.

## Accomplishments

- **Skip hook.** `_check_model_files` takes keyword-only `skip`, `checking` and `skipped`. A skipped source's files are never read after the answer, and its 3D path lines (even those found before the answer) are left out. `scan_all` appends one INFO line, exactly "3D model paths of WurthElektronik were not checked: skipped while the libraries loaded. Rescan checks them.", right after the 3D path lines.
- **Per-library record.** `ScanResult.skipped_sources` and `models_unchecked` (footprint libraries, plus loose footprint files, of skipped sources). `rescan_library` removes a rescanned library from the record, rewrites the line with "except WE_Test (rescanned since)" and drops it once nothing is unchecked; a Custom rescan keeps the line as it was.
- **Saved scan.** `FORMAT = 2`; both fields are encoded and strictly decoded. Reusing a skipped scan logs "... The 3D model paths of WurthElektronik were skipped in that scan; use Rescan for a full scan." (with the "except ... (rescanned since)" variant). A format 1 file runs one full scan.
- **Narrowed signature.** `_scan_code_files(package)` follows relative imports (ast, function-level included) from `library_scanner.py` and `scan_cache.py`: exactly the 15 files of the plan's 2026-11-04 probe. Widget, main window and settings edits no longer make the saved scan stale; edits to atomic_check, importer/fieldrules, models, or a newly imported module still do; an unparsable module gives "".
- **Progress.** Bands: footprint libraries 0-1, symbol libraries 1-10, 3D check 10-92, atomic 92, changes 96, done 100; total is always 100.

## Task Commits

| Task | Phase | Commit |
| ---- | ----- | ------ |
| 1 | RED | b586b78 test(12-16): failing tests for skipping one source's 3D check |
| 1 | GREEN | d78dd15 feat(12-16): skip one source's 3D model path check in scan_all |
| 2 | RED | b257737 test(12-16): failing tests for skipped sources in the saved scan |
| 2 | GREEN | d87c7d5 feat(12-16): save skipped sources and say so when reused |
| 3 | RED | 65f0d95 test(12-16): failing tests for code signature and progress |
| 3 | GREEN | bfe59cf feat(12-16): narrow code signature, one progress scale |

## TDD Gate Compliance

RED then GREEN commits exist for all three tasks; no REFACTOR commit was needed.

RED evidence (semantic assessment; I did not run `gsd_run check tdd-red-evidence`, since pytest's plain output is not one of its supported report formats): Task 1's tests failed on `TypeError: scan_all() got an unexpected keyword argument 'skip'` and `AttributeError: no attribute 'models_skipped_issue'`, the planned missing behavior. To keep collection working (no ImportError), the tests reach the new helpers as `library_scanner.<name>`. Task 2's 10 new tests failed on assertions (missing fields, old note, format 1 still accepted). Task 3's 4 tests failed on `_scan_code_files` missing and on progress totals of 4, 10 and 11 instead of 100.

## Verification

Task 3 plan-level command: `pytest tests/test_scan_cache.py tests/test_scan_skip.py tests/test_scanner_issues.py tests/test_rescan_library.py tests/test_atomic_scan.py tests/test_scan_changes.py tests/test_layering.py -q -m "not wurth"` gave 175 passed, 1 skipped (Custom submodule not checked out in the worktree), 1 deselected in 194 s. The full suite was not run (orchestrator's post-merge gate).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixture overlap in the synthetic repo**
- **Found during:** Task 1 (RED)
- **Issue:** `write_atomic_custom` already creates `WurthElektronik/KiCad-Library/symbols/` (the WE-Connectors atomic fixture) and an `Other/` source with a footprint, so `symbols.mkdir()` failed and the source order seen by `checking` is Custom, Other, WurthElektronik.
- **Fix:** `mkdir(exist_ok=True)`; the unchanged-scan test asserts Custom before WurthElektronik, no repeats and a final None, rather than the plan's literal three-item list; the link test looks the `WE_Test` symbol library up by nickname.
- **Files modified:** tests/test_scan_skip.py
- **Commit:** b586b78

**Total deviations:** 1 auto-fixed (blocking, test-only). **Impact:** none on production code.

## Known Stubs

None.

## Threat Flags

None. T-12-39 to T-12-42 are mitigated by the tests named in the plan; the new `ast` use reads only the package's own source.

## Notes for plan 12-17

- Hooks: `scan_all(..., skip=callable(str) -> bool, checking=callable(str | None) -> None)`; `checking(None)` signals the end of the 3D check.
- `models_skipped_issue` and `models_rechecked` are public in `library_scanner`; `ScanResult.skipped_sources` empty means no skip line.
- Hand-built results with `skipped_sources` and an empty `models_unchecked` read as wholly unchecked.

## Self-Check: PASSED

Files tests/test_scan_skip.py, kicad_lib_manager/library_scanner.py, models.py, scan_cache.py exist; commits b586b78, d78dd15, b257737, d87c7d5, 65f0d95, bfe59cf are on the branch.
