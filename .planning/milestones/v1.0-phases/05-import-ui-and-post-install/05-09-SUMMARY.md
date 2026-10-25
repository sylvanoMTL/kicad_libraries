---
phase: 05-import-ui-and-post-install
plan: 09
subsystem: ui
tags: [pyside6, import-dialog, target-library, blocking-reasons, field-frames, d-09, d-11, tdd]

requires:
  - phase: 05-import-ui-and-post-install
    provides: "05-07 form.py, _fp_name_edit/_field_edits/_fp_list/_library_combo, _dirty/_debounce/_request_rebuild/_update_install_state; 05-06 file_counts; 05-03 theme constants; 05-01 rebuild coordinator"
provides:
  - "importer/form.py (Qt-free): Reason, FormStatus, blocking_reasons, kind_label, library_tokens, library_badge, ready_text, noop_text, UPDATING_REASON, BUILD_FAILED_REASON, NEW_LIBRARY_BADGE"
  - "ImportDialog Target library section: editable combo (alternatives, separator, every library read per open), existing/new badge, amber token line and hint, debounced typing, immediate pick"
  - "Updating... label beside Preview and a 4 px busy strip after 150 ms"
  - "Clickable blocking-reason strip (rich text, escaped, internal reason: links), QFrame#fieldFrame wrappers with the amber blocked border, ready and no-op lines, Ctrl+Return"
  - "_reason_targets / _field_frames dicts for plan 05-10 to register conflict:{key} and rename:{key} controls"
affects: [05-10, 05-11]

plan_head_before: fa011e9d6779550958316ee56cd33d345dcb92a4
plan_head_after: 72cbf434c5ea63c5934e23bf8c61d030fdfb40ef

actuals:
  tokens: 19800
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "blocking_reasons(status, plan) is a pure function: the dialog reads its controls into a FormStatus and renders the list; a plan ERROR a form reason already explains is dropped"
    - "Blocked highlight sits on a QFrame#fieldFrame (property blocked, re-polished), never on the QLineEdit/QComboBox itself; the frame reserves its 2 px border so nothing moves"
    - "Strip is rich text only while it lists reasons: every string html.escape()d, hrefs are internal reason:{n}, setOpenExternalLinks(False); status lines are plain text"
    - "Frames follow the live control text (a rebuild in flight does not clear them); the strip shows only 'Updating preview...' while updating"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/form.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_import_form.py
    - tests/test_import_dialog.py

key-decisions:
  - "Inline completion is switched off on the library combo: it rewrites the typed text to the existing library's case, which hides a case twin (the badge must say 'new' and the planner's install.library_case_clash must fire)"
  - "A plan ERROR links to the control it is about: install.library_case_clash / invalid_library / placeholder_library -> library, empty_required -> value or mpn, invalid_name about a footprint name -> footprint_name; anything else targets 'plan' (focus the preview tree)"
  - "A conflict whose chosen Rename has no text gets only 'Enter a new name for ...' (the plain 'Choose Overwrite, Rename or Skip' reason is skipped for it, the planner's bad_rename for that key is de-duplicated)"
  - "When the last build failed, plan-derived reasons (ERROR Issues, conflicts) of the previous plan are not listed: only the build-failed reason and the form-level reasons"
  - "'Updating preview...' is shown as a plain MUTED status line, not as a blocked strip with a link: it is not something the user can fix, and it keeps the 05-07 test contract"
  - "All five field edits, the footprint name and the read-only Footprint field are framed (not only Value and MPN) so every row keeps the same left and right edge"
  - "The library badge word-wraps: at 900x600 the full 'new - creates .kicad_sym + .pretty' text plus the combo needs more than the 365 px pane, and a single-line badge forced a 640 px left pane"

patterns-established:
  - "Dialog tests for blocked states build a fake plan by dataclasses.replace(real_plan, issues=...) or ops=() inside a build_plan core override"
  - "strip_links(dialog) reads reason text and href from the rich-text strip with a regex; frame_blocked(dialog, key) reads the frame property"

