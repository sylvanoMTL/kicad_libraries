# Phase 4: Plan and Install Core - Pattern Map

**Mapped:** 2026-10-19
**Files analyzed:** 17 (6 source modules, 1 config, 1 layering test edit, 9 test/fixture files)
**Analogs found:** 15 / 17 (all analog paths verified git-tracked)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `kicad_lib_manager/kicad_files.py` (modify: write side) | utility | transform (span edits) | same file (`retarget_model`, `find_property`) + `sexpr.Edit` | exact |
| `kicad_lib_manager/importer/plan.py` | model | transform | `importer/candidate.py` | exact |
| `kicad_lib_manager/importer/planner.py` | service | transform + read-disk | `importer/adapters/base.py` (kicad_files use), `importer/layout.py` (disk listing) | role-match |
| `kicad_lib_manager/importer/kicad_cli.py` | service | request-response (subprocess) | `kicad_lib_manager/kicad_process.py` | exact |
| `kicad_lib_manager/importer/applier.py` | service | file-I/O, transaction | `table_generator.write_tables` / `restore_backup_pair` | role-match |
| `kicad_lib_manager/importer/verify.py` | service | file-I/O (read) + transform | `importer/adapters/base.py` + `kicad_files.load` | role-match |
| `pyproject.toml` (modify: marker) | config | n/a | same file `markers` list | exact |
| `tests/test_importer_layering.py` (modify `ALLOWED`) | test | n/a | same file lines 30-66 | exact |
| `tests/installfixtures.py` | test util | transform | `tests/zipfixtures.py` (`symbol_lib`, `footprint`, `write_custom_layout`) | exact |
| `tests/conftest.py` (modify: fixtures) | test config | n/a | same file | exact |
| `tests/test_kicad_files_write.py` | test | transform | existing kicad_files tests (`tests/test_kicad_files*.py`) | role-match |
| `tests/test_kicad_cli.py` | test | request-response (fake runner) | `tests/test_write_tables.py` monkeypatch style | role-match |
| `tests/test_install_plan.py` | test | transform | `tests/test_write_tables.py` | role-match |
| `tests/test_install_apply.py` | test | fault-injection | `tests/test_write_tables.py::_fail_replace_for` | exact |
| `tests/test_install_verify.py` | test | transform | `tests/test_write_tables.py` | role-match |
| `tests/test_install_e2e.py` | test | e2e | `tests/zipfixtures.py::unpack_sample`, `write_custom_layout` | role-match |

## Pattern Assignments

### `kicad_lib_manager/kicad_files.py` (utility, write side)

**Analog:** itself. The layering rule (`tests/test_layering.py:18`) allows `kicad_files` to import only `{"sexpr", "fsutil", "models"}`. New helpers must not import `importer`. Do not extend `ALLOWED` for it.

**Imports (lines 1-7), keep as-is, add what is needed from sexpr:**
```python
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .fsutil import SourceText, decode_source, read_source
from .models import Issue, Severity
from .sexpr import Edit, Node, SexprError, parse, quote, unquote
```

**Edit-returning helper pattern** (lines 176-178). Every write helper returns `Edit` objects (or lists of them), never mutated text; the caller runs `apply_edits` once:
```python
def retarget_model(ref: ModelRef, new_path: str) -> Edit:
    """Return the edit that replaces only the model path token."""
    return Edit(ref.path_node.start, ref.path_node.end, quote(new_path))
```

**Ref dataclasses to return** (lines 12-46): frozen dataclasses carrying `node`, `name_node`, `value_node`. New helpers (`set_property`, `rename_property`, `rename_symbol`, `insert_symbol`, `set_footprint_name`, `set_or_insert_model`, `symbol_pin_numbers`, `footprint_pad_numbers`) follow `PropertyRef` / `NameRef` / `ModelRef` shape.

**Lookup helpers to reuse, never reimplement:** `find_symbols` (118-129), `find_symbol` (132-137), `find_property` (140-150), `footprint_name` (153-161), `find_models` (164-173), `file_version` (99-110, returns `int | None`), `parse_bytes(data, name, max_nodes=)` (71-76, returns `LoadedFile | Issue`).

