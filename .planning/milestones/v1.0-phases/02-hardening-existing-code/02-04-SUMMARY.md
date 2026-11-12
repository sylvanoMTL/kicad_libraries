---
phase: 02-hardening-existing-code
plan: 04
subsystem: kicad-config
tags: [kicad_common.json, atomic-write, backup, version-ordering, tasklist, pyside6, pytest]

requires:
  - phase: 02-hardening-existing-code
    provides: "fsutil backup/atomic write helpers (02-08), _log_issues and offscreen MainWindow harness (02-01), Issue-returning scanner (02-09)"
provides:
  - "Numeric KiCad version selection (parse_version, newest_version_dirs) for the config dir and footprint dir"
  - "kicad_process.kicad_running(): exact-name KiCad editor detection via absolute tasklist.exe / ps, no shell"
  - "sync_kicad_path_vars returning Issues: null-vars safe, shape checked, D-13 re-parse verification, numbered backup, atomic replace, keep-10 pruning"
  - "_on_generate routes config sync Issues through _log_issues; no substring severity routing left in main_window"
  - "table_generator, library_scanner, kicad_process pinned Qt-free and downward-only in test_layering"
affects: [02-05, 02-06, 02-07, importer phases that call sync_kicad_path_vars]

actuals:
  tokens: 21000
  tasks: 3
  commits: 3

plan_head_before: eedf779fdf8760d400048a6ef448634753202746
plan_head_after: f6d93bccbcf6889aa3ed5704f774e885ed668437

tech-stack:
  added: []
  patterns:
    - "Injectable base paths (config_base, backup_root, running) so config tests never reach the owner's real KiCad config"
    - "Verify-by-reparse before overwrite of a file owned by another program (only_vars_changed)"
    - "Per-version backup folders: <app-data backups>/kicad_common/<version>/"

key-files:
  created:
    - kicad_lib_manager/kicad_process.py
    - tests/test_kicad_config.py
    - tests/test_kicad_process.py
  modified:
    - kicad_lib_manager/library_scanner.py
    - kicad_lib_manager/main_window.py
    - tests/test_main_window.py
    - tests/test_layering.py

key-decisions:
  - "kicad_common.json backups live in default_backup_dir()/kicad_common/<version dir name>/ so 9.0 and 10.0 numbering and the keep-10 window never mix (assumption A6)"
  - "Config tests generate their JSON variants in-test; no tests/fixtures/kicad/ directory, because test_fixtures parses every fixture as an S-expression"
  - "A running KiCad only warns (config.kicad_running); the write still proceeds"
  - "Generate runs both table writes first, then the config sync, then the history update; each is independent"

patterns-established:
  - "Services return list[Issue]; main_window only calls _log_issues and never inspects message text"
  - "Absolute-path, list-argument, no-shell subprocess calls with timeout and CREATE_NO_WINDOW"

requirements-completed: [HARD-02, HARD-03, HARD-04]

coverage:
  - id: D1
    description: "10.0 is chosen over 9.0 for both the KiCad config dir and footprint dir; non-numeric folders are ignored"
    requirement: HARD-04
    verification:
      - kind: unit
        ref: "tests/test_kicad_config.py#test_config_dir_prefers_ten_over_nine"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_config.py#test_footprint_dir_prefers_ten_over_nine_on_windows"
        status: pass
    human_judgment: false
  - id: D2
    description: "kicad_common.json is backed up, verified, atomically written, only environment.vars changes, null vars and malformed shapes never crash or corrupt"
    requirement: HARD-03
    verification:
      - kind: unit
        ref: "tests/test_kicad_config.py (35 tests: null/populated/correct/crlf/bom/json/shape/not_found/verify/running/read_only/locked/backup/prune)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Running KiCad processes are detected without a shell and failures are silent"
    requirement: HARD-03
    verification:
      - kind: unit
        ref: "tests/test_kicad_process.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Generate with a read-only sym-lib-table logs one error, still writes fp-lib-table, runs the config sync and updates history, raising nothing"
    requirement: HARD-02
    verification:
      - kind: integration
        ref: "tests/test_main_window.py#test_generate_with_read_only_sym_table_logs_one_error_and_finishes"
        status: pass
      - kind: integration
        ref: "tests/test_main_window.py#test_generate_without_kicad_config_warns_and_still_writes_both_tables"
        status: pass
    human_judgment: false

duration: 6min
completed: 2026-10-19
status: complete
---

# Phase 2 Plan 04: KiCad config write hardening Summary

**Numeric KiCad version choice plus a backed-up, re-parse-verified, atomic kicad_common.json sync that survives `vars: null`, with all config results logged by Issue severity.**

## Performance

- **Duration:** about 6 min of wall-clock (2026-10-19T08:57:59Z to about 09:04Z)
- **Tasks:** 3
- **Files modified:** 7 (3 created, 4 modified)

## Accomplishments

