---
status: partial
phase: 10-importer-on-the-atomic-scheme
source: [10-VERIFICATION.md]
started: 2026-10-28T12:32:24.473Z
updated: 2026-10-28T21:32:28.849Z
---

## Current Test

[testing complete]

## Tests

### 1. Owner decision on WR-06 (new in the incremental review): a package family can still come from a small leading-letters-only tie whose footprints all name the same family, with no pin-count check. Reproduced on the installed KiCad 10 footprints: the 6-pin vendor codes SON50P150X150X60-6N and SON65P200X200X80-6N tie Package_SON:MicroCrystal_C7_SON-8_1.5x3.2mm_P0.9mm and Package_SON:SON-8-1EP_3x2mm_P0.5mm_EP1.4x1.6mm at score 30, and both name SON-8, so SON-8 is written into the footprint description, tags and symbol keywords when the vendor footprint's own text names no family.
expected: A keep or fix decision. Keep: the owner's rule of 2026-10-28 ('tied matches supply the family only when they all agree') is applied as decided, and the pin-count residual already reported for a lone match (10-26 SUMMARY) now also covers small agreeing ties. Fix: a gap-closure plan adds the review's pad-count filter (a leading-letters-only tie counts only footprints within one pad of the vendor footprint's pad count) or raises the minimum score to 50, plus a test with a two-footprint SON-8 folder and a 6-pad vendor footprint asserting no family.
result: issue
reported: "fix (owner decision: fix WR-06 with the pad-count filter, as recommended)"
severity: major

### 2. Setup S1: build the scratch repo. PowerShell, from the repo root: `$env:KICAD_ATOMIC_UAT_DIR = "$env:TEMP\kicad_atomic_uat"` then `env\Scripts\python.exe -m pytest tests/test_atomic_uat.py -k uat_atomic_scratch -s`. The output holds a line "Run the app on it: <command>"; the "Check in the app:" lines after it belong to the Phase 9 check, so skip them.
expected: The test passes and prints "Run the app on it: <command>".
result: pass
source: automated (run by Claude: 1 passed, printed 'Run the app on it: env\Scripts\python.exe C:\Users\sylvain\AppData\Local\Temp\kicad_atomic_uat\repo\kicad_lib_manager.py')

### 3. Setup S2 and S3: `mkdir "$env:TEMP\kicad_atomic_uat\tables"`. Run the command printed in S1. In the main window's toolbar set "Destination:" to that tables folder. If the app offers to change KiCad's path variables at any point, click No.
expected: The scratch app opens with Destination pointing at the scratch tables folder.
result: pass
source: automated (Claude drove the real app offscreen on the scratch repo, KiCad 10 footprints, sandboxed APPDATA and QSettings; scratchpad uat10/drive_uat10.py)
observed: app started on the scratch repo, KiCad footprints C:/Program Files/KiCad/10.0/share/kicad/footprints, Destination set to the scratch tables folder; no path-variable prompt

### 4. Check 1 [criterion 1]: Ctrl+I (Import Part...), pick downloaded_examples\ul_CSD85301Q2.zip. Read the library field, hover it, and look under it.
expected: The library field reads Atomic_Transistor_FET. Tooltip: "Suggested from 75 similar parts in KiCad's Transistor_FET. Other matches: Diode (2)." The badge next to it reads "new - creates .kicad_sym". There is no amber token line under the field.
result: pass
source: automated (Claude drove the real app offscreen on the scratch repo, KiCad 10 footprints, sandboxed APPDATA and QSettings; scratchpad uat10/drive_uat10.py)
observed: Atomic_Transistor_FET; tooltip 'Suggested from 75 similar parts in KiCad's Transistor_FET. Other matches: Diode (2).'; badge 'new - creates .kicad_sym'; no extra line under the field

### 5. Check 2 [criterion 4]: In the same dialog read the amber strip, click "Type a Description", then type "Dual N-channel MOSFET 30 V" in the Description field.
expected: The strip reads "⚠ Install is blocked: Type a Description". Clicking the reason puts the cursor in the Description field and its frame turns amber. After typing, the reason and the amber frame go at once, and Install Part enables after the preview updates.
result: pass
source: automated (Claude drove the real app offscreen on the scratch repo, KiCad 10 footprints, sandboxed APPDATA and QSettings; scratchpad uat10/drive_uat10.py)
observed: strip '⚠ Install is blocked: Type a Description'; the link focuses Description, its frame is blocked; right after typing the reason and frame clear (strip shows Updating preview...); Install enabled after the plan

### 6. Check 3 [criteria 3, 4, 5]: Look at Value, Manufacturer, Footprint, the Files list, Footprint description, Footprint tags and Keywords.
expected: Value is greyed out and reads CSD85301Q2. Manufacturer reads Texas Instruments. The Footprint field reads Atomic_Footprints:DQK0006B. Files lists Custom/Footprints/Atomic_Footprints.pretty/DQK0006B.kicad_mod and nothing named Atomic_Transistor_FET.pretty. Footprint description reads "WSON-6 2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B". Footprint tags contain WSON-6, DQK0006B and P0.65mm. Keywords contain Transistor, FET, TI and Texas.
result: pass
source: automated (Claude drove the real app offscreen on the scratch repo, KiCad 10 footprints, sandboxed APPDATA and QSettings; scratchpad uat10/drive_uat10.py)
observed: Value CSD85301Q2 read-only; Manufacturer Texas Instruments; Footprint Atomic_Footprints:DQK0006B; Files has Custom/Footprints/Atomic_Footprints.pretty/DQK0006B.kicad_mod, no Atomic_Transistor_FET.pretty; fp description exact; tags 'CSD85301Q2 WSON-6 WSON-6_2.1x2.1mm_P0.65mm DQK0006B P0.65mm'; keywords 'CSD85301Q2 Transistor FET MOSFET N-channel WSON-6 DQK0006B TI Texas Diode'

### 7. Check 4 [criterion 2]: Type each name into the library field and read the strip: "Transistor_FET"; "Atomic_TI"; "atomic_transistor_fet" then Tab; "fet". Then open the dropdown.
expected: "Transistor_FET" gives "Transistor_FET is the name of a KiCad library; use Atomic_Transistor_FET". "Atomic_TI" gives "Atomic_TI is not a library name: after Atomic_ comes a KiCad library name, such as Atomic_Transistor_FET". "atomic_transistor_fet" then Tab turns the text into Atomic_Transistor_FET with the grey note "Spelling corrected to Atomic_Transistor_FET" under the field. "fet" makes the list show only names containing fet. The dropdown shows your Atomic_ libraries first, a divider, then the rest; no IC_... or Connector_..._GCT name.
result: pass
source: automated (Claude drove the real app offscreen on the scratch repo, KiCad 10 footprints, sandboxed APPDATA and QSettings; scratchpad uat10/drive_uat10.py)
observed: both refusal texts exact; atomic_transistor_fet + Tab (through the completer popup) becomes Atomic_Transistor_FET with note 'Spelling corrected to Atomic_Transistor_FET'; 'fet' lists Atomic_Driver_FET, Atomic_Transistor_FET, Atomic_Transistor_FET_Other; dropdown Atomic_Battery_Management, Atomic_Connector, divider, then the rest; no IC_ or Connector_..._GCT

### 8. Check 5 [criterion 3]: Click "Use an official KiCad footprint". Read the list, pick Package_SON:Texas_DQK, read the Footprint field, the Not used section and the footprint name and text fields. Then click "Install the vendor footprint into Atomic_Footprints" to switch back.
expected: Package_SON:Texas_DQK is first in the list. The Footprint field reads Package_SON:Texas_DQK. Not used lists DQK0006B ("footprint, not installed: an official KiCad footprint is used") and DLV0006A.stp ("3D model, not installed: KiCad's own 3D model is used"). The footprint name and the two footprint text fields are greyed with "KiCad's own footprints are never changed". No pad warning appears.
result: pass
source: automated (Claude drove the real app offscreen on the scratch repo, KiCad 10 footprints, sandboxed APPDATA and QSettings; scratchpad uat10/drive_uat10.py)
observed: Package_SON:Texas_DQK first of 15464; Footprint field Package_SON:Texas_DQK; Not used lists DQK0006B and DLV0006A.stp with the exact texts; fp name and both fp text fields disabled with 'KiCad's own footprints are never changed'; no pad warning; switching back restores Atomic_Footprints:DQK0006B

### 9. Check 6 [criterion 3]: Click Install Part. Then look at the result banner, the Library tables row and the scratch tables folder.
expected: The result banner reads "✓ Installed CSD85301Q2 into Atomic_Transistor_FET". The Library tables row reads "Added Atomic_Transistor_FET to sym-lib-table and Atomic_Footprints to fp-lib-table" (the scratch repo has Atomic_Footprints.pretty, and the empty tables folder of S2 does not list it, so it is added). The tables folder of S2 now holds sym-lib-table and fp-lib-table.
result: pass
source: automated (Claude drove the real app offscreen on the scratch repo, KiCad 10 footprints, sandboxed APPDATA and QSettings; scratchpad uat10/drive_uat10.py)
observed: banner '✓ Installed CSD85301Q2 into Atomic_Transistor_FET'; tables row 'Added Atomic_Transistor_FET to sym-lib-table and Atomic_Footprints to fp-lib-table'; tables folder holds fp-lib-table and sym-lib-table; no path-variable prompt

### 10. Check 7 [criteria 1, 4]: Click Change..., pick downloaded_examples\LIB_RS3-1212S_H3.zip. Read the library field, hover it, read Field changes.
expected: The library field reads Atomic_Converter_DCDC_Isolated; tooltip "Suggested from the vendor category Power Supply and the description." Field changes shows "Set Manufacturer" with "RECOM Power → RECOM: canonical spelling". Install Part enables without typing anything.
result: pass
source: automated (Claude drove the real app offscreen on the scratch repo, KiCad 10 footprints, sandboxed APPDATA and QSettings; scratchpad uat10/drive_uat10.py)
observed: Atomic_Converter_DCDC_Isolated; tooltip 'Suggested from the vendor category Power Supply and the description.'; Field changes 'Set Manufacturer | RECOM Power → RECOM: canonical spelling'; Install enabled without typing

### 11. Check 8 [criteria 1, 4]: Click Change..., pick downloaded_examples\ul_ATXK-H14-D-32-768KHZ-E50-T3.zip. Read the library field and the strip, then click the 3D model reason.
expected: The library field is empty with the grey hint "Pick a library, or type Atomic_ and a KiCad library name". The strip lists "Pick or type a library name", "Enter the Manufacturer", "The Datasheet must be a link or a file path" and a reason starting "3D model:". Clicking the 3D model reason moves the focus to the Add 3D model... button.
result: issue
reported: "fix (owner, after Claude's automated run: with the library field empty the strip lists only 'Pick or type a library name'; Enter the Manufacturer, The Datasheet must be a link or a file path, Type a Description and the 3D model reason appear only after a library is typed)"
severity: minor
source: automated (scratchpad uat10/drive_uat10.py and probe_uat10.py); the 3D model reason link does focus Add 3D model...

### 12. Check 9 [criterion 4]: Click Change..., pick downloaded_examples\USB4145-03-0170-C_REVA2.zip. Read the library field and the strip. Click Add 3D model..., pick downloaded_examples\194150990-659-usb4145-03-0170-c.zip.
expected: The library field reads Atomic_Connector. The strip lists "Enter a Datasheet link" and a reason starting "3D model:". After adding the model, the 3D model reason goes away.
result: pass
source: automated (Claude drove the real app offscreen on the scratch repo, KiCad 10 footprints, sandboxed APPDATA and QSettings; scratchpad uat10/drive_uat10.py)
observed: Atomic_Connector; strip 'Enter a Datasheet link' and '3D model: the footprint has no 3D model. Use Add 3D model... or an official KiCad footprint'; after attaching usb4145-03-0170-c.stp only 'Enter a Datasheet link' remains

### 13. Check 10 [criterion 5]: In KiCad 10, Symbol Editor, File > Add Library..., pick <scratch>\Custom\Symbols\Atomic_Transistor_FET.kicad_sym and add it to the PROJECT library table only, never Global (Global edits the owner's real library tables). Open CSD85301Q2's Symbol Properties. Then Footprint Editor, add <scratch>\Custom\Footprints\Atomic_Footprints.pretty, again to the PROJECT table only, and open DQK0006B's Footprint Properties. Afterwards remove both libraries from the Project library table.
expected: The symbol's Keywords equal the Keywords of check 3. The footprint's Description and Keywords equal the footprint description and tags of check 3. Both libraries are removed from the Project table afterwards.
result: pass
source: automated (KiCad 10.0.7 kicad-cli loaded and plotted the scratch symbol CSD85301Q2 and footprint DQK0006B; no library table was edited) plus owner check (the owner's own import CM315D32768DZFT in Atomic_Oscillator opened in KiCad 10 and was placed)
observed: ki_keywords 'CSD85301Q2 Transistor FET MOSFET N-channel WSON-6 DQK0006B TI Texas Diode' and footprint descr 'WSON-6 2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B', tags 'CSD85301Q2 WSON-6 WSON-6_2.1x2.1mm_P0.65mm DQK0006B P0.65mm', equal to check 3

### 14. Check 11 (owner decision): Say whether to keep or change: strict majority for sibling votes, ATXK-H14 asking instead of suggesting Atomic_Oscillator, the measured "2.1x2.1 mm" instead of KiCad's nominal "2x2 mm", and the IPC-style tag WSON-6_2.1x2.1mm_P0.65mm.
expected: A keep or change decision for each of the four behaviours.
result: [pending]

## Summary

total: 14
passed: 11
issues: 2
pending: 1
skipped: 0
blocked: 0

## Gaps

- gap_id: G-10-1
  truth: "A package family is taken from tied KiCad footprint matches only when their pad count is within one of the vendor footprint's pad count (WR-06)"
  status: failed
  reason: "User reported: fix (owner decision: fix WR-06 with the pad-count filter). A 6-pin vendor footprint (SON50P150X150X60-6N, SON65P200X200X80-6N) gets SON-8 from two score-30 tied KiCad matches, written into footprint description, tags and symbol keywords."
  severity: major
  test: 1
  artifacts: []
  missing:
    - "Pad-count filter on leading-letters-only ties: count only footprints within one pad of the vendor footprint's pad count"
    - "Test: two-footprint SON-8 folder plus a 6-pad vendor footprint asserts no family"

- gap_id: G-10-11
  truth: "With the library field empty, the strip lists every reason Install is blocked at once: the library name, Enter the Manufacturer, The Datasheet must be a link or a file path, Type a Description and the 3D model reason"
  status: failed
  reason: "User reported: fix. ATXK-H14 with no library shows only 'Pick or type a library name'; the other reasons appear only after a library is typed."
  severity: minor
  test: 11
  artifacts:
    - path: "kicad_lib_manager/importer/planner.py"
      issue: "build_plan returns refuse(install.invalid_library) before the incoming atomic checks run, so the plan carries no other ERROR Issues"
  missing:
    - "Run the incoming checks (manufacturer, datasheet, description, 3D model) even when the library name is empty or refused, so blocking_reasons lists them all"
    - "Test: ATXK-H14 with an empty library lists all reasons at once"
