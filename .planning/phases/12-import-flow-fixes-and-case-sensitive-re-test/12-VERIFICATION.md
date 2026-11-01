---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
verified: 2026-11-01T18:00:00Z
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
  - kicad_lib_manager/importer/planner.py
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
covered_digest: "v3:sha256:67dd750abeb3ea1c2197417f604229c8535bd0ab243cc65c4083182f8ade5b87"
behavior_unverified: 0
overrides_applied: 0
unverified_prohibitions:
  - statement: "User-facing Help text must never use raw KiCad field names or code identifiers (12-08, judgment tier)"
    status: "unverified-prohibition - human review recommended"
    note: "Non-authoritative judge verdict: no raw field names (ki_*) found, but new text names the tool 'kicad-cli' (Help page, FINISHING slow note) and 12-REVIEW WR-04 flags kicad_common.json in dialog and log text. Owner decides whether that counts."
human_verification:
  - test: "Run tests/test_case_sensitive_install.py on the Windows workstation (D-13 owner UAT)"
    expected: "5 passed, 0 skipped (no 'could not make a case-sensitive folder' skip)"
    why_human: "The 12-01 plan makes the owner's own run the UAT; the verifier ran it here and it passed, but the owner run is the planned sign-off"
  - test: "Look at the Help pages and the conflict rows at 100% and 200% display scale"
    expected: "Headings still larger than body text, code and pre blocks readable, conflict row buttons look as before (Qt rich text does not draw the h2 underline or the left bars; unchanged from before 12-02)"
    why_human: "Visual appearance cannot be checked by grep or unit test"
  - test: "With real KiCad running, press Generate Tables (or install a part) and reach the kicad_common.json question"
    expected: "Dialog titled 'KiCad is open' names the open programs, lists the changes, offers Retry (default), Change anyway, Not now; Retry after closing KiCad leads to the normal Yes/No; Not now writes nothing"
    why_human: "Needs a live KiCad process and a modal dialog; tests replace kicad_running"
  - test: "With a real kicad-cli rebuild running, press Change..., open another package, press Cancel on the strip, and close the dialog and the main window"
    expected: "Dialog greys out with 'Finishing the preview...', window stays responsive, after 10 s the slow note appears, the action runs by itself, Cancel restores the dialog, no hang"
    why_human: "Real kicad-cli timing and window responsiveness; tests use gated stand-in workers"
  - test: "Judgment prohibition: read the new Help sentences and the KiCad-open dialog text"
    expected: "Owner accepts or rejects the wording that names 'kicad-cli' and 'kicad_common.json' (12-REVIEW WR-04)"
    why_human: "Plain-language preference is a judgment; verifier verdict is non-authoritative"
---

# Phase 12: Import Flow Fixes and Case-Sensitive Re-test Verification Report

