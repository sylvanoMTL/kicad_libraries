---
phase: "11"
slug: "commit-gate-and-commit-panel-fixes"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-29"
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-qt 4.5.0 (`qt_api = "pyside6"`) |
| **Config file** | `pyproject.toml` (`addopts = "-ra --strict-markers"`, `testpaths = ["tests"]`, `pythonpath = ["."]`) |
| **Quick run command** | `env/Scripts/python.exe -m pytest tests/test_commit_plan.py tests/test_commit_step.py tests/test_gitops.py tests/test_commit_panel.py tests/test_commit_gate.py -q` |
| **Full suite command** | `env/Scripts/python.exe -m pytest -m "not wurth"` |
| **Estimated runtime** | ~30 seconds quick; ~480 seconds full (not wurth) |

---

## Sampling Rate

- **After every task commit:** Run `{quick run command}`
- **After every plan wave:** Run `env/Scripts/python.exe -m pytest tests/test_commit_plan.py tests/test_commit_step.py tests/test_commit_panel.py tests/test_commit_gate.py tests/test_gitops.py tests/test_import_dialog.py tests/test_importer_layering.py tests/test_layering.py -q`
- **Before `/gsd-verify-work`:** Full suite must be green (the `tests/conftest.py` session guard fails the run if the live `Custom/` changes)
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Filled by the planner from the PLAN.md tasks. Requirement-to-test map from 11-RESEARCH.md § Validation Architecture:

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 11-02-T1/T2, 11-05-T1/T2 | 11-02, 11-05 | 1, 2 | GIT-06 | T-11-03, T-11-04, T-11-10 | a failing new or changed `Atomic_` part blocks the commit; linked parts broken by a committed footprint block; old failures do not | unit | `env/Scripts/python.exe -m pytest tests/test_commit_gate.py -q` | ❌ W0 (created by 11-02) | ⬜ pending |
| 11-08-T1 | 11-08 | 4 | GIT-06 | T-11-18 | probe gated; `_precheck` refuses at the click, no `add`/`commit` argv recorded | unit | `env/Scripts/python.exe -m pytest tests/test_commit_step.py -k "gated or recheck or stale" -q` | partial | ⬜ pending |
| 11-12-T1/T2 | 11-12 | 5 | GIT-06 | T-11-19 | Check again adds only the files a committed part links (exact `Custom/3DModels` listing, no path built from text); unrelated untracked files stay out | unit | `env/Scripts/python.exe -m pytest tests/test_commit_gate.py tests/test_commit_step.py -k "linked_custom_files or recheck_adds or recheck_leaves" -q` | ❌ W0 | ⬜ pending |
| 11-10-T1, 11-11-T1 | 11-10, 11-11 | 5, 6 | GIT-06 | T-11-23, T-11-27 | panel names part and rule, Commit disabled; recovery end to end in the dialog with remote refs unchanged | pytest-qt | `env/Scripts/python.exe -m pytest tests/test_commit_panel.py tests/test_import_dialog.py -k "gated or gate_refusal or open_check" -q` | ❌ W0 | ⬜ pending |
| 11-13-T1/T2 | 11-13 | 7 | GIT-06, REV-09 | T-11-25 | applied fixes rescan and re-check, never commit; changed files open their diff; nothing logged as uncommitted when Custom already holds the files | pytest-qt | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_main_window_import.py -k "fixes or changed_file or not_committed or not_logged or rescans" -q` | ❌ W0 | ⬜ pending |
| 11-06-T1 | 11-06 | 2 | REV-06 | T-11-12, T-11-13 | HEAD moved after timeout: no unstage, no parent commit | unit | `env/Scripts/python.exe -m pytest tests/test_commit_step.py -k timeout -q` | partial | ⬜ pending |
| 11-03-T1 | 11-03 | 1 | REV-07 | T-11-06 | preview equals committed text with and without a gitlink | unit | `env/Scripts/python.exe -m pytest tests/test_commit_plan.py tests/test_commit_step.py -k parent_message -q` | partial | ⬜ pending |
| 11-07-T1/T2 | 11-07 | 3 | REV-08 | T-11-15 | pasted manual command is injection-safe (unit both platforms + real PowerShell) | unit | `env/Scripts/python.exe -m pytest tests/test_commit_step.py -k manual -q` | ❌ W0 | ⬜ pending |
| 11-06-T2, 11-10-T3 | 11-06, 11-10 | 2, 5 | REV-09 | T-11-14 | identical file INFO, all-identical refusal, parent-only bump | unit + pytest-qt | `env/Scripts/python.exe -m pytest tests/test_commit_step.py tests/test_commit_panel.py -k "identical or parent_only or nothing" -q` | ❌ W0 | ⬜ pending |
| 11-04-T1, 11-09-T2 | 11-04, 11-09 | 1, 3 | REV-10 | T-11-08 | refusal then re-probe keeps message, parent choice and refusal text; a failed parent-only bump also re-probes | pytest-qt | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_commit_panel.py -k reprobe -q` | ❌ W0 | ⬜ pending |
| 11-01-T1/T2, 11-07-T3, 11-04-T1, 11-09-T1 | 11-01, 11-07, 11-04, 11-09 | 1, 3, 1, 3 | REV-11 | T-11-01, T-11-21, T-11-22 | only six identity variables re-admitted; repo-redirect variables stripped; Close during probe | unit + pytest-qt | `env/Scripts/python.exe -m pytest tests/test_gitops.py tests/test_commit_step.py tests/test_import_dialog.py tests/test_commit_panel.py -k "identity or close_during_probe or parent_choice" -q` | partial | ⬜ pending |
| 11-04-T2, 11-09-T2 | 11-04, 11-09 | 1, 3 | UI-02 | T-11-09 | N/A | pytest-qt | `env/Scripts/python.exe -m pytest tests/test_commit_panel.py tests/test_import_dialog.py -k "primary or tint or label" -q` | partial | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_commit_gate.py` — superproject with `Atomic_` fixtures (`make_superproject` + `customfixtures.write_atomic_files`), failing and passing symbols for GIT-06
- [ ] `tests/test_importer_layering.py` — register `importer.commit_gate` in `ALLOWED`, widen `importer.commit_step`
- [ ] `tests/test_import_dialog.py` — helpers that wait on `is_committing()` for the probe; `tests/test_gitops.py:101-107` strip behaviour
- [ ] `tests/README.md` — live-PowerShell skip row
- [ ] `widgets/help_dialog.py` Commit section text (dialog closable during probe) and `tests/test_help_dialog.py` pinned text

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The pasted "finish it by hand" command runs as shown in a real PowerShell window | REV-08 | Needs a real interactive paste into PowerShell 5.1 | Trigger a parent-commit failure with a subject holding `'`, `$` and a backtick; copy the command into PowerShell; check the parent commit message matches |
| Commit panel look: primary button, tinted outcome strips, "Committed in Custom only" label | UI-02 | Visual check | Run an import to the Result view; commit success, error and parent-failed cases; compare to the theme |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
