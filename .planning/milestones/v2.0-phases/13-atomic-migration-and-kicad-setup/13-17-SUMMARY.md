---
phase: 13-atomic-migration-and-kicad-setup
plan: 17
subsystem: migration
tags: [migration, atomic-libraries, qt, pyside6, tdd, main-window, help-docs]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "plan 13-16's finished MigrationDialog (Run, the failure view, the Result view with Generate Tables/Set Up KiCad Chooser buttons, the commit step) and its migrated/generate_requested/setup_chooser_requested/issues_logged/atomic_check_requested signals plus is_running()/is_committing()/is_busy(); plan 13-05's inventory.migration_reason(); plan 13-07's _on_setup_chooser/_act_setup_chooser; plan 13-19's checkout banner and _check_checkout"
provides:
  - "kicad_lib_manager/main_window.py: File > Migrate to Atomic Libraries... (Ctrl+Shift+M) with its D-13 enable rule (_refresh_migrate_action), _open_migration's refusal/open logic, _on_migrated's quiet rescan, _select_atomic_libraries (the plural of _apply_post_install_selection), _on_migration_generate/_run_migration_generate (the D-24 Generate Tables hand-off), the importer/migration mutual exclusion (_import_busy, _open_import, closeEvent), and _on_generate now returning the write_tables Issues"
  - "kicad_lib_manager/widgets/help_dialog.py: HELP_PAGES[\"migrating\"], its TOC entry after Importing Parts, and the Ctrl+Shift+M shortcuts row"
affects: ["13-18 (CLAUDE.md/PROJECT.md/tests/README.md docs); any future plan that wires further main-window actions around the migration window"]

actuals:
  tokens: 10600
  tasks: 3
  commits: 5
  plan_head_before: 29c22eca6e5d30921591c14803455fd351947fe3
  plan_head_after: a56389455b2a74f0d64240a94dd1aa596ffd1de0

tech-stack:
  added: []
  patterns:
    - "_select_atomic_libraries is the plural form of the existing _apply_post_install_selection: selects every library whose source is Custom and is_atomic(nickname) is true (the shared Atomic_Footprints library is caught by the same check, no separate constant needed), unchecking a selected same-nickname peer exactly like the singular version does"
    - "_pending_migration / _migration_scan_started is the same two-flag shape as the existing _PostInstall.scan_started: a plain bool pair (not a dataclass, since there is only one in-flight migration at a time) distinguishes a rescan started because of the migration from an unrelated scan that happened to be running when migrated fired, so _on_scan_finished never applies the Atomic_ selection against a stale pre-migration scan result"
    - "_on_migration_generate defers via _generate_after_scan (set, log, return) while a scan/rescan is still outstanding, exactly mirroring the shape of _sync_path_vars's own retry-on-busy pattern elsewhere in this file; _on_scan_finished calls the actual work (_run_migration_generate) directly rather than through the busy-gated public method, since at that point in the try block self._worker has not yet been nulled by _finish_scan (which runs in the finally clause)"
    - "_on_generate now returns list[Issue] instead of None (a backward-compatible signature widening -- existing Qt signal connections ignore the return value) so _run_migration_generate can inspect it for table.stale_managed and add the one extra MIGRATION-ATOMIC.md relink hint line, without write_tables being called a second time just to get that answer"
    - "closeEvent's migration-dialog guard copies the import dialog's exact shape (ignore while is_running()/is_committing(), otherwise reject() then defer via a _close_after_migration flag if is_busy() is still true after the reject), so the two dialogs read as one pattern in this file rather than two"
    - "help_dialog.py imports migration_dialog.py's button-text constants (RUN_TEXT, GENERATE_TEXT, CHOOSER_TEXT, OPEN_MAP_TEXT, FILES_TAB_TEXT, LEFTOVERS_TEXT, MOVE_FOOTPRINT_TEXT) the same way it already imports import_dialog.py's, confirmed not circular since migration_dialog.py never imports help_dialog (unlike import_dialog.py, which does so locally inside one method specifically to avoid that cycle)"

key-files:
  modified:
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_help_dialog.py
  created:
    - tests/test_main_window_migration.py

