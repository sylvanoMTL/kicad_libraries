# Phase 13: Atomic Migration and KiCad Setup - Pattern Map

**Mapped:** 2026-11-11
**Files analyzed:** 27 new/modified
**Analogs found:** 26 / 27 (all analog paths verified git-tracked; no `Custom/` or `WurthElektronik/` file was read)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `kicad_lib_manager/importer/migration/__init__.py` | package marker | n/a | `kicad_lib_manager/importer/__init__.py` | exact (docstring only) |
| `importer/migration/inventory.py` | service | file-I/O read | `importer/layout.py` (`list_symbol_libs`) + `atomic_check.repo_context` | role-match |
| `importer/migration/plan.py` | model (frozen dataclasses) | transform | `importer/plan.py` (`FileOp`, `InstallPlan`) | exact |
| `importer/migration/planner.py` | service | transform | `importer/planner.py` (`_edit_symbol`, `_unit_text`, `_new_source`/`_existing_source`) | role-match (batch, not per part) |
| `importer/migration/gate.py` | service | request-response | `importer/incoming.py` (`incoming_context`, `incoming_issues`) + `atomic_check.AtomicContext` | exact |
| `importer/migration/applier.py` | service (transaction) | file-I/O, batch | `importer/applier.py` | exact (plus delete/rmdir ops) |
| `importer/migration/precheck.py` | service | request-response | `gitops.status_entries` + `commit_step._custom_unavailable` | role-match |
| `importer/migration/mapfile.py` | utility | transform | `importer/commit_plan.py` message builders (text only) | partial |
| `importer/migration/draft.py` | service (app-data JSON) | file-I/O | `scan_cache.py` (`save`, `_read_payload`) | exact |
| `importer/migration/commitplan.py` | service | transform | `importer/commit_plan.build_commit_plan` | exact |
| `kicad_lib_manager/kicad_setup.py` | service (config writer) | file-I/O, request-response | `library_scanner.sync_kicad_path_vars` | exact |
| `kicad_lib_manager/table_descriptions.py` | utility (leaf) | transform | `kicad_files.lib_table` + `table_generator._entry_text` | partial |
| `table_generator.py` (modify) | service | transform | itself (`_entry_text`, `_merge_table`, `_add_entry`) | exact |
| `gitops.py` (modify: `tag`, tag helpers) | service | request-response | `gitops.has_ref`, `head_commit`, `switch_branch` | exact |
| `importer/commit_plan.py` (modify: `deleted`, `message`) | model | transform | itself | exact |
| `importer/commit_gate.py` (modify: skip deleted) | service | transform | itself (`run_gate` loop) | exact |
| `importer/commit_step.py` (modify if rename/delete needs it) | service | request-response | itself (`_precheck`) | exact |
| `importer/planner.py` (modify: promote private names public) | service | transform | itself | exact |
| `settings.py` (modify: `migration_draft_file`) | config | n/a | `settings.scan_cache_file` | exact |
| `widgets/migration_dialog.py` | component (QDialog) | event-driven | `widgets/import_dialog.py` + `atomic_check_dialog.py` | role-match |
| `main_window.py` (modify: 2 actions, hand-off) | controller | event-driven | `_act_import`, `_sync_path_vars`, `_apply_post_install_selection` | exact |
| `widgets/help_dialog.py` (modify: guide page) | component | n/a | existing `HELP_PAGES` | exact |
| `tests/migrationfixtures.py` | test fixture | file-I/O | `tests/customfixtures.py` + `tests/gitfixtures.py` | exact |
| `tests/test_migration_*.py` | test | mixed | `tests/test_install_apply.py`, `test_atomic_fixes.py` | role-match |
| `tests/test_kicad_setup.py` | test | file-I/O | `tests/test_kicad_config.py` | exact |
| `tests/test_importer_layering.py`, `tests/test_layering.py`, `tests/test_gitops.py` (modify) | test | n/a | themselves | exact |
| `CLAUDE.md`, `.planning/PROJECT.md`, `.planning/research/LIBRARY-NAMING.md` | docs | n/a | existing sections (see RESEARCH F-15) | exact |
| `Custom/MIGRATION-ATOMIC.md` (runtime output) | generated doc | file-I/O | none | no analog |

## Pattern Assignments

### `importer/migration/applier.py` (service, ordered-op transaction)

