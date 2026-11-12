---
phase: 13-atomic-migration-and-kicad-setup
reviewed: 2026-11-12T10:15:40Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - kicad_lib_manager/importer/migration/applier.py
  - kicad_lib_manager/importer/migration/footprints.py
  - tests/test_migration_apply.py
  - tests/test_migration_footprints.py
findings:
  critical: 1
  warning: 1
  info: 1
  total: 3
status: issues_found
---

# Phase 13: Code Review Report (incremental, gap-closure 13-21)

**Reviewed:** 2026-11-12T10:15:40Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

This is a follow-up review of the 13-21 gap-closure for CR-01 (two 3D-model rename groups
claiming the same on-disk file name). The three changes under review — the `_model_final_names`
claimed-name registry in `footprints.py`, the `migration.duplicate_write` preflight backstop in
`applier.py`, and the `migration.overwrite_refused` check in `_resolve_clash` — are each correct
for the scenario they target: model-group-vs-model-group collisions are detected
case-insensitively and deterministically (the sorted walk over `model_groups.items()` makes the
"first claimer" stable across runs), the applier refuses before any byte is written when two
writes land on one path, and an Overwrite resolution can no longer be used to sneak a second write
onto a name this run has already queued for another part.

However, the model-rename side of the fix is incomplete: `_model_final_names` checks a proposed
rename candidate against `model_name_set` with **case-sensitive** Python string membership, while
the write op it then emits is placed via a **case-insensitive** real filesystem path
(`new_path.exists()` on Windows, the project's primary platform per `.claude/CLAUDE.md`). A
renamed model whose new name differs only by case from an unrelated, untouched, pre-existing
model file silently clobbers that unrelated file's content — with zero issues raised and the
migration reporting success. I reproduced this end-to-end against the actual code (not just by
inspection): `apply_migration` returned `ok=True` while an untouched `TAKEN.STEP` file's content
was overwritten with a different part's model data. This is the same destructive class of defect
as the original CR-01, just reached through a different path that the gap-closure did not close.

## Critical Issues

### CR-01: `_model_final_names`'s existing-model check is case-sensitive while the filesystem it protects is not — silent data loss

**File:** `kicad_lib_manager/importer/migration/footprints.py:329` (guard), with the unguarded
write emitted at `kicad_lib_manager/importer/migration/footprints.py:477-489`

**Issue:**

In `_model_final_names`, the guard meant to stop a rename candidate from colliding with an
existing, not-being-renamed model file is:

```python
if candidate in model_name_set and candidate != old_name:
    issues.append(Issue(Severity.INFO, "migration.model_kept_name", ...))
    model_final_name[old_name] = old_name
    continue
```

`model_name_set` is `frozenset(inventory.models)` — every model file name read verbatim off disk
(`inventory.py` line 184, `_safe_walk`). The membership test `candidate in model_name_set` is
exact-string, case-sensitive. But the write op this function's result later drives
(`plan_footprints`, lines 477-489) targets the real filesystem:

```python
new_path = layout.models_dir / new_name
...
existing_bytes = new_path.read_bytes() if new_path.exists() else None
base_sha256 = hashlib.sha256(existing_bytes).hexdigest() if existing_bytes is not None else None
ops.append(MigrationOp("write", new_path, new_rel, data=data, base_sha256=base_sha256, source_rel=old_rel))
```

`new_path.exists()` is a real OS call — case-insensitive on Windows (the stated primary and only
currently-supported platform, `.claude/CLAUDE.md` "Platform Requirements"). So a candidate name
that differs from an unrelated, untouched, on-disk model only by letter case sails straight past
the `model_name_set` guard (case-sensitive miss) and then gets correctly detected as "a file
already sits there" by `new_path.exists()` (case-insensitive hit) — except by this point there is
no clash-resolution path left to take: the code just seeds `base_sha256` from the unrelated file's
*current* content and queues a write that will overwrite it. The preflight staleness check in
`applier.py` then passes (the hash matches, because nothing modified that file between planning
and apply), so the write proceeds. The unrelated file is destroyed with no issue, warning, or
`migration.model_clash`/`migration.model_kept_name` of any kind — the run reports
`migration.done`, success.

This is the identical case-insensitive-collision risk CR-01 was opened for, now in a form the
13-21 gap-closure explicitly aimed at (and did fix) for model-group-vs-model-group, but did not
fix for model-group-vs-untouched-model. Note `kicad_lib_manager/importer/naming.py` already has a
`case_clash(name, existing)` helper built for exactly this comparison, but `_model_final_names`
does not use it.

Reproduced end-to-end (script run against the real `plan_footprints`/`apply_migration`, not a
hypothetical): a footprint's model `OLD1.step` (content `b"OLD1-CONTENT"`) renamed via
`PartChoice(model_name="taken")`, with an unrelated untouched model `TAKEN.STEP` (content
`b"UNRELATED-ORIGINAL-CONTENT"`) already on disk and linked by nothing in this migration:

```
ISSUES:                                           (empty — nothing was raised)
MODEL RENAMES: (Rename(kind='model', old='OLD1.step', new='taken.step'),)
WRITE OP: Custom/3DModels/taken.step base_sha256=9e5ec00e...dded8 data=b'OLD1-CONTENT'
          (base_sha256 above is sha256(b'UNRELATED-ORIGINAL-CONTENT') — confirmed by hand)

=== apply_migration ===
apply ok: True
 issue: success migration.done Migrated 0 parts into 0 Atomic_ libraries
TAKEN.STEP content AFTER migration: b'OLD1-CONTENT'   <- destroyed
```

The applier's new `migration.duplicate_write` backstop (Task 2 of 13-21) does **not** catch this,
because there is only one write op in the plan — the pre-existing `TAKEN.STEP` is never referenced
by any op, so there is nothing for the duplicate-path check to compare against. This vector is
structurally outside what that backstop can see.

**Fix:** Make the existing-model guard case-insensitive, matching how `claimed_model_names` was
already built correctly for the D-15 added-model path a few lines below it:

```python
model_names_cf = {name.casefold() for name in model_name_set}
...
for old_name, group in sorted(model_groups.items()):
    ...
    candidate = sanitize_filename(f"{stem}{ext}").sanitized
    if candidate.casefold() == old_name.casefold():
        model_final_name[old_name] = old_name
        continue
    if candidate.casefold() in model_names_cf:
        issues.append(
            Issue(Severity.INFO, "migration.model_kept_name",
                  f"{old_name}: kept, {candidate} is already used by a different model")
        )
        model_final_name[old_name] = old_name
        continue
    ...
```

(The `candidate != old_name` exact check becomes redundant once case-folded, since the preceding
`candidate.casefold() == old_name.casefold()` branch already handles that case and returns first.)
Add a regression test mirroring `test_colliding_model_names_are_case_insensitive` but with the
second "model" being an untouched, unlinked file rather than another rename group — e.g. seed a
`TAKEN.STEP` nothing links, choose `model_name="taken"` for a part whose own model is being
renamed, and assert `migration.model_kept_name` (or an ERROR) is raised and no write op targets
`Custom/3DModels/taken.step`.

## Warnings

### WR-01: `migration.duplicate_write` can name the wrong colliding op when paths differ only by case

**File:** `kicad_lib_manager/importer/migration/applier.py:243-259`

**Issue:** When two or more write ops collide on the same casefolded path, `duplicate_ops[key]`
is overwritten by each later match, so the reported `.rel` in the issue text is always the *last*
colliding op seen, not necessarily the first (`write_paths[key]`). If the two ops differ only in
case (e.g. `COLLIDE.step` vs `Collide.STEP`), the message correctly refuses the whole transaction,
but can misname which spelling is involved, which could confuse someone debugging why the
migration refused to run (this code path is described in the commit as "a planner bug" that should
never reach an owner, so the audience is a developer, not an end user, but the message is the only
diagnostic they get).

**Fix:** Report both colliding ops' `rel` values, e.g.:

```python
issues = [
    _err(
        "migration.duplicate_write",
        f"{write_paths[key].rel} and {duplicate_ops[key].rel} both write the same file; nothing was written",
    )
    for key in sorted(duplicate_ops)
]
```

## Info

### IN-01: No regression test exercises a model rename colliding with an untouched, unlinked model

**File:** `tests/test_migration_footprints.py`

**Issue:** The six CR-01 regression tests added in 13-21 (`test_colliding_model_names_queue_no_write`,
`test_colliding_model_names_are_case_insensitive`, `test_three_groups_one_name_keeps_the_sorted_first`,
`test_model_clash_line_is_plain_and_single`, `test_two_models_resolving_to_one_name_block_run`,
`test_added_model_cannot_take_an_existing_model_name`) all cover group-vs-group or
added-model-vs-existing collisions. None covers a rename-group's candidate colliding (especially
case-insensitively) with an on-disk model that is not itself part of any renamed group — the exact
gap CR-01 above describes. Adding that test would have caught CR-01 before this review.

**Fix:** Add a test alongside the existing six: seed an unlinked model file (so it shows up as a
"leftover" / untouched entry in `inventory.models` but is never added to `model_groups`), choose a
`model_name` for an unrelated part's single-model footprint that collides with it case-insensitively,
and assert no write op targets the shared casefolded path and an issue (ERROR or INFO,
whichever the fix from CR-01 settles on) is raised.

---

_Reviewed: 2026-11-12T10:15:40Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
