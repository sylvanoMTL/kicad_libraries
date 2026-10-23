---
phase: 07-snapeda-and-samacsys-adapters
plan: 09
subsystem: testing
tags: [snapeda, 3d-model, real-vendor-samples, licence-guard, requirements, gap-closure]

requires:
  - phase: 07-snapeda-and-samacsys-adapters
    provides: "open_model_source, attach_models and the synthetic SnapEDA model fixtures from plan 07-07"
provides:
  - "gated real-sample tests: the real SnapEDA model zip opens, and CAD zip + model zip install a linked USB4145-03-0170-C.stp"
  - "originality guard extended to the real model download (hash match and lowercase part name)"
  - "FMT2-02 moved into v1 in REQUIREMENTS, PROJECT, ROADMAP and 07-CONTEXT"
affects: [07-08, phase-7-verification]

actuals:
  tokens: 3500
  tasks: 2
  commits: 2

plan_head_before: 44a76584162baab6bcdac79d28804e3257a19d56
plan_head_after: a9b6d7cb004785a9b9b390cf34f795fb2ad7e4f9

tech-stack:
  added: []
  patterns:
    - "file-name-gated real-sample tests: skipif on the download's name, reason names the file (D-02)"
    - "two real packages held open in one with block until apply_plan returns"

key-files:
  created: []
  modified:
    - tests/test_real_vendor_samples.py
    - tests/test_vendorfixtures.py
    - .planning/REQUIREMENTS.md
    - .planning/PROJECT.md
    - .planning/ROADMAP.md
    - .planning/phases/07-snapeda-and-samacsys-adapters/07-CONTEXT.md

key-decisions:
  - "No implementation change: the gated tests passed against the 07-07 code on first run, so package.py and adapters/base.py were not touched (Task 1 action step 3 did not apply)"
  - "requirements mark-complete deliberately not run: FMT2-02 and INTK-03 are shared with plans 07-07 and 07-08 and the orchestrator owns tracking writes"

patterns-established:
  - "Real model download is read only through open_model_source into a temp staging folder outside the repo; nothing from downloaded_examples/ is copied, extracted or staged"

requirements-completed: [FMT2-02, INTK-03]

coverage:
  - id: D1
    description: "The real SnapEDA model zip opens: exactly usb4145-03-0170-c.stp (2443718 bytes, ISO-10303-21; header), staged outside the repo, the .txt listed as not imported, staging folder removed on close"
    requirement: FMT2-02
    verification:
      - kind: integration
        ref: "tests/test_real_vendor_samples.py#test_real_snapeda_model_zip_opens"
        status: pass
    human_judgment: false
  - id: D2
    description: "The real SnapEDA CAD zip plus its real model zip install Custom/3DModels/USB4145-03-0170-C.stp linked as ${CUSTOM_3DMODEL_DIR}/USB4145-03-0170-C.stp with the Footprint field Connector_USB_GCT:GCT_USB4145-03-0170-C_REVA2 and no no_model issue or ERROR"
    requirement: FMT2-02
    verification:
      - kind: integration
        ref: "tests/test_real_vendor_samples.py#test_real_snapeda_installs_with_separate_model"
        status: pass
    human_judgment: false
  - id: D3
    description: "The model zip stays local (git check-ignore matches, git ls-files lists only the UL sample) and the synthetic model fixture shares no SHA-256 with any real model member nor the real part name in either case"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_real_vendor_samples.py#test_vendor_zips_stay_local"
        status: pass
      - kind: unit
        ref: "tests/test_vendorfixtures.py#test_fixture_originality[snapeda_model]"
        status: pass
    human_judgment: false
  - id: D4
    description: "REQUIREMENTS, PROJECT, ROADMAP and 07-CONTEXT record FMT2-02 as v1 and the amended no-model rule"
    requirement: FMT2-02
    verification:
      - kind: other
        ref: "Task 2 docs check script (prints docs ok)"
        status: pass
    human_judgment: true
    rationale: "The wording of the requirement, decision and success criterion is the owner's call; the script only checks that the planned edits are present"

duration: 20min
completed: 2026-10-23
status: complete
---

# Phase 7 Plan 09: Real SnapEDA model download tests and FMT2-02 docs Summary

**The owner's real SnapEDA CAD zip plus its real 3D model zip are proven to install a linked `USB4145-03-0170-C.stp` into a synthetic `Custom/` (skipping by file name on a fresh clone), the model zip is proven git-ignored and the synthetic fixture original, and FMT2-02 now sits in v1 in the planning docs.**

## Performance

- **Duration:** about 20 min
- **Started:** 2026-10-23T22:30Z (approx.)
- **Completed:** 2026-10-23T22:50Z
- **Tasks:** 2
- **Files modified:** 6 (no new files)

## Accomplishments

