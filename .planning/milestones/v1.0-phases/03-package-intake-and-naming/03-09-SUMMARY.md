---
phase: 03-package-intake-and-naming
plan: 09
subsystem: importer
tags: [zipfile, lzma, zstd, intake, gap-closure, cr-02]

requires:
  - phase: 03-package-intake-and-naming
    provides: "open_package, _copy_member, _refuse and the Issue contract (plans 03-03, 03-08)"
provides:
  - "open_package returns ERROR intake.corrupt for a damaged member on every zip codec this Python can read (LZMA, zstd included) and never raises"
  - "intake.staging_failed for a temp folder that cannot be created or resolved"
  - "corrupt_member test fixture (flip payload bytes, headers intact)"
affects: [phase-04-core, phase-05-gui-worker]

actuals:
  tokens: 6000
  tasks: 2
  commits: 4

plan_head_before: 87b09b904c8030d22523e1070a7cb82284cccf96
plan_head_after: a8a184aef45c9a7bbab9964cdb924aa767edbed5
commits: 4

tech-stack:
  added: []
  patterns:
    - "Optional decompressor errors collected in a private tuple (_READ_ERRORS) from guarded imports, no catch-all Exception handler"
    - "Tripwire test comparing the codecs zipfile can write with the codecs the corrupt-member test covers"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/package.py
    - tests/zipfixtures.py
    - tests/test_zipfixtures.py
    - tests/test_package_zip.py

key-decisions:
  - "WR-03 stays open: the write-side reporting inside _copy_member is unchanged"
  - "No catch-all handler: every decompressor error class is listed in _READ_ERRORS; a tripwire test flags new codecs"
  - "Temp-folder failures get their own code intake.staging_failed, used only for creating or resolving the folder"
  - "_FLIP_OFFSET = 10 kept as planned: its pin test raises lzma.LZMAError and ZstdError on Python 3.14.4"

requirements-completed: [INTK-06, INTK-01]

coverage:
  - id: D1
    description: "A damaged LZMA zip returns one ERROR intake.corrupt naming the member and the zip, with its staging folder already removed when open_package returns"
    requirement: INTK-06
    verification:
      - kind: unit
        ref: "tests/test_package_zip.py#test_corrupt_lzma_member_refused_and_cleaned_up"
        status: pass
      - kind: unit
        ref: "tests/test_package_zip.py#test_corrupt_lzma_fixture_raises_lzma_error"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every compression method this zipfile can write (stored, deflate, bzip2, lzma, zstd) gives one ERROR intake.corrupt for a corrupted member; a tripwire fails when a new codec appears"
    requirement: INTK-06
    verification:
      - kind: unit
        ref: "tests/test_package_zip.py#test_corrupt_member_every_codec_refused_and_cleaned_up"
        status: pass
      - kind: unit
        ref: "tests/test_package_zip.py#test_corrupt_zstd_fixture_raises_zstd_error"
        status: pass
      - kind: unit
        ref: "tests/test_package_zip.py#test_corrupt_member_covers_every_zip_codec"
        status: pass
    human_judgment: false
  - id: D3
    description: "A temp folder that cannot be created or resolved gives one ERROR intake.staging_failed naming the package and the OS reason"
    requirement: INTK-01
    verification:
      - kind: unit
        ref: "tests/test_package_zip.py#test_staging_failed_missing_temp_folder"
        status: pass
      - kind: unit
        ref: "tests/test_package_zip.py#test_staging_failed_permission_error"
        status: pass
    human_judgment: false
  - id: D4
    description: "Interrupted staging removes the files already staged and leaves a second open package byte-identical; a corrupt member in a nested zip names inner.zip/p.kicad_sym"
    requirement: INTK-01
    verification:
      - kind: unit
        ref: "tests/test_package_zip.py#test_corrupt_member_mid_staging_removes_earlier_files_and_spares_other_package"
        status: pass
      - kind: unit
        ref: "tests/test_package_zip.py#test_corrupt_nested_lzma_member_refused"
        status: pass
    human_judgment: false
  - id: D5
    description: "open_package never raises for the listed expected input faults, each returning a refused Package with exactly one ERROR Issue of the expected code"
    requirement: INTK-01
    verification:
      - kind: unit
        ref: "tests/test_package_zip.py#test_open_package_never_raises_on_expected_faults"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-10-19
status: complete
---

# Phase 3 Plan 09: Corrupt zip members and unusable temp folders Summary

**open_package now returns ERROR intake.corrupt for damaged LZMA and zstd members (and every other zip codec) and ERROR intake.staging_failed for an unusable temp folder, removing the staging folder before it returns, with no catch-all handler (CR-02)**

## Performance

- **Duration:** about 5 min
- **Started:** 2026-10-19T16:13:00Z
- **Completed:** 2026-10-19T16:17:28Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- `_READ_ERRORS` in `kicad_lib_manager/importer/package.py` adds `lzma.LZMAError` and, on Python 3.14+, `compression.zstd.ZstdError`, both from guarded imports so the module still imports without them. `_copy_member` catches the tuple and keeps its message text.
- `tempfile.TemporaryDirectory(...)` and `Path(tmp.name).resolve()` in `_stage_zip` are guarded and return ERROR `intake.staging_failed`. `_open_zip` still refuses only after every zip handle is closed, so the folder created before a resolve failure and any files already staged are removed by `_refuse`.
- `corrupt_member` in `tests/zipfixtures.py` flips payload bytes of one member with all headers intact.
- 25 new test cases (23 in `tests/test_package_zip.py`, 2 fixture self-tests): the five codec cases, nested corruption, interrupted staging with a concurrent package kept byte-identical, both staging_failed paths, the codec tripwire, and a ten-case never-raises contract.

