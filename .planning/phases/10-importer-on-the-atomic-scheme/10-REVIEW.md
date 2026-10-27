---
phase: 10-importer-on-the-atomic-scheme
reviewed: 2026-10-27T00:00:00Z
depth: standard
files_reviewed: 70
files_reviewed_list:
  - kicad_lib_manager/atomic_check.py
  - kicad_lib_manager/importer/categories.py
  - kicad_lib_manager/importer/commit_plan.py
  - kicad_lib_manager/importer/footprint_index.py
  - kicad_lib_manager/importer/footprint_text.py
  - kicad_lib_manager/importer/form.py
  - kicad_lib_manager/importer/incoming.py
  - kicad_lib_manager/importer/keywords.py
  - kicad_lib_manager/importer/plan.py
  - kicad_lib_manager/importer/planner.py
  - kicad_lib_manager/importer/preview.py
  - kicad_lib_manager/importer/siblings.py
  - kicad_lib_manager/importer/stems.py
  - kicad_lib_manager/importer/suggest.py
  - kicad_lib_manager/importer/verify.py
  - kicad_lib_manager/kicad_files.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/manufacturers.py
  - kicad_lib_manager/table_generator.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - tests/README.md
  - tests/conftest.py
  - tests/customfixtures.py
  - tests/gitfixtures.py
  - tests/installfixtures.py
  - tests/stockfixtures.py
  - tests/test_adapters.py
  - tests/test_atomic_targets.py
  - tests/test_categories.py
  - tests/test_commit_plan.py
  - tests/test_commit_step.py
  - tests/test_customfixtures.py
  - tests/test_field_cleanup.py
  - tests/test_field_rules.py
  - tests/test_footprint_index.py
  - tests/test_footprint_text.py
  - tests/test_gate_reasons.py
  - tests/test_generated_text.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_import_form.py
  - tests/test_import_preview.py
  - tests/test_importer_layering.py
  - tests/test_incoming_check.py
  - tests/test_install_apply.py
  - tests/test_install_e2e.py
  - tests/test_install_gate.py
  - tests/test_install_options_clear.py
  - tests/test_install_plan.py
  - tests/test_install_verify.py
  - tests/test_keywords.py
  - tests/test_kicad_cli.py
  - tests/test_kicad_files_write.py
  - tests/test_main_window_import.py
  - tests/test_manufacturers.py
  - tests/test_model_attach.py
  - tests/test_naming_suggest.py
  - tests/test_official_footprint.py
  - tests/test_real_vendor_samples.py
  - tests/test_samacsys_adapter.py
  - tests/test_shared_footprints.py
  - tests/test_siblings.py
  - tests/test_single_footprint.py
  - tests/test_stems.py
  - tests/test_suggest_atomic.py
  - tests/test_table_add_entries.py
  - tests/test_vendor_install.py
  - tests/test_zipfixtures.py
  - tests/zipfixtures.py
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-10-27
**Depth:** standard
**Files Reviewed:** 70
**Status:** issues_found

## Summary

I read the diff since 99688315 for the 21 product modules and checked the suspicious paths against the live code, running small experiments with the project venv. The planner, the gate, the shared-footprint conflict logic, the official-footprint link validation (exact-case listing, so typed text never forms a path) and the stem/name rule hold up. The one defect I would not ship is the package-family guess in the planner, which writes wrong data into the library. The rest are robustness gaps and one inconsistency in the post-install table step.

Test files: no test that cannot fail, no weakened assertion and no fixture writing outside `tmp_path` or the isolated QSettings path. Every assertion removed in the gate-ready migrations is either a rename (`synthetic_custom` to `atomic_custom`, `{LIB}.pretty` to `footprint_library_for(LIB)`) or a deliberate flip (a part without a 3D model is now blocked, and the test now asserts `not result.ok` plus an unchanged tree digest). The `if widget.isVisible(): assert ...` loops in `test_import_dialog.py` and `test_official_footprint.py` run against dialogs shown with `show=True` and are followed by explicit visibility assertions, so they are not vacuous. The one test-side gap is that no test covers the ambiguity in CR-01 (a vendor code whose leading letters match many official footprints).

Known and not re-reported: the unescaped tooltip in `widgets/preview_tree.py:121-122` (T-10-17) and the findings in 10-UI-REVIEW.md. WR-04 below is the same class as T-10-17 in other places of `import_dialog.py`.

## Critical Issues

### CR-01: The package family is guessed from an arbitrary official footprint and written into the description, tags and keywords

