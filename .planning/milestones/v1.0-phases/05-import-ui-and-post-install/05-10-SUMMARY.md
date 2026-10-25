---
phase: 05-import-ui-and-post-install
plan: 10
subsystem: ui
tags: [pyside6, import-dialog, conflicts, content-view, build-queue, d-08, d-12, d-14a, tdd]

requires:
  - phase: 05-import-ui-and-post-install
    provides: "05-06 importer/content.py, ContentViewDialog, PreviewTree.row_activated; 05-07 _resolutions/_reset_edit_state; 05-09 _reason_targets/_field_frames, blocking_reasons, rebuild coordinator"
provides:
  - "widgets/conflict_row.py: ConflictRow (Overwrite / Rename / Skip toggles, none checked at first, rename field, hint, left bar, activation)"
  - "importer/form.py: carry_resolutions(old, plan), choices kept by Conflict.key"
  - "ImportDialog Conflicts section: rows updated in place by key, registered as conflict:{key} / rename:{key} reason targets"
  - "Content view wired: file rows and conflicts open ContentViewDialog; content built on a TaskWorker"
  - "One serial build queue shared by rebuilds and one-off conflict builds (at most one build_plan at a time)"
  - "ImportCore.op_content and ImportCore.unchanged_content (replaceable in tests)"
affects: [05-11]

plan_head_before: 531f43207b5c91b4a14850ee60c47c508bc913ae
plan_head_after: afee5aacc201deae765b2b78d79baa722122e4af

actuals:
  tokens: 15200
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "The dialog owns the user's conflict choices (self._resolutions, typed rename text included) and prunes them to the keys of each accepted plan; rows only display and report"
    - "A ConflictRow is never recreated while its key stays in the plan: update_conflict/set_resolution act in place, and set_resolution is skipped when the row already shows the choice, so focus, cursor and typed text survive a rebuild"
    - "Build queue: _pump_builds starts the latest queued rebuild first, then one-off jobs FIFO; a one-off result goes only to its callback and carries the package session so a result of a changed package is dropped"
    - "Content is built by core.op_content / core.unchanged_content on a TaskWorker; only ContentViewDialog rendering runs on the GUI thread"

key-files:
  created:
    - kicad_lib_manager/widgets/conflict_row.py
  modified:
    - kicad_lib_manager/importer/form.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_import_form.py
    - tests/test_import_dialog.py

key-decisions:
  - "The rename field sits on its own line under the three buttons, not to their right: three buttons plus a 160 px field are wider than the 365 px left pane at 900x600 and would be clipped (AlwaysOff horizontal bar). The field keeps min width 160 inside a QFrame#fieldFrame"
  - "Line 1 reads '{name} — {Conflict.existing}' as recorded in the plan (Conflict.existing is already a full sentence)"
  - "A Rename with no name keeps the amber bar and shows the hint 'Rename - enter the name to install the {kind} as; the existing {kind} stays untouched'; the 'Needs a choice' marker is only for a row with no action"
  - "A skipped footprint drops the incoming model, so the planner removes the model conflict from the plan; its row and any choice for it go with it, and it comes back unresolved if the footprint is switched to Overwrite"
  - "A rebuild request (including a queued one) is preferred over a queued one-off job; a one-off job is bound to the package session that queued it"
  - "The one-off build keeps the user's other choices and adds Resolution('overwrite') for the one key; the view always shows the incoming side regardless of what was chosen for that key"

patterns-established:
  - "incoming_op(plan, conflict) finds the op that carries the incoming side of a conflict (footprint by name, model by plan.model_file, symbol_lib for a symbol)"
  - "Dialog tests build conflicts with write_clashes(layout, ...) before opening: a different DQK0006B.kicad_mod, a different CSD85301Q2.stp and a library with a different CSD85301Q2 symbol"

requirements-completed: [PREV-05, PREV-01]

