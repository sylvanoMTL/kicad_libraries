---
status: resolved
trigger: "UAT gap G-10-1 (Phase 10, test 1): a 6-pin vendor footprint (SON50P150X150X60-6N, SON65P200X200X80-6N) gets SON-8 from two score-30 tied KiCad matches; owner chose to fix WR-06 with a pad-count filter"
created: 2026-10-29T00:00:00Z
updated: 2026-11-13T14:45:00Z
goal: find_root_cause_only
---

## Current Focus

bug_class: Bohrbug (deterministic; the same inputs give SON-8 every time, and no threads are involved in the path)
hypothesis: CONFIRMED. _agreed_family_texts (planner.py:91-107) accepts a score-30 tie with no size check because it never gets the vendor pad count. Filtering the score-30 tied entries to those within one distinct pad number of the vendor footprint, before the agreement loop, removes SON-8 for the 6-pad parts and keeps WSON-6 for DQK0006B and SON-8/SOIC-8 for 8-pad parts.
test: done (simulated filter via a scratch pytest plugin, no repo edits)
expecting: done
next_action: Return ROOT CAUSE FOUND to the orchestrator for gap-closure planning (goal find_root_cause_only, so no fix is applied here)
reasoning_checkpoint:
  hypothesis: "_agreed_family_texts (planner.py:91-107) borrows the family of a score-30 (leading-letters-only) tie because it gets no vendor pad count and never compares sizes. For SON50P150X150X60-6N and SON65P200X200X80-6N, the only score-30 footprints in KiCad 10 are two SON-8 footprints (8 and 9 pads) that agree, so SON-8 passes."
  confirming_evidence:
    - "repro_tie.py on the KiCad 10 install: both codes tie at 30 on exactly MicroCrystal_C7_SON-8 (8 pads) and SON-8-1EP (9 pads), and _agreed_family_texts returns texts giving SON-8"
    - "e2e_son.py through build_plan: SON-8 lands in fp_description, fp_tags and keywords for a 6-pad vendor footprint"
    - "Simulated +/-1 distinct-pad filter on score<50 ties: both 6-pad cases give part_text == no-KiCad plan; the DQK0006B/Texas_DQK (8/8) and 8-pad SON controls keep their family; the full suite has only the 2 predicted fixture failures"
  falsification_test: "If SON-8 still appeared for a 6-pad vendor footprint with the filter in place, the family would come from another path (vendor descr/tags or a different tie). It did not: with the filter, the plan equals the no-KiCad plan."
  fix_rationale: "The defect is the missing size check at the only place a borrowed family enters (_agreed_family_texts, whose texts go to footprint_facts). Filtering the score-30 tie by distinct pad count there removes the wrong family from all three outputs at once. It leaves the vendor's own descr/tags and full-code matches untouched."
  blind_spots: "A symmetric +/-1 still lets a 7-pad or 10-pad part borrow SON-8 here (documented; the owner decides). On the live install only the SON, SOIC, WSON and DQK cases were probed; other score-30 ties that still agree after filtering were not listed."
  candidate_causes:
    - "code: _agreed_family_texts has no vendor pad count parameter and no pad comparison for score-30 ties (planner.py:91-107, call at 1091). Confirmed root cause."
    - "config: _MIN_FAMILY_SCORE = 30 equals _SCORE_LEADING_LETTERS (planner.py:84, footprint_index.py:28), so a leading-letters-only match is enough. Contributing; the owner kept it and declined the alternative of 50."
    - "data: KiCad 10 Package_SON has only two footprints whose name contains the whole word SON, both SON-8, so the tie is tiny and unanimous. This is the trigger, not a defect."
  and_gate: "yes. The wrong family needs (1) vendor descr/tags that name no family AND (2) a score-30 tie that agrees AND (3) no size check. Only (3) is a defect, and removing it alone removes the symptom (simulation)."

## Symptoms

expected: For a vendor footprint with 6 pads (e.g. SON50P150X150X60-6N, SON65P200X200X80-6N), the importer does not borrow a package family ("SON-8") from KiCad footprints whose pad count differs by more than one.
actual: A 6-pin vendor footprint (SON50P150X150X60-6N, SON65P200X200X80-6N) gets SON-8 from two score-30 tied KiCad matches. That family is written into the footprint description, the tags and the symbol keywords.
errors: None reported
reproduction: Test 1 in .planning/phases/10-importer-on-the-atomic-scheme/10-UAT.md; review finding WR-06 in 10-REVIEW.md and 10-REVIEW-DISPOSITION.md
started: Discovered during UAT (residual of CR-01 after fix 1276906)