**Phase Goal:** The import dialog, the post-install table step and the `kicad_common.json` write behave correctly in the cases the v1.0 reviews left open. The Help dialog follows the theme, and case-twin rollback is proven on a case-sensitive folder.
**Verified:** 2026-11-01
**Status:** human_needed
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | After install, "already listed" only when the managed entry really points at that library; empty Destination writes no table and never one in the working directory | VERIFIED | `table_generator._add_entry` (lines 319-410) returns "listed" only when `_same_rel(_tail(entry), rel_path)` holds for a tool-owned entry; stale entry repointed with backup (Edit over the uri value node only); live clash and hand entry warn. `main_window._dest_path()` (line 427) returns None for blank text; every call site (post-install line 837, Generate 1215, tables log, backup dialog `_folder()`) stops before reading or writing. No remaining bare `Path(currentText())`. Tests ran green: test_table_add_entries, test_backup_dialog, test_main_window_import (tables/blank/dest subset, 30 passed) |
| 2 | One-off conflict build can never run while Install runs; window stays responsive while kicad-cli works, no GUI wait of up to 60 s | VERIFIED (live kicad-cli check is a human item) | `import_dialog`: `_updating()` counts `self._oneoff` so Install is disabled during a one-off; `_pump_builds` holds one-off jobs while `is_installing()` or `_finishing`; `_request_rebuild` queues during install. Change.../open/close enter `_enter_finishing` (stack disabled, wait cursor, strip with Cancel, 10 s slow note) and the action runs from `_reap` -> `_try_finish`; the only join left is `worker.wait(2000)` on an already finished thread (owner-approved bound). Remaining unbounded `wait()` calls in main_window are scan-worker joins, not kicad-cli. 31 targeted Finishing/close/one-off/cancel tests passed |
| 3 | When KiCad is running the confirm dialog says so before anything is written; confirmed write starts from the file's current content | VERIFIED (real dialog is a human item) | `main_window._sync_path_vars` runs `kicad_running()` in a `TaskWorker` (off GUI thread), `_kicad_open_box` shows Retry (default) / Change anyway / Not now. `library_scanner.sync_kicad_path_vars` calls `confirm` then `_read_config` again, re-plans, re-asks if the change list differs (3-pass cap), verifies only `environment.vars` changed, backs up, writes atomically. tests/test_kicad_config.py + test_main_window.py: 109 passed |
| 4 | Help dialog and conflict rows use theme tokens only: no hard-coded colours, no `#FFFFFF`, no px font sizes | VERIFIED | grep of `help_dialog.py` and `conflict_row.py` for hex colours, `rgb(`, `white`, `font-size: ..px` finds none; CSS is built from `theme` imports (`LINK, ACCENT, SURFACE, SURFACE_HEADER, BORDER, AMBER, AMBER_TINT, DISPLAY_PT, HEADING_PT, MONO_PT, MONO_FAMILY, SP_*`); `conflict_row` uses `SURFACE_BASE` (defined in `theme.py`). Remaining px values are paddings, 1-4 px borders, radius and min-height, not colours or font sizes. test_help_dialog 18 passed |
| 5 | On a case-sensitive folder, case-twin rollback restores the original spelling and removes the twin on rollback and overwrite branches | VERIFIED | `tests/casefixtures.case_sensitive_dir` uses `fsutil setCaseSensitiveInfo` plus a probe file; `planner._decide_file` overwrite writes under `spec.identity_of(hit)` (on-disk spelling). tests/test_case_sensitive_install.py: 5 passed, none skipped, run by the verifier on this workstation. Tests build their own folder, do not mock listdir, do not touch live Custom/ |

**Score:** 5/5 truths verified (0 present-but-behavior-unverified).

### Required Artifacts

| Artifact | Status | Details |
| -------- | ------ | ------- |
| `importer/planner.py` (`identity_of(hit)` overwrite) | VERIFIED | lines 744-747 |
| `tests/casefixtures.py` (`case_sensitive_dir`) | VERIFIED | real probe, stated skip text, README row at tests/README.md:47 |
| `tests/test_case_sensitive_install.py` | VERIFIED | 5 tests, all pass |
| `widgets/theme.py` `SURFACE_BASE` | VERIFIED | line 15, used by conflict_row |
| `widgets/help_dialog.py` CSS from tokens, new Help text | VERIFIED | imports `FINISHING_TEXT` from import_dialog |
| `table_generator.py` `_same_rel`, `_add_entry`, `add_library_entries(repo_root, add_missing, fold)` | VERIFIED | lines 303-450 |
| `main_window.py` `_dest_path`, `_sync_path_vars`, `_ask_kicad_open`, both post-install branches | VERIFIED | callers pass `repo_root=REPO_ROOT`; existing-library branch uses `add_missing=False` |
| `widgets/backup_dialog.py` `_folder` | VERIFIED | blank -> None |
| `library_scanner.py` `ConfirmAnswer`, re-read merge loop | VERIFIED | lines 212-390 |
| `widgets/import_dialog.py` `is_finishing`, `_enter_finishing`, `_try_finish`, `_finish_close`, `FINISHING_TEXT` | VERIFIED | |
| `tests/conftest.py` teardown join | VERIFIED | pytest_runtest_teardown present; full suite clean |

### Key Link Verification

