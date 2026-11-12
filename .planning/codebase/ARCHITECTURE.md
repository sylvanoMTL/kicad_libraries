---
last_mapped_commit: 3353ce8161c4870e85b50fc8d607d41bb942c796
last_mapped_at: 2026-10-18
---
<!-- refreshed: 2026-10-18 -->

# Architecture

**Analysis Date:** 2026-10-18

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                 Entry points (CLI / GUI launcher)                    │
│  `kicad_lib_manager.py`            `generate_lib_tables.py` (legacy) │
└───────────────┬─────────────────────────────────┬───────────────────┘
                │                                 │ (standalone, no
                ▼                                 │  package imports)
┌─────────────────────────────────────────────────┐ │
│  Presentation: `kicad_lib_manager/main_window.py`│ │
│  MainWindow · ScanWorker (QThread) · menus       │ │
├──────────────┬──────────────┬───────────────────┤ │
│ `widgets/`   │ `widgets/`   │ `widgets/`        │ │
│ library_table│ log_panel    │ backup_dialog     │ │
│ help_dialog  │              │                   │ │
└──────┬───────┴──────┬───────┴─────────┬─────────┘ │
       │              │                 │           │
       ▼              ▼                 ▼           ▼
┌──────────────────────────┐  ┌──────────────────────────────────┐
│ Domain model             │  │ Services                         │
│ `kicad_lib_manager/      │◄─┤ `library_scanner.py` (scan, parse,│
│   models.py`            │  │   cross-reference, KiCad config) │
└──────────────────────────┘  │ `table_generator.py` (merge,     │
                              │   write, backup, restore)        │
┌──────────────────────────┐  └──────────────┬───────────────────┘
│ Persistence              │◄───────────────┘
│ `settings.py` (QSettings)│
└──────────────────────────┘
       │
       ▼  filesystem (read: repo `.kicad_sym` / `.pretty`, KiCad install;
          write: `sym-lib-table`, `fp-lib-table`, `*_backup_N`,
          KiCad `kicad_common.json`)
