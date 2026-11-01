---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 08
subsystem: help-and-review-closure
tags: [help, documentation, review-disposition, phase-gate]

requires:
  - phase: 12-import-flow-fixes-and-case-sensitive-re-test
    provides: "12-01..12-07 behaviours: table repoint, blank Destination, Finishing state, KiCad-open question"
provides:
  - "Help pages Generating Tables and Importing Parts describe the Phase 12 behaviour in plain language"
  - "05-REVIEW-DISPOSITION.md records WR-01, WR-02, WR-03, WR-05, WR-06 as fixed by Phase 12 plans"
affects: [verify-work, phase 12 verification]

actuals:
  tokens: 4500
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "The Help sentence quotes the Finishing strip through the imported FINISHING_TEXT constant"

key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_help_dialog.py
    - .planning/milestones/v1.0-phases/05-import-ui-and-post-install/05-REVIEW-DISPOSITION.md

key-decisions:
  - "Help text uses only wording the app shows (Retry, Change anyway, Not now, Cancel, the strip text); no new field names or code names were added"
  - "The KICAD_LIB_GITHUB / CUSTOM_3DMODEL_DIR names already in the Generating bullet were kept as they were; the new sentences add none"

requirements-completed: [REV-01, REV-02, REV-03, REV-04, REV-05]

coverage:
  - id: D1
    description: "Help describes the KiCad-open check, Retry / Change anyway / Not now, the merge into current settings and the empty Destination"
    requirement: REV-05
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_describes_phase_12_behaviour"
        status: pass
    human_judgment: false
  - id: D2
    description: "Help describes the Install wait during a comparison, the Finishing strip with Cancel and the slow note, and the stale-entry repoint, live clash and hand entries"
    requirement: REV-01
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_describes_phase_12_behaviour"
        status: pass
    human_judgment: false
  - id: D3
    description: "05-REVIEW-DISPOSITION.md marks WR-01, WR-02, WR-03, WR-05 and WR-06 fixed with the Phase 12 plan; WR-04 unchanged"
    requirement: REV-01
    verification:
      - kind: manual
        ref: "grep -A 3 'id: WR-0[12356]' ... | grep -c 'disposition: fixed' prints 5"
        status: pass
    human_judgment: false
  - id: D4
    description: "With a real kicad-cli the window stays live during Change..., open and close while a preview rebuilds"
    requirement: REV-04
    human_judgment: true
    rationale: "Real kicad-cli timing; pending owner check (see below)"

duration: 20min
completed: 2026-11-01
status: complete
commits: 2
plan_head_before: 9412c8078d06ae11852f19e99216a31f0b32cfd7
plan_head_after: 38e759e6340f8dd36e70ff84ab6848322967f532
---

# Phase 12 Plan 08: Help text, review dispositions and phase gate Summary

**Help now explains the KiCad-open question (Retry / Change anyway / Not now), the Finishing strip with Cancel, the stale-entry repoint and the empty Destination, and the v1.0 review findings WR-01, WR-02, WR-03, WR-05 and WR-06 are recorded as fixed by their Phase 12 plans.**

## Accomplishments

- `help_dialog.py` imports `FINISHING_TEXT` from `import_dialog` and uses it in the Install and result section. Generating Tables: the path-variable bullet says the app checks whether KiCad is open, that the question offers Retry, Change anyway and Not now, that the settings are read again and only these two paths change, and a new bullet says an empty Destination writes nothing. Importing Parts: Conflicts says Install Part waits while a comparison is prepared; Install and result has a paragraph on Change..., another package or closing during the build (greyed dialog, strip with the text, carries on by itself, Cancel to stay, slow note after 10 s, kicad-cli gives up after 60 s); Library tables says a stale entry the app added earlier is pointed at the installed library after a backup, and that another existing library or a hand-added entry is left alone with a warning, and an empty Destination writes no table.
- `test_help_describes_phase_12_behaviour` checks these claims on the plain text of both pages and that no raw field name (`ki_`) appears. The existing claims test and the token-only and heading-size tests still pass.
- `05-REVIEW-DISPOSITION.md`: the front matter, the table and the Notes list set WR-01, WR-02, WR-03, WR-05 and WR-06 to fixed with the notes the plan names; WR-04 and every other row are unchanged. The acceptance grep prints 5.