**Failure convention:** parse failures come back as `Issue` (`_parse`, lines 61-68). New helpers return `Issue` or `None`/empty list for "not found"; they do not raise for expected failures. `apply_edits` raises `ValueError` only for programmer error (overlap).

**Research code to adopt:** `rename_edits`, `insert_symbol`, `new_hidden_property` in 04-RESEARCH.md "Code Examples" (lines 521-565). Insert text uses `fsutil.normalize_eol(block, target.source.eol)` (fsutil.py:244).

---

### `kicad_lib_manager/importer/plan.py` (model, transform)

**Analog:** `kicad_lib_manager/importer/candidate.py`

**Module style** (lines 1-8): module docstring, `@dataclass(frozen=True)`, `Path`, relative imports from `..models`.
```python
"""Intake data model: what a vendor package holds, as consumed by the install and GUI phases."""

from dataclasses import dataclass
from pathlib import Path

from ..models import Issue
from .naming import NameResult, sanitize_filename, sanitize_name
from .package import PackageFile
```

**Frozen dataclass with tuple fields** (lines 64-74) is the shape for `InstallPlan`, `FileOp`, `Conflict`, `InstallOptions`, `InstallResult`; use `tuple[...]`, not `list`, for plan contents:
```python
@dataclass(frozen=True)
class ImportCandidate:
    vendor: str
    ...
    issues: tuple[Issue, ...]
```

**Derived property pattern** (lines 32-35, 76-78): `@property` for computed views (`name_check`, `has_model`); use the same for `plan.unresolved_conflicts`, `plan.blocked`.

**Reference `PackageFile` (package.py:70-77)** for the model-copy `FileOp.source` (WR-04): fields `member, path, kind, size, sha256, staged`. Docstring must state "Package stays open until `apply_plan` returns" (see `Package` docstring, package.py:82-86, for the lifetime-contract phrasing).

**Allowed imports (register in ALLOWED):** `models`, `importer.candidate`, `importer.package`.

---

### `kicad_lib_manager/importer/planner.py` (service, transform + disk reads)

**Analogs:** `importer/adapters/base.py` (consuming `kicad_files`), `importer/layout.py` (fresh disk listings), `importer/suggest.py` / `naming.py` (contracts to call).

**Imports pattern** (`adapters/base.py` lines 7-20), note three-dot relative to reach package-level modules from `importer/`: from `importer/planner.py` use two dots (`from ..kicad_files import ...`):
```python
from ...kicad_files import (
    SymbolRef, file_kind, file_version, find_models, find_property,
    find_symbols, footprint_name, parse_bytes,
)
from ...models import Issue, Severity
from .. import package as _package
from ..candidate import FootprintItem, ImportCandidate, ModelItem, PartMeta, SymbolItem
from ..package import Package, PackageFile
```

**Field-role constants to import, not redefine** (`adapters/base.py:29-31`). Importing `importer.adapters.base` into planner requires adding it to ALLOWED for `importer.planner` (research Pitfall 10 lists it):
```python
MANUFACTURER_FIELDS = ("Manufacturer", "MF", "MANUFACTURER", "Manufacturer_Name")
MPN_FIELDS = ("MPN", "MP", "Manufacturer_Part_Number", "MANUFACTURER_PART_NUMBER")
DESCRIPTION_FIELDS = ("Description", "ki_description")
```

**Fresh disk listing, case-aware** (`layout.py` lines 8-66): read the target on every `build_plan` call, never reuse `_scan_result`. Use `RepoLayout.for_repo`, `list_symbol_libs`, `list_footprint_libs`, `list_model_files`, `list_existing_libraries`; compare with `casefold()` (D-10):
```python
def _sorted(names) -> list[str]:
    return sorted(set(names), key=lambda n: (n.casefold(), n))

def list_model_files(layout: RepoLayout) -> list[str]:
    """Return every file below Custom/3DModels as a posix path relative to it."""
```

**Contracts to call:** `suggest.placeholder_tokens(name)` (suggest.py:213, refuse when non-empty, D-04); `naming.sanitize_name` (58), `sanitize_filename` (96), `case_clash` (113, returns `list[Issue]`); `fsutil.decode_source` / `normalize_eol`.

