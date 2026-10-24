---
phase: 07-snapeda-and-samacsys-adapters
verified: 2026-10-24T12:00:00Z
status: human_needed
score: 4/4 roadmap success criteria verified (plans 07-01..07-09 must-have truths all verified); 0 failed
covered_files:
  - .gitignore
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-01-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-01-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-02-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-02-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-03-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-03-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-04-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-04-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-05-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-05-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-06-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-06-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-07-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-07-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-08-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-08-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-09-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-09-SUMMARY.md
  - kicad_lib_manager/importer/adapters/base.py
  - kicad_lib_manager/importer/adapters/samacsys.py
  - kicad_lib_manager/importer/adapters/snapeda.py
  - kicad_lib_manager/importer/detect.py
  - kicad_lib_manager/importer/fieldrules.py
  - kicad_lib_manager/importer/package.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/suggest.py
  - kicad_lib_manager/importer/verify.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_model_attach.py
  - tests/test_model_source.py
  - tests/test_real_vendor_samples.py
  - tests/test_vendorfixtures.py
  - tests/vendorfixtures.py
covered_digest: "v3:sha256:0fd48b1ae3dd705779eca88d0ed7f42b6092c477e7881a25cccb35f7425386a2"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 3/3 roadmap criteria (plans 07-01..07-06)
  gaps_closed:
    - "G-07-2: a separately downloaded SnapEDA 3D model (bare .step/.stp/.wrl or a zip holding it) can be added to the open SnapEDA import"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "UAT test 2 re-run in the live GUI. Open downloaded_examples/USB4145-03-0170-C_REVA2.zip in the Import dialog, click 'Add 3D model...' on the 3D model row, pick downloaded_examples/194150990-659-usb4145-03-0170-c.zip (then repeat with the bare .stp extracted from it), read the preview, and install into a scratch copy of Custom/ or cancel at the preview."
    expected: "The 'Add 3D model...' button is visible under the '3D model' row and the file picker offers *.step *.stp *.wrl *.zip. After the pick the row shows usb4145-03-0170-c.stp, the 'no 3D model found' warning is gone, the Files section lists Custom/3DModels/USB4145-03-0170-C.stp, edits typed before the attach (Value, MPN, library, footprint name) are unchanged, Install is disabled only while the model is being read, and the installed footprint links ${CUSTOM_3DMODEL_DIR}/USB4145-03-0170-C.stp. A .txt-only zip or a renamed non-STEP file shows an amber plain-text note and changes nothing."
    why_human: "UAT 07-UAT.md test 2 is still recorded as 'issue' (status diagnosed). The fix is proven headless against the real files, but the owner's own run through the file picker and the live look of the button, note and combo cannot be judged from pytest, and the Qt file dialog is faked in every committed test."
---

# Phase 7: SnapEDA and SamacSys Adapters Verification Report

