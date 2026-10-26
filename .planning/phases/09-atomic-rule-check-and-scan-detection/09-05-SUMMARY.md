---
phase: 09-atomic-rule-check-and-scan-detection
plan: 05
subsystem: scan
tags: [python, git, change-detection, sexpr, kicad-sym, kicad-mod, scan]

requires:
  - phase: 09-atomic-rule-check-and-scan-detection
    provides: "09-02 SymbolEntry/ChangedFootprint/STATUS_NEW/STATUS_CHANGED and the tree marks; 09-03 check_libraries wiring in scan_all and the atomic fixture inventory"
provides:
  - "sexpr.token_stream(node): layout-independent token run of a parsed node"
  - "kicad_lib_manager/changes.py mark_changes(repo_root, sym_libs, fp_libs, *, which=None): marks Custom/ symbols and footprints new or changed since Custom's last commit, by content"
  - "scan_all calls mark_changes after the atomic check"
  - "Issue codes scan.symbol_new, scan.symbol_changed, scan.footprint_new, scan.footprint_changed, scan.changes_skipped (all INFO)"
affects: [09-04 sibling tests, 09-07 and later log or tree wiring, phase-11 commit gate, phase-13 migration]

actuals:
  tokens: 10500
  tasks: 2
  commits: 3
plan_head_before: 45f2d6b1ccba68096beb001d3c6ff771edff5010
plan_head_after: e9e50b63c5284dfd9837de4f56bb80d7590e2eef

tech-stack:
  added: []
  patterns:
    - "Change detection compares token_stream of the work-tree version with cat-file --filters HEAD:<path>, so tabs, CRLF and core.autocrlf never count"
    - "Git output only selects among files the scan already found under Custom/ (status path -> library rel_path), never names a file to open"
    - "One git status call per scan; HEAD versions read only for files git reports as changed"

key-files:
  created:
    - kicad_lib_manager/changes.py
    - tests/test_scan_changes.py
  modified:
    - kicad_lib_manager/sexpr.py
    - kicad_lib_manager/library_scanner.py
    - tests/test_sexpr.py
    - tests/test_scanner_issues.py
    - tests/test_layering.py

key-decisions:
  - "A footprint is compared as a whole file (token_stream of the root); a symbol is compared per top-level symbol, first of a repeated name wins"
  - "An oversized or unparseable HEAD version makes every current symbol or footprint of that file changed; an oversized or unparseable current file gives one 'Change highlight skipped for <file>: <reason>' line and no status"
  - "The skip lines for missing git, a Custom that is not its own checkout and a failing status share the code scan.changes_skipped and use only the first line of git's message"
  - "Skip text for an oversized file says 'the file is too large to compare' instead of a byte count, in keeping with the plain-language UI rule"

patterns-established:
  - "Module-attribute style (gitops.find_git, gitops.head_blob) so an ast test can pin which git functions a module may call"

requirements-completed: [SCAN-02]

