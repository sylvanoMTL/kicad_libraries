# Phase 9: Atomic Rule Check and Scan Detection - Context

**Gathered:** 2026-10-26
**Status:** Ready for planning

<domain>
## Phase Boundary

One Qt-free atomic rule check and one canonical manufacturer table, with the scan as their first user. Every scan runs the check on every symbol in an `Atomic_` library, marks failing symbols in the library tree (tooltip plus one log line per failure), and highlights symbols and footprints added or changed in `Custom/` since the last `Custom` commit. A check dialog lists every violation, offers one-click fixes only where they are safe, and lets the user fill in a missing Datasheet, Description or 3D model. Every fix is previewed and written with a backup. Requirements: ATOM-01, ATOM-02, ATOM-03, FLD-02, SCAN-01, SCAN-02, SCAN-03.

Out of this phase: the importer's use of the check and the table (Phase 10, LIB-04..07, FLD-01/03), the commit gate (Phase 11, GIT-06), and the migration (Phase 13). The check module and the manufacturer table must be designed so those phases reuse them unchanged. Today `Custom/` holds **no** `Atomic_` library (12 v1-named libraries plus 3 `.bak` files), so on the live tree only the changed-part highlight is visible until Phase 13.

</domain>

<decisions>
## Implementation Decisions

### Library tree marks and highlights (SCAN-01, SCAN-02)
- **D-01:** Add **symbol child rows** under symbol library rows in the Symbols tree. Child rows have **no checkbox**, so table selection stays per library and the existing `selected` / footprint-sync logic is untouched. A failing symbol gets the warning icon and amber text (the existing `AMBER` + `SP_MessageBoxWarning` style used for "Missing FP"), and its tooltip lists every broken rule in plain language. The library row's Status shows a count, e.g. `1 of 3 fail`.
- **D-02:** The **changed-since-last-Custom-commit highlight applies to every library in `Custom/`**, not only `Atomic_` ones, so it is useful now and during the migration. Child rows are added only where there is something to show: `Atomic_` libraries (always), and any other `Custom/` library that holds a new or changed item. WurthElektronik and any other submodule source are **never** highlighted or expanded into rows.
- **D-03:** **Separate markers.** Failing: warning icon plus amber. Changed: theme `ACCENT` colour plus the word `New` or `Changed` in the Status column. When a symbol is both, it gets the warning styling and the Status reads e.g. `Changed · 2 rules`, and the tooltip lists both. Use theme tokens only, with no new hard-coded colours.
- **D-04:** The **footprint tree gets the changed highlight too**: a `Custom/` footprint library that holds a `.kicad_mod` added or changed since the `Custom` commit gets child rows for those footprints, marked `New`/`Changed` like symbols. Footprints are not judged by the atomic rules themselves. A footprint problem (missing, or its model missing) is reported on the symbol that links it.
- **D-05:** **Log:** one WARNING line per (symbol, broken rule), e.g. `Atomic_Connector / FFC-0.5-20: no datasheet`, then one summary line, e.g. `Atomic check: 7 of 19 symbols fail (23 problems)`. One INFO line per new or changed symbol or footprint. Messages follow the project's existing `Issue`/`list[str]` message shape and the plain-language rule (no raw field names such as `ki_description`).
- **D-06:** After a scan, **auto-expand only libraries holding a failing or changed item**. Clean libraries stay collapsed. The right-click Expand All / Collapse All keep working.