- `parse_version` / `newest_version_dirs` order dotted-integer folders numerically; `find_kicad_config_dir(base)` and `find_kicad_footprint_dir(base, platform=)` use them and accept injected bases. `10.0-rc1` and `kicad-extras` are ignored.
- `kicad_process.kicad_running()` (stdlib only) reads `tasklist.exe /NH /FO CSV` by absolute `System32` path (or `ps -A -o comm=`), matches exact image names, excludes `kicad-cli`, and returns `[]` on any failure.
- `sync_kicad_path_vars` now returns `list[Issue]`: only the newest config dir is considered, `vars: null` counts as `{}`, bad JSON or shapes give ERROR Issues with nothing written, a re-parse check (`_only_vars_changed`) guards the write, the file is backed up to `kicad_common/<version>/kicad_common.json_backup_N`, written through `fsutil.atomic_write_text` keeping BOM and EOL, and the newest 10 backups are kept (read-only old backups are cleared and removed, unremovable ones only warn).
- `_on_generate` logs the sync through `_log_issues`; the last substring-based severity choice in `main_window.py` is gone. The GUI test proves a read-only `sym-lib-table` gives exactly one error line while `fp-lib-table`, the config sync and destination history all still happen.
- `test_layering` now pins `table_generator`, `library_scanner` and `kicad_process` as Qt-free and downward-only.

## Task Commits

1. **Task 1: Numeric KiCad version selection with injectable base paths** - `1aed74d` (feat)
2. **Task 2: kicad_running() and backed-up, verified, atomic kicad_common.json sync** - `dfcb01c` (feat)
3. **Task 3: Route config sync Issues in Generate, prove HARD-02 in the GUI, pin layering** - `f6d93bc` (feat)

**Plan metadata:** committed separately as `docs(02-04)` after this file.

_Note: tests were written before the implementation in each task and run to a failing state first (Task 1 and Task 2 failed at import/collection of the not-yet-existing names; Task 3 failed with the real `TypeError: argument of type 'Issue' is not a container` in `_on_generate`). Each task was committed as one feat commit carrying both tests and code, as the plan specified._

## Files Created/Modified

- `kicad_lib_manager/kicad_process.py` - `kicad_running()` and `_KICAD_PROCESSES`
- `kicad_lib_manager/library_scanner.py` - version helpers, injectable finders, Issue-returning `sync_kicad_path_vars`, `_only_vars_changed`, `_prune_backups`
- `kicad_lib_manager/main_window.py` - `_on_generate` uses `_log_issues(sync_kicad_path_vars(REPO_ROOT))`
- `tests/test_kicad_config.py` - 35 tests on synthetic `tmp_path` trees
- `tests/test_kicad_process.py` - 7 tests with `subprocess.run` monkeypatched
- `tests/test_main_window.py` - `make_window` runs the real sync against a tmp KiCad tree (`empty_config` option, `make_window.config_file`), two new Generate tests
- `tests/test_layering.py` - three more modules in `ALLOWED` and the fresh-interpreter Qt check

## Decisions Made

- Backups go under `default_backup_dir()/kicad_common/<version>/` (assumption A6 resolved as planned).
- Config JSON variants are generated inside the tests (no committed fixtures directory), as the plan directed.
- A running KiCad is a WARNING only; the write proceeds.

## Deviations from Plan

None - plan executed exactly as written.

Minor test-level notes, not plan deviations: the first draft of a Task 1 test that grepped `library_scanner.py` for `reverse=True` was dropped because `newest_version_dirs` legitimately sorts numerically with `reverse=True`; behaviour is covered by the 10.0-over-9.0 tests. Qt lower-cases the colour in `toHtml()`, so the warning-colour assertion compares `#cc7700` case-insensitively.

**Total deviations:** 0 auto-fixed.
**Impact on plan:** none.

## Issues Encountered

- Between the Task 2 and Task 3 commits `_on_generate` still held the old substring loop and would have raised on `Issue` objects. Tests patch `sync_kicad_path_vars`, so the suite stayed green at the Task 2 commit, but that intermediate commit is not safe to run Generate from. Task 3 (next commit) fixes it.
- Edge-probe assumptions carried from the plan (unchanged): "only environment.vars changes" is checked semantically and is byte-exact only for KiCad-formatted files (2-space indent); a hand-reformatted file is rewritten in KiCad's format with the original in the backup. 10.0 is proven only on synthetic trees (no KiCad 10 install on this machine).

## Verification

- Full suite from the worktree: 454 passed, 7 skipped (submodules not checked out), 0 failed.
- `pytest tests/test_kicad_config.py tests/test_kicad_process.py tests/test_layering.py`: all pass.
- Acceptance greps: no `shell=True`, no `.write_text(` and no `setdefault("vars"` in the touched modules; `System32`, `timeout=`, `ensure_ascii=False`, `_only_vars_changed`, `_prune_backups`, `"kicad_process": set()` all present; zero substring-routing lines remain in `main_window.py`.
- Spot check (read only): the owner's `%APPDATA%/kicad/{7.0,8.0,9.0}/kicad_common.json` modification times (2024-10-25, 2024-11-02, 2026-10-18) predate this run, so no test touched them.

## Known Stubs

None.

## Threat Flags

None. The only new external surface is the `tasklist.exe` / `ps` subprocess, which is already covered by T-02-13 (absolute path, list args, no shell, timeout).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for the remaining wave-3/4 plans. `sync_kicad_path_vars(repo_root, *, config_base, backup_root, running)` and `kicad_running()` are the stable seams; `main_window.py` and `tests/test_main_window.py` are the shared files with plan 02-06.
- No blockers.

## Self-Check: PASSED

- Files present: `kicad_lib_manager/kicad_process.py`, `tests/test_kicad_config.py`, `tests/test_kicad_process.py` (verified below by `[ -f ]`).
- Commits `1aed74d`, `dfcb01c`, `f6d93bc` are ancestors of HEAD.

---
*Phase: 02-hardening-existing-code*
*Completed: 2026-10-19*
