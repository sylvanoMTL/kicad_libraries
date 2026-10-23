---
phase: 07
review: 07-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "21 tests fail because they copy the live `Custom/` submodule, whose checkout already holds the UL sample part"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Vendor-controlled property values now reach Qt tooltips, which auto-detect rich text"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Marker members beyond `MAX_MARKERS` are dropped silently, in archive order rather than shallowest first"
  - id: WR-04
    severity: warning
    disposition: open
    title: "The SamacSys \"other-CAD folders\" summary reports a file count that is not the folders' file count"
  - id: IN-01
    severity: info
    disposition: open
    title: "Dead re-exports and an unused import in `adapters/base.py`"
  - id: IN-02
    severity: info
    disposition: open
    title: "Scoring weights are hard-coded twice in each adapter"
  - id: IN-03
    severity: info
    disposition: open
    title: "`is_protected` compares standard field names case-sensitively but `ki_` case-insensitively"
  - id: IN-04
    severity: info
    disposition: open
    title: "`_kicad_base` takes the first \"kicad\" path segment, so an outer folder named `KiCad` skews the summary and the +1 score"
open: 8
total: 8
recorded: 2026-10-23T12:36:33.169Z
---

# Phase 07: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
