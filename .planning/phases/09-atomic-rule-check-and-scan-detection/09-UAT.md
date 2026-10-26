---
status: testing
phase: 09-atomic-rule-check-and-scan-detection
source: [09-VERIFICATION.md]
started: 2026-10-26T18:10:00Z
updated: 2026-10-26T18:10:00Z
---

## Current Test

number: 1
name: Rebuild the UAT scratch repo from the live Custom/ (G-09-1 helper fix)
expected: |
  Once you have finished importing into Custom/, run from the repo root (Git Bash):
    git -C Custom status --porcelain > "$LOCALAPPDATA/Temp/g091_custom_before.txt"
    KICAD_ATOMIC_UAT_DIR="$LOCALAPPDATA/Temp/kicad_atomic_uat_g091" env/Scripts/python.exe -m pytest tests/test_atomic_uat.py::test_uat_atomic_scratch -rs -q -s
    git -C Custom status --porcelain | diff - "$LOCALAPPDATA/Temp/g091_custom_before.txt"
  The test reports "1 passed" (not skipped) and prints the scratch repo path; the diff is empty.
  FFC2A32-06-T (no Datasheet field) no longer crashes the helper.
awaiting: user response

## Tests

### 1. Rebuild the UAT scratch repo from the live Custom/ (G-09-1 helper fix)
expected: "1 passed" (not skipped), scratch repo path printed, empty diff of the live Custom/ status. Prior results for tests 2-5 of the first UAT round (all passed) are in git history.
result: [pending]

### 2. Re-test UAT test 1: component level in the library tree
expected: Open the GUI on the scratch repo from test 1. An Atomic_ library with problems shows its parts collapsed, each with its Status count (for example "Changed · 3 rules"). Expanding a failing part shows one amber row with a warning icon per broken rule, then one plain row with an info icon per note, full width and readable. Double-clicking a part, or one of its problem rows, opens Check Atomic Parts on that part.
result: [pending]

### 3. Decide on review warning WR-01: double-click also expands the part
expected: Double-clicking a part row opens Check Atomic Parts and also expands or collapses that part. Either accept this, or ask for it to stop (setExpandsOnDoubleClick(False); library and group rows would then also stop toggling on double-click).
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
