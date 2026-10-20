---
status: testing
phase: 04-plan-and-install-core
source: [04-VERIFICATION.md]
started: 2026-10-20T11:40:00Z
updated: 2026-10-20T11:40:00Z
---

## Current Test

number: 1
name: KiCad 9 UAT on the scratch install
expected: |
  Set KICAD_IMPORT_UAT_DIR, run the opt-in test in tests/test_install_e2e.py, and follow the checklist in 04-10-SUMMARY.md.
  The library opens without a load error. CSD85301Q2 shows units A and B with Footprint IC_Battery_Charger_TI:DQK0006B and hidden Manufacturer/MPN. DQK0006B shows 8 pads and the STEP sits on the pads. Includes the A6/A7 field-rule judgement (renamed vendor Manufacturer/MPN keep their own visibility; an extends parent receives Footprint, filters and Manufacturer).
awaiting: user response

## Tests

### 1. KiCad 9 UAT on the scratch install (KICAD_IMPORT_UAT_DIR, checklist in 04-10-SUMMARY.md, including A6/A7)
expected: The library opens without a load error. CSD85301Q2 shows units A and B with Footprint IC_Battery_Charger_TI:DQK0006B and hidden Manufacturer/MPN. DQK0006B shows 8 pads and the STEP sits on the pads. A6/A7: renamed vendor Manufacturer/MPN keep their own visibility; an extends parent receives Footprint, filters and Manufacturer.
result: [pending]

### 2. KiCad 10 symbol format 20251024 (research assumption A1)
expected: Every 20241209 Custom/ library takes the as-is-with-warning row of the D-01 version table.
result: [pending]

### 3. Case-sensitive-volume rollback and overwrite branches (case twin written under another spelling)
expected: Rollback restores the original spelling and removes the twin.
result: [pending]

### 4. A part edited in KiCad shows as a conflict on re-import (accepted D-07 consequence, from 04-09)
expected: Owner confirms this reads correctly in the Phase 5 preview.
result: [pending]

## Summary

total: 4
passed: 0
issues: 0
pending: 4
skipped: 0
blocked: 0

## Gaps
