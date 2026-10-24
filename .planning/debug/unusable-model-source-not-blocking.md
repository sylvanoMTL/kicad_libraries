---
status: diagnosed
trigger: "UAT gap G-07-5 (Phase 07, test 5): an unusable 3D model source shows an amber warning 'dummy_CAD_FILE.step holds no usable 3D model'; user wants a red ERROR that blocks Install, with remove / add-another actions on the model row. Install was observed greyed out."
created: 2026-10-24T11:00:00Z
updated: 2026-10-24T11:50:00Z
goal: find_root_cause_only
---

## Current Focus

bug_class: Bohrbug (deterministic; a design/spec gap against plan 07-08, not a regression)
hypothesis: CONFIRMED H1 - the refusal is rendered amber because _on_model_attached hard-codes tone="amber" (and _set_model_note has no error tone), and the refusal is never stored on the dialog, so it cannot feed blocking_reasons; the greyed Install seen in test 5 was the pre-existing plan state (unresolved symbol conflict) caused by the part already installed in live Custom/ during test 3, not by the refusal and not WR-01.
test: done - headless plan probe + temporary dialog probe (both observed directly)
expecting: n/a
next_action: return ROOT CAUSE FOUND to the orchestrator (goal find_root_cause_only; no fix applied)

reasoning_checkpoint:
  hypothesis: "An unusable model source shows an amber, non-blocking note because (1) _on_model_attached passes tone='amber' for ERROR issues and _set_model_note only knows AMBER/MUTED, and (2) a refused source is closed and forgotten - it never reaches the candidate, the planner, FormStatus or blocking_reasons - so Install keeps whatever state the existing plan gives it."
  confirming_evidence:
    - "import_dialog.py:1673-1675 and :1433 - ERROR issue text routed to tone 'amber' -> AMBER #8A5200; probe note stylesheet 'color: #8A5200;'"
    - "form.py FormStatus/blocking_reasons have no model input; probe snapshot (install, strip, reasons, _gen, candidate id) identical before/after the refusal in both an enabled and a disabled starting state"
    - "Live Custom copy + real SnapEDA zip + bare .stp: Install off with reason 'Choose Overwrite, Rename or Skip for symbol USB4145-03-0170-C_REVA2' before and after the dummy refusal"
  falsification_test: "If any probe snapshot changed after the refusal (Install toggled, new reason, _gen bumped) or the note used ERROR, H1 would be wrong. Neither happened."
  fix_rationale: "Not applied (find_root_cause_only). A fix must add dialog state for the rejected source and route it into blocking_reasons, plus an error tone - changing only the colour would leave Install unblocked."
  blind_spots: "The exact conflict choices the user had made in the test-5 session are not observable; if they had chosen Skip the strip would have shown the no-op line instead. Either way the refusal is not the cause. Partial zips (one good + one bad model) attach the good model and only log a WARNING - whether that should also block is a product decision."
  candidate_causes:
    - "code: hard-coded tone='amber' in _on_model_attached/_on_model_failed; no rejected-source state; FormStatus lacks a model field"
    - "config/spec: plan 07-08 must-have (07-08-PLAN.md:27) explicitly specified 'refused source leaves candidate and row unchanged ... amber note' - the code implements the spec"
    - "data/environment: live Custom/ already held the part from test 3, so the plan had an unresolved symbol conflict that disabled Install independently"
  and_gate: "yes for the observed symptom set: the amber, non-blocking note comes from code+spec; the greyed Install comes from data (pre-installed part). Two independent causes produce the combined UAT observation."

## Symptoms

expected: (UAT test 5 as scripted) "Add 3D model..." with a zip holding only a .txt, then a text file renamed to .stp: each shows an amber plain-text note under the model row (and a log line) and nothing else changes. User's requested truth: an unusable 3D model source is reported as an ERROR (red) that blocks Install, and the model row offers both removing the bad 3D package and adding a different one.
actual: "The warning is 'dummy_CAD_FILE.step holds no usable 3D model' This should be an error, the user should not be able to progress but have an option to remove the 3D package, or add a new package (e.g. if the zip was conteninng an unusable 3D CAD file)". Follow-up: "This is an error not a warning, so red color is needed. I note install part is grayed out"
errors: none (no exception; behaviour/design complaint)
reproduction: UAT test 5 in .planning/phases/07-snapeda-and-samacsys-adapters/07-UAT.md. Before test 5 the same SnapEDA part with model was installed into live Custom/ in test 3.
started: discovered during UAT re-test on 2026-10-24 after gap-closure plans 07-07/07-08/07-09

