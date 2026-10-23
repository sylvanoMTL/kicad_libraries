# Phase 7: SnapEDA and SamacSys Adapters - Context

**Gathered:** 2026-10-23
**Status:** Ready for planning

<domain>
## Phase Boundary

SnapEDA and SamacSys / Component Search Engine zips are recognised as their own vendor. They then import through the same flow as Ultra Librarian packages: intake, plan, preview, install, post-install, commit. The phase adds:

- two adapters in the registry;
- vendor-aware symbol-field cleanup, applied to every vendor;
- SamacSys `part_info.txt` hints for naming;
- licence-safe fixtures with tests.

Requirements: INTK-03, INTK-04.

**Starting point (verified 2026-10-23 against the real samples):** both samples already import through the generic path. Nothing is rejected.
- `USB4145-03-0170-C_REVA2.zip` (SnapEDA) reports `intake.unknown_vendor` and `intake.no_model`.
- `LIB_RS3-1212S_H3.zip` (SamacSys) reports `intake.unknown_vendor`, `intake.legacy_footprint_syntax` (its footprint is `(module "RS3" ...)`) and `intake.legacy_ignored` (`.lib`/`.dcm`/`.mod`, plus `CADSTAR/*.lib`). Its footprint has a bare `(model RS3-1212S_H3.stp ...)`.

So the work is recognition, cleanup and fixtures, not making import possible.

Not in this phase:
- converting KiCad 5 legacy files (FMT2-01, v2);
- migrating existing `Custom/` symbols' `MF`/`MP`/`MANUFACTURER` fields (v2);
- downloading from vendor sites;
- the 3 tests that read the real `Custom/` tree (separate Active item);
- the KiCad 10 CLI format-number test failures (separate concern in STATE.md).

</domain>

<decisions>
## Implementation Decisions

### Carried forward (locked)
- **Registry:** adapters are appended to `ADAPTERS` in `kicad_lib_manager/importer/detect.py`, and callers never change (Phase 3 D-09). A zip with no recognised vendor still imports as generic `Unknown`.
- **Legacy files:** KiCad 5 files beside v6+ files are ignored with one INFO (Phase 3 D-10). The "re-download" rejection applies only per D-11. A `(module ...)` footprint is accepted with WARNING `intake.legacy_footprint_syntax` (Phase 3 D-18).
- **Staging:** intake stages only `.kicad_sym` / `.kicad_mod` / `.step` / `.stp` / `.wrl`. Every other member is listed and never written to disk (Phase 3 D-07). The hostile-zip refusals and size caps of D-05, D-06 and D-19 apply unchanged.
- **Manufacturer and MPN:** the first vendor alias for each role is renamed in place to `Manufacturer` / `MPN` (Phase 4 D-12). Existing `Custom/` symbols are never touched.
- **Default names:** the footprint keeps its vendor name by default and is editable (`RS3`, `GCT_USB4145-03-0170-C_REVA2`). The symbol's Footprint field is always rewritten to `<Lib>:<FP>`, including SnapEDA's `USB4145-03-0170-C_REVA2:GCT_...` and SamacSys's bare `RS3`.
- **3D model:** the model is saved as `<MPN>.<ext>` through `sanitize_name` (Phase 3 D-15), so `RS3-1212S/H3` becomes `RS3-1212S_H3.stp`. The bare vendor model path is stale and is rewritten to `${CUSTOM_3DMODEL_DIR}/...` (Phase 4). With no model, the part installs without one and warns (INTK-08). SnapEDA is the no-model case.
- **Preview and commit:** preview comes before any write, and the preview and the install share one plan (PREV-01..07). The commit trailer `Import-Vendor:` comes from the vendor label (Phase 6).

