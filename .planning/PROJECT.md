# KiCad Part Importer

## What This Is

A part importer added to the existing PySide6 KiCad Library Manager (`kicad_lib_manager`). The user browses to a component package downloaded from Ultra Librarian, SnapEDA, SamacSys / Component Search Engine, or a folder of loose files. They pick or create a target library in the `Custom/` submodule, review a preview, and click install. The importer extracts the package, places the symbol, footprint and 3D model in the right places, and rewrites names and paths to the repo's conventions. It then refreshes the library tables and, after confirmation, commits the part in the `Custom` submodule. It is a personal tool for the repo owner, replacing the manual copy, paste and path-fixing routine described in CLAUDE.md.

## Current State

**Shipped:** v1.0 Part Importer (2026-10-24, closed 2026-10-25). See `.planning/MILESTONES.md` and `.planning/milestones/v1.0-ROADMAP.md`.

- Ultra Librarian, SnapEDA, SamacSys/CSE and loose-file packages import end to end into `Custom/`: intake, editable preview, per-item conflicts, transactional install, table refresh and a confirmed path-limited commit.
- About 15.2k lines of application Python and 29.5k lines of tests (1966 passing). 21 tests depend on the environment and fail on the current workstation (see Active).
- KiCad 10 is now installed on the workstation and is the reference version. KiCad 9 is no longer a target (owner, 2026-10-25).

## Next Milestone Goals

Not yet defined. Run `/gsd-new-milestone`. Candidates carried forward:
- Make the test suite independent of the live `Custom/` contents and retarget the kicad-cli tests at KiCad 10.
- Re-test the deferred KiCad 10 and case-sensitive-folder UAT items (backlog 999.1, 999.2).
- Close the open Phase 5/6 review and UI-review findings listed under Active.
- v2 candidates: SVG preview via `kicad-cli export svg` (PREV2-01), KiCad 5 conversion (FMT2-01), provenance property and `MF`/`MP` field migration (META2-01/02).

## Core Value

A downloaded vendor package ends up as a correctly named, correctly linked part in the right `Custom/` library, with the symbol's Footprint field pointing at `<Lib>:<FP>` and the 3D model at `${CUSTOM_3DMODEL_DIR}/<file>.step`, without hand-editing any KiCad file.

## Requirements

### Validated

<!-- Inferred from the existing codebase (see .planning/codebase/). -->

