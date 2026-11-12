---
phase: 13
review: 13-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "Two footprints' 3D models can be renamed to the same file, silently destroying one of them"
  - id: WR-01
    severity: warning
    disposition: open
    title: "`CommitPlan`/`CommitProbe` type annotations in `migration_dialog.py` are unresolved names"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`CommitPanel._mark_files` never marks a deleted commit row as \"also changed before this import\""
  - id: IN-01
    severity: info
    disposition: open
    title: "Unused parameter `result` in `MainWindow._on_migrated`"
open: 4
total: 4
recorded: 2026-11-12T06:47:44.574Z
---

# Phase 13: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| IN-01 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
