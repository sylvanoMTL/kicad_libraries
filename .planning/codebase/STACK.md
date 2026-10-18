---
last_mapped_commit: 3353ce8161c4870e85b50fc8d607d41bb942c796
last_mapped_at: 2026-10-18
---
# Technology Stack

**Analysis Date:** 2026-10-18

## Languages

**Primary:**
- Python 3.14 (venv built from `C:\Users\sylvain\AppData\Local\Python\pythoncore-3.14-64`, per `env/pyvenv.cfg`) - all application code: `kicad_lib_manager.py`, `generate_lib_tables.py`, `kicad_lib_manager/**/*.py`

**Secondary:**
- Not applicable. No JavaScript, SQL, shell, or other source languages are used by the in-scope code.
- KiCad file formats handled as text (parsed with regex, not a Python parser): `sym-lib-table`, `fp-lib-table` (S-expression), `.kicad_sym`, `.kicad_mod`, `.pretty/` directories, `kicad_common.json` (JSON, read and written). See `kicad_lib_manager/table_generator.py` and `kicad_lib_manager/library_scanner.py`.

## Runtime

**Environment:**
- CPython 3.14.x (Windows, python.org/Store build). CLAUDE.md requires standard Windows CPython, not MSYS2 Python, because PySide6 needs it.
- Code uses modern typing syntax (`Path | None`, `list[str]`, `dict` generics), so Python 3.10+ is the practical minimum.
- Platform branches exist for `win32`, `darwin`, and Linux in `kicad_lib_manager/library_scanner.py` (`find_kicad_config_dir`, `find_kicad_footprint_dir`) and `kicad_lib_manager/settings.py` (docstring lists per-OS paths).

**Package Manager:**
- pip (per CLAUDE.md: `pip install PySide6`)
- Lockfile: missing. No `requirements.txt`, `pyproject.toml`, `setup.py`, `setup.cfg`, or `Pipfile` exists at repo root.
- Virtual environment: `env/` at repo root (git-ignored via `.gitignore`). Installed packages observed in `env/Lib/site-packages`: PySide6 6.12.0, pyside6_essentials / pyside6_addons / pyside6_pdf / pyside6_webengine 6.12.0.140, shiboken6 6.12.0.

## Frameworks

**Core:**
- PySide6 6.12.0 (Qt for Python) - the entire GUI. Imported in `kicad_lib_manager.py`, `kicad_lib_manager/main_window.py`, `kicad_lib_manager/settings.py`, and all modules under `kicad_lib_manager/widgets/`.
  - Qt modules actually imported: `QtWidgets` (QMainWindow, QTreeWidget-based `LibraryTableWidget`, QFileDialog, QMessageBox, QProgressDialog, QComboBox), `QtCore` (QThread, Signal, Qt, QSettings, QByteArray), `QtGui` (QAction, QKeySequence, QCloseEvent, QBrush, QColor, QFont).
  - Threading: `ScanWorker(QThread)` in `kicad_lib_manager/main_window.py` runs `scan_all` off the UI thread and emits `progress`, `finished`, `error` signals.

**Testing:**
- Not detected. No test framework, test directory, or test config is present in scope.

**Build/Dev:**
- Not detected. No build tool, bundler, packaging (PyInstaller, etc.), or linter/formatter config found at repo root. `.claude/` exists but is git-ignored and was not analyzed.

## Standard Library Usage

Modules imported across in-scope code (no third-party dependencies beyond PySide6):
- `json` - read/write KiCad `kicad_common.json` (`kicad_lib_manager/library_scanner.py`)
- `os` - `os.environ["APPDATA"]`, `os.environ` lookups, path handling
- `re` - S-expression parsing for `(property "Footprint" ...)`, `(model ...)`, and `(lib (name ...)(type ...)(uri ...)...)` entries (`library_scanner.py`, `table_generator.py`)
- `shutil` - backup/copy of generated tables (`kicad_lib_manager/table_generator.py`)
- `sys` - `sys.platform` branching, `sys.argv`, `sys.exit`
- `pathlib.Path` - all filesystem access; `Path.home()` for non-Windows KiCad config
- `dataclasses` - models in `kicad_lib_manager/models.py`
- `datetime` - timestamps in `kicad_lib_manager/widgets/log_panel.py`
- `typing.Callable` - progress callbacks in `library_scanner.py`

