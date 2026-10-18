# Phase 2: Hardening Existing Code - Research

**Researched:** 2026-10-18
**Domain:** Desktop-app hardening (PySide6 GUI + Qt-free Python services) over KiCad S-expression tables, `kicad_common.json`, git submodule
**Confidence:** HIGH (all findings come from reading live source and running probes in this worktree; items I could not verify are tagged `[ASSUMED]` and collected in the Assumptions Log)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Carried forward from Phase 1 (locked; see `.planning/phases/01-foundation/01-CONTEXT.md`)
- Services return `Issue(severity, code, text)` lists and do not raise for expected failures. Phase 2 converts `write_tables`, `sync_kicad_path_vars`, `restore_backup_pair` and scan warnings from `list[str]` to Issues. It also removes the substring-based severity classification in `main_window.py` (`Warning:`, `removed`, `Failed`, `Could not`, `not found`) (Phase 1 D-07).
- Atomic write: temp file in the same directory, fsync, `os.replace` with about 1 s of retries on `PermissionError`. A locked or read-only target yields an `fs.locked` / `fs.write_failed` Issue and the original is left intact (Phase 1 D-05).
- Library tables keep side-by-side `<name>_backup_<N>` backups, which the Restore dialog depends on. The `kicad_common.json` backup goes to the app-data backup directory from `fsutil.default_backup_dir`, outside the repo (Phase 1 D-06).
- Edits splice by span and never re-serialise. Line endings, BOM and strict UTF-8 are preserved, and inserted text uses the file's dominant EOL (Phase 1 D-09 to D-11).

### Library identity (HARD-07, HARD-08)
- **D-01:** Nickname collisions across sources (e.g. the same `.kicad_sym` stem in `Custom/` and `WurthElektronik/`) make the two libraries **mutually exclusive**. Both appear in the tree, marked with a collision warning in the log and the item. Checking one unchecks the other, so only one can be in the selection. Nicknames are never renamed or prefixed, because symbols reference `<Lib>:<FP>` and renaming would break those links. This applies to symbols and to footprints, each considered separately.
- **D-02:** Widget and selection state is keyed by `(source, nickname)` (or `rel_path`), never by nickname alone. This fixes `_fp_items` overwriting in `widgets/library_table.py`. Per-source symbol-to-footprint sync is kept: a symbol in source S drives only footprints in source S.
- **D-03:** If a repo library has the same nickname as an **external** entry in the existing table (URI without `${KICAD_LIB_GITHUB}/`), the external entry wins. It is kept untouched, the repo library is not written for that table, and a warning Issue names both URIs.
- **D-04:** On Rescan, and on the rescan after Set KiCad Path, the selection the user currently has is re-applied by `(source, nickname)`. It is not reloaded from the tables. A library that appears for the first time starts **unchecked**. Phase 5 may explicitly select a library it just installed into, but the default rule stays "unchecked". A library that disappeared is dropped from the selection.
- **D-05:** Only **startup** pre-selects from the destination's existing tables. Switching the destination combo, by browsing or picking from history, only logs which tables exist there. It never changes the selection. Consolidate the duplicated `_check_existing_tables` / `_on_dest_changed` logic while touching it, as CONVENTIONS.md asks.

### Table merge output (HARD-01, HARD-06)
- **D-06:** A regenerated table is **spliced in place**. Everything that is not a managed entry stays byte-identical and in its original position: external entries, unknown or unclassifiable top-level children, `(version ...)`, whitespace, comments and EOL. All managed entries are removed, and the new managed block is inserted as one contiguous run where the first managed entry used to be, or before the closing paren if there was none. A table that does not exist yet is created fresh in the existing `_format_entry` layout. — **Reversibility:** reversible — local to `table_generator`.
- **D-07:** A child that cannot be classified as a `(lib ...)` entry (missing `name`/`uri`, unknown shape) is kept verbatim and produces a warning Issue. It is never dropped. The "preserved N external" count includes these children.
- **D-08:** A managed entry (URI contains `${KICAD_LIB_GITHUB}/`) whose library no longer exists in the repo is a **stale** entry. It is removed, and a warning Issue names it, separately from the ordinary "removed (deselected)" info. The backup still contains it.
- **D-09:** An existing table that cannot be parsed (unbalanced parens, invalid UTF-8, `SexprError`) is **refused**. An error Issue gives the file and line/column, and the file is left untouched with no backup and no write. The other table is still generated if it is healthy.
- **D-10:** Every generated value (`name`, `type`, `uri`, `options`, `descr`) is written through `sexpr.quote()`, so `"` and `\` are escaped. External entries are not re-emitted from parsed values. They keep their original bytes per D-06, so escaping is never applied twice.
- **D-11:** **Delete** the legacy CLI `generate_lib_tables.py` and remove its mentions from `CLAUDE.md` (Repository Structure line, and anything that calls it the CLI alternative). That leaves one code path for table generation. — **Reversibility:** reversible — git history keeps the file.

### kicad_common.json writes (HARD-03, HARD-04)
- **D-12:** KiCad version directories (config dir and footprint dir) are sorted by parsed numeric tuple, so `10.0` beats `9.0`. Non-numeric names are ignored. Only the **newest** config directory's `kicad_common.json` is written. Older installs (7.0/8.0/9.0 on the owner's machine) are left alone.
- **D-13:** "Only `environment.vars` differs" is checked **semantically**. Parse the file, set `KICAD_LIB_GITHUB` and `CUSTOM_3DMODEL_DIR`, and re-dump as UTF-8 (`ensure_ascii=False`) with 2-space indent and a trailing newline, matching KiCad's style. Before the atomic replace, re-parse the output and assert that it equals the original with only the two vars changed. If the assertion fails, abort the write with an error Issue. Byte-level JSON splicing is not required.
- **D-14:** If both vars are already correct, there is no write and no backup. Otherwise, back up first to the app-data backup directory, then write atomically. Keep the newest **10** `kicad_common.json` backups and prune older ones.
- **D-15:** Before writing `kicad_common.json`, detect whether KiCad is running from the process list (`tasklist` on Windows, `ps`/`pgrep` elsewhere; stdlib `subprocess` only) by looking for `kicad`, `eeschema`, `pcbnew` and similar. If it is, still write, but log a warning that KiCad may overwrite the vars on exit and should be closed before Generate is run again. Detection failure is not an error: skip the check silently or at info level.

### Model path cleanup (HARD-09)
- **D-16:** The rewrite of the five `${KIPRJMOD}/Custom/3DModels/...` footprints is a **one-off done during this phase**. It is not a GUI feature. The executor uses a tested `kicad_files` model-path splice helper, which Phase 4's importer will reuse, to rewrite each path to `${CUSTOM_3DMODEL_DIR}/<file>`. The files are:
  - `Custom/Footprints/Connector_USB_GCT.pretty/GCT_USB4730-GF-A_REVA.kicad_mod`
  - `Custom/Footprints/IC_Battery_Fuel_Gauge_ADI.pretty/BGA8N40P2X4_93X167X69N.kicad_mod`
  - `Custom/Footprints/IC_Battery_Fuel_Gauge_ADI.pretty/SON50P200X200X80-9N.kicad_mod`
  - `Custom/Footprints/IC_Button_Controller_ADI.pretty/DFN-8_DDB.kicad_mod`
  - `Custom/Footprints/IC_Button_Controller_ADI.pretty/TSOT-23_TS8.kicad_mod`

  All the target model files already exist in `Custom/3DModels/`. Only the model path span changes, and the rest of each file stays byte-identical, EOL included.
- **D-17:** Commit flow: check out `main` in `Custom`. The detached HEAD `6b1fcb4` equals `main`; verify this again at execution time, and stop and ask if it has diverged. Commit only those five files with a message like `fix(3d): use ${CUSTOM_3DMODEL_DIR} for legacy model paths`. Then make a parent-repo commit on `feature/part-importer` that bumps the `Custom` submodule ref. **Never push** either repo. — **Reversibility:** costly — once the owner pushes `Custom/main`, undoing it needs a revert commit in the submodule and another ref bump.
- **D-18:** The scan's model-path warning follows a **per-source rule**:
  - Under `Custom/`, any `(model ...)` path that does not start with `${CUSTOM_3DMODEL_DIR}/` gets a warning.
  - In other sources (Wurth), the warning stays as today: only absolute or non-variable paths. `${WE_3DMODEL_DIR}` and KiCad's own variables are not flagged.
  - Model parsing moves from `MODEL_RE` to `kicad_files.find_models`.
- **D-19:** The scan also warns when a `${CUSTOM_3DMODEL_DIR}/<file>` reference points to a file that does not exist in `Custom/3DModels/`. Names are compared exactly, case included (e.g. `.STEP` vs `.step` counts as missing), because the repo may be cloned on a case-sensitive OS.

### Claude's Discretion
- Busy-guard UX for HARD-05. Either disable Rescan, Set KiCad Path and Generate while a scan runs, or guard `_start_scan` with `isRunning()` and log an info line. The thread reference must be held until `finished`. The guard must also cover the future post-import rescan (Phase 5).
- How the collision mark is shown in the tree (icon, orange text, tooltip), consistent with the existing orange-warning style.
- `Issue.code` names for the new cases (e.g. `table.unparseable`, `table.stale_managed`, `table.external_clash`, `scan.nickname_collision`, `scan.model_var`, `scan.model_missing`, `config.kicad_running`).
- Whether the table insert point for D-06 is "position of the first managed entry" or "end of table" when managed entries were scattered. Either is fine as long as non-managed bytes are untouched.
- Fixing `LogPanel.COLORS[Severity.X]` KeyError (STATE.md blocker): index with `.value` or change how Severity hashes. Pick whatever keeps `models.py` free of internal imports.
- Order of the table writes and the config write, and whether a config failure is reported independently. Recommended: each is independent, and each file gets its own Issue (HARD-02).
- Whether to add a confirmation before Restore overwrites the tables (CONCERNS.md). It is in scope only if it falls out naturally from converting `restore_backup_pair` to Issues.
- Table backup retention (`*_backup_N`) stays unpruned as today, unless the planner finds it is needed.

### Deferred Ideas (OUT OF SCOPE)
- A GUI "Fix legacy model paths" action. It was considered and rejected for this phase in favour of the one-off cleanup (D-16). Revisit only if new non-conforming paths keep appearing.
- Writing path vars into every installed KiCad version's `kicad_common.json`, which was declined (D-12).
- Byte-level JSON splicing for `kicad_common.json`, which was declined in favour of the semantic check (D-13).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HARD-01 | Regenerating tables keeps every existing external entry, whatever formatting/field order; unclassifiable kept verbatim + warning | Span-splice merge over `kicad_files` (prototype verified on all 5 table fixtures); see Pattern 1, Pitfalls 1-3 |
| HARD-02 | Generate on locked/read-only table logs an error per file; no unhandled exception; UI consistent | `fsutil.atomic_write_*` already returns Issues; per-file independence, shared backup number, `_on_generate` wiring; Pattern 2, Pitfall 5 |
| HARD-03 | `kicad_common.json` backed up, written atomically, only `environment.vars` changed | Verified: `json.dumps(indent=2)+"\n"` is byte-identical to all three real files; `vars` can be `null`; Pattern 3 |
| HARD-04 | Newest KiCad version chosen numerically (`10.0` over `9.0`) | `parse_version` tuple sort for config dir and footprint dir; injectable base path for tests; Pattern 4 |
| HARD-05 | No second scan while one runs | Reproduced a hard crash (access violation) from a single Rescan during a scan; guard + disable pattern; Pattern 5 |
| HARD-06 | Generated values with `"`/`\` escaped | `sexpr.quote` for every field; verified round-trip through `lib_table_entries`; Pattern 1 |
| HARD-07 | Rescan keeps current selection | Key by `rel_path`; `populate()` currently re-syncs footprints and discards them (verified); needs no-sync populate; Pattern 6, Pitfall 7 |
| HARD-08 | Same-nickname libraries reported as collision, distinct in UI | `_fp_items` overwrite and cross-source selection leak reproduced; `collision_peers` + `rel_path` keys; Pattern 6 |
| HARD-09 | `${KIPRJMOD}` model paths rewritten in one cleanup commit; scanner warns on non-conforming paths | 5 files verified (CRLF in worktree, LF in index, `core.autocrlf=true`); `retarget_model` helper; per-source scan rule; Pattern 7 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Extracted from `./CLAUDE.md` and `./.claude/CLAUDE.md` (both read this session). The planner must treat these like locked decisions.

