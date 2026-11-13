---
phase: 13-atomic-migration-and-kicad-setup
plan: 09
subsystem: importer
tags: [migration, atomic-check, naming, keywords, kicad-cli, tdd]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "plan 13-06's migration architecture and final entry signatures for every migration module (planner, symbols, footprints, families, gate, mapfile, applier)"
provides:
  - "The complete symbol side of the Atomic_ migration planner: target validation, in-place edits, canonical fields, MPN defaulting and blanking, renames following extends, name-clash and parent-elsewhere blocking, keyword generation, one-file-format normalisation, and the missing-tool block"
affects: [13-12, 13-13, 13-14]

actuals:
  tokens: 12700
  tasks: 3
  commits: 5
  plan_head_before: f4d420948be3dc49328bf83823b58f3e7dbd8018
  plan_head_after: 47861f09aefb3679c942f4c135318c93a5f4e03f

tech-stack:
  added: []
  patterns:
    - "Validate and block before touching any file: name_verdict, parent-elsewhere and name-clash checks all run against the targets/new_names maps before a single byte of library text is read or edited, so a blocked part never gets a half-built op"
    - "Compute every part's prospective new_name up front (before any file I/O), so clash detection and a derived part's extends-forwarding can both consult it without re-deriving it per use"
    - "Normalise an existing target's format once per target (memoised), separately from each incoming unit's own new_source/existing_source normalisation, so a target with kept content and a target built fresh from one part converge on the same installed version either way"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/migration/symbols.py
    - tests/test_migration_symbols.py

key-decisions:
  - "ctx.allowed (ToolContext.allowed_stems) is treated as 'use the built-in KiCad 10 snapshot' whenever it is empty, matching its own documented default, by passing `ctx.allowed or None` into stems.name_verdict (which only applies that fallback for literal None, not for an empty frozenset); without this a ToolContext built without an explicit allowed_stems would refuse every target name, chosen or suggested alike"
  - "The 13-06 draft's 'assembled = loaded_target' preseed (the whole existing target file as the starting point) is replaced by a preseed stripped of every symbol that is itself migrating in this pass (keep_names = existing_names - migrating_here); every migrated part, whatever its source, is spliced in by the normal per-part loop. This is what makes a part that stays in its own target Atomic_ library get edited in place instead of duplicated, since its OWN existing block would otherwise survive in the preseed while a second, edited copy of it was also spliced in"
  - "A derived part's own unit (symbol_unit) always carries its parent (KiCad's extends chain), so the naive 'first part for a brand-new target is the whole edited unit' case is replaced with unit_library_text(edited, keep={new_name}) — keeping only the part actually being planned, dropping any unrenamed parent (or other stray content) that rode along in the same unit text"
  - "Parts within one target are ordered by extends depth before name (not name alone), so a parent is always processed, and already renamed, before any part that extends it; the child's own processing then adds a second rename_symbol_edits pass (old parent name -> parent's new name) against its own unit text, which updates its extends token even though the parent's portion of that same text is never itself spliced into the target (the parent got its own, separate, correctly-ordered block earlier)"
  - "Every still-candidate part's new_name is computed before any file is read, so clash detection (two parts, or a migrated part against one already committed in the target, landing on the same casefolded name) can run as a cheap pre-pass over name strings and existing_names sets, excluding the clashing parts from by_target before the costly per-part edit loop ever starts"
  - "part_mpns blanks a part's default MPN (never a typed choice) whenever that same default is shared, casefolded, by two or more parts of the WHOLE inventory — not just the parts sharing a target — matching the plan's 'across the migration' wording and the four-part LTC2954 fixture, which splits into two distinct-but-still-shared pairs"
  - "A blanked MPN passed through SymbolFields.mpn as the literal empty string, not None, is enough on its own: edit_symbol's role() treats an empty override as the chosen value directly (chosen = override if override is not None else ...), so no separate set_property_edit workaround was needed to force the MPN property blank"
  - "The 'file format updated' note is attached to every part landing in a target whose on-disk version actually changed under normalisation, not just the one part a test happens to check; idempotent for a target with several incoming parts, and cheap since it is one tuple comparison per part"