## Task Commits

1. **Task 1 (tracer): corrupt LZMA member returns intake.corrupt and leaves no staging folder**
   - RED `2993ab7` (test)
   - GREEN `483e078` (feat)
2. **Task 2: every codec, nested and mid-staging corruption, intake.staging_failed, tripwire, never-raises**
   - RED `6f555ae` (test)
   - GREEN `a8a184a` (feat)

**Plan metadata:** committed with this SUMMARY (docs: complete plan)

## TDD Gate Compliance

- Task 1 RED (pre-fix): `test_corrupt_lzma_fixture_raises_lzma_error` passed (the pin: offset 10 raises `lzma.LZMAError` when read with zipfile) and `test_corrupt_lzma_member_refused_and_cleaned_up` failed with `_lzma.LZMAError: Corrupt input data` escaping `open_package`. The two `corrupt_member` self-tests passed once the fixture existed; before it, collection failed with `ImportError: cannot import name 'corrupt_member'`. Semantic assessment: the target test failed on the planned fault (the exception escaping open_package), not on setup or import.
- Task 2 RED (pre-fix): 5 failed, 58 passed. Failures: `test_corrupt_member_every_codec_refused_and_cleaned_up[ZIP_ZSTANDARD]` and `test_open_package_never_raises_on_expected_faults[corrupt_zstd]` (ZstdError escaping), `test_staging_failed_missing_temp_folder` and `[missing_temp_folder]` (FileNotFoundError escaping), `test_staging_failed_permission_error` (PermissionError escaping). The stored, deflate, bzip2 and lzma codec cases and the zstd pin test already passed, as expected, since those paths were covered or only read with zipfile.
- GREEN after each: all targeted tests pass. No REFACTOR commit was needed.
- The RED evidence was inspected by hand (pytest console output); `gsd check tdd-red-evidence` was not run because the project's pytest console output is not one of the classifier's report formats.

## Files Created/Modified

- `kicad_lib_manager/importer/package.py` - `_LZMA_ERRORS`, `_ZSTD_ERRORS`, `_READ_ERRORS`; guarded staging-folder creation returning `intake.staging_failed`
- `tests/zipfixtures.py` - `corrupt_member`
- `tests/test_zipfixtures.py` - `test_corrupt_member_flips_only_payload_bytes`, `test_corrupt_member_rejects_offset_past_payload`
- `tests/test_package_zip.py` - `_FLIP_OFFSET = 10` and the corrupt-member, staging_failed, tripwire and never-raises tests

## Decisions Made

- WR-03 is not folded in; the write-side reporting inside `_copy_member` is untouched.
- No catch-all handler for the base Exception class (`grep` count is 0). The expected decompressor faults are enumerated, and the tripwire test catches a codec added by a future Python.
- `_FLIP_OFFSET = 10` was kept: the LZMA and zstd pin tests both pass at that offset on Python 3.14.4.

## Deviations from Plan

None - plan executed exactly as written.

Two small test-design choices inside the plan's behavior spec: `test_staging_failed_permission_error` replaces the `tempfile` name inside `package.py` with a `types.SimpleNamespace` holding the raising callable, instead of patching `tempfile.TemporaryDirectory` on the shared module, so the patch cannot leak into other code. The never-raises cases are built by small named builder functions keyed by case id.

## Issues Encountered

None. The one `-rs` skip in the touched test modules (`test_package_folder.py`, symlink privilege on this Windows account) is unrelated to this plan.

## Verification

- `pytest tests/test_package_zip.py tests/test_zipfixtures.py tests/test_adapters.py tests/test_package_folder.py tests/test_importer_layering.py`: 133 passed, 1 skipped (symlink privilege).
- `pytest -k "corrupt or staging_failed or never_raises"` in `tests/test_package_zip.py`: 23 passed, no skips on Python 3.14.
- Full suite in this worktree: 776 passed, 13 skipped. 12 of the skips are because the `Custom/` and `WurthElektronik/KiCad-Library` submodules are not checked out in this worktree, so the submodule-dependent tests skip; the orchestrator re-runs the full suite in the main checkout after merging.
- `git status --porcelain -- Custom downloaded_examples` printed nothing.
- `git diff --name-only a4677ea... -- importer/adapters importer/detect.py importer/candidate.py` printed nothing (the fix stays inside `package.py`).
- `grep -v '^\s*#' package.py | grep -cE "except +Exception"` prints 0.

## Known Stubs

None.

## Threat Flags

None. The new code only widens an exception tuple and guards two calls; it adds no endpoint, auth path or trust boundary.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CR-02 can be set to `fixed` in 03-REVIEW-DISPOSITION.md and UAT item 2 in 03-UAT.md can be marked passed. WR-03 stays `open`. `/gsd-secure-phase` can re-audit T-03-09 (threats T-03-38 to T-03-41 are mitigated and tested).
- The Phase 5 GUI worker can rely on `open_package` returning Issues for every expected input fault.

## Self-Check: PASSED

- Files exist: `kicad_lib_manager/importer/package.py`, `tests/zipfixtures.py`, `tests/test_zipfixtures.py`, `tests/test_package_zip.py`.
- Commits exist on this branch: `2993ab7`, `483e078`, `6f555ae`, `a8a184a` (4 commits from the base `87b09b9`).
- All acceptance criteria of both tasks re-run and passing.

---
*Phase: 03-package-intake-and-naming*
*Completed: 2026-10-19*