**Return shape:** `InstallPlan` with an `issues` tuple; ERROR Issues mean refuse (no raise). Fold `package_issues` and `candidate.issues` into `plan.issues` (WR-05).

**Version compare:** `kicad_files.file_version(root)` returns `int | None`; compare as integers. `None` means splice as-is with `install.version_unknown` WARNING (Open Question 3).

**Inject `ToolContext(kicad_cli, kicad_symbols_dir, extra_symbol_dirs)` rather than globals.** No Qt, no settings import.

---

### `kicad_lib_manager/importer/kicad_cli.py` (service, request-response/subprocess)

**Analog:** `kicad_lib_manager/kicad_process.py`

**Subprocess pattern** (lines 25-32, 47-48). Copy the flags exactly, but add an injectable runner and a timeout:
```python
result = subprocess.run(
    [str(exe), "/NH", "/FO", "CSV"],
    capture_output=True,
    text=True,
    errors="replace",
    timeout=5,
    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
)
...
except (OSError, subprocess.SubprocessError):
    return []
```
`kicad_cli.py` must turn `OSError` and `subprocess.TimeoutExpired` (a `SubprocessError`) into an `Issue`, not an exception. Platform branching uses the keyword-only `platform: str | None = None` default idiom (line 19):
```python
def kicad_running(*, platform: str | None = None) -> list[str]:
    platform = sys.platform if platform is None else platform
```
Follow it for `locate_kicad_cli(..., *, platform=None)`. Locate order: explicit path, `<kicad_fp_dir>.parents[2] / "bin" / "kicad-cli[.exe]"`, `shutil.which`. Module docstring in the same "Stdlib only. No shell is used." style (lines 1-4).

**Runner and result handling:** `_run`, `upgrade_symbol_file` in 04-RESEARCH.md lines 505-519. Always a fresh `tempfile.mkdtemp` output dir; treat "exit 0 and no output file" as already current.

**Allowed imports:** `models` (and `fsutil`/`kicad_files` only if it reads the output version).

---

### `kicad_lib_manager/importer/applier.py` (service, file-I/O transaction)

**Analog:** `kicad_lib_manager/table_generator.py::write_tables` (lines 232-297) and `restore_backup_pair` (322-355). Read these when writing; the pattern below is from the `fsutil` calls they make.

**Write seam: always call through the module attribute** so tests can `monkeypatch.setattr(fsutil, "atomic_write_bytes", ...)`:
```python
# table_generator.py:272-279
backup = fsutil.backup_file(path, path.parent, number=backup_number)
if isinstance(backup, Issue):
    issues.append(backup)
...
failure = fsutil.atomic_write_text(path, result.content, bom=bom)
```
In the applier use `from .. import fsutil` (not `from ..fsutil import atomic_write_bytes`) so the patch takes effect. Add `fsutil` to ALLOWED for `importer.applier`.

**fsutil primitives (fsutil.py):**
- `atomic_write_bytes(path, data, *, retry_delays, sleep) -> Issue | None` (85-150): returns `fs.locked`, `fs.read_only`, `fs.write_failed`, `fs.not_a_file`; never raises. Check `isinstance(result, Issue)` / truthiness after each write.
- `backup_file(path, backup_dir, *, number=None) -> Path | Issue` (173-224): returns `Issue` (`fs.backup_failed`) on failure; abort before any write.
- `default_backup_dir()` (227-241): "never created here"; applier creates `installs/<YYYYmmdd-HHMMSS>_<lib>/` and prunes to newest 10 (pattern-match names only).
- `normalize_eol(text, eol)` (244-246).

**Undo list:** append `(original_path_as_listed, pre_image_bytes | None, created_dirs)` after each successful write; reverse on failure; collect `install.rollback_failed` Issues rather than raising. Write order: mkdir `.pretty`, model, footprint(s), then symbol library last.

**Result convention:** return `InstallResult(ok, touched, library, new_library, issues)`; status text only via `Issue` (CONVENTIONS "Error Handling").

---

### `kicad_lib_manager/importer/verify.py` (service, file-I/O read)

**Analog:** `importer/adapters/base.py` (re-parse + `find_*` use) and `library_scanner._custom_model_names` (exact-case name set, referenced by research Pattern 7).

