# Phase 7: SnapEDA and SamacSys Adapters - Pattern Map

**Mapped:** 2026-10-23
**Files analyzed:** 22 (9 new source/test, 13 modified)
**Analogs found:** 22 / 22 (all analogs are git-tracked; verified with `git ls-files`)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `kicad_lib_manager/importer/adapters/snapeda.py` (new) | adapter | transform (score markers) | `importer/adapters/ultralibrarian.py` | exact |
| `kicad_lib_manager/importer/adapters/samacsys.py` (new) | adapter | transform | `importer/adapters/ultralibrarian.py` (+ `base._name_list` for D-16) | exact |
| `kicad_lib_manager/importer/fieldrules.py` (new) | utility (leaf) | transform | `importer/naming.py` (Qt-free leaf, pure predicates) | role-match |
| `kicad_lib_manager/importer/adapters/base.py` (mod) | service | request-response | itself (`Detection`, `part_meta`, `locate`, `_read_limited`) | exact |
| `kicad_lib_manager/importer/detect.py` (mod) | registry | request-response | itself (lines 12, 15-46) | exact |
| `kicad_lib_manager/importer/package.py` (mod) | service | file-I/O | itself (caps at 17-34, `_stage_zip`, `_open_folder`) | exact |
| `kicad_lib_manager/importer/candidate.py` (mod) | model | n/a | itself (`PartMeta`, `ImportCandidate`) | exact |
| `kicad_lib_manager/importer/plan.py` (mod) | model | n/a | itself (frozen dataclasses, defaulted tail field) | exact |
| `kicad_lib_manager/importer/planner.py` (mod) | service | transform | itself, `_edit_symbol` (~150-195) | exact |
| `kicad_lib_manager/importer/preview.py` (mod) | service | transform | itself, "Path rewrites" section | exact |
| `kicad_lib_manager/importer/form.py` (mod) | service | transform | itself, `field_defaults` | exact |
| `kicad_lib_manager/importer/suggest.py` (mod) | service | transform | itself (`REFERENCE_TYPE`, `MANUFACTURER_ALIASES`) | exact |
| `kicad_lib_manager/kicad_files.py` (mod) | utility | transform | `rename_property_edit` (line ~299) | exact |
| `tests/vendorfixtures.py` (new) | test helper | file-I/O (bytes) | `tests/zipfixtures.py` + `tests/installfixtures.py` | exact |
| `tests/test_vendorfixtures.py` (new) | test | n/a | `tests/test_fixtures.py` (self-checks) | role-match |
| `tests/test_snapeda_adapter.py`, `tests/test_samacsys_adapter.py` (new) | test | request-response | `tests/test_adapters.py` | exact |
| `tests/test_field_cleanup.py` (new) | test | transform | `tests/test_install_plan.py` (`_plan`, `_property_names`) | exact |
| `tests/test_vendor_install.py` (new) | test | file-I/O | `tests/test_install_e2e.py` | exact |
| `tests/test_real_vendor_samples.py` (new) | test (gated) | file-I/O | `tests/test_install_e2e.py` skipif gate | role-match |
| `tests/test_importer_layering.py` (mod) | test | n/a | itself (`ALLOWED` map) | exact |
| `tests/test_install_plan.py::test_fields_exact_manufacturer_kept` (re-baseline) | test | | itself, lines 875-883 | exact |
| `.gitignore` (mod) | config | | none (no `downloaded_examples` rule exists today) | none |

## Pattern Assignments

### `adapters/snapeda.py` and `adapters/samacsys.py` (adapter, transform)

**Analog:** `kicad_lib_manager/importer/adapters/ultralibrarian.py` (36 lines, read in full)

**Imports + threshold** (lines 3-8):
```python
import re
from ..package import Package
from .base import Detection
UL_CLAIM_POINTS = 5
```

