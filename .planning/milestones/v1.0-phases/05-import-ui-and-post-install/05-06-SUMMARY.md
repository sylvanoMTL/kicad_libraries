---
phase: 05-import-ui-and-post-install
plan: 06
subsystem: ui
tags: [pyside6, preview, unified-diff, content-view, qtreewidget, qsyntaxhighlighter]

requires:
  - phase: 05-import-ui-and-post-install
    provides: "05-01 preview.py/preview_tree.py tracer and import dialog; 05-03 widgets/theme.py"
  - phase: 04-install
    provides: "InstallPlan, FileOp, Conflict, Rename, build_plan, apply_plan"
provides:
  - "preview_sections: Files, Renames, Path rewrites, Format, Conflicts, Issues in fixed order, derived from the plan only"
  - "file_counts with unchanged files; unchanged and kept-existing rows"
  - "PreviewTree: Heading headers, tone colours, expand and scroll restore, elision, Ctrl+C, row_activated"
  - "importer/content.py: Qt-free ContentText builders (text, unified diff, binary summary) with size caps"
  - "widgets/content_view.py: ContentViewDialog and DiffHighlighter (not yet wired to rows; plan 05-10 does that)"
affects: [05-07, 05-08, 05-09, 05-10, 05-11]

plan_head_before: 42286cae6dd079828e37ea4a5ff9d6b9be6ab0c4
plan_head_after: 6fac0c190827501d75d7750081e83dd1cf112a69

actuals:
  tokens: 16000
  tasks: 3
  commits: 7

tech-stack:
  added: []
  patterns:
    - "Preview rows are a pure function of (plan, candidate, options); the only disk access is an existence check for a planned no-op file"
    - "Slot-ordered Files rows: mkdir ops, model, footprints in plan order, symbol library; an op that fits no slot is still listed"
    - "Section expand state keyed by bare section name (stored in the header's UserRole), scroll value clamped after doItemsLayout"

key-files:
  created:
    - kicad_lib_manager/importer/content.py
    - kicad_lib_manager/widgets/content_view.py
    - tests/test_import_preview.py
    - tests/test_preview_tree.py
    - tests/test_import_content.py
  modified:
    - kicad_lib_manager/importer/preview.py
    - kicad_lib_manager/widgets/preview_tree.py
    - tests/test_import_dialog.py

key-decisions:
  - "A kept symbol (symbol conflict resolved Skip) gets no Footprint and ki_fp_filters rewrite rows: its bytes are not edited, so showing 'old -> (none)' would claim a change the install does not make"
  - "A refused plan with install.version_newer_than_target shows only the Format refusal row (no 'Symbol format unknown -> unknown' row), because a refused plan carries no versions"
  - "The vendor model rename row is suppressed when the model conflict is resolved Skip (the vendor file is not copied)"
  - "Existing-file reads for diffs are capped at MAX_READ looked up at call time, so the cap is testable"
  - "PreviewTree sets NoEditTriggers (rows are read-only); QAbstractItemView's built-in Copy only copied column 0, so keyPressEvent handles Copy itself to put 'Item<TAB>Detail' on the clipboard"

patterns-established:
  - "Tone mapping success/muted/warning/error to theme colours; a conflict row's warning tone colours only its 'Needs a choice' detail"
  - "Content builders return a ContentText value; a dialog renders it and attaches the highlighter only for kind 'diff'"

requirements-completed: [PREV-01, PREV-06]

