---
phase: 13-atomic-migration-and-kicad-setup
plan: 14
subsystem: migration
tags: [migration, atomic-libraries, qt, pyside6, tdd, taskworker, draft]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "plan 13-06's migration architecture (planner.build_migration_plan, gate.check_plan/end_state_context, precheck.check_custom) and plan 13-08's draft service (draft.py, settings.migration_draft_file)"
provides:
  - "kicad_lib_manager/widgets/migration_dialog.py: MigrationCore + MigrationDialog - the migration window's refusal page, grouped part list, detail pane (library/names/fields/field-changes/texts), failure strip, Run gating and the draft"
affects: ["13-15 (footprint/model/family controls, Files tab)", "13-16 (Run itself, Result view, commit step)", "13-17 (wiring into the main window)"]

actuals:
  tokens: 12500
  tasks: 3
  commits: 6
  plan_head_before: f4d420948be3dc49328bf83823b58f3e7dbd8018
  plan_head_after: 979ed781556b42c67f863f830b88aacb387dcf0f

tech-stack:
  added: []
  patterns:
    - "MigrationCore (frozen dataclass, real functions as defaults) is the test seam, mirroring import_dialog.py's ImportCore"
    - "Every slow call (check_custom, read_inventory, prepare_context, build_plan, check_plan, save_draft) runs on a TaskWorker reused from import_dialog.py, tagged with a generation number so an edit mid-rebuild supersedes the stale result instead of racing it onto screen"
    - "Two independent single-shot QTimers (debounced rebuild at 300ms, debounced draft save at 800ms) restarted on every edit via one _update_choice helper"
    - "Tooltips carrying vendor/file text are html.escape'd before setToolTip (Qt's rich-text sniffer would otherwise render raw markup); plain-text widgets (QLineEdit, QTreeWidgetItem/QListWidgetItem text) need no escaping since Qt never treats their text as rich"

key-files:
  created:
    - kicad_lib_manager/widgets/migration_dialog.py
    - tests/test_migration_dialog.py

key-decisions:
  - "MigrationCore.check_plan is a local wrapper (_check_plan) that calls gate.end_state_context then gate.check_plan in one step; the dataclass field list in the plan's artifact table names only 'check_plan', so the window never builds an AtomicContext itself"
  - "The Library combo's item list is existing_libraries() over the plan's own distinct target_library values, plus the selected part's own source_library when it is not already one of them (D-03's 'current library one pick away')"
  - "The Field changes list reuses no code from importer/form.py's private _plain(): a small local _plain_field/_field_change_text pair renders 'Removed MF' / 'Value: old -> new' wording, since importer.form._plain is not exported and the migration dialog's wording only needs to avoid literal ki_ prefixes, not form.py's full reason-sentence grammar"
  - "Generated-text overrides (Keywords, Footprint description, Footprint tags) are QPlainTextEdit per D-11's explicit instruction, unlike import_dialog.py's QLineEdit for the same three fields in the importer - the two windows diverge here on purpose"
  - "The part tree's status column and detail-pane description both resolve through the owner's live PartChoice override before falling back to the raw on-disk InventoryPart field, so a 'changed since the draft' part still shows the owner's saved edit, never the stale disk value"

patterns-established:
  - "A widget module that is not under kicad_lib_manager/importer/ is outside tests/test_importer_layering.py's ALLOWED registry and free to import any importer submodule directly; only the importer package's own internal layering is guarded"

requirements-completed: [MIG-01, MIG-02]