### Test fixtures & licence
- **D-01: Committed fixtures are synthetic, and the real zips stay local.** Both GitHub repos (`sylvanoMTL/kicad_libraries`, `sylvanoMTL/kicad_custom_library`) are public. SamacSys `license.txt` says: "You will not distribute our models in any form useable as a PCB Library Component". So:
  - The committed fixtures are synthetic zips, written from scratch, that copy each vendor's layout and markers: folder tree, `license.txt` / `part_info.txt` / `version.bin` / `how-to-import.htm`, the generator string, property names, the `(module ...)` footprint syntax, bare model paths, legacy `.lib` / `.dcm` / `.mod` siblings, other-CAD folders, and a tiny STEP with a valid `ISO-10303-21;` header. No vendor geometry or models are copied.
  - The real zips are never committed. — **Reversibility:** one-way — once a vendor zip is pushed to the public repo it cannot be un-published; removing it later needs history rewriting on a public remote.
- **D-02: Real-sample tests run automatically when the zips are present, and git ignores the zips.**
  - Tests look for `downloaded_examples/USB4145-03-0170-C_REVA2.zip` and `downloaded_examples/LIB_RS3-1212S_H3.zip` by name. When a zip is missing, its test skips with a clear reason. There is no env var.
  - `.gitignore` excludes `downloaded_examples/*` except `!downloaded_examples/ul_CSD85301Q2.zip`, which stays tracked.
- **D-03: Install tests target a small synthetic `Custom/` built in `tmp_path`**: a couple of libraries plus `3DModels/`. They must not depend on the owner's working tree. Success criterion 3 ("installs into a copy of `Custom/`") is met with this fixture. The 3 existing tests that read the real tree are not fixed here.
- **D-04: A version-agnostic kicad-cli load check.** A `kicad_cli`-marked test loads each installed SnapEDA and SamacSys library (symbol and footprint) with kicad-cli.
  - It asserts that the load succeeds and never pins a format number, because the installed KiCad 10 CLI writes 20251024.
  - It skips when kicad-cli is absent.
  - It runs on the synthetic fixtures, and also on the real zips when they are present.

### Vendor field cleanup (incoming symbols only)
- **D-05: Drop volatile fields and keep identifiers.**
  - **Dropped** (go stale): price, stock and availability fields and their links. SnapEDA: `Price`, `Availability`, `Check_prices`. SamacSys: `Mouser Price/Stock`, `Arrow Price/Stock`.
  - **Kept** (stay true): distributor part numbers and source links, such as `Mouser Part Number`, `SnapEDA_Link`, `STANDARD`, `PARTREV`, `MAXIMUM_PACKAGE_HEIGHT`.
  - The volatile-field list is defined per adapter. A small generic list (names like `Price`, `Stock`, `Availability`, `*Price/Stock`) applies to UL, loose and unknown packages.
- **D-06: Drop vendor-only fields whose value is empty or a placeholder**, compared case-insensitively after trimming: `""`, `None`, `N/A`. Examples: SnapEDA `Package "None"`, SamacSys `Height ""` and `Arrow Part Number ""`. KiCad standard fields (`Reference`, `Value`, `Footprint`, `Datasheet`, `Description` / `ki_description`, `ki_keywords`, `ki_fp_filters`) are never dropped by this rule. An empty Datasheet stays valid.
- **D-07: Description is trimmed and its whitespace collapsed** for every vendor: leading and trailing whitespace is stripped, and internal runs of spaces and newlines become one space. SnapEDA's `"\n   \n      Type C USB 2.0 Connector\n   \n"` becomes `"Type C USB 2.0 Connector"`. The cleaned text is what the preview shows and edits.
- **D-08: Duplicate Manufacturer/MPN aliases are dropped.** After the D-12 rename, the remaining alias fields for the same role are removed from the incoming symbol, so each role has one source of truth.
  - SnapEDA: `MF` → `Manufacturer` = "Global Connector Technology", and `MANUFACTURER "GCT"` is dropped. `MP` → `MPN`, and `SNAPEDA_PN` is dropped.
  - The alias lists are per adapter, extending `MANUFACTURER_FIELDS` / `MPN_FIELDS` in `importer/adapters/base.py` (for example `SNAPEDA_PN` as a SnapEDA MPN alias).
  - This extends Phase 4 D-12. It still never touches existing `Custom/` symbols.
