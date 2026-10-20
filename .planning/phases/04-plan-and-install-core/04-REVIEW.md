---
phase: 04-plan-and-install-core
reviewed: 2026-10-20T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - kicad_lib_manager/importer/applier.py
  - kicad_lib_manager/importer/kicad_cli.py
  - kicad_lib_manager/importer/plan.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/verify.py
  - kicad_lib_manager/kicad_files.py
  - pyproject.toml
  - tests/conftest.py
  - tests/fakecli.py
  - tests/installfixtures.py
  - tests/test_importer_layering.py
  - tests/test_install_apply.py
  - tests/test_install_e2e.py
  - tests/test_install_plan.py
  - tests/test_install_verify.py
  - tests/test_installfixtures.py
  - tests/test_kicad_cli.py
  - tests/test_kicad_files_write.py
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-10-20
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

The planner, the byte-exact splice helpers in `kicad_files.py`, the verifier and the kicad-cli wrapper are in good shape. Edits are span-based and non-overlapping, the stale-plan hash check exists, containment is checked with `resolve()`, and case handling uses exact-case listings. I traced the splice paths (overwrite plus insert-before on the same symbol, zero-width inserts at one position, BOM and EOL round trip) and found no corruption.

The weaknesses are in the transaction wrapper. `apply_plan` guarantees "every change is undone on failure", but that holds only for failures that arrive as `Issue` values. Two defects were reproduced with probe scripts against the real code:

- An exception thrown mid-install leaves a half-installed tree with no rollback.
- A file changed by another process while the kicad-cli gate runs is silently overwritten, and the install reports success.

Carried findings from Phase 3: WR-04 (candidate outliving its staged files) is handled in practice. `_read_vendor` re-hashes the staged file at plan time and the apply preflight re-hashes the model source. WR-05 (package-level warnings) is only half handled; see WR-03 below.

## Critical Issues

### CR-01: apply_plan has no exception safety, so an unexpected exception leaves a partial install and no rollback

**File:** `kicad_lib_manager/importer/applier.py:291-312` (also `323-340`)
**Issue:** Rollback runs only when a write returns an `Issue` (`failures` non-empty). The write loop, the `progress(...)` callback, `_make_folders` and `verify.verify_install` are not wrapped in any `try`. Anything raised there escapes `apply_plan` after files have already been written, and `_rollback` is never called.

Concrete triggers:
- The GUI `progress` callback raises. It is called before every op.
- `folder.resolve()` in `_make_folders` raises `OSError`. It sits outside the `try` that only covers `mkdir`.
- `KeyboardInterrupt` or `MemoryError` during `verify_install`.
- Any bug-class exception in verify.

Reproduced: a hand plan with a progress callback that raises at op index 2 leaves `Custom/3DModels/X.stp` and the empty new `.pretty` folder on disk, and the exception propagates. This breaks the project's "report issues, don't raise" convention and the D-18 transaction promise (INST-07).

**Fix:**
```python
undo: list[_Undo] = []
touched: list[Path] = []
failures: list[Issue] = []
warnings: list[Issue] = []
try:
    for index, op in enumerate(plan.ops):
        if progress is not None:
            progress(f"Writing {op.path.name}", index, total)
        problem = _write(plan, op, sources.get(index), undo, touched, pre_images.get(index))
        if problem is not None:
            failures.append(problem)
            break
    if not failures:
        checked = verify.verify_install(plan)
        failures.extend(i for i in checked if i.severity is Severity.ERROR)
        warnings = [i for i in checked if i.severity is not Severity.ERROR]
except BaseException as e:  # roll back, then let KeyboardInterrupt and SystemExit continue
    leftovers = _rollback(undo, backup_dir)
    if not isinstance(e, Exception):
        raise
    failures.append(_err("install.unexpected", f"The install stopped unexpectedly ({type(e).__name__}: {e})"))
```
Also guard the `progress` call separately, so a UI callback error cannot abort a transaction. Add a regression test with a raising `progress` and a monkeypatched `verify.verify_install` that raises.

