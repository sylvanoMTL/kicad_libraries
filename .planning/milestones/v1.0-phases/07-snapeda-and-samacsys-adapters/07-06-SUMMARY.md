---
phase: 07-snapeda-and-samacsys-adapters
plan: 06
subsystem: importer-tests
tags: [snapeda, samacsys, install, kicad-cli, fixtures, originality, pytest]

requires:
  - phase: 07-snapeda-and-samacsys-adapters
    provides: "07-03 SnapEDA adapter and planner; 07-04 real-sample gating and SnapEDA recognition tests; 07-05 SamacSys adapter, part_info hints and suggestion"
provides:
  - "Both vendors install into a synthetic Custom/ with the UL sample's <Lib>:<FP> link and ${CUSTOM_3DMODEL_DIR} model path, rollback, no-op re-install and Import-Vendor trailer"
  - "D-04 version-agnostic kicad-cli load check on installed SnapEDA and SamacSys libraries (synthetic and real)"
  - "D-01 originality guard: SHA-256 and real-part-name checks of the committed fixtures against the real zips"
  - "Real SamacSys recognition and PowerSupply_SubCategory_RECOM suggestion; real SnapEDA and SamacSys installs"
affects: [phase-07 verification]

actuals:
  tokens: 7000
  tasks: 2
  commits: 2

plan_head_before: 9dfde8c8823022efa6815343035a435443a3a048
plan_head_after: 9a84b4693701e44963533f99bc0bee9b861e8ea6

tech-stack:
  added: []
  patterns:
    - "Case records + parametrised ids for per-vendor install tests; the package stays open across plan and apply (WR-04)"
    - "Real-zip tests gated by file name; real members read in memory only"

key-files:
  created:
    - tests/test_vendorfixtures.py
  modified:
    - tests/test_vendor_install.py
    - tests/test_import_dialog.py
    - tests/test_real_vendor_samples.py

key-decisions:
  - "Synthetic installs use ToolContext() so the cleanup is what is tested; only the D-04 tests install with the detected real tools"
  - "Model ops carry no data (staged), so the op-bytes equality check covers symbol_lib and footprint ops while the model is checked by its ISO-10303-21 header"
  - "test_fixtures_are_deterministic freezes zipfile's wall-clock stamp so whole archives compare byte for byte"
  - "real_tools is repeated in test_real_vendor_samples.py rather than moved to conftest (conftest is outside this plan's files)"

requirements-completed: [INTK-03, INTK-04]

coverage:
  - id: D1
    description: "Synthetic SnapEDA (with and without model) and SamacSys parts install into a synthetic Custom/ with the <Lib>:<FP> Footprint link, the ${CUSTOM_3DMODEL_DIR} model path, the install.no_model warning when no model ships, and no ERROR or pin/pad mismatch"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_vendor_install.py#test_vendor_install_links_like_ul"
        status: pass
    human_judgment: false
  - id: D2
    description: "Installed fields follow CONTEXT: vendor names kept (D-10), Manufacturer/MPN filled, volatile and empty fields gone, Mouser Part Number and ki_description kept"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_vendor_install.py#test_vendor_field_outcomes"
        status: pass
    human_judgment: false
  - id: D3
    description: "Re-install plans a no-op with no field changes; a failed last write rolls back to a byte-identical Custom/ with fs.write_failed and install.rolled_back"
    requirement: INTK-04
    verification:
      - kind: unit
        ref: "tests/test_vendor_install.py#test_vendor_reinstall_is_noop"
        status: pass
      - kind: unit
        ref: "tests/test_vendor_install.py#test_vendor_install_rolls_back_on_failed_write"
        status: pass
    human_judgment: false
  - id: D4
    description: "The commit message names the vendor (Import-Vendor trailer) and the dialog's vendor labels for SnapEDA and SamacSys are unchanged"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_vendor_install.py#test_vendor_commit_trailer"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_vendor_labels"
        status: pass
    human_judgment: false
  - id: D5
    description: "KiCad (kicad-cli load_gate, no version pinned) loads each installed SnapEDA and SamacSys library and footprint, synthetic and real"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_vendor_install.py#test_vendor_installs_load_in_kicad"
        status: pass
      - kind: unit
        ref: "tests/test_real_vendor_samples.py#test_real_vendor_installs_load_in_kicad"
        status: pass
    human_judgment: false
  - id: D6
    description: "Committed fixtures parse, carry vendor markers, are under 4096 bytes, are reproducible and share no SHA-256 or part name with the real downloads"
    requirement: INTK-04
    verification:
      - kind: unit
        ref: "tests/test_vendorfixtures.py#test_fixture_originality"
        status: pass
      - kind: unit
        ref: "tests/test_vendorfixtures.py#test_fixture_members_small"
        status: pass
    human_judgment: false
  - id: D7
    description: "The real SamacSys zip is recognised (1.0, v6 symbol, module footprint, model, 4 legacy ignored, one 62-file other-CAD line) and suggests PowerSupply_SubCategory_RECOM; both real zips install with the expected links and fields"
    requirement: INTK-04
    verification:
      - kind: unit
        ref: "tests/test_real_vendor_samples.py#test_real_samacsys_recognised"
        status: pass
      - kind: unit
        ref: "tests/test_real_vendor_samples.py#test_real_samacsys_suggestion"
        status: pass
      - kind: unit
        ref: "tests/test_real_vendor_samples.py#test_real_snapeda_installs"
        status: pass
      - kind: unit
        ref: "tests/test_real_vendor_samples.py#test_real_samacsys_installs"
        status: pass
    human_judgment: false
  - id: D8
    description: "The Import dialog shows the vendor label, Field changes section, SnapEDA no-model warning, suggestions and the single other-CAD log line for each real zip"
    verification: []
    human_judgment: true
    rationale: "Manual-only verification in 07-VALIDATION.md; the GUI rendering is not asserted by these tests"

