---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 04
subsystem: ui
tags: [pyside6, commit-panel, theme, state-machine]
requires:
  - phase: 06-git-commit-step
    provides: CommitPanel, CommitProbe, CommitOutcome
provides:
  - "CommitPanel.begin_reprobe and pending refusal (panel side of REV-10)"
  - "Parent checkbox choice kept across probes (REV-11 / IN-01)"
  - "Primary Commit button, tinted outcome strip, 'Committed in Custom only' label, theme sizes (UI-02)"
affects: [11-09, 11-10, 11-11]
tech-stack:
  added: []
  patterns: ["object-name QSS selector so a tinted QFrame leaves child labels unstyled", "pending refusal re-rendered by the next probe"]
key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/commit_panel.py
    - tests/test_commit_panel.py
key-decisions:
  - "A non-committed outcome goes to 'probing' (Commit disabled) instead of 'ready'; only apply_probe can re-enable Commit"
  - "Parent choice is remembered in _parent_wanted; a probe with parent_ok=False unticks the box but keeps the choice"
requirements-completed: [REV-10, REV-11, UI-02]
status: complete
duration: 40 min
completed: 2026-10-30
actuals:
  tokens: 14000
  tasks: 2
  commits: 3
plan_head_before: 74718e640c9693b992064bfb5b218a5048d94360
plan_head_after: f65d2c23f33125513aaf39aac80621337103c6e9
commits: 3
coverage:
  - deliverable: "Refusal moves the panel to probing, keeps message, parent choice and refusal text"
    verification:
      - {kind: test, ref: "tests/test_commit_panel.py#test_panel_refusal_waits_for_reprobe", status: pass}
      - {kind: test, ref: "tests/test_commit_panel.py#test_panel_reprobe_keeps_refusal_message_and_parent_choice", status: pass}
      - {kind: test, ref: "tests/test_commit_panel.py#test_panel_own_refusal_replaces_pending", status: pass}
    human_judgment: false
  - deliverable: "Parent checkbox choice kept across probes"
    verification:
      - {kind: test, ref: "tests/test_commit_panel.py#test_panel_parent_choice_kept_across_probes", status: pass}
    human_judgment: false
  - deliverable: "Primary Commit button, tinted outcome strip, partial label, theme sizes"
    verification:
      - {kind: test, ref: "tests/test_commit_panel.py#test_panel_commit_button_primary", status: pass}
      - {kind: test, ref: "tests/test_commit_panel.py#test_panel_outcome_tint_error", status: pass}
      - {kind: test, ref: "tests/test_commit_panel.py#test_panel_failed_label_custom_only", status: pass}
      - {kind: test, ref: "tests/test_commit_panel.py#test_panel_sizes_on_theme_scale", status: pass}
    human_judgment: false
  - deliverable: "In a real run the panel looks like the rest of the app"
    verification: []
    human_judgment: true
    rationale: "Visual match to the theme is a judgment no test asserts; covered by the end-of-phase manual check"
---

# Phase 11 Plan 04: Commit panel refusal, parent choice and theme Summary

**CommitPanel now waits for a fresh probe after a refusal (keeping message, parent choice and refusal text), remembers the user's parent checkbox choice, and uses the primary button, a tinted outcome strip and theme sizes.**

## Accomplishments

- REV-10 (panel side): a non-committed outcome moves the panel to `probing` with Commit disabled, stores the issues in `_pending_refusal` and re-renders them on top of the next probe. A probe that is itself `refused` or `unavailable` replaces them; a Commit or Switch click clears them. `begin_reprobe(cplan=None)` re-enters probing without touching message, parent choice or refusal (plans 11-09 and 11-11 call it).
- REV-11 / IN-01: the parent box is ticked on the first probe after `show_plan` only. `_parent_wanted` holds the choice; a probe that disables the box unticks it and the choice returns when a later probe enables it.
- UI-02: Commit carries `PRIMARY_BUTTON_QSS`; outcome lines sit in one `QFrame#outcomeStrip` tinted by the strongest line (ERROR_TINT, AMBER_TINT, SUCCESS_TINT); the partial result button reads "Committed in Custom only"; progress bar and empty file row use `theme.SP_*`.

## Task Commits

1. Task 1 (tracer): `967b01c` feat(11-04) refusal waits for a fresh probe, parent choice kept
2. Task 2 RED: `f2facac` test(11-04) failing tests for primary Commit, tint, label, sizes
3. Task 2 GREEN: `f65d2c2` feat(11-04) primary Commit, tinted strip, label, theme sizes

## TDD Gate Compliance

Task 2 (`tdd="true"`): RED commit `f2facac` failed on the target tests (missing `_outcome_frame`, stylesheet, label and size assertions; 9 failed, 28 passed), then GREEN `f65d2c2` passed. No REFACTOR commit was needed. Task 1 was a tracer and was committed with its tests.

## Verification

- `pytest tests/test_commit_panel.py tests/test_help_dialog.py -q`: 51 passed.
- Wave check (without `tests/test_commit_gate.py`, which does not exist yet, it belongs to a sibling plan): 188 passed.
- `tests/test_import_dialog.py`: 181 passed (the dialog still works with the panel change).
- Acceptance greps found `begin_reprobe`, `_pending_refusal`, `_parent_wanted`, `PRIMARY_BUTTON_QSS`, `outcomeStrip`, `SP_XL * 8`, "Committed in Custom only"; `test_panel_refusal_returns_to_ready` is gone.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Test pin] Existing progress-bar test pinned the old pixel size**
- **Found during:** Task 2
- **Issue:** `test_panel_committing_locks_inputs` asserted `QSize(240, 16)`; the plan's theme-scale size is `SP_XL * 8` by `SP_MD` (256 x 16).
- **Fix:** Test now asserts `QSize(theme.SP_XL * 8, theme.SP_MD)`.
- **Files modified:** tests/test_commit_panel.py
- **Commit:** f2facac

**2. [Environment] Wave check command lists `tests/test_commit_gate.py`**
- The file does not exist in this worktree (created by another plan); the wave check was run without it.

**Total deviations:** 1 auto-fixed (test pin), 1 environment note. **Impact:** none on behaviour.

## Known Stubs

None.

## Threat Flags

None. T-11-08 mitigated (non-committed outcome never leaves Commit enabled; `test_panel_refusal_waits_for_reprobe`). T-11-09 kept: outcome lines are still plain-text labels; the frame only changes the background.

## Next Phase Readiness

Plans 11-09 (dialog calls `begin_reprobe` after a refusal) and 11-10 (gated state, Check again) can build on `begin_reprobe` and `_pending_refusal`. The dialog does not yet start a fresh probe after a refusal, so until 11-09 lands a refused commit leaves the panel in "probing".

## Self-Check: PASSED

- FOUND: kicad_lib_manager/widgets/commit_panel.py, tests/test_commit_panel.py
- FOUND commits: 967b01c, f2facac, f65d2c2
