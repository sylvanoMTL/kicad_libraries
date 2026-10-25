---
phase: 05-import-ui-and-post-install
plan: 01
subsystem: ui
tags: [pyside6, qthread, import-dialog, preview, post-install-rescan]

requires:
  - phase: 03-intake
    provides: open_package, detect_candidate, suggest_library, Package ownership contract
  - phase: 04-install
    provides: build_plan, apply_plan, InstallPlan, InstallResult
provides:
  - Qt-free preview rows (Files section) derived from InstallPlan.ops
  - TaskWorker, ImportCore, OpenOutcome, ImportDialog (Start/Edit/Result pages, rebuild coordinator, install worker)
  - File > Import Part... (Ctrl+I) and a quiet post-install rescan that checks the installed library
affects: [05-02, 05-03, 05-04, 05-05, 05-06, 05-07, 05-08, 05-09, 05-10, 05-11, phase-06-commit]

plan_head_before: 543f75e8d932da33cca1d1a4a942e1e9fa127343
plan_head_after: ce4c467655d66848e6fc20fa4c2472c0c59626e2

actuals:
  tokens: 38000
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Serialised, superseding rebuild: one build_plan worker at a time, generation counter, latest request wins"
    - "Dialog owns the Package; waits for open/build workers before close(); refuses to close while installing"
    - "Single scan funnel _start_scan(show_progress=...) with a pending post-install request"

key-files:
  created:
    - kicad_lib_manager/importer/preview.py
    - kicad_lib_manager/widgets/preview_tree.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_import_dialog.py
    - tests/test_main_window_import.py
  modified:
    - kicad_lib_manager/main_window.py
    - tests/test_importer_layering.py

key-decisions:
  - "Finished TaskWorker objects are never deleteLater'd: deleting a finished install worker crashed pytest-qt's event processing with an access violation, so workers stay children of the dialog until it is destroyed"
  - "apply_plan is called with self._plan (the rendered object); a build result is not accepted while an install runs, so the object cannot change underneath the worker"
  - "editingFinished on the library combo rebuilds only when the typed name changed; textActivated always rebuilds"
  - "A pending post-install request that arrives while a scan runs is started from _finish_scan, still through _start_scan(show_progress=False)"

patterns-established:
  - "ImportCore dataclass of core callables, replaced field by field with dataclasses.replace in tests"
  - "Gated fakes (threading.Event) to hold a worker open for supersede, close-order and close-refusal tests"

requirements-completed: [PREV-07, POST-01]

coverage:
  - id: D1
    description: "File > Import Part... opens a window-modal dialog; open/detect/build/apply run on worker threads"
    requirement: PREV-07
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_core_calls_run_off_the_gui_thread"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_import_dialog_opens_window_modal"
        status: pass
    human_judgment: false
  - id: D2
    description: "UL sample imported end to end: Files preview lists the plan's three writes, Install applies that exact plan, Result page shows the banner"
    requirement: PREV-07
    verification:
      - kind: e2e
        ref: "tests/test_import_dialog.py#test_tracer_ul_import_end_to_end"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_install_uses_latest_plan_object"
        status: pass
    human_judgment: false
  - id: D3
    description: "Stale rebuilds are discarded, failures keep the previous tree, nothing is written before Install, close waits for workers and is refused while installing"
    requirement: PREV-07
    verification:
      - kind: unit
        ref: "tests/test_import_dialog.py#test_supersede_discards_stale_result"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_tracer_nothing_written_before_install"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_close_waits_and_closes_package"
        status: pass
      - kind: unit
        ref: "tests/test_import_dialog.py#test_close_refused_while_installing"
        status: pass
    human_judgment: false
  - id: D4
    description: "After install the main window rescans once, quietly, and checks the installed library without disturbing other selections"
    requirement: POST-01
    verification:
      - kind: unit
        ref: "tests/test_main_window_import.py#test_post_install_select_checks_installed_library"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_post_install_select_waits_for_running_scan"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_post_install_select_unchecks_peer"
        status: pass
      - kind: unit
        ref: "tests/test_main_window_import.py#test_post_install_select_missing_library"
        status: pass
    human_judgment: false
  - id: D5
    description: "Look and feel of the dialog (layout, spacing, copy) matches the UI-SPEC"
    verification: []
    human_judgment: true
    rationale: "Only the tracer subset of the UI-SPEC is built; no test judges visual layout and later plans widen the dialog"

