# Phase 1: Foundation - Context

**Gathered:** 2026-10-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers the shared base that every later phase builds on. It ships no user-facing feature.

- Pinned dependency manifests (`requirements.txt`, `requirements-dev.txt`) and a `pyproject.toml` holding pytest config.
- A headless pytest harness (`tests/`, `conftest.py` with `QT_QPA_PLATFORM=offscreen`) that includes at least one real Qt widget test.
- `kicad_lib_manager/sexpr.py`: a lossless S-expression tokenizer and tree. Nodes carry `(start, end)` spans. Edits are applied as back-to-front splices, and files are never re-serialised.
- `kicad_lib_manager/fsutil.py`: atomic write, numbered backup, EOL and encoding sniffing.
- `kicad_lib_manager/kicad_files.py`, read side only: span-aware locators for symbols, properties, footprint name, model nodes and lib-table entries.
- `Severity` + `Issue` added to `kicad_lib_manager/models.py`.

Requirements: FOUND-01 to FOUND-05. Existing modules (`table_generator`, `library_scanner`, `main_window`) are not rewired in this phase; that is Phase 2.

</domain>

<decisions>
## Implementation Decisions

### Round-trip test corpus
- **D-01:** The round-trip identity test uses two sources:
  - **Live discovery:** at test time, glob every `.kicad_sym` / `.kicad_mod` under `Custom/` (and `WurthElektronik/` when present), so new parts are covered automatically.
  - **Frozen set:** a small committed fixture set under `tests/fixtures/`. It covers edge cases such as CRLF and LF variants, strings containing parens and escaped quotes, a BOM file and a mixed-EOL file. Core tests must pass even with an uninitialised submodule.
