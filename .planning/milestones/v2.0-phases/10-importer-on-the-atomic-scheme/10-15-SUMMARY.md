---
phase: 10-importer-on-the-atomic-scheme
plan: 15
subsystem: importer
tags: [atomic-scheme, library-suggestion, sibling-vote, qcompleter, pyside6]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "importer/stems.py name_verdict and allowed stems (10-01), siblings.py own_index/stock_index/pick (10-03), categories.py classify (10-04), build_plan name rule and FormStatus.allowed (10-10), shared footprint library rules (10-14)"
provides:
  - "importer/suggest.py: Alternative, LibrarySuggestion(name, source, reason, alternatives, related_stems, issues), suggest_library(meta, *, own, stock, allowed), suggestion_text, existing_libraries, NO_STOCK_TEXT"
  - "the dialog open worker builds the own and stock sibling indexes off the GUI thread and passes them to suggest_library"
  - "library picker: the owner's Atomic_ libraries, a divider, every other allowed Atomic_<stem>, substring completer, D-11 spelling correction with note, ask hint, reason in the tooltip only"
  - "form.NEW_LIBRARY_BADGE = 'new - creates .kicad_sym'; form.library_badge(name, existing, allowed=None)"
affects: [10-16, 10-17, 10-18, 10-25, phase-10-verification]

actuals:
  tokens: 24000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "suggestion order: own Atomic_ siblings, KiCad stock siblings by strict majority, category map, else ask (empty name)"
    - "tooltip text is built as <p> + html.escape(text) + </p> (T-10-20)"
    - "QComboBox swaps wrong-case typed text for the list entry itself on editingFinished, so the dialog remembers the typed text to raise the spelling note"

key-files:
  created:
    - tests/test_suggest_atomic.py
  modified:
    - kicad_lib_manager/importer/suggest.py
    - kicad_lib_manager/importer/form.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_import_dialog.py
    - tests/test_import_form.py
    - tests/test_naming_suggest.py
    - tests/test_real_vendor_samples.py
    - tests/test_samacsys_adapter.py
    - tests/test_adapters.py
    - tests/test_vendor_install.py

key-decisions:
  - "Alternatives of a category or ask result come from the last non-empty sibling pick, so a split family such as MAX4999 keeps its counts in the tooltip text"
  - "suggestion_text always ends with a period: the reason, then '. Other matches: <stem> (<n>), ...' with the Atomic_ prefix dropped from the stems"
  - "The open worker passes tools.allowed_stems (or None) to own_index, existing_libraries and suggest_library, so a newer KiCad's stems count everywhere"
  - "The combo tooltip is set on the combo itself and only while the field holds the suggested name"

patterns-established:
  - "Dialog logs suggestion.issues (the no-KiCad INFO line) through issues_logged when the package is opened"

requirements-completed: [LIB-04, LIB-05]

plan_head_before: c9ca075857a33a62d1c1938034d72a75aa6fb42c
plan_head_after: 0af0f2fab27c62a592b050ff7649393d4e127b81

coverage:
  - id: D1
    description: "The suggestion tries own Atomic_ siblings, then KiCad's stock siblings by strict majority, then the category map, else asks, and never holds a manufacturer"
    requirement: LIB-04
    verification:
      - kind: unit
        ref: "tests/test_suggest_atomic.py#test_own_library_beats_the_stock_family"
        status: pass
      - kind: unit
        ref: "tests/test_suggest_atomic.py#test_a_suggestion_is_empty_or_passes_the_name_rule_and_never_holds_a_manufacturer"
        status: pass
      - kind: unit
        ref: "tests/test_suggest_atomic.py#test_split_family_falls_to_ask_with_the_counts"
        status: pass
    human_judgment: false
  - id: D2
    description: "Real samples: CSD85301Q2 gives Atomic_Transistor_FET with its tooltip text on KiCad 10, RS3 gives Atomic_Converter_DCDC_Isolated, ATXK asks"
    requirement: LIB-04
    verification:
      - kind: integration
        ref: "tests/test_real_vendor_samples.py#test_real_ultra_suggestion_from_kicad_10"
        status: pass
      - kind: integration
        ref: "tests/test_real_vendor_samples.py#test_real_samacsys_suggestion"
        status: pass
      - kind: integration
        ref: "tests/test_real_vendor_samples.py#test_real_ultra_oscillator_is_left_for_the_owner"
        status: pass
    human_judgment: false
  - id: D3
    description: "Opening a package prefills the library from the sibling indexes built on the open worker, with the reason in an escaped tooltip"
    requirement: LIB-04
    verification:
      - kind: automated_ui
        ref: "tests/test_suggest_atomic.py#test_opening_csd_in_the_dialog_prefills_the_family_library_with_its_reason"
        status: pass
      - kind: automated_ui
        ref: "tests/test_import_dialog.py#test_core_calls_run_off_the_gui_thread"
        status: pass
    human_judgment: false
  - id: D4
    description: "The picker lists the owner's Atomic_ libraries, a divider, then every other allowed name; typing filters by substring; a wrong-case name is corrected with a plain note; a nothing-placed part starts empty with the ask hint and blocks Install; the badge reads existing, new - creates .kicad_sym or nothing"
    requirement: LIB-05
    verification:
      - kind: automated_ui
        ref: "tests/test_import_dialog.py#test_library_combo_lists_the_owners_atomic_libraries_then_every_other_allowed_name"
        status: pass
      - kind: automated_ui
        ref: "tests/test_import_dialog.py#test_typing_filters_the_library_list_by_substring_ignoring_case"
        status: pass
      - kind: automated_ui
        ref: "tests/test_import_dialog.py#test_a_name_differing_only_by_case_is_corrected_when_editing_finishes"
        status: pass
      - kind: automated_ui
        ref: "tests/test_import_dialog.py#test_nothing_placing_the_part_leaves_the_library_empty_and_blocks_install"
        status: pass
      - kind: automated_ui
        ref: "tests/test_import_dialog.py#test_library_badge_reads_existing_new_or_nothing"
        status: pass
    human_judgment: false
  - id: D5
    description: "How the picker, the completer popup, the divider and the note look and feel to the owner in the real dialog"
    verification: []
    human_judgment: true
    rationale: "Popup rendering, divider look and focus-out behaviour in a real window are not asserted by the offscreen tests"