- **Stack:** Python 3.10+ (venv 3.14), PySide6 6.12, stdlib only otherwise unless a dependency is clearly justified. Phase 2 needs no new dependency.
- **Platform:** Windows 11 primary, standard CPython (not MSYS2). Keep the existing `win32`/`darwin`/Linux branches working.
- **Safety:** no write without a preview; writes to KiCad files and the repo must be atomic or backed up; git commits need explicit confirmation (D-17 is the explicit confirmation for the HARD-09 commit, never push).
- **Services are Qt-free** except `settings.py`; `main_window.py` orchestrates and is never imported from lower modules; widgets depend on `models` (and `table_generator` for `backup_dialog`).
- **Side-effecting helpers return message lists** (now `list[Issue]`); severity is decided by the producer, not by substrings in the caller.
- **Qt style:** fully qualified enums (`Qt.CheckState.Checked`); `blockSignals(True/False)` paired in one function; `self._updating` flag in `library_table.py`; long work in a `QThread`; `QMessageBox` only for About (errors go to the log panel).
- **Naming:** snake_case, `_on_<event>` handlers, `_private` helpers, UPPER_SNAKE constants, PascalCase dataclasses; relative imports inside the package; comments explain intent only; one-line docstrings.
- **Paths:** `pathlib.Path` everywhere; `.as_posix()` for anything written to KiCad tables; forward-slash normalisation for KiCad config values.
- **Settings** go through `settings.py` helpers only.
- **Git workflow:** commit submodule changes separately (commit in `Custom`, then update the parent ref); `.gitignore` excludes `*_backup_*`, generated `sym-lib-table`/`fp-lib-table`, `env/`.
- **GSD workflow:** repo edits happen through a GSD command (this research feeds `/gsd-plan-phase`).
- **D-11 requires editing `CLAUDE.md`** (Repository Structure line 18). `.claude/CLAUDE.md` is git-ignored and regenerated by GSD; do not hand-edit it.

## Summary

Phase 2 is a rewiring job, not a research-heavy one: Phase 1 already delivered every primitive the fixes need (`sexpr.parse/Edit/apply_edits/quote`, `kicad_files.lib_table_entries/find_models`, `fsutil.atomic_write_*/backup_file/default_backup_dir`, `Issue/Severity`). I verified by reading the live code that the old `table_generator`, `library_scanner` config functions and `main_window` slots still use none of them. The baseline suite is green (`353 passed, 2 skipped`, 6.3 s with the venv interpreter), so every plan can use a red/green workflow against a trustworthy suite.

Four findings change how the planner should write tasks. (1) The STATE.md blocker "`LogPanel.COLORS[Severity.WARNING]` raises KeyError" is stale on Python 3.14.4: `hash(Severity.WARNING) == hash("warning")` and the lookup succeeds. The real quirk is that `f"{Severity.INFO}"` gives `Severity.INFO`, so the fix is still "always pass `.value`", but it is a hygiene fix, not a crash fix. (2) HARD-05 is worse than described: a single `_on_rescan()` while the startup scan is in flight kills the process with a Windows access violation (reproduced). (3) HARD-07 cannot be met by re-applying selection alone: `LibraryTableWidget.populate()` ends by calling `_sync_footprint_selection()` for every source, which recomputes every footprint from the selected symbols and silently discards restored footprint selection (reproduced, including the startup table pre-selection). (4) `kicad_common.json` in the owner's KiCad 7.0 and 8.0 config dirs has `"environment": {"vars": null}`; the current `env.setdefault("vars", {})` returns `None` and crashes with `AttributeError` on the next line. Also verified: `json.dumps(obj, indent=2, ensure_ascii=False) + "\n"` reproduces all three real `kicad_common.json` files byte-for-byte, so the D-13 "only `environment.vars` differs" requirement can be tested at byte level, not only semantically.

The riskiest work is operational, not algorithmic: the HARD-09 commit lands in a worktree-private submodule gitdir (`C:/Git_Repo_Clones/Kicad_Libraries/.git/worktrees/Kicad_Libraries-importer/modules/Custom`) that disappears if the worktree is removed before the owner pushes `Custom/main`. That step must be a non-autonomous checkpoint, and its verify steps must not click Generate against the owner's real `%APPDATA%\kicad\9.0` config from this worktree, because `REPO_ROOT` here is the worktree path, not the main checkout that `KICAD_LIB_GITHUB` points to today.

**Primary recommendation:** Build the phase in six plans along the dependency order models/helpers -> {table merge, KiCad config, scanner} -> widget -> main_window wiring -> HARD-09 cleanup, using only stdlib and Phase 1 modules, writing each plan test-first against `tmp_path` fixtures, and folding in the five small Phase 1 review fixes that sit directly under this work (WR-01, IN-04, WR-04, IN-01, `backup_file` shared number).

## Architectural Responsibility Map

This is a desktop app, so tiers are application layers rather than web tiers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Table merge by span (HARD-01/06, D-06..D-10) | Services (`table_generator` + `kicad_files`) | — | Pure text-in/text-out, Qt-free, unit-testable with fixtures |
| Atomic write, backup, lock handling (HARD-02) | Services (`fsutil`, called by `table_generator`) | GUI (routes Issues to log) | `fsutil` already returns Issues; GUI must not catch OSError itself |
| `kicad_common.json` sync, version pick (HARD-03/04) | Services (`library_scanner` functions or a new `kicad_config` helper) | OS (APPDATA, Program Files) | Qt-free; base paths must be injectable for tests |
| KiCad-running detection (D-15) | Services (new `kicad_process.py`) | OS (`tasklist`/`ps`) | Reused by Phase 5 POST-05; stdlib `subprocess` only |
| Scan, collision and model-path warnings (HARD-08/09, D-18/19) | Services (`library_scanner`) | Domain model (`ScanResult.issues`, `collision_peers`) | Runs in `ScanWorker` thread, must not touch Qt objects |
| Busy guard (HARD-05) | GUI (`main_window`) | — | Thread lifecycle and action enabling are GUI state |
| Selection state, mutual exclusion, no-resync populate (HARD-07/08) | GUI widget (`library_table`) | Domain model (`selected` flags, `rel_path`) | Widget owns check-state propagation; identity key is `rel_path` |
| Startup vs rescan selection policy (D-04/05) | GUI (`main_window`) | Services (`table_generator.managed_rel_paths`) | Orchestration decision; the table read is a service |
| `${KIPRJMOD}` cleanup (HARD-09, D-16/17) | One-off executor script using `kicad_files.retarget_model` | Git CLI in `Custom` | Not a product feature; helper is reused by Phase 4 |
| Log colouring and escaping | GUI (`log_panel`) | Domain (`Severity.value`) | Index by `.value`; escape HTML |

## Standard Stack

### Core

No new runtime or dev dependency is needed. Everything below is already in the repo.