- ✓ Scan the repo for symbol libraries (`.kicad_sym`) and footprint libraries (`.pretty/`), grouped by source (Custom, WurthElektronik) — existing
- ✓ Parse each symbol's footprint references and cross-check them against the repo and KiCad's default footprint libraries, with warnings for missing ones — existing
- ✓ Check 3D model paths referenced in `.kicad_mod` files — existing
- ✓ Auto-detect the KiCad install and user config directory, and prompt for the footprints folder if they aren't found — existing
- ✓ Two-column Symbols | Footprints tree, where symbol selection drives footprint selection per source — existing
- ✓ Generate `sym-lib-table` / `fp-lib-table`, merging in existing external entries, with numbered paired backups and restore — existing
- ✓ Write `KICAD_LIB_GITHUB` and `CUSTOM_3DMODEL_DIR` into KiCad's `kicad_common.json` — existing
- ✓ Background scan on a QThread, a colour-coded log panel, Rescan (Ctrl+Shift+R), and persisted settings (QSettings) — existing
- ✓ Dependency manifest with pinned PySide6 (`requirements.txt` / `requirements-dev.txt`) — Phase 1
- ✓ Headless pytest harness (offscreen Qt, strict markers), run bare from the repo root — Phase 1
- ✓ Lossless S-expression layer: every repo `.kicad_sym`, `.kicad_mod` and lib table round-trips byte-identically; edits change only the targeted span and keep CRLF/LF — Phase 1
- ✓ Atomic write helper (temp file + `os.replace`, read-only pre-check, locked-file retry) and `<name>_backup_<N>` backup helper in `fsutil.py` — Phase 1
- ✓ Table merge keeps every external entry whatever its layout; entries it can't classify are kept verbatim with a warning (HARD-01) — Phase 2
- ✓ Locked or read-only tables during Generate log one error per file and leave the UI consistent (HARD-02) — Phase 2
- ✓ `kicad_common.json` is backed up, written atomically, and only `environment.vars` changes (HARD-03) — Phase 2
- ✓ KiCad version directories sorted numerically, so `10.0` wins over `9.0` (HARD-04) — Phase 2
- ✓ No overlapping scans: one guarded `_start_scan`, with controls disabled while a scan runs (HARD-05) — Phase 2
- ✓ Generated S-expression values are escaped (HARD-06) — Phase 2
- ✓ Rescan keeps the current selection; pre-selection from the tables happens only at startup (HARD-07) — Phase 2
- ✓ Same-nickname libraries in different sources are reported as a collision and kept distinct in the UI (HARD-08) — Phase 2
- ✓ Legacy `${KIPRJMOD}/Custom/3DModels` paths rewritten to `${CUSTOM_3DMODEL_DIR}` in one Custom commit; the scanner warns about any other model path (HARD-09) — Phase 2
- ✓ Legacy `generate_lib_tables.py` CLI removed; issues routed by severity instead of message substrings — Phase 2
- ✓ A vendor package opens as a `.zip` or a folder of loose KiCad files, read in place or staged outside the repo, never written into it (INTK-01) — Phase 3
- ✓ Ultra Librarian zips are recognised and their symbol, footprint and 3D model found at any depth, including a root-level STEP with an unrelated name (INTK-02) — Phase 3
- ✓ KiCad 5-only packages are rejected with a "re-download as KiCad v6+" message (INTK-05) — Phase 3
- ✓ Hostile packages are refused or skipped safely: zip slip, absolute names, symlinks, zip bombs, corrupt members, and oversized or string-heavy KiCad text bounded in memory (INTK-06) — Phase 3
- ✓ A `<Type>_<SubCategory>_<Manufacturer>` library name is suggested from existing `Custom/` libraries and part info (LIB-01; editing arrives with the Phase 5 preview) — Phase 3
- ✓ Symbol, footprint and file names are sanitised, with original and sanitised names both reported (LIB-03) — Phase 3
- ✓ Symbol merged into the target `.kicad_sym` S-expression-aware: other symbols and the header stay byte-identical, renames follow sub-symbols and `extends` (INST-01, INST-02) — Phase 4
- ✓ Footprint copied into the target `.pretty/`; filename, internal name, value, symbol Footprint field `<Lib>:<FP>` and `ki_fp_filters` agree (INST-03) — Phase 4
- ✓ 3D model copied to `Custom/3DModels/<MPN>.<ext>` (same SHA-256 reused) and linked as `${CUSTOM_3DMODEL_DIR}/<file>`, rewriting or inserting the `(model ...)` block (INST-04, INST-05) — Phase 4
- ✓ Packages with no 3D model install without one and warn (INTK-08) — Phase 4
- ✓ A new library creates the matching `.kicad_sym` + `.pretty/` pair; an existing library header is never changed (LIB-02 install side; choosing in the UI arrives with Phase 5) — Phase 4
- ✓ Install is one transaction: app-data backups, ordered atomic writes, verify, and rollback on any failure or exception; a target changed after planning is refused as stale; a second identical install is a no-op (INST-06..INST-09) — Phase 4
- ✓ Post-install warnings for a name found in another library and for pin/pad mismatches (POST-03, POST-04) — Phase 4
- ✓ Import Part dialog (File > Import Part..., Ctrl+I, or drop one zip/folder on the main window) opens one Ultra Librarian zip or loose-files folder per session; the newest Downloads zip and the last folder are offered but never opened without a click (UX-01, UX-02) — Phase 5
- ✓ Several symbols, footprints or models in a package are picked in the dialog (INTK-07); "nothing found" shows the package and detection reasons (Phase 4 WR-06, IN-04) — Phase 5
- ✓ Target library suggested and editable, or an existing `Custom/` library picked; a "new" badge shows a `.kicad_sym` + `.pretty` pair will be created, and placeholder names block Install (LIB-01, LIB-02 UI) — Phase 5
- ✓ Preview before any write: every file, rename, path rewrite and format/kicad-cli action, with diffs and a file content view; footprint name and Value/Datasheet/Description/Manufacturer/MPN editable, explicit clear supported, Footprint field `<Lib>:<FP>` kept in sync; preview and install share one plan (PREV-01..PREV-07) — Phase 5
- ✓ Per-conflict Overwrite / Rename / Skip with no bulk control and nothing pre-selected; Install blocked until every conflict is decided (PREV-05) — Phase 5
- ✓ After install: Result view, rescan with the library checked and current, add-only `sym-lib-table` / `fp-lib-table` entries for a new library, a Generate hint for an existing unlisted one, and a "reopen KiCad's editors" notice when KiCad is running (POST-01, POST-02, POST-05) — Phase 5
- ✓ Commit step in the Result view: shows the Custom branch, the parent repo and branch, the exact installed files and an editable message with Import-Vendor / Import-Package / Import-Date trailers; on click commits only those files in `Custom` (`commit --only`, bystander changes untouched), then only the `Custom` gitlink in the parent; detached HEAD on `main`'s history offers a plain `switch main`, otherwise refuses; never pushes, reports "Not pushed — N commits ahead" (GIT-01..GIT-05) — Phase 6
- ✓ SnapEDA and SamacSys/CSE zips open and auto-detect through the same flow as Ultra Librarian, with the vendor label, a readable Field changes section, and an `Import-Vendor:` commit trailer; a SnapEDA zip with no model installs with the "no 3D model found" warning, SamacSys other-CAD folders are skipped with one log line; real samples install and load in kicad-cli (Phase 7)
- ✓ A separately downloaded 3D model (bare STEP/STP/WRL, or a zip holding one) is added with "Add 3D model..." in the import dialog under the same intake safety checks, and installs as `Custom/3DModels/<MPN>.<ext>` linked as `${CUSTOM_3DMODEL_DIR}/<file>` (FMT2-02, G-07-2) — Phase 7
- ✓ An unusable model source (no model, failed content check, partly bad zip, read failure) is a red blocking error on the model row with Remove / Add 3D model... recovery; preview columns are user-resizable and elide; status-strip reasons carry a click hint (G-07-5, G-07-7, G-07-8) — Phase 7
- ✓ Headless pytest suite for importer logic (format detection, symbol merge, path rewriting, naming), using real downloads as fixtures, plus tests for the hardened table and parser code; real-sample tests skip when the local downloads are absent — v1.0 (1966 passing at close)
- ✓ All 54 v1 requirements (FOUND, HARD, INTK, FMT2-02, LIB, PREV, INST, POST, GIT, UX) — v1.0

