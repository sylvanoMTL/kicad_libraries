---
phase: 04
review: 04-REVIEW.md
titles: json
findings:
  - id: WR-02
    severity: warning
    disposition: open
    title: "Creating a library when Custom/Symbols is missing fails late with a bare \"No such file or directory\""
  - id: WR-04
    severity: warning
    disposition: open
    title: "build_plan is a 528-line function with about a dozen nested closures"
  - id: WR-06
    severity: warning
    disposition: open
    title: "Package-level warnings are still lost when detection finds nothing (the WR-03 fix covers only the found-candidate path)"
  - id: IN-01
    severity: info
    disposition: open
    title: "A no-op plan reports \"Everything is already installed\" without re-checking the disk"
  - id: IN-02
    severity: info
    disposition: open
    title: "Small duplication in the install modules"
  - id: IN-03
    severity: info
    disposition: open
    title: "The opt-in UAT test deletes whatever `<KICAD_IMPORT_UAT_DIR>/Custom` holds"
  - id: IN-04
    severity: info
    disposition: open
    title: "The blank-means-not-set rule covers five fields only; other Qt-sourced options still misbehave on \"\" and non-blank values keep stray spaces"
  - id: IN-05
    severity: info
    disposition: open
    title: "Early aborts after the backup folder exists leave it behind unreported and unpruned"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "apply_plan has no exception safety, so an unexpected exception leaves a partial install and no rollback"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "A file changed between the stale-plan hash check and the write is silently overwritten, and the install reports success (TOCTOU)"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "prune_install_backups can delete the backup folder that was just created"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "WR-05 (package-level warnings) is only half handled"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "An empty string in InstallOptions blanks the vendor value instead of meaning \"not set\""
open: 8
total: 13
recorded: 2026-10-20T11:16:16.222Z
---

# Phase 04: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-02 | warning | open | - |
| WR-04 | warning | open | - |
| WR-06 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| CR-01 | critical | fixed | 04-11-PLAN.md (4a57d26) (not in the current review) |
| CR-02 | critical | fixed | 04-13-PLAN.md (2a2a1de) (not in the current review) |
| WR-01 | warning | fixed | 04-11-PLAN.md (727db69) (not in the current review) |
| WR-03 | warning | fixed | 04-12-PLAN.md (d33fa20) (not in the current review) |
| WR-05 | warning | fixed | 04-12-PLAN.md (bebcbe8) (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
