| IN-01 |  | fixed | 13-22 (confirmed fixed by 13-REVIEW.md, 2026-11-12) || CR-01 |  | fixed | 13-22 (confirmed fixed by 13-REVIEW.md, 2026-11-12) |---
phase: 13
review: 13-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "`migration.rename_would_overwrite` names only the write op's destination, not the rename's source"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "`_model_final_names`'s existing-model check is case-sensitive while the filesystem it protects is not — silent data loss"
  - id: IN-01
    severity: info
    disposition: fixed
    title: "No regression test exercises a model rename colliding with an untouched, unlinked model"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`CommitPanel._mark_files` never marks a deleted commit row as \"also changed before this import\""
open: 2
total: 4
recorded: 2026-11-12T12:08:23.783Z
---

# Phase 13: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| CR-01 | critical | open | - (not in the current review) |
| IN-01 | info | open | - (not in the current review) |
| WR-02 | warning | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
