# Library naming, classification and search: research and decisions

**Date:** 2026-10-23
**Status:** decisions taken by the owner, input for the next phase (library naming / atomic migration)
**Replaces:** the `<Type>_<SubCategory>_<Manufacturer>` convention in `CLAUDE.md` and the 1:1 symbol/footprint library pairing in LIB-01/LIB-02

This research was read-only. Sources:
- the KiCad source (branches `9.0`, `10.0`, `master` on gitlab.com/kicad/code/kicad);
- the KiCad 10 install;
- the Würth GitHub repo;
- 16 public atomic libraries and practitioner write-ups;
- the owner's `kipart-search` tool.

---

## 1. Decisions (owner, 2026-10-23)

| Topic | Decision |
|---|---|
| Nickname scheme | **Option A**: `<official KiCad symbol-library stem>_<token>`, function first and source last |
| Token | **MecaFrog**. The owner typed "Mecafrog"; their brand elsewhere is "MecaFrog". **Confirm the capitalisation before any rename.** |
| Footprints | One shared footprint library named by the token alone (`MecaFrog.pretty`). Use an official KiCad footprint instead when its land pattern matches the datasheet. |
| Symbol ↔ footprint libraries | 1:1 library pairing **dropped**. Each symbol stays locked to exactly one footprint. |
| Third-party sources | Keep upstream names and layout untouched (Würth). Enable only the series actually used. |
| Folders | One top-level folder per source. Third-party sources are submodules in upstream layout; own parts use `Symbols/`, `Footprints/`, `3DModels/`. Optional manufacturer subfolders under `3DModels/` only. |
| Variants | One derived symbol (`extends`) per **electrically different** variant (output voltage, fixed vs adjustable, pinout). None for packaging or reel suffixes. A generic symbol with the MPN filled per project is acceptable for rarely used parts (e.g. `ATXK-H14`). |
| Rejected | `_Custom` / `Custom_` token (unattractive); manufacturer folders or tokens for own parts; distributor categories; database or HTTP libraries for now; KiCad 10 nested tables for now |

---

## 2. How KiCad's chooser search works (verified in source)

**Query handling** (`common/lib_tree_model.cpp`, `LIB_TREE_NODE_ITEM::UpdateScore`):
- The query is lower-cased and split on whitespace into at most 100 words.
- **Every word must match** some term of the item (AND logic). One miss scores the item 0.

**Matchers per word** (`common/eda_pattern_match.cpp`, `EDA_COMBINED_MATCHER`):
- regex, only when the word is `/…/` or `^…$`;
- wildcards `*` and `?`;
- relational `key<op>value` (`< <= = >= >`), with SI multipliers p n u m k meg g t;
- plain substring as the fallback.

There is no `lib:` or field-filter syntax. Typing `Nick:` still filters to a library, because `Nick:Name` is itself a search term.

**Scoring per term** (`ScoreTerms`):
- the whole term equals the word: 8 × weight;
- the word is found at position 0: 2 × weight;
- found elsewhere: 1 × weight.

KiCad 10 and master add an exact-match tier: an item whose name or `Nick:Name` equals the query ranks first.

**Symbol search terms** (`eeschema/lib_symbol.cpp`, `GetSearchTerms`):

| Term | Weight |
|---|---|
| `Nick:Name` | 16 |
| symbol name | 8 |
| library nickname | 4 |
| each whitespace token of `ki_keywords` | 4 |
| whole keywords string | 1 |
| Description | 1 |
| Footprint field | 1 |

The library table `descr` is **not** searched.

**Custom fields (MPN, Manufacturer, …):**
- **KiCad 9.0:** every field is searched at weight 4. That includes SnapEDA leftovers.
- **KiCad 10 and master:** a field is searched **only while it is shown as a chooser column** (`RebuildSearchTerms(aShownColumns)`).
  - The column choice persists in `eeschema.json` → `lib_tree.columns`.
  - Default columns are Item, Description and Value, so **Value is searchable by default and MPN is not**.
  - Column names are case-sensitive. The owner's config currently has a stray SnapEDA `MANUFACTURER` column.
