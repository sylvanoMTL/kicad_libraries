---
phase: 01-foundation
plan: 01
subsystem: testing
tags: [sexpr, atomic-write, pytest, pytest-qt, pyside6, kicad]

requires: []
provides:
  - "Severity (str, Enum) and frozen Issue(severity, code, text) in models.py"
  - "sexpr.py: lossless span tokenizer, Node, Edit, apply_edits, quote, unquote, SexprError"
  - "fsutil.py: SourceText, decode_source, read_source, encode_source, atomic_write_bytes"
  - "kicad_files.py: find_symbols, find_property read-side locators with spans"
  - "Pinned requirements.txt / requirements-dev.txt and pytest config (pyproject.toml, conftest.py)"
  - "Offscreen D-15 LibraryTableWidget sync tests"
  - ".gitattributes (tests/fixtures/** -text) and tracked Ultra Librarian sample zip"
affects: [01-02, 01-03, 01-04, phase-02, phase-03, phase-04]

actuals:
  tokens: 5250
  tasks: 3
  commits: 3

tech-stack:
  added: [pytest==9.1.1, pytest-qt==4.5.0]
  patterns:
    - "Parse for navigation, splice for mutation (Edit/apply_edits, no re-serialisation)"
    - "Expected failures returned as Issue values; programmer errors raise ValueError"
    - "Bytes-only KiCad file I/O with BOM and EOL carried beside the text"

key-files:
  created:
    - kicad_lib_manager/sexpr.py
    - kicad_lib_manager/fsutil.py
    - kicad_lib_manager/kicad_files.py
    - tests/test_edits.py
    - tests/conftest.py
    - tests/test_manifests.py
    - tests/test_library_table_widget.py
    - requirements.txt
    - requirements-dev.txt
    - pyproject.toml
    - .gitattributes
    - downloaded_examples/ul_CSD85301Q2.zip
  modified:
    - kicad_lib_manager/models.py

key-decisions:
  - "unterminated strings are reported by the tokenizer's bad group at the opening quote (sexpr.unterminated)"
  - "atomic_write_bytes is the minimal D-05 core (no read-only pre-check, no retry yet); Plan 02 adds both as keyword-only parameters"
  - "Real-Custom tracer test locates the file via Path(__file__) so it does not depend on conftest"

patterns-established:
  - "Tracer-first: one path through every new layer before expansion"
  - "Private widget access isolated in _sym_item/_fp_item test helpers"

requirements-completed: [FOUND-01, FOUND-02, FOUND-04]

plan_head_before: 92834260b397b91ca6bd644b09405ef613ad4e97
plan_head_after: aad89739b49859aeb44493df61a16abd85f2ec73
commits: 3

coverage:
  - id: D1
    description: "One property-value edit in a CRLF .kicad_sym flows through read_source, parse, find_property, apply_edits, encode_source and atomic_write_bytes, changing only its span"
    requirement: FOUND-04
    verification:
      - kind: unit
        ref: "tests/test_edits.py#test_tracer_value_edit_generated_crlf"
        status: pass
    human_judgment: false
  - id: D2
    description: "Same edit on the real Custom/Symbols/Connector_USB_GCT.kicad_sym leaves the repo file untouched"
    requirement: FOUND-04
    verification:
      - kind: unit
        ref: "tests/test_edits.py#test_tracer_value_edit_real_custom_symbol (skipped in this worktree: Custom/ not checked out; verified by ad hoc run against the orchestrator checkout's file)"
        status: unknown
    human_judgment: true
    rationale: "Test skips in the isolated worktree; orchestrator must re-run the suite after merge with Custom/ present"
  - id: D3
    description: "Exact pins installed and bare pytest imports the package with strict markers"
    requirement: FOUND-01
    verification:
      - kind: unit
        ref: "tests/test_manifests.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "LibraryTableWidget per-source symbol-to-footprint sync pinned offscreen"
    requirement: FOUND-02
    verification:
      - kind: unit
        ref: "tests/test_library_table_widget.py"
        status: pass
    human_judgment: false

duration: 4 min
completed: 2026-10-18
status: complete
---

# Phase 1 Plan 01: Tracer Edit Path and Test Harness Summary

**Lossless S-expression span-splice layer, byte-exact decode/atomic-write, and Issue/Severity model proven end to end on a CRLF KiCad symbol edit, with pinned PySide6/pytest/pytest-qt and an offscreen widget test**

## Performance

- **Duration:** 4 min
- **Started:** 2026-10-18T14:38:14Z
- **Completed:** 2026-10-18T14:41:57Z
- **Tasks:** 3
- **Files modified:** 13 (12 created, 1 modified)

