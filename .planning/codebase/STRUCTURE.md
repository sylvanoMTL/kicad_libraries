---
last_mapped_commit: 3353ce8161c4870e85b50fc8d607d41bb942c796
last_mapped_at: 2026-10-18
---
# Codebase Structure

**Analysis Date:** 2026-10-18

Scope: `kicad_lib_manager/`, `kicad_lib_manager.py`, `generate_lib_tables.py`.
The library submodules `Custom/` and `WurthElektronik/` and the untracked
`downloaded_examples/` are consumed as data only and are not analyzed.

## Directory Layout

```
[repo root]/
├── kicad_lib_manager.py         # GUI entry point (main())
├── generate_lib_tables.py       # Legacy standalone CLI (root sym/fp tables)
├── kicad_lib_manager/           # GUI package
│   ├── __init__.py              # Empty package marker
│   ├── main_window.py           # MainWindow, ScanWorker, REPO_ROOT, APP_TITLE
│   ├── library_scanner.py       # Repo scan, footprint-ref parsing, KiCad discovery
│   ├── table_generator.py       # Table merge/write, backups, restore
│   ├── models.py                # Dataclasses: FootprintRef, SymbolLibrary, FootprintLibrary, ScanResult
│   ├── settings.py              # QSettings wrapper (KiCad dir, history, geometry)
│   ├── __pycache__/             # Generated (not committed)
│   └── widgets/                 # Qt widgets used by MainWindow
│       ├── __init__.py          # Empty package marker
│       ├── library_table.py     # LibraryTableWidget (Symbols | Footprints trees)
│       ├── log_panel.py         # LogPanel (color-coded log)
│       ├── backup_dialog.py     # BackupDialog (restore backup pair)
│       ├── help_dialog.py       # HelpDialog (static HTML user guide)
│       └── __pycache__/         # Generated (not committed)
├── CLAUDE.md                    # Project instructions for AI tooling
├── Custom/                      # Submodule: personal libraries (data input)
└── WurthElektronik/KiCad-Library/  # Submodule: vendor library (data input)
```

Generated at runtime in the destination folder (not in the repo tree by the GUI):
`sym-lib-table`, `fp-lib-table`, `sym-lib-table_backup_N`, `fp-lib-table_backup_N`.
`generate_lib_tables.py` writes `sym-lib-table` and `fp-lib-table` into the repo root.

## Directory Purposes

**`kicad_lib_manager/`:**
- Purpose: All GUI application code, imported as a package via relative imports.
- Contains: Python modules for controller/window, services, model, settings, and `widgets/`.
- Key files: `main_window.py` (orchestration), `library_scanner.py` (discovery),
  `table_generator.py` (output).

**`kicad_lib_manager/widgets/`:**
- Purpose: Self-contained Qt components. Each file defines one widget class.
- Contains: `*.py` modules, each exporting one `QWidget`/`QDialog` subclass.
- Key files: `library_table.py` (selection rules), `log_panel.py` (`COLORS` map).

**Repo root (`.`):**
- Purpose: Launcher scripts and project configuration. The GUI computes `REPO_ROOT`
  as the parent of `kicad_lib_manager/`, so the package must stay one level below the root.
- Contains: `kicad_lib_manager.py`, `generate_lib_tables.py`, `CLAUDE.md`, `.gitignore`.

## Key File Locations

**Entry Points:**
- `kicad_lib_manager.py`: GUI launcher, `main()` creates `QApplication` and `MainWindow`.
- `generate_lib_tables.py`: legacy CLI, `main()` writes root-level tables.

**Configuration:**
- `kicad_lib_manager/settings.py`: QSettings keys `kicad_fp_dir`, `dest_history`,
  `window/geometry` (stored by Qt in the user settings location; see module docstring).
- `kicad_lib_manager/library_scanner.py`: `SKIP_DIRS` (excluded directory names) and
  the regex constants `FOOTPRINT_RE`, `MODEL_RE`.
- `kicad_lib_manager/table_generator.py`: `ENV_VAR` (`KICAD_LIB_GITHUB`) and `_MANAGED_MARKER`.
- `kicad_lib_manager/main_window.py`: `APP_TITLE`, `REPO_ROOT`.

