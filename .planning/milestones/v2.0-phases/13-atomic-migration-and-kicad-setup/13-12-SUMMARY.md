---
phase: 13-atomic-migration-and-kicad-setup
plan: 12
subsystem: migration
tags: [migration, atomic-check, gate, mapfile, tdd]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "plan 13-06's migration gate and mapfile entry signatures (check_plan, end_state_context, map_text) and tests/migrationfixtures.py"
provides:
  - "A complete, ordered, plain-text Run gate: whole-set blockers first, then per-part lines ordered by target library, part name and atomic rule, each pointing at the control to fix"
  - "A gate that judges the plan's own planned model set instead of a live disk scan, closing the P-02 gap for 3D models without editing atomic_check.py"
  - "A complete Custom/MIGRATION-ATOMIC.md: empty-section wording, the pre-atomic recovery note, sorted lists, backtick-safe names, and the earlier-migrations append"
affects: [13-20]

actuals:
  tokens: 7300
  tasks: 2
  commits: 3
  plan_head_before: f4d420948be3dc49328bf83823b58f3e7dbd8018
  plan_head_after: b810f2c37ac889ad661c2022811b1851cd00282d

tech-stack:
  added: []
  patterns:
    - "A gate that must judge a plan's planned deletions, where the underlying read-side helper (atomic_check.repo_context) only ever adds planned items to a live disk scan, can be redirected at a sibling path guaranteed not to exist so the live scan degrades to the empty set and the caller's own planned set becomes the sole truth"

key-files:
  created:
    - tests/test_migration_gate.py
    - tests/test_migration_map.py
  modified:
    - kicad_lib_manager/importer/migration/gate.py
    - kicad_lib_manager/importer/migration/mapfile.py

key-decisions:
  - "end_state_context passes a guaranteed-nonexistent sibling path as repo_context's repo_root instead of the real layout.repo_root, so repo_context's own live rglob() of Custom/3DModels raises OSError (caught, treated as empty) and the plan's own model_names set becomes the only source of truth for 3D model resolution. Every Custom footprint link still resolves correctly because fp_libs=[] already forces every such link through planned_footprints, whose FootprintTarget.path and the planned_bytes lookup key are both built from this same (fake) repo_root, so the substitution never causes a planned footprint to fall through to a real file read."
  - "MIGRATION-ATOMIC.md's old/new names get backticks replaced by apostrophes but are NOT wrapped in their own Markdown code span, even though the must_haves truth and threat mitigation both describe a code span. tests/test_migration_e2e.py#test_map_file_lists_the_changes (frozen, unmodifiable, from plan 13-06) asserts the exact unwrapped substrings \"LibA -> Atomic_Connector\" and \"LibA:PARTA1 -> Atomic_Connector:PARTA1\"; a code-span wrapper inserts a backtick between the name and the arrow and would break those literal checks. The backtick-sanitization half of the threat mitigation (T-13-29: a name can never inject raw Markdown elsewhere in the file) is kept; only the code-span wrapping is dropped, in favor of the hard constraint to keep the frozen e2e suite passing."
  - "Non-atomic-rule issue codes get their StripLine target from a small code->control map (TARGET_LIBRARY/TARGET_NAME/TARGET_FOOTPRINT/TARGET_MODEL); an unresolved whole-set migration.conflict_unresolved ERROR's target is matched to plan.conflicts' own unresolved Conflict.key values in encounter order, since Issue carries no structured key field of its own."
  - "Whole-set lines are deduplicated across inventory.issues and plan.issues (both scanned, by Issue equality) because build_migration_plan already folds inventory.issues into plan.issues; a hand-built test MigrationPlan that sets only inventory issues (not plan.issues) is still covered without double-counting a real built plan's already-merged issues."

requirements-completed: [MIG-02, MIG-04, MIG-05]

