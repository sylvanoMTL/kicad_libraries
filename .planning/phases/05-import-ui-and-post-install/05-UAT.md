---
status: testing
phase: 05-import-ui-and-post-install
source: [05-VERIFICATION.md]
started: 2026-10-22T00:00:00Z
updated: 2026-10-22T00:00:00Z
---

## Where to run it

Run the app from this development worktree (`C:/Git_Repo_Clones/Kicad_Libraries-importer`, branch `feature/part-importer`), which is the only checkout with the phase 5 code:

```
.\env\Scripts\python.exe kicad_lib_manager.py
```

- The install writes into this worktree's `Custom/` submodule, which is the development copy, not the real library at `C:/Git_Repo_Clones/Kicad_Libraries`.
- Set Destination to a scratch folder (for example a copy of a test project), not a real KiCad project.
- Generate and the post-install step will refuse to change KiCad's path variables because this is a git worktree (quick task 261022-gnn). That WARNING is expected.

## Current Test

number: 1
name: Owner UAT steps 1-10 (05-11): import the UL sample end to end
expected: |
  Progress shows, the Result view lists files and warnings, the library list rescans behind the dialog, and the library is checked, expanded and current in both trees. For a new library, sym-lib-table and fp-lib-table in the scratch destination gain exactly one entry each. git -C Custom status shows the new files uncommitted and nothing is pushed.
awaiting: user response

## Tests

### 1. Owner UAT steps 1-10 (05-11): import the UL sample end to end
steps: |
  1. File > Import Part... (Ctrl+I) shows the newest Downloads zip with its age; nothing opens until you click Open or Browse.
  2. Open downloaded_examples/ul_CSD85301Q2.zip. Install Part is blocked with the placeholder reason for IC_SubCategory_TI, and SubCategory is amber.
  3. Type a new name such as Transistor_MOSFET_TI (badge "new - creates .kicad_sym + .pretty"), or pick an existing IC_*_TI library. The Footprint field shows {Lib}:DQK0006B, Path rewrites show ${CUSTOM_3DMODEL_DIR}/CSD85301Q2.stp, and the Format rows state the kicad-cli action.
  4. Empty Datasheet and check the preview diff shows an empty Datasheet value; restore it with the undo arrow. Double-click a Files row to see its content.
  5. If a conflict appears, choose a resolution per row; check there is no overwrite-all.
  6. Click Install Part.
  7. For a new library, check the scratch destination's sym-lib-table and fp-lib-table gained exactly one entry each and nothing else changed. For an existing library missing from the tables, the Generate hint appears.
  10. Afterwards, git -C Custom status shows the new files uncommitted (Phase 6 owns the commit), and nothing was pushed.
expected: Progress shows, the Result view lists files and warnings, the library list rescans behind the dialog, and the library is checked, expanded and current in both trees; tables and Custom as described above.
result: [pending]

### 2. KiCad-running notice and KiCad loading the part (05-11 step 8, POST-05, assumption A4)
steps: |
  With KiCad's Symbol Editor open, install a part and watch the Result view. Then reopen the editor and load the part, including one installed with an emptied Datasheet. Point KiCad at this worktree's Custom/ only through a scratch project's tables, not by changing the global path variables.
expected: The amber "KiCad is running. Reopen KiCad's Symbol and Footprint editors to see <Lib>." notice appears and is logged as a WARNING. After reopening, KiCad loads the symbol, footprint and 3D model and accepts an empty Datasheet value.
result: [pending]

### 3. Visual checks at 100% and 150% scaling (05-07, 05-09, 05-10, 05-11 step 9)
steps: |
  At the 900x600 minimum window size, at 100% and at 150% display scaling, look at the Start page, the left pane (items, target library badge and token line, fields), the blocking-reason strip, conflict rows, the install progress row, the failure banner and the Result view.
expected: No name is clipped, the left pane has no horizontal scroll bar, the amber frames, strip, badge and tinted banners read correctly, and Tab/Enter work on strip links and conflict rows. (Dark mode, high contrast and scaling above 150% are out of scope; note anything you see.)
result: [pending]

### 4. Help re-check (05-11 Task 3)
steps: |
  After the test 1 install, press F1 and read How to Use > Importing Parts, and the Generating Tables bullet about KiCad path variables.
expected: The Conflicts, Install and result, and Library tables sections describe what you saw in test 1, with no step the app does not have. The path-variable bullet matches the confirmation and the worktree refusal you saw.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
