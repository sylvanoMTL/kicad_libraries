---
phase: 13-atomic-migration-and-kicad-setup
reviewed: 2026-11-12T00:00:00Z
depth: standard
files_reviewed: 61
files_reviewed_list:
  - CLAUDE.md
  - kicad_lib_manager/gitops.py
  - kicad_lib_manager/importer/commit_gate.py
  - kicad_lib_manager/importer/commit_plan.py
  - kicad_lib_manager/importer/commit_step.py
  - kicad_lib_manager/importer/form.py
  - kicad_lib_manager/importer/migration/__init__.py
  - kicad_lib_manager/importer/migration/applier.py
  - kicad_lib_manager/importer/migration/commitplan.py
  - kicad_lib_manager/importer/migration/draft.py
  - kicad_lib_manager/importer/migration/families.py
  - kicad_lib_manager/importer/migration/footprints.py
  - kicad_lib_manager/importer/migration/gate.py
  - kicad_lib_manager/importer/migration/inventory.py
  - kicad_lib_manager/importer/migration/mapfile.py
  - kicad_lib_manager/importer/migration/plan.py
  - kicad_lib_manager/importer/migration/planner.py
  - kicad_lib_manager/importer/migration/precheck.py
  - kicad_lib_manager/importer/migration/symbols.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/kicad_setup.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/settings.py
  - kicad_lib_manager/table_generator.py
  - kicad_lib_manager/widgets/commit_panel.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - kicad_lib_manager/widgets/import_result.py
  - kicad_lib_manager/widgets/migration_dialog.py
  - tests/migrationfixtures.py
  - tests/README.md
  - tests/test_checkout_check.py
  - tests/test_checkout_warning.py
  - tests/test_commit_deletions.py
  - tests/test_commit_panel.py
  - tests/test_commit_plan.py
  - tests/test_docs_atomic.py
  - tests/test_gitops.py
  - tests/test_help_dialog.py
  - tests/test_importer_layering.py
  - tests/test_kicad_setup.py
  - tests/test_layering.py
  - tests/test_main_window.py
  - tests/test_main_window_chooser.py
  - tests/test_main_window_import.py
  - tests/test_main_window_migration.py
  - tests/test_migration_apply.py
  - tests/test_migration_commit.py
  - tests/test_migration_dialog.py
  - tests/test_migration_dialog_files.py
  - tests/test_migration_dialog_run.py
  - tests/test_migration_draft.py
  - tests/test_migration_e2e.py
  - tests/test_migration_families.py
  - tests/test_migration_footprints.py
  - tests/test_migration_full.py
  - tests/test_migration_gate.py
  - tests/test_migration_inventory.py
  - tests/test_migration_map.py
  - tests/test_migration_precheck.py
  - tests/test_migration_symbols.py
  - tests/test_table_add_entries.py
  - tests/test_table_descriptions.py
  - tests/test_table_merge.py
findings:
  critical: 1
  warning: 2
  info: 1
  total: 4
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-11-12
**Depth:** standard
**Files Reviewed:** 61 (test files scoped per file-list; reviewed for reliability impact only, not style)
**Status:** issues_found

## Summary

Reviewed the Phase 13 Atomic-migration package (`importer/migration/*`), the chooser-setup service
(`kicad_setup.py`), the migration window (`widgets/migration_dialog.py`), the shared commit panel/step
code it reuses, and the main-window wiring that launches and gates the migration. The git layer
(`gitops.py`, `commit_gate.py`, `commit_step.py`, `commit_plan.py`) and the migration's transactional
applier (`applier.py`, `precheck.py`) are carefully defended: argv-only subprocess calls, a fixed
subcommand allow-list, path-containment and symlink checks before any write, re-verified freshness
checks right before each op, and ordered rollback on any failure.

One genuine data-loss defect was found in the 3D-model-rename pass of the footprint planner
(`importer/migration/footprints.py`): unlike the footprint-rename path (which tracks every name it has
already claimed in this same run), the model-rename path only checks a model's new name against the
*original, pre-migration* inventory of model file names. Two unrelated models that both resolve to the
same final name within one migration run collide silently — one is physically overwritten by the
other's bytes, both original files are then deleted, and neither the preflight checks nor the
post-write verification step in `applier.py` are able to notice the collision because they key off
`op.path`/`op.rel`, which both operations share. The migration reports success.

