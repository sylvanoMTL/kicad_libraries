---
phase: 13-atomic-migration-and-kicad-setup
plan: 13
subsystem: importer
tags: [migration, applier, rollback, commit-plan, kicad-cli, atomic-migration]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "plan 13-06's migration architecture and applier.py skeleton (apply_migration, MigrationResult, MIGRATION_BACKUPS), plan 13-03's precheck.ensure_tag/PRE_ATOMIC_TAG, plan 13-04's CommitFile.deleted/CommitPlan.message on the Phase 11 commit plan"
provides:
  - "A production-safe migration.apply_migration: preflight (containment, link refusal, staleness, name clashes, case twins), a pre-write KiCad load gate, app-data backups of every replaced/deleted file, a post-write verify, full rollback on any op kind (including a locked-delete retry and a kept-folder warning instead of a torn-down folder), and backup pruning"
  - "migration/commitplan.py: build_migration_commit_plan turns a successful MigrationResult into the Phase 11 CommitPlan (every written file, every deleted tracked file except .bak, the migration's own message), ready for the unchanged commit_step.probe_commit/run_commit"
affects: []

actuals:
  tokens: 14530
  tasks: 3
  commits: 5
  plan_head_before: f4d420948be3dc49328bf83823b58f3e7dbd8018
  plan_head_after: 393955b6145cc410a027e6c29b583edbeee32e0e

tech-stack:
  added: []
  patterns:
    - "Preflight order matters: containment (lexical, never resolve()) -> link refusal -> case-twin pairs -> staleness -> name-taken, so a path reached through a symlink or a planner bug gets its own specific error code instead of being folded into a more generic one"
    - "Hash-convention dispatch by (op.kind, suffix): migration.inventory's InventoryFootprint.sha256 is a footprint's own block-text hash, not the whole file's, so a staleness re-check must recompute the SAME hash kind the plan's base_sha256 used, not blindly re-hash the raw file"
    - "A backup-folder name must satisfy the reused prune_install_backups regex (<date>-<time>[-N]_<suffix>) to be seen as a candidate for pruning"

key-files:
  created:
    - kicad_lib_manager/importer/migration/commitplan.py
    - tests/test_migration_apply.py
    - tests/test_migration_commit.py
  modified:
    - kicad_lib_manager/importer/migration/applier.py

key-decisions:
  - "A write/delete pair under different letter-case spellings of the same file (migration.case_twin, P-08) is checked before staleness/name-taken, not after: on any filesystem the write side of such a pair also satisfies the generic name-taken condition, which would otherwise mask the more specific and more useful case-twin diagnosis"
  - "Containment is judged on the lexically-normalized path (os.path.normpath, never Path.resolve()): resolving would follow a symlink/junction and make an op reached through one look like it escaped Custom outright (migration.outside_custom), which is the wrong, less specific diagnosis for exactly the case migration.link_refused exists to name"
  - "_hash_for takes the op's kind and ORIGINAL suffix as separate arguments from the path whose bytes are actually hashed, because _backup_all re-verifies the backup copy (named <name>_backup_<N>, whose own .suffix is no longer .kicad_mod) for identical content against the same base_sha256 convention the original file used"
  - "_rmdir_or_keep checks emptiness by listing the folder first, never by catching rmdir's OSError: that exception does not reliably distinguish 'not empty' (kept, WARNING, migration still succeeds) from a genuine OS-level failure (must roll back the whole transaction), so only a genuinely non-empty folder is kept and every other rmdir failure propagates"

requirements-completed: [MIG-01, MIG-03, MIG-04]

