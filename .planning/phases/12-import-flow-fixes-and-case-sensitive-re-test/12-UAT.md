---
status: diagnosed
phase: 12-import-flow-fixes-and-case-sensitive-re-test
source: [12-VERIFICATION.md, 12-09-SUMMARY.md, 12-10-SUMMARY.md, 12-11-SUMMARY.md, 12-15-SUMMARY.md, 12-16-SUMMARY.md, 12-17-SUMMARY.md, 12-18-SUMMARY.md, 12-19-SUMMARY.md, 12-20-SUMMARY.md]
started: 2026-11-01T15:45:00Z
updated: 2026-11-10T18:01:19.000Z
---

## Current Test

[testing complete]

## Tests

### 1. Case-sensitive install tests pass on the workstation (VER-02, D-13)
setup: PowerShell, repo root `C:\Git_Repo_Clones\Kicad_Libraries-importer`.
steps: run `.\env\Scripts\python.exe -m pytest tests/test_case_sensitive_install.py -v -rs`
expected: five lines end in PASSED (test_rollback_removes_hand_built_twin, test_rollback_planner_overwrite_keeps_disk_spelling, test_overwrite_model_twin_keeps_disk_spelling, test_overwrite_footprint_twin_keeps_disk_spelling, test_incoming_op_finds_case_twin_footprint); last line "5 passed", no "skipped", no "could not make a case-sensitive folder".
result: pass

### 2. Help pages and conflict rows follow the theme (UI-01)
setup: start the app with `.\env\Scripts\python.exe kicad_lib_manager.py`, once at 100% and once at 200% Windows display scale (Settings > System > Display > Scale; sign out/in if asked).
steps: open Help (Help menu) and visit "Importing Parts", "Generating Tables" and the requirements page. Then open a package with Ctrl+I (e.g. `downloaded_examples\ul_CSD85301Q2.zip`) into a library that already holds the part, so the conflict rows show; click Overwrite and Rename on a row.
expected: page headings larger than body text and blue; code blocks monospace on a light grey fill; Tip box pale amber; text sharp and not clipped at 200%. Conflict buttons white with a grey border; Overwrite checked = red with white bold text; Rename checked = blue with white bold text. (No underline under headings and no left bars: Qt rich text never drew them, same as before.)
result: pass

### 3. KiCad-open question before the path-variable change (REV-05)
setup: make one of the two path variables differ from this repo so the app needs to change it: in KiCad, Preferences > Configure Paths, set `KICAD_LIB_GITHUB` to any other folder, OK, and leave KiCad (or the Symbol Editor) open. Start the app.
steps: press Generate Tables (Ctrl+G) with the usual Destination.
expected: a dialog titled "KiCad is open" names the open KiCad program(s), lists the change, and offers Retry (default), Change anyway and Not now. Not now: nothing changes in KiCad's settings and the log says so. Press Generate again, close KiCad, press Retry: the normal Yes/No question appears; Yes changes the path back, and KiCad's other settings (e.g. one changed while the question was open) are kept.
result: blocked
blocked_by: other
reason: "App refused before the dialog: \"Not changing KiCad path variables: this app runs from a git worktree (C:/Git_Repo_Clones/Kicad_Libraries-importer). KICAD_LIB_GITHUB stays C:\Temp.\" The worktree / other-checkout guard (_path_var_refusal, quick-261022-gnn) runs first, so the KiCad-open dialog cannot be reached from this worktree, and changing KICAD_LIB_GITHUB itself always trips the other-checkout guard. Re-test after merge, from the main checkout, by changing CUSTOM_3DMODEL_DIR instead."

### 4. Window stays live during a real kicad-cli rebuild (REV-04)
setup: start the app; open `downloaded_examples\ul_CSD85301Q2.zip` with Ctrl+I and choose a target library so the preview builds.
steps: (a) edit one letter of the part name and immediately press Change...; (b) repeat, and press Cancel on the strip; (c) repeat, and close the import dialog with its X; (d) repeat, and close the main window with its X.
expected: each time the dialog greys out with "Finishing the preview..." and a wait cursor while the window still moves and repaints; after about 10 s a "slow to respond" note may appear; Escape does nothing while it shows. (a) the package picker opens by itself once the preview ends; (b) the dialog comes back usable; (c) the dialog closes by itself; (d) the app closes by itself. No hang, nothing written to `Custom/`.
result: skipped
reason: "Rebuild after an edit finishes before a person can click Change..., so the Finishing strip (and its Cancel) never appears by hand; the waiting state is covered by the automated tests. Owner: skip 4"

### 5. Wording that names kicad-cli and kicad_common.json (plain-language judgment, 12-REVIEW WR-04)
setup: none beyond tests 2-4.
steps: read the new Help sentences about the preview and slow note, the "Finishing the preview..." / slow-note strip, and the KiCad-open dialog and log lines.
expected: owner decides: accept the wording as is, or ask for "the KiCad command-line tool" / "KiCad's settings file" instead (a small follow-up fix).
result: issue
reported: "plain" (owner chose to replace kicad-cli and kicad_common.json with plain names)
severity: minor

### 6. Cancel button beside Install Part (found during test 2)
expected: the import window has a Cancel button to the right of Install Part that closes the window without installing, greyed out while an install runs.
result: issue
reported: "a cancel button on the right side of instal part is misisng" (owner chose: fix now)
severity: major

### 7. Description hint matches the atomic rule (found during test 2)
expected: in an Atomic_ library the empty Description box does not say it will be written blank; its hint says a Description is required, matching the "Install is blocked: Type a Description" bar.
result: issue
reported: "YOU HAVE TO ADMIT THE UI IS SUPER CONFUSING" - placeholder "Empty - the field will be written blank" while Install is blocked for no description (owner chose: fix now)
severity: major

### 8. Change... says what it does (found during test 4)
expected: the Change... button at the top right makes clear it picks a different package (label or tooltip).
result: issue
reported: "YOU HAVE TO ADMIT THE UI IS SUPER CONFUSING" - Change... alone at the top right does not say it picks another package (owner chose: fix now)
severity: minor

