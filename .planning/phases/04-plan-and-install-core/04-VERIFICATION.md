---
phase: 04-plan-and-install-core
verified: 2026-10-20T12:00:00Z
status: gaps_found
score: 5/7 must-haves verified
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
  - kicad_lib_manager/importer/applier.py
  - kicad_lib_manager/importer/kicad_cli.py
  - kicad_lib_manager/importer/plan.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/verify.py
  - kicad_lib_manager/kicad_files.py
  - tests/test_install_apply.py
  - tests/test_install_e2e.py
  - tests/test_install_plan.py
  - tests/test_install_verify.py
covered_digest: "v3:sha256:35c56eb4c934b794db5720e951f28eae2f957f904f1b246b8625390d59c4e39a"
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Any failure during an install, not only a returned write Issue, leaves every touched file exactly as it was (goal: 'transactionally', 'failures are rolled back'; INST-07)"
    status: failed
    reason: "apply_plan wraps nothing in try/except. Rollback runs only when _write or verify returns an Issue. An exception raised by the progress callback, _make_folders (folder.resolve()), or verify.verify_install escapes after files are already written and _rollback is never called. Reproduced independently in this verification (see Behavioral Spot-Checks): a progress callback that raises at op 2 leaves Custom/3DModels/X.stp and Footprints/IC_Test_TI.pretty/FP.kicad_mod on disk and the exception propagates; a verify_install that raises does the same. Review finding CR-01, still disposition 'open'."
    artifacts:
      - path: "kicad_lib_manager/importer/applier.py"
        issue: "Lines 291-312 (write loop, progress call, verify_install) and 323-340 (_make_folders) are not exception-safe; _rollback is unreachable on a raised exception"
    missing:
      - "Wrap the write loop, progress call and verify_install in try/except BaseException; roll back, then convert Exception to an install.unexpected Issue and re-raise KeyboardInterrupt/SystemExit"
      - "Guard the progress callback so a UI error cannot abort the transaction (Phase 5 will pass a Qt progress callback)"
      - "Move folder.resolve() in _make_folders inside the try"
      - "Regression tests: raising progress callback, monkeypatched verify_install that raises, assert tree byte-identical afterwards"
  - truth: "A plan whose target changed after the plan was built is refused and never overwrites the newer content (stale-plan guarantee, 04-07 D2)"
    status: partial
    reason: "The hash check happens in _preflight, then _gate runs up to three kicad-cli processes (60 s timeout each) before the backup and the first write, with no re-check. A target edited in that window is overwritten by the planned bytes, which were spliced onto the preflight-time content, and apply_plan returns ok=True with only install.done. Reproduced independently: a runner that rewrites the .kicad_sym during the gate yields ok=True and the live file no longer contains the edit (it survives only in the backup folder, which the result does not mention). Review finding CR-02, still disposition 'open'. The common stale case (change before apply_plan starts) is correctly refused and tested."
    artifacts:
      - path: "kicad_lib_manager/importer/applier.py"
        issue: "Lines 264-284: backup is taken after the gate and is not compared with op.base_sha256; rollback restores the stale preflight pre-image rather than what was really backed up"
    missing:
      - "Hash the backed-up copy against op.base_sha256 before the first write; refuse with install.stale_plan on mismatch and use the backed-up bytes as the pre-image"
      - "Optionally re-hash the symbol library immediately before its atomic write"
      - "Test: gate runner that edits the target mid-gate must give ok=False and leave the edit intact"
---

# Phase 4: Plan and Install Core Verification Report

**Phase Goal:** A parsed part installs into `Custom/` correctly and transactionally. The symbol is merged, the footprint and 3D model are placed and linked, failures are rolled back and the result is verified, all testable without a display.
**Verified:** 2026-10-20
**Status:** gaps_found
**Re-verification:** No, initial verification

## Summary

The "installs correctly" half of the goal is solidly achieved and independently evidenced. The "transactionally" half is achieved for failures that arrive as returned `Issue` values (every write-failure test passes) but not for unexpected exceptions, and a narrow window lets a concurrent edit be overwritten while reporting success. Both defects were reproduced by me against the real code, not taken from the review. Neither is deferred to a later phase (Phases 5 to 7 do not mention apply_plan exception safety or post-gate re-hashing), and the review disposition still lists both as open.

