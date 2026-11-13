---
status: resolved
trigger: "G-10-11: With the library field empty, the strip lists every reason Install is blocked at once: the library name, Enter the Manufacturer, The Datasheet must be a link or a file path, Type a Description and the 3D model reason. Actual: ATXK-H14 with no library shows only 'Pick or type a library name'; the other reasons appear only after a library is typed."
created: 2026-10-29T00:00:00Z
updated: 2026-11-13T14:45:00Z
goal: find_root_cause_only
---

## Current Focus

hypothesis: CONFIRMED - build_plan (planner.py:870-872) returns refuse(install.invalid_library) before the incoming atomic gate (planner.py:1476-1495) runs, so plan.issues carries only that ERROR; blocking_reasons (form.py:277-278, 303-304) drops it as explained and adds the form's own library reason, leaving one reason
bug_class: Bohrbug (deterministic control-flow ordering; reproduced every run outside the GUI)
test: done (probe_g1011.py reproduces; probe_deferred.py falsification test passed; g1011_emulate plugin lists the affected tests)
expecting: n/a
next_action: return ROOT CAUSE FOUND to the orchestrator for gap-closure planning (goal find_root_cause_only; no fix applied)

reasoning_checkpoint:
  hypothesis: "The strip shows only the library reason because build_plan stops at the name check (planner.py:871-872) and returns a blocked plan whose only ERROR is install.invalid_library; the atomic gate that produces install.atomic.manufacturer/datasheet/description/model_3d runs only at planner.py:1476-1495, which an empty or refused name never reaches. blocking_reasons then hides that one ERROR as explained by its own verdict and lists the verdict reason."
  confirming_evidence:
    - "probe_g1011.py on the real ATXK-H14 zip: library '' and 'Atomic_TI' -> ERRORs == [install.invalid_library]; 'Atomic_Oscillator' -> the four install.atomic.* ERRORs and four strip reasons"
    - "probe_deferred.py: with only the planner's name check forced ok, library '' gives the four atomic ERRORs and the strip lists five reasons (manufacturer, datasheet, description, model, library), so the gate does not need a resolved library"
  falsification_test: "If the dialog skipped build_plan for an empty name, or the gate needed a resolved target library, the deferred probe would show no atomic ERRORs for library ''. It showed all four."
  fix_rationale: "Deferring the refusal until after the library-independent checks (and returning a blocked, op-less plan that carries invalid_library plus the gate's Issues) addresses the control flow that hides the reasons, not the strip rendering."
  blind_spots: "Strip height is capped at 3 lines (import_dialog.py:711); five reasons were not measured on screen. Real KiCad tools (kicad-cli normalisation, real footprint index) were not used in the probes; ToolContext() was. Reason ORDER: the form puts the library reason last today; the UAT text lists it first."
  candidate_causes:
    - "code: planner early return at planner.py:871-872 (CONFIRMED)"
    - "code (UI layer): dialog never builds a plan for an empty name (ELIMINATED by reading _request_rebuild / build_options)"
    - "data: ATXK-H14 has no fields that fail with an empty library (ELIMINATED: Atomic_Oscillator shows all four)"
    - "config: allowed_stems snapshot refusing the name (n/a: '' is refused by the blank check first, stems.py:154-155)"
  and_gate: "yes, partly. The single-reason symptom needs (a) the planner refusing early AND (b) blocking_reasons dropping install.invalid_library as explained. (b) is intended behaviour (no duplicate library line), so the only defect is (a). The reason ORDER is a separate form-side choice (form.py:287-304)."

## Symptoms

expected: Opening downloaded_examples/ul_ATXK-H14-D-32-768KHZ-E50-T3.zip, where no library is suggested so the field stays empty, shows all blocking reasons together in the strip above Install (library name, Enter the Manufacturer, The Datasheet must be a link or a file path, Type a Description, 3D model reason).
actual: ATXK-H14 with no library shows only 'Pick or type a library name'; the other reasons appear only after a library is typed.
errors: None reported
reproduction: UAT test 11 (.planning/phases/10-importer-on-the-atomic-scheme/10-UAT.md), Check 8
started: Discovered during Phase 10 UAT

