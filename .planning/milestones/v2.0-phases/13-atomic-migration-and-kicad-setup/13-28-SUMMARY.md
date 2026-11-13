---
phase: 13-atomic-migration-and-kicad-setup
plan: 28
subsystem: ui
tags: [pyside6, migration-dialog, destination, generate-tables, window-modal, help-dialog]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "13-27 Pin Atomic Libraries in KiCad rename (PIN_ACTION_TEXT), the migration Result view and the Generate Tables mirror pattern"
provides:
  - "Result view Destination row (DESTINATION_LABEL, read-only field, BROWSE_TEXT button, amber note) and a status line for Generate / pin outcomes"
  - "MigrationDialog.destination_changed / set_destination / set_result_status and MigrationCore.pick_destination"
  - "MainWindow _set_dest_items (existing-folder filter), _use_destination, _mirror_destination, _set_migration_status, _generate_outcome"
  - "Generate Tables early stops return their Issue (codes generate.no_scan / no_destination / destination_missing / nothing_selected)"
affects: [phase-13-verification, 13-VALIDATION, user-guide]

actuals:
  tokens: 9000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "The dialog never owns the Destination: it shows what the main window holds and asks for changes through a signal, the main window echoes the result back"
    - "Outcome mirror: _generate_outcome(issues, dest) -> (text, Severity) feeds a Result-view status line, same pattern as the import flow's _tables_outcome"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/migration_dialog.py
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/widgets/help_dialog.py
    - CLAUDE.md
    - tests/test_migration_dialog_run.py
    - tests/test_main_window_migration.py
    - tests/test_main_window.py
    - tests/test_help_dialog.py

key-decisions:
  - "Option A (owner decision 2026-11-12): show and change the Destination in the Result view, main window stays the single source of truth; the migration window stays window-modal (dialog.open() kept, asserted by test)"
  - "No automatic folder prompt on Generate: a blank or missing folder is shown up front with an amber note and Browse...; Generate's own refusal is mirrored"
  - "The history filter is display-only (an unplugged drive may come back); the saved dest_history is never rewritten"
  - "Mirror the Destination before setting the status after Generate, because a changed folder text clears the status line"

patterns-established:
  - "Early stops of a log-writing action return their Issue (same text, same level) so callers can mirror them without changing the log"

requirements-completed: [MIG-04, TBL-02, DOC-01]

duration: not recorded (session interrupted by an API 403 and resumed)
completed: 2026-11-13
plan_head_before: a1749f70918f7bc55c2f7a5c141ac305ebd2d0f1
plan_head_after: a372f7bd8d4e11617ccd94a57034db6555ae09ce
commits: 4
status: complete

coverage:
  - id: D1
    description: "The migration Result view shows the Destination with Browse..., an amber note for a blank or missing folder, and the Generate / pin outcome under the buttons"
    requirement: MIG-04
    verification:
      - kind: unit
        ref: "tests/test_migration_dialog_run.py#test_result_view_shows_destination_and_browse_emits"
        status: pass
      - kind: unit
        ref: "tests/test_migration_dialog_run.py#test_result_status_follows_severity"
        status: pass
    human_judgment: false
  - id: D2
    description: "Browse... in the Result view changes the main window's Destination, Generate Tables writes there and its outcome is shown in the Result view, end to end through the real window pair"
    requirement: TBL-02
    verification:
      - kind: integration
        ref: "tests/test_main_window_migration.py#test_real_result_view_changes_the_destination_end_to_end"
        status: pass
      - kind: integration
        ref: "tests/test_main_window_migration.py#test_destination_changed_in_the_result_view_is_used_by_generate"
        status: pass
    human_judgment: false
  - id: D3
    description: "Blank, missing and deferred Generate (and a blank-Destination pin action) are reported in the Result view; the window stays window-modal"
    requirement: MIG-04
    verification:
      - kind: integration
        ref: "tests/test_main_window_migration.py#test_blank_destination_is_reported_in_the_result_view"
        status: pass
      - kind: integration
        ref: "tests/test_main_window_migration.py#test_deferred_generate_is_reported_in_the_result_view"
        status: pass
      - kind: integration
        ref: "tests/test_main_window_migration.py#test_migration_window_is_window_modal"
        status: pass
    human_judgment: false
  - id: D4
    description: "At start the Destination box offers only folders that still exist; the saved history is not rewritten"
    requirement: TBL-02
    verification:
      - kind: unit
        ref: "tests/test_main_window.py#test_destination_history_skips_folders_that_no_longer_exist"
        status: pass
    human_judgment: false
  - id: D5
    description: "User Guide Migrating and Generating pages and CLAUDE.md describe the Result-view Destination and the skipped stale folders"
    requirement: DOC-01
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_migrating_page"
        status: pass
    human_judgment: false
  - id: D6
    description: "Owner's end-of-phase check in the main checkout (app starts, Skip button, Pin menu entry, a deleted Destination folder is no longer offered after restart)"
    verification: []
    human_judgment: true
    rationale: "Needs the real KiCad checkout C:/Git_Repo_Clones/Kicad_Libraries and a restart of the app; the plan marks it as the owner's human-check after the merge"
---

# Phase 13 Plan 28: Result-view Destination Summary

**The migration Result view now shows the folder the library tables go to with a Browse... button, mirrors Generate Tables' outcome next to the buttons, and the Destination box no longer restores deleted folders, all while the window stays window-modal (gap G-13-1-g, option A).**