Evidence base: the full suite on the merged tree gives **1321 passed, 5 skipped** (re-run by me; skips are the env-gated UAT test, a Windows symlink privilege, and 3 WurthElektronik submodule-not-checked-out). `git status --porcelain Custom` prints nothing. The e2e module carries a module-scoped autouse fixture that digests the real `Custom/` before and after.

## Goal Achievement

### Observable Truths

| #   | Truth (ROADMAP success criteria, then phase-goal truths) | Status | Evidence |
| --- | -------- | ------ | -------- |
| 1 | SC1: UL sample into a copy of `Custom/` adds `CSD85301Q2`, others and header byte-identical; `DQK0006B.kicad_mod` consistent (filename, internal name, value text, `Footprint` field, `ki_fp_filters`); STEP copied to `3DModels/CSD85301Q2.stp`; `${CUSTOM_3DMODEL_DIR}/CSD85301Q2.stp` block inserted | VERIFIED | `tests/test_install_e2e.py::test_ul_symbol_added_others_identical` removes the inserted segment and asserts the remainder equals the original bytes, checks `footprint_name`, value text, a single model path `${CUSTOM_3DMODEL_DIR}/CSD85301Q2.stp`, `Footprint == IC_Battery_Charger_TI:DQK0006B`, `ki_fp_filters == DQK0006B`, model SHA equals intake SHA, backup holds the original. `test_sc1_ul_footprint_model_and_fields` adds the footprint-side asserts. Both pass in the full run. |
| 2 | SC2: rename renames unit sub-symbols and `extends` refs and nothing else; a package with no 3D model installs and warns | VERIFIED | `test_sc2_rename_follows_sub_symbols`, `test_sc2_no_model_package` (warns `install.no_model`); old refusal codes `install.rename_unsupported` / `extends_unsupported` no longer exist in `kicad_lib_manager/` (grep empty), so the 04-01 "Not Done Here" refusals were closed by 04-06 and 04-08. |
| 3 | SC3: new library name creates a matching `.kicad_sym` + `.pretty/` pair; existing version header never changed; with kicad-cli the incoming symbol is normalised (footprints as-is, D-02); without it merged as-is with a warning | VERIFIED | `test_sc3_new_library_pair`, `test_sc3_existing_headers_unchanged` (3 cases: 20211014, 20231120, 20241209), and 7 real-kicad-cli tests (`-m kicad_cli`, kicad-cli 9.0.9 present) covering the five version scenarios and a real load check. INST-06 / ROADMAP text amended for D-02 and present. |
| 4 | SC4: a failure injected on any write leaves every touched file as it was; an identical model (same SHA-256) is reused, a different one is a conflict, not overwritten | VERIFIED for returned write failures | `test_sc4_fail_on_each_write` (3 cases, derives write count from the plan), `test_rollback_fail_on_nth_write`, `test_rollback_fail_with_locked_target`, `test_rollback_on_verify_error`, `test_sc4_model_same_sha_reused`, `test_sc4_model_different_sha_conflict`; byte-identical snapshot and no `.tmp` leftovers. The criterion as written ("failure injected on any write") is met; the wider transaction claim is truth 6. |
| 5 | SC5: verification re-parses files, resolves `<Lib>:<FP>`, confirms the model; warns on name-elsewhere and pin/pad mismatch; importing twice changes nothing | VERIFIED | `test_sc5_name_elsewhere_and_verify` (`verify.name_elsewhere`), `test_sc5_pin_pad_mismatch` (names pad 9), `test_second_install_is_noop` and `test_second_install_new_library_is_noop` (no write, no backup folder, `install.nothing_to_do`), `test_cli_second_install_is_noop`. 04-05's hand-off ("applier drops verify WARNINGs") is closed: `applier.py:300-302,318` appends non-error verify issues, covered by `test_success_keeps_the_soft_verify_warnings`. |
| 6 | Goal: failures are rolled back, i.e. any failure during the install (including an unexpected exception) leaves nothing half-installed | FAILED (BLOCKER) | See gap 1. Independent probe: raising `progress` and raising `verify_install` both leave `3DModels/X.stp` and `Footprints/IC_Test_TI.pretty/FP.kicad_mod` on disk, exception escapes, `_rollback` never invoked. |
| 7 | Goal: the install is transactional against a stale plan, a target changed after planning is never silently overwritten | PARTIAL (BLOCKER) | See gap 2. Pre-apply staleness refused and tested (`test_stale_plan_*`); change during the kicad-cli gate window is overwritten with `ok=True`. |

