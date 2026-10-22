---
phase: 06-git-commit-step
plan: 01
subsystem: git-commit-step
tags: [git, subprocess, pyside6, qthread, submodule, commit-only, tracer]

requires:
  - phase: 05-import-ui-and-post-install
    provides: "ImportResultView.commit_slot, ImportDialog TaskWorker/_spawn, InstallResult/InstallPlan"
provides:
  - "gitops.run_git: the only place a git process starts (allow-list, literal pathspecs, scrubbed GIT_* env)"
  - "CommitPlan, CommitProbe, CommitOutcome field sets and CommitPanel signals/methods that plans 06-02..06-08 build on"
  - "Result view commit step: probe worker, Commit worker, close guards, parent gitlink bump, 'Not pushed' counts"
  - "tests/gitfixtures.py: throwaway superproject + Custom submodule + bare remotes, remote_refs snapshot"
affects: [06-02, 06-03, 06-04, 06-05, 06-06, 06-07, 06-08]

actuals:
  tokens: 16900
  tasks: 1
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Single subprocess choke point with a frozen subcommand allow-list and an injectable runner"
    - "add -N for new files, then commit --only -F <tempfile> --pathspec-from-file=- --pathspec-file-nul"
    - "Qt-free orchestration (commit_step) returning frozen dataclasses with Issues; panel owns layout/state only"

key-files:
  created:
    - kicad_lib_manager/gitops.py
    - kicad_lib_manager/importer/commit_plan.py
    - kicad_lib_manager/importer/commit_step.py
    - kicad_lib_manager/widgets/commit_panel.py
    - tests/gitfixtures.py
  modified:
    - kicad_lib_manager/widgets/import_result.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_import_dialog.py
    - tests/test_importer_layering.py

key-decisions:
  - "Every git call goes through gitops.run_git; ALLOWED_SUBCOMMANDS holds no remote subcommand and a disallowed one raises ValueError before any process starts"
  - "The parent message is built inside the commit job after the Custom commit exists; the panel never shows a final parent text"
  - "A failed parent commit keeps the Custom commit and reports the manual command (D-03); nothing is retried"
  - "The probe worker also blocks Close (one rule for every git job)"
  - "The default git fixture is built once per session and copied (about 5 s to build, 0.8 s to copy)"

patterns-established:
  - "Phase 6 Issue codes start with commit. or git., never import."
  - "Phase 5 tests use no_git_probe / no_git_commit fakes by default so only the tracer starts git"

requirements-completed: [GIT-01, GIT-02, GIT-05]

coverage:
  - id: D1
    description: "After a successful install the Result view's commit slot holds a CommitPanel with branch, parent, exact file list, D-18 message with Import-* trailers, parent checkbox and Commit"
    requirement: GIT-01
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_tracer_commit_end_to_end"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_commit_slot_holds_panel_after_install"
        status: pass
    human_judgment: false
  - id: D2
    description: "Commit makes one path-limited Custom commit with exactly the three installed files, then a parent commit touching only the Custom gitlink, and no remote ref changes"
    requirement: GIT-02
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_tracer_commit_end_to_end"
        status: pass
    human_judgment: false
  - id: D3
    description: "No code path of the commit step reaches a remote: run_git allow-list, scrubbed environment, remote refs unchanged after a full commit"
    requirement: GIT-05
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_tracer_commit_end_to_end"
        status: pass
    human_judgment: false
  - id: D4
    description: "The dialog cannot be closed (done, reject, Esc, closeEvent) while the probe or commit worker runs; a failed or empty install shows no commit step"
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_commit_close_refused_while_git_runs"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_no_commit_step_after_failed_or_empty_install"
        status: pass
    human_judgment: false
  - id: D5
    description: "The panel reads well and fits the Result view at the dialog's minimum size (offscreen rendering has no fonts, so layout was only checked structurally)"
    verification: []
    human_judgment: true
    rationale: "Visual fit and spacing need a real display; plan 06-03 owns the full panel visuals"

duration: 18min
completed: 2026-10-22
status: complete
plan_head_before: ec3bb43b993c91ff8e50cc0fab91a424f36920e9
plan_head_after: 8086006f32392fa947a1c8276f379318ec982535
---

# Phase 6 Plan 01: Git Commit Step Tracer Summary

