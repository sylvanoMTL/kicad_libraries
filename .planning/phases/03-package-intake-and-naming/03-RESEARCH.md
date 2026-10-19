# Phase 3: Package Intake and Naming - Research

**Researched:** 2026-10-19
**Domain:** Headless (Qt-free) zip/folder intake, vendor-layout detection, hostile-archive defence, name sanitising and library-name suggestion, all in Python stdlib
**Confidence:** HIGH (stdlib behaviour probed on this machine; repo conventions read from source; vendor-layout facts limited to the one real UL sample)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward (locked)
- Services return `Issue(severity, code, text)` lists and do not raise for expected failures (Phase 1 D-07). Severity routing is by `Severity`, not by message substrings (Phase 2).
- `downloaded_examples/ul_CSD85301Q2.zip` is committed in the parent repo and is the primary fixture. Tests read it from its committed location and never extract it into the repo (Phase 1 D-04). `downloaded_examples` and `tests` are in the scanner's `SKIP_DIRS`.
- Decoding: strict UTF-8 with BOM preserved, and an `Issue` on invalid UTF-8 (Phase 1 D-11, via `fsutil.decode_source` / `kicad_files.parse_bytes`).
- Stdlib only: `zipfile`, `tempfile`, `unicodedata`, `urllib.parse`. No new runtime dependency.
- The importer writes the `Manufacturer` and `MPN` property names. Existing `MF` / `MP` / `MANUFACTURER` fields are read but never migrated (STATE.md).

#### Library name suggestion (LIB-01)
- **D-01:** Type and SubCategory are a **best guess with a confidence flag**. The guess comes from the symbol's Reference prefix (`U`->`IC`, `Q`->`Transistor`, `J`/`P`->`Connector`, `Y`/`X`->`Oscillator`, `C`->`Capacitor`, `L`->`Inductor`, `D`->`Diode`, `R`->`Resistor`, ...). It is refined by matching the description, `ki_keywords` and Value against tokens already used in `Custom/` library names. If nothing beyond the prefix matches, the suggestion is marked **low confidence**, so the Phase 5 preview can highlight it. Do not just reuse an existing library with the same manufacturer suffix as the suggestion (that would give `IC_Battery_Charger_TI` for the UL MOSFET).
- **D-02:** The manufacturer token comes from, in order:
  1. a Manufacturer-like property in the symbol (`Manufacturer`, `MF`, `MANUFACTURER`, `Manufacturer_Name`), mapped to a token;
  2. the datasheet URL host, mapped through a **small built-in host->token table** (e.g. `ti.com`->`TI`, `analog.com`->`ADI`, `murata.com`->`Murata`, `tdk.com`->`TDK`, `gct.co`->`GCT`, `memsic.com`->`Memsic`, `u-blox.com`->`uBlox`, `abracon.com`->`Abracon`);
  3. for an unknown host, the capitalised second-level domain, marked low confidence.

  The token must agree with the suffixes already used in `Custom/` (`TI`, `ADI`, `GCT`, `Memsic`, `uBlox`, `Abracon`, `TDK`). Match subdomains (`www.ti.com`, `e2e.ti.com`) to their registered domain. The table is a code constant, not a setting.
- **D-03:** Naming returns **one primary suggestion plus up to about 5 existing `Custom/` libraries ranked by shared tokens** (same manufacturer, same Type, overlapping SubCategory). If the primary suggestion equals an existing library name, that means "add to that library". Choosing between existing and new is Phase 4/5. Phase 3 only supplies the data. Existing library names are read from a fresh directory listing of `Custom/Symbols` and `Custom/Footprints`, not from `MainWindow._scan_result`.
- **D-04:** A part that can't be filled gets a **visible placeholder token**, e.g. `IC_SubCategory_TI` (and `Type` when even the Reference prefix is unknown). The suggestion result says which tokens are placeholders. Phase 4/5 must refuse to install while a placeholder token remains in the library name. Record that rule as a contract for those phases. For the UL sample the expected outcome is `IC_SubCategory_TI`, marked low confidence (Reference `U`, no description, datasheet host `ti.com`). This satisfies success criterion 4 (follows the convention, ends in `_TI`, overridable default).

#### Zip safety (INTK-06)
- **D-05:** One hostile member anywhere in the zip **refuses the whole package**, even if that member would have been ignored. Hostile means: `..` segments, absolute paths, drive letters (`C:`), UNC or leading `\`/`/`, symlink entries (Unix mode bits in `external_attr`), or a name that normalises to an escape. An error Issue names the member. Nothing is staged.
- **D-06:** **Generous fixed caps**, as module constants in one place:
  - at most 1000 members;
  - 100 MB uncompressed per member;
  - 250 MB uncompressed in total;
  - a compression-ratio limit of 200:1, applied only to members larger than 1 MB.

  Check declared sizes up front, and also enforce them while reading, because a zip can lie about its sizes. The read cap counts actual bytes. Exceeding any cap refuses the package with an error Issue.
- **D-07:** Stage **only** `.kicad_sym`, `.kicad_mod`, `.step`, `.stp`, `.wrl` members (case-insensitive extension) into a `tempfile.mkdtemp()` directory under generated, safe names. Every other member (HTML guides, `readme.txt`, Altium/Eagle folders, `__MACOSX`) is listed for the log and never written to disk. The size and count caps apply to the whole zip, not just the staged members. Never use `extractall`. The staging dir must be verified to be outside the repo root, and is cleaned up by the context manager that owns it.
- **D-08:** A zip inside the zip is opened **one level deep**, with the same name checks. Its bytes count against the same total budget. A zip nested deeper is refused with an error Issue.

#### Format detection (INTK-01, INTK-02, INTK-05)
- **D-09:** A zip whose layout matches no known vendor but contains v6+ KiCad files is **accepted as generic**. The vendor is reported as `Unknown`, with an info Issue saying vendor-specific quirks were not applied. This lets SnapEDA/CSE zips work before Phase 7 adds their adapters. Ultra Librarian and loose-folder recognition are required in this phase. The registry must let Phase 7 add SnapEDA/SamacSys adapters without changing callers.
- **D-10:** If KiCad 5 files (`.lib`, `.dcm`, `.mod`) sit alongside v6+ files, **use the v6+ files** and log one **info** Issue listing the ignored legacy files.
- **D-11:** The "re-download as KiCad v6+" rejection (error Issue) applies when the package has **no v6+ symbol and no v6+ footprint**, but legacy files exist. It also applies when one half is v6+ and the **other half exists only as legacy** (e.g. a v6 `.kicad_mod` plus a `.lib` symbol). Converting legacy files is v2 (FMT2-01).
- **D-12:** A package with a symbol but **no footprint at all** (or the reverse) and no legacy files is a **valid intake result**, flagged with a warning Issue. Whether it can be installed is decided in Phase 4/5. A package with no 3D model is valid too. The warning that INTK-08 requires is surfaced in Phase 4/5, and intake records "no model found".
- **D-13:** When a package holds several symbols, footprints or models, intake **returns all of them**. Picking which ones to import is INTK-07 (Phase 5).
- **D-14:** Phase 3 is verified by **tests only**: no temporary GUI entry point. The tests are pytest against the UL sample, plus synthetic fixtures built in `tmp_path` or under `tests/fixtures/`. The synthetic fixtures cover hostile zips (traversal, absolute, drive-letter, symlink, too many members, oversize, high ratio, nested two deep), a legacy-only package, a mixed v5/v6 package, a half-legacy package, a symbol-only package, and a loose folder.

#### Name sanitising (LIB-03)
- **D-15:** One `sanitize_name` is used for **library, symbol, footprint and 3D-model file names**. For files, only the stem is sanitised and the original extension is kept, case included. Steps, in order:
  1. Transliterate with a small fixed map (`µ`/`μ`->`u`, `Ω`->`Ohm`, `°`->`deg`, ...), then strip accents with `unicodedata` NFKD (`é`->`e`).
  2. Keep only `A-Z a-z 0-9 _ - .`. Every other character (space, `/`, `:`, `\`, `+`, `#`, parentheses, leftover non-ASCII) becomes `_`.
  3. Collapse runs of `_` into one.
  4. Strip leading and trailing `_`, `.` and spaces.
  5. Cap at **64 characters**, with a warning Issue.
  6. Windows-reserved stem check, case-insensitive (`CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`, including forms like `CON.foo`): **append `_`** (`CON`->`CON_`) with a warning Issue.
  7. An empty result falls back to a placeholder (e.g. `Unnamed`) with an **error** Issue, so install is blocked until the user edits it.

  Already-valid names, including every existing `Custom/` name such as `MEM2085-00-115-00-A_REV0.2` and `TSOT-23_TS8`, pass through unchanged. The result always carries both the original and the sanitised name (success criterion 5).
- **D-16:** A separate naming helper reports a **case-only clash** with an existing `Custom/` name (e.g. new `ic_ldo_ti` vs existing `IC_LDO_TI`) as a warning Issue, because Windows treats them as the same file. Resolving real conflicts (overwrite, rename or skip) stays in Phase 5 (PREV-05).

