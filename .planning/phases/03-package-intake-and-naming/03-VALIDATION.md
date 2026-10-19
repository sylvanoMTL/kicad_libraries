---
phase: "3"
slug: "package-intake-and-naming"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-19"
validated: "2026-10-19"
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (pytest-qt 4.5.0 installed; Phase 3 tests need no Qt) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`, `addopts = "-ra --strict-markers"`) |
| **Quick run command** | `./env/Scripts/python.exe -m pytest tests/test_package_zip.py tests/test_adapters.py tests/test_naming_sanitize.py tests/test_naming_suggest.py -q` |
| **Full suite command** | `./env/Scripts/python.exe -m pytest -q` |
| **Estimated runtime** | ~18 seconds (773 passed / 4 skipped after Phase 3) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (or the task's own targeted test file)
- **After every plan wave:** Run `./env/Scripts/python.exe -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-T1 | 03-01 | 1 | INTK-01, INTK-02 | staging outside repo | UL zip staged outside the repo, no bulk extraction | unit (real fixture) | `./env/Scripts/python.exe -m pytest tests/test_adapters.py -x -q -k ultra` | ✅ | ✅ green |
| 03-01-T2 | 03-01 | 1 | LIB-01 | — | N/A | unit (real fixture) | `./env/Scripts/python.exe -m pytest tests/test_adapters.py -x -q -k ultra` | ✅ | ✅ green |
| 03-02-T1 | 03-02 | 1 | INTK-01 | — | Hostile/lying zip builders, D-17 unpacker | unit | `./env/Scripts/python.exe -m pytest tests/test_zipfixtures.py -x -q` | ✅ | ✅ green |
| 03-02-T2 | 03-02 | 1 | INTK-01 | — | N/A | unit | `./env/Scripts/python.exe -m pytest tests/test_zipfixtures.py tests/test_kicad_files.py -x -q` | ✅ | ✅ green |
| 03-02-T3 | 03-02 | 1 | (layering) | — | No Qt, no `extract`/`extractall` in `importer/` | static | `./env/Scripts/python.exe -m pytest tests/test_importer_layering.py tests/test_layering.py -x -q -rs` | ✅ | ✅ green |
| 03-03-T1 | 03-03 | 2 | INTK-06 | zip-slip / duplicate / encrypted | Whole package refused before any byte is read | unit (synthetic) | `./env/Scripts/python.exe -m pytest tests/test_package_zip.py -x -q -k "hostile or duplicate or encrypted"` | ✅ | ✅ green |
| 03-03-T2 | 03-03 | 2 | INTK-06 | zip-bomb / nested zip | Caps on declared and real bytes, one-level nesting, staging cleanup | unit (synthetic) | `./env/Scripts/python.exe -m pytest tests/test_package_zip.py tests/test_adapters.py tests/test_importer_layering.py -x -q` | ✅ | ✅ green |
| 03-04-T1 | 03-04 | 2 | INTK-01, INTK-02 | lying extension | Content checked against extension, reads capped | unit | `./env/Scripts/python.exe -m pytest tests/test_kicad_files.py tests/test_adapters.py tests/test_layering.py tests/test_importer_layering.py -x -q` | ✅ | ✅ green |
| 03-04-T2 | 03-04 | 2 | INTK-05 | — | N/A | unit (synthetic + real UL loose files) | `./env/Scripts/python.exe -m pytest tests/test_legacy_rules.py tests/test_adapters.py tests/test_importer_layering.py -x -q` | ✅ | ✅ green |
| 03-05-T1 | 03-05 | 2 | LIB-03 | path traversal via names | Reserved/illegal names sanitised | unit | `./env/Scripts/python.exe -m pytest tests/test_naming_sanitize.py tests/test_importer_layering.py -x -q` | ✅ | ✅ green |
| 03-05-T2 | 03-05 | 2 | LIB-03 | path traversal via names | `sanitize_filename`, `case_clash` | unit | `./env/Scripts/python.exe -m pytest tests/test_naming_sanitize.py tests/test_importer_layering.py -x -q` | ✅ | ✅ green |
| 03-05-T3 | 03-05 | 2 | LIB-03 | — | `name_check` on every candidate item | unit | `./env/Scripts/python.exe -m pytest tests/test_candidate_names.py tests/test_naming_sanitize.py tests/test_adapters.py tests/test_importer_layering.py -x -q` | ✅ | ✅ green |
| 03-06-T1 | 03-06 | 3 | LIB-01 | — | Read-only `Custom/` listing | unit | `./env/Scripts/python.exe -m pytest tests/test_naming_suggest.py tests/test_adapters.py tests/test_importer_layering.py -x -q` | ✅ | ✅ green |
| 03-06-T2 | 03-06 | 3 | LIB-01 | — | Sanitise and case-clash pass, D-04 placeholders | unit (synthetic + live `Custom/`) | `./env/Scripts/python.exe -m pytest tests/test_naming_suggest.py tests/test_naming_sanitize.py tests/test_adapters.py tests/test_importer_layering.py -x -q` | ✅ | ✅ green |
| 03-07-T1 | 03-07 | 3 | INTK-01 | symlink / junction / depth | Folder read in place, read-only, links skipped, caps | unit | `./env/Scripts/python.exe -m pytest tests/test_package_folder.py tests/test_package_zip.py tests/test_importer_layering.py -x -q -rs` | ✅ | ✅ green |
| 03-07-T2 | 03-07 | 3 | INTK-01, INTK-02 | — | Folder and unzipped UL give the same candidate as the zip | unit (real UL files) | `./env/Scripts/python.exe -m pytest tests/test_package_folder.py tests/test_package_zip.py tests/test_adapters.py tests/test_legacy_rules.py tests/test_importer_layering.py -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Environment note: `test_folder_symlink_skipped` skips on accounts without the Windows symlink privilege (WinError 1314). The symlink branch is still covered by a fake-entry unit test, and the junction test runs.

---

## Wave 0 Requirements

- [x] `tests/test_package_zip.py`, `tests/test_package_folder.py`, `tests/test_adapters.py`, `tests/test_legacy_rules.py`, `tests/test_naming_sanitize.py`, `tests/test_naming_suggest.py`, `tests/test_importer_layering.py` — new
- [x] `tests/zipfixtures.py` — UL sample unpacker, zip builders, `lie_about_size`, `mark_encrypted` helpers (plain helper module, not conftest fixtures)
- [x] Synthetic `Custom/` layout builder (`Symbols/*.kicad_sym`, `Footprints/*.pretty`, `3DModels/`)
- [x] Framework install: none (pytest already pinned)

---

## Manual-Only Verifications

All phase behaviors have automated verification (D-14: Phase 3 is verified by tests only).

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-19

## Validation Audit 2026-10-19

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
