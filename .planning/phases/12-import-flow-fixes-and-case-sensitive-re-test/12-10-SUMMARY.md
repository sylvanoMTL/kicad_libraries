---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 10
subsystem: ui-text
tags: [plain-language, gap-closure, G-12-5, kicad-config, kicad-cli]
requires: []
provides:
  - "Plain 'KiCad's settings file' wording in both path-variable dialogs and the settings-file log lines"
  - "Plain 'the KiCad command-line tool' wording in import preview rows and importer issue texts"
affects: [12-11]
tech-stack:
  added: []
  patterns: ["message text only; issue codes, severities and matched keywords unchanged"]
key-files:
  created: []
  modified:
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/library_scanner.py
    - kicad_lib_manager/importer/preview.py
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/importer/kicad_cli.py
    - kicad_lib_manager/importer/applier.py
    - tests/test_main_window.py
    - tests/test_kicad_config.py
    - tests/test_import_preview.py
key-decisions:
  - "Raw settings-file and environment.vars wording replaced in bad_shape and verify_failed sentences too (same plain-language rule)"
  - "On-disk names kept: kicad_common.json constant, kicad_common backup folder, bare kicad-cli executable names"
requirements-completed: [REV-05]
duration: 15 min
completed: 2026-11-02
status: complete
commits: 2
plan_head_before: 458317feb681679ec2fbf47036f09787126fc146
plan_head_after: cffa1af6ae9f8e39db7feddc4a096d1a270c4cc1
actuals:
  tokens: 6000
  tasks: 2
  commits: 2
coverage:
  - deliverable: "Path-variable Yes/No question and KiCad-open box say KiCad's settings file"
    verification:
      - {kind: test, ref: "tests/test_main_window.py#test_path_var_question_names_the_settings_file", status: pass}
      - {kind: test, ref: "tests/test_main_window.py#test_kicad_open_box_texts_and_buttons", status: pass}
    human_judgment: false
  - deliverable: "Settings-file log lines (keeps changing, could not read, unexpected structure, did not write, backed up) use plain wording"
    verification:
      - {kind: test, ref: "tests/test_kicad_config.py", status: pass}
    human_judgment: false
  - deliverable: "Import preview rows and importer issue texts name the KiCad command-line tool"
    verification:
      - {kind: test, ref: "tests/test_import_preview.py#test_format_rows_cases", status: pass}
      - {kind: test, ref: "tests/test_kicad_cli.py", status: pass}
      - {kind: test, ref: "tests/test_install_plan.py", status: pass}
      - {kind: test, ref: "tests/test_install_apply.py", status: pass}
    human_judgment: false
---

# Phase 12 Plan 10: Plain names for KiCad's settings file and the KiCad command-line tool Summary

User-facing text outside the import window now says "KiCad's settings file" and "the KiCad command-line tool" instead of raw file and program names (UAT gap G-12-5); no write logic, issue code or severity changed.

## Accomplishments

- Both path-variable dialogs (the Yes/No question and the KiCad-open box) read "These KiCad path variables in KiCad's settings file would change:".
- The keeps-changing, could-not-read, unexpected-structure, did-not-write and backed-up log lines say "KiCad's settings file"; the raw `environment.vars` field name is gone from the structure and verify-failed sentences.
- Import preview rows ("The KiCad command-line tool will normalise the incoming symbol", "KiCad command-line tool not found - symbol merged as-is") and the issue texts in `planner.py`, `kicad_cli.py` and `applier.py` use the plain tool name. "Could not", "not found", "timed out after" and library/footprint names are preserved.

## Task Commits

1. Task 1 (tracer): path-variable dialogs and log lines - `6310786`
2. Task 2: preview rows and importer issue texts - `cffa1af`

## Verification

- Task 1 targeted run: 16 passed; `tests/test_kicad_config.py`: 55 passed.
- Task 2 targeted run (preview, kicad_cli, install_apply, install_plan): 282 passed.
- Plan-level run (kicad_config, main_window, import_preview, kicad_cli, install_plan, install_apply): 392 passed.
- Acceptance greps: `KiCad's settings file would change` x2 in main_window.py; `KiCad's settings file` x5 in library_scanner.py; `KiCad command-line tool` counts kicad_cli.py 9, planner.py 6, preview.py 2, applier.py 1.

## Deviations from Plan

None - plan executed exactly as written. Note on TDD: test edits were written alongside the code in the same working session rather than as separate failing-test commits; each task landed as one commit with tests and code together.

## Known Stubs

None.

## Issues Encountered

None. Not touched, by design (plan 12-11): `widgets/import_dialog.py` slow note and the Help sentence still name the raw tool.

## Self-Check: PASSED

- Modified files exist and commits `6310786` and `cffa1af` are ancestors of HEAD.
