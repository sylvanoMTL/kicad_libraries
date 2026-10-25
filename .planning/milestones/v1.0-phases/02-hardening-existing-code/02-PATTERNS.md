# Phase 2: Hardening Existing Code - Pattern Map

**Mapped:** 2026-10-18
**Files analyzed:** 22 new/modified/deleted
**Analogs found:** 22 / 22 (all analog paths verified git-tracked via `git ls-files`)

All paths are relative to `C:/Git_Repo_Clones/Kicad_Libraries-importer`. Line numbers refer to the current worktree files.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `kicad_lib_manager/models.py` (mod: `ScanResult.issues`, `collision_peers`) | model | transform | itself (dataclass conventions, lines 5-48) | exact |
| `kicad_lib_manager/fsutil.py` (mod: `backup_file(number=)`, WR-04, IN-01) | utility | file-I/O | itself (`backup_file` 144-179) | exact |
| `kicad_lib_manager/kicad_files.py` (mod: table accessor, `retarget_model`, WR-01/IN-04) | service | transform | itself (`find_models` 134-143, `lib_table_entries` 146-180) | exact |
| `kicad_lib_manager/kicad_process.py` (NEW) | utility | request-response (subprocess) | `fsutil.py` (Qt-free, returns values, narrow except) + RESEARCH "Process detection" snippet | role-match |
| `kicad_lib_manager/table_generator.py` (REWRITE) | service | file-I/O + transform | itself (public API) + `fsutil.atomic_write_text/backup_file` + `kicad_files.load` | role-match |
| `kicad_lib_manager/library_scanner.py` (mod: version sort, `sync_kicad_path_vars`, collisions, model checks) | service | file-I/O + batch | itself | exact |
| `kicad_lib_manager/main_window.py` (mod: busy guard, Issue routing, selection policy) | controller | event-driven | itself (`_start_scan` 261-280, `_on_generate` 358-405) | exact |
| `kicad_lib_manager/widgets/library_table.py` (mod: `rel_path` keys, exclusivity, no-resync populate) | component | event-driven | itself (`populate` 64-143, `_sync_footprint_selection` 171-192) | exact |
| `kicad_lib_manager/widgets/log_panel.py` (mod: `log_issue`, `html.escape`) | component | event-driven | itself (`log` 31-36) | exact |
| `kicad_lib_manager/widgets/backup_dialog.py` | component | request-response | itself (unchanged; consumes `list_backup_pairs`) | exact |
| `generate_lib_tables.py` (DELETE) and `CLAUDE.md`, `README.md` mention edits | config | n/a | n/a | n/a |
| `tests/test_table_merge.py` (NEW) | test | transform | `tests/test_kicad_files.py`, `tests/test_edits.py`, `tests/fixtures/tables/*` | role-match |
| `tests/test_write_tables.py` (NEW) | test | file-I/O | `tests/test_fsutil.py` (lines 59-104) | role-match |
| `tests/test_kicad_config.py` (NEW) + `tests/fixtures/kicad/*` | test | file-I/O | `tests/test_fsutil.py`, `tests/fixtures/build_fixtures.py` | role-match |
| `tests/test_kicad_process.py` (NEW) | test | request-response | `tests/test_fsutil.py` (monkeypatch style) | role-match |
| `tests/test_scanner_issues.py` (NEW) | test | batch | `tests/test_scanner_skip_dirs.py` | exact |
| `tests/test_main_window.py` (NEW) | test | event-driven | `tests/test_library_table_widget.py` + RESEARCH Pattern 5 recipe | role-match |
| `tests/test_log_panel.py` (NEW) | test | event-driven | `tests/test_library_table_widget.py` | role-match |
| `tests/test_library_table_widget.py` (extend) | test | event-driven | itself | exact |
| `tests/test_scanner_skip_dirs.py` (update to Issues) | test | batch | itself (lines 48-58) | exact |
| `tests/test_layering.py` (extend `ALLOWED`) | test | transform | itself (lines 14-19, 63-68) | exact |
| `tests/test_fsutil.py`, `tests/test_kicad_files.py`, `tests/test_edits.py` (extend) | test | mixed | themselves | exact |

## Pattern Assignments

### `kicad_lib_manager/table_generator.py` (service, file-I/O + transform) - REWRITE

**Analogs:** the Phase 1 primitives (`fsutil.py`, `kicad_files.py`, `sexpr.py`) for mechanics; the current `table_generator.py` for the public API shape to preserve.

