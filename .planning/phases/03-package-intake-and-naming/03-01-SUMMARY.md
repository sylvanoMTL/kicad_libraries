---
phase: 03-package-intake-and-naming
plan: 01
subsystem: importer-intake
tags: [zipfile, tempfile, ultra-librarian, adapter-registry, library-naming]

requires:
  - phase: 02-kicad-file-layer
    provides: "kicad_files parse_bytes / find_symbols / find_property / footprint_name / find_models, models.Issue"
provides:
  - "kicad_lib_manager/importer/ Qt-free subpackage: Package / open_package (zip staging outside the repo), ImportCandidate data model, adapter registry, UL adapter, library-name suggestion skeleton"
  - "Both Package lifetimes: with block and explicit idempotent close()"
  - "placeholder_tokens contract (D-04) for the install-refusal check in Phases 4 and 5"
affects: [03-03 zip safety, 03-04 detection and legacy rules, 03-05 sanitiser, 03-06 suggestion, 03-07 folder intake, phase-04, phase-05, phase-07]

actuals:
  tokens: 11500
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Issue-returning intake (expected failures become ERROR Issues, never raised)"
    - "Staged files get generated names (model_000.stp, sym_001.kicad_sym, fp_002.kicad_mod); no path part derived from a member name"
    - "Adapter registry list ADAPTERS plus shared locate(); later vendors append, callers never change"

key-files:
  created:
    - kicad_lib_manager/importer/__init__.py
    - kicad_lib_manager/importer/adapters/__init__.py
    - kicad_lib_manager/importer/package.py
    - kicad_lib_manager/importer/candidate.py
    - kicad_lib_manager/importer/adapters/base.py
    - kicad_lib_manager/importer/adapters/ultralibrarian.py
    - kicad_lib_manager/importer/detect.py
    - kicad_lib_manager/importer/suggest.py
    - tests/test_adapters.py
  modified: []

key-decisions:
  - "UL marker weights as planned: KiCADv6/v5 folder 4, ImportGuide(s).html 3, timestamp .kicad_sym 2, ul_ zip stem 1; claim at 5 points; the sample scores 1.0"
  - "Staged files use the lowercase whitelist extension; the vendor's original file name stays on ModelItem.filename"
  - "Package fields other than source and kind have defaults so refused packages can be built incrementally"

patterns-established:
  - "Pattern: _refuse(package, issue) appends the Issue, closes the staging folder and clears files"
  - "Pattern: _copy_capped reads the cap globals at call time so later plans can monkeypatch them"

requirements-completed: [INTK-01, INTK-02, LIB-01]

coverage:
  - id: D1
    description: "UL sample zip is opened, staged outside the repo, claimed by the UL adapter at confidence 1.0, and symbol CSD85301Q2, footprint DQK0006B and model DLV0006A.stp are located with names read from inside the files"
    requirement: "INTK-02"
    verification:
      - kind: unit
        ref: "tests/test_adapters.py#test_ultra_sample_end_to_end"
        status: pass
      - kind: unit
        ref: "tests/test_adapters.py#test_ultra_sample_part_meta"
        status: pass
    human_judgment: false
  - id: D2
    description: "Staging uses generated names under a temp folder outside the repo, ignores guides and readme, and Package works as a with block and with explicit idempotent close()"
    requirement: "INTK-01"
    verification:
      - kind: unit
        ref: "tests/test_adapters.py#test_ultra_sample_staging"
        status: pass
      - kind: unit
        ref: "tests/test_adapters.py#test_ultra_explicit_close"
        status: pass
      - kind: unit
        ref: "tests/test_adapters.py#test_ultra_progress_calls"
        status: pass
      - kind: unit
        ref: "tests/test_adapters.py#test_ultra_unsupported_and_missing"
        status: pass
    human_judgment: false
  - id: D3
    description: "Library-name suggestion IC_SubCategory_TI at low confidence with the SubCategory placeholder and the D-04 placeholder_tokens contract"
    requirement: "LIB-01"
    verification:
      - kind: unit
        ref: "tests/test_adapters.py#test_ultra_suggestion"
        status: pass
      - kind: unit
        ref: "tests/test_adapters.py#test_ultra_placeholder_tokens"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-19
status: complete
plan_head_before: b304331f05e02cd8e63fa6312463607f2c35335f
plan_head_after: 42bc52d05f7b9e2389ee5720746726011067a997
---

# Phase 3 Plan 01: Package Intake Tracer and UL Naming Summary

**Qt-free `importer/` subpackage that stages the Ultra Librarian zip in a temp folder outside the repo, claims it with a scored UL adapter, locates symbol, footprint and model by names read from inside the files, and suggests `IC_SubCategory_TI` at low confidence**

## Performance

- **Duration:** 25 min
- **Started:** 2026-10-19T13:35:00Z (approx.)
- **Completed:** 2026-10-19T13:59:52Z
- **Tasks:** 2 (3 commits: tracer, TDD RED, TDD GREEN)
- **Files modified:** 9 created, 0 modified

## Accomplishments

