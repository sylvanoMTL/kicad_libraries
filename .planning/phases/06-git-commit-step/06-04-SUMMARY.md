---
phase: 06-git-commit-step
plan: 04
subsystem: git-commit-step
tags: [commit-plan, commit-message, sanitising, pytest, tdd, stdlib]

requires:
  - phase: 06-git-commit-step
    provides: "commit_plan.py tracer (CommitFile, CommitPlan, build_commit_plan, default_message, parent_message, parent_preview) from plan 06-01"
provides:
  - "build_commit_plan: files only, each once, on-disk spelling per folder below Custom, ERROR issues for outside-Custom and unknown paths"
  - "changed_since_install(cplan): D-11 stale check for plan 06-07"
  - "pre_install_bytes(cfile, backup_dir): D-09 backup lookup by SHA-256 for the diff view and plan 06-07"
  - "default_message hardened: Unknown vendor fallback, C1/U+2028/U+2029 neutralised, empty values skipped"
  - "tests/test_commit_plan.py: 27 pure tests for the plan, the stale check, the backup lookup and all messages"
affects: [06-03, 06-07, 06-08]

actuals:
  tokens: 5600
  tasks: 2
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Resolve the on-disk spelling of every path component below Custom by listing its folder (case-insensitive fallback) before handing a pathspec to git"
    - "Sanitise every interpolated message value, then decide whether its line exists from the sanitised text"

key-files:
  created:
    - tests/test_commit_plan.py
  modified:
    - kicad_lib_manager/importer/commit_plan.py

key-decisions:
  - "Disk spelling is resolved for every component below custom_dir, not only the file name, so a Symbols/symbols folder case difference cannot give git a pathspec that matches nothing"
  - "A file is listed once by its disk-spelled rel; a repeated touched path is skipped before the op lookup so it cannot raise a second unknown_file issue"
  - "Message line presence is decided on the sanitised value (a package named only of control characters gives no Import-Package line)"
  - "sanitize_line also removes C1 controls and U+2028/U+2029, because str.splitlines splits on them"

patterns-established:
  - "importer/commit_plan.py keeps exactly the imports models and importer.plan (layering test unchanged)"

requirements-completed: [GIT-04, GIT-02]

coverage:
  - id: D1
    description: "The commit plan lists exactly the files the install wrote, never a folder, once each, sorted, under their on-disk spelling, and refuses any path outside Custom or without a plan op"
    requirement: GIT-02
    verification:
      - kind: unit
        ref: "tests/test_commit_plan.py#test_build_files_only_sorted"
        status: pass
      - kind: unit
        ref: "tests/test_commit_plan.py#test_build_refuses_outside_custom"
        status: pass
      - kind: unit
        ref: "tests/test_commit_plan.py#test_build_uses_disk_spelling"
        status: pass
      - kind: integration
        ref: "tests/test_commit_plan.py#test_build_from_real_ul_plan"
        status: pass
    human_judgment: false
  - id: D2
    description: "changed_since_install and pre_install_bytes give plan 06-07 the stale check (D-11) and the pre-install bytes (D-09), matching backups by content hash"
    requirement: GIT-02
    verification:
      - kind: unit
        ref: "tests/test_commit_plan.py#test_changed_since_install"
        status: pass
      - kind: unit
        ref: "tests/test_commit_plan.py#test_pre_install_bytes_picks_matching_backup"
        status: pass
    human_judgment: false
  - id: D3
    description: "The default message records vendor, original package file name and date in the D-18 layout with no injectable control or line-break character and no local path; the parent message and preview follow D-18/D-19"
    requirement: GIT-04
    verification:
      - kind: unit
        ref: "tests/test_commit_plan.py#test_default_message_layout"
        status: pass
      - kind: unit
        ref: "tests/test_commit_plan.py#test_default_message_sanitises_controls"
        status: pass
      - kind: unit
        ref: "tests/test_commit_plan.py#test_default_message_has_no_local_paths"
        status: pass
      - kind: unit
        ref: "tests/test_commit_plan.py#test_parent_message_lists_commits"
        status: pass
    human_judgment: false

