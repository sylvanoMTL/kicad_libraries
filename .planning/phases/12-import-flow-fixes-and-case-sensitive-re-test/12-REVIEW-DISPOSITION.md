---
phase: 12
review: 12-REVIEW.md
titles: json
findings:
  - id: WR-02
    severity: warning
    disposition: open
    title: "The three required-field hints duplicate the atomic-strip sentences instead of deriving from them"
  - id: IN-01
    severity: info
    disposition: open
    title: "Two buttons labelled \"Cancel\" and the help text uses the word for both"
  - id: IN-02
    severity: info
    disposition: open
    title: "Cancel (and Install Part) are missing from the hand-built tab order"
  - id: IN-03
    severity: info
    disposition: open
    title: "`test_install_progress_and_lock` assertion was weakened"
  - id: IN-04
    severity: info
    disposition: open
    title: "The toolbar Help button cannot be reached with Tab; F1 is the only keyboard path"
  - id: WR-01
    severity: warning
    disposition: open
    title: "Plain-name rule (G-12-5) still leaks `kicad_common.json` to the user through interpolated paths"
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
recorded: 2026-11-03T20:26:25.776Z
---

# Phase 12: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-02 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| WR-01 | warning | open | - (not in the current review) |
| WR-03 | warning | open | - (not in the current review) |
| WR-04 | warning | open | - (not in the current review) |
| WR-05 | warning | open | - (not in the current review) |
| IN-05 | info | open | - (not in the current review) |
| IN-06 | info | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