### Active

**Quality**
- [ ] Tests that copy the live `Custom/` tree assume the Ultra Librarian sample part is absent. Since `Custom` commit `eecac22` (2026-10-23, CSD85301Q2 added) 14 of them fail (`test_commit_plan`, `test_install_apply`, `test_install_e2e`, `test_install_plan`). They need a fixture that does not depend on what the owner has installed
- [ ] 7 real kicad-cli tests (`test_kicad_cli`, `test_install_plan`, `test_install_e2e`) hard-code KiCad 9 output (format 20241209). The workstation now runs KiCad 10 (20251024) and KiCad 9 is no longer a target, so retarget them at KiCad 10
- [ ] Phase 5 review warnings, open and non-blocking: WR-01 misleading "already listed" text, WR-02 table write to the process cwd when Destination is empty, WR-03 one-off build can overlap Install, WR-05 GUI thread waits up to 60 s on kicad-cli, WR-06 stale `kicad_common.json` content after the confirm dialog (05-REVIEW-DISPOSITION.md)
- [ ] Help dialog styling outside the theme tokens (hard-coded colours, px font sizes) per 05-UI-REVIEW.md
- [ ] Phase 6 review findings, open and non-blocking (06-REVIEW-DISPOSITION.md): WR-01 a commit timeout is reported as "nothing committed" without checking HEAD, WR-02 parent-message preview differs from the committed text when `gitlink_old` is None, WR-03 the "finish it by hand" command uses POSIX quoting on Windows, WR-04 files identical to HEAD raise a spurious "missing" error, WR-05 a refusal leaves the panel on a stale probe; IN-01..IN-03
- [ ] Phase 6 UI review (06-UI-REVIEW.md 17/24): Commit button not styled as the primary action, "Committed" label in the parent-failed state, error/success outcomes untinted, off-scale sizes in `commit_panel.py`

