---
phase: 13-atomic-migration-and-kicad-setup
plan: 02
subsystem: kicad-config
tags: [kicad, json, config-write, chooser, pins, columns, checkout-check]

# Dependency graph
requires:
  - phase: 12-import-flow-fixes-and-case-sensitive-re-test
    provides: the corrected kicad_common.json write contract (REV-05) that the chooser setup reuses
provides:
  - "kicad_setup.py: chooser_tables, plan_pins, plan_columns, sync_kicad_chooser (TBL-02) -- pins every Atomic_ library and sets the MPN/Manufacturer chooser columns in KiCad 10"
  - "kicad_setup.py: same_folder, CheckoutMismatch, wrong_checkout, checkout_mismatch, wrong_checkout_refusal, wrong_checkout_warning (D-26) -- the shared wrong-checkout compare for Generate Tables, Install Part, the migration and the chooser"
  - "kicad_setup registered as a Qt-free foundation module in tests/test_layering.py"
affects: [13-07 (menu action and dialog), 13-16 (migration Run refusal, Result view Set Up KiCad Chooser button), 13-19 (Generate Tables / Install Part D-26 warning)]

# Actuals (#2632)
actuals:
  tokens: 13300
  tasks: 3
  commits: 6
  plan_head_before: 69225c3c71fb944af6e1fcfb3d5410318027d8b1
  plan_head_after: 089776796ef7d78a35300a9fd822a98c1a34ce22

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Config-write contract reuse: sync_kicad_chooser copies sync_kicad_path_vars's shape (plan -> refuse -> confirm -> re-read-merge loop -> verify-before-backup -> backup -> atomic write -> prune) without editing library_scanner.py"
    - "Two-file atomic write with cross-file rollback: kicad_common.json is written before eeschema.json; a failure writing or backing up the second file restores the first from its in-memory original bytes"
    - "D-26 wrong-checkout compare centralised in one Qt-free function (checkout_mismatch) with an injectable config_base, reused by both the chooser's own refusal and (in later plans) Generate Tables/Install Part/the migration"

key-files:
  created:
    - kicad_lib_manager/kicad_setup.py
    - tests/test_kicad_setup.py
    - tests/test_checkout_check.py
  modified:
    - tests/test_layering.py

key-decisions:
  - "No change to library_scanner.py: every shared helper (find_kicad_config_dir, ConfirmAnswer, _as_answer, _read_config, _prune_backups, _PATH_VAR_PASSES, _KICAD_COMMON_BACKUPS_KEPT) is imported, never refactored, so tests/test_kicad_config.py stays untouched"
  - "checkout_mismatch wraps wrong_checkout with its own config read so later plans (Generate Tables, Install Part, the migration) get one call, not three copies of the read-and-compare"

requirements-completed: [TBL-02]

coverage:
  - id: D1
    description: "chooser_tables/plan_pins/plan_columns compute pins and columns from the Destination tables and the owner's real KiCad 10 file shapes"
    requirement: TBL-02
    verification:
      - kind: unit
        ref: "tests/test_kicad_setup.py#test_owner_columns_become_atomic_columns"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_setup.py#test_pins_from_tables"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_setup.py#test_columns_edges"
        status: pass
    human_judgment: false
  - id: D2
    description: "sync_kicad_chooser writes both files only after a confirmed old -> new list, verified to touch only the chooser keys, backed up, and restores kicad_common.json if the second write fails"
    requirement: TBL-02
    verification:
      - kind: unit
        ref: "tests/test_kicad_setup.py#test_confirmed_setup_writes_both_files"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_setup.py#test_verify_failure_aborts_before_backup"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_setup.py#test_second_write_failure_restores_first"
        status: pass
    human_judgment: false
  - id: D3
    description: "Refuses from a git worktree or a checkout other than KICAD_LIB_GITHUB, before asking and again after the re-read, using the shared D-26 wording"
    requirement: TBL-02
    verification:
      - kind: unit
        ref: "tests/test_kicad_setup.py#test_worktree_refused_before_asking"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_setup.py#test_other_checkout_refused_before_asking"
        status: pass
    human_judgment: false
  - id: D4
    description: "checkout_mismatch/wrong_checkout_warning give every future writer (Generate Tables, Install Part, the migration) the same compare and texts"
    requirement: TBL-02
    verification:
      - kind: unit
        ref: "tests/test_checkout_check.py#test_mismatch_names_both_folders"
        status: pass
      - kind: unit
        ref: "tests/test_checkout_check.py#test_newest_version_wins"
        status: pass
      - kind: unit
        ref: "tests/test_checkout_check.py#test_warning_text"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 02: KiCad Chooser Setup and the Shared Wrong-Checkout Check Summary

