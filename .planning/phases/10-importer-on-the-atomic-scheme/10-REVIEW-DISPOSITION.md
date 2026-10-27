---
phase: 10
review: 10-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "The package family is guessed from an arbitrary official footprint and written into the description, tags and keywords"
  - id: WR-01
    severity: warning
    disposition: open
    title: "Module-level footprint caches are mutated from several worker threads with no lock"
  - id: WR-02
    severity: warning
    disposition: open
    title: "The keyword \"CAN\" is generated from the English word \"can\""
  - id: WR-03
    severity: warning
    disposition: open
    title: "The manufacturer owner chain is not validated, and a cycle loops forever"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Vendor text is set as a tooltip unescaped in several new or extended places, while the library tooltip is escaped"
  - id: WR-05
    severity: warning
    disposition: open
    title: "After a new symbol library is installed, the shared footprint library is never checked against fp-lib-table"
  - id: IN-01
    severity: info
    disposition: open
    title: "Mutable and duplicated \"no planned footprints\" defaults"
  - id: IN-02
    severity: info
    disposition: open
    title: "Sibling index silently reads nothing from libraries with other indentation"
  - id: IN-03
    severity: info
    disposition: open
    title: "The official footprint picker ranking is built once per package and goes stale"
open: 9
total: 9
recorded: 2026-10-27T23:17:47.207Z
---

# Phase 10: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
