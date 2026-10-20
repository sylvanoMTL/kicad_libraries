---
phase: 04-plan-and-install-core
plan: 10
subsystem: testing
tags: [kicad, e2e, kicad-cli, idempotence, uat, pytest]

requires:
  - phase: 04-plan-and-install-core
    provides: "04-01..04-09: build_plan, apply_plan transaction, verify_install, kicad_cli.load_gate, conflicts and resolutions, plan-level no-op"
provides:
  - "ROADMAP Phase 4 success criteria 1-5 as named end-to-end tests on the real Ultra Librarian sample and a copy of the real Custom/ libraries"
  - "INST-09 proven through apply_plan: a second identical install touches nothing, writes no backup folder and reports INFO install.nothing_to_do (existing and new library)"
  - "Real kicad-cli 9.0.9 load check of the installed UL result and the CONTEXT version scenarios (D-01/D-04/D-22)"
  - "tests/conftest.py kicad_cli_path fixture; importer.kicad_cli in CORE_MODULES"
  - "Owner's KiCad 9 UAT scratch install outside the repo, built by test_uat_scratch_install"
  - "INST-06 and ROADMAP Phase 4 criterion 3 amended for D-02 (only the incoming symbol is normalised; footprints are copied as-is)"
affects: [05-preview-and-install-ui, 06-git-and-registration]

actuals:
  tokens: 6200
  tasks: 2
  commits: 2
plan_head_before: e6e98a8005880d4c97290d32472d603c3d56e4a2
plan_head_after: d360a689d18cf0b05a2dc31a7b0d34f5975b127a

tech-stack:
  added: []
  patterns:
    - "A module-scoped autouse fixture snapshots the checkout's own Custom/ before the module and asserts equality after (prohibition: Phase 4 never writes the real Custom/)"
    - "Version scenarios are a dict of scenario functions driven by one parametrised kicad_cli test; a refused scenario returns None and skips the load check"
    - "The manual-UAT scratch install is an env-gated test (KICAD_IMPORT_UAT_DIR) that refuses any folder inside or containing the repository"

key-files:
  created: []
  modified:
    - tests/test_install_e2e.py
    - tests/conftest.py
    - tests/test_importer_layering.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "test_uat_scratch_install is not marked kicad_cli: it is gated by KICAD_IMPORT_UAT_DIR instead, so `-m kicad_cli` shows 7 passed and 0 skipped while the full suite shows it as the one extra skip"
  - "The incoming-newer-than-target scenario is one more case of test_cli_version_scenarios (not a separate test) so the five CONTEXT scenarios are five parameter ids"
  - "The module fixture hashes the whole real Custom/ tree with its own digest function, because the snapshot fixture is function-scoped"

patterns-established:
  - "_install(candidate, layout, tmp_path, library, tools, **options) plans and applies with a tmp_path backup root; every e2e test goes through it"

requirements-completed: [INST-01, INST-02, INST-03, INST-04, INST-05, INST-06, INST-07, INST-08, INST-09, INTK-08, LIB-02, POST-03, POST-04]