coverage:
  - id: D1
    description: "One conflict row per conflict with Overwrite, Rename and Skip; none checked at first, 'Needs a choice' until decided, no bulk control, Install blocked until every row is decided"
    requirement: PREV-05
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_rows_no_bulk_and_none_selected", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_row_exclusive_toggles_and_line_one", status: pass}
    human_judgment: false
  - id: D2
    description: "Choosing a button rebuilds at once with Resolution(action, rename_to); the checked button clicked again changes nothing; Rename pre-fills the suggested name, passes the text exactly as typed, and an empty name blocks Install with 'Enter a new name for ...' and an amber frame"
    requirement: PREV-05
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_choice_rebuilds_and_resolves", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_rename_field_and_empty_reason", status: pass}
    human_judgment: false
  - id: D3
    description: "Choices are kept by Conflict.key (carry_resolutions); a key that vanishes drops its choice, a new key starts unresolved, rows update in place keeping focus and typed text"
    requirement: PREV-05
    verification:
      - {kind: unit, ref: "tests/test_import_form.py#test_carry_resolutions", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_choice_carried_by_key", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_rows_update_in_place", status: pass}
    human_judgment: false
  - id: D4
    description: "Case-twin clash is a row, an identical item has none, rows and reasons follow plan order, section hidden without conflicts, Overwrite is red with its hint and the others use the accent"
    requirement: PREV-05
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_case_twin_row", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_identical_existing_item_has_no_row", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_rows_order", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_row_overwrite_style_and_hint", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_section_hidden_without_conflicts", status: pass}
    human_judgment: false
  - id: D5
    description: "With 3 conflicts and 6 footprints at 900x600 the left pane scrolls vertically, nothing is wider than the viewport, rows are 8 px apart; the rows look right with real fonts and scaling"
    requirement: PREV-05
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflicts_overflow_geometry", status: pass}
    human_judgment: true
    rationale: "The offscreen platform has no fonts (widths and glyphs are exaggerated), so the geometry test proves containment but not the look; owner UAT in 05-11 at 100% and 150% scaling"
  - id: D6
    description: "Double-click or Enter on a Files row opens the read-only content view: planned text, a diff, size and SHA-256, or the unchanged line; hashing and diffing run on a TaskWorker"
    requirement: PREV-01
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_content_view_new_footprint_row", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_content_view_modified_library_diff", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_content_view_model_row_hash_on_worker", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_content_view_unchanged_row", status: pass}
    human_judgment: false
  - id: D7
    description: "A conflict row (left pane or preview) opens existing against incoming; an undecided conflict uses a one-off build with Overwrite for that key and never replaces the shown plan or its generation; a refused one-off shows the plan's first error"
    requirement: PREV-01
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_view_unresolved_uses_one_off_build", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_view_resolved_overwrite_no_extra_build", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_view_from_preview_section", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_view_model_and_symbol", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_conflict_view_refused_one_off_shows_the_error", status: pass}
    human_judgment: false
  - id: D8
    description: "Preview rebuilds and one-off conflict builds share one serial queue: at most one build_plan runs at any time"
    requirement: PREV-01
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_builds_never_overlap", status: pass}
    human_judgment: false

duration: 75min
completed: 2026-10-22
status: complete
---

# Phase 5 Plan 10: Per-item Conflicts and the Content View Summary

**One `ConflictRow` per conflict (Overwrite / Rename / Skip, nothing pre-selected, no bulk control) with choices kept by `Conflict.key` across rebuilds, and a read-only content view opened from file rows and conflicts, where an undecided conflict's incoming side comes from a one-off `build_plan` on a serial build queue shared with the preview rebuilds.**

## Performance

- **Duration:** about 75 min
- **Completed:** 2026-10-22
- **Tasks:** 2 (both TDD), 4 task commits (RED and GREEN per task) plus the SUMMARY commit
- **Files:** 1 created, 4 modified; `conflict_row.py` +309, `import_dialog.py` +266/-15, tests +503, `form.py` +10

## Accomplishments