## Eliminated

- hypothesis: The greyed-out Install after the refusal was caused by the refusal itself (the refusal already blocks).
  evidence: _on_model_attached leaves _candidate, _gen and _plan untouched and FormStatus/blocking_reasons have no model input; the dialog probe shows identical Install/strip/reasons/_gen before and after attaching dummy_CAD_FILE.step, both with Install enabled (UL) and disabled (SnapEDA vs live Custom copy).
  timestamp: 2026-10-24T11:35:00Z

- hypothesis: WR-01 (Install stuck on "Updating preview..." after a stale model result) explains the greyed Install.
  evidence: WR-01 needs the session to change (Change... + new open) while the model worker runs. In test 5 the read of a 0-byte file is instant and no package change happened; the non-stale refusal branch calls _end_model_worker then _update_install_state() (import_dialog.py:1655, 1680), so _updating() is False afterwards. Probe strip after refusal shows the conflict reason, not UPDATING_REASON.
  timestamp: 2026-10-24T11:35:00Z

- hypothesis: The Install was off because the part is a pure no-op ("Nothing to install: this part is already in Connector_USB_GCT.").
  evidence: Partly eliminated. Against the live Custom state the plan is not a no-op: build_plan yields ops [] with an unresolved symbol conflict (USB4145-03-0170-C_REVA2), so the strip shows "Choose Overwrite, Rename or Skip for symbol ...". No-op would only show if the user had chosen Skip for that conflict in the test-5 session; either way it is pre-existing plan state from the test-3 install, not the refusal.
  timestamp: 2026-10-24T11:25:00Z

## Evidence

- timestamp: 2026-10-24T11:05:00Z
  checked: Phase 0 knowledge base (.planning/debug/knowledge-base.md)
  found: No knowledge base file exists; only prior session snapeda-separate-3d-model.md (G-07-2 design gap, which produced the current Add 3D model flow). No MemPalace query available.
  implication: No known-pattern candidate; proceed with code reading.

- timestamp: 2026-10-24T11:08:00Z
  checked: kicad_lib_manager/importer/package.py open_model_source (310-358) and _open_model_file (361-394)
  found: A bare .step/.stp/.wrl is accepted by intake with NO magic check (only lstat/link/size/fstat identity/SHA-256). A .zip with no model member is refused at intake with ERROR intake.no_model_in_source "<zip> holds no 3D model (.step, .stp or .wrl)" (package.refused).
  implication: A text file renamed .step gets through open_model_source; the content check happens later in attach_models.

- timestamp: 2026-10-24T11:10:00Z
  checked: kicad_lib_manager/importer/adapters/base.py _check_model (150-165) and attach_models (358-426)
  found: _check_model returns WARNING intake.content_mismatch "<member> does not look like a STEP file". attach_models with no new usable model returns (None, [*problems(WARNING), *already, Issue(ERROR, "intake.no_model_in_source", f"{source} holds no usable 3D model")]). For a refused package it returns (None, package.issues) (ERROR). The exact UAT text "dummy_CAD_FILE.step holds no usable 3D model" is base.py:409 with source = model_package.source.name.
  implication: The issue the user saw IS severity ERROR in the model layer. The amber colour is not from the Issue severity.

- timestamp: 2026-10-24T11:12:00Z
  checked: kicad_lib_manager/widgets/import_dialog.py _on_model_attached (1651-1687), _set_model_note (1424-1435), _on_model_failed (1689-1696)
  found: When outcome.candidate is None: package closed, errors = ERROR issues, `self._set_model_note(errors[0].text, tone="amber")` (1675); _set_model_note maps tone "amber" -> AMBER, anything else -> MUTED (1433). No ERROR tone exists. _on_model_failed also uses tone="amber" (1695). The candidate, row, _gen and _plan are untouched; the only follow-up is _update_install_state() (1680). Nothing of the refusal is stored on the dialog except the note text.
  implication: Colour is hard-coded amber at the call site regardless of Issue.severity (ERROR constant is imported from theme but unused for the note). The refusal leaves no state that could block Install.

