---
phase: 05-import-ui-and-post-install
verified: 2026-10-22T14:00:00Z
status: human_needed
score: 5/5 roadmap truths verified (plus 6/6 supporting plan truths); 0 behavior-unverified
covered_files:
  - ".planning/phases/05-import-ui-and-post-install/05-01-PLAN.md"
  - ".planning/phases/05-import-ui-and-post-install/05-01-SUMMARY.md"
  - ".planning/phases/05-import-ui-and-post-install/05-02-PLAN.md"
  - ".planning/phases/05-import-ui-and-post-install/05-02-SUMMARY.md"
  - ".planning/phases/05-import-ui-and-post-install/05-03-PLAN.md"
  - ".planning/phases/05-import-ui-and-post-install/05-03-SUMMARY.md"
  - ".planning/phases/05-import-ui-and-post-install/05-04-PLAN.md"
  - ".planning/phases/05-import-ui-and-post-install/05-04-SUMMARY.md"
  - ".planning/phases/05-import-ui-and-post-install/05-05-PLAN.md"
  - ".planning/phases/05-import-ui-and-post-install/05-05-SUMMARY.md"
  - ".planning/phases/05-import-ui-and-post-install/05-06-PLAN.md"
  - ".planning/phases/05-import-ui-and-post-install/05-06-SUMMARY.md"
  - ".planning/phases/05-import-ui-and-post-install/05-07-PLAN.md"
  - ".planning/phases/05-import-ui-and-post-install/05-07-SUMMARY.md"
  - ".planning/phases/05-import-ui-and-post-install/05-08-PLAN.md"
  - ".planning/phases/05-import-ui-and-post-install/05-08-SUMMARY.md"
  - ".planning/phases/05-import-ui-and-post-install/05-09-PLAN.md"
  - ".planning/phases/05-import-ui-and-post-install/05-09-SUMMARY.md"
  - ".planning/phases/05-import-ui-and-post-install/05-10-PLAN.md"
  - ".planning/phases/05-import-ui-and-post-install/05-10-SUMMARY.md"
  - ".planning/phases/05-import-ui-and-post-install/05-11-PLAN.md"
  - ".planning/phases/05-import-ui-and-post-install/05-11-SUMMARY.md"
  - "kicad_lib_manager/importer/content.py"
  - "kicad_lib_manager/importer/downloads.py"
  - "kicad_lib_manager/importer/form.py"
  - "kicad_lib_manager/importer/plan.py"
  - "kicad_lib_manager/importer/planner.py"
  - "kicad_lib_manager/importer/preview.py"
  - "kicad_lib_manager/library_scanner.py"
  - "kicad_lib_manager/main_window.py"
  - "kicad_lib_manager/settings.py"
  - "kicad_lib_manager/table_generator.py"
  - "kicad_lib_manager/widgets/conflict_row.py"
  - "kicad_lib_manager/widgets/content_view.py"
  - "kicad_lib_manager/widgets/help_dialog.py"
  - "kicad_lib_manager/widgets/import_dialog.py"
  - "kicad_lib_manager/widgets/import_result.py"
  - "kicad_lib_manager/widgets/library_table.py"
  - "kicad_lib_manager/widgets/preview_tree.py"
  - "kicad_lib_manager/widgets/theme.py"