**Core Logic:**
- `kicad_lib_manager/library_scanner.py`: `scan_all()` and helpers.
- `kicad_lib_manager/table_generator.py`: `write_tables()`, `_merge_table()`, backup/restore.
- `kicad_lib_manager/widgets/library_table.py`: symbol→footprint selection propagation.

**Testing:**
- Not present. No `tests/` directory and no test files in the scoped paths.

## Naming Conventions

**Files:**
- Modules: `snake_case.py` (e.g. `library_scanner.py`, `backup_dialog.py`).
- Top-level scripts: `snake_case.py` at repo root (`kicad_lib_manager.py`, `generate_lib_tables.py`).
- Widget modules are named after their class in snake_case: `LibraryTableWidget` → `library_table.py`,
  `BackupDialog` → `backup_dialog.py`.

**Directories:**
- Package directories: `snake_case` (`kicad_lib_manager`, `widgets`).

**Classes:** `PascalCase` (`MainWindow`, `ScanWorker`, `LibraryTableWidget`, `SymbolLibrary`).

**Functions and methods:** `snake_case`; Qt slots prefixed `_on_` (`_on_generate`,
`_on_scan_finished`, `_on_sym_item_changed`); private helpers prefixed `_`.

**Module constants:** `UPPER_SNAKE_CASE` (`REPO_ROOT`, `FOOTPRINT_RE`, `SKIP_DIRS`, `COLORS`).

**Imports:** Intra-package imports are relative (`from .models import ...`,
`from ..models import ...` inside `widgets/`). Entry scripts use absolute
package imports (`from kicad_lib_manager.main_window import MainWindow`).

## Where to Add New Code

**New GUI feature (menu action, toolbar button, handler):**
- Primary code: `kicad_lib_manager/main_window.py` (add `QAction` in `_build_menu`
  or a button in `_build_ui`, and an `_on_*` slot).
- Tests: no test location exists yet; create `tests/` at repo root if added.

**New reusable widget or dialog:**
- Implementation: `kicad_lib_manager/widgets/<snake_name>.py`, one class per file,
  and import it in `main_window.py`.

**New scanning rule or library type (e.g. a new KiCad file kind):**
- Discovery: `kicad_lib_manager/library_scanner.py` (add a `find_*_libs` function
  modeled on `find_symbol_libs`, and call it from `scan_all`).
- Data shape: `kicad_lib_manager/models.py`.

**New table format or merge rule:**
- Implementation: `kicad_lib_manager/table_generator.py`. Use `_format_entry` for
  output and `_merge_table` for preservation.

**New persisted user setting:**
- Implementation: `kicad_lib_manager/settings.py`, add a `load_*`/`save_*` pair using
  `get_settings()`.

**Pure logic that must not depend on Qt:**
- Put it in `kicad_lib_manager/library_scanner.py` or `table_generator.py` (or a new
  module in `kicad_lib_manager/`), not in `widgets/`.

**Utilities:**
- Shared helpers: no `utils` module exists. Place helpers in the service module that
  owns the concept (path handling → `library_scanner.py`).

## Special Directories

**`kicad_lib_manager/__pycache__/` and `kicad_lib_manager/widgets/__pycache__/`:**
- Purpose: Python bytecode cache.
- Generated: Yes.
- Committed: No (ignored by `.gitignore`).

**`env/`, `venv/`, `.venv/`:**
- Purpose: Local Python virtual environment (`py -m venv env`).
- Generated: Yes.
- Committed: No (ignored). Skipped by the scanner via `SKIP_DIRS`.

**Destination folder (user-chosen, default repo root):**
- Purpose: Holds generated `sym-lib-table` / `fp-lib-table` and `*_backup_N` files.
- Generated: Yes.
- Committed: `sym-lib-table` and `fp-lib-table` are ignored by `.gitignore`.

**`Custom/` and `WurthElektronik/`:**
- Purpose: Git submodules containing `.kicad_sym` and `.pretty` data consumed by the scanner.
- Generated: No (maintained as submodules).
- Committed: As submodule references in the parent repo.

---

*Structure analysis: 2026-10-18*
