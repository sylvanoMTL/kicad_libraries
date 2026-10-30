---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 13
subsystem: import-dialog
tags: [pyside6, commit-gate, atomic-check, changed-diff, review-disposition]
status: complete

requires:
  - phase: 11-commit-gate-and-commit-panel-fixes
    provides: "changed_diff (11-08), parent-only counts as committed (11-10), Check again and Open Check Atomic Parts in the dialog (11-11), all_identical probe field (11-06)"
provides:
  - "Fixes applied from the import dialog's check dialog reach the main window log and rescan, then the commit is re-checked without committing"
  - "Double-click on a changed or added file opens changed_diff"
  - "No Not committed warning when Custom already held every planned file"
  - "The eight Phase 6 review findings recorded as fixed"
affects: []

plan_head_before: e193ac2a0e57f654a223c85938e78b3d6a621073
plan_head_after: 09f7ad7
actuals:
  tokens: 9000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "The import dialog re-emits the check dialog's applied fixes and the main window alone logs and rescans"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/main_window.py
    - tests/test_import_dialog.py
    - tests/test_main_window_import.py
    - .planning/milestones/v1.0-phases/06-git-commit-step/06-REVIEW-DISPOSITION.md

key-decisions:
  - "Applied fixes start only the read-only Check again; a commit still needs its own Commit click (T-11-25)"
  - "A file counts as changed when its CommitFile has a note or its display path is in the probe's stale list"
  - "The disposition table rows were set to fixed along with the front matter so the two agree"

requirements-completed: [GIT-06, REV-09]

coverage:
  - id: D1
    description: "Fixes applied from the check dialog opened by the import dialog are re-emitted, logged and rescanned by the main window, and the commit is re-checked without any commit"
    requirement: GIT-06
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_fixes_applied_reemitted_and_rechecked"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_main_window_rescans_after_import_dialog_fixes"
        status: pass
    human_judgment: false
  - id: D2
    description: "A changed-since-install or added file opens changed_diff on double-click; an amber pre-import file still opens pre_import_diff"
    requirement: GIT-06
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_changed_file_opens_changed_diff"
        status: pass
    human_judgment: false
  - id: D3
    description: "Closing after an all-identical probe or a parent-only bump logs no Not committed warning, and a parent-only bump starts no re-probe"
    requirement: REV-09
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_parent_only_or_all_identical_not_logged_as_not_committed"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_parent_only_bump_not_logged_and_not_reprobed"
        status: pass
    human_judgment: false
  - id: D4
    description: "06-REVIEW-DISPOSITION.md shows WR-01..WR-05 and IN-01..IN-03 fixed with open: 0"
    requirement: REV-09
    verification:
      - kind: other
        ref: "grep -c 'disposition: fixed' 06-REVIEW-DISPOSITION.md prints 8; grep '^open: 0' finds the line"
        status: pass
    human_judgment: false
  - id: D5
    description: "The commit panel look and a real PowerShell paste in the running app"
    verification: []
    human_judgment: true
    rationale: "Manual-only rows in the phase validation: layout and a real shell paste are not asserted by any test"

duration: 75min
completed: 2026-10-30
---

# Phase 11 Plan 13: Applied fixes, changed diff and phase gate Summary

**Fixes made from the commit panel's check dialog now reach the main window's rescan and re-check the commit without committing, changed and added files open their diff, nothing is warned as uncommitted when Custom already holds the files, and the full suite passes (3065 passed).**

## Performance

- **Started:** 2026-10-30T10:50:00Z (approx.)
- **Completed:** 2026-10-30T11:35:00Z (approx.)
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- `ImportDialog.atomic_fixes_applied = Signal(object)`; `_on_atomic_fixes_applied(issues)` re-emits the list and then runs `_on_check_again()`. The check dialog's `applied` signal is connected to it in `_on_open_atomic_check`.
- `main_window._open_import` passes `atomic_backup_root=ATOMIC_BACKUP_ROOT` and connects `atomic_fixes_applied` to `_on_atomic_fixes_applied` (log, then rescan).
- `ImportCore.changed_diff`; `_on_commit_file_activated` routes a file with a note or a stale display path to `core.changed_diff`, others to `core.pre_import_diff`.
- `_log_not_committed` returns when the probe says every file is already identical to HEAD. A parent-only outcome with a parent commit already counted as committed (11-10), so it logs nothing and starts no re-probe; a regression test pins that.
- Review dispositions: eight findings `fixed`, `open: 0`.

## Task Commits

1. **Task 1 (tracer): applied fixes reach the rescan and re-check** - `7768c67` (feat)
2. **Task 2 RED: changed diff and D-14 tests** - `26b42bc` (test)
3. **Task 2 GREEN: changed_diff routing and all-identical log rule** - `f0564f1` (feat)
4. **Task 3: dispositions** - `09f7ad7` (docs)

## Verification

- Tracer verify (`-k "fixes or rescans"`): 2 passed.
- Task 2 verify (`-k "changed_file or not_committed or not_logged"`, plus dirty-file and fixes tests): 7 passed.
- Phase gate `pytest -m "not wurth" -q -rs` from the worktree: 3065 passed, 33 skipped, 3 deselected (17 min). Skips: the two symlink skips, the two UAT-directory skips, and worktree-specific skips for the `Custom` submodule (not checked out) and the licence-restricted `downloaded_examples/` samples (not present in a worktree). Those extra skips are an effect of running in a worktree; the orchestrator's run on the main checkout is the authoritative gate for the expected-four rule and the live `Custom/` guard.

## Deviations from Plan

None - plan executed exactly as written. One small addition: the disposition table rows were set to `fixed` as well as the front matter so the file is consistent. Test 2 for the parent-only bump needed the probe to carry `head` and `gitlink_old` that differ, so that the panel enables the bump button; that is test setup only.

## Issues Encountered

- Shell commands that mix git with heredocs or compound `&&` chains were refused by the worktree guard; commit messages went through the Write tool and `git commit -F`, and git calls were run one per command.
- `gsd_run` is not available in the worktree, so the plan commit ledger file was not written; `plan_head_before` is the known base SHA.

## Known Stubs

None.

## Threat Flags

None. T-11-25 is mitigated: applying fixes starts only `recheck_commit`; `test_fixes_applied_reemitted_and_rechecked` asserts `run_commit` is never called.

## Next Phase Readiness

Phase 11 plans are complete. Manual rows remain for the end of the phase: the commit panel look and a real PowerShell paste.

## Self-Check: PASSED

- Commits `7768c67`, `26b42bc`, `f0564f1`, `09f7ad7` are ancestors of HEAD.
- `import_dialog.py` contains `atomic_fixes_applied = Signal(object)` and `core.changed_diff(`; `main_window.py` contains `atomic_backup_root=ATOMIC_BACKUP_ROOT`; `06-REVIEW-DISPOSITION.md` has `open: 0` and 8 `disposition: fixed`.