## Performance

- **Duration:** not recorded; the session was cut off by an API 403 after commit a372f7b and resumed in the same worktree
- **Tasks:** 3 (all complete)
- **Files modified:** 8
- **Commits:** 4 (`9174c26` test, `c7c2958` feat, `600a940` feat, `a372f7b` docs)

## Accomplishments

- Result view: `Library tables go to:` row with a read-only field and `Browse...`, an amber note for a blank or missing folder, and a status line under Generate Tables / the pin action coloured by severity (SUCCESS / WARNING / ERROR / INFO).
- `MigrationDialog.destination_changed(str)`, `set_destination`, `set_result_status` and `MigrationCore.pick_destination` (default `_pick_destination_folder`, faked in tests). The dialog never stores the Destination; the main window's `_on_migration_destination_changed` -> `_use_destination` (history, combo, tables-found log) echoes it back.
- `_on_generate` early stops build an `Issue` (`generate.no_scan`, `generate.no_destination`, `generate.destination_missing`, `generate.nothing_selected`) with the same text and level as before, log it and return it; `_generate_outcome` turns the issues into the Result-view line ("Library tables written to ...", "... already up to date", the first error, or the no-destination / nothing-selected warning).
- A deferred Generate shows "Generate Tables runs when the rescan finishes" in the Result view and is replaced by the real outcome; a blank Destination also reports the pin action's refusal there.
- `_set_dest_items` filters blank and deleted history entries (display only), falls back to the repository folder; used by the restore, Generate and Browse paths, replacing three duplicated combo-refill blocks.
- User Guide (Migrating "Afterwards", Generating Destination step) and CLAUDE.md (Startup, Migrate bullets, window-modal note) updated; `NEXT_STEPS_TEXT` now starts with checking the folder; class docstring no longer says "non-modal".

## Task Commits

1. Task 1 (tracer): `9174c26` test (RED: 7 target tests failing on the planned behaviour: ImportError DESTINATION_LABEL, missing `set_destination`, unknown `pick_destination`, empty fake records, old next-steps text) then `c7c2958` feat (GREEN).
2. Task 2: `600a940` feat with `test_destination_history_skips_folders_that_no_longer_exist` (RED observed before the filter: 4 items instead of 2; the test and the filter were committed together). The blank / deferred / modality tests of Task 2 were written in the RED commit `9174c26` and pass since `c7c2958`.
3. Task 3: `a372f7b` docs (RED observed: `DESTINATION_LABEL` missing from the Migrating page; assertion and docs committed together).

## TDD Gate Compliance

Plan type is `execute` with `tdd="true"` tasks. Task 1 has a separate `test(13-28)` RED commit before its `feat(13-28)` GREEN commit. Tasks 2 and 3 saw their RED state locally but the test and the implementation share one commit each (`600a940`, `a372f7b`); this is a minor departure from the two-commit pattern, noted here. No REFACTOR commit was needed.

## Verification

- Task 1 verify (`test_migration_dialog_run`, `test_main_window_migration`, `test_migration_dialog`, `test_main_window`, `test_checkout_warning`, `test_annotations_resolve`): 130 passed after GREEN.
- Task 2 verify (`test_main_window`, `test_main_window_migration`, `test_main_window_import`, `test_checkout_warning`, `test_main_window_chooser`): 167 passed.
- Task 3 verify (`test_help_dialog`, `test_docs_atomic`): 73 passed.
- Plan `<verification>` file list (all ten files): 273 passed, 4 warnings (pre-existing QDragEnterEvent deprecation), 0 failed.
- Acceptance greps: signal, both methods, `destination_changed.connect(self._on_migration_destination_changed)`, `dialog.open()` kept, 5 `generate.*` codes, `_set_dest_items(load_dest_history())`, `is_dir()` filter, `DESTINATION_LABEL` in help page and test, "still exist" in CLAUDE.md all found; "Non-modal migration window" no longer present.
- **Full suite:** run by the orchestrator post-merge (see wave 4 gate). Not run here by instruction.
- **Owner `<human-check>` (Task 3):** pending owner verification after the merge, in the main checkout `C:/Git_Repo_Clones/Kicad_Libraries` (G-13-1-a/b/c/g checks listed in the plan).

## Deviations from Plan

None in behaviour. The plan said Task 1's `_set_dest_items` "may simply refill" and Task 2 adds the filter; that is how it was done (filter added in `600a940`).

## Issues Encountered

- The executor session was interrupted by an API 403 after commit `a372f7b` (docs task done, before the SUMMARY). It was resumed in the same worktree: HEAD identity and ancestry of the base were re-checked, Task 2's tests were confirmed present and committed, every named-file verify command was re-run (273 passed) and this SUMMARY was written. No work was lost or redone.
- Two Bash commands were refused by the worktree guard for being too complex (heredoc append, compound git); the work was redone with plain commands and the Edit tool.

## Known Stubs

None.

## Threat Flags

None. T-13-76 to T-13-80 mitigations are in place and tested (Destination always shown and refreshed, window-modal asserted, history filter, isolated QSettings / patched REPO_ROOT / fake migration core; nothing read from or written to the live Custom/, KiCad config or the main checkout).

## Self-Check: PASSED

- Modified files exist in the worktree; commits `9174c26`, `c7c2958`, `600a940`, `a372f7b` are ancestors of HEAD; `a1749f7` (base) is an ancestor of HEAD; worktree clean before this SUMMARY; no pytest/python process left running.
