---
phase: 04-plan-and-install-core
verified: 2026-10-20T13:00:00Z
status: human_needed
score: 7/7 must-haves verified
covered_files:
  - .planning/phases/04-plan-and-install-core/04-01-PLAN.md
  - .planning/phases/04-plan-and-install-core/04-01-SUMMARY.md
  - .planning/phases/04-plan-and-install-core/04-02-PLAN.md
  - .planning/phases/04-plan-and-install-core/04-02-SUMMARY.md
  - .planning/phases/04-plan-and-install-core/04-03-PLAN.md
  - .planning/phases/04-plan-and-install-core/04-03-SUMMARY.md
  - .planning/phases/04-plan-and-install-core/04-04-PLAN.md
  - .planning/phases/04-plan-and-install-core/04-04-SUMMARY.md
  - .planning/phases/04-plan-and-install-core/04-05-PLAN.md
  - .planning/phases/04-plan-and-install-core/04-05-SUMMARY.md
  - .planning/phases/04-plan-and-install-core/04-06-PLAN.md
  - .planning/phases/04-plan-and-install-core/04-06-SUMMARY.md
  - .planning/phases/04-plan-and-install-core/04-07-PLAN.md
  - .planning/phases/04-plan-and-install-core/04-07-SUMMARY.md
  - .planning/phases/04-plan-and-install-core/04-08-PLAN.md
  - .planning/phases/04-plan-and-install-core/04-08-SUMMARY.md
  - .planning/phases/04-plan-and-install-core/04-09-PLAN.md
  - .planning/phases/04-plan-and-install-core/04-09-SUMMARY.md
  - .planning/phases/04-plan-and-install-core/04-10-PLAN.md
  - .planning/phases/04-plan-and-install-core/04-10-SUMMARY.md
  - .planning/phases/04-plan-and-install-core/04-11-PLAN.md
  - .planning/phases/04-plan-and-install-core/04-11-SUMMARY.md
  - .planning/phases/04-plan-and-install-core/04-12-PLAN.md
  - .planning/phases/04-plan-and-install-core/04-12-SUMMARY.md
  - .planning/phases/04-plan-and-install-core/04-13-PLAN.md
  - .planning/phases/04-plan-and-install-core/04-13-SUMMARY.md
  - kicad_lib_manager/importer/applier.py
  - kicad_lib_manager/importer/candidate.py
  - kicad_lib_manager/importer/detect.py
  - kicad_lib_manager/importer/kicad_cli.py
  - kicad_lib_manager/importer/plan.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/verify.py
  - kicad_lib_manager/kicad_files.py
  - tests/fakecli.py
  - tests/test_install_apply.py
  - tests/test_install_e2e.py
  - tests/test_install_plan.py
  - tests/test_install_verify.py
covered_digest: "v3:sha256:32a4a57a90df03727944e8b25c2d2dfa336a94cbe033e0eccaa765b5d732e965"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/7
  gaps_closed:
    - "Any failure during an install, not only a returned write Issue, leaves every touched file exactly as it was (CR-01, INST-07)"
    - "A plan whose target changed after the plan was built is refused and never overwritten, including during the kicad-cli gate window (CR-02, stale-plan guarantee)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "KiCad 9 UAT on the scratch install (set KICAD_IMPORT_UAT_DIR, run the opt-in test in tests/test_install_e2e.py, follow the checklist in 04-10-SUMMARY.md)"
    expected: "The library opens without a load error. CSD85301Q2 shows units A and B with Footprint IC_Battery_Charger_TI:DQK0006B and hidden Manufacturer/MPN. DQK0006B shows 8 pads and the STEP sits on the pads. Includes the A6/A7 field-rule judgement (renamed vendor Manufacturer/MPN keep their own visibility; an extends parent receives Footprint, filters and Manufacturer)."
    why_human: "KiCad GUI rendering and a design judgement; no automated oracle exists. kicad-cli load checks pass, but visual correctness of pads and the 3D model position is not observable from a test."
  - test: "KiCad 10 symbol format 20251024 (research assumption A1)"
    expected: "Every 20241209 Custom/ library takes the as-is-with-warning row of the D-01 version table."
    why_human: "KiCad 10 is not installed here, so only kicad-cli 9.0.9 was exercised."
  - test: "Case-sensitive-volume rollback and overwrite branches (case twin written under another spelling)"
    expected: "Rollback restores the original spelling and removes the twin."
    why_human: "Only NTFS is available; the branch is covered with faked directory listings only."
  - test: "Product question from 04-09: a part edited in KiCad shows as a conflict on re-import (accepted D-07 consequence)"
    expected: "Owner confirms this reads correctly in the Phase 5 preview."
    why_human: "UX judgement that belongs to Phase 5."