### Manufacturer table (FLD-02)
- **D-07:** The canonical Manufacturer value is the **full company name without a corporate suffix**: `Texas Instruments`, `Global Connector Technology`, `Analog Devices`, `u-blox`, `Memsic`, `Abracon`, `RECOM`. Short forms (`TI`, `GCT`, `ADI`, `U-BLOX`, `uBlox`, `RECOM Power`, `Memsic Inc.`) are aliases. Researcher/planner: confirm each company's own spelling (e.g. u-blox's lowercase form) when seeding the table. — **Reversibility:** costly — Phase 13 migration and Phase 10 imports write these strings into every `Custom/` symbol, so changing a canonical spelling later means rewriting committed parts.
- **D-08:** **Acquired brands keep their original name** as printed on the part's datasheet: `Maxim Integrated` and `Linear Technology` stay themselves and are not folded into `Analog Devices`, and `InvenSense` is not folded into `TDK`. The ownership relation may be recorded in the table for Phase 10's keyword generation (FLD-01), but it never changes the Manufacturer field.
- **D-09:** The table is a **Qt-free Python module** (e.g. `kicad_lib_manager/manufacturers.py`, a leaf like `importer/fieldrules.py`) mapping each canonical name to its aliases. The user extends it by adding a line in code. It is the **one** table read by the check now, and by the importer and migration later. `importer/suggest.py`'s `MANUFACTURER_ALIASES` (which maps to short library tokens such as `TI`) is folded into or derived from it, so two lists cannot drift. Phase 10 drops the manufacturer token from library names anyway (LIB-04), so a folding approach that keeps v1.0 suggestion tests green until Phase 10 is acceptable.
- **D-10:** **Folded matching:** compare after casefolding and removing spaces, punctuation and corporate suffixes (Inc., Ltd, GmbH, Corp., Co., AG, LLC, etc., as `suggest._CORPORATE_WORDS` does today). A value whose folded form matches a table entry but is not exactly the canonical string (an alias, a case variant or a suffix variant) is reported and gets the "use canonical spelling" fix.
- **D-11:** A non-empty Manufacturer **not in the table passes** the "Manufacturer present" rule and gets an **INFO-level** note, `not in the manufacturer table`, in the dialog and the log, so the user knows to add it. It is not blocking.

### Check dialog and fixes (SCAN-03)
- **D-12:** Opened from a **menu item** (e.g. `Check Atomic Parts…` with a shortcut such as Ctrl+Shift+A, free of conflicts with the existing Ctrl+I/G/R/K/Q/Shift+R/F1) **and** by **double-clicking a marked symbol row**, which opens the dialog scrolled to that symbol. The dialog works from the last scan's result, and nothing is re-checked on the GUI thread.
- **D-13:** **Tick, preview, apply.** Each safe fix is a ticked row (e.g. `FFC-0.5-20: Value "FFC20" → "FH12-20S-0.5SH"`) with Select All. `Preview & apply` shows the exact before → after for each file, then writes all ticked fixes with one atomic write plus backup per file (`fsutil.atomic_write_text` / `backup_file`) and triggers a rescan, so the fixed violations are gone from the next scan. Safe fixes are only: Value := MPN (offered only when an MPN is present), `MF`/`MP` (and the other `fieldrules` aliases) → `Manufacturer`/`MPN`, canonical manufacturer spelling, and removing price/stock leftovers.
- **D-14:** **Duplicate alias properties merge.** When a symbol has several Manufacturer (or MPN) properties (e.g. `MF` and `MANUFACTURER`, as two `Custom/` libraries have today), the fix keeps one property named `Manufacturer` (or `MPN`) holding the canonical value and removes the rest, provided the values agree after canonical folding (`GCT` and `Global Connector Technology` count as agreeing). When they name truly different companies, or MPN values differ, no one-click fix is offered. The dialog shows both values and the user picks.
- **D-15:** **3D model fill-in:** the user picks a `.step`/`.wrl` file. It is copied into `Custom/3DModels/` with the same safety checks the importer's separate-model intake applies (name clash, size cap, extension; see `importer/package.py` `open_model_source`). The linked footprint then gets a model line `${CUSTOM_3DMODEL_DIR}/<file>`. If the footprint already has a model line pointing at a missing file, that line is re-pointed rather than a second one added. The footprint write is shown in the same preview and backed up the same way. Datasheet and Description are typed in.
- **D-16:** **KiCad running:** reuse `kicad_process.kicad_running()`. The preview warns that KiCad is running and that a library open in the Symbol Editor must be closed without saving or reloaded, or KiCad may overwrite the fixes. Apply is still allowed. Each file is **re-read just before writing**, and the write is refused if it changed since the preview was built (the same stale-file rule as `importer/applier.py` `install.stale_plan`), so an edit KiCad saved after the scan is never lost.
- **D-17:** **Datasheet validity is one definition used everywhere** (scan rule, dialog input, and later the importer and the commit gate). It must be an `http://`/`https://` URL, a `${VAR}/…` path or an absolute path. It is never fetched. Empty, `~`, or anything else (e.g. `see website`) fails with a plain reason such as `Datasheet is not a link or file path`.
- **D-18:** **Price/stock leftovers are a cleanup finding, not a rule failure.** They are listed in the dialog and the log as leftover price/stock data, and their removal fix is ticked by default. They do not turn the symbol amber, do not count in `N of M fail`, and will not block the Phase 11 commit. ATOM-01's 7 rules stay the only blocking rules. Use `fieldrules.is_volatile` / `GENERIC_VOLATILE` for detection.

