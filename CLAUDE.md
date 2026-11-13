# CLAUDE.md

## Project Overview
KiCad library management repo that aggregates open-source and custom libraries via git submodules, with a PySide6 GUI for generating KiCad library tables.

## Repository Structure
- `Custom/` — submodule: `sylvanoMTL/kicad_custom_library` (personal parts)
- `WurthElektronik/KiCad-Library/` — submodule: open-source Wurth library
- `kicad_lib_manager.py` — PySide6 GUI entry point
- `kicad_lib_manager/` — GUI package:
  - `main_window.py` — MainWindow, ScanWorker (QThread), KiCad detection
  - `library_scanner.py` — scan repo, parse symbol/footprint links, cross-reference with KiCad defaults
  - `table_generator.py` — generate tables, backup/restore logic (paired by number)
  - `models.py` — dataclasses: SymbolLibrary, FootprintLibrary, FootprintRef, ScanResult
  - `widgets/library_table.py` — two-column QTreeWidget (Symbols | Footprints), per-source sync
  - `widgets/log_panel.py` — color-coded log panel (info, warning, error, success)
  - `widgets/backup_dialog.py` — paired backup restore dialog

## KiCad Path Variables
These must be set in KiCad: Preferences > Configure Paths:
- `KICAD_LIB_GITHUB` — points to this repo root (wherever the repo is cloned)
- `CUSTOM_3DMODEL_DIR` — points to `Custom/3DModels/` for custom 3D step files
- `WE_3DMODEL_DIR` — used by WurthElektronik footprints (set by their library)
- On the owner's workstation KiCad reads the main checkout: `KICAD_LIB_GITHUB` =
  `C:/Git_Repo_Clones/Kicad_Libraries` and `CUSTOM_3DMODEL_DIR` =
  `C:/Git_Repo_Clones/Kicad_Libraries/Custom/3DModels`. A git worktree such as
  `Kicad_Libraries-importer` is for development only — imports, Generate Tables, the
  migration, Pin Atomic Libraries in KiCad and their commits run from the main checkout (D-26).

## Library Naming Convention
Own symbol libraries are named `Atomic_<official KiCad symbol library stem>`
(examples: `Atomic_Connector`, `Atomic_Battery_Management`, `Atomic_Transistor_FET`,
`Atomic_Oscillator`), filed by what the device is — never by manufacturer. Every
footprint lives in the one shared `Custom/Footprints/Atomic_Footprints.pretty` (or the
part links an official KiCad footprint instead), so symbol and footprint libraries no
longer pair by name.

Every part in an `Atomic_` library must pass the atomic rule:
- `MPN` and `Manufacturer` fields are set
- `Footprint` resolves to exactly one `Lib:FP`
- `Value` = `MPN`
- `Datasheet` is set (not empty or `~`)
- `Description` is set
- its 3D model file exists

Symbol name = sanitised MPN. 3D models live in `Custom/3DModels/` named `<MPN>.<ext>`
and are linked as `${CUSTOM_3DMODEL_DIR}/<file>`.

## Importing Parts
File > Import Part... (`Ctrl+I`) is the way in for Ultra Librarian, SnapEDA, SamacSys
and loose files — it extracts the package, places the symbol, footprint and 3D model,
and rewrites names and paths to the atomic scheme before any write.

