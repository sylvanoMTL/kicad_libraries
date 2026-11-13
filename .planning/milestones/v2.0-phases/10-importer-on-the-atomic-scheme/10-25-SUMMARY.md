---
phase: 10-importer-on-the-atomic-scheme
plan: 25
subsystem: ui
tags: [help, documentation, pyside6, pytest, uat]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "plans 10-01 to 10-24: the Atomic_ importer, the shared Atomic_Footprints library, the official footprint choice, generated texts and the atomic install gate"
provides:
  - "Importing Parts help page that matches the dialog: Items, Target library, Footprint, Fields, Atomic check"
  - "tests/README.md naming the two synthetic Custom/ fixtures and every conditional skip the suite prints"
  - "The end-of-phase human check (Task 2 human-check) for ROADMAP criteria 1-5, for the verifier to harvest into 10-UAT.md"
affects: [phase-10 verification, 10-UAT.md]

plan_head_before: 1f7ff6893fc6b43b88369d528c30b64d21f702b9
plan_head_after: 124918c9315afa76ed6671abf262906df6bbcf9b

actuals:
  tokens: 5500
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Help tests slice the importing page by h3 heading (_section) instead of by neighbouring words"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_help_dialog.py
    - tests/README.md

key-decisions:
  - "Help names the dialog's own strings through the exported constants (ADD_MODEL_TEXT, OFFICIAL_FOOTPRINT_TEXT, VENDOR_FOOTPRINT_TEXT), so a reworded button cannot leave the page stale"
  - "Regenerate is described by its tooltip (a small button), not as a worded button"
  - "No change to tests/test_atomic_uat.py: the existing KICAD_ATOMIC_UAT_DIR builder already prints the 'Run the app on it:' line the UAT setup relies on"

requirements-completed: [LIB-04, LIB-05, LIB-06, LIB-07, FLD-01, FLD-03]

coverage:
  - id: D1
    description: "Importing Parts help page explains the Atomic_ rule, suggestion and tooltip, refused names, single footprint choice, Atomic_Footprints, official KiCad footprint, Value following MPN, canonical Manufacturer, generated texts with Regenerate, and the install gate with clickable reasons"
    requirement: "LIB-04"
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_import_page_explains_the_atomic_scheme"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_import_page_explains_fields_and_the_install_gate"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_import_page_uses_plain_words"
        status: pass
    human_judgment: true
    rationale: "Whether the wording reads plainly to the owner is a judgement; the tests only check the facts and the banned words"
  - id: D2
    description: "tests/README.md describes synthetic_custom and atomic_custom and lists every conditional skip with the file that prints it"
    verification:
      - kind: other
        ref: "pytest -m 'not wurth' -q -rs (every printed skip reason appears in tests/README.md)"
        status: pass
    human_judgment: false
  - id: D3
    description: "End-of-phase UAT block for ROADMAP criteria 1-5 on a scratch repo (Task 2 human-check)"
    verification: []
    human_judgment: true
    rationale: "Needs the owner to run the app on the scratch copy and look at the dialog and at KiCad 10; the verifier collects the block into 10-UAT.md"

duration: 55min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 25: Help page, test docs and the end-of-phase UAT Summary

**The Importing Parts help page now explains the Atomic_ import from library name to install gate in plain words, tests/README.md names the two synthetic Custom/ fixtures and every skip reason, and the phase's human check is ready for 10-UAT.md.**

## Performance

- **Duration:** about 55 min, most of it the 10 min full-suite run
- **Tasks:** 2 of 2
- **Files modified:** 3

## Accomplishments

- Rewrote the Items, Target library and Fields sections of the importing page and added two sections, Footprint and Atomic check, in flow order (Items, Target library, Footprint, Fields, Atomic check, Conflicts). The page covers the `Atomic_` library rule and where the suggestion comes from (own libraries, KiCad's libraries, vendor category and description) with its tooltip, the refused names (a KiCad library name on its own, a name holding a maker, old names), case correction, the shared `Atomic_Footprints` library, the official KiCad footprint choice with the best matches first, reuse of an identical footprint and Overwrite, Rename and Skip on a differing one, Value equal to the MPN, the standard Manufacturer spelling, the three generated texts with Regenerate, and the install gate with clickable reasons.
- The page names no placeholder word, no "Make linked" button and no raw field name. The old paragraph about generic words in the library name is gone.
- `tests/test_help_dialog.py` gained a `_section` helper and four tests (section order, the Atomic_ scheme, fields and install gate, plain words). The two existing Items slices now use the helper.
- `tests/README.md` now describes `synthetic_custom` (v1 names, models the live tree) and `atomic_custom` (Atomic_ targets, footprints in one `Atomic_Footprints.pretty`), says tests go through `footprint_library_for`, and lists the skip messages with the files that print them: no stock symbols folder (five files), installed KiCad is not version 10 (`test_stems.py`, `test_siblings.py`), no footprints folder, the ul_ATXK-H14 sample and the Ultra Librarian sample skips. The "exactly four" workstation statement is unchanged.
- The Task 2 human check (setup S1-S3 and checks 1-11, each tagged with its ROADMAP criterion) is left in 10-25-PLAN.md for the verifier to harvest. It runs on the scratch repo from `KICAD_ATOMIC_UAT_DIR` and a scratch Destination folder, never on the live `Custom/` or the owner's real tables.

## Task Commits

1. **Task 1: The help page explains the Atomic_ import from start to install** - `6b34f9b` (feat)
2. **Task 2: Test docs and the end-of-phase UAT checklist** - `124918c` (docs)

## Verification

- `tests/test_help_dialog.py`: 14 passed (10 existing, 4 new).
- Acceptance greps for Task 1: one `<h3>Atomic check</h3>`, one `<h3>Footprint</h3>`, zero non-comment `SubCategory`.
- Full run `-m "not wurth" -q -rs` in this worktree: 2853 passed, 31 skipped, 3 deselected, 0 failed. Every skip reason printed is listed in tests/README.md. The skips here are worktree-specific (Custom submodule not checked out, licence-restricted samples absent) plus the two symlink skips and the two UAT-builder skips; the exact-four statement concerns the workstation checkout and could not be re-measured here.

## Deviations from Plan

None - plan executed exactly as written. The plan's README step also asked for a "grep the suite" list of every file printing the stock-symbols skip; that grep found five files and all are listed.

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. The help text is static (T-10-36) and the UAT block keeps every write on the scratch repo and the scratch tables folder (T-10-35).

## Next Phase Readiness

Phase 10 plans are complete. The verifier collects the Task 2 human check into 10-UAT.md for the owner to run in one batch. Out of scope and untouched, as instructed: the main window's saved scan and "Rescan this library" help text.

## Self-Check: PASSED

- kicad_lib_manager/widgets/help_dialog.py, tests/test_help_dialog.py and tests/README.md exist and are committed.
- Commits 6b34f9b and 124918c are ancestors of HEAD.
