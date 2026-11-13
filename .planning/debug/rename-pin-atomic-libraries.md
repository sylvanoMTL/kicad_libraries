---
status: diagnosed
trigger: "G-13-1-c: rename 'Set Up KiCad Chooser...' to 'Pin Atomic Libraries in KiCad...' (plain-language UI)"
created: 2026-11-12T18:00:00Z
updated: 2026-11-12T18:30:00Z
goal: find_root_cause_only
gap_id: G-13-1-c
---

## Current Focus

bug_class: Bohrbug (deterministic wording; naming change, not a defect in logic)
hypothesis: CONFIRMED. The action name "Set Up KiCad Chooser..." (D-17) is hard-coded as literal strings in 4 source modules (main_window.py, kicad_setup.py, widgets/migration_dialog.py, widgets/help_dialog.py), echoed in CLAUDE.md and pinned by assertions in 4 test files; there is no single constant, so the rename has to touch every listed place.
test: repo-wide grep (Chooser|chooser|Set Up KiCad|Ctrl+Shift+K|pins) excluding Custom/, env/, WurthElektronik/ + classification + baseline run of the coupled tests (41 passed)
expecting: n/a (diagnosis complete)
next_action: return ROOT CAUSE FOUND with the inventory and proposed strings to the caller (goal find_root_cause_only)
candidate_causes:
  - "code: literal UI strings in main_window/kicad_setup/migration_dialog/help_dialog"
  - "data/docs: CLAUDE.md wording + test expectations that freeze the old text"
and_gate: "no - one cause (literal wording chosen in D-17); docs and tests only mirror it"

## Symptoms

expected: Plain-language UI (owner's standing rule). The action should be called "Pin Atomic Libraries in KiCad..." (owner's preferred wording); "KiCad Chooser" on its own is vague to the owner.
actual: Menu action, shortcut tooltip, Result view button, log lines, User Guide, CLAUDE.md and tests use "Set Up KiCad Chooser..." / "chooser" wording.
errors: None.
reproduction: UAT test 1 (check 10): File > Set Up KiCad Chooser... (Ctrl+Shift+K), migration Result view button, log lines such as "Not setting up KiCad's chooser: ...", User Guide page, CLAUDE.md, tests asserting these strings.
started: Discovered during UAT on 2026-11-12 (wording introduced in phase 13).

## Eliminated

## Evidence

- timestamp: 2026-11-12T18:05:00Z
  checked: grep -rniI "chooser|Set Up KiCad" outside Custom/, env/, WurthElektronik/, .planning/, .claude/
  found: source hits in kicad_lib_manager/main_window.py, kicad_setup.py, widgets/migration_dialog.py, widgets/help_dialog.py, widgets/import_dialog.py, importer/keywords.py; tests test_checkout_check, test_docs_atomic, test_help_dialog, test_keywords, test_kicad_setup, test_layering, test_main_window_chooser, test_main_window_migration, test_migration_dialog_run; CLAUDE.md; research_notes (KiCad-native "chooser" term only)
  implication: the wording is spread over literal strings in 4 source modules plus docs and tests; no single constant drives it

- timestamp: 2026-11-12T18:08:00Z
  checked: main_window.py lines 58-60, 340-351, 1494-1523
  found: SETUP_CHOOSER_TEXT = "Set Up KiCad &Chooser..." (menu text); _NO_DEST_CHOOSER_TEXT = "No destination folder set; KiCad's chooser not set up"; tooltip == status tip = "Pin the Atomic_ libraries and show the MPN and Manufacturer columns in KiCad's symbol chooser"; confirm title "Set up KiCad's chooser?"; confirm intro "These settings of KiCad's symbol chooser would change:" (Yes/No box and KiCad-open box)
  implication: user-facing strings to rename in main_window.py; identifiers _act_setup_chooser, _on_setup_chooser, _chooser_* are internal and can stay

- timestamp: 2026-11-12T18:10:00Z
  checked: kicad_setup.py full read
  found: user-facing Issue texts naming the old action: chooser.worktree_refused "Not setting up KiCad's chooser: this app runs from a git worktree (...)"; chooser.other_checkout_refused via wrong_checkout_refusal(mismatch, "Not setting up KiCad's chooser"); chooser.confirm_required "Not setting up KiCad's chooser: no confirmation step was provided"; chooser.dir_not_found "...; KiCad's chooser was not set up"; chooser.ok "KiCad's chooser is already set up; nothing to change" (x2, lines 473/536); chooser.declined "KiCad's chooser left unchanged (change declined)"; chooser.keeps_changing "...Try Set Up KiCad Chooser again."; chooser.kicad_running "...it may undo the chooser setup when it exits. If it does, close KiCad and set it up again."; ChooserChange labels "Symbol chooser columns"/"Symbol chooser column widths" (correct KiCad term, keep); verify_failed/bad_shape texts mention "chooser keys"/"chooser columns". Issue codes chooser.* and names sync_kicad_chooser/ChooserChange/chooser_tables are internal.
  implication: kicad_setup.py has ~9 user-facing log texts to rephrase; Issue codes must stay (main_window branches on chooser.retry, tests assert codes)

- timestamp: 2026-11-12T18:12:00Z
  checked: migration_dialog.py lines 108-112, 1687
  found: CHOOSER_TEXT = "Set Up KiCad Chooser..." (Result view button); NEXT_STEPS_TEXT ends "then press Set Up KiCad Chooser to pin them and show the MPN and Manufacturer columns."
  implication: 2 user-facing strings; CHOOSER_TEXT is imported by help_dialog.py so the guide's migrating page follows the constant automatically