key-decisions:
  - "_act_migrate was added to the blanket _set_scan_running disable-list in Task 1 (tracer) for a safe interim state, then removed from it in Task 2 in favour of a dedicated branch (disable outright while running, else _refresh_migrate_action()) once the real D-13 enable rule existed -- normal evolution within one plan's own task sequence, not a Rule 1-4 deviation"
  - "_refresh_migrate_action() is called both inside _set_scan_running(False) and, guarded by 'no new scan was just started', again at the very end of _finish_scan, matching the plan's literal wording for both call sites even though in the common case (nothing pending) the second call is a harmless no-op repeat of the first"
  - "_open_import logs 'Close the migration window before migrating.' -- actually 'Close the migration window before importing.' -- when refused for that specific reason, mirroring _open_migration's own 'Close the import window before migrating.' line, so the mutual exclusion is explained in both directions instead of failing silently only on one side"

requirements-completed: [MIG-02, MIG-04, TBL-01]

coverage:
  - id: D1
    description: "File > Migrate to Atomic Libraries... (Ctrl+Shift+M) opens the migration window; it is enabled only while Custom still has a v1-named library or a .bak in Custom/Symbols, and otherwise greyed out with a tooltip saying why; the state is re-evaluated after every scan and disabled while a scan runs"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_main_window_migration.py#test_migrate_enabled_only_with_v1_libraries"
        status: pass
    human_judgment: false
  - id: D2
    description: "After a successful Run the main window rescans quietly and selects every Atomic_ symbol library of Custom and Atomic_Footprints, so the regenerated tables keep them"
    requirement: "MIG-04"
    verification:
      - kind: unit
        ref: "tests/test_main_window_migration.py#test_generate_after_migration_keeps_atomic_libraries"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Result view's Generate Tables button runs the existing Generate path with the Atomic_ libraries selected: old managed entries are removed and logged as stale, new ones are added with descriptions; a Generate requested mid-rescan is deferred and runs exactly once after the scan"
    requirement: "MIG-04, TBL-01"
    verification:
      - kind: unit
        ref: "tests/test_main_window_migration.py#test_generate_after_migration_keeps_atomic_libraries"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_migration.py#test_generate_requested_during_rescan_waits"
        status: pass
    human_judgment: false
  - id: D4
    description: "The Result view's Set Up KiCad Chooser... button runs the same confirmed action as the menu"
    requirement: "MIG-04"
    verification:
      - kind: unit
        ref: "tests/test_main_window_migration.py#test_chooser_button_runs_the_menu_action"
        status: pass
    human_judgment: false
  - id: D5
    description: "The import window and the migration window never run at the same time; the main window cannot close while a migration runs or commits"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_main_window_migration.py#test_import_and_migration_exclude_each_other"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_migration.py#test_close_blocked_while_migration_runs"
        status: pass
    human_judgment: false
  - id: D6
    description: "The User Guide has a Migrating to Atomic Libraries page under How to Use, opened by the migration window's Help and F1, and the Keyboard Shortcuts page lists Ctrl+Shift+M"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_migrating_page"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_shortcuts_complete"
        status: pass
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_outline_numbers_follow_the_menu_order"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 17: Migration wired into the main window Summary

**File > Migrate to Atomic Libraries... (Ctrl+Shift+M) now opens the migration window, a successful Run rescans quietly and keeps the new `Atomic_` libraries selected through Generate Tables, the import and migration windows refuse to run together, and the User Guide gained a full "Migrating to Atomic Libraries" page.**

## Performance

- **Duration:** ~70 min
- **Started:** 2026-11-11
- **Completed:** 2026-11-11
- **Tasks:** 3 completed
- **Files modified:** 4 (2 production modules extended, 1 test file extended, 1 new test file)

## Accomplishments

- `_act_migrate` (Ctrl+Shift+M) opens `MigrationDialog`, wired to its `issues_logged`, `help_requested`, `migrated`, `generate_requested`, `setup_chooser_requested` and `atomic_check_requested` signals; `_refresh_migrate_action` enables it exactly when `migration_reason()` finds something to migrate and no scan runs, with `_NOTHING_TO_MIGRATE` as the disabled reason
- `_on_migrated` starts a quiet rescan; `_select_atomic_libraries` (the plural of `_apply_post_install_selection`) selects every Custom `Atomic_` symbol/footprint library so the rescan never drops them back out (P-01), using the same two-flag (`_pending_migration`/`_migration_scan_started`) shape as the existing post-install pattern to avoid acting on a stale pre-migration scan
- `_on_migration_generate`/`_run_migration_generate` hand the Result view's Generate Tables button to the normal `_on_generate` path with the `Atomic_` libraries kept selected, deferring via `_generate_after_scan` while a scan is still in flight, and logging the `MIGRATION-ATOMIC.md` relink hint when old entries are removed as stale; `_on_generate` now returns the `write_tables` Issues so this hand-off can inspect them
- The migration and import windows exclude each other (`_import_busy` now also reports busy while `_migration_dialog` is open; each refusal logs why) and `closeEvent` gained a migration guard matching the import dialog's own shape (ignore while running/committing, otherwise reject and defer the window's own close until idle)
- `HELP_PAGES["migrating"]` documents the whole flow -- Before you start, The preview, Run and result, Afterwards -- reusing `migration_dialog.py`'s own button-text constants; added to the How to Use TOC after Importing Parts, and `Ctrl+Shift+M` added to the Keyboard Shortcuts page

