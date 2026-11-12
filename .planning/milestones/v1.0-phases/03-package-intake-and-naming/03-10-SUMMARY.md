---
phase: 03-package-intake-and-naming
plan: 10
subsystem: intake
tags: [sexpr, regex, denial-of-service, tracemalloc, cr-03, gap-closure]

requires:
  - phase: 03-package-intake-and-naming
    provides: "03-08 text caps (MAX_KICAD_TEXT_BYTES, MAX_KICAD_TEXT_NODES, max_nodes) and tests/test_locate_text_caps.py; 03-09 staging fixes"
provides:
  - "Linear string-end scan sexpr._string_end over a bounded _STRING_WINDOW regex window, one code path on every Python"
  - "Linear unquote with a lone-surrogate placeholder chain and an exact regex fallback"
  - "string_body and traced_peak test helpers; reference-oracle differential tests for parse and unquote"
  - "T-03-35 re-closed and CR-03 marked fixed (re-review pending)"
affects: [phase-04-import-write, phase-05-gui, secure-phase]

actuals:
  tokens: 10500
  tasks: 3
  commits: 6

plan_head_before: 4744a7de66e057a47632fd69b2a121f0dfa67cb6
plan_head_after: a38c4785df7f597d4a9ff1627a9c0bcc4f64b121

tech-stack:
  added: []
  patterns:
    - "Bound the repeat count of a regex group to bound its backtracking state, then loop over windows"
    - "Memory contracts measured as an integer tracemalloc peak against k * sys.getsizeof(decoded text); a 64 KiB fail-fast probe guards every full-size case"
    - "Reference oracle copied from the plan base into the tests, importing nothing from the code under test"

key-files:
  created: []
  modified:
    - kicad_lib_manager/sexpr.py
    - tests/zipfixtures.py
    - tests/test_zipfixtures.py
    - tests/test_sexpr.py
    - tests/test_locate_text_caps.py
    - .planning/phases/03-package-intake-and-naming/03-SECURITY.md
    - .planning/phases/03-package-intake-and-naming/03-REVIEW-DISPOSITION.md

key-decisions:
  - "String ends are found by _string_end over _STRING_BODY (at most 1024 escape pairs per regex call), not by a possessive or atomic pattern: those are Python 3.11+ syntax and the floor stays 3.10"
  - "parse moved from finditer to an explicit offset loop over _TOKEN.match so a string scanned outside the regex can be jumped over; the bad group is kept so every position still matches"
  - "unquote made linear with replace passes through a U+D800 placeholder; a body already holding the placeholder takes the old regex path, so the result is exact for any str"
  - "Nothing outside sexpr.py changed: kicad_files.py, importer/ and the D-06 caps are untouched (diff check against the plan base is clean)"

patterns-established:
  - "Fail-fast probes (_require_linear_tokenizer, _require_linear_unquote) run before any 8 MiB case is built"
  - "Contract pins that pass at once are recorded as pins, not RED evidence"

requirements-completed: [INTK-06, INTK-01]