```

## Pattern Overview

**Overall:** Layered desktop application (PySide6 / Qt Widgets) with a
thin presentation layer over plain-Python services. Services are pure
functions over `pathlib.Path` and return data (dataclasses or message
lists); the GUI owns all orchestration and user feedback.

**Key Characteristics:**
- Single process, single window. The only background work is one `QThread`
  (`ScanWorker`) that performs the repository scan.
- Services do not import Qt, except `settings.py` (QSettings) and the
  `widgets/` package. `library_scanner.py` and `table_generator.py` are
  Qt-free and could be used headless.
- The domain model (`kicad_lib_manager/models.py`) is a set of mutable
  dataclasses. The UI mutates the `selected` flags on those objects directly
  (see Anti-Patterns).
- Output is communicated as human-readable strings (`list[str]` "messages")
  that the GUI routes into the `LogPanel` with a severity level. There is no
  structured error/result type for writes.
- A legacy standalone CLI (`generate_lib_tables.py`) duplicates the discovery
  logic rather than importing it. It is not used by the GUI.

## Layers

**Entry / Bootstrap:**
- Purpose: Create the `QApplication`, show the main window, run the event loop.
- Location: `kicad_lib_manager.py`
- Contains: `main()` only.
- Depends on: `kicad_lib_manager.main_window.MainWindow`, PySide6.
- Used by: Run directly (`.\env\Scripts\python.exe kicad_lib_manager.py`).

**Presentation (main window):**
- Purpose: Menu/toolbar actions, destination selection, scan lifecycle,
  generate/restore orchestration, KiCad path prompts, geometry persistence.
- Location: `kicad_lib_manager/main_window.py`
- Contains: `MainWindow` (QMainWindow), `ScanWorker` (QThread), module
  constant `REPO_ROOT` (resolved from `Path(__file__).parent.parent`) and
  `APP_TITLE`.
- Depends on: `library_scanner`, `table_generator`, `models`, `settings`,
  and all widgets.
- Used by: `kicad_lib_manager.py`.

**Presentation (widgets):**
- Purpose: Reusable Qt components with no orchestration logic beyond their
  own state.
- Location: `kicad_lib_manager/widgets/`
- Contains:
  - `library_table.py` — `LibraryTableWidget`: two `QTreeWidget`s (Symbols |
    Footprints), grouped by source, with the symbol→footprint selection
    propagation rule.
  - `log_panel.py` — `LogPanel`: color-coded `QTextEdit`; levels `info`,
    `warning`, `error`, `success` (colors in `COLORS`).
  - `backup_dialog.py` — `BackupDialog`: lists paired backups via
    `table_generator.list_backup_pairs` and returns `selected_backup_num` /
    `selected_folder`.
  - `help_dialog.py` — `HelpDialog`: static HTML user guide (`CSS` and
    `_wrap()` helpers). No data dependencies.
- Depends on: `..models` (library_table), `..table_generator` (backup_dialog).
- Used by: `main_window.py` only.

**Domain model:**
- Purpose: Shared data carriers for a scan.
- Location: `kicad_lib_manager/models.py`
- Contains: `FootprintRef`, `SymbolLibrary`, `FootprintLibrary`, `ScanResult`.
- Depends on: stdlib `dataclasses` only.
- Used by: all services and widgets.

**Services — scanning:**
- Purpose: Discover libraries in the repo, parse footprint references out of
  symbol files, cross-check them against repo and KiCad default libraries,
  check 3D model paths, locate KiCad's install and user config.
- Location: `kicad_lib_manager/library_scanner.py`
- Contains: `scan_all()` (top-level orchestrator), `find_footprint_libs()`,
  `find_symbol_libs()`, `_parse_footprint_refs()`, `cross_reference()`,
  `check_3d_model_paths()`, `find_kicad_footprint_dir()`,
  `find_kicad_config_dir()`, `sync_kicad_path_vars()`,
  `get_kicad_default_fp_nicknames()`, `_determine_source()`.
- Depends on: `models`, stdlib only.
- Used by: `main_window.py` (`scan_all`, `find_kicad_footprint_dir`,
  `sync_kicad_path_vars`).

**Services — table generation:**
- Purpose: Produce KiCad `sym-lib-table` / `fp-lib-table` content by merging
  the current selection with preserved external entries, write files, back up
  previous versions, and restore backup pairs.
- Location: `kicad_lib_manager/table_generator.py`
- Contains: `parse_lib_table()`, `generate_sym_lib_table()`,
  `generate_fp_lib_table()`, `_merge_table()`, `_check_nickname_collisions()`,
  `backup_existing()`, `write_tables()`, `list_backup_pairs()`,
  `restore_backup()`, `restore_backup_pair()`, `MergeResult`.
- Depends on: `models`, stdlib only.
- Used by: `main_window.py`, `widgets/backup_dialog.py`.

**Persistence (user settings):**
- Purpose: Remember KiCad footprint dir, destination history (max 10), and
  window geometry.
- Location: `kicad_lib_manager/settings.py`
- Contains: `get_settings()` (QSettings, IniFormat, UserScope, org/app
  `KiCadExtLibManager`) and typed `load_*`/`save_*`/`add_dest_to_history`
  helpers.
- Depends on: PySide6 `QtCore`.
- Used by: `main_window.py`.

**Legacy CLI:**
- Purpose: Write `sym-lib-table` and `fp-lib-table` into the repo root with
  no merge, no backup, no GUI.
- Location: `generate_lib_tables.py`
- Contains: its own `find_symbol_libs`, `find_footprint_libs`,
  `generate_sym_lib_table`, `generate_fp_lib_table`, `main`.
- Depends on: stdlib only. Does not import `kicad_lib_manager`.
- Used by: manual invocation (`python generate_lib_tables.py`).

## Data Flow

### Primary Request Path: Startup scan

1. `kicad_lib_manager.py:main()` constructs `MainWindow` (`kicad_lib_manager/main_window.py`).
2. `MainWindow.__init__` restores geometry, builds menu and UI, then calls
   `_detect_kicad()` (may open a blocking `QFileDialog` if KiCad is not found),
   `_check_existing_tables()`, and `_start_scan()`.
3. `_start_scan()` creates a `QProgressDialog` and a `ScanWorker(REPO_ROOT, kicad_fp_dir)`
   and starts it.
4. `ScanWorker.run()` calls `library_scanner.scan_all(root, progress, kicad_fp_dir)`:
   footprint libs (`*.pretty` dirs) → symbol libs (`*.kicad_sym`, with
   `_parse_footprint_refs`) → `cross_reference` (sets `FootprintRef.found_in_repo`,
   emits warnings) → `check_3d_model_paths` (scans `*.kicad_mod`).
5. The worker emits `progress(msg, pct)` and `finished(ScanResult)`. The UI
   thread receives these via Qt signals (queued connection).
6. `MainWindow._on_scan_finished` runs `_apply_existing_selection()` (reads the
   destination's current tables and pre-checks matching nicknames), then
   `LibraryTableWidget.populate(result)`, then logs warnings.

### Primary Write Path: Generate Tables (Ctrl+G)

1. `MainWindow._on_generate()` filters `ScanResult` by `selected`.
2. `table_generator.write_tables(dest, sym_libs, fp_libs)`:
   - `_check_nickname_collisions()` for each table (returns warning strings).
   - `generate_*_lib_table()` builds merged text: preserved entries whose URI
     lacks `${KICAD_LIB_GITHUB}/` + new entries for selected libs.
   - `backup_existing()` copies the old file to `<name>_backup_<N+1>`.
   - Writes the new file and returns human-readable messages.
3. `MainWindow` logs each message, then `sync_kicad_path_vars(REPO_ROOT)`
   writes `KICAD_LIB_GITHUB` and `CUSTOM_3DMODEL_DIR` into KiCad's
   `kicad_common.json`.
4. `settings.add_dest_to_history()` persists the destination.

### Selection Propagation Flow (in the widget)

1. User toggles a symbol checkbox → `LibraryTableWidget._on_sym_item_changed`
   sets `SymbolLibrary.selected` (or all children for a group header).
2. The widget calls `_sync_footprint_selection(source)`: the needed footprint set
   is the union of `footprint_refs.library_name` over all selected symbols
   (across all sources). Only footprint items whose `source` matches the
   changed source are re-checked, and `FootprintLibrary.selected` is updated.
3. Footprint toggles only update their own `selected` flag
   (`_on_fp_item_changed`); they do not propagate back to symbols.

### Restore Flow

1. `MainWindow._on_restore_backup()` opens `BackupDialog` for the current
   destination.
2. `BackupDialog._scan()` → `table_generator.list_backup_pairs()`.
3. On accept, `restore_backup_pair(folder, num)` backs up the current files and
   copies the chosen `_backup_<num>` files over them.

**State Management:**
- Scan results live on `MainWindow._scan_result` and are shared by reference
  with `LibraryTableWidget._sym_libs` / `_fp_libs`.
- Selection state lives in the model objects (`selected` fields), mirrored
  into `QTreeWidgetItem` check states.
- Persistent state lives only in QSettings (`settings.py`) and on disk
  (`sym-lib-table`, `fp-lib-table`, backups in the destination folder).

## Key Abstractions

**`ScanResult`:**
- Purpose: Single snapshot of a repository scan (symbol libs, footprint libs,
  warnings).
- Examples: `kicad_lib_manager/models.py`, produced by
  `library_scanner.scan_all`.
- Pattern: Plain dataclass as a transfer object across the thread boundary.

**`SymbolLibrary` / `FootprintLibrary`:**
- Purpose: One `.kicad_sym` file or one `.pretty` folder, identified by
  `nickname` (file/folder stem) and `rel_path` (repo-relative, POSIX).
- Examples: `kicad_lib_manager/models.py`.
- Pattern: Mutable dataclass; `source` is the first path segment of
  `rel_path` (e.g. `Custom`, `WurthElektronik`) and is the grouping key for the UI.

**`FootprintRef`:**
- Purpose: A `Library:Footprint` reference parsed from a symbol's
  `(property "Footprint" ...)`, with `found_in_repo` set by cross-referencing.
- Examples: `_parse_footprint_refs` in `library_scanner.py`.
- Pattern: Value object; de-duplicated per symbol file.

**`MergeResult`:**
- Purpose: Result of generating one table: content, counts, removed nicknames.
- Examples: `kicad_lib_manager/table_generator.py`.
- Pattern: Lightweight class with `__slots__`.

**Managed vs. external table entries:**
- Purpose: Entries whose URI contains `${KICAD_LIB_GITHUB}/` (`_MANAGED_MARKER`)
  are owned by this tool and are replaced on every generate. All other entries
  are preserved verbatim.
- Examples: `_merge_table`, `_apply_existing_selection` in `main_window.py`.
- Pattern: Marker-based ownership; the marker string is imported across modules
  as a private name (`_MANAGED_MARKER`).

## Entry Points

**GUI application:**
- Location: `kicad_lib_manager.py` (`main()`).
- Triggers: Manual run of `kicad_lib_manager.py` with the project venv.
- Responsibilities: Create `QApplication`, show `MainWindow`, exit with Qt's return code.

**Legacy CLI:**
- Location: `generate_lib_tables.py` (`main()`).
- Triggers: `python generate_lib_tables.py` from the repo root.
- Responsibilities: Regenerate root-level `sym-lib-table` and `fp-lib-table`
  with every discovered library (no selection, no merge, no backup).

**Module entry (indirect):**
- `kicad_lib_manager/main_window.py` `MainWindow` is the only object created by
  the GUI entry point.

## Architectural Constraints

- **Threading:** Qt main thread for all widgets. One `ScanWorker` QThread
  (`main_window.py`) runs `scan_all`; it communicates only via `progress`,
  `finished`, and `error` signals. Services called from the worker must not
  touch widgets. `_on_scan_finished` and `_on_scan_error` call `self._worker.wait()`
  and clear `self._worker`; no guard prevents starting a second scan while one
  is running (`_on_rescan` and `_on_set_kicad_path` call `_start_scan()` unconditionally).
- **Global state:** `REPO_ROOT` is a module-level constant in
  `kicad_lib_manager/main_window.py`, derived from the file location, so the
  tool assumes it lives at the repository root. `MANAGED` marker constants
  (`_MANAGED_MARKER` in `table_generator.py`, `ENV_VAR`) and `SKIP_DIRS` in
  `library_scanner.py` are module-level and shared by convention.
- **Circular imports:** None detected inside the package. Dependency direction is
  `main_window` → `widgets`/services → `models`.
- **Startup blocking:** `_detect_kicad()` runs synchronously in the constructor
  and may show a modal folder picker before the window is interactive.
- **Filesystem coupling:** Services assume the repo uses `.kicad_sym` files
  and `.pretty` folders, and that KiCad path variables are named
  `KICAD_LIB_GITHUB` and `CUSTOM_3DMODEL_DIR` (see `sync_kicad_path_vars`).
- **Platform paths:** KiCad discovery is hard-coded per platform in
  `library_scanner.find_kicad_footprint_dir()` (`C:/Program Files/KiCad`
  on Windows) and `find_kicad_config_dir()` (`%APPDATA%/kicad`).
- **Consumed data (not analyzed):** Symbol and footprint libraries under
  `Custom/` and `WurthElektronik/` are read as input only; their internal
  structure is out of scope for this map.

## Anti-Patterns

### Widgets mutate domain model `selected` flags directly

**What happens:** `LibraryTableWidget._on_sym_item_changed`,
`_sync_footprint_selection`, `_set_all_check_state` and `_on_fp_item_changed`
write `lib.selected` on `SymbolLibrary` / `FootprintLibrary` objects that are
also held by `MainWindow._scan_result`.
**Why it's wrong:** Selection logic is split between the widget and the
main window (`_on_generate` reads `selected` from the model). Changing the
rule requires editing the widget, and the model cannot be tested without Qt.
**Do this instead:** Keep the propagation rule in a Qt-free function (for example
a `compute_footprint_selection(sym_libs) -> set[str]` in `library_scanner.py` or a
new `selection.py`), and have the widget call it and update only checkbox state.
Reference: `library_table.py` `_sync_footprint_selection`.

### Cross-module import of a private name

**What happens:** `main_window.py` imports `_MANAGED_MARKER` from
`table_generator.py` and uses it to decide which pre-existing entries are
managed.
**Why it's wrong:** The leading underscore marks it private, and the
ownership rule is duplicated in `table_generator._merge_table` and
`_check_nickname_collisions`.
**Do this instead:** Expose a public helper such as
`table_generator.is_managed_entry(entry)` and use it from both the merge logic
and `_apply_existing_selection`. Reference: `main_window.py` `_apply_existing_selection`.

### Duplicated discovery logic in the legacy CLI

**What happens:** `generate_lib_tables.py` re-implements `find_symbol_libs` and
`find_footprint_libs` without the `SKIP_DIRS` filter used in
`library_scanner.py`, and writes a different output (no merge, no backup).
**Why it's wrong:** The two paths can disagree on which libraries exist. The CLI
will also pick up `.pretty` / `.kicad_sym` files inside `env/` or `.venv/` if
present.
**Do this instead:** Either import `library_scanner` from the CLI (it has no Qt
dependency) or retire the CLI once the GUI covers its use case, as the CLI
docstring already presents it as legacy.

### Blocking modal dialog inside the constructor

**What happens:** `MainWindow._detect_kicad()` calls `QFileDialog.getExistingDirectory`
during `__init__`, before scanning.
**Why it's wrong:** The window is not yet shown and the scan has not started, so the
user is prompted before any context is visible.
**Do this instead:** Defer the prompt to a `QTimer.singleShot(0, ...)` after
`show()`, or let the scan proceed with `kicad_fp_dir=None` and surface a warning in
the log that offers Ctrl+K.

## Error Handling

**Strategy:** Errors are converted to log messages rather than exceptions at the
UI boundary. Service functions catch `OSError` / `UnicodeDecodeError` /
`json.JSONDecodeError` locally and return empty results or message strings.

**Patterns:**
- Reads return empty collections on failure: `parse_lib_table` returns `[]`;
  `_parse_footprint_refs` returns `[]`; `check_3d_model_paths` skips unreadable files.
- Write and config failures return a message string prefixed with
  `Failed to ...` (`sync_kicad_path_vars`), which `main_window.py` classifies as
  a warning by substring matching (`"Failed"`, `"Could not"`, `"not found"`).
- The scan worker catches all `Exception` and emits `error(str)`;
  `_on_scan_error` logs it and closes the progress dialog.
- `write_tables` does not catch exceptions around `path.write_text`; an `OSError`
  there propagates to the Qt slot.

## Cross-Cutting Concerns

**Logging:** `LogPanel.log(message, level)` in `widgets/log_panel.py`. There is no
Python `logging` usage. Level is chosen in `main_window.py` by string matching on
the message content (`"removed" in msg`, `"Failed" in msg`).

**Validation:** Minimal. Footprint reference values must contain `:` to be parsed
(`_parse_footprint_refs`). Destination folder existence is checked in
`_on_generate` and `_check_existing_tables`.

**Authentication:** Not applicable (local desktop tool).

**Persistence:** QSettings (`settings.py`) with IniFormat in the user scope.

---

*Architecture analysis: 2026-10-18*
