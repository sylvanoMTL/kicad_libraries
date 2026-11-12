# Phase 11: Commit Gate and Commit Panel Fixes - Pattern Map

**Mapped:** 2026-10-29
**Files analyzed:** 14 (1 new source, 1 new test, 12 modified)
**Analogs found:** 14 / 14
**Tracked-source check:** every path below was confirmed with `git ls-files` (no `.gsd` mirror paths).

Line numbers were read this session from the current tree. Where RESEARCH.md gave a line, it was confirmed or corrected here.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `kicad_lib_manager/importer/commit_gate.py` (NEW) | service (Qt-free) | transform / batch | `kicad_lib_manager/importer/incoming.py` | exact (same check, same context) |
| `kicad_lib_manager/changes.py` (add public `symbol_changes`) | service | transform | its own `_mark_symbols` (lines 80-119) | exact (extract) |
| `kicad_lib_manager/gitops.py` (`_env`, `stdin_data`, identity) | utility | request-response | itself (`_env` 74-78, `run_git` 87-) | exact (edit) |
| `kicad_lib_manager/importer/commit_plan.py` (`rebaseline`, `note`/`installed`, one message builder) | model/service | transform | itself (`CommitFile` ~133, `changed_since_install` 170, `parent_message` 239) | exact (edit) |
| `kicad_lib_manager/importer/commit_step.py` (probe fields, `_precheck` gate, HEAD-moved, identical, manual cmd) | service | request-response | itself (`probe_commit` 223, `_precheck` 311, `run_commit` 432) | exact (edit) |
| `kicad_lib_manager/widgets/commit_panel.py` (gated state, controls, tint frame, sizes) | component | event-driven | itself (`_apply_strip` 430, `_set_state` 454) + `main_window.py` Generate button QSS | exact (edit) |
| `kicad_lib_manager/widgets/import_dialog.py` (probe off the lock, re-probe, open check dialog, Install QSS) | component/controller | event-driven | itself (`_start_probe` 2835, `_on_probe_done` 2849) + `MainWindow._open_atomic_check` | exact (edit) |
| `kicad_lib_manager/main_window.py` (pass `backup_root`, connect re-emitted `applied`) | controller | event-driven | itself (`_open_atomic_check` 975, `_on_atomic_fixes_applied` 1004) | exact (edit) |
| `tests/test_commit_gate.py` (NEW) | test | batch | `tests/test_incoming_check.py` + `tests/test_scan_changes.py` | role-match |
| `tests/test_commit_step.py`, `test_commit_plan.py`, `test_commit_panel.py`, `test_gitops.py`, `test_import_dialog.py` | test | request-response | themselves | exact (extend) |
| `tests/test_importer_layering.py` | test | static check | itself | exact (register `commit_gate`, widen `commit_step` ALLOWED) |

## Pattern Assignments

### `kicad_lib_manager/importer/commit_gate.py` (NEW; service, transform)

**Analog:** `kicad_lib_manager/importer/incoming.py` (Qt-free leaf, builds the context and runs the unchanged `check_symbol`).

**Imports pattern** (incoming.py lines 8-14):
```python
import os
from collections.abc import Collection, Mapping, Sequence
from pathlib import Path

from .. import kicad_files
from ..atomic_check import AtomicContext, check_symbol, repo_context
from ..models import FootprintLibrary, Issue, Severity
```
Add `from .. import gitops, changes` and `from .incoming import incoming_context`. Do not import Qt. Register the module in `tests/test_importer_layering.py`.

**Context build** (incoming.py 19-44): call `incoming_context(repo_root, layout.footprints_dir, kicad_fp_dir)`; do not use `find_footprint_libs(repo_root)` (rglob over Würth). For the H-view use `planned_footprints={link: (rel, head_bytes)}`, an existing keyword.