Two further issues are reported as warnings (an unresolved annotation reference and a minor UI gap),
plus one informational note.

## Critical Issues

### CR-01: Two footprints' 3D models can be renamed to the same file, silently destroying one of them

**File:** `kicad_lib_manager/importer/migration/footprints.py:314, 376-402, 404-416`
**File (applier does not catch it):** `kicad_lib_manager/importer/migration/applier.py:225, 335-360, 413-434`

**Issue:**

`plan_footprints` renames a footprint's single 3D model to the winning linking part's MPN (or an
owner-typed `model_name` override), one old-model-name group at a time:

```python
model_name_set = frozenset(inventory.models)   # <- fixed snapshot, never updated below
...
model_final_name: dict[str, str] = {}
for old_name, group in model_groups.items():
    winner_key, winner_fp = min(group, key=lambda item: item[0])
    choice = choices.parts.get(winner_key, PartChoice())
    mpn = mpns.get(winner_key, "")
    stem = choice.model_name if choice.model_name else (mpn or None)
    ...
    candidate = sanitize_filename(f"{stem}{ext}").sanitized
    ...
    if candidate in model_name_set and candidate != old_name:
        # kept, name already used by a DIFFERENT (pre-existing) model
        model_final_name[old_name] = old_name
        continue
    model_final_name[old_name] = candidate   # <- never added to model_name_set
```

