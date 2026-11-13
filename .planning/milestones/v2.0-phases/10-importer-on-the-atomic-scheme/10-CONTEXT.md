# Phase 10: Importer on the Atomic Scheme - Context

**Gathered:** 2026-10-26
**Status:** Ready for planning

<domain>
## Phase Boundary

The importer moves onto the `Atomic_` scheme. A part imported from any supported vendor package (Ultra Librarian, SnapEDA, SamacSys/CSE, loose files) is suggested an `Atomic_<official KiCad symbol-library stem>` library by what the device is, never by manufacturer. Its single footprint goes into the shared `Atomic_Footprints.pretty`, or the symbol links an official KiCad footprint instead. The preview generates editable symbol keywords and a footprint description and tags. Install stays disabled until the incoming part passes the Phase 9 atomic check. Requirements: LIB-04, LIB-05, LIB-06, LIB-07, FLD-01, FLD-03.

Out of this phase: the commit gate (Phase 11, GIT-06), the import-flow review fixes (Phase 12), and the migration of the existing 12 v1-named libraries (Phase 13). The v1-named libraries stay on disk untouched until Phase 13. Table descriptions (TBL-01) are Phase 13.

</domain>

<decisions>
## Implementation Decisions

### Library suggestion (LIB-04)
- **D-01:** Suggestion order is: (1) **sibling lookup**, first in the owner's own `Atomic_` libraries, then in KiCad's installed stock symbol libraries; (2) the **category map**; (3) **ask**. A manufacturer name is never part of a suggestion.
- **D-02:** **Family prefix** = the part number's leading letters plus the first digit run after them, with at least 3 letters. Try the longest prefix first and shorten it until something matches, never going below 3 letters. Examples: `CSD85301Q2` tries `CSD85301`, then `CSD8`, then `CSD`. `RS3-1212S` must not match RECOM's `R-78…` parts in `Converter_DCDC`. Researcher: verify the rule against KiCad 10's libraries and all real samples.
- **D-03:** When the family matches several libraries, the **majority wins** (CSD: 84 in `Transistor_FET`, 2 in `Diode` → `Atomic_Transistor_FET`). The other libraries are offered as alternatives with their sibling counts.
- **D-04:** The **category map** reads the vendor or distributor category first (SamacSys `PartCategory`, SnapEDA category). It then reads words in the description and keywords (`MOSFET`, `isolated DC-DC`, `magnetometer`, …). Last comes the reference letter, and only where that letter alone is unambiguous (`J` → `Connector`). Broad letters such as `U` (and `Q` alone) never place a part. It maps to official stems, applying the construction rules of `research/LIBRARY-NAMING.md` §4 (e.g. `PartCategory` "Power Supply" + "isolated" → `Converter_DCDC_Isolated`).
- **D-05:** **Ask:** when nothing places the part, the library field starts **empty** with a plain hint, and Install is blocked until a library is picked or typed. There is no placeholder name such as v1.0's `<Type>_<SubCategory>_<Manufacturer>`.
- **D-06:** **Why a library was suggested** is shown in the library field's **tooltip only**, e.g. "Suggested from 84 similar parts in KiCad's Transistor_FET". v1.0's amber token line is removed.
- **D-07:** **No KiCad install found:** use a **built-in snapshot of KiCad 10's symbol-library stems** for the picker and the name rule. The stock sibling lookup is skipped with one INFO line. The own-`Atomic_` sibling lookup and the category map still run.

### Library choice and name rules (LIB-05)
- **D-08:** Only **`Atomic_` + an official KiCad symbol-library stem** is accepted, e.g. `Atomic_Sensor_Motion`. Anything else is refused with a plain reason. That covers a bare official name (`Transistor_FET`), an invented token (`Atomic_TI`, `Atomic_Connector_GCT`, `Atomic_MyStuff`), and an old v1 name. — **Reversibility:** costly — library nicknames are written into every installed symbol's Footprint/lib links and into the owner's KiCad projects, so loosening or changing the rule later means renaming libraries.
- **D-09:** Official stems that **carry a brand are allowed** because they are KiCad's own classification, e.g. `Atomic_MCU_Espressif` or `Atomic_MCU_ST_STM32F4`. The "no manufacturer name" rule targets only tokens we invent, and those already fail D-08.
- **D-10:** **Excluded stems** (not in the picker, refused if typed): `power`, `Simulation_SPICE` (and the `Simulation_SPICE.sp` file, which is not a stem), `Graphic`, and `Connector_Generic`, `Connector_Generic_MountingPin` and `Connector_Generic_Shielded`. `Device`, `Auxiliary_Items`, `Jumper` and `Mechanical` stay allowed.
- **D-11:** **Spelling:** a name that differs from a valid stem only in case is **auto-corrected** to the official spelling, with a short note. This prevents case twins on Windows.
- **D-12:** **Picker:** the dropdown lists the owner's existing `Atomic_` libraries first, then a divider, then every allowed `Atomic_<stem>`. Typing filters the list by substring. A library that doesn't exist yet carries the "new library" badge. The badge text changes, because a new library now creates only a `.kicad_sym` (D-15).
- **D-13:** **The 12 v1-named `Custom/` libraries are hidden** from the picker. Typing one is refused like any non-`Atomic_` name, so new imports cannot bring the old names back.

