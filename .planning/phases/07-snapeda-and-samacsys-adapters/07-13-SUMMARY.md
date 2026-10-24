---
phase: 07-snapeda-and-samacsys-adapters
plan: 13
subsystem: ui
tags: [pyside6, import-dialog, attach-models, gap-closure, 3d-model, tdd]

requires:
  - phase: 07-snapeda-and-samacsys-adapters
    provides: "07-10 tracer: RejectedModel, _show_rejection, REMOVE_MODEL_TEXT, FormStatus.model_error"
provides:
  - "attach_models rejects a source with any failing model file as a whole (intake.no_model_in_source or intake.unusable_model_in_source)"
  - "A model read failure of the current session is held as a rejected source and blocks Install; a stale failure is only logged"
  - "A usable attach clears a held rejection; an INFO duplicate keeps it"
  - "Importing Parts help names the red error, the blocked Install Part and the Remove button"
affects: [07-UAT test 5, verify-work, help page]

actuals:
  tokens: 9000
  tasks: 2
  commits: 3
plan_head_before: 89452e881d066a1531193e9eb44b3a04b89ca67f
plan_head_after: 958175cd83394ab6b4329b9e21ee62f18ede439c

tech-stack:
  added: []
  patterns:
    - "Session and source name bound into a worker's failed-signal lambda so a late failure can be told stale (T-07-36)"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/adapters/base.py
    - kicad_lib_manager/widgets/import_dialog.py
    - kicad_lib_manager/widgets/help_dialog.py
    - tests/test_model_attach.py
    - tests/test_import_dialog.py
    - tests/test_help_dialog.py
    - .planning/phases/07-snapeda-and-samacsys-adapters/07-08-PLAN.md
    - .planning/phases/07-snapeda-and-samacsys-adapters/07-UAT.md

key-decisions:
  - "A bad file beside a duplicate is the partly bad case (the duplicate passes the magic check): ERROR intake.unusable_model_in_source, no INFO intake.model_already_present"
  - "The Error reason for a read failure carries the logged Issue text unchanged, so it reads 'Import step failed: RuntimeError: disk on fire' (the worker prefixes the exception class)"
  - "A held rejection is replaced by a newer rejection, kept by an INFO duplicate, and cleared only by a usable attach, Remove, Change..., a new open or close"

patterns-established:
  - "Whole-source rejection: attach_models returns (None, [*WARNINGs, one ERROR]) and attaches nothing"

requirements-completed: [FMT2-02, INTK-03]

coverage:
  - id: D1
    description: "A zip with any unusable model file is rejected as a whole; nothing from it is attached, with the per-case ERROR codes"
    requirement: "FMT2-02"
    verification:
      - kind: unit
        ref: "tests/test_model_attach.py#test_attach_rejects_partly_bad_zip"
        status: pass
      - kind: unit
        ref: "tests/test_model_attach.py#test_attach_rejects_bad_beside_duplicate"
        status: pass
      - kind: unit
        ref: "tests/test_model_attach.py#test_attach_rejects_all_bad_zip"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_partly_bad_zip_rejected"
        status: pass
    human_judgment: false
  - id: D2
    description: "A failed model read blocks Install in red until Remove or a usable attach; a stale failure never blocks"
    requirement: "INTK-03"
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_worker_failure_logged"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_stale_failure_does_not_block"
        status: pass
    human_judgment: false
  - id: D3
    description: "A usable attach clears the rejection; duplicates keep it; Change... and a new open reset it; Remove and Add are disabled while reading"
    requirement: "INTK-03"
    verification:
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_success_clears_rejection"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_duplicate_keeps_rejection"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_rejection_reset_by_change"
        status: pass
      - kind: integration
        ref: "tests/test_import_dialog.py#test_add_model_remove_disabled_while_reading"
        status: pass
    human_judgment: false
  - id: D4
    description: "The help page, the superseded 07-08 must-have and UAT test 5 describe the blocking error and Remove"
    verification:
      - kind: unit
        ref: "tests/test_help_dialog.py#test_help_import_page_describes_rejected_model"
        status: pass
    human_judgment: false
  - id: D5
    description: "UAT test 5 end to end in the real dialog (red note, blocked Install, Remove recovers, mixed zip attaches nothing)"
    verification: []
    human_judgment: true
    rationale: "Colour legibility and the feel of the recovery flow are a visual judgment; /gsd-verify-work owns UAT test 5"

duration: 35min
completed: 2026-10-24
status: complete
---

# Phase 7 Plan 13: Whole-source model rejection and blocking read failures Summary

**A model source with any unusable file is rejected whole by attach_models, a failed model read is held as a red blocking rejection for its own session only, a usable attach clears it, and the help page, 07-08 and UAT test 5 describe it.**

## Performance

- **Duration:** about 35 min
- **Started:** 2026-10-24T11:20Z (approx.)
- **Completed:** 2026-10-24T11:55Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- `attach_models` rejects a partly bad source whole: `intake.no_model_in_source` (text unchanged) when no file passed the magic check, new `intake.unusable_model_in_source` (names the source and the first bad file, plus "and N more") when some did, a bad file beside a duplicate included; the WARNINGs stay, nothing is attached, no local folder is named.
- `_on_model_failed` takes the session and file name bound at start: a current-session failure becomes a `RejectedModel` (red note, Remove, "Error: ..." reason, Install blocked); a stale one is only logged and leaves the next package untouched.
- The success branch of `_on_model_attached` clears a held rejection; the INFO-only duplicate branch keeps the red rejection note, Remove and the Error reason instead of replacing the note with the muted one.
- Help page Items section explains the red error, blocked **Install Part**, and **Remove** / **Add 3D model...** using `REMOVE_MODEL_TEXT` and `ADD_MODEL_TEXT`; 07-08's must-have and amber wording and UAT test 5's expected line are rewritten.

