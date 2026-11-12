---
phase: 13-atomic-migration-and-kicad-setup
verified: 2026-11-12T11:40:00Z
status: gaps_found
score: 4/5 must-haves verified
covered_files: [".planning/phases/13-atomic-migration-and-kicad-setup/13-01-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-01-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-02-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-02-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-03-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-03-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-04-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-04-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-05-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-05-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-06-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-06-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-07-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-07-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-08-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-08-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-09-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-09-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-10-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-10-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-11-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-11-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-12-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-12-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-13-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-13-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-14-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-14-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-15-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-15-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-16-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-16-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-17-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-17-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-18-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-18-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-19-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-19-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-20-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-20-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-21-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-21-SUMMARY.md", "kicad_lib_manager/importer/migration/applier.py", "kicad_lib_manager/importer/migration/footprints.py", "tests/test_migration_apply.py", "tests/test_migration_footprints.py"]
covered_digest: "v3:sha256:1b2340cbdfe58973597b3f6f5fd0c902852433914a17a6d4138a6f097c49bc9d"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5
  gaps_closed:
    - "Two 3D model rename groups within one run resolving to the same candidate file name is now a blocking migration.model_clash strip line (the original CR-01 scenario: group-vs-group collision), confirmed by direct code reading of _model_final_names's claimed-name registry (footprints.py:295-361) and by independently running tests/test_migration_footprints.py::test_colliding_model_names_queue_no_write, test_colliding_model_names_are_case_insensitive, test_three_groups_one_name_keeps_the_sorted_first, test_two_models_resolving_to_one_name_block_run, test_added_model_cannot_take_an_existing_model_name — all pass."
    - "A migration plan holding two write ops for the same casefolded path is structurally refused before the first byte (applier.py _preflight's new migration.duplicate_write check), confirmed by running tests/test_migration_apply.py::test_duplicate_write_plan_is_refused — passes."
    - "Choosing Overwrite for a footprint name this run is already creating for another part is refused (migration.overwrite_refused in _resolve_clash), confirmed by running tests/test_migration_footprints.py::test_in_run_footprint_overwrite_is_refused — passes."
  gaps_remaining:
    - "A model-rename candidate that collides, case-insensitively only, with an UNTOUCHED pre-existing model file (one that is not itself part of any rename group) is not caught: _model_final_names's guard at footprints.py:329 ('if candidate in model_name_set and candidate != old_name') is exact-string, case-sensitive Python membership against model_name_set, while the write op this decision drives is placed via new_path.exists() (footprints.py:485), a real, case-insensitive filesystem call on Windows (the project's stated primary platform). This is the same destructive defect class as the original CR-01, reached through a different, still-open path (13-REVIEW.md, this review session, new finding under the reused id CR-01; 13-REVIEW-DISPOSITION.md records disposition 'open', no closure plan has run)."
  regressions: []