- timestamp: 2026-10-24T11:15:00Z
  checked: kicad_lib_manager/importer/form.py FormStatus (89-100), blocking_reasons (133-199); import_dialog.py _form_status (2147-2161), _update_install_state (2171-2199), _updating (2112-2119)
  found: FormStatus has no model field at all (updating, build_failed, library, value_text, mpn_text, several_footprints, footprints_checked, resolutions). blocking_reasons gets ERRORs only from plan.issues (build_plan output) plus form fields and conflicts. The model worker only contributes via _updating() (model_worker not None -> UPDATING_REASON) while reading. Install enabled = candidate and current plan and not reasons and not plan.blocked and not plan.is_noop.
  implication: By design a refused model source cannot block Install: its issues never reach the planner (candidate unchanged) or FormStatus. After the refusal, Install returns to exactly the state the existing plan dictates.

- timestamp: 2026-10-24T11:20:00Z
  checked: user's live checkout C:/Git_Repo_Clones/Kicad_Libraries-importer (read-only ls/grep): Custom/ files and downloaded_examples/ timestamps (BST = UTC+1)
  found: Custom/Footprints/Connector_USB_GCT.pretty/GCT_USB4145-03-0170-C_REVA2.kicad_mod and Custom/3DModels/USB4145-03-0170-C.stp written 2026-10-24 10:48:07 (the test-3 install into live Custom; footprint links ${CUSTOM_3DMODEL_DIR}/USB4145-03-0170-C.stp). Custom/Symbols/Connector_USB_GCT.kicad_sym last written 2026-10-23 22:17 (not rewritten at 10:48, so the symbol was skipped/unchanged in that install). downloaded_examples/194150990-659-usb4145-03-0170-c/dummy_CAD_FILE.step is a 0-byte file created 10:51:43; UAT file updated 10:57 local.
  implication: Test 5 ran against a Custom/ that already held this part; the test file is an empty .step (passes intake, fails _check_model).

- timestamp: 2026-10-24T11:25:00Z
  checked: headless probe (scratchpad probe_g075/probe_plan.py): worktree code, real USB4145-03-0170-C_REVA2.zip, scratch copy of the live Connector_USB_GCT files; ToolContext() and detect_tools(KiCad fp dir)
  found: attach of the dummy -> (None, [WARNING intake.content_mismatch "dummy_CAD_FILE.step does not look like a STEP file", ERROR intake.no_model_in_source "dummy_CAD_FILE.step holds no usable 3D model"]) - exact UAT text. Plans (both tool sets): CAD zip only -> ops [], unresolved conflicts symbol USB4145-03-0170-C_REVA2 + footprint GCT_USB4145-03-0170-C_REVA2, blocked True. CAD zip + bare .stp attached (test 4 state) -> ops [], unresolved conflict symbol USB4145-03-0170-C_REVA2, blocked True, is_noop False. Same with a typed Value.
  implication: In the user's test-5 dialog, Install was already off before the dummy was picked: the strip read "Install is blocked: Choose Overwrite, Rename or Skip for symbol USB4145-03-0170-C_REVA2" (or, had the user chosen Skip, the no-op line "Nothing to install: this part is already in Connector_USB_GCT."; with Overwrite it would be enabled). Supports H1.

- timestamp: 2026-10-24T11:35:00Z
  checked: temporary dialog probe tests/test_zz_probe_g075.py (deleted after the run), run with the importer venv pytest
  found: (1) UL dialog, Install enabled, strip "Ready to install: 2 new, 1 modified, 0 unchanged files"; attach 0-byte dummy_CAD_FILE.step -> snapshot (install, strip, _gen, candidate id, models, strip reasons) IDENTICAL before/after; note "dummy_CAD_FILE.step holds no usable 3D model" styled "color: #8A5200;" (AMBER), not ERROR #CC0000. (2) Real SnapEDA zip against a copy of the live Connector_USB_GCT files: CAD only -> Install off, reasons [symbol conflict, footprint conflict]; after attaching the real bare .stp -> Install off, reasons [Choose Overwrite, Rename or Skip for symbol USB4145-03-0170-C_REVA2], _gen 3; after attaching dummy -> identical snapshot, amber note. 2 passed.
  implication: H1 confirmed by direct observation: the refusal neither blocks nor unblocks Install; the greyed Install in UAT test 5 is the unresolved symbol conflict from the test-3 install into live Custom/ (resolutions reset when the CAD zip was reopened in test 4).

