# KiCad Part Importer

## What This Is

A part importer added to the existing PySide6 KiCad Library Manager (`kicad_lib_manager`). The user browses to a component package downloaded from Ultra Librarian, SnapEDA, SamacSys / Component Search Engine, or a folder of loose files. They pick or create a target library in the `Custom/` submodule, review a preview, and click install. The importer extracts the package, places the symbol, footprint and 3D model in the right places, and rewrites names and paths to the repo's conventions. It then refreshes the library tables and, after confirmation, commits the part in the `Custom` submodule. It is a personal tool for the repo owner, replacing the manual copy, paste and path-fixing routine described in CLAUDE.md.

## Core Value

A downloaded vendor package ends up as a correctly named, correctly linked part in the right `Custom/` library, with the symbol's Footprint field pointing at `<Lib>:<FP>` and the 3D model at `${CUSTOM_3DMODEL_DIR}/<file>.step`, without hand-editing any KiCad file.

## Requirements

### Validated

<!-- Inferred from the existing codebase (see .planning/codebase/). -->

- ✓ Scan the repo for symbol libraries (`.kicad_sym`) and footprint libraries (`.pretty/`), grouped by source (Custom, WurthElektronik) — existing
- ✓ Parse each symbol's footprint references and cross-check them against the repo and KiCad's default footprint libraries, with warnings for missing ones — existing
- ✓ Check 3D model paths referenced in `.kicad_mod` files — existing
- ✓ Auto-detect the KiCad install and user config directory, and prompt for the footprints folder if they aren't found — existing
- ✓ Two-column Symbols | Footprints tree, where symbol selection drives footprint selection per source — existing
- ✓ Generate `sym-lib-table` / `fp-lib-table`, merging in existing external entries, with numbered paired backups and restore — existing
- ✓ Write `KICAD_LIB_GITHUB` and `CUSTOM_3DMODEL_DIR` into KiCad's `kicad_common.json` — existing
- ✓ Background scan on a QThread, a colour-coded log panel, Rescan (Ctrl+Shift+R), and persisted settings (QSettings) — existing
- ✓ Dependency manifest with pinned PySide6 (`requirements.txt` / `requirements-dev.txt`) — Phase 1
- ✓ Headless pytest harness (offscreen Qt, strict markers), run bare from the repo root — Phase 1
- ✓ Lossless S-expression layer: every repo `.kicad_sym`, `.kicad_mod` and lib table round-trips byte-identically; edits change only the targeted span and keep CRLF/LF — Phase 1
- ✓ Atomic write helper (temp file + `os.replace`, read-only pre-check, locked-file retry) and `<name>_backup_<N>` backup helper in `fsutil.py` — Phase 1
- ✓ Table merge keeps every external entry whatever its layout; entries it can't classify are kept verbatim with a warning (HARD-01) — Phase 2
- ✓ Locked or read-only tables during Generate log one error per file and leave the UI consistent (HARD-02) — Phase 2
- ✓ `kicad_common.json` is backed up, written atomically, and only `environment.vars` changes (HARD-03) — Phase 2
- ✓ KiCad version directories sorted numerically, so `10.0` wins over `9.0` (HARD-04) — Phase 2
- ✓ No overlapping scans: one guarded `_start_scan`, with controls disabled while a scan runs (HARD-05) — Phase 2
- ✓ Generated S-expression values are escaped (HARD-06) — Phase 2
- ✓ Rescan keeps the current selection; pre-selection from the tables happens only at startup (HARD-07) — Phase 2
- ✓ Same-nickname libraries in different sources are reported as a collision and kept distinct in the UI (HARD-08) — Phase 2
- ✓ Legacy `${KIPRJMOD}/Custom/3DModels` paths rewritten to `${CUSTOM_3DMODEL_DIR}` in one Custom commit; the scanner warns about any other model path (HARD-09) — Phase 2
- ✓ Legacy `generate_lib_tables.py` CLI removed; issues routed by severity instead of message substrings — Phase 2
- ✓ A vendor package opens as a `.zip` or a folder of loose KiCad files, read in place or staged outside the repo, never written into it (INTK-01) — Phase 3
- ✓ Ultra Librarian zips are recognised and their symbol, footprint and 3D model found at any depth, including a root-level STEP with an unrelated name (INTK-02) — Phase 3
- ✓ KiCad 5-only packages are rejected with a "re-download as KiCad v6+" message (INTK-05) — Phase 3
- ✓ Hostile packages are refused or skipped safely: zip slip, absolute names, symlinks, zip bombs, corrupt members, and oversized or string-heavy KiCad text bounded in memory (INTK-06) — Phase 3
- ✓ A `<Type>_<SubCategory>_<Manufacturer>` library name is suggested from existing `Custom/` libraries and part info (LIB-01; editing arrives with the Phase 5 preview) — Phase 3
- ✓ Symbol, footprint and file names are sanitised, with original and sanitised names both reported (LIB-03) — Phase 3
- ✓ Symbol merged into the target `.kicad_sym` S-expression-aware: other symbols and the header stay byte-identical, renames follow sub-symbols and `extends` (INST-01, INST-02) — Phase 4
- ✓ Footprint copied into the target `.pretty/`; filename, internal name, value, symbol Footprint field `<Lib>:<FP>` and `ki_fp_filters` agree (INST-03) — Phase 4
- ✓ 3D model copied to `Custom/3DModels/<MPN>.<ext>` (same SHA-256 reused) and linked as `${CUSTOM_3DMODEL_DIR}/<file>`, rewriting or inserting the `(model ...)` block (INST-04, INST-05) — Phase 4
- ✓ Packages with no 3D model install without one and warn (INTK-08) — Phase 4
- ✓ A new library creates the matching `.kicad_sym` + `.pretty/` pair; an existing library header is never changed (LIB-02 install side; choosing in the UI arrives with Phase 5) — Phase 4
- ✓ Install is one transaction: app-data backups, ordered atomic writes, verify, and rollback on any failure or exception; a target changed after planning is refused as stale; a second identical install is a no-op (INST-06..INST-09) — Phase 4
- ✓ Post-install warnings for a name found in another library and for pin/pad mismatches (POST-03, POST-04) — Phase 4

