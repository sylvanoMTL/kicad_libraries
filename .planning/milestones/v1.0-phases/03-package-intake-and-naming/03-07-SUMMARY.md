---
phase: 03-package-intake-and-naming
plan: 07
subsystem: importer-intake
tags: [os.scandir, folder-intake, junction, symlink, read-only, pytest]

requires:
  - phase: 03-package-intake-and-naming
    provides: "03-03 _Budget caps / _classify / _refuse / junk filter; 03-04 LooseAdapter and legacy rules; 03-02 unpack_sample (D-17)"
provides:
  - "open_package(folder, repo_root) reads a folder of loose KiCad and 3D files in place, read-only: kind 'folder', staging_dir None, staged False, posix names, size and sha256 (INTK-01)"
  - "Links and junctions never followed (INFO intake.link_skipped); folders deeper than MAX_FOLDER_DEPTH = 8 not read (WARNING intake.depth_limit)"
  - "Zip caps reused for folders: MAX_MEMBERS on every entry, MAX_MEMBER_BYTES / MAX_TOTAL_BYTES on whitelisted files, counted read via _hash_file (intake.too_many_members, intake.too_large)"
  - "D-17 proof of success criterion 1 on real files: the UL zip unpacked flat or at archive paths gives the same names, sha256 and PartMeta as the zip form"
affects: [phase-04, phase-05]

actuals:
  tokens: 12500
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Breadth-first folder walk with collections.deque and os.scandir (3.10-safe; no Path.walk, no Path.is_junction)"
    - "Link detection = DirEntry.is_symlink() or st_file_attributes reparse bit, always with follow_symlinks=False"
    - "Folder files are only ever opened with mode 'rb'; a counted read (_hash_file) catches files that grow after listing"

key-files:
  created:
    - tests/test_package_folder.py
  modified:
    - kicad_lib_manager/importer/package.py

key-decisions:
  - "Existing _classify(name) -> (class, ext) kept as is (it already returns 'stage' with the extension); the folder walk reuses it instead of the plan's string-only return, so test_package_zip.py is untouched"
  - "Folder entries that are neither regular files nor folders (sockets, devices) are skipped silently; entries whose stat fails give WARNING intake.unreadable_file"
  - "Link and depth lists in the Issue text are cut at 20 names with 'and N more', like the ignored-members note"

patterns-established:
  - "Pattern: _ignored_issue(label, ignored) is the single builder of the intake.ignored_members INFO for zip and folder"

requirements-completed: [INTK-01, INTK-02]

coverage:
  - id: D1
    description: "A picked folder is read in place without being touched: kind folder, no staging, staged False, posix relative names, sha256 equal to the file bytes; snapshot of paths, sizes, mtimes and hashes is identical after open, detect and close"
    requirement: "INTK-01"
    verification:
      - kind: unit
        ref: "tests/test_package_folder.py#test_folder_reads_in_place,test_folder_is_not_modified,test_folder_names_are_posix,test_folder_dispatch"
        status: pass
    human_judgment: false
  - id: D2
    description: "Symlinks and junctions are not followed and are named in one INFO intake.link_skipped; folders past MAX_FOLDER_DEPTH are named in one WARNING intake.depth_limit"
    requirement: "INTK-01"
    verification:
      - kind: unit
        ref: "tests/test_package_folder.py#test_is_link_detects_symlink_and_reparse_bit,test_folder_junction_skipped,test_folder_depth_limit,test_folder_depth_default_is_eight"
        status: pass
      - kind: unit
        ref: "tests/test_package_folder.py#test_folder_symlink_skipped"
        status: unknown
    human_judgment: false
  - id: D3
    description: "Caps hold for folders: member count, member size, total size, counted read incl. a file that grows after listing; non-whitelisted files are never read; unreadable folders and files are warnings"
    requirement: "INTK-01"
    verification:
      - kind: unit
        ref: "tests/test_package_folder.py#test_folder_caps,test_folder_counted_read,test_folder_counted_read_refuses_a_file_that_outgrew_its_listing,test_folder_progress,test_folder_unreadable_folder_and_file_are_warnings"
        status: pass
    human_judgment: false
  - id: D4
    description: "Folders flow through detection like zips: real UL files unpacked flat are claimed by Loose at 0.3, the unzipped UL download by UltraLibrarian at 0.9, both with the same sha256 and PartMeta as the zip; empty, legacy-only and zip-inside folders behave as for zips"
    requirement: "INTK-02"
    verification:
      - kind: unit
        ref: "tests/test_package_folder.py#test_folder_real_loose_files,test_folder_unzipped_ul,test_zip_and_folder_same_shape,test_folder_loose_candidate,test_folder_empty_and_legacy_only,test_folder_zip_inside_is_ignored"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-10-19
