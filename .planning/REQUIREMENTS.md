# Requirements: KiCad Part Importer

**Defined:** 2026-10-18
**Core Value:** A downloaded vendor package ends up as a correctly named, correctly linked part in the right `Custom/` library, with the symbol's Footprint field pointing at `<Lib>:<FP>` and the 3D model at `${CUSTOM_3DMODEL_DIR}/<file>.step`, without hand-editing any KiCad file.

## v1 Requirements

Requirements for the initial release. Each one maps to a roadmap phase.

### Foundation

- [x] **FOUND-01**: Developer can install pinned runtime and dev dependencies from `requirements.txt` / `requirements-dev.txt` (PySide6 pinned, pytest, pytest-qt)
- [x] **FOUND-02**: Developer can run a headless pytest suite (`pytest`) with no display, which includes Qt tests in offscreen mode
- [x] **FOUND-03**: Every `.kicad_sym`, `.kicad_mod` and lib-table file in the repo round-trips byte-identically through the S-expression layer when no edits are applied
- [x] **FOUND-04**: An edit made through the S-expression layer changes only the targeted span, keeps the file's line endings (CRLF/LF) and leaves the rest byte-identical
- [x] **FOUND-05**: Files written by the app are replaced atomically (temp file + replace) and a locked or read-only target produces a logged error, not a crash or truncated file

### Hardening

