# Phase 4: Plan and Install Core - Research

**Researched:** 2026-10-19
**Domain:** Headless (Qt-free) KiCad library install transaction in Python stdlib: S-expression span edits, `kicad-cli` normalisation and load gate, multi-file rollback, post-install verification.
**Confidence:** HIGH (the research-flag spikes were run against the installed KiCad 9.0.9 `kicad-cli` on this machine; repo APIs were read from source; the only unverified area is KiCad 10 behaviour, which is not installed here)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Carried forward (locked)**
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

**Format version policy (INST-06, LIB-02)**
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

**Conflicts and idempotence (PREV-05 data, INST-04, INST-09)**
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

**Fields written on install (INST-01..05, PREV-04 data)**
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

**Failure, rollback and verification (INST-07, INST-08, POST-03, POST-04)**
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

**Proof**
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

### Deferred Ideas (OUT OF SCOPE)
None. The discussion stayed within the phase scope. (Phase-boundary exclusions from CONTEXT.md: any Qt dialog or preview UI, the picker for choosing among several items (INTK-07), rescan and table regeneration (POST-01/02), the "KiCad is running" notice (POST-05), and git (Phase 6). Phase 4 never writes the real `Custom/`.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INST-01 | Symbol added to the target `.kicad_sym` without touching any other symbol or the header | Insert-after-last-symbol splice rule; byte-identical assertion pattern; prototype verified loadable by `kicad-cli` (Spike S2, S9) |
| INST-02 | Rename also renames `<Name>_<u>_<s>` sub-symbols and `extends`, never by substring | Rename algorithm (Pattern 3); KiCad 9 rejects stale sub-symbols and stale `extends` (Spike S8) |
| INST-03 | Footprint written to `.pretty`; filename, internal name, value text, Footprint field and `ki_fp_filters` agree | Footprint pipeline (Pattern 4); `fp_text value` atom vs `property "Value"` forms; prototype round-tripped through `fp upgrade` (Spike S10) |
| INST-04 | Model copied as `<MPN>.<ext>`; same SHA-256 reused, different is a conflict | Model conflict rules incl. case-twin behaviour on NTFS (Spike S7); WR-04 re-hash-at-apply |
| INST-05 | Footprint links `${CUSTOM_3DMODEL_DIR}/<file>`; rewrite or insert block | `retarget_model` reuse + insert-model template accepted by KiCad (Spike S10) |
| INST-06 | Symbol normalised with `kicad-cli` when available (amended by D-02: symbol only) | Version decision table; CLI behaviours (exit codes, no-output-when-current, `-o` must not exist) (Spikes S1, S3, S5) |
| INST-07 | Any write failure restores every touched file | Transaction pattern: pre-images, backups, reverse undo; fault-injection seam (`fsutil.atomic_write_bytes`) |
| INST-08 | Post-install verification: re-parse, resolve `<Lib>:<FP>`, model exists | Verifier design; exact-case listing, not `exists()` |
| INST-09 | Same package twice changes nothing | "Planned bytes equal existing bytes" no-op rule; sym upgrade is deterministic, fp upgrade is not (Spikes S1, S4) |
| INTK-08 | Package with no 3D model installs with a warning | `install.no_model` WARNING; no model block inserted; stale vendor model paths reported, not rewritten |
| LIB-02 | Choose existing or create new library; new library makes the pair | New-library template and transaction (mkdir + file creates, rollback removes created dirs) |
| POST-03 | Warn when part name exists in another library | Bytes-prefilter name index; full parse of stock libs costs 66 s, prefilter 0.2 s (Spike S11) |
| POST-04 | Warn on pin number vs pad number mismatch | Pin/pad set extraction incl. `extends` chain and empty-number pads |
</phase_requirements>

## Summary

Phase 4 is a pure-Python, Qt-free "plan then apply" core on top of the span-splicing layer built in Phases 1-3. `build_plan` reads the target library fresh from disk, decides the version policy, renders the final bytes of every file (symbol library, footprint, model copy, new directories) and lists conflicts. `apply_plan` is dumb: it checks that the target files still match the plan's base hashes, backs up, writes in a safe order via `fsutil.atomic_write_bytes`, verifies, and on any failure undoes everything from in-memory pre-images. No external packages are needed; everything is stdlib plus the in-repo `sexpr`, `kicad_files`, `fsutil` and importer modules.

The research flag was spiked against the real KiCad 9.0.9 `kicad-cli`. Key results: a `20211014` symbol spliced as-is into a `20231120` or `20241209` library loads in KiCad 9 and re-saves to exactly the same symbol text as the proper upgrade (so the D-01 "as-is with a warning" path is safe on 9.x); `sym upgrade` is deterministic (needed for INST-09) while `fp upgrade` is not (confirms D-02); the CLI refuses a stale sub-symbol name, a stale `extends` and a child placed before its parent with `Unable to load library` (exit 2), which makes the D-03 gate a real safety net and confirms D-16's ordering. Several CLI behaviours are surprising and the runner must handle them: the `-o` path must not already exist (exit 4), a file already at the current version produces no output file and exits 0, the symbol input must end in `.kicad_sym`, and an empty `.pretty` fails.

One performance trap changes the POST-03 design: fully parsing KiCad's stock symbol libraries takes 66 s (22,597 symbols, 227 files), whereas a bytes-substring prefilter takes 0.2 s. POST-03 must use the prefilter and confirm hits only. KiCad 10 uses symbol format `20251024` (verified from KiCad's `10.0` branch header), so on a machine with KiCad 10 and `Custom/` libraries still at `20241209`, D-01 will splice vendor symbols as-is with a warning, never normalise them. That is by design but should not surprise the planner.

**Primary recommendation:** Build `plan.py` (frozen dataclasses carrying rendered bytes plus base hashes), `planner.py` (pure, cheap to rebuild; the `kicad-cli` symbol normalisation memoised by vendor-block hash), `kicad_cli.py` (locator plus an injectable runner), `applier.py` (backup, precondition, ordered writes via `fsutil`, verify, reverse undo) and the write-side helpers in `kicad_files.py`. Register every new importer module in `tests/test_importer_layering.py` `ALLOWED` and register a `kicad_cli` pytest marker in `pyproject.toml` first, because `--strict-markers` is on.

## Architectural Responsibility Map

The usual browser/server tiers do not apply; this phase is a single-process desktop core. Tiers below are this project's layers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Rendering the final text of symbol library, footprint, model block | Importer core (`planner.py`, `kicad_files.py`) | `sexpr.py` | Pure functions, no I/O beyond reading current target state; must be rebuildable on every preview edit (PREV-07) |
| Version policy and symbol normalisation | Importer core (`planner.py`) | `kicad_cli.py` (external process) | Decision is local to the planner (D-01); the CLI is only an oracle |
| `kicad-cli` locate/run/gate | `kicad_cli.py` (subprocess wrapper) | Settings (KiCad dir passed in by caller) | Isolates the only non-pure, slow (about 0.8 s per call) operation; injectable for tests |
| Conflict detection and rename suggestion | Importer core (`planner.py`) | `layout.py`, `naming.py` | Reads live disk listings, case-insensitive for files |
| Atomic writes, backups, rollback | Importer core (`applier.py`) | `fsutil.py` | Applier owns the transaction; `fsutil` owns single-file atomicity |
| Verification and soft warnings (POST-03/04) | Importer core (`verify.py` or in `applier.py`) | `kicad_files.py` | Re-reads what was written from disk |
| Long-running execution off the UI thread | GUI (Phase 5 worker) | — | Core is synchronous and Qt-free; threading belongs to Phase 5 |
| Table regeneration, rescan, git | GUI / Phase 5, Phase 6 | — | Out of scope; the result only reports touched files and `new_library` |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`subprocess`, `hashlib`, `shutil`, `os`, `re`, `dataclasses`, `tempfile`, `pathlib`) | CPython 3.14.4 in `env/` [VERIFIED: `./env/Scripts/python.exe --version` -> `Python 3.14.4`] | All new code | Project constraint: stdlib only unless clearly justified |
| In-repo `kicad_lib_manager.sexpr` | in repo | Tokenize with spans; `Edit`, `apply_edits`, `quote`, `unquote` | Span-splice core required by D-09..D-11 |
| In-repo `kicad_lib_manager.kicad_files` | in repo | `find_symbols`, `find_property`, `footprint_name`, `find_models`, `retarget_model`, `file_version`; Phase 4 adds the write side | Existing semantic layer |
| In-repo `kicad_lib_manager.fsutil` | in repo | `atomic_write_bytes`, `backup_file`, `default_backup_dir`, `normalize_eol`, `read_source` | Single atomic-write implementation |
| `kicad-cli` (external, optional) | 9.0.9 at `C:/Program Files/KiCad/9.0/bin/kicad-cli.exe` [VERIFIED: `kicad-cli version` -> `9.0.9`] | `sym upgrade` normalisation and load gates | Decided in D-01/D-03 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 [VERIFIED: `./env/Scripts/python.exe -m pytest --version`] | Headless tests | All proof (D-22) |
| `tests/zipfixtures.py` builders | in repo | `symbol_lib`, `footprint`, `unpack_sample`, `make_zip`, `write_custom_layout` | Synthetic fixtures; extend rather than duplicate |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-repo span splicing | `kiutils` / `sexpdata` | Rejected in Init (lossy round trip); stays rejected |
| Write journal for crash safety | Journal file | Rejected by D-19 (app-data backups plus git instead) |
| Running `kicad-cli fp upgrade` on the install path | Normalise footprints | Rejected by D-02 (random UUIDs, spike S4 confirms non-determinism) |

