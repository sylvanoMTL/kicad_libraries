---
phase: 06-git-commit-step
plan: 07
subsystem: git
tags: [git, commit, hooks, pathspec, pytest, real-git-tests]
requires:
  - phase: 06-git-commit-step
    provides: "commit_step.run_commit tracer (06-01), gitops primitives (06-02), changed_since_install and pre_install_bytes (06-04), probe fields and parent state (06-05)"
provides:
  - "run_commit refuses before any git write (stale file, branch changed, detached, parent unavailable, ignored path)"
  - "clean failure paths: rejected Custom commit leaves HEAD unchanged and removes the app's own intent-to-add entries; parent failure keeps the Custom commit with the manual command"
  - "post-commit file-list check (commit.unexpected_files)"
  - "commit_parent_ref: parent message built after the Custom commit from every covered commit, skip when the gitlink already equals Custom HEAD"
  - "pre_import_diff: D-09 HEAD vs pre-import content (ContentText) for the dialog"
  - "gitops.ignored_paths, gitops.commit_files; run_git(literal=...) option; tests/gitfixtures.write_hook"
affects: [06-08 commit dialog, 06-03 commit panel (signatures unchanged)]
actuals:
  tokens: 21000
  tasks: 2
  commits: 4
plan_head_before: 530aa29da069b688140005401ac7ad4a383496d4
plan_head_after: 37f04bc149a82b2126f11e01635291521839c07c
tech-stack:
  added: []
  patterns:
    - "precheck-then-write: every refusal is decided by a read-only _precheck before the first git write"
    - "unstage only the app's own add -N paths (reset -q --pathspec-from-file) on any rejected write"
key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/commit_step.py
    - kicad_lib_manager/gitops.py
    - tests/gitfixtures.py
    - tests/test_commit_step.py
key-decisions:
  - "commit_files in gitops is the new diff-tree reader named by the plan; the 06-01 commit primitive stays commit_paths (different functions, so no rename or alias was needed)"
  - "run_git gained literal=True; check-ignore is the one caller that passes literal=False because git rejects the literal pathspec magic for it"
  - "A post-commit file-list mismatch keeps the Custom commit, reports an ERROR and does not bump the parent"
requirements-completed: [GIT-02, GIT-04, GIT-05]
coverage:
  - id: D1
    description: "run_commit refuses before any git write for stale files, a changed or detached branch, an unavailable parent and ignored paths"
    requirement: GIT-02
    verification:
      - kind: unit
        ref: "tests/test_commit_step.py#test_run_commit_refuses_stale_file / _deleted_file / _when_branch_changed / _detached_at_commit_time / _parent_not_ok_before_commit / _ignored_path"
        status: pass
    human_judgment: false
  - id: D2
    description: "Hook rejection, timeout and index.lock in Custom leave HEAD unchanged and undo the app's intent-to-add; a parent failure keeps the Custom commit"
    requirement: GIT-02
    verification:
      - kind: unit
        ref: "tests/test_commit_step.py#test_custom_hook_rejection_undoes_intent / test_parent_hook_rejection_keeps_custom_commit / test_commit_timeout_reported / test_index_lock_reported"
        status: pass
    human_judgment: false
  - id: D3
    description: "Only the listed files are committed, bystander changes in Custom and the parent are untouched, awkward names match only themselves"
    requirement: GIT-02
    verification:
      - kind: unit
        ref: "tests/test_commit_step.py#test_commit_only_listed_files_with_bystanders / test_parent_commit_only_gitlink_with_bystanders / test_already_staged_touched_file_committed_from_worktree / test_literal_pathspec_brackets / test_unicode_and_glob_names_committed"
        status: pass
    human_judgment: false
  - id: D4
    description: "Message and trailers round-trip; the parent message lists every covered Custom commit; not-pushed lines are exact"
    requirement: GIT-04
    verification:
      - kind: unit
        ref: "tests/test_commit_step.py#test_message_round_trip_and_trailers / test_user_edited_message_verbatim / test_parent_message_lists_covered_commits / test_ahead_counts_and_not_pushed_lines / test_parent_step_skipped_when_gitlink_equal"
        status: pass
    human_judgment: false
  - id: D5
    description: "pre_import_diff gives the D-09 HEAD-vs-backup content (diff, error, binary, unchanged)"
    verification:
      - kind: unit
        ref: "tests/test_commit_step.py#test_pre_import_diff_head_vs_backup / test_pre_import_diff_model_is_binary"
        status: pass
    human_judgment: false