**Analog:** `kicad_lib_manager/importer/applier.py`

**Imports** (lines 7-20): stdlib, then `from .. import fsutil`, `from ..models import Issue, Severity`, `from . import kicad_cli, verify`. In the migration package the relative depth is one more (`from ... import fsutil`).

**Typed undo + rollback** (lines 44-50, 81-110). Extend `kind` with `"rmdir"`; a delete is a `"file"` undo whose `pre_image` is the backed-up bytes:
```python
class _Undo(NamedTuple):
    kind: str  # "file" | "mkdir"
    restore: Path
    written: Path
    pre_image: bytes | None

def _rollback(undo, backup_dir):
    first = {}
    for step in undo:
        if step.kind == "file":
            first.setdefault(str(step.restore).casefold(), step)   # earliest pre-image wins
    for step in reversed(undo):
        ...
            if step.kind == "mkdir":  step.written.rmdir()
            elif step.pre_image is None: step.written.unlink(missing_ok=True)
            else: fsutil.atomic_write_bytes(step.restore, step.pre_image); _drop_twin(step)
        except FileNotFoundError: continue
        except OSError as e: leftovers.append(...)   # keep going, report each leftover
```
New kind `"rmdir"`: undo = `step.restore.mkdir()`; rollback order (reverse) recreates the folder before restoring its files.

**Transaction guard** (lines 329-343): `try: return _transaction(...) except BaseException as error: leftovers = _rollback_once(txn); if not isinstance(error, Exception): raise; ...` Copy verbatim; interrupts roll back then propagate.

**Order inside `_transaction`** (lines 355-431): `_preflight` (containment + sha256 of every source) -> `_gate` (kicad-cli load gate, run once per target library and once for footprints) -> stale-name check -> backup every existing file to app data (`fsutil.backup_file`, re-hash the copy against `base_sha256`) -> ordered writes with `_notify` progress -> `verify` -> rollback on failure. `.bak` files must be backed up too (untracked; app data is the only copy).

**Stale re-check before each write** (lines 460-505): `_still_fresh(op, expected)` and the `expected[casefold path] = sha256(data)` map so a second write to one path sees the first. Copy for write ops; for delete ops compare the current hash to `base_sha256` before `unlink`.

**Case-only rename (P-08):** if `old.casefold() == new.casefold()` keep the on-disk spelling (`_drop_twin` reasoning, `_name_taken` line 209) - never write then delete.

**Folder removal (P-11):** delete listed files, then `os.rmdir`; never `shutil.rmtree`; skip junctions; non-empty folder is kept with a WARNING.

---

### `importer/migration/gate.py` (service, planned end-state atomic gate)

**Analog:** `atomic_check.py` lines 338-361 and `importer/incoming.py:19-47`

```python
@dataclass(frozen=True)
class FootprintTarget:  # text, library, footprint, path, rel_path, problem
@dataclass(frozen=True)
class AtomicContext:
    resolve_footprint: Callable[[str], FootprintTarget]
    model_problems: Callable[[FootprintTarget], list[str]]
# check_symbol(root, name, *, rel_path, fixable, ctx) -> SymbolEntry   (atomic_check.py:586)
# incoming_issues(root, names, *, rel_path, ctx) -> list[Issue]  (ERROR install.atomic.<rule>)
```
Build `AtomicContext` directly over the plan (planned footprints in memory, official KiCad links via `repo_context(repo_root, [], kicad_fp_dir)`); do NOT use `incoming_context` (it lists live `.pretty` folders, so old v1 libraries still resolve - P-02). Convert each failure to `Issue(Severity.ERROR, f"install.atomic.{rule}", text)` and pass through `form.atomic_reason(issue) -> Reason(text, target)` for the plain clickable strip lines (`form._plain` strips raw `ki_*` names).

---

### `importer/migration/planner.py` (service, batch transform)

**Analog:** `importer/planner.py`. Reuse after promoting to public (first, behaviour-neutral task; existing tests protect it): `_edit_symbol(work, ref, new_name, fields, version, rules) -> (edits, mpn, field_changes, keywords)` (line 180), `_Fields` (157), `_unit_text(vendor, unit)` (373, parent-first ordering, spike S8), `_new_source(vendor, unit_text, name, tools)` (518) and `_existing_source(...)` (465, version merge / `kicad-cli sym upgrade`). Do not call `build_plan` per part (reads target library from disk). Lossless edits via `kicad_files` helpers (`rename_symbol_edits`, `footprint_name_edit`, `retarget_model`, `find_models`, `symbol_unit`) and `sexpr.apply_edits`.

