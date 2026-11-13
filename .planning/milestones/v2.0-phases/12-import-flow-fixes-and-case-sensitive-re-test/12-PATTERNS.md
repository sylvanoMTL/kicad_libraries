# Phase 12: Import Flow Fixes and Case-Sensitive Re-test - Pattern Map

**Mapped:** 2026-11-01
**Files analyzed:** 14 (9 modified source, 1 new test helper, 1 new test file, 3 modified test/doc files)
**Analogs found:** 14 / 14 (all analogs are git-tracked; `git ls-files` checked for table_generator, import_dialog, test_install_apply)

Most of this phase edits existing code, so the "analog" is usually the function being changed plus an in-repo precedent for the new shape. Line numbers are current as of this mapping.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `kicad_lib_manager/table_generator.py` (`_add_entry`, `add_library_entries`, `_same_rel`) | service | file-I/O, transform | itself (`_add_entry` 303-366) + `sexpr.Edit/apply_edits` | exact |
| `kicad_lib_manager/main_window.py` (`_dest_path`, `_finish_post_install`, `_tables_outcome`, KiCad-open dialog, check worker, `closeEvent`) | controller | request-response, event-driven | itself (795-893, 1048-1070) + `ImportDialog._start_kicad_check` | exact |
| `kicad_lib_manager/library_scanner.py` (`sync_kicad_path_vars`) | service | file-I/O | itself (181-295) | exact |
| `kicad_lib_manager/widgets/backup_dialog.py` | component | request-response | `main_window._dest_path` (new) | role-match |
| `kicad_lib_manager/widgets/import_dialog.py` (Finishing state, `_pump_builds`, `_updating`, `incoming_op`) | component | event-driven | itself (`_wait_builds` 1452, `_pump_builds` 2506, `_shutdown` 3177) + `_start_kicad_check` 3107 | exact |
| `kicad_lib_manager/importer/planner.py` (`_decide_file` overwrite branch ~742) | service | transform | skip branch at 745-746 | exact |
| `kicad_lib_manager/widgets/help_dialog.py` (CSS) | component | transform | `theme.py` list-join stylesheets (27-36) | role-match |
| `kicad_lib_manager/widgets/conflict_row.py` (`_button_qss`) | component | transform | `theme.FIELD_FRAME_QSS` f-string with tokens | role-match |
| `kicad_lib_manager/widgets/theme.py` (+`SURFACE_BASE`) | config | n/a | existing colour constants 4-15 | exact |
| `tests/casefixtures.py` (NEW) | test utility | file-I/O | `kicad_process.py:24` fsutil path pattern; `test_commit_plan` probe | role-match |
| `tests/test_case_sensitive_install.py` (NEW) | test | file-I/O | `tests/test_install_apply.py::test_rollback_restores_case_twin` (695-714) | exact |
| `tests/test_main_window.py` + `test_main_window_import.py` fixtures | test | request-response | `fake_sync` (60-70), `fake_question` (88-96) | exact |
| `tests/test_import_dialog.py` (Finishing/close tests) | test | event-driven | existing close tests (~294-297, 3605-3638) | exact |
| `tests/README.md` | doc | n/a | existing expected-skips table | exact |

## Pattern Assignments

### `kicad_lib_manager/table_generator.py` (service, file-I/O) - REV-01

**Analog:** the current `_add_entry` (303-366). Change only the match loop; keep backup, atomic write and Issue shape.

**Current match loop to replace** (339-350):
```python
        for entry in table.entries:
            if entry.name != nickname:
                continue
            if _is_managed(entry):
                return "listed"
            issues.append(Issue(
                Severity.WARNING,
                "table.external_clash",
                f"{filename}: '{nickname}' is already defined by an external entry "
                f"({entry.uri}); kept it and did not add {uri}",
            ))
            return "skipped"
```
Use the precedence in RESEARCH Pattern 1: (1) managed + `_same_rel(_tail(entry), rel_path)` -> `"listed"`; (2) managed with live target (`repo_root / tail` exists) -> `table.path_clash` WARNING, `"skipped"`; (3) any hand-added -> `table.external_clash` (plainer wording, D-05); (4) all managed stale -> repoint; (5) none -> add / `"missing"`.

