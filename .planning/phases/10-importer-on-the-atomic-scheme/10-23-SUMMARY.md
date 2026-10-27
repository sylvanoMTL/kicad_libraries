---
phase: 10-importer-on-the-atomic-scheme
plan: 23
subsystem: importer
tags: [keywords, footprint-description, footprint-tags, install-plan, import-dialog, kicad-10-chooser]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "keywords.py and footprint_text.py generators (10-04, 10-05), footprint index (10-03), LibrarySuggestion.related_stems (10-15), atomic gate and reason strip (10-21, 10-22)"
provides:
  - "PartText, InstallPlan.generated_text / part_text, InstallOptions.keywords / fp_description / fp_tags / related_stems, FieldChange.scope"
  - "Planner writes merged keywords into the chosen symbol and a generated description and merged tags into the linked footprint"
  - "Dialog rows Keywords, Footprint description, Footprint tags, each with a Regenerate button"
  - "Field changes rows named as KiCad labels them (Keywords, Footprint description, Footprint tags)"
affects: [10-24 official footprints, 10-25 help page, phase 10 verification]

actuals:
  tokens: 15400
  tasks: 3
  commits: 6
plan_head_before: ad2dca66b23691d61e2201235e0107c89a38f202
plan_head_after: 664137af952b4bd0557515ffb83b84ece9f94e02

tech-stack:
  added: []
  patterns:
    - "One plan object (part_text) feeds the preview, the dialog rows and apply_plan, so the written text is the shown text"
    - "None on InstallOptions means generated; any string, empty included, is written exactly"

key-files:
  created:
    - tests/test_generated_text.py
  modified:
    - kicad_lib_manager/importer/plan.py
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/form.py
    - kicad_lib_manager/importer/preview.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_field_cleanup.py
    - tests/test_import_form.py
    - tests/test_import_preview.py
    - tests/test_install_plan.py
    - tests/test_vendor_install.py

key-decisions:
  - "generated_text is what the planner writes with no typed override (the merged keywords and tags), so Regenerate returns to exactly that and an unedited row equals generated_text"
  - "Regenerate is a 24 px glyph button (same size as the restore buttons) with the accessible name 'Regenerate <label>' and a tooltip, not a worded button, because the longer 'Footprint description' label plus a worded button pushed the left pane past its viewport"
  - "The package family is read from the vendor footprint's own descr and tags first, then from the best official footprint (rank score 30 or more) and its name; never from the pad count"
  - "A footprint text change lists under the final footprint name with scope footprint and is listed only when that footprint is written or still awaits a conflict decision"

patterns-established:
  - "Footprint-scope FieldChange: symbol holds the footprint name; preview prefixes only symbol-scope rows"

requirements-completed: [FLD-01, FLD-03]

coverage:
  - id: D1
    description: "The CSD sample installs with generated keywords, a footprint sentence and tags exactly as the plan and dialog showed them"
    requirement: "FLD-01"
    verification:
      - kind: unit
        ref: "tests/test_generated_text.py#test_installed_files_hold_exactly_the_planned_text"
        status: pass
      - kind: unit
        ref: "tests/test_generated_text.py#test_csd_part_text_is_generated_from_the_package_and_kicads_footprint"
        status: pass
    human_judgment: false
  - id: D2
    description: "Typed and empty texts are written exactly; Regenerate returns to the generated text; untouched rows follow a library change"
    requirement: "FLD-03"
    verification:
      - kind: unit
        ref: "tests/test_generated_text.py#test_typed_texts_are_written_exactly"
        status: pass
      - kind: integration
        ref: "tests/test_generated_text.py#test_an_edited_keywords_row_is_written_and_regenerate_returns_to_the_generated_text"
        status: pass
      - kind: integration
        ref: "tests/test_generated_text.py#test_an_untouched_row_follows_a_library_change"
        status: pass
    human_judgment: false
  - id: D3
    description: "Field changes name the fields as KiCad labels them and every footprint written with the new nodes loads in kicad-cli 10"
    requirement: "FLD-01"
    verification:
      - kind: unit
        ref: "tests/test_generated_text.py#test_field_changes_use_kicads_names_not_raw_ones"
        status: pass
      - kind: integration
        ref: "tests/test_generated_text.py#test_cli_loads_the_generated_text"
        status: pass
    human_judgment: false
  - id: D4
    description: "How the three new dialog rows look and read (glyph button instead of a worded Regenerate)"
    verification: []
    human_judgment: true
    rationale: "Wording, placement and the glyph choice are owner-facing UI judgment that no test asserts"

