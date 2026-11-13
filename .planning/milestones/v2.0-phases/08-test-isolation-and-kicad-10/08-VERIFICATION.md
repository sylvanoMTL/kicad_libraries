---
phase: 08-test-isolation-and-kicad-10
verified: 2026-10-25T20:30:00Z
status: passed
score: 4/4 roadmap success criteria verified (automated); 1 backstop truth (owner's KiCad 10 Symbol Editor check) awaiting human
covered_files:
  - .planning/phases/08-test-isolation-and-kicad-10/08-01-PLAN.md
  - .planning/phases/08-test-isolation-and-kicad-10/08-01-SUMMARY.md
  - .planning/phases/08-test-isolation-and-kicad-10/08-02-PLAN.md
  - .planning/phases/08-test-isolation-and-kicad-10/08-02-SUMMARY.md
  - .planning/phases/08-test-isolation-and-kicad-10/08-03-PLAN.md
  - .planning/phases/08-test-isolation-and-kicad-10/08-03-SUMMARY.md
  - .planning/phases/08-test-isolation-and-kicad-10/08-04-PLAN.md
  - .planning/phases/08-test-isolation-and-kicad-10/08-04-SUMMARY.md
  - .planning/phases/08-test-isolation-and-kicad-10/08-05-PLAN.md
  - .planning/phases/08-test-isolation-and-kicad-10/08-05-SUMMARY.md
  - .planning/phases/08-test-isolation-and-kicad-10/08-06-PLAN.md
  - .planning/phases/08-test-isolation-and-kicad-10/08-06-SUMMARY.md
  - tests/README.md
  - tests/clifixtures.py
  - tests/conftest.py
  - tests/customfixtures.py
  - tests/installfixtures.py
  - tests/test_install_e2e.py
  - tests/test_install_plan.py
  - tests/test_kicad_cli.py
  - tests/test_naming_suggest.py
  - tests/test_roundtrip_corpus.py
covered_digest: "v3:sha256:86f33e1df550bc908c18807bb9ebb5bc1780585982ba573f9508231f84f24d3d"
behavior_unverified: 0
overrides_applied: 0
coincidental_reliance_items:
  - truth: "The live-Custom guard fails the run only on a test write"
    reason: incidental-ordering
    harden: "Guard digests every file at session start and end with no ignore list, so KiCad lock/autosave files created by the owner during the 18-minute run also trip it (review WR-01); declare the ignored artifact names"
human_verification:
  - test: "Owner's KiCad 10 Symbol Editor check of the VER-01 scratch install (08-UAT.md test 2)"
    expected: "Set KICAD_IMPORT_UAT_DIR to a folder outside the repo, run tests/test_install_e2e.py::test_uat_scratch_install -s, add the printed IC_PowerManagementMosfet_TI.kicad_sym as a project symbol library in KiCad 10, open CSD85301Q2 in the Symbol Editor and place both units. The library opens without a load error, CSD85301Q2 shows units A and B, Footprint IC_PowerManagementMosfet_TI:DQK0006B, hidden Manufacturer TI and MPN CSD85301Q2, and the file still begins with (version 20241209)."
    why_human: "Needs the KiCad 10 GUI (Symbol Editor and schematic placement). D-08 and D-10 make the owner's result the thing that closes backlog 999.1; it is recorded as result [pending] in 08-UAT.md."
---

# Phase 8: Test Isolation and KiCad 10 Verification Report

**Phase Goal:** The developer can trust the test suite again. It passes on the workstation whatever parts `Custom/` holds, KiCad 10 is the only kicad-cli target, and the deferred KiCad 10 install check is closed.
**Verified:** 2026-10-25T20:30:00Z
**Status:** human_needed
**Re-verification:** No, initial verification

## Goal Achievement

The code side of the goal is achieved and independently re-confirmed. The one open piece is the owner's manual KiCad 10 Symbol Editor check, which the phase deliberately left as a pending UAT test (D-08, D-10). The phrase "the deferred KiCad 10 install check is closed" is therefore only half true until the owner answers 08-UAT.md test 2.

### Observable Truths (ROADMAP success criteria, plus plan truths)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Adding or removing a part in the live `Custom/` changes no test result; the 14 tests that copied the live tree use an isolated synthetic `Custom/` and pass | VERIFIED | `custom_copy` is gone (`grep -rn custom_copy tests` empty); `copytree` only in `tests/gitfixtures.py` (git template). `tests/customfixtures.py::write_synthetic_custom` builds five libraries (20211014, 20231120, 20241209, 20251024) from `installfixtures` / `zipfixtures` bytes, no UL tokens. `conftest.py::synthetic_custom` returns `write_synthetic_custom(tmp_path / "repo")`. All migrated modules use it. My run of `-m "not wurth"`: 2027 passed, 3 skipped, 0 failed. Orchestrator's scratch-copy-without-`Custom/` proof is recorded in 08-06-SUMMARY (523 passed). Caveat: by decision D-04 a handful of read-only health checks still read the live tree and can go red on a live part that breaks a rule (see Warnings) |
| 2 | Real kicad-cli tests expect KiCad 10 output (format 20251024), pass with the installed kicad-cli 10, and skip with a stated reason where it is absent | VERIFIED | `tests/clifixtures.py`: `KICAD_MAJOR = 10`, `KICAD_SYMBOL_FORMAT = 20251024`, one `functools.cache`d `located_kicad_cli()`; `check_kicad_cli` returns distinct reasons for no binary, not runnable, wrong major, unparsable (unit-tested in `tests/test_clifixtures.py`). `kicad_cli_path` and `real_tools` in `conftest.py` skip with that reason. No module keeps its own lookup (grep for `locate_kicad_cli` / `find_kicad_footprint_dir()` in tests: only gate, conftest and the fake-runner tests). My run: `pytest -m kicad_cli` = 23 passed, 0 skipped, kicad-cli `C:/Program Files/KiCad/10.0/bin/kicad-cli.exe` 10.0.7. No `generator_version "9.0"` expectation remains in real-binary tests |
| 3 | Bare `pytest` on the workstation reports 0 failures and every skip carries a documented reason | VERIFIED (partly from orchestrator and executor runs) | I ran `-m "not wurth" -rs`: 2027 passed, 3 skipped, exactly the KICAD_IMPORT_UAT_DIR skip (`test_install_e2e.py:580`) and the two WinError 1314 symlink skips (`test_model_source.py:201`, `test_package_folder.py:105`). Each has a row in `tests/README.md` "Expected skips". The Wurth corpus is checked out at the pinned `2e6e51b1...` (`git submodule status` shows no prefix). The full bare run (8063 passed, 3 skipped, 0 failed, 17 min 53 s) is from 08-06 and the orchestrator; I did not repeat the 18 minute run |
| 4 | On KiCad 10, installing into an existing 20241209 `Custom/` library installs as-is with the D-01 warning and leaves the format version unchanged | VERIFIED (automated half) | `tests/test_install_e2e.py::_scenario_target_20241209_as_is` asserts `plan.normalised is False`, `target_version == 20241209`, exactly one `install.version_mismatch` WARNING naming 20211014, 20241209 and 20251024, header slice byte-identical with `(version 20241209)`, vendor block keeps `(id `, and `load_gate` returns no issues. Registered as `target_20241209_as_is_with_warning` in `_SCENARIOS`; included in my 23-passed `-m kicad_cli` run |
| 5 | The live `Custom/` is write-protected per session: a run that changes it ends non-zero and names the paths (D-13, TEST-03) | VERIFIED | `conftest.py::_live_custom_untouched` (session, autouse) delegates to `customfixtures.guard_custom`, which digests Symbols/Footprints/3DModels before and after and `pytest.fail`s with "the test run changed the live Custom/ folder: ...". Failure path is proven by subprocess tests `test_guard_failure_fails_the_run` / `test_guard_quiet_run_passes` in `tests/test_customfixtures.py` (passed in my run). `git -C Custom status --short` empty after my runs |
| 6 | `tests/README.md` lists one row per skip condition, the live-`Custom/` rule, read-only health checks and Wurth timing (D-12) | VERIFIED | File read in full: five-row Expected skips table, Other conditional skips, health-check list, measured Wurth numbers and budget rule |
| 7 | No application code changed, no test skipped/deleted, no assertion loosened beyond D-06 retargets and the measured Wurth budget | VERIFIED | `git diff --stat 12e05e3 -- kicad_lib_manager` is empty. Diff of removed `assert` lines shows only fixture renames, the removed live-tree snapshots (superseded by the guard), the 9.0/20241209 to KiCad 10 retargets, and `elapsed < 60`. `test_naming_suggest` ranking assertions are unchanged. No new skip or xfail marks added |
| 8 | The owner's KiCad 10 Symbol Editor check passes (D-08 manual half, `verification: backstop`) | UNCERTAIN (human needed) | `08-UAT.md` test 2 is `result: [pending]` by design. The scratch-install hook (`test_uat_scratch_install`) builds the 20241209 scratch library from the synthetic writer outside the repo and keeps the T-04-28 guards; it is skipped without `KICAD_IMPORT_UAT_DIR` |

**Score:** 4/4 roadmap success criteria verified on automated evidence; truth 8 (backstop) routed to human.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/clifixtures.py` | KiCad 10 constants and cached gate | VERIFIED | Substantive, imported by conftest, test_kicad_cli, test_install_e2e, test_install_plan |
| `tests/customfixtures.py` | `write_synthetic_custom`, guard helpers | VERIFIED | Used by conftest and e2e UAT hook; no live-tree read |
| `tests/conftest.py` | `synthetic_custom`, `kicad_cli_path`, `real_tools`, `_live_custom_untouched`; no `custom_copy` | VERIFIED | Read in full |
| `tests/installfixtures.py` | 20251024 house style | VERIFIED | `target_lib(20251024)` exercised by the passing real-binary fixed-point test in `-m kicad_cli` |
| `tests/test_clifixtures.py`, `tests/test_customfixtures.py` | Gate and contract tests | VERIFIED | Passed in my run |
| `tests/README.md` | Skip table and rules | VERIFIED | |
| `.planning/phases/08-.../08-UAT.md` | Test 1 pass, test 2 pending | VERIFIED | Matches plan (1 pass, 1 `[pending]`) |
| `.planning/PROJECT.md`, `04-UAT.md` | Records claiming only automated evidence | VERIFIED | Wording cites automated result and points to 08-UAT.md test 2; no "closed" field |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| conftest `kicad_cli_path` | clifixtures `located_kicad_cli` | lazy import, `pytest.skip(reason)` | WIRED |
| clifixtures | `kicad_cli.locate_kicad_cli` / `run_cli(["version"])` | direct calls | WIRED |
| conftest `synthetic_custom` | customfixtures `write_synthetic_custom` | lazy import | WIRED |
| conftest `_live_custom_untouched` | customfixtures `guard_custom` | `yield from` | WIRED |
| test_install_e2e `_SCENARIOS` | `test_cli_version_scenarios` | parametrised over keys | WIRED |
| test_install_e2e / test_install_plan / test_kicad_cli | clifixtures constants | `from clifixtures import` | WIRED |
| 04-UAT.md and PROJECT.md | 08-UAT.md | closing note / outcome cell | WIRED |

### Data-Flow Trace (Level 4)

Not applicable: test infrastructure only, no rendered dynamic data.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Real-binary tier on kicad-cli 10 | `pytest -m kicad_cli -q` | 23 passed, 0 skipped (60.6 s) | PASS |
| Gate resolves a binary | `located_kicad_cli()` | `(C:/Program Files/KiCad/10.0/bin/kicad-cli.exe, '')` | PASS |
| Suite without Wurth | `pytest -m "not wurth" -rs` | 2027 passed, 3 skipped, 0 failed (392 s) | PASS |
| Live Custom untouched | `git -C Custom status --short` | empty | PASS |
| App code untouched | `git diff --stat 12e05e3 -- kicad_lib_manager` | empty | PASS |

### Probe Execution

No probes declared by this phase. SKIPPED.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| TEST-01 | 08-01, 08-02, 08-03, 08-04, 08-05, 08-06 | Suite passes whatever `Custom/` holds; synthetic `Custom/` | SATISFIED | Truth 1. REQUIREMENTS.md ticked, traceability "Complete" |
| TEST-02 | 08-01, 08-04, 08-05 | Real kicad-cli tests expect KiCad 10 (20251024), skip with stated reason | SATISFIED in code | Truth 2. **REQUIREMENTS.md still shows `[ ]` and traceability "Pending"**; bookkeeping not updated |
| TEST-03 | 08-02, 08-06 | `pytest` on workstation: 0 failures, only documented skips | SATISFIED | Truths 3, 5, 6. REQUIREMENTS.md ticked |
| VER-01 | 08-04, 08-06 | D-01 as-is-with-warning case re-tested on KiCad 10 (backlog 999.1) | AUTOMATED HALF SATISFIED, MANUAL HALF PENDING | Truths 4 and 8. REQUIREMENTS.md is ticked "Complete" |

All four phase IDs appear in plan frontmatter and in REQUIREMENTS.md. No orphaned requirements: every ID mapped to Phase 8 in REQUIREMENTS.md traceability (TEST-01, TEST-02, TEST-03, VER-01) is claimed by at least one plan.

**Requirements bookkeeping findings (WARNING, not code gaps):**
- TEST-02 is satisfied but left unticked / "Pending" in REQUIREMENTS.md. It should be marked complete.
- VER-01 was ticked by `requirements mark-complete` while its own acceptance rule (D-08 / D-10, and the 08-06 plan: "closure exists only once the owner passes 08-UAT.md test 2") says it is not closed until the owner answers. The literal requirement text ("is re-tested on KiCad 10") is met by the automated re-test, so the tick is defensible, but it is ahead of the phase's own closure definition and ahead of ROADMAP success criterion wording "the deferred KiCad 10 install check is closed". Recommended: either leave it ticked and accept that 999.1 closure is the owner's UAT answer, or revert to unticked until `/gsd-verify-work 8` records test 2. This is a human decision.
- ROADMAP.md still shows Phase 8 as `[ ]`; the orchestrator updates that at phase close.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | - | TBD/FIXME/XXX scan of the changed test files | none | No unreferenced debt markers found in files this phase touched |

### Code review findings (08-REVIEW.md, 0 critical, 4 warning, 4 info; all `open` in 08-REVIEW-DISPOSITION.md)

None blocks a must-have, but two bear directly on "the developer can trust the test suite":
- WR-01 (warning): the session guard hashes every file under Custom with no `OSError` handling and no ignore list. KiCad lock or autosave files (`~*.lck`, `_autosave-*`, `fp-info-cache`) appearing or vanishing during the roughly 18 minute run would fail the run with "changed the live Custom/ folder" although no test wrote anything. This is a realistic false-red for an owner who keeps KiCad open. Recorded as a coincidental-reliance advisory above.
- WR-02 (warning): detection is end-of-session only, names no offending test, and reports after the damage; the docstring calls it a "write-protect" but it only detects.
- WR-03 (warning): the gate checks only the major version while tests pin `20251024` and generator `"10.0"`; a 10.1 build would fail assertions instead of skipping.
- WR-04 (warning): a newer KiCad (11) as the newest install turns the whole real-binary tier into skips without a failure, and a transient probe failure is cached for the session.
- IN-01..IN-04: doubled `.kicad_mod` suffix in one load test, Wurth budget about 4.3 times looser than measured, README health-check list incomplete (`test_locate_text_caps.py::test_real_files_are_below_both_caps` also reads the live tree), UAT hook `rmtree`s a user-supplied `Custom` folder.

Related literal-wording note on success criterion 1: the README states "no test result may depend on which parts it holds", yet the D-04 read-only health checks and `test_locate_text_caps` can change result when a live part breaks a rule or cap. The CONTEXT decision D-04 explicitly keeps them, and the criterion's intent (the 14 write-to-copy tests) is met, so this is recorded as a documentation inconsistency, not a failure.

### Human Verification Required

#### 1. Owner's KiCad 10 Symbol Editor check (08-UAT.md test 2)

**Test:** In PowerShell from the repo root set `$env:KICAD_IMPORT_UAT_DIR` to a new folder outside the repository (for example `C:\Temp\kicad_uat_ver01`), run `.\env\Scripts\python.exe -m pytest tests/test_install_e2e.py::test_uat_scratch_install -s`. In KiCad 10 add the printed `IC_PowerManagementMosfet_TI.kicad_sym` as a project symbol library of a scratch project under a non-clashing nickname, open CSD85301Q2 in the Symbol Editor and place it in a scratch schematic. Close without saving, then open the scratch `.kicad_sym` in a text editor.
**Expected:** The library opens without a load error (an older-format or read-only notice is acceptable). CSD85301Q2 shows units A and B, Footprint `IC_PowerManagementMosfet_TI:DQK0006B`, and hidden Manufacturer TI and MPN CSD85301Q2. Both units can be placed. The file still begins with `(version 20241209)`.
**Why human:** Needs the KiCad 10 GUI; this is the D-08 manual half that closes backlog 999.1.

### Gaps Summary

No code gaps. All four ROADMAP success criteria are met on automated evidence that I re-ran (23 real-binary tests pass on kicad-cli 10.0.7; 2027 non-Wurth tests pass with exactly three documented skips; live `Custom/` and application code untouched). Status is `human_needed` solely because of the owner's pending Symbol Editor check, plus two requirements bookkeeping decisions (tick TEST-02; decide whether VER-01 should stay ticked before the owner's answer). The review warnings WR-01 to WR-04 are open advisory items, with WR-01 the most likely to cause a false red run in daily use.

---

_Verified: 2026-10-25T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
