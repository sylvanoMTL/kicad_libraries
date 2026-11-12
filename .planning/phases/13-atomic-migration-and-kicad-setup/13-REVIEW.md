---
phase: 13-atomic-migration-and-kicad-setup
reviewed: 2026-11-12T00:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - kicad_lib_manager/importer/migration/applier.py
  - kicad_lib_manager/importer/migration/footprints.py
  - tests/test_migration_apply.py
  - tests/test_migration_e2e.py
  - tests/test_migration_footprints.py
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase 13: Code Review Report (incremental, gap-closure 13-22)

**Reviewed:** 2026-11-12T00:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

This is a follow-up review of gap-closure plan 13-22, which re-opened CR-01 from the prior review
(the 13-21 pass fixed `_model_final_names`'s claimed-name registry for group-vs-group model-rename
collisions, but left the existing-model guard exact-string/case-sensitive while the write op it
feeds targets a case-insensitive Windows filesystem).

I traced the fix end to end against the exact diff (`git diff f9ea762..HEAD` on both source files):

- `footprints.py`: `_model_final_names` now builds `model_names_cf = {name.casefold() for name in
  model_name_set}` and tests `candidate.casefold() in model_names_cf` instead of the old
  `candidate in model_name_set and candidate != old_name`. This closes the exact hole CR-01
  described — a candidate that differs from an untouched, on-disk model only by case now correctly
  falls into the `migration.model_kept_name` INFO branch instead of silently queuing a write that
  would clobber the unrelated file. I confirmed the guard fires *before* any write op is appended
  (the `continue` happens inside the per-group loop at the point the write would otherwise be
  queued at lines 478-490), so there is no code path left where a case-only collision with an
  untouched model reaches `ops.append(MigrationOp("write", ...))`.
- `applier.py`: `_preflight` gained a second, independent backstop — `migration.rename_would_overwrite`
  — that refuses any `write` op whose `source_rel` is set (i.e. a model rename, the only emitter of
  that field in the package) and whose target already holds content (`base_sha256 is not None`)
  that no `delete` op in the same plan removes. This is scoped tightly enough that it does not
  false-positive on the legitimate chain-rename case (`test_a_rename_onto_a_model_that_is_itself_renamed_is_kept`)
  or on footprint-clash Overwrite writes (which never set `source_rel`).
- The previously-flagged WR-01 (`migration.duplicate_write` naming only the last-seen colliding op)
  is fixed: the message now names both `write_paths[key].rel` and `duplicate_ops[key].rel`,
  confirmed by `test_duplicate_write_plan_is_refused` asserting both spellings appear in the text.
- The previously-flagged IN-01 (no regression test for a rename colliding with an untouched,
  unlinked model) is fixed: `test_migration_footprints.py` adds
  `test_model_rename_colliding_by_case_with_an_unlinked_model_keeps_its_name`,
  `test_model_rename_onto_an_exact_existing_name_keeps_its_name`,
  `test_a_rename_onto_a_model_that_is_itself_renamed_is_kept`,
  `test_model_kept_name_note_is_plain_and_single`, and
  `test_untouched_model_collision_raises_no_blocking_line`; `test_migration_apply.py` adds
  `test_rename_overwrite_plan_is_refused` for the new applier-level backstop; and
  `test_migration_e2e.py` adds `test_model_rename_cannot_overwrite_an_untouched_model`, which proves
  the fix through plan, gate, apply and a final disk read of the previously-doomed file. All of
  these exercise the exact scenario the prior review's reproduction script hit.

I did not find a new data-loss or security-class defect in this diff. I did find one residual
diagnostic-quality gap in the new applier backstop, in the same spirit as the already-fixed WR-01.

## Warnings

### WR-01: `migration.rename_would_overwrite` names only the write op's destination, not the rename's source

**File:** `kicad_lib_manager/importer/migration/applier.py:279-284`

**Issue:** The new preflight check's message is:

```python
f"{op.rel} would overwrite a file this migration does not remove; nothing was written"
```

This names the write's destination (`op.rel`) but not `op.source_rel` — the file whose rename
produced the colliding write. The function's own docstring frames this check as a backstop for "a
planner bug" that should "never reach an owner", i.e. the audience is a developer debugging why a
future regression tripped this refusal, not an end user. For that audience, knowing only the
destination path leaves them to search the rest of the plan for which rename op is at fault; naming
the source directly (available on the very `op` already being formatted) would save that step. This
is the identical class of diagnostic gap the prior review raised as WR-01 for
`migration.duplicate_write` (now fixed by naming both colliding ops) — the same reasoning applies
here since `source_rel` is already attached to the op and unused.

**Fix:**

```python
issues = [
    _err(
        "migration.rename_would_overwrite",
        f"{op.rel} would overwrite a file this migration does not remove "
        f"(renamed from {op.source_rel}); nothing was written",
    )
    for op in rename_writes
]
```

Add an assertion to `test_rename_overwrite_plan_is_refused` (in `tests/test_migration_apply.py`)
that `"Custom/3DModels/OLD1.step" in overwrite_issues[0].text` (the `source_rel` of the planted
write op), alongside the existing destination-path assertion.

---

_Reviewed: 2026-11-12T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
