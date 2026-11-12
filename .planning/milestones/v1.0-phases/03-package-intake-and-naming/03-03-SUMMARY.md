---
phase: 03-package-intake-and-naming
plan: 03
subsystem: importer-intake
tags: [zipfile, zip-slip, zip-bomb, nested-zip, tempfile, pytest]

requires:
  - phase: 03-package-intake-and-naming
    provides: "03-01 open_package / Package / _refuse / _copy_capped zip staging; 03-02 tests/zipfixtures.py hostile-zip builders and the importer layering guard"
provides:
  - "Whole-package refusal on the first hostile, duplicate or encrypted member before any byte is read or a staging folder exists (D-05, D-19, A8)"
  - "Cap enforcement on declared sizes for every member and on real bytes while copying (D-06): member count, member size, total size, integer 200:1 ratio above 1 MiB"
  - "Nested zip opened one level deep inside the same budget (D-08); two deep refused"
  - "Junk-name filter (__MACOSX, '._' members) and staging-outside-repo / always-cleaned-up proofs (D-07)"
affects: [03-04, 03-05, 03-06, 03-07, phase-04, phase-05]

actuals:
  tokens: 9500
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "_prescan judges only ZipInfo headers, so a refused zip has never had a staging folder"
    - "_stage_zip returns the refusal Issue and _open_zip calls _refuse after every zip handle is closed (Windows cannot delete an open file)"
    - "Cap globals are read at call time inside _prescan and _copy_member so tests monkeypatch them"

key-files:
  created:
    - tests/test_package_zip.py
  modified:
    - kicad_lib_manager/importer/package.py

key-decisions:
  - "Nested members are recorded in names/files/ignored/legacy as '<nested>.zip/<inner>' (prefixed), consistent with PackageFile.member, so vendor adapters see the nested zip as a folder"
  - "_prescan takes an optional prefix so an inner member is shown as 'inner.zip/../x.step' in Issue text, while the label stays 'outer.zip/inner.zip'"
  - "Per entry the order is hostile, duplicate, encrypted, member count, member size, total size, ratio; the first breach wins"

patterns-established:
  - "Pattern: staging work runs in a helper that returns Issue | None; the caller closes handles, then refuses"

requirements-completed: [INTK-06]

coverage:
  - id: D1
    description: "A zip with any hostile member (.., absolute, UNC, leading backslash, drive letter, ':', control character, empty name, symlink, reparse point) is refused whole with one ERROR intake.hostile_member naming the member; nothing is staged, even for ignored members"
    requirement: "INTK-06"
    verification:
      - kind: unit
        ref: "tests/test_package_zip.py#test_hostile_member_refuses_package,test_hostile_ignored_member_still_refuses,test_hostile_symlink_member_refuses,test_hostile_reparse_point_member_refuses,test_hostile_long_name_is_truncated_in_text,test_hostile_reason_empty_name"
        status: pass
    human_judgment: false
  - id: D2
    description: "Duplicate (casefolded) and encrypted members each refuse the whole package; benign and non-ASCII names are accepted and staged under generated ASCII names (D-19)"
    requirement: "INTK-06"
    verification:
      - kind: unit
        ref: "tests/test_package_zip.py#test_duplicate_member_refuses,test_duplicate_distinct_names_not_refused,test_encrypted_member_refuses,test_hostile_benign_names_accepted"
        status: pass
    human_judgment: false
  - id: D3
    description: "Caps with exact boundaries: member count, member size, declared total, integer ratio rule, bomb refused and random data accepted, real-byte counting, lying headers, empty and non-zip inputs"
    requirement: "INTK-06"
    verification:
      - kind: unit
        ref: "tests/test_package_zip.py#test_cap_member_count_boundary,test_cap_member_size_boundary,test_cap_total_boundary,test_ratio_rule_boundaries,test_ratio_bomb_refused_and_random_accepted,test_copy_capped_counts_real_bytes,test_lying_header,test_empty_and_not_a_zip"
        status: pass
    human_judgment: false
  - id: D4
    description: "Nested zip one level deep with shared budget, two deep and hostile inner members refused, junk members ignored"
    requirement: "INTK-06"
    verification:
      - kind: unit
        ref: "tests/test_package_zip.py#test_nested_one_level,test_nested_two_deep_refused,test_nested_hostile_and_budget,test_junk_members_ignored"
        status: pass
    human_judgment: false
  - id: D5
    description: "Staging stays outside the repo and is always cleaned up: staging-in-repo refusal, repo byte-identical after the UL sample, cleanup on exception, concurrent packages isolated"
    requirement: "INTK-06"
    verification:
      - kind: unit
        ref: "tests/test_package_zip.py#test_staging_in_repo_refused,test_ul_sample_leaves_repo_unchanged,test_cleanup_on_exception_and_concurrent"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-10-19