**Core pattern** (incoming.py 55-63): per symbol call `check_symbol(root, name, rel_path=rel_path, fixable=..., ctx=ctx)` and read `entry.violations` (each has `.rule`, `.text`) and `entry.findings` (never block, D-05). In the gate pass `fixable=True` so the entries carry `FixSpec`s for the check dialog.
```python
entry = check_symbol(root, name, rel_path=rel_path, fixable=False, ctx=ctx)
for violation in entry.violations:
    issues.append(Issue(Severity.ERROR, f"install.atomic.{violation.rule}", prefix + violation.text))
```
Log line shape for refusals is `f"{lib} / {part}: {text}"` (atomic_check.py ~673, `prefix = f"{lib.nickname} / {entry.name}: "`).

**Which symbols are "new or changed" (D-01):** extract the loop of `changes._mark_symbols`:

`changes.py` lines 86-110:
```python
root, reason = _read_current(path)
if root is None:
    return [_skipped_for(path, reason)]
in_head, head_root = _read_head(ctx, custom_dir, rel)
if not in_head:
    before: dict[str, tuple] | None = {}  # a new file: every symbol is new
elif head_root is None:
    before = None  # HEAD's version cannot be compared: every symbol counts as changed
else:
    before = _head_symbols(head_root)
...
for ref in kicad_files.find_symbols(root):
    ...
    if before is None:
        status = STATUS_CHANGED
    elif ref.name not in before:
        status = STATUS_NEW
    elif before[ref.name] != sexpr.token_stream(ref.node):
        status = STATUS_CHANGED
    else:
        continue
```
New public `changes.symbol_changes(ctx, custom_dir, rel) -> tuple[dict[str, str] | None, str | None]` returns `{name: STATUS_NEW | STATUS_CHANGED}` or a skip reason; `_mark_symbols` then calls it (no third copy of D-21). Treat a derived symbol as changed when any `kicad_files.extends_name` ancestor changed (RESEARCH Pitfall 4).

**Result types:** frozen dataclasses `AtomicFailure(library, rel_path, part, rule, text)` and `GateResult(blocking, old, problems, entries)` as in RESEARCH Pattern 1. Frozen-dataclass style matches `CommitProbe` (`commit_step.py` 21-41).

**Scope:** only `Atomic_` libraries (`atomic_check.is_atomic`, Phase 9 D-23). Unreadable committed library goes into `problems` and refuses (safe default).

---

### `kicad_lib_manager/changes.py` (service, transform)

**Analog:** `_mark_symbols`, lines 80-119 (excerpt above). Keep `_mark_symbols` behaviour byte-identical (tests in `tests/test_scan_changes.py`); only move the compare into `symbol_changes`.

---

### `kicad_lib_manager/gitops.py` (utility, request-response)

**Analog:** itself.

**Current `_env`** (lines 74-78):
```python
def _env() -> dict[str, str]:
    """The app's environment without any GIT_* variable (a stray GIT_DIR or GIT_INDEX_FILE would redirect every call)."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "GIT_EDITOR": "true", "LC_ALL": "C"})
    return env
```
Change: before `update`, re-add only `GIT_AUTHOR_NAME/EMAIL/DATE` and `GIT_COMMITTER_NAME/EMAIL/DATE` (case-insensitive like the strip). `GIT_DIR`, `GIT_INDEX_FILE`, `GIT_WORK_TREE`, `GIT_CONFIG_*` stay stripped.

**`run_git` signature** (line 87-94): rename `input: bytes | None = None` to `stdin_data`; line 106 `options = {"input": input} ...` becomes `{"input": stdin_data}` (the kwarg to `subprocess.run` stays `input`). Callers per RESEARCH: ~lines 238, 334, 339, 343, 353 (grep `input=` before editing).

**`identity_known`:** must require both `git var GIT_AUTHOR_IDENT` and `git var GIT_COMMITTER_IDENT` (RESEARCH E3); update the message at `commit_step.py` ~147.

**Test to update:** `tests/test_gitops.py:101-107` pins the GIT_* key set; keep that for other variables and add a six-variable case.

---

### `kicad_lib_manager/importer/commit_plan.py` (model/service, transform)

**Analog:** itself.

