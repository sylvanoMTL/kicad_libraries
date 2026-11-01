# Phase 12: Import Flow Fixes and Case-Sensitive Re-test - Context

**Gathered:** 2026-11-01
**Status:** Ready for planning

<domain>
## Phase Boundary

The import flow's open v1.0 review defects are fixed, the Help dialog and conflict rows follow the theme, and case-twin rollback is proven on a real case-sensitive folder:
- The post-install table step says "already listed" only when the tool-owned entry really points at the installed library, and it never writes tables when Destination is empty (REV-01, REV-02).
- A one-off conflict build never overlaps Install, and the GUI thread never waits on a kicad-cli call (REV-03, REV-04).
- The `kicad_common.json` confirm says when KiCad is open before anything is written, and the confirmed write starts from the file's current content (REV-05).
- `help_dialog.py` and `conflict_row.py` use `theme.py` tokens only (UI-01).
- Case-twin rollback and overwrite are re-tested on a case-sensitive folder (VER-02, backlog 999.2, deferred Phase 4 UAT Test 3).

Requirements: REV-01, REV-02, REV-03, REV-04, REV-05, UI-01, VER-02. Sources: `05-REVIEW.md` WR-01, WR-02, WR-03, WR-05, WR-06; `05-UI-REVIEW.md` (Color, Typography, Spacing pillars); `04-UAT.md` Test 3.

Out of this phase:
- Phase 5 IN-01..IN-06 and Phase 4 IN-01/02/03/05 are not in v2.0. Phase 4 WR-04 is deferred as REF-01.
- The open Phase 10 and Phase 11 review findings (10-REVIEW-DISPOSITION, 11-REVIEW-DISPOSITION) are not part of this phase.
- Table descriptions and the chooser setup (TBL-01, TBL-02) belong to Phase 13. TBL-02 will reuse the `kicad_common.json` write corrected here.

</domain>

<decisions>
## Implementation Decisions

### Library name already taken (REV-01)
- **D-01:** **A stale tool-owned entry is repointed.** When a table holds a tool-owned entry (URI contains `${KICAD_LIB_GITHUB}/`) with the installed library's nickname, but its path points at a file or folder that no longer exists (a moved or renamed library), the table step rewrites that entry's URI to the installed library's `rel_path`. The table is backed up first, as for any table write. The Result row reads like "Updated: Atomic_Sensor_Motion now points at Custom/...". No dead entry is left behind.
- **D-02:** **A live clash only warns.** When the tool-owned entry with that nickname points at another library that still exists (e.g. `WurthElektronik/.../IC_X.kicad_sym` while `Custom/.../IC_X` was installed), the table is left unchanged. An amber Result row and a WARNING log line say e.g. "Not added: the name IC_X already points at WurthElektronik/...; KiCad still loads that library. Rename one of them." This is the 05-REVIEW WR-01 fix (`table.path_clash` WARNING, return "skipped"), which `_tables_outcome` already shows as a warning row.
- **D-03:** **"Already listed" only for a real match.** The step reports "already listed" (INFO) only when the tool-owned entry's path tail equals the expected `rel_path`. On Windows, a path that differs only by letter case counts as the same path.
- **D-04:** **The same rule applies to installs into an existing library.** Today the existing-library branch of `MainWindow._finish_post_install` only reads the tables and hints "Press Generate Tables to add it". A stale tool-owned entry under that nickname is now repointed too (D-01), and a live clash warns (D-02). A library missing from the tables entirely keeps today's "Press Generate Tables" hint: an existing library's install still never adds a new entry (Phase 5 D-17).
- **D-05:** **Hand-added entries are never edited.** An entry without the managed marker that uses the nickname keeps today's `table.external_clash` WARNING, stale or not. Only the wording becomes plainer, e.g. "Not added: IC_X is already used by an entry you added by hand (<path>); KiCad keeps loading that one."
- D-01..D-05 apply to both `sym-lib-table` and `fp-lib-table`, including the shared `Atomic_Footprints` entry.

