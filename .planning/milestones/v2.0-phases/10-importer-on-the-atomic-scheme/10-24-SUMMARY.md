---
phase: 10-importer-on-the-atomic-scheme
plan: 24
subsystem: importer
tags: [official-footprint, footprint-picker, pad-check, install-plan, import-dialog, kicad-10]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "footprint index with rank, rank_with_pads and pad_numbers (10-03), atomic gate in build_plan (10-21), reason strip and ATOMIC_TARGETS (10-22), PartText and generated text (10-23)"
provides:
  - "InstallOptions.footprint_target and official_footprint; InstallPlan.unused_models and footprint_target"
  - "Planner official mode: the symbol's Footprint field reads the picked KiCad Lib:FP, no footprint, model or mkdir op, vendor footprints and STEP files listed as Not used"
  - "Issue codes install.official_unavailable, install.official_missing, install.official_unknown, install.pad_mismatch"
  - "verify_install resolves an official link inside KiCad's footprints folder"
  - "Dialog destination radio buttons and the ranked, filterable official picker built on a TaskWorker"
affects: [10-25 help page, phase 10 verification]

actuals:
  tokens: 16000
  tasks: 3
  commits: 5
plan_head_before: 969b6ca72afdefeb432e9ce774188c6e9e09bc18
plan_head_after: acbc5e78000c598ee9861219504684e7f6721d90

tech-stack:
  added: []
  patterns:
    - "Official mode is a branch of build_plan (is_official), not a second planner: the same symbol render, gate and issue list run, with the footprint and model decisions empty"
    - "The picker list is a pure function official_candidates(footprint_index, folder, ...) run on a TaskWorker and tested without Qt"

key-files:
  created:
    - tests/test_official_footprint.py
  modified:
    - kicad_lib_manager/importer/plan.py
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/verify.py
    - kicad_lib_manager/importer/preview.py
    - kicad_lib_manager/importer/form.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/customfixtures.py
    - tests/test_gate_reasons.py
    - tests/test_main_window_import.py

key-decisions:
  - "A stock sibling that links a footprint raises it once, not once per sibling: on KiCad 10 sixty-three of the seventy-five CSD siblings link TDSON-8-1, and counting them put TDSON-8-1 (6300) far above Package_SON:Texas_DQK (470), contradicting the plan's own truth that the CSD sample ranks Texas_DQK first"
  - "In official mode the footprint description and tags rows stay visible but are disabled and empty, with the hint 'KiCad's own footprints are never changed'; any text typed into them is dropped on the switch, as a footprint change already does"
  - "install.official_missing reads as the plain sentence 'Pick an official KiCad footprint' (no 'Error:' prefix) and targets the picker"
  - "A package without footprints may use an official one; the 'no footprint' refusal applies only to the shared destination"
  - "The pad check compares the official pads with the symbol's pins (verify.pin_pad_mismatch) and with the vendor footprint (install.pad_mismatch: missing = vendor pads the official lacks, extra = official pads the vendor lacks); both are WARNINGs"

patterns-established:
  - "InstallPlan.footprint_target records the destination so the preview words its Not used rows for the official case"

requirements-completed: [LIB-06]

coverage:
  - id: D1
    description: "With 'Use an official KiCad footprint' the symbol's Footprint field reads the picked KiCad Lib:FP; no footprint, model or Atomic_Footprints folder is written, and the vendor footprint and STEP files are listed under Not used"
    requirement: "LIB-06"
    verification:
      - kind: unit
        ref: "tests/test_official_footprint.py#test_a_part_links_the_official_footprint_end_to_end"
        status: pass
      - kind: unit
        ref: "tests/test_official_footprint.py#test_an_official_install_never_writes_into_kicads_installation"
        status: pass
    human_judgment: false
  - id: D2
    description: "An unknown, wrong-case, missing or unavailable official link refuses with a plain reason that targets the picker and writes nothing"
    requirement: "LIB-06"
    verification:
      - kind: unit
        ref: "tests/test_official_footprint.py#test_an_official_link_that_cannot_be_verified_refuses_and_writes_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_official_footprint.py#test_a_wurth_footprint_is_never_offered_or_accepted_as_official"
        status: pass
    human_judgment: false
  - id: D3
    description: "A pad difference with the symbol or the vendor footprint is an amber warning and never blocks"
    requirement: "LIB-06"
    verification:
      - kind: unit
        ref: "tests/test_official_footprint.py#test_a_pad_difference_is_a_warning_and_never_blocks"
        status: pass
      - kind: unit
        ref: "tests/test_official_footprint.py#test_matching_pads_raise_no_warning"
        status: pass
    human_judgment: false
  - id: D4
    description: "On the workstation's KiCad 10 the CSD sample ranks Package_SON:Texas_DQK first and its pads match, and kicad-cli loads a symbol linked to an official footprint"
    requirement: "LIB-06"
    verification:
      - kind: integration
        ref: "tests/test_official_footprint.py#test_real_kicad_ranks_texas_dqk_first_for_the_csd_sample_and_its_pads_fit"
        status: pass
      - kind: integration
        ref: "tests/test_official_footprint.py#test_cli_loads_a_symbol_linked_to_an_official_footprint"
        status: pass
    human_judgment: false
  - id: D5
    description: "The dialog's destination choice and picker: the list is ranked and filters as the owner types, built off the GUI thread, and fits the left pane"
    requirement: "LIB-06"
    verification:
      - kind: automated_ui
        ref: "tests/test_official_footprint.py#test_the_picker_lists_kicads_footprints_with_the_best_match_first_and_picks_nothing"
        status: pass
      - kind: automated_ui
        ref: "tests/test_official_footprint.py#test_typing_filters_the_list_by_substring_ignoring_case"
        status: pass
      - kind: automated_ui
        ref: "tests/test_official_footprint.py#test_the_destination_choice_and_picker_fit_the_left_pane"
        status: pass
    human_judgment: false
  - id: D6
    description: "How the two radio buttons, the picker, the muted hints and the disabled rows look and read"
    verification: []
    human_judgment: true
    rationale: "Wording, placement and spacing of the new Footprint section controls are owner-facing UI judgment that no test asserts"