Other reuse (call as-is): `suggest.suggest_library(meta, *, own, stock, allowed) -> LibrarySuggestion(name, source, reason, alternatives)` (line 136), `suggest.existing_libraries`, `stems.name_verdict`, `naming.sanitize_name`/`sanitize_filename`, `manufacturers.canonical`, `footprint_index.rank_with_pads`, `keywords`, `footprint_text`. Derived-symbol compare: `sexpr.token_stream`, with sub-symbol name tokens stripped and `(property ...)` children excluded (P-09). D-23: for a footprint with several `(model ...)` blocks rewrite every path to `${CUSTOM_3DMODEL_DIR}/<own name>`; never emit the importer's `extra_models` blocking warning.

---

### `importer/migration/draft.py` (service, app-data JSON)

**Analog:** `kicad_lib_manager/scan_cache.py`

**Constants and save** (lines 38-39, 451-495):
```python
FORMAT = 2
MAX_CACHE_BYTES = 64 * 1024 * 1024
def _repo_key(repo_root): return os.path.normcase(str(Path(repo_root).resolve()))
def save(cache_file, ...) -> Issue | None:
    def failed(reason): return Issue(Severity.WARNING, "cache.save_failed", f"Could not save ...: {reason}")
    try:
        payload = {"format": FORMAT, "repo_root": _repo_key(repo_root), "saved_at": ..., ...}
        text = json.dumps(payload, separators=(",", ":"))
        Path(cache_file).parent.mkdir(parents=True, exist_ok=True)
    except (OSError, TypeError, ValueError) as e:
        return failed(getattr(e, "strerror", None) or str(e))
    failure = fsutil.atomic_write_text(Path(cache_file), text)
    if failure is not None: return failed(failure.text)
    return None
```
**Untrusted read** (lines 506-532): size cap via `stat().st_size`, `json.loads`, explicit `isinstance` checks on every key, one catch tuple `(OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError)`, bad file = start without a draft (INFO note, never raise).

**Path helper:** add `migration_draft_file(repo_root)` in `settings.py` copying `scan_cache_file` (lines 48-51): `Path(get_settings().fileName()).parent / "migration_draft" / f"{key}.json"` with `key = sha256(normcase(resolved path))[:16]`. Draft part identity = `(source rel_path, original symbol name)` plus sha256 fingerprints of symbol block / footprint / model (content hashes, not `changes.py`).

Layering: `scan_cache` is a top-level module in `tests/test_layering.py` ALLOWED; `draft.py` lives in the importer package and must not import `settings` (Qt). Take the path as an argument.

---

### `kicad_lib_manager/kicad_setup.py` (service, config writer)

**Analog:** `library_scanner.sync_kicad_path_vars` (lines 227-367). Copy the contract, do not refactor it (`test_kicad_config.py:327` monkeypatches `library_scanner._only_vars_changed`). Import its helpers (`find_kicad_config_dir`, `_read_config`, `_path_var_refusal`, `ConfirmAnswer`, `_as_answer`, `_prune_backups`, `_PATH_VAR_PASSES`) - this needs `kicad_setup` registered in `tests/test_layering.py` ALLOWED with `library_scanner`, `fsutil`, `kicad_files`, `kicad_process`, `models`.

