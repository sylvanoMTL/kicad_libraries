# Phase 3: Package Intake and Naming - Context

**Gathered:** 2026-10-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 3 builds the headless (Qt-free) front end of the importer. It takes a vendor `.zip` or a folder of loose files, stages only the KiCad and 3D files in a temp folder outside the repo, and finds the KiCad v6+ symbol, footprint(s) and 3D model(s). It rejects KiCad 5-only and hostile packages, and proposes a sanitised `<Type>_<SubCategory>_<Manufacturer>` target library name. Nothing is written into the repo.

Requirements: INTK-01, INTK-02, INTK-05, INTK-06, LIB-01, LIB-03 (see `.planning/REQUIREMENTS.md`). Not in this phase: the import dialog and preview (Phase 5), choosing which of several candidates to import (INTK-07, Phase 5), installing or creating libraries (Phase 4), and the SnapEDA/CSE adapters (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Carried forward (locked)
- Services return `Issue(severity, code, text)` lists and do not raise for expected failures (Phase 1 D-07). Severity routing is by `Severity`, not by message substrings (Phase 2).
- `downloaded_examples/ul_CSD85301Q2.zip` is committed in the parent repo and is the primary fixture. Tests read it from its committed location and never extract it into the repo (Phase 1 D-04). `downloaded_examples` and `tests` are in the scanner's `SKIP_DIRS`.
- Decoding: strict UTF-8 with BOM preserved, and an `Issue` on invalid UTF-8 (Phase 1 D-11, via `fsutil.decode_source` / `kicad_files.parse_bytes`).
- Stdlib only: `zipfile`, `tempfile`, `unicodedata`, `urllib.parse`. No new runtime dependency.
- The importer writes the `Manufacturer` and `MPN` property names. Existing `MF` / `MP` / `MANUFACTURER` fields are read but never migrated (STATE.md).

### Library name suggestion (LIB-01)
- **D-01:** Type and SubCategory are a **best guess with a confidence flag**. The guess comes from the symbol's Reference prefix (`U`→`IC`, `Q`→`Transistor`, `J`/`P`→`Connector`, `Y`/`X`→`Oscillator`, `C`→`Capacitor`, `L`→`Inductor`, `D`→`Diode`, `R`→`Resistor`, …). It is refined by matching the description, `ki_keywords` and Value against tokens already used in `Custom/` library names. If nothing beyond the prefix matches, the suggestion is marked **low confidence**, so the Phase 5 preview can highlight it. Do not just reuse an existing library with the same manufacturer suffix as the suggestion (that would give `IC_Battery_Charger_TI` for the UL MOSFET).
- **D-02:** The manufacturer token comes from, in order:
  1. a Manufacturer-like property in the symbol (`Manufacturer`, `MF`, `MANUFACTURER`, `Manufacturer_Name`), mapped to a token;
  2. the datasheet URL host, mapped through a **small built-in host→token table** (e.g. `ti.com`→`TI`, `analog.com`→`ADI`, `murata.com`→`Murata`, `tdk.com`→`TDK`, `gct.co`→`GCT`, `memsic.com`→`Memsic`, `u-blox.com`→`uBlox`, `abracon.com`→`Abracon`);
  3. for an unknown host, the capitalised second-level domain, marked low confidence.

  The token must agree with the suffixes already used in `Custom/` (`TI`, `ADI`, `GCT`, `Memsic`, `uBlox`, `Abracon`, `TDK`). Match subdomains (`www.ti.com`, `e2e.ti.com`) to their registered domain. The table is a code constant, not a setting.
- **D-03:** Naming returns **one primary suggestion plus up to about 5 existing `Custom/` libraries ranked by shared tokens** (same manufacturer, same Type, overlapping SubCategory). If the primary suggestion equals an existing library name, that means "add to that library". Choosing between existing and new is Phase 4/5. Phase 3 only supplies the data. Existing library names are read from a fresh directory listing of `Custom/Symbols` and `Custom/Footprints`, not from `MainWindow._scan_result`.
- **D-04:** A part that can't be filled gets a **visible placeholder token**, e.g. `IC_SubCategory_TI` (and `Type` when even the Reference prefix is unknown). The suggestion result says which tokens are placeholders. Phase 4/5 must refuse to install while a placeholder token remains in the library name. Record that rule as a contract for those phases. For the UL sample the expected outcome is `IC_SubCategory_TI`, marked low confidence (Reference `U`, no description, datasheet host `ti.com`). This satisfies success criterion 4 (follows the convention, ends in `_TI`, overridable default).

### Zip safety (INTK-06)
- **D-05:** One hostile member anywhere in the zip **refuses the whole package**, even if that member would have been ignored. Hostile means: `..` segments, absolute paths, drive letters (`C:`), UNC or leading `\`/`/`, symlink entries (Unix mode bits in `external_attr`), or a name that normalises to an escape. An error Issue names the member. Nothing is staged.
- **D-06:** **Generous fixed caps**, as module constants in one place:
  - at most 1000 members;
  - 100 MB uncompressed per member;
  - 250 MB uncompressed in total;
  - a compression-ratio limit of 200:1, applied only to members larger than 1 MB.

  Check declared sizes up front, and also enforce them while reading, because a zip can lie about its sizes. The read cap counts actual bytes. Exceeding any cap refuses the package with an error Issue.
- **D-07:** Stage **only** `.kicad_sym`, `.kicad_mod`, `.step`, `.stp`, `.wrl` members (case-insensitive extension) into a `tempfile.mkdtemp()` directory under generated, safe names. Every other member (HTML guides, `readme.txt`, Altium/Eagle folders, `__MACOSX`) is listed for the log and never written to disk. The size and count caps apply to the whole zip, not just the staged members. Never use `extractall`. The staging dir must be verified to be outside the repo root, and is cleaned up by the context manager that owns it.
- **D-08:** A zip inside the zip is opened **one level deep**, with the same name checks. Its bytes count against the same total budget. A zip nested deeper is refused with an error Issue.

### Format detection (INTK-01, INTK-02, INTK-05)
- **D-09:** A zip whose layout matches no known vendor but contains v6+ KiCad files is **accepted as generic**. The vendor is reported as `Unknown`, with an info Issue saying vendor-specific quirks were not applied. This lets SnapEDA/CSE zips work before Phase 7 adds their adapters. Ultra Librarian and loose-folder recognition are required in this phase. The registry must let Phase 7 add SnapEDA/SamacSys adapters without changing callers.
- **D-10:** If KiCad 5 files (`.lib`, `.dcm`, `.mod`) sit alongside v6+ files, **use the v6+ files** and log one **info** Issue listing the ignored legacy files.
- **D-11:** The "re-download as KiCad v6+" rejection (error Issue) applies when the package has **no v6+ symbol and no v6+ footprint**, but legacy files exist. It also applies when one half is v6+ and the **other half exists only as legacy** (e.g. a v6 `.kicad_mod` plus a `.lib` symbol). Converting legacy files is v2 (FMT2-01).
- **D-12:** A package with a symbol but **no footprint at all** (or the reverse) and no legacy files is a **valid intake result**, flagged with a warning Issue. Whether it can be installed is decided in Phase 4/5. A package with no 3D model is valid too. The warning that INTK-08 requires is surfaced in Phase 4/5, and intake records "no model found".
- **D-13:** When a package holds several symbols, footprints or models, intake **returns all of them**. Picking which ones to import is INTK-07 (Phase 5).
- **D-14:** Phase 3 is verified by **tests only**: no temporary GUI entry point. The tests are pytest against the UL sample, plus synthetic fixtures built in `tmp_path` or under `tests/fixtures/`. The synthetic fixtures cover hostile zips (traversal, absolute, drive-letter, symlink, too many members, oversize, high ratio, nested two deep), a legacy-only package, a mixed v5/v6 package, a half-legacy package, a symbol-only package, and a loose folder.

### Name sanitising (LIB-03)
- **D-15:** One `sanitize_name` is used for **library, symbol, footprint and 3D-model file names**. For files, only the stem is sanitised and the original extension is kept, case included. Steps, in order:
  1. Transliterate with a small fixed map (`µ`/`μ`→`u`, `Ω`→`Ohm`, `°`→`deg`, …), then strip accents with `unicodedata` NFKD (`é`→`e`).
  2. Keep only `A-Z a-z 0-9 _ - .`. Every other character (space, `/`, `:`, `\`, `+`, `#`, parentheses, leftover non-ASCII) becomes `_`.
  3. Collapse runs of `_` into one.
  4. Strip leading and trailing `_`, `.` and spaces.
  5. Cap at **64 characters**, with a warning Issue.
  6. Windows-reserved stem check, case-insensitive (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`, including forms like `CON.foo`): **append `_`** (`CON`→`CON_`) with a warning Issue.
  7. An empty result falls back to a placeholder (e.g. `Unnamed`) with an **error** Issue, so install is blocked until the user edits it.

  Already-valid names, including every existing `Custom/` name such as `MEM2085-00-115-00-A_REV0.2` and `TSOT-23_TS8`, pass through unchanged. The result always carries both the original and the sanitised name (success criterion 5).
- **D-16:** A separate naming helper reports a **case-only clash** with an existing `Custom/` name (e.g. new `ic_ldo_ti` vs existing `IC_LDO_TI`) as a warning Issue, because Windows treats them as the same file. Resolving real conflicts (overwrite, rename or skip) stays in Phase 5 (PREV-05).

### Claude's Discretion
- Module layout under `kicad_lib_manager/importer/` (research suggests `package.py`, `candidate.py`, `adapters/{base,ultralibrarian,loose}.py`, `naming.py`, `layout.py`). Also the dataclass shapes for the package, candidate and suggestion, and the `Issue.code` names (e.g. `intake.hostile_member`, `intake.too_large`, `intake.legacy_only`, `intake.unknown_vendor`, `naming.low_confidence`, `naming.reserved`).
- Ultra Librarian recognition markers (e.g. `KiCADv6/` folder, `ImportGuides.html`, `ul_` filename prefix) and confidence scoring between adapters.
- Folder intake: recursion depth, whether caps apply to folders too, and skipping symlinks and junctions. Folders are read in place, read-only.
- Whether intake also extracts and exposes metadata Phase 4/5 will need: symbol name(s), Value, Datasheet, Description, Reference, existing Manufacturer/MPN-like fields, footprint name(s), and the `(version …)` of each file (for PREV-06). It is recommended where it is cheap.
- Whether intake notes an `(embedded_files` block in an incoming footprint for a later warning (from the untracked report).
- The exact Reference-prefix→Type table and the token-overlap ranking formula for D-01 and D-03.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` §Phase 3: the goal and five success criteria
- `.planning/REQUIREMENTS.md`: INTK-01, INTK-02, INTK-05, INTK-06, LIB-01, LIB-03, plus INTK-07 and INTK-08 (later phases whose contracts this phase feeds)
- `.planning/PROJECT.md`: the importer input and target-library bullets, the sample facts under Context, and the constraints (stdlib only, no write without preview)

### Prior phase decisions
- `.planning/phases/01-foundation/01-CONTEXT.md`: D-04 (sample zip committed, read in memory), D-07 (Issue contract), D-11 (encoding), D-12 (`kicad_files` read side)
- `.planning/phases/02-hardening-existing-code/02-CONTEXT.md`: Issue routing by `Severity`, and `(source, nickname)` identity

### Research
- `.planning/research/SUMMARY.md` §"Phase 3: Package intake, naming and target library": the deliverables list
- `.planning/research/ARCHITECTURE.md`: the `importer/` subpackage layout, `package.py` / adapter registry / `naming.py` responsibilities, Anti-Pattern 6 (extracting into the library), the facts table (STEP at zip root, unrelated names, `ti.com` host)
- `.planning/research/PITFALLS.md`: Pitfall 4 (illegal names), 8 (layout detection), 9 (zip handling), 14 (library-name collisions and conventions), 18 (testing only the happy path)
- `.planning/research/STACK.md`: `zipfile` selective reads and limits (probes done in Phase 1)

### Background (untracked, optional)
- `reports/KiCad 10 vendor part import.md`: competitor survey and KiCad 10 risks. It covers pairing by structure rather than filename, the zip-slip guard, and the `(embedded_files` warning.

### Conventions
- `.planning/codebase/CONVENTIONS.md`: naming, Issue lists, `Path` everywhere, `progress` callback shape
- `.planning/codebase/TESTING.md`: test layout and the run command (`.\env\Scripts\python.exe -m pytest`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kicad_lib_manager/kicad_files.py`: `parse_bytes(data, name)` parses staged or in-memory files into `LoadedFile | Issue`. `find_symbols`, `find_symbol`, `find_property` read Value, Datasheet, Reference, `ki_keywords`, Description and Manufacturer-like fields. `footprint_name` and `find_models` read the footprint.
- `kicad_lib_manager/fsutil.py`: `decode_source` / `read_source` (strict UTF-8, BOM), `default_backup_dir` (shows the per-OS app-data pattern, if a staging location other than system temp is ever needed).
- `kicad_lib_manager/models.py`: `Severity`, `Issue`. Keep `models.py` free of internal imports. Importer dataclasses may live in the importer package instead.
- `kicad_lib_manager/library_scanner.py`: `SKIP_DIRS` already includes `downloaded_examples` and `tests`.
- `downloaded_examples/ul_CSD85301Q2.zip` contains:
  - `KiCADv6/2026-10-18_09-12-49.kicad_sym` (symbol `CSD85301Q2`, `version 20211014`, units `_1_1`/`_2_1`);
  - `KiCADv6/footprints.pretty/DQK0006B.kicad_mod`;
  - `DLV0006A.stp` at the zip root;
  - junk: `ImportGuides.html`, `KiCADv6/ImportGuide.html`, `readme.txt`.

  The symbol has Reference `U`, Footprint `DQK0006B`, Datasheet `https://www.ti.com/lit/gpn/csd85301q2`, `ki_keywords` `CSD85301Q2` and `ki_fp_filters` `DQK0006B`. It has no description and no manufacturer.

### Established Patterns
- Services are Qt-free and return values plus Issue lists. Only `main_window.py` routes them to the log. Phase 3 adds no Qt code.
- Optional progress callbacks are named `progress` and called as `progress(message, current, total)`.
- Module-private helpers use a leading `_`. Constants are `UPPER_SNAKE` (zip caps, host→token table, reserved names, prefix→Type map).
- Tests are pytest with strict markers. Fixtures are built in `tmp_path` where possible (hostile zips are generated programmatically, not committed).

### Integration Points
- New `kicad_lib_manager/importer/` subpackage (Qt-free). It is consumed later by the Phase 4 planner and the Phase 5 dialog through a worker thread.
- `Custom/Symbols/*.kicad_sym` and `Custom/Footprints/*.pretty` names, which are the source for D-01/D-03 token vocabulary and D-16 case-clash checks. Current libraries: `Connector_FFC_GCT`, `Connector_MicroSD_GCT`, `Connector_USB_GCT`, `IC_Battery_Charger_TI`, `IC_Battery_Fuel_Gauge_ADI`, `IC_Button_Controller_ADI`, `IC_IMU_TDK` (symbol only), `IC_Magnetometer_Memsic`, `IC_Wireless_BLE_uBlox`, `Oscillator_TCXO_Abracon`.

</code_context>

<specifics>
## Specific Ideas

- Expected UL result: vendor `UltraLibrarian`, symbol `CSD85301Q2` from the timestamp-named file, footprint `DQK0006B`, model `DLV0006A.stp`, legacy files none, suggested library `IC_SubCategory_TI` (low confidence; the owner would edit it to something like `Transistor_MOSFET_TI`).
- The suggestion should never look finished when it isn't. A placeholder token is preferred over a plausible wrong name.

</specifics>

<deferred>
## Deferred Ideas

- A user-editable host→manufacturer map in settings. It was offered and declined: the map stays a code constant.
- Zip limits that the user can configure. Declined.
- A temporary "Inspect Package…" menu entry for trying intake before Phase 5. Declined: tests only.

</deferred>

---

*Phase: 03-package-intake-and-naming*
*Context gathered: 2026-10-19*