- **Action:** show the `MPN` and `Manufacturer` columns once, and remove `MANUFACTURER`.

**Footprint search terms** (`pcbnew/footprint.cpp`):

| Term | Weight |
|---|---|
| `Nick:Name` | 16 |
| footprint name | 8 |
| library nickname | 4 |
| each `tags` token | 4 |
| whole tags string | 1 |
| `descr` | 1 |

Custom fields are not searched.

**Sorting and grouping:**
- Order is "Recently Used", then pinned libraries, then score (best-match mode), then natural alphabetical order.
- Pins are stored per nickname in `kicad_common.json` → `session.pinned_symbol_libs` / `pinned_fp_libs`.
- The table `descr` fills the library row's Description column, which helps browsing only.

**KiCad 10 nested tables:**
- `LIBRARY_MANAGER::Rows()` flattens them, so there is no group node in the chooser.
- A duplicate nickname is silently shadowed.
- Fixes landed in 10.0.1, 10.0.5 and 10.0.7, and KiCad 9 and earlier cannot read them.
- **Do not rely on them** while KiCad below 10 is supported.

**Database libraries** (`.kicad_dbl`, ODBC):
- Rows point at existing `Lib:Symbol` / `Lib:Footprint` entries.
- They give one chooser node per category across sources, plus parametric columns.
- Costs:
  - a SQLite ODBC driver on every machine;
  - a binary database in git;
  - placed parts link to the database, so renaming a key breaks links;
  - parts appear twice unless the file libraries are hidden.
- **Verdict: later**, and only for atomic passives at scale. kipart-search is the better home if it ever happens.
- HTTP libraries need a server: **never** for a single-user repo.

---

## 3. What real atomic libraries do (16 sources surveyed)

| Library | Nickname scheme | Categories | Classification | Footprints |
|---|---|---|---|---|
| Digi-Key (unmaintained) | `dk_<Family>` prefix | ~150, fine | Copies the Digi-Key family tree | one shared `.pretty` |
| SparkFun (active) | `SparkFun-<Cat>` | 30, coarse | Own buckets; "IC-Power" became a grab-bag | 24 category libraries |
| CDFER JLCPCB (active) | `JLCPCB-<Cat>` | 20, coarse | Copies the LCSC Category field | one shared `.pretty` |
| Olimex / Seeed OPL | `OLIMEX_` / `OPL_` prefix | 13–15, coarse | Coarse buckets | category libraries |
| Alternate KiCad Library | `<KiCad stem>_AKL` **suffix** | 39 | Mirrors KiCad names | package-family libraries |
| Würth | `<Function>_Wurth_<Series>` | 396 (per series) | Product type, then series | 43 `<Function>_<SMD\|THT>_Wurth` |
| azonenberg | `<cat>-azonenberg` | 18 | Mixes function and vendor | one shared `.pretty` |
| Espressif / Tinkerforge / Antmicro | one brand library | 1 | None; search does the work | one shared |
| CERN | plain names inside a database namespace | 31 | Inherited from Altium | package class |
| latke.net blog | `asp_` prefix | 7 | House part numbers | category libraries |

**Patterns observed:**
- A brand or initials token on every library: **16 of 16**. Prefix 8, suffix 3, one brand library 3, namespace 1.
- Footprints are **never** paired 1:1 with symbol libraries.
- Classification is almost always **copied from a reference tree**, not invented.
- Community libraries keep categories coarse.
- **Lesson:** renaming breaks old designs ("stuck with your own legacy"). Migrate **once**, never split finer than KiCad does, and put fine distinctions in keywords.

---

## 4. Classification rule (mechanical)

**Classify by what the device is (construction and primary electrical function), never by application or the manufacturer's marketing tree.**

