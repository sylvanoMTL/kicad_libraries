# Phase 13: Atomic Migration and KiCad Setup - Research

**Researched:** 2026-11-11
**Domain:** Python/PySide6 desktop tool; transactional file migration inside a git submodule; KiCad 10 library tables and settings JSON
**Confidence:** HIGH for everything read in the repo or measured on the owner's machine; MEDIUM for KiCad-internal behaviour (cited from KiCad's Doxygen mirror, not from the KiCad 10 source tree)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Target libraries and live drift**
- **D-01:** Each part's target library comes from the Phase 10 suggestion, editable per part. The suggestion is `suggest.suggest_library`: own-`Atomic_` sibling lookup, then KiCad stock sibling lookup, then the category map.
  - The preview shows the chosen library and its reason (tooltip, as in Phase 10 D-06). It is changed with the same library picker and name rules as the importer (Phase 10 D-08..D-13).
  - A part with no clear match starts with an empty library, which blocks Run (Phase 10 D-05).
  - Each part is decided on its own, so an old library can be split.
  - The research section 5 table is used only as a test expectation, never as a hard-coded map.
- **D-02:** The uncommitted duplicate CSD85301Q2 is cleaned up by hand before migrating: the owner commits or deletes `Atomic_Transistor_FET.kicad_sym` and `Atomic_Footprints.pretty/DQK0006B.kicad_mod`.
  - There is no special duplicate-handling code. The MIG-01 refusal lists the uncommitted files by name, so the cause is obvious.
  - A name clash in a target library still blocks Run (D-05).
- **D-03:** Parts already in an `Atomic_` library are listed too. They are checked like every other part.
  - If the suggestion differs from their current library, the suggestion is pre-selected and the current library stays one pick away. Example: the crystal CM315D32768DZFT moves from `Atomic_Oscillator` to `Atomic_Crystal`, per the LIBRARY-NAMING section 4 rule "passive crystals: `Crystal`".
  - An `Atomic_` library emptied by such moves is removed, like an emptied v1 library.
- **D-04:** There is no fixed library count. Success means:
  - no v1-named library is left;
  - each part sits in the library the preview showed;
  - the next scan reports zero atomic violations.

  Every `*.bak` in `Custom/Symbols/` is listed in the preview and deleted. Emptied old `.kicad_sym` files and `.pretty/` folders are removed. ROADMAP success criterion 2 and MIG-03 were reworded on 2026-11-11 to drop "9 libraries" and "the two `.bak` files".

**Part and footprint renames**
- **D-05:** Symbol name = sanitised MPN, editable. The MPN is taken from MPN, else SnapEDA `MP`, else Value; the importer's sanitiser is reused. Example: `USB4056-03-A_REVA2` becomes `USB4056-03-A`.
  - Every rename is shown as old -> new.
  - A name clash inside a target library (two parts landing on one name) blocks Run with a plain reason.
  - Renames follow sub-symbols and `extends` (v1.0 INST-02 machinery).

  Reversibility: costly. Symbol names are stored as lib_ids in the owner's KiCad projects, so renaming again later means another relink pass (MIG-05 steps).
- **D-06:** Variant families: the owner types each orderable MPN, and family members become derived symbols.
  - Each existing symbol stays one part. Examples: LTC2954-1-DFN8 / -1-TSOT-23 / -2-DFN8 / -2-TSOT-23, MAX17048G / MAX17048X.
  - Where no real MPN is known (the LTC2954 Values read `ltc2954-1`), the MPN box starts empty and blocks Run until the owner types the orderable number. The symbol is then renamed to it.
  - Members of one family whose graphics and pins are identical become derived (`extends`) symbols of the first, as KiCad's own `Regulator_Linear` does. A derived symbol carries its own MPN, Value, Datasheet, Description and Footprint, and is judged on its own fields (Phase 9).
  - Members whose graphics differ stay standalone. The planner defines "identical" with the token-stream compare (Phase 9 D-21).
- **D-07:** Footprint names are kept, editable (Phase 10 D-20). IPC-style names such as `SON50P200X200X80-9N` stay.
  - A name clash inside `Atomic_Footprints` follows Phase 10 D-19: identical content is reused, and different content gets Overwrite / Rename / Skip, with Rename pre-filled.
  - The footprint's internal name and every Footprint field that links it are rewritten to `Atomic_Footprints:<FP>`.
- **D-08:** An official KiCad footprint is offered per part. The default is "move into `Atomic_Footprints`".
  - "Use an official KiCad footprint" opens the Phase 10 ranked `Lib:FP` picker (`footprint_index.rank_with_pads`), with the amber, non-blocking pad check (Phase 10 D-18).
  - Nothing switches by itself. With an official footprint, KiCad's own 3D model is used (Phase 10 D-17), and KiCad's files are never edited.
  - Research candidates to check against the datasheets: TSOT-23-8 / DFN-8 for LTC2954, LGA-16 for MMC5983MA, DSBGA-8 for BQ25180.
