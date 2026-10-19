# Phase 3: Package Intake and Naming - Pattern Map

**Mapped:** 2026-10-19
**Files analyzed:** 16 new (no existing source modified except optional helpers in `kicad_files.py`, and `tests/test_layering.py` / `tests/conftest.py` extended)
**Analogs found:** 14 / 16 (all analog paths verified git-tracked via `git ls-files`)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `kicad_lib_manager/importer/__init__.py` (+ `adapters/__init__.py`) | config | n/a | `kicad_lib_manager/widgets/__init__.py` (empty) | exact |
| `kicad_lib_manager/importer/layout.py` | utility | file-I/O (fresh dir listing) | `kicad_lib_manager/library_scanner.py` `find_footprint_libs` / `_collect_files` (L293-335) | role-match |
| `kicad_lib_manager/importer/package.py` | service | file-I/O + batch | `kicad_lib_manager/fsutil.py` (Issue-returning I/O, `read_source`) | role-match |
| `kicad_lib_manager/importer/candidate.py` | model | transform | `kicad_lib_manager/kicad_files.py` frozen dataclasses (L12-58) | exact |
| `kicad_lib_manager/importer/naming.py` | utility | transform | `kicad_lib_manager/library_scanner.py` `_collide` (L357-379) + `fsutil.decode_source` (Issue returns) | role-match |
| `kicad_lib_manager/importer/adapters/base.py` | service | transform | `kicad_files.py` `parse_bytes` / `find_*` read-side API | role-match |
| `kicad_lib_manager/importer/adapters/ultralibrarian.py` | service | transform | `kicad_files.py` | partial |
| `kicad_lib_manager/importer/adapters/loose.py` | service | file-I/O | `library_scanner._collect_files` | partial |
| `kicad_lib_manager/kicad_files.py` (optional `file_kind`, `file_version`) | utility | transform | itself, `footprint_name` L130-138 | exact |
| `tests/conftest.py` (add `ul_zip`, `make_zip`) | test | n/a | `tests/conftest.py` `repo_root` fixture L16-18 | exact |
| `tests/test_importer_layering.py` | test | n/a | `tests/test_layering.py` | exact |
| `tests/test_package_zip.py`, `test_package_folder.py`, `test_legacy_rules.py` | test | file-I/O | `tests/test_scanner_issues.py` | role-match |
| `tests/test_adapters.py` | test | transform | `tests/test_scanner_issues.py` | role-match |
| `tests/test_naming_sanitize.py`, `test_naming_suggest.py` | test | transform | `tests/test_scanner_issues.py` | role-match |
| `tests/fixtures/...` (only if committed fixtures are needed) | test fixture | n/a | `tests/fixtures/build_fixtures.py` | exact |

## Pattern Assignments

### `importer/candidate.py` (model, transform)

**Analog:** `kicad_lib_manager/kicad_files.py`. Frozen dataclasses, `X | None` unions, tuples for immutable collections (L12-58):
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class NameRef:
    name: str
    node: Node
    name_node: Node
```
Use `@dataclass(frozen=True)` for `ImportCandidate`, `SymbolItem`, `FootprintItem`, `ModelItem`, `PartMeta`, `NameResult`, `LibrarySuggestion`, `TokenChoice`, `RankedLibrary`. Use `field(default_factory=list)` only for mutable ones (`models.py`). Importer dataclasses live in the importer package; `models.py` stays import-free.

### Issue contract (all importer modules)

**Source:** `kicad_lib_manager/models.py` L1-21 and `fsutil.py` L28-40, L66-76:
```python
from .models import Issue, Severity   # from importer/: from ..models import Issue, Severity

def decode_source(data: bytes, name: str) -> SourceText | Issue:
    ...
        return Issue(
            Severity.ERROR,
            "fs.bad_encoding",
            f"Could not read {name}: not valid UTF-8 (byte {e.start})",
        )
```
Rules to copy: dotted lowercase `code` (`intake.hostile_member`, `naming.reserved`); `Could not ...` phrasing; `list[Issue]` / `X | Issue` returns, never raise for expected failures; I/O wrapped as `except OSError as e: ... e.strerror or e`.

### `importer/package.py` (service, file-I/O)

**Analog:** `fsutil.py` (Issue-returning I/O, exclusive-create write at L107-115):
```python
with open(tmp, "xb") as f:
    created = True
    f.write(data)