## Eliminated

- hypothesis: H2 - the dialog never builds a plan while the library field is empty, so the strip has no plan Issues to show
  evidence: import_dialog.py _request_rebuild (2455-2470) has no library guard; build_options (form.py:400) passes library=values.library.strip() (""); probe_g1011 shows build_plan is reached and returns a plan with install.invalid_library
  timestamp: 2026-10-29T00:10:00Z

- hypothesis: H3 - the atomic checks need a resolved target library (target path, existing-library read), so they cannot run for an empty name
  evidence: probe_deferred.py (planner's name check forced ok in-process) gives install.atomic.manufacturer/datasheet/description/model_3d for library ""; atomic_check._check_ref reads only the rendered symbol's fields plus ctx (footprints dir, planned footprint/model); rel_path is used only for FixSpecs and fixable=False
  timestamp: 2026-10-29T00:20:00Z

## Evidence

- timestamp: 2026-10-29T00:00:00Z
  checked: .planning/debug/knowledge-base.md
  found: file does not exist; no knowledge-base match possible
  implication: no known-pattern candidate

- timestamp: 2026-10-29T00:05:00Z
  checked: kicad_lib_manager/importer/planner.py build_plan (839-1580)
  found: line 870 verdict = stems.name_verdict(library, ...); line 871-872 `if not verdict.ok: return refuse(_err("install.invalid_library", verdict.reason))`. refuse() (860-861) returns _refused() with only [*issues (package/candidate), *problems]. The atomic gate (incoming_context + incoming_issues) runs only at 1476-1495, after symbol parse, kicad-cli normalisation, rendering, conflict decisions.
  implication: an empty or refused library name returns before any field check; the prior lead's location is correct

- timestamp: 2026-10-29T00:06:00Z
  checked: kicad_lib_manager/importer/form.py blocking_reasons (258-319)
  found: explained() drops install.invalid_library whenever the form's own verdict is not ok (277-278); the form then appends Reason(verdict.reason, "library") (303-304) AFTER all plan ERROR reasons (290-300). No dedupe except explained(); reasons are a list in order (plan ERRORs -> model_error -> library -> MPN blank -> conflicts -> blank renames).
  implication: with a refused plan the strip shows only "Pick or type a library name"; once the planner emits atomic errors for an empty library, they would lead the strip and the library reason would come after them

- timestamp: 2026-10-29T00:07:00Z
  checked: kicad_lib_manager/widgets/import_dialog.py _request_rebuild (2455-2470), _snapshot_options (1466), form.build_options (375-413)
  found: the dialog always calls build_plan, with library=self._library_combo.currentText().strip() (so "" for an empty field); there is no dialog-side guard that skips the build for an empty name
  implication: alternative H2 (dialog never builds a plan for an empty library) is ruled out by reading; the single reason comes from the planner refusal

- timestamp: 2026-10-29T00:08:00Z
  checked: kicad_lib_manager/importer/incoming.py and atomic_check._check_ref (537-576)
  found: incoming_issues(root, names, rel_path, ctx) runs check_symbol per name; rules mpn/manufacturer/value/datasheet/description read only the rendered symbol's properties; footprint+model_3d use ctx.resolve_footprint(Footprint field) and ctx.model_problems(target), ctx built by incoming_context from layout.footprints_dir, kicad_fp_dir, planned_footprints {link: (path, bytes)} and planned_models. rel_path is used only to build FixSpecs (fixable=False here, so effectively unused).
  implication: no atomic rule depends on the target library; only sym_path (rel_path) and the keyword generation (generate_keywords(library=...)) name it

- timestamp: 2026-10-29T00:12:00Z
  checked: scratchpad g1011/probe_g1011.py - real ATXK-H14 zip (main checkout downloaded_examples, read-only), synthetic atomic Custom/ in a temp dir, ToolContext(), FormStatus(mpn_text="x")
  found: |
    candidate: symbol ATXK-H14-D-32.768KHZ-E50-T3, footprint ATXK-H14_ABR, no models; candidate issues INFO only
    library=""            -> blocked, 0 ops, ERRORs [install.invalid_library 'Pick or type a library name']; strip reason:0 library 'Pick or type a library name'
    library="Atomic_TI"   -> same shape: only install.invalid_library
    library="Atomic_Oscillator" -> ERRORs install.atomic.manufacturer 'no manufacturer', install.atomic.datasheet 'Datasheet is not a link or file path', install.atomic.description 'no description', install.atomic.model_3d 'the footprint has no 3D model'; strip reasons 0 manufacturer, 1 datasheet, 2 description, 3 model
  implication: H1 CONFIRMED by direct observation. The symptom is reproduced exactly outside the GUI; it affects every refused name, not only the empty one

- timestamp: 2026-10-29T00:20:00Z
  checked: scratchpad g1011/probe_deferred.py - the same ATXK-H14 run with planner's stems.name_verdict patched to ok in-process (form keeps the real one); library "" and "Atomic_TI"
  found: |
    both -> ERRORs install.atomic.manufacturer, .datasheet, .description, .model_3d; strip reason:0 manufacturer, 1 datasheet, 2 description, 3 model, 4 library (verdict reason)
    side effects of letting the refused name flow through unchanged: plan.ops == ['footprint', 'symbol_lib'] (symbol_lib at Custom/Symbols/.kicad_sym); keywords for "Atomic_TI" gain "TI" (generate_keywords(library=...) -> _stem_words)
  implication: the gate is library-independent (H3 eliminated). A fix must keep ops=() for a refused name and must not feed the refused name into keywords or paths. With today's form order the library reason comes LAST, while the UAT lists it first

- timestamp: 2026-10-29T00:22:00Z
  checked: PureWindowsPath(symbols_dir / f"{name}.kicad_sym").relative_to(repo_root) for refused names
  found: '' -> Custom/Symbols/.kicad_sym; '/x' -> ValueError; 'D:x' -> ValueError; '../../../x' -> escapes lexically without raising
  implication: planner.py:945 (sym_path) and :1494 (rel_path=sym_path.relative_to(...)) would RAISE for some refused names if the refusal were simply removed; build_plan is documented never to raise for expected failures, and the dialog would show "Preview could not be built". A refused name must not build sym_path; the gate's rel_path needs a fixed placeholder (it only feeds FixSpecs, fixable=False)

- timestamp: 2026-10-29T00:25:00Z
  checked: library-dependent vs library-independent steps of build_plan after line 872
  found: |
    DEPENDS on the library: case-twin check 874-881; Custom/Symbols folder check 907-917 (text names the library); sym_path 945; sym_exists/target read+parse 947-961 (a refused v1 name that exists on disk, e.g. IC_Battery_Charger_TI, WOULD be read); _existing_source vs _new_source 1008-1011; target_version 1019; related-stem filter 1100; keywords via generate_keywords(library=) 1102-1112; linking_parts skip 1284; existing_syms / symbol conflicts keyed symbol:{library}:{name} / bad_rename / case_clash / symbol_kept 1364-1440; sym_edits/sym_bytes 1442-1459; gate rel_path 1494; symbol_lib FileOp 1525-1527; InstallPlan.library/new_symbol_lib 1554-1555
    INDEPENDENT: empty MPN 891; official checks 896-905; Custom/Footprints folder check 910; _select 918-920; vendor parse 922-940; vendor symbol/unit 963-972; name sanitising 974-1004; manufacturer inference 1037-1063; footprint facts/description/tags 1065-1099; render_symbols field edits 1116-1161 (only keyword_source names the library); model naming 1163-1172; model + Atomic_Footprints conflict decisions 1175-1356; the atomic gate 1476-1495 (given target=None so every state is "new" and `written` is non-empty); official pad checks 1497-1515
  implication: the fix can run everything with "target absent" (target=None, sym_exists False, no symbol conflicts, keyword library "") when the name is refused, then return a blocked op-less plan with invalid_library + the gate's Issues

- timestamp: 2026-10-29T00:30:00Z
  checked: import_dialog.py _render_strip (2668-2693) and _on_reason_link (2695-2710); _framed (849-860)
  found: hrefs are reason:{i} from enumerate(reasons) and self._strip_reasons = reasons is the same list, so the index mapping holds for any count; targets manufacturer/datasheet/description/model/library are registered by _framed when the form is built, independent of the plan; the strip max height is 3 lines (711), the tooltip lists every reason
  implication: no change is needed in the link mapping; a 5-reason strip might be clipped on a narrow dialog (blind spot, check in UAT re-run)

- timestamp: 2026-10-29T00:35:00Z
  checked: tests - baseline tests/test_atomic_targets.py tests/test_install_plan.py tests/test_import_form.py (186 passed), then the same with scratch pytest plugin g1011_emulate (refused plan keeps ops=() and gains the install.atomic.* Issues of a new-library pass)
  found: |
    10 failed, 176 passed. Failing (all use the ul_package fixture, CSD85301Q2, which has no Description, so they gain install.atomic.description):
      tests/test_atomic_targets.py:30-37 _assert_refused (asserts ERROR codes == ["install.invalid_library"]) via
        test_a_bare_kicad_name_is_refused_with_its_reason (40), test_an_existing_v1_library_is_refused_like_any_other_name x5 (61),
        test_a_case_variant_is_refused_naming_the_official_spelling (69), test_an_empty_name_is_refused (77)
      tests/test_atomic_targets.py:101 test_the_form_does_not_list_the_plan_error_a_second_time (targets == ["library"] -> ["description", "library"])
      tests/test_install_plan.py:113 test_refused_library_blocked_and_nothing_written (_codes == ["install.invalid_library"])
    Not failing: test_install_plan.py test_name_check_runs_before_the_target_is_read (124), test_library_invalid_name x4 (811), test_library_case_variant... (822) - their vendors pass the atomic rule (ATOMIC_PROPS / DESCRIBED + model)
    Same plugin over tests/test_import_dialog.py tests/test_gate_reasons.py tests/test_atomic_dialog.py: 220 passed
  implication: exactly these 10 tests encode "a refused name has one ERROR" and must be updated; no dialog test breaks. No test pins the library reason AFTER plan ERRORs together, so moving it first would break only test_atomic_targets.py:101 (already listed)

- timestamp: 2026-10-29T00:38:00Z
  checked: scratchpad g1011/probe_siblings.py - other early refusals before the gate on ATXK-H14 with library Atomic_Oscillator
  found: mpn="" -> no early refusal (the four atomic ERRORs show); footprint_target="official" with no footprint picked -> ERRORs == [install.official_missing] only (planner.py:900-901)
  implication: same bug class (early refuse hides independent reasons) also exists for official_missing (and the other refuse() calls between 872 and 1495); outside G-10-11's truth, noted for the planner

## Resolution

root_cause: "build_plan (kicad_lib_manager/importer/planner.py:870-872) returns refuse(_err('install.invalid_library', verdict.reason)) as its first check, before the incoming atomic gate (incoming_context + incoming_issues, planner.py:1476-1495) that produces install.atomic.manufacturer/datasheet/description/model_3d. refuse() (860-861 -> _refused 809-836) returns a blocked plan whose only ERROR is install.invalid_library. blocking_reasons (kicad_lib_manager/importer/form.py:258-319) then treats that ERROR as explained by its own verdict (277-278) and adds Reason(verdict.reason, 'library') (303-304), so the strip shows exactly one reason. This affects every refused name (empty, Atomic_TI, v1 names), not only the empty one."
fix: "Plan 10-30 (G-10-11): build_plan no longer stops at a refused library name; it plans as for a new library it never reads and returns every library-independent reason, with the library reason listed first."
verification: "Phase 10 UAT re-test passed 2026-10-29 (16 checks)."
files_changed: []

Resolved at the v2.0 milestone close (2026-11-13) against the plan that fixed it.
