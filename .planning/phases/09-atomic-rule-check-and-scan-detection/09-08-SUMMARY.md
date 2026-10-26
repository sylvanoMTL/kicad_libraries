---
phase: 09-atomic-rule-check-and-scan-detection
plan: 08
subsystem: testing
tags: [python, pytest, uat, scratch-repo, git, atomic-check]

requires:
  - phase: 09-atomic-rule-check-and-scan-detection
    provides: "09-03/09-04 atomic inventory (write_atomic_files, write_fake_kicad), ATOMIC_RULES, SAFE_FIX_KINDS; 09-05 mark_changes; 09-06 build_preview"
provides:
  - "tests/test_atomic_uat.py: UAT_MARKER, REAL_PARTS, build_atomic_uat(dest, source_custom, app_root) and four tests"
  - "Opt-in KICAD_ATOMIC_UAT_DIR builder that makes the owner's scratch repo from the live Custom/ (read only)"
  - "tests/README.md: the new expected-skip row, the 'exactly four' sentence and the live-Custom/ exception line"
affects: [phase-09 end-of-phase UAT, phase-10, phase-13 migration]

actuals:
  tokens: 4500
  tasks: 2
  commits: 2
plan_head_before: 0752bb2923a767d21d3d74511c06eff6fc184a79
plan_head_after: 7d34f3d25b30e398eb2eccdbd0ba1c13ec03c65c

tech-stack:
  added: []
  patterns:
    - "A destructive helper removes a previous output folder only when it carries the helper's own marker file (fixes the 04-REVIEW IN-03 pattern)"
    - "Scratch git repo made with an isolated environment (no GIT_* variables, empty global config) and identity, signing and autocrlf given with -c"

key-files:
  created:
    - tests/test_atomic_uat.py
  modified:
    - tests/README.md

key-decisions:
  - "The helper refuses, beyond the plan's list, a scratch that contains the source Custom/ or sits inside it, so removing a previous scratch can never delete the source"
  - "The read-only flag git puts on object files is cleared when an old scratch is removed, otherwise a rebuild fails on Windows"
  - "The README exception line names only the atomic builder: the existing KICAD_IMPORT_UAT_DIR builder does not read the live Custom/ at all, so the plan's wording 'the two opt-in UAT builders read the live Custom/' would have been wrong"
  - "The git config file the helper needs (empty global config) is written to dest as .atomic_uat_gitconfig, outside the scratch"

patterns-established:
  - "UAT helper pattern: automated self-test on the synthetic Custom/, same code run opt-in on the live Custom/ behind an environment variable"

requirements-completed: [SCAN-01, SCAN-02, SCAN-03]

coverage:
  - id: D1
    description: "build_atomic_uat makes a throwaway repo copy with the app, two real libraries renamed to Atomic_ names, the synthetic Atomic_ inventory and Custom/ as its own git repo with one baseline commit"
    requirement: "SCAN-01"
    verification:
      - kind: integration
        ref: "tests/test_atomic_uat.py#test_build_atomic_uat_tree"
        status: pass
    human_judgment: false
  - id: D2
    description: "After the baseline the scratch shows Changed (one Atomic_ symbol), Changed (one plain-library symbol) and New (footprint NEW-UAT)"
    requirement: "SCAN-02"
    verification:
      - kind: integration
        ref: "tests/test_atomic_uat.py#test_build_atomic_uat_tree"
        status: pass
    human_judgment: false
  - id: D3
    description: "A scan of the scratch has failing symbols for every rule in ATOMIC_RULES and fix specs of every SAFE_FIX_KINDS kind, and build_preview of all of them has changes and no ERROR issue"
    requirement: "SCAN-03"
    verification:
      - kind: integration
        ref: "tests/test_atomic_uat.py#test_build_atomic_uat_tree"
        status: pass
    human_judgment: false
  - id: D4
    description: "The helper only reads source_custom, refuses a destination in or containing the repository, and refuses a scratch folder it did not create"
    verification:
      - kind: integration
        ref: "tests/test_atomic_uat.py#test_build_refuses_inside_repo"
        status: pass
      - kind: integration
        ref: "tests/test_atomic_uat.py#test_build_refuses_foreign_scratch"
        status: pass
      - kind: integration
        ref: "tests/test_atomic_uat.py#test_build_atomic_uat_tree (source digest unchanged)"
        status: pass
    human_judgment: false
  - id: D5
    description: "tests/README.md lists the KICAD_ATOMIC_UAT_DIR skip, says the expected skips are exactly four and explains how to build and open the scratch repo"
    verification:
      - kind: other
        ref: "grep of tests/README.md and tests/test_atomic_uat.py for the skip message and 'exactly four'; pytest -rs prints the same message"
        status: pass
    human_judgment: false
  - id: D6
    description: "The opt-in run on the owner's real Custom/ builds a scratch repo the app opens, and the marks, highlights, dialog and every fix kind look right in it"
    requirement: "SCAN-03"
    verification: []
    human_judgment: true
    rationale: "Custom/ is not checked out in this worktree, so the live-Custom/ path skipped here; the end-of-phase checklist (Task 2 human-check) is the owner's visual and behavioural judgement"

