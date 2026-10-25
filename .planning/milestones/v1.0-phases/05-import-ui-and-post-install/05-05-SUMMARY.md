---
phase: 05-import-ui-and-post-install
plan: 05
subsystem: ui
tags: [pyside6, import-dialog, start-page, downloads-offer, qsettings, ux-02]

requires:
  - phase: 05-import-ui-and-post-install
    provides: "05-01 ImportDialog, TaskWorker, ImportCore, OpenOutcome, issues_logged; 05-03 theme constants (AMBER, ERROR, MUTED, SP_LG, SP_XL, HEADING_PT)"
provides:
  - "importer/downloads.py: Qt-free newest_zip(folder) and age_text(seconds)"
  - "settings.load_import_dir / save_import_dir (key import/last_dir, re-checked with is_dir on every load)"
  - "ImportDialog Start page per UI-SPEC: centred 560 px column, Downloads offer, Browse zip... / Browse folder..., refused-or-empty issue list"
  - "Edit page package header (name, vendor label, Change...) and ImportCore.downloads_dir"
affects: [05-06, 05-07, 05-08, 05-09, 05-10, 05-11, phase-06-commit]

plan_head_before: 42286cae6dd079828e37ea4a5ff9d6b9be6ab0c4
plan_head_after: 3397e4f7154b282d3b4b05450791e88c529a0049

actuals:
  tokens: 9200
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Offer lookup on a TaskWorker started from QTimer.singleShot(0) in showEvent; the offer only lists, open_path runs only from an explicit click"
    - "_OfferLabel: PlainText one-line label that middle-elides only the name and keeps the full text available through full_text()"
    - "Start page error state is a plain-text QListWidget (QListWidgetItem), so no package string is ever interpreted as markup"

key-files:
  created:
    - kicad_lib_manager/importer/downloads.py
    - tests/test_import_downloads.py
    - tests/test_settings_import.py
  modified:
    - kicad_lib_manager/settings.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_import_dialog.py

key-decisions:
  - "A package counts as 'refused' for the closing line when package.refused OR any shown Issue is an ERROR. A KiCad 5-only zip is not package.refused (the ERROR comes from detection), but the plan requires 'Pick another file.' for it; 'Check that you downloaded the KiCad format...' is reserved for nothing-found with only warnings or no Issues"
  - "Browse start dir uses the folder found by the offer lookup when it has finished, else calls core.downloads_dir() directly, else Path.home()"
  - "The issue list's minimum height follows its row count (capped at 160 px) so one row does not claim a 160 px box; maximumHeight stays 160"
  - "Change... is ignored while installing or while an open worker runs, and is disabled during install; it clears _building after waiting so the state is clean at once, and the stale build result is dropped by the generation guard"
  - "Singular age text ('1 minute ago') as recorded in the plan"

patterns-established:
  - "Start-page tests use a synthetic Custom/ layout (zipfixtures.write_custom_layout) plus fake core calls, so they run without the Custom submodule"

requirements-completed: [UX-02]

coverage:
  - id: D1
    description: "Start page shows the newest .zip in Downloads with its age and an Open button; it is never opened without a click"
    requirement: UX-02
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_start_page_offers_newest_zip"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_start_page_never_auto_opens"
        status: pass
      - kind: unit
        ref: "tests/test_import_downloads.py#test_newest_zip_picks_latest"
        status: pass
      - kind: unit
        ref: "tests/test_import_downloads.py#test_age_text_buckets"
        status: pass
    human_judgment: false
  - id: D2
    description: "No-zip and no-Downloads-folder messages; long names elided with the full path as tooltip"
    requirement: UX-02
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_start_page_no_zip_message"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_start_page_no_downloads_folder"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_start_page_offer_elides_long_name_and_keeps_full_path"
        status: pass
    human_judgment: false
  - id: D3
    description: "Browse zip... and Browse folder... open in the remembered import folder and save it back; a stale stored path is ignored"
    requirement: UX-02
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_start_page_browse_uses_last_dir"
        status: pass
      - kind: unit
        ref: "tests/test_settings_import.py#test_import_dir_round_trip"
        status: pass
      - kind: unit
        ref: "tests/test_settings_import.py#test_deleted_import_dir_gives_none"
        status: pass
    human_judgment: false
  - id: D4
    description: "A refused or empty package keeps the dialog on the Start page with its reasons (package warnings included when nothing was detected), logged to the main log"
    requirement: UX-02
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_start_page_refused_zip_lists_issues"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_nothing_found_shows_package_warnings"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_nothing_found_no_issues_message"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_issue_list_caps_height_and_wraps"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_start_page_list_hidden_and_cleared"
        status: pass
    human_judgment: false
  - id: D5
    description: "Package header and Change... return to the Start page, discard edits and close the package"
    requirement: UX-02
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_change_returns_to_start_and_closes_package"
        status: pass
    human_judgment: false
  - id: D6
    description: "Start page layout and look match the UI-SPEC (spacing, centred column feel, colours)"
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_start_page_layout_and_focus"
        status: pass
    human_judgment: true
    rationale: "Tests check heading size, body copy, max width and focus; no test judges the visual result on a real display (the offscreen test platform has no fonts)"

