---
phase: 10-importer-on-the-atomic-scheme
reviewed: 2026-10-29T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - kicad_lib_manager/importer/footprint_index.py
  - kicad_lib_manager/importer/form.py
  - kicad_lib_manager/importer/planner.py
  - tests/README.md
  - tests/test_atomic_targets.py
  - tests/test_gate_reasons.py
  - tests/test_generated_text.py
  - tests/test_import_form.py
  - tests/test_install_plan.py
findings:
  critical: 1
  warning: 7
  info: 6
  total: 14
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-10-29 (full phase 2026-10-27; incremental re-reviews 2026-10-28 and 2026-10-29)
**Depth:** standard
**Files Reviewed:** 9 (this run; the full-phase review covered 70)
**Status:** issues_found

## Summary

This is an incremental re-review of the gap-closure changes since be38bab: plan 10-29 (pad-count filter on a leading-letters-only family tie, WR-06) and plan 10-30 (a refused library name yields a blocked plan with no operations that lists every library-independent reason; the form lists the library reason first, G-10-11). The 258 tests of the five changed test modules pass with no skips (the licence-restricted ATXK sample is present). 10-29 does what it claims (WR-06 is resolved, see its re-review note). 10-30 keeps the safety property that matters: with a refused name no path is built from it, nothing is read under it and no operation is planned (traced through `build_plan`, including `../../../x`, `/x` and `D:x`). One gap remains: the claim "every library-independent reason" does not hold for the install conflicts (WR-07). Two small maintainability notes follow (IN-05, IN-06). Earlier summary, kept as written:

Previous incremental re-review: since e1235002 of the 8 listed files, after gap-closure plans 10-26 (CR-01), 10-27 (WR-02) and 10-28 (WR-05). The three fixes do what they claim for the cases they name. One narrower residual of the CR-01 class remains (WR-06) and the new tests have two weak spots (IN-04). The 137 tests of the three changed test modules pass. The rest of this section is the original full-phase summary, kept as written.

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

**Re-review 2026-10-28:** Resolved for the reported cases by 1276906. `_agreed_family_texts` ranks with `limit=None` and takes a family only when every footprint at the top score names the same one. Against the installed KiCad 10 footprints `SOIC127P600X175-8N` (48 ties), `LQFP48` (36), `WSON6` (43) and `QFN50P500X500X80-33N` (279) now give no family, and the new tests cover the two-SOIC case, an agreeing tie, a tie with a footprint that names no family, a lower-case code and an empty folder. A narrower form of the same guess survives when a tiny leading-letters-only tie agrees; see WR-06.

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

**Re-review 2026-10-28:** Resolved by f35486b. The English word no longer gives CAN: `can` was replaced by the companion phrases `can bus`, `canbus`, `can fd`, `canfd`, `can transceiver` and `can controller` (matched on the folded text, whole words only), plus the exact-case whole word `CAN` read from the original description and category (`_cased_matched`). The reproduction `You can use it; USB C receptacle` no longer gives CAN, `SPI`/`UART`/`BLE` still match in any case, and the all-caps prose residual is documented in `test_all_caps_can_gives_the_can_keyword` as an owner decision. The test gaps are in IN-04.
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

**Re-review 2026-10-28:** Resolved by 01cd7da. The new-library branch of `_finish_post_install` now passes the footprint pair whenever the footprint library is a folder of this repo (`pending.footprint_library and pending.fp_rel_path`), and `add_library_entries` leaves a table that already lists it untouched (`_add_entry` returns "listed" without a backup). The existing-library branch is unchanged, so an install into existing libraries still gets the "Press Generate Tables" hint. The four new tests in `tests/test_main_window_import.py` cover an unlisted shared library (added), a listed one (table bytes unchanged, no backup file) and both Result-view rows. Nothing found that this change breaks.
### WR-06: A package family is still taken from a small leading-letters-only tie that has no pin check

**File:** `kicad_lib_manager/importer/planner.py:82-84, 91-107` (`_MIN_FAMILY_SCORE`, `_agreed_family_texts`)
**Issue:** Residual of CR-01. The tie rule only asks that the footprints at the top score agree. At score 30 (`_SCORE_LEADING_LETTERS`) the only link to the vendor part is that the first letters of its code are a whole word of the footprint name, so a library with just a few such footprints, all of one family, lets that family through whatever the vendor part is. Reproduced against the installed KiCad 10 footprints:

| Vendor code | Top score | Footprints at the top | Family written |
|---|---|---|---|
| `SON50P150X150X60-6N` (6 pins) | 30 | `MicroCrystal_C7_SON-8_1.5x3.2mm_P0.9mm`, `SON-8-1EP_3x2mm_P0.5mm_EP1.4x1.6mm` | `SON-8` |
| `SON65P200X200X80-6N` (6 pins) | 30 | the same two | `SON-8` |

The wrong family lands in the footprint description, the generated tags, the IPC-style name and the symbol keywords, and the preview shows it as an ordinary generated change. The new test `test_a_single_leading_letters_match_supplies_its_family` only covers a case where the pin count happens to agree (`SOIC-8` for an `-8N` code), so it does not show that this is safe. This still breaks D-28 ("nothing is guessed"), in a narrower set of cases than CR-01.
**Fix:** Let a score-30 match supply a family only when the official footprint is about the same size as the vendor footprint. The vendor pad count is already known in `build_plan` (`footprint_facts` counts it); the official pad count is `len(pad_numbers(footprint_index, link) or ())`. Filter the tied footprints by it before the agreement test, allowing one extra pad for a thermal pad (`1EP`):
```python
def _agreed_family_texts(footprint_index, code, vendor_pads):
    ranked = rank(footprint_index, package_code=code, limit=None)
    if not ranked or ranked[0].score < _MIN_FAMILY_SCORE:
        return []
    tied = [e for e in ranked if e.score == ranked[0].score]
    if ranked[0].score < _SCORE_FULL_CODE:  # leading letters only: demand a matching pad count
        tied = [e for e in tied if abs(len(pad_numbers(footprint_index, e.link) or ()) - vendor_pads) <= 1]
        if not tied:
            return []
    ...  # the existing agreement loop, over `tied`
```
The simpler alternative is to raise `_MIN_FAMILY_SCORE` to 50 so that only a full-code match counts; that also drops the unique `SOIC`-style case the owner chose to keep, so it is the owner's call. Add a test with a two-footprint `SON-8` folder and a 6-pad vendor footprint that asserts no family.

**Re-review 2026-10-29:** Resolved by 29e3834 (plan 10-29). `_agreed_family_texts` now takes the vendor pad count and, when the top score is below `FULL_CODE_SCORE` (so the match rests on leading letters alone), keeps only tied footprints whose distinct pad count is readable and within one of the vendor's. Both counts come from `footprint_pad_numbers` (the vendor node directly, the official one through `_read_facts`), so empty-number and `np_thru_hole` pads are treated the same on both sides. With `words=()` and no `linked`, `rank` can only produce top scores of 30, 50 or 80, so the `< FULL_CODE_SCORE` test cleanly separates the two cases. The 6-pad `SON50P150X150X60-6N` and `SON65P200X200X80-6N` codes give no family; the boundary tests (5, 7, 8, 10, 11 pads) pass; `LQFP48` with 48 pads still gets `LQFP-48` on the live install. Nothing found that this change breaks.

### WR-07: A refused library name hides the install conflicts, although they do not depend on the library

**File:** `kicad_lib_manager/importer/planner.py:820-842` (`_refused` sets `conflicts=()`), `1534-1536` (the early return), `kicad_lib_manager/widgets/import_dialog.py:2066` (`carry_resolutions`)
**Issue:** Plan 10-30 is meant to list "every library-independent reason" so the owner does not fix one reason only to meet the next (G-10-11). The footprint and 3D model conflicts are library-independent: their keys are `footprint:Atomic_Footprints:<name>` and `model:<file>`, and the planner computes them before the refusal return. But `refuse()` goes through `_refused`, which always builds the plan with `conflicts=()` and `renames=()`, so they are thrown away. Reproduced with the Ultra Librarian sample: install it once, change the installed footprint file so it differs, then plan again. With `Atomic_Transistor_FET` the blocking reasons are `Choose Overwrite, Rename or Skip for footprint DQK0006B`; with `x` or an empty library the only reason is the library one and `plan.conflicts` is empty. After the owner fixes the name the conflict reason appears, which is the one-at-a-time experience the plan set out to remove. Worse, the dialog calls `carry_resolutions(self._resolutions, plan)` on every accepted plan, which keeps only choices whose key the plan still has. Typing a library name passes through refused states (`A`, `At`, ...), so a footprint Overwrite or Rename the owner already chose is dropped the moment the name is edited into a refused state and must be chosen again. (The loss on a refused plan existed before 10-30; the new docstring and tests now claim completeness, so the gap is a defect of this change.)
**Fix:** Keep the conflicts in the refused plan. Give `_refused` optional `conflicts` and `renames` arguments and pass the footprint and model conflicts (not the symbol ones, which need the target library) from the final `if name_refusal:` branch:
```python
if name_refusal:
    return _refused(candidate, options, layout, tools, [*issues, *name_refusal],
                    conflicts=tuple(c for c in conflicts if c.kind != "symbol"))
```
Add a test next to `test_an_empty_library_lists_every_reason_at_once` that plants a differing footprint in `Atomic_Footprints.pretty` and asserts the `Choose Overwrite, Rename or Skip` reason beside the library reason, and that a chosen resolution survives `carry_resolutions` for the refused plan.

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

