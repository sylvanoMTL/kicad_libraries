---
phase: 03-package-intake-and-naming
plan: 02
subsystem: testing
tags: [pytest, zipfile, ast, layering, fixtures, kicad]

requires:
  - phase: 02-foundation
    provides: kicad_files.parse_bytes / find_symbols / footprint_name / find_models used by the builder self-tests; tests/test_layering.py pattern
provides:
  - tests/zipfixtures.py shared byte builders (zips, KiCad, 3D, legacy formats, synthetic Custom/ layout) for plans 03-03 to 03-07
  - unpack_sample (D-17) turning the committed UL zip into loose files inside tmp_path
  - tests/test_importer_layering.py guard for every module under kicad_lib_manager/importer/
  - .gitattributes rule keeping downloaded_examples byte-exact
affects: [03-03, 03-04, 03-05, 03-06, 03-07, phase-07-adapters]

actuals:
  tokens: 6500
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Plain helper module tests/zipfixtures.py (no test_ prefix) imported with `from zipfixtures import ...` instead of conftest fixtures"
    - "Path-aware ast import walker with ALLOWED registry; unregistered importer modules are an error"

key-files:
  created:
    - tests/zipfixtures.py
    - tests/test_zipfixtures.py
    - tests/test_importer_layering.py
  modified:
    - .gitattributes

key-decisions:
  - "Builders live in tests/zipfixtures.py as plain functions rather than conftest fixtures (deviation from 03-PATTERNS.md): they are called many times per test with varying arguments, and later plans import them explicitly"
  - "lie_about_size and mark_encrypted locate headers through the end-of-central-directory record instead of searching for the first PK signature, so they cannot hit signature bytes inside compressed data"
  - "Layering guard registers importer.naming as importable from importer.candidate now (for plan 03-05 name_check); naming only imports models, so no cycle"

patterns-established:
  - "Synthetic guard self-tests (test_guard_*) always run; real-module tests (test_importer_*) skip only while kicad_lib_manager/importer/ is absent"
  - "Hostile fixtures are generated in memory or tmp_path at test time; nothing is committed and the committed UL zip is only read"

requirements-completed: [INTK-01]

coverage:
  - id: D1
    description: "Zip byte builders for duplicate, symlink, lying-size and encrypted members, each checked by a self-test"
    requirement: INTK-01
    verification:
      - kind: unit
        ref: "tests/test_zipfixtures.py#test_make_zip_keeps_duplicates,test_symlink_info_mode,test_lie_about_size,test_mark_encrypted"
        status: pass
    human_judgment: false
  - id: D2
    description: "unpack_sample writes the committed UL zip as loose files (full layout and flat KiCad-only) into tmp_path only, leaving the zip unchanged (D-17)"
    requirement: INTK-01
    verification:
      - kind: unit
        ref: "tests/test_zipfixtures.py#test_unpack_sample_full_layout,test_unpack_sample_flat_kicad_only,test_unpack_sample_writes_only_in_dest"
        status: pass
    human_judgment: false
  - id: D3
    description: "KiCad symbol/footprint builders round-trip through kicad_files; 3D and legacy byte constants carry their magic text; synthetic Custom/ layout and current library lists"
    requirement: INTK-01
    verification:
      - kind: unit
        ref: "tests/test_zipfixtures.py#test_symbol_lib_round_trip,test_footprint_round_trip,test_format_magic_bytes,test_write_custom_layout,test_current_custom_lists"
        status: pass
    human_judgment: false
  - id: D4
    description: "downloaded_examples/** -text attribute so vendor zips and STEP files are never line-ending converted"
    verification:
      - kind: other
        ref: "git check-attr text downloaded_examples/ul_CSD85301Q2.zip -> unset"
        status: pass
    human_judgment: false
  - id: D5
    description: "Importer layering guard: registry, relative-import resolution, forbidden absolute imports, bulk extraction ban (D-07), no code in __init__, proven on synthetic trees"
    requirement: INTK-01
    verification:
      - kind: unit
        ref: "tests/test_importer_layering.py#test_guard_clean_tree,test_guard_flags_violation,test_guard_resolves_relative_imports,test_guard_module_key_and_discover"
        status: pass
    human_judgment: false
  - id: D6
    description: "Real-module layering checks on kicad_lib_manager/importer/ (core modules exist, layering clean, no Qt loaded)"
    verification: []
    human_judgment: true
    rationale: "Skipped in this worktree because plan 03-01 builds the importer package in a sibling worktree; they run in the wave-1 post-merge test run, which the orchestrator must confirm"

duration: 25min
completed: 2026-10-19
status: complete
plan_head_before: b304331f05e02cd8e63fa6312463607f2c35335f
plan_head_after: f2060a16aa507c52c360ddafb9b7cc6a651db79f
commits: 3
---

# Phase 3 Plan 02: Test Infrastructure and Importer Layering Guard Summary

**Stdlib-only zip/KiCad/3D byte builders with a D-17 unpacker for the committed Ultra Librarian zip, a `downloaded_examples/** -text` attribute, and an ast-based layering guard whose rules are proven on synthetic trees**

## Performance

- **Duration:** about 25 min
- **Completed:** 2026-10-19
- **Tasks:** 3
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments

- `tests/zipfixtures.py` builds duplicate-name, symlink, lying-size and encrypted zips in memory, builds KiCad 6 and legacy-spelling symbol/footprint bytes, and exposes STEP, VRML and KiCad 5 legacy byte constants plus `write_custom_layout` for plan 03-06.
- `unpack_sample` (D-17) writes the committed UL zip into a caller-supplied `tmp_path` folder, either with its full archive layout or flat with only KiCad and 3D files; it asserts safe member names, opens targets with `xb`, and a self-test proves nothing lands outside the dest folders and the zip's sha256 is unchanged.
- `.gitattributes` gains `downloaded_examples/** -text` (`git check-attr text` reports `unset`).
- `tests/test_importer_layering.py` holds `ALLOWED` for the whole planned importer module set and `layering_errors(package_root)` enforcing registry membership, relative-import targets, forbidden absolute imports (PySide6, shiboken6, kicad_lib_manager), the D-07 ban on `extract`/`extractall`, and docstring-only `__init__.py`.

## Task Commits

1. **Task 1: Zip byte builders and the D-17 UL sample unpacker** - `67b5770` (test)
2. **Task 2: KiCad and 3D byte builders, Custom/ layout, downloaded_examples attribute** - `c53b78d` (test)
3. **Task 3: Importer layering guard with synthetic self-tests** - `f2060a1` (test)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `tests/zipfixtures.py` - shared builders and the D-17 unpacker (stdlib only)
- `tests/test_zipfixtures.py` - 12 self-tests for the builders
- `.gitattributes` - `downloaded_examples/** -text`
- `tests/test_importer_layering.py` - guard helpers, synthetic `test_guard_*` tests, real-module `test_importer_*` tests

## Decisions Made

- **PATTERNS.md deviation (as the plan requested to be recorded):** 03-PATTERNS.md maps the shared builders to `tests/conftest.py` fixtures (`ul_zip`, `make_zip`). They are a plain helper module `tests/zipfixtures.py` instead, because the builders are called repeatedly with different arguments and later plans import them explicitly. `tests/conftest.py` is unchanged.
- `lie_about_size` and `mark_encrypted` walk headers from the end-of-central-directory record rather than searching for the first signature bytes.
- The guard also covers the single-file `.extract` method alongside `.extractall`, with its own synthetic case.

## Deviations from Plan

### Auto-fixed Issues

None required fixes. Two small additions beyond the plan text:

- The guard's violation parametrization has eight cases instead of seven: an extra `bulk-extract` case covers `.extract`, which the rule already named. Plus one extra self-test, `test_guard_module_key_and_discover`, covers `module_key` and `discover`. Acceptance (at least 9 guard tests, none skipped) holds: 11 guard tests passed.
- `kicad_only` filtering in `unpack_sample` uses `PurePosixPath(name).suffix.casefold() in KICAD_SUFFIXES`, which is the plan's rule written directly.

**Total deviations:** 0 auto-fixed, 2 minor additive. **Impact on plan:** none.

## Test Results

- `pytest tests/test_zipfixtures.py`: 12 passed.
- `pytest tests/test_importer_layering.py tests/test_layering.py -rs`: 20 passed, 3 skipped. The 3 skips are exactly the real-module tests `test_importer_core_modules_exist`, `test_importer_modules_follow_layering` and `test_importer_modules_load_no_qt`: `kicad_lib_manager/importer/` is absent from this worktree (plan 03-01 builds it in a sibling worktree). They must run in the wave-1 post-merge test run.
- Spot check: with a throwaway importer package (`__init__.py` plus `package.py`, removed afterwards and never committed), `test_importer_modules_follow_layering` and `test_importer_modules_load_no_qt` passed; `test_importer_core_modules_exist` failed only because the other core modules were missing, as expected.
- Full suite: 538 passed, 12 skipped. Skips are submodule-dependent (`Custom/`, `WurthElektronik/KiCad-Library` not checked out in the worktree) plus the 3 importer real-module tests.
- Run with the main checkout interpreter by absolute path (no `env/` in the worktree).

## Issues Encountered

None. The sandbox rejected compound shell commands in the worktree, so commands were run as separate plain calls.

## Known Stubs

None.

## Threat Flags

None. No new network, auth or trust-boundary surface; T-03-31 (unpack_sample path asserts and dest containment), T-03-32 (nothing committed, `-text`) and T-03-34 (guard proven on synthetic trees, unregistered module is an error) are mitigated as planned.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 03-03 to 03-07 can `from zipfixtures import ...` and run `tests/test_importer_layering.py`.
- After plan 03-01 merges, the orchestrator's wave-1 post-merge run must show the three `test_importer_*` tests running (not skipped) and passing; if plan 03-01 adds a module not in `ALLOWED`, the guard names it.

## Self-Check: PASSED

- `tests/zipfixtures.py`, `tests/test_zipfixtures.py`, `tests/test_importer_layering.py`: FOUND
- `.gitattributes` contains `downloaded_examples/** -text`: FOUND
- Commits `67b5770`, `c53b78d`, `f2060a1`: FOUND on this branch

---
*Phase: 03-package-intake-and-naming*
*Completed: 2026-10-19*
