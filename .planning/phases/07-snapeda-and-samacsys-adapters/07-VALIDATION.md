---
phase: "7"
slug: "snapeda-and-samacsys-adapters"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-23"
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-qt 4.5.0 (offscreen), kicad-cli 10.0.7 for `kicad_cli`-marked tests (kicad-cli 9.0.9 also installed) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, markers incl. `kicad_cli`, `addopts = "-ra --strict-markers"`) |
| **Quick run command** | `./env/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_adapters.py tests/test_naming_suggest.py tests/test_import_form.py tests/test_import_preview.py tests/test_install_plan.py`, plus the new test file(s) of the task |
| **Full suite command** | `./env/Scripts/python.exe -m pytest -p no:cacheprovider -q` (baseline before any change: 21 failed, 1799 passed, 5 skipped; the 21 failing ids are listed in RESEARCH.md Pitfall 8 and are the only accepted failures) |
| **Estimated runtime** | ~340 seconds full suite; the quick run is estimated under 60 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick run command, plus the test file(s) the task touches, e.g. `./env/Scripts/python.exe -m pytest -p no:cacheprovider -q tests/test_field_cleanup.py`
- **After every plan wave:** Run the full suite command. The failure set must equal the RESEARCH.md Pitfall 8 baseline, with nothing new. A baseline test that this phase re-baselines (D-09) must be named in the plan that changes it.
- **Before `/gsd-verify-work`:** Full suite compared to the baseline, `./env/Scripts/python.exe -m pytest -p no:cacheprovider -q -m kicad_cli tests/test_vendor_install.py` green, and `git status` shows the two vendor zips ignored
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

Filled in by the planner/executor per task. Requirement → test map from RESEARCH.md:

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| INTK-03 | Synthetic SnapEDA zip → vendor `SnapEDA`, confidence ≥ 0.7, no `intake.unknown_vendor`, `intake.no_model` + `install.no_model` WARNING; renamed two-file variant still recognised | unit | `pytest tests/test_snapeda_adapter.py -q` | ✅ | ✅ green |
| INTK-03 | Real SnapEDA zip recognised (skips with a clear reason if absent) | integration | `pytest tests/test_real_vendor_samples.py -q` | ✅ | ✅ green |
| INTK-04 | Synthetic SamacSys zip → vendor `SamacSys`; legacy `.lib/.dcm/.mod` ignored (INFO), `(module ...)` WARNING, model found, folder summary line, `candidate.ignored` complete, staging dir holds only sym/fp/model files | unit | `pytest tests/test_samacsys_adapter.py -q` | ✅ | ✅ green |
| INTK-04 | Real SamacSys zip recognised (skips with a clear reason if absent) | integration | `pytest tests/test_real_vendor_samples.py -q` | ✅ | ✅ green |
| D-05..D-09 | Drop volatile / placeholder / duplicate-alias fields, collapse Description, protected set (incl. every `ki_*`), `field_changes`, "Field changes" preview section, UL property list unchanged, preview bytes == install bytes | unit | `pytest tests/test_field_cleanup.py tests/test_import_preview.py -q` | ✅ | ✅ green |
| D-09 | `field_defaults` equals planner output, incl. a SnapEDA-shaped case | unit | `pytest tests/test_import_form.py -q` | ✅ | ✅ green |
| D-11/D-12 | `PS`, `recom`/`recompower`, `PartCategory` table, `part_info` source, expected `PowerSupply_SubCategory_RECOM` | unit | `pytest tests/test_naming_suggest.py -q` | ✅ | ✅ green |
| D-13 | Marker caps; oversize/unreadable → INFO, not refusal; parse caps; markers never written | unit | `pytest tests/test_package_zip.py tests/test_samacsys_adapter.py -q` | ✅ | ✅ green |
| Success crit. 3 | Install each vendor into a synthetic `Custom/`: Footprint `<Lib>:<FP>`, model `${CUSTOM_3DMODEL_DIR}/<MPN>.<ext>`, `verify_install` clean | integration | `pytest tests/test_vendor_install.py -q` | ✅ | ✅ green |
| D-04 | kicad-cli `load_gate` on the installed libraries, no format number pinned, skips when kicad-cli is absent | integration (`kicad_cli`) | `pytest -m kicad_cli tests/test_vendor_install.py -q` | ✅ | ✅ green |
| D-01 | Fixtures parse, markers present, originality guard against the real zips (skips if absent), every synthetic member < 4 KiB | unit | `pytest tests/test_vendorfixtures.py -q` | ✅ | ✅ green |
| D-02 | `.gitignore` ignores the two vendor zips and keeps `ul_CSD85301Q2.zip` tracked | scripted | `git check-ignore -v downloaded_examples/LIB_RS3-1212S_H3.zip downloaded_examples/USB4145-03-0170-C_REVA2.zip` and `git ls-files downloaded_examples` | n/a | ✅ green |
| Layering | New importer modules registered; `fieldrules` imports nothing | unit | `pytest tests/test_importer_layering.py tests/test_layering.py -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/vendorfixtures.py` — in-memory synthetic SnapEDA / SamacSys zip builders (D-01), plus `tests/test_vendorfixtures.py` self-checks
- [x] `tests/test_snapeda_adapter.py` — covers INTK-03 recognition on synthetic zips
- [x] `tests/test_samacsys_adapter.py` — covers INTK-04 recognition, legacy handling, D-13, D-16
- [x] `tests/test_field_cleanup.py` — covers D-05..D-09 with `ToolContext()` (no kicad-cli, RESEARCH.md Pitfall 9)
- [x] `tests/test_vendor_install.py` — success criterion 3 and D-04 on a synthetic `Custom/` (D-03)
- [x] `tests/test_real_vendor_samples.py` — D-02 real-sample tests, skipped by file name when absent
- [x] Existing tests that change with the code, in the plan that changes them: `test_adapters.py` registry lists (lines 50 and 413), `test_install_plan.py::test_fields_exact_manufacturer_kept` (D-08), `test_import_preview.py` `ORDER` (line 34) and section-name lists, `test_importer_layering.py` `ALLOWED`, `test_import_form.py::test_field_defaults_equivalence` (new SnapEDA case), optionally `test_import_dialog.py` `test_vendor_labels`

Framework install: none (pytest, pytest-qt and kicad-cli already present).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Both real downloads import through the GUI with the right vendor label, a readable "Field changes" preview and the expected names | INTK-03, INTK-04 | The real zips are local only (D-01/D-02), and preview readability needs a human | Open each real zip from `downloaded_examples/` in the Import dialog. Confirm the vendor shows as `SnapEDA` / `SamacSys`, and the "Field changes" section lists the dropped and cleaned fields. Confirm SnapEDA suggests `Connector_USB_GCT` and warns that no 3D model was found. Confirm SamacSys suggests `PowerSupply_SubCategory_RECOM`, the model links as `${CUSTOM_3DMODEL_DIR}/RS3-1212S_H3.stp`, and the log shows one "Not imported: other-CAD folders ..." line. Install into a scratch copy of `Custom/`, or cancel at the preview. If committing, check that the trailer reads `Import-Vendor: SnapEDA` / `SamacSys`. |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-10-23 (validate-phase audit after execution: 13/13 rows green in the main checkout with both real zips and kicad-cli present, no skips; full suite 1891 passed, failures identical to the 21-id baseline)

## Validation Audit 2026-10-23

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
