# Phase 1: Foundation - Pattern Map

**Mapped:** 2026-10-18
**Files analyzed:** 24 (new/modified)
**Analogs found:** 8 in-codebase / 24; the rest are covered by RESEARCH.md verified examples (the repo has no tests and no existing S-expression, atomic-write, or enum code)

All analog paths below are git-tracked (checked with `git ls-files`). Nothing under `downloaded_examples/`, `reports/` or `research_notes/` is used as an analog.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `requirements.txt` | config | n/a | RESEARCH.md "Installation" block | research-only |
| `requirements-dev.txt` | config | n/a | RESEARCH.md "Installation" block | research-only |
| `pyproject.toml` | config | n/a | RESEARCH.md "pyproject.toml" example | research-only |
| `.gitattributes` | config | n/a | CONTEXT D-08 (single line `tests/fixtures/** -text`) | research-only |
| `.gitignore` (NOT modified) | config | n/a | n/a: pitfall only, fixtures use `<case>.sym-lib-table` | n/a |
| `kicad_lib_manager/models.py` (modify: add `Severity`, `Issue`) | model | transform | `kicad_lib_manager/models.py` itself | exact |
| `kicad_lib_manager/sexpr.py` | utility | transform | RESEARCH.md Pattern 1 prototype; style from `library_scanner.py` | research-only (style analog partial) |
| `kicad_lib_manager/fsutil.py` | utility | file-I/O | `table_generator.backup_existing` (backup); RESEARCH.md Patterns 2-4 (rest) | role-match |
| `kicad_lib_manager/kicad_files.py` | service | transform (read) | `table_generator.parse_lib_table` + `library_scanner.py` regex parsers | role-match |
| `kicad_lib_manager/library_scanner.py` (modify: add `"tests"` to `SKIP_DIRS`) | service | batch | itself, line 13 | exact |
| `tests/conftest.py` | test config | n/a | RESEARCH.md conftest example | research-only |
| `tests/test_library_table_widget.py` | test | event-driven | `widgets/library_table.py` + RESEARCH.md D-15 example | exact (code under test) |
| `tests/test_models.py` | test | transform | `widgets/log_panel.py` COLORS keys + RESEARCH Pattern 5 | partial |
| `tests/test_manifests.py` | test | file-I/O | none | none |
| `tests/test_sexpr.py` | test | transform | RESEARCH.md Pattern 1 | research-only |
| `tests/test_roundtrip_corpus.py` | test | file-I/O | RESEARCH.md "Corpus helper" example | research-only |
| `tests/test_edits.py` | test | transform | RESEARCH.md "Targeted edit test" | research-only |
| `tests/test_fsutil.py` | test | file-I/O | `table_generator.backup_existing` (naming) + RESEARCH Pattern 3/4 | partial |
| `tests/test_kicad_files.py` | test | transform | RESEARCH.md Pattern 6 | research-only |
| `tests/test_layering.py` | test | request-response (subprocess) | none | none |
| `tests/fixtures/sexpr/*` | fixture | n/a | real files under `Custom/` for shape only (do not copy) | n/a |
| `tests/fixtures/tables/*.sym-lib-table`, `*.fp-lib-table` | fixture | n/a | entry shape of `table_generator._format_entry` | partial |
| `downloaded_examples/ul_CSD85301Q2.zip` (track, explicit path) | fixture | n/a | n/a | n/a |

## Pattern Assignments

### `kicad_lib_manager/models.py` (modify; model, transform)

**Analog:** `kicad_lib_manager/models.py` lines 1-33. It has a single stdlib import line and plain `@dataclass` classes. Keep it free of internal imports. Stdlib `enum` is fine.

**Existing style** (lines 1-9):
```python
from dataclasses import dataclass, field


@dataclass
class FootprintRef:
    library_name: str
    footprint_name: str
    found_in_repo: bool = False
```

**Add** (RESEARCH.md Pattern 5; `Severity` values must equal the `LogPanel.COLORS` keys `info/warning/error/success`; `str, Enum` because `StrEnum` is 3.11+):
```python
from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    text: str
```
Append the new types; do not reorder or touch the existing dataclasses.

---

### `kicad_lib_manager/fsutil.py` (utility, file-I/O)

**Analog (backup only):** `kicad_lib_manager/table_generator.py` `backup_existing`, lines 150-167. `backup_file(path, backup_dir)` must produce identical names (`<name>_backup_<N>`, N = max existing + 1) so `list_backup_pairs` and the Restore dialog keep working.

**Imports and style pattern** (table_generator.py lines 1-5): stdlib imports first, then `from .models import ...` relative import.
```python
import re
import shutil
from pathlib import Path

from .models import FootprintLibrary, SymbolLibrary
```
For fsutil: `from .models import Issue, Severity`. No Qt import.