### Active

**Importer — input**
- [ ] Browse to and open a vendor package: Ultra Librarian zip, SnapEDA zip, SamacSys/CSE zip, or a folder of loose `.kicad_sym` / `.kicad_mod` / `.step`/`.stp` files
- [ ] Auto-detect the package format and locate the KiCad symbol, footprint(s) and 3D model inside it, whatever the folder depth or layout
- [ ] One package per import session
- [ ] When detection finds no part, show the package-level reasons (for example a too-deep folder) instead of a bare "nothing found" (review WR-06, emerged in Phase 4; plus blank-string handling for footprint/symbol/model choices, IN-04)

**Importer — target library**
- [ ] Suggest a target library name following `<Type>_<SubCategory>_<Manufacturer>` (e.g. `Transistor_MOSFET_TI`) from the part's info, editable by the user
- [ ] Choose an existing `Custom/` library or create a new one, creating the matching `.kicad_sym` + `.pretty/` pair

**Importer — preview and editing**
- [ ] A preview step before anything is written: target files, new or renamed names, path rewrites and detected conflicts
- [ ] Footprint name defaults to the vendor name (e.g. `DQK0006B`) and can be edited in the preview
- [ ] Symbol's Footprint field set automatically to `<Lib>:<FP>`. Value, Datasheet, MPN, Manufacturer and Description are shown for editing in the preview
- [ ] Name conflicts with existing symbols or footprints are shown in the preview, and the user picks overwrite, rename or skip each time

