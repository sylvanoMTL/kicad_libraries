---
status: diagnosed
phase: 09-atomic-rule-check-and-scan-detection
source: [09-VERIFICATION.md]
started: 2026-10-26T15:30:00Z
updated: 2026-10-26T16:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Library tree marks after a scan
Open the GUI on a scratch repo (build it with KICAD_ATOMIC_UAT_DIR, tests/test_atomic_uat.py) or on the live Custom/ and look at the library tree after a scan.
expected: Failing symbols carry the warning icon and amber row; New/Changed symbols carry the accent colour; libraries with problems auto-expand; tooltips read clearly (rich text, plain language)
result: issue
reported: "I am so confused by the UI and all the amber: we are in libraries, but the subnodes are the errors, that does not reference the component level. So I think the tree is missing the component level node. [Shown the mock-up Library > Component (Changed · 3 rules) > one row per problem:] seems a better representation, also the error/warnings should be collapsible at the component level."
severity: major
note: "Setup helper build_atomic_uat crashed on the live Custom/ (tests/test_atomic_uat.py:130, FFC2A32-06-T has no Datasheet field); setup finished by hand by editing Description instead." 

### 2. Check Atomic Parts on real parts (D-25)
Open Check Atomic Parts (Ctrl+Shift+A, or double-click a failing symbol) on real parts, tick fixes, preview and apply, then rescan.
expected: Dialog lists every violation per symbol, the preview matches what lands on disk, a backup exists, and the fixed violations are gone on the next scan
result: pass
note: "Exercised rename_alias, merge_alias, remove_leftover, canonical_manufacturer, value_to_mpn, fill_datasheet, fill_description and a rejected datasheet value; disk diff matched the preview, CRLF kept, backups byte-identical to originals. attach_model not exercised." 

### 3. Reason wording for the seven rules
Read the reason wording in the tooltip, log and dialog for each of the seven rules.
expected: Owner finds the wording plain and unambiguous
result: pass

### 4. Canonical manufacturer table
Review kicad_lib_manager/manufacturers.py for the Murata and TDK spellings and the acquired-brand entries (Maxim, Linear, InvenSense).
expected: Owner confirms the canonical names and aliases
result: pass
note: "Owner accepted the recommended options: short canonical names (Murata, TDK); acquired brands keep their own name (Maxim Integrated, Linear Technology, InvenSense); no extra manufacturers added." 

### 5. Undigited ${KICAD_3DMODEL_DIR}
Decide whether an undigited ${KICAD_3DMODEL_DIR} model path should resolve against KiCad's 3dmodels folder.
expected: Owner states the rule; today only ${KICADn_3DMODEL_DIR} (digited) resolves and the undigited form is reported as "Could not check the 3D model: it uses ${...}"
result: pass
note: "Owner kept the current rule: the undigited ${KICAD_3DMODEL_DIR} is not resolved (KiCad itself does not define it) and is reported as could-not-check." 

## Summary

total: 5
passed: 4
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- gap_id: G-09-1
  truth: "The library tree makes the component level obvious: each failing symbol is a row under its library, and its problems are listed as collapsible child rows under that symbol (not only in a tooltip)"
  status: failed
  reason: "User reported: the tree reads as library > errors with no component level; wants Library > Component (status, N rules) > one row per problem/warning, collapsible at the component level"
  severity: major
  test: 1
  root_cause: "LibraryTableWidget._make_symbol_row builds each symbol as a leaf row (name + 'N rules' in Status); violations and findings exist only in the row tooltip, so there is no visible problem level under the component and the synthetic UAT parts (named after their problem, e.g. DS-EMPTY) read as error rows rather than components. Design gap, not a regression."
  artifacts:
    - path: "kicad_lib_manager/widgets/library_table.py"
      issue: "_make_symbol_row (line ~234) adds no child rows for entry.violations / entry.findings; problems only reach the tooltip via _rich_tip"
    - path: "kicad_lib_manager/widgets/library_table.py"
      issue: "_on_sym_item_double_clicked (line ~339) only accepts a SymbolEntry row; a problem row under it must open the check dialog focused on its parent symbol"
    - path: "tests/test_library_table_atomic.py"
      issue: "asserts the current leaf-row shape; needs updating for the three-level tree"
    - path: "tests/test_atomic_uat.py"
      issue: "_edit_first_datasheet (line ~130) asserts every first symbol has a Datasheet field; crashes on the live Custom/ (FFC2A32-06-T has none), so the owner's UAT scratch build fails"
  missing:
    - "Add one inert, non-checkable child row per violation (amber, warning icon) and per finding (plain/note styling) under each symbol row, using the same plain-language text as today's tooltip"
    - "Symbol rows collapsible; collapsed by default so the library shows its component list with the 'Changed · N rules' count; libraries with problems still auto-expand to the component level"
    - "Double-clicking a problem row opens Check Atomic Parts focused on its parent symbol"
    - "Keep selection logic ignoring symbol and problem rows (check state only on library and group rows)"
    - "UAT helper: edit a field the symbol has (Description, falling back to adding Datasheet) instead of asserting Datasheet exists"
  debug_session: ""

## Deferred Follow-Ups

- test: 2
  idea: "kipart-search will resolve the BOM from library data plus online data for non-atomic components. A separate tool is needed later to re-associate atomic components from the KiCad libraries with their MPN data."
  deferred_at: 2026-10-26
