---
phase: 12
review: 12-REVIEW.md
titles: json
findings:
  - id: WR-06
    severity: warning
    disposition: open
    title: "Help or F1 does not bring back a minimized User Guide"
  - id: WR-07
    severity: warning
    disposition: open
    title: "Source name goes unescaped into the Skip button text and tooltip"
  - id: WR-08
    severity: warning
    disposition: open
    title: "Test named for a late Skip click never exercises the late-click path"
  - id: WR-09
    severity: warning
    disposition: open
    title: "Main-window Help scrolls a visible guide back to the heading when the asked topic is the owner's own place, contradicting the documented \"only brought to the front\""
  - id: WR-10
    severity: warning
    disposition: open
    title: "Clicking the already-current asked row is neither saved nor clears the asked-topic flag, so the next Help pulls the owner to a different place"
  - id: IN-07
    severity: info
    disposition: open
    title: "Loose footprint files in a skipped source can only be cleared by a full Rescan, and this path is untested"
  - id: IN-08
    severity: info
    disposition: open
    title: "One ScanProgressDialog is created per scan and never released"
  - id: IN-09
    severity: info
    disposition: open
    title: "The import window's own-guide fallback now outlives the window it was opened from"
  - id: IN-10
    severity: info
    disposition: open
    title: "\"Stays open beside the other windows\" is only true for the dialogs that were made window-modal"
  - id: IN-11
    severity: info
    disposition: open
    title: "Test coupling and brittle negative assertions"
  - id: IN-12
    severity: info
    disposition: open
    title: "Any key press on the menu ends the hold mid-drag, including bare modifier keys"
  - id: IN-13
    severity: info
    disposition: open
    title: "Selected-row delegate depends on `option.widget` and on the click-through tests rely on sleeps"
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
open: 23
total: 23
recorded: 2026-11-11T00:30:24.246Z
---

# Phase 12: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| WR-08 | warning | open | - |
| WR-09 | warning | open | - |
| WR-10 | warning | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |
| IN-09 | info | open | - |
| IN-10 | info | open | - |
| IN-11 | info | open | - |
| IN-12 | info | open | - |
| IN-13 | info | open | - |
| WR-01 | warning | open | - (not in the current review) |
| IN-01 | info | open | - (not in the current review) |
| IN-02 | info | open | - (not in the current review) |
| IN-03 | info | open | - (not in the current review) |
| IN-04 | info | open | - (not in the current review) |
| WR-02 | warning | open | - (not in the current review) |
| WR-03 | warning | open | - (not in the current review) |
| WR-04 | warning | open | - (not in the current review) |
| WR-05 | warning | open | - (not in the current review) |
| IN-05 | info | open | - (not in the current review) |
| IN-06 | info | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
