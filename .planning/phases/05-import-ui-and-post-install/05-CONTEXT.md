# Phase 5: Import UI and Post-Install - Context

**Gathered:** 2026-10-20
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase adds the GUI on top of the Phase 4 core (`build_plan` / `apply_plan`). From the Library Manager the user:

1. opens a vendor package from an "Import Part..." action, by dropping a zip or folder on the main window, or from the newest zip in Downloads;
2. picks items when the package holds several symbols, footprints or models;
3. edits the target library, the footprint name and the fields in a live preview that is exact;
4. resolves each conflict;
5. clicks Install, which runs on a worker thread.

Afterwards the main window rescans and checks the new or updated library. When a library was created, the library tables are regenerated. When KiCad is running, the user is told to reopen its library editors.

Requirements: INTK-07, PREV-01..07, POST-01, POST-02, POST-05, UX-01, UX-02.

Not in this phase:
- the git commit step (Phase 6). Phase 5 must leave a place for it in the result view (D-15).
- SnapEDA and SamacSys adapters (Phase 7).
- SVG previews (v2 PREV2-01).

</domain>

<decisions>
## Implementation Decisions

### Carried forward (locked)
- Preview and install use the same `InstallPlan`. The preview renders the plan object, and Install calls `apply_plan` on that same plan, the most recent one built (PREV-07). Phase 4 designed the plan to be previewable (`plan.py` docstring).
- **Conflicts:**
  - Every conflict blocks until it is resolved. The choices are `overwrite`, `rename` (a free `_2` name is suggested and can be edited) and `skip`.
  - Nothing is pre-selected, and there is no "overwrite all" (Phase 4 D-05, D-06).
  - Skip means "keep the existing item and link it" (D-09).
  - Case-only clashes between files count as conflicts (D-10).
- Install is refused while `importer.suggest.placeholder_tokens(library_name)` is non-empty (Phase 3 D-04, ROADMAP contract).
- The `Package` must stay open until `apply_plan` returns (WR-04). The dialog owns the package for its whole lifetime and closes it when the dialog closes.
- Every scan goes through `MainWindow._start_scan`, which refuses while a worker exists (Phase 2 HARD-05).
- Services return `Issue` lists and never raise for expected failures. Routing is by `Severity`. Errors go to the log panel, not to message boxes (conventions).
- Long work runs on a `QThread` and never on the GUI thread. That includes `open_package`, `detect_candidate`, `build_plan` (which may call kicad-cli) and `apply_plan` (Phase 4 D-03).
- Field roles, D-11..D-15: `Manufacturer` and `MPN` are always filled (D-11), the model is named `<MPN>.<ext>`, and `ki_fp_filters` holds the installed footprint names exactly.

### Dialog flow and entry (UX-01, UX-02, INTK-07)
- **D-01: One window-modal import dialog with a split view.**
  - The left pane holds the choices: package, items, target library, footprint name and fields.
  - The right pane holds the live preview.
  - The bottom row holds the Install button and the blocking-reason status line.
  - There is no wizard and no panel inside the main window.
- **D-02: The start step offers the newest Downloads zip.** When no package is loaded, the dialog shows:
  - "Newest in Downloads: `<name>` (`<age>`) [Open]";
  - next to it, **Browse zip...** and **Browse folder...**, which open in the last-used import folder.

  The last-used folder is persisted through new `settings.py` helpers (`load_*` / `save_*`, key e.g. `import/last_dir`). The package is never auto-opened. A **Change...** control returns to package selection.
- **D-03: Dropping onto the main window opens the dialog with the package loaded.** This works for a `.zip` or a folder. Drops and "Import Part..." are disabled while a scan runs. For other drops (wrong file type, several files), Claude decides the handling: refuse them, with a log line.
- **D-04: The item picker is inline in the left pane (INTK-07).**
  - **Symbol:** a combo box. Exactly one is chosen, and its `extends` parent comes along automatically (D-16, D-17).
  - **Footprints:** a checklist. The first checked footprint is the linked one, and the user can make another the linked one. All checked footprints go into `ki_fp_filters`.
  - **Model:** a combo box with a "No model" entry.
  - A single item shows as a plain label.
  - Changing a pick rebuilds the plan.
  - The UI never passes a blank choice to `InstallOptions` (resolves Phase 4 IN-04).
