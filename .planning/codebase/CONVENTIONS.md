---
last_mapped_commit: 3353ce8161c4870e85b50fc8d607d41bb942c796
last_mapped_at: 2026-10-18
---
# Coding Conventions

**Analysis Date:** 2026-10-18

## Naming Patterns

**Files:**
- Lowercase snake_case modules: `kicad_lib_manager/library_scanner.py`, `kicad_lib_manager/table_generator.py`, `kicad_lib_manager/widgets/backup_dialog.py`
- Widget modules live in `kicad_lib_manager/widgets/` and are named after the class they provide (`library_table.py` → `LibraryTableWidget`, `log_panel.py` → `LogPanel`, `backup_dialog.py` → `BackupDialog`, `help_dialog.py` → `HelpDialog`)
- Entry points at repo root: `kicad_lib_manager.py` (GUI), `generate_lib_tables.py` (legacy CLI)

**Functions:**
- snake_case throughout: `scan_all`, `find_symbol_libs`, `write_tables`, `restore_backup_pair` (`kicad_lib_manager/library_scanner.py`, `kicad_lib_manager/table_generator.py`)
- Module-private helpers are prefixed with a single underscore: `_collect_files`, `_in_skip_dir`, `_parse_footprint_refs`, `_determine_source` (`kicad_lib_manager/library_scanner.py`); `_merge_table`, `_format_entry`, `_check_nickname_collisions` (`kicad_lib_manager/table_generator.py`)
- Module-level constants that are shared across modules are re-exported with a leading underscore but still imported explicitly: `_MANAGED_MARKER` is imported into `kicad_lib_manager/main_window.py` from `kicad_lib_manager/table_generator.py`
- GUI event handlers use `_on_<event>` naming: `_on_generate`, `_on_rescan`, `_on_scan_finished`, `_on_sym_item_changed`, `_on_dest_changed` (`kicad_lib_manager/main_window.py`, `kicad_lib_manager/widgets/library_table.py`)
- Qt-style `populate`, `select_all`, `deselect_all` are public methods on widgets (`kicad_lib_manager/widgets/library_table.py`)

**Variables:**
- snake_case locals; short loop names are common (`f`, `d`, `m`, `lib`, `ref`, `sym`)
- Module-level constants are UPPER_SNAKE_CASE: `FOOTPRINT_RE`, `MODEL_RE`, `SKIP_DIRS` (`kicad_lib_manager/library_scanner.py`), `ENV_VAR`, `REPO_ROOT` (`generate_lib_tables.py`), `COLORS` (`kicad_lib_manager/widgets/log_panel.py`), `APP_TITLE`, `REPO_ROOT` (`kicad_lib_manager/main_window.py`), `APP_ORG`, `APP_NAME` (`kicad_lib_manager/settings.py`)
- Private module constants use a leading underscore: `_MAX_DEST_HISTORY`, `_LIB_ENTRY_RE`, `_MANAGED_MARKER`
- Qt widget attributes are stored as `self._<name>`: `self._sym_tree`, `self._fp_tree`, `self._dest_combo`, `self._generate_btn`, `self._log` (`kicad_lib_manager/main_window.py`, `kicad_lib_manager/widgets/library_table.py`)
- Qt-generated dialog/action objects are kept as locals unless they are needed later: `gen_action`, `restore_action`

**Types and Classes:**
- PascalCase dataclasses for data: `FootprintRef`, `SymbolLibrary`, `FootprintLibrary`, `ScanResult` (`kicad_lib_manager/models.py`)
- Widgets and workers are PascalCase and suffixed by role where applicable: `MainWindow`, `ScanWorker(QThread)`, `LibraryTableWidget`, `LogPanel`, `BackupDialog`, `HelpDialog`, `MergeResult`
- Qt signals are declared as class attributes with lowercase names: `progress`, `finished`, `error` on `ScanWorker` (`kicad_lib_manager/main_window.py`)

## Code Style