Example: TI lists the CSD85301Q2 under "Power management". That is a product line. The part itself is a dual N-MOSFET, so it goes to `Transistor_FET`.

Take the first match:
1. **Sibling lookup.** If the same family or MPN prefix exists in the installed KiCad symbol libraries, use that library. The importer can automate this via `kicad_cli.stock_symbols_dir`.
2. **Construction rules:**
   - Discrete semiconductors (single or arrays, no control logic): `Transistor_FET`, `Transistor_BJT` or `Diode`, even when marketed as "power management".
   - Complete converter modules (regulated output, magnetics inside): `Converter_DCDC_Isolated` if isolated, else `Converter_DCDC` (or `Converter_ACDC`).
   - Regulator IC needing an external inductor, and multi-rail PMICs: `Regulator_Switching`. Controllers driving external FETs: `Regulator_Controller`. Linear regulators: `Regulator_Linear`.
   - Battery-specific ICs (charger, fuel gauge, protector): `Battery_Management`.
   - ICs that switch or control power without regulating it (load switch, ideal diode, power mux, push-button on/off, gate driver plus FET stage): `Power_Management`. eFuses and surge protectors: `Power_Protection`. Supervisors: `Power_Supervisor`. Bare gate drivers: `Driver_FET`.
   - Sensors, by what they measure: `Sensor_Motion`, `Sensor_Magnetic`, `Sensor_Temperature`, and so on.
   - Certified radio modules: `RF_Module`. Bare radio chips by protocol: `RF_Bluetooth`, `RF_WiFi`, `RF_GPS`.
   - Timing parts with an active output (XO, TCXO, VCXO, MEMS): `Oscillator`. Passive crystals: `Crystal`.
   - Connectors: `Connector`.
3. **Tie-break.** Map the distributor category (Digi-Key, LCSC, SamacSys "Power Supply") to a KiCad stem.
4. **Make a wrong guess harmless.** Put the alternative category words, including the manufacturer's marketing category, into `ki_keywords`. Search ignores library boundaries.

---

## 5. Target libraries for the current Custom parts

| Part | Current library | Target library |
|---|---|---|
| GCT FFC2A32-06-T, MEM2085-00-115-00-A, USB4056-03-A, USB4730-GF-A, USB4745-03-A | Connector_FFC_GCT, Connector_MicroSD_GCT, Connector_USB_GCT | `Connector_MecaFrog` |
| TI BQ25180 (charger) | IC_Battery_Charger_TI | `Battery_Management_MecaFrog` |
| ADI MAX17048 (fuel gauge) | IC_Battery_Fuel_Gauge_ADI | `Battery_Management_MecaFrog` |
| ADI LTC2954 (push-button on/off) | IC_Button_Controller_ADI | `Power_Management_MecaFrog` |
| TDK ICM-42688-P (IMU) | IC_IMU_TDK | `Sensor_Motion_MecaFrog` |
| Memsic MMC5983MA (magnetometer) | IC_Magnetometer_Memsic | `Sensor_Magnetic_MecaFrog` |
| TI CSD85301Q2 (dual N-MOSFET) | IC_PowerManagementMosfet_TI | `Transistor_FET_MecaFrog`, keywords `power-management half-bridge dual-nmos` |
| u-blox NORA-W106 (Wi-Fi/BLE module) | IC_Wireless_BLE_uBlox | `RF_Module_MecaFrog`, keywords `wifi ble esp32-s3` |
| Abracon ATXK-H14 (32.768 kHz TCXO) | Oscillator_TCXO_Abracon | `Oscillator_MecaFrog` |
| RECOM RS3-1212S/H3 (isolated 3 W module) | RECOM_DCDC_converters | `Converter_DCDC_Isolated_MecaFrog` |
| two `.bak` libraries | — | delete |

