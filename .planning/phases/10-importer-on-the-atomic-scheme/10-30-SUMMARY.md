---
phase: 10-importer-on-the-atomic-scheme
plan: 30
subsystem: importer
tags: [planner, form, gate-reasons, atomic-scheme, gap-closure]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "10-29 pad-count family filter; the atomic gate (D-21) and blocking_reasons strip (D-25)"
provides:
  - "A refused library name is planned as for a new library that is never read, and reports every library-independent reason before install.invalid_library"
  - "blocking_reasons lists the library reason first"
affects: [10-VERIFICATION check 8, UAT re-run of tests 11 and 14]

actuals:
  tokens: 26000
  tasks: 3
  commits: 4
plan_head_before: 0a81d67049b485fd6430022b43c146298bdf137c
plan_head_after: 148bf9d

tech-stack:
  added: []
  patterns:
    - "A refusal held aside in a list (name_refusal) and appended by refuse() to every blocked return, so it is never lost when an earlier refusal stops the plan"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/form.py
    - tests/test_atomic_targets.py
    - tests/test_install_plan.py
    - tests/test_gate_reasons.py
    - tests/test_import_form.py
    - tests/README.md
    - .planning/phases/10-importer-on-the-atomic-scheme/10-VERIFICATION.md

key-decisions:
  - "Owner 2026-10-29: the library reason comes first, then the plan reasons (UAT test 11)"
  - "Owner 2026-10-29: a refused library name must never produce file operations; the refused plan keeps ops == ()"
  - "Owner 2026-10-29: install.official_missing is out of scope and stays an early refusal; it carries install.invalid_library only through refuse()"
  - "The deferred refusal returns after the official pad checks, so their warnings are listed too"

requirements-completed: [LIB-07, LIB-05]

coverage:
  - id: D1
    description: "ATXK-H14 with an empty library lists the library reason first and the manufacturer, datasheet, description and 3D model reasons after it, in the plan and the form"
    requirement: LIB-07
    verification:
      - kind: unit
        ref: "tests/test_atomic_targets.py#test_an_empty_library_lists_every_reason_at_once"
        status: pass
    human_judgment: false
  - id: D2
    description: "The real dialog shows the five reasons, frames all five fields, keeps Install off and the 3D model reason focuses Add 3D model..."
    requirement: LIB-07
    verification:
      - kind: integration
        ref: "tests/test_gate_reasons.py#test_an_empty_library_lists_every_reason_and_the_model_reason_focuses_add_3d_model"
        status: pass
    human_judgment: true
    rationale: "Whether all five reasons are visible in the three-line strip, or only in its tooltip, is a layout judgment for the UAT re-run"
  - id: D3
    description: "A refused name (empty, Atomic_TI, escaping, v1) never produces an operation, builds a path or reads an existing library"
    requirement: LIB-05
    verification:
      - kind: unit
        ref: "tests/test_atomic_targets.py#test_a_refused_name_builds_no_path_and_writes_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_atomic_targets.py#test_an_existing_v1_library_is_not_read_while_refused"
        status: pass
      - kind: unit
        ref: "tests/test_atomic_targets.py#test_a_refused_name_with_an_empty_mpn_lists_both"
        status: pass
    human_judgment: false
  - id: D4
    description: "blocking_reasons puts the library reason first, after only the Updating short-circuit"
    requirement: LIB-07
    verification:
      - kind: unit
        ref: "tests/test_import_form.py#test_blocking_reasons_put_the_library_reason_first"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-10-29
status: complete
---

# Phase 10 Plan 30: Every reason at once for a refused library name Summary

**build_plan no longer stops at a refused library name: it plans as for a new library it never reads, returns blocked with no operations and every library-independent reason, and blocking_reasons lists the library reason first (G-10-11).**

## Performance

- **Duration:** about 70 min (the 11 min full-suite gate included)
- **Completed:** 2026-10-29
- **Tasks:** 3
- **Files modified:** 8

## Owner decisions of 2026-10-29

- "The library reason comes first, then the plan reasons" (UAT test 11).
- "A refused library name must never produce file operations."
- "install.official_missing is out of scope" and stays an early refusal. When the name is also refused, that plan carries install.invalid_library, through refuse(). This is a consequence of the name refusal, not a change to install.official_missing.
- UAT test 14 stays: ATXK-H14 asks for a library; the dialog test asserts the field stays empty.

## Accomplishments

- `planner.py`: the name verdict is held aside as `name_refusal` and `target_library` (`""` when refused). `refuse()` appends the refusal to every blocked return. The case-twin check, the Symbols folder row, `sym_path` and `sym_exists` are skipped for a refused name, so no file is read and no path is built. Keywords, the related-stem filter and the linking-parts skip use `""`. The atomic gate runs with `rel_path=""`. After the official pad checks, `return refuse()` gives a blocked plan with `ops == ()` whose Issues end with `install.invalid_library`.
- `form.py`: `blocking_reasons` appends the library verdict reason first; `explained()` is unchanged, so a refused name still gives one library line.
- ATXK-H14 with an empty library gives exactly the five reasons, in order, with targets library, manufacturer, datasheet, description and model, at planner, form and real-dialog level.
- Neighbour tests: `/x`, `D:x`, `../../../x`, `Atomic_TI` build no path and write nothing; a corrupt v1 library is not read; an empty MPN with a refused name lists both.

