# Phase 5: Import UI and Post-Install - Research

**Researched:** 2026-10-20
**Domain:** PySide6 6.12 desktop GUI over an existing, finished, Qt-free import core (Phase 3/4), plus an add-only lib-table write and a main-window rescan hook
**Confidence:** HIGH (everything below was read in the repo or measured in the project venv this session; the few `[ASSUMED]` items are listed in the Assumptions Log)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Carried forward (locked)**
- Preview and install use the same `InstallPlan`. The preview renders the plan object, and Install calls `apply_plan` on that same plan, the most recent one built (PREV-07). Phase 4 designed the plan to be previewable (`plan.py` docstring).
- **Conflicts:** Every conflict blocks until it is resolved. The choices are `overwrite`, `rename` (a free `_2` name is suggested and can be edited) and `skip`. Nothing is pre-selected, and there is no "overwrite all" (Phase 4 D-05, D-06). Skip means "keep the existing item and link it" (D-09). Case-only clashes between files count as conflicts (D-10).
- Install is refused while `importer.suggest.placeholder_tokens(library_name)` is non-empty (Phase 3 D-04, ROADMAP contract).
- The `Package` must stay open until `apply_plan` returns (WR-04). The dialog owns the package for its whole lifetime and closes it when the dialog closes.
- Every scan goes through `MainWindow._start_scan`, which refuses while a worker exists (Phase 2 HARD-05).
- Services return `Issue` lists and never raise for expected failures. Routing is by `Severity`. Errors go to the log panel, not to message boxes (conventions).
- Long work runs on a `QThread` and never on the GUI thread. That includes `open_package`, `detect_candidate`, `build_plan` (which may call kicad-cli) and `apply_plan` (Phase 4 D-03).
- Field roles, D-11..D-15: `Manufacturer` and `MPN` are always filled (D-11), the model is named `<MPN>.<ext>`, and `ki_fp_filters` holds the installed footprint names exactly.

**Dialog flow and entry (UX-01, UX-02, INTK-07)**
- **D-01: One window-modal import dialog with a split view.** Left pane: package, items, target library, footprint name and fields. Right pane: live preview. Bottom row: Install button and blocking-reason status line. No wizard and no panel inside the main window.
- **D-02: The start step offers the newest Downloads zip.** When no package is loaded: "Newest in Downloads: `<name>` (`<age>`) [Open]"; next to it **Browse zip...** and **Browse folder...**, which open in the last-used import folder. Last-used folder persisted through new `settings.py` helpers (`load_*` / `save_*`, key e.g. `import/last_dir`). The package is never auto-opened. A **Change...** control returns to package selection.
- **D-03: Dropping onto the main window opens the dialog with the package loaded.** Works for a `.zip` or a folder. Drops and "Import Part..." are disabled while a scan runs. Other drops (wrong type, several files): refuse, with a log line.
- **D-04: The item picker is inline in the left pane (INTK-07).** Symbol: combo box, exactly one chosen, its `extends` parent comes along automatically (D-16, D-17). Footprints: checklist; first checked is the linked one, user can make another linked; all checked go into `ki_fp_filters`. Model: combo box with a "No model" entry. A single item shows as a plain label. Changing a pick rebuilds the plan. The UI never passes a blank choice to `InstallOptions` (resolves Phase 4 IN-04).
- **D-05: A refused or empty package keeps the dialog open on the start step.** Covers hostile zip, KiCad 5-only package, detection finding nothing. The dialog lists the package's ERROR and WARNING reasons, and the same Issues go to the main log. User can pick another file. Resolves Phase 4 **WR-06**: when no candidate is found, `package.issues` must still reach the UI.
- **D-06: The plan rebuilds automatically.** About 300 ms after typing stops, immediately on combo/checkbox change. Rebuilds run on a worker thread. A newer edit supersedes a stale rebuild; its result is discarded. While a rebuild is pending or running, the preview shows "Updating..." and Install is disabled. kicad-cli output is cached so repeated rebuilds don't re-run the CLI (`_cache_key` / `clear_cache` exist; check coverage).
- **D-07: The preview is a sectioned `QTreeWidget`.** Sections: Files (`+` new / `~` modified / `=` unchanged, repo-relative path), Renames (old -> new), Path rewrites (Footprint field `<Lib>:<FP>`, model path `${CUSTOM_3DMODEL_DIR}/...`, `ki_fp_filters`), Format (source -> target version, kicad-cli action), Conflicts, Issues (coloured by severity, incl. "no 3D model found" INTK-08). A rebuild re-renders the tree and keeps expand state and scroll position. Changed rows are not flashed.
- **D-08: Double-clicking a file row opens a read-only content view.** New text file: planned text. Modified file (e.g. `.kicad_sym`): `difflib` unified diff of current file against planned bytes. STEP/binary: size and SHA-256. A conflict row opens the same view, existing item against incoming.
- **D-09: The status line explains why Install is disabled.** Lists every blocking reason (unresolved conflicts, placeholder tokens, ERROR Issues, empty Value or MPN, "Updating..."). Each reason is clickable and focuses the matching field or conflict row. Offending field gets an amber border; one shared amber constant (`#8A5200`).
- **D-10: Install runs on a worker with progress and no Cancel.** Steps from `apply_plan`'s `progress` callback drive a progress bar and step text. All inputs locked, closing blocked until install finishes. No Cancel.

**Editing and conflicts (PREV-02..05, LIB-01/02 UI side)**
- **D-11: The target library is an editable combo box with a badge.** Pre-filled with `suggest_library` name. Dropdown lists ranked `alternatives` first, then every `Custom/` library read fresh via `layout.list_existing_libraries`. Badge "existing" or "new - creates .kicad_sym + .pretty". Low-confidence and placeholder tokens highlighted amber.
- **D-12: Each conflict gets its own row with three toggle buttons** (Overwrite / Rename / Skip), none selected at first. Rename reveals an editable name field pre-filled with `Conflict.suggested_name`. One-line hint per action. Double-click opens existing-against-incoming (D-08). No overwrite-all.
- **D-13: Fields are pre-filled, and an emptied field means "clear" (settles WR-05).** Value, Datasheet, Description, Manufacturer, MPN start with the value the plan would write. A field the user empties installs an empty value. A restore button on each field restores its default. **Value and MPN cannot be emptied** (Install blocked with a reason). **Phase 4 change needed:** `InstallOptions` currently turns `""` into `None` ("keep vendor value"); it must tell "explicitly empty" from "not set" (sentinel or set of cleared fields). Keep WR-05 behaviour for callers that don't opt in; update the docstring. Reversible; local to `InstallOptions` and `_edit_symbol`.
- **D-14: The footprint name is editable (PREV-02); the symbol name is read-only.** Footprint name defaults to the vendor name, sanitised. Symbol name shown vendor -> sanitised and changes only via a conflict's Rename. Displayed Footprint field `<Lib>:<FP>` follows every edit (PREV-03) and is read from the rebuilt plan, never computed separately in the UI.
- **D-14a: Conflict choices are kept by conflict key across rebuilds.** Keys `symbol:<lib>:<name>`, `footprint:<lib>:<name>`, `model:<file>` as built in `planner.py`. Choice stays while its key is in the new plan; a disappeared conflict drops its choice; a new conflict starts unresolved.
- **D-14b: Picking a different symbol resets the field edits.** Every field reloads from the new symbol's defaults; footprint name resets when the linked footprint changes. Changing only the target library keeps all field edits.

**After install (POST-01, POST-02, POST-05)**
- **D-15: The dialog switches to a result view in place.** Success: files written, warnings (pin/pad POST-04, name elsewhere POST-03, no 3D model), KiCad-running notice, backup folder, Close button. **Phase 6 adds its commit step to this view**; leave a slot/hook and keep `InstallResult` (`touched`, `vendor`, `source`) available. Failure: back to preview with rollback reasons on top; user can fix and retry. Full result also goes to the main log.
- **D-16: The post-install rescan starts when the result view appears.** Through `_start_scan`; trees update behind the dialog. After the scan, the installed library's symbol and footprint rows are checked, expanded, scrolled into view, made current in both trees. Rest of selection preserved (HARD-07). If an existing library got the part but isn't in the current tables, a WARNING says to press Generate.
- **D-17: Tables are regenerated automatically for a new library, adding entries only (POST-02).** Only when the install created a library: after the rescan, the new library's entries are added to `sym-lib-table` / `fp-lib-table` in the main window's current destination, using the normal backup and merge path (`write_tables`). Every other entry stays exactly as on disk. Unsaved selection changes in the main tree are **not** written. Selection passed to the merge = "managed entries currently in the tables, plus the new library". `kicad_common.json` path-variable sync follows the same rule as Generate.
- **D-18: The KiCad-running notice (POST-05).** After a successful install, `kicad_process.kicad_running()` is checked (off the GUI thread or with its 5 s timeout respected). If running, result view and log say "Reopen KiCad's Symbol/Footprint editors to see `<Lib>`".
- **D-19: Modality and the busy state.** Dialog is window-modal. "Import Part..." and drops disabled while a scan runs (join `_set_scan_running`). Generate, Rescan, Set KiCad Path unreachable while the dialog is open.