**Formatting:**
- No formatter configuration detected (no `pyproject.toml`, `setup.cfg`, `.flake8`, `.style.yapf`, `ruff.toml`, or `.editorconfig` in the repo root)
- Observed style: 4-space indentation, double quotes predominate, f-strings for interpolation, trailing commas in multi-line calls and literals
- Line length is loose: most lines stay under ~100 characters, but a few exceed it (e.g. the `QAction` tooltip/status lines in `kicad_lib_manager/main_window.py`, the `_build_ui` stylesheet strings)
- Keep new code consistent with the surrounding file rather than reformatting unrelated lines

**Linting:**
- No linter configuration detected. No `# noqa`, `# type: ignore`, or `# pylint:` pragmas were found in scope.
- Code is written against modern Python typing: `X | None` unions, builtin generics `list[str]`, `dict[int, Path]`, `set[str]`, `tuple[int, Path | None, Path | None]` (`kicad_lib_manager/table_generator.py`, `kicad_lib_manager/library_scanner.py`). Requires Python 3.10+.
- Use `from __future__` is not used; annotations rely on runtime-evaluable 3.10+ syntax.

## Import Organization

**Order (as observed in `kicad_lib_manager/main_window.py` and `kicad_lib_manager/library_scanner.py`):**
1. Standard library (`json`, `os`, `re`, `sys`, `shutil`, `pathlib`, `typing`, `datetime`, `dataclasses`)
2. Third-party: PySide6 (`from PySide6.QtWidgets import ...`, `from PySide6.QtCore import ...`, `from PySide6.QtGui import ...`)
3. Local package imports, using relative imports within the `kicad_lib_manager` package

**Path Aliases:**
- None. The package uses explicit relative imports: `from .models import ...` inside `kicad_lib_manager/`, `from ..models import ...` and `from ..table_generator import ...` inside `kicad_lib_manager/widgets/`.
- Root-level scripts use absolute package imports: `from kicad_lib_manager.main_window import MainWindow` in `kicad_lib_manager.py`.
- Qt imports are grouped per module and often span multiple lines with parenthesised lists:
  ```python
  from PySide6.QtWidgets import (
      QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
      QPushButton, QComboBox, QLabel, QFileDialog, QMessageBox,
      QProgressDialog,
  )
  ```

**Barrel Files:**
- `kicad_lib_manager/__init__.py` and `kicad_lib_manager/widgets/__init__.py` are empty. Import concrete modules directly; do not add re-exports unless there is a clear need.

## Error Handling

**Patterns:**
- Filesystem and parsing failures are caught narrowly and converted to return values, not raised. Examples:
  - `read_text` wrapped in `except (OSError, UnicodeDecodeError): return refs` (`kicad_lib_manager/library_scanner.py`, `_parse_footprint_refs` and `check_3d_model_paths`)
  - JSON load wrapped in `except (OSError, json.JSONDecodeError) as e: return [f"Failed to read KiCad config: {e}"]` (`sync_kicad_path_vars`)
  - Missing or unreadable table files return empty lists: `parse_lib_table` returns `[]` (`kicad_lib_manager/table_generator.py`)
- Functions that perform side effects report outcomes as human-readable message lists (`list[str]`) rather than exceptions. `write_tables`, `restore_backup_pair`, `sync_kicad_path_vars`, `scan_all` warnings all follow this. New side-effecting helpers should follow the same shape so `main_window.py` can route each message to the log panel.
- Message severity is decided by the caller from substrings. `MainWindow._on_generate` treats a message as a warning when it starts with `Warning:` or contains `removed`, and `_sync` path messages as warnings when they contain `Failed`, `Could not`, or `not found` (`kicad_lib_manager/main_window.py`). Keep these literal phrases stable if you change the messages.
- Broad `except Exception as e` is used only at the thread boundary: `ScanWorker.run` catches any exception and emits `self.error.emit(str(e))` (`kicad_lib_manager/main_window.py`).
- Bare `except:` is not used.
- Validation of user-facing state is done with early returns plus a log entry, not dialogs. Examples: `_on_generate` logs `"No libraries selected."` at `warning` level and returns; `_on_generate` checks `dest.exists()` first.
- `QMessageBox` is used only for the About dialog (`_on_about`). Errors go to the log panel.

