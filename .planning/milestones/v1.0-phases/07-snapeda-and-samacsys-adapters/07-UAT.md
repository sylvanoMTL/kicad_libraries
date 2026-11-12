---
status: complete
phase: 07-snapeda-and-samacsys-adapters
source: [07-VERIFICATION.md]
started: 2026-10-23T13:05:00Z
updated: 2026-10-24T17:35:08.281Z
---

## Current Test

[testing complete]

## Tests

### 1. Import both real vendor zips through the GUI Import dialog
expected: Vendor label SnapEDA / SamacSys; readable "Field changes" section; SnapEDA suggests Connector_USB_GCT with the no-3D-model warning; SamacSys suggests PowerSupply_SubCategory_RECOM, model linked as ${CUSTOM_3DMODEL_DIR}/RS3-1212S_H3.stp, one "Not imported: other-CAD folders ..." log line; commit trailer Import-Vendor: SnapEDA / SamacSys.
result: pass

### 2. Attach a separately downloaded SnapEDA 3D model
expected: SnapEDA ships the 3D model as a separate download, either a bare .step/.stp or a zip holding it. The user can import the SnapEDA CAD zip together with that model, and the model is copied to Custom/3DModels/ and linked as ${CUSTOM_3DMODEL_DIR}/<file>.step.
result: issue
reported: "there was not 3d model, what if I get a 3d model in a separate file? (in SnapEDA this is what you get, not in a full zip file) ... actually Snap EDA you downlad separately and it is either a cad file or a zip file containing the cad file"
severity: major

### 3. Add 3D model from the SnapEDA model zip (re-test of G-07-2)
expected: Run .\env\Scripts\python.exe kicad_lib_manager.py, open the Import dialog and load downloaded_examples/USB4145-03-0170-C_REVA2.zip. Before attaching, type something into Value or MPN. An "Add 3D model..." button sits under the 3D model row; its picker offers *.step *.stp *.wrl *.zip. Pick downloaded_examples/194150990-659-usb4145-03-0170-c.zip. Install shows as busy only while the model is read. Afterwards the row shows usb4145-03-0170-c.stp, the "no 3D model found" warning is gone, the Files section lists Custom/3DModels/USB4145-03-0170-C.stp, and the values you typed are unchanged.
result: pass

### 4. Add a bare .stp as the 3D model
expected: Reload the SnapEDA CAD zip (or click Change... and reopen it), then click "Add 3D model..." and pick the bare .stp extracted from the model zip. Same outcome as test 3: row shows the .stp, no-model warning gone, Files section lists Custom/3DModels/USB4145-03-0170-C.stp, typed edits kept.
result: pass

### 5. Refused model sources
expected: Click Add 3D model... and pick a zip holding only a .txt, then an empty or renamed text file saved as .stp/.step, then a zip holding one good .stp and one renamed non-STEP file. Each shows a red plain-text error note under the model row (and a log line). Nothing from that source is attached, even the good file of the mixed zip. Install Part is blocked with an 'Error: ...' reason that jumps to the model row, and a Remove button under the note clears it, after which Install is back to what the preview says. Add 3D model... still lets you pick another file, and your edits and the preview stay as they were. Use a part that is not already in the live Custom/, or settle its conflicts, so a conflict does not block Install for another reason.
result: issue
reported: "The warning is 'dummy_CAD_FILE.step holds no usable 3D model' This should be an error, the user should not be able to progress but have an option to remove the 3D package, or add a new package (e.g. if the zip was conteninng an unusable 3D CAD file)"
reported_followup: "This is an error not a warning, so red color is needed. I note install part is grayed out"
severity: major

### 6. Preview and install with the attached model
expected: With the model from test 3 or 4 attached, read the preview. The footprint's model path reads ${CUSTOM_3DMODEL_DIR}/USB4145-03-0170-C.stp. Either cancel at the preview, or install into a scratch copy of Custom/ (not the live one, which already holds an uncommitted UAT part) and confirm the installed footprint links ${CUSTOM_3DMODEL_DIR}/USB4145-03-0170-C.stp.
result: pass