**Phase Goal:** SnapEDA and SamacSys / Component Search Engine downloads import through the same flow as Ultra Librarian packages
**Verified:** 2026-10-24
**Status:** human_needed (all automated checks pass; one live-GUI re-test of UAT test 2 remains)
**Re-verification:** Yes, after gap closure 07-07 to 07-09 (UAT gap G-07-2). The earlier report covered plans 07-01..07-06; every criterion was re-checked here, and criteria 1 to 3 were re-run, not copied.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria, the contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Real SnapEDA zip recognised as SnapEDA; symbol, footprint and any model found; no model gives the "no 3D model found" warning | VERIFIED | Regression run: `test_real_snapeda_recognised`, `test_real_snapeda_installs` PASSED against the real `USB4145-03-0170-C_REVA2.zip` (no skips; `-rA` run shows 11 PASSED in `test_real_vendor_samples.py`). My own `python -I` probe attached nothing and the candidate had `models == ()` with `intake.no_model` as before, so the CAD-zip-alone behaviour is unchanged. |
| 2 | Real SamacSys/CSE zip recognised; KiCad v6+ symbol, footprint and 3D model found; legacy `.lib`/`.dcm` ignored, not rejected | VERIFIED | `test_real_samacsys_recognised`, `test_real_samacsys_installs`, `test_real_samacsys_suggestion` PASSED on the real `LIB_RS3-1212S_H3.zip`. No SamacSys source file changed in the gap closure (`git diff --stat 10b62efa..HEAD -- kicad_lib_manager` touches only `package.py`, `adapters/base.py`, `help_dialog.py`, `import_dialog.py`). |
| 3 | Each vendor sample installs into a copy of `Custom/` with the same `<Lib>:<FP>` link and `${CUSTOM_3DMODEL_DIR}` model path as UL; covered by trimmed/synthetic fixtures where redistribution forbids | VERIFIED | `tests/test_vendor_install.py`, `test_vendorfixtures.py` (originality guard) pass; both `test_real_vendor_installs_load_in_kicad[snapeda|samacsys]` (kicad-cli) PASSED; committed fixtures are synthetic (`tests/vendorfixtures.py`). |
| 4 | User can add a separately downloaded SnapEDA 3D model (bare `.step`/`.stp`/`.wrl`, or a zip holding one) in the import dialog; installs as `Custom/3DModels/<MPN>.<ext>` linked as `${CUSTOM_3DMODEL_DIR}/<file>`; every intake safety check applies; nothing is written before the preview (G-07-2) | VERIFIED (live GUI pass pending, see Human Verification) | See the G-07-2 table below. Real two-file delivery installed headless: `test_real_snapeda_installs_with_separate_model` PASSED (`Custom/3DModels/USB4145-03-0170-C.stp`, 2443718 bytes, footprint `(model ${CUSTOM_3DMODEL_DIR}/USB4145-03-0170-C.stp)`, Footprint field `Connector_USB_GCT:GCT_USB4145-03-0170-C_REVA2`, no `intake.no_model`/`install.no_model`, no ERROR). |

**Score:** 4/4 roadmap criteria verified; 0 behavior-unverified.

### G-07-2 gap closure: plan must-have truths (07-07, 07-08, 07-09)

