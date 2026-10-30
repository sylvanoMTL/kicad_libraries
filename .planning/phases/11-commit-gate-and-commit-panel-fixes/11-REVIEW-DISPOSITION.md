---
phase: 11
review: 11-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "A kept refusal survives the Check again that follows an atomic fix"
  - id: IN-01
    severity: info
    disposition: open
    title: "`refusal_summary` finds the \"folder could not be listed\" problem by searching its text"
  - id: IN-02
    severity: info
    disposition: open
    title: "`combined_view` reports \"diff\" when one half is an error"
  - id: IN-03
    severity: info
    disposition: open
    title: "The case-folding branch of `_env` cannot run in production"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "A file that is both \"changed since install\" (or \"added by a fix\") and dirty before the import loses the pre-import warning"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "An unreadable Atomic_ library that links a committed file passes the gate with only an unseen INFO note"
  - id: IN-04
    severity: info
    disposition: fixed
    title: "`_EARLIER_SHOWN` is reused as the cap for gate failure lines"
  - id: IN-05
    severity: info
    disposition: fixed
    title: "\"(added by a fix)\" is wrong for linked files the user created themselves"
  - id: IN-06
    severity: info
    disposition: fixed
    title: "`gitops._env` promotes lower-case identity variables on every platform"
open: 4
total: 9
recorded: 2026-10-30T20:06:58.288Z
---

# Phase 11: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| WR-02 | warning | fixed | - (not in the current review) |
| WR-03 | warning | fixed | - (not in the current review) |
| IN-04 | info | fixed | - (not in the current review) |
| IN-05 | info | fixed | - (not in the current review) |
| IN-06 | info | fixed | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