### Rule semantics and edge cases (ATOM-01..03)
- **D-19:** **3D model rule for official KiCad footprints:** expand `${KICAD10_3DMODEL_DIR}` (and the older `KICADn_3DMODEL_DIR` names) to the `3dmodels` folder next to the detected KiCad footprints folder (on this workstation `C:/Program Files/KiCad/10.0/share/kicad/3dmodels`) and check that the file exists. `${CUSTOM_3DMODEL_DIR}` resolves to `Custom/3DModels/` in the repo, as `check_3d_model_paths` does today. If KiCad's model folder cannot be found, the rule **fails** with a plain reason (`Could not check the 3D model: KiCad's 3D model folder was not found`). It stays blocking, and nothing is passed on trust.
- **D-20:** **Footprint rule target:** the Footprint field passes when it names exactly one existing `<Lib>:<FP>` in any footprint library in the repo (Custom, WurthElektronik) or in KiCad's installed footprints, which matches the scan's existing cross-reference scope. It fails when it is empty, has no `Lib:` part, names a library that does not exist or is ambiguous (a nickname collision), or names a footprint absent from that library. Restricting targets to `Atomic_Footprints` is Phase 10's job (LIB-06), not this rule's.
- **D-21:** **"Changed" means content, not formatting.** Compare each symbol's S-expression token stream (and each `.kicad_mod`'s) with the same item in the `Custom` HEAD version of the file (`gitops.head_blob`), ignoring whitespace and line endings. `New` means it is not at HEAD. A renamed symbol shows as `New`. A KiCad re-save that only reformats is not flagged, but a format upgrade that rewrites tokens is.
- **D-22:** **Derived (`extends`) symbols** need their **own MPN**, and their Value must equal that MPN, even when the parent has one. Manufacturer, Datasheet, Description and Footprint may be **inherited** from the parent when the child doesn't override them, which is how KiCad displays variants (the `AP2112K-1.2/1.8/2.5/3.3` pattern). The inherited value is judged by the same rules. Researcher: verify which fields KiCad 10 lets a derived symbol override, and how it stores inherited ones.
- **D-23:** **ATOM-03 scope** is by library nickname prefix `Atomic_` (capital A, per the naming decision), wherever the library lives. Libraries without the prefix are never judged by the atomic rules (only the D-02 highlight applies, and only inside `Custom/`).

### Testing and UAT
- **D-24:** Automated tests extend the Phase 8 synthetic fixture (`tests/customfixtures.py`) with `Atomic_` libraries now, rather than in Phase 10 as Phase 8 D-02 had planned. They hold passing and deliberately broken symbols (one per rule, a derived symbol without its own MPN, alias manufacturers, `MF`/`MANUFACTURER` duplicates, price leftovers, an official-footprint link) plus git-backed cases for New/Changed. The Phase 8 write-protect guard on the live `Custom/` stays in force.
- **D-25:** **UAT uses a scratch copy of the repo**: a helper (like Phase 8's `KICAD_IMPORT_UAT_DIR` hook) builds a throwaway repo copy with a few `Atomic_` libraries made from the owner's real parts, some passing and some broken on purpose, and the app runs against it. The real `Custom/` is never touched. The live-tree UAT checks only the changed-part highlight.

### Claude's Discretion
- Module and class names, the check's result data shape (it must be Qt-free and reusable by the importer, the commit gate and the migration), and how results attach to `ScanResult` / `SymbolLibrary`.
- How the check runs inside `ScanWorker` (it must stay off the GUI thread) and how git HEAD reads are batched for speed.
- Behaviour when git is missing or `Custom` is not a git checkout: the highlight is skipped with one INFO line, and the atomic check still runs.
- The exact shortcut key, dialog layout, and plain-language wording of each rule reason.
- Whether `.bak` files are ignored by the check (they are not `.kicad_sym` libraries, so the scanner already skips them).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/REQUIREMENTS.md` — ATOM-01..03, FLD-02, SCAN-01..03 (the 7 rules, the safe-fix list); later consumers LIB-07, GIT-06, MIG-02, FLD-01
- `.planning/ROADMAP.md` § Phase 9 — the 5 success criteria
- `.planning/PROJECT.md` — the Key Decisions row on the `Atomic_` scheme and the atomic rule; the "blank preview text" and stale-plan decisions