**After a successful import the Result view shows a CommitPanel; one click makes a path-limited `commit --only` of exactly the installed files in Custom, then a parent commit of only the Custom gitlink, all through one allow-listed `run_git`, with nothing pushed.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-10-22T17:45:15Z
- **Completed:** 2026-10-22T18:03Z
- **Tasks:** 1 (tracer, TDD: RED then GREEN)
- **Files modified:** 9 (5 new, 4 edited)

## Accomplishments

- `gitops.py` is the only module that starts git: argv `[git, --literal-pathspecs, -c, core.quotepath=false, -C, repo, subcommand, ...]`, no shell, every `GIT_*` variable removed, `GIT_TERMINAL_PROMPT=0` and `GIT_OPTIONAL_LOCKS=0`, `CREATE_NO_WINDOW` on Windows, 17-entry `ALLOWED_SUBCOMMANDS` with no remote subcommand, `find_git` refusing a git inside the repo.
- `commit_plan.py` (pure) maps `InstallResult.touched` to `CommitFile`s (folders skipped, unknown or outside-Custom paths become ERROR issues, expected sha256 from `op.data` or `op.source.sha256`) and builds the D-18 default message, parent message and parent preview.
- `commit_step.py` probes Custom and the parent (toplevel check, branch, detached refusal, parent gitlink) and runs the commit: `add -N` for untracked files, `commit --only -F <tempfile>` with NUL pathspecs on stdin, unstage on failure, parent `commit --only -- Custom` with the message built after the Custom commit, "Not pushed" counts from the local upstream ref.
- `CommitPanel` and the slot container: commit slot opens to the panel after a successful, non-empty install and stays hidden at height 0 otherwise; the dialog runs probe and commit on a `TaskWorker`, and `done`, Esc and `closeEvent` refuse while a git worker runs.
- The tracer test builds a real superproject and proves: Custom commit holds exactly the 3 installed files, Custom status is empty, parent commit touches only `Custom` and records Custom's HEAD, both bare remotes' refs are unchanged, and the panel shows "Not pushed — Custom is 1 commit ahead of origin/main (as last fetched)".

## Task Commits

1. **Task 1 RED:** `130c096` (test) - failing tracer, panel, close-guard and no-commit-step tests, git fixtures, layering registration
2. **Task 1 GREEN:** `8086006` (feat) - gitops, commit_plan, commit_step, CommitPanel, slot container, dialog wiring, Phase 5 test adaptation

**Plan metadata:** committed with this SUMMARY (docs).

## TDD Gate Compliance

- **RED (`130c096`):** the four new tests failed, with `ModuleNotFoundError` for `kicad_lib_manager.widgets.commit_panel` / `importer.commit_step` and `TypeError: ImportCore.__init__() got an unexpected keyword argument 'probe_commit'`, because the feature did not exist. Semantic assessment: the failure is the planned one (modules and fields missing), as the plan prescribes, but it is a load-level failure, not an assertion on behaviour, so it would not pass the stricter #3770 `INVALID_RED` classifier. The `gsd_run check tdd-red-evidence` classifier was not run.
- **GREEN (`8086006`):** all four tests pass first time. No REFACTOR commit.

## Files Created/Modified

- `kicad_lib_manager/gitops.py` - run_git choke point, GitContext/GitRun, find_git, read-only primitives, path-limited write primitives
- `kicad_lib_manager/importer/commit_plan.py` - CommitFile, CommitPlan, build_commit_plan, sanitize_line, default_message, subject_of, parent_message, parent_preview
- `kicad_lib_manager/importer/commit_step.py` - CommitProbe, CommitOutcome, probe_commit, run_commit
- `kicad_lib_manager/widgets/commit_panel.py` - CommitPanel state machine and signals
- `kicad_lib_manager/widgets/import_result.py` - commit slot container, set_commit_panel, clear_commit_panel
- `kicad_lib_manager/widgets/import_dialog.py` - ImportCore.probe_commit/run_commit, commit step after a successful install, is_committing and close guards
- `tests/gitfixtures.py` - make_superproject (session-cached template), populate_custom, remote_refs, requires_git
- `tests/test_import_dialog.py` - four new tests, git-free fakes as defaults, slot assertion updated, probe wait before close in two Phase 5 tests
- `tests/test_importer_layering.py` - `importer.commit_plan` and `importer.commit_step` registered

