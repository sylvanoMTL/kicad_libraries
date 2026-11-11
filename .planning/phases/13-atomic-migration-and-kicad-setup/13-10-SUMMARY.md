---
phase: 13-atomic-migration-and-kicad-setup
plan: 10
subsystem: importer
tags: [migration, footprints, atomic-footprints, 3d-models, tdd]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "plan 13-06's migration architecture and footprints.py entry signature (FootprintsOutcome, plan_footprints(inventory, choices, ctx, *, mpns))"
provides:
  - "The complete footprint side of the Atomic_ migration: shared moves, model renames, multi-model footprints, official-footprint switching, leftover rows (board features included), Atomic_Footprints name clashes, generated footprint text and owner-added 3D models"
affects: ["13-11 (families.py, reads footprints.py's shape for derived-symbol edits)", "13-12 (gate.py, orders/targets the issue codes this plan adds)", "13-13 (applier.py, applies this plan's new op shapes)", "13-14 (migration_dialog.py, renders leftovers/conflicts/texts this plan now fills)", "13-15 (window file-list rendering of model renames and leftovers)"]

actuals:
  tokens: 14300
  tasks: 3
  commits: 5
  plan_head_before: f4d420948be3dc49328bf83823b58f3e7dbd8018
  plan_head_after: cadfbc8fcf4bae559dc328307b266ff09828c855

tech-stack:
  added: []
  patterns:
    - "A footprint move is planned in three stages per run: official-choice resolution (per part, no op), the shared-footprint move (per footprint, name+model+text edits bundled into one apply_edits call), then a leftover pass that reuses the same name-clash resolver for a kept vendor file"
    - "Model renames are decided once per *old* file name across a dict keyed by that name, by the globally smallest linking PartKey, so a model shared by two different footprints (not just two parts of one footprint) is renamed exactly once and every linker is retargeted to the same new name"
    - "Atomic_Footprints.pretty name clashes are resolved against one mutable (known bytes, taken stems) pair threaded through every footprint this run touches, seeded from the on-disk listing, so a within-run clash between two v1 footprints is caught the same way a clash against an existing file is"

key-files:
  created:
    - tests/test_migration_footprints.py
  modified:
    - kicad_lib_manager/importer/migration/footprints.py

key-decisions:
  - "The vendor source file of a footprint being moved always gets a direct 'delete' op from the move pathway itself, whether or not a 'write' happens (identical-content reuse, clash skip, or a plain move) — never routed through a LeftoverRow. Every op-list assertion across this plan, Task 1/2, and the unedited 13-06 e2e test already expects a direct delete; threading the same vendor file through a LeftoverRow as well would double it (an early draft did exactly that and produced a duplicate-delete FileNotFoundError at apply time, caught by the merge-library e2e test)."
  - "A model's own default_keep/keep decision is always independent of its referencing footprint's fate, including when that footprint is a *kept* leftover move: D-10's default_keep rule reads only the model's original linkage, never 'does the footprint that links me still exist afterward'. A kept-but-moved leftover footprint's model therefore still defaults to delete unless the owner separately ticks it, matching the literal rule over a more 'convenient' auto-carry-over."
  - "The identical-footprint-reuse test runs plan_footprints twice (writing the first run's own output to disk as the second run's 'existing' Atomic_Footprints file) rather than hand-authoring two separately-built-but-token-identical vendor footprints. D-11 regenerates the footprint description on every run, and a footprint's 'code' input to footprint_facts is always its own file name (never blank), so describe() can never output the same text as a bare, text-less vendor copy — a genuine idempotent-rerun scenario is the only honest way to exercise this path."
  - "Footprint-text generation's 'maker' input uses importer.keywords.manufacturer_words(raw Manufacturer field text) directly, never importer.manufacturers.canonical() — canonicalising the Manufacturer field for display is symbols.py's job on the symbol side; manufacturers.py is also outside footprints.py's registered import set in tests/test_importer_layering.py."

patterns-established:
  - "A per-run clash resolver (_resolve_clash) takes its mutable state (known bytes by filename, taken stems) as explicit parameters rather than a class, so the exact same resolver instance threads through both the main shared-move loop and the leftover-move loop without either needing to know about the other's bookkeeping."