requirements-completed: [PREV-07, PREV-03, PREV-06]

duration: 55min
completed: 2026-10-22
status: complete

coverage:
  - id: D1
    description: "Target library combo: pre-filled with the suggestion, alternatives then separator then every library read per open; typing rebuilds after 300 ms, picking rebuilds at once and cancels the timer"
    requirement: PREV-07
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_library_combo_lists_alternatives_then_existing", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_library_typing_debounced_pick_immediate", status: pass}
    human_judgment: false
  - id: D2
    description: "Badge (existing / new - creates .kicad_sym + .pretty, case twin is new) and the token line with amber placeholder and low-confidence tokens, the hint, escaping"
    requirement: PREV-07
    verification:
      - {kind: unit, ref: "tests/test_import_form.py#test_library_tokens", status: pass}
      - {kind: unit, ref: "tests/test_import_form.py#test_library_badge", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_library_badge_and_token_line", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_library_token_line_escapes_markup", status: pass}
    human_judgment: false
  - id: D3
    description: "Updating... label at once, busy strip after 150 ms, both hidden with the result; previous tree stays; first build keeps its Building page"
    requirement: PREV-07
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_updating_label_and_busy_strip", status: pass}
    human_judgment: false
  - id: D4
    description: "kicad-cli runs once per symbol pick across library, footprint-name and field rebuilds, and never in two builds at once"
    requirement: PREV-06
    verification:
      - {kind: unit, ref: "tests/test_import_form.py#test_cli_runs_once_across_rebuilds", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_one_build_at_a_time", status: pass}
    human_judgment: false
  - id: D5
    description: "blocking_reasons: UI-SPEC order, Updating alone, build failure, de-duplication, placeholder text, empty rename, targets"
    requirement: PREV-07
    verification:
      - {kind: unit, ref: "tests/test_import_form.py#test_blocking_reasons_order", status: pass}
      - {kind: unit, ref: "tests/test_import_form.py#test_blocking_reasons_updating_alone", status: pass}
      - {kind: unit, ref: "tests/test_import_form.py#test_blocking_reasons_build_failed", status: pass}
      - {kind: unit, ref: "tests/test_import_form.py#test_blocking_reasons_dedup", status: pass}
      - {kind: unit, ref: "tests/test_import_form.py#test_blocking_reasons_issue_targets_link_the_control", status: pass}
      - {kind: unit, ref: "tests/test_import_form.py#test_blocking_reasons_placeholder_text", status: pass}
      - {kind: unit, ref: "tests/test_import_form.py#test_blocking_reasons_empty_rename", status: pass}
      - {kind: unit, ref: "tests/test_import_form.py#test_ready_and_noop_text", status: pass}
    human_judgment: false
  - id: D6
    description: "Phase 3 D-04 enforced in the UI: a placeholder library name blocks Install until a real one is picked; empty name, case twin and invalid name show the plan Issue and the amber frame"
    requirement: PREV-07
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_placeholder_blocks_install", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_empty_library_name_blocks", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_case_twin_and_invalid_name_show_the_plan_issue", status: pass}
    human_judgment: false
  - id: D7
    description: "Strip: reason links focus Value, MPN, library combo, footprint list; unchecking the last footprint; escaping and internal links only; 3-line cap with full tooltip; ready and no-op lines; updating-alone; build failure and retry"
    requirement: PREV-07
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_strip_link_focuses_field", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_strip_link_focuses_library_and_footprint_list", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_strip_link_ignores_unknown_href", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_strip_escapes_markup", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_strip_look", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_strip_caps_three_lines_with_tooltip", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_ready_line_and_install_enabled", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_noop_strip", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_updating_reason_replaces_the_others", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_build_failure_reason_and_retry", status: pass}
    human_judgment: false
  - id: D8
    description: "Field frames reserve their border, Ctrl+Return installs only when enabled, Enter in a line edit never installs, no default buttons"
    requirement: PREV-07
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_field_frames_reserve_their_border", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_ctrl_return_and_no_default_buttons", status: pass}
      - {kind: unit, ref: "tests/test_import_dialog.py#test_ctrl_return_shortcut_is_registered", status: pass}
    human_judgment: false
  - id: D9
    description: "A 60-character library name stays inside the left pane at 900x600 with the badge fully visible and no horizontal scroll bar; the pane, amber frames, strip and badge look right on a real display with real fonts"
    requirement: PREV-07
    verification:
      - {kind: unit, ref: "tests/test_import_dialog.py#test_library_long_name_geometry", status: pass}
    human_judgment: true
    rationale: "The offscreen platform has no fonts (glyphs render as boxes, widths are exaggerated), so the geometry test proves containment but not how the pane looks; owner UAT in 05-11 at 100% and 150% scaling"
