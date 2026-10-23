---
status: testing
phase: 07-snapeda-and-samacsys-adapters
source: [07-VERIFICATION.md]
started: 2026-10-23T13:05:00Z
updated: 2026-10-23T13:05:00Z
---

## Current Test

number: 1
name: Import both real vendor zips through the GUI Import dialog
expected: |
  Open downloaded_examples/USB4145-03-0170-C_REVA2.zip and downloaded_examples/LIB_RS3-1212S_H3.zip in the Import dialog of the running GUI, read the preview, and install into a scratch copy of Custom/ (or cancel at the preview).
  Vendor label shows SnapEDA / SamacSys. A readable "Field changes" section lists the dropped and cleaned fields.
  SnapEDA suggests Connector_USB_GCT and warns that no 3D model was found.
  SamacSys suggests PowerSupply_SubCategory_RECOM, links the model as ${CUSTOM_3DMODEL_DIR}/RS3-1212S_H3.stp and logs one "Not imported: other-CAD folders ..." line.
  If committing, the trailer reads Import-Vendor: SnapEDA / SamacSys.
awaiting: user response

## Tests

### 1. Import both real vendor zips through the GUI Import dialog
expected: Vendor label SnapEDA / SamacSys; readable "Field changes" section; SnapEDA suggests Connector_USB_GCT with the no-3D-model warning; SamacSys suggests PowerSupply_SubCategory_RECOM, model linked as ${CUSTOM_3DMODEL_DIR}/RS3-1212S_H3.stp, one "Not imported: other-CAD folders ..." log line; commit trailer Import-Vendor: SnapEDA / SamacSys.
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
