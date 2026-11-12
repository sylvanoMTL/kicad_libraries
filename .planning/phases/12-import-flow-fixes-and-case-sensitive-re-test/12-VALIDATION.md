---
phase: "12"
slug: "import-flow-fixes-and-case-sensitive-re-test"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
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
| 12-01-T1 | 12-01 | 1 | VER-02 | T-12-01, T-12-03 | Overwrite of a case twin writes the on-disk spelling; one file remains (D-14) | integration | `env/Scripts/python.exe -m pytest tests/test_case_sensitive_install.py tests/test_install_plan.py -q -rs -k "case or twin or overwrite"` | ❌ W0 (this task creates `tests/casefixtures.py` and `tests/test_case_sensitive_install.py`) | ✅ green |
| 12-01-T2 | 12-01 | 1 | VER-02 | T-12-02 | Rollback restores the original spelling and removes the twin; conflict view finds the twin op | integration | `env/Scripts/python.exe -m pytest tests/test_case_sensitive_install.py tests/test_install_plan.py tests/test_install_apply.py tests/test_import_preview.py tests/test_import_content.py tests/test_commit_plan.py -q -rs` | ✅ after T1; README row added here | ✅ green |
| 12-02-T1 | 12-02 | 1 | UI-01 | T-12-04 | N/A | unit | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py -q` | ✅ extend (token and heading-size tests added here) | ✅ green |
| 12-02-T2 | 12-02 | 1 | UI-01 | — | N/A | unit + manual screenshots | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py tests/test_import_dialog.py -q -k "help or conflict_row"` | ✅ extend | ✅ green |
| 12-03-T1 | 12-03 | 1 | REV-01 | T-12-05, T-12-06 | Stale tool-owned entry repointed after a backup; live clash left unchanged | unit + window | `env/Scripts/python.exe -m pytest tests/test_table_add_entries.py tests/test_main_window_import.py tests/test_layering.py -q` | ✅ extend | ✅ green |
| 12-03-T2 | 12-03 | 1 | REV-01 | T-12-05, T-12-07 | Hand entries never edited; existing-library install never adds an entry | unit + window | `env/Scripts/python.exe -m pytest tests/test_table_add_entries.py tests/test_main_window_import.py tests/test_write_tables.py tests/test_table_merge.py -q` | ✅ extend | ✅ green |
| 12-04-T1 | 12-04 | 2 | REV-02 | T-12-08 | Blank Destination after install writes nothing in the working directory | window | `env/Scripts/python.exe -m pytest tests/test_main_window_import.py -q -k "destination or status_rows or tables"` | ✅ extend | ✅ green |
| 12-04-T2 | 12-04 | 2 | REV-02 | T-12-08, T-12-09 | Generate, table logs and Restore Backup never touch the working directory | window + dialog | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py tests/test_backup_dialog.py -q` | ❌ W0 (this task creates `tests/test_backup_dialog.py`) | ✅ green |
| 12-05-T1 | 12-05 | 2 | REV-04 | T-12-10, T-12-11 | Change... during a build defers; package closed only after the build | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py -q -k "change or close_waits or builds_never_overlap or one_build"` | ✅ extend | ✅ green |
| 12-05-T2 | 12-05 | 2 | REV-04 | T-12-10 | Open during a build defers; Cancel restores; no build starts while Finishing | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py -q -k "finishing or open_during or open_path or change"` | ✅ extend | ✅ green |
| 12-05-T3 | 12-05 | 2 | REV-03 | T-12-12 | No one-off build reads the target library during Install | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py -q -k "oneoff or conflict or install"` | ✅ extend | ✅ green |
| 12-06-T1 | 12-06 | 3 | REV-05 | T-12-15, T-12-16 | KiCad check off the GUI thread before the dialog; nothing written without a confirm | unit + window | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py tests/test_kicad_config.py tests/test_layering.py -q` | ✅ extend; fixture change, `settle` helper and conftest teardown join added here | ✅ green |
| 12-06-T2 | 12-06 | 3 | REV-05 | T-12-14, T-12-17 | Confirmed write merges into the re-read file; backup + atomic write | unit | `env/Scripts/python.exe -m pytest tests/test_kicad_config.py tests/test_kicad_process.py tests/test_layering.py -q` | ✅ extend | ✅ green |
| 12-06-T3 | 12-06 | 3 | REV-05 | T-12-15, T-12-16 | Retry never writes; one check at a time; close defers without a wait | window | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py -q -k "kicad_open or retry or not_now or second_generate or check or close or generate or tables"` | ✅ extend | ✅ green |
| 12-07-T1 | 12-07 | 4 | REV-04 | T-12-18, T-12-19, T-12-20 | Package stays open until workers end, without GUI-thread waits; main window closes after the dialog | dialog + window | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_main_window_import.py -q -k "close or finishing or change"` | ✅ rewrite + add | ✅ green |
| 12-07-T2 | 12-07 | 4 | REV-04 | T-12-18, T-12-21 | Escape inert while Finishing; Cancel restores; probe re-run after a cancelled close | dialog + window | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_main_window_import.py -q -k "close or finishing or escape or cancel or probe or kicad_running or add_model_close"` (then the whole `tests/test_import_dialog.py` in the background) | ✅ rewrite + add | ✅ green |
| 12-08-T1 | 12-08 | 5 | REV-01..REV-05 | — | N/A | unit | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py -q` | ✅ extend | ✅ green |
| 12-08-T2 | 12-08 | 5 | REV-01..REV-05 | T-12-22 | Phase gate | per-wave set + full suite (background) + manual | `env/Scripts/python.exe -m pytest tests/test_table_add_entries.py tests/test_kicad_config.py tests/test_help_dialog.py tests/test_main_window.py tests/test_main_window_import.py tests/test_install_apply.py tests/test_install_plan.py tests/test_case_sensitive_install.py tests/test_backup_dialog.py -q`; full: `env/Scripts/python.exe -m pytest -q -rs` | ✅ | ✅ green |
| 12-09-T1 | 12-09 | gap 1 | REV-04 | T-12-23, T-12-24 | Cancel beside Install Part goes through `done()`: greyed out while installing or committing, enters Finishing during a build (G-12-6) | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_help_dialog.py -q -k "cancel_button or install_progress_and_lock or install_failure_banner or close_finishes_after_build or close_refused_while_installing or commit_close_button_disabled or help_names_the_cancel or failure_and_tables_claims or phase_12_behaviour"` | ✅ extend | ✅ green |
| 12-09-T2 | 12-09 | gap 1 | REV-04 | — | N/A (required-field hints, G-12-7) | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_help_dialog.py -q -k "required_field_hints or fields_clear_and_restore or explains_fields or uses_plain_words"` | ✅ extend | ✅ green |
| 12-09-T3 | 12-09 | gap 1 | REV-04 | — | N/A ("Choose another package..." header button, G-12-8) | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_help_dialog.py -q -k "change_button or change_returns or choose_another or phase_12_behaviour or help_import_page"` | ✅ extend | ✅ green |
| 12-10-T1 | 12-10 | gap 1 | REV-05 | T-12-26 | Only message text changes; read, back-up and atomic write of KiCad's settings file unchanged (G-12-5) | unit + window | `env/Scripts/python.exe -m pytest tests/test_kicad_config.py tests/test_main_window.py -q -k "kicad_open or path_var or unstable_file or invalid_json or wrong_shape or verification_failure or null_vars or bad_json or running"` | ✅ extend | ✅ green |
| 12-10-T2 | 12-10 | gap 1 | REV-05 | T-12-25 | Issue codes, severities and matched phrases kept while texts name the command-line tool plainly (G-12-5) | unit | `env/Scripts/python.exe -m pytest tests/test_import_preview.py tests/test_kicad_cli.py tests/test_install_apply.py -q` | ✅ extend | ✅ green |
| 12-11-T1 | 12-11 | gap 2 | REV-04 | — | N/A (slow note and Help sentence, G-12-5) | dialog | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py tests/test_import_dialog.py -q -k "phase_12_behaviour or slow_note or help_import_page or choose_another or cancel_button"` | ✅ extend | ✅ green |
| 12-11-T2 | 12-11 | gap 2 | REV-04 | T-12-27, T-12-28 | Package-wide guard: no user-facing string names the raw tool or settings file; fails on an empty scan; backup folder untouched | source scan | `env/Scripts/python.exe -m pytest tests/test_plain_names.py tests/test_kicad_config.py -q` | ❌ W0 (this task creates `tests/test_plain_names.py`) | ✅ green |
| 12-12-T1 | 12-12 | gap 3 | UI-01 | — | N/A (toolbar Help opens the User Guide on Importing Parts; F1 is the only binding, G-12-9) | dialog | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py tests/test_import_dialog.py -q -k "given_topic or opens_importing_page or toolbar_help or f1_opens or ctrl_return"` | ✅ extend | ✅ green |
| 12-12-T2 | 12-12 | gap 3 | UI-01 | T-12-29, T-12-30 | Help never touches install, build, Finishing or commit state; shown non-modal and closed with the import window (G-12-9) | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py -q -k "help_ or toolbar_help or f1_opens or cancel_button or close_finishes_after_build or escape_does_nothing_while_finishing or commit_close_button_disabled"` | ✅ extend | ✅ green |
| 12-12-T3 | 12-12 | gap 3 | UI-01 | T-12-31 | Static Help text only; plain words (G-12-9) | unit + dialog | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py tests/test_import_dialog.py tests/test_plain_names.py tests/test_main_window_import.py -q` | ✅ extend | ✅ green |
| 12-13-T1 | 12-13 | gap 4 | REV-04 | T-12-32 | Start-page Cancel calls `reject()`: closes without writing, waits in Finishing while a package is read (G-12-10) | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_help_dialog.py -q -k "start_page_cancel or cancel_button or start_page_layout or ctrl_return or help_names_the or install_progress_and_lock"` | ✅ extend | ✅ green |
| 12-13-T2 | 12-13 | gap 4 | UI-01 | T-12-33, T-12-34 | Window and both buttons inside the free screen area at 100% and 200%; real `screen_area` checked against the widget's screen (G-12-10) | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_generated_text.py tests/test_official_footprint.py -q -k "fit_size or fits_the_screen or screen_area or fields_long_text_geometry or library_long_name_geometry or strip_caps_three_lines or conflicts_overflow_geometry or fit_the_left_pane or start_page or cancel_button"` | ✅ extend; autouse `_desktop_screen_area` fixture added to `tests/conftest.py` | ✅ green |
| 12-13-T3 | 12-13 | gap 4 | UI-01 | T-12-33 | N/A (start page opens small, grows for the edit page, shrinks back; Help wording, G-12-10) | dialog + plan-level | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_help_dialog.py tests/test_main_window_import.py tests/test_plain_names.py tests/test_field_rules.py tests/test_gate_reasons.py tests/test_generated_text.py tests/test_install_gate.py tests/test_official_footprint.py tests/test_single_footprint.py tests/test_suggest_atomic.py -q` | ✅ extend | ✅ green |
| 12-14-T1 | 12-14 | gap 4 (w2) | UI-01 | T-12-35 | Numbered three-level menu from the pages' h3 headings; anchors limited to `^[a-z0-9]+(-[a-z0-9]+)*$`; click scrolls to the heading (G-12-11) | unit + dialog | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py -q` | ✅ extend | ✅ green |
| 12-14-T2 | 12-14 | gap 4 (w2) | UI-01 | T-12-37 | Menu follows the shown page; section keys open from every entry point; User Guide bounded by the free screen area at 100% and 200% (G-12-11) | dialog | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py tests/test_import_dialog.py -q -k "help or toolbar or f1_opens or menu or given_topic"` | ✅ extend | ✅ green |
| 12-14-T3 | 12-14 | gap 4 (w2) | UI-01 | T-12-36 | Static Help text only; numbered headings keep theme tokens, size and colour (G-12-11) | unit + dialog | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py tests/test_import_dialog.py tests/test_plain_names.py tests/test_main_window_import.py -q` | ✅ extend | ✅ green |
| 12-15-T1 | 12-15 | gap 5 | UI-01 | T-12-38 | Cancel on the Browse row; start window as tall as its content and inside the free screen area (G-12-12) | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py -q -k "start_page or window_grows or window_fits or result_page_keeps or ctrl_return"` | ✅ extend | ✅ green |
| 12-15-T2 | 12-15 | gap 5 | UI-01 | T-12-38 | Downloads line and reading box share one slot; the window refits when issues show or clear, Cancel stays on screen at 200% (G-12-12) | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py -q -k "start_page or start_issues or offer or window_grows"` | ✅ extend | ✅ green |
| 12-15-T3 | 12-15 | gap 5 | UI-01 | — | N/A (Help names where Cancel sits on each step; plan-level check, G-12-12) | unit + dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_help_dialog.py tests/test_plain_names.py tests/test_main_window_import.py -q` | ✅ extend | ✅ green |
| 12-16-T1 | 12-16 | gap 5 | UI-01 | T-12-42 | Skipping one source's 3D model path check through `scan_all` drops no library and no footprint link (G-12-21) | unit | `env/Scripts/python.exe -m pytest tests/test_scan_skip.py tests/test_scanner_issues.py tests/test_rescan_library.py tests/test_layering.py -q -m "not wurth"` | ❌ W0 (this task creates `tests/test_scan_skip.py`) | ✅ green |
| 12-16-T2 | 12-16 | gap 5 | UI-01 | T-12-39, T-12-41 | Saved scan keeps skipped sources and says so when reused; odd saved values give a full scan (G-12-21) | unit | `env/Scripts/python.exe -m pytest tests/test_scan_cache.py tests/test_scan_skip.py -q` | ✅ extend | ✅ green |
| 12-16-T3 | 12-16 | gap 5 | UI-01 | T-12-40 | Code signature follows the scan's real import graph; an unreadable module never reads as fresh; one rising progress scale (G-12-21) | unit | `env/Scripts/python.exe -m pytest tests/test_scan_cache.py tests/test_scan_skip.py tests/test_scanner_issues.py tests/test_rescan_library.py tests/test_atomic_scan.py tests/test_scan_changes.py tests/test_layering.py -q -m "not wurth"` | ✅ extend | ✅ green |
| 12-17-T1 | 12-17 | gap 5 (w2) | UI-01 | T-12-43 | Skip on the Loading Libraries window stops the shown source's 3D check through a lock-guarded request (G-12-21) | window | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py -q -k "scan or skip or busy or close or startup or rescan or post_install or saved"` | ✅ extend | ✅ green |
| 12-17-T2 | 12-17 | gap 5 (w2) | UI-01 | T-12-44, T-12-45 | Generate after a skip removes no table entry; a reused skipped scan never logs "No warnings." (G-12-21) | window | `env/Scripts/python.exe -m pytest tests/test_main_window.py -q -k "skip or saved or generate or reuse"` | ✅ extend | ✅ green |
| 12-17-T3 | 12-17 | gap 5 (w2) | UI-01 | — | N/A (Help Repository Scan and CLAUDE.md explain Skip and the saved scan; plan-level check, G-12-21) | unit + window | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py tests/test_help_dialog.py tests/test_plain_names.py tests/test_scan_skip.py tests/test_scan_cache.py tests/test_layering.py tests/test_importer_layering.py -q -m "not wurth"` | ✅ extend | ✅ green |
| 12-18-T1 | 12-18 | gap 5 (w3) | UI-01 | T-12-47 | One shared, parentless, non-modal User Guide; closed when the main window's close is accepted, kept when refused (G-12-22) | window | `env/Scripts/python.exe -m pytest tests/test_main_window.py -q -k "guide or close"` | ✅ extend | ✅ green |
| 12-18-T2 | 12-18 | gap 5 (w3) | UI-01 | T-12-46 | Import window shows the shared guide through a callable and stays window-modal over the main window; the guide outlives it (G-12-22) | window + dialog | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py tests/test_import_dialog.py tests/test_plain_names.py tests/test_importer_layering.py -q -m "not wurth"` | ✅ extend | ✅ green |
| 12-19-T1 | 12-19 | gap 5 (w4) | UI-01 | T-12-49, T-12-50 | Guide saves the owner's place and reopens there; tests never write the real settings.ini (G-12-23) | unit + dialog | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py tests/test_settings_import.py -q` | ✅ extend | ✅ green |
| 12-19-T2 | 12-19 | gap 5 (w4) | UI-01 | T-12-49 | Explicit topics win and are not remembered; stale saved places fall back (G-12-23) | dialog | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py tests/test_import_dialog.py -q -k "help or topic or guide or saved or stale"` | ✅ extend | ✅ green |
| 12-19-T3 | 12-19 | gap 5 (w4) | UI-01 | — | N/A (main-window Help and F1 reopen the owner's place; CLAUDE.md; plan-level check, G-12-23) | window + dialog | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py tests/test_main_window.py tests/test_main_window_import.py tests/test_import_dialog.py tests/test_settings_import.py tests/test_plain_names.py -q` | ✅ extend | ✅ green |
| 12-20-T1 | 12-20 | gap 5 (w5) | UI-01 | T-12-48 | Main-window dialogs are window-modal with their safe defaults; the guide stays usable beside them and the Loading Libraries window (G-12-22) | window | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py -q -m "not wurth"` | ✅ extend | ✅ green |
| 12-20-T2 | 12-20 | gap 5 (w5) | UI-01 | — | N/A (Help says the guide is its own window; plan-level check, G-12-22) | window + dialog | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py tests/test_import_dialog.py tests/test_help_dialog.py tests/test_plain_names.py tests/test_importer_layering.py -q -m "not wurth"` | ✅ extend | ✅ green |
| 12-21-T1 | 12-21 | gap 6 (w6) | UI-01 | T-12-51, T-12-54 | Reopened, re-asked and narrowed guides bring the chosen heading back; main-window Help on a guide left on an asked topic goes back to the owner's place; the in-memory asked-topic flag never saves (G-12-27 D1, D2, D6) | unit + window | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py tests/test_main_window.py -q -m "not wurth"` | ✅ extend | ✅ green |
| 12-21-T2 | 12-21 | gap 6 (w6) | UI-01 | T-12-52 | A held left click selects the pressed row; the hold ends on release, hide, key press or a live button check and never consumes an event (G-12-27 D3) | dialog | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py -q` | ✅ extend | ✅ green |
| 12-21-T3 | 12-21 | gap 6 (w6) | UI-01 | T-12-53 | Selected row painted from theme tokens with no stylesheet; arrows and indentation kept; Help and CLAUDE.md wording; tracer stays untracked (G-12-27 D4) | unit + plan-level | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py tests/test_import_dialog.py tests/test_help_dialog.py tests/test_plain_names.py tests/test_importer_layering.py -q -m "not wurth"` | ✅ extend | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

