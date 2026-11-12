---
phase: 13-atomic-migration-and-kicad-setup
plan: 19
subsystem: kicad-config
tags: [kicad, qt, gui, checkout-check, help-docs, d-26]

# Dependency graph
requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "kicad_setup.checkout_mismatch/wrong_checkout_warning/CHECKOUT_MISMATCH (plan 13-02), the shared D-26 wrong-checkout compare"
provides:
  - "main_window.py: CHECKOUT_CONFIG_BASE test seam, _checkout_banner (amber, dismissible, plain-text) above the library tree, _check_checkout(after) wired into both _on_generate and _on_import_installed (D-26)"
  - "widgets/import_result.py: standalone checkout_hint status row beside generate_hint, same build/hide pattern"
  - "widgets/help_dialog.py: one sentence each on the Generating Tables and Importing Parts pages explaining the wrong-checkout warning"
affects: ["13-16 (migration Run refusal reuses checkout_mismatch; unaffected by this plan's UI-only wiring)"]

# Actuals (#2632)
actuals:
  tokens: 5915
  tasks: 2
  commits: 3
  plan_head_before: c1bdc2de6aba85e620725251b75efe58417cc86f
  plan_head_after: c000f5227a131529c9f4e3a7940de31f51db963e

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "D-26 warn-never-block: _check_checkout(after) is the single call site both Generate Tables and Install Part use after their write already happened; it logs once and, for 'generate' only, shows/hides a persistent banner (Install Part gets its own Result-view row instead)"
    - "Banner shape copied from import_dialog.py's failureBanner (QFrame + amber left border + plain-text QLabel + dismiss QToolButton), reused for the D-26 notice between the toolbar and the library tree"

key-files:
  created:
    - tests/test_checkout_warning.py
  modified:
    - kicad_lib_manager/main_window.py
    - kicad_lib_manager/widgets/import_result.py
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_help_dialog.py
    - tests/test_main_window.py
    - tests/test_main_window_import.py

key-decisions:
  - "_check_checkout(after) is one method for both callers rather than two near-duplicates: it always compares and logs, and the `after` parameter (\"generate\"/\"install\") only decides whether the banner is shown/hidden, since Install Part renders its own text into the Result view instead"
  - "The banner is built on the same QFrame/AMBER_TINT/left-border/dismiss-QToolButton shape as import_dialog.py's failureBanner, so the D-26 notice looks native to the existing visual language instead of introducing a new one"

requirements-completed: [TBL-01, MIG-04]

coverage:
  - id: D1
    description: "Generate Tables writes the tables, then a dismissible amber banner above the library tree names both folders when KiCad reads another checkout; it is absent with no variable or no config, and hides itself once the folders match"
    requirement: TBL-01
    verification:
      - kind: unit
        ref: "tests/test_checkout_warning.py#test_generate_warns_on_other_checkout"
        status: pass
      - kind: unit
        ref: "tests/test_checkout_warning.py#test_generate_without_variable_shows_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_checkout_warning.py#test_matching_generate_hides_banner"
        status: pass
      - kind: unit
        ref: "tests/test_checkout_warning.py#test_banner_dismiss_and_plain_text"
        status: pass
    human_judgment: false
  - id: D2
    description: "Install Part writes the part, then the Result view's checkout_hint row shows the same amber warning; absent with no variable; both log exactly one WARNING"
    requirement: MIG-04
    verification:
      - kind: unit
        ref: "tests/test_checkout_warning.py#test_install_warns_in_result_view"
        status: pass
      - kind: unit
        ref: "tests/test_checkout_warning.py#test_install_without_variable_shows_no_hint"
        status: pass
    human_judgment: false
  - id: D3
    description: "The Generating Tables and Importing Parts help pages explain the warning: it names both folders, nothing is blocked, and KiCad sees the write once pushed here and pulled there"
    requirement: MIG-04
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_mentions_wrong_checkout"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 19: Generate Tables and Install Part Warn on the Wrong Checkout Summary

**A dismissible amber banner after Generate Tables and a Result-view row after Install Part both warn, without ever blocking, when KiCad reads its libraries from a different checkout than the one this app runs from (D-26), built on plan 13-02's shared `checkout_mismatch`/`wrong_checkout_warning`.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-11-11T16:29:00Z (approx.)
- **Completed:** 2026-11-11T16:53:59Z
- **Tasks:** 2 completed
- **Files created:** 1 (`tests/test_checkout_warning.py`)
- **Files modified:** 6

