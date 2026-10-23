---
phase: quick-261023-qf7
plan: 01
subsystem: custom-library
tags: [kicad, footprint, abracon, atxk-h14, ipc-7351]
requires: [261023-ptg]
provides:
  - ATXK-H14 footprint in IPC-7351 zero orientation with pin-1 silk dot and chamfered fab body
  - re-runnable IPC-7351 checker for ATXK-H14
affects: [Custom submodule (local commit only, not pushed)]
key-files:
  modified:
    - Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod
  created:
    - .planning/quick/261023-qf7-rotate-atxk-h14-footprint-to-ipc-7351-po/check_atxk_h14.py
requirements: [INST-03]
status: complete
commits: 1
commit_scope: "1 commit inside the Custom submodule (7156bf0); 0 commits in the parent repo"
completed: 2026-10-23
---

# Phase quick-261023-qf7 Plan 01: Rotate ATXK-H14 to IPC-7351 Summary

Abracon ATXK-H14 footprint rotated 90 degrees CW to IPC-7351 zero orientation (portrait, pin 1 top-left), with a pin-1 silkscreen dot and a chamfered F.Fab body, proven a rotation (not a mirror) by an adapted checker running on the source and on kicad-cli 10's re-emitted copy.

## Custom commit

`7156bf0` in `Custom` (branch main, local only, not pushed): "Oscillator_TCXO_Abracon: rotate ATXK-H14 to IPC-7351 orientation, add pin-1 markers". Touches only `Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod` (76 insertions, 15 deletions). The parent `Custom` gitlink is neither staged nor committed.

## Results

- Pads: 1 (-0.5,-0.725), 2 (-0.5,0.725), 3 (0.5,0.725), 4 (0.5,-0.725), smd rect 0.7 x 0.85, no rotation. Each is the 261023-ptg centre mapped by (x,y) -> (-y,x); the 1->2->3 winding sign stays negative.
- Courtyard fp_rect (-1.1,-1.4)-(1.1,1.4), stroke 0.05.
- F.Fab: five fp_line (stroke 0.1) with the 0.3 mm pin-1 chamfer; `${REFERENCE}` at (0,0) rotated 90.
- F.SilkS: one filled dot, r 0.1 at (-1.15,-1.1); clearance to pad 1 is 0.200 mm. Reference at (0,-2.1), Value at (0,2.1).
- descr and Description say "pin 1 top-left (IPC-7351 orientation)". Datasheet, tags, Value and name unchanged; no model; Symbols/ identical to HEAD.
- File keeps version 20241229, CRLF, no BOM, no mixed EOL.

## Checker

- Before edit: `check_atxk_h14.py footprint` exit 1 (pad, size, rotation, courtyard, fab, silk, text and descr mismatches on source and kicad-cli); `symbol` exit 0.
- After edit: `check_atxk_h14.py all` exit 0 (footprint/source, footprint/kicad-cli, symbol/source, symbol/kicad-cli, cleanup all OK); re-run after the commit also exit 0.

## Tests

Scanner/corpus subset: before 333 passed, 3 skipped, 0 failed; after (post-edit and post-commit) 333 passed, 3 skipped, 0 failed. Failure set unchanged. Custom ahead of origin/main: 2 before, 3 after.

## Visual artefact

kicad-cli 10 has no footprint DRC, so an SVG was exported for visual review (exit 0, file exists):
`C:/Users/sylvain/AppData/Local/Temp/claude/c--Git-Repo-Clones-Kicad-Libraries-importer/d79baabd-cbac-4df6-ab86-f52273187e37/scratchpad/svg_qf7/ATXK-H14.svg`

## Deviations from Plan

None - plan executed exactly as written.

## Open items / owner notes

- ATXK-H14 still has no 3D model.
- The silk dot overhangs the courtyard by 0.15 mm in X, by design: the 0.25 mm IPC courtyard excess cannot hold a printable mark that is 0.15 mm clear of pad 1. KiCad has no footprint check against this.
- Custom main is now 3 ahead of origin/main (counting dd63768, 53816f9, 7156bf0). Push, then bump the parent gitlink when ready.
- Owner human check: open `Oscillator_TCXO_Abracon:ATXK-H14` (or the SVG) and confirm pin 1 top-left, 2 bottom-left, 3 bottom-right, 4 top-right, the dot left of pad 1, and the fab chamfer at the top-left corner.

## Known Stubs

None.

## Self-Check: PASSED

- check_atxk_h14.py: FOUND
- ATXK-H14.kicad_mod: FOUND
- Custom commit 7156bf0: FOUND (HEAD of Custom main)