## Task Commits

Task 1 (`type="tracer"`) is a single commit; Tasks 2 and 3 (`tdd="true"`) each carry a RED test commit then a GREEN feat commit:

1. **Task 1: tracer -- migrate, rescan, Generate keep the new Atomic_ libraries** - `dc409b2` (feat)
2. **Task 2 RED** - `5e85447` (test) -- 4 new tests, 3 fail genuinely (missing `_refresh_migrate_action`, the importer/migration exclusion, and the close guard), 1 (`test_chooser_button_runs_the_menu_action`) passes immediately because Task 1's wiring already covers it
3. **Task 2 GREEN** - `279bb62` (feat) -- all tests in the Task 2 verification command pass
4. **Task 3 RED** - `64c853f` (test) -- 3 new/changed tests fail genuinely (`HELP_PAGES["migrating"]` does not exist, the shortcuts row is missing, the outline numbers/anchor count don't match yet)
5. **Task 3 GREEN** - `a563894` (feat) -- all 67 tests in `tests/test_help_dialog.py` pass

**Plan metadata:** committed together with this SUMMARY (worktree mode excludes STATE.md/ROADMAP.md; the orchestrator updates those centrally after merge).

## Files Created/Modified

- `kicad_lib_manager/main_window.py` -- `MIGRATION_CORE`/`MIGRATE_TEXT`/`_MIGRATE_TOOLTIP`/`_NOTHING_TO_MIGRATE`/`_MIGRATION_TOPIC` constants; `_migration_dialog`/`_pending_migration`/`_migration_scan_started`/`_generate_after_scan`/`_close_after_migration` attributes; `_act_migrate` wired into `_build_menu` and `_set_scan_running`; `_refresh_migrate_action`, `_open_migration`, `_on_migration_dialog_finished`, `_on_migrated`, `_select_atomic_libraries`, `_on_migration_generate`, `_run_migration_generate`; `_on_generate` now returns `list[Issue]`; `_import_busy`/`_open_import`/`closeEvent` extended for the migration/import exclusion; `_start_scan`/`_finish_scan`/`_on_scan_finished` extended for the post-migration rescan-and-select flow
- `kicad_lib_manager/widgets/help_dialog.py` -- `HELP_PAGES["migrating"]`, the How to Use TOC entry, the Ctrl+Shift+M shortcuts row, and the new import of `migration_dialog.py`'s button-text constants
- `tests/test_main_window_migration.py` (new) -- own fixture (`FakeMigrationDialog`, a `make_window` builder with `symbols`/`pretty_dirs`/`bak_files` controls and the same KiCad-config isolation as `tests/test_main_window.py`/`tests/test_main_window_chooser.py`) plus 6 behavior tests across the two code tasks
- `tests/test_help_dialog.py` -- `test_help_migrating_page`, the `Ctrl+Shift+M` row in `test_help_shortcuts_complete`, and `MENU_NUMBERS`/the anchor-count assertion updated for the new page

## Decisions Made

See `key-decisions` in the frontmatter: `_act_migrate`'s interim blanket-disable in Task 1 replaced by the dedicated D-13 enable rule in Task 2; `_refresh_migrate_action` called from both `_set_scan_running(False)` and (guarded) the end of `_finish_scan`, matching the plan's literal wording even where the second call is a no-op repeat; `_open_import`'s new refusal log line mirroring `_open_migration`'s existing one.

## Deviations from Plan

None - plan executed exactly as written, Rules 1-3. No auto-fixes were needed. The `_act_migrate` tuple membership change between Task 1 and Task 2 is normal evolution within this plan's own task sequence (explicitly directed by Task 2's action text), not an unplanned deviation.

---

**Total deviations:** 0 auto-fixed.
**Impact on plan:** None - every acceptance criterion and the plan's own verification command pass unchanged.

## TDD Gate Compliance

