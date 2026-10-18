# Project Research Summary

**Project:** KiCad Part Importer (extension of the PySide6 KiCad Library Manager)
**Domain:** Vendor-package part importer (Ultra Librarian, SnapEDA, SamacSys/CSE zips and loose files) writing into a personal `Custom/` KiCad library submodule
**Researched:** 2026-10-18
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is a single-user desktop tool that turns a vendor download into a correctly named, correctly linked part in the `Custom/` submodule. Tools in this space either write straight into the library (fast to build, and the source of most "my library got corrupted" reports) or use a plan/apply pipeline. This project's constraints (preview before any write, per-conflict overwrite/rename/skip, atomic writes, confirmed commits) match the plan/apply shape. Recommendation: detect and parse into a normalised candidate, build a pure `ImportPlan` that drives both preview and install, let the user edit options and re-plan, then apply mechanically with backups and rollback, then rescan, regenerate tables if a library was created, and commit only the touched paths.

The stack adds zero runtime dependencies. The core is an in-repo lossless S-expression tokenizer that edits by byte-span splicing and never re-serialises a file; stdlib `zipfile` read selectively into a temp staging directory; `subprocess` calling the `git` CLI with explicit pathspecs; and an `os.replace`-based atomic write helper. Third-party parsers were measured and rejected: kiutils silently drops KiCad 8/9 tokens such as `(hide yes)` and `exclude_from_sim`, and sexpdata loses formatting. The user's `kicad-cli` is an optional validator and normaliser, not a requirement.

Main risks are integrity risks for the curated libraries: mixed KiCad file-format generations (the UL sample is `20211014`; repo libraries range from `20211014` to `20241209`), sub-symbol and `extends` renames, footprint filename/internal-name drift, 3D model association (the UL footprint has no `(model)` block and the STEP name is unrelated), zip-slip and extraction into the repo (the scanner would then list vendor folders as libraries), and git commits on the detached-HEAD `Custom` submodule. Each has a concrete prevention in the phase plan. The existing regex-based table and scanner code has known data-loss defects and must be hardened on the new foundation before the importer ships.

## Key Findings

### Recommended Stack

Zero new runtime dependencies. Python 3.10+ floor (venv runs 3.14.4); PySide6 pinned `==6.12.0`. Dev-only: `pytest` 9.1.x and `pytest-qt==4.5.0` (verified together with PySide6 6.12.0 offscreen). Add `requirements.txt`, `requirements-dev.txt`, and `pyproject.toml` (pytest config, `qt_api = "pyside6"`).

- **In-repo `sexpr.py`** (about 150-200 lines, `re` only): parse to nodes with `(start, end)` offsets; edits are back-to-front splices. The only option that leaves untouched bytes untouched. Also replaces the table-generator regex.
- **`zipfile`** (stdlib): `infolist()`, classify by suffix and content, read with a hard byte cap, write only to a `tempfile.mkdtemp()` staging dir under generated names. Never `extractall`.
- **`subprocess` + `git` CLI**: list argv, no shell, `GIT_TERMINAL_PROMPT=0`, explicit pathspecs. GitPython rejected (maintenance mode, still needs git); pygit2 rejected (Python 3.11+, native, skips hooks).
- **`os.replace` atomic write**: temp file in the same directory, `flush` + `fsync`, `os.replace` with short retry on `PermissionError` (WinError 5 when held open without delete-sharing). Do not use `NamedTemporaryFile(delete=True)` on Windows. Do not add `filelock` (KiCad does not lock library files).
- **`kicad-cli` (optional, under KiCad `bin/`)**: `sym upgrade --force` as load-check/normaliser on a temp copy; `fp upgrade` only on a staging `.pretty` containing only the incoming footprint (it rewrites every footprint in a directory and assigns new UUIDs). Skip silently if absent.

Rejected: kiutils (writes), sexpdata, kicad-skip, kicad-python/kipy (needs a running PCB editor, no symbol API).

### Expected Features