coverage:
  - id: D1
    description: "Files section lists every created, modified and unchanged file in fixed slot order with model size, mkdir rows and kept-existing detail; file_counts matches"
    requirement: PREV-01
    verification:
      - kind: unit
        ref: "tests/test_import_preview.py#test_rows_ul_first_install"
        status: pass
      - kind: unit
        ref: "tests/test_import_preview.py#test_rows_reimport_shows_unchanged"
        status: pass
      - kind: unit
        ref: "tests/test_import_preview.py#test_rows_case_twin_is_conflict_not_unchanged"
        status: pass
      - kind: unit
        ref: "tests/test_import_preview.py#test_rows_new_library_mkdir"
        status: pass
      - kind: unit
        ref: "tests/test_import_preview.py#test_rows_refused_plan"
        status: pass
    human_judgment: false
  - id: D2
    description: "Renames and Path rewrites show old to new values, and every new value equals what the planned symbol and footprint bytes contain"
    requirement: PREV-01
    verification:
      - kind: unit
        ref: "tests/test_import_preview.py#test_rewrites_match_planned_bytes"
        status: pass
      - kind: unit
        ref: "tests/test_import_preview.py#test_rewrites_skip_a_kept_symbol"
        status: pass
    human_judgment: false
  - id: D3
    description: "Format section states source and target symbol format and the kicad-cli action in all five cases"
    requirement: PREV-06
    verification:
      - kind: unit
        ref: "tests/test_import_preview.py#test_format_rows_cases"
        status: pass
    human_judgment: false
  - id: D4
    description: "Conflicts show the current choice, Issues carry glyph and severity colour including the no-3D-model warning, empty sections are hidden except Files"
    requirement: PREV-01
    verification:
      - kind: unit
        ref: "tests/test_import_preview.py#test_conflict_rows_details"
        status: pass
      - kind: unit
        ref: "tests/test_import_preview.py#test_issue_rows_no_model_warning"
        status: pass
      - kind: unit
        ref: "tests/test_import_preview.py#test_sections_order_and_empty_hidden"
        status: pass
    human_judgment: false
  - id: D5
    description: "PreviewTree renders UI-SPEC styling, restores expand state and scroll, elides in the middle with tooltips, copies a row, emits row_activated"
    requirement: PREV-01
    verification:
      - kind: unit
        ref: "tests/test_preview_tree.py#test_render_headers_and_tones"
        status: pass
      - kind: unit
        ref: "tests/test_preview_tree.py#test_render_restores_expand_and_scroll"
        status: pass
      - kind: unit
        ref: "tests/test_preview_tree.py#test_ctrl_c_copies_row"
        status: pass
      - kind: unit
        ref: "tests/test_preview_tree.py#test_row_activated_on_double_click_and_enter"
        status: pass
    human_judgment: false
  - id: D6
    description: "Content view builders: new text, unified diff with 3 lines of context, binary summary, unchanged and error texts, caps at 5000 lines or 512 KiB"
    requirement: PREV-01
    verification:
      - kind: unit
        ref: "tests/test_import_content.py#test_modified_diff_shows_only_hunk"
        status: pass
      - kind: unit
        ref: "tests/test_import_content.py#test_diff_truncated_at_5000_lines"
        status: pass
      - kind: unit
        ref: "tests/test_import_content.py#test_diff_truncated_at_512_kib"
        status: pass
      - kind: unit
        ref: "tests/test_import_content.py#test_binary_summary_new_and_modified"
        status: pass
    human_judgment: false
  - id: D7
    description: "ContentViewDialog look (800x560, Consolas 9pt, header strip, diff colours) matches the UI-SPEC"
    verification:
      - kind: unit
        ref: "tests/test_import_content.py#test_content_view_dialog"
        status: pass
      - kind: unit
        ref: "tests/test_import_content.py#test_diff_highlighter_colours_whole_lines"
        status: pass
    human_judgment: true
    rationale: "Tests assert sizes, fonts and format attributes, not how the dialog and tree look on screen; the dialog is not reachable from the UI until plan 05-10"

duration: 75min
completed: 2026-10-22
status: complete
---

# Phase 5 Plan 06: Full Preview and Content View Summary

**All six preview sections (Files incl. unchanged rows, Renames, Path rewrites, Format with the kicad-cli action, Conflicts, Issues) derived purely from the InstallPlan, a styled PreviewTree that keeps expand state and scroll across rebuilds, and a self-contained read-only content view (text, unified diff, binary hash summary) with 5000-line / 512 KiB caps.**

## Performance

- **Duration:** about 75 min
- **Completed:** 2026-10-22
- **Tasks:** 3 (all `tdd="true"`), 7 commits (RED and GREEN per task, plus one follow-up test commit)
- **Files:** 8 changed (5 created, 3 modified), none of them `import_dialog.py`

## Accomplishments

