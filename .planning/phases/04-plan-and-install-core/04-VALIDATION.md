---
phase: "4"
slug: "plan-and-install-core"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-19"
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (pytest-qt 4.5.0 installed; Phase 4 tests need no Qt) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`, `addopts = "-ra --strict-markers"`) |
| **Quick run command** | `./env/Scripts/python.exe -m pytest tests/test_install_plan.py -x -q` (or the task's own targeted test file) |
| **Full suite command** | `./env/Scripts/python.exe -m pytest -q` |
| **Estimated runtime** | ~25 seconds (baseline 909 passed / 4 skipped before Phase 4) |

---

## Sampling Rate

- **After every task commit:** Run the task's own targeted test file with `-x -q` (under 10 s)
- **After every plan wave:** Run `./env/Scripts/python.exe -m pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green, including the `kicad_cli` tests on this machine
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

Seeded per requirement from `04-RESEARCH.md` § Validation Architecture. Task IDs, plans and waves are filled in once the plans exist.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | INST-01 | — | Symbol added; header and every other symbol byte-identical | unit + e2e | `./env/Scripts/python.exe -m pytest tests/test_install_e2e.py::test_ul_symbol_added_others_identical -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-02 | — | Rename follows `_u_s` sub-symbols and `extends`; exact match only, no substring rewrite | unit | `./env/Scripts/python.exe -m pytest tests/test_kicad_files_write.py -k rename -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-03 | path traversal via names | Footprint filename, internal name, value, Footprint field and `ki_fp_filters` agree; names sanitised | unit + e2e | `./env/Scripts/python.exe -m pytest tests/test_install_plan.py -k footprint_consistency -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-04 | TOCTOU on model bytes | Model copied as `CSD85301Q2.stp`; same SHA-256 reused; different SHA-256 or case twin is a conflict | unit | `./env/Scripts/python.exe -m pytest tests/test_install_plan.py -k model -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-05 | — | Missing `(model` block inserted; existing path retargeted; offsets kept | unit | `./env/Scripts/python.exe -m pytest tests/test_kicad_files_write.py -k model -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-06 | hostile S-expression sent to `kicad-cli` | Version table (equal / older + CLI match / older + CLI mismatch / no CLI / newer refused); CLI run with timeout and list argv in a temp dir | unit + `kicad_cli` | `./env/Scripts/python.exe -m pytest tests/test_install_plan.py -k version -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-07 | rollback half-state | Fault injected on every write, backup, verify and undo step leaves the tree byte-identical, no `.tmp`, no new dirs | unit | `./env/Scripts/python.exe -m pytest tests/test_install_apply.py -k rollback -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-08 | — | Hard verify failures (broken link, missing model, bad parse) trigger rollback | unit | `./env/Scripts/python.exe -m pytest tests/test_install_verify.py -k hard -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-09 | — | Second identical install: no file ops, nothing touched, no backup folder | e2e | `./env/Scripts/python.exe -m pytest tests/test_install_e2e.py::test_second_install_is_noop -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INTK-08 | — | No model: installs, `install.no_model` WARNING, no model block, no `3DModels` write | unit | `./env/Scripts/python.exe -m pytest tests/test_install_plan.py -k no_model -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LIB-02 | write outside `Custom/` | New library creates the `.kicad_sym` + `.pretty` pair; existing header never changed; case-twin library is an ERROR; placeholder name refused | unit + e2e | `./env/Scripts/python.exe -m pytest tests/test_install_plan.py -k library -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | POST-03 | — | Name found in another library warned; target library excluded | unit | `./env/Scripts/python.exe -m pytest tests/test_install_verify.py -k elsewhere -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | POST-04 | — | Pin/pad mismatch warned both ways; empty-number pads ignored; `extends` child pins read from the parent | unit | `./env/Scripts/python.exe -m pytest tests/test_install_verify.py -k pin_pad -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | (D-03 / D-22) | — | Real `kicad-cli` load check of the UL install result (skipped when absent) | `kicad_cli` e2e | `./env/Scripts/python.exe -m pytest tests/test_install_e2e.py -m kicad_cli -x` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | (layering) | — | New importer modules registered and Qt-free | static | `./env/Scripts/python.exe -m pytest tests/test_importer_layering.py tests/test_layering.py -x -q` | ✅ (edit) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `pyproject.toml` — register the `kicad_cli` marker (`--strict-markers` is on)
- [ ] `tests/conftest.py` — fixtures `custom_copy` (copy `Custom/Symbols`, `Footprints`, `3DModels` into `tmp_path/Custom`, excluding `.git`; skip if the submodule is absent), `ul_package` (open the UL zip, yield the candidate, close), `kicad_cli_path` (locate or skip), and a `snapshot(root)` helper
- [ ] `tests/installfixtures.py` — byte builders for an `extends` parent/child pair, a vendor symbol with `MF`/`MP`/`MANUFACTURER` fields, a footprint that already has a `(model ...)` block, a footprint with an extra exposed pad, and synthetic target libraries at `20211014` (CRLF, blank first line, 2-space indent, ids), `20231120` and `20241209` (tab indent). Built at test time; no copied real libraries committed
- [ ] `tests/test_importer_layering.py` — register the new importer modules in `ALLOWED`
- [ ] A fake `kicad-cli` runner for `tests/test_kicad_cli.py` and the version-table tests (scripted exit codes, outputs, and the "not updated" no-output case)
- [ ] Framework install: none (pytest already present)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The installed UL part opens correctly in KiCad 9 | INST-01, INST-03, INST-05 (D-22) | Needs the KiCad GUI: symbol editor, footprint editor and 3D viewer | Install the UL sample into a scratch copy of `Custom/`, add that copy's libraries in KiCad 9, open the symbol, the footprint and the 3D view, and confirm all three show correctly |
| Mixed-version library loads on KiCad 10 | INST-06 (assumption A1) | KiCad 10 is not installed on this machine | When KiCad 10 is available, open a `20241209` library holding a spliced `20211014` symbol and confirm it loads |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