### 7. Preview table columns resize with the dialog
expected: In the Import dialog preview, the table's columns can be resized by dragging the header dividers, and resizing the Import part window keeps the columns readable instead of squashing them.
result: issue
reported: "The table in preview: the columns cannot resize, and get shricked if expanding, shrinking the Import part window edges"
severity: major
source: observed during test 3

### 8. Status-strip reason links explain what they do
expected: A blocking reason in the status strip (e.g. "Choose Overwrite, Rename or Skip for ...") shows a tooltip saying that clicking it jumps to the control that fixes it.
result: issue
reported: "There is no tooltip on that message, what if I clickon it?"
severity: minor
source: observed during test 3

### 9. Unusable 3D model source blocks Install (re-test of G-07-5)
expected: Load the SnapEDA CAD zip (part not already in live Custom/, or conflicts settled). Add 3D model... with (a) a zip holding only a .txt, (b) an empty/renamed text file saved as .stp/.step, (c) a zip with one good .stp and one renamed non-STEP file. Each gives a red plain-text error note under the model row and a log line; nothing from the source is attached (not even the good file of the mixed zip); Install Part is disabled with an 'Error: ...' strip reason whose click focuses Remove; Remove clears the note and Install returns to what the preview says; Add 3D model... still works; typed edits and preview untouched.
result: pass
source: re-test of G-07-5 (07-10, 07-13)

### 10. Preview columns resize on the real display (re-test of G-07-7)
expected: Open Import with downloaded_examples/USB4145-03-0170-C_REVA2.zip. The Item | Detail divider can be dragged. Narrowing and widening the Import part window keeps both columns readable; long Field changes rows are cut off with an ellipsis inside Detail (full text in the tooltip) instead of running past the right edge. Typing in Value rebuilds the preview and the dragged width is kept.
result: pass
source: re-test of G-07-7 (07-11)