`model_name_set` is a snapshot of the *original* inventory names taken once, before the loop, and it
is never updated as the loop assigns `candidate` names to successive `old_name` groups. Two different
`old_name` groups (two different footprints' models, e.g. two unrelated parts) can therefore both be
assigned the *same* `candidate` — this happens whenever two parts end up with the same resolved MPN
(an owner-typed `choice.mpn` is **not** deduplicated the way the default MPN is in `part_mpns`, so a
owner who types the same MPN for two different parts, or the same `model_name` override for two
different parts, triggers this directly).

When that happens, two `MigrationOp("write", new_path, ...)` entries are queued for the *same*
`new_path`, each carrying a different model's bytes, immediately followed by two independent
`MigrationOp("delete", old_path, ...)` entries for the two original files (lines 404-416):

```python
for old_name, new_name in model_final_name.items():
    if new_name == old_name:
        continue
    ...
    ops.append(MigrationOp("write", new_path, new_rel, data=data, base_sha256=base_sha256, source_rel=old_rel))
    ops.append(MigrationOp("delete", old_path, old_rel, base_sha256=hashlib.sha256(data).hexdigest()))
```

Contrast this with the footprint-name clash path (`_resolve_clash`, lines 171-242 of the same file),
which *does* track every name claimed so far in `shared_known`/`shared_taken_stems` and raises a
`Conflict` the owner must resolve before Run is enabled. The model-rename path has no equivalent
cross-check against its own decisions, only against the pre-migration snapshot.

`applier.apply_migration` cannot catch this either:
- `_preflight` (applier.py:202-256) only builds `writes = {str(op.path).casefold(): op for op in plan.ops if op.kind == "write"}` (line 225) to compare writes against *deletes* for the "case twin" check; a dict comprehension silently keeps only the *last* op for a duplicated key, so a write-vs-write collision is invisible to it.
- `_still_fresh` (lines 335-360) is the per-op freshness re-check run immediately before each op executes. For the *second* colliding write it sees `expected[key]` already populated by the *first* write (which just ran a moment earlier in the same transaction) and the hash matches exactly what is on disk — because the first write just put it there. The check passes, and the second write proceeds to overwrite the first model's content.
- `_verify` (lines 413-434) builds `by_rel = {op.rel: op for op in plan.ops}` (line 415); again the dict collapses the two ops with the same `rel` down to one (the *last* one in `plan.ops`), so the verify step checks the on-disk bytes against the *last* op's `data` twice and never notices the first model's content is gone.

End state: one 3D model's geometry is permanently lost (its original file deleted, and the file it was
renamed to now holds a different model's bytes), with **no Issue, no Conflict row, and no refusal** —
`result.ok` is `True` and the strip reports success.

**Fix:** Track every candidate name claimed so far across *all* `old_name` groups (seed a mutable set
from `model_name_set`, add each `candidate` to it as soon as it is chosen, and check membership in that
growing set — the same pattern `_resolve_clash` already uses for footprints) and raise the same kind of
`Conflict`/blocking `Issue` the footprint path raises when two groups would resolve to the same name,
instead of silently letting both proceed:

```python
model_final_name: dict[str, str] = {}
claimed_model_names: set[str] = set(model_name_set)  # grows as decisions are made
for old_name, group in sorted(model_groups.items()):
    ...
    if candidate.casefold() in {n.casefold() for n in claimed_model_names} and candidate != old_name:
        issues.append(Issue(Severity.INFO, "migration.model_kept_name", ...))
        model_final_name[old_name] = old_name
        claimed_model_names.add(old_name)
        continue
    model_final_name[old_name] = candidate
    claimed_model_names.add(candidate)
```

## Warnings

### WR-01: `CommitPlan`/`CommitProbe` type annotations in `migration_dialog.py` are unresolved names

**File:** `kicad_lib_manager/widgets/migration_dialog.py:322-323, 338, 373`

**Issue:** `_CommitStepHost` annotates its state with `CommitPlan` and `CommitProbe`:

```python
self._plan: CommitPlan | None = None       # line 322
self._probe: CommitProbe | None = None     # line 323
def start(self, plan: CommitPlan): ...     # line 338
def _on_probe_done(self, worker: TaskWorker, probe: CommitProbe): ...  # line 373
```

Neither `CommitPlan` nor `CommitProbe` is imported anywhere in this module (the module imports only
functions from `..importer.commit_step`, not these dataclasses). This does not crash at runtime, because
CPython does not evaluate annotation expressions that target an attribute inside a function body (verified:
`self.x: Undefined = None` inside `__init__` raises no error) — but it means `mypy`/`pyright` cannot
resolve these annotations, and a reader has no way to discover where `CommitPlan`/`CommitProbe` come from
without searching other files. `commit_panel.py`, which needs the exact same two types, imports them
correctly (`from ..importer.commit_plan import CommitPlan`, `from ..importer.commit_step import CommitProbe`).

**Fix:**
```python
from ..importer.commit_plan import CommitPlan
from ..importer.commit_step import CommitProbe
```

### WR-02: `CommitPanel._mark_files` never marks a deleted commit row as "also changed before this import"

**File:** `kicad_lib_manager/widgets/commit_panel.py:591-597`

**Issue:** For a deleted `CommitFile` row, `_mark_files` returns immediately after adding the row to
`_activatable`, before the `dirty = rel in probe.dirty_before` check runs lower in the same loop:

```python
if cfile is not None and cfile.deleted:
    if rel is not None:
        self._activatable.add(rel)
    continue
```

`commit_step._dirty_before` does not exclude `deleted` files from its scan (it only skips a file whose
`base_sha256 is None`), so `probe.dirty_before` can in principle contain the rel of a deleted file. If it
did, the amber "also changed before this import" marker and tooltip would never show for that row, and
the `_DIRTY_MARK`/`_dirty_hint` the UI otherwise promises for exactly this situation would silently not
appear. In the current call path this is unreachable in practice (the migration's own precheck refuses to
start while Custom has any uncommitted change, so a deleted file's pre-image always equals HEAD by the
time the commit step runs) — but the code does not rely on or document that invariant, so a future caller
of `CommitPanel` with a looser precondition would hit this gap silently.

**Fix:** Compute `dirty` before the `cfile.deleted` early return (or move the deleted-row return after
the general marking block) so a deleted-and-dirty file still gets the existing dirty styling/tooltip.

## Info

### IN-01: Unused parameter `result` in `MainWindow._on_migrated`

**File:** `kicad_lib_manager/main_window.py:1276`

**Issue:**
```python
def _on_migrated(self, result):
    """A migration committed: rescan quietly, then select the new Atomic_ libraries (D-24)."""
    self._pending_migration = True
    self._migration_scan_started = False
    if self._worker is None:
        self._start_scan(show_progress=False)
```
`result` (the `MigrationResult`) is taken but never read. Harmless (the method only needs the
notification that a migration committed), but worth either using `_` or dropping the parameter name
conventionally if the signal's payload is ever reduced, to avoid an unused-argument smell.

**Fix:** Rename to `_result` or note in a comment that the slot intentionally ignores the payload.

---

_Reviewed: 2026-11-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
