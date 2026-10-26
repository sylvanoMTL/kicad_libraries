# Phase 10: Importer on the Atomic Scheme - Pattern Map

**Mapped:** 2026-10-26
**Files analyzed:** 24 (10 new, 14 modified)
**Analogs found:** 22 / 24
**Source of truth:** live source under `kicad_lib_manager/` (the `.planning/codebase/` map is stale). All analog paths below are git-tracked.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `importer/stems.py` (new) | utility (rules + data) | transform | `manufacturers.py` (data table + `fold`/`lookup`) and `atomic_check.is_atomic` | role-match |
| `importer/siblings.py` (new) | service (index) | batch/file-I/O | `importer/verify.py` `find_name_elsewhere` (byte prefilter) + `importer/suggest.py` `_rank` | role-match |
| `importer/categories.py` (new) | utility (data + classify) | transform | `importer/suggest.py` `PART_CATEGORY_TYPE`, `REFERENCE_TYPE`, `type_choice` | exact (seed) |
| `importer/suggest.py` (rewrite) | service | transform | itself (`datasheet_host`, `registered_domain`, `is_aggregator_host` kept) | exact |
| `importer/keywords.py` (new) | utility | transform | `importer/fieldrules.py` + `manufacturers.py` | role-match |
| `importer/footprint_text.py` (new) | service | transform | `verify.footprint_pad_numbers` + `kicad_files.model_insert_edit` | role-match |
| `importer/footprint_index.py` (new) | service | file-I/O, batch | `importer/kicad_cli.stock_symbols_dir` + `library_scanner` listing | partial |
| `importer/incoming.py` (new) | service | request-response | `atomic_check.check_symbol` + `repo_context` | role-match |
| `atomic_check.py` (modify `repo_context`) | service | request-response | itself | exact |
| `kicad_files.py` (add descr/tags edit) | utility | transform | `kicad_files.model_insert_edit` / `set_property_edit` | exact |
| `manufacturers.py` (add hosts, drop token) | config/data | transform | itself | exact |
| `importer/plan.py` (modify contract) | model | n/a | itself | exact |
| `importer/planner.py` (modify `build_plan`) | service | CRUD/transform | itself | exact |
| `importer/form.py` (modify) | service | request-response | itself | exact |
| `importer/preview.py` (modify) | service | transform | itself | exact |
| `importer/verify.py` (modify `_linked_footprint`) | service | file-I/O | itself | exact |
| `importer/commit_plan.py`, `importer/applier.py` (modify link/`new_library`) | service | batch | themselves | exact |
| `table_generator.py` (split `add_library_entries`) | service | file-I/O | itself | exact |
| `widgets/import_dialog.py` (modify) | component | event-driven | itself (`_build_library_section`, `_item_combo`, `_framed`, `_render_strip`) | exact |
| `widgets/help_dialog.py`, `main_window.py` (post-install) | component | event-driven | themselves | exact |
| `tests/test_importer_layering.py` (modify `ALLOWED`) | test | n/a | itself | exact |
| new tests: `test_stems`, `test_siblings`, `test_categories`, `test_keywords`, `test_footprint_text`, `test_footprint_index`, `test_incoming` | test | n/a | `tests/test_import_form.py`, `tests/test_atomic_check.py` | role-match |
| `tests/customfixtures.py`, `tests/zipfixtures.py` (modify v1 constants) | test fixture | n/a | `customfixtures.atomic_part`/`write_atomic_custom` | exact |
| migrated tests (test_install_plan, _apply, _e2e, test_vendor_install, test_import_form/_dialog/_preview) | test | n/a | themselves | exact |

## Pattern Assignments

### `importer/stems.py` (new; utility, transform)

**Analog:** `manufacturers.py` (leaf module with a data tuple, import-time validation, `fold`) and `atomic_check.is_atomic` (prefix test).

Leaf/validate-at-import pattern (`manufacturers.py` 13-16, 61-79):
```python
CORPORATE_WORDS = frozenset({...})
def _index(entries):  # raises ValueError on a collision
    ...
# Built at import, so a bad table edit fails at once
_BY_FOLDED = _index(MANUFACTURERS)
```
Apply: `KICAD10_STEMS` as a frozenset, `EXCLUDED_STEMS`, `SHARED_FOOTPRINT_LIBRARY = "Atomic_Footprints"`, a casefold index built at import that raises if two stems collide, and `name_verdict(text, stems, existing) -> (ok, corrected, reason)`. Prefix test reuses `atomic_check.ATOMIC_PREFIX = "Atomic_"` (atomic_check.py:20, `is_atomic` at 43-45, case-sensitive). Allowed stems = snapshot union installed stock stems (never shrink). Layering entry: needs only `atomic_check` if it imports the prefix constant, else `set()`.

