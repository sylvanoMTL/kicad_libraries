# Phase 4: Plan and Install Core - Context

**Gathered:** 2026-10-19
**Status:** Ready for planning

<domain>
## Phase Boundary

A headless, Qt-free core that turns one Phase 3 `ImportCandidate`, plus explicit caller choices, into an **install plan** and applies it to `Custom/` as a transaction. The same plan object is what the Phase 5 preview will show and edit (PREV-07).

The core does the following:
- Merges the symbol into a new or existing `.kicad_sym`, renaming sub-symbols and `extends` where needed.
- Writes the footprint(s) to the matching `.pretty/`.
- Copies the 3D model to `Custom/3DModels/` and links it as `${CUSTOM_3DMODEL_DIR}/<file>`.
- Creates the library pair when the library is new.
- Normalises the incoming symbol with `kicad-cli` according to the version policy below.
- Rolls back every touched file on any failure.
- Verifies the result and reports the warnings POST-03 (duplicate name) and POST-04 (pin/pad mismatch).
- Makes a second identical import change nothing.

Requirements: INST-01..09, INTK-08, LIB-02, POST-03, POST-04.

Not in this phase: any Qt dialog or preview UI, the picker for choosing among several items (INTK-07), rescan and table regeneration (POST-01/02), the "KiCad is running" notice (POST-05), and git (Phase 6). Phase 4 never writes the real `Custom/`. Every test and UAT run uses a copy.

</domain>

<decisions>
## Implementation Decisions

### Carried forward (locked)
- Services return `Issue(severity, code, text)` lists and do not raise for expected failures. Routing is by `Severity` (Phase 1 D-07, Phase 2).
- Writes are atomic: a temp file, then `os.replace` with about 1 s of retries. A locked or read-only target gives `fs.locked` / `fs.write_failed` (Phase 1 D-05).
- Backups of files inside `Custom/` go to the app-data backup directory (`fsutil.default_backup_dir`), never into the repo (Phase 1 D-06).
- Edits are span splices. Nothing is re-serialised. EOL and BOM are kept, and inserted text uses the file's dominant EOL (Phase 1 D-09..D-11).
- The model is saved as `<MPN>.<original ext>` with the extension's case kept. An existing file with the same SHA-256 is reused silently. Different content is a per-item conflict (STATE.md).
- `kicad-cli` only ever touches the incoming part, never the whole target library. The target library's version header is never changed (STATE.md).
- **Phase 3 contract (D-04):** install is refused while `importer.suggest.placeholder_tokens(target_library_name)` is non-empty.
- Phase 3 review findings carried in (03-REVIEW-DISPOSITION.md). Phase 4 must handle both when it consumes `ImportCandidate`:
  - **WR-04:** the candidate's `PackageFile`s point into staging that dies on `Package.close()`.
  - **WR-05:** package-level warnings never reach the candidate.

### Format version policy (INST-06, LIB-02)
- **D-01: The incoming symbol matches the target library's version.** Compare the incoming symbol's `(version N)` with the target library header:
  - **Equal:** splice the vendor text as-is. `kicad-cli` is not needed.
  - **Incoming older than target:** run `kicad-cli sym upgrade` on a staging copy. Use the upgraded symbol **only if the output version equals the target header**. Otherwise splice the original vendor text unchanged and log a WARNING that names both versions. For example, a `20211014` symbol going into `IC_IMU_TDK` at `20231120` with KiCad 9 installed (`cli` gives `20241209`) is spliced unchanged with a warning. The same as-is path with a warning applies when `kicad-cli` is not found.
  - **Incoming newer than target:** for example, a `20241209` symbol going into `IC_Battery_Charger_TI` at `20211014`. Install is **refused** with an ERROR telling the user to open and save that library in KiCad first. A library must never hold content newer than its header.
  - — **Reversibility:** reversible. The policy is local to the planner's normalisation step.
- **D-02: Footprints are copied as-is and never normalised.** A `.kicad_mod` is a standalone file, and KiCad reads older footprint versions and upgrades them on save. Only the footprint name, its value text/property and the `(model ...)` node are edited. Reason: `kicad-cli fp upgrade` assigns random UUIDs, which would break INST-09 (re-import is a no-op).
  - **This amends INST-06 and ROADMAP Phase 4 success criterion 3**, which say "symbol and footprint are normalised". Normalisation now applies to the symbol only. Update both texts when the phase closes.