**Keep these public names** (consumed elsewhere): `ENV_VAR`, `_MANAGED_MARKER` (`table_generator.py:7-8`, imported by `main_window`), `MergeResult` (59-68, `__slots__` style), `generate_sym_lib_table`, `generate_fp_lib_table`, `write_tables`, `list_backup_pairs` (222-242, used by `backup_dialog`), `restore_backup_pair`.

**Delete:** `_LIB_ENTRY_RE`, `parse_lib_table`, `count_table_entries`, `backup_existing`, `_check_nickname_collisions`, `list_backups`, `restore_backup` (dead code).

**Imports pattern** (from `fsutil.py:1-11` and `kicad_files.py:1-7`; relative imports, services depend downward only):
```python
from . import fsutil, kicad_files
from .models import FootprintLibrary, Issue, Severity, SymbolLibrary
from .sexpr import Edit, apply_edits, quote
```

**Entry formatting** - replace `_format_entry` (50-56, no escaping) with `quote()` for every value (D-10), same layout:
```python
# current layout to keep (table_generator.py:50-56)
f'  (lib (name "{name}")(type "{lib_type}")'
f'(uri "{uri}")'
f'(options "{options}")(descr "{descr}"))'
# new: f'(lib (name {quote(name)})(type {quote(t)})(uri {quote(uri)})(options {quote(o)})(descr {quote(d)}))'
```

**Core splice pattern** - copy the `_whole_line` helper and the edit-building loop from 02-RESEARCH.md Pattern 1 (prototype verified on all five `tests/fixtures/tables/*`). Classification of table children follows the RESEARCH rules table. Accessor needed in `kicad_files` (see below) to get the table node.

**Managed identity** (verified `table_generator.py:105,122`): managed URI is `f"${{{ENV_VAR}}}/{lib.rel_path}"`; match managed entries by `uri.removeprefix(_MANAGED_MARKER)` == `rel_path`, never by nickname.

**Per-file write + Issue pattern** (copy flow from `fsutil.py` Issue contract; error codes `fs.read_only` 85-90, `fs.locked` 107-115, `fs.write_failed` 116-121, `fs.backup_failed` 174-179):
```python
result = fsutil.backup_file(path, path.parent, number=n)   # new keyword, Issue on failure => skip write
if isinstance(result, Issue):
    issues.append(result); continue
err = fsutil.atomic_write_text(path, new_text, bom=source.bom)
if err is not None:
    issues.append(err); continue
issues.append(Issue(Severity.SUCCESS, "table.written", f"Written {label}: ..."))
```
Each table is independent (HARD-02); an unparseable table gets the Issue from `kicad_files.load` and no backup/no write (D-09). Shared backup number: compute `N = max(max_sym, max_fp) + 1` once (Pattern 2) so `list_backup_pairs` pairing holds.

**Severity mapping** (replaces `main_window.py:384-397` substring logic): removed-because-deselected = INFO; stale managed (D-08) = WARNING `table.stale_managed`; external clash (D-03) = WARNING `table.external_clash`; unclassifiable child (D-07) = WARNING `table.unclassified`; unparseable = ERROR (from load); duplicate selected nickname = ERROR `table.duplicate_nickname`.

**`restore_backup_pair`** (current 262-274 uses `shutil.copy2`, can raise): convert to `list[Issue]`, read backup bytes, `fsutil.backup_file` current table, then `fsutil.atomic_write_bytes`.

---

### `kicad_lib_manager/kicad_files.py` (service, transform) - extend

**Analog:** itself.

**Accessor to add** next to `lib_table_entries` (146-180). It reuses the private `_top_level` helper (81-87):
```python
def lib_table_entries(root: Node) -> list[LibEntry]:
    table = _top_level(root, lambda head: head.endswith("_lib_table"))
    ...
```
New `lib_table(root) -> LibTable | None` with `node`, `tag`, `entries`, `others` (children that are not `lib`).

**WR-01 / IN-04 fixes** in the field loop (158-167):
```python
if head in _LIB_FIELDS and len(field.children) >= 2 and head not in value_nodes:
    value_nodes[head] = field.children[1]     # WR-01: require field.children[1].kind in ("str", "atom")
elif len(field.children) == 1:
    flags.append(head)                        # IN-04: value-less field heads of _LIB_FIELDS go to extras
```