## Task Commits

1. **Task 1 (TDD): read failures, partly bad zips, clears and resets**
   - RED: `57bf46d` (test)
   - GREEN: `b520827` (feat)
   - REFACTOR: none needed
2. **Task 2: help page and superseded 07-08 / UAT test 5 text** - `958175c` (docs)

**Plan metadata:** committed after this file (docs: complete plan)

## TDD RED evidence

Target run before implementation (pytest, 11 target tests): 8 failed, 3 passed. Each failure was on the planned assertion:
- `test_attach_rejects_partly_bad_zip`: `attached is None` failed (the good file was attached).
- `test_attach_rejects_bad_beside_duplicate`: ERROR codes were `['intake.no_model_in_source']`, not `['intake.unusable_model_in_source']`.
- `test_add_model_worker_failure_logged`: the "Error: ..." strip reason was missing (`{}`).
- `test_add_model_partly_bad_zip_rejected`: `dialog._candidate is candidate` failed (a model was attached).
- `test_add_model_success_clears_rejection`: `_model_rejection` was still a `RejectedModel`.
- `test_add_model_duplicate_keeps_rejection`: the note read "same.stp is already listed as same.stp" instead of the rejection text.
- `test_add_model_stale_failure_does_not_block`: the stale failure's note was shown on the new package (`isHidden()` False).
- `test_add_model_remove_disabled_while_reading`: the rejection was not cleared by the later usable attach.

The 3 that passed (`test_attach_rejects_all_bad_zip`, `test_attach_rejects_wrong_magic`, `test_add_model_rejection_reset_by_change`) pin behaviour that already held (all-bad zip wording, bare bad file, 07-10's `_clear_items` reset) and guard it against regression. The pytest report is not one of the formats `gsd_run check tdd-red-evidence` supports and the plan is `type: execute`, so the semantic assessment above is the RED evidence.

## Files Created/Modified
- `kicad_lib_manager/importer/adapters/base.py` - whole-source rejection in `attach_models`, docstring rule rewritten
- `kicad_lib_manager/widgets/import_dialog.py` - `_start_model_attach` binds session and name, `_on_model_failed(worker, text, session, source)`, clear/keep rules in `_on_model_attached`
- `kicad_lib_manager/widgets/help_dialog.py` - Items sentence, imports `REMOVE_MODEL_TEXT`
- `tests/test_model_attach.py` - replaced `test_attach_keeps_good_drops_bad`, added bad-beside-duplicate and all-bad-zip tests
- `tests/test_import_dialog.py` - rewrote the worker-failure test, added six dialog tests
- `tests/test_help_dialog.py` - `test_help_import_page_describes_rejected_model`
- `.planning/phases/07-snapeda-and-samacsys-adapters/07-08-PLAN.md`, `07-UAT.md` - superseded wording (UAT test 5 `expected:` only)

## Decisions Made
- See `key-decisions` above. The plan's design choices were followed as written.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan text] Worker failure reason includes the exception class**
- **Found during:** Task 1 GREEN run
- **Issue:** The plan's behavior line for `test_add_model_worker_failure_logged` expects the strip link "Error: Import step failed: disk on fire", but `TaskWorker` reports "RuntimeError: disk on fire", so the Issue text (and the reason) is "Import step failed: RuntimeError: disk on fire".
- **Fix:** The test asserts the reason equals `f"Error: {logged[-1][0].text}"` and pins the full text; product code unchanged (the rejection carries the logged Issue text, as the plan says).
- **Files modified:** tests/test_import_dialog.py
- **Committed in:** b520827

---

**Total deviations:** 1 (test expectation, no product impact)
**Impact on plan:** None on scope.

## Issues Encountered
- The working tree is CRLF (autocrlf); edits were made with a CRLF-preserving patch helper so diffs stay clean.
- The plan's `must_haves` frontmatter says `_on_model_failed` pattern `s=session, n=path.name`; the lambda uses exactly that binding.
- Verification: the plan's targeted commands pass (11 passed; 34 passed, 1 skipped for symlinks; 23 passed for `-k add_model`). The plan-level run over `test_import_form`, `test_model_attach`, `test_model_source`, `test_help_dialog`, `test_import_dialog` (minus the two Custom-reading baseline ids) gave 229 passed, 10 skipped (Custom submodule absent, symlink privilege). The full-suite phase gate was not run in this worktree; the orchestrator owns it.

## Known Stubs
None.

## Threat Flags
None. T-07-35 (whole-source rejection, no folder in the new text), T-07-36 (session-bound failure, reset by `_clear_items`) and T-07-40 (read failure routed into `model_error`) are mitigated and tested.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
G-07-5 is closed in code and docs; `/gsd-verify-work` owns UAT test 5's result (the plan's `<human-check>`: pick an empty or renamed .step, a .txt-only zip, then a mixed zip; expect a red note, blocked Install, Remove recovers).

---
*Phase: 07-snapeda-and-samacsys-adapters*
*Completed: 2026-10-24*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/importer/adapters/base.py, kicad_lib_manager/widgets/import_dialog.py, kicad_lib_manager/widgets/help_dialog.py, tests/test_model_attach.py, tests/test_import_dialog.py, tests/test_help_dialog.py
- FOUND commits: 57bf46d, b520827, 958175c