### 11. Status-strip tooltip hint and colours (re-test of G-07-8)
expected: Make a blocking reason show (e.g. empty the Value field). Hovering the reason in the status strip shows a tooltip in normal tooltip colours (not the strip's amber), listing the reasons and ending with "Click a reason to jump to the control that fixes it. A reason about the whole plan jumps to the preview." Characters such as & or ' show as themselves, not &amp; / &#x27;. Clicking the reason focuses the control that fixes it.
result: pass
source: re-test of G-07-8 (07-12)

## Summary

total: 11
passed: 7
issues: 4
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-07-2
  resolved_by: 07-08-PLAN.md
  resolved_at: 2026-10-24
  truth: "A separately downloaded SnapEDA 3D model (bare .step/.stp, or a zip containing it) can be imported together with the SnapEDA CAD zip and gets linked as ${CUSTOM_3DMODEL_DIR}/<file>"
  status: resolved
  reason: "User reported: SnapEDA 3D models are a separate download, either a bare CAD file or a zip containing it; the CAD zip has no model"
  severity: major
  test: 2
  root_cause: "Design/scope gap, not a regression: intake is single-source end to end. open_package takes one zip or folder and ImportCandidate.models is filled only from that Package; _open_folder ignores every .zip (package.py:566-567), so a SnapEDA model zip next to loose files is skipped; a model-only zip is refused (intake.nothing_found) and a bare .stp is refused (intake.unsupported); ImportDialog holds one self._package and its 3D model row has no add action. The feature was explicitly deferred (PROJECT.md:78 Out of Scope, REQUIREMENTS.md:101 FMT2-02 v2, 07-CONTEXT.md:42 'SnapEDA is the no-model case'). Headless proof: attaching a model from a second open_package(model zip) via dataclasses.replace works through build_plan/apply_plan unchanged (case G) - the frozen plan contract needs no change."
  artifacts:
    - path: "kicad_lib_manager/importer/package.py"
      issue: "open_package is single-source and refuses bare .step/.stp/.wrl; _open_folder ignores zips; no model-only intake function"
    - path: "kicad_lib_manager/importer/detect.py"
      issue: "models come only from the primary Package; nothing attaches models to an existing candidate (see also adapters/base.py locate/_check_model)"
    - path: "kicad_lib_manager/widgets/import_dialog.py"
      issue: "single self._package; _on_browse/_on_browse_folder/open_path replace it; 3D model row in _populate_items (1350-1364) has no 'Add 3D model...' action; _discard_package/_shutdown close only self._package; ImportCore has no model-source entry point"
    - path: "kicad_lib_manager/main_window.py"
      issue: "dropEvent accepts one file only (optional)"
    - path: ".planning/PROJECT.md, .planning/REQUIREMENTS.md, 07-CONTEXT.md"
      issue: "feature listed Out of Scope / FMT2-02 v2 / locked as no-model case - must be moved into v1"
  missing:
    - "package.open_model_source(path, repo_root, progress=None): .zip via _open_zip/_stage_zip keeping only model-kind files (all Phase 3 hostile-zip checks and caps apply); bare .step/.stp/.wrl read in place with no-follow lstat, link/reparse/junction refusal, regular-file check, MAX_MEMBER_BYTES cap, SHA-256; new ERROR code when the source holds no model; decide shared vs per-package byte budget"
    - "pure attach_models(candidate, model_package) -> candidate: magic check (_check_model), filename clash avoidance (casefolded), drop intake.no_model, add INFO naming the model source"
    - "ImportDialog: 'Add 3D model...' button on the model row (filter *.step *.stp *.wrl *.zip), run via TaskWorker through ImportCore (fakeable), keep self._model_package open until apply_plan returns (WR-04), close it in _discard_package/_shutdown, rebuild only the model row (do NOT re-run _populate_items - it wipes user edits), then _request_rebuild(); disabled while installing/committing/opening"
    - "Tests: synthetic model zip (.stp+.txt) and bare .stp with refusals (symlink, oversize, hostile zip, wrong magic); attach_models -> build_plan -> apply_plan into tmp Custom/; real-sample test skipping when downloaded_examples/194150990-659-usb4145-03-0170-c.zip is absent; dialog test with fake open_model_source"
    - "Planning docs: move FMT2-02 into v1, remove PROJECT.md:78 Out of Scope entry, note the 07-CONTEXT.md:42 decision change"
  debug_session: ".planning/debug/snapeda-separate-3d-model.md"
  observed: |
    Orchestrator check on the real USB4145-03-0170-C_REVA2.zip, unzipped to a folder:
    - bare .stp next to the .kicad_sym/.kicad_mod + Browse folder -> detected SnapEDA, model found (works)
    - model .zip in the same folder -> ignored ("Not imported ... USB4145-03-0170-C_3D.zip", intake.no_model)
    - Browse zip accepts a single *.zip only, so the CAD zip and the model download cannot be combined

- gap_id: G-07-7
  resolved_by: 07-11-PLAN.md
  resolved_at: 2026-10-24
  truth: "Preview table columns in the Import dialog can be resized by the user and stay readable when the dialog is resized"
  status: resolved
  reason: "User reported: The table in preview: the columns cannot resize, and get shricked if expanding, shrinking the Import part window edges"
  severity: major
  test: 7
  root_cause: "PreviewTree (kicad_lib_manager/widgets/preview_tree.py:26-35) sets section 0 (Item) to Stretch and section 1 (Detail) to ResizeToContents with stretchLastSection False and the horizontal scrollbar always off, per 05-UI-SPEC.md:315. Neither section is Interactive, so the user cannot drag the divider. Detail is pinned to its widest single-line content; since Phase 07 the Field changes drop rows (importer/preview.py:255-283) make that ~734 px, wider than the 479-634 px viewport, so Item keeps a stale width or squashes to ~80 px and the overflow is clipped. Rebuilds do not reset widths."
  artifacts:
    - path: "kicad_lib_manager/widgets/preview_tree.py"
      issue: "lines 26-35: Stretch + ResizeToContents header modes, no Interactive section, horizontal scrollbar off"
    - path: "kicad_lib_manager/importer/preview.py"
      issue: "255-283 Field changes detail text up to ~104 chars; 232-243 Path-rewrite detail text is unbounded"
    - path: ".planning/phases/05-import-ui-and-post-install/05-UI-SPEC.md"
      issue: "lines 315 and 511 lock the current column contract; must be amended"
    - path: "tests/test_preview_tree.py"
      issue: "no test covers column resize modes or widths"
  missing:
    - "Make Item Interactive, give it an initial width once (e.g. ~55% of the viewport on first show/first plan, never inside render() or the build-finished handler), setStretchLastSection(True) so Detail fills the rest and elides when narrow (tooltip already holds the full text)"
    - "Optionally cap Path-rewrite detail length like _shown"
    - "Regression tests: simulated divider drag moves the section; dragged width survives render() and _request_rebuild(); at 900 px and 1400 px dialog widths both columns stay above a readable minimum and fit the viewport"
    - "Amend 05-UI-SPEC.md:315 and :511"
  debug_session: ".planning/debug/preview-table-columns-not-resizable.md"

- gap_id: G-07-8
  resolved_by: 07-12-PLAN.md
  resolved_at: 2026-10-24
  truth: "Clickable reason links in the status strip carry a tooltip saying they jump to the control that fixes the reason"
  status: resolved
  reason: "User reported: There is no tooltip on that message, what if I clickon it?"
  severity: minor
  test: 8
  root_cause: "The strip tooltip only repeats the reason list (05-UI-SPEC.md:353/517 and 05-09-PLAN.md:42 asked only for the overflow list), so with one reason it is the same text the user already reads and never says the reason is a link; linkHovered has no receivers. It is also hard to see: _set_strip applies a selector-less stylesheet (background-color: AMBER_TINT) that Qt also applies to the tooltip, so it draws amber on amber. Side defect: a single-reason tooltip is HTML-escaped but shown as plain text, so & and ' appear as &amp; / &#x27;."
  artifacts:
    - path: "kicad_lib_manager/widgets/import_dialog.py"
      issue: "596-612 strip built without hint; 2163-2169 _set_strip selector-less stylesheet; 2210-2230 _render_strip tooltip = '<br>'.join(escaped reasons) only"
    - path: ".planning/phases/05-import-ui-and-post-install/05-UI-SPEC.md"
      issue: "lines 353 and 517 tooltip copy covers only the overflow reason list"
  missing:
    - "One strip-wide tooltip (user decision 2026-10-24): reason list plus a hint line such as 'Click a reason to go to the control that fixes it' (wording also covering 'plan' targets that focus the preview)"
    - "Force rich text for the tooltip (e.g. wrap in <p>) so a single escaped reason renders correctly"
    - "Give the strip an objectName and scope its stylesheet (QLabel#installStrip {...}) so the tooltip uses normal tooltip colours"
    - "Tests: hint text present, single-reason escaping renders correctly, tooltip background not the strip amber"
    - "Update 05-UI-SPEC.md copy"
  debug_session: ".planning/debug/reason-link-no-tooltip.md"

- gap_id: G-07-5
  resolved_by: 07-13-PLAN.md
  resolved_at: 2026-10-24
  truth: "An unusable 3D model source (e.g. a .step/.stp that fails the content check, or a zip whose only CAD file is unusable) is reported as an ERROR (red, not amber) that blocks Install, and the model row offers both removing the bad 3D package and adding a different one"
  status: resolved
  reason: "User reported: The warning is 'dummy_CAD_FILE.step holds no usable 3D model' This should be an error, the user should not be able to progress but have an option to remove the 3D package, or add a new package (e.g. if the zip was conteninng an unusable 3D CAD file)"
  severity: major
  test: 5
  root_cause: "Design gap, not a regression: 07-08 specified that a refused model source is closed and forgotten, so it never reaches the candidate, FormStatus or blocking_reasons and cannot block Install. The core already returns Severity.ERROR intake.no_model_in_source (adapters/base.py:405-410, package.py:344-348) but the dialog hard-codes tone='amber' in _on_model_attached (import_dialog.py:1675) and _on_model_failed (1695); _set_model_note (1424-1435) has no error tone. The greyed-out Install in the user's test 5 was an unrelated unresolved symbol conflict (part already installed in test 3, conflict choices reset by reopening the zip), not the refusal and not WR-01: with a conflict-free part the same refusal leaves Install enabled ('Ready to install')."
  artifacts:
    - path: "kicad_lib_manager/widgets/import_dialog.py"
      issue: "_on_model_attached/_on_model_failed hard-code amber; _set_model_note lacks an error tone; no rejected-source state; _build_model_row has no Remove control; _form_status carries no model error; _clear_items/_discard_package must reset the new state"
    - path: "kicad_lib_manager/importer/form.py"
      issue: "FormStatus (89-100) has no model field; blocking_reasons (133-199) has no model reason; Reason.target docstring lacks 'model'"
    - path: "kicad_lib_manager/importer/adapters/base.py"
      issue: "attach_models attaches the good model of a partly bad zip and only logs WARNING intake.content_mismatch; per user decision a partly bad source must be rejected as a whole"
    - path: "kicad_lib_manager/widgets/theme.py"
      issue: "ERROR/ERROR_TINT exist but FIELD_FRAME_QSS is amber only"
    - path: "kicad_lib_manager/widgets/help_dialog.py"
      issue: "224-227 must describe the blocking error and Remove"
    - path: ".planning/phases/07-snapeda-and-samacsys-adapters/07-08-PLAN.md"
      issue: "must-have line 27 and notes 111-125 hold the superseded decision"
  missing:
    - "Rejected-model-source state on ImportDialog (source name + first ERROR issue), set when attach returns no candidate with an ERROR, when the model worker fails (read failure), and when a source holds any unusable model file (partly bad zip rejected as a whole: nothing from it is attached)"
    - "FormStatus gains a defaulted model_error field filled in _form_status; blocking_reasons appends Reason('Error: <text>', 'model') after plan errors, so Install is blocked"
    - "Model note rendered in theme.ERROR (red), PlainText kept (T-07-30)"
    - "Remove button under the model note that clears the rejected source and calls _update_install_state(); Add 3D model... stays enabled as 'add another'; a successful attach clears the rejected source; Change.../new open/close reset it"
    - "_reason_targets['model'] registered so the strip link focuses the model row"
    - "Remove scope is rejected sources only (user decision 2026-10-24); detaching a successfully attached model is out of scope"
    - "INFO duplicates (intake.model_already_present, muted note) stay non-blocking"
    - "Update tests: test_add_model_refusal_shows_note, test_add_model_worker_failure_logged, test_add_model_note_is_plain_text (Install-disabled check), test_import_form.py status() helper + blocking_reasons cases, test_model_attach.py partly-bad-zip case; help dialog text"
    - "Reword 07-08 must-have and the UAT test 5 script for the new behaviour"
  decisions:
    - "Read failures block too (user, 2026-10-24)"
    - "Partly bad zip blocks too, rejected as a whole (user, 2026-10-24)"
    - "Remove clears rejected sources only (user, 2026-10-24)"
  debug_session: ".planning/debug/unusable-model-source-not-blocking.md"
  notes: "Current design (07-08): a refused source is never attached, the candidate stays unchanged and only an amber note + log line appear; Install is not blocked. User wants this changed to a blocking error with remove / replace actions on the model row. Design change against 07-08 must-have 'Refused/empty source leaves candidate and row unchanged'. Observed during test 5: Install was greyed out after the refusal; the part was already installed into live Custom/ during test 3, so this may be 'Nothing to install' rather than a block from the refusal, or the WR-01 stale 'Updating preview...' state. Diagnosis must establish which, since the user wants the refusal itself to block."