**Core backup pattern to mirror** (table_generator.py lines 154-167):
```python
    base_name = file_path.name
    parent = file_path.parent
    max_num = 0
    pattern = re.compile(re.escape(base_name) + r"_backup_(\d+)$")

    for f in parent.iterdir():
        m = pattern.match(f.name)
        if m:
            max_num = max(max_num, int(m.group(1)))

    backup_name = f"{base_name}_backup_{max_num + 1}"
    backup_path = parent / backup_name
    shutil.copy2(file_path, backup_path)
    return backup_path
```
Change: iterate `backup_dir` (create with `mkdir(parents=True, exist_ok=True)`), return `Path | Issue` instead of `Path | None`. Do not change the suffix format.

**Error-return style** (project convention): return values rather than raise, with literal phrases kept stable, for example `Issue(Severity.ERROR, "fs.locked", f"Could not write {path.name}: file is in use")`. Existing callers key on "Could not"/"Failed"/"not found" substrings until Phase 2.

**Rest of the module** (`decode_source`, `read_source`, `encode_source`, `normalize_eol`, `atomic_write_bytes`, `default_backup_dir`) has no in-repo analog. Copy from RESEARCH.md Pattern 2 (SourceText), Pattern 3 (atomic write with injectable `retry_delays`/`sleep`, read-only pre-check via `os.access`, `open(tmp, "xb")`, fsync, `os.replace`, cleanup in `finally`) and Pattern 4 (default backup dir; the `KiCadExtLibManager` name matches `APP_ORG` in `settings.py` line 14, but fsutil must not import `settings` because it imports Qt).

Use the section-divider comment style from `settings.py` line 27 (`# ── Label ───...`) if grouping functions.

---

### `kicad_lib_manager/sexpr.py` (utility, transform)

