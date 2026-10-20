---
phase: 04-plan-and-install-core
plan: 08
subsystem: importer
tags: [kicad, symbol-fields, extends, rename, planner, pytest]

requires:
  - phase: 04-plan-and-install-core
    provides: "04-01 build_plan tracer and plan contract; 04-04 kicad_files primitives (symbol_unit, rename_symbol_edits, hidden_template, synth_property_text, description_field_name); 04-06 version table and library pair rules; 04-07 transactional apply_plan"
provides:
  - "D-11..D-15 field rules in build_plan: Manufacturer/MPN renamed in place or added hidden in the block's own format, overrides, Description per format"
  - "Exact-token symbol rename (name, _u_s sub-symbols, extends, Value, ki_keywords) with plan.renames; caller footprint names that drive file, internal name, value, link and filters"
  - "D-16 extends units: parent first, fields on every symbol, one conflict per existing unit member"
  - "D-17/INTK-08 item rules: no_model, model_declined, extra_models, stale_model_path, embedded_files notices"
  - "Issue codes install.invalid_name, install.model_declined, install.extra_models, install.stale_model_path, install.embedded_files; install.no_model now names the package"
affects: [04-09, 04-10, 05-preview-and-install-ui]

actuals:
  tokens: 10000
  tasks: 2
  commits: 4
plan_head_before: 869773f3941bf3454d58fc073d16f9b12f1f75cd
plan_head_after: 2df6e6551d966500eedf1009adb720b443261947

tech-stack:
  added: []
  patterns:
    - "All symbol edits run on a text cut down to the incoming unit, so no existing Custom/ symbol or header can be an edit target"
    - "Each property receives one edit computed from its final value (rename + set, or one insert); inserts at one anchor keep list order"
    - "The unit text is ordered parent first before kicad-cli sees it, so the CLI result and the no-CLI result agree"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/planner.py
    - tests/test_install_plan.py

key-decisions:
  - "New properties are styled after the block they join (source.version), which equals the target's own format whenever kicad-cli normalised the block or the versions already agree; a warned as-is mismatch keeps the block's own style"
  - "Manufacturer override and fallback apply to every symbol of a unit; mpn, value, datasheet and description overrides apply to the chosen (last) symbol only; each symbol's MPN defaults to its own vendor name"
  - "An exact Manufacturer/MPN property is always the role holder, even when empty (filled from a vendor alias or the default), so a duplicate is never created"
  - "A vendor model path is stale unless it starts with a path variable other than ${KIPRJMOD}"
  - "install.no_model is reported when the package has no model, install.model_declined only when the caller declined an existing one"

patterns-established:
  - "_edit_symbol(work, ref, new_name, fields, version) returns (edits, final MPN); build_plan owns ordering, renames and splicing"
  - "Tests for extends units use extends_pair(child_first=True) so the reorder is always exercised"

requirements-completed: []

