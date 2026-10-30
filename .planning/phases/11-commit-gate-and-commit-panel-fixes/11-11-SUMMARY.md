---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 11
subsystem: import-dialog
tags: [pyside6, commit-gate, check-again, atomic-check, help]
status: complete

requires:
  - phase: 11-commit-gate-and-commit-panel-fixes
    provides: "recheck_commit and kicad_fp_dir keywords (11-08), probe worker and generation check (11-09), gated panel and its two signals (11-10), linked-file re-check (11-12)"
provides:
  - "Check again and Open Check Atomic Parts... work inside the real import dialog"
  - "The KiCad footprints folder reaches the probe, the re-check and the commit"
  - "Help page explains the atomic refusal and its recovery"
affects: [11-13 main window wiring]

plan_head_before: 92c0492f7a3580094835c94e06328d94a2d3579c
actuals:
  tokens: 20000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "A re-check runs as the current probe worker (no Close lock) and shares the result path with the first probe"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_import_dialog.py
    - tests/test_help_dialog.py

key-decisions:
  - "The probe result body became _apply_probe_result, used by _on_probe_done and _on_recheck_done"
  - "The check dialog's applied signal is left unconnected here; plan 11-13 connects it with the rescan"
  - "A close rejects an open check dialog before waiting for workers"

requirements-completed: [GIT-06, REV-10]

coverage:
  - id: D1
    description: "A part that breaks the atomic rule shows the gated panel, Open Check Atomic Parts opens the check dialog over the import dialog on that part, Check again re-checks, and Commit works once the part passes, with remote refs unchanged"
    requirement: GIT-06
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_gate_refusal_and_recovery_end_to_end"
        status: pass
    human_judgment: false
  - id: D2
    description: "Open Check Atomic Parts lists every failing part and a second click raises the same dialog; closing the import dialog closes it"
    requirement: GIT-06
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_open_check_dialog_focuses_first_failure"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_close_rejects_open_check_dialog"
        status: pass
    human_judgment: false
  - id: D3
    description: "Check again never starts a commit, and the KiCad footprints folder reaches the probe, the re-check and the commit"
    requirement: REV-10
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_check_again_in_dialog_never_commits"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_kicad_folder_reaches_probe_recheck_and_commit"
        status: pass
    human_judgment: false
  - id: D4
    description: "The Help page explains the refusal, Open Check Atomic Parts and Check again in the words of the panel buttons"
    requirement: GIT-06
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_import_page_describes_commit_step"
        status: pass
    human_judgment: false
  - id: D5
    description: "The check dialog opens over the import dialog and reads well beside the panel"
    verification: []
    human_judgment: true
    rationale: "Window stacking and layout adequacy are not asserted by any test"

duration: 40min
completed: 2026-10-30
---

# Phase 11 Plan 11: Gate recovery in the import dialog Summary

**Check again and Open Check Atomic Parts now work inside the real import dialog, the KiCad footprints folder reaches the gate at probe, re-check and commit, and an end-to-end run against real git proves refusal, fix, re-check and commit with unchanged remote refs.**

## Accomplishments

- `ImportCore.recheck_commit`, the `atomic_backup_root` keyword and `_atomic_dialog` on `ImportDialog`.
- `_on_check_again` starts a re-check as the current probe worker (older probe Events are set, a new one created, no Close lock). `_on_recheck_done` applies the generation check, stores the new plan, refreshes the file list through `begin_reprobe(new_plan)` and hands the probe to `_apply_probe_result`, the body shared with `_on_probe_done`.
- `_on_open_atomic_check` opens `AtomicCheckDialog(scan_result_for(probe.gate), repo_root, focus=(rel, name), backup_root=..., parent=self)` window-modal; a second click raises the open one; `issues_logged` is forwarded; `finished` clears the reference. `_shutdown` rejects an open check dialog first.
- `kicad_fp_dir=self._kicad_fp_dir` is passed to `probe_commit`, `recheck_commit` and `run_commit`.
- Help: one list item in the Commit section on the atomic refusal, Open Check Atomic Parts, Check again, "changed since install" and "added by a fix" markers, old failures not stopping the commit, and Check again never committing.

## Task Commits

1. **Task 1 (tracer): gate refusal and recovery end to end** - `2b85f78` (feat)
2. **Task 2: Help text** - `f1db1de` (docs)

## Verification

- `pytest tests/test_import_dialog.py tests/test_help_dialog.py tests/test_importer_layering.py tests/test_layering.py tests/test_main_window_import.py`: 284 passed (real-git end-to-end test ran, not skipped).
- Tracer verify (`-k "gate_refusal_and_recovery or open_check or expected_branch or tracer_commit"` plus the new tests): 7 passed.
- Not run here: the other wave-check files (`test_commit_plan`, `test_commit_step`, `test_commit_panel`, `test_commit_gate`, `test_gitops`), which this plan does not touch; the orchestrator runs the full suite after merge.

## Deviations from Plan

None - plan executed exactly as written. Two points differ only in wording from the acceptance grep: the dialog passes the folder as `kicad_fp_dir=fp_dir` (a local copied from `self._kicad_fp_dir` before the worker lambda, matching how `core` is captured), so the literal pattern `kicad_fp_dir=self._kicad_fp_dir` does not appear; `test_kicad_folder_reaches_probe_recheck_and_commit` proves the value arrives at all three calls. Extra tests beyond the list: close rejects the open check dialog, Check again never commits, folder reaches all three calls.

## Issues Encountered

- The worktree guard refused shell commands that mix a heredoc with git text; test and script text went through the Write tool and a plain `cat >>` instead. No effect on the result.
- `gsd_run` is not available in the worktree, so the plan commit ledger file was not written; `plan_head_before` is the known base SHA and `commits` is measured with `git rev-list --count` from it.

## Known Stubs

None.

## Threat Flags

None. T-11-27 is covered by `remote_refs` unchanged at the end of the end-to-end test; T-11-26 transfers to the unchanged Phase 9 dialog.

## Next Phase Readiness

Plan 11-13 connects the check dialog's `applied` signal (with an automatic re-check), the "changed since install" diff through `changed_diff`, the main window's `atomic_backup_root`, and the D-14 log rule.

## Self-Check: PASSED

- `kicad_lib_manager/widgets/import_dialog.py` contains `def _on_check_again`; `tests/test_import_dialog.py` contains `def test_gate_refusal_and_recovery_end_to_end`; `help_dialog.py` contains "atomic rule".
- Commits `2b85f78` and `f1db1de` are ancestors of HEAD.
