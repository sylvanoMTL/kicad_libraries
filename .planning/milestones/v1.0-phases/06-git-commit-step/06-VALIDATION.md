---
phase: "6"
slug: "git-commit-step"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-22"
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-qt 4.5.0 (`qt_api = "pyside6"`, `QT_QPA_PLATFORM=offscreen` forced in `tests/conftest.py`), real `git` (2.49.0.windows.1) driven in `tmp_path` repos |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths = ["tests"]`, `--strict-markers`) |
| **Quick run command** | `./env/Scripts/python.exe -m pytest tests/test_gitops.py tests/test_commit_plan.py -x -q` |
| **Full suite command** | `./env/Scripts/python.exe -m pytest -q` (7 real-kicad-cli tests already fail on the phase base, per RESEARCH.md / STATE.md; they are the only accepted failures) |
| **Estimated runtime** | ~130 seconds full suite (Phase 5 baseline ~110 s; the real-git fixtures add time), quick run estimated under 60 s |

---

## Sampling Rate

- **After every task commit:** Run the quick run command, plus the touched test file(s), e.g. `./env/Scripts/python.exe -m pytest tests/test_commit_panel.py -x -q`
- **After every plan wave:** Run `./env/Scripts/python.exe -m pytest tests/test_gitops.py tests/test_commit_plan.py tests/test_commit_panel.py tests/test_import_dialog.py tests/test_layering.py tests/test_importer_layering.py -x -q`
- **Before `/gsd-verify-work`:** Full suite green except the 7 known kicad-cli failures, then the manual UAT below
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

Filled in by the planner/executor per task. Requirement → test map from RESEARCH.md:

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| GIT-01 | Probe reports branch or detached HEAD; panel shows branch, exact files, editable message; Commit disabled for a blank message | unit + pytest-qt | `pytest tests/test_gitops.py::test_probe_branch_and_detached tests/test_commit_panel.py -x -q` | ❌ W0 | ⬜ pending |
| GIT-02 | Only listed files committed with staged/unstaged/untracked bystanders present; new + existing files; literal pathspec with `[ ]`; parent commit touches only `Custom` with a staged `.planning` file present | unit (real git in tmp_path) | `pytest tests/test_gitops.py -k "commit_only or literal or parent" -x -q` | ❌ W0 | ⬜ pending |
| GIT-02 | D-11 stale file refuses; D-09 dirty-before flag with `core.autocrlf` true and false | unit | `pytest tests/test_commit_plan.py tests/test_gitops.py -k "stale or dirty_before" -x -q` | ❌ W0 | ⬜ pending |
| GIT-03 | Detached on main history offers switch; switch carries changes; detached off-history refuses; switch conflict leaves HEAD detached and commits nothing; no local `main` uses `origin/main` | unit | `pytest tests/test_gitops.py -k "detached or switch" -x -q` | ❌ W0 | ⬜ pending |
| GIT-04 | Default message has subject + Import-Vendor/Package/Date trailers parsed by `%(trailers)`; control characters in package name stripped; user-edited message committed verbatim | unit | `pytest tests/test_commit_plan.py -x -q` | ❌ W0 | ⬜ pending |
| GIT-05 | Recorded argv never contains `push`; allow-list rejects it; bare remotes' `for-each-ref` identical before/after a full commit; no `"push"` literal in `gitops.py` / `commit_panel.py` | unit | `pytest tests/test_gitops.py -k "no_push" -x -q` | ❌ W0 | ⬜ pending |
| D-03 | Parent hook rejects → Custom commit stays, ERROR carries stderr and the manual command | unit | `pytest tests/test_gitops.py -k "parent_fails" -x -q` | ❌ W0 | ⬜ pending |
| D-05/D-16 | git absent (monkeypatched `shutil.which` / runner), Custom not its own toplevel, merge in progress in Custom or parent | unit | `pytest tests/test_gitops.py -k "unavailable or busy" -x -q` | ❌ W0 | ⬜ pending |
| D-06 | Failing `pre-commit` hook: rc≠0, stdout+stderr surfaced, HEAD unchanged, intent-to-add undone | unit | `pytest tests/test_gitops.py -k hook -x -q` | ❌ W0 | ⬜ pending |
| D-07/D-08 | Panel state machine; Close/Esc blocked while committing; no panel on no-op/failed install; WR-04 guard | pytest-qt | `pytest tests/test_commit_panel.py tests/test_import_dialog.py -k "commit or install_guard" -x -q` | ❌ W0 / edit existing | ⬜ pending |
| Layering | `gitops` Qt-free, imports `models` only; `importer.commit_plan` registered | unit | `pytest tests/test_layering.py tests/test_importer_layering.py -x -q` | ✅ (edit existing) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/gitfixtures.py` — bare remotes, parent + submodule + linked-worktree builders with config isolation (`GIT_CONFIG_GLOBAL=<tmp>/gitconfig`, `GIT_CONFIG_NOSYSTEM=1`, `protocol.file.allow=always`, `commit.gpgsign=false`), `core.autocrlf` true/false parametrization, module skip when `shutil.which("git")` is `None`
- [ ] `tests/test_gitops.py` — covers GIT-01..GIT-05, D-03, D-05, D-06, D-16
- [ ] `tests/test_commit_plan.py` — covers GIT-04, D-09, D-11
- [ ] `tests/test_commit_panel.py` — pytest-qt panel state machine
- [ ] Edit `tests/test_import_dialog.py:2743-2744` (commit slot hidden / zero-height assertion) in the same plan that changes the slot
- [ ] Register `gitops` and `importer.commit_plan` in `tests/test_layering.py` and `tests/test_importer_layering.py`

Framework install: none (pytest and pytest-qt already present; Git Bash `sh` bundled with Git for Windows runs the fixture hooks).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real import followed by a confirmed commit in the owner's repo | GIT-01..GIT-05 | Real `Custom` submodule, real worktree-private gitdir, real remotes | Import a real Ultra Librarian zip, click Commit with the parent box ticked, then run `git -C Custom status`, `git -C Custom log -1 --stat`, `git log -1 --stat` and `git -C Custom rev-list --count @{u}..HEAD`; confirm the remote is unchanged (`git -C Custom ls-remote origin` equals `git -C Custom rev-parse origin/main`). The owner must push `Custom` before removing the worktree (STATE.md). |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