### Footprint destination (LIB-06)
- **D-14:** **One footprint per atomic part.** The footprint list in the dialog becomes **single-choice**. The other footprints in a package are not installed, and the preview lists them as "not used". (v1.0 INTK-07 allowed several to be ticked.)
- **D-15:** The default is "Install vendor footprint into `Atomic_Footprints`" (`Custom/Footprints/Atomic_Footprints.pretty`), and the Footprint field reads `Atomic_Footprints:<FP>`. A new symbol library **no longer creates a matching `.pretty`**, because the LIB-02 pair completion in `planner.py` is removed. `Atomic_Footprints.pretty` is created on first use, and its table entry follows the existing add-only post-install table rule.
- **D-16:** The alternative is "**Use an official KiCad footprint**". It opens a **filterable `Lib:FP` picker** over KiCad's installed footprints, pre-ranked by matches on the vendor package code (e.g. `DQK0006B`) and on pad count. The Footprint field then reads that official `<Lib>:<FP>`. **Würth footprints are not offered**: only `Atomic_Footprints` or KiCad official.
- **D-17:** With an official footprint, **KiCad's own 3D model is used**. The vendor footprint and the vendor STEP are not installed and appear as "not used" in the preview. KiCad's files are never edited. The 3D-model rule resolves KiCad's model per Phase 9 D-19.
- **D-18:** With an official footprint, a **pad check** compares the pad count and pad numbers with the symbol's pins (the existing POST-04 pin/pad check) and with the vendor footprint. A mismatch is an **amber warning, not blocking**.
- **D-19:** **Name clash in the shared library:** content identical to an existing footprint (token stream, ignoring formatting, as in Phase 9 D-21) means the existing footprint is reused, with no write. Different content gets the existing **Overwrite / Rename / Skip** row, with Rename pre-filled as `<FP>_<MPN>`. Overwrite warns which other `Custom/` symbols link that footprint.
- **D-20:** The default footprint name stays the **vendor name, editable** (the v1.0 decision stands).

### Install gate (LIB-07)
- **D-21:** Install is disabled while the **incoming part, as it would be installed**, fails the Phase 9 atomic check. Reuse `atomic_check` unchanged: the check runs on the planned symbol, footprint and model, not on what's on disk.
- **D-22:** **Value follows the MPN and is read-only.** It updates as MPN is edited. The vendor's old Value appears in the Field changes section. The Value := MPN rule can't be broken from the dialog.
- **D-23:** **Manufacturer is written in its canonical spelling** from `manufacturers.py`. A vendor alias (`TI`) becomes `Texas Instruments`, shown as `TI → Texas Instruments` in Field changes. A name not in the table is kept as typed and gets the Phase 9 D-11 INFO note, which does not block.
- **D-24:** **A missing 3D model blocks Install.** The fix is the existing "Add 3D model..." on the model row, or choosing an official footprint (D-17). There is no "install anyway" override. This reverses the v1.0 "no model → install and warn" decision for `Atomic_` targets, which are now the only targets. — **Reversibility:** reversible — a gate condition only.
- **D-25:** **Failures display:** each failure is a clickable line in the existing reason strip (`form.blocking_reasons` / `Reason.target`) that focuses its field, and the field gets the existing amber frame. Both clear live as the field is filled in. Wording is plain language: no raw field names such as `ki_description`, `ki_keywords` or `ki_fp_filters`.