## Eliminated

- hypothesis: The SON-8 text comes from the vendor footprint's own descr or tags.
  evidence: The plan for the same package built without a KiCad footprints folder has no SON-8 ('1.5 mm pitch, TI SON50P150X150X60-6N'); with the folder it has 'SON-8, ...'. The family is borrowed.
  timestamp: 2026-10-29T00:35:00Z

- hypothesis: The vendor pad count is already available where _agreed_family_texts is called (the review says "footprint_facts counts it"; there is also a vendor_pads variable).
  evidence: vendor_pads (planner.py:928-936) is set only inside `if is_official:`, and the vendor branch leaves it None. FootprintFacts.pads is len(pad_centres), which counts pad nodes rather than distinct numbers (12 against 9 on Texas_DSG0008A_..._ThermalVias). The count must be computed as len(footprint_pad_numbers(fp_refs[0].node)).
  timestamp: 2026-10-29T00:45:00Z

- hypothesis: Comparing the vendor pad count with the pin number written in the family text (SON-8 gives 8) would be an equivalent, cheaper filter.
  evidence: The UAT-passed CSD tracer would break. Vendor DQK0006B has 8 distinct pads (six leads plus two thermal pads), and its family WSON-6 says 6, so it would be dropped. Comparing with the official footprint's own pad count (Texas_DQK, 8) keeps it.
  timestamp: 2026-10-29T00:31:00Z

## Evidence

- timestamp: 2026-10-29T00:10:00Z
  checked: Knowledge base (.planning/debug/knowledge-base.md) and resolved sessions
  found: No knowledge-base.md exists. resolved/ holds 4 unrelated sessions (preview columns, reason-link tooltip, SnapEDA 3D model, model source). MemPalace was not used. No known-pattern candidate.
  implication: Investigate from scratch.

- timestamp: 2026-10-29T00:15:00Z
  checked: kicad_lib_manager/importer/planner.py:82-107 (_MIN_FAMILY_SCORE, _agreed_family_texts) and its only call site, planner.py:1086-1099
  found: _agreed_family_texts(footprint_index, code) ranks with limit=None and returns [] when the top score is under 30. It then walks every entry at the top score and returns the first one's texts when all of them name the same family. It takes no vendor pad count and never reads pads. Nothing separates a score-30 (leading letters only) tie from a score-50/80 (full code) tie. It is called once, at planner.py:1091, and only in the vendor-footprint branch (not is_official).
  implication: A small leading-letters-only tie whose members agree supplies its family regardless of the vendor part's size. This is the WR-06 gap.

