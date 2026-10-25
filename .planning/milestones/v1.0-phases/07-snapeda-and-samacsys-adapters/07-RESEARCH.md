# Phase 7: SnapEDA and SamacSys Adapters - Research

**Researched:** 2026-10-23
**Domain:** Vendor-package recognition (adapter registry), vendor-aware symbol-field cleanup in the shared plan/preview, SamacSys `part_info.txt` naming hints, licence-safe synthetic fixtures (Python 3.14 stdlib + PySide6 6.12 desktop app, pytest 9.1.1)
**Confidence:** HIGH for everything derived from the two real samples and the current code; MEDIUM for the `PartCategory` table (one observed value) and for SnapEDA zips that carry a 3D model (no sample)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Carried forward (locked)**
- **Registry:** adapters are appended to `ADAPTERS` in `kicad_lib_manager/importer/detect.py`, and callers never change (Phase 3 D-09). A zip with no recognised vendor still imports as generic `Unknown`.
- **Legacy files:** KiCad 5 files beside v6+ files are ignored with one INFO (Phase 3 D-10). The "re-download" rejection applies only per D-11. A `(module ...)` footprint is accepted with WARNING `intake.legacy_footprint_syntax` (Phase 3 D-18).
- **Staging:** intake stages only `.kicad_sym` / `.kicad_mod` / `.step` / `.stp` / `.wrl`. Every other member is listed and never written to disk (Phase 3 D-07). The hostile-zip refusals and size caps of D-05, D-06 and D-19 apply unchanged.
- **Manufacturer and MPN:** the first vendor alias for each role is renamed in place to `Manufacturer` / `MPN` (Phase 4 D-12). Existing `Custom/` symbols are never touched.
- **Default names:** the footprint keeps its vendor name by default and is editable (`RS3`, `GCT_USB4145-03-0170-C_REVA2`). The symbol's Footprint field is always rewritten to `<Lib>:<FP>`, including SnapEDA's `USB4145-03-0170-C_REVA2:GCT_...` and SamacSys's bare `RS3`.
- **3D model:** the model is saved as `<MPN>.<ext>` through `sanitize_name` (Phase 3 D-15), so `RS3-1212S/H3` becomes `RS3-1212S_H3.stp`. The bare vendor model path is stale and is rewritten to `${CUSTOM_3DMODEL_DIR}/...` (Phase 4). With no model, the part installs without one and warns (INTK-08). SnapEDA is the no-model case.
- **Preview and commit:** preview comes before any write, and the preview and the install share one plan (PREV-01..07). The commit trailer `Import-Vendor:` comes from the vendor label (Phase 6).

**Test fixtures & licence**
- **D-01: Committed fixtures are synthetic, and the real zips stay local.** Both GitHub repos (`sylvanoMTL/kicad_libraries`, `sylvanoMTL/kicad_custom_library`) are public. SamacSys `license.txt` forbids distributing its models in any form usable as a PCB library component. So the committed fixtures are synthetic zips, written from scratch, that copy each vendor's layout and markers: folder tree, `license.txt` / `part_info.txt` / `version.bin` / `how-to-import.htm`, the generator string, property names, the `(module ...)` footprint syntax, bare model paths, legacy `.lib` / `.dcm` / `.mod` siblings, other-CAD folders, and a tiny STEP with a valid `ISO-10303-21;` header. No vendor geometry or models are copied. The real zips are never committed. (Reversibility: one-way.)
- **D-02: Real-sample tests run automatically when the zips are present, and git ignores the zips.** Tests look for `downloaded_examples/USB4145-03-0170-C_REVA2.zip` and `downloaded_examples/LIB_RS3-1212S_H3.zip` by name. When a zip is missing, its test skips with a clear reason. There is no env var. `.gitignore` excludes `downloaded_examples/*` except `!downloaded_examples/ul_CSD85301Q2.zip`, which stays tracked.
- **D-03: Install tests target a small synthetic `Custom/` built in `tmp_path`**: a couple of libraries plus `3DModels/`. They must not depend on the owner's working tree. Success criterion 3 is met with this fixture. The 3 existing tests that read the real tree are not fixed here.
- **D-04: A version-agnostic kicad-cli load check.** A `kicad_cli`-marked test loads each installed SnapEDA and SamacSys library (symbol and footprint) with kicad-cli. It asserts that the load succeeds and never pins a format number, because the installed KiCad 10 CLI writes 20251024. It skips when kicad-cli is absent. It runs on the synthetic fixtures, and also on the real zips when they are present.

**Vendor field cleanup (incoming symbols only)**
- **D-05: Drop volatile fields and keep identifiers.** Dropped (go stale): price, stock and availability fields and their links. SnapEDA: `Price`, `Availability`, `Check_prices`. SamacSys: `Mouser Price/Stock`, `Arrow Price/Stock`. Kept (stay true): distributor part numbers and source links, such as `Mouser Part Number`, `SnapEDA_Link`, `STANDARD`, `PARTREV`, `MAXIMUM_PACKAGE_HEIGHT`. The volatile-field list is defined per adapter. A small generic list (names like `Price`, `Stock`, `Availability`, `*Price/Stock`) applies to UL, loose and unknown packages.
- **D-06: Drop vendor-only fields whose value is empty or a placeholder**, compared case-insensitively after trimming: `""`, `None`, `N/A`. Examples: SnapEDA `Package "None"`, SamacSys `Height ""` and `Arrow Part Number ""`. KiCad standard fields (`Reference`, `Value`, `Footprint`, `Datasheet`, `Description` / `ki_description`, `ki_keywords`, `ki_fp_filters`) are never dropped by this rule. An empty Datasheet stays valid.
- **D-07: Description is trimmed and its whitespace collapsed** for every vendor: leading and trailing whitespace is stripped, and internal runs of spaces and newlines become one space. The cleaned text is what the preview shows and edits.
- **D-08: Duplicate Manufacturer/MPN aliases are dropped.** After the D-12 rename, the remaining alias fields for the same role are removed from the incoming symbol, so each role has one source of truth. SnapEDA: `MF` -> `Manufacturer` = "Global Connector Technology", and `MANUFACTURER "GCT"` is dropped. `MP` -> `MPN`, and `SNAPEDA_PN` is dropped. The alias lists are per adapter, extending `MANUFACTURER_FIELDS` / `MPN_FIELDS` in `importer/adapters/base.py` (for example `SNAPEDA_PN` as a SnapEDA MPN alias). This extends Phase 4 D-12. It still never touches existing `Custom/` symbols.
- **D-09: The rules apply to all vendors.** D-06, D-07 and D-08 run for every package. D-05 uses the winning adapter's volatile-field list, or the generic list. The UL tracer and e2e expectations may change and are re-baselined. Every dropped field and every cleaned value appears in the preview as a planned change, the same as a rename. There is no per-field "keep" toggle in this phase.

**Names & metadata hints**
- **D-10: The symbol name and Value keep the vendor form.** `USB4145-03-0170-C_REVA2` stays as both symbol name and Value; revision suffixes are not stripped. The `MPN` field already holds the clean `USB4145-03-0170-C`.
- **D-11: SamacSys `part_info.txt` feeds naming.** `PartCategory` maps to a library Type token through a small table, for example `Power Supply`->`PowerSupply`, `Connector`->`Connector`, `Integrated Circuit`->`IC`. The planner or researcher fills in the full table. An unmapped category falls back to the Reference map. `Manufacturer` and `PartNumber` from `part_info.txt` are used only when the symbol lacks them. Symbol properties always win. Also add `PS`->`PowerSupply` to `REFERENCE_TYPE` in `importer/suggest.py`. Expected suggestion for the sample: `PowerSupply_SubCategory_RECOM`. `SubCategory` stays a placeholder that blocks Install until edited, unless token overlap with existing libraries fills it. (Reversibility: costly.)
- **D-12: Add `recom` / `recompower` -> `RECOM` (brand casing) to `MANUFACTURER_ALIASES`.** (Reversibility: costly.)
- **D-13: `part_info.txt` is read in memory, bounded, and never written.** It is not a staged kind under Phase 3 D-07, so it is read from the zip with a small byte cap (planner picks it, e.g. <=64 KiB) and parsed as `key=value` lines. Malformed or oversized content is ignored with an INFO or WARNING Issue, never a refusal. The same bounded in-memory read applies to any other marker text used for detection (D-14).

