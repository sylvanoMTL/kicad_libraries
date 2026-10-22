# Phase 5: Import UI and Post-Install - Pattern Map

**Mapped:** 2026-10-20
**Files analyzed:** 22 (11 new source, 6 modified source, 5 new test files + 3 modified tests)
**Analogs found:** 20 / 22 (all paths verified git-tracked; line numbers from current source, not the stale codebase map)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `kicad_lib_manager/widgets/theme.py` (new) | config (constants) | n/a | `widgets/log_panel.py` `COLORS` (lines 10-15) | role-match |
| `kicad_lib_manager/widgets/workers.py` (new) `TaskWorker(QThread)` | service (thread) | event-driven | `main_window.py` `ScanWorker` (35-55) | exact (with signal rename) |
| `kicad_lib_manager/widgets/import_dialog.py` (new) | component (dialog) | request-response + event-driven | `widgets/backup_dialog.py` (whole file) | role-match |
| `kicad_lib_manager/widgets/conflict_row.py` (new) | component | event-driven | `widgets/backup_dialog.py` (signal wiring) | partial |
| `kicad_lib_manager/widgets/preview_tree.py` (new) | component | transform (plan -> tree) | `widgets/library_table.py` `populate` (65-158) | role-match |
| `kicad_lib_manager/widgets/content_view.py` (new) | component (dialog) | file-I/O (read-only) | `widgets/backup_dialog.py` + `log_panel.py` font setup | partial |
| `kicad_lib_manager/importer/preview.py` (new, Qt-free) | utility | transform | `importer/plan.py` (frozen dataclasses) + `table_generator.py` (pure functions returning Issues) | role-match |
| `kicad_lib_manager/importer/plan.py` (mod: `InstallOptions.cleared`) | model | transform | itself (lines 38-69) | exact |
| `kicad_lib_manager/importer/planner.py` (mod: manufacturer, WR-02) | service | transform | itself (lines 750-763) | exact |
| `kicad_lib_manager/table_generator.py` (mod: `add_library_entries`) | service | file-I/O | `write_tables` + `_merge_table` (69-204, 232-296) | exact |
| `kicad_lib_manager/settings.py` (mod: `load/save_import_dir`) | config | CRUD | `load_kicad_fp_dir` / `save_kicad_fp_dir` (27-41) | exact |
| `kicad_lib_manager/main_window.py` (mod) | controller | event-driven | itself (`_build_menu`, `_set_scan_running`, `_start_scan`, `_on_scan_finished`) | exact |
| `kicad_lib_manager/widgets/library_table.py` (mod: `reveal`, try/finally, columns, amber) | component | event-driven | itself | exact |
| `kicad_lib_manager/widgets/log_panel.py` (mod: amber) | component | n/a | itself | exact |
| `kicad_lib_manager/widgets/help_dialog.py` (mod) | component | static | itself (line 163 amber span) | exact |
| `tests/test_importer_layering.py` (mod: `ALLOWED`) | test | n/a | itself (30-95) | exact |
| `tests/test_library_table_widget.py` (mod: `#CC7700` asserts at 330, 347) | test | n/a | itself | exact |
| `tests/test_import_preview.py` (new) | test | n/a | `tests/test_install_plan.py` + `ul_package`/`custom_copy` fixtures (`tests/conftest.py` 79-103) | role-match |
| `tests/test_install_options_clear.py` (new) | test | n/a | `tests/test_install_plan.py` 281-307 | exact |
| `tests/test_table_add_entries.py` (new) | test | file-I/O | `tests/test_main_window.py` generate test (83-110), `tests/fixtures/tables/*` | role-match |
| `tests/test_import_dialog.py`, `tests/test_main_window_import.py`, `tests/test_settings_import.py` (new) | test | n/a | `tests/test_main_window.py` (`_isolated_settings`, `make_window`, 23-80) | exact |

---

## Pattern Assignments

### `widgets/workers.py` — `TaskWorker(QThread)` (service, event-driven)

**Analog:** `kicad_lib_manager/main_window.py` `ScanWorker` (35-55)