---

# Phase 5 Plan 09: Target Library, Updating Indicators and Blocking Strip Summary

**Qt-free `blocking_reasons` (UI-SPEC order, de-duplicated against the form reasons) plus the Target library combo with an existing/new badge and amber token line, the Updating label and busy strip, and a clickable rich-text reason strip with amber `fieldFrame` borders, ready/no-op lines and Ctrl+Return; Install is only possible for a current, unblocked plan, and a placeholder library name is blocked in the UI as well as by the planner.**

## Performance

- **Duration:** about 55 min
- **Completed:** 2026-10-22
- **Tasks:** 2 (both TDD), 4 commits (RED and GREEN per task) plus the SUMMARY commit
- **Files:** 4 modified; `form.py` +178/-3, `import_dialog.py` +331/-65, tests +807

## Accomplishments

- **Target library (D-11).** The combo is editable, pre-filled with `LibrarySuggestion.name`; the dropdown lists the ranked alternatives, a separator, then every library of the list the open worker reads (so it is fresh at every open). `textEdited` marks the dialog dirty and restarts the 300 ms debounce; `textActivated` stops the timer and rebuilds at once. The editingFinished trigger of 05-01 is gone. A badge to the right reads `existing` (SUCCESS) or `new - creates .kicad_sym + .pretty` (bold), a case twin counts as new, and it follows every keystroke. A Mono token line under the combo shows the name split on `_` with placeholder tokens (and, while the text still equals the suggestion, low-confidence tokens) in bold AMBER, with the MUTED hint while any token is amber. Every token is `html.escape`d; a zero-width space after each `_` lets a long name wrap.
- **Updating indicators (D-06).** `Updating...` (AMBER) shows next to the Preview title as soon as a rebuild is pending (dirty, queued or running) and the previous tree is on screen; a 4 px indeterminate strip joins after 150 ms (it keeps its room when hidden, so the tree does not jump); both go with the accepted result or a failure. The first build keeps its own `Building preview...` page.
- **Blocking reasons (D-09, PREV-07).** `form.blocking_reasons(FormStatus, plan)` returns Updating alone, or the build failure / plan ERROR Issues (`Error: ...`), the library reason (empty or placeholder with the exact copy), `Value is empty`, `MPN is empty - it names the 3D model file`, `Select at least one footprint`, one `Choose Overwrite, Rename or Skip for {kind} {name}` per unresolved conflict and one `Enter a new name for ...` per empty rename. Plan ERRORs that a form reason already explains (placeholder library, empty library name, empty Value/MPN, no footprint of several, empty rename) are not repeated.
- **The strip.** Rich text on AMBER_TINT with 8 px margins and a 3-line height cap; `⚠ Install is blocked: ` then LINK-coloured links joined by ` · `, each an internal `reason:{n}` href that focuses (and scrolls to) the library combo, footprint list, footprint name, Value, MPN or the preview tree; unknown hrefs do nothing; external links never open. The tooltip lists every reason (escaped). Ready reads `✓ Ready to install: {n} new, {m} modified, {k} unchanged files` in SUCCESS, a no-op `Nothing to install: this part is already in {Lib}.` in MUTED.
- **Amber frames.** The library combo, footprint name, the five field edits, the read-only Footprint field and the footprint checklist sit in `QFrame#fieldFrame` with `FIELD_FRAME_QSS`; the `blocked` property follows the reasons (re-polished) and the 2 px border is always reserved. The dialog registers the controls in `_reason_targets` and `_field_frames`; plan 05-10 adds `conflict:{key}` / `rename:{key}` entries.
- **Ctrl+Return** triggers Install only when it is enabled; no button is a default or auto-default, so Enter in a line edit (or the combo) never installs. Install is enabled only for a current plan with no reasons that is not a no-op.
- **kicad-cli cache (PREV-06).** `test_cli_runs_once_across_rebuilds` shows the existing cache already holds: three builds (new library, another library, footprint name plus a typed Manufacturer) give one `sym upgrade` call. No planner change was needed. `test_one_build_at_a_time` shows edits during a running build queue and never overlap.

