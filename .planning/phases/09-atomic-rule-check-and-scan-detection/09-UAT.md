---
status: complete
phase: 09-atomic-rule-check-and-scan-detection
source: [09-VERIFICATION.md]
started: 2026-10-26T18:10:00Z
updated: 2026-10-26T17:30:56.773Z
---

## Current Test

[testing complete]

## Tests

### 1. Rebuild the UAT scratch repo from the live Custom/ (G-09-1 helper fix)
expected: "1 passed" (not skipped), scratch repo path printed, empty diff of the live Custom/ status. Prior results for tests 2-5 of the first UAT round (all passed) are in git history.
result: pass
note: "Run by Claude on request: 1 passed in 3.33s, scratch repo at %LOCALAPPDATA%/Temp/kicad_atomic_uat_g091/repo, Custom/ status diff empty."

### 2. Re-test UAT test 1: component level in the library tree
expected: Open the GUI on the scratch repo from test 1. An Atomic_ library with problems shows its parts collapsed, each with its Status count (for example "Changed · 3 rules"). Expanding a failing part shows one amber row with a warning icon per broken rule, then one plain row with an info icon per note, full width and readable. Double-clicking a part, or one of its problem rows, opens Check Atomic Parts on that part.
result: pass
note: "First reported as many lines in Atomic_Connector not linked to a component. These are the planted synthetic rule-case parts (DS-EMPTY, MPN-NONE, ...), one per rule, not real components; the tree dump showed every problem row under its own part. Owner confirmed expected; re-marked pass."

### 3. Decide on review warning WR-01: double-click also expands the part
expected: Double-clicking a part row opens Check Atomic Parts and also expands or collapses that part. Either accept this, or ask for it to stop (setExpandsOnDoubleClick(False); library and group rows would then also stop toggling on double-click).
result: pass
note: "WR-01 accepted: double-click both opens Check Atomic Parts and toggles expansion."

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