**Detection & vendor label**
- **D-14: Recognition uses file names plus content markers.** Name markers: SnapEDA `how-to-import.htm` redirecting to snapeda.com; SamacSys `LIB_` zip prefix, `license.txt`, `part_info.txt`, `version.bin`, `<Part>/KiCad/` beside many other-CAD folders. Content markers: SnapEDA `SnapEDA_Link` / `SNAPEDA_PN` symbol properties, a snapeda.com URL; SamacSys `(generator SamacSys_ECAD_Model)`, `SamacSys` in `license.txt`. A renamed SnapEDA zip holding only the two KiCad files is still recognised from its symbol. Marker reads stay within the existing caps (`MAX_KICAD_TEXT_BYTES`, node ceiling) and D-13's bounded read. Scoring follows the UL adapter's points-and-threshold style. Tie-breaking stays registry order.
- **D-15: Vendor labels are `SnapEDA` and `SamacSys`.** They appear in the dialog and in the `Import-Vendor:` commit trailer. No distributor suffix, no rebrand naming.
- **D-16: SamacSys's other-CAD members are summarised by folder.** Instead of the 20-paths-plus-"and N more" list, one INFO line: `Not imported: other-CAD folders Altium, Allegro, CADSTAR, ... (62 files)`. The full member list stays on the candidate (`ImportCandidate.ignored`), so nothing is lost. Other vendors keep the current list.

### Claude's Discretion
- The detection scoring weights, thresholds and confidence values for both adapters, and how `detect()` gets access to the bounded content markers. The `Package` and `Adapter` protocol may be extended, as long as callers of `detect_candidate` don't change.
- Where the field-cleanup step lives (an adapter hook vs. a planner step), as long as preview and install share one plan.
- The full `PartCategory`->Type table and the generic volatile-field name list.
- How the synthetic fixtures are produced: `tests/fixtures/build_fixtures.py` generating them byte-exactly, or committed small zips with self-checks as in Phase 1.
- The byte cap for marker and `part_info.txt` reads.

### Deferred Ideas (OUT OF SCOPE)
- Distributor in the vendor label, e.g. "SamacSys (Mouser)". Rejected for now (D-15).
- A per-field "keep" toggle in the preview for fields the cleanup would drop.
- Stripping SnapEDA `_REVxx` revision suffixes from symbol names (rejected, D-10).
- Licence review of the already-tracked `downloaded_examples/ul_CSD85301Q2.zip` in the public repo.
- Moving the 3 tests that read the real `Custom/` tree onto the synthetic `Custom/` fixture built here (existing Active item in PROJECT.md).
- Also out of phase: converting KiCad 5 legacy files (FMT2-01), migrating existing `Custom/` symbols' `MF`/`MP`/`MANUFACTURER` fields (META2-02), downloading from vendor sites, the KiCad 10 CLI format-number failures.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTK-03 | A SnapEDA zip is recognised and its symbol, footprint and any 3D model are found, verified against a real SnapEDA download in `downloaded_examples/` | Scoring table for `SnapEDAAdapter` (Section "Detection design"); real sample inspected: 3 members, no model, `how-to-import.htm`, symbol properties `SnapEDA_Link` / `SNAPEDA_PN`; `locate()` already finds all items, so the work is recognition + cleanup + fixtures; real-sample test skipif by file name (D-02) |
| INTK-04 | A SamacSys / Component Search Engine zip is recognised and its KiCad symbol, footprint and 3D model are found, verified against a real CSE download | Scoring table for `SamacSysAdapter`; real sample: 69 members, 62 ignored, 4 legacy, `(generator SamacSys_ECAD_Model)`, `(module "RS3")`, bare `(model RS3-1212S_H3.stp ...)`; folder summary (D-16) reproduces "(62 files)"; `part_info.txt` bounded read + hints |
</phase_requirements>

## Summary

Both real samples already install end to end through the generic path today (probed this session: `build_plan` + `apply_plan` into a synthetic `Custom/` succeed with and without kicad-cli, and `kicad_cli.load_gate` returns no issues for either sample on KiCad 10.0.7). So Phase 7 is three things: (1) recognise the vendor (two new adapters plus a way for `detect()` to read a few bounded non-staged text members), (2) clean the incoming symbol (drop volatile / placeholder / duplicate-alias fields, collapse the description) in the shared plan so the preview shows every change, and (3) synthetic licence-safe fixtures plus tests. Naming gets two small table edits (`PS`, `recom`/`recompower`) plus a `PartCategory` table fed by `part_info.txt`.

The code needs these structural changes, all additive and defaulted so no caller of `detect_candidate` changes: `Package.markers` (bounded bytes of a whitelist of non-staged members, captured while the zip/folder is open), `Detection` gains optional `rules` / `hints` / `ignored_note`, `ImportCandidate` gains `field_rules`, `PartMeta` gains `category`, `InstallPlan` gains `field_changes`, the preview gains a "Field changes" section, and `kicad_files` gains a `remove_property_edit`. A new Qt-free leaf module (`importer/fieldrules.py`) holds the cleanup rules so `planner`, `form` and the adapters share one definition.

Four findings change the shape of the work and are not in CONTEXT.md: (a) the UL symbol has `ki_locked ""`, which D-06 would drop unless every `ki_*` name is protected (kicad-cli also adds empty `Description` / `Datasheet` fields, which must stay); (b) the Phase 4 D-12 Manufacturer/MPN renames are **not** shown in the preview today, so "the same as a rename" needs a new preview section, not a reuse; (c) `test_fields_exact_manufacturer_kept` asserts the exact behaviour D-08 reverses and must be re-baselined; (d) the generic `intake.ignored_members` note is already in `package.issues` before any adapter runs, so D-16 requires `detect_candidate` to swap that one Issue when the winning adapter supplies a folder summary.

**Primary recommendation:** Build in this order: shared rules module + `remove_property_edit` + `Package.markers` (no behaviour change) -> adapters + registry + D-16 swap -> planner cleanup + `field_changes` + preview section + form defaults (the only step that re-baselines existing tests) -> suggest tables + `part_info` hints -> in-memory synthetic fixtures (`tests/vendorfixtures.py`) with install / kicad-cli / real-sample tests -> `.gitignore`.

## Architectural Responsibility Map

This is a single-process desktop app, so "tiers" are the existing layers (CONVENTIONS/ARCHITECTURE: services are Qt-free, widgets own layout).

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Bounded read of marker members (`part_info.txt`, `license.txt`, `how-to-import.htm`) | Intake service (`importer/package.py`) | — | Only place that still has the zip open; staging stays stage-only (D-07) |
| Vendor scoring / recognition | Adapters (`importer/adapters/*`) | `importer/detect.py` registry | Points-and-threshold style per UL adapter; callers unchanged |
| Bounded sniff of staged symbol heads | Adapters (shared helper in `adapters/base.py`) | — | Staged files are on disk; read-only head read |
| Field cleanup rules (what is volatile, placeholder, alias, standard) | New leaf module `importer/fieldrules.py` | Adapters supply per-vendor `FieldRules` | One definition shared by planner, form and adapters; Qt-free |
| Applying cleanup to the symbol text | Planner (`planner._edit_symbol`) | `kicad_files.remove_property_edit` | Preview and install both consume the plan's final bytes (PREV-07) |
| Showing every dropped/cleaned/renamed field | Preview rows (`importer/preview.py`) from `InstallPlan.field_changes` | `widgets/preview_tree.py` renders unchanged | Plan carries the data; preview is a pure function of plan |
| Form defaults mirror (cleaned Description, part_info fallbacks) | `importer/form.py::field_defaults` | — | Must equal what the planner writes (existing equivalence test) |
| Naming hints (`PartCategory`, `PS`, `recom`) | `importer/suggest.py` | `PartMeta.category` set by `locate()` | Symbol properties win; hints only fill gaps |
| D-16 folder summary | Winning adapter computes; `detect_candidate` swaps the Issue | `package.py` default note stays for other vendors | `ImportCandidate.ignored` is untouched, so nothing is lost |
| Synthetic fixtures / real-sample tests | `tests/vendorfixtures.py` (in-memory builders) | `tests/zipfixtures.py`, `tests/installfixtures.py` reused | Matches the repo's existing zip-fixture precedent; no binary committed |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`zipfile`, `fnmatch`, `re`, `dataclasses`, `pathlib`) | Python 3.14.4 in `env/` (project minimum 3.10) | Marker reads, glob matching of volatile names, parsing `key=value` | Constraint: stdlib only unless clearly justified [VERIFIED: ./env/Scripts/python.exe --version, this session] |
| PySide6 | 6.12.0 | Existing GUI; no widget change needed (the new preview section reuses `kind="rewrite"` rows) | [VERIFIED: requirements.txt via `cat`, this session] |
| pytest / pytest-qt | 9.1.1 / 4.5.0 | Test runner | [VERIFIED: `pytest --version`, requirements-dev.txt] |
| kicad-cli | 10.0.7 and 9.0.9 installed | `kicad_cli`-marked load checks | [VERIFIED: `kicad-cli.exe version` for both, this session] |

