# Requirements: KiCad Part Importer

**Defined:** 2026-10-25 (milestone v2.0 Atomic Libraries)
**Core Value:** A downloaded vendor package ends up as a correctly named, correctly linked part in the right `Custom/` library, with the symbol's Footprint field pointing at `<Lib>:<FP>` and the 3D model at `${CUSTOM_3DMODEL_DIR}/<file>.step`, without hand-editing any KiCad file.

v1.0 requirements (FOUND, HARD, INTK, FMT2-02, LIB-01..03, PREV, INST, POST, GIT-01..05, UX) are archived in `milestones/v1.0-REQUIREMENTS.md`. IDs below continue those categories where they fit.

**Naming scheme (owner, 2026-10-25):** own symbol libraries are `Atomic_<official KiCad symbol-library stem>` (e.g. `Atomic_Connector`, `Atomic_Transistor_FET`), and footprints live in one shared `Atomic_Footprints.pretty`. Parts are filed by what the device is. Every part in an `Atomic_` library is a real, orderable part. Research: `research/LIBRARY-NAMING.md`; its `_MecaFrog` suffix is superseded by the `Atomic_` prefix.

## v2.0 Requirements

### Tests

- [x] **TEST-01**: The test suite passes whatever parts the owner's `Custom/` holds. Tests that need a target library build an isolated synthetic `Custom/` instead of copying the live one.
- [x] **TEST-02**: The real kicad-cli tests expect KiCad 10 output (symbol format 20251024), and skip with a stated reason when kicad-cli 10 is absent.
- [x] **TEST-03**: Developer runs `pytest` on the workstation and gets 0 failures, with only documented skips.

### Atomic Rule

- [ ] **ATOM-01**: For every symbol in an `Atomic_` library, the check reports each broken rule in plain language. The rules are:
  - MPN present;
  - Manufacturer present;
  - the Footprint field resolves to exactly one existing `<Lib>:<FP>`;
  - Value = MPN;
  - Datasheet present (not empty or `~`);
  - Description present;
  - the linked footprint references a 3D model file that exists.
- [ ] **ATOM-02**: Derived symbols (`extends`) are checked on their own fields, and each needs its own MPN.
- [ ] **ATOM-03**: Every rule is blocking for `Atomic_` libraries. Libraries without the `Atomic_` prefix (Würth, anything else) are not checked.

### Library Naming

- [ ] **LIB-04**: The importer suggests `Atomic_<official KiCad library stem>` from what the device is:
  1. a sibling family or MPN prefix in KiCad's installed libraries;
  2. otherwise, a category map that includes vendor and distributor categories;
  3. otherwise, it asks.

  A manufacturer name is never part of the suggestion.
- [ ] **LIB-05**: User can pick an existing `Atomic_` library or type a new one. A name equal to an official KiCad library name, or one using a manufacturer name as the token, is refused.
- [ ] **LIB-06**: Footprints install into the shared `Atomic_Footprints.pretty`, or into an official KiCad footprint the user picks instead. The symbol's Footprint field reads `Atomic_Footprints:<FP>`. A new symbol library no longer creates a matching `.pretty`, because the 1:1 pairing of LIB-02 is dropped.
- [ ] **LIB-07**: Install into an `Atomic_` library is blocked until the incoming part passes the atomic check. Each failure is a clickable reason that jumps to its field. Value defaults to the MPN, and Datasheet, Description and 3D model are editable in the preview.

### Scan Detection

- [ ] **SCAN-01**: Every scan runs the atomic check on all `Atomic_` libraries. Failing symbols are marked in the library tree with a tooltip, with one log line per failure.
- [ ] **SCAN-02**: Symbols added or changed since the last `Custom` commit are highlighted, so a part made by hand in KiCad is noticed.
- [ ] **SCAN-03**: A check dialog lists every violation and offers one-click fixes only where they're safe:
  - Value := MPN;
  - `MF`/`MP` → `Manufacturer`/`MPN`;
  - canonical manufacturer spelling;
  - removing price and stock leftovers.

  Each fix is previewed and written safely with a backup. A missing datasheet, description or model can be filled in the dialog, or stays a reported error.

### Part Metadata

