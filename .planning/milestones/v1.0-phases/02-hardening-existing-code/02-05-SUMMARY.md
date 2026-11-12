---
phase: 02-hardening-existing-code
plan: 05
subsystem: scanner
tags: [kicad, sexpr, 3d-models, scan-issues, tdd]

requires:
  - phase: 02-hardening-existing-code
    provides: "kicad_files.find_models / ModelRef (02-03), Issue-based scan results (02-09), sexpr Edit/quote"
provides:
  - "kicad_files.retarget_model(ref, new_path) -> Edit: span-only model path edit (for plan 02-07 and Phase 4 INST-05)"
  - "library_scanner.check_3d_model_paths rewritten on the s-expression parser with a per-source rule"
  - "Issue codes scan.model_var, scan.model_missing, scan.unreadable"
  - "library_scanner.CUSTOM_MODEL_PREFIX constant"
affects: [02-07 model path cleanup, 04 importer INST-05]

actuals:
  tokens: 19000
  tasks: 2
  commits: 4

plan_head_before: ab739e07c61b63032e1b6c831ff4c4c5e9c92652
plan_head_after: 860f6701ffc990a27064854a12fe0e4fa4d097ae

tech-stack:
  added: []
  patterns:
    - "Exact-name existence check: build a set of relative file names from rglob instead of probing the filesystem (case-sensitive on Windows)"
    - "Per-source scan rule keyed on _determine_source: Custom enforces the variable convention, other sources only flag absolute paths"
    - "Parse failures become WARNING Issues (scan.unreadable) and the scan continues"

key-files:
  created: []
  modified:
    - kicad_lib_manager/kicad_files.py
    - kicad_lib_manager/library_scanner.py
    - tests/test_edits.py
    - tests/test_scanner_issues.py
    - tests/test_scanner_skip_dirs.py

key-decisions:
  - "No scan pre-filter was added for Wurth speed; parser-based scan of live Custom/ took 0.32 s, Wurth is not checked out anywhere on this machine so its cost stays unmeasured (OQ3/A4)"
  - "RED tests for retarget_model call kicad_files.retarget_model through the module so the RED failure is an AttributeError in each target test, not a collection-time ImportError"

patterns-established:
  - "Model path edits go through kicad_files.retarget_model + sexpr.apply_edits, never string replace"

requirements-completed: [HARD-09]

coverage:
  - id: D1
    description: "retarget_model returns a span-only Edit; CRLF, BOM, bare-atom and quote-containing paths round-trip"
    requirement: HARD-09
    verification:
      - kind: unit
        ref: "tests/test_edits.py -k retarget (5 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Custom/ model paths: scan.model_var for non-${CUSTOM_3DMODEL_DIR} paths, scan.model_missing for absent or wrong-case files"
    requirement: HARD-09
    verification:
      - kind: unit
        ref: "tests/test_scanner_issues.py -k custom_model"
        status: pass
    human_judgment: false
  - id: D3
    description: "Other sources stay quiet for ${...} and bare paths; only absolute paths give scan.model_absolute"
    requirement: HARD-09
    verification:
      - kind: unit
        ref: "tests/test_scanner_issues.py -k other_source"
        status: pass
    human_judgment: false
  - id: D4
    description: "Unparseable footprint gives one scan.unreadable WARNING and the scan continues"
    requirement: HARD-09
    verification:
      - kind: unit
        ref: "tests/test_scanner_issues.py::test_unreadable_footprint_warns_and_scan_continues"
        status: pass
    human_judgment: false
  - id: D5
    description: "Live Custom/ checkout yields only the five D-16 scan.model_var findings and no scan.model_missing"
    requirement: HARD-09
    verification:
      - kind: other
        ref: "read-only run of check_3d_model_paths against C:/Git_Repo_Clones/Kicad_Libraries-importer (5 x scan.model_var, 0 other); in-repo live test skips in this worktree (no Custom/) and runs in the post-merge gate"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-19
status: complete
---

# Phase 2 Plan 05: Model Path Scan Rules Summary

**Parser-based, per-source 3D model path checks (scan.model_var / scan.model_missing with exact-name matching) plus a tested span-only `retarget_model` edit helper**

## Performance

- **Duration:** about 25 min
- **Started:** 2026-10-19T08:46:00Z (approx)
- **Completed:** 2026-10-19T09:12:00Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 5

