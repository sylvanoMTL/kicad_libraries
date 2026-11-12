---
status: diagnosed
phase: 13-atomic-migration-and-kicad-setup
source: [13-VERIFICATION.md]
started: 2026-11-12T13:05:57Z
updated: 2026-11-12T18:26:29Z
---

## Current Test

[testing complete]

## Tests

### 1. Owner's live migration UAT (main checkout, real Custom/, real KiCad 10)
expected: Run the full migration end to end from the main checkout (C:/Git_Repo_Clones/Kicad_Libraries, not the Kicad_Libraries-importer worktree) against the real Custom/ submodule and a real KiCad 10 install, following the UAT check list referenced in 13-18-SUMMARY.md (coverage item D6). Preview shows every real part and passes; Run completes as one transaction; the post-migration scan reports zero atomic violations; Generate Tables and Set Up KiCad Chooser behave as documented; the Custom and parent-ref commits are made; KiCad's chooser shows the new Atomic_ libraries pinned. The blocking gap that previously made this unsafe (CR-01's case-insensitive-vs-untouched-model manifestation) is closed by plan 13-22 and independently confirmed.
result: issue
reported: "End-to-end flow passed on 2026-11-12: setup (a)-(d) and checks 1-12 all confirmed on the real Custom/ and KiCad 10 (21 parts into 10 Atomic_ libraries, Custom bbd48c5, parent c6920f5, chooser pinned). Seven problems found on the way, recorded as gaps G-13-1-a..g: the app does not import on Python 3.11 (CommitPlan NameError), Skip greyed during the symbol scan, menu should read Pin Atomic Libraries in KiCad..., Part column and Library dropdown too narrow (hot-fixed in 3dc3081), IMU suggested into Atomic_Timer, Result-view Generate Tables cannot change the Destination."
severity: major

## Summary

total: 1
passed: 0
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-13-1-a
  truth: "The app starts and the migration dialog loads on every supported Python version (3.10+), not only 3.14"
  status: failed
  reason: "Found during UAT setup: with the main checkout's venv (Python 3.11.3, PySide6 6.10.2) importing the app fails with NameError: name 'CommitPlan' is not defined at kicad_lib_manager/widgets/migration_dialog.py:338 (annotation names CommitPlan without importing it; Python 3.14's deferred annotations hide it)"
  severity: major
  test: 1
  root_cause: "migration_dialog.py uses two type names it never imports: CommitPlan (line 338, _CommitStepHost.start) and CommitProbe (line 373, _on_probe_done). Python 3.10-3.13 evaluate parameter hints while the class body runs, so importing migration_dialog (and help_dialog, main_window) raises NameError; Python 3.14 defers evaluation (PEP 649/749) and the repo venv is 3.14, the only interpreter tests ever run on. No CI or linter catches undefined names."
  artifacts:
    - path: "kicad_lib_manager/widgets/migration_dialog.py"
      issue: "lines 338 and 373 annotate with CommitPlan / CommitProbe without importing them (imports at lines 26-28 list only functions)"
    - path: "tests/"
      issue: "no test resolves every module's type hints; pytest runs only on 3.14"
  missing:
    - "Import CommitPlan from ..importer.commit_plan and add CommitProbe to the ..importer.commit_step import in migration_dialog.py (as commit_panel.py and import_dialog.py already do)"
    - "Add a regression test that imports every kicad_lib_manager module via pkgutil.walk_packages and calls inspect.get_annotations on every module-level function, class and method, asserting no NameError (fails on 3.14 too for these two sites; prototype at scratchpad/annscan/annotations_resolve_proto.py; symbols.plan_symbols FootprintsOutcome string hint needs an explicit exemption if eval_str=True is used)"
  debug_session: ".planning/debug/py311-commitplan-nameerror.md"