duration: 95min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 15: The Atomic_ library suggestion and picker Summary

**Atomic_ library suggestion (own siblings, KiCad siblings by majority, category map, else ask) built off the GUI thread, with a substring-filtering library picker, case correction and an escaped reason tooltip**

## Performance

- **Duration:** about 95 min
- **Tasks:** 3
- **Files modified:** 11 (10 modified, 1 created)

## Accomplishments

- `importer/suggest.py` now suggests `Atomic_<allowed stem>` or nothing: own libraries first ("Suggested from n similar parts in your Atomic_X"), then KiCad's stock siblings ("... in KiCad's X"), then the category map ("Suggested from the vendor category Power Supply and the description"), else an empty name. No manufacturer ever reaches the name. Without KiCad's symbols the stock step is skipped with one INFO line and the other two steps still run.
- The dialog's open worker builds `own_index` and `stock_index` (with the progress callback) and calls `suggest_library` there, so KiCad's folders are never read on the GUI thread. The reason shows only in the library combo's tooltip, as `<p>` + `html.escape(text)` + `</p>`.
- The picker lists the owner's existing Atomic_ libraries, a divider, then every other allowed Atomic_ name; v1 names, hand-made names and `Atomic_Footprints` are not listed. A substring, case-insensitive completer filters it. A name that differs from an allowed one only by case is corrected, with the note "Spelling corrected to <name>". A part nothing places starts empty with the hint "Pick a library, or type Atomic_ and a KiCad library name", and Install stays blocked by "Pick or type a library name".
- The v1 token line, its hint, `form.library_tokens` and all v1 suggestion machinery (placeholders, type, subcategory, ranking) are gone. The badge reads "new - creates .kicad_sym" for an allowed library that is not on disk yet, "existing" for a listed one, nothing for a refused name.
- Verified against the real samples on this machine (KiCad 10 installed): CSD85301Q2 gives `Atomic_Transistor_FET` with "Suggested from 75 similar parts in KiCad's Transistor_FET. Other matches: Diode (2).", RS3-1212S/H3 gives `Atomic_Converter_DCDC_Isolated`, USB4145 gives `Atomic_Connector`, ATXK-H14 asks.

## Task Commits

1. **Task 1: tracer, CSD prefilled end to end with its reason in the tooltip** - `a0dd433` (feat). This commit also holds the picker, the correction and the form changes of Task 2, because the removal of the v1 suggestion types and `library_tokens` breaks the dialog and form imports unless they move together (see Deviations).
2. **Task 2: picker tests and the case-correction fix** - `1fd05f5` (feat)
3. **Task 3: real samples and the retired v1 suggestion tests** - `0af0f2f` (test)

**Plan metadata:** the docs commit that holds this SUMMARY follows.

## Files Created/Modified

- `kicad_lib_manager/importer/suggest.py` - Atomic_ suggestion, `suggestion_text`, `existing_libraries`; manufacturer helpers kept for the planner
- `kicad_lib_manager/importer/form.py` - new-library badge text, `library_badge(name, existing, allowed=None)`, `library_tokens` removed
- `kicad_lib_manager/widgets/import_dialog.py` - ImportCore `list_symbol_libs`/`own_index`/`stock_index`, open worker, picker with QCompleter, note, tooltip
- `tests/test_suggest_atomic.py` - new: order, majority, category, ask, no-KiCad, own-over-stock, no-manufacturer, plain wording, the dialog tracer
- `tests/test_import_dialog.py`, `tests/test_import_form.py` - picker, badge, note, tooltip, off-thread tests
- `tests/test_naming_suggest.py`, `tests/test_adapters.py`, `tests/test_samacsys_adapter.py`, `tests/test_real_vendor_samples.py`, `tests/test_vendor_install.py` - v1 suggestion tests removed or retargeted