duration: 55min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 23: Generated keywords, footprint description and tags Summary

**Install now writes vendor-first merged keywords into the symbol and a generated sentence plus merged tags into the footprint, shows them as Field changes and three editable dialog rows with Regenerate, and writes exactly what was shown.**

## Performance

- **Duration:** about 55 min
- **Completed:** 2026-10-27
- **Tasks:** 3 (1 tracer, 1 tdd, 1 auto)
- **Files modified:** 11 (1 created)

## Accomplishments

- The CSD sample reads "WSON-6 2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B" with KiCad's footprints (stand-in Package_SON:Texas_DQK) and "2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B" without them (no family is guessed); keywords hold Transistor, FET, TI and Texas; tags keep the vendor tag first and add WSON-6, the IPC-style name, DQK0006B and P0.65mm.
- `build_plan` computes the text once: `generated_text` (what the generators make) and `part_text` (what is written, with typed overrides applied) on the plan; preview, dialog rows and `apply_plan` all read it. Tests read the installed files back and compare byte for byte with `part_text`.
- Dialog: Keywords, Footprint description and Footprint tags rows, pre-filled from the plan, framed under their `TEXT_NAMES` keys. Typing marks a row edited and dirty; Regenerate forgets the edit and requests a rebuild; an untouched row follows a library change; a typed row keeps its text.
- The preview lists the changes as "Set Keywords", "Set Footprint description" and "Set Footprint tags" (reason "generated"), never `ki_keywords`; `ki_description` and `ki_fp_filters` map to Description and Footprint filters.
- Real kicad-cli 10 loads the written symbol and footprint (`-m kicad_cli`: 34 passed).

## Task Commits

1. **Task 1: tracer, the CSD sample end to end** - `9027ab2` (feat)
2. **Task 2 RED: overrides, empty values, Regenerate, labels, kicad-cli load** - `7c72b32` (test)
3. **Task 2 GREEN: KiCad labels in Field changes** - `c04e659` (feat)
4. **Task 3: geometry fix for the Regenerate button** - `66f8a78` (fix)
5. **Task 3: migrated expectations** - `e2b2097` (test)
6. **Task 3: build_options text pass-through** - `664137a` (test)

## TDD Gate Compliance

Task 2 (`tdd="true"`): RED commit `7c72b32` precedes GREEN commit `c04e659`.

- RED: `tests/test_generated_text.py::test_field_changes_use_kicads_names_not_raw_ones` failed on the planned assertion (`"Set Keywords" in labels` against `['CSD85301Q2: Set ki_keywords', ...]`), the target test, the intended reason. The other Task 2 behaviours were already satisfied by Task 1's planner work (written as regression tests with the behaviour rows), so they passed at the RED commit; they were not independently RED. No `gsd_run check tdd-red-evidence` record was produced (pytest short output is not one of its supported report formats); the semantic assessment above is by inspection of the failing assertion.
- GREEN: preview.py maps the property names; target test and the full file pass.
- REFACTOR: none.

## Files Created/Modified