**Score:** 5/7 truths verified

### Deferred Items

None. Phase 5 (preview/UI), 6 (git commit) and 7 (SnapEDA/SamacSys adapters) goals and success criteria do not cover apply_plan exception safety or post-gate hash re-check, so neither gap qualifies for deferral. Phase 5 will increase exposure to gap 1 by passing a GUI progress callback.

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `kicad_lib_manager/importer/plan.py` (154 lines) | Frozen plan contract, FileOp, InstallResult | VERIFIED | Imported by planner, applier, verify, tests |
| `kicad_lib_manager/importer/planner.py` (1113 lines) | build_plan: versions, rename, conflicts, no-op | VERIFIED (maintainability warning) | Substantive, wired to applier via plan; one 528-line function (WR-04) |
| `kicad_lib_manager/importer/applier.py` (363 lines) | Transactional apply with gate, backup, rollback, prune | VERIFIED but see gaps 1, 2 | Wired and heavily tested; exception safety and TOCTOU defects |
| `kicad_lib_manager/importer/verify.py` (301 lines) | D-18 hard checks, POST-03/04 warnings | VERIFIED | Called from applier line 300 |
| `kicad_lib_manager/importer/kicad_cli.py` (281 lines) | locate/run/upgrade/load_gate | VERIFIED | Called from applier `_gate`; real kicad-cli tests pass |
| `kicad_lib_manager/kicad_files.py` write side | install unit, rename, replace/insert-before, model edits | VERIFIED | Used by planner; `tests/test_kicad_files_write.py` |
| `tests/installfixtures.py`, `tests/fakecli.py`, `tests/conftest.py` | Fixture builders, FakeCli, `kicad_cli` marker and path fixture | VERIFIED | 358-line fixture self-test, marker works |
| `tests/test_importer_layering.py` | `importer.kicad_cli` registered in layering | VERIFIED | Passes in full run |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| planner.build_plan | kicad_files edit primitives | rename/replace/insert/property edits | WIRED | e2e SC1/SC2 exercise it |
| planner.build_plan | kicad_cli.upgrade (memoised) | D-01 version table | WIRED | `-m kicad_cli` scenarios |
| applier.apply_plan | kicad_cli.load_gate | `_gate()` before first backup/write | WIRED | `test_gate_rejects_before_any_write` |
| applier.apply_plan | verify.verify_install | after writes; ERRORs roll back, WARNINGs returned | WIRED | `test_rollback_on_verify_error`, `test_success_keeps_the_soft_verify_warnings` |
| applier.apply_plan | fsutil.atomic_write_bytes / backup_file | module-attribute seam | WIRED | fault injection tests |
| applier._rollback | every `_Undo` step | reverse order, continue past failure | WIRED for Issue failures only | not reachable on a raised exception (gap 1) |
| applier write loop | progress callback | `progress(...)` per op | PARTIAL | unguarded (gap 1) |
| applier._preflight hash | write | stale-plan guarantee | PARTIAL | not re-checked after gate (gap 2) |

### Data-Flow Trace (Level 4)

Not applicable in the rendering sense (no UI in this phase). Equivalent trace done: installed bytes come from the staged, hash-checked vendor files (`_read_vendor` plan-time re-hash and `_preflight` source re-hash), the written `Footprint` field, filter and model path are asserted on the files read back from disk in the e2e tests, so real data flows end to end.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full suite | `./env/Scripts/python.exe -m pytest -q` | 1321 passed, 5 skipped in 99 s | PASS |
| Real Custom/ untouched | `git status --porcelain Custom` | empty | PASS |
| CR-01: raising progress callback | scratchpad probe over `_hand_plan` | `RuntimeError` escapes; tree gained `3DModels/X.stp` and `FP.kicad_mod` | FAIL |
| CR-01: raising verify_install | same | same leftover files, no rollback | FAIL |
| CR-02: target edited during gate | runner that rewrites the .kicad_sym | `ok=True`, issues `['install.done']`, live file lacks the edit | FAIL |

