# Architecture Research

**Domain:** Vendor-package part importer (Ultra Librarian / SnapEDA / SamacSys / loose files) added to an existing layered PySide6 KiCad library manager
**Researched:** 2026-10-18
**Confidence:** HIGH for the integration design (derived from the actual code and the one real sample). MEDIUM for KiCad file-format details (official docs are thin on escaping and version rules). LOW for SnapEDA and SamacSys package layouts (no fixtures yet; Ultra Librarian layout is verified from `downloaded_examples/ul_CSD85301Q2.zip`).

## Standard Architecture

### How part-import pipelines are usually structured

Tools in this space (KiCad's own import wizards, vendor plugins such as the SamacSys Library Loader and the SnapMagic plugin, EasyEDA-to-KiCad converters) fall into two camps. Plugin-style tools parse a vendor file and write straight into the library: parse, rename, write, all in one function. They are easy to build and they are the source of most "my library got corrupted" reports. The safer camp is a **plan/apply pipeline** (the same shape as `terraform plan` / `terraform apply`): detect and parse into a normalized in-memory model, compute a dry-run plan of exactly what will change, let the user edit and resolve conflicts, then apply the plan mechanically. This project's hard constraints (preview before any write, per-conflict overwrite/rename/skip, atomic writes, confirmed commits) are exactly the plan/apply shape, so adopt it explicitly:

```
detect (read-only) -> normalize -> plan (pure, re-runnable) -> user edits -> apply (dumb, atomic) -> post-install
```

Three rules make this work and are non-negotiable here:

1. **Adapters never write and never rewrite.** They only locate and describe what is in a package.
2. **The plan carries final content.** The preview and the apply step consume the same `ImportPlan` object, so what the user reviewed is byte-for-byte what is written. Do not code the preview separately from the apply.
3. **Planning is a pure function of (candidate, options, current disk state)** and is cheap enough to re-run on every keystroke in the preview. User edits change `options`, never the plan itself.

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Presentation (PySide6)                                                        │
│  main_window.py  ──opens──►  widgets/import_dialog.py  (Source > Review > Done)│
│  (menu action, post-import     ├─ widgets/import_review.py (editable preview) │
│   rescan + table regen)        └─ widgets/commit_dialog.py (git confirm)      │
│  workers.py: generic TaskWorker(QThread) wrapping any Qt-free callable         │
├──────────────────────────────────────────────────────────────────────────────┤
│ Importer service layer  kicad_lib_manager/importer/   (Qt-free, headless)     │
│                                                                               │
│  package.py      open_package(path) -> Package (safe extraction / dir view)   │
│  adapters/       detect(Package) -> ImportCandidate   (read-only)             │
│     base.py (registry, generic locator) ultralibrarian.py loose.py            │
│     snapeda.py samacsys.py (later, need fixtures)                             │
│  candidate.py    ImportCandidate / SymbolAsset / FootprintAsset / ModelAsset  │
│  naming.py       library-name suggestion, sanitising, collision-free renames  │
│  planner.py      build_plan(candidate, options, RepoLayout) -> ImportPlan     │
│  plan.py         ImportOptions, ImportPlan, Operation types, Conflict, Issue  │
│  applier.py      apply_plan(plan) -> ApplyResult  (stage, backup, undo-log)   │
│  gitops.py       plan_commit() / run_commit()  (git CLI via subprocess)       │
├──────────────────────────────────────────────────────────────────────────────┤
│ Shared Qt-free foundation  kicad_lib_manager/                                 │
│  sexpr.py        tokenizer + span-preserving tree + splice edits + quote()    │
│  kicad_files.py  KiCad-aware readers/editors built on sexpr (symbol lib,      │
│                  footprint, lib-table)                                        │
│  fsutil.py       atomic_write, numbered backup, safe_join, EOL sniffing       │
│  models.py       existing dataclasses (+ Issue/Severity)                      │
├──────────────────────────────────────────────────────────────────────────────┤
│ Existing services (hardened, then reused)                                     │
│  library_scanner.py (scan_all, find_*_libs)   table_generator.py (write_tables)│
├──────────────────────────────────────────────────────────────────────────────┤
│ Persistence / world                                                           │
│  settings.py (QSettings)   Custom/ (git submodule)   git CLI   KiCad config   │
└──────────────────────────────────────────────────────────────────────────────┘
Dependency direction: presentation -> importer -> {kicad_files, fsutil, models}
                      -> sexpr.   Nothing below presentation imports Qt.
                      importer/ never imports main_window or widgets.
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| `sexpr.py` | Lex and parse KiCad S-expressions into a tree whose nodes remember `(start, end)` offsets in the source text. Provide `apply_edits(text, edits)` splicing and `quote()` for new strings. Know nothing about KiCad semantics. | One compiled regex tokenizer, iterative tree build, ~200 lines, stdlib only |
| `kicad_files.py` | Semantic layer: `SymbolLib` (list symbols with spans, read/set property, rename symbol incl. `_1_1` unit sub-symbols, footprint refs), `Footprint` (name, model paths, rename, set/insert `(model ...)`), `LibTable` (classify `(lib ...)` children, keep unknown children verbatim). Every mutator returns `list[Edit]`, never mutates text. | Thin classes over `sexpr.Node` |
| `fsutil.py` | `atomic_write_text/bytes` (temp in same dir + `os.replace`), `backup_file` (numbered, outside the tracked tree), `safe_join` (zip-slip guard), EOL sniffing, case-insensitive name-collision check | Plain functions, used by importer and by hardened table/`kicad_common.json` writers |
| `importer/package.py` | Turn a user-chosen zip or folder into a `Package` with a real directory `root` and a file listing. Zips are extracted selectively (extension whitelist, size and count caps, no symlinks, sanitized names) into a private temp dir; folders are used in place, read-only. Owns cleanup. | `zipfile` + `tempfile.TemporaryDirectory`, context manager |
| `importer/adapters/` | `detect(package) -> ImportCandidate \| None` plus a `confidence` score. A generic extension-based locator does 90 percent of the work; vendor adapters add metadata quirks and pairing rules. Registry returns ranked matches; loose-files adapter is the fallback. | Small classes implementing a `Protocol`, registered in a list |
| `importer/candidate.py` | Normalized, vendor-independent description of what was found. Holds decoded text of symbol and footprint files and *references* (package-relative paths) to binary assets such as STEP. | Dataclasses |
| `importer/naming.py` | Suggest `<Type>_<SubCategory>_<Manufacturer>` from candidate metadata and from tokens already used by existing `Custom/` library names; sanitize for Windows; produce collision-free rename suggestions. | Pure functions |
| `importer/planner.py` | `build_plan(candidate, options, layout) -> ImportPlan`. Reads current target state fresh from disk, detects conflicts, computes final file contents via `kicad_files` edits, emits `Operation`s and `Issue`s. No side effects. | Pure function, unit-testable with `tmp_path` |
| `importer/plan.py` | Data types: `ImportOptions` (everything the user can edit), `ImportPlan`, `Operation` subtypes, `Conflict`, `Issue`. | Frozen dataclasses where possible |
| `importer/applier.py` | Execute a plan: precondition check (target hashes unchanged), backup, stage, write with `os.replace`, keep an undo log, roll back on any failure. Reports a structured `ApplyResult` with the list of touched paths. | Sequential executor, no decisions |
| `importer/gitops.py` | Dry-run the commit (`CommitPlan`: files, message, branch state, dirty-tree warnings) and execute it after confirmation: path-limited `git add` and `git commit` in `Custom/`, then path-limited commit of the `Custom` gitlink in the parent. Never pushes. | `subprocess.run([...], shell=False)`, no GitPython |
| `widgets/import_dialog.py` | Modal wizard: pick source, show candidate and editable plan, show result and offer commit. Owns an `ImportOptions` instance and re-runs `build_plan` on edit. Contains no file logic. | `QDialog` + `QStackedWidget`, calls services through `TaskWorker` |
| `main_window.py` | Adds "Import Part..." action; after a successful import: guarded rescan, re-apply selection (including the new library), optionally regenerate tables. | One new slot plus small refactors (see Integration Points) |

## Recommended Project Structure

```
kicad_lib_manager/
├── sexpr.py                 # NEW  lowest layer, no kicad knowledge
├── kicad_files.py           # NEW  SymbolLib / Footprint / LibTable on top of sexpr
├── fsutil.py                # NEW  atomic writes, backups, safe paths
├── models.py                # existing, + Severity/Issue
├── library_scanner.py       # existing, regexes replaced by kicad_files calls
├── table_generator.py       # existing, parse/merge via LibTable, atomic writes
├── settings.py              # existing, + last import folder, custom-layout overrides
├── workers.py               # NEW  generic TaskWorker(QThread); ScanWorker becomes a thin user of it
├── importer/                # NEW  Qt-free, headless-testable
│   ├── package.py
│   ├── candidate.py
│   ├── plan.py
│   ├── planner.py
│   ├── applier.py
│   ├── naming.py
│   ├── gitops.py
│   ├── layout.py            # RepoLayout: Custom/Symbols, Custom/Footprints, Custom/3DModels
│   └── adapters/
│       ├── __init__.py      # registry: ADAPTERS = [UltraLibrarian(), SnapEDA(), SamacSys(), Loose()]
│       ├── base.py          # Adapter Protocol + generic extension-based locator
│       ├── ultralibrarian.py
│       ├── loose.py
│       ├── snapeda.py       # added when a real fixture exists
│       └── samacsys.py      # added when a real fixture exists
└── widgets/
    ├── import_dialog.py     # NEW
    ├── import_review.py     # NEW  editable preview table + conflict resolver
    └── commit_dialog.py     # NEW

tests/                       # NEW  pytest, headless; no QApplication needed for services
├── fixtures/                # real vendor downloads (tiny), expected outputs
├── test_sexpr.py            # includes round-trip identity over every repo file
├── test_kicad_files.py
├── test_table_generator.py
├── test_adapters.py
├── test_planner.py
├── test_applier.py          # rollback tests using fault injection
└── test_gitops.py           # temp git repos with a temp submodule
```

### Structure Rationale

- **`sexpr.py` and `kicad_files.py` at package top level, not inside `importer/`.** They are consumed by three clients (importer, `library_scanner`, `table_generator`). Putting them under `importer/` would make the scanner depend on the importer, inverting the layering. Top level beside `models.py` keeps the rule "everything depends downward on `sexpr`/`models`/`fsutil`".
- **Two modules, not one.** `sexpr.py` is generic and small enough to test exhaustively (property-style: parse then splice-nothing must equal input). `kicad_files.py` changes whenever KiCad adds tokens; keeping it separate stops format churn from touching the tokenizer.
- **`importer/` as a subpackage while existing services stay flat.** The existing flat layout works for two service modules. The importer is eight-plus modules with an adapter plugin point, so it earns a subpackage. The boundary is enforceable by a trivial test (`importer` imports no `PySide6`).
- **`workers.py` generic.** Today `ScanWorker` is the only background job. The importer adds three more (open package, apply, git). Copying `ScanWorker` three times repeats the threading bug already documented in CONCERNS (overlapping scans). One generic `TaskWorker` plus one "busy" guard in `MainWindow` solves both.
- **`RepoLayout` in `importer/layout.py`.** The paths `Custom/Symbols`, `Custom/Footprints`, `Custom/3DModels` are a convention of the `Custom` repo (verified on disk), not of the scanner (which finds libraries anywhere). Isolate that knowledge in one frozen dataclass so it is validated once and overridable from settings.

## Architectural Patterns

### Pattern 1: Parse for navigation, splice for mutation

**What:** The S-expression parser returns nodes with `(start, end)` offsets into the original text. All modifications are expressed as `Edit(start, end, replacement)` splices applied to the original string. Nothing is ever re-serialized from the tree, except brand-new nodes built with `quote()`.
**When to use:** Every time the importer or a hardened service touches an existing KiCad file: inserting a symbol into a `.kicad_sym`, renaming a footprint, rewriting a `(model ...)` path, editing a symbol property, preserving unknown `(lib ...)` entries in a table.
**Trade-offs:** Slightly more careful code than parse-modify-dump. In exchange: minimal git diffs, CRLF and indentation of the user's files are preserved (the Custom files on disk are CRLF with mixed formats: some `version 20211014` with `(id N)` properties, others `20241209`), and tokens this tool has never heard of (future KiCad 10 additions) survive untouched. A dump-based approach (the way the `kiutils` library works, and its docs admit round-trip caveats) would normalize every file the importer touches and risk dropping unknown tokens. Do not adopt a third-party parser; the stack constraint is stdlib-only and span access is the key requirement.

```python
# sexpr.py (shape, not final code)
@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    text: str

def apply_edits(src: str, edits: list[Edit]) -> str:
    out, pos = [], 0
    for e in sorted(edits, key=lambda e: e.start):
        if e.start < pos:
            raise ValueError("overlapping edits")
        out += [src[pos:e.start], e.text]
        pos = e.end
    out.append(src[pos:])
    return "".join(out)

# kicad_files.py
class SymbolLib:
    def symbols(self) -> list[SymbolNode]: ...          # top-level only, with spans
    def insert_symbol(self, text: str) -> list[Edit]: ...  # inserts before final ')'
    def replace_symbol(self, name, text) -> list[Edit]: ...
```

Contract tests: `apply_edits(t, []) == t` for **every** `.kicad_sym`, `.kicad_mod`, `sym-lib-table`, `fp-lib-table` found in the repo; parse never raises on any real file; unterminated or unbalanced input raises `SexprError(line, col)` rather than returning a partial tree.

### Pattern 2: Plan carries content; apply is dumb

**What:** `Operation` objects hold the final bytes or text to write, plus the hash of the base file they were computed from. Preview renders diffs (`difflib.unified_diff` of base vs new). Apply replays operations.
**When to use:** All writes under `Custom/` and any KiCad file.
**Trade-offs:** Memory holds new file contents (kilobytes; STEP files are referenced as a copy-from path instead of loaded). Plans become stale if the disk changes between preview and apply, so each modifying operation records `base_sha256` and apply refuses (and tells the user to re-preview) on mismatch. This also covers "user edited the library in KiCad while the dialog was open".

```python
@dataclass(frozen=True)
class WriteText:          # create or overwrite (overwrite requires base_sha256)
    dest: Path
    text: str
    base_sha256: str | None   # None => file must not exist
    summary: str

@dataclass(frozen=True)
class CopyFile:           # 3D model
    src: Path             # inside Package.root
    dest: Path
    base_sha256: str | None

@dataclass(frozen=True)
class MakeDir:
    dest: Path

@dataclass(frozen=True)
class ImportPlan:
    operations: tuple[Operation, ...]
    conflicts: tuple[Conflict, ...]    # each has a stable id and the chosen resolution
    issues: tuple[Issue, ...]          # severity + code + text; ERROR blocks install
    new_library: bool                  # drives table regeneration
    touched_paths: tuple[Path, ...]    # drives the git commit pathspec
```

### Pattern 3: Options in, plan out (Elm-style loop)

**What:** `ImportOptions` is the single mutable piece of UI state: chosen target library (existing or new name), symbol name, footprint name, 3D filename, field overrides (Value, Datasheet, MPN, Manufacturer, Description), per-asset include flags, and `resolutions: dict[conflict_id, Resolution]`. The review widget edits options and calls `build_plan` again; it renders whatever comes back.
**When to use:** The preview step. Conflict ids must be stable across re-planning (for example `"symbol:<lib>:<name>"`, `"footprint:<lib>:<name>"`, `"model:<filename.lower()>"`), otherwise a user's earlier choices vanish when they edit another field.
**Trade-offs:** Replans are repeated disk reads of the target lib; with kilobyte to low-megabyte files that is negligible. Debounce text edits by about 200 ms. The big win is that all interesting behavior (renames cascading to `ki_fp_filters`, the Footprint property, the footprint's own name token and Value text, conflict detection) lives in one pure function with no widget in the loop.

### Pattern 4: Adapter registry over a generic locator

**What:** Only one thing differs per vendor in practice: where files live inside the archive and a few metadata quirks. So a generic locator walks `Package.root`, finds `*.kicad_sym`, `*.kicad_mod` (including inside `*.pretty/`), `*.step|*.stp`, and builds a candidate. Vendor adapters (a) recognize their layout with a confidence score, (b) apply quirks (e.g. Ultra Librarian's timestamp-named symbol file, STEP outside the `KiCADv6/` folder), (c) prefer the KiCad v6+ folder when the archive also contains legacy `.lib`/`.dcm`/Altium/Eagle files, which must be ignored.
**When to use:** All detection. Adding SnapEDA and SamacSys later is "add a class and a fixture", not a pipeline change.
**Trade-offs:** The generic locator can occasionally attach the wrong STEP when a package has several (the sample's STEP is `DLV0006A.stp` while the footprint is `DQK0006B`, so names cannot be matched by string). Resolve by: single STEP means attach it; several means ask the user in the preview (candidate carries `models: list[ModelAsset]` and the options choose one).

```python
class Adapter(Protocol):
    name: str
    def score(self, pkg: Package) -> float: ...       # 0..1, cheap, listing-based
    def read(self, pkg: Package) -> ImportCandidate: ...  # read-only

def detect(pkg: Package) -> list[tuple[Adapter, float]]:   # sorted; Loose adapter always last
    ...
```

### Pattern 5: Staged apply with an undo log (multi-file "atomicity")

**What:** A filesystem cannot give a three-file transaction, so approximate it: (1) verify all `base_sha256` preconditions and that destinations are writable; (2) copy every file that will be overwritten into a backup folder; (3) execute operations in a safe order (new files first: 3D model, footprint; the *existing symbol library last*, since it is the file whose corruption hurts most); each file via temp + `os.replace`; (4) record every completed step in an undo log; (5) on any exception, undo in reverse (delete created files, restore backups) and return a failed `ApplyResult`.
**When to use:** The apply step only.
**Trade-offs:** Not crash-proof (power loss between steps), but the backups plus git (the `Custom` repo is the real safety net) cover that. Put backups **outside** the tracked tree, for example `<repo_root>/.import_backups/<timestamp>/` (add to the parent `.gitignore`; the parent's `*_backup_*` rule does not apply inside the `Custom` submodule, so backups inside `Custom/` would be committed).

### Pattern 6: Structured results instead of message strings

**What:** New services return `Issue(severity, code, text)` and result dataclasses; the GUI maps `severity` straight to `LogPanel` levels. The existing services return `list[str]` and `main_window.py` classifies them with substring checks (`"Failed" in msg`), which is brittle.
**When to use:** Everything new; migrate `write_tables` and `sync_kicad_path_vars` when they are hardened anyway.
**Trade-offs:** Small adapter shim at the boundary for the old code until it is migrated.

## Data Flow

### Request Flow

```
[Import Part... (Ctrl+I)]            MainWindow checks no scan is running
        ↓
[Browse zip/folder] ──► TaskWorker( open_package + detect )          (worker thread)
        ↓                    ↓ safe extract to temp dir (whitelist)
        ↓              adapters.detect(Package) -> ImportCandidate   (read-only)
        ↓
[ImportDialog] holds: candidate (immutable), options (mutable), package (cleanup owner)
        ↓                                         ▲ edit field / pick resolution
        ├─► planner.build_plan(candidate, options, layout) ──► ImportPlan ─┐  (UI thread, pure,
        │       reads Custom/ target files fresh from disk                  │   re-run on every edit)
        │       kicad_files edits -> final text -> Operations + Conflicts   │
        ◄───────────────────────────────────────────────────────────────────┘
[Install] enabled only when plan.issues has no ERROR and all conflicts resolved
        ↓
TaskWorker( applier.apply_plan(plan) )      verify hashes -> backup -> stage -> os.replace
        ↓                                   (undo on failure)            (worker thread)
ApplyResult(touched_paths, issues, backup_dir)
        ↓
MainWindow: guarded rescan  ─►  re-apply selection (+ new lib)  ─► [new_library? regenerate tables]
        ↓
gitops.plan_commit(touched_paths) ─► CommitDialog (files, message, branch state) ─► user confirms
        ↓
gitops.run_commit():  Custom: git add -- <paths>; git commit      parent: git commit -m ... -- Custom
        ↓                                                          (never push)
Log "success" with commit hashes
```

### State Management

```
ImportCandidate (immutable, from adapters)
        │
        ▼
ImportOptions (the only mutable import state; owned by ImportDialog)
        │  build_plan(...)
        ▼
ImportPlan (derived, disposable; replaced on every change)
        │  apply_plan(...)
        ▼
ApplyResult ──► MainWindow (rescan, table regen)  and  gitops (commit pathspec)
```

The planner must read **fresh disk state** for the target library and must **not** reuse `MainWindow._scan_result` objects. The scan can be stale, and the existing anti-pattern (widgets and window sharing mutable `selected` flags on scan objects) should not spread. The planner only needs a tiny read-only snapshot: the existing library names in `Custom/` (for suggestions and cross-source nickname collision checks), obtained from `RepoLayout` plus a directory listing.

### Key Data Flows

1. **Symbol merge:** candidate symbol text -> options overrides become `Edit`s on the *candidate's* symbol text (Value, Datasheet, MPN, Manufacturer, Description, Footprint = `<Lib>:<FP>`, `ki_fp_filters` if present, unit sub-symbol names if the symbol is renamed) -> then one `insert_symbol` / `replace_symbol` edit against the *target library's* text -> final text in a `WriteText`. If the target library is new, create it from a header (version and generator taken from the incoming file so format and content agree) with the symbol inside.
2. **Footprint and 3D model:** footprint text -> `Edit`s for the `(footprint "NAME"` token, the filename, the matching Value `fp_text`, and the `(model "...")` path set to `${CUSTOM_3DMODEL_DIR}/<file>`. If the vendor footprint has **no** `(model` block (true for the Ultra Librarian sample even though a STEP ships in the zip), the planner *inserts* a new model block with default offset 0 / scale 1 / rotate 0 and raises a WARNING that orientation was not verified. The STEP becomes a `CopyFile` into `Custom/3DModels/`. No STEP at all: install without a model block and emit a WARNING (per PROJECT.md decision).
3. **Conflict detection:** symbol name already in target library; footprint file already in `.pretty`; model filename already in `3DModels` (case-insensitive on Windows: the repo already has both `.step` and `.STEP`); target library exists but its `.kicad_sym` / `.pretty` pair is incomplete; a new library nickname already used in another source (nicknames in the tables must be unique); target file does not parse; target file has uncommitted changes in the `Custom` repo. An identical model (same SHA-256) at the same name auto-resolves to "reuse", so re-importing the same package is a no-op rather than a conflict.
4. **Post-install table path:** only a *new* library pair changes the tables (existing libraries are already in them). `new_library` therefore decides whether regeneration is offered. Regeneration reuses `table_generator.write_tables` after a rescan with the new library's `selected` set.

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `MainWindow` -> `ImportDialog` | Construct with `repo_root`; read back an `ImportResult` (touched paths, `new_library`, `committed`) via `exec()` result or a signal | Dialog is modal. Refuse to open while a scan is running (needs the busy guard) |
| `ImportDialog` -> importer services | Plain function calls wrapped in `TaskWorker` for I/O-heavy steps; `build_plan` called directly on the UI thread | Services are Qt-free. Progress callbacks follow the existing `(msg, current, total)` convention from `scan_all` |
| `library_scanner` / `table_generator` -> `kicad_files` | Direct import | Replaces `FOOTPRINT_RE`, `MODEL_RE`, `_LIB_ENTRY_RE`. Scanner keeps its public functions and `ScanResult` unchanged, so widgets are unaffected |
| `importer` -> `library_scanner` | Optional, narrow: reuse `_in_skip_dir`-style discovery only if needed. Prefer `RepoLayout` directory listing | Avoid making the importer depend on `ScanResult` |
| `MainWindow` -> `table_generator` | `write_tables(dest, sym_libs, fp_libs)` after rescan | Refactor `_on_generate` into `regenerate_tables(dest) -> list[Issue]` callable from both the button and the post-import path |
| `importer.gitops` -> git CLI | `subprocess.run([...], cwd=custom_root, capture_output=True, text=True, shell=False, env={..., "GIT_TERMINAL_PROMPT": "0"})` | Check `git` on PATH; Windows paths via `Path`; no commit hooks bypass; no push |
| `fsutil` <- table_generator, scanner (`sync_kicad_path_vars`), applier | Direct import | One atomic-write implementation, three callers; fulfils the hardening requirement and the importer's apply with the same code |

### Required changes to existing code (enablers, in dependency order)

1. **Add `sexpr.py`, `kicad_files.py`, `fsutil.py`** (new files, no behavior change).
2. **`table_generator.parse_lib_table` / `_merge_table`** switch to `LibTable`: classify children; managed entries (URI contains `${KICAD_LIB_GITHUB}/`) are regenerated; every other child, including `(version N)` and entries with `(disabled)`/`(hidden)` flags, other `type` values or different field order, is carried over **verbatim by span**; unclassifiable children produce a warning. Expose `is_managed_entry()` publicly (removes the cross-module `_MANAGED_MARKER` import). Escape generated values with `quote()`.
3. **`library_scanner`**: footprint refs and model paths via `kicad_files`; numeric version sort for the KiCad install and config directories; `sync_kicad_path_vars` uses `fsutil.atomic_write_text` plus a backup of `kicad_common.json`.
4. **`main_window.py`**: `_start_scan()` returns early (or actions are disabled) while a worker runs; Rescan preserves selection by `(source, nickname)`; `_on_generate` wrapped to catch `OSError` and log it; slot added for import.
5. **Settings**: last import folder only. Do not persist import options.

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| git (CLI) | `gitops.py` subprocess, path-limited `add` / `commit` | Pre-checks: `Custom` is a repo, not detached HEAD, no rebase/merge in progress, show pre-existing dirty files. Never `git add -A` / `commit -a`: the working tree may hold unrelated edits. Parent commit must be path-limited to `Custom` for the same reason. Never push |
| KiCad (path variables) | Existing `sync_kicad_path_vars` | `${CUSTOM_3DMODEL_DIR}` must resolve for the model path to work; the importer should WARN if `kicad_common.json` lacks it |
| KiCad editors (open) | None possible | If the Symbol Editor has the target library open, KiCad can overwrite the merge on its next save. Mention in the Install confirmation; cannot be detected reliably |
| `kicad-cli` (optional) | Possible later validation step (`kicad-cli sym upgrade` or export on the merged library) | Not required for v1; useful as an end-to-end sanity test in the phase that proves cross-version merging |

## Build Order (dependencies between components)

```
fsutil ─┐
sexpr ──┼─► kicad_files ─┬─► [harden] table_generator, library_scanner  ─┐
tests ──┘                │                                                │
                         ├─► importer.layout, plan, candidate             │
                         │      └─► package ─► adapters(UL, loose)        │
                         │             └─► naming ─► planner ─► applier  │
                         │                                      │        │
workers.py + busy guard ─┴────────────────────────► ImportDialog ◄───────┘
                                                        │
                                              post-install (rescan, regen)
                                                        │
                                                     gitops ─► commit_dialog
                                                        │
                                           snapeda / samacsys adapters (need fixtures)
```

Suggested phase decomposition (each phase leaves the app working and shippable):

1. **Foundation: pytest scaffold, `fsutil`, `sexpr`, `kicad_files` read side.** Corpus round-trip test over all real repo files. Pin PySide6 in a manifest. Nothing else can start until the tokenizer exists. HIGH confidence on ordering.
2. **Harden existing code on the new foundation** (table merge by span, atomic writes, error catching, numeric version sort, scan guard, escaping, selection-preserving rescan). This is mandated by the project and also de-risks the importer, which will reuse the same write and parse paths. Can overlap with phase 3 once `sexpr` is stable, since they touch different files.
3. **Headless importer vertical slice: Ultra Librarian + loose files.** `package`, `candidate`, adapters, `naming`, `plan`, `planner`, `applier`, `kicad_files` write side (insert/replace symbol, rename footprint, set/insert model). Fully pytest-driven against the real sample and a temp copy of `Custom/`. Includes rollback tests (inject an exception on the second write). No Qt yet.
4. **Import UI + post-install**: generic `TaskWorker`, `ImportDialog` and review widget with live re-planning, conflict resolver, `MainWindow` integration (rescan, selection, optional table regeneration, log panel messages).
5. **Git commit step**: `gitops` plan/run, `CommitDialog`, parent ref bump. Last because it is the most side-effectful, depends on `ApplyResult.touched_paths`, and is the most environment-sensitive (git config, hooks, autocrlf).
6. **Additional vendor adapters (SnapEDA, SamacSys/CSE)**: one small phase per vendor once a real download is in `downloaded_examples/`; independent of everything else because of the adapter registry. Also decide here whether format-version mismatches need a kicad-cli normalization step.

Rationale: foundations first because three clients need them; headless importer before UI because the plan/apply core is where correctness lives and it can be tested without a display; git last because it only consumes outputs; vendor adapters last and independent because fixtures are the blocker, not architecture.

## Anti-Patterns

### Anti-Pattern 1: Regex-on-first-match for symbol merge and path rewrites

**What people do:** `re.sub(r'\(model "[^"]*"', ...)` or find the last `)` in the library and insert before it.
**Why it's wrong:** Strings may contain parentheses and escaped quotes; a symbol's unit sub-symbols repeat the parent name; nested `(symbol` nodes confuse "first match". This is exactly the failure class already documented for the table regex (CONCERNS: external entries silently dropped).
**Do this instead:** Tokenize once, locate nodes by structure and depth, and apply span edits (Pattern 1).

### Anti-Pattern 2: Parse, modify, dump the whole file

**What people do:** Load a `.kicad_sym` into an object model and serialize it back.
**Why it's wrong:** Reformats every symbol (whitespace, number formatting, `(id N)` handling), drops unknown tokens, flips CRLF to LF, and turns a one-symbol import into a whole-file git diff in a curated library.
**Do this instead:** Splice only the bytes that change.

### Anti-Pattern 3: Preview logic separate from apply logic

**What people do:** A "preview" function that describes changes in prose and an "install" function that recomputes them.
**Why it's wrong:** They drift; the user approves one thing and gets another.
**Do this instead:** One `ImportPlan` object; apply is a mechanical replay (Pattern 2).

### Anti-Pattern 4: Adapters that rewrite or install

**What people do:** Vendor handlers that fix names and copy files as they parse.
**Why it's wrong:** Mutation spreads across N adapters, cannot be previewed, and each new vendor reimplements renaming and path rewrites.
**Do this instead:** Adapters describe; the planner mutates (Pattern 4).

### Anti-Pattern 5: Planner or dialog holding live `ScanResult` / `SymbolLibrary` objects

**What people do:** Reuse `MainWindow._scan_result` to find the target library and flip `selected` flags from the importer.
**Why it's wrong:** Scan data can be stale and is shared mutable state between window and widgets (already flagged). The importer would inherit the coupling.
**Do this instead:** The importer works on disk state via `RepoLayout`; the window re-derives scan state by rescanning after the import.

### Anti-Pattern 6: Extracting the zip straight into the library

**What people do:** `ZipFile.extractall(Custom/...)` then move files.
**Why it's wrong:** Zip-slip, name collisions with Windows reserved names, partial junk left on failure, and unrelated vendor files (HTML guides, other-EDA formats) land in the repo.
**Do this instead:** Whitelist-extract to a temp directory, use `safe_join`, copy only planned files, and always delete the temp dir.

### Anti-Pattern 7: Broad git staging

**What people do:** `git add -A && git commit` in the submodule, or `git commit -a` in the parent.
**Why it's wrong:** Captures unrelated work in progress (the parent currently has an untracked `downloaded_examples/`; `Custom` may hold manual edits).
**Do this instead:** `git add -- <touched_paths>` then `git commit -- <touched_paths>`; parent: `git commit -m ... -- Custom`. Show the file list and message in the confirmation dialog.

### Anti-Pattern 8: Substring-classified log messages

**What people do:** Return strings and infer severity with `"Failed" in msg`.
**Why it's wrong:** Already causing mislabeled messages in `_on_generate`.
**Do this instead:** `Issue(severity, code, text)` (Pattern 6).

## Observations from the real sample and repo that shape the design

| Observation (verified on disk) | Design consequence |
|--------------------------------|--------------------|
| `ul_CSD85301Q2.zip` **does** contain a STEP: `DLV0006A.stp` at the zip root, outside `KiCADv6/`. PROJECT.md says "no STEP model" and the footprint indeed has no `(model` block. | Generic locator must search the whole archive, not only the KiCad folder. The planner must be able to **insert** a model block, not only rewrite an existing path. PROJECT.md context line should be corrected. |
| STEP name (`DLV0006A`) differs from footprint name (`DQK0006B`) and from the part (`CSD85301Q2`). | 3D model filename is an editable option; default suggestion is the part number (matches existing `BQ25180YBGR.step` style in `Custom/3DModels`). |
| Symbol `Footprint` property is the bare name `DQK0006B` (no `Lib:` prefix); `ki_fp_filters` and `ki_keywords` repeat vendor names. | Footprint field is always rewritten to `<Lib>:<FP>`; a footprint rename also updates `ki_fp_filters` (offer, not force). |
| Symbol file is named by timestamp (`2026-10-18_09-12-49.kicad_sym`); the symbol name inside is the MPN (`CSD85301Q2`). | Never derive names from vendor filenames; use the symbol node name. |
| Vendor files are format `version 20211014`, `(generator kicad_symbol_editor)`, properties carry `(id N)`. Custom libs are a mix of `20211014`, `20231120` and `20241209`, all CRLF. | Splice preserves the target's EOL (convert inserted text to the target's dominant EOL). Planner raises a `FORMAT_VERSION_MISMATCH` issue when source and target versions differ. Whether KiCad 9/10 accepts `(id N)` inside a newer-version file must be verified empirically (phase 3 spike). |
| No manufacturer in the sample's symbol; Datasheet URL host is `ti.com`. | `naming.py` can infer the manufacturer token from the datasheet host as a suggestion. Type and SubCategory come from tokens in existing `Custom/` library names (dropdowns) plus free text. |
| Existing footprints have both `${CUSTOM_3DMODEL_DIR}/x.step` and legacy `${KIPRJMOD}/Custom/3DModels/x.step` paths; the scanner does not flag the latter (it skips anything starting with `${`). Footprint names contain dots (`GCT_MEM2085-00-115-00-A_REV0.2`). | Importer always writes the `${CUSTOM_3DMODEL_DIR}` form. Never use `Path.stem`/`suffix` on footprint filenames; strip the `.kicad_mod` suffix explicitly. The scanner hardening is a good place to also flag `${KIPRJMOD}` model paths. |
| `Custom/` layout is `Symbols/<Lib>.kicad_sym`, `Footprints/<Lib>.pretty/`, `3DModels/`. Table URIs are therefore `${KICAD_LIB_GITHUB}/Custom/Symbols/<Lib>.kicad_sym`. | `RepoLayout` encodes this; a new library is the pair plus (via the existing generator) two table entries. |
| `Custom/` is a submodule, repo-root `.gitignore` has `*_backup_*`; `core.autocrlf` is true on this machine. | Importer backups must live outside `Custom/`; commit pathspecs must be explicit; CRLF warnings from git are expected, not errors. |
| The `WurthElektronik` submodule is not checked out in this worktree, so realistic large-library scan times could not be measured. | Tokenizer performance is a watch item (see below), not a blocker: largest Custom symbol file is about 49 KB. |

## Scaling Considerations

This is a single-user desktop tool, so "scale" means file sizes and library counts, not users.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| Current (10 symbol libs, about 50 KB max) | Everything synchronous except scan, open-package, apply, git (workers). Re-plan on UI thread |
| A very large third-party library (Wurth, multi-MB symbol files) | Regex-based tokenizer is C-speed per token; building a full tree for multi-MB files in pure Python may cost seconds. Give `kicad_files` a fast path for the scanner (only depth 2 and 3 matter: `symbol` -> `property "Footprint"`), or lex without building a tree. Measure when the submodule is available. |
| Many imports per session | Not in scope (one package per import). Planner remains pure, so batch would be a loop over candidates later without redesign |

### Scaling Priorities

1. **First bottleneck:** scanner time on large vendor libraries once regexes are replaced by tree parsing. Mitigate with the depth-limited fast path and keep the existing `ScanWorker` thread.
2. **Second bottleneck:** preview re-plan latency if a target library becomes large. Cache the parsed target by `(path, mtime, size)` inside the planning call chain.

## Open Questions for phase-level research

- Real SnapEDA and SamacSys/CSE archive layouts (blocked on fixtures; LOW confidence until then). Expect SamacSys archives to carry legacy `.lib`/`.dcm` alongside KiCad v6 files, and SnapEDA symbols to arrive with a different `generator` and often a pre-baked 3D model path.
- Does KiCad 9/10 load a `(id N)`-style 20211014 symbol appended into a 20241209-header library? Verify with the sample and the real KiCad install (possibly via `kicad-cli`). If not, the planner must either refuse or normalize.
- Symbol `(extends "Parent")` in vendor files: the sample has none, and no existing Custom library uses it; the planner should detect it and refuse or import the parent too.
- Behavior of `git commit -- <path>` for the gitlink in the parent under the user's hook configuration; verify in `test_gitops.py` with temp repos.

## Sources

- Project code read directly: `kicad_lib_manager/{main_window,library_scanner,table_generator,models,settings}.py`, `.planning/codebase/{ARCHITECTURE,STRUCTURE,CONCERNS}.md`, `.planning/PROJECT.md` (HIGH)
- Real sample inspected with `python -I` + `zipfile`: `downloaded_examples/ul_CSD85301Q2.zip` members, `readme.txt`, `.kicad_mod`, `.kicad_sym` (HIGH)
- Existing `Custom/` library files (versions, CRLF, `(id N)`, model-path styles) (HIGH)
- KiCad developer docs, S-expression introduction (strings are double-quoted UTF-8, numbers in mm, `(id N)` on symbol properties, `module` renamed to `footprint` in v6): https://dev-docs.kicad.org/en/file-formats/sexpr-intro/index.html (MEDIUM; page does not specify escape rules, which must be taken from KiCad's lexer behavior: backslash escapes for `"` and `\`)
- KiCad developer docs, symbol library header (`version` as YYYYMMDD, `generator` guidance): https://dev-docs.kicad.org/en/file-formats/sexpr-symbol-lib/index.html (MEDIUM)
- kiutils (KiCad 6+ parser, stated SCM-friendliness goal, round-trip caveats): https://pypi.org/project/kiutils/1.1.4/ and https://github.com/mvnmgrx/kiutils (MEDIUM; used only to justify not adopting it)
- Plan/apply pattern: standard infrastructure-as-code practice (Terraform plan/apply) applied by analogy (MEDIUM, design reasoning rather than a cited source)

---
*Architecture research for: KiCad vendor-part importer in a layered PySide6 library manager*
*Researched: 2026-10-18*