**Signature and flow** (lines 227-234, 249-326):
```python
def sync_kicad_path_vars(repo_root, *, config_base=None, backup_root=None,
        running: Callable[[], list[str]] | None = None,
        confirm: Callable[[list[tuple[str, str | None, str]]], bool | ConfirmAnswer] | None = None) -> list[Issue]:
    config_dir = find_kicad_config_dir(config_base)        # WARNING config.dir_not_found
    read = _read_config(config_file)                       # (src, config, old_vars) | Issue
    changes, issues, set_issues = _plan_changes(old_vars, desired)
    if not set_issues: return issues                       # idempotent: INFO only, no write
    refusal = _path_var_refusal(repo_root, repo_str, old_vars)   # worktree / other checkout
    names = (running or kicad_running)()
    for _ in range(_PATH_VAR_PASSES):                      # confirm -> re-read -> recompute (max 3)
        answer = _as_answer(confirm(changes))
        if answer is ConfirmAnswer.RETRY: return issues + [Issue(Severity.INFO, "config.retry", ...)]
        if answer is not ConfirmAnswer.WRITE: return issues + [Issue(Severity.INFO, "config.declined", ...)]
        read = _read_config(config_file)                   # fresh content, never the pre-question copy (D-11)
        ...
        if fresh_changes == changes: break
        changes = fresh_changes
    else:
        return [Issue(Severity.WARNING, "config.keeps_changing", ...)]
```
**Write tail** (lines 328-366):
```python
new_config = copy.deepcopy(config)
new_text = json.dumps(new_config, indent=2, ensure_ascii=False) + "\n"     # byte-identical round trip on KiCad 10 files (F-07)
if not _only_vars_changed(...): ... Issue(Severity.ERROR, "config.verify_failed", ...)   # new verify: only chooser keys changed
new_text = fsutil.normalize_eol(new_text, src.eol)
backup = fsutil.backup_file(config_file, (backup_root or fsutil.default_backup_dir()) / "kicad_common" / config_dir.name)
failure = fsutil.atomic_write_text(config_file, new_text, bom=src.bom)
issues.extend(_prune_backups(backup_dir, config_file.name, keep=_KICAD_COMMON_BACKUPS_KEPT))
```
Chooser differences: two files (`kicad_common.json` `session.pinned_symbol_libs`/`pinned_fp_libs`; `eeschema.json` `lib_tree.columns`/`column_widths`), one confirm for both, verify both before writing either, backups under `backup_root/"kicad_common"/<ver>` and `"eeschema"/<ver>`, write common then eeschema, restore the first from memory if the second fails, refusal reads `KICAD_LIB_GITHUB` from `kicad_common.json` even when only `eeschema.json` changes. Pins/columns algorithms: RESEARCH F-08 (pins from `Atomic_` nicknames in the Destination tables via `table_info`/`kicad_files.lib_table`; columns remove only `"MANUFACTURER"`, insert `"MPN"`,`"Manufacturer"` after `"Description"`, width 200 for MPN).

---

### `table_generator.py` + `table_descriptions.py` (TBL-01)

**Analog:** `table_generator.py` lines 16-20, 80-208, plus `_add_entry` (line 319, call at 398):
```python
def _entry_text(name: str, uri: str) -> str:
    return (f'(lib (name {quote(name)})(type {quote("KiCad")})'
            f'(uri {quote(uri)})(options {quote("")})(descr {quote("")}))')
```
Four call sites: `_merge_table` lines 105 and 161, `_add_entry` lines 398 (and its missing-table template). Change to `_entry_text(name, uri, descr="")` and thread a `describe: Callable[[str, str], str]` (name, rel_path) through `_merge_table`, `generate_sym_lib_table`/`generate_fp_lib_table`, `write_tables`, `add_library_entries`; default describer needs no stock text. Keep an existing non-empty managed `descr`: build `{tail: entry.descr}` from the `managed` list (lines 124-136, `_tail(entry)`) before regenerating. `_merge_table` already drops stale managed entries (`table.stale_managed`, lines 168-176); keep those literal phrases stable (main_window routes severity by substrings). Layering: either add `table_descriptions` to `table_generator`'s ALLOWED set in `tests/test_layering.py` (line 19) or keep the describer injected (preferred; `main_window` passes the stock mapping read from `kicad_fp_dir.parent / "template" / "sym-lib-table"` via `kicad_files.lib_table`).

---

### `gitops.py` (modify) - `tag` helpers

**Analog:** `gitops.py` lines 194-206 and 344-349.
```python
def head_commit(ctx, repo) -> str | None:
    run = run_git(ctx, repo, "rev-parse", "-q", "--verify", "HEAD")
    return run.stdout.strip() or None if _ok(run) else None

def has_ref(ctx, repo, ref) -> bool:
    return _ok(run_git(ctx, repo, "rev-parse", "-q", "--verify", f"{ref}^{{commit}}"))

def switch_branch(ctx, repo, name) -> GitRun | Issue:
    return run_git(ctx, repo, "switch", name)
```
Add `tag_target(ctx, repo, name="pre-atomic")` (rev-parse `refs/tags/{name}^{{commit}}`) and `create_tag(ctx, repo, name="pre-atomic")` -> `run_git(ctx, repo, "tag", name)`; constant tag name only. Add `"tag"` to `ALLOWED_SUBCOMMANDS` (lines 21-24) and edit `EXPECTED_ALLOWED` in `tests/test_gitops.py` (line 25-27) deliberately; `tag` is not in `FORBIDDEN_SUBCOMMANDS`. Add any new module that calls git to `GIT_MODULES` (test line 38-44). Deletions and renames need no new subcommand: `commit_paths` (`commit --only --pathspec-from-file`) and `add_intent` already handle deleted-tracked plus new paths (verified in RESEARCH F-06). Decision: absent -> create; equals `head_commit` -> reuse; elsewhere -> refuse with plain reason.

