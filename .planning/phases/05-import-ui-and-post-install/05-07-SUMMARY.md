---
phase: 05-import-ui-and-post-install
plan: 07
subsystem: ui
tags: [pyside6, import-dialog, item-picker, field-defaults, d-13, debounce, tdd]

requires:
  - phase: 05-import-ui-and-post-install
    provides: "05-02 InstallOptions.cleared and install.empty_required; 05-05 Start page, _on_change/_reset_edit_state; 05-06 preview sections; 05-01 dialog coordinator and importer.form layering entry"
provides:
  - "importer/form.py (Qt-free): FIELD_NAMES, FIELD_LABELS, FieldDefaults, FormValues, field_defaults, build_options"
  - "ImportDialog Items section: symbol combo or label, footprint checklist with Make linked, model combo ending in No model, extends-parent note"
  - "ImportDialog Footprint section (Name + restore + vendor hint) and Fields section (Symbol, read-only plan-driven Footprint field, Value/Datasheet/Description/Manufacturer/MPN with restore buttons)"
  - "300 ms text-edit debounce (_dirty, _debounce); Install is off from the first keystroke"
  - "_form_values(), _linked_fp, _defaults, _edited, _fp_name_edited, _resolutions (empty, for 05-10)"
affects: [05-08, 05-09, 05-10, 05-11]

plan_head_before: 6ec6b1bc8cd7bb9f256b50da1b5261df2088bd7e
plan_head_after: 3d4e76b1045f096cbabb8f135f5793128b213c8f

actuals:
  tokens: 19600
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Qt-free form rules: the dialog collects FormValues, build_options turns them into InstallOptions; only edited fields are passed"
    - "field_defaults mirrors planner._edit_symbol, pinned by an equivalence test (typing every default gives equal ops)"
    - "Read-only Footprint field is set only from an accepted plan; a textEdited-driven debounce, programmatic setText runs under blockSignals"
    - "_OfferLabel(expanding=True): a form-field label that asks for room but can shrink to zero width"

key-files:
  created:
    - kicad_lib_manager/importer/form.py
    - tests/test_import_form.py
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_import_dialog.py

key-decisions:
  - "A field typed back to its default leaves the edited set, so it follows the default again (for example a Value after a conflict Rename); the footprint name behaves the same"
  - "Unchecking every footprint passes footprints=() and the planner reports install.choice_required; the nicer 'Select at least one footprint' reason belongs to plan 05-09"
  - "Left pane stays disabled until the first plan, but a failed first build enables it so the user is not locked out"
  - "Combos cannot elide in the middle natively: they keep the full name as tooltip and popup width, labels and the checklist elide in the middle"
  - "Left-pane choices rebuild through _request_rebuild, which also cancels a pending debounce, so a combo change during typing carries the typed text in one build"

patterns-established:
  - "Tests that drive text fields type with qtbot.keyClicks so textEdited fires (setText does not)"
  - "Dialog tests that need no Custom submodule use write_custom_layout plus zipfixtures zips; a _good_suggestion core override replaces the placeholder library name"

requirements-completed: [INTK-07, PREV-02, PREV-03, PREV-04]

