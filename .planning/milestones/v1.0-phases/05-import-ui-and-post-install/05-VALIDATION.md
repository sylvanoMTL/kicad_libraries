---
phase: "5"
slug: "import-ui-and-post-install"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-20"
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-qt 4.5.0 (`qt_api = "pyside6"`, offscreen via `tests/conftest.py`) |
| **Config file** | `pyproject.toml` (`testpaths = ["tests"]`, `pythonpath = ["."]`, `addopts = "-ra --strict-markers"`) |
| **Quick run command** | `./env/Scripts/python.exe -m pytest tests/test_import_preview.py tests/test_install_options_clear.py tests/test_table_add_entries.py tests/test_import_dialog.py tests/test_main_window_import.py -x -q` |
| **Full suite command** | `./env/Scripts/python.exe -m pytest -q` |
| **Estimated runtime** | ~110 seconds (baseline 1345 passed, 5 skipped in 106 s) |

---

## Sampling Rate

- **After every task commit:** Run the touched test file(s), e.g. `./env/Scripts/python.exe -m pytest tests/test_import_preview.py -x -q`
- **After every plan wave:** Run the quick run command plus `tests/test_main_window.py tests/test_install_plan.py tests/test_importer_layering.py tests/test_layering.py`
- **Before `/gsd-verify-work`:** Full suite must be green, then the manual UAT below
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

Filled in by the planner/executor per task. Requirement → test map from RESEARCH.md:

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| INTK-07 | Picker choices become `InstallOptions` (first checked footprint linked, "No model" → `no_model=True`, never blank) | unit + pytest-qt | `pytest tests/test_import_dialog.py -k picker -x` | ❌ W0 | ⬜ pending |
| PREV-01 | Files (+/~/=), renames, rewrites rows from a real UL plan | unit | `pytest tests/test_import_preview.py -k rows -x` | ❌ W0 | ⬜ pending |
| PREV-02/03 | Footprint name / library edit updates `<Lib>:<FP>` from the rebuilt plan | pytest-qt | `pytest tests/test_import_dialog.py -k footprint_field -x` | ❌ W0 | ⬜ pending |
| PREV-04 | Field defaults equal planner output; clear semantics; Value/MPN block | unit | `pytest tests/test_import_preview.py tests/test_install_options_clear.py -x` | ❌ W0 | ⬜ pending |
| PREV-05 | Per-conflict resolution, no bulk control, carry-over by key | unit + pytest-qt | `pytest tests/test_import_preview.py -k carry tests/test_import_dialog.py -k conflict -x` | ❌ W0 | ⬜ pending |
| PREV-06 | Format rows for normalise / as-is / CLI not found / newer refused | unit | `pytest tests/test_import_preview.py -k format -x` | ❌ W0 | ⬜ pending |
| PREV-07 | Install uses the latest plan object; disabled while updating; superseded result discarded | pytest-qt | `pytest tests/test_import_dialog.py -k supersede -x` | ❌ W0 | ⬜ pending |
| POST-01 | Post-install rescan once; installed library checked/expanded/current; other selection kept | pytest-qt | `pytest tests/test_main_window_import.py -k select -x` | ❌ W0 | ⬜ pending |
| POST-02 | New library: add-only helper adds exactly 2 entries, other bytes kept; existing library: WARNING | unit + pytest-qt | `pytest tests/test_table_add_entries.py tests/test_main_window_import.py -k tables -x` | ❌ W0 | ⬜ pending |
| POST-05 | KiCad running → notice + log WARNING; not running → none | pytest-qt | `pytest tests/test_import_dialog.py -k kicad_running -x` | ❌ W0 | ⬜ pending |
| UX-01 | Drop zip/folder opens dialog; multi/wrong type/busy refused with log line | pytest-qt | `pytest tests/test_main_window_import.py -k drop -x` | ❌ W0 | ⬜ pending |
| UX-02 | `import/last_dir` round trip; newest-zip offer and age; missing Downloads | unit + pytest-qt | `pytest tests/test_import_dialog.py -k start_page tests/test_settings_import.py -x` | ❌ W0 | ⬜ pending |
| Phase 3 D-04 | Install disabled with reason while placeholder tokens remain | pytest-qt | `pytest tests/test_import_dialog.py -k placeholder -x` | ❌ W0 | ⬜ pending |
| WR-02 | Library creation with missing `Custom/Symbols` refused early | unit | `pytest tests/test_install_plan.py -k symbols_missing -x` | ❌ W0 | ⬜ pending |
| WR-06 | No candidate → package + detection Issues reach the UI and log | pytest-qt | `pytest tests/test_import_dialog.py -k nothing_found -x` | ❌ W0 | ⬜ pending |
| Layering | New importer module registered; no Qt in importer | unit | `pytest tests/test_importer_layering.py tests/test_layering.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_import_preview.py` — rows, defaults equivalence, blocking reasons, diff text and truncation, carry-over
- [ ] `tests/test_install_options_clear.py` (or extend `tests/test_install_plan.py`) — cleared semantics, Manufacturer fix, Value/MPN refusal, old tests unchanged
- [ ] `tests/test_table_add_entries.py` — byte preservation, idempotence, missing file, read-only table
- [ ] `tests/test_import_dialog.py`, `tests/test_main_window_import.py`, `tests/test_settings_import.py`
- [ ] Register new importer module(s) in `tests/test_importer_layering.py::ALLOWED`
- [ ] Conftest fixture injecting fake core callables and an isolated QSettings

Framework install: none (pytest-qt already present).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Full UL-sample import into the real `Custom/` | All | Real KiCad, real repo, visual check | Import `downloaded_examples/ul_CSD85301Q2.zip`: placeholder block → pick/type library → resolve conflicts → Install → trees select the library → tables gain entries for a new library → KiCad-running notice |
| Layout at 100 % and 150 % scaling | UI-SPEC | Display scaling not reproducible offscreen | Open the dialog at both scalings; no clipped names, no horizontal scrollbar at 900x600 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