covered_digest: "v3:sha256:e3d8bfe1e4bac2d40dcc6970b3261d8f3c7d603d240a52cfea4675078cf1e55b"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "05-11 owner UAT steps 1-10 on the real Custom/ (run .\\env\\Scripts\\python.exe kicad_lib_manager.py from the main checkout, not a worktree): Ctrl+I offers the newest Downloads zip without opening it; open ul_CSD85301Q2.zip; Install blocked on the IC_SubCategory_TI placeholder; type a new name or pick IC_*_TI; Footprint field reads <Lib>:DQK0006B; empty Datasheet and see it in the diff; resolve any conflict per row; click Install Part."
    expected: "Progress shows, the Result view lists files and warnings, the library list rescans behind the dialog, the library is checked/expanded/current in both trees. For a new library sym-lib-table and fp-lib-table gain exactly one entry each (git diff on the tables). git -C Custom status shows the new files uncommitted and nothing is pushed."
    why_human: "Needs the real Custom/ checkout, real fonts and a real KiCad. The executors and this verifier were forbidden to launch the GUI or touch the real library, tables or %APPDATA%/kicad."
  - test: "05-11 Task 2 step 8: with KiCad's Symbol Editor open, install a part and watch the Result view; then reopen the editor and load the part (including one installed with an emptied Datasheet, assumption A4)."
    expected: "The amber 'KiCad is running. Reopen KiCad's Symbol and Footprint editors to see <Lib>.' notice appears and is logged as a WARNING; after reopening, KiCad loads the symbol, footprint and 3D model and accepts an empty Datasheet value."
    why_human: "POST-05 detection is unit-tested with a faked process list, and KiCad actually loading the written files cannot be checked without a running KiCad."
  - test: "Visual checks at 100% and 150% display scaling at the 900x600 minimum window size (recorded as pending by 05-07, 05-09, 05-10 and 05-11): Start page, left pane (items, target library badge and token line, fields), blocking-reason strip, conflict rows, install progress row, failure banner and Result view."
    expected: "No name is clipped, the left pane has no horizontal scroll bar, amber frames/strip/badge and the tinted banners read correctly, Tab/Enter work on strip links and conflict rows."
    why_human: "The offscreen test platform has no fonts or scaling, so geometry tests prove containment only, not the look. Dark mode, high contrast and scaling above 150% are also unverified."
  - test: "05-11 Task 3 help re-check: after the UAT install press F1 and read How to Use > Importing Parts."
    expected: "The Conflicts, Install and result, and Library tables sections describe what was seen in UAT steps 5-7, with no step the app does not have. Also read the KiCad path-variable bullet (quick 261022-gnn): running from a git worktree refuses the change and logs it, which is expected."
    why_human: "Judging whether prose matches the experienced behaviour is a human call."
---

# Phase 5: Import UI and Post-Install Verification Report

**Phase Goal:** The user imports a part end to end from the Library Manager. They pick a package, review and edit an exact preview, resolve conflicts, install, and see the new library selected with tables refreshed.
**Verified:** 2026-10-22
**Status:** human_needed (no gaps; owner UAT and visual checks outstanding)
**Re-verification:** No, initial verification

## Goal Achievement

The goal is achieved in the code. The whole flow exists, is wired into `MainWindow`, and was exercised both by the phase tests and by an independent end-to-end script that I ran for this report (build plan, preview sections, apply, read back) against a temporary copy of `Custom/`. I found no failed truth and no blocker. The remaining items are owner-only checks that nobody was allowed to perform (real library, real KiCad, real fonts and scaling), plus six open code review warnings that I classify as non-blocking.

### Observable Truths

