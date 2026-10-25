---
phase: 03-package-intake-and-naming
plan: 08
subsystem: importer
tags: [cr-01, intake, dos-limits, sexpr, zip-bomb, t-03-15]

requires:
  - phase: 03-package-intake-and-naming
    provides: "locate / _read_limited / open_package and the D-06 caps (plans 03-03, 03-04, 03-07)"
provides:
  - "MAX_KICAD_TEXT_BYTES (8 MiB) and MAX_KICAD_TEXT_NODES (1,000,000) in importer/package.py"
  - "sexpr.parse(text, *, max_nodes=None) raising sexpr.too_many_nodes; kicad_files.parse_bytes(data, name, *, max_nodes=None)"
  - "locate skips an over-cap or over-ceiling or out-of-memory symbol/footprint file with a WARNING intake.unreadable_file"
affects: [phase-04-installer, 03-REVIEW-DISPOSITION CR-01, 03-SECURITY T-03-15, 03-UAT item 1]

actuals:
  tokens: 8000
  tasks: 3
  commits: 6
plan_head_before: 513c476523908f9a10cc071761c2b030f5dc6ad0
plan_head_after: 7febd5a02e8897af038c54b97396605e33b08405

tech-stack:
  added: []
  patterns:
    - "Parser ceilings are additive keyword-only parameters defaulting to None; only importer/adapters/base.py passes one"
    - "Caps are module constants read through the module object at call time so tests monkeypatch them"

key-files:
  created:
    - tests/test_locate_text_caps.py
  modified:
    - kicad_lib_manager/sexpr.py
    - kicad_lib_manager/kicad_files.py
    - kicad_lib_manager/importer/package.py
    - kicad_lib_manager/importer/adapters/base.py
    - tests/test_sexpr.py
    - tests/test_kicad_files.py

key-decisions:
  - "Skip, never refuse: an over-cap file is a WARNING intake.unreadable_file and the rest of the package is still read"
  - "Byte cap is min(MAX_KICAD_TEXT_BYTES, MAX_MEMBER_BYTES), counted in raw bytes before decoding, so the existing member-cap test still drives the cap"
  - "Node ceiling counts lists, atoms and strings (root excluded) and raises at the token that crosses it, with one parse loop shared with the unlimited path"
  - "Neither cap is user-configurable (declined idea in 03-CONTEXT.md); D-06 zip caps untouched"

requirements-completed: [INTK-06, INTK-01]

coverage:
  - id: D1
    description: "A hostile low-ratio .kicad_sym inside every zip limit (about 3.6 MiB, 10:1) is skipped with one WARNING at the 1,000,000-node ceiling; the rest of the package is still located"
    requirement: INTK-06
    verification:
      - kind: unit
        ref: "tests/test_locate_text_caps.py#test_hostile_text_over_node_ceiling_is_skipped"
        status: pass
    human_judgment: false
  - id: D2
    description: "A symbol or footprint over 8 MiB (raw bytes) is skipped before the parser sees it, in zips and folders, with exact boundary, BOM and member-cap behaviour"
    requirement: INTK-06
    verification:
      - kind: unit
        ref: "tests/test_locate_text_caps.py#test_hostile_text_over_byte_cap_never_parsed"
        status: pass
      - kind: unit
        ref: "tests/test_locate_text_caps.py#test_text_byte_cap_boundary"
        status: pass
      - kind: unit
        ref: "tests/test_locate_text_caps.py#test_text_byte_cap_counts_raw_bytes"
        status: pass
      - kind: unit
        ref: "tests/test_locate_text_caps.py#test_folder_text_over_cap_is_skipped"
        status: pass
    human_judgment: false
  - id: D3
    description: "Parser ceiling contract: exact boundary, default unlimited and unchanged, empty input allowed at max_nodes=0"
    requirement: INTK-06
    verification:
      - kind: unit
        ref: "tests/test_sexpr.py#test_max_nodes_boundary"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_files.py#test_parse_bytes_max_nodes_is_issue"
        status: pass
    human_judgment: false
  - id: D4
    description: "MemoryError while parsing one file is a WARNING and locate continues; 3D models are exempt from the text caps; zero-byte file keeps content_mismatch"
    requirement: INTK-01
    verification:
      - kind: unit
        ref: "tests/test_locate_text_caps.py#test_memory_error_is_a_warning"
        status: pass
      - kind: unit
        ref: "tests/test_locate_text_caps.py#test_models_skip_the_text_caps"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every real Custom/ symbol and footprint and both UL KiCad members are below both caps"
    requirement: INTK-01
    verification:
      - kind: unit
        ref: "tests/test_locate_text_caps.py#test_real_files_are_below_both_caps"
        status: unknown
    human_judgment: false