## Key Dependencies

**Critical:**
- `PySide6` 6.12.0 - sole third-party dependency; the GUI cannot run without it. Installed via `pip install PySide6` (CLAUDE.md). Pinned version is not recorded anywhere in the repo, only in the local venv.

**Infrastructure:**
- None beyond the standard library and PySide6. No ORM, HTTP client, logging library, or config library is used.

## External Software Dependencies (runtime, not pip)

- KiCad (version-agnostic, auto-detected): the app reads the KiCad user config directory and default footprint library directory.
  - Windows config: `%APPDATA%\kicad\<version>\` (`find_kicad_config_dir` in `library_scanner.py`)
  - Windows default footprints: `C:/Program Files/KiCad/<version>/share/kicad/footprints` (`find_kicad_footprint_dir`)
  - Newest version folder is chosen by reverse-lexical sort of directory names.
- Git and git submodules: the library content is pulled as submodules declared in `.gitmodules` (`Custom` -> `sylvanoMTL/kicad_custom_library`, `WurthElektronik/KiCad-Library` -> `WurthElektronik/KiCad-Library`). The app itself does not invoke git (no `subprocess` use in scope).

## Configuration

**Environment:**
- No `.env` file or environment-variable loading is performed by the application. The app reads one OS variable: `APPDATA` (Windows) in `library_scanner.py`.
- KiCad path variables are written, not read, into KiCad's `kicad_common.json` under `environment.vars`:
  - `KICAD_LIB_GITHUB` = repo root (forward slashes)
  - `CUSTOM_3DMODEL_DIR` = `<repo>/Custom/3DModels`
  - Written by `sync_kicad_path_vars()` in `kicad_lib_manager/library_scanner.py`.
- `generate_lib_tables.py` and `table_generator.py` emit the token `${KICAD_LIB_GITHUB}` into generated tables (constant `ENV_VAR` in both files).
- Persistent app settings are stored via `QSettings` (IniFormat, UserScope, org/app `KiCadExtLibManager`/`settings`) in `kicad_lib_manager/settings.py`. Keys: `kicad_fp_dir`, `dest_history` (max 10 entries), `window/geometry`.
  - Windows: `%APPDATA%/KiCadExtLibManager/settings.ini`
  - Linux: `~/.config/KiCadExtLibManager/settings.ini`
  - macOS: `~/Library/Preferences/KiCadExtLibManager/settings.ini`

**Build:**
- No build configuration present.
- Launch command (CLAUDE.md): `.\env\Scripts\python.exe kicad_lib_manager.py`
- CLI alternative: `python generate_lib_tables.py` (stdlib only; imports `os` and `pathlib`).

**Ignored artifacts (`.gitignore`):** `sym-lib-table`, `fp-lib-table`, `env/`, `venv/`, `.venv/`, `__pycache__/`, `.claude/`, `*_backup_*`, KiCad lock/autosave files, `fp-info-cache`, `.planning/`.

## Platform Requirements

**Development:**
- Windows 11 (current workstation; Git Bash and PowerShell in use).
- Python 3.10+ with a standard CPython install (not MSYS2) to create `env/` via `py -m venv env`.
- PySide6 6.12.x installed into the venv.
- A local KiCad installation is optional but recommended: without it, default-footprint cross-referencing is skipped and the user is prompted for the footprints folder.

**Production:**
- No deployment target. The GUI runs locally on each user's machine; the repo itself is the artifact, consumed by KiCad via the generated library tables.

---

*Stack analysis: 2026-10-18*
