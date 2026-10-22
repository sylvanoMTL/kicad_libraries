---
phase: 06-git-commit-step
plan: 08
subsystem: ui
tags: [pyside6, qthread, git-commit-step, import-dialog, close-guard, qscrollarea, wr-04]

requires:
  - phase: 06-git-commit-step
    provides: "CommitPanel signals and states (06-03), commit_step.switch_to_main / run_commit(expected_branch) / pre_import_diff (06-01, 06-07), main-window close guard and Commit help page (06-06)"
provides:
  - "ImportDialog drives the whole commit step: switch to main with a re-probe, Close lock while any git job runs, the single D-02 'Not committed' line, the D-09 diff on an amber file"
  - "Result view body scrolls inside a QScrollArea with Close outside it"
  - "WR-04 fixed (install worker uses the plan captured at the click; open_path refuses under a running install or git job)"
affects: [06-verification, phase-6-uat]

requirements-completed: [GIT-01, GIT-02, GIT-03, GIT-04, GIT-05]

actuals:
  tokens: 9000
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "One _set_git_worker() owns the git-job slot and the Close button state; every probe, switch and commit worker goes through it"
    - "A worker lambda binds its inputs as default arguments (p=plan) and never reads dialog attributes from its thread"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/widgets/import_result.py
    - tests/test_import_dialog.py
    - .planning/phases/05-import-ui-and-post-install/05-REVIEW-DISPOSITION.md

key-decisions:
  - "After a successful switch the whole probe runs again (_start_probe calls show_plan, so the file list and default message are rebuilt too)"
  - "The D-02 line is logged from both done() and closeEvent(), guarded by one flag, so every close path logs it exactly once and none asks a question"
  - "Close regains focus after git goes idle only when it held the focus when it was disabled"
  - "The 'no git before install' test flags the end of apply_plan, not the installed signal: the probe worker starts inside _show_result, a moment before installed is emitted"
  - "WR-04 disposition carries a note: key in the YAML entry and a Notes section; the table row only changes its Disposition cell"

patterns-established:
  - "Dialog-level commit tests use fakes through make_install_dialog(**changes) with gated fakes from the gates fixture"

coverage:
  - id: D1
    description: "Switch to main runs on a worker, logs 'Switched Custom to main', then probes again so the panel shows the new branch; a refusal returns to the offer with git's reason and nothing is committed"
    requirement: GIT-03
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_commit_switch_flow"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_commit_switch_failure_shows_reason"
        status: pass
    human_judgment: false
  - id: D2
    description: "Close is disabled and done/reject/Esc/closeEvent are ignored while a probe, switch or commit runs; a second Commit request is dropped; the main window refuses too through is_committing()"
    requirement: GIT-01
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_commit_close_button_disabled_while_git_runs"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_commit_close_refused_while_git_runs"
        status: pass
    human_judgment: false
  - id: D3
    description: "Commit passes the message as typed, the checkbox state and the probed branch as expected_branch; step texts reach the panel; an unavailable probe is logged once without touching the install result"
    requirement: GIT-02
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_commit_passes_expected_branch"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_commit_step_texts_shown"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_commit_unavailable_logged_once"
        status: pass
    human_judgment: false
  - id: D4
    description: "Closing the Result view without a Custom commit logs exactly one WARNING 'Not committed - commit manually...' and opens no message box; after a commit nothing is logged; no commit step for a no-op plan"
    requirement: GIT-04
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_commit_not_committed_logged_on_close"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_commit_not_logged_after_a_commit"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_no_commit_step_for_noop_plan"
        status: pass
    human_judgment: false
  - id: D5
    description: "Double-clicking an amber file opens the 'HEAD vs before this import' view built on a worker thread"
    requirement: GIT-01
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_dirty_file_double_click_opens_diff"
        status: pass
    human_judgment: false
  - id: D6
    description: "Git changes nothing before an explicit click: with real git only read-only subcommands run between the install and the Commit click, add and commit run after it, push never"
    requirement: GIT-05
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_git_state_changes_only_after_click"
        status: pass
    human_judgment: false
  - id: D7
    description: "The Result view scrolls vertically inside a QScrollArea (no horizontal bar) and Close stays outside it at the 900x600 minimum size"
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_result_view_scrolls_at_minimum_size"
        status: pass
    human_judgment: true
    rationale: "Offscreen Qt has no fonts, so the layout was checked structurally; spacing and the look of the scroll bar need a real display (owner UAT)"
  - id: D8
    description: "WR-04: the install worker receives the plan captured at the click and never reads self._plan from its thread; open_path does nothing while an install or git job runs"
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_install_worker_uses_captured_plan"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_open_path_refused_while_busy"
        status: pass
    human_judgment: false
  - id: D9
    description: "Owner UAT on the real Custom/: the commit holds only the imported files, the parent commit only the Custom ref, every remote unchanged"
    requirement: GIT-02
    verification: []
    human_judgment: true
    rationale: "It writes real commits into the owner's repos with their git configuration, hooks and a live remote; it is a human action and was not performed"