### Claude's Discretion
- Module layout under `kicad_lib_manager/importer/` (research suggests `package.py`, `candidate.py`, `adapters/{base,ultralibrarian,loose}.py`, `naming.py`, `layout.py`). Also the dataclass shapes for the package, candidate and suggestion, and the `Issue.code` names (e.g. `intake.hostile_member`, `intake.too_large`, `intake.legacy_only`, `intake.unknown_vendor`, `naming.low_confidence`, `naming.reserved`).
- Ultra Librarian recognition markers (e.g. `KiCADv6/` folder, `ImportGuides.html`, `ul_` filename prefix) and confidence scoring between adapters.
- Folder intake: recursion depth, whether caps apply to folders too, and skipping symlinks and junctions. Folders are read in place, read-only.
- Whether intake also extracts and exposes metadata Phase 4/5 will need: symbol name(s), Value, Datasheet, Description, Reference, existing Manufacturer/MPN-like fields, footprint name(s), and the `(version ...)` of each file (for PREV-06). It is recommended where it is cheap.
- Whether intake notes an `(embedded_files` block in an incoming footprint for a later warning (from the untracked report).
- The exact Reference-prefix->Type table and the token-overlap ranking formula for D-01 and D-03.

### Deferred Ideas (OUT OF SCOPE)
- A user-editable host->manufacturer map in settings. It was offered and declined: the map stays a code constant.
- Zip limits that the user can configure. Declined.
- A temporary "Inspect Package..." menu entry for trying intake before Phase 5. Declined: tests only.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTK-01 | User can open a vendor package as a `.zip` file or a folder of loose `.kicad_sym` / `.kicad_mod` / `.step` / `.stp` files | `open_package(path)` returns a context-managed `Package` for both kinds. Zip: selective staging of whitelisted members. Folder: read in place, read-only, symlinks and junctions skipped (see Architecture Patterns 1 and 2) |
| INTK-02 | An Ultra Librarian zip is recognised; symbol, footprint and 3D model found wherever they sit, including a STEP at zip root with a different name | Verified UL sample member list (6 members, no directory entries). UL adapter scores path markers, locates by extension + content (root head), takes names from INSIDE the files (Pattern 3) |
| INTK-05 | Legacy KiCad 5-only packages rejected with "re-download as KiCad v6+" | Classification matrix for D-10/D-11/D-12 (Pattern 4), `intake.legacy_only` and `intake.half_legacy` error Issues whose text contains "re-download as KiCad v6+" |
| INTK-06 | Zips read safely: no extraction into repo, traversal/absolute/symlink rejected, size and count limits | Stdlib behaviour probed on Python 3.14.4 / Windows (Pitfalls 1-6, Code Examples). Pre-scan all members before any byte is read; capped streaming copy; staging verified outside repo |
| LIB-01 | Suggested target library name `<Type>_<SubCategory>_<Manufacturer>`, editable | `suggest_library` with per-token provenance and confidence, placeholder tokens, manufacturer alias + host tables, ranked existing libraries (Pattern 5) |
| LIB-03 | Symbol, footprint and file names sanitised; original vs sanitised shown | `sanitize_name` / `sanitize_filename` returning `NameResult(original, sanitized, issues)`; prototype run against all 64 existing `Custom/` names with zero changes (Pattern 6) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Extracted from `./CLAUDE.md` and `./.claude/CLAUDE.md` (planner must verify compliance):

- **Stdlib only** besides PySide6; no new runtime dependency. Python 3.10+ is the floor (venv is 3.14). Do not use 3.11+ only APIs (e.g. `StrEnum`, `Path.walk` is 3.12, `ExceptionGroup`) without a fallback.
- **Qt-free services.** `importer/` must not import `PySide6`, `main_window` or `widgets`. Only `main_window.py` routes messages to the log. Phase 3 adds no Qt code.
- **Issue lists, not exceptions** for expected failures. Route by `Severity`, never by substring.
- Module-private helpers start with `_`; constants `UPPER_SNAKE`; type-annotated parameters; `Path` for all filesystem inputs; `.as_posix()` for anything stored as a repo-relative string; relative imports inside the package (`from .models import ...`, `from ..models import ...` in subpackages).
- Progress callback is named `progress`, typed `Callable | None`, called `progress(message, current, total)`.
- `kicad_lib_manager/__init__.py` and `widgets/__init__.py` are empty; keep `importer/__init__.py` and `importer/adapters/__init__.py` empty too (`tests/test_layering.py::test_package_init_holds_no_code` enforces this for the top-level package).
- `models.py` has no internal imports. Importer dataclasses live in the importer package.
- **Safety:** no write without preview; nothing in Phase 3 may write into the repo. Staging only in a temp folder outside it.
- Library naming convention `<Type>_<SubCategory>_<Manufacturer>`; symbol and footprint library names must match.
- Existing `Custom/` fields `MF` / `MP` / `MANUFACTURER` are read, never migrated. The importer's own property names are `Manufacturer` and `MPN`.
- GSD workflow enforcement: file edits happen through a GSD command (execute-phase), not directly.
- Windows 11 primary, standard CPython (not MSYS2). Run tests with `.\env\Scripts\python.exe -m pytest`.
- Code style: 4-space indent, double quotes, f-strings, trailing commas in multi-line literals, terse English comments above the code, one-line docstrings on public functions.

## Summary

Phase 3 is pure-Python plumbing with a security-sensitive core. Everything it needs is in the standard library plus modules that already exist (`kicad_files.parse_bytes` / `load`, `find_symbols`, `find_property`, `footprint_name`, `find_models`, `fsutil.decode_source`, `models.Issue` / `Severity`). No package has to be installed, so the Package Legitimacy Audit is not applicable. The riskiest part is the zip handling, and the useful finding is that CPython's `zipfile` does **not** protect the caller where it matters: it silently normalises some names, truncates at NUL, keeps duplicate entries, and only reports symlinks through raw `external_attr` bits. The code must therefore pre-scan every `ZipInfo` before any byte is read and refuse the whole package on the first hostile entry, exactly as D-05 says. On the positive side, CPython bounds each member read by its declared size and verifies CRC, so a lying header surfaces as `BadZipFile` (all verified, see Pitfalls). A counted read loop is still required by D-06 and is cheap defence in depth.

The second finding is that the manufacturer logic needs one table more than CONTEXT.md names. Existing `Custom/` symbols store the manufacturer as free text (`Texas Instruments`, `Global Connector Technology`, `Memsic Inc.`, `U-BLOX`, `GCT`), not as a token, so D-02 step 1 ("mapped to a token") needs a small **name-alias table** (normalised-name -> token) in addition to the host table. Datasheet hosts also include aggregators (`snapeda.com`, `mouser.com`, `digikey.com`, ...) and sub-brand hosts (`invensense.tdk.com` for the `IC_IMU_TDK` library) that must not become a fabricated manufacturer token. The sanitiser prototype (run on this machine) reproduces every one of the 64 existing library, symbol, footprint and 3D-model names unchanged, so D-15's "already-valid names pass through" is achievable with the specified algorithm, provided two details are handled: transliterate before AND after NFKD (NFKD turns `µ` into `μ` and `Ω` sign into `Ω`), and drop combining marks instead of replacing them with `_`.

Plan around five small, independently testable units: (1) `layout.py` + `naming.sanitize_*` (no dependencies), (2) `package.py` zip safety and staging, (3) folder intake and the adapter registry with UL, loose and generic adapters plus the legacy matrix, (4) `naming.suggest_library` with the manufacturer tables and ranking, (5) test infrastructure and layering/contract checks. The UL sample's expected outcome (vendor `UltraLibrarian`, symbol `CSD85301Q2`, footprint `DQK0006B`, model `DLV0006A.stp`, suggestion `IC_SubCategory_TI` at low confidence) was confirmed against the actual file contents.

**Primary recommendation:** Build `open_package()` as a pre-scan-then-stage context manager that refuses on the first hostile or over-cap member before reading any data, stages only whitelisted members through a counted streaming copy into a `TemporaryDirectory` verified outside the repo, and hand the resulting `Package` (names + staged files + Issues) to a confidence-scored adapter registry; keep naming as pure functions over plain data so Phase 4/5 can re-run them after user edits.

## Architectural Responsibility Map

