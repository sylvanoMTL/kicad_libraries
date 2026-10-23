---
status: diagnosed
trigger: "there was not 3d model, what if I get a 3d model in a separate file? (in SnapEDA this is what you get, not in a full zip file) ... actually Snap EDA you downlad separately and it is either a cad file or a zip file containing the cad file"
created: 2026-10-23T21:27:54Z
updated: 2026-10-23T22:00:00Z
---

## Current Focus

hypothesis: CONFIRMED - single-source intake (open_package/locate/ImportDialog) with no attach path, plus _open_folder ignoring .zip, plus FMT2-02 deferred to v2
test: headless repro cases A-H (scratchpad repro.py) on the real CAD zip and the real model zip
expecting: done - root cause confirmed, second-source model proven to flow through build_plan/apply_plan unchanged
next_action: hand diagnosis to plan-phase --gaps (G-07-2); no fix applied in this session (find_root_cause_only)
bug_class: bohrbug (deterministic; a design/scope gap, not a regression)
reasoning_checkpoint: null
tdd_checkpoint: null

## Symptoms

expected: The user downloads from SnapEDA the CAD package zip (symbol + footprint, e.g. downloaded_examples/USB4145-03-0170-C_REVA2.zip, no model inside) and SEPARATELY the 3D model, which arrives either as a bare .step/.stp file or as a zip containing it. The importer should let them combine the two in one import; the model is copied to Custom/3DModels/ and linked as ${CUSTOM_3DMODEL_DIR}/<file>.
actual: "there was not 3d model, what if I get a 3d model in a separate file? (in SnapEDA this is what you get, not in a full zip file) ... actually Snap EDA you downlad separately and it is either a cad file or a zip file containing the cad file". Preview shows the "no 3D model found" warning.
errors: None. Preview shows the "no 3D model found" warning (intake.no_model).
reproduction: UAT Test 2 (Phase 07). Orchestrator headless check with the real zip: (a) unzip USB4145-03-0170-C_REVA2.zip into a folder, add a bare .stp, open_package(folder) + detect_candidate -> vendor SnapEDA, model found (WORKS). (b) put the model as a .zip in that folder instead -> ignored, issues 'intake.ignored_members: Not imported from snapeda_folder: how-to-import.htm, USB4145-03-0170-C_3D.zip' and 'intake.no_model'. (c) import_dialog.py _on_browse accepts a single *.zip only, _on_browse_folder a single folder; no way to add a second source.
started: Discovered during UAT of Phase 07 (2026-10-23). Single-source intake has been the design since Phase 03.

## Eliminated

## Evidence

- timestamp: 2026-10-23T21:30:00Z
  checked: knowledge base (.planning/debug/knowledge-base.md)
  found: does not exist (no debug dir before this session); MemPalace not queried
  implication: no known-pattern candidate

- timestamp: 2026-10-23T21:31:00Z
  checked: package.py open_package / _open_zip / _stage_zip / _open_folder / _classify
  found: open_package(path) takes ONE path (zip or folder). _classify returns "nested" for .zip; _stage_zip opens one nested level (D-08). _open_folder line 566-567 puts every non-stage file, including a .zip, in package.ignored with the comment "a nested .zip (never opened here)".
  implication: a model .zip placed beside loose files is dropped by design; folder intake never opens zips

- timestamp: 2026-10-23T21:33:00Z
  checked: adapters/base.py locate + _legacy_rules; detect.py detect_candidate; candidate.py
  found: ImportCandidate.models comes only from package.files of kind "model" in the single Package. _legacy_rules emits intake.no_model INFO when models is empty and ERROR intake.nothing_found when there is no symbol and no footprint.
  implication: a model-only source opened on its own is refused (nothing_found); there is no merge step for a second Package

- timestamp: 2026-10-23T21:35:00Z
  checked: planner.py _select / build_plan model block (L594-606, L884-952); plan.py FileOp; applier.py _preflight L292-304
  found: the model op is FileOp("model", models_dir/name, source=model_item.file). The applier re-reads op.source.path and checks op.source.sha256. Nothing ties a PackageFile to the Package that produced the candidate beyond "the staged file must still exist at apply time" (WR-04).
  implication: the plan/applier contract already accepts a ModelItem from any PackageFile; a second source only needs its PackageFile kept alive (its own Package open, or an unstaged in-place file) until apply_plan returns

- timestamp: 2026-10-23T21:37:00Z
  checked: widgets/import_dialog.py _on_browse (L969), _on_browse_folder (L976), open_path (L988-1022), _on_opened (L1054), _populate_items model row (L1350-1364), _form_values (L1226-1234), _discard_package (L2343)
  found: Browse zip filter "Zip packages (*.zip)", single file; Browse folder single dir; open_path discards the current package before opening the new one; dialog holds exactly one self._package. Model row with no models is a static label "No 3D model in this package" with no action.
  implication: the GUI has no way to add a second source to an open import

