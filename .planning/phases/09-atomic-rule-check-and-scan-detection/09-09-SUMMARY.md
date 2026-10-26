---
phase: 09-atomic-rule-check-and-scan-detection
plan: 09
subsystem: ui
tags: [python, pyside6, qtreewidget, pytest, uat, atomic-check, gap-closure]

requires:
  - phase: 09-atomic-rule-check-and-scan-detection
    provides: "09-02 symbol rows, SymbolEntry.violations/findings and symbol_activated; 09-08 build_atomic_uat scratch helper"
provides:
  - "LibraryTableWidget._make_problem_row: display-only problem rows (amber, warning icon) and note rows (plain, information icon) under each symbol row"
  - "Symbol rows start collapsed; problem and note rows span the full width; double-clicking one emits symbol_activated for its parent symbol"
  - "Library tree help page describing problem and note rows"
  - "tests/test_atomic_uat.py _edit_first_symbol: edits Description, then Datasheet, or adds a Datasheet, so the scratch build works on the live Custom/"
affects: [phase-09 re-test of UAT test 1, phase-10, phase-13 migration]

actuals:
  tokens: 24000
  tasks: 3
  commits: 6
plan_head_before: ede4f72e8db1bc677b19a0de7972c8ed38978cf4
plan_head_after: e68164b9ece6688c98c1b3c2c99afce609dcd721

tech-stack:
  added: []
  patterns:
    - "Rows that stand for a model object's detail store that detail object (Violation or Finding) in UserRole; the double-click handler steps to item.parent() to reach the entry"
    - "setFirstColumnSpanned is called only after the row's ancestors are in the tree, because it does nothing before that"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/library_table.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_library_table_atomic.py
    - tests/test_main_window.py
    - tests/test_help_dialog.py
    - tests/test_atomic_uat.py

key-decisions:
  - "Problem and note texts are Violation.text and Finding.text unchanged; no rewording or prefix (owner decision, D-01)"
  - "Note rows set no brush, so they show default text colour; the information icon marks them (D-03, no new colour literal)"
  - "The UAT helper tries Description before Datasheet because Description is what the owner edited by hand in UAT"

requirements-completed: [SCAN-01, SCAN-03]

coverage:
  - id: D1
    description: "Each symbol with rule problems has one amber problem row per violation (in order) then one plain note row per finding, with the existing texts, display only"
    requirement: "SCAN-01"
    verification:
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_note_rows_follow_problem_rows_in_order"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_problem_row_is_amber_with_warning_icon_and_inert"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_note_row_is_plain_with_the_information_icon"
        status: pass
    human_judgment: false
  - id: D2
    description: "Symbol rows start collapsed with their Status count; libraries with something to show still expand; problem rows span the full width"
    requirement: "SCAN-01"
    verification:
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_symbol_rows_start_collapsed_and_libraries_still_expand"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_problem_and_note_rows_span_the_full_width"
        status: pass
    human_judgment: true
    rationale: "Whether the three-level tree reads clearly to the owner needs the UAT test 1 re-test"
  - id: D3
    description: "Problem and note rows never change library selection or footprint check states, and their tooltips are escaped"
    requirement: "SCAN-01"
    verification:
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_problem_row_change_leaves_selection_unchanged"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_select_all_gives_problem_rows_no_check_state"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_problem_and_note_tooltips_are_escaped"
        status: pass
    human_judgment: false
  - id: D4
    description: "Double-clicking a problem or note row opens Check Atomic Parts on its parent symbol, end to end in the real main window"
    requirement: "SCAN-03"
    verification:
      - kind: integration
        ref: "tests/test_main_window.py#test_atomic_problem_row_double_click_opens_dialog_on_its_symbol"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_double_click_on_a_note_row_emits_its_parent_symbol"
        status: pass
    human_judgment: false
  - id: D5
    description: "The help page describes problem and note rows in plain words"
    requirement: "SCAN-01"
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_library_tree_explains_the_atomic_marks"
        status: pass
    human_judgment: false
  - id: D6
    description: "The UAT helper edits a property the first symbol has (Description, then Datasheet) or adds a Datasheet, keeping line endings, so it no longer crashes on a symbol without a Datasheet"
    requirement: "SCAN-03"
    verification:
      - kind: unit
        ref: "tests/test_atomic_uat.py#test_edit_first_symbol_edits_description_when_there_is_no_datasheet"
        status: pass
      - kind: unit
        ref: "tests/test_atomic_uat.py#test_edit_first_symbol_adds_a_datasheet_when_it_has_neither"
        status: pass
      - kind: unit
        ref: "tests/test_atomic_uat.py#test_edit_first_symbol_keeps_crlf_line_endings_when_it_adds_a_datasheet"
        status: pass
    human_judgment: true
    rationale: "The opt-in live build on the owner's real Custom/ was not run in this worktree (deferred to the orchestrator, see Deviations)"