| Plan | Truth | Status | Evidence |
|------|-------|--------|----------|
| 07-07 | `open_model_source` stages only model members of a zip, lists everything else in one "Not imported from ..." INFO, applies every Phase 3 zip refusal, refuses a zip with no model (`intake.no_model_in_source`) and removes its staging | VERIFIED | Code `package.py:310-358` reuses `_open_zip(..., kinds=MODEL_SOURCE_KINDS)` and `_refuse`s a model-less zip. Probe on the real model zip: files `[usb4145-03-0170-c.stp, 2443718, staged]`, issue `intake.ignored_members` (the `.txt`), not refused. `tests/test_model_source.py` (hostile zip parametrized, nested, ignored, no-model) pass. |
| 07-07 | Bare model read in place behind no-follow `lstat`, link/junction/reparse refusal, regular-file check, handle-identity check, `MAX_MEMBER_BYTES` on lstat and on counted bytes, real size and SHA-256, never copied | VERIFIED | `package.py:318-394` (`_lstat`, `S_ISLNK`/`_WINDOWS_REPARSE`, `fstat` dev/ino match, counted-bytes cap). Probe: `bare.stp` accepted with `kind=file`, `staged=False`, `staging_dir=None`; `x.txt` refused `intake.unsupported`; missing file `intake.not_found`. Tests for reparse point, handle mismatch, oversize and grown-after-listing pass. The symlink variant is skipped here (no symlink privilege, WinError 1314); the same branch is exercised through the reparse-point test, so I count it as covered. |
| 07-07 | `attach_models` attaches only magic-checked models, renames casefolded clashes `<stem>_<n><ext>`, skips duplicate SHA-256, drops `intake.no_model`, adds `intake.model_attached` naming the source file only, returns `None` plus reasons when nothing usable, never mutates the input | VERIFIED | `adapters/base.py:358-426`. Probe: real zip attaches `usb4145-03-0170-c.stp`, `no_model` dropped, issues `[ignored_members, model_attached]`; a text file renamed `.stp` gives `None` with `[content_mismatch, no_model_in_source]`; attaching the same bare file twice gives `None` with `intake.model_already_present`. `tests/test_model_attach.py` passes. |
| 07-07 | Attached model flows through the unchanged `build_plan`/`apply_plan`; saved as `<MPN>.<ext>`; applier refuses a stale bare source or a closed zip source; plan, planner, applier, commit_plan, preview, candidate unchanged | VERIFIED | `git diff --stat 10b62efa..HEAD -- kicad_lib_manager` shows none of those six files touched. `applier.py:292-303` re-reads each `op.source.path` and compares SHA-256 (`install.source_gone` / `install.source_changed`). Real-sample install test above. |
| 07-07 | `open_package` behaves as before | VERIFIED | `test_open_package_unchanged_for_model_zip` and the existing intake/adapter/vendor suites pass (333 passed in the 10 relevant test files). |
| 07-08 | Add 3D model... shows on every model-row state; attaching to a part that has a model turns the row into a combo ending with "No model", attached model selected | VERIFIED | `import_dialog.py:1395-1463` (`_build_model_row`, `_refresh_model_row(select=...)`); `test_add_model_button_on_every_row_state`, `test_add_model_to_part_with_model_selects_it` pass. |
| 07-08 | Attach never wipes edits: no `_populate_items`/`_reload_symbol_defaults`, only the model row rebuilt, then one `_request_rebuild` | VERIFIED | `_refresh_model_row` docstring and body (1437-1463) touch only the slot; `_on_model_attached` (1651-1687) calls it then `_request_rebuild()`. `test_add_model_keeps_edits` passes. |
| 07-08 | Refused/empty source leaves candidate and row unchanged; reason as plain-text amber note and log; staging removed; duplicate gives muted "already listed" note with no rebuild | VERIFIED | `_on_model_attached` 1670-1681; note is `Qt.TextFormat.PlainText` (1417); `test_add_model_refusal_shows_note`, `test_add_model_note_is_plain_text`, `test_add_model_duplicate_is_noted` pass. |
| 07-08 | While reading, Add is disabled and Install blocked as Updating; also disabled while installing/committing/opening | VERIFIED | `_model_busy` (1593-1601) and `_updating()` (2118) count `_model_worker`; `test_add_model_blocks_install_while_reading`, `test_add_model_disabled_while_installing` pass. |
| 07-08 | Model packages stay open until `apply_plan` returns; closed by Change.../new open/close; a read that finishes after Change... or during close is closed and never attached; work runs off the GUI thread | VERIFIED | `_discard_package` and `_shutdown` (2556-2586) close `_model_packages` and unhandled `ModelOutcome`s; the stale branch (1656-1668) closes the package. `test_add_model_package_open_until_install_ends`, `..._result_after_change_is_dropped`, `..._close_while_reading_closes_package`, `..._runs_off_gui_thread` pass. One edge-case defect is recorded under Anti-Patterns (WR-01 of the review): it does not change what these tests assert. |
| 07-08 | Help page tells the user about the separate SnapEDA download and the button; button text and page share one constant | VERIFIED | `help_dialog.py:224-228` builds the paragraph from `ADD_MODEL_TEXT` (defined `import_dialog.py:75`); `test_help_import_page_describes_add_model` passes. |
| 07-09 | Real model zip opens (stages exactly `usb4145-03-0170-c.stp`, 2443718 bytes, ISO-10303-21; magic, `.txt` listed not imported) and installs with the real CAD zip; skip with a reason when the file is absent | VERIFIED | `test_real_snapeda_model_zip_opens` and `test_real_snapeda_installs_with_separate_model` PASSED with the real files present; gated by `requires_snapeda_model` (D-02). |
| 07-09 | Real model zip stays local; synthetic model fixture shares no SHA-256 with a real member and carries no real part name | VERIFIED | `git check-ignore -v` matches `.gitignore:31 downloaded_examples/*`; `git ls-files downloaded_examples` lists only `ul_CSD85301Q2.zip`; `git ls-files` finds no file named for the SnapEDA, SamacSys or model downloads; `test_vendor_zips_stay_local` (now asserts the model zip) and `test_fixture_originality[snapeda_model]` PASSED. |
| 07-09 | Docs: FMT2-02 in v1 and traced to Phase 7 with SnapEDA wording, gone from v2, coverage 54; PROJECT.md Out of Scope entry removed with Active item and Key Decision citing G-07-2; ROADMAP Phase 7 lists FMT2-02 and a fourth criterion; 07-CONTEXT amended without rewriting the decision text | VERIFIED | `REQUIREMENTS.md:40` (v1 Package Intake), only FMT2-01 under v2 Formats, traceability row `FMT2-02 | Phase 7`, "54 total"; `PROJECT.md:64` (Active) and `:111` (Key Decision); `ROADMAP.md` Phase 7 `Requirements: INTK-03, INTK-04, FMT2-02` and criterion 4; `07-CONTEXT.md:42` carries "**Amended 2026-10-23 (UAT G-07-2):**" after the original text. |