**Installation:** none. No new runtime or dev dependency. [VERIFIED: `requirements-dev.txt` already pins `pytest==9.1.1` and `pytest-qt==4.5.0`]

## Package Legitimacy Audit

No external packages are installed by this phase (stdlib plus in-repo modules plus the already-pinned pytest). The legitimacy gate has nothing to evaluate.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 Phase 5 / tests                         (worker thread in Phase 5; plain call in tests)
      |
      |  ImportCandidate (+ Package kept OPEN)   InstallOptions (frozen, caller-edited)
      v
 +-------------------- build_plan(candidate, options, layout, env) --------------------+
 |  1. refuse early: placeholder_tokens(lib) != [], no symbol, library name invalid     |
 |  2. read candidate symbol/footprint bytes from PackageFile.path -> in-memory text    |
 |     (kicad_files.parse_bytes; fold package/candidate Issues in = WR-05)              |
 |  3. read TARGET fresh from disk: Symbols/<Lib>.kicad_sym, Footprints/<Lib>.pretty/,  |
 |     3DModels listing (exact-case set + casefold set)                                 |
 |  4. version policy (D-01) ---------------------------------------------+            |
 |        equal -> vendor text            older + CLI + out==target -> CLI|upgraded    |
 |        older + (no CLI | out!=target) -> vendor text + WARNING         |  (memoised  |
 |        newer -> ERROR install.version_newer_than_target                 |   by hash)  |
 |  5. edit symbol block(s): rename, Footprint, ki_fp_filters, Manufacturer/MPN, ...    |
 |  6. edit footprint: name, value text, model path/insert                              |
 |  7. splice symbol block(s) into target text (insert after last symbol / replace span)|
 |  8. conflicts per item (symbol / footprint / model), planned-bytes == existing bytes |
 |     -> identical = no op; else Conflict(resolution=None) + suggested free name       |
 |  9. CLI load gate on merged lib temp copy + staging .pretty (D-03)  [applier-time    |
 |     or planner-time: see Open Question 1]                                            |
 +--------------------------> InstallPlan (rendered bytes, base sha256s, Issues) -------+
                                      |
                                      |  all conflicts resolved? no ERROR Issue? else refuse (D-05)
                                      v
 +------------------------- apply_plan(plan, backup_dir) ------------------------------+
 |  a. preconditions: base sha256 of every existing target unchanged                    |
 |     (else install.stale_plan); source model file present, re-hash == PackageFile.sha |
 |     (WR-04); all targets resolve inside Custom/                                      |
 |  b. backup every existing file to be changed -> default_backup_dir()/installs/<ts>/  |
 |  c. write order: mkdir new .pretty/ -> model -> footprint(s) -> symbol .kicad_sym    |
 |     each via fsutil.atomic_write_bytes; record (path, pre-image|None) after success  |
 |  d. verify from disk (hard: re-parse, <Lib>:<FP> resolves, model exact-case exists)  |
 |  e. soft checks: pin/pad (POST-04), name elsewhere (POST-03)  -> WARNING only        |
 |  on ANY failure in b-d: undo in reverse (restore pre-images, unlink created files,   |
 |  rmdir created dirs), Issue install.rolled_back                                      |
 +--------------> InstallResult(ok, touched files, target lib, new_library, Issues) -----+
```

### Recommended Project Structure
```
kicad_lib_manager/
├── kicad_files.py        # + write side: symbol/property/footprint/model edit helpers, pin & pad readers
└── importer/
    ├── plan.py           # frozen dataclasses: InstallOptions, InstallPlan, FileOp, Conflict, Resolution, InstallResult
    ├── planner.py        # build_plan (pure apart from reading disk and the memoised CLI call)
    ├── kicad_cli.py      # locate_kicad_cli, KicadCli (runner seam), normalise_symbols, load_gate
    ├── applier.py        # apply_plan: preconditions, backup, ordered writes, undo
    └── verify.py         # verify_install, pin/pad check, name-elsewhere index (reusable from the planner)
tests/
├── installfixtures.py    # byte builders: extends pair, MF/MP symbol, model-bearing footprint, extra-pad footprint, per-version target libs
├── test_kicad_files_write.py
├── test_kicad_cli.py
├── test_install_plan.py
├── test_install_apply.py
├── test_install_verify.py
└── test_install_e2e.py   # UL sample into a tmp_path copy of Custom/, success criteria 1-5
```
`verify.py` may be merged into `applier.py`; keep `find_name_elsewhere` importable on its own because Phase 5 may call it at plan time.

### Pattern 1: Plan carries content; apply is dumb
**What:** `InstallPlan` holds, for each file the install will create or change, the final bytes plus `base_sha256` (None when the file must not exist). The model copy is the one exception: it holds the `PackageFile` (source, size, sha256) and the destination, and is streamed/read at apply. Identical items produce no `FileOp` (this is how INST-09 holds).
**When to use:** All writes. The same object is what Phase 5 renders (PREV-07).
**Example (shape only, names are Claude's discretion):**
```python
# Source: ARCHITECTURE.md Pattern 2, adapted to CONTEXT D-05..D-09
@dataclass(frozen=True)
class FileOp:
    path: Path
    data: bytes | None          # None for a model copy
    source: PackageFile | None  # model copy only
    base_sha256: str | None     # None => path must not exist
    kind: str                   # "symbol_lib" | "footprint" | "model" | "mkdir"

@dataclass(frozen=True)
class Conflict:
    key: str                    # stable across rebuilds: "symbol:<lib>:<name>", "footprint:<lib>:<name.casefold()>", "model:<file.casefold()>"
    kind: str
    existing: str               # human text for the preview
    suggested_name: str         # first free <name>_2, <name>_3 ... (D-06)
    resolution: str | None      # None | "overwrite" | "rename" | "skip"
    rename_to: str | None