- timestamp: 2026-10-29T00:18:00Z
  checked: Everything downstream of facts.family (grep for describe(, generated_tags(, package_words, .family across kicad_lib_manager/)
  found: official_texts flow only into footprint_facts(..., texts=official_texts) (planner.py:1092), where package_family([vendor descr, vendor tags, *texts]) sets facts.family (footprint_text.py:202). facts.family then feeds describe(facts) for the fp description (planner.py:1095), generated_tags(facts) for the family tag and the IPC-style name (planner.py:1096, footprint_text.py:230-250), and package_words, which go to generate_keywords for the symbol keywords (planner.py:1099, 1107). No other module works out the family.
  implication: _agreed_family_texts is the single choke point, and a filter there fixes all three outputs plus the IPC-style name. The vendor's own descr/tags are still read first, so the filter cannot drop a family the vendor names itself.

- timestamp: 2026-10-29T00:22:00Z
  checked: Where pad counts come from: footprint_index.py:173-202 (_read_facts, pad_numbers), verify.py:191-205 (footprint_pad_numbers), footprint_text.py:74-92 and 192-205 (pad_centres, footprint_facts)
  found: footprint_texts(), which _agreed_family_texts already calls, goes through _read_facts. That parses the official file once and caches _Facts(pads=frozenset(footprint_pad_numbers(...)), descr, tags). pad_numbers(index, link) reads the same cache entry, so the official pad count needs no extra file read. On the vendor side, footprint_pad_numbers(fp_refs[0].node) gives the distinct pad numbers and ignores empty numbers and np_thru_hole. FootprintFacts.pads is len(pad_centres(...)), which counts pad nodes, not distinct numbers.
  implication: The official pad count is len(pad_numbers(index, link) or ()) and costs nothing. The vendor pad count is len(footprint_pad_numbers(fp_refs[0].node)). Do NOT use facts.pads. Parsing the "-8" out of the official name would be unreliable: Texas_DQK has no count in its name, and the -1EP names add a pad.

- timestamp: 2026-10-29T00:25:00Z
  checked: Scratch script g101/vendor_pads.py on KiCad 10 Package_SON.pretty/Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm_ThermalVias.kicad_mod
  found: pad nodes=14, pad_centres=12, distinct numbers=9.
  implication: Confirms that pad_centres (and so FootprintFacts.pads) counts every thermal-via pad that shares the EP number. Distinct numbers are the right unit on both sides.

- timestamp: 2026-10-29T00:28:00Z
  checked: Scratch script g101/repro_tie.py against C:/Program Files/KiCad/10.0/share/kicad/footprints (rank, pad_numbers and package_family for each tied entry)
  found: SON50P150X150X60-6N and SON65P200X200X80-6N each tie at score 30 on exactly two footprints: Package_SON:MicroCrystal_C7_SON-8_1.5x3.2mm_P0.9mm (8 pads, SON-8) and Package_SON:SON-8-1EP_3x2mm_P0.5mm_EP1.4x1.6mm (9 pads, SON-8). _agreed_family_texts returns texts that give SON-8. Controls: SOIC127P600X175-8N ties 48 (mixed families) and gives None; WSON6 ties 43 and gives None; DQK0006B has one score-30 match, Package_SON:Texas_DQK (8 distinct pads, WSON-6), and gives WSON-6.
  implication: WR-06 is reproduced on the real install. A +/-1 pad filter drops both SON-8 footprints for a 6-pad vendor part (|8-6|=2, |9-6|=3).

- timestamp: 2026-10-29T00:31:00Z
  checked: Pad counts of the vendor footprints in downloaded_examples (zips read in memory) against their official match
  found: ul_CSD85301Q2 DQK0006B has 8 distinct numbers (1-8: six leads and two thermal pads). KiCad Texas_DQK has 8 distinct numbers. The stock fixture Texas_DQK (tests/stockfixtures.py:82-89) has 8 pads.
  implication: The UAT-passed CSD tracer (checks 3 and 10, with WSON-6 in the description, tags and keywords) keeps WSON-6 under a +/-1 official-pad filter (|8-8|=0).

- timestamp: 2026-10-29T00:35:00Z
  checked: Scratch script g101/e2e_son.py, which runs build_plan end to end with the tests/ fixtures (write_synthetic_custom atomic, write_stock_kicad with the two SON-8 footprints at 8 and 9 pads, vendor_footprint(code, pads=1..6)), with APPDATA and QSettings sandboxed in the scratchpad
  found: SON50P150X150X60-6N (6 pads) gives fp_description 'SON-8, 1.5 mm pitch, TI SON50P150X150X60-6N', fp_tags 'SON-8 SON50P150X150X60-6N P1.5mm' and keywords 'Battery Management SON-8 SON50P150X150X60-6N TI Texas', which differ from the no-KiCad plan. SON65P200X200X80-6N behaves the same. A control with an 8-pad vendor footprint also gets SON-8, which is correct and must stay.
  implication: The symptom reproduces in exactly the shape the new test should take. That test is RED today.

- timestamp: 2026-10-29T00:38:00Z
  checked: Existing tests: tests/test_generated_text.py:320-468 (the CR-01 family block) and the vendor fixture tests/installfixtures.py:368-408 used by _vendor_zip (test_generated_text.py:248-262)
  found: _vendor_zip calls vendor_footprint(footprint) with the default pads=("1","2"), so the vendor footprint in every family test has 2 pads. Baseline: 16 passed (-k "family or tie or ambiguous or csd or lower_case"). The tests that expect a family from a score-30 match are test_a_single_leading_letters_match_supplies_its_family (SOIC-8, 8 pads) and test_a_tie_that_agrees_supplies_the_family[leading letters] (SOIC-8 with 8 pads plus SOIC-8-1EP with 9). The full-code cases (SOT-23-5, score 80) are outside the filter. No test mentions WR-06, or a pad count in a family context.
  implication: With a 2-pad vendor footprint, those two tests will fail once the filter lands. _vendor_zip needs a pads parameter, and those tests need an 8-pad vendor footprint. Three no-family tests (ambiguous, socket, lower-case) would then pass vacuously through the pad filter instead of through their own branch.

- timestamp: 2026-10-29T00:50:00Z
  checked: Falsification run of the fix direction without editing the repo. The scratch plugin g101/g101_filter_plugin.py patches planner._agreed_family_texts and footprint_facts so that, before the agreement loop, ties scoring under 50 keep only footprints with |distinct official pads - distinct vendor pads| <= 1 (unreadable official pads are excluded). Run with e2e_son.py --filter.
  found: Filter OFF: both 6-pad codes (SON50P150X150X60-6N, SON65P200X200X80-6N) give 'SON-8, ...'. Filter ON: both give '1.5 mm pitch, TI <code>', and part_text equals the no-KiCad plan, so SON-8 is gone from the description, tags and keywords. Controls with the filter ON: an 8-pad vendor against the two SON-8 footprints keeps SON-8, and DQK0006B (8 pads) against Texas_DQK (8 pads) keeps WSON-6.
  implication: Hypothesis confirmed. The missing size check is the cause, and a +/-1 distinct-pad filter on score-30 ties removes the symptom without touching the passing CSD case.

- timestamp: 2026-10-29T01:00:00Z
  checked: Boundary neighbours of the +/-1 filter (e2e_son.py --filter) against the two SON-8 footprints (8 and 9 distinct pads)
  found: vendor 5 pads gives no family; 6 gives no family; 7 gives SON-8 (via the 8-pad MicroCrystal, |1|); 8 gives SON-8; 10 gives SON-8 (via the 9-pad SON-8-1EP, |1|).
  implication: The owner's +/-1 rule fixes the reported 6-pad cases. It still lets a 7-pad part (6 leads + EP, IPC -7N) or a 10-pad part borrow SON-8, because a symmetric tolerance cannot tell which side holds the exposed pad. A tighter variant exists: allow official - vendor in {0,+1} when the official footprint has an EP, and {0,-1} when it has none. That changes the owner's rule, so it needs the owner's decision. Whichever rule is chosen, the boundary tests should pin it.

- timestamp: 2026-10-29T00:55:00Z
  checked: tests/test_generated_text.py (30 tests) under the simulated filter (run_with_filter.py)
  found: 28 passed, 2 failed: test_a_single_leading_letters_match_supplies_its_family (line 387) and test_a_tie_that_agrees_supplies_the_family[leading letters] (line 416). Both use the 2-pad default vendor footprint against 8- and 9-pad SOIC footprints. The CSD tracer tests, the full-code SOT-23-5 cases and the live-KiCad tests pass.
  implication: The fix must give _vendor_zip a pads parameter and pass 8 pads in those two expected-family tests, otherwise they go red for a fixture reason.

- timestamp: 2026-10-29T01:20:00Z
  checked: The full test suite (tests/) under the simulated filter with run_with_filter.py; output in scratchpad g101/full_with_filter.txt
  found: 2 failed, 2891 passed, 34 skipped in 703 s. The only failures are test_generated_text.py::test_a_single_leading_letters_match_supplies_its_family and ::test_a_tie_that_agrees_supplies_the_family[leading letters].
  implication: Apart from those two fixture-driven cases, no module or test depends on the borrowed family. The dialog, install, official-footprint, UAT and live-KiCad tests all pass.

## Resolution

root_cause: "_agreed_family_texts(footprint_index, code) in kicad_lib_manager/importer/planner.py:91-107 has no vendor pad count and no size check. When the top rank score is 30 (_SCORE_LEADING_LETTERS, footprint_index.py:28, accepted because _MIN_FAMILY_SCORE = 30 at planner.py:84), the only link to the vendor part is that the code's leading letters are a word of the footprint name. So a small tie whose members all name one family supplies that family whatever the vendor part's size. Its only caller, build_plan at planner.py:1089-1092, passes the result as texts= to footprint_facts. From there the family reaches describe() (fp description, planner.py:1095), generated_tags() (family tag and IPC-style name, planner.py:1096) and package_words, then generate_keywords (symbol keywords, planner.py:1099/1107). Against KiCad 10, SON50P150X150X60-6N and SON65P200X200X80-6N tie at 30 on exactly MicroCrystal_C7_SON-8_1.5x3.2mm_P0.9mm (8 pads) and SON-8-1EP_3x2mm_P0.5mm_EP1.4x1.6mm (9 pads), and both name SON-8."
fix: "Plan 10-29 (G-10-1, WR-06): a leading-letters-only footprint tie supplies a package family only from official KiCad footprints within one distinct pad of the vendor footprint, so 6-pin SON parts no longer get SON-8."
verification: "Phase 10 UAT re-test passed 2026-10-29 (16 checks)."
files_changed: []
oracle_type: "derived (D-28 contract: when no family can be safely borrowed, the plan with KiCad's footprints must equal the plan without them) plus specified (no word starting SON- in the description, tags or keywords)"

Resolved at the v2.0 milestone close (2026-11-13) against the plan that fixed it.
