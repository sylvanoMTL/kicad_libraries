---
phase: 13-atomic-migration-and-kicad-setup
plan: 27
subsystem: kicad-setup-wording
tags: [rename, wording, pin-atomic-libraries, help, claude-md, gap-closure]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "13-07 chooser setup action (D-17), 13-24/13-26 help_dialog.py and CLAUDE.md text"
provides:
  - kicad_setup.PIN_ACTION_TEXT and PIN_REFUSAL_TEXT, the single source of the action's name and refusal prefix
  - "Pin Atomic Libraries in KiCad..." in the menu, tooltip, status tip, confirm box, Result view button, next-steps line, every log and refusal line, the User Guide and CLAUDE.md
affects: [13-28]

actuals:
  tokens: 20000
  tasks: 2
  commits: 3

plan_head_before: 66d59429a1e5958218c36d53ec34c9a15a1f77a8
plan_head_after: e8e14fef76156f9d01bfccfba67c60f9cd1d9afb

tech-stack:
  added: []
  patterns:
    - "one Qt-free constant in kicad_setup drives the action name; main_window and migration_dialog build their texts from it, help_dialog reads migration_dialog.CHOOSER_TEXT"

key-files:
  created: []
  modified:
    - kicad_lib_manager/kicad_setup.py
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/widgets/migration_dialog.py
    - kicad_lib_manager/widgets/help_dialog.py
    - CLAUDE.md
    - tests/test_kicad_setup.py
    - tests/test_main_window_chooser.py
    - tests/test_help_dialog.py
    - .planning/phases/13-atomic-migration-and-kicad-setup/13-CONTEXT.md

key-decisions:
  - "No identifier or chooser.* Issue code was renamed; only user-facing text, docs and test expectations changed"
  - "The guide section heading became 'Pin Atomic libraries in KiCad'; a saved place at the old anchor falls back to its page"
  - "'Symbol Chooser' remains only as KiCad's own window name (change labels, explanatory prose)"

requirements-completed: [TBL-02, DOC-01]

duration: about 40 min (including an API interruption and resume)
completed: 2026-11-13
status: complete
---

# Phase 13 Plan 27: Pin Atomic Libraries in KiCad wording Summary

**The "Set Up KiCad Chooser..." action is now "Pin Atomic Libraries in KiCad..." everywhere the owner sees it, driven by one constant, with every identifier and chooser.* code untouched (closes gap G-13-1-c).**

## Accomplishments

- `kicad_setup.PIN_ACTION_TEXT` and `PIN_REFUSAL_TEXT` added; the worktree, wrong-checkout (still naming both folders, D-26), no-confirmation, declined, already-pinned, config-not-found, keeps-changing, KiCad-open, bad-shape and verify-failed texts reworded.
- Menu text `&Pin Atomic Libraries in KiCad...` (Ctrl+Shift+K kept), new tooltip and status tip (one shared string), confirm title `Pin Atomic libraries in KiCad?` and intro, no-destination warning.
- Result view button and next-steps line built from the constant.
- User Guide (section heading and paragraphs, migrating-page sentence, shortcuts row) and CLAUDE.md (5 places) renamed; D-17 carries a rename note.

## Task Commits

1. Task 1 RED: `becdde1` test(13-27): failing tests for the new wording (new `test_pin_texts_never_name_the_chooser_alone`; updated menu, tooltip, title, intro, declined and refusal expectations)
2. Task 1 GREEN: `381cd73` feat(13-27): one constant names the action across kicad_setup, main_window and migration_dialog
3. Task 2: `e8e14fe` docs(13-27): guide, CLAUDE.md, D-17 and help tests

## TDD notes (Task 1)

- RED: the main-window tests failed on the planned assertions (menu text, confirm title, declined text); the new test and the refusal test failed with AttributeError on the not-yet-existing `PIN_REFUSAL_TEXT`, the planned interface. `gsd_run check tdd-red-evidence` is unavailable in this worktree (no `.claude/gsd-core`), so the semantic assessment was done by hand: 5 failed, 29 passed, all failures are the renamed expectations.
- GREEN: 78 passed on the Task 1 verify command. Tracer gate: the verify was re-run end to end before Task 2 and passed ("Tracer verified end-to-end -- expanding").
- No REFACTOR commit (nothing to clean up).

## Verification

- Task 1 verify (7 test files): 78 passed.
- Task 2 verify (test_help_dialog, test_docs_atomic, test_main_window_chooser): 82 passed.
- Plan `<verification>` (9 test files): 151 passed.
- Acceptance criteria: constants found; no "Set Up KiCad" or "KiCad's chooser" left in the three modules outside the one comment (also reworded); `"chooser.` count in kicad_setup.py is 24 before and after; new test present; `Set Up KiCad Chooser` count 0 in CLAUDE.md and help_dialog.py; `Pin Atomic Libraries in KiCad` appears 5 times in CLAUDE.md; renamed help test present; 13-27 note in 13-CONTEXT.md.
- The whole suite was not run (plan 13-28 runs it once).

## Deviations from Plan

None - plan executed exactly as written. Small additions inside the plan's scope: the `main_window.py` comment mentioning "KiCad's chooser" was reworded too, and `test_setup_chooser_menu_entry` also asserts the status tip equals the tooltip.

## Issues Encountered

The agent session stopped on an API 403 after commit `e8e14fe` (before the SUMMARY). The orchestrator resumed it in the same worktree; the branch identity and base ancestry checks were re-run, the verify commands re-run (all green) and this SUMMARY written. No work was lost or redone.

## Known Stubs

None.

## Threat Flags

None. No new endpoint, auth path or file access; tests keep using the synthetic config tree in tmp_path (T-13-75), the wrong-checkout refusal still names both folders (T-13-73, asserted by two tests) and no chooser.* code changed (T-13-74).

## Self-Check: PASSED

Commits becdde1, 381cd73 and e8e14fe are ancestors of HEAD; all modified files exist; no pytest process left running.
