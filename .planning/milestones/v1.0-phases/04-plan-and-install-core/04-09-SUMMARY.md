---
phase: 04-plan-and-install-core
plan: 09
subsystem: importer
tags: [kicad, conflicts, idempotence, resolutions, planner, pytest]

requires:
  - phase: 04-plan-and-install-core
    provides: "04-01 plan contract (Conflict, Resolution, FileOp.listed_path); 04-04 symbol_replace_edit / symbol_insert_before_edit / block_text; 04-07 apply_plan freshness, backup and rollback; 04-08 unit rendering and extends units"
provides:
  - "D-07 identical rule in build_plan: symbol blocks compared after EOL normalisation, footprints by bytes, models by SHA-256 with the same spelling; identical items get no op"
  - "Second build after apply yields no ops and no conflicts (INST-09 at plan level)"
  - "Per-item Conflicts with stable keys symbol:<lib>:<name>, footprint:<lib>:<name casefolded>, model:<file casefolded>, a suggested free name and a resolution read from options.resolutions"
  - "planner.suggest_free_name(base, taken, *, suffix='', casefold) (D-06)"
  - "Resolutions: overwrite (symbol in place, files with base_sha256 and listed_path), rename (validated, flows into links), skip (existing item is used)"
  - "Issue codes install.bad_rename, install.bad_resolution, install.model_not_attached, install.symbol_kept, install.target_unreadable"
affects: [04-10, 05-preview-and-install-ui]

actuals:
  tokens: 15300
  tasks: 2
  commits: 4
plan_head_before: 0fd53ed4717401aeffde2a06c4672f6bc9ac4685
plan_head_after: 422520160071194539f48687f24d8697335052d9

tech-stack:
  added: []
  patterns:
    - "One generic _decide_file(spec, key, resolution) settles footprints and models (new / identical / conflict / overwrite / rename / skip); kind-specific parts are closures in a _FileSpec"
    - "Decisions run in dependency order: model, footprints, then symbols, so every item is compared with the content it would really carry (Footprint field and model link after earlier resolutions)"
    - "Symbols are judged in a loop that repeats only while a rename resolution still has to be applied (at most len(unit)+1 passes), rendering is memoised"
    - "Unresolved items are left out of the ops; the plan is blocked by the unresolved Conflict"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/planner.py
    - tests/test_install_plan.py

key-decisions:
  - "Symbol conflicts are detected against the block rendered with the footprint names that survive earlier resolutions, so repeating a rename choice finds the earlier result identical instead of asking again"
  - "A kept (skipped) first footprint drops the incoming model entirely (INFO install.model_not_attached) and its model conflict, so the user is never asked about a file that would not be linked"
  - "When the chosen symbol is skipped, plan.linked_footprint is None: the install links nothing and verify_install does not compare an untouched Footprint field"
  - "A renamed model keeps a 3D model extension: the original suffix is added when the caller's name has none"
  - "An unknown resolution action is ERROR install.bad_resolution and leaves the conflict unresolved"
  - "Overwrite records listed_path only when the on-disk spelling differs from the planned file name"

patterns-established:
  - "Tests that apply a plan build and apply inside one _open() so the package stays open (_install helper)"
  - "Case-sensitive comparisons of Windows paths in tests use .name, never Path equality"

requirements-completed: []

