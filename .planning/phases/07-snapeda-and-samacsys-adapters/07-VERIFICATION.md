---
phase: 07-snapeda-and-samacsys-adapters
verified: 2026-10-23T14:00:00Z
status: human_needed
score: 3/3 roadmap success criteria verified (plan must-haves 6 plans, all truths verified)
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
  - kicad_lib_manager/importer/adapters/base.py
  - kicad_lib_manager/importer/adapters/samacsys.py
  - kicad_lib_manager/importer/adapters/snapeda.py
  - kicad_lib_manager/importer/detect.py
  - kicad_lib_manager/importer/fieldrules.py
  - kicad_lib_manager/importer/package.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/suggest.py
  - kicad_lib_manager/importer/verify.py
covered_digest: "v3:sha256:45675bc77c74895b25e2f7c3ca2adc1619e8d12f59b3469e459e181eae32919d"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Open each real zip (downloaded_examples/USB4145-03-0170-C_REVA2.zip, LIB_RS3-1212S_H3.zip) in the Import dialog of the running GUI, read the preview, install into a scratch copy of Custom/ (or cancel at the preview)."
    expected: "Vendor label shows SnapEDA / SamacSys. A readable 'Field changes' section lists the dropped and cleaned fields. SnapEDA suggests Connector_USB_GCT and warns that no 3D model was found. SamacSys suggests PowerSupply_SubCategory_RECOM, links the model as ${CUSTOM_3DMODEL_DIR}/RS3-1212S_H3.stp and logs one 'Not imported: other-CAD folders ...' line. If committing, the trailer reads Import-Vendor: SnapEDA / SamacSys."
    why_human: "Preview readability and the live dialog look cannot be judged from pytest; the real zips are local-only so no committed GUI test covers them (07-VALIDATION.md manual-only row)."
---

# Phase 7: SnapEDA and SamacSys Adapters Verification Report

**Phase Goal:** SnapEDA and SamacSys / Component Search Engine downloads import through the same flow as Ultra Librarian packages
**Verified:** 2026-10-23
**Status:** human_needed (all automated checks pass; one GUI readability check remains)
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria, the contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Real SnapEDA zip is recognised as SnapEDA; symbol, footprint and any model found; no model gives the "no 3D model found" warning | VERIFIED | My own probe (python -I, outside the test suite) on `downloaded_examples/USB4145-03-0170-C_REVA2.zip`: vendor SnapEDA, confidence 1.0, symbol `USB4145-03-0170-C_REVA2`, footprint `GCT_USB4145-03-0170-C_REVA2`, models (), `intake.no_model` raised, not refused. `test_vendor_install.py:363` asserts `install.no_model` has severity WARNING at plan time. `test_real_snapeda_recognised/installs` pass. |
| 2 | Real SamacSys/CSE zip recognised; KiCad v6+ symbol, footprint and 3D model found; legacy .lib/.dcm ignored, not rejected | VERIFIED | Probe on `LIB_RS3-1212S_H3.zip`: vendor SamacSys, confidence 1.0, symbol `RS3-1212S_H3`, footprint `RS3`, model `RS3-1212S_H3.stp` staged; `legacy_ignored` lists 4 files (.lib/.dcm/.mod incl. CADSTAR); issues: INFO `intake.legacy_ignored`, WARNING `intake.legacy_footprint_syntax`, INFO `intake.ignored_members` "other-CAD folders ... (62 files)"; `len(candidate.ignored) == 62`; no ERROR, not refused. |
| 3 | Each vendor sample installs into a copy of Custom/ with the same `<Lib>:<FP>` link and `${CUSTOM_3DMODEL_DIR}` model path as UL; covered by pytest fixtures (trimmed/synthetic where redistribution forbids) | VERIFIED | `test_real_samacsys_installs` asserts Footprint `PowerSupply_DCDC_RECOM:RS3`, model path `${CUSTOM_3DMODEL_DIR}/RS3-1212S_H3.stp`, file in 3DModels, Manufacturer/MPN, dropped price fields; `test_real_snapeda_installs` likewise; synthetic equivalents in `tests/test_vendor_install.py`; kicad-cli `load_gate` tests (5, `-m kicad_cli`) pass on synthetic and real. Committed fixtures are synthetic (`tests/vendorfixtures.py`), originality guarded by `test_vendorfixtures.py`. |