coverage:
  - id: D1
    description: "Success criteria 1 and 2: the UL sample adds CSD85301Q2 with header and other symbols byte-identical, a consistent DQK0006B.kicad_mod, the STEP copied to 3DModels/CSD85301Q2.stp with a ${CUSTOM_3DMODEL_DIR} model block; a renamed symbol carries renamed _u_s sub-symbols and nothing else changes; a package without its STEP installs without a model and warns install.no_model"
    requirement: INST-01
    verification:
      - kind: e2e
        ref: "tests/test_install_e2e.py#test_ul_symbol_added_others_identical / test_sc1_ul_footprint_model_and_fields / test_sc2_rename_follows_sub_symbols / test_sc2_no_model_package"
        status: pass
    human_judgment: false
  - id: D2
    description: "Success criterion 3 without kicad-cli: a new library name creates the .kicad_sym + .pretty pair; existing headers (20211014, 20231120, 20241209) are unchanged; the two newer targets report install.version_mismatch and IC_IMU_TDK also install.pair_completed"
    requirement: LIB-02
    verification:
      - kind: e2e
        ref: "tests/test_install_e2e.py#test_sc3_new_library_pair / test_sc3_existing_headers_unchanged (3 cases)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Success criterion 4: a failure injected on each of the three writes of the UL install leaves Custom/ byte-identical with no .tmp file; an existing model with the same SHA-256 is reused, a different one is the conflict model:csd85301q2.stp and is left unchanged"
    requirement: INST-07
    verification:
      - kind: e2e
        ref: "tests/test_install_e2e.py#test_sc4_fail_on_each_write (3 cases) / test_sc4_model_same_sha_reused / test_sc4_model_different_sha_conflict"
        status: pass
    human_judgment: false
  - id: D4
    description: "Success criterion 5 and INST-09: verification re-parses and resolves the link and model; the same part in a second library warns verify.name_elsewhere naming the first; a pin/pad mismatch warns verify.pin_pad_mismatch naming pad 9; a second identical install changes nothing for an existing and for a new library"
    requirement: INST-09
    verification:
      - kind: e2e
        ref: "tests/test_install_e2e.py#test_sc5_name_elsewhere_and_verify / test_sc5_pin_pad_mismatch / test_second_install_is_noop / test_second_install_new_library_is_noop"
        status: pass
    human_judgment: false
  - id: D5
    description: "The installed UL result passes the real kicad-cli 9.0.9 load check, and the five CONTEXT version scenarios behave as D-01/D-04 specify against the real Custom/ libraries (same version, older incoming normalised to 20241209, target in another format warns, newer incoming refused, new library gets the 20241209 header)"
    requirement: INST-06
    verification:
      - kind: integration
        ref: "tests/test_install_e2e.py#test_cli_load_check_after_install / test_cli_version_scenarios (5 cases) / test_cli_second_install_is_noop"
        status: pass
    human_judgment: false
  - id: D6
    description: "The real Custom/ is never written: the module-scoped _real_custom_untouched fixture compares a full digest of the tree before and after, and git status --porcelain Custom prints nothing"
    verification:
      - kind: e2e
        ref: "tests/test_install_e2e.py#_real_custom_untouched (autouse, scope=module) over the whole module, and the full suite"
        status: pass
    human_judgment: false
  - id: D7
    description: "D-02 text amendment: INST-06 and ROADMAP Phase 4 criterion 3 say only the incoming symbol is normalised and footprints are copied as-is"
    requirement: INST-06
    verification:
      - kind: other
        ref: "grep 'footprints are copied as-is' .planning/REQUIREMENTS.md .planning/ROADMAP.md"
        status: pass
    human_judgment: false
  - id: D8
    description: "D-22 manual UAT in KiCad 9: the scratch Custom/ opens without a load error, CSD85301Q2 shows units A and B with Footprint IC_Battery_Charger_TI:DQK0006B and hidden Manufacturer/MPN, DQK0006B shows 8 pads and its value text, the STEP sits on the pads in the 3D viewer, and the research A6/A7 field-rule choices from 04-08 are confirmed"
    verification: []
    human_judgment: true
    rationale: "KiCad's GUI rendering is not machine-checkable; the owner runs the checklist below against the scratch install"
  - id: D9
    description: "Research A1: KiCad 10 writes symbol format 20251024, so on a KiCad 10 machine every 20241209 Custom/ library takes the as-is-with-warning row"
    verification: []
    human_judgment: true
    rationale: "Only KiCad 9.0.9 is installed here; the KiCad 10 behaviour was not exercised and is recorded, not faked"
  - id: D10
    description: "Rollback and overwrite branches on a case-sensitive filesystem (a case twin written under another spelling)"
    verification: []
    human_judgment: true
    rationale: "Only NTFS was available; those branches are covered with a faked directory listing (04-07 D7, 04-09), not on a real ext4 or APFS volume"

duration: 7min
completed: 2026-10-20
status: complete
---

# Phase 4 Plan 10: Phase proof Summary

**ROADMAP Phase 4 success criteria 1-5 are now named end-to-end tests on the real Ultra Librarian sample and a copy of the real `Custom/` libraries, the install result loads in the real kicad-cli 9.0.9 under the five CONTEXT version scenarios, a second identical install is proven a no-op through `apply_plan`, and the owner has a scratch KiCad 9 UAT install outside the repo.**

## Performance

- **Duration:** about 7 min (2026-10-20T08:40Z to 08:48Z)
- **Tasks:** 2 (tests only, no production code changed)
- **Files modified:** 5 (`test_install_e2e.py` +253 lines, `conftest.py`, `test_importer_layering.py`, `REQUIREMENTS.md`, `ROADMAP.md`)

## Accomplishments