| From | To | Status |
| ---- | -- | ------ |
| planner `_decide_file` -> `make_op(name=identity_of(hit))` | WIRED |
| help_dialog -> theme tokens | WIRED |
| conflict_row `_button_qss` -> `SURFACE_BASE` | WIRED |
| main_window `_finish_post_install` -> `add_library_entries(repo_root=REPO_ROOT)` | WIRED |
| `_finish_post_install` / `_on_generate` -> `_dest_path()` None stop | WIRED |
| import_dialog `_reap` -> `_try_finish(exclude=worker)` | WIRED |
| `_updating` -> `self._oneoff` | WIRED |
| main_window `_sync_path_vars` -> `kicad_running` via TaskWorker | WIRED |
| `_on_path_var_check` -> `sync_kicad_path_vars(running=lambda: names)` | WIRED |
| main_window `closeEvent` -> `is_finishing()` / `_close_after_dialog` | WIRED |
| help_dialog -> `import_dialog.FINISHING_TEXT` | WIRED |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| VER-02 on a real case-sensitive folder, plus Help, table entries, backup dialog | `env/Scripts/python.exe -m pytest tests/test_case_sensitive_install.py tests/test_help_dialog.py tests/test_table_add_entries.py tests/test_backup_dialog.py -q -rs` | 50 passed, no skips | PASS |
| REV-05 config merge and main window | `pytest tests/test_kicad_config.py tests/test_main_window.py -q -rs` | 109 passed | PASS |
| REV-03/04 Finishing, close, one-off, cancel, escape | `pytest tests/test_import_dialog.py -k "finishing or change_waits or close or oneoff or one_off or cancel or escape"` | 31 passed | PASS |
| REV-01/02/05 window level | `pytest tests/test_main_window_import.py -k "tables or dest or blank or close or retry or kicad"` | 30 passed | PASS |
| Full suite at 9412c80 (orchestrator evidence, log checked) | log `fullsuite-9412c80.log` | 9267 passed, 4 skipped (the four documented workstation skips), 0 failed. `git diff 9412c80..HEAD` touches only help_dialog.py, test_help_dialog.py and planning docs, so HEAD code equals the tested code apart from Help text, which test_help_dialog covers | PASS |

### Requirements Coverage

| Requirement | Source Plan | Status | Evidence |
| ----------- | ----------- | ------ | -------- |
| VER-02 | 12-01 | SATISFIED | SC5 |
| UI-01 | 12-02 | SATISFIED | SC4 |
| REV-01 | 12-03, 12-08 | SATISFIED | SC1 |
| REV-02 | 12-04, 12-08 | SATISFIED | SC1 |
| REV-03 | 12-05, 12-08 | SATISFIED | SC2 |
| REV-04 | 12-05, 12-07, 12-08 | SATISFIED | SC2 (live check pending) |
| REV-05 | 12-06, 12-08 | SATISFIED | SC3 (live dialog pending) |

All seven phase IDs appear in PLAN frontmatter and in REQUIREMENTS.md; no orphaned requirements. Bookkeeping: REQUIREMENTS.md still shows these seven as `[ ]` / "Pending" and ROADMAP lists Phase 12 as not yet checked at the top list (line 33); the orchestrator should flip them on phase completion.

### Anti-Patterns Found

No TBD/FIXME/XXX/TODO/HACK markers in the files changed by this phase. No stubs or hollow props found in the traced paths.

12-REVIEW.md lists 0 critical, 5 warning, 6 info, all open in 12-REVIEW-DISPOSITION.md and advisory. Relevant to this phase's goal but not blocking any success criterion:

- WR-01: an exception inside `_on_path_var_check` leaves `_path_var_busy` set until restart.
- WR-02: a small lost-update window remains between the re-read and the atomic write of `kicad_common.json`; SC3 as written (start from the current content) is met.
- WR-03: `_close_after_check` is never reset if the deferred close is vetoed.
- WR-04: new text names `kicad-cli` and `kicad_common.json` (see judgment prohibition below).
- WR-05: the "missing from tables" hint depends on matching message text.

### Judgment-tier prohibition (flagged, non-authoritative)

12-08: "User-facing Help text must never use raw KiCad field names or code identifiers." Verifier verdict: no `ki_*` field names in the new text, test asserts that. The new Help sentences and the slow-note do name `kicad-cli`, which the Help did not mention before this phase. Flagged `unverified-prohibition - human review recommended`; not treated as a pass or a gap.

### Human Verification Required

1. **D-13 owner run.** Run `env/Scripts/python.exe -m pytest tests/test_case_sensitive_install.py -rs`. Expected 5 passed, 0 skipped. Why human: planned owner UAT (verifier run already passed).
2. **Help and conflict-row look** at 100% and 200%. Expected as before; headings larger than body. Why human: visual.
3. **KiCad-open dialog with real KiCad running.** Expected wording, three buttons, Retry default, Not now writes nothing. Why human: live process, modal dialog.
4. **Live kicad-cli rebuild:** Change..., another package, Cancel on the strip, close dialog and main window. Expected window stays live, action runs by itself, slow note after 10 s. Why human: real timing and responsiveness.
5. **Wording judgment** for `kicad-cli` and `kicad_common.json` in new user-facing text (WR-04). Why human: owner preference.

### Gaps Summary

No gaps. All five roadmap success criteria are backed by code and by passing tests, and every requirement ID is accounted for. Status is `human_needed` only because the phase's own plans and validation table reserve live, visual and owner-judgment checks that cannot be done programmatically, plus one flagged judgment-tier prohibition.

---

_Verified: 2026-11-01_
_Verifier: Claude (gsd-verifier)_
