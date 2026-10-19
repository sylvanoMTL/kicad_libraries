---
status: testing
phase: 03-package-intake-and-naming
source: [03-VERIFICATION.md]
started: 2026-10-19T14:45:00Z
updated: 2026-10-19T14:45:00Z
---

## Current Test

number: 1
name: Decide whether CR-01 (parsed KiCad text capped at 100 MB) must be closed before Phase 4 starts
expected: |
  A hostile low-ratio .kicad_sym inside the existing size and ratio limits is skipped with a WARNING instead of costing minutes of CPU and gigabytes of RAM.
awaiting: user response

## Tests

### 1. Decide whether CR-01 (parsed KiCad text capped at 100 MB) must be closed before Phase 4 starts
Recommendation: close it with a small gap-closure plan that adds a separate `MAX_KICAD_TEXT_BYTES` cap (about 8 MB) for symbol and footprint files.
expected: A hostile low-ratio .kicad_sym inside the existing size and ratio limits is skipped with a WARNING instead of costing minutes of CPU and gigabytes of RAM.
result: [pending]

### 2. Decide whether CR-02 (corrupt LZMA member raises out of open_package; TemporaryDirectory creation outside any try) must be closed before Phase 4 starts
Recommendation: close it by adding `lzma.LZMAError` to the caught tuple and guarding the `TemporaryDirectory(...)` creation.
expected: A damaged LZMA zip returns an ERROR Issue `intake.corrupt` and deterministically removes its staging folder; `open_package` never raises for expected input faults.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