### Supporting
In-repo helpers to reuse (all `Read` this session): `kicad_files.{find_property, set_property_edit, rename_property_edit, property_insert_edit}`, `sexpr.{apply_edits, quote, unquote}`, `naming.{sanitize_name, sanitize_filename}`, `kicad_cli.load_gate`, `tests/zipfixtures.{zip_bytes, make_zip, STEP_BYTES, footprint}`, `tests/installfixtures.{vendor_symbol_lib, vendor_footprint}`, `zipfixtures.write_custom_layout` / `CURRENT_CUSTOM_SYMBOL_LIBS`.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-memory synthetic builders (`tests/vendorfixtures.py`) | Committed small `.zip` binaries or `build_fixtures.py` writing them to disk | Binary zips are opaque in diffs and need a "no vendor bytes" review; `build_fixtures.py` exists for frozen on-disk EOL/BOM traits, which an in-memory builder gets exactly anyway. Recommend in-memory (precedent: `zipfixtures.py`, `installfixtures.py`) |
| New leaf module `fieldrules.py` | Putting rules on each adapter and having the planner look up the adapter by name | A planner import of `detect` would be circular and the layering guard forbids it; rules travel on the candidate instead |
| `Package.markers` captured at open time | Re-opening the zip inside `detect()` | `Package` is documented to hold staged files only; the zip is closed after staging, and re-opening would repeat the hostile-zip checks |

**Installation:** none. No new runtime or dev dependency (`requirements.txt` / `requirements-dev.txt` unchanged).

**Version verification:** no external package is recommended, so no registry lookup applies.

## Package Legitimacy Audit

No external packages are installed by this phase. Packages removed due to SLOP: none. Packages flagged SUS: none. (`pip`/`uv.lock` untouched.)

## Architecture Patterns

### System Architecture Diagram

```
 zip / folder -----> open_package(path, repo_root)                      [package.py]
                       |  prescan (hostile names, caps)  -- unchanged
                       |  stage .kicad_sym/.kicad_mod/.step/.stp/.wrl  -- unchanged (D-07)
                       |  NEW: for ignored members whose basename is in MARKER_NAMES
                       |       read <= MAX_MARKER_BYTES in memory -> Package.markers   (never written)
                       |  generic INFO intake.ignored_members (20 paths + "and N more")
                       v
                Package(names, files, ignored, legacy, issues, markers)
                       |
 detect_candidate(package)                                              [detect.py]
   for adapter in ADAPTERS = [UL, SnapEDA, SamacSys, Loose]:
       adapter.detect(package) -> Detection(vendor, confidence, reasons,
                                            rules?, hints?, ignored_note?)       NEW optional fields
          SnapEDA : markers[how-to-import.htm], head-sniff of staged symbols (SnapEDA_Link ...)
          SamacSys: markers[part_info/license], head-sniff "(generator SamacSys_ECAD_Model)", names
   best = highest confidence (ties: registry order); none -> generic Unknown
   NEW: if best.ignored_note: swap package.issues' intake.ignored_members for it   (D-16)
   locate(package, best) -> ImportCandidate(vendor, symbols[meta], ..., field_rules)   NEW field
        part_meta(symbol, rules) + hints (category; manufacturer/mpn only if symbol lacks them)
                       |
 suggest_library(meta, existing)                                        [suggest.py]
   type: PartCategory table -> Reference map (PS added) ; manufacturer: aliases (+recom)
                       |
 build_plan(candidate, options, layout, tools)                          [planner.py]
   _edit_symbol(work, ref, name, fields, version, rules):
       Footprint/ki_fp_filters (existing) ; role("Manufacturer"/"MPN") with per-vendor aliases (D-12)
       NEW: drop other aliases (D-08), drop volatile (D-05), drop placeholder vendor-only (D-06),
            collapse Description (D-07)  -> edits + FieldChange list
   -> InstallPlan(..., field_changes)                                   NEW field
                       |
        +--------------+----------------+
        v                               v
 preview_sections(plan,...)        apply_plan(plan)  (writes plan.ops bytes; unchanged)
   NEW "Field changes" section
```

### Recommended Project Structure
```
kicad_lib_manager/importer/
├── fieldrules.py            # NEW leaf (imports nothing): FieldRules, GENERIC_RULES, STANDARD_FIELDS,
│                            #   is_placeholder(), clean_description(), is_volatile()
├── package.py               # + MAX_MARKER_BYTES, MAX_MARKERS, MARKER_NAMES, Package.markers, marker reads
├── candidate.py             # + PartMeta.category, + ImportCandidate.field_rules (defaults)
├── plan.py                  # + FieldChange dataclass, InstallPlan.field_changes (default ())
├── adapters/
│   ├── base.py              # Detection gains rules/hints/ignored_note; part_meta(symbol, rules); marker helpers
│   ├── snapeda.py           # NEW SnapEDAAdapter + SNAPEDA_RULES
│   └── samacsys.py          # NEW SamacSysAdapter + SAMACSYS_RULES + parse_part_info + folder_summary
├── detect.py                # ADAPTERS = [UL, SnapEDA, SamacSys, Loose]; D-16 issue swap
├── planner.py               # _edit_symbol cleanup, MPN fallback = meta.mpn, field_changes
├── preview.py               # + "Field changes" section (kind="rewrite" rows)
├── form.py                  # field_defaults: cleaned Description (+ part_info fallbacks)
└── suggest.py               # PS, recom/recompower, PART_CATEGORY_TYPE, type_choice(reference, category)
kicad_lib_manager/kicad_files.py   # + remove_property_edit
tests/
├── vendorfixtures.py        # NEW in-memory synthetic SnapEDA / SamacSys zips + Custom layout helper
├── test_vendorfixtures.py   # self-checks (parse with kicad_files; originality guard vs real zips)
├── test_snapeda_adapter.py, test_samacsys_adapter.py, test_field_cleanup.py,
├── test_vendor_install.py   # synthetic Custom/, apply_plan, verify, kicad_cli load check
└── test_real_vendor_samples.py   # skipif zip absent (D-02)
```

### Pattern 1: Points-and-threshold adapter (follow the UL adapter)
**What:** sum points per marker, claim at a threshold, confidence = points / 10 (capped at 1.0).
**Existing style (quote):** `UL_CLAIM_POINTS = 5` ... `if points < UL_CLAIM_POINTS: return None` ... `return Detection(self.name, points / 10, tuple(reasons))` [VERIFIED: kicad_lib_manager/importer/adapters/ultralibrarian.py:8, 34-36].
**Registry (quote):** `ADAPTERS: list[Adapter] = [UltraLibrarianAdapter(), LooseAdapter()]` [VERIFIED: kicad_lib_manager/importer/detect.py:12]. Append the new adapters before `LooseAdapter()` so a SnapEDA/SamacSys folder (Loose scores 0.3) is still claimed by its vendor; ties stay in registry order.

**Recommended weights (all thresholds 5; confidence = min(points, 10) / 10):**

| Adapter | Marker | Points | Source of the marker |
|---------|--------|--------|----------------------|
| SnapEDA | symbol property named `SnapEDA_Link`, `SNAPEDA_PN` or `SNAPEDA_PACKAGE_ID` (case-insensitive raw search in a bounded head of a staged `.kicad_sym`) | 5 | sample: `SnapEDA_Link`, `SNAPEDA_PN` [VERIFIED: sample]; `SNAPEDA_PACKAGE_ID` seen in an existing `Custom/` SnapEDA symbol [VERIFIED: grep of Custom/Symbols] |
| SnapEDA | `snapeda.com` anywhere in that symbol head | 2 | sample: `Check_prices` / `SnapEDA_Link` URLs |
| SnapEDA | member named `how-to-import.htm` (casefold basename) | 2 | sample |
| SnapEDA | that member's bounded text contains `snapeda.com` | 3 | sample: meta refresh + link to the snapeda.com import page |
| SamacSys | `(generator SamacSys_ECAD_Model)` in the head of a staged symbol | 5 | sample first line |
| SamacSys | `part_info.txt` parses to both `Manufacturer` and `PartNumber` keys (present but unparseable: 1) | 3 | sample |
| SamacSys | `license.txt` text contains `samacsys` (casefold) | 2 | sample |
| SamacSys | `version.bin` at the zip/folder root | 1 | sample |
| SamacSys | a `KiCad` folder segment beside >= 2 sibling folders from a known other-CAD name set | 1 | sample has 25 such folders |
| SamacSys | zip/folder stem starts with `lib_` (casefold) | 1 | sample `LIB_RS3-1212S_H3.zip` |

