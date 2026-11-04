---
status: partial
phase: 12-import-flow-fixes-and-case-sensitive-re-test
source: [12-VERIFICATION.md, 12-09-SUMMARY.md, 12-10-SUMMARY.md, 12-11-SUMMARY.md]
started: 2026-11-01T15:45:00Z
updated: 2026-11-04T13:55:25.061Z
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

## Deferred Follow-Ups

[none - the startup-scan skip idea moved to test 21 / G-12-21 on 2026-11-04, owner chose to fix it in Phase 12]

## Summary

total: 23
passed: 10
issues: 11
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
  status: failed
  reason: "User reported: You have not implemented the cancel (skip) button on loading the libraries when opeing the app"
  severity: major
  test: 21
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis

- gap_id: G-12-12
  truth: "The import start page is compact: Browse zip..., Browse folder... and Cancel share one row (same layout grid), with no large empty band, so the window opens smaller."
  status: failed
  reason: "User reported: You can still reduce the size and have the browse and cancel in the same llayout grid. (screenshots at 100%: start page about 634x467 with a large empty band between Browse zip... / Browse folder... and Cancel at the bottom right; owner's sketch moves Cancel up onto the Browse row and shrinks the window to about 634x340)"
  severity: cosmetic
  test: 12
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis

- gap_id: G-12-22
  truth: "The User Guide (from the main window Help menu or F1, or from the import window Help or F1) can stay open beside any other window of the app (main window, import window, other dialogs) and be browsed while those windows are used; neither blocks the other."
  status: failed
  reason: "User reported: is there away to be able to use the main window while the user guide is opened? same for the help"
  severity: major
  test: 22
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis

- gap_id: G-12-23
  truth: "When the User Guide is closed and opened again (also after restarting the app), it shows the page and section last browsed, with that node selected and expanded in the left menu; a caller that asks for a given topic (import window Help/F1 opens Importing Parts) still gets that topic."
  status: failed
  reason: "User reported: 2) Use persistence so that if we close/open, it retains the paragraph that was browsed and display it, and expand the section on the left panel. (I tink selecting and expanding the node would do the job)"
  owner_note: "Note that it is good on importing part; by default we are already on import part, that behavious can be kept (import window Help/F1 keeps opening on Importing Parts; the remembered section applies when no topic is asked for)"
  severity: major
  test: 23
  artifacts: []  # Filled by diagnosis
  missing: []    # Filled by diagnosis
