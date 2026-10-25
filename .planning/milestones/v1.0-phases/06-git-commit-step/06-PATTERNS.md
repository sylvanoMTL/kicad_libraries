# Phase 6: Git Commit Step - Pattern Map

**Mapped:** 2026-10-22
**Files analyzed:** 12 (6 new source/test-support, 6 modified)
**Analogs found:** 11 / 12 (all analog paths verified git-tracked)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `kicad_lib_manager/gitops.py` (NEW) | service (subprocess) | request-response, side-effecting | `kicad_lib_manager/importer/kicad_cli.py` (`run_cli`), `kicad_lib_manager/kicad_process.py` | role-match |
| `kicad_lib_manager/importer/commit_plan.py` (NEW) | service (pure transform) | transform | `kicad_lib_manager/importer/content.py`, `importer/plan.py` | role-match |
| `kicad_lib_manager/widgets/commit_panel.py` (NEW) | component (state machine) | event-driven | `kicad_lib_manager/widgets/import_result.py` | exact |
| `kicad_lib_manager/widgets/import_result.py` (EDIT) | component | event-driven | itself (lines 189-194) | exact |
| `kicad_lib_manager/widgets/import_dialog.py` (EDIT) | component/orchestrator | event-driven (workers) | itself (`_spawn`, install flow, `done`) | exact |
| `tests/gitfixtures.py` (NEW) | test support | file-I/O | `tests/installfixtures.py` | role-match |
| `tests/test_gitops.py` (NEW) | test | request-response | `tests/test_kicad_cli.py`, `tests/test_install_apply.py` | role-match |
| `tests/test_commit_plan.py` (NEW) | test | transform | `tests/test_install_plan.py` | role-match |
| `tests/test_commit_panel.py` (NEW) | test (pytest-qt) | event-driven | `tests/test_import_dialog.py` | role-match |
| `tests/test_layering.py` (EDIT) | test | n/a | itself | exact |
| `tests/test_importer_layering.py` (EDIT) | test | n/a | itself | exact |
| `tests/test_import_dialog.py` (EDIT, ~L2743) | test | n/a | itself | exact |

## Pattern Assignments

### `kicad_lib_manager/gitops.py` (service, subprocess request-response)

**Analog:** `kicad_lib_manager/importer/kicad_cli.py` lines 62-84 (injectable `runner`, timeout, OSError to `Issue`) and `kicad_lib_manager/kicad_process.py` lines 25-32 (`CREATE_NO_WINDOW`).

**Subprocess core pattern** (kicad_cli.py 62-84):
```python
def run_cli(exe, args, *, runner: Callable | None = None, timeout: float = DEFAULT_TIMEOUT) -> CliRun | Issue:
    run = runner or subprocess.run
    try:
        result = run(
            [str(exe), *args],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        return Issue(Severity.ERROR, "install.cli_failed", f"kicad-cli timed out after {timeout:g} s")
    except OSError as e:
        return Issue(Severity.ERROR, "install.cli_failed", f"Could not run kicad-cli: {e.strerror or e}")
    return CliRun(result.returncode, result.stdout or "", result.stderr or "")
```
Adapt: git needs bytes (`input=` NUL pathspecs on stdin, so no `text=True`; decode with `errors="replace"`). Keep the injectable `runner` so tests record argv and assert no `push`. Use the RESEARCH Pattern 1 `run_git` (allow-list, `--literal-pathspecs`, scrubbed `GIT_*` env) as the body; raise `ValueError` (not `assert`) for a disallowed subcommand.

**Imports/layering:** Qt-free, may import only `models` (register in `tests/test_layering.py` ALLOWED as `"gitops": {"models"}`). Use `Issue`/`Severity` from `..models` (`from .models import Issue, Severity`); severity decided by producer, never by substrings.

**Error handling:** Return `Issue` lists/dataclasses, never raise for expected failures; use exit codes, never stderr emptiness. Docstrings one-line triple-double-quoted; private helpers `_name`.

---

### `kicad_lib_manager/importer/commit_plan.py` (service, pure transform)

