---
status: testing
phase: 12-import-flow-fixes-and-case-sensitive-re-test
source: [12-VERIFICATION.md]
started: 2026-11-01T15:45:00Z
updated: 2026-11-01T15:45:00Z
---

## Current Test

number: 1
name: Case-sensitive install tests pass on the workstation (VER-02, D-13)
expected: |
  5 passed, 0 skipped; no "could not make a case-sensitive folder" line.
awaiting: user response

## Tests

### 1. Case-sensitive install tests pass on the workstation (VER-02, D-13)
setup: PowerShell, repo root `C:\Git_Repo_Clones\Kicad_Libraries-importer`.
steps: run `.\env\Scripts\python.exe -m pytest tests/test_case_sensitive_install.py -v -rs`
expected: five lines end in PASSED (test_rollback_removes_hand_built_twin, test_rollback_planner_overwrite_keeps_disk_spelling, test_overwrite_model_twin_keeps_disk_spelling, test_overwrite_footprint_twin_keeps_disk_spelling, test_incoming_op_finds_case_twin_footprint); last line "5 passed", no "skipped", no "could not make a case-sensitive folder".
result: [pending]

### 2. Help pages and conflict rows follow the theme (UI-01)
setup: start the app with `.\env\Scripts\python.exe kicad_lib_manager.py`, once at 100% and once at 200% Windows display scale (Settings > System > Display > Scale; sign out/in if asked).
steps: open Help (Help menu) and visit "Importing Parts", "Generating Tables" and the requirements page. Then open a package with Ctrl+I (e.g. `downloaded_examples\ul_CSD85301Q2.zip`) into a library that already holds the part, so the conflict rows show; click Overwrite and Rename on a row.
expected: page headings larger than body text and blue; code blocks monospace on a light grey fill; Tip box pale amber; text sharp and not clipped at 200%. Conflict buttons white with a grey border; Overwrite checked = red with white bold text; Rename checked = blue with white bold text. (No underline under headings and no left bars: Qt rich text never drew them, same as before.)
result: [pending]

### 3. KiCad-open question before the path-variable change (REV-05)
setup: make one of the two path variables differ from this repo so the app needs to change it: in KiCad, Preferences > Configure Paths, set `KICAD_LIB_GITHUB` to any other folder, OK, and leave KiCad (or the Symbol Editor) open. Start the app.
steps: press Generate Tables (Ctrl+G) with the usual Destination.
expected: a dialog titled "KiCad is open" names the open KiCad program(s), lists the change, and offers Retry (default), Change anyway and Not now. Not now: nothing changes in KiCad's settings and the log says so. Press Generate again, close KiCad, press Retry: the normal Yes/No question appears; Yes changes the path back, and KiCad's other settings (e.g. one changed while the question was open) are kept.
result: [pending]

### 4. Window stays live during a real kicad-cli rebuild (REV-04)
setup: start the app; open `downloaded_examples\ul_CSD85301Q2.zip` with Ctrl+I and choose a target library so the preview builds.
steps: (a) edit one letter of the part name and immediately press Change...; (b) repeat, and press Cancel on the strip; (c) repeat, and close the import dialog with its X; (d) repeat, and close the main window with its X.
expected: each time the dialog greys out with "Finishing the preview..." and a wait cursor while the window still moves and repaints; after about 10 s a "slow to respond" note may appear; Escape does nothing while it shows. (a) the package picker opens by itself once the preview ends; (b) the dialog comes back usable; (c) the dialog closes by itself; (d) the app closes by itself. No hang, nothing written to `Custom/`.
result: [pending]

### 5. Wording that names kicad-cli and kicad_common.json (plain-language judgment, 12-REVIEW WR-04)
setup: none beyond tests 2-4.
steps: read the new Help sentences about the preview and slow note, the "Finishing the preview..." / slow-note strip, and the KiCad-open dialog and log lines.
expected: owner decides: accept the wording as is, or ask for "the KiCad command-line tool" / "KiCad's settings file" instead (a small follow-up fix).
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
