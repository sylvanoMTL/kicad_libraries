---
phase: 04-plan-and-install-core
reviewed: 2026-10-20T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - kicad_lib_manager/importer/applier.py
  - kicad_lib_manager/importer/candidate.py
  - kicad_lib_manager/importer/detect.py
  - kicad_lib_manager/importer/plan.py
  - kicad_lib_manager/importer/planner.py
  - tests/fakecli.py
  - tests/test_install_apply.py
  - tests/test_install_e2e.py
  - tests/test_install_plan.py
findings:
  critical: 0
  warning: 3
  info: 5
  total: 8
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-10-20
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

This is a re-review after gap-closure plans 04-11, 04-12 and 04-13 (`git diff a98636c..HEAD`). I read the current code and the new tests, ran `tests/test_install_apply.py`, `test_install_plan.py` and `test_install_e2e.py` (226 passed, 1 skipped, the opt-in UAT test), and probed the one suspected gap with a script.

### Re-verification of the five claimed fixes

| Previous finding | Verdict | Evidence |
|---|---|---|
| CR-01 exception safety | Fixed | `apply_plan` wraps `_transaction` in `try/except BaseException`. `_Transaction` keeps `undo`, `touched` and `backup_dir` outside the writing code, so the guard can roll back whatever was written. An `Exception` becomes `install.unexpected` plus `install.rolled_back`. `KeyboardInterrupt` and `SystemExit` are rolled back and re-raised. `_notify` isolates a raising progress callback. `_make_folders` now has `resolve()` inside its `try`. `_rollback` catches `Exception` per step and keeps going. `_rollback_once` stops a second rollback. I found no way for the guard to skip a rollback, and no double rollback. Tests cover a raise in a write, in verify, in the gate, in progress, in folder resolve and in a rollback step. |
| CR-02 TOCTOU | Fixed | Three layers: (1) after the gate, a re-check refuses a new-file path that appeared; (2) the backup copy is the authority, so its hash must equal `base_sha256` and the pre-image is taken from that copy; (3) `_still_fresh` runs immediately before every write, tracking the hash this install last wrote through `txn.expected`. A refused write adds no undo entry, so rollback never touches the other process's file. The window left is the single `os.replace` (the code states this). |
| WR-01 prune/UTC | Fixed | `prune_install_backups(..., exclude=backup_dir)` removes the running folder from the candidate list and counts it as one of the kept folders. The stamp uses `time.gmtime()`. The `-N` suffix ordering is unchanged. |
| WR-03 package issues | Fixed for the found-candidate path only | `detect_candidate` folds `package.issues` into `candidate.issues`, deduplicated and in order. `build_plan` copies `candidate.issues`, so a caller no longer forwards them. Two e2e tests prove this for a folder and for a zip. The no-candidate path is still open; see the new WR-06. |
| WR-05 blank text | Fixed | `InstallOptions.__post_init__` turns empty or whitespace-only `value`, `datasheet`, `description`, `manufacturer` and `mpn` into `None`. This also holds for `dataclasses.replace`. The UL probe test shows vendor values kept. Inconsistent edges are in IN-04. |

No Critical findings remain. One new Warning (WR-06) and two new Info items (IN-04, IN-05) are below. WR-02, WR-04 and IN-01 to IN-03 are carried forward from the previous review; I re-checked that each still applies.

## Warnings

### WR-02: Creating a library when Custom/Symbols is missing fails late with a bare "No such file or directory"

*(Carried forward from the previous review. Still applies: `planner.py` op assembly at about 1075 emits `mkdir` only for the `.pretty` folder and `models_dir`; `_make_folders` is called only for `mkdir` ops.)*

**File:** `kicad_lib_manager/importer/planner.py:1070-1080`; `kicad_lib_manager/importer/applier.py:434-457`
**Issue:** The planner emits `mkdir` ops for the `.pretty` folder and for `3DModels`, and `_make_folders` also creates a missing `Footprints` parent. There is no `mkdir` for `layout.symbols_dir`. With a fresh `Custom/` that has no `Symbols/` folder, the symbol write is the last op. The install writes the model and footprint, fails on `fs.write_failed`, and rolls everything back. Rollback is clean (verified), but the user sees "Could not write X.kicad_sym: No such file or directory" after all the work.

**Fix:** In `build_plan`, add `ops.append(FileOp("mkdir", layout.symbols_dir))` when `not layout.symbols_dir.is_dir()` and a new symbol library is planned. Alternatively, have `_write` call `_make_folders(plan, FileOp("mkdir", op.path.parent), undo)` before every file write.

### WR-04: build_plan is a 528-line function with about a dozen nested closures

*(Carried forward from the previous review. Still applies: `build_plan` now spans `planner.py:585-1116`, about 531 lines, with the same closures and the same symbol conflict loop.)*

**File:** `kicad_lib_manager/importer/planner.py:585-1113`
**Issue:** One function holds validation, name planning, version handling, model, footprint and symbol conflict logic, and op assembly. It uses closures over mutable locals (`renders`, `bad_actions`, `known_conflicts`, `rename_notes`, `model_dec`, `states`). The symbol conflict loop (lines 971-1022) has nesting beyond 4 levels. This makes the sequencing rules ("model first", "kept footprint drops the model", "judge symbol last") implicit and easy to break. `_edit_symbol` (71 lines) is also long. Several of these steps already have natural seams (`_decide_file` shows the pattern).

**Fix:** Extract `_plan_names`, `_plan_model`, `_plan_footprints`, `_plan_symbols` and `_assemble_ops`, each returning a small frozen result dataclass. Keep `build_plan` as the sequencer.

### WR-06: Package-level warnings are still lost when detection finds nothing (the WR-03 fix covers only the found-candidate path)

