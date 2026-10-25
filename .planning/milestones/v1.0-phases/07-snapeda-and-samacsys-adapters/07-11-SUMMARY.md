---
phase: 07-snapeda-and-samacsys-adapters
plan: 11
subsystem: ui
tags: [pyside6, qheaderview, qtreewidget, preview, gap-closure]

requires:
  - phase: 07-snapeda-and-samacsys-adapters
    provides: Field changes preview rows (long monospace Detail text) that exposed the column layout defect
provides:
  - PreviewTree with an Interactive Item column, a stretched Detail column and a one-time initial width
  - Narrow-tree clamp so both columns keep MIN_COLUMN_WIDTH and fit the viewport
  - Amended Phase 5 UI contract (05-UI-SPEC.md :315 and :511)
affects: [phase-07 UAT test 7, import dialog preview]

actuals:
  tokens: 9000
  tasks: 3
  commits: 4
plan_head_before: dc5af4a256c52a8334a1aa73f1db71d1976fffac
plan_head_after: 1ecf7780a67beef55588ea4affe0d9676aded5a9

tech-stack:
  added: []
  patterns:
    - "Column widths owned by the tree: set once on first real width (showEvent/resizeEvent), render() never touches them"
    - "Clamp via header.sectionResized for index 0 plus resizeEvent, re-entrancy safe because the clamped width no longer exceeds the limit"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/preview_tree.py
    - tests/test_preview_tree.py
    - tests/test_import_dialog.py
    - .planning/phases/05-import-ui-and-post-install/05-UI-SPEC.md

key-decisions:
  - "Path-rewrite Detail text is not capped: Detail now fits the viewport and elides with the full text in its tooltip, so no path is hidden (PREV-01)"
  - "One constant MIN_COLUMN_WIDTH = 120 serves as header minimumSectionSize and clamp margin"

patterns-established:
  - "Dialog and widget tests share a drag_divider(header, dx) QTest press/move/release helper on header.viewport()"

requirements-completed: [INTK-03, INTK-04]

coverage:
  - id: D1
    description: "Preview divider between Item and Detail is draggable (Item Interactive, Detail stretched last section)"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_preview_tree.py#test_columns_interactive_and_detail_stretches"
        status: pass
      - kind: unit
        ref: "tests/test_preview_tree.py#test_divider_drag_moves_item_and_survives_render"
        status: pass
    human_judgment: false
  - id: D2
    description: "Dragged width survives render(), rebuilds, typing a Value and dialog resize"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_preview_tree.py#test_initial_item_width_once"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_preview_column_drag_survives_rebuild"
        status: pass
    human_judgment: false
  - id: D3
    description: "SnapEDA preview keeps both columns >= 120 px and inside the viewport at 900 and 1400 px dialog width; a narrowing tree shrinks Item before Detail"
    requirement: INTK-04
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_preview_columns_fit_at_900_and_1400"
        status: pass
      - kind: unit
        ref: "tests/test_preview_tree.py#test_item_clamped_when_tree_narrows"
        status: pass
    human_judgment: false
  - id: D4
    description: "Owner UAT test 7 on the real display: columns read well, divider feels right, long Field changes rows elide in Detail"
    verification: []
    human_judgment: true
    rationale: "Real-display font metrics and DPI scaling differ from the offscreen test platform; visual adequacy needs the owner"
  - id: D5
    description: "05-UI-SPEC.md :315 and :511 describe the new column contract"
    verification:
      - kind: other
        ref: "grep -c 'amended 2026-10-24' on 05-UI-SPEC.md (both amendments present)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-24
status: complete
---

# Phase 7 Plan 11: Preview Column Resize (G-07-7) Summary

**PreviewTree now has a draggable Item column (55% of the tree on first show, kept across rebuilds), a stretched eliding Detail column, and a clamp that keeps both columns at least 120 px and inside the viewport.**

## Performance

- **Duration:** about 25 min
- **Started:** 2026-10-24T11:40:00Z (approx.)
- **Completed:** 2026-10-24T12:07:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Header sections are Interactive, `stretchLastSection(True)`, `minimumSectionSize(MIN_COLUMN_WIDTH)`; the root cause (Stretch + ResizeToContents, nothing draggable, Detail pinned wider than the viewport) is gone.
- Item width is applied once in `_apply_initial_width()` from `showEvent`/`resizeEvent`; `render()` never sets a width, so a user drag survives rebuilds, typing a Value and dialog resizes.
- `_clamp_item_width()` (resizeEvent plus `sectionResized` for index 0) shrinks Item when the tree narrows or a drag would push Detail under 120 px; growing the dialog gives the extra width to Detail.
- 05-UI-SPEC.md :315 and :511 amended with the new contract.