coverage:
  - id: D1
    description: "Opening the migration window runs the clean check off the GUI thread; a dirty Custom shows every uncommitted file by name with a Check again button and nothing else"
    requirement: "MIG-01"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_dirty_custom_shows_refusal"
        status: pass
    human_judgment: false
  - id: D2
    description: "A clean Custom shows a part tree grouped by target Atomic_ library (undecided group first), each part with a pass mark, its failure count, and its old library when it moves"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_parts_grouped_by_target"
        status: pass
    human_judgment: false
  - id: D3
    description: "The detail pane edits the library (with suggestion tooltip, badge and name_verdict note), symbol name, MPN, Manufacturer, Datasheet, Description, shows Value read-only, lists field changes in plain words, and regenerates Keywords/Footprint description/Footprint tags"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_library_picker_lists_atomic_libraries_and_current"
        status: pass
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_field_edits_reach_the_plan"
        status: pass
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_field_changes_listed"
        status: pass
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_texts_regenerate"
        status: pass
    human_judgment: false
  - id: D4
    description: "The failure strip lists every gate StripLine as a clickable row; clicking selects the part and focuses the control the line targets; Run stays disabled until the strip is empty and the plan matches the current edit generation"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_run_disabled_until_strip_empty"
        status: pass
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_strip_click_selects_part_and_focuses_field"
        status: pass
    human_judgment: false
  - id: D5
    description: "No slow call (check_custom, read_inventory, prepare_context, build_plan, check_plan) ever runs on the GUI thread"
    requirement: "MIG-01"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_long_work_runs_off_the_gui_thread"
        status: pass
    human_judgment: false
  - id: D6
    description: "Vendor/file text is never rendered as rich text: plain widgets show it literally, and tooltips are html.escape'd"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_vendor_text_is_plain"
        status: pass
    human_judgment: false
  - id: D7
    description: "Every edit saves the migration draft on a worker after a debounce; a failed save shows one WARNING in the status line and never raises"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_edits_save_the_draft"
        status: pass
    human_judgment: false
  - id: D8
    description: "Reopening restores the draft's choices into the first build_plan call and the detail pane; a part changed on disk since the draft is flagged in the tree and the detail pane while keeping the saved values; an unreadable/foreign draft starts clean with one status-line note"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_reopen_restores_the_draft"
        status: pass
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_changed_since_draft_is_marked"
        status: pass
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_unreadable_draft_starts_clean"
        status: pass
    human_judgment: false
  - id: D9
    description: "Closing while any worker runs (precheck, load or rebuild) returns at once and hides the window once the worker ends, without destroying a running thread"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog.py#test_close_while_planning_waits_without_blocking"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 14: Migration window part 1 - refusal, part list, detail pane, strip and Run gating Summary

**`widgets/migration_dialog.py` opens the migration to a refusal page or a part tree grouped by target Atomic_ library, with a detail pane (library picker with suggestion tooltip and badge, names, fields, field changes, regenerable texts), a clickable failure strip that gates Run, and a debounced draft that survives closing the window - every slow call runs off the GUI thread on a generation-tagged TaskWorker reused from import_dialog.py.**

## Performance

- **Duration:** ~70 min
- **Started:** 2026-11-11
- **Completed:** 2026-11-11
- **Tasks:** 3 completed
- **Files created:** 2

## Accomplishments