Manual route (rare — when the importer can't be used):
1. Move the `.kicad_mod` into `Atomic_Footprints.pretty`
2. Add the symbol to the matching `Atomic_<stem>` library via KiCad Symbol Editor
   (copy/paste), with fields filled per the atomic rule above
3. Fix 3D model paths to use `${CUSTOM_3DMODEL_DIR}/<filename>.step`
4. Commit in the Custom submodule first, then update parent repo

## Python Environment
- Use `py -m venv env` (Windows CPython from python.org, NOT MSYS2 Python) — PySide6 requires standard Windows Python
- Activate: `.\env\Scripts\activate` (PowerShell)
- Dependencies: `pip install PySide6`

## Running the GUI
```
.\env\Scripts\python.exe kicad_lib_manager.py
```

### GUI Behavior
- **Startup**: auto-detects KiCad installation for default footprint cross-referencing. If not found, prompts the user to select the footprints folder. The last scan is shown instantly when no library file changed since it was saved; otherwise the full scan runs and the log says why. Rescan always runs the full scan. The Destination box offers only folders that still exist (a deleted folder in the saved history is skipped, and the repository folder is used when none is left).
- **Loading Libraries**: the window shown while a full scan runs has a **Skip** button from the moment the scan starts reading a library source (its symbols, then its 3D model paths); it names that source (for example **Skip WurthElektronik**) and skips only that source's 3D model path check. The symbols are always read in full, so its libraries are still listed and Generate Tables keeps them; a Skip pressed while the symbols are read takes effect when that source's 3D model path check starts. The skip is logged and saved with the scan, the next start says so, and Rescan does the full check.
- **Two columns**: Symbols (left) and Footprints (right), grouped by source (Custom, WurthElektronik).
- **Footprint selection is driven by symbols**: checking/unchecking a symbol auto-selects/deselects its linked footprints. Sync is scoped per source — changing Custom symbols only affects Custom footprints.
- **Select All / Deselect All**: applies to all symbols, then recalculates footprints via the filter.
- **Warnings**: orange text for symbols with missing footprint references. Cross-references check both the repo and KiCad's default libraries.
- **Right-click**: Expand All / Collapse All context menu on both trees. Right-clicking a library row also offers **Rescan this library**, which re-reads just that library (and, for a footprint library, the Atomic_ symbol libraries that link to it) and keeps the check boxes.
- **Saved scan**: stored in `%APPDATA%/KiCadExtLibManager/scan_cache/` (one file per repository folder, beside `settings.ini`, never inside the repo). Safe to delete; the next start then runs the full scan.
- **User Guide**: `F1` or Help > User Guide opens it in its own window, which stays open beside the other windows. It reopens on the page or section you last chose, scrolled to its heading (saved beside `settings.ini`, also after a restart). The import window's Help and `F1` open it on Importing Parts without changing that saved place; the main window's Help and `F1` then bring it back to that place, also while it is still open. If it is already open on that place, it is only brought to the front.
- **Migrate to Atomic Libraries...** (`Ctrl+Shift+M`): offered while `Custom/` still has a v1-named (non-`Atomic_`) symbol or footprint library, or a `.bak` file; otherwise greyed out with a tooltip explaining there is nothing to migrate. Refuses while `Custom` has uncommitted files. Tags `Custom` `pre-atomic` before writing. Shows a part list grouped by target library with a failure strip for every remaining atomic-rule problem and for every library that is only a guess (until you pick a library for that part; the part list marks guessed and suggested libraries, and a weak match on part numbers yields to the part's description) and a draft that is saved and restored; Run Migration stays disabled until the strip is empty. It runs as one transaction, then opens a Result view with the old -> new map (also saved as `Custom/MIGRATION-ATOMIC.md`), the destination folder for the library tables with a Browse... button (the main window's Destination changes with it; a missing or blank folder is pointed out), a Generate Tables button whose outcome is shown under the buttons, a commit step, and a Pin Atomic Libraries in KiCad button. The migration window is window-modal, so it blocks the main window while open.
- **Pin Atomic Libraries in KiCad...** (`Ctrl+Shift+K`): pins every `Atomic_` symbol library and `Atomic_Footprints` at the top of KiCad's library lists, and adds the `MPN` and `Manufacturer` columns right after Description (removing a stray `MANUFACTURER` column). Shows old -> new before writing and backs up the KiCad config files first. Refuses from a git worktree or from a checkout other than the one KiCad's `KICAD_LIB_GITHUB` names.
- **Wrong checkout** (D-26): when KiCad's `KICAD_LIB_GITHUB` names another folder than the one this app runs from, Generate Tables and Install Part still write but show an amber warning naming both folders (KiCad will not see the new libraries or parts until they exist in the folder KiCad reads), while the migration's Run and Pin Atomic Libraries in KiCad refuse outright, naming both folders and saying to run the app from the folder KiCad reads or fix `KICAD_LIB_GITHUB` in KiCad Preferences > Configure Paths. Nothing is said when the variable is not set or there's no KiCad config to read.

### Menu Shortcuts
- `Ctrl+G` — Generate Tables
- `Ctrl+R` — Restore Backup (paired sym + fp)
- `Ctrl+K` — Set KiCad Path (rescans after change)
- `Ctrl+Shift+M` — Migrate to Atomic Libraries...
- `Ctrl+Shift+K` — Pin Atomic Libraries in KiCad...
- `Ctrl+Q` — Exit

## Adding a New Library Submodule
```
git submodule add <repo-url> <VendorName>/<LibName>
```
Then rerun the GUI to scan and generate updated tables.

## Git Workflow
- Always commit submodule changes separately (cd into submodule, commit, push, then update parent ref)
- Use descriptive commit messages with component category context
- `.gitignore` excludes: generated `sym-lib-table`/`fp-lib-table`, `env/`, `venv/`, `.venv/`, `__pycache__/`
