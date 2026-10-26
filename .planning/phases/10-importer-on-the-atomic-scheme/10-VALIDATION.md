---
phase: "10"
slug: "importer-on-the-atomic-scheme"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-26"
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 with pytest-qt 4.5.0 (`qtbot`), offscreen Qt forced in `tests/conftest.py` |
| **Config file** | `pyproject.toml` (`testpaths = ["tests"]`, `pythonpath = ["."]`, `addopts = "-ra --strict-markers"`, markers `wurth`, `local_kicad`, `kicad_cli`) |
| **Quick run command** | `env/Scripts/python.exe -m pytest tests/<file>.py -q` (the test files named in the task) |
| **Full suite command** | `env/Scripts/python.exe -m pytest` (`-m "not wurth"` for the per-wave run) |
| **Estimated runtime** | seconds per task file; ~8 min `-m "not wurth"`; ~18 min full |

---

## Sampling Rate

- **After every task commit:** Run the test files named in that task's `<automated>` command
- **After every plan wave:** Run `env/Scripts/python.exe -m pytest -m "not wurth" -q`
- **Before `/gsd-verify-work`:** Full suite must be green, with only the skips documented in `tests/README.md`
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

Task rows are added from the PLAN.md files once planning completes (and confirmed by `/gsd-validate-phase 10`). The requirement-level map from `10-RESEARCH.md` § Validation Architecture is the starting point:

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| LIB-04 | family prefixes, strict majority, excluded stems, own-before-stock, category map, ask, no manufacturer name | unit (synthetic stock dir) | `env/Scripts/python.exe -m pytest tests/test_suggest_atomic.py -q` | ❌ W0 | ⬜ pending |
| LIB-04 | CSD → `Atomic_Transistor_FET`, RS3 → `Atomic_Converter_DCDC_Isolated`, ATXK asks, USB → `Atomic_Connector` | real-sample (skips without KiCad 10 or the zip) | `env/Scripts/python.exe -m pytest tests/test_real_vendor_samples.py -q` | ✅ retarget | ⬜ pending |
| LIB-04 | every category-map target is an allowed stem; snapshot equals installed KiCad 10 stems | unit + `local_kicad` | `env/Scripts/python.exe -m pytest tests/test_stems.py -q` | ❌ W0 | ⬜ pending |
| LIB-05 | exact, case-corrected and refused names (`Transistor_FET`, `Atomic_TI`, v1 names, excluded stems); picker order and filter | unit + dialog | `env/Scripts/python.exe -m pytest tests/test_stems.py tests/test_import_dialog.py -q` | ❌ W0 / ✅ migrate | ⬜ pending |
| LIB-06 | footprint in `Atomic_Footprints`, no `.pretty` for a new symbol library, official link, D-19 identical/overwrite/rename, tables | plan/apply/e2e | `env/Scripts/python.exe -m pytest tests/test_install_plan.py tests/test_install_apply.py tests/test_install_e2e.py tests/test_table_add_entries.py -q` | ✅ migrate | ⬜ pending |
| LIB-06 | pad check warning, verify with an official link | unit | `env/Scripts/python.exe -m pytest tests/test_install_verify.py -q` | ✅ migrate | ⬜ pending |
| LIB-07 | incoming gate: one ERROR per rule, planned footprint/model seen, reasons with targets, live clear | plan + form + dialog | `env/Scripts/python.exe -m pytest tests/test_incoming_check.py tests/test_import_form.py tests/test_import_dialog.py -q` | ❌ W0 / ✅ migrate | ⬜ pending |
| FLD-01 | keyword sources, merge and de-duplication, junk dropped, MPN variants | unit | `env/Scripts/python.exe -m pytest tests/test_keywords.py -q` | ❌ W0 | ⬜ pending |
| FLD-03 | pitch, body, family, description and tags on the 5 real footprints + stock SOIC-8/Texas_DQK; `descr`/`tags` insertion on `footprint` and `module` roots | unit + `kicad_cli` | `env/Scripts/python.exe -m pytest tests/test_footprint_text.py -q` | ❌ W0 | ⬜ pending |
| all | layering for every new module | static | `env/Scripts/python.exe -m pytest tests/test_importer_layering.py tests/test_layering.py -q` | ✅ extend | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_stems.py` — snapshot vs installed KiCad 10 (skips without), name verdict table, category-map targets
- [ ] `tests/test_suggest_atomic.py` and a synthetic stock KiCad dir builder (`tests/stockfixtures.py`: small `symbols/*.kicad_sym` and `footprints/*.pretty` trees) so no unit test depends on the installed KiCad
- [ ] `tests/test_incoming_check.py`, `tests/test_keywords.py`, `tests/test_footprint_text.py`
- [ ] Fixture migration: Atomic counterparts of `CURRENT_CUSTOM_SYMBOL_LIBS` / `CURRENT_CUSTOM_FOOTPRINT_LIBS` and an `Atomic_Footprints.pretty` in `write_custom_layout` (`tests/zipfixtures.py`)
- [ ] Every new importer module registered in `ALLOWED` of `tests/test_importer_layering.py` (owned by plan 10-01); `tests/test_layering.py` needs no edit, since no Phase 10 change adds a top-level `kicad_lib_manager` import (recorded per plan), and it runs as a guard
- [ ] `tests/test_naming_suggest.py` retargeted to the new API, keeping the `datasheet_host` / `registered_domain` / `is_aggregator_host` tests
- [ ] `tests/test_help_dialog.py` updated for the rewritten "Target library" and "Items" help text
- [ ] RECOM suggestion expectation retargeted: `PowerSupply_SubCategory_RECOM` → `Atomic_Converter_DCDC_Isolated` in `tests/test_real_vendor_samples.py` and `tests/test_samacsys_adapter.py` (owned by plan 10-15); the `tests/test_atomic_uat.py` scratch builder only needs a change if a plan alters what it builds

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Library picker, suggestion tooltip, footprint destination toggle and official-footprint picker read correctly on the real samples | LIB-04, LIB-05, LIB-06 | Visual judgement on the owner's own downloads | Open each sample in `downloaded_examples/` in the import dialog against a scratch copy of `Custom/`; check the suggested library and its tooltip, type a refused name, switch the footprint destination, pick an official footprint |
| Installed part loads in KiCad with the previewed keywords, footprint description and tags | FLD-01, FLD-03, LIB-07 | Needs KiCad's own Symbol and Footprint Editors | Install one sample into the scratch copy, open it in KiCad 10, compare Keywords, footprint Description and Tags with what the preview showed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