### Out of Scope

- Downloading parts from vendor websites or APIs. The user downloads manually; the importer starts from a file on disk.
- Pushing to remotes. The importer commits only; pushing stays manual.
- Importing into the WurthElektronik submodule or other third-party libraries. They're upstream-owned, so imports go only into `Custom/`.
- Batch or queued imports. Decided: one package at a time.
- Non-KiCad formats inside packages (Altium, Eagle, OrCAD). Only the KiCad v6+ files are used.
- Editing symbol graphics or footprint geometry. Only names, fields and paths are changed.

## Context

- **Brownfield.** The importer extends `kicad_lib_manager/`, a layered PySide6 app with Qt-free services (`library_scanner.py`, `table_generator.py`), dataclass models, and a widgets package. See `.planning/codebase/ARCHITECTURE.md`.
- **Parsing:** the original regex parsing was replaced in v1.0 by a lossless span-splicing S-expression layer (`kicad_lib_manager/sexpr`, `kicad_files`). Edits change only their span, and every repo file round-trips byte-identically.
- **Sample data:** `downloaded_examples/` holds the committed Ultra Librarian zip plus local-only, licence-restricted SnapEDA (CAD zip and a separate 3D model zip) and SamacSys downloads. Real-sample tests skip when the local files are absent. The original UL notes follow. Sample `downloaded_examples/ul_CSD85301Q2.zip` (Ultra Librarian): It contains `KiCADv6/<timestamp>.kicad_sym`, `KiCADv6/footprints.pretty/DQK0006B.kicad_mod`, import guides, and a STEP model `DLV0006A.stp` at the zip root, outside `KiCADv6/`. Its name matches neither the footprint nor the part. The symbol file is named by timestamp, not part number. The vendor footprint has no `(model ...)` block, so the importer must be able to insert one, not only rewrite an existing path. The symbol's `Footprint` field is the bare `DQK0006B` with no `Lib:` prefix, and `ki_fp_filters` repeats the vendor footprint name.
- **Manual process being replaced** (from CLAUDE.md): download → move the `.kicad_mod` into `<Lib>.pretty/` → copy and paste the symbol into `<Lib>.kicad_sym` in the KiCad Symbol Editor → fix 3D paths to `${CUSTOM_3DMODEL_DIR}` → commit in the submodule, then update the parent repo.
- **Repo layout:** `Custom/` is a git submodule (`sylvanoMTL/kicad_custom_library`) and is also detected as a separate repo by GSD. Work happens in the worktree `Kicad_Libraries-importer` on branch `feature/part-importer`.
- **Tests and dependencies:** pinned `requirements.txt` / `requirements-dev.txt` and a headless pytest suite (offscreen Qt) since v1.0. There's still no lint config.
- **Workstation KiCad:** KiCad 10.0 and 9.0 are both installed. kicad-cli discovery picks the newest (10.0), which writes symbol format 20251024.

