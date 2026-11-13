# Phase 9: Atomic Rule Check and Scan Detection - Research

**Researched:** 2026-10-26
**Domain:** Qt-free KiCad S-expression rule checking, git-HEAD change detection, safe field-fix writes, PySide6 tree/dialog extension (existing app, stdlib + PySide6 only)
**Confidence:** HIGH for in-repo structure and reuse points (all files read this session); MEDIUM for KiCad derived-symbol load semantics (file layout verified, in-app inheritance behaviour not); MEDIUM for manufacturer spellings (web sources are secondary)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
(Copied from 09-CONTEXT.md `## Implementation Decisions`; D-01 to D-25. Research THESE; do not explore alternatives.)

**Library tree marks and highlights (SCAN-01, SCAN-02)**
- **D-01:** Add **symbol child rows** under symbol library rows in the Symbols tree. Child rows have **no checkbox**, so table selection stays per library and the existing `selected` / footprint-sync logic is untouched. A failing symbol gets the warning icon and amber text (the existing `AMBER` + `SP_MessageBoxWarning` style used for "Missing FP"), and its tooltip lists every broken rule in plain language. The library row's Status shows a count, e.g. `1 of 3 fail`.
- **D-02:** The **changed-since-last-Custom-commit highlight applies to every library in `Custom/`**, not only `Atomic_` ones, so it is useful now and during the migration. Child rows are added only where there is something to show: `Atomic_` libraries (always), and any other `Custom/` library that holds a new or changed item. WurthElektronik and any other submodule source are **never** highlighted or expanded into rows.
- **D-03:** **Separate markers.** Failing: warning icon plus amber. Changed: theme `ACCENT` colour plus the word `New` or `Changed` in the Status column. When a symbol is both, it gets the warning styling and the Status reads e.g. `Changed · 2 rules`, and the tooltip lists both. Use theme tokens only, with no new hard-coded colours.
- **D-04:** The **footprint tree gets the changed highlight too**: a `Custom/` footprint library that holds a `.kicad_mod` added or changed since the `Custom` commit gets child rows for those footprints, marked `New`/`Changed` like symbols. Footprints are not judged by the atomic rules themselves. A footprint problem (missing, or its model missing) is reported on the symbol that links it.
- **D-05:** **Log:** one WARNING line per (symbol, broken rule), e.g. `Atomic_Connector / FFC-0.5-20: no datasheet`, then one summary line, e.g. `Atomic check: 7 of 19 symbols fail (23 problems)`. One INFO line per new or changed symbol or footprint. Messages follow the project's existing `Issue`/`list[str]` message shape and the plain-language rule (no raw field names such as `ki_description`).
- **D-06:** After a scan, **auto-expand only libraries holding a failing or changed item**. Clean libraries stay collapsed. The right-click Expand All / Collapse All keep working.

**Manufacturer table (FLD-02)**
- **D-07:** The canonical Manufacturer value is the **full company name without a corporate suffix**: `Texas Instruments`, `Global Connector Technology`, `Analog Devices`, `u-blox`, `Memsic`, `Abracon`, `RECOM`. Short forms (`TI`, `GCT`, `ADI`, `U-BLOX`, `uBlox`, `RECOM Power`, `Memsic Inc.`) are aliases. Researcher/planner: confirm each company's own spelling (e.g. u-blox's lowercase form) when seeding the table. Reversibility: costly (Phase 13 migration and Phase 10 imports write these strings into every `Custom/` symbol).
- **D-08:** **Acquired brands keep their original name** as printed on the part's datasheet: `Maxim Integrated` and `Linear Technology` stay themselves and are not folded into `Analog Devices`, and `InvenSense` is not folded into `TDK`. The ownership relation may be recorded in the table for Phase 10's keyword generation (FLD-01), but it never changes the Manufacturer field.
- **D-09:** The table is a **Qt-free Python module** (e.g. `kicad_lib_manager/manufacturers.py`, a leaf like `importer/fieldrules.py`) mapping each canonical name to its aliases. The user extends it by adding a line in code. It is the **one** table read by the check now, and by the importer and migration later. `importer/suggest.py`'s `MANUFACTURER_ALIASES` (which maps to short library tokens such as `TI`) is folded into or derived from it, so two lists cannot drift. Phase 10 drops the manufacturer token from library names anyway (LIB-04), so a folding approach that keeps v1.0 suggestion tests green until Phase 10 is acceptable.
- **D-10:** **Folded matching:** compare after casefolding and removing spaces, punctuation and corporate suffixes (Inc., Ltd, GmbH, Corp., Co., AG, LLC, etc., as `suggest._CORPORATE_WORDS` does today). A value whose folded form matches a table entry but is not exactly the canonical string (an alias, a case variant or a suffix variant) is reported and gets the "use canonical spelling" fix.
- **D-11:** A non-empty Manufacturer **not in the table passes** the "Manufacturer present" rule and gets an **INFO-level** note, `not in the manufacturer table`, in the dialog and the log, so the user knows to add it. It is not blocking.

**Check dialog and fixes (SCAN-03)**
- **D-12:** Opened from a **menu item** (e.g. `Check Atomic Parts…` with a shortcut such as Ctrl+Shift+A, free of conflicts with the existing Ctrl+I/G/R/K/Q/Shift+R/F1) **and** by **double-clicking a marked symbol row**, which opens the dialog scrolled to that symbol. The dialog works from the last scan's result, and nothing is re-checked on the GUI thread.
- **D-13:** **Tick, preview, apply.** Each safe fix is a ticked row (e.g. `FFC-0.5-20: Value "FFC20" → "FH12-20S-0.5SH"`) with Select All. `Preview & apply` shows the exact before → after for each file, then writes all ticked fixes with one atomic write plus backup per file (`fsutil.atomic_write_text` / `backup_file`) and triggers a rescan, so the fixed violations are gone from the next scan. Safe fixes are only: Value := MPN (offered only when an MPN is present), `MF`/`MP` (and the other `fieldrules` aliases) → `Manufacturer`/`MPN`, canonical manufacturer spelling, and removing price/stock leftovers.
- **D-14:** **Duplicate alias properties merge.** When a symbol has several Manufacturer (or MPN) properties (e.g. `MF` and `MANUFACTURER`, as two `Custom/` libraries have today), the fix keeps one property named `Manufacturer` (or `MPN`) holding the canonical value and removes the rest, provided the values agree after canonical folding (`GCT` and `Global Connector Technology` count as agreeing). When they name truly different companies, or MPN values differ, no one-click fix is offered. The dialog shows both values and the user picks.
- **D-15:** **3D model fill-in:** the user picks a `.step`/`.wrl` file. It is copied into `Custom/3DModels/` with the same safety checks the importer's separate-model intake applies (name clash, size cap, extension; see `importer/package.py` `open_model_source`). The linked footprint then gets a model line `${CUSTOM_3DMODEL_DIR}/<file>`. If the footprint already has a model line pointing at a missing file, that line is re-pointed rather than a second one added. The footprint write is shown in the same preview and backed up the same way. Datasheet and Description are typed in.
- **D-16:** **KiCad running:** reuse `kicad_process.kicad_running()`. The preview warns that KiCad is running and that a library open in the Symbol Editor must be closed without saving or reloaded, or KiCad may overwrite the fixes. Apply is still allowed. Each file is **re-read just before writing**, and the write is refused if it changed since the preview was built (the same stale-file rule as `importer/applier.py` `install.stale_plan`), so an edit KiCad saved after the scan is never lost.
- **D-17:** **Datasheet validity is one definition used everywhere** (scan rule, dialog input, and later the importer and the commit gate). It must be an `http://`/`https://` URL, a `${VAR}/…` path or an absolute path. It is never fetched. Empty, `~`, or anything else (e.g. `see website`) fails with a plain reason such as `Datasheet is not a link or file path`.
- **D-18:** **Price/stock leftovers are a cleanup finding, not a rule failure.** They are listed in the dialog and the log as leftover price/stock data, and their removal fix is ticked by default. They do not turn the symbol amber, do not count in `N of M fail`, and will not block the Phase 11 commit. ATOM-01's 7 rules stay the only blocking rules. Use `fieldrules.is_volatile` / `GENERIC_VOLATILE` for detection.