| Library / module | Version | Purpose | Why standard here |
|------------------|---------|---------|-------------------|
| Python stdlib (`json`, `os`, `re`, `subprocess`, `csv`, `copy`, `pathlib`, `html`) | CPython 3.14.4 `[VERIFIED: ./env/Scripts/python.exe -c "import sys;print(sys.version)" -> 3.14.4]` | JSON sync, process detection, escaping | Project constraint: stdlib only |
| PySide6 | 6.12.0 `[VERIFIED: requirements.txt]` | GUI, `QThread`, `QSettings` | Already pinned |
| `kicad_lib_manager/sexpr.py`, `kicad_files.py`, `fsutil.py`, `models.py` | Phase 1 | Span splice, KiCad file read side, atomic IO, Issues | Phase 1 decisions; "reuse them rather than proposing parallel implementations" |
| pytest 9.1.1, pytest-qt 4.5.0 | pinned in `requirements-dev.txt` `[VERIFIED: tests/test_manifests.py:26-29 asserts these pins]` | Tests | Phase 1 harness |

### Supporting

| Module | Purpose | When to use |
|--------|---------|-------------|
| `html.escape` (stdlib) | Escape log messages before `QTextEdit.append(html)` | `LogPanel.log` (current code interpolates raw text) |
| `tasklist` / `ps` via `subprocess.run(list, shell=False)` | D-15 | Only inside `kicad_process.py` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-repo span splice for tables | `kiutils`, `sexpdata` | Rejected in STATE.md (lossy); no change |
| `psutil` for process list | stdlib `tasklist`/`ps` | D-15 locks stdlib only; `psutil` would be a new dependency |
| `enum.StrEnum` for `Severity` | `(str, Enum)` + `.value` | `StrEnum` is 3.11+, floor is 3.10; use `.value` |
| Reload selection from tables on rescan | Re-apply by `rel_path` | D-04 locks re-apply |

**Installation:** none (`requirements.txt` unchanged).

**Version verification:** no packages are added. Interpreter and pins were confirmed by running the venv interpreter and reading `requirements*.txt` and `tests/test_manifests.py` this session.

## Package Legitimacy Audit

No external packages are installed or recommended in this phase. The `package-legitimacy` seam was not run because there is nothing to check.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                  Startup / Rescan / Set KiCad Path / (Phase 5 post-import)
                                     |
                                     v
                        MainWindow._request_scan()  --busy?--> log info, return
                                     |  (sets busy, disables Rescan/SetPath/Generate)
                                     v
        snapshot selection by rel_path (only on rescan) ----------------------+
                                     |                                         |
                              ScanWorker (QThread)                             |
                                     |                                         |
              library_scanner.scan_all(repo_root, kicad_fp_dir)               |
              |- find_symbol_libs / find_footprint_libs  (rel_path = identity) |
              |- nickname collision pass --> Issue scan.nickname_collision     |
              |                              + lib.collision_peers             |
              |- cross_reference          --> Issues                           |
              '- check_3d_model_paths (kicad_files.find_models)                |
                    Custom: must be ${CUSTOM_3DMODEL_DIR}/ + file must exist   |
                    others: only absolute / non-variable paths                 |
                                     |  finished(ScanResult with .issues)      |
                                     v                                         |
              MainWindow._on_scan_finished (try/finally clears busy)           |
                |- startup:  preselect from tables by rel_path  <--------------+-- tables read via kicad_files
                |- rescan:   re-apply snapshot by rel_path, new libs unchecked
                |- LibraryTableWidget.populate(result)   (NO footprint re-sync)
                '- log Issues (severity.value)

   Generate (Ctrl+G)
     |
     |-- write_tables(dest, sym_libs, fp_libs) -> list[Issue]
     |      for each table independently (sym, fp):
     |        kicad_files.load(existing) --SexprError/bad utf-8--> error Issue, skip (no backup, no write)
     |        classify children: managed | external | unclassifiable(kept + warn) | version/other(kept)
     |        D-03 external nickname clash -> skip repo lib + warn
     |        D-08 stale managed -> warn ; deselected managed -> info
     |        splice: remove managed spans, insert quote()d block at first managed pos / before ')'
     |        fsutil.backup_file(path, path.parent, number=shared N)  -> Issue on failure => no write
     |        fsutil.atomic_write_text(path, new, bom=src.bom)       -> fs.locked / fs.read_only Issue
     |
     '-- sync_kicad_path_vars(repo_root) -> list[Issue]   (independent of table results)
            newest N.M config dir (numeric) -> read_source -> json.loads
            both vars correct? -> info, no write, no backup
            kicad_running()? -> warning config.kicad_running (still writes)
            backup_file(kicad_common.json, default_backup_dir()/..., prune to 10)
            dumps(indent=2, ensure_ascii=False)+"\n"  -> re-parse -> == original+2 vars ? else abort
            atomic_write_text(config_file, text_in_file_EOL, bom=src.bom)
```

### Recommended Project Structure

```
kicad_lib_manager/
├── models.py            # + ScanResult.issues (list[Issue]), + collision_peers on both library dataclasses
├── sexpr.py             # unchanged
├── fsutil.py            # + backup_file(..., number=None); WR-04 and IN-01 fixes
├── kicad_files.py       # + LibTable accessor, WR-01/IN-04 fixes, + retarget_model(ref, new_path) -> Edit
├── kicad_process.py     # NEW: kicad_running() -> list[str]   (Qt-free; Phase 5 reuses)
├── table_generator.py   # REWRITE: splice merge, write_tables -> list[Issue], restore -> list[Issue];
│                        #   DELETE parse_lib_table/_LIB_ENTRY_RE/count_table_entries/list_backups/restore_backup
├── library_scanner.py   # version-sorted find_*; sync_kicad_path_vars -> list[Issue]; collision + model checks
├── main_window.py       # busy guard, selection policy, Issue routing, consolidated table logging
├── widgets/
│   ├── library_table.py # items keyed by rel_path, exclusivity, populate without re-sync
│   ├── log_panel.py     # log_issue(), html.escape, .value
│   └── backup_dialog.py # unchanged (uses list_backup_pairs)
└── (generate_lib_tables.py DELETED, D-11)
tests/
├── fixtures/tables/     # existing 5 files + new managed/external/unclassifiable cases
├── fixtures/kicad/      # NEW synthetic kicad_common.json variants (vars null, populated, CRLF, BOM)
├── test_table_merge.py, test_write_tables.py, test_kicad_config.py, test_kicad_process.py,
├── test_scanner_issues.py, test_main_window.py
└── (extend) test_library_table_widget.py, test_kicad_files.py, test_edits.py, test_fsutil.py, test_layering.py
```

### Pattern 1: Table merge as a span splice (HARD-01, HARD-06, D-06..D-10)

**What:** Parse the existing table with `kicad_files.load`; classify each child of the table node; delete only managed `(lib ...)` spans; insert one contiguous generated block; apply with `sexpr.apply_edits`. Every other byte is untouched by construction.

**Needed read-side addition (not in Phase 1):** `lib_table_entries` (kicad_files.py:146-180) returns entries but not the table node, which is needed for the closing-paren insert point and for the "other children" (`(version 7)`, atoms, unknown lists) that D-06/D-07 require preserving. Add a small accessor, for example `lib_table(root) -> LibTable | None` with `node`, `tag`, `entries`, `others`.

**Prototype result:** I ran the splice below against all five committed table fixtures (`basic`, `empty`, `escaped`, `flags`, `reordered`) with a library named `We"ird\`. Results: `(version 7)` preserved in every case; the CRLF fixtures stayed CRLF; the reordered multi-line external entry and the minimal external entry kept their bytes; the escaped external `descr "Has \"quotes\" and (parens)"` kept its bytes; the generated name round-tripped through `lib_table_entries` as `We"ird\`. [VERIFIED: ran scratch prototype in this session against tests/fixtures/tables/*]

```python
# Source: prototype run this session (verified against tests/fixtures/tables/*); uses Phase 1 APIs
from kicad_lib_manager import kicad_files
from kicad_lib_manager.sexpr import Edit, apply_edits, quote

def _whole_line(text, start, end):
    """Span of the full source line(s) holding only this node, else None."""
    l = start
    while l > 0 and text[l - 1] in " \t":
        l -= 1
    if not (l == 0 or text[l - 1] == "\n"):
        return None
    r = end
    while r < len(text) and text[r] in " \t":
        r += 1
    if r == len(text):
        return l, r
    if text.startswith("\r\n", r):
        return l, r + 2
    if text[r] == "\n":
        return l, r + 1
    return None  # another token follows on the same line

def _entry_text(name, uri):  # D-10: every value through quote()
    return (f'(lib (name {quote(name)})(type "KiCad")(uri {quote(uri)})'
            f'(options "")(descr ""))')

# for each managed entry: edits.append(Edit(*(whole_line or (node.start, node.end)), ""))
# insert point: first managed whole-line start, else the line start of the closing ')'
#   (')' on its own line), else just before ')' with a leading eol
# block = "".join(f"  {entry}{eol}" ...) where eol = source.eol (dominant), "\n" for a new file
# text = apply_edits(source.text, edits)
```

**When to use:** both `sym-lib-table` and `fp-lib-table`; identical code with `tag` `sym_lib_table` / `fp_lib_table`.

**Classification rules to implement and test:**

| Child of the table node | Treatment |
|-------------------------|-----------|
| `(lib ...)` with `name` and `uri` str/atom tokens, `uri` contains `_MANAGED_MARKER` | managed: remove and regenerate |
| `(lib ...)` with `name` and `uri`, no marker | external: untouched, counts as preserved |
| `(lib ...)` missing `name` or `uri`, or with a non-token value (needs WR-01 fix) | unclassifiable: untouched, warning Issue `table.unclassified`, counts as preserved (D-07) |
| `(version N)` | untouched, no warning, **recommend excluding from the "preserved N external" count** |
| Any other list head or bare atom | untouched, warning Issue `table.unclassified` (D-07 "unknown shape") |
| `(lib (name "X")(type "Table")...)` (KiCad 10 nested table) | external by the rule above; untouched `[CITED: research_notes/KiCad 10 vendor part import/kicad10_native_features.md:40-45]` |

