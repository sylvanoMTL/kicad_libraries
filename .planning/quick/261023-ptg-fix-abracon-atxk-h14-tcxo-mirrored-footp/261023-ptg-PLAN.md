---
phase: quick-261023-ptg
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/quick/261023-ptg-fix-abracon-atxk-h14-tcxo-mirrored-footp/check_atxk_h14.py
  - Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod
  - Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATX-14.kicad_mod
  - Custom/Symbols/Oscillator_TCXO_Abracon.kicad_sym
files_deleted:
  - Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATX-14.kicad_mod
autonomous: true
requirements: [INST-03]

estimate:
  tokens: 45000
  raw_tokens: 45000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "KiCad 10 (kicad-cli fp upgrade re-emitting the footprint into a temp dir) places ATXK-H14 pad 1 at (-0.725, 0.5) bottom-left, pad 2 at (0.725, 0.5), pad 3 at (0.725, -0.5) and pad 4 at (-0.725, -0.5), matching the datasheet top view. Every pad is smd rect 0.85 x 0.7, so the pitch stays 1.45 x 1.00."
    - "The ATXK-H14 footprint has Datasheet https://abracon.com/datasheets/ATXK-H14.pdf, a filled Description property, and matching descr and tags entries."
    - "ATX-14.kicad_mod no longer exists. Before it was deleted, nothing in Custom/ referenced Oscillator_TCXO_Abracon:ATX-14. No KiCad file under Custom/ still mentions ATX-14."
    - "Symbol ATXK-H14 has Datasheet https://abracon.com/datasheets/ATXK-H14.pdf, Description '32.768kHz TCXO, CMOS output, ±5ppm -40..+85°C, 1.5-3.63V, 2.15x1.35mm', ki_keywords 'tcxo oscillator 32.768kHz 32k rtc cmos abracon', ki_fp_filters 'ATXK*H14*' and a hidden Manufacturer 'Abracon'. Value 'ATXK-H14' and Footprint 'Oscillator_TCXO_Abracon:ATXK-H14' are unchanged."
    - "Pin 1 is named OE. The pin map is 1 OE, 2 GND, 3 OUT, 4 VDD."
    - "Both edited files load in kicad-cli 10 (exit 0) and in the app's own parser (kicad_lib_manager.kicad_files) with no mixed line endings and no BOM. Their version headers are unchanged (footprint 20241229, symbol 20241209)."
    - "Custom main gains exactly one new local commit, containing only the three Custom paths. It is not pushed. The parent repo's Custom gitlink is neither staged nor committed."
    - "The scanner/corpus test subset has the same set of failures as before the change."
  artifacts:
    - path: ".planning/quick/261023-ptg-fix-abracon-atxk-h14-tcxo-mirrored-footp/check_atxk_h14.py"
      provides: "One-shot checker: runs kicad-cli upgrade into a temp dir and asserts pads, properties, pins, cleanup and file hygiene on the source and on KiCad's re-emitted text"
      contains: "ATXK*H14*"
    - path: "Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod"
      provides: "Top-view pad numbering plus descr/tags/Datasheet/Description"
      contains: "(descr "
    - path: "Custom/Symbols/Oscillator_TCXO_Abracon.kicad_sym"
      provides: "Corrected ATXK-H14 symbol metadata, hidden Manufacturer, pin 1 OE"
      contains: "(property \"Manufacturer\" \"Abracon\""
  key_links:
    - from: "Custom/Symbols/Oscillator_TCXO_Abracon.kicad_sym Footprint property"
      to: "Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod"
      via: "Oscillator_TCXO_Abracon:ATXK-H14 (library nickname : file stem), unchanged"
      pattern: "Oscillator_TCXO_Abracon:ATXK-H14"
    - from: "Custom/Symbols/Oscillator_TCXO_Abracon.kicad_sym ki_fp_filters"
      to: "footprint name ATXK-H14"
      via: "glob ATXK*H14* matches ATXK-H14"
      pattern: "ATXK\\*H14\\*"
    - from: "check_atxk_h14.py"
      to: "C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
      via: "fp upgrade / sym upgrade --force -o <TemporaryDirectory>, never in place"
      pattern: "upgrade"
---

<objective>
Fix the Abracon ATXK-H14 TCXO in the `Custom` submodule. Its footprint pads are numbered from the datasheet bottom view, so they are mirrored. The symbol carries the wrong datasheet and placeholder metadata. The unused ATX-14 footprint, also mirrored and from a different family, is deleted.

