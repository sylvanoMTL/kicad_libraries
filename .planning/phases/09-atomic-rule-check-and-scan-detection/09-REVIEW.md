---
phase: 09-atomic-rule-check-and-scan-detection
reviewed: 2026-10-26T14:40:00Z
depth: standard
files_reviewed: 29
files_reviewed_list:
  - kicad_lib_manager/atomic_check.py
  - kicad_lib_manager/atomic_fixes.py
  - kicad_lib_manager/changes.py
  - kicad_lib_manager/importer/suggest.py
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/manufacturers.py
  - kicad_lib_manager/models.py
  - kicad_lib_manager/sexpr.py
  - kicad_lib_manager/widgets/atomic_check_dialog.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/library_table.py
  - tests/README.md
  - tests/customfixtures.py
  - tests/test_atomic_check.py
  - tests/test_atomic_dialog.py
  - tests/test_atomic_fixes.py
  - tests/test_atomic_scan.py
  - tests/test_atomic_uat.py
  - tests/test_help_dialog.py
  - tests/test_importer_layering.py
  - tests/test_layering.py
  - tests/test_library_table_atomic.py
  - tests/test_main_window.py
  - tests/test_manufacturers.py
  - tests/test_models.py
  - tests/test_scan_changes.py
  - tests/test_scanner_issues.py
  - tests/test_sexpr.py
findings:
  critical: 0
  warning: 4
  info: 8
  total: 12
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-10-26T14:40:00Z
**Depth:** standard
**Files Reviewed:** 29
**Status:** issues_found

## Summary

The phase adds the atomic rule check, the fix engine, change detection against Custom's HEAD, the manufacturer table and the check dialog. The core logic is sound. I ran an end-to-end pass on the synthetic atomic inventory: scan, build a preview of every safe fix, apply it, rescan. No fixable violation remained and a second preview was empty. Path containment (`_inside`), the SHA-256 stale check, backup-before-write and rollback all read correctly. Vendor text reaches the log, tooltips and labels escaped or as plain text, so I found no markup injection.

The defects found are all in edges the 2350 tests do not reach, and I reproduced each one by script:

- A single `&` in a button label swallows the character and registers an `Alt+Space` shortcut (confirmed).
- A footprint with a NUL character in a 3D model path aborts the whole scan.
- The model-attach fix mishandles two or more symbols that share one footprint. In one case it writes a footprint that links a model file the preview never copies.

No BLOCKER was found. The NUL crash and the dangling model link are the two I would fix first.

Orchestrator notes:
- atomic_check_dialog.py:286: confirmed, see WR-01.
- Carve-back scaffolding in atomic_fixes.py: I found no dead code in that file. Every private helper and constant is used. The leftovers are duplicates (IN-01, IN-02), not unreachable code.

## Warnings

### WR-01: "Preview & apply" button text loses the ampersand and registers Alt+Space

**File:** `kicad_lib_manager/widgets/atomic_check_dialog.py:286`
**Issue:** Qt reads a single `&` in button text as a mnemonic marker. I measured it with PySide6 6.12 offscreen:

| Button text | `sizeHint` width | Mnemonic |
| --- | --- | --- |
| `"Preview & apply 2 fixes"` | 278 | `Alt+Space` |
| `"Preview && apply 2 fixes"` | 290 | none |

So the ampersand does not render (the label reads "Preview  apply"), and the button gets an `Alt+Space` shortcut. On Windows `Alt+Space` is the window system-menu key, so the button can steal it or fire an unintended preview. This is the only such string in `widgets/`.
**Fix:**
```python
self._preview_btn.setText(f"Preview and apply {_plural(count, 'fix', 'fixes')}")
```
Or escape it as `&&`. Update any test that asserts the old text.

### WR-02: A NUL character in a footprint's 3D model path aborts the whole scan

**File:** `kicad_lib_manager/atomic_check.py:362-371` (`_listing`), reached from `:459-461` (`model_path_problem`); no isolation at `:633-644` (`check_libraries`)
**Issue:** `_listing` catches only `OSError`. `os.listdir` raises `ValueError: embedded null character in path` for a NUL. The sexpr parser and UTF-8 decoding accept NUL, so a footprint with a model path such as `"C:/foo\0/bar.step"` reaches `os.listdir(Path(path).parent)`. I reproduced it: `ctx.model_problems(target)` raises `ValueError`. Nothing above it catches the error, so `ScanWorker` reports "Scan error" and every later scan fails until the file is fixed. This contradicts the `check_libraries` docstring ("A library that cannot be read gets check_problem and the scan goes on").