coverage:
  - id: D1
    description: "First vendor Manufacturer-like and MPN-like fields are renamed in place with values kept and no duplicate; an exact Manufacturer is kept; renamed fields keep their own visibility"
    requirement: INST-02
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_fields_mf_mp_renamed_in_place / test_fields_exact_manufacturer_kept"
        status: pass
    human_judgment: false
  - id: D2
    description: "Missing Manufacturer/MPN are added hidden in the block's format (id + bare hide for 20211014, (hide yes) and no id for 20241209); empty Manufacturer warns; overrides win; Description is ki_description or Description by format"
    requirement: INST-02
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_fields_added_hidden_20211014 / test_fields_added_hidden_20241209 / test_fields_overrides_win / test_fields_manufacturer_missing_warns / test_fields_description_name_by_version"
        status: pass
    human_judgment: false
  - id: D3
    description: "A sanitised symbol name renames the symbol, its _u_s sub-symbols and extends references; Value and ki_keywords change only on exact tokens; plan.renames lists it"
    requirement: INST-02
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_rename_sanitised_symbol / test_rename_value_override_beats_the_token_rewrite / test_unit_parent_rename_updates_extends"
        status: pass
    human_judgment: false
  - id: D4
    description: "A caller footprint name flows into the .kicad_mod name, internal name, value text, Footprint field and ki_fp_filters; an unusable name is refused; several footprints link the first and filter all in order"
    requirement: INST-03
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_footprint_consistency_after_override / test_footprint_consistency_override_is_sanitised / test_footprint_consistency_unusable_override_refused / test_several_footprints_order"
        status: pass
    human_judgment: false
  - id: D5
    description: "A derived vendor symbol installs with its parent first (existing and new library, child-first vendor file), fields on every symbol, an existing parent is a conflict, and the round trip holds for units of 1 and 2; real kicad-cli loads the result"
    requirement: INST-02
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_unit_parent_first / test_unit_fields_on_every_symbol / test_unit_existing_parent_is_a_conflict / test_unit_invariant"
        status: pass
      - kind: integration
        ref: "tests/test_install_plan.py#test_unit_real_cli_loads_in_kicad"
        status: pass
    human_judgment: false
  - id: D6
    description: "A package with no model installs with WARNING install.no_model; a declined model gives INFO install.model_declined; vendor model paths are never edited and stale ones warn; extra model blocks and embedded files warn"
    requirement: INTK-08
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_no_model_package / test_no_model_declined / test_no_model_stale_vendor_path / test_model_extra_blocks_warn / test_model_embedded_files_warn"
        status: pass
    human_judgment: false
  - id: D7
    description: "Hostile MPN stays one quoted token and the model file name is sanitised; existing symbols and headers are byte-identical in the planned library"
    verification:
      - kind: unit
        ref: "tests/test_install_plan.py#test_fields_value_injection_quoted / test_fields_existing_symbols_untouched"
        status: pass
    human_judgment: false
  - id: D8
    description: "Whether renamed vendor Manufacturer/MPN properties should keep their own visibility and whether the Footprint link and ki_fp_filters should go on every symbol of an extends unit (research A6/A7)"
    verification: []
    human_judgment: true
    rationale: "Claude's-discretion choices recorded in the plan; the owner confirms both in step 5 of the D-22 manual UAT check in 04-10"

duration: 14min
completed: 2026-10-20
status: complete
---

# Phase 4 Plan 08: Field rules, renames and extends units Summary

**`build_plan` now writes exactly the fields, names and links the preview will show: Manufacturer/MPN renamed in place or added hidden in the block's own format, token-exact symbol renames, caller footprint names, parent-first `extends` units, and a clean no-model path, all computed on a unit-only text so nothing outside the incoming symbols can change.**

## Performance

- **Duration:** about 14 min (2026-10-20T08:00Z to 08:14Z)
- **Tasks:** 2 (both TDD, RED then GREEN)
- **Files modified:** 2

## Accomplishments

- `_edit_symbol` replaces the tracer's `_SymbolEditor`. Each property gets one edit from its final value: `Footprint`/`ki_fp_filters` set or added; `Manufacturer`/`MPN` kept, renamed from the first vendor alias (exact name first, then `MF`, `MANUFACTURER`, `Manufacturer_Name` / `MP`, `Manufacturer_Part_Number`, `MANUFACTURER_PART_NUMBER`) or added hidden via `hidden_template` + `new_property_text`, else `synth_property_text`; overrides win; Description lands in `ki_description` or `Description` through `description_field_name`.
- Symbol rename uses `rename_symbol_edits` on the unit (name, `_u_s` sub-symbols, `extends`) and `replace_exact_tokens` on Value/ki_keywords (unless Value is overridden); `plan.renames` lists symbol and footprint renames. Footprint names from `footprint_names` are sanitised (INFO `naming.changed`), an unusable one is ERROR `install.invalid_name`.
- Extends units (D-16): `symbol_names` is the unit parent first, fields go on every symbol, an existing unit member is a symbol Conflict, and `_unit_text` orders the unit parent first before kicad-cli runs. Real kicad-cli 9.0.9 loads a child-first vendor file into both an existing and a new library.
- Model rules (D-17, INTK-08): `install.no_model` ("No 3D model found in <package>; ..."), `install.model_declined`, `install.extra_models` (first block retargeted, rest untouched), `install.stale_model_path` (vendor paths never edited), `install.embedded_files` (bytes of `(embedded_files)` untouched).