**File:** `kicad_lib_manager/importer/planner.py:81-83, 1066-1081` (threshold), `kicad_lib_manager/importer/footprint_index.py:131-154` (score)
**Issue:** `_MIN_FAMILY_SCORE = 30` equals `_SCORE_LEADING_LETTERS`, so any official footprint that merely has a name token equal to the first letters of the vendor code is accepted as the family source. `rank()` breaks the many-way tie alphabetically, so the footprint whose text names the family is effectively random. The family and pin count are then taken from that footprint's text and put into the footprint description, the generated tags, the IPC-style name and the symbol keywords. This breaks D-28 ("nothing is guessed"). It only applies when the vendor footprint's own descr and tags name no family; Ultra Librarian and SamacSys footprints named like `SOIC127P600X175-8N` usually do not.

Reproduced against the installed KiCad 10 footprints (`rank(idx, package_code=..., limit=1)`, then `package_family` over the winner's texts):

| Vendor code | Winner (score 30) | Family written |
|---|---|---|
| `SOIC127P600X175-8N` | `Package_SO:Infineon_SOIC-20W_7.6x12.8mm_P1.27mm` | `SOIC-20` (an 8-pin part) |
| `LQFP48` | `Package_QFP:LQFP-100-1EP_14x14mm_P0.5mm_EP6.9x6.9mm` | `LQFP-100` |
| `SOT95P280X145-5N` | `Diodes_SOT-553` | none (lucky) |

The wrong text lands in the file, and the preview shows it as an ordinary "generated" change, so it is easy to accept unseen.

**Fix:** Take the family from an official footprint only when the match is specific. Either require the full code in the name (`>= _SCORE_FULL_CODE`), or accept a leading-letters-only match when exactly one footprint reaches the top score:
```python
best = rank(footprint_index, package_code=code, limit=2)
unique = len(best) == 1 or (len(best) > 1 and best[0].score > best[1].score)
if best and best[0].score >= _MIN_FAMILY_SCORE and unique:
    official_texts = [...]
```
Add a test in `tests/test_generated_text.py` with a `SOIC127P600X175-8N`-style code against `stockfixtures` that has two SOIC footprints, asserting no family is taken.

## Warnings

### WR-01: Module-level footprint caches are mutated from several worker threads with no lock

**File:** `kicad_lib_manager/importer/footprint_index.py:68-72, 108-111, 175-188` (also `kicad_lib_manager/importer/siblings.py:117, 133`)
**Issue:** `_INDEX_CACHE` and `_FACTS_CACHE` are plain dicts shared by every thread. `build_index` runs `[k for k in _FACTS_CACHE if k[0] == key]` and then deletes from the dict, while `_read_facts` on another thread inserts. Two threads really do overlap: toggling to "official" starts the picker worker (`import_dialog.py:1851-1875`) and immediately calls `_request_rebuild()`, whose `build_plan` also calls `build_index` and `footprint_texts` (`planner.py:1070-1073`, `1057`). `_reset_official_choice` (`import_dialog.py:1801`) also drops the reference to a running picker worker, so a second one can start on the next package. Iterating a dict that another thread resizes raises `RuntimeError: dictionary changed size during iteration`, which surfaces as "Preview could not be built" or "KiCad's footprints could not be listed". The window is narrow, but both threads begin from a cold cache, which is the slowest and most overlapping case.
**Fix:** Guard every read-modify-write of both caches with one `threading.Lock`, and iterate a snapshot:
```python
_LOCK = threading.Lock()
...
with _LOCK:
    for stale in [k for k in list(_FACTS_CACHE) if k[0] == key]:
        _FACTS_CACHE.pop(stale, None)
    _INDEX_CACHE[key] = (state, index)
```
Apply the same lock to `_STOCK_CACHE` in `siblings.py`.

### WR-02: The keyword "CAN" is generated from the English word "can"

**File:** `kicad_lib_manager/importer/keywords.py:76-88, 118-120`
**Issue:** `INTERFACE_WORDS` contains `("can", "CAN")` and `_matched` tests whole-word presence in the folded description. The folding lowercases everything, so "can" in "can be used with ..." matches. Reproduced: `generate_keywords(description="You can use it; USB C receptacle", ...)` returns a list containing `CAN`. A wrong searchable keyword is then written to the library permanently. `spi`, `ble` and `uart` have the same weakness but are rarely ordinary words.
**Fix:** Match ambiguous words against the original-case text, or require a companion word (`can bus`, `can fd`, `can transceiver`):
```python
("can bus", "CAN"), ("can fd", "CAN"), ("can transceiver", "CAN"),
```

### WR-03: The manufacturer owner chain is not validated, and a cycle loops forever

**File:** `kicad_lib_manager/manufacturers.py:57-80` (build-time checks), `kicad_lib_manager/importer/keywords.py:94-107` (loop)
**Issue:** The comment says the table "is built at import, so a bad table edit fails at once", but `_index` and `_index_hosts` only check name and host clashes. `owner` is never checked to name a real entry or to be acyclic. `manufacturer_words` walks `entry -> lookup(entry.owner)` in a `while entry is not None` loop with no visited set, so one added line such as `Manufacturer("A", owner="B")` plus `Manufacturer("B", owner="A")` hangs `build_plan` on the worker thread for every part that resolves to either name. A dangling owner is silently dropped from the keywords.
**Fix:** In `manufacturers.py`, after `_index`, check that every `owner` folds to an entry and that following owners never revisits an entry, raising `ValueError` like the other two checks. In `manufacturer_words`, also keep a `seen` set as a second guard.

### WR-04: Vendor text is set as a tooltip unescaped in several new or extended places, while the library tooltip is escaped

**File:** `kicad_lib_manager/widgets/import_dialog.py:1559, 1574, 1772, 2261, 2312` (compare the escaped `1406`)
**Issue:** Same class as the known T-10-17. Qt treats a tooltip that looks like HTML as rich text. The phase adds `combo.setToolTip(combo.currentText())` for the vendor footprint combo (`1772`, in `_on_footprint_changed`) and keeps the same pattern for item names (`1559`, `1574`), the symbol-name label (`2261`) and `Restore default: {default}` (`2312`, where `default` is the vendor Datasheet or Description). All of these are vendor-controlled strings. The same file already shows the right pattern at `1406` (`html.escape`). The impact is spoofed or garbled tooltip content, not code execution.
**Fix:** Escape in one place, for example a helper `_plain_tip(text) -> str` returning `f"<p>{html.escape(text)}</p>"` (or `QLabel`-style `Qt.convertFromPlainText`), and use it for every tooltip built from package text.

### WR-05: After a new symbol library is installed, the shared footprint library is never checked against fp-lib-table

**File:** `kicad_lib_manager/main_window.py:828-870`
**Issue:** `_finish_post_install` has two branches. For an install that creates a symbol library, it calls `add_library_entries` with the footprint argument only when `new_footprint_lib` is true, then returns. When `Atomic_Footprints` already exists on disk but is missing from `fp-lib-table` (tables regenerated or edited, or a first install on another machine), the new symbol links to `Atomic_Footprints:<fp>` and the user gets neither an entry nor the "Press Generate Tables" hint that the existing-library branch gives. KiCad then shows an unresolved footprint library.
**Fix:** In the new-library branch, pass the footprint pair whenever the footprint library is a repo folder, not only when it is new. `add_library_entries` already leaves a table that lists the nickname alone, so it is idempotent:
```python
footprint=(
    (pending.footprint_library, pending.fp_rel_path)
    if pending.footprint_library and pending.fp_rel_path
    else None
),
```

## Info

### IN-01: Mutable and duplicated "no planned footprints" defaults

**File:** `kicad_lib_manager/importer/incoming.py:17`, `kicad_lib_manager/importer/footprint_index.py:128`, `kicad_lib_manager/atomic_check.py:42`
**Issue:** `atomic_check.py` defines `_NO_PLANNED_FOOTPRINTS` as a read-only `MappingProxyType`; `incoming.py` redefines it as a plain `{}` and passes it on. `footprint_index.rank` has `linked: Mapping[str, int] = {}`. Neither is mutated today, but both are shared mutable defaults that a later edit could corrupt.
**Fix:** Import one constant (or use `None`) in `incoming.py`, and use `linked: Mapping[str, int] | None = None` in `rank`.

### IN-02: Sibling index silently reads nothing from libraries with other indentation

**File:** `kicad_lib_manager/importer/siblings.py:36-39`
**Issue:** `_TOP_SYMBOL_RE` accepts a top-level symbol only at one tab or one to two spaces of indent. A library saved with 4-space indentation yields no entries, so no siblings are found and the suggestion silently falls through to the category map, with no log line. KiCad's own writers use tabs or two spaces, so this affects only hand-edited or third-party libraries.
**Fix:** Either accept any whitespace indent that is shallower than the first `(symbol "X_<n>_<n>"` unit sub-symbol, or log an INFO when a non-empty library file produces zero entries.

### IN-03: The official footprint picker ranking is built once per package and goes stale

**File:** `kicad_lib_manager/widgets/import_dialog.py:1851, 1872-1906`, `1766-1775`
**Issue:** The picker list is ranked from the symbol and vendor footprint chosen when the owner first switches to "official" (`_start_official_list`), then kept in `_official_links`. `_on_footprint_changed` and `_on_symbol_changed` do not reset it, so choosing a different vendor footprint or symbol afterwards leaves the "best matches first" order based on the earlier choice. The list is still complete and correct, only the order is stale.
**Fix:** Set `self._official_links = None` in `_on_footprint_changed` and `_on_symbol_changed`, and restart the list when the official radio is checked.

---

_Reviewed: 2026-10-27_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