`check_libraries` has no per-library exception boundary, so any other unexpected exception from a rule fails the scan the same way.
**Fix:**
```python
# _listing
except (OSError, ValueError):
    names = frozenset()

# model_path_problem, before any filesystem use of an absolute path
if "\x00" in path:
    return f'3D model path "{path!r}" is not valid'
```
In `check_libraries`, wrap each library's checking in `try/except Exception as e` and set `lib.check_problem` plus an `atomic.unreadable` issue, as the unreadable-file path already does.

### WR-03: Two symbols sharing one footprint can attach two different models to it

**File:** `kicad_lib_manager/atomic_fixes.py:466-492` (`_footprint_file`)
**Issue:** Each symbol that uses a footprint without a model gets its own `attach_model` spec, so a footprint shared by two symbols (the normal case in `Atomic_Footprints`) gets two specs. Each loop iteration reads `refs` from the unmodified footprint node, so both see "no model" and both add an insert edit. If the user picks different files for the two symbols, the preview adds two `(model ...)` blocks to the one footprint with no error. I reproduced it:

```
(model "${CUSTOM_3DMODEL_DIR}/a.step" ...)
(model "${CUSTOM_3DMODEL_DIR}/b.step" ...)
```

The same situation with a broken existing model path correctly fails with "two of the ticked fixes change the same field", so behaviour differs between the two cases. With the same file picked twice it works only because `set(edits)` drops the identical edit.
**Fix:** Make one footprint accept one model per batch. After the first successful pick for a footprint, skip the others with a `notes.skip` line (or raise `atomic.fix_conflict`):
```python
if edits and broken is None:   # an insert is already queued for this footprint
    notes.skip(spec, "another ticked fix already adds a 3D model to this footprint")
    continue
```
The same dedup should drop the second spec's copy `FileChange` too.

### WR-04: A refused group leaves its model copies registered, so a later footprint links a file that is never copied

**File:** `kicad_lib_manager/atomic_fixes.py:498-512` (`_footprint_file`, the `models` registry)
**Issue:** `models[key] = change` is set inside the loop. If a later spec in the same group hits the "different 3D model named ..." conflict, the function does `return []` and discards `out`. The earlier entries stay in `models`. A later footprint that picks the same file (same bytes) then finds `seen is not None`, only extends `seen.specs`, and emits no copy. Its footprint edit still links `${CUSTOM_3DMODEL_DIR}/<file>`. I reproduced it with three footprints: F2's group is refused after registering `m1.step`, and F3 ends up as a changed footprint linking `m1.step` while the preview holds no `m1.step` copy. Apply stays enabled (the preview has changes), and it writes a footprint with a dangling model link, the same fault the rule exists to catch.
**Fix:** Register models only after the whole group succeeds:
```python
staged: list[FileChange] = []
for change in pending:
    key = change.rel_path.casefold()
    seen = models.get(key) or next((s for s in staged if s.rel_path.casefold() == key), None)
    ...
    # on conflict: return [] without touching `models`
# after the loop, once nothing conflicted:
for change in staged:
    models[change.rel_path.casefold()] = change
```

## Info

### IN-01: `check_symbol` and parts of `FootprintTarget` are used only by tests

**File:** `kicad_lib_manager/atomic_check.py:564` and `:336-348`
**Issue:** `check_symbol` has no production caller. `check_libraries` repeats its loop with a shared index, so `tests/test_atomic_check.py` (which calls `check_symbol`) does not exercise the path production uses. `FootprintTarget.text`, `.library` and `.footprint` are written and never read.
**Fix:** Have `check_libraries` call a shared helper that `check_symbol` also uses, or point the tests at `check_libraries`. Drop the unused fields or add a reader.

### IN-02: The Custom model listing and the model prefix are defined three times