duration: 95min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 24: Official KiCad footprint destination Summary

**The Import dialog can link one of KiCad's own footprints instead of installing the vendor one: only the symbol is written, KiCad's model satisfies the atomic gate, a ranked and filterable picker offers the footprints, and a pad difference is only a warning.**

## Performance

- **Duration:** about 95 min
- **Completed:** 2026-10-27
- **Tasks:** 3 (1 tracer, 2 auto; the third carried the behaviour tests)
- **Files modified:** 10 (1 created)

## Accomplishments

- `build_plan` has an official branch: it refuses an unavailable, missing or unknown link (exact-case match through `FootprintIndex.contains`), then plans only the symbol library with the picked link, `ki_fp_filters` set to the footprint name, every vendor footprint in `unused_footprints` and every vendor model in the new `unused_models`. The atomic gate resolves the link and KiCad's own `${KICAD10_3DMODEL_DIR}` model through the footprints folder, so an official footprint with its model passes.
- Pad checks run on the symbol written for the official footprint (`verify.pin_pad_mismatch`) and against the vendor footprint (`install.pad_mismatch`); both are WARNINGs and the tests prove they never block.
- `verify_install` reads an official link from KiCad's folder with exact listings; the post-install table step already added no `fp-lib-table` entry for a footprint library other than `Atomic_Footprints` and a test now pins that.
- The dialog gains the two radio buttons ("Install the vendor footprint into Atomic_Footprints", "Use an official KiCad footprint") and an editable picker with a contains, case-insensitive completer. The list is built on a `TaskWorker` (`official_candidates`): best matches by vendor package code, sibling links and pad fit, then every other KiCad footprint sorted ignoring case. Nothing is preselected.
- Official mode disables the footprint Name, the footprint description and tags (and their Regenerate buttons) with the hint "KiCad's own footprints are never changed", and Add 3D model... with the note "KiCad's own 3D model is used". Without a KiCad install the official radio button is off with "KiCad's footprints were not found".
- The model reason now reads "3D model: <text>. Use Add 3D model... or an official KiCad footprint".

## Task Commits

1. **Task 1: tracer, a part linked to Package_TO_SOT_SMD:SOT-23-5 planned, gated, applied, verified and shown** - `e175928` (feat)
2. **Task 2: destination choice and ranked, filterable picker** - `e9a98dc` (feat)
3. **Task 3: refusals, KiCad folder untouched, tables, the real KiCad 10 CSD case** - `e3111aa` (test)
4. **Layering fix for verify** - `ad2c7ab` (fix)
5. **kicad-cli load check of an official-link symbol** - `acbc5e7` (test)

The tracer gate ran its automated verify (`tests/test_official_footprint.py`, `tests/test_install_verify.py`) after the commit: it passed, so expansion went ahead.

## Files Created/Modified

