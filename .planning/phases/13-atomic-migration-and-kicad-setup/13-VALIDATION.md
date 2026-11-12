---
phase: "13"
slug: "atomic-migration-and-kicad-setup"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-11"
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-qt 4.5.0 (PySide6, offscreen) |
| **Config file** | pyproject.toml [tool.pytest.ini_options] |
| **Quick run command** | `C:/Git_Repo_Clones/Kicad_Libraries-importer/env/Scripts/python.exe -m pytest <targeted files> -q` |
| **Full suite command** | `C:/Git_Repo_Clones/Kicad_Libraries-importer/env/Scripts/python.exe -m pytest` |
| **Estimated runtime** | ~13 seconds per targeted run; ~29 minutes for the full suite (9650+ tests after gap closure 13-22) |

---

## Sampling Rate

- **After every task commit:** Run `{quick run command}`
- **After every plan wave:** Run `{full suite command}`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 13 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 13-01-01..02 | 01 | 1 | TBL-01 | T-13-01, T-13-02 | descriptions quoted; bounded stock read | unit + qtbot | `pytest tests/test_table_descriptions.py tests/test_table_merge.py tests/test_table_add_entries.py tests/test_write_tables.py tests/test_main_window.py -q` | ✅ | ✅ green |
| 13-02-01..03 | 02 | 1 | TBL-02 (D-26) | T-13-03..06 | no write without confirm; worktree / other-checkout refusal; verify before write | unit | `pytest tests/test_kicad_setup.py tests/test_checkout_check.py tests/test_kicad_config.py tests/test_layering.py -q` | ✅ | ✅ green |
| 13-03-01..02 | 03 | 1 | MIG-01 | T-13-07..09 | constant tag name; never force or push; refuse dirty tree | real git | `pytest tests/test_migration_precheck.py tests/test_gitops.py tests/test_importer_layering.py -q` | ✅ | ✅ green |
| 13-04-01..02 | 04 | 1 | MIG-04 | T-13-10..12 | deleted file fresh only while absent; ignored files refused | unit + real git | `pytest tests/test_commit_deletions.py tests/test_commit_plan.py tests/test_commit_panel.py -q` | ✅ | ✅ green |
| 13-05-01..02 | 05 | 2 | MIG-02, MIG-03 | T-13-13, T-13-14 | bounded parse; no link following | unit | `pytest tests/test_migration_inventory.py tests/test_install_plan.py tests/test_importer_layering.py -q` | ✅ | ✅ green |
| 13-07-01..02 | 07 | 2 | TBL-02 | T-13-18, T-13-19 | confirm before write; check off the GUI thread | qtbot | `pytest tests/test_main_window_chooser.py tests/test_main_window.py tests/test_help_dialog.py -q` | ✅ | ✅ green |
| 13-06-01..02 | 06 | 3 | MIG-02, MIG-03, MIG-05 | T-13-15..17 | ops inside Custom; reverse rollback | unit + tmp tree | `pytest tests/test_migration_e2e.py tests/test_importer_layering.py -q` | ✅ | ✅ green |
| 13-08-01..02 | 08 | 3 | MIG-02 | T-13-20, T-13-21 | hostile draft = no draft; draft outside repo | unit | `pytest tests/test_migration_draft.py tests/test_settings_import.py -q` | ✅ | ✅ green |
| 13-19-01..02 | 19 | 3 | TBL-01, MIG-04 (D-26) | T-13-43, T-13-44 | visible non-blocking warning; plain text | qtbot | `pytest tests/test_checkout_warning.py tests/test_main_window_import.py tests/test_help_dialog.py -q` | ✅ | ✅ green |
| 13-09-01..03 | 09 | 4 | MIG-02, MIG-03 | T-13-22, T-13-23 | sanitised names; one format per library | unit | `pytest tests/test_migration_symbols.py tests/test_migration_e2e.py -q` | ✅ | ✅ green |
| 13-10-01..03 | 10 | 4 | MIG-02, MIG-03 | T-13-24..26 | never write KiCad's files; model intake checks; board features kept | unit | `pytest tests/test_migration_footprints.py tests/test_migration_e2e.py -q` | ✅ | ✅ green |
| 13-11-01..02 | 11 | 4 | MIG-02, MIG-03 | T-13-27 | derive only identical members | unit (+ real kicad-cli, may skip) | `pytest tests/test_migration_families.py -q` | ✅ | ✅ green |
| 13-12-01..02 | 12 | 4 | MIG-02, MIG-04, MIG-05 | T-13-28, T-13-29 | end-state gate; safe map text | unit | `pytest tests/test_migration_gate.py tests/test_migration_map.py -q` | ✅ | ✅ green |
| 13-13-01..03 | 13 | 4 | MIG-01, MIG-03, MIG-04 | T-13-30..33 | containment, stale checks, rollback, no .bak in commit | unit + real git | `pytest tests/test_migration_apply.py tests/test_migration_commit.py -q` | ✅ | ✅ green |
| 13-14-01..03 | 14 | 4 | MIG-01, MIG-02 | T-13-34, T-13-35 | plain-text widgets; workers only | qtbot | `pytest tests/test_migration_dialog.py tests/test_plain_names.py -q` | ✅ | ✅ green |
| 13-15-01..03 | 15 | 5 | MIG-02, MIG-03 | T-13-36, T-13-37 | bounded diff on a worker | qtbot | `pytest tests/test_migration_dialog_files.py tests/test_migration_dialog.py -q` | ✅ | ✅ green |
| 13-20-01 | 20 | 5 | MIG-01, MIG-03..05 | T-13-46 | whole-fixture test never touches the live Custom | real git | `pytest tests/test_migration_full.py -q` (the plan's gate; no other task runs it) | ✅ | ✅ green |
| 13-21-01..03 | 21 | 5 | MIG-02, MIG-03 (CR-01) | T-13-47..52 | claimed-name registry blocks two models onto one file; duplicate-write preflight refusal; in-run Overwrite refused | unit + tmp tree | `pytest tests/test_migration_footprints.py tests/test_migration_apply.py tests/test_migration_gate.py tests/test_migration_full.py -q` | ✅ | ✅ green |
| 13-22-01..03 | 22 | 6 | MIG-02, MIG-03 (CR-01 second manifestation) | T-13-53..57 | casefolded existing-model guard keeps a case-colliding model's on-disk name (INFO note, Run stays enabled); rename-would-overwrite preflight refusal; chain rename never planned | unit + tmp tree + e2e | `pytest tests/test_migration_e2e.py tests/test_migration_footprints.py tests/test_migration_apply.py tests/test_migration_gate.py tests/test_migration_dialog_files.py tests/test_migration_dialog_run.py tests/test_importer_layering.py tests/test_migration_full.py -q` | ✅ | ✅ green |
| 13-16-01..02 | 16 | 6 | MIG-01, MIG-03..05 (D-26) | T-13-38, T-13-39, T-13-45 | wrong-checkout refusal; no close mid-run; commit only on click | qtbot | `pytest tests/test_migration_dialog_run.py tests/test_migration_dialog.py -q` | ✅ | ✅ green |
| 13-17-01..03 | 17 | 7 | MIG-02, MIG-04, TBL-01 | T-13-40, T-13-41 | one writer at a time; tables keep Atomic_ libraries | qtbot | `pytest tests/test_main_window_migration.py tests/test_help_dialog.py -q` | ✅ | ✅ green |
| 13-18-01..02 | 18 | 8 | DOC-01 (+ UAT of all) | T-13-42 | docs test never touches live Custom | unit + manual | `pytest tests/test_docs_atomic.py -q`; full suite (with the slow real-git files) in the background as the phase gate | ✅ | ✅ green |

All commands run as `C:/Git_Repo_Clones/Kicad_Libraries-importer/env/Scripts/python.exe -m pytest ...` from the checkout or worktree root.

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Every test file named in the map above was created by its plan and exists on the merged branch (38 files).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live migration of the owner's Custom/, chooser setup in KiCad 10, table regeneration, commit, wrong-checkout notice | MIG-01..05, TBL-01, TBL-02, DOC-01, D-26 | runs on the live submodule and the owner's KiCad settings, which tests must never touch | 13-18 Task 2 `<human-check>` (where to run, setup a-d, checks 1-12; the real run is in the app started from the main checkout `C:/Git_Repo_Clones/Kicad_Libraries` that `KICAD_LIB_GITHUB` names) |

*If none: "All phase behaviors have automated verification."*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (none remained; each plan created its own test file)
- [x] No watch-mode flags
- [x] Feedback latency < 13s for targeted runs
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-12 (execute-phase validation audit)

**Evidence:** gap-closure plan 13-22 (CR-01 second manifestation, casefolded model guard) merged on `24ba91b` and the full suite passed on that tree (9653 passed, 4 skipped, 29 min 46 s, 2026-11-12); gap-closure plan 13-21 (CR-01) merged on `acc1be1` and the full suite passed on that tree (9646 passed, 4 skipped, 26 min, 2026-11-12); earlier: per-wave full-suite gates passed on every merge through wave 6 (last: 9626 passed, 4 skipped on `29c22ec`); plans 13-17 and 13-18 passed their own verification commands (222 and 71 tests) plus a 510-test regression sweep; the final full-suite run on `a5466ce` was stopped at 73% by the host for low system memory with zero failures recorded, and was not rerun (owner decision 2026-11-12).

## Validation Audit 2026-11-12

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Manual-only | 1 |