**Importer — install**
- [ ] After install: rescan and regenerate `sym-lib-table` / `fp-lib-table`
- [ ] After install: ask for confirmation, then commit the new part in the `Custom` submodule and bump the parent repo's submodule ref. Commit only, never push.

**Quality**
- [ ] Headless pytest suite for importer logic (format detection, symbol merge, path rewriting, naming), using real downloads as fixtures, plus tests for the hardened table and parser code (harness and parser tests done in Phase 1, hardened-table/config/scan tests done in Phase 2; importer tests still to come)

### Out of Scope

- Downloading parts from vendor websites or APIs. The user downloads manually; the importer starts from a file on disk.
- Pushing to remotes. The importer commits only; pushing stays manual.
- Importing into the WurthElektronik submodule or other third-party libraries. They're upstream-owned, so imports go only into `Custom/`.
- Attaching a separately downloaded STEP file when the package has none. Decided: install without 3D and warn; models can be added later.
- Batch or queued imports. Decided: one package at a time.
- Non-KiCad formats inside packages (Altium, Eagle, OrCAD). Only the KiCad v6+ files are used.
- Editing symbol graphics or footprint geometry. Only names, fields and paths are changed.

## Context

- **Brownfield.** The importer extends `kicad_lib_manager/`, a layered PySide6 app with Qt-free services (`library_scanner.py`, `table_generator.py`), dataclass models, and a widgets package. See `.planning/codebase/ARCHITECTURE.md`.
- **Existing parsing is regex-based** and flagged as fragile. Symbol merging and footprint model-path rewriting need a real S-expression tokenizer, which can also be used to fix the table-merge bug.
- **Sample data:** only one example exists so far, `downloaded_examples/ul_CSD85301Q2.zip` (Ultra Librarian). It contains `KiCADv6/<timestamp>.kicad_sym`, `KiCADv6/footprints.pretty/DQK0006B.kicad_mod`, import guides, and a STEP model `DLV0006A.stp` at the zip root, outside `KiCADv6/`. Its name matches neither the footprint nor the part. The symbol file is named by timestamp, not part number. The vendor footprint has no `(model ...)` block, so the importer must be able to insert one, not only rewrite an existing path. The symbol's `Footprint` field is the bare `DQK0006B` with no `Lib:` prefix, and `ki_fp_filters` repeats the vendor footprint name.
- **Manual process being replaced** (from CLAUDE.md): download → move the `.kicad_mod` into `<Lib>.pretty/` → copy and paste the symbol into `<Lib>.kicad_sym` in the KiCad Symbol Editor → fix 3D paths to `${CUSTOM_3DMODEL_DIR}` → commit in the submodule, then update the parent repo.
- **Repo layout:** `Custom/` is a git submodule (`sylvanoMTL/kicad_custom_library`) and is also detected as a separate repo by GSD. Work happens in the worktree `Kicad_Libraries-importer` on branch `feature/part-importer`.
- **No tests exist today.** There's no lint config and no requirements file either.

## Constraints