## Task Commits

1. **Task 1 RED:** `6170ea7` (test) - 20 selected tests, 12 failing on the planned behavior
2. **Task 1 GREEN:** `3b8af55` (feat) - field rules, exact renames, caller footprint names
3. **Task 2 RED:** `3743e0a` (test) - 13 of 21 selected tests failing
4. **Task 2 GREEN:** `2df6e65` (feat) - extends units, model and footprint notices, real-CLI unit test

**Plan metadata:** the docs commit carrying this SUMMARY and the STATE/ROADMAP updates.

## TDD Gate Compliance

- **Task 1 RED:** 12 of 20 failed. Failures were assertions on the planned behavior: `ki_description`/`Description` count 0, Value/Datasheet/Manufacturer/MPN not overridden (`'PART' == 'VAL'`), `('DQK0006B',) == ('DQK0006B_TI',)`, a clean plan where `install.invalid_name` was expected, and `install.rename_unsupported` blocking the rename tests. No import, collection or fixture fault. The 8 that passed (`mf_mp_renamed_in_place`, `exact_manufacturer_kept`, `added_hidden_20211014`, `manufacturer_missing_warns`, `rename_not_listed...`, `existing_symbols_untouched` x2) pin 04-01 behavior and are regression guards. Semantic assessment: valid RED. The `tdd-red-evidence` classifier does not read pytest console output and was not run.
- **Task 1 GREEN:** 20 passed; with the e2e, apply, verify and layering files 174 passed; full suite 1236 passed, 4 skipped.
- **Task 2 RED:** 13 of 21 failed on `install.extends_unsupported` blocking every unit test, the old `No 3D model will be installed` text, and the missing `model_declined`, `stale_model_path`, `extra_models` and `embedded_files` issues. The 8 that passed were the 04-01 `several_footprints`/`no_model` characterisation tests and the size-1 invariant. Semantic assessment: valid RED.
- **Task 2 GREEN:** 21 selected tests passed on the first run; a real-CLI test added during GREEN exposed that kicad-cli refuses a child-first unit text (exit 2, "Unable to load library"), fixed by `_unit_text`; 23 passed. Full suite 1255 passed, 4 skipped (baseline 1217 plus 38 new).
- **REFACTOR:** none.

## Files Created/Modified

- `kicad_lib_manager/importer/planner.py` - `_Fields`, `_edit_symbol`, `_unit_text`, `_resolves_in_library`; `build_plan` restructured around the unit (names, footprint names, normalise, cut to unit, edit, splice, footprints)
- `tests/test_install_plan.py` - 38 new tests (fields, rename, footprint_consistency, unit, several, no_model, model_extra, embedded, real-CLI unit); `_vendor`/`_plan` take `model_name`, `footprint_bytes`, `model`

## Decisions Made

- New properties follow the format of the block they join (`source.version`), not blindly the target's: they agree whenever kicad-cli normalised the block or the versions match, and a warned as-is mismatch stays internally consistent.
- Manufacturer (override and fallback) is unit-wide; mpn/value/datasheet/description overrides apply to the chosen symbol only (research Open Question 8); each symbol's MPN defaults to its own vendor name.
- An exact `Manufacturer`/`MPN` property is always the role holder even when empty, so a vendor file with both `Manufacturer` and `MF` never gains a duplicate.
- The model file name uses the final MPN (falling back to the vendor symbol name); a name with no usable characters is `install.invalid_name`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan contradiction on stale model paths**
- **Found during:** Task 2
- **Issue:** The behavior bullet says `${KIPRJMOD}/x.step` must warn `install.stale_model_path`, while the action says only paths not starting with `${` warn.
- **Fix:** A path is stale unless it starts with a path variable other than `${KIPRJMOD}` (the project-relative variable cannot resolve from a library). Absolute and relative paths warn; `${KICAD9_3DMODEL_DIR}` and `${CUSTOM_3DMODEL_DIR}` do not. Tests parametrize all five cases.
- **Files modified:** kicad_lib_manager/importer/planner.py, tests/test_install_plan.py
- **Commit:** 2df6e65