---

# Phase 9 Plan 09: Component-level problem rows and UAT helper fix Summary

**Library tree gets the component level the owner asked for: each failing symbol expands into one amber row per broken rule and one plain row per note, double-clicking either opens Check Atomic Parts on that symbol, and the UAT scratch helper now survives a symbol with no Datasheet.**

## Performance

- **Tasks:** 3 (all `tdd="true"`; Task 1 is the tracer)
- **Files modified:** 6 (2 source, 4 test)
- **Commits:** 6 code commits (RED and GREEN for each task), plus this SUMMARY commit

## Accomplishments

- Problem rows: `LibraryTableWidget._make_problem_row` builds a display-only row (no checkable flag, no check state) holding the `Violation` or `Finding` in `UserRole`, the text unchanged, an escaped tooltip, and the warning icon with AMBER (violations) or the information icon with no brush (findings).
- `_make_symbol_row` adds violation rows first (list order) then finding rows; symbol-row text, styling and tooltip are untouched, so UAT test 3's hover behaviour is kept.
- `_span_problem_rows` calls `setFirstColumnSpanned(True)` right after the library item is added to its group, so long rule text uses the full width.
- No `setExpanded` on symbol rows, so a library shows its component list with each Status count; the library auto-expand condition is unchanged (D-06). Expand All and Collapse All reach the problem rows.
- `_on_sym_item_double_clicked` steps from a Violation or Finding row to its parent symbol row and reuses the existing checks, so the signal carries (library rel_path, parent symbol name).
- Help page "Atomic parts" now explains Status counts, collapsed parts, problem rows and note rows, and says to double-click the part or a problem row.
- UAT helper `_edit_first_symbol` replaces `_edit_first_datasheet`: edits Description, then ki_description, then Datasheet, or adds a hidden Datasheet (mirroring the private `atomic_fixes._insert_property`) with the file's own line endings and BOM kept. The printed checklist is updated for the G-09-1 re-test.

## Task Commits

1. Task 1 RED: `a256b70` test(09-09): add failing tests for problem rows under failing symbols
2. Task 1 GREEN: `de6561f` feat(09-09): show broken rules as problem rows under failing symbols
3. Task 2 RED: `c75f628` test(09-09): add failing tests for note rows, spanning, collapsed symbols and help text
4. Task 2 GREEN: `4844290` feat(09-09): add note rows, full-width problem rows and component-level help
5. Task 3 RED: `afe6fe4` test(09-09): add failing tests for the UAT helper's three edit paths
6. Task 3 GREEN: `e68164b` feat(09-09): UAT helper edits a property the symbol has, or adds a Datasheet

## TDD Gate Compliance