requirements-completed: [MIG-02, MIG-03]

coverage:
  - id: D1
    description: "Every footprint a part links moves into Atomic_Footprints once, however many parts link it; its single 3D model is renamed to the first linking part's MPN with the path rewritten, and a case-only match keeps the on-disk spelling"
    requirement: MIG-02
    verification:
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_shared_footprint_moves_once_and_model_takes_mpn"
        status: pass
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_model_linked_by_two_footprints_keeps_first_mpn"
        status: pass
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_case_only_model_rename_keeps_disk_spelling"
        status: pass
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_blank_mpn_keeps_model_name"
        status: pass
    human_judgment: false
  - id: D2
    description: "A footprint with two or more 3D model blocks keeps every file under its own name; nothing is deduplicated, renamed or deleted"
    requirement: MIG-03
    verification:
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_multi_model_footprint_keeps_every_file"
        status: pass
    human_judgment: false
  - id: D3
    description: "A part can switch to an official KiCad footprint instead of moving into Atomic_Footprints: the link resolves, no file under KiCad's own folders is ever touched, a pin/pad mismatch is an amber warning never a blocker, and a missing official link blocks with an ERROR"
    requirement: MIG-03
    verification:
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_official_switch_links_kicad_footprint"
        status: pass
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_official_pad_mismatch_is_amber"
        status: pass
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_official_link_must_exist"
        status: pass
    human_judgment: false
  - id: D4
    description: "Footprints and models the migration leaves unlinked are leftover rows defaulting to delete, except a footprint already unlinked before the migration (a board feature), which defaults to keep and moves into Atomic_Footprints when it sits in a v1 .pretty; the owner's choice flips either default"
    requirement: MIG-03
    verification:
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_board_feature_defaults_to_keep"
        status: pass
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_kept_leftover_footprint_moves"
        status: pass
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_emptied_pretty_folder_removed"
        status: pass
    human_judgment: false
  - id: D5
    description: "A name clash in Atomic_Footprints reuses identical content with no write, and asks Overwrite/Rename/Skip for different content, blocking Run until answered"
    requirement: MIG-03
    verification:
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_identical_footprint_is_reused"
        status: pass
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_different_footprint_clash_asks"
        status: pass
    human_judgment: false
  - id: D6
    description: "A moved footprint's description is always regenerated and its tags merged, with the old description recorded as a footprint-scope field change and a typed override written exactly; an owner-added 3D model is copied in and linked, with an unusable source blocking as an ERROR"
    requirement: MIG-02
    verification:
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_footprint_text_generated_and_merged"
        status: pass
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_added_model_is_linked"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 10: Footprint side of the Atomic_ migration — moves, clashes, official switch, leftovers, text and added models Summary

**`footprints.py`'s `plan_footprints` now plans every footprint and 3D-model case of a v1 Custom/: shared moves with MPN-based model renames, multi-model footprints kept intact, per-part switches to an official KiCad footprint, board-feature-aware leftover rows, Atomic_Footprints name-clash resolution (reuse/overwrite/rename/skip), regenerated footprint descriptions and tags, and owner-added 3D models — fourteen behaviour tests plus the untouched 13-06 end-to-end tracer, all passing.**

## Performance

