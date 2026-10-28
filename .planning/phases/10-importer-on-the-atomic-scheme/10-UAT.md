---
status: testing
phase: 10-importer-on-the-atomic-scheme
source: [10-VERIFICATION.md]
started: 2026-10-28T12:32:24.473Z
updated: 2026-10-28T12:32:24.473Z
---

## Current Test

number: 1
name: Owner decision on WR-06 (new in the incremental review)
expected: |
  A keep or fix decision. Keep: the owner's rule of 2026-10-28 ('tied matches supply the family only when they all agree') is applied as decided, and the pin-count residual already reported for a lone match (10-26 SUMMARY) now also covers small agreeing ties. Fix: a gap-closure plan adds the review's pad-count filter (a leading-letters-only tie counts only footprints within one pad of the vendor footprint's pad count) or raises the minimum score to 50, plus a test with a two-footprint SON-8 folder and a 6-pad vendor footprint asserting no family.
awaiting: user response

## Tests

### 1. Owner decision on WR-06 (new in the incremental review): a package family can still come from a small leading-letters-only tie whose footprints all name the same family, with no pin-count check. Reproduced on the installed KiCad 10 footprints: the 6-pin vendor codes SON50P150X150X60-6N and SON65P200X200X80-6N tie Package_SON:MicroCrystal_C7_SON-8_1.5x3.2mm_P0.9mm and Package_SON:SON-8-1EP_3x2mm_P0.5mm_EP1.4x1.6mm at score 30, and both name SON-8, so SON-8 is written into the footprint description, tags and symbol keywords when the vendor footprint's own text names no family.
expected: A keep or fix decision. Keep: the owner's rule of 2026-10-28 ('tied matches supply the family only when they all agree') is applied as decided, and the pin-count residual already reported for a lone match (10-26 SUMMARY) now also covers small agreeing ties. Fix: a gap-closure plan adds the review's pad-count filter (a leading-letters-only tie counts only footprints within one pad of the vendor footprint's pad count) or raises the minimum score to 50, plus a test with a two-footprint SON-8 folder and a 6-pad vendor footprint asserting no family.
result: [pending]

### 2. Setup S1: build the scratch repo. PowerShell, from the repo root: `$env:KICAD_ATOMIC_UAT_DIR = "$env:TEMP\kicad_atomic_uat"` then `env\Scripts\python.exe -m pytest tests/test_atomic_uat.py -k uat_atomic_scratch -s`. The output holds a line "Run the app on it: <command>"; the "Check in the app:" lines after it belong to the Phase 9 check, so skip them.
expected: The test passes and prints "Run the app on it: <command>".
result: [pending]

### 3. Setup S2 and S3: `mkdir "$env:TEMP\kicad_atomic_uat\tables"`. Run the command printed in S1. In the main window's toolbar set "Destination:" to that tables folder. If the app offers to change KiCad's path variables at any point, click No.
expected: The scratch app opens with Destination pointing at the scratch tables folder.
result: [pending]

### 4. Check 1 [criterion 1]: Ctrl+I (Import Part...), pick downloaded_examples\ul_CSD85301Q2.zip. Read the library field, hover it, and look under it.
expected: The library field reads Atomic_Transistor_FET. Tooltip: "Suggested from 75 similar parts in KiCad's Transistor_FET. Other matches: Diode (2)." The badge next to it reads "new - creates .kicad_sym". There is no amber token line under the field.
result: [pending]

### 5. Check 2 [criterion 4]: In the same dialog read the amber strip, click "Type a Description", then type "Dual N-channel MOSFET 30 V" in the Description field.
expected: The strip reads "⚠ Install is blocked: Type a Description". Clicking the reason puts the cursor in the Description field and its frame turns amber. After typing, the reason and the amber frame go at once, and Install Part enables after the preview updates.
result: [pending]

### 6. Check 3 [criteria 3, 4, 5]: Look at Value, Manufacturer, Footprint, the Files list, Footprint description, Footprint tags and Keywords.
expected: Value is greyed out and reads CSD85301Q2. Manufacturer reads Texas Instruments. The Footprint field reads Atomic_Footprints:DQK0006B. Files lists Custom/Footprints/Atomic_Footprints.pretty/DQK0006B.kicad_mod and nothing named Atomic_Transistor_FET.pretty. Footprint description reads "WSON-6 2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B". Footprint tags contain WSON-6, DQK0006B and P0.65mm. Keywords contain Transistor, FET, TI and Texas.
result: [pending]

### 7. Check 4 [criterion 2]: Type each name into the library field and read the strip: "Transistor_FET"; "Atomic_TI"; "atomic_transistor_fet" then Tab; "fet". Then open the dropdown.
expected: "Transistor_FET" gives "Transistor_FET is the name of a KiCad library; use Atomic_Transistor_FET". "Atomic_TI" gives "Atomic_TI is not a library name: after Atomic_ comes a KiCad library name, such as Atomic_Transistor_FET". "atomic_transistor_fet" then Tab turns the text into Atomic_Transistor_FET with the grey note "Spelling corrected to Atomic_Transistor_FET" under the field. "fet" makes the list show only names containing fet. The dropdown shows your Atomic_ libraries first, a divider, then the rest; no IC_... or Connector_..._GCT name.
result: [pending]

### 8. Check 5 [criterion 3]: Click "Use an official KiCad footprint". Read the list, pick Package_SON:Texas_DQK, read the Footprint field, the Not used section and the footprint name and text fields. Then click "Install the vendor footprint into Atomic_Footprints" to switch back.
expected: Package_SON:Texas_DQK is first in the list. The Footprint field reads Package_SON:Texas_DQK. Not used lists DQK0006B ("footprint, not installed: an official KiCad footprint is used") and DLV0006A.stp ("3D model, not installed: KiCad's own 3D model is used"). The footprint name and the two footprint text fields are greyed with "KiCad's own footprints are never changed". No pad warning appears.
result: [pending]

### 9. Check 6 [criterion 3]: Click Install Part. Then look at the result banner, the Library tables row and the scratch tables folder.
expected: The result banner reads "✓ Installed CSD85301Q2 into Atomic_Transistor_FET". The Library tables row reads "Added Atomic_Transistor_FET to sym-lib-table and Atomic_Footprints to fp-lib-table" (the scratch repo has Atomic_Footprints.pretty, and the empty tables folder of S2 does not list it, so it is added). The tables folder of S2 now holds sym-lib-table and fp-lib-table.
result: [pending]

### 10. Check 7 [criteria 1, 4]: Click Change..., pick downloaded_examples\LIB_RS3-1212S_H3.zip. Read the library field, hover it, read Field changes.
expected: The library field reads Atomic_Converter_DCDC_Isolated; tooltip "Suggested from the vendor category Power Supply and the description." Field changes shows "Set Manufacturer" with "RECOM Power → RECOM: canonical spelling". Install Part enables without typing anything.
result: [pending]

### 11. Check 8 [criteria 1, 4]: Click Change..., pick downloaded_examples\ul_ATXK-H14-D-32-768KHZ-E50-T3.zip. Read the library field and the strip, then click the 3D model reason.
expected: The library field is empty with the grey hint "Pick a library, or type Atomic_ and a KiCad library name". The strip lists "Pick or type a library name", "Enter the Manufacturer", "The Datasheet must be a link or a file path" and a reason starting "3D model:". Clicking the 3D model reason moves the focus to the Add 3D model... button.
result: [pending]

### 12. Check 9 [criterion 4]: Click Change..., pick downloaded_examples\USB4145-03-0170-C_REVA2.zip. Read the library field and the strip. Click Add 3D model..., pick downloaded_examples\194150990-659-usb4145-03-0170-c.zip.
expected: The library field reads Atomic_Connector. The strip lists "Enter a Datasheet link" and a reason starting "3D model:". After adding the model, the 3D model reason goes away.
result: [pending]

### 13. Check 10 [criterion 5]: In KiCad 10, Symbol Editor, File > Add Library..., pick <scratch>\Custom\Symbols\Atomic_Transistor_FET.kicad_sym and add it to the PROJECT library table only, never Global (Global edits the owner's real library tables). Open CSD85301Q2's Symbol Properties. Then Footprint Editor, add <scratch>\Custom\Footprints\Atomic_Footprints.pretty, again to the PROJECT table only, and open DQK0006B's Footprint Properties. Afterwards remove both libraries from the Project library table.
expected: The symbol's Keywords equal the Keywords of check 3. The footprint's Description and Keywords equal the footprint description and tags of check 3. Both libraries are removed from the Project table afterwards.
result: [pending]

### 14. Check 11 (owner decision): Say whether to keep or change: strict majority for sibling votes, ATXK-H14 asking instead of suggesting Atomic_Oscillator, the measured "2.1x2.1 mm" instead of KiCad's nominal "2x2 mm", and the IPC-style tag WSON-6_2.1x2.1mm_P0.65mm.
expected: A keep or change decision for each of the four behaviours.
result: [pending]

## Summary

total: 14
passed: 0
issues: 0
pending: 14
skipped: 0
blocked: 0

## Gaps