- **D-05: A refused or empty package keeps the dialog open on the start step.** This covers a hostile zip, a KiCad 5-only package, and detection finding nothing.
  - The dialog lists the package's ERROR and WARNING reasons, and the same Issues go to the main log.
  - The user can pick another file.
  - This resolves Phase 4 **WR-06**: when no candidate is found, `package.issues` must still reach the UI.

### Live preview (PREV-01, PREV-06, PREV-07)
- **D-06: The plan rebuilds automatically.**
  - About 300 ms after typing stops, and immediately when a combo box or checkbox changes.
  - Rebuilds run on a worker thread. A newer edit supersedes a stale rebuild; its result is discarded.
  - While a rebuild is pending or running, the preview shows "Updating..." and Install is disabled, so a stale plan can never be installed.
  - kicad-cli output is cached so repeated rebuilds don't re-run the CLI. `importer/kicad_cli.py` already has `_cache_key` / `clear_cache`; check that it covers this case.
- **D-07: The preview is a sectioned `QTreeWidget`.** Sections:
  - **Files:** `+` new / `~` modified / `=` unchanged, with the repo-relative path.
  - **Renames:** old → new.
  - **Path rewrites:** the Footprint field `<Lib>:<FP>`, the model path `${CUSTOM_3DMODEL_DIR}/...` and `ki_fp_filters`.
  - **Format:** source → target version, and the kicad-cli action (normalise / as-is with a warning / not found / refused as newer).
  - **Conflicts.**
  - **Issues**, coloured by severity, including "no 3D model found" (INTK-08).

  A rebuild re-renders the tree and keeps the expand state and scroll position. Changed rows are not flashed or highlighted.
- **D-08: Double-clicking a file row opens a read-only content view.**
  - A new text file shows its planned text.
  - A modified file (e.g. `.kicad_sym`) shows a unified diff (`difflib`) of the current file against the planned bytes.
  - A STEP or binary file shows its size and SHA-256.
  - A conflict row opens the same view, existing item against incoming.
- **D-09: The status line explains why Install is disabled.**
  - It lists every blocking reason: unresolved conflicts, placeholder tokens, ERROR Issues, an empty Value or MPN, and "Updating...".
  - Each reason is clickable and focuses the matching field or conflict row.
  - The offending field gets an amber border. Use one shared amber constant; the Phase 2 UI review suggests `#8A5200` for contrast.
- **D-10: Install runs on a worker with progress and no Cancel.**
  - Steps from `apply_plan`'s `progress` callback drive a progress bar and step text.
  - All inputs are locked, and closing the dialog is blocked until the install finishes.
  - There is no Cancel: failures already roll back on their own (Phase 4 D-18/D-19), and an interrupt would add rollback risk.

### Editing and conflicts (PREV-02..05, LIB-01/02 UI side)
- **D-11: The target library is an editable combo box with a badge.**
  - It is pre-filled with the suggestion from `suggest_library` (e.g. `IC_SubCategory_TI`).
  - The dropdown lists the ranked `alternatives` first, then every `Custom/` library, read fresh via `layout.list_existing_libraries`.
  - A badge shows "existing" or "new – creates .kicad_sym + .pretty".
  - Low-confidence tokens and placeholder tokens are highlighted in amber.
- **D-12: Each conflict gets its own row with three toggle buttons.**
  - The row shows the kind, the name and where the item already exists, with **Overwrite / Rename / Skip** buttons. None is selected at first.
  - Rename reveals an editable name field pre-filled with `Conflict.suggested_name`.
  - A one-line hint explains the chosen action (e.g. "Skip – keep the existing footprint and link it").
  - Double-clicking the row opens the existing-against-incoming view (D-08).
  - There is no overwrite-all.