coverage:
  - id: D1
    description: "A real migration tags Custom pre-atomic, applies, and hands its result to the unchanged Phase 11 commit step for one Custom commit plus the parent ref"
    requirement: "MIG-01"
    verification:
      - kind: integration
        ref: "tests/test_migration_commit.py#test_migration_commit_end_to_end"
        status: pass
      - kind: integration
        ref: "tests/test_migration_commit.py#test_refused_tag_writes_nothing"
        status: pass
    human_judgment: false
  - id: D2
    description: "build_migration_commit_plan produces a CommitPlan with every written file, every deleted tracked file (never a .bak), and the migration's own commit message"
    requirement: "MIG-04"
    verification:
      - kind: integration
        ref: "tests/test_migration_commit.py#test_migration_commit_end_to_end"
        status: pass
    human_judgment: false
  - id: D3
    description: "Nothing is written unless every op is inside Custom with no symlink/junction on the way, every input is unchanged since the preview, and KiCad can load the result"
    requirement: "MIG-03"
    verification:
      - kind: unit
        ref: "tests/test_migration_apply.py#test_op_outside_custom_is_refused"
        status: pass
      - kind: unit
        ref: "tests/test_migration_apply.py#test_junction_or_symlink_is_refused"
        status: pass
      - kind: unit
        ref: "tests/test_migration_apply.py#test_source_changed_after_preview_is_refused"
        status: pass
      - kind: unit
        ref: "tests/test_migration_apply.py#test_case_twin_plan_is_refused"
        status: pass
      - kind: unit
        ref: "tests/test_migration_apply.py#test_load_gate_failure_writes_nothing"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every file the transaction replaces or deletes is backed up before the first write, and only the newest ten migration backups are kept"
    requirement: "MIG-03"
    verification:
      - kind: unit
        ref: "tests/test_migration_apply.py#test_backups_hold_every_replaced_and_deleted_file"
        status: pass
    human_judgment: false
  - id: D5
    description: "A migration either completes fully or leaves Custom exactly as it was, whatever fails and whenever -- every op kind rolls back, a locked delete retries before giving up, an interrupt re-raises after restoring, and a non-empty folder is kept instead of torn down"
    requirement: "MIG-03"
    verification:
      - kind: unit
        ref: "tests/test_migration_apply.py#test_verify_after_ops"
        status: pass
      - kind: unit
        ref: "tests/test_migration_apply.py#test_failure_at_each_op_kind_rolls_back"
        status: pass
      - kind: unit
        ref: "tests/test_migration_apply.py#test_interrupt_rolls_back_and_reraises"
        status: pass
      - kind: unit
        ref: "tests/test_migration_apply.py#test_locked_file_delete_retries_then_rolls_back"
        status: pass
      - kind: unit
        ref: "tests/test_migration_apply.py#test_folder_with_unlisted_file_is_kept"
        status: pass
      - kind: unit
        ref: "tests/test_migration_apply.py#test_rollback_leftover_is_reported"
        status: pass
    human_judgment: false

duration: 90min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 13: Production-safe migration transaction and its hand-off to the Phase 11 commit step Summary

**`migration/applier.py` hardened with preflight (containment/link/stale/name-clash/case-twin), a pre-write KiCad load gate, app-data backups, full rollback (every op kind, locked-delete retry, kept folders, interrupt re-raise) and pruning; new `migration/commitplan.py` turns a successful run into the unchanged Phase 11 `CommitPlan`.**

## Performance

- **Duration:** ~90 min
- **Started:** 2026-11-11
- **Completed:** 2026-11-11
- **Tasks:** 3 completed
- **Files modified:** 4 (1 production file hardened, 1 new production module, 2 new test files)

## Accomplishments