coverage:
  - id: D1
    description: "A one-string 8 MiB .kicad_sym (plain, escape-dense, mixed; as Description or property name; in a zip or a picked folder; with astral text) is located with its Description read back exactly, within 10x the decoded text size, no ERROR and no intake.unreadable_file Issue"
    requirement: "INTK-06"
    verification:
      - kind: integration
        ref: "tests/test_locate_text_caps.py#test_string_heavy_symbol_at_byte_cap_is_read_with_bounded_memory"
        status: pass
      - kind: integration
        ref: "tests/test_locate_text_caps.py#test_string_heavy_escape_classes_at_byte_cap"
        status: pass
      - kind: integration
        ref: "tests/test_locate_text_caps.py#test_string_heavy_property_name_at_byte_cap"
        status: pass
      - kind: integration
        ref: "tests/test_locate_text_caps.py#test_string_heavy_astral_text_bound_is_in_storage_bytes"
        status: pass
    human_judgment: false
  - id: D2
    description: "Folder intake, which has no ratio rule, is bounded the same way and leaves the picked folder byte-identical"
    requirement: "INTK-01"
    verification:
      - kind: integration
        ref: "tests/test_locate_text_caps.py#test_string_heavy_folder_at_byte_cap"
        status: pass
    human_judgment: false
  - id: D3
    description: "Tokenizer and unquote are linear on one long string (parse k=3, unquote k=6 at 512 KiB per class) and unterminated strings still raise sexpr.unterminated at the opening quote"
    requirement: "INTK-06"
    verification:
      - kind: unit
        ref: "tests/test_sexpr.py#test_one_string_token_parse_memory_is_linear"
        status: pass
      - kind: unit
        ref: "tests/test_sexpr.py#test_unterminated_long_string_memory_is_linear"
        status: pass
      - kind: unit
        ref: "tests/test_sexpr.py#test_unquote_memory_is_linear"
        status: pass
    human_judgment: false
  - id: D4
    description: "Token boundaries, parse errors and unquote results are unchanged for every input, including window edges, the byte-cap boundary and the Python 3.10 syntax floor"
    requirement: "INTK-06"
    verification:
      - kind: unit
        ref: "tests/test_sexpr.py#test_tokenizer_matches_reference_parser"
        status: pass
      - kind: unit
        ref: "tests/test_sexpr.py#test_unquote_matches_reference"
        status: pass
      - kind: unit
        ref: "tests/test_sexpr.py#test_string_window_boundaries"
        status: pass
      - kind: unit
        ref: "tests/test_sexpr.py#test_sexpr_patterns_have_no_python_3_11_syntax"
        status: pass
      - kind: integration
        ref: "tests/test_locate_text_caps.py#test_string_heavy_byte_cap_boundary"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-10-19
status: complete
---

# Phase 3 Plan 10: CR-03 Linear String Scan Summary

**Linear bounded-window string scan (`sexpr._string_end`) and a linear `unquote`, so one 8 MiB quoted string costs about 5 times its decoded size instead of 2.8 GiB, with token boundaries and decoded values proven identical to the pre-03-10 code.**

## Performance

- **Duration:** about 10 min
- **Started:** 2026-10-19T19:21:44Z
- **Completed:** 2026-10-19T19:31:12Z
- **Tasks:** 3 (Task 1 tracer, Tasks 2 and 3 auto, all tdd)
- **Files modified:** 7 (3 test modules, 1 test helper module, `sexpr.py`, 2 planning documents)

## Accomplishments

- `sexpr._string_end` finds a string's closing quote by matching `_STRING_BODY` (at most 1024 escape pairs per regex call) in a loop. The regex engine's backtrack state is bounded per call, so memory no longer grows per character. One code path on every Python, no possessive repeat, no atomic group, no version check.
- `parse` now walks `_TOKEN.match` offsets; the `quote` group hands the opening offset to `_string_end`. An unterminated string still raises `sexpr.unterminated` at the opening quote, before the node ceiling is checked.
- `unquote` is linear: escaped-backslash pairs become U+D800, then `\"`, `\n`, `\r`, `\t` are replaced, then the placeholder becomes one backslash. A body already holding U+D800 (never produced by strict UTF-8 decoding) takes the old regex path.
- End-to-end (8 MiB, `open_package` plus `detect_candidate`, measured here with tracemalloc):

  | Case | Peak, multiple of decoded storage | Time |
  |---|---|---|
  | plain, zip | x5.02 | 0.16 s |
  | escape-dense, zip | x5.02 | 0.27 s |
  | mixed, zip | x5.02 | 0.23 s |
  | escape-dense property name, zip | x4.02 | 0.62 s |
  | astral plus escape-dense, zip | x3.50 of 4-byte storage (33,554,480 bytes) | 0.34 s |

  The test bound is 10x. Folder, byte-cap minus one and byte-cap plus one are covered by tests (the plus-one file is skipped with exactly one WARNING and never reaches the parser).
- T-03-35 is re-closed, T-03-15 annotated, an audit-trail row added; CR-03 is `fixed` (re-review pending) and `open:` is 11.

## Task Commits

1. **Task 1 (tracer): one 8 MiB string end to end, plain class**
   - RED: `1ac2094` (test)
   - GREEN: `3a8942f` (feat)
2. **Task 2: linear unquote, escape-dense and mixed strings end to end**
   - RED: `b8d199d` (test)
   - GREEN: `289abaf` (feat)
3. **Task 3: behaviour pins, window and byte-cap boundaries, 3.10 syntax guard, CR-03 bookkeeping**
   - Pins: `0f5a3e5` (test)
   - Bookkeeping: `a38c478` (docs, after the full suite was green)

**Plan metadata:** the SUMMARY commit follows this file.

