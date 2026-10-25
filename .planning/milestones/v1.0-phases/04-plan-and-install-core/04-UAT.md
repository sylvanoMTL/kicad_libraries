---
status: complete
phase: 04-plan-and-install-core
source: [04-VERIFICATION.md]
started: 2026-10-20T11:40:00Z
updated: 2026-10-20T11:46:30.150Z
---

## Current Test

[testing complete]

## Tests

### 1. KiCad 9 UAT on the scratch install (KICAD_IMPORT_UAT_DIR, checklist in 04-10-SUMMARY.md, including A6/A7)
expected: The library opens without a load error. CSD85301Q2 shows units A and B with Footprint IC_Battery_Charger_TI:DQK0006B and hidden Manufacturer/MPN. DQK0006B shows 8 pads and the STEP sits on the pads. A6/A7: renamed vendor Manufacturer/MPN keep their own visibility; an extends parent receives Footprint, filters and Manufacturer.
result: pass

### 2. KiCad 10 symbol format 20251024 (research assumption A1)
expected: Every 20241209 Custom/ library takes the as-is-with-warning row of the D-01 version table.
result: skipped
reason: "Deferred follow-up: I do not have kicad 10 yet"

### 3. Case-sensitive-volume rollback and overwrite branches (case twin written under another spelling)
expected: Rollback restores the original spelling and removes the twin.
result: skipped
reason: "Deferred follow-up: pass i cannot test it"

### 4. A part edited in KiCad shows as a conflict on re-import (accepted D-07 consequence, from 04-09)
expected: Owner confirms this reads correctly in the Phase 5 preview.
result: pass

## Summary

total: 4
passed: 2
issues: 0
pending: 0
skipped: 2
blocked: 0

## Gaps

## Deferred Follow-Ups

- test: 2
  idea: "I do not have kicad 10 yet (re-test the D-01 as-is-with-warning row on KiCad 10, symbol format 20251024)"
  deferred_at: 2026-10-20
- test: 3
  idea: "pass i cannot test it (re-test case-twin rollback and overwrite on a case-sensitive folder; owner chose to defer)"
  deferred_at: 2026-10-20
