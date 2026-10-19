---
phase: "3"
slug: "package-intake-and-naming"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-19"
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
| **Estimated runtime** | ~15 seconds (baseline 553 passed / 3 skipped in ~11 s, plus new tests) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (or the task's own targeted test file)
- **After every plan wave:** Run `./env/Scripts/python.exe -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Requirement-level map from RESEARCH.md. The planner/executor refine it to task IDs.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | INTK-01 | — | Folder read in place, read-only | unit | `./env/Scripts/python.exe -m pytest tests/test_package_folder.py tests/test_adapters.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INTK-02 | — | N/A | unit (real fixture) | `./env/Scripts/python.exe -m pytest tests/test_adapters.py -k ultra -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INTK-05 | — | N/A | unit (synthetic) | `./env/Scripts/python.exe -m pytest tests/test_legacy_rules.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INTK-06 | zip-slip / zip-bomb / symlink | Hostile zip refused whole, nothing staged, staging outside repo, cleanup | unit (synthetic) | `./env/Scripts/python.exe -m pytest tests/test_package_zip.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LIB-01 | — | N/A | unit | `./env/Scripts/python.exe -m pytest tests/test_naming_suggest.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LIB-03 | path traversal via names | Reserved/illegal names sanitised | unit | `./env/Scripts/python.exe -m pytest tests/test_naming_sanitize.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | (layering) | — | No Qt, no `extractall` in `importer/` | static | `./env/Scripts/python.exe -m pytest tests/test_importer_layering.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_package_zip.py`, `tests/test_package_folder.py`, `tests/test_adapters.py`, `tests/test_legacy_rules.py`, `tests/test_naming_sanitize.py`, `tests/test_naming_suggest.py`, `tests/test_importer_layering.py` — new
- [ ] `tests/conftest.py` (or `tests/zipfixtures.py`) — `ul_zip` fixture, `make_zip`, `symlink_info`, `lie_about_size` helpers
- [ ] Synthetic `Custom/` layout builder fixture (`Symbols/*.kicad_sym`, `Footprints/*.pretty`, `3DModels/`)
- [ ] Framework install: none (pytest already pinned)

---

## Manual-Only Verifications

All phase behaviors have automated verification (D-14: Phase 3 is verified by tests only).

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