### Claude's Discretion
- **Module layout.** E.g. `widgets/import_dialog.py` (dialog, start step, left pane, preview tree, result view); a small widget module for the preview tree or conflict row; `QThread` workers for open/detect, rebuild and install, beside `ScanWorker` or in the dialog module.
- Keyboard shortcut for "Import Part..." (e.g. `Ctrl+I`), menu placement, toolbar button.
- **How "newest zip in Downloads" is found** (Windows Known Folder or `Path.home() / "Downloads"`; other OSes `Path.home() / "Downloads"`), the age shown, whether a stale zip is still offered.
- Exact debounce (~300 ms) and how a superseded rebuild is discarded (generation counter).
- How the add-only table merge is built: new helper in `table_generator.py`, or a selection derived from `table_info` / existing entries plus the new library.
- How `difflib` output is shown (monospace `QPlainTextEdit`), size cap for very large diffs.
- **Folding in the Phase 2 UI-review fixes where the touched code overlaps** (recommended; STATE.md blocker says fold into Phase 5): `populate()` `_updating` needs try/finally; Symbols Status column off-screen at default size; help text missing Collision and Ctrl+Shift+R; Select All / Deselect All enabled during a scan; shared amber colour constant. Also add "Import Part..." and the import flow to the help dialog.
- **Phase 4 review items the UI exposes.** **WR-02**: creating a library when `Custom/Symbols` is missing fails late; give a clear early refusal. IN-01 and IN-05 optional.
- Test strategy: pytest-qt offscreen tests for the dialog state machine (blocking reasons, rebuild supersession, conflict-choice carry-over, WR-05 clear semantics), plus manual UAT of the full UL-sample import into the real `Custom/`.

### Deferred Ideas (OUT OF SCOPE)
None. The discussion stayed within the phase scope. The git commit from the result view is already Phase 6 (D-15 leaves a place for it). Also not in this phase: SnapEDA/SamacSys adapters (Phase 7), SVG previews (v2 PREV2-01).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTK-07 | User picks which symbol/footprints/model when a package holds several | `ImportCandidate.symbols/footprints/models` are tuples of items with `.name`/`.filename`; `InstallOptions.symbol/footprints/model/no_model` select (see Phase 4 API table). Footprint order = link order. |
| PREV-01 | Preview lists every file created/modified, every rename, every path rewrite | `plan.ops` (new/modified via `base_sha256`), `plan.renames`; **unchanged files and "old" rewrite values are not in the plan** and need a Qt-free derivation helper (Pitfall 1, 2). |
| PREV-02 | Edit footprint name, default vendor name | `InstallOptions.footprint_names` (vendor name -> typed name); default `FootprintItem.name_check.sanitized`. |
| PREV-03 | Footprint field `<Lib>:<FP>` follows edits | Plan carries `library` + `linked_footprint`; field rebuilt each plan. |
| PREV-04 | Edit Value, Datasheet, Description, Manufacturer, MPN; missing fields created | `InstallOptions` text fields + the new "cleared" opt-in (Phase 4 delta, Pitfall 3). |
| PREV-05 | Per-conflict overwrite / rename / skip | `plan.conflicts` + `InstallOptions.resolutions` keyed by `Conflict.key`. Incoming content of an unresolved conflict is **not** in the plan (Pitfall 2). |
| PREV-06 | Source vs target versions + kicad-cli normalise | `plan.source_version`, `plan.target_version`, `plan.normalised`, `plan.tools.kicad_cli`, Issue codes `install.version_*`, `install.cli_not_found`. |
| PREV-07 | Preview == installed | One `InstallPlan` object; `apply_plan` re-checks freshness (`install.stale_plan`). Generation counter + Install disabled while updating. |
| POST-01 | Rescan and select the new/updated library | `MainWindow._start_scan` + a pending-selection hook in `_on_scan_finished` (Architecture Pattern 5). |
| POST-02 | Tables regenerated for a new library (add-only) | New add-only helper in `table_generator` recommended (Pattern 6). |
| POST-05 | Tell user to reopen KiCad editors if running | `kicad_process.kicad_running()` on a worker (blocking, up to 5 s). |
| UX-01 | Drop zip/folder on main window | `setAcceptDrops(True)` + `dragEnterEvent`/`dropEvent` (Pattern 4). |
| UX-02 | Remember last folder, offer newest Downloads zip | New `settings.py` helpers; `QStandardPaths.DownloadLocation` (verified: returns `C:/Users/sylvain/Downloads` here). |
</phase_requirements>

## Summary

Phase 5 is almost entirely a GUI phase on top of a finished core. The Phase 4 API (`open_package` -> `detect_candidate` -> `build_plan` -> `apply_plan`) is Qt-free, never raises for expected failures, and reports progress through plain `progress(message, current, total)` callbacks, so each of the three long operations maps onto one generic `QThread` worker that emits queued signals. The dependencies are already in place: PySide6 6.12.0, pytest 9.1.1 and **pytest-qt 4.5.0 are installed in `env/`** and pinned in `requirements-dev.txt`; `tests/conftest.py` forces `QT_QPA_PLATFORM=offscreen`. The full suite is green (1345 passed, 5 skipped, 106 s) so the planner has a clean baseline. No new packages are needed.

Four findings change the plan and are not obvious from CONTEXT.md. (1) **The plan object does not hold everything the preview must show**: unchanged files, the vendor "old" values for path rewrites, and the incoming content of an *unresolved* conflict are not on `InstallPlan`; POST-03/POST-04 warnings only exist after `apply_plan` (they come from `verify.verify_install`), so they belong to the result view only. (2) **D-13 needs a real planner change, not just `InstallOptions`**: an explicit empty `manufacturer` is currently replaced by an inferred token in `build_plan` (`planner.py:751-757`), so a `cleared` set on `InstallOptions` alone would not work for Manufacturer. (3) **D-17 "add-only" is not what `write_tables` does**: it regenerates every managed entry as one block, drops flags/extras and removes stale managed entries; a small new add-only helper in `table_generator.py` is the only way to meet "every other entry stays exactly as it is on disk". (4) **The kicad-cli cache covers only `upgrade_symbol_text` and only successes**, keyed on the *unrenamed* unit text, so repeated rebuilds with different library/footprint/field edits are cache hits; but it is an unsynchronised module-level `OrderedDict`, so rebuilds must be serialised (one `build_plan` worker at a time, latest request wins).

**Primary recommendation:** Put all decisions that can be tested without Qt into new Qt-free importer modules (plan -> preview rows, field defaults, blocking reasons, diff text, conflict-choice carry-over, add-only table entries) registered in `tests/test_importer_layering.py`; keep the Qt layer thin (one dialog, one generic `TaskWorker(QThread)`, a serialised rebuild coordinator with a generation counter); make the Phase 4 delta (`InstallOptions.cleared` + planner manufacturer fix + WR-02 refusal) the first wave.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Open/detect/build/apply | Importer core (Qt-free, `importer/`) | GUI worker thread | Already built; UI only schedules it off the GUI thread |
| Preview rows, field defaults, blocking reasons, diff text | New Qt-free importer module(s) | Widgets render | Testable without Qt; plan -> rows is pure |
| Dialog state machine, debounce, generation counter | Widget layer (`widgets/import_dialog.py`) | Workers | Owns Package lifetime and Qt timers |
| Drag and drop, menu/toolbar, busy state, post-install scan hook | `main_window.py` | `settings.py` | MainWindow already owns `_start_scan` and `_set_scan_running` |
| Last-used folder | `settings.py` | — | Conventions: all persistence through `settings.py` |
| Newest Downloads zip | Widget/start page via `QStandardPaths` | Qt-free sort helper | Qt locates the folder; the "newest zip" scan can be pure |
| Add-only table write | `table_generator.py` (Qt-free) | `main_window.py` calls it | Backup and merge logic live there |
| KiCad-running check | `kicad_process.py` on a worker | Result view | Blocking subprocess, 5 s timeout |
| Shared colours/spacing/button QSS | New `widgets/theme.py` | — | UI-SPEC: single source of truth |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PySide6 | 6.12.0 | All GUI | Already the only third-party runtime dependency [VERIFIED: requirements.txt `PySide6==6.12.0`; `PySide6.__version__` printed `6.12.0` in env/] |
| Python stdlib (`difflib`, `hashlib`, `zipfile`, `os`, `time`) | 3.14 | Diff text, SHA-256 display, newest zip, age text | Project constraint: stdlib only |

### Supporting (test only)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 | Runner | All tests [VERIFIED: `requirements-dev.txt` lines `pytest==9.1.1`] |
| pytest-qt | 4.5.0 | `qtbot`, `waitUntil`, `waitSignal` | Dialog state-machine tests [VERIFIED: `env/Lib/site-packages/pytest_qt-4.5.0.dist-info` and `pytestqt/` exist; `pyproject.toml` has `qt_api = "pyside6"`] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `QStandardPaths.DownloadLocation` | `SHGetKnownFolderPath(FOLDERID_Downloads)` via ctypes | Qt already resolves the Known Folder on Windows (measured: `['C:/Users/sylvain/Downloads']`); ctypes adds platform code for no gain. Fall back to `Path.home() / "Downloads"` if the list is empty or the folder is missing. |
| New add-only table helper | `write_tables` with a derived selection | See Pattern 6. Derived selection is cheaper but regenerates managed entries and removes stale ones. |
| `QThread` subclass per task | `QThreadPool`/`QRunnable` | Project convention is `QThread` + signals (`ScanWorker`); `QRunnable` has no signals without a helper `QObject`. Stay with `QThread`. |