coverage:
  - id: D1
    description: "An existing symbol, footprint or model equal to the planned output is not a conflict and gets no op; building again after apply gives no ops and no conflicts (also for a normalised 20241209 target with the real kicad-cli and after an EOL change of the library)"
    requirement: INST-09
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_noop_second_plan_after_apply / test_noop_symbol_identical_is_not_spliced / test_noop_eol_difference_is_identical / test_conflict_footprint_identical_is_not_written / test_model_same_sha_reused"
        status: pass
      - kind: integration
        ref: "tests/test_install_plan.py#test_noop_second_plan_after_normalised_apply"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every other clash is a Conflict with a stable key, resolution None and a suggested free name; files compare ignoring case, a case-only twin symbol only warns, and the plan stays blocked until each key has a resolution"
    requirement: INST-04
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_conflict_symbol_different / test_conflict_symbol_case_twin_warns / test_conflict_footprint_bytes_differ / test_conflict_footprint_case_twin / test_model_different_sha_conflict / test_model_case_twin_conflict / test_conflict_keys_stable / test_conflict_suggested_names / test_conflict_suggest_free_name_rules / test_conflict_unresolved_blocks"
        status: pass
    human_judgment: false
  - id: D3
    description: "Overwrite replaces the old symbol block in place and records the on-disk spelling of a file as listed_path; on NTFS a case-twin model is replaced by one entry"
    requirement: INST-04
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_resolution_overwrite_symbol_in_place / test_resolution_overwrite_footprint / test_resolution_overwrite_model_case_twin / test_resolution_parent_before_child"
        status: pass
      - kind: integration
        ref: "tests/test_install_plan.py#test_resolution_overwrite_model_case_twin_applies_on_ntfs"
        status: pass
    human_judgment: false
  - id: D4
    description: "Rename uses the caller's name or the suggestion, re-sanitised and re-checked; a renamed footprint flows into the Footprint field and ki_fp_filters, a renamed model into the model link, a renamed parent into the child's extends; an unusable or clashing name is ERROR install.bad_rename; a rename onto identical content is accepted so repeating the choice is a no-op"
    requirement: INST-04
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_resolution_rename_symbol / test_resolution_rename_symbol_follows_extends / test_resolution_rename_footprint_flows / test_resolution_rename_footprint_uses_the_suggestion / test_resolution_rename_model_flows / test_resolution_rename_invalid (9 cases) / test_resolution_rename_target_identical"
        status: pass
    human_judgment: false
  - id: D5
    description: "Skip keeps the existing item and uses it: a skipped footprint is linked under its existing spelling and the incoming model is not copied; a skipped model is linked under its existing spelling; a skipped symbol is left byte-identical with WARNING install.symbol_kept; the pin/pad check runs against the footprint actually linked"
    requirement: INST-04
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_resolution_skip_footprint / test_resolution_skip_model / test_resolution_skip_symbol / test_resolution_skip_parent_symbol_keeps_the_child_linked"
        status: pass
    human_judgment: false
  - id: D6
    description: "There is no default resolution and no overwrite-all: a mapping that resolves one key leaves every other conflict unresolved and the plan blocked; an unknown key changes nothing; an unknown action is refused"
    requirement: INST-04
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_resolution_no_global_default / test_resolution_unknown_action_is_refused"
        status: pass
    human_judgment: false
  - id: D7
    description: "A part the owner edited in KiCad after the first import shows as a conflict on re-import (accepted consequence of D-07), and a skipped chosen symbol makes plan.linked_footprint None"
    verification: []
    human_judgment: true
    rationale: "Product behaviour the owner should confirm in the Phase 5 preview; both follow from the plan text but are not asserted as a desired UX by any test"

duration: 19min
completed: 2026-10-20
status: complete
---

# Phase 4 Plan 09: Conflicts, identical items and resolutions Summary

**`build_plan` now treats an existing symbol, footprint or model that equals the planned output as nothing to do (so a second import plans nothing), turns every real clash into a blocking per-item Conflict with a stable key and a suggested free name, and carries out only explicit overwrite, rename or skip resolutions, each keeping names and links consistent.**

## Performance

- **Duration:** about 19 min (2026-10-20T08:18Z to 08:37Z)
- **Tasks:** 2 (both TDD, RED then GREEN)
- **Files modified:** 2 (`planner.py` +447/-92, `test_install_plan.py` +541/-1)

## Accomplishments

- Identical rule (D-07): `_decide_file` hashes the existing file and compares it with the planned output (footprint bytes, model SHA-256, same spelling); symbol blocks are compared after `normalize_eol(..., "\n")`. Identical items drop out of the ops, the symbol is dropped from the splice, and with every unit symbol identical there is no `symbol_lib` op. The UL sample re-planned after apply gives `ops == ()`, `conflicts == ()`, `is_noop`; the same holds into a 20241209 target with real kicad-cli and after the library's line endings change.
- Conflict model (D-05, D-06, D-10): keys `symbol:<lib>:<name>`, `footprint:<lib>:<name casefolded>`, `model:<file casefolded>` are built from the default names only. Files match ignoring case; a case-twin with equal bytes is still a conflict; a case-only twin symbol adds WARNING `naming.case_clash`. `suggest_free_name` returns the first free `<name>_2`, `_3`, ... (exact for symbols, casefold for files, base cut before the number at the length limit).
- Resolutions (D-06, D-08, D-09): overwrite splices the new symbol block over the old span via `symbol_replace_edit` and gives files `base_sha256` plus `listed_path` when the on-disk spelling differs; rename re-sanitises the name, re-checks it (ERROR `install.bad_rename` on a placeholder or clash, accepted as identical when the content already matches) and flows into the Footprint field, `ki_fp_filters`, the model link and `extends`; skip links the existing footprint or model, never copies a model the kept footprint does not link (INFO `install.model_not_attached`) and leaves a kept symbol untouched (WARNING `install.symbol_kept`).
- Ordering: a new parent goes in front of an existing descendant with `symbol_insert_before_edit`; a new child still appends after its parent.
- Real `Custom/` untouched: all installs target `tmp_path`; `git status --porcelain Custom` prints nothing.