| Task | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| Task 1 (tracer) | - | `dc409b2` (feat, single tracer commit) | - | Pass |
| Task 2 | `5e85447` (test) - 3/4 new tests genuinely fail; 1 (`test_chooser_button_runs_the_menu_action`) passes immediately | `279bb62` (feat) - all tests in the Task 2 verification command pass | not needed | Pass* |
| Task 3 | `64c853f` (test) - 3/3 new/changed tests genuinely fail | `a563894` (feat) - all 67 tests in `tests/test_help_dialog.py` pass | not needed | Pass |

**Task 1 note:** Task 1 is `type="tracer"`. Its own `<verify>` command (`pytest tests/test_main_window_migration.py tests/test_main_window.py tests/test_main_window_chooser.py`) carried only `<automated>` verification with no `<human-check>`, and `workflow._auto_chain_active`/`workflow.auto_advance` were both `false` while `workflow.human_verify_mode` is `end-of-phase` (project default) - per the executor's tracer-feedback precedence chain (row 3: interactive + `end-of-phase` + automated-only), the gate re-ran `<verify>` (90/90 passed) and continued straight to Task 2 with no synthesized checkpoint.

**Task 2 note (*):** `test_chooser_button_runs_the_menu_action` passed in the RED run because it only confirms wiring Task 1 already completed (`setup_chooser_requested` -> `_on_setup_chooser`); no Task 2 production code was needed to make it pass. This is an "unexpected GREEN" only in the narrow, explainable sense documented by the plan's own behavior list -- it is not a sign the Task 2 behaviors (the enable rule, the exclusion, the close guard) were already implemented, which the other 3 tests in the same RED commit prove were not. Investigated and accepted rather than silently committed.

**RED evidence caveat:** `gsd_run check tdd-red-evidence` was not invoked from inside this isolated worktree executor session (matching the same caveat recorded in every prior plan's SUMMARY in this phase - no `.claude/gsd-core/` is present in this worktree). RED was established by running each task's own `<automated>` pytest command directly before its GREEN commit and inspecting the failures: every Task 2 and Task 3 failure was a genuine `AssertionError` or `KeyError` on the missing behavior (never a collection or import error, never an unrelated assertion).

## Issues Encountered

None beyond the Task 2 unexpected-GREEN note above (investigated and accepted, not a bug).

## Known Stubs

None.

## Threat Flags

None - both STRIDE register entries (T-13-40 concurrent importer/migration writes, T-13-41 tables regenerated without the new libraries) are mitigated by code in this plan and proven by `test_import_and_migration_exclude_each_other`/`test_close_blocked_while_migration_runs` and `test_generate_after_migration_keeps_atomic_libraries` respectively; no new write surface outside the plan's own `<threat_model>` was introduced.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- MIG-02, MIG-04 and TBL-01 are now complete at the main-window level: the migration is reachable only when there is something to migrate, mutually exclusive with the importer, unclosable mid-run/mid-commit, and followed by a Generate Tables hand-off that keeps the new libraries; the User Guide documents the whole flow end to end.
- This was the last code plan of the phase (per its own objective). Plan 13-18 (CLAUDE.md/PROJECT.md/tests/README.md docs) and the phase's end-of-phase verification are next.
- No blockers.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/main_window.py
- FOUND: kicad_lib_manager/widgets/help_dialog.py
- FOUND: tests/test_main_window_migration.py
- FOUND: tests/test_help_dialog.py
- FOUND: commit dc409b2 (Task 1)
- FOUND: commit 5e85447 (Task 2 RED)
- FOUND: commit 279bb62 (Task 2 GREEN)
- FOUND: commit 64c853f (Task 3 RED)
- FOUND: commit a563894 (Task 3 GREEN)
- `grep -n "def _select_atomic_libraries\|def _on_migration_generate\|def _on_migrated\|Ctrl+Shift+M" kicad_lib_manager/main_window.py` -> all four found
- `grep -n "def _refresh_migrate_action\|_NOTHING_TO_MIGRATE" kicad_lib_manager/main_window.py` -> both found
- `grep -n "\"migrating\", \"Migrating to Atomic Libraries\"\|Ctrl+Shift+M" kicad_lib_manager/widgets/help_dialog.py` -> both found
- `python -m pytest tests/test_main_window_migration.py tests/test_main_window.py tests/test_main_window_import.py tests/test_main_window_chooser.py tests/test_help_dialog.py tests/test_plain_names.py -q` -> 222 passed
- `python -m pytest tests/ -q -k "help_dialog or migration_dialog or main_window or import_dialog"` -> 510 passed (broader regression check; not required by this plan's own done-criteria but run anyway since `help_dialog.py` gained a new cross-module import)
- `git rev-list --count 29c22eca6e5d30921591c14803455fd351947fe3..HEAD` -> 5 (matches `actuals.commits`)
