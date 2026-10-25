# Phase 3: Package Intake and Naming - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log keeps the alternatives that were considered.

**Date:** 2026-10-19
**Phase:** 03-package-intake-and-naming
**Areas discussed:** Library name suggestion, Zip safety limits, Format detection & mixes, Name sanitising rules

---

## Library name suggestion

**Type_SubCategory guess when the file has no hint**

| Option | Description | Selected |
|--------|-------------|----------|
| Best guess + low-confidence flag | Guess from the Reference prefix and keywords matched against Custom/ tokens; flag as low confidence | ✓ |
| Placeholder only | Suggest only the manufacturer token; the user fills in the rest | |
| Reuse existing same-maker lib | Suggest an existing `_TI` library (wrong for the UL sample) | |

**Datasheet host → manufacturer token**

| Option | Description | Selected |
|--------|-------------|----------|
| Built-in map + Custom/ suffixes | Code-constant host table, also honours Manufacturer-like properties; unknown host = capitalised SLD, low confidence | ✓ |
| Only Custom/ suffixes | Match only existing suffixes; unknown makers left blank | |
| User-editable map in settings | Same as the first option, but editable in QSettings | |

**One suggestion or ranked existing libs**

| Option | Description | Selected |
|--------|-------------|----------|
| One name + ranked existing libs | Primary suggestion plus up to ~5 existing Custom/ libs ranked by shared tokens | ✓ |
| Single suggestion only | Just one editable name | |

**SubCategory can't be filled**

| Option | Description | Selected |
|--------|-------------|----------|
| Visible placeholder token | e.g. `IC_SubCategory_TI`; install refused while a placeholder remains | ✓ |
| Drop the missing part | e.g. `IC_TI` | |
| Use the part number | e.g. `IC_CSD85301Q2_TI` | |

---

## Zip safety limits

| Question | Options | Selected |
|----------|---------|----------|
| One hostile member | Refuse the whole zip / Skip that member, warn | Refuse the whole zip |
| Zip-bomb limits | Generous fixed caps (1000 members, 100 MB/member, 250 MB total, 200:1 over 1 MB) / Tight caps (200, 50 MB, 100 MB, 100:1) / Caps in settings | Generous fixed caps |
| What is staged | Only KiCad + 3D files / Whole zip into temp / Nothing staged, read in memory | Only KiCad + 3D files |
| Nested zips | One level, same checks / No nesting | One level, same checks |

---

## Format detection & mixes

| Question | Options | Selected |
|----------|---------|----------|
| Unknown vendor zip with v6+ files | Accept as generic / Refuse until supported | Accept as generic |
| Mixed v5 + v6 content | Use v6+, info log / Use v6+, warning | Use v6+, info log |
| v6 half + legacy other half | Reject with the v6+ message / Accept the v6+ half | Reject with the v6+ message |
| Way to try intake before Phase 5 | Tests only / Temporary "Inspect Package…" menu | Tests only |
| Symbol-only or footprint-only package | Valid, flagged / Reject at intake | Valid, flagged |

---

## Name sanitising rules

| Question | Options | Selected |
|----------|---------|----------|
| Character set | Strict ASCII, `_` replaces / Only remove the dangerous ones | Strict ASCII, `_` replaces |
| Non-ASCII | Transliterate, then strip / Replace with `_` | Transliterate, then strip |
| Reserved or empty names | Append `_` + warning (empty → placeholder + error) / Reject the name | Append `_` + warning |
| Length and case | Cap 64 chars, case-check in naming / No length cap, case-check only / Neither | Cap 64 chars, case-check in naming |

---

## Claude's Discretion

- Importer module layout, dataclass shapes and `Issue.code` names
- Ultra Librarian recognition markers and adapter scoring
- Folder intake recursion and caps
- Which metadata intake exposes for Phase 4/5 (names, fields, file-format versions)
- Noting `(embedded_files` in incoming footprints
- The Reference-prefix → Type table and the ranking formula

## Deferred Ideas

- A user-editable host→manufacturer map (declined)
- Zip limits the user can configure (declined)
- A temporary "Inspect Package…" menu (declined)
