---
phase: 06-git-commit-step
plan: 05
subsystem: git-commit-step
tags: [git, probe, worktree, submodule, autocrlf, pytest, tdd]

requires:
  - phase: 06-git-commit-step
    provides: "plans 06-01/06-02: gitops.run_git, probe_commit with the detached-HEAD policy, gitfixtures.make_superproject/import_files"
provides:
  - "gitops: MIN_GIT_VERSION, git_version, busy_operation (via rev-parse --git-path), identity_known, head_blob (cat-file --filters), status_entries"
  - "probe_commit availability order: git version, install errors, Custom toplevel, busy operation, identity, branch policy; one commit.unavailable WARNING per unavailable probe"
  - "parent pre-checks (no repo, merge/rebase/etc in progress, detached) reported as parent_ok/parent_reason without blocking the Custom commit"
  - "dirty_before (D-09), other_changes (D-10), earlier/earlier_listed (D-13) on ready and offer_switch probes"
  - "gitfixtures: git_path, start_merge_conflict, clone_parent_without_submodule, make_worktree"
affects: [06-03, 06-06, 06-07, 06-08]

actuals:
  tokens: 7500
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Busy markers located with rev-parse --git-path so a worktree-private submodule gitdir is found"
    - "Pre-install state compared through the smudge filter (cat-file --filters), identical for core.autocrlf true and false"
    - "Probe returns the first failing availability check as the single reason; later checks never run"

key-files:
  created: []
  modified:
    - kicad_lib_manager/gitops.py
    - kicad_lib_manager/importer/commit_step.py
    - tests/gitfixtures.py
    - tests/test_commit_step.py

key-decisions:
  - "find_git resolves shutil.which per call (default None) instead of binding it as a default argument, so a missing git is testable by patching shutil.which"
  - "An unreadable 'git --version' makes the step unavailable ('git did not report its version') rather than being assumed fine"
  - "Parent checks and the D-09/D-10/D-13 facts are computed for ready and offer_switch probes; unavailable and refused probes keep the field defaults"
  - "gitlink_old is only read when the parent is usable (parent_ok); otherwise earlier is empty and earlier_listed is False"
  - "A failing 'git status' while counting other changes gives other_changes 0 plus a WARNING commit.status_failed instead of failing the probe"

patterns-established:
  - "Phase 6 Issue code commit.status_failed for a non-fatal probe gap"

requirements-completed: [GIT-01, GIT-02]

coverage:
  - id: D1
    description: "The commit step is unavailable with the specific reason and one 'Commit unavailable: ...' WARNING for: git missing, git older than 2.25, uninitialised Custom, a merge/rebase/cherry-pick/revert/bisect in progress in Custom, unknown committer identity"
    requirement: GIT-01
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_git_missing_unavailable"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_old_git_unavailable"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_uninitialised_custom_unavailable"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_custom_busy_unavailable"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_custom_real_merge_unavailable"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_identity_unknown_unavailable"
        status: pass
    human_judgment: false
  - id: D2
    description: "Parent pre-checks report parent_ok False with the exact reason (no repo, detached, merge in progress) while Custom stays ready; the probe reports parent_dir, branch and old gitlink, also in a linked worktree on feature/x with a worktree-private Custom gitdir, where probe and commit work"
    requirement: GIT-02
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_parent_states"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_reports_parent_path_and_branch"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_and_commit_in_linked_worktree"
        status: pass
    human_judgment: false
  - id: D3
    description: "dirty_before flags files that differed from HEAD (or were untracked) before the install, never files the install created, identically with core.autocrlf true and false"
    requirement: GIT-01
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_dirty_before_flags_preexisting_edit"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_dirty_before_clean_file_not_flagged"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_dirty_before_preexisting_untracked_flagged"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_new_file_never_dirty"
        status: pass
    human_judgment: false
  - id: D4
    description: "other_changes counts every non-touched changed or untracked file once (each file in a new folder, a rename once); earlier lists the Custom commits from the parent gitlink to Custom HEAD oldest first, empty when equal, unlisted when the old gitlink is unknown"
    requirement: GIT-01
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_other_changes_counts_each_untracked_file"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_status_entries_rename_counts_once"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_earlier_commits_listed_oldest_first"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_earlier_commits_none_when_gitlink_equals_head"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_earlier_commits_unlisted_when_old_unknown"
        status: pass
    human_judgment: false

duration: 154min (wall clock, includes one 10 min test run that stalled on a busy machine; about 35 min of work)
completed: 2026-10-22
status: complete
plan_head_before: b34f2a5b24cbf4e2600eff24fc41b5f86f68a411
plan_head_after: 1700c05b7ad730fb2521908868bdff6d7c44986a
---

