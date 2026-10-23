---
phase: 07-snapeda-and-samacsys-adapters
reviewed: 2026-10-23T00:00:00Z
depth: standard
files_reviewed: 30
files_reviewed_list:
  - .gitignore
  - kicad_lib_manager/importer/adapters/base.py
  - kicad_lib_manager/importer/adapters/samacsys.py
  - kicad_lib_manager/importer/adapters/snapeda.py
  - kicad_lib_manager/importer/candidate.py
  - kicad_lib_manager/importer/detect.py
  - kicad_lib_manager/importer/fieldrules.py
  - kicad_lib_manager/importer/form.py
  - kicad_lib_manager/importer/package.py
  - kicad_lib_manager/importer/plan.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/preview.py
  - kicad_lib_manager/importer/suggest.py
  - kicad_lib_manager/importer/verify.py
  - kicad_lib_manager/kicad_files.py
  - tests/test_adapters.py
  - tests/test_field_cleanup.py
  - tests/test_import_dialog.py
  - tests/test_import_form.py
  - tests/test_importer_layering.py
  - tests/test_install_plan.py
  - tests/test_install_verify.py
  - tests/test_naming_suggest.py
  - tests/test_package_zip.py
  - tests/test_real_vendor_samples.py
  - tests/test_samacsys_adapter.py
  - tests/test_snapeda_adapter.py
  - tests/test_vendor_install.py
  - tests/test_vendorfixtures.py
  - tests/vendorfixtures.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-10-23
**Depth:** standard
**Files Reviewed:** 30
**Status:** issues_found

## Summary

I read the Phase 7 diff (`b38997e..HEAD`) and its surrounding code. The new vendor adapters, the in-memory marker reader, the field-cleanup rules in `_edit_symbol`, the `Field changes` preview section and `remove_property_edit` hold up. I traced these cases:

- Edit overlaps between a removal and a zero-width insert at the same offset.
- Adjacent removals.
- A removal next to a symbol-rename edit.
- The `handled` set stopping a property from receiving two edits.

All of them are safe under `sexpr.apply_edits`' sort order.

`part_info.txt` text cannot reach a path. `sanitize_name` reduces every name to ASCII, and the 40/200/100 caps and control-character stripping hold. Marker reads stay inside the existing hostile-zip prescan and size budget.

I found no security vulnerability and no correctness bug that corrupts data. I ran the full suite with the project venv: 1891 passed, 21 failed, 5 skipped. The 21 failures are environmental. The suite reads the live `Custom/` submodule, and its checkout is now ahead of the commit the parent repo records (WR-01). The remaining findings are robustness and maintainability issues.

## Warnings

### WR-01: 21 tests fail because they copy the live `Custom/` submodule, whose checkout already holds the UL sample part

**File:** `tests/conftest.py:79-89` (fixture `custom_copy`); affects `tests/test_install_plan.py` and `tests/test_import_dialog.py` among the reviewed files

**Issue:** `custom_copy` copies the real `Custom/{Symbols,Footprints,3DModels}` into `tmp_path`. Many tests then install the Ultra Librarian sample `CSD85301Q2` into `IC_Battery_Charger_TI` and assert a fresh install.

- The working-tree `Custom` is at `eecac22` ("added CSF85301Q2 Dual mosfet"). The parent repo records `485d530` (`git ls-tree HEAD Custom`), and `git status` shows ` M Custom`.
- At `eecac22`, `Custom/3DModels/CSD85301Q2.stp` and the installed footprint and symbol already exist. At `485d530` they do not.
- The planner correctly sees the model as identical and plans no write.

Assertions such as `result.touched == (model, footprint, symbol)`, `'+ Custom/3DModels/CSD85301Q2.stp'` and "source gone at apply must fail" then break.

