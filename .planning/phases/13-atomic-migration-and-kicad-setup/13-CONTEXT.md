# Phase 13: Atomic Migration and KiCad Setup - Context

**Gathered:** 2026-11-11
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase migrates every existing `Custom/` part to the `Atomic_` scheme in one previewed, reversible transaction and one `Custom` commit, plus a parent ref commit.
- **Before writing:** it refuses while `Custom` has uncommitted changes. Otherwise it tags `Custom` as `pre-atomic`.
- **The move:** it re-files symbols into `Atomic_<stem>` libraries and moves footprints into `Atomic_Footprints` or switches them to official KiCad footprints. It also rewrites names, fields, Footprint links and model paths, and deletes the old libraries and `.bak` files.
- **The gate:** Run stays disabled until every part passes the atomic rule.

Afterwards:
- the tables are regenerated with library descriptions (TBL-01);
- a confirmed action sets up KiCad 10's chooser: pins, plus the MPN and Manufacturer columns (TBL-02);
- the old → new map and the relink steps are shown and saved (MIG-05);
- the docs describe the `Atomic_` scheme (DOC-01).

Requirements: MIG-01..MIG-05, TBL-01, TBL-02, DOC-01.

**Live state differs from the research plan** (`research/LIBRARY-NAMING.md` §5, "12 → 9"). As of 2026-11-11, `Custom/` holds:
- 13 v1-named symbol libraries, including the new `LED_Cree`;
- `Atomic_Oscillator`, committed, which holds the passive crystal CM315D32768DZFT;
- an uncommitted `Atomic_Transistor_FET.kicad_sym` plus `Atomic_Footprints.pretty/DQK0006B.kicad_mod`, a duplicate CSD85301Q2 left from a UAT import;
- 3 `.bak` files.

The target count is therefore no longer 9 (see D-04).

</domain>

<decisions>
## Implementation Decisions

### Target libraries and live drift
- **D-01:** **Each part's target library comes from the Phase 10 suggestion, editable per part.** The suggestion is `suggest.suggest_library`: own-`Atomic_` sibling lookup, then KiCad stock sibling lookup, then the category map.
  - The preview shows the chosen library and its reason (tooltip, as in Phase 10 D-06). It is changed with the same library picker and name rules as the importer (Phase 10 D-08..D-13).
  - A part with no clear match starts with an empty library, which blocks Run (Phase 10 D-05).
  - Each part is decided on its own, so an old library can be split.
  - The research §5 table is used only as a test expectation, never as a hard-coded map.
- **D-02:** **The uncommitted duplicate CSD85301Q2 is cleaned up by hand** before migrating: the owner commits or deletes `Atomic_Transistor_FET.kicad_sym` and `Atomic_Footprints.pretty/DQK0006B.kicad_mod`.
  - There is no special duplicate-handling code. The MIG-01 refusal lists the uncommitted files by name, so the cause is obvious.
  - A name clash in a target library still blocks Run (D-05).
- **D-03:** **Parts already in an `Atomic_` library are listed too.** They are checked like every other part.
  - If the suggestion differs from their current library, the suggestion is pre-selected and the current library stays one pick away. Example: the crystal CM315D32768DZFT moves from `Atomic_Oscillator` to `Atomic_Crystal`, per the LIBRARY-NAMING §4 rule "passive crystals: `Crystal`".
  - An `Atomic_` library emptied by such moves is removed, like an emptied v1 library.
  - **Amended 2026-11-11 (planning):** the crystal example is withdrawn. `Atomic_Crystal` is not a legal name, because KiCad 10 has no `Crystal` symbol library and `stems.name_verdict` refuses it. CM315D32768DZFT **stays in `Atomic_Oscillator`**. No crystal rule and no naming-rule change are added. See D-22.
- **D-04:** **There is no fixed library count.** Success means:
  - no v1-named library is left;
  - each part sits in the library the preview showed;
  - the next scan reports zero atomic violations.

  Every `*.bak` in `Custom/Symbols/` is listed in the preview and deleted. Emptied old `.kicad_sym` files and `.pretty/` folders are removed. ROADMAP success criterion 2 and MIG-03 were reworded on 2026-11-11 to drop "9 libraries" and "the two `.bak` files".