- **D-03: `kicad-cli` is a blocking load gate.** When it is available, the would-be library is checked before anything is written:
  - Run `kicad-cli sym upgrade` on a temp copy of the fully merged target `.kicad_sym`.
  - Run `kicad-cli fp upgrade` on a staging `.pretty` that holds only the incoming footprint(s). Never point it at the real `.pretty`, because it rewrites the whole directory.
  - A non-zero exit or "Unable to load" **refuses the install**. The CLI's stderr goes into an ERROR Issue, and nothing is written.
  - When `kicad-cli` is not found, the gate is skipped with an INFO Issue.
  - The gate runs with a timeout, never on the UI thread (Phase 5 runs the core on a worker). `kicad-cli` is located under the detected KiCad install's `bin/`.
- **D-04: New library header.**
  - A brand-new `.kicad_sym` gets the **installed KiCad's format**: the incoming symbol is normalised with `kicad-cli`, and the header is what KiCad 9 writes (`20241209`, `kicad_symbol_editor` generator).
  - Without `kicad-cli`, the new library uses the vendor file's own version, so header and content agree.
  - A new `.pretty/` is created in the same transaction as its first footprint.

### Conflicts and idempotence (PREV-05 data, INST-04, INST-09)
- **D-05: An unresolved conflict blocks install.** The plan lists each conflict per item (symbol in the target lib, footprint file in the target `.pretty`, model file in `3DModels`) with `resolution = None`. Applying the plan is refused while any resolution is unresolved. Resolutions are `overwrite`, `rename` and `skip`. There is never a global default or an "overwrite all". Tests pass choices explicitly, and Phase 5 surfaces them in the preview.
- **D-06: Rename gets a suggested free name.**
  - The plan proposes the first free `<name>_2`, `<name>_3`, … (model: `CSD85301Q2_2.stp`), run through `sanitize_name` / `sanitize_filename`. The caller may override it, and an override is validated (sanitised, no new clash).
  - A renamed footprint flows into the symbol's Footprint field (`<Lib>:<FP>`) and into `ki_fp_filters`.
- **D-07: "Identical" means byte-equal to the planned output.** An identical item is not a conflict and is not written, which is what makes a second import a no-op (INST-09).
  - Symbol: the existing block's text equals the block the plan would write, compared after EOL normalisation.
  - Footprint: the file bytes equal the planned bytes.
  - Model: the SHA-256 matches.
  - A part the user has since edited in KiCad will show as a conflict on re-import. That is accepted.
- **D-08: Overwriting a symbol replaces it in place.** The new block is spliced over the old block's span. Library order is kept, and the git diff shows only that symbol.
- **D-09: Skip means "keep the existing item and use it".**
  - Skipping a footprint still links the symbol to the existing `<Lib>:<FP>`.
  - Skipping a model leaves the existing model file and the existing footprint link in place.
  - The pin/pad check then runs against the footprint that is actually linked.
- **D-10: Case-only clashes on files are conflicts.** Footprint files, model files and library pair names are compared case-insensitively when detecting conflicts, because Windows treats them as the same file. Symbol names inside a `.kicad_sym` are compared exactly. A case-only twin symbol gets a WARNING (it reuses Phase 3 `naming.case_clash`).

### Fields written on install (INST-01..05, PREV-04 data)
- **D-11: Manufacturer and MPN are always filled.**
  - `MPN` comes from a vendor MPN-like field if there is one, else the vendor symbol name. For the UL sample that is `CSD85301Q2`, so the model is `CSD85301Q2.stp`.
  - `Manufacturer` comes from a vendor manufacturer-like field, else the Phase 3 suggestion token (`TI`), else it is left empty with a WARNING.
  - Caller overrides (from the Phase 5 preview) win over these defaults.
  - — **Reversibility:** costly. These property names become the convention for every imported part. Changing them later means a migration (v2 META2-02 territory).
- **D-12: Vendor equivalent fields on the incoming symbol are renamed in place.** This covers `MF`, `MP`, `MANUFACTURER`, `Manufacturer_Name`, `Manufacturer_Part_Number` and similar. The first match for each role is renamed to `Manufacturer` / `MPN`, so there are no duplicates. Existing `Custom/` symbols are never touched (migration stays v2).
- **D-13: The new Manufacturer and MPN properties are hidden,** like Datasheet. They still show in the symbol's properties and in the BOM.
- **D-14: Name-bearing fields follow a rename only on exact matches.** Rename never uses substring replacement.
  - **Symbol rename:** the top-level name, every `<Name>_<u>_<s>` sub-symbol and every `(extends "<Name>")` follow. `Value` and `ki_keywords` tokens change only where they equal the old name exactly.
  - **Footprint:** the file name, the internal footprint name, the value text/property, the symbol's `Footprint` field and `ki_fp_filters` always follow the final footprint name.
