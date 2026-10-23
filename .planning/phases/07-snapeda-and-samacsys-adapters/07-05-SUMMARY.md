---
phase: 07-snapeda-and-samacsys-adapters
plan: 05
subsystem: importer-intake
tags: [samacsys, component-search-engine, part_info, intake, suggest, pytest]

requires:
  - phase: 07-snapeda-and-samacsys-adapters
    provides: "07-04 Package.markers / marker_text; 07-03 planner meta.mpn fallback; 07-02 FieldRules"
provides:
  - "SamacSysAdapter: scores generator, part_info.txt, license.txt, version.bin, KiCad-beside-other-folders, LIB_ prefix (D-14, D-15)"
  - "parse_part_info: in-memory, 100 lines, 40-char keys, 200-char control-stripped values (D-13)"
  - "D-16: other-CAD files collapse to one INFO intake.ignored_members line, swapped into package.issues idempotently"
  - "Detection.hints / ignored_note / notes; locate fills PartMeta manufacturer, single-symbol MPN and category from hints (D-11)"
  - "suggest: PS -> PowerSupply, RECOM aliases, PART_CATEGORY_TYPE, type_choice(reference, category); synthetic part suggests PowerSupply_SubCategory_RECOM"
affects: [07-06 real-sample tests]

actuals:
  tokens: 21000
  tasks: 2
  commits: 4

plan_head_before: a67b8ac5b41d2b6d53afde0feec5ea335b7d9610
plan_head_after: e56719ae07d48a16a6c0d0d5081527bb77985956

tech-stack:
  added: []
  patterns:
    - "Adapter-computed replacement note applied by detect_candidate before locate (D-16)"
    - "Package metadata as PartHints that only fill gaps; symbol properties win"

key-files:
  created:
    - kicad_lib_manager/importer/adapters/samacsys.py
    - tests/test_samacsys_adapter.py
  modified:
    - kicad_lib_manager/importer/adapters/base.py
    - kicad_lib_manager/importer/detect.py
    - kicad_lib_manager/importer/candidate.py
    - kicad_lib_manager/importer/suggest.py
    - tests/vendorfixtures.py
    - tests/test_adapters.py
    - tests/test_naming_suggest.py

key-decisions:
  - "The D-16 summary is computed by the SamacSys adapter and swapped into package.issues by detect_candidate; other vendors' notes are untouched"
  - "Detection.notes carries adapter Issues (malformed part_info.txt) so D-13's INFO-never-refusal needs no wider Adapter protocol"
  - "A part_info MPN applies only to a single-symbol package; Manufacturer and category apply to every symbol"
  - "PART_CATEGORY_TYPE rows other than 'Power Supply' are assumed SamacSys wording; a wrong key falls through to the Reference map"

patterns-established:
  - "Total marker helpers: parse and score from Package.markers, never raise, missing marker scores nothing"

requirements-completed: [INTK-04]

coverage:
  - id: D1
    description: "A SamacSys zip (full synthetic layout, or only part_info.txt plus license.txt markers) is detected as SamacSys at 1.0 / 0.5, with its v6 symbol, (module) footprint and .stp model found and legacy files ignored"
    requirement: INTK-04
    verification:
      - kind: unit
        ref: "tests/test_samacsys_adapter.py#test_samacsys_full_zip_recognised"
        status: pass
      - kind: unit
        ref: "tests/test_samacsys_adapter.py#test_samacsys_markers_only"
        status: pass
    human_judgment: false
  - id: D2
    description: "Other-CAD files are summarised in one intake.ignored_members line, idempotently, leaving other vendors' notes alone"
    requirement: INTK-04
    verification:
      - kind: unit
        ref: "tests/test_samacsys_adapter.py#test_folder_summary_replaces_list"
        status: pass
      - kind: unit
        ref: "tests/test_samacsys_adapter.py#test_detect_twice_keeps_one_summary"
        status: pass
    human_judgment: false
  - id: D3
    description: "part_info.txt is parsed in memory with line/key/value caps; malformed or oversized is INFO, never a refusal"
    requirement: INTK-04
    verification:
      - kind: unit
        ref: "tests/test_samacsys_adapter.py#test_part_info_parse_caps"
        status: pass
      - kind: unit
        ref: "tests/test_samacsys_adapter.py#test_part_info_malformed_is_info"
        status: pass
      - kind: unit
        ref: "tests/test_samacsys_adapter.py#test_part_info_oversized_is_skipped"
        status: pass
    human_judgment: false
  - id: D4
    description: "part_info.txt fills missing Manufacturer/MPN/category (symbol wins), the planner and form agree, and the synthetic part suggests PowerSupply_SubCategory_RECOM"
    requirement: INTK-04
    verification:
      - kind: unit
        ref: "tests/test_samacsys_adapter.py#test_samacsys_suggestion"
        status: pass
      - kind: unit
        ref: "tests/test_samacsys_adapter.py#test_part_info_fills_missing_fields"
        status: pass
      - kind: unit
        ref: "tests/test_naming_suggest.py#test_unmapped_category_falls_back"
        status: pass
    human_judgment: false
  - id: D5
    description: "The PART_CATEGORY_TYPE vocabulary (rows beyond 'Power Supply') matches what SamacSys actually writes"
    verification: []
    human_judgment: true
    rationale: "Only 'Power Supply' is observed in a real download; the other category strings are assumed and the Type token is costly to rename once a library exists"