## Accomplishments

- `main_window.py` gained the `CHECKOUT_CONFIG_BASE` test seam, a `_checkout_banner` (amber-tinted `QFrame`, 2px left border, word-wrapped plain-text `QLabel`, "✕" dismiss `QToolButton`) placed between the toolbar and the library tree, and `_check_checkout(after)` built directly on plan 13-02's `kicad_setup.checkout_mismatch`/`wrong_checkout_warning`/`CHECKOUT_MISMATCH`.
- `_on_generate` calls `_check_checkout("generate")` right after `write_tables` (before `_sync_path_vars`): the tables are already written, so the compare only ever warns, shows the banner on a mismatch, and hides it once the folders match or there is nothing to compare.
- `_on_import_installed` calls `_check_checkout("install")` first and, when it returns text, sets the new `checkout_hint` row (standalone line, same hide pattern as `generate_hint`) in the Result view to `"⚠ {text}"` at `Severity.WARNING` — the install itself, the post-install rescan and the table step all run unaffected.
- The Generating Tables and Importing Parts help pages each gained one sentence explaining the warning: it names both folders, the write (tables or part) still happens, and KiCad sees it once it exists in the folder KiCad reads (push here, pull there).
- `tests/test_checkout_warning.py` (new): its own fixture (`CHECKOUT_CONFIG_BASE` monkeypatched to a tmp folder in every test) with 6 tests across both tasks — the mismatch case, the no-variable case, the matching-hides-the-banner case, the dismiss/plain-text case, the Install Result-view case, and the Install no-variable case.

## Task Commits

Each task was committed atomically; Task 2 (`tdd="true"`) followed RED → GREEN (no REFACTOR commit needed):

1. **Task 1: Generate warns visibly when KiCad reads another checkout (tracer)** - `e34f5ac` (feat)
2. **Task 2a: RED - failing tests for the Install Part checkout_hint and help sentences** - `242bb36` (test)
2. **Task 2b: GREEN - checkout_hint row, _on_import_installed wiring, help sentences** - `c000f52` (feat)

_No separate plan-metadata commit beyond this SUMMARY's own commit (worktree mode: STATE.md/ROADMAP.md excluded)._

## Files Created/Modified

- `kicad_lib_manager/main_window.py` - `CHECKOUT_CONFIG_BASE` seam; `_checkout_banner`/`_checkout_label` built in `_build_ui`; `_check_checkout(after)`; wired into `_on_generate` and `_on_import_installed`
- `kicad_lib_manager/widgets/import_result.py` - `_HINT_ROWS` tuple (`generate_hint`, `checkout_hint`); `checkout_hint` row built and hidden the same way as `generate_hint`; `set_status` docstring updated
- `kicad_lib_manager/widgets/import_dialog.py` - `set_post_install_status` docstring updated to name `checkout_hint`
- `kicad_lib_manager/widgets/help_dialog.py` - one sentence in `HELP_PAGES["generating"]`'s "What happens" list and one paragraph in `HELP_PAGES["importing"]`'s "Install and result" section
- `tests/test_checkout_warning.py` (new) - own fixture, 6 behavior tests covering both tasks
- `tests/test_help_dialog.py` - `test_help_mentions_wrong_checkout`
- `tests/test_main_window.py` - `make_window` fixture patches the new `CHECKOUT_CONFIG_BASE` seam to its existing synthetic `config_base` (deviation, see below)
- `tests/test_main_window_import.py` - same fixture patch (deviation, see below)

## Decisions Made