- **D-09: The rules apply to all vendors.**
  - D-06, D-07 and D-08 run for every package. D-05 uses the winning adapter's volatile-field list, or the generic list.
  - The UL tracer and e2e expectations may change and are re-baselined.
  - Every dropped field and every cleaned value appears in the preview as a planned change, the same as a rename. There is no per-field "keep" toggle in this phase.

### Names & metadata hints
- **D-10: The symbol name and Value keep the vendor form.** `USB4145-03-0170-C_REVA2` stays as both symbol name and Value, and the owner can rename it in the preview. Revision suffixes are not stripped. The `MPN` field already holds the clean `USB4145-03-0170-C`.
- **D-11: SamacSys `part_info.txt` feeds naming.**
  - `PartCategory` maps to a library Type token through a small table, for example `Power Supply`→`PowerSupply`, `Connector`→`Connector`, `Integrated Circuit`→`IC`. The planner or researcher fills in the full table. An unmapped category falls back to the Reference map.
  - `Manufacturer` and `PartNumber` from `part_info.txt` are used only when the symbol lacks them. Symbol properties always win.
  - Also add `PS`→`PowerSupply` to `REFERENCE_TYPE` in `importer/suggest.py`.
  - Expected suggestion for the sample: `PowerSupply_SubCategory_RECOM`. `SubCategory` stays a placeholder that blocks Install until edited, unless token overlap with existing libraries fills it. — **Reversibility:** costly — once a `PowerSupply_*` library exists in `Custom/`, changing the Type token means renaming the `.kicad_sym` / `.pretty` pair, every symbol's Footprint field and the table entries.
- **D-12: Add `recom` / `recompower` → `RECOM` (brand casing) to `MANUFACTURER_ALIASES`.** — **Reversibility:** costly — the same library-rename cost as D-11 applies once a `*_RECOM` library is committed.
- **D-13: `part_info.txt` is read in memory, bounded, and never written.** It is not a staged kind under Phase 3 D-07, so it is read from the zip with a small byte cap (planner picks it, e.g. ≤64 KiB) and parsed as `key=value` lines. Malformed or oversized content is ignored with an INFO or WARNING Issue, never a refusal. The same bounded in-memory read applies to any other marker text used for detection (D-14).

### Detection & vendor label
- **D-14: Recognition uses file names plus content markers.**
  - **Name markers:**
    - SnapEDA: `how-to-import.htm` redirecting to snapeda.com.
    - SamacSys: `LIB_` zip prefix, `license.txt`, `part_info.txt`, `version.bin`, `<Part>/KiCad/` beside many other-CAD folders.
  - **Content markers:**
    - SnapEDA: `SnapEDA_Link` / `SNAPEDA_PN` symbol properties, a snapeda.com URL.
    - SamacSys: `(generator SamacSys_ECAD_Model)`, `SamacSys` in `license.txt`.
  - A renamed SnapEDA zip holding only the two KiCad files is still recognised from its symbol.
  - Marker reads stay within the existing caps (`MAX_KICAD_TEXT_BYTES`, node ceiling) and D-13's bounded read. Scoring follows the UL adapter's points-and-threshold style. Tie-breaking stays registry order.
- **D-15: Vendor labels are `SnapEDA` and `SamacSys`.** They are short, stable, and match the words in the files. They appear in the dialog and in the `Import-Vendor:` commit trailer. There is no distributor suffix and no rebrand naming (SnapMagic, Component Search Engine).
- **D-16: SamacSys's other-CAD members are summarised by folder.** Instead of the 20-paths-plus-"and N more" list, there is one INFO line: `Not imported: other-CAD folders Altium, Allegro, CADSTAR, ... (62 files)`. The full member list stays on the candidate (`ImportCandidate.ignored`), so nothing is lost. Other vendors keep the current list.