- [ ] **FLD-01**: The importer and the migration generate `ki_keywords`: function words, interfaces, package codes, manufacturer aliases and MPN variants. They're editable in the preview.
- [ ] **FLD-02**: One canonical manufacturer table (a name plus its aliases) is used by the importer, the check and the migration. An alias is reported and fixable.
- [ ] **FLD-03**: Footprints written by the importer or the migration get a description and tags: package, IPC name, vendor package code and pitch.

### Library Tables and KiCad Setup

- [ ] **TBL-01**: Generated `sym-lib-table` / `fp-lib-table` entries carry a library description instead of an empty one.
- [ ] **TBL-02**: One confirmed action sets up KiCad 10's chooser:
  - pins the `Atomic_` libraries;
  - shows the `MPN` and `Manufacturer` columns and removes the stray `MANUFACTURER` column;
  - shows old → new values first, backs up the config, and refuses to run from a worktree or another checkout, like the path-variable sync.

### Migration

- [ ] **MIG-01**: Before migrating, the app tags `Custom` as `pre-atomic`, and refuses to start while `Custom` has uncommitted changes.
- [ ] **MIG-02**: The migration preview shows, for every existing part, its target `Atomic_` library, its footprint destination, every rename and field change, and every atomic-rule failure with an edit box. The migration cannot run until every part passes.
- [ ] **MIG-03**: The migration runs as one transaction with rollback, using byte-safe span edits. It:
  - merges the 12 symbol libraries into 9 `Atomic_` libraries;
  - moves every footprint into `Atomic_Footprints`, or switches it to an official footprint;
  - rewrites every Footprint field and model path;
  - deletes the two `.bak` files.
- [ ] **MIG-04**: After migration, the scan reports zero atomic violations, and the library tables are regenerated (old names removed, new ones added). One `Custom` commit plus a parent ref commit is offered through the commit step.
- [ ] **MIG-05**: The app shows and saves the old → new library name map, plus the KiCad steps to relink existing projects (Edit Symbol Library Links → Update Symbols → Update PCB).

### Git

- [ ] **GIT-06**: The commit panel refuses while any part being committed fails the atomic check, naming the part and the rule.

### Re-tests

- [x] **VER-01**: The D-01 "install as-is with warning" case is re-tested on KiCad 10 (backlog 999.1).
- [ ] **VER-02**: Case-twin rollback and overwrite are re-tested on a case-sensitive folder (backlog 999.2).

### v1.0 Review Fixes

- [ ] **REV-01**: The post-install table step only says "already listed" when the managed entry really points at that library (Phase 5 WR-01).
- [ ] **REV-02**: The post-install table write never goes to the process working directory when Destination is empty (Phase 5 WR-02).
- [ ] **REV-03**: A one-off conflict build can never overlap Install (Phase 5 WR-03).
- [ ] **REV-04**: The GUI thread never blocks waiting for a kicad-cli call (Phase 5 WR-05).
- [ ] **REV-05**: The `kicad_common.json` write uses fresh content after the confirm dialog, and the KiCad-running check gates it (Phase 5 WR-06).
- [ ] **REV-06**: A commit timeout checks HEAD before reporting "nothing committed" (Phase 6 WR-01).
- [ ] **REV-07**: The parent-message preview matches the committed text when there's no previous gitlink (Phase 6 WR-02).
- [ ] **REV-08**: The "finish it by hand" command uses Windows quoting on Windows (Phase 6 WR-03).
- [ ] **REV-09**: Files identical to HEAD no longer raise a spurious "missing" error (Phase 6 WR-04).
- [ ] **REV-10**: After a precheck refusal, the commit panel re-probes instead of showing a stale "ready" (Phase 6 WR-05).
- [ ] **REV-11**: The parent checkbox keeps the user's choice across probes, the dialog and main window can close during the read-only probe, and `run_git` keeps identity-related `GIT_*` variables (Phase 6 IN-01..IN-03).

### UI Polish

- [ ] **UI-01**: The Help dialog and the conflict rows use theme tokens only, with no hard-coded colours, `#FFFFFF` literals or px font sizes (05-UI-REVIEW).
- [ ] **UI-02**: The Commit button is styled as the primary action, error and success outcomes are tinted, the parent-failed state is not labelled "Committed", and `commit_panel.py` sizes are on the theme scale (06-UI-REVIEW).