## RED Evidence

Semantic assessment: each failing test failed on its planned memory assertion for the intended reason (the old pattern or the old callback), not on a syntax, import or fixture fault. No `gsd_run check tdd-red-evidence` record was produced; the evidence is the pytest assertion output below.

**Task 1 (old tokenizer, 512 KiB token, k=3 allows 1.5 MB):**

| Class | parse peak | multiple | unterminated peak |
|---|---|---|---|
| plain | 122,542,926 | x234 | 122,018,947 |
| escape | 62,996,266 | x120 | 62,472,447 |
| mixed | 78,615,016 | x150 | 78,091,197 |
| special | 62,996,266 | x120 | 62,472,447 |

The 8 MiB plain end-to-end case failed at `_require_linear_tokenizer` (64 KiB probe), so no 8 MiB case was ever run against the old tokenizer.

**Task 2 (old unquote, 512 KiB token, k=6 allows 3.1 MB):** escape 14,633,266 bytes (x27.9), mixed 11,490,188 (x21.9). Every full-size escaped case failed at `_require_linear_unquote` (peak 1,817,458 bytes for a 65,579 byte probe token).

**Pass-both guards** (passed before and after the change): `test_unquote_memory_is_linear[plain]` and `[special]`. These pin that the plain and special classes stay linear.

**Contract pins** (passed at once, not RED evidence, as plans 03-04 and 03-07 recorded): `test_unquote_matches_reference`, `test_unquote_placeholder_path_matches_reference`, `test_unquote_placeholder_never_comes_from_file_text`, and every Task 3 test (`test_tokenizer_matches_reference_parser`, `test_string_window_boundaries`, `test_string_token_edge_cases`, `test_empty_and_lone_quote_tokens`, `test_unterminated_string_is_reported_before_the_node_ceiling`, `test_sexpr_patterns_have_no_python_3_11_syntax`, `test_long_atom_and_whitespace_runs_parse_linearly`, `test_string_heavy_byte_cap_boundary`).

## Tracer Gate

Task 1 `<verify>` carries only `<automated>`, `human_verify_mode` is `end-of-phase` and auto mode is off. The verify command was re-run after the GREEN commit and passed (240 passed, 6 skipped), logged "Tracer verified end-to-end - expanding".

## Parse-Path Audit Record

Planning numbers re-measured or pinned:

- atom and whitespace patterns are single-character-class repeats: pinned by `test_long_atom_and_whitespace_runs_parse_linearly` (512 KiB, at most 3x).
- `_STRING_BODY` is bounded by `_STRING_WINDOW`.
- `_ESCAPE_RE` is reached only through the lone-surrogate fallback.
- `decode_source` uses `str.count` only.
- The regexes in `importer/suggest.py` and `importer/naming.py` are single-character-class repeats over values Phase 4/5 pass in and are not on the `open_package` / `detect_candidate` path. `naming._clean` does linear per-character work and was not changed.

## Files Created/Modified

- `kicad_lib_manager/sexpr.py` - `_STRING_WINDOW`, `_STRING_BODY`, `_string_end`, `quote` token group, offset loop in `parse`, linear `unquote`, `_BACKSLASH_PLACEHOLDER`, `_PAIR_ESCAPES`
- `tests/zipfixtures.py` - `STRING_KINDS`, `string_body`, `traced_peak`
- `tests/test_zipfixtures.py` - self-tests for both
- `tests/test_sexpr.py` - per-class memory bounds, `_reference_unquote` and `_reference_parse` oracles, differential, window, edge, syntax-guard and audit tests
- `tests/test_locate_text_caps.py` - `_string_symbol`, `_open_and_detect`, both probes, `_measure`, seven string-heavy end-to-end tests
- `.planning/phases/03-package-intake-and-naming/03-SECURITY.md`, `03-REVIEW-DISPOSITION.md` - CR-03 bookkeeping

## Decisions Made

See `key-decisions` in the frontmatter. No decision departs from the plan.

## Deviations from Plan

### Auto-fixed Issues

None - no defect surfaced in Task 1 or Task 2 code, so Task 3 changed no shipped code.

### Structural differences from the plan text (no behaviour or coverage lost)

