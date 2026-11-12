# Feature Research

**Domain:** KiCad vendor-part importer (Ultra Librarian, SnapEDA/SnapMagic, SamacSys/Component Search Engine zips + loose files) inside an existing PySide6 library manager, for a single-owner personal library (`Custom/` submodule)
**Researched:** 2026-10-18
**Confidence:** MEDIUM overall. Ultra Librarian layout is HIGH (real sample inspected). SamacSys/CSE layout is MEDIUM (consistent across three independent third-party importers/tests, no official doc and no real sample). SnapEDA zip layout is LOW-MEDIUM (official docs only say "a `.kicad_sym` and a `.kicad_mod`"; no real sample). Feature landscape is MEDIUM-HIGH (source code of two importers read directly).

## READ FIRST: findings that contradict or sharpen PROJECT.md

These come from inspecting `downloaded_examples/ul_CSD85301Q2.zip` and the existing `Custom/` library. They change requirement wording; they do not relitigate any recorded decision.

1. **The UL sample DOES contain a 3D model.** `DLV0006A.stp` (192 KB, STEP AP203/214 from Creo) sits at the zip ROOT, outside `KiCADv6/`. PROJECT.md says "no STEP model". The "no 3D = warn" decision still applies to other packages, but 3D discovery must search the whole archive, not just the KiCad subfolder.
2. **The 3D file name does not match the footprint name or the symbol name.** Footprint `DQK0006B`, symbol `CSD85301Q2`, model `DLV0006A` (TI's package-drawing ID). Name-based pairing will fail; "the only model in the archive" is the only reliable rule for UL.
3. **The UL footprint has NO `(model ...)` entry at all.** "Rewrite the footprint's model path" must really be "rewrite if present, otherwise INSERT a `(model ...)` block" (with default offset/scale/rotate). Rewrite-only logic would silently produce a footprint with no 3D.
4. **UL symbol's `Footprint` property is the bare name** (`"DQK0006B"`, no `Lib:` prefix) and there is also a `ki_fp_filters` property containing `DQK0006B`. If the user renames the footprint in the preview, `ki_fp_filters` goes stale; the importer should update or drop it.
5. **Footprint rename touches three places**, not one: the file name, the `(footprint "NAME" ...)` token, and the `fp_text value` text (UL puts the name there too). Symbol rename must also rename nested unit sub-symbols (`CSD85301Q2_1_1` -> `<new>_1_1`).
6. **No Manufacturer or MPN property exists in the UL symbol.** It has Reference, Value, Footprint, Datasheet (a ti.com URL), `ki_keywords`, `ki_locked`, `ki_fp_filters`, and no Description. The preview's Manufacturer/MPN/Description editors therefore create properties, not just edit them, and the Datasheet URL domain is the only manufacturer hint in that package.
7. **The repo already mixes KiCad file-format versions.** `Custom/Symbols/*.kicad_sym` headers: `20211014` (3 files), `20231120` (1), `20241209` (6). `Custom/Footprints/*.kicad_mod`: all `20241229`. The UL sample is `20211014` for both, with legacy `(id N)` property tokens, `fp_text`, and `(width ...)` line style. A merge of an old-format symbol into a new-format library needs an explicit policy and a "does KiCad still load it" check.
8. **Existing custom symbols use SnapEDA-style property names** (`MF`, `MP`, `MANUFACTURER`, `Package`, `Price`, `Check_prices`, `SnapEDA_Link`, `PARTREV`, `STANDARD`, `MAXIMUM_PACKAGE_HEIGHT`, `Availability`, `Description`), inconsistently across libraries (`Description` x18, `MANUFACTURER` x9, `MF` x7). Requirements need one decision on the canonical Manufacturer/MPN property names the importer writes.
9. **Existing 3D files are kept with their original vendor names AND extension case** (`MEM2085-00-115-00-A_revA.STEP`, `USB4745-03-A.stp`, `BQ25180YBGR.step`) in a single flat `Custom/3DModels/`. A flat shared directory means 3D filename collisions are possible and need the same overwrite/rename/skip treatment as symbols and footprints, which the recorded decision only names for symbols and footprints.

## Observed package layouts

### Ultra Librarian (KiCad v6+ export) -- HIGH (real sample)

```
<zip root>
  DLV0006A.stp                      <- 3D model at ROOT, named by TI package-drawing ID
  ImportGuides.html                 <- redirect page to UL web help, ignore
  readme.txt                        <- generic UL footprint notes (drill sizes, slots), ignore
  KiCADv6/
    2026-10-18_09-12-49.kicad_sym   <- symbol file named by DOWNLOAD TIMESTAMP, not part number
    ImportGuide.html                <- ignore
    footprints.pretty/
      DQK0006B.kicad_mod            <- footprint named by package code
```
- Symbol file: format `(version 20211014) (generator kicad_symbol_editor)`, one `(symbol "CSD85301Q2" ...)` with nested `CSD85301Q2_1_1` unit. Part name comes from INSIDE the file.
- Footprint: `(version 20211014) (generator pcbnew)`, `fp_text`, `tags "CSD85301Q2 "`, no model.
- Folder name is `KiCADv6/` for the v6+ export. UL's own KiCad 6+ help page still describes a dated `.lib` file; the older KiCad 5 export (`KiCAD/` folder in Impart's detector) ships legacy `.lib` and is NOT importable by this tool.
- Other UL sources: tscircuit docs say v6+ downloads contain `.kicad_sym` + `.kicad_mod` (MEDIUM). Impart notes some UL bundles ship multiple variants (MEDIUM, from a third-party evaluation).