## Accomplishments
- `kicad_files.retarget_model(ref, new_path)` returns `Edit(path_node.start, path_node.end, quote(new_path))`; tested on the CRLF two-model fixture, a bare-atom path, a BOM file, input immutability and a path containing a double quote.
- `check_3d_model_paths` no longer uses a regex. It loads each `.kicad_mod` with `kicad_files.load`, finds models with `find_models`, and applies a rule by source: under `Custom/` every path must start with `${CUSTOM_3DMODEL_DIR}/` (else `scan.model_var`) and the remainder must be in an exact-name set of `Custom/3DModels` (else `scan.model_missing`); in other sources only absolute or non-variable paths warn (`scan.model_absolute`).
- Unparseable footprints give a `scan.unreadable` WARNING and the scan continues.
- Live check (read-only against the main checkout's `Custom/`): exactly five `scan.model_var` findings, all in the D-16 files, zero `scan.model_missing`, 0.32 s.

## Task Commits

1. **Task 1: retarget_model** - `613540f` (test, RED), `1492461` (feat, GREEN)
2. **Task 2: per-source model-path rule** - `80dc710` (test, RED), `860f670` (feat, GREEN)

**Plan metadata:** committed after this file (docs).

## TDD Evidence

- **Task 1 RED:** 5 `-k retarget` tests failed with `AttributeError: module 'kicad_lib_manager.kicad_files' has no attribute 'retarget_model'` (tests reach the helper via the module so each target test fails on its own, not at collection). Semantic assessment: the target tests executed and failed because the planned function does not exist yet. GREEN: 5 passed, full suite 483 passed.
- **Task 2 RED:** 9 of 25 tests in `tests/test_scanner_issues.py` failed on assertions (model_var / model_missing codes, `scan.unreadable`, scan_all inclusion, `MODEL_RE` removal); the "quiet" cases passed against the old regex as expected. GREEN: all pass.
- No `refactor` commits were needed. `gsd_run check tdd-red-evidence` was not run (plan type is `execute`, not `tdd`).

## Files Created/Modified
- `kicad_lib_manager/kicad_files.py` - `retarget_model`; sexpr import extended with `Edit`, `quote`
- `kicad_lib_manager/library_scanner.py` - `CUSTOM_MODEL_PREFIX`, `_custom_model_names`, rewritten `check_3d_model_paths`; `MODEL_RE` removed; imports `kicad_files`
- `tests/test_edits.py` - five retarget tests and `_apply_edit_on_disk` helper
- `tests/test_scanner_issues.py` - 18 model-path tests (synthetic repos, live Custom, `wurth`-marked quiet test)
- `tests/test_scanner_skip_dirs.py` - `test_model_absolute_issue_shape` moved to a `WurthElektronik/` source

## Decisions Made
- Existence check uses a set built from `rglob` and exact string membership, never `Path.exists()`, so `c.STEP` vs `c.step` is caught on Windows (T-02-16).
- No Wurth pre-filter added (plan OQ3/A4 says only on measured regression).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing model_absolute shape test contradicted the new Custom rule**
- **Found during:** Task 2 (GREEN full-suite run)
- **Issue:** `tests/test_scanner_skip_dirs.py::test_model_absolute_issue_shape` wrote an absolute model path under `Custom/` and expected `scan.model_absolute`; under D-18 that is now `scan.model_var`.
- **Fix:** Moved the fixture to a `WurthElektronik/F.pretty` source, which still expects `scan.model_absolute`; the Custom case is covered in `test_scanner_issues.py`.
- **Files modified:** tests/test_scanner_skip_dirs.py (not in the plan's `files_modified`)
- **Verification:** full suite 499 passed, 9 skipped
- **Committed in:** `860f670`

---

**Total deviations:** 1 auto-fixed (1 test updated for the new rule)
**Impact on plan:** Necessary consequence of the planned rule change; no scope creep.

## Issues Encountered
- The Wurth timing item (OQ3) could not be measured: `WurthElektronik/KiCad-Library` is not checked out in this worktree or in the main checkout (0 `.kicad_mod` files). The `wurth`-marked test skips with the standard reason. Parser cost on Custom/ was 0.32 s.
- The in-repo live Custom test skips in this worktree (no `Custom/Footprints`); the equivalent check was run read-only against `C:/Git_Repo_Clones/Kicad_Libraries-importer/Custom/` and the post-merge gate in the main checkout will run the real test. `Custom/` was not modified.

## Known Stubs
None.

## Threat Flags
None. T-02-16 (case-insensitive false "found") and T-02-17 (malformed footprint crashing the scan) are mitigated and tested.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 02-07 can use `kicad_files.retarget_model` + `sexpr.apply_edits` to rewrite the five D-16 footprints; after that the live scan should report zero model findings.

## Self-Check: PASSED

- Files modified exist; commits `613540f`, `1492461`, `80dc710`, `860f670` are ancestors of HEAD.
- Acceptance criteria re-run: `MODEL_RE` absent, `kicad_files.find_models` / three issue codes present in `library_scanner.py`, 0 `.exists()` calls in `_custom_model_names`, `-k "model or live or unreadable"` 16 passed (2 skipped by design), `-k collision` 7 passed, full suite 499 passed, 9 skipped.

---
*Phase: 02-hardening-existing-code*
*Completed: 2026-10-19*