This is a desktop application with no web tiers; the tiers below are the app's own layers (see `.planning/codebase/ARCHITECTURE.md`).

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Zip pre-scan, caps, hostile-member refusal, staging | Service layer (`importer/package.py`, Qt-free) | Filesystem (system temp) | Security logic must be headless-testable and independent of any dialog |
| Folder walk (read-only, skip links) | Service layer (`importer/package.py`) | Filesystem (user folder) | Same `Package` abstraction as zips so adapters do not care about the source |
| Vendor detection and file location | Service layer (`importer/adapters/*`) | `kicad_files` (parsing) | Adapters are pure functions of a `Package`; registry lets Phase 7 add vendors |
| Legacy (KiCad 5) rejection rules | Service layer (`importer/adapters/base.py` or `candidate.py`) | -- | One decision matrix shared by every adapter |
| Name sanitising | Service layer (`importer/naming.py`) | -- | Pure function reused by Phase 4 planner and Phase 5 dialog on every edit |
| Library-name suggestion and ranking | Service layer (`importer/naming.py`) | `importer/layout.py` (fresh directory listing) | Reads `Custom/` fresh, not from `MainWindow._scan_result` (D-03) |
| Repo path knowledge (`Custom/Symbols`, `Footprints`, `3DModels`) | Service layer (`importer/layout.py`) | -- | One frozen dataclass so the convention is validated once |
| Issue display / severity colours | GUI (`main_window.py`, later phases) | -- | Not touched in Phase 3; Phase 3 only returns Issues |
| Temp-folder lifetime | Service layer (`Package` context manager) | Caller (`with` block, later a worker thread) | Staging must outlive intake because Phase 4/5 read the staged files |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `zipfile` (stdlib) | Python 3.14.4 on the dev machine (3.10+ floor) | Read zip metadata and stream members | Only zip reader in the stdlib; behaviour probed this session [VERIFIED: py -I probe, Python 3.14.4 win32] |
| `tempfile` (stdlib) | same | `TemporaryDirectory(prefix=..., ignore_cleanup_errors=True)` staging | `ignore_cleanup_errors` exists from 3.10 [CITED: docs.python.org/3/library/tempfile.html] |
| `unicodedata` (stdlib) | same | NFKD + `combining()` for accent stripping | Required by D-15 |
| `urllib.parse` (stdlib) | same | `urlsplit(...).hostname` | Lower-cases host, strips port and userinfo [VERIFIED: probe: `https://E2E.TI.COM:443/a` -> `e2e.ti.com`] |
| `hashlib` (stdlib) | same | SHA-256 of staged models while copying | INST-04 needs same-content detection later; free to compute during the copy |
| `re`, `stat`, `os`, `dataclasses`, `pathlib`, `io` (stdlib) | same | Name checks, symlink bits, `os.scandir`, dataclasses | Project convention |
| `kicad_lib_manager.kicad_files` (in-repo) | existing | `parse_bytes`, `load`, `find_symbols`, `find_property`, `footprint_name`, `find_models` | Phase 1 read side; reuse, do not re-parse with regexes |
| `kicad_lib_manager.models` (in-repo) | existing | `Issue`, `Severity` | Issue contract |

`Issue` and `Severity` exactly as defined [VERIFIED: kicad_lib_manager/models.py:5-21]:

```python
class Severity(str, Enum):
    # Values equal the LogPanel.COLORS keys
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

@dataclass(frozen=True)
class Issue:
    severity: Severity
    code: str
    text: str
```

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | 9.1.1 (pinned in `requirements-dev.txt`) | Test runner | All Phase 3 verification (D-14); baseline run is 553 passed, 3 skipped in about 11 s [VERIFIED: pytest run this session] |
| `struct` (stdlib, tests only) | same | Patch central-directory sizes to build "lying" zips | One synthetic fixture (see Code Examples) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Own pre-scan over `ZipInfo` | `safezip` or similar PyPI hardening wrapper | Adds a dependency, which D-"Stdlib only" forbids. The checks needed are about 60 lines |
| Public-suffix-list library for registered domains | Small heuristic (last two labels, three when the TLD is a 2-letter ccTLD preceded by a `co`/`com`/`org`/`net`/`ac`/`gov`/`edu` label) | Library is a new dependency. Heuristic is correct for every host in the D-02 table; unknown exotic suffixes degrade to a low-confidence guess |
| `tempfile.mkdtemp()` (D-07 wording) | `tempfile.TemporaryDirectory` | `TemporaryDirectory` calls `mkdtemp` internally and adds owned cleanup plus a finalizer. Compatible with D-07 |

**Installation:** none. Phase 3 adds no package. [VERIFIED: CONTEXT.md "Stdlib only"]

**Version verification:** `py --version` -> `Python 3.14.4`; `requirements-dev.txt` lists `pytest==9.1.1`, `pytest-qt==4.5.0`, `PySide6==6.12.0` [VERIFIED: file read]. No registry lookups are needed because nothing is installed.

## Package Legitimacy Audit

Not applicable: this phase installs no external packages (stdlib only, per the locked "Stdlib only" decision).

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | -- | -- | -- | -- | -- | -- |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 user path (zip file | folder)            repo layout (Custom/Symbols, Footprints, 3DModels)
        |                                              |
        v                                              |
 open_package(path, repo_root)                         |
   |-- folder? --> walk (scandir, no symlinks/junctions, caps) --> Package(kind="folder", in place)
   |-- zip?    --> PRE-SCAN every ZipInfo (no data read yet)
   |                 |-- hostile name / symlink / duplicate / too many / declared size / ratio?
   |                 |       --> ERROR Issue, nothing staged, Package(refused)
   |                 `-- ok --> TemporaryDirectory (verified outside repo)
   |                             stream whitelisted members through counted copy
   |                             (.kicad_sym .kicad_mod .step .stp .wrl) -> generated names
   |                             nested .zip: one level, same checks, shared byte budget
   |                             all other names kept in Package.names only (never written)
   v
 Package: names[] (all members, posix), files[] (staged/in-place), ignored[], issues[]
        |
        v
 detect_candidate(package) -- registry of adapters, each returns (vendor, confidence)
   UltraLibrarian | Loose(folder) | Generic("Unknown")  <-- Phase 7 appends SnapEDA, SamacSys
        |  best confidence wins
        v
 locate by extension + root-head sniff (kicad_files.parse_bytes)
   names from INSIDE the files, never from file/folder names
        |
        v
 legacy matrix (D-10/D-11/D-12)  --> ImportCandidate | refused (ERROR Issue "re-download as KiCad v6+")
        |
        v
 ImportCandidate: vendor, symbols[], footprints[], models[], legacy_ignored[], issues[]
        |
        +--> PartMeta (reference, value, datasheet, description, keywords, manufacturer...)
                 |
                 v
        suggest_library(meta, existing_names) --> LibrarySuggestion
             (Reference->Type, vocab->SubCategory, property/host->Manufacturer, placeholders,
              ranked existing libs)       ^
                                          |
                  list_existing_libraries(layout)  (fresh listing of Custom/)
        sanitize_name / sanitize_filename --> NameResult(original, sanitized, issues)
```

### Recommended Project Structure
```
kicad_lib_manager/
├── importer/
│   ├── __init__.py          # empty (project convention)
│   ├── layout.py            # RepoLayout (frozen): custom_dir, symbols_dir, footprints_dir, models_dir; list_* fresh listings
│   ├── package.py           # limits constants, open_package, Package (context manager), _scan_zip, _stage_zip, _walk_folder
│   ├── candidate.py         # ImportCandidate, SymbolItem, FootprintItem, ModelItem, PartMeta dataclasses
│   ├── naming.py            # NameResult, sanitize_name, sanitize_filename, case_clash, LibrarySuggestion, suggest_library, tables
│   └── adapters/
│       ├── __init__.py      # empty
│       ├── base.py          # Adapter protocol, Detection, generic locator, legacy matrix, detect_candidate registry
│       ├── ultralibrarian.py
│       └── loose.py
└── (existing flat modules unchanged; possibly +file_kind/file_version helpers in kicad_files.py)
tests/
├── conftest.py              # add: ul_zip fixture path, make_zip builder helpers
├── test_importer_layering.py
├── test_package_zip.py
├── test_package_folder.py
├── test_adapters.py
├── test_legacy_rules.py
├── test_naming_sanitize.py
└── test_naming_suggest.py
```

The module list matches CONTEXT.md "Claude's Discretion" and `.planning/research/ARCHITECTURE.md` (importer/ subpackage). [VERIFIED: 03-CONTEXT.md, ARCHITECTURE.md lines 71-78, 94-103]

### Pattern 1: Pre-scan, then stage (zip)
**What:** Walk `ZipFile.infolist()` once before reading any member data. Every `ZipInfo` is validated against the same hostile rules and against the cumulative caps. Only if the whole list passes does a second pass stream whitelisted members to disk.
**When to use:** Always, for every zip including a nested one.
**Rules to implement (D-05, D-06, D-07, D-08) plus recommended extras:**
- Member count `> MAX_MEMBERS` -> `intake.too_many_members`.
- For each `info`: take `name = info.filename`, then work on `n = name.replace("\\", "/")` because CPython only converts `\` when `os.sep` is `\` (Windows), so on other platforms a backslash survives (Pitfall 1).
- Hostile if any of: `n.startswith("/")` (also covers UNC `//host/share`), a drive pattern `^[A-Za-z]:` at the start, any segment `== ".."`, a `:` anywhere in any segment (alternate data streams and drive letters in the middle; recommended extra, [ASSUMED] no legitimate vendor zip needs it), a control character (`ord < 32`), an empty name.
- Hostile if `stat.S_ISLNK(info.external_attr >> 16)`; also hostile if the low byte carries the Windows reparse-point flag `stat.FILE_ATTRIBUTE_REPARSE_POINT` (`0x400` is in the **low 16 bits** only for archivers that store NTFS attributes; [ASSUMED], cheap and safe to check because it is a pure refusal) [VERIFIED for the Unix bits: probe, `create_system=3`, mode `0o120777` -> `S_ISLNK` True].
- Duplicate names after `casefold()` (and after separator normalisation) -> refuse (`intake.duplicate_member`, recommended; CPython keeps both entries and `ZipFile.read(name)` returns the last, so a hostile zip can shadow a member [VERIFIED: probe `dups ['a.step','a.step'] b'2'`]).
- Declared sizes: `info.file_size > MAX_MEMBER_BYTES` and running sum `> MAX_TOTAL_BYTES` -> `intake.too_large`. Ratio: `info.file_size > RATIO_MIN_SIZE (1 MiB)` and `info.file_size / max(info.compress_size, 1) > MAX_RATIO` -> `intake.high_ratio`. A 50 MB zero-fill compresses to about 48 KB, ratio about 1029:1 [VERIFIED: probe].
- Encrypted (`info.flag_bits & 0x1`) -> `intake.encrypted` (CPython raises `RuntimeError` on read, probe confirmed).
- Directory entries (`info.is_dir()`) count toward the member count and are skipped otherwise.
- A hostile finding reports the member name (`repr`-safe, truncated to about 200 characters) in the Issue text and returns immediately: refuse the whole package.

