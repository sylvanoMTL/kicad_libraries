---
status: diagnosed
phase: 07-snapeda-and-samacsys-adapters
source: [07-VERIFICATION.md]
started: 2026-10-23T13:05:00Z
updated: 2026-10-23T22:00:00Z
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

## Summary

total: 2
passed: 1
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-07-2
  truth: "A separately downloaded SnapEDA 3D model (bare .step/.stp, or a zip containing it) can be imported together with the SnapEDA CAD zip and gets linked as ${CUSTOM_3DMODEL_DIR}/<file>"
  status: failed
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