**Must have (table stakes):**
- Zip or folder open; extension- and content-driven discovery of `.kicad_sym`, `.kicad_mod`, `.step/.stp/.wrl` at any depth; junk filtering (`.html`, `.txt`, `__MACOSX`, Altium/Eagle dirs)
- Clear rejection of legacy formats (`.lib`, `.dcm`, KiCad 5 `.mod`, UL `KiCAD/` v5 export) with "re-download as KiCad v6+"
- Safe archive reading (zip-slip, size and ratio caps, no symlinks)
- Real S-expression editing: symbol insert/replace, rename (incl. `_u_s` sub-symbols and `extends`), footprint edit, model insert/rewrite
- Selection when a package holds several symbols, footprints or models
- Target library: existing `Custom/` library or new `.kicad_sym` + `.pretty` pair, with editable `<Type>_<SubCategory>_<Manufacturer>` suggestion
- Preview of everything that will be written (names, Footprint field, model path, conflicts, warnings, format versions)
- Per-conflict overwrite / rename / skip, including the flat `3DModels/`; rename propagates everywhere
- Symbol `Footprint` set to `<Lib>:<FP>` automatically; Value, Datasheet, MPN, Manufacturer, Description editable
- Transactional install with rollback; post-write verification (re-parse, footprint resolves, model file exists)
- Rescan and table regeneration when a new library is created; log panel messages per action
- Git: confirm, commit only touched paths in `Custom/`, bump parent gitlink, never push

**Should have (differentiators):**
- Naming-convention-aware library suggestion (no surveyed tool does this)
- Pin/pad cross-check; cross-library duplicate-name warning (both cheap, v1.x)
- `kicad-cli` normalise/load check (v1.x, after version policy decided)
- Drag-and-drop, remembered folder, "latest zip in Downloads" (v1.x)
- Provenance in the commit message (vendor, original filename, date)

**Defer (v2+):** SVG preview via `kicad-cli export svg`; legacy `.lib`/`.dcm` conversion; separate STEP attachment (already deferred; loose-files mode covers it); hidden provenance property on the symbol.

**Anti-features (do not build):** watch-folder auto-import; EasyEDA/LCSC or MPN search; silent overwrite default; batch/multi-zip queue; restyling symbol graphics; `${KIPRJMOD}`/relative path variable options; `.step.gz`; keeping source zips in the repo; built-in undo manager (git is the undo); push.

### Architecture Approach

Layered, strict dependency direction: presentation (PySide6) -> importer service layer (Qt-free) -> shared foundation (`sexpr`, `kicad_files`, `fsutil`, `models`) -> existing services (`library_scanner`, `table_generator`) -> persistence (`Custom/`, git, KiCad config). `sexpr.py` and `kicad_files.py` sit at the package top level because the scanner and table generator also consume them. The `importer/` subpackage holds `package.py`, `candidate.py`, `adapters/` (registry: generic extension-based locator plus per-vendor quirks), `naming.py`, `planner.py` (pure `build_plan(candidate, options, layout) -> ImportPlan`), `plan.py`, `applier.py`, `gitops.py`, and `layout.py` (`RepoLayout` for `Custom/Symbols`, `Custom/Footprints`, `Custom/3DModels`). A generic `workers.py` `TaskWorker(QThread)` replaces copy-pasted workers, with a busy guard in `MainWindow`.

Key patterns: parse for navigation, splice for mutation; plan carries content and apply is dumb; options in, plan out on each edit (debounced); adapter registry over a generic locator; structured `Issue(severity, code, text)` results instead of substring-classified strings.

### Critical Pitfalls

