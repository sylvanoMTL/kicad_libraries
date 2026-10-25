---
phase: 04-plan-and-install-core
plan: 06
subsystem: importer
tags: [kicad, kicad-cli, symbol-format, library-pair, planner, pytest]

requires:
  - phase: 04-plan-and-install-core
    provides: "04-01 build_plan tracer and plan contract; 04-02 target_lib / vendor_symbol_lib / extends_pair / vendor_footprint builders; 04-03 kicad_cli (upgrade_symbol_text, load_gate) and FakeCli; 04-04 symbol_unit and unit_library_text"
provides:
  - "D-01 version table in build_plan: equal as-is, older normalised with kicad-cli only when its output version equals the target header, otherwise vendor text with a WARNING, newer refused"
  - "D-04 new-library header: kicad-cli's own header, or the vendor file's header without kicad-cli"
  - "LIB-02 pair rules: new pair, pair completion in both directions, invalid name, case-twin refusal"
  - "planner.detect_tools(kicad_fp_dir, explicit_cli=, runner=) -> ToolContext"
  - "Issue codes install.version_mismatch, version_newer_than_target, version_unknown, extends_parent_missing, invalid_library, library_case_clash, pair_completed"
affects: [04-07, 04-08, 04-09, 04-10, 05-preview-and-install-ui]

actuals:
  tokens: 7050
  tasks: 2
  commits: 4
plan_head_before: 88671897896fd493f95df30cd275ccc55cc691df
plan_head_after: 2d73f523eb8d993fd5bf758c48498cdae2e6d991

tech-stack:
  added: []
  patterns:
    - "kicad-cli runs once, on the unrenamed unit text; every later edit is a span splice on the chosen source (memoised by upgrade_symbol_text)"
    - "_SymbolSource(loaded, normalised, version) carries where the block comes from; a new library is that source with the edited block spliced in place"
    - "Library existence comes from exact-case layout listings, not Path.is_file/is_dir, so a case twin is caught on Windows"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/planner.py
    - tests/test_install_plan.py

key-decisions:
  - "A refused version or CLI failure returns a source of None plus ERROR issues, so the table stays a pure function of (vendor, target version, tools)"
  - "extends_parent_missing is checked before the still-open extends_unsupported refusal, and both run before kicad-cli so a refused plan never starts a process"
  - "For a new library with kicad-cli, normalised is result.changed: a vendor file already at the installed format is not reported as normalised"
  - "Library name must be non-empty and equal its sanitize_name form; the earlier install.bad_library_name code is replaced by install.invalid_library"

patterns-established:
  - "Tests that need a target at a given format build it with target_lib in a synthetic Custom/; only the IC_IMU_TDK pair-completion case uses custom_copy"
  - "_MarkingCli (a FakeCli whose output also changes a block field) proves a block came from the CLI and not from the vendor text"

requirements-completed: [INST-06, LIB-02]

coverage:
  - id: D1
    description: "Equal-version symbols are spliced as-is with no kicad-cli call; older ones are normalised only when kicad-cli's output version equals the target header, else merged unchanged with a WARNING naming all versions"
    requirement: INST-06
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_version_equal_as_is / test_version_older_cli_match / test_version_older_cli_mismatch / test_version_older_no_cli"
        status: pass
      - kind: integration
        ref: "tests/test_install_plan.py#test_version_real_cli_into_20241209"
        status: pass
    human_judgment: false
  - id: D2
    description: "A newer incoming symbol is refused with a message telling the user to open and save the library in KiCad; unknown versions merge as-is with a WARNING; a rejecting kicad-cli blocks the plan"
    requirement: INST-06
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_version_newer_refused / test_version_unknown / test_version_cli_rejects"
        status: pass
    human_judgment: false
  - id: D3
    description: "kicad-cli normalisation runs on the unrenamed chosen unit only and is memoised across rebuilds"
    requirement: INST-06
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_version_memoised / test_version_cli_sees_the_chosen_unit_only / test_version_extends_parent_missing"
        status: pass
    human_judgment: false
  - id: D4
    description: "A new library is a .kicad_sym with the installed KiCad's header (or the vendor's own header without kicad-cli) plus a new .pretty, created in one plan; ops are ordered mkdir, model, footprint, symbol_lib"
    requirement: LIB-02
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_library_new_pair_with_cli / test_library_new_pair_without_cli"
        status: pass
      - kind: integration
        ref: "tests/test_install_plan.py#test_library_real_cli_new_header"
        status: pass
    human_judgment: false
  - id: D5
    description: "A half pair gets its missing half created with WARNING install.pair_completed (IC_IMU_TDK case applied end to end on a tmp copy); an existing header is byte-identical for 20211014, 20231120 and 20241209 targets"
    requirement: LIB-02
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_library_pair_completed_pretty_missing / test_library_pair_completed_sym_missing / test_library_existing_header_unchanged"
        status: pass
    human_judgment: false
  - id: D6
    description: "Empty or unsanitised library names and names that differ from an existing library only by case are refused with ERRORs and write nothing"
    requirement: LIB-02
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_library_invalid_name / test_library_case_clash"
        status: pass
    human_judgment: false
  - id: D7
    description: "KiCad 10 writes symbol format 20251024, so on a KiCad 10 machine every 20241209 Custom/ library takes the as-is-with-warning row; whether KiCad 10 loads such a mixed library is unverified (assumption A1)"
    requirement: INST-06
    verification: []
    human_judgment: true
    rationale: "Only KiCad 9.0.9 is installed here; the 04-VALIDATION.md manual-only row covers KiCad 10"

