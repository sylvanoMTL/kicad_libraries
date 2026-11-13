---
phase: 10-importer-on-the-atomic-scheme
plan: 03
subsystem: importer
tags: [kicad, siblings, footprint-index, family-vote, tdd, stdlib]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: "stems.py (EXCLUDED_STEMS, name_verdict, ATOMIC_PREFIX) from plan 10-01"
provides:
  - "importer/siblings.py: family_prefixes, read_library, stock_index, own_index, pick (strict-majority family vote)"
  - "importer/footprint_index.py: build_index, FootprintIndex.contains, rank, rank_with_pads, pad_numbers, footprint_texts"
  - "tests/stockfixtures.py: write_stock_kicad and write_stock_sample, a synthetic KiCad symbols and footprints tree"
affects: [10-suggestion-planner, 10-import-dialog, official-footprint-picker]

actuals:
  tokens: 9250
  tasks: 2
  commits: 3
plan_head_before: b4f956441ef5cab68b1bc6efe104c5a92c09da70
plan_head_after: bb50e4d15319f203ecc59f8c00c64c645e684953

tech-stack:
  added: []
  patterns:
    - "Byte-regex symbol index instead of S-expression parsing of KiCad's stock libraries"
    - "Per-folder cache keyed by (resolved folder, entry count, newest os.stat mtime)"
    - "Exact-case link membership before any path is built (T-10-06)"

key-files:
  created:
    - kicad_lib_manager/importer/siblings.py
    - kicad_lib_manager/importer/footprint_index.py
    - tests/stockfixtures.py
    - tests/test_siblings.py
    - tests/test_footprint_index.py
  modified: []

key-decisions:
  - "Strict majority (more than half) decides the vote; a split family returns stem None with its counts kept (D-03, RESEARCH A1)"
  - "The first prefix step with any sibling ends the vote, so USB4145-03-0170-C stops at USB4 (three Connector parts), not at USB"
  - "stock_index calls progress for every .kicad_sym file including skipped excluded stems, so total equals the file count"
  - "Cache state uses os.stat on the .pretty folders; os.DirEntry.stat gave an unstable modification time on NTFS"
  - "unquote is imported through kicad_files because the registered layering entry for footprint_index does not list sexpr"

patterns-established:
  - "Qt-free index modules take progress(message, current, total) so the dialog can build them on its open worker"

requirements-completed: [LIB-04, LIB-06]

coverage:
  - id: D1
    description: "CSD85301Q2 votes into Transistor_FET from both a synthetic stock tree and the owner's Atomic_ libraries, with the Diode count kept as an alternative"
    requirement: LIB-04
    verification:
      - kind: unit
        ref: "tests/test_siblings.py#test_csd_part_votes_into_transistor_fet_from_the_stock_tree"
        status: pass
      - kind: unit
        ref: "tests/test_siblings.py#test_csd_part_votes_into_transistor_fet_from_the_owners_atomic_libraries"
        status: pass
    human_judgment: false
  - id: D2
    description: "Family prefix rules, strict majority, split-family fall-through, top-level-only counting and own-index name filtering"
    requirement: LIB-04
    verification:
      - kind: unit
        ref: "tests/test_siblings.py (family_prefixes, pick, read_library, stock_index rows)"
        status: pass
      - kind: integration
        ref: "tests/test_siblings.py#test_live_kicad_10_votes_csd_into_transistor_fet_and_usb_into_connector (75 vs 2 on KiCad 10.0.7)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Official footprint index: exact-case membership, repo and Wurth never listed, name-first ranking with DQK0006B ranking Package_SON:Texas_DQK first, lazy cached pad reads"
    requirement: LIB-06
    verification:
      - kind: unit
        ref: "tests/test_footprint_index.py"
        status: pass
      - kind: integration
        ref: "tests/test_footprint_index.py#test_live_kicad_footprints_rank_the_dqk_package_first"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-27
status: complete
---

# Phase 10 Plan 03: Sibling index and official footprint index Summary

**Qt-free family-prefix vote over KiCad's stock and the owner's Atomic_ symbols (CSD85301Q2 -> Transistor_FET, 75 vs 2 on KiCad 10) plus a name-first, cached ranking of KiCad's official footprints with lazy pad reads**

## Performance

- **Duration:** about 25 min
- **Started:** 2026-10-27T09:38:00Z (approx)
- **Completed:** 2026-10-27T10:03:00Z
- **Tasks:** 2
- **Files modified:** 5 created, 0 modified

## Accomplishments
- `siblings.py` votes a part number into a library: prefix steps `CSD85301, CSD8, CSD`, first non-empty step decides, strict majority wins, counts kept as alternatives; unit sub-symbols and excluded stems never vote; the owner's index reads only `Atomic_` libraries that pass the name rule.
- `footprint_index.py` lists KiCad's installed footprints by file name only (never the repo or WurthElektronik), answers exact-case `Lib:FP` membership, ranks by package code, sibling links and family words, and reads pad numbers only for the shortlist, once, through a cache.
- `tests/stockfixtures.py` gives later plans a synthetic KiCad tree so no unit test needs the installed KiCad. Live KiCad 10.0.7 rows ran here and passed (75 Transistor_FET vs 2 Diode; DQK0006B ranks `Package_SON:Texas_DQK` first; more than 100 footprint libraries).

## Task Commits