### CR-02: A file changed between the stale-plan hash check and the write is silently overwritten, and the install reports success (TOCTOU)

**File:** `kicad_lib_manager/importer/applier.py:194-239, 264-284, 294`
**Issue:** `_preflight` hashes each existing target and stores its bytes as the pre-image. Then `_gate` runs up to three kicad-cli processes, each with a 60 s timeout. Only after that does the backup copy and the first write happen. Nothing re-checks the hash after the gate. The planned symbol library bytes were spliced onto the preflight-time base. If KiCad (or a git operation, or the user) saves the library during that window, the splice discards the other change.

Reproduced: a fake runner that appends an edit to the target `.kicad_sym` while the gate runs makes `apply_plan` return `ok=True` with only `install.done`. The live file no longer contains the edit; it survives only in the backup folder, which the result never mentions. Rollback would also restore the stale preflight pre-image rather than what the backup holds.

**Fix:** Make the backup the authority, and compare it with the hash the plan was built from before writing anything:
```python
for op in plan.ops:
    if op.base_sha256 is None:
        continue
    saved = fsutil.backup_file(op.listed_path or op.path, backup_dir)
    if isinstance(saved, Issue):
        return _result(plan, False, [saved])
    if hashlib.sha256(saved.read_bytes()).hexdigest() != op.base_sha256:
        return _result(plan, False, [_err("install.stale_plan", f"{op.path.name} changed on disk while the install was being checked; rebuild the plan")], backup_dir=backup_dir)
    pre_images[index] = saved.read_bytes()   # roll back to what was really backed up
```
Optionally re-hash the symbol library again immediately before its atomic write (it is the last op).

## Warnings

### WR-01: prune_install_backups can delete the backup folder that was just created

**File:** `kicad_lib_manager/importer/applier.py:129-141, 284`
**Issue:** The folder stamp comes from local-time `time.strftime`, and pruning keeps the "newest 10" by that string. If the clock steps back (DST fall-back hour, manual clock change) and 10 or more folders already sort later, the new folder ranks as the oldest. It is deleted by `prune_install_backups` before the first write.

Reproduced: with 10 existing later-stamped folders, `apply_plan` returned `ok=True` with `backup_dir` pointing at a folder that no longer exists. On a later rollback failure the message "the original is in {backup_dir}" would point at nothing.

**Fix:** Never prune the folder just made. Pass `exclude=backup_dir` to `prune_install_backups` and skip it in the delete loop. Prefer `time.gmtime()` for the stamp.

### WR-02: Creating a library when Custom/Symbols is missing fails late with a bare "No such file or directory"

**File:** `kicad_lib_manager/importer/planner.py:1070-1080`; `kicad_lib_manager/importer/applier.py:323-340`
**Issue:** The planner emits `mkdir` ops for the `.pretty` folder and for `3DModels`, and `_make_folders` also creates a missing `Footprints` parent. There is no `mkdir` for `layout.symbols_dir`. With a fresh `Custom/` that has no `Symbols/` folder, the symbol write is the last op. The install writes the model and footprint, fails on `fs.write_failed`, and rolls everything back. Rollback is clean (verified), but the user sees "Could not write X.kicad_sym: No such file or directory" after all the work.

**Fix:** In `build_plan`, add `ops.append(FileOp("mkdir", layout.symbols_dir))` when `not layout.symbols_dir.is_dir()` and a new symbol library is planned. Alternatively, have `_write` call `_make_folders(plan, FileOp("mkdir", op.path.parent), undo)` before every file write.

### WR-03: WR-05 (package-level warnings) is only half handled

**File:** `kicad_lib_manager/importer/planner.py:591, 600-601`; `kicad_lib_manager/importer/candidate.py:64-76`
**Issue:** `build_plan` gained an optional `package_issues=()` keyword. `ImportCandidate.issues` still does not carry the package-level issues (skipped deep folders, unreadable members), and `detect_candidate` returns them separately as its second tuple element. Any caller that does not remember to forward `package.issues` plus that second element silently reproduces the Phase 3 defect: a skipped part looks like "nothing found". The only coverage is one unit test (`test_install_plan.py:248`) that passes hand-made issues. None of the e2e tests install from a package that has package-level warnings and assert they appear in `InstallResult.issues`.

