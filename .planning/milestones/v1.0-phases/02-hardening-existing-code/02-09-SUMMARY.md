---
phase: 02-hardening-existing-code
plan: 09
subsystem: scanner
tags: [scanner, issues, nickname-collision, log-panel, severity]
requires:
  - phase: 02-01
    provides: LogPanel.log_issue, MainWindow._log_issues, offscreen MainWindow test harness
provides:
  - ScanResult.issues (list[Issue]) replacing the string warning list
  - SymbolLibrary.collision_peers / FootprintLibrary.collision_peers
  - find_nickname_collisions and the scan.nickname_collision Issue code
  - Issue-returning cross_reference and check_3d_model_paths
  - Severity formats as its value; downloaded_examples/ skipped by the scan
affects: [02-02, 02-05, 02-06]
tech-stack:
  added: []
  patterns: ["scan findings are Issue objects with their own severity; no substring classification"]
key-files:
  created:
    - tests/test_log_panel.py
    - tests/test_scanner_issues.py
  modified:
    - kicad_lib_manager/models.py
    - kicad_lib_manager/library_scanner.py
    - kicad_lib_manager/main_window.py
    - tests/test_scanner_skip_dirs.py
key-decisions:
  - "Severity.__str__ returns self.value; one method fixes str() and f-string formatting on 3.10 and 3.12+ (IN-02)"
  - "downloaded_examples added to SKIP_DIRS so vendor packages never become a library source (IN-03)"
  - "Collision pass resets collision_peers per kind on every call, making it idempotent; nicknames are never touched"
requirements-completed: [HARD-08]
duration: 15 min
completed: 2026-10-19
status: complete
commits: 4
plan_head_before: 107cae314ac58f8cfb40e799a59bd19c024ee0cd
plan_head_after: 6e47413830f5536a2ee2989f31d7d70beb2e7b49
actuals:
  tokens: 14000
  tasks: 2
  commits: 4
---

# Phase 2 Plan 09: Scan Issues and Nickname Collisions Summary

**Scan findings now travel as `Issue` objects into the log with their own severity, and the scan reports every shared library nickname per kind while recording each library's same-nickname peers for the widget.**

## Accomplishments

- `ScanResult.issues` replaces the string list; `cross_reference` emits `scan.footprint_lib_missing` and `check_3d_model_paths` emits `scan.model_absolute` WARNING Issues with unchanged text. `_on_scan_finished` logs them through `_log_issues`, and logs "No warnings." only when no WARNING or ERROR Issue exists.
- `Severity` and `Issue` moved above the library dataclasses; `Severity.__str__` returns the value (IN-02).
- `downloaded_examples` added to `SKIP_DIRS` (IN-03), with a synthetic-repo regression test.
- `collision_peers` added as the last field of both library dataclasses (positional construction in existing tests still works).
- `find_nickname_collisions` reports one `scan.nickname_collision` WARNING per shared nickname, separately for symbols and footprints, naming all rel_paths, and fills sorted `collision_peers`. `scan_all` puts these Issues first.
- LogPanel contract pinned: colour per Severity and HTML escaping.

## TDD Gate Compliance

| Task | RED | GREEN |
|------|-----|-------|
| 1 | 64d82e2 `test(02-09)` | ecba0e2 `feat(02-09)` |
| 2 | b145981 `test(02-09)` | 6e47413 `feat(02-09)` |

RED evidence, task 1: 10 tests failed on assertions/AttributeErrors for the planned behaviour (Severity str, `downloaded_examples`, `issues`, `collision_peers`, Issue-shaped scan output); 9 existing-behaviour tests passed. Task 2: all 9 tests executed and failed (AttributeError for the missing `find_nickname_collisions`, empty `collision_peers` in the `scan_all` test). The test file calls `library_scanner.find_nickname_collisions` through the module rather than a top-level import so RED is a test failure, not a collection error. The classifier `gsd_run check tdd-red-evidence` was not run (no record file produced); semantic assessment was done by reading pytest output. No REFACTOR commit was needed.

## Task Commits

1. Task 1 RED: 64d82e2; GREEN: ecba0e2
2. Task 2 RED: b145981; GREEN: 6e47413

## Deviations from Plan

None - plan executed exactly as written. Note: the model-default and Issue-shape tests (`test_scan_result_carries_issues_not_warnings`, `test_libraries_default_to_no_collision_peers`, `test_model_absolute_issue_shape`, `test_scan_all_cross_reference_issue`) live in `tests/test_scanner_skip_dirs.py` because that file was already in Task 1's file list.

## Verification

- `pytest -q` (worktree, submodules absent): 376 passed, 7 skipped. Baseline with submodules was 388 passed, 2 skipped; the extra skips are submodule-dependent tests.
- All Task 1 and Task 2 grep acceptance criteria pass (`issues: list[Issue]`, 0 `warnings: list`, 2 `collision_peers: list[str]`, issue codes, `self._log_issues(result.issues)`, 0 `result.warnings`, `__str__`, `"downloaded_examples"`, 0 nickname assignments).
- `pytest tests/test_scanner_issues.py -k collision`: 7 passed.
- Plan-level `git -C Custom status --porcelain` was not run: the Custom submodule is not checked out in this worktree. The plan only reads Custom/ and no file under it was touched.

## Known Stubs

None.

## Threat Flags

None. Mitigations T-02-28, T-02-29 and T-02-32 are implemented as planned.

## Self-Check: PASSED

- Files exist: tests/test_log_panel.py, tests/test_scanner_issues.py, modified sources and tests.
- Commits 64d82e2, ecba0e2, b145981, 6e47413 are ancestors of HEAD.