| # | Truth (ROADMAP success criterion) | Status | Evidence |
|---|-----------------------------------|--------|----------|
| 1 | SC1: Import starts from "Import Part..." or a zip/folder drop; file dialog opens in the last-used folder; newest Downloads zip is offered; user picks among several symbols/footprints/models | VERIFIED | `main_window.py:116-123` (File > Import Part..., Ctrl+I, first item) and `:190` toolbar button; `setAcceptDrops(True)` at `:100`, `dropEvent` `:707-734` accepts exactly one local .zip (case-insensitive) or folder and calls `_open_import(path)`, refuses several, wrong type, and busy state. `importer/downloads.py:newest_zip` (files only, case-insensitive, read-only); `import_dialog.py:893-951` offers it, never auto-opens, `_browse_start_dir` returns saved `import/last_dir` then Downloads then home; `_pick` saves the parent via `save_import_dir`. Picker: symbol combo, footprint checklist, model combo ending in "No model" (tests `test_picker_*`). Tests pass: `test_start_page_*`, `test_picker_*`, `test_drop_*`. |
| 2 | SC2: Before anything is written the preview lists every file created/modified, every rename and path rewrite, source vs target format, whether kicad-cli normalises, and warnings; nothing changes until Install | VERIFIED | `importer/preview.py` builds six sections (Files, Renames, Path rewrites, Format, Conflicts, Issues) as a pure function of the plan. My script output on the UL sample: `Files (3)`, `Renames (2): DLV0006A.stp -> CSD85301Q2.stp, DQK0006B -> DQK0006B_X`, `Path rewrites (3): Footprint, Model, ki_fp_filters`, `Format (2): Symbol format 20211014 -> 20211014 / Already in the target format`, `Issues (1)` with the ignored-members note. `test_tracer_nothing_written_before_install` asserts a byte-snapshot of the repo copy is unchanged across plan builds. `test_preview_sections_follow_plan_ops` passes. |
| 3 | SC3: User edits target library, footprint name, Value, Datasheet, Description, Manufacturer, MPN; the Footprint field follows as `<Lib>:<FP>` on every edit; installed files match what the preview last showed | VERIFIED | `import_dialog.py` Footprint field is read from the accepted plan (`f"{plan.library}:{plan.linked_footprint}"`), never computed in the widget; `test_footprint_field_follows_library_and_name` passes (`IC_Battery_Charger_TI:DQK0006B` -> `...:DQK_0006B` -> `IC_IMU_TDK:DQK_0006B`). Independent script: with edits (footprint `DQK0006B_X`, description, datasheet, manufacturer, MPN) the installed symbol had `Footprint = IC_Battery_Charger_TI:DQK0006B_X`, `Datasheet`, `ki_description`, `Manufacturer = Texas Instruments`, `MPN` and `model = Custom/3DModels/CSD85301Q2.stp`; every `FileOp.data` equalled the bytes read back from disk ("planned bytes == installed bytes"). `test_install_uses_latest_plan_object` asserts `apply_plan` receives the very rendered plan object (identity), `test_tracer_ul_import_end_to_end` asserts `plan is dialog._plan`. `InstallOptions.cleared` (plan 05-02) gives explicit-empty fields; `tests/test_install_options_clear.py` passes. |
| 4 | SC4: Every conflict with an existing symbol/footprint/model shows its own overwrite / rename / skip choice; no "overwrite all" | VERIFIED | `widgets/conflict_row.py` one row per `Conflict.key` with exclusive Overwrite/Rename/Skip toggles, none selected initially; grep of `widgets/` for overwrite-all / apply-to-all / bulk finds only the docstring stating there is no bulk control. Choices kept by key across rebuilds (`test_conflict_choice_carried_by_key`), unresolved rows block Install (`test_conflict_rows_no_bulk_and_none_selected`, `test_conflict_choice_rebuilds_and_resolves`, `test_conflict_rename_field_and_empty_reason`). All pass. |
| 5 | SC5: After install the library list rescans and shows the new/updated library selected; tables regenerated for a new library; user told to reopen KiCad's library editors if KiCad runs | VERIFIED (code and tests; real-KiCad behaviour is a human item) | `_on_import_installed` -> `_start_scan` -> `_apply_post_install_selection` (checks the rel_path match, unchecks a same-nickname peer) -> `_tree.reveal(...)` -> `_finish_post_install`. New library: `add_library_entries` writes one managed entry per table with backup and atomic write (D-17 add-only, deliberately not a full `write_tables`), then `_sync_path_vars()`, which per quick 261022-gnn only changes `kicad_common.json` after an explicit confirm and refuses worktree/other-checkout runs. Existing library missing from tables: Generate hint. POST-05: `_start_kicad_check` runs `kicad_running()` on a worker, `_on_kicad_running` shows the notice in the Result view and logs a WARNING. Tests `test_post_install_select_*`, `test_tables_*`, `test_status_rows_*`, `test_kicad_running_*`, `test_post_install_steps_never_run_git` pass. |
| 6 | Preview equals install (PREV-07): the plan is rebuilt on every edit, stale results are dropped, builds are serial | VERIFIED (behavioral tests ran) | Generation counter in `_on_build_result` drops stale results; `test_supersede_discards_stale_result`, `test_one_build_at_a_time`, `test_builds_never_overlap`, `test_debounce_single_rebuild` pass. These are behavior-dependent (ordering/cancellation) and each has a passing named test, so none is left present-but-unexercised. |
| 7 | Install is gated and locked: disabled while updating/blocked/no-op, no cancel, close/Esc ignored while installing, rollback returns to a rebuilt preview with a banner | VERIFIED | `_on_install_clicked`, `_set_install_ui`, `done()`/`closeEvent`/`keyPressEvent` guards (`import_dialog.py:2029-2205`); tests `test_install_progress_and_lock`, `test_install_close_esc_reject_ignored`, `test_install_failure_banner_and_rebuild`, `test_close_refused_while_installing`, `test_noop_plan_disables_install`, `test_placeholder_blocks_install` pass. |
| 8 | Layering and safety: importer package stays Qt-free, nothing in the import flow runs git or subprocess, no write happens off the user's confirm | VERIFIED | `tests/test_importer_layering.py` passes; `test_import_flow_modules_do_not_import_subprocess` and `test_import_flow_never_runs_git` pass; grep for `subprocess`/`git` in `widgets/` and `main_window.py` is empty; grep for TBD/FIXME/XXX/TODO/HACK/"not yet implemented" in `kicad_lib_manager/` is empty. The real `Custom/` checkout was clean after my script (it only wrote to a temp dir). |
| 9 | Result view: warnings, files written (openable read-only), backup folder, live status rows, hidden Phase 6 `commitSlot` | VERIFIED | `widgets/import_result.py` (`commitSlot` at `:191`); `test_result_view_*`, `test_post_install_status_rows`, `test_dialog_forwards_post_install_status`, `test_file_activated_signal_carries_absolute_path` pass. |
| 10 | Help pages describe the new flow and match the finished widgets | VERIFIED (text present; prose accuracy is a human item) | `help_dialog.py` has "Importing Parts" page (`:211-260`), Ctrl+I in the shortcut table (`:312`), KiCad-running notice (`:257`); `tests/test_help_dialog.py` passes. |
| 11 | Persisted last folder and Downloads offer do not leak into tests or the real settings | VERIFIED | `_isolated_settings` autouse fixture redirects QSettings to `tmp_path` and asserts it; `tests/test_settings_import.py` passes. |