**New `kicad_setup.py` service pins every `Atomic_` library and adds the MPN/Manufacturer columns to KiCad 10's symbol chooser in one confirmed, backed-up, two-file atomic write, and factors the wrong-checkout compare (D-26) into one Qt-free function every future writer will share.**

## Performance

- **Duration:** 35 min (estimate)
- **Tasks:** 3 completed
- **Files created:** 3 (`kicad_lib_manager/kicad_setup.py`, `tests/test_kicad_setup.py`, `tests/test_checkout_check.py`)
- **Files modified:** 1 (`tests/test_layering.py`)

## Accomplishments

- `chooser_tables`, `plan_pins`, `plan_columns` compute the chooser's target state from the Destination tables and the owner's real KiCad 10 `kicad_common.json`/`eeschema.json` shapes (verified byte-for-byte against the owner's files in RESEARCH F-07).
- `sync_kicad_chooser` copies the `sync_kicad_path_vars` config-write contract exactly: idempotent no-op when already set up, worktree/other-checkout refusal before asking and after the re-read, up to three confirm/re-read/re-plan passes, verify-only-chooser-keys-changed before any backup, `kicad_common.json` written before `eeschema.json`, and a restore of `kicad_common.json` from its in-memory original bytes if the second file's backup or write fails.
- D-26's wrong-checkout compare (`same_folder`, `CheckoutMismatch`, `wrong_checkout`, `checkout_mismatch`, `wrong_checkout_refusal`, `wrong_checkout_warning`) is one small Qt-free module with an injectable config base, ready for Generate Tables, Install Part and the migration Run (later plans) to call without re-deriving the compare or its wording.
- `kicad_setup` registered in `tests/test_layering.py` as a Qt-free foundation module (`fsutil`, `kicad_files`, `kicad_process`, `library_scanner`, `models` only).

## Task Commits

Each task was committed atomically, with Tasks 2 and 3 (tdd="true") following RED -> GREEN -> REFACTOR:

1. **Task 1: Confirmed write (pins, columns)** - `2b1ac1a` (feat)
2. **Task 2a: RED - refusal/retry/restore/D-26 tests** - `a1119b2` (test)
2. **Task 2b: GREEN - refusal, retry, re-read merge, restore** - `63b3df3` (feat)
2. **Task 2c: REFACTOR - extract `_plan_pins_from_common`** - `9ac7311` (refactor)
3. **Task 3a: RED - checkout_mismatch tests** - `ae1f169` (test)
3. **Task 3b: GREEN - checkout_mismatch implementation** - `0897767` (feat)

_No separate plan-metadata commit was required beyond this SUMMARY's own commit (worktree mode: STATE.md/ROADMAP.md excluded)._

## Files Created/Modified

- `kicad_lib_manager/kicad_setup.py` - `ChooserChange`/`CheckoutMismatch` dataclasses; `chooser_tables`, `plan_pins`, `plan_columns`, `sync_kicad_chooser`; `same_folder`, `wrong_checkout`, `checkout_mismatch`, `wrong_checkout_refusal`, `wrong_checkout_warning`, `CHECKOUT_MISMATCH`; private helpers `_chooser_refusal`, `_restore_common`, `_read_eeschema`, `_plan_pins_from_common`, `_plan_chooser_changes`, `_only_chooser_keys_changed`
- `tests/test_kicad_setup.py` - 23 behavior tests covering pins, columns, confirmed write, idempotence, refusals, D-26 `same_folder`, retry/decline/missing-confirm, KiCad-open warning, re-read merge (changed/unstable), bad JSON/shape for both files, verify-before-backup, second-file restore, missing `eeschema.json`, CRLF/BOM preservation
- `tests/test_checkout_check.py` - 11 behavior tests for `checkout_mismatch`/`wrong_checkout_warning`: mismatch, same checkout in another spelling, every absent/invalid input returns `None` without raising, newest version wins, warning text
- `tests/test_layering.py` - `kicad_setup` added to `ALLOWED` and to the Qt-free import-check script

## Decisions Made

- Imported every shared helper from `library_scanner.py` (`find_kicad_config_dir`, `ConfirmAnswer`, `_as_answer`, `_read_config`, `_norm_path`, `_prune_backups`, `_PATH_VAR_PASSES`, `_KICAD_COMMON_BACKUPS_KEPT`) rather than duplicating or refactoring them, per the plan's explicit "never refactor library_scanner in this plan" constraint. Verified with `git diff --stat -- kicad_lib_manager/library_scanner.py` printing nothing after every task.
- `checkout_mismatch` wraps `wrong_checkout` with its own `_read_config` call so later plans get a single ready-made function instead of re-deriving the newest-config-dir-and-read dance each has needed so far.
- `_only_chooser_keys_changed(before, after, file)` takes a `file` selector ("common"/"eeschema") rather than two separate functions, since both verifications share the same "deep-copy before, overwrite only these key paths with after's values, compare" shape; `test_verify_failure_aborts_before_backup` monkeypatches it with a `lambda *a: False`, matching the existing `library_scanner._only_vars_changed` test pattern.

## Deviations from Plan

None - plan executed exactly as written. All three tasks' `<action>` and `<behavior>` specifications were implemented as described; the TDD tasks (2 and 3) followed the full RED -> GREEN -> REFACTOR cycle with evidence captured by running the target tests before and after each implementation step (13 of 24 tests RED before Task 2's GREEN commit; 10 of 11 RED before Task 3's GREEN commit).

## TDD Gate Compliance

| Task | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| 2 (refusal, retry, restore, D-26 compare) | ✓ `a1119b2` (13/24 tests failing for the right reason: missing `same_folder`/refusal/retry/restore logic) | ✓ `63b3df3` (24/24 pass) | ✓ `9ac7311` (dedup helper, 96/96 still pass) | Pass |
| 3 (`checkout_mismatch`) | ✓ `ae1f169` (10/11 tests failing with `AttributeError: no attribute 'checkout_mismatch'`) | ✓ `0897767` (11/11 pass) | - (no refactor needed) | Pass |

Note: this plan's frontmatter carries `type: execute`, not `type: tdd`, so the machine-validated RED-evidence gate (`gsd_run check tdd-red-evidence`) and `workflow.tdd_mode` plan-level enforcement were not active (`workflow.tdd_mode` is absent from `.planning/config.json`). The RED -> GREEN -> REFACTOR discipline above was still followed in full for both `tdd="true"` tasks per the executor's per-task instruction.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `kicad_setup.py` is ready for plan 13-07 (the "Set Up KiCad Chooser..." menu action and its confirm dialog, which will call `sync_kicad_chooser` with a real `confirm`/`running` wired to the GUI) and plan 13-16 (the migration Result view button, and the migration Run's own D-26 refusal via `checkout_mismatch`).
- `checkout_mismatch`/`wrong_checkout_warning` are ready for plan 13-19 (Generate Tables and Install Part D-26 warnings).
- The full plan-level `<verification>` command passed (107 tests: `test_kicad_setup.py`, `test_kicad_config.py`, `test_layering.py`, `test_plain_names.py`, `test_checkout_check.py`). A broader whole-repo `pytest -q` sanity run was also started to confirm no unrelated regression; its result was not required for this plan's own done-criteria and is not blocking.
- No blockers for the next plan in this phase.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/kicad_setup.py
- FOUND: tests/test_kicad_setup.py
- FOUND: tests/test_checkout_check.py
- FOUND: tests/test_layering.py (modified)
- FOUND commit: 2b1ac1a (Task 1)
- FOUND commit: a1119b2 (Task 2 RED)
- FOUND commit: 63b3df3 (Task 2 GREEN)
- FOUND commit: 9ac7311 (Task 2 REFACTOR)
- FOUND commit: ae1f169 (Task 3 RED)
- FOUND commit: 0897767 (Task 3 GREEN)
- Plan-level `<verification>` command (107 tests) re-run: PASSED
- All `<acceptance_criteria>` greps for all three tasks: PASSED