### `importer/siblings.py` (new; service, batch/file-I/O)

**Analog:** `importer/verify.py` `find_name_elsewhere` (bytes prefilter + depth-1 `_declaration_pattern`) for the index; `importer/suggest.py` `RankedLibrary` for the alternatives record.

Use the RESEARCH "Stock index (names only)" regex `rb'(?:^|\n)(?:\t| {1,2})\(symbol "([^"]+)"'` and `family_prefixes` / `pick` (RESEARCH Code Examples). Count top-level symbols only (75 not 84). Strict majority (`n * 2 > total`). No S-expression parsing of stock libraries. Cache in a module dict keyed by `(dir, entry count, newest mtime)`. Runs inside the dialog's `TaskWorker` (`widgets/import_dialog.py:182-204`, `fn(progress.emit)` signature, result/failed signals), so index builders take `progress: Callable | None = None` called as `progress(message, current, total)` per project convention.

### `importer/categories.py` (new; utility, transform)

**Analog:** `importer/suggest.py` lines 24-87 and `type_choice` (183-193).

Seed data pattern to copy and retarget to official stems:
```python
PART_CATEGORY_TYPE = {"powersupply": "PowerSupply", ...}   # key = casefolded letters+digits
def type_choice(reference, category=""):
    mapped = PART_CATEGORY_TYPE.get(re.sub(r"[^a-z0-9]", "", category.casefold()))
    ...
    match = re.match(r"[A-Za-z]+", reference.strip())
```
Change values to stems (`Converter_DCDC_Isolated`, ...); keep only unambiguous reference letters (`K`, `SW`, `TR`, `M`, `JP`, `J`); drop `U`, `Q`, `D`, `X`, `Y`. No `Crystal` stem exists (map to `Device` or nothing). Add a unit test that every target stem is in the snapshot minus excluded.

### `importer/suggest.py` (rewrite; service, transform)

**Analog:** itself. Keep `datasheet_host`, `registered_domain`, `is_aggregator_host`, `AGGREGATOR_DOMAINS`, `_SLD_LABELS` (lines 103-125, 158-199). Remove `PLACEHOLDER_TOKENS`, `TokenChoice`, `HOST_TOKENS`, `MANUFACTURER_ALIASES`, `placeholder_tokens`, `_rank`, `_subcategory`, `manufacturer_choice` token logic. New dataclass follows the existing frozen-dataclass-with-`issues: tuple[Issue, ...]` shape of `LibrarySuggestion` (145-155): `name` (empty = ask), `source`, `reason`, `alternatives`, `issues`. Issues use `Issue(Severity.INFO, code, text)` from `..models`. Manufacturer inference from host moves to `manufacturers.py` (`hosts`), keeping the aggregator guard. Layering: `ALLOWED["importer.suggest"]` currently `{"models", "manufacturers", "importer.candidate", "importer.naming"}`; add `importer.stems`, `importer.siblings`, `importer.categories`.

### `importer/keywords.py` and `importer/footprint_text.py` (new; utility, transform)

**Analog:** `importer/fieldrules.py` (pure, imports nothing, `ALLOWED = set()`) and `manufacturers.py` (`Manufacturer.owner`, `aliases`).

Pure functions returning `str`/`list[str]`; case-insensitive dedupe keeping first spelling; every keyword a single word. Footprint pad geometry reuses the skip rules of `verify.footprint_pad_numbers` (skip unnumbered and `np_thru_hole`). Descr/tags edits reuse `kicad_files` primitives (below). They take parsed nodes, never Qt.

### `kicad_files.py` (modify: add descr/tags edit primitives)

**Analog:** `kicad_files.model_insert_edit` (225-237) and `set_property_edit` (240-242).
```python
def model_insert_edit(text, footprint_node, model_path, eol) -> Edit:
    anchor = footprint_node.children[-1]
    indent = _line_indent(text, anchor.start)
    inner = indent + ("\t" if "\t" in indent else "  ")
    ...
    return Edit(anchor.end, anchor.end, eol + indent + eol.join(lines))
def set_property_edit(prop, value) -> Edit:
    return Edit(prop.value_node.start, prop.value_node.end, quote(value))
```
New `footprint_text_edit(text, footprint_node, key, value, eol)`: replace the string token if `(descr ...)`/`(tags ...)` exists, else zero-width insert after the `(layer ...)` child using the file's indent and eol. Must work for both `footprint` and legacy `module` roots (verified with kicad-cli in RESEARCH). Add to `tests/test_kicad_files_write.py` style tests.

