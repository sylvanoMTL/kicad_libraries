---
status: testing
phase: 06-git-commit-step
source: [06-VERIFICATION.md]
started: 2026-10-22T22:17:38Z
updated: 2026-10-22T22:17:38Z
---

## Current Test

number: 1
name: Owner UAT on the real repo (plan 06-08 Task 2) — commit an imported part from the Result view
expected: |
  Run `.\env\Scripts\python.exe kicad_lib_manager.py`, File > Import Part..., open downloaded_examples/ul_CSD85301Q2.zip, pick or type a real library, click Install Part.
  The Commit step shows "Custom branch: main", "Parent repo: {this checkout} (feature/part-importer)", "Files to commit (3)" listing exactly the three installed files, a message starting "Add CSD85301Q2 to ..." with Import-Vendor: Ultra Librarian, Import-Package: ul_CSD85301Q2.zip and today's Import-Date, the parent checkbox ticked, and (while the parent's committed Custom gitlink is still 485d530) "Parent bump also includes 2 earlier Custom commits" listing 49f746c and d3ff246.
  Editing the subject updates the generated parent message. After Commit, the panel and log show both commit hashes and "Not pushed — Custom is 1 commit ahead of origin/main (as last fetched)" plus the parent line.
  In a shell: `git -C Custom log -1 --stat` lists only the three files; `git -C Custom status` still shows any other change; `git log -1 --stat` lists only Custom; `git status` still shows the .planning changes uncommitted; `git -C Custom rev-list --count @{u}..HEAD` prints 1; `git -C Custom ls-remote origin refs/heads/main` equals `git -C Custom rev-parse origin/main`.
  Keep or undo the UAT commits yourself; the app never pushes.
awaiting: user response

## Tests

### 1. Owner UAT on the real repo (plan 06-08 Task 2) — commit an imported part from the Result view
expected: Only the 3 imported files are committed in Custom, only the Custom ref in the parent, both hashes and "Not pushed — Custom is 1 commit ahead of origin/main (as last fetched)" are shown, every other change in both repos stays uncommitted, and the remote main is unchanged.
result: [pending]

### 2. Close the dialog on a second import without committing
expected: The log shows "Not committed — commit manually: ..." exactly once.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
