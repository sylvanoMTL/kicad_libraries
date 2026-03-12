# CLAUDE.md

## Project Overview
KiCad library management repo that aggregates open-source and custom libraries via git submodules, with a PySide6 GUI for generating KiCad library tables.

## Repository Structure
- `Custom/` — submodule: `sylvanoMTL/kicad_custom_library` (personal parts)
- `WurthElektronik/KiCad-Library/` — submodule: open-source Wurth library
- `kicad_lib_manager.py` — PySide6 GUI entry point
- `kicad_lib_manager/` — GUI package (scanner, table generator, widgets)
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

## Known Issues
- Some Custom symbols still reference old footprint library names from before the rename (e.g., `GCT_USB4056-03-A_REVA2` instead of `Connector_USB_GCT`). These show as orange warnings in the GUI. Fix by editing the Footprint property in KiCad Symbol Editor.
- `USB4730-GF-A_REVA.kicad_sym` and `USB4745-03-A_REVA.kicad_sym` need merging into `Connector_USB_GCT.kicad_sym`

## Python Environment
- Use `py -m venv env` (Windows CPython from python.org, NOT MSYS2 Python) — PySide6 requires standard Windows Python
- Activate: `.\env\Scripts\activate` (PowerShell)
- Dependencies: `pip install PySide6`

## Running the GUI
```
.\env\Scripts\python.exe kicad_lib_manager.py
```
The GUI has two columns (Symbols left, Footprints right). Checking a symbol auto-selects linked footprints. Right-click for Expand/Collapse All.

## Adding a New Library Submodule
```
git submodule add <repo-url> <VendorName>/<LibName>
```
Then rerun the GUI to scan and generate updated tables.

## Git Workflow
- Always commit submodule changes separately (cd into submodule, commit, push, then update parent ref)
- Use descriptive commit messages with component category context
- `.gitignore` excludes: generated `sym-lib-table`/`fp-lib-table`, `env/`, `venv/`, `.venv/`, `__pycache__/`
