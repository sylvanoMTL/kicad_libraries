---
phase: "01"
slug: "foundation"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-18"
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-qt 4.5.0 (PySide6 6.12.0, `QT_QPA_PLATFORM=offscreen`) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, markers `wurth`, `local_kicad`, `--strict-markers`) |
| **Quick run command** | `./env/Scripts/python.exe -m pytest tests/test_sexpr.py tests/test_fsutil.py tests/test_kicad_files.py tests/test_models.py -x -q` (forward slashes work in Git Bash and PowerShell) |
| **Full suite command** | `./env/Scripts/python.exe -m pytest` (or bare `./env/Scripts/pytest.exe`) |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run the quick run command for the touched module
- **After every plan wave:** Run `./env/Scripts/python.exe -m pytest`
- **Before `/gsd-verify-work`:** Full suite must be green, plus the fresh-venv install run (SC1)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | FOUND-04 | T-01-01, T-01-02 | One value edit changes only its span, CRLF kept, atomic write leaves no temp | tracer (end-to-end) | `./env/Scripts/python.exe -m pytest tests/test_edits.py -x -q` | ✅ | ✅ green |
| 01-01-02 | 01 | 1 | FOUND-01, FOUND-02 | T-01-SC | Exact pins installed; bare pytest imports the package; strict markers | unit / smoke | `./env/Scripts/python.exe -m pytest tests/test_manifests.py -x -q` and `./env/Scripts/pytest.exe --collect-only -q` | ✅ | ✅ green |
| 01-01-03 | 01 | 1 | FOUND-02 | T-01-04, T-01-05 | Offscreen Qt widget test; UL zip tracked by explicit path with pinned SHA-256 | integration (Qt) | `./env/Scripts/python.exe -m pytest tests/test_library_table_widget.py -x -q` | ✅ | ✅ green |
| 01-02-01 | 02 | 2 | FOUND-05 | T-01-06, T-01-09, T-01-10 | Read-only / locked / OSError / concurrent writes return Issues, original intact, no temp | unit | `./env/Scripts/python.exe -m pytest tests/test_fsutil.py -x -q` | ✅ | ✅ green |
| 01-02-02 | 02 | 2 | FOUND-05, FOUND-04 | T-01-07 | Backups go to a caller-chosen / off-repo dir; EOL x BOM identity; strict UTF-8 | unit | `./env/Scripts/python.exe -m pytest tests/test_fsutil.py tests/test_models.py -x -q` | ✅ | ✅ green |
| 01-03-01 | 03 | 2 | FOUND-03 | T-01-11 | Deep nesting, 2 MB input and fuzz handled without crash | unit | `./env/Scripts/python.exe -m pytest tests/test_sexpr.py -x -q` | ✅ | ✅ green |
| 01-03-02 | 03 | 2 | FOUND-04 | T-01-12, T-01-13 | quote() cannot break out of a string; bad splices raise | unit | `./env/Scripts/python.exe -m pytest tests/test_sexpr.py -x -q` | ✅ (01-03-01) | ✅ green |
| 01-04-01 | 04 | 2 | FOUND-03 | T-01-14 | tests/ never appears as a library source in the GUI scan | unit | `./env/Scripts/python.exe -m pytest tests/test_scanner_skip_dirs.py -x -q` | ✅ | ✅ green |
| 01-04-02 | 04 | 2 | FOUND-03 | T-01-15, T-01-16 | Fixture bytes match the builder and carry `-text`; a named check per D-02 case proves the table fixtures hold every lib-table edge case, odd whitespace included | unit | `./env/Scripts/python.exe -m pytest tests/test_fixtures.py tests/test_scanner_skip_dirs.py -x -q` | ✅ | ✅ green |
| 01-05-01 | 05 | 3 | FOUND-04, FOUND-03 | T-01-17, T-01-20 | Exact-name locators with spans; foundation modules import no Qt | unit | `./env/Scripts/python.exe -m pytest tests/test_kicad_files.py tests/test_layering.py -x -q` | ✅ | ✅ green |
| 01-05-02 | 05 | 3 | FOUND-04 | T-01-18, T-01-19 | Edits/inserts keep EOL and BOM; interrupted write leaves original intact | unit | `./env/Scripts/python.exe -m pytest tests/test_edits.py -x -q` | ✅ (01-01-01) | ✅ green |
| 01-06-01 | 06 | 3 | FOUND-03 | T-01-22, T-01-23 | Zip members read in memory under a size cap; repo corpus round-trips | corpus | `./env/Scripts/python.exe -m pytest tests/test_roundtrip_corpus.py -x -q -m "not wurth and not local_kicad"` | ✅ | ✅ green |
| 01-06-02 | 06 | 3 | FOUND-03 | T-01-21, T-01-24 | Personal KiCad tables read in place, never copied or printed | corpus (opt-in) | `./env/Scripts/python.exe -m pytest tests/test_roundtrip_corpus.py -q -rs` | ✅ (01-06-01) | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `.gitattributes` (commit `.gitattributes` before any fixture is staged)
- [x] `tests/conftest.py`: forced offscreen platform, repo-root and corpus-discovery fixtures
- [x] `tests/test_manifests.py`, `tests/test_library_table_widget.py`, `tests/test_models.py`, `tests/test_layering.py`
- [x] `tests/test_sexpr.py`, `tests/test_roundtrip_corpus.py`, `tests/test_edits.py`, `tests/test_kicad_files.py`, `tests/test_fsutil.py`
- [x] `tests/fixtures/sexpr/*` created byte-exact (LF, CRLF, BOM, mixed EOL, parens and escaped quotes in strings, bare atoms, no trailing newline)
- [x] `tests/fixtures/tables/*.sym-lib-table` / `*.fp-lib-table` (not named bare `sym-lib-table` / `fp-lib-table`, which `.gitignore` ignores) covering escaped `"` and `\`, reordered fields, odd whitespace between sub-forms (three spaces, a TAB, a line break inside an entry), missing options/descr, `(disabled)`/`(hidden)`, an unknown child and an empty table, each asserted by `test_table_fixtures_cover_d02_edge_cases`
- [x] `downloaded_examples/ul_CSD85301Q2.zip` tracked by explicit path
- [x] `pytest-qt` installed: `.\env\Scripts\python.exe -m pip install -r requirements-dev.txt`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Fresh venv installs pinned deps and `pytest` is green with no display (SC1) | FOUND-01 | Slow (>30 s) and needs a throwaway venv outside the repo plus PyPI access, so it is not a per-task `<automated>` command. The executor runs it as Plan 01 Task 3 step (4) and again at the phase gate (Plan 06 verification) | Git Bash: `py -3.14 -m venv "$TEMP/kicadlib-fresh-venv"`, then `"$TEMP/kicadlib-fresh-venv/Scripts/python.exe" -m pip install -r requirements-dev.txt`, then `"$TEMP/kicadlib-fresh-venv/Scripts/pytest.exe" -q` from the repo root |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-10-18. All 13 task commands green in the orchestrator checkout with `Custom/` present (full suite 353 passed, 2 skipped: WurthElektronik submodule not checked out). SC1 fresh-venv run recorded in 01-01-SUMMARY (install exit 0, suite green).

## Validation Audit 2026-10-18

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
