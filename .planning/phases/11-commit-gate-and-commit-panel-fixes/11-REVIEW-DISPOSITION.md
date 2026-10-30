---
phase: 11
review: 11-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "A refused or failed commit loses its git output and the \"finish it by hand\" command immediately"
  - id: WR-02
    severity: warning
    disposition: open
    title: "A file that is both \"changed since install\" (or \"added by a fix\") and dirty before the import loses the pre-import warning"
  - id: WR-03
    severity: warning
    disposition: open
    title: "An unreadable Atomic_ library that links a committed file passes the gate with only an unseen INFO note"
  - id: IN-01
    severity: info
    disposition: open
    title: "Dead code left in the new and touched modules"
  - id: IN-02
    severity: info
    disposition: open
    title: "`_check_linked_symbols` takes 12 parameters, four of them output lists"
  - id: IN-03
    severity: info
    disposition: open
    title: "Probe supersede logic is duplicated and the two entry points disagree on a running probe"
  - id: IN-04
    severity: info
    disposition: open
    title: "`_EARLIER_SHOWN` is reused as the cap for gate failure lines"
  - id: IN-05
    severity: info
    disposition: open
    title: "\"(added by a fix)\" is wrong for linked files the user created themselves"
  - id: IN-06
    severity: info
    disposition: open
    title: "`gitops._env` promotes lower-case identity variables on every platform"
open: 9
total: 9
recorded: 2026-10-30T12:10:49.926Z
---

# Phase 11: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved.
