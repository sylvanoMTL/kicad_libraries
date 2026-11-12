---
phase: 04-plan-and-install-core
plan: 07
subsystem: importer
tags: [kicad, transaction, rollback, backup, kicad-cli, fault-injection, pytest]

requires:
  - phase: 04-plan-and-install-core
    provides: "04-01 plan contract and tracer applier; 04-02 installfixtures; 04-03 kicad_cli.load_gate and FakeCli; 04-05 verify_install hard and soft checks; 04-06 planner INFO install.cli_not_found and mkdir ops for new libraries"
provides:
  - "apply_plan as one transaction: containment, freshness, staged sources, D-03 load gate, bounded app-data backups, ordered atomic writes, verify, reverse rollback"
  - "run_load_gate(plan) for a Phase 5 'Check with KiCad' action; writes nothing"
  - "prune_install_backups(installs_dir, keep) and INSTALL_BACKUPS_KEPT = 10"
  - "tests/test_install_apply.py: 48 tests, including the fault matrix selected by -k rollback"
  - "Issue codes install.rollback_failed, install.backup_prune_failed; install.stale_plan and install.nothing_to_do now come from the full precondition pass"
affects: [04-08, 04-09, 04-10, 05-preview-and-install-ui, 06-git-and-registration]

actuals:
  tokens: 11970
  tasks: 3
  commits: 5

plan_head_before: 2eec5e85b238bc8637cf62129a30b7aca3a3e07d
plan_head_after: 875b17c623843c5293315931280c483da86ad389

tech-stack:
  added: []
  patterns:
    - "Preflight passes report every problem of one kind and stop before the next kind, so nothing is written until all hold"
    - "Undo entries are (kind, restore path, written path, pre-image); rollback restores each path once from the earliest pre-image and keeps going past a failed step"
    - "Fault injection by wrapping fsutil.atomic_write_bytes through the module attribute; forward calls are counted, undo calls pass through"
    - "Directory-link tests fall back from os.symlink to a Windows junction (mklink /J), which needs no privilege"

key-files:
  created:
    - tests/test_install_apply.py
  modified:
    - kicad_lib_manager/importer/applier.py

key-decisions:
  - "Backup folder suffixes sit between the timestamp and the library (20261020-101500-2_Lib), so pruning sorts on (date, time, sequence) and treats a name without a suffix as sequence 1; a plain name sort would rank -2 as older than the plain folder"
  - "Rollback removes a file written under another spelling only when both spellings are listed at once (a case-sensitive filesystem). On a case-insensitive one the listing holds a single name and unlinking it would delete the file just restored"
  - "A plan with several writes to one path restores it once, from the earliest pre-image"
  - "The mkdir op creates missing parents but never Custom/ itself or anything outside it"
  - "install.rolled_back always follows the cause and says whether every change was undone or some files could not be restored; leftovers follow it"
  - "Prune warnings are reported on both the success and the failure result"

patterns-established:
  - "The same hand-built plan helper (_hand_plan) serves existing-library and new-library shapes and passes verify_install, so fault tests need no vendor package"
  - "Tests that only need an existing library use the synthetic hand plan; the slow custom_copy plus ul_package path (about 1.2 s each) is kept for source-file checks, the gate bytes, the success order and the matrix"

requirements-completed: [INST-07, INST-08, INST-04]