coverage:
  - id: D1
    description: "Picker: combo, checklist (6 rows then scroll, linked row bold with '(linked)', Make linked, linked moves on uncheck), model combo ending in No model, labels for one item, AMBER labels for none, extends note from the plan"
    requirement: INTK-07
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_picker_several_items_build_options", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_picker_checklist_shows_six_rows_then_scrolls", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_picker_single_items_are_labels", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_picker_no_model_and_no_footprint_labels", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_picker_extends_note", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_picker_never_passes_blank", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_left_pane_disabled_until_first_plan", status: pass}
    human_judgment: false
  - id: D2
    description: "Footprint name defaults to the sanitised vendor name with restore and vendor hint; an empty name blocks; a typed name is sanitised and a case-twin is a conflict"
    requirement: PREV-02
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_footprint_name_default_and_vendor_hint", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_footprint_name_edit_and_restore", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_empty_footprint_name_blocks", status: pass}
      - {kind: unit, ref: "tests/test_import_form.py#test_empty_footprint_name_blocks_the_plan", status: pass}
      - {kind: unit, ref: "tests/test_import_form.py#test_typed_footprint_name_case_twin_is_a_conflict", status: pass}
    human_judgment: false
  - id: D3
    description: "The read-only Footprint field is <Lib>:<FP> from the accepted plan, '(none)' in MUTED when unlinked, keeps the old text while a rebuild runs, and follows library, name, link and checked order (with ki_fp_filters)"
    requirement: PREV-03
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_footprint_field_follows_library_and_name", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_footprint_field_none_when_unlinked", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_footprint_field_and_filters_follow_checked_order", status: pass}
    human_judgment: false
  - id: D4
    description: "Fields start with what the plan writes (equivalence on UL, aliases, inferred manufacturer, renamed symbol); only edited fields are passed; emptied fields install blank via cleared; Value and MPN block; restore buttons; debounce; reload rules"
    requirement: PREV-04
    verification:
      - {kind: unit, ref: "tests/test_import_form.py#test_field_defaults_equivalence", status: pass}
      - {kind: unit, ref: "tests/test_import_form.py#test_field_defaults_value_follows_final_name", status: pass}
      - {kind: unit, ref: "tests/test_import_form.py#test_build_options_fields", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_fields_clear_and_restore", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_emptied_mpn_blocks_install", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_fields_reset_on_symbol_change_kept_on_library_change", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_debounce_single_rebuild", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_restore_buttons_accessible", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_edit_state_cleared_by_change", status: pass}
    human_judgment: false
  - id: D5
    description: "At 900x600 with a 60-character name and a 120-character Description no left-pane control is clipped, overlaps its restore button, or adds a horizontal scroll bar; the pane looks right on a real display with real fonts"
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_fields_long_text_geometry", status: pass}
    human_judgment: true
    rationale: "The offscreen platform has no fonts (glyphs render as boxes, widths are exaggerated), so the geometry test proves containment but not how the pane looks; owner UAT in 05-11 at 100% and 150% scaling"

duration: 35min
completed: 2026-10-22
status: complete
---

# Phase 5 Plan 07: Item Picker, Footprint Name and Fields Summary

**Qt-free `form.py` (field_defaults mirrors the planner, build_options passes only edited fields and names emptied ones in `cleared`) plus the Items, Footprint and Fields sections of the Import dialog: symbol/footprint/model pickers with Make linked, an editable footprint name, five pre-filled fields with restore buttons, a read-only Footprint field read from the accepted plan, and a 300 ms text debounce.**

## Performance

- **Duration:** about 35 min
- **Completed:** 2026-10-22
- **Tasks:** 2 (both TDD), 4 commits (RED and GREEN per task) plus the SUMMARY commit
- **Files:** 4 (2 created, 2 modified); `import_dialog.py` +591/-17, `form.py` 123 lines

## Accomplishments

- `importer/form.py`: `FIELD_NAMES`, `FIELD_LABELS`, frozen `FieldDefaults` and `FormValues`, `field_defaults(candidate, symbol_name, final_name=None)` and `build_options(values, defaults, linked_vendor=None)`. No Qt import. `build_options` passes an edited field with text exactly, passes `""` plus a `cleared` entry for an emptied field whose default is non-empty, passes nothing for an emptied field whose default is already empty, and puts an edited footprint name against the linked vendor footprint (an empty one is an explicit override the planner refuses with `install.invalid_name`).
- `field_defaults` equals what the planner writes: `test_field_defaults_equivalence` builds a plan with nothing set and a plan with every default typed and asserts `plan.ops`, `plan.issues` and `model_file` equal, for the UL sample, MF/MP/ki_description alias properties, an inferred manufacturer (TI from the datasheet host) and a symbol whose name changes when sanitised (`PART/1` gives Value `PART_1`, MPN stays `PART/1`).
- Items section built per package: `_populate_items` fills a persistent QFormLayout. Symbol and model are a QComboBox when several (model ends in `No model`), a middle-eliding plain label for one, an AMBER label for none; footprints are a checklist (all checked, 6 rows then a vertical scroll bar, linked row bold with `  (linked)`, **Make linked**) for several. The extends-parent note is read from `plan.symbol_names[:-1]` of each accepted plan.
- Footprint section: Name field defaulting to the linked footprint's sanitised vendor name, 24x24 restore button, MUTED `Vendor name: {original}` hint when the names differ; the field restarts when the linked footprint changes.
- Fields section: Symbol (`{vendor} → {final}` when renamed), read-only Mono Footprint field set only from an accepted plan (`(none)` in MUTED when unlinked or refused), and Value, Datasheet, Description, Manufacturer, MPN with restore buttons (disabled while the text equals the default, tooltip `Restore default: {value}`), placeholder `Empty - the field will be written blank` on the three optional fields and the tooltip `MPN names the 3D model file`.
- Debounce and state: `textEdited` sets `_dirty` (Install off, strip `Updating preview...`) and restarts a 300 ms single-shot timer; combo, checklist, Make linked and restore changes call `_request_rebuild()` at once, which cancels the timer and takes the snapshot (Pitfall 10). `_reset_edit_state` and `_shutdown` stop the timer; Change... clears edits, items, defaults and the Footprint field.
- The left pane is disabled until the first plan is accepted (or the first build fails).