- timestamp: 2026-10-24T11:40:00Z
  checked: baseline run of tests/test_import_dialog.py, test_model_attach.py, test_model_source.py, test_import_form.py, test_help_dialog.py (-k "add_model or attach or model_source or blocking or help")
  found: 63 passed, 1 skipped (symlink privilege). Tests that encode the current non-blocking amber design: test_import_dialog.py::test_add_model_refusal_shows_note (3786: AMBER style, candidate is same object, row "No 3D model in this package", _model_packages == []), ::test_add_model_worker_failure_logged (4067: AMBER note AND `assert dialog._install_btn.isEnabled()` at 4083), ::test_add_model_note_is_plain_text (3830: refusal note visible, plain text - keeps passing if the note stays PlainText), ::test_add_model_duplicate_is_noted (3851: MUTED note, _gen unchanged - INFO duplicate, should stay non-blocking). Pure-layer tests test_model_attach.py::test_attach_rejects_wrong_magic / ::test_attach_refused_package and test_model_source.py:114 assert (None, ERROR intake.no_model_in_source) - still valid if the fix is dialog/form-side only. test_import_form.py builds FormStatus through a `status(**changes)` helper (line ~367), so a new defaulted FormStatus field costs one helper default.
  implication: Current behaviour exactly matches plan 07-08's must-have (07-08-PLAN.md:27, :111-115, :125); this is a spec change, not a regression. Those tests must be rewritten together with the change.

- timestamp: 2026-10-24T11:45:00Z
  checked: removal paths for model sources in import_dialog.py (_make_model_widget 1379-1393, _discard_package 2556-2563, 07-08-PLAN.md:61 design note)
  found: The only "remove" today is the combo's final "No model" entry, which exists only when the candidate has more than one model (one model -> plain label, no decline). Attached packages are append-only (self._model_packages) and released only by Change..., a new open or close (_discard_package). A refused source is closed immediately and leaves no entry at all. Add 3D model... (ADD_MODEL_TEXT) stays enabled after a refusal (_sync_add_model_button / _model_busy).
  implication: There is no existing "remove this model source" control or state to reuse for the rejected entry; "add another" is already available (the Add 3D model... button). Removing a successfully attached single model would need new detach logic (rebuild the candidate from the base candidate + remaining packages) and WR-04-safe package release.

## Resolution

root_cause: |
  Design/spec gap, not a regression. Plan 07-08 specified (must-have, 07-08-PLAN.md:27) that a refused model source leaves the candidate and row unchanged and shows its reason as an amber plain-text note, and the code does exactly that:
  (1) Colour: attach_models returns ERROR intake.no_model_in_source ("<source> holds no usable 3D model", base.py:409; zip refusal package.py:347), but ImportDialog._on_model_attached picks tone="amber" for it (import_dialog.py:1673-1675; also _on_model_failed :1695), and _set_model_note only knows AMBER or MUTED (:1433). Issue.severity is never used for the note colour; theme.ERROR (#CC0000) is imported but unused there.
  (2) Not blocking: a refused source is closed at once and nothing is stored (no rejected-source state). Its issues never reach the candidate or build_plan, and FormStatus / blocking_reasons (form.py:89-199) have no model input, so _update_install_state (:2171-2199) computes the same result as before the attach. Only while the worker runs does _updating() block Install as "Updating preview...".
  (3) The greyed Install in the user's session was pre-existing plan state: the part was installed into live Custom/ during test 3 (footprint and model at 10:48:07). Reopening the SnapEDA zip reset the conflict choices, so the plan has an unresolved symbol conflict and the strip reads "Install is blocked: Choose Overwrite, Rename or Skip for symbol USB4145-03-0170-C_REVA2". This was observed in a probe against a copy of the live files. It is not the refusal and not WR-01. It would read "Nothing to install: ..." only if Skip had been chosen.
  (4) No remove action exists: the only decline is the combo's "No model" entry, and that appears only with more than one model. Attached packages are append-only. "Add another" is already there as the Add 3D model... button, which stays enabled.
fix: (not applied - goal find_root_cause_only)
verification: Diagnosis verified by headless probe (scratchpad probe_g075/probe_plan.py) and a temporary dialog probe test (deleted); baseline related tests 63 passed / 1 skipped.
files_changed: []