- `preview_sections` returns Files, Renames, Path rewrites, Format, Conflicts, Issues in that order, hiding empty sections except Files. Files rows follow the slot order mkdir ops, model, footprints in `plan.footprint_names` order, symbol library, and an unchanged slot renders `= path` / `unchanged` (or `unchanged (kept existing)` for a Skip). A slot with an unresolved conflict is left out (a case-twin footprint is never shown as unchanged).
- Rewrite values are the strings the planner wrote (`<Lib>:<FP>`, `${CUSTOM_3DMODEL_DIR}/<file>`, filters joined by space); `test_rewrites_match_planned_bytes` parses the planned symbol and footprint bytes and compares.
- Format row 2 covers normalise, already in target format, kicad-cli not found, newer-than-target refusal, and the fifth case (cli present but its output version differs: `⚠ Symbol merged as-is - see Issues`).
- `PreviewTree`: Heading (10pt bold) headers on SURFACE_HEADER, tone colours, bold `+`/`~` rows, monospace rewrite detail, bold amber `Needs a choice`, ElideMiddle with tooltips, no horizontal scroll bar, expand state keyed by section name, scroll restored and clamped, Ctrl+C copies `Item<TAB>Detail`, `row_activated(PreviewRow)` on double-click and Enter for non-header rows only.
- `importer/content.py` (Qt-free) and `widgets/content_view.py`: `op_content`, `diff_text`, `cap_lines`, `binary_text`, `sha256_file`, `unchanged_content`, `ContentViewDialog`, `DiffHighlighter`. Models are sized and hashed in 1 MiB chunks and never decoded; an existing file is read at most 8 MiB.

## TDD Gate Compliance

| Task | RED commit | GREEN commit |
|------|-----------|--------------|
| 1 | 06d763f `test(05-06)` | 64b2220 `feat(05-06)` |
| 2 | dbc50b3 `test(05-06)` | 65d1c3a `feat(05-06)` |
| 3 | 8afef4f `test(05-06)` | 3c931f9 `feat(05-06)` |