### Keywords and footprint tags (FLD-01, FLD-03)
- **D-26:** **Symbol keywords** are generated from function words, interfaces, package and vendor package codes, manufacturer aliases and MPN variants (FLD-01). Two extra sources are added. One is the **runner-up category words**: the library or vendor category the suggestion didn't pick, e.g. `diode` or `power supply` (LIBRARY-NAMING §4 step 4). The other is the **parent brand of an acquired maker**, from the manufacturer table's `owner` note (Phase 9 D-08), e.g. Maxim → `ADI Analog`. The Manufacturer field never changes because of this. **No relational spec tokens** (`Vout=12`): the owner can type them by hand.
- **D-27:** **Vendor keywords are merged**: vendor words first, then generated words not already present (case-insensitive de-duplication). Price, stock and distributor junk words are dropped.
- **D-28:** **Footprint tags**: package name, IPC name, vendor package code and pitch. **Pitch is computed from pad geometry** (the smallest repeated pad-to-pad spacing) and the body size from the fab or courtyard outline. An **IPC-7351 name** is built only when the package family is recognised. Anything that can't be worked out is left out, never guessed. Vendor tags are **merged** with the generated ones.
- **D-29:** **Footprint description is replaced** by one generated plain sentence, e.g. "WSON-6 2x2 mm, 0.65 mm pitch, TI DQK0006B". The old description appears in Field changes. Official KiCad footprints are never edited: no description or tags are written to them.
- **D-30:** **Editing:** three plain line edits, "Keywords", "Footprint description" and "Footprint tags", hold space-separated words as KiCad stores them. They are pre-filled with the generated text and have a "Regenerate" link. The installed files carry exactly what the preview showed, because preview and install share one plan (v1.0 PREV contract).

