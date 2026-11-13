# Phase 10: Importer on the Atomic Scheme - Research

**Researched:** 2026-10-26
**Domain:** Python/PySide6 desktop importer for KiCad 10 libraries: name suggestion from KiCad's stock libraries, `Atomic_` naming rules, footprint destination, incoming-part atomic gate, generated keywords and footprint tags
**Confidence:** HIGH on the code seams and the measured KiCad 10 facts; MEDIUM on the heuristics the owner still has to confirm (see Assumptions Log)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Library suggestion (LIB-04)
- **D-01:** Suggestion order is: (1) **sibling lookup**, first in the owner's own `Atomic_` libraries, then in KiCad's installed stock symbol libraries; (2) the **category map**; (3) **ask**. A manufacturer name is never part of a suggestion.
- **D-02:** **Family prefix** = the part number's leading letters plus the first digit run after them, with at least 3 letters. Try the longest prefix first and shorten it until something matches, never going below 3 letters. Examples: `CSD85301Q2` tries `CSD85301`, then `CSD8`, then `CSD`. `RS3-1212S` must not match RECOM's `R-78…` parts in `Converter_DCDC`. Researcher: verify the rule against KiCad 10's libraries and all real samples.
- **D-03:** When the family matches several libraries, the **majority wins** (CSD: 84 in `Transistor_FET`, 2 in `Diode` → `Atomic_Transistor_FET`). The other libraries are offered as alternatives with their sibling counts.
- **D-04:** The **category map** reads the vendor or distributor category first (SamacSys `PartCategory`, SnapEDA category). It then reads words in the description and keywords (`MOSFET`, `isolated DC-DC`, `magnetometer`, …). Last comes the reference letter, and only where that letter alone is unambiguous (`J` → `Connector`). Broad letters such as `U` (and `Q` alone) never place a part. It maps to official stems, applying the construction rules of `research/LIBRARY-NAMING.md` §4 (e.g. `PartCategory` "Power Supply" + "isolated" → `Converter_DCDC_Isolated`).
- **D-05:** **Ask:** when nothing places the part, the library field starts **empty** with a plain hint, and Install is blocked until a library is picked or typed. There is no placeholder name such as v1.0's `<Type>_<SubCategory>_<Manufacturer>`.
- **D-06:** **Why a library was suggested** is shown in the library field's **tooltip only**, e.g. "Suggested from 84 similar parts in KiCad's Transistor_FET". v1.0's amber token line is removed.
- **D-07:** **No KiCad install found:** use a **built-in snapshot of KiCad 10's symbol-library stems** for the picker and the name rule. The stock sibling lookup is skipped with one INFO line. The own-`Atomic_` sibling lookup and the category map still run.

#### Library choice and name rules (LIB-05)
- **D-08:** Only **`Atomic_` + an official KiCad symbol-library stem** is accepted, e.g. `Atomic_Sensor_Motion`. Anything else is refused with a plain reason. That covers a bare official name (`Transistor_FET`), an invented token (`Atomic_TI`, `Atomic_Connector_GCT`, `Atomic_MyStuff`), and an old v1 name. — **Reversibility:** costly — library nicknames are written into every installed symbol's Footprint/lib links and into the owner's KiCad projects, so loosening or changing the rule later means renaming libraries.
- **D-09:** Official stems that **carry a brand are allowed** because they are KiCad's own classification, e.g. `Atomic_MCU_Espressif` or `Atomic_MCU_ST_STM32F4`. The "no manufacturer name" rule targets only tokens we invent, and those already fail D-08.
- **D-10:** **Excluded stems** (not in the picker, refused if typed): `power`, `Simulation_SPICE` (and the `Simulation_SPICE.sp` file, which is not a stem), `Graphic`, and `Connector_Generic`, `Connector_Generic_MountingPin` and `Connector_Generic_Shielded`. `Device`, `Auxiliary_Items`, `Jumper` and `Mechanical` stay allowed.
- **D-11:** **Spelling:** a name that differs from a valid stem only in case is **auto-corrected** to the official spelling, with a short note. This prevents case twins on Windows.
- **D-12:** **Picker:** the dropdown lists the owner's existing `Atomic_` libraries first, then a divider, then every allowed `Atomic_<stem>`. Typing filters the list by substring. A library that doesn't exist yet carries the "new library" badge. The badge text changes, because a new library now creates only a `.kicad_sym` (D-15).
- **D-13:** **The 12 v1-named `Custom/` libraries are hidden** from the picker. Typing one is refused like any non-`Atomic_` name, so new imports cannot bring the old names back.

#### Footprint destination (LIB-06)
- **D-14:** **One footprint per atomic part.** The footprint list in the dialog becomes **single-choice**. The other footprints in a package are not installed, and the preview lists them as "not used". (v1.0 INTK-07 allowed several to be ticked.)
- **D-15:** The default is "Install vendor footprint into `Atomic_Footprints`" (`Custom/Footprints/Atomic_Footprints.pretty`), and the Footprint field reads `Atomic_Footprints:<FP>`. A new symbol library **no longer creates a matching `.pretty`**, because the LIB-02 pair completion in `planner.py` is removed. `Atomic_Footprints.pretty` is created on first use, and its table entry follows the existing add-only post-install table rule.
- **D-16:** The alternative is "**Use an official KiCad footprint**". It opens a **filterable `Lib:FP` picker** over KiCad's installed footprints, pre-ranked by matches on the vendor package code (e.g. `DQK0006B`) and on pad count. The Footprint field then reads that official `<Lib>:<FP>`. **Würth footprints are not offered**: only `Atomic_Footprints` or KiCad official.
- **D-17:** With an official footprint, **KiCad's own 3D model is used**. The vendor footprint and the vendor STEP are not installed and appear as "not used" in the preview. KiCad's files are never edited. The 3D-model rule resolves KiCad's model per Phase 9 D-19.
- **D-18:** With an official footprint, a **pad check** compares the pad count and pad numbers with the symbol's pins (the existing POST-04 pin/pad check) and with the vendor footprint. A mismatch is an **amber warning, not blocking**.
- **D-19:** **Name clash in the shared library:** content identical to an existing footprint (token stream, ignoring formatting, as in Phase 9 D-21) means the existing footprint is reused, with no write. Different content gets the existing **Overwrite / Rename / Skip** row, with Rename pre-filled as `<FP>_<MPN>`. Overwrite warns which other `Custom/` symbols link that footprint.
- **D-20:** The default footprint name stays the **vendor name, editable** (the v1.0 decision stands).

#### Install gate (LIB-07)
- **D-21:** Install is disabled while the **incoming part, as it would be installed**, fails the Phase 9 atomic check. Reuse `atomic_check` unchanged: the check runs on the planned symbol, footprint and model, not on what's on disk.
- **D-22:** **Value follows the MPN and is read-only.** It updates as MPN is edited. The vendor's old Value appears in the Field changes section. The Value := MPN rule can't be broken from the dialog.
- **D-23:** **Manufacturer is written in its canonical spelling** from `manufacturers.py`. A vendor alias (`TI`) becomes `Texas Instruments`, shown as `TI → Texas Instruments` in Field changes. A name not in the table is kept as typed and gets the Phase 9 D-11 INFO note, which does not block.
- **D-24:** **A missing 3D model blocks Install.** The fix is the existing "Add 3D model..." on the model row, or choosing an official footprint (D-17). There is no "install anyway" override. This reverses the v1.0 "no model → install and warn" decision for `Atomic_` targets, which are now the only targets. — **Reversibility:** reversible — a gate condition only.
- **D-25:** **Failures display:** each failure is a clickable line in the existing reason strip (`form.blocking_reasons` / `Reason.target`) that focuses its field, and the field gets the existing amber frame. Both clear live as the field is filled in. Wording is plain language: no raw field names such as `ki_description`, `ki_keywords` or `ki_fp_filters`.

#### Keywords and footprint tags (FLD-01, FLD-03)
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

### Deferred Ideas (OUT OF SCOPE)
- **A derived variant per extra footprint.** When a package ships several footprints (e.g. IPC density variants), each extra one would become its own `extends` symbol with its own MPN and footprint. The owner's idea; it needs a real multi-footprint sample in `downloaded_examples/` first (project rule). Phase 10 uses single choice instead.
- **Relational spec tokens** (`Vout=12 Viso=3k`) generated in keywords: not generated now, since they are error-prone. The owner can type them.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIB-04 | Importer suggests `Atomic_<official KiCad library stem>` from what the device is: sibling family / MPN prefix in KiCad's installed libraries, else a category map, else ask. No manufacturer name. | Family-prefix rule measured on all 223 KiCad 10 libraries and the 5 samples (strict-majority guard lifts precision 79% to 97%); stock index costs 0.5 s warm; category-map rules and reference-letter evidence; KiCad 10 stem list (Appendix A). |
| LIB-05 | Pick an existing `Atomic_` library or type a new one; official KiCad names and manufacturer tokens are refused. | Allow-list rule `Atomic_` + stem (217 allowed of 223); case-fold auto-correction is collision-free (223 stems are unique under casefold); `QCompleter` MatchContains filter verified on a combo model. |
| LIB-06 | Footprints install into shared `Atomic_Footprints.pretty` or a picked official footprint; no `.pretty` pairing. | Full coupling-point list for `plan.library` / `pretty_path` / `new_library` / `add_library_entries` / `verify`; `Package_SON:Texas_DQK` is the real official match for the CSD sample; footprint index costs 0.5 s for names, 158 s for a full pad scan (so pad counts must be lazy). |
| LIB-07 | Install blocked until the incoming part passes the atomic check; each failure is a clickable reason; Value defaults to MPN; Datasheet, Description, 3D model editable. | `AtomicContext` seam and the minimal `repo_context` extension to see planned files; violations to `Issue` codes to `Reason.target` mapping; live-clear via the existing `explained()` pattern; real-sample outcomes (which sample fails which rule). |
| FLD-01 | Generate `ki_keywords`: function words, interfaces, package codes, manufacturer aliases, MPN variants; editable. | Keyword sources per sample, merge rule, MPN-variant rule, real sibling keyword examples from KiCad 10 (`CSD16301Q2`). |
| FLD-03 | Footprints get description and tags: package, IPC name, vendor package code, pitch. | Pitch algorithm verified on 6 footprints; body from F.Fab bbox (courtyard overstates); family only from text sources; `descr`/`tags` insertion verified with real `kicad-cli 10.0.7` for both `footprint` and legacy `module` roots. |
</phase_requirements>