## Accomplishments

- Tracer: editing one `Value` in a CRLF `.kicad_sym` changes only that value's bytes. CRLF count, bare-LF count and every other byte are unchanged, and no temp file remains.
- The same edit was also checked ad hoc against the real `Connector_USB_GCT.kicad_sym` from the orchestrator checkout (1970 CRLF, 9-byte shrink, source file hash unchanged).
- Pinned `PySide6==6.12.0`, `pytest==9.1.1`, `pytest-qt==4.5.0`; `pytest` runs bare from the repo root with strict markers and the offscreen platform forced.
- D-15 widget test pins per-source sync and select/deselect all (5 tests).
- `.gitattributes` committed before any fixture; UL sample zip tracked by explicit path with the expected SHA-256.
- SC1 fresh-venv gate passed.

## SC1 Fresh-venv Gate

- Venv: `py -3.14 -m venv` outside the repo (deleted afterwards).
- `pip install -r requirements-dev.txt`: exit status 0.
- Bare `pytest -q` from the repo root: exit 0, `9 passed, 1 skipped in 0.24s` (the skip is the real-Custom tracer test, `Custom/` not checked out in this worktree).

## Task Commits

1. **Task 1: Tracer edit path** - `2b42a87` (feat)
2. **Task 2: Manifests, pytest config, conftest** - `29b044f` (chore)
3. **Task 3: Widget test, .gitattributes, UL sample** - `aad8973` (test)

**Plan metadata:** committed separately after this file (docs).

## Files Created/Modified

- `kicad_lib_manager/models.py` - appended Severity and Issue
- `kicad_lib_manager/sexpr.py` - tokenizer, Node, Edit, apply_edits, quote, unquote, SexprError
- `kicad_lib_manager/fsutil.py` - SourceText, decode/read/encode_source, atomic_write_bytes
- `kicad_lib_manager/kicad_files.py` - SymbolRef, PropertyRef, find_symbols, find_property
- `tests/test_edits.py`, `tests/test_manifests.py`, `tests/test_library_table_widget.py`, `tests/conftest.py` - tests and fixtures (`repo_root`, `assert_tiles`)
- `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `.gitattributes` - harness config
- `downloaded_examples/ul_CSD85301Q2.zip` - tracked vendor sample (never opened or extracted)

## Decisions Made

- Followed the plan as specified. `atomic_write_bytes` is deliberately the minimal core; Plan 02 adds the read-only pre-check and retry window.
- The `assert_tiles` fixture was exercised ad hoc against two real Custom symbol files plus a corrupted-span negative case (detected); no committed test consumes it yet (Plan 03 will).

## Deviations from Plan

### Environment setup (not a code deviation)

- `env/` did not exist in the isolated worktree; created with `py -3.14 -m venv env` and installed the owner-approved pins per the plan's executor-environment note. `env/` is gitignored and not staged.
- The UL zip was copied from `C:/Git_Repo_Clones/Kicad_Libraries-importer/downloaded_examples/` (checkout listed by `git worktree list`); SHA-256 verified before `git add`.

**Total deviations:** 0 auto-fixed. **Impact:** none.

## Issues Encountered

- `Custom/` is uninitialised in this worktree, so `test_tracer_value_edit_real_custom_symbol` skips. The orchestrator must re-run `pytest` after merge with `Custom/` present to see "2 passed" for `tests/test_edits.py`, and confirm `git -C Custom status --porcelain` is empty.
- Git prints LF-to-CRLF warnings on add (`core.autocrlf=true`); harmless for these files.

## Known Stubs

None.

## Threat Flags

None. No new network, auth or trust-boundary surface beyond the plan's threat model.

## Next Phase Readiness

- Wave 2 plans can expand `sexpr`, `fsutil` (read-only pre-check, retry, backup) and `kicad_files` from this tracer; `.gitattributes` and the UL zip are committed before any fixture.
- Open flag from RESEARCH Pitfall 2: `"tests"` is not yet in `SKIP_DIRS` in `library_scanner.py`; must be added in the plan that first commits `.kicad_sym` fixtures under `tests/`.

## Self-Check: PASSED

- Created files all present (checked below); commits `2b42a87`, `29b044f`, `aad8973` are ancestors of HEAD.
- `pytest -q`: 9 passed, 1 skipped (Custom absent). Task 1/2/3 acceptance criteria re-run and passing; `git ls-files -- reports research_notes env` prints nothing.

---
*Phase: 01-foundation*
*Completed: 2026-10-18*
