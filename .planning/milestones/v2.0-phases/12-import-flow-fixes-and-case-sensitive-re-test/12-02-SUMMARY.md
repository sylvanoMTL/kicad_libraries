---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 02
subsystem: ui
tags: [pyside6, theme, help-dialog, stylesheet, ui-review]
requires: []
provides:
  - "theme.SURFACE_BASE white token"
  - "help_dialog.CSS built from theme tokens (colours, SP_* spacing, pt font sizes)"
  - "conflict_row button styles built from theme tokens"
affects: [help_dialog, conflict_row, theme]
tech-stack:
  added: []
  patterns: ["stylesheet as '\\n'.join of f-string rules over theme constants"]
key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/theme.py
    - kicad_lib_manager/widgets/help_dialog.py
    - kicad_lib_manager/widgets/conflict_row.py
    - tests/test_help_dialog.py
key-decisions:
  - "Help body sets no font size or colour: it inherits the application font and palette"
  - "Dropped border-radius on code and overflow-x on pre (Qt rich text ignores both) and the unlisted F9A825 amber border"
requirements-completed: [UI-01]
duration: 20 min
completed: 2026-11-01
status: complete
commits: 2
plan_head_before: a03faf412e01d4fde7367bb567e2dd0bac18c828
plan_head_after: 608c7fc6acf40988e3ae9c21a7f5e42bd55487fd
actuals:
  tokens: 6000
  tasks: 2
  commits: 2
coverage:
  - deliverable: "Help stylesheet assembled from theme tokens with no hex literal, no px font size, SP_* padding"
    verification:
      - kind: test
        ref: "tests/test_help_dialog.py#test_help_css_uses_theme_tokens_only"
        status: pass
    human_judgment: false
  - deliverable: "Help headings keep distinct sizes (h2 DISPLAY_PT, h3 HEADING_PT, code/pre MONO_PT)"
    verification:
      - kind: test
        ref: "tests/test_help_dialog.py#test_help_headings_keep_their_sizes"
        status: pass
    human_judgment: false
  - deliverable: "Conflict row buttons use theme.SURFACE_BASE, no hex literal in conflict_row.py"
    verification:
      - kind: test
        ref: "tests/test_help_dialog.py#test_conflict_row_styles_use_theme_tokens"
        status: pass
    human_judgment: false
  - deliverable: "Rendered Help pages and conflict rows look as before at 100% and 200%"
    verification: []
    human_judgment: true
    rationale: "Visual look of rich text; the executor viewed the screenshots but the owner check stays open"
---

# Phase 12 Plan 02: Theme-token Help and conflict rows Summary

**The Help dialog stylesheet and the conflict-row buttons now take every colour, gap and font size from `theme.py`, with a new `SURFACE_BASE` white token and regression tests.**

## Accomplishments

- `help_dialog.CSS` is rebuilt as newline-joined f-string rules over theme constants: LINK/ACCENT headings and link colour, SURFACE/SURFACE_HEADER code and table headers, BORDER table borders, AMBER/AMBER_TINT callout. No hex literal and no px font size remain; h2 is `DISPLAY_PT`, h3 `HEADING_PT`, code and pre `MONO_PT` in `MONO_FAMILY`; padding and margins use the SP_* scale.
- `theme.SURFACE_BASE = "#FFFFFF"` added; `conflict_row._button_qss` uses it for the plain fill and the checked text colour.
- Three tests added to `tests/test_help_dialog.py`: tokens only, headings keep sizes (rendered through a `QTextBrowser`, checking `headingLevel()` and fragment point sizes), conflict-row tokens.

## Task Commits

1. Task 1 (tracer): `72f33f0` feat(12-02): build the Help stylesheet from theme tokens
2. Task 2: `608c7fc` feat(12-02): conflict row buttons take their white from SURFACE_BASE

## Verification

- `pytest tests/test_help_dialog.py -q`: 16 passed (after Task 1).
- `pytest tests/test_help_dialog.py tests/test_import_dialog.py -q -k "help or conflict_row"`: 22 passed.
- Acceptance greps: 0 hex literals, 0 px font sizes, 0 `border-radius` in `help_dialog.py`; 0 hex literals in `conflict_row.py`; `SURFACE_BASE` defined in `theme.py` and used twice in `conflict_row.py`.
- Tracer verified end to end (automated verify re-run green) before Task 2.
- Screenshots (executor-rendered with the Windows platform plugin at `QT_SCALE_FACTOR` 1 and 2; throwaway script and PNGs in the session scratchpad): Help "importing" and "requirements" pages show blue h2 larger than bold h3 larger than body, code on a light grey background in monospace, the Tip callout on a pale amber background; conflict rows show white plain buttons with grey border, Overwrite checked red with white bold text, Rename checked blue with white bold text. Sharp and not clipped at 200%.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None blocking. Observation for the owner screenshot check: in the rendered pages the h2 underline and the left bars on `pre` and the Tip callout are not drawn. Qt rich text does not paint `border-bottom` / `border-left` on block elements; the old stylesheet declared the same properties, so this is not a change. The plan's expected-look text mentions a blue underline and amber bar, which Qt does not show. The owner check from the plan remains open for confirmation.

## Test environment notes

- Ran only the targeted files with the orchestrator checkout's venv; the full suite was not run (orchestrator does that after the merge).
- No submodule-dependent skips in these files.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- FOUND: kicad_lib_manager/widgets/theme.py, help_dialog.py, conflict_row.py, tests/test_help_dialog.py
- FOUND commits: 72f33f0, 608c7fc