duration: 14min
completed: 2026-10-22
status: complete
plan_head_before: 87b5565b5b526b09b12047cb8c07532c34eda9ba
plan_head_after: 198fe95d83387dac796fc23d55ae4c2b74d3c011
---

# Phase 6 Plan 04: Exact Commit Plan and Messages Summary

**The commit plan now lists only real files once each under their on-disk spelling (refusing anything outside Custom), ships the D-11 stale check and the D-09 hash-matched backup lookup, and the D-18 default message cannot be split or spoofed by package-name text or leak a local path.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-10-22T18:04Z
- **Completed:** 2026-10-22T18:18Z
- **Tasks:** 2 (both TDD: RED then GREEN)
- **Files modified:** 2 (1 new test file, 1 edited module)

## Accomplishments

- `build_commit_plan` walks every path component below `Custom` through a case-insensitive folder listing (`_disk_spelling`), skips folders and repeated touched paths, and emits `commit.outside_custom` / `commit.unknown_file` ERROR issues instead of a pathspec for anything it cannot vouch for.
- `changed_since_install(cplan)` returns the display paths, in plan order, of files that are missing or no longer hash (1 MiB chunks) to `expected_sha256`; `pre_install_bytes(cfile, backup_dir)` picks the `{name}_backup_{N}` copy whose SHA-256 equals `base_sha256`, so same-named files from different folders are told apart.
- `default_message`: blank vendor label becomes `Unknown vendor`; C1 controls and U+2028/U+2029 are neutralised along with C0/DEL; Footprint, 3D model and Import-Package lines are omitted when the sanitised value is empty; Unicode text such as `Pièce—1` is untouched; no path ever enters the message.
- `tests/test_commit_plan.py` holds 27 pure tests (26 run in a fresh worktree; the real-UL install test needs the Custom checkout, and the disk-spelling test needs a case-insensitive volume). The real Ultra Librarian install test was run against the main checkout's `Custom/` (read only) and passes.

## Task Commits

1. **Task 1 RED:** `aeb61ec` (test) - duplicate listing, disk spelling and missing `changed_since_install` / `pre_install_bytes` fail
2. **Task 1 GREEN:** `052d0b8` (feat) - `_disk_spelling`, de-duplication, stale check, backup lookup
3. **Task 2 RED:** `9c5ad7b` (test) - blank vendor, Unicode line breaks and empty-after-sanitising values fail
4. **Task 2 GREEN:** `3259986` (feat) - message hardening
5. **Refactor:** `198fe95` (refactor) - `is_relative_to` for the outside-Custom check; separators written as named escapes so no invisible character sits in the source

**Plan metadata:** committed with this SUMMARY (docs).

## TDD Gate Compliance

- **Task 1 RED (`aeb61ec`):** 4 failed. `test_build_lists_each_file_once` and `test_build_uses_disk_spelling` failed on the planned assertions (two entries for one file; `Conn_A.kicad_sym` instead of `conn_a.kicad_sym`). `test_changed_since_install` and `test_pre_install_bytes_picks_matching_backup` failed with `AttributeError` because the functions did not exist; the tests reference them through the module (`commit_plan.changed_since_install`) so only those tests fail and nothing is a collection error. The four tests that passed already (sorted files, rel/display, hashes, refusals) describe behaviour plan 06-01 had built; they are kept as regression pins. `gsd_run check tdd-red-evidence` was not run (no TAP/JUnit/unittest report; pytest only).
- **Task 2 RED (`9c5ad7b`):** 3 failed on planned assertions (`Import-Vendor: ` blank line; `splitlines()` splitting at U+0085/U+2028; empty `Import-Package:` / `Footprint:` lines). The other eight message and parent-message tests were green at RED because plan 06-01 already implemented the D-18 layout; this is expected for a hardening plan and the tests pin the contract.
- **GREEN:** `052d0b8` and `3259986`. **REFACTOR:** `198fe95` (no behaviour change; tests still pass).

## Files Created/Modified