### Claude's Discretion
- The detection scoring weights, thresholds and confidence values for both adapters, and how `detect()` gets access to the bounded content markers. The `Package` and `Adapter` protocol may be extended, as long as callers of `detect_candidate` don't change.
- Where the field-cleanup step lives (an adapter hook vs. a planner step), as long as preview and install share one plan.
- The full `PartCategory`→Type table and the generic volatile-field name list.
- How the synthetic fixtures are produced: `tests/fixtures/build_fixtures.py` generating them byte-exactly, or committed small zips with self-checks as in Phase 1.
- The byte cap for marker and `part_info.txt` reads.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and requirements
- `.planning/ROADMAP.md` §"Phase 7: SnapEDA and SamacSys Adapters": goal, the 3 success criteria, and the research flag (now unblocked: both samples are present)
- `.planning/REQUIREMENTS.md`: INTK-03, INTK-04
- `.planning/PROJECT.md`: Constraints (public repos, safety, preview-first), Key Decisions, Out of Scope

### Prior decisions this phase builds on
- `.planning/phases/03-package-intake-and-naming/03-CONTEXT.md`: D-01..D-04 (naming suggestion, placeholder refusal), D-05..D-08 and D-19 (hostile zip and caps), D-07 (stage-only kinds), D-09 (registry and generic vendor), D-10..D-12 (legacy matrix), D-15 (`sanitize_name`), D-18 (`(module ...)` accepted)
- `.planning/phases/04-plan-and-install-core/04-CONTEXT.md`: D-12 (Manufacturer/MPN alias rename in place), model-path staleness rules, kicad-cli normalisation (D-01, D-02)
- `.planning/phases/05-import-ui-and-post-install/05-CONTEXT.md`: preview contract (how planned field changes are shown and edited)

### Vendor format research
- `research_notes/KiCad 10 vendor part import/vendor_formats_and_file_changes.md` Q1: SnapEDA and SamacSys known defects (Footprint field missing the library prefix, models not linked). Written before real samples existed; the samples now override its "unverified" notes.
- `reports/KiCad 10 vendor part import.md`: consolidated research report

### Real samples (local only, never commit — D-01/D-02)
- `downloaded_examples/USB4145-03-0170-C_REVA2.zip`: SnapEDA. Files: `USB4145-03-0170-C_REVA2.kicad_sym` (version 20211014, generator kicad_symbol_editor), `GCT_USB4145-03-0170-C_REVA2.kicad_mod` (`(footprint ... (tedit ...))`, no model), `how-to-import.htm`
- `downloaded_examples/LIB_RS3-1212S_H3.zip`: SamacSys. Files: `RS3-1212S_H3/KiCad/{RS3-1212S_H3.kicad_sym, RS3.kicad_mod, .lib, .dcm, .mod}`, `RS3-1212S_H3/3D/RS3-1212S_H3.stp`, `part_info.txt`, `license.txt`, `version.bin`, and ~30 other-CAD folders
- `downloaded_examples/ul_CSD85301Q2.zip`: tracked UL sample (unchanged)

