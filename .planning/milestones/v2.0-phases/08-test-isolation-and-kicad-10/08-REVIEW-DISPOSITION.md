---
phase: 08
review: 08-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "The live-Custom guard digests every file with no error handling, so a transient file can fail the run or error the whole suite"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Write detection moved from per-test assertions to one end-of-session check, so the offending test is never named and the damage has already happened"
  - id: WR-03
    severity: warning
    disposition: open
    title: "The gate checks only the KiCad major version, but the tests assert an exact format number and generator version"
  - id: WR-04
    severity: warning
    disposition: open
    title: "The gate can silently turn the entire real-binary tier into skips, and a failed probe is cached for the whole session"
  - id: IN-01
    severity: info
    disposition: open
    title: "`test_every_synthetic_library_loads_in_kicad_cli` passes file names that already include `.kicad_mod`"
  - id: IN-02
    severity: info
    disposition: open
    title: "The Wurth parse budget now scales with the corpus and is about 4.3 times looser than the measurement"
  - id: IN-03
    severity: info
    disposition: open
    title: "The README's list of read-only live-Custom tests is incomplete"
  - id: IN-04
    severity: info
    disposition: open
    title: "The UAT test removes a folder named `Custom` under a user-supplied path"
open: 8
total: 8
recorded: 2026-10-25T20:00:00.000Z
---

# Phase 08: Code Review Disposition

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
