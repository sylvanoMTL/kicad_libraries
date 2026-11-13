# Roadmap: KiCad Part Importer

## Milestones

- ✅ **v1.0 Part Importer** — Phases 1-7 (shipped 2026-10-25) — [archive](milestones/v1.0-ROADMAP.md)
- ✅ **v2.0 Atomic Libraries** — Phases 8-13 (shipped 2026-11-13) — [archive](milestones/v2.0-ROADMAP.md)

Next milestone: not yet defined. Run `/gsd-new-milestone`. Candidates are listed in PROJECT.md under Next Milestone Goals and in the Backlog below.

## Phases

<details>
<summary>✅ v1.0 Part Importer (Phases 1-7) — SHIPPED 2026-10-25</summary>

- [x] Phase 1: Foundation (6/6 plans) — completed 2026-10-18
- [x] Phase 2: Hardening Existing Code (9/9 plans) — completed 2026-10-19
- [x] Phase 3: Package Intake and Naming (10/10 plans) — completed 2026-10-19
- [x] Phase 4: Plan and Install Core (13/13 plans) — completed 2026-10-20
- [x] Phase 5: Import UI and Post-Install (11/11 plans) — completed 2026-10-22
- [x] Phase 6: Git Commit Step (8/8 plans) — completed 2026-10-23
- [x] Phase 7: SnapEDA and SamacSys Adapters (13/13 plans) — completed 2026-10-24

</details>

<details>
<summary>✅ v2.0 Atomic Libraries (Phases 8-13) — SHIPPED 2026-11-13</summary>

**Milestone Goal:** Every own part lives in an `Atomic_<KiCad stem>` library and is guaranteed atomic, whether it came through the importer or was made by hand. The existing parts are migrated in one clean commit, and the test suite no longer depends on the workstation.

- [x] Phase 8: Test Isolation and KiCad 10 (6/6 plans) — completed 2026-10-26
- [x] Phase 9: Atomic Rule Check and Scan Detection (9/9 plans) — completed 2026-10-26
- [x] Phase 10: Importer on the Atomic Scheme (30/30 plans) — completed 2026-10-29
- [x] Phase 11: Commit Gate and Commit Panel Fixes (17/17 plans) — completed 2026-11-01
- [x] Phase 12: Import Flow Fixes and Case-Sensitive Re-test (21/21 plans) — completed 2026-11-11
- [x] Phase 13: Atomic Migration and KiCad Setup (28/28 plans) — completed 2026-11-13

Quick task 261027-gg7 (saved scan reused at startup, Rescan this library) is archived in `milestones/v2.0-quick/`.

</details>

## Progress

| Milestone | Phases | Plans | Tasks | Shipped |
|-----------|--------|-------|-------|---------|
| v1.0 Part Importer | 1-7 | 70 | 148 | 2026-10-25 |
| v2.0 Atomic Libraries | 8-13 | 111 | 228 | 2026-11-13 |

## Backlog

Former backlog 999.1 is now VER-01 (Phase 8) and 999.2 is now VER-02 (Phase 12).

### Phase 999.3: Follow-up — Phase 12 deferred UAT follow-up: Test 3 (BACKLOG)

**Goal:** Resolve the UAT checkpoint deferred during Phase 12 verification
**Source phase:** 12
**Deferred at:** 2026-11-11 during /gsd-verify-work 12 session completion
**Follow-ups:**
- [ ] Test 3: KiCad-open question before the path-variable change (REV-05): re-test after the merge from the main checkout (not a worktree), changing CUSTOM_3DMODEL_DIR, with KiCad open; check Retry / Change anyway / Not now and that KiCad's other settings are kept. (deferred 2026-11-11)

### Phase 999.4: Follow-up — Phase 12 deferred UAT follow-up: Test 4 (BACKLOG)

**Goal:** Resolve the UAT checkpoint deferred during Phase 12 verification
**Source phase:** 12
**Deferred at:** 2026-11-11 during /gsd-verify-work 12 session completion
**Follow-ups:**
- [ ] Test 4: Window stays live during a real kicad-cli rebuild (REV-04): Finishing strip, slow note and Cancel with a real rebuild; too fast to catch by hand, covered by automated tests. (deferred 2026-11-11)

### Phase 999.1: Follow-up — Phase 13 deferred UAT follow-up: Test 4 (BACKLOG)

**Goal:** Resolve the UAT checkpoint deferred during Phase 13 verification
**Source phase:** 13
**Deferred at:** 2026-11-13 during /gsd-verify-work 13 session completion
**Follow-ups:**
- [ ] Test 4: Regroup the main-window menus (today everything but Help is under File). Decided 2026-11-13 with the owner: File = Import Part (Ctrl+I), Exit (Ctrl+Q); Libraries = Rescan Libraries (Ctrl+Shift+R), Select All / Deselect All, separator, Check Atomic Parts (Ctrl+Shift+A), Migrate to Atomic Libraries (Ctrl+Shift+M); KiCad = Generate Tables (Ctrl+G), Restore Backup (Ctrl+R), separator, Pin Atomic Libraries in KiCad (Ctrl+Shift+K), Set KiCad Footprint Path (Ctrl+K); Help unchanged. Menu is named Libraries (not Atomic Libraries) because Rescan and Select All also cover Wurth; Pin lives under KiCad because it edits KiCad config. Shortcuts unchanged; update the User Guide menu paths and CLAUDE.md Menu Shortcuts. (deferred 2026-11-13)