## TDD Gate Compliance

| Task | RED commit | GREEN commit |
|------|-----------|--------------|
| 1 | e111518 `test(05-09)` | ae3f620 `feat(05-09)` |
| 2 | 9ad32ea `test(05-09)` | 72cbf43 `feat(05-09)` |

RED evidence (manual semantic assessment; `gsd_run` is not available in the worktree, so `check tdd-red-evidence` was not run):
- Task 1: 8 failed, 3 passed. The form tests failed with `AttributeError: module ... has no attribute 'library_tokens'` / `'library_badge'`; the dialog tests failed on missing widgets (`_token_line`, `_updating_label`, `_library_badge`) and two on the planned assertions (combo order `['IC_SubCategory_TI', ...] != ['IC_IMU_TDK', ...]`; `_dirty` false after typing in the library line edit). `test_cli_runs_once_across_rebuilds` passed in RED by design: it pins existing planner/cache behaviour (PREV-06), and its passing is the finding. This is the weaker missing-API RED accepted in 05-01, 05-05 and 05-07 for new surface.
- Task 2: the form test module failed at collection with `ImportError: cannot import name 'FormStatus'`; the dialog subset showed 16 failed (missing `_field_frames`, strip format/links, shortcut, `Install is blocked` rich text) and 4 pre-existing tests passing.
- No refactor commit.

## Task Commits

1. Task 1 RED `e111518`, GREEN `ae3f620`: Target library combo, badge, token line, Updating indicators
2. Task 2 RED `9ad32ea`, GREEN `72cbf43`: blocking reasons, strip, amber frames, ready and no-op lines, Ctrl+Return

## Files Created/Modified

- `kicad_lib_manager/importer/form.py` - `library_tokens`, `library_badge`, `kind_label`, `Reason`, `FormStatus`, `blocking_reasons`, `ready_text`, `noop_text`
- `kicad_lib_manager/widgets/import_dialog.py` - library section, Updating label and busy bar, `_framed`, `_form_status`, `_render_strip`, `_on_reason_link`, `_apply_blocked_frames`, Ctrl+Return shortcut
- `tests/test_import_form.py` - 12 new tests (tokens, badge, cache across rebuilds, reasons)
- `tests/test_import_dialog.py` - 23 new tests

## Decisions Made