- `_check_checkout(after)` is one shared method for both callers. It always runs the compare and logs the single WARNING; the `after` parameter only decides whether the persistent banner is shown/hidden (`"generate"`) versus leaving the caller to render its own Result-view text (`"install"`), since Generate Tables and Install Part present the warning in different places in the UI.
- The banner reuses the exact `QFrame`/`AMBER_TINT`/2px-left-border/dismiss-`QToolButton` shape already established by `import_dialog.py`'s `failureBanner`, so the D-26 notice reads as the same visual language rather than a new one-off pattern.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Patched the new `CHECKOUT_CONFIG_BASE` seam into two pre-existing test fixtures not in this plan's `files_modified`**
- **Found during:** Task 2 GREEN step, running the plan's own `<verification>` command
- **Issue:** `tests/test_main_window.py` and `tests/test_main_window_import.py` both patch `main_window.REPO_ROOT` to a tmp repo but never touched a `CHECKOUT_CONFIG_BASE` seam (it didn't exist before this plan). With the new `_check_checkout` calls wired into `_on_generate`/`_on_import_installed`, those tests started reading the real `%APPDATA%` KiCad config on the executing workstation — which has `KICAD_LIB_GITHUB` set to a different checkout than the tests' tmp repos, so 3 previously-passing tests in `test_main_window_import.py` broke (`test_status_rows_new_library_settle`, `test_status_rows_existing_library_hint`, `test_status_rows_skipped_after_dialog_closed`), and the whole suite became workstation-dependent, which the project's own test-isolation convention (TEST-01, CLAUDE.md) forbids.
- **Fix:** Added `monkeypatch.setattr(main_window, "CHECKOUT_CONFIG_BASE", config_base)` to both fixtures' existing `config_base` tmp directory (already used for the path-variable sync and already carrying no `KICAD_LIB_GITHUB`), so `checkout_mismatch` always reads a synthetic, `None`-valued config there — zero behavior change for any existing test, and no real-environment read.
- **Files modified:** `tests/test_main_window.py`, `tests/test_main_window_import.py`
- **Verification:** `tests/test_main_window_import.py` and `tests/test_main_window.py` both pass in full after the patch; the plan's full `<verification>` command (232 tests) passes
- **Committed in:** `c000f52` (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 blocking test-isolation fix)
**Impact on plan:** Necessary to keep the test suite workstation-independent per the project's own TEST-01 convention; no scope creep in production behavior.

## TDD Gate Compliance

| Task | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| 2 (checkout_hint row, `_on_import_installed` wiring, help sentences) | ✓ `242bb36` (2/3 new tests failing for the right reason: `test_install_warns_in_result_view` — empty `status_text("checkout_hint")`; `test_help_mentions_wrong_checkout` — neither help page mentions the warning yet. `test_install_without_variable_shows_no_hint` already passed, correctly, since there is nothing to hide before or after GREEN) | ✓ `c000f52` (all 3 new tests pass; full 232-test `<verification>` command passes) | - (no refactor needed) | Pass |

Note: this plan's frontmatter carries `type: execute`, not `type: tdd`, so the machine-validated RED-evidence gate (`gsd_run check tdd-red-evidence`) and `workflow.tdd_mode` plan-level enforcement were not active (`workflow.tdd_mode` is absent from `.planning/config.json`, consistent with plans 13-02 and 13-07's own notes). The RED → GREEN discipline above was followed in full for the `tdd="true"` task per the executor's per-task instruction, including reverting the GREEN-step production edits before writing the RED tests so the failure was genuine.

## Issues Encountered

None beyond the test-isolation deviation documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- D-26 is now visible and non-blocking at both of this plan's write sites (Generate Tables, Install Part); plan 13-16's migration Run refusal is a separate blocking use of the same `checkout_mismatch` and is unaffected by this plan.
- The full plan-level `<verification>` command passed (232 tests: `test_checkout_warning.py`, `test_checkout_check.py`, `test_main_window.py`, `test_main_window_import.py`, `test_main_window_chooser.py`, `test_help_dialog.py`, `test_plain_names.py`). A broader regression check (`test_layering.py` plus the same GUI test files, 85 tests) also passed; not required by this plan's own done-criteria and not blocking.
- `requirements.ready-ids` for TBL-01 and MIG-04: 0/2 ready (both blocked by sibling plans in this phase that have no SUMMARY yet) — `REQUIREMENTS.md` correctly left unmarked.
- No blockers for the next plan in this phase.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- FOUND: tests/test_checkout_warning.py
- FOUND: kicad_lib_manager/main_window.py (modified)
- FOUND: kicad_lib_manager/widgets/import_result.py (modified)
- FOUND: kicad_lib_manager/widgets/help_dialog.py (modified)
- FOUND commit: e34f5ac (Task 1)
- FOUND commit: 242bb36 (Task 2 RED)
- FOUND commit: c000f52 (Task 2 GREEN)
- Plan-level `<verification>` command (232 tests) re-run: PASSED
- Both tasks' acceptance-criteria greps: PASSED
- `requirements.ready-ids` for TBL-01, MIG-04: 0/2 ready — REQUIREMENTS.md correctly left unmarked
