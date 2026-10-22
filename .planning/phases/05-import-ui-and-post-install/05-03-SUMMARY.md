---
phase: 05-import-ui-and-post-install
plan: 03
subsystem: ui
tags: [pyside6, qtreewidget, theme, contrast, tdd]

requires:
  - phase: 02-hardening-existing-code
    provides: LibraryTableWidget, LogPanel, 02-UI-REVIEW findings
provides:
  - widgets/theme.py single source of Phase 5 colours, spacing, fonts and shared QSS
  - AMBER #8A5200 warnings in the log panel and both library trees
  - LibraryTableWidget.reveal(sym_rel_path, fp_rel_path) for the post-install step
  - populate guard, visible Status column and Status tooltips in the library trees
affects: [05-import-dialog, 05-post-install, help_dialog, main_window]

actuals:
  tokens: 9000
  tasks: 2
  commits: 5
plan_head_before: 543f75e8d932da33cca1d1a4a942e1e9fa127343
plan_head_after: 42a664c7887a6e43448128d1a2d4a369de8f9e90

tech-stack:
  added: []
  patterns:
    - "Qt-free constants module (widgets/theme.py) imported by widgets"
    - "_updating guard with previous/try/finally for every programmatic tree change"

key-files:
  created:
    - kicad_lib_manager/widgets/theme.py
  modified:
    - kicad_lib_manager/widgets/log_panel.py
    - kicad_lib_manager/widgets/library_table.py
    - tests/test_library_table_widget.py
    - tests/test_main_window.py

key-decisions:
  - "populate keeps its body in a new _populate_trees helper so the _updating guard is a plain try/finally in populate"
  - "Status tooltip is the status word for OK/Missing FP rows and the collision tip (plus '; Missing FP') for collided rows"
  - "Tests in test_main_window.py now compare against COLORS['warning'] instead of a literal"

patterns-established:
  - "Colours come from widgets/theme.py; tests read them through theme or COLORS, never literals"

requirements-completed: [POST-01]

coverage:
  - id: D1
    description: "theme.py defines the UI-SPEC colours, spacing, fonts, PRIMARY_BUTTON_QSS and FIELD_FRAME_QSS with no Qt import"
    requirement: POST-01
    verification:
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_theme_constants_match_ui_spec"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_theme_imports_no_qt"
        status: pass
    human_judgment: false
  - id: D2
    description: "Warnings in the log panel and library trees use AMBER #8A5200"
    verification:
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_log_panel_warning_is_amber"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_collided_symbol_is_marked_with_collision_status_and_tooltip"
        status: pass
    human_judgment: false
  - id: D3
    description: "populate always resets _updating; symbol tree Status column visible at default size; Status tooltips"
    verification:
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_populate_resets_updating_after_error"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_symbol_tree_columns_fit"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_status_cell_tooltip"
        status: pass
    human_judgment: false
  - id: D4
    description: "reveal() expands, selects and scrolls to a library in both trees without touching check state"
    requirement: POST-01
    verification:
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_reveal_makes_rows_current_and_visible"
        status: pass
    human_judgment: false
  - id: D5
    description: "Visual appearance of the resized columns at the real default window size"
    verification: []
    human_judgment: true
    rationale: "Offscreen tests prove geometry; whether the layout reads well on screen is a visual judgment"

duration: 25min
completed: 2026-10-22
status: complete
---

# Phase 5 Plan 03: Shared Theme and Library Tree Fixes Summary

**Qt-free `widgets/theme.py` as the single colour/spacing/QSS source, amber `#8A5200` warnings in log and trees, a try/finally `populate`, a visible Status column with tooltips, and `LibraryTableWidget.reveal()` for the post-install step**

## Performance

- **Duration:** about 25 min
- **Tasks:** 2 (both TDD)
- **Files modified:** 5 (1 created)

## Accomplishments
- `theme.py` carries every UI-SPEC constant exactly, with `PRIMARY_BUTTON_QSS` and `FIELD_FRAME_QSS`, and imports no Qt (verified in a fresh `-I` subprocess).
- `COLORS["warning"]` and both tree warning brushes use `AMBER`; the `font-size: 13px` label styles became a 10pt bold `QFont`.
- `populate` can no longer leave `_updating` stuck (02-UI-REVIEW fix 1); symbol tree columns are 240/100/stretch/contents and the footprint tree 240/100/contents so Status shows at the default size (fix 2); Status cells carry tooltips.
- `reveal()` expands the source group, makes the row current and scrolls to it, under the `_updating` guard, skipping unknown or `None` paths silently.

