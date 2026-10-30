---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 10
subsystem: ui
tags: [pyside6, commit-panel, atomic-gate, pytest-qt]

requires:
  - phase: 11-commit-gate-and-commit-panel-fixes
    provides: "gate result and text builders (11-02/05), notes and parent-only preview (11-03), gated probe fields (11-06, 11-08)"
provides:
  - "Gated state of the commit panel with per-part refusal lines and Commit disabled"
  - "Open Check Atomic Parts... and Check again buttons with open_check_requested and check_again_requested signals"
  - "Old-failure note, changed-since-install and added-by-a-fix file markers"
  - "Nothing-to-commit strip and the parent-only bump (Commit parent ref)"
affects: [11-11 dialog wiring]

actuals:
  tokens: 8000
  tasks: 3
  commits: 6
plan_head_before: 447234416164cea1d8a2776a7a46318711277ede
plan_head_after: 7dff98f

tech-stack:
  added: []
  patterns:
    - "Gate widgets are shown by _show_gate from the probe and hidden by _set_state for every other state"
    - "Row activation uses a per-probe set of activatable rels instead of probe.dirty_before alone"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/commit_panel.py
    - tests/test_commit_panel.py

key-decisions:
  - "Stale-only gated probes (no refused gate) show Check again but not Open Check Atomic Parts"
  - "A row that is both stale and noted added reads as changed (changed is checked first, as the plan orders it)"
  - "Old-failure lines stay visible in ready, gated and later states; only probing hides them"

requirements-completed: [GIT-06, REV-09, REV-10]

coverage:
  - id: D1
    description: "A gated probe lists each failing part and rule, capped at ten, with Commit disabled and the message and parent option editable"
    requirement: GIT-06
    verification:
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_gated_lists_failures_and_disables_commit"
        status: pass
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_gated_lines_capped"
        status: pass
    human_judgment: false
  - id: D2
    description: "Open Check Atomic Parts and Check again buttons emit their signals; Check again clears the pending refusal"
    requirement: REV-10
    verification:
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_gated_buttons_secondary_and_signals"
        status: pass
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_check_again_clears_pending_refusal"
        status: pass
    human_judgment: false
  - id: D3
    description: "Old failures show one amber line per library and never block Commit; changed and added files carry markers and open on double-click"
    requirement: REV-09
    verification:
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_old_failures_note_keeps_commit"
        status: pass
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_changed_and_added_markers"
        status: pass
    human_judgment: false
  - id: D4
    description: "Nothing to commit strip, Commit parent ref button with the parent-only preview, and a parent-only outcome ending in done"
    requirement: REV-10
    verification:
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_nothing_to_commit"
        status: pass
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_parent_only_bump_label_and_preview"
        status: pass
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_parent_only_outcome_done"
        status: pass
    human_judgment: false
  - id: D5
    description: "The wording and layout of the refusal block and buttons read well to the user"
    verification: []
    human_judgment: true
    rationale: "Visual layout and wording adequacy are not asserted by any test"

duration: 25min
completed: 2026-10-30
status: complete
---

# Phase 11 Plan 10: Commit Panel Gate Display Summary

**The commit panel now shows the atomic gate: a refused probe names each failing part and rule with Commit disabled, offers Open Check Atomic Parts and Check again, marks changed and added files, notes old failures, and handles the nothing-to-commit and parent-only cases.**

## Performance

- **Duration:** about 25 min
- **Tasks:** 3 (one tracer, two TDD)
- **Files modified:** 2 (`kicad_lib_manager/widgets/commit_panel.py`, `tests/test_commit_panel.py`)

## Accomplishments

- Gated state: strip "Commit refused: ...", one "Library / Part: rule" line per failure (ten shown, then "...and k more"), Commit disabled, message and parent option editable.
- Two secondary buttons (no style sheet, never default): Open Check Atomic Parts... emits `open_check_requested(rel_path, part)` of the first blocking failure; Check again emits `check_again_requested` and clears the pending refusal. Only Check again shows for stale-only probes.
- `_mark_files` replaces `_mark_dirty_files`: "(changed since install)" and "(added by a fix)" markers, amber, with plain-language tooltips, a hint line, and double-click activation for dirty, changed, stale and added rows.
- `_old_label` shows `old_notes` lines in ready and gated without touching Commit.
- D-14: "Nothing to commit: Custom already holds these files" strip; when the parent gitlink is behind and the parent box is ticked, Commit reads "Commit parent ref" and the preview is `parent_only_preview`. A parent-only outcome with a parent commit ends in "done" and `committed()` is True; one without a parent commit follows the non-committed path (probing, refusal kept).

## TDD Gate Compliance

- Task 1 (tracer): RED commit `3d8d30f` (7 of 8 new tests failed with AttributeError on the new widgets), GREEN `c59b192`.
- Task 2: RED `ca463d2` (4 failed on the planned marker and note assertions), GREEN `a650ee1`.
- Task 3: RED `194f3e2` (5 failed on the planned strip, label, preview and done-state assertions), GREEN `7dff98f`.
- Tests that already passed at RED time (`test_panel_gated_commit_never_emits`, `test_panel_plain_row_has_no_marker_and_does_not_activate`, `test_panel_parent_only_failure_reprobes`) pin existing behaviour that the new code must not break.

## Deviations from Plan

None - plan executed exactly as written. Extra tests were added beyond the plan's list (Commit never emits while gated, unchecked-library problems hide Open Check, Check again outside gated is a no-op, changed beats dirty-before, parent-only needs a message and an enabled parent, label reset after state change).

## Issues Encountered

- Python heredoc edits turned `"\n"` into a literal newline twice (syntax error on first run); fixed with the Edit tool. No functional impact.
- The test run uses the orchestrator interpreter (`env/` is absent in the worktree), as the environment notes direct.

## Known Stubs

None.

## Threat Flags

None. T-11-23 (Commit enabled while gated) is covered by `test_panel_gated_lists_failures_and_disables_commit` and `test_panel_gated_commit_never_emits`; T-11-24 (rich text) by `test_panel_gated_text_is_plain`.

## Next Phase Readiness

Plan 11-11 connects `check_again_requested` and `open_check_requested` in the dialog and re-probes whenever `committed()` is False after `show_outcome`.

## Self-Check: PASSED

- `kicad_lib_manager/widgets/commit_panel.py` and `tests/test_commit_panel.py` exist and are committed.
- Commits `3d8d30f`, `c59b192`, `ca463d2`, `a650ee1`, `194f3e2`, `7dff98f` exist on the worktree branch.
- `tests/test_commit_panel.py` and `tests/test_help_dialog.py`: 74 passed.