- `kicad_lib_manager/importer/plan.py` - `PartText`, new `InstallOptions` fields, `InstallPlan.generated_text` / `part_text`, `FieldChange.scope`
- `kicad_lib_manager/importer/planner.py` - footprint facts, official-footprint family lookup, keyword/description/tag generation, `_put_keywords`, `render_fp` text edits and changes
- `kicad_lib_manager/importer/form.py` - `TEXT_NAMES`, `TEXT_LABELS`, `FormValues.texts` / `related_stems`, `build_options`
- `kicad_lib_manager/importer/preview.py` - KiCad labels, footprint-scope rows without symbol prefix
- `kicad_lib_manager/widgets/import_dialog.py` - three rows with Regenerate, edit tracking, plan display
- `tests/test_generated_text.py` - 18 tests (generation, override, empty, quotes, written equals previewed, vendor keywords, rename retoken, dialog, geometry, kicad-cli)
- `tests/test_field_cleanup.py`, `tests/test_import_form.py`, `tests/test_import_preview.py`, `tests/test_install_plan.py`, `tests/test_vendor_install.py` - expectations migrated

## Decisions Made

See key-decisions. Also: keywords use the final manufacturer as written (canonical spelling, nothing for a cleared Manufacturer), and the family search ranks the official folder only when `tools.kicad_footprints_dir` is set.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Regenerate is a glyph button, not a worded one**
- **Found during:** Task 3 (full suite)
- **Issue:** A worded "Regenerate" button plus the longer "Footprint description" label made the left pane 438 px wide against a 364 px viewport; three geometry tests failed (`test_fields_long_text_geometry`, `test_library_long_name_geometry`, `test_conflicts_overflow_geometry`).
- **Fix:** The button is the shared 24 px restore-button helper with the glyph and accessible name "Regenerate <label>" and a tooltip starting "Regenerate". The three label texts stay as the plan names them.
- **Files modified:** kicad_lib_manager/widgets/import_dialog.py, tests/test_generated_text.py (geometry test)
- **Committed in:** `66f8a78`

**2. [Rule 1 - Expectation migration] Byte and field-change expectations moved to the new written text**
- **Found during:** Task 3
- **Issue:** Six tests compared property lists, field-change lists, section order or the retokened keywords, which now include the generated text.
- **Fix:** Expected values updated to the new output (reason: every installed part now carries generated keywords and footprint text); no assertion weakened. `tests/test_install_apply.py`, `tests/test_install_e2e.py` and `tests/test_import_dialog.py` needed no change.
- **Files modified:** tests/test_field_cleanup.py, tests/test_import_preview.py, tests/test_install_plan.py, tests/test_vendor_install.py
- **Committed in:** `e2b2097`

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 expectation migration)
**Impact on plan:** The visible Regenerate word is replaced by a tooltip and accessible name; nothing else changed.

## Issues Encountered

- `preview_sections` rows had `.name`, not `.title` with a count suffix; the first test helper used the wrong attribute.
- A kept (skipped) footprint still shows its generated text in the dialog rows although nothing is written for it; the plan lists no footprint change in that case. Plan 10-24 handles official footprints separately.

## Known Stubs

None.

## Threat Flags

None. The planner reads the matched official footprint only (`footprint_texts`) and writes nothing into the KiCad folder (T-10-30); typed text goes through `quote()` and a quotes-and-backslashes test reads it back (T-10-29); preview, rows and `apply_plan` share one plan (T-10-31).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 10-24 (official footprints) can keep generated text off official links through `InstallOptions.fp_description` / `fp_tags` and the plan's `part_text`.
- 10-25 rewrites the help page; `widgets/help_dialog.py` was not touched.
- Verification: `pytest -m "not wurth"` 2840 passed, 13 skipped (worktree-only skips: Custom submodule and the two UAT env vars, plus two symlink skips); `pytest -m kicad_cli` 34 passed.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*

## Self-Check: PASSED

- Created and modified files exist; commits `9027ab2`, `7c72b32`, `c04e659`, `66f8a78`, `e2b2097`, `664137a` are ancestors of HEAD.