**Staging pass:**
- `TemporaryDirectory(prefix="kicad_import_", ignore_cleanup_errors=True)`. Immediately verify `Path(tmp).resolve()` is not under `repo_root.resolve()` (`not tmp.is_relative_to(repo)`; both `resolve()`d, Windows comparison is case-insensitive and `resolve()` expands 8.3 short names). On failure clean up and refuse with `intake.staging_in_repo`.
- Staged name: `f"{kind}_{index:03d}{ext}"` where `kind` in `sym|fp|model`, `index` is a running integer and `ext` is the allow-listed extension **with its original case** (safe because it was matched against the whitelist). Never derive any path component from the member name.
- Use `Path(tmp) / staged_name` and assert the parent is the staging dir; open with `"xb"` (exclusive create) as defence in depth.
- Copy with `with zf.open(info) as src:` using the **`ZipInfo` object** (not the name; avoids the duplicate-name ambiguity) through `_read_capped` / `_copy_capped` that counts actual bytes against `min(MAX_MEMBER_BYTES, remaining_total)`.
- Compute SHA-256 while copying for model files (store in `PackageFile.sha256`).

### Pattern 2: Folder intake (read in place, read-only)
**What:** `os.scandir` iterative walk (no recursion limit trouble), `follow_symlinks=False`, depth cap (recommended 8), the same `MAX_MEMBERS` / `MAX_MEMBER_BYTES` / `MAX_TOTAL_BYTES` caps applied to the sum of **whitelisted** files' `st_size` and to total entry count (caps for folders are Claude's discretion; recommended yes, because a user can point at `C:\`). Skip (and log an info Issue for) symlinks and Windows junctions: `entry.is_symlink()` is False for junctions on Windows, so also test `getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT` [VERIFIED: `stat.FILE_ATTRIBUTE_REPARSE_POINT == 1024` on this machine; `Path.is_junction` exists in 3.12+ only, so use the stat bit for the 3.10 floor].
**Files** keep their real paths (`PackageFile.path` points into the user's folder, `staged=False`). Never open for write. `Package.names` holds the posix path relative to the chosen folder.

### Pattern 3: Adapter registry with confidence scoring
**What:** `Adapter` protocol with `detect(package) -> Detection | None` (vendor label + confidence 0..1) and a shared `locate(package, detection) -> ImportCandidate`. `detect_candidate(package)` evaluates the registry list, picks the highest confidence, and falls back to the generic adapter (confidence floor 0.1, vendor `"Unknown"`). Phase 7 appends `SnapEDAAdapter` / `SamacSysAdapter` to the list; callers never change (D-09).
**Ultra Librarian markers** (only one real sample exists, so score, do not hard-require):
- A path segment equal (case-insensitively) to `KiCADv6` (or `KiCADv5`, which is also a UL marker but then legacy rules apply) -> +0.5.
- `ImportGuides.html` at root or `ImportGuide.html` inside that folder -> +0.3 (these names are in `Package.names` even though HTML is never staged).
- A symbol file whose basename matches `^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.kicad_sym$` -> +0.2.
- Source filename stem starts with `ul_` (zip only) -> +0.1 (weak: the owner may rename downloads).
- Claim UL at `>= 0.5`.
The sample scores 1.0 (all four) and an unzipped copy of it in a folder scores 0.9 (no `ul_` zip name). Because adapters read `Package.names`, the same UL adapter handles a zip and an already-unzipped folder.
**Loose adapter:** claims a folder package with no stronger vendor match; vendor `"Loose"` (the CONTEXT calls the folder case "loose"). A zip with no vendor match is `"Unknown"` plus info Issue `intake.unknown_vendor` (D-09).
**Locating files:** by extension from `Package.files`, then confirm by root head after `kicad_files.parse_bytes`: `.kicad_sym` -> head `kicad_symbol_lib`; `.kicad_mod` -> head `footprint` (or `module`, see Open Question 1); `.step/.stp` -> text begins `ISO-10303-21;` after optional whitespace; `.wrl` -> begins `#VRML`. A mismatch yields a warning Issue and the file is not offered (do not guess).
**Names from inside the files** (Pitfall 8 in research): symbol names from `find_symbols(root)`; footprint name from `footprint_name(root)`; never from file names (the UL symbol file is a timestamp). Keep the in-package posix path as display/provenance only (GIT-04 will want the original package filename).

### Pattern 4: Legacy decision matrix (D-10, D-11, D-12)
Legacy classes by extension: symbol side `.lib`, `.dcm`; footprint side `.mod`. v6+ presence is `sym6` (at least one valid `.kicad_sym`), `fp6` (at least one valid footprint file). Evaluate in this order:

| sym6 | fp6 | legacy present | Result |
|------|-----|----------------|--------|
| no | no | `.lib`/`.dcm`/`.mod` any | ERROR `intake.legacy_only`: text must contain "re-download as KiCad v6+" |
| no | no | none | ERROR `intake.nothing_found` (no KiCad v6+ symbol or footprint) ([ASSUMED]: CONTEXT does not say; a package with only a STEP has nothing to import) |
| yes | no | `.mod` present (footprint-side legacy) | ERROR `intake.half_legacy` ("footprint only exists as legacy ... re-download as KiCad v6+") |
| no | yes | `.lib`/`.dcm` present | ERROR `intake.half_legacy` |
| yes | no | none, or only symbol-side legacy | OK, WARNING `intake.no_footprint`; plus INFO `intake.legacy_ignored` when legacy is present |
| no | yes | none, or only footprint-side legacy | OK, WARNING `intake.no_symbol`; plus INFO `intake.legacy_ignored` when legacy is present |
| yes | yes | any | OK; one INFO `intake.legacy_ignored` listing the ignored legacy files |
| any OK result | | no model | OK; INFO `intake.no_model` (D-12: "intake records no model found"; the INTK-08 warning is surfaced later) |

On any ERROR, `detect_candidate` returns no candidate, only Issues. The refused package is still closed by its `with` block.

### Pattern 5: Library-name suggestion (LIB-01, D-01..D-04)
**Inputs:** a `PartMeta` (for one symbol) and the existing library names from a fresh listing. Suggested API:

```python
@dataclass(frozen=True)
class TokenChoice:
    token: str
    source: str        # "reference" | "vocab" | "property" | "name_alias" | "host_table" | "host_guess" | "placeholder"
    confident: bool

@dataclass(frozen=True)
class RankedLibrary:
    name: str
    score: int
    shared_tokens: tuple[str, ...]
    has_symbols: bool
    has_footprints: bool

@dataclass(frozen=True)
class LibrarySuggestion:
    name: str                       # e.g. "IC_SubCategory_TI"
    type: TokenChoice
    subcategory: TokenChoice
    manufacturer: TokenChoice
    confidence: str                 # "high" only when all three tokens are confident, else "low"
    placeholders: tuple[str, ...]   # subset of PLACEHOLDER_TOKENS actually present
    matches_existing: bool          # primary name equals an existing library (case-insensitive) -> "add to that library"
    alternatives: tuple[RankedLibrary, ...]   # at most 5
    issues: tuple[Issue, ...]
```
- `PLACEHOLDER_TOKENS = ("Type", "SubCategory", "Manufacturer")` and `placeholder_tokens(name) -> list[str]` so Phase 4/5 re-check a user-edited name. Record in the Phase 3 docs and in the Phase 4/5 notes: **install is refused while `placeholder_tokens(name)` is non-empty** (D-04 contract). Also suggest adding the same sentence to ROADMAP Phase 4 and 5 success-criteria notes.
- **Type:** `re.match(r"[A-Za-z]+", reference)` then longest-prefix lookup in `REFERENCE_TYPE` (upper-cased). Recommended table [ASSUMED, user may edit]: `U,IC -> IC`, `Q -> Transistor`, `J,P,CN -> Connector`, `Y,X,XTAL -> Oscillator`, `C -> Capacitor`, `L -> Inductor`, `FB -> Ferrite`, `D -> Diode`, `LED -> LED`, `R -> Resistor`, `F -> Fuse`, `SW,S -> Switch`, `K -> Relay`, `TP -> TestPoint`, `BT,B -> Battery`. `X -> Oscillator` follows D-01's literal list. Unknown prefix, `REF**`, `#PWR`, or empty -> placeholder `Type`. Prefix-only Type is "confident" for Type, but D-01 makes the **overall** suggestion low confidence unless a SubCategory also matched.
- **SubCategory:** build the vocabulary by parsing each existing library name: `type = first token`, `manufacturer = last token`, `sub = middle tokens` (SubCategory may itself contain `_`: `Battery_Fuel_Gauge`, `Wireless_BLE`). Tokenise the part's description (after collapsing literal `\n` escapes and whitespace; existing `Custom/` descriptions contain `\n` + blanks, see Pitfall 11), `ki_keywords` and Value on `[^A-Za-z0-9]+`, lower-cased. A library's SubCategory matches only when **all** its sub tokens appear as whole tokens (no substring matching, so the `usb4056` token of a part number never matches the `USB` vocabulary token; see Pitfall 12) and only libraries with the same Type are considered when Type came from the prefix. Choose the match with the most sub tokens, then lexicographic. Source `"vocab"`, confident. No match -> `"SubCategory"` placeholder.
- **Manufacturer:** (1) first present of `Manufacturer`, `MF`, `MANUFACTURER`, `Manufacturer_Name` -> `manufacturer_token(value)`: normalise (casefold, strip non-alphanumerics, drop corporate suffix words `inc ltd gmbh corp co ag llc plc`), look up `MANUFACTURER_ALIASES`; hit -> confident (`name_alias`); miss -> first word capitalised, not confident (`property`, low). (2) `datasheet` -> `registered_domain(host)` -> `HOST_TOKENS` (confident, `host_table`); host in `AGGREGATOR_HOSTS` -> skip (not a manufacturer). (3) unknown host -> capitalised second-level label with hyphens removed (`u-blox` -> `Ublox`), not confident (`host_guess`). (4) none -> `"Manufacturer"` placeholder.
- **Tables as code constants** [ASSUMED unless noted]: `HOST_TOKENS` = the D-02 list (`ti.com`, `analog.com`, `murata.com`, `tdk.com`, `gct.co`, `memsic.com`, `u-blox.com`, `abracon.com`) plus repo-evidenced extras: `invensense.com` -> `TDK`, `maximintegrated.com` -> `ADI`, `linear.com` -> `ADI` (the repo files MAX17048 and LTC2954 under `IC_Battery_Fuel_Gauge_ADI` / `IC_Button_Controller_ADI`) [VERIFIED: Custom/Symbols listing and symbol names read this session]. `MANUFACTURER_ALIASES` seeded from values actually present in `Custom/`: `texasinstruments -> TI`, `globalconnectortechnology -> GCT`, `gct -> GCT`, `memsic -> Memsic`, `ublox -> uBlox`, `analogdevices -> ADI`, `tdk -> TDK`, `abracon -> Abracon`, `murata -> Murata` [VERIFIED for the property values `Texas Instruments`, `Global Connector Technology`, `GCT`, `Memsic Inc.`, `U-BLOX` read from Custom symbols this session].
- **Ranking (D-03):** for each existing library name parsed into (type, sub tokens, manufacturer): `score = 3 * (manufacturer equal, casefold) + 2 * (type equal) + len(shared sub tokens)`. Keep `score > 0`, sort by `(-score, name.casefold())`, take 5. Deterministic ties. The primary suggestion is never replaced by the top alternative. UL sample: primary `IC_SubCategory_TI`; `IC_Battery_Charger_TI` ranks first with score 5 but is only an alternative.
- **Result tokens must pass `sanitize_name`:** build the name with `"_".join(...)` and run it through `sanitize_name`; surface its issues.

### Pattern 6: Name sanitising (LIB-03, D-15, D-16)
**Two entry points, one algorithm:**

```python
@dataclass(frozen=True)
class NameResult:
    original: str
    sanitized: str
    issues: tuple[Issue, ...]
    @property
    def changed(self) -> bool: return self.original != self.sanitized

def sanitize_name(name: str, *, max_len: int = MAX_NAME_LEN) -> NameResult: ...          # library / symbol / footprint names
def sanitize_filename(filename: str, *, extensions=MODEL_EXTENSIONS) -> NameResult: ...  # 3D model files: stem sanitised, listed extension kept with case
```
- Split a filename only at a **listed** extension (`.step`, `.stp`, `.wrl`, `.kicad_sym`, `.kicad_mod`, case-insensitive). Never use `os.path.splitext` on a part or footprint **name**: existing names contain dots (`MEM2085-00-115-00-A_REV0.2`) and would lose `.2` [VERIFIED: that name exists in Custom/ and passes through the prototype unchanged].
- Algorithm (prototype `san_proto.py` in the session scratchpad, results quoted below): NFKD, then the transliteration map (include both pre- and post-NFKD code points: `U+00B5` micro sign and `U+03BC` Greek mu -> `u`, `U+2126` ohm sign and `U+03A9` Omega -> `Ohm`, `U+00B0` -> `deg`, plus `ø o`, `ß ss`, `æ ae`), then drop characters with `unicodedata.combining(c)`, then `[^A-Za-z0-9_.\-]` -> `_`, collapse `_+`, strip `"_. "`, cap at 64 and re-strip, reserved-name check on the segment before the first `.`, empty -> `Unnamed`.
- Reserved check form: `head, dot, rest = s.partition("."); if head.upper() in RESERVED: s = head + "_" + dot + rest`. So `CON` -> `CON_`, `NUL.foo` -> `NUL_.foo`. Windows treats `NUL.tar.gz` as the device `NUL`, so the check is on the segment before the **first** dot [ASSUMED, well-known Windows behaviour; the extension-bearing form is what D-15 asks for].
- Prototype results [VERIFIED: ran `san_proto.py` this session]: `CON`->`CON_`, `con`->`con_`, `NUL.foo`->`NUL_.foo`, `COM1`->`COM1_`, `COM¹`->`COM1_` (NFKD maps the superscript), `a/b`->`a_b`, `a:b`->`a_b`, `..`->`Unnamed` (empty), `../../x`->`x`, `µF cap`->`uF_cap`, `10Ω`->`10Ohm`, `café`->`cafe`, `S3G-E3/57T`->`S3G-E3_57T`, `CONIN$`->`CONIN` (the `$` becomes `_` and is stripped; not reserved after that), a katakana-only name -> `Unnamed` (empty, error), 80 `x` -> 64 `x` with truncation. **All 64 existing names pass unchanged**: 10 symbol libraries, 9 `.pretty` libraries, footprint file stems, 3D-model stems (13 files), and top-level symbol names.
- **Traversal:** sanitising converts every separator to `_` and strips leading dots, so the sanitised result is a single safe path component. The consumer must still do `(dir / name).resolve().is_relative_to(dir.resolve())` at write time (Phase 4).
- **Issue codes:** `naming.changed` (INFO, text `'<orig>' -> '<new>'`), `naming.truncated` (WARNING), `naming.reserved` (WARNING), `naming.empty` (ERROR). Always return the original beside the sanitised one.
- **D-16:** `case_clash(name, existing_names) -> list[Issue]`: casefold equality with a different spelling gives `naming.case_clash` (WARNING). Exact equality is not a clash (that is "add to existing", D-03).

### Anti-Patterns to Avoid
- **`ZipFile.extractall` / `extract`** into any directory, and any path built from `info.filename` (D-07). Staged names are generated.
- **Reading by name** (`zf.read("x")`) after a pre-scan: duplicate names make the name lookup return a different member than the one that was validated. Use the `ZipInfo`.
- **Constants captured as default arguments** (`def f(limit=MAX_MEMBER_BYTES)`): tests could then not monkeypatch the cap. Read module globals at call time.
- **Using symbol/footprint file names as part names** (UL: a timestamp). Take names from file contents.
- **Matching library tokens by substring.** Use whole tokens.
- **Treating the datasheet host as the manufacturer unconditionally.** Aggregator hosts exist.
- **Importing `main_window`, `widgets` or Qt** anywhere under `importer/`.
- **Raising for expected failures** (bad zip, hostile member, legacy package). Return Issues.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Zip parsing, decompression, CRC | A custom zip reader | `zipfile` | CPython verifies CRC and bounds the read by the declared size [VERIFIED: probe, lied `file_size=100` -> `BadZipFile: Bad CRC-32`] |
| Temp dir creation/cleanup | `mkdir` under a guessed path | `tempfile.TemporaryDirectory` | Unique, 0700-style creation, owned cleanup, finalizer |
| S-expression parsing | Regexes for `(property ...)` / `(footprint ...)` | `sexpr.parse` via `kicad_files.parse_bytes`, `find_symbols`, `find_property`, `footprint_name`, `find_models` | Already round-trip tested (Phase 1); the legacy regex approach was rejected |
| UTF-8/BOM decoding | `open(..., encoding="utf-8")` | `fsutil.decode_source` (through `parse_bytes`) | Strict decode with an `Issue` on invalid bytes |
| URL host extraction | String splitting on `/` | `urllib.parse.urlsplit` | Lower-cases the host, strips port and userinfo. Note it returns `hostname=None` without a scheme or `//` (Pitfall 9) |
| Accent stripping | A giant char map | `unicodedata.normalize("NFKD")` + `combining()` | Only the few non-decomposing symbols need a map |
| Atomic writes | Anything | `fsutil.atomic_write_*` | Not needed in Phase 3: nothing is written to the repo |

**Key insight:** The hard part of this phase is not parsing, it is refusing inputs correctly. Keep the refusal rules in one pre-scan function and make the parser dumb.

## Runtime State Inventory

Not applicable: this phase is greenfield (a new `importer/` subpackage and new tests). No rename, refactor or migration.

## Common Pitfalls