Probe script: `C:/Users/sylvain/AppData/Local/Temp/claude/c--Git-Repo-Clones-Kicad-Libraries-importer/6eafc438-c508-4cf8-b673-8efcd5b12975/scratchpad/test_probe_verify.py` (reads only the `tmp_path` trees it builds).

### Probe Execution

SKIPPED (no `scripts/*/tests/probe-*.sh` declared by any plan).

### Requirements Coverage

All 13 phase IDs appear in plan frontmatter and in REQUIREMENTS.md; none orphaned. REQUIREMENTS.md maps no other ID to Phase 4.

| Requirement | Source Plans | Description | Status | Evidence |
| ----------- | ------------ | ----------- | ------ | -------- |
| INST-01 | 04-01, 04-04, 04-10 | Symbol added without altering others/header | SATISFIED | e2e byte-identical remainder test |
| INST-02 | 04-02, 04-04, 04-08, 04-10 | Rename follows unit sub-symbols and `extends`, never substring | SATISFIED | `test_sc2_rename_follows_sub_symbols`, extends pair fixtures |
| INST-03 | 04-01, 04-04, 04-08, 04-10 | Footprint filename/name/value/Footprint field/filters consistent | SATISFIED | SC1 tests |
| INST-04 | 04-01, 04-07, 04-09, 04-10 | Model as `<MPN>.<ext>`, same SHA reused, different is conflict | SATISFIED | SC4 model tests |
| INST-05 | 04-01, 04-02, 04-04, 04-10 | Model path rewrite/insert `${CUSTOM_3DMODEL_DIR}` | SATISFIED | SC1 asserts single model path |
| INST-06 | 04-02, 04-03, 04-06, 04-10 | Symbol normalised with kicad-cli, as-is with warning without | SATISFIED | SC3 + real kicad-cli scenarios; KiCad 10 format untested (human item) |
| INST-07 | 04-07, 04-10 | If any write fails, every touched file restored and failure logged | PARTIAL | Satisfied for returned write failures; an exception outside the write call defeats rollback (gap 1) |
| INST-08 | 04-01, 04-05, 04-07, 04-10 | Result verified: re-parse, `<Lib>:<FP>` resolves, model exists | SATISFIED | verify tests, SC5 |
| INST-09 | 04-09, 04-10 | Second identical import changes nothing | SATISFIED | no-op tests (existing and new library, with and without CLI) |
| INTK-08 | 04-08, 04-10 | No-model package installs and warns | SATISFIED | `test_sc2_no_model_package` |
| LIB-02 | 04-06, 04-10 | Create new library pair | SATISFIED | `test_sc3_new_library_pair`; WR-02 (missing `Custom/Symbols/` late failure) is an edge, rollback is clean |
| POST-03 | 04-05, 04-10 | Warn if part name exists in another library | SATISFIED | `verify.name_elsewhere` e2e |
| POST-04 | 04-02, 04-05, 04-10 | Warn on pin/pad number mismatch | SATISFIED | `verify.pin_pad_mismatch` e2e |

INST-07 should be treated as not fully complete in REQUIREMENTS.md traceability until gap 1 is closed.

### Anti-Patterns Found

No TBD/FIXME/XXX debt markers checked as BLOCKER beyond the gaps above (scan of the modified importer files for unreferenced markers is not a source of findings; the findings come from the review, re-verified for CR-01/CR-02 only).

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `kicad_lib_manager/importer/applier.py` | 291-312, 323-340 | No exception safety around write loop / progress / verify | BLOCKER | Gap 1 |
| `kicad_lib_manager/importer/applier.py` | 264-284 | No hash re-check after gate | BLOCKER | Gap 2 |
| `kicad_lib_manager/importer/applier.py` | 129-141, 284 | Prune can delete the just-created backup folder when the clock steps back with 10+ later-stamped folders (CR review WR-01, not reproduced by me) | WARNING | Rollback-failure message could point at a missing folder |
| `kicad_lib_manager/importer/planner.py` | 1070-1080 | No `mkdir` for a missing `Custom/Symbols/` (WR-02) | WARNING | Late, but cleanly rolled back |
| `kicad_lib_manager/importer/planner.py` + `candidate.py` | 591-601 | Package-level issues not carried by `ImportCandidate.issues` (WR-03) | WARNING | A Phase 5 caller that forgets `package_issues=` silently reproduces the Phase 3 WR-05 defect; no e2e test |
| `kicad_lib_manager/importer/planner.py` | 120-123, 183-193, 748-760 | Empty string in `InstallOptions` blanks vendor value (WR-05) | WARNING | The Phase 5 form will pass `""`; must be normalised before or in Phase 5 |
| `kicad_lib_manager/importer/planner.py` | 585-1113 | 528-line `build_plan` (WR-04) | WARNING | Maintainability only |
| `kicad_lib_manager/importer/applier.py` | 256-257 | No-op claim not re-checked against disk (IN-01) | INFO | No data at risk |
| `tests/test_install_e2e.py` | 551-566 | UAT test rmtree's whatever `<dir>/Custom` holds (IN-03) | INFO | Only when the env var is set |
| various | - | Duplicated `_err`, `_listing` (IN-02) | INFO | Cosmetic |