duration: 25min
completed: 2026-10-26
status: complete
---

# Phase 9 Plan 08: Atomic-check UAT scratch repo Summary

**tests/test_atomic_uat.py builds a throwaway repo (app copy, two real libraries renamed to Atomic_ names, the synthetic Atomic_ inventory, Custom/ as its own git repo with a baseline commit and three fresh edits) that the real app can be run against, proven on a synthetic source and runnable on the live Custom/ behind KICAD_ATOMIC_UAT_DIR**

## Performance

- **Duration:** about 25 min
- **Started:** 2026-10-26T13:37Z
- **Completed:** 2026-10-26T14:03Z
- **Tasks:** 2 (1 tracer, 1 auto)
- **Files modified:** 2 (1 created: tests/test_atomic_uat.py; tests/README.md edited)

## Accomplishments

- `build_atomic_uat(dest, source_custom, app_root)` copies `kicad_lib_manager/` and `kicad_lib_manager.py`, the source `Symbols`, `Footprints` and `3DModels` (no `*.bak`), renames the two REAL_PARTS libraries (a missing stem gives way to the first unused source stem, so two real libraries are always renamed), adds the synthetic inventory with `write_atomic_files`, commits Custom/ as its own repo ("UAT baseline"), then edits one Datasheet in the first renamed Atomic_ library and one in the first plain source library and adds `NEW-UAT.kicad_mod`.
- On the synthetic source the scan of the scratch gives Changed, Changed and New, failing symbols for all seven rules, fix specs of all five safe kinds, and `build_preview` of every safe fix succeeds with no ERROR; the source digest is unchanged.
- Refusals are tested: a destination inside or containing the repository creates nothing; an existing `dest/repo` without the marker raises and keeps its files. A second build over an existing scratch (read-only git objects included) was exercised by hand and works.
- `tests/README.md` documents the new opt-in skip, says the expected skips are exactly four, and states the one live-Custom/ exception.

## Task Commits

1. **Task 1: Scratch repo builder, proven on a synthetic source (tracer)** - `0b467cd` (feat)
2. **Task 2: Test docs for the new opt-in skip and the UAT checklist** - `7d34f3d` (docs)

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified

- `tests/test_atomic_uat.py` - the helper, its refusals, the automated self-test and the opt-in builder (new)
- `tests/README.md` - skip row, "exactly four" sentence, live-Custom/ exception line

## Decisions Made

