---
phase: 07-snapeda-and-samacsys-adapters
verified: 2026-10-24T14:00:00Z
status: human_needed
score: 7/8 must-haves verified (4/4 roadmap success criteria; gap truths G-07-2, G-07-5, G-07-7 verified; G-07-8 click hint verified, tooltip colour behavior-unverified)
covered_files:
  - .gitignore
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-01-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-01-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-02-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-02-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-03-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-03-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-04-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-04-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-05-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-05-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-06-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-06-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-07-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-07-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-08-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-08-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-09-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-09-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-10-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-10-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-11-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-11-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-12-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-12-SUMMARY.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-13-PLAN.md
  - .planning/phases/07-snapeda-and-samacsys-adapters/07-13-SUMMARY.md
  - kicad_lib_manager/importer/adapters/base.py
  - kicad_lib_manager/importer/adapters/samacsys.py
  - kicad_lib_manager/importer/adapters/snapeda.py
  - kicad_lib_manager/importer/detect.py
  - kicad_lib_manager/importer/fieldrules.py
  - kicad_lib_manager/importer/form.py
  - kicad_lib_manager/importer/package.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/suggest.py
  - kicad_lib_manager/importer/verify.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - kicad_lib_manager/widgets/preview_tree.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_import_form.py
  - tests/test_model_attach.py
  - tests/test_model_source.py
  - tests/test_preview_tree.py
  - tests/test_real_vendor_samples.py
  - tests/test_vendorfixtures.py
  - tests/vendorfixtures.py
covered_digest: "v3:sha256:ec42b03ab72e9d5250922cac73f3eabec22f48c3eae7deb1a2324421c02db9bb"
behavior_unverified: 1
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 4/4 roadmap criteria (plans 07-01..07-09)
  gaps_closed:
    - "G-07-2: separately downloaded SnapEDA 3D model can be added (live re-test: UAT tests 3, 4, 6 pass)"
    - "G-07-5 (code and tests): an unusable 3D model source is a red ERROR that blocks Install, with Remove / Add 3D model... recovery"
    - "G-07-7 (code and tests): preview columns are user-resizable and fit the viewport at 900 and 1400 px"
    - "G-07-8 (code and tests, text and scoping only): strip tooltip carries the click hint, rich text, scoped stylesheet"
  gaps_remaining: []
  regressions: []
behavior_unverified_items:
  - truth: "The strip tooltip is drawn in the normal tooltip colours and not on the strip's AMBER_TINT (G-07-8)"
    test: "Hover a blocking reason in the status strip on the live display"
    expected: "Tooltip in the platform's normal tooltip colours, listing the reasons and ending with the click hint"
    why_human: "Plan 07-12 makes this manual-only: showing a QToolTip and sampling pixels is display and DPI dependent. Tests assert only that the strip stylesheet is one QLabel#installStrip rule."
human_verification:
  - test: "UAT test 5, live GUI. Run .\\env\\Scripts\\python.exe kicad_lib_manager.py, open Import, load downloaded_examples/USB4145-03-0170-C_REVA2.zip (use a part not already in the live Custom/, or settle its conflicts). Click Add 3D model... and pick (a) a zip holding only a .txt, (b) an empty or renamed text file saved as .stp/.step, (c) a zip holding one good .stp and one renamed non-STEP file."
    expected: "Each shows a red plain-text error note under the model row and a log line. Nothing from the source is attached, even the good file of the mixed zip. Install Part is disabled with an 'Error: ...' reason in the strip, clicking it focuses the Remove button. Remove clears the note and Install returns to what the preview says. Add 3D model... still works and typed edits and the preview are untouched."
    why_human: "07-UAT.md test 5 is still recorded as 'issue'. The red colour on the real theme, the strip-link focus jump and the feel of the recovery flow cannot be judged from offscreen pytest."
  - test: "UAT test 7, live GUI, real display. Open Import with downloaded_examples/USB4145-03-0170-C_REVA2.zip. Drag the Item | Detail divider, narrow and widen the Import part window, type in Value."
    expected: "The divider drags, the long Field changes rows elide inside Detail instead of running past the right edge, both columns stay readable at every window width, and the dragged width survives the rebuild from typing."
    why_human: "Offscreen font metrics and DPI differ from the owner's display (the UAT report was a 734 px Detail on Windows). 07-UI-REVIEW.md also claims Detail wraps rather than elides; my offscreen probe showed single-line rows, so the real display decides."
  - test: "UAT test 8, live GUI. With a blocking reason showing (for example empty the Value field), hover the reason in the status strip, then click it."
    expected: "A tooltip in normal tooltip colours (not the strip's amber) lists the reasons and ends with 'Click a reason to jump to the control that fixes it. A reason about the whole plan jumps to the preview.' Clicking the reason focuses the control that fixes it."
    why_human: "Tooltip colour is manual-only by design (07-12 must-have). G-07-8 must not be marked resolved until this passes."
