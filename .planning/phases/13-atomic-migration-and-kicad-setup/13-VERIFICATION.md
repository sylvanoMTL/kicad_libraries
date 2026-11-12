---
phase: 13-atomic-migration-and-kicad-setup
verified: 2026-11-12T12:30:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files: [".planning/phases/13-atomic-migration-and-kicad-setup/13-01-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-01-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-02-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-02-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-03-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-03-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-04-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-04-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-05-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-05-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-06-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-06-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-07-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-07-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-08-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-08-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-09-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-09-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-10-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-10-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-11-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-11-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-12-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-12-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-13-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-13-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-14-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-14-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-15-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-15-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-16-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-16-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-17-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-17-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-18-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-18-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-19-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-19-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-20-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-20-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-21-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-21-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-22-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-22-SUMMARY.md", "kicad_lib_manager/importer/migration/applier.py", "kicad_lib_manager/importer/migration/footprints.py", "tests/test_migration_apply.py", "tests/test_migration_e2e.py", "tests/test_migration_footprints.py"]
covered_digest: "v3:sha256:11a58e0361c388f1d08f3d78d80f36cb742c9e9efad4bbc0e4849adeec118d7d"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "A 3D-model rename candidate colliding only by letter case with an untouched, unlinked, pre-existing model file is no longer silently destroyed: _model_final_names's existing-model guard in footprints.py now casefolds the comparison against a prebuilt casefolded inventory (model_names_cf), mirroring the already-correct claimed_model_names registry. Confirmed by reading the guard at footprints.py (candidate.casefold() in model_names_cf) and by independently running the exact reproduction test, tests/test_migration_e2e.py::test_model_rename_cannot_overwrite_an_untouched_model, which builds the identical scenario the prior verification round used to demonstrate the gap (an untouched TAKEN.STEP model and a colliding rename candidate) and now asserts the untouched file's bytes survive a full plan/gate/apply/disk round trip — passes."
    - "The exact-name collision variant of the same guard (candidate matches an on-disk model exactly, not just by case) is now covered by its own regression, tests/test_migration_footprints.py::test_model_rename_onto_an_exact_existing_name_keeps_its_name — passes."
    - "A rename chain (A renaming onto B while B itself renames away) is refused rather than reordered, because the guard keeps comparing against the whole pre-migration inventory rather than a post-migration projection — tests/test_migration_footprints.py::test_a_rename_onto_a_model_that_is_itself_renamed_is_kept — passes."
    - "The kept-name note is confirmed plain-language, single, and non-blocking (Run stays enabled) — tests/test_migration_footprints.py::test_model_kept_name_note_is_plain_and_single and test_untouched_model_collision_raises_no_blocking_line — both pass."
    - "A structural, transaction-layer backstop now exists for the whole defect class (not only this one instance): applier.py's _preflight gained migration.rename_would_overwrite, refusing before the first byte any write op carrying source_rel whose target existed at plan time and is removed by no delete op in the same plan — confirmed by reading the new block in _preflight and by independently running tests/test_migration_apply.py::test_rename_overwrite_plan_is_refused — passes."
  gaps_remaining: []
  regressions: []
---

# Phase 13: Atomic Migration and KiCad Setup Verification Report