- **D-13: Fields are pre-filled, and an emptied field means "clear" (this settles the WR-05 decision Phase 4 deferred).**
  - Value, Datasheet, Description, Manufacturer and MPN start with the value the plan would write: the vendor value, or the D-11 default for Manufacturer and MPN.
  - What the user sees is what gets written. A field the user empties installs an empty value.
  - A ↺ button on each field restores its default.
  - **Value and MPN cannot be emptied.** Install is blocked with a reason, because MPN names the 3D model file.
  - **Phase 4 change needed:** `InstallOptions` currently turns `""` into `None`, which means "keep the vendor value". It must be able to tell "explicitly empty" from "not set", for example with a sentinel or a set of cleared fields. Keep the WR-05 behaviour for callers that don't opt in, and update the `InstallOptions` docstring.
  - — **Reversibility:** reversible. The change is local to `InstallOptions` and `_edit_symbol` in the planner.
- **D-14: The footprint name is editable (PREV-02); the symbol name is read-only.**
  - The footprint name defaults to the vendor name, sanitised (e.g. `DQK0006B`).
  - The symbol name is shown as vendor → sanitised (LIB-03) and changes only through a conflict's Rename.
  - The displayed Footprint field `<Lib>:<FP>` follows every library or footprint-name edit (PREV-03). It is read from the rebuilt plan, never computed separately in the UI.
- **D-14a: Conflict choices are kept by conflict key across rebuilds.**
  - The keys are `symbol:<lib>:<name>`, `footprint:<lib>:<name>` and `model:<file>`, as built in `planner.py`.
  - A choice stays while its key is still in the new plan.
  - A conflict that disappears drops its choice, and a new conflict starts unresolved.
  - Switching library therefore never carries an Overwrite across to another library's item.
- **D-14b: Picking a different symbol resets the field edits.**
  - Every field reloads from the new symbol's defaults.
  - The footprint name resets when the linked footprint changes.
  - Changing only the target library keeps all field edits.

### After install (POST-01, POST-02, POST-05)
- **D-15: The dialog switches to a result view in place.**
  - On success it shows the files written, the warnings (pin/pad mismatch POST-04, name already elsewhere POST-03, no 3D model), the KiCad-running notice and the backup folder, with a Close button.
  - **Phase 6 adds its commit step to this view.** Leave a clear slot or hook for it, and keep the `InstallResult` (`touched`, `vendor`, `source`) available there.
  - On failure the dialog returns to the preview with the rollback reasons at the top, and the user can fix the problem and retry.
  - The full result also goes to the main log.
- **D-16: The post-install rescan starts when the result view appears.**
  - It goes through `_start_scan`, and the trees update behind the dialog.
  - After the scan, the installed library's symbol and footprint rows are checked, expanded, scrolled into view and made current in both trees.
  - The rest of the selection is preserved (HARD-07).
  - If an existing library got the part but isn't in the current tables, a WARNING says to press Generate.
- **D-17: Tables are regenerated automatically for a new library, adding entries only (POST-02).**
  - Only when the install created a library: after the rescan, the new library's entries are added to `sym-lib-table` / `fp-lib-table` in the main window's current destination.
  - This uses the normal backup and merge path (`write_tables`).
  - Every other entry stays exactly as it is on disk. Selection changes in the main tree that haven't been generated yet are **not** written.
  - The selection passed to the merge is therefore "the managed entries currently in the tables, plus the new library", not the tree's current selection.
  - The `kicad_common.json` path-variable sync follows the same rule as Generate.
- **D-18: The KiCad-running notice (POST-05).** After a successful install, `kicad_process.kicad_running()` is checked (off the GUI thread or with its 5 s timeout respected). If KiCad is running, the result view and the log say "Reopen KiCad's Symbol/Footprint editors to see `<Lib>`".
- **D-19: Modality and the busy state.**
  - The dialog is window-modal.
  - "Import Part..." and drops are disabled while a scan runs, joining the `_set_scan_running` controls.
  - Generate, Rescan and Set KiCad Path can't be reached while the dialog is open.