## Decisions Made

- Alternatives of a category or ask result come from the last non-empty sibling pick, so a split family (MAX4999) keeps its counts as "Other matches" text.
- The open worker passes the tool's allowed stems to `own_index`, `existing_libraries` and `suggest_library`, so a newer KiCad's extra stems are honoured everywhere.
- The completer's `activated` signal is connected beside `textActivated` (RESEARCH A10), and the typed text is remembered because QComboBox itself swaps wrong-case text for the list entry when editing ends.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 2 source landed in the Task 1 commit**
- **Found during:** Task 1
- **Issue:** The new `LibrarySuggestion` and the removal of `placeholder_tokens` break `form.py` and the dialog's library section at import time, so the picker, the form change and the suggestion could not be committed apart.
- **Fix:** One source commit (`a0dd433`) carries suggest.py, form.py and import_dialog.py; Task 2 then added its tests. TDD RED/GREEN for Task 2 was therefore not a separate failing-test commit. To make up for it, two mutations were applied by hand and reverted (completer filter mode changed to starts-with, case correction disabled) and the matching tests failed as they should.
- **Files modified:** kicad_lib_manager/importer/suggest.py, kicad_lib_manager/importer/form.py, kicad_lib_manager/widgets/import_dialog.py
- **Committed in:** a0dd433

**2. [Rule 1 - Bug] QComboBox hid the wrong-case input from the correction**
- **Found during:** Task 2 (test run)
- **Issue:** On editingFinished the combo replaces wrong-case text with the matching list entry by itself, so the planned "text differs only by case" check saw already-correct text and never showed the note or rebuilt.
- **Fix:** The dialog keeps the text as typed (`_typed`, set on textEdited) and raises the note and a rebuild when it differs from the corrected text only by case; the original name_verdict check stays for names the combo did not swap.
- **Files modified:** kicad_lib_manager/widgets/import_dialog.py
- **Verification:** `test_a_name_differing_only_by_case_is_corrected_when_editing_finishes`, `test_a_pick_with_the_wrong_case_is_corrected_too`
- **Committed in:** 1fd05f5

**3. [Rule 3 - Blocking] tests/test_vendor_install.py retargeted**
- **Found during:** Task 3
- **Issue:** `test_vendor_suggestion_snapeda` (not in the plan's file list) called the removed v1 `suggest_library(meta, existing)`.
- **Fix:** It now calls `suggest_library(meta, stock=None)` and expects `Atomic_Connector`; the unused v1 mirror imports were dropped.
- **Files modified:** tests/test_vendor_install.py
- **Committed in:** 0af0f2f

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** None on scope; one extra test file touched, and the Task 2 TDD sequence is documented above.

## Issues Encountered

- tests/test_main_window_import.py needed no change: it passed unchanged in the full run.
- The help page (`widgets/help_dialog.py`, "Target library") still describes the v1 amber guesses and the Type/SubCategory/Manufacturer words. It is rewritten by plan 10-25, so it was left alone here.

## TDD Gate Compliance

Tasks 1 and 3 are not TDD. Task 2 is `tdd="true"`, but its implementation was committed with Task 1 (`a0dd433`) and its tests in `1fd05f5`, so there is no `test(10-15)` commit before the `feat(10-15)` commit for it. Behaviour was checked by mutation (see Deviation 1) instead of a recorded RED run.

## Known Stubs

None.

## Threat Flags

None. T-10-20 (tooltip built from escaped text, plain-text note and badge), T-10-21 (indexes built on the open worker) and T-10-22 (the picker offers only verdict-ok names; build_plan stays the authority) are implemented and tested.

## User Setup Required

None - no external service configuration required.

## Verification Results

- `tests/test_suggest_atomic.py tests/test_importer_layering.py`: pass
- `tests/test_import_dialog.py tests/test_import_form.py`: 210 passed
- `tests/test_suggest_atomic.py tests/test_real_vendor_samples.py tests/test_samacsys_adapter.py tests/test_adapters.py tests/test_naming_suggest.py -rs`: 97 passed, 0 skipped (KiCad 10 and the vendor samples are present on this machine)
- `pytest -m "not wurth" -q -rs`: 2741 passed, 13 skipped, 3 deselected. The skips are the Custom-submodule tests (submodule not checked out in the worktree) and the two symlink-privilege tests.

## Next Phase Readiness

- Ready for the plans that remove `TokenChoice`, `manufacturer_token`, `manufacturer_choice` and the host tables (10-17, 10-18); they are still imported by the planner and `form.field_defaults`.
- The help page text for the Target library section is stale until plan 10-25.

## Self-Check: PASSED

- Files found: suggest.py, form.py, import_dialog.py, tests/test_suggest_atomic.py
- Commits found: a0dd433, 1fd05f5, 0af0f2f

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*
