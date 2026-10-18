---
phase: 01-foundation
plan: 06
subsystem: testing
tags: [pytest, round-trip, corpus, zipfile, kicad, sexpr]

requires:
  - phase: 01-foundation
    provides: "fsutil decode/encode/atomic write (01-03), sexpr parse/apply_edits (01-02), frozen fixtures and UL zip (01-04), assert_tiles fixture"
provides:
  - "FOUND-03 corpus identity tests across live Custom, fixtures, UL zip members, owner's KiCad tables and Wurth"
affects: [phase-02, phase-03]

actuals:
  tokens: 3500
  tasks: 2
  commits: 2
plan_head_before: 900d4f08ed6f052b1764e50b325aad4f38af2335

tech-stack:
  added: []
  patterns:
    - "Collection-time pytest.param builders with zero-arg byte loaders and relative-POSIX ids"
    - "Opt-in sources gated by registered markers (wurth, local_kicad) with explicit skip reasons"
    - "Assertion messages carry ids, Issue codes and byte offsets only, never file content"

key-files:
  created:
    - tests/test_roundtrip_corpus.py
  modified: []

key-decisions:
  - "Zip members are read in memory only via zf.read after a ZipInfo.file_size cap check; no extraction anywhere"
  - "Owner's KiCad tables are read in place with no write leg; ids are local/<version>/<filename>"
  - "design-block-lib-table included under local_kicad as a read-only, in-memory extension beyond D-02"

requirements-completed: [FOUND-03]

duration: 10min
completed: 2026-10-18
status: complete
---

# Phase 1 Plan 06: Corpus Round-Trip Identity Summary

**Non-vacuous byte-identity tests (tiling, apply_edits no-op, bytes to SourceText to bytes, atomic-write leg) over live Custom/, frozen fixtures, UL zip members read in memory, the owner's real KiCad tables and Wurth, with marker-gated opt-in sources and explicit skip reasons**

## Performance

- **Duration:** ~10 min
- **Tasks:** 2
- **Files modified:** 1 (created)

## Accomplishments
- `tests/test_roundtrip_corpus.py` covers every repo-owned KiCad file: 9 sexpr fixtures, 5 lib-table fixtures and both KiCad members of the UL zip pass here; `custom/` params are generated at collection time and skip with a reason when the submodule is empty (this worktree), to be exercised by the orchestrator checkout.
- UL zip SHA-256 pinned, git-tracked check, and a size-cap boundary test (cap == largest member succeeds, cap-1 raises ValueError naming the member).
- `local_kicad` round-trips the owner's `sym-lib-table`, `fp-lib-table` and `design-block-lib-table` (7 files across 7.0, 8.0, 9.0 here) in memory; `wurth` round-trips files plus a 60 s parse budget test, both skipping with "WurthElektronik submodule not checked out" when empty.
- `-m "not wurth and not local_kicad"` runs the repo-owned corpus only (19 passed, 1 skipped for Custom). Full suite: 249 passed, 4 skipped.

## Task Commits

1. **Task 1: Repo-owned corpus identity** - `b460e0b` (test)
2. **Task 2: Opt-in local_kicad and wurth sources** - `cc36b6c` (test)

## Files Created/Modified
- `tests/test_roundtrip_corpus.py` - FOUND-03 corpus identity tests, zip helper with size cap, opt-in local KiCad and Wurth sources

## Decisions Made
See key-decisions; all follow the plan as specified.

## Deviations from Plan

None - plan executed exactly as written. Environment note: `env/` did not exist in the isolated worktree, so it was created with `py -3.14 -m venv env` and the pinned `requirements-dev.txt` installed as the plan instructs (env/ is gitignored, not staged).

## Issues Encountered
None. The Custom/ live-discovery leg could not be exercised here because the submodule is uninitialised in this worktree (by design); it must be re-run in the orchestrator checkout after merge.

## Known Stubs
None.

## Threat Flags
None.

## Self-Check: PASSED

- tests/test_roundtrip_corpus.py exists; commits b460e0b and cc36b6c are on the branch.
- Acceptance greps: `file_size` present, no `.extract(`/`.extractall(` call, SHA-256 string present; collect-only lists `fixture/sexpr/`, `fixture/tables/`, `zip/KiCADv6/` ids and `local/9.0/sym-lib-table` with no user path; `git status` shows no new files under tests/ or downloaded_examples/ beyond the plan file.

---
*Phase: 01-foundation*
*Completed: 2026-10-18*
