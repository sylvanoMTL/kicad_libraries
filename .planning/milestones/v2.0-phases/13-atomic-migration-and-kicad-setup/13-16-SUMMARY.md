---
phase: 13-atomic-migration-and-kicad-setup
plan: 16
subsystem: migration
tags: [migration, atomic-libraries, qt, pyside6, tdd, taskworker, commit-step, run]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "plan 13-14/13-15's MigrationDialog shell (_targets, _plan, _ctx, _layout, is_running()/is_committing() seams, the migrated/generate_requested/setup_chooser_requested signals), plan 13-13's applier.apply_migration/precheck.ensure_tag/commitplan.build_migration_commit_plan, plan 13-02's kicad_setup.checkout_mismatch/wrong_checkout_refusal (D-26), plan 13-07's _on_setup_chooser"
provides:
  - "kicad_lib_manager/widgets/migration_dialog.py: Run itself (wrong-checkout refusal, KiCad-open check, tag-then-apply on a worker, the failure banner), the Result view (map text, Copy, open file, Generate Tables, Set Up KiCad Chooser buttons) and _CommitStepHost (the commit panel wiring: probe, Check again, commit, switch to main)"
affects: ["13-17 (wiring MigrationDialog's issues_logged/atomic_check_requested/generate_requested/setup_chooser_requested signals into the main window)"]

actuals:
  tokens: 12518
  tasks: 2
  commits: 3
  plan_head_before: 58924c6fdef50f28ee6c595d07ed12afd3f5e2d2
  plan_head_after: 02cc6445b3dd6282df1ec8d1a57a9dd3fd5c6906

tech-stack:
  added: []
  patterns:
    - "MigrationCore grows eight more seam fields (apply, ensure_tag, checkout_mismatch, ask_kicad_open, commit_plan, probe_commit, recheck_commit, run_commit, switch_to_main, pre_import_diff, changed_diff, open_file) following the existing frozen-dataclass-with-real-function-defaults pattern; ask_kicad_open and open_file are new module-level functions in migration_dialog.py itself (Qt dialog wrappers), the rest are re-exports of existing Qt-free service functions"
    - "_CommitStepHost is a standalone class (not dialog methods) copying import_dialog.py's commit-step glue almost verbatim - generation-cancelled probe, Check again, commit, switch to main, amber-file diff views - with its own docstring recording the duplication as known debt (RESEARCH F-10) rather than factoring a shared base that would touch import_dialog.py, outside this plan's isolation boundary"
    - "The Run sequence is three sequential off-thread checks chained through worker result signals (checkout_mismatch -> kicad_running -> ask_kicad_open on the GUI thread for the modal decision -> apply), each stage able to stop the chain (a mismatch refuses immediately; Cancel declines; Retry restarts the kicad_running check) before the apply worker - and therefore the actual write - ever starts"
    - "A failed Run's banner reuses import_dialog.py's _show_failure shape (title switches to the not-everything-restored variant, closing line names the backup folder) without importing it, since the migration's own ERROR issues and MigrationResult.backup_dir carry the same information through a different Issue code (migration.rollback_incomplete vs install.rollback_failed)"

key-files:
  modified:
    - kicad_lib_manager/widgets/migration_dialog.py
  created:
    - tests/test_migration_dialog_run.py

key-decisions:
  - "is_running() tracks the whole Run attempt (set True at the first click, cleared only once the checkout refusal/Cancel/apply-done path resolves), not just the apply worker itself - because the window must stay locked through the wrong-checkout and KiCad-open checks too, and the plan's own wording (\"never closable mid-way\") reads as covering the whole sequence, not just the write"
  - "ask_kicad_open is a MigrationCore field taking (parent, names) rather than a bound dialog method, so its default implementation (a plain QMessageBox with Retry/Run anyway/Cancel) can be swapped for a fake in every test without the dialog itself growing a second code path for tests vs production, mirroring how pick_model_file (13-15) already does this for QFileDialog"
  - "A failed Run calls _start_load() (not just _start_rebuild()) to recover, re-reading the inventory, context and draft from scratch - this matches the plan's literal instruction (\"re-read the inventory and rebuild\") and is safe because a failed migration always rolls back to the exact pre-Run state, so the fresh read reproduces what the owner already had open, at the cost of re-applying the saved draft over any very recent unsaved edit (a debounced-but-not-yet-fired draft save)"
  - "_run_content is a new one-line MigrationDialog helper (build a ContentText on a worker, then open it via the existing _on_file_content_ready) so _CommitStepHost's amber-file double-click reuses the same off-thread content pipeline the Files tab (plan 13-15) already established, instead of building a second one"

