# Phase 2: Hardening Existing Code - Context

**Gathered:** 2026-10-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 2 rewires the existing table generator, scanner, KiCad detection, `kicad_common.json` writer and main window onto the Phase 1 primitives (`sexpr.py`, `kicad_files.py`, `fsutil.py`, `Issue`/`Severity`). It fixes the known defects HARD-01 to HARD-09, so that generating tables, detecting KiCad and rescanning no longer lose data, crash or race. It also carries out the one-off `${KIPRJMOD}` model-path cleanup commit in `Custom`.

It delivers no importer functionality and no new user-facing feature beyond warnings, collision handling and safer behaviour. Requirements: HARD-01 to HARD-09 (see `.planning/REQUIREMENTS.md`).

</domain>

<decisions>
## Implementation Decisions

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` §Phase 2: goal and the five success criteria
- `.planning/REQUIREMENTS.md`: HARD-01 to HARD-09
- `.planning/PROJECT.md`: constraints (stdlib only, atomic or backed-up writes, Windows CPython) and the hardening list under Active
- `.planning/STATE.md` §Blockers/Concerns: `Severity` hashing / `LogPanel.COLORS` KeyError; the HARD-09 commit in a detached `Custom` HEAD

### Prior phase decisions
- `.planning/phases/01-foundation/01-CONTEXT.md`: D-05 (atomic write), D-06 (backup locations), D-07 (Issue contract), D-09 to D-11 (EOL/encoding), D-12 (kicad_files read side, which Phase 2 extends)
- `.planning/phases/01-foundation/01-REVIEW-DISPOSITION.md`: Phase 1 code-review dispositions (check for any `open` or `deferred` rows touching the modules Phase 2 rewires)

### Defect analysis
- `.planning/codebase/CONCERNS.md`: line-level descriptions of every defect fixed here (dropped external entries, unhandled OSError, overlapping scans, selection reset, nickname collisions, non-atomic config write, unescaped values, lexical version sort, log-level substrings)
- `.planning/research/SUMMARY.md` §"Phase 2: Harden existing code": deliverables list
- `.planning/research/PITFALLS.md`: pitfalls 14, 15 and 17 (named in SUMMARY.md for Phase 2)
- `.planning/research/ARCHITECTURE.md`: `LibTable` / `kicad_files` responsibilities and the dependency direction (services stay Qt-free)

### Conventions
- `.planning/codebase/CONVENTIONS.md`: naming, Issue/message routing, `blockSignals` and `_updating` patterns, the duplication-to-avoid notes
- `.planning/codebase/TESTING.md`: test layout and run command (`.\env\Scripts\python.exe -m pytest`)
- `CLAUDE.md`: needs the `generate_lib_tables.py` mentions removed (D-11)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kicad_lib_manager/kicad_files.py`: `load`, `parse_bytes`, `lib_table_entries` (returns `LibEntry` with spans), `find_models` (`ModelRef` with spans), `footprint_name`. These are the basis for the D-06 splice merge and the D-16/D-18 model-path work. Phase 2 adds a model-path edit helper here.
- `kicad_lib_manager/sexpr.py`: `parse`, `Edit`, `apply_edits`, `quote`, `unquote`, `SexprError(line, col)`, used for D-06, D-09 and D-10.
- `kicad_lib_manager/fsutil.py`: `atomic_write_bytes` / `atomic_write_text`, `backup_file(path, backup_dir)`, `default_backup_dir`, `read_source`, `normalize_eol`, used for HARD-02/03 and D-14.
- `kicad_lib_manager/models.py`: `Severity(str, Enum)`, `Issue`. Watch the COLORS KeyError noted in STATE.md.
- `tests/test_library_table_widget.py`: the existing offscreen widget test for per-source sync. Extend it for `(source, nickname)` keying and mutual exclusion (D-01/D-02).
- `tests/fixtures/`: synthetic lib tables with escaped quotes, reordered fields and unknown children (Phase 1 D-02), ready to drive the merge tests.

### Established Patterns
- Services are Qt-free and return values. `main_window.py` routes Issues to `LogPanel` by severity.
- `blockSignals(True/False)` pairs and the `self._updating` flag in `library_table.py` prevent feedback loops. Use them for the mutual-exclusion uncheck.
- `ScanWorker(QThread)` with `progress` / `finished` / `error` signals. Currently `_start_scan` overwrites `self._worker` unguarded (`main_window.py` ~276).

### Integration Points
- `table_generator.py`: `parse_lib_table` (regex `_LIB_ENTRY_RE`), `_merge_table`, `_format_entry`, `generate_sym_lib_table`, `generate_fp_lib_table`, `_check_nickname_collisions`, `write_tables`, `backup_existing`, `restore_backup_pair`. The unused `list_backups` / `restore_backup` are dead code (CONCERNS.md).
- `library_scanner.py`: `find_kicad_config_dir` / `find_kicad_footprint_dir` (lexical sort), `sync_kicad_path_vars` (non-atomic write, no backup), `check_3d_model_paths` (`MODEL_RE`), `_parse_footprint_refs` (`FOOTPRINT_RE`), `cross_reference` (nickname-only matching).
- `main_window.py`: `_on_generate` (no OSError handling, substring severity), `_apply_existing_selection` (to become startup-only), `_on_rescan`, `_on_set_kicad_path`, `_check_existing_tables` / `_on_dest_changed` (duplicated).
- `widgets/library_table.py`: `_fp_items: dict[str, QTreeWidgetItem]` keyed by nickname (line ~58, ~134); `_sync_footprint_selection(source)`.
- `widgets/backup_dialog.py` / `restore_backup_pair`: messages to convert to Issues.
- The `Custom` submodule: detached HEAD at `6b1fcb4`, equal to `main`. Its gitdir is worktree-private.

</code_context>

<specifics>
## Specific Ideas

- Hand-made entries in your KiCad tables must never be lost or overridden by the tool (D-03, D-06, D-07).
- The diff between a regenerated table and its backup should show only managed-entry changes (D-06).
- No warning noise from upstream libraries: Wurth's `${WE_3DMODEL_DIR}` paths must stay quiet (D-18).
- Nothing is pushed. Pushing stays a deliberate act by the owner (D-17).

</specifics>

<deferred>
## Deferred Ideas

- A GUI "Fix legacy model paths" action. It was considered and rejected for this phase in favour of the one-off cleanup (D-16). Revisit only if new non-conforming paths keep appearing.
- Writing path vars into every installed KiCad version's `kicad_common.json`, which was declined (D-12).
- Byte-level JSON splicing for `kicad_common.json`, which was declined in favour of the semantic check (D-13).

</deferred>

---

*Phase: 02-hardening-existing-code*
*Context gathered: 2026-10-18*