1. **Old-format symbol spliced into a newer-format library.** Header versions change interpretation (`(id N)` stops being saved from 20220914; `~` Datasheet semantics change 20250318). Never rewrite a target's `(version)` header; compare versions as integers; show source vs target versions in preview; new libraries take the header from the installed KiCad or the highest version in `Custom/`.
2. **Regex or `str.replace` on S-expressions.** Picks the wrong `Footprint` property, breaks on strings containing parens, rewrites Datasheet and keyword fields. Prevention: one tokenizer, span splices, re-tokenise after every edit, round-trip identity over every repo KiCad file.
3. **Symbol rename missing sub-symbols and `extends`.** Units are `<Name>_<u>_<s>` children (UL sample: `CSD85301Q2_1_1`, `_2_1`). Rename only exact `OLD_int_int` children and `(extends "OLD")` references; never substring-replace.
4. **Illegal or hostile names.** `/` and `:` break LIB_IDs and filenames; Windows reserved names; traversal via names from file content. One `sanitize_name` used everywhere; show original vs sanitised in preview; keep `.` and `-` (existing practice uses them); check case-insensitive uniqueness.
5. **Footprint filename, internal name and references drifting.** Filename must equal `(footprint "NAME")`. A rename updates the file, the footprint node, `Footprint` as `Lib:NAME`, `ki_fp_filters`, and `fp_text value`. Post-install, resolve every `Lib:Name` and fail loudly on a miss.
6. **3D model association and path errors.** UL STEP sits at zip root with an unrelated name and the footprint has no `(model)` block: find the model anywhere in the archive and insert a node (identity transform, "orientation unverified" warning). Write `${CUSTOM_3DMODEL_DIR}/<file>`, keep original extension case, dedupe by SHA-256 (identical = reuse, different = conflict), warn if `CUSTOM_3DMODEL_DIR` is unset in `kicad_common.json`.
7. **Zip-slip, extraction into the repo, zip bombs.** Extracting under the repo makes the scanner (which `rglob`s everything) list vendor folders as libraries. Read members into a temp staging dir outside the repo with generated names; enforce count, size and ratio limits; reject symlinks, `..`, absolute and drive-letter names.
8. **Git on a detached-HEAD submodule.** `Custom` is currently `HEAD (no branch)`, and its gitdir is worktree-private (`.git/worktrees/Kicad_Libraries-importer/modules/Custom`). A commit there is on no branch and may not be visible from the main checkout. Detect with `git -C Custom symbolic-ref -q HEAD`, require a decision before committing, stage explicit paths only, never `add -A` or `commit -a`.
9. **Line-ending churn.** Index is LF, working tree CRLF (`autocrlf=true`, no `.gitattributes`). Read/write with `newline=""`; convert inserted fragments to the target's EOL; verify no whole-file diff. Consider `.gitattributes` as its own deliberate commit.
10. **Non-atomic multi-file writes and Windows locks.** Validate everything in memory first; write footprint and model before the symbol library; restore pre-images on failure; catch `OSError` in services, not Qt slots.

## Implications for Roadmap

The three researchers proposed compatible but differently cut phase orders (ARCHITECTURE: six phases; PITFALLS: eight; STACK and FEATURES: foundation, then importer, then git). The reconciled order below keeps the shared dependency logic.

### Recommended phase order

**Phase 1: Foundation (test harness, atomic IO, S-expression layer)**
- Rationale: everything structural depends on the tokenizer; three clients consume it. Harness and round-trip corpus must exist before any writer.
- Delivers: `requirements.txt` / `requirements-dev.txt` (pinned PySide6); `pyproject.toml` pytest config; `tests/conftest.py` setting `QT_QPA_PLATFORM=offscreen`; `sexpr.py` (spans, `apply_edits`, `quote()`, balance validation, `SexprError(line, col)`); `fsutil.py` (`atomic_write_text/bytes`, EOL sniffing, `safe_join`, numbered backup); `kicad_files.py` read side; round-trip identity over every `Custom/` file, with Wurth libraries as stress corpus.
- Avoids: Pitfalls 2, 11, 12, 15, 18, 20.

**Phase 2: Harden existing code on the new foundation**
- Rationale: importer reuses table, scanner and write paths that carry known data-loss defects; PROJECT.md gates the importer on this.
- Delivers: `table_generator` merges by span through `LibTable`, carries unknown children verbatim, warns on unclassifiable ones; numeric KiCad version sort (`10.0` over `9.0`); no overlapping scans (busy guard); `OSError` caught in Generate and logged; generated values escaped; atomic writes for tables and `kicad_common.json` with backup first; table entries keyed by unique nickname; `${KIPRJMOD}` model paths flagged (report only).
- Avoids: Pitfalls 14, 15, 17.

