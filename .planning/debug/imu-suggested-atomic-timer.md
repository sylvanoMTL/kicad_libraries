---
status: diagnosed
trigger: "G-13-1-f: migration planner suggested ICM-42688-P (IMU, from IC_IMU_TDK) into Atomic_Timer instead of Atomic_Sensor_Motion, with no strip line"
created: 2026-11-12T18:00:00Z
updated: 2026-11-12T18:40:00Z
goal: find_root_cause_only
gap_id: G-13-1-f
---

## Current Focus

bug_class: Bohrbug (deterministic; same input -> same Atomic_Timer every run)
hypothesis: CONFIRMED - the KiCad stock sibling vote decides on the bare letters "ICM" (family_prefixes drops everything after the hyphen), where Intersil ICM7xxx timers (4 in Timer) outnumber InvenSense ICM-2xxxx IMUs (2 in Sensor_Motion); the vote runs before the category map, and nothing in the gate or dialog flags a split-vote suggestion.
test: scratchpad/repro_imu.py against the real KiCad 10 stock + temp Custom/ (done)
expecting: Atomic_Timer, source stock, counts Timer 4 / Sensor_Motion 2 (observed)
next_action: return ROOT CAUSE FOUND to caller (goal find_root_cause_only)

reasoning_checkpoint:
  hypothesis: "ICM-42688-P is filed in Atomic_Timer because siblings.family_prefixes('ICM-42688-P') yields only ['ICM'] and siblings.pick lets the >50% library of that step win (Timer 4 of 6), and suggest_library returns that stock pick before categories.classify is consulted."
  confirming_evidence:
    - "pick(stock_index(KiCad 10), 'ICM-42688-P') == SiblingPick(stem='Timer', prefix='ICM', counts=(('Timer',4),('Sensor_Motion',2)))"
    - "full migration pipeline on temp Custom/ -> PartPlan.target_library='Atomic_Timer', suggestion.source='stock'; gate strip has only 'Enter the Manufacturer'"
    - "description with 'IMU accelerometer gyroscope' still gives Atomic_Timer: the stock vote preempts the words rule"
  falsification_test: "If pick returned None or Sensor_Motion for ICM-42688-P, or if suggest_library consulted classify before stock, the hypothesis would fail. Observed neither."
  fix_rationale: "n/a (diagnose only)"
  blind_spots: "The UAT dump's suggestion=None could not be reproduced (repro shows it populated); the dump script is not available. Did not test Phase 10 Import Part UI, which shares suggest_library and would mis-file any new ICM-xxxxx the same way until Atomic_Sensor_Motion exists in the owner's libraries."
  candidate_causes:
    - "code: family_prefixes regex ([A-Za-z]+)(\d+)? stops at '-' so only the 3-letter step exists"
    - "code: pick accepts a bare simple-majority at the coarsest step; suggest_library ranks any decided stock vote above the description words"
    - "data: KiCad 10 stock has 4 Intersil ICM7xxx in Timer vs 2 ICM-2xxxx in Sensor_Motion, and no ICM-42688-P; part has empty MPN/keywords and a description with no category word"
    - "design/UI: 13-CONTEXT accepted the mis-suggestion; gate has no low-confidence line; dialog shows a suggestion identically to a choice"
  and_gate: "yes - the wrong library needs (1) the hyphen-truncated prefix AND (2) the Timer-majority stock data AND (3) stock vote preempting the category map; silent acceptance additionally needs (4) no gate/UI signal for a split-vote suggestion."

## Symptoms