coverage:
  - id: D1
    description: "A rejecting kicad-cli returns install.cli_gate_failed before any backup or write; the gate sees exactly the planned symbol library and footprint bytes; without kicad-cli the install proceeds with one INFO install.cli_not_found"
    requirement: INST-08
    verification:
      - kind: unit
        ref: "tests/test_install_apply.py#test_gate_rejects_before_any_write / test_gate_runs_on_planned_bytes / test_gate_blames_merge_or_target_with_the_original_bytes / test_gate_standalone_writes_nothing / test_gate_skipped_without_cli / test_gate_cli_note_emitted_once_when_the_planner_already_added_it"
        status: pass
    human_judgment: false
  - id: D2
    description: "A stale plan (target changed or deleted, planned path or its case twin now present, new library folder appeared) is refused with install.stale_plan and nothing is written; a changed or missing staged model gives install.source_changed or install.source_gone; paths outside Custom/ (including through a junction) are refused"
    requirement: INST-04
    verification:
      - kind: unit
        ref: "tests/test_install_apply.py -k 'stale or source or outside' (9 tests, one parametrised over two spellings)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A no-op plan writes nothing, makes no backup folder and runs no gate; a blocked plan is refused first"
    requirement: INST-07
    verification:
      - kind: unit
        ref: "tests/test_install_apply.py#test_noop_plan_writes_nothing_and_runs_no_gate / test_blocked_plan_is_refused_before_noop"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every existing file the install changes is backed up to installs/<timestamp>_<library> before the first write; only the newest ten timestamp-named folders directly under installs/ survive, links are never followed, a prune failure is a WARNING"
    requirement: INST-07
    verification:
      - kind: unit
        ref: "tests/test_install_apply.py -k 'backup or prune' (9 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Any write, lock, backup, verify or rollback-step failure leaves the Custom/ tree byte-identical (folders included) with no .tmp files; failed undo steps are reported and the rest still run"
    requirement: INST-07
    verification:
      - kind: unit
        ref: "tests/test_install_apply.py -k rollback (18 tests, including test_rollback_fail_on_nth_write[existing-1..3, new-1..3] and test_rollback_fail_with_locked_target)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Soft verify WARNINGs (pin/pad mismatch, name elsewhere) appear in InstallResult.issues on a successful install"
    requirement: INST-08
    verification:
      - kind: unit
        ref: "tests/test_install_apply.py#test_success_keeps_the_soft_verify_warnings"
        status: pass
    human_judgment: false
  - id: D7
    description: "Case-twin restore on a case-sensitive filesystem (Foo.step written over foo.STEP, both spellings coexisting)"
    requirement: INST-07
    verification:
      - kind: unit
        ref: "tests/test_install_apply.py#test_rollback_drops_a_file_written_under_another_spelling (listing faked)"
        status: pass
    human_judgment: true
    rationale: "Only NTFS was available. The case-insensitive path is exercised for real (test_rollback_restores_case_twin); the case-sensitive branch is proven with a faked directory listing, not on a real ext4 or APFS volume"

duration: 14min
completed: 2026-10-19
status: complete
---

# Phase 4 Plan 07: Install transaction Summary

**`apply_plan` is now a full transaction: containment, freshness (including case twins), staged-source and D-03 kicad-cli checks run before the first byte, existing files are backed up to a bounded `installs/<timestamp>_<library>` folder, and any failure (write, lock, backup, verify) is undone in reverse order, including created folders, until the `Custom/` snapshot is byte-identical.**

## Performance

- **Duration:** about 14 min
- **Started:** 2026-10-19T23:05:46Z
- **Completed:** 2026-10-19T23:17Z
- **Tasks:** 3 (Tasks 1 and 2 TDD with RED and GREEN commits, Task 3 tests only)
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- Preconditions in plan order: blocked plan, no-op plan (`install.nothing_to_do`, no gate, no backup folder), containment of `path` and `listed_path` (resolved, so junctions are caught), freshness (a created path or any casefold twin of it must be absent from an exact-case listing; a modified path must hash to `base_sha256` at its on-disk spelling), then the staged model hash. Each pass reports all of its problems and stops the next pass.
- `run_load_gate(plan)` wraps `kicad_cli.load_gate` on exactly the planned bytes (merged symbol library, footprint op data), passes the current target bytes as `original_symbol_lib` so a rejection says whether the merge or the target is to blame, and returns one INFO `install.cli_not_found` when there is no CLI. `apply_plan` calls it between the preconditions and the first backup.
- D-19 backups: one folder per install with `-2`, `-3` suffixes on a name clash, `fsutil.backup_file` on the on-disk spelling of every op that has a base, then `prune_install_backups`. Pruning keeps the newest ten, touches only direct child folders whose names fullmatch the timestamp pattern, and skips symlinks, junctions and anything whose resolved parent is not `installs/`.
- Writes: `mkdir` creates missing parents below `Custom/` and records each folder; file ops go through `fsutil.atomic_write_bytes`; an undo entry is recorded only after a successful write. Rollback walks the entries in reverse, restores each path once from the earliest pre-image, unlinks created files, `rmdir`s created folders last, reports every failed step as `install.rollback_failed` naming the path and the backup folder, and always ends with `install.rolled_back` naming the cause.
- Fault matrix: a failure injected at each of the three writes of the real Ultra Librarian plan (existing library) and of the new-library plan (folder, then three files), a locked symbol library on both shapes, a backup failure, a forced verify ERROR, an unremovable created file, a failed restore, the same file written twice. All end with an identical snapshot and no `.tmp` files. A mutation check (dropping the last undo entry from the rollback) made 13 of these tests fail, so they do detect a broken rollback.