## Summary

Phase 10 is mostly a re-plumbing of an importer that already works. Five seams carry nearly all the change: `suggest.py` (replaced), `planner.build_plan` (footprint destination, field rules, incoming gate, generated text), `form.py` (name rule, reasons), `import_dialog.py` (picker, destination toggle, single-choice footprint, three new edits) and the post-install table step in `main_window.py` / `table_generator.add_library_entries`. Everything the phase needs from KiCad is read-only: the stock symbol and footprint folders next to the detected `kicad_fp_dir`. No new third-party package is needed.

The measured findings that change how the plan should be written: (1) the D-02 family-prefix rule is only 79% precise on KiCad 10 itself if the plurality is taken, but 96.9% precise (on 77% of symbols that have a usable prefix) if a strict majority is required, which is literally D-03's "majority wins"; (2) the CONTEXT's "84 CSD symbols" counts unit sub-symbols too, the real top-level count is 75 in `Transistor_FET` and 2 in `Diode`; (3) the `Texas_DQK` footprint in KiCad's `Package_SON` is the exact official match for the CSD85301Q2 sample and carries `WSON-6` and `2x2mm` in its own `descr`/`tags`, which is the only honest source of "WSON-6" (the vendor footprint has none); (4) full pad counting over KiCad's 15,464 footprints takes 158 s, so the official-footprint ranking must use names first and read pads lazily; (5) `Converter_DCDC_Isolated` exists only in KiCad 10, so the stem allow-list must be the built-in KiCad 10 snapshot (union with the installed stems), and there is no `Crystal` stem despite LIBRARY-NAMING §4; (6) about 240 `library=` call sites and about 250 v1-name mentions in 14 test files, so the strictness choice for `build_plan` decides a large mechanical test migration.

Four real samples fail the atomic gate for different reasons, which is the proof set for LIB-07 and the UAT: CSD85301Q2 (no Description, Manufacturer must be inferred as `Texas Instruments`), ATXK-H14 (Datasheet is not a link, no Manufacturer, no 3D model), RS3-1212S/H3 (passes once the model is kept; Manufacturer `RECOM Power` becomes `RECOM`), USB4145 (no Datasheet, no 3D model until the separate SnapEDA model is attached).

**Primary recommendation:** Keep `build_plan` as the single enforcement point (library-name allow-list, incoming atomic check as ERROR Issues with field-mapped codes), add the new data to `InstallOptions`/`InstallPlan` rather than to the dialog, implement all new logic as Qt-free modules under `importer/`, and require a strict majority for stock-sibling suggestions.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Stem allow-list, name verdict, case correction | Qt-free service (`importer/`) | GUI shows the verdict | One rule used by form (live) and planner (authoritative); D-08 is costly to reverse so it must not live only in the dialog |
| Stock/own sibling index, family prefix, category map, suggestion | Qt-free service | Open worker thread (`TaskWorker`) | Reads 235 MB of KiCad files; must run off the GUI thread and cache |
| Footprint destination, link string, tables | Qt-free planner (`build_plan`) | Dialog toggle; `main_window` post-install | Preview and install share one `InstallPlan` (PREV contract) |
| Incoming atomic check | Qt-free planner via `atomic_check` | `form.blocking_reasons` maps to targets | D-21 says reuse the check unchanged on planned bytes |
| Keyword / footprint description / tags generation | Qt-free service | Dialog edits, Regenerate | Phase 13 migration reuses the same functions |
| Pad geometry (pitch, body) | Qt-free service reading parsed footprint nodes | none | Uses `sexpr`/`kicad_files` primitives only |
| Official-footprint index and ranking | Qt-free service, built on a worker | Filterable picker widget | 0.5 s name listing; pad counts lazy |
| Library picker, destination toggle, single-choice footprint, three line edits, amber frames | GUI (`widgets/import_dialog.py`) | `form.py` rules | Widgets only; no rules |
| KiCad install (stock symbols/footprints/3D models, kicad-cli) | External, read-only | `ToolContext` carries paths | Never written; footprint links are just strings |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python (venv) | 3.14.4 | all code | `env/Scripts/python.exe --version` printed `Python 3.14.4` [VERIFIED: run this session] |
| PySide6 | 6.12.0 | dialog widgets (`QComboBox`, `QCompleter`) | `PySide6.__version__` printed `6.12.0` [VERIFIED: run this session] |
| Python stdlib (`re`, `os`, `dataclasses`, `html`, `pathlib`) | stdlib | index, rules, escaping | Project constraint: stdlib only unless clearly justified (`.claude/CLAUDE.md` Constraints) |
| In-repo `sexpr`, `kicad_files`, `atomic_check`, `manufacturers`, `fieldrules`, `verify`, `fsutil` | n/a | parsing, check, canonical names, pin/pad compare, writes | Reuse unchanged (D-21, Phase 9 contracts) |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 | tests | `requirements-dev.txt` pins `pytest==9.1.1` [VERIFIED: read this session] |
| pytest-qt | 4.5.0 | dialog tests | `requirements-dev.txt` pins `pytest-qt==4.5.0` [VERIFIED: read this session] |
| KiCad (external, read-only) | 10.0.7 (`kicad-cli version` printed `10.0.7`) | stock libraries, 3D models, `kicad-cli fp/sym upgrade` load gate | Optional at runtime; D-07 defines the fallback |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Strict-majority stock suggestion | Plurality (literal "family prefix, majority-ish") | Plurality is 79.1% precise vs 96.9% on KiCad 10 leave-one-out; the extra 3,086 uncovered symbols fall to the category map or ask, which is safe because Install needs a library anyway |
| Name-first official footprint ranking | Pad count over all footprints | Full pad scan = 158 s cold for 165.7 MB; not viable for the GUI |
| Library nickname rule inside `build_plan` | Rule only in the dialog | Dialog-only leaves `build_plan` open to any name; D-08 is "costly" |

**Installation:** none. No new package is installed by this phase.

**Version verification:** versions above were read from the venv and `requirements-dev.txt` in this session, not from training data.

## Package Legitimacy Audit

