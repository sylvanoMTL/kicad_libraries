---
phase: "02"
slug: "hardening-existing-code"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-18"
validated: "2026-10-19"
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
| 02-01-01 | 01 | 1 | HARD-01 | — | Generate keeps hand-made entries byte-identical | integration | `pytest tests/test_main_window.py tests/test_kicad_files.py -x -q` | ✅ | ✅ green |
| 02-01-02 | 01 | 1 | HARD-01, HARD-02, HARD-06 | — | Restore as Issues; lossless table_info; rel_path pre-selection | unit + GUI | `pytest tests/test_table_merge.py tests/test_write_tables.py tests/test_main_window.py -x -q` | ✅ | ✅ green |
| 02-08-01 | 08 | 1 | HARD-02 | — | fsutil failures are Issues, never exceptions | unit | `pytest tests/test_fsutil.py -x -q` | ✅ | ✅ green |
| 02-08-02 | 08 | 1 | HARD-01 (D-11) | — | Single table-generation path (legacy CLI gone) | structural | `test ! -e generate_lib_tables.py && pytest -q` | ✅ | ✅ green |
| 02-03-01 | 03 | 2 | HARD-01, HARD-06 | — | Every table child classified; unsafe merges refused | unit | `pytest tests/test_table_merge.py tests/test_kicad_files.py tests/test_edits.py -x -q` | ✅ | ✅ green |
| 02-03-02 | 03 | 2 | HARD-02 | — | Independent table writes; shared backup number | unit | `pytest tests/test_write_tables.py tests/test_fsutil.py -x -q` | ✅ | ✅ green |
| 02-09-01 | 09 | 2 | HARD-08 | — | Scan findings as Issues | unit + GUI | `pytest tests/test_log_panel.py tests/test_scanner_skip_dirs.py tests/test_models.py tests/test_main_window.py tests/test_library_table_widget.py -x -q` | ✅ | ✅ green |
| 02-09-02 | 09 | 2 | HARD-08 | — | Nickname collisions reported, peers recorded | unit | `pytest tests/test_scanner_issues.py -x -q -k collision` | ✅ | ✅ green |
| 02-02-01 | 02 | 3 | HARD-07 | — | Items keyed by rel_path; populate never re-syncs | widget | `pytest tests/test_library_table_widget.py -x -q` | ✅ | ✅ green |
| 02-02-02 | 02 | 3 | HARD-08 | — | Same-nickname libraries mutually exclusive | widget | `pytest tests/test_library_table_widget.py -x -q` | ✅ | ✅ green |
| 02-04-01 | 04 | 3 | HARD-04 | — | Newest KiCad version chosen numerically | unit | `pytest tests/test_kicad_config.py -x -q -k "version or config_dir or footprint_dir"` | ✅ | ✅ green |
| 02-04-02 | 04 | 3 | HARD-03 | — | kicad_common.json verified, backed up, atomic | unit | `pytest tests/test_kicad_config.py tests/test_kicad_process.py -x -q` | ✅ | ✅ green |
| 02-04-03 | 04 | 3 | HARD-02, HARD-03 | — | Config sync Issues logged by severity; services Qt-free | GUI + structural | `pytest tests/test_main_window.py tests/test_layering.py -x -q` | ✅ | ✅ green |
| 02-05-01 | 05 | 4 | HARD-09 | — | Span-only model-path edit | unit | `pytest tests/test_edits.py tests/test_kicad_files.py -x -q` | ✅ | ✅ green |
| 02-05-02 | 05 | 4 | HARD-09 | — | Per-source model-path rules | unit + live | `pytest tests/test_scanner_issues.py tests/test_scanner_skip_dirs.py -x -q -rs` | ✅ | ✅ green |
| 02-06-01 | 06 | 4 | HARD-05 | — | Overlapping scans refused; controls disabled while busy | GUI (gated QThread) | `pytest tests/test_main_window.py -x -q` | ✅ | ✅ green |
| 02-06-02 | 06 | 4 | HARD-07, HARD-08 | — | Selection re-applied by rel_path on rescan | GUI | `pytest tests/test_main_window.py tests/test_library_table_widget.py -x -q` | ✅ | ✅ green |
| 02-07-01 | 07 | 5 | HARD-09 | — | Five legacy paths rewritten span-only | live scan | `pytest tests/test_scanner_issues.py -q -k live` (durable form; the original pre-commit numstat check was one-time) | ✅ | ✅ green |
| 02-07-02 | 07 | 5 | HARD-09 | — | Owner approves the Custom commit | checkpoint | — | n/a | manual (approved 2026-10-19) |
| 02-07-03 | 07 | 5 | HARD-09 | — | Custom commit + gitlink bump, never pushed | git state + live | `pytest tests/test_scanner_issues.py -q -k live -rs` (git half hard-codes origin/main=6b1fcb4: one-time) | ✅ | ✅ green |

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
| `Custom` model-path cleanup commit approved and preserved | HARD-09 | Git commits need the owner's explicit confirmation, and the new commit lives only in this worktree's private module gitdir until `Custom/main` is pushed | Approved 2026-10-19 (Custom `485d530`, 5 files 1/1). Still pending: `git -C Custom push origin main` before removing the worktree |
| Real GUI: press Rescan / Ctrl+Shift+R during the startup scan | HARD-05 | Tests drive the handlers against a real gated QThread; a physical click is UAT only | Launch the GUI, press Rescan while the startup scan runs: one "A scan is already running" info line, no crash, controls greyed until done |
| Real KiCad loads a table entry containing `"` or `\` | HARD-06 (optional) | Tests prove the round trip through the project's own parser, not KiCad's | Generate a table with such a name into a scratch dir and open it in KiCad's library manager |
| Busy guard for the post-import rescan | HARD-05 (forward) | The importer's rescan trigger does not exist until Phase 3/4 | Add a busy test in `tests/test_main_window.py` when that path is built |

GUI UAT caution: pressing Generate from this worktree against the real `%APPDATA%\kicad\<version>\kicad_common.json` repoints `KICAD_LIB_GITHUB` at the worktree path (a backup is made first). Only do it on purpose.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (only 02-07-02, a checkpoint, has none)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (every listed test file exists and runs green)
- [x] No watch-mode flags
- [x] Feedback latency < 30s (full suite 553 passed, 3 skipped in ~11 s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-10-19 (validate-phase, no gaps)

## Validation Audit 2026-10-19

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