coverage:
  - id: D1
    description: "A symbol whose tokens differ from the same-named symbol in Custom HEAD is changed; a symbol absent from HEAD (appended, renamed, or in a new file) is new"
    requirement: "SCAN-02"
    verification:
      - kind: integration
        ref: "tests/test_scan_changes.py#test_one_edited_symbol_is_marked_changed_with_one_log_line"
        status: pass
      - kind: integration
        ref: "tests/test_scan_changes.py#test_an_appended_symbol_is_new"
        status: pass
      - kind: integration
        ref: "tests/test_scan_changes.py#test_a_renamed_symbol_is_new_under_its_new_name"
        status: pass
      - kind: integration
        ref: "tests/test_scan_changes.py#test_every_symbol_of_an_untracked_library_file_is_new_in_file_order"
        status: pass
    human_judgment: false
  - id: D2
    description: "Tabs to spaces, LF to CRLF and core.autocrlf checkouts mark nothing; real edits are still found under autocrlf"
    requirement: "SCAN-02"
    verification:
      - kind: integration
        ref: "tests/test_scan_changes.py#test_replacing_every_tab_with_two_spaces_marks_nothing"
        status: pass
      - kind: integration
        ref: "tests/test_scan_changes.py#test_replacing_every_line_feed_with_crlf_marks_nothing"
        status: pass
      - kind: integration
        ref: "tests/test_scan_changes.py#test_a_checkout_with_autocrlf_and_no_edits_marks_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_sexpr.py -k token_stream (9 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Footprints added or changed under Custom/ footprint libraries appear on FootprintLibrary.changed sorted by name, one INFO line each"
    requirement: "SCAN-02"
    verification:
      - kind: integration
        ref: "tests/test_scan_changes.py#test_an_edited_footprint_is_changed_and_logged"
        status: pass
      - kind: integration
        ref: "tests/test_scan_changes.py#test_changed_footprints_are_sorted_by_name_ignoring_case"
        status: pass
    human_judgment: false
  - id: D4
    description: "Changed items of Custom/ libraries without the Atomic_ prefix get rows holding only those items; nothing outside Custom/ is marked"
    requirement: "SCAN-02"
    verification:
      - kind: integration
        ref: "tests/test_scan_changes.py#test_an_edit_in_a_library_without_the_prefix_gives_only_the_changed_row"
        status: pass
      - kind: integration
        ref: "tests/test_scan_changes.py#test_nothing_outside_custom_is_ever_marked"
        status: pass
    human_judgment: false
  - id: D5
    description: "Missing git, a Custom that is not its own checkout, a failing git status and an oversized library each cost one INFO line and leave the atomic check intact"
    requirement: "SCAN-02"
    verification:
      - kind: integration
        ref: "tests/test_scan_changes.py#test_missing_git_skips_the_highlight_with_one_line_and_keeps_the_atomic_check"
        status: pass
      - kind: integration
        ref: "tests/test_scan_changes.py#test_a_custom_that_is_not_a_git_checkout_skips_the_highlight_with_one_line"
        status: pass
      - kind: integration
        ref: "tests/test_scan_changes.py#test_a_failing_git_status_skips_the_highlight_with_its_first_line"
        status: pass
      - kind: integration
        ref: "tests/test_scan_changes.py#test_a_library_over_the_size_cap_is_skipped_with_one_line_and_no_status"
        status: pass
    human_judgment: false
  - id: D6
    description: "The scan only reads git: one status call on a clean Custom, HEAD read only for changed files, git state identical before and after, and changes.py calls only find_git, show_toplevel, status_entries, head_blob and GitContext"
    requirement: "SCAN-02"
    verification:
      - kind: integration
        ref: "tests/test_scan_changes.py#test_a_clean_custom_costs_one_status_call_and_reads_no_head_version"
        status: pass
      - kind: integration
        ref: "tests/test_scan_changes.py#test_the_scan_leaves_the_git_state_of_custom_alone"
        status: pass
      - kind: unit
        ref: "tests/test_scan_changes.py#test_changes_calls_only_the_read_only_git_functions"
        status: pass
    human_judgment: false
  - id: D7
    description: "Wording of the log lines ('Symbol Atomic_Connector / USB4105-GF-A: changed since the last Custom commit', 'Change highlight skipped: ...') reads well to the owner"
    verification: []
    human_judgment: true
    rationale: "Plain-language quality is a judgement about the owner's vocabulary; tests pin the text, not whether it is clear"

duration: 20min
completed: 2026-10-26
status: complete
---

# Phase 9 Plan 05: Change detection for Custom/ Summary

**Content-based New/Changed detection for Custom/ symbols and footprints: token_stream comparison against the Custom HEAD version through read-only gitops calls, wired into scan_all, with formatting-only edits ignored and one INFO line per skipped or marked part**

## Performance

- **Duration:** about 20 min
- **Completed:** 2026-10-26T13:08Z
- **Tasks:** 2 (1 tracer, 1 TDD)
- **Files modified:** 7 (2 created: changes.py, test_scan_changes.py)

## Accomplishments

- `sexpr.token_stream` walks a node iteratively (5000 nested lists fine) and drops whitespace and line endings by construction, so only content can differ.
- `changes.mark_changes` costs one `git status` on a clean Custom and reads HEAD versions only for files git reports; a status path is used only when it equals the `rel_path` of a library the scan already found under Custom/.
- Symbols: `SymbolEntry.status` set on atomic libraries' existing rows, rows holding only the changed items appended for other Custom libraries. Footprints: `ChangedFootprint` entries on the library, sorted by name ignoring case.
- Missing git, a Custom that is not its own checkout (including a plain folder inside a git repository) and a failing status each give exactly one `scan.changes_skipped` INFO line; the atomic check results stay.