**Core pattern:** `kicad_files.load(path)` returns `LoadedFile | Issue` (line 79); check `isinstance(loaded, Issue)` for the hard "re-parses" check. Existence checks use `os.listdir` name sets, not `Path.exists()`.

**POST-03 prefilter** (research Pattern 8): bytes-substring `("(symbol " + quote(name)).encode()` over `.kicad_sym` bytes, then a multiline depth-1 regex confirm. Do not route stock libs through the intake `_read_limited` 8 MiB cap.

**POST-04:** pins from `(number "N" ...)` under `pin` across all sub-symbols and the `extends` chain; pads from the first token after `pad` in direct children; ignore empty `""`. Soft: WARNING `verify.pin_pad_mismatch`.

Keep `find_name_elsewhere` importable on its own (Phase 5 may call it).

---

### `pyproject.toml` (config)

**Analog:** itself, lines 1-9:
```toml
addopts = "-ra --strict-markers"
markers = [
    "wurth: needs the WurthElektronik submodule checked out (stress/perf corpus)",
    "local_kicad: reads the user's real KiCad config tables under the OS config dir (opt-in, read-only)",
]
```
Add one line: `"kicad_cli: needs the real kicad-cli binary (skipped when absent)",`. Must land before any test uses `@pytest.mark.kicad_cli`.

---

### `tests/test_importer_layering.py` (modify)

**Analog:** the `ALLOWED` dict (lines 30-66). Add one entry per new module; keys are dotted paths relative to `kicad_lib_manager`, values are the exact set of resolved relative-import targets:
```python
"importer.detect": {
    "models", "importer.package", "importer.candidate",
    "importer.adapters.base", ...
},
```
Suggested entries (adjust to real imports; the guard fails on any unlisted import and on unregistered modules):
```python
"importer.plan": {"models", "importer.candidate", "importer.package"},
"importer.kicad_cli": {"models"},
"importer.planner": {"models", "fsutil", "kicad_files", "sexpr", "importer.plan",
    "importer.candidate", "importer.package", "importer.naming", "importer.layout",
    "importer.suggest", "importer.adapters.base", "importer.kicad_cli", "importer.verify"},
"importer.verify": {"models", "fsutil", "kicad_files", "sexpr", "importer.plan", "importer.layout"},
"importer.applier": {"models", "fsutil", "kicad_files", "importer.plan", "importer.kicad_cli",
    "importer.verify", "importer.layout"},
```
Rules to respect: no absolute `kicad_lib_manager`/`PySide6` imports (`FORBIDDEN_TOP`, line 77), no `.extract`/`.extractall` attributes (line 78), a relative import is resolved by `resolve_relative`. Note `from .. import fsutil` resolves to target `fsutil` (module-name alias path, lines 150-156).

---

### Test infrastructure

**`tests/installfixtures.py`**, analog `tests/zipfixtures.py`: builders `symbol_lib` (170), `footprint` (192), `write_custom_layout` (313), `unpack_sample` (138), `make_zip` (55), `_quote` (165). Build bytes at test time; extend rather than duplicate. New builders (extends pair, MF/MP symbol, model-bearing footprint, extra-pad footprint, per-version target libs 20211014 CRLF / 20231120 / 20241209 tab-indent).

**`tests/conftest.py`**: add fixtures `custom_copy`, `ul_package`, `kicad_cli_path`, `snapshot(root)` (relpath to sha256).

**`tests/test_install_apply.py` fault injection**, analog `tests/test_write_tables.py:115-127, 165-177`:
```python
def _fail_replace_for(monkeypatch, target_name, exc):
    real_replace = os.replace
    real_write = fsutil.atomic_write_bytes
    def replace(src, dst):
        if os.path.basename(dst) == target_name:
            raise exc
        return real_replace(src, dst)
    def quick_write(path, data, *, retry_delays=(), sleep=None):
        return real_write(path, data, retry_delays=(0.0,), sleep=lambda s: None)
```
```python
real_backup = fsutil.backup_file
def backup(path, backup_dir, **kwargs):
    return failure if path.name == "sym-lib-table" else real_backup(path, backup_dir, **kwargs)
monkeypatch.setattr(fsutil, "backup_file", backup)
```
Parametrised Nth-write failure test: 04-RESEARCH.md lines 567-583. Assertions follow `test_write_tables.py:157-162`: `(error,) = _errors(issues)`, `error.code == "fs.locked"`, bytes unchanged, `not list(tmp_path.glob(".*.tmp"))`.

