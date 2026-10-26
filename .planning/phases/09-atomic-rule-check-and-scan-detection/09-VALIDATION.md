---
phase: "9"
slug: "atomic-rule-check-and-scan-detection"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-26"
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 with pytest-qt (`qtbot`), offscreen Qt forced in `tests/conftest.py` |
| **Config file** | `pyproject.toml` (`testpaths = ["tests"]`, `addopts = "-ra --strict-markers"`, markers `wurth`, `local_kicad`, `kicad_cli`) |
| **Quick run command** | `env/Scripts/python.exe -m pytest <the phase 9 test files present at that task> tests/test_layering.py tests/test_importer_layering.py -q` |
| **Full suite command** | `env/Scripts/python.exe -m pytest` (`-m "not wurth"` for the per-wave run) |
| **Estimated runtime** | ~30 seconds quick; ~8 min `-m "not wurth"`; ~18 min full |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (only the new test files that exist at that task)
- **After every plan wave:** Run `env/Scripts/python.exe -m pytest -m "not wurth"`
- **Before `/gsd-verify-work`:** Full suite must be green, with only the skips documented in `tests/README.md`
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-01-T1 | 09-01 | 1 | FLD-02 | — | — | unit + layering | `env/Scripts/python.exe -m pytest tests/test_manufacturers.py tests/test_naming_suggest.py tests/test_layering.py tests/test_importer_layering.py -q` | ✅ | ✅ green |
| 09-01-T2 | 09-01 | 1 | FLD-02 | — | — | unit (tdd) | `env/Scripts/python.exe -m pytest tests/test_manufacturers.py tests/test_naming_suggest.py -q` | ✅ | ✅ green |
| 09-02-T1 | 09-02 | 1 | SCAN-01 | — | — | GUI (qtbot) | `env/Scripts/python.exe -m pytest tests/test_library_table_atomic.py tests/test_models.py tests/test_library_table_widget.py -q` | ✅ | ✅ green |
| 09-02-T2 | 09-02 | 1 | SCAN-02 | — | — | GUI (qtbot, tdd) | `env/Scripts/python.exe -m pytest tests/test_library_table_atomic.py tests/test_library_table_widget.py -q` | ✅ | ✅ green |
| 09-02-T3 | 09-02 | 1 | SCAN-01 | — | — | GUI (qtbot, tdd) | `env/Scripts/python.exe -m pytest tests/test_library_table_atomic.py tests/test_library_table_widget.py tests/test_main_window.py -q` | ✅ | ✅ green |
| 09-03-T1 | 09-03 | 2 | ATOM-02, SCAN-01 | — | — | integration | `env/Scripts/python.exe -m pytest tests/test_atomic_scan.py tests/test_layering.py tests/test_scanner_issues.py tests/test_scanner_skip_dirs.py -q` | ✅ | ✅ green |
| 09-03-T2 | 09-03 | 2 | ATOM-01, ATOM-02, FLD-02 | — | — | unit (tdd) | `env/Scripts/python.exe -m pytest tests/test_atomic_check.py tests/test_atomic_scan.py -q` | ✅ | ✅ green |
| 09-03-T3 | 09-03 | 2 | ATOM-03 | — | — | unit (tdd) | `env/Scripts/python.exe -m pytest tests/test_atomic_check.py tests/test_atomic_scan.py -q` | ✅ | ✅ green |
| 09-04-T1 | 09-04 | 3 | ATOM-01 | — | — | unit + integration | `env/Scripts/python.exe -m pytest tests/test_atomic_check.py tests/test_atomic_scan.py -q` | ✅ | ✅ green |
| 09-04-T2 | 09-04 | 3 | ATOM-01, ATOM-03 | — | — | unit (tdd) | `env/Scripts/python.exe -m pytest tests/test_atomic_check.py tests/test_atomic_scan.py tests/test_scanner_issues.py -q` | ✅ | ✅ green |
| 09-05-T1 | 09-05 | 3 | SCAN-02 | — | — | integration (git) | `env/Scripts/python.exe -m pytest tests/test_scan_changes.py tests/test_layering.py tests/test_atomic_scan.py -q` | ✅ | ✅ green |
| 09-05-T2 | 09-05 | 3 | SCAN-02 | — | — | unit + git (tdd) | `env/Scripts/python.exe -m pytest tests/test_scan_changes.py tests/test_sexpr.py tests/test_scanner_issues.py tests/test_scanner_skip_dirs.py -q` | ✅ | ✅ green |
| 09-06-T1 | 09-06 | 4 | SCAN-03 | — | — | unit (tmp_path) | `env/Scripts/python.exe -m pytest tests/test_atomic_fixes.py tests/test_layering.py -q` | ✅ | ✅ green |
| 09-06-T2 | 09-06 | 4 | SCAN-03, FLD-02 | — | — | unit (tdd) | `env/Scripts/python.exe -m pytest tests/test_atomic_fixes.py -q` | ✅ | ✅ green |
| 09-06-T3 | 09-06 | 4 | SCAN-03 | — | — | unit (tdd) | `env/Scripts/python.exe -m pytest tests/test_atomic_fixes.py tests/test_atomic_scan.py tests/test_layering.py -q` | ✅ | ✅ green |
| 09-07-T1 | 09-07 | 5 | SCAN-03 | — | — | GUI (qtbot) | `env/Scripts/python.exe -m pytest tests/test_atomic_dialog.py tests/test_main_window.py -q` | ✅ | ✅ green |
| 09-07-T2 | 09-07 | 5 | SCAN-03 | — | — | GUI (qtbot, tdd) | `env/Scripts/python.exe -m pytest tests/test_atomic_dialog.py -q` | ✅ | ✅ green |
| 09-07-T3 | 09-07 | 5 | SCAN-01, SCAN-03 | — | — | GUI (qtbot, tdd) | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_help_dialog.py tests/test_atomic_dialog.py tests/test_library_table_atomic.py -q` | ✅ | ✅ green |
| 09-08-T1 | 09-08 | 5 | SCAN-01, SCAN-02, SCAN-03 | — | — | UAT builder (opt-in) | `env/Scripts/python.exe -m pytest tests/test_atomic_uat.py -q` | ✅ | ✅ green (live-Custom build opt-in via `KICAD_ATOMIC_UAT_DIR`) |
| 09-08-T2 | 09-08 | 5 | SCAN-01..03 | — | — | docs + skip reason | `env/Scripts/python.exe -m pytest tests/test_atomic_uat.py -rs -q` | ✅ | ✅ green |

Threat references and secure behaviour are audited by `/gsd-secure-phase 9`, not here.

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_manufacturers.py` — FLD-02 fold, lookup, uniqueness, derivation of `suggest.MANUFACTURER_ALIASES`
- [x] `tests/test_atomic_check.py` — ATOM-01..03 rules
- [x] `tests/test_atomic_fixes.py` — SCAN-03 fixes, apply, rollback, fill-in
- [x] `tests/test_scan_changes.py` — SCAN-02, git-backed (`requires_git` from `tests/gitfixtures.py`)
- [x] `tests/test_atomic_scan.py` — SCAN-01 integration over a synthetic tree
- [x] `tests/test_library_table_atomic.py`, `tests/test_atomic_dialog.py` — GUI (`qtbot`)
- [x] `tests/customfixtures.py` — `Atomic_` libraries (builders return bytes, no paths; Phase 8 D-01/D-02)
- [x] Git-backed Custom populator for `make_superproject` (commit an Atomic baseline, then mutate)
- [x] `tests/test_layering.py` and `tests/test_importer_layering.py` ALLOWED maps updated for each new module

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Marks, tooltips and dialog read correctly on real parts | SCAN-01, SCAN-03 | Visual judgement on the owner's own parts | Run the app against the D-25 scratch repo copy; check marked rows, tooltips, log lines, and apply one of each fix |
| Changed-part highlight on the live tree | SCAN-02 | Needs a real hand edit in KiCad | Edit one symbol in KiCad's Symbol Editor, rescan, confirm `Changed` on that symbol only |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [ ] Feedback latency < 60s — not met for every task: the combined phase 9 set (11 files) takes 2 min 51 s; single-file task commands are faster but were not timed one by one
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated by /gsd-validate-phase 9 on 2026-10-26 (476 passed, 1 opt-in skip)

## Validation Audit 2026-10-26

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
