---
status: testing
phase: 02-hardening-existing-code
source: [02-VERIFICATION.md]
started: 2026-10-19T09:55:00Z
updated: 2026-10-19T09:55:00Z
---

## Current Test

number: 1
name: Rescan pressed repeatedly during the startup scan (HARD-05, plan 02-06 human check)
expected: |
  Launch `./env/Scripts/python.exe kicad_lib_manager.py` and, while the "Scanning libraries..." dialog is visible,
  press Ctrl+Shift+R several times. Do NOT press Generate Tables (it would repoint KICAD_LIB_GITHUB in the real
  KiCad config). No crash. The log shows "A scan is already running; request ignored." for each press. Rescan and
  Generate Tables are greyed out until the scan ends, then re-enabled.
awaiting: user response

## Tests

### 1. Rescan pressed repeatedly during the startup scan (HARD-05, plan 02-06 human check)
expected: No crash. The log shows "A scan is already running; request ignored." for each press. Rescan and Generate Tables are greyed out until the scan ends, then re-enabled. (Do NOT press Generate Tables during this test.)
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