duration: 17min
completed: 2026-10-22
status: complete
plan_head_before: 8f4141c1a3cf0d777fbf2822cb20759e4bfd9e60
plan_head_after: cb30b7051cf3def25db8974d1023e9a113754f71
commits: 4
---

# Phase 6 Plan 08: Wire the Commit Step into the Import Dialog Summary

**The Import dialog now runs the Switch-to-main round trip with a re-probe, locks Close while any git job runs, logs one "Not committed" line when the user simply closes, opens the pre-import diff on an amber file, and keeps git read-only until the Commit click; the Result view scrolls so the panel fits at 900x600, and WR-04 is fixed.**

## Performance

- **Duration:** 17 min
- **Started:** 2026-10-22T21:35:23Z
- **Completed:** 2026-10-22T21:52Z
- **Tasks:** 2 (both TDD: RED then GREEN); the Task 2 owner UAT is pending
- **Files modified:** 4 (no new files)

## Accomplishments

- `import_dialog.py`: `ImportCore` gained `switch_to_main` and `pre_import_diff`. `_set_git_worker()` is the one place that records the running git job and enables or disables the Result view's Close button (focus is given back to Close when it held it). `_start_probe()` is shared by the first probe and the re-probe after a switch. `_on_switch_requested()` runs `core.switch_to_main` on a worker, logs its issues, then probes again on success or returns the panel to the offer with git's reason on refusal. `_on_commit_file_activated()` shows the D-09 diff through `_run_content`. `_on_commit_requested()` still passes the message untouched plus the probed branch as `expected_branch`, and drops a request while a worker runs.
- D-02: `_log_not_committed()` emits one WARNING (`commit.not_committed`) from `done()` and `closeEvent()` when a panel was shown and no Custom commit was made. It asks nothing.
- `import_result.py`: the banner down to the commit slot sits in a `QScrollArea` (`widgetResizable`, horizontal bar off, no frame); Close is below it. Every attribute name Phase 5 tests read is unchanged.
- WR-04: the install lambda binds `p=plan`; `open_path` also returns while `is_installing()` or `is_committing()`. `05-REVIEW-DISPOSITION.md` shows WR-04 as `fixed` with the plan 06-08 note.
- Full suite without the `kicad_cli` marker: 1802 passed, 5 skipped (an env-var UAT scratch test, a symlink-privilege test and three Wurth-submodule tests, none from this phase), 0 failed.

## Task Commits

1. **Task 1 RED:** `ede8611` (test) - 11 dialog tests; 6 fail (switch flow, switch failure, Close lock, D-02 line, D-09 diff, scrolling), 5 pass already because plan 06-01 covered them
2. **Task 1 GREEN:** `8703a16` (feat) - dialog wiring and the scrolling Result view
3. **Task 2 RED:** `cac567c` (test) - both WR-04 tests fail
4. **Task 2 GREEN:** `cb30b70` (fix) - WR-04 code, the test split below and the disposition update