duration: 15min
completed: 2026-10-22
status: complete
---

# Phase 5 Plan 05: Import Start Page Summary

**Start page of the Import dialog: the newest Downloads zip is offered (never opened without a click), Browse zip/folder start in the remembered import folder, refused or empty packages explain themselves in a plain-text issue list including package warnings, and the Edit page gets a package header with Change....**

## Performance

- **Duration:** about 15 min
- **Started:** 2026-10-22T10:00:00Z (approx.)
- **Completed:** 2026-10-22T10:14:14Z
- **Tasks:** 2 (both TDD), 4 commits (RED and GREEN for each)
- **Files modified:** 6 (3 created, 3 modified)

## Accomplishments

- `importer/downloads.py` (stdlib only): `newest_zip` scans one folder with `os.scandir`, case-insensitive `.zip`, files only, skips per-entry OSError; `age_text` gives "just now" below a minute (and for future mtimes), then minutes, hours, days with the singular for 1.
- `ImportDialog` Start page rebuilt as a centred column (max 560, top inset SP_XL, SP_LG between blocks): 10pt bold heading, body copy, Downloads offer (looked up on a worker after show; "Newest in Downloads: {name} ({age})" with the name middle-elided, full-path tooltip, Open button; "No .zip files found in your Downloads folder." in MUTED; "Downloads folder not found."), Browse zip... and Browse folder..., initial focus on Browse zip.
- `settings.load_import_dir` / `save_import_dir` under `import/last_dir`; every load re-checks `is_dir()`.
- Refused or empty package: package and detection Issues merged once (`dict.fromkeys`), all logged through `issues_logged`, ERROR/WARNING rows shown glyph-prefixed in ERROR/AMBER, closing MUTED line, package closed; the list is cleared and hidden when the next read starts, which shows "Reading package..." with disabled buttons.
- Edit page header: bold "Package: {name}", MUTED vendor label (`vendor_label()` maps UltraLibrarian, Loose, Unknown), right-aligned Change... over a 1 px line. Change... waits for a running build, closes the package, resets all per-package state and returns to the Start page with title "Import Part".

## TDD Gate Compliance

| Task | RED commit | GREEN commit |
|------|-----------|--------------|
| 1 | 8eb5a0e `test(05-05)` | 0a33d59 `feat(05-05)` |
| 2 | 61aae64 `test(05-05)` | 3397e4f `feat(05-05)` |

RED evidence: Task 1's downloads tests failed at collection (`ModuleNotFoundError: kicad_lib_manager.importer.downloads`) and the five Start-page dialog tests failed on `TypeError: ImportCore.__init__() got an unexpected keyword argument 'downloads_dir'`. Task 2: 19 tests failed on missing API (`AttributeError` for `load_import_dir`, `_browse_folder_btn`, `_issue_box`, `_change_btn`, `vendor_label`). These are missing-API REDs for new surface (load or attribute failures, not assertion failures), the same weaker form accepted in 05-01; the classifier (`check tdd-red-evidence`) was not run. Semantic assessment: acceptable for greenfield modules and widgets, the behavioural assertions first executed in GREEN.

## Task Commits

1. Task 1 RED: `8eb5a0e` test(05-05): add failing tests for the Downloads offer on the Start page
2. Task 1 GREEN: `0a33d59` feat(05-05): Start page offers the newest Downloads zip without opening it
3. Task 2 RED: `61aae64` test(05-05): add failing tests for Browse folder, refused packages and the package header
4. Task 2 GREEN: `3397e4f` feat(05-05): Browse in the last-used folder, explain refused packages, package header with Change...

## Files Created/Modified

