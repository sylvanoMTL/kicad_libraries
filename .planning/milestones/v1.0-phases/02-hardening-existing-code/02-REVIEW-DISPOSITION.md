---
phase: 02
review: 02-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "Empty destination text resolves to the current working directory"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Unreadable symbol library is silently treated as having no footprint references"
  - id: WR-03
    severity: warning
    disposition: open
    title: "A missing or uninitialised submodule makes Generate delete its managed entries"
  - id: WR-04
    severity: warning
    disposition: open
    title: "External-clash casualties are reported as \"Removed (deselected)\""
  - id: WR-05
    severity: warning
    disposition: open
    title: "Restore dialog and `list_backup_pairs` crash on a destination that is a file or unreadable"
  - id: WR-06
    severity: warning
    disposition: open
    title: "Generate runs process listing, fsync and retry sleeps on the GUI thread"
  - id: WR-07
    severity: warning
    disposition: open
    title: "Atomic replace discards symlinks and the original file's permissions"
  - id: IN-01
    severity: info
    disposition: open
    title: "Scan progress runs backwards between phases"
  - id: IN-02
    severity: info
    disposition: open
    title: "Unused `pytest` imports"
  - id: IN-03
    severity: info
    disposition: open
    title: "CLAUDE.md repository structure omits the new foundation modules"
  - id: IN-04
    severity: info
    disposition: open
    title: "Paired backup numbers can silently diverge if the shared number is already taken"
open: 11
total: 11
recorded: 2026-10-19T09:41:45.943Z
---

# Phase 02: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