requirements-completed: [MIG-01, MIG-03, MIG-04, MIG-05]

coverage:
  - id: D1
    description: "Run first compares the app's repo folder with KiCad's KICAD_LIB_GITHUB folder; a mismatch refuses with nothing written, naming both folders and the fix; no mismatch (or no KiCad config) runs"
    requirement: "MIG-01"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_run.py#test_wrong_checkout_refuses_run"
        status: pass
    human_judgment: false
  - id: D2
    description: "Run checks for a running KiCad on a worker and, when found, asks Retry (default) / Run anyway / Cancel before anything is written"
    requirement: "MIG-01"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_run.py#test_kicad_open_asks_before_run"
        status: pass
    human_judgment: false
  - id: D3
    description: "Run tags Custom pre-atomic and applies the plan as one transaction on a worker with progress; the window cannot be closed while it runs"
    requirement: "MIG-01, MIG-03"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_run.py#test_run_applies_on_a_worker_with_tag_first"
        status: pass
    human_judgment: false
  - id: D4
    description: "A failed Run shows every reason, says every file was restored (or names the backup folder when one could not be), and returns to the preview rebuilt from the files on disk"
    requirement: "MIG-03"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_run.py#test_failed_run_shows_reasons_and_rebuilds"
        status: pass
    human_judgment: false
  - id: D5
    description: "A successful Run clears the draft, emits migrated, and shows the Result view: the old -> new map (read-only, equal to plan.map_text) and the ordered next-steps line"
    requirement: "MIG-04, MIG-05"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_run.py#test_successful_run_shows_result_and_clears_draft"
        status: pass
    human_judgment: false
  - id: D6
    description: "The Result view offers Copy (clipboard) and an Open MIGRATION-ATOMIC.md link (core.open_file)"
    requirement: "MIG-05"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_run.py#test_copy_and_open_map"
        status: pass
    human_judgment: false
  - id: D7
    description: "Generate Tables and Set Up KiCad Chooser... only emit signals; neither writes anything by itself"
    requirement: "D-24, D-17"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_run.py#test_generate_and_chooser_buttons_emit"
        status: pass
    human_judgment: false
  - id: D8
    description: "The Result view hosts a commit panel fed by core.commit_plan(result, plan) (deleted files marked), probed on a worker; a commit click runs on a worker and is_committing() blocks closing meanwhile; Check again re-probes; open_check_requested re-emits as atomic_check_requested"
    requirement: "MIG-04"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_run.py#test_commit_panel_offered_and_probed"
        status: pass
    human_judgment: false

duration: 65min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 16: Migration window part 3 - Run, the failure and Result views, and the commit step Summary

