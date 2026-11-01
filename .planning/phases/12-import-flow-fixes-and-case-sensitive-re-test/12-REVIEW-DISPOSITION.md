---
phase: 12
review: 12-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "An exception in the path-variable check leaves `_path_var_busy` set for the whole session"
  - id: WR-02
    severity: warning
    disposition: open
    title: "A lost-update window remains in the `kicad_common.json` write"
  - id: WR-03
    severity: warning
    disposition: open
    title: "`_close_after_check` is a latch that is never cleared"
  - id: WR-04
    severity: warning
    disposition: open
    title: "New user-facing text uses file names and tool names (owner preference: plain language)"
  - id: WR-05
    severity: warning
    disposition: open
    title: "The \"library missing from the tables\" decision is derived by matching message text"
  - id: IN-01
    severity: info
    disposition: open
    title: "A second `_sync_path_vars` while one is in flight is dropped without a log line"
  - id: IN-02
    severity: info
    disposition: open
    title: "`closeEvent` still joins the scan worker without a bound"
  - id: IN-03
    severity: info
    disposition: open
    title: "`_same_rel` folds case only on Windows, so a case-insensitive macOS volume reports a false clash"
  - id: IN-04
    severity: info
    disposition: open
    title: "A conflict-compare request is silently dropped if the dialog is Finishing when its build ends"
  - id: IN-05
    severity: info
    disposition: open
    title: "Restore with a blank folder box does nothing and gives no feedback"
  - id: IN-06
    severity: info
    disposition: open
    title: "The Qt teardown hook can hide a hung worker for 60 s per widget"
open: 11
total: 11
recorded: 2026-11-01T15:21:13.928Z
---

# Phase 12: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