Review disposition: all 10 findings are still `open` in 04-REVIEW-DISPOSITION.md. None was fixed, accepted or deferred.

### SUMMARY claims vs. code

- 04-10 SUMMARY "Self-Check: PASSED" and "Known Stubs: None": true as far as stubs go; the SUMMARIES do not mention CR-01/CR-02 (the review ran after).
- Hand-offs checked and closed: 04-01 refusals (library_not_found, version_unsupported, rename_unsupported, extends_unsupported, conflict resolutions, kicad-cli gate, fault-injection tests, backup pruning) all implemented; 04-05 dropped-verify-warnings closed (applier lines 300-318); 04-06 duplicate `install.cli_not_found` closed in 04-07; 04-03 layering registration closed. Nothing dropped.
- 04-10 UAT items remain human-only as recorded; they were not performed.

### Human Verification Required

These do not change the status (gaps_found takes precedence) but remain open for the owner after the gaps are closed:

1. **KiCad 9 UAT on the scratch install** (`C:\Users\sylvain\AppData\Local\Temp\kicad_import_uat`, checklist in 04-10-SUMMARY.md). Expected: library opens without a load error, `CSD85301Q2` shows units A and B with `Footprint IC_Battery_Charger_TI:DQK0006B` and hidden Manufacturer/MPN, `DQK0006B` shows 8 pads and the STEP sits on the pads. Why human: KiCad GUI rendering. Includes the A6/A7 field-rule yes/no judgement (renamed vendor Manufacturer/MPN keep their own visibility; extends parent receives Footprint/filters/Manufacturer).
2. **KiCad 10 symbol format 20251024 (research A1)**. Expected: every 20241209 `Custom/` library takes the as-is-with-warning row. Why human: KiCad 10 not installed.
3. **Case-sensitive-volume rollback/overwrite branches** (case twin written under another spelling). Why human: only NTFS available; covered with faked directory listings only.
4. **Product question from 04-09**: a part edited in KiCad shows as a conflict on re-import (accepted D-07 consequence), confirm in Phase 5 preview.

### Gaps Summary

Two gaps, both in `applier.py`, both reproduced independently:

1. **Rollback is not exception-safe (BLOCKER).** The transaction promise ("every change is undone on failure") holds for write failures returned as `Issue`s, which is all that the injected-fault tests exercise. It does not hold if anything in the write loop, the progress callback, `_make_folders` or `verify_install` raises. Phase 5 will supply a GUI progress callback, which makes this a realistic path. Fix is small and local (try/except BaseException around the loop and verify, roll back, convert to an Issue, re-raise interrupts), plus two regression tests.
2. **Stale-plan check is not held across the gate window (BLOCKER for "transactionally", recoverable data).** A target saved by KiCad, git or the user between preflight and the first write is overwritten and the install reports success; the edit is only preserved in the backup folder, which the result does not mention. Fix: compare the backed-up copy with `op.base_sha256` before writing and use it as the rollback pre-image.

Recommended next step: `/gsd-plan-phase 04 --gaps` to close both (one small plan), then re-verify. The WARNING-level review items WR-03 (package-level issues) and WR-05 (empty-string options) should be closed in that same plan or explicitly handed to Phase 5 planning, since both bite at the Phase 5 form/caller boundary.

---

_Verified: 2026-10-20_
_Verifier: Claude (gsd-verifier)_
