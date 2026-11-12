---
phase: 13
review: 13-REVIEW.md
titles: json
findings:
  - id: CR-01
    severity: critical
    disposition: open
    title: "`_model_final_names`'s existing-model check is case-sensitive while the filesystem it protects is not — silent data loss"
  - id: WR-01
    severity: warning
    disposition: open
    title: "`migration.duplicate_write` can name the wrong colliding op when paths differ only by case"
  - id: IN-01
    severity: info
    disposition: open
    title: "No regression test exercises a model rename colliding with an untouched, unlinked model"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`CommitPanel._mark_files` never marks a deleted commit row as \"also changed before this import\""
open: 4
total: 4
recorded: 2026-11-12T10:17:25.568Z
---

# Phase 13: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-01 | critical | open | - |
| WR-01 | warning | open | - |
| IN-01 | info | open | - |
| WR-02 | warning | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
