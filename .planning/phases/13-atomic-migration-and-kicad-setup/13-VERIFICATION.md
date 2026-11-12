---
phase: 13-atomic-migration-and-kicad-setup
verified: 2026-11-12T07:16:36Z
status: gaps_found
score: 4/5 must-haves verified
covered_files: [".planning/PROJECT.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-01-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-01-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-02-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-02-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-03-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-03-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-04-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-04-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-05-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-05-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-06-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-06-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-07-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-07-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-08-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-08-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-09-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-09-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-10-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-10-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-11-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-11-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-12-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-12-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-13-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-13-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-14-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-14-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-15-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-15-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-16-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-16-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-17-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-17-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-18-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-18-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-19-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-19-SUMMARY.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-20-PLAN.md", ".planning/phases/13-atomic-migration-and-kicad-setup/13-20-SUMMARY.md", ".planning/research/LIBRARY-NAMING.md", "CLAUDE.md", "kicad_lib_manager/gitops.py", "kicad_lib_manager/importer/commit_gate.py", "kicad_lib_manager/importer/commit_plan.py", "kicad_lib_manager/importer/commit_step.py", "kicad_lib_manager/importer/form.py", "kicad_lib_manager/importer/migration/__init__.py", "kicad_lib_manager/importer/migration/applier.py", "kicad_lib_manager/importer/migration/commitplan.py", "kicad_lib_manager/importer/migration/draft.py", "kicad_lib_manager/importer/migration/families.py", "kicad_lib_manager/importer/migration/footprints.py", "kicad_lib_manager/importer/migration/gate.py", "kicad_lib_manager/importer/migration/inventory.py", "kicad_lib_manager/importer/migration/mapfile.py", "kicad_lib_manager/importer/migration/plan.py", "kicad_lib_manager/importer/migration/planner.py", "kicad_lib_manager/importer/migration/precheck.py", "kicad_lib_manager/importer/migration/symbols.py", "kicad_lib_manager/importer/planner.py", "kicad_lib_manager/kicad_setup.py", "kicad_lib_manager/main_window.py", "kicad_lib_manager/settings.py", "kicad_lib_manager/table_generator.py", "kicad_lib_manager/widgets/commit_panel.py", "kicad_lib_manager/widgets/help_dialog.py", "kicad_lib_manager/widgets/import_dialog.py", "kicad_lib_manager/widgets/import_result.py", "kicad_lib_manager/widgets/migration_dialog.py", "tests/README.md", "tests/migrationfixtures.py", "tests/test_checkout_check.py", "tests/test_checkout_warning.py", "tests/test_commit_deletions.py", "tests/test_commit_panel.py", "tests/test_commit_plan.py", "tests/test_docs_atomic.py", "tests/test_gitops.py", "tests/test_help_dialog.py", "tests/test_importer_layering.py", "tests/test_kicad_setup.py", "tests/test_layering.py", "tests/test_main_window.py", "tests/test_main_window_chooser.py", "tests/test_main_window_import.py", "tests/test_main_window_migration.py", "tests/test_migration_apply.py", "tests/test_migration_commit.py", "tests/test_migration_dialog.py", "tests/test_migration_dialog_files.py", "tests/test_migration_dialog_run.py", "tests/test_migration_draft.py", "tests/test_migration_e2e.py", "tests/test_migration_families.py", "tests/test_migration_footprints.py", "tests/test_migration_full.py", "tests/test_migration_gate.py", "tests/test_migration_inventory.py", "tests/test_migration_map.py", "tests/test_migration_precheck.py", "tests/test_migration_symbols.py", "tests/test_table_add_entries.py", "tests/test_table_descriptions.py", "tests/test_table_merge.py"]
covered_digest: "v3:sha256:48e5b359de3ccc1dc3365a371e9cb640351ad326b889c13767ec1b489f3e16d3"
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Running the migration as one transaction with rollback never silently destroys a part's data — every operation that would overwrite another part's file is caught as a blocking issue before Run (ROADMAP SC2; MIG-02 'every atomic-rule failure with an edit box'; MIG-03 'rewrites every Footprint field and model path')"
    status: failed
    reason: >
      Confirmed by direct code reading (not just trusting 13-REVIEW.md's CR-01 claim): in
      kicad_lib_manager/importer/migration/footprints.py, `model_name_set` (line 314) is a frozen
      snapshot of the pre-migration inventory of 3D model file names, taken once before the
      per-old-model-name rename loop (lines 377-402). The loop checks each candidate new name
      against that frozen snapshot but never adds a newly chosen candidate back into it. Two
      different footprints' model-rename groups within the SAME migration run can therefore both
      resolve to the same candidate file name (triggered directly whenever two parts share an
      owner-typed MPN or `model_name` override that is not deduplicated the way default MPNs are
      in `part_mpns`). The planner then queues two independent `MigrationOp("write", new_path, ...)`
      entries for the same `new_path` with two different models' bytes, followed by two
      `MigrationOp("delete", old_path, ...)` entries (lines 404-416) — with no Conflict/Issue raised,
      unlike the footprint-name clash path (`_resolve_clash`) which does track every name claimed so
      far and blocks Run on a collision. `applier.py`'s three safety nets cannot catch it either,
      because all three key off `op.path`/`op.rel`, which the two colliding ops share by construction:
      `_preflight`'s `writes = {...}` dict comprehension (line 225) silently keeps only the last op
      for a duplicate key; `_still_fresh` (335-360) re-checks the second write's freshness against
      disk content the FIRST write of the same transaction just wrote a moment earlier, so it passes;
      `_verify` (413-434) builds `by_rel = {op.rel: op for op in plan.ops}`, which likewise collapses
      the two colliding ops to one and never notices the first model's bytes are gone. End state: one
      3D model's geometry is permanently deleted, `result.ok` is `True`, and the next atomic-rule scan
      reports zero violations (model-content identity is not part of the atomic rule), so nothing in
      the run's own reporting reveals the loss. This is the opposite of "reversible": the transaction
      "succeeds" while quietly destroying a part's file. No regression test exercises or guards this
      path (tests/test_migration_footprints.py and tests/test_migration_apply.py were run directly
      during this verification and both pass, but neither constructs the two-groups-same-candidate
      scenario). Disposition in 13-REVIEW-DISPOSITION.md is `open` (unresolved) as of this
      verification.
    artifacts:
      - path: "kicad_lib_manager/importer/migration/footprints.py"
        issue: "model_name_set (line 314) never grows with candidates chosen in the same loop (lines 377-402, 404-416); no cross-group collision check or blocking Issue/Conflict, unlike the footprint-name clash path"
      - path: "kicad_lib_manager/importer/migration/applier.py"
        issue: "_preflight (line 225), _still_fresh (335-360) and _verify (413-434) all key off op.path/op.rel, which two colliding write ops share, so none of the three safety nets can detect or block the collision"
    missing:
      - "Seed a mutable set from model_name_set and grow it with every chosen candidate as the rename loop runs (the same pattern _resolve_clash already uses for footprint names), raising a blocking Issue/Conflict the owner must resolve before Run when two groups would resolve to the same candidate — per the fix already proposed in 13-REVIEW.md CR-01"
      - "A regression test that builds two footprints whose models resolve to the same candidate name within one migration run, asserting Run is blocked (or at minimum that no data is lost)"
human_verification:
  - test: "Run the full migration end to end from the main checkout (C:/Git_Repo_Clones/Kicad_Libraries) against the real Custom/ submodule and a real KiCad 10 install, per the UAT check list in 13-18-SUMMARY.md (coverage item D6)"
    expected: "Preview shows every real part and passes; Run completes as one transaction; the post-migration scan reports zero atomic violations; Generate Tables and Set Up KiCad Chooser behave as documented; the Custom + parent-ref commits are made"
    why_human: "This is a live run against the owner's real Custom/ submodule and real KiCad 10 settings; no automated test may touch that live data (13-18-SUMMARY.md explicitly marks this human_judgment: true, coverage D6), and the orchestrator's instructions forbid verification from touching the Custom submodule"
---

# Phase 13: Atomic Migration and KiCad Setup Verification Report

**Phase Goal:** All existing `Custom/` parts move to the `Atomic_` scheme in one previewed, reversible commit, with every part passing the atomic rule, and KiCad's library list and chooser show the new libraries
**Verified:** 2026-11-12T07:16:36Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Migration refuses to start while `Custom` has uncommitted changes; tags `pre-atomic` before writing; preview shows target library, footprint destination, every rename/field change and every atomic-rule failure with an edit box; Run disabled until every part passes | ✓ VERIFIED | `precheck.check_custom`/`ensure_tag` (precheck.py:60,123); `migration_dialog.py` refusal page, part list, detail pane, failure strip; `tests/test_migration_precheck.py` (12 passed), `tests/test_migration_dialog.py` (part of 64 passed), `tests/test_migration_gate.py` (part of 23 passed) all run green during this verification |
| 2 | One transaction with rollback leaves no v1-named library; every footprint moved to `Atomic_Footprints`/official; every Footprint field and model path rewritten; every `.bak` gone; next scan reports zero atomic violations | ✗ FAILED | `applier.apply_migration` does roll back correctly on a *detected* failure (`tests/test_migration_apply.py`, `tests/test_migration_full.py` pass), but CR-01 (confirmed by direct code read, see Gaps) lets two colliding 3D-model renames within one run silently destroy one model's data with **no failure reported** — the transaction "succeeds" and the scan still reports zero violations because model-content identity isn't checked by the atomic rule |
| 3 | Regenerated tables drop old names, add new ones with non-empty descriptions; one `Custom` commit plus a parent ref commit offered through the commit step | ✓ VERIFIED | `table_generator.library_description`/`stock_descriptions` (table_generator.py:29,51) wired via `main_window._stock_descriptions` (main_window.py:1577) into `write_tables`/`add_library_entries`; `commitplan.build_migration_commit_plan` (commitplan.py); `tests/test_table_descriptions.py` (38 passed), `tests/test_migration_commit.py` (part of 23 passed) |
| 4 | One confirmed action sets up KiCad 10's chooser: pins `Atomic_` libraries, adds MPN/Manufacturer columns, removes stray MANUFACTURER, shows old→new first, backs up config, refuses from a worktree/other checkout | ✓ VERIFIED | `kicad_setup.sync_kicad_chooser`, `checkout_mismatch`, `wrong_checkout_refusal` (kicad_setup.py); menu wiring `main_window._on_setup_chooser`; `tests/test_kicad_setup.py` (part of 38 passed), `tests/test_main_window_chooser.py` (21 passed) |
| 5 | App shows/saves old→new library map plus KiCad relink steps; `CLAUDE.md`, PROJECT.md and `research/LIBRARY-NAMING.md` describe the `Atomic_` scheme and atomic rule | ✓ VERIFIED | `mapfile.map_text`, `RELINK_STEPS` (mapfile.py:18-22); CLAUDE.md lines 28-90 describe the scheme, menu actions and D-26 wording; `.planning/research/LIBRARY-NAMING.md` update note; `tests/test_docs_atomic.py` (15 passed), `tests/test_migration_map.py` (part of 71 passed) |

**Score:** 4/5 truths verified (1 failed — CR-01 data-loss defect)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kicad_lib_manager/table_generator.py` | `library_description`, `stock_descriptions`, `_entry_text` with description, `stock=` threading | ✓ VERIFIED | Present, substantive (598 lines), wired into `main_window.py` and the commit/Generate paths |
| `kicad_lib_manager/kicad_setup.py` | `ChooserChange`, `plan_pins`, `plan_columns`, `sync_kicad_chooser`, `checkout_mismatch` | ✓ VERIFIED | Present (633 lines), wired into `main_window._on_setup_chooser` and `migration_dialog.py` Result view |
| `kicad_lib_manager/gitops.py` | `"tag"` subcommand, `create_tag` | ✓ VERIFIED | `ALLOWED_SUBCOMMANDS` includes `"tag"` (line 24); `create_tag` (line 362) |
| `kicad_lib_manager/importer/migration/precheck.py` | `PRE_ATOMIC_TAG`, `check_custom`, `ensure_tag` | ✓ VERIFIED | Present (158 lines); wired as `before_first_write` callback in `applier.py` and `migration_dialog.py` |
| `kicad_lib_manager/importer/migration/plan.py` | frozen dataclasses of the migration contract | ✓ VERIFIED | Present (155 lines) |
| `kicad_lib_manager/importer/migration/inventory.py` | `Inventory`, `read_inventory`, `migration_reason` | ✓ VERIFIED | Present (308 lines); `migration_reason` wired into `main_window._act_migrate` enable rule |
| `kicad_lib_manager/importer/migration/planner.py` | `build_migration_plan` orchestration | ✓ VERIFIED | Present (141 lines) |
| `kicad_lib_manager/importer/migration/symbols.py` | symbol targeting, MPN, rename, field, keyword, clash rules | ✓ VERIFIED | Present (665 lines); `tests/test_migration_symbols.py` passes (part of 71 passed) |
| `kicad_lib_manager/importer/migration/footprints.py` | footprint/model move, clash, official-switch, multi-model, leftovers | ⚠️ VERIFIED (with defect) | Present (681 lines), wired, tested — but contains CR-01 (see Gaps): the model-rename cross-group collision is not caught |
| `kicad_lib_manager/importer/migration/families.py` | `find_families`, `derived_edits` | ✓ VERIFIED | Present (176 lines); `tests/test_migration_families.py` passes (part of 71 passed) |
| `kicad_lib_manager/importer/migration/gate.py` | complete `check_plan` with strip lines | ✓ VERIFIED | Present (222 lines); `tests/test_migration_gate.py` passes (part of 23 passed) |
| `kicad_lib_manager/importer/migration/mapfile.py` | complete `map_text` | ✓ VERIFIED | Present (86 lines); `tests/test_migration_map.py` passes |
| `kicad_lib_manager/importer/migration/applier.py` | transactional apply with rollback | ✓ VERIFIED (for detected failures) | Present (544 lines); rollback on a *detected* failure confirmed by `tests/test_migration_apply.py`; does not detect CR-01's silent collision (see Gaps) |
| `kicad_lib_manager/importer/migration/draft.py` | draft save/load/changed-since-draft | ✓ VERIFIED | Present (290 lines); `tests/test_migration_draft.py` passes (part of 71 passed) |
| `kicad_lib_manager/importer/migration/commitplan.py` | `build_migration_commit_plan` | ✓ VERIFIED | Present (107 lines); `tests/test_migration_commit.py` passes |
| `kicad_lib_manager/widgets/migration_dialog.py` | full migration window (refusal, list, detail, strip, Run, Result, commit) | ✓ VERIFIED | Present (1758 lines); `tests/test_migration_dialog*.py` (64 passed) |
| `kicad_lib_manager/main_window.py` | `_act_migrate`, `_act_setup_chooser`, rescan/select-after-Run, checkout banner | ✓ VERIFIED | Present (1817 lines); wiring confirmed by grep and `tests/test_main_window_migration.py` (21 passed) |
| `CLAUDE.md` | Atomic_ scheme, SnapEDA/import steps, GUI Behavior, Menu Shortcuts | ✓ VERIFIED | Confirmed by direct read (lines 28-90) |
| `.planning/research/LIBRARY-NAMING.md` | update note, refreshed section 5 | ✓ VERIFIED | Present (287 lines) |
| `tests/test_docs_atomic.py` | docs-consistency checks | ✓ VERIFIED | Present, 15 tests pass |
| `tests/test_migration_full.py` | whole-fixture end-to-end migration | ✓ VERIFIED | Present, 1 test passes (71.5s against real git) |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `main_window._on_generate` | `table_generator.write_tables` | `stock=self._stock_descriptions()` | ✓ WIRED (grep-confirmed, lines 1014, 1039, 1648) |
| `main_window._on_setup_chooser` | `kicad_setup.sync_kicad_chooser` | confirm + write flow | ✓ WIRED (`tests/test_main_window_chooser.py` passes) |
| `precheck.check_custom`/`ensure_tag` | `gitops.status_entries`/`create_tag` | clean check and tag creation | ✓ WIRED (`tests/test_migration_precheck.py` passes against real git) |
| `applier.apply_migration` | `precheck.ensure_tag` | `before_first_write` callback | ✓ WIRED (grep-confirmed in applier.py:461 and migration_dialog.py:1586-1590) |
| `migration_dialog.py` Result view | `commitplan.build_migration_commit_plan` | `_CommitStepHost` | ✓ WIRED (`tests/test_migration_dialog_run.py` passes) |
| `main_window._act_migrate` | `inventory.migration_reason` | `_refresh_migrate_action` after each scan | ✓ WIRED (`tests/test_main_window_migration.py` passes) |
| `migration_dialog.py` Generate/Chooser buttons | `main_window._on_migration_generate`/`_on_setup_chooser` | signal connections | ✓ WIRED (grep-confirmed; `tests/test_main_window_migration.py` passes) |
| `footprints.plan_footprints` (model rename) | `applier.apply_migration` (preflight/freshness/verify) | `MigrationOp` write/delete pairs | ⚠️ WIRED BUT UNSAFE — see Gaps (CR-01): the link exists and runs, but the receiving safety checks cannot detect a same-run collision because all three key off `op.path`/`op.rel` |

### Behavioral Spot-Checks / Targeted Test Runs

Full workspace suite was not re-run per orchestrator constraint (memory-limited, ~30 min); targeted single/few-file `pytest` runs were executed directly in this verification session instead (no reliance on SUMMARY-claimed counts):

| Test file(s) | Result |
|---|---|
| `tests/test_migration_footprints.py` | 15 passed |
| `tests/test_docs_atomic.py`, `tests/test_table_descriptions.py`, `tests/test_kicad_setup.py` | 38 passed |
| `tests/test_migration_full.py` | 1 passed (71.5s, real git) |
| `tests/test_migration_apply.py`, `tests/test_migration_gate.py`, `tests/test_migration_commit.py` | 23 passed |
| `tests/test_migration_symbols.py`, `tests/test_migration_families.py`, `tests/test_migration_draft.py`, `tests/test_migration_inventory.py`, `tests/test_migration_precheck.py`, `tests/test_migration_map.py` | 71 passed |
| `tests/test_main_window_migration.py`, `tests/test_main_window_chooser.py`, `tests/test_checkout_warning.py` | 21 passed |
| `tests/test_migration_dialog.py`, `tests/test_migration_dialog_files.py`, `tests/test_migration_dialog_run.py`, `tests/test_importer_layering.py`, `tests/test_layering.py` | 64 passed |

All targeted runs green. None of these tests constructs the CR-01 two-colliding-model-names scenario, consistent with the code review's finding that it is an untested gap, not a regression.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| TBL-01 | 13-01, 13-17, 13-19 | Table entries carry a non-empty description | ✓ SATISFIED | `table_generator.library_description`; `tests/test_table_descriptions.py` passes |
| TBL-02 | 13-02, 13-07, 13-18 | One confirmed action sets up KiCad 10's chooser | ✓ SATISFIED | `kicad_setup.sync_kicad_chooser`; `tests/test_kicad_setup.py`, `tests/test_main_window_chooser.py` pass |
| MIG-01 | 13-03, 13-13, 13-14, 13-16, 13-18, 13-20 | Refuses to start with uncommitted changes; tags `pre-atomic` | ✓ SATISFIED | `precheck.check_custom`/`ensure_tag`; `tests/test_migration_precheck.py` passes against real git |
| MIG-02 | 13-05, 13-06, 13-08, 13-09, 13-12, 13-14, 13-17, 13-18 | Preview shows target library, footprint destination, renames, field changes, atomic-rule failures with edit box; Run blocked until all pass | ✓ SATISFIED (for the failure modes the gate models) | `gate.check_plan`, `migration_dialog.py` failure strip; `tests/test_migration_gate.py`, `tests/test_migration_dialog.py` pass — but see MIG-03 note: one failure mode (model-name collision) is never modeled as a gate Issue, so MIG-02's "every atomic-rule failure" promise has a real gap |
| MIG-03 | 13-05, 13-06, 13-09, 13-10, 13-13, 13-15, 13-16, 13-18, 13-20 | One transaction with rollback; moves every part/footprint; rewrites every Footprint field and model path | ✗ BLOCKED | CR-01: silent 3D-model collision bypasses rollback entirely because no failure is ever detected (see Gaps) |
| MIG-04 | 13-04, 13-12, 13-13, 13-17, 13-18, 13-19, 13-20 | Post-migration scan reports zero violations; tables regenerated; commit offered | ✓ SATISFIED | `tests/test_migration_full.py` (whole-fixture, real git) passes; note zero-violations is a necessary but not sufficient signal given CR-01 (model-content identity isn't checked by the atomic rule) |
| MIG-05 | 13-06, 13-12, 13-13, 13-16, 13-18, 13-20 | Shows/saves old→new map and relink steps | ✓ SATISFIED | `mapfile.map_text`; `tests/test_migration_map.py` passes |
| DOC-01 | 13-18 | CLAUDE.md, PROJECT.md, LIBRARY-NAMING.md describe the Atomic_ scheme | ✓ SATISFIED | Confirmed by direct read of CLAUDE.md; `tests/test_docs_atomic.py` passes |

No orphaned requirements: all 8 IDs assigned to Phase 13 in REQUIREMENTS.md (TBL-01, TBL-02, MIG-01..05, DOC-01) are claimed by at least one of the phase's 20 plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `kicad_lib_manager/importer/migration/footprints.py` | 314, 377-402, 404-416 | Stale membership-check snapshot used across a mutating loop without being grown (same defect class as a TOCTOU bug, confirmed by direct code read) | 🛑 Blocker | Silent data loss on Run; no Issue/Conflict/rollback; "reversible" and "every part passing" promises both violated for this failure mode |
| `kicad_lib_manager/widgets/migration_dialog.py` | 322-323, 338, 373 | `CommitPlan`/`CommitProbe` annotated but never imported (WR-01, open) | ⚠️ Warning | Static-analysis blind spot only; no runtime effect (annotations on `self.x` inside a method body aren't evaluated by CPython) |
| `kicad_lib_manager/widgets/commit_panel.py` | 591-597 | Deleted-row early return skips the dirty-marker check (WR-02, open) | ⚠️ Warning | Currently unreachable given the precheck's clean-Custom invariant; a future looser caller could hit it |
| `kicad_lib_manager/main_window.py` | 1276 | Unused `result` parameter in `_on_migrated` (IN-01, open) | ℹ️ Info | Cosmetic only |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any phase-covered source file (grep across all `importer/migration/*`, `kicad_setup.py`, `table_generator.py`, `migration_dialog.py`, `main_window.py`, `gitops.py`).

### Human Verification Required

### 1. Owner's live migration UAT (main checkout, real Custom/, real KiCad 10)

**Test:** Run the full migration end to end from the main checkout (`C:/Git_Repo_Clones/Kicad_Libraries`, not this worktree) against the real `Custom/` submodule and a real KiCad 10 install, following the UAT check list referenced in `13-18-SUMMARY.md` (coverage item D6).
**Expected:** Preview shows every real part and passes; Run completes as one transaction; the post-migration scan reports zero atomic violations; Generate Tables and Set Up KiCad Chooser behave as documented; the `Custom` + parent-ref commits are made; KiCad's chooser shows the new `Atomic_` libraries pinned.
**Why human:** This is a live run against the owner's real `Custom/` submodule and real KiCad 10 settings. `13-18-SUMMARY.md` explicitly marks this item `human_judgment: true` (coverage D6) because no automated test may touch that live data, and this verification's own instructions forbid touching the `Custom` submodule. Given CR-01 (below), the owner should specifically watch for any typed MPN or 3D-model-name override shared between two different parts during this live run, since that is the exact trigger condition for the undetected data-loss defect.

### Gaps Summary

The phase delivers a large, well-tested, carefully-defended migration subsystem: 4 of 5 ROADMAP success criteria are fully verified against the actual codebase (table descriptions, KiCad chooser setup, the saved library map and relink steps, and the project documentation), all 8 requirement IDs are claimed and satisfied by at least one plan, every declared artifact exists and is substantively wired, and 233 targeted tests run directly in this verification session (not merely cited from a SUMMARY) all pass, including the slow real-git whole-fixture end-to-end test (`test_migration_full.py`).

The one blocking gap is CR-01, a critical, **unresolved** (disposition `open` in `13-REVIEW-DISPOSITION.md`) defect in `kicad_lib_manager/importer/migration/footprints.py`'s 3D-model rename pass, confirmed here by direct reading of the current code (not merely trusting the review's prose): a frozen snapshot of pre-migration model names is checked but never grown as the same run assigns new candidate names, so two unrelated footprints' models can resolve to the same final file name within one migration transaction. Nothing in `applier.py`'s preflight, freshness, or verify checks can catch this, because all three key off the op's own path — which the two colliding operations share by construction. The result is a transaction that reports success (`result.ok == True`) and a post-migration scan that reports zero atomic violations, while one part's 3D model file has been permanently and silently overwritten and deleted. This directly contradicts the phase goal's "reversible" promise (there is no failure to roll back from — the loss is baked into a "successful" commit) and MIG-03's "rewrites every Footprint field and model path" / MIG-02's "every atomic-rule failure with an edit box" guarantees, since this specific failure mode never surfaces as an edit-box line at all. No existing test (verified directly in this session) constructs the colliding-name scenario, so nothing currently guards against a recurrence.

The fix proposed in `13-REVIEW.md` (grow a mutable claimed-names set across the rename loop, mirroring the pattern `_resolve_clash` already uses for footprint names, and raise a blocking Issue/Conflict on collision) is concrete and scoped to `footprints.py`'s model-rename section; it should come with a regression test that constructs two parts whose models resolve to the same candidate name in one run.

---

*Verified: 2026-11-12T07:16:36Z*
*Verifier: Claude (gsd-verifier)*
