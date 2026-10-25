---
phase: "8"
slug: "test-isolation-and-kicad-10"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-25"
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-qt 4.5.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths `tests`, `addopts = "-ra --strict-markers"`, markers `wurth`, `local_kicad`, `kicad_cli`) |
| **Quick run command** | `env/Scripts/python.exe -m pytest -q -m "not wurth" tests/test_customfixtures.py tests/test_installfixtures.py tests/test_install_e2e.py tests/test_install_plan.py tests/test_install_apply.py tests/test_import_preview.py tests/test_commit_plan.py tests/test_kicad_cli.py` |
| **Full suite command** | `env/Scripts/python.exe -m pytest` |
| **Estimated runtime** | ~320 seconds baseline (5 min 21 s); longer once the WurthElektronik submodule is checked out |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (no Wurth, no full suite)
- **After every plan wave:** Run `env/Scripts/python.exe -m pytest -m "not wurth"`
- **Before `/gsd-verify-work`:** Full suite (Wurth included) must be green
- **Max feedback latency:** ~120 seconds for the quick run

---

## Per-Task Verification Map

Filled in by the planner/executor once task IDs exist. Requirement-level map from research:

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| TEST-01 | Fixture holds the four format versions with today's names, lacks CSD85301Q2 / DQK0006B / its model, parses, `IC_IMU_TDK` has no `.pretty`, `IC_MOSFET_Dual_TI` absent | unit | `env/Scripts/python.exe -m pytest tests/test_customfixtures.py -x` | ❌ W0 | ⬜ pending |
| TEST-01 | The 14 formerly live-dependent tests pass on the fixture | integration | `env/Scripts/python.exe -m pytest tests/test_commit_plan.py tests/test_import_preview.py tests/test_install_apply.py tests/test_install_e2e.py tests/test_install_plan.py tests/test_import_dialog.py -x` | ✅ (rename) | ⬜ pending |
| TEST-01 | No test references `custom_copy` or copies the live tree | static | `grep -rn "custom_copy" tests --include=*.py` returns nothing | n/a | ⬜ pending |
| TEST-01 | Suite result independent of live parts | proof run | Copy the repo (without `env/`, `.git`, `Custom/`) to a scratch dir outside the repo and run the six files above; expect pass | manual command | ⬜ pending |
| TEST-01 | 20251024 builder equals what KiCad 10 writes | real-binary | `env/Scripts/python.exe -m pytest tests/test_installfixtures.py -k 20251024 -m kicad_cli` | ❌ W0 | ⬜ pending |
| TEST-02 | Real-binary tests expect 20251024 / `"10.0"` | real-binary | `env/Scripts/python.exe -m pytest -m kicad_cli -v` | ✅ (edit) | ⬜ pending |
| TEST-02 | Skip with reason when the located CLI is not major 10 (none, 9.x, 11.x, unparsable) | unit | Monkeypatched gate test in `tests/` (cache cleared per test) | ❌ W0 | ⬜ pending |
| TEST-03 | Bare `pytest` reports 0 failures; only documented skips | full run | `env/Scripts/python.exe -m pytest -rs`, compare skip list with `tests/README.md` | n/a | ⬜ pending |
| TEST-03 | Guard fails when the live `Custom/` changes | unit | Digest function run on a `tmp_path` tree; changed file reported | ❌ W0 | ⬜ pending |
| VER-01 | As-is row on KiCad 10: D-01 warning, header stays 20241209, load gate clean | real-binary | `env/Scripts/python.exe -m pytest "tests/test_install_e2e.py::test_cli_version_scenarios" -m kicad_cli` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/customfixtures.py` and `tests/test_customfixtures.py` (TEST-01)
- [ ] 20251024 rows in `tests/test_installfixtures.py` plus the real-CLI fixed-point test (D-03)
- [ ] `tests/conftest.py`: synthetic `Custom/` fixture, cached KiCad 10 gate with its tests, shared `real_tools` fixture, session write-protect guard with a unit test of its failure path
- [ ] `tests/README.md` (skip table and live-`Custom/` rule)
- [ ] Framework install: none (pytest and pytest-qt already in the venv)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Owner opens the installed 20241209 scratch library in KiCad 10's Symbol Editor and places CSD85301Q2 | VER-01 | Needs the KiCad 10 GUI | Set `KICAD_IMPORT_UAT_DIR` to a scratch folder, run `env/Scripts/python.exe -m pytest tests/test_install_e2e.py::test_uat_scratch_install`, open the library in KiCad 10 and place the part |
| WurthElektronik submodule checked out in this worktree | TEST-03 | One-off workstation setup | `git submodule update --init WurthElektronik/KiCad-Library` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
