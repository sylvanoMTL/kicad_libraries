---
phase: "02"
slug: "hardening-existing-code"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-18"
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-qt 4.5.0 (PySide6 6.12.0, offscreen forced in `tests/conftest.py`) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths=["tests"]`, `qt_api="pyside6"`, `addopts="-ra --strict-markers"`, markers `wurth`, `local_kicad`) |
| **Quick run command** | `./env/Scripts/python.exe -m pytest tests/test_table_merge.py -x -q` (swap in the single test file for the module being changed) |
| **Full suite command** | `./env/Scripts/python.exe -m pytest -q` |
| **Estimated runtime** | ~7 seconds (baseline before this phase: 353 passed, 2 skipped in 6.3 s) |

---

## Sampling Rate

- **After every task commit:** Run the single test file for the module being changed (about 1-3 s each)
- **After every plan wave:** Run `./env/Scripts/python.exe -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green, plus the HARD-09 live scan check and `git -C Custom diff --stat` evidence
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | REQ-{XX} | T-02-01 / — | {expected secure behavior or "N/A"} | unit | `{command}` | ✅ / ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_table_merge.py`, `tests/test_write_tables.py` (HARD-01, HARD-02, HARD-06)
- [ ] `tests/test_kicad_config.py` with the synthetic `kicad_common.json` variants (`vars` null, populated, CRLF, BOM) generated inside the tests with `json.dumps(obj, indent=2, ensure_ascii=False) + "\n"` and written to `tmp_path` (plan 02-04). No committed `tests/fixtures/kicad/` directory: the frozen-fixture checks in `tests/test_fixtures.py` parse every fixture as an S-expression, which JSON is not.
- [ ] `tests/test_kicad_process.py` (monkeypatch `subprocess.run`)
- [ ] `tests/test_scanner_issues.py` (nickname collisions, model path rules, live `Custom/` check)
- [ ] `tests/test_main_window.py` + conftest fixtures: autouse `QSettings.setPath` redirect, window factory with patched `load_kicad_fp_dir`, `REPO_ROOT` and `scan_all`
- [ ] `tests/test_log_panel.py`
- [ ] Extend `tests/test_library_table_widget.py` (`_fp_item` helper keyed by `rel_path`), `tests/test_kicad_files.py` / `tests/test_edits.py`, `tests/test_fsutil.py` (`number=`, WR-04, IN-01), `tests/test_scanner_skip_dirs.py` (Issues), `tests/test_layering.py`
- [ ] Framework install: none needed (Phase 1 harness covers it)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `Custom` model-path cleanup commit approved and preserved | HARD-09 | Git commits need the owner's explicit confirmation, and the new commit lives only in this worktree's private module gitdir until `Custom/main` is pushed | Check `git -C Custom diff --stat` shows exactly 5 files with 1 insertion and 1 deletion each, approve the commit, then push `Custom/main` before removing the worktree |

GUI UAT caution: pressing Generate from this worktree against the real `%APPDATA%\kicad\<version>\kicad_common.json` repoints `KICAD_LIB_GITHUB` at the worktree path (a backup is made first). Only do it on purpose.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
