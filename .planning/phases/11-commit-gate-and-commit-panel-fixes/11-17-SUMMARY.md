---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 17
subsystem: ui
tags: [pyside6, commit-step, git, content-view, review-closure]

requires:
  - phase: 11-commit-gate-and-commit-panel-fixes
    provides: plans 11-14..11-16 (panel marks, gate, gitops fixes)
provides:
  - commit_step.combined_view (since-install plus before-this-import in one ContentText)
  - ImportDialog._begin_probe_generation (the only place older probe Events are set)
  - Check again that supersedes a running probe or check
  - all nine 11-REVIEW findings recorded as fixed (open: 0)
affects: [11-verification, verify-work]

actuals:
  tokens: 9000
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "One probe-generation helper shared by _start_probe and _on_check_again"
    - "Compose two existing ImportCore diff fields on one worker instead of adding a new field"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/commit_step.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_commit_step.py
    - tests/test_import_dialog.py
    - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-REVIEW-DISPOSITION.md

key-decisions:
  - "No new ImportCore field for the combined view: the dialog composes changed_diff and pre_import_diff, so existing test fakes keep working"
  - "Check again is refused only while a Switch to main or Commit git job runs; a running read-only probe is superseded"

requirements-completed: [GIT-06, REV-10]

duration: 55min
completed: 2026-10-30
status: complete
plan_head_before: 2a71f0d841fc1a6c8f82e49ea74de9645801ae82
plan_head_after: 0481381
---

# Phase 11 Plan 17: Combined change view, superseding Check again, review closed Summary

**A changed file that also held pre-import changes now opens one view with both diffs, Check again supersedes a running probe instead of being dropped, and all nine Phase 11 review findings are recorded fixed under a green 3094-test suite.**

## Performance

- **Duration:** about 55 min (the full suite took 17 min 13 s of that)
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- WR-02 (dialog part): `commit_step.combined_view` joins the "as installed vs now" and "HEAD vs before this import" views; `_on_commit_file_activated` builds both on one worker thread for a marked and dirty row, and still routes changed-only and dirty-only rows to a single view.
- IN-03: `_begin_probe_generation()` is the one place older probe Events are set; `_start_probe` and `_on_check_again` both call it. `_on_check_again` no longer returns while a probe runs (so the re-check that applied fixes request is never swallowed) and is still refused while a git job runs. Nothing starts `run_commit`.
- `11-REVIEW-DISPOSITION.md`: nine findings `fixed`, `open: 0`.
- Gate: `pytest -m "not wurth" -q -rs` gave 3094 passed, 33 skipped, exit 0.

## Task Commits

1. **Task 1: combined view (WR-02)** - RED `bb9c562` (test), GREEN `bcf6fd6` (feat)
2. **Task 2: superseding Check again (IN-03)** - RED `95dc359` (test), GREEN `a9863fc` (feat)
3. **Task 3: dispositions and full suite** - `0481381` (docs)

## TDD notes (RED evidence)
- Task 1 RED: `test_combined_view_holds_both_sections` failed with `AttributeError: ... has no attribute 'combined_view'`; `test_changed_and_dirty_file_opens_both_views` failed on the planned assertion (record held only `changed`, no `before`). The row-text assertion already passed, confirming plan 11-14's wording.
- Task 2 RED: `test_check_again_supersedes_running_probe` timed out waiting for `ready` because the request was dropped while a probe ran (the planned failure). `test_check_again_refused_while_committing` already passed at RED; it is a regression guard for T-11-34, not new behaviour.
- No REFACTOR commits.

## Files Created/Modified
- `kicad_lib_manager/importer/commit_step.py` - `combined_view`
- `kicad_lib_manager/widgets/import_dialog.py` - combined routing, `_begin_probe_generation`, superseding `_on_check_again`
- `tests/test_commit_step.py` - `test_combined_view_holds_both_sections`
- `tests/test_import_dialog.py` - `test_changed_and_dirty_file_opens_both_views`, `test_check_again_supersedes_running_probe`, `test_check_again_refused_while_committing`
- `.planning/phases/11-commit-gate-and-commit-panel-fixes/11-REVIEW-DISPOSITION.md` - nine findings fixed

## Decisions Made
See key-decisions above.

## Deviations from Plan

None in code. One environmental note on Task 3: the plan's foreground verdict command (the expected-skips filter) was not run as written, because the sandbox refused the long compound command. I read the same facts from the log by hand: last line `pytest exit 0`, summary `3094 passed, 33 skipped, 3 deselected`. All 33 skips are workstation or worktree skips: `Custom submodule not checked out` (this worktree has no `Custom/`), licence-restricted `downloaded_examples/*.zip not present` (gitignored samples, not in the worktree), two `symlinks not permitted here`, and the two `KICAD_*_UAT_DIR` opt-ins. The `Custom submodule not checked out` and `downloaded_examples ... not present` messages are not in the plan's literal expected-skips list, so the strict verdict command would list them; they come from running in an agent worktree. The live `Custom/` was not touched (the suite's session guard passed). The orchestrator may want to re-run the suite once in the main checkout if it needs the strict skip list satisfied.

**Total deviations:** 0 auto-fixed. **Impact:** none on code.

## Issues Encountered
- The tool sandbox rejected some compound shell commands; I split them or ran the suite through a small script in the scratchpad. No effect on results.
- The plan's commit ledger file (protocol 0c) was not created; `plan_head_before` was taken from the spawn base `2a71f0d`, and `commits: 5` is `git rev-list --count 2a71f0d..HEAD` before this SUMMARY commit.

## Known Stubs
None.

## Threat Flags
None. T-11-34 and T-11-35 are mitigated by the tests above.

## Next Phase Readiness
Phase 11 gap closure is complete in code and docs. Requirement checkboxes, the ROADMAP tick and STATE are left to the orchestrator. Human items 1 and 2 of 11-VERIFICATION.md (panel look, real PowerShell paste) remain for `/gsd-verify-work`.

## Self-Check: PASSED
- Commits `bb9c562`, `bcf6fd6`, `95dc359`, `a9863fc`, `0481381` are ancestors of HEAD.
- `def combined_view`, `def _begin_probe_generation` and the three new dialog tests are present; awk acceptance counts (1, 1, 0, 0) match.

---
*Phase: 11-commit-gate-and-commit-panel-fixes*
*Completed: 2026-10-30*