RED evidence (semantic assessment; `gsd_run` was not available in the worktree, so `check tdd-red-evidence` was not run and the assessment is manual):
- Task 1: 16 of 19 tests failed on the planned assertions (missing `Renames`/`Path rewrites`/`Format`/`Issues` sections as `KeyError` on the section lookup, missing model size detail, missing unchanged rows). 3 tests passed already because the tracer covered them (mkdir first, plain new rows, repeatability); they are regression guards.
- Task 2: 8 of 8 failed on the planned properties (background `#000000` instead of SURFACE_HEADER, no `row_activated` attribute, horizontal policy `AsNeeded`, clipboard held only column 0 because QAbstractItemView's built-in copy ran).
- Task 3: the module did not exist, so a plain run would only be a collection error (INVALID_RED). I put throwaway stubs in place (uncommitted, deleted before the RED commit) so the tests loaded: 18 of 21 failed on assertions against the stubs' empty values. The 3 that passed against stubs (`cap_lines` identity on a small list, no highlighter for non-diff kinds, no decode of binary) were then also green after implementation.
- A follow-up commit 6fac0c1 (`test(05-06)`) adapted a 05-01 test and added a real-Custom round trip; it is not a TDD gate.

## Task Commits

1. Task 1 RED `06d763f`, GREEN `64b2220`: preview sections
2. Task 2 RED `dbc50b3`, GREEN `65d1c3a`: PreviewTree
3. Task 3 RED `8afef4f`, GREEN `3c931f9`: content view
4. Follow-up `6fac0c1`: tracer preview test adapted, real Custom round trip added

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 05-01's `test_preview_sections_follow_plan_ops` broke when the sections grew**
- **Found during:** verification in a Custom-enabled mirror (the test skips in a bare worktree)
- **Issue:** it unpacked exactly one section (`(files,) = preview_sections(...)`) and expected model detail `"new"`
- **Fix:** read `preview_sections(...)[0]` and expect `new, ... KiB` for the model row
- **Files modified:** tests/test_import_dialog.py (outside this plan's `files_modified`, three lines; may merge-conflict with 05-05's edits to the same file, resolution is trivial)
- **Commit:** 6fac0c1

**2. [Rule 2 - Missing critical] No rewrite rows for a kept symbol**
- **Issue:** the plan says `Footprint` new value is `Lib:FP` "or (none)" and `ki_fp_filters` always appears. For a symbol conflict resolved Skip, `plan.linked_footprint` is None and the symbol bytes are untouched, so `old -> (none)` would show a change the install does not make (T-05-20 spoofing).
- **Fix:** the Footprint and ki_fp_filters rows are omitted when `plan.linked_footprint is None`; the Model row stays when a model is installed. Covered by `test_rewrites_skip_a_kept_symbol`.
- **Commit:** 64b2220

**3. [Rule 2 - Missing critical] Refused newer-than-target plan shows only the refusal row**
- **Issue:** a refused plan has `source_version` and `target_version` None, so row 1 would read `Symbol format unknown -> unknown`.
- **Fix:** Format shows only the `✖ Incoming file is newer than the library - refused` row in that case.
- **Commit:** 64b2220

**4. [Rule 3 - Blocking] Tests use synthetic Custom layouts**
- **Issue:** the plan names `custom_copy` for the UL tests, which skips in a worktree (Custom submodule not initialised) and would trip the "no SKIPPED" fail condition.
- **Fix:** UL tests build `write_custom_layout(tmp_path, [UL_LIBRARY], [UL_LIBRARY])`; one extra test (`test_rows_reimport_into_the_real_custom_library`) uses `custom_copy` and skips in a bare worktree (1 skip, passes in the mirror).
- **Commit:** 06d763f, 6fac0c1

**Additions beyond the plan:** `PreviewTree` sets `NoEditTriggers`; the vendor model rename row is suppressed for a Skip-resolved model conflict; extra tests for text-file caps, BOM stripping, the read cap, `diff_text` labels and the highlighter's format attributes.

Total deviations: 4 (1 bug, 2 missing safety/correctness, 1 blocking). Impact: none on scope.

## Verification

- Bare worktree, this plan's files: `tests/test_import_preview.py tests/test_preview_tree.py tests/test_import_content.py tests/test_importer_layering.py tests/test_layering.py` all pass; the only skip among them is the one `custom_copy` test.
- Bare worktree full suite: 1326 passed, 78 skipped, 4 failed. All 4 failures are on the known KiCad 10 baseline list (`test_version_real_cli_into_20241209`, `test_library_real_cli_new_header`, `test_noop_second_plan_after_normalised_apply`, `test_real_cli_upgrades_ul_symbol_deterministically`). `test_install_e2e.py` baseline cases were skipped in the bare worktree. Skips are Custom-submodule dependent (78 total, 1 added by this plan).
- Custom-enabled mirror (worktree code plus a copy of the main checkout's `Custom/`, in the scratchpad): `test_import_preview`, `test_preview_tree`, `test_import_content`, `test_import_dialog`, `test_importer_layering`, `test_layering`, `test_main_window_import`, `test_main_window` give 111 passed, 0 skipped.
- `test_preview_tree.py` and `test_import_content.py` ran 5 times in a row without a flake.
- Acceptance greps: `content.py` has no PySide6 import line (count 0); required literals present in `preview.py`, `preview_tree.py`, `content.py`, `content_view.py`.
- The plan's `<automated>` commands name `./env/Scripts/python.exe`, which does not exist in a worktree; the main checkout's interpreter was used by absolute path, as the orchestrator instructed.

## Known Stubs

None. `ContentViewDialog` and `row_activated` are complete components with no consumer yet by design: plan 05-10 connects them to preview and conflict rows. POST-03/POST-04 warnings are intentionally not in the preview (RESEARCH Pitfall 4).

## Threat Flags

None. T-05-19 (DoS) mitigated by the line/byte/read caps and chunked hashing, T-05-20 (spoofing) by deriving rows from the plan and the bytes-parsing guard test, T-05-21 (markup) by plain-text items, `QPlainTextEdit` and a `PlainText` header label.

## Next Phase Readiness

Plan 05-10 can wire `PreviewTree.row_activated` to `op_content(plan.ops[row.op_index], repo_root)` (file rows), `unchanged_content(row.path, repo_root)` (`=` rows, `op_index` None) and `op_content(..., conflict=True)` (conflict rows; an unresolved conflict has no op, so 05-10 must supply the existing and incoming bytes itself via `diff_text`). Run content builders on a `TaskWorker` because hashing a large STEP file is slow. `import_dialog.py` already calls `preview_sections(...)`, `file_counts(...)` and `PreviewTree.render(...)` unchanged.

## Self-Check: PASSED

- Files exist: preview.py, preview_tree.py, content.py, content_view.py, test_import_preview.py, test_preview_tree.py, test_import_content.py (all FOUND).
- Commits 06d763f, 64b2220, dbc50b3, 65d1c3a, 8afef4f, 3c931f9, 6fac0c1 are ancestors of HEAD.