- gap_id: G-13-1-b
  truth: "The Loading Libraries window's Skip button is available during the symbol scan stage, not only during the 3D model path check"
  status: failed
  reason: "User reported: the skip button is grayed out I guess for the symbol scanning, This should not be grayed out. user can skip that stage."
  severity: minor
  test: 1
  root_cause: "By design (plan 12-17, owner decision 2026-11-04) the Skip button is enabled only by checking(source), which scan_all passes solely to _check_model_files; find_symbol_libs and the other stages get only progress. Skipping the symbol parse itself is incompatible with the contract that a skip never drops a library or footprint link (_merge_table would delete unseen managed entries, _sync_footprint_selection would uncheck footprints). The symbol stage costs about 6 s on the owner's checkout (412 files, 12.9 MB WR-TBL); the 40-100 s is the Wurth 3D check, already skippable once it starts. ScanWorker._skip_sources is a lasting per-source set, so an early skip request is already honoured by _check_model_files."
  artifacts:
    - path: "kicad_lib_manager/library_scanner.py"
      issue: "scan_all (670-733) passes skip/checking only to _check_model_files; find_symbol_libs (429-444) takes only progress"
    - path: "kicad_lib_manager/widgets/scan_progress.py"
      issue: "_show_idle starts Skip disabled; set_skippable resets text on every report so an early click could be re-enabled later"
    - path: "kicad_lib_manager/main_window.py"
      issue: "_on_scan_checking / _on_skip_requested (634-645) are the only path that enables Skip"
  missing:
    - "Offer Skip <source> from the start of the full scan (e.g. find_symbol_libs reports the source via checking(source), or the dialog offers each known source once listing is done) as an advance skip of that source's 3D model path check; the symbol parse still completes so links and Generate Tables stay intact"
    - "Dialog remembers requested sources so a later checking(source) shows Skipping <source>... disabled instead of re-enabling the button; the log line still comes only from the scan result"
    - "Update tooltip, Help Repository Scan text, CLAUDE.md Loading Libraries bullet, and tests/test_main_window.py:1454 (and 1517/1549/1616 as needed); owner confirms this amends the 2026-11-04 decision"
  debug_session: ".planning/debug/skip-greyed-symbol-scan.md"
- gap_id: G-13-1-c
  truth: "The File menu action, its shortcut tooltip, the Result view button, the log lines and the User Guide call the action 'Pin Atomic Libraries in KiCad...' instead of 'Set Up KiCad Chooser...'"
  status: failed
  reason: "User reported: 'KiCad Chooser' is vague on its own; 'Pin Atomic Libraries in KiCad...' is much better"
  severity: cosmetic
  test: 1
  root_cause: "The action name Set Up KiCad Chooser... (D-17) and the word chooser are literal strings in 4 source modules (main_window.py SETUP_CHOOSER_TEXT :59, _NO_DEST_CHOOSER_TEXT :60, tooltip/status tip :342-349, confirm intro :1501/:1513, title :1518; kicad_setup.py 9 log/refusal texts :309 :317 :419 :473 :485 :501 :536 :545 :553 plus rare errors :389 :572 :588; migration_dialog.py CHOOSER_TEXT :108 and NEXT_STEPS_TEXT :109-112; help_dialog.py :255 :256 :268 :510 :570), repeated on CLAUDE.md lines 28, 81, 82, 83, 90, and pinned by tests/test_main_window_chooser.py (:1 :183 :199 :203-206 :268 :276 :281), tests/test_kicad_setup.py :324, tests/test_help_dialog.py :91 :98-100 :415; test_docs_atomic.py:51 follows SETUP_CHOOSER_TEXT automatically. No shared constant controls the wording."
  artifacts:
    - path: "kicad_lib_manager/main_window.py"
      issue: "menu text, tooltip/status tip, no-destination warning, confirm title and intro (x2)"
    - path: "kicad_lib_manager/kicad_setup.py"
      issue: "9 user-facing Issue texts + 3 rare error texts (keep Issue codes and identifiers)"
    - path: "kicad_lib_manager/widgets/migration_dialog.py"
      issue: "CHOOSER_TEXT and NEXT_STEPS_TEXT"
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: "h3 KiCad chooser, generating-page paragraph, migrating sentence, shortcuts row"
    - path: "CLAUDE.md"
      issue: "lines 28, 81, 82, 83, 90"
    - path: "tests/test_main_window_chooser.py, tests/test_kicad_setup.py, tests/test_help_dialog.py"
      issue: "expectations on the old strings"
  missing:
    - "Rename to &Pin Atomic Libraries in KiCad... (menu, access key P is free) / Pin Atomic Libraries in KiCad... (Result view button, Help shortcuts row), tooltip: Pin the Atomic_ libraries at the top of KiCad's library lists and show the MPN and Manufacturer columns when you place a symbol; confirm title: Pin Atomic libraries in KiCad?; refusals: Not pinning the Atomic_ libraries in KiCad: ... (worktree and wrong_checkout_refusal); the other log lines per the debug session; keep every identifier and chooser.* Issue code; Symbol Chooser / Footprint Chooser stays only as KiCad's term inside explanatory prose"
    - "Update CLAUDE.md (5 lines), the User Guide texts, and the three test files; optionally a rename note under D-17 in 13-CONTEXT.md"
  debug_session: ".planning/debug/rename-pin-atomic-libraries.md"