See `key-decisions` in the frontmatter. For the owner: the opt-in run needs git on PATH and a folder outside the repository; it prints the scratch path and the run command `env\Scripts\python.exe <scratch>\kicad_lib_manager.py`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Refuse a scratch that contains or sits inside the source Custom/**
- **Found during:** Task 1
- **Issue:** The plan listed refusals for the repository and a foreign scratch only. A dest chosen so that `dest/repo` contains the source would have the helper delete its own source when it removes a previous scratch (T-09-22 requires the source be only read).
- **Fix:** `_check_destination` also refuses when the scratch and the source contain each other.
- **Files modified:** tests/test_atomic_uat.py
- **Committed in:** `0b467cd`

**2. [Rule 1 - Bug] Rebuild failed on read-only git objects**
- **Found during:** Task 1 (hand check of a second build)
- **Issue:** `shutil.rmtree` cannot delete git's read-only object files on Windows, so removing a previous scratch would have failed.
- **Fix:** an error handler clears the read-only flag and retries (`onexc` on 3.12+, `onerror` before).
- **Files modified:** tests/test_atomic_uat.py
- **Committed in:** `0b467cd`

**3. [Rule 1 - Bug] README exception line would have been wrong as the plan worded it**
- **Found during:** Task 2
- **Issue:** The plan asks for "the two opt-in UAT builders read the live Custom/". `test_uat_scratch_install` (KICAD_IMPORT_UAT_DIR) builds from the synthetic Custom/ and never reads the live one.
- **Fix:** the line names only the atomic builder and says the other one does not read the live Custom/.
- **Files modified:** tests/README.md
- **Committed in:** `7d34f3d`

---

**Total deviations:** 3 auto-fixed (1 missing critical, 2 bug)
**Impact on plan:** Additive and accuracy fixes. The plan's behaviours, test names and skip text are unchanged.

## Issues Encountered

- `Custom/` and `WurthElektronik/KiCad-Library` are not checked out in this worktree, so the acceptance check `git -C Custom status --short` does not apply and the live-Custom/ path of `test_uat_atomic_scratch` was not exercised; it also stays skipped when `KICAD_ATOMIC_UAT_DIR` is unset, which is the documented skip. The orchestrator's post-merge run on the real checkout, and the owner's end-of-phase check, cover it. The same code path was run by hand against a synthetic source that also held a library named `Connector_FFC_GCT`.
- The plan's `<automated>` command is root-relative (`env/Scripts/python.exe`); `env/` is absent in the worktree, so the orchestrator checkout's interpreter was used against the worktree's code (confirmed: the package imported from the worktree).

## Known Stubs

None.

## Threat Flags

None. T-09-22 (source only read, every write under dest, dest in or around the repository refused, scratch removed only with its marker, source/scratch containment refused, live digest compared in the opt-in test) and T-09-23 (git run with no GIT_* variables, an empty global config, no system config, identity, signing and autocrlf by `-c`) are implemented. The helper writes one extra file, `.atomic_uat_gitconfig` (empty), into `dest` beside the scratch.

## User Setup Required

None - no external service configuration required. The owner's end-of-phase check is listed in 09-08-PLAN.md Task 2 `<human-check>`.

## Next Phase Readiness

- The owner can run the D-25 checklist: set `KICAD_ATOMIC_UAT_DIR` to a folder outside the repo, run `env\Scripts\python.exe -m pytest tests/test_atomic_uat.py -k uat_atomic_scratch -s`, and start the printed command. That check also needs plan 09-07's dialog to be merged.
- Open for the owner: the canonical spellings "Murata" and "TDK" (carried from 09-01), item 7 of the checklist.
- The orchestrator's phase gate should show exactly four skips on the workstation.

## Self-Check: PASSED

- FOUND: tests/test_atomic_uat.py, tests/README.md change, this SUMMARY
- FOUND commits: 0b467cd, 7d34f3d
- `pytest tests/test_atomic_uat.py -rs -q` - 3 passed, 1 skipped (the documented KICAD_ATOMIC_UAT_DIR skip)
- `pytest tests/test_atomic_uat.py tests/test_layering.py tests/test_customfixtures.py -rs -q` - 39 passed, 1 skipped
- Acceptance greps: signature line, KICAD_ATOMIC_UAT_DIR (test file and README), "expected skips are exactly four", skip message in both files

---
*Phase: 09-atomic-rule-check-and-scan-detection*
*Completed: 2026-10-26*
