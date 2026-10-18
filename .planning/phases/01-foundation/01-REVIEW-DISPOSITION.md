---
phase: 01
review: 01-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "`find_symbols`, `find_property` and `lib_table_entries` do not validate the kind of the name and value token"
  - id: WR-02
    severity: warning
    disposition: open
    title: "`unquote` decodes only five escapes, so `quote(unquote(x))` can change a foreign value"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Any `PermissionError` from `os.replace` is reported as \"file is in use\", after about 1 s of pointless retries"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`atomic_write_text` and `encode_source` can raise, which breaks the \"return an Issue\" contract"
  - id: WR-05
    severity: warning
    disposition: open
    title: "The mixed-EOL warning text is wrong for lone-CR files"
  - id: WR-06
    severity: warning
    disposition: open
    title: "`test_ul_zip_is_pinned_and_tracked` calls `git` without the `needs_git` guard"
  - id: WR-07
    severity: warning
    disposition: open
    title: "`local_kicad` tests are documented as opt-in but run on every default invocation"
  - id: IN-01
    severity: info
    disposition: open
    title: "`backup_file` reports failure after a complete backup exists, and copies the read-only attribute"
  - id: IN-02
    severity: info
    disposition: open
    title: "`Severity(str, Enum)` formats as `Severity.INFO` on Python 3.12+"
  - id: IN-03
    severity: info
    disposition: open
    title: "Scanner skips `tests/` but not `downloaded_examples/`, which will hold vendor KiCad files"
  - id: IN-04
    severity: info
    disposition: open
    title: "A bare `(name)` / `(uri)` in a lib entry is classified as a flag"
  - id: IN-05
    severity: info
    disposition: open
    title: "Environment-coupled and wall-clock tests are brittle"
  - id: IN-06
    severity: info
    disposition: open
    title: "Fixtures are protected from EOL conversion, but the zip and temp leftovers are not"
  - id: IN-07
    severity: info
    disposition: open
    title: "Live-data tests encode content assumptions about the Custom submodule"
open: 14
total: 14
recorded: 2026-10-18T16:25:45.595Z
---

# Phase 01: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| WR-06 | warning | open | - |
| WR-07 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| IN-07 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