**Analog:** none in the repo (current parsing is regex-only). Copy the RESEARCH.md Pattern 1 prototype (`_TOKEN` regex, `SexprError(line, col)`, `Node` with `slots=True, eq=False`, iterative `parse`, `Edit`, `apply_edits`). Add `quote()` (escape `\`, `"`, `\n`, `\r`; tab raw, per Pitfall 8) and `unquote()`.

**Project style to conform to** (CONVENTIONS): one-line triple-double-quoted docstrings with no type info, `_private` helpers, UPPER_SNAKE constants, `X | None` unions, no `from __future__ import annotations`. Note that the prototype's `list["Node"]` forward reference is valid on 3.10+.

**Regex-constant style** (library_scanner.py lines 10-11):
```python
FOOTPRINT_RE = re.compile(r'\(property\s+"Footprint"\s+"([^"]*)"')
MODEL_RE = re.compile(r'\(model\s+"([^"]*)"')
```
These are the regexes `kicad_files` replaces (they match the first `Footprint` property and break on parens inside strings). Do not import them into the new modules.

---

### `kicad_lib_manager/kicad_files.py` (service, transform, read side)

**Analog:** `table_generator.parse_lib_table`, lines 11-42. It has the same job for lib-table entries, so mirror its shape (load with `OSError`/`UnicodeDecodeError` caught narrowly, empty or error results instead of raising).

```python
def parse_lib_table(path: Path) -> list[dict]:
    """Parse an existing sym-lib-table or fp-lib-table file.

    Returns a list of dicts with keys: name, type, uri, options, descr, raw.
    """
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
```
Changes for the new module:
- Read through `fsutil.read_source` (bytes + strict decode), not `read_text`.
- Return span-carrying dataclasses instead of dicts.
- Return `Issue` rather than silently `[]` on a bad file.
- Handle `(disabled)` and `(hidden)` flags: `_LIB_ENTRY_RE` (lines 11-17) cannot match a `(disabled)` entry.
- Build the locators (`find_symbols`, `find_property`, `footprint_name`, `find_models`, `lib_table_entries`, `load`) from RESEARCH.md Pattern 6.
- Compare names via `unquote(token_text)`. Accept `str` or `atom` node kinds for the footprint name.
- Dependency direction: imports `sexpr`, `fsutil`, `models` only.

---

### `kicad_lib_manager/library_scanner.py` (modify one constant)

**Analog:** itself, line 13. Flag as Open Question 1 in the plan, since it touches an existing module.
```python
SKIP_DIRS = {"env", "venv", ".venv", ".git", ".claude", "__pycache__"}
```
Change to include `"tests"`. `_in_skip_dir` (lines 138-140) checks only `rel[0]`, so a top-level `tests/` is skipped:
```python
def _in_skip_dir(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).parts
    return rel[0] in SKIP_DIRS if rel else False
```
Add a regression test (in `tests/test_layering.py` per RESEARCH, or a dedicated test) asserting `"tests" in SKIP_DIRS`.

---

### `tests/test_library_table_widget.py` (test, event-driven; D-15)

**Code under test:** `kicad_lib_manager/widgets/library_table.py`. Pin this behaviour.

**Selection and sync logic** (lines 145-192, key excerpts):
```python
    def _on_sym_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._updating or column != 0:
            return
        lib = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(lib, SymbolLibrary):
            lib.selected = item.checkState(0) == Qt.CheckState.Checked
        ...
        self._sync_footprint_selection(source)

    def _sync_footprint_selection(self, source: str):
        needed = set()
        for lib in self._sym_libs:
            if lib.selected:
                for ref in lib.footprint_refs:
                    needed.add(ref.library_name)
        self._updating = True
        for nickname, fp_item in self._fp_items.items():
            fp_lib = fp_item.data(0, Qt.ItemDataRole.UserRole)
            if not fp_lib or fp_lib.source != source:
                continue  # Only manage footprints from the affected source
            ...
```
**Test skeleton:** copy the verified D-15 example in RESEARCH.md ("D-15 widget test", lines ~495-537): `scan` fixture builds `ScanResult` with `SymbolLibrary(nickname, rel_path, source, footprint_refs=[FootprintRef(lib, fp, True)])` and `FootprintLibrary(nickname, rel_path, source)` (constructors per `models.py` lines 4-25). Tests use `qtbot.addWidget(w)`, `w.populate(scan)`, `widget._sym_tree.topLevelItem(i).child(j).setCheckState(...)` (sources sorted: Custom=0, WurthElektronik=1) and `w._fp_items[...]`. Keep private-attribute access in one helper (`_sym_item`). The remaining lines 517-537 of RESEARCH.md contain the full body (read that range when writing the plan action).

---

### `tests/conftest.py` (test config)

No in-repo analog. Copy RESEARCH.md conftest: `os.environ["QT_QPA_PLATFORM"] = "offscreen"` (force, not `setdefault`) before any PySide6 import. Add `repo_root` and corpus-discovery fixtures. Also add an offscreen platform assertion test (`QGuiApplication.platformName() == "offscreen"`).

---

### `tests/test_models.py`

**Analog for the contract:** `kicad_lib_manager/widgets/log_panel.py` `COLORS` keys (`info`, `warning`, `error`, `success`). Assert `{s.value for s in Severity}` equals the `COLORS` key set. Note that importing `log_panel` imports Qt, so read the keys via the widget module only in a Qt-allowed test, or hard-code the four expected strings. Also assert `Issue` is frozen (`dataclasses.FrozenInstanceError`).

---

### `tests/test_fsutil.py`

**Backup naming analog:** `table_generator.backup_existing` (lines 154-167 above). Assert `backup_file(p, p.parent)` yields `<name>_backup_1`, then `_2`, equal to what `backup_existing` yields; a `backup_dir` that does not exist is created. Always pass `tmp_path`, never the real app-data directory.

**Atomic write tests:** follow the matrix in RESEARCH.md "Validation Architecture" (success leaves no temp, read-only gives `fs.read_only`, held-open file gives `fs.locked` on win32 only via `skipif`, `monkeypatch` raising `PermissionError` from `os.replace` elsewhere, fsync and `OSError` injection gives `fs.write_failed`, missing dir). Inject `sleep=lambda s: None`. Restore permissions with `os.chmod(path, stat.S_IREAD | stat.S_IWRITE)` in `finally`. After every failure assert the directory listing equals `[target]`.

---

### `tests/test_roundtrip_corpus.py`, `tests/test_sexpr.py`, `tests/test_edits.py`, `tests/test_kicad_files.py`

Analog: RESEARCH.md only.
- `test_roundtrip_corpus.py` uses "Corpus helper and round-trip identity (non-vacuous)": the `_tiles` check, the `_check(data, name)` bytes to `SourceText` to bytes identity, and parametrisation over `Custom/` live files, `tests/fixtures/sexpr/*`, `tests/fixtures/tables/*.sym-lib-table|*.fp-lib-table`, UL zip members (read in memory with a `file_size` cap, never extract), local tables (`@pytest.mark.local_kicad`), and Wurth (`@pytest.mark.wurth` plus an explicit `pytest.skip` reason when empty). Use `pytest.param(path, id=rel_posix, marks=...)`.
- `test_edits.py` uses "Targeted edit test (FOUND-04)".
- `test_kicad_files.py` assertions follow Pattern 6 facts (18 symbols in 10 `Custom/` files, one direct `Footprint` property per top-level symbol, models 0/1/2, bare-atom `fp_text value`).
- Fixtures must be created bytes-exact with `Path.write_bytes` (not the Write tool). Commit `.gitattributes` before staging fixtures. Add self-check tests asserting each fixture's EOL/BOM matches its name.

---

### `tests/test_layering.py`

No analog. Per RESEARCH.md: run a subprocess with `cwd=repo` and `-I`-style isolation that imports `kicad_lib_manager.sexpr`, `kicad_files`, `fsutil`, `models` and asserts `"PySide6" not in sys.modules`. Also hosts the `SKIP_DIRS` regression test.

---

### Config files (`requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `.gitattributes`)

No analog. Copy verbatim from RESEARCH.md: requirements (`PySide6==6.12.0`; dev: `-r requirements.txt`, `pytest==9.1.1`, `pytest-qt==4.5.0`), the `[tool.pytest.ini_options]` block (`testpaths`, `pythonpath = ["."]` is required, `addopts = "-ra --strict-markers"`, `qt_api = "pyside6"`, markers `wurth` and `local_kicad`), and `.gitattributes` containing only `tests/fixtures/** -text`. `test_manifests.py` asserts every requirement is `==`-pinned and matches these values.

## Shared Patterns

### Services return values, do not raise
**Source:** `table_generator.parse_lib_table` (lines 25-30) and CONVENTIONS "Error Handling".
**Apply to:** `fsutil.py`, `kicad_files.py`. Catch `OSError`/`UnicodeDecodeError` narrowly; return `Issue` (new) where the old code returned `[]` or a message string. `sexpr.parse` may raise `SexprError` like `json.loads`; `kicad_files.load` converts it to an `Issue`. No bare `except:`.

### Qt-free layering and imports
**Source:** `table_generator.py` lines 1-5 (stdlib, blank line, relative `.models` import); `models.py` has no internal imports.
**Apply to:** all new modules. Allowed internal imports: `fsutil -> models`; `sexpr -> none`; `kicad_files -> sexpr, fsutil, models`. Only `settings.py` imports Qt. Do not add re-exports to `__init__.py` (it stays empty).

### Path handling
**Source:** CONVENTIONS "Path Handling". Use `pathlib.Path`; read via `Path.read_bytes()`, never `read_text`/`write_text` for KiCad files (EOL translation); `.as_posix()` for KiCad-facing strings and test ids.

### Numbered backup naming
**Source:** `table_generator.backup_existing` lines 157-166 (see fsutil section). Apply to `fsutil.backup_file` and its tests.

### Docstrings and style
One-line `"""..."""` summaries with no type info; 4-space indent, double quotes, trailing commas; comment on the line above the code.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `kicad_lib_manager/sexpr.py` | utility | transform | Repo parses only with regex; use RESEARCH.md Pattern 1 |
| Atomic write / EOL / BOM code in `fsutil.py` | utility | file-I/O | No atomic writes exist (`write_tables` uses a bare `path.write_text`); use RESEARCH.md Patterns 2-3 |
| `tests/*` (all) | test | various | Repo has no tests; use RESEARCH.md "Code Examples" and "Validation Architecture" |
| `requirements*.txt`, `pyproject.toml`, `.gitattributes` | config | n/a | None exist at repo root |

## Pitfalls the planner must carry into plans

1. Fixture lib-table files must be named `<case>.sym-lib-table` / `<case>.fp-lib-table`; bare names are ignored by `.gitignore` lines 2-3, and `*_backup_*` is also ignored.
2. Add `"tests"` to `SKIP_DIRS` (`library_scanner.py:13`) in the same plan that adds fixtures; avoid `.pretty` dirs under `tests/`.
3. Commit `.gitattributes` before staging fixtures; create CRLF/BOM/mixed fixtures with `write_bytes`; `git add downloaded_examples/ul_CSD85301Q2.zip` by explicit path (D-04, costly to reverse).
4. `pythonpath = ["."]` is required for bare `pytest`.
5. Create source files with Write/Edit, not shell heredocs (backslash mangling in the string regex).
6. The `checkpoint:human-verify` for the three SUS-flagged pins goes before the install step.

## Metadata

**Analog search scope:** `kicad_lib_manager/` (all modules, targeted reads of `models.py`, `table_generator.py`, `library_scanner.py`, `settings.py`, `widgets/library_table.py`), repo root, `.planning/phases/01-foundation/`.
**Files scanned:** 12 tracked package files listed, 6 read (some partially).
**Pattern extraction date:** 2026-10-18