## Task Commits

1. **Task 1 RED:** `a104512` (test) - 19 selected, 12 failing on the planned behavior
2. **Task 1 GREEN:** `7a04172` (feat) - identical rule, keyed conflicts, suggestions; resolutions read but refused as unsupported
3. **Task 2 RED:** `fe26559` (test) - 27 selected, 25 failing (blocked by `install.resolution_unsupported`)
4. **Task 2 GREEN:** `4225201` (feat) - overwrite, rename and skip

**Plan metadata:** the docs commit carrying this SUMMARY and the STATE/ROADMAP updates.

## TDD Gate Compliance

- **Task 1 RED:** 12 of 19 selected tests failed on assertions about the planned behavior (`ops == ()` after apply, a Conflict where none belongs, `suggested_name ''` vs `PART_2`, the missing `suggest_free_name`, a case-twin symbol without WARNING). The 7 that passed (three 04-01/04-08 conflict tests, `test_conflict_symbol_different`, `test_conflict_footprint_bytes_differ`, `test_conflict_keys_stable`, `test_conflict_unresolved_blocks`) pin conflict behavior the tracer already had. The first draft of two tests applied a plan after its package closed (`install.source_gone`); fixed with the `_install` helper before the RED commit. Semantic assessment: valid RED. The `tdd-red-evidence` classifier does not read pytest console output and was not run.
- **Task 1 GREEN:** 19 selected tests pass (none skipped, so the real-CLI no-op test ran); plan, apply, e2e, verify and layering files 209 passed.
- **Task 2 RED:** 25 of 27 failed on `install.resolution_unsupported` blocking the plan (or `bad_rename` expected where it reported unsupported). The 2 that passed (`test_resolution_no_global_default`, `test_resolution_unknown_action_is_refused`) pin the no-default rule that Task 1 already delivered. Semantic assessment: valid RED.
- **Task 2 GREEN:** 27 resolution tests passed on the first run; the same five-file group 236 passed; full suite 1298 passed, 4 skipped (baseline 1255 plus 43 new). A mutation check (dropping the overwrite splice, the identical rule, skip's `kept` flag and the parent-before-child anchor) made 2, 5, 2 and 1 tests fail respectively.
- **REFACTOR:** none.

## Files Created/Modified

- `kicad_lib_manager/importer/planner.py` - `suggest_free_name`, `_FileSpec` / `_Decision` / `_decide_file` / `_rename_file` / `_find_hit`, `_digest`, `_footprint_files`, `_SymState`; `build_plan` tail restructured into render closures (`render_symbols`, `render_fp`), the model, footprint and symbol decisions, and ops assembly
- `tests/test_install_plan.py` - 43 new tests (`test_noop_*`, `test_conflict_*`, `test_model_same_sha_reused`, `test_model_different_sha_conflict`, `test_model_case_twin_conflict`, `test_resolution_*`); helpers `_clashing_layout`, `_put_footprint`, `_put_model`, `_install`, `_res`, `_with`

## Decisions Made

See `key-decisions`. In short: decisions run model, then footprints, then symbols, so the symbol is compared with the Footprint field it would really get; a skipped first footprint drops the model; a skipped chosen symbol sets `linked_footprint` to None; a renamed model keeps a 3D model extension.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Unknown resolution action**
- **Found during:** Task 1 design
- **Issue:** `Resolution.action` is a free string; a typo such as "replace" would have fallen through to the rename branch and renamed an item the caller never asked to rename.
- **Fix:** ERROR `install.bad_resolution`; the conflict stays unresolved, so the plan is blocked (`test_resolution_unknown_action_is_refused`).
- **Files modified:** kicad_lib_manager/importer/planner.py, tests/test_install_plan.py
- **Commit:** 7a04172, 4225201

**2. [Rule 2 - Missing critical] Unreadable existing file**
- **Found during:** Task 1 (`_decide_file`)
- **Issue:** Hashing an existing footprint or model can fail; treating that as "different" would offer overwrite of a file the planner never saw.
- **Fix:** ERROR `install.target_unreadable` naming the file, no conflict, no op.
- **Commit:** 7a04172

**3. [Rule 1 - Bug] Plan wording: `verify_install` cannot accept a kept chosen symbol**
- **Found during:** Task 2 design
- **Issue:** The plan says a skipped symbol writes no change while the footprint and model still install. `verify_install` compares the chosen symbol's Footprint field with `<Lib>:<linked_footprint>`, which an untouched existing symbol rarely matches, so apply would roll the install back.
- **Fix:** `plan.linked_footprint` is None when the chosen symbol is skipped (the field already allows None), which makes verify skip the link, model and pin/pad checks. No edit to `verify.py` or `plan.py`.
- **Files modified:** kicad_lib_manager/importer/planner.py
- **Commit:** 4225201

**4. [Rule 3 - Blocking] Dropped model conflict when the first footprint is kept**
- **Found during:** Task 2 design
- **Issue:** The plan says a skipped footprint does not copy the incoming model. Keeping that model's own conflict would force the user to resolve a file that is never installed.
- **Fix:** The model decision (op, conflict, notes) is discarded and INFO `install.model_not_attached` is added; the footprint is still judged with the model link first, because its conflict can only be decided on the bytes it would carry.
- **Commit:** 4225201

**5. [Plan wording] "At most two render passes"**
- The plan asks for detection on default names, then one render with final names. Comparing against the final Footprint field is what makes a repeated rename choice a no-op, so symbols are judged after footprints and models, and the symbol loop repeats only while a rename resolution still has to be applied (at most `len(unit)+1` passes, memoised). In the common case it is still two renders.

**Total deviations:** 4 auto-fixed (2 Rule 2, 1 Rule 1, 1 Rule 3) plus 1 wording note. **Impact:** none on the contract; each keeps a resolution from silently doing the wrong thing.

## Known Stubs

None.

## Threat Flags

None. T-04-24 (silent overwrite): every non-identical clash is a Conflict with `resolution None`, `plan.blocked` until each key has a Resolution, and no default exists (`test_conflict_unresolved_blocks`, `test_resolution_no_global_default`, mutation check on the identical and overwrite paths). T-04-25 (caller `rename_to`): re-sanitised (`../x` becomes `x`), placeholder and clash give ERROR `install.bad_rename` (`test_resolution_rename_invalid`, 9 cases across symbol, footprint and model); the applier's containment check stays as the second layer. T-04-26 (case twins): files compare casefold, overwrite records `listed_path`, and the NTFS replace leaves one entry (`test_resolution_overwrite_model_case_twin_applies_on_ntfs`).

## Issues Encountered

- The Bash tool rejects heredocs with unbalanced quotes; patch scripts and test blocks were written with the Write tool into the scratchpad and spliced in by a Python script.
- Python path equality ignores case on Windows, so tests that distinguish `fp.kicad_mod` from `FP.kicad_mod` compare `.name` strings.
- Requirements INST-04 and INST-09 are not marked complete: plan 04-10 also declares them and has no SUMMARY yet.

## Next Phase Readiness

- 04-10 can add the end-to-end INST-09 test (import twice through `apply_plan`) on top of the plan-level no-op proven here.
- Phase 5 can show `plan.conflicts` (key, kind, name, existing text, suggested name, resolution) and rebuild the plan with `InstallOptions.resolutions` on every choice; keys do not change when other options change.
- Open: the case-sensitive-filesystem outcome of an overwrite onto a case twin (a second entry instead of a replace) has no real-volume test, as in 04-07; whether the owner wants a re-import of a KiCad-edited part to show as a conflict is the accepted D-07 consequence.

## Self-Check: PASSED

`kicad_lib_manager/importer/planner.py` and `tests/test_install_plan.py` exist; commits `a104512`, `7a04172`, `fe26559`, `4225201` are ancestors of HEAD and `git rev-list --count` from `plan_head_before` is 4. Acceptance greps: `def suggest_free_name(`, `options.resolutions`, `case_clash(`, `normalize_eol(`, `symbol_replace_edit(`, `symbol_insert_before_edit(`, `"install.bad_rename"`, `"install.model_not_attached"`, `"install.symbol_kept"`, `listed_path=` all present in planner.py. `-k "noop or conflict"` 18 passed; `-k model` 17 passed; `-k resolution` 27 passed; the five-file group 236 passed; full suite 1298 passed, 4 skipped; `git status --porcelain Custom` prints nothing.

---
*Phase: 04-plan-and-install-core*
*Completed: 2026-10-20*