### Naming and field conventions
- `.planning/research/LIBRARY-NAMING.md` §6 — canonical field names (match kipart-search), alias names, "no price, stock or distributor fields", the manufacturer-table need, and the gaps found in the existing 19 symbols. Its `_MecaFrog` suffix is superseded by the `Atomic_` prefix.
- `CLAUDE.md` — KiCad path variables (`CUSTOM_3DMODEL_DIR`, `KICAD_LIB_GITHUB`) and the Git workflow

### Prior phase context
- `.planning/phases/08-test-isolation-and-kicad-10/08-CONTEXT.md` — synthetic `Custom/` fixture rules (D-01/D-02: builders return bytes, no paths), the live-`Custom/` write-protect guard (D-13), and the UAT scratch hook (D-09)
- `tests/README.md` — expected skips, and the rule that the suite must not write to or depend on the live `Custom/`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kicad_lib_manager/importer/fieldrules.py`: `MANUFACTURER_FIELDS`, `MPN_FIELDS`, `GENERIC_VOLATILE`, `is_volatile`, `is_placeholder`, `is_protected`. These are the alias and leftover definitions the check and fixes must reuse. It's a leaf module (stdlib only), so the check module can import it, or it can move up a layer if the layering tests require that.
- `kicad_lib_manager/importer/suggest.py`: `MANUFACTURER_ALIASES` and `_CORPORATE_WORDS` hold the folding logic and seed data for the new manufacturer table (D-09, D-10).
- `kicad_lib_manager/kicad_files.py`: `find_symbols`, `find_property`, `list_properties`, `extends_name`, `find_models`, `set_property_edit`, `rename_property_edit`, `remove_property_edit`, `retarget_model`, `model_insert_edit`, `footprint_name` are the parse and edit primitives for the check and every fix.
- `kicad_lib_manager/sexpr.py`: `parse` (with the node cap), `Edit`, `apply_edits`. Use the token stream for the D-21 content compare.
- `kicad_lib_manager/fsutil.py`: `read_source`, `atomic_write_text`, `backup_file`, `default_backup_dir` for safe fix writes (D-13).
- `kicad_lib_manager/gitops.py`: `find_git`, `run_git`, `head_blob`, `status_entries`, `show_toplevel` for the HEAD compare (D-21).
- `kicad_lib_manager/kicad_process.py`: `kicad_running()` for the D-16 warning.
- `kicad_lib_manager/library_scanner.py`: `cross_reference`, `get_kicad_default_fp_nicknames`, `find_kicad_footprint_dir`, `check_3d_model_paths`, `_custom_model_names`, `CUSTOM_MODEL_PREFIX` for footprint resolution and model checks (D-19, D-20).
- `kicad_lib_manager/importer/package.py`: `open_model_source` / `_open_model_file` provide the separate-model intake safety checks for D-15.
- `kicad_lib_manager/importer/applier.py`: the `install.stale_plan` pattern (re-read and hash-compare before each write) for D-16.
- `kicad_lib_manager/widgets/theme.py`: `AMBER`, `ACCENT`, `AMBER_TINT`, the spacing scale and `PRIMARY_BUTTON_QSS` for tree marks and the dialog.
- `tests/customfixtures.py` (Phase 8 synthetic `Custom/`) and `tests/gitfixtures.py` for git-backed New/Changed tests.

### Established Patterns
- Services return `Issue` lists or message lists, and `main_window.py` routes them to the log. Severity comes from the `Issue.severity`, so keep message phrasing stable.
- Long work runs in `ScanWorker(QThread)`. Never parse or call git on the GUI thread.
- `blockSignals` / `self._updating` around programmatic tree changes in `widgets/library_table.py`. The child rows must not fire `_on_sym_item_changed` selection logic.
- Layering tests (`tests/test_layering.py`, `tests/test_importer_layering.py`) enforce import direction, so the check and manufacturer modules must be Qt-free and must not import `main_window` or widgets.
- Untrusted-text caps (8 MiB, 1,000,000 nodes) apply to every KiCad file parse.
- Plain-language UI text (owner feedback 2026-10-24): map internal names to KiCad's own labels.

### Integration Points
- `library_scanner.scan_all()`: add the atomic check and the changed-item detection, and attach results to `ScanResult` (or per-library models).
- `widgets/library_table.py` `_populate_trees`: symbol and footprint child rows, markers, counts, tooltips, auto-expand, and the double-click signal to the dialog.
- `main_window.py`: the new menu action, `_on_scan_finished` log lines (D-05), opening the dialog, and a rescan after Apply.
- New dialog under `kicad_lib_manager/widgets/` (named after its class, constructed with `parent=`).

</code_context>

<specifics>
## Specific Ideas

- Manufacturer spellings found in `Custom/` today, the seed data for the table: `GCT`, `Global Connector Technology`, `Texas Instruments`, `TI`, `Memsic Inc.`, `U-BLOX`, `Abracon`, `RECOM Power`. They are spread across `Manufacturer`, `MF` and `MANUFACTURER` properties, and two libraries carry both `MF` and `MANUFACTURER`.
- Tree mock-up the owner picked:
  ```
  ▾ Custom
    ☑ Atomic_Connector      Custom   …   ⚠ 1 of 3 fail
        USB4105-GF-A                        OK
      ⚠ FFC-0.5-20                          Changed · 2 rules
        MicroSD-MEM2067                     OK
  ```
- Dialog mock-up the owner picked: ticked fix rows (`Value: "FFC20" → "FH12-20S-0.5SH"`, `Rename MF → Manufacturer`, `Manufacturer: "GCT" → "Global Connector Technology"`, `Remove "Price"`), non-fixable rows with a `Fill in…` button, and one `Preview & apply N fixes` button.

</specifics>

<deferred>
## Deferred Ideas

- Editing the manufacturer table from inside the app ("treat X as an alias of Y"). It was rejected for this phase; the table is edited in code. It could be a later quality-of-life phase.
- Restricting Footprint targets to `Atomic_Footprints` or KiCad stock is Phase 10 (LIB-06) and Phase 13 (migration), not this rule.

</deferred>

---

*Phase: 09-atomic-rule-check-and-scan-detection*
*Context gathered: 2026-10-26*
