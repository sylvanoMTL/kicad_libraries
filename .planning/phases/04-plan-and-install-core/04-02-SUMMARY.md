---
phase: 04-plan-and-install-core
plan: 02
subsystem: testing
tags: [pytest, kicad, fixtures, s-expression, byte-builders]

requires:
  - phase: 03-package-intake
    provides: "tests/zipfixtures.py (_quote), kicad_files read side (parse_bytes, find_symbols, find_property, footprint_name, find_models)"
provides:
  - "target_lib: Custom/ target libraries at 20211014, 20231120 and 20241209 as exact bytes"
  - "vendor_symbol_lib: vendor symbol with units, numbered pins, MF/MP fields, Value and ki_keywords control"
  - "extends_pair: parent/child symbol library where the child holds (extends) and no sub-symbol"
  - "vendor_footprint: footprints in both value forms, with models, extra pads, NPTH pad and embedded files"
affects: [04-04, 04-05, 04-06, 04-07, 04-08, 04-09, 04-10]

actuals:
  tokens: 6755
  tasks: 2
  commits: 4
plan_head_before: fc65f8464a3757c4ce792c2566d614ccc9c4e229
plan_head_after: 6c5c67e34b6ed529835e312644456993ca3905d3

tech-stack:
  added: []
  patterns:
    - "Byte builders return bytes, take no paths, and import only the standard library plus zipfixtures._quote"
    - "_tree() renders (head, atom, (child)...) tuples in KiCad 8/9 tab-indented layout"

key-files:
  created:
    - tests/installfixtures.py
    - tests/test_installfixtures.py
  modified: []

key-decisions:
  - "Tab-indented libraries are rendered from nested tuples by one small _tree() helper, so the 20231120 and 20241209 layouts match KiCad's own one-child-per-line output without hand-written strings"
  - "Extra vendor props (MF, MP) are written hidden and placed directly after Datasheet, before ki_keywords"
  - "vendor_symbol_lib and extends_pair share one _v6_symbol helper so the UL shape (ids, bare hide, ki_* fields) has a single definition"

requirements-completed: [INST-02, INST-05, INST-06, POST-04]

coverage:
  - id: D1
    description: "target_lib builds Custom/ libraries at 20211014 (CRLF, leading blank line, ids, bare hide), 20231120 and 20241209 (tab indent, generator_version, hide yes, no ids)"
    requirement: "INST-06"
    verification:
      - kind: unit
        ref: "tests/test_installfixtures.py -k target"
        status: pass
    human_judgment: false
  - id: D2
    description: "vendor_symbol_lib and extends_pair build symbols with sub-symbols, numbered pins, MF/MP fields and an extends child without sub-symbols"
    requirement: "INST-02"
    verification:
      - kind: unit
        ref: "tests/test_installfixtures.py -k 'vendor_symbol_lib or extends_pair'"
        status: pass
    human_judgment: false
  - id: D3
    description: "vendor_footprint builds both value forms, model blocks with non-zero offset, extra and NPTH pads, embedded files"
    requirement: "INST-05, POST-04"
    verification:
      - kind: unit
        ref: "tests/test_installfixtures.py -k vendor_footprint"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every builder returns bytes and writes nothing to disk"
    verification:
      - kind: unit
        ref: "tests/test_installfixtures.py#test_every_builder_returns_bytes_and_writes_nothing"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-10-19
status: complete
---

# Phase 4 Plan 02: Install Fixture Builders Summary

**Pure byte builders for Custom/ target libraries at three KiCad format versions, an extends parent/child pair, MF/MP vendor symbols and model-bearing or pad-mismatched footprints, each proven by parsing with kicad_files.**

## Performance

- **Duration:** about 20 min
- **Completed:** 2026-10-19T22:31Z
- **Tasks:** 2 (each as a RED then GREEN commit)
- **Files modified:** 2 created

## Accomplishments

