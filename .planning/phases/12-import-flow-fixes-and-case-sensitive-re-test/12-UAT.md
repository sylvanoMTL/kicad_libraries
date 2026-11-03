---
status: partial
phase: 12-import-flow-fixes-and-case-sensitive-re-test
source: [12-VERIFICATION.md, 12-09-SUMMARY.md, 12-10-SUMMARY.md, 12-11-SUMMARY.md]
started: 2026-11-01T15:45:00Z
updated: 2026-11-03T17:25:34.311Z
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
reported: "a) ok b) ok c) ok d) where is the help? e) pass" then "Help user guide is not accessible from the import part window"
severity: major

## Summary

total: 9
passed: 2
issues: 5
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
  truth: "The User Guide can be opened from the import window (Help button and F1) without closing it, so the Importing Parts page can be read while importing."
  status: failed
  reason: "User reported: Help user guide is not accessible from the import part window"
  severity: major
  test: 9
  artifacts: []
  missing: []
