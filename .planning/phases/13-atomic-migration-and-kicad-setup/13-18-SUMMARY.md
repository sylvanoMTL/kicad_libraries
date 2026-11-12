---
phase: 13-atomic-migration-and-kicad-setup
plan: 18
subsystem: docs
tags: [claude-md, project-md, library-naming, tests-readme, docs-consistency]

# Dependency graph
requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "the Migrate to Atomic Libraries... and Set Up KiCad Chooser... menu actions (13-07, 13-13..13-17), the atomic rule and scheme (09, 10), TBL-01/TBL-02 table descriptions and chooser setup"
provides:
  - "CLAUDE.md naming section, Importing Parts steps, GUI Behavior and Menu Shortcuts entries for the Atomic_ scheme and the two new menu actions"
  - "PROJECT.md Atomic_ requirements and Key Decision marked delivered"
  - "research/LIBRARY-NAMING.md Update 2026-11 note and a refreshed section 5 target table"
  - "tests/test_docs_atomic.py keeping CLAUDE.md in step with the shipped menu text"
  - "tests/README.md Migration tests (Phase 13) section and the test_edits.py live-skip note"
  - "the owner's UAT check list for the live migration (Task 2 human-check)"
affects: [docs, tests-readme]

# Actuals (#2632)
actuals:
  tokens: 5267
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Docs-consistency test reads only tracked Markdown and main_window text constants (MIGRATE_TEXT, SETUP_CHOOSER_TEXT with & stripped), never the live Custom/, so docs and shipped menu text cannot drift apart silently"

key-files:
  created:
    - tests/test_docs_atomic.py
  modified:
    - CLAUDE.md
    - .planning/PROJECT.md
    - .planning/research/LIBRARY-NAMING.md
    - tests/README.md

key-decisions:
  - "CLAUDE.md's Key Decisions outcome for the Atomic_ scheme now reads delivered-pending-owner-UAT rather than Pending, since Phases 9-13 shipped the check, importer, commit gate and migration code; only the owner's live run on the real Custom/ remains"
  - "test_edits.py's live-skip reason after migration is the generic \"Custom submodule not checked out\" message (the code's CUSTOM_SYMBOL.exists() check has no separate renamed-away message) -- documented as-is rather than treated as a code bug, since changing it is out of this plan's scope"

requirements-completed: [DOC-01, MIG-01, MIG-02, MIG-03, MIG-04, MIG-05, TBL-01, TBL-02]

coverage:
  - id: D1
    description: "CLAUDE.md describes the Atomic_ naming scheme, the atomic rule, and the importer as the way in for vendor parts, replacing the v1 <Type>_<SubCategory>_<Manufacturer> convention"
    requirement: "DOC-01"
    verification:
      - kind: unit
        ref: "tests/test_docs_atomic.py#test_claude_md_describes_atomic_scheme"
        status: pass
    human_judgment: false
  - id: D2
    description: "CLAUDE.md names the two new menu actions (Migrate to Atomic Libraries..., Set Up KiCad Chooser...) with their shortcuts, and documents the D-26 wrong-checkout warning/refusal and the main-checkout KiCad path values"
    requirement: "DOC-01"
    verification:
      - kind: unit
        ref: "tests/test_docs_atomic.py#test_claude_md_names_the_new_actions"
        status: pass
    human_judgment: false
  - id: D3
    description: "research/LIBRARY-NAMING.md carries an update note mapping _MecaFrog to Atomic_ and MecaFrog.pretty to Atomic_Footprints.pretty, and its section 5 table is refreshed to the live parts"
    requirement: "DOC-01"
    verification:
      - kind: unit
        ref: "tests/test_docs_atomic.py#test_library_naming_has_update_note"
        status: pass
    human_judgment: false
  - id: D4
    description: "PROJECT.md's Atomic_ naming and migration requirements are checked off as delivered by Phase 13"
    requirement: "DOC-01"
    verification:
      - kind: unit
        ref: "tests/test_docs_atomic.py#test_project_md_marks_migration_delivered"
        status: pass
    human_judgment: false
  - id: D5
    description: "tests/README.md documents the migration test fixtures, the four tests needing a real git binary, the kicad_cli real-tool skip, and the live test_edits.py skip after migration"
    requirement: "MIG-01, MIG-02, MIG-03, MIG-04, MIG-05, TBL-01, TBL-02"
    verification:
      - kind: other
        ref: "grep -n \"Migration tests (Phase 13)\" tests/README.md"
        status: pass
    human_judgment: false
  - id: D6
    description: "The owner has a complete, step-by-step UAT check list to run the live migration, Set Up KiCad Chooser, and verify ROADMAP Phase 13 success criteria 1-5 on the real Custom/ and KiCad 10"
    verification: []
    human_judgment: true
    rationale: "This is a human-only live run against the owner's real Custom/ submodule and KiCad 10 installation from the main checkout; no test may touch that live data (threat T-13-42), so the plan's <human-check> block is the deliverable and only the owner can execute and judge it"

