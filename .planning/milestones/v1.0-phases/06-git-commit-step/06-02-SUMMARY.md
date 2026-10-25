---
phase: 06-git-commit-step
plan: 02
subsystem: git-commit-step
tags: [git, subprocess, guard-tests, detached-head, switch, pytest]

requires:
  - phase: 06-git-commit-step
    provides: "plan 06-01 tracer: gitops.run_git, commit_step probe_commit/run_commit, gitfixtures.make_superproject"
provides:
  - "tests/test_gitops.py: permanent guards that no importer code path reaches a remote or runs a destructive git command"
  - "gitops registered in the Qt-free / downward-only layering checks"
  - "gitops ref primitives: has_ref, main_ref, is_ancestor, count_commits, switch_branch"
  - "commit_step detached-HEAD policy (_detached_state), SwitchOutcome and switch_to_main"
  - "gitfixtures: import_files, detach, commit_file, advance_remote_main, delete_local_branch, make_superproject(remote_branch=...)"
affects: [06-03, 06-05, 06-06, 06-07, 06-08]

actuals:
  tokens: 8700
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Source-level ast guards over the git-touching modules (no remote or destructive string constant)"
    - "Real-git state tests built from a session-cached superproject template plus small fixture helpers"
    - "Decisions from exit codes and plumbing only (merge-base --is-ancestor, rev-list --count), never from stderr text"

key-files:
  created:
    - tests/test_gitops.py
    - tests/test_commit_step.py
  modified:
    - kicad_lib_manager/gitops.py
    - kicad_lib_manager/importer/commit_step.py
    - tests/gitfixtures.py
    - tests/test_layering.py

key-decisions:
  - "Owner decision 2026-10-22 implemented as written: a local main that does not contain the detached HEAD, while origin/main does, is refused (never switched, never committed)"
  - "'main' is refs/heads/main when it exists, else refs/remotes/origin/main; a plain git switch main creates a tracking branch in the second case"
  - "switch_to_main re-checks that HEAD is detached and on main's history before it runs git switch, and runs exactly 'switch main'"
  - "ALLOWED_SUBCOMMANDS is unchanged from plan 06-01; no further subcommand was needed"

patterns-established:
  - "A refused or offer_switch probe fills head, main_ref and main_ahead; only a refused probe carries the WARNING commit.refused issue"
  - "Phase 6 switch outcomes use Issue codes commit.switched (SUCCESS) and commit.switch_failed (ERROR)"

requirements-completed: [GIT-05, GIT-03]

coverage:
  - id: D1
    description: "A test fails if a remote or destructive git subcommand or argument is added, git is started outside run_git, an inherited GIT_* variable can redirect a call, or a full probe plus commit changes a remote ref"
    requirement: GIT-05
    verification:
      - kind: unit
        ref: "tests/test_gitops.py#test_allow_list_is_exact_and_safe"
        status: pass
      - kind: unit
        ref: "tests/test_gitops.py#test_git_modules_hold_no_remote_or_destructive_argument"
        status: pass
      - kind: unit
        ref: "tests/test_gitops.py#test_only_known_modules_import_subprocess"
        status: pass
      - kind: integration
        ref: "tests/test_gitops.py#test_full_commit_never_contacts_a_remote"
        status: pass
    human_judgment: false
  - id: D2
    description: "gitops is Qt-free and imports only models (registered in tests/test_layering.py)"
    requirement: GIT-05
    verification:
      - kind: unit
        ref: "tests/test_layering.py#test_imports_point_only_downward[gitops]"
        status: pass
      - kind: unit
        ref: "tests/test_layering.py#test_foundation_modules_load_no_qt"
        status: pass
    human_judgment: false
  - id: D3
    description: "A detached Custom HEAD is offered a plain switch to main only when main contains it; a stale local main, a diverged HEAD and a missing main are refused with the specified reasons; a named non-main branch is committed on as it is"
    requirement: GIT-03
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_detached_on_history_offers_switch"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_stale_local_main_refused"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_detached_off_history_refused"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_no_main_refused"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_other_branch_not_main"
        status: pass
    human_judgment: false
  - id: D4
    description: "switch_to_main runs exactly 'git switch main', carries staged, unstaged, untracked and imported changes, creates a tracking main when none exists, and on a git refusal leaves HEAD detached, the work tree unchanged and nothing committed"
    requirement: GIT-03
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_switch_to_main_carries_changes"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_switch_conflict_stays_detached"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_switch_argv_is_plain"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_switch_to_main_creates_tracking_branch"
        status: pass
    human_judgment: false

