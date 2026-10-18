# Stack Research

**Domain:** Vendor-part importer (Ultra Librarian / SnapEDA / SamacSys-CSE zips + loose files) inside an existing PySide6 KiCad library manager
**Researched:** 2026-10-18
**Confidence:** HIGH for the recommendations (each was checked against PyPI metadata and/or a hands-on probe against the real sample zip, the repo's own `Custom/` libraries and the KiCad 9.0.9 install on this machine). MEDIUM for vendor-layout claims about SnapEDA and SamacSys (only the Ultra Librarian zip exists locally).

## Bottom line

**Add zero runtime dependencies.** The app stays "PySide6 only". The importer needs:

1. a small in-repo **lossless S-expression tokenizer with span-based edits** (about 150 lines, stdlib `re`),
2. stdlib **`zipfile`** used in read-members-selectively mode (never `extractall`),
3. stdlib **`subprocess`** driving the **`git` CLI**,
4. a 20-line **`atomic_write`** helper over **`os.replace`** with retry,
5. optionally, the **`kicad-cli`** that already ships with the user's KiCad, as a normaliser and validator.

Dev-only additions: `pytest` (already in the venv) and `pytest-qt`.

The existing `env/` venv has PySide6 6.12.0 and pytest 9.1.1; nothing else is installed (verified with `pip list`).

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| Python (stdlib only) | 3.10+ floor (venv is 3.14.4) | Everything in the importer | Matches the existing constraint "stdlib only unless clearly justified". Do not use 3.12+/3.14-only APIs (`Path.walk`, `Path.copy`, `tarfile` filters) so the 3.10 floor stays honest. | HIGH |
| PySide6 | 6.12.0, pinned `==` | GUI, QThread workers | Already in use. PySide6 6.12.0 on Python 3.14.4 verified working with pytest-qt 4.5.0 (see Testing). | HIGH |
| In-repo `sexpr.py`: lossless tokenizer + span editor | n/a (about 150 lines, `re` only) | Parse, query and surgically edit `.kicad_sym`, `.kicad_mod`, `sym-lib-table`, `fp-lib-table` | **The only option that leaves untouched bytes untouched.** Every library option tested rewrites or drops content (see "Parser evidence" below). The same module also fixes the regex table-merge bug in the hardening scope. | HIGH |
| `zipfile` (stdlib) | stdlib | Read vendor zips | Reads members straight from the archive. Selective reads plus our own output names sidestep zip-slip. | HIGH |
| `subprocess` + `git` CLI | git 2.49.0 here (any 2.30+ is fine) | Commit in `Custom/`, bump parent submodule ref | The user's real git config (autocrlf, hooks, gpg, credential helpers, worktree/submodule layout) applies for free. No new dependency. | HIGH |
| `os.replace` + same-directory temp file | stdlib | Atomic writes for libraries, tables, `kicad_common.json` | On Windows `os.replace` maps to `MoveFileExW(REPLACE_EXISTING)`, which is atomic on NTFS for same-volume moves. The temp file must be in the same directory. | HIGH |

### Supporting Tools (optional, no pip install)

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `kicad-cli sym upgrade --force -o <out> <in.kicad_sym>` | KiCad 9.0.9 here | (a) **Validator**: exit 2 and "Unable to load library" on unparseable input, exit 0 otherwise. (b) **Normaliser**: rewrites old-format symbols to the current format (drops `(id N)`, adds `exclude_from_sim`, `(hide yes)` and so on). | After the in-memory merge, run it on a *temp copy* of the merged library as a "will KiCad load this?" gate. Treat as best-effort: skip silently if `kicad-cli` is not found. |
| `kicad-cli fp upgrade --force <dir.pretty>` | same | Same validator/normaliser for footprints | **Only on a temporary staging `.pretty` containing just the incoming footprint.** It rewrites every footprint in the directory in place, so never point it at the real library. It assigns fresh random UUIDs, so output is not byte-reproducible. |

`kicad-cli` locations: Windows `<KiCad root>/<ver>/bin/kicad-cli.exe` (the app already knows the install root through `find_kicad_footprint_dir`), macOS `KiCad.app/Contents/MacOS/kicad-cli`, Linux on `PATH`.

### Development Tools

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| pytest | `>=9.1,<10` (9.1.1 installed) | Test runner | Config in a new `pyproject.toml` under `[tool.pytest.ini_options]`: `testpaths = ["tests"]`, `qt_api = "pyside6"`. |
| pytest-qt | `==4.5.0` (released 2025-07-01, MIT, `requires_python>=3.9`) | `qtbot` for `QThread` and signal tests | **Verified here**: PySide6 6.12.0 + Python 3.14.4 + `QT_QPA_PLATFORM=offscreen`; a `QThread` worker plus `qtbot.waitSignal` and a widget test passed. Only needed for the worker/dialog tests, not for importer logic. |
| `QT_QPA_PLATFORM=offscreen` | n/a | Headless Qt | Set in `tests/conftest.py` via `os.environ.setdefault` *before* any PySide6 import. |

## Parser decision (question 1): hand-written lossless tokenizer

### Evidence (probed 2026-10-18; kiutils 1.4.8, sexpdata 1.0.2)

I round-tripped real files through each candidate and compared token streams.

| Candidate | Version / last release | Result | Verdict |
|-----------|-----------------------|--------|---------|
| **kiutils** | 1.4.8, 2024-02-02, no release since | Parse-then-save **silently drops KiCad 8/9 content**. KiCad 9 `Device.kicad_sym`: 17,179 tokens lost (all `(hide yes)` flags, 528 `exclude_from_sim`, 141 `pin_numbers`, the `generator_version` line). The user's `Connector_USB_GCT.kicad_sym` (v20241209): lost `(hide yes)` x69, `exclude_from_sim`, `generator_version`. A KiCad 9 footprint lost `generator_version` and per-property `layer`/`at` elements. It also reorders (`justify bottom left` becomes `left bottom`), re-indents everything (a v9 file diffed as 100% changed lines) and injects a `tedit` into footprints. Hiding pins and fields would be silently lost on a merge. | **Reject for writes.** Fine as a read-only inspector at best, but a second parser alongside the tokenizer buys nothing. |
| **sexpdata** | 1.0.2, 2024-01-09 | Parses fine but discards all whitespace and layout; `dumps` output is 35-40% shorter than the original, so every write would be a full-file rewrite in a different style. No source spans. | **Reject.** Not round-trip safe. |
| **kicad-skip** | 0.2.5, 2024-02-16 | Built on sexpdata, aimed at editing `.kicad_sch`/`.kicad_pcb` instances, not library files. Stale. | **Reject.** |
| **kicad-python (`kipy`, IPC API)** | 0.8.0, 2026-08-30; needs `protobuf`, `pynng`, `jsonschema` | Talks to a **running KiCad GUI over IPC**. KiCad's own docs say the IPC API covers the PCB editor; schematic/symbol/library editors are "planned". Cannot read or edit a file on disk. | **Reject.** Wrong tool: needs a live KiCad, no symbol support, three native dependencies. |
| **kicad-sym** | 0.5.3, 2026-08-14 | Third-party symbol-lib reader/writer. Not evaluated in depth (unknown fidelity for v9 flags). | Not recommended: same "re-serialise everything" risk as kiutils. Revisit only if the tokenizer proves painful. |
| **Hand-written tokenizer with spans** | in-repo | Prototype: regex `\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+`, building a tree of `(start, end)` byte spans. Parsed `Device.kicad_sym` (2.3 MB, 451k tokens) in 577 ms and the user's 30 KB libraries in 9 ms. Because edits are text splices into the original string, every byte outside the edit is preserved: whitespace, tabs, CRLF, ordering, unknown future tokens. | **Use.** |

### Required design of `sexpr.py`

- **Model:** parse to nodes carrying `start`/`end` offsets into the original `str`. Edits are `(start, end, replacement)` splices applied back-to-front. Never re-serialise the tree.
- **Operations needed** (this is the whole public API):
  - `top_level(name)` / find a child by head atom
  - `get_property(symbol, "Footprint")` and `set_property_value(...)`: replace only the *string token's span*
  - `rename_symbol(node, old, new)`: must also rename **sub-unit nodes** named `<Old>_<unit>_<style>` (for example `"CSD85301Q2_0_1"`, `"CSD85301Q2_1_1"`) and any `(extends "<Old>")` in siblings
  - `append_child(lib_node, text)` for symbol merge and for inserting a `(model ...)` into a footprint
  - `find_models(fp)` / `replace_model_path`
  - `escape_string()` (backslash and double quote)
- **Correctness details the sample already shows:**
  - The Ultra Librarian footprint has **no `(model ...)` node at all**, so "rewrite model path" really means *insert* a node. Insert `(model "${CUSTOM_3DMODEL_DIR}/<file>" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))` before the closing paren.
  - The UL symbol's Footprint property is a **bare name** (`"DQK0006B"`), not `Lib:Name`. Always overwrite it.
  - Both vendor files and the repo's libraries are **CRLF on disk** (`core.autocrlf=true` at system level, so the checkout converts). Detect the target file's EOL and normalise the inserted text to it. Read/write with `newline=""` so Python never translates.
  - The target libs are **mixed format generations**: `IC_Battery_Charger_TI.kicad_sym` is `(version 20211014)` with `(id N)` properties; `Connector_USB_GCT.kicad_sym` is `(version 20241209)`. Existing models in `Custom/` use `${CUSTOM_3DMODEL_DIR}/x.step`, `.STEP` and `.stp` extensions, and one uses `${KIPRJMOD}/Custom/3DModels/...` (a legacy path the importer will see when scanning, though it only writes new ones).
- **Mixing formats is tolerated by KiCad 9.0.9.** Probe: spliced a v20211014 symbol into a v20241209 library, a v9-format symbol into a v20211014 library, and v6 into v6, then ran `kicad-cli sym upgrade --force`: all three loaded, symbol count correct, `(id N)` stripped on resave. Rule: **splice verbatim by default, do not rewrite the target's header version.** Offer "normalise incoming file via `kicad-cli` first" when `kicad-cli` is available. Compatibility with KiCad 6/7 readers of a mixed file was not testable here (MEDIUM).
- **Tokenizer pitfalls:** strings may contain parens and escaped quotes (regex above handles it); KiCad 6-era files have bare atoms (`hide`, `italic`) and KiCad 9 has `(hide yes)`, so never assume atom-vs-list shape. Validate balanced parens after every edit and refuse to write on failure.
- **Reuse for hardening:** `sym-lib-table`/`fp-lib-table` use the same grammar, so the same module replaces the regex in `table_generator.py`; entries it cannot classify become warnings, not silent drops.

## Zip handling (question 2)

**Verdict: stdlib `zipfile`; read selected members, never `extractall`.**

Probe on Python 3.14.4: `ZipFile.extract` already neutralises `../x`, `/abs/x`, `C:/x`, `a/../../x`. Nothing escaped. That is a safety net, not the design, because it silently *relocates* names and leaves Windows-reserved names (`CON.txt` extracted without complaint) and size attacks unhandled.

Prescribed approach:

1. `infolist()`, skip `is_dir()`, normalise `name.replace("\\", "/")`, then classify by lower-cased suffix with `PurePosixPath`. **Reject** any member whose parts contain `..`, a drive letter, or an absolute root. Log a warning and ignore it rather than abort.
2. **Detect by content and suffix, not by folder name.** Ultra Librarian puts the KiCad files under `KiCADv6/` but the STEP at the *zip root* (`DLV0006A.stp`) with the vendor's own name that differs from the footprint's (`DQK0006B`). SamacSys/SnapEDA layouts reportedly vary again (STEP at top level or in a 3D folder; `footprints.pretty/`). Match `*.kicad_sym` (header `(kicad_symbol_lib (version N)`), `*.kicad_mod`, `*.step|*.stp|*.wrl` case-insensitively; ignore legacy `.lib/.dcm/.mod`, `.html`, `.txt`.
3. Read with `zf.open(info)` in chunks with a **hard byte cap** (suggest 100 MB per member, 300 MB per archive, and reject compress ratio above about 200:1). Do not trust `info.file_size` alone.
4. Write chosen members to a **fresh `tempfile.mkdtemp()` staging dir outside the repo** under *names we choose* (sanitised stem, allow-list `[A-Za-z0-9._+-]`, reject Windows reserved device names and trailing dots/spaces). Never use the archive's path as the output path.
5. Handle duplicates and case-insensitive collisions (two members `A.STEP` and `a.step`) as a preview-time conflict.
6. Clean the staging dir in a `finally`. Treat zip content as untrusted text: parse errors are warnings in the log panel, not crashes in a Qt slot.

Loose-files mode uses the same classifier over a directory listing (`os.scandir`, no recursion into symlinks).

## Git from Python (question 3)

**Verdict: `subprocess.run(["git", ...])`. No GitPython, no pygit2.**

| Option | Version (PyPI) | Assessment |
|--------|---------------|------------|
| **subprocess + git CLI** | git 2.49.0 present | **Use.** Matches the exact manual workflow in CLAUDE.md. Hooks, `core.autocrlf`, signing, worktree + submodule `gitdir` indirection all behave like the user's terminal. |
| GitPython | 3.2.1 (2026-10-14) | Still shells out to the `git` executable, so it adds a dependency without removing the dependency on git. Its README states the project is in **maintenance mode**. Reject. |
| pygit2 | 1.20.1 (2026-09-12), GPLv2 with linking exception, native libgit2 wheels, `requires_python>=3.11` | Violates the Python 3.10 floor, adds a compiled dependency, and libgit2 does not run hooks or honour all the user's config the same way. Reject. |

Conventions for the wrapper (`gitops.py`, Qt-free, run inside a `QThread` like `ScanWorker`):

- `shutil.which("git")` once; clear error if missing. Always a list argv, never `shell=True`.
- `subprocess.run(..., cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, timeout=60, env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"})`. On Windows add `creationflags=subprocess.CREATE_NO_WINDOW` so no console flashes if the app is launched windowless.
- Use `-C <dir>` or `cwd=` to target `Custom/`. Parse `git status --porcelain=v1 -z -- <paths>` (NUL-separated, quoting-safe), not human output.
- **Stage and commit only explicit paths**: `git add -- <paths>` then `git commit -m <msg> -- <paths>`. The user may have unrelated staged work; the importer's temp files (`.name.pid.tmp`) must never be swept in.
- Sequence: (1) preflight, (2) commit in `Custom/`, (3) in the parent `git add Custom` then `git commit -m "..." -- Custom`. Never `push`.
- **Preflight checks that matter here (found by probing this worktree):**
  - `git -C Custom status -sb` reports **`HEAD (no branch)`: the submodule is on a detached HEAD** (parent `git submodule status` shows `heads/main` for the recorded commit). A commit made on a detached HEAD is easy to orphan. Detect with `git -C Custom symbolic-ref -q HEAD` (non-zero exit means detached) and make the user confirm switching to `main`, or refuse to commit.
  - The target library files should be **clean before the write** (`status --porcelain` empty for those paths). That makes `git restore -- <paths>` a safe rollback if an install fails midway, and keeps the commit containing only the import.
  - This repo is a **git worktree** (`.git` is a file pointing into `Kicad_Libraries/.git/worktrees/...`; submodule git dir is under `.git/worktrees/.../modules/Custom`). Always go through git commands; never open `.git` paths directly.
- Test tip: creating a local submodule in a test repo needs `git -c protocol.file.allow=always submodule add` (git blocks the `file` transport by default since the 2022 CVE fix).

## Atomic writes on Windows (question 4)

**Verdict: write temp in the same directory, `flush` + `os.fsync`, then `os.replace` with a short retry; if it still fails, surface a clear error.**

```python
def atomic_write_text(path: Path, text: str, *, encoding="utf-8", retries=5) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")   # same dir => same volume
    try:
        with open(tmp, "w", encoding=encoding, newline="") as f:   # newline="" keeps CRLF/LF exactly
            f.write(text); f.flush(); os.fsync(f.fileno())
        for attempt in range(retries):
            try:
                os.replace(tmp, path); return
            except PermissionError:                        # WinError 5/32: held open or read-only
                if attempt == retries - 1: raise
                time.sleep(0.1 * 2 ** attempt)
    finally:
        tmp.unlink(missing_ok=True)
```

Verified behaviour on this machine (Python 3.14.4, Windows 11):

- `os.replace(tmp, target)` while another handle has `target` open with `open(..., "rb")` raises **`PermissionError: [WinError 5] Access is denied`**, and the original content is intact. Same error for a read-only target. Python's `open` does not request `FILE_SHARE_DELETE`, so any process holding the file without delete-sharing blocks the swap. That is exactly the failure the "locked or read-only tables" hardening item must catch.
- Do **not** use `tempfile.NamedTemporaryFile(delete=True)` for this on Windows (the file cannot be reopened/renamed while the handle is open); use a plain named temp file as above. Use `tempfile.mkdtemp` only for staging.
- Do **not** add `filelock` (4.2.2 exists, needs Python 3.11+): KiCad does not take locks on library files, only on project files, so a lock library protects against nothing real. Guard against double-clicks with an in-process "busy" flag, like the planned no-overlapping-scans fix.
- Multi-file install (symbol lib + footprint + STEP + possibly a new `.pretty`) is **not** atomic as a set. Pattern: stage and validate everything first, snapshot original bytes of existing targets in memory, apply with per-file atomic writes, and on any failure restore snapshots and delete files created in this run. The "clean before write" git preflight is the second safety net.
- KiCad caches libraries in memory. After install, tell the user to refresh or reopen the symbol/footprint editors (exact auto-reload behaviour per KiCad version not verified; MEDIUM).
- `kicad_common.json`: copy to a timestamped `.bak` first (already a hardening requirement), then `atomic_write_text`.

## Testing (question 5)

- **Importer logic (parser, merge, zip classifier, naming, path rewrite, gitops, atomic write): plain `pytest`, no Qt imported.** Keep the services Qt-free (the codebase already does this), so these run in milliseconds.
- **Worker/dialog behaviour: `pytest-qt==4.5.0`** with `QT_QPA_PLATFORM=offscreen`. Keep this layer thin (signals emitted, preview model populated, no write before confirm).
- **Fixtures:**
  - Commit a *trimmed* copy of the real sample as `tests/fixtures/ul_CSD85301Q2.zip` (or read from `downloaded_examples/` and skip if absent). Add SnapEDA, SamacSys/CSE and loose-file samples when the owner downloads them (PROJECT.md already lists that as a dependency). Check redistribution terms before committing vendor files to a public repo; the project is personal but `Custom/` is public on GitHub.
  - **Synthetic zips built in `tmp_path` with `zipfile.ZipFile(..., "w")`** for layout variants (nested depth, STEP at root vs. in a folder, no STEP, two footprints, backslash names) and hostile cases (`../evil`, absolute, drive letters, `CON.step`, duplicate and case-colliding names, oversized member, high ratio).
  - **Golden-text tests for edits:** assert that after `set_property_value`/`append_child` the output equals the input with exactly one span replaced (diff is only the intended lines). This directly guards the "preserve untouched content" requirement.
  - **Real git tests:** `git init` in `tmp_path`, local submodule with `protocol.file.allow=always`, commit with `-c user.name=... -c user.email=...`, assert a detached HEAD is detected, assert only listed paths are committed.
  - **Windows-only lock test:** hold the target open with `open(p, "rb")`, expect `PermissionError`, then expect the retry helper to raise a friendly error (`@pytest.mark.skipif(sys.platform != "win32")`).
  - **`kicad-cli` integration test:** `@pytest.mark.skipif(shutil.which("kicad-cli") is None and not <detected install>)`; merge into a copy of a `Custom` library and require exit 0 from `kicad-cli sym upgrade`.
- **Do not** snapshot-compare against files regenerated by KiCad (random UUIDs from `fp upgrade`). Assert structure and exact spliced spans instead.

## Installation

```bash
# requirements.txt  (new; the dependency manifest PROJECT.md asks for)
PySide6==6.12.0

# requirements-dev.txt
-r requirements.txt
pytest>=9.1,<10
pytest-qt==4.5.0
```

```powershell
.\env\Scripts\python.exe -m pip install -r requirements-dev.txt
.\env\Scripts\python.exe -m pytest
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| In-repo lossless tokenizer | kiutils 1.4.8 | Only for a throwaway read-only inspection script. Never for anything that writes into curated libraries until it stops dropping KiCad 8/9 tokens (no release since Feb 2024). |
| In-repo lossless tokenizer | `kicad-cli sym export`/`upgrade` as the editor | If you only needed format conversion. It cannot merge into an existing library, rename, or set fields. Fine as validator, wrong as editor. |
| subprocess `git` | pygit2 1.20.1 | Only for a daemon needing high-volume repo reads without a git install; not this app. |
| `os.replace` retry helper | `filelock` 4.2.2 | Only if KiCad (or a sync tool) were proven to lock library files. It does not. |
| Selective zip reads | `shutil.unpack_archive` / `extractall` | Never for untrusted vendor zips. |
| pytest-qt | Hand-rolled `QEventLoop` in tests | If pytest-qt ever lags a PySide6 release; today 4.5.0 works with 6.12.0. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| kiutils (for writes) | Measured: silently drops `(hide yes)`, `exclude_from_sim`, `pin_numbers`, `generator_version`, property layers on KiCad 9 files; reorders `justify`; re-indents whole files; unmaintained since 2024-02 | In-repo span-based tokenizer |
| sexpdata / kicad-skip | Lose all formatting; not library-oriented | Same |
| `kicad-python` / `kipy` (IPC) | Requires a running KiCad PCB editor; no symbol/footprint-library file API; protobuf + pynng deps | Direct file editing |
| Regex-on-first-match for symbol merge or property edits | The failure mode the project exists to remove; breaks on nested units, multiple `property "Footprint"`, strings containing parens | Tokenizer queries |
| `ZipFile.extractall` / extracting into the repo | Unbounded size, Windows-reserved names, relocation hides problems, leaves junk in a git repo | Selective member reads into a `mkdtemp` staging dir with sanitised names |
| GitPython (maintenance mode, still needs git) / pygit2 (3.11+, native, no hooks) | Extra dependency for no gain | `subprocess` + `git` |
| `NamedTemporaryFile(delete=True)` for atomic writes on Windows | Cannot be renamed over a target while open | Plain `.name.pid.tmp` in the target dir + `os.replace` |
| `kicad-cli fp upgrade` on the real `.pretty` | Rewrites every footprint, new UUIDs, huge diff in a curated lib | Staging dir with only the incoming footprint |
| `git add -A` / `git commit -a` | Would sweep in unrelated or temp files | Explicit pathspecs |
| Committing while the submodule is on a detached HEAD without asking | Commit becomes unreachable once the user switches branches | Detect and require a branch |

## Stack Patterns by Variant

**If `kicad-cli` is found (KiCad install detected):**
- Normalise the incoming symbol/footprint to the current format in a temp dir, then splice, then validate the merged temp copy with `sym upgrade`.
- Because it yields consistent modern output and a strong "KiCad can load this" gate.

**If `kicad-cli` is not found:**
- Splice verbatim, rely on the tokenizer's balanced-paren check and header sanity checks, show a "not validated by KiCad" note in the preview.
- Because KiCad 9 loaded all mixed-generation merges in the probe.

**If a package has no STEP (or the STEP name differs from the footprint, as in the sample: `DLV0006A.stp` vs `DQK0006B`):**
- No STEP: insert no `(model)` node and log a warning (matches the PROJECT.md decision).
- Mismatched name: pair by "single STEP in archive", default to keeping the vendor filename and extension, and offer a rename in the preview.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| PySide6 6.12.0 | Python 3.14.4 | Installed and running in `env/`. |
| pytest-qt 4.5.0 | PySide6 6.12.0, Python 3.14.4, pytest 9.x | Probed with a `QThread` + `waitSignal` + widget test under offscreen Qt. Set `qt_api = "pyside6"` so it does not try other bindings. |
| pytest 9.1.1 | Python 3.10+ | Already installed in `env/`. |
| KiCad 9.0.9 `kicad-cli` | files at `(version 20211014)` through `20241209` | Loads all generations, including mixed-version merges; drops legacy `(id N)` on resave. KiCad 10 behaviour not tested here. |
| `os.replace` | NTFS, same volume | Atomic; fails with `PermissionError` (WinError 5) on a target held open without delete-sharing or marked read-only. |

## Discrepancy with PROJECT.md to resolve before planning

PROJECT.md says the sample "contains ... and no STEP model". The actual `downloaded_examples/ul_CSD85301Q2.zip` **does contain a STEP file, `DLV0006A.stp` (192 KB), at the zip root**, outside `KiCADv6/`. The footprint `DQK0006B.kicad_mod` has no `(model)` node, so it is not linked to it. The Ultra Librarian fixture is therefore the "STEP outside the KiCad folder, differently named, footprint has no model" case, and the "no STEP" case still needs a separate fixture. This sharpens the 3D-model requirement: the importer must be able to *add* a `(model)` node, not just rewrite an existing path.

## Sources

- PyPI JSON metadata, queried 2026-10-18: kiutils 1.4.8 (2024-02-02), sexpdata 1.0.2 (2024-01-09), kicad-skip 0.2.5 (2024-02-16), kicad-python 0.8.0 (2026-08-30), kicad-sym 0.5.3 (2026-08-14), GitPython 3.2.1 (2026-10-14), pygit2 1.20.1 (2026-09-12), pytest-qt 4.5.0 (2025-07-01), filelock 4.2.2 (2026-10-18), pytest 9.1.1, PySide6 6.12.0 (HIGH).
- Hands-on probes in this environment (HIGH): round-trip token diffs of kiutils/sexpdata on the sample zip, `Custom/` libraries and KiCad 9 `Device.kicad_sym`; tokenizer prototype timings; `kicad-cli 9.0.9 sym upgrade` / `fp upgrade` validation and mixed-format merge tests; `zipfile.extract` traversal behaviour on Python 3.14.4; `os.replace` over open and read-only files on Windows 11; pytest-qt 4.5.0 with PySide6 6.12.0 offscreen; `git` 2.49.0 worktree/submodule state (detached `Custom`).
- [KiCad IPC API: For Add-on Developers](https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/): IPC needs a running GUI, PCB editor only, schematic/library editors planned (MEDIUM-HIGH; one secondary source suggests schematic IPC lands in KiCad 11, not verified).
- [KiCad 9.0 CLI reference](https://docs.kicad.org/9.0/en/cli/cli.html) and local `kicad-cli sym upgrade --help` / `fp upgrade --help` (HIGH).
- [GitPython README](https://github.com/gitpython-developers/GitPython): maintenance mode, requires the `git` executable (HIGH).
- SnapEDA/SamacSys layout: [SnapMagic KiCad v6+ import guide](https://support.snapmagic.com/en/articles/5995733-how-to-import-into-kicad-v6-and-later), [SamacSys KiCad note](https://www.samacsys.com/?p=318527), [parts2kicad thread](https://forum.kicad.info/t/parts2kicad-script-for-importing-from-samacsys-mouser-farnell/66224), [UT Austin guide](https://cloud.wikis.utexas.edu/wiki/x/Eo_vAQ) (LOW-MEDIUM: forum/third-party descriptions only; verify against real downloads).
- Note: the `research-plan` / `classify-confidence` seam was not invoked; confidence levels above come from direct verification (HIGH) or third-party sources (LOW-MEDIUM) as labelled.

---
*Stack research for: vendor-part importer in a PySide6 KiCad library manager*
*Researched: 2026-10-18*