---

# Phase 4: Plan and Install Core Verification Report

**Phase Goal:** A parsed part installs into `Custom/` correctly and transactionally. The symbol is merged, the footprint and 3D model are placed and linked, failures are rolled back and the result is verified, all testable without a display.
**Verified:** 2026-10-20
**Status:** human_needed
**Re-verification:** Yes, after gap closure (plans 04-11, 04-12, 04-13). Previous status gaps_found, 5/7.

## Summary

Both blockers from the first verification are closed. I re-read `applier.py` as merged and replayed the two original reproductions plus new variants with a probe file of my own. Every probe now ends in the correct outcome. The five previously verified success-criteria truths show no regression. All 13 requirement IDs are accounted for.

What is left is the human-only UAT list (KiCad GUI, KiCad 10, a case-sensitive filesystem, one Phase 5 UX question) and 8 open non-blocking review items. None of them contradicts the goal. Nothing is marked `gaps_found`.

Evidence run by me on the merged tree (HEAD 6e3d03d):

- Full suite `./env/Scripts/python.exe -m pytest -q`: **1345 passed, 5 skipped** in 103 s. The skips are the env-gated UAT test, a Windows symlink privilege, and 3 WurthElektronik submodule-not-checked-out cases.
- `-m kicad_cli` (real kicad-cli 9.0.9): **15 passed**.
- `tests/test_install_apply.py::test_stale_plan_ul_target_edited_during_gate`: passes. This is the test that 04-13 could not run in its worktree.
- `git status --porcelain Custom`: empty, so the real submodule was not touched.
- Own probe file `.../scratchpad/test_reprobe.py` (reads only `tmp_path` trees): **9 passed**.

## Goal Achievement

### Observable Truths

| #   | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| 1 | SC1: UL sample into a copy of `Custom/` adds `CSD85301Q2`; other symbols and header byte-identical; footprint consistent (filename, internal name, value, `Footprint` field, `ki_fp_filters`); STEP copied to `3DModels/`; `${CUSTOM_3DMODEL_DIR}/...` block present | VERIFIED (regression check) | `test_ul_symbol_added_others_identical` and `test_sc1_ul_footprint_model_and_fields` in the 1345-pass run. The plan, apply and write path they cover changed only by the additive transaction wrapper. |
| 2 | SC2: rename follows unit sub-symbols and `extends` refs; a package with no 3D model installs and warns | VERIFIED (regression check) | `test_sc2_rename_follows_sub_symbols` and `test_sc2_no_model_package` pass. |
| 3 | SC3: new library creates a matching `.kicad_sym` + `.pretty/` pair; existing header never changed; kicad-cli normalises the incoming symbol, else merged as-is with a warning | VERIFIED (regression check) | `test_sc3_new_library_pair`, `test_sc3_existing_headers_unchanged`, 15 real kicad-cli tests pass. |
| 4 | SC4: a failure injected on any write leaves every touched file as it was; identical model SHA reused, different one is a conflict | VERIFIED | `test_sc4_fail_on_each_write`, `test_rollback_fail_on_nth_write`, `test_rollback_fail_with_locked_target`, `test_sc4_model_*` pass. |
| 5 | SC5: verification re-parses, resolves `<Lib>:<FP>`, confirms the model; warns on name-elsewhere and pin/pad mismatch; importing twice changes nothing | VERIFIED (regression check) | `test_sc5_*`, `test_second_install_is_noop`, `test_second_install_new_library_is_noop` pass; soft verify warnings are still appended (`applier.py:408-412,429`). |
| 6 | Goal: failures are rolled back, including an unexpected exception anywhere in the transaction (gap 1 / CR-01 / INST-07) | VERIFIED (gap closed) | `apply_plan` (`applier.py:329-343`) wraps `_transaction` in `try/except BaseException`. `_Transaction` (lines 57-69) holds `undo`, `touched` and `backup_dir` outside the writing code, so the guard rolls back whatever was written. An `Exception` becomes `install.unexpected` + `install.rolled_back` and returns an `InstallResult`; `KeyboardInterrupt` and `SystemExit` roll back and re-raise. `_notify` (113-127) absorbs a raising progress callback into one WARNING `install.progress_failed`. `_make_folders` has `resolve()` inside its `try` (437, 446-449). `_rollback` catches `Exception` per step (108-109) and continues. `_rollback_once` prevents a double rollback. My probes: progress raising on every call still gives `ok=True` (new and existing library); `verify_install` raising rolls back to a byte-identical tree for both shapes; a late `Path.resolve` failure inside the mkdir path leaves the tree identical. Repo tests: `test_rollback_unexpected_error_in_a_write`, `..._in_verify`, `..._interrupt_*_is_reraised` (write, verify, progress), `test_unexpected_error_before_any_write`, `test_progress_error_does_not_abort_the_install`, `test_make_folders_resolve_error_is_an_issue`, `test_rollback_step_error_is_reported`. |
| 7 | Goal: transactional against a stale plan, a target changed after planning is never silently overwritten (gap 2 / CR-02) | VERIFIED (gap closed) | Three layers in `applier.py`: (1) after the gate, every no-base op's path is re-checked with `_name_taken` before any backup (367-370); (2) each backup copy is read back and hashed against `op.base_sha256`, a mismatch returns `install.stale_plan` with the live file untouched, and the backed-up bytes become the rollback pre-image (381-396); (3) `_still_fresh` runs immediately before every `atomic_write_bytes` (494-496) and tracks this install's own prior writes through `txn.expected` (501). A refused write adds no undo entry, so rollback never overwrites the other process's file. My probes: a runner that rewrites the `.kicad_sym` during the gate gives `ok=False`, one `install.stale_plan` error, live edit intact (this is the original CR-02 reproduction, now refused); an edit landing between backup read-back and the first write is caught by `_still_fresh` and nothing is written; a target deleted during the gate is refused and not recreated. Repo tests: `test_stale_plan_target_edited_during_gate`, `test_stale_plan_ul_target_edited_during_gate`, `test_stale_plan_created_path_appears_during_gate`, `..._edited_between_writes`, `..._created_path_appears_between_writes`. Residual window: the single `os.replace` inside `fsutil.atomic_write_bytes`, which the code comment states and which cannot be closed in user space. |