# Metrics
duration: 25min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 18: Docs for the Atomic_ Scheme and the Owner's Live Migration UAT Summary

**CLAUDE.md, PROJECT.md and research/LIBRARY-NAMING.md rewritten for the Atomic_ naming scheme and the two new menu actions, locked to the shipped code by a new docs-consistency test, plus a documented UAT check list for the owner's live migration.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-11-11T00:00:00Z (approx; not tracked by a wall clock in this session)
- **Completed:** 2026-11-11
- **Tasks:** 2 completed
- **Files modified:** 5 (4 modified, 1 created)

## Accomplishments
- Rewrote CLAUDE.md's "Library Naming Convention" (now `Atomic_<official KiCad stem>`, the atomic rule, the shared `Atomic_Footprints.pretty`) and "Importing from SnapEDA" (now "Importing Parts", leading with the importer and keeping a short manual route), and added GUI Behavior / Menu Shortcuts entries for "Migrate to Atomic Libraries..." (`Ctrl+Shift+M`), "Set Up KiCad Chooser..." (`Ctrl+Shift+K`), and the D-26 wrong-checkout warning/refusal, plus the main-checkout KiCad Path Variables values.
- Checked off the two Atomic_ requirements in PROJECT.md's Active section and updated the matching Key Decision's outcome column to reflect Phase 13 delivery.
- Added an "Update 2026-11" note to `research/LIBRARY-NAMING.md` (the `_MecaFrog` -> `Atomic_` rename, `MecaFrog.pretty` -> `Atomic_Footprints.pretty`, the D-22 crystal decision) and refreshed its section 5 target table to the live parts from the Phase 13 CONTEXT Specifics table, replacing the stale "12 reduced to 9" sentence with the D-04 success definition.
- Created `tests/test_docs_atomic.py` with four tests that read only CLAUDE.md, PROJECT.md, research/LIBRARY-NAMING.md and the `main_window.MIGRATE_TEXT` / `SETUP_CHOOSER_TEXT` constants, so the docs and the shipped menu text cannot silently drift apart.
- Added a "Migration tests (Phase 13)" section to `tests/README.md` documenting the synthetic-`Custom/` + throwaway-git-repo fixture pattern, the four tests needing a real git binary, and the `kicad_cli`-marked real-tool skip for `test_real_kicad_loads_derived_library`; updated the live-health-checks note to describe exactly how `test_edits.py` skips once the owner's live migration renames `Connector_USB_GCT.kicad_sym` away.

## Task Commits

Each task was committed atomically:

1. **Task 1: Docs describe the Atomic_ scheme and the two new actions, checked by a test (DOC-01)** - `16b0d60` (docs)
2. **Task 2: Test notes, the phase suite gate and the owner's live migration (MIG-01..05, TBL-01, TBL-02)** - `5bda487` (test)

**Plan metadata:** commit for this SUMMARY follows separately.

## Files Created/Modified
- `CLAUDE.md` - Atomic_ naming scheme, atomic rule, Importing Parts, GUI Behavior / Menu Shortcuts for the migration and chooser actions, D-26 wrong-checkout note, main-checkout KiCad Path Variables values
- `.planning/PROJECT.md` - Atomic_ requirements checked off, Key Decision outcome updated
- `.planning/research/LIBRARY-NAMING.md` - Update 2026-11 note, refreshed section 5 table
- `tests/README.md` - new "Migration tests (Phase 13)" section, updated live-health-check note for `test_edits.py`
- `tests/test_docs_atomic.py` - new docs-consistency tests (created)

## Decisions Made
- Scoped `test_claude_md_names_the_new_actions` assertions to the `### GUI Behavior` and `## KiCad Path Variables` sections specifically (not just file-wide `in` checks), matching the plan's `<behavior>` wording that ties each assertion to its section, and making the test fail precisely if a future edit moves content between sections without updating it.
- Left `.claude/CLAUDE.md` untouched, per plan instruction (it is GSD-generated and not hand-edited); verified with `git diff --stat -- .claude/CLAUDE.md` printing nothing after both commits.
- Did not add the board-feature rule (D-21) to CLAUDE.md, per the plan's "Edge coverage" note that this documentation is deferred to the phase's Deferred Ideas list, not this plan.