## TDD Gate Compliance

| Task | RED commit | GREEN commit |
|------|-----------|--------------|
| 1 | 3d363f7 `test(05-07)` | 759d2f6 `feat(05-07)` |
| 2 | b7b2eb9 `test(05-07)` | 3d4e76b `feat(05-07)` |

RED evidence (manual semantic assessment; `gsd_run` is not available in the worktree, so `check tdd-red-evidence` was not run):
- Task 1: with a temporary throwaway `form.py` stub (uncommitted, deleted before the RED commit) the two `build_options` tests failed on the planned assertions (`AttributeError: 'NoneType' object has no attribute ...` from the stub's return value); the 8 dialog tests failed on missing API (`_symbol_combo`, `_dirty`, ...) and `test_left_pane_disabled_until_first_plan` failed on its assertion (`assert not True` for `_left_scroll.isEnabled()`). This is the weaker missing-API RED accepted in 05-01 and 05-05 for new surface.
- Task 2: `form.py` existed, so the 8 form tests failed on the planned behaviour (`field_defaults` missing, `build_options` ignoring fields and footprint names, an empty footprint name not producing a blocked plan); the 13 dialog tests failed with `AttributeError` for the missing widgets. 21 failed, 31 passed (the passing ones were the Task 1 tests and the pre-existing suite).
- No refactor commit.

## Task Commits

1. Task 1 RED `3d363f7`, GREEN `759d2f6`: item picker
2. Task 2 RED `b7b2eb9`, GREEN `3d4e76b`: footprint name, field defaults and clear semantics

## Files Created/Modified

- `kicad_lib_manager/importer/form.py` - Qt-free form rules
- `kicad_lib_manager/widgets/import_dialog.py` - Items, Footprint and Fields sections, `_form_values`, debounce, `_OfferLabel(expanding=True)`
- `tests/test_import_form.py` - 12 tests (items, fields, footprint name, equivalence x4 parametrised, case-twin)
- `tests/test_import_dialog.py` - 23 new tests (picker, footprint name and field, fields, debounce, restore buttons, geometry)

## Decisions Made

See `key-decisions` above. The one to review is "typed back to the default leaves the edited set": it keeps an unedited field following the planner (a Value after a conflict Rename) at the cost of treating a deliberately retyped default as unedited, which is harmless because both give equal ops.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Single-item labels collapsed to zero width in the form**
- **Found during:** Task 2 (offscreen screenshot of the dialog)
- **Issue:** `_OfferLabel` uses an Ignored horizontal policy, so in a QFormLayout (ExpandingFieldsGrow) the field column got no width and the Symbol, Footprints and 3D model values, and the Fields Symbol row, were invisible.
- **Fix:** `_OfferLabel(expanding=True)` asks for room (Expanding) but reports a zero minimum width, so it still shrinks and never widens the pane. The two read-only rows are wrapped so they end where a line edit plus restore button ends.
- **Files modified:** kicad_lib_manager/widgets/import_dialog.py
- **Commit:** 3d4e76b

### Test and environment adjustments

**2. [Test design] Synthetic Custom layout instead of `custom_copy`**
- The plan's precondition and tests name the Custom submodule; it is absent in a worktree, which would make every UL test skip. The new tests build `write_custom_layout` libraries and zipfixtures zips, so all 35 new tests run in a bare worktree. A `_good_suggestion` core override (as in 05-01) replaces the placeholder library name where a non-blocked plan is needed.

**3. [Test design] 'No 3D model found' is an `intake.no_model` Issue**
- The plan says the plan carries the 'No 3D model found' WARNING; with the placeholder library the plan is refused before the planner's own `install.no_model`, so the test asserts the package-level `intake.no_model` Issue that the plan copies from the candidate.

**4. [Rule 2 - Missing critical] Tab order**
- Items controls are created after the page, so Qt's creation-order tab chain would put them after the Fields. `_set_tab_order` chains Change... to Items, Target library, Footprint name, Footprint field and the fields with their restore buttons, as the UI-SPEC tab order asks.

**Additions beyond the plan:** extra tests for the case-twin footprint name (`install` conflict "letter case"), the `ki_fp_filters` order with the linked footprint first, an emptied MPN, `_on_change` clearing edit state, the symbol-name rename label, and an `inferred` case in the equivalence test.

**Total deviations:** 1 auto-fixed bug, 1 missing-critical addition, 2 test adjustments. **Impact:** none on scope.

## Issues Encountered

None.

## Verification

- Bare worktree: `tests/test_import_form.py tests/test_import_dialog.py` give 55 passed, 11 skipped. All 11 skips are the plan 05-01 `custom_copy` tests (Custom submodule not checked out); none of this plan's tests skip. Run 3 times in a row without a flake.
- Full suite in the bare worktree: 4 failed, 1415 passed, 78 skipped. The 4 failures are on the known KiCad 10 baseline list (`test_version_real_cli_into_20241209`, `test_library_real_cli_new_header`, `test_noop_second_plan_after_normalised_apply`, `test_real_cli_upgrades_ul_symbol_deterministically`); the `test_install_e2e.py` baseline cases skip in a bare worktree. The 78 skips are the same Custom/Wurth/symlink-privilege skips as before this plan (none added).
- Custom-enabled mirror (worktree sources plus a copy of the main checkout's `Custom/` in the scratchpad): `test_import_form`, `test_import_dialog`, `test_install_options_clear`, `test_import_preview`, `test_importer_layering` give 109 passed, 0 skipped, so the 11 skipped 05-01 tests pass with the new left pane. `test_main_window`, `test_main_window_import`, `test_preview_tree`, `test_import_content`, `test_library_table_widget` also pass there. The mirror has no `.git`, so unrelated git/requirements tests fail in it; they are not touched by this plan.
- Acceptance greps: `form.py` has 0 PySide6 import lines; `form.py` holds `def build_options(`, `class FormValues`, `FIELD_NAMES = (...)`, `def field_defaults(candidate`, `replace_exact_tokens`, `cleared`; the dialog holds every required literal (`Make linked`, `(linked)`, `No model`, `No footprint in this package`, `No 3D model in this package`, `is included automatically`, `Empty - the field will be written blank`, `Restore default footprint name`, `MPN names the 3D model file`, `Vendor name: `, `setInterval(300)`).
- The plan's `<automated>` commands name `./env/Scripts/python.exe`, which does not exist in a worktree; the main checkout's interpreter was used by absolute path, as instructed.

## Known Stubs

None. `self._resolutions` is an empty dict that plan 05-10 fills; `FormValues.resolutions` already carries it through `build_options` (tested).

## Threat Flags

None beyond the plan's threat model. T-05-22 (blank choice reaching InstallOptions) is mitigated by `_form_values` and proven by `test_picker_never_passes_blank`; T-05-23 (shown value differs from written value) by `test_field_defaults_equivalence` and by reading the Footprint field from the plan only.

## Next Phase Readiness

- 05-09 can wrap the Footprint name, Value, MPN and footprint list in `FIELD_FRAME_QSS` frames and add blocking reasons: `_fp_name_edit`, `_field_edits[...]`, `_fp_list`, `_library_combo` are stable attributes; `_dirty`, `_debounce`, `_request_rebuild()` and `_update_install_state()` behave as its plan assumes (`_updating()` already includes `_dirty`). The library combo still rebuilds on `editingFinished`; 05-09 replaces that with the debounce.
- 05-10 should fill `self._resolutions` and call `_request_rebuild()`; `build_options` passes them to the planner unchanged.
- Manual UAT (05-11): the look at 100% and 150% scaling with real fonts, and whether an empty Datasheet loads in KiCad (carried over from 05-02).

## Self-Check: PASSED

- Files exist: `kicad_lib_manager/importer/form.py`, `tests/test_import_form.py` (created); `kicad_lib_manager/widgets/import_dialog.py`, `tests/test_import_dialog.py` (modified).
- Commits 3d363f7, 759d2f6, b7b2eb9 and 3d4e76b are ancestors of HEAD; `git rev-list --count` from the base gives 4 before this SUMMARY commit.
