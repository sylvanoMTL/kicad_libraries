---
phase: quick-261022-gnn
plan: 01
subsystem: kicad-config
tags: [kicad_common.json, path-variables, safety, confirm, worktree-guard]
requires: [HARD-03]
provides: [guarded sync_kicad_path_vars, MainWindow._sync_path_vars]
affects: [kicad_lib_manager/library_scanner.py, kicad_lib_manager/main_window.py]
key-files:
  modified:
    - kicad_lib_manager/library_scanner.py
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_kicad_config.py
    - tests/test_main_window.py
    - tests/test_main_window_import.py
    - .planning/PROJECT.md
    - .planning/STATE.md
decisions:
  - "KiCad path variables are never written silently; worktree and other-checkout runs are refused with a WARNING"
status: complete
estimate:
  tokens: 90000
actuals:
  tokens: 30000
  tasks: 3
  commits: 3
plan_head_before: 60c80867c21d28db5281cc03156e6a2fcaf14848
plan_head_after: 7b426fb2ba484e383fba8c7453192b6b53cdcacc
commits: 3
completed: 2026-10-22
---

# Quick 261022-gnn: Guard KiCad path-variable sync Summary

`sync_kicad_path_vars` now writes only after a `confirm(changes)` callback returns True, and refuses outright from a git worktree or a checkout other than the configured `KICAD_LIB_GITHUB`.

## Tasks

1. Tracer: `confirm` keyword on `sync_kicad_path_vars` (no callback = `config.confirm_required` WARNING, No = `config.declined` INFO), `MainWindow._confirm_path_var_changes` (Yes/No, default No, `VAR: old -> new` lines) and `_sync_path_vars` used by Generate and the post-install new-library branch. Commit 12e3ca4.
2. `_norm_path` and `_path_var_refusal`: `config.worktree_refused` (`.git` is a file) and `config.other_checkout_refused` (normalised compare), returned before any prompt, backup or write. Unset or empty `KICAD_LIB_GITHUB` goes through confirmation. Commit ee1daf6.
3. Help page bullet, PROJECT.md Key Decisions row, STATE.md Decisions bullet. Commit 7b426fb.

## Verification

- tests/test_kicad_config.py, test_main_window.py, test_main_window_import.py: 94 passed.
- Full suite with the known kicad-cli baseline deselected: 1444 passed, 72 skipped, 0 failed (the extra skips, versus the planning baseline of 5, are Custom and Wurth submodule tests, as the submodules are not initialised in a worktree).
- grep gates: `self._sync_path_vars()` appears 2 times, `sync_kicad_path_vars(` once in main_window.py, no PySide6 in library_scanner.py.
- Phase 5 files (import_dialog.py, importer/form.py, test_import_form.py, test_import_dialog.py) untouched.
- All sync calls in tests use tmp_path overrides; the real kicad_common.json and the real library checkout were not touched; the GUI was not launched.

## Deviations from Plan

**1. [Rule 1 - Bug] Existing test conflicted with the other-checkout refusal**
- **Found during:** Task 2
- **Issue:** `test_populated_vars_keep_other_entries_and_report_update` seeded `KICAD_LIB_GITHUB` as `C:/old`, a different checkout, which the new guard (correctly) refuses. The plan said existing tests pass unchanged, which is impossible with that seed value.
- **Fix:** The seed is now the same checkout spelled with backslashes (still a change, not another checkout); the assertions check that old value in the update message. The behaviour under test (other vars kept, update reported) is unchanged.
- **Files modified:** tests/test_kicad_config.py
- **Commit:** ee1daf6

**2. Test-fixture placement:** `fake_question` is patched at fixture level (outside `make()`) as the plan requires; in `fake_sync`, `**kwargs` comes before the explicit overrides so a duplicate keyword raises TypeError.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

Commits 12e3ca4, ee1daf6 and 7b426fb exist on the branch; all modified files exist.