- timestamp: 2026-10-23T21:39:00Z
  checked: downloaded_examples/194150990-659-usb4145-03-0170-c.zip (real SnapEDA 3D model download, added 22:20)
  found: two members: usb4145-03-0170-c.stp (2443718 B, deflate, starts ISO-10303-21; STEP AP242) and usb4145-03-0170-c.txt (900 B, mount metadata). No symbol, footprint or how-to-import marker. CAD zip USB4145-03-0170-C_REVA2.zip has .kicad_sym, .kicad_mod, how-to-import.htm, no model.
  implication: real fixture exists for the model-zip case; the model zip is flat (one level), lowercase filename differs from the CAD part name

- timestamp: 2026-10-23T21:45:00Z
  checked: scope docs: PROJECT.md L78 (Out of Scope), REQUIREMENTS.md L101 FMT2-02 (v2), research/FEATURES.md L141, 03-04-PLAN A5, 07-CONTEXT L42
  found: "Attaching a separately downloaded STEP file when the package has none" is explicitly Out of Scope for v1 (FMT2-02, v2). FEATURES.md names the workaround "loose-files mode with the STEP in the same folder". 07-CONTEXT locks "SnapEDA is the no-model case". 03-04 A5: a STEP-only package is ERROR intake.nothing_found by design.
  implication: no code was ever planned for a second source; the only documented workaround assumes a bare STEP, but SnapEDA really ships the model as a zip

- timestamp: 2026-10-23T21:50:00Z
  checked: headless repro script (scratchpad/scripts/repro.py) on the real CAD zip + real model zip, cases A-H
  found: A CAD zip alone -> SnapEDA, models=[], intake.no_model. B model zip alone -> Package not refused (stp staged, txt ignored) but detect gives ERROR intake.nothing_found. C folder CAD+model.zip -> zip ignored, no_model. D folder CAD + unzipped model (.stp+.txt) -> model found. E folder with both zips -> both ignored, nothing_found. F folder CAD + bare .stp -> model found. G CAD Package + model PackageFile from a SECOND open_package(model zip), candidate = replace(models=(ModelItem,)) -> build_plan unblocked, model_file USB4145-03-0170-C.stp, footprint gets (model "${CUSTOM_3DMODEL_DIR}/USB4145-03-0170-C.stp"), apply_plan ok, file in 3DModels. H baseline without it -> intake.no_model + install.no_model.
  implication: confirmed root cause (single-source intake + folder intake ignores zips + no dialog entry); confirmed fix feasibility without changing InstallPlan/FileOp/applier, provided the model Package stays open until apply_plan returns

- timestamp: 2026-10-23T21:55:00Z
  checked: open_package(bare .stp); main_window.dropEvent L707-734; commit_plan.py L121-150; preview.py _chosen_model L87-92
  found: bare .stp -> ERROR intake.unsupported "not a .zip file or a folder". Main-window drop refuses more than one URL ("drop one .zip file or one folder at a time"). commit_plan takes the model's expected hash from op.source.sha256 and preview reads candidate.models: neither is tied to the producing Package.
  implication: a bare model file needs its own intake branch; commit and preview work unchanged once the dialog's candidate carries the attached model

- timestamp: 2026-10-23T21:57:00Z
  checked: import_dialog.py _populate_items -> _clear_items -> _clear_form (L1261) and _reload_symbol_defaults (L1695)
  found: both clear self._edited; _reset_fp_name resets the footprint Name field
  implication: re-running _populate_items after an attach would wipe the user's field edits; a fix should rebuild only the 3D model row, then _request_rebuild

## Resolution

root_cause: |
  Design/scope gap, not a regression. The import pipeline is single-source end to end, and the one documented workaround does not cover SnapEDA's real model delivery. Contributing causes (AND-gate fired):
  (1) code/intake: open_package(path) takes exactly one zip or folder; detect_candidate/locate build ImportCandidate.models only from that Package's files; no API attaches models from a second source. A model-only zip opened alone is refused at locate (intake.nothing_found, A5); a bare .stp is refused by open_package (intake.unsupported).
  (2) code/intake: _open_folder classifies any .zip as ignored ("a nested .zip (never opened here)", package.py:566-567), so the workaround from research FEATURES.md:141 (STEP beside the loose KiCad files) fails when the model comes as a zip, which is how SnapEDA ships it (real file: 194150990-659-usb4145-03-0170-c.zip = .stp + .txt).
  (3) code/GUI: ImportDialog holds one self._package; Browse zip (single *.zip) and Browse folder (single dir) replace it via open_path -> _discard_package; the model row is a static "No 3D model in this package" label with no action; main-window drop accepts one URL only.
  (4) requirements: PROJECT.md:78 lists "attaching a separately downloaded STEP" as Out of Scope, REQUIREMENTS.md:101 defers it as FMT2-02 (v2), and 07-CONTEXT:42 locks "SnapEDA is the no-model case", so no phase ever planned it.
fix: (not applied: goal find_root_cause_only)
verification: |
  Feasibility probe (case G): CAD zip Package plus the model PackageFile from a second open_package(model zip), candidate = dataclasses.replace(models=(ModelItem,)), then build_plan (unblocked, model_file USB4145-03-0170-C.stp, footprint (model "${CUSTOM_3DMODEL_DIR}/USB4145-03-0170-C.stp")) and apply_plan (ok, file copied to 3DModels). InstallPlan, FileOp, applier and commit_plan need no change.
oracle_type:
files_changed: []
