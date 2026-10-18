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

### Active

**Importer — input**
- [ ] Browse to and open a vendor package: Ultra Librarian zip, SnapEDA zip, SamacSys/CSE zip, or a folder of loose `.kicad_sym` / `.kicad_mod` / `.step`/`.stp` files
- [ ] Auto-detect the package format and locate the KiCad symbol, footprint(s) and 3D model inside it, whatever the folder depth or layout
- [ ] Handle packages with no 3D model: install without one and log a warning
- [ ] One package per import session

**Importer — target library**
- [ ] Suggest a target library name following `<Type>_<SubCategory>_<Manufacturer>` (e.g. `Transistor_MOSFET_TI`) from the part's info, editable by the user
- [ ] Choose an existing `Custom/` library or create a new one, creating the matching `.kicad_sym` + `.pretty/` pair

**Importer — preview and editing**
- [ ] A preview step before anything is written: target files, new or renamed names, path rewrites and detected conflicts
- [ ] Footprint name defaults to the vendor name (e.g. `DQK0006B`) and can be edited in the preview
- [ ] Symbol's Footprint field set automatically to `<Lib>:<FP>`. Value, Datasheet, MPN, Manufacturer and Description are shown for editing in the preview
- [ ] Name conflicts with existing symbols or footprints are shown in the preview, and the user picks overwrite, rename or skip each time

**Importer — install**
- [ ] Merge the symbol into the target `.kicad_sym` without hand-editing (S-expression-aware, not regex-on-first-match)
- [ ] Copy the footprint into the target `.pretty/` folder
- [ ] Copy the 3D model into `Custom/3DModels/` and rewrite the footprint's model path to `${CUSTOM_3DMODEL_DIR}/<file>.step`
- [ ] After install: rescan and regenerate `sym-lib-table` / `fp-lib-table`
- [ ] After install: ask for confirmation, then commit the new part in the `Custom` submodule and bump the parent repo's submodule ref. Commit only, never push.

**Hardening of existing code (all High / Medium-High concerns from `.planning/codebase/CONCERNS.md`)**
- [ ] Table merge no longer silently drops external entries that don't match the strict regex. Use a proper S-expression parse, and warn about entries that can't be classified.
- [ ] File-system errors during Generate (locked or read-only tables) are caught and logged instead of raising inside a Qt slot
- [ ] Atomic writes (temp file + `os.replace`) for the library tables and `kicad_common.json`, with a backup of `kicad_common.json` before it is modified
- [ ] KiCad version directories sorted numerically, so `10.0` is chosen over `9.0`
- [ ] No overlapping scans: Rescan and Set KiCad Path can't start a scan while one is running
- [ ] Generated S-expression values are escaped

**Quality**
- [ ] Headless pytest suite for importer logic (format detection, symbol merge, path rewriting, naming), using real downloads as fixtures, plus tests for the hardened table and parser code
- [ ] Dependency manifest with pinned PySide6

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
- **Sample data:** only one example exists so far, `downloaded_examples/ul_CSD85301Q2.zip` (Ultra Librarian). It contains `KiCADv6/<timestamp>.kicad_sym` and `KiCADv6/footprints.pretty/DQK0006B.kicad_mod`, plus import guides, and no STEP model. The symbol file is named by timestamp, not part number.
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
| Fix all High/Medium-High concerns from the codebase map | Importer builds on table/scan/write code that has known data-loss risks | — Pending |
| Headless pytest for importer and hardened logic | No tests today; parsers and merges are regression-prone | — Pending |
| Replace regex parsing with an S-expression tokenizer | Needed for safe symbol merge and fixes the table-merge bug | — Pending |

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
*Last updated: 2026-10-18 after initialization*
