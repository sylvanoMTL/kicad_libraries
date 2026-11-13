---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 11
subsystem: ui-text
tags: [plain-language, gap-closure, G-12-5, import-dialog, help, guard-test]
requires:
  - phase: 12-import-flow-fixes-and-case-sensitive-re-test
    provides: "Plans 12-09 (Help/Finishing paragraph) and 12-10 (plain names elsewhere in the package)"
provides:
  - "Finishing strip slow note and Help sentence say 'the KiCad command-line tool'"
  - "tests/test_plain_names.py: package-wide guard against raw tool and settings-file names in user-facing strings"
  - "Gap-closure gate result for plans 12-09, 12-10 and 12-11"
affects: [phase 12 verification, UAT test 5 re-check]
tech-stack:
  added: []
  patterns: ["ast scan of string constants outside docstrings, with an allowlist of bare on-disk names"]
key-files:
  created:
    - tests/test_plain_names.py
  modified:
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_help_dialog.py
key-decisions:
  - "Search token includes .json so the 'kicad_common' backup folder segment is never matched and stays untouched"
  - "Allowlist holds only the bare names 'kicad-cli', 'kicad-cli.exe' and 'kicad_common.json' that the code uses to find and open them"
requirements-completed: [REV-04]
duration: 40 min (about 17.5 min of it the full-suite gate)
completed: 2026-11-02
status: complete
commits: 3
plan_head_before: a22db6bcbb71a711a43a97eb6770acfef4e82fc5
plan_head_after: 6884371e0ab09b3aff1b2dd76b4e9e90ac02bb89
actuals:
  tokens: 2500
  tasks: 2
  commits: 3
coverage:
  - id: D1
    description: "The Finishing strip's slow note reads 'The KiCad command-line tool is slow to respond (it gives up after 60 s)' and the Help sentence uses the same plain name"
    requirement: REV-04
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_describes_phase_12_behaviour"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_finishing_shows_slow_note"
        status: pass
    human_judgment: false
  - id: D2
    description: "A package-wide test fails if any user-facing string brings back kicad-cli or kicad_common.json; on-disk names and the backup folder are untouched"
    requirement: REV-04
    verification:
      - kind: unit
        ref: "tests/test_plain_names.py#test_no_user_text_names_kicad_cli_or_its_settings_file"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_config.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "UAT test 5 reads well to the owner in the running window (Help page, Finishing strip, both path-variable dialogs)"
    verification: []
    human_judgment: true
    rationale: "Wording adequacy in the running window is a judgment no test asserts"
---

# Phase 12 Plan 11: Plain tool name in the slow note and Help, plus a guard test Summary

The last two raw "kicad-cli" strings (Finishing strip slow note and its Help sentence) now say "the KiCad command-line tool", and `tests/test_plain_names.py` fails if any user-facing string in `kicad_lib_manager` brings back "kicad-cli" or "kicad_common.json".

## Performance

- **Duration:** about 40 min including the 17 min 28 s gate run
- **Tasks:** 2 (3 commits)
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- `SLOW_CLI_TEXT` reads "The KiCad command-line tool is slow to respond (it gives up after 60 s)". Help's Finishing paragraph now ends "After 10 seconds the strip adds that the KiCad command-line tool is slow to respond; it gives up after 60 seconds." The "Press Cancel" sentence and the `CHANGE_PACKAGE_TEXT` concatenation from plan 12-09 are kept.
- `test_help_describes_phase_12_behaviour` also checks the new Help sentence and that neither the generating nor the importing page holds "kicad-cli" or "kicad_common".
- `tests/test_plain_names.py` parses every `.py` under `kicad_lib_manager`, skips docstrings, and fails on any other string constant containing "kicad-cli" or "kicad_common.json" unless it is exactly one of the three allowed bare names. It also fails if 20 or fewer files were scanned or no allowed bare name was seen (T-12-27). The failure message lists file:line:text and names the plain replacements. A one-off check on a sample module confirmed it flags `"kicad-cli is slow"` and an f-string part, and skips a docstring.
- It passed at once on the merged package: plans 12-09 and 12-10 had already removed every other user-facing hit, so no extra string needed fixing. The backup folder line `"kicad_common" / config_dir.name` is untouched.

