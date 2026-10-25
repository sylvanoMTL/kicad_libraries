---
phase: 04-plan-and-install-core
plan: 13
subsystem: importer
status: complete
tags: [applier, stale-plan, toctou, rollback, gap-closure, tdd]

requires:
  - phase: 04-plan-and-install-core
    provides: "_Transaction holder, _transaction, exception-safe rollback (04-11); package issues and blank options (04-12)"
provides:
  - "post-gate freshness pass: created paths re-checked right after the gate, backup copy hashed against op.base_sha256 before the first write"
  - "backed-up bytes are the rollback pre-image"
  - "_still_fresh per-write re-check with an expected-hash map on the transaction"
  - "FakeCli on_call hook"
  - "04-REVIEW-DISPOSITION.md: CR-01, CR-02, WR-01, WR-03, WR-05 fixed, open: 5"
affects: [phase-04-reverification]

actuals:
  tokens: 4200
  tasks: 3
  commits: 5
plan_head_before: ad197878085d40b153a46ebde99793c33dcb92bc
plan_head_after: 668933fe063065bd66ab5cc7ea11dcd9f0fc11fe
commits: 5

tech-stack:
  added: []
  patterns:
    - "Backup copy is the authority: read back and hash it before any write, use it as the rollback pre-image"
    - "A refused write adds no undo entry, so the rollback never touches another process's file"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/applier.py
    - tests/fakecli.py
    - tests/test_install_apply.py
    - .planning/phases/04-plan-and-install-core/04-REVIEW-DISPOSITION.md

key-decisions:
  - "The created-path re-check runs for every plan, before the D-19 backup block, so a pure new-library plan is covered too"
  - "expected map is keyed by the casefolded on-disk spelling (listed_path or path), so a second write of one path compares against what this install wrote"

requirements-completed: []  # INST-07 and LIB-02 await phase re-verification (/gsd-verify-work 04); nothing marked complete by this plan
---

# Phase 4 Plan 13: Stale-plan guarantee across the gate window Summary

A target edited, or a path created, by another process at any point from the preflight to its own write is now refused as `install.stale_plan` and never overwritten or deleted; the rollback restores the backed-up bytes. The phase awaits re-verification (`/gsd-verify-work 04`).

## What was built

- **Task 1 (tracer, CR-02):** `FakeCli(on_call=...)` hook. In `_transaction`, right after the gate and before the D-19 backup block, every op without a base is re-checked with `_name_taken` (unconditional, so a new-library plan is covered). In the backup block each copy is read back and hashed against `op.base_sha256`; a mismatch returns `install.stale_plan` ("changed on disk while the install was being checked") with `backup_dir` set and the live file untouched. The backed-up bytes replace the preflight bytes as the rollback pre-image.
- **Task 2:** `_Transaction.expected` and `_still_fresh(op, expected)`. `_write` takes `expected` as a new last parameter (call site passes `txn.expected`), re-checks immediately before `fsutil.atomic_write_bytes`, and records the written hash afterwards. A refused write adds no undo entry.
- **Task 3:** Full suite run, then `04-REVIEW-DISPOSITION.md` edited: CR-01 (4a57d26), WR-01 (727db69) from 04-11; WR-03 (d33fa20), WR-05 (bebcbe8) from 04-12; CR-02 (2a2a1de) from 04-13. `open: 5`, `total: 10`; WR-02, WR-04, IN-01, IN-02, IN-03 untouched. REQUIREMENTS.md not touched.

## TDD record

- RED 1 (34b8b81): `test_stale_plan_target_edited_during_gate` and `test_stale_plan_created_path_appears_during_gate` failed on `assert not result.ok` (result was ok=True, edit lost) after the hook-ran assertion passed, so the gate window was exercised.
- GREEN 1 (9255368).
- RED 2 (dcf30b2): `test_stale_plan_target_edited_between_writes` and `test_stale_plan_created_path_appears_between_writes` failed on `assert not result.ok`.
- GREEN 2 (2a2a1de).
- No refactor commit.

## Test counts

- BASE (collected in tests/test_install_apply.py before any edit): 61. Final collected: 66 (BASE + 5).
- Full suite in this worktree (Custom and WurthElektronik submodules not checked out): 1252 passed, 66 skipped, 0 failed. The orchestrator's merged-tree run with Custom (1340 passed, 5 skipped before this plan) should be repeated.
- `git status --porcelain Custom` printed nothing; no commit touched `.planning/REQUIREMENTS.md`.

## Skipped here (submodule absent), to be run on the merged tree

- `test_stale_plan_ul_target_edited_during_gate` (needs `custom_copy`/`ul_package`): written to the plan's spec but could not be executed or seen failing in this worktree. Same code path as the hand-plan variant, which passes.
- The other `custom_copy` tests in tests/test_install_apply.py and tests/test_install_e2e.py, including the `-m kicad_cli` real-CLI run from the plan's `<verification>`.

## Deviations from Plan

None - plan executed exactly as written. The 04-11 names matched the interfaces block (`_Transaction`, `_transaction`, `_rollback_once`). Note: the executor ledger file was created at the start (Task 1 step 0) with the base commit ad19787.

One accepted edge: a plan that writes a case twin (`listed_path` differing in case from `path`) twice on a case-sensitive filesystem would compare the second write against the listed spelling; no such plan exists and the first-write behavior is unchanged.

## Known Stubs

None.

## Threat Flags

None. T-04-36, T-04-37 and T-04-38 are mitigated as planned; T-04-39 (change between the re-check read and `os.replace`) is accepted and noted in a code comment.

## Self-Check: PASSED

- Files present: applier.py, fakecli.py, test_install_apply.py, 04-REVIEW-DISPOSITION.md.
- Commits present: 34b8b81, 9255368, dcf30b2, 2a2a1de, 668933f.