**Analog:** `kicad_lib_manager/importer/content.py` (pure builders `diff_text`, `ContentText`) and `importer/plan.py` (`InstallResult`, `FileOp` frozen dataclasses). Read these two for dataclass style; map `result.touched` to `FileOp` via
```python
op = next((c for c in plan.ops if c.path == path), None)   # import_dialog.py:2125
```
Expected hash: `hashlib.sha256(op.data).hexdigest() if op.data is not None else op.source.sha256` (RESEARCH Pattern 3). Register in `tests/test_importer_layering.py` ALLOWED, e.g. `"importer.commit_plan": {"models", "importer.plan"}`. Do not import widgets; take the finished vendor label string as a parameter (`vendor_label` lives in `widgets/import_dialog.py:84`).

---

### `kicad_lib_manager/widgets/commit_panel.py` (component, event-driven)

**Analog:** `kicad_lib_manager/widgets/import_result.py`

**Imports pattern** (lines 6-17):
```python
from pathlib import Path
from PySide6.QtCore import QSize, Qt, QUrl, Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)
from ..importer.plan import InstallPlan, InstallResult
from ..models import Severity
from . import theme
```

**Plain-text label helper** (98-102), reuse via import (`from .import_result import _plain_label, _heading, ElidedLabel, _FilesList` or duplicate minimally):
```python
def _plain_label(*, wrap: bool = True) -> QLabel:
    label = QLabel()
    label.setTextFormat(Qt.TextFormat.PlainText)
    label.setWordWrap(wrap)
    return label
```

**Amber highlight / severity colour pattern** (133-135, 287-288):
```python
self._kicad_notice.setStyleSheet(f"background-color: {theme.AMBER_TINT}; padding: {theme.SP_SM}px;")
color = {Severity.SUCCESS: theme.SUCCESS, Severity.ERROR: theme.ERROR, Severity.WARNING: theme.AMBER}.get(severity)
label.setStyleSheet(f"color: {color};" if color else "")
```

**File list with Enter/double-click activation** (`_FilesList` 71-85, wiring 163-169): items carry `Path` in `Qt.ItemDataRole.UserRole`; `itemActivated` emits; Enter handled in `keyPressEvent` so it never reaches the default button. Reuse for the read-only commit file list (D-09 double-click diff, D-11a no checkboxes).

**Rules:** widget owns layout only; no git calls (emit signals / take callbacks); `setAutoDefault(False)` on Commit and Switch buttons (dialog only does this once at construction); all text `Qt.TextFormat.PlainText`; `self._name` attributes; `_on_<event>` handlers; `parent=None` ctor then `super().__init__(parent)`; `blockSignals` paired.

---

### `kicad_lib_manager/widgets/import_result.py` (EDIT)

**Analog / current code** lines 189-194:
```python
# Phase 6 puts its commit step here: empty, hidden and zero height until then
self.commit_slot = QWidget()
self.commit_slot.setObjectName("commitSlot")
self.commit_slot.setFixedHeight(0)
self.commit_slot.hide()
lay.addWidget(self.commit_slot)
```
`setFixedHeight(0)` pins min and max. To expand: `setMinimumHeight(0)`, `setMaximumHeight(16777215)`, `show()`, or replace with a real container holding the `CommitPanel`. Also update class docstring (lines 105-111) and `show_result` (208-220) hook (commit panel starts from the dialog, not here). Must hide/collapse again for a no-op or failed install (D-08).

---

### `kicad_lib_manager/widgets/import_dialog.py` (EDIT)

**Analog:** the install flow in the same file.

**Worker class** (170-192): `TaskWorker(fn, parent, tag)`, `fn(progress_emit)`, signals `progress(str,int,int)`, `result(object)`, `failed(str)`.

**Spawn** (1008-1013): `worker = self._spawn(fn)`; stays referenced in `self._workers`.

**Worker wiring pattern to copy for probe/switch/commit** (2037-2047, 2105-2111):
```python
worker = self._spawn(lambda progress: core.apply_plan(self._plan, backup_root=backup_root, progress=progress))
self._install_worker = worker
worker.progress.connect(self._on_install_progress)
worker.result.connect(lambda result, w=worker, p=plan: self._on_install_done(w, p, result))
worker.failed.connect(lambda text, w=worker: self._on_install_failed(w, text))
worker.start()
```
Late-result guard: `if self._closing ...: return` (2114). WR-04 fix: change `self._plan` inside the lambda to the captured `plan` (`lambda progress, p=plan: core.apply_plan(p, ...)`), and add an install/commit guard at top of `open_path` (~line 972).

