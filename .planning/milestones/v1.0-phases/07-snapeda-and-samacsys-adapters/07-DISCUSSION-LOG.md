# Phase 7: SnapEDA and SamacSys Adapters - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-23
**Phase:** 07-snapeda-and-samacsys-adapters
**Areas discussed:** Test fixtures & licence, Vendor field cleanup, Names & metadata hints, Detection & vendor label

Pre-discussion probe: both real samples already import through the generic path. SnapEDA reports `unknown_vendor` and `no_model`. SamacSys reports `unknown_vendor`, `legacy_footprint_syntax` and `legacy_ignored`. Both GitHub repos are public, and the SamacSys `license.txt` forbids redistributing the models.

---

## Test fixtures & licence

### How should the samples become fixtures?

| Option | Description | Selected |
|--------|-------------|----------|
| Synthetic + local opt-in | Synthetic look-alike zips committed; real zips local only and tested opt-in | ✓ |
| Trimmed real files | Cut-down real `.kicad_sym` / `.kicad_mod`, no STEP body | |
| Commit the real zips | Track both, like `ul_CSD85301Q2.zip` | |

### When do the real-zip tests run, and how are accidental commits prevented?

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-run if present + gitignore | Skip with a reason when the zip is missing; ignore `downloaded_examples/*` except the UL zip | ✓ |
| Env-var gate + gitignore | Same pattern as `KICAD_IMPORT_UAT_DIR` | |
| Auto-run, no gitignore | Untracked, with no ignore rule | |

### What is the "copy of Custom/" for install tests?

| Option | Description | Selected |
|--------|-------------|----------|
| Small synthetic Custom | Minimal fixture in `tmp_path` | ✓ |
| Synthetic + fix the 3 tests | Also move the 3 tests that read the real tree | |
| Copy of real Custom/ | Copy the live tree | |

### Should the phase prove that KiCad loads the installed parts?

| Option | Description | Selected |
|--------|-------------|----------|
| kicad-cli check, version-agnostic | `kicad_cli`-marked load test that pins no format number | ✓ |
| Pytest structure only | Assert links and paths only | |
| Manual UAT only | Owner checks in KiCad 10 | |

---

## Vendor field cleanup

### Marketing and stock fields

| Option | Description | Selected |
|--------|-------------|----------|
| Drop volatile, keep identifiers | Drop price, stock and availability fields with their links; keep distributor part numbers and the source link | ✓ |
| Keep everything | Copy every field as-is | |
| Drop all vendor-only fields | Keep only standard fields plus Manufacturer, MPN and Description | |

### Placeholder fields (empty or `None`)

| Option | Description | Selected |
|--------|-------------|----------|
| Drop empty and "None" | Vendor-only fields only, never KiCad standard fields | ✓ |
| Keep them | Copy as-is | |

### Description whitespace

| Option | Description | Selected |
|--------|-------------|----------|
| Trim + collapse whitespace | Gives "Type C USB 2.0 Connector" | ✓ |
| Trim ends only | Keep internal line breaks | |
| Leave as-is | Fix by hand in the preview | |

### Duplicate Manufacturer/MPN aliases after the D-12 rename

| Option | Description | Selected |
|--------|-------------|----------|
| Drop duplicate aliases | Remove `MANUFACTURER` and `SNAPEDA_PN` once Manufacturer and MPN are set; incoming symbols only | ✓ |
| Keep duplicates | Leave them in place | |
| Prefer the short name | Write "GCT" into Manufacturer | |

### Which packages the rules apply to

| Option | Description | Selected |
|--------|-------------|----------|
| All vendors, per-vendor field lists | Generic rules for everyone, volatile-field list per adapter, UL tests re-baselined | ✓ |
| Only SnapEDA/SamacSys | UL and generic output unchanged | |

---

## Names & metadata hints

### SnapEDA `_REVA2` suffix

| Option | Description | Selected |
|--------|-------------|----------|
| Keep vendor name | Symbol name and Value stay as shipped; rename in the preview | ✓ |
| Strip SnapEDA _REVxx suffix | Propose the MPN as the name | |
| Value = MPN only | Keep the symbol name, set Value to the MPN | |

### SamacSys `part_info.txt`

| Option | Description | Selected |
|--------|-------------|----------|
| Category → Type + fallbacks | PartCategory maps to Type; Manufacturer and PartNumber fill gaps; add `PS`→`PowerSupply` | ✓ |
| Fallbacks only | Manufacturer and PartNumber fill gaps only | |
| Ignore part_info.txt | Use symbol properties only | |

### RECOM token spelling

| Option | Description | Selected |
|--------|-------------|----------|
| RECOM (brand casing) | Alias `recom` / `recompower` → `RECOM` | ✓ |
| Recom (title case) | Alias to `Recom` | |
| No alias, guess is fine | Leave the guessed token | |

---

## Detection & vendor label

### What recognition relies on

| Option | Description | Selected |
|--------|-------------|----------|
| Names + content markers | Name scoring plus the generator string, properties and `license.txt` / htm text | ✓ |
| Names only | Member and zip names only | |

### Vendor label

| Option | Description | Selected |
|--------|-------------|----------|
| SnapEDA / SamacSys | Short, stable names | ✓ |
| Add distributor when known | e.g. "SamacSys (Mouser)" | |
| Current brand names | SnapMagic and Component Search Engine | |

### Reporting SamacSys's 62 other-CAD members

| Option | Description | Selected |
|--------|-------------|----------|
| Summarise by folder | One INFO line listing the folder names | ✓ |
| Keep current list | 20 paths plus "and N more" | |

---

## Claude's Discretion

- Detection weights and thresholds, and how `detect()` reaches the content markers
- Where the field-cleanup step lives (adapter hook vs. planner step)
- The full PartCategory→Type table and the generic volatile-field list
- How the synthetic fixtures are produced (builder script vs. committed small zips)
- The byte cap for marker and `part_info.txt` reads

## Deferred Ideas

- Distributor in the vendor label
- A per-field "keep" toggle in the preview
- Stripping `_REVxx` revision suffixes
- Licence review of the tracked UL zip in the public repo
- Moving the 3 tests that read the real `Custom/` tree onto the synthetic fixture
