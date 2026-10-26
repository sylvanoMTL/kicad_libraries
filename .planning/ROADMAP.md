# Roadmap: KiCad Part Importer

## Milestones

- ✅ **v1.0 Part Importer** — Phases 1-7 (shipped 2026-10-25) — [archive](milestones/v1.0-ROADMAP.md)
- 🚧 **v2.0 Atomic Libraries** — Phases 8-13 (in progress)

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

### 🚧 v2.0 Atomic Libraries (In Progress)

**Milestone Goal:** Every own part lives in an `Atomic_<KiCad stem>` library and is guaranteed atomic, whether it came through the importer or was made by hand. The existing parts are migrated in one clean commit, and the test suite no longer depends on the workstation.

Phase 8 makes the suite green first, so every later phase starts from a baseline it can trust. Phase 9 builds the shared atomic rule check and the canonical manufacturer table, with the scan as their first user. Phase 10 moves the importer onto the `Atomic_` scheme and gates Install on the check, so new imports cannot bring the old names back before the migration. Phase 11 adds the atomic commit gate next to the open commit-panel fixes, because they touch the same panel. Phase 12 holds the remaining v1.0 import-flow fixes and the case-sensitive re-test. It depends only on Phase 8 and gates nothing in the atomic chain, but it is placed before Phase 13 so the chooser setup reuses the corrected `kicad_common.json` write (REV-05). Phase 13 migrates the existing parts last, because it uses the check, the metadata generation, the table generator and the commit step.

- [x] **Phase 8: Test Isolation and KiCad 10** - Tests build their own synthetic `Custom/`, kicad-cli tests expect KiCad 10, the deferred D-01 re-test passes, and `pytest` is green on the workstation (completed 2026-10-26)
- [x] **Phase 9: Atomic Rule Check and Scan Detection** - One atomic rule check and one canonical manufacturer table, run on every scan, with tree marks, changed-part highlights and a check dialog of safe fixes (completed 2026-10-26)
- [ ] **Phase 10: Importer on the Atomic Scheme** - Importer suggests `Atomic_<stem>`, installs footprints into `Atomic_Footprints`, generates keywords and footprint tags, and blocks Install until the part is atomic
- [ ] **Phase 11: Commit Gate and Commit Panel Fixes** - Commit panel refuses non-atomic parts, reports what git really did, and follows the theme
- [ ] **Phase 12: Import Flow Fixes and Case-Sensitive Re-test** - Post-install table step, import threading, `kicad_common.json` write and Help dialog fixed; case-twin rollback re-tested
- [ ] **Phase 13: Atomic Migration and KiCad Setup** - Existing parts migrated into 9 `Atomic_` libraries in one previewed commit, tables regenerated with descriptions, KiCad's chooser set up, docs updated

## Phase Details

### Phase 8: Test Isolation and KiCad 10

**Goal**: The developer can trust the test suite again. It passes on the workstation whatever parts `Custom/` holds, KiCad 10 is the only kicad-cli target, and the deferred KiCad 10 install check is closed.
**Depends on**: Nothing (first v2.0 phase; v1.0 is shipped)
**Requirements**: TEST-01, TEST-02, TEST-03, VER-01
**Success Criteria** (what must be TRUE):
  1. Adding or removing a part in the live `Custom/` (for example CSD85301Q2, added in `Custom` commit `eecac22`) changes no test result. The 14 tests that copied the live tree build an isolated synthetic `Custom/` instead, and pass.
  2. The real kicad-cli tests expect KiCad 10 output (symbol format 20251024) and pass with the installed kicad-cli 10. Where kicad-cli 10 is absent, they skip with a stated reason instead of failing.
  3. Running bare `pytest` from the repo root on the workstation reports 0 failures, and every skip carries a documented reason.
  4. On KiCad 10, installing into an existing `Custom/` library in the KiCad 9 format (20241209) installs the symbol as-is with the D-01 warning and leaves the library's format version unchanged, as the deferred Phase 4 UAT Test 2 (backlog 999.1) expected.

**Plans:** 6/6 plans complete

