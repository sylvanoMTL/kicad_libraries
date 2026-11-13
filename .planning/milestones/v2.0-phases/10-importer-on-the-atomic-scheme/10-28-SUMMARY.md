---
phase: 10-importer-on-the-atomic-scheme
plan: 28
subsystem: importer
tags: [fp-lib-table, post-install, WR-05, gap-closure, disposition]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: plans 10-11 (post-install table rule), 10-25, 10-26 (CR-01 fix), 10-27 (WR-02 fix)
provides:
  - "_finish_post_install offers the repo footprint library to fp-lib-table after every new-library install, idempotently (WR-05)"
  - "10-REVIEW-DISPOSITION.md records CR-01, WR-02 and WR-05 as fixed with their closing plans and commits"
  - "Check 6 of 10-VERIFICATION.md expects both table files"
affects: [10-VERIFICATION re-run, end-of-phase human checklist]

actuals:
  tokens: 14000
  tasks: 3
  commits: 4  # measured before the SUMMARY commit (git rev-list --count 05f21a4..2455181); the SUMMARY commit makes 5
plan_head_before: 05f21a4c53cd1e807af0e23d723f6c329ef00863
plan_head_after: 2455181  # last task commit; the SUMMARY commit follows it

tech-stack:
  added: []
  patterns: ["offer-and-let-add_library_entries-decide: the caller passes the repo footprint pair, the add-only helper skips a listed nickname"]

key-files:
  created: []
  modified:
    - kicad_lib_manager/main_window.py
    - tests/test_main_window_import.py
    - .planning/phases/10-importer-on-the-atomic-scheme/10-REVIEW-DISPOSITION.md
    - .planning/phases/10-importer-on-the-atomic-scheme/10-VERIFICATION.md

key-decisions:
  - "The footprint pair goes to add_library_entries whenever the footprint library is a repo folder; add_library_entries returns 'listed' before any backup or write for a table that already lists it"
  - "Library tables row keeps KiCad's file names (sym-lib-table / fp-lib-table), owner decision 2026-10-28; no new wording"

requirements-completed: [LIB-06]

coverage:
  - id: D1
    description: "A new symbol library linking an existing but unlisted Atomic_Footprints adds exactly one managed fp-lib-table entry, every other byte kept, with the combined 'Added ... and ... to fp-lib-table' log and success row"
    requirement: LIB-06
    verification:
      - kind: integration
        ref: "tests/test_main_window_import.py#test_tables_new_symbol_library_adds_the_existing_unlisted_footprint_library"
        status: pass
      - kind: integration
        ref: "tests/test_main_window_import.py#test_status_rows_new_symbol_library_adds_an_unlisted_footprint_library"
        status: pass
    human_judgment: false
  - id: D2
    description: "An already-listed Atomic_Footprints leaves fp-lib-table byte-identical with no backup, and the row reads 'Added <lib> to sym-lib-table; fp-lib-table already lists Atomic_Footprints; not changed' (info)"
    requirement: LIB-06
    verification:
      - kind: integration
        ref: "tests/test_main_window_import.py#test_tables_new_symbol_library_leaves_a_listed_footprint_library_alone"
        status: pass
      - kind: integration
        ref: "tests/test_main_window_import.py#test_status_rows_new_symbol_library_with_a_listed_footprint_library"
        status: pass
    human_judgment: false
  - id: D3
    description: "Official-link and outside-repo footprint libraries still get no fp-lib-table entry; existing-library install still gets only the hint"
    requirement: LIB-06
    verification:
      - kind: integration
        ref: "tests/test_main_window_import.py#test_tables_a_footprint_library_outside_the_repo_gets_no_fp_entry"
        status: pass
      - kind: integration
        ref: "tests/test_main_window_import.py#test_tables_an_official_link_into_a_new_symbol_library_adds_only_the_symbol_entry"
        status: pass
    human_judgment: false
  - id: D4
    description: "Disposition record (CR-01, WR-02, WR-05 fixed; six rows left open) and check 6's new expected text in 10-VERIFICATION.md"
    verification: []
    human_judgment: true
    rationale: "Planning-record edits; checked by the Task 3 verify script and git diff --numstat, and the owner runs check 6 by hand at end of phase"

duration: 75min
completed: 2026-10-28
status: complete
---

# Phase 10 Plan 28: WR-05 shared footprint library offered to fp-lib-table Summary

**After an install that creates a new symbol library, a repo-folder Atomic_Footprints missing from fp-lib-table now gets its entry, a listed one is left byte-identical, and CR-01, WR-02 and WR-05 are recorded as fixed.**

## Performance

- **Duration:** about 75 min, most of it the 12-minute full suite
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- `_finish_post_install` passes `footprint=(pending.footprint_library, pending.fp_rel_path)` whenever both are set (they are set only for a repo folder, so official KiCad links and outside-repo libraries still stay out, D-16). Symbol pair unchanged (new symbol library only). A 3-line comment above the call names WR-05. The docstring, `_PostInstall`, `_on_import_installed`, `_tables_outcome` and `table_generator.py` are untouched.
- Four new tests pin the behaviour end to end: bytes of both tables, no fp-lib-table backup when listed, log text, and the Library tables status row (success when added, info when already listed, no generate hint). `run_install` takes `**plan_options`.
- Disposition record and check 6 text updated after the combined suite passed.

## Task Commits