duration: 10min
completed: 2026-10-19
status: complete
---

# Phase 4 Plan 06: Version table and library pair rules Summary

**`build_plan` now matches every incoming symbol to its target library's format (as-is, kicad-cli-normalised only when the CLI lands exactly on the target header, warned, or refused) and creates new libraries as matching `.kicad_sym` + `.pretty` pairs whose header agrees with their content, without ever editing an existing header.**

## Performance

- **Duration:** about 10 min
- **Completed:** 2026-10-19
- **Tasks:** 2 (both TDD, RED then GREEN)
- **Files modified:** 2

## Accomplishments

- D-01 table: `_existing_source` decides by integer comparison of `file_version`. Equal splices the vendor block with no process. Older with kicad-cli runs `upgrade_symbol_text` on the unrenamed unit text (memoised); its output is used only when its version equals the target header, otherwise the vendor text is merged with `install.version_mismatch` naming the symbol and all three versions. No kicad-cli gives the same WARNING plus INFO `install.cli_not_found`. Newer is refused with `install.version_newer_than_target` ("open it in KiCad's Symbol Editor and save it"). An unreadable version on either side is a WARNING `install.version_unknown`.
- `symbol_unit` runs first, so a missing `extends` parent is `install.extends_parent_missing` (naming the parent) before any process starts. The 04-01 interim `install.version_unsupported` branch and its code are gone.
- D-04 and LIB-02: `_new_source` builds the whole new file (kicad-cli output, or `unit_library_text` of the vendor file) and the edited block replaces the original span. The pair state comes from exact-case `list_symbol_libs`/`list_footprint_libs`; a missing half is created in the same plan with WARNING `install.pair_completed`. `ops` order is mkdir, model, footprint(s), symbol_lib; `new_symbol_lib`/`new_footprint_lib` are set from the listings.
- Library names: empty or not equal to their `sanitize_name` form is `install.invalid_library` with the sanitised suggestion; a casefold match with a different spelling in either listing is `install.library_case_clash`. This replaces 04-01's `install.bad_library_name`.
- `detect_tools(kicad_fp_dir, explicit_cli=None, runner=None)` builds the `ToolContext` from `locate_kicad_cli` and `stock_symbols_dir`.
- Real kicad-cli 9.0.9 proves both CLI paths: the UL sample into a 20241209 library is normalised (`(hide yes)`, no `(id `), and both that plan and a brand-new library (header `(version 20241209)`, `(generator "kicad_symbol_editor")`, `(generator_version "9.0")`) pass `kicad_cli.load_gate`.

## Task Commits

1. **Task 1 RED:** `f6cc82c` (test) - 12 failing version tests
2. **Task 1 GREEN:** `9f5cb27` (feat) - version table, detect_tools
3. **Task 2 RED:** `04b3b57` (test) - 11 failing library tests
4. **Task 2 GREEN:** `2d73f52` (feat) - pair rules, new-library header, name rules

**Plan metadata:** the docs commits carrying this SUMMARY and the STATE/ROADMAP/REQUIREMENTS updates.

## TDD Gate Compliance