## Task Commits

1. **Task 1: theme module and amber** - `48d9a75` (test, RED), `227a1bd` (feat, GREEN)
2. **Task 2: populate guard, columns, tooltips, reveal** - `6429006` (test, RED), `1fb414a` (feat, GREEN)
3. **Follow-up fix** - `42a664c` (fix: test_main_window colour assertions)

**Plan metadata:** committed separately as `docs(05-03)`.

## TDD Notes

- RED 1: new theme tests fail because `kicad_lib_manager.widgets.theme` did not exist (ImportError / NameError in the two modified collision assertions). Semantic assessment: the target tests ran and failed for the intended reason (planned new module absent). The formal `gsd_run check tdd-red-evidence` classifier was not run; assessment is manual.
- RED 2: `_updating` stayed `True` after a raising populate (`assert True is False`); column modes, tooltips and `reveal` assertions failed against the old code. No unexpected greens.

## Files Created/Modified
- `kicad_lib_manager/widgets/theme.py` - colour, spacing, font and QSS constants
- `kicad_lib_manager/widgets/log_panel.py` - `COLORS` built from theme constants
- `kicad_lib_manager/widgets/library_table.py` - amber, heading font, header resize modes, populate guard, tooltips, `reveal()`
- `tests/test_library_table_widget.py` - six new tests plus amber assertions
- `tests/test_main_window.py` - three colour assertions now read `COLORS["warning"]`

## Decisions Made
- `populate` delegates to `_populate_trees` so the guard is a simple try/finally; the body is unchanged.
- Tooltip text for non-collided Status cells is the status word ("OK", "Missing FP").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_main_window.py asserted the old `#cc7700` literal**
- **Found during:** Task 2 full-suite run
- **Issue:** Three assertions in `tests/test_main_window.py` (lines 239, 374, 608) hard-coded `#cc7700`, failing after the amber change. The file is outside the plan's `files_modified` (plan 05-01 also edits it), so only those three lines and one import were touched to keep merge conflicts minimal.
- **Fix:** Compare against `COLORS["warning"]` imported from `log_panel`.
- **Files modified:** tests/test_main_window.py
- **Committed in:** 42a664c

---

**Total deviations:** 1 auto-fixed (1 bug). **Impact:** necessary for the suite; small merge-conflict risk with 05-01 in `tests/test_main_window.py` (import block and three one-line assertions).

## Issues Encountered
- Full suite: 4 failures, all pre-existing and unrelated (real kicad-cli on this machine reports symbol version 20251024, tests expect 20241209): `tests/test_install_plan.py::test_version_real_cli_into_20241209`, `::test_library_real_cli_new_header`, `::test_noop_second_plan_after_normalised_apply`, `tests/test_kicad_cli.py::test_real_cli_upgrades_ul_symbol_deterministically`. Out of scope; not fixed.
- Full suite result in this worktree: 1258 passed, 66 skipped, 4 failed. The skips come from uninitialised submodules (Custom, WurthElektronik) plus one symlink-privilege skip; the orchestrator should re-run on the merged tree.
- `kicad_lib_manager/widgets/help_dialog.py:163` still contains a `#CC7700` span (UI-SPEC says it should use AMBER). It is outside this plan's files; left for the plan that owns the help dialog.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `theme` constants and `reveal()` are ready for the import dialog and post-install flow.
- `main_window.py` should adopt `PRIMARY_BUTTON_QSS` for Generate Tables (owned by 05-01).

## Self-Check: PASSED

- theme.py FOUND; commits 48d9a75, 227a1bd, 6429006, 1fb414a, 42a664c present on the branch.
- Acceptance greps: no Qt import in theme.py, no `CC7700` in log_panel.py or library_table.py, no `font-size: 13px`, no `setColumnWidth(2, 300)`.
- `pytest tests/test_library_table_widget.py tests/test_log_panel.py tests/test_models.py tests/test_main_window.py` passes.

---
*Phase: 05-import-ui-and-post-install*
*Completed: 2026-10-22*
