---
phase: 13-atomic-migration-and-kicad-setup
plan: 15
subsystem: migration
tags: [migration, atomic-libraries, qt, pyside6, tdd, taskworker, footprints, conflicts, files-tab]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "plan 13-14's MigrationCore/MigrationDialog shell (_targets, _framed, _update_choice, the rebuild/draft timer pair), plan 13-10's footprint-side planner outcomes (official switch, leftovers, clashes, footprint text, added models), plan 13-11's families.py FamilyRow, plan 13-12's gate.py strip targets"
provides:
  - "kicad_lib_manager/widgets/migration_dialog.py: the footprint choice (move/official + picker), the 3D model row, the Atomic_Footprints clash rows, the derive-as-family-member check box, and a new Files tab (every planned op with its diff, and the leftover check boxes)"
affects: ["13-16 (Run itself, the Result view and the commit step, building on this plan's Files tab and _targets map)"]

actuals:
  tokens: 12700
  tasks: 3
  commits: 5
  plan_head_before: 7f3d06a76c6676c697ab36917d263823f72a1b06
  plan_head_after: b52f35114caae445c5232b3e29f00548ea5e7612

tech-stack:
  added: []
  patterns:
    - "MigrationCore grows four more seam fields (footprint_index, official_candidates, op_content, pick_model_file) following the existing frozen-dataclass-with-real-function-defaults pattern; op_content and pick_model_file are module-level functions in migration_dialog.py itself (not re-exports), since they are Qt-dialog-specific (QFileDialog wrapper) or operate on MigrationOp (not importer.plan.FileOp, which already has its own op_content in importer/content.py)"
    - "A strip target key (self._targets[...]) is re-registered every _display_part call rather than fixed once at build time, for the 3D model row: the single-model editable box, the multi-model read-only list and the Add 3D model... button all share the literal target key \"model\" that gate.py's TARGET_MODEL names, and only one of the three is the right fix-point depending on how many models the currently selected part carries"
    - "Per-part conflict rows (detail pane) are matched to plan.conflicts by footprint name (part.footprint_new/footprint_old's name portion), not by re-deriving the planner's own wanted-stem computation; this matches while a clash is unresolved (footprint_new still carries the original wanted name) and is a known simplification once a clash is resolved via rename (documented below, not exercised by this plan's own tests)"
    - "_files_sections pairs a model/footprint rename into one \"Move or rename\" row by matching a write op's source_rel against another op's rel (the delete of the old file), rather than by op order; mkdiven never render in the Files tab, following the must_haves truth's own enumerated list (write, move/rename, delete, folder removal - no folder creation)"

key-files:
  modified:
    - kicad_lib_manager/widgets/migration_dialog.py
  created: []
  modified_tests:
    - tests/test_migration_dialog_files.py

key-decisions:
  - "The footprint name QLineEdit (not the official-footprint combo) is registered under strip target \"footprint\" (gate.py's TARGET_FOOTPRINT), per the plan's own literal action text; this means a migration.official_missing strip line focuses the name edit even when the official picker (not the name edit) is the actual fix point. Accepted as a minor UX gap rather than deviating from the plan's explicit instruction - no behavior test in this plan exercises that specific strip-click scenario."
  - "official_candidates' vendor_path argument is derived by reconstructing the v1 footprint file's path from part.footprint_old (\"Library:Name\" -> Custom/Footprints/<Library>.pretty/<Name>.kicad_mod), guarded by an existence check (None otherwise) rather than threading a Path through PartPlan, since PartPlan carries only the \"Library:Name\" string, not a filesystem path, and no task text specifies a different source."
  - "op_content and _is_model_rel classify a model purely by file extension (.step/.stp/.wrl) on the op's own rel path, never by consulting PartPlan.model_files or MigrationOp metadata - MigrationOp carries no kind flag distinguishing a model write from a text write, and the extension check is the same approach footprints.py and content.py already use elsewhere in this codebase."
  - "A deleted model file is also rendered as kind=\"binary\" (never decoded as text), even though the plan's acceptance test only requires kind=\"text\" for a generic (non-model) delete; this follows the action text's \"never decoding a model\" instruction literally for every op kind, not only writes."

requirements-completed: [MIG-02, MIG-03]