- RED (tasks 1 and 2): the target tests failed on assertions for the planned behaviour (missing child rows, `AttributeError` on a missing problem row, missing help phrases). One new test per task (`test_symbol_rows_keep_their_status_styling_and_tooltip`, `test_problem_row_change_leaves_selection_unchanged`) passed at RED on purpose: they pin existing behaviour that must not regress.
- RED (task 3): the four helper tests failed with `NameError: _edit_first_symbol` because the helper did not exist yet. This is a name-resolution failure rather than an assertion failure; semantic assessment: the target tests did execute and failed for the intended reason (the planned function was absent). `gsd_run check tdd-red-evidence` was not run.
- GREEN and the tracer gate: after Task 1 the tracer `<verify>` (`tests/test_library_table_atomic.py tests/test_library_table_widget.py tests/test_main_window.py`, 95 passed) was re-run end to end before expansion. No REFACTOR commits were needed.

## Deviations from Plan

### Deferred

**1. Opt-in live build of Task 3 deferred to the orchestrator: owner importing into live Custom/**
- **Found during:** Task 3
- **Issue:** The worktree has no checked-out `Custom/` submodule, and the owner is using the part importer on the main checkout, so the live `Custom/` must not be read through git commands or touched from this worktree. `tests/test_atomic_uat.py::test_uat_atomic_scratch` therefore skips with "set KICAD_ATOMIC_UAT_DIR..." here (and would skip with "Custom submodule not checked out" if set).
- **What was verified instead:** the default `tests/test_atomic_uat.py` run (7 passed, 1 skipped, the opt-in test) and the three helper paths (Description edited, Datasheet edited, Datasheet added, plus CRLF) on synthetic fixtures.
- **Command for the orchestrator to run on the merged branch, from the repository root, once the owner has finished importing:**
  ```
  git -C Custom status --porcelain > "$LOCALAPPDATA/Temp/g091_custom_before.txt"
  KICAD_ATOMIC_UAT_DIR="$LOCALAPPDATA/Temp/kicad_atomic_uat_g091" env/Scripts/python.exe -m pytest tests/test_atomic_uat.py::test_uat_atomic_scratch -rs -q -s
  git -C Custom status --porcelain | diff - "$LOCALAPPDATA/Temp/g091_custom_before.txt"
  ```
  Expected: `1 passed` (not skipped) and an empty diff. The scratch repo path is printed by the test (`UAT scratch repo: ...`); leave it for the owner's G-09-1 re-test.

### Auto-fixed Issues

None. A test-helper slip during Task 3 (`_property_names` read `.value` on a `Node`, which has `.text`) was fixed within the task before the GREEN commit.

**Total deviations:** 1 deferred verification step, 0 auto-fixed. **Impact:** none on the code; the live-Custom check remains to be run.

## Verification

- `pytest tests/test_library_table_atomic.py tests/test_library_table_widget.py tests/test_main_window.py tests/test_help_dialog.py tests/test_atomic_uat.py tests/test_layering.py`: 135 passed, 1 skipped (the opt-in test).
- Plan gate `pytest -m "not wurth"`: 2309 passed, 26 skipped, 3 deselected. Every skip is environmental to this worktree (Custom submodule not checked out, licence-restricted vendor samples not present in `downloaded_examples/`, the opt-in UAT builders).
- Acceptance greps: `SP_MessageBoxInformation` and `setFirstColumnSpanned(True)` present in library_table.py; zero quoted colour literals outside comments; `one row for each problem` appears once in help_dialog.py; `-k "note or span or collapsed or problem"` gave 13 passed; `-k atomic` in test_main_window.py gave 7 passed.
- The `git -C Custom status` and `WurthElektronik` status checks were not run in this worktree (submodules are not checked out here, by instruction). No file under `Custom/` or `WurthElektronik/` was written.

## Known Stubs

None.

## Threat Flags

None. T-09-24 (escaped tooltips) and T-09-25 (inert rows, selection safety) are covered by tests; T-09-26 is covered by the destination checks that were already in place and by the deferred live check above.

## Self-Check: PASSED

- Modified files exist: library_table.py, help_dialog.py, test_library_table_atomic.py, test_main_window.py, test_help_dialog.py, test_atomic_uat.py.
- Commits a256b70, de6561f, c75f628, 4844290, afe6fe4, e68164b are on the branch.
