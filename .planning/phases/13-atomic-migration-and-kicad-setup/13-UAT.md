---
status: complete
phase: 13-atomic-migration-and-kicad-setup
source: [13-VERIFICATION.md]
started: 2026-11-12T13:05:57Z
updated: 2026-11-12T17:41:12.531Z
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
  artifacts:
    - path: "kicad_lib_manager/widgets/migration_dialog.py"
      issue: "_CommitStepHost.start annotates plan: CommitPlan but CommitPlan is not imported in the module"
  missing: []    # Filled by diagnosis
- gap_id: G-13-1-b
  truth: "The Loading Libraries window's Skip button is available during the symbol scan stage, not only during the 3D model path check"
  status: failed
  reason: "User reported: the skip button is grayed out I guess for the symbol scanning, This should not be grayed out. user can skip that stage."
  severity: minor
  test: 1
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis
- gap_id: G-13-1-c
  truth: "The File menu action, its shortcut tooltip, the Result view button, the log lines and the User Guide call the action 'Pin Atomic Libraries in KiCad...' instead of 'Set Up KiCad Chooser...'"
  status: failed
  reason: "User reported: 'KiCad Chooser' is vague on its own; 'Pin Atomic Libraries in KiCad...' is much better"
  severity: cosmetic
  test: 1
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis
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
  artifacts:
    - path: "kicad_lib_manager/importer/migration/planner.py"
      issue: "prepare_context / suggestion maps the IMU to Atomic_Timer"
  missing: []    # Filled by diagnosis
- gap_id: G-13-1-g
  truth: "Generate Tables in the migration Result view lets the owner see and change the Destination folder, or the Result view shows which Destination it will write to"
  status: failed
  reason: "Observed in the live run: the migration window blocks the main window, so the Destination box (still pointing at a deleted throwaway folder from step (c)) could not be changed before pressing Generate Tables in the Result view; the owner had to close the migration window and generate from the main window instead"
  severity: minor
  test: 1
  artifacts:
    - path: "kicad_lib_manager/widgets/migration_dialog.py"
      issue: "Result view's Generate Tables uses the main window Destination without showing or allowing to change it"
  missing: []    # Filled by diagnosis
