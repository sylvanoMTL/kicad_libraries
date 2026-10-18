# Pitfalls Research

**Domain:** Vendor ECAD package importer (Ultra Librarian, SnapEDA, SamacSys/CSE, loose files) for KiCad libraries, added to an existing PySide6 library manager, with regex-based KiCad file handling being hardened
**Researched:** 2026-10-18
**Confidence:** MEDIUM-HIGH. Findings tagged [LOCAL] come from direct inspection of `downloaded_examples/ul_CSD85301Q2.zip`, the `Custom/` submodule and the repo's git state (HIGH). Findings tagged [DOCS] come from KiCad dev-docs or the KiCad source version header (HIGH/MEDIUM). Findings tagged [FORUM] come from KiCad forum threads (MEDIUM). Findings tagged [INFERRED] are engineering judgment that should be verified by a fixture or a real KiCad round trip (LOW-MEDIUM).

## Facts Established From the Real Sample and Repo (read these first)

These change how the phases should be planned.

1. **[LOCAL] The UL sample DOES contain a STEP model, contrary to PROJECT.md ("no STEP model").** `DLV0006A.stp` (192 KB, `.stp` extension) sits at the zip root, outside `KiCADv6/`. Its name is the TI package-drawing code, which differs from the footprint name (`DQK0006B`) and the part (`CSD85301Q2`). The footprint has no `(model ...)` block at all. So the importer must (a) find the model outside the KiCad subfolder, (b) associate it with the footprint without any name link, and (c) ADD a `(model ...)` node, not just rewrite an existing path. PROJECT.md "Context" and "Out of Scope" need correcting.
2. **[LOCAL] The UL files are stamped KiCad 6 format and are CRLF.** The symbol has `(version 20211014) (generator kicad_symbol_editor)`, `(id N)` on every property, `ki_locked ""`, 2-space indentation, and 702 CRLF lines. The footprint has `(version 20211014) (generator pcbnew)` with 38 CRLF lines, `fp_text` (not `property`), and unquoted layers (`(layer F.SilkS)`).
3. **[LOCAL] UL symbol `Footprint` property is the bare name `"DQK0006B"` (no `Lib:` prefix), `Reference` is `U` for a dual MOSFET (should be `Q`), and `ki_fp_filters` is `"DQK0006B"`.** The symbol file is named by timestamp (`2026-10-18_09-12-49.kicad_sym`), and the footprint folder is the generic `footprints.pretty`. The symbol is multi-unit (`CSD85301Q2_1_1`, `CSD85301Q2_2_1`).
4. **[LOCAL] The `Custom/` target libraries are a mix of format generations.** Symbol libs: six at `20241209` (KiCad 9, tab-indented, with `generator_version "9.0"`, `exclude_from_sim`, `embedded_fonts`), one at `20231120`, three at `20211014` (UL-era). Footprints: all 14 at `20241229`, `generator "pcbnew"`, `generator_version "9.0"`. Merging a `20211014` symbol into a `20241209` file is the normal case, not an edge case.
5. **[LOCAL] 3D model references in `Custom/` are already inconsistent.** Eight use `${CUSTOM_3DMODEL_DIR}/X.step`, five use `${KIPRJMOD}/Custom/3DModels/X.step`, and extensions vary (`.step`, `.STEP`, `.stp`). Names like `GCT_MEM2085-00-115-00-A_REV0.2` (a dot) and `LTC2954-1-DFN8` (hyphens) are in use, so "names must be alphanumeric/underscore" would reject existing practice.
6. **[LOCAL] The `Custom/` submodule in this worktree is on a detached HEAD** (`git -C Custom symbolic-ref -q HEAD` returns nothing, `status -sb` prints `## HEAD (no branch)`), and its gitdir is `Kicad_Libraries/.git/worktrees/Kicad_Libraries-importer/modules/Custom`, a worktree-private module repository. A commit made there is on no branch and lives in a repo the main checkout does not share.
7. **[LOCAL] `core.autocrlf=true`; the index is LF while the working tree is CRLF** (`git ls-files --eol` shows `i/lf w/crlf`). There is no `.gitattributes`.
8. **[LOCAL] `downloaded_examples/` is untracked in the parent repo**, and the scanner `rglob`s the whole repo tree (CONCERNS.md "Scaling Limits"). Anything extracted inside the repo becomes a "library" in the next scan.

---

## Critical Pitfalls

### Pitfall 1: Pasting an old-format symbol into a newer-format library file

**What goes wrong:** A `(symbol ...)` node written for `(version 20211014)` is spliced verbatim into a `.kicad_sym` whose header says `20241209` (or the reverse, after a future KiCad bumps the version). The header version governs how KiCad interprets the whole file, and the format changed in ways that matter for old content: property IDs stopped being saved (20220914), `ki_description` became the Description field (20230620), `generator_version` and V8 cleanups (20231120), embedded files (20240529), private field flags (20241209), "tilde no longer means empty text" (20250318) [DOCS: `sch_file_versions.h`]. Result ranges from silent oddities (a Datasheet field showing a literal `~`, `ki_description` becoming a custom field) to a library KiCad refuses to load ("created with a newer version" is the common error when going the other direction).

**Why it happens:** Merge code treats the symbol as an opaque text block, and the first manual test happens to load.

**How to avoid:**
- Never rewrite a file's `(version ...)` header to "fix" a mismatch. Never stamp a vendor file with a version newer than its content (a `fp_text` reference under a v8+ header, for example, can fail to parse).
- Preferred path: stage the vendor symbol in a temp `.kicad_sym`, run `kicad-cli sym upgrade` on it (and `kicad-cli fp upgrade` for the `.pretty`), when a KiCad install is detected, then merge the upgraded node [DOCS: kicad-cli reference, 8.0+]. This normalizes to the installed KiCad's format. If `kicad-cli` is absent, merge as-is and warn "format X into format Y" in the preview.
- Surface source version, target version, and generator in the preview for every file. Compare as integers, not strings.
- Strip `(id N)` only when the target header is >= 20220914. Blank a `"~"` Datasheet/Description when the target is >= 20250318.
- Never copy the vendor header (`generator`, `version`) into an existing library. For a NEW library, write the header with the version of the installed KiCad (or the highest version already used in `Custom/`).

**Warning signs:** `Custom/` shows mixed `version` values after an import; KiCad reports "symbol library ... could not be loaded"; Datasheet fields containing `~`.

**Phase to address:** Symbol merge phase. Policy decision (upgrade via CLI vs. leave as-is plus warning) belongs in the roadmap phase that defines the preview.

---

### Pitfall 2: Regex or `str.replace` on S-expressions instead of a lossless tokenizer