That is 12 symbol libraries reduced to 9. All 11 `.pretty` folders go into `MecaFrog.pretty`, or to official footprints after a datasheet check (candidates: TSOT-23-8/DFN-8 for LTC2954, LGA-16 for MMC5983MA, DSBGA-8 for BQ25180).

---

## 6. Fields, keywords and atomic rules

**Fields:**
- Canonical names match kipart-search, which writes exactly `MPN`, `Manufacturer`, `Datasheet`, `Description` (`gui/assign_dialog.py`).
- kipart-search reads these MPN aliases: mpn, manf#, mfr part, part number, pn. Manufacturer aliases: manufacturer, mfr, mfg, manf, vendor.
- SnapEDA `MF`/`MP` are invisible to it. Würth's `Part Number` is recognised.
- No price, stock or distributor-number fields in libraries.

**Symbol:**
- Symbol name = sanitised MPN; Value = MPN, for ICs, connectors and modules.
- A canonical manufacturer-name table is needed (e.g. "GCT" vs "Global Connector Technology").

**`ki_keywords`** (each token weighs 4):
- function words and synonyms;
- interfaces;
- package and vendor package codes;
- manufacturer aliases (`TI Texas`, `ADI Analog Maxim Linear`, `TDK InvenSense`, `u-blox ublox`);
- MPN variants that are not substrings of the name;
- optional relational tokens such as `Vout=12 Viso=3k` (multiplier only, no unit letter).

**Description:** a full sentence with the key specs.

**Footprints:**
- `descr` plus `tags` with the package name, IPC name, vendor package code and pitch.
- IPC-7351 zero orientation (pin 1 top-left).
- A pin-1 marker on silkscreen and fab.

**Variants:** derived symbols, as in KiCad's own `Regulator_Linear` (`MIC5504-1.8YM5 (extends "MIC5504-3.3YM5")`, `AP2112K-1.2/1.8/2.5/3.3`).

**Gaps found in the existing 19 symbols:**
- Only 2 have a canonical Manufacturer + MPN pair.
- 15 have an empty Datasheet, 7 an empty Description, and only 4 have keywords.
- LTC2954 has Value ≠ MPN.
- `_REVx` suffixes appear in connector names.
- 7 symbols carry SnapEDA leftovers.

**ATXK-H14:** fixed in quick tasks 261023-ptg and 261023-qf7. The mirrored pads were corrected and then rotated to IPC orientation; the result is confirmed identical to Ultra Librarian's `ATXK-H14_ABR`. It still has no 3D model.

**Lesson:** vendor and hand-made footprints can be mirrored. The importer should check pad 1 against the datasheet top view.

---

## 7. Implementation impact (next phase)

**Importer** (`kicad_lib_manager/importer/`):
- **`suggest.py`:**
  - suggest `<stem>_MecaFrog` from the installed KiCad library vocabulary (`kicad_cli.stock_symbols_dir`);
  - sibling lookup, then a distributor-category map, then ask;
  - drop the manufacturer token and its 3× rank weight;
  - remap `PART_CATEGORY_TYPE` (e.g. PS → `Converter_DCDC`, or `_Isolated` when "isolat" appears).
- **`planner.py`:**
  - send footprints to the shared `MecaFrog` library (LIB-02 pair completion around lines 741–747, conflict key around line 1023);
  - write canonical fields, Value = MPN, generated keywords, and footprint `descr`/`tags`.
- **`form.py`:** footprint-library field.
- **Warnings:**
  - empty Datasheet or Description;
  - name equals an official KiCad nickname;
  - token is a manufacturer name;
  - pad-1 orientation.
- **Tests affected:** test_install_plan, test_install_apply, test_install_e2e, test_vendor_install, test_import_form, test_import_dialog, test_import_preview, and `zipfixtures.py:295`.
- **Phase 7 UAT expectation:** the suggestion `PowerSupply_SubCategory_RECOM` changes to `Converter_DCDC_Isolated_MecaFrog`.

