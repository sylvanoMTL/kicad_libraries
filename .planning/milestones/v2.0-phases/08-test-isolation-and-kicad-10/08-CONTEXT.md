# Phase 8: Test Isolation and KiCad 10 - Context

**Gathered:** 2026-10-25
**Status:** Ready for planning

<domain>
## Phase Boundary

The test suite passes on the owner's workstation whatever parts the live `Custom/` holds. Real kicad-cli tests target KiCad 10 only. The deferred D-01 "as-is with warning" check (backlog 999.1, Phase 4 UAT Test 2) is closed on KiCad 10. Requirements: TEST-01, TEST-02, TEST-03, VER-01.

Nothing in the application changes behaviour. This phase touches `tests/`, test documentation, worktree setup (WurthElektronik checkout), and planning records only. If a retargeted test exposes a real product bug on KiCad 10, report it rather than silently changing app code. A fix belongs in this phase only if it is needed for the D-01 row to behave as specified.

**Baseline (run during discussion, 2026-10-25):** `env/Scripts/python.exe -m pytest` → 1965 passed, 21 failed, 6 skipped in 5 min 21 s. Failing:
- Live-`Custom/` dependent (14): `test_commit_plan::test_build_from_real_ul_plan`, `test_import_dialog::{test_tracer_ul_import_end_to_end, test_preview_sections_follow_plan_ops}`, `test_import_preview::test_rows_reimport_into_the_real_custom_library`, `test_install_apply::{test_stale_plan_ul_target_edited_during_gate, test_source_changed_at_apply, test_source_gone_at_apply, test_rollback_fail_on_nth_write[existing-1/2/3], test_success_touched_order}`, `test_install_e2e::{test_ul_symbol_added_others_identical, test_sc4_fail_on_each_write[3]}`, `test_install_plan::{test_model_changed_after_plan_is_refused_by_apply, test_noop_second_plan_after_normalised_apply}`.
- KiCad 9 expectations (7): `test_kicad_cli::test_real_cli_upgrades_ul_symbol_deterministically`, `test_install_plan::{test_version_real_cli_into_20241209, test_library_real_cli_new_header}`, `test_install_e2e::{test_cli_version_scenarios[older_incoming_is_normalised], test_cli_version_scenarios[new_library_gets_cli_header], test_cli_second_install_is_noop}`.