**Score:** 7/7 truths verified (0 behavior-unverified; the two gap truths are behavior-dependent and each has a passing behavioral test plus my own probe).

### Deferred Items

None. Phase 5 to 7 goals do not cover the 8 open review items below.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `kicad_lib_manager/importer/plan.py` | Frozen plan contract, FileOp, InstallResult, InstallOptions | VERIFIED | `InstallOptions.__post_init__` (lines 66-69) turns blank text overrides into `None` (WR-05 fix). |
| `kicad_lib_manager/importer/planner.py` | `build_plan`: versions, rename, conflicts, no-op | VERIFIED (maintainability warning WR-04) | Wired to applier through the plan. |
| `kicad_lib_manager/importer/applier.py` (506 lines) | Transactional apply: gate, backup, rollback, prune | VERIFIED | Exception safe and TOCTOU-guarded as shown above. Called from tests; Phase 5 will call it. |
| `kicad_lib_manager/importer/detect.py`, `candidate.py` | `Package.issues` folded into the candidate | VERIFIED for the found-candidate path | Line 58-59 folds and de-duplicates. The no-candidate path is WR-06 (open, warning). |
| `kicad_lib_manager/importer/verify.py` | D-18 hard checks, POST-03/04 warnings | VERIFIED | Called from `_transaction`. |
| `kicad_lib_manager/importer/kicad_cli.py` | locate/run/upgrade/load_gate | VERIFIED | 15 real-CLI tests pass. |
| `kicad_lib_manager/kicad_files.py` write side | install unit, rename, replace/insert, model edits | VERIFIED | `tests/test_kicad_files_write.py` in the full run. |
| `tests/fakecli.py` | `on_call` hook for mid-gate changes | VERIFIED | Used by the 04-13 stale tests. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `apply_plan` | `_transaction` + `_rollback_once` | `try/except BaseException` | WIRED | Rollback now reachable on any raised exception. |
| `_transaction` | `_notify` | progress callback per op | WIRED | A raising callback is dropped and noted once. |
| `_transaction` | `kicad_cli.load_gate` | `_gate()` before first backup/write | WIRED | Post-gate re-check added. |
| `_transaction` | backup copy hash | `hashlib.sha256(copy)` vs `op.base_sha256` | WIRED | Pre-image taken from the copy. |
| `_write` | `_still_fresh` | before `fsutil.atomic_write_bytes` | WIRED | Uses `txn.expected`. |
| `_transaction` | `verify.verify_install` | after writes | WIRED | ERRORs roll back, WARNINGs returned. |
| `_transaction` | `prune_install_backups(exclude=backup_dir)` | housekeeping | WIRED | Running backup folder never pruned (WR-01). |
| `detect_candidate` | `ImportCandidate.issues` | `replace(candidate, issues=...)` | WIRED (found path only) | WR-06 for the no-candidate path. |