**Installation:** none. `pip install -r requirements-dev.txt` already satisfied in `env/`.

## Package Legitimacy Audit

No external packages are added in this phase. `pytest-qt==4.5.0` and `PySide6==6.12.0` are already pinned in `requirements-dev.txt` / `requirements.txt` and installed in `env/` (Phase 1, FOUND-01). The legitimacy seam was therefore not run.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none new) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Phase 4 API the UI drives (verified by reading the source this session)

| Call | Signature (verbatim) | Returns | Slow? | Progress shape |
|------|---------------------|---------|-------|----------------|
| `open_package` (`importer/package.py:251`) | `open_package(path: Path, repo_root: Path, progress: Callable \| None = None) -> Package` | `Package`; expected failures are ERROR Issues in `package.issues`, `package.refused` is true | Yes (zip staging, SHA-256 of every file; up to 250 MiB) | `progress(f"Staging {name}", i, total)` (zip) / `progress(f"Reading {rel}", i, total)` (folder) |
| `detect_candidate` (`importer/detect.py:15`) | `detect_candidate(package: Package) -> tuple[ImportCandidate \| None, list[Issue]]` | `(None, [])` if `package.refused`; the returned list is detection Issues **only, excludes `package.issues`** | Medium (reads/parses files) | none |
| `detect_tools` (`planner.py:231`) | `detect_tools(kicad_fp_dir, *, explicit_cli=None, runner=None) -> ToolContext` | `ToolContext(kicad_cli, cli_runner, kicad_symbols_dir)` | Fast (stat/`which`) | none |
| `build_plan` (`planner.py:585`) | `build_plan(candidate, options, layout, tools=ToolContext(), *, package_issues=(), progress=None) -> InstallPlan` | Frozen `InstallPlan`; never raises for expected failures; refusals are ERROR Issues on a blocked plan | **Yes when kicad-cli runs** (`upgrade_symbol_text`, 60 s timeout); otherwise fast | `progress(message, current, 5)`, steps 1..5 ("Reading the package", "Reading the target library", "Planning names", "Editing the symbol", "Checking for conflicts") |
| `apply_plan` (`applier.py:308`) | `apply_plan(plan, *, backup_root=None, progress=None) -> InstallResult` | `InstallResult(ok, library, new_library, touched, issues, backup_dir, vendor, source)`; refuses a blocked plan (`ok=False`, ERRORs); no-op returns `ok=True` + INFO `install.nothing_to_do` | **Yes**: kicad-cli load gate ("can take minutes", `applier.py:367`), file writes, verify | `progress(f"Writing {op.path.name}", index, total)` with `index` in `0..total-1`: **never reaches `total`**, so the UI must set 100 % itself on completion. A raising callback is dropped for the rest of the run and noted once (`install.progress_failed`). |
| `suggest_library` (`suggest.py:299`) | `suggest_library(meta: PartMeta, existing: Sequence[ExistingLibrary] = ()) -> LibrarySuggestion` | `.name`, `.type/.subcategory/.manufacturer` (`TokenChoice.token/.source/.confident`), `.confidence`, `.placeholders`, `.matches_existing`, `.alternatives` (`RankedLibrary.name/.score/...`, max 5), `.issues` | Fast | none |
| `placeholder_tokens` (`suggest.py:213`) | `placeholder_tokens(name: str) -> list[str]` | e.g. `["SubCategory"]` | Fast | none |
| `list_existing_libraries` (`layout.py:69`) | `(layout: RepoLayout) -> list[ExistingLibrary]` (`name`, `has_symbols`, `has_footprints`) | Fresh disk listing, names only | Fast (directory listing) | none |
| `sanitize_name` / `sanitize_filename` (`naming.py`) | `-> NameResult` (`.original`, `.sanitized`, `.issues`) | | Fast | none |
| `kicad_running` (`kicad_process.py:19`) | `kicad_running(*, platform: str \| None = None) -> list[str]` | Sorted lower-case process names, `[]` on none or failure | **Blocking subprocess, 5 s timeout** | none |
| `run_load_gate` (`applier.py:247`) | `run_load_gate(plan) -> list[Issue]` | Public, writes nothing; **not** needed for the preview (apply runs the gate itself) | Slow | none |

Key verbatim facts the planner needs:

- Conflict keys, built in `planner.py`: `f"model:{model_file.casefold()}"` (line 864), `f"footprint:{library}:{name.casefold()}"` (line 937), `key = f"symbol:{library}:{default}"` (line 996, **not** casefolded). Because the library is inside footprint and symbol keys, switching library naturally drops carried choices (D-14a), and renaming a footprint changes its key (choice dropped, by design).
- `Conflict` fields (`plan.py:84-93`): `key`, `kind` (`"symbol" | "footprint" | "model"`), `name`, `existing`, `suggested_name`, `resolution`. `Resolution(action, rename_to=None)` with `action` one of `"overwrite" | "rename" | "skip"`.
- `InstallPlan.blocked` is `any ERROR issue or unresolved conflicts`; `is_noop` is `not self.blocked and not self.ops` (`plan.py:151-157`). `apply_plan` on a blocked plan returns `ok=False` without writing.
- `FileOp.kind` values: `"mkdir" | "model" | "footprint" | "symbol_lib"`; `base_sha256 is None` means "new file", otherwise "modified/overwritten" (`plan.py:73-81`). For `symbol_lib` the `data` is the **whole** planned `.kicad_sym` file, so a modified-library diff is `existing file` vs `op.data` (the unified diff shows only the added/replaced symbol hunk).
- `InstallOptions` blank rule, verbatim (`plan.py:65-69`):
  ```python
  def __post_init__(self) -> None:
      for name in _TEXT_OVERRIDES:
          text = getattr(self, name)
          if isinstance(text, str) and not text.strip():
              object.__setattr__(self, name, None)
  ```
  with `_TEXT_OVERRIDES = ("value", "datasheet", "description", "manufacturer", "mpn")` (`plan.py:38`).
- Library name checks done by the planner (so the UI can rely on ERROR Issues): placeholder (`install.placeholder_library`), `install.invalid_library` (name not equal to its sanitised form, or empty), `install.library_case_clash`.
- Item names in `InstallOptions` are **vendor** names: `SymbolItem.name`, `FootprintItem.name`, `ModelItem.filename` (`plan.py` docstring). `footprint_names` maps vendor footprint name -> typed target name. `options.footprints` order defines the linked (first) footprint. `no_model=True` means "No model"; if the package has no model at all, pass neither (the planner then adds the WARNING `install.no_model`).
- `PartMeta` (`candidate.py:12-22`) carries the **vendor** `value`, `datasheet`, `description`, `manufacturer`, `mpn` (first non-empty alias, `adapters/base.py:60-73`) and is the source for field defaults.

## Architecture Patterns

### System Architecture Diagram

```
 File>Import Part... / Ctrl+I      drag a .zip/folder onto MainWindow
            |                                   |
            +-------------> MainWindow._open_import(path | None) <--- refuses if self._worker is not None
                                   |
                         ImportDialog.open()  (window-modal, non-blocking; owns Package)
                                   |
        Start page --(Open/Browse/drop)--> TaskWorker[open_package -> detect_candidate]
              ^   (refused/empty: show package.issues + detection issues, stay)      |
              |                                                                      v candidate
          [Change...]                                      Edit page (left: choices, right: preview tree)
                                                                   |  any edit
                                    combo/check: now    text: QTimer 300 ms (restart on keystroke)
                                                                   v
                                 RebuildCoordinator (one build_plan worker at a time, latest options win,
                                      generation counter; Install disabled + "Updating preview...")
                                                                   |
                                         InstallPlan (frozen) --> preview rows (Qt-free) --> QTreeWidget
                                                                   |  blocking_reasons(state, plan) --> strip + Install enabled?
                                                                   v Install
                              TaskWorker[apply_plan(plan, progress)]  (inputs locked, no Cancel, close blocked)
                                   | ok                                    | not ok
                      Result page + signal installed(InstallResult)   banner + auto rebuild (stale plan guard)
                                   |
        MainWindow._on_import_installed: log Issues -> set _pending_post_install -> _start_scan()
              |-> _on_scan_finished: _reapply_selection -> apply pending (check/expand/current) -> populate
              |-> new library? add-only table write to dest (backup + atomic) + sync_kicad_path_vars
              '-> TaskWorker[kicad_running()] -> result view notice + log
```