- **D-15: `ki_fp_filters` holds the installed footprint names exactly.** It is a space-separated list of the installed footprint name(s) (e.g. `DQK0006B`) and replaces the vendor value.
- **D-16: For `extends`, the parent is imported too.** A derived vendor symbol is installed together with its parent from the same vendor file, as one unit. The parent is placed before the child, and renames are applied consistently across the chain. If the parent is missing from the package, the install is refused with an ERROR.
- **D-17: Items per install.**
  - **Exactly one symbol**, counting its `extends` parent as part of that one unit.
  - **One or more footprints.** The first chosen footprint is linked in the Footprint field, and all chosen footprints go into `ki_fp_filters`.
  - **Zero or one model**, attached to the linked footprint.
  - Choosing among several items is the caller's input here. The picker UI is INTK-07 in Phase 5.
  - With no model, the plan installs without one and carries a "no 3D model found" WARNING (INTK-08). The model is linked by rewriting an existing `(model ...)` path, or by inserting a model block when the vendor footprint has none (INST-05).

### Failure, rollback and verification (INST-07, INST-08, POST-03, POST-04)
- **D-18: A failed verification rolls everything back.** Verification is the last step of the transaction. The hard checks are:
  - every written file re-parses;
  - `<Lib>:<FP>` resolves to a written or existing footprint;
  - the model file exists, with the name matched exactly, case included.

  Any hard failure restores every file the install touched and logs the reason. The soft checks (pin/pad mismatch, name exists elsewhere) are WARNINGs only and never roll back.
- **D-19: Crash safety comes from app-data backups, with no journal.**
  - Before any write, every existing file the install will change is backed up to the app-data backup directory. These backups are pruned to the newest N installs; N is Claude's choice, around 10.
  - A failure during the run rolls back from in-memory pre-images, and files the install created are deleted.
  - After a hard crash, `git status` plus those backups are the recovery path. There is no auto-recovery or startup prompt.
  - Write order follows the research: new files first (model, then footprint), with the existing symbol library last.
- **D-20: The pin/pad check warns in both directions.**
  - It compares the set of symbol pin numbers with the set of footprint pad numbers. Pads with an empty number (NPTH or mechanical) are ignored.
  - One WARNING lists pins that have no pad and pads that have no pin (e.g. an unconnected exposed pad).
  - It never blocks. It runs against the footprint that is actually linked (see D-09).
- **D-21: The duplicate-name check covers every repo source plus KiCad's stock libraries.** POST-03 searches:
  - the other `Custom/` libraries;
  - `WurthElektronik` when it is checked out;
  - KiCad's default symbol libraries when they are detected.

  The WARNING names each library where the part name already exists. Duplicates across libraries are legal in KiCad, so this never blocks.

### Proof
- **D-22: The proof is a pytest test with `kicad-cli`, plus a manual UAT.**
  - Pytest installs the UL sample into a `tmp_path` copy of `Custom/` and asserts success criteria 1–5. That includes failure injection on each write and an import repeated twice.
  - A `kicad-cli` load check runs on the result and is skipped when `kicad-cli` is absent.
  - Manual UAT: the owner opens that scratch library once in KiCad 9 and confirms the symbol, the footprint and the 3D view.
  - Phase 4 never writes the real `Custom/`.