### Part and footprint renames
- **D-05:** **Symbol name = sanitised MPN, editable.** The MPN is taken from MPN, else SnapEDA `MP`, else Value; the importer's sanitiser is reused. Example: `USB4056-03-A_REVA2` becomes `USB4056-03-A`.
  - Every rename is shown as old → new.
  - A name clash inside a target library (two parts landing on one name) blocks Run with a plain reason.
  - Renames follow sub-symbols and `extends` (v1.0 INST-02 machinery).

  — **Reversibility:** costly. Symbol names are stored as lib_ids in the owner's KiCad projects, so renaming again later means another relink pass (MIG-05 steps).
- **D-06:** **Variant families: the owner types each orderable MPN, and family members become derived symbols.**
  - Each existing symbol stays one part. Examples: LTC2954-1-DFN8 / -1-TSOT-23 / -2-DFN8 / -2-TSOT-23, MAX17048G / MAX17048X.
  - Where no real MPN is known (the LTC2954 Values read `ltc2954-1`), the MPN box starts empty and blocks Run until the owner types the orderable number. The symbol is then renamed to it.
  - Members of one family whose graphics and pins are identical become derived (`extends`) symbols of the first, as KiCad's own `Regulator_Linear` does. A derived symbol carries its own MPN, Value, Datasheet, Description and Footprint, and is judged on its own fields (Phase 9).
  - Members whose graphics differ stay standalone. The planner defines "identical" with the token-stream compare (Phase 9 D-21).
- **D-07:** **Footprint names are kept, editable** (Phase 10 D-20). IPC-style names such as `SON50P200X200X80-9N` stay.
  - A name clash inside `Atomic_Footprints` follows Phase 10 D-19: identical content is reused, and different content gets Overwrite / Rename / Skip, with Rename pre-filled.
  - The footprint's internal name and every Footprint field that links it are rewritten to `Atomic_Footprints:<FP>`.
- **D-08:** **An official KiCad footprint is offered per part. The default is "move into `Atomic_Footprints`".**
  - "Use an official KiCad footprint" opens the Phase 10 ranked `Lib:FP` picker (`footprint_index.rank_with_pads`), with the amber, non-blocking pad check (Phase 10 D-18).
  - Nothing switches by itself. With an official footprint, KiCad's own 3D model is used (Phase 10 D-17), and KiCad's files are never edited.
  - Research candidates to check against the datasheets: TSOT-23-8 / DFN-8 for LTC2954, LGA-16 for MMC5983MA, DSBGA-8 for BQ25180.
