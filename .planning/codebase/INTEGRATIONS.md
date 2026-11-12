---
last_mapped_commit: 3353ce8161c4870e85b50fc8d607d41bb942c796
last_mapped_at: 2026-10-18
---
# External Integrations

**Analysis Date:** 2026-10-18

## APIs & External Services

**Network APIs:**
- None. No HTTP, REST, GraphQL, or socket client code exists in the in-scope files (`kicad_lib_manager.py`, `kicad_lib_manager/**`, `generate_lib_tables.py`). No `requests`, `urllib`, or `http` imports were found.
- Hyperlinks only: `kicad_lib_manager/main_window.py` (About dialog) and `kicad_lib_manager/widgets/help_dialog.py` link to `https://github.com/sylvanoMTL/kicad_libraries`. These are displayed as rich text and are not fetched by the app.

**Local KiCad application (file-level integration):**
- The app does not call KiCad's API or launch KiCad. It reads and writes KiCad's on-disk configuration and library files.
  - Reads/writes `kicad_common.json` in the KiCad user config directory, under `environment.vars`, via `sync_kicad_path_vars()` in `kicad_lib_manager/library_scanner.py`. Sets `KICAD_LIB_GITHUB` and `CUSTOM_3DMODEL_DIR`. Restart of KiCad is required for changes to apply (message emitted by the app).
  - Writes generated `sym-lib-table` and `fp-lib-table` into the repo root and/or the user-selected destination folder (`write_tables` in `kicad_lib_manager/table_generator.py`).
  - Reads default KiCad footprint nicknames from the installed KiCad footprint folder (`get_kicad_default_fp_nicknames` in `library_scanner.py`), used for cross-reference warnings.
  - Parses `.kicad_sym` symbol files and `.kicad_mod` / `.pretty` footprint libraries from the repo (`library_scanner.py`), using regex on `(property "Footprint" ...)` and `(model ...)`.

**Git submodule sources (declared, not accessed by app code):**
- `.gitmodules` declares two remote library sources:
  - `Custom` -> `https://github.com/sylvanoMTL/kicad_custom_library.git` (personal parts)
  - `WurthElektronik/KiCad-Library` -> `https://github.com/WurthElektronik/KiCad-Library.git` (open-source Wurth library)
- These are fetched by git during `git clone --recurse-submodules` or `git submodule update --remote --merge` (README.md). The Python app does not perform the fetch.

## Data Storage

**Databases:**
- None. No database driver, ORM, or SQL usage is present.

**File Storage:**
- Local filesystem only.
  - Library source files: repo root `Custom/` and `WurthElektronik/KiCad-Library/` (scanned, excluded directories: `env`, `venv`, `.venv`, `.git`, `.claude`, `__pycache__` per `SKIP_DIRS` in `library_scanner.py`).
  - Generated tables: `sym-lib-table`, `fp-lib-table` (git-ignored).
  - Backups: paired `*_backup_*` files created by `table_generator.py`, restored via `restore_backup_pair` and `kicad_lib_manager/widgets/backup_dialog.py`.
  - App settings: `QSettings` INI file (see below).
  - KiCad footprint cache: `fp-info-cache` is listed in `.gitignore` but no code in scope references it.

**Caching:**
- None. No cache service. The scan result is held in memory in `ScanResult` (`kicad_lib_manager/models.py`) for the session.

## Authentication & Identity

**Auth Provider:**
- Not applicable. The app is a local desktop tool with no user accounts, tokens, or credential handling.
- No secrets are read by the in-scope code. `.gitignore` excludes `env/`, `.claude/`, and backup/lock artifacts.

## Monitoring & Observability

**Error Tracking:**
- None. No Sentry, Rollbar, or similar SDK is imported.

**Logs:**
- In-app only. `kicad_lib_manager/widgets/log_panel.py` provides a color-coded `QTextEdit` (info, warning, error, success) with timestamps from `datetime`. Messages come from scan, generate, and sync operations in `main_window.py`.
- No log files are written to disk. Errors surface via `QMessageBox` (`main_window.py`) and `ScanWorker.error` signal.

## Platform / OS Integrations

**OS environment:**
- `APPDATA` environment variable (Windows) locates the KiCad config directory (`find_kicad_config_dir` in `library_scanner.py`).
- `sys.platform` branches for `win32`, `darwin`, and Linux paths: KiCad config (`%APPDATA%\kicad`, `~/Library/Preferences/kicad`, `~/.config/kicad`) and KiCad footprints (`C:/Program Files/KiCad`, `/Applications/KiCad`, `/usr/share/kicad`).
- Native file picker via `QFileDialog.getExistingDirectory` (`main_window.py`) for the KiCad footprints folder and the destination folder.

## CI/CD & Deployment

**Hosting:**
- Not applicable. No server deployment. Distribution is the git repository itself.

**CI Pipeline:**
- None detected. No `.github/workflows`, `.gitlab-ci.yml`, or similar file was found in scope.

## Environment Configuration

**Required environment variables:**
- None required by the application.
- `APPDATA` (Windows, OS-provided) is read when locating KiCad config.
- The KiCad-side variables the app manages (not read by the app): `KICAD_LIB_GITHUB` (repo root) and `CUSTOM_3DMODEL_DIR` (`<repo>/Custom/3DModels`). `WE_3DMODEL_DIR` is used by the Wurth library per CLAUDE.md and is not set by this app.

**Secrets location:**
- Not applicable. No secrets are stored or required. Note: a `.env` file is not referenced by any in-scope code. Its presence was not checked, and no contents were read.

## Webhooks & Callbacks

**Incoming:**
- None.

**Outgoing:**
- None.

---

*Integration audit: 2026-10-18*