- 16 new non-CLI tests in `tests/test_install_e2e.py` (`test_sc1_*` to `test_sc5_*`, `test_second_install_is_noop`, `test_second_install_new_library_is_noop`), each installing into a `custom_copy` with `backup_root=tmp_path / "bk"` and `ToolContext()` (no CLI) so the results are deterministic. `test_sc4_fail_on_each_write` derives its write count from the plan's non-mkdir ops and wraps `fsutil.atomic_write_bytes` with the flaky-Nth-write pattern.
- 7 `kicad_cli` tests against the installed kicad-cli 9.0.9: the load check after the UL install, five version scenarios, and the no-op after a normalised install into `IC_Magnetometer_Memsic`. Every non-blocked scenario is applied and then load-gated with no ERROR.
- Module-scoped autouse fixture `_real_custom_untouched` hashes the whole checkout `Custom/` before and after the module; `git status --porcelain Custom` is empty after the full suite.
- `kicad_cli_path` fixture in `tests/conftest.py`; `"importer.kicad_cli"` added to `CORE_MODULES`.
- D-02 text amendment applied with scoped byte replacements to `INST-06` in `.planning/REQUIREMENTS.md` and criterion 3 in `.planning/ROADMAP.md`.
- UAT scratch install built (see below).

## Task Commits

1. **Task 1:** `f9244dd` (test) - success criteria 1-5, no-op and the real-Custom guard
2. **Task 2:** `d360a68` (test) - real kicad-cli tests, `kicad_cli_path`, CORE_MODULES, UAT scratch test, D-02 text

**Plan metadata:** the docs commit carrying this SUMMARY and the STATE/ROADMAP/REQUIREMENTS updates.

## TDD Gate Compliance

Both tasks are `tdd="true"` but add proof over behavior plans 04-01 to 04-09 already delivered, so there is no failing phase and no `feat` commit (same shape as 04-07 Task 3). Every new test passed on its first run; the value of each was checked by reading what it asserts, and two guards were exercised directly: the UAT test refuses a folder inside the repo (run with `KICAD_IMPORT_UAT_DIR` set to `<repo>/zz_uat`: AssertionError "must lie outside the repository", nothing created), and `_real_custom_untouched` ran over the whole module and the full suite with the tree unchanged. No RED/GREEN gate commits exist for this plan; this is recorded here as the TDD gate note rather than hidden. The `tdd-red-evidence` classifier was not run.

## Verification

- `pytest tests/test_install_e2e.py::test_second_install_is_noop tests/test_install_e2e.py::test_ul_symbol_added_others_identical -x -q`: 2 passed
- `pytest tests/test_install_e2e.py -x -q -m "not kicad_cli" -k "sc1 or sc2 or sc3 or sc4 or sc5 or second_install" -rs`: 16 passed, none skipped
- `pytest tests/test_install_e2e.py -x -q -m kicad_cli -rs`: 7 passed, 0 skipped
- `pytest -q`: 1321 passed, 5 skipped (baseline 1298 passed, 4 skipped, plus 23 new; the extra skip is `test_uat_scratch_install` without its environment variable)
- `git status --porcelain Custom`: empty

## Manual KiCad 9 UAT (D-22): set up for the owner, not performed

Scratch install (outside the repo, built by `KICAD_IMPORT_UAT_DIR="C:/Users/sylvain/AppData/Local/Temp/kicad_import_uat" pytest tests/test_install_e2e.py::test_uat_scratch_install -s`; rerun it to rebuild a fresh copy):

- Scratch library: `C:\Users\sylvain\AppData\Local\Temp\kicad_import_uat\Custom\Symbols\IC_Battery_Charger_TI.kicad_sym`
- Scratch footprint library: `C:\Users\sylvain\AppData\Local\Temp\kicad_import_uat\Custom\Footprints\IC_Battery_Charger_TI.pretty`
- Scratch footprint: `C:\Users\sylvain\AppData\Local\Temp\kicad_import_uat\Custom\Footprints\IC_Battery_Charger_TI.pretty\DQK0006B.kicad_mod`
- Scratch model: `C:\Users\sylvain\AppData\Local\Temp\kicad_import_uat\Custom\3DModels\CSD85301Q2.stp`
- Scratch 3D folder: `C:\Users\sylvain\AppData\Local\Temp\kicad_import_uat\Custom\3DModels`
- Install backups of that run: `C:\Users\sylvain\AppData\Local\Temp\kicad_import_uat\bk`

Checklist for the owner (reply "approved" or describe what is wrong):