### Recommended Project Structure
```
kicad_lib_manager/
├── importer/
│   ├── plan.py            # + InstallOptions.cleared (Phase 4 delta)
│   ├── planner.py         # + honour cleared; manufacturer inference skipped when explicit; WR-02 early refusal
│   └── preview.py         # NEW, Qt-free: plan -> rows, field defaults, blocking reasons, diff text, choice carry-over
├── table_generator.py     # + add_library_entries(...) add-only helper (Qt-free)
├── settings.py            # + load_import_dir / save_import_dir
├── main_window.py         # menu/toolbar/drop/busy state/post-install hook
└── widgets/
    ├── theme.py           # NEW: AMBER etc., SP_*, PRIMARY_BUTTON_QSS (no Qt imports)
    ├── workers.py         # NEW: TaskWorker(QThread) generic
    ├── import_dialog.py   # NEW: ImportDialog (QStackedWidget pages)
    ├── conflict_row.py    # NEW
    ├── preview_tree.py    # NEW
    └── content_view.py    # NEW: read-only text/diff dialog + QSyntaxHighlighter
tests/
├── test_import_preview.py        # Qt-free logic
├── test_install_options_clear.py # Phase 4 delta
├── test_table_add_entries.py
├── test_import_dialog.py         # pytest-qt, offscreen
└── test_main_window_import.py    # drop, busy state, post-install hook
```
Module names are suggestions (Claude's Discretion); the constraints are: Qt-free logic lives in `importer/` (or another module added to a layering list) and every new `importer/*.py` must be added to `ALLOWED` in `tests/test_importer_layering.py` or `test_importer_modules_follow_layering` fails with `not registered in ALLOWED`. Suggested entry: `"importer.preview": {"models", "kicad_files", "importer.plan", "importer.candidate", "importer.suggest", "importer.naming", "importer.layout"}`. `test_importer_modules_load_no_qt` also asserts that importing every importer module loads no PySide6, `settings`, `main_window` or `widgets.*`. [VERIFIED: tests/test_importer_layering.py:30-95, 319-358]. There is **no layering test for `widgets/`**; the convention (widgets never import `main_window`; `backup_dialog` imports `table_generator`) is by review only.

### Pattern 1: One generic worker, signals not callbacks (D-06, D-10)
**What:** `TaskWorker(QThread)` with `result = Signal(object)`, `failed = Signal(str)`, `progress = Signal(str, int, int)`. Do **not** name a signal `finished`: `ScanWorker` does (`main_window.py:37`), which shadows `QThread.finished`, so `deleteLater`-on-finished and `QThread.isFinished` semantics are muddied. Broad `except Exception` only inside `run()` (convention).
```python
class TaskWorker(QThread):
    progress = Signal(str, int, int)
    result = Signal(object)
    failed = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.result.emit(self._fn(self.progress.emit))
        except Exception as e:  # thread boundary only
            self.failed.emit(f"{type(e).__name__}: {e}")
```
Pass `progress.emit` as the `progress` callback of the core; it takes `(str, int, int)` and the core callbacks are `progress(message, current, total)`. A callable that raises is dropped by `apply_plan` (`_notify`), so never touch widgets in it. Verified in 6.12.0: a signal emitted from a `QThread.run()` reaches both a bound-method slot and a lambda on the **main thread** (queued) [VERIFIED: scratchpad experiment thr.py this session]. Prefer bound methods of the dialog anyway.

### Pattern 2: Serialised, superseding rebuild (D-06)
**What:** the dialog holds `_gen: int`, `_building: TaskWorker | None`, `_queued: bool`, `_debounce: QTimer(singleShot, 300)`.
1. Any edit marks the dialog **dirty** immediately (Install disabled, strip = `Updating preview...`), then either calls `_request_rebuild()` now (combo/checkbox/Make linked) or restarts the debounce timer (text edits, rename name fields, library combo typing).
2. `_request_rebuild()`: `_gen += 1`; if a worker is running set `_queued = True` and return (do **not** start a second `build_plan`); else start a worker that carries `gen` and a snapshot of `InstallOptions`.
3. On `result(plan)`: ignore if `gen != self._gen` (superseded); else render. In both cases, if `_queued`, clear it and start the next worker with the **latest** options.
Why serialise: `kicad_cli._cache` is a plain module-level `OrderedDict` read with `if key in _cache: _cache.move_to_end(key)` (`kicad_cli.py:150-152`) and trimmed with `popitem`; two overlapping workers could race between the `in` test and `move_to_end`. A running `build_plan` cannot be cancelled anyway, so queue-latest loses nothing. [VERIFIED: kicad_cli.py:94-114, 147-152, 186-189].
**Install gating:** `Install` enabled only when `not dirty and not building and plan is not None and plan.generation == self._gen and no blocking reasons`. `apply_plan` is called with exactly `self._plan`.

### Pattern 3: Worker lifetime and Package ownership (WR-04, D-10)
- The `Package` is created inside the open worker thread and handed to the GUI thread through the `result` signal; from then on the **dialog** owns it. Closing it is a plain `package.close()` (idempotent) on the GUI thread.
- Close order in `done()`/`closeEvent`/`reject`: (1) refuse while the install worker runs (ignore the event); (2) otherwise set `_closing`, stop the debounce timer, `wait()` for a running rebuild/open worker (bounded by a build; `MainWindow.closeEvent` already uses this `wait()` pattern); (3) only then `package.close()`. Closing earlier makes a still-running rebuild return the harmless Issue `install.source_gone` ("is no longer available ... open the package again", `planner.py:89`), never a crash.
- Never let a `QThread` be garbage-collected while running (Qt aborts with "QThread: Destroyed while thread is still running"). Parent the worker to the dialog and keep a reference until it ends; the dialog's wait-before-close covers the dialog path, and the main-window `kicad_running` check should be owned by the dialog (result view) so it ends with it.
- Use `ImportDialog.open()` (window-modal, non-blocking) from `MainWindow`, not `exec()`, so tests can drive it with `qtbot`; connect a `installed = Signal(object)` carrying `InstallResult` to a `MainWindow` slot.

### Pattern 4: Drag and drop on QMainWindow (UX-01, D-03)
```python
self.setAcceptDrops(True)

def dragEnterEvent(self, event):
    if self._worker is not None or self._import_dialog is not None or not event.mimeData().hasUrls():
        event.ignore(); self.statusBar().showMessage("Import is unavailable while a scan is running.", 3000); return
    event.acceptProposedAction()

def dropEvent(self, event):
    urls = [u for u in event.mimeData().urls() if u.isLocalFile()]
    ...  # exactly one: Path(u.toLocalFile()); is_dir() or suffix.casefold() == ".zip" -> self._open_import(path)
```
Accept on enter (so `dropEvent` can explain a refusal, UI-SPEC), re-check the busy state in `dropEvent` too (a scan can start between enter and drop). Wording is fixed by UI-SPEC. Test with `QMimeData.setUrls([QUrl.fromLocalFile(...)])` and `QDropEvent(QPointF, Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)` constructed in the test, posted via `QApplication.sendEvent(window, event)`; no real drag is needed offscreen. [ASSUMED: exact `QDropEvent` constructor argument list in 6.12; check in the first test.]

### Pattern 5: Post-install rescan and selection (D-16)
`_start_scan` refuses while `self._worker is not None` (`main_window.py:290`), and `_finish_scan` clears `_worker` only after `_on_scan_finished`/`_on_scan_error`, so a scan that is *already running* when Install finishes would swallow the post-install request. Because Import is disabled during a scan and the dialog is modal, this only happens if the user triggered a rescan before the dialog opened and it is still going; guard by disabling "Import Part..." while `_worker is not None` (D-19) and have `_on_import_installed` queue `self._pending_post_install` and call `_start_scan()`; if `_start_scan` was refused, keep the pending request and run it from `_finish_scan`.
Hook point: inside `_on_scan_finished`, after `_reapply_selection(previous, result)` / startup branch and **before** `self._tree.populate(result)` set `lib.selected = True` on the installed library's `SymbolLibrary` and `FootprintLibrary` (match by `rel_path`, derived from the layout: `layout.symbols_dir.relative_to(repo_root).as_posix() + f"/{library}.kicad_sym"` and `.../{library}.pretty`; `source` is the first path segment, `Custom`, `library_scanner.py:281-285`). `populate` renders `selected` flags as given (`library_table.py:157`). Then, after `populate`, add a new public method on `LibraryTableWidget` (e.g. `reveal(sym_rel_path, fp_rel_path)`) that expands the groups, `setCurrentItem`, and `scrollToItem` in both trees (the tree already stores `_sym_items`/`_fp_items` by `rel_path`). Keep `_updating` try/finally while doing programmatic changes.
`_reapply_selection` keeps only previously selected rel_paths, so a **new** library (absent from `previous`) comes in unchecked; that is why the explicit "select the installed library" step is needed. Selecting the symbol library does **not** need `_sync_footprint_selection` here because both flags are set directly.
Existing-library case (D-16 last sentence): after the scan, if `not new_library` and the library's rel_path is not in `table_info(dest/"sym-lib-table").managed` (or fp table), log the WARNING `"{Lib} is not in the library tables. Press Generate Tables to add it."` (UI-SPEC copy).

### Pattern 6: Add-only table write (D-17, POST-02)
What `write_tables` actually does (verified `table_generator.py:69-204, 232-296`): it takes `libs` with `.selected`, rewrites **all** managed entries (URI contains `${KICAD_LIB_GITHUB}/`) as a single regenerated block at the first managed entry's position, removes managed entries whose library is not selected (`removed`), removes "stale" managed entries whose rel_path is not in the scanned list (`table.stale_managed` WARNING), and drops per-entry `flags`/`extras` (`table.managed_flags_dropped` WARNING). External entries are preserved byte-for-byte.
- **Option A (derived selection; cheapest, within D-17 text):** `selected = rel_path in table_info(...).managed or rel_path == new lib`, applied to copies of the scan lists. It satisfies "does not write unrelated *selection* changes" but regenerates managed entries (loses `(disabled)`-style flags with a warning) and removes stale managed entries.
- **Option B (recommended): a new add-only helper** `add_library_entries(dest, sym_libs, fp_libs) -> list[Issue]` in `table_generator.py` that loads each table with `kicad_files.load`, skips nicknames already present (any entry, external or managed; log `Library tables not changed: {Lib} was already listed`), inserts only the new `_entry_text(...)` lines before the closing paren using the same insertion branch as `_merge_table` (`if not placed and block:`), then reuses `fsutil.backup_file(path, path.parent, number=backup_number)` and `fsutil.atomic_write_text(path, content, bom=bom)` exactly as `write_tables` does. If a table file is missing, create it from the same template `_merge_table` uses. This honours "every other entry stays exactly as it is on disk" literally and is ~40 lines with tests. The planner should pick B unless the owner prefers A for reuse; both satisfy the Claude's-Discretion clause.
After the table write, call `sync_kicad_path_vars(REPO_ROOT)` and log its Issues (same as `_on_generate`, `main_window.py:540`); that call rewrites `kicad_common.json` (backed up, atomic, HARD-03) and its `running=` seam already warns when KiCad runs. Destination = `Path(self._dest_combo.currentText())`; mirror `_on_generate`'s `dest.exists()` check and log an ERROR instead of creating it silently if it is missing.

### Anti-Patterns to Avoid
- **Computing `<Lib>:<FP>` in the widget.** Read `plan.library` + `plan.linked_footprint` from the latest plan only; show `(none)` when `linked_footprint is None` (skipped chosen symbol).
- **Starting a second `build_plan` while one runs.** See Pattern 2.
- **Passing blank strings into `InstallOptions`** for symbol/footprints/model (Phase 4 IN-04): omit the argument or pass the one real item.
- **A modal `QMessageBox` for any failure** (project convention and UI-SPEC: none in this phase).
- **Letting the Enter key in a line edit trigger Install**: `setAutoDefault(False)`/`setDefault(False)` on every button (UI-SPEC); in a `QDialog`, buttons auto-default unless disabled.
- **Reading the plan on the GUI thread beyond rendering**: `plan.ops[i].data` for a big file is already in memory; hashing/diffing a large model is not (STEP can be up to 100 MiB); hash on a worker.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unified diff | Custom line differ | `difflib.unified_diff(a, b, fromfile=, tofile=, lineterm="", n=3)` | Measured 0.04 s for a 40,000-line library with 300 changed lines [VERIFIED: scratchpad dl.py]; real `Custom/Symbols` files are 5-50 KB [VERIFIED: wc -c, largest 49,378 bytes] |
| Atomic write and backups of tables | New write code | `fsutil.atomic_write_text`, `fsutil.backup_file` (same as `write_tables`) | Locked-file retry, read-only pre-check, Issue reporting already done (FOUND-05) |
| Name checks (library, footprint, rename) | Regex in the widget | The planner's ERROR Issues (`install.invalid_library`, `install.invalid_name`, `install.bad_rename`, `install.library_case_clash`) + `placeholder_tokens` | One source of truth; the UI shows the Issue text as a blocking reason |
| Conflict suggestion names | `_2` logic | `Conflict.suggested_name` | Already case-folded and length-safe (`suggest_free_name`) |
| Libraries on disk | `os.listdir` in the widget | `layout.list_existing_libraries` (fresh each call) | D-11 says read fresh at dialog open |
| Downloads folder | ctypes Known Folder | `QStandardPaths.standardLocations(QStandardPaths.StandardLocation.DownloadLocation)` | Verified working here |
| Process listing | New tasklist call | `kicad_process.kicad_running()` | Done, tested, 5 s timeout |
| Settings persistence | Direct `QSettings` | New `load_import_dir`/`save_import_dir` in `settings.py` | Convention |
| Rollback/backup | Any | `apply_plan` | Phase 4 D-18/D-19 |

**Key insight:** every decision the dialog displays already exists as data on `InstallPlan`, `Conflict`, `Issue` or `LibrarySuggestion`; the UI's job is to (re)build the plan from the user's choices and render it. Anything the plan does not carry (unchanged rows, old values) is derived in one Qt-free module and tested against the real UL sample, not recomputed in widgets.

## Runtime State Inventory

Not a rename/refactor phase. Omitted. (The Phase 4 delta changes an internal dataclass only; no stored data, service config, OS registration, secrets or build artefacts carry the renamed items.)

## Common Pitfalls

### Pitfall 1: The plan does not list unchanged files, and "old" rewrite values are not on it
**What goes wrong:** D-07 wants `= unchanged` rows and `{old} -> {new}` in Path rewrites; `InstallPlan` has only `ops` (writes), so an identical footprint/model/library produces **no** op and silently vanishes from the tree.
**How to avoid:** the Qt-free `preview.py` derives rows from `plan` + `candidate`: for each name in `plan.footprint_names` with no `footprint` op at `plan.pretty_path / f"{name}.kicad_mod"` -> `=` (or "kept existing" when the conflict resolution is `skip`); the same for `plan.model_file` against the `model` op; `plan.symbol_lib_path` with no `symbol_lib` op -> `=`. `base_sha256 is None` -> `+`, else `~`; `mkdir` ops are shown as `+ <name>.pretty/`. Old values: `SymbolItem.meta.footprint_field`, `.fp_filters`, and `FootprintItem.model_paths[0]`; new values: `f"{plan.library}:{plan.linked_footprint}"`, `" ".join(plan.footprint_names)`, `f"{MODEL_DIR_VAR}/{plan.model_file}"` (`MODEL_DIR_VAR = "${CUSTOM_3DMODEL_DIR}"`, `plan.py:16`). These formats are the planner's own (`planner.py:793, 889, 963-964`); guard with a test that parses the planned symbol/footprint bytes for the same values (see Validation).
**Warning signs:** a re-import of the same package shows an empty Files section instead of three `=` rows.

### Pitfall 2: The incoming content of an unresolved conflict is not in the plan
**What goes wrong:** `_decide_file` returns **no op** while `resolution is None` (`planner.py:485-486`), so D-08/D-12 "existing against incoming" has nothing to show for the very state the user is deciding in.
**How to avoid (no Phase 4 change):** on double-click of a conflict row, run a one-off `build_plan` on a worker with the current options plus `Resolution("overwrite")` for that single key (discarded afterwards; CLI results are cached so it is cheap), then take the matching op: footprint -> op whose `path.name == f"{name}.kicad_mod"`; symbol -> the `symbol_lib` op diffed whole-file against the library on disk (the diff is only that symbol's hunk); model -> `op.source.size`/`sha256` vs `os` size and SHA-256 of the existing file (hash on the worker). For an already resolved Overwrite the op is on the current plan and no extra build is needed. The "existing" side is read from `op.listed_path or op.path`.
**Alternative:** extend `InstallPlan` with per-conflict incoming bytes (Phase 4 change, larger blast radius); not recommended.

### Pitfall 3: An explicit empty Manufacturer is overwritten by inference (D-13)
**What goes wrong:** adding only a `cleared` set to `InstallOptions` is not enough. `build_plan` does (`planner.py:751-757`):
```python
manufacturer = options.manufacturer if options.manufacturer is not None else meta.manufacturer
if not manufacturer:
    choice = manufacturer_choice(meta)
    if choice.source != "placeholder":
        manufacturer = choice.token
    else:
        issues.append(Issue(Severity.WARNING, "install.manufacturer_missing", ...))
```
so `options.manufacturer == ""` falls into the inference branch and writes e.g. `TI`; with `manufacturer_forced=options.manufacturer is not None` (`planner.py:762`) it is then written as forced.
**How to avoid:** the Phase 4 delta (first wave): add `cleared: frozenset[str] = frozenset()` to `InstallOptions`; `__post_init__` keeps converting blank to `None` **except** it stores `""` for names listed in `cleared` (so `replace()` and the existing tests keep working: `test_blank_options_mean_not_set` and `test_blank_option_keeps_ul_vendor_values` in `tests/test_install_plan.py:281-307` must stay green unchanged); in `build_plan`, if `options.manufacturer == ""` (explicitly cleared) skip inference and the `manufacturer_missing` warning; `_edit_symbol`'s `put`/`role` already accept `""` (`role`: `value = override if override is not None else ...`, `put` -> `set_property_edit`). `value` or `mpn` in `cleared` must be refused by `build_plan` with an ERROR (suggested code `install.empty_required`) because `mpn` names the 3D model file (`planner.py:801` uses `final_mpn or sym_item.name`, which would silently fall back). Datasheet: an empty value is written as an empty property value (not `~`); confirm that is what the owner wants. Update the `InstallOptions` docstring (`plan.py:43-49`).
**Warning signs:** the UI shows Manufacturer empty but the preview's symbol diff shows `TI`.

### Pitfall 4: POST-03 / POST-04 warnings exist only after install
`verify.verify_install(plan)` (called in `apply_plan` after the writes) produces `verify.pin_pad_mismatch` and `verify.name_elsewhere` (`verify.py:211, 284`); `build_plan` does not call it. They arrive in `InstallResult.issues` and belong to the result view (matches D-15). UI-SPEC's phrase "when the plan carries them" for the preview is therefore a no-op: do not try to pre-compute them (the public helpers `pin_pad_issues`/`find_name_elsewhere` exist if the owner later wants a preview warning, but they need a loaded planned symbol and the footprint bytes, a Phase 4-level change).

### Pitfall 5: WR-06, nothing found drops `package.issues`
`detect_candidate` returns `(None, [])` for a refused package and only the locate Issues otherwise; package Issues are folded into a candidate only when one is found (`detect.py:43-45`). When `candidate is None` the UI must show `list(dict.fromkeys([*package.issues, *detect_issues]))` filtered to ERROR and WARNING for the start-page list, log them all, and when the combined list is empty show `No KiCad symbol or footprint was found in this package.` (UI-SPEC). Close the package at once on a refused/empty result (staged files are useless and `Package.close()` is idempotent; the refused path already closes inside `_refuse`).

### Pitfall 6: kicad-cli cache scope
- Cached: only `kicad_cli.upgrade_symbol_text` **successes**, keyed `(sha256(unit text), str(exe), (st_size, st_mtime_ns), runner)`, max 32, LRU [VERIFIED: kicad_cli.py:20, 102-114, 186-189]. Failures (timeouts, load errors) are **not** cached, so a broken CLI re-runs (up to 60 s) on every rebuild; the UI should surface the Issue and not rebuild on a timer.
- The cached text is the **unrenamed** unit (planner D-01: "normalised once, on the unrenamed unit, so later edits never re-run kicad-cli"), so changing library, footprint name, fields, conflict choices all hit the cache. A different **symbol** pick is a new key (one CLI run). Switching target library between existing/new changes which function runs: `_new_source` always calls the CLI; `_existing_source` calls it only when incoming version < target version.
- `load_gate` (the other CLI use) is **not** run by `build_plan`, only by `apply_plan`; Install therefore takes noticeably longer than a rebuild (progress text for it is not reported through `progress`; the bar will sit at the last "Writing ..." value or 0 while the gate runs, UI-SPEC already allows a held value).
- The install worker should call `kicad_cli.clear_cache()` never; the cache is process-wide and keyed to the binary stat.

### Pitfall 7: `QProgressDialog` from `_start_scan` appears over the result view
`_start_scan` always creates a window-modal `QProgressDialog` parented to the main window (`main_window.py:295-305`). Offscreen check this session: with a window-modal import dialog already shown, the progress dialog becomes `app.activeModalWidget()` [VERIFIED: scratchpad thr.py printed `activeModal: QProgressDialog`]. Per Qt's window-modality rules it blocks the main window, not the sibling import dialog [ASSUMED from Qt docs; verify visually in UAT], so the user will see a small progress box over the result view for the scan. Decide explicitly: either accept it (simple, consistent) or add an optional parameter to `_start_scan` (e.g. `show_progress: bool = True`) so the post-install scan runs quietly. Keep `_start_scan` the only entry point either way.

### Pitfall 8: Case-folded and sanitised names in keys and options
Footprint conflict keys use the **sanitised, casefolded** target name; model keys the casefolded model file name; symbol keys the sanitised default name case-sensitively. A carry-over map keyed by `Conflict.key` (D-14a) works as-is. Feed `Resolution("rename", rename_to=typed_text)` with the exact text from the field (empty string -> planner ERROR `install.bad_rename`, which also yields the UI reason `Enter a new name for ...`); `rename_to=None` makes the planner use `suggested_name`.

### Pitfall 9: Default field values must match what the planner would write
The planner's defaults: Value = vendor value (unchanged if no override); Datasheet/Description = vendor; Manufacturer = `meta.manufacturer` else `manufacturer_choice(meta).token` unless it is the `placeholder` source (then empty + WARNING); MPN = `meta.mpn` else the **vendor** symbol name (`role("MPN", MPN_FIELDS, fields.mpn, ref.name)`, `planner.py:183`). Put these in one Qt-free `field_defaults(candidate, symbol_name)` and pin it with an equivalence test: `build_plan(options with all defaults filled in)` must produce the same `ops` bytes as `build_plan(options with nothing set)` for the UL sample. If the equality breaks later, the preview would lie.

### Pitfall 10: Debounce edge cases
- A text edit and a combo change can race: combo change calls `_request_rebuild()` immediately and must **stop** the pending debounce timer, otherwise a stale snapshot is taken later (take the `InstallOptions` snapshot at request time, not at timer creation).
- `QLineEdit.textChanged` fires for programmatic `setText` (the restore button, defaults reload); wrap programmatic updates in `blockSignals(True)`/`False` with try/finally and call `_request_rebuild()` once afterwards (project convention).
- Editable `QComboBox`: use `currentTextChanged` for the debounce (typing) and `textActivated` for immediate rebuilds; `main_window.py:171-173` documents the same pitfall for the destination combo.

### Pitfall 11: Candidate lists parent symbols too
`locate` (adapters/base) does not filter `extends` parents out of `candidate.symbols`; the picker will therefore offer both a base symbol and its derived ones. Choosing a derived symbol installs parent + derived (`symbol_unit`, `planner.py:679`); choosing the base installs just it. The UI-SPEC note "extends parent included automatically" applies to derived picks. [ASSUMED: not confirmed by a multi-symbol fixture; `tests/installfixtures.py::extends_pair` builds one for tests.]

### Pitfall 12: Window close while the install runs
`QDialog` Esc/`reject()`/`closeEvent` and the window-manager close all route through different paths; override `closeEvent`, `reject` and `keyPressEvent`(Esc) to ignore while the install worker `isRunning()`. Also guard `MainWindow.closeEvent` (it already waits for its scan worker): with a modal child dialog the main window cannot be closed by the user, but a programmatic close in tests should not destroy a running install.

## Code Examples

### Downloads folder and newest zip (UX-02)
```python
# Source: QStandardPaths verified in env/ this session -> ['C:/Users/sylvain/Downloads']
from pathlib import Path
from PySide6.QtCore import QStandardPaths

def downloads_dir() -> Path | None:
    for text in QStandardPaths.standardLocations(QStandardPaths.StandardLocation.DownloadLocation):
        if Path(text).is_dir():
            return Path(text)
    fallback = Path.home() / "Downloads"
    return fallback if fallback.is_dir() else None

def newest_zip(folder: Path) -> tuple[Path, float] | None:   # Qt-free; no recursion
    best = None
    try:
        with os.scandir(folder) as it:
            for e in it:
                if e.name.casefold().endswith(".zip") and e.is_file():
                    m = e.stat().st_mtime
                    if best is None or m > best[1]:
                        best = (Path(e.path), m)
    except OSError:
        return None
    return best
```
Do the scan after the dialog is shown (a OneDrive-redirected Downloads can be slow); a `TaskWorker` or `QTimer.singleShot(0, ...)` is fine. Age text per UI-SPEC: `just now`, `{n} minutes ago`, `{n} hours ago`, `{n} days ago`.

### Blocking reasons (D-09) as a pure function
```python
# Qt-free; reasons carry a target id the widget maps to a control
@dataclass(frozen=True)
class Reason:
    text: str
    target: str   # "library" | "footprint_name" | "value" | "mpn" | "footprints" | "conflict:<key>" | "rename:<key>" | "plan"

def blocking_reasons(state: DialogState, plan: InstallPlan | None) -> list[Reason]: ...
```
Order fixed by UI-SPEC: Updating, plan ERROR issues, library name (empty or placeholder), Value/MPN empty, footprint selection, unresolved conflicts (row order), empty rename names. Placeholder text from UI-SPEC: ``Library name still contains a placeholder ({tokens}). Pick an existing library or type a real name.``

### Settings helpers (convention, `settings.py`)
```python
# ── Import folder ───────────────────────────────────────────────
def load_import_dir() -> Path | None:
    val = get_settings().value("import/last_dir", "")
    p = Path(val) if val else None
    return p if p is not None and p.is_dir() else None

def save_import_dir(path: Path) -> None:
    get_settings().setValue("import/last_dir", str(path))
```
Tests must redirect `QSettings` into `tmp_path` exactly like `tests/test_main_window.py` does (`QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, ...)` in an autouse fixture) or they will write the owner's real settings.

### Rebuild snapshot and carry-over
```python
def carry_resolutions(old: Mapping[str, Resolution], plan: InstallPlan) -> dict[str, Resolution]:
    keys = {c.key for c in plan.conflicts}
    return {k: r for k, r in old.items() if k in keys}   # D-14a
```
Keep the *user's* resolution map in the dialog (typed rename text included) and merge it into `InstallOptions.resolutions` at snapshot time; prune after each accepted plan.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `QThread` subclass overriding `finished` signal (existing `ScanWorker`) | Distinct signal names (`result`, `failed`) | n/a (project hygiene) | Avoids shadowing `QThread.finished` |
| `dialog.exec()` | `dialog.open()` + signals | Qt 5+ | Testable under pytest-qt, no nested loop in tests |

**Deprecated/outdated:** none relevant; PySide6 6.12 uses fully qualified enums (`Qt.WindowModality.WindowModal`), matching the project convention.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Window-modal `QProgressDialog` does not block a sibling window-modal `QDialog` (Qt docs semantics; only `activeModalWidget` was checked offscreen) | Pitfall 7 | The import dialog could be unclickable during the post-install scan; mitigation: quiet scan option. Check in UAT. |
| A2 | `QDropEvent` constructor signature `(QPointF, DropAction, QMimeData, MouseButton, KeyboardModifier)` works as written in 6.12 | Pattern 4 | Drop tests need a small adjustment |
| A3 | `candidate.symbols` lists extends parents as separate entries | Pitfall 11 | Picker may need to hide parents or label them |
| A4 | Owner wants an emptied Datasheet written as an empty value (not `~`) | Pitfall 3 | One-line change in the planner; confirm in UAT |
| A5 | Owner prefers the byte-preserving add-only helper (Option B) over reusing `write_tables` with a derived selection (Option A) | Pattern 6 | Option A is a fallback with documented side effects |
| A6 | Display scaling >150 % and dark mode are out of scope (UI-SPEC marks both unresolved assumptions) | UI-SPEC | Cosmetic only |

## Open Questions

1. **Quiet post-install scan?** Accept the standard progress dialog over the result view, or add `show_progress` to `_start_scan`? Recommendation: add the optional parameter (default unchanged), because the UI-SPEC says trees update "behind the dialog".
2. **Should the result view re-run the plan's pin/pad check earlier?** No: out of scope (Pitfall 4). Result view only.
3. **Hide parent symbols from the picker?** Needs a look at a real `extends` package; none is in `downloaded_examples/` (only the UL zip). Default: list everything the candidate lists.
4. **Table write outcome when the destination has no tables yet** (fresh machine): Option B creates both; log `Added ...`. Confirm the owner is happy for a first-ever table to be created by an import (Generate would do the same).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv `env/` | everything | yes | 3.14 (`env/Scripts/python.exe`) | — |
| PySide6 | GUI, tests | yes | 6.12.0 | — |
| pytest + pytest-qt | tests | yes | 9.1.1 / 4.5.0 | — |
| QT offscreen platform | headless Qt tests | yes | forced by `tests/conftest.py:10` | — |
| `kicad-cli` on PATH | none required | no (`which kicad-cli` empty) | — | Tests locate it through `find_kicad_footprint_dir`; `C:/Program Files/KiCad/9.0` exists. Tests needing it use `kicad_cli_path` fixture and skip if absent; dialog tests should inject `ToolContext(kicad_cli=None)` or the `tests/fakecli.py` runner |
| KiCad 9.0 install | UAT, `-m kicad_cli` tests | yes (`C:/Program Files/KiCad/9.0`) | 9.0 | — |
| `downloaded_examples/ul_CSD85301Q2.zip` | UL walk-through tests | yes | — | — |
| `Custom/` submodule | `custom_copy` fixture | yes (5 libraries listed) | — | fixture skips if missing |
| Downloads folder | start page | yes (`C:/Users/sylvain/Downloads`) | — | `Path.home()/Downloads`, then message |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `kicad-cli` not on PATH (resolved by app detection / fake runner).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-qt 4.5.0 (`qt_api = "pyside6"`) |
| Config file | `pyproject.toml` (`testpaths = ["tests"]`, `pythonpath = ["."]`, `addopts = "-ra --strict-markers"`; markers `wurth`, `local_kicad`, `kicad_cli`) |
| Quick run command | `./env/Scripts/python.exe -m pytest tests/test_import_preview.py tests/test_install_options_clear.py tests/test_table_add_entries.py tests/test_import_dialog.py tests/test_main_window_import.py -x -q` |
| Full suite command | `./env/Scripts/python.exe -m pytest -q` (baseline this session: **1345 passed, 5 skipped in 106.30 s**) |

Existing patterns to reuse: `tests/test_main_window.py` `make_window` fixture (fake `scan_all`, redirected QSettings, synthetic KiCad config); `ul_package` and `custom_copy` fixtures in `tests/conftest.py`; Phase 4 builders in `tests/installfixtures.py` (`target_lib`, `vendor_symbol_lib`, `extends_pair`, `vendor_footprint`) and `tests/zipfixtures.py`; `tests/fakecli.py` for a fake kicad-cli runner. `tests/` is in the scanner's `SKIP_DIRS`.

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTK-07 | Several symbols/footprints/models: picker choices become `InstallOptions` (first checked footprint linked; "No model" -> `no_model=True`; never blank) | unit + pytest-qt | `pytest tests/test_import_dialog.py -k picker -x` | ❌ Wave 0 |
| PREV-01 | Rows for new/modified/unchanged files, renames, rewrites derived from a real UL plan; re-import shows `=` rows | unit | `pytest tests/test_import_preview.py -k rows -x` | ❌ Wave 0 |
| PREV-02/03 | Typing a footprint name / library updates the displayed `<Lib>:<FP>` only after rebuild, from the plan | pytest-qt | `pytest tests/test_import_dialog.py -k footprint_field -x` | ❌ Wave 0 |
| PREV-04 | Field defaults equal planner output (equivalence test); clear semantics for Datasheet/Description/Manufacturer; Value/MPN block | unit | `pytest tests/test_import_preview.py tests/test_install_options_clear.py -x` | ❌ Wave 0 |
| PREV-05 | Per-conflict resolution; no bulk control; carry-over by key; library switch drops Overwrite | unit + pytest-qt | `pytest tests/test_import_preview.py -k carry tests/test_import_dialog.py -k conflict -x` | ❌ Wave 0 |
| PREV-06 | Format rows for each case (normalise / as-is / cli not found / newer refused) | unit | `pytest tests/test_import_preview.py -k format -x` | ❌ Wave 0 |
| PREV-07 | Install passes the identical latest plan object; Install disabled while updating; superseded result discarded (gate a fake `build_plan` with `threading.Event`) | pytest-qt | `pytest tests/test_import_dialog.py -k supersede -x` | ❌ Wave 0 |
| POST-01 | After a fake install, `_start_scan` runs once, installed library rows are checked/expanded/current, other selection kept (HARD-07) | pytest-qt | `pytest tests/test_main_window_import.py -k select -x` | ❌ Wave 0 |
| POST-02 | New library: add-only helper adds exactly 2 entries, keeps every other byte; existing library: tables untouched + WARNING; backup created | unit + pytest-qt | `pytest tests/test_table_add_entries.py tests/test_main_window_import.py -k tables -x` | ❌ Wave 0 |
| POST-05 | `kicad_running` stubbed non-empty -> notice and log WARNING; stubbed empty -> none | pytest-qt | `pytest tests/test_import_dialog.py -k kicad_running -x` | ❌ Wave 0 |
| UX-01 | Drop zip/folder opens dialog; several paths / wrong type / busy rejected with exact log strings | pytest-qt | `pytest tests/test_main_window_import.py -k drop -x` | ❌ Wave 0 |
| UX-02 | `import/last_dir` round trip; newest-zip choice and age text; missing Downloads message | unit + pytest-qt | `pytest tests/test_import_dialog.py -k start_page tests/test_settings_import.py -x` | ❌ Wave 0 |
| (D-04 Phase 3 contract) | Install disabled with reason while `placeholder_tokens(name)` non-empty | pytest-qt | `pytest tests/test_import_dialog.py -k placeholder -x` | ❌ Wave 0 |
| WR-02 | Library creation with missing `Custom/Symbols` is refused early with the UI-SPEC text | unit | `pytest tests/test_install_plan.py -k symbols_missing -x` | ❌ Wave 0 |
| WR-06 | No candidate -> package + detection Issues reach the start-page list and the log | pytest-qt | `pytest tests/test_import_dialog.py -k nothing_found -x` | ❌ Wave 0 |
| Layering | New importer module registered; no Qt in importer; amber literal gone | unit | `pytest tests/test_importer_layering.py tests/test_layering.py -x` | ✅ (edit ALLOWED) |

Deterministic testing of threads under pytest-qt: inject the core calls into the dialog as constructor arguments (e.g. `ImportDialog(..., build=build_plan, apply=apply_plan, open_fn=open_package, running_fn=kicad_running)`) so a test passes a fake `build` that blocks on a `threading.Event`; assert on `qtbot.waitUntil(lambda: ..., timeout=5000)` and use `qtbot.waitSignal`. Always `qtbot.addWidget(dialog)` and, in teardown, wait for workers (`qtbot.waitUntil(lambda: not dialog._busy())`) before the widget is destroyed. For Install tests use the real `apply_plan` against `custom_copy` (a tmp copy) with `backup_root=tmp_path` (inject `backup_root`) so nothing touches the checkout or `%LOCALAPPDATA%`.
Geometry backstops from UI-SPEC (60-char names at 900x600, no horizontal scrollbar) are offscreen widget-geometry assertions (`dialog.resize(900, 600)`, `widget.geometry()` containment, `scrollArea.horizontalScrollBar().isVisible()` false); manual UAT confirms.

### Sampling Rate
- **Per task commit:** the touched test file(s), e.g. `pytest tests/test_import_preview.py -x -q` (seconds).
- **Per wave merge:** quick run command above plus `tests/test_main_window.py tests/test_install_plan.py tests/test_importer_layering.py`.
- **Phase gate:** full suite green (about 2 min) before `/gsd-verify-work`, then the manual UAT: full UL-sample import into the real `Custom/` (placeholder block -> pick/type a library -> conflict handling -> install -> trees select the library -> tables added for a new library -> KiCad-running notice), at 100 % and, as an assumption check, 150 % scaling.

### Wave 0 Gaps
- [ ] `tests/test_import_preview.py`: rows, defaults equivalence, blocking reasons, diff text and truncation, carry-over
- [ ] `tests/test_install_options_clear.py` (or extend `tests/test_install_plan.py`): cleared semantics, Manufacturer fix, Value/MPN refusal, old tests unchanged
- [ ] `tests/test_table_add_entries.py`: byte-preservation of externals and unrelated managed entries, idempotence, missing file, read-only table
- [ ] `tests/test_import_dialog.py`, `tests/test_main_window_import.py`, `tests/test_settings_import.py`
- [ ] Register new importer module(s) in `tests/test_importer_layering.py::ALLOWED`
- [ ] A conftest fixture that injects fake core callables and an isolated QSettings (copy the autouse fixture from `tests/test_main_window.py`)
- Framework install: none (already present)

## Security Domain

`security_enforcement` is enabled (ASVS L1, block on high) [VERIFIED: .planning/config.json `"security_enforcement": true, "security_asvs_level": 1, "security_block_on": "high"`].

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | single-user local tool |
| V3 Session Management | no | — |
| V4 Access Control | partly | Only `Custom/` is writable: `apply_plan._preflight` refuses any op path outside `layout.custom_dir` (`install.path_outside_custom`, `applier.py:266-273`) |
| V5 Input Validation | yes | Planner validation of library/footprint/rename names (`sanitize_name`, `install.invalid_library`, `install.invalid_name`, `install.bad_rename`); zip/folder limits in `package.py`; UI adds only display-side escaping and does not weaken any of it |
| V6 Cryptography | no (integrity only) | SHA-256 via `hashlib` for freshness/integrity and display; no secrets |
| V12 Files/Resources | yes | Zips never extracted into the repo, staged outside it (`intake.staging_in_repo` guard); atomic writes and backups (`fsutil`) |

### Known Threat Patterns for this stack (trust boundaries this phase touches)

| Boundary / Pattern | STRIDE | Standard Mitigation (existing) | What Phase 5 must add |
|--------------------|--------|-------------------------------|------------------------|
| Untrusted vendor zip/folder (Downloads, drag-drop) -> `open_package` | Tampering, DoS | Phase 3: path traversal/absolute/symlink/reparse rejection, member/size/ratio caps, no extraction into the repo, 8 MiB / 1M-node parser caps | Call it only on a worker; accept exactly one dropped local path; never auto-open the newest zip; show Issues, do not eval anything |
| Package-derived strings rendered in the UI (member names, symbol/footprint names, Issue text, `Conflict.existing`) -> rich-text `QLabel`/`LogPanel`/tree | Spoofing, injection of markup/links | `LogPanel.log` escapes with `html.escape` | **Escape every vendor-derived string before putting it in a rich-text `QLabel`** (blocking-reason strip, badge, hints, banner, token line use `RichText` per UI-SPEC); use `Qt.TextFormat.PlainText` for labels showing vendor names; `QTreeWidgetItem` text is plain by default. Links in the strip must be internal ids (`linkActivated` payload), never URLs from the package. |
| Paths shown from the package/plan and the "Open folder" button | Elevation / unintended execution | — | `QDesktopServices.openUrl(QUrl.fromLocalFile(str(backup_dir)))` only for `InstallResult.backup_dir` (a folder created by the app under `fsutil.default_backup_dir()`), never for package-supplied paths; do not open files from the result list (double-click opens the in-app content view only) |
| Content view of package/target files | DoS | caps already in the planner | Cap displayed text (UI-SPEC: 5000 lines or 512 KiB) and read files with a byte cap; STEP/binary shows size + SHA-256 only, never decoded; hash large files in chunks on a worker |
| Files written into the repo (`Custom/`) | Tampering | `apply_plan`: containment check, stale-plan hash checks, backups, transactional rollback, post-write verify | Install exactly the latest plan (generation guard); never write from the UI; add WR-02 early refusal |
| `kicad-cli` subprocess | Elevation, DoS | No shell, fixed args, `creationflags=CREATE_NO_WINDOW`, timeout 60 s, temp folders outside repo (`kicad_cli.py`) | Run on a worker; pass only the `ToolContext` located by `detect_tools`; never put package text on a command line (it is not) |
| Lib-table write (`sym-lib-table`/`fp-lib-table`) and `kicad_common.json` | Tampering | `atomic_write_text`, backup before write, quote escaping (HARD-06), path-variable sync backup (HARD-03) | Add-only helper must reuse `_entry_text` (escaping) and the backup/atomic path; no write when the destination does not exist |
| Persisted `import/last_dir` | Tampering (low) | `QSettings` | Treat the stored value as untrusted: `Path(...).is_dir()` before use |
| Process listing (`tasklist.exe`) | — | absolute path under `SystemRoot`, no shell | Call on a worker |

No high-severity unmitigated threat identified; the one UI-introduced risk worth an explicit task is markup injection from vendor strings into `RichText` labels (Medium).

## Folded-in review items (where the touched code overlaps)

| Item | Source | Concrete change |
|------|--------|-----------------|
| `populate()` `_updating` stuck | 02-UI-REVIEW fix 1 | Wrap body of `LibraryTableWidget.populate` (`library_table.py:65-158`) in `try/finally`; the new `reveal()` uses the same guard. Test: patch `QTreeWidgetItem` creation to raise and assert later `itemChanged` is still handled. |
| Status column off-screen | fix 2 | Columns per UI-SPEC (Name 240, Source 100, Linked Footprints `Stretch`, Status `ResizeToContents`); tooltip on the Status cell. |
| Help text | fix 3 | Add Collision, `Ctrl+Shift+R`, `Ctrl+I`, import flow, add-only tables to `help_dialog.py` (HTML string sections `<h2>...`; existing tests may assert some wording: run `tests/` help tests). |
| Select All / Deselect All during scan | review | Add `_select_all_btn`/`_deselect_all_btn` to `_set_scan_running` (`main_window.py:276-281`). |
| Shared amber | review | New `widgets/theme.py` `AMBER = "#8A5200"`; replace `#CC7700` in `log_panel.COLORS["warning"]`, two `QColor("#CC7700")` in `library_table.py`, the help span. Any existing test asserting the old hex must be updated. |
| WR-02 | Phase 4 | In `build_plan`, when creating a library and `layout.symbols_dir` (or `footprints_dir`) is missing, refuse with ERROR `Cannot create {Lib}: the Custom/Symbols folder is missing. Check the Custom submodule is checked out.` before any write. |
| WR-04 | Phase 4 | Already satisfied by the dialog owning the Package; add the wait-then-close ordering test. |
| WR-06 | Phase 4 | Pitfall 5. |
| IN-04 | Phase 4 | UI never passes blank choices. |
| IN-01 / IN-05 | Phase 4 | Optional; skip unless trivial. |

## Sources

### Primary (HIGH confidence, read or executed this session)
- Repo source: `importer/plan.py`, `planner.py`, `applier.py`, `package.py`, `detect.py`, `candidate.py`, `suggest.py`, `layout.py`, `kicad_cli.py`, `verify.py` (headers/codes), `kicad_process.py`, `table_generator.py`, `library_table.py`, `log_panel.py`, `backup_dialog.py`, `main_window.py`, `settings.py`, `models.py`
- Tests/config: `tests/conftest.py`, `tests/test_layering.py`, `tests/test_importer_layering.py`, `tests/test_main_window.py` (head), `tests/test_install_plan.py` (WR-05 section), `pyproject.toml`, `requirements*.txt`, `.planning/config.json`
- Planning docs: `05-CONTEXT.md`, `05-UI-SPEC.md`, `REQUIREMENTS.md`, `STATE.md`, `04-REVIEW-DISPOSITION.md`, `02-UI-REVIEW.md`
- Executed in `env/`: full pytest run (1345 passed, 5 skipped, 106.30 s); `QStandardPaths` Download location; thread-signal delivery and `activeModalWidget` experiment; `difflib` timing

### Secondary (MEDIUM)
- Qt window-modality rules from general Qt documentation knowledge [ASSUMED where noted]

### Tertiary (LOW)
- none

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (nothing new; versions read from pinned files and installed dist-info)
- Architecture: HIGH for core-API facts and hook points (source read); MEDIUM for Qt modality interaction (A1) and drop-event construction (A2)
- Pitfalls: HIGH (1, 2, 3, 4, 5, 6 derived directly from code); MEDIUM (7, 11)

**Research date:** 2026-10-20
**Valid until:** 2026-11-19 (stable; re-check if Phase 4 modules change before planning)