**`widgets/migration_dialog.py` gains Run itself (wrong-checkout refusal, a KiCad-open Retry/Run anyway/Cancel check, tag-then-apply on a worker, a failure banner that restores and rebuilds) and the Result view (the saved old-to-new map with Copy/open-file buttons, Generate Tables and Set Up KiCad Chooser signals, and a `_CommitStepHost` wiring the existing `CommitPanel` to the migration's own `commit_plan`/`probe_commit`/`run_commit`/`switch_to_main`).**

## Performance

- **Duration:** ~65 min
- **Started:** 2026-11-11
- **Completed:** 2026-11-11
- **Tasks:** 2 completed
- **Files modified:** 2 (1 widget module extended, 1 new test file)

## Accomplishments

- `_on_run` -> `_start_checkout_check` -> `_on_checkout_checked`: a `core.checkout_mismatch(repo_root)` worker refuses Run outright on a KiCad checkout mismatch (D-26), naming both folders via the shared `kicad_setup.wrong_checkout_refusal`, before any KiCad-open check, tag or write
- `_start_kicad_check_for_run` -> `_on_run_kicad_checked`: a `core.kicad_running()` worker followed by `core.ask_kicad_open(self, names)` when KiCad is open (default: a `QMessageBox` with Retry/Run anyway/Cancel); Retry re-checks, Cancel stops, Run anyway (or no KiCad) continues to `_start_run`
- `_start_run`: shows the new running page, then a worker calling `core.apply(plan, tools=ctx.tools, progress=progress, before_first_write=lambda: core.ensure_tag(layout.custom_dir, repo_root))`; `is_running()` is true for the whole Run attempt (from the first click through a refusal, a decline, or the apply worker's own result) and both `done()`/`closeEvent()` already deferred on it
- `_show_run_failure`/`_show_run_banner`: a new failure banner on the edit page lists every ERROR text plus "Every file was restored." (or, when `migration.rollback_incomplete` is present, the backup folder), then `_start_load()` re-reads the inventory and rebuilds
- `_build_result_page`/`_show_result`: on success, `clear_draft` runs, `migrated` is emitted, and the window shows `RESULT_TITLE`, a read-only monospace `plan.map_text`, `COPY_TEXT` (clipboard), `OPEN_MAP_TEXT` (`core.open_file(Custom/MIGRATION-ATOMIC.md)`), `GENERATE_TEXT`/`CHOOSER_TEXT` (pure signal emissions) and `NEXT_STEPS_TEXT`
- `_CommitStepHost`: copied from `import_dialog.py`'s commit-step glue (probe with generation-cancel, Check again, commit, switch to main, amber-file diff views via the dialog's new `_run_content` helper); fed by `core.commit_plan(result, plan)`; `is_committing()` now reflects it and blocks closing; `open_check_requested` re-emits as the dialog's `atomic_check_requested` signal for a later plan's main-window handler

## Task Commits

Task 1 (`type="tracer"`) is a single commit; Task 2 (`tdd="true"`) carries a RED test commit then a GREEN feat commit:

1. **Task 1: tracer - Run itself, wrong-checkout refusal, KiCad check, tag and transaction, failure view** - `6ff896d` (feat)
2. **Task 2 RED** - `756526c` (test) - 4 new tests, all 4 fail genuinely (2 `AttributeError` on `dialog._result_page` not built yet, 2 `TypeError` on `MigrationCore.__init__()` rejecting `open_file`/`commit_plan` keyword args not yet fields)
3. **Task 2 GREEN** - `02cc644` (feat) - the Result view, `_CommitStepHost`, the eight new `MigrationCore` fields; all tests in the verification command pass

**Plan metadata:** committed together with this SUMMARY (worktree mode excludes STATE.md/ROADMAP.md; the orchestrator updates those centrally after merge).

## Files Created/Modified

- `kicad_lib_manager/widgets/migration_dialog.py` - `RUN_REFUSAL_ACTION`, `RESULT_TITLE`, `COPY_TEXT`, `OPEN_MAP_TEXT`, `GENERATE_TEXT`, `CHOOSER_TEXT`, `NEXT_STEPS_TEXT` and the failure-banner text constants; `_ask_kicad_open`, `_open_file` module-level default functions; `_CommitStepHost` class; eight new `MigrationCore` fields; `issues_logged`/`atomic_check_requested` signals; `_build_running_page`, `_build_run_failure_banner`, `_on_run` and its full worker chain, `_show_run_failure`/`_show_run_banner`, `_build_result_page`, `_show_result`, `_on_copy_map`/`_on_open_map`, `_start_commit_step`/`_clear_commit_host`, `_run_content`
- `tests/test_migration_dialog_run.py` - new file: its own `fake_core` fixture (copied convention from `tests/test_migration_dialog.py`/`tests/test_migration_dialog_files.py`), 8 behavior tests across the two tasks

## Decisions Made

See `key-decisions` in the frontmatter: `is_running()` covering the whole Run attempt (not just the apply worker), `ask_kicad_open` as a `(parent, names)` MigrationCore field rather than a bound method, `_start_load()` (not `_start_rebuild()`) as the failed-Run recovery step, and the new `_run_content` helper reusing the Files tab's off-thread content pipeline for the commit panel's amber-file views.

## Deviations from Plan

None - plan executed exactly as written, Rules 1-3. No auto-fixes were needed.

### Test-authoring note (not a Rule 1-4 deviation - documented for transparency)

Two early drafts of the Task 1 tests failed for the WRONG reason before being corrected (caught during this plan's own execution, not left in the committed RED/GREEN history): `dialog._run_failure_banner.isVisible()` is always `False` in every test in this file, because `make_dialog`'s dialogs are never `.show()`n (matching the rest of the migration-dialog test suite) - a hidden top-level widget's children report `isVisible() == False` regardless of their own `show()`/`hide()` state, while `isHidden()` reflects only the widget's own explicit state and is unaffected by the ancestor chain. `tests/test_migration_dialog_files.py` already established `isHidden()` as the correct assertion for exactly this reason (see its `_official_box`/`_derive_check` checks); this plan's tests follow that same convention for the new failure banner. The one test that does need real top-level visibility (`test_run_applies_on_a_worker_with_tag_first`'s "a close attempt is ignored" assertion, and `test_commit_panel_offered_and_probed`'s equivalent) calls `dialog.show()` first, matching `tests/test_migration_dialog.py#test_close_while_planning_waits_without_blocking`'s own pattern. Both corrections were made and verified before Task 1's tracer commit and Task 2's RED/GREEN commits respectively - no committed test ever asserted on `isVisible()` without first showing the dialog.

---

**Total deviations:** 0 Rule 1-4 auto-fixes.
**Impact on plan:** None - every acceptance criterion and the plan's own verification command pass unchanged.

## TDD Gate Compliance

| Task | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| Task 1 (tracer) | - | `6ff896d` (feat, single tracer commit) | - | Pass |
| Task 2 | `756526c` (test) - 4/4 new tests genuinely fail (2 `AttributeError`, 2 `TypeError`) | `02cc644` (feat) - all 101 tests across the plan's verification command plus `test_help_dialog.py` pass | not needed | Pass |

**Task 1 note:** Task 1 is `type="tracer"`. Its own `<verify>` command (`pytest tests/test_migration_dialog_run.py tests/test_migration_dialog.py tests/test_migration_dialog_files.py`) carried only `<automated>` verification with no `<human-check>`, and `workflow._auto_chain_active`/`workflow.auto_advance` were both `false` while `workflow.human_verify_mode` is `end-of-phase` (project default) - per the executor's tracer-feedback precedence chain (row 3: interactive + `end-of-phase` + automated-only), the gate re-ran `<verify>` (30/30 passed) and continued straight to Task 2 with no synthesized checkpoint.

**RED evidence caveat:** `gsd_run check tdd-red-evidence` was not invoked from inside this isolated worktree executor session (matching the same caveat recorded in every prior plan's SUMMARY in this phase - no `.claude/gsd-core/` is present in this worktree). RED was established by running the plan's own `<automated>` pytest command directly before the GREEN commit and inspecting the failures: 2 genuine `AttributeError`s (`dialog._result_page` does not exist on the Task-1-only dialog) and 2 genuine `TypeError`s (`MigrationCore.__init__()` rejects the `open_file`/`commit_plan` keyword arguments, which were not yet fields) - never a collection or import error, and never an unrelated assertion.

## Issues Encountered

None beyond the test-authoring note above (resolved before any commit).

## Known Stubs

None.

## Threat Flags

None - every write surface this plan touches (the Run worker's call into the already-hardened `applier.apply_migration`, the commit host's call into the already-hardened `commit_step.run_commit`/`switch_to_main`) was already in the plan's own `<threat_model>`, and no new surface outside it was introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- MIG-01, MIG-03, MIG-04 and MIG-05 are now complete at the window level: Run is safe (checkout-aware, KiCad-open-aware, tagged, atomic, restorable on failure), and a successful Run shows and saves its map, offers the single Custom commit plus the parent ref, and signals Generate Tables / Set Up KiCad Chooser for the next plan to wire.
- Plan 13-17 (wiring the window into the main window menu and the User Guide page) is ready to connect `MigrationDialog.issues_logged`, `atomic_check_requested`, `generate_requested` and `setup_chooser_requested` to the main window's existing log, `Check Atomic Parts`/`AtomicCheckDialog`, Generate Tables and `_on_setup_chooser` handlers respectively - none of those main-window-side handlers were touched by this plan, per its isolation boundary.
- The whole-fixture end-to-end proof (plan 13-20, already merged at this plan's base) exercises the same service-level pipeline (`applier.apply_migration`, `commitplan.build_migration_commit_plan`) this plan's window now drives interactively; this plan's own tests stay at the fake-core level by design (no test in this plan opens a real git repository or a real modal dialog).
- No blockers.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/widgets/migration_dialog.py
- FOUND: tests/test_migration_dialog_run.py
- FOUND: commit 6ff896d (Task 1)
- FOUND: commit 756526c (Task 2 RED)
- FOUND: commit 02cc644 (Task 2 GREEN)
- `python -m pytest tests/test_migration_dialog_run.py tests/test_migration_dialog.py tests/test_migration_dialog_files.py tests/test_plain_names.py tests/test_help_dialog.py -q` -> 101 passed
- `python -m pytest tests/test_layering.py tests/test_importer_layering.py tests/test_commit_panel.py tests/test_import_dialog.py -q` -> 354 passed (broader regression check; not required by this plan's own done-criteria but run anyway since `migration_dialog.py`'s import set grew substantially)
- `grep -n "before_first_write=\|def _on_run\|def _start_run\|checkout_mismatch\|RUN_REFUSAL_ACTION" kicad_lib_manager/widgets/migration_dialog.py` -> all five found
- `grep -n "class _CommitStepHost\|generate_requested.emit\|setup_chooser_requested.emit\|clear_draft" kicad_lib_manager/widgets/migration_dialog.py` -> all four found
- `git rev-list --count 58924c6..HEAD` -> 3 (matches `actuals.commits`)