Outcomes: real SnapEDA zip = 5+2+2+3 = 12 -> 1.0; renamed two-file SnapEDA zip = 7 -> 0.7 (recognised, as D-14 requires); real SamacSys zip = 5+3+2+1+1+1 = 13 -> 1.0; a zip holding only `part_info.txt` + `license.txt` = 5 -> 0.5 (claimed). A UL zip scores 0 on both, a generic zip stays `Unknown`. Do not gate SamacSys on a minimum number of other-CAD folders: the owner's sample has 25, but a download for a single CAD tool may carry fewer [ASSUMED] - keep that marker at 1 point.

### Pattern 2: Bounded marker reads into `Package.markers`
**Why:** `Package` today exposes only `names`, `files` (staged), `ignored`, `legacy`, `issues` [VERIFIED: package.py:90-94], and the zip is closed once `_stage_zip` returns, so `detect()` cannot read `part_info.txt` or `license.txt` afterwards. `how-to-import.htm`, `part_info.txt` and `license.txt` all land in `package.ignored` today.

**Recommended addition (constants beside the existing caps at package.py:17-26):**
```python
# Source: new code; style follows package.py:17-26 (module-level caps read at call time)
MAX_MARKER_BYTES = 64 * 1024          # one marker member (real ones are 194, 294 and 445 bytes)
MAX_MARKERS = 16                      # members kept per package
MARKER_NAMES = frozenset({"part_info.txt", "license.txt", "how-to-import.htm", "how-to-import.html"})
# Package: markers: dict[str, bytes] = field(default_factory=dict)   # member name -> bounded bytes
```
Capture rules: only members classified `ignored`, not junk (`_is_junk_name`), basename casefold in `MARKER_NAMES`; read with `src.read(MAX_MARKER_BYTES + 1)` inside the existing `_READ_ERRORS` tuple handling; add the real bytes read to `budget.actual`; an over-cap or unreadable member is skipped with one INFO `intake.marker_skipped` (D-13: never a refusal). Do it inside the existing `with ExitStack()` block of `_stage_zip` (the outer and any nested zip are still open there) and in `_open_folder` after the walk (plain `open(path, "rb")`, links already excluded). A manually built `Package(...)` (several tests do this) has an empty `markers`, so adapters must treat missing markers as "no points", never as an error.

**Staged-symbol content markers** need no new storage: staged files are on disk and `PackageFile.path` is readable. Add one helper in `adapters/base.py`:
```python
SNIFF_BYTES = 64 * 1024     # head of a staged .kicad_sym; SnapEDA props start ~3 KiB in, the generator is on line 1
SNIFF_FILES = 8             # at most this many staged symbols are sniffed
def read_head(pf: PackageFile, limit: int = SNIFF_BYTES) -> bytes:   # b"" on OSError, never raises
def marker_text(package: Package, basename: str) -> str | None:       # decode(errors="replace") of the shallowest match
```
Raw `bytes.lower()` substring tests are enough (no parse, no node ceiling needed), so the head read is far below `MAX_KICAD_TEXT_BYTES` (8 MiB) [VERIFIED: package.py:25].

### Pattern 3: Field cleanup lives in the planner, rules travel on the candidate
**Decision:** put the *rules* in `importer/fieldrules.py` (data + pure predicates), put the *application* in `planner._edit_symbol`, and carry the *result* on `InstallPlan.field_changes`. Rationale: `_edit_symbol` already computes every property edit from final values ("Every property receives at most one edit") and runs on the post-kicad-cli text, preview and `apply_plan` both consume the plan's bytes, and an adapter hook would run before kicad-cli normalisation and could not show the change in the plan.

```python
# Source: new code (leaf module, imports nothing -> add "importer.fieldrules": set() to the layering ALLOWED map)
@dataclass(frozen=True)
class FieldRules:
    volatile: tuple[str, ...] = GENERIC_VOLATILE        # casefolded fnmatch patterns
    manufacturer_aliases: tuple[str, ...] = MANUFACTURER_FIELDS
    mpn_aliases: tuple[str, ...] = MPN_FIELDS
GENERIC_RULES = FieldRules()
```
- `Detection.rules: FieldRules = GENERIC_RULES`, `locate()` copies it to `ImportCandidate.field_rules` (default `GENERIC_RULES`), the planner reads `candidate.field_rules`. UL, Loose and Unknown get the generic rules, as D-09 says.
- Per-vendor lists: SnapEDA volatile = `price`, `availability`, `check_prices` (+ `purchase-url`, see Open Question 2); mpn_aliases = `MPN_FIELDS + ("SNAPEDA_PN",)`. SamacSys volatile = `*price/stock`; aliases already present in base (`Manufacturer_Name`, `Manufacturer_Part_Number`).
- `MANUFACTURER_FIELDS` / `MPN_FIELDS` / `DESCRIPTION_FIELDS` are the existing alias tuples [VERIFIED: base.py:29-31, quoted below].

**Order inside `_edit_symbol` (each property gets at most one edit):**
1. Existing: `put("Footprint")`, `put("ki_fp_filters")`, `role("Manufacturer", ...)`, `role("MPN", ...)` [VERIFIED: planner.py:179-183]. Pass the vendor's alias tuples; make `role()` return its target and the aliases it did not choose.
2. D-08: every alias of the role other than the chosen target (case-sensitive exact names, as `find_property` is exact) -> drop, reason `duplicate`.
3. D-05: any other direct property whose casefolded name matches the volatile patterns -> drop, reason `volatile`.
4. D-06: any other direct property that is not protected and whose `value.strip().casefold()` is in `{"", "none", "n/a"}` -> drop, reason `placeholder`.
5. D-07: for `Description` / `ki_description`, if `" ".join(value.split()) != value` and the caller did not override -> `set_property_edit`, change `clean`.

**Protected from steps 3-4:** `Reference`, `Value`, `Footprint`, `Datasheet`, `Description`, **every name starting with `ki_` (casefold)**, and the role targets `Manufacturer` / `MPN`. This is wider than D-06's list on purpose: the UL sample carries `ki_locked ""` [VERIFIED: sample, property list: Reference, Value, Footprint, Datasheet, ki_keywords, ki_locked, ki_fp_filters], the repo's own pitfalls note says "`ki_keywords`, `ki_description`, `ki_locked`, `ki_fp_filters` are reserved names" [CITED: .planning/research/PITFALLS.md:141], and kicad-cli adds empty `Description` / `Datasheet` properties when normalising [VERIFIED: probe this session, see Common Pitfalls 1]. Without this, D-06 would silently strip `ki_locked` from every UL part.

**New edit helper** (kicad_files.py, beside `rename_property_edit` at line 299): `remove_property_edit(text, prop) -> Edit` that deletes the node span plus the preceding gap back to the previous token (`eol + indent` or a single space). `apply_edits` raises `ValueError` on overlapping edits [VERIFIED: sexpr.py apply_edits], and `_loaded_text` re-parses the edited text, so a wrong span fails loudly in tests instead of corrupting a library.

**Plan data and preview:**
```python
# Source: new code in plan.py (frozen, defaulted at the END of InstallPlan so existing InstallPlan(**values) test helpers keep working)
@dataclass(frozen=True)
class FieldChange:
    symbol: str     # final symbol name
    action: str     # "drop" | "clean" | "rename"
    field: str      # property name (the old name for a rename)
    old: str = ""   # value before ("" for rename)
    new: str = ""   # value after ("" for drop; the new property name for a rename)
    reason: str = ""  # "volatile" | "placeholder" | "duplicate" | "whitespace" | "alias"
```
Preview: a new section `"Field changes"` inserted after `"Path rewrites"`, hidden when empty, rows `kind="rewrite"` (so `preview_tree` already gives the detail column the mono font, preview_tree.py:99-100 shows no other kind-specific code needed). Row text e.g. `Drop Price` / detail `None -> (removed)`; `Clean Description` / detail with the old value collapsed to one line and truncated; `Rename MF` / detail `-> Manufacturer`. Include the D-12 renames here: they are NOT surfaced today (probe: the SamacSys and SnapEDA previews list only Footprint, Model and ki_fp_filters under "Path rewrites"), so D-09's "the same as a rename" needs them to be rows too.