**What goes wrong:** Regex-on-first-match picks the wrong `(property "Footprint" ...)` (the file has one per symbol), mis-handles multi-line values, strings containing `(`, `)` or `\"`, and nested sub-symbols. The same fragility already drops external table entries (CONCERNS.md, High). A global `replace("CSD85301Q2", new)` also rewrites the Datasheet URL, `ki_keywords`, and `ki_fp_filters`.

**Why it happens:** The existing codebase has a regex culture, and S-expressions look simple.

**How to avoid:**
- Write ONE small tokenizer/parser module (stdlib) that yields nodes with byte spans (`start`, `end`) and keeps whitespace, so unedited text round-trips byte for byte. Use it for symbols, footprints, AND `sym-lib-table`/`fp-lib-table` (this resolves the table-drop bug as a side effect).
- Edit by splicing: replace only the span of the specific string token or node you change.
- Handle: quoted strings with `\"`, `\\`, `\n`; unquoted atoms (`yes`, `F.Cu`, `${REFERENCE}`, `1.5`); tab, space, CRLF and LF between tokens; no whitespace between `)(` (KiCad writes table entries that way); a UTF-8 BOM; trailing whitespace after the last `)`.
- After every edit, re-tokenize the output: assert balanced parens, assert the untouched sibling nodes are byte-identical, assert the top-level symbol count went up by exactly the expected number.
- Round-trip test: `serialize(parse(x)) == x` for every fixture (UL sample, all 10 `Custom/` symbol libs, all 14 `Custom/` footprints, and the Wurth libs as a stress corpus).

**Warning signs:** A diff of an import touches lines of other symbols; "preserved N external" counts that differ from the entry count in the file.

**Phase to address:** Foundation phase (S-expression module + tests), before any importer logic. Everything else depends on it.

---

### Pitfall 3: Renaming a symbol without renaming its sub-symbols, `extends` children, and name-bearing fields

**What goes wrong:** KiCad stores units as nested nodes named `<SymbolName>_<unit>_<bodystyle>` (the sample has `CSD85301Q2_1_1` and `CSD85301Q2_2_1`; other `Custom/` symbols have `_0_0` and `_0_1`). Renaming only the outer node leaves sub-symbols with the old prefix; KiCad's parser expects sub-symbol names to be built from the parent name, so the library fails to load or the symbol shows no graphics/pins [DOCS/INFERRED: the exact error text was not confirmed; the naming relationship is documented by the format, and a third-party guide states sub-symbols carry the bare parent name plus suffix]. Derived symbols add `(extends "Parent")`; renaming the parent without updating every `extends` that references it breaks the derived symbols (KiCad 8 added multi-level inheritance, 20230819). Related name-bearing fields: `Value` (UL sets it equal to the name), `ki_keywords`, `ki_fp_filters`, and the `Footprint` field if the footprint is renamed.

**Why it happens:** Rename is implemented as "change the first string after `(symbol`".

**How to avoid:**
- Rename = one function that, on the parsed tree, (1) changes the top-level `(symbol "OLD" ...)` name, (2) for each child `(symbol "OLD_<int>_<int>")` rewrites only the prefix when `name == OLD + "_" + digits + "_" + digits`, (3) updates `(extends "OLD")` in any symbol of the same file, (4) leaves everything else alone. Do NOT rewrite by substring.
- Treat parse as `rsplit("_", 2)` with integer checks on the last two segments, because part numbers may legitimately contain underscores and digits (`..._1_1` suffix ambiguity is rare but possible).
- Decide explicitly whether `Value` follows the symbol name (usually yes on import: Value is user-editable in the preview).
- Tests: a multi-unit symbol (the UL sample), an `extends` fixture (build one by hand), a name with underscores and a trailing number, a name containing the substring of another field.

**Warning signs:** Symbol appears in the chooser but is empty; KiCad errors when opening the library; sub-symbol names that do not start with the parent name.

**Phase to address:** Symbol transform phase.

---

### Pitfall 4: Symbol/footprint names that are illegal in KiCad IDs, filenames, or on Windows

