# Phase 13: Atomic Migration and KiCad Setup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md. This log keeps the alternatives that were considered.

**Date:** 2026-11-11
**Phase:** 13-atomic-migration-and-kicad-setup
**Areas discussed:** Target libraries & drift, Part & footprint renames, Migration window & fill-in, Chooser setup & descriptions, plus board features (raised by the owner mid-session)

---

## Target libraries & drift

| Question | Options | Selected |
|---|---|---|
| How is each part's target decided? | Importer's suggestion, editable / Fixed table from research §5 / Suggestion per old library | Importer's suggestion, editable |
| Uncommitted duplicate CSD85301Q2 (Atomic_Transistor_FET + DQK0006B) | I clean it up by hand first / Migration treats duplicates generally / Both | I clean it up by hand first |
| Parts already in an Atomic_ library (crystal in Atomic_Oscillator) | Listed, may be moved / Left as they are / Listed, kept by default | Listed, may be moved |
| "9 libraries" and "two .bak" wording | No fixed count, delete every .bak / Keep 9 as a target / No fixed count, .bak only if listed | No fixed count, delete every .bak |

## Part & footprint renames

| Question | Options | Selected |
|---|---|---|
| Symbol names | Symbol name = MPN, editable / Keep current names / MPN keeping a revision suffix | Symbol name = MPN, editable |
| Variant families (LTC2954 ×4, MAX17048G/X) | Type each MPN, variants via extends / Type each MPN, no restructuring / Keep family names as MPN | Type each MPN, variants via extends |
| Footprint names in Atomic_Footprints | Keep, editable / Strip SnapEDA prefixes / Generate package-based names | Keep, editable |
| Official KiCad footprint switch | Offered per part, default move / Pre-select a strong match / Move all, switch later | Offered per part, default move |
| 3D model file names | Keep / Rename to `<MPN>.<ext>`, editable | Rename to `<MPN>.<ext>`, editable |
| Unlinked leftovers | Delete, listed in preview / Always keep / Always delete | Delete, listed in preview (later amended, see Board features) |
| Keywords, footprint description and tags | Same rules as the importer / Only fill empty ones | Same rules as the importer |
| Old alias fields (MF/MP, leftovers) | Removed, shown in Field changes / Kept alongside | Removed, shown in Field changes |

## Migration window & fill-in

| Question | Options | Selected |
|---|---|---|
| Entry point | Menu item while v1 libraries exist / Permanent Reorganise tool / Startup prompt | Menu item while v1 libraries exist |
| Progress across sessions | Saved draft, restored on reopen / Fill in KiCad first / Write each fill-in straight away | Saved draft |
| Preview layout | Part list + detail pane / One long page / Spreadsheet table | Part list + detail pane |
| Where the old → new map is saved | In Custom, committed / App data only / Both | In Custom, committed (`Custom/MIGRATION-ATOMIC.md`) |

## Chooser setup & descriptions

| Question | Options | Selected |
|---|---|---|
| When it is offered | Own menu action + offered after migration / Only after migration / Folded into Generate | Own menu action + after migration |
| Pins | All Atomic_ symbol libs + Atomic_Footprints / Symbol libs only / Replace the pin lists | All Atomic_ symbol libs + Atomic_Footprints |
| Columns | MPN + Manufacturer after Description, drop MANUFACTURER / Add at the end / Minimal set | After Description, drop MANUFACTURER |
| Table descriptions | Generated from name + KiCad stock text / Simple pattern / Editable per library | Generated from name + KiCad stock text |

## Board features (owner question mid-session)

The owner asked how to create a PCB-trace USB-A plug (SparkFun `USB-A-PCB.kicad_mod`) with a USB symbol. It is a creation, not an import.

| Option | Selected |
|---|---|
| Footprint only in Atomic_Footprints + KiCad stock symbol; amend D-10 so pre-existing unlinked footprints default to Keep | ✓ |
| Own part with a self-assigned MPN, Manufacturer and dummy 3D model | |
| Decide later | |

## Claude's Discretion

- The after-Run flow (rescan, table regeneration through the Generate confirmations, commit panel)
- `pre-atomic` tag handling and the git allow-list additions
- The transaction pattern
- The draft format
- Threading
- Wording
- DOC-01 content
- Test strategy

## Deferred Ideas

- A general Reorganise tool
- An editable per-library description column
- A "create a part" flow