### Data-Flow Trace (Level 4)

No UI in this phase. Equivalent trace: installed bytes come from staged, hash-checked vendor files (`_preflight` source re-hash), and the e2e tests read the written `Footprint` field, filter and model path back from disk. Real data flows end to end.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full suite | `./env/Scripts/python.exe -m pytest -q` | 1345 passed, 5 skipped | PASS |
| Real kicad-cli | `... -m kicad_cli` | 15 passed | PASS |
| UL mid-gate edit | `pytest tests/test_install_apply.py::test_stale_plan_ul_target_edited_during_gate` | 1 passed | PASS |
| Real `Custom/` untouched | `git status --porcelain Custom` | empty | PASS |
| CR-01: progress raises at every call | own probe, new and existing library | `ok=True`, install completes | PASS |
| CR-01: `verify_install` raises | own probe, both shapes | `install.unexpected`, tree byte-identical | PASS |
| CR-01: folder `resolve()` raises late | own probe | `ok=False`, tree byte-identical | PASS |
| CR-02: gate runner rewrites the target | own probe | `ok=False`, one `install.stale_plan`, edit intact | PASS |
| CR-02: edit after backup, before first write | own probe (patched `prune_install_backups`) | `ok=False`, model not written, edit intact | PASS |
| CR-02: target deleted during gate | own probe | `ok=False`, not recreated | PASS |
| Happy path still works | own probe | `ok=True`, 3 files touched | PASS |

Probe file: `C:/Users/sylvain/AppData/Local/Temp/claude/c--Git-Repo-Clones-Kicad-Libraries-importer/53df746d-7e1a-45ca-b0e2-f61d662a0b18/scratchpad/test_reprobe.py`.

### Probe Execution

SKIPPED (no `scripts/*/tests/probe-*.sh` declared by any plan).

### Requirements Coverage

All 13 IDs appear in plan frontmatter and in REQUIREMENTS.md; none is orphaned. REQUIREMENTS.md maps no other ID to Phase 4. INST-07 now has 04-07, 04-10, 04-11, 04-13; INST-08 has 04-01, 04-05, 04-07, 04-10, 04-11, 04-13.

| Requirement | Source Plans | Description | Status | Evidence |
| ----------- | ------------ | ----------- | ------ | -------- |
| INST-01 | 04-01, 04-04, 04-10, 04-13 | Symbol added without altering others/header | SATISFIED | Truth 1 |
| INST-02 | 04-02, 04-04, 04-08, 04-10, 04-13 | Rename follows sub-symbols and `extends` | SATISFIED | Truth 2 |
| INST-03 | 04-01, 04-04, 04-08, 04-10, 04-13 | Footprint name/value/field/filters consistent | SATISFIED | Truth 1 |
| INST-04 | 04-01, 04-07, 04-09, 04-10, 04-12, 04-13 | Model as `<MPN>.<ext>`, same SHA reused, different is conflict; blank MPN keeps vendor value | SATISFIED | Truth 4, `test_blank_options_mean_not_set` |
| INST-05 | 04-01, 04-02, 04-04, 04-10, 04-13 | Model path rewrite/insert | SATISFIED | Truth 1 |
| INST-06 | 04-02, 04-03, 04-06, 04-10, 04-13 | Normalise with kicad-cli, else as-is with warning | SATISFIED | Truth 3; KiCad 10 untested (human item 2) |
| INST-07 | 04-07, 04-10, 04-11, 04-13 | Any write failure restores every touched file, failure logged | SATISFIED | Truths 4, 6, 7 |
| INST-08 | 04-01, 04-05, 04-07, 04-10, 04-11, 04-13 | Result verified | SATISFIED | Truth 5 |
| INST-09 | 04-09, 04-10, 04-13 | Second identical import changes nothing | SATISFIED | Truth 5 |
| INTK-08 | 04-08, 04-10, 04-12, 04-13 | No-model package installs and warns | SATISFIED | Truth 2; package issues now reach the result on the found path |
| LIB-02 | 04-06, 04-10, 04-13 | Create new library pair | SATISFIED | Truth 3; WR-02 is a late-failure edge with clean rollback |
| POST-03 | 04-05, 04-10, 04-13 | Warn if part name exists elsewhere | SATISFIED | Truth 5 |
| POST-04 | 04-02, 04-05, 04-10, 04-13 | Warn on pin/pad mismatch | SATISFIED | Truth 5 |