---

### `importer/commit_plan.py`, `commit_gate.py` (modify) - deletions

**Analog:** themselves.
```python
@dataclass(frozen=True)
class CommitFile:        # commit_plan.py:25-35
    rel: str; display: str; path: Path; kind: str; expected_sha256: str
    base_sha256: str | None; note: str = ""; installed: bytes | None = None
# add:  deleted: bool = False   (expected_sha256 = "")

def changed_since_install(cplan):   # line 175-177 - deleted file is fresh while absent
    return tuple(f.display for f in cplan.files if file_sha256(f.path) != f.expected_sha256)
```
Update `changed_since_install` and `rebaseline` (lines 180-195) to treat `deleted` as fresh while `file_sha256(path) is None` (stale if it reappears). `commit_gate.run_gate` (line 361-371 loop `for cfile in cplan.files: ... if cfile.kind != "symbol_lib" or not is_atomic(library): continue`) must `continue` on `cfile.deleted` first, else an emptied `Atomic_` library yields "the library could not be checked" (P-04). Same skip in `_committed_footprints`, `_committed_models`, `linked_custom_files`, `_with_linked_files`. Add `CommitPlan.message: str | None = None` so `default_message` returns the migration text. Never put `.bak` in `files` (git-ignored; `_precheck` refuses `commit.ignored`, P-03). Layering: `importer.commit_plan` ALLOWED is `{"models","importer.plan"}` (test_importer_layering.py line 156); the migration builder lives in `importer/migration/commitplan.py` (new ALLOWED entry including `importer.commit_plan`).

**Builder analog** `build_commit_plan` (lines 97-160): per-file `_disk_spelling` (git matches pathspecs exactly), containment `resolved.is_relative_to(custom_real)` -> `commit.outside_custom` ERROR, `seen_rel` de-dupe, sort by `(display.casefold(), display)`.

---

### `widgets/migration_dialog.py` (component, event-driven)

**Analogs:** `widgets/import_dialog.py` (shell, worker, commit glue), `widgets/atomic_check_dialog.py` (failure list, fill-in inputs, preview/apply pages), `widgets/preview_tree.py` + `widgets/content_view.py` (Files tab).

Do NOT try to extract widgets from the 3,600-line `ImportDialog` (library combo etc. are methods). Reuse as imports (import_dialog.py lines 36-75, 268-289, 343-366): `TaskWorker(fn, parent, tag)` with signals `progress(str,int,int)`, `result(object)`, `failed(str)`; `official_candidates(footprint_index, folder, *, package_code, vendor_path, stock, part, progress)`; `centre_window`/`fit_window`; `ADD_MODEL_TEXT`, `OFFICIAL_FOOTPRINT_TEXT`; `CommitPanel`; `ContentViewDialog(content: ContentText)`; `PreviewTree.render(sections)` fed by `importer/preview.PreviewRow/PreviewSection`; `ConflictRow`; `theme` tokens only (no hard-coded colours or px sizes). Copy (do not share) `ImportDialog._start_commit_step`, `_start_probe`, `_apply_probe_result`, `_on_check_again`, `_on_recheck_done`, `_on_commit_requested`, `_on_commit_done` into a small `CommitStepHost` helper, keep the generation-event cancel and "cannot close while committing" rule. Test seam: a frozen dataclass of callables like `ImportCore` (line 368-371).

Rules to follow: planning, kicad-cli, stock sibling index, footprint index, git probe all on `TaskWorker`; finished threads are never `deleteLater`'d (`_reap`); every label/tooltip/strip line `setTextFormat(Qt.TextFormat.PlainText)` or escaped (P-14); plain-language text (use `form.TEXT_LABELS`, `form._plain`); `blockSignals` pairs; widgets depend only on `models` and importer services.