1. **Task 1 (tracer, TDD):** RED `004f813` (test), GREEN `01cd7da` (feat) - **`01cd7da` is the commit that changed main_window.py (WR-05)**
2. **Task 2:** `ef50eb3` (test) - listed-footprint and status-row tests
3. **Task 3:** `2455181` (docs) - disposition and check 6

**Plan metadata:** the SUMMARY commit that follows this file.

## TDD notes

- **RED:** `test_tables_new_symbol_library_adds_the_existing_unlisted_footprint_library` failed on `assert fp-lib-table bytes == old_fp[:-2] + <Atomic_Footprints entry> + ")\n"` (fp-lib-table unchanged), the planned assertion, not an import or fixture fault. Semantic assessment: target ran, failed for the intended reason. The pytest report is not among the formats `gsd check tdd-red-evidence` supports, so the classifier was not run.
- **Mutation check (Task 2):** with main_window.py restored to the pre-GREEN version (`004f813`), all four new tests fail and the other 40 of tests/test_main_window_import.py pass; the GREEN file was then restored.

## Test totals (measured in this worktree)

- Task 1/2 command `pytest tests/test_main_window_import.py tests/test_table_add_entries.py -q`: 58 passed (44 + 14).
- Verifier's targeted command (14 files, `-m "not wurth"`): 417 passed, 4 skipped, 0 failed.
- Wave gate `pytest -m "not wurth" -q -rs`: **2893 passed, 31 skipped, 3 deselected, 0 failed** (718 s).
- The 31 skips are the 4 expected ones of tests/README.md (KICAD_ATOMIC_UAT_DIR, KICAD_IMPORT_UAT_DIR, two symlink skips) plus 27 worktree-only skips: 9 "Custom submodule not checked out" and 18 "downloaded_examples/... not present (licence-restricted sample)". The orchestrator's main-checkout measurement (2956 passed, 4 skipped before this plan) is the authoritative gate and is re-run after merge. This plan adds 4 tests.
- Not measurable here: `git -C Custom status --porcelain` and `git -C WurthElektronik/KiCad-Library status --porcelain` cannot measure the real submodules because they are not checked out in this worktree (`Custom/` is an empty directory). `git status --porcelain` of the worktree itself was empty before and after the run. No submodule was touched.

## Fix commits cited in 10-REVIEW-DISPOSITION.md

- CR-01: `1276906` (planner.py, plan 10-26)
- WR-02: `f35486b` (keywords.py, plan 10-27)
- WR-05: `01cd7da` (main_window.py, this plan)

The WR-02 Source cell ends `; spi/uart/ble left as is, all-caps CAN accepted by owner 2026-10-28, see 10-27`. Two residuals: spi/uart/ble stay on the any-case match by plan 10-27's judgement (not an owner decision), and all-caps prose such as "YOU CAN USE IT" still gives CAN, accepted by the owner on 2026-10-28 and pinned by `test_all_caps_can_gives_the_can_keyword`. WR-01, WR-03, WR-04, IN-01, IN-02 and IN-03 stay `open` with Source `-` (owner decision: out of scope). Frontmatter reads `open: 6`, `total: 9`.

## Human check changes

For the end-of-phase checklist (10-VERIFICATION.md check 6, from plan 10-25 Task 2):

**Check 6 expected:** the result banner reads '✓ Installed CSD85301Q2 into Atomic_Transistor_FET'. The Library tables row reads 'Added Atomic_Transistor_FET to sym-lib-table and Atomic_Footprints to fp-lib-table' (the scratch repo has Atomic_Footprints.pretty but the scratch tables folder of S2 is empty, so its entry is added, WR-05). The tables folder of S2 now holds sym-lib-table and fp-lib-table.

Checks 1-5 and 7-11 are unchanged by plans 10-26, 10-27 and 10-28. 10-VERIFICATION.md was updated as in plan step 5: two scoped edits (the `human_verification` frontmatter item and item 6 of the Checks body); `git diff --numstat 33347c9` reports exactly 2 added and 2 deleted lines.

## Owner decision 2026-10-28

The Library tables row keeps KiCad's own file names. When Atomic_Footprints is already listed, the row after a new symbol library reads "Added <library> to sym-lib-table; fp-lib-table already lists Atomic_Footprints; not changed". It uses the existing add_library_entries wording, so no new text was added.

## Deviations from Plan

None - plan executed exactly as written. Task 2's tests passed immediately because Task 1's change already implemented the rule; the plan anticipated this ("pin the rule of Task 1"), and the mutation check above shows they are not vacuous.

## Issues Encountered

- Source files are CRLF, so edits were made with byte-exact Python replacements to keep line endings.
- Two tool calls were refused by the worktree guard (compound git commands) and re-run as plain commands. A stray backup copy briefly created at `.claude/worktrees/mw_backup_10_28.py` (outside the worktree, in the main checkout's git-ignored `.claude/`) was deleted at once.

## Known Stubs

None.

## Threat Flags

None. The new write path is the existing add-only `add_library_entries`; T-10-47 to T-10-51 are mitigated by the byte-exact and no-backup tests and the verify script.

## Next Phase Readiness

Ready for the end-of-phase verifier re-run and the owner's human checks with the updated check 6. The mirror case (new Atomic_Footprints with an existing unlisted symbol library gets no symbol hint) is unchanged and flagged in the plan for a later decision.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-28*
