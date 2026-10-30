---
status: partial
phase: 11-commit-gate-and-commit-panel-fixes
source: [11-VERIFICATION.md]
started: 2026-10-30T00:00:00Z
updated: 2026-10-30T21:18:19.550Z
---

## Current Test

[testing complete]

## Tests

### 1. Commit panel look (primary button, outcome strips, "Committed in Custom only" label, sizes)
expected: Commit button reads as the primary action; error, success and warning outcomes show red, green and amber strips; a parent-failed result reads 'Committed in Custom only'; sizes look right at normal and high DPI
result: pass
source: automated
note: "Owner away; checked by Claude from screenshots of the real CommitPanel (Windows platform plugin, widget.grab) in ready, success, error, warning and parent-failed states at QT_SCALE_FACTOR 1 and 2. Commit is a filled blue primary button; strips are green, red and amber; parent-failed button reads 'Committed in Custom only'; text and controls scale cleanly at 200%. Panel shown alone, not inside the full import dialog."

### 2. Paste the "Finish it by hand" command into interactive Windows PowerShell 5.1 and PowerShell 7, with a subject holding quotes, $ and a backtick
expected: The command runs as shown and makes the parent commit with the subject intact
result: blocked
blocked_by: other
reason: "Owner away. Windows PowerShell 5.1 checked automatically: the manual_command output made a real parent commit with the subject intact for subjects with double quotes (-F form), single quotes, $HOME, $(...), and backticks (-m form), via -Command, a .ps1 file and stdin to -Command -. A typographic-quote subject passed via -Command and .ps1; its stdin run failed only because 5.1 decodes redirected stdin in the OEM code page (harness artifact, not the command). PowerShell 7 is not installed on this machine and downloading a portable copy was not permitted, so the PowerShell 7 half and a true console paste remain for the owner."

## Summary

total: 2
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 1

## Gaps