### Pattern 4: `part_info.txt` hints without changing precedence
`Detection.hints: PartHints | None` (category, manufacturer, mpn) set by the SamacSys adapter; `locate()` builds each `PartMeta` from the symbol first and only then fills gaps: `manufacturer = meta.manufacturer or hints.manufacturer`, `mpn = meta.mpn or hints.mpn` (apply the MPN hint only when the package holds exactly one symbol), `category = hints.category`. **Planner must follow:** today `role("MPN", MPN_FIELDS, fields.mpn, ref.name)` falls back to the symbol name, not `meta.mpn` [VERIFIED: planner.py:183], while `form.field_defaults` returns `mpn=meta.mpn or symbol_name`; once `meta.mpn` can come from `part_info.txt` these diverge, and `test_field_defaults_equivalence` will fail unless the chosen symbol's fallback becomes `meta.mpn or ref.name`.

Parsing (`adapters/samacsys.py::parse_part_info(text) -> dict[str, str]`): `text.splitlines()`, first 100 lines, split on the first `=`, key casefolded and limited to 40 chars, value stripped of control characters and limited to 200 chars, lines without `=` ignored. Keys observed in the sample: `Manufacturer`, `PartNumber`, `PartCategory`, `PackageCategory`, `PinCount`, `Version`, `Released`, `Downloaded`, `3D` [VERIFIED: sample, CRLF `key=value` lines]. Unmapped `PartCategory` values are never used raw as a Type token.

### Pattern 5: D-16 folder summary
The default note is built when the package is opened (`_ignored_issue`, 20 paths then "and N more") [VERIFIED: package.py:39 `_IGNORED_LISTED = 20`, and the INFO text in probe output], before any adapter has run, and the dialog logs `[*package.issues, *outcome.detect_issues]` [VERIFIED: import_dialog.py:1063]. So a SamacSys-only change must replace that Issue in `package.issues` itself: the SamacSys adapter computes `Detection.ignored_note`, and `detect_candidate` does `package.issues[:] = [note if i.code == "intake.ignored_members" else i for i in package.issues]` for the winning detection before `locate()`. Idempotent on a second call; `ImportCandidate.ignored` still gets `tuple(package.ignored)` in `locate()` (base.py:273), so it stays complete.

Algorithm verified against the real sample (simulated this session): base = parent of the `KiCad` folder holding the staged symbol/footprint (`RS3-1212S_H3`); folder names = first path segment below base for each ignored member, in first-appearance order -> 25 folders (not ~30); 5 ignored members are loose (`RS3-1212S_H3.epw`, `part_info.txt`, `How_To_Use_Models.pdf`, `license.txt`, `version.bin`); total ignored = 62. Text: `Not imported: other-CAD folders Altium, OrCAD_Allegro16, Capture, DEHDL, Allegro, CircuitStudio, ... (62 files)` (show the first 6 names). Return `None` (keep the default list) when no `KiCad` base or no folders are found.

### Anti-Patterns to Avoid
- **Reading `part_info.txt` through `PackageFile`/staging:** that writes it to disk and breaks D-07. Memory only.
- **Looking the adapter up by name inside the planner:** circular import and the layering guard forbids it. Carry `field_rules` on the candidate.
- **Cleaning in `part_meta()` only (or in the planner only):** the form default and the planner output must match; do the Description collapse in both through the one `clean_description()` and extend the equivalence test.
- **Trusting kicad-cli output to show D-07:** kicad-cli 10 already trims the SnapEDA Description itself (probe), so D-07 tests must run with `ToolContext()` (no CLI) or a fake runner, not the real binary.
- **Dropping by exact `Price` only:** SamacSys names are `Mouser Price/Stock` / `Arrow Price/Stock`; use casefolded `fnmatch`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Glob match of vendor field names | custom string loops | `fnmatch.fnmatchcase` on casefolded names | Handles `*price/stock`; no regex-injection surface |
| Quoting/escaping a property value | manual string building | `sexpr.quote` / `set_property_edit` | Escapes `\\`, `"`, `\n`, `\r`; part_info text can reach a property |
| Splicing symbol text | string `replace` | `sexpr.Edit` + `apply_edits` (raises on overlap) | Span-exact, byte-preserving (FOUND-04) |
| File-name safety of MPN-derived model name | custom regex | `naming.sanitize_filename` | Already turns `RS3-1212S/H3` into `RS3-1212S_H3.stp` [VERIFIED: probe] |
| KiCad load check | parsing the library yourself | `kicad_cli.load_gate(exe, library=, symbol_lib=, footprints=)` | Already version-agnostic: returns `list[Issue]`, pins no format number [VERIFIED: kicad_cli.py:215-281] |
| Zip fixtures | writing zips to the repo | `zipfixtures.zip_bytes` / `make_zip` into `tmp_path` | Existing precedent; deterministic content |
| Synthetic `Custom/` | copying the real tree | `zipfixtures.write_custom_layout(root, CURRENT_CUSTOM_SYMBOL_LIBS, CURRENT_CUSTOM_FOOTPRINT_LIBS)` | Independent of the owner's dirty working tree (D-03) |
| Parsing legacy `.lib`/`.dcm`/`.mod` | any parser | nothing | Ignored by design (D-10) |

**Key insight:** every hard part (escaping, span edits, hostile-zip caps, CLI gate) already exists. The new code is data (rules, tables, marker lists), one edit helper, and glue.

## Runtime State Inventory

Not a rename/refactor/migration phase. Omitted. (One related note: an already-installed SnapEDA part in `Custom/` that is re-imported will now render a *different* block than the stored one - cleaned fields - so INST-09 "same package twice changes nothing" still holds for the new behaviour, but re-importing a part installed before Phase 7 shows a symbol conflict. Expected; `Custom/` symbols are never auto-migrated, META2-02.)

## Common Pitfalls

### Pitfall 1: D-06 silently strips `ki_locked` and kicad-cli's added empty fields
**What goes wrong:** the UL symbol has `ki_locked ""`; kicad-cli (10.0.7) turns UL's 7 properties into 8 by adding an empty `Description`, and adds an empty `Datasheet` to the SnapEDA symbol [VERIFIED: probe this session]. A literal "empty -> drop unless in the CONTEXT list" rule removes `ki_locked`.
**Why:** D-06's standard list omits `ki_locked`; the cleanup runs on the post-normalisation text.
**How to avoid:** protect `Reference`, `Value`, `Footprint`, `Datasheet`, `Description`, every `ki_*`, plus the `Manufacturer`/`MPN` role targets. Add a test that the UL sample's property name list is unchanged by the cleanup.
**Warning signs:** UL tracer diff shows `ki_locked` missing.

### Pitfall 2: D-08 breaks a currently-passing test
`tests/test_install_plan.py::test_fields_exact_manufacturer_kept` builds `props={"Manufacturer": "Exact Co", "MANUFACTURER": "Other Co"}` and asserts `names.count("MANUFACTURER") == 1` and the value `Other Co` survives [VERIFIED: test_install_plan.py:875-883]. D-08 deletes the case twin. Re-baseline to `count == 0` and add the drop to the expected `field_changes`.

### Pitfall 3: preview/form drift on Description
`form.field_defaults` returns `description=meta.description` [VERIFIED: form.py field_defaults body]. If the planner collapses whitespace but `meta.description` keeps the raw SnapEDA text (`"\n    ...Type C USB 2.0 Connector\n..."`), the dialog edit box shows text the plan will not write. Clean in `part_meta()` (via `clean_description`) and in the planner, and add a `snapeda`-shaped case to `test_field_defaults_equivalence` (the existing cases are `ul`, `aliases`, `inferred`, `renamed`).

### Pitfall 4: placeholder values count as a manufacturer
`_first()` returns the first truthy value and `role()` picks `next(p.value for p in present if p.value)` [VERIFIED: base.py:52-57, planner.py:159]. A vendor `MF "N/A"` would become `Manufacturer = N/A` and feed `manufacturer_token`. Make both treat `is_placeholder(value)` as absent so inference runs.

### Pitfall 5: `detect()` runs for every adapter and must never raise
`detect_candidate` calls `adapter.detect(package)` unguarded [VERIFIED: detect.py:25-28], so an exception becomes "Import step failed". All marker helpers must be total (`b""`/`None` on error), decode with `errors="replace"`, and handle a hand-built `Package` with no `markers` (tests build these, e.g. `test_ul_folder_beats_loose`).

### Pitfall 6: layering guard rejects unregistered modules
`tests/test_importer_layering.py` keeps an `ALLOWED` map; every importer module must be registered and its relative imports must resolve into its entry [VERIFIED: test_importer_layering.py:11-17, 33-]. Register `importer.fieldrules` (`set()`), `importer.adapters.snapeda`, `importer.adapters.samacsys` (`models`, `importer.package`, `importer.adapters.base`, `importer.fieldrules`), and widen `importer.candidate`, `importer.adapters.base`, `importer.detect`, `importer.planner`, `importer.form` as needed. Keep zip bulk extraction (`extract`, `extractall`) out of any new code.

