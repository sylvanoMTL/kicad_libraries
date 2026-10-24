---
status: complete
phase: 07-snapeda-and-samacsys-adapters
source: [07-VERIFICATION.md]
started: 2026-10-23T13:05:00Z
updated: 2026-10-24T09:57:21.618Z
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
expected: Click "Add 3D model..." and pick a zip holding only a .txt, then a text file renamed to .stp. Each shows an amber plain-text note under the model row (and a log line) and nothing else changes: the row, the preview and your edits stay as they were.
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

## Summary

total: 8
passed: 4
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
  truth: "Preview table columns in the Import dialog can be resized by the user and stay readable when the dialog is resized"
  status: failed
  reason: "User reported: The table in preview: the columns cannot resize, and get shricked if expanding, shrinking the Import part window edges"
  severity: major
  test: 7
  artifacts: []
  missing: []

- gap_id: G-07-8
  truth: "Clickable reason links in the status strip carry a tooltip saying they jump to the control that fixes the reason"
  status: failed
  reason: "User reported: There is no tooltip on that message, what if I clickon it?"
  severity: minor
  test: 8
  artifacts: []
  missing: []

- gap_id: G-07-5
  truth: "An unusable 3D model source (e.g. a .step/.stp that fails the content check, or a zip whose only CAD file is unusable) is reported as an ERROR (red, not amber) that blocks Install, and the model row offers both removing the bad 3D package and adding a different one"
  status: failed
  reason: "User reported: The warning is 'dummy_CAD_FILE.step holds no usable 3D model' This should be an error, the user should not be able to progress but have an option to remove the 3D package, or add a new package (e.g. if the zip was conteninng an unusable 3D CAD file)"
  severity: major
  test: 5
  artifacts: []
  missing: []
  notes: "Current design (07-08): a refused source is never attached, the candidate stays unchanged and only an amber note + log line appear; Install is not blocked. User wants this changed to a blocking error with remove / replace actions on the model row. Design change against 07-08 must-have 'Refused/empty source leaves candidate and row unchanged'. Observed during test 5: Install was greyed out after the refusal; the part was already installed into live Custom/ during test 3, so this may be 'Nothing to install' rather than a block from the refusal, or the WR-01 stale 'Updating preview...' state. Diagnosis must establish which, since the user wants the refusal itself to block."