### Docs

- [ ] **DOC-01**: `CLAUDE.md` (naming section and SnapEDA import steps), PROJECT.md and `research/LIBRARY-NAMING.md` describe the `Atomic_` scheme and the atomic rule.

## Future Requirements

Deferred. Tracked but not in the current roadmap.

- **PREV2-01**: SVG preview of symbol and footprint via `kicad-cli export svg`
- **FMT2-01**: Convert legacy KiCad 5 `.lib` / `.dcm` / `.mod` packages instead of rejecting them
- **META2-01**: Hidden provenance property on imported symbols
- **PAD-01**: Pad-1 orientation check of a footprint against the datasheet top view
- **REF-01**: Split `build_plan` (about 531 lines) into smaller units (Phase 4 WR-04)
- **DBL-01**: Database libraries (`.kicad_dbl`) for atomic passives at scale

## Out of Scope

| Feature | Reason |
|---------|--------|
| Brand or manufacturer token in library names | The owner chose the `Atomic_` prefix (2026-10-25); manufacturer tokens split same-function parts |
| Bare KiCad stems with no token | KiCad 10 ships libraries under every target stem, so the names would clash |
| Generic symbols in `Atomic_` libraries | Every `Atomic_` part is a real, orderable part (atomic rule) |
| KiCad 10 nested library tables | Flattened in the chooser, duplicates silently shadowed, unreadable by KiCad 9 and earlier |
| HTTP or database libraries | Need a server or ODBC driver; not worth it for a single-user repo now |
| Renaming third-party (Würth) libraries | Upstream-owned; names and layout stay untouched |
| Editing the owner's KiCad projects to relink them | KiCad's own Edit Symbol Library Links / Update Symbols / Update PCB tools do this; the app only provides the map and the steps |
| Fixes applied without a preview | Preview before every write stays a project constraint |
| Downloading parts, pushing to remotes, batch imports | Unchanged from v1.0 |

## Traceability

Which phases cover which requirements. Filled in during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TEST-01 | Phase 8 | Complete |
| TEST-02 | Phase 8 | Complete |
| TEST-03 | Phase 8 | Complete |
| ATOM-01 | Phase 9 | Pending |
| ATOM-02 | Phase 9 | Pending |
| ATOM-03 | Phase 9 | Pending |
| LIB-04 | Phase 10 | Pending |
| LIB-05 | Phase 10 | Pending |
| LIB-06 | Phase 10 | Pending |
| LIB-07 | Phase 10 | Pending |
| SCAN-01 | Phase 9 | Pending |
| SCAN-02 | Phase 9 | Pending |
| SCAN-03 | Phase 9 | Pending |
| FLD-01 | Phase 10 | Pending |
| FLD-02 | Phase 9 | Pending |
| FLD-03 | Phase 10 | Pending |
| TBL-01 | Phase 13 | Pending |
| TBL-02 | Phase 13 | Pending |
| MIG-01 | Phase 13 | Pending |
| MIG-02 | Phase 13 | Pending |
| MIG-03 | Phase 13 | Pending |
| MIG-04 | Phase 13 | Pending |
| MIG-05 | Phase 13 | Pending |
| GIT-06 | Phase 11 | Pending |
| VER-01 | Phase 8 | Complete |
| VER-02 | Phase 12 | Pending |
| REV-01 | Phase 12 | Pending |
| REV-02 | Phase 12 | Pending |
| REV-03 | Phase 12 | Pending |
| REV-04 | Phase 12 | Pending |
| REV-05 | Phase 12 | Pending |
| REV-06 | Phase 11 | Pending |
| REV-07 | Phase 11 | Pending |
| REV-08 | Phase 11 | Pending |
| REV-09 | Phase 11 | Pending |
| REV-10 | Phase 11 | Pending |
| REV-11 | Phase 11 | Pending |
| UI-01 | Phase 12 | Pending |
| UI-02 | Phase 11 | Pending |
| DOC-01 | Phase 13 | Pending |

**Coverage:**
- v2.0 requirements: 40 total
- Mapped to phases: 40
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-25*
*Last updated: 2026-10-25 after v2.0 roadmap creation (Phases 8-13)*