status: complete
commits: 3
plan_head_before: bce329ae46b61858b754d393ea3c42d9d07f0cbc
plan_head_after: b693f75ee24eaf25e3bee83af96d2191f6c566db
---

# Phase 3 Plan 07: Folder Intake Summary

**`open_package` now reads a user-picked folder of loose KiCad and 3D files in place and read-only (breadth-first `os.scandir`, symlinks and junctions skipped, depth 8, zip caps with a counted read), and the real Ultra Librarian files unpacked into `tmp_path` give the same names, sha256 and PartMeta as the zip, as Loose (0.3) or UltraLibrarian (0.9)**

## Performance

- **Duration:** about 15 min
- **Completed:** 2026-10-19
- **Tasks:** 2 (3 commits: RED, GREEN, proof tests)
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `_open_folder` walks with a `deque` of `(folder, depth)` and `os.scandir`, entries sorted by casefolded name; names and `PackageFile.member` are posix paths relative to the picked folder; nothing is staged, so `staging_dir` stays `None` and `staged` is `False`.
- Link safety (T-03-27): `_is_link` is `DirEntry.is_symlink()` or the `st_file_attributes` reparse bit via `stat(follow_symlinks=False)`; links are listed in one INFO `intake.link_skipped` and never entered. A real junction test passes on this machine.
- Limits (T-03-28, T-03-30): `MAX_FOLDER_DEPTH = 8` (WARNING `intake.depth_limit`), `MAX_MEMBERS` on every entry, `MAX_MEMBER_BYTES` / `MAX_TOTAL_BYTES` on whitelisted files only, and `_hash_file(path, limit)` counts real bytes so a file that grows after listing is refused with `intake.too_large`.
- Read-only (T-03-29): files are only opened `"rb"`; a before/after snapshot of every path, size, mtime_ns, sha256 and folder is identical after open, `detect_candidate` and `close`.
- `_ignored_issue(label, ignored)` now builds the `intake.ignored_members` note for both zip and folder; `.zip` files inside a folder are listed as ignored and never opened.
- D-17 proof of success criterion 1: `unpack_sample(..., flat=True, kicad_only=True)` read as a folder is claimed by Loose at 0.3 and gives symbol `CSD85301Q2`, footprint `DQK0006B`, model `DLV0006A.stp` with the same sha256 and PartMeta as the zip; `unpack_sample(...)` at archive paths is UltraLibrarian at 0.9.

## Task Commits

1. **Task 1 RED: failing folder intake tests** - `9e40e52` (test)
2. **Task 1 GREEN: read-only folder walk** - `1eda3d0` (feat)
3. **Task 2: zip/folder parity and real-file proofs** - `b693f75` (test)

**Plan metadata:** committed with this SUMMARY (docs).

## TDD Gate Compliance

- **Task 1 RED (`9e40e52`):** 10 failed, 1 passed, 1 skipped. Failures are on the planned assertions: `package.kind == 'folder'` got `'zip'`, `['intake.unsupported'] == ['intake.too_many_members']`, no `intake.link_skipped` note, no progress calls, and `AttributeError` for the not-yet-existing `MAX_FOLDER_DEPTH` / `_hash_file`. The one pass (`test_folder_is_not_modified`) is a regression pin that is trivially true while folders are unsupported. No collection error; names reached through the `pkg` module object. Semantic assessment: the target tests executed and failed because folder intake did not exist. `workflow.tdd_mode` is not enabled, so `check tdd-red-evidence` was not run.
- **Task 1 GREEN (`1eda3d0`):** 66 passed, 1 skipped (symlink privilege) across `test_package_folder.py`, `test_package_zip.py`, `test_importer_layering.py`.
- **Task 2 (`b693f75`):** these tests exercise the existing detection pipeline over the Task 1 walk and passed at once (no defect found in `_open_folder`), so there was no RED for them; they are the plan's acceptance proofs, committed as `test(...)`. Documented rather than fabricated.
- **REFACTOR:** none needed.

