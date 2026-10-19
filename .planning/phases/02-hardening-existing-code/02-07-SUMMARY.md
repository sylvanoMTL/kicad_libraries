---
phase: 02-hardening-existing-code
plan: 07
subsystem: library-data
tags: [kicad, 3d-models, custom-submodule, git-submodule, cleanup]

requires:
  - phase: 02-hardening-existing-code
    provides: "retarget_model span-only edit helper and check_3d_model_paths scan rule (plan 02-05)"
provides:
  - "Five legacy Custom footprints reference ${CUSTOM_3DMODEL_DIR}/<file> instead of ${KIPRJMOD}/Custom/3DModels/<file>"
  - "One dedicated Custom commit (485d530) on main and one parent gitlink bump (e9e7fcb)"
  - "Live Custom test now requires zero scan.model_* findings"
affects: [phase-02 verification, Custom submodule push]

actuals:
  tokens: 1500
  tasks: 3
  commits: 2

plan_head_before: b7edeeb85d5dfe594d7fb57613196c116c7243e1
plan_head_after: c006b48

tech-stack:
  added: []
  patterns:
    - "Submodule cleanup: commit in Custom first with explicit paths, then gitlink-only parent commit via `git commit -- Custom`"

key-files:
  created: []
  modified:
    - Custom/Footprints/Connector_USB_GCT.pretty/GCT_USB4730-GF-A_REVA.kicad_mod
    - Custom/Footprints/IC_Battery_Fuel_Gauge_ADI.pretty/BGA8N40P2X4_93X167X69N.kicad_mod
    - Custom/Footprints/IC_Battery_Fuel_Gauge_ADI.pretty/SON50P200X200X80-9N.kicad_mod
    - Custom/Footprints/IC_Button_Controller_ADI.pretty/DFN-8_DDB.kicad_mod
    - Custom/Footprints/IC_Button_Controller_ADI.pretty/TSOT-23_TS8.kicad_mod
    - Custom (parent gitlink)
    - tests/test_scanner_issues.py

key-decisions:
  - "Owner approved the Custom commit at the Task 2 blocking-human checkpoint ('commit') after seeing the exact five-file diff and the orphan-risk warning; nothing was pushed"
  - "Removed the now-unused _D16_FILES constant from tests/test_scanner_issues.py when tightening the live test"

patterns-established:
  - "Live submodule tests assert zero findings and skip when the submodule is absent"

requirements-completed: [HARD-09]

coverage:
  - id: D1
    description: "The five D-16 footprints use ${CUSTOM_3DMODEL_DIR}/<same file name>; each file differs by exactly one inserted and one deleted line"
    requirement: HARD-09
    verification:
      - kind: other
        ref: "git -C Custom diff-tree --numstat 485d530 (5 files, each 1/1) and git -C Custom grep -n KIPRJMOD -- '*.kicad_mod' (no match)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Scan of Custom/ reports zero scan.model_var and zero scan.model_missing Issues, asserted by a committed live test"
    requirement: HARD-09
    verification:
      - kind: unit
        ref: "tests/test_scanner_issues.py#test_live_custom_model_findings_are_zero"
        status: pass
    human_judgment: false
  - id: D3
    description: "One owner-approved Custom commit on main, one gitlink-only parent commit, neither repository pushed"
    requirement: HARD-09
    verification:
      - kind: other
        ref: "git -C Custom rev-parse origin/main == 6b1fcb4 and git -C Custom rev-list --count origin/main..main == 1; git show --name-only e9e7fcb prints only Custom"
        status: pass
    human_judgment: false
  - id: D4
    description: "Boards that already placed these footprints still carry the old embedded ${KIPRJMOD} path until Update Footprint from Library is run in KiCad"
    verification: []
    human_judgment: true
    rationale: "Behavior inside KiCad on the owner's boards cannot be asserted by a repo test"

duration: 20min
completed: 2026-10-19
status: complete
---

# Phase 2 Plan 07: Legacy 3D Model Path Cleanup Summary

**The five legacy `${KIPRJMOD}/Custom/3DModels/` footprints now reference `${CUSTOM_3DMODEL_DIR}/<file>` via one owner-approved, span-only Custom commit, a gitlink-only parent bump, and a live test that requires zero Custom model-path findings; nothing was pushed.**

## Performance

- **Duration:** about 20 min of executor time, split across the Task 2 owner checkpoint (Task 1 in the first run, Task 3 in the continuation)
- **Completed:** 2026-10-19
- **Tasks:** 3 (Task 1 auto, Task 2 blocking-human decision, Task 3 auto)
- **Files modified:** 7 (five footprints in Custom, the Custom gitlink, `tests/test_scanner_issues.py`)

## Accomplishments