*(New; follow-up to WR-03 from the previous review.)*

**File:** `kicad_lib_manager/importer/detect.py:22-46` (see also the docstring at 18-21)
**Issue:** The fold of `package.issues` happens only when `candidate is not None`. The returned list is documented as "detection Issues only and excludes package.issues". When `locate` reports an ERROR (`intake.nothing_found`, which makes `locate` return `None`), neither the returned list nor any other object carries the package's own warnings. This is exactly the scenario WR-05 of Phase 3 described: a part skipped because its folder was too deep, or because a file was unreadable, looks like "nothing found".

Reproduced with a folder whose only `.kicad_sym` sits `MAX_FOLDER_DEPTH + 1` levels deep:
```
package issues [('intake.depth_limit', 'WARNING')]
candidate None returned [('intake.nothing_found', 'ERROR')]
```
The `intake.depth_limit` warning that explains the failure is visible only to a caller that separately reads `package.issues`. The new tests do not cover the no-candidate path.

**Fix:** Return the package issues with the no-candidate result, deduplicated:
```python
candidate, issues = locate(package, best)
...
if candidate is not None:
    candidate = replace(candidate, issues=tuple(dict.fromkeys((*package.issues, *candidate.issues))))
else:
    issues = list(dict.fromkeys((*package.issues, *issues)))
```
Update the docstring to say the list holds detection Issues, plus the package's Issues when no candidate is returned. Add a test using the probe above that asserts `intake.depth_limit` is in the returned list.

## Info

### IN-01: A no-op plan reports "Everything is already installed" without re-checking the disk

*(Carried forward from the previous review. Still applies: `applier.py:326-327` is unchanged.)*

**File:** `kicad_lib_manager/importer/applier.py:326-327`
**Issue:** `is_noop` is computed at plan time. If a footprint, model or symbol was deleted between plan and apply, `apply_plan` still returns `ok=True, "Everything is already installed"` and never runs `verify_install`. Nothing is written, so no data is at risk, but the claim can be false.
**Fix:** Run `verify.verify_install(plan)` on the no-op path and return its errors.

### IN-02: Small duplication in the install modules

*(Carried forward from the previous review. Still applies: `_err` is defined in `planner.py:71`, `verify.py:30` and `applier.py:23`; `_listing` in `planner.py:223` and `verify.py:34`; the literal `5` remains in `planner.step` at line 611.)*

**File:** `kicad_lib_manager/importer/planner.py:71-72, 223-228`; `kicad_lib_manager/importer/verify.py:30-38`; `kicad_lib_manager/importer/applier.py:23-24`
**Issue:** `_err` is defined three times, and `_listing` twice with different return types (`list[str]` versus `set[str]`). The progress total `5` is a magic number in `planner.step`.
**Fix:** Share `_err` through a small helper (for example `Issue.error(code, text)` in `models.py`) and one `_listing` helper. Name the step count.

### IN-03: The opt-in UAT test deletes whatever `<KICAD_IMPORT_UAT_DIR>/Custom` holds

*(Carried forward from the previous review. Still applies: `tests/test_install_e2e.py:581-594`, now at lines 584-594; the guard is unchanged.)*

**File:** `tests/test_install_e2e.py:581-594`
**Issue:** The guard only rejects folders inside or containing this checkout. A `KICAD_IMPORT_UAT_DIR` that points at another clone, or a home folder holding an unrelated `Custom/`, has that folder removed with `shutil.rmtree`.
**Fix:** Refuse unless `scratch` is absent or contains a marker file the test itself wrote, or create a fresh `tempfile.mkdtemp` sub-folder under the given directory.

### IN-04: The blank-means-not-set rule covers five fields only; other Qt-sourced options still misbehave on "" and non-blank values keep stray spaces

*(New; follow-up to WR-05.)*

**File:** `kicad_lib_manager/importer/plan.py:38-69`; `kicad_lib_manager/importer/planner.py:514-546, 700-703`
**Issue:** Three edges remain after the WR-05 fix:
- `footprint_names={"FP": ""}` (an untouched Qt line edit) is not treated as unset. `wanted is None` is false, `sanitize_name("")` reports `naming.empty`, and the plan is refused with "has no usable characters; enter another name". The result is a refusal rather than silent data loss, but it is the same form-field problem WR-05 fixed for the text overrides.
- `model=""` fails with "The package has no 3D model named ''", and `symbol=""` fails the same way.
- Non-blank values are not stripped. `mpn=" CSD85301Q2 "` is stored with its spaces in the `MPN` property (`test_blank_options_mean_not_set` asserts this on purpose). The model file name is sanitised, but the property is not.
**Fix:** In `__post_init__`, also strip the five text overrides (`object.__setattr__(self, name, text.strip())`), turn `symbol` and `model` of `""` into `None`, and drop blank-string entries from `footprint_names`. Update the test that pins the unstripped `mpn`.

### IN-05: Early aborts after the backup folder exists leave it behind unreported and unpruned

*(New.)*

**File:** `kicad_lib_manager/importer/applier.py:378-395`
**Issue:** The backup folder is created by the first `fsutil.backup_file` call. If a later step in that loop returns early (a failed backup of another file, an unreadable backup copy, or a stale-plan hash mismatch), the function returns before `prune_install_backups` runs. The folder stays, and the `fs.backup_failed`/`[saved]` return at line 383 omits `backup_dir=` while the other two early returns include it. Repeated stale-plan retries add folders that are pruned only at the next successful install. No data is at risk.
**Fix:** Pass `backup_dir=backup_dir` on the `saved` failure return too, and run the prune (or delete the just-created folder) on these early-exit paths.

---

_Reviewed: 2026-10-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