### 9. Gap fixes re-check (UAT 5-8)
setup: start the app with `.\env\Scripts\python.exe kicad_lib_manager.py`; press Ctrl+I, open `downloaded_examples\ul_CSD85301Q2.zip`, pick an Atomic_ target library.
steps: (a) look at the bottom row; (b) clear the Description box; (c) hover the top-right header button; (d) open Help > Importing Parts and read the Finishing paragraph; (e) press Cancel.
expected: (a) a Cancel button right of Install Part; (b) the empty box reads "Required - type a Description" (Datasheet and Manufacturer likewise say "Required - ..."), matching the "Install is blocked" strip; (c) the button reads "Choose another package..." and its tooltip says the package and edits are dropped and nothing is written; (d) Help says "the KiCad command-line tool", not kicad-cli; (e) the window closes and nothing is written to `Custom/`.
result: issue
reported: "a) ok b) ok c) ok d) where is the help? e) pass" then "Help user guide is not accessible from the import part window"; then "There is no access to help also when on the import part to open package"
severity: major

### 10. Help in the import window (re-check of 9(d), plan 12-12)
setup: start the app with `.\env\Scripts\python.exe kicad_lib_manager.py`; press Ctrl+I.
steps: (a) look at the top of the import window before opening a package; open `downloaded_examples\ul_CSD85301Q2.zip`, pick an Atomic_ target library, look again; (b) click Help; (c) click and type in the import window, then in the guide; (d) close the guide, press F1; (e) press Cancel in the import window.
expected: (a) a toolbar row at the very top of the import window shows the help icon with "Help" beside it, on the start page and the edit page; (b) clicking Help opens the User Guide on "Importing Parts" in a second window and the import window stays open; (c) you can click and type in both windows; (d) pressing F1 does the same (no second guide window); (e) Cancel closes the import window and the guide closes with it, nothing written to `Custom/`. The row looks right: icon and text not clipped, no stray gap or line.
result: issue
reported: "the inport part window is too big and has no Cancel button."
severity: major

### 11. User Guide headings numbered and listed in the left menu (found during test 10)
expected: every heading in the User Guide carries a number that matches its place in the left menu (e.g. 4.4 Importing Parts, 4.4.8 Conflicts), and the sections inside a page (Start, Items, ..., Conflicts, Install and result, Commit) appear in the left menu under their page; clicking one scrolls the page to that heading.
result: issue
reported: "The help should have numbered items, and titles should also be in the menu on the left." (screenshot: Importing Parts page with the Conflicts heading underlined; the left menu lists pages only)
severity: major

### 12. Import window fits the screen, Cancel on every page (re-check of 10, plan 12-13)
setup: at 100% and again at 200% Windows display scale (sign out/in if asked). From the repo root run `git -C Custom status --short` and note the output; start the app with `.\env\Scripts\python.exe kicad_lib_manager.py`; press Ctrl+I.
steps: (a) look at the import window; (b) open `downloaded_examples\ul_CSD85301Q2.zip`, pick an Atomic_ library; (c) press "Choose another package..."; (d) press Cancel; (e) run `git -C Custom status --short` again.
expected: (a) small window, fully on screen, Cancel at its bottom right; (b) the window grows, stays above the taskbar, Install Part and Cancel show at its bottom right; (c) the window is small again; (d) the window closes; (e) same output as noted, nothing written to `Custom/`.
result: issue
reported: "You can still reduce the size and have the browse and cancel in the same llayout grid. (screenshots at 100%: start page about 634x467 with a large empty band between Browse zip... / Browse folder... and Cancel at the bottom right; owner's sketch moves Cancel up onto the Browse row and shrinks the window to about 634x340)"
severity: cosmetic
note: "At 100%: (b)-(d) behaved as expected (owner: done); (e) git -C Custom status --short unchanged (same two untracked files as before). 200% run still to do."

### 13. User Guide numbered menu with page sections, fits the screen (re-check of 11, plan 12-14)
setup: at 100% and again at 200% Windows display scale (sign out/in if asked). Start the app with `.\env\Scripts\python.exe kicad_lib_manager.py`.
steps: (1) press F1; (2) click "4.4 Importing Parts"; (3) click its Conflicts section; (4) close the guide, press Ctrl+I, click Help in the import window, close the guide, press F1 there.
expected: (1) the guide is fully on screen above the taskbar with Close visible; the left menu reads "1 Overview", "2 Getting Started" ..., and the page heading reads "1 Overview"; (2) its sections appear under it, "4.4.1 Start" to "4.4.10 Library tables", and the page headings carry the same numbers; (3) the page scrolls to the "4.4.7 Conflicts" heading, text sharp and not cut off; (4) both times the guide opens on "4.4 Importing Parts", fully on screen with Close visible.
result: pass
note: "Checked at 100% in the Phase 12 build (owner: well done on the renumbering). 200% look still open; folded into the re-check after the gap fixes."

### 14. Start page Cancel closes without writing, waits while a package is read (12-13 D1)
expected: Start page has a Cancel at its bottom right that closes the window, writes nothing, and waits in Finishing while a package is read
result: pass
source: automated
coverage_id: D1

### 15. Start page small, grows for the edit page, shrinks back (12-13 D3)
expected: Start page opens small, the window grows for the edit page, shrinks back, and the result page keeps its size and has Close
result: pass
source: automated
coverage_id: D3

### 16. Help names the start-page Cancel and the window size (12-13 D4)
expected: Help Importing Parts, Start section, names the start page Cancel and the window size in plain words
result: pass
source: automated
coverage_id: D4

### 17. Menu numbers and page sections derived from the page text (12-14 D1)
expected: The User Guide menu numbers every entry from its place (1, 4.4, 4.4.7) and lists each page's h3 sections under that page, derived from the page text
result: pass
source: automated
coverage_id: D1

### 18. Heading numbers match the menu; section click scrolls (12-14 D2)
expected: Page and section headings show the same number as the menu; clicking a section scrolls to its heading, and clicking the selected section again scrolls back
result: pass
source: automated
coverage_id: D2

### 19. Menu follows the shown page; topic keys still open (12-14 D3)
expected: The menu opens the shown page's sections and folds the others; page, section and group keys still open from the main window, the import window Help and F1
result: pass
source: automated
coverage_id: D3

### 20. Numbered headings keep the theme look (12-14 D4)
expected: Numbered headings keep their size and colour; theme tokens only, no colour literal, no px font size
result: pass
source: automated
coverage_id: D4

