---
phase: "01"
slug: "foundation"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-18"
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-qt 4.5.0 (PySide6 6.12.0, `QT_QPA_PLATFORM=offscreen`) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`): none yet, Wave 0 creates it |
| **Quick run command** | `.\env\Scripts\python.exe -m pytest tests\test_sexpr.py tests\test_fsutil.py tests\test_kicad_files.py tests\test_models.py -x -q` |
| **Full suite command** | `.\env\Scripts\python.exe -m pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick run command for the touched module
- **After every plan wave:** Run `.\env\Scripts\python.exe -m pytest`
- **Before `/gsd-verify-work`:** Full suite must be green, plus the fresh-venv install run (SC1)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {N}-01-01 | 01 | 1 | REQ-{XX} | T-{N}-01 / — | {expected secure behavior or "N/A"} | unit | `{command}` | ✅ / ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `.gitattributes` (commit `.gitattributes` before any fixture is staged)
- [ ] `tests/conftest.py`: forced offscreen platform, repo-root and corpus-discovery fixtures
- [ ] `tests/test_manifests.py`, `tests/test_library_table_widget.py`, `tests/test_models.py`, `tests/test_layering.py`
- [ ] `tests/test_sexpr.py`, `tests/test_roundtrip_corpus.py`, `tests/test_edits.py`, `tests/test_kicad_files.py`, `tests/test_fsutil.py`
- [ ] `tests/fixtures/sexpr/*` created byte-exact (LF, CRLF, BOM, mixed EOL, parens and escaped quotes in strings, bare atoms, no trailing newline)
- [ ] `tests/fixtures/tables/*.sym-lib-table` / `*.fp-lib-table` (not named bare `sym-lib-table` / `fp-lib-table`, which `.gitignore` ignores)
- [ ] `downloaded_examples/ul_CSD85301Q2.zip` tracked by explicit path
- [ ] `pytest-qt` installed: `.\env\Scripts\python.exe -m pip install -r requirements-dev.txt`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Fresh venv installs pinned deps and `pytest` is green with no display (SC1) | FOUND-01 | Needs a throwaway venv outside the repo and network access to PyPI | `py -m venv $env:TEMP\f1 ; & $env:TEMP\f1\Scripts\python.exe -m pip install -r requirements-dev.txt ; & $env:TEMP\f1\Scripts\pytest.exe` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