**Core detect pattern** (lines 15-36): class with `name = "..."`, accumulate `points` and `reasons`, then
```python
        segments = [name.split("/") for name in package.names]
        if any(seg.casefold() in _FOLDER_MARKERS for parts in segments for seg in parts[:-1]):
            points += 4
            reasons.append("KiCADv6/KiCADv5 folder")
        ...
        if package.kind == "zip" and package.source.stem.casefold().startswith("ul_"):
            points += 1
        if points < UL_CLAIM_POINTS:
            return None
        return Detection(self.name, points / 10, tuple(reasons))
```
Copy: `name` attribute becomes `"SnapEDA"` / `"SamacSys"` (D-15, exact labels); stem prefix check becomes `lib_` for SamacSys; weights per RESEARCH Pattern 1 table; use `min(points, 10) / 10`; pass `rules=` and, for SamacSys, `hints=` and `ignored_note=` through the extended `Detection`. `detect()` must never raise (Pitfall 5): marker helpers return `b""`/`None` on failure and handle a hand-built `Package` with empty `markers`.

**D-16 folder summary:** reuse the "names" idiom from `base._name_list` (base.py ~170-175): `", ".join(names[:_LISTED_NAMES])`. The default note is the `intake.ignored_members` Issue built in `package._ignored_issue` (package.py, `_IGNORED_LISTED = 20`); SamacSys builds its replacement with the same code `intake.ignored_members`, severity INFO, text `Not imported: other-CAD folders A, B, ... (62 files)`.

---

### `adapters/base.py` (mod): extend `Detection`, `part_meta`, add head/marker helpers

**Existing to extend** (lines 29-45, 52-73):
```python
MANUFACTURER_FIELDS = ("Manufacturer", "MF", "MANUFACTURER", "Manufacturer_Name")
MPN_FIELDS = ("MPN", "MP", "Manufacturer_Part_Number", "MANUFACTURER_PART_NUMBER")
DESCRIPTION_FIELDS = ("Description", "ki_description")

@dataclass(frozen=True)
class Detection:
    vendor: str
    confidence: float
    reasons: tuple[str, ...] = ()
```
Add defaulted fields at the END (`rules`, `hints`, `ignored_note`) so `Detection(name, conf, reasons)` callers stay valid. `_first()` (52-57) returns the first truthy value: make it skip `is_placeholder()` values (Pitfall 4). `part_meta(symbol)` gains a rules param and uses `clean_description` for `description`.

**Bounded-read helper pattern to copy for `read_head` / `marker_text`** (`_read_limited`, lines 76-93):
```python
    try:
        with open(pf.path, "rb") as handle:
            data = handle.read(cap + 1)
    except OSError as e:
        return Issue(Severity.WARNING, "intake.unreadable_file", f"Could not read {pf.member}: {e.strerror or e}")
```
New helpers are total: return `b""` on `OSError` rather than an Issue; `decode(errors="replace")`.

**`locate()` tail** (lines ~255-276): the `ImportCandidate(...)` construction; add `field_rules=detection.rules` and hint-filled `PartMeta` here. `ignored=tuple(package.ignored)` stays untouched (D-16 requires the full list on the candidate).

---

### `detect.py` (mod): register adapters + D-16 swap

