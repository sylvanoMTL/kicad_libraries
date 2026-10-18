---
last_mapped_commit: 3353ce8161c4870e85b50fc8d607d41bb942c796
last_mapped_at: 2026-10-18
---
# Testing Patterns

**Analysis Date:** 2026-10-18

## Current State

**No automated tests exist in scope.** The explored prefixes (`kicad_lib_manager/`, `kicad_lib_manager.py`, `generate_lib_tables.py`) contain no `test_*.py`, `*_test.py`, or `tests/` directory. The repo root has no `tests/`, `pytest.ini`, `pyproject.toml`, `setup.cfg`, `tox.ini`, `noxfile.py`, or CI workflow for testing. Verification is manual: run the GUI and inspect the generated tables in KiCad.

Confirmed absent from the repo-level scan. Dependencies are only `PySide6` (per `CLAUDE.md`); no test runner is declared.

## Test Framework

**Runner:**
- Not configured. No framework is declared or installed.
- If tests are added, `pytest` is the recommended runner for the pure-Python modules. It is not a current dependency.
- Config: none. A future `pytest.ini` or `[tool.pytest.ini_options]` in `pyproject.toml` would be the place for it.

**Assertion Library:**
- Not applicable today. Use plain `assert` under pytest if tests are introduced.

**Run Commands:**

```bash

# No test command exists yet. Recommended once pytest is added (from repo root, using the project venv):

.\env\Scripts\python.exe -m pytest              # Run all tests
.\env\Scripts\python.exe -m pytest -k scanner   # Run a subset
```

Note: `CLAUDE.md` specifies the venv at `env/` created with Windows CPython (`py -m venv env`). Use that interpreter for any test run.

## Test File Organization

**Location (recommended):**
- Separate `tests/` directory at repo root, mirroring the package layout. No co-located tests exist to copy from.

**Naming (recommended):**
- `tests/test_library_scanner.py`, `tests/test_table_generator.py`, `tests/test_settings.py`, `tests/test_library_table.py`
- Test functions named `test_<behavior>` in snake_case.

**Structure (recommended):**

```
tests/
├── conftest.py                # shared fixtures (tmp repo tree, sample .kicad_sym / .kicad_mod)
├── test_library_scanner.py    # pure-Python scanning, cross-reference, 3D path checks
├── test_table_generator.py    # table merge, backup numbering, restore
└── test_widgets.py            # optional, requires pytest-qt
```

**Note:** `.gitignore` already excludes `env/`, `venv/`, `.venv/`, `__pycache__/`. A `tests/` directory would not be ignored and would be committed; keep fixtures small and synthetic. Do not copy real libraries from `Custom/` or `WurthElektronik/` into fixtures.

## Test Structure

**Suite Organization (recommended, matches the function-oriented style of the code):**

```python
from pathlib import Path

from kicad_lib_manager.table_generator import generate_sym_lib_table
from kicad_lib_manager.models import SymbolLibrary

def test_generate_sym_lib_table_writes_only_selected(tmp_path: Path):
    libs = [
        SymbolLibrary(nickname="IC_LDO_TI", rel_path="Custom/Symbols/IC_LDO_TI.kicad_sym",
                      source="Custom", selected=True),
        SymbolLibrary(nickname="Connector_USB_GCT", rel_path="Custom/Symbols/Connector_USB_GCT.kicad_sym",
                      source="Custom", selected=False),
    ]
    result = generate_sym_lib_table(libs)
    assert '(name "IC_LDO_TI")' in result.content
    assert "Connector_USB_GCT" not in result.content
    assert result.added == 1
```

**Patterns to follow when writing tests:**
- Use `tmp_path` for every filesystem fixture. Never write into the real repo, the real `sym-lib-table`/`fp-lib-table`, or the user's `%APPDATA%/kicad`.
- Build models directly with the dataclasses from `kicad_lib_manager/models.py`; they have no required external state.
- Pass `kicad_fp_dir=` explicitly to `scan_all` and `cross_reference` so tests do not depend on a local KiCad install. Use `tmp_path` to stand in for the KiCad footprint folder.
- Pass `existing_path=` to `generate_sym_lib_table` / `generate_fp_lib_table` to test merge behavior; use `None` to test fresh generation.

**Setup and teardown:**
- pytest `tmp_path` / `monkeypatch` fixtures cover all needs. No `setUp`/`tearDown` pattern is in use anywhere (none exists).
- For `settings.py`, `QSettings` writes to the real user scope. Monkeypatch `kicad_lib_manager.settings.get_settings` to return a `QSettings` pointed at a temp file (`QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)`) before testing.

## Mocking

**Framework:** None in use. `unittest.mock` (stdlib) or `pytest-mock` would be the natural choice if needed.

**What to Mock (recommended):**
- `find_kicad_config_dir` and `find_kicad_footprint_dir`: these probe `APPDATA`, `Path.home()`, and `C:/Program Files/KiCad`. Monkeypatch `sys.platform`/`os.environ` or the functions directly.
- `QSettings` via `get_settings` (see above).
- Interactive dialogs (`QFileDialog.getExistingDirectory`, `QMessageBox`) if GUI tests are added.

**What NOT to Mock:**
- Filesystem access inside `tmp_path`. Real files are cheap and the scanner and table code are file-driven.
- The regexes (`FOOTPRINT_RE`, `MODEL_RE`, `_LIB_ENTRY_RE`). Test them with real S-expression snippets.
- `dataclasses` models.