## Task Commits

1. **Task 1 (tracer): Help pages describe the table, Finishing and KiCad-open behaviour** - `e9f518f` (feat)
2. **Task 2: review dispositions** - `38e759e` (docs)

## Verification

- Task 1: `pytest tests/test_help_dialog.py -q`: 18 passed.
- Per-wave set (Task 2 automated command, run in the foreground from the worktree root with the main checkout's interpreter): `tests/test_table_add_entries.py tests/test_kicad_config.py tests/test_help_dialog.py tests/test_main_window.py tests/test_main_window_import.py tests/test_install_apply.py tests/test_install_plan.py tests/test_case_sensitive_install.py tests/test_backup_dialog.py`: 421 passed, 0 failed, 0 skipped, 4 DeprecationWarnings (QDragEnterEvent, pre-existing), 37.7 s.
- Full suite: by orchestrator decision it is not run in this worktree (no submodules, so the Wuerth results and the four expected workstation skips cannot be shown). The orchestrator runs `env/Scripts/python.exe -m pytest -q -rs` in the main checkout on base commit 9412c80 and re-runs `tests/test_help_dialog.py` after merging this plan; the result is recorded at verification. This is the planned phase gate, not a deviation.
- `START_SHA` for the acceptance check on touched files: `9412c8078d06ae11852f19e99216a31f0b32cfd7`. `git diff --name-only 9412c80..HEAD` lists only the three files this plan changes (plus this SUMMARY once committed).

## Deviations from Plan

None - plan executed as written. The plan's full-suite background run was replaced by the orchestrator's run (instruction from the orchestrator, see Verification). The on-disk plan ledger file of protocol 0c was not written (the harness blocks writes into the shared git directory, as in 12-05 and 12-07); the base commit was verified at start and `git rev-list --count 9412c80..HEAD` was 2 before this SUMMARY commit.

## Pending owner check (REV-04, real kicad-cli)

Not done here; the executor has no display and no way to time a real kicad-cli. Setup: KiCad 10 installed so the app finds kicad-cli. In `C:\Git_Repo_Clones\Kicad_Libraries-importer` run `.\env\Scripts\python.exe kicad_lib_manager.py`, press Ctrl+I, Browse to `downloaded_examples\ul_CSD85301Q2.zip` and wait for the preview.

- Check 1: type one letter at the end of the Description box and within a second press Change....
- Check 2: open the package again, type a letter, and within a second press Change..., then Cancel on the strip.
- Check 3: type a letter and within a second press the window X. Close the app without installing anything.

Expected: Check 1: if the preview was still rebuilding, the dialog greys out, the cursor is busy, a strip at the bottom reads "Finishing the preview..." with a Cancel button, the window can still be dragged, and the dialog returns to the Start page by itself; if the rebuild had already ended, Change... goes straight to the Start page. Check 2: Cancel brings back the preview with the package still open and the cursor normal. Check 3: the dialog closes by itself once the rebuild ends. The window never freezes; if a rebuild takes over 10 s the strip adds "kicad-cli is slow to respond (it gives up after 60 s)". Nothing is written to Custom/.

Also noted by 12-06: the real KiCad-open dialog (button look, default Retry, wording) has not been seen with KiCad running; the owner should see it once.

## Known Stubs

None.

## Threat Flags

None. T-12-22 is mitigated: each fixed finding names the Phase 12 plan and the behaviour, matching the SUMMARYs of 12-03 to 12-07.

## Self-Check: PASSED

- `kicad_lib_manager/widgets/help_dialog.py`, `tests/test_help_dialog.py` and `05-REVIEW-DISPOSITION.md` carry the changes; commits e9f518f and 38e759e are on the branch.
