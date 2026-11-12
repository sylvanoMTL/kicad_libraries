---
status: complete
phase: 08-test-isolation-and-kicad-10
source: [08-04-SUMMARY.md]
started: 2026-10-25T19:21:00Z
updated: 2026-10-26T09:18:09.151Z
---

## Current Test

[testing complete]

## Tests

### 1. VER-01 automated: a 20241209 target on kicad-cli 10 takes the D-01 as-is-with-warning row
expected: One install WARNING naming 20211014, 20241209 and 20251024. The target header is kept at `(version 20241209)`. The vendor symbol is merged unchanged. The kicad-cli load gate reports no issues.
result: pass
source: automated
evidence: tests/test_install_e2e.py::test_cli_version_scenarios[target_20241209_as_is_with_warning] on kicad-cli 10.0.7, 2026-10-25. Full suite in the same run: 8063 passed, 3 skipped, 0 failed (17 min 53 s).

### 2. KiCad 10 Symbol Editor check of the VER-01 scratch install (D-08 manual half)
expected: |
  In PowerShell from the repo root: set `$env:KICAD_IMPORT_UAT_DIR` to a new folder outside the repository (for example `C:\Temp\kicad_uat_ver01`), run `.\env\Scripts\python.exe -m pytest tests/test_install_e2e.py::test_uat_scratch_install -s`, then in KiCad 10 add the printed `IC_PowerManagementMosfet_TI.kicad_sym` as a project symbol library of a scratch project under a nickname that does not clash with the global table (for example `UAT_PowerMosfet`), open CSD85301Q2 in the Symbol Editor, and place it in a scratch schematic. Close without saving the library, then open the scratch .kicad_sym in a text editor.

  Expected: The library opens without a load error (an older-format or read-only notice is acceptable). CSD85301Q2 shows units A and B, Footprint `IC_PowerManagementMosfet_TI:DQK0006B`, and hidden Manufacturer TI and MPN CSD85301Q2. Both units can be placed. The file still begins with `(version 20241209)`.
result: pass
evidence: Owner confirmed in KiCad 10 (2026-10-26): library opened, units A and B shown, Footprint IC_PowerManagementMosfet_TI:DQK0006B, Manufacturer/MPN hidden, both units placed. Scratch library SHA-256 unchanged before/after the session (d371dd97...7d31); header still (version 20241209). kicad-cli 10.0.7 sym export svg plotted both units.

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

