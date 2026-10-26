---
phase: 09
review: 09-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "\"Preview & apply\" button text loses the ampersand and registers Alt+Space"
  - id: WR-02
    severity: warning
    disposition: open
    title: "A NUL character in a footprint's 3D model path aborts the whole scan"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Two symbols sharing one footprint can attach two different models to it"
  - id: WR-04
    severity: warning
    disposition: open
    title: "A refused group leaves its model copies registered, so a later footprint links a file that is never copied"
  - id: IN-01
    severity: info
    disposition: open
    title: "`check_symbol` and parts of `FootprintTarget` are used only by tests"
  - id: IN-02
    severity: info
    disposition: open
    title: "The Custom model listing and the model prefix are defined three times"
  - id: IN-03
    severity: info
    disposition: open
    title: "Foundation modules import size caps from the importer package"
  - id: IN-04
    severity: info
    disposition: open
    title: "`suggest.manufacturer_token` repeats `manufacturers.fold`"
  - id: IN-05
    severity: info
    disposition: open
    title: "Unreachable `bad` branch in the sexpr tokenizer"
  - id: IN-06
    severity: info
    disposition: open
    title: "User Guide Status column text is out of date"
  - id: IN-07
    severity: info
    disposition: open
    title: "`_group_violation` and `repo_context` are hard to follow"
  - id: IN-08
    severity: info
    disposition: open
    title: "Backslash separators are judged inconsistently for model paths"
open: 12
total: 12
recorded: 2026-10-26T14:38:40.379Z
---

# Phase 09: Code Review Disposition

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
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |
| IN-08 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
