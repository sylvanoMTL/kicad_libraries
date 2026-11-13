---
phase: 09-atomic-rule-check-and-scan-detection
plan: 02
subsystem: ui
tags: [pyside6, qtreewidget, dataclasses, atomic-check, change-highlight]

requires:
  - phase: 08-scan-and-table-hardening
    provides: "rel_path-keyed LibraryTableWidget, ScanResult/SymbolLibrary/FootprintLibrary models, theme tokens AMBER and ACCENT"
provides:
  - "Qt-free result contract in models.py: FixSpec, Violation, Finding, SymbolEntry, ChangedFootprint, STATUS_NEW, STATUS_CHANGED, plus defaulted SymbolLibrary.atomic/symbols/check_problem and FootprintLibrary.changed"
  - "Symbol child rows in the library tree: amber failing rows with warning icon, rule count and per-rule tooltip, library 'N of M fail' count"
  - "New/Changed ACCENT highlights for symbol and footprint child rows, combined 'Changed . 2 rules' status, No symbols / Could not check library states, auto-expand of libraries with something to show"
  - "LibraryTableWidget.symbol_activated(rel_path, symbol name) double-click signal and the _rich_tip escaping helper"
affects: [09-atomic-check, 09-change-detection, phase-10-fix-dialog, phase-11, phase-13]

actuals:
  tokens: 7500
  tasks: 3
  commits: 5
plan_head_before: 45caf99bddaf5a8c864dbe8263c194d45e93a850
plan_head_after: 05ed066ad2cf1489c65aae842a0bed8bf35906a9

tech-stack:
  added: []
  patterns:
    - "Result contract as frozen Qt-free dataclasses in models.py, stored on tree rows via Qt.ItemDataRole.UserRole"
    - "Display-only child rows: ItemIsUserCheckable cleared, never setCheckState, early return in _on_sym_item_changed"
    - "All scan-derived tooltip text goes through _rich_tip (html.escape per line, <qt> wrapper)"
    - "QTreeWidgetItem.setExpanded only after the item is attached to the tree"

key-files:
  created:
    - tests/test_library_table_atomic.py
  modified:
    - kicad_lib_manager/models.py
    - kicad_lib_manager/widgets/library_table.py
    - tests/test_models.py

key-decisions:
  - "Library row Status precedence: Collision, Could not check, 'N of M fail', Missing FP, No symbols, OK; the atomic count is appended to the tooltip when Collision wins"
  - "Footprint library rows keep their Status text; changed footprints are child rows in ACCENT"
  - "Finding-only symbol rows read OK, are not auto-expanded, but are double-clickable and show the finding in the tooltip"

patterns-established:
  - "Child rows of the symbol tree are identified by UserRole holding SymbolEntry (symbol tree) or ChangedFootprint (footprint tree)"

requirements-completed: [SCAN-01, SCAN-02]

coverage:
  - id: D1
    description: "Failing symbols show as amber child rows with warning icon, rule count, one tooltip line per broken rule, and the library row reads '<failing> of <total> fail'"
    requirement: "SCAN-01"
    verification:
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_failing_rows_are_amber_with_warning_icon_and_a_rule_count"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_library_status_counts_failing_symbols"
        status: pass
    human_judgment: false
  - id: D2
    description: "New and changed symbols and footprints are highlighted in ACCENT with New/Changed status; failing plus changed stays one amber row with a combined status"
    requirement: "SCAN-02"
    verification:
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_failing_and_changed_symbol_is_one_amber_row_with_both_facts"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_changed_footprints_get_child_rows_in_order"
        status: pass
    human_judgment: false
  - id: D3
    description: "Only libraries holding a failing, new or changed child are expanded after populate"
    requirement: "SCAN-01"
    verification:
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_only_libraries_with_something_to_show_are_expanded"
        status: pass
    human_judgment: false
  - id: D4
    description: "Child rows can never change library selection or footprint check states; Select All and Deselect All act on library rows only"
    requirement: "SCAN-01"
    verification:
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_selection_is_unchanged_when_a_child_row_changes"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_select_all_and_deselect_all_act_on_library_rows_only"
        status: pass
    human_judgment: false
  - id: D5
    description: "Double-clicking a symbol row with rule problems or findings emits symbol_activated(rel_path, name)"
    verification:
      - kind: unit
        ref: "tests/test_library_table_atomic.py#test_double_click_on_a_row_with_rule_problems_emits_symbol_activated"
        status: pass
    human_judgment: false
  - id: D6
    description: "Visual appearance of the amber and accent rows, warning icons and auto-expansion in the real window"
    verification: []
    human_judgment: true
    rationale: "Offscreen tests assert colours, icons and expanded flags, not whether the result reads well; the real tree has not been looked at yet"

duration: 25min
completed: 2026-10-26
status: complete
---

# Phase 9 Plan 02: Result contract and library tree marks Summary

**Qt-free FixSpec/Violation/Finding/SymbolEntry/ChangedFootprint contract in models.py, rendered in the library tree as amber failing symbol rows with per-rule tooltips, ACCENT New/Changed rows for symbols and footprints, a 'N of M fail' library count, auto-expansion and a symbol_activated double-click signal**