- **Tech stack:** Python 3.10+ (venv on 3.14), PySide6 6.12, stdlib only otherwise unless a dependency is clearly justified. This extends the existing app rather than starting a new one.
- **Platform:** Windows 11 is primary, with standard CPython (not MSYS2) because PySide6 requires it. Keep the existing cross-platform branches working.
- **KiCad file formats:** output must load in KiCad 6+ (current install up to 9/10). Symbol and footprint names must match the library naming convention, and `.kicad_sym` / `.pretty` names must pair.
- **Safety:** no write without a preview first. Writes to KiCad files and the repo must be atomic or backed up. Git commits need explicit confirmation.
- **Dependencies:** real sample downloads from SnapEDA, SamacSys/CSE, and a loose-files case must be added to `downloaded_examples/` before those formats can be built and tested.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Importer lives inside the existing Library Manager app | Reuses scanner, log panel, settings and table generation; one tool for the repo | — Pending |
| Support UL, SnapEDA, SamacSys/CSE and loose files in v1 | Owner uses all of them; zip layouts differ | — Pending |
| Preview before every write; per-conflict overwrite/rename/skip | Avoid silent damage to curated libraries | — Pending |
| Library name suggested from `<Type>_<SubCategory>_<Manufacturer>`, editable | Keeps the convention without blocking edge cases | — Pending |
| Footprint keeps vendor name by default, editable | Package codes are often the right name; user can override | — Pending |
| Footprint link set automatically; other fields editable in preview | Footprint link is the most error-prone manual step | — Pending |
| No 3D model → install without it and warn | Keep the flow simple; models can be added later | — Pending |
| One package per import | Simpler review; batch not needed | — Pending |
| Commit in `Custom` + bump parent ref after confirmation; never push | Matches the CLAUDE.md git workflow; pushing stays a deliberate act | — Pending |
| Fix all High/Medium-High concerns from the codebase map | Importer builds on table/scan/write code that has known data-loss risks | ✓ Good — HARD-01..09 verified and UAT passed (Phase 2) |
| Managed table entries identified by URI tail after `${KICAD_LIB_GITHUB}/`, not by nickname | Nicknames can collide across sources; the path cannot | ✓ Good (Phase 2) |
| Scan busy guard is both disabled controls and a refusing `_start_scan` | A disabled control doesn't stop a programmatic caller (e.g. post-import rescan) | ✓ Good (Phase 2) |
| On a nickname collision, the peer whose rel_path sorts first (Custom before WurthElektronik) stays selected | Deterministic, and personal parts win | ✓ Good (Phase 2) |
| A running KiCad only warns; the `kicad_common.json` write still proceeds | Blocking would make Generate unusable while KiCad is open | — Pending |
| Headless pytest for importer and hardened logic | No tests today; parsers and merges are regression-prone | ✓ Good — harness in place, 290+ tests at Phase 1 close |
| Replace regex parsing with an S-expression tokenizer | Needed for safe symbol merge and fixes the table-merge bug | ✓ Good — span-splicing layer round-trips the whole corpus byte-identically (Phase 1) |
| Untrusted KiCad text is bounded before and during parsing: 8 MiB raw-byte cap, 1,000,000-node ceiling, and a linear windowed string scan; an over-cap file is skipped with a WARNING, never a whole-package refusal | Vendor packages are untrusted input; a single hostile file must not exhaust memory or hide the rest of the package | ✓ Good — CR-01/CR-03 closed, 8 MiB hostile strings read within 10× decoded size (Phase 3) |
| Intake never extracts into the repo: zips are staged member-by-member into a temp folder outside the repo, folders are read in place | Keeps the "no write without preview" guarantee for the whole intake step | ✓ Good (Phase 3) |
| Install is a transaction under `except BaseException`: any exception rolls back (`install.unexpected`), interrupts roll back then re-raise | A partial install in a curated library is the worst outcome; an Issue-only rollback missed exceptions (CR-01) | ✓ Good — gap closed and re-verified (Phase 4) |
| Stale-plan check held from preflight to the last write: post-gate re-check, backup copy hashed and used as the rollback pre-image, re-check before every write | kicad-cli runs between preflight and the first write; an edit there was silently overwritten (CR-02) | ✓ Good — gap closed and re-verified (Phase 4) |
| Blank preview text means "not set, keep the vendor value"; an explicit clear is a Phase 5 preview decision | A Qt line edit returns "" for untouched fields (WR-05) | — Pending (Phase 5 clear option) |
| kicad-cli normalises only the incoming symbol, and only when its output version equals the target header; footprints are copied as-is | Never change a library's version header; mixed versions load in KiCad 9 (D-01, D-02) | ✓ Good — loads in kicad-cli 9.0.9; KiCad 10 re-test deferred (backlog 999.1) |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-20 after Phase 4*