**`retarget_model` helper** (mirrors `find_models` 134-143 / `ModelRef` 42-45; returns an `Edit`, never mutates):
```python
def retarget_model(ref: ModelRef, new_path: str) -> Edit:
    """Return the edit that replaces only the model path token."""
    return Edit(ref.path_node.start, ref.path_node.end, quote(new_path))
```
Add `Edit, quote` to the `from .sexpr import ...` line (currently `Node, SexprError, parse, unquote`).

---

### `kicad_lib_manager/fsutil.py` (utility, file-I/O) - extend

**Analog:** itself, `backup_file` (144-179).

Add keyword `number: int | None = None`: when given, skip the `max_num + 1` scan (149-154) and start the exclusive-create loop at that number (the loop at 156-163 already bumps on `FileExistsError`). Default behaviour must stay unchanged (`test_backup_file_numbers_like_table_generator`). Fix IN-01: wrap `shutil.copystat` (172) so its failure does not report a complete backup as failed. WR-04: see `01-REVIEW.md`.

**Test style to copy for new fsutil tests** - `tests/test_fsutil.py:59-72` (read-only via `os.chmod`, restore in `finally`) and 90-104 (lock simulation):
```python
def always_denied(src, dst):
    raise PermissionError(13, "Access is denied")
monkeypatch.setattr(fsutil.os, "replace", always_denied)
result = atomic_write_bytes(target, b"new", retry_delays=delays, sleep=recorder)
assert result.code == "fs.locked"
```

---

### `kicad_lib_manager/library_scanner.py` (service, file-I/O + batch) - modify

**Analog:** itself. Keep these shapes: `progress(message, current, total)` callback (155, 176, 235), `_collect_files` / `_in_skip_dir` (138-147), `_determine_source` (131-135).

**Version selection** (HARD-04) - replace the lexical sort at 31-35 and 104-107 (`sorted(..., reverse=True)`) with `parse_version` / `newest_version_dirs` from RESEARCH Pattern 4. Make base dirs injectable (`find_kicad_config_dir(base=None)`, `find_kicad_footprint_dir(base=None)`). Keep the existing platform branches:
```python
if sys.platform == "win32":
    appdata = os.environ.get("APPDATA") ...
    base = Path(appdata) / "kicad"
elif sys.platform == "darwin":
    base = Path.home() / "Library" / "Preferences" / "kicad"
else:
    base = Path.home() / ".config" / "kicad"
```

**`sync_kicad_path_vars`** (38-87) -> `list[Issue]`. Reuse as-is: `repo_str = str(repo_root).replace("\\", "/")` and the `desired` dict (56-60). Replace:
- `config_file.read_text` (49) with `fsutil.read_source`; Issue-returning.
- `env.setdefault("vars", {})` (53-54) crash on `vars: null` with `env.get("vars") or {}`.
- `write_text(json.dumps(config, indent=2) + "\n")` (78-80) with: backup to `default_backup_dir()/"kicad_common"/"<N.M>"`, `json.dumps(config, indent=2, ensure_ascii=False) + "\n"`, `normalize_eol(text, src.eol)`, D-13 re-parse assertion (`_only_vars_changed` in RESEARCH), `fsutil.atomic_write_text(..., bom=src.bom)`, prune to 10 backups catching `OSError`.
- Per-key message strings (67-74) become INFO/SUCCESS Issues; "not found"/"Failed" become WARNING/ERROR Issues with codes like `config.not_found`.

**Scan Issues** - `cross_reference` (207-227) and `check_3d_model_paths` (230-250) return `list[str]`; convert to `list[Issue]` (`scan.footprint_lib_missing`, `scan.model_var`, `scan.model_missing`, `scan.nickname_collision`). `ScanResult.warnings` becomes `issues`.

**Model check via parser** (replace `MODEL_RE` 11, 236-249): `kicad_files.load(path)` -> `footprint_name(root).node` -> `find_models(node)`. Existing non-Custom rule to preserve (244-249):
```python
if path.startswith("${"):
    continue
if "/" in path or "\\" in path:
    ...warn
```
Custom rule (D-18/D-19): must start with `${CUSTOM_3DMODEL_DIR}/`, and the remainder must exist by exact name in a set built once from `Custom/3DModels` (do not use `Path.exists()`).

**`_parse_footprint_refs`** (187-204) uses `FOOTPRINT_RE` plus `read_text`; keep unless the plan routes it through `kicad_files.find_property` (optional).

---

### `kicad_lib_manager/kicad_process.py` (utility, subprocess) - NEW