### Waiting on kicad-cli (REV-03, REV-04)
- **D-06:** **The Finishing state.** When Change..., opening another package, or closing the dialog (Close button, window X, Escape) would have to wait for a running build or worker, the GUI thread never calls `worker.wait()`. Instead:
  - the dialog greys out and shows a wait cursor and "Finishing the preview...";
  - the window still moves and repaints;
  - the requested action runs by itself once the last relevant worker ends (from its `finished` handler), with no second click.

  This replaces `_wait_builds()` (`import_dialog.py` ~1223, ~3153) and the waits in `_shutdown` (~3191) and `_reap` (~1276), so the package lifetime stays protected without blocking.
- **D-07:** **There is a way out.** The Finishing strip has a **Cancel** button. Cancel drops the pending action and restores the dialog's previous state (for a close, the dialog stays open). After 10 s the strip adds "kicad-cli is slow to respond (it gives up after 60 s)". kicad-cli is not killed: its existing 60 s timeout (`cli_timeout`) still ends it.
- **D-08:** **Install is disabled while a one-off build runs.** `_updating()` counts `self._oneoff`, so Install greys out and the existing "Updating..." marker shows while a one-off conflict build reads the target library. Install comes back by itself when the build ends. `_pump_builds` holds every queued build and one-off job while `is_installing()`, and `_on_install_done` / `_on_install_failed` call `_pump_builds()` so held jobs resume (the 05-REVIEW WR-03 fix).

### KiCad running / file changed (REV-05)
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

### Case-sensitive re-test (VER-02)
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Review findings being fixed
- `.planning/milestones/v1.0-phases/05-import-ui-and-post-install/05-REVIEW.md`: WR-01 (already listed), WR-02 (empty Destination), WR-03 (one-off vs Install), WR-05 (GUI waits on kicad-cli), WR-06 (`kicad_common.json` stale content and KiCad-running gate), with file and line pointers (v1.0 line numbers; the code has moved since) and suggested fixes
- `.planning/milestones/v1.0-phases/05-import-ui-and-post-install/05-REVIEW-DISPOSITION.md`: set each finding's disposition when fixed
- `.planning/milestones/v1.0-phases/05-import-ui-and-post-install/05-UI-REVIEW.md`: Color, Typography and Spacing findings for `help_dialog.py` and `conflict_row.py`
- `.planning/milestones/v1.0-phases/04-plan-and-install-core/04-UAT.md`: Test 3 (case-sensitive rollback and overwrite), skipped and deferred 2026-10-20