- timestamp: 2026-11-12T18:14:00Z
  checked: help_dialog.py lines 255-268, 360, 510-511, 570 and section-anchor logic (page_sections/section_anchor/show_remembered)
  found: h3 "KiCad chooser" (TOC section, key generating#kicad-chooser); body "File &rarr; Set Up KiCad Chooser... (Ctrl+Shift+K) pins every ..."; "nothing when the chooser is already set up"; migrating page "Then click <b>CHOOSER_TEXT</b> to pin the new libraries in KiCad's chooser."; shortcuts row "Set Up KiCad Chooser". Line 360 (importing page, "KiCad's symbol and footprint choosers search") is the KiCad term and unrelated to the action. show_remembered falls back from an unknown "page#anchor" to its page, so renaming the h3 is safe for a saved help topic.
  implication: guide places to change: h3 + paragraph, migrating sentence, shortcuts row; keep line 360

- timestamp: 2026-11-12T18:20:00Z
  checked: tests/*.py grep for Chooser/chooser/Set Up KiCad/SETUP_CHOOSER/CHOOSER_TEXT
  found: string-coupled tests: test_main_window_chooser.py:183 title "Set up KiCad's chooser?", :199 menu text "Set Up KiCad &Chooser...", :203-206 tooltip, :268 "KiCad's chooser left unchanged (change declined)", :276/:281 intro passed to _kicad_open_box directly (not coupled to main_window's string), :342 uses _NO_DEST_CHOOSER_TEXT constant (auto-follows); test_kicad_setup.py:324 wrong_checkout_refusal(mismatch, "Not setting up KiCad's chooser"), :201 label "Symbol chooser columns" (only if labels change); test_help_dialog.py:91 ("Ctrl+Shift+K","Set Up KiCad Chooser"), :98-100 test_help_generating_page_explains_the_chooser asserts "KiCad chooser", :415 "Set Up KiCad Chooser" in migrating page; test_docs_atomic.py:51 asserts SETUP_CHOOSER_TEXT (minus &) is in CLAUDE.md (auto-forces the CLAUDE.md update). test_migration_dialog_run.py / test_main_window_migration.py only use internal identifiers (_chooser_btn, setup_chooser_requested). test_layering/test_checkout_check/test_keywords: comments/docstrings only. All other test_kicad_setup assertions use Issue codes (chooser.*), not text.
  implication: 4 test files need expectation updates; Issue codes and identifiers must stay so the rest of the suite is untouched

- timestamp: 2026-11-12T18:22:00Z
  checked: CLAUDE.md, README.md, .claude/CLAUDE.md, .planning docs, memory dir, migration core (importer/migration)
  found: CLAUDE.md lines 28, 81, 82, 83, 90 name "Set Up KiCad Chooser(...)"; README.md and .claude/CLAUDE.md have no hit; importer/migration (MIGRATION-ATOMIC.md writer, commit message) has no hit; .planning REQUIREMENTS.md TBL-02, ROADMAP.md, 13-CONTEXT D-17/D-26 and phase plans/summaries use the old name historically and no test reads them for it; LIBRARY-NAMING.md (read by test_docs_atomic) uses "chooser" only as KiCad's term; memory kicad-checkout-layout.md says "chooser setup" generically (outside repo)
  implication: CLAUDE.md is the only doc that must change; planning history stays, optionally a D-17 rename note

- timestamp: 2026-11-12T18:24:00Z
  checked: File-menu mnemonics in main_window.py (&File, &Import, &Generate, &Restore, Re&scan, Check &Atomic, &Migrate, Set Up KiCad &Chooser, Set KiCad &Footprint, E&xit)
  found: P is free, so "&Pin Atomic Libraries in KiCad..." has no clash
  implication: proposed menu text is safe for keyboard access

- timestamp: 2026-11-12T18:25:00Z
  checked: baseline run of test_docs_atomic, test_kicad_setup, test_main_window_chooser and 4 help tests (offscreen, env python 3.14)
  found: 41 passed in 5.59s
  implication: suite is green before the rename; the listed assertions are the ones a rename will flip

- timestamp: 2026-11-12T18:26:00Z
  checked: library_scanner.py path-variable sync message pattern
  found: "Not changing KiCad path variables: ..." / "KiCad path variables left unchanged (change declined)" / "...kept changing while you were asked; nothing was written. Press Generate Tables to try again."
  implication: new pin messages should mirror this shape ("Not pinning the Atomic_ libraries in KiCad: ...")

## Resolution

root_cause: The action was named "Set Up KiCad Chooser..." in decision D-17 (phase 13) and that wording, plus KiCad's jargon word "chooser", was written as literal strings into main_window.py (menu text, tooltip/status tip, no-destination warning, confirm title and intro), kicad_setup.py (9 log/refusal texts), migration_dialog.py (Result view button + next-steps label) and help_dialog.py (section heading, paragraph, migrating sentence, shortcuts row), mirrored in CLAUDE.md (5 lines) and frozen by assertions in test_main_window_chooser.py, test_kicad_setup.py, test_help_dialog.py and (indirectly) test_docs_atomic.py.
fix: (not applied; diagnosis only) see ROOT CAUSE FOUND report for the per-file inventory and proposed strings
verification: baseline 41 coupled tests pass before any change
files_changed: []