### Claude's Discretion
- **Module layout.** For example:
  - `widgets/import_dialog.py`: the dialog, start step, left pane, preview tree and result view;
  - a small widget module for the preview tree or the conflict row;
  - `QThread` workers for open/detect, rebuild and install, placed beside `ScanWorker` or in the dialog module.
- The keyboard shortcut for "Import Part..." (e.g. `Ctrl+I`), the menu placement, and a toolbar button if one fits.
- **How "newest zip in Downloads" is found.** On Windows, the Downloads Known Folder or `Path.home() / "Downloads"`; on other OSes, `Path.home() / "Downloads"`. The age shown, and whether a stale zip (e.g. over 7 days old) is still offered.
- The exact debounce interval (about 300 ms) and how a superseded rebuild is discarded (generation counter).
- How the add-only table merge is built: a new helper in `table_generator.py`, or a selection derived from `table_info` / existing entries plus the new library.
- How `difflib` output is shown (monospace `QPlainTextEdit`), and the size cap for very large diffs.
- **Folding in the Phase 2 UI-review fixes where the touched code overlaps.** These are recommended; the STATE.md blocker says to fold them into Phase 5:
  - `populate()` `_updating` needs try/finally;
  - the Symbols Status column is off-screen at the default size;
  - the help text is missing Collision and Ctrl+Shift+R;
  - Select All and Deselect All are enabled during a scan;
  - the shared amber colour constant.

  Also add "Import Part..." and the import flow to the help dialog.