**Phase 3: Package intake, naming and target library (headless)**
- Rationale: adapter and naming decisions feed the plan. UL is the only real sample, so UL and loose-files first; the registry lets SnapEDA and SamacSys slot in later.
- Delivers: `importer/package.py` (safe staging, limits, junk filter); `candidate.py`; `adapters/base.py` generic locator; `ultralibrarian.py` (finds `KiCADv6/*.kicad_sym`, `footprints.pretty/*.kicad_mod`, and root `DLV0006A.stp`); `loose.py`; legacy rejection with log line; `naming.py` (`sanitize_name`; library suggestion from existing `Custom/` prefixes plus datasheet host, e.g. `ti.com` -> `TI`); `layout.py` (`RepoLayout`).
- Avoids: Pitfalls 4, 8, 9, 14.

**Phase 4: Transform, plan and apply (headless correctness core)**
- Rationale: where correctness lives; testable without Qt. Needs the version policy decided (see decisions) and a short spike.
- Delivers: `kicad_files` write side (insert/replace symbol; rename symbol with `_u_s` and `extends`; rename footprint across all five places; set `Footprint`; set-or-create fields in the file's own style; insert or rewrite `(model)`); `plan.py` and `planner.py` (pure; final text; operations with `base_sha256`; conflicts with stable ids; issues); `applier.py` (precondition check, backup outside `Custom/`, staged writes, undo log, rollback); post-install verification; double-import is a no-op.
- Test core: UL sample end to end on a `tmp_path` copy of `Custom/`; `20211014` symbol into `20241209` library; multi-unit rename; failure injected on second write leaves no dangling symbol.
- Avoids: Pitfalls 1, 3, 5, 6, 7, 16, 19, 24, 26.

**Phase 5: Import UI and post-install**
- Delivers: `workers.py` generic `TaskWorker`; `widgets/import_dialog.py` (Source > Review > Done) and `import_review.py` (editable preview, live re-plan with ~200 ms debounce, conflict resolver showing before/after); "Import Part..." action with busy guard; post-install rescan preserving selection by `(source, nickname)` and selecting the new library; table regeneration only when a new library was created; "close and reopen KiCad editors" notice; KiCad-running warning.
- Avoids: Pitfalls 13, 26; UX pitfalls (silent "no 3D", commit dialog without file list).

**Phase 6: Git commit step**
- Rationale: most side-effectful and environment-sensitive; last because it consumes `ApplyResult.touched_paths` and a failed install must never reach it.
- Delivers: `gitops.py` plan/run (preflight: HEAD state, `index.lock`, user config, staged-changes check; `git add -- <paths>`, `git commit -- <paths>`, then parent `git add -- Custom` and commit; never push); `widgets/commit_dialog.py` showing branch or DETACHED, file list, editable message in repo style; tests with temp repos and a temp detached submodule.
- Avoids: Pitfalls 10, 11 (diff check); anti-pattern 7.

**Phase 7: Additional vendor adapters (SnapEDA, SamacSys/CSE)**
- Rationale: blocked on real downloads, not architecture. One small phase per vendor.
- Delivers: `snapeda.py` and `samacsys.py` adapters with fixtures from real downloads in `downloaded_examples/` (synthetic fixtures marked provisional until then); SamacSys legacy `.lib`/`.dcm` detection; `(at (xyz))` legacy model offset handling if a legacy fixture appears.
- Avoids: Pitfalls 8, 18.

### Phase ordering rationale

- Foundation first: three services depend on the tokenizer and atomic IO; round-trip corpus is the gate for every write.
- Hardening before importer: importer inherits table/scan/write defects; the nickname-keying bug is triggered by creating a new library.
- Headless plan/apply before UI: correctness is testable without a display; preview must render the same `ImportPlan` the applier executes.
- Git last: most side-effectful; depends on install success.
- Vendor adapters last: fixtures are the blocker.

### Research flags

Needs deeper research or a spike during planning:
- **Phase 4 (version policy):** verify KiCad 9/10 loads a `20211014` `(id N)` symbol spliced into a `20241209` library, and `kicad-cli sym upgrade` behaviour on a mixed file. STACK probe says mixed loads on KiCad 9.0.9 (HIGH for that version only); KiCad 6/7 readers untested (MEDIUM). Verify legacy `(at (xyz))` model offset units only if a legacy fixture appears.
- **Phase 6 (git in worktree):** spike early. `Custom` is detached, gitdir is worktree-private, and `commit -- Custom` behaviour under the owner's hooks is unverified.
- **Phase 7 (SnapEDA, SamacSys):** real layouts unverified. SnapEDA may ship no 3D; SamacSys may ship legacy files alongside v6 files. Needs real downloads.

Standard patterns (skip research-phase):
- **Phase 1:** span-based tokenizer, `os.replace` atomic writes, `zipfile` selective reads (local probes done).
- **Phase 2:** scoped fixes against known defects in CONCERNS.md.
- **Phase 5:** Qt worker and dialog patterns already in the codebase (`ScanWorker`).

## Decisions Needed During Requirements

1. **Canonical Manufacturer and MPN property names.** Existing `Custom/` symbols are inconsistent: `MF`, `MP`, `MANUFACTURER`, `Manufacturer_Name`, `Description` (x18), `MANUFACTURER` (x9), `MF` (x7). The UL sample has neither Manufacturer nor MPN. Pick the names the importer writes; decide whether non-conforming existing symbols are left alone (recommended) or migrated.
2. **3D-model filename conflict handling in flat `Custom/3DModels/`.** Proposed: identical SHA-256 at the same name is reuse (auto-resolved, no-op); different content is per-conflict overwrite / rename / skip. Confirm, and confirm default model filename (part number plus original extension, case preserved, or footprint name).
3. **Format-version merge policy and `kicad-cli` role.** Options: (a) splice verbatim and warn on mismatch (STACK default; loads on KiCad 9.0.9); (b) normalise incoming file with `kicad-cli sym upgrade` first when a KiCad install is detected (PITFALLS and ARCHITECTURE preference); (c) upgrade the whole target library (rejected by all researchers: noisy diff). Decide whether normalisation is default-on or opt-in. Recommended: never change the target's header version.
4. **Detached-HEAD `Custom` submodule in the commit step.** Options: refuse to commit until on a branch; offer `git switch main` only if the detached commit is an ancestor of `main`; or create a named branch. Also decide where the commit should be visible (worktree module gitdir vs main checkout's `Custom`).
5. **Legacy `${KIPRJMOD}/Custom/3DModels/...` paths in existing footprints** (five footprints). Options: report only (recommended); normalise in a separate explicit cleanup commit; or leave untouched and exclude from warnings.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Checked against PyPI metadata and hands-on probes on the real UL zip, `Custom/` libraries and KiCad 9.0.9. |
| Features | MEDIUM | UL layout HIGH (real sample). SamacSys/CSE MEDIUM (three agreeing third-party importers, no sample). SnapEDA LOW-MEDIUM (official docs only). |
| Architecture | HIGH | Derived from actual code and real sample. KiCad escape rules and version semantics MEDIUM (thin dev docs). |
| Pitfalls | MEDIUM-HIGH | Local facts HIGH. KiCad version history and caching MEDIUM. Several items INFERRED and need a fixture or KiCad round trip. |

**Overall confidence:** MEDIUM-HIGH. Architecture and UL path are well grounded. SnapEDA/SamacSys support, KiCad 9/10 mixed-version behaviour, and worktree git behaviour are the weak points.

### Gaps to Address

- **Resolved fact (not an open discrepancy):** the UL sample contains `DLV0006A.stp` (192 KB) at the zip root, outside `KiCADv6/`; footprint `DQK0006B.kicad_mod` has no `(model)` node. Importer must find the model anywhere in the archive and insert a model node. A separate "no STEP" fixture is still needed to test the warning path. PROJECT.md corrected in `23193e5`.
- **SnapEDA and SamacSys layouts:** no real samples. Handle in Phase 7; owner should download one sample of each into `downloaded_examples/`.
- **KiCad parser error text** for sub-symbol prefix mismatch, KiCad's escape set for `quote()`, and how the symbol editor reacts to an external change to an open library: unverified. Test with a KiCad round trip in Phase 4.
- **KiCad 10:** `kicad-cli` results are from 9.0.9 only.
- **Legacy `(at (xyz))` model offsets (inches in KiCad 5):** unverified; relevant only if a legacy fixture is accepted.
- **Symbol `extends` in vendor files:** none in the sample or in `Custom/`. Planner should detect and refuse, or import the parent too. Decide in Phase 4.
- **Worktree submodule behaviour:** `git commit -- Custom` in the parent under the owner's hooks and worktree-private module is unverified (Phase 6 spike).
- **Wurth submodule not checked out in this worktree:** performance on multi-MB libraries unmeasured. Largest `Custom/` symbol file is ~49 KB.
- **Legal:** check redistribution terms before committing vendor fixtures into the public `Custom/` repo. Prefer trimmed or synthetic fixtures.

## Sources

### Primary (HIGH confidence)
- `downloaded_examples/ul_CSD85301Q2.zip` (real Ultra Librarian sample, inspected with `zipfile`)
- `Custom/` submodule census: versions, model paths, name/file invariant, `core.autocrlf`, `git ls-files --eol`, `symbolic-ref` state
- Existing code: `kicad_lib_manager/{main_window,library_scanner,table_generator,models,settings}.py`; `.planning/codebase/CONCERNS.md`
- `.planning/PROJECT.md` (corrected in `23193e5`)
- Local probes (STACK): kiutils 1.4.8 and sexpdata 1.0.2 round-trip diffs; tokenizer timings; `kicad-cli 9.0.9 sym upgrade` / `fp upgrade` on mixed-format merges; `os.replace` on open and read-only files (Windows 11); pytest-qt 4.5.0 with PySide6 6.12.0 offscreen

### Secondary (MEDIUM confidence)
- KiCad dev docs S-expression pages: https://dev-docs.kicad.org/en/file-formats/sexpr-intro/ , https://dev-docs.kicad.org/en/file-formats/sexpr-symbol-lib/ , https://dev-docs.kicad.org/en/file-formats/sexpr-footprint/
- KiCad 9.0 CLI reference: https://docs.kicad.org/9.0/en/cli/cli.html
- KiCad symbol-library version history: https://docs.kicad.org/doxygen/sch__file__versions_8h_source.html
- Impart Import-LIB-KiCad-Plugin: https://github.com/Steffen-W/Import-LIB-KiCad-Plugin
- component-importer-for-kicad: https://github.com/robertxdx/component-importer-for-kicad
- AxxAxx KiCad_scripts: https://github.com/AxxAxx/KiCad_scripts
- Ultra Librarian KiCad 6+ help: https://app.ultralibrarian.com/content/help/kicad-6_0.htm
- SnapMagic KiCad v6+ guide: https://support.snapmagic.com/en/articles/5995733-how-to-import-into-kicad-v6-and-later
- SamacSys notes: https://www.samacsys.com/?p=318527 , https://www.samacsys.com/?p=321860
- KiCad forum threads cited in PITFALLS.md (names with `/` and `:`, prefix-less Footprint fields, stale `fp-info-cache`, 3D path problems)
- GitPython README: https://github.com/gitpython-developers/GitPython

### Tertiary (LOW confidence, needs validation)
- SnapMagic download playbook: https://wiki.adom.inc/api/pages/adom/chip-fetcher/files/playbooks/snapmagic.md
- parts2kicad forum thread: https://forum.kicad.info/t/parts2kicad-script-for-importing-from-samacsys-mouser-farnell/66224
- Averyy/pcbparts-mcp fixture (mock data): https://github.com/Averyy/pcbparts-mcp

---
*Research completed: 2026-10-18*
*Ready for roadmap: yes*