1. In KiCad 9 > Preferences > Manage Symbol Libraries, add the scratch `IC_Battery_Charger_TI.kicad_sym` as a test entry (or open it from the Symbol Editor's File > Open). Open symbol CSD85301Q2: it shows units A and B, and the properties dialog lists Footprint `IC_Battery_Charger_TI:DQK0006B`, Manufacturer `TI` and MPN `CSD85301Q2` (Manufacturer and MPN hidden on the canvas).
2. In Manage Footprint Libraries, add the scratch `IC_Battery_Charger_TI.pretty`. Open DQK0006B: 8 pads, value text DQK0006B.
3. Temporarily set CUSTOM_3DMODEL_DIR (Preferences > Configure Paths) to the scratch `Custom\3DModels` folder. Open the footprint's 3D viewer: the CSD85301Q2.stp body sits on the pads. Restore CUSTOM_3DMODEL_DIR afterwards.
4. Remove the temporary library entries.
5. Confirm the two discretion choices from 04-08 (research assumptions A6/A7, Open Questions 7 and 8), a yes/no answer since the UL sample shows neither case: (a) a vendor manufacturer or part-number field renamed in place to Manufacturer/MPN keeps the vendor's own visibility, and only newly added Manufacturer/MPN properties are hidden (D-13); (b) for a derived (`extends`) symbol, the Footprint link, ki_fp_filters and Manufacturer are set on the parent as well as the child.

Other items recorded as human judgment (not faked): KiCad 10 symbol format 20251024 (research A1, every 20241209 library takes the as-is-with-warning row on a KiCad 10 machine), and the case-sensitive-filesystem rollback and overwrite branches (04-07, 04-09, faked listings only).

## Decisions Made

See `key-decisions`. The remaining open product question from 04-09 (a part the owner edited in KiCad shows as a conflict on re-import) stays a Phase 5 preview confirmation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_uat_scratch_install` left unmarked for `kicad_cli`**
- **Found during:** Task 2
- **Issue:** The plan lists the UAT test with the `kicad_cli`-marked tests but also requires `-m kicad_cli` to show 0 skipped on this machine; a marked UAT test without its variable would be skipped.
- **Fix:** The UAT test is gated only by `KICAD_IMPORT_UAT_DIR`, so `-m kicad_cli` runs exactly 7 tests, all passing. It still builds the scratch install through the real detected tools.
- **Files modified:** tests/test_install_e2e.py
- **Commit:** d360a68

**2. [Plan wording] Version scenario count**
- The plan lists "one case per CONTEXT scenario" with five bullets; they are five parameter ids of `test_cli_version_scenarios` (`same_version_target`, `older_incoming_is_normalised`, `target_in_another_format_warns`, `incoming_newer_than_target_is_refused`, `new_library_gets_cli_header`).

**Total deviations:** 1 auto-fixed (Rule 3) plus 1 wording note. **Impact:** none on the contract.

## Known Stubs

None.

## Threat Flags

None. T-04-27 (e2e tests vs real Custom/): every install targets `custom_copy` or a tmp_path/out-of-repo folder; `_real_custom_untouched` passed over the module and the full suite; `git status --porcelain Custom` is empty. T-04-28 (UAT folder): the test resolves `KICAD_IMPORT_UAT_DIR`, refuses a folder equal to, inside or containing the repository (exercised with `<repo>/zz_uat`), refuses a linked `Custom`, and is skipped without the variable.

## Issues Encountered

- The `gsd_run` shell function is not defined in this runtime; `node .claude/gsd-core/bin/gsd-tools.cjs query ...` was used instead for the requirement and state updates.

## User Setup Required

None for the suite. The owner runs the KiCad 9 checklist above against the scratch install.

## Next Phase Readiness

- Phase 4 is complete pending the owner's D-22 reply. `build_plan` / `apply_plan` / `run_load_gate` / `verify_install` are proven on the real sample, the real kicad-cli and the real `Custom/` libraries (copied).
- Phase 5 can build the preview and install UI on the public API listed in the plan and show `plan.conflicts`, `plan.issues` and `InstallResult.issues` as they are.
- Open items for the owner: KiCad 9 UAT answer (including A6/A7), KiCad 10 behaviour (A1), case-sensitive filesystem branches, and whether a KiCad-edited part showing as a conflict on re-import is acceptable (D-07).

## Self-Check: PASSED

`tests/test_install_e2e.py`, `tests/conftest.py`, `tests/test_importer_layering.py` exist (`def _real_custom_untouched`, `scope="module"`, `def kicad_cli_path`, `"importer.kicad_cli"` present); commits `f9244dd` and `d360a68` are ancestors of HEAD and `git rev-list --count` from `plan_head_before` is 2. INST-06 and criterion 3 contain "footprints are copied as-is". Acceptance and plan-level verification commands re-run as listed under Verification; `git status --porcelain Custom` prints nothing; the UAT scratch folder lies outside the repo.

---
*Phase: 04-plan-and-install-core*
*Completed: 2026-10-20*