---

### `main_window.py` (modify)

**Analog:** itself.

**Menu action** (lines 255-260):
```python
self._act_import = QAction("&Import Part...", self)
self._act_import.setShortcut(QKeySequence("Ctrl+I"))
self._act_import.setToolTip("Import a vendor package (.zip or folder) into Custom/")
self._act_import.setStatusTip("...")
self._act_import.triggered.connect(lambda: self._open_import())
file_menu.addAction(self._act_import)
```
Add `_act_migrate` (enabled only while Custom has a non-`is_atomic` symbol library, a Custom footprint library other than `Atomic_Footprints`, or a `.bak` in `Custom/Symbols`; greyed with a tooltip saying why) and `_act_setup_chooser`. Include both in `_set_scan_running` (line 468-474), add a `_migration_dialog` slot with the same close handling as `_import_dialog` (lines 226, 945, 979, 1051-1061, 1397; closeEvent ~1394-1425). If a shortcut is added, update `HELP_PAGES["shortcuts"]` (`tests/test_help_dialog.py::test_help_shortcuts_complete`).

**KiCad-open dialog and worker for the chooser** (lines 1152-1250): `_confirm_path_var_changes` / `_kicad_open_box` (Retry / Change anyway / Not now; `ConfirmAnswer.RETRY/WRITE/DECLINE`), `_sync_path_vars` -> `TaskWorker(lambda progress: kicad_running())` -> `_on_path_var_check(names)` -> `sync_...(running=lambda: names, confirm=lambda changes: ...)`, `config.retry` restarts the worker, `_path_var_busy` guard. Parameterise the dialog title and text with the subject; keep the path-variable defaults byte-stable (tests assert them).

**Post-Run selection** (lines 813-838, `_apply_post_install_selection`): plural variant that sets `lib.selected = True` for every `Atomic_*` symbol library and `Atomic_Footprints` in the new `ScanResult` before `write_tables` (P-01; `_reapply_selection` unchecks new libraries). Generate stays behind a Result-view button (D-24); a main-window test must show the new libraries survive Generate.

---

### `tests/migrationfixtures.py` and migration tests

**Analogs:** `tests/customfixtures.py`, `tests/gitfixtures.py`.

`customfixtures.py` (lines 40-117): `SyntheticLibrary(name, v1_name, version, symbols, footprints, models)`, `SYNTHETIC_LIBRARIES` tuple, `FORMAT_VERSIONS = (20211014, 20231120, 20241209, 20251024)`, `write_synthetic_custom(root, *, naming="v1") -> RepoLayout` writing `root/Custom/{Symbols,Footprints,3DModels}`; `write_atomic_custom(root)` (line 405), `write_fake_kicad(root)` (387, fake KiCad stock + footprints), `guard_custom(custom_dir)` (459, live-`Custom/` digest guard; tests must never touch live `Custom/`). Build `migrationfixtures` by extending these (do not edit the existing tuple): add variants (LTC2954-style shared Value, MAX17048G/X), a shared footprint, a two-model footprint (D-23), a duplicate model file, a `.bak`, an already-Atomic part, and a board-feature footprint (D-21).

`gitfixtures.py` (lines 36-115): `GitRepos(root, parent, custom, custom_remote, parent_remote, env)` with `.git(cwd, *args, check=True, input=None)`; `populate_custom(custom)` (writes `.gitignore` with `*.bak`); `_build(root, autocrlf, populate, remote_branch)`; `make_superproject(...)` (161); `requires_git` marker (36); `import_files` (213), `commit_file` (269). Use for MIG-01 clean check (untracked files, ignored `.bak` not blocking), tag create/reuse/refuse, and the deletions+renames commit (`git diff-tree` lists both sides).

`tests/test_kicad_config.py` (template for `test_kicad_setup.py`): fixtures `repo`, `cfg`, `backups` (lines 101-115), helpers `_write_config(base, version, obj, *, crlf, bom)` (131), `_sync(...)` (145), `_recorder(answer)` (151), `_assert_untouched` (254); cases to mirror: declined/missing confirm writes nothing, unchanged never asks, worktree and other-checkout refuse without asking (493-530), KiCad running warns, read-only/locked file returns Issue and keeps bytes (349-380), unusable backup root blocks, only newest ten backups kept, CRLF/BOM preserved, verification failure aborts before backup (324-334).