duration: 45min
completed: 2026-10-22
status: complete
---

# Phase 6 Plan 07: Exact, Safe Commit Summary

**run_commit now refuses before any git write, leaves nothing behind when a hook, lock or timeout rejects the commit, verifies the committed file list, and builds the parent message from every covered Custom commit; pre_import_diff supplies the D-09 diff content. All proven against real git.**

## Performance

- **Duration:** about 45 min
- **Tasks:** 2 (both TDD)
- **Files modified:** 4

## Accomplishments

- `_precheck` (read-only) runs at the top of `run_commit`: plan ERRORs, `changed_since_install` (D-11), Custom availability, detached HEAD, `expected_branch`, parent state when the bump is ticked, and `check-ignore` on the new paths. The first failure returns one ERROR and no `add`, `commit` or `reset` is issued.
- A rejected `add -N` or commit (hook exit, `index.lock`, 300 s timeout) runs `reset -q` on exactly the app's own new paths, reports git's/hook's stdout and stderr, and never retries. A parent failure keeps the Custom commit and carries the `git -C ... commit -m "Update Custom: ..." -- Custom` command.
- After the Custom commit, `gitops.commit_files` (diff-tree) must equal the planned set, otherwise ERROR `commit.unexpected_files` (the commit stays, the parent is not bumped).
- `commit_parent_ref` builds the parent message after the Custom commit (earlier D-13 commits included) and skips with INFO `commit.parent_skipped` when the gitlink already equals Custom HEAD.
- `pre_import_diff(cplan, rel)` returns a `ContentText` titled `{path} - HEAD vs before this import` (diff / binary / unchanged / error).

## TDD Gate Compliance

- Task 1: RED `868d6d2` (test), GREEN `c719bff` (feat). Task 2: RED `e04afd9` (test), GREEN `37f04bc` (feat). No refactor commits.
- RED evidence: pytest output is not one of the report formats `gsd_run check tdd-red-evidence` supports, so the verdict is a manual semantic assessment. Task 1 RED: 6 of 11 target tests failed on the planned assertions (stale file committed anyway, wrong error codes `commit.custom_failed` instead of `commit.stale_file`/`commit.ignored`, etc.). Task 2 RED: 5 of 14 failed (`AttributeError` for `commit_files`, `commit_parent_ref`, `pre_import_diff`, and the missing `commit.unexpected_files` ERROR). The remaining tests in each batch passed already because plan 06-01's tracer implemented those behaviors; they are kept as regression characterization tests.

## Task Commits

1. **Task 1 RED:** `868d6d2` (test)
2. **Task 1 GREEN:** `c719bff` (feat)
3. **Task 2 RED:** `e04afd9` (test)
4. **Task 2 GREEN:** `37f04bc` (feat)

## Files Created/Modified

- `kicad_lib_manager/importer/commit_step.py` - `_precheck`, `_custom_failure`, `commit_parent_ref`, `pre_import_diff`, post-commit file check; `CommitProbe`/`CommitOutcome`/`SwitchOutcome` and the `run_commit` signature unchanged
- `kicad_lib_manager/gitops.py` - `ignored_paths`, `commit_files`, `run_git(literal=...)`
- `tests/gitfixtures.py` - `write_hook`; `_local_config` drops a copied `core.hooksPath` first
- `tests/test_commit_step.py` - 26 new real-git tests

## Decisions Made