```
Copy `"xb"` exclusive create for staged files. Module-level `UPPER_SNAKE` caps (`MAX_MEMBERS`, `MAX_MEMBER_BYTES`, `MAX_TOTAL_BYTES`, `MAX_RATIO`, `RATIO_MIN_SIZE`) read as module globals at call time (no default-arg capture, so tests can monkeypatch). Progress callback shape from `library_scanner.py` L300-306: `progress: Callable | None = None`, then `if progress: progress(f"...", i, total)`. Zip pre-scan, `_hostile_reason`, `_copy_capped` and the context manager: follow RESEARCH.md Pattern 1/2 and its Code Examples (no codebase analog; stdlib `zipfile`).

### `importer/layout.py` (utility, file-I/O)

**Analog:** `library_scanner.py` L293-335 (fresh listing, `Path` everywhere, `sorted`, `.stem` as nickname, `.as_posix()`):
```python
pretty_dirs = sorted(
    d for d in root.rglob("*.pretty")
    if d.is_dir() and not _in_skip_dir(d, root)
)
...
nickname=d.stem,
```
Use the same for `list_symbol_libs` (`Custom/Symbols/*.kicad_sym` stems) and `list_footprint_libs` (`Custom/Footprints/*.pretty` stems). A frozen `RepoLayout` dataclass holds `custom_dir`, `symbols_dir`, `footprints_dir`, `models_dir`. Do NOT read `MainWindow._scan_result` (D-03).

### `importer/adapters/base.py`, `ultralibrarian.py`, `loose.py` (service, transform)

**Analog:** `kicad_files.py` read-side API. Parse staged bytes, branch on `LoadedFile | Issue`:
```python
loaded = parse_bytes(data, name)          # kicad_files.py L71-73
if isinstance(loaded, Issue):
    issues.append(loaded); continue
for sym in find_symbols(loaded.root): ...  # L95-106
prop = find_property(sym.node, "Reference") # L117-127 -> PropertyRef.value
fp = footprint_name(loaded.root)            # L130-138, accepts "footprint" or "module"
models = find_models(fp.node)               # L141-150
```
Take names from inside files (UL symbol file is a timestamp). `isinstance(x, Issue)` early-out is the established idiom (`_parse`, L61-62). Registry, confidence scoring and the legacy matrix: RESEARCH.md Patterns 3-4. Pitfall 7: `footprint_name` accepts `module`; add `file_kind(root)` / `file_version(root)` helpers to `kicad_files.py` (use `_top_level`, L81-87) rather than touching `Node` from the importer.

### `importer/naming.py` (utility, transform)

**Analog:** `library_scanner._collide` (L357-379) for Issue-emitting pure helper, and the case-clash shape:
```python
issues.append(Issue(
    Severity.WARNING,
    "scan.nickname_collision",
    f"[{nickname}] {kind} library nickname is used by ...",
))
```
Mirror for `naming.case_clash` (WARNING), `naming.truncated`, `naming.reserved`, `naming.empty` (ERROR), `naming.changed` (INFO). Algorithm and tables: RESEARCH.md Patterns 5-6. Constants `UPPER_SNAKE` (`HOST_TOKENS`, `MANUFACTURER_ALIASES`, `REFERENCE_TYPE`, `PLACEHOLDER_TOKENS`, `AGGREGATOR_HOSTS`); private helpers `_x`.

### Tests

**Analog `tests/test_scanner_issues.py` L1-40:** module docstring naming the decisions covered, plain `def test_...` functions, tiny `_helper` builders, and Issue assertions of all three fields:
```python
assert isinstance(issue, Issue)
assert issue.severity is Severity.WARNING
assert issue.code == "scan.nickname_collision"
```
**Analog `tests/test_layering.py`:** copy for `tests/test_importer_layering.py`. Extend with a `ALLOWED`-style dict for importer modules and `_imports()` AST walker (L48-65), and the subprocess no-Qt check (L25-45, `sys.executable, "-I", "-c", ...`). Note existing `ALLOWED` map is keyed by flat module name and `_imports` reads `PACKAGE / f"{module}.py"`, so importer modules need a path-aware variant. Also assert `importer/__init__.py` and `adapters/__init__.py` hold no code (copy `test_package_init_holds_no_code`, L76-84).
**Analog `tests/conftest.py`:** add fixtures beside `repo_root` (L16-18); `REPO_ROOT = Path(__file__).resolve().parent.parent`; point `ul_zip` at `REPO_ROOT / "downloaded_examples" / "ul_CSD85301Q2.zip"` (read in place, never extracted into the repo). `make_zip` builders generate hostile zips in `tmp_path` (build backslash names with `chr(92)`, per Pitfall 1). `tests/fixtures/build_fixtures.py` is the model if a committed byte-exact fixture is ever needed.

## Shared Patterns

### Issue-returning services, no Qt
**Source:** `models.py` L1-21; `fsutil.py` L28-76. **Apply to:** every `importer/*.py`. No `PySide6`, no `main_window`/`widgets` imports; relative imports (`from ..models import ...`, `from ..kicad_files import ...`).

### Path handling
**Source:** `library_scanner.py` L293-335. `Path` for inputs, `.as_posix()` for stored strings, `.stem` as nickname. Compare resolved paths with `is_relative_to` for the staging-outside-repo check (RESEARCH Pitfall 14).

### Progress callback
**Source:** `library_scanner.py` L300-306. `progress: Callable | None = None`, called `progress(message, current, total)`.

### Placeholder-token contract (D-04)
Expose `placeholder_tokens(name)`; Phase 4/5 must refuse install while non-empty. No codebase analog.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `importer/package.py` zip pre-scan, capped streaming copy, `TemporaryDirectory` staging | service | batch/streaming | No zip or temp-dir code exists; use RESEARCH.md Pattern 1/2 and Code Examples |
| `importer/naming.py` sanitiser and suggestion tables | utility | transform | No sanitiser exists; use RESEARCH.md Patterns 5-6 (prototype verified against all 64 existing `Custom/` names) |

## Metadata

**Analog search scope:** `kicad_lib_manager/*.py`, `tests/`, `tests/fixtures/`
**Files read:** `kicad_files.py`, `fsutil.py` (L1-120), `tests/conftest.py`, `tests/test_layering.py`, `tests/test_scanner_issues.py` (head), `library_scanner.py` (L281-380), `models.py`
**Tracked-source check:** all named analogs appear in `git ls-files`; no gitignored mirror paths used
**Pattern extraction date:** 2026-10-19