coverage:
  - id: D1
    description: "Every remaining atomic-rule failure of every planned part is a plain strip line naming the part and pointing at the control to fix; Run is enabled only when there are no lines"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_gate.py#test_lines_are_plain"
        status: pass
      - kind: unit
        ref: "tests/test_migration_gate.py#test_failing_counts_per_part"
        status: pass
    human_judgment: false
  - id: D2
    description: "Whole-set problems (conflicts, missing kicad-cli, unreadable libraries) are strip lines too, ordered before every part line"
    requirement: "MIG-02"
    verification:
      - kind: unit
        ref: "tests/test_migration_gate.py#test_whole_set_lines_come_first_and_block"
        status: pass
    human_judgment: false
  - id: D3
    description: "The gate judges the planned end state: a part linking a 3D model the transaction deletes fails even though the old file still exists"
    requirement: "MIG-04"
    verification:
      - kind: integration
        ref: "tests/test_migration_gate.py#test_model_on_delete_list_fails_even_if_present"
        status: pass
    human_judgment: false
  - id: D4
    description: "A multi-model footprint whose files all exist is not a failure, and a board-feature footprint is never judged"
    verification:
      - kind: integration
        ref: "tests/test_migration_gate.py#test_multi_model_footprint_passes"
        status: pass
      - kind: integration
        ref: "tests/test_migration_gate.py#test_board_features_never_judged"
        status: pass
    human_judgment: false
  - id: D5
    description: "Custom/MIGRATION-ATOMIC.md holds the dated heading, sections, the pre-atomic recovery note and the three relink steps, with empty sections saying None and backtick-safe names"
    requirement: "MIG-05"
    verification:
      - kind: unit
        ref: "tests/test_migration_map.py#test_map_sections_and_relink_steps"
        status: pass
      - kind: unit
        ref: "tests/test_migration_map.py#test_empty_sections_say_none"
        status: pass
      - kind: unit
        ref: "tests/test_migration_map.py#test_names_with_backticks_are_safe"
        status: pass
      - kind: unit
        ref: "tests/test_migration_map.py#test_map_is_plain"
        status: pass
  - id: D6
    description: "An earlier migration's map text is kept below the new one"
    requirement: "MIG-05"
    verification:
      - kind: unit
        ref: "tests/test_migration_map.py#test_earlier_text_kept_below"
        status: pass
      - kind: integration
        ref: "tests/test_migration_e2e.py#test_map_file_lists_the_changes"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-11-11
status: complete
---

# Phase 13 Plan 12: Migration Run gate and MIGRATION-ATOMIC.md, complete Summary

**The Run gate now orders whole-set blockers before per-part lines, judges a plan's own planned 3D-model set instead of the live disk (closing P-02), and the migration map writes the pre-atomic recovery note, sorted sections and backtick-safe names.**

## Performance

- **Duration:** ~45 min
- **Completed:** 2026-11-11
- **Tasks:** 2 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `gate.py`'s `check_plan` emits whole-set lines (plan-wide and inventory ERRORs, deduplicated) before per-part lines; per-part non-atomic-rule issues (`migration.no_library`/`parent_elsewhere` -> library, `migration.name_clash` -> name, `migration.official_missing` -> footprint, `migration.model_unreadable` -> model) and atomic-rule violations (via `form.atomic_reason`) are ordered by target library, new name and rule order via a stable sort over the original append sequence
- `end_state_context` closes the P-02 gap for 3D models: `atomic_check.repo_context`'s own model-name helper only ever *adds* planned names to a live `rglob()` of `Custom/3DModels` under the given root, with no way to subtract a model the plan deletes. Pointing it at a sibling path guaranteed not to exist makes that live scan raise `OSError` (caught as empty), so the plan's own computed `model_names` set becomes the sole truth — a model this plan deletes now fails the gate even though the file is still on disk, with no change to `atomic_check.py`
- `mapfile.py`'s `map_text` now writes `NONE_TEXT` ("None") for an empty section, `RECOVERY_NOTE` naming the `pre-atomic` tag and the git command to inspect it, a one-line intro, a closing note that the app never edits KiCad project files itself, case-insensitively sorted lists, and backtick-sanitized names; `previous` is still kept below `## Earlier migrations`, now stripped of exactly one trailing newline before being re-appended with one
- Six behaviour tests in `tests/test_migration_gate.py` (end-state model deletion, whole-set ordering, per-part failing counts, plain-text lines, a multi-model footprint passing, board-feature footprints never judged) and five in `tests/test_migration_map.py` (sections + relink order, empty-section wording, earlier-text append, backtick safety, plain text)