**Frozen value + positional constructor** (line 133): `files.append(CommitFile(rel, display, path, op.kind, expected, op.base_sha256))`. New fields `note: str = ""` and `installed: bytes | None = None` go last with defaults so the positional 6-arg calls in `commit_plan.py:133`, `tests/gitfixtures.py:235` and `tests/test_commit_panel.py:34` keep working. Set `installed=op.data` there.

**Re-baseline model** (copy the shape of `changed_since_install`, lines 170-172):
```python
def changed_since_install(cplan: CommitPlan) -> tuple[str, ...]:
    return tuple(f.display for f in cplan.files if _sha256_of(f.path) != f.expected_sha256)
```
New `rebaseline(cplan) -> CommitPlan` uses `dataclasses.replace(cplan, files=...)` and `replace(f, expected_sha256=<current via _sha256_of>, note="changed")`. Never mutate (frozen). Diff for the marker: `content.diff_text(installed, current, ...)` as `pre_import_diff` does (`commit_step.py:398`).

**One message builder (D-15):** current `parent_message` (239-255) and `parent_preview` (258-261):
```python
lines.append(f"{custom_rel} {_short(old)}..{_short(new)}" if old else f"{custom_rel} {_short(new)}")
if listed:
    lines.extend(f"- {short} {sanitize_line(text)}" for short, text in commits)
else:
    lines.append(f"(the {custom_rel} commits since {_short(old)} could not be listed)")
```
Fix: when `old is None` never emit the "could not be listed" line (`if old is None or listed`). `_earlier` (`commit_step.py:192`) returns `((), True)` for `gitlink_old is None`. `commit_parent_ref` (`commit_step.py:373`) and `parent_preview` must call the one function. Use `subject_of` for the subject on both sides (Pitfall 7).

---

### `kicad_lib_manager/importer/commit_step.py` (service, request-response)

**Analog:** itself. Error-handling style: functions return `Issue` or a frozen dataclass carrying `issues: tuple[Issue, ...]`, never raise.

**Probe fields** (`CommitProbe`, lines 21-41): add `gate: GateResult | None = None`, `identical: frozenset[str] = frozenset()`, `changed: tuple[str, ...] = ()`, and a state for the gated refusal (`"gated"`, see panel). Return construction pattern (lines 246-252):
```python
return CommitProbe(
    state="ready", branch=branch, head=head,
    not_main=branch != "main",
    **_preexisting(ctx, cplan, head),
)
```
Add `cancelled: Callable[[], bool] | None = None` to `probe_commit(cplan, *, git=None)` (line 223) and check it between git calls (IN-02). Existing fakes take `**kwargs`, so new keywords are safe.

**`_precheck` gate slot** (lines 311-357): add the gate call after `changed_since_install` and before `_custom_unavailable`; style to copy:
```python
stale = changed_since_install(cplan)
if stale:
    plural = "s" if len(stale) != 1 else ""
    return Issue(Severity.ERROR, "commit.stale_file", f"Not committed: ... Check the file{plural} and commit by hand.")
```
Change this text to point at "Check again" (D-09). Gate refusal: `Issue(Severity.ERROR, "commit.atomic", ...)` with plain-language lines.

**HEAD-moved after failure (D-12)**, current block lines 467-471:
```python
run = gitops.commit_paths(ctx, custom, message, rels)
if _run_failed(run):
    if new:
        gitops.unstage(ctx, custom, new)
    return _custom_failure(run, committing=True)
```
Read `before = gitops.head_commit(ctx, custom)` just above; on failure re-read. Moved: build outcome from the success fields (`short`, `branch`, as lines 473-485), WARNING issue, skip `unstage` and the parent step, set `manual_command` when `bump_parent`. Not moved: keep the path above.

