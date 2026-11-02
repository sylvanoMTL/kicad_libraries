---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
verified: 2026-11-02T09:00:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files:
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-01-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-01-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-02-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-02-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-03-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-03-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-04-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-04-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-05-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-05-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-06-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-06-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-07-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-07-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-08-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-08-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-09-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-09-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-10-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-10-SUMMARY.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-11-PLAN.md
  - .planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-11-SUMMARY.md
  - kicad_lib_manager/importer/applier.py
  - kicad_lib_manager/importer/kicad_cli.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/preview.py
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/table_generator.py
  - kicad_lib_manager/widgets/backup_dialog.py
  - kicad_lib_manager/widgets/conflict_row.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - kicad_lib_manager/widgets/theme.py
  - tests/casefixtures.py
  - tests/test_case_sensitive_install.py
  - tests/test_plain_names.py
covered_digest: "v3:sha256:9b2a223080d43d3a8b9c0e6d5fc6bf76854bc319a780e7e66b88cd85f635502c"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 5/5
  gaps_closed:
    - "G-12-5 plain names for the KiCad command-line tool and KiCad's settings file (plans 12-10, 12-11)"
    - "G-12-6 Cancel button beside Install Part (plan 12-09)"
    - "G-12-7 Datasheet/Description/Manufacturer hints say the field is required (plan 12-09)"
    - "G-12-8 header button reads 'Choose another package...' with a tooltip (plan 12-09)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "UAT 5-8 visual re-check in the running window: open a package with Ctrl+I"
    expected: "Cancel sits right of Install Part and closes the window; empty Datasheet/Description/Manufacturer boxes read 'Required - ...' and agree with the atomic strip; the header button reads 'Choose another package...' with its tooltip; Help 'Importing Parts' and the 'KiCad is open' / Yes-No texts say 'the KiCad command-line tool' and 'KiCad's settings file'"
    why_human: "Wording and layout in the live window; the executors flagged these human_judgment, tests assert strings and widget state, not appearance"
  - test: "UAT 3 (blocked earlier by the worktree guard): from the main checkout change CUSTOM_3DMODEL_DIR in KiCad, leave KiCad open, press Generate Tables"
    expected: "Dialog 'KiCad is open' with Retry (default), Change anyway, Not now; Retry after closing KiCad leads to the Yes/No question; Not now writes nothing"
    why_human: "Needs a live KiCad process and a modal dialog; tests replace kicad_running"
  - test: "UAT 4 (skipped by owner): Finishing strip during a real kicad-cli rebuild"
    expected: "Dialog greys out with 'Finishing the preview...', window stays live, slow note after 10 s, no hang"
    why_human: "Real timing; covered only by gated stand-in workers. Owner chose to skip the manual check"
---

# Phase 12: Import Flow Fixes and Case-Sensitive Re-test Verification Report

**Phase Goal:** The import dialog, the post-install table step and the `kicad_common.json` write behave correctly in the cases the v1.0 reviews left open. The Help dialog follows the theme, and case-twin rollback is proven on a case-sensitive folder.
**Verified:** 2026-11-02
**Status:** human_needed
**Re-verification:** Yes, after gap closure plans 12-09, 12-10, 12-11 (UAT gaps G-12-5..G-12-8). Plans 12-01..12-08 were verified in the previous report; their code was spot-checked again and showed no regression.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | "Already listed" only when the managed entry points at that library; empty Destination writes no table, never in the working directory | VERIFIED | `table_generator._add_entry` / `_same_rel`; `main_window._dest_path()` returns None for blank text and each caller stops. Not changed by 12-09..11; the 12-10 edit to `main_window.py` is message text only (diff 4 lines). tests/test_main_window.py path_var/settings subset passes |
| 2 | One-off conflict build never runs during Install; window responsive while the command-line tool works | VERIFIED (live check is a human item) | `import_dialog` `_updating`, `_pump_builds`, Finishing state (`_enter_finishing`, `_try_finish`). 12-09 reuses it: `_cancel_btn.clicked` -> `self.reject` -> `done()` (import_dialog.py:3397) which returns while installing or committing, enters Finishing when a build runs. 29 targeted tests (cancel, required hints, change button, finishing, slow note, close) pass |
| 3 | KiCad-running confirm says so before writing; confirmed write starts from current content | VERIFIED (real dialog is a human item) | `library_scanner.sync_kicad_path_vars` re-reads after confirm; `main_window._kicad_open_box` Retry/Change anyway/Not now. 12-10 changed text only ("KiCad's settings file would change", main_window.py:1118,1141); write logic untouched. tests/test_kicad_config.py passes (inside the 97-test run) |
| 4 | Help dialog and conflict rows use theme tokens only | VERIFIED | No hex/px-font hits in help_dialog.py or conflict_row.py; tokens from `theme`. tests/test_help_dialog.py passes. 12-09/11 Help edits are text only |
| 5 | Case-twin rollback proven on a case-sensitive folder | VERIFIED | tests/test_case_sensitive_install.py: 5 passed, no skips, re-run in this verification |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified).

