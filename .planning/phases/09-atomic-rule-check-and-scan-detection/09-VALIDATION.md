---
phase: "9"
slug: "atomic-rule-check-and-scan-detection"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| (filled by the planner from 09-RESEARCH.md § Validation Architecture) | | | | | | | | | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_manufacturers.py` — FLD-02 fold, lookup, uniqueness, derivation of `suggest.MANUFACTURER_ALIASES`
- [ ] `tests/test_atomic_check.py` — ATOM-01..03 rules
- [ ] `tests/test_atomic_fixes.py` — SCAN-03 fixes, apply, rollback, fill-in
- [ ] `tests/test_scan_changes.py` — SCAN-02, git-backed (`requires_git` from `tests/gitfixtures.py`)
- [ ] `tests/test_atomic_scan.py` — SCAN-01 integration over a synthetic tree
- [ ] `tests/test_library_table_atomic.py`, `tests/test_atomic_dialog.py` — GUI (`qtbot`)
- [ ] `tests/customfixtures.py` — `Atomic_` libraries (builders return bytes, no paths; Phase 8 D-01/D-02)
- [ ] Git-backed Custom populator for `make_superproject` (commit an Atomic baseline, then mutate)
- [ ] `tests/test_layering.py` and `tests/test_importer_layering.py` ALLOWED maps updated for each new module

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Marks, tooltips and dialog read correctly on real parts | SCAN-01, SCAN-03 | Visual judgement on the owner's own parts | Run the app against the D-25 scratch repo copy; check marked rows, tooltips, log lines, and apply one of each fix |
| Changed-part highlight on the live tree | SCAN-02 | Needs a real hand edit in KiCad | Edit one symbol in KiCad's Symbol Editor, rescan, confirm `Changed` on that symbol only |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