- Tracer path works end to end on the real sample: `open_package` -> staging (`model_000.stp`, `sym_001.kicad_sym`, `fp_002.kicad_mod`, SHA-256 per file) -> `UltraLibrarianAdapter` (1.0) -> `locate` -> `ImportCandidate` with `CSD85301Q2` / `DQK0006B` / `DLV0006A.stp`, and no ERROR Issue.
- `PartMeta` filled from symbol properties (reference U, datasheet `https://www.ti.com/lit/gpn/csd85301q2`, keywords, fp filters); HTML guides and readme are listed in one INFO `intake.ignored_members` Issue and never written.
- `Package` supports both lifetimes (with block and explicit idempotent `close()`), reports progress as `(message, i, total)`, and refuses missing / unsupported / corrupt inputs without raising.
- `suggest_library` yields `IC_SubCategory_TI` (Type from reference `U`, Manufacturer from the `ti.com` host table, SubCategory placeholder) with `naming.low_confidence` and `naming.placeholder` warnings; `placeholder_tokens` documents the D-04 refusal contract.

## Task Commits

1. **Task 1: UL sample zip -> staging -> UL adapter -> candidate (tracer)** - `8980ce1` (feat)
2. **Task 2 RED: failing suggestion tests** - `8d7c373` (test)
3. **Task 2 GREEN: suggestion implementation** - `42bc52d` (feat)

**Plan metadata:** committed separately (docs: complete plan)

## TDD Gate Compliance

- **RED:** `test_ultra_suggestion` and `test_ultra_placeholder_tokens` were committed in `8d7c373` alongside signature-only stubs in `suggest.py` (empty name, empty placeholder list). A first run with no module failed at collection with `ModuleNotFoundError`, which is INVALID_RED, so the stubs were added so the target tests fail on the planned assertions (`'' == 'IC_SubCategory_TI'`, `[] == ['SubCategory']`). Semantic assessment: both failures are on the planned behavior. `workflow.tdd_mode` is not enabled in config, so the `check tdd-red-evidence` classifier was not run.
- **GREEN:** `42bc52d` makes both pass; full suite green.
- **REFACTOR:** none needed.

## Files Created/Modified

- `kicad_lib_manager/importer/package.py` - `open_package`, `Package`, `PackageFile`, caps, counted copy, zip staging
- `kicad_lib_manager/importer/candidate.py` - `PartMeta`, `SymbolItem`, `FootprintItem`, `ModelItem`, `ImportCandidate`, `ExistingLibrary`
- `kicad_lib_manager/importer/adapters/base.py` - `Detection`, `Adapter` protocol, `part_meta`, `locate`
- `kicad_lib_manager/importer/adapters/ultralibrarian.py` - UL marker scoring
- `kicad_lib_manager/importer/detect.py` - `ADAPTERS` registry and `detect_candidate`
- `kicad_lib_manager/importer/suggest.py` - library-name suggestion skeleton and placeholder contract
- `kicad_lib_manager/importer/__init__.py`, `kicad_lib_manager/importer/adapters/__init__.py` - empty
- `tests/test_adapters.py` - 9 UL tests (7 tracer, 2 suggestion)

## Decisions Made

- Followed the plan's UL weights and staged-name scheme exactly.
- `Package` list fields and `staging_dir` carry defaults, so a refused package can be built incrementally and returned as-is.
- `open_package` treats a directory path as `intake.unsupported` until plan 03-07 adds the folder branch.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Signature-only stubs in the RED commit**
- **Found during:** Task 2 (RED)
- **Issue:** With no `suggest.py`, the new tests fail at collection with an import error, which tdd.md classes as INVALID_RED.
- **Fix:** Committed minimal stubs of `suggest.py` with the RED tests so they fail on the planned assertions; the GREEN commit replaced them.
- **Files modified:** kicad_lib_manager/importer/suggest.py
- **Verification:** RED run showed 2 failed (assertion errors), 7 passed; GREEN run 9 passed.
- **Committed in:** 8d7c373

---

**Total deviations:** 1 auto-fixed (1 blocking, process only)
**Impact on plan:** None on behavior; only the shape of the RED commit.

## Issues Encountered

None. Note: the Task 1 tracer was written test-first but committed once (tests and implementation together), as the task is `type="tracer"`, not `tdd="true"`.

## Test Results

Run with the main checkout interpreter from the worktree root: `pytest -q` gives **524 passed, 9 skipped**. The skips are the existing submodule-dependent tests (`Custom/` and `WurthElektronik/KiCad-Library` not checked out in the worktree). `tests/test_adapters.py -k ultra`: 9 passed. `git status --porcelain -- Custom downloaded_examples` printed nothing. Qt-free import check printed `[]`; the no-bulk-extraction grep printed nothing; both `__init__.py` files are 0 lines.

## Known Stubs

None.

## Threat Flags

None. The only write target is the system temp staging folder; the threat-model mitigations T-03-01 to T-03-05 are implemented as planned (resolved-path check against the repo root, generated staged names with "xb" and `ZipInfo` open, `TemporaryDirectory` cleanup, HTML never written, counted copy against caps).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 03-03 (zip pre-scan and cap matrix), 03-04 (legacy rules, content sniffing), 03-05, 03-06 and 03-07 can build on `package.py`, `locate` and `suggest.py` as laid out. The AST layering guard from plan 03-02 should be run against these modules once both wave-1 branches are merged.

## Self-Check: PASSED

- All nine created files exist on disk (verified with `[ -f ]` listing).
- Commits `8980ce1`, `8d7c373`, `42bc52d` are ancestors of HEAD.

---
*Phase: 03-package-intake-and-naming*
*Completed: 2026-10-19*
