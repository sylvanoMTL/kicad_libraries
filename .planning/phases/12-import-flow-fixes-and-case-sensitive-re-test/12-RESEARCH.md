# Phase 12: Import Flow Fixes and Case-Sensitive Re-test - Research

**Researched:** 2026-11-01
**Domain:** PySide6 desktop app (stdlib + PySide6 only): lib-table editing, QThread lifetime, `kicad_common.json` write, Qt rich-text theming, Windows per-directory case sensitivity
**Confidence:** HIGH for defect locations and the case-sensitive test mechanism (read and run this session); MEDIUM for the threading and dialog designs (recommendations, not yet built)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Library name already taken (REV-01)**
- **D-01:** **A stale tool-owned entry is repointed.** When a table holds a tool-owned entry (URI contains `${KICAD_LIB_GITHUB}/`) with the installed library's nickname, but its path points at a file or folder that no longer exists (a moved or renamed library), the table step rewrites that entry's URI to the installed library's `rel_path`. The table is backed up first, as for any table write. The Result row reads like "Updated: Atomic_Sensor_Motion now points at Custom/...". No dead entry is left behind.
- **D-02:** **A live clash only warns.** When the tool-owned entry with that nickname points at another library that still exists (e.g. `WurthElektronik/.../IC_X.kicad_sym` while `Custom/.../IC_X` was installed), the table is left unchanged. An amber Result row and a WARNING log line say e.g. "Not added: the name IC_X already points at WurthElektronik/...; KiCad still loads that library. Rename one of them." This is the 05-REVIEW WR-01 fix (`table.path_clash` WARNING, return "skipped"), which `_tables_outcome` already shows as a warning row.
- **D-03:** **"Already listed" only for a real match.** The step reports "already listed" (INFO) only when the tool-owned entry's path tail equals the expected `rel_path`. On Windows, a path that differs only by letter case counts as the same path.
- **D-04:** **The same rule applies to installs into an existing library.** Today the existing-library branch of `MainWindow._finish_post_install` only reads the tables and hints "Press Generate Tables to add it". A stale tool-owned entry under that nickname is now repointed too (D-01), and a live clash warns (D-02). A library missing from the tables entirely keeps today's "Press Generate Tables" hint: an existing library's install still never adds a new entry (Phase 5 D-17).
- **D-05:** **Hand-added entries are never edited.** An entry without the managed marker that uses the nickname keeps today's `table.external_clash` WARNING, stale or not. Only the wording becomes plainer, e.g. "Not added: IC_X is already used by an entry you added by hand (<path>); KiCad keeps loading that one."
- D-01..D-05 apply to both `sym-lib-table` and `fp-lib-table`, including the shared `Atomic_Footprints` entry.

**Waiting on kicad-cli (REV-03, REV-04)**
- **D-06:** **The Finishing state.** When Change..., opening another package, or closing the dialog (Close button, window X, Escape) would have to wait for a running build or worker, the GUI thread never calls `worker.wait()`. Instead:
  - the dialog greys out and shows a wait cursor and "Finishing the preview...";
  - the window still moves and repaints;
  - the requested action runs by itself once the last relevant worker ends (from its `finished` handler), with no second click.

  This replaces `_wait_builds()` (`import_dialog.py` ~1223, ~3153) and the waits in `_shutdown` (~3191) and `_reap` (~1276), so the package lifetime stays protected without blocking.
- **D-07:** **There is a way out.** The Finishing strip has a **Cancel** button. Cancel drops the pending action and restores the dialog's previous state (for a close, the dialog stays open). After 10 s the strip adds "kicad-cli is slow to respond (it gives up after 60 s)". kicad-cli is not killed: its existing 60 s timeout (`cli_timeout`) still ends it.
- **D-08:** **Install is disabled while a one-off build runs.** `_updating()` counts `self._oneoff`, so Install greys out and the existing "Updating..." marker shows while a one-off conflict build reads the target library. Install comes back by itself when the build ends. `_pump_builds` holds every queued build and one-off job while `is_installing()`, and `_on_install_done` / `_on_install_failed` call `_pump_builds()` so held jobs resume (the 05-REVIEW WR-03 fix).