No external package is added by this phase (stdlib, PySide6 6.12.0 already in the venv, pytest and pytest-qt already pinned). Nothing to check with `package-legitimacy`.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none added) | n/a | n/a | n/a | n/a | n/a | n/a |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 package opened (zip/folder)                        KiCad install (read-only)
        |                                           symbols/*.kicad_sym   footprints/*.pretty   3dmodels
        v                                                  |                     |
 open worker (TaskWorker) ------------------------------>  |                     |
   detect_candidate -> PartMeta (mpn/category/description/keywords/reference/datasheet)
        |                                                  v                     v
        |                                    stock sibling index (cached)   footprint name index (cached)
        v                                                  |                     |
 suggest_library:  own Atomic_ siblings -> stock siblings (strict majority) -> category map -> ask
        |   (reason text -> library tooltip; alternatives with counts)
        v
 dialog (GUI thread):  library picker | destination toggle | single footprint | fields | 3 text edits
        |  FormValues -> form.build_options -> InstallOptions(library, fp target, overrides)
        v
 build_plan (worker, serialised, latest wins)
   name verdict (Atomic_<stem>)  ->  footprint destination (shared lib | official link)
   -> edit symbol (Manufacturer canonical, Value := MPN, keywords)  -> edit footprint (descr, tags, model link)
   -> D-19 token-stream clash decision -> ops (mkdir, model, footprint, symbol_lib)
   -> incoming atomic check on the planned bytes (AtomicContext sees planned fp + model)
   -> InstallPlan{ops, issues (ERROR per violation), generated text, fp link}
        |
        +--> preview_sections (Files, Renames, Path rewrites, Field changes, Not used, Issues)
        +--> form.blocking_reasons -> reason strip (clickable) -> focus target + amber frame
        v
 Install enabled only if plan has no ERROR and no unresolved conflict
        v
 apply_plan (unchanged transaction) -> verify_install (official-link aware) -> main_window post-install:
   add sym-lib-table entry (new Atomic_<stem>)  +  add fp-lib-table entry (Atomic_Footprints, first use)
```

### Recommended Project Structure
```
kicad_lib_manager/
├── manufacturers.py          # + hosts per entry, infer_from_host(); drop token/token_map when suggest no longer needs them
├── kicad_files.py            # + footprint descr/tags edit primitives
├── atomic_check.py           # repo_context(..., planned_footprints, planned_models) extension only; rules untouched
├── table_generator.py        # add_library_entries split into separate symbol / footprint nicknames
├── importer/
│   ├── stems.py              # KICAD10_STEMS snapshot, EXCLUDED_STEMS, SHARED_FOOTPRINT_LIBRARY, name_verdict()
│   ├── siblings.py           # family_prefixes(), stock index build + cache, own-library index, majority()
│   ├── categories.py         # vendor-category / word / reference-letter rules -> stem (data + classify())
│   ├── suggest.py            # rewritten: suggest_library() orchestrator; keeps datasheet_host / registered_domain / is_aggregator_host
│   ├── keywords.py           # generate_keywords(), merge_words()
│   ├── footprint_text.py     # pad geometry, package family, description, tags, merge_tags()
│   ├── footprint_index.py    # official Lib:FP name index, rank(), lazy pad count
│   ├── incoming.py           # builds the AtomicContext for the planned part; violations -> Issues
│   ├── plan.py / planner.py / form.py / preview.py / verify.py / commit_plan.py   # changed
└── widgets/import_dialog.py, help_dialog.py ; main_window.py (post-install)       # changed
tests/ ...                    # new + migrated (see Validation Architecture)
```
Every new importer module must be added to `ALLOWED` in `tests/test_importer_layering.py`; `incoming.py` needs `atomic_check` in its entry, and `tests/test_layering.py` needs the `atomic_check` / `kicad_files` additions noted below.

### Pattern 1: Suggestion pipeline (LIB-04)
**What:** `suggest_library(meta, own_libs, stock_index, stems) -> LibrarySuggestion(name or "", source, reason, alternatives, issues)`.
1. Part number = `meta.mpn or meta.symbol_name`. Prefixes (D-02, example form): `letters+digitrun`, `letters+first digit` (only if the run is longer than one digit), `letters`; skip entirely when `len(letters) < 3`.
2. For each source in order (own `Atomic_` libraries, then stock): take the first prefix step that has any sibling; excluded stems do not vote; **a strict majority (> 50%) of the matched siblings wins**; otherwise stop at that step with no suggestion and carry the counts as alternatives.
3. Category map (Pattern 2), then ask (`name == ""`).
4. `reason` is a plain sentence for the library tooltip (D-06), built from trusted pieces only (see Pitfall 9).

**Measured on the real samples** [VERIFIED: scripts run against `C:/Program Files/KiCad/10.0/share/kicad/symbols` this session]:

| Sample | Part number | Prefix steps | Result |
|--------|-------------|--------------|--------|
| CSD85301Q2 | `CSD85301Q2` (symbol name; `meta.mpn` is empty) | `CSD85301`, `CSD8`: no sibling; `CSD`: `Transistor_FET` 75, `Diode` 2 (97.4%) | `Atomic_Transistor_FET`, alternative `Diode` (2) |
| RS3-1212S/H3 | `RS3-1212S/H3` | letters `RS` = 2 < 3, no lookup (so it cannot hit RECOM's `R-78…`) | category map |
| ATXK-H14 | `ATXK-H14-D-32.768KHZ-E50-T3` | `ATXK`: 0 siblings | category map, then ask |
| USB4145 | `USB4145-03-0170-C` | `USB4145`, `USB4`: none; `USB`: `Connector` 17, `Interface_USB` 10, `Power_Protection` 4 (54.8%) | `Connector` passes the majority guard; the reference letter `J` agrees |

**Rule quality on KiCad 10 itself** (leave-one-out: remove the symbol, ask the rule where it belongs; 21,725 symbols outside the excluded stems, 14,929 of them have a prefix with 3+ letters) [VERIFIED: script run this session]:

| Policy | Suggested | Precision |
|--------|-----------|-----------|
| First step with any sibling, plurality | 14,621 | 79.1% |
| First step with any sibling, strict majority | 11,535 | 96.9% |
| Step precision (any plurality): full run / first digit / letters only | 8,045 ok vs 2,531 wrong / 2,003 vs 359 / 1,512 vs 171 | 76.1% / 84.8% / 89.8% |

Short manufacturer prefixes (`MAX4`, `LTC1`, `INA1`) span many functions; the majority guard is what keeps them from mis-filing.

### Pattern 2: Category map as data with a self-check
**What:** an ordered tuple of rules `(vendor_categories, words_all, words_any, stem)` plus a reference-letter table, all in `categories.py`. A unit test asserts every target stem is in the KiCad 10 snapshot minus the excluded stems, so the map cannot drift from the allow-list.
- Vendor category keys are the casefolded letters and digits of `PartCategory` (as `suggest.type_choice` does today). Only `Power Supply` has been seen in a real download; **no SnapEDA sample carries any category** (the SnapEDA adapter never sets `PartMeta.category`), so the SnapEDA hook stays a pass-through until a real sample exists (project rule).
- Words come from description + keywords + category, tokenised as `suggest._part_tokens` does. Initial rules from LIBRARY-NAMING §4:
  - `power supply` or `converter` with `isolat*` -> `Converter_DCDC_Isolated`; with `ac/dc` -> `Converter_ACDC`; with `dc/dc` or `dcdc` -> `Converter_DCDC`; `ldo` or `linear regulator` -> `Regulator_Linear`; `buck`/`boost`/`switching regulator` -> `Regulator_Switching`.
  - `mosfet`/`n-channel`/`p-channel` -> `Transistor_FET`; `bjt`/`npn`/`pnp` -> `Transistor_BJT`; `diode` -> `Diode`; `magnetometer` -> `Sensor_Magnetic`; `imu`/`accelerometer`/`gyroscope` -> `Sensor_Motion`; `fuel gauge`/`charger` -> `Battery_Management`; `tcxo`/`oscillator`/`mems oscillator` -> `Oscillator`; `usb`+`connector`/`receptacle`/`header` -> `Connector`.
  - **There is no `Crystal` stem in KiCad 10**; passive crystals live in `Device` (reference `Y`: `Oscillator` 121, `Device` 12 in stock), so a "crystal" word must map to `Device` or not map at all, never to `Crystal`.
- The reference-letter fallback uses stock evidence [VERIFIED: script over 21,725 symbols, excluded stems removed]: `K` -> `Relay` (256 of 256), `SW` -> `Switch` (80 of 83), `TR` -> `Transformer` (81 of 81), `M` -> `Motor` (23 of 23), `JP` -> `Jumper` (11 of 11), `J` -> `Connector` (386 of 625, the rest is `Connector_Audio` 233). `J` is therefore the example D-04 names but is not 100% unambiguous; keep it, per the owner's example. `U` (17,126 symbols over every stem), `Q` (54% FET, 35% BJT), `D` (57% Diode), `X` (5 symbols, `RF_Filter`) and `Y` (91% Oscillator, but crystal vs oscillator is exactly the ambiguity LIBRARY-NAMING §4 calls out) should not place a part. Result: ATXK-H14 (reference `X`, no category, no description) correctly asks.
- RS3-1212S/H3 resolves by category `Power Supply` + description words `Isolated DC/DC Converters ...` -> `Converter_DCDC_Isolated` [VERIFIED: description and category read from the sample via the repo's own adapter].

### Pattern 3: One name rule, used twice
**What:** `stems.name_verdict(text, stems, existing)` returns `(ok, corrected, reason)`. The form calls it live (reason with target `library`), `build_plan` calls it again and returns `install.invalid_library` as an ERROR; `build_plan` stays the authority.
- Rule: casefold the whole text against `{ "Atomic_" + stem }` for every allowed stem; exact match -> ok; case-only difference -> corrected (D-11) with a short note, applied by the dialog on `editingFinished`/activation, never per keystroke; anything else -> refused with a plain reason distinguishing: bare official stem (`Transistor_FET`), excluded stem, invented token (`Atomic_TI`), old v1 name, empty.
- `Atomic_` prefix test is the existing `atomic_check.is_atomic`, case-sensitive: `ATOMIC_PREFIX = "Atomic_"` (atomic_check.py:20). Quote: `def is_atomic(nickname: str) -> bool: ... return nickname.startswith(ATOMIC_PREFIX)` (atomic_check.py:43-45).
- Allowed stems = KiCad 10 snapshot (223 stems, Appendix A) minus the 6 excluded (217 allowed), **unioned with the installed stock stems** when KiCad is found (a newer KiCad adds stems; a KiCad 9 install lacks `Converter_DCDC_Isolated`, `Driver` and `FPGA_Altera_MAX10`, so the installed set must never shrink the snapshot).
- The 223 stems are unique under `casefold()` [VERIFIED], so case correction can never be ambiguous.
- Existing libraries: list only symbol libraries whose name passes the verdict; this hides all v1 names (D-13) without a hard-coded list of 12 and also hides any hand-made `Atomic_MyStuff`. The live `Custom/Symbols` today has 13 `.kicad_sym` files (plus 3 `.bak`), none `Atomic_` [VERIFIED: `ls Custom/Symbols | grep -c`]; CONTEXT says 12 v1-named libraries, the extra one on disk is `LED_Cree`, so do not hard-code a count of 12.

### Pattern 4: New data on the existing plan contract
Change `plan.py`, not the dialog:
- `InstallOptions`: add `footprint_target` (`"shared"` or `"official"`), `official_footprint` (`"Lib:FP"` or None), `keywords`, `fp_description`, `fp_tags` (each `None` = generated). `value` stops being an override (Value := MPN always, D-22); `footprints` is a single name. Existing quote: `_TEXT_OVERRIDES = ("value", "datasheet", "description", "manufacturer", "mpn")` (plan.py:38).
- `InstallPlan`: add `footprint_library: str | None` (None when the symbol keeps an existing link only), `new_footprint_lib` stays, `linked_footprint` stays the footprint name, plus `footprint_link` (the exact `Lib:FP` string), the generated text, the "not used" names, and `atomic` violations. `new_library` today is `self.new_symbol_lib or self.new_footprint_lib` (plan.py:169) and `pretty_path` is `self.layout.footprints_dir / f"{self.library}.pretty"` (plan.py:177): both now describe two different libraries.
- `FieldChange` (plan.py:114-128): action is `drop | clean | rename`; add `set` (old -> new) for Value := MPN, `TI -> Texas Instruments`, and the replaced footprint description; add a scope so footprint changes are not filtered out by `pending = {state.final ...}` (planner.py:1183).
- `ToolContext` (plan.py:20-27) has `kicad_symbols_dir` and no footprints folder: add `kicad_footprints_dir` and the allowed-stems set; `detect_tools` (planner.py:285) fills them from `kicad_fp_dir`.

### Pattern 5: Incoming atomic check on planned bytes (D-21)
**What:** after the symbol and footprint bytes are final, call `atomic_check.check_symbol(root, name, rel_path=..., fixable=False, ctx=ctx)` for each symbol of the unit with an `AtomicContext` that knows the planned files. Run it on the edited unit root (`edited.root` in `render_symbols`), which already holds the chosen symbol plus any `extends` parents, so no second parse of the target library is needed.
- Seam (verbatim, atomic_check.py:351-359): `@dataclass(frozen=True) class AtomicContext: ... resolve_footprint: Callable[[str], FootprintTarget]` and `model_problems: Callable[[FootprintTarget], list[str]]`. `FootprintTarget(text, library, footprint, path, rel_path, problem)` (atomic_check.py:343-348).
- `repo_context` hides `model_path_problem` and the Custom model listing in closures, so the clean minimal change is to extend its signature, not copy it: `repo_context(repo_root, fp_libs, kicad_fp_dir, *, planned_footprints: Mapping[str, bytes] = {}, planned_models: Collection[str] = ())`. A planned `Lib:FP` resolves without being on disk; its `(model ...)` is judged from the planned bytes; `${CUSTOM_3DMODEL_DIR}/<file>` passes when `<file>` is in `planned_models` or already in `Custom/3DModels`. `check_symbol` and every rule stay untouched ("reuse unchanged"). Official footprints already work through `kicad_fp_dir` and `_KICAD_MODEL_RE = re.compile(r"\$\{KICAD\d+_3DMODEL_DIR\}/")` (atomic_check.py:33).
- Convert each `Violation` to an ERROR `Issue` with code `install.atomic.<rule>` (rules: `ATOMIC_RULES = ("mpn", "manufacturer", "footprint", "value", "datasheet", "description", "model_3d")`, atomic_check.py:22) so `apply_plan` still refuses a blocked plan (defence in depth) and the form maps code to target.
- Real-sample outcome on the current vendor files (before any user input) [VERIFIED by reading the parsed `PartMeta` and files with the repo's own adapters]:

| Sample | Rules that fail as-is | Fix in the dialog |
|--------|----------------------|-------------------|
| CSD85301Q2 | description (vendor has none); manufacturer unless inferred from `ti.com` as `Texas Instruments` | type a Description |
| ATXK-H14 | datasheet (`'ATXK-H14-D-32.768KHZ-E50-T3'` is not a link), manufacturer (no host to infer), model_3d (no model in package) | Datasheet, Manufacturer, Add 3D model... or official footprint |
| RS3-1212S/H3 | none expected (Manufacturer -> `RECOM`, Datasheet is a URL, Description present, model `RS3-1212S_H3.stp` present) | none |
| USB4145 | datasheet (empty), model_3d (separate download) | Datasheet, Add 3D model... with the SnapEDA model zip |

### Pattern 6: Footprint destination
- Default: shared library `Atomic_Footprints` under `layout.footprints_dir` (D-15). `pretty_exists` becomes "does `Atomic_Footprints.pretty` exist", the `mkdir` op is emitted only when absent, and the `install.pair_completed` WARNING block (planner.py:740-747) and the `sym_exists != pretty_exists` logic are deleted. `new_symbol_lib=not sym_exists` stays (planner.py:1190).
- Link = `f"{footprint_library}:{linked}"` where today `link = f"{library}:{linked}"` (planner.py:1049) and the first render uses `f"{library}:{fp_names[0]}"` (planner.py:879). Filters stay the footprint name.
- Official: link = the picked `Lib:FP`; no footprint or model op; vendor footprint and STEP become "Not used" preview rows (D-17); `kicad_cli.load_gate` then runs for the symbol library only (applier `_gate` passes `footprints=[]` when no footprint op exists).
- **Pad check (D-18)** reuses `verify.symbol_pin_numbers` / `footprint_pad_numbers` / `pin_pad_issues` (WARNING `verify.pin_pad_mismatch`, never blocking). For the CSD sample the symbol pins, the vendor footprint and `Package_SON:Texas_DQK` all give exactly `['1'..'8']` [VERIFIED: script using `verify.py` functions], so the official choice produces no warning there.
- `verify.verify_install` must become link-aware: `_linked_footprint` today hard-codes `expected = f"{plan.library}:{plan.linked_footprint}"` and looks the `.pretty` up in `plan.layout.footprints_dir` (verify.py:59-66); for an official link it must resolve in `tools.kicad_footprints_dir`, and skip the model-installed check (already skipped when `plan.model_file is None`).
- D-19 identical-footprint reuse: today `same=lambda name, digest: hashlib.sha256(render_fp(index, name)[0]).hexdigest() == digest` (planner.py:1014) compares bytes. Replace by comparing `sexpr.token_stream(parse(existing_text))` with the rendered text's stream (`token_stream` exists, sexpr.py:154; Phase 9 `changes.py` already uses it). Rename suggestion becomes `<FP>_<MPN>` instead of `suggest_free_name`'s `<FP>_2`. "Overwrite warns which other symbols link it": scan `Custom/Symbols/*.kicad_sym` bytes for `Atomic_Footprints:<FP>` (bytes prefilter, as `verify.find_name_elsewhere` does) and put the names in `Conflict.existing`.

### Pattern 7: Generated text, computed in the planner, shown by the dialog
- `keywords.generate_keywords(...)`, `footprint_text.describe(...)`, `footprint_text.tags(...)` are pure functions; the planner calls them when the matching option is `None` and records the result on the plan; the dialog fills unedited line edits from the plan (like `_set_field_texts`) and "Regenerate" clears the edited flag. An edit becomes an option override; the plan then carries exactly that text, so "installed files carry exactly what the preview showed" holds by construction.
- **Keywords (FLD-01, D-26, D-27)** in this order: vendor words (junk dropped), stem words of the chosen library (`Transistor_FET` -> `Transistor FET`), function and interface words found in description/category/keywords against a short curated vocabulary, package family and vendor package code, manufacturer aliases (aliases from the table plus the first word of the canonical name, e.g. `TI Texas`), MPN variants (raw MPN when it is not a substring of the symbol name: `RS3-1212S/H3` vs name `RS3-1212S_H3`), runner-up category words (alternative stems, raw vendor category), parent brand from `Manufacturer.owner`. De-duplicate case-insensitively, keep first spelling. KiCad weights each whitespace token of `ki_keywords` at 4 in the chooser (LIBRARY-NAMING §2), so every token must be a single word.
- **Pad geometry (D-28):** pitch = the smallest nearest-neighbour centre distance, rounded to 0.01 mm, that occurs at least twice; skip unnumbered pads and `np_thru_hole` (as `verify.footprint_pad_numbers` does). Verified results [VERIFIED: script using the repo's `kicad_files.load`]:

| Footprint | Pads | Pitch (algorithm) | Known truth | F.Fab bbox |
|-----------|------|-------------------|-------------|-----------|
| DQK0006B (UL) | 8 | 0.65 | 0.65 mm | 2.1 x 2.1 |
| ATXK-H14_ABR (UL) | 4 | 1.0 | n/a | 1.45 x 2.26 (looks partial) |
| RS3 (SamacSys, legacy `module`) | 7 | 2.54 | 2.54 mm SIP | 21.8 x 9.2 |
| GCT_USB4145... (SnapEDA) | 22 | 0.5 | USB-C 0.5 mm | 8.94 x 4.24 |
| `Package_SON:Texas_DQK` (stock) | 8 numbered | 0.65 | 0.65 mm | 2.0 x 2.0 |
| `Package_SO:SOIC-8_3.9x4.9mm_P1.27mm` (stock) | 8 | 1.27 | `P1.27mm` in its name | 3.9 x 4.9 |

  Body from the **F.Fab** outline: the stock SOIC-8 gives exactly its nominal 3.9 x 4.9, while its courtyard is 7.4 x 5.4 (clearance included), so the courtyard overstates; use courtyard only when no Fab outline exists.
- **Package family** cannot be computed from the footprint file. Sources, in order: the vendor footprint's own `descr`/`tags` words; the descr/name of the official footprint that the vendor package code matches (`Package_SON:Texas_DQK` has `descr "Texas WSON-6 DQK, ..."` and `tags "Texas WSON6 2x2mm"`); otherwise omit. A family regex over a closed list (SOIC, SSOP, TSSOP, MSOP, QFN, DFN, WSON, SON, LGA, BGA, QFP, SOT-23, ...) takes pin count from the matched text, not from the pad count (DQK has 8 numbered pads, the family is `WSON-6`). This is the only way the CONTEXT example "WSON-6 2x2 mm, 0.65 mm pitch, TI DQK0006B" can be reproduced; see Open Question 2 for the 2x2 vs 2.1x2.1 mismatch.
- **IPC name:** the true IPC-7351B long name (for example `WSON65P200X200X80-6`) needs the body height, which a footprint file does not hold, so it can never be built honestly. The recommended reading of D-28 is KiCad's own IPC-derived pattern (stock names such as `WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm`, `SOIC-8_3.9x4.9mm_P1.27mm`): `<Family>-<pins>_<W>x<H>mm_P<pitch>mm`, built only when the family is recognised (Assumption A6).
- **Inserting `(descr ...)` / `(tags ...)`:** replace the string token if the node exists, otherwise insert after the `(layer ...)` child with the file's own indent and eol, the way `kicad_files.model_insert_edit` inserts a zero-width `Edit`. Verified with the real tool: `kicad-cli 10.0.7 fp upgrade --force` loaded and kept `(descr ...)`/`(tags ...)` inserted after `(layer "F.Cu")` in the UL vendor footprint (root `footprint`, version 20211014) and in the SamacSys legacy `(module "RS3" (layer F.Cu) ...)` root; output was `(version 20260206)` with both nodes intact [VERIFIED: ran kicad-cli on scratch copies this session].

### Pattern 8: Official footprint picker (D-16)
- Index = `os.listdir` of `kicad_fp_dir` for `*.pretty` and each folder's `*.kicad_mod` names: 155 libraries, 15,464 footprints, 0.52 s [VERIFIED]. Build once on the open worker, cache in a module dict keyed by `(dir, count of entries, newest mtime)`.
- Ranking without reading files: score tokens of the footprint name against the vendor package code; match the **full code or its leading letters (3+)** as a token (`DQK0006B` -> `DQK` hits `Texas_DQK`, the only name containing `DQK` in all of KiCad 10 [VERIFIED]), plus family words. Read pad numbers lazily only for the top N (about 200) name candidates or for rows the user scrolls to; a full pad scan took 158 s for 165.7 MB [VERIFIED].
- Optional, cheap, strong: harvest each stock sibling symbol's `Footprint` value during the same index pass; the sibling `CSD16301Q2` links `Package_SON:Texas_DQK` [VERIFIED in `Transistor_FET.kicad_sym`], i.e. the exact answer for this package.
- Würth is never offered (D-16): the picker reads only `kicad_fp_dir`, never the repo. Without a KiCad install the "official" choice is disabled with a plain hint.

### Pattern 9: Library tables after install
`table_generator.add_library_entries(dest, nickname, sym_rel_path, fp_rel_path)` writes both entries under one nickname (table_generator.py:369) and `main_window._PostInstall` carries one `library`, one `new_library` and `fp_rel_path=plan.pretty_path.relative_to(root)` (main_window.py:815-824). Both must take two nicknames: `Atomic_<stem>` for `sym-lib-table` (when the symbol library is new) and `Atomic_Footprints` for `fp-lib-table` (first use only); each independently follows today's rule (added when absent, left alone when listed, `table.external_clash` otherwise). An official footprint adds no fp entry. `_apply_post_install_selection` and `reveal` already tolerate a missing path (`reveal` skips `None`).

### Pattern 10: Dialog changes (UI hint: yes)
- Library: editable `QComboBox` with `QCompleter` (`setFilterMode(Qt.MatchFlag.MatchContains)`, case-insensitive, `PopupCompletion`) over the combo's own model; existing `Atomic_` libraries, a separator (`insertSeparator`), then the remaining allowed `Atomic_<stem>`. Verified in-process: with `PySide6 6.12.0` `'fet'` matches 1 item and `'tor'` matches 3, and the separator row does not match [VERIFIED]. The current combo calls `setCompleter(None)` on purpose (comment: inline completion "would change its letter case"), so use popup mode, not inline. Connect the completer's own `activated` signal too (Assumption A10).
- Remove `_token_line`, `_token_hint`, `_TOKEN_HINT`, `library_tokens` (D-06); the tooltip carries the reason. Badge: `NEW_LIBRARY_BADGE = "new - creates .kicad_sym + .pretty"` (form.py:63) becomes a `.kicad_sym`-only text.
- Footprint single choice (D-14): replace the checklist (`_build_footprint_list`, `Make linked`, `_linked_fp`, `_set_linked`, `FormStatus.several_footprints/footprints_checked`) with the existing `_item_combo` pattern used for symbols and models; unselected footprints become "Not used" preview rows.
- Destination toggle + official picker + three line edits with Regenerate; Value row read-only.
- `_reason_targets["model"] = remove` (import_dialog.py:1457) points at the hidden Remove button; a missing-model reason needs the visible "Add 3D model..." button as its target, with the rejection reason keeping the Remove target under another key.
- The 5 field frames already exist for value/datasheet/description/manufacturer/mpn (`_framed(edit, name)`, import_dialog.py:919), so every atomic rule except footprint and model already has a frame and a focus target.

### Anti-Patterns to Avoid
- **Counting `(symbol "` text occurrences:** counts unit sub-symbols (`CSD..._1_1`). Use the depth-1 declaration pattern (tab or 1-2 spaces, as `verify._declaration_pattern`). This is why CONTEXT says 84 and the top-level count is 75.
- **Parsing KiCad's stock libraries with the S-expression parser:** `verify.find_name_elsewhere`'s docstring says it costs about a minute; use byte regex for the index.
- **Plurality voting on 3-4 letter manufacturer prefixes:** `MAX`, `LTC`, `INA`, `TPS` span many stems.
- **Putting the name rule only in the dialog.**
- **Copying `repo_context` internals** into a second context implementation; extend it.
- **Writing a vendor alias token (`TI`) as Manufacturer:** `form.field_defaults` and `planner` currently take `manufacturer_choice(meta).token`, which is a v1 library token (`Manufacturer("Texas Instruments", ("TI",), "TI")`, manufacturers.py:39).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| KiCad S-expression read/edit | regex edits of vendor text | `sexpr.parse`, `kicad_files` primitives, `Edit`/`apply_edits` | span-exact edits, caps already enforced |
| Atomic rules for the incoming part | a second rule set | `atomic_check.check_symbol` with an `AtomicContext` | D-21; one definition for scan, install, commit gate, migration |
| Canonical manufacturer spelling | alias dicts in the importer | `manufacturers.lookup` / `Manufacturer` | FLD-02; add `hosts` there, not in `suggest.py` |
| Footprint content equality | byte or hash compare | `sexpr.token_stream` | D-19 / Phase 9 D-21 |
| Pin/pad comparison | new comparison | `verify.symbol_pin_numbers`, `footprint_pad_numbers`, `pin_pad_issues` | D-18 is "the existing POST-04 check" |
| Writing files | `open(..., "w")` | `fsutil.atomic_write_*`, `applier.apply_plan` | atomic + backup transaction |
| KiCad load proof | own parser check | `kicad_cli.load_gate` | already runs `sym upgrade` and `fp upgrade` before any write |
| Substring-filter picker | custom list filtering | `QCompleter` + `MatchContains` | verified above |
| Rich-text safety in strip/tooltips | string concatenation | `html.escape` as `_render_strip` does | tooltips auto-detect rich text (T-07-34 precedent) |

**Key insight:** the phase adds almost no new mechanism. It adds data (stems, rules, vocabularies), five Qt-free pure functions (siblings, categories, keywords, footprint text, footprint index) and one extension point (`repo_context` planned files).

## Runtime State Inventory

Not a rename or migration phase: the 12 v1-named `Custom/` libraries stay on disk untouched until Phase 13 (CONTEXT, Phase Boundary). No stored data, live service config, OS registration, secret or build artifact carries a name this phase changes. The only carry-over: the sample test constants `CURRENT_CUSTOM_SYMBOL_LIBS` / `CURRENT_CUSTOM_FOOTPRINT_LIBS` in `tests/zipfixtures.py` hold v1 names and need Atomic counterparts (code edit, not data migration).

## Common Pitfalls

### Pitfall 1: Sibling counts include unit sub-symbols
**What goes wrong:** the CONTEXT's "84 CSD symbols in `Transistor_FET`" is `grep -o '(symbol "CSD[^"]*"' | sort -u` = 84; top-level symbols starting `CSD` are 75 (`Diode` has `CSD01060A`, `CSD01060E`). **Why:** unit symbols `NAME_1_1` also start with the prefix. **Avoid:** depth-1 pattern only; the tooltip must say 75 and tests must not hard-code 84. **Warning sign:** counts that disagree with the Symbol Editor's list.

### Pitfall 2: Plurality voting looks right on the headline sample and fails elsewhere
**What goes wrong:** CSD works either way, so a plurality implementation passes the success criterion but mis-files 21% of stock-like parts. **Avoid:** strict majority (> 50%) per D-03's wording; test it with a synthetic split family (for example `MAX4`) that must fall through.

### Pitfall 3: Allow-list drift between snapshot, category map and installed KiCad
**What goes wrong:** `Converter_DCDC_Isolated` is in KiCad 10 and absent in KiCad 9 (KiCad 9 also lacks `Driver`, `FPGA_Altera_MAX10`; KiCad 10 lacks `Driver_Haptic`, `Driver_Relay`, `Driver_TEC`, `MCU_WCH_CH32V0/V2/V3/X0`) [VERIFIED: stem diff of both installs]. **Avoid:** allow-list = snapshot union installed; unit-test the snapshot against a live KiCad 10 (skip when absent, `local_kicad`-style) and every category-map target against the snapshot.

### Pitfall 4: No `Crystal` stem
LIBRARY-NAMING §4 says "Passive crystals: `Crystal`". KiCad 10 has no such library [VERIFIED: stem list]. A map entry to `Crystal` would produce a name the rule refuses. Map to `Device` or do not map.

### Pitfall 5: Hidden coupling of "the footprint library is the symbol library"
Every one of these assumes one library name for both halves and must change together [VERIFIED by grep + reads]: `plan.pretty_path` (plan.py:177, preview.py:184, main_window.py:823), `plan.new_library` (plan.py:169, applier.py:31, commit_plan.py:145/206, main_window.py:638-644/820/827), `f"{plan.library}:{plan.linked_footprint}"` (preview.py:238, commit_plan.py:147, verify.py:59/131, import_dialog.py:1964), `add_library_entries` (table_generator.py:369), `verify._linked_footprint` (verify.py:54-76), the conflict key `footprint:{library}:{name.casefold()}` (planner.py:1023). Missing one leaves a stale `Atomic_<stem>:FP` link that `verify_install` reports as `verify.link_unresolved`.

### Pitfall 6: Manufacturer written as a library token
`manufacturer_choice` returns tokens (`TI`, `ADI`, `uBlox`) and planner/form write them when the vendor gave no Manufacturer. For the CSD sample the datasheet host `ti.com` currently yields `TI`. D-23 needs the canonical name, so move host knowledge into `manufacturers.py` (`hosts`), keep the aggregator-host guard from `suggest.py`, and note `HOST_TOKENS` maps `maximintegrated.com` and `linear.com` to token `ADI` while D-08 of Phase 9 says those keep their own canonical names.

### Pitfall 7: Pad-count scans on the GUI path
158 s cold for the whole stock footprint tree. Name index first; lazy reads only for the shortlist; cap each read with `MAX_KICAD_TEXT_BYTES` as other readers do.

### Pitfall 8: Description and Datasheet can never be generated
Three of four packages arrive without a usable Datasheet or Description. The gate blocks until the owner types them; do not invent values (atomic rule says "present", not "good", but fake text defeats the purpose). Provide clear reasons and focus targets instead.

### Pitfall 9: Tooltips auto-detect rich text
The code already documents this (`import_dialog.py` comment: a file name "must never reach a tooltip, which auto-detects rich text (T-07-34)"). The new library tooltip contains stem names and counts. Stems come from the snapshot or the owner's disk listing, so escape them or build the tooltip from `<p>` + `html.escape` as `_render_strip` does.

### Pitfall 10: Hidden Remove button used as the model focus target
See Pattern 10. `setFocus` on a hidden widget does nothing, so the click on a missing-model reason would appear dead.

### Pitfall 11: `field_defaults` must keep mirroring the planner
The docstring says `test_field_defaults_equivalence` proves equality with the planner. Value := MPN, canonical Manufacturer and the generated text change both sides; update both and keep the test.

### Pitfall 12: Footprint creation needs `Custom/Footprints`
`build_plan` already refuses to create a library when its parent folder is missing (`install.footprints_dir_missing`, planner.py:697-706); keep that check for `Atomic_Footprints.pretty`.

### Pitfall 13: Case twins of the shared footprint library
`build_plan` rejects a name differing from an existing library only by case (planner.py:679-687), comparing symbol and `.pretty` names together. After the change the symbol name can never equal `Atomic_Footprints`, but a hand-made `atomic_footprints.pretty` is possible: check the shared name against `list_footprint_libs` with `casefold` and refuse with the existing `install.library_case_clash` style message.

## Code Examples

Logic below was run as scripts in this session (stdlib only); names are illustrative.

### Family prefix and strict-majority pick
```python
# Source: leave-one-out experiment over C:/Program Files/KiCad/10.0/share/kicad/symbols (this session)
import re
from collections import Counter

def family_prefixes(part_number: str) -> list[str]:
    m = re.match(r"([A-Za-z]+)(\d+)?", part_number)
    if not m or len(m.group(1)) < 3:
        return []
    letters, digits = m.group(1), m.group(2) or ""
    steps = []
    if digits:
        steps.append(letters + digits)
        if len(digits) > 1:
            steps.append(letters + digits[0])
    steps.append(letters)
    return list(dict.fromkeys(steps))

def pick(counts_for_step: Counter, excluded: frozenset[str]):
    votes = Counter({lib: n for lib, n in counts_for_step.items() if lib not in excluded})
    total = sum(votes.values())
    if not total:
        return None, votes
    lib, n = votes.most_common(1)[0]
    return (lib if n * 2 > total else None), votes   # strict majority; votes feed the alternatives
```

### Stock index (names only, both indents)
```python
# Source: scratch script, 223 files / 22,905 symbols in 0.53 s warm (KiCad 9 first read: 2.91 s)
_TOP = re.compile(rb'(?:^|\n)(?:\t| {1,2})\(symbol "([^"]+)"')
def stock_names(path):          # path: one .kicad_sym; returns top-level symbol names
    return [m.group(1).decode("utf-8", "replace") for m in _TOP.finditer(path.read_bytes())]
```

### Pitch from pad centres
```python
# Source: verified on DQK0006B, ATXK-H14_ABR, RS3, GCT_USB4145, Texas_DQK, SOIC-8 (see Pattern 7)
import math
from collections import Counter

def pitch_mm(centres: list[tuple[float, float]]) -> float | None:
    if len(centres) < 2:
        return None
    nearest = [round(min(math.dist(a, b) for j, b in enumerate(centres) if j != i), 2)
               for i, a in enumerate(centres)]
    repeated = [d for d, n in Counter(nearest).items() if n >= 2]
    return min(repeated) if repeated else None
```

### Name verdict skeleton
```python
# Skeleton: stems = snapshot | installed, minus EXCLUDED_STEMS
def name_verdict(text, stems, existing):
    wanted = {("Atomic_" + s).casefold(): "Atomic_" + s for s in stems}
    exact = wanted.get(text.casefold())
    if exact == text:
        return True, text, ""
    if exact is not None:
        return True, exact, f"Spelling corrected to {exact}"       # D-11
    return False, text, reason_for(text, stems)                     # bare stem, excluded, invented token, v1, empty
```

### Completer on the library combo
```python
# Source: verified offscreen with PySide6 6.12.0 (matching only; popup activation not verified)
completer = QCompleter(combo.model(), combo)
completer.setFilterMode(Qt.MatchFlag.MatchContains)
completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
combo.setCompleter(completer)
completer.activated[str].connect(self._on_library_activated)   # in addition to combo.textActivated
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `<Type>_<SubCategory>_<Manufacturer>` library, 1:1 `.pretty` pairing (v1.0 LIB-01/02) | `Atomic_<official stem>` + one shared `Atomic_Footprints.pretty` | Owner decision 2026-10-25 | planner pair completion removed; two library nicknames per install |
| Library names guessed from manufacturer host tokens | Stock sibling family + category map + ask | this phase | `HOST_TOKENS`, `MANUFACTURER_ALIASES`, `token_map` leave the suggestion path |
| KiCad symbol format 20251024 and footprint format 20260206 | written by KiCad 10.0.7 itself | KiCad 10 | new footprints inserted as-is keep their vendor version; `fp upgrade` is a check, not a rewrite |
| KiCad 9 chooser searched every field | KiCad 10 searches only shown columns | KiCad 10 | keywords and Value carry the search; MPN/Manufacturer columns are TBL-02 (Phase 13) |

**Deprecated/outdated:** `Converter_DCDC` for isolated modules (KiCad 10 added `Converter_DCDC_Isolated`; the stock `Converter_DCDC` still holds RECOM `R-78…`); `Crystal` as a stem (does not exist).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "Majority wins" (D-03) means a strict majority (> 50%) of the matched siblings, with a split family falling through to the category map | Pattern 1 | If the owner meant plurality, more parts get a (less accurate) stock suggestion; trivial to flip, but UAT expectations change |
| A2 | D-02's shortening follows the example literally (full run, first digit, letters), not one digit at a time | Pattern 1 | Same results on all five samples; differs on other families |
| A3 | The reference-letter table (`J`,`P` -> Connector; `K` -> Relay; `SW` -> Switch; `TR` -> Transformer; `M` -> Motor; `JP` -> Jumper) and exclusion of `U`,`Q`,`D`,`X`,`Y` | Pattern 2 | A wrong letter mis-suggests a library (user can change); omitting `Y`/`X` makes ATXK-H14 ask |
| A4 | ATXK-H14 should "ask" rather than suggest `Atomic_Oscillator` | Pattern 1/2 | Owner may prefer `Atomic_Oscillator`; one extra rule |
| A5 | Existing hand-made `Atomic_` libraries that are not `Atomic_<stem>` are hidden from the picker and refused when typed | Pattern 3 | Owner could be surprised if such a library exists (none today) |
| A6 | "IPC name" = KiCad's IPC-derived name pattern `<Family>-<pins>_<W>x<H>mm_P<pitch>mm`, not the IPC-7351B long name | Pattern 7 | Owner may want the long name, which cannot be derived without body height |
| A7 | Body size prints at 0.1 mm resolution from the F.Fab outline (DQK: `2.1x2.1`), so the CONTEXT sentence "WSON-6 2x2 mm" will read `2.1x2.1 mm` unless the stock footprint's nominal `2x2mm` is used | Pattern 7 | Mismatch with the CONTEXT example text |
| A8 | Package family text is taken from vendor descr/tags or the matched official footprint's descr/name, else omitted | Pattern 7 | Without it the CSD sentence has no `WSON-6` |
| A9 | Allowed stems = KiCad 10 snapshot union installed stems | Pattern 3 | If only the snapshot is used, a future KiCad's new stems cannot be typed |
| A10 | `QCompleter` popup selection raises the combo's activation path on this setup | Pattern 10 | Picked names would not rebuild until the next edit; connect `completer.activated` explicitly and test with pytest-qt |
| A11 | Strict enforcement of the name rule and the atomic gate inside `build_plan` (tests migrated) rather than an opt-in policy | Summary, Open Q 6 | Opt-in leaves a bypass; strict costs roughly 240 `library=` edits plus about 250 v1-name mentions in tests |
| A12 | The curated function/interface vocabulary and the manufacturer-alias keyword rule (aliases + first word of the canonical name) | Pattern 7 | Keyword quality only; no blocking effect |
| A13 | Footprint `(descr)`/`(tags)` insertion position after `(layer)` is order-insensitive for KiCad on every vendor format | Pattern 7 | Verified for two roots with kicad-cli 10.0.7; other roots would be caught by the existing load gate |

## Open Questions

1. **Strict majority vs plurality (A1).**
   - Known: strict majority = 96.9% precise, 77% coverage on the stock leave-one-out; plurality = 79.1% precise. All five real samples behave the same either way.
   - Unclear: the owner's intent behind "majority wins".
   - Recommendation: implement strict majority; mention it in the plan so the discuss step can veto cheaply.

2. **Where does "WSON-6 2x2 mm" come from, and is it `2x2` or `2.1x2.1`?**
   - Known: the vendor footprint carries neither (`tags "CSD85301Q2 "`, no descr); its F.Fab box is 2.1 x 2.1; the stock `Package_SON:Texas_DQK` descr is `Texas WSON-6 DQK, ...` with tags `Texas WSON6 2x2mm`.
   - Recommendation: take the family from the matched stock footprint (A8), print the measured body at 0.1 mm, and let the owner edit the sentence; accept that the sample sentence will read `WSON-6 2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B` unless the nominal is preferred.

3. **Meaning of "IPC name" (A6).** Recommendation above; confirm with the owner before UAT.

4. **ATXK-H14 outcome (A4).** Recommendation: ask; add `Y`/`X` rules only if the owner wants Oscillator suggested on a bare reference letter.

5. **Hand-made non-stem `Atomic_` libraries (A5).** None exist; low risk.

6. **Strictness of `build_plan` vs test migration (A11).** About 240 `library=` sites (and about 250 v1-name mentions) across `test_install_plan` (76), `test_install_apply` (45), `test_import_dialog` (37), `test_install_e2e` (22), `test_import_form` (16), `test_import_preview` (13), `test_main_window_import` (10), `test_vendor_install` (7), `test_commit_plan` (7) and others use v1 or arbitrary names [VERIFIED: grep counts]. Recommendation: strict, with one plan wave for the mechanical migration (shared `ATOMIC_*` constants in the fixtures).

7. **SnapEDA category.** D-04 names a SnapEDA category, but no real SnapEDA sample provides one and the adapter does not set it. Build the hook, do not invent mappings (project rule: real samples first).

8. **UI contract.** `workflow.ui_phase` is true and the roadmap says "UI hint: yes", but the phase directory holds no UI-SPEC yet. A `/gsd-ui-phase` pass before planning would settle the destination toggle, the official picker layout and the three new edits.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| KiCad 10 install | stock siblings, footprint picker, 3D model check, real-tool tests | yes | 10.0.7 at `C:/Program Files/KiCad/10.0` | D-07 snapshot + category map; picker disabled |
| kicad-cli | load gate, symbol normalisation | yes | 10.0.7 | existing `install.cli_not_found` INFO path |
| KiCad 9 install | none (not a target) | yes | 9.0 present | n/a |
| Python venv | everything | yes | 3.14.4, PySide6 6.12.0, pytest 9.1.1 | n/a |
| git | commit step (Phase 6, unchanged) | yes | 2.49.0 | n/a |
| Real samples | acceptance tests | yes | five items in `downloaded_examples/` | tests skip when absent (existing pattern) |

**Missing dependencies:** none. The `ctx7` documentation CLI is not installed and no Context7 MCP tools were available; no external documentation was needed (all behaviour was verified locally).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-qt 4.5.0 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `pythonpath = ["."]`, `addopts = "-ra --strict-markers"`, markers `wurth`, `local_kicad`, `kicad_cli`) |
| Quick run command | `env/Scripts/python.exe -m pytest tests/<file>.py -q` |
| Full suite command | `env/Scripts/python.exe -m pytest` (about 18 minutes; `-m "not wurth"` about 8 minutes, per `tests/README.md`) |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIB-04 | family prefixes, strict majority, excluded stems, own-before-stock, category map, ask, no manufacturer name | unit (synthetic stock dir) | `env/Scripts/python.exe -m pytest tests/test_suggest_atomic.py -q` | ❌ Wave 0 |
| LIB-04 | CSD -> `Atomic_Transistor_FET` (75 vs 2), RS3 -> `Atomic_Converter_DCDC_Isolated`, ATXK asks, USB -> `Atomic_Connector` | real-sample, skips without KiCad 10 or the zip | `env/Scripts/python.exe -m pytest tests/test_real_vendor_samples.py -q` | ✅ retarget |
| LIB-04 | every category-map target is an allowed stem; snapshot equals installed KiCad 10 stems | unit + `local_kicad` | `env/Scripts/python.exe -m pytest tests/test_stems.py -q` | ❌ Wave 0 |
| LIB-05 | exact/case-corrected/refused names (`Transistor_FET`, `Atomic_TI`, v1 names, excluded stems), picker order and filter | unit + dialog | `env/Scripts/python.exe -m pytest tests/test_stems.py tests/test_import_dialog.py -q` | ❌ Wave 0 / ✅ migrate |
| LIB-06 | footprint in `Atomic_Footprints`, no `.pretty` for a new symbol library, official link, D-19 identical/overwrite/rename, tables | plan/apply/e2e | `env/Scripts/python.exe -m pytest tests/test_install_plan.py tests/test_install_apply.py tests/test_install_e2e.py tests/test_table_add_entries.py -q` | ✅ migrate |
| LIB-06 | pad check warning, verify with official link | unit | `env/Scripts/python.exe -m pytest tests/test_install_verify.py -q` | ✅ migrate |
| LIB-07 | incoming gate: one ERROR per rule, planned footprint/model seen, reasons with targets, live clear | plan + form + dialog | `env/Scripts/python.exe -m pytest tests/test_incoming_check.py tests/test_import_form.py tests/test_import_dialog.py -q` | ❌ Wave 0 / ✅ migrate |
| FLD-01 | keyword sources, merge/dedupe, junk dropped, MPN variants | unit | `env/Scripts/python.exe -m pytest tests/test_keywords.py -q` | ❌ Wave 0 |
| FLD-03 | pitch/body/family/description/tags on the 5 real footprints + stock SOIC-8/Texas_DQK, `descr`/`tags` insertion on `footprint` and `module` roots | unit + `kicad_cli` | `env/Scripts/python.exe -m pytest tests/test_footprint_text.py -q` | ❌ Wave 0 |
| all | layering for every new module | static | `env/Scripts/python.exe -m pytest tests/test_importer_layering.py tests/test_layering.py -q` | ✅ extend |

### Sampling Rate
- **Per task commit:** the single test file named in the task (seconds).
- **Per wave merge:** `env/Scripts/python.exe -m pytest -m "not wurth" -q` (about 8 minutes).
- **Phase gate:** full suite green with only the documented skips before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_stems.py`: snapshot vs installed KiCad 10 (skip without), name verdict table, category-map targets.
- [ ] `tests/test_suggest_atomic.py` and a **synthetic stock KiCad dir builder** (`tests/stockfixtures.py`: small `symbols/*.kicad_sym` and `footprints/*.pretty` trees) so no unit test depends on the installed KiCad.
- [ ] `tests/test_incoming_check.py`, `tests/test_keywords.py`, `tests/test_footprint_text.py`.
- [ ] Fixture migration: Atomic counterparts of `CURRENT_CUSTOM_SYMBOL_LIBS` / `CURRENT_CUSTOM_FOOTPRINT_LIBS` and an `Atomic_Footprints.pretty` in `write_custom_layout` (tests/zipfixtures.py).
- [ ] Register every new importer module in `ALLOWED` of `tests/test_importer_layering.py` and update `tests/test_layering.py` for `atomic_check` / `kicad_files` / `manufacturers` changes.
- [ ] Retarget `tests/test_naming_suggest.py` (459 lines, 32 tests) to the new API; keep the `datasheet_host` / `registered_domain` / `is_aggregator_host` tests.
- [ ] Update `tests/test_help_dialog.py` for the rewritten "Target library" and "Items" help text (`help_dialog.py` currently says the name is blocked while it contains `Type`, `SubCategory` or `Manufacturer`).
- [ ] Rebuild the UAT scratch builder expectation `PowerSupply_SubCategory_RECOM` -> `Atomic_Converter_DCDC_Isolated`.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | single-user desktop tool |
| V3 Session Management | no | n/a |
| V4 Access Control | no | local files only; writes stay inside `Custom/` via the existing `install.path_outside_custom` preflight |
| V5 Input Validation | yes | library names by allow-list (`Atomic_` + stem), footprint/model names by `sanitize_name`/`sanitize_filename`, official footprint pick validated against the exact-case index, vendor files under the 8 MiB / 1,000,000-node caps, generated text single-line |
| V6 Cryptography | no | SHA-256 for identity only (existing) |
| V12 Files and Resources | yes | stock libraries and footprints read-only with size caps; no execution of anything from a package; temp staging stays outside the repo |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal through a typed library or footprint name | Tampering | allow-list for library names; `sanitize_name` for footprints; exact-listing lookups before building a path (as `repo_context` does) |
| Rich-text / HTML injection through names reaching tooltips or the reason strip | Tampering | `html.escape` on every dynamic string; build tooltips from escaped parts |
| Resource exhaustion reading KiCad's 235 MB stock tree or 15k footprints | Denial of service | byte-regex index on a worker thread, cache, lazy pad reads with the existing byte cap |
| Malicious vendor footprint/symbol (huge, deeply nested) | Denial of service | existing `MAX_KICAD_TEXT_BYTES` / `MAX_KICAD_TEXT_NODES` parse caps (also apply to the new geometry reader) |
| Stale plan installed after inputs changed | Tampering | existing generation counter and `install.stale_plan` hash preflight; new options must flow through `InstallOptions` so a rebuild is triggered |
| Overwriting a shared footprint other parts link | Tampering | D-19 conflict row with the list of linking symbols; backup before write (existing) |

## Sources

### Primary (HIGH confidence)
- Local files read this session: `10-CONTEXT.md`, `REQUIREMENTS.md`, `STATE.md`, `research/LIBRARY-NAMING.md`, `09-CONTEXT.md`, `kicad_lib_manager/importer/{suggest,form,candidate,plan,planner,preview,verify,applier,layout,kicad_cli,fieldrules,naming,commit_plan}.py`, `kicad_lib_manager/{atomic_check,manufacturers,models,kicad_files,sexpr,table_generator,main_window}.py` (relevant ranges), `widgets/import_dialog.py`, `widgets/help_dialog.py`, `tests/{conftest,test_layering,test_importer_layering,test_real_vendor_samples,README}`, `pyproject.toml`, `requirements-dev.txt`, `.planning/config.json`, `ROADMAP.md` Phase 10/13.
- Scripts run this session (scratchpad, `py -I`) over `C:/Program Files/KiCad/10.0/share/kicad/{symbols,footprints,3dmodels}` and the five samples: stem list and diff vs KiCad 9, sibling counts, leave-one-out precision, reference-letter distribution, footprint index and pad-scan timing, pitch/body geometry, pin/pad numbers of vendor vs `Texas_DQK`.
- `kicad-cli 10.0.7 fp upgrade --force` on scratch copies with inserted `(descr)`/`(tags)` (roots `footprint` and legacy `module`).
- PySide6 6.12.0 offscreen run of `QCompleter` with `MatchContains` on a combo model.

### Secondary (MEDIUM confidence)
- KiCad chooser search weights quoted from `research/LIBRARY-NAMING.md` §2 (the project's own earlier source-reading of the KiCad source); not re-verified against the KiCad source in this session.

### Tertiary (LOW confidence)
- None used.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, nothing new is installed; versions read from the environment.
- Architecture: HIGH for the seams (every coupling point was read), MEDIUM for the new dialog layout until a UI-SPEC exists.
- Pitfalls: HIGH, each is backed by a measurement or a read of the code.
- Heuristics (category rules, reference letters, vocabularies, IPC name): MEDIUM, listed in the Assumptions Log.

**Research date:** 2026-10-26
**Valid until:** 2026-11-25 for the code seams (repo changes only through this milestone's phases); the KiCad-10-specific counts stay valid until KiCad 10 is updated (re-run the scripts if the install changes).

## Appendix A: KiCad 10.0.7 symbol-library stems (223) [VERIFIED: directory listing and top-level symbol scan]

Excluded by D-10 (6): `power`, `Simulation_SPICE`, `Graphic`, `Connector_Generic`, `Connector_Generic_MountingPin`, `Connector_Generic_Shielded`. Allowed: the other 217. Longest stem is 29 characters, so `Atomic_` + stem is at most 36 characters (limit `MAX_NAME_LEN = 64`, naming.py:10).

```
4xxx 4xxx_IEEE 74xGxx 74xx 74xx_IEEE Amplifier_Audio Amplifier_Buffer Amplifier_Current Amplifier_Difference
Amplifier_Instrumentation Amplifier_Operational Amplifier_Video Analog Analog_ADC Analog_DAC Analog_Switch
Audio Auxiliary_Items Battery_Management Buffer Comparator Connector Connector_Audio Connector_Generic
Connector_Generic_MountingPin Connector_Generic_Shielded Converter_ACDC Converter_DCDC Converter_DCDC_Isolated
CPLD_Altera CPLD_Microchip CPLD_Renesas CPLD_Xilinx CPU CPU_NXP_6800 CPU_NXP_68000 CPU_NXP_IMX CPU_PowerPC
Device Diode Diode_Bridge Diode_Laser Display_Character Display_Graphic Driver Driver_Display Driver_FET
Driver_LED Driver_Motor DSP_AnalogDevices DSP_Freescale DSP_Microchip_DSPIC33 DSP_Motorola DSP_Texas
Fiber_Optic Filter FPGA_Altera_MAX10 FPGA_CologneChip_GateMate FPGA_Efinix_Trion FPGA_Lattice FPGA_Microsemi
FPGA_Xilinx FPGA_Xilinx_Artix7 FPGA_Xilinx_Kintex7 FPGA_Xilinx_Spartan6 FPGA_Xilinx_Virtex5
FPGA_Xilinx_Virtex6 FPGA_Xilinx_Virtex7 GPU Graphic Interface Interface_CAN_LIN Interface_CurrentLoop
Interface_Ethernet Interface_Expansion Interface_HDMI Interface_HID Interface_LineDriver Interface_Optical
Interface_Telecom Interface_UART Interface_USB Isolator Isolator_Analog Jumper LED Logic_LevelTranslator
Logic_Programmable MCU_AnalogDevices MCU_Cypress MCU_Dialog MCU_Espressif MCU_Intel MCU_Microchip_8051
MCU_Microchip_ATmega MCU_Microchip_ATtiny MCU_Microchip_AVR MCU_Microchip_AVR_Dx MCU_Microchip_PIC10
MCU_Microchip_PIC12 MCU_Microchip_PIC16 MCU_Microchip_PIC18 MCU_Microchip_PIC24 MCU_Microchip_PIC32
MCU_Microchip_SAMA MCU_Microchip_SAMD MCU_Microchip_SAME MCU_Microchip_SAML MCU_Microchip_SAMV MCU_Module
MCU_Nordic MCU_NXP_ColdFire MCU_NXP_HC11 MCU_NXP_HC12 MCU_NXP_HCS12 MCU_NXP_Kinetis MCU_NXP_LPC
MCU_NXP_MAC7100 MCU_NXP_MCore MCU_NXP_NTAG MCU_NXP_S08 MCU_Parallax MCU_Puya MCU_RaspberryPi
MCU_Renesas_Synergy_S1 MCU_SiFive MCU_SiliconLabs MCU_ST_STM32C0 MCU_ST_STM32F0 MCU_ST_STM32F1 MCU_ST_STM32F2
MCU_ST_STM32F3 MCU_ST_STM32F4 MCU_ST_STM32F7 MCU_ST_STM32G0 MCU_ST_STM32G4 MCU_ST_STM32H5 MCU_ST_STM32H7
MCU_ST_STM32L0 MCU_ST_STM32L1 MCU_ST_STM32L4 MCU_ST_STM32L5 MCU_ST_STM32MP1 MCU_ST_STM32U0 MCU_ST_STM32U5
MCU_ST_STM32WB MCU_ST_STM32WL MCU_ST_STM8 MCU_STC MCU_Texas MCU_Texas_MSP430 MCU_Texas_SimpleLink MCU_Trident
MCU_WCH_RiscV Mechanical Memory_EEPROM Memory_EPROM Memory_Flash Memory_NVRAM Memory_RAM Memory_ROM
Memory_UniqueID Motor Oscillator Potentiometer_Digital power Power_Management Power_Protection
Power_Supervisor Reference_Current Reference_Voltage Regulator_Controller Regulator_Current Regulator_Linear
Regulator_SwitchedCapacitor Regulator_Switching Relay Relay_SolidState RF RF_AM_FM RF_Amplifier RF_Bluetooth
RF_Filter RF_GPS RF_GSM RF_Mixer RF_Module RF_NFC RF_RFID RF_Switch RF_WiFi RF_ZigBee Security Sensor
Sensor_Audio Sensor_Current Sensor_Distance Sensor_Energy Sensor_Gas Sensor_Humidity Sensor_Magnetic
Sensor_Motion Sensor_Optical Sensor_Pressure Sensor_Proximity Sensor_Temperature Sensor_Touch Sensor_Voltage
Simulation_SPICE Switch Timer Timer_PLL Timer_RTC Transformer Transistor_Array Transistor_BJT Transistor_FET
Transistor_FET_Other Transistor_IGBT Transistor_Power_Module Triac_Thyristor Valve Video
```

## Appendix B: Layering registrations the plan must not forget

Quote (tests/test_importer_layering.py, ALLOWED excerpt): `"importer.suggest": {"models", "manufacturers", "importer.candidate", "importer.naming"},` and `"importer.planner": {... "importer.suggest", "importer.adapters.base", "importer.kicad_cli", "importer.verify", "importer.fieldrules",},`. A new module that is not a key fails with `not registered in ALLOWED`; a relative import not listed fails with `imports <target>, which its ALLOWED entry forbids`. So: `importer.planner` needs `manufacturers`, `atomic_check`, `importer.stems`, `importer.keywords`, `importer.footprint_text`, `importer.incoming`; `importer.form` needs `importer.stems`; `importer.incoming` needs `atomic_check`, `kicad_files`, `models`, `importer.plan`. In `tests/test_layering.py`, quote: `"atomic_check": {"models", "fsutil", "kicad_files", "sexpr", "manufacturers", "importer"},` already allows `importer`; `table_generator` is `{"fsutil", "kicad_files", "models", "sexpr"}`, so `add_library_entries` may not import from `importer`. The subprocess test `test_foundation_modules_load_no_qt` imports the foundation modules in `-I` mode; keep every new module Qt-free.