1. **Task 1 (tracer): CSD85301Q2 to Transistor_FET end to end** - `e17c0b8` (feat)
2. **Task 2 RED: failing tests for footprint index, prefix rules, cache and live counts** - `74dd076` (test)
3. **Task 2 GREEN: footprint index, ranking, lazy pads, cached stock index** - `bb50e4d` (feat)

No REFACTOR commit was needed.

**Plan metadata:** the docs commit that adds this SUMMARY.

## TDD Gate Compliance

- **RED:** `74dd076` added 18 failing tests. Every failure is an assertion on the planned behaviour (cache identity, progress calls, index contents, ranking order, pad values, texts, the live DQK ranking); none is an import, collection or fixture fault. `footprint_index.py` was committed as a behaviour-less skeleton (empty index, empty rankings) so the tests could import and fail on assertions. The 35 tests that passed at RED were the family-prefix and vote rows already satisfied by the Task 1 tracer, plus negative cases a skeleton satisfies. The machine classifier `gsd_run check tdd-red-evidence` was not run; the semantic assessment above stands in its place.
- **GREEN:** `bb50e4d`, 67 passed across `test_siblings.py`, `test_footprint_index.py`, `test_importer_layering.py`.
- **REFACTOR:** none.

## Files Created/Modified
- `kicad_lib_manager/importer/siblings.py` - family_prefixes, read_library, stock_index (cached, progress), own_index, pick
- `kicad_lib_manager/importer/footprint_index.py` - FootprintIndex, build_index (cached, progress), rank, rank_with_pads, pad_numbers, footprint_texts
- `tests/stockfixtures.py` - stock_footprint, write_stock_kicad, write_stock_sample
- `tests/test_siblings.py`, `tests/test_footprint_index.py` - 53 tests including live KiCad 10 rows

## Decisions Made
See key-decisions above. The vote and ranking weights follow the plan's flagged assumptions (100 per sibling link, 50 full code, 30 leading letters, 5 per word, 20 + 20 for pads).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan's USB4145 expectation contradicts its own pick rule and sample**
- **Found during:** Task 2 (writing the pick behaviour rows)
- **Issue:** The behaviour row says `USB4145-03-0170-C` gives counts Connector 3, Interface_USB 1, Power_Protection 1. With the specified sample (Connector holds USB4105, USB4110, USB4085) the prefix step `USB4` already finds three Connector parts, and the rule "stop at the first prefix step that has any sibling" ends there.
- **Fix:** Kept the sample names (other plans may rely on them) and the rule. Tests assert `SiblingPick("Connector", "USB4", (("Connector", 3),))` for USB4145, and a new test with `USB9999` asserts the three-library count triple at prefix `USB`. The live KiCad 10 check (`stem == "Connector"`) is unaffected.
- **Files modified:** tests/test_siblings.py
- **Committed in:** `74dd076`

**2. [Rule 1 - Bug] NTFS directory listing gave an unstable modification time**
- **Found during:** Task 2 GREEN (`test_build_index_is_cached_until_the_folder_changes` failed)
- **Issue:** `os.DirEntry.stat()` on a `.pretty` folder returned a different mtime on the second listing, so the cache never hit.
- **Fix:** The cache state uses `os.stat(entry.path)`.
- **Files modified:** kicad_lib_manager/importer/footprint_index.py
- **Committed in:** `bb50e4d`

**3. [Rule 1 - Bug] Own test expectation for a 2-letter code**
- **Found during:** Task 2 GREEN
- **Issue:** My RED test expected no result for `package_code="SO"`, but the plan's full-code rule (50 when the code is inside the name) matches SOIC-8 and SOT-23-5.
- **Fix:** The test now asserts both at score 50 and no leading-letters (30) credit.
- **Files modified:** tests/test_footprint_index.py
- **Committed in:** `bb50e4d`

---

**Total deviations:** 3 auto-fixed (3 Rule 1)
**Impact on plan:** None on interfaces or behaviour; two test expectations corrected and one cache-key detail fixed.

## Issues Encountered
- The worktree has no `env/`, so tests ran with the orchestrator's interpreter, as the notes describe. The `Custom/` submodule is absent here; no test in this plan needs it.
- `unquote` is imported via `kicad_files` rather than `sexpr`, because the registered layering entry for `importer.footprint_index` (owned by plan 10-01) lists `kicad_files` but not `sexpr`.

## Known Stubs

None.

## Threat Flags

None. T-10-05 is mitigated (byte regex, file-name listing, lazy capped pad reads, folder-state cache, progress callback) and T-10-06 is mitigated (a link becomes a path only after both halves match exact-case listing names; `../` links return None, tested).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- The suggestion and the official-footprint dialog can call `pick(stock_index(...), mpn)`, `pick(own_index(...), mpn)`, `build_index(...)`, `rank`, `rank_with_pads` and `footprint_texts` on their open worker.
- The wave gate `pytest -m "not wurth"` was not run here; the orchestrator runs it after the merge.

## Self-Check: PASSED

- Created files exist: siblings.py, footprint_index.py, stockfixtures.py, test_siblings.py, test_footprint_index.py.
- Commits `e17c0b8`, `74dd076`, `bb50e4d` are in the branch history.
- `pytest tests/test_siblings.py tests/test_footprint_index.py tests/test_importer_layering.py`: 67 passed.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*