## Files Created/Modified

- `kicad_lib_manager/importer/package.py` - `MAX_FOLDER_DEPTH`, `_ignored_issue`, `_hash_file`, `_is_link`, `_open_folder`, folder branch in `open_package`; `_open_zip` uses `_ignored_issue`
- `tests/test_package_folder.py` - 20 tests (read in place, snapshot, links, depth, caps, counted read, progress, unreadable, dispatch, detection and parity on real UL files)

## Decisions Made

- Kept the existing `_classify(name) -> (class, ext)` from plan 03-03 rather than the plan's string-returning signature; it already distinguishes junk/nested/stage/legacy/ignored and keeps `test_package_zip.py` unchanged.
- Entries that are not regular files or folders (sockets, devices) are skipped silently; a `stat` failure on an entry is a WARNING `intake.unreadable_file`.
- Link and depth Issue texts list at most 20 names plus "and N more".

## Deviations from Plan

### Plan wording adjustments

**1. [Plan wording] `_classify` signature**
- **Found during:** Task 1
- **Issue:** The plan asks to extract `_classify(name) -> str`; plan 03-03 had already extracted it as `(class, ext)`.
- **Fix:** Reused it unchanged; only `_ignored_issue` was newly extracted.
- **Files modified:** none beyond the plan list
- **Committed in:** 1eda3d0

**2. [Rule 2 - Missing critical] Extra regression tests**
- **Found during:** Task 1
- **Issue:** The symlink test cannot run without privileges here, leaving the `is_symlink` branch of link detection unproven.
- **Fix:** Added `test_is_link_detects_symlink_and_reparse_bit` (fake DirEntry) and a grow-after-listing test, `test_folder_unreadable_folder_and_file_are_warnings` and `test_folder_depth_default_is_eight`.
- **Files modified:** tests/test_package_folder.py
- **Committed in:** 1eda3d0

---

**Total deviations:** 0 auto-fixed bugs, 1 wording adjustment, 1 added tests
**Impact on plan:** None on behavior; all stated truths hold. No files outside `files_modified` were touched; no follow-up needed in detect.py, adapters or candidate.py.

## Issues Encountered

- `os.symlink` needs a privilege this account lacks (WinError 1314), so `test_folder_symlink_skipped` skips as the plan allows; the symlink branch is covered by the fake-entry test and the junction test (which ran and passed).
- The sandbox rejects compound git commands in the worktree, so git was run as plain separate calls and the commit ledger file was not written; `plan_head_before` is the known base `bce329a` and the count was measured with `git rev-list --count bce329a..HEAD`.

## Test Results

- `pytest -q` from the worktree root with the main-checkout interpreter: **689 passed, 11 skipped** (10 submodule-dependent skips because `Custom/` and `WurthElektronik/KiCad-Library` are not checked out, plus the 1 symlink-privilege skip).
- `tests/test_package_folder.py`: 19 passed, 1 skipped (`test_folder_symlink_skipped`); `-k real_loose_files`: 1 passed, 0 skipped; `-k "loose or unzipped or same_shape or empty or zip_inside or posix"`: 7 passed.
- Task 2 verify set (`test_package_folder`, `test_package_zip`, `test_adapters`, `test_legacy_rules`, `test_importer_layering`): 107 passed, 1 skipped.
- `git status --porcelain -- Custom downloaded_examples` printed nothing.

## Known Stubs

None.

## Threat Flags

None. T-03-27 to T-03-30 are implemented and tested; no new network, auth or trust-boundary surface. T-03-SC: no package installed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- A folder `Package` has the same shape as a zip one, so install and GUI phases can treat both uniformly; the only difference is that folder files are the user's own files (`staged False`) and must never be written or deleted by later phases.
- Phase 7 still owes real SnapEDA and SamacSys/CSE samples; the D-17 waiver covers only Phase 3's loose-folder format.

## Self-Check: PASSED

- `kicad_lib_manager/importer/package.py` and `tests/test_package_folder.py`: FOUND
- Commits `9e40e52`, `1eda3d0`, `b693f75`: FOUND as ancestors of HEAD

---
*Phase: 03-package-intake-and-naming*
*Completed: 2026-10-19*