- `target_lib(version, names, *, eol)` reproduces the real Custom/ header styles: 20211014 with CRLF, a leading blank line, a one-line header, ids and bare `hide`; 20231120 and 20241209 tab-indented with `(generator_version "8.0"/"9.0")`, `(hide yes)`, a Description property and no ids. An unknown version raises ValueError.
- `vendor_symbol_lib`, `extends_pair` and `vendor_footprint` give the downstream plans exact inputs for rename across sub-symbols and `extends` (INST-02), model retargeting (INST-05) and the pin/pad warning (POST-04).
- 42 self-tests parse every builder's output with `kicad_files` and assert names, sub-symbol names, pin numbers, pad first tokens, model counts and offsets. A final test runs every builder inside an empty tmp cwd and checks nothing was written.

## Task Commits

1. **Task 1: Target library builders** - `663f5c2` (test, RED), `9411486` (feat, GREEN)
2. **Task 2: Vendor symbol and footprint builders** - `28381d3` (test, RED), `6c5c67e` (feat, GREEN)

**Plan metadata:** committed separately (docs).

## TDD Gate Compliance

RED and GREEN commits exist for both tasks. RED for each task used a stub in `tests/installfixtures.py` that returns `b""`, so the target tests ran and failed on the planned assertions instead of on import errors.

- Task 1 RED: 22 of 22 `-k target` tests failed (one vacuous pass on the CRLF-only count was tightened with a `> 20` check first). Failures were assertion errors on the empty output (startswith, file_version None, missing symbols) and `DID NOT RAISE ValueError`. Semantic assessment: the target tests executed and failed for the intended reason.
- Task 2 RED: 20 new tests failed, 22 earlier tests still passed. Failures were assertion errors on empty output, `DID NOT RAISE`, and a few `[x] = find_symbols(...)` unpacking errors that are the same missing-output condition. Semantic assessment: valid RED, the target behavior is absent.
- The `gsd_run check tdd-red-evidence` classifier was not run: the plan is `type: execute` with per-task `tdd="true"`, not a `type: tdd` plan, and pytest output is not one of the classifier's supported report formats.

## Files Created/Modified

- `tests/installfixtures.py` - the four public builders plus private style helpers (`_v6_property`, `_v6_pin`, `_tree`, `_v6_symbol`, `_v6_library`, `_atom`)
- `tests/test_installfixtures.py` - self-tests for every builder

## Decisions Made

- The tab-indented style is generated from nested tuples by a 15-line `_tree()` renderer, which yields KiCad 8/9's one-child-per-line layout directly and keeps the builders short.
- Extra vendor props go hidden right after Datasheet; this gives later plans a stable position to assert on.
- `vendor_symbol_lib` raises ValueError when `pins` does not hold one group per unit, and `vendor_footprint` raises on an unknown `value_form`; both guard test authors against silent fixture typos.

## Deviations from Plan

None - plan executed exactly as written.

The plan's `<automated>` commands use `./env/Scripts/python.exe`, which does not exist inside the worktree (the venv is git-ignored). Tests were run with the main checkout's interpreter at `C:/Git_Repo_Clones/Kicad_Libraries-importer/env/Scripts/python.exe` from the worktree root, as the orchestrator instructed. This is an environment note, not a plan change.

## Verification

- `pytest tests/test_installfixtures.py -x -q`: 42 passed
- `pytest tests/test_installfixtures.py -x -q -k target`: 22 passed
- `pytest -q` (whole suite): 909 passed, 14 skipped (submodule and symlink skips only)
- `grep -c "def target_lib("` = 1; `def vendor_symbol_lib(`, `def extends_pair(`, `def vendor_footprint(` present (3 matches); `grep -c "write_bytes\|open("` = 0; `grep -c "def test_" tests/installfixtures.py` = 0
- The 20211014 self-test asserts the exact prefix `b"\r\n(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\r\n"`

## Known Stubs

None. The `return b""` RED stubs were replaced in the GREEN commits.

## Threat Flags

None. T-04-05 mitigated: builders return bytes only, take no paths, and the write-grep returns 0.

## Issues Encountered

None.

## Next Phase Readiness

Plans 04-04 to 04-10 can import `from installfixtures import target_lib, vendor_symbol_lib, extends_pair, vendor_footprint`.

## Self-Check: PASSED

- FOUND: tests/installfixtures.py
- FOUND: tests/test_installfixtures.py
- FOUND commits: 663f5c2, 9411486, 28381d3, 6c5c67e