coverage:
  - id: D1
    description: "The detail pane offers 'Move into Atomic_Footprints' (default) or 'Use an official KiCad footprint'; the latter opens the ranked, filterable Lib:FP picker and shows the amber, non-blocking pad check; nothing switches by itself"
    requirement: "MIG-03"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_files.py#test_official_switch_reaches_the_plan"
        status: pass
      - kind: unit
        ref: "tests/test_migration_dialog_files.py#test_pad_mismatch_is_amber_not_blocking"
        status: pass
      - kind: unit
        ref: "tests/test_migration_dialog_files.py#test_default_is_move"
        status: pass
    human_judgment: false
  - id: D2
    description: "The footprint name and the 3D model name are editable; the model row lists the part's model files and offers 'Add 3D model...' for a footprint without one"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_files.py#test_model_row_lists_files_and_renames"
        status: pass
      - kind: unit
        ref: "tests/test_migration_dialog_files.py#test_add_model_sets_source"
        status: pass
    human_judgment: false
  - id: D3
    description: "A clash in Atomic_Footprints shows the importer's conflict row with Overwrite / Rename / Skip and Rename pre-filled; its strip line focuses that row"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_files.py#test_clash_row_resolution_reaches_plan"
        status: pass
    human_judgment: false
  - id: D4
    description: "A family member that can be derived shows a 'Make it a derived symbol of <parent>' check box, ticked by default"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_files.py#test_derive_box"
        status: pass
    human_judgment: false
  - id: D5
    description: "The Files tab lists every write, move or rename, delete and folder removal of the plan, with a diff view on double-click, computed off the GUI thread"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_files.py#test_files_tab_sections"
        status: pass
      - kind: unit
        ref: "tests/test_migration_dialog_files.py#test_file_row_opens_diff_off_thread"
        status: pass
      - kind: unit
        ref: "tests/test_migration_dialog_files.py#test_op_content_kinds"
        status: pass
    human_judgment: false
  - id: D6
    description: "Each leftover footprint or 3D model is a row with a check box (ticked = delete); rows the migration orphans start ticked, board features start unticked; unticking keeps the file and rebuilds the plan"
    requirement: "MIG-03"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_files.py#test_leftover_untick_keeps_file"
        status: pass
    human_judgment: false

duration: 95min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 15: Migration window part 2 - footprint, model, clash, derive controls and the Files tab Summary

**`widgets/migration_dialog.py` gains the footprint choice (move into Atomic_Footprints or switch to a ranked, filterable official KiCad footprint with a non-blocking amber pad check), an editable/read-only 3D model row with Add 3D model..., per-part Atomic_Footprints clash rows reusing the importer's `ConflictRow`, a derive-as-family-member check box, and a new Files tab listing every write/move-or-rename/delete/folder-removal with an off-thread diff view and leftover-file check boxes.**

## Performance

- **Duration:** ~95 min
- **Started:** 2026-11-11
- **Completed:** 2026-11-11
- **Tasks:** 3 completed
- **Files modified:** 2 (1 widget module extended, 1 new test file)

## Accomplishments

- `_build_footprint_section`: two radio buttons (`MOVE_FOOTPRINT_TEXT`, `OFFICIAL_FOOTPRINT_TEXT`), the footprint name `QLineEdit` (target `"footprint"`), and the official picker (filterable `QComboBox`, built on a `TaskWorker` via `core.official_candidates`, the `"KiCad's own footprints are never changed"` hint, an amber `migration.pad_mismatch` line); switching back to Move clears `official_footprint`
- `_build_model_row`: a `QStackedWidget` between a single editable model-name box (target `"model"`), a read-only list for two or more models (D-23), and an Add 3D model... / Remove pair using `core.pick_model_file(self)` (a plain `QFileDialog` wrapper so no test opens a system dialog); the active page's widget is re-registered under target `"model"` on every `_display_part` call
- `_build_conflict_rows_host` / `_display_conflicts`: one `ConflictRow` per `plan.conflicts` entry matching the selected part's footprint name, wired to `MigrationChoices.resolutions`, each registered under `"conflict:<key>"` / `"rename:<key>"` for the strip
- `_build_derive_box` / `_display_derive`: a check box from `plan.families`, labelled `"Make it a derived symbol of <parent's new name>"`, reflecting the live `PartChoice.derive` (default `True`); unticking sends `derive=False`
- `_build_files_tab` / `_files_sections`: a `PreviewTree` rendered from one row per planned `MigrationOp`, grouped into `"Write"`, `"Move or rename"` (a write+delete pair sharing `source_rel` becomes one `"old → new"` row), `"Delete"` and `"Remove folder"` sections (`mkdir` ops are never shown); double-click runs the module-level `op_content(op, repo_root)` on a worker and opens a `ContentViewDialog`
- `op_content`: diffs an existing text file against its planned bytes, shows a new text file's content directly, sizes/hashes a `.step`/`.stp`/`.wrl` model (binary, never decoded) for both writes and deletes, shows `"Deleted by the migration."` plus the current content for other deletes, and `"Folder removed."` for an `rmdir`; every disk read is capped by `content.MAX_READ`
- A `"Leftover files (ticked ones are deleted)"` `QListWidget` with one checkable item per `plan.leftovers` row (ticked = delete, i.e. `not row.keep`), tooltip the reason (html-escaped); toggling writes `choices.leftovers[rel]` and restarts the rebuild/draft timers