**Repoint edit** (reuse the byte-preserving edit mechanism already used for insertion at 351-354):
```python
block = f"  {_entry_text(nickname, uri)}{loaded.source.eol}"
new_text = apply_edits(text, [_insert_before_close(text, table.node, loaded.source.eol, block)])
# repoint instead: node = entry.value_nodes["uri"]
# new_text = apply_edits(text, [Edit(node.start, node.end, quote(uri))])
```
**Write tail to keep unchanged** (356-366): `fsutil.backup_file(path, path.parent, number=backup_number)` -> INFO `table.backed_up`; `fsutil.atomic_write_text(path, new_text, bom=loaded.source.bom)`; return `"updated"` instead of `"added"`.

**Summary block to extend** (`add_library_entries` 395-406): add `"updated"` -> `Issue(Severity.SUCCESS, "table.entry_updated", ...)`, and `"missing"` -> `Issue(Severity.INFO, "table.not_listed", ...)`. `table.entries_added` requires all outcomes `"added"`; keep that. New keywords: `repo_root: Path`, `add_missing: bool = True`; `_same_rel(a, b, *, fold=None)` with `fold` defaulting to `os.name == "nt"` (test seam). Imports allowed by `tests/test_layering.py`: `fsutil, kicad_files, models, sexpr` only.

---

### `kicad_lib_manager/main_window.py` (controller) - REV-01/02/05

**Analog:** itself; the existing-library branch (850-871) and new-library branch (829-848).

**New-library branch call to extend with `repo_root=`** (833-848):
```python
issues = add_library_entries(dest, symbol=(library, pending.sym_rel_path) if pending.new_symbol_lib else None,
                             footprint=(...))
self._log_issues(issues)
text, severity = self._tables_outcome(issues)
self._set_import_status("tables", text, severity)
self._sync_path_vars()
return
```
D-04: the existing-library branch (852-871, currently `table_info(...)` + `rel_path not in info.managed` -> "Press Generate Tables" hint) calls `add_library_entries(..., add_missing=False)` instead; keep the hint for `table.not_listed` nicknames and the `import.not_in_tables` WARNING + `generate_hint` row.

**`_tables_outcome` code list to extend** (889-893): add `table.entry_updated`, `table.path_clash`, `table.not_listed` to the `parts` filter tuple `("table.entry_added", "table.already_listed", "table.external_clash")`.

**`_dest_path` helper (REV-02)** replaces `Path(self._dest_combo.currentText())` at lines 215, 714, 820, 1077, 1113, 1153, 1157 (and `_log_existing_tables` must accept `None`):
```python
def _dest_path(self) -> Path | None:
    text = self._dest_combo.currentText().strip()
    return Path(text) if text else None
```
Blank in `_finish_post_install`: `self._set_import_status("tables", "No destination folder set; library tables not changed", Severity.WARNING)` plus a `self._log.log(..., "warning")`, then return (existing missing-folder pattern at 821-827).

**KiCad path-var confirm: sanctioned dialog pattern** (1045-1070). The tri-state variant goes behind one monkeypatchable method (`_ask_kicad_open(changes, names)`), built as a `QMessageBox` instance with `addButton("Retry", AcceptRole)` default / `"Change anyway"` / `"Not now"`; Yes/No stays `QMessageBox.question` (tests patch `QMessageBox.question`):
```python
answer = QMessageBox.question(self, "Change KiCad path variables?", text,
    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
return answer == QMessageBox.StandardButton.Yes
```
**Off-thread KiCad check precedent:** `ImportDialog._start_kicad_check` (`import_dialog.py` 3107-3113):
```python
worker = self._spawn(lambda progress: core.kicad_running())
worker.result.connect(lambda names, lib=library: self._on_kicad_running(lib, names))
worker.failed.connect(lambda text: None)
worker.start()
```
In `MainWindow` use `TaskWorker` (`import_dialog.py` 257-279) with `kicad_running` looked up as a module attribute of `main_window` (test seam); keep finished workers referenced in a list, never `deleteLater`; add a `_path_var_busy` re-entry flag (Generate click + post-install both start the sync).

---

### `kicad_lib_manager/library_scanner.py` `sync_kicad_path_vars` (service, file-I/O) - REV-05

**Analog:** itself, 181-295. Current order is read -> parse -> changes -> refusal -> `confirm(changes)` -> build from the STALE `config`/`old_vars` -> `running()` after confirm (268). Rework into a bounded (3-pass) loop:

**Parse/shape block to reuse as a local helper for the re-read** (181-208): `fsutil.read_source`, `json.loads`, `config.bad_json` / `config.bad_shape` Issues.