Failing tests in the reviewed files:
- `tests/test_install_plan.py::test_model_changed_after_plan_is_refused_by_apply`
- `tests/test_install_plan.py::test_version_real_cli_into_20241209`
- `tests/test_install_plan.py::test_library_real_cli_new_header`
- `tests/test_install_plan.py::test_noop_second_plan_after_normalised_apply`
- `tests/test_import_dialog.py::test_tracer_ul_import_end_to_end`
- `tests/test_import_dialog.py::test_preview_sections_follow_plan_ops`

The same cause also fails 15 tests in unreviewed files: `test_commit_plan`, `test_import_preview`, `test_install_apply` (7), `test_install_e2e` (5) and `test_kicad_cli`. The suite goes red whenever the owner imports the sample part for real, which is the exact workflow this tool exists for. This phase did not add the fixture. It still affects the phase's own regression gate, and the new tests deliberately avoid the live tree (`test_vendor_install.py` header).

**Fix:** Do not use the live checkout as test input. Either of these works:
```python
# conftest.py: build the fixture from the committed tree, not the working tree
subprocess.run([GIT, "-C", str(REPO_ROOT), "submodule", "status", "Custom"], ...)
# or copy from `git -C Custom archive <recorded sha>` into tmp_path
```
Or use `write_custom_layout(CURRENT_CUSTOM_*_LIBS)` as the new tests do. At minimum, make `custom_copy` skip when the sample part's model already exists in the copy, so the suite reports "skipped" instead of "failed".

### WR-02: Vendor-controlled property values now reach Qt tooltips, which auto-detect rich text

**File:** `kicad_lib_manager/importer/preview.py:268-282` (source of the data); rendered by `kicad_lib_manager/widgets/preview_tree.py:81-83`

**Issue:**
- `_field_changes_section` puts up to 57 characters of each dropped or cleaned property value (`change.old`, vendor controlled) into `PreviewRow.detail`.
- `preview_tree._row_item` sets that same string as `item.setToolTip(1, row.detail)`. The comment above it says "QTreeWidgetItem never interprets markup". That holds for item text but not for tooltips: Qt treats a tooltip as rich text when `Qt::mightBeRichText` matches, for example `<b>...</b>` or `<img src=...>`.
- A hostile SnapEDA, SamacSys or loose symbol with a property such as `Price = "<img src='file:///...'>"` could therefore render markup or load a local image in the preview. This is a display-spoofing and information-disclosure surface, not code execution. It is new because this phase is the first to show raw vendor property values.

**Fix:** Make the tooltip plain text in `preview_tree._row_item`:
```python
from PySide6.QtCore import Qt
item.setToolTip(1, Qt.convertFromPlainText(row.detail))  # or "<qt>" + html.escape(row.detail) + "</qt>"
```
Apply the same to column 0. Alternatively, strip `<` and `>` in `preview._shown`.

### WR-03: Marker members beyond `MAX_MARKERS` are dropped silently, in archive order rather than shallowest first

**File:** `kicad_lib_manager/importer/package.py:448` (zip) and `:613` (folder)

**Issue:** `markers[:MAX_MARKERS]` keeps the first 16 marker-named members in walk order and discards the rest with no Issue. `marker_text()` later prefers the shallowest match, but only among the kept ones. A zip that holds 16 or more nested `license.txt` or `how-to-import.htm` files before a root-level `part_info.txt` loses that file. The adapter then misses its 3 points and the `hints` (manufacturer, MPN, category), and the `intake.part_info_ignored` note says nothing about why. `test_marker_limits` locks in the first-come behaviour. The cap itself is fine. The silence and the ordering are the problem.

**Fix:** Sort candidates by depth before slicing, and report the overflow:
```python
ordered = sorted(markers, key=lambda m: (m[2].count("/"), m[2]))
for source, info, name in ordered[:MAX_MARKERS]:
    ...
if len(ordered) > MAX_MARKERS:
    package.issues.append(Issue(Severity.INFO, "intake.marker_skipped",
        f"Read {MAX_MARKERS} of {len(ordered)} marker files in {path.name}"))
```
Do the same in `_open_folder`.