**Refusals (D-09):** `SexprError` / bad UTF-8 -> the Issue already carried by `kicad_files.load` (`sexpr.unbalanced`, `sexpr.unclosed`, `sexpr.unterminated`, `fs.bad_encoding`; text includes line/col). Also refuse when the root head is not the expected tag (e.g. a `sym_lib_table` file passed as the fp table) and when the file parses but contains no table node and is not whitespace-only. A whitespace-only or missing file is treated as "create fresh".

**Managed-entry facts the code must use:**
- `_MANAGED_MARKER` is `f"${{{ENV_VAR}}}/"` with `ENV_VAR = "KICAD_LIB_GITHUB"` `[VERIFIED: kicad_lib_manager/table_generator.py:7-8]`. A managed entry's identity is `uri.removeprefix(marker)`, which equals `lib.rel_path` for a library that still exists. Use that for "stale" (D-08), for startup pre-selection (Pattern 6) and to avoid nickname-only matching.
- Generated URI is `f"${{{ENV_VAR}}}/{lib.rel_path}"` `[VERIFIED: table_generator.py:105,122]`.
- Entries removed because deselected are INFO; stale managed entries are WARNING (D-08); the old code classified any "removed" message as a warning by substring `[VERIFIED: main_window.py:385]`.

### Pattern 2: Per-file independent write with a shared backup number (HARD-02)

**What:** For each table separately: load -> merge -> backup -> `atomic_write_text(path, text, bom=source.bom)`. Any failing step yields exactly one ERROR Issue for that file and skips the remaining steps for that file only. Success yields one SUCCESS summary Issue.

**Why a shared number matters:** `list_backup_pairs` pairs `sym-lib-table_backup_N` with `fp-lib-table_backup_N` by number, and the Restore dialog restores a pair `[VERIFIED: kicad_lib_manager/widgets/backup_dialog.py:63-76, table_generator.py:222-242]`. `fsutil.backup_file` numbers each file independently as `max+1` over its own name `[VERIFIED: fsutil.py:146-154]`. With D-09 (an unparseable table gets no backup while the other is still generated) the two sequences diverge, and a later "paired" restore would silently combine tables from different generations. Fix: add an optional keyword `number: int | None = None` to `backup_file` (default behaviour unchanged, so `test_backup_file_numbers_like_table_generator` stays valid) and have `write_tables` compute `N = max(max_sym, max_fp) + 1` once and back up whichever tables it is about to write with that `N`.

**Failure outputs to test** (all use real fsutil codes):

| Situation | Expected single Issue code |
|-----------|----------------------------|
| Target has read-only attribute | `fs.read_only` `[VERIFIED: fsutil.py:85-90]` |
| `os.replace` keeps raising `PermissionError` | `fs.locked` `[VERIFIED: fsutil.py:107-115]` |
| Backup copy fails | `fs.backup_failed` `[VERIFIED: fsutil.py:174-179]`, table not written |
| Existing table unparseable | `sexpr.*` / `fs.bad_encoding`, table not written, no backup |

Simulating a lock deterministically: `monkeypatch.setattr(fsutil.os, "replace", always_denied)` as in `tests/test_fsutil.py:90-105`; the default `retry_delays` is bound at definition time, so a test through `write_tables` costs about 1 s of real sleeping unless `write_tables` forwards `retry_delays`/`sleep` or the test patches `fsutil.atomic_write_bytes`'s defaults. For read-only use `os.chmod(path, stat.S_IREAD)` (as `tests/test_fsutil.py:59-72` does) and restore the mode in a `finally`.

**`restore_backup_pair`:** convert to Issues; read backup bytes, make a safety backup of the current table with `backup_file`, then `atomic_write_bytes`. Unlike today's `shutil.copy2` it can no longer raise `OSError` into the Qt slot.

### Pattern 3: `kicad_common.json` sync (HARD-03, D-12..D-15)

Verified facts that shape the design:

1. `json.dumps(json.loads(raw), indent=2, ensure_ascii=False) + "\n"` equals the raw bytes for all three real files (`7.0`, `8.0`, `9.0`; LF endings, no BOM). [VERIFIED: ran round-trip probe against %APPDATA%\kicad\{7.0,8.0,9.0}\kicad_common.json read-only]. So a byte-level test of "only environment.vars lines differ" is feasible with a synthetic fixture generated the same way, in addition to the semantic D-13 check.
2. `environment.vars` is `null` in the owner's 7.0 and 8.0 files (`{'vars': None}`), populated in 9.0 with `CUSTOM_3DMODEL_DIR`, `KICAD_LIB_GITHUB` and `WE_3DMODEL_DIR`. [VERIFIED: same probe]. The current code does `env_vars = env.setdefault("vars", {})` `[VERIFIED: library_scanner.py:53-54]`, which returns `None` when the key exists with value `null`, and the next line `env_vars.get(key)` raises `AttributeError`. Treat `None` as `{}`; treat any non-dict `environment`/`vars` or non-dict top level as an error Issue with no write (this also covers the Import-LIB wipe scenario in `reports/KiCad 10 vendor part import.md:35`).
3. Desired values are `"KICAD_LIB_GITHUB": repo_str` and `"CUSTOM_3DMODEL_DIR": f"{repo_str}/Custom/3DModels"` with `repo_str = str(repo_root).replace("\\", "/")` `[VERIFIED: library_scanner.py:56-60]`.

**Flow:**

```python
# Source: design derived from verified facts above; Phase 1 APIs
src = fsutil.read_source(config_file)            # Issue on read/encoding failure -> return, no write
config = json.loads(src.text)                    # JSONDecodeError -> Issue, no write
# validate dict shapes; vars None -> {}
# if both vars already equal desired -> INFO "already set", return (D-14: no write, no backup)
# if kicad_running(): WARNING config.kicad_running (still proceed)
# backup first: backup_file(config_file, backup_dir) ; Issue => abort (no write)
new_text = json.dumps(config, indent=2, ensure_ascii=False) + "\n"
# D-13 assertion: json.loads(new_text) == expected, where
#   expected = deepcopy(original); expected["environment"]["vars"] = {**(orig vars or {}), **desired}
# normalize_eol(new_text, src.eol) so a CRLF file stays CRLF; bom=src.bom
atomic_write_text(config_file, new_text, bom=src.bom)   # Issue on lock/read-only
# prune: keep newest 10 numbered backups (numeric sort, not lexical); tolerate unlink errors
```

**Backup location:** `default_backup_dir()` returns `base / "KiCadExtLibManager" / "backups"` `[VERIFIED: fsutil.py:196]` (`%LOCALAPPDATA%` on Windows). Different KiCad versions all name the file `kicad_common.json`, so a flat folder would mix 9.0 and 10.0 backups under one numbering and one retention window. Recommend a subfolder per version: `default_backup_dir() / "kicad_common" / "<N.M>"`, which stays "the app-data backup directory" for D-06/D-14 and keeps pruning simple.

**Pruning pitfall (Windows):** `backup_file` ends with `shutil.copystat`, which copies the read-only attribute `[VERIFIED: fsutil.py:172; reproduced in 01-REVIEW.md IN-01]`; `Path.unlink` on a read-only file raises `PermissionError` on Windows. Prune with a helper that catches `OSError` (and optionally clears the read-only bit first), and fix IN-01 so a failing `copystat` does not report a complete backup as failed.

**Dev hazard:** `REPO_ROOT` in `main_window.py` is `Path(__file__).parent.parent.resolve()` `[VERIFIED: main_window.py:28]`, i.e. this worktree. Running Generate from the worktree against the real `%APPDATA%\kicad\9.0` would repoint `KICAD_LIB_GITHUB` at the worktree (today it points at `C:/Git_Repo_Clones/Kicad_Libraries`). Tests must inject the config base path; human UAT must not press Generate against the real config unless the owner wants that (a backup is made, but the vars change).

### Pattern 4: Numeric KiCad version selection (HARD-04, D-12)

Both functions sort `iterdir()` lexically with `reverse=True` `[VERIFIED: library_scanner.py:31-35, 104-107]`, so `"9.0"` outranks `"10.0"`. Fix with one shared helper:

```python
# Source: design; behaviour verified by reasoning on tuple ordering ((10, 0) > (9, 0))
_VERSION_RE = re.compile(r"[0-9]+(?:\.[0-9]+)*")

def parse_version(name: str) -> tuple[int, ...] | None:
    return tuple(int(p) for p in name.split(".")) if _VERSION_RE.fullmatch(name) else None

def newest_version_dirs(parent: Path) -> list[Path]:
    keyed = [(v, d) for d in parent.iterdir() if d.is_dir() and (v := parse_version(d.name))]
    return [d for _, d in sorted(keyed, key=lambda t: t[0], reverse=True)]
```

- Config dir: take `newest_version_dirs(base)[0]` (D-12: only the newest). The owner's machine has only `7.0 8.0 9.0` config dirs and only `C:\Program Files\KiCad\9.0` `[VERIFIED: directory listing this session]`, so there is no live 10.0 to test against; tests must build `tmp_path/{8.0,9.0,10.0,"kicad-extras"}` trees.
- Footprint dir (Windows): keep the "first version whose `share/kicad/footprints` exists" loop, over the numeric order `[VERIFIED loop shape: library_scanner.py:108-111]`.
- Make the base directories injectable (`find_kicad_config_dir(base=None)`, `find_kicad_footprint_dir(base=None)`), because both branch on `sys.platform` and read `os.environ["APPDATA"]` `[VERIFIED: library_scanner.py:18-26, 92-97]`; patching `sys.platform` in tests is fragile.
- A newest config dir may exist without `kicad_common.json` (fresh install, KiCad not yet closed once). Per D-12 do not fall back to an older version; return a WARNING Issue `config.not_found`.

### Pattern 5: Scan busy guard (HARD-05)

