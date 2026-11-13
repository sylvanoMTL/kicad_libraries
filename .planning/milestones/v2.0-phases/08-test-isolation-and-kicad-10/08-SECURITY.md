---
phase: "8"
slug: "test-isolation-and-kicad-10"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-25"
---

# Phase 8 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| test process -> kicad-cli binary | The suite starts an external program found on the machine | argv lists only; version text and exported KiCad files back |
| kicad-cli stdout -> gate | The version text decides whether real-binary tests run | untrusted text, parsed by an anchored regex |
| test suite -> live Custom/ (owner data) | Tests run in the owner's checkout next to the curated libraries | owner library files (must never be written) |
| guard test -> child pytest process | A subprocess runs generated test files under tmp_path | generated test files under tmp_path |
| migrated tests -> filesystem | Install, rollback and preview tests write KiCad files | KiCad files under tmp_path only |
| KICAD_IMPORT_UAT_DIR (owner-set env var) -> filesystem writes | The manual hook writes a scratch Custom/ where the variable points | synthetic library files outside the repository |
| GitHub (WurthElektronik/KiCad-Library) -> worktree | Third-party library content enters the worktree as a submodule | read-only test corpus at the pinned gitlink |
| test results -> planning records | Records claim a verification happened | test ids and kicad-cli version |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-08-01 | Elevation of Privilege | `tests/clifixtures.py` locating kicad-cli | medium | mitigate | Located only via `kicad_cli.locate_kicad_cli` (`tests/clifixtures.py:53`) and run only via `kicad_cli.run_cli(exe, ["version"], timeout=VERSION_TIMEOUT)` (`tests/clifixtures.py:34`) | closed |
| T-08-02 | Tampering | parsing `kicad-cli version` output | low | mitigate | Anchored `_VERSION_RE` with `.match` and a major-10 check (`tests/clifixtures.py:27,42-43`); every other output skips with a reason, pinned by 9 tests in `tests/test_clifixtures.py` | closed |
| T-08-03 | Tampering | live `Custom/` during a test run | high | mitigate | Session autouse `_live_custom_untouched` delegating to `guard_custom(REPO_ROOT / "Custom")` (`tests/conftest.py:129-136`); failure path proven by the subprocess guard tests (`-k guard`, 2 passed); full runs left `git -C Custom status` empty | closed |
| T-08-04 | Tampering | generated files of the guard subprocess test | low | mitigate | Child run uses `-p no:cacheprovider` and a tmp_path run dir (`tests/test_customfixtures.py:262`) | closed |
| T-08-05 | Tampering | install and rollback tests in test_install_apply.py / test_import_dialog.py | medium | mitigate | Both files use `synthetic_custom`; `custom_copy` has 0 references in `tests/**/*.py`; session guard active | closed |
| T-08-06 | Tampering | `test_uat_scratch_install` writing a scratch tree | high | mitigate | Outside-repo and not-a-parent asserts, link refusal, scratch tree from `write_synthetic_custom` (`tests/test_install_e2e.py:582-589`) | closed |
| T-08-07 | Elevation of Privilege | real kicad-cli runs in scenarios and the UAT hook | low | mitigate | Binary only from the shared `real_tools` / `kicad_cli_path` gate; module-local `real_tools` removed from `tests/test_install_e2e.py` | closed |
| T-08-08 | Elevation of Privilege | module-local kicad-cli lookups in three test modules | low | mitigate | No `_real_tools`, `real_exe` or own `shutil.which("kicad...")` lookup remains under `tests/` | closed |
| T-08-09 | Tampering | UL-plan tests in test_install_plan.py | medium | mitigate | Targets are `synthetic_custom` or tmp_path layouts; live-tree snapshot replaced by the session guard | closed |
| T-08-10 | Tampering | WurthElektronik submodule checkout | medium | mitigate | `git submodule status` shows the pinned `2e6e51b1bd78f89b31c358214642ba7e795872e0` with no `+`; the `objects/info/alternates` file is gone (dissociated) | closed |
| T-08-11 | Repudiation | PROJECT.md / 04-UAT.md / 08-UAT.md records | low | mitigate | `08-UAT.md` test 1 `result: pass` (automated, cites test id and kicad-cli 10.0.7); test 2 (owner's Symbol Editor check) `result: [pending]` for `/gsd-verify-work 8` | closed |
| T-08-12 | Tampering | live Custom/ during the full run and the scratch-copy proof | high | mitigate | Live-copy fixture deleted; session guard active for the full run (8063 passed, guard did not trip); proof copy ran in a `mktemp -d` folder without `Custom/` | closed |
| T-08-SC | Tampering | npm/pip/cargo installs | low | accept | No packages installed in this phase; the git submodule is covered by T-08-10 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-08-01 | T-08-SC | Phase 8 installs no npm/pip/cargo packages (RESEARCH Package Legitimacy Audit: none); the only third-party content is the pinned WurthElektronik submodule, handled by T-08-10 | planner (plan-time disposition) | 2026-10-25 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-25 | 13 | 13 | 0 | secure-phase (L1 grep verification, execute-phase verify:post) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-25