status: complete
commits: 4
plan_head_before: af7bf2b412306a4fa45362d8ec697436e091d872
plan_head_after: 0e61e67a0c7cdda611729873f4960ade23545778
---

# Phase 3 Plan 03: Zip Safety and Cap Hardening Summary

**`open_package` now refuses a whole zip on the first hostile, duplicate, encrypted, oversized or over-compressed member before any byte is read, opens a nested zip one level deep inside the same byte and member budget, and is proven to stage only whitelisted files in a temp folder outside the repo that never outlives its Package**

## Performance

- **Duration:** about 12 min
- **Started:** 2026-10-19T14:01:00Z (approx.)
- **Completed:** 2026-10-19T14:13:00Z
- **Tasks:** 2 (4 production commits: RED and GREEN per task)
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `_hostile_reason` + `_prescan` check every header (directories and ignored members included) on the backslash-normalised name: empty, absolute/UNC, drive letter, control character, `:` (D-19), all-dots segment, symlink mode, Windows reparse bit (A8); duplicates compare casefolded; encrypted flag bit refuses. One ERROR names the member with a repr cut at 200 characters.
- Caps (D-06): `_prescan` enforces member count (directories counted), per-member and total declared size, and `_ratio_exceeded` (`file_size > RATIO_MIN_SIZE and file_size > MAX_RATIO * max(compress_size, 1)`, integers only). `_copy_member` counts real bytes against `min(MAX_MEMBER_BYTES, MAX_TOTAL_BYTES - budget.actual)`; a header that under-declares fails CPython's CRC check and becomes `intake.corrupt`.
- Nested zips (D-08): the nested archive is copied under the shared budget to `nested_NNN.zip`, pre-scanned with the same `_Budget`, its whitelisted members staged after the outer ones with `member = '<nested>.zip/<inner>'`, and the copy removed. A zip inside a nested zip gives `intake.nested_too_deep`.
- `__MACOSX/` and `._` members are classified ignored before the extension test, so they are listed and never staged.
- 40 new tests pin every boundary: exact `MAX_MEMBERS`, `MAX_MEMBER_BYTES`, `MAX_TOTAL_BYTES`, `RATIO_MIN_SIZE` (and +1), exactly 200:1 versus 200:1+1, compress_size 0.

## Task Commits

1. **Task 1 RED: failing hostile/duplicate/encrypted tests** - `df7a953` (test)
2. **Task 1 GREEN: pre-scan refusal rules** - `57cc165` (feat)
3. **Task 2 RED: failing caps/nested/junk/staging tests** - `d37e684` (test)
4. **Task 2 GREEN: caps, nested zips, junk filter, `_stage_zip`** - `0e61e67` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

## TDD Gate Compliance

- **Task 1 RED (`df7a953`):** 21 failed, 4 passed (the 4 are the benign-name and distinct-name acceptance tests, which pin behavior that must not regress). Failures are on the planned assertions: `[] == ['intake.hostile_member']`, `intake.corrupt != intake.encrypted` (encrypted read raised RuntimeError in the old path), and `AttributeError` for the not-yet-existing `_hostile_reason`. No collection error. GREEN: 25 passed.
- **Task 2 RED (`d37e684`):** 9 failed, 31 passed. The failures are on the planned assertions (`[] == ['intake.too_many_members']`, `[] == ['intake.too_large']`, `[] == ['intake.nested_too_deep']`, junk files staged, `_ratio_exceeded` missing). The 22 already-green tests are regression pins for behavior plan 03-01 already provided (member-size cap via the counted copy, corrupt and empty zips, staging-in-repo, cleanup, UL repo-unchanged). Names are reached through the `pkg` module object so a missing helper fails at run time, not at collection. GREEN: 63 passed across `test_package_zip.py`, `test_adapters.py`, `test_importer_layering.py`.
- **REFACTOR:** none needed. `workflow.tdd_mode` is not enabled, so the `check tdd-red-evidence` classifier was not run; semantic assessment of each RED is recorded above.

## Files Created/Modified