**`tests/test_kicad_cli.py`**: scripted fake runner (exit codes, outputs, "not updated" no-output case). Real-CLI tests carry `@pytest.mark.kicad_cli` and skip via `kicad_cli_path`.

## Shared Patterns

### Issue-list returns, no raise for expected failures
**Source:** `kicad_lib_manager/models.py` (`Issue`, `Severity`), `fsutil.py:85-150`, `kicad_files.py:61-68`
**Apply to:** planner, applier, verify, kicad_cli
```python
return Issue(Severity.ERROR, "fs.bad_encoding", f"Could not read {name}: not valid UTF-8 (byte {e.start})")
```
Codes are dotted lowercase (`install.conflict_unresolved`, `install.version_newer_than_target`, `install.cli_gate_failed`, `install.rolled_back`, `verify.pin_pad_mismatch`, `verify.name_elsewhere`). Callers route by `Severity`, not substring.

### Span-splice edits, EOL and BOM preserved
**Source:** `sexpr.py:154-173` (`Edit`, `apply_edits`), `fsutil.py:28-82` (`SourceText.eol`, `bom`, `encode_source`)
**Apply to:** every write that changes existing KiCad text
```python
@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    text: str
```
Build edits against the original parse, apply once, re-encode with `encode_source(text, source.bom)`. Inserted text through `normalize_eol(text, source.eol)`.

### Atomic write and app-data backup, through the module attribute
**Source:** `fsutil.py` (`atomic_write_bytes`, `backup_file`, `default_backup_dir`); call style from `table_generator.py:272-279`
**Apply to:** applier only

### Path handling
Use `pathlib.Path` everywhere; `.as_posix()` for strings written into KiCad files (model path `${CUSTOM_3DMODEL_DIR}/<file>`); resolve and require `is_relative_to(layout.custom_dir.resolve())` before any write.

### Style (from project CLAUDE.md)
snake_case, `_`-prefixed private helpers, one-line triple-double-quoted docstrings, double quotes, f-strings, `X | None` unions, builtin generics, relative imports, optional `progress(message, current, total)` callback, `Path` not `str` for filesystem inputs.

### Layering
Importer modules are Qt-free and registered in `tests/test_importer_layering.py` `ALLOWED`; `kicad_files` may import only `sexpr, fsutil, models`; `models.py` imports nothing internal; never import `main_window`.

## No Analog Found

| File / concern | Role | Data Flow | Reason |
|----------------|------|-----------|--------|
| Multi-file transaction with undo list (in `applier.py`) | service | transaction | `write_tables` writes two independent tables with per-file backup but has no reverse-undo of pre-images; use `fsutil` primitives plus 04-RESEARCH.md Pattern 6 |
| Stock-library bytes-prefilter name index (`verify.py`) | utility | batch scan | No existing multi-library scan of this size; use research Pattern 8 |
| `kicad-cli` memoisation by block hash | utility | cache | No caching precedent in the codebase; use research Pattern 3 step 2 |
| Backup pruning of `installs/` folders | utility | file-I/O | `backup_file` numbers files but never prunes; implement per Pattern 6 step 2 and the "delete only timestamp-pattern dirs" security row |

## Metadata

**Analog search scope:** `kicad_lib_manager/*.py`, `kicad_lib_manager/importer/**`, `tests/test_importer_layering.py`, `tests/test_write_tables.py`, `tests/zipfixtures.py`, `tests/test_layering.py`, `pyproject.toml`
**Files scanned:** about 14 read in full or by range; `git ls-files` confirmed tracking for the modules and tests named above
**Pattern extraction date:** 2026-10-19
**Not re-checked:** `tests/test_kicad_files*.py` file names (analog named by convention; planner should `Glob tests/test_kicad_files*.py` and `tests/conftest.py` before editing)
