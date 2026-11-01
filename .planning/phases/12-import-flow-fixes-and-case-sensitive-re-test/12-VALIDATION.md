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
- **After every plan wave:** Run `env/Scripts/python.exe -m pytest tests/test_table_add_entries.py tests/test_kicad_config.py tests/test_help_dialog.py tests/test_main_window.py tests/test_main_window_import.py tests/test_install_apply.py tests/test_install_plan.py tests/test_case_sensitive_install.py -q` (~1 min; add `tests/test_backup_dialog.py` from wave 2 on), plus `tests/test_import_dialog.py` in full once after the REV-04 wave (wave 4, background)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds (per-task targeted runs)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-T1 | 12-01 | 1 | VER-02 | T-12-01, T-12-03 | Overwrite of a case twin writes the on-disk spelling; one file remains (D-14) | integration | `env/Scripts/python.exe -m pytest tests/test_case_sensitive_install.py tests/test_install_plan.py -q -rs -k "case or twin or overwrite"` | ❌ W0 (this task creates `tests/casefixtures.py` and `tests/test_case_sensitive_install.py`) | ⬜ pending |
| 12-01-T2 | 12-01 | 1 | VER-02 | T-12-02 | Rollback restores the original spelling and removes the twin; conflict view finds the twin op | integration | `env/Scripts/python.exe -m pytest tests/test_case_sensitive_install.py tests/test_install_plan.py tests/test_install_apply.py tests/test_import_preview.py tests/test_import_content.py tests/test_commit_plan.py -q -rs` | ✅ after T1; README row added here | ⬜ pending |
| 12-02-T1 | 12-02 | 1 | UI-01 | T-12-04 | N/A | unit | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py -q` | ✅ extend (token and heading-size tests added here) | ⬜ pending |
| 12-02-T2 | 12-02 | 1 | UI-01 | — | N/A | unit + manual screenshots | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py tests/test_import_dialog.py -q -k "help or conflict_row"` | ✅ extend | ⬜ pending |
| 12-03-T1 | 12-03 | 1 | REV-01 | T-12-05, T-12-06 | Stale tool-owned entry repointed after a backup; live clash left unchanged | unit + window | `env/Scripts/python.exe -m pytest tests/test_table_add_entries.py tests/test_main_window_import.py tests/test_layering.py -q` | ✅ extend | ⬜ pending |
| 12-03-T2 | 12-03 | 1 | REV-01 | T-12-05, T-12-07 | Hand entries never edited; existing-library install never adds an entry | unit + window | `env/Scripts/python.exe -m pytest tests/test_table_add_entries.py tests/test_main_window_import.py tests/test_write_tables.py tests/test_table_merge.py -q` | ✅ extend | ⬜ pending |
| 12-04-T1 | 12-04 | 2 | REV-02 | T-12-08 | Blank Destination after install writes nothing in the working directory | window | `env/Scripts/python.exe -m pytest tests/test_main_window_import.py -q -k "destination or status_rows or tables"` | ✅ extend | ⬜ pending |
| 12-04-T2 | 12-04 | 2 | REV-02 | T-12-08, T-12-09 | Generate, table logs and Restore Backup never touch the working directory | window + dialog | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py tests/test_backup_dialog.py -q` | ❌ W0 (this task creates `tests/test_backup_dialog.py`) | ⬜ pending |
| 12-05-T1 | 12-05 | 2 | REV-04 | T-12-10, T-12-11 | Change... during a build defers; package closed only after the build | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py -q -k "change or close_waits or builds_never_overlap or one_build"` | ✅ extend | ⬜ pending |
| 12-05-T2 | 12-05 | 2 | REV-04 | T-12-10 | Open during a build defers; Cancel restores; no build starts while Finishing | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py -q -k "finishing or open_during or open_path or change"` | ✅ extend | ⬜ pending |
| 12-05-T3 | 12-05 | 2 | REV-03 | T-12-12 | No one-off build reads the target library during Install | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py -q -k "oneoff or conflict or install"` | ✅ extend | ⬜ pending |
| 12-06-T1 | 12-06 | 3 | REV-05 | T-12-15, T-12-16 | KiCad check off the GUI thread before the dialog; nothing written without a confirm | unit + window | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py tests/test_kicad_config.py tests/test_layering.py -q` | ✅ extend; fixture change, `settle` helper and conftest teardown join added here | ⬜ pending |
| 12-06-T2 | 12-06 | 3 | REV-05 | T-12-14, T-12-17 | Confirmed write merges into the re-read file; backup + atomic write | unit | `env/Scripts/python.exe -m pytest tests/test_kicad_config.py tests/test_kicad_process.py tests/test_layering.py -q` | ✅ extend | ⬜ pending |
| 12-06-T3 | 12-06 | 3 | REV-05 | T-12-15, T-12-16 | Retry never writes; one check at a time; close defers without a wait | window | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py -q -k "kicad_open or retry or not_now or second_generate or check or close or generate or tables"` | ✅ extend | ⬜ pending |
| 12-07-T1 | 12-07 | 4 | REV-04 | T-12-18, T-12-19, T-12-20 | Package stays open until workers end, without GUI-thread waits; main window closes after the dialog | dialog + window | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_main_window_import.py -q -k "close or finishing or change"` | ✅ rewrite + add | ⬜ pending |
| 12-07-T2 | 12-07 | 4 | REV-04 | T-12-18, T-12-21 | Escape inert while Finishing; Cancel restores; probe re-run after a cancelled close | dialog + window | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_main_window_import.py -q -k "close or finishing or escape or cancel or probe or kicad_running or add_model_close"` (then the whole `tests/test_import_dialog.py` in the background) | ✅ rewrite + add | ⬜ pending |
| 12-08-T1 | 12-08 | 5 | REV-01..REV-05 | — | N/A | unit | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py -q` | ✅ extend | ⬜ pending |
| 12-08-T2 | 12-08 | 5 | REV-01..REV-05 | T-12-22 | Phase gate | per-wave set + full suite (background) + manual | `env/Scripts/python.exe -m pytest tests/test_table_add_entries.py tests/test_kicad_config.py tests/test_help_dialog.py tests/test_main_window.py tests/test_main_window_import.py tests/test_install_apply.py tests/test_install_plan.py tests/test_case_sensitive_install.py tests/test_backup_dialog.py -q`; full: `env/Scripts/python.exe -m pytest -q -rs` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task IDs are `{plan}-T{n}` (task n of that PLAN.md). Wave 0 items are created by the task named in the File Exists column.*

---

## Wave 0 Requirements

- [ ] `tests/casefixtures.py` — `case_sensitive_dir()` fixture (fsutil on Windows, real case-sensitivity probe, skip with stated reason) — 12-01-T1
- [ ] `tests/test_case_sensitive_install.py` — rollback-with-twin and D-14 overwrite tests (T1–T4 per RESEARCH.md) — 12-01-T1 (T3), 12-01-T2 (T1, T2, T4, incoming_op)
- [ ] `settle(qtbot, window)` helper and the `fake_sync` / `kicad_running` fixture change in `tests/test_main_window.py` and `tests/test_main_window_import.py` — 12-06-T1
- [ ] join-workers teardown for dialog tests (RESEARCH.md Pitfall 3) — a `pytest_runtest_teardown` wrapper in `tests/conftest.py` that joins QThread children of registered widgets before pytest-qt closes them (order verified at planning) — 12-06-T1
- [ ] `tests/README.md` expected-skips row for "could not make a case-sensitive folder" — 12-01-T2
- [ ] `tests/test_backup_dialog.py` — blank backup folder tests — 12-04-T2
- [ ] UI-01 token and heading-size tests in `tests/test_help_dialog.py` — 12-02-T1

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