**Analog:** `kicad_lib_manager/fsutil.py` for module style (stdlib only, no Qt, `Issue`-free pure function returning values, narrow `except OSError`). Copy the `kicad_running()` implementation from 02-RESEARCH.md "Process detection (D-15)" (absolute `System32\tasklist.exe`, `csv` parsing, exact-name matching, `except (OSError, subprocess.SubprocessError): return []`). Caller (`sync_kicad_path_vars`) turns a non-empty result into WARNING `config.kicad_running`.

---

### `kicad_lib_manager/models.py` (model) - extend

**Analog:** itself. Dataclass conventions (5-33): `@dataclass`, `field(default_factory=list)`, no internal imports.
```python
@dataclass
class SymbolLibrary:
    nickname: str
    rel_path: str
    source: str
    footprint_refs: list[FootprintRef] = field(default_factory=list)
    selected: bool = False
```
Add `collision_peers: list[str] = field(default_factory=list)` to `SymbolLibrary` and `FootprintLibrary`; rename `ScanResult.warnings: list[str]` to `issues: list[Issue]` (`Issue` is defined later in the same file at 44-48; move it above `ScanResult` or use a forward-safe ordering). `Severity` (36-41) values equal `LogPanel` color keys; always pass `.value`.

---

### `kicad_lib_manager/main_window.py` (controller, event-driven) - modify

**Analog:** itself.

**Busy guard** - `_start_scan` (261-280) overwrites `self._worker` unguarded. Add at the top:
```python
if self._worker is not None:
    self._log.log("Scan already running.", "info")
    return
```
Guard on `self._worker is not None`, not `isRunning()` (see RESEARCH Pattern 5). Keep the existing worker wiring (276-280):
```python
self._worker = ScanWorker(REPO_ROOT, self._kicad_fp_dir)
self._worker.progress.connect(self._on_scan_progress)
self._worker.finished.connect(self._on_scan_finished)
self._worker.error.connect(self._on_scan_error)
self._worker.start()
```
Clear busy state via `try/finally` in `_on_scan_finished` (286-309; currently `self._worker.wait(); self._worker = None` at 308-309) and `_on_scan_error` (352-356). Hold action objects as `self._act_*` to disable Rescan / Set KiCad Path / Generate while busy.

**Issue routing** - replace the substring branches at 384-397:
```python
if msg.startswith("Warning:") or "removed" in msg: level = "warning"   # DELETE
if "Failed" in msg or "Could not" in msg or "not found" in msg: ...    # DELETE
```
with a single `_log_issues(issues)` calling `self._log.log_issue(issue)`.

**Selection policy** - `_apply_existing_selection` (311-350) is startup-only and must match by `rel_path` (`uri.removeprefix(_MANAGED_MARKER)`) through `kicad_files`, not `parse_lib_table` nickname lookup (324-329). Rescan (`_on_rescan` 407-410, `_on_set_kicad_path` 421-435) snapshots selected `rel_path`s from the old `self._scan_result` and re-applies to the new result (D-04).

**Consolidate** `_check_existing_tables` (246-259) and `_on_dest_changed` (450-463) into one `_log_existing_tables(dest)` (D-05); both currently use `count_table_entries`.

**History combo block/unblock pattern to keep** (401-405):
```python
self._dest_combo.blockSignals(True)
self._dest_combo.clear()
self._dest_combo.addItems(history)
self._dest_combo.setCurrentIndex(0)
self._dest_combo.blockSignals(False)
```

---

### `kicad_lib_manager/widgets/library_table.py` (component, event-driven) - modify

**Analog:** itself.

**Keying** - `self._fp_items: dict[str, QTreeWidgetItem]` keyed by nickname (58, 134) -> key by `lib.rel_path`.

**No resync on populate** - delete lines 140-143:
```python
sources = sorted(set(lib.source for lib in self._fp_libs))
for source in sources:
    self._sync_footprint_selection(source)
```
(populate must render the `selected` flags as given; sync stays on user toggles).

**Source-scoped `needed`** - `_sync_footprint_selection` (171-192) builds `needed` from all selected symbols (177-181). Restrict to `lib.source == source`.

**Re-entrancy pattern to reuse for mutual exclusion** (183-192, `self._updating` set/clear around programmatic changes; model flag updated alongside widget):
```python
self._updating = True
...
fp_item.setCheckState(0, state)
fp_lib.selected = should_check
self._updating = False
```
Exclusivity: in `_on_sym_item_changed` / `_on_fp_item_changed` (145-169, 194-199), when a lib is checked, uncheck items for its `collision_peers` under `_updating`. `_set_all_check_state` (213-237) uses `blockSignals(True/False)` pairs; keep that pairing and make Select All skip a collided lib if a peer is already selected.

