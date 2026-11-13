# Milestones

## v2.0 Atomic Libraries (Shipped: 2026-11-13)

**Delivered:** Every own part now lives in an `Atomic_<official KiCad stem>` symbol library with one shared `Atomic_Footprints`, and is held to a blocking atomic rule (MPN, Manufacturer, a Footprint field resolving to exactly one `<Lib>:<FP>`, Value = MPN, Datasheet, Description, an existing 3D model) by the importer, every scan, the Check Atomic Parts dialog and the commit gate. The 21 existing parts were migrated into 10 `Atomic_` libraries in one previewed transaction on 2026-11-12, KiCad 10's chooser pins them with MPN and Manufacturer columns, and the test suite runs on synthetic fixtures against KiCad 10 instead of the owner's live `Custom/`.

**Phases completed:** 6 phases (8–13), 111 plans, 228 tasks, plus quick task 261027-gg7
**Timeline:** 20 days (2026-10-25 → 2026-11-13), 918 commits
**Code:** 164 files changed outside `.planning/` (+48,439 / −3,091); about 30.6k lines of application Python and 59.3k lines of tests (9689 passing, 4 documented skips, about 30 min per full run)
**Requirements:** 40/40 v2.0 requirements complete
**Archive:** [v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md) · [v2.0-REQUIREMENTS.md](milestones/v2.0-REQUIREMENTS.md) · [v2.0-phases/](milestones/v2.0-phases/) · [v2.0-quick/](milestones/v2.0-quick/)

**Key accomplishments:**
- Test isolation: code-built synthetic `Custom/` fixtures, a session guard that fails any run touching the live `Custom/`, and one cached kicad-cli 10 gate; bare `pytest` is green with no `Custom/` at all, and the D-01 re-test passed on KiCad 10 (Phase 8)
- One Qt-free atomic rule check and one canonical manufacturer table, run on every scan: failing parts marked per rule in the tree, New/Changed parts detected against the `Custom` HEAD, and a Check Atomic Parts dialog that previews and applies only safe fixes with backups and rollback (Phase 9)
- Importer on the atomic scheme: `Atomic_<stem>` suggested by a KiCad sibling vote or the category map (else it asks), footprints into the shared `Atomic_Footprints` or an official KiCad footprint, generated keywords, footprint descriptions and tags, and Install blocked with clickable reasons until the part is atomic (Phase 10)
- Commit gate that fails closed on any non-atomic committed part, and a commit panel that reports what git really did, keeps its state across re-probes, quotes the manual command for PowerShell and passes the git identity through (Phase 11)
- Import-flow fixes: the five open Phase 5 review findings closed, the KiCad-open question before a path-variable write, theme tokens in Help and conflict rows, the case-sensitive re-test, Cancel on every import page, Skip while libraries load, and one shared User Guide window that reopens on the chosen section (Phase 12)
- One-transaction migration (`pre-atomic` tag, dirty-`Custom` refusal, per-part preview with a failure strip and saved draft, rollback, old → new map in `Custom/MIGRATION-ATOMIC.md`), table descriptions, Pin Atomic Libraries in KiCad, and the D-26 wrong-checkout guard; live run 2026-11-12 moved 21 parts into 10 libraries with zero violations (Phase 13)
- The last scan is saved beside `settings.ini` and reused at startup when nothing changed, with a right-click Rescan this library (quick 261027-gg7)

**Closeout:** override_closeout. No milestone audit was run (owner chose to close without one, as for v1.0). The Phase 8–12 VERIFICATION.md reports read `passed` but are flagged stale: gap-closure plans and UAT files were committed in those phase folders after each verifier ran. Each phase's UAT passed after its gap plans (Phase 9: 3/3 on 2026-10-26; Phase 10: 16 checks on 2026-10-29; Phase 11: 3/3 on 2026-11-01; Phase 12: 28 checks on 2026-11-11). Phase 13 was verified as passed on the final code on 2026-11-13, with 81/81 threats closed at ASVS L1 and a 16/24 advisory UI review.
**Known verification overrides:** 1 newly acknowledged (todo: speed up the full test suite), 0 carried forward from a prior close (see STATE.md Deferred Items). The 8 diagnose-only debug sessions open at close (G-10-1, G-10-11, G-12-27, G-13-1-a/b/c/f/g) were resolved against the plans that fixed them (10-29, 10-30, 12-21, 13-23..13-28), not deferred; the completed quick task 261027-gg7 was archived into `milestones/v2.0-quick/`.

### Known Gaps

