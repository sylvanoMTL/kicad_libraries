---
status: resolved
trigger: "G-13-1-g: Result view Generate Tables - Destination folder not visible or changeable (migration window modal; Destination pointed at deleted folder)"
created: 2026-11-12T00:00:00Z
updated: 2026-11-13T14:45:00Z
goal: find_root_cause_only
gap_id: G-13-1-g
---

## Current Focus

bug_class: Bohrbug (deterministic UI design gap; no concurrency/timing component)
hypothesis: |
  H1 (code/UI): MainWindow._open_migration opens the MigrationDialog with QDialog.open(), which makes it
  Qt.WindowModal on its parent (the main window), so the main window's Destination combo and Browse...
  are blocked for the whole life of the migration window; AND the Result view has no Destination
  display or picker (generate_requested is a bare Signal() and the slot reads self._dest_path() from
  the blocked main-window combo). With a missing Destination, _on_generate logs
  "Destination folder does not exist: <dest>" only to the main-window log and returns [], so the
  Result view shows nothing.
test: Offscreen pytest in scratchpad: real MainWindow + real MigrationDialog (fake MigrationCore), Destination
  set to a non-existent folder, event filter on the main window for QEvent.WindowBlocked, drive Run to the
  Result view, click its Generate Tables button.
expecting: windowModality()==WindowModal, main window receives WindowBlocked; after click: main log has the
  "Destination folder does not exist" error, no tables written, no widget in the dialog shows the path.
next_action: DONE (diagnose-only) - return ROOT CAUSE FOUND to the orchestrator
result: H1 CONFIRMED by the offscreen probe (see Evidence)
rca:
  candidate_causes:
    - "code: QDialog.open() makes the migration window WindowModal on the main window (confirmed)"
    - "code/UI: Result view has no Destination display or picker; slot reads the hidden main-window combo and reports failures only to the main log (confirmed)"
    - "data/config: dest_history restores a deleted folder as the current Destination without an existence check (contributing trigger)"
    - "environment: none - offscreen reproduces the same modality as the owner's Windows desktop"
  and_gate: "yes - the owner is stuck only when BOTH (1) the window blocks the main window AND (2) the Result view offers no Destination of its own; a stale Destination (data) is what made it visible. Fixing either (1) or (2) restores 'change it'; only (2) also gives 'see it'."

## Symptoms