---

# Phase 7: SnapEDA and SamacSys Adapters Verification Report

**Phase Goal:** SnapEDA and SamacSys / Component Search Engine downloads import through the same flow as Ultra Librarian packages
**Verified:** 2026-10-24
**Status:** human_needed (all automated checks pass; UAT tests 5, 7 and 8 need the live GUI)
**Re-verification:** Yes. The earlier report covered plans 07-01..07-09 and is superseded. This report covers all 13 plans, including gap closure 07-10..07-13 for UAT gaps G-07-5, G-07-7 and G-07-8. Code was read and tests were re-run in this session, not copied from the SUMMARYs.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria, the contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Real SnapEDA zip recognised as SnapEDA; symbol, footprint and any model found; no model gives the "no 3D model found" warning | VERIFIED | `test_real_snapeda_recognised`, `test_real_snapeda_suggestion`, `test_real_snapeda_installs` PASSED against the real `USB4145-03-0170-C_REVA2.zip` (no skips, `-rA` run). UAT test 1 pass (live GUI). |
| 2 | Real SamacSys/CSE zip recognised; KiCad v6+ symbol, footprint and 3D model found; legacy `.lib`/`.dcm` ignored | VERIFIED | `test_real_samacsys_recognised`, `_suggestion`, `_installs` PASSED on the real `LIB_RS3-1212S_H3.zip`. UAT test 1 pass. No SamacSys source changed in the gap closure. |
| 3 | Each vendor sample installs into a copy of `Custom/` with the same `<Lib>:<FP>` link and `${CUSTOM_3DMODEL_DIR}` model path as UL; synthetic fixtures where redistribution forbids | VERIFIED | `test_real_vendor_installs_load_in_kicad[snapeda]` and `[samacsys]` (real kicad-cli) PASSED; synthetic fixtures in `tests/vendorfixtures.py`; `test_vendor_zips_stay_local` PASSED; `git ls-files downloaded_examples` lists only `ul_CSD85301Q2.zip`; `.gitignore:31` matches the SnapEDA model zip. |
| 4 | User can add a separately downloaded SnapEDA 3D model to the SnapEDA package in the import dialog; installs as `Custom/3DModels/<MPN>.<ext>` linked as `${CUSTOM_3DMODEL_DIR}/<file>`; every safety check applies; nothing written before the preview (G-07-2) | VERIFIED | `test_real_snapeda_model_zip_opens` and `test_real_snapeda_installs_with_separate_model` PASSED on the real files. Live re-test: UAT tests 3 (model zip), 4 (bare .stp) and 6 (preview and install link) all `pass`, which closes the live-GUI item the previous report left open. |

### Gap-closure truths (UAT gaps from 07-UAT.md, plans 07-07..07-13)