- `MigrationCore` wraps the migration services (`check_custom`, `read_inventory`, `detect_tools`, `prepare_context`, `build_plan`, `check_plan`, `fingerprints`, `load_draft`, `save_draft`, `clear_draft`, `changed_parts`, `draft_file`, `kicad_running`) behind a frozen dataclass test seam, with the real functions as defaults - `check_plan`'s default is a small local wrapper that also builds the plan's `AtomicContext` via `gate.end_state_context` so the window never does
- `MigrationDialog` opens to a checking page, a refusal page (every uncommitted file listed, `Check again` re-runs the check, no inventory read happens first), a loading page, or the edit page: a failure strip (`QListWidget`), a `QSplitter` with the part tree (grouped by target library, undecided group first, pass mark or failure count per part, "from `<old library>`" when a part moves, "changed since the draft" when flagged) on the left and a `QTabWidget` with the Part detail pane on the right
- The detail pane: an editable Library `QComboBox` (existing Atomic_ libraries plus the part's own current library, a `library_badge`, the suggestion as its tooltip, a `name_verdict` reason note, the typed text kept verbatim for the planner to judge), Symbol name, MPN, Manufacturer, Datasheet, Description, read-only Value, a plain-worded Field changes list, and Keywords/Footprint description/Footprint tags as `QPlainTextEdit`s with Regenerate buttons that clear the override back to the generated text
- The failure strip's lines are clickable: each selects its part and focuses the control its `StripLine.target` names; Run stays disabled until the strip is empty and the displayed plan's generation matches the latest edit
- Every edit restarts two independent debounced timers: one rebuilds the plan+gate on a worker (latest edit wins via a generation tag), the other saves the migration draft on a worker; a failed save shows one WARNING in the status line without raising
- Reopening restores the saved draft's choices into the very first `build_plan` call; `changed_parts` flags surface in the tree row and a detail-pane note while keeping the saved values in the boxes; an unreadable or foreign draft starts clean with one status-line note, and a missing draft (`draft.none`) stays silent
- Closing the window while any worker (precheck, load or rebuild) is still running returns immediately and hides the window once the worker ends, via the same `done()`/`closeEvent()` pattern as `import_dialog.py`, never destroying a running thread

## Task Commits

Each task was committed atomically; Task 1 is `type="tracer"` (single commit); Tasks 2 and 3 carry `tdd="true"` (RED test commit, then GREEN feat commit):

1. **Task 1: tracer - window shell, refusal, grouped tree, strip, Run gating** - `9ae6dbb` (feat)
2. **Task 2 RED** - `32c81e0` (test) - 5 new tests; 4 fail genuinely against the Task 1 shell (missing `_library_note`/`_field_changes_list`/`_text_edits`/escaped tooltips), 1 (`test_field_edits_reach_the_plan`) already passes against Task 1's minimal field wiring
3. **Task 2 GREEN** - `a2280f0` (feat) - library picker (badge/suggestion/verdict), field changes list, generated texts with Regenerate, html-escaped tooltips
4. **Task 3 RED** - `7516e21` (test) - 5 new tests; 2 fail genuinely (no draft-save timer, no `_changed_label`), 3 (`test_reopen_restores_the_draft`, `test_unreadable_draft_starts_clean`, `test_close_while_planning_waits_without_blocking`) already pass against Task 1's load handling and `done()`/`closeEvent()` logic
5. **Task 3 GREEN** - `f564323` (feat) - debounced draft-save timer, `_changed_label`, CHANGED_MARK in the tree
6. **Refactor** - `979ed78` (refactor) - hoisted the `RepoLayout` import to module level, shortened one overlong line; no behavior change

**Plan metadata:** committed together with this SUMMARY (worktree mode excludes STATE.md/ROADMAP.md; the orchestrator updates those centrally after merge).

## Files Created/Modified

- `kicad_lib_manager/widgets/migration_dialog.py` - `MigrationCore`, `MigrationDialog`, constants (`WINDOW_TITLE`, `RUN_TEXT`, `CHECK_AGAIN_TEXT`, `UNDECIDED_GROUP`, `CHANGED_MARK`, `PASS_MARK`, `_REBUILD_DELAY_MS`, `_DRAFT_DELAY_MS`), local helpers (`_plural`, `_plain_field`, `_field_change_text`, `_check_plan`)
- `tests/test_migration_dialog.py` - fake-core fixture (`core_with`, `make_dialog`) and hand-built `Inventory`/`PartPlan`/`MigrationPlan`/`GateOutcome` helpers (`_empty_inventory`, `_inventory_with_part`, `_part`, `_plan_for`); 15 behavior tests across the three tasks

## Decisions Made

See `key-decisions` in the frontmatter: the `check_plan` wrapper, the library combo's item set, the local field-change wording helper (not reusing `importer.form`'s private `_plain`), `QPlainTextEdit` for the three generated texts (per D-11, diverging from `import_dialog.py`'s `QLineEdit`), and resolving status/description display through the live choice override before the raw on-disk field.

## Deviations from Plan

None - plan executed exactly as written, Rules 1-3.

### TDD note (not a Rule 1-4 deviation - documented for transparency)

As with plan 13-08's tracer, several of Task 2's and Task 3's own listed behavior tests passed immediately against the prior task's already-production-quality implementation, rather than failing first:
- Task 2: `test_field_edits_reach_the_plan` (the minimal Task 1 field wiring already routed MPN/Manufacturer/Datasheet/Description/Symbol name edits into `choices.parts` and already showed the planned MPN read-only in Value).
- Task 3: `test_reopen_restores_the_draft`, `test_unreadable_draft_starts_clean` and `test_close_while_planning_waits_without_blocking` (Task 1's `_on_loaded` draft handling and `done()`/`closeEvent()` busy-wait already covered these cases).

Each RED commit was still created and still genuinely failed on at least one of its listed tests (4/5 for Task 2, 2/5 for Task 3) before the matching GREEN commit, verified with the plan's own `<verify>` pytest command at each step; the TDD Gate Compliance section below accounts for every test.

---

**Total deviations:** 0 Rule 1-4 auto-fixes.
**Impact on plan:** None - every acceptance criterion and the plan's own verification command pass unchanged.

## TDD Gate Compliance

| Task | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| Task 1 (tracer) | - | `9ae6dbb` (feat, single tracer commit) | - | Pass |
| Task 2 | `32c81e0` (test) - 4/5 new tests genuinely fail (AttributeError/AssertionError), 1 already passes (see TDD note) | `a2280f0` (feat) - all 10 tests in the file pass | not needed | Pass |
| Task 3 | `7516e21` (test) - 2/5 new tests genuinely fail (TimeoutError/AttributeError), 3 already pass (see TDD note) | `f564323` (feat) - all 15 tests in the file pass | `979ed78` (refactor) - import hoist + line-length cleanup, re-verified against all 15 tests | Pass |

RED evidence: `gsd_run check tdd-red-evidence` was unavailable in this isolated worktree (no `.claude/gsd-core/` present); RED was established by running the plan's own `<automated>` pytest command directly before each GREEN commit and inspecting the failures captured above (genuine `AttributeError`/`AssertionError`/`TimeoutError` on the planned behavior, never a collection or import error).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 13-15 extends `widgets/migration_dialog.py` with the footprint, model and family controls and the Files tab; it can build on `self._targets`, `self._field_edits`/`self._text_edits`, `_framed`, `_update_choice` and the rebuild/draft timer pair without touching this plan's structure.
- Plan 13-16 owns Run itself, the Result view and the commit step; `is_running()`/`is_committing()` are already present as overridable seams (both return `False` here), and `MigrationDialog.migrated`/`generate_requested`/`setup_chooser_requested` signals are declared but unemitted, ready for that plan to wire.
- Plan 13-17 wires this dialog into the main window; `help_requested` is the only signal this plan emits (on F1/Help).
- No blockers.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/widgets/migration_dialog.py
- FOUND: tests/test_migration_dialog.py
- FOUND: commit 9ae6dbb (Task 1)
- FOUND: commit 32c81e0 (Task 2 RED)
- FOUND: commit a2280f0 (Task 2 GREEN)
- FOUND: commit 7516e21 (Task 3 RED)
- FOUND: commit f564323 (Task 3 GREEN)
- FOUND: commit 979ed78 (refactor)
- `python -m pytest tests/test_migration_dialog.py tests/test_migration_draft.py tests/test_plain_names.py tests/test_layering.py -q` -> 59 passed
- All plan acceptance criteria greps (`class MigrationDialog`, `class MigrationCore`, `RUN_TEXT = "Run Migration"`, `deleteLater` count 0, `name_verdict(`/`suggestion_text(`/`library_badge(`, `save_draft`/`changed_parts`/`CHANGED_MARK`) confirmed present as required