### Plan must-have truths (spot-verified against code and tests)

| Plan | Key truths | Status | Evidence |
|------|-----------|--------|----------|
| 07-01 | SnapEDAAdapter registered before Loose; Import-Vendor trailer; zips git-ignored | VERIFIED | `detect.py:15` `ADAPTERS = [UltraLibrarianAdapter(), SnapEDAAdapter(), SamacSysAdapter(), LooseAdapter()]`; `git check-ignore -v` ignores both zips (`.gitignore:31`); `git ls-files downloaded_examples` lists only `ul_CSD85301Q2.zip`; `git ls-files` finds no vendor member files |
| 07-02 | Per-adapter FieldRules, volatile drops, FieldChange, Field changes preview section | VERIFIED | `fieldrules.py`, planner `_edit_symbol`, `test_field_cleanup.py` and `test_import_preview.py` pass |
| 07-03 | Alias/placeholder/whitespace cleanup, protected set, MPN fallback | VERIFIED | `test_field_cleanup.py`, `test_import_form.py` (equivalence cases) pass |
| 07-04 | Bounded in-memory markers, how-to-import scoring, np_thru_hole pad skip | VERIFIED | `test_package_zip.py`, `test_snapeda_adapter.py`, `test_install_verify.py` pass; real SnapEDA zip scores 1.0 |
| 07-05 | SamacSys adapter, part_info parsing, D-16 summary line, PartCategory suggestion | VERIFIED | `test_samacsys_adapter.py`, `test_naming_suggest.py` pass; real zip detected at 1.0 with single summary line |
| 07-06 | Vendor installs into synthetic Custom/, fixture originality, real-sample tests, kicad-cli load | VERIFIED | `test_vendor_install.py`, `test_vendorfixtures.py`, `test_real_vendor_samples.py` pass with real zips present (no skips) |

**Score:** 3/3 roadmap criteria verified; 0 behavior-unverified.

### Wiring and Data-Flow

| Link | Status | Details |
|------|--------|---------|
| `widgets/import_dialog.py:1004` -> `core.detect_candidate` -> `ADAPTERS` | WIRED | The dialog calls the same `detect_candidate` as the UL path, so no vendor-specific GUI branch exists; the new adapters flow through the registry |
| Adapter -> Detection.rules -> `ImportCandidate.field_rules` -> planner `is_volatile/is_placeholder` | WIRED | Real zips produce plans with the dropped fields (real-install tests assert absence of `Mouser Price/Stock`, etc.) |
| `Package.markers` -> `marker_text()` -> adapters | WIRED | Real zips reach confidence 1.0 only with markers read |
| Real data (not static) | FLOWING | Probe used real files, no stubs/mocks |

### Behavioral Spot-Checks and Test Runs

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase test files (snapeda, samacsys, real samples, vendor install, fixtures, field cleanup, package zip, layering, suggest, form, preview, adapters, verify) | `pytest -p no:cacheprovider -q` on those files | 332 passed, 1 failed | PASS (the 1 failure is baseline, see below) |
| kicad_cli-marked vendor tests | `pytest -m kicad_cli tests/test_vendor_install.py tests/test_real_vendor_samples.py` | 5 passed | PASS |
| Real-zip detect probe | `env/Scripts/python.exe -I probe.py` | SnapEDA 1.0, SamacSys 1.0, UL still UltraLibrarian 1.0 (no regression) | PASS |

The single failure, `tests/test_import_preview.py::test_rows_reimport_into_the_real_custom_library`, is in the pre-phase baseline set (07-RESEARCH.md line 340: it is one of the 21 known ids), caused by the live `Custom/` submodule already holding the UL CSD85301Q2 part. It is not a phase-7 regression. The orchestrator's full-suite result (1891 passed, 21 failed, 5 skipped, identical id set) corroborates it. I did not re-run the full suite.

### Probe Execution

No `probe-*.sh` scripts are declared or present. Skipped.

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|--------------|-------------|--------|----------|
| INTK-03 | 07-01, 07-02, 07-03, 07-04, 07-06 | SnapEDA zip recognised; symbol, footprint, any 3D model found; verified against a real download | SATISFIED | Real SnapEDA zip detected at 1.0 with symbol and footprint found, no-model warning; real-install test passes |
| INTK-04 | 07-03, 07-05, 07-06 | SamacSys/CSE zip recognised; KiCad symbol, footprint, 3D model found; verified against a real download | SATISFIED | Real SamacSys zip detected at 1.0 with symbol, footprint, model found, legacy files ignored |