**Hook point:** `_on_install_done` (2065-2079) and `_show_result` (2091-2099): after `view.show_result(...)`, start the probe worker only when `result.ok and not plan.is_noop` (D-08).

**Log routing:** `self.issues_logged.emit(list_of_Issue)` with `Issue(Severity.X, "code", text)` (2085-2086). Errors never use QMessageBox.

**Close guards** (2187-2205): extend `is_installing()`-style checks with `is_committing()` in all three:
```python
def done(self, r: int):
    if self.is_installing():
        return
    self._shutdown(); super().done(r)
def keyPressEvent(self, event):
    if self.is_installing() and event.key() == Qt.Key.Key_Escape: event.accept(); return
def closeEvent(self, event):
    if self.is_installing(): event.ignore(); return
```
D-02: emit one WARNING "Not committed — commit manually" from `done()` when the panel was Ready/OfferSwitch and nothing committed.

**D-09 diff via content view** (2120-2139): copy `_on_written_file_activated` shape (`self._run_content(build)` returning `ContentText`, `replace(...)`) for the HEAD vs pre-install diff.

**Vendor label** (81-86): `vendor_label(result.vendor)` for the message's `Import-Vendor` trailer.

---

### `tests/gitfixtures.py`, `tests/test_gitops.py`, `tests/test_commit_plan.py`, `tests/test_commit_panel.py` (NEW)

**Analogs:** `tests/installfixtures.py` (fixture builders in `tmp_path`, see `tests/test_installfixtures.py`), `tests/test_kicad_cli.py` (injectable runner, fake subprocess; `tests/fakecli.py`), `tests/test_install_apply.py`/`test_install_e2e.py` (real filesystem side effects), `tests/test_import_dialog.py` (pytest-qt dialog tests). Recipe for git fixtures (bare remotes, submodule, linked worktree, isolated `GIT_CONFIG_GLOBAL`, `autocrlf` parametrize) is in RESEARCH "Test fixture recipe". Skip module when `shutil.which("git")` is None.

### `tests/test_layering.py` (EDIT)
Add to `ALLOWED` (lines 14-23): `"gitops": {"models"},`; add `kicad_lib_manager.gitops` to the import list in `_CODE` (lines 28-30) so the Qt-free subprocess check covers it.

### `tests/test_importer_layering.py` (EDIT)
Add `"importer.commit_plan": {...}` to `ALLOWED` dict (starts line ~28).

### `tests/test_import_dialog.py` (EDIT ~2743-2744)
Replace the assertion `slot.isHidden() and slot.height() == 0 and slot.maximumHeight() == 0` after a successful install with panel-visible assertions.

## Shared Patterns

### Issue/Severity routing
**Source:** `kicad_lib_manager/models.py` (`Severity.INFO/WARNING/ERROR/SUCCESS`, `Issue(severity, code, text)`); dialog emission at `import_dialog.py:2085-2086`.
**Apply to:** `gitops.py`, `commit_plan.py`, dialog wiring. Producer sets severity; never infer from text.

### Subprocess hygiene
**Source:** `kicad_cli.py:62-84`, `kicad_process.py:25-32`.
**Apply to:** `gitops.py` only (single `run_git` choke point). `creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)`, timeout, `errors="replace"`, catch `TimeoutExpired` and `OSError`.

### Plain-text, themed UI
**Source:** `import_result.py:98-102`, `theme.AMBER/AMBER_TINT/SUCCESS/ERROR/MUTED`, `theme.SP_*`.
**Apply to:** `commit_panel.py`.

### Worker + closing guard
**Source:** `import_dialog.py:170-192, 1008-1013, 2037-2047, 2114`.
**Apply to:** probe, switch, commit jobs in the dialog.

### Path display
`Path.relative_to(repo_root).as_posix()` with `ValueError` fallback (import_result.py 258-262); also the strings handed to git.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| git state-machine logic inside `gitops.py` (probe, `add -N` + `commit --only`, switch) | service | request-response | No git use anywhere in the codebase; use RESEARCH Patterns 1-5 and the spike table (S1-S17). Only the subprocess shell has analogs. |

## Metadata

**Analog search scope:** `kicad_lib_manager/`, `kicad_lib_manager/importer/`, `kicad_lib_manager/widgets/`, `tests/`
**Files scanned:** about 12 read or grepped
**Pattern extraction date:** 2026-10-22
