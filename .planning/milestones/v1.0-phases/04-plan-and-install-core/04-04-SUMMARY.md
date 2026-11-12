---
phase: 04-plan-and-install-core
plan: 04
subsystem: importer
tags: [kicad, s-expression, span-edits, symbol-rename, extends, properties, footprint-model, pytest]

requires:
  - phase: 04-plan-and-install-core
    provides: "04-01 kicad_files write helpers and plan contract; 04-02 tests/installfixtures.py builders"
provides:
  - "Install-unit extraction (extends_name, symbol_unit, unit_library_text)"
  - "Exact symbol rename across unit sub-symbols and extends (rename_symbol_edits, replace_exact_tokens)"
  - "Block replace and insert-before (symbol_replace_edit, symbol_insert_before_edit, block_text)"
  - "Property primitives with format-aware hide and ids (rename_property_edit, property_is_hidden, hidden_template, synth_property_text, description_field_name, new_property_text version keyword)"
  - "tests/test_kicad_files_write.py: 69 tests incl. the -k rename / -k model selections for 04-VALIDATION.md"
affects: [04-06, 04-07, 04-08, 04-09, 04-10]

actuals:
  tokens: 10500
  tasks: 3
  commits: 5

plan_head_before: 6a9588bab168f6ebc1d6fe4f9f316982e1c4d047
plan_head_after: 09d7e19a6291fb786c0485373b27dac0555c0294

tech-stack:
  added: []
  patterns:
    - "Every KiCad change is a pure function returning Edit objects or text; callers batch them in one apply_edits"
    - "Names are compared unquoted and exact; no substring rewrite anywhere"
    - "Hide and id style follow the target file's format version, not the vendor's"

key-files:
  created:
    - tests/test_kicad_files_write.py
  modified:
    - kicad_lib_manager/kicad_files.py

key-decisions:
  - "synth_property_text and new_property_text treat an unknown version as the current style (no id, (hide yes)); new_property_text without a version infers bare hide from the template carrying an (id)"
  - "description_field_name prefers an existing Description over ki_description when both exist"
  - "unit_library_text deletes each unwanted symbol together with the whitespace after the previous sibling, so removed symbols leave no blank line and consecutive removals stay non-overlapping"
  - "A (hide no) in a cloned template is converted in place (to bare hide or (hide yes)) instead of adding a second hide"

patterns-established:
  - "Test oracles built by string replacement or by a fixture builder with the expected name, so 'only these tokens changed' is a byte-equality assertion"

requirements-completed: [INST-01, INST-02, INST-03, INST-05]

coverage:
  - id: D1
    description: "rename_symbol_edits renames the symbol, every <old>_<u>_<s> sub-symbol and every extends reference, never by substring, case-sensitively, with quote round-trip"
    requirement: INST-02
    verification:
      - kind: unit
        ref: "tests/test_kicad_files_write.py -k rename (12 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "symbol_unit returns extends ancestors parent first and None on missing parent or cycle; unit_library_text keeps only named symbols with no blank line"
    requirement: INST-01
    verification:
      - kind: unit
        ref: "tests/test_kicad_files_write.py -k unit"
        status: pass
    human_judgment: false
  - id: D3
    description: "symbol_replace_edit and symbol_insert_before_edit splice exactly one span in the target's EOL and indent"
    requirement: INST-01
    verification:
      - kind: unit
        ref: "tests/test_kicad_files_write.py -k 'replace or insert'"
        status: pass
    human_judgment: false
  - id: D4
    description: "Property rename, hidden detection and template search, synthesised and cloned hidden properties with id and hide style by format version, Description name by version"
    requirement: INST-02
    verification:
      - kind: unit
        ref: "tests/test_kicad_files_write.py -k 'property or description or hidden' (29 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Footprint name, value (atom or string, fp_text or property) and model insert/retarget are exact for CRLF/LF, space/tab indent and leave header, tags and embedded_files alone"
    requirement: INST-03
    verification:
      - kind: unit
        ref: "tests/test_kicad_files_write.py -k 'model or footprint or value' (18 tests)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-10-19
status: complete
---

# Phase 4 Plan 04: Complete kicad_files write side Summary

**`kicad_files` now expresses every INST-01/02/03/05 change as a small, separately tested span edit: extends-aware install units, an exact rename that follows `_u_s` sub-symbols and `(extends ...)` but never matches by substring, symbol replace and insert-before, and property primitives that hide and number new properties in the target file's own style.**

## Performance

- **Duration:** about 15 min
- **Started:** 2026-10-19T22:33Z
- **Completed:** 2026-10-19T22:49Z
- **Tasks:** 3 (all TDD)
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- Task 1: `extends_name`, `symbol_unit` (parent first, None on missing parent or cycle), `unit_library_text`, `rename_symbol_edits`, `replace_exact_tokens`, `block_text`, `symbol_replace_edit`, `symbol_insert_before_edit`. Rename tests use byte-equality oracles, including a PART/PARTX library with datasheet URLs containing `PART`, and a `A"B\C` name that round-trips through `quote`/`unquote`.
- Task 2: `rename_property_edit`, `property_is_hidden` (bare `hide` and `(hide yes)`), `hidden_template` (Datasheet, Footprint, ki_fp_filters, ki_keywords, then any hidden), `synth_property_text` (id only before 20220914, bare hide before 20231120), `description_field_name` (existing field wins, else Description from 20230620). `new_property_text` gained a keyword-only `version` and now always yields a hidden property.
- Task 3: whole-file tests for footprint name, value (both forms, bare atoms, legacy `module`) and model insert/retarget on CRLF space-indented and LF tab-indented footprints, plus header/tags/embedded_files untouched (D-02).
- `kicad_files` still imports only `sexpr`, `fsutil`, `models`; `tests/test_layering.py` and `tests/test_importer_layering.py` pass.