duration: 85min
completed: 2026-10-22
status: complete
---

# Phase 5 Plan 01: Import Part Tracer Summary

**Import Part dialog tracer: the UL sample is opened, planned, previewed and installed through TaskWorker threads, with a generation-counted rebuild coordinator so Install always applies the exact plan that was rendered, and a quiet post-install rescan that checks the installed library.**

## Performance

- **Duration:** about 85 min
- **Completed:** 2026-10-22
- **Tasks:** 2 (1 tracer, 1 auto), 4 commits (RED and GREEN for each)
- **Files modified:** 7 (5 created, 2 modified)

## Accomplishments

- `importer/preview.py` (Qt-free): `PreviewRow`, `PreviewSection` (`title`), `FileCounts`, `preview_sections`, `file_counts`. The Files section lists `plan.ops` in order, `+` for new files and mkdirs, `~` for modified ones. Registered in the layering guard together with the forward registrations for `importer.form`, `importer.content` and `importer.downloads`.
- `widgets/preview_tree.py`: `PreviewTree.render(sections)` with bold expanded section headers and plain-text rows.
- `widgets/import_dialog.py`: `TaskWorker` (signals `progress`, `result`, `failed`, never `finished`), `ImportCore`, `OpenOutcome` and `ImportDialog` with Start, Edit and Result pages, the rebuild coordinator (`_gen`, `_building`, `_queued`, `_plan`, `_plan_gen`), Install gating, an install worker, and WR-04 close semantics.
- `main_window.py`: `Import Part...` (Ctrl+I) first in the File menu followed by a separator, `_open_import`, `_on_import_installed`, `_apply_post_install_selection`, and `_start_scan(show_progress=...)` as the single scan funnel. `Import Part...` joins the `_set_scan_running` controls.

## TDD Gate Compliance

| Task | RED commit | GREEN commit |
|------|-----------|--------------|
| 1 (tracer) | a424730 `test(05-01)` | b5c5bca `feat(05-01)` |
| 2 | 91f0c39 `test(05-01)` | ce4c467 `feat(05-01)` |

RED evidence: Task 1's RED run failed at collection with `ModuleNotFoundError: kicad_lib_manager.importer.preview`, exactly the "module missing" RED the plan specifies; a collection error is a load failure rather than an assertion failure, so it is weaker than a classifier-grade RED (semantic assessment: acceptable for a greenfield module, the first behavioural assertions ran in GREEN). Task 2's RED run failed 7 of 7 tests on the missing action/methods (assertion and `AttributeError` on `_on_import_installed`, `_act_import`).

The tracer gate (`type="tracer"`): `<verify>` re-run end to end after the Task 1 commit passed (34 passed, no skips in the Custom-enabled mirror), so expansion to Task 2 went ahead.

## Task Commits