patterns-established:
  - "A migration rule that blocks a specific part (name_clash, parent_elsewhere, no_library) is represented the same way: an entry in one `blocked: dict[PartKey, Issue]`, excluded from by_target the same way, and surfaced through PartPlan.issues the same way, so gate.check_plan's existing per-part issue loop needs no new code per rule"

requirements-completed: [MIG-02, MIG-03]

coverage:
  - id: D1
    description: "Every fixture part the suggestion can place gets its Phase 10 suggested library by default; the IMU-style part's mis-suggestion (Atomic_Timer) and its owner-corrected placement (Atomic_Sensor_Motion) both pass through unchanged"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_default_targets_follow_the_suggestion"
        status: pass
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_imu_picked_library_passes_gate"
        status: pass
    human_judgment: false
  - id: D2
    description: "A part already in its own target Atomic_ library (the crystal staying in Atomic_Oscillator) is rewritten in place with no duplicate block"
    requirement: "MIG-03"
    verification:
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_crystal_stays_in_atomic_oscillator"
        status: pass
    human_judgment: false
  - id: D3
    description: "A chosen or suggested library name stems.name_verdict refuses (no KiCad stem, or a manufacturer token) blocks only that part with migration.no_library and the verdict's own reason, leaving the part's current library untouched and unmigrated"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_refused_library_name_blocks"
        status: pass
    human_judgment: false
  - id: D4
    description: "SnapEDA MF/MP aliases fold into canonical Manufacturer/MPN, Value tracks the final MPN, and price/stock/purchase-url leftovers are removed, each change listed in field_changes"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_snapeda_fields_become_canonical"
        status: pass
    human_judgment: false
  - id: D5
    description: "A symbol is renamed to its sanitised MPN (slashes and other unsafe characters become underscores); a typed symbol_name overrides the MPN and is itself sanitised; every rename is recorded old -> new"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_rename_to_sanitised_mpn"
        status: pass
    human_judgment: false
  - id: D6
    description: "A default MPN shared by two or more parts of the whole migration (the four LTC2954 symbols, pairwise) is blanked so the owner must type each orderable number; the two MAX17048 parts, whose defaults do not collide, keep their own Value as MPN"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_shared_default_mpn_is_blanked"
        status: pass
    human_judgment: false
  - id: D7
    description: "A typed MPN (including one with characters sanitize_name strips) sets the part's MPN and Value to the typed text exactly, and renames the symbol to its sanitised form"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_typed_mpn_renames_the_part"
        status: pass
    human_judgment: false
  - id: D8
    description: "Two parts choosing the same symbol name in one target block Run with one migration.name_clash issue naming both and the library; a migrated part named like a part already committed in the target library clashes the same way"
    requirement: "MIG-03"
    verification:
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_name_clash_blocks_run"
        status: pass
    human_judgment: false
  - id: D9
    description: "A derived part's rename follows its extends reference to the parent's own new name, with the parent's block ordered first in the target library; a derived part whose parent is heading to a different target blocks with migration.parent_elsewhere instead of migrating alone"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_rename_follows_extends"
        status: pass
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_parent_in_other_library_blocks"
        status: pass
    human_judgment: false
  - id: D10
    description: "Keywords start with the vendor's own existing ki_keywords text, followed by generated words not already present; a typed keyword override is written exactly as typed instead"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_keywords_merge_existing_first"
        status: pass
    human_judgment: false
  - id: D11
    description: "Every written target library ends in one KiCad file format, whatever format mix its sources and its own pre-existing content started in; without the KiCad command-line tool the whole migration blocks with migration.cli_missing instead of silently merging mixed formats"
    requirement: "MIG-03"
    verification:
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_existing_target_in_older_format_is_normalised"
        status: pass
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_missing_cli_blocks_run"
        status: pass
      - kind: unit
        ref: "tests/test_migration_symbols.py#test_all_targets_share_one_format"
        status: pass
    human_judgment: false