```python
class ScanWorker(QThread):
    progress = Signal(str, int)  # message, percentage
    finished = Signal(object)    # ScanResult
    error = Signal(str)

    def __init__(self, repo_root: Path, kicad_fp_dir: Path | None = None):
        super().__init__()
        ...
    def run(self):
        try:
            def on_progress(msg: str, current: int, total: int):
                pct = int(current / max(total, 1) * 100)
                self.progress.emit(msg, pct)
            result = scan_all(self._repo_root, progress=on_progress, kicad_fp_dir=self._kicad_fp_dir)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

Copy: the broad `except Exception` only inside `run()` (thread boundary). Deviate (RESEARCH Pattern 1): name signals `result` / `failed` (not `finished`, which shadows `QThread.finished`), pass `self.progress.emit` as the core `progress(message, current, total)` callback, `progress = Signal(str, int, int)`, accept `parent` and keep a reference so a running QThread is never garbage collected.

**Close ordering** copy from `MainWindow.closeEvent` (620-625): `if self._worker is not None: self._worker.wait()` before destroying.

---

### `widgets/import_dialog.py` (component, dialog + state machine)

**Analog:** `kicad_lib_manager/widgets/backup_dialog.py`

**Imports / class shape** (lines 1-21):
```python
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QDialogButtonBox, QFileDialog,
)
from ..table_generator import list_backup_pairs