1. Task 1 RED: `a424730` test(05-01): add failing tests for the import dialog tracer
2. Task 1 GREEN: `b5c5bca` feat(05-01): import dialog tracer with real plan preview and install
3. Task 2 RED: `91f0c39` test(05-01): add failing tests for the import menu entry and post-install selection
4. Task 2 GREEN: `ce4c467` feat(05-01): File > Import Part entry and quiet post-install rescan

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] deleteLater on a finished install worker crashed the process**
- **Found during:** Task 1 (GREEN)
- **Issue:** Reaping each worker with `worker.deleteLater()` from its `finished` slot aborted pytest (access violation in pytest-qt's event processing) after an install; build workers were fine, the timing made it intermittent.
- **Fix:** Workers are no longer deleted early. `_reap` only waits and releases the result; the QThread objects stay children of the dialog until it is destroyed. A full main-window flow with the dialog's own `deleteLater` ran clean repeatedly.
- **Files modified:** kicad_lib_manager/widgets/import_dialog.py
- **Commit:** b5c5bca

**2. [Rule 1 - Bug] Open worker's package could be closed twice**
- **Found during:** Task 1 (GREEN), `test_close_waits_and_closes_package` saw two `close()` calls
- **Issue:** `_shutdown` also closed the package held by the still-referenced open outcome after the dialog had already adopted it.
- **Fix:** `_on_opened` clears the worker's retained value once the package is adopted, so `_shutdown` only closes a package from an open that finished while closing.
- **Commit:** b5c5bca

**3. [Rule 1 - Bug] Test raced the worker thread**
- **Found during:** Task 2 (GREEN)
- **Issue:** `test_post_install_select_checks_installed_library` asserted the scan-call count right after `_on_import_installed`, but the fake scan records its call on the worker thread.
- **Fix:** assert `w._worker is not None` immediately and the call count after the scan ends.
- **Files modified:** tests/test_main_window_import.py
- **Commit:** ce4c467

**4. [Rule 2 - Missing critical] Guard against accepting a build result during an install**
- **Issue:** the literal `core.apply_plan(self._plan, ...)` required by the plan's key link reads `self._plan` on the worker thread; a late build result must not replace it.
- **Fix:** `_on_build_result` does not accept a plan while `is_installing()`.
- **Commit:** b5c5bca

Total deviations: 4 auto-fixed (3 bugs, 1 missing safety guard). Impact: none on scope.

## Verification

- Custom-enabled mirror (worktree plus a copy of the main checkout's `Custom/`, because the submodule is not initialised in worktrees): `tests/test_import_dialog.py tests/test_main_window_import.py tests/test_main_window.py tests/test_importer_layering.py tests/test_layering.py` passes with no SKIPPED line, repeated 3 times for stability.
- In the bare worktree: 51 passed, 11 skipped. All 11 skips are `tests/test_import_dialog.py` tests that need the `custom_copy` fixture (Custom submodule not checked out). `tests/test_main_window_import.py` needs no submodule and passes.
- Full suite in the mirror: 1339 passed, 5 skipped, 38 failed. The 38 failures are mirror artefacts, not regressions: `tests/test_fixtures.py` (28) and others call `git` in a directory that is not a repository, or depend on the real Wurth submodule and kicad-cli/format dates. None of the failing tests touch files changed by this plan. The orchestrator should confirm with the full suite on the merged tree.
- Acceptance greps: `finished = Signal` count 0 in `import_dialog.py`; no `PySide6` in `preview.py`; `_start_scan(show_progress=False)` appears twice in `main_window.py`.

## Known Limitations (by plan design, not stubs)

- The Start page offers only Browse zip... and the issue text; the full start step (Downloads offer, Browse folder, Change...) is plan 05-05.
- `ImportDialog.result` shadows `QDialog.result()` on the instance, as the plan requires; do not call `result()` as a method.
- Install progress shows step text in the strip only; the bar and failure banner are plan 05-11.
- No stubs found in the created files.

## Threat Flags

None. The dialog reads user-chosen packages through the existing Phase 3 caps and writes only via `apply_plan` after Install (T-05-01 proven by `test_tracer_nothing_written_before_install`).

## Next Phase Readiness

Plans 05-04 onwards can widen `preview_sections` (the other sections), `_snapshot_options` (picker and fields) and the Start page without changing the thread or ownership architecture. Requirements PREV-07 and POST-01 are shared with later plans, so they were not marked complete in REQUIREMENTS.md here (the orchestrator owns that after the wave).

## Self-Check: PASSED

- Files exist: preview.py, preview_tree.py, import_dialog.py, test_import_dialog.py, test_main_window_import.py (all FOUND); main_window.py and test_importer_layering.py modified.
- Commits a424730, b5c5bca, 91f0c39, ce4c467 are ancestors of HEAD.
