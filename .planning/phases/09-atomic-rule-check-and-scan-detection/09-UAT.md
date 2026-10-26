---
status: testing
phase: 09-atomic-rule-check-and-scan-detection
source: [09-VERIFICATION.md]
started: 2026-10-26T15:30:00Z
updated: 2026-10-26T15:30:00Z
---

## Current Test

number: 1
name: Library tree marks after a scan
expected: |
  Failing symbols carry the warning icon and amber row; New/Changed symbols carry the accent colour; libraries with problems auto-expand; tooltips read clearly (rich text, plain language)
awaiting: user response

## Tests

### 1. Library tree marks after a scan
Open the GUI on a scratch repo (build it with KICAD_ATOMIC_UAT_DIR, tests/test_atomic_uat.py) or on the live Custom/ and look at the library tree after a scan.
expected: Failing symbols carry the warning icon and amber row; New/Changed symbols carry the accent colour; libraries with problems auto-expand; tooltips read clearly (rich text, plain language)
result: [pending]

### 2. Check Atomic Parts on real parts (D-25)
Open Check Atomic Parts (Ctrl+Shift+A, or double-click a failing symbol) on real parts, tick fixes, preview and apply, then rescan.
expected: Dialog lists every violation per symbol, the preview matches what lands on disk, a backup exists, and the fixed violations are gone on the next scan
result: [pending]

### 3. Reason wording for the seven rules
Read the reason wording in the tooltip, log and dialog for each of the seven rules.
expected: Owner finds the wording plain and unambiguous
result: [pending]

### 4. Canonical manufacturer table
Review kicad_lib_manager/manufacturers.py for the Murata and TDK spellings and the acquired-brand entries (Maxim, Linear, InvenSense).
expected: Owner confirms the canonical names and aliases
result: [pending]

### 5. Undigited ${KICAD_3DMODEL_DIR}
Decide whether an undigited ${KICAD_3DMODEL_DIR} model path should resolve against KiCad's 3dmodels folder.
expected: Owner states the rule; today only ${KICADn_3DMODEL_DIR} (digited) resolves and the undigited form is reported as "Could not check the 3D model: it uses ${...}"
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