### 21. Skip a library while loading at startup (raised during UAT, owner chose: fix in Phase 12)
expected: While the app loads the libraries at startup, the loading dialog offers a way to skip the library being scanned (e.g. the whole Wurth Elektronik library) so startup is faster, without breaking the scan result.
result: issue
reported: "You have not implemented the cancel (skip) button on loading the libraries when opeing the app" (first raised as: \"can we add a skip this library when scaning for the libraries ... it would skip the full Wurth Elektronic lib\"; screenshot: Loading Libraries dialog at 97%, 'Checking 3D paths: T_Wurth_WE-OLTI-EE16_7_5_750315526', empty area right of the bar circled for a Skip button)
severity: major

### 22. Main window usable while the User Guide is open (raised during test 13)
expected: The User Guide (from the main window Help menu or F1, or from the import window Help or F1) can stay open beside any other window of the app (main window, import window, other dialogs) and be browsed while those windows are used; neither blocks the other.
result: issue
reported: "is there away to be able to use the main window while the user guide is opened? same for the help" (restated after test 13: "1) a way to have the user guide and help open at the same time as any window. with possibility to browse it.")
severity: major
note: "Same message reported no numbered sections and File > Import Part missing; that window was a second app instance started 13:44 from the main checkout C:/Git_Repo_Clones/Kicad_Libraries (main @ 5fdce28, 2026-10-18), which predates the importer and plan 12-14. Not counted as issues; test 13 to be redone in the Phase 12 build."

### 23. User Guide remembers the last section browsed (raised after test 13)
expected: When the User Guide is closed and opened again (also after restarting the app), it shows the page and section last browsed, with that node selected and expanded in the left menu; a caller that asks for a given topic (import window Help/F1 opens Importing Parts) still gets that topic.
result: issue
reported: "2) Use persistence so that if we close/open, it retains the paragraph that was browsed and display it, and expand the section on the left panel. (I tink selecting and expanding the node would do the job)"
severity: major

### 24. Start page compact, Cancel on the Browse row (re-check of 12, plan 12-15)
setup: from the repo root run `git -C Custom status --short` and note the output. Windows display scale 100% (later 200%; Settings > System > Display > Scale, sign out/in if asked). Start `.\env\Scripts\python.exe kicad_lib_manager.py`.
steps: (1) press Ctrl+I; (2) open `downloaded_examples\ul_CSD85301Q2.zip`, pick an Atomic_ library; (3) press "Choose another package..."; (4) press Cancel; (5) run `git -C Custom status --short` again. Repeat 1-5 at 200%.
expected: (1) compact window: Cancel at the right end of the Browse zip... / Browse folder... row, no empty band under that row; the window does not jump when the "Newest in Downloads:" line appears; (2) the window grows, stays above the taskbar, Install Part and Cancel at its bottom right; (3) compact again; (4) the window closes; (5) same output as noted. At 200% text and buttons sharp, not cut off.
result: pass
note: "Passed at 100% (2026-11-10); git -C Custom status --short unchanged. 200% run deferred to one combined 200% pass at the end of the session."

### 25. Skip a source while the libraries load (re-check of 21, plans 12-16, 12-17)
setup: 100% scale. Close the app and delete the folder `%APPDATA%\KiCadExtLibManager\scan_cache` so the next start runs the full scan. Start `.\env\Scripts\python.exe kicad_lib_manager.py`.
steps: (1) watch the Loading Libraries window, press Escape once; (2) click "Skip WurthElektronik" while it shows; (3) close the app, start it again; (4) press Rescan and let it finish without skipping, close, start again. Repeat 1-2 at 200% (delete the scan_cache folder first).
expected: (1) the bar rises once, never restarts at 0; the button is greyed "Skip" at first, then reads "Skip Custom", then "Skip WurthElektronik" during those 3D model path checks; Escape and the title-bar X do nothing; (2) the window closes soon; the log says "3D model paths of WurthElektronik were not checked: skipped while the libraries loaded. Rescan checks them." and does not say "No warnings."; both trees still list every WurthElektronik library; (3) the log says "Showing the saved scan from ..." and that the 3D model paths of WurthElektronik were skipped in that scan; (4) the note no longer mentions a skip. At 200% the button text is sharp, not cut off.
result: pass
note: "Passed at 100% (2026-11-10): Skip WurthElektronik at startup worked, log said the 3D model paths were not checked and 'No warnings in the checks that ran.' (the intended wording after a skip), both trees kept the WurthElektronik libraries; next start showed the saved scan with the skip note; Rescan bar rose once, button went Skip -> Skip Custom -> Skip WurthElektronik, Escape and X did nothing, log ended 'No warnings.'; next start note had no skip. 200% run deferred."

### 26. User Guide usable beside every window (re-check of 22, plans 12-18, 12-20)
setup: 100% scale. From the repo root run `git -C Custom status --short` and note it. Start `.\env\Scripts\python.exe kicad_lib_manager.py`.
steps: (1) press F1; click Select All and a library check box in the main window, click pages in the guide; press F1 again; (2) open Help > About, scroll and change page in the guide, close About; (3) press Ctrl+I, try clicking the main window, click pages in the guide; click Help in the import window; open `downloaded_examples\ul_CSD85301Q2.zip`, pick an Atomic_ library, double-click a file row of the preview; click pages in the guide; (4) press Cancel in the import window; (5) press Rescan and change page in the guide while Loading Libraries shows; (6) close the main window; (7) run `git -C Custom status --short`. Repeat 1 and 3 at 200%.
expected: (1) the guide opens over the main window, fully on screen; both windows respond; the second F1 brings the same guide to the front (no second guide); (2) the guide scrolls and changes page while About is open; (3) the main window does not respond, the guide does; import Help shows the same guide on Importing Parts; the guide still responds with the content view open; (4) the guide stays open, the main window responds again; (5) the guide changes page; (6) the guide closes with it and the app ends; (7) same output as noted. At 200% the guide stays on screen with Close visible. (File pickers such as Browse zip... may block the guide while open: owner-approved.)
result: pass
note: "Passed at 100% (2026-11-10), step by step: F1 beside the main window (one guide), About, import window + Help + content view, Cancel, Rescan (guide changes page on click), closing the main window ends the app; Custom unchanged. A first 'No' on the Rescan step was a misreading of the step wording (re-run passed). 200% run deferred."

### 27. User Guide reopens where you left it (re-check of 23, plan 12-19)
setup: 100% scale. Start `.\env\Scripts\python.exe kicad_lib_manager.py`.
steps: (1) press F1, click "4.4 Importing Parts", then its Conflicts section; close the guide with Close; (2) press F1; (3) click "4.3 Generating Tables", press Escape; press Ctrl+I, click Help in the import window; press Cancel in the import window, close the guide, press F1 in the main window; (4) close the app, start it again, press F1. Repeat step 2 at 200%.
expected: (2) the guide opens on 4.4.7 Conflicts, Importing Parts open in the left menu and the other pages folded, the Conflicts heading in view; (3) the import window's Help shows Importing Parts; the main window's F1 then opens on Generating Tables, not Importing Parts; (4) the guide opens on Generating Tables. At 200% the selected row and the heading are visible and not cut off.
result: issue
reported: "No by default it is selecting 4.4 Importing Parts"
severity: major
note: "Step 1: after F1 > 4.4 Importing Parts > 4.4.7 Conflicts, Close, F1 again, the guide selected the page 4.4 Importing Parts, not the section 4.4.7 Conflicts. settings.ini [help] last_topic=importing#conflicts, so the save works; the restore of the reused hidden guide (MainWindow.show_guide -> HelpDialog.show_remembered -> show_topic) lands on the page."

## Deferred Follow-Ups

[none - the startup-scan skip idea moved to test 21 / G-12-21 on 2026-11-04, owner chose to fix it in Phase 12]

## Owner Decisions (2026-11-04, for the gap-closure plans)

- G-12-23: only the owner's own moves in the guide are remembered. Opening the guide on a given topic (import window Help/F1 -> Importing Parts) does NOT overwrite the remembered place; main-window Help/F1 reopens the page or section the owner last chose.
- G-12-21: skip unit is the source (e.g. "Skip WurthElektronik"), skipping only that source's 3D model path check. A skipped scan IS saved, with the skipped sources recorded; the next start reuses it and the log says the 3D paths of that source were skipped then and Rescan does the full check (never silent, O-04).
- G-12-21 (included): narrow the saved-scan code signature so only code that affects scan results makes the saved scan stale.
- G-12-22: the main window stays locked while the import window is open (Phase 5 design kept); only the User Guide becomes a shared free-floating window usable beside every window.
- G-12-22 (approved exclusion, asked after plan check): system file pickers (Browse zip..., Browse folder..., Add 3D model..., Set KiCad Footprint Path, the backup folder, the destination Browse..., the Check Atomic Parts model picker) may stay as they are and block the User Guide while open. Owner chose "No, pickers may block" over converting them to Qt window-modal pickers.

## Summary

total: 27
passed: 13
issues: 12
pending: 0
skipped: 1
blocked: 1

## Gaps

- gap_id: G-12-6
  truth: "The import window has a Cancel button to the right of Install Part that closes the window without installing; it is greyed out while an install runs."
  status: resolved
  resolved_by: 12-09-PLAN.md
  resolved_at: 2026-11-02
  reason: "User reported: a cancel button on the right side of instal part is misisng"
  severity: major
  test: 6
  root_cause: "The Edit page's bottom row (ImportDialog edit page builder) holds only the atomic strip, the install progress row and Install Part; no Cancel was ever specified (Phase 5 D-10 only forbade cancelling a running install). Leaving relies on the title-bar X or Escape."
  artifacts:
    - path: "kicad_lib_manager/widgets/import_dialog.py"
      issue: "bottom row ~L760-794 adds _install_btn only; reject()/closeEvent (~L3370-3407) already handle Finishing, busy builds, installing and committing"
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: "Importing Parts page does not mention a Cancel button"
  missing:
    - "QPushButton('Cancel') to the right of Install Part that calls self.reject() (same path as X/Escape, so Finishing and close waits are reused)"
    - "Cancel disabled while installing or committing, re-enabled after (follow the Install Part enable/disable points)"
    - "Help sentence + tests in tests/test_import_dialog.py (Cancel closes idle dialog; disabled during install; during a build it enters Finishing like X)"

- gap_id: G-12-5
  truth: "User-facing text names no raw tools or files: the Help page, the Finishing strip slow note, the path-variable questions (Yes/No and KiCad is open) and the keeps-changing log line say \"the KiCad command-line tool\" and \"KiCad's settings file\" instead of kicad-cli and kicad_common.json."
  status: resolved
  resolved_by: 12-11-PLAN.md
  resolved_at: 2026-11-02
  reason: "User reported: plain (replace kicad-cli / kicad_common.json with plain names)"
  severity: minor
  test: 5
  root_cause: "Phase 12 added user-facing text that names the tool and settings file by their raw names, against the owner's plain-language rule."
  artifacts:
    - path: "kicad_lib_manager/widgets/import_dialog.py"
      issue: "L107 SLOW_CLI_TEXT = 'kicad-cli is slow to respond (it gives up after 60 s)'"
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: "L320-321 'the strip adds that kicad-cli is slow to respond; kicad-cli gives up after 60 seconds'"
    - path: "kicad_lib_manager/main_window.py"
      issue: "L1118 and L1141 'These KiCad path variables in kicad_common.json would change'"
    - path: "kicad_lib_manager/library_scanner.py"
      issue: "L323 'kicad_common.json kept changing while you were asked; nothing was written.'"
  missing:
    - "Replace kicad-cli with 'the KiCad command-line tool' and kicad_common.json with \"KiCad's settings file\" in these user-facing strings"
    - "Grep all user-facing strings (widgets, main_window, library_scanner messages, help pages) for other raw kicad-cli / kicad_common.json mentions added in phase 12 and fix them the same way; keep message prefixes the caller matches on (Failed, Could not, not found, Warning:) unchanged"
    - "Update tests that assert these strings (tests/test_import_dialog.py, tests/test_kicad_config.py)"

- gap_id: G-12-7
  truth: "In an Atomic_ library the empty Description box's hint says a Description is required (not that it will be written blank), matching the atomic check that blocks Install."
  status: resolved
  resolved_by: 12-09-PLAN.md
  resolved_at: 2026-11-02
  reason: "User reported: the UI is super confusing - Description placeholder says it will be written blank while Install is blocked for no description"
  severity: major
  test: 7
  root_cause: "_BLANK_FIELD_HINT ('Empty - the field will be written blank', import_dialog.py L87) is set as the placeholder of Datasheet, Description and Manufacturer (L1110-1111). It predates the atomic rule (Phase 9/10): the importer now only accepts Atomic_ target libraries (stems.name_verdict refuses anything else), and the atomic check requires all three fields, so the hint always contradicts the 'Install is blocked: Type a Description' strip."
  artifacts:
    - path: "kicad_lib_manager/widgets/import_dialog.py"
      issue: "L87 _BLANK_FIELD_HINT; L1110-1111 applied to datasheet/description/manufacturer"
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: "Fields section says 'An emptied optional field is written blank', which no longer applies to these three fields"
  missing:
    - "Placeholder that says the field is required, in plain words (e.g. 'Required - type a Description'), for Datasheet, Description and Manufacturer"
    - "Help Fields paragraph reworded to match (these fields are required for an Atomic_ library)"
    - "Tests asserting the placeholder text updated"

- gap_id: G-12-8
  truth: "The Change... button makes clear it picks a different package."
  status: resolved
  resolved_by: 12-09-PLAN.md
  resolved_at: 2026-11-02
  reason: "User reported: the UI is super confusing - Change... does not say it picks another package"
  severity: minor
  test: 8
  root_cause: "The package header's button is labelled only 'Change...' (import_dialog.py L662) with no tooltip; it sits alone at the top right, so nothing says it discards this package and goes back to pick another one."
  artifacts:
    - path: "kicad_lib_manager/widgets/import_dialog.py"
      issue: "L662 QPushButton('Change...') with no tooltip"
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: "Help text names the button 'Change...' in several places"
  missing:
    - "Clearer label (e.g. 'Choose another package...') and a tooltip saying the current package and its edits are discarded and nothing has been written"
    - "Help pages and tests that name the button updated to the new label (grep 'Change...' in kicad_lib_manager and tests)"

- gap_id: G-12-9
  truth: "From every page of the import window (the open-package start page and the edit/preview page), the User Guide opens without closing the import window: a Help button and F1 open it on the Importing Parts page."
  status: resolved
  resolved_by: 12-12-PLAN.md
  resolved_at: 2026-11-04
  reason: "User reported: Help user guide is not accessible from the import part window; also not from the open-package page"
  severity: major
  test: 9
  root_cause: "ImportDialog sets Qt.WindowModality.WindowModal (import_dialog.py L494), so while it is open the main window's Help menu and its F1 QAction (main_window.py L297-304, window-scoped shortcut) cannot be reached. The import dialog itself has no Help button and no F1 shortcut on any page (start page _build_start_page ~L547-642, edit page bottom row ~L790-810, result page ~L897). HelpDialog (help_dialog.py L481) always opens on the first topic; it has no way to open on a given page such as 'importing'."
  artifacts:
    - path: "kicad_lib_manager/widgets/import_dialog.py"
      issue: "WindowModal at L494; no Help button or F1 shortcut on the start, edit or result pages"
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: "HelpDialog.__init__ selects topLevelItem(0); no topic argument to open on Importing Parts (TOC key 'importing')"
    - path: "kicad_lib_manager/main_window.py"
      issue: "_on_help (L1307) opens HelpDialog(parent=self).exec(); only reachable when no import dialog is open"
  missing:
    - "HelpDialog accepts an optional topic key (e.g. topic='importing') and selects that TOC item on open; default unchanged"
    - "A Help button on the import window reachable from every page (start, edit, result), e.g. in a shared top or bottom row, opening HelpDialog(topic='importing', parent=self) without closing the import dialog"
    - "F1 inside the import window opens the same page (QShortcut on the dialog)"
    - "Help page Importing Parts and Keyboard Shortcuts mention the Help button / F1 inside the import window"
    - "Tests in tests/test_import_dialog.py and tests/test_help_dialog.py: Help button exists on start and edit pages, F1 opens HelpDialog on 'Importing Parts', import dialog stays open; HelpDialog(topic=...) selects the topic"

- gap_id: G-12-10
  truth: "The import window fits on the screen and shows a Cancel button (beside Install Part on the edit page, and a way to cancel on the start page) without resizing or scrolling."
  status: resolved
  resolved_by: 12-13-PLAN.md
  resolved_at: 2026-11-04
  reason: "User reported: the inport part window is too big and has no Cancel button. Screenshot of the start page (Choose a part package): window opens near full screen (~1100x750), content is a narrow centred column with large empty margins; only Open, Browse zip..., Browse folder... and the toolbar Help; no Cancel anywhere on the page."
  severity: major
  test: 10
  root_cause: "Two causes. (1) G-12-6 (plan 12-09) added Cancel only to the edit page's bottom row (import_dialog.py L846-849); the start page (_build_start_page L587-654) has Open, Browse zip... and Browse folder... and no way to leave except the title-bar X or Escape; the result page was not checked either. (2) ImportDialog.__init__ always calls self.resize(1100, 720) and setMinimumSize(900, 600) (L499-500) for every page, never limited to the screen's available area. The start page is a 560-wide column, so the window is mostly empty, and on a scaled or small display the fixed 720 px height reaches or passes the taskbar, which can also push the edit page's bottom row (Install Part, Cancel) out of view."
  artifacts:
    - path: "kicad_lib_manager/widgets/import_dialog.py"
      issue: "L499-500 fixed resize(1100, 720) / setMinimumSize(900, 600), not clamped to screen availableGeometry; start page L587-654 has no Cancel"
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: "Importing Parts page mentions Cancel beside Install Part only"
  missing:
    - "A Cancel button on the start page (and on any other page without a way out) that calls self.reject(), the same close path as the X and Escape, so Finishing and the install/commit refusals are reused"
    - "Initial size limited to the screen: take the available geometry of the screen the dialog opens on and shrink the 1100x720 default (and the minimum, if needed) so the whole window, bottom row included, is on screen at 100% and 200% scale"
    - "Start page should not open huge: a smaller start size or a size that grows when the edit page is shown, without breaking the edit page's splitter layout"
    - "Help sentence for the start-page Cancel; tests in tests/test_import_dialog.py: Cancel exists on the start page and closes the dialog without writing; window size never exceeds the screen's available geometry"
  debug_session: ""

- gap_id: G-12-11
  truth: "User Guide headings are numbered to match the left menu, and each page's sections are listed in the left menu under that page; clicking a section scrolls to its heading."
  status: resolved
  resolved_by: 12-14-PLAN.md
  resolved_at: 2026-11-04
  reason: "User reported: The help should have numbered items, and titles should also be in the menu on the left."
  severity: major
  test: 11
  root_cause: "help_dialog.py TOC_STRUCTURE (L461-482) is a hand-written two-level list (group -> page); the <h3> sections inside each HELP_PAGES entry (e.g. Importing Parts has Start, Items, Target library, Footprint, Fields, Atomic check, Conflicts, Install and result, Commit, Library tables) have no anchors and are not in the tree, and _on_topic_selected (L550-562) only does setHtml per page. Nothing numbers the groups, pages or sections, in the tree or in the <h2>/<h3> text."
  artifacts:
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: "TOC_STRUCTURE two levels only; _build_toc / _on_topic_selected / show_topic know pages, not sections; page HTML <h2>/<h3> unnumbered and without anchors"
    - path: "tests/test_help_dialog.py"
      issue: "tests that assert TOC labels, heading text or show_topic keys will need updating"
  missing:
    - "Derive section entries from each page's <h3> headings (one source of truth, so tree and page cannot drift) and add them as a third tree level under their page, with an anchor per heading; clicking a section shows the page and scrolls to the anchor (QTextBrowser.scrollToAnchor)"
    - "Number groups, pages and sections from their tree order (1, 4.4, 4.4.8) and show the same number in the tree label and in the page heading, computed at render time, not typed into the HTML"
    - "show_topic(key) keeps working for page keys (import window opens on 'importing'); optionally accept a section key"
    - "Tests: every <h3> of every page appears in the tree under its page with a matching number; clicking a section item scrolls to it; heading numbers match tree numbers; HelpDialog(topic='importing') still opens Importing Parts"
  debug_session: ""

- gap_id: G-12-21
  truth: "While the app loads the libraries at startup, the loading dialog offers a way to skip the library being scanned (e.g. the whole Wurth Elektronik library) so startup is faster, without breaking the scan result."
  status: resolved
  resolved_by: 12-17-PLAN.md
  resolved_at: 2026-11-05
  reason: "User reported: You have not implemented the cancel (skip) button on loading the libraries when opeing the app"
  severity: major
  test: 21
  root_cause: "Never built at any layer. main_window._start_scan (L480-488) builds 'Loading Libraries' as a QProgressDialog and calls setCancelButton(None); canceled is unconnected. ScanWorker.run (L87-137) has no stop/skip state and saves every scan to scan_cache unconditionally (L122-134). scan_all (library_scanner.py L603-634) and its per-file loops take only a progress callback. About 63 of ~70 s is the per-file 3D model path check over 5645 Wurth footprints (_check_model_files L553-593); listing libraries takes 0.25 s and reading symbol footprint links 6 s. The saved scan is also discarded whenever any package .py changes (scan_cache._code_signature L194-210), so during development nearly every start runs the full scan."
  artifacts:
    - path: "kicad_lib_manager/main_window.py"
      issue: "L480-488 dialog has no button (setCancelButton(None)); L73-137 ScanWorker has no skip request and saves every scan as complete; L512-515 _on_scan_progress does not know the source; L586-625 _on_scan_finished claims 'No warnings.' unqualified"
    - path: "kicad_lib_manager/library_scanner.py"
      issue: "scan_all L603-634 has no skip hook and does not report the current source; _check_model_files L553-593 per-file loop is where a per-source skip belongs"
    - path: "kicad_lib_manager/models.py"
      issue: "ScanResult has no marker for skipped sources"
    - path: "kicad_lib_manager/scan_cache.py"
      issue: "save L401-437, encode/decode L372-388, load_fresh L477-536 carry no skipped sources; _code_signature L194-210 hashes the whole package"
    - path: "kicad_lib_manager/table_generator.py"
      issue: "_merge_table L165-178 removes managed entries missing from the scan as stale, so a skip must never drop libraries"
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: "HELP_PAGES['repo_scan'] L110-125 does not mention the saved scan or Skip"
    - path: "tests/test_main_window.py"
      issue: "L49 fake_scan(root, progress=None, kicad_fp_dir=None) breaks with a new keyword; same in tests/test_main_window_import.py L62+"
  missing:
    - "A Skip button on the Loading Libraries dialog (startup and Rescan) that names the source being checked (e.g. 'Skip WurthElektronik') and is active only while that source can be skipped"
    - "A thread-safe skip request on ScanWorker (lock or threading.Event) passed to scan_all as an optional plain-callable skip hook (library_scanner and scan_cache stay Qt-free, tests/test_layering.py)"
    - "scan_all reports the current source and checks the hook per file in _check_model_files; a skipped source's 3D model path check stops while its libraries are still listed and its symbol footprint links still read (never dropped or emptied, so Generate Tables removes nothing and pre-select / footprint auto-select keep working)"
    - "ScanResult records skipped sources; one plain log line says what was skipped and that Rescan checks it again; 'No warnings.' is not claimed after a skip"
    - "Saved scan stays honest per the owner's choice: either a skipped scan is not saved, or it is saved with the skipped sources and the reuse note says so (never reused silently as complete, O-04)"
    - "Optional: progress weighted across phases so the bar does not restart at 0; narrow _code_signature to modules that affect scan output"
    - "Help 'Repository Scan' page and CLAUDE.md GUI Behavior explain Skip in plain words"
    - "Tests: Skip button exists and sets the request; a skipped source keeps all libraries and footprint links and only its 3D path lines are absent; Generate Tables after a skip removes no Wurth entry; saved-scan behaviour after a skip; update fake_scan signatures in tests/test_main_window.py and tests/test_main_window_import.py"
  debug_session: ""

- gap_id: G-12-12
  truth: "The import start page is compact: Browse zip..., Browse folder... and Cancel share one row (same layout grid), with no large empty band, so the window opens smaller."
  status: resolved
  resolved_by: 12-15-PLAN.md
  resolved_at: 2026-11-05
  reason: "User reported: You can still reduce the size and have the browse and cancel in the same llayout grid. (screenshots at 100%: start page about 634x467 with a large empty band between Browse zip... / Browse folder... and Cancel at the bottom right; owner's sketch moves Cancel up onto the Browse row and shrinks the window to about 634x340)"
  severity: cosmetic
  test: 12
  root_cause: "The start page has a fixed 640x440 size (import_dialog.py:82 _START_SIZE, applied at :554 and _show_page :614) that is taller than its content (layout wants about 476x316), and outer.addStretch(1) (:690) between the centred column and the separate _start_bottom Cancel row (:768-776) absorbs the extra height, leaving a ~144 px band between the Browse row and Cancel. _fit_size only clamps to the screen, never to the content. The 440 'room for the issue list' rationale does not hold: the window grows by itself through its layout minimum when issues show."
  artifacts:
    - path: "kicad_lib_manager/widgets/import_dialog.py"
      issue: ":82 _START_SIZE = QSize(640, 440) used at :554 and :614; :690 outer.addStretch(1); :737-742 Browse row is a local layout; :768-776 separate _start_bottom Cancel row; :1338 showEvent refit and :1357-1379 _on_offer_found show the Downloads offer row after the window is shown"
    - path: "tests/test_import_dialog.py"
      issue: ":6042-6044 asserts Cancel last in _start_bottom; :6151 test_start_page_opens_small and :6170 test_window_grows_for_the_edit_page_and_shrinks_back pin 640x440"
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: ":226-227 Start section says Cancel is at the bottom right"
    - path: "tests/test_help_dialog.py"
      issue: ":145-148 test_help_names_the_start_page_cancel requires 'bottom right'"
  missing:
    - "Move _start_cancel_btn into the Browse zip... / Browse folder... row after its stretch (Cancel at the row's right end); remove the separate _start_bottom row; keep the row as an attribute (e.g. self._start_buttons) for tests"
    - "Replace the fixed 640x440 start size with width 640 and a height taken from the layout at that width (heightForWidth / sizeHint) in __init__, showEvent and _show_page(start); fix the 'room for the issue list' comment"
    - "Reserve the Downloads offer row's space before the lookup finishes (setRetainSizeWhenHidden or one shared slot with the reading box) so the window does not open ~44 px short and squeeze when the offer appears"
    - "Tests: Browse row holds Browse zip..., Browse folder... and Cancel (Cancel last after a spacer); start size is width 640 and the computed compact height; no empty band (Cancel top == Browse zip... top; height <= layout height at 640) at 100% and 200%"
    - "Help Importing Parts > Start says in plain words Cancel sits next to Browse zip... and Browse folder...; on the editing step it stays at the bottom right, right of Install Part; update test_help_names_the_start_page_cancel"
    - "Optional: refit the window after _show_start_issues so the many-issues state stays inside a 200% Full HD screen"
  debug_session: ""

- gap_id: G-12-22
  truth: "The User Guide (from the main window Help menu or F1, or from the import window Help or F1) can stay open beside any other window of the app (main window, import window, other dialogs) and be browsed while those windows are used; neither blocks the other."
  status: resolved
  resolved_by: 12-20-PLAN.md
  resolved_at: 2026-11-05
  reason: "User reported: is there away to be able to use the main window while the user guide is opened? same for the help"
  severity: major
  test: 22
  root_cause: "Three causes. (1) MainWindow._on_help (main_window.py:1307-1308) runs HelpDialog(parent=self).exec(); exec() makes the guide ApplicationModal, blocking every other window, and builds a new guide per F1. (2) The import window's guide (import_dialog.py:633-649, parent=self) escapes the import dialog's WindowModal only because it descends from it; any window-modal child of the import dialog (ContentViewDialog content_view.py:43 opened at import_dialog.py:2516, AtomicCheckDialog opened at :3279) blocks it, and _shutdown closes it with the import window (:3508-3510). (3) A guide parented to the main window is blocked by the import dialog and the scan progress dialog (transientParent is the main window even with Qt.Window/Qt.Tool); only a parentless guide escapes window-modal dialogs, and ApplicationModal exec() dialogs (path-variable QMessageBox.question :1122, KiCad-open box :1158, BackupDialog.exec :1260, About :1321) block even a parentless guide. A parentless visible guide keeps the app running after the main window closes."
  artifacts:
    - path: "kicad_lib_manager/main_window.py"
      issue: "L1307-1308 _on_help uses exec() and a new instance per call; L1009-1025 _open_import must hand the import dialog a way to show the shared guide; L1323-1351 closeEvent must close the guide once the close is accepted; L1122, L1136-1158, L1260, L1311-1321 are ApplicationModal"
    - path: "kicad_lib_manager/widgets/import_dialog.py"
      issue: "L446 _help_dialog and L633-649 _on_help keep a private guide parented to self; L3508-3510 _shutdown closes the guide; comment at L643 states the old reasoning"
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: "HelpDialog works parentless but first show is no longer centred over the main window; Help text L233-235 and the F1 row L446-447 should say the guide is its own window"
    - path: "kicad_lib_manager/widgets/backup_dialog.py"
      issue: "opened with exec() (ApplicationModal) at main_window.py:1260"
    - path: "tests/test_import_dialog.py"
      issue: "L5847-5859 assert guide parent is the import dialog / one child guide; L5906, L5930, L5958, L5993, L6031-6032 assert the guide closes with the import window; L6203 reads dialog._help_dialog"
    - path: "tests/test_main_window.py"
      issue: "no test covers _on_help or guide modality; L96 and tests/test_main_window_import.py L116 monkeypatch QMessageBox.question"
  missing:
    - "MainWindow._on_help: no exec(); one shared HelpDialog created with parent=None, kept on the main window, shown with show()/raise_()/activateWindow() and reused on every Help menu click or F1"
    - "ImportDialog Help action and F1 show the shared guide on Importing Parts (show_topic('importing')) through an injected callable or signal wired in _open_import (widgets never import main_window); parentless fallback guide when no hook is given; never parent the guide to the import dialog"
    - "ImportDialog._shutdown no longer closes the guide (drop the 12-12 'guide closes with the import window' rule)"
    - "MainWindow.closeEvent closes the guide once the close is accepted (after the install/commit/finishing/path-check ignore branches)"
    - "First show of the shared guide placed on the main window's screen; fit_window still applies"
    - "Main-window dialogs that are ApplicationModal today made WindowModal so they never block the guide: About, KiCad-open box, path-variable question (replace static QMessageBox.question), BackupDialog"
    - "Help text: Importing Parts > Start and the Keyboard Shortcuts F1 row say in plain words the User Guide is its own window that stays open beside the main window and the import window"
    - "Tests (window-system clicks via QTest.mouseClick(QWindow, ...)): main window F1/Help opens a non-modal guide and main window buttons still take clicks; a second F1 reuses the same guide; the guide takes clicks while the import window, its content view, Check Atomic Parts dialog, or the scan progress dialog is open; the guide stays open after the import window closes; import Help/F1 still opens Importing Parts; closing the main window closes the guide; update the import-dialog help tests and QMessageBox.question monkeypatches listed above"
  debug_session: ""

- gap_id: G-12-23
  truth: "When the User Guide is closed and opened again (also after restarting the app), it shows the page and section last browsed, with that node selected and expanded in the left menu; a caller that asks for a given topic (import window Help/F1 opens Importing Parts) still gets that topic."
  status: resolved
  resolved_by: 12-19-PLAN.md
  resolved_at: 2026-11-05
  reason: "User reported: 2) Use persistence so that if we close/open, it retains the paragraph that was browsed and display it, and expand the section on the left panel. (I tink selecting and expanding the node would do the job)"
  owner_note: "Note that it is good on importing part; by default we are already on import part, that behavious can be kept (import window Help/F1 keeps opening on Importing Parts; the remembered section applies when no topic is asked for)"
  severity: major
  test: 23
  root_cause: "The guide has no saved place. HelpDialog.__init__ (help_dialog.py:598-600) opens on the first menu item whenever no topic is given and never reads a saved key; nothing saves the current key (settings.py has no help/* key; _on_topic_selected L638-655 writes nothing; no closeEvent/done/hideEvent hook); and MainWindow._on_help (main_window.py:1307-1308) builds a new guide per F1, so the place is lost on close. Saving on close is not enough: Esc/reject() skip closeEvent and deleting the parent fires no event, so the key must be saved each time a page or section is shown. Restore already works through show_topic(key)."
  artifacts:
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: "__init__ L598-600 never reads a saved key and selects topLevelItem(0); _on_topic_selected L638-655 saves nothing"
    - path: "kicad_lib_manager/settings.py"
      issue: "no load_help_topic/save_help_topic helpers or 'help/last_topic' key"
    - path: "kicad_lib_manager/main_window.py"
      issue: "L1307-1308 new guide per F1 (see G-12-22)"
    - path: "kicad_lib_manager/widgets/import_dialog.py"
      issue: "L635-649 passes topic='importing'; keep as is (owner_note)"
    - path: "tests/test_help_dialog.py"
      issue: "no _isolated_settings fixture, so saving would write the real settings.ini; L419-424 test_help_dialog_opens_on_a_given_topic asserts a fresh HelpDialog() opens on Overview right after an Importing Parts one"
  missing:
    - "settings.py: load_help_topic() -> str | None and save_help_topic(key) under 'help/last_topic' in a new '# ── User Guide ──' section; a non-string or empty value reads as None"
    - "help_dialog.py __init__: when topic is None, read the saved key BEFORE any menu selection, then show_topic(saved) -> show_topic(saved page part) -> first item; an explicit topic never reads the saved key"
    - "help_dialog.py _on_topic_selected: save entry.key for every page and section shown per the owner's choice on explicit-topic opens (after the group early return; not in closeEvent)"
    - "Restore selects the node, expands its page, folds the others and scrolls the section heading into view once shown; exact pixel scroll is out of scope (owner: selecting and expanding the node does the job)"
    - "main_window._on_help passes no topic; with the shared guide of G-12-22, F1 only shows and raises it and never calls show_topic"
    - "import_dialog Help/F1 keeps opening 'importing' (owner_note)"
    - "tests/test_help_dialog.py: autouse _isolated_settings(tmp_path) fixture (pattern of tests/test_import_dialog.py:38-46); change test_help_dialog_opens_on_a_given_topic L419-424 to 'no topic and nothing saved: Overview'"
    - "Tests: browse to importing#conflicts, close via Close, Esc and deleting the parent; a new HelpDialog() opens there with Importing Parts expanded and 4.4.7 Conflicts in view; a key saved only through save_help_topic (app restart) is restored; an explicit topic wins over a saved key and import Help/F1 still opens 'importing'; stale keys fall back (unknown section -> its page, unknown page -> Overview, group -> first child, empty -> Overview)"
  debug_session: ""

- gap_id: G-12-27
  truth: "When the User Guide is closed and opened again, it shows the section last chosen (e.g. 4.4.7 Conflicts) with that section selected in the left menu, its page opened out and its heading in view."
  status: failed
  reason: "User reported: No by default it is selecting 4.4 Importing Parts"
  severity: major
  test: 27
  root_cause: "Inconclusive for the exact report (owner saw the page row 4.4 selected and the page top), not reproduced on the real Windows desktop in 7 full-app runs; settings.ini kept last_topic=importing#conflicts throughout. Two confirmed defects on the real platform: D1 - reopening never brings the section heading back into view: show_topic on the already-current item emits no currentItemChanged, so _on_topic_selected (the only scrollToAnchor) never runs on a reused guide; if the page was scrolled before Close it reopens at the page top ('4.4 Importing Parts'). Also the anchor scroll before show lands short whenever fit_window narrows the guide in showEvent. D3 - a menu click can select and save the wrong row: QTimer.singleShot(0, _sync_expansion) folds and opens pages while the mouse button is still held (a real press spans several event-loop turns), so the rows move under the cursor and the release selects the row now under it (e.g. with Generating Tables open, a click on 4.4 lands on 4.4.1 Start). Also: in the windows11 style the selected row (faint grey fill plus a 3 px bar at the far left) looks like a hovered row. Remaining possibility for the exact report: a quiet move to the page row (import window Help/F1 -> show_topic('importing')) combined with D1."
  artifacts:
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: "show_topic L640-658 / show_remembered L630-638 never re-scroll to the anchor when the item is already current; _on_topic_selected L678-698 schedules _sync_expansion with QTimer.singleShot(0) while the mouse button is still down; showEvent fit_window can narrow the window after the anchor scroll"
    - path: "kicad_lib_manager/main_window.py"
      issue: "show_guide L1356-1374 reshows a hidden guide through show_remembered, inheriting D1"
    - path: "tests/test_help_dialog.py"
      issue: "persistence tests use QTest.mouseClick (instant press/release), so they never hold the button across event-loop turns and miss D3; no test scrolls the page away before Close"
  missing:
    - "After every show of the guide (new or reused) and once fit_window has finished, scroll the browser to the current section's anchor, including when show_remembered selects the already-current item"
    - "Fold and open menu pages only after the mouse release (or ignore drag-selection under a held button), so a click selects and saves the row that was pressed"
    - "Optional: make the selected menu row clearly different from a hovered row in the windows11 style"
    - "Tests: choose a section, scroll the page to the top, Close, reopen -> heading in view; a press held across event-loop turns on a page row selects that row, not a shifted one; fresh guide after fit_window narrows the width still shows the heading"
    - "Re-check (UAT): if the page row still shows after the fix, run the tracer C:/Users/sylvain/AppData/Local/Temp/claude/258e6a257498df82/1c63b19d-e7f0-4611-9982-ec8610123914/scratchpad/probe/guide_trace.py in place of kicad_lib_manager.py and return guide_trace.log"
  debug_session: ".planning/debug/guide-reopens-on-page-not-section.md"
