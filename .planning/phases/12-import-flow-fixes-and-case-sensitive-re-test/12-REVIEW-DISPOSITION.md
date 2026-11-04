---
phase: 12
review: 12-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "Start page adds a third \"Cancel\" button, and two opposite ones can be visible together (widens IN-01)"
  - id: IN-01
    severity: info
    disposition: open
    title: "Re-clicking the current section re-scrolls with the mouse only"
  - id: IN-02
    severity: info
    disposition: open
    title: "`_edit_size` comment says a user resize updates it; only leaving the page does"
  - id: IN-03
    severity: info
    disposition: open
    title: "Duplicate `<h3>` labels within one page are only caught by a test"
  - id: IN-04
    severity: info
    disposition: open
    title: "The screen-area fixture silently does nothing if the module is not yet imported"
  - id: WR-02
    severity: warning
    disposition: open
    title: "The three required-field hints duplicate the atomic-strip sentences instead of deriving from them"
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
recorded: 2026-11-04T11:11:32.641Z
---

# Phase 12: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| WR-02 | warning | open | - (not in the current review) |
| WR-03 | warning | open | - (not in the current review) |
| WR-04 | warning | open | - (not in the current review) |
| WR-05 | warning | open | - (not in the current review) |
| IN-05 | info | open | - (not in the current review) |
| IN-06 | info | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