**Identical-to-HEAD compare (D-13)**, current lines 487-497:
```python
planned = set(rels)
committed_files = gitops.commit_files(ctx, custom)
if committed_files is not None and set(committed_files) != planned:
    extra, missing = sorted(set(committed_files) - planned), sorted(planned - set(committed_files))
    ...
    issues.append(Issue(Severity.ERROR, "commit.unexpected_files", ...))
    return CommitOutcome(issues=tuple(issues), **fields)
```
Split `missing` into `already` (in `identical`, INFO) and `real_missing`; ERROR only when `extra or real_missing`. `identical` comes from `sha256(gitops.head_blob(...)) == _sha256_of(path)` (`head_blob` uses `cat-file --filters`, autocrlf-safe). Add `CommitOutcome.parent_only: bool = False` (dataclass at lines 44-57) so the dialog does not log "Not committed" after a parent-only bump.

**Manual command (D-16)**, current lines 506-508:
```python
subject = text.splitlines()[0].replace('"', '\\"')
manual = f'git -C "{parent.as_posix()}" commit -m "{subject}" -- {cplan.custom_rel}'
```
Replace with a pure `manual_command(parent, custom_rel, subject, *, windows=None)` (RESEARCH Pattern 9: `_ps_quote` doubling `'`, `shlex.quote` on POSIX). Per amended D-16: when the subject holds `"` or ends in `\`, write the message to a temp file outside the repo and emit `git commit -F '<file>'`. Keep the literal `Finish it by hand:` in the issue text (line 513) because `commit_panel.show_outcome` filters on it (~line 341); update both together; label becomes "In PowerShell:" on Windows.

---

### `kicad_lib_manager/widgets/commit_panel.py` (component, event-driven)

**Analog:** itself.

**State tuple and strip prefix** (lines 25-32): add `"gated"` to `_STATES`; reuse `_STRIP_PREFIX["refused"] = "Commit refused: "` text for the gated strip. `_EARLIER_SHOWN = 10` and the cap pattern (lines 501-503) is the model for "…and k more":
```python
lines.extend(f"- {short} {text}" for short, text in earlier[:_EARLIER_SHOWN])
if len(earlier) > _EARLIER_SHOWN:
    lines.append(f"…and {len(earlier) - _EARLIER_SHOWN} more")
```

**Strip look** (`_apply_strip`, lines 430-452) — the tint pattern to generalise to the outcome area:
```python
self._strip.setStyleSheet(
    f"background-color: {theme.AMBER_TINT}; color: {theme.AMBER}; padding: {theme.SP_SM}px;"
)
```
For D-18 wrap `_outcome_layout` in a `QFrame` named `outcomeStrip` with `QFrame#outcomeStrip {{ background-color: {tint}; padding: {theme.SP_SM}px; }}`; tint chosen by strongest severity (ERROR -> `ERROR_TINT`, WARNING -> `AMBER_TINT`, else `SUCCESS_TINT`). Keep per-label colour styles (tests read `panel._outcome_labels[0].styleSheet()`, `tests/test_commit_panel.py:377,464`).

**`_set_state`** (lines 454-464): `self._message.setReadOnly(not ready)` becomes editable in `gated` too; line 462 label map `{"committing": "Committing...", "done": "Committed", "failed": "Committed"}` -> `"failed": "Committed in Custom only"` (D-17).

**Signals** (lines 104-106) style for new ones: `check_again_requested = Signal()`, `open_check_requested = Signal(str, str)` (rel_path, name).

**Primary button (D-19):** after `self.commit_button = QPushButton("Commit")` (~line 189) add `self.commit_button.setStyleSheet(theme.PRIMARY_BUTTON_QSS)`. Pattern source: `main_window.py:346` `self._generate_btn.setStyleSheet(PRIMARY_BUTTON_QSS)`. New "Check again" / "Open Check Atomic Parts…" stay unstyled (secondary).

**Sizes (D-20):** line 205 `self._progress.setFixedSize(240, 16)` -> `theme.SP_XL * 8` x `theme.SP_MD`; line ~259 `fontMetrics().height() + 8` -> `+ theme.SP_SM`.

**`apply_probe` / `show_plan`** (lines 246-290): `show_plan` resets the message and outcome, `apply_probe` calls `_clear_outcome()` first and re-ticks the parent box. Add `begin_reprobe()` that keeps the message and file list, `_pending_refusal` re-rendered unless the new probe refuses on its own (D-11), and `_parent_wanted` tracked via a programmatic-change guard (IN-01).

