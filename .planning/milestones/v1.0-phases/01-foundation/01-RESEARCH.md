# Phase 1: Foundation - Research

**Researched:** 2026-10-18
**Domain:** Python test harness (pytest + pytest-qt, offscreen Qt) and a stdlib-only lossless S-expression + atomic file-IO layer for KiCad files, on Windows 11 / CPython 3.14
**Confidence:** HIGH (every load-bearing claim below was exercised against this machine's real files, a fresh venv, or prototype code run this session)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Round-trip test corpus**
- **D-01:** The round-trip identity test uses two sources:
  - **Live discovery:** at test time, glob every `.kicad_sym` / `.kicad_mod` under `Custom/` (and `WurthElektronik/` when present), so new parts are covered automatically.
  - **Frozen set:** a small committed fixture set under `tests/fixtures/`. It covers edge cases such as CRLF and LF variants, strings containing parens and escaped quotes, a BOM file and a mixed-EOL file. Core tests must pass even with an uninitialised submodule.
- **D-02:** Lib-table round-trips have two sources:
  - **Committed synthetic fixtures:** hand-written `sym-lib-table` / `fp-lib-table` files covering escaped `"` and `\`, reordered fields, odd whitespace, unknown children and missing optional fields.
  - **Opt-in local tables:** the real global tables in `%APPDATA%/kicad/*/` (7.0, 8.0 and 9.0 exist on the owner's machine) are round-tripped when present and skipped when absent. Real personal tables are never copied into the repo.
- **D-03:** WurthElektronik tests carry a marker (e.g. `wurth`) and skip with a clear reason when the submodule is empty. It is currently not checked out in this worktree. When it is present it doubles as the stress and performance corpus.
- **D-04:** Commit `downloaded_examples/ul_CSD85301Q2.zip` to the parent repo (`sylvanoMTL/kicad_libraries`, which is private), not to `Custom/`. The round-trip test reads the `.kicad_sym` (format `20211014`) and `.kicad_mod` members straight from the zip into memory, without extracting into the repo. Phases 3 and 4 reuse it. — **Reversibility:** costly — removing a vendor file from git history once pushed requires a history rewrite of the parent repo.

**Write failure and backups**
- **D-05:** Atomic write sequence: temp file in the same directory, write, `flush` + `os.fsync`, then `os.replace`.
  - If `os.replace` fails with `PermissionError` (Windows lock, antivirus or indexer), retry briefly, about 1 second in total.
  - If it still fails, delete the temp file, leave the original byte-identical, and return an error Issue such as "Could not write X: file is in use".
  - A read-only target also produces an error Issue. No crash and no truncated file.
  - Do not use `NamedTemporaryFile(delete=True)` on Windows.
- **D-06:** The backup helper has the signature `backup_file(path, backup_dir)`, and the caller chooses `backup_dir`. Backups are numbered, matching the existing `<name>_backup_<N>` scheme in `table_generator.backup_existing`.
  - Library tables keep today's side-by-side `*_backup_*` files (already gitignored; the Restore dialog depends on them).
  - Files inside `Custom/` (Phase 4) and `kicad_common.json` (Phase 2) back up to an app-data directory outside the repo, e.g. `%LOCALAPPDATA%/KiCadExtLibManager/backups/`, so backups never show up in `git status`.
  - The exact app-data path and its cross-platform equivalent are Claude's discretion.
- **D-07:** Add `Severity` (info / warning / error, plus success if the log panel needs it) and `Issue(severity, code, text)` to `kicad_lib_manager/models.py` now. All new foundation code returns Issues and does not raise for expected failures. Existing `list[str]` callers are untouched in Phase 1; Phase 2 converts them, which ends the substring-based classification in `main_window` (`Warning:`, `Failed`, `not found`). — **Reversibility:** costly — once Phases 2-4 adopt Issue codes, changing the shape touches every service and the log routing.

**Line endings, encoding and .gitattributes**
- **D-08:** Add a parent-repo `.gitattributes` containing only `tests/fixtures/** -text`, so CRLF and LF fixtures stay byte-exact under `core.autocrlf=true`. There is no repo-wide EOL policy and no `.gitattributes` in `Custom/`. The S-expression layer preserves whatever EOL each file has.
- **D-09:** Inserted text, such as a new property line, is converted to the file's dominant EOL (sniffed CRLF vs LF).
- **D-10:** A file with mixed CRLF and LF endings round-trips untouched. Inserts use the majority EOL, and a warning Issue names the file. Never normalise silently.
- **D-11:** Decode as strict UTF-8. A leading BOM, if present, is preserved byte-for-byte. Invalid UTF-8 produces an error Issue, and that file is never edited. Read and write with `newline=""` (or equivalent bytes handling) so EOLs are not translated.

**Phase 1 module scope**
- **D-12:** Phase 1 includes a minimal `kicad_files.py` read side: locate symbols (by name), properties (by name, value span), footprint name, `(model ...)` nodes and lib-table `(lib ...)` entries, each with spans. It provides the property locator that success criterion 3 needs. The write-side semantics (symbol insert/rename incl. `_u_s` sub-symbols and `extends`, footprint rename, model insert, version policy) stay in Phase 4. Phase 2 extends the read side as the scanner and table generator need it.
- **D-13:** `pyproject.toml` holds tool config only: `[tool.pytest.ini_options]` with testpaths, `qt_api = "pyside6"` and registered markers (e.g. `wurth`, `local_kicad`). There is no `[project]` metadata and no installable package. The app still runs as `python kicad_lib_manager.py`.
- **D-14:** Pin every dependency exactly. `requirements.txt`: `PySide6==6.12.0`. `requirements-dev.txt`: `-r requirements.txt`, `pytest==9.1.x` (the exact patch the researcher verified) and `pytest-qt==4.5.0`. Upgrades are deliberate.
- **D-15:** The offscreen Qt test is a `LibraryTableWidget` symbol-to-footprint sync test. Populate the widget from a hand-built `ScanResult` with two sources, then check two things: toggling a symbol selects and deselects its linked footprints, and the sync is scoped per source (changing Custom symbols doesn't touch WurthElektronik footprints). This pins down current behaviour before Phase 2 changes rescans and nickname handling.

### Claude's Discretion
- Exact retry count and backoff inside the ~1 s window (D-05).
- App-data backup path naming and cross-platform equivalents (D-06).
- `Issue.code` naming scheme (e.g. dotted `fs.locked`, `sexpr.unbalanced`).
- Tokenizer internals: regex lexer, iterative tree build, the `SexprError(line, col)` shape, the `quote()` escape set (`"` and `\` at minimum), and the edit/splice API shape (`Edit(start, end, text)`, `apply_edits`). Follow the shape sketched in `.planning/research/ARCHITECTURE.md`.
- Fixture file selection and naming within `tests/fixtures/`.
- Whether the round-trip test checks the zip members of the UL sample individually or as one parametrised case.

### Deferred Ideas (OUT OF SCOPE)
- A repo-wide EOL policy (`*.kicad_sym *.kicad_mod text eol=lf`) in the parent and `Custom/`. It was offered and declined for Phase 1 because it needs a renormalisation commit. Revisit after the importer ships, if ever.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOUND-01 | Developer can install pinned runtime and dev dependencies from `requirements.txt` / `requirements-dev.txt` | Exact pins verified: `PySide6==6.12.0`, `pytest==9.1.1` (latest 9.1.x), `pytest-qt==4.5.0`. A fresh-venv install of exactly these pins succeeded on CPython 3.14.4 / Windows (see Standard Stack). |
| FOUND-02 | Headless pytest suite (`pytest`) with no display, including Qt tests in offscreen mode | Verified config: `pythonpath = ["."]` is REQUIRED for bare `pytest` to import the package (it fails without it); conftest forces `QT_QPA_PLATFORM=offscreen`; D-15 widget test skeleton verified passing (5/5) in the fresh venv. |
| FOUND-03 | Every `.kicad_sym`, `.kicad_mod` and lib-table file round-trips byte-identically through the S-expression layer | Prototype tokenizer parsed all 24 `Custom/` files, both UL zip members and all 7 real KiCad 7/8/9 user tables (31 files, 523 KB, 0.136 s) with zero errors. Corpus facts, the "tiling" test design (so the identity test is not vacuous) and fixture traps documented. |
| FOUND-04 | An edit changes only the targeted span, keeps CRLF/LF, rest byte-identical | Prototype splice of one `Value` property in a real CRLF file produced a 2-line diff, byte-delta equal to the replacement delta. `apply_edits` contract, EOL sniff/convert rules and test designs documented. |
| FOUND-05 | Atomic replace; locked or read-only target gives a logged error, not a crash or truncated file | Prototype `atomic_write_bytes` exercised on Windows 11: success, read-only (instant Issue), locked (1.01 s retry then Issue, original intact, temp removed), lock released mid-retry (succeeds), fsync failure injection, missing directory. |
</phase_requirements>

## Summary

Phase 1 is almost entirely greenfield Python with no new runtime dependencies. The stack is already decided and now verified: `PySide6==6.12.0`, `pytest==9.1.1` (9.1.1 is the newest 9.1.x on PyPI and is already installed in `env/`), and `pytest-qt==4.5.0` (newest release; the only package not yet installed). A fresh venv built from those exact pins installed cleanly on CPython 3.14.4 and a `LibraryTableWidget` test ran offscreen, with the repo's real widget code. The one configuration trap found: with only `testpaths` and `qt_api` in `pyproject.toml`, a bare `pytest` fails with `ModuleNotFoundError: No module named 'kicad_lib_manager'`; `pythonpath = ["."]` fixes it (and the root-level `kicad_lib_manager.py` module does not shadow the package of the same name; the package wins).

The S-expression layer is small and de-risked. A regex tokenizer with an iterative tree builder, node `(start, end)` spans and back-to-front splices parsed every real file available here (all of `Custom/`, the Ultra Librarian zip members, and the user's real 7.0/8.0/9.0 library tables including 246 `(disabled)` entries) in 0.14 s total, rejects unterminated strings and unbalanced parens with line/column, survives 5000-deep nesting, and a targeted `Value` edit changed exactly one line while preserving CRLF. The BOM must be stripped before tokenizing (otherwise it becomes a bogus first atom), so a `SourceText(text, bom, eol)` decode step belongs in `fsutil`. For atomic writes, `os.replace` over a read-only or held-open file raises `PermissionError` (WinError 5) immediately and leaves the original intact; a read-only target should be detected up front with `os.access` (no pointless 1 s retry) while a genuinely locked file gets the ~1 s retry window.

Four non-obvious planning hazards were found: (1) git ignores any fixture literally named `sym-lib-table` or `fp-lib-table` (`.gitignore` lines 2-3, unanchored), so D-02 fixtures must use a suffix naming scheme such as `<case>.sym-lib-table`; (2) the existing scanner `rglob`s the whole repo and its `SKIP_DIRS` does not include `tests`, so committed `tests/fixtures/*.kicad_sym` files would show up as a "tests" library source in the GUI (and Select All + Generate would write them into the user's tables); (3) fixtures with CRLF must be created with a bytes-exact method (Python `write_bytes`), because the agent Write tool and editors normalise EOLs, and the `.gitattributes` must be committed before the fixtures are staged; (4) the repo's own planning docs suggest `quote()` should escape tab, but KiCad's writer does not (see Pitfall 8).

**Primary recommendation:** Build in this order: (a) harness + manifests + `.gitattributes` + `pyproject.toml` + `conftest.py` + D-15 widget test, (b) `Severity`/`Issue` + `fsutil`, (c) `sexpr`, (d) `kicad_files` read side + corpus/round-trip tests, with the corpus tests written as "token tiling" checks plus an end-to-end bytes -> `SourceText` -> atomic write -> bytes identity so the identity requirement is not vacuous.

## Project Constraints (from CLAUDE.md)

Extracted from `./CLAUDE.md` and `./.claude/CLAUDE.md`. The planner must verify compliance; none of the recommendations below contradict them.

- **Stdlib only** beyond PySide6 unless a dependency is clearly justified (no kiutils, sexpdata, GitPython, filelock, hypothesis).
- **Python:** `py -m venv env` with standard Windows CPython, NOT MSYS2. Run tools with `.\env\Scripts\python.exe` (PowerShell). Floor is Python 3.10: no `Path.walk`, `Path.copy`, `enum.StrEnum` (3.11+), `tomllib` (3.11+) etc. in production code.
- **Typing/style:** `X | None`, builtin generics, no `from __future__ import annotations`; snake_case; `_private` helpers; UPPER_SNAKE module constants; one-line triple-double-quoted docstrings, no type info in docstrings; 4-space indent, double quotes, trailing commas; comments on the line above, terse; relative imports inside the package (`from .models import ...`); `__init__.py` files stay empty (no re-exports).
- **Error handling:** services are Qt-free and return values; side-effecting helpers report outcomes instead of raising (now `Issue`s, per D-07). No bare `except:`. `QMessageBox` only for About.
- **Dependency direction:** `models.py` has no internal imports; lower modules never import `main_window`; nothing below presentation imports Qt (only `settings.py` does).
- **Paths:** `pathlib.Path` everywhere; `.as_posix()` for KiCad-facing strings; `newline=""`/bytes for KiCad files.
- **Git:** commit messages descriptive with component context; `.gitignore` already excludes generated `sym-lib-table`/`fp-lib-table`, `env/`, `*_backup_*`, `__pycache__/`.
- **GSD workflow:** file edits happen through a GSD command (plan execution), not ad hoc.
- **Testing guidance in `.planning/codebase/TESTING.md`:** use `tmp_path` for every filesystem fixture, never write to the real repo or `%APPDATA%/kicad`; keep fixtures small and synthetic; do not copy real libraries from `Custom/` or `WurthElektronik/` into fixtures (the UL zip is the explicit D-04 exception).

## Architectural Responsibility Map

This is a desktop app with no web tiers; "tiers" are the project's own layers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Dependency manifests, pytest config, markers | Repo root (config) | — | `requirements*.txt` + `pyproject.toml` tool config only (D-13); no installable package |
| Lossless tokenizer, spans, `apply_edits`, `quote()` | Foundation service (`sexpr.py`, Qt-free) | — | Pure string logic; consumed later by scanner, table generator, importer |
| KiCad-aware locators (symbol, property, footprint name, model, lib entry) | Foundation service (`kicad_files.py`, Qt-free) | — | Reads `sexpr` trees; read side only in this phase (D-12) |
| Atomic write, backups, EOL/BOM/encoding sniffing | Foundation service (`fsutil.py`, Qt-free) | Filesystem | Single implementation reused by Phases 2-4; owns all expected-failure -> `Issue` conversion |
| `Severity` / `Issue` types | Domain model (`models.py`) | — | Must stay import-free; mapped by callers to `LogPanel` levels |
| Offscreen widget test | Presentation (`widgets/library_table.py`) | Test harness | Test-only; pins current behaviour, no widget change |
| Corpus discovery (live `Custom/`, Wurth, local KiCad tables, zip members) | Test harness (`tests/`) | Filesystem | Collection-time globbing; markers gate opt-in sources |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PySide6 | `==6.12.0` | GUI (existing); needed by the offscreen widget test | Already pinned in the project; published 2026-10-08; `requires_python <3.16,>=3.10`. [VERIFIED: PyPI JSON + `pip index versions` + fresh-venv install] |
| pytest | `==9.1.1` | Test runner | 9.1.1 is the newest 9.1.x on PyPI (`pip index versions pytest` lists 9.1.1, 9.1.0, 9.0.3 ...); published 2026-06-19; `requires_python >=3.10`; already installed in `env/`. [VERIFIED: `pip index versions pytest`, PyPI JSON, `env/` pip list] |
| pytest-qt | `==4.5.0` | `qtbot`, `qapp`, Qt-binding selection via `qt_api` | Newest release (2025-07-01), `requires_python >=3.9`, requires `pytest`, `pluggy>=1.1`, `typing_extensions`. Fresh install + offscreen widget test passed with PySide6 6.12.0. [VERIFIED: PyPI JSON, fresh-venv run] |

**D-14 answer (explicit):** pin **`pytest==9.1.1`**. `PySide6==6.12.0` and `pytest-qt==4.5.0` remain the right exact pins. Nothing newer exists for any of the three as of 2026-10-18.

### Supporting
None. Phase 1 adds no further packages. Resolved transitive set in the fresh venv (informational, not pinned): pluggy 1.7.0, iniconfig 2.3.1, packaging 26.3, Pygments 2.21.0, colorama 0.4.6, typing_extensions 4.16.0, shiboken6 6.12.0, PySide6_Essentials/Addons 6.12.0, PySide6_Pdf/WebEngine 6.12.0.140. [VERIFIED: `pip list` in the scratch venv]

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `PySide6==6.12.0` (metapackage, pulls Addons/WebEngine/Pdf) | `PySide6-Essentials==6.12.0` | Much smaller install; the app only needs QtCore/QtGui/QtWidgets. D-14 locks `PySide6`, so keep it; mention only if install size/time becomes an issue. |
| `pythonpath = ["."]` | `tests/__init__.py` + `python -m pytest` | `python -m pytest` alone works (cwd on `sys.path`) but the success criterion says bare `pytest`; `pythonpath` makes both work. |
| `strict = true` (pytest 9) | `addopts = "-ra --strict-markers"` | Both rejected an unregistered marker in a probe. `addopts` is less surprising (`strict` also enables strict xfail and parametrization-id checks). |
| hypothesis for fuzzing | seeded `random` generator in a test | hypothesis would be a new dependency; a ~30-line seeded generator is enough (CLAUDE.md: stdlib only). |

**Installation (verified in a scratch venv outside the repo):**
```powershell
py -m venv env                                   # only if env\ does not exist yet
.\env\Scripts\python.exe -m pip install -r requirements-dev.txt
.\env\Scripts\python.exe -m pytest
```
```text
# requirements.txt
PySide6==6.12.0

# requirements-dev.txt
-r requirements.txt
pytest==9.1.1
pytest-qt==4.5.0
```

**Version verification performed:** `pip index versions` for all three (latest: pytest 9.1.1, pytest-qt 4.5.0, PySide6 6.12.0); PyPI JSON for publish dates and `requires_dist`; a brand-new venv from `C:\Users\sylvain\AppData\Local\Python\pythoncore-3.14-64\python.exe` installed `requirements-dev.txt` with exit code 0 and `pytest` ran 5 tests green there.

## Package Legitimacy Audit

Seam command run: `gsd-tools query package-legitimacy check --ecosystem pypi pytest pytest-qt PySide6`.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| pytest | PyPI | long-established (9.1.1 published 2026-06-19) | seam returned `null` | github.com/pytest-dev/pytest | SUS (`unknown-downloads` only) | Flagged. Already installed in `env/` as 9.1.1. |
| pytest-qt | PyPI | 4.5.0 published 2025-07-01 | seam returned `null` | github.com/pytest-dev/pytest-qt | SUS (`unknown-downloads` only) | Flagged. The ONLY package not yet installed. |
| PySide6 | PyPI | 6.12.0 published 2026-10-08 (`too-new`) | seam returned `null` | pyside.org (Qt for Python) | SUS (`too-new`, `unknown-downloads`) | Flagged. Already installed in `env/` and the project's existing dependency. |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** pytest, pytest-qt, PySide6. All three SUS reasons are tooling artefacts (the seam has no download-count data; PySide6 6.12.0 is simply 10 days old). All three names are established by project docs (CLAUDE.md, STACK.md, CONTEXT.md D-14), by the official pytest-qt docs (pytest-qt.readthedocs.io lists PySide6 support), and both pytest packages live under the `pytest-dev` GitHub org. Per the gate protocol the planner should still add **one** `checkpoint:human-verify` before the install step (consolidated for the three pins, since only `pytest-qt` is actually new to `env/`). The `postinstall` signal is `null` for all three.

## Architecture Patterns

### System Architecture Diagram

```
 bytes (file on disk | zip member read in memory)
        │
        ▼
 fsutil.decode_source(data)  ── invalid UTF-8 ──► Issue(error, "fs.bad_encoding")  ──► STOP (never edited)
        │  strict UTF-8; strip leading BOM (remember it); sniff EOL counts
        ▼
 SourceText(text, bom, eol, mixed_eol)  ── mixed_eol ──► Issue(warning, "fs.mixed_eol", names the file)
        │
        ▼
 sexpr.parse(text) ── unbalanced/unterminated ──► SexprError(line, col) ──► kicad_files wrapper ──► Issue(error, "sexpr.*")
        │  iterative build; Node(start, end, kind, children)
        ▼
 kicad_files locators (read only): symbols / property value span / footprint name / (model) / (lib) entries
        │  each returns nodes carrying spans
        ▼
 caller builds [Edit(start, end, text)]   ◄── fsutil.normalize_eol(inserted_text, source.eol)
        │
        ▼
 sexpr.apply_edits(text, edits)  → new text  (untouched bytes never re-serialised)
        │
        ▼
 fsutil.encode_source(new_text, bom) → bytes
        │
        ├─► fsutil.backup_file(path, backup_dir)  → numbered "<name>_backup_<N>"  (caller picks backup_dir)
        ▼
 fsutil.atomic_write_bytes(path, data)
        │   read-only? ─► Issue(error, "fs.read_only") immediately
        │   temp (same dir, "xb") → write → flush → fsync → os.replace
        │   PermissionError → retry ~1 s → Issue(error, "fs.locked"); temp deleted; original untouched
        ▼
 None (success)  |  Issue
```

### Recommended Project Structure
```
Kicad_Libraries-importer/
├── requirements.txt            # PySide6==6.12.0
├── requirements-dev.txt        # -r requirements.txt, pytest==9.1.1, pytest-qt==4.5.0
├── pyproject.toml              # [tool.pytest.ini_options] ONLY (D-13)
├── .gitattributes              # tests/fixtures/** -text   (D-08; commit BEFORE adding fixtures)
├── downloaded_examples/
│   └── ul_CSD85301Q2.zip       # tracked (D-04); add this file only, not the whole directory
├── kicad_lib_manager/
│   ├── models.py               # + Severity, Issue (stdlib enum/dataclasses only)
│   ├── sexpr.py                # NEW tokenizer, Node, Edit, apply_edits, quote/unquote, SexprError
│   ├── fsutil.py               # NEW decode/encode_source, normalize_eol, atomic_write_*, backup_file, default_backup_dir
│   └── kicad_files.py          # NEW read side locators
└── tests/
    ├── conftest.py             # forces QT_QPA_PLATFORM=offscreen; repo_root + corpus helper fixtures
    ├── fixtures/               # frozen edge-case files (bytes-exact, see Pitfall 3)
    │   ├── sexpr/              # lf/crlf/bom/mixed/parens-in-strings/escapes ... (.kicad_sym / .kicad_mod)
    │   └── tables/             # <case>.sym-lib-table, <case>.fp-lib-table  (NOT bare names, Pitfall 1)
    ├── test_manifests.py       # FOUND-01
    ├── test_library_table_widget.py   # FOUND-02 (D-15)
    ├── test_sexpr.py           # tokenizer/edit unit tests (FOUND-03/04)
    ├── test_roundtrip_corpus.py       # FOUND-03 (live, frozen, zip, local tables, wurth)
    ├── test_edits.py           # FOUND-04
    ├── test_fsutil.py          # FOUND-05
    ├── test_kicad_files.py     # D-12 locators
    ├── test_models.py          # Severity/Issue
    └── test_layering.py        # sexpr/kicad_files/fsutil/models import no PySide6
```

### Pattern 1: Parse for navigation, splice for mutation
**What:** `parse(text)` yields nodes with `(start, end)` offsets into the decoded `str`; every change is an `Edit(start, end, text)`; `apply_edits` splices back-to-front equivalents and never re-serialises.
**When to use:** Any change to an existing KiCad file.
**Example (prototype, run against the real corpus):**
```python
# Source: prototype validated this session (31 real files, 0.136 s); shape from .planning/research/ARCHITECTURE.md
import re
from dataclasses import dataclass

_TOKEN = re.compile(
    r'(?P<open>\()|(?P<close>\))'
    r'|(?P<str>"(?:[^"\\]|\\.)*")'          # quoted string; backslash escapes any char
    r'|(?P<atom>[^ \t\r\n()"]+)'             # bare atom (ASCII whitespace only separates, like KiCad's lexer)
    r'|(?P<ws>[ \t\r\n]+)'
    r'|(?P<bad>.)',                          # stray char or unterminated string -> error
    re.S,
)

class SexprError(ValueError):
    def __init__(self, message: str, line: int, col: int):
        super().__init__(f"{message} at line {line}, col {col}")
        self.line, self.col = line, col

@dataclass(slots=True, eq=False)             # eq=False/slots: no recursive __eq__/__repr__ blowups on deep trees
class Node:
    start: int
    end: int
    kind: str                                # "list" | "str" | "atom"
    children: list["Node"]
    text: str = ""

def parse(text: str) -> Node:
    root = Node(0, len(text), "list", [])
    stack = [root]                           # ITERATIVE: no recursion limit on hostile nesting
    for m in _TOKEN.finditer(text):
        kind = m.lastgroup
        if kind == "ws":
            continue
        if kind == "bad":                    # raise at the FIRST bad char: keeps failure O(n), not O(n^2)
            raise SexprError("unterminated string or stray character", *_line_col(text, m.start()))
        if kind == "open":
            node = Node(m.start(), -1, "list", [])
            stack[-1].children.append(node)
            stack.append(node)
        elif kind == "close":
            if len(stack) == 1:
                raise SexprError("unbalanced ')'", *_line_col(text, m.start()))
            stack.pop().end = m.end()
        else:
            stack[-1].children.append(Node(m.start(), m.end(), kind, [], m.group()))
    if len(stack) != 1:
        raise SexprError("unclosed '('", *_line_col(text, stack[-1].start))
    return root

@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    text: str

def apply_edits(src: str, edits: list[Edit]) -> str:
    out, pos = [], 0
    for e in sorted(edits, key=lambda e: (e.start, e.end)):   # zero-width inserts at p sort before a replace starting at p
        if e.start < pos or not 0 <= e.start <= e.end <= len(src):
            raise ValueError("overlapping or out-of-range edits")
        out += [src[pos:e.start], e.text]
        pos = e.end
    out.append(src[pos:])
    return "".join(out)
```
`_line_col(text, pos)` is `text.count("\n", 0, pos) + 1` and `pos - (text.rfind("\n", 0, pos) + 1) + 1`. Unfinished design points left to the planner: `apply_edits` raising `ValueError` vs returning an `Issue` (D-07 says expected failures return Issues; overlapping edits are a programmer error, so raising is defensible and should be documented), and whether `Node` carries a `.head` convenience.

### Pattern 2: Decode once, carry BOM + EOL beside the text
```python
# Source: design from D-09/D-10/D-11; BOM behaviour verified by prototype (a leading U+FEFF otherwise tokenises as a bogus first atom)
@dataclass(frozen=True)
class SourceText:
    text: str            # BOM removed, newlines untranslated
    bom: bool
    eol: str             # "\r\n" if CRLF count > LF count else "\n"  (ties and no-EOL files -> "\n", KiCad's native output)
    mixed_eol: bool      # True if both CRLF and bare LF (or a bare CR) occur
    issues: tuple[Issue, ...] = ()   # e.g. warning "fs.mixed_eol" naming the file
```
Recommended API (names are discretion): `decode_source(data: bytes, name: str) -> SourceText | Issue`, `read_source(path) -> SourceText | Issue` (read via `Path.read_bytes()`, never text mode), `encode_source(text: str, bom: bool) -> bytes`, `normalize_eol(text: str, eol: str) -> str` (`replace("\r\n","\n").replace("\r","\n")` then `replace("\n", eol)`). The same `decode_source` serves the zip-member round-trip test (D-04), so file and in-memory paths are identical.

### Pattern 3: Atomic write that distinguishes "read-only" from "locked"
```python
# Source: prototype exercised on Windows 11 / CPython 3.14.4 this session (see Validation Architecture for the matrix)
_RETRY_DELAYS = (0.05, 0.1, 0.2, 0.3, 0.35)      # sums to 1.0 s: inside the D-05 "about 1 second"

def atomic_write_bytes(path, data, *, retry_delays=_RETRY_DELAYS, sleep=time.sleep) -> Issue | None:
    path = Path(path)
    if path.exists() and not os.access(path, os.W_OK):       # read-only: fail NOW, no pointless retries
        return Issue(Severity.ERROR, "fs.read_only", f"Could not write {path.name}: file is read-only")
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")   # unique, same dir, ends .tmp
    try:
        with open(tmp, "xb") as f:                            # exclusive create; NOT NamedTemporaryFile(delete=True)
            f.write(data); f.flush(); os.fsync(f.fileno())
        for attempt in range(len(retry_delays) + 1):
            try:
                os.replace(tmp, path)
                return None
            except PermissionError:                           # WinError 5: held open without delete-sharing, AV, indexer
                if attempt == len(retry_delays):
                    return Issue(Severity.ERROR, "fs.locked", f"Could not write {path.name}: file is in use")
                sleep(retry_delays[attempt])
    except OSError as e:                                      # disk full, missing dir, etc.
        return Issue(Severity.ERROR, "fs.write_failed", f"Could not write {path.name}: {e.strerror or e}")
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass                                              # already replaced (FileNotFoundError) or unremovable
```
Make `retry_delays`/`sleep` injectable so unit tests do not wait a real second. `atomic_write_text(path, text, *, bom=False)` is `atomic_write_bytes(path, encode_source(text, bom))`.

### Pattern 4: Numbered backup compatible with the existing scheme
`backup_file(path, backup_dir)` must produce names identical to `table_generator.backup_existing`, which today is (verbatim, `kicad_lib_manager/table_generator.py:157,164`):
```python
    pattern = re.compile(re.escape(base_name) + r"_backup_(\d+)$")
    backup_name = f"{base_name}_backup_{max_num + 1}"
```
i.e. `max(existing N in backup_dir) + 1`, copy with `shutil.copy2`. Create `backup_dir` if missing (`mkdir(parents=True, exist_ok=True)`), create the destination exclusively (retry the next number on `FileExistsError`), return `Path | Issue`. With `backup_dir=path.parent` the output equals `backup_existing`'s, which keeps the Restore dialog working when Phase 2 switches over. `list_backup_pairs` matches `sym-lib-table_backup_(\d+)$` (table_generator.py:224-225), so do not change the suffix format.

Default off-repo backup root (discretion): `default_backup_dir() -> Path` using only `os.environ`/`sys.platform` (fsutil must not import Qt):
- Windows: `%LOCALAPPDATA%\KiCadExtLibManager\backups` (fallback `Path.home()/"AppData/Local"`). `LOCALAPPDATA` is set on this machine. The org name `KiCadExtLibManager` matches `APP_ORG = "KiCadExtLibManager"` (`kicad_lib_manager/settings.py:14`).
- macOS: `~/Library/Application Support/KiCadExtLibManager/backups`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/KiCadExtLibManager/backups` [ASSUMED conventions]
Tests must always pass an explicit `tmp_path` backup dir (or monkeypatch the env) so they never write to the real app-data folder.

### Pattern 5: `Severity` and `Issue` in `models.py`
`models.py` currently contains only `@dataclass` classes and imports `from dataclasses import dataclass, field` (`models.py:1`); keep it import-light (stdlib `enum` is fine). `LogPanel.COLORS` keys are verbatim (`kicad_lib_manager/widgets/log_panel.py:8-13`): `"info": "#000000", "warning": "#CC7700", "error": "#CC0000", "success": "#007700"`. So:
```python
from enum import Enum

class Severity(str, Enum):          # NOT enum.StrEnum: that is 3.11+, the project floor is 3.10
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
`str(Severity.ERROR.value)` maps straight to `LogPanel.log(message, level)`, which is how Phase 2 will drop the substring classification. Keep the three fields exactly as D-07 states.
Suggested codes (discretion): `fs.read_only`, `fs.locked`, `fs.write_failed`, `fs.bad_encoding`, `fs.mixed_eol`, `fs.backup_failed`, `sexpr.unterminated`, `sexpr.unbalanced`, `sexpr.unclosed`, `kicad.not_a_symbol_lib` ...

### Pattern 6: `kicad_files.py` read side (D-12) matched to real file shapes
Verified structure on the real corpus:
- `.kicad_sym`: one top-level `(kicad_symbol_lib ...)`; its direct children are `version`, `generator`, optional `generator_version`, and `symbol` nodes (18 symbols across 10 files). Each top-level symbol has exactly one `(property "Footprint" "<Lib>:<FP>" ...)` as a direct child; unit sub-symbols are nested `(symbol ...)` children of the symbol, never top-level. Property name and value are the 2nd and 3rd children (`"Footprint"` / `"Connector_USB_GCT:GCT_USB4056-03-A_REVA2"`), values may be `""`.
- `.kicad_mod` (all 14 real files, UL sample too): `(footprint "NAME" (version ...) ...)`; the name is a quoted string. Legacy `(module NAME` with a bare atom exists in older KiCad, so the locator should accept both string and atom nodes. `(model "path" ...)` nodes are direct children of the footprint; counts in the corpus: 0 (2 files), 1 (11 files), 2 (`XCVR_NORA-W106-00B`). In the UL sample the footprint has none, and `(fp_text value DQK0006B ...)` uses a BARE atom, so never assume "value is a string".
- lib tables: root `(sym_lib_table|fp_lib_table|design_block_lib_table ...)` with a `(version 7)` child and `(lib (name "..")(type "..")(uri "..")(options "..")(descr ".."))` entries with NO whitespace between the sub-forms. In the user's real 9.0 sym table 246 of 511 entries carry an extra `(disabled)` child; every entry was otherwise exactly `name,type,uri,options,descr` in that order. (The current `_LIB_ENTRY_RE` cannot match a `(disabled)` entry, so today's regeneration would silently drop them; that is Phase 2 scope, HARD-01, but it confirms the priority.)

Recommended minimal API (names are discretion): `find_symbols(root) -> list[SymbolRef]` (name token + node, top-level only), `find_property(symbol_node, name) -> PropertyRef | None` (direct children only; exposes `name_node`, `value_node`, decoded `value`), `footprint_name(root) -> NameRef | None` (accept `str` or `atom`), `find_models(footprint_node) -> list[ModelRef]` (path token + node), `lib_table_entries(root) -> list[LibEntry]` (decoded `name/type/uri/options/descr` as `str | None`, plus `flags: tuple[str, ...]` for bare children such as `disabled`/`hidden`, plus `extras` for unknown children, plus the entry node span). Compare names by `unquote(token_text)`, never by raw token text. A `load(path)` convenience that turns `SexprError` into `Issue(ERROR, "sexpr.*", ...)` keeps D-07 ("return Issues, do not raise for expected failures") while `sexpr.parse` itself raises like `json.loads`.

### Anti-Patterns to Avoid
- **Re-serialising any tree.** Not even for "just the one node". Splice only.
- **Python text mode for KiCad files** (`read_text`/`write_text`): translates `\r\n` on Windows. Use `read_bytes` + strict decode, `write_bytes` through `atomic_write_bytes`.
- **A vacuous identity test.** `apply_edits(text, []) == text` is true for any parser, even a broken one. See the tiling test in Validation Architecture.
- **Recursion in the tokenizer, walkers, or `__repr__`/`__eq__`.** Hostile or generated nesting hits `RecursionError` (and pytest's failure output would try to repr a 5000-deep tree).
- **Opening, extracting or executing anything from `downloaded_examples/`.** Tests read zip members into memory only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Parsing KiCad files for edits | Regex on the raw file (`FOOTPRINT_RE`, `_LIB_ENTRY_RE` style) | `sexpr.parse` + `kicad_files` locators | The existing regexes already drop `(disabled)` entries and match the first `Footprint` property; strings can contain parens |
| Third-party S-expression libs | kiutils / sexpdata / kicad-skip | In-repo tokenizer | Measured lossy in prior research (kiutils drops `(hide yes)`, `exclude_from_sim`, re-indents; sexpdata discards layout) |
| Atomic file replace | Write-in-place or `shutil.move` | `fsutil.atomic_write_bytes` (temp + fsync + `os.replace`) | Truncated files on crash; `os.replace` is the single-step swap |
| Temp files for the swap | `NamedTemporaryFile(delete=True)` | `open(tmp, "xb")` with a unique name in the target directory | Cannot be renamed over a target while open on Windows (D-05) |
| Test runner glue for Qt | Hand-rolled `QEventLoop` / manual `QApplication` | `pytest-qt` `qtbot` + `qapp` | Creates the single QApplication, closes widgets, works with `qt_api = "pyside6"` |
| Headless display | Xvfb or a virtual desktop | `QT_QPA_PLATFORM=offscreen` | Built into Qt; verified on Windows with PySide6 6.12.0 |
| File locking | `filelock` | Retry on `PermissionError` + Issue | KiCad does not lock library files (prior STACK.md finding); a lock library protects against nothing real |
| Property-based fuzzing | hypothesis | Seeded stdlib `random` generator | No new dependency |

**Key insight:** every tool needed is stdlib or already pinned. The risk in this phase is not missing libraries; it is tests that pass trivially and edge cases (BOM, mixed EOL, ignored fixture names, scanner pollution) that only show up on this specific Windows + `autocrlf=true` + gitignore setup.

## Runtime State Inventory

Not applicable: this is a greenfield foundation phase (no rename, refactor or migration). Nothing existing is renamed; no stored data, service config, OS registrations, secrets or build artifacts carry a changed name. The only existing-state interaction is read-only (the user's `%APPDATA%\kicad\*\` tables in opt-in tests).

## Common Pitfalls

### Pitfall 1: Fixtures named `sym-lib-table` / `fp-lib-table` are silently git-ignored
**What goes wrong:** D-02's committed synthetic tables never reach the repo; tests pass locally and fail on a clean clone.
**Why it happens:** `.gitignore` lines 2-3 are the unanchored patterns `sym-lib-table` and `fp-lib-table`, which match at any depth. `git check-ignore -v` confirmed `tests/fixtures/sym-lib-table -> .gitignore:2:sym-lib-table` and `tests/fixtures/tables/fp-lib-table -> .gitignore:3:fp-lib-table`; `tests/fixtures/escaped.sym-lib-table` is NOT ignored. [VERIFIED: `git check-ignore -v`, `.gitignore:1-15` read this session]
**How to avoid:** name fixtures `<case>.sym-lib-table` / `<case>.fp-lib-table` (also avoid any `_backup_` substring, ignored by `.gitignore:15` `*_backup_*`). The corpus helper globs `tests/fixtures/tables/*.sym-lib-table` and `*.fp-lib-table`. Do not edit `.gitignore` to negate (it would change generated-table ignoring behaviour).
**Warning signs:** `git status` shows no new files in `tests/fixtures/tables/` after creating them.

### Pitfall 2: Committed fixtures become libraries in the GUI scan
**What goes wrong:** Scanner `find_symbol_libs` does `root.rglob("*.kicad_sym")` over the whole repo and skips only directories named in `SKIP_DIRS`; any `tests/fixtures/**.kicad_sym` appears as a source named `tests`, and Select All + Generate writes fixture libraries into the user's real tables.
**Why it happens:** verbatim `kicad_lib_manager/library_scanner.py:13`: `SKIP_DIRS = {"env", "venv", ".venv", ".git", ".claude", "__pycache__"}` and `_in_skip_dir` checks only the first path component (`rel[0] in SKIP_DIRS`). [VERIFIED: Read this session]
**How to avoid:** add `"tests"` to `SKIP_DIRS` as a one-line constant change in the same plan that adds fixtures, plus a tiny regression test, OR give fixtures non-library suffixes (e.g. `*.sym.fixture`) and load them by explicit name. The first is recommended (keeps real extensions so the corpus helpers and locators behave exactly as on real files). This is the only touch to an existing module in Phase 1 and it conflicts mildly with "existing modules are not rewired", so flag it to the user in the plan (Open Question 1). Avoid `.pretty` directories under `tests/` regardless; the footprint scan keys on `*.pretty` dirs.
**Warning signs:** after adding fixtures, the GUI scan reports extra libraries from `tests`.

### Pitfall 3: CRLF/BOM/mixed-EOL fixtures get silently normalised
**What goes wrong:** The fixture meant to be CRLF is committed as LF (or the reverse), so the EOL tests exercise nothing.
**Why it happens:** (a) the agent Write tool and most editors write LF; (b) `core.autocrlf=true` (set on the parent AND `Custom/`, no `.gitattributes`) converts on `git add`/checkout unless the path is `-text`; (c) `.gitattributes` must already be committed/present when fixtures are first staged.
**How to avoid:** create byte-exact fixtures with a Python/`printf` step (`Path.write_bytes(b"...\r\n...")`) or, better, build EOL variants programmatically inside the tests from one LF source into `tmp_path` and commit only a handful of frozen files; commit `.gitattributes` first. Verified in a scratch repo with `core.autocrlf=true`: `tests/fixtures/** -text` kept `lf`, `crlf`, `mixed` and BOM bytes exact through add/commit/delete/checkout (including a nested `sub/` path), while an unlisted `other/lf.kicad_sym` came back as CRLF. [VERIFIED: scratch-repo experiment, `git ls-files --eol`]. Add "fixture self-check" tests asserting each fixture has the EOL/BOM its name claims; they fail loudly if normalisation ever happens.
**Warning signs:** `git ls-files --eol tests/fixtures` shows `i/lf w/crlf` instead of `attr/-text`.

### Pitfall 4: Bare `pytest` cannot import `kicad_lib_manager`
**What goes wrong:** Success criterion 1 requires `pytest` (not `python -m pytest`); with only `testpaths` + `qt_api` it errors at collection.
**Why it happens:** pytest's default `prepend` import mode puts `tests/` (the conftest directory) on `sys.path`, not the repo root; `python -m pytest` happens to add the cwd.
**How to avoid:** `pythonpath = ["."]` under `[tool.pytest.ini_options]`. [VERIFIED: bare `pytest` -> `ModuleNotFoundError: No module named 'kicad_lib_manager'` without it; 5/5 pass with it, including when invoked from another cwd with `--rootdir`]. The root-level `kicad_lib_manager.py` does NOT shadow the `kicad_lib_manager/` package (package directories win on the same path entry). [VERIFIED: copied both into the probe project and ran]

### Pitfall 5: BOM becomes a bogus first token
**What goes wrong:** `"\ufeff(kicad_symbol_lib ..."` tokenizes as atom `'\ufeff'` followed by the real list; locators looking for "the single top-level form" misbehave and a naive write drops the BOM (violating D-11).
**How to avoid:** `decode_source` strips one leading U+FEFF, records `bom=True`, `encode_source` re-adds the 3 bytes. [VERIFIED: prototype parse of `"\ufeff(a)"` -> `[('atom', '\ufeff'), ('list', '')]`]. No real file in the corpus has a BOM; the frozen fixture covers it.

### Pitfall 6: Retrying a read-only target for a second
**What goes wrong:** A deterministic failure (read-only attribute) burns the whole retry window and reports "in use".
**How to avoid:** check `os.access(path, os.W_OK)` first (Windows reflects the read-only attribute: probe gave `os.access(W_OK) = False`, and `os.replace` over it fails instantly with `PermissionError: [WinError 5]`, original intact, temp left behind until cleaned). Retry only the remaining `PermissionError` case. Note: on POSIX a read-only file can still be replaced if the directory is writable, and root bypasses `os.access`; the explicit pre-check gives the same user-visible behaviour on every platform. [ASSUMED for POSIX/root behaviour; the Windows behaviour is verified]

### Pitfall 7: Leaking temp files and mode surprises
**What goes wrong:** A failed replace leaves `.name.<pid>.tmp` next to the library; with `tempfile.mkstemp` the replaced file would get mode 0600 on POSIX.
**How to avoid:** unique exclusive `open(tmp, "xb")` (default umask permissions), `finally: tmp.unlink()` swallowing `OSError`, temp names end in `.tmp`. (`Custom/.gitignore` ignores `*.tmp`; the parent `.gitignore` does not, so cleanup in `finally` is what keeps the parent clean.) Tests assert the directory listing equals `[target]` after every failure case.

### Pitfall 8: `quote()` escape set contradicts one project doc
**What goes wrong:** `.planning/research/PITFALLS.md` (Pitfall 15) suggests encoding tab as `\t`. KiCad's own writer does not.
**Evidence:** KiCad `OUTPUTFORMATTER::Quotes` escapes exactly four characters: newline -> `\n`, carriage return -> `\r`, backslash -> `\\`, double quote -> `\"`; everything else (including tab) is copied raw. The reader (`DSNLEXER::NextTok`) accepts `\" \\ \a \b \f \n \r \t \v`, `\xHH` and 1-3 digit octal. [CITED: gitlab.com/kicad/code/kicad/-/raw/master/common/richio.cpp and common/dsnlexer.cpp, fetched this session; the fetch tool summarised the source, so re-check against an actual KiCad-saved fixture in Phase 4]
**How to avoid:** `quote(s)` = wrap in `"`, escaping `\` first (single-pass translate, never replace-twice), then `"`, `\n`, `\r`; leave tab raw. `unquote()` decodes at least `\\ \" \n \r \t`; for other escapes keep them verbatim rather than guessing. Copy unedited strings by span, never decode/re-encode.

### Pitfall 9: Mixed lexer assumptions
**What goes wrong:** KiCad's lexer treats only space, `\n`, `\r`, `\t` and NUL as separators (plus parens) [CITED: dsnlexer.cpp]; Python's `\s` also matches NBSP, `\x0b`, `\x0c`, `\u2028`, so `\s` would split atoms KiCad does not.
**How to avoid:** use explicit `[ \t\r\n]` classes (as in the prototype). Round-trip identity does not depend on this (nothing is re-serialised), but locators comparing atoms do.

### Pitfall 10: Shell heredocs mangle backslashes
**What goes wrong:** A script containing the string regex `r'"(?:[^"\\]|\\.)*"'` written through a shell heredoc in this environment arrived with one level of backslashes stripped (`[^"\]`), producing `re.PatternError: unterminated character set`. [VERIFIED: observed this session; worked around with `chr(92)`]
**How to avoid:** executors must create source files with the Write/Edit tools, not shell heredocs/`echo`, and a unit test for the regex (strings with `\"`, `\\`, trailing backslash, parens inside strings) will catch any mangling immediately.

### Pitfall 11: Collection-time parametrization over an empty corpus
**What goes wrong:** With `Custom/` uninitialised, `parametrize` over an empty list reports an unexplained skip; with Wurth absent (it is, in this worktree: `WurthElektronik/KiCad-Library` has 0 entries) nothing says why.
**How to avoid:** one explicit always-collected test per optional source that calls `pytest.skip("WurthElektronik submodule not checked out (git submodule update --init)")` when empty, run with `-ra` in `addopts` so reasons print. Mark the per-file Wurth params with `pytest.mark.wurth` and local-table params with `pytest.mark.local_kicad` (use `pytest.param(path, id=rel_posix, marks=...)`). Register both markers and use `--strict-markers` (verified to fail collection on an unregistered marker).

### Pitfall 12: `tests/` and dev tooling picked up by the wrong consumers
Besides Pitfall 2 (scanner), note `testpaths = ["tests"]` keeps pytest out of `env/`, `Custom/` and `WurthElektronik/`. Keep `-ra --strict-markers` in `addopts`. Do NOT add `filterwarnings = error` without trying it against PySide6 on the real `env/` first (a probe with `-W error` passed here, so it is optional, not required).

## Code Examples

### `pyproject.toml` (verified with pytest 9.1.1 + pytest-qt 4.5.0)
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-ra --strict-markers"
qt_api = "pyside6"
markers = [
    "wurth: needs the WurthElektronik submodule checked out (stress/perf corpus)",
    "local_kicad: reads the user's real KiCad config tables under the OS config dir (opt-in, read-only)",
]
```
`[tool.pytest.ini_options]` works unchanged in pytest 9.1.1 (pytest 9 also supports native `pytest.toml`/`[tool.pytest]`; D-13 keeps `ini_options`, which was verified). `qt_api` is documented at pytest-qt.readthedocs.io (the `PYTEST_QT_API` env var overrides it). [CITED: pytest-qt.readthedocs.io/en/latest/intro.html]

### `tests/conftest.py`
```python
import os

# Force (not setdefault): a developer shell with QT_QPA_PLATFORM=windows must not open real windows.
os.environ["QT_QPA_PLATFORM"] = "offscreen"
```
Set before any PySide6 import (conftest is imported before test modules). Add a test asserting `QGuiApplication.platformName() == "offscreen"` so the claim is machine-checked. [VERIFIED in the fresh venv]

### D-15 widget test (verified 5/5 passing in the fresh venv against the real `LibraryTableWidget`)
```python
import pytest
from PySide6.QtCore import Qt

from kicad_lib_manager.models import FootprintLibrary, FootprintRef, ScanResult, SymbolLibrary
from kicad_lib_manager.widgets.library_table import LibraryTableWidget


@pytest.fixture
def scan():
    return ScanResult(
        symbol_libs=[
            SymbolLibrary("Sym_C", "Custom/Symbols/Sym_C.kicad_sym", "Custom",
                          footprint_refs=[FootprintRef("FP_C", "A", True)]),
            SymbolLibrary("Sym_W", "WurthElektronik/KiCad-Library/symbols/Sym_W.kicad_sym",
                          "WurthElektronik", footprint_refs=[FootprintRef("FP_W", "B", True)]),
        ],
        footprint_libs=[
            FootprintLibrary("FP_C", "Custom/Footprints/FP_C.pretty", "Custom"),
            FootprintLibrary("FP_W", "WurthElektronik/KiCad-Library/footprints/FP_W.pretty", "WurthElektronik"),
        ],
    )


def _sym_item(widget, source_idx, child_idx=0):
    return widget._sym_tree.topLevelItem(source_idx).child(child_idx)   # sources are sorted: Custom=0, WurthElektronik=1


def test_toggle_is_scoped_per_source(qtbot, scan):
    w = LibraryTableWidget()
    qtbot.addWidget(w)
    w.populate(scan)
    sym_c, sym_w = scan.symbol_libs
    fp_c, fp_w = scan.footprint_libs
    _sym_item(w, 1).setCheckState(0, Qt.CheckState.Checked)        # Wurth symbol on
    assert (sym_w.selected, fp_w.selected, fp_c.selected) == (True, True, False)
    _sym_item(w, 0).setCheckState(0, Qt.CheckState.Checked)        # Custom symbol on
    assert (fp_c.selected, fp_w.selected) == (True, True)
    _sym_item(w, 0).setCheckState(0, Qt.CheckState.Unchecked)      # Custom symbol off
    assert (fp_c.selected, fp_w.selected) == (False, True)         # Wurth footprint untouched
    assert w._fp_items["FP_W"].checkState(0) == Qt.CheckState.Checked
```
The behaviour pinned here is `LibraryTableWidget._sync_footprint_selection(source)` (`library_table.py:171-192`), whose per-source guard is verbatim `if not fp_lib or fp_lib.source != source:` / `continue  # Only manage footprints from the affected source`. Also verified: checking the "Custom" group header selects Custom symbols and footprints only, and `select_all()`/`deselect_all()` flip everything. The tests reach into `_sym_tree`/`_fp_items` (private attributes); that is acceptable for a behaviour-pinning test but keep all private access in one helper so Phase 2 can adapt it.

### Corpus helper and round-trip identity (non-vacuous)
```python
# tests/test_roundtrip_corpus.py (shape)
import re, zipfile
from pathlib import Path
import pytest
from kicad_lib_manager import fsutil, sexpr

REPO = Path(__file__).resolve().parent.parent
ZIP = REPO / "downloaded_examples" / "ul_CSD85301Q2.zip"
WS = re.compile(r"[ \t\r\n]*")

def _tiles(text: str, root: sexpr.Node) -> bool:
    """Independent check: tokens (flattened iteratively) + inter-token gaps rebuild the text exactly."""
    ...                                  # walk with an explicit stack; gaps must fullmatch WS

def _check(data: bytes, name: str):
    src = fsutil.decode_source(data, name)
    assert not isinstance(src, fsutil.Issue)
    root = sexpr.parse(src.text)
    assert _tiles(src.text, root)                                   # spans are correct, not just "no edits"
    assert sexpr.apply_edits(src.text, []) == src.text
    assert fsutil.encode_source(src.text, src.bom) == data          # bytes -> SourceText -> bytes identity (BOM, CRLF, mixed)
```
Parametrize over: live `Custom/**/*.kicad_sym|*.kicad_mod`, `tests/fixtures/sexpr/*`, `tests/fixtures/tables/*.sym-lib-table|*.fp-lib-table`, the UL zip members (`.kicad_sym`/`.kicad_mod` only; check `info.file_size` against a small cap before `zf.read`), the opt-in local tables, and Wurth files. Use relative POSIX paths as test ids. Never extract the zip.

### Targeted edit test (FOUND-04)
```python
def test_value_edit_changes_only_its_span(corpus_sym_file):
    src = fsutil.read_source(corpus_sym_file)
    root = sexpr.parse(src.text)
    sym = kicad_files.find_symbols(root)[0]
    value = kicad_files.find_property(sym.node, "Value").value_node
    new = sexpr.apply_edits(src.text, [sexpr.Edit(value.start, value.end, sexpr.quote("NEWVAL"))])
    assert new[:value.start] == src.text[:value.start]
    assert new[value.start + len(sexpr.quote("NEWVAL")):] == src.text[value.end:]
    assert new.count("\r\n") == src.text.count("\r\n") and new.count("\n") - new.count("\r\n") == src.text.count("\n") - src.text.count("\r\n")
```
(Prototype result on `Custom/Symbols/Connector_USB_GCT.kicad_sym`, a CRLF file: the diff was exactly `-\t\t(property "Value" "USB4056-03-A_REVA2"\r\n` / `+\t\t(property "Value" "NEWVAL"\r\n`, length delta -12.)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `[pytest]` in `pytest.ini` / `[tool.pytest.ini_options]` | pytest 9 also supports native `pytest.toml` / `[tool.pytest]` | pytest 9.0 | Not adopted: D-13 keeps `[tool.pytest.ini_options]`, which works unchanged on 9.1.1 |
| `strict` flags scattered | pytest 9 `strict = true` umbrella | pytest 9.x | Verified working but opt for explicit `--strict-markers` in `addopts` |
| `kiutils`-style parse/dump | span-preserving tokenizer | project decision (see prior research) | Zero dependency, byte-exact |

**Contradictions with prior project research (for the planner to resolve in favour of this document):**
- STACK.md's atomic-write snippet retries on every `PermissionError` with `0.1 * 2**attempt` (total 1.5 s over 5 attempts) and uses one temp name per pid. Refine to: pre-check read-only, ~1.0 s total window (D-05), unique temp name, injectable sleep.
- PITFALLS.md Pitfall 15 lists tab among escaped characters. KiCad's writer does not escape tab (Pitfall 8 above).
- ARCHITECTURE.md places backups at `<repo_root>/.import_backups/`; superseded by D-06 (app-data directory, outside the repo).
- PITFALLS.md suggests decoding vendor text as `utf-8-sig` with a cp1252 fallback; D-11 for this phase is strict UTF-8 with an error Issue. A cp1252 fallback for vendor packages is a Phase 3 decision.
- STACK.md says "pytest `>=9.1,<10`"; D-14 supersedes it with `pytest==9.1.1`.

**Deprecated/outdated:** none relevant. An unrelated, untrusted note appeared in the working tree during research (`reports/KiCad 10 vendor part import.md`, untracked, not authored here); it claims KiCad 10 writes symbol/footprint versions `20251024`/`20260206` and tab-indented files. Not relied on; it only reinforces that the tokenizer must not assume any token set.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | macOS/Linux backup paths (`~/Library/Application Support/KiCadExtLibManager/backups`, `$XDG_DATA_HOME/...`) are acceptable conventions | Pattern 4 | Low; only affects non-Windows users, and the owner is on Windows. Discretion item |
| A2 | On POSIX a read-only file in a writable directory can still be `os.replace`d and root bypasses `os.access`, so the explicit pre-check is needed there | Pitfall 6 | Low; Windows (primary) behaviour is verified. A Linux read-only test could behave differently as root |
| A3 | Tokenizing multi-MB Wurth libraries stays fast (earlier research measured 2.3 MB in 577 ms; here 523 KB total in 0.136 s) | Summary, D-03 | Medium-low; Wurth is not checked out so unmeasured. Fall back to a depth-limited scan fast path in Phase 2 if needed |
| A4 | The upstream WurthElektronik repo may contain its own `*-lib-table` files; the glob-based test handles either case | Corpus | Low |
| A5 | KiCad's `Quotes()` source summary (4 escapes, tab raw) is accurate; fetched via a summarising tool | Pitfall 8 | Low-medium; wrong escaping would only matter once Phase 4 writes user-typed text. Re-check against a KiCad-saved fixture then |
| A6 | `SUS` verdicts for pytest, pytest-qt, PySide6 are tooling artefacts (no download data; PySide6 10 days old) rather than real risk | Package Legitimacy Audit | Low; mitigated by the single human-verify checkpoint and the verified fresh install |
| A7 | Tie / no-EOL files default to LF (`"\n"`) for inserted text | Pattern 2 | Low; design choice within D-09/D-10, confirm if the owner prefers CRLF on Windows |
| A8 | `os.replace` is atomic on NTFS same-volume (MoveFileEx REPLACE_EXISTING) | Pattern 3 | Low; from prior STACK.md research and Python docs, not re-proven here (power-loss semantics cannot be tested) |

## Open Questions

1. **Add `"tests"` to `SKIP_DIRS` in `library_scanner.py`?**
   - What we know: fixtures with real `.kicad_sym` extensions would appear as a library source named `tests` in the GUI scan (`library_scanner.py:13` skips only `env, venv, .venv, .git, .claude, __pycache__`).
   - What's unclear: whether the owner accepts this one-line touch to an existing module in a phase that says existing modules are not rewired.
   - Recommendation: do it (one constant plus one regression test); fall back to non-library fixture suffixes only if the owner objects.

2. **Should the frozen fixtures include EOL variants as committed files or be generated into `tmp_path` per test?**
   - What we know: `-text` makes committed files safe; generated variants avoid any git/editor normalisation risk entirely.
   - Recommendation: commit one minimal file per distinct trait (CRLF, LF, BOM, mixed, escapes/parens) plus self-check tests, and ALSO generate the full EOL x BOM matrix in `tmp_path` for the edit tests.

3. **Tie-break and lone-CR policy for EOL sniffing (A7).**
   - Recommendation: majority wins, ties and EOL-less files -> LF, any bare CR counts as "mixed" (warn, do not normalise).

4. **Committing `downloaded_examples/ul_CSD85301Q2.zip` (D-04, costly to reverse).**
   - What we know: it is TI/Ultra Librarian content, 45,550 bytes, currently untracked; git stores it as binary (`i/-text`), size preserved. STATE.md flags redistribution terms as a Phase 7 concern for the *public* `Custom/` repo; D-04 targets the private parent repo.
   - Recommendation: honour D-04 as locked; `git add downloaded_examples/ul_CSD85301Q2.zip` explicitly (not the directory); surface the irreversibility once more in the plan task.

5. **Should failed `decode_source` also be representable as a `SourceText` with `issues`?**
   - Recommendation: no; return `Issue` alone so callers cannot accidentally edit an undecodable file (D-11).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| CPython (python.org) | Everything | ✓ | 3.14.4 (`env/`, base at `...\pythoncore-3.14-64`) | — |
| pip | FOUND-01 | ✓ | 26.0.1 (26.2.1 available; not required) | — |
| PySide6 | D-15 widget test | ✓ | 6.12.0 in `env/` | — |
| pytest | Runner | ✓ | 9.1.1 in `env/` | — |
| pytest-qt | `qtbot` | ✗ in `env/` (✓ in scratch venv) | 4.5.0 on PyPI | `pip install -r requirements-dev.txt` |
| PyPI network access | Install | ✓ | `pip index versions` worked | — |
| git | `.gitattributes`/`check-ignore` verification | ✓ | 2.49.0.windows.1 | — |
| `Custom/` submodule | Live corpus | ✓ | 10 `.kicad_sym` + 14 `.kicad_mod`, HEAD `6b1fcb4` | Frozen fixtures |
| `WurthElektronik/KiCad-Library` | Stress corpus (`wurth` marker) | ✗ | directory exists, empty | Skip with reason (D-03) |
| KiCad user config | `local_kicad` opt-in tests | ✓ | `%APPDATA%\kicad\7.0`, `8.0`, `9.0`: `sym-lib-table`, `fp-lib-table` each (+ 9.0 `design-block-lib-table`) | Skip when absent |
| KiCad install / `kicad-cli` | Not needed in Phase 1 | ✓ dir `C:\Program Files\KiCad\9.0` | — | — |
| Display | Not needed (offscreen) | — | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `pytest-qt` (install step), Wurth submodule (skip marker).

## Validation Architecture

Nyquist validation is enabled (`workflow.nyquist_validation: true` in `.planning/config.json`).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-qt 4.5.0 (PySide6 6.12.0, offscreen) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`), Wave 0 creates it |
| Quick run command | `.\env\Scripts\python.exe -m pytest tests\test_sexpr.py tests\test_fsutil.py tests\test_kicad_files.py tests\test_models.py -x -q` |
| Full suite command | `.\env\Scripts\python.exe -m pytest` (equivalently bare `pytest` inside the activated venv) |
| Skip opt-in sources | `.\env\Scripts\python.exe -m pytest -m "not wurth and not local_kicad"` |
| Fresh-venv gate (phase gate, manual) | `py -m venv $env:TEMP\f1 ; & $env:TEMP\f1\Scripts\python.exe -m pip install -r requirements-dev.txt ; & $env:TEMP\f1\Scripts\pytest.exe` (verified equivalent run: install exit 0, tests green) |

Expected full-suite runtime is a few seconds (corpus of 24 real files + zip + 7 local tables parsed in 0.14 s in prototype).

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUND-01 | `requirements.txt` is exactly `PySide6==6.12.0`; `requirements-dev.txt` is `-r requirements.txt`, `pytest==9.1.1`, `pytest-qt==4.5.0`, every entry `==`-pinned | unit | `pytest tests/test_manifests.py -x` | ❌ Wave 0 |
| FOUND-01 | Fresh venv install + `pytest` green (SC1) | manual phase-gate | fresh-venv command above | ❌ (documented, run once at phase gate) |
| FOUND-02 | Headless: platform is `offscreen`; D-15 widget tests pass (toggle select/deselect, per-source scope, group header, select/deselect all) | integration (Qt) | `pytest tests/test_library_table_widget.py -x` | ❌ Wave 0 |
| FOUND-02 | Bare `pytest` imports the package (pythonpath), markers strict | smoke | `pytest --collect-only -q` | ❌ Wave 0 |
| FOUND-03 | Tokens + gaps tile the source exactly; bytes -> `SourceText` -> bytes identity for live `Custom/`, frozen fixtures, UL zip members, synthetic tables | unit/corpus | `pytest tests/test_roundtrip_corpus.py -x` | ❌ Wave 0 |
| FOUND-03 | Opt-in real KiCad tables (7.0/8.0/9.0) and Wurth corpus round-trip | corpus (opt-in) | `pytest -m "local_kicad or wurth" -x` | ❌ Wave 0 |
| FOUND-03 | Tokenizer edge cases: parens/escapes in strings, bare atoms, unterminated string, unbalanced, 100k nesting, BOM, trailing/no trailing newline | unit | `pytest tests/test_sexpr.py -x` | ❌ Wave 0 |
| FOUND-04 | One-property edit changes only its span (CRLF, LF, mixed, BOM files; real + fixtures); overlapping edits rejected; inserted text converted to dominant EOL; mixed file yields a warning Issue and is not normalised | unit | `pytest tests/test_edits.py tests/test_sexpr.py -x` | ❌ Wave 0 |
| FOUND-04 | Locators return correct spans: symbols, property name/value, footprint name (string and bare atom), models (0/1/2), lib entries incl. `(disabled)`, reordered fields, escaped `"`/`\` | unit | `pytest tests/test_kicad_files.py -x` | ❌ Wave 0 |
| FOUND-05 | Success replaces in one step and leaves no temp; read-only -> `fs.read_only` Issue instantly, original intact; held-open (Windows) -> `fs.locked` after retry, original intact, no temp; lock released mid-retry succeeds; fsync/OSError injection -> `fs.write_failed`, original intact; missing dir -> Issue; invalid UTF-8 -> `fs.bad_encoding` and never edited | unit | `pytest tests/test_fsutil.py -x` | ❌ Wave 0 |
| FOUND-05 | `backup_file` names match `table_generator.backup_existing` (`<name>_backup_1`, `_2`), custom `backup_dir` created, no write to real app-data | unit | `pytest tests/test_fsutil.py -k backup -x` | ❌ Wave 0 |
| (D-07) | `Severity` values equal `LogPanel` level keys; `Issue` frozen | unit | `pytest tests/test_models.py -x` | ❌ Wave 0 |
| (layering) | Importing `sexpr`, `kicad_files`, `fsutil`, `models` does not import PySide6 (subprocess with `cwd=repo`) | unit | `pytest tests/test_layering.py -x` | ❌ Wave 0 |
| (Pitfall 2) | `"tests"` in `library_scanner.SKIP_DIRS` (if Open Question 1 is accepted) | unit | `pytest tests/test_layering.py -k skip_dirs` | ❌ Wave 0 |

Locked-file tests: gate the held-open case with `@pytest.mark.skipif(sys.platform != "win32", reason="...")` (that is the platform where an open handle blocks `os.replace`); simulate the same path on other platforms with `monkeypatch` raising `PermissionError` from `os.replace`. Always `os.chmod(path, stat.S_IREAD | stat.S_IWRITE)` in a `finally` so pytest can clean `tmp_path`. Inject `sleep=lambda s: None` or tiny `retry_delays` so unit tests do not wait.

### Sampling Rate
- **Per task commit:** the quick run command for the touched module (under 5 s).
- **Per wave merge:** `.\env\Scripts\python.exe -m pytest` (full suite, a few seconds).
- **Phase gate:** full suite green (including `-m "local_kicad or wurth"` on the owner's machine, where Wurth will report SKIPPED with reason) and the fresh-venv install run, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `.gitattributes` (commit `.gitattributes` BEFORE any fixture is staged)
- [ ] `tests/conftest.py` (forced offscreen; repo-root and corpus-discovery fixtures)
- [ ] `tests/test_manifests.py`, `tests/test_library_table_widget.py`, `tests/test_models.py`, `tests/test_layering.py`
- [ ] `tests/test_sexpr.py`, `tests/test_roundtrip_corpus.py`, `tests/test_edits.py`, `tests/test_kicad_files.py`, `tests/test_fsutil.py`
- [ ] `tests/fixtures/sexpr/*` (lf, crlf, bom, mixed, parens-in-strings/escaped quotes, bare atoms, no-trailing-newline, legacy `(module NAME`, empty-string values) created bytes-exact
- [ ] `tests/fixtures/tables/*.sym-lib-table`, `*.fp-lib-table` (escaped `"` and `\`, reordered fields, odd whitespace between forms, unknown children, `(disabled)`/`(hidden)` flags, missing optional fields, `(version 7)`)
- [ ] Track `downloaded_examples/ul_CSD85301Q2.zip` (explicit path)
- [ ] `pytest-qt` install: `.\env\Scripts\python.exe -m pip install -r requirements-dev.txt`
- [ ] (if accepted) `"tests"` added to `library_scanner.SKIP_DIRS`

## Security Domain

`security_enforcement` is enabled (ASVS level 1, block on high). Phase 1 has no network, auth, or user-account surface; the relevant surface is parsing untrusted vendor files and writing local files.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | Local single-user desktop tool |
| V5 Input Validation | yes | Strict UTF-8 decode; tokenizer rejects unterminated strings/unbalanced parens with line/col; iterative parse (no recursion DoS); raise at first bad char (no quadratic behaviour); zip members read in memory with a size check |
| V6 Cryptography | no | — (hashing for conflicts is Phase 4) |
| V12 Files and Resources | yes | Temp file in the target directory with exclusive create; cleanup in `finally`; atomic `os.replace`; never extract or execute `downloaded_examples/` content; tests use `tmp_path` and never write to the real repo, app-data, or `%APPDATA%\kicad` |
| V14 Configuration / dependencies | yes | Exact version pins (`==`) for all three direct dependencies; legitimacy gate executed; no `postinstall` signals |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Hostile or corrupt S-expression (deep nesting, huge strings, unterminated string) | Denial of Service | Iterative parser; first-bad-char raise; no recursive `repr`/`eq` on `Node` (`slots=True, eq=False`); 5000-deep parse took 0.008 s in prototype; add a 100k-deep test |
| Zip member from untrusted vendor zip | Tampering / DoS | Phase 1 test reads only `.kicad_sym`/`.kicad_mod` members of the one committed zip, in memory, after a `file_size` cap check; no `extract`/`extractall`; full zip safety is Phase 3 (INTK-06) |
| Partial/truncated write on lock or crash | Tampering / Availability | Temp + fsync + `os.replace`; original untouched on failure; Issue returned |
| Silent data change via EOL/BOM/encoding normalisation | Tampering | `newline=""` semantics via bytes, BOM carried, strict UTF-8, mixed EOL warned not normalised |
| Real user config leaking into the repo | Information Disclosure | Local-table tests are read-only and opt-in; assertions must not print table contents; never copy tables into `tests/fixtures` |
| Supply-chain (typosquat) | Spoofing | Pinned exact versions; names confirmed on PyPI with pytest-dev GitHub repos; single human-verify checkpoint |

## Sources

### Primary (HIGH confidence)
- This machine, this session: fresh-venv install of the exact pins (`pip list`: pytest 9.1.1, pytest-qt 4.5.0, PySide6 6.12.0, pluggy 1.7.0, typing_extensions 4.16.0 ...) and a 5-test offscreen run; `pip index versions` for pytest/pytest-qt/PySide6; PyPI JSON for `requires_python`, `requires_dist`, upload times.
- Read in full this session: `kicad_lib_manager/models.py`, `kicad_lib_manager/widgets/library_table.py`; targeted Reads: `library_scanner.py:10-15`, `table_generator.py:150-167`, `settings.py:10-23`, `.gitignore:1-15`; `widgets/log_panel.py` (COLORS) via shell.
- Prototype runs (scratchpad, not committed): tokenizer over 24 `Custom/` files + 2 UL zip members + 7 `%APPDATA%\kicad` tables; targeted-edit diff; error cases; deep nesting; atomic-write matrix on Windows 11 (success, read-only, held-open, released mid-retry, fsync failure, missing dir); scratch git repo with `core.autocrlf=true` for `.gitattributes`/`-text` and binary-zip behaviour; `git check-ignore -v` for fixture names.
- `.planning/research/{SUMMARY,STACK,ARCHITECTURE,PITFALLS}.md`, `.planning/codebase/TESTING.md`, `.planning/phases/01-foundation/01-CONTEXT.md`.
- KiCad source (fetched, summarised): [richio.cpp](https://gitlab.com/kicad/code/kicad/-/raw/master/common/richio.cpp) `OUTPUTFORMATTER::Quotes`; [dsnlexer.cpp](https://gitlab.com/kicad/code/kicad/-/raw/master/common/dsnlexer.cpp) `NextTok` string and separator handling.

### Secondary (MEDIUM confidence)
- [pytest-qt introduction](https://pytest-qt.readthedocs.io/en/latest/intro.html): `qt_api` ini option / `PYTEST_QT_API`, PySide6 supported.
- [pytest reference](https://docs.pytest.org/en/stable/reference/reference.html): confirms native TOML support added in pytest 9.0 (page truncated before the ini-option details; `ini_options` behaviour itself verified empirically).

### Tertiary (LOW confidence)
- The untracked `reports/KiCad 10 vendor part import.md` (not authored in this session, unverified) was noted but not relied upon.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. Exact pins verified on PyPI and by a clean install; D-14 answered (`pytest==9.1.1`).
- Architecture: HIGH. Prototype validated against all available real files; API shapes are recommendations within the stated discretion areas.
- Pitfalls: HIGH for the five found by direct experiment (ignored fixture names, scanner pollution, `pythonpath`, BOM token, heredoc mangling); MEDIUM for KiCad escape semantics (source summarised by a fetch tool) and for POSIX behaviours (not testable here).

**Research date:** 2026-10-18
**Valid until:** 2026-11-17 (30 days; pinned toolchain, stable domain. Re-check `pip index versions` if planning slips and a pytest 9.1.2 / pytest-qt 4.5.1 appears.)
