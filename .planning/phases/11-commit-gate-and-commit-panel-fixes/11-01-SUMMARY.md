---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 01
subsystem: git-integration
tags: [git, identity, environment, subprocess, pytest]
status: complete

requires:
  - phase: 06-commit-step
    provides: gitops.run_git choke point and the throwaway superproject fixtures
provides:
  - "_IDENTITY_VARS allow-list: the six GIT_AUTHOR_*/GIT_COMMITTER_* variables reach git, every other GIT_* stays stripped"
  - "run_git and _commit_with_message take stdin_data (no parameter shadows the input builtin)"
  - "identity_known needs both the author and the committer ident"
affects: [11-07 commit_step identity message]

actuals:
  tokens: 6500
  tasks: 2
  commits: 3
plan_head_before: 74718e640c9693b992064bfb5b218a5048d94360
plan_head_after: c9e318cee538236b604f7c8c28184a8dba97b7d4

tech-stack:
  added: []
  patterns: ["env allow-list re-admitted after a full GIT_* strip"]

key-files:
  created: []
  modified:
    - kicad_lib_manager/gitops.py
    - tests/test_gitops.py

key-decisions:
  - "Exactly six identity variables are re-admitted (author and committer name, email, date); GIT_DIR, GIT_WORK_TREE, GIT_INDEX_FILE and every GIT_CONFIG_* stay stripped, matched case-insensitively"
  - "identity_known checks the author first, then the committer; the panel-facing message stays in commit_step (plan 11-07)"

requirements-completed: [REV-11]

coverage:
  - id: D1
    description: "A commit whose only identity source is the GIT_AUTHOR_*/GIT_COMMITTER_* variables succeeds through run_git; without them it fails"
    requirement: REV-11
    verification:
      - kind: integration
        ref: "tests/test_gitops.py#test_commit_with_identity_from_environment_only"
        status: pass
    human_judgment: false
  - id: D2
    description: "run_git passes exactly the six identity variables plus its three fixed GIT_ variables; repository-redirecting variables are stripped"
    requirement: REV-11
    verification:
      - kind: unit
        ref: "tests/test_gitops.py#test_run_git_keeps_only_identity_variables"
        status: pass
      - kind: unit
        ref: "tests/test_gitops.py#test_run_git_strips_every_git_variable_regardless_of_case"
        status: pass
    human_judgment: false
  - id: D3
    description: "identity_known is True only when both author and committer idents resolve"
    requirement: REV-11
    verification:
      - kind: integration
        ref: "tests/test_gitops.py#test_identity_known_needs_author_and_committer"
        status: pass
    human_judgment: false
  - id: D4
    description: "run_git and _commit_with_message use stdin_data instead of input"
    verification:
      - kind: unit
        ref: "tests/test_gitops.py#test_run_git_has_no_input_keyword"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-30
---

# Phase 11 Plan 01: Git identity from the environment Summary

**`gitops._env` now hands the six GIT_AUTHOR_*/GIT_COMMITTER_* variables to git while still stripping every repository-redirecting GIT_* variable, `identity_known` requires both author and committer, and `run_git` takes `stdin_data` instead of shadowing `input`.**

## Accomplishments

- Tracer: an env-only identity (no user.name or user.email in any config, empty HOME, `user.useConfigOnly`) commits through `commit_paths` on a throwaway superproject, and the same commit fails with the variables unset, so the test cannot pass by reading some other identity.
- `_IDENTITY_VARS` allow-list in `_env`, applied case-insensitively after the full GIT_* strip (threat T-11-01 mitigated and tested with GIT_DIR, GIT_WORK_TREE, GIT_INDEX_FILE, GIT_CONFIG_GLOBAL, GIT_CONFIG_PARAMETERS set).
- `identity_known` runs `git var GIT_AUTHOR_IDENT` then `GIT_COMMITTER_IDENT`; a committer-only environment is no longer reported ready.
- IN-03: `input` renamed to `stdin_data` in `run_git`, `_commit_with_message` and all their callers.

## Task Commits

1. Task 1 (tracer): `07b52c1` feat(11-01): keep the git identity variables through run_git
2. Task 2 RED: `5f61b15` test(11-01): allow-list, two-ident and stdin_data tests (red)
3. Task 2 GREEN: `c9e318c` feat(11-01): require author and committer identity, rename input to stdin_data

## Verification

- `pytest tests/test_gitops.py` : 32 passed.
- Wave check (`test_commit_plan`, `test_commit_step`, `test_gitops`, `test_commit_panel`, `test_importer_layering`, `test_layering`): 178 passed.
- RED confirmed before GREEN: `test_run_git_has_no_input_keyword` and `test_identity_known_needs_author_and_committer` failed against the old code.

## Deviations from Plan

None - plan executed exactly as written. Two small additions inside the planned test work: `test_commit_with_identity_from_environment_only` calls `gitops.add_intent` first (as the real commit flow does) so `commit --only` knows the new file, and `tests/gitfixtures.py` `GitRepos.git(input=...)` was left alone because it is a fixture helper, not `run_git`.

## Known Stubs

None.

## Threat Flags

None. The only trust boundary touched (process environment to git) is the one in the plan's threat model.

## Self-Check: PASSED

- kicad_lib_manager/gitops.py and tests/test_gitops.py exist and contain `_IDENTITY_VARS` and `test_commit_with_identity_from_environment_only`.
- Commits 07b52c1, 5f61b15, c9e318c are on the branch.