**Rule semantics and edge cases (ATOM-01..03)**
- **D-19:** **3D model rule for official KiCad footprints:** expand `${KICAD10_3DMODEL_DIR}` (and the older `KICADn_3DMODEL_DIR` names) to the `3dmodels` folder next to the detected KiCad footprints folder (on this workstation `C:/Program Files/KiCad/10.0/share/kicad/3dmodels`) and check that the file exists. `${CUSTOM_3DMODEL_DIR}` resolves to `Custom/3DModels/` in the repo, as `check_3d_model_paths` does today. If KiCad's model folder cannot be found, the rule **fails** with a plain reason (`Could not check the 3D model: KiCad's 3D model folder was not found`). It stays blocking, and nothing is passed on trust.
- **D-20:** **Footprint rule target:** the Footprint field passes when it names exactly one existing `<Lib>:<FP>` in any footprint library in the repo (Custom, WurthElektronik) or in KiCad's installed footprints, which matches the scan's existing cross-reference scope. It fails when it is empty, has no `Lib:` part, names a library that does not exist or is ambiguous (a nickname collision), or names a footprint absent from that library. Restricting targets to `Atomic_Footprints` is Phase 10's job (LIB-06), not this rule's.
- **D-21:** **"Changed" means content, not formatting.** Compare each symbol's S-expression token stream (and each `.kicad_mod`'s) with the same item in the `Custom` HEAD version of the file (`gitops.head_blob`), ignoring whitespace and line endings. `New` means it is not at HEAD. A renamed symbol shows as `New`. A KiCad re-save that only reformats is not flagged, but a format upgrade that rewrites tokens is.
- **D-22:** **Derived (`extends`) symbols** need their **own MPN**, and their Value must equal that MPN, even when the parent has one. Manufacturer, Datasheet, Description and Footprint may be **inherited** from the parent when the child doesn't override them, which is how KiCad displays variants (the `AP2112K-1.2/1.8/2.5/3.3` pattern). The inherited value is judged by the same rules. Researcher: verify which fields KiCad 10 lets a derived symbol override, and how it stores inherited ones.
- **D-23:** **ATOM-03 scope** is by library nickname prefix `Atomic_` (capital A, per the naming decision), wherever the library lives. Libraries without the prefix are never judged by the atomic rules (only the D-02 highlight applies, and only inside `Custom/`).

**Testing and UAT**
- **D-24:** Automated tests extend the Phase 8 synthetic fixture (`tests/customfixtures.py`) with `Atomic_` libraries now, rather than in Phase 10 as Phase 8 D-02 had planned. They hold passing and deliberately broken symbols (one per rule, a derived symbol without its own MPN, alias manufacturers, `MF`/`MANUFACTURER` duplicates, price leftovers, an official-footprint link) plus git-backed cases for New/Changed. The Phase 8 write-protect guard on the live `Custom/` stays in force.
- **D-25:** **UAT uses a scratch copy of the repo**: a helper (like Phase 8's `KICAD_IMPORT_UAT_DIR` hook) builds a throwaway repo copy with a few `Atomic_` libraries made from the owner's real parts, some passing and some broken on purpose, and the app runs against it. The real `Custom/` is never touched. The live-tree UAT checks only the changed-part highlight.

### Claude's Discretion
- Module and class names, the check's result data shape (it must be Qt-free and reusable by the importer, the commit gate and the migration), and how results attach to `ScanResult` / `SymbolLibrary`.
- How the check runs inside `ScanWorker` (it must stay off the GUI thread) and how git HEAD reads are batched for speed.
- Behaviour when git is missing or `Custom` is not a git checkout: the highlight is skipped with one INFO line, and the atomic check still runs.
- The exact shortcut key, dialog layout, and plain-language wording of each rule reason.
- Whether `.bak` files are ignored by the check (they are not `.kicad_sym` libraries, so the scanner already skips them).

### Deferred Ideas (OUT OF SCOPE)
- Editing the manufacturer table from inside the app ("treat X as an alias of Y"). Rejected for this phase; the table is edited in code.
- Restricting Footprint targets to `Atomic_Footprints` or KiCad stock is Phase 10 (LIB-06) and Phase 13 (migration), not this rule.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ATOM-01 | Every symbol in an `Atomic_` library: each broken rule reported in plain language (MPN, Manufacturer, Footprint resolves to exactly one `<Lib>:<FP>`, Value = MPN, Datasheet, Description, 3D model exists) | `atomic_check.py` pure rule functions over `kicad_files` properties; footprint/model resolution via injected resolver context built by `scan_all` (Architecture Patterns 1, 2) |
| ATOM-02 | Derived symbols judged on own fields, each needs own MPN | `kicad_files.extends_name` / `symbol_unit` give the chain; KiCad 10 writes own copies of all standard properties on derived symbols (verified on 407 official derived symbols), so "own" = `list_properties(child.node)` (Pattern 3) |
| ATOM-03 | Every rule blocking for `Atomic_`; other libraries unchecked | Prefix test on nickname (D-23); `Issue`/`Violation` model separates blocking violations from cleanup findings and INFO notes (D-18, D-11) |
| FLD-02 | One canonical manufacturer table (name + aliases); alias reported and fixable | `kicad_lib_manager/manufacturers.py` leaf; folding as `suggest.manufacturer_token` does; `suggest.MANUFACTURER_ALIASES` derived from it (Pattern 4, Manufacturer Seed table) |
| SCAN-01 | Every scan runs the check; failing symbols marked with tooltip, one log line per failure | Check runs inside `scan_all` (already inside `ScanWorker`); child rows in `LibraryTableWidget._populate_trees`; `Issue` list routed by `_log_issues` (Patterns 5, 6) |
| SCAN-02 | Symbols added/changed since last `Custom` commit highlighted | One `git status` + `head_blob` only for changed files; token-stream compare (Pattern 7) |
| SCAN-03 | Check dialog; one-click safe fixes with preview, backup; fill-in for Datasheet/Description/3D model | Fix specs resolved to span edits at preview time; hash-compare before write; `backup_file` + `atomic_write_text`; `open_model_source` for model intake (Patterns 8, 9) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Extracted from `CLAUDE.md` and `.claude/CLAUDE.md` (project instructions, read this session). Treated as locked.

- Stack: Python 3.10+ (venv on 3.14), PySide6 6.12, stdlib only otherwise; extend the existing app. No new dependency is needed for this phase.
- Windows 11 primary; keep the existing cross-platform branches working.
- KiCad 6+ must load all output; `.kicad_sym` / `.pretty` names must pair under the library naming convention (the Atomic scheme drops 1:1 pairing in Phase 10; this phase does not change naming).
- **Safety: no write without a preview first. Writes to KiCad files and the repo must be atomic or backed up. Git commits need explicit confirmation.** This phase never commits.
- Style: snake_case; module-private helpers prefixed `_`; `pathlib.Path` for all file work; `.as_posix()` for compared/written paths; type-annotated params with defaults last; `X | None` unions; `list[str]`/`Issue` message results rather than exceptions; `except Exception` only at the thread boundary; Qt enums fully qualified; `blockSignals`/`self._updating` around programmatic tree changes; long work only in `QThread`; widgets take `parent=None` and call `super().__init__(parent)`.
- Message severity is decided from `Issue.severity`; keep message phrasing stable where `main_window` inspects substrings (`Warning:`, `removed`, `Failed`, `Could not`, `not found`).
- `models.py` has no internal imports; services never import Qt except `settings.py`; do not import `main_window` from lower modules. Layering tests (`tests/test_layering.py`, `tests/test_importer_layering.py`) enforce this and must be updated for every new module.
- Plain-language UI (memory: no jargon or raw field names such as `ki_fp_filters` in user-facing text). Map `MPN`/`Manufacturer` to the labels KiCad shows; avoid `ki_description`.
- Memory (`library-naming-decision`): `Atomic_<KiCad stem>` prefix, shared `Atomic_Footprints`; strict blocking atomic rule.
- GSD workflow enforcement: file edits only through a GSD command (planning/execution), not ad hoc.
- Do not use emojis in user-facing or doc text.

## Summary

Everything this phase needs already exists as a primitive in the repo. The parse and edit layer (`sexpr.py`, `kicad_files.py`) provides property lookup, span edits for set / rename / remove property, footprint model lookup, model-line insert and retarget, and the `extends` chain. The write layer (`fsutil.py`) provides strict decode, atomic replace with lock retry, and numbered backups. The git layer (`gitops.py`) provides `find_git`, `show_toplevel`, `status_entries` and `head_blob`, with an allow-list that already contains `status` and `cat-file`. `fieldrules.py` has the alias and volatile definitions. The work is therefore composition, not new infrastructure: two new Qt-free leaf modules (`manufacturers.py`, `atomic_check.py`) plus a change-detection helper, new result dataclasses in `models.py`, a scan integration in `library_scanner.scan_all`, child rows in `library_table.py`, and a new dialog.

Three findings matter for the plan. (1) **KiCad 10 writes its own copy of every standard property on every derived symbol** (verified: 403 of 407 derived symbols in four official libraries carry Reference/Value/Footprint/Datasheet/Description/ki_keywords/ki_fp_filters; the other 4 lack only `ki_fp_filters`). So a child's "own fields" are simply its direct properties, and "inheritance" only occurs for a property absent from the child, which a hand-edited or third-party file can produce. The in-app inheritance rule for an absent property is not verified here; the check should resolve it parent-chain-first through `symbol_unit` and treat it as an assumption. (2) **Layering is the main mechanical risk.** `fieldrules.py` lives under `importer/`, the new check is a top-level service the scanner must call, and `suggest.py` must import the new manufacturer table. Both layering tests carry hard-coded ALLOWED maps that must be extended in the same plan as each new module, and `library_scanner` must not be imported back by the check (pass resolution context in as parameters). (3) **The tree has a latent trap:** `_on_sym_item_changed` treats any item whose UserRole data is not a `SymbolLibrary` as a group header, so child rows must carry a different marker and the handler must early-return for them, or the first `setText`/`setIcon` outside `_updating` would run a bogus footprint sync.

**Primary recommendation:** Build a pure `atomic_check.check_symbol(...)` over parsed properties with an injected `AtomicContext` (footprint resolver, model resolver), a `manufacturers.py` leaf that `suggest.MANUFACTURER_ALIASES` derives from, change detection that runs ONE `git status` and reads HEAD blobs only for files git reports as changed, and fixes expressed as semantic specs (file, symbol, kind, params) that are turned into span edits against a fresh read at preview time and verified by SHA-256 immediately before the atomic write.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Atomic rule evaluation (7 rules) | Qt-free service (`atomic_check.py`) | — | Must be reused unchanged by Phases 10, 11, 13; no Qt, no git, no scanner import |
| Manufacturer canonical table + folding | Qt-free leaf (`manufacturers.py`) | `importer/suggest.py` derives its token map | Single table (D-09); a leaf like `fieldrules.py` |
| Footprint and 3D-model resolution | Scanner (`library_scanner.py`) builds an `AtomicContext` | `atomic_check.py` consumes it via callables | Scanner already owns fp-lib discovery, KiCad fp dir, Custom model names; check stays pure |
| Changed-since-HEAD detection | Qt-free service (new `changes.py` or inside scanner) | `gitops.py` (only git process owner) | D-21; all git goes through `gitops.run_git` |
| Running check + change detection | `ScanWorker` thread via `scan_all` | — | Never parse or call git on the GUI thread |
| Marking, tooltips, auto-expand, double-click | GUI main thread (`widgets/library_table.py`) | `main_window.py` (log lines, menu, dialog open, rescan) | Widget owns tree layout; window orchestrates |
| Violation list, fix selection, fill-in inputs | GUI dialog (`widgets/atomic_check_dialog.py`) | — | UI only; no rule logic |
| Fix edit generation, stale check, backup, atomic write | Qt-free service (`atomic_fixes.py`) | `fsutil`, `kicad_files`, `sexpr` | Same shape as `importer/applier.py`; testable without Qt; callable from the dialog on demand (short, user-initiated) |
| KiCad-running warning | `kicad_process.kicad_running()` | Dialog shows result | Existing helper (subprocess `tasklist`, 5 s timeout) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`re`, `unicodedata`, `hashlib`, `pathlib`, `dataclasses`, `os`, `shutil`) | 3.14 venv, 3.10+ floor | All check, fold, hash and fix logic | Project constraint: stdlib only [VERIFIED: .claude/CLAUDE.md Constraints; pyproject.toml] |
| PySide6 | 6.12.0 | Tree child rows, dialog | Already the app's GUI [VERIFIED: .claude/CLAUDE.md "PySide6 6.12.0"] |
| pytest | 9.1.1 | Test runner | [VERIFIED: `./env/Scripts/python.exe -m pytest --version` printed `pytest 9.1.1`] |
| pytest-qt (`qtbot`) | installed | Widget/dialog tests | [VERIFIED: `qtbot` used in tests/test_library_table_widget.py and tests/test_main_window.py] |

### Supporting (existing in-repo modules to reuse, not install)
| Module | Purpose | When to Use |
|--------|---------|-------------|
| `kicad_lib_manager/kicad_files.py` | `find_symbols`, `find_property`, `list_properties`, `extends_name`, `symbol_unit`, `find_models`, `set_property_edit`, `rename_property_edit`, `remove_property_edit`, `retarget_model`, `model_insert_edit`, `parse_bytes`, `load` | Every parse and every fix edit |
| `kicad_lib_manager/sexpr.py` | `parse(text, max_nodes=)`, `Edit`, `apply_edits`, `quote`, `unquote` | Token-stream compare (add a helper here) and fix splicing |
| `kicad_lib_manager/fsutil.py` | `read_source`, `decode_source`, `atomic_write_text`, `atomic_write_bytes`, `backup_file`, `default_backup_dir` | D-13 writes |
| `kicad_lib_manager/gitops.py` | `find_git`, `show_toplevel`, `status_entries`, `head_blob` | D-21 |
| `kicad_lib_manager/importer/fieldrules.py` | `MANUFACTURER_FIELDS`, `MPN_FIELDS`, `DESCRIPTION_FIELDS`, `is_volatile`, `is_placeholder`, `is_protected`, `STANDARD_FIELDS` | Alias and leftover definitions |
| `kicad_lib_manager/importer/package.py` | `open_model_source`, `MAX_KICAD_TEXT_BYTES`, `MAX_KICAD_TEXT_NODES`, `Package.close()` | D-15 intake and parse caps |
| `kicad_lib_manager/widgets/theme.py` | `AMBER`, `ACCENT`, `AMBER_TINT`, `SP_*`, `PRIMARY_BUTTON_QSS` | Marks and dialog |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled token-stream compare | Text diff after whitespace normalisation | A text normaliser would mis-handle whitespace inside quoted strings and `\r\n` escapes; a token walk over `sexpr.Node` is exact and already available |
| Per-file `git diff` | `status` once + `cat-file --filters` for changed files only | `diff` is not in `ALLOWED_SUBCOMMANDS`; adding it widens the allow-list for no benefit |

**Installation:** none. This phase installs no external package.

**Version verification:** no new packages. The only third-party packages are PySide6 6.12.0 and pytest 9.1.1, both already installed in `env/` [VERIFIED: .claude/CLAUDE.md; pytest --version].

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | No external package is installed by this phase |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 startup / Rescan / after Apply
            |
            v
   MainWindow._start_scan --> ScanWorker (QThread) --> scan_all(repo_root, kicad_fp_dir)
                                                           |
        +--------------------------------------------------+------------------------+
        |                                                  |                        |
  find_symbol_libs / find_footprint_libs         build AtomicContext          change detection
  (existing; regex footprint refs)               - fp lib index (nickname ->  (Custom only)
        |                                           [rel_paths], lazy stems)   find_git -> show_toplevel(Custom)
        |                                        - KiCad stock fp dir            == Custom ? else INFO "skipped"
        |                                        - KiCad 3dmodels dir            status_entries (ONE call)
        |                                        - Custom/3DModels name set      for each changed .kicad_sym/.kicad_mod:
        |                                              |                            head_blob -> token-stream compare
        |                                              v                            -> New / Changed per symbol/footprint
        |                                  for each lib with nickname "Atomic_*"
        |                                  (and only those): parse (caps) ->
        |                                  atomic_check.check_symbol per top-level symbol
        |                                  (own properties; parent chain only for inherited)
        |                                              |
        +----------------------------+-----------------+
                                     v
              ScanResult: symbol_libs[i].symbols = [SymbolEntry(name, status,
              violations, findings, notes)], footprint_libs[i].changed = [...],
              issues += Issue(WARNING "atomic.<rule>") per (symbol, rule),
              Issue(INFO "scan.changed") per New/Changed, summary Issue
                                     |
                       finished(ScanResult) signal (GUI thread)
                                     v
        MainWindow._on_scan_finished -> _log_issues -> LibraryTableWidget.populate
              child rows (no checkbox), amber/warning or ACCENT, tooltip, auto-expand
                                     |
          double-click child row / menu "Check Atomic Parts..." (Ctrl+Shift+A)
                                     v
        AtomicCheckDialog(scan_result, focus=(lib, symbol))
          tick fixes / Fill in... ---> [Preview & apply]
                                     v
        atomic_fixes.build_preview(specs)  (re-read files, resolve span edits, sha256 each)
          shows before -> after per file, KiCad-running warning
                                     v  user confirms
        atomic_fixes.apply(preview): per file re-read + hash compare (refuse if stale)
          -> backup_file -> atomic_write_text ; on any failure restore earlier files from backups
                                     v
                            emit applied -> MainWindow._start_scan (rescan) ; violations gone
```

