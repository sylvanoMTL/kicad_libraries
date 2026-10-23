---
status: complete
phase: 07-snapeda-and-samacsys-adapters
source: [07-VERIFICATION.md]
started: 2026-10-23T13:05:00Z
updated: 2026-10-23T21:27:08.810Z
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
  artifacts: []
  missing: []
  observed: |
    Orchestrator check on the real USB4145-03-0170-C_REVA2.zip, unzipped to a folder:
    - bare .stp next to the .kicad_sym/.kicad_mod + Browse folder -> detected SnapEDA, model found (works)
    - model .zip in the same folder -> ignored ("Not imported ... USB4145-03-0170-C_3D.zip", intake.no_model)
    - Browse zip accepts a single *.zip only, so the CAD zip and the model download cannot be combined