## Task Commits

1. **Task 1 (tracer, TDD):** `fdb12c9` (test, RED), `7fbe5a8` (feat, GREEN)
2. **Task 2 (TDD guard):** `6884371` (test)

Plan metadata: committed with this SUMMARY (docs).

## TDD Gate Compliance

- RED (Task 1): `test_help_describes_phase_12_behaviour` failed with `AssertionError: the kicad command-line tool is slow to respond` on the importing page. Semantic assessment: the target test ran and failed on the planned claim, not a collection or fixture fault. `gsd_run check tdd-red-evidence` was not run; the failure is the plain pytest assertion above.
- GREEN: the 18 targeted tests passed after the two string edits.
- Task 2 is a new guard that must pass on the already-clean package, so there is no RED commit; the guard's detection was checked by hand on a sample source (flagged the raw names, skipped the docstring). No REFACTOR commits.

## Verification

- Task 1 targeted run (`-k "phase_12_behaviour or slow_note or help_import_page or choose_another or cancel_button"`): 18 passed.
- Task 2 run (`test_plain_names.py`, `test_kicad_config.py`): 56 passed.
- Plan-level run (plain_names, help_dialog, import_dialog, kicad_config, main_window, import_preview, kicad_cli): 433 passed in 169.75 s.
- Acceptance greps: `The KiCad command-line tool is slow to respond` found at `import_dialog.py:116`; `the KiCad command-line tool is slow to respond` found at `help_dialog.py:329`; the `"kicad_common" / config_dir.name` backup line is still at `library_scanner.py:347`; `kicad_common.json` appears in `tests/test_plain_names.py` as the token and allowlist constants.

## Gap-closure gate

`env/Scripts/python.exe -m pytest -m "not wurth" -q`, run from this worktree after all three plans were merged into its base: **passed**, exit 0. **3170 passed, 33 skipped, 3 deselected, 4 warnings** in 1048.88 s (17 min 28 s). The 4 warnings are Qt deprecation warnings for `QDragEnterEvent` in `tests/test_main_window_import.py`, not from this plan.

All 33 skips are conditions listed in `tests/README.md`, and are the extra ones a worktree without submodules and without the gitignored vendor samples produces:

- The two README "expected on the workstation" opt-in skips: `KICAD_ATOMIC_UAT_DIR` unset, `KICAD_IMPORT_UAT_DIR` unset.
- Two symlink skips (`test_model_source.py:201`, `test_package_folder.py:105`).
- 10 skips with "Custom submodule not checked out" (`test_edits.py` x2, `test_kicad_files.py` x2, `test_locate_text_caps.py`, `test_naming_sanitize.py`, `test_roundtrip_corpus.py`, `test_scanner_issues.py`, `test_sexpr.py`; the worktree has an empty `Custom/`).
- 19 skips for licence-restricted vendor samples absent from the worktree (`downloaded_examples/ul_ATXK-H14-D-32-768KHZ-E50-T3.zip`, `LIB_RS3-1212S_H3.zip`, `USB4145-03-0170-C_REVA2.zip`, `194150990-659-usb4145-03-0170-c.zip`) in `test_atomic_targets`, `test_categories`, `test_footprint_text`, `test_gate_reasons`, `test_real_vendor_samples` and `test_vendorfixtures`.

No failures and no skip outside the README. The orchestrator's own checkout should show only the four workstation skips.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Compound git commands (several git calls chained in one shell line) were refused by the worktree guard, so the plan-commit ledger file was not written; the base commit `a22db6b` is recorded above from the dispatch instructions instead.

## Known Stubs

None.

## Self-Check: PASSED

- `tests/test_plain_names.py` exists; modified files exist.
- Commits `fdb12c9`, `7fbe5a8`, `6884371` are ancestors of HEAD.