**1. Custom-corpus check split into its own test**
- **Found during:** Task 3
- **Issue:** The plan puts the `Custom/` files inside `test_tokenizer_matches_reference_parser`, which would then skip as a whole where `Custom/` is absent (this worktree), hiding the 22,000-text fuzz comparison.
- **Fix:** The comparison test always runs the generated texts, `_symbol_library(300)`, both UL members and any `Custom/` file that exists. A sibling `test_reference_corpus_includes_the_custom_library_files` skips with a reason when `Custom/` holds no file and otherwise asserts a symbol library is in the corpus.
- **Consequence:** `-k "reference_parser"` does not select the skipping test, so the plan's "no skipped test" acceptance reading is satisfied by name here. The orchestrator's `Custom/` checkout will run both.

**2. `test_long_atom_and_whitespace_runs_parse_linearly` is parametrized (two cases) instead of one test with two inputs.** Same assertions.

### Precondition note (Task 3)

Task 3's `<precondition>` ("the Custom submodule is checked out") is unmet in this worktree. The orchestrator's environment notes state that the submodules are intentionally not checked out here, that dependent tests skip, and that the orchestrator re-runs the suite in its own checkout. I proceeded on that basis and compensated with a read-only run (scratchpad script, not committed) of the new `parse` and `unquote` against the reference copies over the 24 `.kicad_sym` and `.kicad_mod` files of the orchestrator checkout's `Custom/`: 0 mismatches. Strings in those files were all compared with `unquote` too.

**Total deviations:** 0 auto-fixed, 2 structural test-layout notes, 1 precondition note.
**Impact on plan:** none on behaviour or coverage.

## Issues Encountered

- The sandbox rejected compound git commands and heredocs; commands were split into single calls and files written with the editor tools. No effect on the result.

## Skipped Tests In This Worktree (14)

Full suite in the worktree: `867 passed, 14 skipped`. The skips are all environmental and expected to run in the orchestrator checkout:

- `Custom/` not checked out (10): `test_edits.py:106,179`, `test_kicad_files.py:365,380`, `test_locate_text_caps.py:341`, `test_naming_sanitize.py:191`, `test_naming_suggest.py:420`, `test_roundtrip_corpus.py:106`, `test_scanner_issues.py:271`, plus the new `test_sexpr.py:680` (`test_reference_corpus_includes_the_custom_library_files`).
- WurthElektronik not checked out (3): `test_roundtrip_corpus.py:229,244`, `test_scanner_issues.py:284`.
- Symlink privilege missing on this account (1): `test_package_folder.py:105` (WinError 1314).

## Verification Results

- `pytest -q -rs`: 867 passed, 14 skipped (environmental, above).
- Plan acceptance greps and counts all pass: `_string_end`, `_STRING_WINDOW = 1024`, `(?P<quote>")`, 0 `version_info`, `_PAIR_ESCAPES`, 8 + 4 + 10 + 6 + 7 targeted test counts, 35 passed for the Task 3 `-k` group.
- `git diff` against the plan base for `kicad_files.py`, `importer/`, `test_roundtrip_corpus.py`, `test_adapters.py`, `test_package_zip.py`: empty.
- Commits stage explicit paths only; none of `.planning/config.json`, `state.json`, `milestone.lock`, `reports/`, `research_notes/` appears in the plan's commits.
- `STATE.md`, `ROADMAP.md` and `REQUIREMENTS.md` were not edited (the orchestrator owns them after the wave).

## Known Stubs

None.

## Threat Flags

None. T-03-42 to T-03-45 from the plan's threat model are mitigated by this plan's tests and await `/gsd-secure-phase` to enter the register.

## Next Phase Readiness

- Phase 3 gap truth 7 (03-VERIFICATION.md) can be re-verified; CR-03 awaits re-review.
- Phase 4 reads candidates through this parser, so the fix is in place before it starts.
- Remaining open review findings (WR-01 to WR-05, IN-01 to IN-06) are untouched, as the plan requires.

## Self-Check: PASSED

- Files exist: `kicad_lib_manager/sexpr.py`, `tests/zipfixtures.py`, `tests/test_zipfixtures.py`, `tests/test_sexpr.py`, `tests/test_locate_text_caps.py`, `03-SECURITY.md`, `03-REVIEW-DISPOSITION.md`.
- Commits exist on the branch: `1ac2094`, `3a8942f`, `b8d199d`, `289abaf`, `0f5a3e5`, `a38c478`.

---
*Phase: 03-package-intake-and-naming*
*Completed: 2026-10-19*