See `key-decisions` above. The two worth a review: inline completion is off on the library combo (a typed case twin has to stay visible), and `Updating preview...` is a plain MUTED line rather than a link, because the user cannot act on it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The single-line library badge widened the left pane to 640 px**
- **Found during:** Task 1 (`test_library_long_name_geometry`: left pane 640 px against a 364 px viewport)
- **Issue:** The badge text `new - creates .kicad_sym + .pretty` plus the combo needed more than the pane's width, so the left pane grew and the badge was clipped.
- **Fix:** The badge word-wraps (minimum width = its longest word), and the combo shrinks (`AdjustToMinimumContentsLengthWithIcon`, 12 characters).
- **Files modified:** kicad_lib_manager/widgets/import_dialog.py
- **Commit:** ae3f620

**2. [Rule 2 - Missing critical] Inline completion would hide a case twin**
- **Found during:** Task 1 design (the combo's default completer rewrites typed text to an existing library's case)
- **Issue:** Typing `ic_battery_charger_ti` would be auto-corrected to `IC_Battery_Charger_TI`, so the badge and the planner's `install.library_case_clash` would never see the case twin and the typed name would not be the one used.
- **Fix:** `setCompleter(None)` on the library combo; the dropdown still lists every library.
- **Files modified:** kicad_lib_manager/widgets/import_dialog.py
- **Commit:** ae3f620

**3. [Rule 2 - Missing critical] Plan ERRORs link to the control they are about**
- **Found during:** Task 2 (UI E6/error: a case twin or invalid name must show the amber frame on the library combo, but the plan fixes only `plan` as the target of an `Error:` reason)
- **Fix:** `_issue_target` maps the library, empty-field and footprint-name codes to their control and leaves every other code on `plan`, as the plan's test expects.
- **Files modified:** kicad_lib_manager/importer/form.py
- **Commit:** 72cbf43

### Plan adjustments and test design

**4. [Test design] Synthetic layout instead of `custom_copy` for the new dialog tests**
- The plan's precondition for Task 2 names `Custom/Symbols/IC_Battery_Charger_TI.kicad_sym`, which a worktree does not have (submodules are not initialised). The new dialog tests use `make_item_dialog` (a `write_custom_layout` copy with `IC_Battery_Charger_TI`) so `test_placeholder_blocks_install` and the rest run and never skip here; the plan's expected `✓ Ready to install: 2 new, 1 modified, 0 unchanged files` holds on that layout. On the mirror with the real `Custom/` the full set also passes (see Verification).

**5. [Plan adjustment] Footprint field also framed**
- Beyond the plan's list, the read-only Footprint field and the three never-blocked fields (Datasheet, Description, Manufacturer) are framed too so every row has the same edges; they are never highlighted.

**6. [Plan adjustment] `Updating preview...` as a plain status line**
- The plan lists it as a reason; `blocking_reasons` returns it (alone) as specified, but the strip shows it as plain MUTED text without the `Install is blocked` prefix and link, which keeps the 05-07 test `dialog._strip.text() == "Updating preview..."`.

**Additions beyond the plan:** `test_one_build_at_a_time`, `test_strip_link_ignores_unknown_href`, `test_strip_look`, `test_field_frames_reserve_their_border`, `test_ctrl_return_shortcut_is_registered`, `test_library_token_line_escapes_markup`, `test_blocking_reasons_issue_targets_link_the_control`, `test_kind_label`, and a case for a bad_rename that stays because its name is typed but taken.

**Total deviations:** 1 auto-fixed bug, 2 missing-critical additions, 3 plan adjustments. **Impact:** none on scope.

## Issues Encountered

None.

## Verification

