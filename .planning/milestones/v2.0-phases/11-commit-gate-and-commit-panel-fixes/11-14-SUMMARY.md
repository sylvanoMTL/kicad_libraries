---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 14
subsystem: ui
tags: [pyside6, commit-panel, gap-closure, qt]

requires:
  - phase: 11-commit-gate-and-commit-panel-fixes
    provides: commit panel, atomic gate, re-probe after a refused commit
provides:
  - git output and the manual command kept across the automatic re-probe
  - combined row marks for changed or added files that were also dirty before the import
  - "added: linked by a committed part" mark and matching Help text
  - own gate-line cap constant, first_failure for Open Check, dead state removed
affects: [11-15, 11-17]

actuals:
  tokens: 14000
  tasks: 3
  commits: 6
plan_head_before: d851ab8ffd04e8f1f236844d89a6f63c6b2de226
plan_head_after: 0f09fb98ffcd77a447381a710d3f0c30ec691d5d

tech-stack:
  added: []
  patterns:
    - "Pending refusal state (issues, output lines, manual command) stored and dropped together by _drop_pending, shown by _show_pending"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/commit_panel.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_commit_panel.py
    - tests/test_help_dialog.py
    - tests/test_import_dialog.py

key-decisions:
  - "The kept refusal detail is display state only; Commit still follows the fresh probe"
  - "Marks are bare-word constants; the row adds the parentheses and joins several marks with '; '"

requirements-completed: [REV-10, GIT-06, UI-02]

coverage:
  - id: D1
    description: "After a refused or failed commit the panel keeps git's output and the 'Finish it by hand' command through the automatic re-probe, in the running dialog"
    requirement: REV-10
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_hook_rejection_output_survives_reprobe_in_dialog"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_parent_only_failure_reprobes_in_dialog"
        status: pass
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_failure_detail_survives_reprobe"
        status: pass
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_failure_detail_dropped"
        status: pass
    human_judgment: false
  - id: D2
    description: "A changed or added file that also had changes before the import shows both marks, a combined tooltip and both hints, and stays double-clickable"
    requirement: UI-02
    verification:
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_changed_or_added_and_dirty_before_combined"
        status: pass
    human_judgment: false
  - id: D3
    description: "Added files read '(added: linked by a committed part)' in the file list and on the Help page"
    requirement: UI-02
    verification:
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_changed_and_added_markers"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_import_page_describes_commit_step"
        status: pass
    human_judgment: false
  - id: D4
    description: "Open Check Atomic Parts opens GateResult.first_failure; gate refusal lines have their own cap constant; dead state tuple and unused local removed"
    requirement: GIT-06
    verification:
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_open_check_uses_first_failure"
        status: pass
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_gate_cap_is_its_own_constant"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-30
status: complete
---

# Phase 11 Plan 14: Commit panel gap closure Summary

**The commit panel now keeps git's output and the pasteable manual command through the automatic re-probe, shows combined marks for changed or added files with pre-import changes, and uses the new "added: linked by a committed part" wording.**

## Performance

- **Duration:** 25 min
- **Tasks:** 3
- **Files modified:** 5 (2 source, 3 test)

## Accomplishments

- WR-01 closed: `show_outcome` stores the refusal, the output-box lines and the manual-command text together; `begin_reprobe` and `apply_probe` show them again via `_show_pending`, and `_drop_pending` clears all three at the next Commit, Check again or Switch click, a new plan, a committed outcome, or a probe that is itself refused or unavailable. Commit stays governed by the fresh probe.
- WR-02 (panel part): a changed or added row that is also in `dirty_before` reads `(<mark>; also changed before this import)`, has the combined tooltip, turns on both hints and stays activatable.
- IN-05: added files carry `_ADDED_MARK = "added: linked by a committed part"`; the Help page and its test use the panel's own constants.
- IN-01 (panel part) and IN-04: removed the unused `_STATES` tuple and the unused `ready` local, fixed the `_WARNING_NOISE` spacing, Open Check uses `GateResult.first_failure`, gate refusal lines are capped by `_GATE_LINES_SHOWN`.

## TDD Record

- **RED (Task 1):** both dialog tests (`test_parent_only_failure_reprobes_in_dialog` strengthened, `test_hook_rejection_output_survives_reprobe_in_dialog`) failed on the output-box assertion (`assert [] == ['hook says: no', 'fix the footer first']`), the verifier's offscreen reproduction. Semantic assessment: the target tests ran and failed on the planned assertion because the box was empty after the second probe. Commit d804f79.
- **GREEN (Task 1):** 47d02ff, 6 `-k reprobe/hook_rejection_output` tests pass.
- **Task 2:** `test_panel_changed_or_added_and_dirty_before_combined` and the updated `test_panel_changed_and_added_markers` failed on the row text before the change (ddca9b8 fixes it). The failure-detail panel tests were written after Task 1's fix and pass; they guard the behavior Task 1 introduced (cb16700).
- **Task 3:** `test_panel_gate_cap_is_its_own_constant` failed (no `_GATE_LINES_SHOWN`) and the Help test failed on the new wording before 0f09fb9. `test_panel_open_check_uses_first_failure` passes on both old and new code because `blocking[0]` equals `first_failure` when blocking is non-empty; it pins the contract.

## Task Commits

1. **Task 1: git output and manual command survive the re-probe** - `d804f79` (test), `47d02ff` (feat)
2. **Task 2: kept-detail tests, combined marks, new added mark** - `cb16700` (test), `ddca9b8` (feat)
3. **Task 3: dead code, first_failure, gate cap, Help wording** - `9b33d40` (test), `0f09fb9` (fix)

## Files Created/Modified

- `kicad_lib_manager/widgets/commit_panel.py` - pending output and manual command, `_show_pending`/`_drop_pending`, combined marks, `_GATE_LINES_SHOWN`, `first_failure`, dead code removed
- `kicad_lib_manager/widgets/help_dialog.py` - Commit section names the new added mark
- `tests/test_commit_panel.py` - failure-detail, combined-mark, gate-cap and Open Check tests
- `tests/test_help_dialog.py` - Help page checked against `_CHANGED_MARK` and `_ADDED_MARK`
- `tests/test_import_dialog.py` - dialog-level WR-01 tests

## Decisions Made

None beyond the plan; `import_dialog.py` is unchanged (`git diff` against the base is empty).

## Deviations from Plan

None - plan executed exactly as written. The plan's second `<automated>` command for Task 3 (`-k "gate_refusal or changed_file or open_check"`) was run together with `reprobe` and `hook_rejection`: 10 passed.

## Issues Encountered

None. The full suite was not run (plan 11-17 owns the single full run); targeted runs: `tests/test_commit_panel.py` + `tests/test_help_dialog.py` 82 passed; `tests/test_import_dialog.py -k "gate_refusal or changed_file or open_check or reprobe or hook_rejection"` 10 passed.

## Known Stubs

None.

## Threat Flags

None. T-11-28 and T-11-29 mitigations hold: the kept lines go through `_set_output` and the plain-text manual label only, and `test_panel_failure_detail_survives_reprobe` asserts Commit stays disabled while probing.

## Next Phase Readiness

Ready for 11-15 and 11-17 (double-click routing and the full suite run).

## Self-Check: PASSED

- All five modified files exist; commits d804f79, 47d02ff, cb16700, ddca9b8, 9b33d40, 0f09fb9 are ancestors of HEAD.
- Acceptance greps: `_STATES` 0, `ready = state == "ready"` 0, `"by a fix"` 0 in both source files, `_GATE_LINES_SHOWN = 10` present, `first_failure` used in `_on_open_check_clicked`.