## Constraints

- **Tech stack:** Python 3.10+ (venv on 3.14), PySide6 6.12, stdlib only otherwise unless a dependency is clearly justified. This extends the existing app rather than starting a new one.
- **Platform:** Windows 11 is primary, with standard CPython (not MSYS2) because PySide6 requires it. Keep the existing cross-platform branches working.
- **KiCad file formats:** output must load in KiCad 6+ libraries. The reference install is KiCad 10, and KiCad 9 is no longer a test target (owner, 2026-10-25). Symbol and footprint names must match the library naming convention, and `.kicad_sym` / `.pretty` names must pair.
- **Safety:** no write without a preview first. Writes to KiCad files and the repo must be atomic or backed up. Git commits need explicit confirmation.
- **Dependencies:** a new vendor format needs a real sample download in `downloaded_examples/` before it can be built and tested (met for UL, SnapEDA, SamacSys/CSE and loose files in v1.0).

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Importer lives inside the existing Library Manager app | Reuses scanner, log panel, settings and table generation; one tool for the repo | ✓ Good — Phase 5 UAT passed |
| Support UL, SnapEDA, SamacSys/CSE and loose files in v1 | Owner uses all of them; zip layouts differ | ✓ Good — Phase 7 UAT passed on the real SnapEDA and SamacSys zips |
| Preview before every write; per-conflict overwrite/rename/skip | Avoid silent damage to curated libraries | ✓ Good — Phase 5 UAT passed |
| Library name suggested from `<Type>_<SubCategory>_<Manufacturer>`, editable | Keeps the convention without blocking edge cases | ✓ Good — Phase 5 UAT passed |
| Footprint keeps vendor name by default, editable | Package codes are often the right name; user can override | ✓ Good — Phase 5 UAT passed |
| Footprint link set automatically; other fields editable in preview | Footprint link is the most error-prone manual step | ✓ Good — Phase 5 UAT passed |
| No 3D model → install without it and warn | Keep the flow simple; models can be added later | ✓ Good — SnapEDA no-model warning verified (Phase 7 UAT) |
| A separately downloaded 3D model is added in the import dialog as a second intake source with the same safety checks; the plan contract is unchanged | SnapEDA ships the model as a separate download (bare file or zip); the Phase 7 UAT (G-07-2) reversed the earlier Out of Scope choice | ✓ Good — Phase 7 UAT tests 3, 4, 6 passed |
| An unusable 3D model source blocks Install as an ERROR; a partly bad zip is rejected as a whole; Remove clears only rejected sources | A silently ignored bad model looked like success (G-07-5, owner decisions 2026-10-24) | ✓ Good — Phase 7 UAT re-test passed |
| One package per import | Simpler review; batch not needed | ✓ Good — Phase 5 UAT passed |
| Commit in `Custom` + bump parent ref after confirmation; never push | Matches the CLAUDE.md git workflow; pushing stays a deliberate act | ✓ Good — Phase 6 UAT passed on the real repo; remote unchanged |
| Fix all High/Medium-High concerns from the codebase map | Importer builds on table/scan/write code that has known data-loss risks | ✓ Good — HARD-01..09 verified and UAT passed (Phase 2) |
| Managed table entries identified by URI tail after `${KICAD_LIB_GITHUB}/`, not by nickname | Nicknames can collide across sources; the path cannot | ✓ Good (Phase 2) |
| Scan busy guard is both disabled controls and a refusing `_start_scan` | A disabled control doesn't stop a programmatic caller (e.g. post-import rescan) | ✓ Good (Phase 2) |
| On a nickname collision, the peer whose rel_path sorts first (Custom before WurthElektronik) stays selected | Deterministic, and personal parts win | ✓ Good (Phase 2) |
| A running KiCad only warns; the `kicad_common.json` write still proceeds | Blocking would make Generate unusable while KiCad is open | — Pending |
| Headless pytest for importer and hardened logic | No tests today; parsers and merges are regression-prone | ✓ Good — harness in place, 290+ tests at Phase 1 close |
| Replace regex parsing with an S-expression tokenizer | Needed for safe symbol merge and fixes the table-merge bug | ✓ Good — span-splicing layer round-trips the whole corpus byte-identically (Phase 1) |
| Untrusted KiCad text is bounded before and during parsing: 8 MiB raw-byte cap, 1,000,000-node ceiling, and a linear windowed string scan; an over-cap file is skipped with a WARNING, never a whole-package refusal | Vendor packages are untrusted input; a single hostile file must not exhaust memory or hide the rest of the package | ✓ Good — CR-01/CR-03 closed, 8 MiB hostile strings read within 10× decoded size (Phase 3) |
| Intake never extracts into the repo: zips are staged member-by-member into a temp folder outside the repo, folders are read in place | Keeps the "no write without preview" guarantee for the whole intake step | ✓ Good (Phase 3) |
| Install is a transaction under `except BaseException`: any exception rolls back (`install.unexpected`), interrupts roll back then re-raise | A partial install in a curated library is the worst outcome; an Issue-only rollback missed exceptions (CR-01) | ✓ Good — gap closed and re-verified (Phase 4) |
| Stale-plan check held from preflight to the last write: post-gate re-check, backup copy hashed and used as the rollback pre-image, re-check before every write | kicad-cli runs between preflight and the first write; an edit there was silently overwritten (CR-02) | ✓ Good — gap closed and re-verified (Phase 4) |
| Blank preview text means "not set, keep the vendor value"; an explicit clear is a Phase 5 preview decision | A Qt line edit returns "" for untouched fields (WR-05) | ✓ Good — Phase 5: an emptied field is an explicit clear (Datasheet written empty, cleared Manufacturer skips inference, cleared MPN refused); KiCad loads an empty Datasheet (UAT) |
| kicad-cli normalises only the incoming symbol, and only when its output version equals the target header; footprints are copied as-is | Never change a library's version header; mixed versions load in KiCad 9 (D-01, D-02) | ✓ Good — loads in kicad-cli 9.0.9; KiCad 10 is now installed, re-test still open (backlog 999.1) |
| Post-install table update is add-only: one entry per table for a new library, a no-op when listed, never the tree selection; an existing unlisted library gets a Generate hint | Import must not rewrite the owner's tables or apply an ungenerated selection | ✓ Good (Phase 5) |
| The import flow never runs git; the Result view holds a hidden commit slot for Phase 6 | Commit needs its own confirmation step (GIT-01..05) | ✓ Good (Phase 5) |
| Git runs as `git --literal-pathspecs -c core.quotepath=false -C <repo>` from an allow-list with no remote subcommand, `GIT_*` env stripped, paths on stdin (`--pathspec-file-nul`), message via `-F`; owner hooks always run (no `--no-verify`, D-06) | Package-derived names are untrusted; the user's other changes and the remote must never be touched | ✓ Good — 06-SECURITY.md 26/26 threats closed (Phase 6) |
| KiCad path variables are never written silently: Generate and the post-install table update show `VAR: old -> new` and ask (default No); a git worktree or a checkout other than the configured `KICAD_LIB_GITHUB` is refused with a WARNING; no confirm callback means no write | 2026-10-21: Generate from the dev worktree repointed KiCad 10 at it; 89 WurthElektronik libraries went missing and an ERC error followed | ✓ Good (Quick 261022-gnn) |
| KiCad 10 is the reference version; KiCad 9 expectations are dropped | KiCad 10 is installed on the workstation and the owner no longer targets KiCad 9 (2026-10-25, v1.0 close) | — Pending: 7 kicad-cli tests still expect KiCad 9 output |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-10-25 after v1.0 milestone*