## Task Commits

Task 1 (`type="tracer"`) is a single commit; Tasks 2 and 3 (`tdd="true"`) carry a RED test commit then a GREEN feat commit:

1. **Task 1: tracer - official footprint switch from the detail pane (D-08)** - `ddc2a7d` (feat)
2. **Task 2 RED** - `31c19d5` (test) - 4 new tests, all 4 fail genuinely (`AttributeError`: no `_model_name_edit`/`_model_list`/`_add_model_btn`/`_conflict_rows`/`_derive_check` yet)
3. **Task 2 GREEN** - `95615b7` (feat) - model row, clash rows, derive box; all 22 tests in the file pass
4. **Task 3 RED** - `dcc3175` (test) - 4 new tests; 3 fail genuinely (`AttributeError`: no `_files_tree`/`_leftovers_list`), 1 (`test_op_content_kinds`) already passes (see TDD note below)
5. **Task 3 GREEN** - `b52f351` (feat) - the Files tab, leftover rows; all 93 tests across the four verification files pass

**Plan metadata:** committed together with this SUMMARY (worktree mode excludes STATE.md/ROADMAP.md; the orchestrator updates those centrally after merge).

## Files Created/Modified

- `kicad_lib_manager/widgets/migration_dialog.py` - `MOVE_FOOTPRINT_TEXT`, `DERIVE_TEXT`, `FILES_TAB_TEXT`, `LEFTOVERS_TEXT`, `PART_TAB_TEXT`, `_OFFICIAL_HINT` constants; `op_content`, `_pick_model_file`, `_is_model_rel`, `_read_capped` module-level helpers; `MigrationCore.footprint_index`/`.official_candidates`/`.op_content`/`.pick_model_file` seam fields; `_build_footprint_section`, `_build_model_row`, `_build_conflict_rows_host`, `_build_derive_box`, `_build_files_tab`, `_files_sections`, `_on_file_row`, `_on_leftover_changed` and their supporting display/handler methods
- `tests/test_migration_dialog_files.py` - new file: its own `fake_core` fixture (copied from `tests/test_migration_dialog.py`, not imported), 11 behaviour tests across the three tasks

## Decisions Made

See `key-decisions` in the frontmatter: the footprint-name-edit-gets-target-"footprint" literal instruction, the reconstructed `vendor_path` for `official_candidates`, extension-based model classification in `op_content`, and treating a deleted model as binary too (beyond what the test strictly requires).

## Deviations from Plan

None - plan executed exactly as written, Rules 1-3. No auto-fixes were needed.

### TDD note (not a Rule 1-4 deviation - documented for transparency)

As with plans 13-08, 13-10, 13-11 and 13-14's own tracer/TDD notes, Task 3's `test_op_content_kinds` passed immediately against the Task 1 implementation rather than failing first: `op_content` (and its `_is_model_rel`/`_read_capped` helpers) was written in full during Task 1, because it is one of the four `MigrationCore` seam fields that plan's artifact table calls for up front (`footprint_index`, `official_candidates`, `op_content`, `pick_model_file`), and Task 1's own behaviour tests needed the `MigrationCore` dataclass to carry all four fields to stay consistent with the interfaces section. Task 3's action text was then the one that actually *wires* `op_content` into a new UI (the Files tab, double-click handling), which is what its other three tests (`test_files_tab_sections`, `test_file_row_opens_diff_off_thread`, `test_leftover_untick_keeps_file`) genuinely exercise and genuinely fail against the Task 1/2 state before the GREEN commit.