### Gap-closure truths (plans 12-09, 12-10, 12-11)

| Gap | Truth | Status | Evidence |
| --- | ----- | ------ | -------- |
| G-12-6 | Cancel beside Install Part; closes without installing; greyed while installing/committing; Finishing during a build; Enter never presses it | VERIFIED | `_cancel_btn` built after `_install_btn` in the same row (import_dialog.py:806-809), connected to `reject`; `_sync_cancel_button` (line 2921) called from `_set_install_ui` (2919) and `_set_git_worker` (2997); the `setAutoDefault(False)` loop (511-513) runs after the edit page is built, so it covers Cancel. Tests: test_cancel_button_closes_without_installing, _disabled_while_installing, _enabled_again_after_failed_install, _during_build_enters_finishing pass |
| G-12-7 | Required hints for Datasheet, Description, Manufacturer; no "written blank" text | VERIFIED | `_REQUIRED_HINTS` (lines 92-96) applied at line 1128; old `_BLANK_FIELD_HINT` is gone (grep finds only the Help test asserting "blank" absent). Help Fields paragraph (help_dialog.py:281) says the three fields are required. test_required_field_hints_match_the_atomic_strip passes |
| G-12-8 | Header button says it picks another package, with tooltip; Help names it | VERIFIED | `CHANGE_PACKAGE_TEXT = "Choose another package..."` (87), tooltip `_CHANGE_PACKAGE_TIP` (88-90), button at 671-672; Help imports the constant; no literal `Change...` button text remains in user-facing strings (only code comments and a signal comment). test_change_button_says_it_picks_another_package and test_help_names_choose_another_package pass |
| G-12-5 | No user-facing string names `kicad-cli` or `kicad_common.json`; slow note and Help use plain names; on-disk names unchanged | VERIFIED | `SLOW_CLI_TEXT` = "The KiCad command-line tool is slow to respond (it gives up after 60 s)" (116); Help line 328-329 matches. Own grep of every `kicad-cli` / `kicad_common.json` hit in `kicad_lib_manager`: all are docstrings, comments, or the bare file-finding names (`kicad-cli.exe`, `"kicad-cli"` in `which`, config file path). tests/test_plain_names.py (AST scan of non-docstring string constants, allowlist of the three bare names) passes; it is not vacuous (asserts an allowed name was seen and more than 20 files scanned) |

### Required Artifacts

| Artifact | Status | Details |
| -------- | ------ | ------- |
| `widgets/import_dialog.py` Cancel, `_REQUIRED_HINTS`, `CHANGE_PACKAGE_TEXT`, `SLOW_CLI_TEXT` | VERIFIED | all present, substantive, wired (see above) |
| `widgets/help_dialog.py` Cancel / required / Choose another package / plain tool name sentences | VERIFIED | lines 281, 318-329 |
| `tests/test_plain_names.py` | VERIFIED | 1 test, passes |
| `tests/test_import_dialog.py`, `tests/test_help_dialog.py`, `tests/test_main_window.py`, `tests/test_kicad_config.py`, `tests/test_import_preview.py` additions | VERIFIED | named tests exist and pass |
| 12-01..12-08 artifacts (planner `identity_of`, `casefixtures`, `table_generator`, `library_scanner` re-read loop, Finishing state, theme tokens) | VERIFIED | previous report; unchanged apart from message text |

### Key Link Verification