gaps:
  - truth: "Running the migration as one transaction with rollback never silently destroys a part's data — every operation that would overwrite another part's file is caught as a blocking issue before Run (ROADMAP SC2; MIG-02 'every atomic-rule failure with an edit box'; MIG-03 'rewrites every Footprint field and model path')"
    status: failed
    reason: >
      Independently reproduced in this verification session (not merely trusting 13-REVIEW.md's
      prose): built a tmp_path repo with one part whose footprint links model OLD1.step
      (content b"OLD1-CONTENT"), plus an unrelated, untouched, unlinked model file TAKEN.STEP
      (content b"UNRELATED-ORIGINAL-CONTENT") already on disk. Gave the part's choice
      model_name="taken". plan_footprints returned zero issues and queued exactly one write op:
      MigrationOp("write", .../Custom/3DModels/taken.step, data=b"OLD1-CONTENT",
      base_sha256=sha256(b"UNRELATED-ORIGINAL-CONTENT")) — the base_sha256 matching the
      UNRELATED file's current content confirms new_path.exists() resolved true against
      TAKEN.STEP via Windows' case-insensitive filesystem, even though the case-sensitive
      `candidate in model_name_set` guard at footprints.py:329 missed the collision (the
      candidate string "taken.step" is not equal to the on-disk "TAKEN.STEP" as Python strings).
      Built the resulting MigrationPlan with the project's own test fixtures and ran it through
      the real apply_migration: result.ok was True, result.issues contained only
      Severity.SUCCESS "migration.done — Migrated 0 parts into 0 Atomic_ libraries", and
      TAKEN.STEP's on-disk content after apply was b"OLD1-CONTENT" — the unrelated model's
      original bytes are gone, permanently, with no issue, warning, or rollback of any kind.
      This is the identical failure shape as the original CR-01 gap (a "successful" transaction
      that silently destroys a part's file), now through a narrower trigger: a rename candidate
      colliding only by case with an on-disk model that is not itself part of any rename group
      (so the group-vs-group registry fix in 13-21 does not see it, and applier.py's new
      migration.duplicate_write backstop cannot see it either, because there is only one write
      op in the plan — the pre-existing TAKEN.STEP is never referenced by any op). Disposition in
      13-REVIEW-DISPOSITION.md is `open` (unresolved); no gap-closure plan has addressed this
      finding yet.

      By contrast, the original CR-01 scenario (two rename groups both wanting the same name) IS
      now closed: tests/test_migration_footprints.py::test_colliding_model_names_queue_no_write,
      test_colliding_model_names_are_case_insensitive, test_three_groups_one_name_keeps_the_sorted_first,
      and the end-to-end test_two_models_resolving_to_one_name_block_run all pass when run
      directly in this session, confirming the claimed-name registry (_model_final_names,
      footprints.py:295-361) correctly blocks that case. The owner-added-model path (D-15) is
      also correctly guarded: its check at footprints.py:525 (`claim_key in claimed_model_names`)
      compares casefolded strings against a casefolded registry (footprints.py:474-475), unlike
      the rename pass's guard. The footprint-name clash path (`_resolve_clash`) is also safe: its
      `known`/`taken_stems` checks are backed by a real `existing_path.exists()` filesystem call
      (footprints.py:193-195), not a frozen in-memory set, so it cannot suffer this same
      case-mismatch. The defect is narrowly confined to the one guard at footprints.py:329.
    artifacts:
      - path: "kicad_lib_manager/importer/migration/footprints.py"
        issue: "_model_final_names's existing-model guard (line 329: `if candidate in model_name_set and candidate != old_name`) is case-sensitive Python string membership, while the write op it permits at lines 477-489 is placed via new_path.exists() (line 485), a case-insensitive real filesystem call on the project's primary platform (Windows). naming.py already has a case_clash(name, existing) helper built for this exact comparison, but _model_final_names does not use it."
    missing:
      - "Casefold the existing-model guard in _model_final_names: compare candidate.casefold() against a casefolded view of model_name_set (mirroring how claimed_model_names is already built correctly for the D-15 added-model path at footprints.py:474), so a rename candidate differing only by case from any on-disk model — whether or not that model is part of a rename group — is caught and raises migration.model_kept_name (or model_clash, per the fix 13-REVIEW.md proposes) instead of silently queuing an overwrite."
      - "A regression test seeding an untouched, unlinked model file and a rename candidate that collides with it only by case, asserting no write op targets the shared casefolded path and an issue is raised (13-REVIEW.md IN-01 proposes this exact test; none of the seven tests added by 13-21 covers this scenario)."
human_verification:
  - test: "Run the full migration end to end from the main checkout (C:/Git_Repo_Clones/Kicad_Libraries) against the real Custom/ submodule and a real KiCad 10 install, per the UAT check list in 13-18-SUMMARY.md (coverage item D6)."
    expected: "Preview shows every real part and passes; Run completes as one transaction; the post-migration scan reports zero atomic violations; Generate Tables and Set Up KiCad Chooser behave as documented; the Custom + parent-ref commits are made."
    why_human: "This is a live run against the owner's real Custom/ submodule and real KiCad 10 settings; no automated test may touch that live data (13-18-SUMMARY.md explicitly marks this human_judgment: true, coverage D6), and this verification's own instructions forbid touching the Custom submodule. Given the still-open CR-01 case-insensitivity gap, the owner must not run this live migration yet — a typed model_name or MPN whose sanitized 3D-model file name differs only by case from an existing, untouched model file in the real Custom/3DModels/ would silently destroy that file with zero warning, exactly as reproduced in this verification."
---

# Phase 13: Atomic Migration and KiCad Setup Verification Report

**Phase Goal:** All existing `Custom/` parts move to the `Atomic_` scheme in one previewed, reversible commit, with every part passing the atomic rule, and KiCad's library list and chooser show the new libraries
**Verified:** 2026-11-12T11:40:00Z
**Status:** gaps_found
**Re-verification:** Yes — after gap closure 13-21 (CR-01)

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Migration refuses to start while `Custom` has uncommitted changes; tags `pre-atomic` before writing; preview shows target library, footprint destination, every rename/field change and every atomic-rule failure with an edit box; Run disabled until every part passes | ✓ VERIFIED | Unchanged by 13-21; `precheck.check_custom`/`ensure_tag` and `migration_dialog.py` still present and wired (file existence + no modification since prior verification confirmed) |
| 2 | One transaction with rollback leaves no v1-named library; every footprint moved to `Atomic_Footprints`/official; every Footprint field and model path rewritten; every `.bak` gone; next scan reports zero atomic violations | ✗ FAILED | **Still failing.** 13-21 closed the original CR-01 scenario (two rename groups colliding) — confirmed by direct code read and by independently running the relevant tests. But this verification independently reproduced a new, still-open manifestation of the same defect class: a rename candidate that collides only by case with an untouched, pre-existing model file is not caught (`_model_final_names`'s guard at footprints.py:329 is case-sensitive while the real write path is case-insensitive on Windows). Reproduction: `apply_migration` returned `ok=True`, `issues` contained only a SUCCESS `migration.done`, and an unrelated `TAKEN.STEP` model file's content was silently overwritten and destroyed. See Gaps. |
| 3 | Regenerated tables drop old names, add new ones with non-empty descriptions; one `Custom` commit plus a parent ref commit offered through the commit step | ✓ VERIFIED | Unchanged by 13-21; not touched by this gap-closure plan, no regression found (file presence and line-count sanity checked) |
| 4 | One confirmed action sets up KiCad 10's chooser: pins `Atomic_` libraries, adds MPN/Manufacturer columns, removes stray MANUFACTURER, shows old→new first, backs up config, refuses from a worktree/other checkout | ✓ VERIFIED | Unchanged by 13-21; not touched by this gap-closure plan, no regression found |
| 5 | App shows/saves old→new library map plus KiCad relink steps; `CLAUDE.md`, PROJECT.md and `research/LIBRARY-NAMING.md` describe the `Atomic_` scheme and atomic rule | ✓ VERIFIED | Unchanged by 13-21; not touched by this gap-closure plan, no regression found |

**Score:** 4/5 truths verified (1 failed — new manifestation of the CR-01 defect class, same truth as the previous verification round)

### Gap Closure vs. New Finding (what 13-21 actually fixed)

| Scenario | Status | Evidence |
|---|---|---|
| Two rename groups both claim the same candidate model file name (the original CR-01 scenario verified gaps_found on) | ✓ CLOSED | `_model_final_names` claimed-name registry (`footprints.py:295-361`); `test_colliding_model_names_queue_no_write`, `test_colliding_model_names_are_case_insensitive`, `test_three_groups_one_name_keeps_the_sorted_first`, `test_two_models_resolving_to_one_name_block_run` run directly in this session — all pass |
| An owner-added 3D model (D-15) takes another part's model file name | ✓ CLOSED | `claimed_model_names` casefolded registry (`footprints.py:474-475, 524-525`); `test_added_model_cannot_take_an_existing_model_name` passes |
| A plan holding two write ops for one path reaches the filesystem | ✓ CLOSED (structural backstop) | `applier.py` `_preflight`'s new `migration.duplicate_write` check; `test_duplicate_write_plan_is_refused` passes |
| Overwrite chosen for a footprint name this run is already creating for another part | ✓ CLOSED | `_resolve_clash`'s `queued` set and `migration.overwrite_refused`; `test_in_run_footprint_overwrite_is_refused` passes |
| A rename candidate collides **only by case** with an **untouched, pre-existing** model file (not part of any rename group) | ✗ STILL OPEN | Independently reproduced in this session (see Gaps); no write-op collision exists for the structural backstop to catch, since the pre-existing file is never referenced by any op |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kicad_lib_manager/importer/migration/footprints.py` | `_model_final_names` claimed-name registry, `migration.model_clash`, `migration.overwrite_refused`, `queued` threading | ✓ VERIFIED (with residual defect) | Present (774 lines); `_model_final_names` (lines 295-361) correctly closes group-vs-group and added-model collisions; its existing-model guard (line 329) is case-sensitive against a case-insensitive filesystem — see Gaps |
| `kicad_lib_manager/importer/migration/applier.py` | `migration.duplicate_write` preflight check | ✓ VERIFIED | Present (569 lines); `test_duplicate_write_plan_is_refused` passes; this backstop is structurally unable to see the remaining gap (only one write op exists in that scenario) |
| `tests/test_migration_footprints.py` | Seven CR-01 regression tests (13-21) | ✓ VERIFIED | All seven present and pass (confirmed by direct pytest run), but none constructs the case-insensitive-vs-untouched-model scenario (13-REVIEW.md IN-01, independently confirmed by reading the file's new test section) |
| `tests/test_migration_apply.py` | `test_duplicate_write_plan_is_refused` | ✓ VERIFIED | Present and passes |
| All other Phase 13 artifacts (table_generator.py, kicad_setup.py, mapfile.py, CLAUDE.md, LIBRARY-NAMING.md, migration_dialog.py, main_window.py, etc.) | Unchanged since prior verification | ✓ VERIFIED (regression check only) | Not modified by 13-21; existence and line-count sanity confirmed, no further re-verification performed per Step 0's "passed items: quick regression check" rule |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `footprints._model_final_names` | `gate._whole_set_lines` | `migration.model_clash` ERROR in `plan.issues` | ✓ WIRED (for the group-vs-group and added-model cases; `test_two_models_resolving_to_one_name_block_run` confirms `run_enabled is False`) |
| `footprints.plan_footprints` (rename pass, line 477-489) | `applier.apply_migration` | `MigrationOp` write/delete pair | ⚠️ WIRED BUT STILL UNSAFE for the case-insensitive-vs-untouched-model path — the write op this link produces for a colliding candidate carries a `base_sha256` seeded from the unrelated file's real content (confirmed by direct reproduction), and no issue accompanies it, so the applier has no signal to refuse |
| `applier._preflight` `migration.duplicate_write` | `apply_migration`'s pre-write refusal | duplicate casefolded `op.path` | ✓ WIRED for actual duplicate ops; **not applicable** to the remaining gap, where only one op exists |

### Behavioral Spot-Checks / Targeted Test Runs

Full workspace suite was not re-run (per orchestrator constraint — ~29 min). Targeted runs executed directly in this verification session:

| Test file(s) | Result |
|---|---|
| `tests/test_migration_footprints.py tests/test_migration_apply.py tests/test_migration_gate.py tests/test_migration_full.py` | 46 passed |
| Standalone reproduction script (not pytest): built a tmp_path repo with one rename candidate colliding by case with an untouched model file, ran the real `plan_footprints` then the real `apply_migration` | `apply ok: True`, unrelated model file's content destroyed — confirms the gap independently of 13-REVIEW.md's own reproduction |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| TBL-01 | 13-01, 13-17, 13-19 | Table entries carry a non-empty description | ✓ SATISFIED | Unchanged since prior verification; not touched by 13-21 |
| TBL-02 | 13-02, 13-07, 13-18 | One confirmed action sets up KiCad 10's chooser | ✓ SATISFIED | Unchanged since prior verification; not touched by 13-21 |
| MIG-01 | 13-03, 13-13, 13-14, 13-16, 13-18, 13-20 | Refuses to start with uncommitted changes; tags `pre-atomic` | ✓ SATISFIED | Unchanged since prior verification; not touched by 13-21 |
| MIG-02 | 13-05, 13-06, 13-08, 13-09, 13-12, 13-14, 13-17, 13-18, 13-21 | Preview shows target library, footprint destination, renames, field changes, atomic-rule failures with edit box; Run blocked until all pass | ✓ SATISFIED (for the failure modes the gate now models) | `gate.check_plan` plus 13-21's new `migration.model_clash`/`migration.overwrite_refused` whole-set lines; but the case-insensitive-vs-untouched-model failure mode (below) is still never modeled as a gate Issue, so MIG-02's "every atomic-rule failure" promise still has a real gap for that one scenario |
| MIG-03 | 13-05, 13-06, 13-09, 13-10, 13-13, 13-15, 13-16, 13-18, 13-20, 13-21 | One transaction with rollback; moves every part/footprint; rewrites every Footprint field and model path | ✗ BLOCKED | 13-21 closed the group-vs-group and duplicate-write-op manifestations of CR-01, but the case-insensitive-vs-untouched-model manifestation (same defect class) remains open and was independently reproduced in this session |
| MIG-04 | 13-04, 13-12, 13-13, 13-17, 13-18, 13-19, 13-20 | Post-migration scan reports zero violations; tables regenerated; commit offered | ✓ SATISFIED (necessary but not sufficient, per MIG-03) | Unchanged since prior verification; zero-violations still does not detect the model-content loss, since model-content identity is outside the atomic rule |
| MIG-05 | 13-06, 13-12, 13-13, 13-16, 13-18, 13-20 | Shows/saves old→new map and relink steps | ✓ SATISFIED | Unchanged since prior verification; not touched by 13-21 |
| DOC-01 | 13-18 | CLAUDE.md, PROJECT.md, LIBRARY-NAMING.md describe the Atomic_ scheme | ✓ SATISFIED | Unchanged since prior verification; not touched by 13-21 |

No orphaned requirements: all 8 IDs assigned to Phase 13 in REQUIREMENTS.md (TBL-01, TBL-02, MIG-01..05, DOC-01) are claimed by at least one of the phase's 21 plans (13-21 adds MIG-02, MIG-03 coverage on top of the plans already claiming them).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `kicad_lib_manager/importer/migration/footprints.py` | 329 | Existing-model membership check is exact-string/case-sensitive (`candidate in model_name_set`) against a filesystem path decision (`new_path.exists()`, line 485) that is case-insensitive on the project's primary platform (Windows) — confirmed by direct code read and independent reproduction in this session | 🛑 Blocker | Silent data loss on Run for this one trigger shape; no Issue/Conflict/rollback; same violation of "reversible" and "every part passing" as the original CR-01, now narrower in scope |
| `kicad_lib_manager/widgets/migration_dialog.py` | 322-323, 338, 373 | `CommitPlan`/`CommitProbe` annotated but never imported (WR-01, open per 13-REVIEW-DISPOSITION.md) | ⚠️ Warning | Static-analysis blind spot only; no runtime effect |
| `kicad_lib_manager/widgets/commit_panel.py` | 591-597 | Deleted-row early return skips the dirty-marker check (WR-02, open per 13-REVIEW-DISPOSITION.md) | ⚠️ Warning | Currently unreachable given the precheck's clean-Custom invariant |
| `kicad_lib_manager/importer/migration/applier.py` | 243-259 | `migration.duplicate_write` can misname which of two colliding ops is reported when paths differ only by case (WR-01 of the latest 13-REVIEW.md; recorded as WR-01 in disposition, open) | ⚠️ Warning | Diagnostic-only; the refusal itself still fires correctly |
| `tests/test_migration_footprints.py` | — | No regression test exercises a rename candidate colliding (case-insensitively) with an untouched, unlinked model file (IN-01, open per 13-REVIEW-DISPOSITION.md) | ℹ️ Info | Directly explains why this gap survived the 13-21 gap-closure's own test suite |
| `kicad_lib_manager/main_window.py` | 1276 | Unused `result` parameter in `_on_migrated` (IN-01 of the original review, open) | ℹ️ Info | Cosmetic only |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in `footprints.py` or `applier.py` (the two files this round's gap-closure touched).

### Human Verification Required

### 1. Owner's live migration UAT (main checkout, real Custom/, real KiCad 10) — DO NOT RUN until the remaining gap is closed

**Test:** Run the full migration end to end from the main checkout (`C:/Git_Repo_Clones/Kicad_Libraries`, not this worktree) against the real `Custom/` submodule and a real KiCad 10 install, following the UAT check list referenced in `13-18-SUMMARY.md` (coverage item D6).
**Expected:** Preview shows every real part and passes; Run completes as one transaction; the post-migration scan reports zero atomic violations; Generate Tables and Set Up KiCad Chooser behave as documented; the `Custom` + parent-ref commits are made; KiCad's chooser shows the new `Atomic_` libraries pinned.
**Why human:** This is a live run against the owner's real `Custom/` submodule and real KiCad 10 settings; `13-18-SUMMARY.md` marks this item `human_judgment: true` (coverage D6), and this verification's own instructions forbid touching the `Custom` submodule. **The owner should not run this live migration until the remaining CR-01 gap below is closed** — a typed `model_name` or default MPN whose sanitized 3D-model file name differs only by letter case from any existing, untouched file in the real `Custom/3DModels/` would silently destroy that file's content with zero warning, exactly as independently reproduced in this verification session.

### Gaps Summary

13-21 correctly closed every scenario it set out to close: the group-vs-group model-rename collision, the owner-added-model-vs-registry collision, the structural duplicate-write-op backstop, and the in-run footprint-Overwrite refusal are all confirmed working by direct code reading and by independently running their regression tests in this session (46 tests passed, including the slow whole-fixture `test_migration_full.py`). This is genuine, verified progress — the phase is not back to square one.

However, the phase goal's "reversible" promise is still false for one narrower-but-equally-destructive trigger shape, discovered by the incremental code review (`13-REVIEW.md`, same session as this verification) and **independently reproduced from scratch in this verification** rather than taken on the review's word: `_model_final_names`'s guard against renaming a model onto an already-used file name (`footprints.py:329`) compares the candidate name to the pre-migration inventory using exact-string, case-sensitive Python membership — but the write operation this guard permits is placed onto the real filesystem via `Path.exists()` (`footprints.py:485`), which is case-insensitive on Windows, the project's stated primary and currently-only-supported platform. A rename candidate differing only by case from an untouched, unlinked, pre-existing model file therefore sails past the guard, and the resulting write op's `base_sha256` is silently seeded from the unrelated file's *current* bytes — so the preflight staleness check (which exists specifically to prevent exactly this kind of surprise) passes, and the write proceeds. In this verification's own from-scratch reproduction: `apply_migration` returned `ok=True` with only a `migration.done` SUCCESS issue, and an untouched `TAKEN.STEP` model's original content was gone, replaced by a different, unrelated part's model bytes. Nothing in the run's own reporting reveals this — there is no failure to roll back from, because no failure is ever detected.

This is the same failure *shape* as the original CR-01 (a "successful" migration that silently destroys a part's file), through a different, narrower trigger that the 13-21 gap-closure's own seven new regression tests do not cover (all seven test group-vs-group or added-model-vs-registry collisions; none tests a rename candidate against an untouched, unlinked on-disk model). `13-REVIEW-DISPOSITION.md` records this finding's disposition as `open` as of this verification — no gap-closure plan has yet addressed it.

The fix `13-REVIEW.md` proposes (casefold the guard at `footprints.py:329`, mirroring the already-correct pattern used for the D-15 added-model path's `claimed_model_names` registry) is narrowly scoped and consistent with how the rest of this module already handles case-insensitivity correctly (the footprint-name clash path's `_resolve_clash` is safe because its `known` dict is backed by a real `Path.exists()` check rather than a frozen snapshot). It should ship with the regression test `13-REVIEW.md` IN-01 and this verification both independently call for: an untouched, unlinked model file colliding case-insensitively with a rename candidate.

---

*Verified: 2026-11-12T11:40:00Z*
*Verifier: Claude (gsd-verifier)*