**Warning style to reuse for collision mark** (108-112):
```python
item.setIcon(3, warn_icon)
orange = QBrush(QColor("#CC7700"))
for col in range(item.columnCount()):
    item.setForeground(col, orange)
```
Add a tooltip naming the peer.

---

### `kicad_lib_manager/widgets/log_panel.py` (component, event-driven) - modify

**Analog:** itself (`log` 31-36). Add:
```python
import html
def log_issue(self, issue: Issue):
    self.log(issue.text, issue.severity.value)
```
and wrap the message with `html.escape(message)` inside the f-string at 35. Import `Issue` from `..models` (widgets may depend on `models`).

---

### `tests/test_table_merge.py`, `tests/test_write_tables.py` (test, transform / file-I/O) - NEW

**Analogs:** `tests/test_fsutil.py` (tmp_path + monkeypatch + Issue assertions, quoted above), `tests/test_roundtrip_corpus.py` / `tests/test_fixtures.py` for fixture loading, `tests/fixtures/tables/{basic,empty,escaped,flags,reordered}.*`.

Assertion style from `test_fsutil.py:59-69`:
```python
result = atomic_write_bytes(target, b"new", sleep=recorder)
assert isinstance(result, Issue)
assert result.severity is Severity.ERROR
assert result.code == "fs.read_only"
assert target.read_bytes() == b"original\r\n"
```
Required cases: bytes outside managed spans identical (CRLF and LF), `(version 7)` kept, unclassifiable kept + warning, escaped name round-trip through `kicad_files.lib_table_entries`, D-03/D-08/D-09, locked and read-only per file, shared backup number. To avoid a 1 s sleep in lock tests, forward `retry_delays` or patch `fsutil` defaults.

---

### `tests/test_kicad_config.py`, `tests/test_kicad_process.py` (test, file-I/O) - NEW

**Analog:** `tests/test_fsutil.py` for monkeypatching and `tmp_path` trees; `tests/fixtures/build_fixtures.py` to generate `tests/fixtures/kicad/*.json` (fixtures dir is `-text` in `.gitattributes`). Build `tmp_path/{8.0,9.0,10.0,"kicad-extras"}` trees for version tests; inject base dirs instead of patching `sys.platform`. Monkeypatch `subprocess.run` for `kicad_running`.

---

### `tests/test_scanner_issues.py` (test, batch) - NEW; `tests/test_scanner_skip_dirs.py` (update)

**Analog:** `tests/test_scanner_skip_dirs.py` - synthetic repo builder (22-30) and the call style:
```python
def _build_repo(root: Path) -> None:
    (root / "Custom" / "Symbols").mkdir(parents=True)
    (root / "Custom" / "Symbols" / "A.kicad_sym").write_bytes(b"(kicad_symbol_lib)\n")
    (root / "Custom" / "Footprints" / "F.pretty").mkdir(parents=True)
```
Lines 48-49 and 57-58 assert `m.startswith("[tests/")` on strings; change to `issue.text.startswith(...)` once `check_3d_model_paths` returns Issues. Add `_MOD_WITH_ABSOLUTE_MODEL`-style byte constants for `${KIPRJMOD}`, `${CUSTOM_3DMODEL_DIR}`, `${WE_3DMODEL_DIR}`, and `.STEP`/`.step` case cases. Live check against real `Custom/` should skip when empty.

---

### `tests/test_main_window.py` (test, event-driven) - NEW

**Analog:** `tests/test_library_table_widget.py` (pytest-qt `qtbot.addWidget`, fixture-built `ScanResult`, lines 9-49) plus the verified recipe in 02-RESEARCH.md Pattern 5 (autouse `QSettings.setPath` redirect, patch `load_kicad_fp_dir`, `REPO_ROOT`, `scan_all` with a `threading.Event` gate). Put the `QSettings.setPath` redirect in an autouse fixture (in `tests/conftest.py` or the test file) so the owner's real settings are never touched. `tests/conftest.py:8` already forces `QT_QPA_PLATFORM=offscreen`.

---

### `tests/test_library_table_widget.py` (extend)

**Analog:** itself. The single adaptation point (comment at line 33: "Phase 2 adapts one place"):
```python
def _fp_item(widget, nickname):
    return widget._fp_items[nickname]
```
Change to look up by `rel_path`. Existing `scan` fixture (9-30) is the template for collision fixtures (same nickname in Custom and Wurth). Add tests: both items kept, checking one unchecks peer, Select All respects exclusivity, footprint with no referencing symbol survives `populate`, source-scoped `needed`.