- **Task 1 RED:** 12 of 13 selected tests failed; the 13th (`test_version_equal_as_is`) passed because 04-01 already delivered the equal row, which is a characterisation test and not an unexpected green. Failures were assertions on the planned behavior (`plan.blocked` with `install.version_unsupported` where a plan was expected, `['install.version_unsupported'] != ['install.version_newer_than_target']`, `install.extends_unsupported != install.extends_parent_missing`) and `AttributeError: no attribute 'detect_tools'` for the three `detect_tools` tests and the real-CLI test. No collection, import or fixture fault. Semantic assessment: valid RED. The `tdd-red-evidence` classifier does not read pytest console output and was not run.
- **Task 1 GREEN:** 13 version tests, 50 with the e2e and layering tests; none skipped (the real-CLI test ran).
- **Task 2 RED:** 11 of 16 selected tests failed on `install.library_not_found`, `install.bad_library_name != install.invalid_library`, and a case twin planning instead of refusing. The five that passed are 04-01 tests whose names contain "library" plus the three `test_library_existing_header_unchanged` cases, which pin behavior the code already had (an existing header is untouched); they are regression guards for GREEN. Semantic assessment: valid RED.
- **Task 2 GREEN:** 16 `-k library` tests, 64 across plan, e2e and layering files; full suite 1169 passed, 4 skipped (baseline 1142 plus 27 new).
- **REFACTOR:** none.

## Files Created/Modified

- `kicad_lib_manager/importer/planner.py` - `detect_tools`, `_SymbolSource`, `_existing_source`, `_new_source`, `_broken_parent`, `_loaded_text`; `build_plan` restructured around them
- `tests/test_install_plan.py` - 27 new tests (`test_version_*`, `test_library_*`), autouse `kicad_cli.clear_cache()` fixture, `_MarkingCli`

## Decisions Made

- The source helpers return `(source | None, issues)`: a `None` source always comes with an ERROR, so `build_plan` has one refusal path for newer versions, CLI failures and unreadable CLI output.
- `extends_parent_missing` is raised from `symbol_unit` returning `None` (missing parent or loop); the still-open `extends_unsupported` for a resolvable parent stays until plan 04-08 lifts it.
- A new library with kicad-cli uses `result.changed` for `normalised`, so a vendor file already at the installed KiCad's format is not shown as normalised.
- The sanitised-name hint distinguishes the empty case ("enter a library name such as Type_SubCategory_Manufacturer") from a cleanable one ("use 'IC_Bad_TI'").

## Deviations from Plan

None - plan executed exactly as written.

Notes, not deviations: the plan's `<verify>` selector `-k version` also selects the two `detect_tools` tests, which I named `test_version_detect_tools_*` so they run in that selection; the count is 13 against the plan's "at least 10". The plan sets `new_symbol_lib` for a pair-completion where only the `.pretty` exists to False, which is what the listings give.

## Known Stubs

None. `install.extends_unsupported` and `install.rename_unsupported` remain as intentional refusals owned by plan 04-08.

## Threat Flags

None. T-04-15 (library name to path): name must be non-empty, equal its `sanitize_name` form, free of placeholder tokens and not a case twin. T-04-16 (version policy): newer is refused, and CLI output is used only when its version equals the target header. T-04-17 (rebuild cost): `test_version_memoised` proves one `sym upgrade` for two builds.

## Issues Encountered

- The Bash tool rejected long heredocs containing nested quotes; patch scripts were written with the Write tool instead. No effect on the result.
- When a plan has no kicad-cli, the planner now adds INFO `install.cli_not_found` and `apply_plan` (04-01) still appends its own INFO of the same code on success, so a result can carry two. Plan 04-07 rewrites that part of `applier.py` and should drop its copy when `plan.issues` already has the code.

## Next Phase Readiness

- 04-07 (apply_plan load gate) can read `plan.tools.kicad_cli`, `plan.normalised` and the `symbol_lib` op's `base_sha256` (None for a new library) directly; `mkdir` ops for a new `.pretty` precede model and footprint ops.
- 04-08 can build on `_SymbolSource`: the rename and field edits apply to `source.loaded`, never before normalisation.
- `git status --porcelain Custom` is empty: every install in the tests targets a `tmp_path` copy.

## Self-Check: PASSED

`kicad_lib_manager/importer/planner.py` and `tests/test_install_plan.py` exist; commits `f6cc82c`, `9f5cb27`, `04b3b57`, `2d73f52` are ancestors of HEAD; `git rev-list --count` from `plan_head_before` is 4. Acceptance greps: `install.version_unsupported` 0 matches outside comments; all required codes and `detect_tools`, `list_footprint_libs(` present. `pytest tests/test_install_plan.py tests/test_install_e2e.py tests/test_importer_layering.py -rs` 64 passed, 0 skipped; full suite 1169 passed, 4 skipped.

---
*Phase: 04-plan-and-install-core*
*Completed: 2026-10-19*
