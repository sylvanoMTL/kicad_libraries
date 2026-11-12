---
phase: 03
review: 03-REVIEW.md
titles: json
findings:
  - id: CR-03
    severity: critical
    disposition: fixed
    title: "A single large quoted string costs about 2.7 GiB in the parser, so the 8 MiB cap and the node ceiling do not bound memory"
  - id: WR-01
    severity: warning
    disposition: open
    title: "A bare filename or IP address in the Datasheet field becomes a bogus manufacturer guess"
  - id: WR-02
    severity: warning
    disposition: open
    title: "The Windows reparse-point bit also matches OneDrive and cloud placeholders, so real files may be skipped silently"
  - id: WR-03
    severity: warning
    disposition: open
    title: "A write failure while staging is reported as a corrupt archive"
  - id: WR-04
    severity: warning
    disposition: open
    title: "`ImportCandidate` outlives the staged files it points at, and nothing says so"
  - id: WR-05
    severity: warning
    disposition: open
    title: "Package-level warnings never reach the candidate, so a skipped deep or unreadable part looks like \"nothing found\""
  - id: IN-01
    severity: info
    disposition: open
    title: "Dead parameter, oversized function and misleading `kind` on error packages"
  - id: IN-02
    severity: info
    disposition: open
    title: "Look-alike non-ASCII literals in source, and a stale \"stays ASCII\" comment"
  - id: IN-03
    severity: info
    disposition: open
    title: "Sanitised-name and model-basename collisions inside one candidate are not reported"
  - id: IN-04
    severity: info
    disposition: open
    title: "`test_ul_sample_leaves_repo_unchanged` is fragile"
  - id: IN-05
    severity: info
    disposition: open
    title: "Directory listings are fully materialised before the member cap is applied"
  - id: IN-06
    severity: info
    disposition: open
    title: "The layering guard only matches the attribute names `extract` and `extractall`"
  - id: CR-01
    severity: critical
    disposition: fixed
    title: "Untrusted KiCad files are parsed in memory with a 100 MB cap, a practical DoS (T-03-15 is not really closed)"
  - id: CR-02
    severity: critical
    disposition: fixed
    title: "`open_package` raises on corrupt LZMA members and on temp-folder failures, breaking its \"never raised\" contract"
open: 11
total: 14
recorded: 2026-10-19T16:35:17.760Z
---

# Phase 03: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| CR-03 | critical | fixed | plan 03-10 (linear string scan sexpr._string_end + linear unquote; string-heavy hostile tests); re-review pending |
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| WR-05 | warning | open | - |
| IN-01 | info | open | - |
| IN-02 | info | open | - |
| IN-03 | info | open | - |
| IN-04 | info | open | - |
| IN-05 | info | open | - |
| IN-06 | info | open | - |
| CR-01 | critical | fixed | plan 03-08 (text byte cap + node ceiling, verified in re-review); string-token residual tracked as CR-03 (not in the current review) |
| CR-02 | critical | fixed | plan 03-09 (_READ_ERRORS + intake.staging_failed, verified in re-review) (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
