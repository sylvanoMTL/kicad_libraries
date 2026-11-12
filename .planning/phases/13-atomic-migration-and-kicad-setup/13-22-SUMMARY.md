---
phase: 13-atomic-migration-and-kicad-setup
plan: 22
subsystem: migration
tags: [kicad, migration, atomic-rule, casefold, transaction, gap-closure]

requires:
  - phase: 13-atomic-migration-and-kicad-setup
    provides: "13-21's claimed-name registry for the model-rename clash (gap CR-01, first manifestation)"
provides:
  - "A casefolded existing-model guard in _model_final_names, closing CR-01's second manifestation on Windows"
  - "A structural migration.rename_would_overwrite invariant in the applier's _preflight, catching the whole defect class at the transaction boundary"
affects: [13-VERIFICATION, 13-REVIEW]

actuals:
  tokens: 4328
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Casefolded set membership for filesystem-identity comparisons (mirrors claimed_model_names)"
    - "Preflight invariant scoped by a dataclass marker field (source_rel) rather than filesystem content"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/migration/footprints.py
    - kicad_lib_manager/importer/migration/applier.py
    - tests/test_migration_e2e.py
    - tests/test_migration_footprints.py
    - tests/test_migration_apply.py

key-decisions:
  - "Casefold the existing-model guard inline in _model_final_names rather than calling naming.case_clash: one prebuilt O(1) set, no second issue-code vocabulary, and the exact-match branch directly above already uses this shape"
  - "Raise Severity.INFO migration.model_kept_name for a case-only collision, not a blocking migration.model_clash: the exact-match half of the same guard already does this, D-09 already settles a case-only clash by keeping the on-disk spelling, and nothing is destroyed so Run should stay enabled"
  - "Keep the guard comparing against the WHOLE pre-migration inventory, never a post-migration projection: this is what makes a rename chain (A renaming onto B while B renames away) structurally impossible, not merely reordered"
  - "Add a transaction-layer invariant (migration.rename_would_overwrite) scoped to writes carrying source_rel, as a backstop for the defect class rather than only this one instance -- the existing migration.duplicate_write check is structurally blind to a single-write-op shape"

requirements-completed: [MIG-02, MIG-03]

coverage:
  - id: D1
    description: "A 3D-model rename candidate colliding with an untouched, unlinked, pre-existing model file -- exactly or only by letter case -- keeps its own name, queues no op, and the untouched file's bytes survive a full plan/gate/apply run"
    requirement: MIG-03
    verification:
      - kind: unit
        ref: "tests/test_migration_e2e.py#test_model_rename_cannot_overwrite_an_untouched_model"
        status: pass
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_model_rename_colliding_by_case_with_an_unlinked_model_keeps_its_name"
        status: pass
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_model_rename_onto_an_exact_existing_name_keeps_its_name"
        status: pass
    human_judgment: false
  - id: D2
    description: "A rename chain (A renaming onto B while B itself renames away) is refused rather than reordered, because the guard compares against the whole pre-migration inventory"
    requirement: MIG-03
    verification:
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_a_rename_onto_a_model_that_is_itself_renamed_is_kept"
        status: pass
    human_judgment: false
  - id: D3
    description: "The kept-name note is a single plain-language INFO that names both files and never becomes a blocking strip line"
    requirement: MIG-02
    verification:
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_model_kept_name_note_is_plain_and_single"
        status: pass
      - kind: unit
        ref: "tests/test_migration_footprints.py#test_untouched_model_collision_raises_no_blocking_line"
        status: pass
    human_judgment: false
  - id: D4
    description: "A migration transaction refuses any rename write that would overwrite bytes the plan does not delete, before the first byte is touched, whichever planner path produced it"
    requirement: MIG-03
    verification:
      - kind: unit
        ref: "tests/test_migration_apply.py#test_rename_overwrite_plan_is_refused"
        status: pass
      - kind: unit
        ref: "tests/test_migration_apply.py#test_duplicate_write_plan_is_refused"
        status: pass
    human_judgment: false
  - id: D5
    description: "The pre-existing migration test suite (footprints, e2e, apply, gate, dialog, layering, and the slow whole-fixture run) stays green -- no legitimate plan trips either new check"
    verification:
      - kind: unit
        ref: "tests/test_migration_e2e.py, tests/test_migration_footprints.py, tests/test_migration_apply.py, tests/test_migration_gate.py, tests/test_migration_dialog_files.py, tests/test_migration_dialog_run.py, tests/test_importer_layering.py"
        status: pass
      - kind: unit
        ref: "tests/test_migration_full.py#test_whole_v1_custom_migrates_to_zero_violations"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-11-12