**Guard pattern:**

```python
def _on_restore_backup(self):
    dialog = BackupDialog(self._dest_combo.currentText(), parent=self)
    if dialog.exec() and dialog.selected_backup_num is not None:
        ...
```

## Logging

**Framework:** None. No `logging` module usage. No `print()` in the GUI package.

**GUI logging:** Use `LogPanel.log(message, level)` from `kicad_lib_manager/widgets/log_panel.py`. Valid levels are `"info"`, `"warning"`, `"error"`, `"success"`; unknown levels fall back to `info`. Each line is prefixed with a `HH:MM:SS` timestamp.

```python
self._log.log(f"Scan error: {error_msg}", "error")
```

**CLI logging:** `generate_lib_tables.py` uses plain `print()` for its summary and next-step instructions only.

**When to log:** Log at user-visible operation boundaries (scan start/finish, table generation, backup/restore, KiCad path changes). Do not log inside tight loops; progress is reported through the `progress` callback instead (see Function Design).

## Comments

**When to Comment:**
- Comments explain intent or non-obvious behavior, placed on the line above the code. Examples: `# Try saved path first`, `# Pre-select libraries that exist in the current table files`, `# Footprints are driven by the symbol filter`, `# Block signals to prevent stray itemChanged`.
- Section dividers in `kicad_lib_manager/settings.py` use the form `# ── Label ───...` to group related functions. Follow that when adding a new group in that file.
- Inline trailing comments are used for short notes: `s.setValue(...)`-style lines, `# Available in KiCad's default libraries`.
- Comments are generally English and terse. Avoid restating what the code does.

**Docstrings:**
- Module docstrings are used for entry points and settings (`kicad_lib_manager/settings.py`, `generate_lib_tables.py`, `kicad_lib_manager.py`).
- Function docstrings are one-line summaries for most public functions (`find_kicad_config_dir`, `parse_lib_table`, `list_backup_pairs`). Multi-line docstrings give the return shape when it is a tuple or dict, e.g. `parse_lib_table` lists the dict keys `name, type, uri, options, descr, raw`.
- Triple-double-quoted docstrings. No type information duplicated in docstrings; annotations carry types.
- Docstrings are not used on every private helper.

**JSDoc/TSDoc:** Not applicable (Python).

## Function Design

**Size:** Most helpers are under ~40 lines. `MainWindow` methods and `LibraryTableWidget.populate` are longer (30–50 lines) because they build Qt widgets inline. Prefer extracting a helper when a block is reused (the destination-combo repopulation is repeated in `_populate_dest_combo`, `_on_browse_dest`, and `_on_generate`; reuse `_populate_dest_combo`-style logic rather than copying it again).

**Parameters:**
- Type-annotated parameters with defaults at the end: `def scan_all(repo_root: Path, progress: Callable | None = None, kicad_fp_dir: Path | None = None) -> ScanResult`
- Optional progress callback is always named `progress` and typed `Callable | None`, invoked as `progress(message, current, total)` (`kicad_lib_manager/library_scanner.py`). `ScanWorker` converts it into a percentage for the Qt signal.
- Filesystem inputs are `Path`, not `str`. Convert with `Path(...)` at the boundary (e.g. `Path(self._dest_combo.currentText())`).
- Keyword arguments are used when calling Qt constructors and for `parent=`: `BackupDialog(self._dest_combo.currentText(), parent=self)`.

**Return Values:**
- Functions return `None`, a dataclass, a list, or a `str | None`/`Path | None`. Use `None` for "not found" (`find_kicad_config_dir`, `find_kicad_footprint_dir`, `load_kicad_fp_dir`) rather than sentinel strings.
- Functions that produce status text return `list[str]` (see Error Handling).
- Use `set[str]` for nickname lookups and membership checks (`get_kicad_default_fp_nicknames`, `_check_nickname_collisions`).

## Module Design

**Exports:** No `__all__` declared. Public names are those without a leading underscore. Dataclass models in `kicad_lib_manager/models.py` are the shared vocabulary between scanner, generator, and widgets.