**Write block to run on fresh content** (256-266, 277-292):
```python
new_config = copy.deepcopy(config)
new_config.setdefault("environment", {})["vars"] = {**old_vars, **desired}
new_text = json.dumps(new_config, indent=2, ensure_ascii=False) + "\n"
if not _only_vars_changed(config, json.loads(new_text), desired): ... config.verify_failed
new_text = fsutil.normalize_eol(new_text, src.eol)
backup = fsutil.backup_file(config_file, backup_dir) ... fsutil.atomic_write_text(config_file, new_text, bom=src.bom)
```
Changes: call `running()` BEFORE `confirm` (D-09); `confirm` may return bool or a tri-state enum (write / decline / retry; plain True/False still valid so the 25+ `tests/test_kicad_config.py` tests stay valid); retry returns an INFO `config.retry` Issue before any backup; after the confirm re-read, recompute `changes`: same -> write fresh; different -> ask again; empty -> log `config.var_ok` and write nothing. Reword `config.kicad_running` (D-12, WARNING) and update `tests/test_kicad_config.py:328-329`. Keep Issue shape `Issue(Severity, code, text)`; no Qt.

---

### `kicad_lib_manager/widgets/import_dialog.py` (component, event-driven) - REV-03/04

**REV-03 core** (analog: current `_updating` 2577-2584 and `_pump_builds` 2506-2518):
```python
def _updating(self) -> bool:
    return (self._building is not None or self._queued is not None or self._dirty
            or self._model_worker is not None)          # add: or self._oneoff is not None

def _pump_builds(self):
    if self._closing or self._building is not None or self._oneoff is not None:   # add: or self._finishing or self.is_installing()
        return
```
`_on_install_done` / `_on_install_failed` (~2774/2790) call `_pump_builds()` after clearing `_install_worker`; on success clear `_oneoff_jobs`/`_queued` instead of resuming. `_request_rebuild` (~2472) also holds while `_finishing`. `_on_oneoff_done` (2528-2538) skips `on_result` while `_finishing`.

**REV-04: the blocking code being replaced:**
- `_wait_builds` (1452-1456): `for worker in (self._building, self._oneoff): worker.wait()`; called from `_on_change` (3153).
- `_shutdown` (3177-3197): `for worker in list(self._workers): worker.wait()` then releases `OpenOutcome/ModelOutcome` packages and `_discard_package()`.
- `done` (3199-3206) / `closeEvent` (3214-3220): early-return guard `if self.is_installing() or self.is_committing(): return`; closeEvent uses `event.ignore()`.
- `_reap` (1269-1278): keep a bounded `worker.wait(2000)` (owner answer); never `deleteLater`.

**Pattern to copy for the Finishing state:** idle -> run now (existing idle tests stay synchronous); busy predicate `[w for w in self._workers if w is not exclude and w.isRunning()]`; store `self._pending` action as a bound method (not a lambda with zero-arg `super()`; write `_finish_close(r)`); run from `_reap`/`finished` handler when none running; in `closeEvent` when deferring call `event.ignore()` and return without `super().closeEvent`. Do NOT set `_closing` on entry (handlers at ~1292-1299 drop results when `_closing`). Disable `self._stack` only, strip in `outer`; `QGuiApplication.setOverrideCursor`/`restoreOverrideCursor` paired in one `_end_finishing()`; `_SLOW_NOTE_MS = 10_000` module constant for the 10 s note via single-shot `QTimer` (monkeypatch-able). Escape: extend `keyPressEvent` (3208-3212) to swallow Escape while `_finishing`.

**`incoming_op` footprint branch (~145-147):** compare `op.path.name.casefold() == f"{conflict.name}.kicad_mod".casefold()` (D-14 ripple).