status: complete
---

# Phase 13 Plan 22: Casefolded model-rename guard and the rename-overwrite transaction invariant Summary

**Closed gap CR-01's second manifestation: `_model_final_names`'s existing-model guard now casefolds, and a new `migration.rename_would_overwrite` preflight check makes the whole defect class structurally impossible at the transaction boundary.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-11-12T11:35:00Z
- **Completed:** 2026-11-12T12:00:00Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments
- `_model_final_names`'s existing-model guard in `footprints.py` now compares a rename candidate's casefolded form against a prebuilt casefolded view of the whole pre-migration model inventory (`model_names_cf`), mirroring the already-correct `claimed_model_names` registry a few lines below it. A candidate that collides only by letter case with an untouched, unlinked model file now keeps its own name with one `Severity.INFO` `migration.model_kept_name` note, instead of silently producing a write op whose `base_sha256` is seeded from the unrelated file's own bytes.
- Six new regression tests prove the fix end to end: the full plan/gate/apply/disk round trip (`test_model_rename_cannot_overwrite_an_untouched_model`), the case-only and exact-match collision shapes, a rename chain (a candidate colliding with a model that is itself being renamed away stays refused, proving the guard's comparison is scoped to the whole pre-migration inventory and not a post-migration projection), the note's plain-language wording, and its non-blocking nature (`Run` stays enabled).
- Added a structural invariant to the migration applier's `_preflight`: `migration.rename_would_overwrite` refuses, before the first byte is touched, any write op carrying `source_rel` whose target existed at plan time and is removed by no delete op in the same plan. This is scoped to renames (the only emitter of `source_rel` in the package) and catches the defect class itself, not only this plan's one instance — a backstop for any future planner path that reintroduces the same mistake.
- Folded in review WR-01: `migration.duplicate_write`'s message now names both colliding write ops' own `rel` spelling instead of only the later one.

## Task Commits

Each task followed the RED -> GREEN TDD cycle:

1. **Task 1: Casefolded model-rename guard, proved end to end (tracer)**
   - `965c34d` test(13-22): add failing test for case-only model rename overwrite guard (RED)
   - `fafa6d1` feat(13-22): casefold the existing-model rename guard (GREEN)
2. **Task 2: Unit regressions for case-only, exact, chain, wording and non-blocking**
   - `278e4e3` test(13-22): add regressions for the casefolded model rename guard (test-only; the behavior was already correct after Task 1, so these five tests pass immediately — exactly as the plan's own text anticipated)
3. **Task 3: Transaction-layer rename-overwrite invariant**
   - `765843f` test(13-22): add failing test for the rename-overwrite preflight invariant (RED)
   - `5197cc2` feat(13-22): refuse a migration rename that would overwrite undeleted bytes (GREEN)

**Plan metadata:** (this commit)

_Note: Task 1 is `type="tracer"` — its tracer feedback gate (re-running `<verify>`'s automated pytest command) passed with 32/32, so Tasks 2 and 3 expanded without a checkpoint._

## Files Created/Modified
- `kicad_lib_manager/importer/migration/footprints.py` - `_model_final_names` casefolds its existing-model guard via a prebuilt `model_names_cf` set
- `kicad_lib_manager/importer/migration/applier.py` - `_preflight` gains the `migration.rename_would_overwrite` invariant; `migration.duplicate_write`'s message names both colliding ops
- `tests/test_migration_e2e.py` - `test_model_rename_cannot_overwrite_an_untouched_model` (full plan/gate/apply/disk round trip)
- `tests/test_migration_footprints.py` - five new unit regressions for the casefolded guard's case-only, exact, chain, wording and non-blocking shapes
- `tests/test_migration_apply.py` - `test_rename_overwrite_plan_is_refused`; `test_duplicate_write_plan_is_refused` extended to exercise and assert the WR-01 both-ops-named fix

## Decisions Made
- Casefold inline in `_model_final_names` rather than reusing `naming.case_clash` — see `key-decisions` in frontmatter for the three reasons recorded in the plan's `<objective>` (shape match with the existing exact-match branch, no second issue-code vocabulary, O(1) prebuilt set vs. a per-candidate list).
- The kept-name note stays `Severity.INFO`, not a blocking `migration.model_clash` — nothing is destroyed, the part's footprint keeps pointing at its existing model file, and the atomic rule only requires the model file exist.
- The existing-model guard keeps comparing against the whole pre-migration inventory (never a post-migration projection), which is what makes a rename chain structurally impossible rather than merely reordered — accepting an occasional conservative "kept" decision as the intended trade, unchanged from the exact-match guard's existing behavior.
- `migration.rename_would_overwrite` is a planner-bug backstop, not an owner-facing path: Task 1 already removes the planner path that could produce such an op, so this invariant exists so a future recurrence refuses loudly instead of destroying a file.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected `test_duplicate_write_plan_is_refused`'s own WR-01 assertion**
- **Found during:** Task 3 GREEN run
- **Issue:** My first version of the WR-01 assertion checked for `OLD1.step`/`OLD2.step` substrings in the `migration.duplicate_write` message, but those are the *delete* ops' `rel` values — the message only ever names the two colliding *write* ops, which in that test shared one identical `rel` spelling, so the assertion could never pass regardless of correctness.
- **Fix:** Rewrote the test so the two colliding write ops point at the same casefolded path but spell their own `rel` differently (a case-twin-shaped duplicate write: `COLLIDE.step` vs `collide.step`), then asserted both spellings appear in the message — which now genuinely proves WR-01 (both ops named, not only the later one) rather than asserting on fields the code never puts in that message.
- **Files modified:** `tests/test_migration_apply.py`
- **Verification:** `pytest tests/test_migration_apply.py -q` — 17/17 passed
- **Committed in:** `5197cc2` (folded into Task 3's GREEN commit, since it corrects the test assertion added in that same task's RED commit before GREEN was applied)

---

**Total deviations:** 1 auto-fixed (1 bug, test-assertion-only — no production code affected).
**Impact on plan:** None beyond the test file itself; the fix makes the WR-01 regression test actually test what it claims to test.

## Issues Encountered
- `Path(old_name).suffix` preserves the on-disk file's exact extension casing (e.g. `.STEP` vs `.step`), which the sanitiser also preserves — so a chain-rename candidate's final written filename follows the *source* model's extension case, not a normalized lowercase form. This was verified empirically (`test_a_rename_onto_a_model_that_is_itself_renamed_is_kept` asserts `FINAL7.STEP`, matching `OLD7.STEP`'s own casing) rather than assumed, and matches the existing single-group rename path's behavior unchanged by this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Verification gap CR-01 is closed on both manifestations (13-21's claimed-name registry for same-run collisions, and this plan's casefolded guard plus transaction-layer backstop for pre-existing on-disk collisions).
- This was the last blocking gap recorded in `13-VERIFICATION.md`. The owner's live migration UAT (`human_verification` item) is now unblocked, but is explicitly out of scope for this plan and must not be run from this development worktree (CLAUDE.md D-26) — it runs from the main checkout.
- Next step per `STATE.md`: re-run `/gsd-plan-phase 13` verification (or the orchestrator's equivalent) to confirm no further gaps, then the owner's live migration UAT from the main checkout.

---
*Phase: 13-atomic-migration-and-kicad-setup*
*Completed: 2026-11-12*

## Self-Check: PASSED

- FOUND: .planning/phases/13-atomic-migration-and-kicad-setup/13-22-SUMMARY.md
- FOUND: 965c34d (test commit, Task 1 RED)
- FOUND: fafa6d1 (feat commit, Task 1 GREEN)
- FOUND: 278e4e3 (test commit, Task 2)
- FOUND: 765843f (test commit, Task 3 RED)
- FOUND: 5197cc2 (feat commit, Task 3 GREEN)

## TDD Gate Compliance

| Plan | RED | GREEN | REFACTOR | Status |
|------|-----|-------|----------|--------|
| 13-22 | ✓ (965c34d, 765843f) | ✓ (fafa6d1, 5197cc2) | — (none needed) | Pass |