### Pitfall 7: `verify.pin_pad_mismatch` on SnapEDA's `None` pads
Installing the real SnapEDA sample yields `WARNING verify.pin_pad_mismatch ... pads with no pin: None` (its two mounting holes are `(pad None np_thru_hole ...)`); `footprint_pad_numbers` ignores only empty numbers [VERIFIED: verify.py:184-192, install probe]. Not required by the success criteria (only the no-model warning is). See Open Question 1.

### Pitfall 8: pre-existing red tests will mask regressions
Baseline on this branch before any change: **21 failed, 1799 passed, 5 skipped in 340 s** (`pytest -q -p no:cacheprovider`), all from the dirty `Custom/` UAT install or KiCad 10's 20251024 format [VERIFIED: full run this session]. Failing ids: `test_commit_plan::test_build_from_real_ul_plan`; `test_import_dialog::{test_preview_sections_follow_plan_ops, test_tracer_ul_import_end_to_end}`; `test_import_preview::test_rows_reimport_into_the_real_custom_library`; `test_install_apply::{test_rollback_fail_on_nth_write[existing-1..3], test_source_changed_at_apply, test_source_gone_at_apply, test_stale_plan_ul_target_edited_during_gate, test_success_touched_order}`; `test_install_e2e::{test_cli_second_install_is_noop, test_cli_version_scenarios[new_library_gets_cli_header], test_cli_version_scenarios[older_incoming_is_normalised], test_sc4_fail_on_each_write[3], test_ul_symbol_added_others_identical}`; `test_install_plan::{test_library_real_cli_new_header, test_model_changed_after_plan_is_refused_by_apply, test_noop_second_plan_after_normalised_apply, test_version_real_cli_into_20241209}`; `test_kicad_cli::test_real_cli_upgrades_ul_symbol_deterministically`. Verification must compare against this set, not against "all green".

### Pitfall 9: kicad-cli rewrites the Description itself
The real CLI output for the SnapEDA symbol already has `Description` = the trimmed text [VERIFIED: probe]. A D-07 test that uses `real_tools` would pass without the new code. Run the cleanup tests with `ToolContext()`.

## Code Examples

### Existing verbatim values the new code builds on
```python
# kicad_lib_manager/importer/adapters/base.py:29-31 [VERIFIED]
MANUFACTURER_FIELDS = ("Manufacturer", "MF", "MANUFACTURER", "Manufacturer_Name")
MPN_FIELDS = ("MPN", "MP", "Manufacturer_Part_Number", "MANUFACTURER_PART_NUMBER")
DESCRIPTION_FIELDS = ("Description", "ki_description")

# kicad_lib_manager/importer/adapters/base.py:34-38 [VERIFIED]
@dataclass(frozen=True)
class Detection:
    vendor: str
    confidence: float
    reasons: tuple[str, ...] = ()

# kicad_lib_manager/importer/package.py:28-34 [VERIFIED]
STAGE_KINDS = {".kicad_sym": "symbol", ".kicad_mod": "footprint", ".step": "model", ".stp": "model", ".wrl": "model"}
```

### SnapEDA adapter skeleton
```python
# Source: new code; mirrors adapters/ultralibrarian.py:15-36
SNAPEDA_CLAIM_POINTS = 5
_PROP_MARKERS = (b"snapeda_link", b"snapeda_pn", b"snapeda_package_id")

class SnapEDAAdapter:
    name = "SnapEDA"

    def detect(self, package: Package) -> Detection | None:
        points, reasons = 0, []
        heads = [read_head(pf).lower() for pf in package.files if pf.kind == "symbol"][:SNIFF_FILES]
        if any(m in head for head in heads for m in _PROP_MARKERS):
            points += 5; reasons.append("SnapEDA_Link / SNAPEDA_PN symbol property")
        if any(b"snapeda.com" in head for head in heads):
            points += 2; reasons.append("snapeda.com URL in symbol")
        how_to = marker_text(package, "how-to-import.htm")
        if how_to is not None:
            points += 2; reasons.append("how-to-import.htm")
            if "snapeda.com" in how_to.casefold():
                points += 3; reasons.append("how-to-import.htm points to snapeda.com")
        if points < SNAPEDA_CLAIM_POINTS:
            return None
        return Detection(self.name, min(points, 10) / 10, tuple(reasons), rules=SNAPEDA_RULES)
```

### `suggest.py` table edits (D-11, D-12)
```python
# Source: new code. REFERENCE_TYPE gains "PS": "PowerSupply" [existing dict: suggest.py:23-46, no "PS" key today]
# MANUFACTURER_ALIASES gains "recom": "RECOM", "recompower": "RECOM" [existing dict: suggest.py:65-84]
PART_CATEGORY_TYPE = {            # key = casefolded letters+digits of PartCategory
    "powersupply": "PowerSupply",           # [VERIFIED: sample "Power Supply"]
    "integratedcircuit": "IC", "integratedcircuits": "IC", "ic": "IC",           # [ASSUMED strings]
    "connector": "Connector", "connectors": "Connector",
    "capacitor": "Capacitor", "capacitors": "Capacitor",
    "resistor": "Resistor", "resistors": "Resistor",
    "inductor": "Inductor", "inductors": "Inductor",
    "ferritebead": "Ferrite", "ferritebeads": "Ferrite", "ferrite": "Ferrite",
    "diode": "Diode", "diodes": "Diode",
    "transistor": "Transistor", "transistors": "Transistor",
    "led": "LED", "leds": "LED",
    "crystal": "Oscillator", "crystals": "Oscillator", "oscillator": "Oscillator", "oscillators": "Oscillator",
    "fuse": "Fuse", "fuses": "Fuse",
    "switch": "Switch", "switches": "Switch",
    "relay": "Relay", "relays": "Relay",
    "battery": "Battery", "batteries": "Battery",
}
# type_choice(reference, category="") -> TokenChoice(token, "part_info", True) when the category maps,
# else the existing Reference lookup. _subcategory() must treat source "part_info" like "reference"
# (suggest.py:262 only restricts libraries for source == "reference").
```
Prototype check (applying only the `PS` and `recom`/`recompower` edits in memory against the real `Custom/` library list): `PowerSupply_SubCategory_RECOM`, Type `PowerSupply` confident, Manufacturer `RECOM` via `name_alias`, SubCategory placeholder, `low` confidence, no alternatives [VERIFIED: probe this session]. So for the sample the Reference map alone gives the expected name; `PartCategory` matters when the Reference is unmapped.

### Synthetic fixture layout each builder must reproduce
SnapEDA zip (3 members, all at the zip root): `<Sym>.kicad_sym` (LF; starts with one blank line; `(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)`; every property carries `(id N)` and `(justify bottom) hide` effects; no `Datasheet` property); `<VendorPrefix>_<Sym>.kicad_mod` (`(footprint <unquoted name> (layer F.Cu) (tedit 6ADB0C96)`, no model, two pads literally named `None` with type `np_thru_hole`); `how-to-import.htm` (own text: meta-refresh + link to `https://www.snapeda.com/about/import/`). Symbol properties, in order, with the same *names* as the sample [VERIFIED: sample]: `Reference`, `Value`, `Footprint` (`<Sym>:<FP>`), `MF`, `MAXIMUM_PACKAGE_HEIGHT`, `Package` ("None"), `Price` ("None"), `Check_prices` (URL), `STANDARD`, `PARTREV`, `SnapEDA_Link` (URL), `MP`, `Description` (`"\n   \n      <text>\n   \n"` escapes), `MANUFACTURER` (short form), `Availability`, `SNAPEDA_PN`. Use an invented part, invented URLs on a reserved domain for the price links, invented pins/rectangle. A second variant adds a tiny `.step` to cover "any 3D model".