duration: 95min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 09: Symbol migration planner complete — targets, renames, fields, keywords, clashes, formats Summary

**`migration/symbols.py`'s `plan_symbols` now fully drives who moves where under what name: validated Atomic_ targets, in-place edits for parts staying in their own library, MPN defaulting with duplicate-blanking, sanitised renames that follow extends chains, name-clash and parent-elsewhere blocking, generated-and-merged keywords, and one normalised file format across every written target, with a plain-language block when the KiCad command-line tool is missing.**

## Performance

- **Duration:** ~95 min
- **Started:** 2026-11-11
- **Completed:** 2026-11-11
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- `target_libraries`/`stems.name_verdict` integration: a chosen or suggested library name that fails the Atomic_-plus-KiCad-stem rule blocks only that part (`migration.no_library`), leaving its library and content untouched rather than silently creating an invalid target
- Fixed a duplication bug inherited from the 13-06 tracer: a part already sitting in its own target Atomic_ library used to get a second, separately-inserted copy of its edited block alongside its untouched original; the target's preseed now excludes every symbol migrating in this same pass, so the part is rewritten in place
- `part_mpns` rebuilt on `_default_mpn` (MPN, else MP, else SNAPEDA_PN, else Value) with duplicate-blanking across the whole inventory (not just within one target), matching the four-part LTC2954 fixture exactly
- `_new_name` sanitises the typed symbol name or the MPN, falling back to the part's own name only when both are blank; renames are computed for every still-candidate part before any file is touched, enabling two new pre-edit blocking checks (`migration.parent_elsewhere`, `migration.name_clash`) that exclude the blocked part(s) from `by_target` before the costly per-part edit loop runs
- Parts within one target are ordered by extends depth so a parent is always processed, and renamed, before any part that extends it; the derived part's own processing then forwards the parent's old-to-new rename onto its own extends token
- Keywords: every part now carries a `generate_keywords`-backed `keyword_source` closure (target library, footprint package words, final canonical manufacturer, the suggestion's related stems minus the target's own stem) plus the caller's typed override, with the generated and written texts recorded on `PartPlan.generated_text`/`.part_text`
- `_normalised_target` upgrades an existing target's text once (memoised) through `kicad_cli.upgrade_symbol_text` before anything is spliced into it, so a target that already has kept content converges on the installed KiCad's format the same way a brand-new target does; a `FieldChange` notes "file format updated" on every part landing in a target whose version actually moved
- `ctx.tools.kicad_cli is None` now short-circuits the whole symbol plan with one `migration.cli_missing` ERROR and no ops, rather than letting each part fall through the importer's own per-part "merged unchanged" warning

## Task Commits

1. **Task 1: tracer — targets, in-place edits, canonical fields** - `cb386ff` (feat)
2. **Task 2 RED** - `3d9305b` (test) — six behaviour tests for D-05/D-06; four fail against the Task 1 implementation (shared-MPN blanking, name clash, rename-follows-extends, parent-elsewhere)
3. **Task 2 GREEN** - `2fb3cba` (feat) — `part_mpns`, `_new_name`, extends-depth ordering, clash and parent-elsewhere pre-pass; all eleven tests pass
4. **Task 3 RED** - `50229a9` (test) — four behaviour tests for D-11/F-13/A4; three fail against the Task 2 implementation (keywords, format normalisation, missing-tool block)
5. **Task 3 GREEN** - `47861f0` (feat) — keyword wiring, `_normalised_target`, the `migration.cli_missing` short-circuit; all fifteen tests pass

**Plan metadata:** commit pending (this SUMMARY)

## Files Created/Modified

