# Roadmap: KiCad Part Importer

## Overview

The importer is built bottom-up on a shared foundation. First comes a headless test harness, atomic file writes and a lossless S-expression layer that edits by span and never re-serialises a file. The existing table, scanner and config code is then hardened on that layer, because the importer reuses it and it has known data-loss defects. Next, headless package intake and naming turn a vendor zip or loose-file folder into a candidate part with a convention-following library name. The headless plan/install core is where correctness lives: it is proven end to end against the real Ultra Librarian sample on a copy of `Custom/`. The import dialog and post-install flow wrap that core in the Library Manager GUI, and a confirmed git commit closes the loop. SnapEDA and SamacSys/CSE adapters follow once real downloads are in `downloaded_examples/`.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - Pinned dependencies, headless pytest harness, atomic writes and a lossless S-expression layer (completed 2026-10-18)
- [x] **Phase 2: Hardening Existing Code** - Table generation, KiCad detection, scanning and config writes made safe on the new foundation (completed 2026-10-19)
- [ ] **Phase 3: Package Intake and Naming** - Headless, safe reading of Ultra Librarian and loose-file packages, plus library name suggestion and sanitisation
- [ ] **Phase 4: Plan and Install Core** - Headless, transactional install of a part into `Custom/` with linking, rollback and verification
- [ ] **Phase 5: Import UI and Post-Install** - Import dialog with an editable preview, per-item conflict resolution, rescan and table refresh
- [ ] **Phase 6: Git Commit Step** - Confirmed commit of exactly the imported files in `Custom/` plus the parent ref bump, never pushing
- [ ] **Phase 7: SnapEDA and SamacSys Adapters** - Remaining vendor formats, gated on real downloads in `downloaded_examples/`

## Phase Details

### Phase 1: Foundation

**Goal**: The developer has a headless test harness and a shared S-expression and file-writing layer that provably never damages bytes it was not asked to change
**Depends on**: Nothing (first phase)
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05
**Success Criteria** (what must be TRUE):
  1. In a fresh venv, `pip install -r requirements-dev.txt` installs pinned PySide6, pytest and pytest-qt, and `pytest` passes with no display attached, including at least one Qt widget test running offscreen
  2. Every `.kicad_sym`, `.kicad_mod`, `sym-lib-table` and `fp-lib-table` file in the repo (all of `Custom/`, plus WurthElektronik when checked out) parses and re-serialises byte-identically when no edits are applied
  3. A targeted edit, such as changing one property value, changes only that span. The rest of the file stays byte-identical and its CRLF or LF line endings are kept.
  4. Writing over a locked or read-only file logs an error and leaves the original content intact, with no crash and no truncated file. A successful write replaces the file in one step (temp file + replace).

**Plans**: 6/6 plans complete