**Layering registrations (same task as each new module, P-16):**
- `tests/test_importer_layering.py` `ALLOWED` (lines 35-187): add `importer.migration` (`set()`), plus an entry for each migration module listing exactly the relative targets it imports (note `importer.migration.*` modules reach top-level modules as `models`, `fsutil`, `gitops`, `atomic_check`, etc.). Package `__init__.py` must hold only a docstring (rule at lines 14, 270).
- `tests/test_layering.py` `ALLOWED` (lines 14-35) and `_CODE` import list (lines 40-44): add `kicad_setup` and `table_descriptions`; widen `table_generator` only if it imports the leaf.
- `tests/test_gitops.py`: `EXPECTED_ALLOWED` (add `"tag"`), `GIT_MODULES`.

## Shared Patterns

### Qt-free services return `Issue` lists
**Source:** `kicad_lib_manager/models.py` (`Issue(Severity, code, text)`), used in `applier.py:23-24` (`_err`), `scan_cache.py:49`, `gitops`. Side-effecting helpers return `list[Issue]`; callers route by severity and literal phrases (`Warning:`, `removed`, `Failed`, `Could not`, `not found` - keep stable). `QMessageBox` only for the sanctioned KiCad-config confirm.

### Atomic writes, backups, lossless edits
**Source:** `fsutil.atomic_write_bytes/atomic_write_text(path, text, bom=)`, `fsutil.backup_file(path, dir)` (numbered `_backup_N`), `fsutil.read_source` (BOM/EOL kept), `fsutil.normalize_eol`, `fsutil.default_backup_dir`. **Apply to:** every write in the migration, chooser, draft. Never `open(..., "w")`. Span edits via `sexpr.Edit`/`apply_edits` and `kicad_files` helpers; CRLF/LF and untouched bytes stay identical.

### Containment and stale checks
**Source:** `applier._preflight`/`_still_fresh`, `atomic_fixes._inside(repo_root, rel, area)` (line 89) and `apply_preview` (637-678: refuse the whole batch when any file differs from the preview). **Apply to:** all migration ops: `path.resolve().is_relative_to(custom_dir.resolve())`.

### Git only through gitops
**Source:** `gitops.run_git` + `ALLOWED_SUBCOMMANDS`. **Apply to:** tag, clean check (`status_entries`, which omits ignored files), commit. No `subprocess` elsewhere; no push; Custom commit first, then parent ref (`commit_gitlink`, line 398).

### Atomic rule and plain reasons
**Source:** `atomic_check.check_symbol`, `importer/incoming.incoming_issues`, `importer/form.atomic_reason`. **Apply to:** Run gate and failure strip. Never re-implement rules.

### App-data JSON with untrusted read
**Source:** `scan_cache._read_payload` (506-532). **Apply to:** draft; plus the stock-table and KiCad JSON reads (tolerate bad shape, return Issue, never raise).

### Worker discipline
**Source:** `widgets/import_dialog.TaskWorker` (343-366), `main_window._start_path_var_check` (1209-1218). **Apply to:** migration planning, kicad-cli, git probe, Run, chooser `kicad_running()`. GUI thread never blocks.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `Custom/MIGRATION-ATOMIC.md` writer (`importer/migration/mapfile.py`) | text generator | transform | No existing generated report document; shape is defined by D-16 (library map, symbol renames, footprint link changes, relink steps: Edit Symbol Library Links -> Update Symbols from Library -> Update PCB from Schematic). Write it as an ordinary planned file inside the transaction so it passes `_inside` and enters the commit list. |

Partial analogs (planner should lean on RESEARCH): `table_descriptions.py` stock-table reader (use `kicad_files.lib_table(...).entries[i].name/.descr`; RESEARCH F-01/F-02), delete/rmdir/move ops (no existing delete op in `applier` or `atomic_fixes`; RESEARCH F-03), derived-symbol rendering (RESEARCH F-11).

## Metadata

**Analog search scope:** `kicad_lib_manager/`, `kicad_lib_manager/importer/`, `kicad_lib_manager/widgets/`, `tests/`
**Files scanned:** about 30 read or grepped (excerpts only; large files via targeted offsets)
**Tracked-source gate:** all 21 analog files confirmed by `git ls-files`; none is a gitignored mirror
**Pattern extraction date:** 2026-11-11