## Fixtures and Factories

**Test Data (recommended shapes, taken from the formats the code parses):**

Symbol library snippet containing a footprint reference (matches `FOOTPRINT_RE` in `kicad_lib_manager/library_scanner.py`):

```
(kicad_symbol_lib ...
  (symbol "IC_LDO_TI"
    (property "Footprint" "Package_SO:SOIC-8" ...)
  )
)
```

Footprint model snippet containing a 3D path (matches `MODEL_RE`):

```
(footprint "R_0603"
  (model "${CUSTOM_3DMODEL_DIR}/R_0603.step" ...)
)
(footprint "Bad"
  (model "C:/Users/me/3d/Bad.step" ...)   ; should produce a warning
)
```

Existing table with managed and external entries (matches `_LIB_ENTRY_RE`, which requires the exact field order `name, type, uri, options, descr`):

```
(sym_lib_table
  (lib (name "External_Lib")(type "KiCad")(uri "C:/other/External.kicad_sym")(options "")(descr ""))
  (lib (name "IC_LDO_TI")(type "KiCad")(uri "${KICAD_LIB_GITHUB}/Custom/Symbols/IC_LDO_TI.kicad_sym")(options "")(descr ""))
)
```

**Location:** None exist. Put shared fixtures in `tests/conftest.py` if created.

## Coverage

**Requirements:** None enforced. No `--cov` configuration, no coverage threshold, no coverage tool declared.

**View Coverage (recommended, only if `pytest-cov` is added):**

```bash
.\env\Scripts\python.exe -m pytest --cov=kicad_lib_manager --cov-report=term-missing
```

## Test Types

**Unit Tests (highest value, no existing coverage):**
- `kicad_lib_manager/table_generator.py`: `parse_lib_table`, `_format_entry`, `_merge_table` (external entries preserved, managed entries replaced, removed managed entries reported), `backup_existing` (numbering increments), `list_backup_pairs` (sorted descending, sym/fp paired by number), `restore_backup_pair` (current file backed up first).
- `kicad_lib_manager/library_scanner.py`: `_parse_footprint_refs` (dedup, skips entries without `:`), `cross_reference` (repo hit, KiCad default hit, miss produces warning), `check_3d_model_paths` (skips `${...}` paths), `_in_skip_dir` (skips `env/`, `.git/`, `.claude/`), `sync_kicad_path_vars` (idempotent; writes only when changed).
- `kicad_lib_manager/settings.py`: `add_dest_to_history` ordering and cap of 10 (`_MAX_DEST_HISTORY`).
- `generate_lib_tables.py`: `generate_sym_lib_table` / `generate_fp_lib_table` produce the same format as the package. Consider deleting the duplicate or having it import from the package.

**Widget Tests (optional, needs `pytest-qt`):**
- `LibraryTableWidget`: selecting a symbol checks its footprints; deselecting unchecks only footprints from the same source; `select_all` / `deselect_all` update all symbol and footprint selections.
- `LogPanel.log`: emits the right color span for each level.
- `BackupDialog`: OK button is disabled until a row is selected.

**Integration Tests:**
- Full scan of a synthetic repo tree under `tmp_path` followed by `write_tables` and a re-read of the output. Verify the two-pass merge: generate, add an external entry by hand, regenerate, assert the external entry is preserved and a `_backup_1` file exists.

**E2E Tests:**
- Not used. Verification is manual in KiCad (Preferences > Configure Paths, then confirm libraries load).

## Manual Verification (current practice)

Because no automated tests exist, changes to the GUI or generator should be verified by:
1. Running `.\env\Scripts\python.exe kicad_lib_manager.py` and confirming the scan log reports the expected symbol and footprint counts.
2. Toggling a symbol and confirming the linked footprints follow (scoped to its source).
3. Generating tables into a scratch folder (not the real KiCad config) and inspecting `sym-lib-table` / `fp-lib-table` for correct `${KICAD_LIB_GITHUB}/` URIs and preserved external entries.
4. Confirming a `*_backup_N` file appears for each regenerated table and that Restore (`Ctrl+R`) brings it back.
5. Running `python generate_lib_tables.py` only if the legacy CLI is still needed, and noting it writes `sym-lib-table` and `fp-lib-table` into the repo root (gitignored).

## Common Patterns

**Filesystem fixtures (recommended):**

```python
def test_backup_numbering_increments(tmp_path: Path):
    table = tmp_path / "sym-lib-table"
    table.write_text("(sym_lib_table\n)\n", encoding="utf-8")
    first = backup_existing(table)
    second = backup_existing(table)
    assert first.name == "sym-lib-table_backup_1"
    assert second.name == "sym-lib-table_backup_2"
```

**Error paths (recommended):**
- Unreadable or non-UTF-8 files: `_parse_footprint_refs` and `check_3d_model_paths` must return empty results, not raise. Write bytes that fail UTF-8 decoding to test this.
- Missing tables: `parse_lib_table(tmp_path / "missing")` returns `[]`.
- Bad JSON: `sync_kicad_path_vars` returns a single `"Failed to read KiCad config: ..."` message.
- `ScanWorker` errors are surfaced as `error` signal strings; test via `pytest-qt`'s `qtbot.waitSignal` if worker tests are added.

**Async Testing:**
- Not applicable to the scanner (synchronous). `ScanWorker` is a `QThread`; if tested, use `qtbot.waitSignal(worker.finished, timeout=...)` rather than sleeping.

---

*Testing analysis: 2026-10-18*