- Task 1 (tracer): `apply_migration` gained a `tools: ToolContext | None` parameter and a fixed `before_first_write` check (only an ERROR refuses; an INFO like `precheck.ensure_tag`'s "tagged"/"tag_reused" carries through). New `migration/commitplan.py` (`MIGRATION_SUBJECT`, `MIGRATION_VENDOR`, `migration_message`, `build_migration_commit_plan`) turns a `MigrationResult` into a `CommitPlan` the unchanged `commit_step.probe_commit`/`run_commit` can commit as one Custom commit plus the parent ref — proven end to end on a real throwaway git superproject.
- Task 2: `_preflight` refuses before a single byte is touched (containment, symlink/junction, case-twin pair, staleness, name-taken); `_load_gate` asks kicad-cli to load every written symbol library and footprint before any backup or write; `_backup_all` copies every file about to be replaced or deleted into the stamp folder first; `_verify` confirms the planned bytes landed; `prune_install_backups` (reused from `importer/applier.py`) keeps the newest 10 migration backups.
- Task 3: rollback is now complete for every op kind. A locked delete retries for about 1s before giving up with `migration.locked`; a non-empty `rmdir` target is kept with a `migration.folder_kept` WARNING instead of being torn down; every rollback leftover is `migration.rollback_incomplete` and names the backup folder; a `migration.rolled_back` INFO summarises whether the undo was complete; a `KeyboardInterrupt` still restores the tree and re-raises; success reports `migration.done`.

## Task Commits

Task 1 is `type="tracer"` (one commit); Tasks 2 and 3 are `tdd="true"` (RED then GREEN each):

1. **Task 1: tag, apply, commit plan, probe and commit in one Custom commit plus the parent ref** - `bb00a93` (feat)
2. **Task 2 RED** - `d42c511` (test) — seven behavior tests against the Task-1 applier.py, all failing on the planned assertion (no preflight/load-gate/backup/verify checks exist yet)
3. **Task 2 GREEN** - `ea34043` (feat) — preflight, load gate, backups, verify, prune; all seven pass
4. **Task 3 RED** - `5505831` (test) — five more behavior tests (one parametrized over all four op kinds), all failing on the planned assertion except the pre-existing interrupt-reraise path (kept as regression coverage, not new RED — see TDD Gate Compliance)
5. **Task 3 GREEN** - `393955b` (feat) — locked-delete retry, kept-folder handling, rollback-leftover reporting with the backup folder, the rolled-back/done summary issues; all five pass

**Plan metadata:** commit pending (this SUMMARY)

## Files Created/Modified

- `kicad_lib_manager/importer/migration/applier.py` - hardened `apply_migration`; new `_preflight`, `_load_gate`, `_backup_all`, `_still_fresh`, `_verify`, `_delete_with_retry`, `_rmdir_or_keep`, `_hash_for`/`_footprint_block_hash`/`_current_hash`; `MIGRATION_BACKUPS_KEPT`
- `kicad_lib_manager/importer/migration/commitplan.py` - new: `MIGRATION_SUBJECT`, `MIGRATION_VENDOR`, `migration_message`, `build_migration_commit_plan`
- `tests/test_migration_apply.py` - new: 15 tests (hand-built `MigrationPlan`s under `tmp_path`, never the live Custom)
- `tests/test_migration_commit.py` - new: 2 real-git tests (`gitfixtures.make_superproject`)

## Decisions Made

- See frontmatter `key-decisions`: preflight check ordering (case-twin before staleness/name-taken), lexical (never-resolving) containment, `_hash_for`'s separate kind/original-suffix/content-path arguments, and listing-first `rmdir`.
- `migration.rollback_failed` was renamed to `migration.rollback_incomplete` in Task 3 to match the plan's own naming and to carry the backup-folder path in the message, as the plan's `must_haves` requires.
- The migration backup folder name gained a `_migration` suffix (`<stamp>[-N]_migration`) so it matches the regex `importer/applier.py`'s reused `prune_install_backups` already enforces (`<date>-<time>[-N]_<suffix>`); the unsuffixed name from 13-06 would never have been recognised as a pruning candidate.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `before_first_write`'s own INFO issues were mistaken for a refusal**
- **Found during:** Task 1, writing `test_migration_commit_end_to_end`
- **Issue:** The 13-06 `apply_migration` treated ANY non-empty `before_first_write()` return as a refusal (`if pre_issues: return MigrationResult(False, ...)`), but `precheck.ensure_tag` always returns a non-empty list on success too (`[Issue(INFO, "migration.tagged", ...)]` or `[Issue(INFO, "migration.tag_reused", ...)]`). Every successful tag-and-apply call would have been rejected.
- **Fix:** Only issues with `Severity.ERROR` stop the transaction now; the rest carry through into the final result's issues (success or failure) instead of being discarded or mistaken for a refusal.
- **Files modified:** `kicad_lib_manager/importer/migration/applier.py`
- **Verification:** `tests/test_migration_commit.py::test_migration_commit_end_to_end` exercises the real `ensure_tag` callback and passes
- **Committed in:** `bb00a93` (Task 1 commit)

**2. [Rule 1 - Bug] The migration backup folder name did not match the reused pruning regex**
- **Found during:** Task 2, writing `test_backups_hold_every_replaced_and_deleted_file`'s pruning assertion
- **Issue:** `_backup_folder` (from 13-06) returned `<root>/migrations/<stamp>` with no suffix; `importer/applier.py`'s `prune_install_backups`, reused verbatim per the plan's interfaces, only recognises folders named `<date>-<time>[-N]_<something>` and silently skips everything else, so no migration backup folder was ever a pruning candidate.
- **Fix:** The folder name gained a fixed `_migration` suffix (and the same `-N` collision-numbering `importer/applier.py`'s own `_backup_folder` uses).
- **Files modified:** `kicad_lib_manager/importer/migration/applier.py`
- **Verification:** `tests/test_migration_apply.py::test_backups_hold_every_replaced_and_deleted_file` seeds 11 folders and confirms pruning to 10
- **Committed in:** `ea34043` (Task 2 commit)

**3. [Rule 1 - Bug] A simulated non-empty-unrelated `rmdir` failure was swallowed as "folder kept"**
- **Found during:** Task 3, running `test_failure_at_each_op_kind_rolls_back[rmdir]`
- **Issue:** The first `_rmdir_or_keep` draft caught any `OSError` from `path.rmdir()` and treated it as "not empty, keep it" — which also silently absorbed a genuine, unrelated rmdir failure (permissions, a simulated fault) instead of letting it roll back the transaction.
- **Fix:** Emptiness is checked by listing the folder first (`os.listdir`); only a folder that is actually non-empty is kept. `path.rmdir()` is then called unguarded (except for a benign `FileNotFoundError` race), so any other failure propagates to the transaction's `except BaseException` handler and rolls back, exactly like a failure in any other op kind.
- **Files modified:** `kicad_lib_manager/importer/migration/applier.py`
- **Verification:** `tests/test_migration_apply.py::test_failure_at_each_op_kind_rolls_back[rmdir]` and `test_folder_with_unlisted_file_is_kept` both pass
- **Committed in:** `393955b` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 — bugs found while implementing this plan's own tasks, each in `applier.py`, this plan's own file). **Impact on plan:** All three were necessary for the plan's own `must_haves`/`acceptance_criteria` to hold; no scope creep.

## Issues Encountered

- **`footprints.py`'s footprint-delete `base_sha256` is a block-text hash, not a whole-file hash — out of this plan's scope.** `migration/footprints.py` (plan 13-10's module, explicitly out of bounds for this plan) sets a deleted v1 footprint's `base_sha256` to `fp.sha256` from `migration/inventory.py`'s `InventoryFootprint`, which is `hashlib.sha256(block_text(...).encode("utf-8"))` — the hash of just the `(footprint ...)` S-expression's own span, excluding the file's surrounding whitespace (typically a trailing CRLF). Every other op producer in this codebase (`symbols.py`'s library deletes, `planner.py`'s `.bak` deletes, every write's pre-existing-target check) hashes the whole file's raw bytes. A naive whole-file re-hash in this plan's new staleness check (`_preflight`, `_backup_all`, `_still_fresh`) therefore flagged every untouched footprint delete as `migration.stale`, breaking the pre-existing `tests/test_migration_e2e.py` tracer tests. **Fix applied entirely within this plan's own file:** `_hash_for` (in `applier.py`) recomputes the exact same block-text hash `migration.inventory` uses, via `kicad_files` (already in this module's `ALLOWED` import set — the plan's interfaces list suggests this was anticipated), for a `kind == "delete"` op whose original path suffix is `.kicad_mod`; every other op keeps the whole-file hash. `footprints.py`/`inventory.py` themselves were not touched, per this plan's boundary. A future plan that revisits `footprints.py`/`inventory.py` should consider aligning `InventoryFootprint.sha256` with the whole-file convention the rest of the codebase uses, which would let this workaround in `applier.py` be simplified back to a single hash function.

## Known Stubs

None.

## Threat Flags

None — every write surface this plan touches (`applier.py`'s own filesystem ops, `commitplan.py`'s pure CommitPlan construction) was already in the plan's `<threat_model>`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `migration/applier.py`'s `apply_migration` and `migration/commitplan.py`'s `build_migration_commit_plan` are complete at the service level: MIG-01 (tag at Run), MIG-03 (transaction safety: preflight, load gate, backups, rollback, pruning) and MIG-04 (one Custom commit plus the parent ref, through the unchanged Phase 11 commit step) all hold.
- Sibling wave-4 plans (13-09 symbols.py, 13-10 footprints.py, 13-11 families.py, 13-12 gate.py/mapfile.py, 13-14 widgets/migration_dialog.py) were not touched, per this plan's isolation boundary.
- The `footprints.py`/`migration.inventory` hash-convention mismatch documented above (Issues Encountered) is not a blocker for this plan — `applier.py` works around it correctly and the full verification suite passes — but is worth revisiting if a later plan touches either module, so the workaround in `_hash_for` does not become the only place this knowledge lives.
- No blockers.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/importer/migration/applier.py
- FOUND: kicad_lib_manager/importer/migration/commitplan.py
- FOUND: tests/test_migration_apply.py
- FOUND: tests/test_migration_commit.py
- FOUND: commit bb00a93 (Task 1)
- FOUND: commit d42c511 (Task 2 RED)
- FOUND: commit ea34043 (Task 2 GREEN)
- FOUND: commit 5505831 (Task 3 RED)
- FOUND: commit 393955b (Task 3 GREEN)
- `pytest tests/test_migration_apply.py tests/test_migration_commit.py tests/test_migration_e2e.py tests/test_importer_layering.py tests/test_gitops.py -q` -> 79 passed
- `grep -n "migration.outside_custom\|migration.stale\|migration.load_failed\|prune_install_backups(" kicad_lib_manager/importer/migration/applier.py` -> all four found
- `grep -c "rmtree" kicad_lib_manager/importer/migration/applier.py` -> 0
- `grep -n "except BaseException" kicad_lib_manager/importer/migration/applier.py` -> found
- `grep -n "def build_migration_commit_plan\|MIGRATION_SUBJECT" kicad_lib_manager/importer/migration/commitplan.py` -> both found