**Table generator** (`table_generator.py`):
- write a library `descr` (currently `(descr "")`);
- optional "pin my libraries" action writing `session.pinned_symbol_libs` (with backup, like the path-variable sync);
- keep refusing nickname clashes;
- no nested tables.

**Docs:** update the `CLAUDE.md` naming section, LIB-01/LIB-02 in REQUIREMENTS.md, and PROJECT.md.

**Migration:**
1. Do the importer and generator phase first.
2. Tag `Custom` as `pre-atomic`.
3. One scripted, previewed Custom commit: merge into 9 libraries, move footprints, rewrite Footprint fields, normalise fields and keywords, delete the `.bak` files.
4. Regenerate the tables.
5. In KiCad 10, show the `MPN` and `Manufacturer` columns.
6. Existing projects keep working from their embedded copies. Relink with Edit Symbol Library Links, then Update Symbols, then Update PCB.

---

## 8. Sources

- KiCad source: [lib_tree_model.cpp](https://gitlab.com/kicad/code/kicad/-/blob/master/common/lib_tree_model.cpp), [eda_pattern_match.cpp](https://gitlab.com/kicad/code/kicad/-/blob/master/common/eda_pattern_match.cpp), [lib_symbol.cpp](https://gitlab.com/kicad/code/kicad/-/blob/master/eeschema/lib_symbol.cpp), [footprint.cpp](https://gitlab.com/kicad/code/kicad/-/blob/master/pcbnew/footprint.cpp), [library_manager.cpp (10.0)](https://gitlab.com/kicad/code/kicad/-/blob/10.0/common/libraries/library_manager.cpp)
- KiCad docs: [Schematic Editor 9.0 (database and HTTP libraries)](https://docs.kicad.org/9.0/en/eeschema/eeschema.html); [KLC](https://klc.kicad.org/) (G1.3, G2.1, S6.2), [KLC source](https://gitlab.com/kicad/libraries/klc)
- Libraries: [Digi-Key](https://github.com/Digi-Key/digikey-kicad-library), [SparkFun](https://github.com/sparkfun/SparkFun-KiCad-Libraries), [CDFER JLCPCB](https://github.com/CDFER/JLCPCB-Kicad-Library), [Alternate KiCad Library](https://github.com/DawidCislo/Alternate-KiCad-Library), [Würth](https://github.com/WurthElektronik/KiCad-Library), [Antmicro](https://github.com/antmicro/hardware-components), [CERN](https://gitlab.com/ohwr/cern-kicad-libs), [Ki-nTree](https://github.com/sparkmicro/Ki-nTree), [Olimex](https://github.com/OLIMEX/KiCAD), [azonenberg](https://github.com/azonenberg/kicad-libraries)
- Practitioners: [KiCad forum: library organisation](https://forum.kicad.info/t/ideas-for-library-organization/40633), [atomic or not](https://forum.kicad.info/t/atomic-or-not-what-are-you-doing-with-kicad/5673), [naming standards](https://forum.kicad.info/t/standards-for-naming-components-in-libraries/19077), [latke.net asp_ library](https://www.latke.net/asp_digital/?p=53), [Altium: types vs folders](https://resources.altium.com/p/component-types-verses-folders)
- Parts: [TI CSD85301Q2](https://www.ti.com/product/CSD85301Q2), [Abracon ATXK-H14 datasheet](https://abracon.com/datasheets/ATXK-H14.pdf)
- Local:
  - `C:/Program Files/KiCad/10.0/share/kicad/symbols` (sibling placements, `extends` usage)
  - `%APPDATA%/kicad/10.0/eeschema.json` (`lib_tree.columns`)
  - `%APPDATA%/kicad/10.0/kicad_common.json` (`session.pinned_*`)
  - kipart-search `src/kipart_search/core/models.py`, `core/merge.py`, `gui/assign_dialog.py`