- **D-09:** **3D model files are renamed to `<MPN>.<ext>`, editable** (matching the importer's convention). Each rename is shown in the preview, and the model path in the footprint is rewritten to `${CUSTOM_3DMODEL_DIR}/<file>`.
  - A model linked by several footprints keeps the first part's MPN, and every linker is rewritten.
  - A case-only clash keeps the on-disk spelling (Phase 12 D-14).
- **D-10:** **Leftovers are deleted, each as a preview row the owner can untick to keep.** Leftovers are vendor footprints and models that are no longer linked: after an official-footprint switch, or a footprint no symbol links.
  - A kept footprint goes into `Atomic_Footprints`, and a kept model stays in `3DModels/`.
  - The `pre-atomic` tag keeps everything recoverable.
  - **Amended 2026-11-11 (board features):** delete-by-default applies only to footprints and models that the migration itself leaves unlinked. A footprint already unlinked before the migration, for example a board feature such as a PCB-trace USB-A plug in `Atomic_Footprints`, still gets a row, but it defaults to **Keep** (moved into `Atomic_Footprints` if it sits in a v1 `.pretty`). See D-21.

### Board features (non-orderable)
- **D-21:** **Board features live only as footprints in `Atomic_Footprints`, used with KiCad's stock symbols.** Board features are things that are not orderable parts, such as a PCB-trace USB-A plug, an edge connector, a test pad or a logo.
  - No `Atomic_` symbol is made for them, so the "every part is orderable" rule stays strict.
  - Example: `Atomic_Footprints:USB-A-PCB` used with KiCad's `Connector:USB_A` symbol, assigned in the project.
  - The atomic check judges symbols only, so such a footprint is never flagged. The migration keeps it by default (D-10 amendment).
  - The owner raised this on 2026-11-11 with SparkFun's `USB-A-PCB.kicad_mod` as the example.
- **D-11:** **Keywords, footprint description and tags follow the importer rules** (Phase 10 D-26..D-30):
  - keywords: the existing words first, then generated words not already present;
  - footprint description: replaced by the generated sentence, with the old one shown in Field changes;
  - tags: merged.

  All are editable in the detail pane with Regenerate. Official KiCad footprints are never written to.
- **D-12:** **Old alias fields are removed once their content is copied into the canonical fields.** These are SnapEDA `MF`/`MP` and the known price, stock and vendor-URL leftovers.
  - The canonical fields are `MPN`, `Manufacturer` (canonical spelling from `manufacturers.py`, Phase 10 D-23), `Datasheet` and `Description`, and Value = MPN.
  - Each removal is listed in Field changes.

### Migration window and fill-in
- **D-13:** **Entry point: a menu item "Migrate to Atomic Libraries…"** (File or Tools menu, planner's choice) opens its own window.
  - It is enabled only while `Custom/` still has a v1-named (non-`Atomic_`) symbol or footprint library or a `.bak` file. Otherwise it is greyed out with a tooltip saying why.
  - The code stays in the app after the migration, kept working by tests.
- **D-14:** **Progress is saved as a draft and restored on reopen.** The draft holds:
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
- **D-15:** **The layout is a part list plus a detail pane.**
  - **Left:** a tree grouped by target `Atomic_` library. Each part shows a pass mark or a failure count, and parts that will move show their old library.
  - **Right:** the selected part's detail. It reuses the import preview pieces: library picker, footprint choice (move / official picker), model row with "Add 3D model…", field edit boxes, Field changes, and keyword and footprint-text edits.
  - **Top:** a failure strip lists every remaining atomic-rule failure as a clickable line that selects the part and focuses the field (Phase 10 D-25 style, plain language). Run stays disabled until the strip is empty.
  - **"Files" tab:** every write, rename, move and delete, with the Phase 5 content and diff view.
- **D-16:** **The old → new map is saved in `Custom/MIGRATION-ATOMIC.md`**, written by the migration and included in the single `Custom` commit. It holds:
  - the library map, the symbol renames and the footprint link changes;
  - the KiCad relink steps: Edit Symbol Library Links → Update Symbols from Library → Update PCB from Schematic.

  The Result view shows the same content, with a Copy button and a link that opens the file.

### KiCad chooser setup and table descriptions
- **D-17:** **"Set Up KiCad Chooser…" is its own menu action.** It can be run any time, for example after the importer creates a new `Atomic_` library, and the migration Result view also offers it as a button.
  - It follows the path-variable sync contract: old → new values shown first, a backup of each config file, an atomic write of only the changed keys, and a refusal from a worktree or a checkout other than the configured `KICAD_LIB_GITHUB`.
  - Renamed 2026-11-12 by plan 13-27 (UAT gap G-13-1-c) to "Pin Atomic Libraries in KiCad..." in every user-facing text; identifiers and `chooser.*` codes unchanged.
  - It uses the KiCad-open Retry / Change anyway / Not now dialog with a re-read and merge into fresh content (Phase 12 D-09..D-11).
  - It writes two files: `kicad_common.json` (`session.pinned_symbol_libs`, `session.pinned_fp_libs`) and `eeschema.json` (`lib_tree.columns`, `lib_tree.column_widths`).
- **D-18:** **Pins:**
  - `pinned_symbol_libs` gets every `Atomic_` symbol library in the current tables, and `pinned_fp_libs` gets `Atomic_Footprints`.
  - Pins the owner added by hand are kept.
  - `Atomic_` pins whose library no longer exists, such as one emptied by D-03, are removed and shown as old → new.
- **D-19:** **Columns:** `MPN` and `Manufacturer` are inserted right after `Description`, and the stray `MANUFACTURER` column is removed. Its width entry moves to `Manufacturer`.
  - The owner's other columns keep their order. Today's list `Item, Description, Capacitance, R, Voltage, Value, MANUFACTURER` becomes `Item, Description, MPN, Manufacturer, Capacitance, R, Voltage, Value`.
  - The action is idempotent: already set up means nothing to write and an INFO line.
- **D-20:** **Table descriptions (TBL-01) are generated.**
  - `Atomic_<stem>`: "Atomic parts: " + KiCad's own description for that stem, read from the installed KiCad 10 stock `sym-lib-table`. Without it, the stem words with underscores as spaces are used.
  - `Atomic_Footprints`: "Atomic part footprints (own and vendor)".
  - Every other generated entry, Würth and any remaining v1 name included: `<Source>: <nickname with underscores as spaces>`.
  - A description already present in an existing table entry is kept, not overwritten.
  - This applies to Generate and to the post-install add-only entry alike, since both go through `_format_entry`.

### Planning-time decisions (owner, 2026-11-11, after research)
- **D-22:** **The crystal CM315D32768DZFT stays in `Atomic_Oscillator`** (D-03 amendment). The `Atomic_Crystal` row in Specifics is withdrawn. The naming rule (LIB-05, official KiCad stems only) is not widened.
- **D-23:** **A footprint with several model blocks keeps every block and every model file under its own name.** Nothing is deduplicated, renamed or deleted, even when the files are byte-identical. Each `(model ...)` path is only rewritten to `${CUSTOM_3DMODEL_DIR}/<its own file name>`.
  - The D-09 rename to `<MPN>.<ext>` applies only to a footprint's single model.
  - Live case: `XCVR_NORA-W106-00B` lists `NORA-W106-00B.step` and `NORA-W106-10B.step`, which are byte-identical. Both NORA symbols link it. Both files follow the MPN naming convention, so both stay.
  - Several model blocks are neither an atomic-rule failure nor a leftover row. The importer's "extra_models" warning must not block the migration.
- **D-24:** **Tables are regenerated behind a "Generate Tables" button in the migration Result view, not automatically.** The button calls the existing Generate path with every new `Atomic_` library selected first (research P-01: a plain rescan unchecks them). The path-variable confirm and the table backups therefore behave as today.
- **D-25:** **The migration window is planned from D-15 directly.** There is no separate UI design contract (UI-SPEC).
- **D-26:** **Wrong-checkout check.** Before writing, Generate Tables, Install Part, the migration Run and Set Up KiCad Chooser compare the app's repo folder with the folder KiCad's `KICAD_LIB_GITHUB` names (in `kicad_common.json`). The compare uses resolved paths, normalised separators, and is case-insensitive on Windows.
  - **Migration Run: refuses** when they differ. Running it would rewrite a copy KiCad does not read. The refusal names both folders and says to run the app from the folder KiCad reads, or to fix the path in KiCad Preferences → Configure Paths.
  - **Set Up KiCad Chooser:** already refuses per D-17. It reuses the same check and wording.
  - **Generate Tables and Install Part: warn, not block.** Importing in the development copy, pushing, then pulling in the copy KiCad reads is a legitimate workflow. The warning is plain: it names both folders and says that KiCad will not see the new libraries or parts until they exist in the folder KiCad reads (push, then pull there). It appears where the user will see it before or right after the write, not only as a log line; the planner chooses where (the existing Generate confirm or the Result view).
  - **No variable, or no KiCad config:** no warning. The existing path-variable sync handles that case.
  - **Why:** on 2026-11-11 the app, run from the `Kicad_Libraries-importer` worktree, wrote an `Atomic_Footprints` entry into the USBlitz project table. KiCad resolved it through `KICAD_LIB_GITHUB` to the `Kicad_Libraries` checkout, which lacked the library, and reported "Atomic_Footprints not found". Today only the path-variable sync detects another checkout.
  - The check is a Qt-free service function with an injectable config path, so tests run from worktrees and temp folders without touching the owner's KiCad config.

### Claude's Discretion
- **Research defaults the owner did not override** (13-RESEARCH.md Open Questions 2, 3, 5):
  - ICM-42688-P may be mis-suggested as `Atomic_Timer`. Phase 10 suggestion behaviour is not changed; the owner corrects it in the preview. A test proves that a changed library then passes the gate.
  - The default MPN is blanked whenever two or more parts of the migration would get the same default MPN (research A6; this catches the four LTC2954 symbols). MAX17048G/X keep Value as MPN per D-05.
  - The chooser pins (D-18) come from the tables in the Destination folder, and the log names the folder read.
- **After Run:** the order is rescan, then table regeneration through the D-24 button (old managed entries removed, new ones added), then the Phase 11 commit panel offering one `Custom` commit plus the parent ref. The commit gate (GIT-06) must accept a commit that holds deletions and renames. Nothing is written to KiCad's config without its confirm.
- **`pre-atomic` tag:** it is created after the MIG-01 clean check and before the first write. It is a local, lightweight or annotated tag, never pushed. If the tag already exists and points at HEAD, it is reused. If it points elsewhere, the migration refuses with a plain reason and the manual command. `gitops.ALLOWED_SUBCOMMANDS` has no `tag` (and no `rm`/`mv`) today, so the planner adds what is needed under the existing allow-list rules.
- **Transaction:** it reuses the importer's applier pattern (`importer/applier.py`: app-data backups, ordered atomic writes, verify, roll back on any `BaseException`, stale-file re-check before each write) or the `atomic_fixes.apply_preview` pattern. Deletes and moves are part of the same rollback.
- **Rule failures with edit boxes:** these reuse `atomic_fixes.complete_fill` / the Check Atomic Parts fill-ins where they fit.
- How migration planning runs off the GUI thread, and how the KiCad stock sibling index and footprint index are shared with the importer.
- Draft file format and its versioning.
- The exact wording of the menu items, strip lines, tooltips, `MIGRATION-ATOMIC.md` and the Result rows: plain language, with no raw field names such as `ki_keywords` or `ki_fp_filters`.
- **DOC-01 content:** `CLAUDE.md` naming section and SnapEDA import steps, PROJECT.md, and `research/LIBRARY-NAMING.md`. The latter gets an update note that `_MecaFrog` became the `Atomic_` prefix and `MecaFrog.pretty` became `Atomic_Footprints.pretty`, and its §5 table is refreshed to the live parts. The CLAUDE.md GUI Behavior and Menu Shortcuts sections also gain the two new menu actions.
- **Tests:** they use the synthetic `Custom/` (`tests/customfixtures.py`) and throwaway git repos (`tests/gitfixtures.py`). The live-`Custom/` write-protect guard stays in force. The live migration is the owner's UAT run.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scheme and target libraries
- `.planning/research/LIBRARY-NAMING.md`: §4 classification rules (passive crystal → `Crystal`, radio module → `RF_Module`, ...), §5 target table (written with `_MecaFrog`; read it as `Atomic_` prefix and `Atomic_Footprints`; it predates `LED_Cree` and `Atomic_Oscillator`), §6 fields/keywords/footprint rules and the gaps found in the existing symbols, §7 migration steps
- `.planning/REQUIREMENTS.md`: MIG-01..MIG-05, TBL-01, TBL-02, DOC-01 (and FLD-01..FLD-03, which name the migration as a user)
- `.planning/ROADMAP.md`: Phase 13 success criteria

### Prior phase decisions this phase builds on
- `.planning/phases/09-atomic-rule-check-and-scan-detection/09-CONTEXT.md`: the atomic rules, derived-symbol judging, the token-stream compare (D-21), only-`Atomic_` scope (D-23), safe fixes and fill-ins in Check Atomic Parts
- `.planning/phases/10-importer-on-the-atomic-scheme/10-CONTEXT.md`: suggestion order (D-01..D-07), name rules and picker (D-08..D-13), footprint destination and official picker (D-14..D-20), install gate and Value/Manufacturer rules (D-21..D-25), keywords and footprint text (D-26..D-30)
- `.planning/phases/11-commit-gate-and-commit-panel-fixes/11-CONTEXT.md`: commit gate scope (D-01..D-05), refusal and "Check again" (D-06..D-11), commit outcome handling
- `.planning/phases/12-import-flow-fixes-and-case-sensitive-re-test/12-CONTEXT.md`: table entry repoint and clash rules (D-01..D-05), KiCad-open dialog and fresh-content merge for KiCad config writes (D-09..D-12), on-disk spelling on case-only overwrite (D-14)
- `.planning/PROJECT.md`: Key Decisions (KiCad path variables never written silently; worktree refusal; managed table entries by URI tail)

### Project docs
- `CLAUDE.md`: naming section and SnapEDA steps to rewrite (DOC-01), GUI Behavior / Menu Shortcuts to extend, Git workflow (Custom commit first, then the parent ref)
- `tests/README.md`: expected skips; the suite must not read or write the live `Custom/`

### KiCad files touched (owner's workstation, read for format)
- `%APPDATA%/kicad/10.0/kicad_common.json`: `session.pinned_symbol_libs`, `session.pinned_fp_libs` (both empty today)
- `%APPDATA%/kicad/10.0/eeschema.json`: `lib_tree.columns` = `Item, Description, Capacitance, R, Voltage, Value, MANUFACTURER`; `lib_tree.column_widths`
- `C:/Program Files/KiCad/10.0/share/kicad/template/sym-lib-table` (or wherever KiCad 10 keeps its stock table): source of stock library descriptions for D-20 (researcher: confirm the path)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kicad_lib_manager/importer/suggest.py`: `suggest_library`, `suggestion_text`, `existing_libraries` (D-01).
- `kicad_lib_manager/importer/stems.py`: `allowed_stems`, `name_verdict`.
- `kicad_lib_manager/importer/siblings.py`: sibling indexes.
- `kicad_lib_manager/importer/footprint_index.py`: `build_index`, `rank_with_pads`, `pad_numbers` (D-08).
- `kicad_lib_manager/importer/keywords.py`: `generate_keywords`, `merge_words`.
- `kicad_lib_manager/importer/footprint_text.py`: `footprint_facts`, `describe`, `generated_tags` (D-11).
- `kicad_lib_manager/importer/naming.py`: sanitiser (D-05).
- `kicad_lib_manager/importer/applier.py`: the install transaction with backups, ordered writes, stale checks, rollback, `_drop_twin`, and on-disk spelling.
- `kicad_lib_manager/importer/planner.py`: symbol merge and rename following sub-symbols and `extends`, footprint copy with model insert or rewrite.
- `kicad_lib_manager/atomic_check.py`: `check_symbol`, `check_libraries`, `repo_context`, `AtomicContext`, `FootprintTarget`, `effective_mpn` (the Run gate and the failure strip).
- `kicad_lib_manager/atomic_fixes.py`: `build_preview`, `apply_preview`, `complete_fill`, `_set_or_insert`, `_insert_property` (field edits and fill-ins).
- `kicad_lib_manager/manufacturers.py`: canonical names and aliases (D-12).
- `kicad_lib_manager/changes.py`: token-stream compare against HEAD (D-06 "identical graphics", draft "changed since").
- `kicad_lib_manager/importer/commit_gate.py`, `commit_plan.py`, `commit_step.py`, `widgets/commit_panel.py`: the Phase 11 commit path for the migration commit.
- `kicad_lib_manager/gitops.py`: `run_git` and `ALLOWED_SUBCOMMANDS`, which lacks `tag`/`rm`/`mv`.
- `kicad_lib_manager/table_generator.py`: `_format_entry`, which writes `(descr "")` today (TBL-01). Also `_merge_table`, `add_library_entries`, `table_info`.
- `kicad_lib_manager/library_scanner.py`: `sync_kicad_path_vars`, `_only_vars_changed`, `_path_var_refusal`, which are the template for the chooser setup write (D-17).
- `kicad_lib_manager/kicad_process.py`: `kicad_running()`.
- `kicad_lib_manager/widgets/import_dialog.py`, `preview_tree.py`, `content_view.py`, `conflict_row.py`: preview pieces to reuse in the detail pane and Files tab.
- `kicad_lib_manager/widgets/atomic_check_dialog.py`: the failure list and fill-in UI.
- `kicad_lib_manager/scan_cache.py`: an app-data storage pattern for the draft (D-14).
- `kicad_lib_manager/settings.py`: app-data location helpers.

### Established Patterns
- Qt-free services return `Issue` lists routed by `Severity`. Errors go to the log and Result views, not message boxes, except the sanctioned KiCad-config confirm.
- Long work runs on a `QThread`/`TaskWorker`. The GUI thread never blocks, including kicad-cli and `tasklist`.
- Lossless span edits (`sexpr`, `kicad_files`): untouched bytes stay identical, and CRLF/LF is kept.
- No write without a preview. Writes are atomic with backups. Git commits need explicit confirmation and never push.
- Plain-language UI: no raw KiCad field names in user-facing text.
- Layering tests keep services Qt-free.

### Integration Points
- `main_window.py`: the two new menu actions (Migrate, Set Up KiCad Chooser). The migration's post-Run rescan, table regeneration and commit panel hand-off.
- `table_generator._format_entry` / `_merge_table`: descriptions, plus dropping removed managed entries.
- A new KiCad-config writer for `eeschema.json` and the `session` keys in `kicad_common.json`, beside `sync_kicad_path_vars`.
- `gitops.ALLOWED_SUBCOMMANDS`, plus a tag helper. The commit plan must carry deletions and renames.

</code_context>

<specifics>
## Specific Ideas

- **Live parts to expect** (2026-11-11), as the likely suggestion outcome. These are test expectations, not a hard-coded map:

  | Parts | Likely target |
  |---|---|
  | GCT FFC2A32-06-T, MEM2085, USB4056/4730/4745 | `Atomic_Connector` |
  | BQ25180, MAX17048G/X | `Atomic_Battery_Management` |
  | LTC2954 ×4 | `Atomic_Power_Management` |
  | ICM-42688-P | `Atomic_Sensor_Motion` |
  | MMC5983MA | `Atomic_Sensor_Magnetic` |
  | CSD85301Q2 | `Atomic_Transistor_FET` |
  | NORA-W106-00B/10B | `Atomic_RF_Module` |
  | ATXK-H14 | `Atomic_Oscillator` |
  | CM315D32768DZFT | `Atomic_Oscillator` (stays; D-22) |
  | RS3-1212S/H3 | `Atomic_Converter_DCDC_Isolated` |
  | UHD1110 (Cree) | `Atomic_LED` |

- Known gaps the owner will fill in the preview: about 15 empty datasheets, about 7 empty descriptions, the LTC2954 orderable MPNs, and missing 3D models (ATXK-H14 has none).
- The migration must still work if the owner first commits the duplicate `Atomic_Transistor_FET` instead of deleting it. In that case it is just another listed part, and its name clash with the migrated CSD85301Q2 blocks Run until one is renamed or its library is changed.

</specifics>

<deferred>
## Deferred Ideas

- A general "Reorganise" tool to re-file or rename parts between `Atomic_` libraries at any time. It was considered as the migration entry point and rejected for this phase as a bigger scope. It could be its own phase later.
- An editable per-library description column in the main window. It was rejected in favour of generated descriptions (D-20).
- A "create a part" flow (new symbol and footprint from scratch, not from a vendor package). Today a creation goes through Import Part with a loose-files folder. A board feature is footprint-only (D-21).
- Documenting the board-feature rule (D-21) in `CLAUDE.md` can ride with DOC-01 if the planner sees fit.
- **A reserved prefix for intentionally non-atomic own parts** (for example `Generic_Symbols`, `Generic_Footprints`). The atomic check, the migration and the Migrate menu would recognise it as deliberate: not checked, not migrated, not counted as v1. Without it, any non-`Atomic_` library in `Custom/` counts as v1-named (D-04, D-13). It was raised on 2026-11-11 and deferred by the owner. For now, generic parts use KiCad's stock symbols, and board features use `Atomic_Footprints` (D-21).

</deferred>

---

*Phase: 13-atomic-migration-and-kicad-setup*
*Context gathered: 2026-11-11*