duration: 25min
completed: 2026-10-19
status: complete
---

# Phase 3 Plan 08: Text caps for untrusted symbol and footprint files Summary

**CR-01 closed: symbol and footprint text is read at most 8 MiB and parsed to at most 1,000,000 nodes, so a hostile low-ratio file inside every zip limit is skipped with a WARNING instead of costing minutes and gigabytes**

## Performance

- **Duration:** about 25 min
- **Completed:** 2026-10-19T16:10Z
- **Tasks:** 3 (1 tracer, 2 auto, all TDD)
- **Files modified:** 7 (1 created, 6 modified)

## Accomplishments

- Parser node ceiling: `sexpr.parse(text, *, max_nodes=None)` counts lists, atoms and strings (root excluded) in the single existing loop and raises `SexprError("sexpr.too_many_nodes", "more than N nodes", line, col)` at the crossing token. `kicad_files.parse_bytes` forwards it as an Issue. With `max_nodes` omitted nothing changes; the existing sexpr, kicad_files and round-trip corpus tests pass unchanged.
- Byte cap: `_read_limited` reads `cap + 1` raw bytes where `cap = min(MAX_KICAD_TEXT_BYTES, MAX_MEMBER_BYTES)`, so an over-cap text file never reaches the parser. 3D models stay on the 256-byte sniff.
- `locate` passes `max_nodes=_package.MAX_KICAD_TEXT_NODES` and catches `MemoryError` around `parse_bytes` only; every failure mode is a WARNING `intake.unreadable_file` and the rest of the package is still read. Zips and picked folders share the path, so both are covered.
- The reproduction from the review (a seeded dense mix, about 3.6 MiB, 10:1 deflate, 1.82 million nodes) is a default-cap regression test; so is an 8.8 MiB file that must never be handed to the parser.

## Task Commits

1. **Task 1 (tracer): node ceiling end to end**: RED `29e28ca` (test), GREEN `e9f7468` (feat)
2. **Task 2: 8 MiB byte cap in `_read_limited`**: RED `637e689` (test), GREEN `5afd2fe` (feat)
3. **Task 3: ceiling contract pins, MemoryError guard, real-files test**: RED `0db57d7` (test), GREEN `7febd5a` (feat)

**Plan metadata:** the docs commit that adds this SUMMARY.

## TDD notes

