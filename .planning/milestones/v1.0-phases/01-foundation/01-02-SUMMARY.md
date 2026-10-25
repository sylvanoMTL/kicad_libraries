---
phase: 01-foundation
plan: 02
subsystem: filesystem
tags: [atomic-write, backup, eol, bom, pytest, windows]

requires:
  - phase: 01-foundation
    provides: "Plan 01 tracer fsutil (decode_source, encode_source, atomic_write_bytes) and Severity/Issue"
provides:
  - "atomic_write_bytes with fs.read_only / fs.locked (~1 s retry) / fs.write_failed Issues"
  - "atomic_write_text, backup_file, default_backup_dir, normalize_eol"
  - "Severity/Issue contract tests pinned against LogPanel.COLORS"
affects: [phase-02-table-generation, phase-04-install]

requirements-completed: [FOUND-05, FOUND-04]

actuals:
  tokens: 12000
  tasks: 2
  commits: 4

plan_head_before: ccda2fd23dfca20abaf95b5ef14cc280900db9c1
plan_head_after: 4806fea08f3dcee009533396f24304012017f9be
commits: 4

tech-stack:
  added: []
  patterns:
    - "Issue-returning side-effect helpers with injectable sleep for fast failure tests"
    - "Exclusive-create ('xb') for temp and backup files"

key-files:
  created:
    - tests/test_fsutil.py
    - tests/test_models.py
  modified:
    - kicad_lib_manager/fsutil.py

key-decisions:
  - "Retry schedule _RETRY_DELAYS = (0.05, 0.1, 0.2, 0.3, 0.35): 5 delays, 6 replace attempts, exactly 1.0 s total (D-05 discretion)"
  - "default_backup_dir: LOCALAPPDATA (win32), ~/Library/Application Support (darwin), XDG_DATA_HOME or ~/.local/share (other), under KiCadExtLibManager/backups (D-06 discretion)"
  - "decode_source from Plan 01 already met the OQ3/OQ5 rules; left unchanged"

duration: 4 min
completed: 2026-10-18
status: complete

coverage:
  - id: D1
    description: "Atomic write failure matrix: read-only, locked retry, OSError/fsync, missing dir, concurrent writers, no temp left"
    requirement: FOUND-05
    verification:
      - kind: unit
        ref: "tests/test_fsutil.py#test_read_only_target_returns_issue_without_retry, test_held_open_target_returns_locked_issue_after_retries, test_lock_released_mid_retry_window_succeeds, test_fsync_failure_returns_write_failed, test_concurrent_writers_leave_one_complete_payload"
        status: pass
    human_judgment: false
  - id: D2
    description: "Numbered backups matching table_generator.backup_existing, off-repo default backup dir"
    requirement: FOUND-04
    verification:
      - kind: unit
        ref: "tests/test_fsutil.py#test_backup_file_name_matches_backup_existing_with_gaps, test_default_backup_dir_*"
        status: pass
    human_judgment: false
  - id: D3
    description: "EOL/BOM/encoding identity matrix, normalize_eol and Severity/Issue contract"
    requirement: FOUND-04
    verification:
      - kind: unit
        ref: "tests/test_fsutil.py#test_decode_encode_is_byte_identical, tests/test_models.py"
        status: pass
    human_judgment: false
---

# Phase 1 Plan 02: Atomic Write Hardening and Backups Summary

**Atomic writes now return fs.read_only / fs.locked (about 1 s retry) / fs.write_failed Issues with the original untouched, plus numbered off-repo backups, EOL normalisation and a Severity/Issue contract pinned to the log panel colors**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-18T15:03:30Z
- **Completed:** 2026-10-18T15:07:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `atomic_write_bytes` pre-checks read-only targets (no retry), retries `os.replace` on PermissionError over a 1.0 s window, and maps every other OSError to `fs.write_failed`; the temp file is always removed.
- `backup_file` reproduces the `<name>_backup_<N>` scheme exactly (verified against `table_generator.backup_existing`), creates the backup directory, and uses exclusive create; `default_backup_dir` points outside the repo without creating anything or importing Qt.
- `normalize_eol`, `atomic_write_text`, and the EOL x BOM identity matrix are covered; `tests/test_models.py` pins Severity values to `LogPanel.COLORS`.
- Full suite: 55 passed, 1 skipped (Custom submodule not checked out in this worktree).

## Task Commits

1. **Task 1 RED:** `5079dd2` (test) - failing failure-matrix tests
2. **Task 1 GREEN:** `c35b74f` (feat) - read-only check, locked retry, atomic_write_text
3. **Task 2 RED:** `f236c79` (test) - backup, default dir, EOL, Issue contract tests
4. **Task 2 GREEN:** `4806fea` (feat) - backup_file, default_backup_dir, normalize_eol

## Files Created/Modified
- `kicad_lib_manager/fsutil.py` - hardened atomic write, text writer, backups, default backup dir, EOL normaliser
- `tests/test_fsutil.py` - 350 lines: failure matrix, backup naming parity, platform dirs, EOL/BOM/encoding
- `tests/test_models.py` - Severity/Issue contract

## Decisions Made
- Retry schedule `(0.05, 0.1, 0.2, 0.3, 0.35)`; default backup folder per OS as listed in frontmatter.
- No change to `decode_source`: tie, lone-CR and no-EOL rules already matched the behavior list.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test design] Dropped a COLORS[Severity.X] lookup test**
- **Found during:** Task 2
- **Issue:** Not in the plan; `Severity(str, Enum)` hashes by member name, so `COLORS[Severity.WARNING]` would KeyError. Phase 2 must index COLORS with `.value`.
- **Fix:** Did not add that assertion; recorded as a Phase 2 hand-off note below.

**2. [Rule 2 - Missing critical] Truncated-backup cleanup**
- **Found during:** Task 2
- **Issue:** A copy failing mid-stream would leave a partial `_backup_N` the Restore dialog would list.
- **Fix:** `backup_file` unlinks the partial file and returns the fs.backup_failed Issue.
- **Files modified:** kicad_lib_manager/fsutil.py (part of `4806fea`)

**Total deviations:** 2 (1 test-scope note, 1 Rule 2 hardening). **Impact:** none on plan scope.

Note: the RED step for Task 1 was first collected as an ImportError (invalid RED); the test import was changed to module-attribute access so the committed RED fails on the planned behavior (TypeError for missing kwargs / AttributeError for missing functions).

## Issues Encountered
- The worktree had no `env/`; created with `py -3.14 -m venv env` and the pinned `requirements-dev.txt` (gitignored, not staged).

## Known Stubs
None.

## Threat Flags
None.

## Next Phase Readiness
- Phase 2 can route table writes through `atomic_write_bytes`/`atomic_write_text` and `backup_file`; messages start with "Could not write" / "Could not back up", compatible with existing substring routing.
- Phase 2 hand-off: when mapping `Issue.severity` to `COLORS`, use `issue.severity.value`.

## Self-Check: PASSED

- fsutil.py, tests/test_fsutil.py, tests/test_models.py exist; commits 5079dd2, c35b74f, f236c79, 4806fea are ancestors of HEAD.
- Full suite `55 passed, 1 skipped`; held-open Windows test ran (not skipped).