- `test_real_snapeda_model_zip_opens`: `open_model_source` on the real model zip stages exactly `usb4145-03-0170-c.stp` (2443718 bytes, starts `ISO-10303-21;`) under a staging folder inside the test temp root and outside the repo, lists `usb4145-03-0170-c.txt` as not imported, and removes the staging folder on close.
- `test_real_snapeda_installs_with_separate_model`: open_package on the real CAD zip, `open_model_source` on the real model zip, `attach_models`, `build_plan` into a synthetic `Custom/`, `apply_plan`. Model installs as `Custom/3DModels/USB4145-03-0170-C.stp`, the installed footprint has exactly one model path `${CUSTOM_3DMODEL_DIR}/USB4145-03-0170-C.stp`, the symbol Footprint field is `Connector_USB_GCT:GCT_USB4145-03-0170-C_REVA2`, `intake.model_attached` is present, `intake.no_model` and `install.no_model` are absent, no ERROR.
- `test_vendor_zips_stay_local` also asserts `git check-ignore` matches the model zip (the existing `.gitignore` rule covers it; `.gitignore` untouched). `git ls-files downloaded_examples` still lists only `ul_CSD85301Q2.zip`.
- Originality guard: `REAL_ZIPS["snapeda_model"]`, the parametrize entry, `_all_members()` including `snapeda_model_members()`, and `REAL_PART_NAMES` gaining the lowercase `usb4145-03-0170-c`, so the parse/small/deterministic/originality checks cover the synthetic model download.
- Docs: FMT2-02 is a v1 Package Intake requirement traced to Phase 7 (coverage 54); PROJECT.md loses the Out of Scope entry and gains an Active item and a Key Decision; ROADMAP Phase 7 lists FMT2-02 with a fourth success criterion and a corrected Research flag; 07-CONTEXT keeps its original rule with a dated amendment.

## TDD Gate Compliance

Task 1 is marked `tdd="true"` but there is no RED commit and no GREEN (`feat`) commit. The tests exercise production code delivered by plan 07-07 (`open_model_source`, `attach_models`), so every new test passed on its first run; there was no behaviour to implement. Forcing a RED would have meant weakening an assertion or deleting working code, so none was made. The tests are regression guards on real data: a single `test(07-09)` commit carries them. No defect was found, so Task 1 action step 3 (fix in `package.py` / `adapters/base.py`) did not apply and neither file was touched.

## Task Commits

1. **Task 1: real SnapEDA model zip opens, attaches and installs when present, stays local** - `6d064c1` (test)
2. **Task 2: separately downloaded model moved into v1 in the planning docs** - `a9b6d7c` (docs; includes the approved ROADMAP.md Phase 7 content edit)

**Plan metadata:** the commit that adds this file (docs).

## Files Created/Modified

- `tests/test_real_vendor_samples.py` - `REAL_SNAPEDA_MODEL`, `requires_snapeda_model`, the two new gated tests, the extra check-ignore assertion
- `tests/test_vendorfixtures.py` - originality guard extended to the model download
- `.planning/REQUIREMENTS.md`, `.planning/PROJECT.md`, `.planning/ROADMAP.md` (Phase 7 section only), `.planning/phases/07-snapeda-and-samacsys-adapters/07-CONTEXT.md` - FMT2-02 reversal

## Decisions Made

- No production change was needed; the 07-07 implementation handled the real 2.4 MB model zip as designed.
- `requirements mark-complete` was not run: FMT2-02 and INTK-03 are declared by plans 07-07 and 07-08 as well, 07-08 is not finished, and in worktree mode the orchestrator owns tracking. FMT2-02 is left unchecked / `Pending` in REQUIREMENTS.md as the plan specifies.

## Deviations from Plan

None - plan executed exactly as written (the absent RED/GREEN split is explained under TDD Gate Compliance and is not a code deviation).

## Issues Encountered

- The real vendor zips are gitignored and absent from a fresh worktree. As approved by the owner, the two SnapEDA zips were copied from the main checkout into this worktree's `downloaded_examples/` before Task 1 (SHA-256 verified, `check-ignore` printed both, `git status` showed nothing). They were never staged; `git log --name-only` over the plan's commits shows no `downloaded_examples/` path.
- Verification here shows 6 skips, none naming a SnapEDA zip: five name `LIB_RS3-1212S_H3.zip` (the SamacSys real sample, not copied into this worktree because only the two SnapEDA files were approved) and one is the symlink-privilege skip in `test_model_source.py` (Windows account lacks the privilege). Baseline before my edits was 42 passed, 6 skipped; after, 45 passed, 6 skipped.
- Pre-existing, unrelated: 4 real `kicad-cli` tests fail on the base (KiCad 10 writes symbol format 20251024 where tests expect 20241209). They are outside the suites this plan touches and were not run here.

## Known Stubs

None.

## Threat Flags

None. T-07-31 (model zip never committed) and T-07-32 (synthetic fixture originality) are mitigated as planned and covered by `test_vendor_zips_stay_local` and `test_fixture_originality[snapeda_model]`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for phase verification once plan 07-08 lands. The owner should re-run UAT test 2 (G-07-2) with the real CAD zip plus model download in the dialog. FMT2-02 stays `Pending` in the traceability table until the orchestrator marks it after the shared-ID gate clears.

## Self-Check: PASSED

- Modified files present: the two test modules and four planning docs exist; this SUMMARY exists.
- Commits present on this branch: `6d064c1`, `a9b6d7c`.
- `git ls-files downloaded_examples` prints only `downloaded_examples/ul_CSD85301Q2.zip`; no commit of this plan touches `downloaded_examples/`.
- Task 2 docs check prints `docs ok`; the four-suite pytest run is 45 passed, 6 skipped with no SnapEDA skip.

---
*Phase: 07-snapeda-and-samacsys-adapters*
*Completed: 2026-10-23*