- `kicad_lib_manager/importer/package.py` - `_Budget`, `_shown`, `_hostile_reason`, `_prescan`, `_ratio_exceeded`, `_is_junk_name`, `_copy_member`, `_stage_zip`; `_classify` gains junk and nested classes; `_open_zip` delegates to `_stage_zip`
- `tests/test_package_zip.py` - 40 tests (hostile matrix, duplicates, encryption, caps, ratio, lying headers, nested, junk, staging, cleanup)

## Decisions Made

- Inner names are appended to `names`, `ignored` and `legacy` with the `<nested>.zip/` prefix, so vendor adapters that read `package.names` see a nested zip as a folder and `PackageFile.member` stays consistent.
- `_prescan` got an optional `prefix` keyword (not in the plan's signature) so the Issue for a hostile inner member reads `member 'inner.zip/../x.step'`; the label stays `outer.zip/inner.zip` as planned.
- Staging work moved into `_stage_zip`, which returns the refusal Issue; `_open_zip` calls `_refuse` only after the outer and nested `ZipFile` handles are closed, because an open nested copy would make the staging-folder cleanup fail silently on Windows.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Refusal moved out of the open-handle scope**
- **Found during:** Task 2 (nested zips)
- **Issue:** Calling `_refuse` from inside the `with ExitStack()` / `with zf:` block would try to remove the staging folder while `nested_NNN.zip` is still open, which fails on Windows and, with `ignore_cleanup_errors=True`, would leave the folder behind.
- **Fix:** `_stage_zip` returns `Issue | None`; `_open_zip` refuses after all handles are closed.
- **Files modified:** kicad_lib_manager/importer/package.py
- **Verification:** `test_nested_two_deep_refused` and `test_nested_hostile_and_budget` assert the temp folder is empty after refusal.
- **Committed in:** 0e61e67

**2. [Plan wording] `_prescan` prefix parameter**
- Added `prefix: str = ""` so the plan's required text (`inner.zip/../x.step`) holds while keeping the plan's `outer.zip/inner.zip` label. Additive; no other caller affected.

**3. [Plan wording] too_large text for the copy overflow**
- The 03-01 text ("Could not stage member ... larger than the size limit") became the plan's "Refused {label}: member {shown} is larger than it declared". No test depended on the old text.

---

**Total deviations:** 1 auto-fixed (1 blocking) plus 2 small plan-wording adjustments
**Impact on plan:** None on behavior; all stated truths hold.

## Issues Encountered

- The sandbox rejects compound and heredoc shell commands in the worktree, so test files were written with the Edit tool and git/pytest were run as separate plain calls.
- Per-plan commit ledger file could not be written with a compound git command; `plan_head_before` is the known base `af7bf2b` and the commit count was measured with `git rev-list --count af7bf2b..HEAD` (4 at production HEAD).

## Test Results

- `pytest -q` from the worktree root with the main checkout interpreter: **590 passed, 9 skipped** (baseline before this plan was 550 passed, 9 skipped; +40 new tests). The 9 skips are the submodule-dependent tests (`Custom/` and `WurthElektronik/KiCad-Library` are not checked out in the worktree).
- `tests/test_package_zip.py`: 40 passed, 0 skipped; `-k repo_unchanged` 1 passed 0 skipped; `-k staging_in_repo` 1 passed.
- `tests/test_adapters.py` + `tests/test_importer_layering.py`: 23 passed, no skips (the layering guard now runs on the merged importer package and passes).
- `git status --porcelain -- Custom downloaded_examples` printed nothing.

## Known Stubs

None.

## Threat Flags

None. All mitigations in the plan's threat register are implemented and tested (T-03-06 to T-03-13); no new network, auth or trust-boundary surface beyond the planned system temp staging folder. T-03-SC: no package installed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 03-04 to 03-07 can rely on a non-refused `Package` holding only whitelisted files under generated names in a temp folder outside the repo, with nested zip members named `<nested>.zip/<inner>`.
- Plan 03-07 (folder intake) should reuse `_hostile_reason`, `_is_junk_name` and `_ratio_exceeded`-style caps where they apply to loose files.

## Self-Check: PASSED

- `kicad_lib_manager/importer/package.py` and `tests/test_package_zip.py`: FOUND
- Commits `df7a953`, `57cc165`, `d37e684`, `0e61e67`: FOUND as ancestors of HEAD

---
*Phase: 03-package-intake-and-naming*
*Completed: 2026-10-19*