- gap_id: G-13-1-d
  truth: "In the migration window the Part column is wide enough to read library and part names in full at the default window size"
  status: resolved
  resolved_by: "commit 3dc3081 (hot fix applied during UAT, not a gap-closure plan)"
  resolved_at: 2026-11-12
  reason: "Observed in the owner's screenshot at 1875x946: the Part column is about 90 px wide, so every group and part name is elided (Atomic_B..., BQ2..., LTC...), while the Status column takes the rest of the tree"
  severity: cosmetic
  test: 1
  artifacts:
    - path: "kicad_lib_manager/widgets/migration_dialog.py"
      issue: "part tree column sizing leaves the Part column truncated"
  missing: []    # Filled by diagnosis
- gap_id: G-13-1-e
  truth: "The Library combo box in the migration window's Part tab is wide enough to show a full library name such as Atomic_Battery_Management"
  status: resolved
  resolved_by: "commit 3dc3081 (hot fix applied during UAT, not a gap-closure plan)"
  resolved_at: 2026-11-12
  reason: "User reported: the dropdown is too narrow; I cannot read what I am selecting (screenshot: the editable Library combo is about 70 px wide while the other fields span the tab)"
  severity: major
  test: 1
  artifacts:
    - path: "kicad_lib_manager/widgets/migration_dialog.py"
      issue: "Library combo box has no minimum width or expanding size policy"
  missing: []    # Filled by diagnosis
- gap_id: G-13-1-f
  truth: "The migration's library suggestion files an IMU (ICM-42688-P, 6-axis MEMS motion sensor) under Atomic_Sensor_Motion, not Atomic_Timer"
  status: failed
  reason: "Observed in the live run: with no owner choice the planner put ICM-42688-P (from IC_IMU_TDK, description 'High Precision 6-Axis MEMS MotionTrackingTM Device') into Atomic_Timer without any strip line, so Run would have accepted a wrong library silently"
  severity: major
  test: 1
  root_cause: "siblings.family_prefixes(ICM-42688-P) yields only [ICM] because its regex stops at the hyphen; siblings.pick accepts a simple majority at that coarsest step, and in KiCad 10 the ICM* stock symbols are 4 Intersil timers (ICM7209, ICM7555xB/xP, ICM7556 in Timer) vs 2 IMUs (ICM-20602, ICM-20948 in Sensor_Motion), so Timer wins 4:2. suggest.suggest_library returns a decided stock result before categories.classify runs (and the Sensor_Motion rule lacks 6-axis / motiontracking anyway). symbols.target_libraries adopts the suggestion as the target, gate.check_plan only flags an empty target, and the dialog shows a suggestion exactly like a choice (reason and runner-up only in a tooltip; alternatives not in the dropdown). Known and accepted at planning time (13-RESEARCH OQ2, 13-CONTEXT line 162); tests/test_migration_symbols.py:160 asserts Atomic_Timer. Reproduction: scratchpad/repro_imu.py against the real KiCad 10 symbols."
  artifacts:
    - path: "kicad_lib_manager/importer/siblings.py"
      issue: "family_prefixes drops the separator; pick accepts a bare-letters simple majority"
    - path: "kicad_lib_manager/importer/suggest.py"
      issue: "a decided stock vote outranks the description and is not marked weak"
    - path: "kicad_lib_manager/importer/categories.py"
      issue: "Sensor_Motion rule lacks 6-axis / motiontracking / mems motion"
    - path: "kicad_lib_manager/importer/migration/gate.py, kicad_lib_manager/importer/migration/symbols.py"
      issue: "a suggested target is accepted with no check-this-library line"
    - path: "kicad_lib_manager/widgets/migration_dialog.py"
      issue: "suggestion shown like a choice; alternatives missing from the dropdown list"
    - path: "tests/test_migration_symbols.py:160, tests/migrationfixtures.py (write_v1_stock), tests/test_migration_full.py:138-143"
      issue: "lock in the mis-suggestion"
  missing:
    - "Make the part-number match more specific (keep ICM- / ICM-4 steps before bare letters, or require a clear majority for a letters-only vote); let the description outrank a split stock vote and add motion words to the Sensor_Motion rule"
    - "Make guesses visible: a strip line or visible note (check this library) when the suggestion came from a split vote or a letters-only step, and mark suggested-but-unconfirmed libraries in the tree; list the alternatives in the dropdown"
    - "Update the tests that assert Atomic_Timer for ICM-42688-P"
  debug_session: ".planning/debug/imu-suggested-atomic-timer.md"
