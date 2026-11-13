---
phase: 13
review: 13-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "A weak vote from the owner's own libraries shadows a strong vote from KiCad's libraries"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`SiblingPick.weak` flags overwhelming letter-only majorities, and misses the equally coarse `ICM-` step"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Pin Atomic Libraries outcome is never shown in the Result view; only Generate Tables got the new status line"
  - id: IN-01
    severity: info
    disposition: open
    title: "A Skip pressed for a source that has no 3D model files is accepted and silently does nothing"
  - id: IN-02
    severity: info
    disposition: open
    title: "Garbled module docstring in gate.py"
  - id: IN-03
    severity: info
    disposition: open
    title: "Test hygiene nits in the new tests"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "`_model_final_names`'s existing-model check is case-sensitive while the filesystem it protects is not — silent data loss"
open: 6
total: 7
recorded: 2026-11-13T11:08:51.502Z
---

# Phase 13: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| CR-01 | critical | fixed | 13-22 (confirmed fixed by 13-REVIEW.md, 2026-11-12) (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