| # | Gap / Truth | Status | Evidence |
|---|-------------|--------|----------|
| 5 | G-07-2: separate model download attachable (07-07, 07-08, 07-09) | VERIFIED | Criterion 4 above. `open_model_source` / `attach_models` wired through `ImportCore` on a `TaskWorker` (`import_dialog.py:1675-1677`). UAT 3, 4, 6 pass live. |
| 6 | G-07-5: an unusable model source (bare file failing the magic check, zip with no model, partly bad zip, read failure) is a red ERROR that blocks Install and the model row offers Remove and Add 3D model... (07-10, 07-13) | VERIFIED in code and tests; live re-test pending (human item 1) | See the G-07-5 table below. |
| 7 | G-07-7: preview columns user-resizable and readable when the dialog is resized (07-11) | VERIFIED in code and tests; live re-test pending (human item 2) | `preview_tree.py:27-90`: all sections `Interactive`, `setStretchLastSection(True)`, `setMinimumSectionSize(MIN_COLUMN_WIDTH=120)`, one-time `_apply_initial_width` (ITEM_SHARE 0.55) from `showEvent`/`resizeEvent` only, `_clamp_item_width` from `resizeEvent` and `sectionResized(0)`; `render()` sets no width. Tests PASSED: `test_columns_interactive_and_detail_stretches`, `test_initial_item_width_once`, `test_divider_drag_moves_item_and_survives_render`, `test_item_clamped_when_tree_narrows`, `test_preview_columns_fit_at_900_and_1400`, `test_preview_column_drag_survives_rebuild`. 05-UI-SPEC.md lines 315 and 511 carry the amendment (grep). My offscreen probe (600 px tree, 330-char Field changes row): columns 329 + 269 within a 598 px viewport, rows single-line. |
| 8 | G-07-8a: the blocked strip tooltip lists every reason plus a click hint, always rich text, every reason escaped; strip stylesheet scoped to `QLabel#installStrip` (07-12) | VERIFIED | `import_dialog.py:88` `STRIP_LINK_HINT`, `:618` `setObjectName("installStrip")`, `:2255` scoped `_set_strip`, `:2312-2315` tooltip `<p>` + escaped reasons + `<i>` escaped hint. Tests PASSED: `test_strip_tooltip_says_reasons_are_links`, `test_strip_tooltip_single_reason_decodes_entities`, `test_strip_tooltip_style_scoped_to_strip`, `test_strip_caps_three_lines_with_tooltip`. 05-UI-SPEC.md lines 353 and 517 amended (grep). |
| 9 | G-07-8b: the tooltip is drawn in normal tooltip colours, not on the amber strip | PRESENT_BEHAVIOR_UNVERIFIED | The scoping rule exists and is asserted by text. No test shows a tooltip or samples a colour, by design (07-12). Routed to human item 3. G-07-8 stays open until UAT test 8 passes. |

**Score:** 7/8 truths verified (4 roadmap + G-07-5, G-07-7, G-07-8a, with G-07-2 counted under criterion 4); 1 present but behavior-unverified (G-07-8b).

### G-07-5 detail (07-10 tracer and 07-13 completion)

| Plan truth | Status | Evidence |
|-----------|--------|----------|
| Rejected source held by the dialog: first ERROR as plain-text red note (`theme.ERROR`), candidate and model row unchanged, package closed at once | VERIFIED | `_on_model_attached` candidate-None branch `import_dialog.py:1740-1756` closes the package, sets `RejectedModel`, `_show_rejection`; `_set_model_note` uses `ERROR` for the "error" tone and the label is `PlainText` (`:1440`, `:1469`). `test_add_model_rejection_blocks_install`, `test_add_model_refusal_shows_note`, `test_add_model_note_is_plain_text` PASSED. |
| Install blocked with `Error: <text>` reason, target `model`, focusing Remove | VERIFIED | `form.py:101` `FormStatus.model_error`, `:174-175` appended after plan errors; `import_dialog.py:2244` passes it; `:1457` `_reason_targets["model"] = remove`. `test_blocking_reasons_model_error` PASSED; the tracer asserts the strip link, disabled Install and focus on Remove. |
| Remove clears a rejected source only; Add 3D model... stays enabled | VERIFIED | `_on_remove_model` `:1710-1719` touches only `_model_rejection`; never the candidate or attached models. Disabled while busy (`:1708`). `test_add_model_remove_disabled_while_reading` PASSED. |
| Partly bad zip rejected whole: bare bad or all-bad -> `intake.no_model_in_source`, partly bad (bad beside good or duplicate) -> `intake.unusable_model_in_source`, nothing attached | VERIFIED | `adapters/base.py:392-403`. `test_attach_rejects_partly_bad_zip`, `_bad_beside_duplicate`, `_all_bad_zip`, `_wrong_magic`, and dialog `test_add_model_partly_bad_zip_rejected` PASSED. |
| Read failure held as a rejection for its own session only; stale failure only logged | VERIFIED | `_start_model_attach` binds `s=session, n=path.name` (`:1691-1693`); `_on_model_failed` `:1766-1779`. `test_add_model_worker_failure_logged`, `test_add_model_stale_failure_does_not_block` PASSED. |
| Usable attach clears a held rejection; INFO duplicate keeps it; Change.../new open/close reset it | VERIFIED | `:1748-1759`, `_clear_items` `:1294-1295`. `test_add_model_success_clears_rejection`, `_duplicate_keeps_rejection`, `_rejection_reset_by_change` PASSED. |
| Help page names the red error, blocked Install Part, Remove and Add 3D model... from shared constants; 07-08 must-have and UAT test 5 script reworded | VERIFIED | `help_dialog.py:224-231` uses `ADD_MODEL_TEXT` and `REMOVE_MODEL_TEXT`; `test_help_import_page_describes_rejected_model` PASSED; 07-08-PLAN.md must-have line 27 reads the new behaviour. |