### Recommended Project Structure
```
kicad_lib_manager/
├── manufacturers.py       # NEW leaf, stdlib only: Manufacturer table, fold(), lookup()
├── atomic_check.py        # NEW Qt-free: rules, AtomicContext, check_symbol, datasheet_problem()
├── atomic_fixes.py        # NEW Qt-free: FixSpec -> edits, preview, stale check, apply with backup/rollback
├── changes.py             # NEW Qt-free: changed-since-HEAD detection (uses gitops, sexpr)
├── models.py              # EXTEND: SymbolEntry, Violation, Finding, ChangedFootprint; fields on SymbolLibrary/FootprintLibrary/ScanResult (all defaulted)
├── sexpr.py               # EXTEND: token_stream(node) iterative helper
├── library_scanner.py     # EXTEND: scan_all builds context, runs check + changes, emits Issues
├── importer/suggest.py    # EDIT: derive MANUFACTURER_ALIASES from manufacturers.py
└── widgets/
    ├── library_table.py   # EXTEND: child rows, markers, tooltips, auto-expand, double-click signal
    └── atomic_check_dialog.py  # NEW: AtomicCheckDialog
tests/
├── customfixtures.py      # EXTEND: atomic builders + inventory (see Validation Architecture)
├── test_manufacturers.py, test_atomic_check.py, test_atomic_fixes.py, test_scan_changes.py,
│   test_atomic_scan.py, test_library_table_atomic.py, test_atomic_dialog.py   # NEW
└── test_layering.py, test_importer_layering.py   # EDIT: register new modules
```