**Registry** (line 12):
```python
ADAPTERS: list[Adapter] = [UltraLibrarianAdapter(), LooseAdapter()]
```
becomes `[UltraLibrarianAdapter(), SnapEDAAdapter(), SamacSysAdapter(), LooseAdapter()]` (before Loose so a vendor beats Loose's 0.3).

**Selection loop** (lines 24-31, ties go to registry order because of strict `>`):
```python
    for adapter in ADAPTERS:
        found = adapter.detect(package)
        if found is not None and (best is None or found.confidence > best.confidence):
            best = found
```
Add after this loop and before `locate(package, best)`: if `best.ignored_note`, `package.issues[:] = [best.ignored_note if i.code == "intake.ignored_members" else i for i in package.issues]`. Issue construction style (lines 35-40): `Issue(Severity.INFO, "intake.unknown_vendor", f"...")`. Note line 45 dedups with `dict.fromkeys`, so swap must happen before it.

---

### `package.py` (mod): `Package.markers`, `MAX_MARKER_BYTES`

**Analog:** itself. Caps live at lines 17-34 (module-level, read at call time) and `STAGE_KINDS` at 28-34. Add `MAX_MARKER_BYTES = 64 * 1024`, `MAX_MARKERS = 16`, `MARKER_NAMES` there. `Package` dataclass (lines ~90-94) gets `markers: dict[str, bytes] = field(default_factory=dict)` (use the `field(default_factory=...)` convention from `models.py`). Read inside the existing `with ExitStack()` in `_stage_zip` using `src.read(MAX_MARKER_BYTES + 1)` within the existing `_READ_ERRORS` handling; add bytes to `budget.actual`; over-cap yields INFO `intake.marker_skipped`, never a refusal. Never use `extract`/`extractall` (layering test forbids it).

---

### `fieldrules.py` (new leaf)

**Analog:** `importer/naming.py` (imports only `models`; pure functions). Must import nothing and be registered `set()` in the layering map. Contents per RESEARCH Pattern 3: `FieldRules` frozen dataclass, `GENERIC_RULES`, `STANDARD_FIELDS`, `is_placeholder()` (`value.strip().casefold() in {"", "none", "n/a"}`), `clean_description()` (`" ".join(value.split())`), `is_volatile()` using `fnmatch.fnmatchcase` on casefolded names. Protected names: Reference, Value, Footprint, Datasheet, Description, every `ki_*`, and Manufacturer/MPN targets.

---

### `kicad_files.py` (mod): `remove_property_edit`

**Analog:** `rename_property_edit` (lines ~299-302) and `set_property_edit`:
```python
def rename_property_edit(prop: PropertyRef, new_name: str) -> Edit:
    """Return the edit that replaces only the property's name token."""
    return Edit(prop.name_node.start, prop.name_node.end, quote(new_name))
```
`remove_property_edit(text, prop) -> Edit` deletes the property node span plus the preceding whitespace gap (`eol + indent`). Place it beside the other helpers. `sexpr.apply_edits` raises `ValueError` on overlap, so each property gets at most one edit.

---

### `planner.py::_edit_symbol` (mod)

**Analog:** itself, lines ~150-195. Key excerpt to extend:
```python
    def role(name, aliases, override, fallback) -> str:
        present = [p for p in (find_property(node, alias) for alias in aliases) if p is not None]
        vendor_value = next((p.value for p in present if p.value), "")
        value = override if override is not None else (vendor_value or fallback)
        exact = find_property(node, name)
        target = exact or next((p for p in present if p.value), present[0] if present else None)
        if target is None:
            add(name, value); return value
        if target is not exact:
            edits.append(rename_property_edit(target, name))
        if target.value != value:
            edits.append(set_property_edit(target, value))
        return value
    ...
    forced = fields.manufacturer if fields.manufacturer_forced else None
    role("Manufacturer", MANUFACTURER_FIELDS, forced, fields.manufacturer)
    mpn = role("MPN", MPN_FIELDS, fields.mpn, ref.name)
```
Changes: pass `candidate.field_rules.manufacturer_aliases` / `.mpn_aliases`; make `role()` also record a `FieldChange("rename", ...)` and return which alias fields it did not choose (D-08 drop, reason `duplicate`); treat `is_placeholder(p.value)` as empty in `vendor_value`; then volatile (D-05), placeholder vendor-only (D-06), Description collapse (D-07). MPN fallback becomes `meta.mpn or ref.name` (RESEARCH Pattern 4) so it matches `form.field_defaults`. Return `field_changes` alongside `edits, mpn`.

---

### `plan.py`, `candidate.py` (mod): defaulted tail fields

Pattern: frozen dataclasses with new fields appended at the end with defaults so existing `InstallPlan(**values)` test helpers keep working. Add `FieldChange` (frozen) and `InstallPlan.field_changes: tuple[FieldChange, ...] = ()`; `PartMeta.category: str = ""`; `ImportCandidate.field_rules: FieldRules = GENERIC_RULES` (candidate may import `importer.fieldrules`, update layering map).

---

### `preview.py` (mod): "Field changes" section

**Analog:** the existing "Path rewrites" section in `preview_sections` (rows `kind="rewrite"`). Insert a hidden-when-empty section after it; row text `Drop Price` / `None -> (removed)`, `Clean Description`, `Rename MF` / `-> Manufacturer`. `widgets/preview_tree.py` needs no change.

---

### `suggest.py` (mod)

Edit tables in place: `REFERENCE_TYPE` (lines ~23-46) add `"PS": "PowerSupply"`; `MANUFACTURER_ALIASES` (~65-84) add `"recom": "RECOM", "recompower": "RECOM"` following the existing `gct`/`globalconnectortechnology` entries; add `PART_CATEGORY_TYPE` and extend `type_choice` with a `category` arg returning `TokenChoice(token, "part_info", True)`; `_subcategory()` (~line 262) must treat source `"part_info"` like `"reference"`.

---

### `tests/vendorfixtures.py` (new)

**Analog:** `tests/zipfixtures.py` (docstring convention: plain helper, no `test_` prefix, stdlib only, builders return bytes) and `tests/installfixtures.py`.

**Reuse directly:**
```python
from zipfixtures import STEP_BYTES, make_zip, zip_bytes, footprint, symbol_lib, write_custom_layout, CURRENT_CUSTOM_SYMBOL_LIBS, CURRENT_CUSTOM_FOOTPRINT_LIBS
```
`symbol_lib(names, version=20211014, props={...})` (zipfixtures.py 170-189) and `footprint(name, head="module", version=None, model="RS3.stp")` (192-213) are the base builders; the vendor builders need hand-written text for the vendor-specific bits (generator atom `SamacSys_ECAD_Model`, `(id N)` props, CRLF, unquoted footprint name, `(pad None np_thru_hole ...)`), so write them as explicit line lists in the style of `symbol_lib`. Use `_quote` style escaping (BS = chr(92)). Synthetic content only (D-01): invented part, invented URLs, own `license.txt` sentence containing the word SamacSys, members under 4 KiB.

---

### `tests/test_snapeda_adapter.py`, `test_samacsys_adapter.py`

**Analog:** `tests/test_adapters.py`. Imports (lines 3-17):
```python
from zipfixtures import STEP_BYTES, VRML_BYTES, footprint, make_zip, symbol_lib, unpack_sample
from kicad_lib_manager.importer.detect import ADAPTERS, detect_candidate
from kicad_lib_manager.importer.package import Package, PackageFile, open_package
from kicad_lib_manager.models import Severity
```
Pattern (lines 29-40): `with open_package(path, REPO_ROOT) as package: candidate, issues = detect_candidate(package)` then assert `candidate.vendor`, `confidence`, symbol/footprint names and members. Also assert Unknown fallback still works for a UL/generic zip, a renamed two-file SnapEDA zip scores 0.7, and a hand-built `Package` with no markers does not raise.

---

### `tests/test_field_cleanup.py` and re-baselines

**Analog:** `tests/test_install_plan.py` helpers `_target_layout`, `_plan`, `_property_names`, `_value_of`, `vendor_symbol_lib(VENDOR, props=...)` from `installfixtures`. Run with `ToolContext()` (no CLI), never the real binary (Pitfall 9).

**Re-baseline** `test_fields_exact_manufacturer_kept` (lines 875-883):
```python
    vendor = vendor_symbol_lib(VENDOR, props={"Manufacturer": "Exact Co", "MANUFACTURER": "Other Co"})
    ...
    assert names.count("Manufacturer") == 1 and names.count("MANUFACTURER") == 1
```
change to `names.count("MANUFACTURER") == 0` and assert the drop appears in `plan.field_changes`. Add: UL sample property-name list unchanged by cleanup (guards `ki_locked`); extend `test_field_defaults_equivalence` with a SnapEDA-shaped case (cleaned Description) and a part_info-MPN case.

---

### `tests/test_vendor_install.py` and kicad-cli check (D-03, D-04)

**Analog:** `tests/test_install_e2e.py` lines 455-480:
```python
@pytest.fixture
def real_tools(kicad_cli_path):
    tools = detect_tools(find_kicad_footprint_dir())
    assert tools.kicad_cli == kicad_cli_path
    return tools

def _written_gate_issues(exe, layout, library, footprint_names=("DQK0006B",)):
    pretty = layout.footprints_dir / f"{library}.pretty"
    footprints = [(name, (pretty / f"{name}.kicad_mod").read_bytes()) for name in footprint_names]
    symbol_lib = (layout.symbols_dir / f"{library}.kicad_sym").read_bytes()
    return kicad_cli.load_gate(exe, library=library, symbol_lib=symbol_lib, footprints=footprints)

@pytest.mark.kicad_cli
def test_cli_load_check_after_install(custom_copy, ul_package, tmp_path, real_tools, kicad_cli_path):
    ...
    assert [i for i in issues if i.severity is Severity.ERROR] == [], issues
```
Copy as-is; swap `custom_copy` for a `tmp_path` layout built with `write_custom_layout(...)` so the test never reads the owner's `Custom/` tree. Never pin a format number. The `kicad_cli_path` fixture is in `tests/conftest.py` (line ~107) and skips when absent.

---

### `tests/test_real_vendor_samples.py` (gated, D-02)

**Analog:** the skipif gate pattern in `tests/test_install_e2e.py` (`KICAD_IMPORT_UAT_DIR`). Use `pytest.mark.skipif(not ZIP.exists(), reason="downloaded_examples/<name> not present (licence-restricted, local only)")` with `ZIP = REPO_ROOT / "downloaded_examples" / "LIB_RS3-1212S_H3.zip"`; `REPO_ROOT = Path(__file__).resolve().parent.parent` as in test_adapters.py line 19. Never read the real zips in a non-gated test.

---

### `tests/test_importer_layering.py` (mod)

**Analog:** itself, `ALLOWED` map (lines 30+). Register:
```python
"importer.fieldrules": set(),
"importer.adapters.snapeda": {"models", "importer.package", "importer.adapters.base", "importer.fieldrules"},
"importer.adapters.samacsys": {"models", "importer.package", "importer.adapters.base", "importer.fieldrules"},
```
and widen `importer.candidate`, `importer.adapters.base`, `importer.detect`, `importer.planner`, `importer.form`, `importer.preview`, `importer.plan` as their new imports require. An unregistered module fails the guard.

---

### `.gitignore` (mod)

No analog; no `downloaded_examples` rule exists. Add `downloaded_examples/*` then `!downloaded_examples/ul_CSD85301Q2.zip` (D-02). Note the two vendor zips are currently untracked (`??` in git status); do not `git add` them.

## Shared Patterns

### Issue / Severity contract
**Source:** `kicad_lib_manager/importer/adapters/base.py` lines 85-92, `detect.py` lines 35-40
**Apply to:** package marker reads, adapters, detect swap
`Issue(Severity.INFO|WARNING, "intake.<code>", "text")`; expected failures return Issues and never raise; codes namespaced `intake.*` / `install.*`.

### Bounded untrusted read
**Source:** `adapters/base.py::_read_limited`; caps in `package.py` 17-34
**Apply to:** `Package.markers`, `read_head`, `part_info.txt` parsing
Read `cap + 1` bytes, compare, degrade to INFO/WARNING (D-13). Parse `part_info.txt` with first 100 lines, `=` split, key length 40, value length 200, control characters stripped.

### Span-exact edits
**Source:** `kicad_files.py` (`set_property_edit`, `rename_property_edit`, `property_insert_edit`), `sexpr.apply_edits`
**Apply to:** all symbol field cleanup. One edit per property; no string `replace`.

### Defaulted-tail dataclass extension
**Source:** `Detection`, `PartMeta`, `InstallPlan`, `ImportCandidate`
**Apply to:** every new field, so hand-built instances in tests keep working.

### Layering
**Source:** `tests/test_importer_layering.py` `ALLOWED`; CONVENTIONS ("services do not import Qt")
**Apply to:** every new module; carry `field_rules` on the candidate instead of looking up adapters from the planner.

## No Analog Found

| File | Role | Reason |
|---|---|---|
| `.gitignore` rule for `downloaded_examples/*` | config | No existing rule; write per D-02 |
| `PART_CATEGORY_TYPE` table | data | Only one observed value (`Power Supply`); other keys are ASSUMED (RESEARCH) |
| `Package.markers` capture | file-I/O | Nothing today retains non-staged member bytes; design follows RESEARCH Pattern 2 using the `_stage_zip` read idiom |

## Metadata

**Analog search scope:** `kicad_lib_manager/importer/` (and `adapters/`), `kicad_lib_manager/kicad_files.py`, `tests/`
**Files read:** ultralibrarian.py, detect.py, base.py (lines 1-180, 255-276), planner.py (150-215), kicad_files.py (295-325), zipfixtures.py (1-40, 165-215), test_adapters.py (1-40), test_install_plan.py (868-890), test_install_e2e.py (455-485), test_importer_layering.py (1-40)
**Tracked-source check:** all named analogs appear in `git ls-files`; no mirror/install paths used
**Pattern extraction date:** 2026-10-23