**Plan metadata:** committed with this SUMMARY (docs). STATE.md and ROADMAP.md are left to the orchestrator.

## Files Created/Modified

- `kicad_lib_manager/widgets/import_dialog.py` - switch and diff seams, `_set_git_worker`, `_start_probe`, D-02 line, WR-04 fixes
- `kicad_lib_manager/widgets/import_result.py` - scrolling body with Close outside it
- `tests/test_import_dialog.py` - 14 new tests (the parametrized open_path test counts as two cases)
- `.planning/phases/05-import-ui-and-post-install/05-REVIEW-DISPOSITION.md` - WR-04 fixed

## TDD Gate Compliance

- **Task 1 RED (`ede8611`):** run against the unchanged dialog, 6 of the 11 target tests failed on planned gaps: `TypeError: ImportCore.__init__() got an unexpected keyword argument 'switch_to_main'` / `'pre_import_diff'` (3 tests; a load-level failure, not an assertion), `assert not True` for the enabled Close button, the empty list where the D-02 WARNING was expected, and "not enough values to unpack" for the missing `QScrollArea`. The other 5 (`unavailable_logged_once`, `passes_expected_branch`, `step_texts_shown`, `not_logged_after_a_commit`, `no_commit_step_for_noop_plan`) and `git_state_changes_only_after_click` passed already because plan 06-01 implemented that behaviour; they stay as regression tests. `gsd_run check tdd-red-evidence` was not run (pytest has no supported report format); the semantic assessment is manual, as in plans 06-01, 06-03 and 06-07.
- **Task 1 GREEN (`8703a16`):** all 19 target tests pass, 229 pass across the dialog, panel, help, main-window and layering files.
- **Task 2 RED (`cac567c`):** `assert <TaskWorker> is None` (open_path started a worker under a running commit) and `assert ['Dummy-1'] == []` (the install lambda read `self._plan` on a worker thread). Both are the planned assertions.
- **Task 2 GREEN (`cb30b70`):** all pass. No REFACTOR commits.

## Decisions Made

- The re-probe calls `show_plan`, so the file list and default message are rebuilt after a switch. This loses nothing: the message is read-only until the panel is ready.
- The D-02 line is also emitted from `closeEvent`, not only `done()`, so a close path that never reaches `done()` still logs it once.
- The Close focus is restored only if Close held it when disabled, so a user who moved to another widget is not pulled back.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The first version of test_open_path_refused_while_busy tested nothing in its second half**
- **Found during:** Task 2 (GREEN verification)
- **Issue:** the test did a commit job and an install job in one test on the same layout. After the first install the second dialog's plan was a no-op, so Install stayed disabled and the wait timed out.
- **Fix:** the test is parametrized over `commit` and `install`, each with its own layout. The `-k open_path_refused` selection still finds both.
- **Files modified:** tests/test_import_dialog.py
- **Verification:** both cases pass, and both failed against the unfixed `open_path` before the fix
- **Committed in:** cb30b70

**2. [Rule 1 - Bug] "Flag on the installed signal" is racy for the click-gated git test**
- **Found during:** Task 1 (writing the test)
- **Issue:** the plan says a slot on `installed` sets the flag, but the probe worker starts inside `_show_result`, before `installed` is emitted. The probe's first git call can therefore run before the slot, which would make the test flaky.
- **Fix:** the flag is set at the end of the real `apply_plan` (a wrapper in the test), which is the actual "install finished" point. Everything recorded before it must be empty.
- **Files modified:** tests/test_import_dialog.py
- **Committed in:** ede8611

---

**Total deviations:** 2 auto-fixed (2 bug, both in test design)
**Impact on plan:** none on behaviour; the dialog code matches the plan.

## Issues Encountered