## Task Commits

1. **Task 1 RED:** `3ab4abc` (test) - 7 failing, 10 passing characterisation tests
2. **Task 1 GREEN:** `1a019a3` (feat) - preflight passes, `run_load_gate`, verify warnings kept, `install.cli_not_found` once
3. **Task 2 RED:** `b3c45a6` (test) - 7 failing
4. **Task 2 GREEN:** `4bd56e1` (feat) - backups, pruning, mkdir parents, reverse rollback
5. **Task 3:** `875b17c` (test) - fault matrix and extra rollback edges

**Plan metadata:** the docs commits carrying this SUMMARY and the STATE/ROADMAP/REQUIREMENTS updates.

## TDD Gate Compliance

- **Task 1 RED:** `tests/test_install_apply.py` committed with 7 failing and 10 passing tests. The failures are `AttributeError: module ... has no attribute 'run_load_gate'` (four tests and the model-only test), `gate rejects` / `runs on planned bytes` asserting the gate had not run (`result.ok` true, zero fake calls), and `fs.write_failed` where `install.stale_plan` was expected for a pre-existing new-library folder. No collection or fixture fault: `applier.run_load_gate` is reached through the module object, not imported by name, precisely so a missing function fails its own test. The 10 passes pin behavior 04-01 already had (stale hash, source hash, containment, no-op), which is a characterisation, not an unexpected green. Semantic assessment: valid RED. The `tdd-red-evidence` classifier does not read pytest console output and was not run.
- **Task 1 GREEN:** 18 selected tests pass; full suite 1187 passed, 4 skipped.
- **Task 2 RED:** 7 failing (`applier.time` and `prune_install_backups` missing, `mkdir` without parents failing with `fs.write_failed`), 9 passing (backup naming, the 04-01 rollback and `rollback_failed` behavior). Semantic assessment: valid RED.
- **Task 2 GREEN:** 34 tests pass; full suite 1203 passed, 4 skipped.
- **Task 3:** tests only, no implementation change. The matrix runs over behavior Task 2 delivered, so it has no failing phase; its value was confirmed by the mutation check above instead of a RED commit.
- **REFACTOR:** none. Between the Task 3 commit and the final run the test file was shortened (see Deviations); that is part of the Task 3 commit.

## Files Created/Modified

- `kicad_lib_manager/importer/applier.py` - `INSTALL_BACKUPS_KEPT`, `prune_install_backups`, `run_load_gate`, `_preflight`, `_rollback`, `_make_folders`; `apply_plan` rewritten around them; the 04-01 `_undo` removed
- `tests/test_install_apply.py` - `_hand_plan`, `_flaky_writes`, `_link_dir` helpers; gate, stale, source, containment, no-op, backup, prune, rollback tests and the fault matrix (48 tests)

## Decisions Made

See `key-decisions`. Cross-plan findings handled here, as the orchestrator asked:

1. **Soft verify WARNINGs (from 04-05).** `apply_plan` keeps the non-ERROR issues of `verify_install` and appends them to the success result before `install.done`. `test_success_keeps_the_soft_verify_warnings` installs a footprint with an extra pad next to a name that already exists in another library and asserts both `verify.pin_pad_mismatch` and `verify.name_elsewhere` are in `InstallResult.issues` on an `ok` result.
2. **Duplicate `install.cli_not_found` (from 04-06).** The applier's own copy is gone. The gate returns the INFO only when there is no CLI, and `apply_plan` adds a gate issue only when `plan.issues` does not already carry its code. `test_gate_cli_note_emitted_once_when_the_planner_already_added_it` and `test_gate_skipped_without_cli` assert exactly one.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Backup folder pruning sort key**
- **Found during:** Task 2 design
- **Issue:** The plan sorts the timestamp folders by name. With the suffix between timestamp and library, `20261020-101500-2_Lib` sorts before `20261020-101500_Lib` (`-` is below `_`), so the newer folder of two in one second would be pruned first.
- **Fix:** Sort on `(date, time, sequence, name)` with a missing suffix counting as sequence 1; `test_prune_orders_suffixed_folders_after_plain_ones` and `test_prune_keeps_newest_ten` cover it.
- **Files modified:** `kicad_lib_manager/importer/applier.py`
- **Commit:** `4bd56e1`