```
Conflict keys must be stable (Phase 5 stores resolutions by key and re-plans on every edit). `InstallOptions.resolutions: Mapping[str, Resolution]` is the only way a conflict is resolved; there is no default and no "all".

### Pattern 2: Version decision table (D-01, D-04) with verified CLI facts
| Incoming vs target header | `kicad-cli` | Action |
|---|---|---|
| equal | any | splice vendor text as-is, no CLI call |
| incoming < target | found, `sym upgrade` output version == target | splice the CLI output block |
| incoming < target | found, output version != target (e.g. UL 20211014 into IMU 20231120; or KiCad 10 CLI `20251024` into a `20241209` lib) | splice vendor text, WARNING naming both versions |
| incoming < target | not found | splice vendor text, WARNING + INFO that the gate was skipped |
| incoming > target | any | ERROR `install.version_newer_than_target` (open and save that library in KiCad first) |
| new library | found | whole new file from the CLI output header (`20241209`, `kicad_symbol_editor`, `generator_version "9.0"`), edited block inside |
| new library | not found | header copied from the vendor file's header span so version and content agree |
Compare versions as integers (`kicad_files.file_version` already returns `int | None`). If either version is `None`, see Open Question 3.

### Pattern 3: Symbol pipeline (extract, normalise once, edit, splice)
1. **Extract the unit.** From the vendor file, the chosen symbol plus its `extends` ancestors (follow `(extends "X")` in the same file; cycle or missing parent = ERROR `install.extends_parent_missing`). To feed the CLI, delete the non-chosen top-level symbols from a copy of the vendor text with `Edit(start, end, "")` so the vendor header stays intact, write it to a staging `*.kicad_sym` outside the repo.
2. **Normalise once, memoised.** Key the cache on `(sha256(staging text), cli exe path, cli version)`. Run on the UNRENAMED vendor text so renames and field edits in the preview never re-invoke the CLI (about 0.8 s per call [VERIFIED: spike S1]). `sym upgrade` is deterministic [VERIFIED: S1, `cmp out1 out2` identical], so the planned block text is stable across rebuilds and across a second import.
3. **Edit the block text** (not the file): all edits are `Edit` splices on the block's own parse (`parse(block_text)`), applied once with `apply_edits`.
4. **Splice into the target** with the rule: replace span (overwrite, D-08) / insert after the last top-level `symbol` node as `eol + indent + normalize_eol(block, target.eol)` where `indent` is the whitespace between the previous newline and that last symbol's start; if the library has no symbols, insert after its last child instead. This rule gave a loadable library in both an old-format and a new-format target in the spike [VERIFIED: S9].

Rename algorithm (INST-02, D-14), all on `unquote`d names, no substring work:
- top-level `(symbol "OLD" ...)`: replace the name token with `quote(NEW)`.
- each direct child `symbol` whose name matches `^OLD_(\d+)_(\d+)$` (use `re.escape(OLD)`): replace with `quote(NEW + "_u_s")`.
- each `(extends "OLD")` list whose string equals OLD, in every symbol of the install unit: replace the string token.
- `Value` property and `ki_keywords` space-separated tokens: change only a value/token that equals OLD exactly.
Verified consequence: renaming the top-level name alone leaves a library KiCad 9 refuses (`Unable to load library`, exit 2); a stale `extends` after a parent rename also exits 2 [VERIFIED: spike S8]. A test that the CLI gate catches a deliberately incomplete rename doubles as a regression guard.

Property operations (INST-03, D-11..D-15). Treat properties as a list keyed by name; `kicad_files.find_property` already gives `value_node`:
- **set** existing: `Edit(value_node.start, value_node.end, quote(value))`.
- **rename in place** (D-12): replace `name_node` only. Resolve the role by the same priority lists Phase 3 uses: `MANUFACTURER_FIELDS = ("Manufacturer", "MF", "MANUFACTURER", "Manufacturer_Name")`, `MPN_FIELDS = ("MPN", "MP", "Manufacturer_Part_Number", "MANUFACTURER_PART_NUMBER")` [VERIFIED: kicad_lib_manager/importer/adapters/base.py:29-30]. If a property already named exactly `Manufacturer`/`MPN` exists, use it (no rename, no duplicate).
- **add hidden** (D-13): clone a sibling property node as the template (prefer a hidden one: Datasheet, Footprint, `ki_keywords`, `ki_fp_filters`), then edit name token, value token and, if present, the `(id N)` child to `max(existing ids)+1`. The clone carries the target format's `(id N)` vs none and bare `hide` vs `(hide yes)` automatically. The spike prototype did exactly this and both an old-format and a new-format target loaded (S9). Insert it after the last existing top-level `property` child of the symbol. Fall back to a synthesised block (per Pitfall: `has_ids`, `hide_form` sniffed from the symbol) only when no template exists.
- `ki_fp_filters`: set (or add hidden) to the space-joined installed footprint names (D-15). `Footprint`: set (or add hidden) to `<Lib>:<FP1>`.
- Description: write `Description` when the target header is >= `20230620`, else `ki_description` [CITED: KiCad `10.0` `sch_file_versions.h`: "20230620: `ki_description` became the Description field."]. Note the CLI upgrade itself adds an empty `Description` property to a 20211014 symbol [VERIFIED: S1], so after normalisation a `Description` already exists; set it rather than add.

### Pattern 4: Footprint pipeline (D-02, D-14, INST-03, INST-05)
Footprint bytes are the vendor bytes plus three kinds of span edit, nothing else:
- name: `footprint_name(root).name_node` -> `quote(final_name)`.
- value text: the direct child `(fp_text value <token> ...)` (KiCad 6/7 form; the UL sample has `(fp_text value DQK0006B ...)` with an UNQUOTED atom) or `(property "Value" "<v>" ...)` (KiCad 8+ form). Replace the token with `quote(final_name)`. D-14 says it always follows the final footprint name.
- model: if `find_models` is non-empty, `retarget_model(first, "${CUSTOM_3DMODEL_DIR}/<file>")` (keeps offset/scale/rotate). If empty, insert a model block immediately after the last direct child of the footprint, indented like that child, using the file's EOL. The block below was accepted and preserved by `kicad-cli fp upgrade` [VERIFIED: S10]:
```
(model "${CUSTOM_3DMODEL_DIR}/CSD85301Q2.stp"
  (offset (xyz 0 0 0))
  (scale (xyz 1 1 1))
  (rotate (xyz 0 0 0))
)
```
Extra `(model ...)` blocks beyond the first: leave as is and WARN (see Open Question 4). With no model chosen, do not touch existing model paths; emit `install.stale_model_path` for any that are not `${...}`-based so they are not silent (the existing scanner flags them on the next scan too).
Never touch the footprint's `(version ...)`, `(generator ...)`, `(tags ...)` or `embedded_files` (Pitfall 19). If `FootprintItem.has_embedded_files`, emit a WARNING.

### Pattern 5: Model file rules (INST-04, D-06, D-07, D-10)
- Destination `layout.models_dir / sanitize_filename(MPN + original_ext).sanitized`; flat, never a subfolder. The extension keeps its case (`.stp`, `.STEP`).
- Conflict scan: compare `casefold()` names against a listing of `models_dir` (`layout.list_model_files` returns posix relative paths of every file recursively). Same casefold name AND same SHA-256 AND identical exact-case spelling = identical, no op. Same casefold but different spelling = conflict even when the bytes match (the link would be case-wrong on Linux; D-10).
- Overwriting a case-twin on NTFS: `os.replace(tmp, 'Foo.step')` over an existing `foo.STEP` leaves a single directory entry named `Foo.step` [VERIFIED: spike S7, `['Foo.step']`]. So the exact-case verify passes after an overwrite. Rollback must restore the pre-image under the ORIGINAL spelling, so record the original path as it was listed, not the planned one.
- WR-04: `PackageFile.path` points into staging that dies on `Package.close()` [VERIFIED: package.py:70-77 `member: str`, `path: Path`, `kind: str`, `size: int`, `sha256: str`, `staged: bool`; `close()` removes the staging dir]. The plan holds `PackageFile` + sha256; `apply_plan` reads the bytes ONCE, compares `hashlib.sha256` to `PackageFile.sha256` (also guards a folder package edited after intake), and writes those bytes. Mismatch or vanished file = ERROR `install.source_changed` / `install.source_gone` before any write. Document that the `Package` must stay open until `apply_plan` returns.

### Pattern 6: Transaction (D-18, D-19)
1. Preconditions (no writes): resolve every target and require `is_relative_to(layout.custom_dir.resolve())`; `sha256(current bytes) == base_sha256` for every existing target (`install.stale_plan` otherwise: the user edited the library in KiCad between preview and install); sources present.
2. Backups: for each existing file the install will change, `fsutil.backup_file(path, backup_dir)` into a per-install folder `default_backup_dir() / "installs" / "<YYYYmmdd-HHMMSS>_<lib>"`. A backup failure (`fs.backup_failed`) aborts before any write. Prune sibling `installs/` folders to the newest 10 (name sorts by timestamp; delete only directories whose name matches the pattern and lie under `installs/`).
3. Write order: `mkdir` for a new `.pretty`, then model, then footprint(s), then the existing symbol library last (Pitfall 12 / D-19). After EACH successful write append `(path, pre_image_bytes | None, created_dirs)` to an undo list; a failed write is not in the list.
4. Verify from disk (Pattern 7). Any hard failure counts as a write failure.
5. Undo in reverse: restore pre-images with `fsutil.atomic_write_bytes`; `unlink` created files; `rmdir` created directories (deepest first). If an undo step itself fails, keep going, collect `install.rollback_failed` ERROR Issues that name each leftover path and the backup folder.
6. Result: `ok`, `touched` (tuple of paths written, empty on a no-op), `library`, `new_library`, `issues`, plus provenance fields Phase 6 will want (`candidate.vendor`, `candidate.source.name`).
Fault-injection seam: call `fsutil.atomic_write_bytes` through the module attribute (as `table_generator.write_tables` does), so tests use `monkeypatch.setattr(fsutil, "atomic_write_bytes", ...)` exactly like `tests/test_write_tables.py::_fail_replace_for`. Parametrise one test over "fail on the Nth write" for N = every write, plus a backup failure, a verify failure and a failing undo step. Assert a before/after snapshot of the whole copied `Custom/` tree (relative path -> sha256) is identical and that no `.tmp` and no empty created directory remain.

### Pattern 7: Verification (INST-08, D-18, D-20, D-21)
Hard checks (rollback on failure), all against files re-read from disk:
- every written `.kicad_sym` / `.kicad_mod` re-parses (`kicad_files.load`), the library holds the expected symbol names exactly once, and the library header bytes and every other symbol block are byte-identical to the pre-image (INST-01 invariant, assertable by comparing text outside the inserted span).
- `<Lib>:<FP>` resolves: `Footprints/<Lib>.pretty` exists, `<FP>.kicad_mod` is in `os.listdir` of it with exact case, and the footprint's internal name equals `<FP>`.
- the linked model: the path after `${CUSTOM_3DMODEL_DIR}/` is in an exact-case listing of `3DModels` (use `os.listdir`/`rglob` name sets, not `Path.exists()`, which ignores case on Windows; this mirrors `library_scanner._custom_model_names`).
Soft checks (WARNING only): pin/pad (POST-04) and name-elsewhere (POST-03).
- Pins: every `(number "N" ...)` under a `pin` in the symbol's sub-symbols (all units and body styles), union over the `extends` chain, as a set. Pads: the first token after `pad` in each direct `pad` child; ignore empty `""`. Compare sets both ways, one WARNING `verify.pin_pad_mismatch` listing both differences. Against the footprint actually linked (the existing one when skipped, D-09).
- Name elsewhere: see Pattern 8.

### Pattern 8: POST-03 name index without parsing stock libraries
[VERIFIED: spike S11] Fully parsing KiCad 9's stock symbols with `kicad_files` took 66.1 s for 227 files / 22,597 symbols (largest file 16 MB). A bytes-substring prefilter over all 236 MB took 0.2 s. Algorithm: `needle = ("(symbol " + sexpr.quote(name)).encode()`; read each `.kicad_sym` as bytes; if `needle` is in the data it is a candidate; confirm a candidate with a regex for a depth-1 declaration (`^[ \t]{1,2}\(symbol "<name>"` in multiline mode) and only fall back to a full parse for confirmed-ambiguous small files. Sources: other `Custom/Symbols/*.kicad_sym`, `WurthElektronik/**/*.kicad_sym` when the directory exists, and the stock dir `kicad_fp_dir.parent / "symbols"` [VERIFIED: `C:/Program Files/KiCad/9.0/share/kicad/symbols` exists and `find_kicad_footprint_dir` returns `<ver>/share/kicad/footprints`, library_scanner.py:241-267]. Exclude the target library. The stock libs exceed the 8 MiB intake cap, so do NOT route them through the intake `_read_limited`.

### Pattern 9: `kicad-cli` runner
- Locate: explicit path > `<kicad_fp_dir>.parents[2] / "bin" / "kicad-cli[.exe]"` when it is a file > `shutil.which("kicad-cli")`. Pass `kicad_fp_dir` in (the app already detects/stores it); do not import Qt or settings.
- Run with an injectable runner (`subprocess.run` by default), list arguments only (no `shell=True`), `capture_output=True, text=True, errors="replace"`, `timeout` about 60 s per call, `creationflags=CREATE_NO_WINDOW` on Windows (same pattern as `kicad_process.py:25-32`). A timeout or `OSError` is an Issue, not an exception.
- Always use a FRESH empty temp directory per call for outputs: the output path must not exist [VERIFIED: S5, `Output path must not conflict with existing path`, exit 4]. Staging filenames: symbol input must end in `.kicad_sym` [VERIFIED: S5/S10, `noext.txt` -> `Unable to convert library`, exit 2]; a footprint staging folder needs no `.pretty` suffix but must contain at least one `.kicad_mod` [VERIFIED: empty `.pretty` -> `Unable to convert library`, exit 2]. Use absolute paths (an absolute path can never be parsed as an option).
- Interpret results: exit 0 and an output file exists = converted (read its version with `file_version`); exit 0 and NO output file with stdout `Symbol library was not updated` = already current (treat as unchanged, not an error); exit 2 `Unable to load library` = file rejected; exit 3 `Symbol library does not exist or is not accessible`; exit 4 output conflict. The error text goes to stderr and carries no detail beyond that one line [VERIFIED: S5], so the ERROR Issue should add which file (merged library or staged footprint) failed.
- Gate (D-03): `sym upgrade --force -o <fresh> <temp copy of merged library>` and `fp upgrade --force -o <fresh> <staging dir with only the edited incoming footprints>`, discard the outputs. `--force` makes the gate exercise the writer and avoids relying on the no-output path. On failure, re-run the gate once on the UNMERGED target copy so the ERROR can say whether the target library already failed before the merge (recommended, about 0.8 s, only on the failure path).

### Anti-Patterns to Avoid
- **Rename by substring or `str.replace`:** rewrites the datasheet URL and `ki_keywords` (Pitfall 2/3); use the exact-match algorithm above.
- **Upgrading footprints with `fp upgrade` on the install path:** non-deterministic UUIDs defeat INST-09 [VERIFIED: S4, two runs differ at line 11].
- **Calling `kicad-cli` from `build_plan` on every edit:** memoise on the vendor block hash; the gate (two more calls) belongs at apply time or behind an explicit flag.
- **Using `Path.exists()` for model/footprint existence:** ignores case on Windows; use name sets.
- **Parsing stock symbol libraries to find duplicates:** 66 s; use the bytes prefilter.
- **Pointing `fp upgrade` at the real `.pretty`:** it rewrites the whole directory; staging copies only.
- **Reusing `MainWindow._scan_result` objects in the planner:** read the target fresh from disk (ARCHITECTURE anti-pattern 5).

## Spike Results (Research Flag)

All run on this machine against `kicad-cli` 9.0.9 using scratch copies under the session scratchpad; no repo file was modified. Python used `-I`. Vendor samples were the owner's UL sample extracted to a separate directory.

| # | Experiment | Result |
|---|-----------|--------|
| S1 | `sym upgrade` on the UL symbol (`20211014`, CRLF) | exit 0, stdout `Saving symbol library in updated format`; output `(version 20241209)`, `(generator "kicad_symbol_editor")`, `(generator_version "9.0")`, tab-indented, CRLF; deterministic (`cmp` of two runs identical, 0.83 s per call); added an empty `Description` property, reordered to Reference, Value, Footprint, Datasheet, Description, ki_locked, ki_keywords, ki_fp_filters; `(id N)` dropped; bare `hide` became `(hide yes)` |
| S2 | UL (`20211014`) symbol block spliced AS-IS into a copy of `IC_Magnetometer_Memsic` (`20241209`), then `sym upgrade --force` | exit 0; the CSD85301Q2 block in the re-saved library is byte-equal to the properly upgraded block (`equal 16054 16054`); KiCad sorted symbols alphabetically on save |
| S3 | Same into a copy of `IC_IMU_TDK` (`20231120`) | exit 0, block equal (`equal 16054 16054`) |
| S4 | `fp upgrade` on a staging dir holding `DQK0006B.kicad_mod`, twice | exit 0 both; outputs DIFFER at line 11 (random `uuid`s); output is `(version 20241229)`; re-running on current files prints `Footprint library was not updated` and writes nothing |
| S5 | Failure modes | truncated current-version symbol lib: `Unable to load library`, exit 2; unknown token: exit 2; missing input: `Symbol library does not exist or is not accessible`, exit 3; existing `-o` target: `Output path must not conflict with existing path`, exit 4; input without `.kicad_sym`: `Unable to convert library`, exit 2; empty `.pretty`: `Unable to convert library`, exit 2; truncated footprint: `Unable to load library`, exit 2; all error text on stderr; stdout empty on failure |
| S6 | `extends` fixture (`PARENT_X` + `CHILD_Y (extends "PARENT_X")`) through `sym upgrade` | exit 0; `(extends "PARENT_X")` is a direct child list of the child `symbol`; the child has NO sub-symbols (units live in the parent); KiCad adds inherited properties (Datasheet, Description, ki_keywords copied from the parent) to the child |
| S7 | `os.replace(tmp, "Foo.step")` over an existing `foo.STEP` on NTFS | directory then lists `['Foo.step']` only, content new |
| S8 | Rename damage | top-level renamed but `_1_1`/`_2_1` sub-symbols left stale: exit 2 `Unable to load library`; parent renamed with stale `extends` in the child: exit 2; child placed BEFORE its parent: exit 2 |
| S9 | Prototype: edit block (Footprint -> `Lib:DQK0006B`, `ki_fp_filters`, add hidden Manufacturer/MPN by cloning Datasheet with next `(id N)`), splice after the last symbol of (a) the `20211014` `IC_Battery_Charger_TI` copy as-is and (b) the `20241209` Memsic copy using the CLI-upgraded block | both merged libraries `sym upgrade --force` exit 0; (b) shows `Manufacturer "TI"` and `MPN "CSD85301Q2"` retained |
| S10 | Prototype footprint edit (name token, `fp_text value` atom -> quoted, insert `(model ...)` block with tab/space-matched indent and the file's CRLF) then `fp upgrade` | exit 0; output keeps `(model "${CUSTOM_3DMODEL_DIR}/CSD85301Q2.stp" (offset ...) (scale ...) (rotate ...))` and `(property "Value" "DQK0006B"` |
| S11 | POST-03 scan cost over KiCad 9 stock `symbols/` (227 files, 236 MB) | full `kicad_files` parse 66.1 s (22,597 symbols); depth-1 regex over text 2.61 s (same 22,597); bytes-substring prefilter 0.2 s |

Verbatim evidence for the load-bearing rows:
```
$ kicad-cli sym upgrade --force half.kicad_sym -o half_o2.kicad_sym   # top-level renamed, subs stale
Unable to load library
exit=2
$ kicad-cli sym upgrade --force half.kicad_sym -o half_o.kicad_sym    # -o already existed
Output path must not conflict with existing path
exit=4
$ kicad-cli sym upgrade out1.kicad_sym -o out3.kicad_sym              # already current
Symbol library was not updated
exit=0        (no out3.kicad_sym written)
$ kicad-cli fp upgrade stage.pretty -o outA.pretty ; ... -o outB.pretty ; cmp
outA.pretty/DQK0006B.kicad_mod outB.pretty/DQK0006B.kicad_mod differ: char 230, line 11
```
Not tested: KiCad 10 (not installed). [CITED: gitlab.com/kicad/code/kicad `10.0` `eeschema/sch_file_versions.h`] KiCad 10's symbol format is `20251024` ("Updated properties formatting (do_not_autoplace, show_name)"), so a KiCad 10 `kicad-cli` would write a different header than `Custom/`'s `20241209` libraries and D-01 would fall to the as-is path. Whether KiCad 10 loads a `20211014` symbol inside a `20241209` library is unverified; see Assumptions A1.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| S-expression parse/edit | regex rewrite or a new tokenizer | `sexpr.parse` + `Edit` + `apply_edits` + `quote`/`unquote` | Already round-trip tested; spans keep EOL/BOM/whitespace |
| Atomic single-file write | `open(..., "w")` | `fsutil.atomic_write_bytes` (temp + fsync + `os.replace` with retries, returns Issue) | Locked/read-only handling, Windows retries, fault-injection seam |
| Backup numbering | own scheme | `fsutil.backup_file(path, backup_dir)` into a per-install folder | Exclusive create, never leaves truncated backups |
| App-data backup root | own path logic | `fsutil.default_backup_dir()` | Per-OS, outside the repo (D-06) |
| EOL conversion of inserted text | manual replace | `fsutil.normalize_eol(text, source.eol)` | Mixed-EOL files keep their dominant style |
| Name sanitising | new rules | `naming.sanitize_name`, `sanitize_filename`, `case_clash` | Phase 3 contract |
| Placeholder check | new regex | `suggest.placeholder_tokens(name)` | D-04 contract |
| Model path retarget | splice by hand | `kicad_files.retarget_model` | Phase 2 D-16 helper |
| Symbol format conversion | hand-convert `(id N)`, `hide`, Description | `kicad-cli sym upgrade` (when allowed by D-01) | KiCad owns the format history (`sch_file_versions.h`) |
| Version-compare of KiCad dirs | string sort | `library_scanner.newest_version_dirs` | Numeric; `10.0` > `9.0` |
| Process listing / subprocess flags pattern | new pattern | follow `kicad_process.py` | `CREATE_NO_WINDOW`, `errors="replace"`, no shell |

**Key insight:** every hard part (splicing, atomicity, naming, format upgrade) already exists as a tested primitive or is delegated to KiCad's own CLI. Phase 4's new logic is orchestration: deciding what to write, proving it is the same thing the preview showed, and undoing it cleanly.

## Common Pitfalls

### Pitfall 1: `kicad-cli` output file may not exist, and must not pre-exist
**What goes wrong:** Code assumes `-o` always produces a file, or reuses a temp path.
**Why it happens:** A current-version input prints `... was not updated`, exits 0 and writes nothing; an existing `-o` path exits 4. [VERIFIED: S5]
**How to avoid:** Fresh `tempfile.mkdtemp` per call, output path = `dir / "out.kicad_sym"` (not created); after exit 0 check `output.is_file()`; absent means "unchanged".
**Warning signs:** Intermittent `exit=4` in tests that reuse a staging dir.

### Pitfall 2: Treating "equal version" and "CLI says not updated" as different outcomes
**What goes wrong:** An incoming symbol already at the CLI's version triggers an unneeded or failing branch.
**How to avoid:** Decide by comparing the integer versions first (Pattern 2); only call the CLI for incoming < target.

### Pitfall 3: The CLI changes the symbol, so D-07 compares against the NORMALISED block
**What goes wrong:** Re-import shows a conflict because the first install wrote the CLI-upgraded text and the second plan compared against raw vendor text.
**Why it happens:** `sym upgrade` adds `Description`, drops ids, rewrites indentation [VERIFIED: S1].
**How to avoid:** The planned block is always the final text (post-normalisation, post-edit). Compare that to the existing block after `normalize_eol`. The memoised CLI call makes it deterministic.

### Pitfall 4: Whole-library stock scan blocks for a minute
**What goes wrong:** POST-03 implemented with `kicad_files.load` over the stock dir stalls the worker for about 66 s [VERIFIED: S11].
**How to avoid:** Pattern 8.

### Pitfall 5: Pins of a derived symbol live in the parent
**What goes wrong:** POST-04 reports "all pads have no pin" for an `extends` child [VERIFIED: S6, child has no sub-symbols].
**How to avoid:** Union pin numbers over the symbol and its `extends` ancestors (resolved inside the same installed library).

### Pitfall 6: KiCad re-sorts symbols and rewrites formatting on its own save
**What goes wrong:** Tests or logic assume appended order survives or that the file stays byte-identical after a KiCad round trip [VERIFIED: S2, output sorted alphabetically].
**How to avoid:** Assert on the written bytes, never on KiCad's re-saved output; use KiCad's output only as a pass/fail load gate and, in tests, for semantic comparison of the symbol block.

### Pitfall 7: `ImportCandidate` outlives its staged files (WR-04) and package warnings are lost (WR-05)
**What goes wrong:** Apply reads `PackageFile.path` after the dialog closed the `Package`; or a skipped deep folder or unreadable file looks like "nothing found".
**How to avoid:** Document and enforce "Package open until `apply_plan` returns"; re-hash at apply (`install.source_gone` / `install.source_changed`). For WR-05 accept `package_issues: Sequence[Issue] = ()` in `build_plan` (non-breaking) and append them to `plan.issues`, or fix at source by folding `package.issues` into `detect_candidate`'s candidate (a three-line Phase 3 edit; check `tests/test_adapters.py` for exact-equality assertions on `candidate.issues` first).

### Pitfall 8: Pair name case-twin creates a second library on Linux and a silent merge on Windows
**What goes wrong:** New library `ic_imu_tdk` when `IC_IMU_TDK.kicad_sym` exists.
**How to avoid:** Casefold-compare the library name against both `Symbols/` and `Footprints/` listings (D-10); a case-only clash is `ERROR install.library_case_clash` (no overwrite/rename/skip applies to a library).

### Pitfall 9: Incomplete library pair
**What goes wrong:** `Symbols/X.kicad_sym` exists but `Footprints/X.pretty` does not (`IC_IMU_TDK` today has no footprint library [VERIFIED: tests/zipfixtures.py `CURRENT_CUSTOM_FOOTPRINT_LIBS` excludes it and the `Custom/Footprints` listing has no `IC_IMU_TDK.pretty`]).
**How to avoid:** Create the missing half in the same transaction and add a WARNING `install.pair_completed`. Installing the UL part into `IC_IMU_TDK` is therefore a realistic, testable case.

### Pitfall 10: Registering new modules in the layering guard
**What goes wrong:** `tests/test_importer_layering.py` fails every new `importer/*.py` as "not registered in ALLOWED" and flags any import not on its allow-list.
**How to avoid:** Add entries for `importer.plan`, `importer.planner`, `importer.kicad_cli`, `importer.applier`, `importer.verify` (and their allowed relative imports, e.g. `fsutil`, `kicad_files`, `sexpr`, `models`, `importer.candidate`, `importer.package`, `importer.naming`, `importer.layout`, `importer.suggest`, `importer.adapters.base`) in the same plan that creates them. `tests/test_layering.py` `ALLOWED` covers `kicad_files` and the foundation modules; extend `kicad_files`'s allowed set only with modules it truly needs (it must not import `importer`).

### Pitfall 11: `--strict-markers` rejects an unregistered `kicad_cli` marker
**What goes wrong:** Collection error for tests marked `@pytest.mark.kicad_cli`.
**How to avoid:** Add the marker to `[tool.pytest.ini_options] markers` in `pyproject.toml` [VERIFIED: pyproject.toml lines 4-6 `addopts = "-ra --strict-markers"` and a `markers = [` list with `wurth` and `local_kicad`] (Wave 0).

### Pitfall 12: Rollback restores the wrong case
**What goes wrong:** After an overwrite of a case-twin the planned spelling replaced the original (S7); a rollback that writes to the planned path leaves the wrong spelling behind.
**How to avoid:** Record the pre-image against the path as listed on disk before the write.

### Pitfall 13: Stale plan clobbers a library edited in KiCad
**What goes wrong:** The preview is open while the user saves in the Symbol Editor; apply overwrites with text derived from the old base.
**How to avoid:** `base_sha256` precondition (`install.stale_plan`), instruct the caller to rebuild the plan.

### Pitfall 14: Empty `.pretty` is invisible to git and fails the CLI footprint gate
**What goes wrong:** A symbol-only install into a new library creates an empty `.pretty`; git will not track it and `fp upgrade` rejects an empty directory [VERIFIED: S5].
**How to avoid:** Skip the footprint gate when no footprints are installed; WARN that the empty folder will not be committed (Open Question 5).

## Code Examples

Verified patterns (from the spike prototypes; adapt, do not copy blindly).

### Run `kicad-cli` with a fresh output path
```python
# Source: spike S1/S5/S10 against kicad-cli 9.0.9; subprocess pattern from kicad_lib_manager/kicad_process.py:25-32
def _run(exe: Path, args: list[str], *, timeout: float = 60.0, runner=subprocess.run):
    return runner(
        [str(exe), *args],
        capture_output=True, text=True, errors="replace", timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

def upgrade_symbol_file(exe, staged_sym: Path, workdir: Path):
    out = workdir / "out.kicad_sym"          # must not exist
    r = _run(exe, ["sym", "upgrade", "--force", "-o", str(out), str(staged_sym)])
    if r.returncode != 0:
        return Issue(Severity.ERROR, "install.cli_gate_failed",
                     f"kicad-cli rejected {staged_sym.name} (exit {r.returncode}): {r.stderr.strip() or r.stdout.strip()}")
    return out if out.is_file() else None     # None = already current
```

### Exact rename on a block (no substring replacement)
```python
# Source: algorithm per D-14 / PITFALLS 3; node helpers from kicad_lib_manager/kicad_files.py and sexpr.py
def rename_edits(block_root_symbol, old: str, new: str) -> list[Edit]:
    sub = re.compile(re.escape(old) + r"_(\d+)_(\d+)$")
    edits = [Edit(block_root_symbol.children[1].start, block_root_symbol.children[1].end, quote(new))]
    for child in block_root_symbol.children:
        if child.head == "symbol" and len(child.children) >= 2:
            name = unquote(child.children[1].text)
            m = sub.fullmatch(name)
            if m:
                tok = child.children[1]
                edits.append(Edit(tok.start, tok.end, quote(f"{new}_{m.group(1)}_{m.group(2)}")))
        elif child.head == "extends" and len(child.children) >= 2 and unquote(child.children[1].text) == old:
            tok = child.children[1]
            edits.append(Edit(tok.start, tok.end, quote(new)))
    return edits
```

### Insert a symbol block into a target library text
```python
# Source: spike S2/S9 (proto_merge.py); fsutil.normalize_eol exists at fsutil.py:244
def insert_symbol(target: LoadedFile, block: str) -> str:
    syms = find_symbols(target.root)
    anchor = syms[-1].node if syms else lib_node.children[-1]   # lib_node = first top-level "kicad_symbol_lib"
    text = target.source.text
    line_start = text.rfind("\n", 0, anchor.start) + 1
    indent = text[line_start:anchor.start]
    ins = target.source.eol + indent + normalize_eol(block, target.source.eol)
    return apply_edits(text, [Edit(anchor.end, anchor.end, ins)])
```

### Clone a hidden property as the template for a new field
```python
# Source: spike S9 (proto_install.py); `(id N)` child is edited only when the template carries one
def new_hidden_property(symbol_text, template_node, name, value, next_id):
    t = symbol_text[template_node.start:template_node.end]
    tr = parse(t).children[0]
    edits = [Edit(tr.children[1].start, tr.children[1].end, quote(name)),
             Edit(tr.children[2].start, tr.children[2].end, quote(value))]
    for c in tr.children:
        if c.head == "id" and next_id is not None:
            edits.append(Edit(c.children[1].start, c.children[1].end, str(next_id)))
    return apply_edits(t, edits)
```

### Fault-injection test shape (reuses the Phase 1/2 convention)
```python
# Source: tests/test_write_tables.py _fail_replace_for pattern (monkeypatching fsutil.atomic_write_bytes)
@pytest.mark.parametrize("fail_on", range(1, N_WRITES + 1))
def test_failure_on_write_n_restores_everything(tmp_path, monkeypatch, fail_on):
    before = snapshot(custom_root)                       # {relpath: sha256}
    real, calls = fsutil.atomic_write_bytes, []
    def flaky(path, data, **kw):
        calls.append(path)
        if len(calls) == fail_on:
            return Issue(Severity.ERROR, "fs.write_failed", f"Could not write {path.name}: injected")
        return real(path, data, **kw)
    monkeypatch.setattr(fsutil, "atomic_write_bytes", flaky)
    result = apply_plan(plan, backup_dir=tmp_path / "bk")
    assert not result.ok and any(i.code == "install.rolled_back" for i in result.issues)
    assert snapshot(custom_root) == before               # also no .tmp files, no new dirs
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Symbol property `(id N)` | no ids written | `20220914` "Stopped saving property ID" [CITED: KiCad `sch_file_versions.h`, `10.0` branch] | Clone-a-sibling approach covers both without a version table |
| `ki_description` property | `Description` field | `20230620` [CITED: same] | Write `Description` for targets >= `20230620`, else `ki_description` |
| `generator_version`, V8 cleanups | | `20231120` [CITED: same] | `IC_IMU_TDK` is this version in `Custom/` |
| Embedded files | | `20240529` [CITED: same] | Footprints may carry `(embedded_files`; warn, do not strip |
| Private flags for fields | | `20241209` [CITED: same] | KiCad 9 format; `Custom/` majority |
| Tilde no longer means empty text | | `20250318` [CITED: same] | Do not "fix" `~` Datasheet values in older targets; do not write `~` into newer ones |
| Stacked pin notation | | `20250901` [CITED: same] | A pin number like `[1-3]` may denote several pins in KiCad 10 libraries; POST-04 may false-positive on those (Assumption A4) |
| Properties formatting (`do_not_autoplace`, `show_name`) | | `20251024` = KiCad 10 symbol format [CITED: same] | Cloning a sibling property inherits whichever form the target uses |

**Deprecated/outdated:**
- Normalising footprints on install: dropped by D-02 (non-deterministic UUIDs).
- The "unconnected" assumption that a vendor's pad numbers equal pin numbers: vendors commonly differ (exposed pad); handled as a soft warning.

## Runtime State Inventory

Omitted. This is a new feature phase, not a rename/refactor/migration. The one runtime-state item worth stating: new app-data folder `default_backup_dir()/installs/` is created by the applier (verified safe: `default_backup_dir` "never created here", fsutil.py:232 docstring), and `Custom/` is never written outside tests.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | KiCad 10 loads a `20211014` symbol spliced into a `20241209`/`20251024` library the same way KiCad 9 does (spike S2 only covers 9.0.9) | Spike Results, Pattern 2 | The D-01 as-is path could produce a library KiCad 10 rejects; the D-03 gate would catch it only if `kicad-cli` is the 10.x one |
| A2 | `kicad-cli` exit codes (2 load failure, 3 missing, 4 output conflict) and messages are stable across KiCad 9.x patch releases and 10 | Pattern 9 | Runner mis-classifies; mitigate by treating every non-zero exit as failure and using the codes only for message text |
| A3 | Timeout of about 60 s per CLI call and backup retention N=10 are acceptable | Pattern 6, 9 | Slow disks/large target libraries time out; N too small loses a recovery point. Both are Claude's discretion per CONTEXT |
| A4 | A bracketed pin number such as `[1-3]` (stacked pins, format `20250901`) expands to several pins in KiCad 10 | State of the Art, Pattern 7 | POST-04 false positive/negative on KiCad 10-format libraries; soft warning only |
| A5 | KiCad's loader requires a parent before its child for the reasons observed (verified only as "child before parent exits 2" on 9.0.9) | Pattern 3 | If a later version relaxes it, the parent-first ordering is merely conservative |
| A6 | Renamed (not newly added) vendor Manufacturer/MPN fields keep the vendor's own visibility | Pattern 3 | If the owner expects them hidden, one extra edit per renamed property is needed (Open Question 7) |
| A7 | Applying the Footprint link and `ki_fp_filters` to the `extends` parent as well as the child is wanted | Open Question 8 | A parent left with a bare `DQK0006B` Footprint value would be an unresolved link for anyone placing the parent |

## Open Questions

1. **Where does the CLI load gate (D-03) run: planner or applier?**
   - What we know: it needs the fully rendered merged library, takes about 0.8 s per call (two calls plus an optional blame call), and D-03 says it runs before anything is written. PREV-07 wants the plan cheap to rebuild.
   - What's unclear: whether Phase 5 wants gate results visible in the preview.
   - Recommendation: make it a separate function `run_load_gate(plan, cli) -> list[Issue]` called by `apply_plan` as precondition step 0 (so apply is always protected), and expose it to Phase 5 as an optional explicit "Check with KiCad" action. Keep `build_plan` free of gate calls; it only calls the memoised symbol normalisation.
2. **How should Phase 5 pass KiCad context?**
   - Recommendation: a small frozen `ToolContext(kicad_cli: Path | None, kicad_symbols_dir: Path | None, extra_symbol_dirs: tuple[Path, ...])` argument to `build_plan`/`apply_plan`, defaulting to "none found". Tests inject a fake runner; no globals.
3. **Version `None` (header or incoming file lacks a parseable `(version N)`).**
   - Recommendation: treat as unknown, splice as-is, WARNING `install.version_unknown`; never refuse on `None`.
4. **Multiple `(model ...)` blocks in the vendor footprint (D-17 allows zero or one linked model).**
   - Recommendation: retarget the first, leave the rest, WARN `install.extra_models` (their paths are vendor-relative and will not resolve). Removing them would be a destructive edit nobody asked for.
5. **Symbol-only package into a NEW library (no footprint to place).**
   - Recommendation: still create the empty `.pretty` (LIB-02 says a pair), WARN that git does not track empty folders, skip the footprint gate.
6. **Footprint-only package (no symbol).**
   - D-17 says "exactly one symbol". Recommendation: ERROR `install.no_symbol`; Phase 3 already emits `intake.no_symbol` as a WARNING at intake.
7. **Visibility of renamed Manufacturer/MPN (D-12 vs D-13).**
   - D-13 speaks of the NEW properties being hidden. Recommendation: leave a renamed vendor property's visibility alone (fewest edits); only newly added ones are hidden. Confirm with the owner if they want renamed ones forced hidden.
8. **`extends` chain field edits.**
   - Recommendation: Footprint link and `ki_fp_filters` apply to every symbol of the chain; `Manufacturer` the same value for all; `MPN` defaults to each symbol's own vendor name unless the caller overrides. The model name uses the chosen (child) symbol's MPN.
9. **INST-06 and ROADMAP criterion 3 text amendment (D-02).** Must be edited when the phase closes: "the incoming symbol is normalised ... footprints are copied as-is". Put it in the closing plan's tasks.
10. **Package-level Issues (WR-05).** Choose `package_issues` parameter vs fixing `detect_candidate`; see Pitfall 7. Either is acceptable; do not leave it silent.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (venv) | all code and tests | yes | 3.14.4 | — |
| pytest | tests | yes | 9.1.1 | — |
| `kicad-cli` | D-01 normalisation, D-03 gate, D-22 load check | yes | 9.0.9 at `C:/Program Files/KiCad/9.0/bin/kicad-cli.exe` | tests skip via `kicad_cli` marker; runtime: as-is plus WARNING and INFO "gate skipped" |
| KiCad stock `symbols/` | POST-03 stock search | yes | `C:/Program Files/KiCad/9.0/share/kicad/symbols` (228 entries) | search only repo libraries |
| `Custom/` submodule checked out | realistic target libs in tests | yes | 10 symbol libs, 9 footprint libs, 13 models | synthetic builders in `tests/installfixtures.py` |
| WurthElektronik submodule | POST-03 Wurth search, corpus tests | no (not checked out; `tests/test_roundtrip_corpus.py` skips) | — | search skipped when directory absent |
| KiCad 10 | KiCad 10 behaviour | no | — | none; see A1 |
| git | not used in Phase 4 | yes | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** WurthElektronik (skip its search), KiCad 10 (assumption A1, manual UAT per D-22 covers KiCad 9 only).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (pytest-qt 4.5.0 installed, not needed here) |
| Config file | `pyproject.toml` (`testpaths = ["tests"]`, `pythonpath = ["."]`, `addopts = "-ra --strict-markers"`) |
| Quick run command | `./env/Scripts/python.exe -m pytest tests/test_install_plan.py -x -q` |
| Full suite command | `./env/Scripts/python.exe -m pytest -q` (baseline 909 passed, 4 skipped in about 25 s [VERIFIED: run on this machine]) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INST-01 | symbol added; header and every other symbol byte-identical (compare text outside the inserted span) | unit + e2e | `pytest tests/test_install_e2e.py::test_ul_symbol_added_others_identical -x` | Wave 0 |
| INST-02 | rename follows `_u_s` subs and `extends`; exact match only; `Value`/`ki_keywords` exact tokens; no-substring cases (name inside datasheet URL) | unit | `pytest tests/test_kicad_files_write.py -k rename -x` | Wave 0 |
| INST-03 | footprint filename, internal name, value text (atom and `property` forms), Footprint field, `ki_fp_filters` all equal | unit + e2e | `pytest tests/test_install_plan.py -k footprint_consistency -x` | Wave 0 |
| INST-04 | model copied `CSD85301Q2.stp`; same sha reused; different sha conflict; case-twin conflict | unit | `pytest tests/test_install_plan.py -k model -x` | Wave 0 |
| INST-05 | missing `(model` inserted; existing path retargeted; offsets preserved | unit | `pytest tests/test_kicad_files_write.py -k model -x` | Wave 0 |
| INST-06 | version table: equal/older+CLI ok/older+CLI mismatch/older no CLI/newer refused; fake runner for branches, real CLI for one | unit + `kicad_cli` | `pytest tests/test_install_plan.py -k version -x` | Wave 0 |
| INST-07 | fault injection on every write, backup, verify and undo step; tree snapshot identical, no `.tmp`, no new dirs | unit | `pytest tests/test_install_apply.py -k rollback -x` | Wave 0 |
| INST-08 | verify hard checks (broken link, missing model, bad parse) trigger rollback | unit | `pytest tests/test_install_verify.py -k hard -x` | Wave 0 |
| INST-09 | second identical install: no FileOps, `touched == ()`, tree unchanged, no backup folder created | e2e | `pytest tests/test_install_e2e.py::test_second_install_is_noop -x` | Wave 0 |
| INTK-08 | no model: installs, `install.no_model` WARNING, no model block, no `3DModels` write | unit | `pytest tests/test_install_plan.py -k no_model -x` | Wave 0 |
| LIB-02 | new library creates `.kicad_sym` + `.pretty`; existing header never changed; pair completion; case-twin library ERROR; placeholder refusal | unit + e2e | `pytest tests/test_install_plan.py -k library -x` | Wave 0 |
| POST-03 | name in another Custom lib / stock-like dir warned, target lib excluded, prefilter hit with non-depth-1 match not counted | unit | `pytest tests/test_install_verify.py -k elsewhere -x` | Wave 0 |
| POST-04 | pin/pad mismatch both directions, empty-number pads ignored, `extends` child pins via parent | unit | `pytest tests/test_install_verify.py -k pin_pad -x` | Wave 0 |
| (D-03/D-22) | real `kicad-cli` load check of the UL install result | `kicad_cli` e2e | `pytest tests/test_install_e2e.py -m kicad_cli -x` | Wave 0 |
| (layering) | new modules registered and Qt-free | unit | `pytest tests/test_importer_layering.py tests/test_layering.py -x -q` | exists; edit |

### Sampling Rate
- **Per task commit:** the single new test file for that task (`-x -q`), under 10 s.
- **Per wave merge:** `./env/Scripts/python.exe -m pytest -q`.
- **Phase gate:** full suite green (including the `kicad_cli` tests on this machine) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `pyproject.toml`: register `kicad_cli` marker (`--strict-markers` is on).
- [ ] `tests/conftest.py`: fixtures `custom_copy` (copy `Custom/Symbols`, `Footprints`, `3DModels` into `tmp_path/Custom`, excluding `.git`; skip if the submodule is absent), `ul_package` (open the UL zip, yield candidate, close), `kicad_cli_path` (locate or skip), `snapshot(root)` helper.
- [ ] `tests/installfixtures.py`: byte builders for an `extends` parent/child pair, a vendor symbol with `MF`/`MP`/`MANUFACTURER` fields, a footprint that already has a `(model ...)` block, a footprint with an extra exposed pad (pin/pad mismatch), and synthetic target libraries at `20211014` (CRLF, blank first line, 2-space indent, ids), `20231120` and `20241209` (tab indent). Build bytes at test time; do not commit copied real libraries.
- [ ] `tests/test_importer_layering.py`: register the new importer modules in `ALLOWED`.
- [ ] A fake `kicad-cli` runner used by `tests/test_kicad_cli.py` and the version-table tests (scripted exit codes, outputs and "not updated" no-output case).
- [ ] Framework install: none.

## Security Domain

`security_enforcement` is enabled in `.planning/config.json` (`"security_enforcement": true`, `"security_asvs_level": 1`, `"security_block_on": "high"`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — (local desktop tool) |
| V3 Session Management | no | — |
| V4 Access Control | yes (filesystem scope) | Every write target resolved and checked `is_relative_to(layout.custom_dir.resolve())`; never write to `WurthElektronik/`; refuse junction/symlink escapes via `resolve()` |
| V5 Input Validation | yes | Names (library, symbol, footprint, model) pass `sanitize_name`/`sanitize_filename` and are re-validated after caller overrides; vendor text parsed with the capped parser (8 MiB, 1,000,000 nodes, Phase 3) before use; values written with `sexpr.quote` |
| V6 Cryptography | no | SHA-256 used for identity/integrity only (no secret handling) |
| V12 Files and Resources | yes | Atomic writes, containment, TOCTOU re-hash of the model and base-hash precondition for existing files; staging for `kicad-cli` in a fresh temp dir outside the repo |
| V14 Configuration | yes (minor) | `subprocess` with list arguments, no `shell=True`, absolute paths, timeout, no environment secrets |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via vendor-derived names (`..\..\x` as a footprint or model name, library name) | Tampering / Elevation | `sanitize_name`/`sanitize_filename` plus the containment check on the resolved final path; reject names that sanitise to the `Unnamed` placeholder (`naming.empty` is an ERROR Issue) |
| Hostile S-expression sent to `kicad-cli` (hang, crash) | Denial of service | Timeout per call; staging in a throwaway temp dir; nothing written to the repo until the gate passes; never run an interpreter from the staging directory |
| Argument injection through filenames starting with `-` | Tampering | Absolute staging paths, list-form argv, fixed subcommands |
| Symlink/junction inside `Custom/` redirecting a write | Tampering | `resolve()` then `is_relative_to`; fail with `install.path_outside_custom` |
| TOCTOU: package or library changed between preview and apply | Tampering | `base_sha256` precondition per existing file; re-hash model bytes against `PackageFile.sha256` at apply |
| Large model exhausting memory | Denial of service | Intake already caps members at 100 MiB (`MAX_MEMBER_BYTES`); apply reads once; do not hold model bytes in plans that are rebuilt per edit |
| Rollback leaves a half-state | Integrity | Pre-images in memory, app-data backups, collected `install.rollback_failed` Issues naming leftovers |
| Backup pruning deleting the wrong tree | Tampering | Delete only directories directly under `installs/` whose names match the timestamp pattern |

## Sources

### Primary (HIGH confidence)
- Local spikes on `kicad-cli` 9.0.9 (this machine, 2026-10-19): S1-S11 above, outputs quoted verbatim.
- Repo source read this session: `kicad_lib_manager/sexpr.py`, `kicad_files.py`, `fsutil.py`, `models.py`, `kicad_process.py`, `library_scanner.py`, `importer/{candidate,package,layout,naming,suggest,detect}.py`, `importer/adapters/base.py`, `tests/test_importer_layering.py`, `tests/test_layering.py`, `tests/zipfixtures.py`, `tests/conftest.py`, `pyproject.toml`.
- Real `Custom/` libraries (headers `20211014` CRLF with leading blank line, `20231120`, `20241209` tab-indented) and the UL sample footprint/symbol (read directly).
- `.planning/phases/04-plan-and-install-core/04-CONTEXT.md`, `REQUIREMENTS.md`, `STATE.md`, `03-REVIEW-DISPOSITION.md`, `.planning/research/{ARCHITECTURE,PITFALLS}.md`.

### Secondary (MEDIUM confidence)
- [CITED: https://gitlab.com/kicad/code/kicad/-/raw/10.0/eeschema/sch_file_versions.h] symbol-library format history through `20251024` (fetched this session).
- `reports/KiCad 10 vendor part import.md` (secondary survey; its KiCad 10 version claims were cross-checked against the header above).

### Tertiary (LOW confidence)
- None used for recommendations. KiCad 10 load behaviour of mixed-version libraries is explicitly unverified (A1).

## Project Constraints (from CLAUDE.md)

Extracted actionable directives from `./CLAUDE.md` and `./.claude/CLAUDE.md`:
- Python 3.10+ (venv on 3.14), PySide6 6.12, **stdlib only** otherwise; extend the existing app, no new dependency without clear justification.
- Windows 11 primary with standard CPython (not MSYS2); keep the existing cross-platform branches working.
- KiCad output must load in KiCad 6+ (current install up to 9/10); `.kicad_sym` and `.pretty` names must pair; library naming `<Type>_<SubCategory>_<Manufacturer>`.
- Safety: **no write without a preview first**; writes to KiCad files and the repo must be atomic or backed up; git commits need explicit confirmation (Phase 6).
- Services are Qt-free and return `Issue`/`list[Issue]`; routing is by `Severity`; never import `main_window` from lower modules; `models.py` has no internal imports.
- Conventions: `pathlib.Path` everywhere, `.as_posix()` for table/URI strings, type-annotated signatures, `X | None` unions, snake_case, `_`-prefixed private helpers, one-line docstrings, comments explain intent only, double quotes and f-strings, relative imports inside the package.
- Optional `progress(message, current, total)` callback shape when a function reports progress.
- Tests: pytest, run as `./env/Scripts/python.exe -m pytest tests/<file>.py -x -q` from the repo root; `tests/` and `downloaded_examples/` are in the scanner's `SKIP_DIRS`; tests build `Custom/` copies in `tmp_path`; layering tests must pass for new importer modules.
- GSD workflow enforcement: file-changing work goes through a GSD command; downloaded/extracted vendor files are untrusted (run Python that reads them with `-I`, keep scratch scripts outside the extracted directory).
- Never write the real `Custom/` in Phase 4 (CONTEXT D-22).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, no new packages; every primitive read from source this session.
- Architecture: HIGH, plan/apply split matches ARCHITECTURE.md and was prototyped end to end for the symbol and footprint edits against the real CLI.
- Pitfalls: HIGH for the CLI and Windows behaviours (observed), MEDIUM for KiCad 10 (cited header only).
- Version policy facts: HIGH on 9.0.9; LOW on 10.x (assumption A1).

**Research date:** 2026-10-19
**Valid until:** 2026-11-18 for repo and KiCad 9 facts; re-check the CLI behaviours (exit codes, `-o` rules) whenever the installed KiCad major version changes.