To confirm this was investigated rather than assumed: before writing Task 3's GREEN commit, `kicad_lib_manager/widgets/migration_dialog.py` was reverted to the Task 2 commit (`git checkout -- <file>`) and the four new Task 3 tests were run against that exact state - 3 failed genuinely (`AttributeError` on the missing Files-tab/leftovers widgets) and `test_op_content_kinds` passed, confirming `op_content` was already complete and the other three were not. The GREEN implementation was then restored from a backup copy before committing Task 3 RED, then re-applied and verified for Task 3 GREEN.

---

**Total deviations:** 0 Rule 1-4 auto-fixes.
**Impact on plan:** None - every acceptance criterion and the plan's own verification command pass unchanged.

## TDD Gate Compliance

| Task | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| Task 1 (tracer) | - | `ddc2a7d` (feat, single tracer commit) | - | Pass |
| Task 2 | `31c19d5` (test) - 4/4 new tests genuinely fail (`AttributeError`) | `95615b7` (feat) - all 22 tests in the file pass | not needed | Pass |
| Task 3 | `dcc3175` (test) - 3/4 new tests genuinely fail (`AttributeError`), 1 (`test_op_content_kinds`) already passes (see TDD note) | `b52f351` (feat) - all 93 tests across the four verification files pass | not needed | Pass |

**Task 1 note:** Task 1 is `type="tracer"`. Its own `<verify>` command (`pytest tests/test_migration_dialog_files.py tests/test_migration_dialog.py`) carried only `<automated>` verification with no `<human-check>`, and `workflow._auto_chain_active`/`workflow.auto_advance` were both `false` while `workflow.human_verify_mode` is `end-of-phase` (project default) - per the executor's tracer-feedback precedence chain (row 3: interactive + `end-of-phase` + automated-only), the gate re-ran `<verify>` (18/18 passed) and continued straight to Task 2 with no synthesized checkpoint.

**RED evidence caveat:** `gsd_run check tdd-red-evidence` was not invoked from inside this isolated worktree executor session (matching the same caveat recorded in 13-06/13-10/13-11/13-12/13-14's SUMMARYs). RED was established for Task 2 by running the plan's own `<automated>` pytest command directly before the GREEN commit and inspecting the failures (4 genuine `AttributeError`s on the planned new widgets, never a collection/import error). For Task 3, RED was established the same way, with the additional step of reverting the implementation file to the prior commit first (documented above) specifically because `op_content` already existed from Task 1 and a false "it also fails" claim would not have been honest.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 13-16 (Run itself, the Result view and the commit step) can build on this plan's Files tab (`_files_tree`, `_files_sections`), the leftovers list, and the full `_targets` map (footprint/model/conflict/derive keys) without touching this plan's structure.
- `is_running()`/`is_committing()` are still the overridable seams from 13-14, both returning `False` here; `MigrationDialog.migrated`/`generate_requested`/`setup_chooser_requested` signals remain declared but unemitted, ready for 13-16 to wire.
- Known simplification (not a blocker): the per-part detail-pane conflict-row matching (`_conflicts_for_part`) is by current footprint name, so a clash already resolved via rename in an earlier rebuild may stop matching its part in the detail pane on a later rebuild (it remains visible as a strip line and, once 13-16/future work surfaces it, in any all-conflicts view) - no test in this plan's scope exercises that specific sequence.
- No blockers.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/widgets/migration_dialog.py
- FOUND: tests/test_migration_dialog_files.py
- FOUND: commit ddc2a7d (Task 1)
- FOUND: commit 31c19d5 (Task 2 RED)
- FOUND: commit 95615b7 (Task 2 GREEN)
- FOUND: commit dcc3175 (Task 3 RED)
- FOUND: commit b52f351 (Task 3 GREEN)
- `python -m pytest tests/test_migration_dialog_files.py tests/test_migration_dialog.py tests/test_plain_names.py tests/test_help_dialog.py -q` -> 93 passed
- `grep -n "official_candidates(\|MOVE_FOOTPRINT_TEXT" kicad_lib_manager/widgets/migration_dialog.py` -> both found
- `grep -n "ConflictRow(\|ADD_MODEL_TEXT\|DERIVE_TEXT" kicad_lib_manager/widgets/migration_dialog.py` -> all three found
- `grep -n "def _build_files_tab\|def op_content\|LEFTOVERS_TEXT" kicad_lib_manager/widgets/migration_dialog.py` -> all three found