# Phase 6 Plan 05: Commit Availability, Parent Pre-checks and Pre-existing State Summary

**probe_commit now refuses early with the exact reason (no git, git < 2.25, uninitialised Custom, merge/rebase/cherry-pick/revert/bisect, unknown identity), reports parent problems without blocking Custom, and returns the D-09 amber files, D-10 other-change count and D-13 earlier Custom commits, all verified against real git including a worktree-private submodule gitdir and both core.autocrlf settings.**

## Performance

- **Duration:** wall clock 18:27Z to 21:02Z; one full-suite run stalled ten minutes on a loaded machine, real work was about 35 min
- **Started:** 2026-10-22T18:27:28Z
- **Completed:** 2026-10-22T21:02Z
- **Tasks:** 2 (both TDD, RED then GREEN each)
- **Files modified:** 4 (no new files)

## Accomplishments

- `gitops` gained `MIN_GIT_VERSION = (2, 25)`, `git_version`, `busy_operation`, `identity_known`, `head_blob`, `status_entries`. Busy markers come from `rev-parse --git-path`, so they are found where a linked worktree keeps its Custom gitdir (`.git/worktrees/<wt>/modules/Custom`).
- `probe_commit` runs the plan's availability order (git version, install errors, `show_toplevel(Custom) == Custom`, busy operation, identity, then the 06-02 branch policy); the first failure becomes the single reason and one `commit.unavailable` WARNING.
- Parent checks (`_parent_state`) give `parent_ok`/`parent_reason` for no repo (posix path in the message), a merge/rebase/etc in progress, or a detached HEAD, and never change the Custom state. `parent_dir` is always `repo_root`, also in a worktree.
- `_preexisting` fills `dirty_before` (hash of `cat-file --filters HEAD:<rel>` vs `base_sha256`, created files never flagged), `other_changes` (`status --porcelain=v1 -z -uall` minus touched rels, casefolded, renames once) and `earlier`/`earlier_listed` (`log_range(gitlink_old, HEAD)`) for ready and offer_switch probes.
- The linked-worktree test builds a real worktree on `feature/x` with its own Custom, proves the probe, the busy marker at the `--git-path` location, and a full `run_commit` with the parent bump (Custom commit has only the file, parent commit touches only `Custom`).
- `tests/gitfixtures.py` gained `git_path`, `start_merge_conflict`, `clone_parent_without_submodule`, `make_worktree`.

## Task Commits

1. **Task 1 RED:** `5324f6f` (test) - unavailable reasons, parent states, worktree test and fixtures
2. **Task 1 GREEN:** `47997d1` (feat) - gitops primitives, availability order, parent checks
3. **Task 2 RED:** `e14aac7` (test) - dirty_before, other_changes, earlier commits tests
4. **Task 2 GREEN:** `1700c05` (feat) - head_blob, status_entries, the pre-existing-state fields

**Plan metadata:** committed with this SUMMARY (docs).

## TDD Gate Compliance

- **Task 1 RED (`5324f6f`):** 12 failed, 4 passed. Failures were assertion errors on the planned behaviour (`'ready' == 'unavailable'` for git missing, old git, busy markers and unknown identity; the parent-states test failed on the as_posix reason text). The 4 that already passed (`uninitialised_custom_unavailable`, `windows_git_version_is_accepted`, `identity_known_by_default`, `reports_parent_path_and_branch`) describe behaviour plan 06-01/06-02 already had; they guard the new code against regressing it. Semantic assessment: the target tests ran and failed on the planned assertion, not on import, syntax or fixture faults. The `gsd_run check tdd-red-evidence` classifier was not run.
- **Task 1 GREEN:** all 29 tests in `tests/test_commit_step.py` pass.
- **Task 2 RED (`e14aac7`):** 6 failed, 6 passed. Failures: `dirty_before` empty instead of flagged (both autocrlf values), `other_changes` not counted, `earlier` empty, `status_entries` missing (`AttributeError` at the call site in the rename test). The passing ones are the negative cases and defaults that the unchanged probe already satisfied.
- **Task 2 GREEN:** all tests pass; no REFACTOR commit.

## Files Created/Modified

- `kicad_lib_manager/gitops.py` - version, busy, identity, head_blob, status_entries; `find_git` looks up `shutil.which` per call
- `kicad_lib_manager/importer/commit_step.py` - `_custom_unavailable`, `_parent_state`, `_dirty_before`, `_other_changes`, `_earlier`, `_preexisting`; reworked `probe_commit`
- `tests/gitfixtures.py` - `git_path`, `start_merge_conflict`, `clone_parent_without_submodule`, `make_worktree`
- `tests/test_commit_step.py` - the tests named in both tasks plus a few extra guards (see Decisions)