- The five D-16 footprints (`GCT_USB4730-GF-A_REVA`, `BGA8N40P2X4_93X167X69N`, `SON50P200X200X80-9N`, `DFN-8_DDB`, `TSOT-23_TS8`) use `${CUSTOM_3DMODEL_DIR}/<same file name>`. Each file changed by exactly one line (numstat 1/1), CRLF endings preserved, and every target `.step` exists in `Custom/3DModels/` by exact name.
- The Custom scan reports no `scan.model_var` or `scan.model_missing` Issue; the live test `test_live_custom_model_findings_are_zero` enforces that (previously it tolerated the five D-16 warnings).
- Full suite: 553 passed, 3 skipped (Wurth submodule not checked out, unrelated).

## Task Commits

1. **Task 1: Rewrite five legacy model paths span-only (D-16)** - no commit by design; the work stayed uncommitted on Custom `main` until the owner approved
2. **Task 2: Commit-timing decision (checkpoint, blocking-human)** - owner answered `commit`
3. **Task 3: Commit, bump gitlink, tighten live test (D-17)**
   - Custom repo: `485d530998deaba79f02d57d4846909c1f6b811d` `fix(3d): use ${CUSTOM_3DMODEL_DIR} for legacy model paths` (5 files, 5 insertions, 5 deletions)
   - Parent repo: `e9e7fcb` `chore(custom): bump Custom to the legacy model path cleanup` (touches only the `Custom` gitlink, mode 160000)
   - Parent repo: `c006b48` `test(02-07): require zero Custom model-path findings`

**Plan metadata:** recorded in the docs commit that carries this file.

## Files Created/Modified

- `Custom/Footprints/**/*.kicad_mod` (five files) - model path switched to `${CUSTOM_3DMODEL_DIR}/`
- `Custom` (gitlink) - now `485d530998deaba79f02d57d4846909c1f6b811d`
- `tests/test_scanner_issues.py` - live Custom test asserts zero `scan.model_*` findings under `Custom/`; unused `_D16_FILES` removed

## Decisions Made

- The owner approved the commit at the blocking-human checkpoint after seeing the exact five-file diff, the orphan-risk warning and the board-impact note. The approval covered the Custom commit and the parent bump only, not any push.
- Dropped `_D16_FILES` rather than leaving dead code, since the tightened test no longer allowlists those files.

## Deviations from Plan

None - plan executed exactly as written.

The worktree branch-namespace check (`agent-*`) from the executor commit protocol does not apply here: the plan is sequential and must commit on `feature/part-importer`, which the orchestrator pinned. The project-root pin guard passed before each parent commit.

## Issues Encountered

None.

## Orphan risk (action required from the owner)

The new Custom commit `485d530` exists only in this worktree's private module gitdir (`C:/Git_Repo_Clones/Kicad_Libraries/.git/worktrees/Kicad_Libraries-importer/modules/Custom`). Custom's `origin/main` still points at `6b1fcb4272d64fc6697b81bade1bd71c1053d447`, and local `main` is exactly one commit ahead. The parent's `Custom` gitlink now points at `485d530`. If this worktree is removed before the commit is pushed, the commit is lost and the gitlink points at a commit nobody has.

Before removing the worktree, run:

```
git -C Custom push origin main
```

Pushing the parent branch (`feature/part-importer`) is also a separate deliberate step; it was not done here.

Edge note (HARD-09, unclassified): boards (`.kicad_pcb`) that already placed these footprints keep their embedded `${KIPRJMOD}` model path until "Update Footprint from Library" is run in KiCad, and open KiCad sessions keep the old library contents until the footprint library is reloaded. The cleaned footprints resolve their models only where `CUSTOM_3DMODEL_DIR` is set.

## Known Stubs

None.

## Threat Flags

None. No new network, auth, or file-access surface; the one-off rewrite script lives outside the repo and was not committed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

HARD-09 is closed locally. Phase 2 verification can proceed; the owner should push Custom `main` before removing this worktree.

## Verification Results

- `git -C Custom rev-parse origin/main` = `6b1fcb4272d64fc6697b81bade1bd71c1053d447`; `git -C Custom rev-list --count origin/main..main` = 1
- Task 3 `<verify>` chain (Custom on `main`, last Custom commit touches five files, Custom tree clean, origin/main unchanged, one commit ahead, parent shows no Custom change) passed
- `pytest tests/test_scanner_issues.py -k live`: 1 passed (not skipped); full suite 553 passed, 3 skipped

## Self-Check: PASSED

- Custom commit `485d530` found; parent commits `e9e7fcb` and `c006b48` are ancestors of HEAD
- `git ls-files -s Custom` shows mode 160000 at `485d530998deaba79f02d57d4846909c1f6b811d`, equal to `git -C Custom rev-parse main`

---
*Phase: 02-hardening-existing-code*
*Completed: 2026-10-19*