- **D-09:** 3D model files are renamed to `<MPN>.<ext>`, editable (matching the importer's convention). Each rename is shown in the preview, and the model path in the footprint is rewritten to `${CUSTOM_3DMODEL_DIR}/<file>`.
  - A model linked by several footprints keeps the first part's MPN, and every linker is rewritten.
  - A case-only clash keeps the on-disk spelling (Phase 12 D-14).
- **D-10:** Leftovers are deleted, each as a preview row the owner can untick to keep. Leftovers are vendor footprints and models that are no longer linked: after an official-footprint switch, or a footprint no symbol links.
  - A kept footprint goes into `Atomic_Footprints`, and a kept model stays in `3DModels/`.
  - The `pre-atomic` tag keeps everything recoverable.
  - Amended 2026-11-11 (board features): delete-by-default applies only to footprints and models that the migration itself leaves unlinked. A footprint already unlinked before the migration, for example a board feature such as a PCB-trace USB-A plug in `Atomic_Footprints`, still gets a row, but it defaults to **Keep** (moved into `Atomic_Footprints` if it sits in a v1 `.pretty`). See D-21.

**Board features (non-orderable)**
- **D-21:** Board features live only as footprints in `Atomic_Footprints`, used with KiCad's stock symbols. Board features are things that are not orderable parts, such as a PCB-trace USB-A plug, an edge connector, a test pad or a logo.
  - No `Atomic_` symbol is made for them, so the "every part is orderable" rule stays strict.
  - Example: `Atomic_Footprints:USB-A-PCB` used with KiCad's `Connector:USB_A` symbol, assigned in the project.
  - The atomic check judges symbols only, so such a footprint is never flagged. The migration keeps it by default (D-10 amendment).
  - The owner raised this on 2026-11-11 with SparkFun's `USB-A-PCB.kicad_mod` as the example.
- **D-11:** Keywords, footprint description and tags follow the importer rules (Phase 10 D-26..D-30):
  - keywords: the existing words first, then generated words not already present;
  - footprint description: replaced by the generated sentence, with the old one shown in Field changes;
  - tags: merged.

  All are editable in the detail pane with Regenerate. Official KiCad footprints are never written to.
- **D-12:** Old alias fields are removed once their content is copied into the canonical fields. These are SnapEDA `MF`/`MP` and the known price, stock and vendor-URL leftovers.
  - The canonical fields are `MPN`, `Manufacturer` (canonical spelling from `manufacturers.py`, Phase 10 D-23), `Datasheet` and `Description`, and Value = MPN.
  - Each removal is listed in Field changes.

**Migration window and fill-in**
- **D-13:** Entry point: a menu item "Migrate to Atomic Libraries..." (File or Tools menu, planner's choice) opens its own window.
  - It is enabled only while `Custom/` still has a v1-named (non-`Atomic_`) symbol or footprint library or a `.bak` file. Otherwise it is greyed out with a tooltip saying why.
  - The code stays in the app after the migration, kept working by tests.
- **D-14:** Progress is saved as a draft and restored on reopen. The draft holds:
  - library choices;
  - typed MPNs, datasheets and descriptions;
  - keyword and footprint text edits;
  - official-footprint picks;
  - added 3D model sources;
  - untick choices and renames.

  It lives in app data beside `settings.ini` (like `scan_cache/`), never in the repo.
  - A part whose files changed on disk since the draft was saved is marked "changed since the draft" for re-checking.
  - Nothing is written to `Custom/` until Run.
  - A successful Run clears the draft.
- **D-15:** The layout is a part list plus a detail pane.
  - **Left:** a tree grouped by target `Atomic_` library. Each part shows a pass mark or a failure count, and parts that will move show their old library.
  - **Right:** the selected part's detail. It reuses the import preview pieces: library picker, footprint choice (move / official picker), model row with "Add 3D model...", field edit boxes, Field changes, and keyword and footprint-text edits.
  - **Top:** a failure strip lists every remaining atomic-rule failure as a clickable line that selects the part and focuses the field (Phase 10 D-25 style, plain language). Run stays disabled until the strip is empty.
  - **"Files" tab:** every write, rename, move and delete, with the Phase 5 content and diff view.
- **D-16:** The old -> new map is saved in `Custom/MIGRATION-ATOMIC.md`, written by the migration and included in the single `Custom` commit. It holds:
  - the library map, the symbol renames and the footprint link changes;
  - the KiCad relink steps: Edit Symbol Library Links -> Update Symbols from Library -> Update PCB from Schematic.

  The Result view shows the same content, with a Copy button and a link that opens the file.

**KiCad chooser setup and table descriptions**
- **D-17:** "Set Up KiCad Chooser..." is its own menu action. It can be run any time, for example after the importer creates a new `Atomic_` library, and the migration Result view also offers it as a button.
  - It follows the path-variable sync contract: old -> new values shown first, a backup of each config file, an atomic write of only the changed keys, and a refusal from a worktree or a checkout other than the configured `KICAD_LIB_GITHUB`.
  - It uses the KiCad-open Retry / Change anyway / Not now dialog with a re-read and merge into fresh content (Phase 12 D-09..D-11).
  - It writes two files: `kicad_common.json` (`session.pinned_symbol_libs`, `session.pinned_fp_libs`) and `eeschema.json` (`lib_tree.columns`, `lib_tree.column_widths`).
- **D-18:** Pins:
  - `pinned_symbol_libs` gets every `Atomic_` symbol library in the current tables, and `pinned_fp_libs` gets `Atomic_Footprints`.
  - Pins the owner added by hand are kept.
  - `Atomic_` pins whose library no longer exists, such as one emptied by D-03, are removed and shown as old -> new.
- **D-19:** Columns: `MPN` and `Manufacturer` are inserted right after `Description`, and the stray `MANUFACTURER` column is removed. Its width entry moves to `Manufacturer`.
  - The owner's other columns keep their order. Today's list `Item, Description, Capacitance, R, Voltage, Value, MANUFACTURER` becomes `Item, Description, MPN, Manufacturer, Capacitance, R, Voltage, Value`.
  - The action is idempotent: already set up means nothing to write and an INFO line.
- **D-20:** Table descriptions (TBL-01) are generated.
  - `Atomic_<stem>`: "Atomic parts: " + KiCad's own description for that stem, read from the installed KiCad 10 stock `sym-lib-table`. Without it, the stem words with underscores as spaces are used.
  - `Atomic_Footprints`: "Atomic part footprints (own and vendor)".
  - Every other generated entry, Wurth and any remaining v1 name included: `<Source>: <nickname with underscores as spaces>`.
  - A description already present in an existing table entry is kept, not overwritten.
  - This applies to Generate and to the post-install add-only entry alike, since both go through `_format_entry`.

### Claude's Discretion
- **After Run:** the order is rescan, then table regeneration (old managed entries removed, new ones added) through the existing Generate path with its confirmations, then the Phase 11 commit panel offering one `Custom` commit plus the parent ref. The commit gate (GIT-06) must accept a commit that holds deletions and renames. The planner decides whether the tables regenerate automatically after Run or behind a "Generate Tables" button in the Result view, as long as nothing is written to KiCad's config without its confirm.
- **`pre-atomic` tag:** it is created after the MIG-01 clean check and before the first write. It is a local, lightweight or annotated tag, never pushed. If the tag already exists and points at HEAD, it is reused. If it points elsewhere, the migration refuses with a plain reason and the manual command. `gitops.ALLOWED_SUBCOMMANDS` has no `tag` (and no `rm`/`mv`) today, so the planner adds what is needed under the existing allow-list rules.
- **Transaction:** it reuses the importer's applier pattern (`importer/applier.py`: app-data backups, ordered atomic writes, verify, roll back on any `BaseException`, stale-file re-check before each write) or the `atomic_fixes.apply_preview` pattern. Deletes and moves are part of the same rollback.
- **Rule failures with edit boxes:** these reuse `atomic_fixes.complete_fill` / the Check Atomic Parts fill-ins where they fit.
- How migration planning runs off the GUI thread, and how the KiCad stock sibling index and footprint index are shared with the importer.
- Draft file format and its versioning.
- The exact wording of the menu items, strip lines, tooltips, `MIGRATION-ATOMIC.md` and the Result rows: plain language, with no raw field names such as `ki_keywords` or `ki_fp_filters`.
- **DOC-01 content:** `CLAUDE.md` naming section and SnapEDA import steps, PROJECT.md, and `research/LIBRARY-NAMING.md`. The latter gets an update note that `_MecaFrog` became the `Atomic_` prefix and `MecaFrog.pretty` became `Atomic_Footprints.pretty`, and its section 5 table is refreshed to the live parts. The CLAUDE.md GUI Behavior and Menu Shortcuts sections also gain the two new menu actions.
- **Tests:** they use the synthetic `Custom/` (`tests/customfixtures.py`) and throwaway git repos (`tests/gitfixtures.py`). The live-`Custom/` write-protect guard stays in force. The live migration is the owner's UAT run.

### Deferred Ideas (OUT OF SCOPE)
- A general "Reorganise" tool to re-file or rename parts between `Atomic_` libraries at any time. It was considered as the migration entry point and rejected for this phase as a bigger scope. It could be its own phase later.
- An editable per-library description column in the main window. It was rejected in favour of generated descriptions (D-20).
- A "create a part" flow (new symbol and footprint from scratch, not from a vendor package). Today a creation goes through Import Part with a loose-files folder. A board feature is footprint-only (D-21).
- Documenting the board-feature rule (D-21) in `CLAUDE.md` can ride with DOC-01 if the planner sees fit.

(Typographic note: this copy uses ASCII `->` and plain `Wurth`; the CONTEXT.md original is authoritative.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MIG-01 | Tag `Custom` `pre-atomic`; refuse while `Custom` has uncommitted changes | `gitops.status_entries` lists changed and untracked files but never ignored ones, so the three `.bak` files do not trigger the refusal (finding F-09). `tag` must be added to `ALLOWED_SUBCOMMANDS` (F-05). Experiment in a throwaway repo showed create, reuse and refuse-if-elsewhere all work with `rev-parse` plus `git tag`. |
| MIG-02 | Preview of every part: target library, footprint destination, renames, field changes, failures with an edit box; Run disabled until all pass | `suggest_library` results on the live parts (F-12), `atomic_check.AtomicContext` is two callables, so the Run gate can judge the planned end state without touching disk (F-04). `form.atomic_reason` already turns rule failures into plain clickable sentences (F-08). |
| MIG-03 | One transaction with rollback, byte-safe span edits: re-file parts, remove emptied libraries, move or switch footprints, rewrite Footprint fields and model paths, delete `.bak` | `importer/applier.py` has write-only ops and no delete, rmdir or move (F-03); `planner._edit_symbol` is reusable once its private names are promoted (F-03). Mixed symbol format versions 20211014..20251024 need kicad-cli normalisation (F-13). |
| MIG-04 | Zero atomic violations after; tables regenerated (old names out, new in); one `Custom` commit plus parent ref through the commit step | `_merge_table` already drops managed entries whose library is gone, but a rescan leaves new libraries unchecked, so Generate would drop them (pitfall P-01). The commit plan, gate and step need a "deleted" file notion (F-06). |
| MIG-05 | Show and save old -> new library map and the KiCad relink steps | `Custom/MIGRATION-ATOMIC.md` is written inside the transaction and committed with it (D-16); it is a plain text file under `Custom/`, so it passes `_inside` containment. |
| TBL-01 | Generated table entries carry a library description | `_entry_text` writes `(descr "")` today (F-02); stock descriptions exist for all 223 KiCad 10 stems (F-01). |
| TBL-02 | One confirmed action sets up KiCad 10's chooser (pins, MPN and Manufacturer columns, remove MANUFACTURER), old -> new first, backup, worktree and other-checkout refusal | Exact JSON shapes of the owner's files read (F-07); `json.dumps(indent=2, ensure_ascii=False)+"\n"` reproduces all four checked KiCad 10 files byte for byte (F-07), so the same writer as `sync_kicad_path_vars` is safe. The owner's `KICAD_LIB_GITHUB` is currently `C:\Temp`, which makes the refusal fire (pitfall P-12). |
| DOC-01 | `CLAUDE.md`, PROJECT.md and `research/LIBRARY-NAMING.md` describe the `Atomic_` scheme and the atomic rule | Exact sections to edit listed in F-17; no test reads these docs, so add a small docs-consistency test. |
</phase_requirements>

## Summary

This phase adds no new third-party dependency. Everything is stdlib plus PySide6 6.12, built from pieces that already exist: the atomic check (`AtomicContext` is just two callables, so the Run gate can judge a planned end state in memory), the importer's symbol editing (`_edit_symbol`, `_Fields`, `rename_symbol_edits`, footprint name, text and model edits), the app-data backup and rollback machinery of `applier.py`, the Phase 11 commit gate, plan and step, `scan_cache.py` as the template for the draft, and `sync_kicad_path_vars` as the template for the chooser writer. The genuinely new work is (1) a migration planner that composes those pieces over a whole set of parts and several target libraries at once, (2) transaction ops the applier does not have yet (delete, remove-folder, move, and a "deleted" notion in the commit plan and gate), (3) a `tag` subcommand in `gitops`, (4) a chooser/pins writer, (5) table descriptions, (6) the two-pane migration window, and (7) documentation.

Three things in the live data and the code contradict or complicate the CONTEXT and must be decided before planning (details in Open Questions): **`Atomic_Crystal` is not a legal library name** under the Phase 10 name rule (KiCad 10 has no `Crystal` symbol library; `test_categories.py` asserts it); the current suggestion engine **mis-files ICM-42688-P into `Atomic_Timer`** and leaves **10 of 22 parts unplaced**; and the **`.bak` files are git-ignored**, so they must be deleted by the transaction but must never enter the commit file list (the commit precheck refuses ignored paths). Separately, the owner's live `kicad_common.json` has `KICAD_LIB_GITHUB` set to `C:\Temp`, which makes both the existing path-variable sync and the new chooser setup refuse with "other checkout".

**Primary recommendation:** Build the migration as a new Qt-free package `kicad_lib_manager/importer/migration/` (so the existing importer layering guard applies for free) that plans the whole set in memory, gates Run with a custom `AtomicContext` over the planned end state, applies through a new ordered-op transaction that extends the applier's `_Undo`/`_rollback` with delete and rmdir kinds, and hands the result to the unchanged commit step through a `CommitPlan` whose files can be marked `deleted`. Leave `sync_kicad_path_vars` untouched; write `kicad_setup.sync_kicad_chooser` beside it that reuses its helpers and copies its contract.

## Architectural Responsibility Map

This is a single-process desktop app, so the tiers are code layers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Part inventory, target suggestion, rename/field/footprint planning | Qt-free service (`importer/migration/`) | - | Services return `Issue` lists and dataclasses; layering tests keep them Qt-free |
| Run gate (atomic rule on planned end state) | Qt-free service, via `atomic_check.check_symbol` + custom `AtomicContext` | `form.atomic_reason` for plain wording | The check is one function everywhere; never re-implement rules |
| Transaction (write, delete, rmdir, move, rollback) | Qt-free service (`importer/migration/applier.py`) built on `fsutil` and `importer/applier.py` helpers | worker thread | Must be atomic per file and reversible as a set |
| `pre-atomic` tag, clean check, commit | `gitops.py` (only module that starts git) | `importer/commit_*` | GIT-05 choke point and allow-list |
| Chooser setup (pins, columns) | Qt-free service (`kicad_setup.py`) | `main_window` for dialogs and worker | Same split as `sync_kicad_path_vars` (service) and `_confirm_path_var_changes` (dialog) |
| Table descriptions | `table_generator.py` + new leaf `table_descriptions.py` | `main_window` passes the stock mapping | `table_generator` may not import KiCad discovery; inject the describer |
| Draft persistence | Qt-free service (`importer/migration/draft.py`) with path from `settings.py` | - | `scan_cache.py` pattern: plain JSON, atomic write, untrusted on read |
| Migration window | `widgets/migration_dialog.py` | `main_window` (menu, enable state, post-Run hand-off) | Widgets own layout only; long work on `TaskWorker` |
| Docs | Markdown files | `help_dialog.py` User Guide pages | `test_help_dialog.py` pins shortcut and menu lists |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python (stdlib only) | 3.14.4 in `env/` [VERIFIED: `env/Scripts/python.exe --version`] | All services | Project constraint: stdlib only unless clearly justified |
| PySide6 | 6.12.0 [VERIFIED: `tests/test_manifests.py` pins `["PySide6==6.12.0"]`] | Migration window, dialogs, `QThread` workers | Already the only third-party runtime dependency |
| pytest / pytest-qt | 9.1.1 / 4.5.0 [VERIFIED: `requirements-dev.txt`] | Tests | Existing suite |
| git | 2.49.0.windows.1 [VERIFIED: `git --version`] | Tag and commit, through `gitops` only | Existing choke point |
| kicad-cli | 10.0.7 at `C:/Program Files/KiCad/10.0/bin/kicad-cli.exe` [VERIFIED: `kicad-cli.exe version`] | Symbol format normalisation and load gate | The importer already depends on it |

### Supporting (existing in-repo modules to reuse)
| Module | Purpose | When to Use |
|--------|---------|-------------|
| `importer/planner.py` `_edit_symbol`, `_Fields`, `_unit_text`, `_new_source`, `_existing_source` | Field and name span edits, unit cut, version normalisation | Per part; promote the private names to public first (see Don't Hand-Roll) |
| `kicad_files.py` (`rename_symbol_edits`, `footprint_name_edit`, `footprint_value_edits`, `footprint_text_edit`, `retarget_model`, `find_models`, `symbol_unit`, `unit_library_text`, `symbol_insert_edit`, `symbol_insert_before_edit`, `extends_name`) | Lossless span edits | Symbol and footprint rewriting |
| `importer/applier.py` `_Undo`, `_rollback`, `_still_fresh`, `_backup_folder`, `prune_install_backups` | Rollback, stale checks, app-data backups | Base of the migration transaction |
| `atomic_check.py` `check_symbol`, `AtomicContext`, `FootprintTarget`, `repo_context` | The one atomic rule | Run gate |
| `importer/incoming.py` `incoming_issues` | One ERROR `Issue` per broken rule | Feeds `form.atomic_reason` |
| `importer/form.py` `atomic_reason`, `ATOMIC_TARGETS`, `FIELD_LABELS`, `TEXT_LABELS` | Plain-language reasons mapped to controls | Failure strip |
| `importer/suggest.py`, `siblings.py`, `categories.py`, `stems.py`, `footprint_index.py` | Library suggestion, name rule, official footprint ranking | Library column, picker |
| `importer/keywords.py`, `footprint_text.py`, `manufacturers.py`, `naming.py`, `fieldrules.py` | Generated texts, canonical manufacturer, sanitiser, alias and volatile rules | Fields and texts |
| `importer/commit_plan.py`, `commit_gate.py`, `commit_step.py`, `widgets/commit_panel.py` | Commit path | Single `Custom` commit plus parent ref |
| `changes.py` `symbol_changes`, `sexpr.token_stream` | Token-stream compare | "Identical graphics" test, "changed since the draft" |
| `scan_cache.py`, `settings.py` | App-data JSON pattern and path helpers | Draft file |
| `widgets/import_dialog.py` `TaskWorker`, `centre_window`, `fit_window`, `official_candidates`; `preview_tree.py`; `content_view.py`; `conflict_row.py`; `theme.py` | Worker, window sizing, picker data, Files tab, conflict rows | Migration window |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `importer/migration/` package | Top-level `kicad_lib_manager/migration/` | Top-level skips the free importer layering guard (it only discovers `importer/`); a clone of the guard would be needed |
| Calling `build_plan` once per part | Own planner composing helpers | `build_plan` reads its target library from disk, so two parts landing in one new library cannot see each other; it also expects an `ImportCandidate` from a `Package` |
| Refactor `sync_kicad_path_vars` into a generic edit flow | New `sync_kicad_chooser` beside it | Refactoring touches a UAT-tested contract and `test_kicad_config.py` monkeypatches `library_scanner._only_vars_changed` (line 327); copying the contract is safer |
| Regenerate tables inside Run | Behind a button in the Result view | Discretion item; a button keeps "nothing written to KiCad config without confirm" obvious |

**Installation:** none. No new packages. **Version verification:** versions above were read from `requirements-dev.txt`, `tests/test_manifests.py` and the venv this session.

## Package Legitimacy Audit

No external packages are installed or added by this phase (stdlib plus the already-pinned PySide6 6.12.0).

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | - | - | - | - | - | - |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 File > Migrate to Atomic Libraries...          File > Set Up KiCad Chooser...
            |                                              |
   enabled only while Custom has a v1 symbol library,      kicad_running() on worker
   a non-Atomic_Footprints .pretty, or a .bak              |
            |                                         kicad_setup.plan -> old->new lines
            v                                         confirm (Yes/No or Retry/Change anyway/Not now)
   precheck (worker): git status (changed+untracked,      re-read fresh -> backup -> verify -> atomic write
   NOT ignored), busy op, identity, branch                 kicad_common.json (session pins)
            | clean                                       eeschema.json (lib_tree columns, widths)
            v
   inventory (worker): parse every Custom symbol lib, footprint, model;
   KiCad stock sibling + footprint index (shared with importer, cached)
            |
            v
   planner (worker, re-run on every edit, debounced)  <---- draft.json (app data) restores choices
     per part: target library (suggest_library, editable) -> name (sanitised MPN) ->
       fields via _edit_symbol -> footprint (move | official) -> model rename ->
       derived-symbol check (token streams) -> kicad-cli normalise per target library
     whole set: name clashes, footprint conflicts, leftovers, emptied libraries, .bak list
            |
            v
   gate: custom AtomicContext over the planned END STATE + check_symbol per planned symbol
            |  failures -> clickable strip lines (form.atomic_reason) -> detail-pane controls
            v  strip empty -> Run enabled
   Run (worker):
     tag pre-atomic (create | reuse at HEAD | refuse elsewhere)
     preflight (containment, sha256 of every source, names free) -> load gate per target library
     backup every touched/deleted file to app data
     ordered ops: mkdir, write new files, rewrite footprints, move models, delete old files
                  (incl. .bak), rmdir emptied folders, write MIGRATION-ATOMIC.md
     verify (rescan-equivalent check) -> any BaseException: reverse undo list
            |
            v
   Result view: map + relink steps (Copy, open file) | Set Up KiCad Chooser button
            |
            v
   main window: rescan (select ALL Atomic_ libs) -> Generate (confirm) -> path-var confirm
            |
            v
   CommitPanel: CommitPlan(files incl. deleted=True) -> probe (gate) -> run_commit -> parent ref
```

### Recommended Project Structure
```
kicad_lib_manager/
  kicad_setup.py                 # chooser/pins writer (Qt-free), beside library_scanner
  table_descriptions.py          # stock description reader + description rules (Qt-free leaf)
  gitops.py                      # + tag_target, create_tag (ALLOWED_SUBCOMMANDS += "tag")
  importer/
    commit_plan.py               # CommitFile.deleted, CommitPlan.message hook
    commit_gate.py               # skip deleted files
    migration/
      __init__.py                # docstring only (layering test)
      inventory.py               # read Custom: parts, footprints, models, .bak
      plan.py                    # frozen dataclasses: PartChoice, MigrationPlan, MigrationOp
      planner.py                 # build_migration_plan(inventory, choices, tools)
      gate.py                    # AtomicContext over the planned end state
      applier.py                 # ordered ops, delete/rmdir undo, tag, backups
      precheck.py                # MIG-01 clean check + tag decision
      mapfile.py                 # MIGRATION-ATOMIC.md text and the relink steps
      draft.py                   # load/save draft JSON, fingerprints
      commitplan.py              # build_migration_commit_plan
  widgets/
    migration_dialog.py          # two panes, strip, Files tab, Result view
tests/
  migrationfixtures.py           # rich v1 Custom (variants, .bak, shared footprint, 2-model footprint)
  test_migration_*.py, test_kicad_setup.py, test_table_descriptions.py, ...
```

### Pattern 1: Judge the planned end state, not the disk
**What:** `AtomicContext` is a dataclass of two callables (`resolve_footprint`, `model_problems`). Build one over the plan: a link resolves if it is a planned footprint (bytes in memory) or an official KiCad footprint; a model exists if it is in the planned model set and not in the delete set.
**When to use:** the Run gate and the failure strip. `repo_context` and `incoming_context` read the live disk, where the old v1 libraries and old model names still exist until the transaction runs, so they would let a stale link pass.
**Example:**
```python
# Source: kicad_lib_manager/atomic_check.py:353-361 (verified this session)
@dataclass(frozen=True)
class AtomicContext:
    resolve_footprint: Callable[[str], FootprintTarget]
    model_problems: Callable[[FootprintTarget], list[str]]
# FootprintTarget(text, library, footprint, path, rel_path, problem)  (atomic_check.py:338-350)
# check_symbol(root, name, *, rel_path, fixable, ctx) -> SymbolEntry  (atomic_check.py:586)
```
Run `check_symbol(planned_root, name, rel_path=..., fixable=False, ctx=ctx)` for every planned symbol, convert each violation to `Issue(Severity.ERROR, f"install.atomic.{rule}", text)` (what `incoming_issues` does) and pass it to `form.atomic_reason`.

### Pattern 2: Ordered ops with a typed undo list
**What:** Extend the applier's undo entry (`_Undo(kind, restore, written, pre_image)`) with `"rmdir"` (undo = `mkdir`) and treat a delete as a `"file"` undo whose pre-image is restored. `_rollback` walks the list in reverse, so a folder removed last is recreated first, then its files come back.
**When to use:** delete old `.kicad_sym`, `.kicad_mod`, models and `.bak`; remove emptied `.pretty` folders.

### Pattern 3: Copy the config-write contract, do not refactor it
**What:** `sync_kicad_chooser` calls the same helper sequence as `sync_kicad_path_vars` (find config dir, read, `_path_var_refusal`, running list, confirm loop of at most 3 passes with re-read, verify, `backup_file`, `atomic_write_text`, `_prune_backups`), but its verify step proves only the chooser keys changed.
**Example:** see Code Examples.

### Anti-Patterns to Avoid
- **Calling `build_plan` per part:** it reads the target library from disk, so a batch cannot see its own earlier parts, and it needs a `Package`.
- **Importing private names across modules:** the repo lists this as an anti-pattern (ARCHITECTURE.md). Promote `_edit_symbol`, `_Fields`, `_unit_text`, `_new_source`, `_existing_source` to public names in a first, behaviour-neutral task (existing tests protect it).
- **`shutil.rmtree` on a library folder:** delete the listed files, then `os.rmdir`; if anything unlisted remains, keep the folder and warn.
- **Writing the `.bak` deletions into the commit list:** they are git-ignored (see P-03).
- **Showing raw field names in user text:** use "Keywords", "Footprint description", "Footprint tags" (the `form.TEXT_LABELS`) and `form._plain`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| S-expression edits | String replace or regex on `.kicad_sym`/`.kicad_mod` | `sexpr.Edit`/`apply_edits` plus the `kicad_files` helpers | Lossless, keeps CRLF/LF and every untouched byte (project constraint) |
| Atomic file write, backup, retry on lock | `open(..., "w")` | `fsutil.atomic_write_bytes/text`, `fsutil.backup_file` | Handles read-only, locks (retry window about 1 s), temp file, `os.replace` |
| Atomic rule | New rule code | `atomic_check.check_symbol` | One rule everywhere (scan, importer, commit gate); the module docstring says so |
| Plain-language failure lines | New wording table | `form.atomic_reason`, `form._plain` | Already maps each rule to a control and removes raw `ki_*` names |
| Symbol name and filename sanitising | New regex | `naming.sanitize_name`, `sanitize_filename` | `+` and `/` become `_`; reserved Windows names handled |
| Library name rule and picker data | New checks | `stems.name_verdict`, `suggest.existing_libraries` | LIB-05 semantics |
| Official footprint ranking | New ranking | `official_candidates`, `footprint_index.rank_with_pads` | Phase 10 D-16..D-18 |
| Manufacturer canonical spelling | New table | `manufacturers.canonical` | FLD-02: one table |
| Library table splicing | New table writer | `table_generator._merge_table` with a describer | Keeps external entries byte for byte, drops stale managed entries |
| KiCad config JSON write | Hand-built text | `json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"` then `fsutil.normalize_eol` | Verified byte-identical round trip on four owner files (F-07) |
| Git calls | `subprocess` | `gitops.run_git` | GIT-05 choke point; `tests/test_gitops.py` scans modules |
| Diff and file view | New viewer | `importer/content.py` + `ContentViewDialog` | Bounded, binary-safe |
| Token compare | Custom normaliser | `sexpr.token_stream` (strip the name tokens, see P-09) | Whitespace-insensitive |
| App-data JSON with untrusted read | `pickle` or raw `json.load` | `scan_cache.py` pattern (format key, size cap, type checks) | Hardened pattern from Phase 9 |

**Key insight:** every individual step of this migration already exists as a tested function; the risk is in composing them for a whole set and in the three places where today's code assumes "one part, write only" (applier ops, commit plan and gate, rescan selection state).

## Runtime State Inventory

This phase renames libraries, footprints, symbols and model files, so runtime state outside the repo matters.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | The owner's KiCad projects store symbol lib_ids (`Library:Symbol`) and footprint lib_ids. Nothing in this repo stores them. | None in code; MIG-05 map and relink steps (Edit Symbol Library Links, Update Symbols, Update PCB). The `pre-atomic` tag is the recovery point. |
| Live service config | The owner's `%APPDATA%/kicad/10.0/sym-lib-table` and `fp-lib-table` hold 317 and 111 entries; the grep for `Custom/` returned nothing, so no v1 `Custom/` entry exists in them today (verified by `grep -n "Custom/"`). They hold Wurth entries with `(descr "")` and `(disabled)`, and a nested `(type "Table")` entry pointing at the stock templates. | Data regeneration (Generate) writes `Atomic_*` entries; no v1 entries need removal in the owner's current tables. Tests must still cover removal of stale v1 managed entries. |
| OS-registered state | None found: the app registers no tasks or services. | None. |
| Secrets/env vars | KiCad path variables in `kicad_common.json` `environment.vars`: `KICAD_LIB_GITHUB` is `C:\\Temp`, `CUSTOM_3DMODEL_DIR` is `C:/Git_Repo_Clones/Kicad_Libraries-importer/Custom/3DModels`, `WE_3DMODEL_DIR` points at a different clone (`C:\\Git_Repo_Clones\\Kicad_Libraries\\...`). | Owner must correct `KICAD_LIB_GITHUB` in KiCad Preferences > Configure Paths before the chooser setup or path sync will write (P-12). Not a code change. |
| Build artifacts / installed packages | `__pycache__` only; no installed package carries the library names. The scan cache (`%APPDATA%/KiCadExtLibManager/scan_cache/`) fingerprints the Custom git HEAD, so the commit invalidates it. | None; rescan after Run. |

## Findings for the CONTEXT research questions

### F-01 KiCad 10 stock table location and description format (question 1)
- The stock table is at `C:/Program Files/KiCad/10.0/share/kicad/template/sym-lib-table`, confirmed on disk. It holds 223 `(lib ...)` entries; `fp-lib-table` beside it holds 155. [VERIFIED: parsed with `kicad_files.lib_table` this session]
- The owner's own user table references it directly: `(lib (name "KiCad") (type "Table") (uri "C:/Program Files/KiCad/10.0/share/kicad/template/sym-lib-table") (options "") (descr "KiCad Default Libraries"))` in `%APPDATA%/kicad/10.0/sym-lib-table` line 3. [VERIFIED: `head -3`]
- Entry shape (verbatim first line): `(lib (name "4xxx") (type "KiCad") (uri "${KICAD10_SYMBOL_DIR}/4xxx.kicad_sym") (options "") (descr "4xxx series symbols"))`. All 223 stems on disk have an entry, and none has an empty `descr`. [VERIFIED: set comparison of `symbols/*.kicad_sym` stems against table names: both lists empty]
- Descriptions are free text, may contain parentheses and colons: `Connector => Connector symbols (Examples: Terminal Block, D-SUB, DIN, USB...)`, `Sensor_Motion => Accelerometers, gyroscopic sensors`, `Converter_DCDC_Isolated => Isolated DC to DC converter modules`, `Transistor_FET => FET transistor symbols`, `RF_Module => RF module symbols`, `Oscillator => Oscillator symbols`, `LED => Light Emitting Diode (LED) symbols`, `Power_Management => Power management and distribution ICs`, `Battery_Management => Battery management ICs`, `Sensor_Magnetic => Magnetic field and hall-effect sensors`. [VERIFIED]
- How the code finds KiCad today: `library_scanner.find_kicad_footprint_dir()` returns `C:/Program Files/KiCad/<newest>/share/kicad/footprints` on Windows (lines 370-396), saved in settings and held as `MainWindow._kicad_fp_dir`; `kicad_cli.stock_symbols_dir(kicad_fp_dir)` returns `kicad_fp_dir.parent / "symbols"` (kicad_cli.py:54-59). The template folder is therefore `kicad_fp_dir.parent / "template"`. Reuse that, do not hard-code `C:/Program Files`. [VERIFIED: read both functions]
- Reading cost is negligible (about 30 KB); read once per Generate on the GUI thread or inject the mapping from a worker.

### F-02 Where descriptions plug in (question 6)
- The real name is `_entry_text(name, uri)`, not `_format_entry`: [VERIFIED: table_generator.py:16-20]
  `(lib (name {quote(name)})(type {quote("KiCad")})(uri {quote(uri)})(options {quote("")})(descr {quote("")}))`.
  It has four call sites: `_merge_table` (new-file template and the regenerated block) and `_add_entry` (template for a missing table, and the inserted block). Every other path (`write_tables`, `add_library_entries`) goes through those two.
- `_merge_table` classifies existing entries by `_is_managed` (URI contains `${KICAD_LIB_GITHUB}/`, table_generator.py:12 `_MANAGED_MARKER = f"${{{ENV_VAR}}}/"`). It removes every managed entry and re-emits the selected ones as one block at the first managed position (lines 188-206). Managed entries whose repo path is not in the scan are dropped with WARNING `table.stale_managed`; ones scanned but unselected go to `removed`. So "old names removed, new added" is already how Generate behaves.
- To keep an existing description: build `{tail: entry.descr}` from the managed entries that have a non-empty `descr` (`kicad_files.LibEntry.descr` is the decoded string) and look it up by `lib.rel_path` before generating. The `(disabled)` flag the owner's Wurth entries carry is already dropped with WARNING `table.managed_flags_dropped` today; this is existing behaviour and not part of this phase.
- Implementation shape: `_entry_text(name, uri, descr)`, a `describe: Callable[[str, str], str]` argument threaded through `_merge_table`, `generate_*`, `write_tables` and `add_library_entries`, defaulting to a built-in describer without stock text. `layering` ALLOWED for `table_generator` currently is `{"fsutil","kicad_files","models","sexpr"}`; either add the new leaf `table_descriptions` to that set or keep the describer injected.
- Description rules (D-20), with the source derived from the first path segment of `rel_path` (as `library_scanner._determine_source` does): `Atomic_Footprints` -> "Atomic part footprints (own and vendor)"; `Atomic_<stem>` -> "Atomic parts: " + stock descr for `<stem>` else the stem with underscores as spaces; anything else -> `<Source>: <nickname with underscores as spaces>`.

### F-03 Importer transaction machinery (question 4)
- `FileOp.kind` is `"mkdir" | "model" | "footprint" | "symbol_lib"` and a `FileOp` is always a write (`plan.py:115-123`). `applier._write` handles only mkdir and file writes; `_Undo.kind` is `"file" | "mkdir"` (applier.py:44-50). There is no delete, rmdir or move. [VERIFIED: read]
- What it gives that must be reused: `_preflight` (containment against `plan.layout.custom_dir`, sha256 of every `base_sha256`, "appeared after the preview" check), `_gate` (kicad-cli load gate before any backup), per-file app-data backups in `installs/<stamp>_<library>` with `prune_install_backups` (keeps 10), `_still_fresh` re-check immediately before each write (the stale-file re-check), `expected` map so a second write to one path sees the first write's hash, `_rollback` (reverse order, once-per-path from the earliest pre-image, keeps going past a failed step, reports each leftover), `apply_plan`'s `except BaseException` that rolls back then re-raises interrupts, and `_drop_twin` for case-twin spelling. [VERIFIED: read]
- What must be added for the migration (new module `importer/migration/applier.py` importing these helpers, registered in the layering ALLOWED): op kinds `delete_file` (backup pre-image, `unlink`, undo = restore bytes), `remove_dir` (only when empty, undo = `mkdir`), `move_file` for models or footprints (write new, delete old; see P-08 for case-only), `write_file`. Backups go to a `migrations/<stamp>` folder beside `installs/`. `.bak` files are backed up too (they are untracked, so the app-data backup is their only copy).
- The load gate (`kicad_cli.load_gate`) checks one symbol library plus a batch of footprints per call: run it once per target library and once for the footprints. kicad-cli takes about a second per call; planning with normalisation is on a worker.
- `atomic_fixes.apply_preview` is write-only too (`FileChange` has `old_text/new_text/new_bytes`; `_roll_back` unlinks new files and rewrites originals) and has no delete. It is the pattern for "fill-in edits to files before the migration", not a base for the transaction.
- Live-`Custom/` write-protect guard: it is a test-session guard, not production code. `tests/conftest.py:177 _live_custom_untouched` plus `customfixtures.guard_custom` fail the run when the live `Custom/` digest changes. The production containment check is `path.resolve().is_relative_to(plan.layout.custom_dir.resolve())` in `_preflight` and `atomic_fixes._inside`. The migration tests must build every repo from `tests/customfixtures.py` or `tests/gitfixtures.py`, and the `pre-atomic` tag creation must only ever target a throwaway repo. [VERIFIED: tests/README.md and conftest]

### F-04 Reusing the atomic gate for the Run gate (questions 4 and 7)
- `incoming_context(repo_root, footprints_dir, kicad_fp_dir, planned_footprints=..., planned_models=...)` lists `.pretty` folders on disk, so v1 libraries and old model files still resolve during planning. For a faithful end-state gate build `AtomicContext` directly (Pattern 1). Official footprints resolve through `repo_context(repo_root, [], kicad_fp_dir)` (it takes KiCad's `.pretty` listing and its `3dmodels` folder).
- A footprint can carry several `(model ...)` blocks: `find_models` returns all and `check` reports each model problem; `retarget_model` edits one (see P-07).

### F-05 gitops allow-list and the tag (question 5)
- Verbatim, [VERIFIED: gitops.py:21-24]:
  `ALLOWED_SUBCOMMANDS = frozenset({ "--version", "rev-parse", "symbolic-ref", "status", "merge-base", "rev-list", "log", "ls-tree", "cat-file", "var", "add", "reset", "switch", "commit", "ls-files", "diff-tree", "check-ignore", })`
- `tests/test_gitops.py` pins this set: `assert set(ALLOWED_SUBCOMMANDS) == EXPECTED_ALLOWED` (line 63) and the forbidden list (`push, fetch, pull, ls-remote, remote, config, stash, clean, checkout, restore, rebase, merge, am, cherry-pick, gc, prune, update-ref, worktree, submodule`). Adding `"tag"` means editing `EXPECTED_ALLOWED` in that test deliberately ("widening it is a deliberate, reviewed act", the test's own comment). `tag` is not in the forbidden list. Also add any new module that calls git to `GIT_MODULES` (test line 38) so the forbidden-constant scan covers it.
- Experiment, throwaway repo, git 2.49 [VERIFIED: ran in the scratchpad]: `git tag pre-atomic` creates a lightweight tag at HEAD; `git rev-parse -q --verify "refs/tags/pre-atomic^{commit}"` prints the commit (exit 0) or exits 1 when absent; a second `git tag pre-atomic` fails with `fatal: tag 'pre-atomic' already exists`. So: `tag_target(ctx, repo, name)` via `rev-parse` (already allowed), compare with `head_commit`; create only when absent; refuse with the manual command (`git -C Custom tag -f ...` is NOT to be suggested; suggest `git -C Custom tag pre-atomic-2 <commit>` or a deliberate decision text) when it points elsewhere. Use the constant tag name only (no user text in argv). The tag lives in the Custom repo (submodule git dir); it is never pushed (no `push` allowed).

### F-06 Commit gate, plan and step with deletions and renames (question 5)
Facts [VERIFIED: read]:
- `CommitFile` is `rel, display, path, kind, expected_sha256: str, base_sha256, note, installed` (commit_plan.py:25-35). `changed_since_install` compares `file_sha256(f.path) != f.expected_sha256` for every file, so a deleted file (hash `None`) reads as "changed after the install" (stale) and blocks the commit.
- `commit_gate.run_gate` loops `cplan.files`, takes every `kind == "symbol_lib"` whose stem is atomic and reads it from the work tree; a read failure appends `"{library}: the library could not be checked ({why})"` to `problems`, which refuses the commit (commit_gate.py:363-371). An emptied `Atomic_Oscillator.kicad_sym` that is deleted and listed as `symbol_lib` therefore refuses the commit (P-04). `_committed_footprints` and `_committed_models` also trust `kind`.
- `commit_step._precheck` re-runs the gate, then `tracked_paths`, then `ignored_paths` for the untracked rels; an ignored path refuses the commit (commit_step.py:536-541).
- Real git, throwaway repo [VERIFIED: experiment]: `git add -N` for the new files, then `git --literal-pathspecs commit --only -m ... --pathspec-from-file=- --pathspec-file-nul` with both deleted tracked paths and new paths commits the deletions, the creations and records `rename Footprints/{Old.pretty => Atomic_Footprints.pretty}/F.kicad_mod (100%)`. `git diff-tree --root --no-commit-id --name-only -r -z HEAD` lists both old and new paths, so `run_commit`'s "committed files equal planned files" check holds when the plan lists both sides. `git status --porcelain=v1 -z --untracked-files=all` showed ` D old` and `?? new` and did not show the ignored `.bak`.
- Needed changes: `CommitFile.deleted: bool = False` (with `expected_sha256 = ""`), `changed_since_install` and `rebaseline` treat a deleted file as fresh while it is absent; `run_gate`, `_committed_footprints`, `_committed_models`, `linked_custom_files`, `_with_linked_files` skip deleted files; `CommitPlan.message: str | None` (or a `kind` field) so `default_message` returns the migration text; `build_migration_commit_plan` builds the plan from the migration result (files written, files deleted, `MIGRATION-ATOMIC.md`; never `.bak`). `layering` ALLOWED for `importer.commit_plan` is `{"models","importer.plan"}`; the new builder lives in the migration package, which needs `importer.commit_plan` in its own entry.
- The Phase 11 refusal-keeping and Check again logic needs no change.

### F-07 KiCad settings JSON shapes (question 2)
Owner's real files, read-only, this session.
- `%APPDATA%/kicad/10.0/kicad_common.json` top-level keys: `api, appearance, auto_backup, dialog, do_not_show_again, embed_file_defaults, environment, git, graphics, input, meta, netclass_panel, package_manager, session, spacemouse, system`. Verbatim `session`: `{"pinned_design_block_libs": [], "pinned_fp_libs": [], "pinned_symbol_libs": [], "remember_open_files": false}`. All three pin lists are empty arrays in 10.0 and 9.0; in 8.0 and 7.0 `session` has only the fp and symbol lists. So no real sample of a populated entry exists locally.
  - KiCad's `COMMON_SETTINGS::SESSION` has three vector-of-string members `pinned_symbol_libs`, `pinned_fp_libs`, `pinned_design_block_libs` [CITED: https://docs.kicad.org/doxygen/structCOMMON__SETTINGS_1_1SESSION.html]. `PROJECT::PinLibrary` pushes the library argument into the vector only if absent and then calls `cfg->SaveToFile(...)` at once (project.cpp lines 344-352), and `UnpinLibrary` erases by value [CITED: https://docs.kicad.org/doxygen/project_8cpp_source.html]. The stored string is the library nickname [ASSUMED: inferred from the symbol tree adapter treating a library as pinned when its name is in the session or project list; the Doxygen page does not say "nickname" in so many words]. Write plain strings and verify in UAT.
- `%APPDATA%/kicad/10.0/eeschema.json` `lib_tree` verbatim: `"column_widths": {"Capacitance": 98, "Description": 445, "Item": 225, "MANUFACTURER": 339, "R": 110, "Value": 300, "Voltage": 73}`, `"columns": ["Item", "Description", "Capacitance", "R", "Voltage", "Value", "MANUFACTURER"]`, `"open_libs": ["power"]`. The same file has `symbol_chooser` and `lib_view` sections that must not be touched. `pcbnew.json` has its own `lib_tree` (footprint chooser) with `["Item", "Description"]`; D-17 only touches `eeschema.json`. 9.0 holds the same stray column and widths, 8.0 and 7.0 do not.
- Column semantics [CITED: https://docs.kicad.org/doxygen/lib__tree__model__adapter_8cpp_source.html, current KiCad]: `loadColumnConfig()` reads `m_shownColumns = m_cfg.columns` and falls back to `{ "Item", "Description" }` when empty; "Item" is always first (if the first shown column is not "Item" it is inserted at the front); widths are keyed by header name and a width counts only when `IsValidColumnWidth` (greater than 0 and not above a maximum); lookups are exact-key `std::map<wxString, ...>` so `MANUFACTURER` and `Manufacturer` are different columns; an unknown name is created later by `createMissingColumns`; unavailable columns have a null column and are skipped when saving widths. Consequence: removing the `MANUFACTURER` entry from `columns` and `column_widths` is clean, and any `Manufacturer`/`MPN` name must match the symbol field name exactly. A width for `MPN` is optional [ASSUMED: KiCad falls back to a default width; write a modest explicit one, 200 px, and check it in the owner's UAT].
- Byte fidelity: for `kicad_common.json`, `eeschema.json`, `pcbnew.json` and `symbol_editor.json` of KiCad 10.0, `json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n" == text` is `True`, LF endings, no BOM, trailing newline. [VERIFIED: ran this session on the owner's four files]. So whole-file JSON write is minimal-diff; no span editing is needed. Existing code (`library_scanner.py:330`) already does exactly this.
- What KiCad does while running: KiCad saves `kicad_common.json` immediately on pin or unpin (above). When it writes the other settings files is not documented on the KiCad developer settings page [CITED: https://dev-docs.kicad.org/en/components/settings says only that parameters sync "right before saving to disk" and that removed parameters are dropped on next save; nothing about when or about file watching]. It is therefore [ASSUMED] that KiCad holds its settings in memory and rewrites them on save or exit, which is exactly what the shipped message says (`library_scanner.py:342-346`: "KiCad is open (...); it may undo these paths when it exits"). Treat an open KiCad as "the write may be undone", reuse the Retry / Change anyway / Not now dialog.

### F-08 The existing path-variable sync and Phase 12 contract (question 3)
Structure [VERIFIED: library_scanner.py:77-367, main_window.py:1147-1250]:
1. `find_kicad_config_dir(base=None)` returns the newest numeric version folder under `%APPDATA%/kicad` (10.0 beats 9.0); no folder gives a WARNING `config.dir_not_found`; a missing `kicad_common.json` gives `config.not_found`.
2. `_read_config` reads with `fsutil.read_source` (strict UTF-8, BOM and EOL remembered), `json.loads`, tolerates `"vars": null`, and returns ERROR `config.bad_json` or `config.bad_shape` without writing.
3. `_plan_changes(old_vars, desired)` returns `(var, old, new)` triples only for variables that differ; none left means INFO `config.var_ok` lines and no write.
4. `_path_var_refusal(repo_root, repo_str, old_vars)` returns WARNING `config.worktree_refused` when `(repo_root / ".git").is_file()` and `config.other_checkout_refused` when `KICAD_LIB_GITHUB` is set and `_norm_path` differs from the repo root. It runs before the confirm and again after the re-read. It is pure and reusable as is.
5. `names = (running or kicad_running)()` runs once before the confirm; `confirm(changes)` returns `bool | ConfirmAnswer` (`WRITE`, `DECLINE`, `RETRY`); `RETRY` returns INFO `config.retry` and writes nothing.
6. Up to `_PATH_VAR_PASSES = 3` passes: after a `WRITE` the file is re-read and the change list recomputed; an empty list returns, a different list asks again, an unchanged list proceeds; three differing passes give WARNING `config.keeps_changing` and no write.
7. The new content is `json.dumps(new_config, indent=2, ensure_ascii=False) + "\n"`, proven by `_only_vars_changed(config, json.loads(new_text), desired)` (ERROR `config.verify_failed` otherwise), then `fsutil.normalize_eol(new_text, src.eol)`.
8. Backup: `fsutil.backup_file(config_file, backup_root/"kicad_common"/<version>)` (numbered `_backup_N`), then `atomic_write_text(config_file, new_text, bom=src.bom)`, then `_prune_backups(keep=10)`. A KiCad-running WARNING `config.kicad_running` is appended before the backup.
9. In the GUI: `_sync_path_vars` runs `kicad_running` on a `TaskWorker` first (the GUI never waits on `tasklist`), then `_on_path_var_check` calls the sync on the GUI thread with `running=lambda: names` and a confirm that shows the window-modal `QMessageBox` (`_confirm_path_var_changes`, or the three-button box `_kicad_open_box`). `RETRY` restarts the worker. The dialog texts say "KiCad path variables"; the chooser needs its own text and title, so parameterise `_confirm_*` with the subject and keep the defaults byte-stable (tests assert them).
- Contract for `sync_kicad_chooser(repo_root, dest_tables, *, config_base, backup_root, running, confirm)`: compute pins and columns changes for both files from fresh content; one confirm listing old -> new lines for both files; verify both new texts change only their intended keys before writing either; backup each file under `backup_root/"kicad_common"/<ver>` and `backup_root/"eeschema"/<ver>`; write `kicad_common.json` then `eeschema.json`; if the second write fails, restore the first from its in-memory original bytes and report it; use the same refusal (it reads `KICAD_LIB_GITHUB` from `kicad_common.json` even when only `eeschema.json` changes).
- Pins source (D-18): `Atomic_` nicknames in the destination `sym-lib-table` (via `table_info`/`kicad_files.lib_table` entries whose `name` starts with `Atomic_`), plus `Atomic_Footprints` from `fp-lib-table`. Keep hand pins, drop `Atomic_` pins whose nickname is not in the tables.
- Column algorithm (D-19, idempotent): start from `columns`; remove exactly `"MANUFACTURER"` (carry its width to `"Manufacturer"` when `Manufacturer` has no width yet); ensure `"MPN"` then `"Manufacturer"` appear immediately after `"Description"` (after `"Item"` if `Description` is absent); never reorder other entries; never write a width that is not a positive int. Already in that state: no change, INFO line.

### F-09 Clean check and the `.bak` trap (questions 5 and 9)
- `gitops.status_entries(ctx, custom_dir)` runs `status --porcelain=v1 -z --untracked-files=all`, which omits ignored files [VERIFIED: gitops.py:290-311 and the experiment]. `Custom/.gitignore` line 6 is `*.bak` [VERIFIED: `grep -n "^\*.bak" Custom/.gitignore`] and `git ls-files | grep -ci '\.bak'` in Custom printed `0` [VERIFIED]. So the three `.bak` files (`IC_Button_Controller_ADI.bak`, `IC_PowerManagementMosfet_TI.bak`, `IC_Wireless_BLE_uBlox.bak`) are untracked and ignored: they do not block MIG-01, they are not in any commit, and `_precheck` would refuse the commit if a plan listed them (`commit.ignored`). The transaction still deletes them (D-04) and must back them up (app data is their only copy).
- Today the live `Custom/` is not clean: `git status --short` shows `?? Footprints/Atomic_Footprints.pretty/DQK0006B.kicad_mod` and `?? Symbols/Atomic_Transistor_FET.kicad_sym` (D-02). The parent shows ` M Custom` and `?? uv.lock`, which the migration does not touch. HEAD of Custom is on branch `main`; git `core.autocrlf=true`; every live `.kicad_sym` is CRLF.
- Commit-readiness checks to run up front (not only at the end): git new enough, `busy_operation`, `identity_known`, on a named branch or an offerable switch, parent state. These live as `commit_step._custom_unavailable` and `_parent_state`, which take a `CommitPlan`; either build a minimal plan for the pre-check or call the `gitops` primitives directly in `precheck.py`.

### F-10 Reuse map for the window (question 7)
- `ImportDialog` is one 3,600-line class; its library combo, footprint choice, model row and field boxes are methods (`_build_library_section` line 1134, `_build_footprint_section` 1184, `_build_destination_choice` 1214, `_build_fields_section` 1274, `_build_model_row` 1991), not widgets. They cannot be dropped into another window. What is reusable as-is: `TaskWorker` (343-366; signals `result`, `failed`, `progress`; the `_reap` discipline: finished threads are never `deleteLater`'d), `ImportCore` as the test-seam pattern (a frozen dataclass of callables the dialog calls), `official_candidates` (268-289), `centre_window`/`fit_window`/`screen_area` (sizing), `ADD_MODEL_TEXT`, `OFFICIAL_FOOTPRINT_TEXT`, `VENDOR_FOOTPRINT_TEXT`; `widgets/preview_tree.PreviewTree` with `importer/preview.PreviewRow/PreviewSection` (plain dataclasses; build the Files rows yourself, `op_index` is optional); `importer/content.ContentText` and `diff_text` with `widgets/content_view.ContentViewDialog`; `widgets/conflict_row.ConflictRow` driven by an `importer.plan.Conflict` (key, kind, name, existing, suggested_name) and `Resolution`; `widgets/theme.py` tokens (hard-coded colours and px font sizes are banned by `test_help_dialog.py::test_help_css_uses_theme_tokens_only` for the help page and by UI-01 elsewhere); `widgets/commit_panel.CommitPanel`, `widgets/import_result.ElidedLabel`, `_heading`, `_plain_label`.
- `form.py` (Qt-free) holds the reusable rules: `atomic_reason`, `ATOMIC_TARGETS`, `blocking_reasons` pattern, `library_badge`, `FIELD_LABELS`, `TEXT_NAMES`, `TEXT_LABELS`, `Reason(text, target)`.
- Build `widgets/migration_dialog.py` as a new `QDialog` with its own small widgets (a `QTreeWidget` grouped by target library, a detail `QWidget`, a `QTabWidget` with Part and Files, a `QLabel` failure strip with `linkActivated`). Do not try to extract widgets out of `ImportDialog` in this phase.
- Commit glue to copy, not share: `ImportDialog._start_commit_step`, `_start_probe`, `_apply_probe_result`, `_on_check_again`, `_on_recheck_done`, `_on_commit_requested`, `_on_commit_done`, with the generation-event cancel (`_begin_probe_generation`) and the "dialog cannot close while committing" rule. About 250 lines; a small `CommitStepHost` helper inside `migration_dialog.py` is enough, with the debt noted.
- Threading: planning, kicad-cli, the stock sibling index (about 7 s the first time: 21,725 stock symbols), the official footprint index and the git probe all run on `TaskWorker`; the Run transaction on a worker with progress; the GUI thread never blocks (REV-04). `siblings.stock_index` and `footprint_index.build_index` are cached per folder, so the importer and the migration share them when called through the same module functions.
- Main window integration: add `_act_migrate` and `_act_setup_chooser` actions in `_build_menu`, include both in `_set_scan_running` (lines 468-477) so they are disabled during a scan, and add a `_migration_dialog` slot with the same `_close_after_dialog` handling as `_import_dialog` (closeEvent lines 1394-1425). The migrate action is enabled only while the last `ScanResult` shows a Custom symbol library that is not `is_atomic`, a Custom footprint library other than `Atomic_Footprints`, or a `.bak` in `Custom/Symbols` (a `.bak` is not in the scan; list `Custom/Symbols` once per scan finish).
- User Guide: `tests/test_help_dialog.py::test_help_shortcuts_complete` and the outline tests pin the shortcut list and the page/menu order; if a shortcut is added, `HELP_PAGES["shortcuts"]` must list it. Add a "Migrating to Atomic libraries" section to the guide in the same plan as the window (project convention).

### F-11 Draft and "identical graphics" (question 8)
- `settings.scan_cache_file(repo_root)` = `Path(get_settings().fileName()).parent / "scan_cache" / f"{key}.json"` with `key` the first 16 hex of the sha256 of the normcased resolved repo path (settings.py:48-51). Add `migration_draft_file(repo_root)` the same way (`migration_draft/<key>.json`). `scan_cache.save` is the template: payload with `"format"`, repo key, `saved_at`, size cap (`MAX_CACHE_BYTES`), `json.dumps(..., separators)`, `fsutil.atomic_write_text`, a failed save is one WARNING and never raises; `_read_payload` validates every type, returns an `Issue` note, and a bad file means "start without a draft".
- Part identity in the draft: `(source rel_path, original symbol name)`. Store per part the choices plus a fingerprint (sha256 of the symbol block bytes, of the linked footprint file and of the model file, computed at save time). On load recompute; a mismatch marks "changed since the draft" and keeps the user's typed values for re-checking. `changes.py` is not needed for this: its `symbol_changes` compares against git HEAD, not against a draft; use content hashes. A successful Run deletes the draft file.
- "Identical graphics" for D-06: `sexpr.token_stream(node)` returns a whitespace-insensitive token tuple (`sexpr.py:154-173`). Do not compare whole symbol nodes: the sub-symbols are named `<NAME>_0_1`, `<NAME>_1_1`, so streams differ by name. Compare the token streams of the child `(symbol "<name>_<u>_<s>" ...)` nodes with the leading symbol name removed from those string tokens, and exclude `(property ...)` children; require equal pin numbers, names, types and positions. Candidate families: parts in the same target library that share the first `siblings.family_prefixes` step (for example `LTC2954`, `MAX17048`). Render a derived symbol by deleting the parent-style sub-symbol children of the member block and inserting `(extends "<parent>")` after the name token; keep every property. The first member of the family stays standalone, and the file must list the parent before the derived symbol (`_unit_text` / KiCad spike S8 note in planner.py:373-388).

### F-12 Live `Custom/` and what `suggest_library` does with it (question 9)
Read-only inspection and a script run this session. 15 `.kicad_sym` files (13 v1, `Atomic_Oscillator`, and the uncommitted `Atomic_Transistor_FET`), 22 symbols, 18 footprints in 14 `.pretty` folders, 17 model files, 3 `.bak`. Symbol file formats: 20211014 (FFC, MicroSD, Battery_Charger), 20231120 (IMU), 20241209 (USB, Fuel_Gauge, Magnetometer, LED, Oscillator_TCXO, RECOM, Atomic_Oscillator), 20251024 (Button_Controller, PowerManagementMosfet, Wireless_BLE, Atomic_Transistor_FET). All CRLF.

| Part (source library) | Fields found | `suggest_library` today | CONTEXT expectation |
|---|---|---|---|
| CM315D32768DZFT (`Atomic_Oscillator`) | MPN, Value, Manufacturer `CITIZEN FINEDEVICE`, datasheet, description; extra `Height`, `Mouser Part Number` | ask (no stem) | `Atomic_Crystal` (not a legal name, see Open Question 1) |
| CSD85301Q2 (`Atomic_Transistor_FET`, uncommitted) | full; `ki_locked` | `Atomic_Transistor_FET` [own] | same |
| FFC2A32-06-T | MPN, Mfr `Global Connector Technology`, no datasheet, description with raw newlines; SnapEDA leftovers (`MF, MP, Price, Check_prices, ...`) | ask | `Atomic_Connector` |
| MEM2085-00-115-00-A_REV0.2 | MPN `MEM2085-00-115-00-A`, no datasheet | ask | `Atomic_Connector` |
| USB4056-03-A_REVA2, USB4730-GF-A_REVA, USB4745-03-A_REVA | MPN set, no datasheet, no description (`Description_1` leftover) | `Atomic_Connector` [stock, 17 similar] | same |
| BQ25180YBGR | MPN, no datasheet | `Atomic_Battery_Management` [category] | same |
| MAX17048G, MAX17048X | no MPN, no manufacturer, no datasheet | `Atomic_Battery_Management` [category] | same |
| LTC2954-1-DFN8, -1-TSOT-23, -2-DFN8, -2-TSOT-23 | Value `ltc2954-1`/`-2` (shared by two members each), no MPN, no manufacturer | ask (`LTC2` votes split) | `Atomic_Power_Management` |
| ICM-42688-P | no MPN field, Value, Mfr empty, datasheet; Footprint already official `Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y` | **`Atomic_Timer` [stock, 4 of 6 `ICM` siblings]** | `Atomic_Sensor_Motion` |
| MMC5983MA | MPN, Mfr `Memsic Inc.` | `Atomic_Sensor_Magnetic` [stock] | same |
| CSD85301Q2 (`IC_PowerManagementMosfet_TI`) | Mfr `TI`, datasheet, no description | `Atomic_Transistor_FET` [own, from the uncommitted file; stock otherwise] | same |
| NORA-W106-00B, NORA-W106-10B | Value only, Mfr `U-BLOX`, no description; both link footprint `XCVR_NORA-W106-00B` | ask | `Atomic_RF_Module` |
| UHD1110-FKA-CL1A13R3Q1BBQFMF3 (`LED_Cree`) | MPN, Mfr `Cree Inc.`, no description | ask | `Atomic_LED` |
| ATXK-H14 | no MPN, Mfr `Abracon`, datasheet; footprint has no model | `Atomic_Oscillator` [category] | same |
| RS3-1212S_H3 | MPN `RS3-1212S/H3`, Mfr `RECOM Power` | `Atomic_Converter_DCDC_Isolated` [category] | same |

Outcome: 11 of 22 placed as expected, 10 unplaced (blocks Run until the owner picks), 1 mis-filed (ICM-42688-P). The script built a `PartMeta` from the symbol's own fields with an empty vendor category; the real migration's `PartMeta` should do the same (description cleaned with `fieldrules.clean_description`), and results may differ slightly.
- Cause of the ICM result: `siblings.pick` takes the first family-prefix step with any sibling (`ICM`), and `Timer` holds `ICM7555`-type parts: `SiblingPick(stem='Timer', prefix='ICM', counts=(('Timer', 4), ('Sensor_Motion', 2)))` [VERIFIED: ran `pick(stock, "ICM-42688-P")`]. The description "High Precision 6-Axis MEMS MotionTracking Device" matches no category word. Either accept it (the owner edits the library per part, D-01, the table is only a test expectation) or add a words rule (`6 axis`, `motiontracking`, `mems motion`) that outranks a weak stock vote; the second changes Phase 10 behaviour and its tests (`test_suggest_atomic.py`, `test_categories.py`).
- Footprint and model facts the planner must handle:
  - `IC_Wireless_BLE_uBlox.pretty/XCVR_NORA-W106-00B.kicad_mod` has two `(model ...)` blocks: `NORA-W106-00B.step` and `NORA-W106-10B.step`, and both NORA symbols link this one footprint (P-07).
  - `DFN-8_DDB` and `TSOT-23_TS8` are each linked by two LTC2954 symbols; the footprint is moved once.
  - `CSD85301Q2.stp` is linked by two footprints (`DQK0006B`, uncommitted, and `WSON_DLV_6`), the "several footprints" case of D-09.
  - `ATXK-H14.kicad_mod` has no `(model ...)`: model rule fails, owner must add one (known gap).
  - `IC_Battery_Fuel_Gauge_ADI` footprints link `MAX17048G_T10.step` (from `SON50P200X200X80-9N`) and `BGA8N40P2X4_93X167X69N.step` (from the BGA footprint); the model names do not match the symbol names, so the D-09 rename applies (`MAX17048G.step`/`MAX17048X.step` after the MPN is typed).
  - Model renames the preview will show: `MEM2085-00-115-00-A_revA.STEP` -> `MEM2085-00-115-00-A.STEP`, `USB4056-03-A_REVA2.step` -> `USB4056-03-A.step`, `USB4730-GF-A_REVA.step` -> `USB4730-GF-A.step`, `RS3-1212S_H3.stp` -> `RS3-1212S_H3.stp` (the sanitised MPN `RS3-1212S/H3` gives `RS3-1212S_H3`, unchanged). The extension keeps its on-disk case (`sanitize_filename` keeps the listed extension case).
  - No `3DModels` file is unreferenced today.
  - Footprint file stems and internal names already match, so footprint renames are none by default (D-07).
- The `.pretty` folders contain only `.kicad_mod` files today, so every folder can be removed once emptied.

### F-13 Symbol format versions and kicad-cli (new finding)
The 13 v1 libraries span four format versions. The importer's rule (`planner._existing_source`) is: same version merge as is; incoming newer than the target is an ERROR (cannot downgrade); older is upgraded through `kicad-cli sym upgrade` (`upgrade_symbol_text`, memoised, one process per call); a brand-new library goes through the CLI so its header is the installed KiCad's. For a migration that creates mostly new libraries from mixed-version sources, normalise every moved unit through `upgrade_symbol_text` (as `_new_source` does) so each target library has one consistent version; reuse `_existing_source` when a target is an existing file (`Atomic_Oscillator` receiving ATXK-H14, both 20241209). With no kicad-cli the importer merges unchanged with a warning; for the migration treat a missing kicad-cli as a blocking issue (mixed-version content in one library is the failure mode) or at least a strong warning, planner's call. kicad-cli 10.0.7 is present at `C:/Program Files/KiCad/10.0/bin/kicad-cli.exe`.

### F-14 Selection and table regeneration after Run (question 6, MIG-04)
`MainWindow._on_scan_finished` calls `_reapply_selection(previous, result)`, which copies `selected` flags by `rel_path` from the previous result: new libraries start unchecked and vanished ones are dropped with "Dropped N selections for libraries no longer found". `_on_generate` writes only `lib.selected` libraries. After a migration every `Atomic_*` library would therefore be unchecked and Generate would remove all of them from the tables. The post-Run hand-off must set `selected = True` for every Atomic_ symbol library and `Atomic_Footprints` in the new `ScanResult` before `write_tables` (the `_PostInstall`/`_apply_post_install_selection` pattern at main_window.py:813-838 is the model; the migration needs a plural variant). Note also that `table.stale_managed` WARNING lines will appear for removed v1 entries; that is expected output, word the log hint accordingly.

### F-15 Docs to change (DOC-01)
- `CLAUDE.md` (repo root, project instructions): "Library Naming Convention" section currently reads "Format: `<Type>_<SubCategory>_<Manufacturer>`" with v1 examples and "Symbol and footprint folder names must match"; "Importing from SnapEDA" step 2 says "Move the .kicad_mod into the appropriate `<Type>_<SubCategory>_<Manufacturer>.pretty/` folder"; GUI Behavior and Menu Shortcuts need the two new actions. The importer is now the way to import; keep the SnapEDA steps accurate for the manual route (Atomic_Footprints, MPN naming, `${CUSTOM_3DMODEL_DIR}`).
- `.planning/PROJECT.md`: line 101 lists "Own symbol libraries named `Atomic_<official KiCad stem>` ..." as an active (unchecked) requirement and the Key Decisions row at line 143 ends "the migration (Phase 13) remains"; line 142 marks the old naming "Revisit".
- `.planning/research/LIBRARY-NAMING.md`: section 5 still uses `_MecaFrog` and "12 symbol libraries reduced to 9"; add the update note and refresh the table to the live parts (the F-12 table is the source).
- `.claude/CLAUDE.md` is GSD-generated and is not edited by hand.
- `tests/README.md` mentions Phase 13 twice (live health checks skip when `Connector_USB_GCT` is renamed; `customfixtures` header says v1 names "until Phase 13"). Update after the live migration.

## Common Pitfalls

### P-01: New libraries are dropped by Generate after the rescan
**What goes wrong:** after Run the rescan marks every `Atomic_*` library unchecked, so the regenerated tables hold none of them.
**Why:** `_reapply_selection` keeps only previously selected `rel_path`s (F-14).
**How to avoid:** set the new libraries selected before `write_tables`; test it with a main-window test.
**Warning signs:** the log shows "Dropped N selections" and `table.removed` lines naming the new libraries.

### P-02: Gate that judges the disk instead of the plan
**What goes wrong:** Run is enabled while a rewritten link points at a footprint or model the transaction will delete (or the old v1 library still lists it).
**Why:** `incoming_context` lists the live `.pretty` folders and `custom_model_names()` lists the live model files.
**How to avoid:** Pattern 1; add a test where a model is on the delete set but a footprint still links it, expecting a model failure.

### P-03: `.bak` files in the commit list
**What goes wrong:** the commit is refused with "ignored by Custom's .gitignore".
**Why:** `*.bak` is in `Custom/.gitignore`; the three files are untracked and ignored (F-09).
**How to avoid:** delete them in the transaction (backed up in app data) and keep them out of `CommitPlan.files` and out of the Files-to-commit count.

### P-04: Emptied `Atomic_` library breaks the commit gate
**What goes wrong:** deleting `Atomic_Oscillator.kicad_sym` (when its only part moves out) makes the gate report "the library could not be checked".
**Why:** `run_gate` reads every `kind == "symbol_lib"` file of an atomic library from the work tree (commit_gate.py:363-371).
**How to avoid:** `CommitFile.deleted` skipped by the gate (F-06).

### P-05: Deleted files look "changed after the install"
**What goes wrong:** Commit stays gated with "changed after the install ... Check again".
**Why:** `changed_since_install` hashes a missing file as `None`, never equal to `expected_sha256`.
**How to avoid:** a deleted file is fresh while absent; if it reappears it is stale.

### P-06: Moved symbols of mixed format versions in one library
**What goes wrong:** a library file with a 20251024 header holding blocks written in 20211014 syntax may not load in KiCad.
**How to avoid:** F-13; run `kicad_cli.load_gate` per target library before writing; test with a fake runner and with the real kicad-cli (`-m kicad_cli`).

### P-07: One footprint with two models, two parts sharing it, D-09 ambiguity
**What goes wrong:** `NORA-W106-00B` and `NORA-W106-10B` share one footprint holding two model blocks; `retarget_model` rewrites only the first and the importer warns "extra_models".
**How to avoid:** the planner must define the rule. Recommended: rename each model file to the MPN of the first part that links its footprint when it is the only model, and for a multi-model footprint keep every model file's own (already MPN-like) name and rewrite all `(model ...)` paths to `${CUSTOM_3DMODEL_DIR}/<name>`; show each as a row. Flag in Open Question 4.

### P-08: Case-only rename deletes the new file on Windows
**What goes wrong:** write `a.step`, then delete `A.STEP`, and the delete removes the file just written (same file on NTFS).
**How to avoid:** detect `old.casefold() == new.casefold()`; keep the on-disk spelling (Phase 12 D-14) or use a single `os.replace` rename; reuse `applier._drop_twin` reasoning and `_name_taken`. Test on the real case-sensitive folder fixture in `tests/casefixtures.py`.

### P-09: Token-stream compare of whole symbols never matches
**What goes wrong:** family members are never judged identical.
**Why:** sub-symbol names embed the symbol name (`NAME_0_1`).
**How to avoid:** F-11 normalisation; test with two synthetic members that differ only by name and one that differs by a pin.

### P-10: `Atomic_Crystal` and the name rule
**What goes wrong:** typing or defaulting to `Atomic_Crystal` is refused ("is not a library name: after Atomic_ comes a KiCad library name").
**Why:** `stems.name_verdict` allows `Atomic_` plus an allowed stem; KiCad 10 has no `Crystal` library (`ls symbols | grep -i cryst` is empty); `categories.py:40` says "No rule names Crystal: KiCad 10 has no such library" and `test_categories.py:147` asserts `"Crystal" not in targets`. See Open Question 1.

### P-11: Directory removal
**What goes wrong:** `shutil.rmtree` deletes more than planned, or follows a junction.
**How to avoid:** delete listed files first, then `os.rmdir`; refuse symlinks and junctions (`os.path.isjunction`, as `prune_install_backups` does); leave a non-empty folder and warn.

### P-12: The owner's `KICAD_LIB_GITHUB` is `C:\Temp`
**What goes wrong:** both the existing path sync and the new chooser setup refuse ("KICAD_LIB_GITHUB is set to C:\Temp, but this app runs from ...") and the owner thinks the new action is broken.
**How to avoid:** the refusal text is already explicit; add a UAT prerequisite: set `KICAD_LIB_GITHUB` to the repo in KiCad Preferences > Configure Paths first (or clear it). Check the message wording is plain.

### P-13: KiCad open
**What goes wrong:** KiCad rewrites `kicad_common.json` on a pin change or `eeschema.json` on close and undoes the setup; Windows may also hold a library file open and block a delete or rename.
**How to avoid:** `kicad_running()` before Run (warn) and before the config confirm (Retry / Change anyway / Not now); `fsutil.atomic_write_bytes` already retries about 1 s on a lock; delete uses the same retry idea, and a failed delete rolls the whole transaction back.

### P-14: Description or text with markup
**What goes wrong:** vendor strings in a `QLabel` or tooltip render as HTML (open review finding WR-04).
**How to avoid:** `setTextFormat(Qt.TextFormat.PlainText)` or escape, in every new label, tooltip and strip line.

### P-15: Hash-stale draft rows
**What goes wrong:** the owner edits a symbol in KiCad between sessions and the draft silently applies old choices.
**How to avoid:** content-hash fingerprints per part (F-11) and the "changed since the draft" mark.

### P-16: Layering and registration tests
**What goes wrong:** `tests/test_importer_layering.py` fails on every new module not in `ALLOWED`; `test_layering.py` lists top-level modules for the Qt-free import check; `tests/test_gitops.py` pins the subcommand set.
**How to avoid:** register each new module in the same task that creates it.

## Code Examples

### Tag decision (create, reuse, refuse)
```python
# Source: experiment in a throwaway repo, git 2.49 (this session); rev-parse is already allowed
def tag_target(ctx, repo, name="pre-atomic") -> str | None:
    run = run_git(ctx, repo, "rev-parse", "-q", "--verify", f"refs/tags/{name}^{{commit}}")
    return run.stdout.strip() or None if _ok(run) else None

def create_tag(ctx, repo, name="pre-atomic") -> GitRun | Issue:
    return run_git(ctx, repo, "tag", name)          # needs "tag" in ALLOWED_SUBCOMMANDS
# decision: absent -> create_tag; == head_commit -> reuse; else refuse with a plain reason
```

### Config write contract for the chooser (shape only)
```python
# Source: library_scanner.py:305-363 (verified) adapted
new_config = copy.deepcopy(config)
session = new_config.setdefault("session", {})
session["pinned_symbol_libs"] = new_symbol_pins     # list[str], hand pins kept first
session["pinned_fp_libs"] = new_fp_pins
new_text = json.dumps(new_config, indent=2, ensure_ascii=False) + "\n"
assert _only_chooser_keys_changed(config, json.loads(new_text))   # verify before any write
new_text = fsutil.normalize_eol(new_text, src.eol)
backup = fsutil.backup_file(config_file, backup_root / "kicad_common" / config_dir.name)
failure = fsutil.atomic_write_text(config_file, new_text, bom=src.bom)
```

### A deleted commit file (shape)
```python
# Source: commit_plan.py:25-35 (verified) with the proposed field
@dataclass(frozen=True)
class CommitFile:
    rel: str; display: str; path: Path; kind: str
    expected_sha256: str            # "" when deleted
    base_sha256: str | None
    note: str = ""
    installed: bytes | None = None
    deleted: bool = False           # proposed: absent on disk is the expected state
```

### Description rule (shape)
```python
# Source: D-20, F-01
def library_description(kind, nickname, rel_path, stock):   # kind "symbol" | "footprint"
    if nickname == "Atomic_Footprints":
        return "Atomic part footprints (own and vendor)"
    if nickname.startswith("Atomic_"):
        stem = nickname[len("Atomic_"):]
        return "Atomic parts: " + (stock.get(stem) or stem.replace("_", " "))
    return f"{rel_path.split('/')[0]}: {nickname.replace('_', ' ')}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `<Type>_<SubCategory>_<Manufacturer>` libraries, 1:1 `.pretty` pairing | `Atomic_<KiCad stem>` symbol libraries, one `Atomic_Footprints.pretty` | v2.0, owner decision 2026-10-25 | Footprint link is `Atomic_Footprints:<FP>`; migration moves everything |
| `(descr "")` in generated tables | generated descriptions | this phase | KiCad's library list shows text |
| Hand-set chooser columns | one confirmed action | this phase | `MPN` and `Manufacturer` visible, stray column gone |
| KiCad 9 as a target | KiCad 10 reference only | v1.0 close | Config writes touch only the newest version folder (`find_kicad_config_dir`) |

**Deprecated/outdated:** KiCad nested library tables are out of scope (flattened in the chooser); the owner's tables nevertheless reference the stock table as a `(type "Table")` entry, which `_merge_table` keeps as an external entry.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The strings in `session.pinned_symbol_libs` / `pinned_fp_libs` are library nicknames | F-07 | Pins do not show; fix is a one-line change after the UAT check |
| A2 | KiCad holds its settings in memory and rewrites `eeschema.json` on save or exit (so a write while KiCad is open may be undone) | F-07 | If KiCad actually reloads or never overwrites, the warning is merely cautious |
| A3 | A missing `MPN` width entry gets a sensible default in KiCad; write 200 px explicitly | F-07, F-08 | Narrow or zero-width column; owner adjusts in the chooser |
| A4 | A missing kicad-cli should be a blocking issue for the migration | F-13 | If treated as a warning, mixed-format libraries could be written (caught by the load gate only when kicad-cli exists) |
| A5 | Family detection by the first `family_prefixes` step plus identical normalised sub-symbol streams is the right reading of "family" | F-11 | Wrong grouping would derive unrelated parts or miss real families; the owner sees every derive in the preview and can untick |
| A6 | Default MPN rule: MPN, else MP, else Value, but empty when two or more parts of the migration would get the same value (the LTC2954 case) | Open Question 3 | Without it the D-05 default makes `ltc2954-1` the MPN of two parts |
| A7 | New code belongs in `importer/migration/` and registered in the importer layering test | Architecture | Planner may prefer a top-level package; needs its own layering test |
| A8 | Lightweight `git tag` is enough (no annotated tag) | F-05 | An annotated tag needs `-m` and identity; the CONTEXT allows either |

## Open Questions

1. **`Atomic_Crystal` is not a legal library name. Which way?**
   - What we know: D-03 and the CONTEXT table send CM315D32768DZFT to `Atomic_Crystal`; `stems.name_verdict` refuses it; KiCad 10 has no `Crystal` library [VERIFIED: stock `symbols` folder listing]; `categories.py` and `test_categories.py` say crystals are never filed by a guess; LIBRARY-NAMING section 4 says "Passive crystals: `Crystal`" but its own scheme says the second half is an official KiCad stem.
   - What's unclear: whether the owner wants (a) the crystal to stay in `Atomic_Oscillator` (legal, zero move; the current library is already offered), (b) to move it to `Atomic_Device` (KiCad's `Device` library holds `Crystal` symbols), or (c) to widen the name rule with an extra non-KiCad stem `Crystal` (changes LIB-05, REQUIREMENTS naming scheme "official KiCad symbol-library stem", Out of Scope row "Bare KiCad stems").
   - Recommendation: take (a) as the default (no suggestion differs, so no move), keep the planner free of a crystal rule, and ask the owner before planning if (c) is wanted. This is a decision for the discuss step, not for the executor.
2. **ICM-42688-P is suggested `Atomic_Timer`.** Accept the suggestion mis-file (the owner changes it in the preview; the CONTEXT table is only a test expectation) or add a category rule? Recommendation: accept and cover it with a test that asserts the owner can change the library and the gate then passes; do not alter Phase 10 behaviour in this phase.
3. **MPN default for families (D-05 vs D-06).** D-05 says MPN, else MP, else Value; D-06 says the LTC2954 box starts empty although Value is `ltc2954-1`. Recommendation: blank the default whenever two or more parts of the migration would receive the same default MPN (A6); that rule alone catches the four LTC2954 symbols (their Values are `ltc2954-1` twice and `ltc2954-2` twice). The planner should also decide what MAX17048G and MAX17048X (no MPN, Value `MAX17048G`) do: they keep Value as the MPN by D-05 and the owner can edit.
4. **Multi-model footprint and shared footprint (P-07).** Confirm the recommended rule: every model file of a footprint is kept under its own sanitised name unless it is the footprint's only model, in which case it is renamed to the first linking part's MPN; all `(model ...)` paths are rewritten.
5. **Where the chooser pins come from when the destination folder is not KiCad's config folder.** D-18 says "every `Atomic_` symbol library in the current tables". Recommendation: the tables in the Destination box (what Generate writes), and log which folder was read.
6. **Regenerate tables automatically after Run or behind a button.** Discretion item. Recommendation: a button ("Generate Tables") in the Result view that calls the existing `_on_generate` path after selecting the Atomic_ libraries, so the path-variable confirm and the table backups behave exactly as they do today.
7. **UI-SPEC.** The roadmap marks this phase "UI hint: yes" and `workflow.ui_phase` is true; no `13-UI-SPEC.md` exists. Run the UI design contract step before planning the window, or fold the layout decisions of D-15 into the plan.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv | everything | yes | 3.14.4, `env/Scripts/python.exe` | none needed |
| PySide6 | window, workers | yes | 6.12.0 | none |
| git | tag, commit, tests | yes | 2.49.0.windows.1 | `git.not_found` Issue, migration disabled |
| kicad-cli | normalise symbols, load gate, 3 real-binary tests | yes | 10.0.7 | tests skip with a stated reason; migration treats absence as blocking (A4) |
| KiCad 10 install (stock `symbols`, `template`, `footprints`, `3dmodels`) | descriptions, sibling index, official footprints | yes | `C:/Program Files/KiCad/10.0` | stem words as descriptions (D-20); suggestion falls back with INFO `naming.no_stock_libraries` |
| KiCad user config | chooser setup | yes | `%APPDATA%/kicad/10.0` | `config.dir_not_found` WARNING |
| `Custom/` submodule, checked out, branch `main` | everything | yes | HEAD `8f7d454`, 2 untracked files | none |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none on this workstation.
**Owner prerequisites for the live UAT:** commit or delete the two uncommitted duplicate files (D-02); set `KICAD_LIB_GITHUB` to this repo (P-12); close KiCad.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 with pytest-qt 4.5.0 (`qt_api = "pyside6"`, `QT_QPA_PLATFORM=offscreen` forced in `tests/conftest.py`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`addopts = "-ra --strict-markers"`, markers `wurth`, `local_kicad`, `kicad_cli`) |
| Quick run command | `.\env\Scripts\python.exe -m pytest <files> -q -p no:cacheprovider` (use absolute `C:/Git_Repo_Clones/Kicad_Libraries-importer/env/Scripts/python.exe` in worktrees) |
| Full suite command | `.\env\Scripts\python.exe -m pytest` (about 21-27 min, 9,000+ tests); `-m "not wurth"` about 15-20 min; neither fits the 600 s task gate, so every task runs targeted files |

### Phase Requirements to Test Map
Timings below were measured this session (whole file, Windows, warm venv).

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MIG-01 | Refuse on uncommitted files and list them by name; ignored `.bak` does not refuse; tag create / reuse at HEAD / refuse elsewhere; `tag` allowed, nothing else widened | unit + real git | `pytest tests/test_migration_precheck.py tests/test_gitops.py -q` (gitops 16 s) | Wave 0: new precheck test; edit `test_gitops.py` `EXPECTED_ALLOWED` and `GIT_MODULES` |
| MIG-02 | Per-part target, rename, field changes, footprint choice, failures; Run blocked until all pass; empty library blocks; name clash blocks | unit | `pytest tests/test_migration_plan.py tests/test_migration_gate.py tests/test_suggest_atomic.py -q` (suggest 5 s) | Wave 0: new |
| MIG-03 | One transaction: files written, old files and `.bak` deleted, emptied folders removed, rollback restores bytes after an injected failure at each op kind, stale source refuses, containment, case-only rename, locked file | unit + tmp tree | `pytest tests/test_migration_apply.py tests/test_install_apply.py -q` (install_apply 41 s) | Wave 0: new; `test_install_apply.py` exists |
| MIG-04 | After apply the scan reports zero atomic violations; tables regenerated; selection after rescan; commit plan with deletions passes the gate and commits | unit + real git + Qt | `pytest tests/test_migration_e2e.py tests/test_commit_plan.py tests/test_write_tables.py -q`; real git: `tests/test_commit_gate.py` (140 s) and `tests/test_commit_step.py` (349 s) run per wave in the background, not per task | Wave 0: new e2e; extend `test_commit_plan.py` (2 s), `test_commit_gate.py`, `test_commit_step.py` |
| MIG-05 | `MIGRATION-ATOMIC.md` holds the library map, symbol renames, footprint link changes and the three relink steps; Result view shows it with Copy | unit + qtbot | `pytest tests/test_migration_map.py tests/test_migration_dialog.py -q` | Wave 0: new |
| TBL-01 | Every generated entry has a non-empty description; existing description kept; add-only entry described; stock text read from the template; fallback words | unit | `pytest tests/test_table_merge.py tests/test_table_add_entries.py tests/test_write_tables.py tests/test_table_descriptions.py -q` (5 s + 2 s + 2 s) | Wave 0: new `test_table_descriptions.py`; extend the three existing |
| TBL-02 | Pins and columns old -> new, idempotent, backup per file, refusals (worktree, other checkout), KiCad-open retry flow, fresh merge, bad JSON, locked file; menu action and dialog texts | unit + qtbot | `pytest tests/test_kicad_setup.py tests/test_kicad_config.py -q` (config 3 s) and `tests/test_main_window.py` (11 s) for the action; `tests/test_commit_panel.py` 2 s, `tests/test_help_dialog.py` 6 s, `tests/test_atomic_check.py` 5 s, `tests/test_preview_tree.py` 1 s | Wave 0: new `test_kicad_setup.py` (copy the `cfg`/`backups`/`repo` fixtures of `test_kicad_config.py`) |
| DOC-01 | Docs describe the scheme; User Guide pages and shortcut list stay consistent | unit | `pytest tests/test_docs_atomic.py tests/test_help_dialog.py -q` | Wave 0: small new docs test (asserts `Atomic_`, `Atomic_Footprints`, the new menu names, no `<Type>_<SubCategory>_<Manufacturer>` in `CLAUDE.md`) |

Layering and guards that every new module must satisfy: `pytest tests/test_importer_layering.py tests/test_layering.py -q` (4 s + 2 s).
Draft persistence: `pytest tests/test_migration_draft.py tests/test_scan_cache.py -q` (scan cache 24 s). Atomic rule regression: `pytest tests/test_atomic_check.py tests/test_atomic_fixes.py -q` (fixes 16 s).

### Sampling Rate
- **Per task commit:** the targeted files of the area touched (all under about 40 s except real-git files) plus `tests/test_importer_layering.py tests/test_layering.py`.
- **Per wave merge:** add `tests/test_commit_gate.py tests/test_commit_step.py tests/test_gitops.py` (several minutes, run in the background) and `tests/test_main_window.py tests/test_main_window_import.py`.
- **Phase gate:** the full suite on the workstation (the owner's run, 21-27 min) green with only the four documented skips before `/gsd-verify-work`; then the owner's live UAT migration.

### Wave 0 Gaps
- [ ] `tests/migrationfixtures.py`: a rich v1 `Custom/` inside a throwaway superproject (`gitfixtures.make_superproject(populate=...)`): variants with shared Values, a family with identical graphics and one with a different pin, SnapEDA alias fields, a `.bak` (git-ignored), one footprint shared by two symbols, one footprint with two models, a symbol already linking an official footprint, mixed format versions, an `Atomic_` library to receive and one to empty. Build from `customfixtures`/`installfixtures` builders; never copy the live `Custom/`.
- [ ] `tests/test_migration_precheck.py`, `test_migration_plan.py`, `test_migration_gate.py`, `test_migration_apply.py`, `test_migration_e2e.py`, `test_migration_map.py`, `test_migration_draft.py`, `test_migration_dialog.py`
- [ ] `tests/test_kicad_setup.py`, `tests/test_table_descriptions.py`, `tests/test_docs_atomic.py`
- [ ] Edits to existing tests: `tests/test_gitops.py` (`EXPECTED_ALLOWED`, `GIT_MODULES`), `tests/test_importer_layering.py` (ALLOWED entries for every new `importer.migration.*` module), `tests/test_layering.py` (`kicad_setup`, `table_descriptions` in `ALLOWED` and `_CODE`), `tests/test_help_dialog.py` (new guide section and any shortcut), `tests/README.md` (Phase 13 notes), `tests/test_edits.py` (reads `Connector_USB_GCT.kicad_sym` from the live tree; skips once the owner has migrated)
- [ ] Framework install: none (pytest and pytest-qt already pinned)

## Security Domain

`security_enforcement` is enabled (`security_asvs_level: 1`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | single-user local tool |
| V3 Session Management | no | - |
| V4 Access Control | partly | filesystem containment: every path resolved and checked `is_relative_to(Custom)` before any write or delete; `WurthElektronik/` never touched (owner rule) |
| V5 Input Validation | yes | typed MPN, names, descriptions, paths: `naming.sanitize_name/sanitize_filename`, `stems.name_verdict`, `atomic_fixes._inside`, reserved Windows names, `complete_fill` validation; JSON draft and config read as untrusted with type checks and size caps |
| V6 Cryptography | no | sha256 only for change detection (`hashlib`), nothing secret |
| V8 Data Protection | partly | the draft holds only part choices in app data; no secrets; backups in `%LOCALAPPDATA%/KiCadExtLibManager/backups` |
| V12 Files and Resources | yes | atomic writes, temp files in the target folder, no `rmtree`, symlink/junction refusal, bounded reads (`MAX_KICAD_TEXT_BYTES`) |
| V14 Configuration | yes | KiCad config writes only the named keys, verified by re-parse, backup first, worktree and other-checkout refusal |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal through a typed library, symbol, footprint or model name | Tampering | sanitiser plus name verdict; build every path from a sanitised stem and an exact directory listing; never from text read out of a library file |
| Deleting outside `Custom/` or following a link | Tampering / Elevation | `resolve()` + `is_relative_to(custom_dir)` in preflight for every op; refuse junctions and symlinks; delete only paths in the plan |
| Half-applied migration | Repudiation / DoS of the library | one transaction, app-data backups, reverse-order rollback, `pre-atomic` tag, stale-file sha256 check before each op |
| Git argument or message injection | Tampering | constant tag name, `--literal-pathspecs`, messages through `commit_plan.sanitize_line` and a temp file (`-F`), allow-list in `gitops` (no remote subcommand) |
| Markup injection from vendor strings into Qt labels or tooltips | Tampering | plain-text labels or escaping (P-14) |
| Corrupt or hostile draft or config JSON | Tampering / DoS | untrusted-read pattern of `scan_cache`; a bad file means "no draft" or an ERROR with nothing written |
| Silent change of KiCad's global settings | Tampering | old -> new confirm, backup, refusal rules, no write without confirm (PROJECT.md safety constraint) |

## Sources

### Primary (HIGH confidence, read or run this session)
- Repository files opened with Read or measured with scripts: `13-CONTEXT.md`, `REQUIREMENTS.md`, `STATE.md`, `kicad_lib_manager/{library_scanner,table_generator,fsutil,gitops,atomic_check,atomic_fixes,changes,scan_cache,settings,kicad_process,kicad_files,sexpr,models,main_window}.py`, `importer/{applier,plan,layout,planner,incoming,form,suggest,siblings,categories,stems,naming,candidate,commit_plan,commit_gate,commit_step,kicad_cli,preview,content}.py`, `widgets/{import_dialog,commit_panel,import_result,preview_tree,content_view,conflict_row,atomic_check_dialog,help_dialog}.py`, `tests/{README.md,conftest.py,customfixtures.py,gitfixtures.py,test_gitops.py,test_layering.py,test_importer_layering.py,test_kicad_config.py,test_categories.py,test_help_dialog.py,test_manifests.py}`, `.planning/research/LIBRARY-NAMING.md`, `.planning/phases/12-.../12-CONTEXT.md` (D-09..D-12).
- The owner's KiCad files, read only: `C:/Program Files/KiCad/10.0/share/kicad/template/{sym-lib-table,fp-lib-table}`, `%APPDATA%/kicad/{7.0,8.0,9.0,10.0}/{kicad_common,eeschema,pcbnew,symbol_editor}.json`, `%APPDATA%/kicad/10.0/{sym-lib-table,fp-lib-table}`.
- The live `Custom/` (read only): `git status`, `git ls-files`, `.gitignore`, every `.kicad_sym`, `.kicad_mod` and the model folder listing; `suggest_library` run over every symbol (scratchpad scripts, nothing written to the repo).
- Experiments in a throwaway repo in the scratchpad: `git tag`, `rev-parse` tag lookup, `commit --only` with deletions, creations and renames, `status` omitting ignored files.

### Secondary (MEDIUM confidence)
- [KiCad Doxygen: COMMON_SETTINGS::SESSION](https://docs.kicad.org/doxygen/structCOMMON__SETTINGS_1_1SESSION.html) (three pin vectors).
- [KiCad Doxygen: project.cpp](https://docs.kicad.org/doxygen/project_8cpp_source.html) (`PinLibrary`, `UnpinLibrary`, immediate `SaveToFile`).
- [KiCad Doxygen: lib_tree_model_adapter.cpp](https://docs.kicad.org/doxygen/lib__tree__model__adapter_8cpp_source.html) (column load and save, "Item" first, exact-key lookups). This is the current master, not the 10.0 tag.
- [KiCad developer docs: Settings Framework](https://dev-docs.kicad.org/en/components/settings) (JSON, nlohmann, no statement on write timing or file watching).

### Tertiary (LOW confidence)
- None beyond the `[ASSUMED]` items in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, no new dependency; versions read from pins and the venv.
- Architecture: HIGH for reuse boundaries and the three "write-only" assumptions (read in code); MEDIUM for the exact module split (A7).
- Pitfalls: HIGH for P-01..P-05 and P-12 (reproduced or read), MEDIUM for P-06, P-08, P-13 (reasoned from code and Windows behaviour, tests will confirm).
- KiCad behaviour: MEDIUM (Doxygen mirror of current source, no KiCad 10 source tree read; write timing assumed).

**Research date:** 2026-11-11
**Valid until:** 2026-12-11 for the repo facts (the live `Custom/` changes with every owner commit; re-run the F-12 table before planning if it moves); KiCad facts are stable within 10.0.x.