- **Phase 4 review items that the UI exposes.** **WR-02**: creating a library when `Custom/Symbols` is missing fails late; give a clear early refusal. IN-01 and IN-05 are optional.
- Test strategy: pytest-qt offscreen tests for the dialog state machine (blocking reasons, rebuild supersession, conflict-choice carry-over, the WR-05 clear semantics), plus a manual UAT of the full UL-sample import into the real `Custom/`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` § "Phase 5: Import UI and Post-Install": goal, success criteria 1–5, Phase 3 D-04 contract
- `.planning/REQUIREMENTS.md`: INTK-07, PREV-01..07, POST-01/02/05, UX-01/02 (GIT-* are Phase 6)
- `.planning/PROJECT.md`: Key Decisions table (WR-05 "Phase 5 clear option" row)

### Prior phase decisions
- `.planning/phases/04-plan-and-install-core/04-CONTEXT.md`: D-03 (CLI never on the UI thread), D-05..D-10 (conflicts), D-11..D-17 (fields and items per install), D-18/D-19 (rollback, backups)
- `.planning/phases/04-plan-and-install-core/04-REVIEW-DISPOSITION.md`: open items WR-02, WR-04, WR-06, IN-01..IN-05 (WR-06 and IN-04 are resolved by D-05 and D-04 here)
- `.planning/phases/03-package-intake-and-naming/03-CONTEXT.md`: D-01..D-04 (suggestion, confidence, placeholders), D-15/D-16 (sanitising, case clash)
- `.planning/phases/02-hardening-existing-code/02-UI-REVIEW.md`: UI fixes to fold in, and the amber contrast value

### Codebase maps
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONVENTIONS.md`: layering (widgets don't import `main_window`), `QThread` workers, `blockSignals` and the `_updating` guard, settings only through `settings.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `importer/package.py` `open_package(path, repo_root, progress)` gives a `Package` (a context manager, with `.refused` and `.issues`). `importer/detect.py` `detect_candidate(package)` gives `(ImportCandidate | None, issues)`.
- `importer/planner.py`:
  - `build_plan(candidate, options, layout, tools, *, package_issues, progress)` gives an `InstallPlan`;
  - `detect_tools(...)` gives a `ToolContext` (kicad-cli path, stock symbols dir);
  - `suggest_free_name`.
- `importer/plan.py`: `InstallOptions`, `Resolution`, and `InstallPlan`, whose properties are `blocked`, `unresolved_conflicts`, `is_noop`, `new_library`, `symbol_lib_path`, `pretty_path`, `ops`, `renames`, `conflicts`, `issues`, `source_version` / `target_version` / `normalised`. Also `Conflict` (`key`, `kind`, `name`, `existing`, `suggested_name`) and `FileOp` (`kind`, `path`, `data`, `base_sha256`).
- `importer/applier.py` `apply_plan(plan, *, backup_root, progress)` gives an `InstallResult` (`ok`, `touched`, `issues`, `backup_dir`, `vendor`, `source`).
- `importer/suggest.py`: `suggest_library(meta, existing)` gives a `LibrarySuggestion` (`name`, per-token `TokenChoice.confident`, `placeholders`, `alternatives`, `matches_existing`), plus `placeholder_tokens(name)`.
- `importer/layout.py`: `list_existing_libraries(layout)` and `RepoLayout`.
- `importer/naming.py`: `sanitize_name` and `sanitize_filename` give a `NameResult` (original vs sanitised).
- `importer/kicad_cli.py`: there is already a result cache (`_cache_key`, `clear_cache`).
- `kicad_process.kicad_running()` returns the names of running KiCad processes (stdlib, 5 s timeout).
- `table_generator.write_tables(dest, symbol_libs, footprint_libs)` and `table_info(path)`.
- `widgets/log_panel.py` `LogPanel`, and `MainWindow._log_issues(issues)`.

### Established Patterns
- `ScanWorker(QThread)` with `progress` / `finished` / `error` signals, and a broad `except` only at the thread boundary. The import workers should follow it.
- `_set_scan_running(running)` toggles the busy controls; add the Import action and drop acceptance to it.
- `_start_scan()` is the only scan entry point. `_on_scan_finished` and `_reapply_selection` keep the selection across rescans (HARD-07). The post-install "check this library" step hooks in after `_reapply_selection`.
- Qt enums are fully qualified. Programmatic changes are wrapped in `blockSignals` or `self._updating`, with try/finally.
- Persistent state only through the `settings.py` helpers, with slash-separated keys.

### Integration Points
- `MainWindow._build_menu`: add "Import Part..." to the File menu, with a shortcut.
- `MainWindow`: `setAcceptDrops(True)` plus `dragEnterEvent` / `dropEvent` that accept one `.zip` or a directory.
- `MainWindow`: a post-install callback that starts the rescan, selects the library, and runs the add-only table write for a new library against `self._dest_combo.currentText()`.
- `widgets/help_dialog.py`: document the import flow.

</code_context>

<specifics>
## Specific Ideas

- The UL sample (`downloaded_examples/ul_CSD85301Q2.zip`) is the reference walkthrough. The suggestion is `IC_SubCategory_TI` (low confidence, a placeholder), so Install starts blocked until the user picks or types a real name, e.g. an existing `IC_*_TI` library or a new `Transistor_MOSFET_TI`. The footprint is `DQK0006B`, the model `DLV0006A.stp` → `CSD85301Q2.stp`, and the Footprint field becomes `<Lib>:DQK0006B`.
- Approved layout (the left/right split from the discussion):

```
┌ Import Part — ul_CSD85301Q2.zip ─────────────────────────┐
│ Package: ul_CSD85301Q2.zip  (Ultra Librarian) [Change…] │
├──────────────────────────┬──────────────────────────────┤
│ Items / Target library / │ Preview (sectioned tree)     │
│ Footprint name / Fields  │ Files · Renames · Rewrites · │
│ Conflicts (rows)         │ Format · Conflicts · Issues  │
├──────────────────────────┴──────────────────────────────┤
│ ⚠ <blocking reasons, clickable>             [Install]   │
└─────────────────────────────────────────────────────────┘
```

- Conflict row shape: `footprint DQK0006B exists in IC_MOSFET_TI.pretty  ( ) Overwrite ( ) Rename [DQK0006B_2] ( ) Skip — keep & link existing`.

</specifics>

<deferred>
## Deferred Ideas

None. The discussion stayed within the phase scope. The git commit from the result view is already Phase 6 (D-15 leaves a place for it).

</deferred>

---

*Phase: 05-import-ui-and-post-install*
*Context gathered: 2026-10-20*
