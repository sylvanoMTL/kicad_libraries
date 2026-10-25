---
phase: 01
review: 01-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: deferred
    title: "`find_symbols`, `find_property` and `lib_table_entries` do not validate the kind of the name and value token"
  - id: WR-02
    severity: warning
    disposition: deferred
    title: "`unquote` decodes only five escapes, so `quote(unquote(x))` can change a foreign value"
  - id: WR-03
    severity: warning
    disposition: deferred
    title: "Any `PermissionError` from `os.replace` is reported as \"file is in use\", after about 1 s of pointless retries"
  - id: WR-04
    severity: warning
    disposition: deferred
    title: "`atomic_write_text` and `encode_source` can raise, which breaks the \"return an Issue\" contract"
  - id: WR-05
    severity: warning
    disposition: deferred
    title: "The mixed-EOL warning text is wrong for lone-CR files"
  - id: WR-06
    severity: warning
    disposition: deferred
    title: "`test_ul_zip_is_pinned_and_tracked` calls `git` without the `needs_git` guard"
  - id: WR-07
    severity: warning
    disposition: deferred
    title: "`local_kicad` tests are documented as opt-in but run on every default invocation"
  - id: IN-01
    severity: info
    disposition: deferred
    title: "`backup_file` reports failure after a complete backup exists, and copies the read-only attribute"
  - id: IN-02
    severity: info
    disposition: deferred
    title: "`Severity(str, Enum)` formats as `Severity.INFO` on Python 3.12+"
  - id: IN-03
    severity: info
    disposition: deferred
    title: "Scanner skips `tests/` but not `downloaded_examples/`, which will hold vendor KiCad files"
  - id: IN-04
    severity: info
    disposition: deferred
    title: "A bare `(name)` / `(uri)` in a lib entry is classified as a flag"
  - id: IN-05
    severity: info
    disposition: deferred
    title: "Environment-coupled and wall-clock tests are brittle"
  - id: IN-06
    severity: info
    disposition: deferred
    title: "Fixtures are protected from EOL conversion, but the zip and temp leftovers are not"
  - id: IN-07
    severity: info
    disposition: deferred
    title: "Live-data tests encode content assumptions about the Custom submodule"
open: 0
total: 14
recorded: 2026-10-18T16:25:45.595Z
---

# Phase 01: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | deferred | Scheduled in Phase 2: plan 02-03 Task 1 adds `_is_token` and the token-kind guards in `find_symbols`, `find_property` and the lib-entry reader. Set to fixed when 02-03-SUMMARY.md records it. |
| WR-02 | warning | deferred | Deferred to Phase 4. Phase 2 never re-quotes a decoded value: external table bytes are kept verbatim (D-10) and generated values are quoted from repo file names. Its only use of `unquote` is D-03/D-08 name and URI matching, and KiCad's own writer emits only escapes `unquote` decodes, so a mismatch needs a hand-typed hex or octal escape. Phase 4 decodes and rewrites vendor values and must fix or guard `unquote` there. |
| WR-03 | warning | deferred | Scheduled in Phase 2: plan 02-08 Task 1 returns `fs.not_a_file` for a folder target before any retry and re-checks write access after the retries (`fs.read_only`). Set to fixed when 02-08-SUMMARY.md records it. |
| WR-04 | warning | deferred | Scheduled in Phase 2: plan 02-08 Task 1 returns `fs.bad_encoding` from `atomic_write_text` instead of raising. Set to fixed when 02-08-SUMMARY.md records it. |
| WR-05 | warning | deferred | Scheduled in Phase 2: plan 02-08 Task 1 builds the `fs.mixed_eol` text from the CRLF/LF/CR counts. Set to fixed when 02-08-SUMMARY.md records it. |
| WR-06 | warning | deferred | Deferred to a later quick task: test hygiene in `tests/test_roundtrip_corpus.py`, which no Phase 2 plan touches and which is not code Phase 2 rewires. Git is always on PATH on the owner's machine, so the test cannot error there. |
| WR-07 | warning | deferred | Deferred to a later quick task: marker policy in `pyproject.toml`, outside the modules Phase 2 rewires. The `local_kicad` tests only read the owner's `sym-lib-table` and write nothing. |
| IN-01 | info | deferred | Scheduled in Phase 2: plan 02-08 Task 1 makes `copystat` best-effort and leaves backups writable. Set to fixed when 02-08-SUMMARY.md records it. |
| IN-02 | info | deferred | Scheduled in Phase 2: plan 02-09 Task 1 adds `Severity.__str__` returning the value (works on Python 3.10 and 3.12+). Set to fixed when 02-09-SUMMARY.md records it. |
| IN-03 | info | deferred | Scheduled in Phase 2: plan 02-09 Task 1 adds `downloaded_examples` to `SKIP_DIRS` with a regression test. Set to fixed when 02-09-SUMMARY.md records it. |
| IN-04 | info | deferred | Scheduled in Phase 2: plan 02-03 Task 1 routes a value-less `(name)` / `(uri)` to `extras`, never `flags`. Set to fixed when 02-03-SUMMARY.md records it. |
| IN-05 | info | deferred | Deferred to a later quick task: brittle-test hygiene (installed-version pins, wall-clock budgets, POSIX root) in tests whose code under test Phase 2 does not rewire. The owner runs Windows without root, so none of them misfires today. |
| IN-06 | info | deferred | Deferred to Phase 4. Ignoring `.*.tmp` in `Custom` needs its own `Custom` commit, and D-17 limits Phase 2's only `Custom` commit to the five footprint files. Every Phase 2 commit stages explicit paths, so a leftover temp file cannot be committed. Phase 4 writes into `Custom` transactionally and should add the ignore rules and `*.zip binary` then. |
| IN-07 | info | deferred | Deferred to Phase 4. Phase 2 changes no symbol in `Custom` (HARD-09 edits five footprints only), so the live symbol assertions stay true. Phase 4 installs new symbols into `Custom` and must turn them into warnings or a marked live-corpus test then. |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