### `importer/incoming.py` (new) and `atomic_check.repo_context` (modify)

**Analog:** `atomic_check.py` 335-420 (`FootprintTarget`, `AtomicContext`, `repo_context`).
```python
@dataclass(frozen=True)
class AtomicContext:
    resolve_footprint: Callable[[str], FootprintTarget]
    model_problems: Callable[[FootprintTarget], list[str]]

def repo_context(repo_root, fp_libs, kicad_fp_dir) -> AtomicContext:
    listings: dict[Path, frozenset[str]] = {}
    ...
    def resolve_footprint(text): ...   # exact directory listings, not path probes
```
Extend the signature with keyword-only `planned_footprints: Mapping[str, bytes] = {}` and `planned_models: Collection[str] = ()`; a planned `Lib:FP` resolves without disk, its model is judged from planned bytes, `${CUSTOM_3DMODEL_DIR}/<file>` passes if in `planned_models` or `custom_model_names()`. Do not touch rules or `check_symbol`. `incoming.py` runs `check_symbol(root, name, rel_path=..., fixable=False, ctx=ctx)` over `edited.root`, converting each `Violation` to `Issue(Severity.ERROR, f"install.atomic.{rule}", text)`. Layering: add `incoming` entry with `atomic_check`, `models`, `importer.plan`.

### `importer/plan.py` (modify; model)

**Analog:** itself. Add fields in the same frozen-dataclass style.
- `ToolContext` (20-27): add `kicad_footprints_dir: Path | None = None` and `allowed_stems: frozenset[str] = frozenset()`; `planner.detect_tools` (285-296) fills from `kicad_fp_dir` like `kicad_symbols_dir=kicad_cli.stock_symbols_dir(kicad_fp_dir)`.
- `InstallOptions` (41-79): add `footprint_target`, `official_footprint`, `keywords`, `fp_description`, `fp_tags` (None = generated). Extend `_TEXT_OVERRIDES` handling (line 38) in the same `__post_init__` blank-to-None loop; `value` stops being an override; `footprints` becomes one name.
- `FieldChange` (114-128): action gains `set`; add scope so footprint changes are not filtered by `pending` (planner.py ~1183).
- `InstallPlan` (131-189): add `footprint_library`, `footprint_link`, generated text, not-used names. `new_library` (168-169, `new_symbol_lib or new_footprint_lib`) and `pretty_path` (176-177, built from `self.library`) must describe two libraries now.

### `importer/planner.py` (modify `build_plan`)

**Analog:** itself. Touch points:
- Remove the LIB-02 block (737-744): `if sym_exists != pretty_exists: ... "install.pair_completed"`.
- `pretty` becomes `Atomic_Footprints.pretty`; `mkdir` op only if absent; keep `install.footprints_dir_missing` check (697-706) and add a casefold case-twin check against `list_footprint_libs` in the style of 679-687.
- Link strings: `link = f"{library}:{linked}"` (~1049) and `f"{library}:{fp_names[0]}"` (~879) use `footprint_library` or the official `Lib:FP`.
- Clash decision (`footprint_spec`, ~1005-1015): replace the byte digest compare
  ```python
  same=lambda name, digest: hashlib.sha256(render_fp(index, name)[0]).hexdigest() == digest,
  ```
  with `sexpr.token_stream(parse(existing))` equality; rename default `<FP>_<MPN>`; conflict key `footprint:{library}:{name.casefold()}` (1023) uses the footprint library. Overwrite warning lists symbols linking `Atomic_Footprints:<FP>` via a bytes prefilter.
- Final `InstallPlan(...)` construction (1183-1205): `new_footprint_lib=not pretty_exists` stays but refers to the shared library; `linked_footprint` stays the footprint name.
- Name verdict: call `stems.name_verdict` and return `install.invalid_library` ERROR (authoritative, as dialog is advisory).
- Run `incoming` check after final bytes; append ERROR Issues.
- `_edit_symbol` already retokens `ki_keywords` (~218); reuse for generated keywords. Value := MPN, canonical Manufacturer via `manufacturers.lookup`.
- Pad check reuses `verify.symbol_pin_numbers`, `footprint_pad_numbers`, `pin_pad_issues` (WARNING `verify.pin_pad_mismatch`).

### `importer/form.py` (modify)