- Task 1 RED: `test_hostile_text_over_node_ceiling_is_skipped` ran the hostile file through the old code and failed on `assert len(skipped) == 1` (0 WARNINGs; the file was parsed whole). The first draft failed on a missing `MAX_KICAD_TEXT_BYTES` attribute, which is not a valid RED, so the sanity check was changed to the literal `8 * 1024 * 1024` before committing. `test_text_cap_constants` failed on the missing constant, the planned assertion.
- Task 2 RED: with the byte-cap constant present uncommitted so that monkeypatching works, four tests failed on the planned assertions (no skip WARNING, spy saw the member, symbol still located). `test_text_cap_never_exceeds_member_cap`, `test_zero_byte_text_file_is_not_a_cap_issue` and `test_models_skip_the_text_caps` passed at once as pins of behaviour that must not change.
- Task 3: the sexpr and kicad_files `max_nodes` tests are contract pins that pass on the Task 1 code, not RED evidence, as in plans 03-04 and 03-07. `test_node_ceiling_boundary_in_locate` also passed at once. `test_memory_error_is_a_warning` was the RED test (MemoryError propagated out of `locate`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test packages skipped the only symbol and so had no candidate**
- **Found during:** Task 2
- **Issue:** the planned boundary, raw-byte and member-cap tests used a lone symbol; skipping it leaves nothing, `_legacy_rules` returns `intake.nothing_found` and `locate` returns `candidate = None`.
- **Fix:** each of those tests also carries a small valid footprint (asserted shorter than every cap tried); the boundary test's parser-spy assertion became `seen == ["f.kicad_mod"]`.
- **Files modified:** tests/test_locate_text_caps.py
- **Committed in:** 637e689 / 5afd2fe

**2. [Rule 1 - Bug] Zero-byte test no longer monkeypatches the caps**
- **Found during:** Task 2
- **Issue:** the plan's footprint beside the empty file would itself exceed a 1-byte cap and add a "larger than" text.
- **Fix:** the test runs on the default caps and asserts the empty file keeps its `intake.content_mismatch` WARNING with no cap text; the max_nodes=0 empty-input case is pinned in tests/test_sexpr.py.
- **Files modified:** tests/test_locate_text_caps.py

**3. [Rule 1 - Bug] Parametrized test with a 100 KB id errored at collection**
- **Found during:** Task 3
- **Issue:** `test_max_nodes_default_is_unlimited` parametrized over the generated 50-symbol library produced a huge test id that errored on Windows.
- **Fix:** plain loop over the two texts inside one test.
- **Files modified:** tests/test_sexpr.py

---

**Total deviations:** 3 auto-fixed (all test-construction bugs, Rule 1). **Impact:** none on production code; all behaviour in the plan's truths is covered.

## Issues Encountered

- `test_real_files_are_below_both_caps` skips in this worktree because `Custom/` is empty here (submodules not checked out); the plan's acceptance of 0 skipped holds only where `Custom/` is present, so the orchestrator should confirm it in the main checkout after merge. As a stand-in I read the main checkout's `Custom/` read-only with the same checks: 24 symbol and footprint files, largest 49,378 bytes, all below both caps and all parse with `max_nodes=1_000_000`. The UL members are covered by the in-test zip read, and the UL tracer tests in tests/test_adapters.py pass unchanged.
- The sandbox rejected compound git and shell commands, so git ran as separate plain calls.

## Known Stubs

None.

## Threat Flags

None. No new endpoint, auth path or trust boundary; T-03-35, T-03-36 and T-03-37 from the plan are mitigated as written.

## Verification

- Full suite in the worktree: 751 passed, 13 skipped (all skips are missing submodules or the Windows symlink privilege).
- `grep max_nodes` over `kicad_lib_manager` lists only sexpr.py, kicad_files.py and importer/adapters/base.py.
- `git diff 513c476 HEAD --stat` shows tests/test_adapters.py and tests/test_package_zip.py untouched.
- Only `except MemoryError` was added to base.py; no `except Exception`.
- Not touched: WR-01 to WR-05, IN-01 to IN-06, `.planning/config.json`, state.json, milestone.lock.

## Next Phase Readiness

CR-01 can be set to `fixed` in 03-REVIEW-DISPOSITION.md and UAT item 1 marked passed; `/gsd-secure-phase` can re-audit T-03-15. Phase 4 builds on the unchanged `locate` and `ImportCandidate` contract.

## Self-Check: PASSED

- Created and modified files exist on disk (tests/test_locate_text_caps.py and the six modified files).
- Commits 29e28ca, e9f7468, 637e689, 5afd2fe, 0db57d7, 7febd5a are ancestors of HEAD.

---
*Phase: 03-package-intake-and-naming*
*Completed: 2026-10-19*