| From | To | Status |
| ---- | -- | ------ |
| `_cancel_btn.clicked` -> `self.reject` -> `done()` | WIRED |
| `_set_install_ui` / `_set_git_worker` -> `_sync_cancel_button` | WIRED |
| `help_dialog` -> `CHANGE_PACKAGE_TEXT`, `FINISHING_TEXT` | WIRED |
| `test_plain_names` -> every module under `kicad_lib_manager` (ast scan) | WIRED |
| `library_scanner.sync_kicad_path_vars` -> `main_window._confirm_path_var_changes` / `_kicad_open_box` | WIRED |
| 12-01..12-08 links (planner, table_generator, `_dest_path`, `_reap`/`_try_finish`, theme tokens) | WIRED (previous report) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Plain-name guard, Help, config sync, preview rows | `env/Scripts/python.exe -m pytest tests/test_plain_names.py tests/test_help_dialog.py tests/test_kicad_config.py tests/test_import_preview.py -q` | 97 passed | PASS |
| Cancel, required hints, change button, Finishing, slow note, close | `pytest tests/test_import_dialog.py -k "cancel or required_field or change_button or finishing or slow_note or close"` | 29 passed | PASS |
| Case-twin (VER-02) and path-variable dialogs | `pytest tests/test_main_window.py tests/test_case_sensitive_install.py -rs -k "path_var or kicad_open or case or settings"` | 11 passed, no skips | PASS |
| Full suite at 60df383 (orchestrator evidence; not re-run, 27 min) | n/a | 9281 passed, 4 skipped (listed in tests/README.md), 0 failed. `git diff 9412c80..HEAD` limited to the 12-09..11 files above plus planning docs | PASS (reported) |

### Probe Execution

No `probe-*.sh` declared or found. SKIPPED.

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
| ----------- | ----------- | ------ | -------- |
| VER-02 | 12-01 | SATISFIED | SC5 |
| UI-01 | 12-02 | SATISFIED | SC4 |
| REV-01 | 12-03, 12-08 | SATISFIED | SC1 |
| REV-02 | 12-04, 12-08 | SATISFIED | SC1 |
| REV-03 | 12-05, 12-08 | SATISFIED | SC2 |
| REV-04 | 12-05, 12-07, 12-08, 12-09, 12-11 | SATISFIED | SC2 and G-12-6 (live check pending) |
| REV-05 | 12-06, 12-08, 12-10 | SATISFIED | SC3 and G-12-5 text (live dialog pending) |

All seven IDs appear in PLAN frontmatter and REQUIREMENTS.md; no orphaned requirements. Bookkeeping: REQUIREMENTS.md still shows all seven as `[ ]` / "Pending", and ROADMAP line 33 still shows Phase 12 unchecked ("3 gap-closure plans pending" at line 257 is stale since all 11 plan boxes are checked). The orchestrator should flip these on phase completion.

### Anti-Patterns Found

No TBD/FIXME/XXX/TODO/HACK in the changed source files or tests/test_plain_names.py. No stubs or hollow props in the traced paths. 12-REVIEW.md (0 critical, 2 warning, 3 info after disposition, ledger 12-REVIEW-DISPOSITION.md) is advisory and does not block a success criterion. 12-SECURITY.md reports 28 threats, 0 open. 12-UI-REVIEW.md scores 17/24 (advisory).

### Prohibitions

- Judgment-tier (12-08) "User-facing text must not use raw KiCad field names or code identifiers": previously flagged because of `kicad-cli` / `kicad_common.json` wording. Resolved by G-12-5: the guard test passes and my own grep found no remaining user-visible raw names. Verdict is mechanical for these two tokens; the broader plain-language judgment of the new Cancel/Required/Choose-another-package wording stays with the owner (human item 1).
- Test-tier prohibitions in 12-09/10/11 (Cancel never closes during install/commit; settings-file write logic and backup folder names unchanged; guard not satisfied by renaming on-disk names) have wired tests: test_cancel_button_disabled_while_installing, test_kicad_config.py backup-folder assertions, test_plain_names (allowlist and the explicit "kicad_common" segment note). All pass.

### Human Verification Required

1. **UAT 5-8 wording and layout.** Test: start the app, open `downloaded_examples\ul_CSD85301Q2.zip` with Ctrl+I. Expected: Cancel right of Install Part and closes the window; empty Datasheet, Description, Manufacturer boxes read "Required - ..." and match the atomic strip; header button reads "Choose another package..." with tooltip; Help and the path-variable dialogs say "the KiCad command-line tool" / "KiCad's settings file". Why human: appearance and wording judgment.
2. **UAT 3 live KiCad-open dialog** from the main checkout (the worktree guard blocked it earlier). Why human: live KiCad process and modal dialog.
3. **UAT 4 (owner skipped)**: Finishing strip with a real kicad-cli rebuild. Covered only by stand-in workers.

### Gaps Summary

No gaps. All five roadmap success criteria and the four gap-closure truths (G-12-5..G-12-8) are verified in code and by targeted tests run in this verification; the full-suite result is the orchestrator's. Status is `human_needed` solely because the live-window wording/layout re-check (UAT 5-8), the live KiCad-open dialog (UAT 3) and the live rebuild (UAT 4) cannot be confirmed programmatically.

---

_Verified: 2026-11-02_
_Verifier: Claude (gsd-verifier)_