`MainWindow.closeEvent` (`main_window.py` 1181) currently calls `dialog.reject()` then closes; must handle a deferred dialog close (ignore the event, re-issue `close()` from the dialog's finished signal).

---

### `kicad_lib_manager/importer/planner.py` (service, transform) - D-14

**Analog:** the skip branch directly below the overwrite branch (742-747):
```python
    if resolution.action == "overwrite":
        # The write replaces the file on disk under whatever spelling it has now (Pitfall 12)
        return _Decision(spec.default, op=spec.make_op(spec.default, existing, digest), conflict=resolved)
    if resolution.action == "skip":
        return _Decision(spec.identity_of(hit), conflict=resolved, kept=True)
```
Change overwrite to `name = spec.identity_of(hit)` for both the `_Decision` name and `make_op(name, existing, digest)`. `make_model_op` (~1218-1225) and `make_fp_op` (~1308-1315) then set `listed_path=None`; the model link (`model_dec.name`, ~1245/1267), Footprint field (~1378-1380) and `plan.model_file` (~1587) follow automatically. Keep `listed_path` handling in `applier` (`_drop_twin` ~72, `_rollback` ~80), `content.py:122`, `commit_plan.py:121`, `preview.py:149`. Existing tests encoding the old behaviour must change: `tests/test_install_plan.py` ~1574-1590, 1593-1601, 1604-1612.

---

### `kicad_lib_manager/widgets/help_dialog.py` + `conflict_row.py` + `theme.py` (UI-01)

**Analog:** `theme.py` 27-36 (stylesheet assembled from tokens, joined with newlines, f-strings with `{{ }}` only where needed):
```python
FIELD_FRAME_QSS = "\n".join([
    "QFrame#fieldFrame { border: 2px solid transparent; border-radius: 2px; }",
    f'QFrame#fieldFrame[blocked="true"] {{ border: 2px solid {AMBER}; }}',
])
```
`help_dialog.py` already imports `from .theme import ACCENT, AMBER` (line 8) but CSS (10-60) is a literal block. Rebuild as a list of rule strings from `LINK, ACCENT, SURFACE, SURFACE_HEADER, BORDER, AMBER, AMBER_TINT, SP_*, HEADING_PT, DISPLAY_PT, MONO_PT, MONO_FAMILY`. Mapping: `#0057A0`->LINK, `#0078D4`->ACCENT, `#EEF1F5`->SURFACE_HEADER, `#F5F7FA`->SURFACE, `#FFF8E1`->AMBER_TINT, `#F9A825`->AMBER, `#CCC`->BORDER; drop `color:#222/#333` (inherit palette); drop `border-radius` (unsupported). Set explicit `h2 { font-size: DISPLAY_PT pt }` and `h3 { font-size: HEADING_PT pt }` (headings flatten otherwise).

`conflict_row.py` 35 and 37 hold `#FFFFFF`; replace with new `theme.SURFACE_BASE = "#FFFFFF"` (add near theme.py line 13-15).

---

### `tests/casefixtures.py` (NEW) and `tests/test_case_sensitive_install.py` (NEW)

**Analog for the fault-injected rollback test:** `tests/test_install_apply.py` 695-714:
```python
def test_rollback_restores_case_twin(hand_layout, snapshot, monkeypatch):
    original = b"original model bytes"
    twin = hand_layout.models_dir / "foo.STEP"
    twin.write_bytes(original)
    plan = _hand_plan(hand_layout, new_library=True)
    overwrite = FileOp("model", hand_layout.models_dir / "Foo.step", data=STEP_BYTES,
                       base_sha256=_sha(original), listed_path=twin)
    plan = dataclasses.replace(plan, ops=tuple(overwrite if op.kind == "model" else op for op in plan.ops))
    before = snapshot(hand_layout.custom_dir)
    _flaky_writes(monkeypatch, fail_on=2)
    result = apply_plan(plan, backup_root=hand_layout.repo_root / "bk")
    assert not result.ok
    spellings = [n for n in os.listdir(hand_layout.models_dir) if n.casefold() == "foo.step"]
    assert spellings == ["foo.STEP"]
```
Build the layout inside `case_sensitive_dir(tmp_path / "cs")` and do NOT mock `os.listdir` (D-13). Reuse `_hand_plan`, `snapshot`, `_flaky_writes` (fault injection only); planner-built plans reuse `_target_layout/_put_model/_put_footprint/_vendor` from `tests/test_install_plan.py` or `write_synthetic_custom(root, naming="atomic")`. T1 hand-built twin rollback; T2 planner-built rollback; T3 model overwrite end state `["part.STEP"]` with model line `${CUSTOM_3DMODEL_DIR}/part.STEP`; T4 footprint overwrite `["fp.kicad_mod"]` (full matrix in RESEARCH "Recommended VER-02 test matrix").

**Fixture** (RESEARCH "Case-sensitive folder fixture"; fsutil path built like `kicad_process.py:24`): new empty dir, `fsutil.exe file setCaseSensitiveInfo <dir> enable` on win32 with `CREATE_NO_WINDOW` and a timeout, `pytest.skip(...)` with the reason on `OSError`/non-zero exit/probe failure; probe: write `CaseProbe`, check `caseprobe` not visible. Add a row to the expected skips table in `tests/README.md`. UAT command: `.\env\Scripts\python.exe -m pytest tests/test_case_sensitive_install.py -v -rs` (must PASS, no skips).

---

### Test fixture ripples

**`tests/test_main_window.py` 60-70** (and the same shape in `tests/test_main_window_import.py` ~100-112): `fake_sync` passes `running=lambda: []` itself, so `MainWindow` passing `running=` gives a duplicate-keyword `TypeError`. Change to `kwargs.setdefault("running", lambda: [])` and monkeypatch `main_window.kicad_running` to `lambda: []`. Add a `settle(qtbot, w)` helper that waits for `w._path_var_busy` false for the ~6 Generate tests and post-install tests.

**`tests/test_main_window.py` 88-96:** `fake_question` replacing `QMessageBox.question` is the model for monkeypatching the new `_ask_kicad_open`.

**`tests/test_import_dialog.py`:** `:294-297` asserts old blocking (`time >= 0.2`, events `["build_end","close"]`) -> rewrite as "returns immediately, then closes after the gate opens"; `:3605-3620`, `:3623-3638` close-with-running-worker tests change; add a finaliser that joins `dialog._workers` after `qtbot.addWidget` to avoid destroying a widget under a live QThread; assert `QGuiApplication.overrideCursor() is None` in Finishing tests.

---

## Shared Patterns

### Issue-list return, routed by Severity (no message-substring routing)
**Source:** `kicad_lib_manager/table_generator.py` 332-337, `library_scanner.py` 187-192
**Apply to:** all new/changed service functions (`_add_entry`, `add_library_entries`, `sync_kicad_path_vars`)
```python
issues.append(Issue(Severity.ERROR, "table.unrecognised",
    f"Could not update {filename}: no ({tag} ...) table found; file left unchanged"))
```
Severity is read from `issue.severity` (`LogPanel.log_issue`); the CLAUDE.md substring-routing note is stale. Keep codes in `Issue(severity, code, text)`.

### Atomic write after backup
**Source:** `table_generator.py` 356-366; `library_scanner.py` 277-287
**Apply to:** repoint in `_add_entry`; the `kicad_common.json` write on fresh content.
`fsutil.backup_file(...)` -> `isinstance(backup, Issue)` check -> `fsutil.atomic_write_text(path, text, bom=src.bom)` -> `failure` Issue.

### Off-thread work, never `deleteLater` a finished worker
**Source:** `import_dialog.py` `TaskWorker` 257-279, `_reap` 1269-1278, `_start_kicad_check` 3107-3113
**Apply to:** MainWindow KiCad check worker, Finishing state.

### Plain-language text
**Apply to:** every new Result row, log line, dialog and Finishing strip: no raw KiCad field names (e.g. no `ki_fp_filters`), per the owner's plain-language UI memory.

### Layering
**Source:** `tests/test_layering.py` `ALLOWED`
**Apply to:** `table_generator` (imports `fsutil, kicad_files, models, sexpr` only), `kicad_process` (no package imports), `library_scanner` (Qt-free). The tri-state confirm enum lives in `library_scanner.py`; the dialog stays in `main_window.py`.

## No Analog Found

| File / Feature | Role | Data Flow | Reason |
|----------------|------|-----------|--------|
| Finishing strip (Cancel button, 10 s note, wait cursor, pending-action slot) | component | event-driven | No deferred-action UI exists; compose from `_busy_timer`/`_sync_updating` (import_dialog ~2586) for timer style and RESEARCH Pattern 2 for behaviour |
| Three-button KiCad-open `QMessageBox` (Retry/Change anyway/Not now) | component | request-response | Only `QMessageBox.question` Yes/No exists; build a `QMessageBox` instance with custom buttons (RESEARCH Pattern 3) |
| `fsutil file setCaseSensitiveInfo` test fixture | test utility | file-I/O | No case-sensitive test fixture exists; use the RESEARCH fixture code |

## Metadata

**Analog search scope:** `kicad_lib_manager/` (table_generator, library_scanner, main_window, widgets/import_dialog, help_dialog, conflict_row, theme, importer/planner), `tests/` (test_install_apply, test_main_window)
**Files read:** CONTEXT.md, RESEARCH.md (lines 1-461 of 581; remainder was not needed), and targeted ranges of the source above
**Pattern extraction date:** 2026-11-01