**Score:** 5/5 roadmap success criteria verified (11/11 including supporting truths); 0 behavior-unverified.

### Deferred Items

None. Phase 6 (git commit step) is later work and nothing in Phase 5's contract depends on it; the `commitSlot` hook it needs is present.

### Advisory (New Scope, Unevidenced)

None. This is an initial verification.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kicad_lib_manager/widgets/import_dialog.py` | Dialog: start page, items, library combo, fields, strip, conflicts, install, result | VERIFIED | 2205 lines, wired from `main_window._open_import`; no stub markers |
| `kicad_lib_manager/widgets/import_result.py` | Result view + `commitSlot` | VERIFIED | 304 lines, used by `_show_result` |
| `kicad_lib_manager/widgets/conflict_row.py` | Per-conflict Overwrite/Rename/Skip | VERIFIED | 309 lines, rows synced by key in `_sync_conflicts` |
| `kicad_lib_manager/widgets/preview_tree.py`, `content_view.py` | Styled preview tree, read-only content/diff view | VERIFIED | Used by dialog; tests pass |
| `kicad_lib_manager/widgets/theme.py` | Shared colours/QSS (AMBER etc.) | VERIFIED | Used by log panel, trees, dialog |
| `kicad_lib_manager/importer/preview.py`, `form.py`, `content.py`, `downloads.py` | Qt-free preview rows, field defaults, content text, newest zip | VERIFIED | Imported by the dialog; layering test passes |
| `kicad_lib_manager/importer/plan.py`, `planner.py` | `InstallOptions.cleared`, empty Value/MPN refusal, early Custom-folder refusal | VERIFIED | `tests/test_install_options_clear.py` passes |
| `kicad_lib_manager/table_generator.py` (`add_library_entries`) | Add-only table update | VERIFIED | Called in `_finish_post_install`; `tests/test_table_add_entries.py` passes (see WR-01 caveat) |
| `kicad_lib_manager/library_scanner.py` (`sync_kicad_path_vars` confirm/refusals) | Never silent | VERIFIED | Sole `kicad_common.json` writer, always called with `confirm=` (also confirmed by 05-REVIEW) |
| `kicad_lib_manager/widgets/library_table.py` (`reveal`), `settings.py` (`import/last_dir`), `main_window.py` | Reveal, persistence, wiring | VERIFIED | Wired and tested |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `MainWindow` action/button/drop | `ImportDialog` | `_open_import` | WIRED | window-modal `dialog.open()`, signals `installed`, `issues_logged`, `finished` connected |
| `ImportDialog.installed` | rescan + post-install | `_on_import_installed` -> `_start_scan` -> `_on_scan_finished` -> `_finish_post_install` | WIRED | also runs when the rescan fails (`_on_scan_error`) |
| `_finish_post_install` | tables | `add_library_entries` (new) / `table_info` hint (existing) | WIRED | |
| `_finish_post_install` | `kicad_common.json` | `_sync_path_vars(confirm=...)` | WIRED | confirm dialog, default No |
| Dialog Install button | `apply_plan` | worker lambda over the rendered plan | WIRED | see WR-04 (reads `self._plan` at thread run) |
| Result view | KiCad-running notice | `_start_kicad_check` worker | WIRED | |
| Dialog | Phase 4 core | `ImportCore` (`open_package`, `detect_candidate`, `build_plan`, `apply_plan`, ...) on `TaskWorker` threads | WIRED | `test_core_calls_run_off_the_gui_thread` passes |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| Preview tree | sections | `preview_sections(plan, candidate, options)` from a real `build_plan` | Yes (my script printed real rows from the UL zip) | FLOWING |
| Footprint field | `plan.library:plan.linked_footprint` | accepted plan | Yes | FLOWING |
| Result view files | `InstallResult.touched` / plan ops | `apply_plan` result | Yes | FLOWING |
| Library list after install | `ScanResult` from `ScanWorker` | real scan | Yes | FLOWING |
| Table status rows | Issues from `add_library_entries` | real table files | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase test modules (dialog, form, preview, content, downloads, main window x2, preview tree, settings, table add, library table, help, options clear, layering, kicad config) | `./env/Scripts/python.exe -m pytest <15 modules> -q` | 398 passed, 4 warnings (a Qt deprecation on `QDragEnterEvent`) | PASS |
| Plan, preview, install, read back on a temp copy of `Custom/` with all five field edits and a footprint rename | `python -I -X utf8 e2e_check.py` (scratchpad script) | `ok True`, planned bytes == installed bytes, Footprint field `IC_Battery_Charger_TI:DQK0006B_X`, real `Custom/` git status clean | PASS |
| Orchestrator-reported full suite on the merged tree | not re-run by me | 1643 passed, 5 skipped, 7 failed | see below |

The 7 failures are real-`kicad-cli` tests (`test_install_plan.py::test_version_real_cli_into_20241209`, `::test_library_real_cli_new_header`, `::test_noop_second_plan_after_normalised_apply`; `test_kicad_cli.py::test_real_cli_upgrades_ul_symbol_deterministically`; `test_install_e2e.py::test_cli_version_scenarios[older_incoming_is_normalised]`, `[new_library_gets_cli_header]`, `::test_cli_second_install_is_noop`). They fail identically on the phase base commit 543f75e because the installed KiCad 10 CLI writes symbol format 20251024 where the tests expect 20241209. This is a pre-existing environment issue and is not recorded as a gap. It is still worth a future fix, because it also means the "kicad-cli normalises" path has no passing end-to-end proof on this machine (the PREV-06 preview text itself is tested with a fake CLI).

### Probe Execution

SKIPPED: the phase declares no `probe-*.sh` scripts.

### Requirements Coverage

All 13 IDs claimed in the PLAN frontmatter (union across 05-01 to 05-11) match the 13 IDs that ROADMAP and REQUIREMENTS.md map to Phase 5. No requirement is orphaned and no plan claims an ID outside the phase.

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|-------------|--------|----------|
| INTK-07 | 05-07 | Pick which symbol/footprint/model to import | SATISFIED | Symbol combo, footprint checklist, model combo + "No model"; `test_picker_*` |
| PREV-01 | 05-06, 05-10 | Preview lists every file, rename, path rewrite | SATISFIED | `importer/preview.py`; script output |
| PREV-02 | 05-07 | Editable footprint name defaulting to vendor name | SATISFIED | `test_footprint_name_default_and_vendor_hint`, `_edit_and_restore` |
| PREV-03 | 05-07, 05-09 | Footprint field `<Lib>:<FP>` stays in sync | SATISFIED | `test_footprint_field_follows_library_and_name` |
| PREV-04 | 05-02, 05-07 | Edit Value/Datasheet/Description/Manufacturer/MPN, exact property names | SATISFIED | `test_install_options_clear.py`, `test_fields_*`; script read back `Manufacturer`, `MPN`, `Datasheet`, `ki_description` (see note 1) |
| PREV-05 | 05-10 | Per-conflict overwrite/rename/skip | SATISFIED | `conflict_row.py`, `test_conflict_*` |
| PREV-06 | 05-06, 05-09 | Source vs target format and kicad-cli normalisation shown | SATISFIED | Format section rows; tested with fakes (real-CLI tests fail for the environment reason above) |
| PREV-07 | 05-01, 05-09 | Preview and install share one plan, rebuilt per edit | SATISFIED | identity test, generation counter, byte equality in my script |
| POST-01 | 05-01, 05-03, 05-04, 05-11 | Rescan, show and select the library | SATISFIED | `test_post_install_select_*`, `reveal` |
| POST-02 | 05-04, 05-11 | Tables updated when a new library was created | SATISFIED (add-only per D-17; see note 2) | `add_library_entries`, `test_tables_new_library_add_only` |
| POST-05 | 05-11 | Tell the user to reopen KiCad editors if KiCad runs | SATISFIED in code and tests | `_on_kicad_running`; real-KiCad confirmation is a human item |
| UX-01 | 05-08 | Drag and drop starts an import | SATISFIED | `dropEvent`, `test_drop_*` |
| UX-02 | 05-05 | Remembers last folder, offers newest Downloads zip | SATISFIED | `downloads.py`, `settings.py`, `test_start_page_*` |

Notes:
1. The description is written to `ki_description` (the existing planner convention from Phase 4), not a property literally named `Description`. This is Phase 4 behaviour that Phase 5 inherits; KiCad accepts it. No gap, mentioned for the UAT reader.
2. ROADMAP SC5 says tables are "regenerated"; the implementation adds only the new library's entries (documented decision D-17) so that unrelated tree selections are never written. This satisfies the intent and is safer; REQUIREMENTS.md wording could be tightened in a later docs pass.

REQUIREMENTS.md bookkeeping: the 13 checkboxes and the traceability rows still read `[ ]` / `Pending`. The orchestrator should flip them to Complete when this phase is closed, after the human items below are accepted.

### Anti-Patterns Found

Debt-marker scan (TBD/FIXME/XXX/TODO/HACK/placeholder/coming soon/not yet implemented) over `kicad_lib_manager/`: no hits. Stub scan found nothing that flows to user-visible output. The only issues are the open code review findings (0 critical, 6 warning, 8 info, all `open` in `05-REVIEW-DISPOSITION.md`). I re-read the code behind WR-01 to WR-04 and agree with the reviewer's descriptions; none breaks a roadmap truth, so none is a blocker.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `table_generator.py` | 339-343 | WR-01: a managed entry with the same nickname but a different path returns "listed", so the Result row says "Not changed: X was already in the tables" while the new Custom library is not in the table | Warning | Edge case (nickname collision with another managed library, e.g. a Wurth one). The scanner already reports collisions; the Result row is misleading, KiCad still loads the other library |
| `main_window.py` | 619-638, 816-817 | WR-02: an empty Destination combo gives `Path('.')`, which passes `is_dir()`, so the post-install table write and Generate target the process working directory | Warning | Needs the user to clear the editable combo. Writes `sym-lib-table`/`fp-lib-table` (with backups) in the CWD instead of the repo. Worth fixing before the owner relies on it |
| `import_dialog.py` | 1588, 1821-1894 | WR-03: `_updating()` ignores `_oneoff`, and `_pump_builds` does not check `is_installing()`, so Install can be enabled while a one-off conflict build still reads target files, and a held job can start during an install | Warning | A torn read in the "existing vs incoming" view or a spurious `install.target_unreadable` log line. Install itself uses atomic writes, so no corruption |
| `import_dialog.py` | 2038, 972-975 | WR-04: the install worker lambda reads `self._plan` when the thread runs, and `open_path` has no `is_installing()` guard | Warning | Safe today (inputs locked, results dropped while installing); a future caller of `open_path` during install could install a different plan than the one previewed. Fix is a one-line default argument |
| `import_dialog.py` | 1160-1164, 2171-2185 | WR-05: GUI thread `wait()`s on workers (up to the 60 s kicad-cli timeout) when changing package or closing | Warning | Possible UI freeze on a hung kicad-cli, contradicts the "GUI never blocks" rule; no data risk |
| `library_scanner.py` | 246-282 | WR-06: after the confirm dialog the stale `kicad_common.json` copy is written without re-reading, and the KiCad-running check runs after the confirm and does not gate the write | Warning | The "never silent" guarantee holds (confirm is intact); the risk is overwriting KiCad's newer settings, with a backup taken |
| various | n/a | IN-01 to IN-08 (invisible U+200B literal, three elided-label classes, dead `_PostInstall.symbol` and unused `file_counts` params, `cap_lines` wording, unpruned worker list, tooltip rich-text heuristic, `self.result` shadows `QDialog.result()`, test hygiene and fixed sleeps) | Info | Cosmetic or maintainability |

### Human Verification Required

#### 1. Owner UAT on the real Custom/ (05-11 Task 2 steps 1-10)

**Test:** Run the app from the main checkout (not a worktree, which refuses path-variable changes by design). Follow UAT steps 1-10 listed in `05-11-SUMMARY.md`: newest Downloads zip offer, open `ul_CSD85301Q2.zip`, placeholder block, choose or type a library, Footprint field and Path rewrites, empty Datasheet in the diff, per-row conflict choice with no overwrite-all, Install, Result view, rescan selection, table diff, `git -C Custom status`.
**Expected:** Install completes with progress; the library is checked, expanded and current in both trees; a new library adds exactly one entry to each table; files are left uncommitted and nothing is pushed.
**Why human:** Needs the real library, real fonts and KiCad config, which no agent was allowed to touch.

#### 2. KiCad-running notice and KiCad loading the part (step 8, assumption A4)

**Test:** Keep the Symbol Editor open during an install, then reopen it and load the part, including one installed with an emptied Datasheet.
**Expected:** The amber notice shows and logs a WARNING; after reopening, the part loads with symbol, footprint and 3D model, and KiCad accepts the empty Datasheet.
**Why human:** Detection is tested with a fake process list only; KiCad acceptance of the written files needs a real KiCad.

#### 3. Visual checks at 100% and 150% scaling

**Test:** At the 900x600 minimum window size, inspect the Start page, left pane, strip, conflict rows, install row, failure banner and Result view. Also glance at dark mode and high contrast.
**Expected:** No clipped names, no horizontal scroll bar in the left pane, readable amber/tinted elements, Tab/Enter work on strip links and conflict rows.
**Why human:** The offscreen platform has no fonts or scaling; 05-07, 05-09, 05-10 and 05-11 all recorded this as pending.

#### 4. Help page re-check (05-11 Task 3)

**Test:** After the UAT install press F1 and read How to Use > Importing Parts.
**Expected:** The Conflicts, Install and result, and Library tables sections match what UAT steps 5-7 showed.
**Why human:** Prose accuracy against observed behaviour.

### Gaps Summary

There are no gaps. All five roadmap success criteria and the supporting plan truths are backed by code, wiring and passing tests, and an independent end-to-end run confirmed that the preview, the plan and the installed bytes agree. The status is `human_needed` solely because the four owner-only checks above were deliberately not performed. The six open review warnings are recorded as non-blocking; WR-02 (empty Destination writes tables into the working directory) and WR-01 (misleading "already listed" row) are the two I would fix first, ahead of the owner's first real use, and neither blocks closing the phase once the UAT passes.

---

_Verified: 2026-10-22_
_Verifier: Claude (gsd-verifier)_