class BackupDialog(QDialog):
    def __init__(self, default_folder: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Restore Backup")
        self.setMinimumWidth(500)
        self.selected_backup_num: int | None = None   # public result attrs, read by MainWindow
```

**Browse pattern** (55-61):
```python
def _browse_folder(self):
    folder = QFileDialog.getExistingDirectory(self, "Select backup folder", self._folder_edit.text())
    if folder:
        self._folder_edit.setText(folder)
        self._scan()
```
Use for Browse zip... (`getOpenFileName`) / Browse folder... starting in `load_import_dir()`, then `save_import_dir`.

**Button box + signals** (40-49): `QDialogButtonBox`, `.button(StandardButton.Ok).setEnabled(False)` for gating. Import dialog: `setAutoDefault(False)`/`setDefault(False)` on every button (UI-SPEC), Install not the default.

**How MainWindow uses it** (`main_window.py` 555-560): `BackupDialog(..., parent=self)`, `dialog.exec()`, then reads public attrs. Deviation for Phase 5 (RESEARCH Pattern 3): use `open()` + `installed = Signal(object)` instead of `exec()` so pytest-qt can drive it. Keep `import_dialog` free of any `main_window` import (conventions: lower modules never import `main_window`); the dialog may import `..importer.*`, `..models`, `..settings`, `..table_generator`, `..kicad_process`, `.theme`, `.workers`.

**Dialog rules to follow from repo conventions:**
- Qt enums fully qualified (`Qt.WindowModality.WindowModal`, `QDialogButtonBox.StandardButton.Ok`).
- Programmatic changes wrapped in `blockSignals(True)` ... `finally: blockSignals(False)` (see `_populate_dest_combo` 203-212 and library_table 289-322).
- Editable combo: use `textActivated` for immediate rebuild and `currentTextChanged`/`editingFinished` for debounce. Existing precedent with comment `main_window.py` 171-173:
```python
# Not currentTextChanged: that fires on every keystroke of a typed path
self._dest_combo.textActivated.connect(self._on_dest_changed)
self._dest_combo.lineEdit().editingFinished.connect(self._on_dest_changed)
```
- Errors go to the log (via a signal or returned Issues), never `QMessageBox`.

**Core API call shapes** (inject as constructor args for tests): `open_package(path, repo_root, progress)` (`importer/package.py:251`), `detect_candidate(package)`, `build_plan(candidate, options, layout, tools, *, package_issues, progress)`, `apply_plan(plan, *, backup_root=None, progress=None)` (`applier.py:308`), `list_existing_libraries(layout)` (`layout.py:69`), `kicad_running()` (`kicad_process.py:19`, blocking 5 s subprocess, must run on a worker). `Package.close()` is idempotent (package.py 81-117); dialog owns it.

**Progress caveat** (`applier.py` `_notify` 113-125): a raising progress callback is dropped for the rest of the run, so the callback must only `emit`, never touch widgets. Also `index` never reaches `total`; set 100% on completion.

---

### `widgets/preview_tree.py` (component, transform)

**Analog:** `widgets/library_table.py` `populate` (65-158)

**Section/group pattern** (lines 83-92, 126):
```python
bold_font = self._sym_tree.font()
bold_font.setBold(True)
for source in sources:
    group = QTreeWidgetItem([source])
    group.setFont(0, bold_font)
    self._sym_tree.addTopLevelItem(group)
    ...
    group.setExpanded(True)
```
Copy for the sectioned Files/Renames/Path rewrites/Format/Conflicts/Issues tree. Deviation: before clearing, record expand state per section name and vertical scrollbar value; restore afterwards (D-07).

**Per-severity colour and glyph** — colour via `QBrush(QColor(...))` (115-117):
```python
orange = QBrush(QColor("#CC7700"))     # replace literal with theme.AMBER
for col in range(item.columnCount()):
    item.setForeground(col, orange)
```
**Guard flag:** use `try/finally` (the existing `populate` sets `self._updating = True` at 66 and clears at 158 with NO finally; this is the folded-in fix). Reference of the correct form is `_sync_footprint_selection` 247-262:
```python
previous = self._updating
self._updating = True
try:
    ...
finally:
    self._updating = previous
```
Also: `setAlternatingRowColors(True)` (28), `Qt.ContextMenuPolicy.CustomContextMenu` expand/collapse menu (30-33, 273-277) can be reused.

---

### `widgets/library_table.py` (mod): `reveal()`, try/finally, columns, amber

**Analog:** itself. Items are stored in `self._sym_items` / `self._fp_items` keyed by `rel_path` (58-59).

New `reveal(sym_rel_path, fp_rel_path)` should copy the guard from `_sync_footprint_selection` (247-262) and operate on `self._sym_items.get(rel_path)`: `setCurrentItem`, `scrollToItem`, `item.parent().setExpanded(True)`. Do not rely on `populate` selection (it renders `lib.selected` as given, line 157 comment), so `MainWindow` sets `lib.selected = True` before `populate`.

Edits at known lines: column widths 24-27 and 44-46 (use header `setSectionResizeMode`; Status `ResizeToContents`, Linked Footprints `Stretch`); `font-size: 13px` at 20 and 40 (move to Heading size); `QColor("#CC7700")` at 115 and 148 -> `theme.AMBER`; wrap body 66-158 in try/finally; Status tooltip via `item.setToolTip(3, status)`.

**Test updated:** `tests/test_library_table_widget.py` lines 330 and 347 assert `"#CC7700"`; change to `theme.AMBER.upper()`. Also check `tests/test_log_panel.py` for the warning hex.

---

### `widgets/theme.py` (config)

**Analog:** `widgets/log_panel.py` lines 10-15
```python
COLORS = {
    "info": "#000000",
    "warning": "#CC7700",
    "error": "#CC0000",
    "success": "#007700",
}
```
Plain module constants, no Qt imports. Values per UI-SPEC (AMBER `#8A5200`, etc., `SP_XS..SP_XL = 4, 8, 16, 24, 32`, `PRIMARY_BUTTON_QSS`). `log_panel.COLORS["warning"] = AMBER` (keeps the key = `Severity.value` contract from `log_issue` line 43). Generate button currently inline QSS at `main_window.py` 186-189 -> `PRIMARY_BUTTON_QSS`. Help dialog span at `help_dialog.py:163` uses `#CC7700` literal.

---

### `importer/plan.py` + `importer/planner.py` (mod): `InstallOptions.cleared`, manufacturer, WR-02

**Analog:** itself.

`plan.py` blank rule to extend (lines 38, 65-69):
```python
_TEXT_OVERRIDES = ("value", "datasheet", "description", "manufacturer", "mpn")
def __post_init__(self) -> None:
    for name in _TEXT_OVERRIDES:
        text = getattr(self, name)
        if isinstance(text, str) and not text.strip():
            object.__setattr__(self, name, None)
```
Add `cleared: frozenset[str] = frozenset()`; skip the blank->None conversion for names in `cleared` (store `""`). Update docstring (43-49 says "no way to ask for an empty value"). Tests `test_blank_options_mean_not_set`, `test_blank_option_keeps_ul_vendor_values` (`tests/test_install_plan.py` ~281-307) must stay green unchanged.

`planner.py` 750-763, the inference that defeats an explicit empty Manufacturer:
```python
manufacturer = options.manufacturer if options.manufacturer is not None else meta.manufacturer
if not manufacturer:
    choice = manufacturer_choice(meta)
    if choice.source != "placeholder":
        manufacturer = choice.token
    else:
        issues.append(Issue(Severity.WARNING, "install.manufacturer_missing", "..."))
base_fields = _Fields(..., manufacturer=manufacturer, manufacturer_forced=options.manufacturer is not None)
```
Fix: skip inference and the warning when `options.manufacturer == ""`. Refusal for `value`/`mpn` cleared: `Issue(Severity.ERROR, "install.empty_required", ...)` using the planner's `_err` helper style (`applier.py:23` `_err(code, text)`). WR-02: refuse early with ERROR text from UI-SPEC when `layout.symbols_dir` missing and a library will be created. Issues are returned, never raised.

---

### `importer/preview.py` (Qt-free utility, transform)

**Analogs:** `importer/plan.py` (frozen dataclasses, pure), `table_generator.TableInfo`/`MergeResult` style (small value objects).

Pattern:
```python
@dataclass(frozen=True)
class Reason:
    text: str
    target: str   # "library" | "footprint_name" | "value" | "mpn" | "conflict:<key>" ...
```
Functions: `preview_rows(plan, candidate)`, `field_defaults(candidate, symbol_name)`, `blocking_reasons(state, plan)`, `diff_text(...)`, `carry_resolutions(old, plan)`, `newest_zip(folder)`, `age_text(...)`. Use `MODEL_DIR_VAR` from `plan.py:16`; `plan.library`, `plan.linked_footprint`, `plan.footprint_names`, `plan.model_file`, `op.base_sha256 is None` for new vs modified.

**Mandatory layering registration** (`tests/test_importer_layering.py` `ALLOWED`, lines 30-95), format:
```python
"importer.applier": {"models", "fsutil", "kicad_files", "importer.plan", "importer.kicad_cli", "importer.verify", "importer.layout"},
```
Add `"importer.preview": {...}` and append `"importer.preview"` to `CORE_MODULES` (lines 97-110) if it must load without Qt. No `PySide6`/`kicad_lib_manager` absolute imports, `__init__` stays docstring-only. Escape nothing here; vendor-string escaping is the widgets' job (use `html.escape`, as `log_panel.py` line 38 does).

---

### `table_generator.py` (mod): `add_library_entries` (service, file-I/O)

**Analog:** `write_tables` (232-296) and `_merge_table` insertion branch (177-196).

Reuse exactly:
```python
loaded = kicad_files.load(path)           # Issue | LoadedFile
if isinstance(loaded, Issue): issues.append(loaded); continue
issues.extend(loaded.source.issues)
bom = loaded.source.bom
...
backup = fsutil.backup_file(path, path.parent, number=backup_number)   # number via _next_backup_number(dest) (217-229)
if isinstance(backup, Issue): issues.append(backup); continue
issues.append(Issue(Severity.INFO, "table.backed_up", f"Backed up {filename} -> {backup.name}"))
failure = fsutil.atomic_write_text(path, content, bom=bom)
```
Insertion branch to copy for "append before closing paren, preserving every other byte" (188-196):
```python
p = table.node.end - 1
line_start = p
while line_start > 0 and text[line_start - 1] in " \t": line_start -= 1
if line_start == 0 or text[line_start - 1] == "\n":
    edits.append(Edit(line_start, line_start, block))
else:
    edits.append(Edit(p, p, eol + block))
return apply_edits(text, edits)
```
Entry text: `_entry_text(nickname, f"{_MANAGED_MARKER}{rel_path}")` (16-20, 94, 150) which already quotes via `sexpr.quote`. Missing/empty file: copy the template branch (91-98). Skip nicknames already present (any entry) and return INFO `Library tables not changed: {Lib} was already listed`. Unchanged-content short-circuit: copy 265-269 (`table.unchanged`). Success code style: `Severity.SUCCESS, "table.written"`. Existing table classification: `kicad_files.lib_table(loaded.root)`, `table.entries` with `.name`, `.uri`, `.node` (110-126). Existing managed-rel_path reader: `table_info(path)` (362-376) returns `TableInfo(entry_count, managed)` or `Issue`.

Wrong-way note: do NOT call `write_tables` with a derived selection; it regenerates all managed entries, drops flags (168-175), and removes stale entries (157-165).

---

### `settings.py` (mod): `load_import_dir` / `save_import_dir`

**Analog:** `load_kicad_fp_dir` / `save_kicad_fp_dir` (27-41)
```python
def load_kicad_fp_dir() -> Path | None:
    s = get_settings()
    val = s.value("kicad_fp_dir", "")
    if val:
        p = Path(val)
        if p.is_dir():
            return p
    return None

def save_kicad_fp_dir(path: Path) -> None:
    s = get_settings()
    s.setValue("kicad_fp_dir", str(path))
```
Add under a new `# ── Import folder ───...` divider (existing divider style, e.g. line 27). Key `"import/last_dir"`. Treat stored value as untrusted (`is_dir()`).

---

### `main_window.py` (mod): menu, busy state, drag/drop, post-install hook

**Analog:** itself.

**Menu action pattern** (90-95), keep as attributes so `_set_scan_running` can toggle:
```python
self._act_generate = QAction("&Generate Tables", self)
self._act_generate.setShortcut(QKeySequence("Ctrl+G"))
self._act_generate.setToolTip("...")
self._act_generate.setStatusTip("...")
self._act_generate.triggered.connect(self._on_generate)
file_menu.addAction(self._act_generate)
```
Add `self._act_import` ("&Import Part...", `Ctrl+I`) as first item before `_act_generate`, then `file_menu.addSeparator()`. Toolbar: `QPushButton` first in `toolbar = QHBoxLayout()` (154-158), `toolbar.addSpacing(16)`.

**Busy state** (274-280) — extend the tuple:
```python
for control in (self._rescan_btn, self._act_rescan, self._act_set_kicad_path, self._act_generate, self._generate_btn):
    control.setEnabled(not running)
```
Add `_act_import`, `_import_btn`, `_select_all_btn`, `_deselect_all_btn`; drop acceptance checks `self._worker is not None`.

**Scan entry/guard** (`_start_scan` 282-313): refuses when `self._worker is not None` with a log line; `_finish_scan` 319-325 clears worker. Post-install: queue `self._pending_post_install`, call `_start_scan()`, and if refused run from `_finish_scan`. Optional `show_progress` param (RESEARCH Open Q1) keeps `_start_scan` the only entry.

**Selection hook point** (`_on_scan_finished` 341-351): insert after `_reapply_selection` / `_trim_collided_selection`, before `self._tree.populate(result)`:
```python
if startup: self._apply_existing_selection(result) else: self._reapply_selection(previous, result)
self._log_issues(self._trim_collided_selection(result))
...
self._tree.populate(result)     # insert pending-selection set (lib.selected = True by rel_path) BEFORE; call self._tree.reveal(...) AFTER
```
Do NOT call `_trim_collided_selection` twice or alter `_reapply_selection`'s keep-set logic (HARD-07).

**Add-only table write call**, mirror `_on_generate` (512-548):
```python
dest = Path(self._dest_combo.currentText())
if not dest.exists():
    self._log.log(f"Destination folder does not exist: {dest}", "error"); return
self._log_issues(add_library_entries(dest, ...))
self._log_issues(sync_kicad_path_vars(REPO_ROOT))   # same as Generate, line 540
```
Issue routing: `_log_issues(issues)` -> `self._log.log_issue(issue)` (508-510). Warnings message wording must stay: severity decided by `Issue.severity`.

**Drag and drop:** no analog (see No Analog table); follow RESEARCH Pattern 4 and put the log strings from UI-SPEC verbatim.

**Import dialog open:** `ImportDialog(...parent=self)` modelled on `_on_restore_backup` (555-560); `closeEvent` (620-625) already waits on the scan worker; keep.

---

### `widgets/help_dialog.py` (mod)
**Analog:** itself; HTML string sections, amber span at line 163 (`"<span style='color:#CC7700;font-weight:bold'>orange</span>.</p>"` -> `theme.AMBER`). Add Import Part, `Ctrl+I`, `Ctrl+Shift+R`, Collision, add-only table behaviour. Run existing help tests after editing.

---

### `widgets/conflict_row.py`, `widgets/content_view.py` (components)
**Closest analogs:** `backup_dialog.py` (signal-to-slot wiring, `QDialog` with Close via `QDialogButtonBox`), `log_panel.py` (monospace: `self._text.setFont(QFont("Consolas", 9))` line 30, `setReadOnly(True)` 29). Content view: `QPlainTextEdit` read-only, `QFont("Consolas", 9)`, cap diff at 5000 lines/512 KiB. Conflict choices: `Resolution(action, rename_to)` from `importer/plan.py:31`; keys from `Conflict.key`.

---

## Shared Patterns

### Issue-list return + log routing
**Source:** `kicad_lib_manager/models.py` (`Issue`, `Severity` values equal LogPanel keys), `main_window.py` 508-510, `log_panel.py` 41-43.
**Apply to:** every new service (`add_library_entries`, `preview.py`, worker results) and every dialog-to-log path.
```python
def log_issue(self, issue: Issue):
    # Severity.value is the COLORS key; the enum itself is not
    self.log(issue.text, issue.severity.value)
```
Services return `list[Issue]`; never raise for expected failures; broad `except Exception` only inside thread `run()`.

### Guard flags with try/finally
**Source:** `library_table.py` 247-262 (`previous = self._updating` ... `finally: self._updating = previous`), `main_window.py` 203-212 / `blockSignals` pairs.
**Apply to:** `populate()`, `reveal()`, dialog programmatic `setText`/`setCurrentIndex`, preview tree re-render.

### Atomic write + backup
**Source:** `fsutil.backup_file(path, backup_dir, number=)` (fsutil 173), `fsutil.atomic_write_text(path, text, bom=)` (153), both return `Issue | Path | None`.
**Apply to:** `add_library_entries` only; the dialog never writes (apply_plan does).

### Settings through `settings.py` only
**Source:** `settings.py` `get_settings()` (18-24). Widgets never touch `QSettings`.

### Test harness for Qt
**Source:** `tests/test_main_window.py` 23-80:
```python
@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path):
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "qsettings"))
    file_name = Path(settings.get_settings().fileName()).resolve()
    assert tmp_path.resolve() in file_name.parents
```
and `make_window` which monkeypatches `main_window.REPO_ROOT`, `scan_all`, `load_kicad_fp_dir`, `sync_kicad_path_vars`, then `qtbot.addWidget(w)` and `qtbot.waitUntil(lambda: w._worker is None, timeout=5000)`. Copy for `test_import_dialog.py` / `test_main_window_import.py` / `test_settings_import.py`; `tests/conftest.py` forces `QT_QPA_PLATFORM=offscreen` (line 10). Fixtures: `ul_package` (conftest 93-103, yields `(package, candidate)`), `custom_copy` (79-89, tmp copy of real `Custom/`), plus `tests/installfixtures.py`, `tests/zipfixtures.py`, `tests/fakecli.py`. Pass `backup_root=tmp_path` to `apply_plan` in tests.

### Qt conventions
Fully qualified enums; PascalCase widget names; `_on_<event>` handlers; `self._name` attributes; relative imports (`from ..models import ...`); `Path` for filesystem; type hints `X | None`.

## No Analog Found

| File / Feature | Role | Data Flow | Reason |
|---|---|---|---|
| Drag and drop on `MainWindow` (`dragEnterEvent`/`dropEvent`) | controller | event-driven | No drop handling exists anywhere in the repo; use RESEARCH Pattern 4 and UI-SPEC copy. Confirm `QDropEvent` constructor in the first test (assumption A2). |
| Debounce `QTimer` + generation counter + serialised rebuild | component | event-driven | No timer-based or superseding worker exists; follow RESEARCH Pattern 2. |
| `QStackedWidget` multi-page dialog, `QSplitter`, `QScrollArea`, `QSyntaxHighlighter` diff colouring | component | n/a | Not used elsewhere; follow UI-SPEC component table. |
| Downloads folder lookup (`QStandardPaths.DownloadLocation`) | utility | file-I/O | No precedent; see RESEARCH "Downloads folder and newest zip" code example (`newest_zip` can be Qt-free in `preview.py`). |
| Rich-text blocking-reason strip with `linkActivated` | component | event-driven | No precedent; escape vendor strings with `html.escape` (as `log_panel.py` 38 does). |

## Metadata

**Analog search scope:** `kicad_lib_manager/` (main_window, settings, table_generator, fsutil, kicad_process, models, widgets/*, importer/plan, planner, applier, layout, package), `tests/` (conftest, test_main_window, test_importer_layering, test_library_table_widget).
**Files scanned:** ~25. All named analog paths confirmed in `git ls-files`.
**Pattern extraction date:** 2026-10-20
