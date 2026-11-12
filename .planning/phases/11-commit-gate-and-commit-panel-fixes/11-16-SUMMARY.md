---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 16
subsystem: git
tags: [git, environment, identity, gitops, tdd]

requires:
  - phase: 11-commit-gate-and-commit-panel-fixes
    provides: REV-11 env-identity commit path in gitops.run_git
provides:
  - "gitops._env passes only GIT_AUTHOR_NAME/EMAIL and GIT_COMMITTER_NAME/EMAIL from the session"
  - "Author and committer dates are stripped, so an exported date never stamps a commit"
  - "Identity name case folding only on Windows; exact upper-case key wins on every platform"
affects: [commit panel, commit step]

actuals:
  tokens: 5500
  tasks: 2
  commits: 3
plan_head_before: d851ab8ffd04e8f1f236844d89a6f63c6b2de226
plan_head_after: 9260600

tech-stack:
  added: []
  patterns:
    - "Platform branch made testable through keyword argument (_env(environ, windows=...))"

key-files:
  created: []
  modified:
    - kicad_lib_manager/gitops.py
    - tests/test_gitops.py

key-decisions:
  - "Owner decision 5: GIT_AUTHOR_DATE and GIT_COMMITTER_DATE are stripped like every other GIT_* variable"
  - "Lower-case identity names are promoted only when sys.platform == win32; elsewhere git ignores them, so they are dropped"

requirements-completed: [REV-11]

coverage:
  - id: D1
    description: "A commit made through gitops with an environment identity keeps that identity and ignores exported GIT_AUTHOR_DATE / GIT_COMMITTER_DATE"
    requirement: REV-11
    verification:
      - kind: integration
        ref: "tests/test_gitops.py#test_commit_ignores_exported_dates"
        status: pass
      - kind: integration
        ref: "tests/test_gitops.py#test_commit_with_identity_from_environment_only"
        status: pass
    human_judgment: false
  - id: D2
    description: "_env keeps exactly four identity variables, folds case only on Windows, and lets an exact upper-case key win"
    requirement: REV-11
    verification:
      - kind: unit
        ref: "tests/test_gitops.py#test_env_keeps_four_identity_names"
        status: pass
      - kind: unit
        ref: "tests/test_gitops.py#test_env_folds_case_only_on_windows"
        status: pass
      - kind: unit
        ref: "tests/test_gitops.py#test_env_exact_upper_case_wins"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-10-30
status: complete
---

# Phase 11 Plan 16: Git identity passthrough (IN-06) Summary

**gitops._env now hands git only the four author/committer name and email variables, strips both DATE variables, and folds identity-name case only on Windows with an exact upper-case key winning.**

## Performance

- **Duration:** 12 min
- **Completed:** 2026-10-30T18:16:57Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Fixed IN-06: an exported `GIT_AUTHOR_DATE` / `GIT_COMMITTER_DATE` no longer stamps every commit the GUI makes; REV-11's env-identity commit still passes against real git.
- `_env(environ=None, *, windows=None)` makes the platform branch testable on one machine; a lower-case identity name is no longer promoted on POSIX, where git ignores it.
- The strip of repository-redirecting variables (`GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_CONFIG_*`) is unchanged and now also pinned by `test_env_keeps_four_identity_names` (lower-case `git_work_tree` included).

## TDD Evidence

- **RED:** `tests/test_gitops.py::test_commit_ignores_exported_dates` against the old `_env`. Exit code 1, `1 failed, 3 passed, 29 deselected`. Assertion output: `Env Author <author@example.invalid>|Env Committer <committer@example.invalid>|2001|2001` with `assert ('2001' != '2001')`. Semantic assessment: the target test ran to completion, the commit succeeded with the env identity, and it failed on exactly the planned assertion (the exported 2001 date stamped both author and committer dates). Not a setup or import failure. (The `check tdd-red-evidence` classifier was not run: pytest console output is not one of its supported report formats and no JUnit XML was produced.)
- **GREEN:** `_env` rewritten; the same test passes (`4 passed` for `-k "identity or dates"`).
- **REFACTOR:** none needed.

## Task Commits

1. **Task 1 RED: failing date test** - `09435c0` (test)
2. **Task 1 GREEN: four identity variables, Windows-only folding** - `266f889` (feat)
3. **Task 2: folding-rule tests** - `9260600` (test)

## Files Created/Modified
- `kicad_lib_manager/gitops.py` - `_IDENTITY_VARS` reduced to four, `_env` takes `environ` / `windows`, `sys` and `Mapping` imported, module docstring reworded.
- `tests/test_gitops.py` - new `test_commit_ignores_exported_dates`, `test_env_keeps_four_identity_names`, `test_env_folds_case_only_on_windows`, `test_env_exact_upper_case_wins`; `test_run_git_keeps_only_identity_variables` updated; new `KEPT_IDENTITY_NAMES` constant (`IDENTITY_NAMES` kept at six for clearing the developer's own variables).

## Decisions Made
- Followed owner decision 5 (dates stripped), superseding the CONTEXT note that kept them.
- Identity vars set via exact key first, then (Windows only) the first case-insensitive match.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated `test_run_git_keeps_only_identity_variables` in the Task 1 GREEN commit rather than Task 2**
- **Found during:** Task 1
- **Issue:** Task 1's verify selector (`-k "identity or dates"`) matches that test, and it asserted the old six-name behavior, so Task 1 could not go green without updating it.
- **Fix:** Updated it (four kept names, DATE variables set but expected stripped) together with the `_env` change.
- **Files modified:** tests/test_gitops.py
- **Committed in:** 266f889

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Ordering only; the final content matches the plan's Task 2 description for that test.

## Verification Run
- `tests/test_gitops.py tests/test_commit_step.py -k "identity or env"`: 15 passed.
- `tests/test_gitops.py` whole file: 40 passed.
- Not run: `tests/test_commit_step.py -k identity` as a separate command is covered by the `identity or env` selection above. The full suite was not run (15 to 27 minutes, per worktree instructions).

## Issues Encountered
None

## Known Stubs
None

## User Setup Required
None - no external service configuration required.

## Self-Check: PASSED