Purpose: a board laid out with the current footprint would have pin 1 (OE) and pin 4 (VDD) in the wrong positions, and likewise pins 2 (GND) and 3 (OUT). The source of truth is the Abracon ATXK-H14 datasheet rev 09-05-25, page 3 (Mechanical Dimensions). Top view: #1 bottom-left, #2 bottom-right, #3 top-right, #4 top-left. Pins: 1 Output Enable (tie to VDD), 2 GND, 3 Output, 4 VDD. Land pattern: pads 0.85 x 0.70 mm, centre pitch 1.45 mm (X) x 1.00 mm (Y). Package 2.15 x 1.35 x 1.1 mm. KiCad Y grows downward, so "bottom" means +Y.

Output: corrected `ATXK-H14.kicad_mod` and `Oscillator_TCXO_Abracon.kicad_sym`, `ATX-14.kicad_mod` removed, one local commit inside `Custom` (not pushed, parent gitlink untouched), and a re-runnable checker script in this quick-task folder.

Requirement note: this is a library-content fix with no importer code change. INST-03 is cited because the fix restores, for an existing Custom part, the consistency INST-03 demands: file name, internal footprint name, symbol Footprint field and ki_fp_filters. No CONTEXT.md exists, so there are no D-XX decisions. Owner-specified values are quoted verbatim below. The footprint Description/descr/tags wording is planner's discretion (see Task 1).
</objective>

<execution_context>
@C:/Git_Repo_Clones/Kicad_Libraries-importer/.claude/gsd-core/workflows/execute-plan.md
@C:/Git_Repo_Clones/Kicad_Libraries-importer/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod
@Custom/Symbols/Oscillator_TCXO_Abracon.kicad_sym
@kicad_lib_manager/kicad_files.py