### SamacSys / Component Search Engine (CSE, also served via Mouser/Farnell/RS) -- MEDIUM (no real sample; three independent importers agree)

```
<PART>/                              (zip may be named LIB_<PART>.zip; top folder may be absent)
  KiCad/
    <PART>.kicad_sym                 <- named by part number; may hold >1 symbol
    <FOOTPRINT>.kicad_mod            <- named by package code, e.g. DIP794, SOP50P490X110-10N
  3D/
    <PART>.stp                       <- named by part number
  Altium/ ... Eagle/ ... etc.        <- present in some downloads, ignore
```
- Evidence: `Averyy/pcbparts-mcp` test fixture (`LM358P/KiCad/LM358P.kicad_sym`, `LM358P/KiCad/DIP794.kicad_mod`, `LM358P/Altium/...`, `LM358P/3D/LM358P.stp`); `AxxAxx/KiCad_scripts` globs `KiCad/*.kicad_sym`, `KiCad/*.kicad_mod`, `3D/*.stp|.step|.wrl`; Impart detects a folder literally named `KiCad` (case-sensitive vs UL `KiCAD`).
- Symbol `Footprint` property is the bare footprint name (AxxAxx's linker splits on `:` only if present). Footprint carries a `(model ...)` entry pointing at SamacSys's own path, so this is the "rewrite existing" case.
- Older CSE zips (KiCad 5 era) ship `<PART>.lib` + `<PART>.dcm` + legacy `.kicad_mod`; SamacSys' own "Library Loader" (V2.50+ for `.kicad_sym`) merges into `SamacSys_Parts.kicad_sym` / `SamacSys_Parts.pretty`. Legacy case is out of scope but must be detected.
- Component properties in CSE symbols (Manufacturer_Name, Manufacturer_Part_Number, Description, Datasheet link, Height) are from memory, not verified against a sample: LOW.

### SnapEDA / SnapMagic (KiCad v6+ download) -- LOW-MEDIUM (no real sample)

- Official support article: extract the zip; you get a `.kicad_sym` and a `.kicad_mod`; for footprints you point KiCad at "the folder containing the `.kicad_mod`" (so files may sit loose at the root or in a plain folder, NOT necessarily in a `.pretty`). Third-party playbook: download is `<MPN>.zip` with `<MPN>.kicad_sym` + `<MPN>.kicad_mod`.
- 3D model: that playbook says the STEP is a SEPARATE download (not in the KiCad zip). A 2021 SnapEDA forum example shows `.kicad_mod`, `.lib`, `.step` all in one zip (older packaging). Plan for "usually no 3D in the zip" -- this makes the loose-files input path the practical way to bring a SnapEDA STEP along (put it in the same folder).
- Support threads report some downloads missing the footprint, and the existing `Custom/` libraries confirm SnapEDA symbol property conventions (see item 8 above).
- Impart treats "has a symbol file, nothing else recognisable" as SnapEDA, i.e. the fallback is a flat layout.

### Loose files / Octopart / generic

- Extension-driven discovery handles all of these (`.kicad_sym`, `.kicad_mod`, `.step|.stp|.wrl`). Octopart bundles use `device.lib` + `device.dcm` (legacy) -- unsupported, detect and explain.

### Cross-vendor facts the importer must handle

| Fact | Evidence | Consequence |
|------|----------|-------------|
| Symbol file name is meaningless (timestamp / MPN / arbitrary) | UL sample; CSE | Read symbol names from file contents |
| Footprint file name usually equals its internal name, but not guaranteed | Impart names footprints "by content" and sanitises | Use internal `(footprint "X")` as truth, sanitise for file name |
| 3D model name unrelated to footprint | UL sample (`DLV0006A` vs `DQK0006B`) | Match by uniqueness, then name-token score, then ask |
| 3D model outside the KiCad subfolder | UL sample (zip root), CSE (`3D/` sibling of `KiCad/`) | Search whole archive |
| Non-KiCad junk members | `ImportGuides.html`, `readme.txt`, `Altium/`, possible `__MACOSX/._*` | Ignore by extension, filter resource forks |
| Symbol `Footprint` is bare, wrong, or empty | UL, CSE | Always overwrite with `<Lib>:<FP>` |
| Format version differs from target library | UL `20211014` vs repo `20241209` | Version policy + load check (see Pitfalls) |
| Multiple symbols/footprints per package | Averyy/AxxAxx handle many symbols; UL variants | Selection step in preview |

## Feature Landscape

### Table Stakes (Users Expect These)

"Users" here is one person who currently does this by hand. Missing any of these means the tool is worse than copy-paste in the Symbol Editor.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Open a `.zip` OR a folder; recursive, extension-driven discovery of `.kicad_sym` / `.kicad_mod` / `.step` `.stp` `.wrl` | Every surveyed importer (Impart, component-importer-for-kicad, AxxAxx) does this; layouts differ per vendor and per year | LOW | Do not hard-code `KiCADv6/` or `KiCad/`. Vendor name is a label for the UI/log, not a code path. Ignore `.html`, `.txt`, `.url`, `.pdf`, `__MACOSX`, non-KiCad CAD dirs. |
| Reject legacy formats with a clear message | Impart and SamacSys loaders convert `.lib`/`.dcm`; we don't, so we must say why | LOW | Detect `.lib`/`.dcm`/`device.lib`, `(module ...)` footprints, `KiCAD/` UL v5 export. "Re-download as KiCad v6+". |
| Safe archive reading | component-importer-for-kicad guards zip-slip, encrypted entries, entry-count and size bombs | LOW | Read members in memory or extract to a fresh temp dir; never `extractall` into the repo; reject `..`/absolute member names. |
| Parse real S-expressions (no regex on first match) | Already decided; AxxAxx and robertxdx hand-rolled paren walkers are the documented fragile spot; Impart uses kiutils | MEDIUM | One shared tokenizer/tree used by symbol merge, footprint edit, and the table-merge fix. Must preserve unknown tokens and comments-free formatting; round-trip untouched content byte-stable where possible to keep git diffs small. |
| Pick one symbol / one footprint when the package has several | CSE zips can hold several symbols; UL can ship variants; AxxAxx and Impart both loop over symbols | MEDIUM | Preview lists candidates, user selects. Pairing = symbol's `Footprint` property name matches footprint, else single-footprint-in-zip rule, else ask. "One package per session" still holds. |
| Preview of everything that will be written | Decided; also what makes the tool trustworthy | MEDIUM | A pure `ImportPlan` object (files to create/modify/overwrite, final names, path rewrites, conflicts, warnings) built with zero side effects; the dialog only renders it; install only executes it. Show relative paths, pin count, pad count, 3D present/absent. |
| Per-item conflict detection + overwrite / rename / skip | Decided. Impart defaults to overwrite silently (API default `overwrite_if_exists=True`); easyeda2kicad needs `--overwrite` | MEDIUM | Check symbol in target `.kicad_sym`, footprint in `.pretty` (case-insensitive on Windows), AND 3D filename in the flat `3DModels/`. "Rename" must propagate to `Footprint` field, `ki_fp_filters`, `(footprint "...")`, `fp_text value`, nested unit sub-symbols, and the `(model ...)` path. |
| Editable library name, suggested `<Type>_<SubCategory>_<Manufacturer>`; choose existing or create new | Decided | LOW-MEDIUM | Creating = new `.kicad_sym` with header + empty `.pretty/`; validate that sym/pretty names pair and the name has no `:` `/` `\` spaces or Windows-reserved names (Impart's `cleanName` covers reserved `CON`, `PRN`, `NUL`, `COMn`, trailing dots). |
| Name hygiene for footprint/symbol names | A `:` in a footprint name breaks `Lib:FP`; reserved/odd names break Windows files | LOW | Validate in the editable field, show inline error, block Install. |
| Symbol `Footprint` = `<Lib>:<FP>` set automatically; Value/Datasheet/MPN/Manufacturer/Description editable | Decided; Impart, robertxdx and AxxAxx all auto-link | LOW-MEDIUM | Create the property if absent (UL lacks Manufacturer/MPN/Description). Pre-fill from existing values; Datasheet pre-filled from vendor URL. |
| Footprint copy with correct internal name | Impart names by content; naive file copy leaves name mismatch after rename | LOW-MEDIUM | See "READ FIRST" item 5. |
| 3D model: copy to `Custom/3DModels/`, set `(model "${CUSTOM_3DMODEL_DIR}/<file>")` (rewrite OR insert), keep offset/scale/rotate if present | Every surveyed tool fixes 3D paths (robertxdx `footprint_3d_fixer`, AxxAxx `copy_footprint`, Impart `update_or_add_model`) | MEDIUM | Insert case is real (UL). Preserve original extension/case like the existing library does. Prefer STEP over WRL (Impart: "archives always prefer STEP"). Handle multiple `(model)` entries (Impart's tests cover this). |
| 3D picker when several models exist | robertxdx scores token overlap between model and footprint names | LOW-MEDIUM | Order: single model -> use; else name-token score; else ask. |
| No-3D case: install and warn (decided) | Decided | LOW | Preview states "no 3D model" prominently; log warning after install. If the footprint still references a vendor `(model ...)` path with no file shipped, REMOVE or flag it so the repo doesn't contain a dangling model path (existing scanner would warn). |
| Transactional install with rollback | Impart records backups for every target and rolls ALL of them back on any failure (and verifies the written symbol lib re-parses non-empty) | MEDIUM | Reuses the already-planned atomic-write helper (`os.replace`). Write order: 3D, footprint, then symbol lib last; on failure restore. Never leave a half-imported part. |
| Post-write verification | Impart re-reads the written library; robertxdx has a validator (symbol present, footprint resolves, 3D resolves, lib registered) | LOW-MEDIUM | Re-parse written files, assert symbol exists, `Footprint` resolves in the repo, model file exists. Existing scanner (`ScanResult` warnings) can be re-run after install for free. |
| Refresh library tables / rescan after install | Decided; also KiCad (esp. v10) caches tables, so the user must reload | LOW | Reuse Rescan + Generate. Tell the user to reload/restart KiCad when a NEW library was created (robertxdx and Impart both document this). |
| Clear log lines for every action | Existing log panel; Impart/robertxdx print "added/updated symbol", "saved footprint", "skipped" | LOW | Use the existing colour-coded panel. |
| Git: confirm, commit only the touched paths in `Custom`, bump parent ref, never push | Decided; CLAUDE.md workflow | MEDIUM | See Pitfalls: stage explicit paths (not `git add -A`), warn if submodule is on a detached HEAD or has other uncommitted changes, pre-fill an editable commit message in repo style (e.g. `Add CSD85301Q2 (IC_... ) symbol, footprint DQK0006B, 3D model`). |

### Differentiators (Competitive Advantage)

These are not expected, but each directly serves the Core Value ("correct name, correct link, no hand-editing") for this repo. None of the surveyed tools has a naming-convention-aware workflow; that is the real differentiator.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Library-name suggestion engine: Manufacturer -> short code, matched against existing `Custom/` libs (`*_TI`, `*_GCT`), shown as a filtered dropdown plus "New..." | Enforces the `<Type>_<SubCategory>_<Manufacturer>` convention (no surveyed tool does; Impart uses one lib per vendor like `Snapeda.kicad_sym`) | MEDIUM | Manufacturer sources: symbol `MANUFACTURER`/`MF`/`Manufacturer_Name` property, Datasheet URL domain (`ti.com` -> `TI`), footprint tags. Type/SubCategory: suggest from existing library prefixes; do not try to infer from the part. Always editable. |
| Pin/pad cross-check | Catches wrong-package downloads (a classic vendor error) before they reach a curated library | LOW-MEDIUM | Compare symbol pin numbers vs footprint pad numbers (allow NC/mount pads/duplicate numbers); show as warning in preview, not a block. |
| Cross-library duplicate warning | Prevents the same MPN living in two `Custom/` libraries | LOW | `ScanResult` already holds every symbol; check name across all Custom libs and show the existing location. |
| Hide-or-keep vendor junk properties choice | Vendor symbols carry `Price`, `Availability`, `Check_prices`, `SnapEDA_Link`; the existing libs just keep them hidden | LOW | Default: keep as-is (matches existing libs). Do not delete data unasked. |
| Version-normalisation + "will KiCad load this" check using `kicad-cli` when found | Impart runs `kicad-cli sym/fp upgrade` after writing; here it would eliminate the mixed `20211014` / `20241209` problem | MEDIUM | App already auto-detects the KiCad install; add `kicad-cli` discovery. Optional (graceful skip when absent). Needs a policy decision: rewrite imported part to the library's version, or upgrade the whole library file (the latter touches unrelated symbols = noisy diff). |
| Rendered preview (SVG of symbol and footprint) via `kicad-cli sym/fp export svg` into a `QSvgWidget` | Lets you eyeball pin layout/orientation before commit; no need to implement a renderer | MEDIUM-HIGH | Only if kicad-cli present. Defer to v1.x; the textual preview is enough for v1. |
| Drag-and-drop a zip/folder onto the window; remember last browse dir; "latest zip in Downloads" button | Impart added drag-and-drop; trivial in Qt and removes the file dialog friction | LOW | Not a watcher. |
| Provenance trail: vendor, original filename, import date written into the commit message (and optionally a hidden symbol property) | Later answers "where did this symbol come from / which vendor's pin names" | LOW | Commit message is enough for v1; hidden property is optional. |
| Dry-run self-test via fixtures | Real downloads as pytest fixtures (decided) double as living documentation of the layouts above | MEDIUM | The only sample today is UL. SnapEDA, CSE and loose-file samples must be collected before those formats are claimed "supported". |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Watch the Downloads folder and auto-import (robertxdx, SamacSys Library Loader) | "Zero click" | Contradicts preview-first and the curated-library goal; a stray zip silently modifies the repo | Browse / drag-and-drop / "latest zip in Downloads" button, always followed by preview |
| Search / download by MPN, online-search links, EasyEDA/LCSC import (easyeda2kicad, robertxdx Search tab) | Fewer manual steps | Already out of scope; needs accounts/APIs/scraping and legal/ToS exposure; EasyEDA output "can't be guaranteed" correct per its own README | Download manually; importer starts from a file |
| Silent overwrite as default, or one global `--overwrite` switch (Impart API default, easyeda2kicad) | Simpler code | Destroys curated, hand-edited parts (re-import wipes user fixes) | Per-conflict overwrite/rename/skip (decided) |
| Batch / multi-zip queue (Impart folder import, AxxAxx loop) | Convenient for bulk | Decided out; multiplies conflict UI and failure modes | One package per session |
| Legacy `.lib`/`.dcm`/KiCad 5 `.mod` conversion | SamacSys/Octopart/old SnapEDA still ship them | Needs `kicad-cli` (not always present), dcm merging, and format-quality risk | Detect + clear message; revisit only if a real need shows up |
| Restyling symbols to KiCad conventions (robertxdx "symbol formatting") or fixing geometry | Vendor symbols look inconsistent | Editing graphics is explicitly out of scope; high regression risk | Leave graphics untouched; fix in KiCad's editor |
| Choice of 3D path variable (`${KIPRJMOD}`, `${KICAD_3RD_PARTY}`, relative) as in Impart/easyeda2kicad | Flexibility for many setups | This repo has exactly one convention, `${CUSTOM_3DMODEL_DIR}`; options invite inconsistent libs | Hard-code it (note: a few existing footprints still use `${KIPRJMOD}/Custom/3DModels`; normalising those is a separate cleanup, not an importer feature) |
| Gzip-compressing STEP (`.step.gz`, Impart) | Smaller repo | Existing library keeps plain `.step`; other tools and the scanner expect it | Keep plain files |
| Keeping a copy of every source zip in the repo (robertxdx) | Auditability | Bloats the git history; vendor licences vary | Record provenance in the commit message |
| Writing KiCad's own global tables / settings beyond the app's existing Generate | Convenience | Already handled by Generate; touching live KiCad config from the importer widens blast radius | Rescan + existing table generator |
| Built-in undo manager | "Oops" safety | Duplicates git; the commit is the unit of undo | Per-install transactional rollback on failure, `git reset`/`revert` for after-the-fact |
| Push after commit | One fewer step | Decided out | Manual push |
| Attaching a separately downloaded STEP | SnapEDA delivers STEP separately, so this is a real itch | Decided out for v1 | Workaround already supported: loose-files mode with the STEP in the same folder as the SnapEDA files |

## Feature Dependencies

```
S-expression tokenizer/tree
    ├──required by──> Symbol merge (insert / replace / rename incl. nested units)
    ├──required by──> Footprint edit (rename, model insert/rewrite, tags)
    └──required by──> Table-merge hardening (existing concern)

Archive/folder reader (safe, extension-driven discovery)
    └──feeds──> Package model (symbols[], footprints[], models[], warnings)
                    ├──feeds──> Pairing rules (symbol<->footprint, footprint<->3D)
                    └──feeds──> Legacy-format detection (reject)

Package model + target lib + user edits
    └──produces──> ImportPlan (pure, no side effects)
                      ├──rendered by──> Preview dialog (names, fields, conflicts, warnings)
                      │                     └──enhanced by──> pin/pad check, cross-library duplicates, SVG render
                      └──executed by──> Transactional installer
                                           (needs: atomic write helper, backup/rollback)
                                           ├──then──> Post-write verification
                                           ├──then──> Rescan + Generate Tables
                                           └──then──> Confirm dialog -> git commit in Custom -> bump parent ref

Library-name suggestion ──enhances──> Target library selection (needs ScanResult of existing Custom libs)
Create-new-library ──requires──> sym/pretty name pairing validation, version-header policy
Version-header policy ──requires──> decision on KiCad format version for new/merged content (+ optional kicad-cli check)
Per-conflict rename ──requires──> rename propagation (Footprint field, ki_fp_filters, internal names, model path)
Batch import / watch folder ──conflicts──> Preview-before-write and one-package-per-session
Silent overwrite ──conflicts──> Per-conflict overwrite/rename/skip
```

### Dependency Notes

- **Everything structural requires the S-expression layer.** It is the first thing to build; it also unblocks the "Table merge drops external entries" hardening item, so build and test it once.
- **ImportPlan must be pure.** If the preview and the installer are produced from the same plan object, "preview matches what is written" holds by construction, and the whole importer is unit-testable headless without Qt (matches the stated pytest goal).
- **Pairing rules need real fixtures.** Only UL is available now; SnapEDA, CSE and loose-file paths should be built extension-driven (so they probably work) but cannot be marked verified until samples exist (already noted in PROJECT.md constraints).
- **Rename propagation is a shared dependency** of the conflict feature and the "edit footprint name" feature; implement once as a single `rename_footprint`/`rename_symbol` operation on the parsed tree.
- **Git step depends on a successful install + rescan**, not the other way round; a failed install must never reach the commit prompt.

## MVP Definition

### Launch With (v1)

- [ ] Zip/folder open, safe reading, extension-driven discovery, junk filtering -- foundation for all formats
- [ ] Legacy-format detection with a clear rejection message
- [ ] S-expression layer + symbol merge + footprint edit + 3D insert/rewrite -- the core transformation
- [ ] Selection step when more than one symbol/footprint/model exists
- [ ] Target library: existing or new, convention-based suggestion (simple version: manufacturer code + dropdown of existing libs)
- [ ] ImportPlan + preview with editable names/fields, warnings (no 3D, dangling vendor model path, version mismatch, name hygiene), conflicts incl. 3D filename
- [ ] Per-conflict overwrite / rename / skip with full rename propagation
- [ ] Transactional install + post-write verification + rescan + table regeneration
- [ ] Commit-only git step with explicit paths, detached-HEAD and dirty-submodule checks, editable message
- [ ] Headless pytest using the UL sample plus synthetic CSE-shaped and SnapEDA-shaped fixtures built from the layouts documented above

### Add After Validation (v1.x)

- [ ] Pin/pad cross-check -- add once the preview exists; cheap
- [ ] Cross-library duplicate warning -- cheap, needs only `ScanResult`
- [ ] `kicad-cli` version normalisation / load check -- once the version policy is decided
- [ ] Drag-and-drop, remembered folder, "latest zip in Downloads"
- [ ] SVG preview via `kicad-cli export svg` -- once real use shows textual preview is insufficient
- [ ] Replace synthetic fixtures with real SnapEDA / CSE / loose-file downloads as the owner collects them

### Future Consideration (v2+)

- [ ] Legacy `.lib`/`.dcm` conversion -- only if the owner keeps meeting old packages
- [ ] Separate-STEP attachment -- already deferred by decision
- [ ] Hidden provenance property on the symbol

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Discovery + safe reading + junk filtering | HIGH | LOW | P1 |
| S-expression layer (shared with hardening) | HIGH | MEDIUM | P1 |
| Symbol merge + Footprint link | HIGH | MEDIUM | P1 |
| Footprint rename + 3D insert/rewrite | HIGH | MEDIUM | P1 |
| ImportPlan + preview | HIGH | MEDIUM | P1 |
| Conflicts overwrite/rename/skip (incl. 3D) | HIGH | MEDIUM | P1 |
| Transactional install + verification | HIGH | MEDIUM | P1 |
| New/existing library + name hygiene | HIGH | LOW-MEDIUM | P1 |
| Selection when multiple candidates | MEDIUM | MEDIUM | P1 |
| Legacy-format rejection message | MEDIUM | LOW | P1 |
| Git commit step (safe) | HIGH | MEDIUM | P1 |
| Library-name suggestion engine | HIGH | MEDIUM | P1 (simple) / P2 (smart) |
| Pin/pad cross-check | MEDIUM | LOW-MEDIUM | P2 |
| Cross-library duplicate warning | MEDIUM | LOW | P2 |
| kicad-cli normalise/check | MEDIUM | MEDIUM | P2 |
| Drag-and-drop / Downloads shortcut | LOW-MEDIUM | LOW | P2 |
| SVG render preview | MEDIUM | MEDIUM-HIGH | P3 |
| Legacy conversion | LOW | HIGH | P3 |

**Priority key:** P1 must have for launch; P2 add when possible; P3 future.

## Competitor Feature Analysis

| Feature | Impart (Import-LIB-KiCad-Plugin, Steffen-W) | component-importer-for-kicad (robertxdx) | easyeda2kicad / parts2kicad / AxxAxx script | KiCad built-in | Our Approach |
|---------|------|------|------|------|------|
| Input | UL, SnapEDA, SamacSys, Octopart zips; drag-drop; folder; EasyEDA by ID | KiCad zips; watched Downloads folder | LCSC IDs / SamacSys zip / zips in a folder | Symbol/Footprint editor "Import" per file | zip or folder, extension-driven, one package |
| Format detection | Folder-name heuristics (`KiCad`, `KiCAD`, `device.lib`) then SnapEDA fallback | Pure extension dispatch | Glob `KiCad/*.kicad_sym` etc. | Manual | Extension-driven; vendor only as label |
| Preview | None | None (post-import report) | None | n/a | Full pre-write plan (decided) |
| Target library | One per vendor (`Snapeda`, `Samacsys`) or single custom name | Project or global lib, or both | One folder/lib per part (AxxAxx) or one lib (`easyeda2kicad`) | User chooses | Convention-based `<Type>_<SubCategory>_<Manufacturer>` |
| Conflicts | Overwrite by default; flag to skip | Skip if already present | Skip if exists / `--overwrite` | Prompts in editor | Per-item overwrite / rename / skip |
| Footprint link | Sets `Lib:FP` | Sets via linker | Sets `part:fp` | Manual | Auto, plus rename propagation |
| 3D handling | Copies to `<lib>.3dshapes`, rewrites/ adds `(model)`, optional gzip, path var option | Copies to organised folder, repairs paths with token-overlap scoring | Copies next to part, rewrites to `${KIPRJMOD}` | Manual | Copy to `Custom/3DModels`, `${CUSTOM_3DMODEL_DIR}`, insert-or-rewrite |
| Safety | Atomic writes + full rollback + re-parse check | Backups + validator + zip-bomb/zip-slip guards | AxxAxx: leaves existing parts untouched | n/a | Atomic + rollback + verification + zip guards |
| Legacy `.lib` | Converts via `kicad-cli` | Not handled | n/a | Editor can import | Detect + reject (v1) |
| Library tables | Checks, never edits | Registers in tables | AxxAxx edits project tables | Manual | Existing Generate Tables |
| Git | None | None | None | None | Commit in submodule + bump parent (unique) |

## Sources

- Real sample: `downloaded_examples/ul_CSD85301Q2.zip` (listed and read with `python -I` + `zipfile`; HIGH).
- Existing repo state: `Custom/Symbols/*.kicad_sym` property and version census, `Custom/Footprints/*.pretty` model-path census (HIGH).
- Impart / Import-LIB-KiCad-Plugin source and README, read via `gh api` (`plugins/KiCadImport/__init__.py`, `tests/test_lib_importer.py`) -- https://github.com/Steffen-W/Import-LIB-KiCad-Plugin (HIGH for behaviour, as code).
- component-importer-for-kicad README -- https://github.com/robertxdx/component-importer-for-kicad (MEDIUM) and the kicad-tools evaluation of its source: https://github.com/rjwalters/kicad-tools/blob/main/docs/research/component-importer-for-kicad-evaluation.md (MEDIUM).
- AxxAxx `import_3rd_party_libs.py` (CSE zip handling, source code) -- https://github.com/AxxAxx/KiCad_scripts (MEDIUM for CSE layout).
- Averyy/pcbparts-mcp test fixture showing `LM358P/KiCad/...`, `LM358P/3D/LM358P.stp` -- https://github.com/Averyy/pcbparts-mcp (MEDIUM, mock data).
- easyeda2kicad README -- https://github.com/uPesy/easyeda2kicad.py (MEDIUM).
- parts2kicad thread -- https://forum.kicad.info/t/parts2kicad-script-for-importing-from-samacsys-mouser-farnell/66224 (LOW-MEDIUM).
- Ultra Librarian KiCad 6+ help -- https://app.ultralibrarian.com/content/help/kicad-6_0.htm (HIGH for steps; does not document layout).
- SnapMagic KiCad v6+ import guide -- https://support.snapmagic.com/en/articles/5995733-how-to-import-into-kicad-v6-and-later (HIGH for what it says; layout not documented).
- SnapMagic download playbook (3D model downloaded separately) -- https://wiki.adom.inc/api/pages/adom/chip-fetcher/files/playbooks/snapmagic.md (LOW-MEDIUM, third party).
- SamacSys KiCad setup/Library Loader pages -- https://www.samacsys.com/?p=321860 and https://www.samacsys.com/?p=318527 (MEDIUM; no zip layout).

---
*Feature research for: KiCad vendor-part importer (personal library workflow)*
*Researched: 2026-10-18*