- `kicad_lib_manager/importer/downloads.py` - Qt-free `newest_zip`, `age_text`
- `kicad_lib_manager/settings.py` - `load_import_dir`, `save_import_dir` under a new "Import folder" divider
- `kicad_lib_manager/widgets/import_dialog.py` - `default_downloads_dir`, `ImportCore.downloads_dir`, `_OfferLabel`, `vendor_label`/`_VENDOR_LABELS`, Start page, issue box, package header, `_on_change`
- `tests/test_import_downloads.py`, `tests/test_settings_import.py` - new
- `tests/test_import_dialog.py` - 5 Task 1 tests plus 11 Task 2 tests (one parametrised); `test_refused_package_stays_on_start_and_logs` now reads the issue list instead of the removed `_start_issues` label

## Decisions Made

See `key-decisions` above. The closing-line rule is the one to review: "refused" includes any ERROR Issue, not only `package.refused`, because the plan's KiCad 5-only example must read "Pick another file." while `detect_candidate` reports that case as a detection ERROR.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing test read the removed `_start_issues` label**
- **Found during:** Task 2 (GREEN)
- **Issue:** `test_refused_package_stays_on_start_and_logs` (plan 05-01) asserted on `_start_issues.text()`; the plan replaces that label with the issue list.
- **Fix:** the assertion now checks the issue box is shown and a row mentions "not a .zip file".
- **Files modified:** tests/test_import_dialog.py
- **Commit:** 3397e4f

**2. [Rule 2 - Missing critical] Change... guarded during install**
- **Issue:** UI-SPEC says Change... is disabled while Installing; discarding the package under the install worker would break WR-04.
- **Fix:** `_on_install_clicked` disables the button, `_update_install_state` re-enables it, and `_on_change` returns early while installing, closing, or reading.
- **Commit:** 3397e4f

**3. [Rule 1 - Bug, test only] Offscreen platform has no fonts**
- **Issue:** text widths are exaggerated (12 px per char), so the offer label elides even short names and `text()` cannot be compared with the full copy.
- **Fix:** `_OfferLabel.full_text()` returns the unelided text; tests assert on it, and a separate test proves eliding and the full-path tooltip.
- **Commit:** 0a33d59

Total deviations: 3 auto-fixed (2 bugs, 1 missing guard). Impact: none on scope.

## Verification

- Worktree: `tests/test_import_dialog.py tests/test_settings_import.py tests/test_import_downloads.py tests/test_main_window.py tests/test_main_window_import.py tests/test_importer_layering.py tests/test_layering.py` gives 90 passed, 11 skipped. All 11 skips are the plan 05-01 `custom_copy` tests in `tests/test_import_dialog.py` (Custom submodule not checked out here); every new test of this plan runs in the worktree because it uses a synthetic Custom layout.
- Custom-enabled mirror (copy of the worktree sources plus the main checkout's `Custom/` outside the repo): `tests/test_import_dialog.py` and `tests/test_main_window_import.py` give 38 passed, 0 skipped, so the 11 skipped tests pass with the new Start page.
- Full suite in the worktree: 4 failed, 1316 passed, 77 skipped. The 4 failures are the known KiCad 10 baseline failures (`test_install_plan.py::test_version_real_cli_into_20241209`, `::test_library_real_cli_new_header`, `::test_noop_second_plan_after_normalised_apply`, `tests/test_kicad_cli.py::test_real_cli_upgrades_ul_symbol_deterministically`); the 77 skips are Custom/Wurth submodule and symlink-privilege skips.
- Acceptance greps: `downloads.py` has 0 PySide6 import lines; all required strings and signatures are present.

## Issues Encountered

None.

## Known Stubs

None. Browse, Open, Change... and the issue list are all wired to live data; nothing returns placeholder values.

## Threat Flags

None beyond the plan's threat model. T-05-15 (no auto open) is proven by `test_start_page_never_auto_opens`, T-05-16 by `test_import_dir_round_trip` and `test_deleted_import_dir_gives_none`, T-05-17 by `test_issue_text_is_plain` (markup in an Issue stays literal), T-05-18 by `test_nothing_found_shows_package_warnings`.

## Next Phase Readiness

Plans 05-06 onward build on the Edit page header (`_package_label`, `_vendor_label`, `_change_btn`) and on `_on_change`, which resets through `_reset_edit_state`; a plan that adds per-package edits or debounce timers must extend `_on_change` and `_reset_edit_state` to clear them (the plan text asks Change... to "stop pending timers"; there are none yet). No files outside this plan's `files_modified` were touched.

## Self-Check: PASSED

- Created files exist: `kicad_lib_manager/importer/downloads.py`, `tests/test_import_downloads.py`, `tests/test_settings_import.py`.
- Commits 8eb5a0e, 0a33d59, 61aae64 and 3397e4f are ancestors of HEAD.