**Reproduced failure:** with `scan_all` patched to block, constructing `MainWindow()` (which starts scan #1) and calling `_on_rescan()` once crashed the interpreter with `Windows fatal exception: access violation` (exit code 127 through Git Bash). The cause is `self._worker = ScanWorker(...)` overwriting the only Python reference to a running `QThread` `[VERIFIED: main_window.py:276 and the probe in this session]`.

**Prescription:**
- One funnel: `_start_scan()` itself returns early (logging an INFO line) when `self._worker is not None`. Every entry (`__init__`, `_on_rescan`, `_on_set_kicad_path`, Phase 5 post-import) goes through it.
- Guard on `self._worker is not None`, **not** `isRunning()`: `ScanWorker.finished = Signal(object)` shadows `QThread.finished`, and `_on_scan_finished` runs on the GUI thread while the thread is still inside `run()`, so `isRunning()` is still true there.
- Also disable the Rescan button, the Rescan / Set KiCad Path / Generate actions while busy (keep action objects as `self._act_*`, since the convention "locals unless needed later" no longer applies).
- Clear the busy state in `try/finally` inside both `_on_scan_finished` and `_on_scan_error`. If `populate()` raises before `self._worker = None`, the guard would otherwise lock the app forever.
- `closeEvent`: if a worker exists, `wait()` before closing, to avoid "QThread: Destroyed while thread is still running" at exit.

**Test recipe (verified to be constructible offscreen):**

```python
# Source: probe in this session; QSettings redirect verified (fileName() moved under tmp dir)
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))  # autouse fixture
monkeypatch.setattr(main_window, "load_kicad_fp_dir", lambda: tmp_path)   # skips the modal QFileDialog
monkeypatch.setattr(main_window, "REPO_ROOT", tmp_repo)
gate = threading.Event(); calls = []
def fake_scan(root, progress=None, kicad_fp_dir=None):
    calls.append(1); gate.wait(5); return ScanResult()
monkeypatch.setattr(main_window, "scan_all", fake_scan)
w = MainWindow(); qtbot.addWidget(w)
w._on_rescan(); w._on_rescan()
gate.set(); qtbot.waitUntil(lambda: w._worker is None)
assert len(calls) == 1
```

Without the `QSettings.setPath` redirect, tests would read and write the owner's real `%APPDATA%/KiCadExtLibManager/settings.ini` `[VERIFIED: get_settings().fileName() printed C:/Users/sylvain/AppData/Roaming/KiCadExtLibManager/settings.ini before redirect]`.

### Pattern 6: Selection identity, collisions and no-resync populate (HARD-07, HARD-08, D-01..D-05)

**Identity key:** use `rel_path`. It is unique per file or `.pretty` directory; `(source, nickname)` is not unique when two libraries in the same source share a stem (for example `Custom/Symbols/A.kicad_sym` and `Custom/Other/A.kicad_sym`). D-02 explicitly allows "or `rel_path`". It also equals the managed URI tail, which gives exact startup pre-selection from tables.

**Reproduced widget defects (so tests can pin them):**
- Preselected footprint with no referencing symbol: after `populate()` its `selected` is `False`, because `populate` ends by calling `_sync_footprint_selection(source)` for every source `[VERIFIED: library_table.py:140-143 and probe output "preselected standalone footprint after populate: False"]`. This also means today's startup footprint pre-selection from the tables is mostly discarded.
- Cross-source nickname collision (`Same` in Custom and Wurth, one Custom symbol selected that references `Same`): `_fp_items` keeps one item `[VERIFIED: library_table.py:58, 134 and probe "items kept: 1"]`; the Custom footprint stays unchecked while the **Wurth** `Same` becomes selected, because the `needed` set is built from all selected symbols regardless of source `[VERIFIED: library_table.py:177-181]`.

**Prescriptions:**
1. `ScanResult.warnings: list[str]` becomes `issues: list[Issue]`; add `collision_peers: list[str]` (peer `rel_path`s) to `SymbolLibrary` and `FootprintLibrary`, filled by the scanner. `models.py` stays free of internal imports; the widget needs no scanner import and tests can set the field by hand.
2. `populate(scan_result)` renders the `selected` flags it was given and does not call `_sync_footprint_selection`. The sync stays on user toggles only. (For a first-ever scan with nothing selected there is nothing to sync.)
3. `_sync_footprint_selection(source)` builds `needed` from symbols **of that source only** (D-02 "a symbol in source S drives only footprints in source S"), and keys items by `rel_path`.
4. Exclusivity: a manual check of a library unchecks its `collision_peers` (inside `self._updating`, with the model flag updated too). During programmatic passes (`select_all`, `_sync_footprint_selection`) a collided library is checked only if no peer is already selected; sorted source order (`Custom` before `WurthElektronik`) makes it deterministic. `write_tables` independently refuses to emit two selected libraries with the same nickname (ERROR Issue `table.duplicate_nickname`, that table not written), so a UI bug cannot corrupt a table.
5. Collision mark: orange foreground + warning icon + tooltip on both items, reusing the style at `library_table.py:108-112`.
6. Startup: pre-select by `rel_path` from the managed entries of both tables for symbols and footprints; no sync. Rescan: in `_on_scan_finished`, snapshot `{rel_path}` of selected symbols and footprints from the old `_scan_result` (objects still alive) and re-apply to the new result; unseen libraries stay unchecked; vanished ones are dropped (D-04).
7. D-05: destination change/browse only logs existing tables. Replace `currentTextChanged` (fires on every keystroke in the editable combo `[VERIFIED: main_window.py:159-163]`) with `textActivated` / `lineEdit().editingFinished`, or accept the log spam; consolidate `_check_existing_tables` and `_on_dest_changed` into one `_log_existing_tables(dest)` using the new table reader.

**Behavioural consequence to document, not fix:** after a restored selection, the first symbol toggle in a source recomputes that source's footprints from its symbols and discards any footprint that was checked manually (CONCERNS.md "Footprint checkboxes are overwritten by symbol state"). Out of Phase 2 scope; add one test that pins current behaviour so a future change is deliberate.

### Pattern 7: Model paths: scan rule and one-off cleanup (HARD-09, D-16..D-19)

**Scan rule (D-18/D-19):** replace `MODEL_RE` text matching `[VERIFIED: library_scanner.py:11,242-249]` with `kicad_files.load(path)` -> `footprint_name(root).node` -> `find_models(node)` (`ModelRef.path` is already `unquote`d). Source = first path segment of the repo-relative path.
- `Custom`: warn `scan.model_var` unless `path.startswith("${CUSTOM_3DMODEL_DIR}/")`; if it does, strip the prefix and warn `scan.model_missing` unless the remainder exists **by exact name**. Build the set once per scan from `Custom/3DModels` (`{p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file()}`); do not use `Path.exists()`, which is case-insensitive on Windows.
- Other sources: keep the current test (`startswith("${")` skip; warn when the path contains `/` or `\`).
- A footprint file that fails to parse yields the Issue from `kicad_files.load` (WARNING level in a scan, not an exception).

**Baseline measured this session:** all 13 `(model ...)` references in `Custom/` resolve by exact name; the 5 `${KIPRJMOD}/Custom/3DModels/...` paths are the only non-conforming ones (`USB4730-GF-A_REVA.step`, `BGA8N40P2X4_93X167X69N.step`, `MAX17048G_T10.step`, `LTC2954IDDB.step`, `LTC2954CTS8.step`); other paths include `MEM2085-00-115-00-A_revA.STEP` and `USB4745-03-A.stp`, which are already correct-case. After the cleanup commit a scan of `Custom/` must produce zero `scan.model_*` Issues, which is the HARD-09 acceptance check.

**Helper to add to `kicad_files` (reused by Phase 4 INST-05):**

```python
# Source: design using verified Phase 1 types (ModelRef.path_node, Edit, quote)
def retarget_model(ref: ModelRef, new_path: str) -> Edit:
    """Return the edit that replaces only the model path token."""
    return Edit(ref.path_node.start, ref.path_node.end, quote(new_path))
```

**One-off executor script (not committed to the package; run with `-I`, scratch location):** for each of the five files from D-16: `kicad_files.load` -> `find_models` -> where `ref.path.startswith("${KIPRJMOD}/Custom/3DModels/")` build `new = "${CUSTOM_3DMODEL_DIR}/" + ref.path.rsplit("/", 1)[1]` -> assert the target exists by exact name -> `apply_edits` -> `fsutil.encode_source(text, bom)` -> `atomic_write_bytes`. Then assert before/after bytes differ only inside the one span (same prefix up to `path_node.start`, same suffix after the old end).

**Git facts verified this session (all in the worktree's `Custom/`):**

| Fact | Evidence |
|------|----------|
| HEAD is detached at `6b1fcb4272d64fc6697b81bade1bd71c1053d447`, equal to local `main` and `origin/main` (`0 0` ahead/behind), working tree clean | `git rev-parse HEAD main`, `git rev-list --left-right --count main...origin/main`, `git status` |
| gitdir is `C:/Git_Repo_Clones/Kicad_Libraries/.git/worktrees/Kicad_Libraries-importer/modules/Custom` (inside the main checkout's `.git`, worktree-private) | `git rev-parse --git-dir` |
| The five files are CRLF in the working tree and LF in the index: `i/lf w/crlf`; `core.autocrlf=true` | `git ls-files --eol`, `git config` |
| No active hooks in the module gitdir or the common dir; `core.hooksPath` unset | listing filtered for non-`.sample` files |
| `git config user.name`/`user.email` set in `Custom` (`sylvanoMTL`) | `git -C Custom config` |
| Parent index has nothing staged; gitlink for `Custom` is `160000 6b1fcb4... Custom` | `git diff --cached`, `git ls-files -s Custom` |

**Commit flow notes:** because the index stores LF while files are CRLF, `git diff --stat` after the edit must show exactly 5 files with 1 insertion and 1 deletion each; anything larger means the edit changed line endings. Stage with explicit paths, never `-A`. Use `git -C Custom checkout main` first (HEAD equals `main`, so no working-tree change). In the parent use `git commit -m "..." -- Custom` so unrelated modified files (`.planning/config.json`) are not swept in. **Orphan risk:** the new `Custom` commit exists only in the worktree-private module gitdir; removing the worktree before the owner pushes `Custom/main` (or fetches the commit elsewhere) discards it and leaves the parent gitlink dangling. The plan must say so in its checkpoint text.

### Pattern 8: Issue routing and LogPanel (all HARD, Phase 1 D-07)

- Add `LogPanel.log_issue(issue)` calling `self.log(issue.text, issue.severity.value)`; `MainWindow._log_issues(issues)` loops it. Delete every `startswith("Warning:")` / `"removed" in msg` / `"Failed" in msg` branch `[VERIFIED: main_window.py:384-397]`.
- `Severity` values are `"info"`, `"warning"`, `"error"`, `"success"` `[VERIFIED: models.py:36-41]` and equal the `COLORS` keys `[VERIFIED: widgets/log_panel.py:7-12; tests/test_models.py:8-9]`.
- STATE.md blocker is stale on this interpreter: `COLORS[Severity.WARNING]` returned `#CC7700` for all four members, and `hash(Severity.WARNING) == hash("warning")` is `True`. What does misbehave is formatting: `f"{Severity.INFO}"` prints `Severity.INFO` `[VERIFIED: probe this session on 3.14.4]`. Use `.value` everywhere and add a test that iterates `Severity` through `log_issue`.
- `LogPanel.log` interpolates the message into HTML with no escaping `[VERIFIED: log_panel.py:34-36]`. Library names, URIs or file paths containing `<` or `&` would render wrongly. Wrap with `html.escape`.

### Anti-Patterns to Avoid

- **Re-serialising a parsed table** (`"\n".join(lines)`): loses `(version 7)`, flags, comments and EOL; this is the HARD-01 bug.
- **Matching managed entries by nickname only:** use the URI tail (`rel_path`).
- **Catching `OSError` in the Qt slot** instead of returning Issues from the service: fsutil already returns Issues; the slot must only route them.
- **Using `isRunning()` as the busy guard** (see Pattern 5).
- **`Path.exists()` for D-19:** case-insensitive on Windows.
- **Calling `scan_all` or any scan helper from the GUI thread** (CONVENTIONS).
- **Importing `main_window` or Qt from services;** `test_layering.py` only pins four foundation modules today, so extend it (see Validation).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parsing lib tables | Another regex (`_LIB_ENTRY_RE`) | `kicad_files.lib_table_entries` (+ small accessor) | Regex requires exact token adjacency; this was the HARD-01 root cause |
| S-expression escaping | `replace('"', '\\"')` | `sexpr.quote` | Handles `\\`, `"`, `\n`, `\r` exactly as KiCad's writer `[VERIFIED: sexpr.py:15-22]` |
| Atomic replace with Windows retry | `write_text` / own temp-file logic | `fsutil.atomic_write_text/bytes` | Already handles read-only pre-check, retries, temp cleanup |
| Numbered backups | `shutil.copy2` + own numbering | `fsutil.backup_file` (+ `number=`) | Exclusive-create, no truncated backups |
| Backup folder location | Hard-coded `%APPDATA%` | `fsutil.default_backup_dir()` | Cross-platform, outside repo |
| EOL / BOM / UTF-8 handling | `read_text`/`write_text` (translates newlines on Windows) | `fsutil.read_source`, `encode_source`, `normalize_eol` | `Path.write_text` on Windows turns `\n` into `\r\n` |
| Span edits | String `replace` | `sexpr.Edit` + `apply_edits` | Rejects overlapping edits |
| Model path rewrite | Regex on the file | `kicad_files.find_models` + `retarget_model` | Scoped to direct `(model ...)` children |
| JSON writing | Manual formatting | `json.dumps(indent=2, ensure_ascii=False)` | Verified byte-identical to KiCad's output on all 3 real files |
| Process detection | Parsing localized `tasklist` text | `tasklist /NH /FO CSV` + `csv` module, exact image-name match | Verified output format; the filtered form prints an "INFO: No tasks..." line on stdout with exit code 0 |
| Version ordering | String sort | Tuple of ints | `"9.0" > "10.0"` lexically |

**Key insight:** every defect in this phase exists because an old module re-implements something Phase 1 now provides. The work is deletion plus rewiring, and the tests prove behaviour is preserved where it should be.

## Runtime State Inventory

HARD-09 is a one-off migration of a path convention, so the five categories are answered explicitly.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | The 5 `.kicad_mod` files in `Custom/` carry `${KIPRJMOD}/Custom/3DModels/...` `[VERIFIED: grep this session]`. Boards (`.kicad_pcb`) that already placed these footprints hold their own copy of the model path and are not changed by editing the library | Code edit via `retarget_model` (data migration of 5 files); no board migration. Mention in the summary that existing boards keep the old path until "Update Footprint from Library" |
| Live service config | `CUSTOM_3DMODEL_DIR` exists in the owner's KiCad 9.0 `kicad_common.json` and points to `C:/Git_Repo_Clones/Kicad_Libraries/Custom/3DModels` `[VERIFIED: probe output]`. 7.0/8.0 have `vars: null` | None for the owner's current machine. After the cleanup, those 5 footprints resolve their models only if Generate (or manual Configure Paths) has set `CUSTOM_3DMODEL_DIR` |
| OS-registered state | None: no scheduled tasks, services or registry keys reference model paths | None, verified by repo grep for `KIPRJMOD` (only the 5 files) |
| Secrets/env vars | `CUSTOM_3DMODEL_DIR`, `KICAD_LIB_GITHUB` live in KiCad's JSON, not process env. The unversioned names are unaffected by KiCad 10's `KICAD10_3DMODEL_DIR` versioning `[CITED: reports/KiCad 10 vendor part import.md:39]` | None |
| Build artifacts | `__pycache__` dirs only; nothing embeds the old string. The legacy `generate_lib_tables.py` is deleted by D-11 (no installed copy; `grep` found no importers) | Delete file; edit `CLAUDE.md` line 18 and `README.md` lines 14, 36, 70 |

**Canonical question answered:** after the five files are updated, the only systems still holding the old string are open KiCad sessions (stale in-memory libraries, restart or reload the footprint library) and existing boards (unchanged by design). The parent repo gitlink must be bumped in a second commit.

## Common Pitfalls

### Pitfall 1: Dropping `(version 7)` and entry flags on regenerate
**What goes wrong:** the old merge emits only `(lib ...)` entries, so `(version 7)` disappears from an existing table, and `(disabled)`, `(hidden)` and unknown fields on a managed entry vanish because managed entries are regenerated.
**Why:** `_merge_table` rebuilds the file `[VERIFIED: table_generator.py:87-91]`; the `flags.fp-lib-table` fixture has three managed entries with `(disabled)`, `(hidden)` and `(future_field "x")` that regeneration drops.
**How to avoid:** splice (Pattern 1). For managed flags, D-06 says remove and regenerate; emit an INFO/WARNING Issue `table.managed_flags_dropped` when a replaced managed entry had `flags` or `extras`, so the loss is visible (Open Question 1).
**Warning signs:** diff between a table and its `_backup_N` shows lines other than managed `(lib ...)` rows.

### Pitfall 2: Inserted block with the wrong EOL or in the wrong place
**What goes wrong:** inserting `\n` into a CRLF file, or putting the block after `)`. 
**How to avoid:** use `SourceText.eol` for every inserted line; a fresh table uses `"\n"` (KiCad's own; ties default to LF per `decode_source` `[VERIFIED: fsutil.py:44-45]`). `Path.write_text` translates newlines on Windows, so never use it. Test CRLF, LF, no trailing newline, `)` on the same line as the last entry, and an empty table (`empty.sym-lib-table` fixture).

### Pitfall 3: Classifying with fields that are not tokens
**What goes wrong:** `lib_table_entries` accepts `(lib (name (x y)) (uri "u"))` as having a name, and bare `(name)` as a flag.
**Why:** open Phase 1 findings WR-01 and IN-04 `[VERIFIED: kicad_files.py:162-168; 01-REVIEW.md]`.
**How to avoid:** fix both in `kicad_files` (require `kind in ("str", "atom")`; route value-less field heads to `extras`) before relying on `LibEntry.name/uri` for D-07 classification.

### Pitfall 4: Backup numbers drifting between the two tables
See Pattern 2. A refused or missing table breaks number pairing unless both use one shared `N`.

### Pitfall 5: A failed write still leaves a backup and a success line
**What goes wrong:** backup created, write fails, GUI also prints "Written ...". 
**How to avoid:** one Issue per failure; never emit the SUCCESS summary unless `atomic_write_text` returned `None`. Accept that a backup may exist for a write that failed (harmless; do not delete it).

### Pitfall 6: `environment.vars: null`
See Pattern 3. Reproduce with a synthetic fixture; this is a current crash, not a hypothetical.

### Pitfall 7: Rescan "preserves" selection but `populate` re-syncs it away
See Pattern 6. Test that a footprint checked with no referencing symbol survives `populate`.

### Pitfall 8: Busy flag stuck after an exception
Clear it in `finally`. Test by making `populate` raise (monkeypatch) and asserting `_worker is None` afterwards.

### Pitfall 9: Wurth scan time after moving to the parser
`kicad_files.load + footprint_name + find_models` ran at about 3.5 MB/s on the 14 `Custom/` footprints (0.039 s for 0.136 MB) versus 0.002 s for the old regex `[VERIFIED: timing probe this session]`. The Wurth submodule is not checked out in this worktree, so the full-scan cost is **unmeasured**. If Wurth holds on the order of tens of MB of `.kicad_mod` files, a rescan could grow from sub-second to several seconds (still off the GUI thread, with progress). Mitigation, in order: add a `wurth`-marked informational timing test; if it is a problem, skip parsing for non-`Custom` files whose text has no `(model` substring or whose cheap regex hits all start with `${`. Do not read the main checkout's Wurth tree to measure (orchestrator rule); measure after `git submodule update --init` in this worktree if the owner agrees.

### Pitfall 10: Orphaned `Custom` commit
See Pattern 7. The checkpoint text must tell the owner to push `Custom/main` (or otherwise preserve the commit) before removing the worktree.

### Pitfall 11: GUI tests touching real state
`MainWindow()` calls `_detect_kicad()` (may open a modal `QFileDialog` and block the test forever), `load_window_geometry()` and `QSettings` writes. Fix with the autouse `QSettings.setPath` fixture plus patching `load_kicad_fp_dir`, `find_kicad_footprint_dir`, `QFileDialog.getExistingDirectory`, `REPO_ROOT` and `scan_all`.

### Pitfall 12: `tests/` that this phase will break (plan their update)
- `tests/test_scanner_skip_dirs.py` calls `check_3d_model_paths` and asserts `m.startswith("[tests/")` on strings `[VERIFIED: file read]`; it must be updated to Issues.
- `tests/test_library_table_widget.py::_fp_item(widget, nickname)` reads `widget._fp_items[nickname]` and its comment says "Phase 2 adapts one place" `[VERIFIED: file read]`.
- `tests/test_layering.py` lists only four modules in `ALLOWED`; extend it to `table_generator`, `library_scanner`, `kicad_process` (Qt-free, imports only downward).

### Pitfall 13: Subprocess search path
A bare `tasklist` is resolved through the process search order. Prefer the absolute path `Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "tasklist.exe"` with `shell=False`, a timeout, and `creationflags=subprocess.CREATE_NO_WINDOW` so no console flashes under `pythonw`. `[ASSUMED: Windows searches the current directory before PATH for bare names]`; the absolute path removes the question.

## Code Examples

### Process detection (D-15), verified on this machine

```python
# Source: probe this session. `tasklist /NH /FO CSV` returned 595 rows on this machine; the
# filtered form (/FI "IMAGENAME eq kicad.exe") prints 'INFO: No tasks are running...' with exit code 0,
# so parse rows and compare names exactly instead of trusting the return code.
import csv, io, os, subprocess, sys
from pathlib import Path

_KICAD_PROCS = {"kicad", "eeschema", "pcbnew", "pl_editor", "gerbview", "pcb_calculator"}

def kicad_running() -> list[str]:
    """Names of running KiCad processes; empty when none or when detection fails."""
    try:
        if sys.platform == "win32":
            exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "tasklist.exe"
            r = subprocess.run([str(exe), "/NH", "/FO", "CSV"], capture_output=True, text=True,
                               errors="replace", timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
            names = [row[0] for row in csv.reader(io.StringIO(r.stdout)) if row]
        else:
            r = subprocess.run(["ps", "-A", "-o", "comm="], capture_output=True, text=True,
                               errors="replace", timeout=5)
            names = [Path(line.strip()).name for line in r.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.SubprocessError):
        return []
    found = {n for n in (x.lower().removesuffix(".exe") for x in names) if n in _KICAD_PROCS}
    return sorted(found)
```

Exact-name matching excludes `kicad-cli` (not an editor) and avoids substring false positives. The executables present in the owner's 9.0 install include `kicad.exe`, `eeschema.exe`, `pcbnew.exe`, `pl_editor.exe`, `gerbview.exe`, `pcb_calculator.exe` and `kicad-cli.exe` `[VERIFIED: directory listing of C:/Program Files/KiCad/9.0/bin]`. `ps -A -o comm=` on Linux/macOS is `[ASSUMED]` portable.

### Semantic check for D-13

```python
# Source: design; json semantics from stdlib
def _only_vars_changed(before: dict, after: dict, desired: dict[str, str]) -> bool:
    expected = copy.deepcopy(before)
    env = expected.setdefault("environment", {})
    env["vars"] = {**(env.get("vars") or {}), **desired}
    return after == expected
```

### Dest-independent lock simulation for tests

```python
# Source: pattern from tests/test_fsutil.py:90-105 (verified by reading)
def always_denied(src, dst):
    raise PermissionError(13, "Access is denied")
monkeypatch.setattr(fsutil.os, "replace", always_denied)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Regex-matched, re-serialised tables | Span-splice over a lossless tree | Phase 1 foundation | Entire merge rewritten |
| `list[str]` messages + substring severity | `Issue(severity, code, text)` | Phase 1 D-07 | Remove substring routing |
| KiCad versions sorted as strings | Numeric tuples | this phase | KiCad 10 (released 2026-03-20 per owner's notes) now sorts first |
| Nested library tables absent | KiCad 10 allows `(type "Table")` entries inside tables | KiCad 10.0 `[CITED: research_notes/KiCad 10 vendor part import/kicad10_native_features.md:40-45]` | Treated as external; preserved byte-for-byte |

**Deprecated/outdated in this repo:**
- `generate_lib_tables.py`: deleted by D-11. Its own regex-free generator ignores existing external entries entirely; no other code imports it.
- `table_generator.list_backups`, `restore_backup`: dead code `[VERIFIED: grep showed only list_backup_pairs and restore_backup_pair used by main_window/backup_dialog]`; remove with the rewrite.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | KiCad's table lexer does not support `#` comments; any comment text without parens/quotes parses as atoms and is preserved as an "unknown child" with a warning | Pattern 1 | Low: a comment with `(` or `"` would be refused as unparseable (D-09), never corrupted |
| A2 | `ps -A -o comm=` works on Linux and macOS for process names | Code Examples | Low: failure returns `[]` (detection is best-effort per D-15) |
| A3 | Windows resolves a bare executable name against the current directory before PATH | Pitfall 13 | Low: the recommended absolute path makes it moot |
| A4 | Wurth's `.kicad_mod` volume makes parser-based scanning noticeably slower than the regex | Pitfall 9 | Medium: if scans become slow the planner needs the pre-filter task; unmeasured |
| A5 | Preserving `(disabled)`/`(hidden)` flags of managed entries is desirable; D-06 as written regenerates them | Pitfall 1, Open Question 1 | Medium: either surprising re-enabling of libraries (if not warned) or a scope change (if preserved) |
| A6 | The owner is fine with `kicad_common` backups in `default_backup_dir()/kicad_common/<N.M>` (a subfolder) rather than the flat folder | Pattern 3 | Low: path detail only |
| A7 | Existing boards keep their embedded model path until the footprint is updated from the library | Runtime State Inventory | Low: informational |

## Open Questions

1. **Managed-entry flags and descriptions (A5).**
   - What we know: D-06 removes and regenerates all managed entries; the `flags.fp-lib-table` fixture shows `(disabled)`, `(hidden)` and unknown fields would be dropped. D-07 and the "Specifics" section stress never silently losing hand-made entries.
   - What's unclear: whether re-enabling a library the owner disabled in KiCad is acceptable.
   - Recommendation: keep D-06 literally and emit a WARNING Issue `table.managed_flags_dropped` naming the library. If the owner prefers preservation, the change is local: reuse `entry.flags` and `extras` source text for entries with the same `rel_path`. Raise at plan review; do not block the plan.

2. **"Preserved N external" count and `(version ...)`.**
   - What we know: D-07 says the count includes unclassifiable children.
   - What's unclear: whether `(version 7)` counts.
   - Recommendation: exclude `(version ...)`; count external `(lib ...)` plus unclassifiable children. Pin it in a test so the number in the log is stable.

3. **Wurth scan time (A4).**
   - What we know: parser is about 20x slower than the old regex on `Custom/`; Wurth is absent here.
   - Recommendation: add the `wurth`-marked informational timing test; include a contingency task (pre-filter) only if the owner reports a regression.

4. **Rescan interplay with in-progress toggles.**
   - What we know: the progress dialog is `WindowModal`, so the user cannot toggle during a scan; snapshotting from the old result at `finished` time is safe.
   - Recommendation: no extra work; document in the plan.

5. **Restore confirmation dialog.**
   - Recommendation: skip (CONVENTIONS limits `QMessageBox` to About; not required by any HARD-*). Converting `restore_backup_pair` to Issues is enough.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Venv Python | all tests, GUI | yes | 3.14.4 `[VERIFIED]` | — |
| PySide6 / pytest / pytest-qt | tests | yes | 6.12.0 / 9.1.1 / 4.5.0 `[VERIFIED: pins + test_manifests]` | — |
| git (Git Bash) | HARD-09 | yes | in use this session | — |
| `Custom/` submodule checkout | HARD-09, live scan tests | yes, detached at `6b1fcb4`, clean | — | — |
| `WurthElektronik/KiCad-Library` checkout | `wurth` tests, D-18 non-Custom behaviour | no (0 entries; 2 tests skipped) `[VERIFIED: pytest skip lines]` | — | Synthetic fixtures; `wurth` marker skips |
| KiCad install | detection tests | KiCad 9.0 only (`C:\Program Files\KiCad\9.0`), config dirs `7.0 8.0 9.0` | — | `tmp_path` trees for 10.0; no live 10.0 available |
| `tasklist` | D-15 | yes `[VERIFIED: ran it]` | — | return `[]` |
| `kicad-cli` | not used in Phase 2 | present at `...\9.0\bin\kicad-cli.exe` | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** Wurth checkout (synthetic fixtures), a real KiCad 10 install (synthetic directory trees).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-qt 4.5.0 (offscreen forced in `tests/conftest.py`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths=["tests"]`, `qt_api="pyside6"`, `addopts="-ra --strict-markers"`, markers `wurth`, `local_kicad`) |
| Quick run command | `./env/Scripts/python.exe -m pytest tests/test_table_merge.py -x -q` |
| Full suite command | `./env/Scripts/python.exe -m pytest -q` |
| Baseline | `353 passed, 2 skipped` in 6.3 s `[VERIFIED: run this session]` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HARD-01 | Every non-managed byte survives; unclassifiable kept + warning; `(version)` kept; CRLF/LF/BOM kept | unit | `./env/Scripts/python.exe -m pytest tests/test_table_merge.py -x -q` | Wave 0 |
| HARD-01 | D-03 external clash, D-08 stale, D-09 refusal (no backup, other table still written) | unit | `./env/Scripts/python.exe -m pytest tests/test_write_tables.py -x -q` | Wave 0 |
| HARD-06 | Value with `"` and `\` is escaped and re-parses to the same value | unit | `./env/Scripts/python.exe -m pytest tests/test_table_merge.py -k escape -x -q` | Wave 0 |
| HARD-02 | Read-only and locked table -> exactly one error Issue per file, original intact, no exception, other table + config still processed | unit | `./env/Scripts/python.exe -m pytest tests/test_write_tables.py -k "locked or read_only" -x -q` | Wave 0 |
| HARD-02 | `_on_generate` with failing write still updates history and runs config sync | Qt | `./env/Scripts/python.exe -m pytest tests/test_main_window.py -k generate -x -q` | Wave 0 |
| HARD-03 | `vars: null`, populated, CRLF, BOM fixtures; backup before write; no write when already correct; unparseable/non-dict -> no write; atomic failure leaves original; only `environment.vars` lines differ; verify-assertion abort | unit | `./env/Scripts/python.exe -m pytest tests/test_kicad_config.py -x -q` | Wave 0 |
| HARD-03 | Backup retention keeps newest 10, numeric order, tolerates read-only backups | unit | `./env/Scripts/python.exe -m pytest tests/test_kicad_config.py -k prune -x -q` | Wave 0 |
| HARD-03 | `kicad_running()` parsing for tasklist CSV, no-match INFO line, `OSError`, timeout | unit | `./env/Scripts/python.exe -m pytest tests/test_kicad_process.py -x -q` | Wave 0 |
| HARD-04 | `10.0` beats `9.0` for config and footprint dir; non-numeric ignored; newest lacking footprints falls through | unit | `./env/Scripts/python.exe -m pytest tests/test_kicad_config.py -k version -x -q` | Wave 0 |
| HARD-05 | Second Rescan / Set KiCad Path while scanning starts no second scan; busy cleared after error and after `populate` exception | Qt | `./env/Scripts/python.exe -m pytest tests/test_main_window.py -k busy -x -q` | Wave 0 |
| HARD-07 | Selection (symbols + footprints, including a footprint with no referencing symbol) identical after rescan; new lib unchecked; vanished lib dropped; startup pre-selects from tables by `rel_path` | Qt | `./env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_library_table_widget.py -k selection -x -q` | Extend existing file + Wave 0 |
| HARD-08 | Scan reports `scan.nickname_collision` for symbols and footprints; widget keeps both items; checking one unchecks the peer; Select All respects exclusivity; `needed` is source-scoped; `write_tables` refuses duplicate nicknames | unit + Qt | `./env/Scripts/python.exe -m pytest tests/test_scanner_issues.py tests/test_library_table_widget.py -x -q` | Wave 0 + extend |
| HARD-09 | `retarget_model`: only the path span changes; CRLF/BOM/two-model/atom-path cases | unit | `./env/Scripts/python.exe -m pytest tests/test_edits.py -k retarget -x -q` | Extend |
| HARD-09 | Scan rule: Custom non-`${CUSTOM_3DMODEL_DIR}` warns, `.STEP`/`.step` case mismatch warns, Wurth-style `${WE_3DMODEL_DIR}` silent, absolute path in other source warns | unit | `./env/Scripts/python.exe -m pytest tests/test_scanner_issues.py -k model -x -q` | Wave 0 |
| HARD-09 | Live: real `Custom/` scan yields zero `scan.model_*` Issues after the cleanup commit (skip if `Custom/` empty) | integration | `./env/Scripts/python.exe -m pytest tests/test_scanner_issues.py -k live -x -q` | Wave 0 |
| Cross-cutting | `LogPanel.log_issue` for every `Severity`; HTML escaping | Qt | `./env/Scripts/python.exe -m pytest tests/test_log_panel.py -x -q` | Wave 0 |
| Cross-cutting | New services are Qt-free and import downward only | unit | `./env/Scripts/python.exe -m pytest tests/test_layering.py -x -q` | Extend |

### Sampling Rate
- **Per task commit:** the single test file for the module being changed (commands above), about 1-3 s each.
- **Per wave merge:** `./env/Scripts/python.exe -m pytest -q`.
- **Phase gate:** full suite green, plus the HARD-09 live scan check and `git -C Custom diff --stat` evidence, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_table_merge.py`, `tests/test_write_tables.py` (HARD-01/02/06)
- [ ] `tests/test_kicad_config.py` + `tests/fixtures/kicad/` synthetic `kicad_common.json` files: `vars` null, populated, CRLF, BOM (generate with `json.dumps(indent=2)`; fixtures dir is already `-text` in `.gitattributes`)
- [ ] `tests/test_kicad_process.py` (monkeypatch `subprocess.run`)
- [ ] `tests/test_scanner_issues.py` (collisions, model rules, live check)
- [ ] `tests/test_main_window.py` + conftest fixtures: autouse `QSettings.setPath`, window factory with patched `load_kicad_fp_dir`, `REPO_ROOT`, `scan_all`
- [ ] `tests/test_log_panel.py`
- [ ] Extend `tests/test_library_table_widget.py` (`_fp_item` helper keyed by `rel_path`), `tests/test_kicad_files.py`/`test_edits.py`, `tests/test_fsutil.py` (`number=`, WR-04, IN-01), `tests/test_scanner_skip_dirs.py` (Issues), `tests/test_layering.py`
- [ ] Framework install: none needed

## Security Domain

`security_enforcement` is enabled in `.planning/config.json` (`"security_enforcement": true`, ASVS level 1, block on `high`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no (single-user local tool) | Writes limited to user-selected destination, KiCad config dir, and `Custom/` for the HARD-09 commit |
| V5 Input Validation / Output Encoding | yes | `sexpr.quote` for all generated S-expression values; strict parse then refuse (D-09); `html.escape` for log text; `json.loads` + shape validation before touching `kicad_common.json` |
| V6 Cryptography | no | — |
| V10 / V12 Files and resources | yes | Atomic same-directory replace, backup-before-write, refuse unparseable inputs, read-only/lock handling via `fsutil`; no path built from file contents without `Path` normalisation |
| V14 Configuration | yes | Back up and verify before modifying KiCad's global config; write only `environment.vars` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed/hand-edited table breaks KiCad or hides entries (injection through names/URIs containing `"` or `\`) | Tampering | `sexpr.quote` on every generated field; external entries never re-emitted (D-10) |
| Truncated or wiped `kicad_common.json` (cf. Import-LIB issue #100 in the owner's report) | Tampering / DoS | Backup first, atomic replace, refuse to write if read/parse failed or shape is not a dict, semantic re-parse assertion (D-13) |
| Partial write on crash or lock | DoS | `fsutil.atomic_write_*`; temp file in same directory |
| Planted `tasklist.exe` found via search order | Elevation of privilege | Absolute `System32` path, `shell=False`, list args, timeout |
| Log injection / HTML rendering of file-derived names | Spoofing / Tampering | `html.escape` in `LogPanel.log` |
| Restore from an arbitrary folder overwrites tables | Tampering | Out of scope for Phase 2 (CONCERNS.md); pattern-restricted names plus safety backup before overwrite |
| Committing unintended files in `Custom` | Tampering | Stage the five explicit paths only, verify `git diff --stat`, never `add -A`, never push (D-17) |

## Sources

### Primary (HIGH confidence) — files read and probes run this session
- `kicad_lib_manager/{table_generator,library_scanner,kicad_files,fsutil,sexpr,models,settings,main_window}.py`, `widgets/{library_table,log_panel,backup_dialog}.py` — full reads with line references above
- `tests/conftest.py`, `test_library_table_widget.py`, `test_layering.py`, `test_scanner_skip_dirs.py`, `test_models.py`, `test_manifests.py`, `test_fsutil.py` (selected), `tests/fixtures/tables/*`
- `pyproject.toml`, `requirements*.txt`, `.gitignore`, `.gitattributes`, `.gitmodules`
- `.planning/{REQUIREMENTS,STATE}.md`, `phases/02-hardening-existing-code/02-CONTEXT.md`, `phases/01-foundation/{01-CONTEXT,01-REVIEW,01-REVIEW-DISPOSITION}.md`, `codebase/{CONCERNS,TESTING}.md`, `research/SUMMARY.md`
- Probes (scratchpad): Severity/COLORS behaviour; widget populate/collision behaviour; `MainWindow` double-scan crash; `QSettings.setPath` redirect; `kicad_common.json` JSON round-trip on `%APPDATA%\kicad\{7.0,8.0,9.0}`; `tasklist` CSV behaviour; parser vs regex timing; splice prototype on all table fixtures; `Custom/` git state, EOL state, model-path inventory

### Secondary (MEDIUM confidence)
- `reports/KiCad 10 vendor part import.md` and `research_notes/KiCad 10 vendor part import/kicad10_native_features.md` (owner notes, which cite KiCad docs/release posts): nested tables in KiCad 10, `kicad_common.json` wipe incident, unversioned custom variables unaffected

### Tertiary (LOW confidence)
- None used for recommendations; unverified items are in the Assumptions Log

No external documentation fetch was needed (stdlib, Qt behaviour and in-repo code only), so the research-plan seam was not invoked.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; Phase 1 modules read in full
- Architecture: HIGH — splice, config and scan flows prototyped or probed against real data
- Pitfalls: HIGH for items reproduced here (double-scan crash, populate resync, collision leak, `vars: null`); MEDIUM for Wurth performance (unmeasured) and git-orphan consequences (reasoned from the verified gitdir location)

**Research date:** 2026-10-18
**Valid until:** 2026-11-17 (stable; revalidate if Phase 1 modules change or the Wurth submodule is checked out)