## Decisions Made

- `find_git`'s `which` default changed from `shutil.which` to `None`, resolved per call (see Deviations).
- `git --version` that cannot be read makes the step unavailable instead of being guessed.
- Parent checks and the D-09/D-10/D-13 facts also run for `offer_switch` probes (the plan says "ready and offer_switch"); `refused` and `unavailable` keep defaults.
- A non-zero `git status` while counting yields `other_changes == 0` plus a WARNING `commit.status_failed` rather than a failed probe.
- Extra tests beyond the plan: Windows-style version string accepted, identity known by default, real merge in Custom, `status_entries` rename, offer_switch carries the new fields, unavailable probe leaves defaults, `other_changes == 0` baseline.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] find_git bound shutil.which at definition time**
- **Found during:** Task 1 (RED run of `test_probe_git_missing_unavailable`)
- **Issue:** The plan's test patches `kicad_lib_manager.gitops.shutil.which` to simulate a missing git, but `find_git(..., which=shutil.which)` captured the original function as a default argument, so the patch had no effect and the probe stayed "ready".
- **Fix:** `which` defaults to `None` and `find_git` calls `(which or shutil.which)("git")`. Explicit `which=` callers (tests/test_gitops.py) are unchanged.
- **Files modified:** kicad_lib_manager/gitops.py
- **Verification:** `test_probe_git_missing_unavailable` and the existing `tests/test_gitops.py` pass
- **Committed in:** 47997d1

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** None on behaviour; the production default is identical, only the lookup time moved.

## Issues Encountered

- **The plan's `no SKIPPED line` verify cannot be shown in a fresh worktree.** `pytest tests/test_import_dialog.py` reports 11 SKIPPED lines ("Custom submodule not checked out"), all Phase 5 tests using the `custom_copy` fixture. None of this plan's tests skip. Verification run here: `tests/test_commit_step.py tests/test_gitops.py tests/test_import_dialog.py tests/test_layering.py tests/test_importer_layering.py` gave 213 passed, 11 skipped (all the Phase 5 ones); `pytest -q -m "not kicad_cli"` gave 1662 passed, 72 skipped (Custom/Wurth corpora and similar), 0 failed. Re-run the verify line in the main checkout for the clean no-SKIPPED result.
- The Bash tool in this worktree refuses compound commands that mention `git`, so every git, `file` and ledger call was issued separately and the plan-head ledger was written by hand to the git dir.
- One background test run stalled for ten minutes (machine load from the parallel plan); re-running the same tests individually finished in seconds. Not a test defect.

## Known Stubs

None.

## Threat Flags

None. T-06-07 (committing in the parent when Custom is an uninitialised folder) is mitigated by `show_toplevel(Custom) == Custom` with `test_probe_uninitialised_custom_unavailable`, which also asserts no `add`/`reset`/`commit`/`switch` ran. T-06-10 is covered by plan 06-01's timeouts; every new git call goes through `run_git` with `DEFAULT_TIMEOUT`. No CommitProbe or CommitOutcome field was added, removed or renamed, and `ALLOWED_SUBCOMMANDS` is unchanged (`--version`, `var`, `cat-file`, `rev-parse`, `status` were already allowed).

## Next Phase Readiness

- Plan 06-03's panel can render `dirty_before`, `other_changes`, `earlier`/`earlier_listed` and `parent_ok`/`parent_reason` from a `ready` or `offer_switch` probe.
- Plan 06-07 should re-check both repos inside the commit job; the helpers `_custom_unavailable` and `_parent_state` are reusable for that.
- Plan 06-06 runs in parallel and touches `main_window.py`/`help_dialog.py`; this plan touched none of its files.

## Self-Check: PASSED

- Modified files exist: gitops.py, importer/commit_step.py, tests/gitfixtures.py, tests/test_commit_step.py (all FOUND)
- Commits `5324f6f`, `47997d1`, `e14aac7`, `1700c05` are ancestors of HEAD
- Acceptance greps match (`MIN_GIT_VERSION = (2, 25)`, `def git_version(`, `def busy_operation(`, `def identity_known(`, `"--git-path"`, `GIT_COMMITTER_IDENT`, all probe reason strings, `def head_blob(`, `"--filters"`, `def status_entries(`, `--untracked-files=all`, `dirty_before=`, `other_changes=`, `earlier_listed=`, `def make_worktree(`, `def start_merge_conflict(`)
- All eight named Task 1 tests and eight named Task 2 tests exist and pass

---
*Phase: 06-git-commit-step*
*Completed: 2026-10-22*