## Task Commits

1. **Task 1: One changed symbol marked Changed end to end (tracer)** - `671004e` (feat)
2. **Task 2 RED: failing tests for footprints, skip lines and formatting-only changes** - `58d2c20` (test)
3. **Task 2 GREEN: changed footprints and the skip line** - `e9e50b6` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified

- `kicad_lib_manager/sexpr.py` - `token_stream`
- `kicad_lib_manager/changes.py` - `mark_changes` (new, Qt-free, read-only git through gitops)
- `kicad_lib_manager/library_scanner.py` - `scan_all` calls `mark_changes` after the atomic check (progress 98)
- `tests/test_scan_changes.py` - 26 git-backed tests (new)
- `tests/test_sexpr.py` - 9 token_stream tests
- `tests/test_scanner_issues.py` - model-issue scan test compares non-INFO codes and expects one `scan.changes_skipped`
- `tests/test_layering.py` - `changes` registered in ALLOWED and `_CODE`; `library_scanner` may import it

## Decisions Made

See `key-decisions` in the frontmatter. The one that matters downstream: every scan of a Custom/ tree that is not a git checkout now carries one INFO `scan.changes_skipped` line, so any test that asserts an exact issue list from `scan_all` on such a tree must filter by code or severity (only `test_scan_all_includes_model_issues` needed it).

## Deviations from Plan

None - plan executed exactly as written.

## TDD Gate Compliance

Task 1 is a tracer (single production commit with its tests). Task 2 has RED then GREEN commits; no REFACTOR commit was needed.

- **Task 2 RED (`58d2c20`):** 8 of the new or changed tests failed on the planned assertions: footprint lists were `[]` where `ChangedFootprint` entries were expected, and the skip lines were `[]` where one `scan.changes_skipped` line was expected (missing git, plain tree, plain folder inside a git repo, failing status, and the scanner-issues test). Semantic assessment: the target tests executed and failed on the intended assertions, not on import, fixture or syntax faults. The `check tdd-red-evidence` classifier was not run (plain pytest output is not a format it supports).
- The 9 `token_stream` tests and the symbol-side tests added in Task 2 (renamed, untracked file, tab, CRLF, autocrlf, non-Atomic, Wurth, deleted, size cap, git call counts, ast guard) already passed at RED because Task 1 implemented `token_stream` and the symbol path; they are guards, not RED evidence.

## Issues Encountered

- A heredoc append of the token_stream tests halved the doubled backslashes in a test literal (one test failed on a real line break inside the string). Fixed by building the string from a raw literal with the Edit tool; no production impact.
- `Custom/` and `WurthElektronik/KiCad-Library` are not checked out in this worktree, so the three submodule-backed tests (`test_sexpr.py:680`, `test_scanner_issues.py:273` and `:286`) skip; the orchestrator's post-merge run covers them. All 26 new scan tests run (git is on PATH) and none skip.

## Known Stubs

None.

## Threat Flags

None. T-09-10 (gitops only, find_git refuses an in-repo git, rev-parse/status/cat-file pinned by an ast test), T-09-11 (size and node caps on both versions, tested by lowering the cap) and T-09-12 (status paths read only when they equal a scanned library's rel_path) are implemented and tested.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The tree already renders `SymbolEntry.status` and `FootprintLibrary.changed` (09-02); a hand edit in KiCad shows on the next scan with no further widget change.
- Open for the owner: the wording of the new log lines (coverage D7). Deleted and renamed-away parts are not listed, as flagged in the plan.

## Self-Check: PASSED

- FOUND: kicad_lib_manager/changes.py, tests/test_scan_changes.py
- FOUND commits: 671004e, 58d2c20, e9e50b6
- `pytest tests/test_scan_changes.py tests/test_sexpr.py tests/test_scanner_issues.py tests/test_scanner_skip_dirs.py tests/test_layering.py tests/test_atomic_scan.py` - 253 passed, 3 skipped (submodules absent)
- `pytest tests/test_main_window.py tests/test_importer_layering.py tests/test_models.py tests/test_library_table_atomic.py tests/test_atomic_check.py` - 137 passed
- `pytest tests/test_sexpr.py -k token_stream` - 9 passed; `pytest tests/test_scan_changes.py` - 26 passed

---
*Phase: 09-atomic-rule-check-and-scan-detection*
*Completed: 2026-10-26*