### WR-04: The SamacSys "other-CAD folders" summary reports a file count that is not the folders' file count

**File:** `kicad_lib_manager/importer/adapters/samacsys.py:120` (asserted by `tests/test_real_vendor_samples.py:144-145`, `tests/test_samacsys_adapter.py:135`)

**Issue:** The note reads `Not imported: other-CAD folders X, Y, ... (N files)`, but `N` is `len(package.ignored)`. That counts every ignored member, including root-level `license.txt`, `version.bin`, `part_info.txt`, PDFs and the `.epw` file, none of which sit in an other-CAD folder. For the real sample, 62 is the whole ignored list. The user is told 62 files live in the named folders, so the line overstates what the folders contain. The tests assert the same number, so they would pass a fix only after being rewritten.

**Fix:** Count only the members whose first segment below `base` is one of the listed folders:
```python
count = sum(1 for n in package.ignored
            if (r := _below(base, n)) is not None and "/" in r
            and r.split("/", 1)[0].casefold() != "kicad")
return Issue(..., f"... other-CAD folders {names} ({count} files)")
```
Alternatively, reword to "(N ignored files)" and keep the count.

## Info

### IN-01: Dead re-exports and an unused import in `adapters/base.py`

**File:** `kicad_lib_manager/importer/adapters/base.py:20-28`

**Issue:** The comment says the field tuples "stay importable from here". A repo-wide grep finds no importer of `MANUFACTURER_FIELDS` or `MPN_FIELDS` from `adapters.base`. `snapeda.py` and `planner.py` import from `fieldrules`. Both names are unused in `base.py` itself, so they are dead re-exports that a linter would flag as unused imports. `DESCRIPTION_FIELDS` is used.

**Fix:** Drop `MANUFACTURER_FIELDS` and `MPN_FIELDS` from the import, and shorten the comment.

### IN-02: Scoring weights are hard-coded twice in each adapter

**File:** `kicad_lib_manager/importer/adapters/samacsys.py:145-176`, `kicad_lib_manager/importer/adapters/snapeda.py:39-49`

**Issue:** The weights appear once in the module docstring and again as literals (`points += 5/3/1/2`). Only the claim threshold is a named constant. Changing a weight needs two edits, and nothing keeps them in step.

**Fix:** Name the weights as module constants (`_W_GENERATOR = 5` and so on) and have the docstring and code use them.

### IN-03: `is_protected` compares standard field names case-sensitively but `ki_` case-insensitively

**File:** `kicad_lib_manager/importer/fieldrules.py:48`

**Issue:** `name in STANDARD_FIELDS` is exact-case, while the prefix test uses `casefold()`. A vendor property spelled `description`, `datasheet` or `value` with an empty value is not protected and is dropped as a placeholder. If another vendor property has the same name, it also loses the alias handling. This is unlikely in practice and the rule is only inconsistent. Be aware that GENERIC rules apply the placeholder drop to every vendor, UL and loose files included.

**Fix:** Compare `name.casefold()` against a casefolded standard set, or document that exact-case is intended.

### IN-04: `_kicad_base` takes the first "kicad" path segment, so an outer folder named `KiCad` skews the summary and the +1 score

**File:** `kicad_lib_manager/importer/adapters/samacsys.py:73-85`

**Issue:** For a package picked from a folder such as `KiCad/LIB_X/KiCad/x.kicad_sym`, the first segment matches, `base` becomes `""`, and sibling or other-CAD folders are computed relative to the wrong level. The summary then names the wrong folders. The effect is cosmetic, because a package is only claimed on the generator or `part_info.txt` evidence.

**Fix:** Prefer the deepest "kicad" segment (`reversed(list(enumerate(parts)))`), since the KiCad folder directly holds the files.

---

_Reviewed: 2026-10-23_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
