---
phase: 05
review: 05-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "`add_library_entries` reports \"already listed\" when the managed entry points at a different library"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Post-install table write goes to the process working directory when the Destination box is empty"
  - id: WR-03
    severity: warning
    disposition: open
    title: "A one-off conflict build can overlap Install, although the code says it cannot"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "Install worker reads `self._plan` from the worker thread; `open_path` has no install guard"
    note: "Phase 6 plan 06-08: the install worker gets the plan captured at the click; open_path refuses while installing or committing"
  - id: WR-05
    severity: warning
    disposition: open
    title: "GUI thread blocks on worker `wait()` for as long as a kicad-cli call (up to 60 s)"
  - id: WR-06
    severity: warning
    disposition: open
    title: "`kicad_common.json` write: stale content after the confirm dialog, and a KiCad-running check that does not gate the write"
  - id: IN-01
    severity: info
    disposition: open
    title: "Invisible character as a source literal"
  - id: IN-02
    severity: info
    disposition: open
    title: "Three near-identical elided-label classes"
  - id: IN-03
    severity: info
    disposition: open
    title: "Dead field and unused parameters"
  - id: IN-04
    severity: info
    disposition: open
    title: "Truncation wording and an oversized first line in `cap_lines`"
  - id: IN-05
    severity: info
    disposition: open
    title: "Worker threads are never released while the dialog lives"
  - id: IN-06
    severity: info
    disposition: open
    title: "Package-derived names are used in tooltips (Qt rich-text heuristic)"
  - id: IN-07
    severity: info
    disposition: open
    title: "`self.result` shadows `QDialog.result()`"
  - id: IN-08
    severity: info
    disposition: open
    title: "Test hygiene"
---

# Phase 05 code review disposition

One row per finding in 05-REVIEW.md. Every finding starts as `open`; change a row when it is fixed, deferred or accepted.

| ID | Severity | Disposition | Title |
|----|----------|-------------|-------|
| WR-01 | warning | open | `add_library_entries` reports "already listed" when the managed entry points at a different library |
| WR-02 | warning | open | Post-install table write goes to the process working directory when the Destination box is empty |
| WR-03 | warning | open | A one-off conflict build can overlap Install, although the code says it cannot |
| WR-04 | warning | fixed | Install worker reads `self._plan` from the worker thread; `open_path` has no install guard |
| WR-05 | warning | open | GUI thread blocks on worker `wait()` for as long as a kicad-cli call (up to 60 s) |
| WR-06 | warning | open | `kicad_common.json` write: stale content after the confirm dialog, and a KiCad-running check that does not gate the write |
| IN-01 | info | open | Invisible character as a source literal |
| IN-02 | info | open | Three near-identical elided-label classes |
| IN-03 | info | open | Dead field and unused parameters |
| IN-04 | info | open | Truncation wording and an oversized first line in `cap_lines` |
| IN-05 | info | open | Worker threads are never released while the dialog lives |
| IN-06 | info | open | Package-derived names are used in tooltips (Qt rich-text heuristic) |
| IN-07 | info | open | `self.result` shadows `QDialog.result()` |
| IN-08 | info | open | Test hygiene |

## Notes

- WR-04: Phase 6 plan 06-08: the install worker gets the plan captured at the click; open_path refuses while installing or committing.