**Analog:** itself.
- `blocking_reasons` (134-202): keep the `explained(issue)` pattern (153-165) so plan ERRORs duplicated by a form reason are dropped; add entries for `install.atomic.*` codes. `FormStatus` (90-101): drop `several_footprints`/`footprints_checked`, add the name verdict.
- `_issue_target` (116-131): add mapping `install.atomic.value|mpn|datasheet|description|manufacturer` to the same-named field, `install.atomic.model_3d` to a new visible target (not the hidden Remove button; RESEARCH Pitfall 10), `install.atomic.footprint` to `"footprint_name"`.
  ```python
  if code == "install.empty_required":
      return "mpn" if text.startswith("MPN") else "value"
  ```
- Remove `library_tokens` (224-239), `placeholder_tokens` import; change `NEW_LIBRARY_BADGE` (63) to ".kicad_sym only" text; `library_badge` (242-247) otherwise unchanged.
- `field_defaults` (250-279) must mirror the planner: Value = MPN, canonical Manufacturer (remove `manufacturer_choice(...).token` use, lines 269-272); keep `test_field_defaults_equivalence`.
- `build_options` (282-314): same pass-through style for the new options; `value` is no longer collected from `FIELD_NAMES` edits.
- Plain-language reason wording: no `ki_*` names.

### `importer/verify.py`, `importer/preview.py`, `importer/commit_plan.py`, `importer/applier.py` (modify)

**Analog:** themselves. `verify._linked_footprint` (54-76) hardcodes `expected = f"{plan.library}:{plan.linked_footprint}"` and looks the `.pretty` up in `plan.layout.footprints_dir`:
```python
expected = f"{plan.library}:{plan.linked_footprint}"
...
pretty = f"{lib}.pretty"
if pretty not in _listing(plan.layout.footprints_dir): ...
```
Use `plan.footprint_link`; for an official link resolve in `plan.tools.kicad_footprints_dir`. Same replacement for `f"{plan.library}:{plan.linked_footprint}"` at preview.py:238, commit_plan.py:147, verify.py:131, import_dialog.py:1964; `plan.pretty_path` at preview.py:184, main_window.py:823; `plan.new_library` at applier.py:31, commit_plan.py:145/206, main_window.py:638-644/820/827. Add "Not used" and "Field changes (set)" sections in preview in the existing section style.

### `table_generator.py` (modify `add_library_entries`)

**Analog:** itself (369-400). Current shape: one `nickname`, both tables, `_add_entry(tag, path, nickname, rel_path, backup_number, issues)` per `("sym_lib_table", sym_rel_path), ("fp_lib_table", fp_rel_path)`, outcomes `added|listed|skipped`. Split into independent sym and fp calls each with its own nickname and optional `None` (official footprint adds no fp entry); keep the backup numbering, `table.dest_missing` guard, and success/info message strings (message substrings drive log severity, per CONVENTIONS). `main_window._PostInstall` (≈815-824) carries two nicknames.

### `widgets/import_dialog.py` (modify; component, event-driven)

**Analog:** itself.
- `_build_library_section` (798-846): keep the editable combo, `NoInsert`, `textActivated` + `lineEdit().textEdited` wiring, `_framed(combo, "library")`, badge label. Replace `setCompleter(None)` (comment says inline completion would change case) with a `QCompleter` in popup mode, `setFilterMode(Qt.MatchFlag.MatchContains)`, case-insensitive, and connect `activated` too. Existing libraries first, `insertSeparator`, then remaining `Atomic_<stem>`. Remove `_token_line` and `_token_hint`/`_TOKEN_HINT` (lines 826-846); put the reason in the combo tooltip, built with `html.escape` inside `<p>` (T-07-34).
- `_item_combo` (1338-1350): reuse for the single-choice footprint picker, replacing `_build_footprint_list` (1531).
- `_framed(widget, key)` (758-775): reuse for new fields (keywords, footprint description, footprint tags) with `self._field_frames[key]` and `self._reason_targets[key]`; make Value read-only.
- `_render_strip` (2298-2325): reasons already render as `reason:{i}` links with escape; no change except wording. `_reason_targets["model"]` (~1457) must point at the visible "Add 3D model..." button.
- Long work: `TaskWorker(fn)` (182-204) for index building; follow the serialised latest-wins `build_plan` pattern.
- Naming: handlers `_on_<event>`, widgets `self._<name>`, fully qualified Qt enums.

### `tests/test_importer_layering.py` (modify)