### Prior phase context
- `.planning/milestones/v1.0-phases/05-import-ui-and-post-install/05-CONTEXT.md`: the threading rule ("long work runs on a `QThread` and never on the GUI thread"; the package stays open until `apply_plan` returns), D-15/D-16 (Result view and post-install rescan), D-17 (post-install adds only the new library's own entries), D-18 (KiCad-running notice after install)
- `.planning/milestones/v1.0-phases/04-plan-and-install-core/04-CONTEXT.md`: the install transaction and rollback contract (INST-07); its D-03 is the "GUI never blocks" reference used by `import_dialog.py`'s docstring
- `.planning/milestones/v1.0-phases/05-import-ui-and-post-install/05-UI-SPEC.md`: the theme contract (colours, 9/10/12 pt, spacing scale) that UI-01 enforces

### Project docs
- `CLAUDE.md`: KiCad path variables, generated table format, Git workflow
- `tests/README.md`: expected skips (add the case-sensitive ones); the suite must not write to or depend on the live `Custom/`
- `.planning/REQUIREMENTS.md`: REV-01..REV-05, UI-01, VER-02

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kicad_lib_manager/table_generator.py`: `_add_entry` (~303, the "listed" shortcut at ~343), `add_library_entries` (~369), `table_info` / `TableInfo.managed` (~472), `_tail`, `_is_managed`, `_entry_text`, `fsutil.backup_file`, `apply_edits`.
- `kicad_lib_manager/main_window.py`: `_finish_post_install` (~795; new-library branch ~834, existing-library branch ~850), `_tables_outcome`, `_confirm_path_var_changes` (~1048), `_sync_path_vars` (~1066), `_on_generate` (~1072), `_set_import_status`.
- `kicad_lib_manager/library_scanner.py`: `sync_kicad_path_vars` (~147; confirm at ~249, running check at ~263), `_only_vars_changed`, `_path_var_refusal`, `_prune_backups`.
- `kicad_lib_manager/kicad_process.py`: `kicad_running()`, which shells out to `tasklist` with a 5 s timeout. kicad-cli is deliberately not counted.
- `kicad_lib_manager/widgets/import_dialog.py`: `_wait_builds` (~1452), `_reap` (~1268), `_pump_builds` (~2506), `_start_oneoff`, `_on_oneoff_done`, `is_installing` (~2574), `_updating` (~2577), `_sync_updating`, `_busy_timer`, `_on_install_done` / `_on_install_failed` (~2774/2790), `_shutdown` (~3177), `done`, `closeEvent`, `keyPressEvent`.
- `kicad_lib_manager/importer/applier.py`: `_drop_twin` (~72), `_rollback` (~80), the write step (~488-506) that writes `op.path` and records `listed_path` for undo, `_current_bytes`, `_still_fresh`.
- `kicad_lib_manager/importer/plan.py`: `FileOp.listed_path` (the on-disk spelling when it differs by case).
- `kicad_lib_manager/widgets/theme.py`: `AMBER`, `AMBER_TINT`, `ACCENT`, `LINK`, `SURFACE`, `SURFACE_HEADER`, `BORDER`, `SP_*`, `HEADING_PT`, `DISPLAY_PT`, `MONO_PT`.
- `tests/test_install_apply.py`: `test_rollback_restores_case_twin` (~695), the `_drop_twin` unit tests with a mocked listing (~810-833), `hand_layout`, `snapshot`, `_flaky_writes`, and the INST-07 fault matrix.

### Established Patterns
- Qt-free services return `Issue` lists routed by `Severity`. Errors go to the log and the Result view, never to message boxes. The path-variable confirm is the one sanctioned dialog.
- Background work runs on the import dialog's `TaskWorker`. The GUI never blocks (Phase 4 D-03), which this phase finally enforces for shutdown and Change....
- Finished worker objects are never `deleteLater`'d early (a crash, see `_reap`'s docstring). The Finishing state must keep that rule.
- Plain-language UI: no raw KiCad field names in user-facing text.

### Integration Points
- `table_generator._add_entry` gains the path comparison, the stale-entry repoint and the live-clash warning. The existing-library branch of `_finish_post_install` needs a table-write path for the repoint (D-04).
- `sync_kicad_path_vars` gains the re-read and merge, plus a way to report "changes differ, ask again". Its `confirm` callback in `main_window.py` grows the three-button KiCad-open variant, fed by a running check made off the GUI thread.
- The import dialog gains a Finishing strip (with Cancel and the 10 s note) and a "pending action" slot, run from worker `finished` handlers.
- The applier and planner move the overwrite target and the footprint model reference to the on-disk spelling (D-14).

</code_context>

<specifics>
## Specific Ideas

- Stale repoint row: "Updated: Atomic_Sensor_Motion now points at Custom/...".
- Live clash row: "Not added: the name IC_X already points at WurthElektronik/...; KiCad still loads that library. Rename one of them."
- Hand entry row: "Not added: IC_X is already used by an entry you added by hand (<path>); KiCad keeps loading that one."
- Finishing strip: "Finishing the preview..." with Cancel; after 10 s, "kicad-cli is slow to respond (it gives up after 60 s)".
- KiCad-open dialog: names the programs, "Close KiCad, then press Retry"; buttons Retry (default) / Change anyway / Not now.
- After Change anyway: "KiCad is open (kicad, eeschema); it may undo these paths when it exits. If they revert, close KiCad and press Generate Tables."
- VER-02 UAT: give the owner the exact command (the env/ python path and the test selection) and what "pass, not skip" looks like, with full setup steps kept concise (owner preference).

</specifics>

<deferred>
## Deferred Ideas

None. The discussion stayed within phase scope. A startup check that notices path variables reverted by KiCad was offered and declined (D-12), not deferred.

</deferred>

---

*Phase: 12-import-flow-fixes-and-case-sensitive-re-test*
*Context gathered: 2026-11-01*