## Task Commits

1. **Task 1: Tracer, SnapEDA preview fits at 900 and 1400 px with an Interactive Item column** - `83875f8` (feat)
2. **Task 2: divider drag, kept width, clamp (TDD)**
   - RED - `ed812a0` (test)
   - GREEN - `899fd79` (feat)
3. **Task 3: UI-SPEC amendment** - `1ecf778` (docs)

**Plan metadata:** committed with this SUMMARY (docs: complete plan)

## TDD Gate Compliance

Task 2 is the only `tdd="true"` task. RED commit `ed812a0` precedes GREEN commit `899fd79`.

- **RED:** `test_item_clamped_when_tree_narrows` failed on the planned assertion (`500 <= 398 - 120`: Item kept 500 px in a 398 px viewport). Semantic assessment: the target test executed and failed on the clamp assertion for the intended reason (no clamp existed), not on a setup or import fault. The other four Task 2 tests (`test_columns_interactive_and_detail_stretches`, `test_initial_item_width_once`, `test_divider_drag_moves_item_and_survives_render`, `test_preview_column_drag_survives_rebuild`) passed at RED because the Task 1 tracer already implemented the Interactive header and one-time width; they characterise that behaviour and are not claimed as RED evidence. The `gsd_run check tdd-red-evidence` classifier was not run (no gsd_run in the worktree); the evidence above is from the pytest output.
- **GREEN:** all 14 targeted tests pass; the plan's wider run (`tests/test_preview_tree.py tests/test_import_dialog.py` minus the two real-Custom ids) gives 172 passed, 9 skipped (Custom submodule absent in the worktree), 2 deselected. The 7-test verify set was run three times in a row, stable.
- **REFACTOR:** none needed.

## Files Created/Modified
- `kicad_lib_manager/widgets/preview_tree.py` - `ITEM_SHARE`, `MIN_COLUMN_WIDTH`, Interactive header, `_apply_initial_width`, `_clamp_item_width`, `showEvent`/`resizeEvent` overrides
- `tests/test_preview_tree.py` - 4 new widget tests and the `drag_divider` helper
- `tests/test_import_dialog.py` - `test_preview_columns_fit_at_900_and_1400`, `test_preview_column_drag_survives_rebuild`, `drag_divider` helper
- `.planning/phases/05-import-ui-and-post-install/05-UI-SPEC.md` - the two amended lines

## Decisions Made
- Path-rewrite Detail text stays uncapped (the plan listed a cap as optional): Detail now fits the viewport and elides with the full text in its tooltip, so cutting a path would only hide what PREV-01 requires the preview to show.
- Clamping uses both `resizeEvent` and the header's `sectionResized(0)` so a drag stops where Detail would fall under 120 px.

## Deviations from Plan

None - plan executed exactly as written. The plan's `./env/Scripts/python.exe` commands were run with the orchestrator checkout's interpreter (`C:/Git_Repo_Clones/Kicad_Libraries-importer/env/Scripts/python.exe`) from the worktree root, as the environment notes direct.

## Issues Encountered
None. The full-suite phase gate (about 6 minutes) was not run here; the orchestrator runs it after merge. Tests run offscreen, so real-display font metrics (the UAT 734 px Detail on Windows) are covered only by the `sizeHintForColumn(1) > viewport` precondition at 900 px, which held.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Ready for owner UAT test 7 on the real display (see the plan's human-check): drag the divider, narrow and widen the Import part window, type in Value and confirm the width holds.

## Self-Check: PASSED

- Files exist: preview_tree.py, test_preview_tree.py, test_import_dialog.py, 05-UI-SPEC.md (modified, all present).
- Commits `83875f8`, `ed812a0`, `899fd79`, `1ecf778` are ancestors of HEAD.
- Acceptance criteria of all three tasks re-run: PASS.

---
*Phase: 07-snapeda-and-samacsys-adapters*
*Completed: 2026-10-24*