- **Duration:** ~70 min
- **Completed:** 2026-11-11
- **Tasks:** 3 completed
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- Shared footprints move once into `Atomic_Footprints.pretty` however many parts link them, in key order of their first linker; a footprint's single 3D model is renamed to that linker's MPN with the path rewritten, a case-only match keeps the on-disk spelling, and a model shared by *two different footprints* is renamed exactly once, by the globally smallest linking part key, with every footprint retargeted to the same new name
- A footprint with two or more model blocks keeps every file under its own name — nothing deduplicated, renamed or deleted — with each path only rewritten to its own file name (D-23)
- A part can switch to "Use an official KiCad footprint": the link is validated against `footprint_index.build_index`, a pin/pad mismatch is a non-blocking amber `migration.pad_mismatch` warning, a missing link is `migration.official_missing`, and no operation is ever planned under KiCad's own footprint or 3D-model folders
- Every footprint and model the plan leaves unlinked becomes a `LeftoverRow`: `default_keep` is `True` only when the file was already unlinked before the migration (a board feature); the owner's `choices.leftovers` override flips either default, a kept v1-folder footprint moves into `Atomic_Footprints.pretty` under its own name through the same clash resolver the main move pathway uses, and folder removal now tracks every footprint's delete from *both* pathways through one `deleted_rels` set
- `_resolve_clash` settles an `Atomic_Footprints.pretty` name clash by comparing `sexpr.token_stream` after this plan's own edits: identical content is reused with no write, different content raises a `Conflict` (`footprint:<name>`, suggested `<name>_<MPN>`) and blocks with `migration.conflict_unresolved` until `choices.resolutions` answers it with overwrite, rename or skip
- A moved footprint's description is always regenerated from `footprint_text.footprint_facts`/`describe`, with the old one recorded as a footprint-scope `FieldChange`; tags are merged with the vendor's own words via `keywords.merge_words`; a typed `fp_description`/`fp_tags` override is written exactly; `texts`/`package_words` are filled for every moved part (closing a gap left open since Task 1, see Deviations)
- `_open_added_model` follows `atomic_fixes._open_model`'s intake pattern (one member, size cap, sha256 re-check) for `PartChoice.model_source`: a footprint with no model of its own gets a new `3DModels/<MPN>.<ext>` write and a `(model ...)` block inserted; an unreadable, oversized or non-model source is `migration.model_unreadable`

## Task Commits

TDD gate sequence for Tasks 2 and 3 (`tdd="true"`); Task 1 (`type="tracer"`) committed as a single tracer commit first:

1. **Task 1: tracer — shared footprints move once, models take the MPN, multi-model footprints keep their files** - `b82afd7` (feat) — base move pathway, model-rename grouping, multi-model path, five behaviour tests
2. **Task 2 RED** - `3ed900c` (test) — six new tests for official-footprint switching, leftovers and board features; all six fail against the Task 1 implementation
3. **Task 2 GREEN** - `c59ac71` (feat) — official-switch stage, leftover computation, and folder-removal rewired onto a shared `deleted_rels` set; all eleven tests pass
4. **Task 3 RED** - `6c5c908` (test) — four new tests for Atomic_Footprints clashes, footprint text and added 3D models; all four fail against the Task 1/2 implementation
5. **Task 3 GREEN** - `cadfbc8` (feat) — `_resolve_clash`, footprint-text generation, `_open_added_model`; all fifteen tests pass, including a fixture fix to `test_identical_footprint_is_reused` discovered while writing this task (see Deviations)

**Plan metadata:** this SUMMARY (worktree mode excludes STATE.md/ROADMAP.md; the orchestrator updates those centrally after merge).

## Files Created/Modified

- `kicad_lib_manager/importer/migration/footprints.py` - `plan_footprints` complete: official-switch stage, shared-move pass with model-rename grouping, name-clash resolver, footprint-text generation, added-model intake, leftover pass, folder removal
- `tests/test_migration_footprints.py` - fifteen behaviour tests across the three tasks, with local fixture-writing helpers (never `tests/migrationfixtures.py`, which this plan does not edit)

## Decisions Made