### UAT gap status (07-UAT.md, 8 tests: 4 pass, 4 issue as recorded)

| Gap | UAT test | Recorded in 07-UAT.md | Code and tests | Live re-test |
|-----|----------|----------------------|----------------|--------------|
| G-07-2 separate SnapEDA model | 2 (re-tests 3, 4, 6 pass) | `resolved` | Closed (plans 07-07..07-09) | Done: tests 3, 4, 6 pass |
| G-07-5 unusable model must block Install | 5 | `failed` (not yet updated) | Closed (plans 07-10, 07-13) | Pending: UAT test 5 (human item 1) |
| G-07-7 preview columns resizable | 7 | `failed` (not yet updated) | Closed (plan 07-11) | Pending: UAT test 7 (human item 2) |
| G-07-8 strip reason tooltip | 8 | `failed` (not yet updated) | Text and scoping closed (plan 07-12); colour manual-only | Pending: UAT test 8 (human item 3) |

`07-UAT.md` still shows G-07-5, G-07-7 and G-07-8 as `status: failed` and the file `status: diagnosed`. That is bookkeeping: `/gsd-verify-work` should re-run tests 5, 7 and 8 and update it. Plan 07-12 forbids marking G-07-8 resolved before UAT test 8 passes.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kicad_lib_manager/importer/form.py` | `FormStatus.model_error`, `model` reason | VERIFIED | lines 101, 174-175; wired from `_form_status` |
| `kicad_lib_manager/importer/adapters/base.py` | whole-source rejection in `attach_models` | VERIFIED | lines 376-439 |
| `kicad_lib_manager/widgets/import_dialog.py` | `RejectedModel`, `REMOVE_MODEL_TEXT`, `STRIP_LINK_HINT`, scoped strip, rejection lifecycle | VERIFIED | grep hits at lines 76, 88, 253, 618, 1447-1457, 1696-1779, 2244-2255, 2312-2318 |
| `kicad_lib_manager/widgets/preview_tree.py` | Interactive Item, stretched Detail, one-time width, clamp | VERIFIED | whole file read |
| `kicad_lib_manager/widgets/help_dialog.py` | Items text from the two constants | VERIFIED | lines 7, 224-231 |
| Tests (20 named gap tests) | present in `test_import_dialog.py`, `test_import_form.py`, `test_model_attach.py`, `test_preview_tree.py`, `test_help_dialog.py` | VERIFIED | all 20 `def` names found and PASSED in the full run |
| `05-UI-SPEC.md` amendments | lines 315, 353, 511, 517 | VERIFIED | all four "amended 2026-10-24" markers present |
| Plans 07-01..07-09 artifacts | adapters, field rules, `open_model_source`, docs moves | VERIFIED | unchanged since the previous report except `base.py` (attach_models rule) and `import_dialog.py`; their suites pass in the full run |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `import_dialog._form_status` | `form.blocking_reasons` | `model_error=` | WIRED | `import_dialog.py:2244`, `form.py:174` |
| `blocking_reasons` Reason `model` | Remove button | `_reason_targets["model"]` | WIRED | `import_dialog.py:1457`; tracer test emits the link and asserts focus |
| `_start_model_attach` | `_on_model_failed` | lambda binding `s=session, n=path.name` | WIRED | `import_dialog.py:1691-1693` |
| `attach_models` ERROR | candidate-None branch of `_on_model_attached` | `errors[0]` -> `RejectedModel` | WIRED | `import_dialog.py:1743-1747` |
| `_set_strip` | `QLabel#installStrip` | f-string selector | WIRED | `:2255`, objectName `:618` |
| `_render_strip` | `STRIP_LINK_HINT` | tooltip build | WIRED | `:2312-2315` |
| `PreviewTree.showEvent` / `resizeEvent` | `_apply_initial_width`, `_clamp_item_width` | direct calls | WIRED | `preview_tree.py:83-90` |
| `help_dialog` | `REMOVE_MODEL_TEXT`, `ADD_MODEL_TEXT` | import | WIRED | `help_dialog.py:7` |
| `import_dialog` | `package.open_model_source`, `attach_models` | `core.` calls on a worker | WIRED | `import_dialog.py:1675-1677` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| Model note and Remove | `_model_rejection.issue` | first ERROR from `attach_models` / worker failure Issue | Yes: real `open_model_source` + `attach_models` in the tracer test | FLOWING |
| Strip reasons | `FormStatus.model_error` | `_model_rejection` | Yes: Install disabled and reason present in `strip_links` | FLOWING |
| Strip tooltip | `reasons` | `blocking_reasons` | Yes | FLOWING |
| Preview columns | `columnWidth(0/1)` | header state, set once from viewport width | Yes: measured in dialog tests at 900 and 1400 px | FLOWING |
| Installed model | `candidate.models` -> plan op | attached `ModelItem` | Yes: real two-file install test | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `env/Scripts/python.exe -m pytest -p no:cacheprovider -q -rf` (offscreen) | 1966 passed, 21 failed, 6 skipped in 355 s | PASS (failures equal the baseline, see below) |
| Failure set equals baseline | diff of my 21 FAILED ids vs the orchestrator's wave-4 id list, and vs the 07-RESEARCH.md Pitfall 8 list | IDENTICAL, 21 vs 21 | PASS |
| Real-sample and gap-area modules | `pytest -rA tests/test_real_vendor_samples.py tests/test_preview_tree.py tests/test_import_form.py tests/test_model_attach.py tests/test_help_dialog.py` | 74 passed; all 11 real-sample tests PASSED, none skipped | PASS |
| Skips | `-rs` | 6 skipped: UAT scratch env var, 2 symlink-privilege (WinError 1314), 3 Wurth submodule absent. None is a gap-closure test; the symlink branch is also covered through the reparse-point test | PASS |
| Preview columns offscreen | scratch probe of a 600 px `PreviewTree` with a 330-char Detail | cols 329/269, viewport 598, row height equals a short row's (single line, elided) | PASS |
| Stale model result after Change... | scratch test: gate a model read, Change..., reopen UL zip, release the gate | strip `'Updating preview...'`, Install disabled after the worker ended | FAIL (advisory, see Anti-Patterns) |