- **Help page versus wired behaviour (plan 06-06 asked for this check).** The D-02 text ("the files stay uncommitted and the log says so"), the Close/main-window lock, Switch to main, amber double-click and "never pushed" all match the dialog. One wording mismatch: the page says "Any other detached HEAD is refused, and so is a local main that is behind origin/main", while `commit_step` (line 119) refuses a *detached* HEAD when local main is behind origin/main; a named branch that is behind is not refused. The help file belongs to plan 06-06 and this plan was told not to change it, so it is left as is. A one-clause fix would be "and so is a detached HEAD when local main is behind origin/main".
- The probe worker starts a moment before the `installed` signal is emitted (inside `_show_result`). It is read-only and runs after `apply_plan` returned, so the "no git before the install finishes" rule holds, but the literal "before installed" is not strictly true.
- Pending human verification: see below.

## Pending Human Verification (Owner UAT, not performed)

The task's `<human-check>` writes real commits into the owner's repos and is a human action. The GUI was not launched and no import, commit or switch was done in `Custom` or the parent. To run it: start `.\env\Scripts\python.exe kicad_lib_manager.py`, File > Import Part..., open `downloaded_examples/ul_CSD85301Q2.zip`, pick a library and Install, then check the Commit step (branch main; parent repo and branch; "Files to commit (3)"; message "Add CSD85301Q2 to ..." with Import-Vendor/Package/Date; parent box ticked; "Parent bump also includes 2 earlier Custom commits" listing 49f746c and d3ff246 while the parent gitlink is 485d530), edit the subject, click Commit, and compare `git -C Custom log -1 --stat`, `git log -1 --stat`, `git -C Custom rev-list --count @{u}..HEAD` (1) and `git -C Custom ls-remote origin refs/heads/main` against `origin/main`. Then close a second import without committing and look for the "Not committed" line once. Also confirm by eye that the Result view scrolls cleanly at 900x600. UAT commit hashes and whether they are kept: none yet (to be filled in by the owner). Push Custom before removing this worktree (STATE.md).

## Known Stubs

None.

## Threat Flags

None. T-06-20 (Close lock) is covered by `test_commit_close_button_disabled_while_git_runs`, T-06-21 (no git write without a click) by `test_git_state_changes_only_after_click`, T-06-22 (WR-04) by `test_install_worker_uses_captured_plan` and `test_open_path_refused_while_busy`, T-06-23 by `test_commit_unavailable_logged_once` and `test_commit_not_committed_logged_on_close`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All eight Phase 6 plans are in; what remains is the owner UAT above and `/gsd-verify-work`.
- WR-05 (GUI thread waiting on kicad-cli) stays open, as planned.
- The owner's uncommitted changes (`.planning/config.json`, the `Custom` gitlink, `.planning/milestone.lock`, `.planning/state.json`, `reports/`, `research_notes/`, `uv.lock`) are untouched. `git status --porcelain Custom` still shows the owner's own ` M Custom` (49f746c/d3ff246), unchanged by the test runs. The 7 known real-kicad-cli failures are unchanged (`-m kicad_cli`: 7 failed, 8 passed).

## Self-Check: PASSED

- Modified files exist: import_dialog.py, import_result.py, test_import_dialog.py, 05-REVIEW-DISPOSITION.md
- Commits `ede8611`, `8703a16`, `cac567c`, `cb30b70` are ancestors of HEAD
- Acceptance greps match (`switch_to_main: Callable`, `pre_import_diff: Callable`, `def _start_probe(`, `def _on_switch_requested(`, `def _set_git_worker(`, `switch_requested.connect(`, `file_activated.connect(`, the D-02 text, `commit.not_committed`, `expected_branch=`, `QScrollArea`, `ScrollBarAlwaysOff`, `p=plan`, `self.is_installing() or self.is_committing()`); all 13 named tests exist and pass

---
*Phase: 06-git-commit-step*
*Completed: 2026-10-22*