- `kicad_lib_manager/importer/commit_plan.py` - disk spelling, de-duplication, `changed_since_install`, `pre_install_bytes`, hardened `default_message`, wider control-character class
- `tests/test_commit_plan.py` - 27 tests with an `Install` helper that writes a small real install (symbol library, footprint, model) under `tmp_path`

## Decisions Made

- Disk spelling is resolved for each component below `custom_dir` (not just the file name); a path outside `custom_dir` lexically falls back to resolving the file name only.
- The repeated-path check runs before the op lookup so a duplicated unknown path yields one issue.
- Presence of a message line depends on the sanitised text, not the raw field.
- The tests import `commit_plan` as a module so a missing function fails one test, not the whole file.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Wider control-character class and empty-value handling**
- **Found during:** Task 2
- **Issue:** The plan asks that "every other control character" be replaced. The tracer's class covered only C0 and DEL; `str.splitlines()` (used by `subject_of` and Qt text handling) also splits on U+0085, U+2028 and U+2029, and a value made only of controls produced a blank `Import-Package:` / `Footprint:` trailer line.
- **Fix:** `_CONTROL_RE` now covers C0, DEL, C1 and the Unicode line and paragraph separators; footprint, model and package lines are built from the sanitised value and skipped when empty; a whitespace-only vendor label inside `default_message` falls back to `Unknown vendor`.
- **Files modified:** kicad_lib_manager/importer/commit_plan.py, tests/test_commit_plan.py
- **Verification:** `test_default_message_cannot_be_split_by_unicode_line_breaks`, `test_default_message_skips_values_that_sanitise_to_nothing`, `test_default_message_blank_vendor_label_says_unknown`
- **Committed in:** `3259986`

**2. [Rule 1 - Bug] Duplicate touched paths listed twice**
- **Found during:** Task 1
- **Issue:** `build_commit_plan` listed a path once per occurrence in `InstallResult.touched`, breaking "each exactly once".
- **Fix:** repeated raw paths and repeated disk-spelled `rel` values are skipped.
- **Files modified:** kicad_lib_manager/importer/commit_plan.py
- **Verification:** `test_build_lists_each_file_once`
- **Committed in:** `052d0b8`

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** both inside the plan's stated truths (control characters, each file once); no scope change, no signature change (plan 06-03 callers unaffected).

## Issues Encountered

- `test_build_from_real_ul_plan` skips in a fresh worktree because `Custom/` is not checked out. It was run with a throwaway pytest plugin (outside the repo) that points `conftest.REPO_ROOT` at the main checkout (read only): `tests/test_commit_plan.py` 27 passed (none skipped), `tests/test_import_dialog.py` plus it 156 passed, and `pytest -m "not kicad_cli"` gave 1624 passed, 15 skipped (all Custom/Wurth/symlink/UAT related), 0 failed. Re-run the verify line in the main checkout for the clean no-SKIPPED result; the only skip that remains legitimate there is `test_build_uses_disk_spelling` on a case-sensitive volume.
- `test_build_uses_disk_spelling` ran (NTFS is case-insensitive) and passes.

## Known Stubs

None.

## Threat Flags

None. T-06-13 (outside-Custom refusal), T-06-14 (line/trailer injection) and T-06-18 (local paths) are mitigated and each has a named test.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 06-07 can call `changed_since_install` before any git write and `pre_install_bytes` for the diff view; neither imports git or Qt.
- Plan 06-03 callers (`default_message`, `subject_of`, `parent_preview`) keep their signatures.
- `importer/commit_plan.py` still imports only `..models` and `.plan` (layering test passes).

## Self-Check: PASSED

- `kicad_lib_manager/importer/commit_plan.py` and `tests/test_commit_plan.py` exist
- Commits `aeb61ec`, `052d0b8`, `9c5ad7b`, `3259986`, `198fe95` are ancestors of HEAD
- Acceptance greps match: `def changed_since_install(`, `def pre_install_bytes(`, `_backup_(`, `is_relative_to(`, `Unknown vendor`, `to new library`, `Update `
- All test names listed in both tasks' acceptance criteria are defined in `tests/test_commit_plan.py`

---
*Phase: 06-git-commit-step*
*Completed: 2026-10-22*