## Performance

- **Duration:** ~25 min
- **Completed:** 2026-10-26T12:21Z
- **Tasks:** 3 (1 tracer, 2 TDD)
- **Files modified:** 4 (1 created)

## Accomplishments

- Shared result contract that the atomic check, change detection and fix dialog (phases 10, 11, 13) consume: all new `SymbolLibrary`/`FootprintLibrary` fields are defaulted, so existing constructors and scan fakes keep working.
- Failing symbols are visible: one inert child row per symbol, warning icon plus AMBER, status "1 rule" / "n rules", tooltip with every broken rule on its own line, library row "2 of 3 fail".
- New and changed symbols and footprints show in ACCENT with the word New or Changed; a symbol that is failing and changed is one amber row reading "Changed . 2 rules" with both facts in the tooltip.
- Only libraries with a failing, new or changed child open on their own; "No symbols" and "Could not check" library states exist.
- Child rows cannot alter selection (T-09-03) and all scan text in tooltips is escaped (T-09-04); both pinned by tests.

## Task Commits

1. **Task 1: Result contract and failing symbol rows (tracer)** - `11b6b43` (feat)
2. **Task 2 RED: failing tests for highlights, status and auto-expand** - `f4dfc19` (test)
3. **Task 2 GREEN: New/Changed highlights, combined status, auto-expand** - `e0f8996` (feat)
4. **Task 3 RED: failing tests for selection safety and symbol_activated** - `9397186` (test)
5. **Task 3 GREEN: child rows out of selection, symbol_activated** - `05ed066` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## TDD Gate Compliance

Task 1 is a tracer (single production commit with its tests). Tasks 2 and 3 followed RED then GREEN; no REFACTOR commit was needed.

- **Task 2 RED (`f4dfc19`):** 9 of 17 tests failed on assertions for the planned behaviour (for example `'OK' == 'Changed'`, `'OK' == 'No symbols'`, empty tooltip where the finding text is expected); the 8 Task 1 tests still passed. Semantic assessment: failures are the intended assertions, not import, fixture or syntax faults.
- **Task 3 RED (`9397186`):** 4 of 24 tests failed. The selection test failed on its assertion (a hand-ticked footprint was cleared by a child-row edit: the real source-wide recalculation bug). The three `symbol_activated` tests failed with `AttributeError: no attribute 'symbol_activated'`, the expected failure for a signal that does not exist yet. Semantic assessment: the target tests executed and failed for the planned reason. The `check tdd-red-evidence` classifier was not run (plain pytest output is not a format it supports).

## Files Created/Modified

- `kicad_lib_manager/models.py` - result contract dataclasses, status words, new defaulted library fields
- `kicad_lib_manager/widgets/library_table.py` - child rows, `_rich_tip`, `_make_symbol_row`, `_make_footprint_row`, `_colour_row`, auto-expand, child-row guard in `_on_sym_item_changed`, `symbol_activated` and `_on_sym_item_double_clicked`
- `tests/test_library_table_atomic.py` - 24 widget tests (new)
- `tests/test_models.py` - contract field order, frozen, `failing`, backward-compatible defaults

## Decisions Made

- Status precedence on the library row is Collision, Could not check, "N of M fail", Missing FP, No symbols, OK (extends the plan's flagged assumption with the two new states).
- A finding-only row reads OK and is not auto-expanded (plan expands only for failing or status), but is still double-clickable and shows the finding.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] setExpanded had no effect before the item joined the tree**
- **Found during:** Task 2 (GREEN)
- **Issue:** The plan says to call `item.setExpanded(True)` after adding children; doing so before `group.addChild(item)` left the library collapsed.
- **Fix:** Call `setExpanded` after the library item is attached to its group, for both symbol and footprint trees.
- **Files modified:** kicad_lib_manager/widgets/library_table.py
- **Verification:** `test_only_libraries_with_something_to_show_are_expanded` passes
- **Committed in:** `e0f8996`

---

**Total deviations:** 1 auto-fixed (1 bug in the planned call order)
**Impact on plan:** No scope change.

## Issues Encountered

- Full `pytest` with no path filter ran longer than the 2 minute tool limit in this worktree (the orchestrator checkout holds the submodules; Custom-backed tests skip here). The plan verification set (atomic, widget, models, main_window, layering tests: 107 tests) passes; the orchestrator's post-merge run covers the whole suite.

## Known Stubs

None.

## Threat Flags

None. T-09-03 and T-09-04 from the plan's register are mitigated and tested.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The atomic check (plan 09-01 sibling work and follow-ups) can fill `SymbolLibrary.atomic/symbols/check_problem` and `FootprintLibrary.changed`; the tree renders them with no further widget change.
- Whoever opens the fix dialog connects to `LibraryTableWidget.symbol_activated(rel_path, symbol name)`.
- Visual review of the amber/accent rows in the real window is still open (D6).

---
*Phase: 09-atomic-rule-check-and-scan-detection*
*Completed: 2026-10-26*