**Bookkeeping for the orchestrator:** `.planning/REQUIREMENTS.md` rows 154-177 still read `Gaps Found` for all 13 IDs (reverted in commit 7921587). They are now supportable as complete once the human UAT is accepted or waived. I did not edit REQUIREMENTS.md.

### Anti-Patterns Found

TBD/FIXME/XXX scan over the modified importer files and `tests/fakecli.py`: no matches. No stubs or hollow props.

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `kicad_lib_manager/importer/detect.py` | 22-46 | When `locate` finds nothing, `package.issues` (for example `intake.depth_limit`) are not in the returned list or any object (WR-06, confirmed by reading the code) | WARNING | A Phase 5 caller sees "nothing found" with no explanation; the Phase 3 WR-05 symptom on the no-candidate path. Does not affect any Phase 4 success criterion. |
| `kicad_lib_manager/importer/planner.py` | 1070-1080 | No `mkdir` for a missing `Custom/Symbols/` (WR-02) | WARNING | Late failure with clean rollback |
| `kicad_lib_manager/importer/planner.py` | 585-1113 | 528-line `build_plan` (WR-04) | WARNING | Maintainability only |
| `kicad_lib_manager/importer/applier.py` | 326-327 | No-op claim not re-checked against disk (IN-01) | INFO | No data at risk |
| `kicad_lib_manager/importer/applier.py` | 378-395 | Early aborts after the backup folder exists leave it unpruned and one return omits `backup_dir` (IN-05) | INFO | No data at risk |
| `kicad_lib_manager/importer/plan.py` | 38-69 | Blank rule covers 5 fields; `footprint_names={"FP": ""}`, `model=""`, `symbol=""` and stray spaces not handled (IN-04) | INFO | Refusal rather than data loss; Phase 5 form should normalise |
| several | - | Duplicated `_err`/`_listing`, UAT test `rmtree` guard (IN-02, IN-03) | INFO | Cosmetic / opt-in only |

Review disposition: CR-01, CR-02, WR-01, WR-03, WR-05 are `fixed`; 8 are `open` (WR-02, WR-04, WR-06, IN-01 to IN-05). No critical findings remain. The open items are triaged as non-blocking for the Phase 4 goal. WR-06 and IN-04 are worth handing to Phase 5 planning because they bite at the caller and form boundary.

### SUMMARY claims vs. code

- 04-11, 04-12 and 04-13 claims were each checked against `applier.py`, `plan.py` and `detect.py` and held. 04-13 stated it could not run `test_stale_plan_ul_target_edited_during_gate` in its worktree; I ran it on the merged tree and it passes.
- 04-11 recorded "Accepted limitation (T-04-40)": a `KeyboardInterrupt` landing inside `_rollback` itself stops the restore part-way. This is documented in the code (lines 130-134), the pre-images stay in the backup folder, and I accept it as a design decision rather than a gap.

### Human Verification Required

The four items in the frontmatter remain for the owner. They are UAT and environment items that were already recorded before the gap closure and do not indicate a code defect.

1. **KiCad 9 UAT on the scratch install.** Set `KICAD_IMPORT_UAT_DIR`, run the opt-in e2e test, follow the 04-10-SUMMARY checklist. Expected: library opens cleanly, `CSD85301Q2` shows units A and B with the right Footprint field, `DQK0006B` has 8 pads with the STEP on the pads. Why human: GUI rendering and a field-visibility judgement.
2. **KiCad 10 format 20251024.** Expected: 20241209 libraries take the as-is-with-warning row. Why human: KiCad 10 not installed.
3. **Case-sensitive-volume rollback.** Why human: only NTFS here.
4. **Re-import of a KiCad-edited part shows as a conflict (D-07).** Why human: confirm in the Phase 5 preview.

### Gaps Summary

No gaps. Gap 1 (exception-safe rollback) and gap 2 (stale-plan guarantee across the gate window) are closed in code, covered by passing tests, and independently reproduced as fixed. The five earlier-verified success criteria show no regression. The status is `human_needed` only because the UAT items above were never performed by a human and the decision tree makes a non-empty human list take precedence over `passed`.

---

_Verified: 2026-10-20_
_Verifier: Claude (gsd-verifier)_