Plans:
**Wave 1**
- [x] 01-01-PLAN.md — Tracer: one property edit end to end (models, sexpr, fsutil, kicad_files), pinned manifests, pytest config, offscreen Qt test, .gitattributes, tracked UL zip (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-02-PLAN.md — fsutil hardening: atomic-write failure matrix, numbered backups, EOL/BOM/encoding, Issue contract (wave 2)
- [x] 01-03-PLAN.md — sexpr hardening: tokenizer edge cases, error positions, hostile input, splice and quoting contract (wave 2)
- [x] 01-04-PLAN.md — "tests" in SKIP_DIRS, byte-exact fixture builder and frozen fixtures with self-checks (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 01-05-PLAN.md — kicad_files read side complete, layering checks, full targeted-edit suite (wave 3)
- [x] 01-06-PLAN.md — Corpus round-trip: live Custom, fixtures, UL zip members, opt-in local KiCad tables and Wurth (wave 3)

### Phase 2: Hardening Existing Code

**Goal**: Generating tables, detecting KiCad and rescanning no longer lose data, crash or race, so the importer can safely build on them
**Depends on**: Phase 1
**Requirements**: HARD-01, HARD-02, HARD-03, HARD-04, HARD-05, HARD-06, HARD-07, HARD-08, HARD-09
**Success Criteria** (what must be TRUE):
  1. Regenerating `sym-lib-table` / `fp-lib-table` keeps every existing external entry, whatever its formatting or field order. Entries that can't be classified are kept verbatim and a warning is logged. Values containing `"` or `\` are escaped, so KiCad loads the table.
  2. Clicking Generate while a table is locked or read-only logs one error per file and leaves the GUI responsive and consistent. `kicad_common.json` is backed up before it changes, is written atomically, and afterwards only `environment.vars` differs.
  3. When both KiCad 9.0 and 10.0 are present, 10.0 is chosen. Pressing Rescan or Set KiCad Path while a scan is running does not start a second scan.
  4. After Rescan, the user's symbol and footprint selection is unchanged. Two libraries with the same nickname in different sources are reported as a collision and stay distinct in the UI, so neither overwrites the other.
  5. The existing footprints that used `${KIPRJMOD}/Custom/3DModels/...` reference `${CUSTOM_3DMODEL_DIR}/...` after one dedicated cleanup commit in `Custom`. A scan warns about any model path that still doesn't use `${CUSTOM_3DMODEL_DIR}`.

**Plans**: 9/9 plans complete

Plans:
**Wave 1**
- [x] 02-01-PLAN.md — Tracer: Generate splices a table and logs Issues end to end; restore and table reads on the lossless reader, rel_path pre-selection, one destination logger (wave 1)
- [x] 02-08-PLAN.md — fsutil review fixes (numbered backups, best-effort copystat, encodable-text guard, folder/read-only error mapping, honest mixed-EOL text) and legacy CLI deleted with its docs (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 02-03-PLAN.md — Table merge hardening: child classification, D-03/D-07/D-08/D-09 handling, per-file failures with one shared backup number (wave 2)
- [x] 02-09-PLAN.md — Scan output as Issues, collision_peers field and nickname collision pass; Severity formats as its value, downloaded_examples/ skipped (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 02-02-PLAN.md — Library tree: rel_path-keyed items, populate without footprint re-sync, collision mark and mutual exclusion (wave 3)
- [x] 02-04-PLAN.md — KiCad config: numeric version choice, backed-up and verified atomic kicad_common.json sync, KiCad-running warning, Issue routing in Generate (wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 02-05-PLAN.md — Scanner: per-source model-path rules on the parser, retarget_model helper (wave 4)
- [x] 02-06-PLAN.md — Main window: one guarded scan funnel, startup-only table pre-selection with collision trim and linked footprints, rel_path re-apply on rescan (wave 4)

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 02-07-PLAN.md — HARD-09 one-off: rewrite the five legacy model paths, owner-approved Custom commit and parent ref bump, never pushed (wave 5)

### Phase 3: Package Intake and Naming

**Goal**: Given a vendor zip or a folder of loose files, the importer safely finds the KiCad symbol, footprint and 3D model and proposes a sanitised, convention-following target library name, without writing anything into the repo
**Depends on**: Phase 2
**Requirements**: INTK-01, INTK-02, INTK-05, INTK-06, LIB-01, LIB-03
**Success Criteria** (what must be TRUE):
  1. Opening `downloaded_examples/ul_CSD85301Q2.zip` identifies it as Ultra Librarian. It finds the timestamp-named symbol file under `KiCADv6/`, `DQK0006B.kicad_mod` under `KiCADv6/footprints.pretty/`, and `DLV0006A.stp` at the zip root. A folder of loose `.kicad_sym` / `.kicad_mod` / `.step` / `.stp` files is read the same way.
  2. A package containing only KiCad 5 files (`.lib`, `.dcm`, `.mod`) is rejected with a clear "re-download as KiCad v6+" message
  3. A zip is refused if it has `..`, absolute or drive-letter member names, symlinks, or exceeds the size, count or compression-ratio limits. Package content is only ever staged in a temporary folder outside the repo, never inside it.
  4. For the UL sample, the suggested target library follows `<Type>_<SubCategory>_<Manufacturer>`, ends in `_TI` (from the `ti.com` datasheet host and existing `Custom/` prefixes), and is a default that can be overridden
  5. Names containing `/`, `:`, Windows-reserved names (e.g. `CON`, `NUL`) or traversal are sanitised, with `.` and `-` kept. Both the original and the sanitised name are reported.

**Plans**: 9/9 plans executed (03-08 and 03-09 are gap closure)

Plans:
**Wave 1**
- [x] 03-01-PLAN.md — Tracer: UL zip -> staging outside the repo -> UL adapter -> candidate (with-block and explicit `close()`), then `IC_SubCategory_TI`; Qt-free and no-bulk-extraction checks on its modules (wave 1)
- [x] 03-02-PLAN.md — Shared test infrastructure: hostile/lying/encrypted zip builders, `unpack_sample` (UL zip unpacked into `tmp_path` as the real loose-files case, D-17), KiCad/3D/legacy bytes, synthetic `Custom/` layout, `downloaded_examples/** -text`, importer layering guard with synthetic self-tests (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 03-03-PLAN.md — Zip safety: whole-package refusal of hostile, duplicate and encrypted members (D-05, D-19), size/count/ratio caps on declared and real bytes, one-level nested zips, staging and cleanup checks (wave 2)
- [x] 03-04-PLAN.md — Detection: `file_kind` / `file_version` helpers, content checks and versions, `(module ...)` footprints accepted with a warning (D-18), every item returned, KiCad 5 legacy matrix, generic Unknown vendor, loose-folder adapter on real UL files (D-17) (wave 2)
- [x] 03-05-PLAN.md — Name sanitiser: `sanitize_name`, `sanitize_filename`, `case_clash`; every existing `Custom/` name unchanged; `name_check` on every candidate symbol, footprint and model (original beside sanitised) (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 03-06-PLAN.md — Library suggestion: fresh `Custom/` listing, manufacturer alias/host/aggregator chain, SubCategory vocabulary with an explicit spelling rule, ranked alternatives, D-04 placeholder contract (wave 3)
- [x] 03-07-PLAN.md — Folder intake: read-only walk, links and junctions skipped, depth and size caps, real loose UL files and unzipped UL parity with zips (D-17) (wave 3)

**Wave 4 (gap closure)** *(blocked on Wave 3 completion)*
- [x] 03-08-PLAN.md — CR-01: parsed KiCad text capped at 8 MiB (`MAX_KICAD_TEXT_BYTES`) and 1,000,000 parser nodes (`MAX_KICAD_TEXT_NODES`, additive `max_nodes` on `sexpr.parse` / `parse_bytes`); over-cap symbol or footprint files skipped with a WARNING, MemoryError guard (wave 4)

**Wave 5 (gap closure)** *(blocked on Wave 4 completion)*
- [x] 03-09-PLAN.md — CR-02: corrupt LZMA / zstd members return `intake.corrupt` with the staging folder removed before `open_package` returns; guarded temp-folder creation (`intake.staging_failed`); codec tripwire and never-raises contract tests; WR-03 left open (wave 5)

### Phase 4: Plan and Install Core

**Goal**: A parsed part installs into `Custom/` correctly and transactionally. The symbol is merged, the footprint and 3D model are placed and linked, failures are rolled back and the result is verified, all testable without a display.
**Depends on**: Phase 3
**Requirements**: INST-01, INST-02, INST-03, INST-04, INST-05, INST-06, INST-07, INST-08, INST-09, INTK-08, LIB-02, POST-03, POST-04
**Success Criteria** (what must be TRUE):
  1. Installing the UL sample into a copy of `Custom/` does four things. It adds `CSD85301Q2` to the target `.kicad_sym`, leaving every other symbol and the library header byte-identical. It writes `DQK0006B.kicad_mod` with filename, internal name, value text, the symbol's `Footprint` field (`<Lib>:DQK0006B`) and `ki_fp_filters` all in agreement. It copies the STEP to `Custom/3DModels/CSD85301Q2.stp`. It inserts a `${CUSTOM_3DMODEL_DIR}/CSD85301Q2.stp` model block, because the vendor footprint has none.
  2. Renaming a symbol renames its unit sub-symbols (e.g. `CSD85301Q2_1_1`, `CSD85301Q2_2_1`) and any `extends` reference, and nothing else. A package with no 3D model installs without one and reports a "no 3D model found" warning.
  3. Installing into a new library name creates a matching `.kicad_sym` + `.pretty/` pair, and an existing library's version header is never changed. When `kicad-cli` is available, the incoming symbol and footprint are normalised to the installed KiCad's format before merging. Without it, they are merged as-is with a warning.
  4. A failure injected on any write leaves every file the install touched exactly as it was, with no dangling symbol, orphan footprint or stray model, and the failure is logged. An existing model with the same SHA-256 is reused, and a different one is reported as a conflict instead of being overwritten.
  5. After install, verification re-parses the written files, resolves `<Lib>:<FP>` and confirms the model file exists. It warns when the part name already exists in another library or the symbol's pin numbers don't match the footprint's pad numbers. Importing the same package twice with the same choices changes nothing the second time.

**Plans**: TBD
**Contract from Phase 3 (D-04)**: install is refused while `importer.suggest.placeholder_tokens(name)` is non-empty for the chosen target library name (a `Type`, `SubCategory` or `Manufacturer` placeholder is still in it).
**Research flag**: Spike early. Check that KiCad 9/10 loads a `20211014` symbol spliced into a `20241209` library, and check how `kicad-cli sym upgrade` / `fp upgrade` behave on a staging copy. Also decide how vendor symbols that use `extends` are handled.

### Phase 5: Import UI and Post-Install

**Goal**: The user imports a part end to end from the Library Manager. They pick a package, review and edit an exact preview, resolve conflicts, install, and see the new library selected with tables refreshed.
**Depends on**: Phase 4
**Requirements**: INTK-07, PREV-01, PREV-02, PREV-03, PREV-04, PREV-05, PREV-06, PREV-07, POST-01, POST-02, POST-05, UX-01, UX-02
**Success Criteria** (what must be TRUE):
  1. User starts an import from an "Import Part..." action or by dropping a zip or folder onto the main window. The file dialog opens in the last-used folder and offers the newest zip in Downloads. When the package holds several symbols, footprints or models, the user picks which ones to import.
  2. Before anything is written, the preview lists every file to be created or modified, every rename and every path rewrite. It also shows source vs target KiCad format versions, whether `kicad-cli` will normalise the part, and warnings such as "no 3D model found". Nothing on disk changes until the user clicks Install.
  3. User can edit the target library (an existing `Custom/` library or a new name), the footprint name (defaulting to the vendor name, e.g. `DQK0006B`), Value, Datasheet, Description, `Manufacturer` and `MPN`. The displayed `Footprint` field follows as `<Lib>:<FP>` on every edit. The installed files match exactly what the preview last showed.
  4. Every conflict with an existing symbol, footprint or 3D model appears in the preview with its own overwrite / rename / skip choice. There is no "overwrite all" option.
  5. After install, the library list rescans and shows the new or updated library selected. `sym-lib-table` / `fp-lib-table` are regenerated when a new library was created. If KiCad appears to be running, the user is told to reopen KiCad's library editors.

**Plans**: TBD
**UI hint**: yes
**Contract from Phase 3 (D-04)**: the Install button stays disabled, with the reason shown, while `importer.suggest.placeholder_tokens(name)` is non-empty for the edited target library name.

### Phase 6: Git Commit Step

**Goal**: After a successful install, one confirmed action commits exactly the imported part in the `Custom` submodule and bumps the parent repo's ref. The importer never pushes.
**Depends on**: Phase 5
**Requirements**: GIT-01, GIT-02, GIT-03, GIT-04, GIT-05
**Success Criteria** (what must be TRUE):
  1. After a successful install, a confirmation dialog shows the `Custom` branch (or that HEAD is detached) and the exact list of files to commit. It also shows an editable commit message that already records the vendor, the original package filename and the date.
  2. On confirm, only the files touched by the install are committed in `Custom`, so other modified or untracked files stay uncommitted. A parent-repo commit of the updated `Custom` ref follows.
  3. If `Custom` is on a detached HEAD that lies on `main`'s history, the user is offered a switch to `main` before committing. Otherwise the commit is refused with an explanation and nothing is committed.
  4. No importer code path pushes. After a commit, the local branches are ahead of their remotes and no remote has changed.

**Plans**: TBD
**UI hint**: yes
**Research flag**: Spike early. `Custom` is on a detached HEAD, and its gitdir is worktree-private (`.git/worktrees/Kicad_Libraries-importer/modules/Custom`). How `git commit -- Custom` behaves in the parent under the owner's hooks is unverified.

### Phase 7: SnapEDA and SamacSys Adapters

**Goal**: SnapEDA and SamacSys / Component Search Engine downloads import through the same flow as Ultra Librarian packages
**Depends on**: Phase 6
**Requirements**: INTK-03, INTK-04
**Success Criteria** (what must be TRUE):
  1. A real SnapEDA zip in `downloaded_examples/` is recognised as SnapEDA, and its symbol, footprint and any 3D model are found. If it ships no model, it installs with the "no 3D model found" warning.
  2. A real SamacSys / CSE zip in `downloaded_examples/` is recognised, and its KiCad v6+ symbol, footprint and 3D model are found. Legacy `.lib` / `.dcm` files alongside them are ignored instead of causing a rejection.
  3. Each vendor's sample installs into a copy of `Custom/` with the same `<Lib>:<FP>` link and `${CUSTOM_3DMODEL_DIR}` model path as the UL sample. This is covered by pytest fixtures, trimmed or synthetic where redistribution terms forbid committing the original.

**Plans**: TBD
**Research flag**: Blocked until the owner adds one real SnapEDA download and one real SamacSys/CSE download to `downloaded_examples/`. The layouts are unverified: SnapEDA may ship no 3D model, and SamacSys may ship legacy files alongside v6 files.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 6/6 | Complete    | 2026-10-18 |
| 2. Hardening Existing Code | 9/9 | Complete    | 2026-10-19 |
| 3. Package Intake and Naming | 9/9 | In Progress | - |
| 4. Plan and Install Core | 0/TBD | Not started | - |
| 5. Import UI and Post-Install | 0/TBD | Not started | - |
| 6. Git Commit Step | 0/TBD | Not started | - |
| 7. SnapEDA and SamacSys Adapters | 0/TBD | Not started | - |
