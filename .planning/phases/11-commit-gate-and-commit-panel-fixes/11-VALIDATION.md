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
| TBD | — | — | GIT-06 | — | a failing new or changed `Atomic_` part blocks the commit; nothing is written | unit | `env/Scripts/python.exe -m pytest tests/test_commit_gate.py -q` | ❌ W0 | ⬜ pending |
| TBD | — | — | GIT-06 | — | `_precheck` refuses at the click, no `add`/`commit` argv recorded | unit | `env/Scripts/python.exe -m pytest tests/test_commit_step.py -k gate -q` | ❌ W0 | ⬜ pending |
| TBD | — | — | REV-06 | — | HEAD moved after timeout: no unstage, no parent commit | unit | `env/Scripts/python.exe -m pytest tests/test_commit_step.py -k timeout -q` | partial | ⬜ pending |
| TBD | — | — | REV-07 | — | N/A | unit | `env/Scripts/python.exe -m pytest tests/test_commit_plan.py tests/test_commit_step.py -k parent_message -q` | partial | ⬜ pending |
| TBD | — | — | REV-08 | — | pasted manual command is injection-safe | unit | `env/Scripts/python.exe -m pytest tests/test_commit_step.py -k manual -q` | ❌ W0 | ⬜ pending |
| TBD | — | — | REV-09 | — | N/A | unit | `env/Scripts/python.exe -m pytest tests/test_commit_step.py -k identical -q` | ❌ W0 | ⬜ pending |
| TBD | — | — | REV-10 | — | N/A | pytest-qt | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_commit_panel.py -k reprobe -q` | ❌ W0 | ⬜ pending |
| TBD | — | — | REV-11 | — | only six identity variables re-admitted; repo-redirect variables stripped | unit + pytest-qt | `env/Scripts/python.exe -m pytest tests/test_gitops.py tests/test_commit_step.py tests/test_import_dialog.py -k "identity or probe_close or parent_choice" -q` | partial | ⬜ pending |
| TBD | — | — | UI-02 | — | N/A | pytest-qt | `env/Scripts/python.exe -m pytest tests/test_commit_panel.py tests/test_import_dialog.py -k "primary or tint or label" -q` | partial | ⬜ pending |

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