*Task IDs are `{plan}-T{n}` (task n of that PLAN.md). Wave 0 items are created by the task named in the File Exists column.*

---

## Wave 0 Requirements

- [x] `tests/casefixtures.py` — `case_sensitive_dir()` fixture (fsutil on Windows, real case-sensitivity probe, skip with stated reason) — 12-01-T1
- [x] `tests/test_case_sensitive_install.py` — rollback-with-twin and D-14 overwrite tests (T1–T4 per RESEARCH.md) — 12-01-T1 (T3), 12-01-T2 (T1, T2, T4, incoming_op)
- [x] `settle(qtbot, window)` helper and the `fake_sync` / `kicad_running` fixture change in `tests/test_main_window.py` and `tests/test_main_window_import.py` — 12-06-T1
- [x] join-workers teardown for dialog tests (RESEARCH.md Pitfall 3) — a `pytest_runtest_teardown` wrapper in `tests/conftest.py` that joins QThread children of registered widgets before pytest-qt closes them (order verified at planning) — 12-06-T1
- [x] `tests/README.md` expected-skips row for "could not make a case-sensitive folder" — 12-01-T2
- [x] `tests/test_backup_dialog.py` — blank backup folder tests — 12-04-T2
- [x] UI-01 token and heading-size tests in `tests/test_help_dialog.py` — 12-02-T1
- [x] autouse `_desktop_screen_area` fixture in `tests/conftest.py` (Full HD 100% desktop for the `screen_area` seam; patches nothing unless the import dialog module is loaded) — 12-13-T2
- [x] `tests/test_scan_skip.py` — skip-one-source scan tests (libraries and links kept, skip line, one-library rescan) — 12-16-T1
- [x] autouse `_isolated_settings(tmp_path)` in `tests/test_help_dialog.py` (asserts the settings file lies under tmp_path, T-12-50) — 12-19-T1

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Case-sensitive tests pass (not skip) on the owner's Windows machine | VER-02 | Skips are environment-dependent; only the workstation proves the fsutil path | From the repo root run `.\env\Scripts\python.exe -m pytest tests/test_case_sensitive_install.py -v -rs`; every test PASSED, no "skipped" in the summary |
| Help dialog and conflict rows look right with theme tokens | UI-01 | Visual check | Owner reviews rendered screenshots, as in Phase 11 UAT |
| Window stays responsive while kicad-cli works | REV-04 | Real kicad-cli timing | Open a package with a slow build, press Change...; window moves/repaints, strip shows, action runs by itself |
| Gap re-check: plain names, Cancel, required hints, Choose another package (UAT 5–8) | REV-04, REV-05 | Wording and layout in the running window | Re-run UAT tests 5–8 from 12-UAT.md in the GUI |
| Toolbar Help looks right in the import window (G-12-9) | UI-01 | Visual fit of the toolbar in the real window | Open an import, check the toolbar sits above every page and Help (or F1) opens the User Guide on Importing Parts while the import window stays usable (UAT test 9) |
| Import window fits a real Windows screen at 100% and 200% display scale (G-12-10, 12-13 D2) | UI-01, REV-04 | Tests model 200% in logical pixels on the offscreen platform; the real display scale and taskbar need a look | At 100% and then 200% (Settings > Display > Scale), open an import: the start page is small with Cancel at the bottom right; after a package loads the whole window, title bar and Install Part / Cancel are on screen above the taskbar; Choose another package... shrinks it back (12-13-PLAN.md Task 3 human-check) |
| Numbered User Guide menu and screen fit on a real display (G-12-11, 12-14 D5) | UI-01 | Visual check of numbering, section scroll and fit at real display scale | At 100% and 200%, press F1 in the import window: the guide is fully on screen with Close visible; the menu shows numbered groups, pages and Importing Parts sections; clicking 4.4.7 Conflicts scrolls to that heading; also open the guide from the main window (12-14-PLAN.md Task 3 human-check) |
| Compact import start window with Cancel on the Browse row at 100% and 200% (G-12-12) | UI-01 | Real display scale and taskbar | 12-15-PLAN.md Task 3 human-check: Ctrl+I, window compact with no empty band, grows for a package, shrinks on Choose another package..., Cancel closes; `git -C Custom status --short` unchanged |
| Skip on the Loading Libraries window with the real WurthElektronik library (G-12-21) | UI-01 | Real scan timing and log wording | 12-17-PLAN.md Task 3 human-check: delete `%APPDATA%\KiCadExtLibManager\scan_cache`, start, Skip WurthElektronik, check the log line, restart for the saved-scan note, Rescan clears it |
| User Guide reopens on the owner's last place across restarts (G-12-23) | UI-01 | Real settings.ini and visual selection | 12-19-PLAN.md Task 3 human-check |
| Guide usable beside About, the import window, its content view and Loading Libraries; closes with the main window (G-12-22) | UI-01 | Real window-system modality | 12-20-PLAN.md Task 2 human-check |
| Guide reopens on the chosen section with its heading at the top; a held click keeps the pressed row; the selected row stands out (G-12-27, UAT test 27, 12-21 D5) | UI-01 | Real mouse, windows11 style and display scaling; the step-1 order (Close, then F1) has no reproduced mechanism | 12-21-PLAN.md Task 3 human-check at 100% and 200%; blocking trace fallback with `.claude\debug\guide_trace.py` if row 4.4 or the page top shows where Conflicts is expected |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-11-01 (all 18 tasks green in the full suite at 9412c80: 9267 passed, 4 expected skips; manual-only rows stay with the owner UAT). Re-validated 2026-11-02 after gap plans 12-09..12-11: all 25 tasks green in the full suite at 60df383 (9281 passed, 4 expected skips). Re-validated 2026-11-03 after gap plan 12-12: all 28 tasks green in the full suite at 859170c (9290 passed, 4 expected skips). Re-validated 2026-11-04 after gap plans 12-13 and 12-14: all 34 tasks mapped; the 6 new tasks' 26 named tests all exist and the 11-file plan-level set (superset of every 12-13/12-14 verify command) ran green at ede1d97 (508 passed, 0 skipped, 257.9 s); full-suite phase gate run separately. Re-validated 2026-11-04 after gap plans 12-15..12-20: all 50 tasks mapped; the 16 new tasks all carry an automated verify and Wave 0 adds `tests/test_scan_skip.py` and the `_isolated_settings` fixture in `tests/test_help_dialog.py`; the 14-file union of every 12-15..12-20 verify command (`-m "not wurth"`) ran at ce4d71c: 632 passed, 1 failed, 1 deselected, 387.9 s. The one failure, `tests/test_import_dialog.py::test_footprint_name_edit_and_restore` (pre-existing, untouched by 12-15..12-20), was a 30 s preview-build `waitUntil` timeout while the orchestrator's full suite ran in parallel; it passed alone in 13.9 s (⚠️ load-sensitive, not a regression). Full-suite phase gate run separately by the orchestrator. Re-validated 2026-11-11 after gap plan 12-21: all 53 tasks mapped; the 3 new tasks all carry an automated verify and their 12 named tests exist in `tests/test_help_dialog.py` and `tests/test_main_window.py`; the post-merge full suite (`-m "not wurth"`) at 90c2db9 ran green: 3366 passed, 4 expected skips, 1115 s. The 12-21 executor's own full run had one failure, `tests/test_official_footprint.py::test_the_destination_choice_and_picker_fit_the_left_pane` (untouched by 12-21); it passed alone and in the post-merge run (⚠️ order- or timing-sensitive, not a regression). UAT test 27 stays with the owner (manual-only row above).

## Validation Audit 2026-11-01

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