SamacSys zip (`LIB_<Part>.zip`): root `license.txt` (CRLF, your own sentence that contains the word SamacSys - do not reuse the vendor text), root `version.bin` (7 arbitrary bytes), `<Part>/part_info.txt` (CRLF `key=value`, keys listed above, invented values, `PartCategory=Power Supply`), `<Part>/How_To_Use_Models.pdf` (tiny placeholder bytes), `<Part>/<Part>.epw`, ~12 other-CAD folders each with one tiny placeholder file, including names with spaces and punctuation (`DesignSpark PCB`, `SOLIDWORKS PCB`, `TARGET 3001!`, nested `Proteus/8.8 or earlier/Readme.html`, deep `DEHDL/<p>/sym_1/symbol.css`) to exercise hostile-name checks and the D-16 grouping, `<Part>/CADSTAR/<Part>.lib` (a legacy file outside the KiCad folder), `<Part>/KiCad/{<Part>.kicad_sym, <FP>.kicad_mod, <Part>.lib, <Part>.dcm, <Part>.mod}` and `<Part>/3D/<Part>.stp`. Symbol: CRLF, `(kicad_symbol_lib (version 20211014) (generator SamacSys_ECAD_Model)` (generator is a bare atom), `Reference` "PS", `Footprint` = bare `<FP>`, properties named `ki_description`, `Height` (""), `Manufacturer_Name`, `Manufacturer_Part_Number` (with a `/`), `Mouser Part Number`, `Mouser Price/Stock`, `Arrow Part Number` (""), `Arrow Price/Stock` (""). Footprint: CRLF, `(module "<FP>" (layer F.Cu)`, bare `(model <Part>.stp (at (xyz ...)) (scale ...) (rotate ...))`. STEP: `zipfixtures.STEP_BYTES` style with a valid `ISO-10303-21;` header, a few lines only.

Originality guard (cheap, enforces D-01): `test_vendorfixtures.py` asserts that, when a real sample is present, no member of the synthetic zip has the same SHA-256 as any member of it (skip otherwise), and that every synthetic member is under 4 KiB.

### kicad-cli load check (D-04)
```python
# Source: pattern of tests/test_install_e2e.py:465-480 [VERIFIED]; load_gate returns list[Issue], pins no version
@pytest.mark.kicad_cli
def test_vendor_installs_load_in_kicad(vendor_case, tmp_path, kicad_cli_path):
    layout, library, footprint_names = _install(vendor_case, tmp_path)        # synthetic Custom/, ToolContext() or real tools
    pretty = layout.footprints_dir / f"{library}.pretty"
    footprints = [(n, (pretty / f"{n}.kicad_mod").read_bytes()) for n in footprint_names]
    symbol_lib = (layout.symbols_dir / f"{library}.kicad_sym").read_bytes()
    issues = kicad_cli.load_gate(kicad_cli_path, library=library, symbol_lib=symbol_lib, footprints=footprints)
    assert [i for i in issues if i.severity is Severity.ERROR] == [], issues   # no format number anywhere
```
Real-sample variant: same body, parametrised on the two real zips with `pytest.mark.skipif(not path.exists(), reason="local sample downloaded_examples/<name> not present")`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Unknown-vendor generic path for both samples | Recognised vendors with cleanup | This phase | `intake.unknown_vendor` disappears for them; vendor label flows to `Import-Vendor` |
| kicad-cli 9 writes 20241209 | kicad-cli 10.0.7 writes 20251024 | KiCad 10 | D-04 must not pin; baseline already red (Pitfall 8) |