- The full `pytest` run takes about 30 minutes (9689 tests). Deferred todo with an agreed plan: measure with `--durations`, parallelise with pytest-xdist, add a `slow` marker, share the expensive git fixtures (`todos/pending/2026-11-13-speed-up-full-test-suite.md`).
- Backlog 999.1: regroup the main-window menus into File / Libraries / KiCad / Help (owner decision 2026-11-13).
- Backlog 999.3 and 999.4: live re-tests of the KiCad-open question (REV-05) from the main checkout and of the Finishing strip during a real kicad-cli rebuild (REV-04). Both are covered by automated tests.
- Open non-blocking review findings: Phase 10 (WR-01, WR-03, WR-04, IN-01..IN-06), Phase 11 (WR-01, IN-01..IN-03), Phase 12 (12-REVIEW-DISPOSITION.md), and the Phase 13 UI review's advisory items (accessible names on icon-only controls, User Guide wording, spacing of the new windows never rendered). See the REVIEW-DISPOSITION and UI-REVIEW files in `milestones/v2.0-phases/`.
- Phase 10 follow-up kept in 10-UAT.md: a log panel inside the import dialog for debugging.
- Carried from v1.0 and still open: Phase 4 WR-04 (split `build_plan`, deferred as REF-01), Phase 4 IN-01/02/03/05 and Phase 5 IN-01..IN-06.

---

## v1.0 Part Importer (Shipped: 2026-10-25)

**Delivered:** A vendor package from Ultra Librarian, SnapEDA, SamacSys/CSE or a folder of loose files is imported into `Custom/` through an editable preview. It is installed as one transaction with the Footprint field linked as `<Lib>:<FP>` and the 3D model as `${CUSTOM_3DMODEL_DIR}/<file>`, then the library tables are refreshed and the part is committed after confirmation, without hand-editing any KiCad file.

**Phases completed:** 7 phases (1–7), 70 plans, 148 tasks
**Timeline:** 7 days (2026-10-18 → 2026-10-24), 619 commits
**Code:** 134 files changed outside `.planning/` (+43,946 / −611); about 15.2k lines of application Python and 29.5k lines of tests
**Requirements:** 54/54 v1 requirements complete (FMT2-02 moved into v1 during Phase 7)
**Archive:** [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) · [v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md) · [v1.0-phases/](milestones/v1.0-phases/)

**Key accomplishments:**
- Lossless span-splicing S-expression layer plus atomic writes and numbered backups: every repo `.kicad_sym`, `.kicad_mod` and lib table round-trips byte-identically, and an edit changes only its span (Phase 1)
- Existing app hardened on that layer: managed-only lib-table splicing that keeps hand-made entries, nickname-collision handling, numeric KiCad version choice, and a backed-up, confirmed `kicad_common.json` sync (Phase 2)
- Safe headless intake of zips and loose folders (zip slip, bombs, corrupt members and hostile text all bounded), vendor adapters for UL, SnapEDA and SamacSys, and `<Type>_<SubCategory>_<Manufacturer>` name suggestion (Phases 3, 7)
- Transactional install: format matching through kicad-cli, extends-aware renames, per-item conflicts, model linking, rollback on any exception, post-install verification and a no-op second import (Phase 4)
- Import Part dialog with an editable preview that is exactly what gets installed, per-conflict Overwrite/Rename/Skip, drag and drop, separate 3D model attach, and add-only table refresh (Phases 5, 7)
- Confirmed commit step: path-limited `commit --only` of the installed files in `Custom`, then the gitlink in the parent, from an allow-listed git runner that never pushes (Phase 6)

**Closeout:** override_closeout. No milestone audit was run (owner chose to close without one). Phase 1–6 verification reports are stale because later phases changed files they covered. Phase 7 was verified as passed on the final code.
**Known verification overrides:** 0 newly acknowledged, 0 carried forward. The 5 open artifacts found at close (4 diagnose-only debug sessions, Phase 03 UAT decisions CR-01/CR-02) were resolved against the plans that fixed them, not deferred.

### Known Gaps

- 21 of 1993 tests fail on the current workstation. The cause is the environment, not the code:
  - 14 copy the live `Custom/` tree and assume the UL sample part is absent. `Custom` commit `eecac22` (2026-10-23) added CSD85301Q2, and with `Custom` at the commit before it these tests pass.
  - 7 real kicad-cli tests expect KiCad 9 output (format 20241209). KiCad 10 is now installed and writes 20251024. The owner no longer targets KiCad 9 (2026-10-25), so these tests need retargeting.
- Backlog 999.1 (re-test D-01 on KiCad 10) and 999.2 (case-twin rollback on a case-sensitive folder) remain open.
- Open non-blocking review findings: Phase 5 WR-01..WR-06 and Phase 6 WR-01..WR-05 / IN-01..IN-03 (see the REVIEW-DISPOSITION files in `milestones/v1.0-phases/`), plus the Help dialog and Commit panel styling items from the UI reviews.

---