- Bare worktree: `tests/test_import_form.py tests/test_import_dialog.py tests/test_import_preview.py tests/test_preview_tree.py tests/test_importer_layering.py` give 131 passed, 12 skipped. All 12 skips are `custom_copy`-based tests of earlier plans (11 in `test_import_dialog.py`, 1 in `test_import_preview.py`: Custom submodule not checked out); none of this plan's 35 new tests skip. Run 3 times in a row without a flake.
- Full suite in the bare worktree: 1462 passed, 78 skipped, 4 deselected (the known KiCad 10 baseline failures `test_version_real_cli_into_20241209`, `test_library_real_cli_new_header`, `test_noop_second_plan_after_normalised_apply`, `test_real_cli_upgrades_ul_symbol_deterministically`; the `test_install_e2e.py` baseline cases skip in a bare worktree). The 78 skips are the same Custom/Wurth/symlink-privilege skips as before this plan (none added).
- Custom-enabled mirror (worktree sources plus a read-only copy of the main checkout's `Custom/` in the scratchpad): `test_import_form`, `test_import_dialog`, `test_import_preview`, `test_preview_tree`, `test_importer_layering`, `test_main_window`, `test_main_window_import`, `test_import_content`, `test_library_table_widget` give 243 passed, 0 skipped, so the plan's own `-rs` "no SKIPPED line" check holds there (the 11 plan 05-01 tests, including the tracer that reads `✓ Ready to install: 2 new, 1 modified, 0 unchanged files` on the real `Custom/`, pass with the new strip). Dialog and form tests run 3 more times there without a flake.
- Acceptance greps: `form.py` holds `def library_tokens(`, `def library_badge(`, `def blocking_reasons(`, `class Reason`, `class FormStatus`, `Updating preview...`, `Select at least one footprint`, `MPN is empty - it names the 3D model file`, `Choose Overwrite, Rename or Skip for`, `Enter a new name for`, and no PySide6 import; the dialog holds `new - creates .kicad_sym + .pretty` (docstring; the text itself comes from `form.library_badge`), the hint text, `Updating...`, `insertSeparator`, `html.escape`, `Install is blocked: `, `setOpenExternalLinks(False)`, `fieldFrame`, `Ctrl+Return`, `reason:`.
- An offscreen screenshot (scratchpad) confirms the amber frame around the combo (edge pixel `#8A5200`), the badge, the amber token, the hint and the AMBER_TINT strip with underlined links; the offscreen platform has no fonts, so the look with real fonts is a UAT item (D9).
- The plan's `<automated>` commands name `./env/Scripts/python.exe`, which does not exist in a worktree; the main checkout's interpreter was used by absolute path, as instructed.

## Known Stubs

None. `_reason_targets` / `_field_frames` have no conflict or rename entries yet; plan 05-10 registers them (the reasons and `blocking_reasons` already produce `conflict:{key}` and `rename:{key}` targets, tested).

## Threat Flags

None beyond the plan's threat model. T-05-27 (markup or link injection): every interpolated string in the strip, token line and tooltip is `html.escape`d, hrefs are internal `reason:{n}` ids that are bounds-checked, `setOpenExternalLinks(False)` (`test_strip_escapes_markup`, `test_strip_link_ignores_unknown_href`, `test_library_token_line_escapes_markup`). T-05-28 (placeholder library): a UI reason plus the planner's `install.placeholder_library` (`test_placeholder_blocks_install`). T-05-29 (Enter installs): no default buttons, Ctrl+Return only when enabled (`test_ctrl_return_and_no_default_buttons`).

## Next Phase Readiness

- 05-10 registers conflict rows and rename fields in `_reason_targets` and `_field_frames` under `conflict:{key}` and `rename:{key}`, removes them with the row (a stale entry would point at a deleted widget), and fills `self._resolutions`; `blocking_reasons` already lists the conflict and empty-rename reasons and `_apply_blocked_frames` already highlights any registered frame.
- Manual UAT (05-11): the look at 100% and 150% scaling with real fonts (badge wrapping, token line, amber frames, strip), and tabbing through the strip links.

## Self-Check: PASSED

- Files exist: `kicad_lib_manager/importer/form.py`, `kicad_lib_manager/widgets/import_dialog.py`, `tests/test_import_form.py`, `tests/test_import_dialog.py`.
- Commits e111518, ae3f620, 9ad32ea and 72cbf43 are ancestors of HEAD; `git rev-list --count` from the base gives 4 before this SUMMARY commit.