---

### `tests/test_layering.py` (extend)

**Analog:** itself. Add entries to `ALLOWED` (14-19):
```python
ALLOWED = {
    "models": set(), "sexpr": set(), "fsutil": {"models"},
    "kicad_files": {"sexpr", "fsutil", "models"},
    # add: "table_generator": {"fsutil","kicad_files","models","sexpr"},
    #      "library_scanner": {"fsutil","kicad_files","models"},
    #      "kicad_process": set()
}
```
and the module list in `_CODE` (21-29) for the no-Qt subprocess check. `test_imports_point_only_downward` (63-68) parametrises over `ALLOWED`, so new keys are picked up automatically.

---

### `tests/test_log_panel.py` (NEW)

**Analog:** `tests/test_library_table_widget.py` (qtbot widget pattern). Iterate every `Severity` through `log_issue`; assert HTML escaping of `<` and `&`.

---

### HARD-09 one-off (no committed source file)

Uses `kicad_files.load` + `find_models` + `retarget_model` + `sexpr.apply_edits` + `fsutil.encode_source` + `fsutil.atomic_write_bytes` in a scratch script (run with `python -I`, outside the repo). Follow RESEARCH Pattern 7 steps. Unit coverage for the helper goes in `tests/test_edits.py` (`-k retarget`); copy that file's existing edit-test style (fixtures `two_models.kicad_mod`, `crlf`, `bom` in `tests/fixtures/sexpr/`).

## Shared Patterns

### Issue contract (services never raise for expected failures)
**Source:** `kicad_lib_manager/models.py:36-48`, `kicad_lib_manager/fsutil.py:27-68`
**Apply to:** `table_generator`, `library_scanner`, `kicad_files` additions, `kicad_process` callers
```python
return Issue(Severity.ERROR, "fs.read_failed", f"Could not read {path.name}: {e.strerror or e}")
```
Functions return `X | Issue` (read side) or `Issue | None` (write side); aggregate into `list[Issue]` at the service boundary. Codes are dotted `area.reason`.

### Atomic write plus backup
**Source:** `kicad_lib_manager/fsutil.py:76-141` (`atomic_write_bytes`, `atomic_write_text`), `144-179` (`backup_file`)
**Apply to:** table writes, `kicad_common.json` write, `restore_backup_pair`, HARD-09 script. Never use `Path.write_text` (translates newlines on Windows). Preserve `SourceText.bom` / `.eol` from `read_source`.

### Span-splice edits (never re-serialise)
**Source:** `kicad_lib_manager/sexpr.py` (`Edit`, `apply_edits`, `quote`, `unquote`), `kicad_files.py` node types
**Apply to:** table merge, `retarget_model`. Insert text with `source.eol`; new files use `"\n"`.

### Issue routing in the GUI
**Source:** to be created in `widgets/log_panel.py` (`log_issue`) and `main_window.py` (`_log_issues`)
**Apply to:** `_on_generate`, `_on_scan_finished`, `_on_restore_backup`, sync results. No substring checks on message text.

### Qt feedback-loop guards
**Source:** `widgets/library_table.py:183-192` (`self._updating`), `213-232` (`blockSignals` pairs), `main_window.py:401-405`
**Apply to:** exclusivity logic, selection restore, any programmatic check-state change.

### Test harness
**Source:** `tests/conftest.py` (offscreen forced at line 8; `repo_root`, `assert_tiles` fixtures), `pyproject.toml` pytest config, run command `./env/Scripts/python.exe -m pytest -q`. Services tested with `tmp_path`; Qt tests use `qtbot`.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `kicad_lib_manager/kicad_process.py` | utility | subprocess | No existing `subprocess` use in the repo; use RESEARCH "Process detection" snippet and `fsutil.py` for module style |
| `tests/test_main_window.py` | test | event-driven | No existing `MainWindow` test; use RESEARCH Pattern 5 recipe on top of the widget test style |

## Metadata

**Analog search scope:** `kicad_lib_manager/`, `kicad_lib_manager/widgets/`, `tests/`, `tests/fixtures/` (git-tracked files only; no gitignored mirrors involved)
**Files scanned:** 13 source files read in full or by range, 4 test files, 2 planning docs
**Pattern extraction date:** 2026-10-18