**2. [Rule 1 - Bug] kicad-cli rejects a child-first unit text**
- **Found during:** Task 2 (real-CLI test)
- **Issue:** `unit_library_text` keeps file order, so a vendor file listing the child first made `sym upgrade` fail before any later reordering.
- **Fix:** `_unit_text` orders the unit parent first right after cutting; the new-library path therefore needs no later reorder.
- **Files modified:** kicad_lib_manager/importer/planner.py
- **Commit:** 2df6e65

**3. [Rule 1 - Bug] test_version_memoised compared full bytes across different Value overrides**
- **Found during:** Task 1
- **Issue:** The 04-06 test built two plans with `value="ONE"`/`"TWO"` and asserted identical symbol bytes, which held only because the Value override was not implemented yet.
- **Fix:** It now asserts each Value and that the bytes differ only by that value; the one-CLI-call assertion is unchanged.
- **Files modified:** tests/test_install_plan.py
- **Commit:** 3b8af55

**4. [Rule 1 - Bug] Missing `Node` import after rewriting the imports**
- **Found during:** Task 1 (commit review)
- **Issue:** `_broken_parent(root: Node, ...)` still used `Node`; Python 3.14 defers annotations so tests passed, but 3.10 to 3.13 would raise NameError at import.
- **Fix:** Import restored before the Task 1 commit was finalised.
- **Commit:** 3b8af55

**Total deviations:** 4 auto-fixed (4 Rule 1). **Impact:** none on scope; the first two sharpen behavior the plan described loosely.

Notes, not deviations: the plan's `-k "fields or rename or footprint_consistency"` selector also matches the Task 2 tests `test_unit_fields_on_every_symbol` and `test_unit_parent_rename_updates_extends`; they pass after Task 2. The 04-01 refusals `install.rename_unsupported`, `install.extends_unsupported` and `install.no_property_template` are gone: renames and units are supported, and a symbol with no hidden property to clone gets `synth_property_text`.

## Known Stubs

None.

## Threat Flags

None. T-04-22: the model file name is `sanitize_filename(final MPN + suffix).sanitized`; `test_fields_value_injection_quoted` writes the hostile MPN `A") (x` as one quoted token and the file becomes `A_x.step`. T-04-23: every vendor and caller value passes through `quote` in the `kicad_files` helpers; renames touch only name tokens; planned libraries are re-parsed in the tests. The prohibition on changing existing symbols or headers holds by construction (edits run on the unit-only text) and is asserted by `test_fields_existing_symbols_untouched` for 20211014 and 20241209 targets.

## Issues Encountered

- The Bash tool rejects heredocs containing unbalanced quotes; patch scripts and test blocks were written with the Write tool and appended with `cat`.
- Requirements INST-02, INST-03 and INTK-08 are not marked complete: plan 04-10 also declares them and has no SUMMARY yet.

## Next Phase Readiness

- 04-09 and 04-10 can rely on `plan.symbol_names` being the whole unit (parent first), `plan.renames` listing symbol and footprint renames, and Conflict keys `symbol:<lib>:<name>` for each existing unit member.
- The real `Custom/` folder was never written: `git status --porcelain Custom` prints nothing.

## Self-Check: PASSED

`kicad_lib_manager/importer/planner.py` and `tests/test_install_plan.py` exist; commits `6170ea7`, `3b8af55`, `3743e0a`, `2df6e65` are ancestors of HEAD and `git rev-list --count` from `plan_head_before` is 4. Acceptance greps: every required code and helper name present in planner.py. `pytest tests/test_install_plan.py -k no_model` 9 passed; plan, e2e, apply, verify and layering files 193 passed; full suite 1255 passed, 4 skipped.

---
*Phase: 04-plan-and-install-core*
*Completed: 2026-10-20*