duration: 25min
completed: 2026-10-23
status: complete
---

# Phase 7 Plan 06: Vendor Install, Fixture Originality and Real-Sample Tests Summary

**Both vendors install end to end into a synthetic Custom/ like the UL sample (Footprint link, `${CUSTOM_3DMODEL_DIR}` model path, cleaned fields, rollback, no-op re-install, vendor trailer) and load in kicad-cli, the committed fixtures are proven original against the real downloads, and the real SamacSys and SnapEDA zips are recognised, suggested, installed and loaded.**

## Performance

- **Duration:** about 25 min (including the 312 s full-suite run)
- **Completed:** 2026-10-23
- **Tasks:** 2
- **Files:** 1 created, 3 modified (all under tests/)

## Accomplishments
- `tests/test_vendor_install.py`: `CASES` (snapeda, snapeda_with_model, samacsys), `_open_case` / `_install_case`, and seven new tests; 23 tests in the file pass, the 3 `kicad_cli` ones run (not skipped).
- `tests/test_import_dialog.py`: `test_vendor_labels` gains the SnapEDA and SamacSys pairs.
- `tests/test_vendorfixtures.py` (new): parse, marker, size, determinism and originality checks; originality runs against both real zips here.
- `tests/test_real_vendor_samples.py`: real SamacSys recognition and suggestion (moved from 07-05), real SnapEDA and SamacSys installs, and the real kicad-cli load test, all gated by file name.

## Task Commits

1. **Task 1:** `18ac376` (test) - synthetic vendor installs, rollback, re-install, trailer, kicad-cli load, dialog labels
2. **Task 2:** `9a84b46` (test) - fixture originality guard and real-sample tests

## TDD Gate Compliance

Production code was complete after plans 07-01 to 07-05 (the plan says so), so these tests pass on first run: there is no failing-test commit and no feat commit. Each task is a single `test(07-06)` commit. This is a deliberate shape of the plan, not a skipped RED: no behaviour was added. The one failure seen while writing (a model op carries no `data`, because models are staged) was a test bug and was fixed before the first commit.

## Verification

- `pytest tests/test_vendor_install.py tests/test_import_dialog.py::test_vendor_labels`: 29 passed, no skips.
- `pytest -m kicad_cli tests/test_vendor_install.py`: 3 passed. `pytest -m kicad_cli tests/test_vendor_install.py tests/test_real_vendor_samples.py`: 5 passed, no skips.
- `pytest tests/test_vendorfixtures.py tests/test_real_vendor_samples.py`: 15 passed, no skips (both real zips present, kicad-cli installed).
- Full suite: 21 failed, 1891 passed, 5 skipped. The 21 failed ids are exactly the 21 baseline ids from the plan (checked one by one); nothing new fails.
- `git status --porcelain downloaded_examples Custom`: only the pre-existing ` M Custom` (its 3 untracked files are the earlier CSD85301Q2 import); no vendor zip tracked (`git ls-files downloaded_examples` lists only ul_CSD85301Q2.zip).
- Acceptance greps: no `20251024` or `20241209` in tests/test_vendor_install.py; `@pytest.mark.kicad_cli`, `load_gate(`, `hashlib.sha256` and `4096` present where required.

## Deviations from Plan

None - plan executed exactly as written. No production defect was exposed by the new tests, so no production code changed.

## Authentication Gates

None.

## Known Stubs

None.

## Threat Flags

None. T-07-17 to T-07-19 are mitigated by test_fixture_originality, test_fixture_members_small, test_vendor_install_rolls_back_on_failed_write and test_vendor_zips_stay_local; real members are read in memory only and nothing from downloaded_examples was staged.

## Issues Encountered

- The checkout is a linked git worktree on `feature/part-importer` (not an `agent-*` branch), as the orchestrator stated; commits were made there with hooks enabled and no `--no-verify`.
- Git Bash rejected two long heredocs containing code; the test files were edited with the Edit/Write tools instead. No effect on the result.

## Next Phase Readiness

All six Phase 7 plans have SUMMARYs. Remaining: the manual dialog check listed in 07-VALIDATION.md (open each real zip in the Import dialog) and phase verification.

## Self-Check: PASSED

- tests/test_vendorfixtures.py, tests/test_vendor_install.py, tests/test_real_vendor_samples.py, tests/test_import_dialog.py: FOUND
- Commits 18ac376 and 9a84b46: FOUND in HEAD history