- `commit_files` (new diff-tree reader) and `commit_paths` (06-01 commit primitive) are different functions, so the orchestrator's naming note needed no rename or alias; every plan key_link (`commit_files(`) is satisfied by the new function.
- Parent step with no committed gitlink (`old` is None) keeps the earlier behaviour (empty commit list, listed) instead of the plan's literal "listed=False", which would print "(the Custom commits since  could not be listed)".
- A mismatch in the committed file list stops before the parent bump and says so in the ERROR text.
- Messages are committed with git's default cleanup for `-F` (whitespace mode): `#` lines are kept, but trailing whitespace and runs of blank lines are normalised. Tests compare with trailing newlines stripped as the plan allows.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] check-ignore rejects the literal pathspec magic**
- **Found during:** Task 1 (GREEN)
- **Issue:** `run_git` always passes `--literal-pathspecs`; `git check-ignore` exits 128 with "pathspec magic not supported ... 'literal'", so `ignored_paths` failed on every call.
- **Fix:** `run_git(..., literal=True)` keyword; `ignored_paths` passes `literal=False` (argv gets `--no-literal-pathspecs`, so the subcommand stays at `argv[6]`) and `--no-index`, so git does not glob-match names such as `AB[1].step` against the index.
- **Files modified:** kicad_lib_manager/gitops.py
- **Verification:** `test_run_commit_refuses_ignored_path`; `tests/test_gitops.py` (argv shape and forbidden-argument tests) still pass.
- **Committed in:** c719bff

**2. [Rule 1 - Bug] Test fixture copies shared the session template's hooks folder**
- **Found during:** Task 1 (RED run)
- **Issue:** `make_superproject` copies a session template whose config holds an absolute `core.hooksPath`; `_local_config` then asked `rev-parse --git-path hooks`, which honours that value, so a hook written for one test's repo landed in the template and made unrelated tests fail with "hook says no".
- **Fix:** `_local_config` unsets `core.hooksPath` before computing and setting it.
- **Files modified:** tests/gitfixtures.py
- **Verification:** all 11 Task 1 tests and the full suite pass.
- **Committed in:** 868d6d2

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug). **Impact on plan:** both necessary for the planned behavior; no scope change.

## Issues Encountered

- The orchestrator's pre-check expected a `commit_files` name clash with `commit_paths`; there is none (see Decisions).
- `Custom` and `WurthElektronik` submodules are not checked out in the worktree, so older tests that need them skip (72 skips in the full run, none in the tests of this plan). The orchestrator re-runs the suite in the main checkout. The plan's `git status --porcelain Custom` check is vacuous in the worktree.

## Verification

- `pytest tests/test_commit_step.py tests/test_commit_plan.py tests/test_gitops.py tests/test_importer_layering.py -q -rs`: 135 passed, 1 skipped (Custom submodule not checked out in this worktree).
- `pytest -q -m "not kicad_cli"`: 1688 passed, 72 skipped, 15 deselected.
- Prohibition scan: `test_git_modules_hold_no_remote_or_destructive_argument` passes; no `-a`, `-A`, `--all`, `-f`, `--amend`, `--no-verify` constants were added.

## Known Stubs

None.

## Threat Flags

None. `run_git(literal=False)` is used by `check-ignore` only, with stdin-supplied paths and no shell.

## Next Phase Readiness

Plan 06-08 can call `commit_step.pre_import_diff(cplan, rel)` and `commit_step.commit_parent_ref`; the `CommitProbe`/`CommitOutcome` fields and `run_commit` signature are unchanged.

## Self-Check: PASSED

- Modified files exist: commit_step.py, gitops.py, gitfixtures.py, test_commit_step.py.
- Commits `868d6d2`, `c719bff`, `e04afd9`, `37f04bc` are ancestors of HEAD.
- Acceptance greps (`def _precheck(`, `def commit_parent_ref(`, `def pre_import_diff(`, `def ignored_paths(`, `def commit_files(`, `def write_hook(`, issue codes, all named tests) pass.