### Codebase conventions
- `.planning/codebase/TESTING.md`: test markers (`kicad_cli`), fixture patterns
- `.planning/codebase/CONVENTIONS.md`: Issue/Severity contract, naming, module layering

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kicad_lib_manager/importer/adapters/ultralibrarian.py`: the template for new adapters (points-based `detect()` returning `Detection(name, points/10, reasons)`, with a claim threshold).
- `kicad_lib_manager/importer/adapters/base.py`: `locate()` already handles both samples. It provides `MANUFACTURER_FIELDS` / `MPN_FIELDS` / `DESCRIPTION_FIELDS` (which already include `MF`, `MANUFACTURER`, `Manufacturer_Name`, `MP`, `Manufacturer_Part_Number`), `part_meta()`, `_legacy_rules()` and `_name_list()`.
- `kicad_lib_manager/importer/detect.py`: the `ADAPTERS` registry and `detect_candidate()` (best confidence wins, ties go by registry order).
- `kicad_lib_manager/importer/suggest.py`: `REFERENCE_TYPE`, `MANUFACTURER_ALIASES` (already has `gct` / `globalconnectortechnology`→`GCT`), `AGGREGATOR_DOMAINS` (already lists snapeda, snapmagic, samacsys, componentsearchengine, mouser, arrow), `suggest_library()`.
- `kicad_lib_manager/importer/package.py`: `open_package(path, repo_root)`, `_classify()`, and the `Package.names` / `legacy` / `ignored` lists, which are where marker detection and the D-16 summary hook in.
- `tests/fixtures/build_fixtures.py`: the byte-exact fixture builder.
- `tests/conftest.py`: `kicad_cli_path` fixture.
- `pyproject.toml`: the `kicad_cli` marker.

### Established Patterns
- Services return `Issue(severity, code, text)` and never raise for expected failures. Codes are namespaced (`intake.*`, `install.*`).
- Untrusted text is bounded before parsing (8 MiB cap, 1,000,000-node ceiling). Intake never writes inside the repo.
- Gated tests use `pytest.mark.skipif` with a clear reason (see the `KICAD_IMPORT_UAT_DIR` gate in `tests/test_install_e2e.py`).

### Integration Points
- New adapters register in `ADAPTERS` (`detect.py`). The vendor label flows through `ImportCandidate.vendor` → `InstallPlan.vendor` → `commit_plan` `Import-Vendor` trailer.
- Field cleanup must show up in the preview through the shared plan (planner `_edit_symbol` area, `importer/planner.py`), so preview and install stay identical.
- The `part_info.txt` hints feed `suggest_library()` through `PartMeta` (or an extension of it) without changing the precedence "symbol fields win".

</code_context>

<specifics>
## Specific Ideas

- Expected SnapEDA outcome:
  - vendor `SnapEDA`, no 3D model warning;
  - Manufacturer "Global Connector Technology", MPN "USB4145-03-0170-C", `MANUFACTURER` and `SNAPEDA_PN` dropped;
  - Description "Type C USB 2.0 Connector";
  - Footprint field `<Lib>:GCT_USB4145-03-0170-C_REVA2`;
  - the suggestion should land on, or rank, the existing `Connector_USB_GCT` ("USB" appears in the Description). The planner should verify this.
- Expected SamacSys outcome:
  - vendor `SamacSys`;
  - legacy files ignored (INFO), `(module ...)` WARNING;
  - Manufacturer "RECOM Power", MPN "RS3-1212S/H3";
  - model `Custom/3DModels/RS3-1212S_H3.stp` linked as `${CUSTOM_3DMODEL_DIR}/RS3-1212S_H3.stp`;
  - Mouser/Arrow price fields and empty `Height` / `Arrow Part Number` dropped, `Mouser Part Number` kept;
  - suggestion `PowerSupply_SubCategory_RECOM`.
- SamacSys downloads from Mouser carry `Mouser Part Number` and a `mouser.co.uk` link. Keep the part number (D-05).

</specifics>

<deferred>
## Deferred Ideas

- Distributor in the vendor label, e.g. "SamacSys (Mouser)". Rejected for now (D-15); could return as provenance metadata.
- A per-field "keep" toggle in the preview for fields the cleanup would drop.
- Stripping SnapEDA `_REVxx` revision suffixes from symbol names (rejected, D-10).
- Licence review of the already-tracked `downloaded_examples/ul_CSD85301Q2.zip` in the public repo. It was not discussed and is worth a look.
- Moving the 3 tests that read the real `Custom/` tree onto the synthetic `Custom/` fixture built here (existing Active item in PROJECT.md).

</deferred>

---

*Phase: 07-snapeda-and-samacsys-adapters*
*Context gathered: 2026-10-23*