(The split above is by symptom from the run; the planner should confirm each test's root cause. Some kicad-cli scenarios also use `custom_copy`.)

Skips: 3 × WurthElektronik submodule not checked out, 2 × symlinks not permitted (Windows privilege), 1 × `KICAD_IMPORT_UAT_DIR` unset.

</domain>

<decisions>
## Implementation Decisions

### Synthetic Custom/ fixture (TEST-01)
- **D-01:** Replace the `custom_copy` fixture (`tests/conftest.py`, copies the live `Custom/Symbols|Footprints|3DModels`) with an isolated `Custom/` **built in code**. It is a *format mirror*: one symbol library per format version the real `Custom/` holds today, 20211014, 20231120, 20241209 and 20251024. Each has a few footprints in a matching `.pretty/` and stub 3D model files. The Ultra Librarian sample part (CSD85301Q2 / DQK0006B / its model) is **absent by construction**, so tests never depend on what the owner has installed. Follow the existing builder rule in `tests/installfixtures.py`: builders return bytes, write nothing and take no paths. A fixture function writes them under `tmp_path`.
- **D-02:** Fixture libraries use **today's v1 names**, mirroring the real ones (e.g. `IC_Battery_Charger_TI` at 20211014, `IC_IMU_TDK` at 20231120, `IC_PowerManagementMosfet_TI` at 20241209, a 20251024 library such as `IC_Wireless_BLE_uBlox`). The library names the 14 tests already reference (`IC_Battery_Charger_TI`, `IC_Test_TI`, `IC_MOSFET_Dual_TI` as a new library, etc.) keep working without rewriting assertions. Phase 10 will add `Atomic_` libraries to this same fixture. — **Reversibility:** reversible — test-only names.
- **D-03:** The KiCad 10 (20251024) house style for the new builder is taken from **real kicad-cli 10 output** (header layout, `(generator_version "10.0")`, `(embedded_fonts no)`, CRLF/LF as written). It is checked once against a real `sym upgrade` run and documented in the builder's docstring, as the 20211014 and 20231120/20241209 styles were. Don't just bump the version number on the 20241209 builder.
- **D-04:** Tests that only **read** the live `Custom/` stay as they are and pass whatever it holds. These include the round-trip corpus (`test_roundtrip_corpus.py`), `test_edits.py` reading `Connector_USB_GCT.kicad_sym`, and scanner checks. They keep skipping when the submodule isn't checked out. Only tests that write to a copy or assume which parts exist move to the synthetic fixture.

### KiCad version targeting (TEST-02)
- **D-05:** Real kicad-cli tests **pin KiCad 10 exactly**: expected symbol format `20251024` and `(generator_version "10.0")` as named constants. A test that runs the real binary **skips with a stated reason unless the located kicad-cli is major version 10**. That covers both "only KiCad 9 installed" and a future KiCad 11, so newer output gets reviewed rather than silently accepted. Discovery stays as the app does it (`locate_kicad_cli(kicad_fp_dir=find_kicad_footprint_dir())`, picks the newest; 10.0 on this workstation, where 9.0 is also installed).
- **D-06:** KiCad 9 real-CLI tests are **retargeted to their KiCad 10 equivalents**, keeping each test's intent:
  - "normalised into a 20241209 library" → normalised into a **20251024** library;
  - the 20241209 target becomes the **as-is-with-warning** row (this is VER-01);
  - a new library gets the **KiCad 10 header**;
  - the deterministic-upgrade and second-install-is-noop tests expect 20251024.

  No KiCad 9 expectation remains in any test that runs the real binary.
- **D-07:** Fake-runner unit tests that use 20241209 constants (e.g. `SYM_UP` in `test_kicad_cli.py`, `V9` in `test_install_plan.py`, `FakeCli(output_version=20241209)`) are **left unchanged**. They don't start a process, they pass, and D-01 is version-generic logic.

### D-01 re-test on KiCad 10 (VER-01)
- **D-08:** Close backlog 999.1 with **an automated test plus one manual KiCad check**:
  - Automated (real kicad-cli 10, marked `kicad_cli`): install the UL sample into the fixture's **20241209** library. Assert the D-01 as-is WARNING naming both versions, the library header still `(version 20241209)`, the vendor symbol spliced unchanged, and `kicad_cli.load_gate` with kicad-cli 10 returning no issues.
  - Manual: the owner opens the installed library in KiCad 10's Symbol Editor and places the part.
- **D-09:** The manual check uses a **scratch copy** through the existing `KICAD_IMPORT_UAT_DIR` hook (`tests/test_install_e2e.py::test_uat_scratch_install`). The real `Custom/` is never touched. Today that hook copies the live `Custom/` and installs into `IC_Battery_Charger_TI` (20211014). For VER-01 it must target a **20241209** library that doesn't already hold the part. The live `IC_PowerManagementMosfet_TI` now contains CSD85301Q2, so build the scratch tree from the synthetic fixture or otherwise guarantee the part is absent. Update its docstring from "KiCad 9 UAT" to KiCad 10.
- **D-10:** Record the outcome in the **Phase 8 UAT file**:
  - add a closing note to the archived `.planning/milestones/v1.0-phases/04-plan-and-install-core/04-UAT.md` Test 2 pointing to it;
  - update the PROJECT.md Key Decisions row for the kicad-cli normalisation policy from "re-test still open (backlog 999.1)" to verified on KiCad 10;
  - update the "KiCad 10 is the reference version" row, which is pending on the 7 kicad-cli tests.

### Skips and regression guard (TEST-03)
- **D-11:** **Check out the WurthElektronik submodule in this worktree** (`git submodule update --init WurthElektronik/KiCad-Library`), so the 3 Würth stress/round-trip tests run on the workstation. This is a one-off setup step; the skip stays in code for machines without it. After that, the expected workstation skips are the 2 symlink-privilege skips and the `KICAD_IMPORT_UAT_DIR` one.
- **D-12:** Document the expected skips in a new **`tests/README.md`** table with one row per skip condition. The conditions are: no kicad-cli 10, symlinks not permitted, no WurthElektronik submodule, `KICAD_IMPORT_UAT_DIR` unset, and any `local_kicad` opt-in. Each row says why and how to enable it. The existing `pytest.skip(...)` messages stay. Also note there that the suite must not write to or depend on the contents of the live `Custom/`.
- **D-13:** Add a **write-protect guard**: a session-scoped check (e.g. in `tests/conftest.py`) hashes the live `Custom/` (Symbols, Footprints, 3DModels) before the run and fails the session if anything changed afterwards. The `custom_copy` fixture is removed, so nothing copies the live tree any more. Read-only corpus tests still pass under the guard. The guard must be cheap: about 19 MB of models plus about 430 KB of KiCad text. Hash once per session, or compare size and mtime with a hash fallback, at Claude's discretion.

### Claude's Discretion
- Fixture shape and API: one session- or function-scoped fixture vs a builder function, its name, and how many symbols, footprints and models each library holds, as long as D-01/D-02 hold and every D-01 version row is reachable.
- How the "kicad-cli is major 10" check is implemented. It could parse `kicad-cli version`, or use the install path's version folder. Add a shared fixture, e.g. replace `kicad_cli_path` / `real_exe` / `_real_tools` with one helper that applies the KiCad 10 skip.
- Guard implementation details under D-13.
- Whether to refresh the stale `.planning/codebase/TESTING.md` (it still says "no tests exist"). Optional; `tests/README.md` is the required doc.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` § "Phase 8: Test Isolation and KiCad 10": goal and the 4 success criteria
- `.planning/REQUIREMENTS.md` § Tests (TEST-01..03) and § Re-tests (VER-01)
- `.planning/STATE.md` § Blockers/Concerns: the 14 + 7 failing tests and backlog 999.1

### D-01 version policy (what VER-01 re-tests)
- `.planning/milestones/v1.0-phases/04-plan-and-install-core/04-CONTEXT.md` § D-01: equal / older-than-target / newer-than-target rows and the as-is-with-warning rule
- `.planning/milestones/v1.0-phases/04-plan-and-install-core/04-UAT.md`: Test 2 (expected "every 20241209 Custom/ library takes the as-is-with-warning row"), deferred line 47
- `.planning/milestones/v1.0-ROADMAP.md` § "Phase 999.1": the backlog entry being closed
- `.planning/PROJECT.md` § Key Decisions: rows for kicad-cli normalisation (D-01/D-02) and "KiCad 10 is the reference version" (to update per D-10)

### Test conventions
- `.planning/codebase/TESTING.md`: "keep fixtures small and synthetic; do not copy real libraries from Custom/ or WurthElektronik/ into fixtures" (otherwise stale)
- `tests/installfixtures.py` module docstring: builder rule (bytes only, no paths, stdlib + `zipfixtures._quote`) and the recorded 20211014 / 20231120 / 20241209 house styles
- `pyproject.toml` `[tool.pytest.ini_options]`: markers `wurth`, `local_kicad`, `kicad_cli`; `--strict-markers -ra`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tests/installfixtures.py`: `target_lib(...)`, `vendor_symbol_lib`, `extends_pair`, `vendor_footprint`, and the v6 / modern (20231120, 20241209) symbol builders. Extend these with a 20251024 style (D-03) and use them to build the format-mirror `Custom/`.
- `tests/zipfixtures.py`: `symbol_lib`, `footprint`, `STEP_BYTES` (stub model bytes), `unpack_sample`, `UL_ZIP`.
- `tests/conftest.py`: `custom_copy` (to be replaced), `ul_package`, `kicad_cli_path`, `snapshot` (folder → sha256 map, reusable for the D-13 guard).
- `tests/fakecli.py` (`FakeCli`): fake kicad-cli runner; keep as is (D-07).
- `kicad_lib_manager.importer.layout.RepoLayout.for_repo(repo)`: what `custom_copy` returns. The new fixture should return the same type, so the 14 tests change only their fixture name.
- `kicad_lib_manager.importer.planner.detect_tools`, `kicad_cli.locate_kicad_cli`, `kicad_cli.load_gate`: real-CLI entry points the KiCad 10 tests use.

### Established Patterns
- `custom_copy` users: `test_install_plan.py` (35), `test_install_e2e.py` (39), `test_install_apply.py` (32), `test_import_dialog.py` (13), `test_import_preview.py` (3), `test_commit_plan.py` (2).
- Real-binary tests carry `@pytest.mark.kicad_cli` and locate the CLI in three places with slightly different helpers: `real_exe` (module fixture in `test_kicad_cli.py`), `_real_tools()` (`test_install_plan.py`), and `kicad_cli_path` / `real_tools` (`conftest.py`, `test_install_e2e.py`). Centralise the KiCad 10 skip (D-05).
- `test_install_e2e.py::_SCENARIOS` holds the five D-01 version scenarios (same version, older-incoming normalised, target-in-another-format warns, incoming-newer refused, new library header). This is the natural home for the retargeted rows and the VER-01 as-is case.
- Live `Custom/` today: 12 symbol libraries. Versions: 20211014 ×3, 20231120 ×1, 20241209 ×6, 20251024 ×2. There are 11 `.pretty` folders and 15 models (about 19 MB). CSD85301Q2 lives in `IC_PowerManagementMosfet_TI` (added in `Custom` commit `eecac22`).

### Integration Points
- `tests/conftest.py`: new fixture, removal of `custom_copy`, session write-protect guard, shared KiCad 10 skip helper.
- `tests/test_install_e2e.py::test_uat_scratch_install`: retarget for the manual VER-01 check (D-09).
- `tests/README.md` (new): skip table and the live-`Custom/` rule.

</code_context>

<specifics>
## Specific Ideas

- The phase is done when bare `pytest` from the repo root on the workstation reports 0 failures. With WurthElektronik checked out, the only skips should be the symlink-privilege pair and `KICAD_IMPORT_UAT_DIR`, each listed in `tests/README.md`.
- Adding or removing a part in the live `Custom/` (e.g. CSD85301Q2) must change no test result. A good verification step is to run the suite, temporarily stage a dummy part in a scratch copy, or simply confirm no test reads part-dependent state from the live tree.
- The manual KiCad 10 check mirrors the original Phase 4 UAT Test 2: open the scratch 20241209 library in KiCad 10's Symbol Editor and place CSD85301Q2.

</specifics>

<deferred>
## Deferred Ideas

None. Discussion stayed within phase scope. (Run time of 5+ minutes was noted but not raised as a goal.)

</deferred>

---

*Phase: 08-test-isolation-and-kicad-10*
*Context gathered: 2026-10-25*