**Dependency direction:**
- `models.py` has no internal imports.
- `library_scanner.py` and `table_generator.py` depend only on `models.py`.
- `widgets/*` depend on `models.py` and, for `backup_dialog.py`, on `table_generator.py`.
- `main_window.py` orchestrates everything. Do not import `main_window` from lower modules.

**Qt conventions:**
- Each widget owns its layout and is constructed with `parent=None` in `__init__`, calling `super().__init__(parent)`.
- Use `blockSignals(True)`/`blockSignals(False)` around programmatic changes to combo boxes and trees to avoid feedback loops (`_populate_dest_combo`, `_set_all_check_state`). Pair every block with an unblock in the same function.
- Use a `self._updating` flag to suppress reentrant `itemChanged` handling in `kicad_lib_manager/widgets/library_table.py`.
- Long-running work runs in a `QThread` subclass that emits signals (`ScanWorker`). Do not call scanning functions directly on the GUI thread.
- Qt enums are fully qualified: `Qt.CheckState.Checked`, `Qt.ItemFlag.ItemIsUserCheckable`, `Qt.WindowModality.WindowModal`, `QDialogButtonBox.StandardButton.Ok`.
- Qt constructors use the PySide6 6.x enum style (`QSettings.Format.IniFormat`, `QSettings.Scope.UserScope`).

**Barrel Files:** Not used. See Import Organization.

## Data Model Conventions

- Use `@dataclass` with `field(default_factory=list)` for mutable defaults (`kicad_lib_manager/models.py`).
- Mutable selection state (`selected`) lives on the model object and is mutated by the GUI. `library_table.py` writes `lib.selected` directly in response to check-state changes. Keep that pattern for any new selectable entity.
- Library identity is the `nickname` (the file stem for `.kicad_sym`, the `.pretty` directory stem for footprints). Nicknames must match between symbol and footprint folders (see `CLAUDE.md` naming convention).

## Generated Table Format

- Generated `sym-lib-table` and `fp-lib-table` entries are produced by `_format_entry` (`kicad_lib_manager/table_generator.py`). Keep the exact S-expression layout:
  ```
    (lib (name "<nick>")(type "KiCad")(uri "${KICAD_LIB_GITHUB}/<rel>")(options "")(descr ""))
  ```
- The managed marker `${KICAD_LIB_GITHUB}/` identifies entries owned by this tool. Entries without it are treated as external and preserved on merge. Do not change this marker without updating `_MANAGED_MARKER` consumers.
- Paths written into tables are forward-slash relative paths via `Path.as_posix()`.

## Settings and Persistence

- All persistent state goes through `QSettings` helpers in `kicad_lib_manager/settings.py` (`load_*`/`save_*`/`add_*` functions). Do not read or write the INI file directly from widgets.
- Settings keys use slash-separated groups: `"window/geometry"`, `"kicad_fp_dir"`, `"dest_history"`.

## Path Handling

- Use `pathlib.Path` for all filesystem work. Convert to `str` only for display or for the `QSettings` / KiCad config payloads.
- Use `.as_posix()` for paths that are written into KiCad tables or compared against repo-relative strings.
- Normalise Windows separators when writing KiCad config: `repo_str = str(repo_root).replace("\\", "/")` (`kicad_lib_manager/library_scanner.py`).

## Script Conventions (root-level)

- Root scripts carry a `#!/usr/bin/env python3` shebang and a module docstring with usage (`generate_lib_tables.py`, `kicad_lib_manager.py`).
- Guard the entry point with `if __name__ == "__main__": main()`.
- Keep `main()` thin. Real logic lives in the `kicad_lib_manager` package.

## Duplication to Avoid Extending

- `generate_lib_tables.py` duplicates `find_symbol_libs`, `find_footprint_libs`, and table formatting from `kicad_lib_manager/library_scanner.py` and `kicad_lib_manager/table_generator.py`. The CLI is legacy (per `CLAUDE.md`). New behavior should go into the package, not the script.
- `_on_dest_changed` and `_check_existing_tables` in `kicad_lib_manager/main_window.py` contain the same logic. Consolidate when touching either.

---

*Convention analysis: 2026-10-18*