**What goes wrong:**
- `/` and `:` are reserved: they break the LIB_ID parser/formatter (KiCad's own commit message: "The '/' and ':' are reserved and cannot be used in symbol or footprint names") [DOCS/FORUM]. A forum report shows a symbol named `S3G-E3/57T` made the whole library unloadable, and renaming inside the editor did not recover it (GitLab issue #11939 "Forward slash in a symbol name corrupts symbol library") [FORUM].
- Footprint names become filenames. KiCad's footprint-name validator rejects `\ / : * ? | " < >` [FORUM]. Windows additionally has reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`...), trailing dots/spaces, and MAX_PATH. SnapEDA/UL part numbers frequently contain `/`, `#`, spaces, `+`, `(`, `)`, `%`, and non-ASCII characters (`µ`, `Ω`).
- A footprint name built from file content and joined into a path is a path-traversal vector (`..\..\x`), independent of zip-slip.
- A hostname-style name in `Footprint` = `Lib:Name` breaks if `Name` contains `:`.
- Do not over-reject: the repo already uses `.` and `-` in names (`GCT_MEM2085-00-115-00-A_REV0.2`, `LTC2954-1-DFN8`).

**Why it happens:** Names are taken from the vendor file and used as-is; developers validate only the library name.

**How to avoid:** One `sanitize_name(kind, s)` helper used by both symbol and footprint paths: replace `\ / : * ? " < > | #`, control characters, and whitespace runs with `_`, strip leading/trailing space and dot, reject Windows reserved names (case-insensitive, with or without extension), cap length (e.g. 100 chars, leaving room for the 260-char path limit), then show original and sanitized names side by side in the preview. Keep `.` and `-`. Re-verify the final name after the user edits it in the preview (validate on edit, not only on load). Check case-insensitive uniqueness within the target library (Windows is case-insensitive, Linux is not, and this repo is shared).

**Warning signs:** A `.kicad_mod` file name differs from its internal `(footprint "...")` name; `Path.exists()` true for a name that "should be new" (case-folding); the preview shows names containing `/`.

**Phase to address:** Naming/preview phase, with unit tests on a table of hostile names.

---

### Pitfall 5: Footprint filename vs internal name mismatch, and not propagating a footprint rename

**What goes wrong:** KiCad addresses a `.pretty` footprint by FILENAME in the library table but shows and writes the internal `(footprint "NAME" ...)`. If the importer renames the file but not the internal name (or vice versa), the footprint is listed under one name and saved under another; symbols then point to a name that does not exist. Because the user can edit the footprint name in the preview (PROJECT.md), the new name must also reach: the file name, the footprint node name, the symbol `Footprint` property (`Lib:NAME`), `ki_fp_filters`, and (for UL) the footprint's `Value` text (`fp_text value DQK0006B`) if you keep them in sync. In all 14 current `Custom/` footprints, file name == internal name, which is the invariant to preserve (checked [LOCAL]).

**How to avoid:** One "plan" object holds `fp_name`; all five places are derived from it. Edit only the first string token after `(footprint`/`(module`. Do not regex-replace the name in `fp_text`/tags/descr (the sample has `(tags "CSD85301Q2 ")` and part numbers that may coincide with the footprint name). Set `Footprint` to `<LibNickname>:<fp_name>` where the nickname is the `.pretty` stem exactly as the table generator will name it. UL emits `"DQK0006B"` with no prefix, and KiCad flags a prefix-less value as "not a valid library identifier"/"Invalid footprint specified" [FORUM, two threads]. Post-install check: re-parse the symbol, resolve `Lib:Name` against the files just written, and fail loudly if it does not resolve.

**Warning signs:** Symbol chooser shows an empty or red footprint field; `check_3d_model_paths`/cross-reference logs "missing footprint" immediately after import.

**Phase to address:** Install phase (planning object) and the post-install verification step.

---

### Pitfall 6: 3D model handling: wrong association, missing block, bad path, silent overwrite, unit and orientation errors

**What goes wrong:**
1. **Association.** The STEP name is unrelated to the footprint name (sample: `DLV0006A.stp` vs `DQK0006B`) and it sits outside the KiCad folder. A rule like "same stem as the footprint" finds nothing; a rule like "any `*.step`" picks up the wrong file in a loose folder with several parts.
2. **No `(model)` node to rewrite.** The sample footprint has none. Rewriting code that looks for an existing path silently does nothing and the user sees no model.
3. **Path forms in vendor files.** Absolute paths (`C:\Users\...`, `/home/...`), `${KIPRJMOD}/...`, `${KICAD6_3DMODEL_DIR}/...` (version-numbered variable names; KiCad 6/7/8/9 differ), `.wrl` instead of `.step`, backslashes, and relative paths. Backslashes in an S-expression string are escape characters, so a Windows path must be treated carefully.
4. **Collisions.** `Custom/3DModels/` is a flat directory. Generic names (`model.step`, `3d.stp`) or two variants of the same part overwrite each other silently.
5. **Extension case.** `.STEP`, `.step`, `.stp` are all used already; a path written as `.step` for a file saved as `.STEP` works on Windows and fails on Linux/macOS.
6. **Units and legacy syntax.** KiCad 6+ writes `(model "path" (offset (xyz x y z)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))` with offset in mm; KiCad 5 legacy used `(at (xyz ...))` with offset in inches [FORUM/INFERRED, verify with a legacy fixture]. Preserving the vendor transform while changing the path is correct; "normalizing" it is a trap. A model dropped in with identity transform may be rotated or offset relative to the pads, and there is no way to detect that without a 3D viewer.
7. **Unresolved variable.** `${CUSTOM_3DMODEL_DIR}` only resolves if the user set it (the app writes it to `kicad_common.json`; the five `${KIPRJMOD}/Custom/3DModels/...` paths in `Custom/` show it has not always been used).

**How to avoid:**
- Model discovery: candidates = all `.step/.stp/.wrl` in the package, any depth. If exactly one STEP, propose it; if several, require the user to choose in the preview; if a footprint already has a `(model ...)`, prefer the file whose basename matches that path's basename. Offer "no model" as an explicit choice (matches the decided behavior: install without and warn).
- Default model file name = footprint name + original extension lower-cased; compare SHA-256 with an existing file of that name: identical -> reuse; different -> conflict in the preview (overwrite/rename/skip).
- If a `(model)` exists: rewrite only the path string, keep `offset/scale/rotate` unchanged. If absent: insert a new node with the explicit identity transform, in the file's own indent/EOL style, and warn "model orientation unverified, check in the 3D viewer".
- Write the path with forward slashes and `${CUSTOM_3DMODEL_DIR}/<file>`. Handle any existing variable-based form but do not touch other footprints' paths (do not silently "fix" the five `${KIPRJMOD}` paths; at most report them).
- Post-install: resolve the written path with the same variable substitution the scanner uses and assert `exists()`. If `CUSTOM_3DMODEL_DIR` is unset in `kicad_common.json`, warn.
- Warn but do not fail on `.wrl`-only packages (KiCad 3D viewer accepts both; STEP is preferred by this repo).

**Warning signs:** Preview shows "model: none" for a zip that contains a `.stp`; two parts share a model file name; the scanner reports a missing model right after import.

**Phase to address:** Package-intake phase (discovery) and install phase (path rewrite and verification). Needs a real SnapEDA and SamacSys sample (PROJECT.md "Dependencies") before the heuristics can be considered validated.

---

### Pitfall 7: Property fields: hidden state, duplicates, ordering, reserved names, wrong Reference prefix

**What goes wrong:**
- New fields (MPN, Manufacturer, Description) are appended without `hide`/`(hide yes)` and without `(at x y 0)`, so they render stacked on the symbol origin in the schematic [INFERRED]. Hidden syntax differs by era: `hide` inside `effects` (UL sample) vs. `(hide yes)` in newer files (20241004 for schematics; verify per file for libs). KiCad reads both, but new nodes should follow the target file's style.
- Old format has `(id N)`; adding a field without a unique id (or reusing 4 for two fields) is tolerated by new readers and ignored since 20220914, but for a `20211014`-stamped file ids matter. Duplicate property NAMES within one symbol are always wrong.
- `ki_keywords`, `ki_description`, `ki_locked`, `ki_fp_filters` are reserved names and cannot be user fields [DOCS]. Do not add a user field named like them.
- Mandatory order/presence: Reference, Value, Footprint, Datasheet (and Description in newer files). A missing `Footprint` or `Datasheet` property makes the symbol editor create them with defaults on next save, and BOM tools assume the order.
- **UL sets Reference `U` for a MOSFET** [LOCAL]; SnapEDA/SamacSys similarly default. Letting vendor defaults through yields wrong designators (`U1` for a transistor) and ERC/annotation confusion.
- `ki_locked ""` and `ki_fp_filters` with a stale footprint name after renaming (Pitfall 5).

**How to avoid:** Treat fields as a list keyed by name, not position. Operations: set-or-create by name, with creation using the target file's style (copy an existing sibling property node as the template, then change name/value/id/at). Always hide new non-core fields. Preview shows Reference as an editable field with a suggestion from the library name (`Transistor_*` -> `Q`, `IC_*` -> `U`, `Connector_*` -> `J`, `Capacitor_*` -> `C`, ...). Update `ki_fp_filters` to the final footprint name. Tests: add MPN to a `20211014` symbol and to a `20241209` symbol and diff both.

**Warning signs:** Overlapping text at the symbol origin in a schematic; the `Footprint` field order differs between imported and hand-made symbols.

**Phase to address:** Symbol transform phase and preview-editing phase.

---

### Pitfall 8: Package layout detection that assumes one layout

**What goes wrong:** Zips differ in depth and in where files live. The UL sample: `KiCADv6/<timestamp>.kicad_sym`, `KiCADv6/footprints.pretty/<FP>.kicad_mod`, `DLV0006A.stp` and `readme.txt`/`ImportGuides.html` at the root. SamacSys downloads reportedly contain both new files (`.kicad_mod`, `.kicad_sym`) and legacy ones (`.lib`, `.dcm`, `.mod`); some contain only legacy [FORUM, MEDIUM: no first-party doc]. SnapEDA layouts, and what a "loose files" folder looks like, are unverified here (no samples). Typical failures:
- Picking the legacy `.lib/.dcm/.mod` or the wrong `.kicad_sym` when several exist (e.g. a `KiCADv5` and a `KiCADv6` folder, as UL offers).
- Using the symbol file name as the part name (UL: a timestamp).
- Treating the generic `footprints.pretty` folder as the library name, or copying the whole `.pretty` directory into `Custom/Footprints/` (creating a library named `footprints`).
- Several symbols in one `.kicad_sym` (multi-part packages) or several `.kicad_mod` (variants), while the "one package per import" decision assumes one of each.
- Nested zips; duplicate member names differing only by case; macOS `__MACOSX/` and `._*` junk; HTML/PDF guides.

**How to avoid:** Detection by CONTENT, not path: classify every member by extension plus a header sniff (`(kicad_symbol_lib`, `(footprint`/`(module`, `ISO-10303-21;` for STEP). Discard `.lib/.dcm/.mod/.sch/.brd` etc. with a visible "ignored: legacy format" log line. If more than one candidate per kind, force a choice in the preview. Take names from INSIDE the files (symbol node name, footprint node name), never from file or folder names. Install footprints by copying the contained `.kicad_mod` files into the chosen `.pretty`, not the vendor `.pretty` folder. Build a fixtures table per vendor in `tests/fixtures/` from real downloads and keep the UL zip as the first one.

**Warning signs:** The preview shows a timestamp as the part name; a new library named `footprints` appears after Rescan.

**Phase to address:** Package-intake phase. SnapEDA and SamacSys/CSE support should be gated on real samples, and flagged for per-vendor research.

---

### Pitfall 9: Zip handling: zip-slip, extraction into the repo, zip bombs, odd names and encodings

**What goes wrong:**
- Extracting with `extractall` into a directory under the repo; member names like `..\..\Custom\Symbols\X.kicad_sym` or absolute paths overwrite arbitrary files (zip-slip). CPython's `ZipFile.extract` sanitizes `..` and drive letters, but code that joins `member.filename` itself does not.
- **Extracting inside the repo** makes the scanner (which `rglob`s everything) list the vendor `KiCADv6/footprints.pretty` and `.kicad_sym` as libraries in the next scan and generated tables [LOCAL, CONCERNS.md].
- Zip bombs / huge members (STEP files can be large; this one is 192 KB, others tens of MB).
- Member names that are non-UTF-8 (cp437 vs UTF-8 flag mojibake), Windows reserved names, trailing dots, alternate data streams (`name:stream`), symlink entries (check `external_attr`), directory entries, duplicate names.
- Text content in UTF-8 with BOM, cp1252 (`µ`, `°`, `Ω` in descr), or UTF-16; output must be UTF-8 without BOM.

**How to avoid:** Do not extract at all for analysis: read members into memory via `ZipFile.read(info)` after enforcing limits (member count, per-file and total uncompressed size, compression ratio). Write only the files you intend to install, to names you generate from sanitized content-derived names (Pitfall 4), never from archive paths. If staging is needed (e.g. for `kicad-cli upgrade`), use `tempfile.TemporaryDirectory()` outside the repo. Reject entries that are symlinks, absolute, contain `..` after normalization, or whose resolved path leaves the staging root. Decode text as UTF-8 (`utf-8-sig` to tolerate BOM), fall back to cp1252 with a log warning, and always write UTF-8 no BOM. Never open or render the bundled `.html` guides (embedded SVG/JS) in a Qt web view.

**Warning signs:** A new library appears after Rescan with a name from the vendor; files appear outside the target directories.

**Phase to address:** Package-intake phase; add hostile-zip unit tests (traversal, absolute path, duplicate, oversized, symlink).

---

### Pitfall 10: Git: committing in the `Custom` submodule on a detached HEAD (and in a worktree-private module)

**What goes wrong:** [LOCAL] In this worktree `Custom` is on a detached HEAD. A commit there is on no branch; the next `git submodule update`, a checkout, or a GC can orphan it, while the parent happily records the new gitlink SHA. Because the module's gitdir is worktree-private (`.git/worktrees/Kicad_Libraries-importer/modules/Custom`), the commit may not even be visible from the main checkout `C:/Git_Repo_Clones/Kicad_Libraries`. "Commit only, never push" then means the parent points at a submodule SHA that exists nowhere else: anyone (or another clone) who pulls the parent cannot fetch it. In addition: `git add -A`/`commit -a` in `Custom` sweeps in unrelated modified files (3D model line-ending noise, user scratch files); `git commit -a` in the parent sweeps `downloaded_examples/` and unrelated `.planning/` files [LOCAL: untracked at start].

**How to avoid:**
- Before committing, run `git -C Custom symbolic-ref -q HEAD`. If it fails: stop and offer (a) `git switch main` if the current commit is an ancestor/equal to `main`'s tip, otherwise (b) `git switch -c <name>` and tell the user, never commit silently on a detached HEAD. The confirmation dialog must show branch (or "DETACHED"), the exact files to be staged, and the commit message.
- Stage by explicit pathspec (the files this import wrote), `git add -- <paths>`, and `git commit -m ... -- <paths>`; refuse if the index already has other staged changes, and show `git status --porcelain` for the submodule.
- In the parent, stage only the gitlink: `git add -- Custom` then `git commit -m ... -- Custom`. Verify afterward that `git -C Custom rev-parse HEAD` equals `git ls-tree HEAD Custom`.
- After commit, tell the user explicitly: "Commit is local; push Custom FIRST, then the parent" (matches CLAUDE.md workflow), and show `git -C Custom status -sb` ahead count.
- Run git via `subprocess.run([...], capture_output=True, text=True, timeout=...)` with no shell, check return codes, surface stderr in the log panel (not in a Qt slot exception), and never run git on the UI thread.
- Pre-flight: `git config user.name/user.email` set; submodule initialized; `index.lock` absent.

**Warning signs:** `git status` in parent shows `Custom (new commits)` but `git branch --contains` in `Custom` shows nothing; "fatal: not a git repository" for the submodule path in a worktree.

**Phase to address:** Git-commit phase (last). Add an integration test using a temp parent repo + a temp submodule with a detached HEAD.

---

### Pitfall 11: Line endings (CRLF/LF) and encoding churn making commits unreadable

**What goes wrong:** [LOCAL] The UL files are CRLF; `Custom/` has `autocrlf=true` with an LF index and CRLF working tree, no `.gitattributes`. Python text-mode `open(..., "w")` on Windows turns `\n` into `\r\n`; reading with default `newline=None` turns `\r\n` into `\n`, so a read-modify-write of an LF file silently rewrites every line ending and produces a whole-file diff, or mixed endings if text from a CRLF vendor file is spliced into an LF file (and the reverse). KiCad itself rewrites a file on the next save in its own style (tabs in v9, space-indented in older). So whole-file diffs will occasionally come from KiCad, not from the importer, and the two must be distinguishable.

**How to avoid:** Read and write with `newline=""` (or bytes) so nothing is translated; detect the dominant EOL of the TARGET file and convert only the inserted fragment to it (new files: LF, which is what KiCad 9 writes, and the working-tree CRLF then follows autocrlf). Consider adding a `.gitattributes` to `Custom/` (`*.kicad_sym text eol=lf`, `*.kicad_mod text eol=lf`, `*.kicad_pro`, and binary for `*.step`/`*.stp`/`*.wrl`) as a separate, deliberate commit, because STEP files with `autocrlf=true` are at risk of being rewritten (`.step` is ASCII text and git treats it as text, so CRLF conversion changes the bytes and the hash; compare `Custom/3DModels` entries which currently show `i/lf w/crlf`). Add a test: merge a CRLF symbol into an LF library and vice versa, assert uniform line endings and that untouched lines are byte-identical. Optionally re-indent inserted nodes to the target style, but it is cosmetic.

**Warning signs:** `git diff --stat` after import shows hundreds of changed lines in an existing library; `git ls-files --eol` shows `w/mixed`.

**Phase to address:** Foundation phase (IO helpers) and install phase tests.

---

### Pitfall 12: Non-atomic, unbacked writes to curated libraries, and Windows file locking

**What goes wrong:** The importer is writing hand-curated files (`.kicad_sym`) that are not recoverable except via git. A crash or exception mid-write truncates a library. On Windows, `os.replace()` raises `PermissionError` if any process has the target open without `FILE_SHARE_DELETE` (KiCad while loading, antivirus, indexer, Explorer preview, git); a naive `write_text` on the same file may succeed but truncate while KiCad has it in memory [INFERRED for KiCad's exact locking behavior]. A multi-file install (symbol + footprint + model) can fail halfway, leaving a symbol whose footprint was never written (Pitfall 5).

**How to avoid:**
- Atomic write helper (shared with the table/`kicad_common.json` hardening): temp file in the SAME directory -> flush+`os.fsync` -> `os.replace`, with a few retries/backoff on `PermissionError`, then a clear error. Temp names must be ignored by git (`Custom/.gitignore` already ignores `*.tmp`, `*.bak`) and cleaned up in `finally`.
- Transactional install: validate everything in memory first (preview plan -> rendered outputs -> re-parse), then write footprint(s), model, and finally the symbol last (the symbol is the entry point that refers to the rest), record each written path, and on failure restore/delete what was written in this run. Keep a pre-image of the target `.kicad_sym` in memory for rollback; do not rely on `.bak` files in the repo.
- Guard the destination: only write inside `Custom/` (resolve and `is_relative_to`), never into `WurthElektronik/`.
- Catch `OSError` at the service level and return structured results; the Qt slot only logs (this is the existing "unhandled FS errors in a Qt slot" concern).
- Best-effort check that KiCad is running (e.g. `tasklist` for `kicad.exe`, `eeschema.exe`, `pcbnew.exe`) and warn.

**Warning signs:** "Permission denied" only on some runs; a library that is shorter than before.

**Phase to address:** Foundation phase (atomic IO) and install phase (transaction).

---

### Pitfall 13: KiCad's in-memory state and caches go stale after an external write

**What goes wrong:** KiCad loads library tables at startup and caches footprint library contents (`fp-info-cache`, location depends on version, per-user). Forum reports (mostly KiCad 5/6 era) show footprints added or moved outside KiCad not appearing, ghost entries, and zero-length/corrupt caches; the usual remedy is quitting KiCad and deleting the cache [FORUM, MEDIUM; behaviour in 9/10 unverified]. A symbol or footprint editor that already has `Custom/Symbols/X.kicad_sym` open holds its own copy and may overwrite the importer's edit when the user saves [INFERRED]. A brand new library only appears after the table is regenerated AND KiCad reloads its tables (a restart in older versions; the library table dialog's OK in newer).

**How to avoid:** Never touch KiCad's caches yourself. After install, show a "Done" panel: what was written, "close and reopen the Symbol/Footprint editors; if the new part does not appear, restart KiCad". Run the table regeneration (existing feature) only if a NEW library was created, and pre-select it (the existing Rescan resets in-progress selection, a known bug in CONCERNS.md that will make the new library silently unchecked). Warn if KiCad processes are detected (Pitfall 12).

**Warning signs:** Part visible in Explorer but not in KiCad; the new library missing from `fp-lib-table` after Generate.

**Phase to address:** Install phase (post-install UX) and the table-hardening phase.

---

### Pitfall 14: Library-name collisions and wrong target conventions

**What goes wrong:** A new `Custom` library name that equals an existing nickname in `WurthElektronik/` (or a KiCad default library like `Connector_USB`) collides in the generated table (CONCERNS.md: `_fp_items` keyed by nickname only; table `name` must be unique). Symbol and footprint lib names must pair (`X.kicad_sym` + `X.pretty`), and `.kicad_sym` is under `Symbols/` while `.pretty` is under `Footprints/` in `Custom/` [LOCAL]. Creating only one half, or one with different case, breaks the pairing logic and the synced selection. Suggested names `<Type>_<SubCategory>_<Manufacturer>` can contain characters illegal as nicknames (spaces, `:`), and nicknames are cut off in the KiCad chooser.

**How to avoid:** Validate the library name (same sanitizer, Pitfall 4) and check case-insensitively against ALL scanned nicknames across sources plus the detected KiCad default library names. Create both halves atomically as part of the plan (empty `.pretty` dir is fine for the filesystem but not for git; the footprint is written into it in the same transaction). Make symbol-name uniqueness check target-library-scoped (duplicate names across libraries are legal in KiCad since the nickname disambiguates), but warn when the same name exists elsewhere in `Custom/`. Fix the key-by-nickname bug before shipping the importer, as the new library name is the very thing that triggers it.

**Warning signs:** Generated table has two entries with the same `name`; selecting a Custom symbol toggles a Wurth footprint library.

**Phase to address:** Target-library phase; the keying fix belongs to the hardening phase and must land first.

---

## Moderate Pitfalls

### Pitfall 15: S-expression string escaping when writing values

**What goes wrong:** Values from the preview (Description, Datasheet URLs, MPN) can contain `"`, `\`, newlines, or non-ASCII. Writing them raw produces an invalid file (the existing table writer has the same defect, CONCERNS.md). Windows paths in `descr`/model strings contain backslashes. Doing escape then unescape twice corrupts values.
**Prevention:** One `quote(s)` function: escape `\` first, then `"`, and encode newline/CR/tab as `\n`/`\r`/`\t` (the escapes KiCad's own formatter produces; confirm against a KiCad-saved fixture with a description containing a quote). Copy unedited strings from source SPANS verbatim (never decode/re-encode); escape only values the user typed. Test with `a"b`, `c:\d`, a trailing backslash, a unicode `µ`, and an embedded newline. Reject control characters in single-line fields (names).
**Phase to address:** Foundation (S-expression module).

### Pitfall 16: Duplicates and overwrite semantics

**What goes wrong:** Importing the same part twice appends a second `(symbol "X")` to the library (two top-level nodes with the same name), which KiCad treats as a duplicate/overwrites unpredictably. "Overwrite" replaces by name match on the first regex hit instead of node span. "Rename" suggests `X_1` which already exists. Case-insensitive FS collisions on footprints (`dqk0006b` vs `DQK0006B`).
**Prevention:** Conflict detection on the parsed tree for symbols and on a case-folded name set for footprint and model files. Auto-suggest the next free suffix by checking the actual set. Overwrite replaces the node span exactly; skip leaves all files byte-identical; the three choices are per-object (symbol, footprint, model), tested individually. Importing the identical bytes again should report "no changes" and not create a commit.
**Phase to address:** Preview/conflict phase.

### Pitfall 17: KiCad table and variable assumptions inherited from the existing code

**What goes wrong:** The importer reuses scan/table code with known defects: lexical version sort (`9.0` > `10.0`), non-atomic writes of `kicad_common.json`, no external-entry preservation, overlapping scans. Importer features that depend on them (`CUSTOM_3DMODEL_DIR` resolution, rescan after install, regenerating tables) inherit the bugs. Also `${KICAD9_FOOTPRINT_DIR}`-style variables are version-named, so cross-referencing defaults through them breaks on a new major version.
**Prevention:** Complete the hardening items first and gate the importer on them (PROJECT.md already lists them). Use numeric version sorting. Treat the importer's "rescan after install" as a guarded single scan (no overlapping workers).
**Phase to address:** Hardening phase precedes importer phases.

### Pitfall 18: Testing only the happy-path fixture

**What goes wrong:** A suite built from the one UL sample proves nothing about SnapEDA/SamacSys/loose files, KiCad 9 `20241209` inputs, extends, CRLF/LF, or hostile zips. Tests that compare against a hand-edited "expected" file freeze today's bug.
**Prevention:** Fixtures: UL sample, 3+ `Custom/` libs (real KiCad 9 output), the two Wurth libs as parse/round-trip stress, synthetic hostile zips, hand-built `extends` and legacy-syntax cases. Property tests: parse/serialize identity, untouched-nodes-byte-identical after merge. A smoke test that loads the output with `kicad-cli` when it is installed (skipped otherwise). Mark SnapEDA/SamacSys tests `xfail`/skipped until real samples exist (PROJECT.md says they are required).
**Phase to address:** Every phase; foundation phase creates the harness.

### Pitfall 19: Footprint/KiCad version attributes in the footprint file mishandled

**What goes wrong:** The importer "updates" `(generator pcbnew)`/`(version ...)` of a footprint to look newer, or converts `fp_text` to `property` by hand. Vendor tools put `generator pcbnew` (third-party tools are told not to use KiCad's own generator names [DOCS], yet UL uses `pcbnew` and `kicad_symbol_editor`), so generator can't be used to detect "KiCad-authored".
**Prevention:** Leave footprint headers and bodies untouched except for the name token and the model node. KiCad upgrades on load. Detect format by `version` integer only; use `generator` for display. Do not hand-convert; use `kicad-cli fp upgrade` if conversion is wanted.
**Phase to address:** Footprint transform phase.

### Pitfall 20: Mutating the user's real library on the first test run

**What goes wrong:** Development against the real `Custom/` submodule leaves test parts in the user's curated libraries, or tests commit into the real submodule.
**Prevention:** All tests use `tmp_path` copies; the app's install path takes `custom_root` as a parameter; a "dry-run" mode renders the whole plan and writes nothing; the git step is mockable and its pure part (command building) unit-tested.
**Phase to address:** Foundation and install phases.

## Minor Pitfalls

### Pitfall 21: Datasheet and description artifacts
UL/SnapEDA datasheet fields may be empty, `~`, or a local file path; keywords contain trailing spaces (`(tags "CSD85301Q2 ")`). **Prevention:** trim, blank `~`, warn on `file://` and absolute local paths.

### Pitfall 22: Symbol pin names with overbars and special characters
`~{RESET}` is the overbar syntax in newer files; older files used `~RESET~`-style (changed 20210619). Do not "fix" pin text. **Prevention:** leave graphics and pins untouched (matches the Out-of-Scope decision to not edit symbol graphics).

### Pitfall 23: Hidden-pin / power-pin and `in_bom`/`on_board` flags
UL has `(in_bom yes) (on_board yes)`; newer files use `(exclude_from_sim ...)`, `(in_bom ...)`, `(on_board ...)`, `(dnp ...)`. Missing `exclude_from_sim` is accepted. **Prevention:** copy verbatim; do not add flags yourself.

### Pitfall 24: Empty target library bootstrap
A new `.kicad_sym` needs a valid header: `(kicad_symbol_lib (version N) (generator "...") (generator_version "..."))` + closing paren, and `Symbols/` / `Footprints/` directories must exist. A header with the wrong version (Pitfall 1) or missing closing paren makes the first import look like a merge bug. **Prevention:** a single `new_symbol_lib_text(version)` function, round-trip tested through the tokenizer.

### Pitfall 25: Large STEP files in git
STEP files are text and compress well, but multi-MB files bloat the submodule history and `autocrlf` can corrupt them (Pitfall 11). **Prevention:** warn when a model exceeds a size threshold (e.g. 5 MB); consider Git LFS only as a user decision; do not auto-add LFS config.

### Pitfall 26: Preview that lies
The preview is computed by a different code path than the install (the old CLI vs GUI divergence in CONCERNS.md). **Prevention:** build one immutable `ImportPlan` with the rendered output text and target paths; the preview renders the plan, install executes the same plan, no recomputation.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Regex find/replace for names and paths in vendor files | Fast to write | Corrupts multi-unit, `extends`, other fields (Pitfalls 2, 3) | Never for writes; acceptable only for read-only sniffing of a file kind |
| Splice vendor symbol text verbatim, ignore `version` | Works for the first sample | Mixed-format libraries, odd rendering, load failures (Pitfall 1) | Only with the preview warning, and only when source <= target version |
| Extract the zip to a repo subfolder | Easy file handling | Scanner picks up vendor libraries; zip-slip risk (Pitfall 9) | Never |
| `git add -A && git commit` in the submodule | One command | Sweeps unrelated files, commits on detached HEAD (Pitfall 10) | Never |
| Hard-code `${CUSTOM_3DMODEL_DIR}` only | Matches CLAUDE.md | Silent missing model when the variable isn't set; five existing `${KIPRJMOD}` paths | Fine as the default, with a post-install resolve check |
| Text-mode file IO | Simple code | EOL churn, BOM issues (Pitfall 11) | Never; use `newline=""` or bytes |
| Skipping `kicad-cli` normalization | No dependency on an install | Mixed formats | Acceptable as the fallback path when CLI is not found |
| One fixture (UL sample) | Quick start | Heuristics tuned to one vendor | Only until real SnapEDA/SamacSys samples are added |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| KiCad symbol lib format | Assuming a single format | Read `version` as an integer; compare to the target; normalize via `kicad-cli sym upgrade` when available |
| KiCad footprint lib | Assuming the file name defines the footprint | Filename == internal name must hold; both change together |
| KiCad path variables | Assuming `CUSTOM_3DMODEL_DIR` is defined | Check `kicad_common.json`, warn if absent, verify the resolved path exists |
| Library tables | Regenerating after every part | Only when a new library was created; preselect it; preserve external entries |
| `kicad-cli` | Assuming it is on PATH | Locate under the detected KiCad `bin/`; treat as optional; run with a timeout, capture stderr; never on the UI thread |
| Git (CLI) | Using shell strings, ignoring detached HEAD | `subprocess.run([...])`, explicit pathspecs, check HEAD state, surface stderr |
| Git worktree + submodule | Assuming the submodule is shared between worktrees | The module gitdir is worktree-private here; tell the user where the commit lives |
| Vendor zips | Trusting `filename` | Content sniffing, in-memory reads, size limits |
| Qt | Doing import/IO in a slot | Run on a worker thread; return structured results (level, message); no exceptions escaping the slot |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Re-tokenizing every library on every preview keystroke | UI lag when editing names | Parse the target once per session; cache by (path, mtime); validate names against a precomputed set | Libraries over a few MB or 500+ symbols |
| Hashing large STEP files repeatedly | Preview freeze | Hash once, stream in chunks | 50 MB+ models |
| Full-repo rescan after every import | 10 s+ stalls with the Wurth submodule | Targeted rescan of the changed library (or the existing mtime cache idea in CONCERNS.md) | Wurth-sized trees |
| Tokenizer written as repeated `str.find` on a big string | Quadratic time | Single-pass index-based scanner | Files over about 1 MB |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Joining archive member names to paths | Arbitrary file overwrite (zip-slip) | Never use archive paths; generate names; assert resolved path is inside the target |
| Using names from file content as path segments | Path traversal via `(footprint "..\\..\\x")` | Sanitizer (Pitfall 4) + `resolve().is_relative_to(target)` |
| Decompressing unbounded input | Disk/memory exhaustion | Per-member and total size/ratio limits |
| Rendering vendor HTML guides | Script execution in a web view | Ignore them; never open |
| Running commands built from file content | Command injection (e.g. commit message from a part name via shell) | List-form `subprocess`, no shell; commit message passed as an argument |
| Symlink entries in a zip or a folder import | Reading or writing outside the sandbox | Skip symlinks (`os.path.islink`, `external_attr`) |
| Writing into `WurthElektronik/` or any non-`Custom` path | Corrupting upstream-owned libraries | Hard allow-list of the `Custom` root |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Preview shows only the final names | User can't see what rewrites happened | Show before -> after for: symbol name, sub-symbol prefix, footprint name, `Footprint` property, `ki_fp_filters`, model path, plus format versions |
| Silent "no 3D model" | Part is later found without a model | Explicit row "3D model: none (install without) / chosen file", warning in the log and the commit message |
| Overwrite prompt per conflict with no diff | Wrong choice | Show the existing vs new node summary (pin count, units, footprint) |
| Commit dialog without file list or branch | User can't judge the commit | List files, show branch or DETACHED, offer "Commit in Custom" and "Update parent ref" as separate confirmable steps |
| Errors as modal tracebacks | Lost context | Structured results to the log panel (red) plus a summary |
| Wrong default Reference prefix accepted blindly | Wrong designators later | Editable Reference with a suggestion from the library type |

## "Looks Done But Isn't" Checklist

- [ ] **Symbol merge:** Verify untouched symbols are byte-identical, paren balance holds, and the output loads in KiCad's Symbol Editor (manual once per format era: 20211014 into 20241209).
- [ ] **Sub-symbol rename:** Verify every `<Name>_<u>_<s>` child and every `extends` follows the rename.
- [ ] **Footprint link:** Verify the symbol `Footprint` value is `<Lib>:<FP>`, the `.kicad_mod` exists at `<Lib>.pretty/<FP>.kicad_mod`, and the internal name equals the file name.
- [ ] **3D model:** Verify the `(model ...)` path resolves with `CUSTOM_3DMODEL_DIR` set, the file exists in `Custom/3DModels/`, and the 3D viewer shows the part aligned with the pads (cannot be automated; manual check list).
- [ ] **UL sample specifically:** Verify `DLV0006A.stp` is found at the zip root and a model node is added to `DQK0006B`.
- [ ] **Line endings:** Verify no whole-file diff in an existing library after import.
- [ ] **Git:** Verify HEAD is on a branch, only intended files were committed, the parent records the new SHA, and nothing was pushed.
- [ ] **Tables:** Verify a NEW library is present and checked after the post-install rescan/Generate, and external entries survive.
- [ ] **Failure path:** Kill the import after the footprint write; verify rollback leaves no dangling symbol.
- [ ] **Hostile zip:** Verify traversal, absolute, duplicate, symlink and oversized entries are rejected and nothing is written outside the staging area.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Corrupt/truncated library written | LOW | `git checkout -- <file>` in `Custom/` (or restore from the in-memory pre-image the importer kept for rollback) |
| Commit on detached HEAD | LOW-MEDIUM | `git branch rescue <sha>` in `Custom`, then `git switch main && git merge rescue`; use `git reflog` if already moved |
| Parent points to a submodule SHA not pushed | MEDIUM | Push `Custom` first from the clone that has the commit, then the parent; if the module is worktree-private, `git fetch` from the worktree's module gitdir into the main module |
| Stale KiCad caches | LOW | Close KiCad; delete `fp-info-cache`; reopen |
| Mixed-version library | MEDIUM | `kicad-cli sym upgrade --force` on the library (or open and save in KiCad); review the diff |
| Whole-file EOL diff committed | LOW-MEDIUM | `git revert`, then re-apply with the corrected IO; add `.gitattributes` |
| Wrong model alignment | LOW | Edit offset/rotate in the footprint editor's 3D settings and save |
| Collided library nickname | MEDIUM | Rename the `.kicad_sym`/`.pretty` pair, regenerate tables, update `Footprint` fields |

## Pitfall-to-Phase Mapping

Suggested phases (names are placeholders for the roadmap; the order is driven by dependencies):

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| 2 Regex vs tokenizer; 15 Escaping | P1 Foundation: S-expression module, atomic IO, test harness | Round-trip byte identity over all repo KiCad files; escape tests |
| 11 CRLF/LF; 12 Atomic writes and locks | P1 Foundation (IO helpers) | Mixed-EOL merge test; replace-with-retry test with a held lock |
| 17 Inherited defects (version sort, table drop, scan overlap, nickname key) | P2 Hardening of existing code (precedes importer) | Existing CONCERNS.md test list passes |
| 8 Layout detection; 9 Zip safety | P3 Package intake | UL fixture finds sym, fp, and the root `.stp`; hostile-zip tests |
| 4 Names; 5 Footprint rename; 14 Library names | P4 Naming and target library | Hostile-name table test; filename == internal name invariant |
| 1 Format versions; 3 Sub-symbols; 7 Fields; 19 Footprint headers | P5 Transform (symbol and footprint) | 20211014 into 20241209 test; multi-unit and extends tests; Footprint field resolves |
| 6 3D model | P5 Transform + P6 Install | Model discovered and node added for the UL sample; path resolves; hash conflict test |
| 16 Duplicates; 26 Preview lies | P6 Preview, conflicts, install transaction | One `ImportPlan` drives preview and install; double-import is a no-op; failure rolls back |
| 13 KiCad caches; tables | P7 Post-install (rescan, tables) | New library checked and present in generated table |
| 10 Git detached HEAD, worktree module | P8 Commit | Integration test with a temp detached submodule; explicit pathspec only |
| 18 Test coverage | All phases | Fixtures grow with each vendor; SnapEDA and SamacSys tests unskipped when samples arrive |

**Research flags for phases:**
- P3 (SnapEDA, SamacSys/CSE layouts): needs real downloads and per-vendor research. Current knowledge is forum-level only.
- P5 (symbol version normalization via `kicad-cli`): verify `kicad-cli sym upgrade`/`fp upgrade` behavior and the installed KiCad version on the target machine with a spike before committing to the approach.
- P5 (3D model orientation and legacy `(at (xyz))` inch semantics): verify with a legacy SamacSys fixture.
- P8 (git in a worktree with a private submodule gitdir): spike early; the behavior of the main checkout vs the worktree is environment-specific.
- P1, P2, P4, P6, P7: standard patterns, unlikely to need further research.

## Sources

- Local inspection (HIGH): `downloaded_examples/ul_CSD85301Q2.zip` (members, headers, CRLF counts, STEP header), `Custom/` submodule (symbol/footprint versions, model paths, name/file match, `.gitignore`, `core.autocrlf`, `git ls-files --eol`, `symbolic-ref`, `.git` gitfile), `.planning/PROJECT.md`, `.planning/codebase/CONCERNS.md`.
- KiCad developer docs, S-expression intro, symbol and footprint pages: https://dev-docs.kicad.org/en/file-formats/sexpr-intro/ , https://dev-docs.kicad.org/en/file-formats/sexpr-symbol-lib/ , https://dev-docs.kicad.org/en/file-formats/sexpr-footprint/ (HIGH: strings UTF-8, `ki_*` reserved names, library IDs, third-party generators must not use KiCad's names; escape rules are NOT documented there).
- KiCad symbol-lib format version history: https://docs.kicad.org/doxygen/sch__file__versions_8h_source.html (MEDIUM-HIGH: doxygen snapshot of the master branch; it lists versions beyond what current KiCad releases write, so use only the milestones cited).
- KiCad `LIB_ID` and name validation: https://docs.kicad.org/doxygen/classLIB__ID.html , https://docs.kicad.org/doxygen/classFOOTPRINT__NAME__VALIDATOR.html , KiCad source commit 56e2df79 (Wayne Stambaugh) quoted via search results (MEDIUM).
- Forum: forward slash in symbol name corrupts library (GitLab #11939): https://forum.kicad.info/t/issue-with-unsupported-characters-in-symbol-name/36462 (MEDIUM).
- Forum: prefix-less Footprint field flagged invalid: https://forum.kicad.info/t/footprint-is-not-a-valid-library-identifier-format-when-assigning-to-symbol/44403 and https://forum.kicad.info/t/footprint-of-samacsys-component-shown-as-invalid-in-schematic-editor/60895 (MEDIUM). The second thread also reports SamacSys downloads including both legacy (`.lib/.dcm/.mod`) and new files.
- Forum: forbidden characters in names: https://forum.kicad.info/t/are-there-any-forbidden-discouraged-characters-in-footprint-symbols/55145 (LOW-MEDIUM).
- Forum: stale `fp-info-cache` and library not refreshing: https://forum.kicad.info/t/fp-info-cache-keeps-getting-corrupted/29768 and related threads (LOW-MEDIUM; KiCad 5/6 era).
- Forum: 3D model path problems (`${KIPRJMOD}`, relative paths, missing files): https://forum.kicad.info/t/kiprjmod-resets-to-empty-value-after-opening-pcb-editor/69987 , https://forum.kicad.info/t/why-a-footprint-points-to-a-3d-model-but-the-model-file-doesnt-exist/24979 (LOW-MEDIUM).
- `kicad-cli sym upgrade` / `fp upgrade`: https://docs.kicad.org/8.0/en/cli/cli.html , https://docs.kicad.org/doxygen/command__sym__upgrade_8cpp_source.html , https://techoverflow.net/2024/05/05/how-to-force-upgrade-all-kicad-symbol-libraries/ (MEDIUM-HIGH).
- Not verified (explicit gaps): exact KiCad parser error text for sub-symbol prefix mismatch; whether KiCad 9/10 still reads legacy `(at (xyz))` model offsets in inches; the precise escape set KiCad's formatter emits; SnapEDA package layout and its habitual model paths; KiCad's symbol-editor behavior when the library file changes on disk.

---
*Pitfalls research for: KiCad vendor-part importer and S-expression hardening*
*Researched: 2026-10-18*