**Fix:** Make the data path structural. Either fold the package issues into `ImportCandidate.issues` inside `detect_candidate` (`replace(candidate, issues=(*issues, *candidate.issues))`, de-duplicated), or make `package_issues` a required keyword so a caller has to pass something. Add an e2e test with a zip that triggers an `intake.skipped_deep` warning and assert it reaches `InstallResult.issues`.

### WR-04: build_plan is a 528-line function with about a dozen nested closures

**File:** `kicad_lib_manager/importer/planner.py:585-1113`
**Issue:** One function holds validation, name planning, version handling, model, footprint and symbol conflict logic, and op assembly. It uses closures over mutable locals (`renders`, `bad_actions`, `known_conflicts`, `rename_notes`, `model_dec`, `states`). The symbol conflict loop (lines 971-1022) has nesting beyond 4 levels. This makes the sequencing rules ("model first", "kept footprint drops the model", "judge symbol last") implicit and easy to break. `_edit_symbol` (71 lines) is also long. Several of these steps already have natural seams (`_decide_file` shows the pattern).

**Fix:** Extract `_plan_names`, `_plan_model`, `_plan_footprints`, `_plan_symbols` and `_assemble_ops`, each returning a small frozen result dataclass. Keep `build_plan` as the sequencer.

### WR-05: An empty string in InstallOptions blanks the vendor value instead of meaning "not set"

**File:** `kicad_lib_manager/importer/planner.py:120-123, 183-193, 748-760`
**Issue:** Overrides are tested with `is not None`. `InstallOptions(mpn="", value="", datasheet="")` writes empty `MPN`, `Value` and `Datasheet` properties, destroying the vendor data. The probe on the Ultra Librarian sample gave `Value ""`, `Datasheet ""` and `MPN ""` instead of `CSD85301Q2` and the real datasheet URL. A Qt line edit returns `""`, not `None`, for an untouched field, so the Phase 5 form will hit this. With `mpn=""` the model file name also silently falls back to the symbol name.

**Fix:** Normalise in one place, for example `__post_init__` on `InstallOptions` turning empty or whitespace-only strings to `None`, or compare `if options.mpn:` etc. in `build_plan`. If an explicit "clear this field" is needed, give it its own sentinel.

## Info

### IN-01: A no-op plan reports "Everything is already installed" without re-checking the disk

**File:** `kicad_lib_manager/importer/applier.py:256-257`
**Issue:** `is_noop` is computed at plan time. If a footprint, model or symbol was deleted between plan and apply, `apply_plan` still returns `ok=True, "Everything is already installed"` and never runs `verify_install`. Nothing is written, so no data is at risk, but the claim can be false.
**Fix:** Run `verify.verify_install(plan)` on the no-op path and return its errors.

### IN-02: Small duplication in the install modules

**File:** `kicad_lib_manager/importer/planner.py:71-72, 223-228`; `kicad_lib_manager/importer/verify.py:30-38`; `kicad_lib_manager/importer/applier.py:22-23`
**Issue:** `_err` is defined three times, and `_listing` twice with different return types (`list[str]` versus `set[str]`). The progress total `5` is a magic number in `planner.step`.
**Fix:** Share `_err` through a small helper (for example `Issue.error(code, text)` in `models.py`) and one `_listing` helper. Name the step count.

### IN-03: The opt-in UAT test deletes whatever `<KICAD_IMPORT_UAT_DIR>/Custom` holds

**File:** `tests/test_install_e2e.py:551-566`
**Issue:** The guard only rejects folders inside or containing this checkout. A `KICAD_IMPORT_UAT_DIR` that points at another clone, or a home folder holding an unrelated `Custom/`, has that folder removed with `shutil.rmtree`.
**Fix:** Refuse unless `scratch` is absent or contains a marker file the test itself wrote, or create a fresh `tempfile.mkdtemp` sub-folder under the given directory.

---

_Reviewed: 2026-10-20_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