Plan 07-01..07-06 truths were verified in the earlier report and their tests still pass in this run (see Spot-Checks); no code in their files changed in the gap closure except `package.py` and `adapters/base.py`, whose existing suites pass.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kicad_lib_manager/importer/package.py` | `open_model_source`, `_open_model_file`, `kinds` filter | VERIFIED | 130 lines added; substantive, wired from the dialog via `ImportCore` and from tests |
| `kicad_lib_manager/importer/adapters/base.py` | `attach_models` | VERIFIED | Same `_check_model` as `locate`; wired from the dialog |
| `kicad_lib_manager/widgets/import_dialog.py` | Add 3D model... flow, busy guards, package lifetime | VERIFIED | `core.open_model_source(` at 1623, `core.attach_models(` at 1625 |
| `kicad_lib_manager/widgets/help_dialog.py` | Help text from `ADD_MODEL_TEXT` | VERIFIED | Line 224 |
| `tests/vendorfixtures.py` | `snapeda_model_zip`, `snapeda_model_members` | VERIFIED | Used by `test_model_*` and the originality guard |
| `tests/test_model_source.py`, `tests/test_model_attach.py` | Intake and attach suites | VERIFIED | Pass |
| `.planning/REQUIREMENTS.md`, `PROJECT.md`, `ROADMAP.md`, `07-CONTEXT.md` | Doc moves | VERIFIED | See above |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `import_dialog.py` (`_start_model_attach` task) | `package.open_model_source` | `core.open_model_source(path, repo_root, progress)` on a `TaskWorker` | WIRED | `import_dialog.py:1623`; `ImportCore` field present; test fakes it via `dataclasses.replace` |
| `import_dialog.py` | `adapters.base.attach_models` | `core.attach_models(candidate, package)` same worker | WIRED | `import_dialog.py:1625`; result handed to `_on_model_attached` on the GUI thread |
| `open_model_source` | `_open_zip`/`_stage_zip`/`_prescan` | `kinds=MODEL_SOURCE_KINDS` | WIRED | `package.py:343` |
| `attach_models` | `_check_model` | direct call | WIRED | `base.py:382` |
| Attached `ModelItem` | `build_plan` -> `apply_plan` | `candidate.models` | WIRED | Real two-file install test; planner/applier unchanged |
| `_updating()` | Install state | `_model_worker is not None` | WIRED (see WR-01) | `import_dialog.py:2118` |
| `help_dialog` | `ADD_MODEL_TEXT` | import | WIRED | `help_dialog.py:7` |
| `ROADMAP.md` Phase 7 | `REQUIREMENTS.md` | `INTK-03, INTK-04, FMT2-02` | WIRED | Present in both |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| Dialog model row | `candidate.models` | `attach_models(candidate, open_model_source(real file))` | Yes: real 2443718-byte STEP staged and hashed | FLOWING |
| Plan model op | `op.source` (`PackageFile`) | attached `ModelItem.file` | Yes: applier re-reads and re-hashes the staged bytes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 7 test files (model source/attach, help, import dialog, real samples, fixtures, vendor install, snapeda, samacsys, package zip) | `env/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_model_source.py tests/test_model_attach.py tests/test_help_dialog.py tests/test_import_dialog.py tests/test_real_vendor_samples.py tests/test_vendorfixtures.py tests/test_vendor_install.py tests/test_snapeda_adapter.py tests/test_samacsys_adapter.py tests/test_package_zip.py` | 333 passed, 1 skipped (symlink privilege), 2 failed | PASS (the 2 failures are baseline, see below) |
| Real-sample tests with real files present | `pytest -rA tests/test_real_vendor_samples.py` | 11 PASSED, 0 skipped, including both new G-07-2 tests and both kicad-cli load tests | PASS |
| Real model zip and bare file through `open_model_source`/`attach_models` | `python -I` probe in the scratchpad against `downloaded_examples/` | Zip stages one STEP, bare file read in place, non-STEP and `.txt` refused, duplicate skipped | PASS |
| Frozen plan-contract modules unchanged | `git diff --stat 10b62efa..HEAD -- kicad_lib_manager` | only 4 files changed, none of plan/planner/applier/commit_plan/preview/candidate | PASS |

The 2 failures, `test_import_dialog.py::test_tracer_ul_import_end_to_end` and `::test_preview_sections_follow_plan_ops`, are in the 21-id pre-execution baseline: they copy the live `Custom/` tree, which already holds `Custom/3DModels/CSD85301Q2.stp` from the owner's UAT install (`= ...` row instead of `+ ...`). Neither is a gap-closure test. I did not re-run the full suite; the orchestrator's full run (1946 passed, 6 skipped, 21 failed, ids identical to baseline, none in a gap-closure test file) is consistent with my subset.

### Probe Execution

No `probe-*.sh` scripts are declared or present. Skipped.

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|--------------|-------------|--------|----------|
| INTK-03 | 07-01, 07-02, 07-03, 07-04, 07-06, 07-07, 07-08, 07-09 | SnapEDA zip recognised; symbol, footprint, any 3D model found; verified against a real download | SATISFIED | Real SnapEDA zip detected at 1.0, install test passes; model now attachable (criteria 1 and 4) |
| INTK-04 | 07-03, 07-05, 07-06 | SamacSys/CSE zip recognised; symbol, footprint, 3D model found; verified against a real download | SATISFIED | Real SamacSys install test passes (criterion 2) |
| FMT2-02 | 07-07, 07-08, 07-09 | Separately downloaded 3D model (bare `.step`/`.stp`/`.wrl` or zip) added in the import dialog, checked like a package, copied as `<MPN>.<ext>`, linked as `${CUSTOM_3DMODEL_DIR}/<file>` | SATISFIED | Code, probe and real two-file install test above; live GUI pass pending as a human item |

All three IDs appear in PLAN frontmatter and in REQUIREMENTS.md (v1 list lines 34, 35, 40; traceability rows INTK-03, INTK-04, FMT2-02 all "Phase 7"). No orphaned requirements. Bookkeeping: REQUIREMENTS.md still shows INTK-03, INTK-04 and FMT2-02 as `[ ]` and "Pending" in the traceability table; tick them when the phase completes (not a gap).

### Prohibitions (must_haves.prohibitions, all test-tier)

| Prohibition | Enforcement found | Status |
|-------------|-------------------|--------|
| Never stage, commit or copy any byte of `downloaded_examples/194150990-659-usb4145-03-0170-c.zip` (07-09) | `.gitignore:31`, `git ls-files downloaded_examples` shows only the UL zip, `test_vendor_zips_stay_local` asserts the model zip is ignored, `test_real_snapeda_model_zip_opens` asserts staging is outside the repo and removed on close, `test_fixture_originality[snapeda_model]` | RESOLVED (wired, executed and passing) |
| Earlier prohibitions from 07-01..07-06 (no real vendor bytes, no unseen field change, no edit of existing symbols, markers never on disk, no unmapped PartCategory) | Same tests as the earlier report, all in this run's passing set | RESOLVED |

No unverified prohibitions.

### Anti-Patterns Found

TBD/FIXME/XXX/TODO/HACK scan over the changed source files found no markers. No stubs; the new code is exercised on real data.

Advisory review (07-REVIEW.md: 0 critical, 3 warning, 2 info, all disposition `open`). None contradicts a must-have truth. My assessment of each:

| Finding | Severity | Verified here | Impact on goal |
|---------|----------|---------------|----------------|
| WR-01 stale model result leaves Install stuck on "Updating preview..." | Warning | REPRODUCED. Scratch test: gate a model read, Change..., open the UL zip, release the gate. After the worker ends the strip reads "Updating preview..." and `_install_btn.isEnabled()` is False. Cause: the stale branch of `_on_model_attached` (`import_dialog.py:1662-1668`) only calls `_update_install_state()` when `outcome.session == self._session`, and `_end_model_worker` (1640-1643) only re-syncs the Add button. | Does not break the goal or a stated truth (the failure mode is safe: nothing installs from an unfinished preview, and the next field edit rebuilds). It needs a Change... plus a second open while a model read is still running, a window of a few tens of milliseconds with real files. Fix is a one-liner: call `_update_install_state()` from `_end_model_worker` when not closing, plus a test. Recommend a small follow-up, not a phase blocker. |
| WR-02 failed model read for an older package writes its error onto the new package's model row | Warning | Confirmed by reading: `_on_model_failed` (1689-1696) has no session check | Cosmetic, same narrow race, only on an unexpected worker exception |
| WR-03 two dialog tests depend on the live `Custom/` tree | Warning | Confirmed (the 2 failures above); the new gap-closure tests use synthetic layouts and are not affected | Environmental baseline, not a phase regression |
| IN-01 help dialog imports the whole import dialog module for one constant | Info | Confirmed (`help_dialog.py:7`) | Layering nit |
| IN-02 `intake.not_found` text carries the full path | Info | Confirmed (`package.py:323`) | Reachable only by a race after the file dialog |

Earlier WR-04/IN-03/IN-04 (SamacSys summary count wording, protected-name case, `_kicad_base`) remain `open` and cosmetic.

Housekeeping carried over: `07-VALIDATION.md` frontmatter vs sign-off `nyquist_compliant` mismatch was noted last time; the commit `4d024e4` ("fix nyquist_compliant frontmatter") addresses it.

### Human Verification Required

#### 1. Re-run UAT test 2 (separate SnapEDA 3D model) in the live GUI

**Test:** Run `.\env\Scripts\python.exe kicad_lib_manager.py`, open the Import dialog, load `downloaded_examples/USB4145-03-0170-C_REVA2.zip`, click **Add 3D model...** and pick `downloaded_examples/194150990-659-usb4145-03-0170-c.zip`. Repeat with the bare `.stp` extracted from that zip. Also try a `.txt`-only zip or a renamed non-STEP file. Read the preview and install into a scratch copy of `Custom/`, or cancel at the preview. Do not install into the live `Custom/`, which already holds an uncommitted UAT part.
**Expected:** The button sits under the 3D model row and the picker offers `*.step *.stp *.wrl *.zip`. After the pick the row shows `usb4145-03-0170-c.stp`, the no-3D-model warning is gone, the Files section lists `Custom/3DModels/USB4145-03-0170-C.stp`, values typed before the attach are untouched, and Install is off only while the model is read. The installed footprint links `${CUSTOM_3DMODEL_DIR}/USB4145-03-0170-C.stp`. The refused cases show an amber plain-text note and change nothing.
**Why human:** `07-UAT.md` test 2 still reads `issue` (status `diagnosed`). The fix is proven headless on the real files, but the real file picker and the on-screen look cannot be checked from pytest, and every committed dialog test fakes the picker.

### Gaps Summary

No gaps. Gap G-07-2 is closed in code and tests: `open_model_source` and `attach_models` exist, are substantive and are wired into the dialog's `Add 3D model...` flow on a worker thread. The attached model reaches the unchanged plan and applier and installs as `Custom/3DModels/<MPN>.<ext>` linked as `${CUSTOM_3DMODEL_DIR}/<file>`. This is proven on the owner's real two-file SnapEDA delivery. The real downloads stay out of git, and the planning documents carry FMT2-02 in v1. Status is `human_needed` only because the owner has not yet re-run UAT test 2 in the live GUI. One reproduced advisory defect (review WR-01, Install left on "Updating preview..." after a stale model read) is worth a small follow-up fix.

---

_Verified: 2026-10-24_
_Verifier: Claude (gsd-verifier)_
