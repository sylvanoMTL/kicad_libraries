# Milestones

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