## Deviations from Plan

### Auto-fixed Issues

None - plan executed exactly as written for both tasks' automated scope.

### Scope-limited by dispatch instructions (not a deviation from the plan's intent, but a documented difference from the plan's literal text)

**1. [Dispatch instruction] Full-repository pytest phase gate not run in this worktree**
- **Found during:** Task 2
- **Issue:** The plan's `<verification>` section and Task 2's `<action>`/`<done>` ask the executor to run the full suite (`pytest` from the repo root, 21-27 min, started in the background) as the phase gate and record its counts in this summary.
- **Why not run here:** This worktree's dispatch instructions explicitly prohibit starting a full-repository `pytest -q` run as "extra diligence" in a parallel-executor worktree: the run takes about 30 minutes, a background run left behind would block the orchestrator from removing this worktree after I return, and the orchestrator runs the post-merge gate itself. I ran only the plan's own per-task `<verify>` commands (both `tests/test_docs_atomic.py tests/test_help_dialog.py -q` and `tests/test_docs_atomic.py -q`), which passed (71 passed, then 4 passed).
- **Files modified:** None (no code change; this is a verification-scope note, not a fix).
- **Verification:** `tests/test_docs_atomic.py` and `tests/test_help_dialog.py` pass standalone; the orchestrator's post-merge gate is the authoritative full-suite check for this phase.
- **Committed in:** not applicable (documented here, not as a code change).

---

**Total deviations:** 0 auto-fixed; 1 scope-limitation documented per explicit dispatch instruction (not a Rule 1-4 deviation).
**Impact on plan:** None on docs correctness or test coverage delivered by this plan. The full-suite phase gate and its recorded counts are deferred to the orchestrator's post-merge run, which is the correct single owner of that check across all Phase 13 worktree agents.

## Issues Encountered
None.

## Authentication Gates
None - no external service or CLI authentication was needed for this plan.

## Known Stubs
None - no stub, placeholder or empty-value pattern was introduced by this plan's doc/test changes.

## Threat Flags
None - this plan only edits tracked Markdown and adds a test that reads tracked Markdown and two Python string constants; no new network endpoint, auth path, file-access pattern, or schema change at a trust boundary is introduced.

## User Setup Required
None - no external service configuration required. The plan's `<human-check>` block (Task 2) is the owner's own live-migration UAT, run by hand from the main checkout `C:/Git_Repo_Clones/Kicad_Libraries` after this phase's branch is merged there; it is not an automated setup step and the executor never runs it (per the worktree dispatch instructions: `Custom/` is absent from this worktree and must never be read, copied from, tagged or edited here).

## Next Phase Readiness
- DOC-01 is met: CLAUDE.md, PROJECT.md and research/LIBRARY-NAMING.md describe the Atomic_ scheme and the two new menu actions, locked to the shipped code by `tests/test_docs_atomic.py`.
- `tests/README.md` now documents the migration test fixtures and the live `test_edits.py` skip behavior post-migration.
- The owner's UAT check list (Task 2's `<human-check>`) is ready to run once `feature/part-importer` is merged into `main` at the main checkout `C:/Git_Repo_Clones/Kicad_Libraries` and `Custom` is pulled there -- this is Phase 13's final manual verification of ROADMAP success criteria 1-5 on the live data, and is explicitly out of scope for any executor to run.
- The full-repository pytest phase gate for this plan (and the phase as a whole) is deferred to the orchestrator's post-merge run, per this worktree's dispatch instructions.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- `CLAUDE.md` exists and contains the Atomic_ scheme text: FOUND
- `.planning/PROJECT.md` exists with Atomic_ requirements checked: FOUND
- `.planning/research/LIBRARY-NAMING.md` exists with the Update 2026-11 note and refreshed section 5: FOUND
- `tests/README.md` exists with the "Migration tests (Phase 13)" section: FOUND
- `tests/test_docs_atomic.py` exists: FOUND
- Commit `16b0d60` (Task 1, docs): FOUND in HEAD ancestry
- Commit `5bda487` (Task 2, test): FOUND in HEAD ancestry
- `tests/test_docs_atomic.py tests/test_help_dialog.py -q`: 71 passed
- `tests/test_docs_atomic.py -q`: 4 passed
- `git diff --stat -- .claude/CLAUDE.md`: prints nothing (unchanged)
- `grep -n "Migration tests (Phase 13)" tests/README.md`: found at line 82