**KiCad running / file changed (REV-05)**
- **D-09:** **The KiCad-open check runs before the dialog.** `kicad_running()` is evaluated before the confirm dialog is shown, not after the confirm. `tasklist` (up to 5 s) must not run on the GUI thread: today it runs inside `_on_scan_finished` on the post-install path. The planner picks the mechanism.
- **D-10:** **When KiCad is open, the dialog offers Retry / Change anyway / Not now.**
  - The text names the open KiCad programs (e.g. "kicad, eeschema") and says "Close KiCad, then press Retry".
  - **Retry** (the default button) checks again: if KiCad is still open, the same dialog returns; if not, the normal Yes/No confirm follows or the write goes ahead (planner's choice, as long as nothing is written without a confirm).
  - **Change anyway** writes now and logs a WARNING (D-12).
  - **Not now** writes nothing and logs today's INFO `config.declined`.

  When KiCad is not open, today's Yes/No dialog is unchanged.
- **D-11:** **The confirmed write merges into the fresh file.** After a positive confirm, `kicad_common.json` is read again (`fsutil.read_source`). Only the two path variables are set on top of the content as it is now, so settings KiCad saved while the dialog was open survive. The `_only_vars_changed` check, the backup and the atomic write run on the fresh content.
  - If the fresh file needs a different change list than the one confirmed (e.g. KiCad already holds the right path, or a value changed), the dialog is shown again with the new list.
  - If no change is needed any more, nothing is written and the INFO `config.var_ok` lines are logged.
  - Invalid JSON or a bad shape on the re-read aborts with the existing `config.bad_json` / `config.bad_shape` errors.
- **D-12:** **The warning after "Change anyway" is reworded.** It reads like "KiCad is open (kicad, eeschema); it may undo these paths when it exits. If they revert, close KiCad and press Generate Tables." It is correct after both Generate and an install. There is no startup re-check: Generate already offers the change again whenever the paths differ.
- Keep the message phrases `main_window.py` routes on (`Failed`, `Could not`, `not found`; the `Warning:` / `removed` substrings in `_on_generate`) stable, or update the routing with the text.

**Case-sensitive re-test (VER-02)**
- **D-13:** **Proof is automated tests plus one owner run.** New pytest tests create a case-sensitive temporary folder and run real `apply_plan` installs, with no mocked `os.listdir` and no live `Custom/`:
  - one install fails mid-way and rolls back: the original spelling is restored, and the twin is removed;
  - one overwrite succeeds (end state per D-14).

  Making the folder case-sensitive:
  - Windows: `fsutil file setCaseSensitiveInfo <dir> enable`, set on the empty temp folder before any child is created. It worked on the owner's machine on 2026-11-01 without admin rights.
  - Linux: `tmp_path` already is case-sensitive.
  - macOS, or when the folder cannot be made case-sensitive: the tests skip with a clear reason, added to the expected skips in `tests/README.md`.

  UAT is a single step: the owner runs these tests on Windows and sees them **pass, not skip**. Any defect the tests reveal is fixed in this phase.
- **D-14:** **A successful overwrite keeps the spelling already on disk.** When an incoming model (e.g. `Foo.step`) overwrites an existing file that differs only by case (`foo.STEP`):
  - the new bytes go into `foo.STEP`;
  - the installed footprint's model line links `foo.STEP`;
  - one file remains, with no rename.

  Other parts that already link `foo.STEP` keep working, and git on Windows (`core.ignorecase`) sees a plain content change, not a hidden case-only rename. Today `apply_plan` writes `op.path` (the incoming spelling) and keeps `listed_path` only for undo. On a case-sensitive folder that leaves two files, and on NTFS it may silently re-case the entry (research spike S7). The planner moves the write target and the footprint's model reference to the on-disk spelling, on every platform. — **Reversibility:** reversible: install logic only, no stored format.

### Claude's Discretion
- **Empty Destination (REV-02):** one helper rejects blank or whitespace Destination text (05-REVIEW WR-02 `_dest_path() -> Path | None`). It is used everywhere `self._dest_combo.currentText()` becomes a `Path`: `_finish_post_install`, `_on_generate`, `_apply_existing_selection`, `_log_existing_tables`, and the backup dialog (`main_window.py` ~215, 714, 820, 1077, 1113-1157). A blank Destination writes no table and never reads or writes the process working directory. The Result row and log say e.g. "No destination folder set; library tables not changed". Generate logs the same.
- **Help dialog and conflict rows (UI-01):**
  - `help_dialog.py`'s CSS is built from `theme.py` constants: `LINK`/`ACCENT` for headings and links, `SURFACE`/`SURFACE_HEADER` for code, pre blocks and table headers, `BORDER` for table borders, and `AMBER`/`AMBER_TINT` for the note callout (the unlisted `#F9A825` goes).
  - px font sizes become the pt scale (body at the app default or 10 pt, Mono at `MONO_PT`), and padding moves to the `SP_*` scale. 1/2/3 px borders are allowed.
  - `conflict_row.py`'s `#FFFFFF` literals become a theme constant (add a `SURFACE_BASE`/white token to `theme.py` if none fits).
  - The owner checks the result from rendered screenshots, as in Phase 11 UAT.
- The "keep the on-disk spelling" rule (D-14) applies to footprint `.kicad_mod` files in a `.pretty` folder as well as 3D models.
- The exact wording of the Finishing strip, the KiCad-open dialog and the Result rows, as long as it stays plain language with no raw field names.

### Deferred Ideas (OUT OF SCOPE)
None. The discussion stayed within phase scope. A startup check that notices path variables reverted by KiCad was offered and declined (D-12), not deferred.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REV-01 | Post-install table step says "already listed" only when the managed entry really points at that library | `_add_entry` returns `"listed"` on nickname alone (`table_generator.py:342-343`); design: compare tail to `rel_path`, repoint a stale entry, warn on a live clash (sections "REV-01" below) |
| REV-02 | Post-install table write never goes to the process working directory when Destination is empty | `Path("")` is `Path('.')`; 9 sites turn `currentText()` into a `Path` (list in "REV-02"); `BackupDialog` has the same flaw |
| REV-03 | A one-off conflict build can never overlap Install | `_updating()` omits `self._oneoff` (`import_dialog.py:2577-2584`); `_pump_builds` ignores `is_installing()` (`:2506-2518`) |
| REV-04 | The GUI thread never blocks waiting for a kicad-cli call | `_wait_builds` (`:1452`), `_shutdown` (`:3190-3191`), `_reap` (`:1276`); the Finishing-state design, the `closeEvent` ripple in `main_window.py`, and the test ripple |
| REV-05 | `kicad_common.json` write uses fresh content after the confirm, and the KiCad-running check gates it | `sync_kicad_path_vars` reads once, confirms, then writes the stale copy (`library_scanner.py:181-285`); `kicad_running()` is called after the confirm (`:268`) on the GUI thread |
| UI-01 | Help dialog and conflict rows use theme tokens only | Literal inventory for `help_dialog.py:11-59` and `conflict_row.py:35-37`; Qt rich-text behaviour measured (headings flatten if body gets a pt size) |
| VER-02 | Case-twin rollback and overwrite re-tested on a case-sensitive folder | `fsutil` mechanism verified on this machine; current behaviour on such a folder measured (rollback already correct, successful overwrite leaves two files); D-14 ripples in planner, preview, `incoming_op` and four existing tests |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python 3.10+ syntax, stdlib + PySide6 only; no new packages are needed for this phase. [VERIFIED: `.claude/CLAUDE.md` Constraints; `env` has pytest 9.1.1, pytest-qt 4.5.0, PySide6 6.12.0]
- Windows 11 primary; keep the `win32` / `darwin` / Linux branches working. Tests must not depend on a Windows-only tool without a skip path.
- "Safety: no write without a preview first. Writes to KiCad files and the repo must be atomic or backed up. Git commits need explicit confirmation." The `kicad_common.json` confirm is the one sanctioned `QMessageBox` besides About (comment at `main_window.py:1045-1047`).
- Services stay Qt-free except `settings.py`; `table_generator`, `library_scanner`, `kicad_process` are layering-checked (`tests/test_layering.py` `ALLOWED`): `table_generator` may import only `fsutil, kicad_files, models, sexpr`; `kicad_process` imports nothing from the package. Do not add Qt or upward imports to them.
- Side-effecting helpers return `list[Issue]`, routed by `Severity` (verified: `LogPanel.log_issue` uses `issue.severity.value`, `log_panel.py:42-44`). The CLAUDE.md note about substring-based severity routing is stale; no message substring routing exists, so rewording texts needs no routing change.
- Plain-language UI text, no raw KiCad field names in dialogs, Result rows, log lines or help (owner memory).
- `WurthElektronik/KiCad-Library` is read-only; tests must not read or write the live `Custom/` (`tests/README.md`).
- Worktree executors need the absolute `env/Scripts/python.exe` path; the full suite is 9000+ tests and takes 15-27 min, so per-task checks use targeted selections (owner memory and orchestrator notes).
- All edits go through GSD commands (GSD Workflow Enforcement).

## Summary

All seven requirements are real defects in the current code and every one was confirmed against the files read this session. The work splits into five independent slices that touch largely different files: (1) lib-table matching and repointing in `table_generator.py` plus the two branches of `MainWindow._finish_post_install`; (2) one `_dest_path()` helper in `main_window.py` and `BackupDialog`; (3) the import dialog's build coordinator and the new Finishing state, with a ripple into `MainWindow.closeEvent`; (4) `sync_kicad_path_vars` (re-read loop, tri-state confirm, KiCad check before the dialog) plus a worker in the main window; (5) the theme-token cleanup and the case-sensitive tests with the D-14 planner change.

Three findings change how the planner should size the work. First, **D-14 removes the only producer of case twins**: after the planner writes to the on-disk spelling, no planner path sets `listed_path` any more, so the "twin removed on rollback" proof must come from a hand-built plan (like the existing `test_rollback_restores_case_twin`) run unmocked on the case-sensitive folder, while the planner-driven tests prove the D-14 end state. Second, **D-06 is a cross-cutting change**: `ImportDialog.done()`/`closeEvent` stop being synchronous, so `MainWindow.closeEvent` (which calls `dialog.reject()` and then closes) must be changed, and about a dozen existing close tests plus one test that encodes the old blocking behaviour (`tests/test_import_dialog.py:294-297`, "`time >= 0.2`") must be rewritten. Third, the fixture `fake_sync` in `tests/test_main_window.py:63-70` and `tests/test_main_window_import.py` injects `running=lambda: []` itself, so the main window cannot also pass `running=`; the fixture must change when the KiCad check moves off the GUI thread.

I measured the machine facts the plan depends on: `fsutil file setCaseSensitiveInfo` works here without elevation, children inherit the flag, two spellings coexist, `os.replace` of a temp file onto `Foo.step` leaves `foo.STEP` untouched, and pytest's `--basetemp` cleanup deletes such folders without error. On a case-sensitive folder today, a rollback with a hand-built twin plan already ends correct (one file, original bytes), and a planner-built successful overwrite leaves **two** files for both the model and the footprint. So D-14 is a genuine fix, and the rollback half of VER-02 is expected to pass at once.

**Primary recommendation:** Build in this order: D-14 planner change plus the `incoming_op` casefold fix and the case-sensitive test file (smallest, self-contained, gives the owner's UAT); then `table_generator` REV-01 with `add_missing=False` for the existing-library branch; then REV-02; then the `sync_kicad_path_vars` rework with a main-window `TaskWorker` check; then REV-03 (3 lines) and REV-04 (the large, test-heavy slice) last; UI-01 anytime.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Match / repoint / warn on a lib-table entry | Service (`table_generator.py`, Qt-free) | `main_window.py` (routes Issues to Result row and log) | Layering test forbids Qt here; it already owns `_add_entry`, `table_info` |
| Blank Destination guard | GUI orchestrator (`main_window.py`) | `widgets/backup_dialog.py` | The combo text lives in the main window; the backup dialog has its own text field |
| Build coordinator, Install gating, Finishing state | Widget (`import_dialog.py`) | `main_window.py` (`closeEvent`, `finished` handler) | Worker lifetime is owned by the dialog (WR-04 rule) |
| KiCad-open check off the GUI thread | Main window worker (`TaskWorker`) | `kicad_process.py` (stays synchronous, Qt-free) | `tasklist` is blocking I/O; only a thread can keep the window live |
| `kicad_common.json` read-merge-write | Service (`library_scanner.sync_kicad_path_vars`) | `main_window.py` (dialog + Retry loop) | Pure file logic with callbacks; the dialog is GUI-only |
| Theme tokens | `widgets/theme.py` (plain constants) | `help_dialog.py`, `conflict_row.py` consumers | Single source of colour, per 05-UI-SPEC |
| Overwrite target spelling (D-14) | Importer planner (`planner._decide_file`) | `applier` (unchanged, still undoes twins), `import_dialog.incoming_op`, `preview` | The plan carries final paths; the applier is a dumb write loop |
| Case-sensitive folder for tests | Test fixture (`tests/`) | `tests/README.md` skip table | Test-only concern; production code never needs it |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`os`, `pathlib`, `subprocess`, `json`, `enum`) | 3.14 venv | All service logic | Project rule: stdlib only unless clearly justified |
| PySide6 | 6.12.0 | `QThread`/`TaskWorker`, `QMessageBox`, `QTextBrowser` | Already the GUI toolkit [VERIFIED: `env` pip list] |
| pytest + pytest-qt | 9.1.1 / 4.5.0 | Tests, `qtbot.waitUntil` | Already the suite [VERIFIED: `env/Scripts/python.exe -m pytest --version`] |

### Supporting
| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `fsutil.exe` (Windows, `System32`) | OS built-in | `file setCaseSensitiveInfo <dir> enable` for the VER-02 tests | Windows only, on an empty directory, before any child exists |
| `ImportDialog.TaskWorker` | repo (`import_dialog.py:257`) | Generic off-thread callable with `result`/`failed` signals | Reuse in `main_window.py` for the KiCad check |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `TaskWorker` for the KiCad check | A new `QThread` subclass in `main_window.py` like `ScanWorker` | More code for the same thing; `ScanWorker` has progress/cache logic that does not apply |
| `QThreadPool` + `QRunnable` | n/a | No precedent in repo; worker lifetime rules differ; do not introduce a third pattern |
| Nested `QEventLoop` for Retry | Return-to-caller Retry (recommended) | Nested loops make tests and re-entrancy harder |

**Installation:** none. No package is added by this phase.

**Version verification:** n/a (no new packages). Existing versions read from the venv above.

## Package Legitimacy Audit

No external packages are installed or added in this phase. `fsutil.exe` is an OS binary, not a package. Packages removed due to [SLOP] verdict: none. Packages flagged [SUS]: none.

## Architecture Patterns

### System Architecture Diagram

```
Install finishes (ImportDialog.installed)
  -> MainWindow._on_import_installed -> _PostInstall(rel paths) -> quiet rescan
  -> _on_scan_finished -> _finish_post_install
        |
        |-- _dest_path()  --None--> Result row "No destination folder set; library tables not changed", stop
        |
        |-- new-library branch ---> add_library_entries(add_missing=True)
        |-- existing-library branch -> add_library_entries(add_missing=False)  [D-04]
        |        per table, per nickname:
        |          no entry          -> add (new) | "missing" -> Generate hint (existing)
        |          managed, tail==rel_path (casefold on Windows) -> "listed" INFO
        |          managed, other tail, target still exists      -> path_clash WARNING (skip)
        |          managed, other tail, target gone              -> repoint URI (backup first) "updated"
        |          hand-added                                    -> external_clash WARNING (skip)
        |
        '-- any table written -> _sync_path_vars()
                 |
                 v
        TaskWorker(kicad_running)  (off GUI thread, D-09)
                 |  names
                 v
        sync_kicad_path_vars(running=lambda: names, confirm=callback)
                 read file -> changes? -> [refusal?] -> confirm:
                    KiCad closed: Yes/No      KiCad open: Retry | Change anyway | Not now
                 WRITE -> re-read fresh -> same change list? no -> ask again (bounded)
                       -> backup -> atomic write (+ WARNING if names and "Change anyway")
                 RETRY -> returns sentinel Issue -> MainWindow starts the check again

ImportDialog leave-requests (Change..., open_path, done/closeEvent)
        |
   any relevant worker running? --no--> run now (today's synchronous path)
        |yes
        v
   Finishing: stack disabled + wait cursor + strip(Cancel, 10 s note); builds paused
        |  each worker 'finished' -> _reap -> all idle? -> run pending action
        '-- Cancel -> drop pending, re-enable, resume queued builds
```

### Recommended Project Structure
```
kicad_lib_manager/
├── table_generator.py      # REV-01: _add_entry, add_library_entries(+repo_root, add_missing), _same_rel
├── library_scanner.py      # REV-05: sync_kicad_path_vars loop, tri-state confirm
├── main_window.py          # REV-02 _dest_path(); REV-01 branch; REV-05 check worker + 3-button dialog; closeEvent
├── widgets/
│   ├── import_dialog.py    # REV-03 (_updating/_pump_builds); REV-04 Finishing state; incoming_op casefold
│   ├── backup_dialog.py    # REV-02 blank folder
│   ├── help_dialog.py      # UI-01 CSS from tokens
│   ├── conflict_row.py     # UI-01 #FFFFFF -> token
│   └── theme.py            # + SURFACE_BASE
├── importer/planner.py     # D-14 in _decide_file overwrite branch
tests/
├── casefixtures.py         # NEW: case_sensitive_dir(), shared with test_commit_plan's probe
├── test_case_sensitive_install.py   # NEW: the VER-02 tests (the owner's UAT selection)
└── README.md               # expected-skips row
```

### Pattern 1: Entry matching (REV-01)
**What:** One helper decides the outcome for a nickname, used by both the new-library and existing-library branches.
**When to use:** every `_add_entry` call.
**Verified current code (quote):** `table_generator.py:339-343`
```python
        for entry in table.entries:
            if entry.name != nickname:
                continue
            if _is_managed(entry):
                return "listed"
```
**Recommended outcome precedence for all entries named `nickname`** (the current loop returns on the first one):
1. any managed entry with `_same_rel(_tail(entry), rel_path)` -> `"listed"` (INFO `table.already_listed`)
2. else any managed entry whose `(repo_root / tail)` exists -> `table.path_clash` WARNING, `"skipped"` (D-02)
3. else any non-managed entry -> `table.external_clash` WARNING, `"skipped"` (D-05; text reworded)
4. else a managed entry (all stale) -> repoint the first one, `"updated"` (D-01)
5. no entry -> `"added"` (new-library branch) or `"missing"` (existing branch, `add_missing=False`, D-04)

```python
# Source: this phase's recommendation; Edit/quote/apply_edits are existing sexpr helpers (sexpr.py:177-200)
def _same_rel(a: str, b: str, *, fold: bool | None = None) -> bool:
    """Equal repo-relative paths: slash direction and a trailing slash never matter; case matters only on Windows (D-03)."""
    fold = (os.name == "nt") if fold is None else fold
    norm = lambda t: (t.strip().replace("\\", "/").rstrip("/")).casefold() if fold else t.strip().replace("\\", "/").rstrip("/")
    return norm(a) == norm(b)

node = entry.value_nodes["uri"]                       # LibEntry.value_nodes (kicad_files.py:59, filled :580-590)
new_text = apply_edits(text, [Edit(node.start, node.end, quote(f"{_MANAGED_MARKER}{rel_path}"))])
```
`add_library_entries` needs the repo root to test "still exists": add a keyword `repo_root: Path` (Qt-free, layering-safe). Callers: `MainWindow._finish_post_install` (two branches) and `tests/test_table_add_entries.py`. Use `fold` as a keyword so the Windows rule is testable on any OS (the repo already does this with `platform=` in `find_kicad_footprint_dir`).

New Issue codes (keep `Issue(severity, code, text)` shape): `table.entry_updated` SUCCESS, `table.path_clash` WARNING, `table.not_listed` INFO (existing branch, one per missing nickname, carries the nickname so the caller builds the hint). `_tables_outcome` (`main_window.py:880-893`) must learn the new codes: its `parts` filter today lists only `table.entry_added`, `table.already_listed`, `table.external_clash`, and it returns early only for `table.entries_added`. `add_library_entries`' summary block (`:395-406`) must also count `"updated"` and not call a mixed result "entries_added" (it requires all outcomes to be `"added"`).

### Pattern 2: Deferred leave-requests with a Finishing state (REV-04)
**What:** One mechanism for Change..., `open_path`, and `done`/`closeEvent`. Idle -> run now (so every existing idle test keeps its synchronous behaviour); busy -> enter Finishing; run from the last worker's `finished` handler.
**Key design points (all derived from code read this session):**
- **"Busy" predicate:** `[w for w in self._workers if w is not exclude and w.isRunning()]`. `self._workers` is never pruned (`_spawn`, `import_dialog.py:1262-1267`), so it is the complete list. Use the `exclude=worker` form inside `_reap`, because the Qt docs say `finished()` is emitted "right before it finishes executing" and "the thread may still run for arbitrary amount of time after the finished() signal is emitted", so the reaped worker itself may still report `isRunning()`. Every worker eventually triggers its own `_reap`, so the last one always re-checks.
- **Scope per action:** Change/`open_path` wait for `_building` and `_oneoff` only (that is today's `_wait_builds` scope, and the only workers that read the package under `build_plan`). Close waits for all running workers (today's `_shutdown` scope).
- **Builds must pause while Finishing:** `_pump_builds` (`:2506`) and `_request_rebuild` (`:2472`) must not start a new `build_plan` while `self._finishing` is set, otherwise a queued rebuild restarts a 60 s kicad-cli call and the wait never ends. Do not clear `_queued`/`_oneoff_jobs` on entry; Cancel then calls `_pump_builds()` to resume, and the real action's `_reset_edit_state` (`:1458`) clears them on completion.
- **Do not set `_closing` on entry.** Handlers such as `_on_opened` (`:1292-1299`) close the package and drop the result when `_closing` is set; Cancel would then leave a Start page stuck on "Reading package...". Set `_closing` only in the real `_shutdown`.
- **One-off results while Finishing:** `_on_oneoff_done` (`:2528`) calls `on_result` which opens a `ContentViewDialog`; skip `on_result` while `_finishing`.
- **`_reap` rule:** never `deleteLater` a finished worker (crash recorded in the docstring at `:1270-1275`; Qt docs: "Deleting a running QThread (i.e. isFinished() returns false) will result in a program crash. ... Wait for the finished() signal before deleting"). The Finishing state satisfies this because the pending action (which lets the main window `deleteLater` the dialog) runs only after every worker's `finished` has been handled. The existing `worker.wait()` in `_reap` joins a thread whose `run()` already returned (it cannot wait for kicad-cli). **Recommendation:** keep a bounded `worker.wait(2000)` there with a one-line comment. Removing it fully, as D-06 words it, relies on Qt's QThread destructor joining a thread that is still in its finish phase; I believe it does but did not verify it this session [ASSUMED], and a crash here is exactly what the docstring warns about. Flag to the owner if the planner removes it entirely.
- **Close during Finishing:** a later close request upgrades a pending Change/open to a pending close ("close wins"); Escape, a second X and the Close button are otherwise no-ops; only the strip's Cancel cancels.
- **`done()` must not call `super().done()` from a lambda:** zero-argument `super()` fails in a lambda. Write `_finish_close(r)` as a method and defer a bound method.
- **`closeEvent` (`:3214-3220`):** when it defers, call `event.ignore()` and return without `super().closeEvent(event)`; `super().closeEvent` would call `reject()` -> `done()` again.
- **Cursor and enabling:** disable `self._stack` only (the strip lives in `outer` outside the stack so Cancel stays enabled). Prefer `QGuiApplication.setOverrideCursor(WaitCursor)` paired with `restoreOverrideCursor()` in one `_end_finishing()` that every exit path calls (Cancel, completion, `_shutdown`), because child line edits set their own I-beam cursor and ignore a cursor set on the dialog. A leaked override cursor persists across tests: assert `QGuiApplication.overrideCursor() is None` in the Finishing tests.
- **10 s note:** a single-shot `QTimer` driven by a module constant (`_SLOW_NOTE_MS = 10_000`) so tests set it to a few ms with `monkeypatch`.

### Pattern 3: KiCad check before the confirm, Retry by return (REV-05)
**What:** The main window runs `kicad_running` on a `TaskWorker`, then calls `sync_kicad_path_vars(REPO_ROOT, running=lambda: names, confirm=...)`. `sync_kicad_path_vars` stays synchronous and Qt-free; all 25+ tests in `tests/test_kicad_config.py` keep working if the one-argument `confirm` and `running` contracts are kept (bool return still accepted).
- Add a tri-state return from `confirm` (e.g. a small `enum` in `library_scanner.py`: write / decline / retry; plain `True`/`False` still mean write/decline). Retry makes `sync_kicad_path_vars` return before any backup with an INFO Issue whose code the main window recognises (`config.retry`); the main window then starts the check again and shows the dialog again (Retry never writes).
- After the Retry loop, the normal Yes/No confirm follows when KiCad is closed (recommended, simplest, and nothing is written without a confirm).
- Replace the single read-confirm-write with a bounded loop (3 passes): read -> parse -> `desired` changes -> refusal check -> `confirm(changes)` -> **re-read** with `fsutil.read_source` -> recompute; same list -> build `new_config` from the **fresh** parse and write; different non-empty list -> ask again with the new list; empty list -> log the INFO `config.var_ok` lines and write nothing (D-11). Re-evaluate `_path_var_refusal` on the fresh `old_vars`. After 3 passes without a stable list, return a WARNING ("kicad_common.json keeps changing; nothing was written") rather than loop forever.
- `running()` is called before `confirm` (D-09). The WARNING `config.kicad_running` is emitted only when names are non-empty at write time, which, with the D-10 dialog, means "Change anyway". Reword it per D-12 and keep it a WARNING; `tests/test_kicad_config.py:328-329` asserts the old text and must change.
- Dialog: `QMessageBox.question` accepts only standard buttons and cannot offer three custom ones with a default. Build a `QMessageBox` instance with `addButton("Retry", AcceptRole)` (default), `"Change anyway"`, `"Not now"`, and put it behind one method (e.g. `MainWindow._ask_kicad_open(changes, names)`) that tests monkeypatch, just as `fake_question` replaces `QMessageBox.question` at `tests/test_main_window.py:88-96`.

**Where the off-thread check lives (options and recommendation):**
1. **Recommended:** reuse `TaskWorker` from `import_dialog.py:257` inside `MainWindow` (it already imports `ImportDialog`). The dialog's own `_start_kicad_check` (`import_dialog.py:3107-3113`) is the in-repo precedent: `self._spawn(lambda progress: core.kicad_running())` with a `result` handler and a no-op `failed` handler. Keep the finished workers referenced in a list on the window (never `deleteLater`; same rule as `_reap`). Test seam: look up `kicad_running` as a module attribute of `main_window` so a fixture can monkeypatch it.
2. `ScanWorker`-style dedicated `QThread` in `main_window.py`: no benefit over option 1.
3. `ImportCore.kicad_running`: the dialog may already be closed on the post-install path, so it cannot own this.
- Closing the main window during the 5 s `tasklist`: do not `wait()`; `event.ignore()` and re-issue `close()` from the worker's `finished` (the same pattern as the dialog). The existing `closeEvent` already waits on the scan worker (`:1195-1196`), out of scope here.
- Two entry points start the sync (`_on_generate` end and `_finish_post_install`); guard re-entry with a `_path_var_busy` flag (a second Generate click while the check runs must not start a second dialog).
- Ordering ripple in `_on_generate` (`:1095-1109`): the history update after `_sync_path_vars()` still works because it does not depend on the sync result.

### Pattern 4: D-14 keep the on-disk spelling
**Verified current code (quote):** `planner.py:742-744`
```python
    if resolution.action == "overwrite":
        # The write replaces the file on disk under whatever spelling it has now (Pitfall 12)
        return _Decision(spec.default, op=spec.make_op(spec.default, existing, digest), conflict=resolved)
```
and the skip branch at `:745-746` already does the right thing: `return _Decision(spec.identity_of(hit), conflict=resolved, kept=True)`.
**Recommended change:** in the overwrite branch use `name = spec.identity_of(hit)` for both the `_Decision` name and `make_op(name, existing, digest)`. Both `make_model_op` (`:1218-1225`) and `make_fp_op` (`:1308-1315`) set `listed_path` only when `existing.name != name`, so with `name == hit` they set `None` and `op.path` becomes the on-disk spelling. The footprint's model line (`model_link = model_dec.name`, `:1245`, used at `:1267`), the symbol's Footprint field and filters (`linked = final_fps[0]`, `:1378-1380`), `plan.model_file` (`:1587`) and the gate context (`:1502`) all derive from the decision name, so they follow with no further change. The footprint is re-rendered with the on-disk name (`render_fp(index, decision.name)`), so a case-twin `fp.kicad_mod` yields a footprint named `fp` and a symbol link `...:fp`.

Ripples the planner must handle (found by reading, not by running):
- `import_dialog.incoming_op` footprint branch (`:145-147`) compares `op.path.name == f"{conflict.name}.kicad_mod"` exactly; with a case twin `conflict.name` is `FP` and the op is `fp.kicad_mod`, so the conflict view would say "not part of the plan". Compare casefolded. (The model branch already compares to `plan.model_file`, which follows.)
- `fp_renames` / `model_renames` (`planner.py:1551-1560`) will add a `Rename` row for a case-only change (`FP -> fp`, `PART.step -> part.STEP`), shown by `preview._renames_section` with details "footprint" / "model file". That is accurate but could read as a user rename; decide on wording or accept.
- `preview._file_rows` slot lookup (`preview.py:175-186`) uses `models_dir / plan.model_file`, now identical to `op.path`; the `listed_path` fallback in `by_path` (`:149-150`) becomes dead for planner plans but is harmless. Keep `listed_path` handling in `applier`, `content.py:122`, `commit_plan.py:121` and `preview.py:149` (defence in depth, and the hand-built twin test needs `applier`'s twin handling to stay).
- Existing tests that encode the old behaviour and must change: `tests/test_install_plan.py:1593-1601` (`("PART.step", "part.STEP")`, `plan.model_file == "PART.step"`), `:1604-1612` (`os.listdir == ["PART.step"]`), and the `case-twin` parametrisation at `:1574-1590` (`op.path.name == "FP.kicad_mod"`).

### Anti-Patterns to Avoid
- **`worker.wait()` anywhere on the GUI thread for a build/one-off/open worker.** That is the defect.
- **Setting `_closing = True` to "stop the handlers" during Finishing.** Breaks Cancel (see Pattern 2).
- **Lambdas that call zero-argument `super()`** in deferred actions.
- **Starting the KiCad check inside `sync_kicad_path_vars`** (it runs on the GUI thread there). Pass the names in.
- **Mocking `os.listdir` in the new VER-02 tests.** D-13 forbids it; the existing mocked unit tests (`tests/test_install_apply.py:810-833`) stay as they are.
- **Treating "path exists" as case-sensitive on Windows** for the stale test: `Path.exists()` is case-insensitive there, which is the desired "same path" behaviour (D-03).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Editing a table entry's URI | String `replace` on the file text | `Edit(node.start, node.end, quote(uri))` from `sexpr.py` + `apply_edits`, node from `LibEntry.value_nodes["uri"]` | Preserves every other byte (CRLF, BOM, hand edits); the module's whole contract |
| Atomic write + backup of tables / `kicad_common.json` | New temp-file code | `fsutil.backup_file`, `fsutil.atomic_write_text/bytes`, `fsutil.read_source` | Already handles locks, read-only, BOM, EOL |
| Off-thread call | New thread class or `threading.Thread` | `TaskWorker` (`import_dialog.py:257`) | Signals marshalled to the GUI thread; the lifetime rules are already documented |
| Windows process list | A new `tasklist` wrapper | `kicad_process.kicad_running()` (called on the worker) | Already no-shell, 5 s timeout, silent on failure |
| Case-insensitive path compare | `str.lower()` everywhere | One `_same_rel` helper with a `fold` keyword | One place for the Windows rule and one test seam |
| Making a case-sensitive folder | Mocking the filesystem | `fsutil file setCaseSensitiveInfo` on Windows + a real probe | The point of VER-02 is real behaviour |
| HTML/CSS for the help page | Hex literals | CSS strings assembled from `theme.py` constants | UI-01 itself |

**Key insight:** every piece of file mechanics this phase needs already exists in `fsutil`, `sexpr` and `TaskWorker`; the risk is in sequencing (async hops, deferred actions) and in tests that assumed synchronous behaviour, not in missing primitives.

## Runtime State Inventory

This is not a rename/migration phase. It changes install logic and GUI code; nothing renames a stored string.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None. Only the saved scan cache and QSettings exist; no key is renamed. D-14 changes new installs only and leaves existing files untouched. | none |
| Live service config | None. | none |
| OS-registered state | None. | none |
| Secrets/env vars | `KICAD_LIB_GITHUB`, `CUSTOM_3DMODEL_DIR` are still written by the same code to the same keys. | none |
| Build artifacts | None. | none |

## Common Pitfalls

### Pitfall 1: The test fixture injects `running=`
**What goes wrong:** `tests/test_main_window.py:63-70` defines `fake_sync(repo_root, **kwargs)` that calls `sync_kicad_path_vars(repo_root, **kwargs, config_base=..., backup_root=..., running=lambda: [])`. Its comment says a caller passing `running` makes a duplicate-keyword `TypeError` on purpose. Passing `running=lambda: names` from the main window then raises.
**How to avoid:** change the fixture to `kwargs.setdefault("running", lambda: [])` and monkeypatch `main_window.kicad_running` to `lambda: []` in `make_window`. Same fixture shape exists in `tests/test_main_window_import.py` (fixture around `:100-112`).
**Warning signs:** `TypeError: ... got multiple values for keyword argument 'running'`.

### Pitfall 2: Async sync breaks "call then assert" tests
**What goes wrong:** about 6 Generate tests (`tests/test_main_window.py`) and the post-install tests assert on the config file / log right after `w._on_generate()` or after the scan worker ended.
**How to avoid:** expose an observable "sync idle" condition (e.g. `w._path_var_busy` false) and add one helper `settle(qtbot, w)` that every such test calls; apply it in the same plan as the main-window change.

### Pitfall 3: Dialog tests that close with a running worker
**What goes wrong:** ~25 `dialog.reject()` / `dialog.close()` calls in `tests/test_import_dialog.py`. Idle closes stay synchronous. Closes with a running worker (e.g. `:294-297` build gate; `test_close_during_probe_cancels_and_closes` at `:3605-3620`; the parametrised `test_close_button_enabled_while_probing` at `:3623-3638`) now return at once with the dialog still visible. `:294-297` asserts the old blocking (`time.monotonic() - started >= 0.2`, events `["build_end", "close"]`) and must be rewritten as "returns immediately, then closes after the gate opens".
**Teardown risk:** `qtbot` closes registered widgets at teardown; if a worker is still running then, `close()` now defers and the widget can be destroyed under a live `QThread` (fatal). The `gates` fixture releases gates at its own teardown, which runs before `qtbot`'s, but a just-released worker may still be running. **Mitigation:** give tests a blocking join helper (for example a `finish_workers`-style call plus `for w in dialog._workers: w.wait()`) in a fixture finaliser registered after `qtbot.addWidget`, and keep a private forced `_join_workers()` that is used only by tests and by `_shutdown` once no worker `isRunning()`. Run the whole `tests/test_import_dialog.py` once before declaring the plan done; a crash shows up as a process abort, not a failure.

### Pitfall 4: Headings flatten when the help body gets a pt size
**What goes wrong:** measured with `QTextBrowser` offscreen: with no CSS, `<h2>`/`<h3>` report point size 0.0 (relative to the app font); with `body{font-size:10pt}` all of h2, h3, p, pre report exactly 10.0. With `body{font-size:14px}` (today) headings are unaffected. Replacing the px body size by a pt size silently removes the visual hierarchy.
**How to avoid:** set explicit sizes: `h2 { font-size: <DISPLAY_PT>pt }`, `h3 { font-size: <HEADING_PT>pt }`; leave body at the app default (omit `font-size`) or `HEADING_PT`, `code`/`pre` at `MONO_PT` with `font-family: MONO_FAMILY`. `font-size: Npt` and `line-height: 1.55` (becomes 155 %) are honoured by Qt's rich text engine [VERIFIED: offscreen probe this session]. `border-radius` is not supported by Qt rich text (ignored); drop it.

### Pitfall 5: A stale-looking entry is actually fine on a different checkout
**What goes wrong:** the stale test resolves `${KICAD_LIB_GITHUB}/<tail>` against `repo_root` (the app's checkout). If the user keeps tables for another checkout, an entry may look stale here.
**How to avoid:** the post-install write only runs when the Destination is the user's own table folder and KiCad's `KICAD_LIB_GITHUB` refuses a different checkout elsewhere (`_path_var_refusal`); accept the app's `REPO_ROOT` as the reference (use `plan.layout.repo_root`/`REPO_ROOT`, the same root the install used) and say so in the code comment.

### Pitfall 6: Two same-nickname entries
**What goes wrong:** the current loop returns at the first entry named `nickname`. A table can hold a stale managed entry and a live one.
**How to avoid:** apply the precedence in Pattern 1 across all matches before deciding.

### Pitfall 7: `fsutil` set after children exist, or on a non-empty folder
**What goes wrong:** the flag must be set on an empty directory; `tmp_path` itself already exists and pytest may have put things beside it.
**How to avoid:** create a fresh subfolder (`tmp_path / "cs"`), enable the flag on it, then build the layout inside it. Verified: children inherit the flag, and an enabled folder listed `['Foo.step', 'foo.STEP']` together.

### Pitfall 8: Windows PATH for `fsutil`
**How to avoid:** build the path like `kicad_process.py:24` does: `Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "fsutil.exe"`, with `timeout` and `CREATE_NO_WINDOW`; skip (not fail) on `OSError`, a non-zero exit, or a failed probe, with the reason in the skip message.

## Code Examples

### Case-sensitive folder fixture (VER-02) — measured working on this machine
```python
# tests/casefixtures.py (new). Verified behaviour: fsutil rc 0, children inherit, probe works,
# pytest --basetemp cleanup of such folders succeeded on a second run.
import os, subprocess, sys
from pathlib import Path
import pytest

def case_sensitive_dir(path: Path) -> Path:
    path.mkdir()                                   # must be new and empty
    if sys.platform == "win32":
        exe = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "fsutil.exe"
        try:
            r = subprocess.run([str(exe), "file", "setCaseSensitiveInfo", str(path), "enable"],
                               capture_output=True, text=True, timeout=30,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except (OSError, subprocess.SubprocessError) as e:
            pytest.skip(f"could not make a case-sensitive folder: fsutil did not run ({e})")
        if r.returncode != 0:
            pytest.skip(f"could not make a case-sensitive folder: {(r.stdout + r.stderr).strip()}")
    (path / "CaseProbe").write_bytes(b"x")
    sensitive = not (path / "caseprobe").exists()
    (path / "CaseProbe").unlink()
    if not sensitive:
        pytest.skip("could not make a case-sensitive folder: this volume ignores letter case")
    return path
```
macOS (usually case-insensitive) skips through the probe; Linux passes through the probe with no `fsutil`.

### Measured baseline on a case-sensitive folder (before any change)
Script run this session against the current code, with the tests' own helpers (`tests/test_install_apply.py::_hand_plan`, `tests/test_install_plan.py::_target_layout/_put_model/_put_footprint/_vendor`):
```
rollback, hand-built twin plan, 2nd write failed : ok=False, models dir -> ['foo.STEP']   (twin removed, correct)
planner overwrite (model part.STEP, footprint fp.kicad_mod), apply succeeded:
    op model PART.step listed part.STEP ; op footprint FP.kicad_mod listed fp.kicad_mod
    after: models ['PART.step', 'part.STEP']   pretty ['FP.kicad_mod', 'fp.kicad_mod']   <- two files each (the D-14 defect)
```
So tests T1/T2 below pass today and T3/T4 fail today.

### Recommended VER-02 test matrix (new `tests/test_case_sensitive_install.py`)
| # | Plan source | Setup | Assert |
|---|-------------|-------|--------|
| T1 rollback, hand-built twin | `_hand_plan` + `FileOp(path=Foo.step, listed_path=foo.STEP)` as in `tests/test_install_apply.py:695-714`, built inside the case-sensitive dir | inject failure with the existing `_flaky_writes(monkeypatch, fail_on=2)` seam (fault injection only, no `os.listdir` mock) | `os.listdir(models) == ["foo.STEP"]`, original bytes, `snapshot(custom) == before`, backup copy intact. Proves `applier._drop_twin` on a real listing. |
| T2 rollback, planner-built | `build_plan` with `Resolution("overwrite")` on a model case twin | same failure injection | listing and bytes unchanged; the recorded forward write target is `part.STEP`, not `PART.step` (D-14) |
| T3 overwrite succeeds, model | as T2 without failure | — | `listdir == ["part.STEP"]`, bytes == new, footprint model line `${CUSTOM_3DMODEL_DIR}/part.STEP`, `result.ok`, `verify_install` clean |
| T4 overwrite succeeds, footprint | footprint twin `fp.kicad_mod` | — | `listdir(pretty) == ["fp.kicad_mod"]`, symbol Footprint field `Atomic_Footprints:fp` (use `footprint_library_for`) |
Use `write_synthetic_custom(root, naming="atomic")` or `_target_layout(root, V6)` with `root = case_sensitive_dir(tmp_path / "cs")`. Keep the NTFS-only test `tests/test_install_plan.py:1604-1612`, updated to expect `["part.STEP"]`.

**The owner's UAT (VER-02), single step:** from the repo root, `.\env\Scripts\python.exe -m pytest tests/test_case_sensitive_install.py -v -rs`, expect every test listed `PASSED` and the summary line to show no `skipped`. Name the file in the plan's UAT text exactly; if the planner picks another file name, the command changes with it.

### Blank-Destination helper (REV-02)
```python
# Source: 05-REVIEW WR-02 fix, adapted
def _dest_path(self) -> Path | None:
    text = self._dest_combo.currentText().strip()
    return Path(text) if text else None
```
Current sites that must use it [VERIFIED: grep of `main_window.py`]: `:215` (`Path(self._dest_combo.currentText())`), `:714` (`_apply_existing_selection`), `:820` (`_finish_post_install`), `:1077` (`_on_generate`, uses `dest.exists()`), `:1113` (`_on_rescan`), `:1153` (`_on_browse_dest`), `:1157` (`_on_dest_changed`); `:1117` passes the raw string to `BackupDialog`. `_log_existing_tables(dest: Path)` (`:415`) must accept `None`. `BackupDialog` has the same flaw in its own field: `Path(self._folder_edit.text())` at `backup_dialog.py:66` and `:90`; strip and treat blank as "no folder". The Result-row text for a blank destination (suggested: "No destination folder set; library tables not changed") is a discretion item; the existing missing-folder case sets ERROR (`:824-826`, test `tests/test_main_window_import.py:888`), a blank one is arguably a WARNING, planner's call.

### Install gating (REV-03) — three-line core
```python
# import_dialog.py _updating (:2577-2584) add: or self._oneoff is not None
# _pump_builds (:2506) guard becomes:
if self._closing or self._finishing or self.is_installing() or self._building is not None or self._oneoff is not None:
    return
# _on_install_done / _on_install_failed: call self._pump_builds() after clearing _install_worker
```
On a successful install, clear `_oneoff_jobs` (and `_queued`) instead of resuming them: a held conflict-view job for a plan that was just installed would open a stale content view over the Result page. Resume only after a failure (the retry path already calls `_request_rebuild()`).

### UI-01 literal inventory
`help_dialog.py:11-59` CSS literals [VERIFIED by reading], with the token each maps to:
| Literal | Where | Token |
|---------|-------|-------|
| `#0057A0` (h2 color) | `h2` | `LINK` |
| `#0078D4` (h2 border, pre border-left, a color) | `h2`, `pre`, `a` | `ACCENT` |
| `#EEF1F5` (code, th) | `code`, `th` | `SURFACE_HEADER` |
| `#F5F7FA` (pre) | `pre` | `SURFACE` |
| `#FFF8E1`, `#F9A825` (.hint) | `.hint` | `AMBER_TINT`, `AMBER` (the callout border) |
| `#CCC` (td border) | `th, td` | `BORDER` (`#C8C8C8`) |
| `#222`, `#333` (body, h3 text) | `body`, `h3` | no text token exists: omit `color:` and inherit the platform palette (05-UI-SPEC: surfaces come from the platform palette) |
| `14px`, `13px`, `13px` | `body`, `code`, `pre` | body: omit or `HEADING_PT`pt; code/pre: `MONO_PT`pt + `MONO_FAMILY` |
| `padding: 2px 5px / 10px 14px / 6px 12px / 8px 12px`, `margin: 16px 20px` | various | `SP_XS/SP_SM/SP_MD` values |
`conflict_row.py:35` and `:37` hold `#FFFFFF` (button fill; checked text). Add `SURFACE_BASE = "#FFFFFF"` to `theme.py:13` area (no existing token is white; `PRIMARY_BUTTON_QSS` uses the word `white`, inside `theme.py` itself, which is the token module). `conflict_row.py` also has `padding: 4px {_BUTTON_PAD}px` with `_BUTTON_PAD = 12` (off the 4/8/16 scale); the requirement text lists only colours, `#FFFFFF` and px font sizes, so changing it is optional. The CSS is not an f-string today; build it from a list of rule strings joined with newlines (as `theme.py:27-36` does) rather than a brace-doubled f-string.

Regression test for UI-01 (new, cheap): assert `re.findall(r"#[0-9A-Fa-f]{3,8}\b", CSS)` is empty when the CSS is built from tokens (or every hit is a theme constant), assert no `\d+px` follows `font-size`, and assert `"#FFFFFF"` is absent from `conflict_row.py` source. `tests/test_help_dialog.py` already imports `AMBER, ACCENT`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Blocking `QThread.wait()` on the GUI thread | Deferred action from `finished` + visible Finishing state | This phase | Window stays live for up to 60 s of kicad-cli |
| Overwrite writes the incoming spelling | Overwrite keeps the on-disk spelling | This phase (D-14) | No twin on case-sensitive folders, no hidden case-only rename in git |
| Read once, confirm, write stale copy | Re-read after confirm, bounded retry loop | This phase | KiCad's own settings saved meanwhile survive |

**Deprecated/outdated:** the `kicad_running` warning text "Close KiCad and press Generate again" (wrong after an install); the CLAUDE.md remark that severity is routed by message substrings (routing is by `Issue.severity`).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Qt's `QThread` destructor joins a thread that is still in its finish phase, so removing `_reap`'s `wait()` entirely would be safe | Pattern 2 | A crash (access violation) on dialog destruction; mitigated by the recommendation to keep a bounded wait there |
| A2 | `fsutil file setCaseSensitiveInfo` works without elevation on other Windows setups the owner may use | Environment / tests | Tests skip with a message instead of passing; owner UAT would then need a different machine |
| A3 | Returning to the main window for Retry (re-run the check, re-enter `sync_kicad_path_vars`) is preferable to a nested event loop | Pattern 3 | Another mechanism would still meet D-10; only plan structure changes |
| A4 | The post-install write always compares against the app's `REPO_ROOT` checkout when deciding "stale" | Pitfall 5 | A table kept for another checkout could have a live entry repointed; low, because `_path_var_refusal` already assumes one checkout |
| A5 | Cancelling a Finishing close restores the dialog fully by resuming `_pump_builds()` | Pattern 2 | A dirty preview could stay out of date; fix is one `_request_rebuild()` on Cancel |
| A6 | Owner prefers "close wins" over a pending Change when X is pressed during Finishing | Pattern 2 | Cosmetic; CONTEXT does not specify |

## Open Questions

1. **Keep a bounded wait in `_reap`?**
   - What we know: D-06 says the Finishing state "replaces ... the waits in `_shutdown` and `_reap`". `_reap`'s wait only joins a thread whose `run()` has returned, but Qt warns the thread "may still run for arbitrary amount of time" after `finished()`.
   - What's unclear: whether the owner means that join too.
   - Recommendation: replace the unbounded waits in `_wait_builds` and `_shutdown`, keep `worker.wait(2000)` in `_reap`, and say so in the plan.
2. **What does Escape do while Finishing?** Recommendation: nothing (Cancel is the only way out), close-wins for the X button.
3. **Blank-Destination severity in the Result row:** WARNING (recommended) vs ERROR (matches the missing-folder row).
4. **Should the `Rename` row for a case-only D-14 change be suppressed or reworded?** Recommendation: keep it (it explains why the link spelling differs from the vendor's) and let the UAT screenshot decide.
5. **After Retry finds KiCad closed: Yes/No confirm (recommended) or write at once?** CONTEXT leaves it to the planner; the confirm path is the only one that cannot write without a confirm.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Repo venv `env/Scripts/python.exe` | all tests | ✓ | CPython 3.14, pytest 9.1.1, pytest-qt 4.5.0, PySide6 6.12.0 | — |
| `fsutil.exe` case-sensitive flag | VER-02 tests | ✓ (ran this session: rc 0, flag enabled, child inherits) | Windows 11 10.0.26200 | tests skip with a stated reason |
| `tasklist` | REV-05 real check | ✓ (used by `kicad_process`) | OS | tests fake `kicad_running` |
| Real KiCad / kicad-cli | not needed for new tests (fakes via `FakeCli`/`core_with`) | n/a | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none on this machine; macOS or a volume that rejects the flag falls back to a skip.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-qt 4.5.0 (`qt_api = "pyside6"`) |
| Config file | `pyproject.toml` (`testpaths = ["tests"]`, `addopts = "-ra --strict-markers"`) |
| Quick run command | `env/Scripts/python.exe -m pytest <files> -q` from the repo root (no xdist) |
| Full suite command | `env/Scripts/python.exe -m pytest -q` (15-27 min; phase gate only; `-m "not wurth"` is ~15-20 min) |

Measured this session: `tests/test_table_add_entries.py tests/test_kicad_config.py tests/test_help_dialog.py tests/test_kicad_process.py` = 83 passed in 5 s; `tests/test_main_window.py tests/test_main_window_import.py tests/test_install_apply.py` = 155 passed in 15 s; `tests/test_import_dialog.py -k "close or change or oneoff or conflict"` = 38 passed in 41 s.

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REV-01 | listed only on a real match; stale repointed with backup; live clash warns; hand entry untouched; existing-library branch repoints but never adds; Windows case-insensitive match | unit + window | `env/Scripts/python.exe -m pytest tests/test_table_add_entries.py tests/test_main_window_import.py -q` | ✅ extend both |
| REV-02 | blank / whitespace Destination writes nothing, never touches cwd (use `monkeypatch.chdir(tmp_path)` and assert no table appears); Generate logs the same; backup dialog blank folder | window | `env/Scripts/python.exe -m pytest tests/test_main_window.py tests/test_main_window_import.py -q` | ✅ extend; backup dialog test ❌ Wave 0 |
| REV-03 | Install disabled while a one-off runs; one-off jobs held during install and resumed after failure; cleared after success | dialog | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py -q -k "oneoff or conflict or install"` | ✅ extend |
| REV-04 | Change/open/close return immediately while a gated build runs, strip + wait cursor shown, action runs by itself, Cancel restores, 10 s note (patched constant), main-window close defers, no `worker.wait` on the GUI thread | dialog + window | `env/Scripts/python.exe -m pytest tests/test_import_dialog.py tests/test_main_window_import.py -q -k "finishing or close or change"` | ✅ rewrite `:294-297` test, add new |
| REV-05 | check before dialog, Retry loop, Change anyway warning text, Not now, re-read merge keeps KiCad's newer settings, changed list asks again, no change -> `config.var_ok` only, bad JSON on re-read aborts, bounded loop | unit + window | `env/Scripts/python.exe -m pytest tests/test_kicad_config.py tests/test_main_window.py tests/test_kicad_process.py -q` | ✅ extend; fixture change (Pitfall 1) |
| UI-01 | no hex literal / px font size in help CSS, no `#FFFFFF` in `conflict_row.py`; headings keep distinct pt sizes | unit | `env/Scripts/python.exe -m pytest tests/test_help_dialog.py -q` | ✅ extend; token test ❌ Wave 0 |
| VER-02 | T1-T4 on a real case-sensitive folder; D-14 plan tests; NTFS test updated | integration | `env/Scripts/python.exe -m pytest tests/test_case_sensitive_install.py tests/test_install_plan.py tests/test_install_apply.py -q -k "case or twin or rollback"` | ❌ Wave 0: new file + `tests/casefixtures.py` |

### Sampling Rate
- **Per task commit:** the single targeted file(s) above for the slice touched (5-45 s each).
- **Per wave merge:** all of `tests/test_table_add_entries.py tests/test_kicad_config.py tests/test_help_dialog.py tests/test_main_window.py tests/test_main_window_import.py tests/test_install_apply.py tests/test_install_plan.py tests/test_case_sensitive_install.py` (about 1 min) plus `tests/test_import_dialog.py` once after the REV-04 wave (it is 5254 lines; run it in the background, it exceeds the 600 s foreground limit only if the whole file is slow, so measure first).
- **Phase gate:** full suite green (`-m "not wurth"` acceptable for iteration; run the full one once, in the background, before `/gsd-verify-work`).

### Wave 0 Gaps
- [ ] `tests/casefixtures.py` — `case_sensitive_dir()`; also let `tests/test_commit_plan.py:196-200` reuse the probe if the planner wants one definition
- [ ] `tests/test_case_sensitive_install.py` — T1-T4
- [ ] a `settle(qtbot, window)` helper and the `fake_sync` / `kicad_running` fixture change in both main-window test modules
- [ ] a join-workers fixture finaliser for dialog tests (Pitfall 3)
- [ ] `tests/README.md` expected-skips row: condition "case-sensitive folder cannot be made", message `could not make a case-sensitive folder: ...`, why, how to enable (`fsutil file setCaseSensitiveInfo` works without admin on Windows 11 builds that support it). The "exactly four expected skips on the workstation" sentence stays true because these tests pass there.
- [ ] `05-REVIEW-DISPOSITION.md` (under `.planning/milestones/v1.0-phases/05-import-ui-and-post-install/`): set WR-01, WR-02, WR-03, WR-05, WR-06 dispositions when fixed; WR-04 is already fixed (worker lambda captures `p=plan` at `import_dialog.py:2746`; `open_path` guards `is_installing()` at `:1219`).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — (single-user desktop tool) |
| V5 Input Validation | yes | Blank/whitespace Destination rejected (`_dest_path`); `quote()` on every URI written into a table; JSON shape checks on the re-read |
| V6 Cryptography | no | — |
| V12 File and Resources | yes | Atomic writes via `fsutil`, backup before every table / `kicad_common.json` write, containment check unchanged in `applier._preflight` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Write to an unintended folder (CWD via empty path) | Tampering | `_dest_path()` returns `None`; never `Path("")` |
| Lost update of `kicad_common.json` (stale copy written back) | Tampering / Integrity | Re-read after confirm, merge only the two vars, backup, atomic replace (REV-05) |
| Path traversal in table URIs | Tampering | URIs are built from `rel_path` of scanned/planned libraries and passed through `sexpr.quote`; repoint never takes user text |
| Zip/package strings shown as markup | Spoofing | Unchanged; new Finishing and dialog texts are fixed strings, names go through plain-text labels |
| Rolling back over another process's file | Tampering | Unchanged (`_still_fresh`); D-14 does not alter it, but the key is `listed_path or path`, which stays equal to `path` for planner plans |

## Sources

### Primary (HIGH confidence — files read this session)
- `kicad_lib_manager/table_generator.py` (1-487), `main_window.py` (1-120, 195-240, 405-460, 555-640, 705-915, 985-1198), `library_scanner.py` (1-60, 100-330), `kicad_process.py`, `fsutil.py`, `importer/applier.py` (all), `importer/planner.py` (640-790, 1150-1380, 1500-1600), `importer/verify.py` (40-150), `importer/preview.py` (130-260), `importer/content.py` (100-149), `widgets/import_dialog.py` (1-130, 240-500, 590-640, 826-860, 1130-1352, 1440-1480, 2140-2260, 2460-2860, 3100-3220), `widgets/help_dialog.py` (1-140), `widgets/conflict_row.py` (1-150), `widgets/theme.py`
- `.planning/phases/12-.../12-CONTEXT.md`, `.planning/milestones/v1.0-phases/05-import-ui-and-post-install/05-REVIEW.md`, `05-UI-REVIEW.md`, `.planning/milestones/v1.0-phases/04-plan-and-install-core/04-UAT.md`, `tests/README.md`
- Tests read: `tests/test_install_apply.py` (1-140, 464-500, 670-835), `tests/test_install_plan.py` (480-515, 1300-1345, 1540-1615), `tests/test_main_window_import.py` (320-520), `tests/test_main_window.py` (40-135), `tests/test_kicad_config.py` (120-170), `tests/test_import_dialog.py` (40-100, 170-325, 3590-3640), `tests/test_help_dialog.py`, `tests/test_layering.py`, `tests/test_commit_plan.py:190-215`
- Executed this session: `fsutil file setCaseSensitiveInfo/queryCaseSensitiveInfo` on a fresh folder; hand-built twin rollback and planner overwrite on that folder (results quoted above); offscreen `QTextBrowser` rich-text probes (`pt` sizes, heading flattening, `line-height`); pytest runs and timings above; a throwaway pytest file confirming case-sensitive folders are cleaned by `--basetemp`

### Secondary (MEDIUM confidence)
- Qt 6 QThread documentation (https://doc.qt.io/qt-6/qthread.html): `finished()` is emitted from the associated thread "right before it finishes executing"; "the thread may still run for arbitrary amount of time after the finished() signal is emitted"; "Deleting a running QThread (i.e. isFinished() returns false) will result in a program crash. ... Wait for the finished() signal before deleting the QThread." [CITED: doc.qt.io/qt-6/qthread.html]

### Tertiary (LOW confidence)
- Qt's QThread destructor behaviour while a thread is in its finish phase (A1): recalled from source, not checked this session.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; versions read from the venv.
- Architecture: MEDIUM — defect locations and data flow are verified; the Finishing state, Retry loop and worker placement are designs that have not been built.
- Pitfalls: HIGH for the ones measured (headings, case-sensitive behaviour, fixture `running=` conflict, stale `incoming_op`), MEDIUM for the teardown-crash risk.

**Research date:** 2026-11-01
**Valid until:** 2026-12-01 (stable code; re-check line numbers if Phase 13 lands first)