## Decisions Made

- `expected_branch` is accepted by `run_commit` but not used yet; the refusal that uses it belongs to plan 06-07.
- `run_commit` uses `committed_gitlink` for the parent's old gitlink and treats a missing old gitlink as "nothing to list" (empty list, listed=True) rather than "could not be listed".
- `build_commit_plan` takes the on-disk spelling from `op.listed_path` when set, for both the git pathspec and the display name.
- `CommitPanel` adds a public `outcome_lines()` method (not in the plan's list) so the tracer can read the "Not pushed" line.
- No `gitops` entry was added to `tests/test_layering.py`, as the plan assigns that to 06-02.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two Phase 5 tests raced the new probe worker**
- **Found during:** Task 1 verification
- **Issue:** `test_install_close_esc_reject_ignored` and `test_close_refused_while_installing` closed the dialog right after the install ended. The new probe worker blocks Close for a moment (D-07, as the plan intends), so the close was refused.
- **Fix:** both tests now also wait for `not dialog.is_committing()` before closing.
- **Files modified:** tests/test_import_dialog.py
- **Verification:** both pass (the second only runs where Custom is checked out; see Issues Encountered)
- **Committed in:** 8086006

**2. [Rule 3 - Blocking] Session-cached git fixture**
- **Found during:** Task 1 (RED)
- **Issue:** building one superproject took about 5.3 s, above the plan's 1 s threshold.
- **Fix:** `make_superproject` builds a template once per session and copies it, then re-points the remote URLs, the submodule URL and `core.hooksPath` at the copy (the plan allowed this). A copy takes about 0.8 s.
- **Files modified:** tests/gitfixtures.py
- **Committed in:** 130c096

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** both within the plan's intent; no scope change.

## Issues Encountered

- **The plan's verify line cannot pass in a fresh worktree.** `pytest tests/test_import_dialog.py tests/test_importer_layering.py tests/test_layering.py -rs` shows 11 SKIPPED lines ("Custom submodule not checked out") because the `Custom` submodule is not checked out in the worktree. They are Phase 5 tests that use the `custom_copy` fixture, not Phase 6 tests. The four new tests, including the tracer, do not skip and ran. To prove the skipped tests also pass, a throwaway pytest plugin outside the repo pointed `conftest.REPO_ROOT` at the orchestrator checkout's `Custom/` (read only): 152 passed, 0 skipped for the three verify files, and `pytest -m "not kicad_cli"` gave 1597 passed, 15 skipped (all unrelated: Wurth/Custom corpora, symlinks, UAT), 0 failed. Re-run the verify line in the main checkout to get the clean no-SKIPPED result.
- Offscreen Qt has no fonts, so the panel's layout was checked structurally only (size hint 648x373). With the banner, warnings, status rows and an 8-row files list above it, the Result view may be tight at the dialog's 900x600 minimum; plan 06-03 owns the panel visuals.

## Known Stubs

None. `expected_branch` is an accepted-but-unused parameter that plan 06-07 consumes; it affects no behaviour here.

## Threat Flags

None. The new surface (child git process, temp message file) is covered by the plan's threat model; `gitops.py` contains no remote subcommand and `commit_panel.py` renders every string as plain text.

## Next Phase Readiness

- Plans 06-02, 06-03 and 06-04 can run in parallel against the fixed contracts: `CommitPlan`/`CommitProbe`/`CommitOutcome` fields, `CommitPanel` signals (`commit_requested`, `switch_requested`, `file_activated`) and methods (`show_plan`, `apply_probe`, `set_committing`, `set_step`, `show_outcome`, `state`, `message`, `bump_parent`, `committed`, `outcome_lines`, `commit_button`).
- Plan 06-02 owns `tests/test_gitops.py`, the `import_files` fixture and the `gitops` entry in `tests/test_layering.py`.

## Self-Check: PASSED

- Created files exist: gitops.py, importer/commit_plan.py, importer/commit_step.py, widgets/commit_panel.py, tests/gitfixtures.py (all FOUND)
- Commits `130c096` and `8086006` are ancestors of HEAD
- Acceptance-criteria greps all match; the four new tests pass

---
*Phase: 06-git-commit-step*
*Completed: 2026-10-22*