- gap_id: G-13-1-g
  truth: "Generate Tables in the migration Result view lets the owner see and change the Destination folder, or the Result view shows which Destination it will write to"
  status: failed
  reason: "Observed in the live run: the migration window blocks the main window, so the Destination box (still pointing at a deleted throwaway folder from step (c)) could not be changed before pressing Generate Tables in the Result view; the owner had to close the migration window and generate from the main window instead"
  severity: minor
  test: 1
  root_cause: "MainWindow._open_migration (main_window.py:1265) opens the dialog with dialog.open(), i.e. WindowModal: the main window's Destination box, Browse and log are blocked while it is open (verified offscreen: WindowBlocked event, activeModalWidget is the dialog, still modal on the Result page). The Result view (_build_result_page, migration_dialog.py:1647-1708) shows no Destination and generate_requested is a plain Signal(); the slot chain _on_migration_generate -> _run_migration_generate -> _on_generate reads the hidden main-window Destination and, when the folder is missing or blank, logs Destination folder does not exist / No destination folder set to the main log only, writes nothing, and reports nothing back to the Result view. Set Up KiCad Chooser from the Result view has the same hidden dependency. Trigger: _populate_dest_combo (473-482) restores a deleted folder from dest_history without checking it exists. No test covers a missing or blank Destination from the migration window or asserts its modality."
  artifacts:
    - path: "kicad_lib_manager/main_window.py"
      issue: "_open_migration uses dialog.open() (WindowModal); _on_migration_generate / _run_migration_generate / _on_generate and _on_setup_chooser read the hidden Destination and report only to the main log; _populate_dest_combo restores non-existent folders"
    - path: "kicad_lib_manager/widgets/migration_dialog.py"
      issue: "_build_result_page has no Destination label or picker; generate_requested carries no folder; docstring at 491 says Non-modal"
    - path: "tests/test_main_window_migration.py, tests/test_migration_dialog_run.py"
      issue: "no coverage of a missing Destination from the Result view or of modality"
  missing:
    - "Show the Destination path in the Result view above Generate Tables and the pin action, with a Browse... button; the main window passes the current Destination in and handles a destination_changed(str) signal reusing add_dest_to_history and the _on_browse_dest logic"
    - "Mirror the Generate outcome (success, Destination folder does not exist, No destination folder set) into the Result view like the import flow's _set_import_status(tables, ...)"
    - "Optionally: when the Destination is blank or missing, ask for a folder with QFileDialog.getExistingDirectory parented to the migration window; _populate_dest_combo skips or flags history entries whose folder no longer exists"
    - "Regression tests: real-dialog test that a missing Destination is shown and reported in the Result view and can be changed there; explicit modality assertion"
  debug_session: ".planning/debug/result-view-destination.md"
- gap_id: G-13-1-h
  truth: "A library picked from the migration window's Library dropdown list is saved as the owner's choice exactly like a typed one"
  status: failed
  reason: "Found during diagnosis of G-13-1-f: migration_dialog.py:752 connects only lineEdit().textEdited; an offscreen Qt probe (scratchpad/combo_probe.py) showed that selecting an item from the dropdown list emits currentTextChanged / textActivated but not textEdited, so the pick is not recorded in the draft or the plan"
  severity: major
  test: 1
  root_cause: "Only the editable combo's lineEdit().textEdited signal is connected to _on_library_edited; list selections do not emit textEdited. test_library_picker_lists_atomic_libraries_and_current fires textEdited by hand so it does not cover a list pick."
  artifacts:
    - path: "kicad_lib_manager/widgets/migration_dialog.py"
      issue: "line 752: _library_combo.lineEdit().textEdited is the only connected signal (the official-footprint combo at 834-835 does connect textActivated)"
  missing:
    - "Also connect textActivated (and/or currentTextChanged guarded against programmatic updates) to the same handler"
    - "Add a Qt test that picking a list item records the choice"
  debug_session: ".planning/debug/imu-suggested-atomic-timer.md"
