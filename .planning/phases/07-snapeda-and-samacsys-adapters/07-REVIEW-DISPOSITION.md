---
phase: 07
review: 07-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "A model result that arrives for an older package leaves Install stuck on \"Updating preview...\""
  - id: WR-02
    severity: warning
    disposition: open
    title: "A failed model read for an older package writes its error onto the current package's model row"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Two dialog tests fail whenever the live `Custom/` checkout already holds the UL sample part (carry-over of first-review WR-01)"
  - id: IN-01
    severity: info
    disposition: open
    title: "`help_dialog` now imports the whole import dialog module for one string constant"
  - id: IN-02
    severity: info
    disposition: open
    title: "`open_model_source` puts the full path into its `intake.not_found` text, unlike the \"file names only\" rule `attach_models` states"
  - id: WR-04
    severity: warning
    disposition: open
    title: "The SamacSys \"other-CAD folders\" summary reports a file count that is not the folders' file count"
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
recorded: 2026-10-24T08:38:49.971Z
---

# Phase 07: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| WR-04 | warning | open | - (not in the current review) |
| IN-03 | info | open | - (not in the current review) |
| IN-04 | info | open | - (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