- The vendor source file of a moved footprint always gets a direct `delete` op from the move pathway, never a `LeftoverRow` — see key-decisions above for the duplicate-delete bug this avoided
- A model's own keep/delete default is independent of its referencing footprint's fate, even for a kept-and-moved leftover footprint — matches the literal D-10 rule rather than auto-carrying the footprint's keep decision onto its model
- `test_identical_footprint_is_reused` runs the planner twice instead of hand-building two token-identical vendor footprints, because D-11's always-regenerated description makes a bare vendor copy never literally match another bare vendor copy
- Footprint-text generation's manufacturer input goes through `keywords.manufacturer_words` directly, never `manufacturers.canonical()` (outside this module's registered import set, and canonicalising the field is the symbol side's job)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Duplicate delete op for a renamed model's old file**
- **Found during:** Task 2 GREEN, full verify run (`test_two_libraries_merge_into_one_atomic_library` from the untouched 13-06 e2e suite)
- **Issue:** The new leftover-model loop skipped only names already in `final_model_names` (the set of *final*, post-rename model names). A renamed model's *old* name was never in that set, so it was independently treated as an orphaned leftover and given a second `delete` op — the same file already deleted once by the model-rename logic. `apply_migration` raised `FileNotFoundError` on the second delete.
- **Fix:** The leftover-model loop also skips any name that is a *key* of `model_final_name` (every old name tied to a moving footprint's single model, renamed or not), not just the value set.
- **Files modified:** `kicad_lib_manager/importer/migration/footprints.py`
- **Verification:** `pytest tests/test_migration_footprints.py tests/test_migration_e2e.py` — 19/19 pass
- **Committed in:** `c59ac71` (Task 2 GREEN commit)

**2. [Rule 1 - Bug] `test_identical_footprint_is_reused`'s own fixture was never actually identical**
- **Found during:** Task 3 GREEN, first test run
- **Issue:** The test built the "already in Atomic_Footprints" file and the v1 vendor file from the same bare `vendor_footprint("FPC", ...)` call, expecting token-identical content. Task 3's footprint-text generation (D-11) always regenerates the description from `footprint_facts`/`describe`, and `describe()`'s maker/code segment is never empty (the footprint's own file name is always part of it), so the migration's own edited output could never equal a plain, text-less vendor copy — the test was asserting a scenario the implementation correctly never produces.
- **Fix:** Rewrote the test to run `plan_footprints` once, write its own generated output to disk as the pre-existing Atomic_Footprints file, then run `plan_footprints` again and assert the second run reuses it with no write — a genuine idempotent-rerun scenario instead of a hand-assumed one.
- **Files modified:** `tests/test_migration_footprints.py`
- **Verification:** `pytest tests/test_migration_footprints.py` — 15/15 pass
- **Committed in:** `cadfbc8` (Task 3 GREEN commit)

**3. [Rule 2 - Missing Critical] `package_words`/`texts` left unfilled since Task 1**
- **Found during:** Task 3, re-reading Task 1's own action text while implementing footprint-text generation
- **Issue:** Task 1's action text ("Fill `links`, `models`, `targets`, `footprint_links`, `model_renames`, `package_words` (`[facts.family, code]` from `footprint_facts`)") already called for `package_words`, but `footprint_facts` needs a manufacturer/text-generation context that only became available with Task 3's footprint-text work; Tasks 1 and 2 shipped with `package_words={}`/`texts={}` hardcoded, matching no test but also not the plan's own fill list.
- **Fix:** Task 3's footprint-text block (which already computes `facts` for every moved footprint) also populates `package_words[key]` and `texts[key]` for every linking part, closing the gap retroactively for every footprint this module ever moves, not just the ones with changed text.
- **Files modified:** `kicad_lib_manager/importer/migration/footprints.py`
- **Verification:** Covered incidentally by `test_footprint_text_generated_and_merged`'s `outcome.texts[key]` assertions; no dedicated `package_words` test was added since no behavior test in this plan names it
- **Committed in:** `cadfbc8` (Task 3 GREEN commit)

---

**Total deviations:** 3 auto-fixed (2 Rule 1 bugs caught by the plan's own verify loop before any commit, 1 Rule 2 completeness fix). **Impact on plan:** All three were necessary for the plan's own tasks and verify commands to pass or to satisfy Task 1's own un-tested instruction; no scope creep beyond `footprints.py` and its test file.

## TDD Gate Compliance

Task 2 and Task 3 (`tdd="true"`) gate sequences, verified against `git log`:

| Task | Gate | Commit | Pattern | Status |
|------|------|--------|---------|--------|
| 2 | RED | `3ed900c` | `test(13-10): ...` | Present — six new tests failed against the Task 1 implementation (missing official-switch handling, leftovers, folder-removal-with-leftovers) |
| 2 | GREEN | `c59ac71` | `feat(13-10): ...` | Present — all eleven tests in `tests/test_migration_footprints.py` pass |
| 2 | REFACTOR | — | `refactor(13-10): ...` | Not needed — no cleanup opportunity after GREEN |
| 3 | RED | `6c5c908` | `test(13-10): ...` | Present — four new tests failed against the Task 1/2 implementation (no clash check, no text generation, no added-model path) |
| 3 | GREEN | `cadfbc8` | `feat(13-10): ...` | Present — all fifteen tests pass |
| 3 | REFACTOR | — | `refactor(13-10): ...` | Not needed — no cleanup opportunity after GREEN |

**Task 1 note:** Task 1 is `type="tracer"`, not `tdd="true"`; committed as a single `feat` commit per the tracer execution rule. Its own `<verify>` command (`pytest tests/test_migration_footprints.py tests/test_migration_e2e.py tests/test_importer_layering.py`) was re-run and passed before Task 2 began (the tracer feedback gate); this run carried only `<automated>` verification with no `<human-check>`, and auto-mode/`_auto_chain_active` were both false, so per the executor's tracer-feedback precedence chain (row 3, interactive + `end-of-phase` + automated-only) the gate re-ran `<verify>` and continued to Task 2 with no synthesized checkpoint.

**RED evidence caveat:** `gsd_run check tdd-red-evidence` was unavailable in this isolated worktree (no `.claude/gsd-core/` present, matching the same caveat recorded in 13-06-SUMMARY.md and 13-05-SUMMARY.md). Both RED commits were established by running the full test file directly and inspecting the failure output (captured in each RED commit's own message and this SUMMARY's narrative above): Task 2's six new tests failed on genuine assertion mismatches (wrong footprint link, empty leftovers, `StopIteration` from a missing op) against the Task 1 implementation's actual behavior, never a collection, import or syntax error; Task 3's four new tests failed the same way against the Task 1/2 implementation. Both satisfy the gate's semantic-assessment requirement even without the automated record pipeline.

## Issues Encountered

None beyond the two Rule 1 bugs documented above, both caught and fixed by the plan's own verify loop before any affected commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `footprints.py`'s `FootprintsOutcome` is now fully populated (`links`, `models`, `targets`, `ops`, `footprint_links`, `model_renames`, `leftovers`, `conflicts`, `texts`, `package_words`, `field_changes`, `removed_folders`, `issues`) for every case the live `Custom/` is known to hold (RESEARCH F-12): shared moves, multi-model footprints, a model shared by two footprints, official-footprint switches, board features, and owner-added models.
- 13-11 (`families.py`) can read `footprints.links`/`.targets` as `symbols.py` already does; no new cross-module contract was introduced.
- 13-12 (`gate.py`) can order and target the new issue codes this plan adds (`migration.official_missing`, `migration.pad_mismatch`, `migration.model_kept_name`, `migration.model_unreadable`, `migration.conflict_unresolved`) the same way it already handles `migration.unreadable`.
- 13-13 (`applier.py`) sees no new `MigrationOp` kinds, only more of the existing four (`mkdir`/`write`/`delete`/`rmdir`), so its rollback logic needs no changes for this plan's additions; `source_rel` is populated on every model-rename write for a future preview/diff consumer (13-15/13-16) but is not read by `applier.py` itself.
- 13-14/13-15 (migration dialog, files tab) can render `outcome.leftovers`, `outcome.conflicts` and `outcome.texts` directly; no placeholder data remains in this module's own scope.
- No blockers.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/importer/migration/footprints.py
- FOUND: tests/test_migration_footprints.py
- FOUND: commit b82afd7 (Task 1)
- FOUND: commit 3ed900c (Task 2 RED)
- FOUND: commit c59ac71 (Task 2 GREEN)
- FOUND: commit 6c5c908 (Task 3 RED)
- FOUND: commit cadfbc8 (Task 3 GREEN)
- `pytest tests/test_migration_footprints.py tests/test_migration_e2e.py tests/test_importer_layering.py tests/test_plain_names.py -q` -> 38 passed
- `pytest tests/ -k migration -q` -> 67 passed, 3398 deselected