**Analog:** itself (`ALLOWED` dict, lines ~35-80). Register every new module, for example:
```python
"importer.suggest": {"models", "manufacturers", "importer.candidate", "importer.naming"},
"importer.verify": {"models", "fsutil", "kicad_files", "sexpr", "importer.plan", "importer.layout"},
```
New entries: `importer.stems`, `importer.siblings`, `importer.categories`, `importer.keywords`, `importer.footprint_text`, `importer.footprint_index`, `importer.incoming`. Also update `importer.planner`/`importer.form` allowed sets and `tests/test_layering.py` for `atomic_check` and `kicad_files` additions.

### Tests, fixtures

**Analog:** `tests/customfixtures.py` `atomic_part(...)` (139-163) and `write_atomic_custom(root)` (379) for synthetic `Atomic_` libraries; `tests/test_import_form.py` for form tests (`test_field_defaults_equivalence`, `test_build_options_*`). Rules: the suite never writes to or depends on live `Custom/`; real-sample tests use `downloaded_examples/` and skip when absent; kicad-cli tests pin KiCad 10; a snapshot-vs-live KiCad 10 stem test skips when absent. Do not hard-code 84 CSD siblings (75 top-level). Add a split-family test (MAX4-like) that must fall through. About 240 `library=` call sites and 250 v1-name mentions across 14 test files need mechanical retargeting; `CURRENT_CUSTOM_SYMBOL_LIBS` / `CURRENT_CUSTOM_FOOTPRINT_LIBS` in `tests/zipfixtures.py` need Atomic counterparts; the UAT expectation `PowerSupply_SubCategory_RECOM` becomes `Atomic_Converter_DCDC_Isolated`.

## Shared Patterns

### Issue-based reporting (no exceptions)
**Source:** `models.Issue`/`Severity`, used in `suggest.py` 17 and `form.py` 13. **Apply to:** all new services (`incoming`, `siblings`, `footprint_index`). Return `list[Issue]`; messages are plain language; keep substrings that callers key on (`Warning:`, `removed`, `Failed`, `Could not`, `not found`).

### Qt-free layering
**Source:** `tests/test_importer_layering.py`. **Apply to:** every module under `importer/`: relative imports only, register in `ALLOWED`, no PySide6.

### Preview and install share one `InstallPlan`
**Source:** `plan.py`. **Apply to:** generated keywords/description/tags and footprint link. The dialog fills unedited edits from the plan; an edit becomes an `InstallOptions` override; `build_plan` is the single enforcement point.

### Plain-language reasons with field targets
**Source:** `form.blocking_reasons` + `Reason(text, target)` + `import_dialog._framed`/`_reason_targets`. **Apply to:** every atomic failure and name verdict. Escape with `html.escape` for strip and tooltips.

### Canonical manufacturer
**Source:** `manufacturers.lookup`/`fold`/`Manufacturer.owner`. **Apply to:** planner Manufacturer write, `field_defaults`, keywords. Add `hosts` to the table; drop `token`/`token_map` once suggest no longer uses them. Do not write library tokens (`TI`) as Manufacturer.

### Safe writes and edits
**Source:** `sexpr.parse`, `kicad_files` `Edit`/`apply_edits`, `fsutil.atomic_write_*`, `applier.apply_plan`, `kicad_cli.load_gate`. **Apply to:** all file changes; never regex-edit vendor text, never write directly.

### Untrusted vs trusted text
Vendor files keep caps (8 MiB, 1,000,000 nodes via `parse_bytes`); KiCad stock libraries are trusted but large: byte regex for names, lazy reads capped by `MAX_KICAD_TEXT_BYTES`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `importer/footprint_index.py` | service | file-I/O/batch | Nothing indexes KiCad's footprint tree yet; use `os.listdir` of `kicad_fp_dir` (`stock_symbols_dir` shows the sibling-dir convention) and RESEARCH Pattern 8 |
| Pad geometry (pitch/body) in `footprint_text.py` | service | transform | No geometry code exists; follow RESEARCH Pattern 7 pitch algorithm and verify.py pad-skip rules |
| Filterable `QCompleter` popup picker for `Lib:FP` | component | event-driven | No completer-based widget exists (current combo disables it); follow RESEARCH Pattern 10 |

## Metadata

**Analog search scope:** `kicad_lib_manager/`, `kicad_lib_manager/importer/`, `kicad_lib_manager/widgets/`, `tests/`.
**Files read:** suggest.py (1-200), form.py, plan.py, manufacturers.py, plus targeted ranges of kicad_files.py, atomic_check.py, planner.py, table_generator.py, verify.py, kicad_cli.py, import_dialog.py, customfixtures.py, test_importer_layering.py.
**Pattern extraction date:** 2026-10-26