## Task Commits

1. **Task 1 RED:** `3714fc1` (test) - 25 failing tests
2. **Task 1 GREEN:** `97b70d1` (feat)
3. **Task 2 RED:** `8894207` (test) - 28 failing tests
4. **Task 2 GREEN:** `74ca6ad` (feat)
5. **Task 3:** `09d7e19` (test) - characterization tests, no production change needed

**Plan metadata:** the docs commit carrying this SUMMARY.

## TDD Gate Compliance

- **Task 1 RED:** 25 of 25 selected tests failed with `AttributeError: module 'kicad_lib_manager.kicad_files' has no attribute '<helper>'`. Tests import the module and look the helper up at call time, so collection succeeded and each target test executed and failed because the feature is absent. Semantic assessment: valid RED (missing feature, no import/collection/fixture fault). Evidence inspected by hand from pytest output; the `tdd-red-evidence` classifier does not read pytest console format and was not run.
- **Task 1 GREEN:** 48 passed (write tests plus both layering tests).
- **Task 2 RED:** 28 of 28 selected tests failed, 27 on `AttributeError` for the missing helpers and the `new_property_text(..., version=...)` ones on the unexpected keyword. Semantic assessment: valid RED.
- **Task 2 GREEN:** 93 passed, 6 skipped (the skips are 04-01's `custom_copy` tests; the Custom submodule is not initialised in a worktree).
- **Task 3:** all 15 tests passed on first run, so there is no RED. This is an unexpected green by the gate's wording; I investigated and it is explained: `footprint_name_edit`, `footprint_value_edits`, `model_insert_edit` and `retarget_model` were already delivered and correct in 04-01 and the plan asks only to harden them "without changing signatures". The tests were written first against the planned behavior (whole-file expected strings built by hand), and they confirm the existing code already meets it, so no production change was made. Three more fixture-based tests (bare atoms, legacy module, no trailing newline) were added after the first run and also passed. The commit is a `test(04-04)` commit with no `feat` pair.
- **REFACTOR:** none.

## Files Created/Modified

- `kicad_lib_manager/kicad_files.py` - the 13 new helpers listed above plus the `version` keyword on `new_property_text`
- `tests/test_kicad_files_write.py` - 69 tests (12 rename, 29 property/description/hidden, 18 model/footprint/value, rest unit/replace/insert)

## Decisions Made

- An unknown (`None`) version is written in the current style by `synth_property_text`; `new_property_text` without a version infers bare hide from the template carrying an `(id N)`, so existing 04-01 callers behave as before.
- When both `Description` and `ki_description` exist, `description_field_name` returns `Description`.
- `unit_library_text` removes each symbol together with the whitespace after its previous sibling, which also handles runs of consecutive removed symbols without overlapping edits.
- A cloned template carrying `(hide no)` is converted in place rather than getting a second hide flag.

## Deviations from Plan

None - plan executed exactly as written. Two environment notes: the plan's `./env/Scripts/python.exe` was run as `C:/Git_Repo_Clones/Kicad_Libraries-importer/env/Scripts/python.exe` from the worktree root, as the orchestrator instructed; and the plan-start ledger under the git dir could not be written from inside the worktree sandbox, so `plan_head_before` is the known worktree base SHA.

## Verification

- `pytest tests/test_kicad_files_write.py -k rename`: 12 passed
- `-k "property or description or hidden"`: 29 passed
- `-k model`: 10 passed
- `pytest tests/test_kicad_files_write.py tests/test_edits.py tests/test_kicad_files.py tests/test_layering.py`: 155 passed, 4 skipped
- `pytest tests/test_install_e2e.py tests/test_install_plan.py`: passes; the `custom_copy` tests skip in the worktree (Custom submodule not initialised), so the 04-01 planner path that calls `new_property_text` was not exercised against real Custom/ libraries here. The change is backward compatible (new keyword defaults to None; a hidden template is returned unchanged apart from name, value and id).
- Whole suite: 1051 passed, 20 skipped (submodule-dependent tests).

## Known Stubs

None.

## Threat Flags

None. T-04-10: every name, value and path written goes through `sexpr.quote`; tests inject `"`, `)`, `\` and check the re-parse. T-04-11: the exact-match substring test proves `PARTX`, `PARTX_1_1` and datasheet URLs are untouched.

## Issues Encountered

None.

## Next Phase Readiness

Plans 04-06 onward can compose rename, unit extraction, replace/insert-before and property helpers in the planner without adding span arithmetic. The planner still refuses renames and `extends` units with `install.rename_unsupported` / `install.extends_unsupported`; wiring these helpers in is owned by a later plan.

## Self-Check: PASSED

`kicad_lib_manager/kicad_files.py` and `tests/test_kicad_files_write.py` exist; commits `3714fc1`, `97b70d1`, `8894207`, `74ca6ad`, `09d7e19` are ancestors of HEAD; all 13 helper definitions are present.