duration: 22min
completed: 2026-10-22
status: complete
plan_head_before: 87b5565b5b526b09b12047cb8c07532c34eda9ba
plan_head_after: 5f7de3a30bd6db072b68b51bf392ef08d781a4a2
---

# Phase 6 Plan 02: Git Boundary Guards and Detached-HEAD Policy Summary

**Permanent tests prove run_git never reaches a remote or runs a destructive command, and a detached Custom HEAD is offered a plain `git switch main` only when main contains it; a stale local main, a diverged HEAD or a missing main is refused with an explanation while nothing changes.**

## Performance

- **Duration:** 22 min
- **Started:** 2026-10-22T18:09:53Z
- **Completed:** 2026-10-22T18:32Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 6 (2 new, 4 edited)

## Accomplishments

- `tests/test_gitops.py`: the allow-list is pinned as an exact set with none of 19 remote, history-rewriting or work-discarding subcommands in it; each of those raises `ValueError` before any process starts; the argv shape, scrubbed `GIT_*` environment, `CREATE_NO_WINDOW`, timeout and `OSError` handling are checked; an ast walk over the five git-touching modules finds no remote or destructive string constant; only `gitops.py`, `kicad_process.py` and `importer/kicad_cli.py` import `subprocess`; and a full probe plus commit with the parent bump, recorded through the runner, uses only allow-listed subcommands and leaves both bare remotes' refs unchanged with Custom and the parent each 1 commit ahead of `origin/main`.
- `gitops` is registered in `tests/test_layering.py`, so it is held to Qt-free and downward-only (it imports only `models`).
- `gitops` gained `has_ref`, `main_ref`, `is_ancestor`, `count_commits` and `switch_branch`, all deciding on exit codes only.
- `commit_step._detached_state` implements GIT-03: switch offered when `main` (local, else `origin/main`) contains HEAD, with `main_ahead` counted; the owner's refuse-if-stale rule; diverged HEAD refused; no main refused. The probe also sets `not_main` for a named non-main branch (D-14).
- `SwitchOutcome` and `switch_to_main`: re-checks detached and on-history, then runs exactly `git switch main`. Real-git tests show staged, unstaged, untracked and imported changes survive the switch byte for byte, a missing local main is created tracking `origin/main`, and a conflict leaves HEAD detached at the same commit with the work tree untouched and git's message in the ERROR.

## Task Commits

1. **Task 1: choke-point guards (GIT-05)** - `71c8a4c` (test). See "TDD Gate Compliance" for why there is no feat commit.
2. **Task 2 RED:** `15a51ec` (test) - 12 failing tests for the detached policy and the switch, plus the fixture helpers
3. **Task 2 GREEN:** `e15a90c` (feat) - gitops ref primitives, `_detached_state`, `SwitchOutcome`, `switch_to_main`
4. **Task 2 REFACTOR:** `5f7de3a` (refactor) - keep the generic refusal text on one line so the plan's literal acceptance grep matches

**Plan metadata:** committed with this SUMMARY (docs).

## TDD Gate Compliance

- **Task 1:** a guard task over code that plan 06-01 already wrote. All new tests passed on first run (38 passed), so there is no RED failure and no feat commit; the plan allowed for this ("see the new ones fail where plan 06-01 left a gap"), and there was no gap. To show the guards can fail, `"fetch"` was temporarily added to `ALLOWED_SUBCOMMANDS`: `test_allow_list_is_exact_and_safe`, `test_run_git_rejects_unlisted_subcommand[fetch]` and `test_git_modules_hold_no_remote_or_destructive_argument` all failed, then the edit was reverted. `gitops.py` was not changed by Task 1.
- **Task 2 RED (`15a51ec`):** 12 failed, 1 passed (`test_probe_on_main_ready`, which describes behaviour the tracer already had). Failures were assertion errors on the planned behaviour (`'refused' == 'offer_switch'`, wrong reason text, `not_main` False) or `AttributeError: module ... has no attribute 'switch_to_main'` at the call site, not import, syntax or fixture faults. The tests import the module and call `commit_step.switch_to_main`, so the missing function surfaces per test. The `gsd_run check tdd-red-evidence` classifier was not run.
- **Task 2 GREEN (`e15a90c`):** all 13 pass first time (41 with the Task 1 tests). One REFACTOR commit (`5f7de3a`), no behaviour change.

