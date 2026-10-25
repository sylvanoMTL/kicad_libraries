---
phase: quick-261023-ptg
plan: 01
subsystem: custom-library-content
tags: [kicad, footprint, symbol, abracon, tcxo, custom-submodule]
requires: []
provides:
  - "ATXK-H14 footprint pads numbered per datasheet top view"
  - "ATXK-H14 symbol with correct datasheet, metadata, hidden Manufacturer, pin 1 OE"
  - "check_atxk_h14.py re-runnable checker"
affects: [Custom submodule (Oscillator_TCXO_Abracon)]
key-files:
  created:
    - .planning/quick/261023-ptg-fix-abracon-atxk-h14-tcxo-mirrored-footp/check_atxk_h14.py
  modified:
    - Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod
    - Custom/Symbols/Oscillator_TCXO_Abracon.kicad_sym
  deleted:
    - Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATX-14.kicad_mod
decisions:
  - "No pin-1 graphic added; the footprint never had one (open item for the owner)"
requirements: [INST-03]
status: complete
commits: 1
plan_head_before: 5250afc
plan_head_after: 5250afc
custom_commit: 53816f9
actuals:
  tokens: 14000
  tasks: 3
  commits: 1
---

# Phase quick-261023-ptg Plan 01: Fix Abracon ATXK-H14 TCXO Summary

ATXK-H14 footprint pads renumbered to the datasheet top view (1 BL, 2 BR, 3 TR, 4 TL), symbol metadata and pin 1 (OE) corrected, unused mirrored ATX-14 footprint deleted, all in one local commit inside the Custom submodule.

## Custom commit

- `53816f9` in `Custom` (main): "Oscillator_TCXO_Abracon: fix ATXK-H14 mirrored pads and symbol data, drop ATX-14"
- Contains exactly: M `Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod`, D `Footprints/Oscillator_TCXO_Abracon.pretty/ATX-14.kicad_mod`, M `Symbols/Oscillator_TCXO_Abracon.kicad_sym`.
- Not pushed. Parent `Custom` gitlink not staged or committed (`git diff --cached --name-only` is empty; parent shows ` M Custom`).
- `plan_head_before`/`plan_head_after` refer to the parent repo, which this plan did not commit to (the Custom commit lives in the submodule; the docs commit is handled by the orchestrator).

## Checker results

`check_atxk_h14.py all` (kicad-cli 10.0.7, output only to a temp dir):

- Before the edits: exit 1, 30 FAIL lines (mirrored pads, empty footprint Datasheet/Description, missing descr/tags, old symbol Datasheet/Description/keywords/filters, no Manufacturer, pin 1 "Ctrl", ATX-14 file present).
- After the edits and again after the commit: exit 0.
  ```
  OK footprint/source
  OK footprint/kicad-cli
  OK symbol/source
  OK symbol/kicad-cli
  OK cleanup
  ```
- Source version headers unchanged (footprint 20241229, symbol 20241209), no BOM, no mixed EOL (CRLF preserved).

## Tests (scanner/corpus subset)

- Before: `334 passed, 3 skipped`, 0 failed.
- After: `333 passed, 3 skipped`, 0 failed.
- Failure set unchanged (0 before, 0 after). The one-case drop in passed count is the per-file corpus case for the deleted ATX-14 footprint, as anticipated in the plan.

## Reference check before deleting ATX-14

```
$ grep -rn "Oscillator_TCXO_Abracon:ATX-14" Custom/
(no output)
$ grep -rln "ATX-14" Custom/
Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATX-14.kicad_mod
Custom/Symbols/Oscillator_TCXO_Abracon.kicad_sym
```
The symbol hit was the old Datasheet URL, fixed in the same commit. No other file referenced it, so deletion proceeded.

## Deviations from Plan

None - plan executed as written. Task 1 and Task 2 produced no separate commits, since the plan specifies a single Custom commit in Task 3.

## Open items for the owner

- The ATXK-H14 footprint has no pin-1 marker on silkscreen or fab; none existed to move and none was invented. Decide whether to add one.
- No 3D model is attached to ATXK-H14 (owner will download one).
- Visual check: open `Oscillator_TCXO_Abracon:ATXK-H14` in the Footprint Editor against datasheet rev 09-05-25 p.3 (top view), and confirm symbol pin 1 reads OE.
- Push Custom main (now 2 ahead of origin/main, counting the earlier unpushed dd63768) and bump the parent gitlink when ready.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- check_atxk_h14.py: FOUND
- Custom commit 53816f9: FOUND (ancestor of Custom HEAD)
- ATX-14.kicad_mod: removed