### Claude's Discretion
- Module layout under `kicad_lib_manager/importer/`. Research suggests `plan.py`, `planner.py`, `applier.py`, a `kicad_cli.py` locator/runner, and the write side of `kicad_files.py` (insert/replace symbol, rename symbol and sub-symbols, rename footprint, set/insert model, set/add/rename property).
- The dataclass shapes for the plan, items, conflicts, resolutions and result, and `Issue.code` names (e.g. `install.conflict_unresolved`, `install.version_newer_than_target`, `install.cli_gate_failed`, `install.rolled_back`, `verify.pin_pad_mismatch`, `verify.name_elsewhere`).
- How to resolve WR-04: for example, the plan copies the needed bytes into memory, or the API requires the `Package` to be open for the plan's lifetime and documents this. How to resolve WR-05: package issues are folded into the candidate or the plan's Issue list.
- How Description is written per target version: the `ki_description` property in older formats, `Description` in newer ones. Follow whatever the target library's format uses.
- How the new property blocks are laid out (position, `(at ...)`, effects, `(id N)` only where the target format uses ids), matching neighbouring properties.
- `kicad-cli` timeout value, the backup retention count N, and how KiCad's stock symbol directory is located (as a sibling of the detected footprint dir).
- The empty-library template for a new `.kicad_sym` when no `kicad-cli` is available.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` §Phase 4: the goal, the five success criteria, the Phase 3 D-04 contract, and the research flag (spike KiCad 9/10 on mixed versions and `kicad-cli sym/fp upgrade` behaviour; `extends` handling is now decided by D-16)
- `.planning/REQUIREMENTS.md`: INST-01..09, INTK-08, LIB-02, POST-03, POST-04, plus PREV-01..07 (Phase 5 consumes this phase's plan)
- `.planning/PROJECT.md`: Core Value, the install bullets, constraints (stdlib only, no write without preview, atomic or backed-up writes), and the UL sample facts under Context

### Prior phase decisions
- `.planning/phases/01-foundation/01-CONTEXT.md`: D-05 (atomic write), D-06 (app-data backups for `Custom/` files), D-07 (Issue contract), D-09..D-11 (EOL, BOM, encoding), D-12 (`kicad_files` write side deferred to Phase 4)
- `.planning/phases/02-hardening-existing-code/02-CONTEXT.md`: D-16 (the `kicad_files` model-path splice helper `retarget_model`, reused here), D-19 (exact-case model file existence)
- `.planning/phases/03-package-intake-and-naming/03-CONTEXT.md`: D-04 (placeholder refusal contract), D-12 (symbol-only and no-model packages), D-13 (intake returns all items), D-15 (`sanitize_name`), D-16 (`case_clash`)
- `.planning/phases/03-package-intake-and-naming/03-REVIEW-DISPOSITION.md` and `03-REVIEW.md`: WR-04 and WR-05, which Phase 4 must resolve

### Research
- `.planning/research/ARCHITECTURE.md`: the importer layout, the plan/planner/applier split, the transaction pattern (precondition checks, backups, safe order, undo log), and the open questions (mixed versions, `extends`)
- `.planning/research/PITFALLS.md`: Pitfall 1 (format versions and the `kicad-cli` upgrade path), 3 (sub-symbol and `extends` rename, no substring rewrite), 16 (duplicates), 19 (leave footprint headers alone), 26 (the preview must match the install); the "Looks Done But Isn't" checklist
- `.planning/research/STACK.md`: `kicad-cli sym upgrade` / `fp upgrade` behaviour and locations (it writes the whole `.pretty` in place and assigns random UUIDs)
- `.planning/research/FEATURES.md`: the transactional install with rollback, and the `kicad-cli` normalise/check rows

### Background (untracked, optional)
- `reports/KiCad 10 vendor part import.md`: the competitor survey and KiCad 10 risks, including the `(embedded_files` warning

### Conventions
- `.planning/codebase/CONVENTIONS.md`: naming, Issue lists, `Path` everywhere, the `progress` callback shape
- `.planning/codebase/TESTING.md`: test layout and the run command (`.\env\Scripts\python.exe -m pytest`)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kicad_lib_manager/sexpr.py`: `parse` (with `max_nodes`), `Edit`, `apply_edits`, `quote` / `unquote`. This is the span-splicing core for every write.
- `kicad_lib_manager/kicad_files.py`: `parse_bytes`, `load`, `file_kind`, `file_version`, `find_symbols` / `find_symbol`, `find_property`, `footprint_name`, `find_models`, `retarget_model`. Phase 4 adds the write-side helpers next to these.
- `kicad_lib_manager/fsutil.py`: `atomic_write_bytes` / `atomic_write_text`, `backup_file(path, backup_dir)`, `default_backup_dir`, `decode_source` / `read_source` / `encode_source`, `normalize_eol`.
- `kicad_lib_manager/importer/candidate.py`: `ImportCandidate`, `SymbolItem` (`meta: PartMeta`, `format_version`, `name_check`), `FootprintItem` (`model_paths`, `has_embedded_files`, `format_version`), `ModelItem`, `ExistingLibrary`.
- `kicad_lib_manager/importer/package.py`: `open_package` → `Package` (context manager; staged files die on `close()`), `PackageFile`.
- `kicad_lib_manager/importer/naming.py`: `sanitize_name`, `sanitize_filename`, `case_clash`.
- `kicad_lib_manager/importer/suggest.py`: `suggest_library`, `placeholder_tokens`, `manufacturer_choice`.
- `kicad_lib_manager/importer/layout.py`: `RepoLayout`, `list_symbol_libs`, `list_footprint_libs`, `list_model_files`, `list_existing_libraries`.
- `kicad_lib_manager/library_scanner.py`: KiCad install/footprint-dir detection (the base for locating `kicad-cli` and the stock symbol libraries).
- `kicad_lib_manager/kicad_process.py`: `kicad_running()`, a stdlib `subprocess` pattern to follow for running `kicad-cli`.

### Established Patterns
- Services are Qt-free and return values plus Issue lists. Only `main_window.py` routes them to the log. Phase 4 adds no Qt code.
- The optional `progress(message, current, total)` callback.
- `tests/` and `downloaded_examples/` are in the scanner's `SKIP_DIRS`. Tests build `Custom/` copies in `tmp_path`.
- The layering tests (`tests/test_layering.py`, `tests/test_importer_layering.py`) enforce the import direction. New importer modules must pass them.

### Facts observed during discussion (2026-10-19)
- The installed KiCad is 9.0, with `kicad-cli` at `C:/Program Files/KiCad/9.0/bin/kicad-cli.exe`.
- `Custom/Symbols` headers are mixed:
  - `20211014`: `Connector_FFC_GCT`, `Connector_MicroSD_GCT`, `IC_Battery_Charger_TI`;
  - `20231120`: `IC_IMU_TDK`;
  - `20241209`: the other six.
- All `Custom/` footprints are at `20241229`.
- UL sample symbol `CSD85301Q2`:
  - format `20211014`, CRLF line endings;
  - units `_1_1` and `_2_1`;
  - pin numbers 1–8, which match footprint `DQK0006B` pads 1–8;
  - no `Manufacturer`, `MPN` or description;
  - `Footprint` = `DQK0006B` and `ki_fp_filters` = `DQK0006B`;
  - the footprint has no `(model ...)` block, and the STEP `DLV0006A.stp` sits at the zip root.
- Existing `Custom/` symbols use `MF`, `MP` and `MANUFACTURER`, which are never migrated. No `Custom/` symbol uses `extends`.

### Integration Points
- New modules under `kicad_lib_manager/importer/`, consumed by the Phase 5 dialog through a worker thread. The plan must be cheap to rebuild on every preview edit (PREV-07).
- Phase 5 performs the post-install rescan through `MainWindow._start_scan` (Phase 2 busy guard). Phase 4 only returns the result: touched files, the target library, whether the library is new, and Issues.
- Phase 6 commits exactly the files the install touched, so the result must list them.

</code_context>

<specifics>
## Specific Ideas

- The UL sample's expected outcome:
  - `CSD85301Q2` in the target `.kicad_sym`, with every other symbol and the header byte-identical;
  - `DQK0006B.kicad_mod` with matching file name, internal name, value text, `Footprint` field (`<Lib>:DQK0006B`) and `ki_fp_filters`;
  - the model at `Custom/3DModels/CSD85301Q2.stp`;
  - a model block `${CUSTOM_3DMODEL_DIR}/CSD85301Q2.stp` inserted into the footprint;
  - hidden `Manufacturer` = `TI` and `MPN` = `CSD85301Q2` added.
- Version scenarios to test explicitly:
  - UL (`20211014`) into a `20211014` library: as-is.
  - UL into a `20241209` library: `kicad-cli` upgrade.
  - UL into `IC_IMU_TDK` (`20231120`): as-is with a warning.
  - A `20241209` symbol into a `20211014` library: refused.
  - A new library: KiCad 9 header.
- Hand-built fixtures are needed for an `extends` parent/child pair, a vendor symbol with `MF`/`MP` fields, a footprint that already has a `(model ...)` block, and a pin/pad mismatch (e.g. an extra exposed pad).

</specifics>

<deferred>
## Deferred Ideas

None. The discussion stayed within the phase scope.

</deferred>

---

*Phase: 04-plan-and-install-core*
*Context gathered: 2026-10-19*