- **D-02:** Lib-table round-trips have two sources:
  - **Committed synthetic fixtures:** hand-written `sym-lib-table` / `fp-lib-table` files covering escaped `"` and `\`, reordered fields, odd whitespace, unknown children and missing optional fields.
  - **Opt-in local tables:** the real global tables in `%APPDATA%/kicad/*/` (7.0, 8.0 and 9.0 exist on the owner's machine) are round-tripped when present and skipped when absent. Real personal tables are never copied into the repo.
- **D-03:** WurthElektronik tests carry a marker (e.g. `wurth`) and skip with a clear reason when the submodule is empty. It is currently not checked out in this worktree. When it is present it doubles as the stress and performance corpus.
- **D-04:** Commit `downloaded_examples/ul_CSD85301Q2.zip` to the parent repo (`sylvanoMTL/kicad_libraries`, which is private), not to `Custom/`. The round-trip test reads the `.kicad_sym` (format `20211014`) and `.kicad_mod` members straight from the zip into memory, without extracting into the repo. Phases 3 and 4 reuse it. — **Reversibility:** costly — removing a vendor file from git history once pushed requires a history rewrite of the parent repo.

### Write failure and backups
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

### Line endings, encoding and .gitattributes
- **D-08:** Add a parent-repo `.gitattributes` containing only `tests/fixtures/** -text`, so CRLF and LF fixtures stay byte-exact under `core.autocrlf=true`. There is no repo-wide EOL policy and no `.gitattributes` in `Custom/`. The S-expression layer preserves whatever EOL each file has.
- **D-09:** Inserted text, such as a new property line, is converted to the file's dominant EOL (sniffed CRLF vs LF).
- **D-10:** A file with mixed CRLF and LF endings round-trips untouched. Inserts use the majority EOL, and a warning Issue names the file. Never normalise silently.
- **D-11:** Decode as strict UTF-8. A leading BOM, if present, is preserved byte-for-byte. Invalid UTF-8 produces an error Issue, and that file is never edited. Read and write with `newline=""` (or equivalent bytes handling) so EOLs are not translated.

### Phase 1 module scope
- **D-12:** Phase 1 includes a minimal `kicad_files.py` read side: locate symbols (by name), properties (by name, value span), footprint name, `(model ...)` nodes and lib-table `(lib ...)` entries, each with spans. It provides the property locator that success criterion 3 needs. The write-side semantics (symbol insert/rename incl. `_u_s` sub-symbols and `extends`, footprint rename, model insert, version policy) stay in Phase 4. Phase 2 extends the read side as the scanner and table generator need it.
- **D-13:** `pyproject.toml` holds tool config only: `[tool.pytest.ini_options]` with testpaths, `qt_api = "pyside6"` and registered markers (e.g. `wurth`, `local_kicad`). There is no `[project]` metadata and no installable package. The app still runs as `python kicad_lib_manager.py`.
- **D-14:** Pin every dependency exactly. `requirements.txt`: `PySide6==6.12.0`. `requirements-dev.txt`: `-r requirements.txt`, `pytest==9.1.x` (the exact patch the researcher verified) and `pytest-qt==4.5.0`. Upgrades are deliberate.
- **D-15:** The offscreen Qt test is a `LibraryTableWidget` symbol-to-footprint sync test. Populate the widget from a hand-built `ScanResult` with two sources, then check two things: toggling a symbol selects and deselects its linked footprints, and the sync is scoped per source (changing Custom symbols doesn't touch WurthElektronik footprints). This pins down current behaviour before Phase 2 changes rescans and nickname handling.

### Resolved during planning (2026-10-18)
- **D-16:** Add `"tests"` to `SKIP_DIRS` in `kicad_lib_manager/library_scanner.py`, with a regression test. This lets fixtures under `tests/fixtures/` keep real `.kicad_sym` / `.kicad_mod` names without showing up as a `tests` library source in the GUI scan. It is the one exception to "existing modules are not touched in Phase 1" (RESEARCH.md Open Question 1).
- **D-17:** The owner approved the three D-14 pins (`pytest==9.1.1`, `pytest-qt==4.5.0`, `PySide6==6.12.0`), which the package-legitimacy check had flagged SUS only for missing download data or recent release. That approval is the human verification, so the install step runs without a `checkpoint:human-verify`.

### Claude's Discretion
- Exact retry count and backoff inside the ~1 s window (D-05).
- App-data backup path naming and cross-platform equivalents (D-06).
- `Issue.code` naming scheme (e.g. dotted `fs.locked`, `sexpr.unbalanced`).
- Tokenizer internals: regex lexer, iterative tree build, the `SexprError(line, col)` shape, the `quote()` escape set (`"` and `\` at minimum), and the edit/splice API shape (`Edit(start, end, text)`, `apply_edits`). Follow the shape sketched in `.planning/research/ARCHITECTURE.md`.
- Fixture file selection and naming within `tests/fixtures/`.
- Whether the round-trip test checks the zip members of the UL sample individually or as one parametrised case.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` §Phase 1: goal and the four success criteria
- `.planning/REQUIREMENTS.md`: FOUND-01 to FOUND-05
- `.planning/PROJECT.md`: constraints (stdlib only, atomic or backed-up writes, Windows CPython)

### Design research
- `.planning/research/SUMMARY.md`: reconciled phase plan; Phase 1 deliverables; pitfalls 2, 9, 10
- `.planning/research/STACK.md`: tokenizer approach, kiutils/sexpdata rejection evidence, `os.replace` probe results on Windows 11, pytest-qt 4.5.0 + PySide6 6.12.0 offscreen verification, exact versions
- `.planning/research/ARCHITECTURE.md`: `sexpr.py` / `kicad_files.py` / `fsutil.py` responsibilities, API shape sketch, dependency direction (nothing below presentation imports Qt), `tests/` layout
- `.planning/research/PITFALLS.md`: S-expression regex pitfalls, line-ending churn, atomic-write and Windows-lock pitfalls

### Codebase maps
- `.planning/codebase/TESTING.md`: recommended test layout and run commands (`.\env\Scripts\python.exe -m pytest`)
- `.planning/codebase/CONVENTIONS.md`: naming, error-handling style, module dependency rules
- `.planning/codebase/CONCERNS.md`: background for why these primitives are needed (Phase 2 consumes them)

### Sample data
- `downloaded_examples/ul_CSD85301Q2.zip`: real Ultra Librarian package (`KiCADv6/*.kicad_sym` at `20211014`, `KiCADv6/footprints.pretty/DQK0006B.kicad_mod`, `DLV0006A.stp` at zip root)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kicad_lib_manager/table_generator.py` `backup_existing()` (line ~150): the existing numbered `<name>_backup_<N>` scheme. `fsutil.backup_file` should produce the same naming so the Restore dialog keeps working when Phase 2 switches over.
- `kicad_lib_manager/models.py`: dataclass home for the new `Severity` / `Issue`. It has no internal imports, so keep it that way.
- `kicad_lib_manager/widgets/library_table.py` `LibraryTableWidget.populate(scan_result)` and `_on_sym_item_changed` / `_sync_footprint_selection(source)`: the targets of the D-15 Qt test. They are driven by `QTreeWidgetItem` check-state changes and mutate `lib.selected`.

### Established Patterns
- Services are Qt-free and return values rather than raising. The new modules return `Issue` lists (D-07).
- Use `pathlib.Path` everywhere, `.as_posix()` for KiCad-facing paths, and snake_case with `_private` helpers and UPPER_SNAKE constants.
- Docstrings are one-line summaries, with no type info in docstrings.
- Relative imports inside the package (`from .models import ...`).

### Integration Points
- The new top-level package modules `sexpr.py`, `kicad_files.py` and `fsutil.py` sit beside `models.py`. Nothing in Phase 1 imports them from existing modules yet.
- The repo root gets `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `.gitattributes`, `tests/` and the tracked `downloaded_examples/`.
- The corpus is small: `Custom/` has 10 `.kicad_sym` and 14 `.kicad_mod` files, and the largest symbol file is about 49 KB. The repo has no lib tables (they're generated and gitignored).
- Both the parent repo and `Custom/` have `core.autocrlf=true` and no `.gitattributes`, so working-tree files are CRLF on Windows.

</code_context>

<specifics>
## Specific Ideas

- Personal KiCad tables must never be committed. The local-table tests are opt-in reads only.
- Git status inside `Custom/` must stay clean of backup files (the reason for D-06).

</specifics>

<deferred>
## Deferred Ideas

- A repo-wide EOL policy (`*.kicad_sym *.kicad_mod text eol=lf`) in the parent and `Custom/`. It was offered and declined for Phase 1 because it needs a renormalisation commit. Revisit after the importer ships, if ever.

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-10-18*