- **Conflict rows (PREV-05, D-12).** `ConflictRow` shows the kind in bold, `{name} — {Conflict.existing}` elided in the middle with the full text as tooltip, and `Needs a choice` (bold AMBER) while undecided. Three checkable buttons live in a `QButtonGroup(setExclusive(False))` with manual exclusivity: clicking an unchecked one unchecks the others and emits `choice_changed(key, Resolution)`; clicking the checked one re-checks it and emits nothing. Overwrite is red when checked, Rename and Skip use the accent; the hint line carries the UI-SPEC copy (Overwrite in ERROR colour, the others MUTED). A 4 px left bar is AMBER until the conflict is settled, then SUCCESS. The row is focusable and a double click, or Enter / Space on the row itself, emits `activated(key)`.
- **Rename (D-12).** Choosing Rename reveals a line edit (min width 160, in a `QFrame#fieldFrame`) pre-filled with `Conflict.suggested_name`; its text is passed exactly as typed as `rename_to`, rebuilds after the 300 ms debounce, and an empty name shows `Enter a new name for {kind} {name}` and the amber frame (the `rename:{key}` target registered in 05-09's dicts).
- **Choices by key (D-14a, T-05-31).** `form.carry_resolutions(old, plan)` keeps only keys the plan still has. The dialog owns `self._resolutions`, prunes it after each accepted plan and updates rows in place by key (focus, cursor and typed text survive); a vanished key drops its row, choice and reason targets; a new key starts unresolved. Switching the library or renaming the footprint never carries an Overwrite to another item. Install stays blocked until every row is decided (the existing `blocking_reasons`, now with real `conflict:{key}` targets that focus the Overwrite button).
- **Content view (D-08).** `PreviewTree.row_activated` and `ConflictRow.activated` open `ContentViewDialog`: planned text for a new file, a unified diff for a modified `.kicad_sym` / `.kicad_mod`, size and SHA-256 for a STEP file, `This file is unchanged by the install.` for an `=` row. `op_content` / `unchanged_content` run on a `TaskWorker` through two new `ImportCore` fields, so nothing is hashed or diffed on the GUI thread.
- **Existing against incoming (Pitfall 2).** For a conflict already set to Overwrite the op comes from the current plan, no extra build. For an undecided one the dialog queues a one-off `build_plan` with `Resolution("overwrite")` for that key added, finds the footprint / model / symbol-library op (`incoming_op`), and shows `{rel} - existing vs incoming`. The one-off plan is read only for that op: `_plan`, `_plan_gen` and `_gen` are untouched. A refused one-off shows the plan's first ERROR text as an error view.
- **One serial build queue (T-05-32).** `_pump_builds` starts the latest queued rebuild, then one-off jobs in order, and only when neither `_building` nor `_oneoff` runs. Jobs carry a package session number, so a result for a package that was changed meanwhile is dropped; `open_path`, `_on_change` and `_shutdown` wait for both workers before the package closes (WR-04).

## TDD Gate Compliance

| Task | RED commit | GREEN commit |
|------|-----------|--------------|
| 1 | ffb3ef8 `test(05-10)` | 328ae86 `feat(05-10)` |
| 2 | 6d0bdc9 `test(05-10)` | afee5aa `feat(05-10)` |

RED evidence (manual semantic assessment; `gsd_run` is not available in the worktree, so `check tdd-red-evidence` was not run):
- Task 1: 13 failed, 1 passed (an existing blocking-reasons test matched the `-k` filter). `test_carry_resolutions` failed with `ImportError: cannot import name 'carry_resolutions'`; the dialog tests got as far as building a real plan with real clashes and then failed on `AttributeError: 'ImportDialog' object has no attribute '_conflict_rows'`, and the widget test on the missing `conflict_row` module. This is the missing-API RED accepted in 05-01, 05-05, 05-07 and 05-09 for new surface; the clash fixtures themselves were exercised.
- Task 2: 10 failed. Two failed with `TypeError: ImportCore.__init__() got an unexpected keyword argument 'op_content'` / `'unchanged_content'`; the other eight timed out in `waitUntil` (30 s each) because no content view ever opened, which is the planned assertion failing.
- No refactor commit.

## Task Commits

1. Task 1 RED `ffb3ef8`, GREEN `328ae86`: conflict rows, `carry_resolutions`, Conflicts section
2. Task 2 RED `6d0bdc9`, GREEN `afee5aa`: content view wiring, one-off conflict builds, serial build queue

## Files Created/Modified

- `kicad_lib_manager/widgets/conflict_row.py` - `ConflictRow` and a private middle-eliding label
- `kicad_lib_manager/importer/form.py` - `carry_resolutions`
- `kicad_lib_manager/widgets/import_dialog.py` - Conflicts section, `_sync_conflicts` and row add / remove, `_on_conflict_choice` / `_on_conflict_rename`, `incoming_op`, `_pump_builds` / `_start_oneoff` / `_on_oneoff_done`, `_on_preview_row_activated`, `_open_conflict_view`, `_run_content` / `_show_content`
- `tests/test_import_form.py` - `test_carry_resolutions`
- `tests/test_import_dialog.py` - 15 conflict-row tests and 10 content-view tests; the helpers `write_clashes`, `clash_dialog`, `preview_row`, `wait_view`

## Decisions Made

See `key-decisions` above. The two worth a review: the rename field is on its own line under the buttons (a deviation from "to the right of the buttons", forced by the 365 px pane), and a Skip on the first footprint removes the model conflict from the plan (planner behaviour: the kept footprint does not link the incoming model), so that row disappears.

## Deviations from Plan

### Auto-fixed Issues

None - no Rule 1-3 fixes were needed in files outside the plan.

### Plan wording adjusted

- **Rename field position.** UI-SPEC and the plan say the field is "to the right of the buttons"; it is on a second line under them so the row never exceeds the left pane (see key-decisions). Min width 160, pre-fill and debounce are as specified.
- **Empty Rename hint.** For a Rename with no name the hint reads `Rename - enter the name to install the {kind} as; the existing {kind} stays untouched` instead of an `install as  and ...` sentence with a blank, and the left bar stays amber until a name exists.
- **`test_conflict_choice_rebuilds_and_resolves`** follows the planner: after Skip on the footprint the model conflict is gone from the plan, so the Overwrite-on-model step is exercised after switching the footprint to Overwrite.
- `requirements-completed` lists PREV-05 and PREV-01 as the plan declares; `requirements.mark-complete` was not run here (worktree mode, `gsd_run` unavailable), so the orchestrator should mark them after the merge (PREV-01 is shared with other plans of the phase).

**Total deviations:** 0 auto-fixed, 3 wording / layout adjustments. **Impact:** none on behaviour covered by the plan's truths.

## Issues Encountered

- The Custom submodule is not initialised in the worktree, so `custom_copy`-based tests skip here. All 25 new tests build their own layout (`item_layout` / `write_custom_layout`) and run. Skip counts in this worktree: `tests/test_import_dialog.py` 11 (all pre-existing `custom_copy` tests), `tests/test_install_plan.py` 13, whole suite 78. The orchestrator should run the full suite on the merged tree.
- Full suite in the worktree: 1502 passed, 78 skipped, 4 failed. The four failures are baseline: `test_install_plan.py::test_version_real_cli_into_20241209`, `::test_library_real_cli_new_header`, `::test_noop_second_plan_after_normalised_apply` and `test_kicad_cli.py::test_real_cli_upgrades_ul_symbol_deterministically` (KiCad 10 kicad-cli writes symbol format 20251024).
- The RED run of Task 2 took four minutes because eight tests waited out their 30 s `waitUntil`.

## Known Stubs

None.

## Threat Flags

None. The one-off build is read-only and goes through the same `core.build_plan` and kicad-cli cache as the rebuilds, serialised by the queue (T-05-32); no new caller of `sync_kicad_path_vars` and no write outside the plan's own install path.

## Next Phase Readiness

- 05-11 can run owner UAT on the Conflicts section and the content view (look at 100% and 150% scaling, keyboard use of the row: Tab to the row, Enter / Space opens the view).
- `ImportCore` now has `op_content` and `unchanged_content`; the post-install work can keep using the same fake-able core.

## Self-Check: PASSED

- `kicad_lib_manager/widgets/conflict_row.py` exists; `def carry_resolutions(` is in `kicad_lib_manager/importer/form.py`; `def _open_conflict_view(`, `row_activated.connect`, `op_content(`, `unchanged_content(` and `ContentViewDialog(` are in `kicad_lib_manager/widgets/import_dialog.py`.
- No "overwrite all" / "skip all" text outside comments in `conflict_row.py` or `import_dialog.py`.
- Commits `ffb3ef8`, `328ae86`, `6d0bdc9`, `afee5aa` are on the branch (`git rev-list --count` from the base: 4).
- Plan verification: `tests/test_import_dialog.py tests/test_import_content.py tests/test_preview_tree.py tests/test_import_form.py` pass; `tests/test_install_plan.py` shows only the three baseline failures.

---
*Phase: 05-import-ui-and-post-install*
*Completed: 2026-10-22*