---

### `kicad_lib_manager/widgets/import_dialog.py` (controller, event-driven)

**Analog:** itself.

**Probe wiring today** (lines 2835-2866):
```python
self._commit_probe = None
panel.show_plan(cplan)
core = self._core
worker = self._spawn(lambda progress, cp=cplan: core.probe_commit(cp))
self._set_git_worker(worker)
worker.result.connect(lambda probe, w=worker: self._on_probe_done(w, probe))
worker.failed.connect(lambda text, w=worker: self._on_probe_failed(w, text))
worker.start()
```
Changes: drop `_set_git_worker(worker)` for the probe (IN-02); create a `threading.Event` per probe, pass `cancelled=event.is_set` (`core.probe_commit(cp, kicad_fp_dir=..., cancelled=...)`); set all probe events at the start of `_shutdown` (line 3028) before its `worker.wait()` loop; in `_on_probe_done` add `if worker is not self._probe_worker: return`. Use `begin_reprobe` instead of `show_plan` for re-probes and the post-switch probe. `_on_probe_failed` (2859) already shows the failure style for `unavailable`.

**Commit-done re-probe (REV-10):** `_on_commit_done` (line 2932): after `show_outcome` for a non-committed outcome call the re-probe. `_on_commit_requested` (2910) already passes `probe.branch`.

**Opening the check dialog:** copy `MainWindow._open_atomic_check` (`main_window.py:987-998`) with `parent=self`, `focus=(rel_path, name)`, `backup_root` passed in as a new `ImportDialog` keyword:
```python
dialog = AtomicCheckDialog(
    self._scan_result, REPO_ROOT, focus=focus, backup_root=ATOMIC_BACKUP_ROOT, parent=self,
)
dialog.applied.connect(self._on_atomic_fixes_applied)
dialog.issues_logged.connect(self._log_issues)
dialog.finished.connect(self._on_atomic_dialog_finished)
dialog.open()
```
In the import dialog build a small `ScanResult(symbol_libs=[SymbolLibrary(nickname, rel_path, "Custom", atomic=True, symbols=[entry...])])` from `GateResult.entries` instead of `self._scan_result`. Re-emit `applied` through a new `Signal(list)`; `MainWindow` connects it to `_on_atomic_fixes_applied` (`main_window.py:1004-1007`: `self._log_issues(issues); self._start_scan()`).

**Install Part style (D-19):** after line 735 `self._install_btn = QPushButton("Install Part")` add `self._install_btn.setStyleSheet(PRIMARY_BUTTON_QSS)` (import from `.theme`); pinned in tests like `tests/test_main_window_import.py:672` for Generate.

**Tests waiting on `is_committing()` for the probe** (e.g. `tests/test_import_dialog.py:324`) must move to `finish_workers(qtbot, dialog)` or a new `is_probing()`.

---

### `kicad_lib_manager/main_window.py` (controller, event-driven)

**Analog:** itself, lines 975-1011 (excerpt above). Changes are small: where `ImportDialog` is constructed pass `backup_root=ATOMIC_BACKUP_ROOT` and connect the dialog's re-emitted fixes signal to `_on_atomic_fixes_applied`. `closeEvent` already calls `dialog.reject()`; no change expected beyond the IN-02 dialog fix.

---

### `tests/test_commit_gate.py` (NEW; test, batch)

**Analogs:** `tests/test_incoming_check.py` (check on planned content), `tests/test_scan_changes.py` (HEAD compare), `tests/gitfixtures.py` + `tests/customfixtures.py` (throwaway git repos, `Atomic_` fixtures).

Helpers available in `tests/gitfixtures.py`: `make_superproject`, `import_files`, `commit_file`, `detach`, `write_hook`, `make_worktree`, `populate_custom`. Cases from CONTEXT: failing new part, failing pre-import edit, failing part already at HEAD (amber, no block), footprint overwrite breaking a linked symbol. The live `Custom/` is never touched (write-protect guard).