HARD RULES (every task):
- `Custom/` is a git submodule (`sylvanoMTL/kicad_custom_library`). Commit only inside it with `git -C Custom ...`. Never push, in Custom or in the parent. Never stage or commit the parent's `Custom` gitlink; the owner bumps it. Do not run `git submodule update`, `git -C Custom checkout/reset/stash`, or anything else that moves Custom's HEAD or discards work.
- Run sequentially on the main tree. Do not create a worktree, because the change is inside a submodule.
- Never run `kicad-cli fp upgrade` or `kicad-cli sym upgrade` in place. Output always goes to a temp dir (`-o <TemporaryDirectory>`). An in-place upgrade would rewrite the library version header, which the project forbids (STATE: the target library's version header is never changed).
- Edit KiCad files with exact text replacements that keep the existing layout: tab indentation, one S-expression token per line as already laid out, and CRLF line endings. The working tree is CRLF (`core.autocrlf=true`) and the index is LF. Every inserted line must end in CRLF like its neighbours, or the app's loader reports `fs.mixed_eol`. Files stay UTF-8 without a BOM.
- Do not touch any other symbol, footprint, library, or the 3D model folder. ATXK-H14 gets no 3D model; the owner will download one.

Planning-time facts (verified 2026-10-23):
- `Custom` is on branch `main`, the working tree is clean, and it is 1 commit ahead of `origin/main` (dd63768, unpushed).
- `kicad-cli` 10.0.7 is at `C:/Program Files/KiCad/10.0/bin/kicad-cli.exe`. `fp upgrade [--force] [-o OUTPUT_DIR] INPUT_FILE_OR_DIR` and `sym upgrade [--force] [-o OUTPUT_FILE_OR_DIR] INPUT_FILE_OR_DIR` exit 0 on success. On a file that does not parse, they print "Unable to load library" and exit 2. With `-o` to a temp dir, Custom stays clean. KiCad 10 re-emits the footprint as version 20260206 and the symbol as 20251024, with `(hide yes)` moved directly under each property.
- `grep -rln "ATX-14" Custom/` lists only `Footprints/Oscillator_TCXO_Abracon.pretty/ATX-14.kicad_mod` itself and `Symbols/Oscillator_TCXO_Abracon.kicad_sym`, whose Datasheet URL is the old ATX-14 PDF. `grep -rn "Oscillator_TCXO_Abracon:ATX-14" Custom/` finds nothing.
- `tests/test_naming_sanitize.py` lists "ATX-14" in a static name list for sanitiser stability only. It does not read the filesystem and needs no change.
- The current ATXK-H14 footprint has no pin-1 marker on F.SilkS or F.Fab. Its only graphic is the F.CrtYd `fp_rect` (±1.4 x ±1.1). F.SilkS carries only the Reference property; F.Fab carries Value/Datasheet/Description and the `${REFERENCE}` text.
- Test subset baseline at planning: `334 passed, 3 skipped` (the skips are WurthElektronik not checked out), 0 failed.

<interfaces>
App parser API the checker reuses (Qt-free; import after putting the repo root on sys.path):
- `kicad_lib_manager.kicad_files.load(path: Path) -> LoadedFile | Issue`: strict UTF-8 decode plus parse. `LoadedFile.source` is a `fsutil.SourceText` with `.text`, `.bom: bool`, `.eol: str`, `.mixed_eol: bool`, `.issues`. `LoadedFile.root` is a `sexpr.Node`.
- `kicad_lib_manager.kicad_files.parse_bytes(data: bytes, name: str) -> LoadedFile | Issue`
- `find_symbols(root) -> list[SymbolRef]`, `find_symbol(root, name) -> SymbolRef | None` (`.name`, `.node`)
- `find_property(node, name) -> PropertyRef | None` (`.value` already unquoted, `.node`). It works on any node's direct children, including a footprint node.
- `footprint_name(root) -> NameRef | None` (`.name`, `.node` = the top-level footprint list)
- `file_version(root) -> int | None`
- `kicad_lib_manager.sexpr.Node`: `.kind` is one of "root", "list", "str" or "atom"; also `.children: list[Node]`, `.text: str`, `.head` (first atom of a list, or None). `kicad_lib_manager.sexpr.unquote(token) -> str`.

Current footprint pad blocks (ATXK-H14.kicad_mod lines 80-103). Each pad is a `(pad "N" smd rect` line followed by an `(at X Y)` line:
pad "1" (at -0.725 -0.5) | pad "2" (at 0.725 -0.5) | pad "3" (at 0.725 0.5) | pad "4" (at -0.725 0.5), all (size 0.85 0.7).
Target: pad "1" (at -0.725 0.5) | pad "2" (at 0.725 0.5) | pad "3" (at 0.725 -0.5) | pad "4" (at -0.725 -0.5). Only the Y sign of each pad flips.

Current symbol lines to change (Oscillator_TCXO_Abracon.kicad_sym): line 39 Datasheet (ATX-14 PDF with tracking params), line 48 Description, line 57 ki_keywords, line 66 ki_fp_filters, line 105 pin 1 `(name "Ctrl"`. The hidden-property layout to copy is the ki_keywords block, lines 57-65: `(property "K" "V"`, then `(at 0 0 0)`, then `(effects (font (size 1.27 1.27)) (hide yes))`, one token per line, two-tab base indent.
</interfaces>
</context>

## Source Coverage Audit

| Source | Item | Covered by |
|--------|------|------------|
| GOAL | Footprint pads renumbered to the datasheet top view (1 BL, 2 BR, 3 TR, 4 TL), size 0.85x0.70 and pitch 1.45x1.00 kept | Task 1 |
| GOAL | Any pin-1 marker on silk/fab moved to pad 1 (none exists; confirmed and reported) | Task 1 |
| GOAL | Footprint Datasheet, Description, descr, tags filled | Task 1 |
| GOAL | Confirm no reference to Oscillator_TCXO_Abracon:ATX-14, then delete ATX-14.kicad_mod | Task 2 |
| GOAL | Symbol Datasheet, Description, ki_keywords, ki_fp_filters, hidden Manufacturer, pin 1 renamed to OE; Value and Footprint kept; no 3D model | Task 2 |
| GOAL | kicad-cli fp/sym upgrade into a scratch dir proves parsing; grep/python check of pads and properties | Tasks 1-3 (check_atxk_h14.py) |
| GOAL | Scanner tests before/after, report only whether failures change | Tasks 1 and 3 |
| GOAL | Commit inside Custom only, descriptive message, no push, no parent gitlink bump | Task 3 |
| REQ | INST-03 (name / Footprint field / ki_fp_filters consistency) | Tasks 1-2 |
| RESEARCH / CONTEXT | none (quick mode, no RESEARCH.md or CONTEXT.md) | n/a |

<tasks>

<task type="tracer">
  <name>Task 1: Baseline tests and checker, then fix ATXK-H14 footprint pads and metadata (proven by kicad-cli re-emit)</name>
  <files>.planning/quick/261023-ptg-fix-abracon-atxk-h14-tcxo-mirrored-footp/check_atxk_h14.py, Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod</files>
  <precondition>`git -C Custom status --porcelain` prints nothing, `git -C Custom branch --show-current` prints main, and `C:/Program Files/KiCad/10.0/bin/kicad-cli.exe` exists.</precondition>
  <behavior>
    - `check_atxk_h14.py footprint` exits 0 only when, in the source file and in kicad-cli's re-emitted copy, the footprint is named ATXK-H14 with exactly pads 1-4 at (-0.725,0.5), (0.725,0.5), (0.725,-0.5), (-0.725,-0.5) (tolerance 1e-6), each smd rect 0.85 x 0.7. It also needs Datasheet = https://abracon.com/datasheets/ATXK-H14.pdf, Description = descr = FP_TEXT, tags = FP_TAGS and Value = ATXK-H14. In the source file only, it also needs version 20241229, no mixed line endings and no BOM.
    - `check_atxk_h14.py symbol` and `check_atxk_h14.py all` (all = footprint + symbol + cleanup) exit 1 against today's files and name every mismatch.
    - kicad-cli missing gives exit 2 with a clear message (never a silent pass); a non-zero kicad-cli exit is a failure.
  </behavior>
  <action>
Step A, baseline (before any edit). Run the test subset command from this task's verify block and record the final summary line and every FAILED id (the planning-time result was 334 passed, 3 skipped, 0 failed). Also record the output of `git -C Custom rev-list --count origin/main..main` (1 at planning). Keep both for the SUMMARY; Task 3 compares against them.

Step B, write the checker `.planning/quick/261023-ptg-fix-abracon-atxk-h14-tcxo-mirrored-footp/check_atxk_h14.py` (stdlib plus the app's Qt-free parser; module docstring with usage; a `main()` guarded by `if __name__ == "__main__"`).
- The repo root is `Path(__file__).resolve().parents[3]`. Insert it at the front of sys.path, then import `load`, `parse_bytes`, `find_symbols`, `find_symbol`, `find_property`, `footprint_name` and `file_version` from `kicad_lib_manager.kicad_files`, and `unquote` from `kicad_lib_manager.sexpr`. Reuse this parser rather than regex-parsing S-expressions.
- Its single optional argument is the part: `footprint`, `symbol` or `all` (default `all`). `all` runs footprint, symbol and cleanup checks.
- Find kicad-cli from the `KICAD_CLI` env var, then `C:/Program Files/KiCad/10.0/bin/kicad-cli.exe` if that file exists, then `shutil.which("kicad-cli")`. If none is found, print a FAIL line and exit 2.
- Inside one `tempfile.TemporaryDirectory()`, run `fp upgrade --force -o <tmp>/Oscillator_TCXO_Abracon.pretty <repo>/Custom/Footprints/Oscillator_TCXO_Abracon.pretty`. For the symbol part, also run `sym upgrade --force -o <tmp>/Oscillator_TCXO_Abracon.kicad_sym <repo>/Custom/Symbols/Oscillator_TCXO_Abracon.kicad_sym`. Use subprocess with an argument list, capture_output, a 120 s timeout and no shell. A non-zero return code is a failure; print its stderr.
- Run every content check twice, once on `load(<source path>)` labelled "source" and once on `parse_bytes(<re-emitted bytes>)` labelled "kicad-cli". An Issue result (parse failure) is itself a failure.
- Module constants: FP_DATASHEET = SYM_DATASHEET = "https://abracon.com/datasheets/ATXK-H14.pdf"; FP_TEXT = "Abracon ATXK-H14 TCXO, 4-pad SMD 2.15x1.35x1.1mm, pads 0.85x0.70mm, pitch 1.45x1.00mm, pin 1 bottom-left (top view)"; FP_TAGS = "tcxo oscillator 32.768kHz abracon ATXK-H14"; PADS = {"1": (-0.725, 0.5), "2": (0.725, 0.5), "3": (0.725, -0.5), "4": (-0.725, -0.5)}; PAD_SIZE = (0.85, 0.7). The footprint wording is planner's discretion: plain ASCII, with descr equal to the Description property, following KiCad stock footprints that put the summary in descr.
- Symbol constants: SYM_DESCRIPTION uses `\u00b1` for the plus-minus sign and `\u00b0` for the degree sign, so the script stays ASCII. Its value is the owner's string "32.768kHz TCXO, CMOS output, ±5ppm -40..+85°C, 1.5-3.63V, 2.15x1.35mm". SYM_KEYWORDS = "tcxo oscillator 32.768kHz 32k rtc cmos abracon"; SYM_FP_FILTERS = "ATXK*H14*"; SYM_FOOTPRINT = "Oscillator_TCXO_Abracon:ATXK-H14"; PINS = {"1": "OE", "2": "GND", "3": "OUT", "4": "VDD"}.
- Footprint checks. `footprint_name(root).name` is "ATXK-H14". Among the footprint node's direct children with head "pad", the pad numbers (unquoted children[1]) are exactly 1, 2, 3 and 4. children[2] and children[3] are the atoms smd and rect. The "at" child's first two values match PADS within 1e-6, and the "size" child matches PAD_SIZE. Use `find_property` on the footprint node for Datasheet, Description and Value. The direct children with head "descr" and "tags" give unquoted children[1] equal to FP_TEXT and FP_TAGS. Source only: `file_version` is 20241229, `source.mixed_eol` is False and `source.bom` is False.
- Symbol checks. `find_symbols` returns exactly one symbol, named "ATXK-H14". Use `find_property` for Reference = "Y", Value = "ATXK-H14", Footprint = SYM_FOOTPRINT, Datasheet, Description, ki_keywords, ki_fp_filters and Manufacturer = "Abracon". Manufacturer is hidden: somewhere under its property node, at any depth, there is a list with head "hide" whose children[1] text is "yes". This works for both the KiCad 9 layout (hide inside effects) and the KiCad 10 layout (hide directly under the property). Walk the symbol node recursively for lists with head "pin". From each pin's direct "name" and "number" children, build number to name; the map must equal PINS exactly. Source only: version 20241209, not mixed EOL, no BOM.
- Cleanup checks (all only). The ATX-14 footprint file path does not exist. The re-emitted .pretty directory contains exactly one file, ATXK-H14.kicad_mod. Read every file under `<repo>/Custom` with suffix .kicad_sym, .kicad_mod, .kicad_sch or .kicad_pcb as bytes, skipping any `.git` path. None may contain the old family name: build that literal in the script as "ATX" + "-14", so a later grep for it does not match the checker.
- Output: print `OK <part>/<label>` for each clean target and `FAIL <part>/<label>: <what> expected <x> got <y>` for each mismatch. Exit 1 if any FAIL, otherwise 0.
Run `check_atxk_h14.py all` now and confirm it exits 1 (red). Expected failures: pads mirrored, empty footprint properties, missing descr/tags, symbol values, pin name, the cleanup file still present. Note this in the SUMMARY.

Step C, fix the footprint `Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod` with exact text edits:
- Pads: for each pad, replace its two-line pair (the `(pad "N" smd rect` line and the `(at X Y)` line directly below it) as one unit, so the anchor is unique. Change only the Y sign: pad 1 to `(at -0.725 0.5)`, pad 2 to `(at 0.725 0.5)`, pad 3 to `(at 0.725 -0.5)`, pad 4 to `(at -0.725 -0.5)`. Keep pad order 1-4 in the file, and keep each pad's size, layers and uuid unchanged.
- Set the Datasheet property value (currently empty) to FP_DATASHEET and the Description property value (currently empty) to FP_TEXT. Keep their at/layer/hide/uuid/effects lines.
- Insert two top-level lines directly after the one-tab `(layer "F.Cu")` line and before `(property "Reference"`, each with one tab indent and a CRLF ending: `(descr "<FP_TEXT>")` and `(tags "<FP_TAGS>")`. This is where KiCad's stock footprints place them.
- Pin-1 marker: none exists on F.SilkS or F.Fab (planning-time fact), so there is nothing to move. Add no graphics; adding one was not requested. Record in the SUMMARY that the footprint has no pin-1 indicator, as an open item for the owner.
- Do not change the version/generator header, Reference/Value text positions, the `${REFERENCE}` text or the courtyard.
  </action>
  <verify>
    <automated>./env/Scripts/python.exe .planning/quick/261023-ptg-fix-abracon-atxk-h14-tcxo-mirrored-footp/check_atxk_h14.py footprint</automated>
    <automated>git -C Custom status --porcelain   # prints exactly one line: " M Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod"</automated>
    <automated>./env/Scripts/python.exe -m pytest tests/test_scanner_issues.py tests/test_scanner_skip_dirs.py tests/test_naming_sanitize.py tests/test_roundtrip_corpus.py tests/test_sexpr.py tests/test_kicad_files.py -q --tb=no -p no:cacheprovider -rf   # run once in Step A before any edit (baseline: record summary + FAILED ids), and again here after Step C; the FAILED set must equal the baseline</automated>
  </verify>
  <done>Baseline test result and the Custom ahead-count are recorded. The checker exists, `all` was red before the edit, and `footprint` now exits 0 on both the source and kicad-cli's re-emitted copy. The only Custom change is ATXK-H14.kicad_mod.</done>
</task>

<task type="auto">
  <name>Task 2: Delete unused ATX-14 footprint after a reference check, and correct the ATXK-H14 symbol</name>
  <files>Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATX-14.kicad_mod, Custom/Symbols/Oscillator_TCXO_Abracon.kicad_sym</files>
  <precondition>Task 1 done: `check_atxk_h14.py footprint` exits 0.</precondition>
  <action>
Step A, reference check before deleting. Run `grep -rn "Oscillator_TCXO_Abracon:ATX-14" Custom/`; it must print nothing. Also run `grep -rln "ATX-14" Custom/`; it must list only the ATX-14 footprint file itself and `Custom/Symbols/Oscillator_TCXO_Abracon.kicad_sym` (the old Datasheet URL, fixed below). If any other file shows up, stop: do not delete. Report it as a blocker with the matching paths. Paste both command outputs into the SUMMARY.

Step B, delete with `git -C Custom rm -- Footprints/Oscillator_TCXO_Abracon.pretty/ATX-14.kicad_mod`. This stages the deletion in the submodule and touches nothing in the parent.

Step C, edit `Custom/Symbols/Oscillator_TCXO_Abracon.kicad_sym` with exact single-line replacements, keeping each line's two-tab indent and CRLF:
- The Datasheet property value (line 39, the long ATX-14 URL with tracking parameters) becomes exactly `https://abracon.com/datasheets/ATXK-H14.pdf`.
- The Description property value (line 48) becomes exactly `32.768kHz TCXO, CMOS output, ±5ppm -40..+85°C, 1.5-3.63V, 2.15x1.35mm`. The plus-minus and degree signs are real UTF-8 characters (U+00B1, U+00B0), not escapes, and the file stays UTF-8 without a BOM.
- The ki_keywords value (line 57) becomes `tcxo oscillator 32.768kHz 32k rtc cmos abracon`.
- The ki_fp_filters value (line 66) becomes `ATXK*H14*`.
- Insert a hidden Manufacturer property with value `Abracon` after the Description property block and directly before the `(property "ki_keywords"` line. Copy the ki_keywords block's exact layout: the property line, `(at 0 0 0)`, then effects, font, size 1.27 1.27, the font close, `(hide yes)`, the effects close and the property close, one token per line. Use the same tab depths and CRLF endings as that block. This placement follows KiCad's save order: user fields after Description, before ki_keywords.
- Pin 1's `(name` line (line 105, inside `ATXK-H14_1_1`) gets the value `OE` in place of the current placeholder. Keep the pin type `input`, its position and its number `1`.
- Leave Reference "Y", Value "ATXK-H14", Footprint "Oscillator_TCXO_Abracon:ATXK-H14" and every graphic and other pin unchanged. Library renaming is a separate future phase. Add no 3D model.
  </action>
  <verify>
    <automated>./env/Scripts/python.exe .planning/quick/261023-ptg-fix-abracon-atxk-h14-tcxo-mirrored-footp/check_atxk_h14.py all</automated>
    <automated>git -C Custom status --porcelain   # prints exactly 3 lines: " M Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod", "D  Footprints/Oscillator_TCXO_Abracon.pretty/ATX-14.kicad_mod", " M Symbols/Oscillator_TCXO_Abracon.kicad_sym"</automated>
    <automated>git -C Custom diff --stat -- Symbols/Oscillator_TCXO_Abracon.kicad_sym   # 1 file changed, about 14 insertions and 5 deletions (4 value lines + 1 pin name replaced, 9 Manufacturer lines added)</automated>
  </verify>
  <done>The reference check outputs are recorded and showed no symbol link to the ATX-14 footprint. ATX-14.kicad_mod is deleted (staged in Custom). The symbol carries the owner's exact values, a hidden Manufacturer "Abracon" and pin 1 OE. `check_atxk_h14.py all` exits 0 on the source files and on kicad-cli's re-emitted copies.</done>
</task>

<task type="auto">
  <name>Task 3: Re-run tests against the baseline and commit inside Custom only (no push, no gitlink bump)</name>
  <files>Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod, Custom/Footprints/Oscillator_TCXO_Abracon.pretty/ATX-14.kicad_mod, Custom/Symbols/Oscillator_TCXO_Abracon.kicad_sym</files>
  <precondition>Task 2 done: `check_atxk_h14.py all` exits 0 and `git -C Custom status --porcelain` shows exactly the three expected entries.</precondition>
  <action>
Step A, tests. Re-run the same test subset command used for the Task 1 baseline. Compare the set of FAILED ids with the baseline. The passed count may drop slightly, because per-file corpus cases for the deleted footprint disappear; that is expected and not a regression. Report only whether the failure set changed: "unchanged (N failures before, N after)" or the exact added and removed ids. If a new failure names an Oscillator_TCXO_Abracon file, stop and fix the KiCad text before committing. A mixed line ending or a parse problem from the edits would show up here.

Step B, commit inside the submodule only:
- Stage the two edited files explicitly with `git -C Custom add -- Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod Symbols/Oscillator_TCXO_Abracon.kicad_sym`. The deletion is already staged from Task 2. Never use `add -A` or `add .`.
- Write the message to a file in your session scratch/temp directory (never inside the repo), then commit with `git -C Custom commit -F <that file>`. Let any owner hooks run; do not bypass them.
- Subject: `Oscillator_TCXO_Abracon: fix ATXK-H14 mirrored pads and symbol data, drop ATX-14`.
- Body, one bullet each:
  - Footprint ATXK-H14 pads renumbered to the datasheet top view (pin 1 bottom-left, 2 bottom-right, 3 top-right, 4 top-left). They were laid out from the bottom view. Pad size 0.85x0.70 and pitch 1.45x1.00 are unchanged; Datasheet, Description, descr and tags are filled.
  - Symbol ATXK-H14: the datasheet points to ATXK-H14.pdf (it was the ATX-14 PDF with tracking parameters). Description, keywords and ki_fp_filters ATXK*H14* are updated, a hidden Manufacturer Abracon is added, and pin 1 is renamed OE.
  - Unused ATX-14 footprint removed (different family, also mirrored, not referenced).
  - Source: Abracon ATXK-H14 datasheet rev 09-05-25, p.3.
  - End the body with the commit-attribution trailer your session is configured with.
- Do not push. In the parent repo, do not `git add Custom` and do not commit. The parent will show `M Custom` (new commits); leave it for the owner. The orchestrator's planning-docs commit must stage only `.planning/` paths.

Step C, record in the SUMMARY: the Custom commit hash and subject, the test comparison line, the reference-check outputs from Task 2, and the open item "ATXK-H14 footprint has no pin-1 marker on silkscreen or fab; none existed to move". Also remind the owner to push Custom main (now 2 ahead of origin/main counting dd63768) and to bump the parent gitlink when ready.
  </action>
  <verify>
    <automated>git -C Custom show --name-status --format= HEAD   # prints exactly: "M Footprints/Oscillator_TCXO_Abracon.pretty/ATXK-H14.kicad_mod", "D Footprints/Oscillator_TCXO_Abracon.pretty/ATX-14.kicad_mod", "M Symbols/Oscillator_TCXO_Abracon.kicad_sym" (tab-separated)</automated>
    <automated>git -C Custom status --porcelain   # prints nothing</automated>
    <automated>git -C Custom rev-list --count origin/main..main   # prints Task 1's recorded count + 1 (2 at planning time); proves nothing was pushed</automated>
    <automated>git diff --cached --name-only -- Custom   # prints nothing: the parent gitlink is not staged</automated>
    <automated>./env/Scripts/python.exe .planning/quick/261023-ptg-fix-abracon-atxk-h14-tcxo-mirrored-footp/check_atxk_h14.py all</automated>
    <automated>./env/Scripts/python.exe -m pytest tests/test_scanner_issues.py tests/test_scanner_skip_dirs.py tests/test_naming_sanitize.py tests/test_roundtrip_corpus.py tests/test_sexpr.py tests/test_kicad_files.py -q --tb=no -p no:cacheprovider -rf   # FAILED set equals the Task 1 baseline</automated>
    <human-check>The owner opens Oscillator_TCXO_Abracon:ATXK-H14 in the KiCad Footprint Editor and compares it with datasheet rev 09-05-25, p.3 top view: pad 1 bottom-left, 2 bottom-right, 3 top-right, 4 top-left. They decide whether to add a pin-1 silkscreen/fab marker. They also open the ATXK-H14 symbol and confirm pin 1 reads OE.</human-check>
  </verify>
  <done>A single new local commit on Custom main contains exactly the three paths, with a descriptive message. Custom's working tree is clean, nothing is pushed, and the parent gitlink is untouched. The checker passes post-commit, and the test failure set is unchanged versus baseline (reported in the SUMMARY).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Datasheet to KiCad files | Owner-transcribed datasheet facts (rev 09-05-25 p.3) become pad coordinates and pin names; a transcription error ships to a PCB |
| Executor to Custom submodule git | Local commit in a separately published repo; the push and the parent gitlink are owner-only |
| kicad-cli to repo files | An external binary reads library files; a misuse (in place) would rewrite them |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261023-ptg-01 | Tampering | ATXK-H14.kicad_mod pad coordinates | high | mitigate | check_atxk_h14.py asserts the exact top-view coordinates and pad size on the source and on kicad-cli's re-emitted text (Task 1). The owner's human-check compares against datasheet p.3 (Task 3). |
| T-261023-ptg-02 | Tampering | kicad-cli upgrade run against Custom | high | mitigate | The checker always passes `-o` to a TemporaryDirectory. Source-only assertions require version 20241229/20241209, so an in-place upgrade would fail the check. `git -C Custom status --porcelain` gates each task. |
| T-261023-ptg-03 | Tampering | Commit scope (Custom commit, parent gitlink, push) | high | mitigate | Explicit-path `git -C Custom add` and `rm`. `show --name-status HEAD` must list exactly 3 paths. `rev-list --count origin/main..main` = baseline + 1 proves no push. `git diff --cached -- Custom` in the parent must be empty (Task 3). |
| T-261023-ptg-04 | Denial of Service | Deleting ATX-14.kicad_mod | medium | mitigate | A grep reference check runs before `git rm`, with a stop-and-report rule if anything links to it. The checker's cleanup part asserts no Custom KiCad file mentions the old name (Task 2). |
| T-261023-ptg-05 | Information Disclosure | Datasheet URL with gclid/_gl tracking parameters | low | mitigate | Replaced by the clean https://abracon.com/datasheets/ATXK-H14.pdf, with an exact-value check in the checker (Task 2) |
| T-261023-ptg-06 | Tampering | Line endings / encoding of edited files | low | mitigate | The checker asserts no mixed EOL and no BOM through the app's own `load()`. The corpus round-trip tests re-run in Task 3. |
| T-261023-ptg-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs (stdlib plus the existing app parser only) |
</threat_model>

<verification>
- `./env/Scripts/python.exe .planning/quick/261023-ptg-fix-abracon-atxk-h14-tcxo-mirrored-footp/check_atxk_h14.py all` exits 0. kicad-cli 10 parses both files (into a temp dir), and pads, properties, pins and cleanup match on the source and on KiCad's re-emitted text.
- `git -C Custom show --name-status --format= HEAD` lists exactly the three Custom paths. `git -C Custom status --porcelain` is empty. The ahead count is the baseline + 1. `git diff --cached --name-only -- Custom` is empty in the parent.
- The test subset failure set equals the Task 1 baseline (planning time: 0 failures).
</verification>

<success_criteria>
- ATXK-H14 footprint pads follow the datasheet top view (1 BL, 2 BR, 3 TR, 4 TL), with size 0.85x0.70 and pitch 1.45x1.00 kept and Datasheet/Description/descr/tags filled.
- ATX-14.kicad_mod is deleted after a recorded reference check showing nothing used it.
- The ATXK-H14 symbol has the owner's exact Datasheet, Description, ki_keywords, ki_fp_filters, a hidden Manufacturer Abracon and pin 1 OE. Value and Footprint are unchanged and there is no 3D model.
- One local commit exists inside Custom; nothing is pushed and the parent gitlink is not bumped.
- The SUMMARY reports the test failure comparison, the commit hash, and the open item that the footprint has no pin-1 marker.
</success_criteria>

<output>
Create `.planning/quick/261023-ptg-fix-abracon-atxk-h14-tcxo-mirrored-footp/261023-ptg-SUMMARY.md` when done
</output>
