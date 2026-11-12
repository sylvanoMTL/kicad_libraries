---
phase: 06
review: 06-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "A commit timeout is reported as \"nothing was committed\" without checking HEAD"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "Parent commit preview differs from the message actually committed when Custom is not yet in the parent's HEAD"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "The \"Finish it by hand\" command is mis-quoted for the primary platform and for shell metacharacters"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "A planned file that is unchanged against HEAD turns a correct commit into an ERROR and silently skips the parent bump"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "After a precheck refusal the panel returns to \"ready\" with a stale probe and cannot recover"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "`apply_probe` re-ticks the parent checkbox on every probe"
  - id: IN-02
    severity: info
    disposition: fixed
    title: "The dialog and main window cannot be closed during the read-only probe"
  - id: IN-03
    severity: info
    disposition: fixed
    title: "`run_git` shadows a builtin, and `_env` drops identity-related `GIT_*` variables"
open: 0
total: 8
recorded: 2026-10-22T22:06:17.785Z
---

# Phase 06: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | fixed | - |
| WR-02 | warning | fixed | - |
| WR-03 | warning | fixed | - |
| WR-04 | warning | fixed | - |
| WR-05 | warning | fixed | - |
| IN-01 | info | fixed | - |
| IN-02 | info | fixed | - |
| IN-03 | info | fixed | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