### Claude's Discretion
- Module layout for the stem list, the category map, the sibling index (and its caching, since KiCad's stock libraries are large), keyword generation and footprint geometry analysis. They must stay Qt-free and pass the layering tests.
- How the incoming-part check builds an `AtomicContext` that sees the planned `Atomic_Footprints` footprint and the planned model before they exist on disk.
- The ranking formula of the official-footprint picker, and how its footprint index is built off the GUI thread.
- The exact wording of reasons, hints, tooltips and the "not used" rows.
- How the existing v1.0 suggestion tests and the UAT expectation (`PowerSupply_SubCategory_RECOM` → `Atomic_Converter_DCDC_Isolated`) are retargeted.
- Price/stock leftovers in the incoming symbol: dropped at import, as the volatile-field rules already do.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/REQUIREMENTS.md`: LIB-04..07, FLD-01, FLD-03 (and FLD-02, ATOM-01..03 as reused contracts)
- `.planning/ROADMAP.md` § Phase 10: the 5 success criteria (CSD → `Atomic_Transistor_FET`, RS3-1212S/H3 → `Atomic_Converter_DCDC_Isolated`)
- `.planning/PROJECT.md`: Key Decisions (the `Atomic_` scheme, footprint keeps the vendor name, the preview-before-write and stale-plan rules)

### Naming and classification
- `.planning/research/LIBRARY-NAMING.md` §2 (chooser search weights: why keywords and tags matter), §4 (classification rule and construction rules for the category map), §5 (target libraries for the existing parts), §6 (fields, keywords, footprint descr/tags), §7 (importer impact: `suggest.py`, `planner.py` LIB-02 pair completion, affected tests). Its `_MecaFrog` suffix and `MecaFrog.pretty` are superseded by the `Atomic_` prefix and `Atomic_Footprints.pretty`.

### Prior phase context
- `.planning/phases/09-atomic-rule-check-and-scan-detection/09-CONTEXT.md`: D-07..D-11 (manufacturer table, folding, INFO note), D-17 (Datasheet validity), D-19 (KiCad 3D model resolution), D-20 (Footprint rule scope), D-21 (token-stream compare), D-22 (derived symbols)
- `.planning/phases/08-test-isolation-and-kicad-10/08-CONTEXT.md`: synthetic `Custom/` fixture rules and the live-`Custom/` write-protect guard
- `tests/README.md`: expected skips; the suite must not write to or depend on the live `Custom/`

### Project docs
- `CLAUDE.md`: KiCad path variables (`CUSTOM_3DMODEL_DIR`) and the Git workflow. Its naming section is updated in Phase 13 (DOC-01), not here.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kicad_lib_manager/atomic_check.py`: `is_atomic`, `datasheet_problem`, `check_symbol(root, name, rel_path=, fixable=, ctx=)`, `AtomicContext`, `repo_context`. This is the gate (D-21), reused unchanged.
- `kicad_lib_manager/manufacturers.py`: `lookup`, `fold`, `CORPORATE_WORDS`, and the `Manufacturer.owner` note for D-23 and D-26. `token_map()` and `suggest.MANUFACTURER_ALIASES` exist only for the v1.0 manufacturer token and can go once that token is dropped.
- `kicad_lib_manager/importer/kicad_cli.py` `stock_symbols_dir(kicad_fp_dir)`: the source of official stems and stock siblings.
- `kicad_lib_manager/importer/suggest.py`: `type_choice`, `PART_CATEGORY_TYPE`, `REFERENCE_TYPE`, `_part_tokens`, `datasheet_host`. These are the seeds for the category map (D-04). `suggest_library`, `_rank`, `_subcategory`, `placeholder_tokens` and `HOST_TOKENS` are v1.0 `<Type>_<SubCategory>_<Manufacturer>` logic to replace.
- `kicad_lib_manager/importer/form.py`: `blocking_reasons`, `Reason(text, target)`, `_issue_target`, `library_tokens`, `library_badge`, `NEW_LIBRARY_BADGE`, `field_defaults`, `build_options`. These are where the gate reasons, the read-only Value and the badge text change.
- `kicad_lib_manager/importer/planner.py` `build_plan`: the LIB-02 pair completion (around lines 740-747 and 1160, `new_footprint_lib`) is removed. Footprint ops retarget to `Atomic_Footprints.pretty`. `_edit_symbol` already retokens `ki_keywords` (line ~218).
- `kicad_lib_manager/importer/candidate.py` `PartMeta`: `keywords`, `category`, `reference`, `description` are the inputs for suggestion and keywords.
- `kicad_lib_manager/kicad_files.py`: property and model edit primitives; `footprint_name`.
- `kicad_lib_manager/sexpr.py`: the token stream for the D-19 identical-footprint compare.
- `kicad_lib_manager/widgets/import_dialog.py`: `_build_library_section` (the combo), `_build_footprint_section`, `_build_fields_section` (field edits, amber frames via `_framed`), `_build_footprint_list` (becomes single-choice), `_build_model_row` ("Add 3D model...").

### Established Patterns
- Qt-free services return `Issue` lists; the dialog maps them to reasons. Preview and install share one `InstallPlan` (PREV contract): what the preview shows is what gets written.
- Long work (package reading, kicad-cli, plan building) runs off the GUI thread via the dialog's `TaskWorker`. The stock-library and footprint indexes must follow this rule.
- Untrusted-text caps (8 MiB, 1,000,000 nodes) apply to vendor files. KiCad's stock libraries are trusted but large, so their parse cost matters.
- Plain-language UI (owner feedback 2026-10-24): map internal names to KiCad's labels.
- Tests: synthetic `Custom/` fixtures (`tests/customfixtures.py`) with `Atomic_` libraries since Phase 9. Real-sample tests use `downloaded_examples/` and skip when absent. Real kicad-cli tests pin KiCad 10.

### Integration Points
- `suggest.py` → new Atomic suggestion API consumed by the import dialog.
- `planner.build_plan` → footprint destination (`Atomic_Footprints` or official link), generated keywords, footprint descr/tags, canonical Manufacturer, Value = MPN.
- `form.blocking_reasons` → atomic-check reasons with field targets.
- `import_dialog.py` → library picker, footprint toggle and official picker, single-choice footprint list, read-only Value, three new edit fields.
- Tests named in LIBRARY-NAMING §7: test_install_plan, test_install_apply, test_install_e2e, test_vendor_install, test_import_form, test_import_dialog, test_import_preview, and `tests/zipfixtures.py`.

</code_context>

<specifics>
## Specific Ideas

- KiCad 10 facts found while scouting: `Transistor_FET` holds 84 `CSD…` symbols, `Diode` holds `CSD01060A/E` (Cree SiC), and no `CSD8…` exists anywhere. `Converter_DCDC` holds RECOM `R-78…` parts, and `Converter_DCDC_Isolated` holds no `RS3`. KiCad 10 ships 224 symbol-library files; `Simulation_SPICE.sp` is not a library.
- All five real samples ship exactly one footprint: CSD85301Q2 `DQK0006B`, ATXK-H14 `ATXK-H14_ABR`, RS3-1212S `RS3`, USB4145 `GCT_USB4145-03-0170-C_REVA2`, and the SnapEDA USB4145 folder.
- Example footprint description: "WSON-6 2x2 mm, 0.65 mm pitch, TI DQK0006B".

</specifics>

<deferred>
## Deferred Ideas

- **A derived variant per extra footprint.** When a package ships several footprints (e.g. IPC density variants), each extra one would become its own `extends` symbol with its own MPN and footprint. The owner's idea; it needs a real multi-footprint sample in `downloaded_examples/` first (project rule). Phase 10 uses single choice instead.
- **Relational spec tokens** (`Vout=12 Viso=3k`) generated in keywords: not generated now, since they are error-prone. The owner can type them.

</deferred>

---

*Phase: 10-importer-on-the-atomic-scheme*
*Context gathered: 2026-10-26*
