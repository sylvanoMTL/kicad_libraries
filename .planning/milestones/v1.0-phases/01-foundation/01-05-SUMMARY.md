---
phase: 01-foundation
plan: 05
subsystem: testing
tags: [kicad, sexpr, locators, lib-table, eol, bom, atomic-write, pytest, layering]

requires:
  - phase: 01-foundation
    provides: "sexpr parser/apply_edits (01-03), fsutil decode/encode/atomic write/normalize_eol (01-02), frozen fixtures (01-04), tracer find_symbols/find_property (01-01)"
provides:
  - "kicad_files read side: LoadedFile, parse_bytes, load, find_symbol, NameRef/footprint_name, ModelRef/find_models, LibEntry/lib_table_entries"
  - "Mechanical Qt-free and downward-only import checks (tests/test_layering.py)"
  - "FOUND-04 targeted-edit suite across fixtures, live Custom, UL zip member, EOL x BOM matrix, inserts, footprint/model/table edits, interrupted write"
affects: [02-tables, 03-import-pipeline, 04-install-write-side]

actuals:
  tokens: 21000
  tasks: 2
  commits: 2

plan_head_before: 900d4f08ed6f052b1764e50b325aad4f38af2335
plan_head_after: 26e58ab0f02266c166164a0a6649b3a8d3895357

tech-stack:
  added: []
  patterns:
    - "Locators return span-carrying Node refs; edits are zero/replace-width Edits applied with apply_edits"
    - "Loaders return Issue instead of raising (sexpr.* / fs.* codes, text starting 'Could not')"
    - "AST + subprocess layering test guards foundation modules"

key-files:
  created:
    - tests/test_kicad_files.py
    - tests/test_layering.py
  modified:
    - kicad_lib_manager/kicad_files.py
    - tests/test_edits.py

key-decisions:
  - "_top_level takes a head predicate (not a heads tuple) so lib tables match any head ending in _lib_table"
  - "LibEntry keeps flags (single-atom children), unknown children as extras, and value_nodes for Phase 2 span edits; first occurrence of a known field wins"

requirements-completed: [FOUND-04, FOUND-03]

duration: 25min
completed: 2026-10-18
status: complete
---

# Phase 1 Plan 5: kicad_files read side and FOUND-04 edit suite Summary

**Span-exact locators for symbols, properties, footprint names, 3D models and lib-table entries, with Issue-returning loaders, enforced layering, and a 27-case targeted-edit suite proving one edit changes only its span while EOL and BOM survive.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- D-12 read side complete in `kicad_lib_manager/kicad_files.py`: `parse_bytes`/`load` (Issue on undecodable, unreadable or unparseable input), exact `find_symbol`, `footprint_name` (quoted or bare atom, `footprint` or legacy `module`), `find_models` (document order), `lib_table_entries` (fields in any order, flags and unknown children kept).
- `tests/test_layering.py`: a `-I` subprocess proves models/sexpr/fsutil/kicad_files load no PySide6/shiboken6, and AST checks pin the downward-only import graph and an empty package `__init__`.
- `tests/test_edits.py` expanded: Value edit on all 5 symbol fixtures, live Custom symbols (skipped here, see below) and the UL zip symbol member; 12-case EOL x BOM x site matrix through `atomic_write_bytes` (mixed-EOL warning, no normalisation); property insert converted with `normalize_eol` for CRLF and LF files; footprint-name, model-path and lib-table descr edits; interrupted write returning `fs.locked` with the original byte-identical and no temp left.
- Full suite: 290 passed, 4 skipped (all four skips are the "Custom submodule not checked out" reason in this isolated worktree).

## Task Commits

1. **Task 1: kicad_files read side and layering checks** - `6948282` (feat)
2. **Task 2: full FOUND-04 targeted-edit suite** - `26e58ab` (test)

## Files Created/Modified

- `kicad_lib_manager/kicad_files.py` - locators, dataclasses and loaders (D-12)
- `tests/test_kicad_files.py` - locator tests on fixtures, UL zip member, loader Issues, live Custom invariants
- `tests/test_layering.py` - Qt-free subprocess check and AST import-direction checks
- `tests/test_edits.py` - FOUND-04 suite; tracer tests kept

## Decisions Made

- `_top_level` accepts a predicate so `sym_lib_table`, `fp_lib_table` and `design_block_lib_table` share one finder.
- A `(lib ...)` child counts as a flag when it is a list with only its head atom (`(disabled)`, `(hidden)`); any other non-field child is kept in `extras`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Helper name collision in tests/test_edits.py**
- **Found during:** Task 2
- **Issue:** The tracer tests already defined `_assert_only_span_changed(old, new, start, end)` over bytes; the plan requires the same name with a different (str, 5-argument) signature.
- **Fix:** Renamed the tracer helper to `_assert_tracer_span_changed` and updated its two call sites; tracer test names and assertions are otherwise unchanged. The new helper has the planned name and signature.
- **Files modified:** tests/test_edits.py
- **Committed in:** 26e58ab

**2. [Environment] No `env/` in the isolated worktree**
- Created `env/` with `py -3.14 -m venv env` and installed `requirements-dev.txt` (pinned, plan-authorised); `env/` is gitignored and not staged.

**3. Live Custom coverage verified out-of-tree**
- `Custom/` is uninitialised in this worktree (and `git submodule update` is forbidden), so live-Custom tests skip here. To still exercise them I copied the orchestrator checkout's `Custom/` (read-only copy) plus the package and tests into the scratchpad and ran `tests/test_edits.py` and `tests/test_kicad_files.py` there: 75 passed, 0 skipped. The orchestrator should re-run `pytest tests/test_kicad_files.py tests/test_edits.py -q -rs` after merge to confirm no Custom skip in the real checkout.

---

**Total deviations:** 1 auto-fixed (Rule 3), 2 environment notes. **Impact:** none on behavior; no defects found in sexpr.py, fsutil.py or the Plan 01 tracer code.

## Issues Encountered

- First matrix run failed because my "mixed" variant had a 5/5 CRLF/LF tie (which defaults to LF by design); fixed the test data to an 8/2 CRLF majority. Test-data bug, not a code defect.
- TDD RED for Task 1 was an ImportError at collection (new names absent), not an assertion failure; the tests were written first but the RED evidence is not assertion-level.

## Known Stubs

None.

## Threat Flags

None. Threat register T-01-17 to T-01-20 mitigations are covered by tests (exact/direct/top-level matching, EOL/BOM byte-identity, `fs.locked` interrupted write, layering checks).

## Next Phase Readiness

Read side and edit proofs are ready for Phase 2 (table merge using `lib_table_entries` + `value_nodes`) and Phase 4 write-side work. Plan 01-06 can build on these locators.

## Self-Check: PASSED

- kicad_lib_manager/kicad_files.py, tests/test_kicad_files.py, tests/test_layering.py, tests/test_edits.py exist
- Commits 6948282 and 26e58ab are ancestors of HEAD
- `git status` clean apart from this SUMMARY; Custom/, tests/fixtures and downloaded_examples untouched

---
*Phase: 01-foundation*
*Completed: 2026-10-18*