### Pitfall 1: Trusting `ZipInfo.filename` as already normalised
**What goes wrong:** On Windows `ZipInfo` converts `\` to `/`; on Linux/macOS a backslash survives, so a name like `a\..\..\x` is a single "segment" on POSIX and a traversal on Windows. A NUL byte truncates the name silently.
**Why it happens:** CPython normalises `os.sep` only [VERIFIED: probe on Windows: `'a\\b.txt' -> 'a/b.txt'`, `'a/..\\..\\x' -> 'a/../../x'`, `'x\x00.txt' -> 'x'`; `'../x.txt'`, `'C:/x.txt'`, `'C:x.txt'`, `'/abs.txt'`, `'//unc/share/x'`, `'a/b:stream.txt'` all survive unchanged].
**How to avoid:** Normalise `\` to `/` yourself before the hostile-name checks, then check every segment. Tests must pass on Windows (dev) and still describe the POSIX behaviour: build the names with `chr(92)`.
**Warning signs:** A test for `..\\evil` passes on Windows but the same name is accepted on Linux.

### Pitfall 2: Symlink detection that depends on `create_system`
**What goes wrong:** `external_attr >> 16` holds Unix mode bits only for Unix-created archives (`create_system == 3`). Web search could not confirm this in the official docs [UNVERIFIED search]; the probe confirms the mechanics only.
**How to avoid:** Check `S_ISLNK(info.external_attr >> 16)` unconditionally when the high bits are non-zero (false positives are implausible: DOS-created archives leave the high 16 bits zero, sample has `external_attr = 0x0` for all 6 members [VERIFIED: sample dump]). Never create symlinks regardless (staged files are written from bytes).
**Warning signs:** A symlink member staged as a tiny file containing a path.

### Pitfall 3: Duplicate member names
**What goes wrong:** Two members named `a.step`; validation sees both, `read(name)` returns the second [VERIFIED: probe].
**How to avoid:** Refuse duplicates (casefolded) in the pre-scan and open members by `ZipInfo`.

### Pitfall 4: Lying sizes and the "enforce while reading" requirement
**What goes wrong:** D-06 wants the cap enforced on actual bytes. In CPython the read is bounded by the declared `file_size` and a mismatch fails the CRC, so with this implementation a lying header yields `BadZipFile`, not oversized memory [VERIFIED: probe, declared 100, real 5,000,000 -> `BadZipFile: Bad CRC-32 for file 'big.kicad_sym'` for both `read` and `open().read(65536)` loop].
**How to avoid:** Still implement `_read_capped(fileobj, limit)` that counts bytes per chunk and refuses past the limit; test it directly with a `BytesIO` larger than the limit (the lie cannot be reproduced through CPython), and test the lying-header zip separately, expecting `intake.corrupt`. Catch `zipfile.BadZipFile`, `RuntimeError` (encrypted), `NotImplementedError` (unsupported compression), `zlib.error`, `EOFError`, `OSError` around the member copy and the central-directory open.

### Pitfall 5: Ratio limit applied to everything
**What goes wrong:** Tiny text files legitimately compress 50:1 (sample symbol is 18271/1019 = about 18:1); a ratio test on all members would reject junk or future samples.
**How to avoid:** Apply the 200:1 limit only to members above 1 MiB (D-06). Check `compress_size == 0` without a divide-by-zero.

### Pitfall 6: Windows cleanup failures on the staging directory
**What goes wrong:** Antivirus or an open handle makes `rmtree` raise `PermissionError` during `__exit__`, turning a successful intake into a crash.
**How to avoid:** `TemporaryDirectory(ignore_cleanup_errors=True)`. Cleanup also must run when intake refuses a package.

### Pitfall 7: `(module` footprints in `.kicad_mod` files
**What goes wrong:** KiCad 5 also used the `.kicad_mod` extension, with a `(module ...)` root head. Classifying by extension would accept a KiCad 5 footprint as "v6+". `kicad_files.footprint_name` already accepts `module` [VERIFIED: kicad_files.py:130-138, `lambda head: head in ("footprint", "module")`].
**How to avoid:** Record the root head and `(version N)` on every `FootprintItem`. Recommended handling: accept but emit WARNING `intake.legacy_footprint_syntax` (see Open Question 1). Add small public helpers to `kicad_files.py` (`file_kind(root)`, `file_version(root)`) rather than reaching into `Node` from the importer.

### Pitfall 8: Extension handling on names with dots
**What goes wrong:** `os.path.splitext("MEM2085-00-115-00-A_REV0.2")` returns extension `.2`; the sanitiser then treats `.2` as the extension and sanitises the wrong part.
**How to avoid:** Split only at an allow-listed extension (Pattern 6).

### Pitfall 9: `urlsplit` returns `None` for scheme-less and malformed URLs
**What goes wrong:** `urlsplit("www.ti.com/lit/x").hostname` is `None`; `urlsplit("http://[bad")` raises `ValueError`; `file:///C:/x.pdf` and `~` give `None` [VERIFIED: probe].
**How to avoid:** Wrap in `try/except ValueError`; if there is no `://` and no leading `//`, retry with `"//" + value`; treat an empty/`~` datasheet as "no host" (no manufacturer from host, no error).

### Pitfall 10: Aggregator and sub-brand datasheet hosts
**What goes wrong:** A SnapEDA/Mouser/DigiKey/Octopart datasheet link would yield a nonsense manufacturer (`Mouser`). `invensense.tdk.com` must collapse to `tdk.com` to get `TDK` (repo evidence: `IC_IMU_TDK` datasheet host is `invensense.tdk.com`) [VERIFIED: Custom/Symbols/IC_IMU_TDK.kicad_sym Datasheet value read this session].
**How to avoid:** `AGGREGATOR_HOSTS` deny-list (registered domains such as `snapeda.com`, `snapmagic.com`, `ultralibrarian.com`, `componentsearchengine.com`, `samacsys.com`, `digikey.com`, `mouser.com`, `octopart.com`, `lcsc.com`, `arrow.com`, `farnell.com`, `alldatasheet.com` [ASSUMED list]) -> host ignored. Registered domain = last two labels, or last three when the TLD is two letters and the preceding label is one of `co com org net ac gov edu` [ASSUMED heuristic; `gct.co` stays `gct.co` because `gct` is not in that set].

### Pitfall 11: Descriptions in `Custom/` are noisy
**What goes wrong:** Existing descriptions contain literal `\n` escapes plus runs of blanks (SnapEDA/DigiKey style), and non-ASCII (`µP`, `I²C`, `3μA`) [VERIFIED: property survey of Custom symbols this session]. Token matching on the raw string fails or false-matches.
**How to avoid:** Normalise (`replace("\\n", " ")`, collapse whitespace, NFKD) before tokenising.

### Pitfall 12: Substring token matching
**What goes wrong:** Vendor part numbers like `USB4056-03-A`, `LTC2954` contain vocabulary strings. Substring matching would classify any `USB...` part as `Connector_USB`.
**How to avoid:** Split into tokens on non-alphanumerics and require whole-token equality. Part-number tokens (`usb4056`) then do not equal `usb`.

### Pitfall 13: UL footprint field has no library prefix
**What goes wrong (for later phases):** The sample symbol's `Footprint` property is `DQK0006B`, not `Lib:Name`, and the sample footprint has no `(model ...)` block [VERIFIED: sample symbol and footprint dump this session]. Phase 3 should record the raw `Footprint` field and `find_models()` result in the candidate so Phase 4/5 know to rewrite the field and insert a model block.

### Pitfall 14: Staging "outside the repo" is not automatic
**What goes wrong:** `%TEMP%` can in principle be configured inside the repo (or an 8.3 short path hides the relation); then staged files appear in the next scan.
**How to avoid:** Compare `resolve()`d paths with `is_relative_to`; refuse with `intake.staging_in_repo`. Test by monkeypatching `tempfile.tempdir` to a folder under a fake repo root.

## Code Examples

### Pre-scan of a zip (sketch, follows Python 3.10+ typing and project style)
```python
# Source: derived from probes run this session on Python 3.14.4 (win32) and D-05/D-06
import stat
import zipfile
from pathlib import PurePosixPath

MAX_MEMBERS = 1000
MAX_MEMBER_BYTES = 100 * 1024 * 1024
MAX_TOTAL_BYTES = 250 * 1024 * 1024
MAX_RATIO = 200
RATIO_MIN_SIZE = 1024 * 1024
_WINDOWS_REPARSE = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _hostile_reason(name: str, info: zipfile.ZipInfo) -> str | None:
    n = name.replace("\\", "/")
    if not n or n.startswith("/") or (len(n) >= 2 and n[1] == ":" and n[0].isalpha()):
        return "absolute or drive-letter path"
    if any(seg == ".." for seg in n.split("/")):
        return "path traversal (..)"
    if ":" in n or any(ord(c) < 32 for c in n):
        return "illegal character"
    mode = info.external_attr >> 16
    if mode and stat.S_ISLNK(mode):
        return "symbolic link"
    if info.external_attr & _WINDOWS_REPARSE:
        return "reparse point"
    return None
```

### Counted copy (module globals read at call time so tests can monkeypatch the caps)
```python
def _copy_capped(src, dst, limit: int, sha=None) -> int | None:
    """Copy src to dst in chunks; return bytes copied, or None when more than limit were read."""
    total = 0
    while chunk := src.read(65536):
        total += len(chunk)
        if total > limit:
            return None
        if sha is not None:
            sha.update(chunk)
        dst.write(chunk)
    return total
```

### Building hostile and lying zips in tests (no committed binaries)
```python
# Source: probes run this session (zprobe.py in the session scratchpad)
import io, struct, zipfile

def make_zip(path, members: dict, *, compression=zipfile.ZIP_DEFLATED) -> None:
    with zipfile.ZipFile(path, "w", compression) as z:
        for name, data in members.items():
            z.writestr(name, data)             # name may be str or ZipInfo

def symlink_info(name: str) -> zipfile.ZipInfo:
    zi = zipfile.ZipInfo(name)
    zi.create_system = 3
    zi.external_attr = 0o120777 << 16
    return zi

def lie_about_size(zip_bytes: bytes, declared: int) -> bytes:
    raw = bytearray(zip_bytes)
    cd = raw.find(b"PK\x01\x02"); lh = raw.find(b"PK\x03\x04")
    struct.pack_into("<I", raw, cd + 24, declared)    # central directory uncompressed size
    struct.pack_into("<I", raw, lh + 22, declared)    # local header uncompressed size
    return bytes(raw)

# duplicate names need warnings suppressed on write; a 2 MiB zero-fill gives ratio > 200 and > 1 MiB
```
Backslash names must be built with `BS = chr(92)` in the test source to avoid escaping mistakes (the probe script hit exactly that).

### Registered domain and host extraction
```python
from urllib.parse import urlsplit

_SLD_LABELS = {"co", "com", "org", "net", "ac", "gov", "edu"}

def _host(datasheet: str) -> str | None:
    value = datasheet.strip()
    if not value or value == "~":
        return None
    try:
        host = urlsplit(value if "://" in value or value.startswith("//") else "//" + value).hostname
    except ValueError:
        return None
    return host.rstrip(".") if host else None

def _registered_domain(host: str) -> str:
    labels = host.split(".")
    if len(labels) >= 3 and len(labels[-1]) == 2 and labels[-2] in _SLD_LABELS:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])
```
Expected: `www.ti.com`, `e2e.ti.com` -> `ti.com`; `invensense.tdk.com` -> `tdk.com`; `www.gct.co` -> `gct.co`; `www.murata.co.jp` -> `murata.co.jp`.

### Sanitise core (matches the prototype that passed all 64 existing names)
```python
import re, unicodedata

_TRANSLIT = {"\u00b5": "u", "\u03bc": "u", "\u03a9": "Ohm", "\u2126": "Ohm", "\u00b0": "deg",
             "\u00d8": "O", "\u00f8": "o", "\u00df": "ss", "\u00e6": "ae", "\u00c6": "AE"}
_BAD = re.compile(r"[^A-Za-z0-9_.\-]")

def _clean(name: str) -> str:
    s = "".join(_TRANSLIT.get(c, c) for c in name)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(_TRANSLIT.get(c, c) for c in s if not unicodedata.combining(c))
    s = _BAD.sub("_", s)
    return re.sub(r"_+", "_", s).strip("_. ")
```

### UL sample expectations to assert (all verified against the committed zip)
```python
# Source: dump of downloaded_examples/ul_CSD85301Q2.zip this session
MEMBERS = {   # name: (file_size, compress_size); all external_attr == 0x0, no directory entries
    "DLV0006A.stp": (192031, 37607),
    "ImportGuides.html": (8175, 2523),
    "readme.txt": (1152, 567),
    "KiCADv6/2026-10-18_09-12-49.kicad_sym": (18271, 1019),
    "KiCADv6/ImportGuide.html": (8251, 2551),
    "KiCADv6/footprints.pretty/DQK0006B.kicad_mod": (2468, 517),
}
# symbol "CSD85301Q2": Reference "U", Value "CSD85301Q2", Footprint "DQK0006B",
#   Datasheet "https://www.ti.com/lit/gpn/csd85301q2", ki_keywords "CSD85301Q2", ki_fp_filters "DQK0006B", (version 20211014)
# footprint (footprint "DQK0006B" (version 20211014) ...), no (model ...) block, no (embedded_files
# STEP header: ISO-10303-21;  FILE_NAME('DLV0006A_ASM', ...)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `extractall` into a folder, then scan | Pre-scan `infolist()`, stream whitelisted members to generated names | Standard secure-coding guidance (zip slip, CWE-409) [CITED: best.openssf.org/Secure-Coding-Guide-for-Python/CWE-664/CWE-409, titles only via search] | Matches D-05..D-07 |
| `TemporaryDirectory()` raising on cleanup errors | `ignore_cleanup_errors=True` | Python 3.10 [CITED: docs.python.org/3/library/tempfile.html] | Safe on Windows with scanners holding handles |
| `Path.is_junction()` | stat `st_file_attributes` reparse bit | `is_junction` added in 3.12 | The project floor is 3.10, so use the stat bit |

**Deprecated/outdated:**
- KiCad 5 `.lib` / `.dcm` / `.mod`: rejected by design in v1; conversion is FMT2-01 (v2).
- `(module ...)` root head in `.kicad_mod`: pre-6 syntax (see Open Question 1).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Reference-prefix -> Type table beyond the D-01 literal list (`FB`, `LED`, `SW`, `K`, `TP`, `BT`, `F`, ...) | Pattern 5 | Cosmetic: wrong default Type, the user edits the name |
| A2 | `AGGREGATOR_HOSTS` list and the registered-domain heuristic (2-letter TLD + `co/com/org/net/ac/gov/edu`) | Pattern 5, Pitfall 10 | A distributor host could still yield a bogus low-confidence manufacturer; user edits the name |
| A3 | Extra host/alias entries (`invensense.com`, `maximintegrated.com`, `linear.com`, `analogdevices`) map to `TDK`/`ADI` | Pattern 5 | Wrong token suggested; mitigated because confidence is shown and the name is editable. Repo evidence exists for the MAX/LTC -> ADI filing |
| A4 | A `.kicad_mod` with a `(module ...)` head should be accepted with a WARNING rather than treated as legacy | Pitfall 7, Open Question 1 | If KiCad 6+ cannot load such a file, Phase 4 would install a footprint KiCad cannot read. Needs user confirmation |
| A5 | A package with no v6+ symbol, no v6+ footprint and no legacy files (e.g. STEP only) is an ERROR `intake.nothing_found` | Pattern 4 | A user wanting to attach only a model gets refused; that case is FMT2-02 (v2) anyway |
| A6 | Refusing `:` anywhere in a member name, duplicates (casefolded) and encrypted members goes beyond the D-05 list | Pattern 1 | Slightly stricter than CONTEXT; a legitimate vendor zip with such names would be refused (none seen) |
| A7 | Windows reserved-device behaviour applies to the segment before the first dot, and `COM¹` style names are reserved | Pattern 6 | Under-protection of an exotic name; the NFKD step already turns `¹` into `1` |
| A8 | The Windows reparse-point attribute `0x400` can appear in the low bits of `external_attr` for symlink/junction members | Pattern 1 | None: it is only an extra refusal |
| A9 | Folder intake caps (same constants), depth 8 and skip-links policy | Pattern 2 | A very large legitimate folder would be refused; constants are in one place |
| A10 | Mapping to ASVS V12 (file/resource handling) and V5 (input validation) | Security Domain | Documentation label only |
| A11 | UL `KiCADv5` is the UL layout for KiCad 5 downloads, with `.lib`/`.dcm` | Pattern 3 | Only one UL sample exists; a v5 zip is rejected through the legacy matrix either way |

## Open Questions

1. **Are `(module ...)` `.kicad_mod` files "v6+"?**
   - What we know: KiCad 5 wrote `.kicad_mod` files with a `(module` head; `kicad_files.footprint_name` already accepts both heads.
   - What's unclear: whether the owner wants a SamacSys KiCad-5-era `.kicad_mod` accepted (KiCad 6+ reads and rewrites them) or refused under INTK-05.
   - Recommendation: accept with WARNING `intake.legacy_footprint_syntax` and record `format_version=None`; Phase 4's normalisation step (kicad-cli when available) handles it. Ask the owner during planning review (A4).
2. **Should a Reference of `U` for a discrete MOSFET really suggest `IC`?** Locked by D-01/D-04 and the expected `IC_SubCategory_TI`; no action, only a reminder that the owner expects to edit it.
3. **Where does `Package` live when Phase 5 runs intake in a worker thread?** The `with` block must span intake and the later plan/install, or the dialog must hold the `Package` and call `close()`. Provide both `__enter__/__exit__` and an idempotent `close()`; Phase 5 decides.
4. **Should `kicad_files.py` gain `file_kind` / `file_version` read helpers now?** Recommended (tiny, tested) so the importer does not touch `Node` internals; this is an additive change to a Phase 1 module and the layering test's `ALLOWED` map is unaffected.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (venv `env/`) | everything | yes | 3.14.4 (system `py`); venv built from the same install | -- |
| pytest | verification (D-14) | yes | 9.1.1 (`requirements-dev.txt`); baseline 553 passed, 3 skipped, about 11 s | -- |
| `downloaded_examples/ul_CSD85301Q2.zip` | primary fixture | yes (committed, 6 members) | -- | -- |
| `Custom/` submodule contents | naming vocabulary tests | yes (10 `.kicad_sym`, 9 `.pretty`, 13 3D files) | -- | Tests should build a synthetic `Custom/` layout in `tmp_path`; use the real one only for a smoke test |
| `WurthElektronik/KiCad-Library` submodule | not required by Phase 3 | no (not checked out; 3 baseline tests skip) | -- | none needed |
| `kicad-cli` | not required by Phase 3 (Phase 4/6 concern) | no (not on PATH) | -- | none needed |
| git | not used by Phase 3 | yes | -- | -- |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none relevant to this phase.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (+ pytest-qt 4.5.0 already installed; Phase 3 tests do not need Qt) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `pythonpath = ["."]`, `addopts = "-ra --strict-markers"`. New markers, if any, must be registered there |
| Quick run command | `.\env\Scripts\python.exe -m pytest tests/test_package_zip.py tests/test_adapters.py tests/test_naming_sanitize.py tests/test_naming_suggest.py -q` |
| Full suite command | `.\env\Scripts\python.exe -m pytest -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INTK-01 | zip and folder of loose files both open; same result shape | unit | `pytest tests/test_package_folder.py tests/test_adapters.py -q` | Wave 0 |
| INTK-02 | UL sample: vendor `UltraLibrarian`, timestamp symbol -> `CSD85301Q2`, footprint `DQK0006B`, model `DLV0006A.stp` at root; unzipped UL folder behaves the same | unit (real fixture) | `pytest tests/test_adapters.py -k ultra -q` | Wave 0 |
| INTK-05 | legacy-only, half-legacy rejected (text has "re-download as KiCad v6+"); mixed v5/v6 uses v6 with one info Issue | unit (synthetic) | `pytest tests/test_legacy_rules.py -q` | Wave 0 |
| INTK-06 | traversal, absolute, drive-letter, UNC, backslash, symlink, duplicate, too many members, oversize, high ratio, nested two deep, lying header, encrypted, not-a-zip all refuse with an error Issue naming the member; nothing staged; staging outside repo; repo tree unchanged after opening the UL sample; cleanup removes the staging dir | unit (synthetic) | `pytest tests/test_package_zip.py -q` | Wave 0 |
| LIB-01 | UL sample suggests `IC_SubCategory_TI`, low confidence, placeholders `("SubCategory",)`; property-based manufacturer (`Texas Instruments` -> `TI`); aggregator host ignored; ranking deterministic and capped at 5; equal-to-existing flagged | unit | `pytest tests/test_naming_suggest.py -q` | Wave 0 |
| LIB-03 | hostile-name table (`/`, `:`, `CON`, `NUL.foo`, `COM1`, `..`, unicode, long); every existing `Custom/` name unchanged; original and sanitised both returned; extension case preserved; case-only clash warns | unit | `pytest tests/test_naming_sanitize.py -q` | Wave 0 |
| (layering) | `importer/` imports no Qt, no `main_window`/`widgets`; imports point downward; no `extractall` in source; `importer/__init__.py` has no code | static | `pytest tests/test_importer_layering.py -q` | Wave 0 |

### Sampling Rate
- **Per task commit:** the quick run command (under 30 s).
- **Per wave merge:** `.\env\Scripts\python.exe -m pytest -q` (baseline about 11 s plus new tests).
- **Phase gate:** full suite green before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_package_zip.py`, `tests/test_package_folder.py`, `tests/test_adapters.py`, `tests/test_legacy_rules.py`, `tests/test_naming_sanitize.py`, `tests/test_naming_suggest.py`, `tests/test_importer_layering.py`: all new
- [ ] `tests/conftest.py`: add `ul_zip` fixture (path under `REPO_ROOT / "downloaded_examples"`), `make_zip`, `symlink_info`, `lie_about_size` helpers (or a `tests/zipfixtures.py` helper module)
- [ ] A synthetic `Custom/` layout builder fixture (`Symbols/*.kicad_sym`, `Footprints/*.pretty`, `3DModels/`) so naming tests do not depend on the real submodule contents
- [ ] Extend `tests/test_layering.py` or add `test_importer_layering.py` covering `importer/**/*.py`
- Framework install: none (pytest already pinned).
- Optional hardening: add `downloaded_examples/** -text` to `.gitattributes` (currently only `tests/fixtures/** -text`) so STEP/zip fixtures added in Phase 7 are never line-ending-converted [VERIFIED: .gitattributes read this session].

## Security Domain

`security_enforcement` is enabled in `.planning/config.json` (`"security_enforcement": true`, `"security_asvs_level": 1`, `"security_block_on": "high"`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | -- (local single-user tool) |
| V3 Session Management | no | -- |
| V4 Access Control | no | -- |
| V5 Input Validation | yes | Pre-scan of every archive member; allow-listed extensions; `sanitize_name`; strict UTF-8 decode via `fsutil.decode_source`; sexpr parse errors become Issues |
| V6 Cryptography | no | SHA-256 via `hashlib` only for content identity, not security |
| V12 Files and Resources | yes | Zip-bomb caps (count, per-member, total, ratio), no `extractall`, generated staging names, staging outside repo, symlink/junction refusal, temp cleanup [ASSUMED mapping: ASVS 4.0 V12.1 file upload / V12.3 file execution] |

### Known Threat Patterns for Python zip/file intake

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Zip slip (`..`, absolute, drive letter, UNC, backslash) | Tampering | Normalise separators, check every segment, never build paths from member names (generated staged names), refuse whole package (D-05) |
| Symlink / junction member or folder entry | Tampering / Information disclosure | Refuse symlink members; skip symlinks and junctions in folders; never create links |
| Zip bomb (many members, huge member, high ratio, nested) | Denial of service | Caps in D-06, nesting limit D-08, counted copy, ratio only above 1 MiB |
| Lying size fields | Denial of service | CPython CRC + declared bound (verified) plus counted read loop |
| Duplicate/shadow members | Tampering / Spoofing | Refuse casefolded duplicates; open by `ZipInfo` |
| Alternate data stream name (`name:stream`) | Tampering | Refuse `:` in member names |
| Hostile names inside KiCad files (`(footprint "..\\..\\x")`) becoming paths | Tampering | `sanitize_name` on every name that will become a file name; consumers re-check containment at write time (Phase 4) |
| Staging inside the repo, polluting the next scan | Tampering | Verify `resolve()`d staging path outside repo root; refuse otherwise |
| Opening bundled HTML guides (embedded SVG/JS) | Elevation of privilege | Never stage or open `.html`; names only (D-07). Never render in a web view |
| Invalid UTF-8 / huge text file | Denial of service | Strict decode Issue; per-member cap |
| Temp files left behind on error | Information disclosure | Context-manager cleanup, also on refusal and exception paths |

## Sources

### Primary (HIGH confidence)
- Local files read this session: `03-CONTEXT.md`, `REQUIREMENTS.md`, `STATE.md`, `kicad_lib_manager/models.py`, `kicad_files.py`, `fsutil.py`, `sexpr.py`, `library_scanner.py` (SKIP_DIRS), `tests/conftest.py`, `tests/test_layering.py`, `tests/test_fixtures.py`, `pyproject.toml`, `requirements*.txt`, `.gitattributes`, `.gitignore`, `.planning/research/{SUMMARY,ARCHITECTURE,PITFALLS}.md` sections, `reports/KiCad 10 vendor part import.md` (embedded_files section)
- Probes run on Python 3.14.4 / Windows 11 with `py -I`: zip name normalisation, lying sizes, symlink bits, duplicates, ratio, encryption, nested zips, `urlsplit` edge cases, NFKD behaviour, `stat.FILE_ATTRIBUTE_REPARSE_POINT`; UL sample member listing, symbol, footprint and STEP header dump; sanitiser prototype over `Custom/`; property survey of `Custom/` symbols
- Baseline test run: 553 passed, 3 skipped

### Secondary (MEDIUM confidence)
- docs.python.org `tempfile` / `zipfile` (general behaviour, `ignore_cleanup_errors` since 3.10) [CITED, not re-fetched this session; training knowledge corroborated by probes]
- OpenSSF Secure Coding Guide for Python (zip slip, CWE-409) [CITED via search result titles/summaries only]

### Tertiary (LOW confidence)
- Web search on Ultra Librarian layout: confirmed only that UL KiCad 6 exports contain a `.pretty` folder, a `.kicad_sym`, and a separately loaded STEP; it did not confirm the `KiCADv6/` folder name. Only the committed sample supports the marker names. [Search results: app.ultralibrarian.com KiCad 6.0+ help, docs.tscircuit.com]
- All `[ASSUMED]` table contents (A1-A11)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. Stdlib only, behaviours probed on the target interpreter.
- Architecture: HIGH. Matches the locked decisions and the earlier project research; module layout is within Claude's discretion.
- Zip safety rules: HIGH for the CPython behaviours probed; MEDIUM for the extra recommended refusals (A6, A8).
- Vendor detection: MEDIUM. One real UL sample; markers are scored, not required. SnapEDA/CSE are Phase 7.
- Naming suggestion tables: MEDIUM. Seeded from repo evidence; the broader tables are assumptions (A1-A3).
- Sanitiser: HIGH. Prototype reproduces all 64 existing names unchanged.
- Pitfalls: HIGH for the verified ones; flagged individually otherwise.

**Research date:** 2026-10-19
**Valid until:** 2026-11-18 for stdlib behaviour (stable); re-check vendor-layout assumptions when a SnapEDA or SamacSys sample is added (Phase 7).