Both IDs appear in PLAN frontmatter and in REQUIREMENTS.md (lines 34-35, traceability lines 149-150 mapped to Phase 7). No orphaned requirements. Note: REQUIREMENTS.md still shows both as `[ ]` / "Pending"; the orchestrator should tick them on phase completion (bookkeeping, not a gap).

### Prohibitions (must_haves.prohibitions, all test-tier)

| Prohibition | Enforcement found | Status |
|-------------|-------------------|--------|
| Never commit/stage/copy real vendor bytes (07-01, 07-06) | `test_vendor_zips_stay_local`, `test_fixture_originality`, `test_fixture_members_small`; independently: `.gitignore:31` ignores both zips, `git ls-files` shows only the UL zip, no vendor-named files tracked | RESOLVED (wired, executed and passing) |
| Never drop/clean a property without a FieldChange and preview row (07-02, 07-03) | `test_snapeda_volatile_fields_dropped`, `test_field_changes_section`, `test_snapeda_symbol_cleaned`, `test_field_change_rows` pass | RESOLVED |
| Never alter existing symbols in the target library (07-03) | `test_cleanup_never_touches_existing_symbols` passes | RESOLVED |
| Markers never written to disk (07-04) | `test_markers_held_in_memory_only`; probe shows staging holds only sym/fp/model files | RESOLVED |
| No unmapped PartCategory as Type token; part_info values capped (07-05) | `test_unmapped_category_falls_back`, `test_part_info_parse_caps` pass | RESOLVED |

No unverified prohibitions.

### Anti-Patterns Found

TBD/FIXME/XXX/TODO/HACK scan over `importer/adapters/`, `fieldrules.py`, `package.py`: no matches. No stubs; adapters are substantive and exercised on real data.

Code review (07-REVIEW.md: 0 critical, 4 warning, 4 info) is advisory and recorded in 07-REVIEW-DISPOSITION.md as `open`; none contradicts a must-have:

| Finding | Severity | Impact on goal |
|---------|----------|----------------|
| WR-01 21 baseline test failures from live Custom/ | Warning | Environmental baseline, not caused by phase 7 |
| WR-02 vendor property values in Qt tooltips (rich text auto-detect) | Warning | UI hardening, does not block import |
| WR-03 marker members past MAX_MARKERS dropped silently, archive order | Warning | Only matters for zips with more than 16 marker-named members; real zips unaffected |
| WR-04 SamacSys folder summary file count semantics | Warning | Cosmetic count wording |
| IN-01..IN-04 | Info | Cleanup |

Housekeeping: `07-VALIDATION.md` frontmatter says `nyquist_compliant: false` while its sign-off section says `true` was set; reconcile the frontmatter.

### Human Verification Required

#### 1. Real zips through the live Import dialog

**Test:** Run `.\env\Scripts\python.exe kicad_lib_manager.py`, open the Import dialog, load each real zip from `downloaded_examples/`, review the preview, install into a scratch copy of `Custom/` or cancel at the preview.
**Expected:** Vendor label SnapEDA / SamacSys; readable "Field changes" section; SnapEDA suggests `Connector_USB_GCT` with a no-3D-model warning; SamacSys suggests `PowerSupply_SubCategory_RECOM`, model linked as `${CUSTOM_3DMODEL_DIR}/RS3-1212S_H3.stp`, one "Not imported: other-CAD folders ..." log line; commit trailer reads `Import-Vendor: SnapEDA` / `SamacSys`.
**Why human:** Visual readability of the preview and the live dialog cannot be judged programmatically; the real zips are local-only so no committed test drives the GUI with them. (07-UI-REVIEW.md scored the UI 17/24, advisory.)

### Gaps Summary

No gaps. Both vendors are registered in the shared detection registry that the Import dialog already uses, recognised on the real downloads at confidence 1.0, install with the same `<Lib>:<FP>` link and `${CUSTOM_3DMODEL_DIR}` model path as UL, ignore legacy files without rejection, and keep real vendor bytes out of git. Status is `human_needed` solely because of the manual GUI check recorded in the phase's own validation plan.

---

_Verified: 2026-10-23_
_Verifier: Claude (gsd-verifier)_