### IN-04: Two keyword test rows cannot fail on the CAN rule, and two live-footprint tests depend on KiCad's file contents

**File:** `tests/test_keywords.py` (the two `("category", ...)` rows of `test_ordinary_can_gives_no_can_keyword` and `test_can_bus_text_gives_the_can_keyword_once`), `tests/test_generated_text.py` (`test_kicad_footprints_give_no_family_to_an_ambiguous_code`, `test_kicad_footprints_give_no_family_to_sot_23_5`)
**Issue:** (1) `generate_keywords` appends `split_words(category)` as keywords. The `("category", "Interface CAN")` row therefore passes on the word taken from the category alone, whether or not `_cased_matched` reads the category. The `("category", "can")` row asserts `"CAN" not in words` against a list that holds `can` from the category (the check is case-sensitive, KiCad's search is not). Neither row tests the rule. (2) The two live tests assert exact equality with the plan built without a footprints folder and name KiCad 10 contents in a comment. They have no version guard, while `tests/README.md` lists the other KiCad-10-dependent tests as skipping on another version, so a KiCad release that renames or adds one footprint fails them with no code change.
**Fix:** (1) Drop the two category rows, or put the word only in the description. (2) Skip them with the same `installed KiCad is not version 10` reason as `tests/test_stems.py`, or build the footprint folder from `stockfixtures` as the other tests of this block do.

### IN-05: After the refusal, `build_plan` mixes `library` and `target_library`

**File:** `kicad_lib_manager/importer/planner.py:881` (`target_library`), `1026`, `1409-1418`, `1456` (still use `library`)
**Issue:** 10-30 introduces `target_library = library if verdict.ok else ""` and switches `related` (1117), the keywords (1121) and the `skip` of `_linking_symbols` (1301) to it, but the later messages and keys (`_existing_source`, `bad_rename`, `symbol:{library}:...`, `symbol_kept`) still read `library`. They are unreachable with a refused name today because `sym_exists` is forced false, so no behaviour is wrong, but the next edit that reaches one of them will put a refused (possibly path-like) name into a message or key. Two names for one concept after a guard is the pattern that breaks silently.
**Fix:** After the verdict, rebind once (keep `options.library` for `_refused`) and delete `target_library`, or comment on `library` that every use below the refusal is only reachable when the name is allowed.

### IN-06: New tests lean on another test module and on the UL sample's missing Description

**File:** `tests/test_atomic_targets.py:8` (`from test_import_form import pairs`), `:50-52`, `:136` (exact error-code lists)
**Issue:** The helper `pairs` is imported from a sibling test module, so `test_atomic_targets.py` fails at collection if `test_import_form.py` is renamed or fails to import, and it relies on pytest putting `tests/` on `sys.path`. Several assertions compare the whole error list to `["install.atomic.description", "install.invalid_library"]`, which is true only while the Ultra Librarian sample has no Description; a sample with one makes `_assert_refused`, `test_an_existing_v1_library_is_not_read_while_refused` and the `test_install_plan.py` check fail for a reason unrelated to the refusal.
**Fix:** Move `pairs` to a shared helper module in `tests/` (as `installfixtures` is) and assert that `install.invalid_library` is last and the list holds nothing library-dependent, or pass `description=` in the options so the list is just the refusal.

---

_Reviewed: 2026-10-29 (incremental re-review since be38bab; full phase 2026-10-27)_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