### Pattern 1: Pure check over parsed properties with injected context
**What:** `check_symbol(symbol_ref, chain, ctx) -> SymbolCheck`. No file IO, no git, no scanner import. `AtomicContext` carries callables: `resolve_footprint(lib, fp) -> FootprintResolution` and `model_status(footprint_path, ) -> list[ModelProblem]`, plus the manufacturer lookup. `library_scanner` constructs the context (it already knows `fp_libs`, `kicad_fp_dir`, and `_custom_model_names`).
**When to use:** always; this is what lets Phase 10's preview, Phase 11's gate and Phase 13's migration reuse the check unchanged (they build a different context: for an incoming part the footprint is not on disk yet).
**Example:**
```python
# Source: composition of kicad_files.py primitives read this session (find_property, list_properties, extends_name)
@dataclass(frozen=True)
class Violation:
    rule: str          # "mpn" | "manufacturer" | "footprint" | "value" | "datasheet" | "description" | "model_3d"
    text: str          # plain language, e.g. "no datasheet"
    fix: "FixSpec | None" = None       # safe one-click fix, else None
    fill: str | None = None            # "datasheet" | "description" | "model" when the dialog can fill it in

def check_symbol(name, props, effective, ctx) -> list[Violation]:
    ...
```

### Pattern 2: Footprint rule via directory listing, never path joining
**What:** Build `{nickname: frozenset(stems)}` lazily with `os.listdir` on each `.pretty` folder, compare exactly (case-sensitive), as `_custom_model_names` already does for models. The Footprint field is untrusted text (from SnapEDA etc.); never build a path from `FP` before it is matched against a listing.
**Resolution outcomes:** `ok(path)`, `no_library`, `ambiguous` (more than one repo library with the nickname, i.e. `collision_peers`), `no_footprint`, `empty`, `no_colon`. Repo libraries first, then KiCad stock (`kicad_fp_dir / f"{lib}.pretty"`).
**3D rule:** for the resolved `.kicad_mod`, `kicad_files.load` it, `footprint_name`, `find_models`. Zero model lines is a failure ("The footprint has no 3D model"). For each model path: `${CUSTOM_3DMODEL_DIR}/x` against the Custom names set (exact case); `${KICAD<n>_3DMODEL_DIR}/x` against `kicad_fp_dir.parent / "3dmodels" / x` with `is_file()`; when the KiCad folder is unknown, fail with the D-19 sentence. Cache the per-footprint model verdict by resolved path, because many symbols share a footprint.

### Pattern 3: Derived symbols
**What:** KiCad 10 stores a full set of its own property copies on a derived symbol. Evaluate the child's own `list_properties(child.node)`. For a field absent from the child, walk `symbol_unit(root, name)` (parent first) and judge the first definition found. MPN is never inherited (ATOM-02): absent own MPN fails even when the parent has one. Value must equal the child's own MPN. If `symbol_unit` returns `None` (missing parent or loop) report one violation "Parent symbol X is missing" and skip the inheritance-dependent rules for that symbol.
**Fix targeting:** a fix edits the property where it physically lives. If a violating inherited value lives in the parent, the fix targets the parent's property and affects every sibling: dedupe edits by `(file, property node start)` before `apply_edits`, because `apply_edits` raises `ValueError` on overlapping edits, and say in the preview that siblings change too.