**Phase Goal:** All existing `Custom/` parts move to the `Atomic_` scheme in one previewed, reversible commit, with every part passing the atomic rule, and KiCad's library list and chooser show the new libraries
**Verified:** 2026-11-12T12:30:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure 13-22 (CR-01's second manifestation)

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Migration refuses to start while `Custom` has uncommitted changes; tags `pre-atomic` before writing; preview shows target library, footprint destination, every rename/field change and every atomic-rule failure with an edit box; Run disabled until every part passes | ✓ VERIFIED | Unchanged by 13-22; not touched by this gap-closure plan; `precheck.check_custom`/`ensure_tag` and `migration_dialog.py` still present (quick regression check — no modification since prior verification round) |
| 2 | One transaction with rollback leaves no v1-named library; every footprint moved to `Atomic_Footprints`/official; every Footprint field and model path rewritten; every `.bak` gone; next scan reports zero atomic violations | ✓ VERIFIED | **Gap closed.** `_model_final_names`'s existing-model guard in `kicad_lib_manager/importer/migration/footprints.py` now compares `candidate.casefold()` against a prebuilt casefolded inventory `model_names_cf` (read directly in this session), and `applier.py`'s `_preflight` gained a structural `migration.rename_would_overwrite` backstop. Independently ran the exact prior-round reproduction as a real pytest test (`test_model_rename_cannot_overwrite_an_untouched_model`): the untouched model's bytes survive a full plan/gate/apply/disk round trip. All 54 tests in the three touched test files pass; the whole-fixture `test_migration_full.py` and the dialog/gate/layering suites named in the plan's own `<verification>` block also pass with no regressions. |
| 3 | Regenerated tables drop old names, add new ones with non-empty descriptions; one `Custom` commit plus a parent ref commit offered through the commit step | ✓ VERIFIED | Unchanged by 13-22; not touched by this gap-closure plan, no regression found (quick regression check — file presence confirmed, not modified by the 13-22 commits) |
| 4 | One confirmed action sets up KiCad 10's chooser: pins `Atomic_` libraries, adds MPN/Manufacturer columns, removes stray MANUFACTURER, shows old→new first, backs up config, refuses from a worktree/other checkout | ✓ VERIFIED | Unchanged by 13-22; not touched by this gap-closure plan, no regression found |
| 5 | App shows/saves old→new library map plus KiCad relink steps; `CLAUDE.md`, PROJECT.md and `research/LIBRARY-NAMING.md` describe the `Atomic_` scheme and atomic rule | ✓ VERIFIED | Unchanged by 13-22; not touched by this gap-closure plan, no regression found |

**Score:** 5/5 truths verified (the previously-failing truth 2 is now closed and independently confirmed)

### Gap Closure Confirmation (what 13-22 fixed)

| Scenario | Status | Evidence |
|---|---|---|
| A rename candidate collides, case-insensitively only, with an untouched, pre-existing model file (the exact scenario this phase's previous VERIFICATION.md reproduced and recorded as the remaining gap) | ✓ CLOSED | `model_names_cf = {name.casefold() for name in model_name_set}` built once in `_model_final_names`; guard now reads `if candidate.casefold() in model_names_cf:`. Confirmed by direct code read and by running `test_model_rename_cannot_overwrite_an_untouched_model`, which reproduces the prior gap's own scenario (an untouched `TAKEN.STEP`/`taken.step`-style collision) and asserts the untouched file's bytes survive apply — passes. |
| A rename candidate collides exactly (same spelling) with an on-disk model not part of any rename group | ✓ CLOSED (previously untested, now covered) | `test_model_rename_onto_an_exact_existing_name_keeps_its_name` — passes |
| A rename chain (A→B while B→C) that would let an in-order delete remove freshly-written bytes | ✓ CLOSED | Guard keeps comparing against the *whole* pre-migration inventory, not a post-migration projection; `test_a_rename_onto_a_model_that_is_itself_renamed_is_kept` — passes |
| Structural backstop for the defect class, independent of which planner path produces it | ✓ CLOSED | `applier.py` `_preflight` new `migration.rename_would_overwrite` block, scoped to writes carrying `source_rel`; `test_rename_overwrite_plan_is_refused` — passes |
| Kept-name note is plain-language, single, and non-blocking | ✓ CLOSED | `test_model_kept_name_note_is_plain_and_single`, `test_untouched_model_collision_raises_no_blocking_line` — both pass |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kicad_lib_manager/importer/migration/footprints.py` | Casefolded existing-model guard (`model_names_cf`) in `_model_final_names` | ✓ VERIFIED | Read directly: the set is built once per call, and the guard's condition is `candidate.casefold() in model_names_cf`; the dead `and candidate != old_name` clause was correctly dropped per the plan's reasoning (the preceding case-only-self-match branch already handles that case) |
| `kicad_lib_manager/importer/migration/applier.py` | `migration.rename_would_overwrite` invariant in `_preflight`, placed after `migration.duplicate_write` and before the staleness loop | ✓ VERIFIED | Read directly: block collects `deleted` (casefolded delete-op paths) and flags any write op with `source_rel is not None`, `base_sha256 is not None`, and a casefolded path not in `deleted`; returns early exactly like the blocks above it |
| `tests/test_migration_e2e.py` | `test_model_rename_cannot_overwrite_an_untouched_model` | ✓ VERIFIED | Present (line 158); passes |
| `tests/test_migration_footprints.py` | Five new regression tests (case-only, exact, chain, wording, non-blocking) | ✓ VERIFIED | All five present (lines 736, 763, 790, 823, 844); all pass |
| `tests/test_migration_apply.py` | `test_rename_overwrite_plan_is_refused` | ✓ VERIFIED | Present (line 200); passes |
| All other Phase 13 artifacts (table_generator.py, kicad_setup.py, mapfile.py, CLAUDE.md, LIBRARY-NAMING.md, migration_dialog.py, main_window.py, etc.) | Unchanged since prior verification | ✓ VERIFIED (regression check only) | Confirmed by `git show --stat` on all five 13-22 commits: only `footprints.py`, `applier.py`, and the three named test files were touched; no other phase artifact was modified |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `footprints._model_final_names` (casefolded guard) | rename op loop (lines 477-489) | `model_final_name[old_name] == old_name`, so neither write nor delete is ever created for a kept group | ✓ WIRED — confirmed by `test_model_rename_cannot_overwrite_an_untouched_model` asserting no op `rel` starts with `Custom/3DModels/` for the colliding candidate |
| `applier._preflight` `migration.rename_would_overwrite` | `apply_migration`'s pre-write refusal | a write op's `source_rel` present, `base_sha256` present, and casefolded path not among this plan's deletes | ✓ WIRED — confirmed by `test_rename_overwrite_plan_is_refused` asserting `result.ok is False` and the target file's bytes unchanged |
| `_preflight`'s existing `migration.duplicate_write` block | its message text | now names both colliding ops' own `rel` spelling (review WR-01, first occurrence) | ✓ WIRED — confirmed by the corrected `test_duplicate_write_plan_is_refused` assertion (SUMMARY documents this as an auto-fixed test-assertion bug, now passing) |

### Behavioral Spot-Checks / Targeted Test Runs

Full workspace suite was not re-run (per orchestrator constraint — ~9650 tests, ~30 min). Targeted runs executed directly in this verification session:

| Test file(s) | Result |
|---|---|
| `tests/test_migration_e2e.py tests/test_migration_footprints.py tests/test_migration_apply.py` | 54 passed |
| `tests/test_migration_gate.py tests/test_migration_dialog_files.py tests/test_migration_dialog_run.py tests/test_importer_layering.py` | 39 passed |
| `tests/test_migration_full.py` (slow whole-fixture, real-git run) | 1 passed |

No debt markers (`TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`) found in any of the five files this round's gap-closure touched.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| TBL-01 | 13-01, 13-17, 13-19 | Table entries carry a non-empty description | ✓ SATISFIED | Unchanged since prior verification; not touched by 13-22 |
| TBL-02 | 13-02, 13-07, 13-18 | One confirmed action sets up KiCad 10's chooser | ✓ SATISFIED | Unchanged since prior verification; not touched by 13-22 |
| MIG-01 | 13-03, 13-13, 13-14, 13-16, 13-18, 13-20 | Refuses to start with uncommitted changes; tags `pre-atomic` | ✓ SATISFIED | Unchanged since prior verification; not touched by 13-22 |
| MIG-02 | 13-05, 13-06, 13-08, 13-09, 13-12, 13-14, 13-17, 13-18, 13-21, 13-22 | Preview shows target library, footprint destination, renames, field changes, atomic-rule failures with edit box; Run blocked until all pass | ✓ SATISFIED | 13-22's `migration.model_kept_name` INFO note and `gate._whole_set_lines`'s ERROR-only lift confirmed non-blocking by `test_untouched_model_collision_raises_no_blocking_line` |
| MIG-03 | 13-05, 13-06, 13-09, 13-10, 13-13, 13-15, 13-16, 13-18, 13-20, 13-21, 13-22 | One transaction with rollback; moves every part/footprint; rewrites every Footprint field and model path | ✓ SATISFIED | **Now fully satisfied.** Both manifestations of CR-01 (group-vs-group from 13-21, and case-insensitive-vs-untouched-model from 13-22) are closed and independently confirmed by running their tests directly |
| MIG-04 | 13-04, 13-12, 13-13, 13-17, 13-18, 13-19, 13-20 | Post-migration scan reports zero violations; tables regenerated; commit offered | ✓ SATISFIED | Unchanged since prior verification; not touched by 13-22 |
| MIG-05 | 13-06, 13-12, 13-13, 13-16, 13-18, 13-20 | Shows/saves old→new map and relink steps | ✓ SATISFIED | Unchanged since prior verification; not touched by 13-22 |
| DOC-01 | 13-18 | CLAUDE.md, PROJECT.md, LIBRARY-NAMING.md describe the Atomic_ scheme | ✓ SATISFIED | Unchanged since prior verification; not touched by 13-22 |

No orphaned requirements: all 8 IDs assigned to Phase 13 in REQUIREMENTS.md (TBL-01, TBL-02, MIG-01..05, DOC-01) are claimed by at least one of the phase's 22 plans.

**Note on REQUIREMENTS.md tracking table:** `.planning/REQUIREMENTS.md`'s own checkbox/status column still marks MIG-01, MIG-04, MIG-05, TBL-01, TBL-02 and DOC-01 as "Pending" (only MIG-02/MIG-03 show `[x]`/"Complete"). This is a documentation-sync lag in a file this verifier does not own, not a code defect — the prior VERIFICATION.md round already confirmed these five requirements SATISFIED with concrete evidence, and this round's regression check found no change to any of their supporting artifacts. Flagged here for the record, not as a gap.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `kicad_lib_manager/importer/migration/applier.py` | ~279-284 | `migration.rename_would_overwrite`'s message names only the write op's destination (`op.rel`), not the rename's source (`op.source_rel`), per the latest `13-REVIEW.md` (new finding, reused id WR-01, disposition `open` in `13-REVIEW-DISPOSITION.md`, not addressed by 13-22) | ⚠️ Warning | Diagnostic-quality only — this is a developer-facing backstop for a planner bug, not an owner-facing path (the planner path that could produce such an op was already removed by Task 1); the refusal itself still fires correctly and no data is at risk |
| `kicad_lib_manager/widgets/commit_panel.py` | 591-597 | Deleted-row early return skips the dirty-marker check (WR-02, open per `13-REVIEW-DISPOSITION.md`, pre-existing, not touched by 13-22) | ⚠️ Warning | Currently unreachable given the precheck's clean-Custom invariant; carried forward unchanged from the prior verification round |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in `footprints.py`, `applier.py`, or any of the three test files modified by 13-22.

### Human Verification Required

### 1. Owner's live migration UAT (main checkout, real Custom/, real KiCad 10)

**Test:** Run the full migration end to end from the main checkout (`C:/Git_Repo_Clones/Kicad_Libraries`, not this worktree) against the real `Custom/` submodule and a real KiCad 10 install, following the UAT check list referenced in `13-18-SUMMARY.md` (coverage item D6).
**Expected:** Preview shows every real part and passes; Run completes as one transaction; the post-migration scan reports zero atomic violations; Generate Tables and Set Up KiCad Chooser behave as documented; the `Custom` + parent-ref commits are made; KiCad's chooser shows the new `Atomic_` libraries pinned.
**Why human:** This is a live run against the owner's real `Custom/` submodule and real KiCad 10 settings; `13-18-SUMMARY.md` marks this item `human_judgment: true` (coverage D6), and this verification's own instructions forbid touching the `Custom` submodule or the owner's KiCad configuration. The blocking gap that previously made this unsafe to run (CR-01's case-insensitive-vs-untouched-model manifestation) is now closed and independently confirmed in this session — the owner may proceed with this UAT.

### Gaps Summary

No gaps remain from this verification round. The single gap carried forward from the prior `gaps_found` round — a rename candidate colliding only by letter case with an untouched, pre-existing model file silently destroying that file's content — is closed: `_model_final_names`'s existing-model guard now casefolds its comparison against a prebuilt casefolded inventory, and a new structural `migration.rename_would_overwrite` invariant in the applier's `_preflight` backstops the whole defect class (not only the specific instance) at the transaction boundary.

This was confirmed by (1) direct reading of both changed production files, confirming the code matches the plan's and SUMMARY's descriptions exactly; (2) independently running all 54 tests in the three test files 13-22 touched, all passing; (3) independently running the gate/dialog/layering suites and the slow whole-fixture `test_migration_full.py` named in the plan's own `<verification>` block, confirming zero regressions; (4) confirming via `git show --stat` on all five 13-22 commits that only the five declared files were touched, so the "unchanged since prior verification" claim for every other phase artifact holds structurally, not just by assertion; and (5) confirming `13-REVIEW-DISPOSITION.md` records CR-01 and IN-01 as `fixed`.

The phase goal is now achieved in the codebase. The remaining item is the owner's own live migration run against real data, which by design no automated check may perform — this routes the overall status to `human_needed` rather than `passed`, per the decision tree (a non-empty human-verification section always does, even when every truth is independently verified). Two pre-existing `⚠️ Warning`-severity findings (WR-01 diagnostic wording, WR-02 commit-panel edge case) remain open in `13-REVIEW-DISPOSITION.md`; neither blocks the phase goal or the owner's live UAT.

---

*Verified: 2026-11-12T12:30:00Z*
*Verifier: Claude (gsd-verifier)*