### Other test files (extend)

**Timeout with HEAD moved** — copy `tests/test_commit_step.py:800-817` and run the real commit first:
```python
def runner(argv, **kwargs):
    calls.append(list(argv))
    if argv[6] == "commit":
        raise subprocess.TimeoutExpired(argv, kwargs.get("timeout", 0))
    return subprocess.run(argv, **kwargs)
```
New variant: `done = subprocess.run(argv, **kwargs)` then raise; assert HEAD moved, no `reset` call, no parent commit. Real variant uses `write_hook(repos, repos.custom, "post-commit", "#!/bin/sh\nsleep 3\n")` with the timeout forced to 1.
Panel tests use `qtbot`; PowerShell-safety test skips when `powershell` is absent and must be added to the expected-skips table in `tests/README.md`.

## Shared Patterns

### Reuse the unchanged rule engine (D-05)
**Source:** `kicad_lib_manager/importer/incoming.py` 47-63 and `atomic_check.check_symbol`
**Apply to:** `commit_gate.py` only. No rule logic is copied or altered; findings never block.

### Qt-free service returning `Issue`s, errors to panel and log
**Source:** `commit_step.py` (`_failed`, `_probe_issue`, `Issue(Severity.ERROR, "commit.<code>", text)`)
**Apply to:** `commit_gate.py`, every new `commit_step` branch. Severity routes display; no message boxes.

### Frozen dataclasses, `dataclasses.replace`
**Source:** `CommitProbe` / `CommitOutcome` (`commit_step.py` 21-57), `CommitPlan` / `CommitFile`
**Apply to:** `GateResult`, `AtomicFailure`, `rebaseline`. Defaults go last so positional constructors keep working.

### All git through `run_git`
**Source:** `gitops.py` 87-; allow-list, `--literal-pathspecs`, no push.
**Apply to:** any new git read (HEAD-moved check, `head_blob` for identical files). No direct `subprocess` in `commit_step`/`commit_gate`.

### Worker threads
**Source:** `import_dialog.py` `_spawn` / `TaskWorker` and the lambda-with-default-arg connect pattern (2843-2847).
**Apply to:** the probe, the gate, Check again. The gate never runs on the GUI thread; do not abandon a running `QThread` (see `_reap` docstring).

### Theme constants only
**Source:** `kicad_lib_manager/widgets/theme.py` (`PRIMARY_BUTTON_QSS`, `AMBER_TINT`, `ERROR_TINT`, `SUCCESS_TINT`, `SP_*`).
**Apply to:** `commit_panel.py`, Install button. No raw pixel numbers or colour literals.

### Plain-language text
**Source:** project memory "Plain-language UI".
**Apply to:** all refusal, marker and strip text. Use rule text from `Violation.text`; no raw KiCad field names.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Cooperative cancel (`threading.Event` passed as `cancelled`) | utility | event-driven | No existing cancellable worker; `ScanWorker`/`TaskWorker` have no cancel hook. Use RESEARCH Pattern 7. |
| H-view context for "introduced by this commit" (D-04) | service | transform | `repo_context(planned_footprints=...)` exists, but no wrapper that makes a new footprint resolve as "not in library". Follow RESEARCH Pattern 2 (about 10 lines around `AtomicContext`'s two callables). |
| `_ps_quote` / `-F` temp-file manual command | utility | transform | Only the old double-quote form exists. Use RESEARCH Pattern 9 and the amended D-16. |

## Metadata

**Analog search scope:** `kicad_lib_manager/` (importer, widgets, root modules), `tests/`
**Files read for excerpts:** `commit_step.py`, `incoming.py`, `changes.py`, `commit_plan.py`, `gitops.py` (74-110), `commit_panel.py` (425-475), `import_dialog.py` (2835-2895), `main_window.py` (972-1011), `tests/test_commit_step.py` (796-818), `tests/gitfixtures.py` (symbols)
**Pattern extraction date:** 2026-10-29