- [x] **HARD-01**: Regenerating tables keeps every existing external entry in `sym-lib-table` / `fp-lib-table`, whatever its formatting or field order. Entries that can't be classified are kept verbatim and a warning is logged.
- [x] **HARD-02**: Generate on a locked or read-only table logs an error per file and leaves the UI consistent, with no unhandled exception
- [x] **HARD-03**: `kicad_common.json` is backed up before modification and written atomically, and only `environment.vars` is changed
- [x] **HARD-04**: With multiple KiCad versions installed, the newest is chosen by numeric comparison (`10.0` over `9.0`)
- [x] **HARD-05**: User cannot start a second scan while one is running (Rescan, Set KiCad Path, post-import rescan)
- [x] **HARD-06**: Generated table values containing `"` or `\` are escaped so KiCad loads the table
- [x] **HARD-07**: Rescan keeps the user's current symbol/footprint selection instead of resetting it from the tables
- [x] **HARD-08**: Libraries with the same nickname in different sources are reported as a collision and no longer overwrite each other in the UI
- [x] **HARD-09**: Existing footprints using `${KIPRJMOD}/Custom/3DModels/...` are rewritten to `${CUSTOM_3DMODEL_DIR}/...` in one explicit cleanup commit, and the scanner warns about any non-`${CUSTOM_3DMODEL_DIR}` model path that remains

### Package Intake

- [x] **INTK-01**: User can open a vendor package as a `.zip` file or a folder of loose `.kicad_sym` / `.kicad_mod` / `.step` / `.stp` files
- [x] **INTK-02**: An Ultra Librarian zip is recognised, and its symbol, footprint and 3D model are found wherever they sit, including a STEP at the zip root whose name differs from the footprint (e.g. `ul_CSD85301Q2.zip`)
- [ ] **INTK-03**: A SnapEDA zip is recognised and its symbol, footprint and any 3D model are found, verified against a real SnapEDA download in `downloaded_examples/`
- [ ] **INTK-04**: A SamacSys / Component Search Engine zip is recognised and its KiCad symbol, footprint and 3D model are found, verified against a real CSE download in `downloaded_examples/`
- [x] **INTK-05**: Packages containing only legacy KiCad 5 files (`.lib`, `.dcm`, `.mod`) are rejected with a clear "re-download as KiCad v6+" message
- [x] **INTK-06**: Zips are read safely: no extraction into the repo, path traversal, absolute names and symlinks are rejected, and size and count limits stop zip bombs
- [ ] **INTK-07**: When a package holds several symbols, footprints or models, the user picks which ones to import
- [ ] **INTK-08**: A package with no 3D model can still be installed, and the preview and log warn that no model was found

### Target Library

- [x] **LIB-01**: User sees a suggested target library name following `<Type>_<SubCategory>_<Manufacturer>`, derived from existing `Custom/` libraries and part info (e.g. datasheet host `ti.com` → `TI`), and can edit it
- [ ] **LIB-02**: User can choose an existing `Custom/` library from a list or create a new one, and a new library creates a matching `.kicad_sym` + `.pretty/` pair
- [x] **LIB-03**: Symbol, footprint and file names are sanitised (no `/`, `:`, Windows-reserved names or traversal; `.` and `-` kept), and the preview shows original vs sanitised names

### Preview & Editing

- [ ] **PREV-01**: Before anything is written, user sees a preview listing every file to be created or modified, every rename and every path rewrite
- [ ] **PREV-02**: User can edit the footprint name in the preview. It defaults to the vendor name (e.g. `DQK0006B`).
- [ ] **PREV-03**: The symbol's Footprint field is set to `<Lib>:<FP>` automatically and stays in sync when the library or footprint name is edited
- [ ] **PREV-04**: User can edit Value, Datasheet, Description, `Manufacturer` and `MPN` in the preview. Missing fields are created with those exact property names.
- [ ] **PREV-05**: Each name conflict with an existing symbol, footprint or 3D model is shown in the preview, and the user picks overwrite, rename or skip for each one
- [ ] **PREV-06**: Preview shows source vs target KiCad file-format versions and whether the incoming part will be normalised with `kicad-cli`
- [ ] **PREV-07**: What the preview shows is exactly what gets installed. Preview and install use the same plan, and the plan is rebuilt on every edit.

### Install

- [ ] **INST-01**: The symbol is added to the target `.kicad_sym` without changing any other symbol or the library header
- [ ] **INST-02**: Renaming a symbol also renames its unit sub-symbols (`<Name>_<u>_<s>`) and any `extends` reference, and never renames by substring
- [ ] **INST-03**: The footprint is written to the target `.pretty/`, with filename, internal footprint name, value text, the symbol's Footprint field and `ki_fp_filters` all consistent
- [ ] **INST-04**: The 3D model is copied into `Custom/3DModels/` as `<MPN>.<original ext>` (case kept). An identical existing file (same SHA-256) is reused silently; a different one is a preview conflict.
- [ ] **INST-05**: The footprint references the model as `${CUSTOM_3DMODEL_DIR}/<file>`, rewriting an existing `(model ...)` path or inserting a model block when the vendor footprint has none
- [ ] **INST-06**: When `kicad-cli` is available, the incoming symbol is normalised to the target library's format before merging (footprints are copied as-is, D-02). Without it, the symbol is merged as-is with a warning.
- [ ] **INST-07**: If any write fails, every file touched by the install is restored to its previous state and the failure is logged
- [ ] **INST-08**: After install, the result is verified: files re-parse, `<Lib>:<FP>` resolves, and the model file exists. Any failure is reported in the log.
- [ ] **INST-09**: Importing the same package twice with the same choices changes nothing the second time

### Post-Install

- [ ] **POST-01**: After install, the library list rescans and the new or updated library is shown and selected
- [ ] **POST-02**: When a new library was created, `sym-lib-table` / `fp-lib-table` are regenerated
- [ ] **POST-03**: User is warned when the imported part name already exists in another library
- [ ] **POST-04**: User is warned when the symbol's pin numbers don't match the footprint's pad numbers
- [ ] **POST-05**: User is told to reopen KiCad's library editors if KiCad appears to be running

### Git

- [ ] **GIT-01**: After install, user is asked to confirm a commit and sees the branch, the exact file list and an editable message
- [ ] **GIT-02**: On confirm, only the files touched by the install are committed in the `Custom` submodule (never `add -A`), and then the parent repo's `Custom` ref is committed
- [ ] **GIT-03**: If `Custom` is on a detached HEAD that is on `main`'s history, user is offered a switch to `main` before committing. Otherwise the commit is refused with an explanation.
- [ ] **GIT-04**: The commit message records provenance: vendor, original package filename and date
- [ ] **GIT-05**: The importer never pushes

### Usability

- [ ] **UX-01**: User can start an import by dropping a zip or folder onto the main window
- [ ] **UX-02**: The import dialog remembers the last folder used and offers the most recent zip in the Downloads folder

## v2 Requirements

Deferred to a future release. Tracked but not in the current roadmap.

### Preview

- **PREV2-01**: SVG preview of symbol and footprint via `kicad-cli export svg`

### Formats

- **FMT2-01**: Convert legacy KiCad 5 `.lib` / `.dcm` / `.mod` packages instead of rejecting them
- **FMT2-02**: Attach a separately downloaded STEP to a part whose package has none

### Metadata

- **META2-01**: Hidden provenance property on imported symbols
- **META2-02**: Migrate existing symbols' `MF` / `MP` / `MANUFACTURER` fields to `Manufacturer` / `MPN`

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Downloading parts from vendor sites / MPN search / EasyEDA-LCSC import | User downloads manually; importer starts from a file on disk |
| Pushing to remotes | Pushing stays a deliberate manual act |
| Importing into WurthElektronik or other third-party submodules | Upstream-owned; only `Custom/` is writable |
| Batch / queued imports | Decided: one package at a time |
| Watch-folder auto-import | Silent imports contradict preview-before-write |
| Silent or global "overwrite all" | Conflicts are resolved per item |
| Restyling symbol graphics or footprint geometry | Only names, fields and paths are changed |
| Choice of 3D path variable / `.step.gz` compression | Convention is `${CUSTOM_3DMODEL_DIR}/<file>` |
| Keeping source zips in the repo | Repo holds libraries, not downloads |
| Built-in undo manager | Git is the undo; transactional install covers failures |
| Upgrading a whole target library's format | Noisy diffs; only the incoming part is normalised |
| Legacy CLI table generator | Deleted in Phase 2 (D-11); the GUI is the only table-generation path |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| FOUND-04 | Phase 1 | Complete |
| FOUND-05 | Phase 1 | Complete |
| HARD-01 | Phase 2 | Complete |
| HARD-02 | Phase 2 | Complete |
| HARD-03 | Phase 2 | Complete |
| HARD-04 | Phase 2 | Complete |
| HARD-05 | Phase 2 | Complete |
| HARD-06 | Phase 2 | Complete |
| HARD-07 | Phase 2 | Complete |
| HARD-08 | Phase 2 | Complete |
| HARD-09 | Phase 2 | Complete |
| INTK-01 | Phase 3 | Complete |
| INTK-02 | Phase 3 | Complete |
| INTK-03 | Phase 7 | Pending |
| INTK-04 | Phase 7 | Pending |
| INTK-05 | Phase 3 | Complete |
| INTK-06 | Phase 3 | Complete |
| INTK-07 | Phase 5 | Pending |
| INTK-08 | Phase 4 | Pending |
| LIB-01 | Phase 3 | Complete |
| LIB-02 | Phase 4 | Pending |
| LIB-03 | Phase 3 | Complete |
| PREV-01 | Phase 5 | Pending |
| PREV-02 | Phase 5 | Pending |
| PREV-03 | Phase 5 | Pending |
| PREV-04 | Phase 5 | Pending |
| PREV-05 | Phase 5 | Pending |
| PREV-06 | Phase 5 | Pending |
| PREV-07 | Phase 5 | Pending |
| INST-01 | Phase 4 | Pending |
| INST-02 | Phase 4 | Pending |
| INST-03 | Phase 4 | Pending |
| INST-04 | Phase 4 | Pending |
| INST-05 | Phase 4 | Pending |
| INST-06 | Phase 4 | Pending |
| INST-07 | Phase 4 | Pending |
| INST-08 | Phase 4 | Pending |
| INST-09 | Phase 4 | Pending |
| POST-01 | Phase 5 | Pending |
| POST-02 | Phase 5 | Pending |
| POST-03 | Phase 4 | Pending |
| POST-04 | Phase 4 | Pending |
| POST-05 | Phase 5 | Pending |
| GIT-01 | Phase 6 | Pending |
| GIT-02 | Phase 6 | Pending |
| GIT-03 | Phase 6 | Pending |
| GIT-04 | Phase 6 | Pending |
| GIT-05 | Phase 6 | Pending |
| UX-01 | Phase 5 | Pending |
| UX-02 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 53 total
- Mapped to phases: 53
- Unmapped: 0 ✓

---
*Requirements defined: 2026-10-18*
*Last updated: 2026-10-18 after roadmap creation (traceability mapped)*