expected: The planner suggests Atomic_Sensor_Motion for ICM-42688-P (6-axis MEMS motion sensor) from the part's own data (Phase 13 D-01); a wrong suggestion should at least not be silently accepted.
actual: Live run on real Custom/ (headless planner dump, no owner choice): ICM-42688-P from Custom/Symbols/IC_IMU_TDK.kicad_sym planned with target_library='Atomic_Timer', suggestion=None in PartPlan dump. Fields: Datasheet=TDK URL, Description='High Precision 6-Axis MEMS MotionTrackingTM Device', Footprint='Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y', ki_keywords='', Manufacturer='', MPN='', Value='ICM-42688-P'. No strip line. Other parts suggested correctly, all with suggestion=None too.
errors: None.
reproduction: migration fixture (tests/migrationfixtures.py) with ICM-42688-P, fields above, official LGA-14 footprint, v1 library IC_IMU_TDK; run read_inventory + detect_tools + prepare_context + build_migration_plan with empty MigrationChoices; inspect PartPlan.target_library. KiCad 10 stock symbols at C:\Program Files\KiCad\10.0\share\kicad\symbols.
started: Discovered during UAT on 2026-11-12 (anticipated in 13-RESEARCH.md Open Question 2 and accepted in 13-CONTEXT Claude's Discretion).

## Eliminated

## Evidence

- timestamp: 2026-11-12T18:00:00Z
  checked: 13-RESEARCH.md lines 466, 475, 656 and 13-CONTEXT.md line 162
  found: Research already ran pick(stock, "ICM-42688-P") -> SiblingPick(stem='Timer', prefix='ICM', counts=(('Timer', 4), ('Sensor_Motion', 2))). CONTEXT Claude's Discretion accepted the mis-file ("Phase 10 suggestion behaviour is not changed; the owner corrects it in the preview").
  implication: The mis-suggestion was known before planning and deliberately not fixed; the open question for this session is to confirm the mechanism in code and explain why nothing flags it to the owner.

- timestamp: 2026-11-12T18:10:00Z
  checked: suggest.py suggest_library, siblings.py family_prefixes/pick, migration/planner.py prepare_context/part_meta, migration/symbols.py target_libraries
  found: Order is own Atomic_ siblings -> KiCad stock siblings -> category map -> ask. part = meta.mpn or meta.symbol_name ("ICM-42688-P", MPN empty). family_prefixes uses re `([A-Za-z]+)(\d+)?` which stops at the hyphen, so ICM-42688-P yields only ["ICM"] (the coarsest step). pick() returns the first prefix step with any match and the library with >50% of those matches wins. target_libraries copies suggestion.name when no owner choice.
  implication: A 3-letter manufacturer-style prefix shared by unrelated vendors decides the library; the category map is never consulted once the stock vote decides.

- timestamp: 2026-11-12T18:15:00Z
  checked: KiCad 10 stock symbols (C:/Program Files/KiCad/10.0/share/kicad/symbols) for top-level ICM* symbols and for 42688
  found: Sensor_Motion: ICM-20602, ICM-20948 (2). Timer: ICM7209, ICM7555xB, ICM7555xP, ICM7556 (4, Intersil CMOS timers). No stock library contains ICM-42688-P (grep 42688 -> nothing); the symptom note that Sensor_Motion contains it is incorrect.
  implication: Intersil ICM7xxx timers outnumber InvenSense ICM-xxxxx IMUs 4:2 under the bare "ICM" prefix.

- timestamp: 2026-11-12T18:20:00Z
  checked: scratch repro (scratchpad/repro_imu.py) with real KiCad 10 stock index + temp Custom/IC_IMU_TDK.kicad_sym carrying the live fields; full read_inventory + detect_tools + prepare_context + build_migration_plan(MigrationChoices()) + check_plan
  found: pick(stock,"ICM-42688-P") = SiblingPick(stem='Timer', prefix='ICM', counts=(('Timer',4),('Sensor_Motion',2))). suggest_library -> name='Atomic_Timer', source='stock', reason "Suggested from 4 similar parts in KiCad's Timer", alternatives (Atomic_Sensor_Motion, 2). classify(meta) alone -> stem None (description has no imu/accelerometer/gyroscope word). PartPlan.target_library='Atomic_Timer', PartPlan.suggestion populated (NOT None). Gate: run_enabled False, only strip line "ICM-42688-P: Enter the Manufacturer"; nothing about the library.
  implication: Root cause reproduced deterministically. suggestion=None in the UAT dump is an artifact of how that dump was produced, not of the planner. The gate has no library-confidence check, so once Manufacturer is filled Run accepts Atomic_Timer.

- timestamp: 2026-11-12T18:22:00Z
  checked: same repro, probes
  found: (a) description "6-axis IMU with accelerometer and gyroscope" still -> Atomic_Timer (classify alone -> Sensor_Motion): stock vote outranks words. (b) MPN "ICM42688P" -> prefixes ICM42688, ICM4, ICM; first two have no stock match, ICM -> Timer. (c) Stock names ICM-20602/ICM-20948 start with "ICM-"; no Timer name does, so a separator-aware step "ICM-" would vote 2/2 Sensor_Motion.
  implication: Two independent weaknesses: the prefix drops the separator/series digits, and a split vote at the coarsest (letters-only) step outranks explicit description words.

- timestamp: 2026-11-12T18:30:00Z
  checked: importer/migration/gate.py check_plan; widgets/migration_dialog.py _display_part, _status_text, _populate_tree, library combo wiring (line 752)
  found: The gate's only library line is "Choose a library for X" when target_library is empty (gate.py:184-185); there is no rule for a suggestion made from a split/weak vote. The dialog puts the suggested name into the editable Library combo exactly like an owner choice; the reason ("Suggested from 4 similar parts in KiCad's Timer. Other matches: Sensor_Motion (2).") is only the combo tooltip; the tree groups the part under Atomic_Timer with status "N problems - from IC_IMU_TDK"; library_badge says only existing/new. The combo list holds only libraries already targeted in the plan plus the source library, so Atomic_Sensor_Motion (the alternative) is not offered when no other part targets it.
  implication: Nothing visible tells the owner the library was guessed, let alone from a 4-vs-2 split; once the atomic-rule lines are fixed Run enables with Atomic_Timer.

- timestamp: 2026-11-12T18:35:00Z
  checked: Qt offscreen probe (scratchpad/combo_probe.py): editable QComboBox, pick item from popup
  found: Picking from the list emits currentTextChanged + textActivated only, NOT lineEdit().textEdited. migration_dialog.py connects only lineEdit().textEdited -> _on_library_edited. Test test_library_picker_lists_atomic_libraries_and_current only emits textEdited manually.
  implication: Side finding: a library picked from the dropdown list (rather than typed) is not recorded as a choice, so the owner's correction of a mis-suggestion only sticks when typed. Not the cause of G-13-1-f, but it weakens the "owner corrects it in the preview" mitigation.

- timestamp: 2026-11-12T18:36:00Z
  checked: tests locking the behaviour
  found: tests/test_migration_symbols.py:160 asserts targets[key] == "Atomic_Timer" ("the mis-suggestion the owner corrects in the preview"); tests/migrationfixtures.py write_v1_stock deliberately builds a Timer stock with ICM7555/7556/7232/7211 to reproduce it; tests/test_migration_full.py:138-143 pre-sets the IMU choice to Atomic_Sensor_Motion.
  implication: The mis-suggestion is a documented, test-locked design acceptance (13-RESEARCH Open Question 2, 13-CONTEXT Claude's Discretion), not a regression. A fix must update these tests.

## Resolution

root_cause: "siblings.family_prefixes('ICM-42688-P') returns only ['ICM'] (regex ([A-Za-z]+)(\d+)? stops at the hyphen); siblings.pick votes on every KiCad 10 stock symbol starting with ICM - Timer: ICM7209, ICM7555xB, ICM7555xP, ICM7556 (Intersil timers, 4) vs Sensor_Motion: ICM-20602, ICM-20948 (2) - and 4/6 > 50% decides Timer; suggest.suggest_library returns that stock pick before categories.classify runs (and classify would find no category word in 'High Precision 6-Axis MEMS MotionTrackingTM Device' anyway); symbols.target_libraries copies the suggestion as the target; the gate has no rule for split/weak-vote suggestions and the dialog shows the suggested library identically to a chosen one (reason only in a tooltip), so Run enables once the atomic-rule lines are fixed. The behaviour was foreseen and accepted in 13-RESEARCH Open Question 2 / 13-CONTEXT Claude's Discretion and is locked by tests/test_migration_symbols.py:160."
fix: ""
verification: "diagnosis reproduced with scratchpad/repro_imu.py on real KiCad 10 stock symbols + temp Custom/"
files_changed: []