duration: 11min
completed: 2026-10-23
status: complete
---

# Phase 7 Plan 05: SamacSys Adapter Summary

**SamacSys / Component Search Engine downloads are recognised by marker scoring, their other-CAD files collapse into one log line, and part_info.txt feeds the library suggestion so the synthetic part suggests PowerSupply_SubCategory_RECOM.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-10-23T11:43:42Z
- **Completed:** 2026-10-23T11:53:36Z
- **Tasks:** 2 (TDD: 2 test commits, 2 feat commits)
- **Files modified:** 9

## Accomplishments
- `SamacSysAdapter` with the D-14 weights (generator 5, part_info 3, license 2, version.bin 1, folder layout 1, LIB_ prefix 1); full synthetic zip scores 1.0, markers-only zip 0.5.
- `parse_part_info` is bounded and control-character-stripped; a part_info.txt without usable lines gives one INFO `intake.part_info_ignored`, an oversized one is skipped by the 07-04 marker cap.
- D-16: `detect_candidate` swaps the winning adapter's `ignored_note` into `package.issues` (idempotent); `candidate.ignored` keeps every member.
- `Detection.hints` fills `PartMeta.manufacturer`, `mpn` (single-symbol packages only) and `category`; symbol properties win.
- `suggest.py`: `PS` -> PowerSupply, `recom` / `recompower` -> RECOM, `PART_CATEGORY_TYPE`, `type_choice(reference, category)` with source `part_info`; part_info Types restrict the SubCategory vocabulary like Reference Types.

## Task Commits

1. **Task 1 RED:** `b23d923` (test) - SamacSys fixtures, recognition/D-16/D-13 tests, skeleton adapter
2. **Task 1 GREEN:** `7e656fa` (feat) - adapter, Detection fields, detect swap and notes
3. **Task 2 RED:** `7d85ebb` (test) - suggest and hint tests, signature skeletons
4. **Task 2 GREEN:** `e56719a` (feat) - suggest tables, locate hints, part_hints

**Plan metadata:** committed separately (docs: complete plan)

## Files Created/Modified
- `kicad_lib_manager/importer/adapters/samacsys.py` - adapter, `parse_part_info`, `part_hints`, `folder_summary`
- `kicad_lib_manager/importer/adapters/base.py` - `PartHints`, `Detection.hints/ignored_note/notes`, `_apply_hints` in locate
- `kicad_lib_manager/importer/detect.py` - registry with SamacSys, D-16 swap, notes appended
- `kicad_lib_manager/importer/candidate.py` - `PartMeta.category`
- `kicad_lib_manager/importer/suggest.py` - tables and `type_choice`
- `tests/vendorfixtures.py` - SamacSys builders (synthetic, written from scratch)
- `tests/test_samacsys_adapter.py`, `tests/test_naming_suggest.py`, `tests/test_adapters.py` - tests and registry asserts

## Decisions Made
- Followed the plan's decisions (adapter-computed D-16 note swapped in `detect_candidate`; `Detection.notes`; single-symbol MPN hint; folder marker counts any two sibling folders).
- RED commits carry minimal skeletons (a stub `samacsys.py`, the `PartMeta.category` field, signature-only `type_choice`/`part_hints`) so tests fail on assertions rather than on imports.

## Deviations from Plan

None - plan executed exactly as written. Two extra tests beyond the behavior block were added (`test_folder_summary_leaves_other_vendors_alone`, `test_samacsys_symbol_helper_omits_fields`, plus `test_part_hints_none_when_empty`); a test bug found during GREEN (an `extra` property that the fixture's own `omit` also removed) was fixed in the test before the GREEN commit.

**Total deviations:** 0 auto-fixed.

## Issues Encountered
None. The full suite (excluding the kicad-cli group) gives 1708 passed, 74 skipped; the kicad-cli group fails only the four known KiCad 10 format-20251024 baseline tests.

## Known Stubs
None.

## Threat Flags
None. T-07-13 to T-07-16 are covered by `test_part_info_parse_caps`, `test_unmapped_category_falls_back`, `test_part_info_oversized_is_skipped` / `test_samacsys_detect_survives_hand_built_package` and `test_folder_summary_replaces_list`.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 07-06 can run the same recognition and suggestion checks on the real `LIB_RS3-1212S_H3.zip` (expected `PowerSupply_SubCategory_RECOM`).
- Owner to confirm the `PART_CATEGORY_TYPE` rows beyond "Power Supply" (assumed wording).

## TDD Gate Compliance
Both tasks have a `test(07-05)` commit before the `feat(07-05)` commit. RED evidence: Task 1 RED failed on `assert 'Unknown' == 'SamacSys'`; Task 2 RED failed 10 tests on assertions (PS/RECOM/category/hints not yet implemented).

---
*Phase: 07-snapeda-and-samacsys-adapters*
*Completed: 2026-10-23*

## Self-Check: PASSED