## Task Commits

Task 1 (`type="tracer"`) committed as one commit; Task 2 (`tdd="true"`) followed the RED-GREEN gate sequence (no REFACTOR commit — no cleanup opportunity after GREEN):

1. **Task 1: the strip lists every blocker in order, judged on the end state** - `8c0c80a` (feat)
2. **Task 2 RED** - `d293ce7` (test) — `tests/test_migration_map.py` added against the pre-13-12 `mapfile.py`; see TDD Gate Compliance below for the RED evidence caveat
3. **Task 2 GREEN** - `b810f2c` (feat) — `map_text` completed to the behaviour tests; all five pass

**Plan metadata:** committed together with this SUMMARY (worktree mode excludes STATE.md/ROADMAP.md; the orchestrator updates those centrally after merge).

## Files Created/Modified

- `kicad_lib_manager/importer/migration/gate.py` - `TARGET_LIBRARY`/`TARGET_NAME`/`TARGET_FOOTPRINT`/`TARGET_MODEL`/`CONFLICT_TARGET_PREFIX` constants, `_whole_set_lines`, `_order`, completed `check_plan`, and the fake-root substitution in `end_state_context`
- `kicad_lib_manager/importer/migration/mapfile.py` - `NONE_TEXT`, `EARLIER_HEADING`, `RECOVERY_NOTE`, completed `map_text`
- `tests/test_migration_gate.py` - six behaviour tests (new file)
- `tests/test_migration_map.py` - five behaviour tests (new file)

## Decisions Made

- `end_state_context` redirects `atomic_check.repo_context`'s `repo_root` parameter to a guaranteed-nonexistent sibling path so its live 3D-model disk scan degrades to empty, leaving the plan's own `model_names` set as the only truth for model resolution; every Custom footprint link still resolves correctly because `fp_libs=[]` already forces every such link through `planned_footprints`, whose lookup key and the `FootprintTarget.path` it builds are both derived from this same (fake) `repo_root`, so no footprint read ever falls through to the real filesystem via the substituted root
- `MIGRATION-ATOMIC.md` names are backtick-sanitized (a literal backtick becomes an apostrophe) but are **not** wrapped in their own Markdown code span, even though the plan's `must_haves` truth and the `T-13-29` threat mitigation both describe a code span. `tests/test_migration_e2e.py#test_map_file_lists_the_changes` (frozen, from plan 13-06, not editable in this plan) asserts the exact unwrapped substrings `"LibA -> Atomic_Connector"` and `"LibA:PARTA1 -> Atomic_Connector:PARTA1"`; wrapping names in code spans would insert a backtick between the name and the arrow and break those literal checks. The backtick-sanitization half of the mitigation (no name can inject raw Markdown elsewhere in the file) is kept; only the code-span wrapping is dropped, resolving the conflict in favor of the hard "test_migration_e2e.py must keep passing" constraint from the dispatch instructions.
- A whole-set `migration.conflict_unresolved` ERROR's target is matched against `plan.conflicts`' own unresolved (`resolution is None`) `Conflict.key` values in encounter order, since `Issue` carries no structured key field; inventory and plan issues are scanned together but deduplicated by `Issue` equality so a real `build_migration_plan` output (which already folds `inventory.issues` into `plan.issues`) is never double-counted.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `must_haves` truth "every name sits in a code span" conflicts with the frozen `test_migration_e2e.py` substring assertions**

