# Phase 10: Importer on the Atomic Scheme - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-26
**Phase:** 10-importer-on-the-atomic-scheme
**Areas discussed:** Library suggestion & names, Footprint destination, Install gate in preview, Keywords & footprint tags

---

## Library suggestion & names

| Question | Options | Selected |
|----------|---------|----------|
| Family matches several stock libraries (CSD: 84 FET, 2 Diode) | Majority wins, others shown / Majority only if clear / Always ask | Majority wins, others shown |
| What "asks" looks like | Empty name + stem picker / Placeholder name like v1.0 / Separate popup | Empty name + stem picker |
| Which typed names are accepted | Atomic_ + official stem only / Atomic_ + anything not a brand / Official stem, warn otherwise | Atomic_ + official stem only |
| Old v1 libraries as targets | Hide them / Show greyed with a reason / Allow with a warning | Hide them |
| Stem list when KiCad not found | Built-in KiCad 10 stem list / Block importing / Accept existing Atomic_ only | Built-in KiCad 10 stem list |
| Category map inputs | Vendor category + description words + reference / Vendor category only / Everything incl. reference letter | Vendor category + description words + reference |
| How the suggestion source is shown | One plain line under the field / Tooltip only / Line + confidence colour | Tooltip only |
| Family prefix rule | Letters + first digit run / Leading letters only, 3+ / You decide | Letters + first digit run |
| Sibling lookup in own Atomic_ libraries | Own Atomic_ first, then stock / Stock only / Both, pooled count | Own Atomic_ first, then stock |
| Spelling of typed names | Auto-correct to official spelling / Refuse with a reason / Accept as typed | Auto-correct |
| Dropdown with 224 stems | Existing first, then searchable stems / Existing + suggested only / Grouped by first stem word | Existing first, then searchable stems |
| Brand-carrying official stems (MCU_Espressif) | Allowed: KiCad's own name / Fold to brand-free parent / Allowed but stop at family | Allowed: KiCad's own name |
| Non-device stems excluded (multi-select) | power, Simulation_SPICE, Graphic / Connector_Generic* / Device / Auxiliary_Items, Jumper, Mechanical | power, Simulation_SPICE, Graphic; Connector_Generic* |

**Notes:** The owner asked for more questions after the first round. The scout found brand names inside many official stems (MCU_ST_STM32F4, DSP_Texas), which led to the brand-stem question.

---

## Footprint destination

| Question | Options | Selected |
|----------|---------|----------|
| How to choose an official footprint | Toggle + searchable picker with hints / Toggle + plain text field / Toggle + full list, no ranking | Toggle + searchable picker with hints |
| Vendor 3D model with official footprint | Use KiCad's model, skip vendor's / Still install the vendor STEP / Ask per import | Use KiCad's model, skip vendor's |
| Name clash in shared Atomic_Footprints | Identical = reuse, different = conflict / Always a conflict row / Always rename to <FP>_<MPN> | Identical = reuse, different = conflict |
| Check official footprint before Install | Warn on pad mismatch / Block on pad mismatch / No check | Warn on pad mismatch |
| Default footprint name | Vendor name, editable / MPN-based / Package code + MPN | Vendor name, editable |
| Würth footprints as linked footprint | No: Atomic_Footprints or KiCad only / Yes, in the same picker | No |
| Several footprints in a package | All into Atomic_Footprints / Only the linked one / Extras only in vendor mode | (free text) "There should be only 1 footprint as it is an atomic library" |
| Follow-up: how to pick | Pick exactly one, others ignored / Pick one, keep others unlinked / Pick one per derived variant | Pick one per derived variant |
| Follow-up: where to build derived variants | Defer it; single choice now / Build it in Phase 10 / Defer, but block multi-footprint packages | Defer it; single choice now |

**Notes:** All five real samples ship one footprint, so derived variants could not be tested on real data. They were deferred under the project's sample-first rule.

---

## Install gate in preview

| Question | Options | Selected |
|----------|---------|----------|
| Value behaviour | Follows MPN, read-only / Defaults to MPN, editable / Follows until edited | Follows MPN, read-only |
| Manufacturer alias from vendor | Write the canonical name / Keep vendor text, offer a fix / Block until canonical | Write the canonical name |
| Missing 3D model | Blocking, "Add 3D model..." to fix / Blocking, but allow "install anyway" | Blocking, "Add 3D model..." to fix |
| How failures appear | Reason strip + amber field frames / Reason strip only / Separate "Atomic check" panel | Reason strip + amber field frames |

---

## Keywords & footprint tags

| Question | Options | Selected |
|----------|---------|----------|
| Vendor keywords | Merge, de-duplicated / Replace / Generated first, then vendor | Merge, de-duplicated |
| Editing UI | Plain text fields, pre-filled / Word chips / Text fields, generated shown separately | Plain text fields, pre-filled |
| Pitch and IPC name source | Computed from pad geometry / Only from vendor text / Pitch computed, no IPC name | Computed from pad geometry |
| Extra keyword sources (multi-select) | Runner-up category / Parent brand / Relational spec tokens / None beyond the list | All four ticked (contradictory) |
| Clarification | All three extras / Extras, no relational tokens / None beyond FLD-01 | "honestly, I have no idea" |
| Recommendation confirmed | Yes, that / You decide later | Yes: runner-up category + parent brand, no relational tokens |
| Vendor footprint description and tags | Description replaced, tags merged / Both merged / Both replaced | Description replaced, tags merged |

---

## Claude's Discretion

- Module layout, caching of stock-library and footprint indexes, the official-footprint ranking formula, how the incoming-part check sees planned files, reason wording, and retargeting the v1.0 suggestion tests.

## Deferred Ideas

- A derived (`extends`) variant per extra footprint in a multi-footprint package, each with its own MPN. It needs a real sample first.
- Relational spec tokens in generated keywords.
