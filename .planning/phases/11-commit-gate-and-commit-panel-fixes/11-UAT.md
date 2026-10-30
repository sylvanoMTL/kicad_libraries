---
status: testing
phase: 11-commit-gate-and-commit-panel-fixes
source: [11-VERIFICATION.md]
started: 2026-10-30T00:00:00Z
updated: 2026-10-30T00:00:00Z
---

## Current Test

number: 1
name: Commit panel look (primary button, outcome strips, "Committed in Custom only" label, sizes)
expected: |
  Commit button reads as the primary action; error, success and warning outcomes show red, green and amber strips; a parent-failed result reads 'Committed in Custom only'; sizes look right at normal and high DPI
awaiting: user response

## Tests

### 1. Commit panel look (primary button, outcome strips, "Committed in Custom only" label, sizes)
expected: Commit button reads as the primary action; error, success and warning outcomes show red, green and amber strips; a parent-failed result reads 'Committed in Custom only'; sizes look right at normal and high DPI
result: [pending]

### 2. Paste the "Finish it by hand" command into interactive Windows PowerShell 5.1 and PowerShell 7, with a subject holding quotes, $ and a backtick
expected: The command runs as shown and makes the parent commit with the subject intact
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