## Task Commits

1. **Task 1 RED:** `ca0666e` (test) - 12 tests failed on the planned assertions (only the library reason listed).
2. **Task 1 GREEN:** `5e9550a` (feat) - planner and form change; 266 tests in the plan's seven files pass.
3. **Task 2:** `10adba3` (test) - refused-name neighbours and the form-level order (guards; they passed on the Task 1 code).
4. **Task 3:** `148bf9d` (docs) - check 8 in two places and the tests/README.md skip row.

**Planner and form commit:** `5e9550a`. **Plan metadata:** the docs(10-30) SUMMARY commit that follows.

## TDD Gate Compliance

- RED: `ca0666e`. The target tests `test_an_empty_library_lists_every_reason_at_once` and `test_an_empty_library_lists_every_reason_and_the_model_reason_focuses_add_3d_model` failed on the planned assertion (`['install.invalid_library'] == [...five codes]`; the strip held one reason). Semantic assessment: the target tests executed and failed for the intended reason; no import, fixture or collection fault. The 10 single-ERROR tests updated by the plan failed too, as the diagnosis predicted.
- GREEN: `5e9550a`. REFACTOR: none needed.

## Decisions Made

None beyond the owner decisions above; followed the plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan input] Empty MPN given as `cleared`, not `mpn=""`**
- **Found during:** Task 2 (`test_a_refused_name_with_an_empty_mpn_lists_both`)
- **Issue:** `InstallOptions(mpn="")` is normalised to `None` ("not set") by `__post_init__`, so it never reaches the empty-MPN refusal; the plan's literal input gave `install.atomic.description` instead of `install.empty_required`.
- **Fix:** The test builds `InstallOptions(library="Atomic_TI", cleared=frozenset({"mpn"}))`, the way `tests/test_install_options_clear.py` does. Expected codes and form pairs are as the plan states.
- **Files modified:** tests/test_atomic_targets.py
- **Committed in:** 10adba3

**2. [Environment] ATXK-H14 sample copied into the worktree**
- The zip is git-ignored and absent from the worktree, so the two new tests would skip. I copied it (read-only) from the main checkout into the worktree's `downloaded_examples/` (ignored, not committed) to run them. They ran and passed, none skipped.

**Total deviations:** 1 auto-fixed (test input), 1 environmental. **Impact:** none on production code.

## Combined gate for 10-29 and 10-30

`QT_QPA_PLATFORM=offscreen python -m pytest -m "not wurth" -q -rs` in the worktree (interpreter of the main checkout): **2914 passed, 29 skipped, 3 deselected, 0 failed** in 11 min 11 s, exit 0.

The "exactly 4 skipped" criterion cannot be met in this worktree: 25 further skips are environmental, because `Custom/` is not checked out (9) and the licence-restricted SnapEDA/SamacSys/other vendor samples are absent from `downloaded_examples/` (16). The four workstation skips are present with the expected reasons: `symlinks not permitted here: [WinError 1314]` (2), `set KICAD_IMPORT_UAT_DIR to build the manual UAT scratch install`, `set KICAD_ATOMIC_UAT_DIR to build the atomic-check UAT scratch repo`. No ATXK-H14 skip appeared. The orchestrator should re-run the gate on the main checkout after merge to confirm the passed count (about 2982 expected there, Wurth corpus included) and "4 skipped". `git -C Custom status` and `git -C WurthElektronik/KiCad-Library status` are meaningless here (the submodules are not checked out, git falls back to the worktree repo), so the unchanged-submodule check was not performed; no test touched either tree.

## Issues Encountered

- `sed -i` on the CRLF test files stripped the carriage returns; CRLF was restored with a script before the commit, and the diff shows only the intended lines.

## Known Stubs

None.

## For the UAT re-run

Check 8 of 10-VERIFICATION.md now expects: the strip lists, in this order, "Pick or type a library name", "Enter the Manufacturer", "The Datasheet must be a link or a file path", "Type a Description" and a reason starting "3D model:"; clicking the 3D model reason moves focus to Add 3D model... **Owner, please confirm on the re-run that all five reasons are visible in the strip or its tooltip.** The strip is capped at three lines (import_dialog.py line 711).

## Self-Check: PASSED

- Files modified exist; commits ca0666e, 5e9550a, 10adba3, 148bf9d are on HEAD.
- Acceptance greps: `return refuse(_err("install.invalid_library"` = 0; `_err("install.invalid_library", verdict.reason)` = 1; `name_refusal` = 3; library reason precedes `if status.build_failed:` in `blocking_reasons`; check 8 pattern matches 2; `git diff --numstat` shows 2/2 on 10-VERIFICATION.md and 2/2 on tests/README.md.
- test_atomic_targets.py 24 passed, test_import_form.py 31 passed, the three-file run 181 passed (none skipped).