The 21 failures are all in `test_commit_plan`, `test_import_dialog` (2), `test_import_preview`, `test_install_apply` (7), `test_install_e2e` (5), `test_install_plan` (4) and `test_kicad_cli`. They come from the dirty live `Custom/` tree (`CSD85301Q2.stp` already installed by the owner's UAT) and from real kicad-cli KiCad 10 writing format 20251024 against tests that expect 20241209. Per the orchestrator, all 21 were re-run on the pre-gap base and fail there too; the id set equals the 07-RESEARCH.md Pitfall 8 baseline, so there is no new failure and no baseline id that now passes.

### Probe Execution

No `probe-*.sh` scripts are declared or present. Skipped.

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|--------------|-------------|--------|----------|
| INTK-03 | 07-01, 07-02, 07-03, 07-04, 07-06, 07-07, 07-08, 07-09, 07-10, 07-11, 07-12, 07-13 | SnapEDA zip recognised; symbol, footprint, any 3D model found; verified against a real download | SATISFIED | Criterion 1, real-sample tests PASSED, UAT 1 pass |
| INTK-04 | 07-03, 07-05, 07-06, 07-11 | SamacSys/CSE zip recognised; symbol, footprint, 3D model found; verified against a real download | SATISFIED | Criterion 2, real-sample tests PASSED, UAT 1 pass |
| FMT2-02 | 07-07, 07-08, 07-09, 07-10, 07-12, 07-13 | Separately downloaded 3D model added in the import dialog, checked like a package, copied as `<MPN>.<ext>`, linked as `${CUSTOM_3DMODEL_DIR}/<file>` | SATISFIED | Criterion 4, UAT 3, 4, 6 pass; refusal handling now blocking (G-07-5) |

All three IDs appear in PLAN frontmatter (07-10 `[FMT2-02, INTK-03]`, 07-11 `[INTK-03, INTK-04]`, 07-12 `[FMT2-02, INTK-03]`, 07-13 `[FMT2-02, INTK-03]`, earlier plans as before) and in REQUIREMENTS.md (v1 lines 34, 35, 40; traceability rows all "Phase 7"). No orphaned requirements. Bookkeeping: REQUIREMENTS.md still shows these three as `[ ]` and "Pending"; tick them when the phase completes (not a gap).

### Prohibitions (must_haves.prohibitions, all test-tier)

| Prohibition | Enforcement found | Status |
|-------------|-------------------|--------|
| Never stage, commit or copy any byte of `downloaded_examples/194150990-659-usb4145-03-0170-c.zip` (07-09) | `.gitignore:31` (git check-ignore), `git ls-files downloaded_examples` shows only the UL zip, `test_vendor_zips_stay_local` PASSED | RESOLVED |
| Earlier prohibitions (07-01..07-06: no real vendor bytes, no unseen field change, no edit of existing symbols, markers never on disk, no unmapped PartCategory) | Same tests as before, all in the passing set | RESOLVED |
| Untrusted file names and Issue texts never read as markup (T-07-30, T-07-34, T-07-39) | Note is `PlainText`; Remove tooltip is static; strip and tooltip `html.escape` every reason; tests above PASSED | RESOLVED |

No unverified prohibitions.

### Anti-Patterns Found

TBD/FIXME/XXX/TODO/HACK scan over `form.py`, `package.py`, `adapters/*.py`, `help_dialog.py`, `import_dialog.py`, `preview_tree.py`: no markers. No stubs; the new code is exercised by tests that drive the real dialog and real `open_model_source` / `attach_models`.

Advisory items (07-REVIEW.md plus my own check; none contradicts a must-have truth):

| Finding | Severity | Verified here | Impact |
|---------|----------|---------------|--------|
| Stale model result leaves Install on "Updating preview..." (old review WR-01, no longer listed in 07-REVIEW-DISPOSITION.md) | Warning | REPRODUCED again. Gate a model read, Change..., open the UL zip, release the gate: after the worker ends the strip reads "Updating preview..." and Install is disabled. Cause: the stale branch of `_on_model_attached` (`import_dialog.py:1732-1738`) calls `_update_install_state()` only when `outcome.session == self._session`, and `_end_model_worker` (`:1696-1699`) only re-syncs the Add and Remove buttons. The 07-13 fix covers the failure path (`_on_model_failed` always calls `_update_install_state`) but not this path. | Safe failure (nothing installs from an unfinished preview) and the next field edit rebuilds. Needs Change... plus a second open while a model read is still running. Fix: call `_update_install_state()` from `_end_model_worker` unless closing, plus a test. Recommend a small follow-up; I did not make it a blocker because no stated must-have asserts the unblock. |
| WR-01 (07-REVIEW) `test_tracer_ul_import_end_to_end` and `test_preview_sections_follow_plan_ops` read the live `Custom/` tree | Warning | Confirmed (both in the 21-id baseline) | Environmental, not a regression |
| WR-02 (07-REVIEW) vendor-derived text reaches rich-text-autodetecting tooltips (`preview_tree.py` `_row_item`, model combo `setToolTip`) | Warning | Confirmed by reading (`preview_tree.py:120-121`) | Pre-existing, low impact; inconsistent with the T-07-34 rule but not a gap-closure truth |
| IN-01 `RejectedModel.source` stored, never read by production code | Info | Confirmed (only construction sites at `:1746`, `:1777`) | Dead plumbing |
| IN-02 `sectionResized` connected before `_item_width_set` assigned; `setWordWrap(True)` | Info | Confirmed (`preview_tree.py:36`, `:44`, `:46`). Offscreen the rows stay single-line, but 07-UI-REVIEW.md reports wrapping on the Detail column | Real-display behaviour is a human item (UAT 7) |
| WR-03/WR-04, IN-03/IN-04 carried from earlier reviews (SamacSys other-CAD count wording, protected-name case, `_kicad_base`) | Warning/Info | All dispositions `open`, cosmetic | None |

### Human Verification Required

Three items, matching the frontmatter. All three need the live GUI.

#### 1. UAT test 5: refused model sources block Install, Remove recovers

**Test:** Run `.\env\Scripts\python.exe kicad_lib_manager.py`, open Import with `downloaded_examples/USB4145-03-0170-C_REVA2.zip` (a part not already in the live `Custom/`, or settle its conflicts first). Click **Add 3D model...** and pick a `.txt`-only zip, then an empty or renamed text file saved as `.stp`/`.step`, then a zip with one good `.stp` and one renamed non-STEP file.
**Expected:** A red plain-text note under the model row and a log line each time. Nothing from the source is attached, not even the good file of the mixed zip. Install Part is disabled with an "Error: ..." reason; clicking the reason focuses **Remove**; Remove clears it and Install returns to what the preview says; Add 3D model... still works; edits and preview unchanged.
**Why human:** The red on the real theme, focus jump and recovery feel are visual and interactive. The UAT file still records the original `issue`.

#### 2. UAT test 7: preview columns on the real display

**Test:** Open the same package, drag the Item | Detail divider, narrow and widen the Import part window, type in Value.
**Expected:** The divider drags; long Field changes rows elide in Detail (full text in the tooltip) and do not run past the edge; both columns stay readable; the dragged width survives the rebuild.
**Why human:** Real font metrics and DPI differ from offscreen, and the UI review disputes whether Detail wraps or elides.

#### 3. UAT test 8: strip tooltip hint and colour

**Test:** With a blocking reason showing (for example an emptied Value), hover then click the reason in the status strip.
**Expected:** Tooltip in normal tooltip colours (not amber) listing the reasons and ending with "Click a reason to jump to the control that fixes it. A reason about the whole plan jumps to the preview."; the click focuses the control that fixes it.
**Why human:** The tooltip colour is manual-only by the 07-12 must-have. G-07-8 stays open until this passes.

### Gaps Summary

No gaps block the phase goal. SnapEDA and SamacSys downloads, plus the separately downloaded SnapEDA model, import through the same preview-then-install flow as Ultra Librarian, proven on the owner's real files and on the live GUI for tests 1, 3, 4 and 6. The three later UAT gaps are closed in code and tests: G-07-5 (unusable model source blocks Install in red, with Remove), G-07-7 (draggable preview columns that fit at 900 and 1400 px) and G-07-8 (strip tooltip click hint, rich text, scoped stylesheet). Status is `human_needed` only because UAT tests 5, 7 and 8 have not been re-run in the live GUI, and the tooltip colour for G-07-8 has no automated check by design. One reproduced advisory defect, Install stuck on "Updating preview..." after a stale model result, is worth a small follow-up fix. The full suite shows 1966 passed and 21 failed, with the failing ids equal to the pre-phase baseline.

---

_Verified: 2026-10-24_
_Verifier: Claude (gsd-verifier)_