- `kicad_lib_manager/importer/migration/symbols.py` - `plan_symbols` complete: name validation, in-place-edit fix, canonical manufacturer, `_default_mpn`, `part_mpns` (rebuilt), `_new_name`, `_extends_depth`, `_ClashEntry`/`_clash_issues`, `_normalised_target`, keyword wiring, `migration.cli_missing` short-circuit
- `tests/test_migration_symbols.py` - new file: 15 behaviour tests across the three tasks, plus local fixtures for a parent/derived family (`_write_family_tree`) and a part with existing vendor keywords (`_write_keyword_part`)

## Decisions Made

See `key-decisions` in the frontmatter for the seven implementation decisions; the most consequential is the in-place-edit fix (a real bug in the 13-06 tracer that this plan's own `test_crystal_stays_in_atomic_oscillator` would have caught had it existed earlier).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `manufacturer_forced` was always `False`, letting vendor data override an owner's typed Manufacturer choice**
- **Found during:** Task 1 (tracing `edit_symbol`'s `role()` against the plan's own wording "the part's SymbolFields take ... manufacturer_forced=choice.manufacturer is not None")
- **Issue:** The 13-06 draft passed `manufacturer_forced=False` unconditionally, so `edit_symbol`'s `role()` always treated the owner's choice as a mere fallback behind any existing vendor Manufacturer/MF value, rather than an override
- **Fix:** `manufacturer_forced=choice.manufacturer is not None`, with the fallback value itself now reading the vendor's own `Manufacturer`/`MF` field directly (previously `""`)
- **Files modified:** `kicad_lib_manager/importer/migration/symbols.py`
- **Verification:** no dedicated test (no fixture part exercises an owner-typed Manufacturer with a conflicting vendor value in this plan's scope); covered implicitly by every passing test that supplies no `choice.manufacturer` and relies on the vendor fallback
- **Committed in:** `cb386ff` (Task 1 commit)

**2. [Rule 1 - Bug] A part staying in its own target Atomic_ library was duplicated, not edited in place**
- **Found during:** Task 1, writing `test_crystal_stays_in_atomic_oscillator` against the inherited 13-06 implementation
- **Issue:** `assembled = loaded_target` preseeded the WHOLE existing target file (including the part about to be re-edited), and the per-part loop then spliced the edited copy in separately, leaving two blocks of the same symbol
- **Fix:** the preseed strips every symbol migrating in this same pass (`keep_names = existing_names - migrating_here`) before being used as the starting content; every migrated part, including one staying in its own current library, is then spliced in by the ordinary per-part loop exactly once
- **Files modified:** `kicad_lib_manager/importer/migration/symbols.py`
- **Verification:** `tests/test_migration_symbols.py::test_crystal_stays_in_atomic_oscillator` asserts exactly one `CM315D32768DZFT` symbol in the written library
- **Committed in:** `cb386ff` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs, both Rule 1). **Impact on plan:** Both were required for Task 1's own behaviour tests and this plan's `<verify>` to pass; no scope creep.

## TDD Gate Compliance

Task 2 and Task 3 (`tdd="true"`) gate sequences, verified against `git log -E --grep` with the zero-padded `(0*13)-(0*9)` scope match:

| Task | Gate | Commit | Pattern | Status |
|------|------|--------|---------|--------|
| 2 | RED | `3d9305b` | `test(13-09): ...` | Present — four of six new tests failed against the Task 1 implementation for the planned reason (assertion mismatches on blanked MPN, missing clash issue, duplicated/unrenamed parent block, missing parent-elsewhere issue), not a collection or import error |
| 2 | GREEN | `2fb3cba` | `feat(13-09): ...` | Present — all eleven tests in `tests/test_migration_symbols.py` pass |
| 2 | REFACTOR | — | `refactor(13-09): ...` | Not needed — no cleanup opportunity after GREEN |
| 3 | RED | `50229a9` | `test(13-09): ...` | Present — three of four new tests failed against the Task 2 implementation for the planned reason (empty keyword text, stale target format, no cli_missing issue), not a collection or import error |
| 3 | GREEN | `47861f0` | `feat(13-09): ...` | Present — all fifteen tests pass |
| 3 | REFACTOR | — | `refactor(13-09): ...` | Not needed — no cleanup opportunity after GREEN |

**RED evidence:** established by running `python -m pytest tests/test_migration_symbols.py -q --tb=short` directly (via the Bash tool, inside this isolated worktree) and inspecting each failure's traceback before committing the test-only RED state, then restoring the GREEN implementation and re-running the same command to confirm all tests passed before the GREEN commit. `gsd_run check tdd-red-evidence`'s machine-validated record pipeline was unavailable in this isolated worktree (no `.claude/gsd-core/` present), the same caveat recorded in `13-06-SUMMARY.md`. Every RED failure was a genuine assertion mismatch on the planned behaviour (shown in each commit message above), never a `nonzero_exit_without_test_failure`/`zero_tests_discovered`/`fixture_or_load_failure` class of failure.

**Task 1 note:** Task 1 is `type="tracer"`, not `tdd="true"`; it was committed as a single `feat` commit per the tracer execution rule. Its own `<verify>` (`tests/test_migration_symbols.py tests/test_migration_e2e.py tests/test_importer_layering.py`) was re-run and passed before Task 2 began (the tracer feedback gate); `HUMAN_VERIFY_MODE` is `end-of-phase` (project default) and the task's `<verify>` carries only `<automated>` checks, so per the tracer feedback gate's row 3 this continued straight to Task 2 without a checkpoint.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `migration/symbols.py`'s `plan_symbols` is complete for every behaviour this plan's `must_haves.truths` named; plans 13-10 (`footprints.py`), 13-11 (`families.py`), 13-12 (`gate.py`/`mapfile.py`), 13-13 (`applier.py`/`commitplan.py`) and 13-14 (`widgets/migration_dialog.py`) can deepen their own modules independently
- `footprints.py`'s `package_words`/`texts`/`field_changes` stubs (still `{}` as left by 13-06) are consumed by `symbols.py` exactly as before; once 13-10 fills them in, `PartPlan.generated_text`/`.part_text` will carry both the footprint's own generated text (fp_description/fp_tags, 13-10's job) and this plan's keyword text (already wired) without any further change here
- `families.py`'s `find_families`/`derived_edits` stubs (still returning nothing, as left by 13-06) are unaffected by this plan: the extends-following and parent-elsewhere logic here operates on each symbol's OWN pre-existing `(extends ...)` relationship read straight from the source file by `read_inventory`, not on 13-11's not-yet-filled family-derivation decisions. 13-11 fills a different, additive case (grouping separate standalone symbols into a NEW derived relationship, D-06's "variant families"); nothing in this plan assumes that case is handled yet, and nothing here will need to change once it is
- No blockers

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED

- `kicad_lib_manager/importer/migration/symbols.py` — FOUND
- `tests/test_migration_symbols.py` — FOUND
- Commit `cb386ff` (Task 1 feat) — FOUND on this branch
- Commit `3d9305b` (Task 2 RED test) — FOUND on this branch
- Commit `2fb3cba` (Task 2 GREEN feat) — FOUND on this branch
- Commit `50229a9` (Task 3 RED test) — FOUND on this branch
- Commit `47861f0` (Task 3 GREEN feat) — FOUND on this branch
- All three tasks' `<acceptance_criteria>` greps re-verified: `EXPECTED_TARGETS|Atomic_Battery_Management|Atomic_Sensor_Motion` → 0 matches; `migration.name_clash|migration.parent_elsewhere` → both found; `migration.cli_missing` → found
- Plan-level `<verification>` re-run: `pytest tests/test_migration_symbols.py tests/test_migration_e2e.py tests/test_importer_layering.py tests/test_plain_names.py -q` → 38 passed