- `kicad_lib_manager/importer/plan.py` - `footprint_target`, `official_footprint`, `unused_models`, `InstallPlan.footprint_target`
- `kicad_lib_manager/importer/planner.py` - the official branch, refusals, pad checks
- `kicad_lib_manager/importer/verify.py` - official-link-aware `_linked_footprint`, public `natural_order`
- `kicad_lib_manager/importer/preview.py` - Not used rows for the vendor footprint and models; Footprint Filter row for an official link
- `kicad_lib_manager/importer/form.py` - `FormValues` fields, `official_footprint` reason target, plain "Pick an official KiCad footprint", the new model sentence
- `kicad_lib_manager/widgets/import_dialog.py` - radio buttons, picker, `official_candidates`, `ImportCore.footprint_index`, `OpenOutcome.stock`
- `tests/test_official_footprint.py` - 25 tests (new); `tests/customfixtures.py` - the fake KiCad's SOT-23-5 now has its five pads; `tests/test_gate_reasons.py`, `tests/test_main_window_import.py` - the sentence and the tables row

## Decisions Made

See `key-decisions` above. The sibling-weight decision is the one the next reader should know: the plan's ranking formula (100 per linking sibling) cannot rank Texas_DQK first on the real KiCad 10.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Sibling link count ranked the wrong footprint first on real KiCad 10**
- **Found during:** Task 3 (real KiCad 10 test)
- **Issue:** The plan counts the Footprint fields of the stock siblings as `linked`. On KiCad 10 the "CSD" family has 75 Transistor_FET siblings, 63 of which link `Package_TO_SOT_SMD:TDSON-8-1` and 4 `Package_SON:Texas_DQK`, so TDSON-8-1 scored 6300 against 470 and the plan's truth "the CSD sample ranks Package_SON:Texas_DQK first" failed.
- **Fix:** `_sibling_links` gives each linked footprint weight 1. Texas_DQK then scores 170 (sibling 100, leading letters 30, pad match 40) against 100 for the others. Ranking was left to discretion in the plan's Flagged Assumptions.
- **Files modified:** `kicad_lib_manager/widgets/import_dialog.py`
- **Verification:** `test_real_kicad_ranks_texas_dqk_first_for_the_csd_sample_and_its_pads_fit` passes on this workstation's KiCad 10.
- **Committed in:** `e9a98dc`

**2. [Rule 3 - Blocking] verify imported stems, which the importer layering test forbids**
- **Found during:** full-suite run after Task 3
- **Issue:** `importer.verify: imports importer.stems, which its ALLOWED entry forbids`.
- **Fix:** "not the shared library" is `plan.footprint_library != plan.pretty_path.stem`, the same test `main_window` uses.
- **Files modified:** `kicad_lib_manager/importer/verify.py`
- **Verification:** `tests/test_importer_layering.py` passes.
- **Committed in:** `ad2c7ab`

**3. [Rule 3 - Blocking] The fake KiCad's SOT-23-5 had two pads, not the five the plan describes**
- **Found during:** Task 1
- **Issue:** The tracer needs a pad difference with a 2-pad vendor footprint; `write_fake_kicad` wrote the default two pads.
- **Fix:** `write_fake_kicad` now writes pads 1 to 5 (`OFFICIAL_PADS`); no other test depends on its pad count.
- **Files modified:** `tests/customfixtures.py`
- **Committed in:** `e175928`

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking). **Impact on plan:** none on scope; the first changes only the ranking weight, within the plan's discretion.

## Issues Encountered

- `tests/test_main_window_import.py` already had a test with an official-style footprint library name from plan 10-11 (`test_tables_a_footprint_library_outside_the_repo_gets_no_fp_entry`). A new test pins the realistic case (new symbol library, official link, shared footprint library unlisted).
- The scratch `.git/worktrees/.../gsd-plan-head-before-10-24` ledger could not be written (the sandbox blocks writes outside the worktree), so `plan_head_before` is the base SHA the orchestrator named in the prompt.

## Known Stubs

None.

## Test Results

- `tests/test_official_footprint.py`: 25 passed (including the real KiCad 10 case and the kicad-cli load check).
- `-m "not wurth"`: 2847 passed, 31 skipped, 1 failed (the layering test, fixed in `ad2c7ab` and re-run green). Skips are the known ones: Custom submodule not checked out, licence-restricted samples absent, symlinks not permitted, opt-in UAT directories.
- `-m kicad_cli`: 32 passed, 2 skipped (absent licence-restricted samples), run before the final kicad-cli test; that test passes on its own.

## Self-Check: PASSED

Created and modified files exist, the five commits are in the branch history (`e175928`, `e9a98dc`, `e3111aa`, `ad2c7ab`, `acbc5e7`), and all three tasks' acceptance greps and test counts hold.

## Next Phase Readiness

Ready for 10-25 (help page): the public strings `VENDOR_FOOTPRINT_TEXT` and `OFFICIAL_FOOTPRINT_TEXT` in `import_dialog.py` name the two choices, as `ADD_MODEL_TEXT` does for the model button. `widgets/help_dialog.py` was not touched.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*