### Pattern 4: Manufacturer table and folding
**What:** leaf module, stdlib only. Entry = canonical name, aliases, library token (for `suggest`), optional `owner` (D-08, informational only). `fold(text)`: NFKD, drop combining marks, casefold, split on non-alphanumerics, drop `_CORPORATE_WORDS`, join. Build a dict `folded -> entry` at import; a module-level assertion (and a unit test) that no two entries share a folded key. `lookup(value) -> Match(entry, exact: bool) | None`. `exact` is `value == entry.name`. An alias/case/suffix variant (folded hit, not exact) yields the "use canonical spelling" fix.
**Derive, do not duplicate:** `suggest.MANUFACTURER_ALIASES` becomes a comprehension over the table (`fold(alias) -> entry.token`). The existing v1.0 mapping has `maxim`/`maximintegrated`/`linear`/`lineartechnology` -> `ADI` and `invensense` -> `TDK`, so the entry needs a `token` independent of the canonical name (Maxim's canonical stays "Maxim Integrated" per D-08 while its library token stays `ADI`). `suggest.manufacturer_token` keeps its own word-splitting and only swaps the dictionary source. `_CORPORATE_WORDS` should move to `manufacturers.py` and be imported by `suggest.py`.

### Pattern 5: Result model on `ScanResult`
**What:** add defaulted fields so existing constructors and the fakes in `tests/test_main_window.py` (which monkeypatch `scan_all`) keep working: `SymbolLibrary.symbols: list[SymbolEntry] = field(default_factory=list)`, `SymbolLibrary.atomic: bool = False`, `FootprintLibrary.changed: list[ChangedFootprint] = ...`, `ScanResult.atomic_summary`. `SymbolEntry(name, extends, status: None|"new"|"changed", violations, findings, notes)`. `models.py` may not import other package modules, so the dataclasses live there and `atomic_check.py` imports them. `Violation.fix` therefore needs a models-level `FixSpec` dataclass (kind, rel_path, symbol, params dict of plain values).
**Selection preservation:** the child rows must not touch `lib.selected`; `main_window._reapply_selection` keys by `rel_path` and stays unchanged.

### Pattern 6: Tree child rows (library_table.py)
**What:** after creating each symbol library item, add `QTreeWidgetItem` children with `flags` left at default minus `ItemIsUserCheckable` (do not OR the flag in). Store a `SymbolEntry` (not a `SymbolLibrary`) in `UserRole`. Inside `_populate_trees` the `_updating` flag is already set, so `itemChanged` is suppressed during build. **Guard `_on_sym_item_changed`:** add `if item.parent() is not None and item.parent().parent() is not None: return` (or an `isinstance(data, SymbolEntry)` check) before the group-header branch, because the current code treats any non-`SymbolLibrary` item as a group header and would call `_sync_footprint_selection(item.text(0))`.
**`_set_all_check_state`** iterates `group.child(j)` as library items; grandchildren are not visited, so it is safe, but a test must assert `select_all` still checks only library rows.
**Expand:** `group.setExpanded(True)` stays (sources). Library items default collapsed; `setExpanded(True)` only on libraries with failing or changed items (D-06). `reveal()` must also accept a symbol name to expand and scroll to the child (double-click target and dialog focus).
**Signal:** `symbol_activated = Signal(str, str)` (library rel_path, symbol name) from `itemDoubleClicked` only when the item holds a `SymbolEntry`; keep default expand/collapse on library rows.
**Footprint tree:** the same, with `ChangedFootprint` entries, no violations.
**Status text (D-03):** `OK`, `New`, `Changed`, `2 rules`, `Changed · 2 rules`; library row `1 of 3 fail`. Colours: `QBrush(QColor(AMBER))` + `SP_MessageBoxWarning` for failing; `QColor(ACCENT)` for changed. No new hex literals.

### Pattern 7: Changed-since-HEAD detection
**What (batched):**
1. `gitops.find_git(repo_root)`; if `Issue`, emit one INFO ("Change highlight skipped: ...") and continue (the atomic check still runs).
2. `top = gitops.show_toplevel(ctx, custom_dir)`; if `None` or `top.resolve() != custom_dir.resolve()` (Custom not its own checkout, e.g. submodule not initialised so git answers with the parent) skip with the same INFO. `commit_step._custom_unavailable` does the equivalent test [VERIFIED: commit_step.py:127-149 references].
3. `entries = gitops.status_entries(ctx, custom_dir)` ONE call (`status --porcelain=v1 -z --untracked-files=all`). Porcelain v1 paths are relative to the repo top, which here equals Custom, so `Symbols/X.kicad_sym` and `Footprints/L.pretty/F.kicad_mod` are directly the `rel` to pass to `head_blob`. Keep only `.kicad_sym` and `.kicad_mod`; ignore deletions (the file is absent on disk), models, `.gitkeep`, `.bak` (ignored by `Custom/.gitignore` `*.bak`).
4. For each changed `.kicad_sym`: `head_blob(ctx, custom_dir, rel)`; `None` means the whole file is new, so every symbol is `New` without a second read. Otherwise parse the HEAD blob once (`parse_bytes` with the caps), build `{symbol_name: token_stream}`, and compare each current symbol: absent -> `New`, differs -> `Changed`, equal -> not flagged. For each changed `.kicad_mod`: whole-file token stream vs HEAD.
5. Cost is O(changed files) subprocesses; a clean tree costs one `status`.
**Token stream:** add `sexpr.token_stream(node) -> tuple[tuple[str, str], ...]`, an iterative walk emitting `(kind, text)` for strings/atoms plus `("(", "")`/`(")", "")` for list boundaries. Whitespace between tokens and CRLF vs LF are excluded by construction; a string containing an escaped newline is compared by its raw token text (`\n` escape), so it is identical across EOL styles. Do not use Python recursion (the parser avoids it for deep input).
**Detached HEAD:** the Custom submodule is normally detached; `HEAD:` blob reads work regardless.

### Pattern 8: Fixes as semantic specs resolved at preview time
**What:** `FixSpec(kind, rel_path, symbol, params)` with kinds `value_to_mpn`, `rename_alias`, `merge_alias`, `canonical_manufacturer`, `remove_leftover`, `set_datasheet`, `set_description`, `attach_model`. `atomic_fixes.build_preview(repo_root, specs)` re-reads each affected file, re-parses, locates the symbol by name, and produces span `Edit`s using `kicad_files.set_property_edit`, `rename_property_edit`, `remove_property_edit`, `retarget_model`, `model_insert_edit`; the result is `{path: (old_text, new_text, sha256_of_old_bytes)}` for the before -> after display. If a spec no longer applies on the fresh read (already fixed), drop it and say so.
**Apply:** for every file: re-read bytes, compare SHA-256 to the preview's (refuse the whole batch with `atomic.stale_file` before writing anything if any file differs; this is the `install.stale_plan` rule); `backup_file(path, backup_dir)`; `atomic_write_text(path, new_text, bom=src.bom)`. On a failed write, restore every earlier file from its backup bytes with `atomic_write_bytes` and report. Backup dir: `fsutil.default_backup_dir() / "atomic_fixes" / <timestamp or library>` so the table Restore dialog (which scans for `_backup_<N>` pairs of the tables) does not list them.
**EOL/BOM:** new text is produced by splicing into the original text, so line endings and BOM are preserved (`read_source` returns `SourceText.bom`/`eol`); inserted text must go through `fsutil.normalize_eol`.
**Containment:** refuse to write a path that is not under `Custom/` (`Path.resolve().is_relative_to(custom)`, as `applier._preflight` does with `install.path_outside_custom`). An `Atomic_` library found under another source (D-23) is reported and its violations listed, but its fixes are not offered. WurthElektronik and the KiCad install are never written.

### Pattern 9: 3D model fill-in (D-15)
**What:** `package.open_model_source(path, repo_root)` already enforces extension, size cap (`MAX_MEMBER_BYTES`), link/junction refusal, zip hostile-member caps, and returns a `Package` with `PackageFile(name, path, "model", size, sha256, ...)`. Call `package.close()` in a `finally` (zip sources stage to a temp dir). Copy rule: destination `Custom/3DModels/<name>`; if a file of the same name (compare by casefold, as `applier._name_taken` does, because Windows is case-insensitive) exists with the same SHA-256, reuse it without copying; if it exists with different content, refuse with a plain "a different model with this name is already there". Copy through `fsutil.atomic_write_bytes` after verifying the SHA-256 of the bytes read. Then edit the footprint: if `find_models` has a line whose file is missing, `retarget_model` it, else `model_insert_edit`. The model copy is a new file and must appear in the preview list; include it in the rollback (delete the new model if a later write fails).
**Only offer** the model fill-in when the resolved footprint file is inside `Custom/Footprints`.

### Anti-Patterns to Avoid
- **Parsing every symbol library:** only `Atomic_*` libraries get the rule check, and only `Custom/` files get change detection. Parsing WurthElektronik symbols would add to a corpus that already takes about 69.5 s for 6034 files [VERIFIED: STATE.md "08-06: Wurth parse budget ... measured 69.5 s for 6034 files"].
- **`Path.exists()` for model or footprint existence:** it ignores case on Windows. Compare against exact-name listings like `_custom_model_names`.
- **Joining the Footprint field into a path** before matching it to a listing (path traversal via `..` or `/` in untrusted text).
- **Computing edits at scan time and applying them later:** offsets go stale. Store semantic specs; compute edits at preview time; hash-guard at apply time.
- **Applying duplicate edits to a shared parent property** (overlapping edits raise `ValueError`).
- **Re-checking on the GUI thread** (D-12): the dialog reads the scan result; only the fix preview/apply runs in the dialog, and it is bounded, user-initiated file work.
- **Importing `library_scanner` from `atomic_check`:** circular, and breaks reuse by Phases 10/11/13.
- **Raw field names in text** (`ki_description`, `MF`): map to "Description", "Manufacturer" in every user-visible string (alias names appear only inside quoted examples of what is being renamed, e.g. `Rename "MF" to "Manufacturer"`, since the user must recognise the property in KiCad).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| S-expression parsing and span edits | A regex field scraper | `sexpr.parse` + `kicad_files.*_edit` | Handles quoting, escapes, EOL, caps; edits are byte-exact |
| Atomic write with lock retry | `open(...,"w")` | `fsutil.atomic_write_text` | Windows lock/AV retry, read-only detection, BOM |
| Backups | `shutil.copy` | `fsutil.backup_file` | Numbered scheme, exclusive create, no truncated backups |
| Alias / leftover lists | New lists | `importer/fieldrules.py` | One definition (D-18) |
| Git invocation | `subprocess` | `gitops.run_git` helpers | Scrubbed env, allow-list, literal pathspecs, no shell |
| HEAD content incl. autocrlf | `git show` | `gitops.head_blob` (`cat-file --filters`) | Matches work-tree line endings |
| Model intake safety | New zip/size checks | `package.open_model_source` | Hostile-zip, junction, size-cap handling |
| Stale-file detection | mtime compare | SHA-256 of bytes (as `applier._preflight`) | mtime is unreliable on Windows/AV |
| Manufacturer folding | New normaliser | Same algorithm as `suggest.manufacturer_token` moved to `manufacturers.fold` | Keeps v1.0 behaviour and tests |
| KiCad running detection | New process scan | `kicad_process.kicad_running()` | Already tested |

**Key insight:** every hard part (parse, edit, write, backup, git, model intake) exists and is tested in this repo. New code should be rule logic, data shapes, and UI; any new low-level file or git code is a signal to stop and reuse.

## Runtime State Inventory

Not a rename/refactor/migration phase. Omitted per the template. Note for Phase 13 only: Manufacturer strings written by the Phase 9 fixes become the committed canonical spellings (D-07 reversibility is "costly").

## Common Pitfalls

### Pitfall 1: Child rows trigger the selection handler
**What goes wrong:** `_on_sym_item_changed` treats any non-`SymbolLibrary` item as a group header and runs `_sync_footprint_selection(item.text(0))`.
**Why:** the else-branch is the only discrimination [VERIFIED: library_table.py:209-243].
**Avoid:** early return for `SymbolEntry` items; populate under `_updating`; test that toggling a library still syncs footprints and that touching a child row changes nothing.
**Warning signs:** footprint check states change when a child row is expanded or its text updated.

### Pitfall 2: Layering tests fail the moment a module is added
**What goes wrong:** `tests/test_layering.py` ALLOWED is a fixed dict for foundation modules (note `library_scanner` allows only `fsutil, kicad_files, kicad_process, models`); `tests/test_importer_layering.py` fails on any unregistered importer module and on imports outside an entry.
**Avoid:** in the same plan as each module: add `manufacturers: set()`, `atomic_check: {models, fsutil, kicad_files, sexpr, manufacturers, importer}`, `atomic_fixes: {...}`, `changes: {models, gitops, kicad_files, sexpr, fsutil, importer}`, extend `library_scanner` to include `atomic_check`, `changes`, `manufacturers`; extend `importer.suggest` with `manufacturers`; add the new modules to the `_CODE` Qt-free import list. The relative import `from .importer import package` registers as `importer` in `_imports`.
**Decision for the planner:** `atomic_check` needs `fieldrules` and the parse caps from `importer`. Registering `importer` as an allowed target for the top-level services is acceptable because `importer/__init__.py` holds only a docstring (enforced) and `fieldrules` imports nothing; the alternative (moving `fieldrules` up one level) would touch every adapter import and is not worth it.

### Pitfall 3: `apply_edits` overlap
**What goes wrong:** two fixes on the same property (e.g. canonical spelling plus rename plus merge) produce overlapping spans; `apply_edits` raises `ValueError("overlapping or out-of-range edits")`.
**Avoid:** one composed edit plan per symbol: decide the surviving property, then emit exactly one set-value edit, at most one rename edit (name token and value token are disjoint spans), and removals for the others; dedupe shared-parent targets.

### Pitfall 4: Removing a property block and the id gap
**What:** `remove_property_edit` removes the whole block with its leading whitespace; old formats (before 20220914) carry `(id N)` per property. Gaps in ids are tolerated by KiCad. Do not renumber (it would rewrite untouched properties). [ASSUMED: KiCad accepts id gaps; the existing importer already removes properties via the same edit and `kicad-cli` load gating exists in tests.]

### Pitfall 5: MP / MF alias detection scope
**What:** `MPN_FIELDS` contains `MP`, and `MANUFACTURER_FIELDS` contains `MF` and `MANUFACTURER`; these are exact, case-sensitive names. The real `Custom/` also has `Description_1` (SnapEDA) which is NOT a description, and `Mouser Part Number` which is neither MPN nor volatile. Do not fuzzy-match.

### Pitfall 6: Footprint listings on large trees
**What:** KiCad stock has many `.pretty` folders with thousands of files each; listing all of them per scan is wasteful. List lazily only for referenced nicknames and cache per scan.

### Pitfall 7: Windows case-insensitivity on existence checks
**What:** `Path.exists()`/`is_file()` pass a wrong-case model name on NTFS but KiCad on Linux/macOS would fail. For Custom use the exact-name set; for KiCad stock models check the directory listing of the parent for an exact name match (cache listings).

### Pitfall 8: Scan result fakes in tests
`tests/test_main_window.py` monkeypatches `main_window.scan_all` with fakes returning `ScanResult(...)`; new fields must default so these keep working. Also `_on_scan_finished` logic "No warnings." counts any WARNING in `result.issues`; atomic violations will suppress it, which is correct.

### Pitfall 9: Stale dialog after a rescan
After Apply the window rescans and replaces `_scan_result`; an open dialog holding the old result shows ghosts. Close the dialog on successful apply (simplest) or rebuild it from the new result. Also disable the menu action while a scan runs (`_set_scan_running` toggles actions; register the new action there).

### Pitfall 10: `kicad_running()` blocks briefly
It shells out to `tasklist` with a 5 s timeout. It is already called on the GUI thread by `sync_kicad_path_vars`; calling it once when building the preview is consistent. Do not poll it. (Note REV-04, Phase 12, concerns kicad-cli waits, not this call.)

### Pitfall 11: Duplicate alias with differing values (D-14)
No one-click fix, but the dialog must let the user choose a value. Model this as a `Violation.fix = None` plus `choices: tuple[str, ...]`; once the user picks, the dialog produces a `merge_alias` `FixSpec` with `params["value"]`. Without this, the case in D-14 has no path to "fixed".

### Pitfall 12: A value that is only in an alias field
`MP` set, `MPN` absent: decide once whether "MPN present" looks only at the canonical name. See Open Question 1. Whichever is chosen, "Value = MPN" and the Phase 10 import must use the same effective-MPN function (expose `effective_mpn(props)` in `atomic_check`).

## Code Examples

### Token-stream helper (new, in sexpr.py)
```python
# Source: derived from sexpr.Node as read this session (kind "list"|"str"|"atom", children, text)
def token_stream(node: Node) -> tuple[tuple[str, str], ...]:
    """Return the node's tokens in order, list boundaries included and all whitespace excluded."""
    out: list[tuple[str, str]] = []
    stack = [iter([node])]
    while stack:
        child = next(stack[-1], None)
        if child is None:
            stack.pop()
            if stack:          # closing a list (the sentinel level is the first iterator)
                out.append((")", ""))
            continue
        if child.kind == "list":
            out.append(("(", ""))
            stack.append(iter(child.children))
        else:
            out.append((child.kind, child.text))
    return tuple(out)
```
(The close-marker handling needs a test; the planner should specify tests for nested lists, strings containing parentheses, and CRLF vs LF equality.)

### Datasheet validity (D-17), one definition
```python
# Source: D-17 wording; PurePath behaviour is stdlib
import re
from pathlib import PurePosixPath, PureWindowsPath

_URL = re.compile(r"https?://\S+", re.I)
_VAR_PATH = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*\}[/\\]\S")

def datasheet_problem(value: str) -> str | None:
    v = value.strip()
    if not v or v == "~":
        return "no datasheet"
    if _URL.fullmatch(v) or _VAR_PATH.match(v):
        return None
    if PurePosixPath(v).is_absolute() or PureWindowsPath(v).is_absolute():
        return None
    return "Datasheet is not a link or file path"
```

### Property fix edits (existing primitives)
```python
# Source: kicad_files.py lines 240-242, 312-326 (read this session)
edits = [
    kicad_files.set_property_edit(prop, "FH12-20S-0.5SH"),        # Value := MPN
    kicad_files.rename_property_edit(alias_prop, "Manufacturer"),  # MF -> Manufacturer
    kicad_files.remove_property_edit(text, price_prop),            # drop leftover
]
new_text = sexpr.apply_edits(text, edits)
```

### Stale-guard + backup + atomic write
```python
# Source: pattern from library_scanner.sync_kicad_path_vars and applier._preflight (read this session)
data = path.read_bytes()
if hashlib.sha256(data).hexdigest() != preview.sha256:
    return Issue(Severity.ERROR, "atomic.stale_file",
                 f"{path.name} changed after the preview was built; preview again")
backup = fsutil.backup_file(path, backup_dir)
if isinstance(backup, Issue):
    return backup
failure = fsutil.atomic_write_text(path, new_text, bom=src.bom)
```

### Change detection (git, batched)
```python
# Source: gitops.py signatures read this session
ctx = GitContext(found_git_path)
paths = gitops.status_entries(ctx, custom_dir)           # list[str] | Issue
for rel in paths:                                        # relative to Custom top
    if rel.endswith((".kicad_sym", ".kicad_mod")) and (custom_dir / rel).is_file():
        head = gitops.head_blob(ctx, custom_dir, rel)    # bytes | None
```

## Manufacturer Seed Table (D-07)

Spellings found in the live `Custom/` symbols [VERIFIED: grep of Custom/Symbols/*.kicad_sym this session; values quoted verbatim]: `"GCT"`, `"Global Connector Technology"`, `"Memsic Inc."`, `"Texas Instruments"`, `"U-BLOX"`, `"Abracon"`, `"RECOM Power"`, `"TI"`. They sit under property names `MANUFACTURER`, `MF`, and `Manufacturer`.

| Canonical name | Aliases to seed | Library token (v1.0 `suggest`) | Source / confidence |
|----------------|-----------------|--------------------------------|---------------------|
| Texas Instruments | TI, Texas Instruments Inc. | TI | Custom/ data (VERIFIED). Own spelling: [ASSUMED] |
| Global Connector Technology | GCT | GCT | Custom/ data (VERIFIED). Own spelling: [ASSUMED] |
| Analog Devices | ADI, Analog Devices Inc. | ADI | suggest.py table (VERIFIED); own spelling [ASSUMED] |
| Maxim Integrated | Maxim, Maxim Integrated Products | ADI (token only) | D-08 keeps it separate; `owner = "Analog Devices"` informational |
| Linear Technology | Linear, Linear Tech | ADI (token only) | D-08; same note |
| TDK | TDK Corporation (folds to the same key) | TDK | suggest.py (VERIFIED) |
| InvenSense | TDK InvenSense (existing key `tdkinvensense`) | TDK (token only) | D-08; `owner = "TDK"` |
| Murata | Murata Manufacturing, Murata Electronics | Murata | suggest.py has `muratamanufacturing`. Canonical choice between "Murata" and "Murata Manufacturing" is the owner's call (see Open Questions) |
| Memsic | Memsic Inc. | Memsic | Custom/ data (VERIFIED) |
| u-blox | U-BLOX, uBlox, u-blox AG, u-blox Holding AG | uBlox | Lowercase brand: [CITED: https://www.u-blox.com/en/press-releases/u-blox-revamped-new-brand-identity-new-era] and [CITED: https://lkml.iu.edu/hypermail/linux/kernel/2511.1/05144.html] (kernel patch states the company name is written in lowercase); search-result summaries only, MEDIUM |
| Abracon | Abracon LLC | Abracon | Custom/ data (VERIFIED) |
| RECOM | RECOM Power, RECOM Power GmbH | RECOM | D-07 fixes "RECOM". Brand shown as RECOM / RECOM Power by distributors: [CITED: https://uk.farnell.com/b/recom-power] (MEDIUM) |

Folding consequences to test: `fold("U-BLOX") == fold("uBlox") == fold("u-blox") == "ublox"`; `fold("Memsic Inc.") == "memsic"`; `fold("RECOM Power")` is `"recompower"`, so it must be an explicit alias (the corporate-word filter does not remove "power"). `fold("TI")` is `"ti"`; the table must contain no entry whose folded canonical equals another entry's folded alias.

## Derived-Symbol Findings (D-22)

- **What KiCad 10 writes.** Reading `C:/Program Files/KiCad/10.0/share/kicad/symbols/Amplifier_Operational.kicad_sym`, a derived symbol is `(symbol "AD797" (extends "NE5534") (property "Reference" ...) (property "Value" ...) (property "Footprint" "" ...) (property "Datasheet" "https://...") (property "Description" ...) (property "ki_keywords" ...) (property "ki_fp_filters" ...) ...)` [VERIFIED: that file, lines 5-6 and following; `awk` output listed property names `"Reference" "Value" "Footprint" "Datasheet" "Description" "ki_keywords" "ki_fp_filters"` for AD797]. A statistical pass over derived symbols in Amplifier_Operational, Connector_Generic, Device and 74xGxx: 407 derived symbols, 403 with all seven properties, 4 with the same list minus `ki_fp_filters` [VERIFIED: script run this session using `kicad_files.list_properties`]. Conclusion: KiCad writes its own value for every standard field on a derived symbol, so the child's own properties are authoritative in files KiCad saved, and the pin/graphics content is the only inherited part.
- **Overridable fields.** Reference, Value, Footprint, Datasheet, Description and the `ki_*` fields all appear on the child in saved files, so all are overridable in the file format [VERIFIED as above]. Custom fields such as `MPN` and `Manufacturer` appear only if the child declares them: whether KiCad shows a parent's custom field on a child that omits it is [ASSUMED] (training knowledge of the symbol "flatten" step that copies parent fields the child lacks). It does not matter for MPN (ATOM-02 requires an own MPN), and for the other fields the check resolves a missing child field through `symbol_unit` and judges the parent's value, which is what D-22 asks.
- **Footnote on the example:** the AP2112K-1.2/1.8/2.5/3.3 pattern named in D-22 was not located in this session's reading and is not needed for the design.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Symbol property `(id N)` and bare `hide` | no ids; `(hide yes)` | formats 20220914 and 20231120 | Already handled by `kicad_files.new_property_text` / `synth_property_text`; this phase only edits existing properties, so it does not need them |
| `ki_description` | `Description` | format 20230620 | `DESCRIPTION_FIELDS = ("Description", "ki_description")` already covers both; show "Description" in text |
| Manufacturer short tokens in library names (v1.0) | `Atomic_<stem>`, no manufacturer token (v2.0) | Phase 10 | The table keeps tokens only to keep v1.0 `suggest` green until Phase 10 |

**Deprecated/outdated:** the `_MecaFrog` suffix idea in `research/LIBRARY-NAMING.md` is superseded by the `Atomic_` prefix [CITED: 09-CONTEXT.md canonical refs].

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | KiCad's loader copies parent custom fields onto a derived symbol that omits them (flatten behaviour) | Derived-Symbol Findings | Low: the check never relies on it for MPN; for other fields it judges the parent value as D-22 asks |
| A2 | KiCad accepts gaps in property `(id N)` after a property removal | Pitfall 4 | Low: ids only exist in formats before 20220914; load gate via kicad-cli would catch it |
| A3 | Canonical spelling "Texas Instruments", "Global Connector Technology", "Analog Devices" match each company's own usage | Manufacturer Seed Table | Costly (D-07): rewrites committed parts. Confirm with owner before seeding |
| A4 | A repo footprint library sharing a nickname with a KiCad stock library counts as "ambiguous" for the Footprint rule | Pattern 2 | Could flag a legitimate part; D-20 says "a nickname collision" without naming stock |
| A5 | Zero `(model ...)` lines in the linked footprint fails the 3D rule; every model line must resolve | Pattern 2 | Could over- or under-flag footprints with several models |
| A6 | A model path that is absolute, or uses another variable (`${KIPRJMOD}`, `${KISYS3DMOD}`), is checked as an absolute file if absolute, and fails with a plain reason otherwise | Pattern 2 | D-19 only specifies the two named variables |
| A7 | `MPN`/`Manufacturer` "present" judges the canonical property name, with a value under an alias name reported as "stored as MF / MP" and fixable by rename | Pitfall 12 / Open Question 1 | Decides whether alias-only symbols block Phase 11 |
| A8 | The "Murata" canonical spelling | Seed table | Same as A3 |
| A9 | `file:///` URLs are not valid Datasheet values under D-17 | datasheet_problem | Minor: stricter than KiCad accepts |
| A10 | Adding `Atomic_` libraries to `SYNTHETIC_LIBRARIES` could change counts asserted by other tests (not checked) | Validation Architecture | Use a separate `ATOMIC_LIBRARIES` inventory unless a grep proves safety |
| A11 | `Existing test_naming_suggest.py` manufacturer-token cases stay green when `MANUFACTURER_ALIASES` is derived | Pattern 4 | Only the first ~240 lines were skimmed; planner must run the file after the change |

## Open Questions

1. **Does a value stored only under an alias name (`MP`, `MF`) count as "MPN present" / "Manufacturer present"?**
   - Known: the safe fixes rename aliases; Phase 10 will write canonical names; the live `Custom/` has `MF`/`MP` everywhere.
   - Unclear: D-13/D-14 describe the rename as a fix, not whether the unfixed state is a blocking failure.
   - Recommendation: report it as the failure of the MPN/Manufacturer rule with the reason `MPN is stored as "MP", not as "MPN"` and attach the rename fix. This keeps the KiCad chooser columns (which read the canonical names) honest, and Phase 11 then blocks until fixed.
2. **Murata canonical spelling, and whether to seed Würth Elektronik.** Recommendation: ask the owner when planning (one line in the plan's confirmation checkpoint); seed Murata as "Murata Manufacturing" only if confirmed. Würth parts are not imported through Custom today; leave unseeded (unknown names pass with an INFO).
3. **Where a fix lands for an inherited value** (parent shared by variants). Recommendation: edit the parent property and say so in the preview; do not copy the value onto the child.
4. **3D model rule details (A5, A6).** Recommendation: fail on zero models; each model line must resolve; other variables fail with "Could not check the 3D model: uses {var}".
5. **`SYNTHETIC_LIBRARIES` vs a separate inventory (A10).** Recommendation: a separate `ATOMIC_LIBRARIES` + `write_atomic_custom(root)`, so existing counts are untouched; D-24's intent (extend the Phase 8 fixture module) is still met.
6. **Choice UI for D-14 conflicts.** Needs a small choice control in the dialog (radio per candidate value); confirm in the UI phase if one is run (the roadmap marks this phase "UI hint: yes").

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git | SCAN-02 change detection; git-backed tests | yes | 2.49.0.windows.1 (>= `MIN_GIT_VERSION` 2.25) | Highlight skipped with one INFO line (CONTEXT discretion) |
| KiCad 10 3D models folder | D-19 official model check; tests that touch it | yes | `C:/Program Files/KiCad/10.0/share/kicad/3dmodels` (`ls` shows `Battery.3dshapes`, ...) | Rule fails with the D-19 sentence; tests use a fake folder |
| KiCad 10 symbols | Derived-symbol research only | yes | 10.0 (symbol format 20251024) | — |
| pytest + pytest-qt | Validation | yes | pytest 9.1.1 | — |
| `Custom` as its own git checkout | SCAN-02 | yes here | `Custom/.git` is a gitfile into the worktree's modules dir; HEAD `da070aef...` | If not initialised, skip highlight |
| tasklist.exe | `kicad_running()` | yes (Windows) | system | Returns [] on failure |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none on this workstation; the fallbacks above are for other machines.

## Validation Architecture

`workflow.nyquist_validation` is `true` in `.planning/config.json` [VERIFIED: config.json printed this session].

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 with pytest-qt (`qtbot`), offscreen Qt forced in `tests/conftest.py` |
| Config file | `pyproject.toml` (`testpaths = ["tests"]`, `pythonpath = ["."]`, `addopts = "-ra --strict-markers"`, markers `wurth`, `local_kicad`, `kicad_cli`) |
| Quick run command | `.\env\Scripts\python.exe -m pytest tests/test_manufacturers.py tests/test_atomic_check.py tests/test_atomic_fixes.py tests/test_scan_changes.py tests/test_atomic_scan.py tests/test_library_table_atomic.py tests/test_atomic_dialog.py tests/test_layering.py tests/test_importer_layering.py tests/test_naming_suggest.py -q` |
| Full suite command | `.\env\Scripts\python.exe -m pytest` (about 18 min; `-m "not wurth"` about 8 min) [CITED: tests/README.md] |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ATOM-01 | One failing symbol per rule is reported with the plain reason; a passing symbol yields none | unit | `pytest tests/test_atomic_check.py -x -q` | No - Wave 0 |
| ATOM-01 | Footprint outcomes: ok, empty, no colon, unknown library, ambiguous, unknown footprint, wrong case | unit | `pytest tests/test_atomic_check.py -k footprint -q` | No - Wave 0 |
| ATOM-01 | 3D rule: Custom var ok/missing/wrong case; KiCad var ok/missing; KiCad folder unknown fails; zero model lines fails | unit | `pytest tests/test_atomic_check.py -k model -q` | No - Wave 0 |
| ATOM-01 | Datasheet validity table (url, `${VAR}/x`, absolute win/posix, `~`, empty, `see website`) | unit | `pytest tests/test_atomic_check.py -k datasheet -q` | No - Wave 0 |
| ATOM-02 | Derived symbol without own MPN fails even when parent has one; inherited Manufacturer judged; missing parent reported | unit | `pytest tests/test_atomic_check.py -k derived -q` | No - Wave 0 |
| ATOM-03 | Non-`Atomic_` library (incl. Würth-like source) never yields violations; `Atomic_` library outside Custom is judged but fixes not offered | unit/integration | `pytest tests/test_atomic_scan.py -k prefix -q` | No - Wave 0 |
| FLD-02 | Fold cases; alias reported with canonical; unknown passes with INFO; folded keys unique; `suggest.MANUFACTURER_ALIASES` equals derived table | unit | `pytest tests/test_manufacturers.py tests/test_naming_suggest.py -q` | No - Wave 0 (suggest file exists) |
| SCAN-01 | `scan_all` on a synthetic tree emits one WARNING per (symbol, rule) + one summary; entries attached to libs; plain wording (no `ki_`/raw names) | integration | `pytest tests/test_atomic_scan.py -q` | No - Wave 0 |
| SCAN-01 | Tree: child rows have no check flag, failing row amber with warning icon and tooltip lists rules, library Status `1 of 3 fail`, only failing/changed libs expanded, toggling a library still syncs footprints, child edits do not | widget | `pytest tests/test_library_table_atomic.py -q` | No - Wave 0 (existing `tests/test_library_table_widget.py` must stay green) |
| SCAN-02 | git-backed: new symbol, changed symbol, reformat-only not flagged, CRLF-only not flagged, renamed shows New, new library file all New, footprint New/Changed, Würth never marked, no git / Custom not a checkout -> one INFO and atomic check still runs | integration (`requires_git`) | `pytest tests/test_scan_changes.py -q` | No - Wave 0 (uses `tests/gitfixtures.py`) |
| SCAN-02 | `sexpr.token_stream` unit cases | unit | `pytest tests/test_sexpr.py -k token_stream -q` | Extend existing file |
| SCAN-03 | Each safe fix produces the exact expected text (byte-compare, EOL and BOM kept): value:=MPN only with MPN; rename MF/MP; merge duplicates agreeing; disagreeing duplicates give no fix; canonical spelling; leftover removal; shared-parent dedupe | unit | `pytest tests/test_atomic_fixes.py -q` | No - Wave 0 |
| SCAN-03 | Apply: backup exists, atomic write, stale file refused before any write, KiCad-running warning shown, rollback on injected write failure, path outside Custom refused, violations gone after rescan | integration | `pytest tests/test_atomic_fixes.py -k apply -q` | No - Wave 0 |
| SCAN-03 | Fill-in: datasheet/description typed; model copy name clash, same-hash reuse, size cap, bad extension; footprint model line inserted or re-pointed (not duplicated); non-Custom footprint not fillable | integration | `pytest tests/test_atomic_fixes.py -k fill -q` | No - Wave 0 |
| SCAN-03 | Dialog: lists every violation, fix rows ticked, Select All, double-click opens scrolled to symbol, `Preview & apply N fixes` shows before -> after, applied signal triggers rescan, menu action + shortcut exist and are disabled during a scan | widget | `pytest tests/test_atomic_dialog.py tests/test_main_window.py -k atomic -q` | No - Wave 0 |
| (cross) | Layering: new modules registered, Qt-free, import downward only | unit | `pytest tests/test_layering.py tests/test_importer_layering.py -q` | Exists; edit ALLOWED |
| (cross) | Live `Custom/` untouched by the suite | guard | automatic session guard in `tests/conftest.py` | Exists [CITED: tests/README.md] |

### Sampling Rate
- **Per task commit:** the quick run command above (new test files only run when they exist; list only those present at that task).
- **Per wave merge:** `pytest -m "not wurth"` (about 8 min).
- **Phase gate:** full suite green with only the documented skips before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_manufacturers.py` - FLD-02 fold/lookup/uniqueness/derivation
- [ ] `tests/test_atomic_check.py` - ATOM-01..03 rules
- [ ] `tests/test_atomic_fixes.py` - SCAN-03 fixes, apply, rollback, fill-in
- [ ] `tests/test_scan_changes.py` - SCAN-02, git-backed (`requires_git` from `tests/gitfixtures.py`)
- [ ] `tests/test_atomic_scan.py` - SCAN-01 integration over a synthetic tree
- [ ] `tests/test_library_table_atomic.py`, `tests/test_atomic_dialog.py` - GUI (`qtbot`)
- [ ] `tests/customfixtures.py` - add `ATOMIC_LIBRARIES` inventory and `write_atomic_custom(root)` with symbol builders returning bytes (no paths, per Phase 8 D-01/D-02): passing part; one broken part per rule; derived symbol with and without own MPN; `MF`/`MP`/`MANUFACTURER` aliases; duplicate `MF` + `MANUFACTURER` agreeing and disagreeing; `Price`/`Availability`/`Check_prices` leftovers; a link to an official footprint (fake KiCad fp/3dmodels dirs built under `tmp_path`); Custom 3D model present, missing and wrong-case
- [ ] A git-backed Custom populator (new `populate` callable for `make_superproject`) that commits an Atomic baseline, then tests mutate files
- [ ] Update `tests/test_layering.py` and `tests/test_importer_layering.py` ALLOWED maps and the Qt-free import list
- [ ] UAT scratch-repo helper per D-25 (like Phase 8's `KICAD_IMPORT_UAT_DIR`) is a deliverable of the phase, not a test dependency

## Security Domain

`security_enforcement` is enabled in config (ASVS level 1, block on high) [VERIFIED: .planning/config.json].

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | single-user local tool |
| V3 Session Management | no | — |
| V4 Access Control | partial | write containment: refuse any write outside `Custom/`; never write Würth or the KiCad install |
| V5 Input Validation | yes | untrusted KiCad text: 8 MiB / 1,000,000-node caps (`MAX_KICAD_TEXT_BYTES`, `MAX_KICAD_TEXT_NODES`), strict UTF-8 via `decode_source`; Footprint/Datasheet/model fields are untrusted strings |
| V6 Cryptography | no (hashing only) | `hashlib.sha256` for stale-file detection, not a security control |
| V12 Files and Resources | yes | atomic write, backups, no symlink/junction following for model intake (`open_model_source`), name-clash refusal, size cap |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal through the `Lib:FP` Footprint field or a model path (`..`, `/`, drive letters) | Tampering | Match against directory listings (exact names); never join untrusted text into a path before matching; resolve and `is_relative_to` check before any write |
| Oversized or deeply nested `.kicad_sym` / HEAD blob (DoS) | Denial of service | Size cap before parse, `parse(max_nodes=...)`, iterative token walk (no recursion) |
| Hostile model archive or link as the fill-in source | Tampering | `package.open_model_source` (zip caps, link/junction refusal), copy only after SHA-256 check, `Package.close()` |
| Overwriting a file KiCad saved meanwhile | Tampering (lost update) | SHA-256 compare immediately before write; refuse on mismatch (D-16) |
| Partial multi-file write leaving a half-fixed library | Tampering | Backup every file first, restore earlier files on any failure |
| Datasheet field causing a network fetch or file open | Information disclosure | Validate the string only; never fetch or open it (D-17) |
| Git invocation with attacker-controlled repo config | Elevation | Only `gitops.run_git` (no `GIT_*` env, allow-list, literal pathspecs); `find_git` refuses a git inside the repo |

## Sources

### Primary (HIGH confidence)
- In-repo files read this session: `09-CONTEXT.md`, `REQUIREMENTS.md`, `STATE.md`, `.planning/config.json`, `kicad_lib_manager/{kicad_files,sexpr,fsutil,gitops,kicad_process,library_scanner,models}.py`, `widgets/{library_table,theme}.py`, `importer/{fieldrules,suggest (lines 90-270),package (300-430),applier (205-310)}.py`, `main_window.py` (50-185, 340-570), `tests/{customfixtures,gitfixtures,conftest,test_layering,test_importer_layering}.py`, `tests/README.md`, `pyproject.toml`.
- KiCad 10 install `C:/Program Files/KiCad/10.0/share/kicad/symbols/Amplifier_Operational.kicad_sym` and a 407-symbol property census (script run this session).
- Live `Custom/Symbols/*.kicad_sym` property census and Manufacturer value grep (this session).

### Secondary (MEDIUM confidence)
- u-blox lowercase brand: https://www.u-blox.com/en/press-releases/u-blox-revamped-new-brand-identity-new-era and https://lkml.iu.edu/hypermail/linux/kernel/2511.1/05144.html (WebSearch result summaries; pages not opened)
- RECOM brand as shown by distributors: https://uk.farnell.com/b/recom-power (WebSearch result summary)

### Tertiary (LOW confidence)
- KiCad "flatten" inheritance for omitted custom fields (training knowledge, A1)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependencies; all reuse points read in source
- Architecture: HIGH - integration points (scan_all, populate, ScanWorker, layering tests) read directly; MEDIUM on dialog UX details (Claude's discretion)
- Derived-symbol semantics: MEDIUM - file layout verified on 407 symbols; in-app inheritance for omitted fields assumed
- Manufacturer spellings: MEDIUM - live data verified; official spellings from secondary sources; owner confirmation advised (costly to reverse)
- Pitfalls: HIGH for code-derived ones (1, 2, 3, 8, 9); MEDIUM for 4

**Research date:** 2026-10-26
**Valid until:** 30 days (stable internal codebase; re-check only if Phases 10-13 change shared modules first)