**Deprecated/outdated:** `.planning/codebase/TESTING.md` says no tests exist (written 2026-10-18); the suite now has ~1,800 tests. Use `tests/` as the source of truth.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `PartCategory` strings other than "Power Supply" (Integrated Circuit, Connector, Capacitor, ...) are guesses at SamacSys / CSE wording. Web searches this session returned no document listing the values (no observation, not a declared absence) | Code Examples (`PART_CATEGORY_TYPE`) | A category silently falls through to the Reference map (the designed fallback). Low impact, but the Type token is costly to rename once a library exists (D-11), so the owner should confirm each row |
| A2 | A SnapEDA zip that includes a 3D model ships a `.step` / `.stp` member; the layout is unknown (the only sample has none) | Pattern 1, fixtures | `locate()` finds models by extension anywhere, so recognition is unaffected; only the synthetic "with model" fixture's layout is a guess |
| A3 | A CSE download for a single CAD tool may carry fewer other-CAD folders than the 25 in the sample | Pattern 1 | Why the folder marker is only 1 point; if wrong, a stronger weight would also be safe |
| A4 | `Purchase-URL` should be a SnapEDA volatile field (it is a tracking link seen in 5 of the owner's 7 existing SnapEDA symbols [VERIFIED: grep of Custom/Symbols]); it is not in D-05's list | Pattern 3 | If the owner wants it kept it stays as a "kept link" - no correctness risk, a preview-visible choice |
| A5 | Generic volatile names: exact `price`, `prices`, `stock`, `availability`, `check_prices`, glob `*price/stock` | Pattern 3 | Too narrow = a stale price field survives for loose/UL packages; too broad (e.g. `*stock*`) could drop a stock-code identifier. Preview shows every drop |
| A6 | 64 KiB per marker, 16 markers, 64 KiB x 8 symbol heads are adequate (real members are 194-445 bytes; the symbol markers sit in the first ~3 KiB) | Pattern 2 | A larger legitimate file would only lose its detection points, never fail the import |

## Open Questions

1. **Spurious `verify.pin_pad_mismatch` for SnapEDA `None` pads (Pitfall 7).**
   - What we know: the real sample installs with `WARNING verify.pin_pad_mismatch ... pads with no pin: None`; `footprint_pad_numbers` skips only empty numbers.
   - What's unclear: whether the owner wants this fixed in Phase 7 (touches Phase 4 `verify.py`), since success criteria do not require a clean install.
   - Recommendation: add a small task: ignore `np_thru_hole` pads (or the literal number `None`) in `footprint_pad_numbers`, with a test; otherwise note it as known and leave.
2. **`Purchase-URL` (A4).** Recommendation: include it in `SNAPEDA_RULES.volatile`, flagged in the plan for owner confirmation.
3. **Show D-12 renames in "Field changes"?** Recommendation: yes (they are invisible today and D-09 says changes show "the same as a rename"). Cost: one row per renamed alias.
4. **Swapping `intake.ignored_members` inside `package.issues` (Pattern 5)** mutates a `Package` from `detect_candidate`. Alternative (change `open_package` to summarise structurally) would also change other vendors, which D-16 forbids. Recommendation: the swap, documented in the `detect_candidate` docstring.
5. **Re-importing a pre-Phase-7 SnapEDA part** produces a symbol conflict (cleaned block differs). Expected; no action unless the owner objects.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv `env/` | all code and tests | yes | 3.14.4 | — |
| pytest, pytest-qt, PySide6 (offscreen) | tests | yes | 9.1.1, 4.5.0, 6.12.0 | — |
| kicad-cli (newest) | D-04 `kicad_cli` tests | yes | 10.0.7 (`C:\Program Files\KiCad\10.0\bin`) | tests skip via `kicad_cli_path` fixture |
| kicad-cli 9 | optional cross-check of KiCad 9 load | yes | 9.0.9 | — |
| Real samples | D-02 tests | yes (both present, untracked) | — | per-test skip with reason |
| git | `.gitignore` check | yes | — | — |

**Missing dependencies with no fallback:** none.

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json`.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-qt 4.5.0 (offscreen) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, markers incl. `kicad_cli`, `addopts = "-ra --strict-markers"`) [VERIFIED: pyproject.toml, this session] |
| Quick run command | `.\env\Scripts\python.exe -m pytest -p no:cacheprovider -q tests/test_adapters.py tests/test_naming_suggest.py tests/test_import_form.py tests/test_import_preview.py tests/test_install_plan.py` plus the new test files |
| Full suite command | `.\env\Scripts\python.exe -m pytest -p no:cacheprovider -q` (about 340 s; baseline 21 failed, see Pitfall 8) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTK-03 | Synthetic SnapEDA zip -> vendor `SnapEDA`, confidence >= 0.7, no `intake.unknown_vendor`, `intake.no_model` + `install.no_model` WARNING, renamed two-file variant still recognised | unit | `pytest tests/test_snapeda_adapter.py -q` | Wave 0 |
| INTK-03 | Real SnapEDA zip recognised (skips if absent) | integration | `pytest tests/test_real_vendor_samples.py -q` | Wave 0 |
| INTK-04 | Synthetic SamacSys zip -> vendor `SamacSys`; legacy `.lib/.dcm/.mod` ignored (INFO), `(module ...)` WARNING, model found, 62-style folder summary, `candidate.ignored` complete, staging dir holds only sym/fp/model files | unit | `pytest tests/test_samacsys_adapter.py -q` | Wave 0 |
| INTK-04 | Real SamacSys zip recognised (skips if absent) | integration | `pytest tests/test_real_vendor_samples.py -q` | Wave 0 |
| D-05..D-09 | Drop volatile / placeholder / alias, collapse Description, protected set, `field_changes`, preview section, UL property list unchanged, preview == install bytes | unit | `pytest tests/test_field_cleanup.py tests/test_import_preview.py -q` | Wave 0 |
| D-09 | `field_defaults` equals planner output incl. a SnapEDA-shaped case | unit | `pytest tests/test_import_form.py -q` | extend |
| D-11/D-12 | `PS`, `recom`/`recompower`, category table, source `part_info`, expected `PowerSupply_SubCategory_RECOM` | unit | `pytest tests/test_naming_suggest.py -q` | extend |
| D-13 | marker caps, oversize/unreadable -> INFO not refusal, parse caps, never written | unit | `pytest tests/test_package_zip.py tests/test_samacsys_adapter.py -q` | extend |
| Success crit. 3 | Install each vendor into synthetic `Custom/`: Footprint `<Lib>:<FP>`, model `${CUSTOM_3DMODEL_DIR}/RS3-1212S_H3.stp`-style path, `verify_install` clean | integration | `pytest tests/test_vendor_install.py -q` | Wave 0 |
| D-04 | kicad-cli `load_gate` on installed libs, no version pinned | integration (`kicad_cli`) | `pytest -m kicad_cli tests/test_vendor_install.py -q` | Wave 0 |
| D-01 | Fixtures parse, markers present, originality guard | unit | `pytest tests/test_vendorfixtures.py -q` | Wave 0 |
| D-02 | `.gitignore` rule | manual/scripted | `git check-ignore -v downloaded_examples/LIB_RS3-1212S_H3.zip` and `git ls-files downloaded_examples` | n/a |

### Sampling Rate
- **Per task commit:** the quick run command above plus the new file(s) of that task.
- **Per wave merge:** full suite; failure set must equal the Pitfall 8 baseline minus nothing, plus nothing new.
- **Phase gate:** full suite compared to baseline, `-m kicad_cli` green for the new tests, `git status` shows the two vendor zips ignored.

### Wave 0 Gaps
- [ ] `tests/vendorfixtures.py`, `tests/test_vendorfixtures.py` - synthetic builders + self-checks (D-01)
- [ ] `tests/test_snapeda_adapter.py`, `tests/test_samacsys_adapter.py`, `tests/test_field_cleanup.py`, `tests/test_vendor_install.py`, `tests/test_real_vendor_samples.py`
- [ ] Existing tests that must change with the code: `test_adapters.py` lines 50 and 413 (registry lists), `test_install_plan.py::test_fields_exact_manufacturer_kept` (D-08), `test_import_preview.py` `ORDER` (line 34) and section-name lists, `test_importer_layering.py` `ALLOWED`, `test_import_form.py::test_field_defaults_equivalence` (new case), `test_import_dialog.py` `test_vendor_labels` (optionally add the two new labels)
- Framework install: none needed.

## Security Domain

`security_enforcement` is `true`, ASVS level 1, block on `high`.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | yes | Bounded reads; control-character stripping and length caps on `part_info.txt`; mapped-only Type tokens; `quote()` escaping; `sanitize_name` / `sanitize_filename` |
| V6 Cryptography | no | SHA-256 only for existing integrity checks |
| V12 Files and Resources | yes | Zip hostile-member refusals and caps unchanged (Phase 3 D-05/D-06/D-19); markers are read in memory and never written; staged kinds unchanged |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Oversized or decompression-bomb marker member (`part_info.txt` etc.) | Denial of service | Member already passes `_prescan` (declared size, total, ratio); read `MAX_MARKER_BYTES + 1`, count real bytes against the shared budget, skip with INFO beyond the cap |
| Marker member written to disk / path traversal via marker name | Tampering | Markers are keyed by name but only held as bytes; nothing is created from them; `STAGE_KINDS` unchanged; test that the staging dir lists only `sym_*`, `fp_*`, `model_*` files |
| `part_info.txt` values with quotes, newlines, control characters reaching the symbol, the preview or the commit message | Tampering / Injection | Strip control characters and cap lengths at parse time; values enter symbol text only via `quote()`; MPN -> model file name only via `sanitize_filename`; preview rows are plain `QTreeWidgetItem` text; commit trailer vendor comes from a fixed label and `sanitize_line` |
| `PartCategory` used verbatim to build a library name | Tampering | Only values found in `PART_CATEGORY_TYPE` become a Type token |
| Lookalike package mislabelled as SnapEDA/SamacSys to trigger drops | Tampering (low) | Cleanup only removes fields from the *incoming* symbol, every drop is shown in the preview, nothing is written without the preview |
| Adapter `detect()` raising on hostile text | Denial of service | Total helpers; no regex with nested quantifiers (plain `in` on bytes); decode `errors="replace"` |
| Wrong property-removal span corrupting a library | Tampering | `apply_edits` rejects overlaps; `_loaded_text` re-parses the edited block; install is already transactional with rollback (INST-07) |

## Project Constraints (from CLAUDE.md)

From `./CLAUDE.md` and `./.claude/CLAUDE.md`:
- **Stack:** Python 3.10+ (venv on 3.14), PySide6 6.12, stdlib only otherwise. No new dependency.
- **Platform:** Windows 11 primary, standard CPython (not MSYS2); keep cross-platform branches working. Run tests with `.\env\Scripts\python.exe`.
- **Safety:** no write without a preview first; writes atomic or backed up; git commits need explicit confirmation; the importer never pushes.
- **KiCad output:** must load in KiCad 6+; symbol/footprint names follow `<Type>_<SubCategory>_<Manufacturer>`; `.kicad_sym` / `.pretty` names pair.
- **Conventions:** services return `Issue(severity, code, text)` and never raise for expected failures; codes are namespaced (`intake.*`, `install.*`); services do not import Qt; lower modules never import `main_window`; explicit relative imports; `pathlib.Path` everywhere, `.as_posix()` for table/KiCad paths; type hints with `X | None`; comments explain intent only; new behaviour goes in the package, not the legacy script; keep message literals stable.
- **Data:** the repos are public - never commit vendor symbols, footprints, models or licence text; real vendor zips stay local and ignored (D-01/D-02).
- **Dependencies:** real samples are required before building a vendor format (now satisfied: both present).
- **GSD:** repo edits go through a GSD workflow (`/gsd-execute-phase` for planned work).
- **Research environment rules used here:** vendor zips were read in memory with `python -I`; no extraction; scripts kept outside the repo.

## Sources

### Primary (HIGH confidence)
- Real samples `downloaded_examples/USB4145-03-0170-C_REVA2.zip`, `downloaded_examples/LIB_RS3-1212S_H3.zip`, `downloaded_examples/ul_CSD85301Q2.zip` - member listings, text members, symbol/footprint property and structure facts, read in memory with `zipfile` under `python -I`
- Repo source `Read` this session: `importer/adapters/ultralibrarian.py`, `importer/adapters/base.py`, `importer/package.py`, `importer/suggest.py`, `importer/detect.py`, `importer/planner.py` (lines 154-193 and full pass), `tests/test_install_plan.py` (874-885); plus full reads via shell of `plan.py`, `preview.py`, `form.py`, `candidate.py`, `kicad_cli.py`, `layout.py`, `commit_plan.py`, `verify.py`, `kicad_files.py`, `sexpr.py`, `tests/zipfixtures.py`, `tests/installfixtures.py`, `tests/conftest.py`, `tests/test_adapters.py`, `tests/test_importer_layering.py`
- Live probes this session: current-code behaviour on both samples (detect/suggest/plan/preview/apply, with and without kicad-cli 10.0.7), `kicad_cli.load_gate` on both samples, kicad-cli property rewrite of all three samples, D-16 grouping simulation, `.gitignore` rule in a throwaway repo, full pytest baseline

### Secondary (MEDIUM confidence)
- `.planning/research/PITFALLS.md:141` (reserved `ki_*` field names) and `.planning/phases/07-snapeda-and-samacsys-adapters/07-CONTEXT.md`

### Tertiary (LOW confidence)
- WebSearch for SamacSys `part_info.txt` / `PartCategory` documentation returned nothing relevant (third-party importer tools only); no observation either way, so the category table is `[ASSUMED]` beyond the one sample value

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies; versions read from the venv and requirements files
- Architecture: HIGH - every integration point read, and the key flows probed against the real samples
- Detection weights: MEDIUM - derived from one sample per vendor; thresholds leave headroom (renamed-zip case verified arithmetically, not against a second real download)
- `PartCategory` table: MEDIUM-LOW - one observed value
- Pitfalls: HIGH - each was reproduced or read in code

**Research date:** 2026-10-23
**Valid until:** 2026-11-22 (stable code; re-check only if the importer package changes first)
