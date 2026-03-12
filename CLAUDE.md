# CLAUDE.md

## Project Overview
KiCad library management repo that aggregates open-source and custom libraries via git submodules, with a PySide6 GUI for generating KiCad library tables.

## Repository Structure
- `Custom/` — submodule: `sylvanoMTL/kicad_custom_library` (personal parts)
- `WurthElektronik/KiCad-Library/` — submodule: open-source Wurth library
- `kicad_lib_manager.py` — PySide6 GUI entry point
- `kicad_lib_manager/` — GUI package (scanner, table generator, widgets)
- `generate_lib_tables.py` — CLI script for table generation (legacy, GUI preferred)

## Key Conventions
- **Library naming**: `<Type>_<SubCategory>_<Manufacturer>` (e.g., `IC_Battery_Charger_TI`, `Connector_USB_GCT`)
- **KiCad path variable**: `${KICAD_LIB_GITHUB}` for library paths, `${CUSTOM_3DMODEL_DIR}` for 3D models
- **Python env**: Use `py -m venv env` (Windows CPython from python.org, NOT MSYS2 Python) — PySide6 requires standard Windows Python
- **Activate**: `.\env\Scripts\activate` (PowerShell) or `source env/bin/activate` (bash)

## Running the GUI
```
.\env\Scripts\python.exe kicad_lib_manager.py
```

## Adding a New Library Submodule
```
git submodule add <repo-url> <VendorName>/<LibName>
```
Then rerun the GUI to scan and generate updated tables.

## Commits
- Always commit submodule changes separately (cd into submodule, commit, push, then update parent ref)
- Use descriptive commit messages with component category context
