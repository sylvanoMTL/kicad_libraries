---
phase: "12"
slug: "import-flow-fixes-and-case-sensitive-re-test"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-11-01"
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-qt 4.5.0 (`qt_api = "pyside6"`) |
| **Config file** | `pyproject.toml` (`testpaths = ["tests"]`, `addopts = "-ra --strict-markers"`) |
| **Quick run command** | `env/Scripts/python.exe -m pytest <targeted files> -q` (repo root, no xdist) |
| **Full suite command** | `env/Scripts/python.exe -m pytest -q` (phase gate only; run in the background) |
| **Estimated runtime** | quick: 5–45 s per file set; per-wave set ~60 s; full suite ~21–27 min (`-m "not wurth"` ~15–20 min) |

---

## Sampling Rate

- **After every task commit:** Run the targeted file(s) for the slice touched (see map below)
- **After every plan wave:** Run `env/Scripts/python.exe -m pytest tests/test_table_add_entries.py tests/test_kicad_config.py tests/test_help_dialog.py tests/test_main_window.py tests/test_main_window_import.py tests/test_install_apply.py tests/test_install_plan.py tests/test_case_sensitive_install.py -q` (~1 min), plus `tests/test_import_dialog.py` in full once after the REV-04 wave (background)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds (per-task targeted runs)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-TBD | TBD | TBD | REV-01 | — | Tool-owned entry repointed only when stale; table backed up first; hand entries never edited | unit + window | `env/Scripts/python.exe -m pytest tests/test_table_add_entries.py tests/test_main_window_import.py -q` | ✅ extend | ⬜ pending |
| 12-TBD | TBD | TBD | REV-02 | — | Blank Destination never reads or writes the process working directory | window | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py -q` | ✅ extend; backup dialog ❌ W0 | ⬜ pending |
| 12-TBD | TBD | TBD | REV-03 | — | No one-off build reads the target library during Install | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py -q -k "oneoff or conflict or install"` | ✅ extend | ⬜ pending |
| 12-TBD | TBD | TBD | REV-04 | — | Package stays open until workers end, without GUI-thread waits | dialog + window | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_main_window_import.py -q -k "finishing or close or change"` | ✅ rewrite + add | ⬜ pending |
| 12-TBD | TBD | TBD | REV-05 | — | Confirmed write merges into fresh file; backup + atomic write; nothing written without confirm | unit + window | `env/Scripts/python.exe -m pytest tests/test_kicad_config.py tests/test_main_window.py tests/test_kicad_process.py -q` | ✅ extend; fixture change | ⬜ pending |
| 12-TBD | TBD | TBD | UI-01 | — | N/A | unit | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py -q` | ✅ extend; token test ❌ W0 | ⬜ pending |
| 12-TBD | TBD | TBD | VER-02 | — | Rollback restores original spelling; no twin left; overwrite keeps on-disk spelling | integration | `env/Scripts/python.exe -m pytest tests/test_case_sensitive_install.py tests/test_install_plan.py tests/test_install_apply.py -q -k "case or twin or rollback"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task IDs are filled in once plans exist.*

---

## Wave 0 Requirements

- [ ] `tests/casefixtures.py` — `case_sensitive_dir()` fixture (fsutil on Windows, real case-sensitivity probe, skip with stated reason)
- [ ] `tests/test_case_sensitive_install.py` — rollback-with-twin and D-14 overwrite tests (T1–T4 per RESEARCH.md)
- [ ] `settle(qtbot, window)` helper and the `fake_sync` / `kicad_running` fixture change in `tests/test_main_window.py` and `tests/test_main_window_import.py`
- [ ] join-workers fixture finaliser for dialog tests (RESEARCH.md Pitfall 3)
- [ ] `tests/README.md` expected-skips row for "could not make a case-sensitive folder"

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Case-sensitive tests pass (not skip) on the owner's Windows machine | VER-02 | Skips are environment-dependent; only the workstation proves the fsutil path | From the repo root run `.\env\Scripts\python.exe -m pytest tests/test_case_sensitive_install.py -v -rs`; every test PASSED, no "skipped" in the summary |
| Help dialog and conflict rows look right with theme tokens | UI-01 | Visual check | Owner reviews rendered screenshots, as in Phase 11 UAT |
| Window stays responsive while kicad-cli works | REV-04 | Real kicad-cli timing | Open a package with a slow build, press Change...; window moves/repaints, strip shows, action runs by itself |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
