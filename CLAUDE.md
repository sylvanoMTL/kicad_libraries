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
- `generate_lib_tables.py` — CLI script for table generation (legacy, GUI preferred)

## KiCad Path Variables
These must be set in KiCad: Preferences > Configure Paths:
- `KICAD_LIB_GITHUB` — points to this repo root (e.g., `C:\Git_Repo_Clones\Kicad_Libraries`)
- `CUSTOM_3DMODEL_DIR` — points to `Custom/3DModels/` for custom 3D step files
- `WE_3DMODEL_DIR` — used by WurthElektronik footprints (set by their library)

## Library Naming Convention
Format: `<Type>_<SubCategory>_<Manufacturer>`

Examples:
- `IC_Battery_Charger_TI`, `IC_DCDC_Buck_TI`, `IC_LDO_TI`
- `Connector_USB_GCT`, `Connector_FFC_GCT`
- `Capacitor_MLCC_Murata`, `Inductor_Power_TDK`
- `Oscillator_TCXO_Abracon`

Symbol and footprint folder names must match (e.g., `Connector_USB_GCT.kicad_sym` + `Connector_USB_GCT.pretty/`).

## Importing from SnapEDA
1. Download the .kicad_sym and .kicad_mod files
2. Move the .kicad_mod into the appropriate `<Type>_<SubCategory>_<Manufacturer>.pretty/` folder
3. Add the symbol to the matching .kicad_sym file via KiCad Symbol Editor (copy/paste)
4. Fix 3D model paths to use `${CUSTOM_3DMODEL_DIR}/<filename>.step`
5. Commit in the Custom submodule first, then update parent repo

## Python Environment
- Use `py -m venv env` (Windows CPython from python.org, NOT MSYS2 Python) — PySide6 requires standard Windows Python
- Activate: `.\env\Scripts\activate` (PowerShell)
- Dependencies: `pip install PySide6`

## Running the GUI
```
.\env\Scripts\python.exe kicad_lib_manager.py
```

### GUI Behavior
- **Startup**: auto-detects KiCad installation for default footprint cross-referencing. If not found, prompts the user to select the footprints folder.
- **Two columns**: Symbols (left) and Footprints (right), grouped by source (Custom, WurthElektronik).
- **Footprint selection is driven by symbols**: checking/unchecking a symbol auto-selects/deselects its linked footprints. Sync is scoped per source — changing Custom symbols only affects Custom footprints.
- **Select All / Deselect All**: applies to all symbols, then recalculates footprints via the filter.
- **Warnings**: orange text for symbols with missing footprint references. Cross-references check both the repo and KiCad's default libraries.
- **Right-click**: Expand All / Collapse All context menu on both trees.

### Menu Shortcuts
- `Ctrl+G` — Generate Tables
- `Ctrl+R` — Restore Backup (paired sym + fp)
- `Ctrl+K` — Set KiCad Path (rescans after change)
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