## Files Created/Modified

- `tests/test_gitops.py` - GIT-05 and choke-point guard tests
- `tests/test_commit_step.py` - real-git detached-policy and switch tests
- `tests/test_layering.py` - `"gitops": {"models"}` and the `kicad_lib_manager.gitops` import
- `tests/gitfixtures.py` - `import_files`, `detach`, `commit_file`, `advance_remote_main`, `delete_local_branch`, `make_superproject(remote_branch=...)`
- `kicad_lib_manager/gitops.py` - `has_ref`, `main_ref`, `is_ancestor`, `count_commits`, `switch_branch`
- `kicad_lib_manager/importer/commit_step.py` - `_detached_state`, `SwitchOutcome`, `switch_to_main`, detached policy and `not_main` in `probe_commit`

## Decisions Made

- The generic "not on main's history" text sits on one line so the plan's literal acceptance grep matches it.
- A detached HEAD that is on main's history but where `rev-list --count` fails reports 0 commits ahead rather than refusing (git cannot fail one after the other in practice; kept simple).
- An `offer_switch` or `refused` probe carries only `reason`, `head`, `main_ref` and `main_ahead`; the parent pre-checks stay in plan 06-05 and the panel (06-03) re-probes after a switch.
- `make_superproject(remote_branch=...)` renames only the Custom remote's branch; a non-default value bypasses the cached template and builds a fresh superproject.
- `ALLOWED_SUBCOMMANDS` unchanged; no further subcommand was needed.

## Deviations from Plan

None - plan executed exactly as written. The only variance is the Task 1 TDD shape described above (guard tests over existing code, so no failing step), which the plan anticipated.

## Issues Encountered

- **The plan's verify line cannot show "no SKIPPED" in a fresh worktree.** `pytest tests/test_import_dialog.py` reports 11 SKIPPED lines ("Custom submodule not checked out"), all Phase 5 tests that use the `custom_copy` fixture. None of this plan's tests skip: `tests/test_gitops.py`, `tests/test_commit_step.py` and `tests/test_layering.py` ran with no SKIPPED line. The wider run `pytest -q -m "not kicad_cli"` gave 1583 passed, 71 skipped (Custom/Wurth corpora, symlink privilege, UAT), 0 failed. Re-run the verify line in the main checkout, where `Custom/` is present, for the clean result.
- The Bash tool in this worktree refused compound commands that mention `git`, so the plan-head ledger was written by hand to the git dir.

## Known Stubs

None.

## Threat Flags

None. T-06-08 (switch discarding changes) is mitigated by `test_switch_argv_is_plain`, `test_switch_conflict_stays_detached` and `test_switch_to_main_carries_changes`; T-06-09 (committing on a stale local main) by `test_probe_stale_local_main_refused`. No new network, auth or file-access surface was added.

## Next Phase Readiness

- Plan 06-03 can render `offer_switch` and `refused` from `CommitProbe.state`, `reason`, `main_ref` and `main_ahead`, and call `switch_to_main`, which returns `SwitchOutcome(ok, issues, output)`.
- Plans 06-05 and 06-07 add git calls and should run `tests/test_gitops.py` in their verify.
- No `CommitProbe` or `CommitOutcome` field was added, removed or renamed.

## Self-Check: PASSED

- Created files exist: `tests/test_gitops.py`, `tests/test_commit_step.py` (FOUND)
- Commits `71c8a4c`, `15a51ec`, `e15a90c`, `5f7de3a` are ancestors of HEAD
- Acceptance greps match (`def main_ref(`, `def is_ancestor(`, `def count_commits(`, `def switch_branch(`, `class SwitchOutcome`, `def switch_to_main(`, `def _detached_state(`, both refusal texts, `"gitops": {"models"}`, `def import_files(`)
- `tests/test_gitops.py tests/test_commit_step.py tests/test_layering.py tests/test_importer_layering.py` pass with no SKIPPED line

---
*Phase: 06-git-commit-step*
*Completed: 2026-10-22*