**2. [Rule 2 - Missing critical] Rollback must not unlink on a case-insensitive filesystem**
- **Found during:** Task 2 design
- **Issue:** The plan says to unlink the written spelling when an entry spelled exactly `written_path.name` is still listed. On NTFS that listing holds a single name after the restore, so the unlink would delete the file just restored.
- **Fix:** Unlink only when both the restore spelling and the written spelling are listed together. Proven by two tests with a faked listing, plus the real NTFS case in `test_rollback_restores_case_twin`.
- **Files modified:** `kicad_lib_manager/importer/applier.py`
- **Commit:** `4bd56e1`

**3. [Rule 2 - Missing critical] Additions the plan implied but did not spell out**
- The `listed_path` is contained in `Custom/` as well as `path`; `mkdir` refuses to create `Custom/` itself or anything outside it; an op with neither `data` nor a source is a `fs.write_failed` rather than a crash; a prune listing failure is a WARNING; the `-2`, `-3` collision loop is in `_backup_folder`.
- **Commit:** `1a019a3`, `4bd56e1`

**4. [Plan wording] `_hand_plan` sets the Footprint field through `vendor_symbol_lib(footprint_field=...)`**
- The plan names `kicad_files.set_property_edit`. `installfixtures.vendor_symbol_lib` already produces the same field text, so the helper uses its `footprint_field` argument and `verify_install` passes on it.

**5. [Plan wording] Fault-matrix coverage check lives inside the matrix test**
- The matrix asserts `non-mkdir ops == MATRIX_WRITES` in every case instead of in a separate test, because a separate test cost two more copies of the 19 MB `Custom/` tree. The plan's "derive the count from the plan" holds: a changed plan shape fails the matrix.

**6. [Performance] Slow-test trimming**
- Each `custom_copy` plus `ul_package` test costs about 1.2 s. The first full run of the file took 18.5 s against the acceptance limit of 20 s, so gate, backup-naming and created-path tests that only need an existing library use the synthetic hand plan. Final run of the file: about 13.5 s.

**Total deviations:** 6 (2 Rule 2 corrections of the plan's text, 1 Rule 2 group of guards, 3 notes on wording and speed). **Impact:** none on the contract.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. T-04-18 (stale plan: hash recheck plus casefold absence recheck), T-04-19 (containment after `resolve()`, covered with a real junction), T-04-20 (in-memory pre-images, reverse undo, reported leftovers) and T-04-21 (pruning limited to timestamp-named direct children, links never followed) are each covered by tests listed in the coverage block. `git status --porcelain Custom` is empty: every install ran against `tmp_path` and every backup root is under `tmp_path`.

## Issues Encountered

- A long Python heredoc with nested quotes was rejected by the Bash tool; the patch and test scripts were written with the Write tool into the scratchpad and run from there. No effect on the result.
- `os.symlink` needs a privilege this account lacks, so directory-link tests use a junction (`mklink /J`) and skip only if both fail.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 04-08 (`install.rename_unsupported`, `install.extends_unsupported`, conflict resolutions) and 04-09/04-10 can build on `apply_plan` unchanged: overwrites arrive as ops with `base_sha256` and `listed_path`, which the freshness, backup and rollback code already handles.
- Phase 5 can call `applier.run_load_gate(plan)` for a preview-time "Check with KiCad" and show `InstallResult.issues` as is (warnings included, a single `install.cli_not_found`).
- Open: the case-sensitive-filesystem rollback branch has no real-volume test (see coverage D7); KiCad 10 behavior of the load gate is unverified here, as in 04-06.

## Self-Check: PASSED

`kicad_lib_manager/importer/applier.py` and `tests/test_install_apply.py` exist; commits `3ab4abc`, `1a019a3`, `b3c45a6`, `4bd56e1` and `875b17c` are ancestors of HEAD (`git rev-list --count 2eec5e8..HEAD` = 5 before this SUMMARY). Plan verification: `pytest tests/test_install_apply.py` 48 passed in about 13.5 s; `-k rollback` 18 passed; `-k fail_on_nth_write -v` lists 6 passed cases; the four-file group (apply, e2e, verify, layering) 106 passed; full suite 1217 passed, 4 skipped (baseline 1169 plus 48 new). `git status --porcelain Custom` prints nothing.

---
*Phase: 04-plan-and-install-core*
*Completed: 2026-10-19*