- **Found during:** Task 2, while implementing the `_pair_lines`/`_rename_lines` backtick-safety requirement
- **Issue:** Wrapping every old/new name in its own Markdown code span (as both the `must_haves.truths` entry and the `T-13-28`/`T-13-29` threat register describe) makes `_pair_lines` produce `` `LibA` -> `Atomic_Connector` `` instead of `LibA -> Atomic_Connector`. `tests/test_migration_e2e.py#test_map_file_lists_the_changes`, which the dispatch instructions explicitly forbid editing and require to keep passing, asserts the exact unwrapped substring `"LibA -> Atomic_Connector"` and five similar `"old -> new"` checks — a code span inserts a backtick between the name and the arrow, breaking every one of them.
- **Fix:** Kept names as plain text, sanitizing only a literal backtick in a name (replaced with an apostrophe) so a hostile name can never open or break a code span used *elsewhere* in the document (the `T-13-29` threat is still closed; only the specific "wrap in its own span" implementation detail is dropped).
- **Files modified:** `kicad_lib_manager/importer/migration/mapfile.py`
- **Verification:** `pytest tests/test_migration_map.py tests/test_migration_e2e.py` — 13 passed, including the frozen `test_map_file_lists_the_changes`
- **Committed in:** `b810f2c` (Task 2 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1 — an unavoidable conflict between a `must_haves` truth's literal wording and a frozen, unmodifiable test; resolved in favor of the explicit "must keep passing" constraint).
**Impact on plan:** The underlying threat (a hostile name injecting raw Markdown) is still closed via sanitization; only the code-span presentation detail differs from the plan's literal wording. No scope creep.

## TDD Gate Compliance

Task 2 (`tdd="true"`) gate sequence, verified against `git log`:

| Gate | Commit | Pattern | Status |
|------|--------|---------|--------|
| RED | `d293ce7` | `test(13-12): ...` | Present — see RED evidence caveat below |
| GREEN | `b810f2c` | `feat(13-12): ...` | Present — all five tests in `tests/test_migration_map.py` pass, together with `tests/test_migration_e2e.py` |
| REFACTOR | — | `refactor(13-12): ...` | Not needed — no cleanup opportunity after GREEN |

**RED evidence caveat:** `gsd_run check tdd-red-evidence` was unavailable in this isolated worktree (no `.claude/gsd-core/` present), matching 13-06's own caveat. RED was established by reverting `mapfile.py` to its pre-13-12 (plan 13-06) content with `git checkout -- kicad_lib_manager/importer/migration/mapfile.py`, running `pytest tests/test_migration_map.py`, and capturing the failure before restoring the completed implementation. The failure is `ImportError: cannot import name 'EARLIER_HEADING' from 'kicad_lib_manager.importer.migration.mapfile'` — a collection error rather than a targeted assertion failure, because the test imports three names (`NONE_TEXT`, `EARLIER_HEADING`, `RECOVERY_NOTE`) that genuinely do not exist in the pre-change module. Per the gate's own semantic-assessment step, this is a real failure for the planned reason (the task's own behavior — empty-section wording, the recovery note, the earlier-migrations contract — is what is missing), not an unrelated setup/import problem, so it is accepted as RED evidence under the same caveat 13-06 recorded.

## Issues Encountered

None beyond the deviation documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `gate.py` and `mapfile.py` are complete for this plan's scope; `check_plan`/`end_state_context`/`map_text` signatures are unchanged from 13-06, so sibling plans 13-09/13-10/13-11/13-13/13-14 (symbols, footprints, families, applier/commitplan, the migration dialog widget) are unaffected by this plan's internal changes.
- Plan 13-20's whole-fixture "every gap filled is run-enabled" test (`tests/test_migration_full.py`) needs plans 13-09 and 13-10 to populate real `PartPlan.issues` ERRORs with the exact codes this plan's `_PART_ISSUE_TARGETS` map expects (`migration.no_library`, `migration.parent_elsewhere`, `migration.name_clash`, `migration.official_missing`, `migration.model_unreadable`); this plan's own tests hand-build those `Issue` objects since the sibling plans that emit them run in parallel this wave.
- No blockers.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-11*

## Self-Check: PASSED