**File:** `kicad_lib_manager/atomic_check.py:412-422`, `kicad_lib_manager/atomic_fixes.py:368-373`, `kicad_lib_manager/library_scanner.py:472-479` and `:24`
**Issue:** Three copies of "exact relative names under Custom/3DModels". Two catch `OSError`. The `library_scanner` copy does not, so an unreadable subfolder fails the scan there. `CUSTOM_MODEL_PREFIX` is defined in `atomic_check.py:30` (its comment says plan 09-06 reuses it) and again in `library_scanner.py:24`, although `library_scanner` already imports from `atomic_check`.
**Fix:** Keep one `custom_model_names(repo_root)` helper (it can live in `atomic_check`) and import `CUSTOM_MODEL_PREFIX` in `library_scanner`.

### IN-03: Foundation modules import size caps from the importer package

**File:** `kicad_lib_manager/changes.py:13`, `kicad_lib_manager/atomic_check.py:16`
**Issue:** `MAX_KICAD_TEXT_BYTES` and `MAX_KICAD_TEXT_NODES` live in `importer/package.py` (zip handling), and the scan-time modules now depend on that package. `tests/test_layering.py` was widened to allow it (`"importer"` in the `ALLOWED` sets), so the test passes, but the dependency points from the scanner into the importer.
**Fix:** Move the two constants to `kicad_files` or `fsutil` and re-export them from `importer.package`.

### IN-04: `suggest.manufacturer_token` repeats `manufacturers.fold`

**File:** `kicad_lib_manager/importer/suggest.py:201-211` and `:108`
**Issue:** The NFKD, strip-marks, casefold, split and drop-corporate-words steps copy `manufacturers.fold`. `_CORPORATE_WORDS = CORPORATE_WORDS` is a bare alias. `HOST_TOKENS` (line 89) still repeats the library tokens held in the manufacturer table, so two lists can drift.
**Fix:** Use `manufacturers.fold(value)` and `MANUFACTURER_ALIASES.get(fold(value))`. Drop the alias. Note `suggest` still needs the "first word" fallback from the word list.

### IN-05: Unreachable `bad` branch in the sexpr tokenizer

**File:** `kicad_lib_manager/sexpr.py:13` and `:117-122`
**Issue:** With `re.S`, `(?P<bad>.)` can never match: `atom` and `ws` already cover every character that `open`, `close` and `quote` do not. The `kind == "bad"` branch is dead. The comment says it keeps "every position matches" true, which is only a defensive guard.
**Fix:** Keep it as a guard but say so in the comment, or drop both.

### IN-06: User Guide Status column text is out of date

**File:** `kicad_lib_manager/widgets/help_dialog.py:163-164`
**Issue:** The Library Tree page lists the Status values as "OK, Missing FP or Collision". The tree now also shows `N of M fail`, `Could not check`, `No symbols`, `New` and `Changed`. The new "Atomic parts" paragraph covers some of them but the column list contradicts it.
**Fix:** Extend the list, or point to the Atomic parts section.

### IN-07: `_group_violation` and `repo_context` are hard to follow

**File:** `kicad_lib_manager/atomic_check.py:98-198` and `:374-488`
**Issue:** `_group_violation` is about 100 lines with four nested closures and three kinds of branching (single value, agreeing values, disagreeing values) that switch on `is_mpn`. `repo_context` is about 115 lines with seven closures sharing mutable cache state. Both are correct today (the end-to-end pass above), but they are where the next rule change will go wrong.
**Fix:** Split the MPN and Manufacturer judgments into two functions over a shared "group" helper, and turn the `repo_context` closures into a small class that holds the listing cache.

### IN-08: Backslash separators are judged inconsistently for model paths

**File:** `kicad_lib_manager/atomic_check.py:424-436` (`in_kicad_models`) and `:449`
**Issue:** `model_path_problem` splits `rel` on both `/` and `\`, but `in_kicad_models` splits on `/` only. A path such as `${KICAD9_3DMODEL_DIR}/X.3dshapes\a.step` passes the segment check, then fails the lookup as one segment named `X.3dshapes\a.step`. For a Custom path with a backslash the message says "names are case-sensitive", which is misleading.
**Fix:** Split with `_SEPARATOR_RE` in `in_kicad_models`, or reject a backslash up front with its own message.

---

_Reviewed: 2026-10-26T14:40:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