Plans:
**Wave 1**
- [x] 08-01-PLAN.md — KiCad 10 gate for real kicad-cli tests, 20251024 builder style, test_kicad_cli retargeted (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 08-02-PLAN.md — Synthetic format-mirror Custom/ fixture and the live-Custom/ write-protect guard (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 08-03-PLAN.md — Dialog, preview, install-apply and ranking tests moved to the synthetic Custom/ (wave 3)
- [x] 08-04-PLAN.md — VER-01 as-is row on KiCad 10, KiCad 10 scenario rows, UAT hook retargeted in test_install_e2e (wave 3)
- [x] 08-05-PLAN.md — test_install_plan real-CLI tests on KiCad 10 and the shared gate, synthetic Custom/ (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 08-06-PLAN.md — Live-copy fixture removed, WurthElektronik checkout and budget, tests/README.md, green full suite, D-10 records (wave 4)

### Phase 9: Atomic Rule Check and Scan Detection

**Goal**: Every part in an `Atomic_` library is held to the atomic rule on every scan, so a broken or hand-made part is flagged, explained and, where it is safe, fixed in one click
**Depends on**: Phase 8
**Requirements**: ATOM-01, ATOM-02, ATOM-03, FLD-02, SCAN-01, SCAN-02, SCAN-03
**Success Criteria** (what must be TRUE):
  1. After a scan, each symbol in an `Atomic_` library that breaks a rule is marked in the library tree. Its tooltip names each broken rule in plain language, and the log has one line per failure. The rules are: MPN present, Manufacturer present, the Footprint field resolving to exactly one existing `<Lib>:<FP>`, Value equal to MPN, a Datasheet that is not empty or `~`, a Description, and a linked footprint whose 3D model file exists.
  2. A derived (`extends`) symbol is judged on its own fields and is flagged when it has no MPN of its own, even if its parent has one. Symbols in Würth or any other library without the `Atomic_` prefix are never flagged.
  3. A symbol added or changed in KiCad since the last `Custom` commit is highlighted in the tree on the next scan, so a part made by hand is noticed.
  4. The check dialog lists every violation. It offers one-click fixes only for Value := MPN, `MF`/`MP` → `Manufacturer`/`MPN`, canonical manufacturer spelling and removing price and stock leftovers. Each fix is previewed, written with a backup, and gone on the next scan. A missing Datasheet, Description or 3D model can be filled in the dialog, or it stays a reported error.
  5. A Manufacturer written as an alias is reported with its canonical name from the one manufacturer table (a name plus its aliases), and the fix writes that canonical name.

**Plans:** 9/9 plans complete

Plans:
**Wave 1**
- [x] 09-01-PLAN.md — Canonical manufacturer table as a Qt-free leaf, suggest.MANUFACTURER_ALIASES derived from it (wave 1)
- [x] 09-02-PLAN.md — Scan result contract in models.py and library-tree marks, New/Changed highlights, auto-expand, double-click signal (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 09-03-PLAN.md — Atomic check on every scan: MPN, Manufacturer, Value, Datasheet, Description, derived symbols, safe-fix specs, log lines (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 09-04-PLAN.md — Footprint and 3D model rules through an injected resolver context, official KiCad footprints included (wave 3)
- [x] 09-05-PLAN.md — Changed-since-last-Custom-commit detection by token stream, symbols and footprints (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 09-06-PLAN.md — Qt-free fix engine: preview, stale check, backup, atomic write, rollback, 3D model intake (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 09-07-PLAN.md — Check Atomic Parts dialog (Ctrl+Shift+A, double-click), fill-ins, preview and apply, rescan (wave 5)
- [x] 09-08-PLAN.md — D-25 UAT scratch repo builder, tests/README.md skip row, end-of-phase checklist (wave 5)

**Wave 6** *(gap closure: UAT G-09-1)*
- [x] 09-09-PLAN.md — Library tree component level: one row per problem and note under each collapsed symbol, double-click to the check; UAT helper no longer needs a Datasheet field (wave 6)

**UI hint**: yes

### Phase 10: Importer on the Atomic Scheme

**Goal**: A part imported from any supported vendor package lands in the right `Atomic_<stem>` library, with its footprint in the shared `Atomic_Footprints`, and only once it passes the atomic rule, so new imports never bring back the old names
**Depends on**: Phase 9
**Requirements**: LIB-04, LIB-05, LIB-06, LIB-07, FLD-01, FLD-03
**Success Criteria** (what must be TRUE):
  1. Opening `ul_CSD85301Q2.zip` suggests `Atomic_Transistor_FET`, from the `CSD` family in KiCad's installed libraries. The SamacSys RECOM RS3-1212S/H3 sample has no sibling there, so it gets `Atomic_Converter_DCDC_Isolated` from the category map. When neither step can place a part, the importer asks. No suggestion contains a manufacturer name.
  2. The user can pick an existing `Atomic_` library or type a new name. A name equal to an official KiCad library (for example `Transistor_FET`), or one that uses a manufacturer as its token (for example `Atomic_TI`), is refused and the reason is shown.
  3. The footprint installs into the shared `Atomic_Footprints.pretty`, or into an official KiCad footprint the user picks instead. The symbol's Footprint field then reads `Atomic_Footprints:<FP>` or that official `<Lib>:<FP>`. Creating a new symbol library no longer creates a matching `.pretty`.
  4. Install stays disabled while the incoming part fails the atomic check. Each failure is a clickable reason that jumps to its field. Value defaults to the MPN, and filling in Datasheet, Description or the 3D model in the preview clears the matching reason.
  5. The preview shows generated `ki_keywords` (function words, interfaces, package codes, manufacturer aliases, MPN variants) and a footprint description and tags (package, IPC name, vendor package code, pitch). All of them are editable, and the installed files carry exactly what the preview showed.

**Plans**: TBD
**UI hint**: yes

### Phase 11: Commit Gate and Commit Panel Fixes

**Goal**: The commit step never commits a part that breaks the atomic rule, and the commit panel always shows what git actually did, with the open v1.0 review and UI findings closed
**Depends on**: Phase 9
**Requirements**: GIT-06, REV-06, REV-07, REV-08, REV-09, REV-10, REV-11, UI-02
**Success Criteria** (what must be TRUE):
  1. While any part being committed fails the atomic check, the commit panel refuses, names the part and the broken rule, and commits nothing.
  2. After a commit timeout, the panel checks HEAD and reports what was actually committed instead of "nothing committed". Files identical to HEAD no longer raise a spurious "missing" error. After a precheck refusal, the panel probes again instead of showing a stale "ready".
  3. The parent-message preview is exactly the committed text, also when there is no previous gitlink. On Windows, the "finish it by hand" command uses Windows quoting, so a subject containing quotes or `$` runs as shown when pasted.
  4. The parent checkbox keeps the user's choice across probes. The dialog and the main window can be closed while the read-only probe runs. A user whose git identity comes from `GIT_AUTHOR_*` / `GIT_COMMITTER_*` variables can commit from the panel.
  5. The Commit button is styled as the primary action, error and success outcomes are tinted, the parent-failed state is no longer labelled "Committed", and the panel's sizes come from the theme scale.

**Plans**: TBD
**UI hint**: yes

### Phase 12: Import Flow Fixes and Case-Sensitive Re-test

**Goal**: The import dialog, the post-install table step and the `kicad_common.json` write behave correctly in the cases the v1.0 reviews left open. The Help dialog follows the theme, and case-twin rollback is proven on a case-sensitive folder.
**Depends on**: Phase 8
**Requirements**: REV-01, REV-02, REV-03, REV-04, REV-05, UI-01, VER-02
**Success Criteria** (what must be TRUE):
  1. After install, the table step says "already listed" only when the managed entry really points at that library. With an empty Destination, it writes no table at all, and never one in the process working directory.
  2. A one-off conflict build can never run while Install runs, and the window stays responsive while kicad-cli works, with no GUI wait of up to 60 s.
  3. When KiCad is running, the confirm dialog for a `kicad_common.json` change says so before anything is written. The confirmed write starts from the file's current content, so settings KiCad saved while the dialog was open are not lost.
  4. The Help dialog and the conflict rows use theme tokens only, with no hard-coded colours, `#FFFFFF` literals or px font sizes.
  5. On a case-sensitive folder, when a case twin was written under another spelling, rollback restores the original spelling and removes the twin on both the rollback and the overwrite branches, as the deferred Phase 4 UAT Test 3 (backlog 999.2) expected.

**Plans**: TBD
**UI hint**: yes

### Phase 13: Atomic Migration and KiCad Setup

**Goal**: All existing `Custom/` parts move to the `Atomic_` scheme in one previewed, reversible commit, with every part passing the atomic rule, and KiCad's library list and chooser show the new libraries
**Depends on**: Phase 9, Phase 10, Phase 11
**Requirements**: MIG-01, MIG-02, MIG-03, MIG-04, MIG-05, TBL-01, TBL-02, DOC-01
**Success Criteria** (what must be TRUE):
  1. The migration refuses to start while `Custom` has uncommitted changes, and otherwise tags `Custom` as `pre-atomic` before it writes anything. Its preview shows, for every existing part, the target `Atomic_` library, the footprint destination, every rename and field change, and every atomic-rule failure with an edit box. Run stays disabled until every part passes.
  2. Running it as one transaction, which rolls back on any failure, leaves 9 `Atomic_` symbol libraries in place of the 12 old ones. Every footprint is in `Atomic_Footprints` or switched to an official footprint, every Footprint field and model path is rewritten, and the two `.bak` files are gone. The next scan reports zero atomic violations.
  3. The regenerated library tables drop the old names and add the new ones. Every generated table entry, from Generate or from the migration, carries a library description instead of an empty one. One `Custom` commit plus a parent ref commit is offered through the commit step.
  4. One confirmed action sets up KiCad 10's chooser: it pins the `Atomic_` libraries, shows the `MPN` and `Manufacturer` columns and removes the stray `MANUFACTURER` column. Like the path-variable sync, it shows old → new values first, backs up the config, and refuses to run from a worktree or another checkout.
  5. The app shows and saves the old → new library name map with the KiCad steps to relink existing projects (Edit Symbol Library Links → Update Symbols → Update PCB). `CLAUDE.md`, PROJECT.md and `research/LIBRARY-NAMING.md` describe the `Atomic_` scheme and the atomic rule.

**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 8 → 9 → 10 → 11 → 12 → 13

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 8. Test Isolation and KiCad 10 | v2.0 | 6/6 | Complete    | 2026-10-26 |
| 9. Atomic Rule Check and Scan Detection | v2.0 | 9/9 | Complete    | 2026-10-26 |
| 10. Importer on the Atomic Scheme | v2.0 | 0/TBD | Not started | - |
| 11. Commit Gate and Commit Panel Fixes | v2.0 | 0/TBD | Not started | - |
| 12. Import Flow Fixes and Case-Sensitive Re-test | v2.0 | 0/TBD | Not started | - |
| 13. Atomic Migration and KiCad Setup | v2.0 | 0/TBD | Not started | - |

## Backlog

No open items. Former backlog 999.1 is now VER-01 (Phase 8) and 999.2 is now VER-02 (Phase 12).