expected: After Run Migration, the Result view offers a Generate Tables button (CLAUDE.md, CONTEXT D-13/D-17). The owner should know, and be able to choose, where the tables go.
actual: Migration window is modal and blocks the main window, so the main window's Destination box (pointing at a deleted throwaway folder C:\Users\sylva\OneDrive\Desktop\d26-check) could not be changed before pressing Generate Tables in the Result view; the Result view does not display the Destination at all. Owner closed the migration window and generated from the main window instead (worked: 10 symbol + 1 footprint entries to C:\Git_Repo_Clones\USBlitz\USBlitz).
errors: None observed (Result view's Generate Tables not pressed; unknown behaviour with non-existent Destination).
reproduction: UAT Test 1 check 8. Set Destination to a folder, delete it, run a migration (fixtures tests/migrationfixtures.py, tests/test_main_window_migration.py), then in the Result view press Generate Tables.
started: Discovered during UAT 2026-11-12.

## Eliminated

## Evidence

- timestamp: 2026-11-12
  checked: .planning/debug/knowledge-base.md (Phase 0)
  found: file does not exist; no MemPalace; no known-pattern candidate
  implication: open-ended investigation

- timestamp: 2026-11-12
  checked: kicad_lib_manager/main_window.py _open_migration (lines 1240-1265)
  found: MigrationDialog(REPO_ROOT, self._kicad_fp_dir, core=MIGRATION_CORE, parent=self) ... dialog.open().
    QDialog.open() shows the dialog as a WINDOW-MODAL dialog (Qt docs), i.e. it blocks its parent window.
    The class docstring (migration_dialog.py:491) says "Non-modal migration window" - but 13-14-PLAN.md
    only meant "non-modal to the guide"; 13-17-PLAN.md copied `dialog.open()` from _open_import.
  implication: while the migration window is open the main window (Destination combo, Browse..., Generate
    Tables button, log scroll) cannot take input

- timestamp: 2026-11-12
  checked: kicad_lib_manager/widgets/migration_dialog.py _build_result_page (1647-1708) + constants (100-113)
  found: Result view = title, map text, Copy/Open MIGRATION-ATOMIC.md, NEXT_STEPS_TEXT label, a row with
    Generate Tables (clicked -> generate_requested.emit, a bare Signal() with no argument) and
    Set Up KiCad Chooser, the commit panel host, Close. No label, field or button mentions Destination.
    MigrationDialog receives only repo_root and kicad_fp_dir; it never knows the Destination folder.
  implication: the Result view cannot show or change where tables go

- timestamp: 2026-11-12
  checked: main_window.py _on_migration_generate (1593) -> _run_migration_generate (1606) -> _on_generate (1620)
  found: Destination comes from self._dest_path() (the main-window combo text). _on_generate: if dest is None ->
    log _NO_DEST_TEXT warning, return []; if not dest.exists() -> self._log.log(f"Destination folder does not
    exist: {dest}", "error"); return []. Nothing is created, nothing is sent back to the dialog. The deferred
    path (_generate_after_scan while the post-migration rescan runs) ends in the same _on_generate.
    Contrast: the import path (_finish_post_install ~988-1000) also mirrors the same message into its Result
    view via _set_import_status("tables", ..., Severity.ERROR); the migration path has no equivalent.
  implication: with a missing Destination, pressing Result-view Generate Tables silently (from the dialog's
    point of view) does nothing; the only trace is an error line in the blocked main window's log

- timestamp: 2026-11-12
  checked: _on_setup_chooser (1525-1533) and _on_chooser_check (1550-1558)
  found: the chooser also reads self._dest_path() (sync_kicad_chooser(REPO_ROOT, self._dest_path(), ...)),
    pins come from the tables in the Destination folder (CONTEXT Claude's Discretion)
  implication: the Result view's Set Up KiCad Chooser button has the same hidden-Destination dependency

- timestamp: 2026-11-12
  checked: tests/test_main_window_migration.py, tests/test_migration_dialog_run.py
  found: FakeMigrationDialog replaces the real dialog in main-window tests (its open() calls QDialog.open(),
    modality never asserted). Both generate tests (test_generate_after_migration_keeps_atomic_libraries,
    test_generate_requested_during_rescan_waits) run with the default Destination = REPO_ROOT, which exists.
    test_generate_and_chooser_buttons_emit only asserts the button emits the signal. No test covers a missing
    or blank Destination from the migration path, the dialog's modality, or any Destination display.
    By contrast tests/test_main_window_import.py:352 explicitly asserts the IMPORT dialog is WindowModal.
  implication: nothing in the suite would catch or constrain this; a fix changing modality must not
    break other tests (none assert migration modality)

- timestamp: 2026-11-12
  checked: Offscreen probe (scratchpad g13g/test_g13g_probe.py, QT_QPA_PLATFORM=offscreen): real MainWindow,
    real MigrationDialog with a fake MigrationCore (no Custom/ read), REPO_ROOT/scan_all/kicad_running/
    sync_kicad_path_vars patched, Destination combo set to a non-existent tmp folder, event filter on the
    main window, Run -> Result view, click Result-view Generate Tables
  found: |
    dialog.isModal() True; windowModality() WindowModal; QApplication.activeModalWidget() is the dialog;
    main window received QEvent.WindowBlocked on open and WindowUnblocked only on close; still WindowModal on
    the Result page.
    Result view: no text mentions Destination or the path; buttons = Copy, Open MIGRATION-ATOMIC.md,
    Generate Tables, Set Up KiCad Chooser..., (commit panel buttons), Close - no Browse.
    Click Generate Tables -> main-window log only: "Destination folder does not exist: <tmp>\d26-check-deleted";
    folder not created; no sym-lib-table/fp-lib-table written; dialog stays on the Result page with labels
    unchanged (no feedback). Blank Destination -> main log "No destination folder set; library tables not
    changed", same silence in the dialog.
    Set Up KiCad Chooser from the Result view with the missing Destination: main log "No sym-lib-table found
    in <missing>", "No fp-lib-table found in <missing>", "Read the Atomic_ libraries from the tables in
    <missing>", then refused by the D-26 checkout check (probe REPO_ROOT != KiCad's KICAD_LIB_GITHUB; the
    real kicad_common.json was only read, nothing written).
  implication: H1 CONFIRMED. Answers the open question in Symptoms.errors: pressing the Result view's Generate
    Tables with the deleted Destination would have written nothing and shown nothing in the migration window;
    the only trace is one error line in the main window's log (visible but not scrollable/interactive behind
    the window-modal dialog). The chooser would read pins from a folder with no tables.

- timestamp: 2026-11-12
  checked: main_window.py _populate_dest_combo (473-482), settings.load_dest_history/add_dest_to_history
  found: the Destination combo is restored from QSettings dest_history (most recent first) with no existence
    check, so a folder deleted after use (UAT step (c) d26-check) stays the current Destination at next start
  implication: data trigger that exposed the gap (contributing condition, not the root cause)

## Resolution

root_cause: |
  AND-gate of two code causes (plus a data trigger):
  (1) MainWindow._open_migration shows the MigrationDialog with QDialog.open(), which makes it WindowModal on
      the main window (verified: isModal True, WindowModal, main window gets WindowBlocked until close), so the
      main window's Destination combo and Browse... cannot be used while the migration window is open - even
      though the class docstring calls it a "Non-modal migration window";
  (2) the Result view (migration_dialog._build_result_page) neither shows nor lets the owner choose the
      Destination: generate_requested is a bare Signal() and the slot chain _on_migration_generate ->
      _run_migration_generate -> _on_generate reads self._dest_path() from the blocked main-window combo; a
      missing/blank Destination only logs "Destination folder does not exist: ..." / "No destination folder
      set..." to the main-window log and returns [] - no folder is created, nothing is reported back to the
      Result view (unlike the import path, which mirrors it via _set_import_status("tables", ...)).
  Trigger (data): the Destination combo is restored from QSettings dest_history without an existence check,
  so a deleted throwaway folder stayed current.
fix: "Plan 13-28 (G-13-1-g): the migration Result view shows and changes the Destination (Browse...), reports Generate's outcome under the buttons, and the Destination box skips folders that no longer exist."
verification: "Phase 13 re-test UAT 5/5 passed 2026-11-13."
files_changed: []

Resolved at the v2.0 milestone close (2026-11-13) against the plan that fixed it.
