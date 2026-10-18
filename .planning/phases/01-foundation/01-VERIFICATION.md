---
phase: 01-foundation
verified: 2026-10-18T12:00:00Z
status: human_needed
score: 4/4 roadmap success criteria verified (plus all plan-level truths; 2 test-tier prohibitions flagged)
covered_files:
  - .gitattributes
  - .planning/phases/01-foundation/01-01-PLAN.md
  - .planning/phases/01-foundation/01-01-SUMMARY.md
  - .planning/phases/01-foundation/01-02-PLAN.md
  - .planning/phases/01-foundation/01-02-SUMMARY.md
  - .planning/phases/01-foundation/01-03-PLAN.md
  - .planning/phases/01-foundation/01-03-SUMMARY.md
  - .planning/phases/01-foundation/01-04-PLAN.md
  - .planning/phases/01-foundation/01-04-SUMMARY.md
  - .planning/phases/01-foundation/01-05-PLAN.md
  - .planning/phases/01-foundation/01-05-SUMMARY.md
  - .planning/phases/01-foundation/01-06-PLAN.md
  - .planning/phases/01-foundation/01-06-SUMMARY.md
  - kicad_lib_manager/fsutil.py
  - kicad_lib_manager/kicad_files.py
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/models.py
  - kicad_lib_manager/sexpr.py
  - pyproject.toml
  - requirements-dev.txt
  - requirements.txt
  - tests/conftest.py
  - tests/fixtures/build_fixtures.py
  - tests/test_edits.py
  - tests/test_fixtures.py
  - tests/test_fsutil.py
  - tests/test_kicad_files.py
  - tests/test_layering.py
  - tests/test_library_table_widget.py
  - tests/test_manifests.py
  - tests/test_models.py
  - tests/test_roundtrip_corpus.py
  - tests/test_scanner_skip_dirs.py
  - tests/test_sexpr.py
covered_digest: "v3:sha256:a4c41a48b09f891db45f59d5eaf924b2855393b4d87daa33ca4504189c09b41a"
behavior_unverified: 0
overrides_applied: 0
unverified_prohibitions:
  - statement: "MUST NOT write to, back up into, or modify the owner's real KiCad config (%APPDATA%/kicad), the real app-data backup folder, or any tracked file under Custom/ from the test suite; every write in tests goes to tmp_path (plan 01-02)"
    verification: test
    status: unverified-prohibition
    note: "No automated test enforces this. Observed not violated in this run (Custom git status clean after full suite, %LOCALAPPDATA%/KiCadExtLibManager absent, all write calls in tests target tmp paths)."
  - statement: "MUST NOT copy, commit, write to disk, or print the contents of the owner's real KiCad library tables (plan 01-06)"
    verification: test
    status: unverified-prohibition
    note: "No automated test enforces this. Code read: local-table test reads bytes in place, ids are local/<version>/<filename>, assertions are boolean/byte-offset only."
human_verification:
  - test: "Review the two flagged test-tier prohibitions (writes confined to tmp_path; owner's real KiCad tables never copied or printed) and accept them or ask for a regression test"
    expected: "Owner confirms the observed evidence is sufficient, or schedules a guard test (e.g. a conftest autouse fixture that fails if a write lands outside tmp_path / Custom changes)"
    why_human: "Test-tier prohibitions with no wired enforcement fail closed (ADR-550 D4); they cannot be reported green on an LLM read alone"
---

# Phase 1: Foundation Verification Report

**Phase Goal:** The developer has a headless test harness and a shared S-expression and file-writing layer that provably never damages bytes it was not asked to change
**Verified:** 2026-10-18
**Status:** human_needed (all goal truths verified; only two soft-gated prohibition flags remain)
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths (ROADMAP success criteria, the contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | In a fresh venv, `pip install -r requirements-dev.txt` installs pinned PySide6, pytest, pytest-qt, and `pytest` passes with no display, including an offscreen Qt widget test | VERIFIED | I built a new venv outside the repo (scratchpad), ran `pip install -r requirements-dev.txt` (PySide6 6.12.0, pytest 9.1.1, pytest-qt 4.5.0), then `pytest` with `QT_QPA_PLATFORM` and `DISPLAY` unset: 353 passed, 2 skipped. `tests/conftest.py` forces `QT_QPA_PLATFORM=offscreen`; `test_platform_is_offscreen` asserts `QGuiApplication.platformName() == "offscreen"`; 5 `LibraryTableWidget` tests pin per-source symbol-to-footprint sync. The 2 skips are the WurthElektronik submodule (not checked out), with an explicit reason. |
| 2 | Every `.kicad_sym`, `.kicad_mod`, `sym-lib-table`, `fp-lib-table` in the repo parses and re-serialises byte-identically with no edits | VERIFIED | Independent script (not the test suite): 33 files found by rglob (24 in `Custom/`, plus fixtures; 27 are CRLF), all decode, parse, and `encode_source(apply_edits(text, []), bom) == original bytes`: 0 mismatches. Corpus test `test_roundtrip_repo_owned` additionally runs `assert_tiles` (independent check that node spans plus pure-whitespace gaps cover the text exactly) so identity is not vacuous; `test_assert_tiles_rejects_shifted_span` proves the checker can fail. Owner's real KiCad tables round-trip under `local_kicad`; UL zip members round-trip in memory. Wurth is skipped (not checked out), which the SC allows ("when checked out"). |
| 3 | A targeted edit changes only that span; rest stays byte-identical and CRLF/LF is kept | VERIFIED | Independent script: for the first symbol's `Value` property in each of 15 real/fixture `.kicad_sym` files (CRLF, LF, BOM), replaced the value (with an embedded `"`) via `find_property` -> `Edit` -> `apply_edits` -> `encode_source` -> `atomic_write_bytes`; prefix and suffix around the span identical, CRLF/LF counts equal to original, no `.tmp` left. `tests/test_edits.py` adds the EOL x BOM matrix, inserted text via `normalize_eol`, footprint-name/model-path/lib-table field edits, and flags/unknown children surviving. |
| 4 | Writing over a locked or read-only file logs an error and leaves the original intact (no crash, no truncation); success replaces in one step (temp + replace) | VERIFIED | Observed directly on Windows: read-only target returns `Issue(ERROR, fs.read_only, "Could not write ro.txt: file is read-only")` in 0.0001 s, original bytes unchanged. Target held open via `CreateFileW` share-mode 0 returns `fs.locked` after 1.01 s, original unchanged, no temp left; after the handle is released the write succeeds. Missing parent returns `fs.write_failed` Issue, no exception. Simulated hard kill (`os._exit` inside `os.replace`): target still `ORIGINAL`, exactly one `.t.kicad_sym.<pid>.<hex>.tmp` left, matching the plan's stated residual. `atomic_write_bytes` uses same-directory exclusive-create temp + fsync + `os.replace`. `Issue` is returned, never raised; text starts with "Could not write" per Phase 2 routing. |

**Score:** 4/4 roadmap criteria verified.

### Plan-level truths (condensed)

| Plan | Truth group | Status | Evidence |
|------|-------------|--------|----------|
| 01-01 | Tracer edit path; pins `PySide6==6.12.0`, `pytest==9.1.1`, `pytest-qt==4.5.0`; pytest config (pythonpath, strict markers, qt_api); `.gitattributes` = only `tests/fixtures/** -text`; UL zip tracked with SHA-256 9890115a... | VERIFIED | `requirements*.txt`, `pyproject.toml`, `.gitattributes` read; `test_manifests.py` passes; `sha256sum` of the zip equals the pinned hash; `git ls-files` lists the zip and fixtures. |
| 01-02 | Atomic write matrix (success/read-only/locked/fsync/OSError/missing parent/concurrent), `backup_file` naming, `default_backup_dir` outside repo and Qt-free, EOL x BOM round-trip, `fs.bad_encoding`, `fs.mixed_eol`, `normalize_eol`, Severity/Issue contract | VERIFIED | `fsutil.py` read in full; behaviors reproduced independently (above); `test_fsutil.py` (350 lines) incl. `test_concurrent_writers_leave_one_complete_payload`; backstop truth (hard kill) observed directly. |
| 01-03 | Tokenizer edge cases, error codes with line/col, 100k nesting, fuzz, `apply_edits` contract, `quote`/`unquote` | VERIFIED | `sexpr.py` read in full: iterative stack, no module-level mutable state (only compiled regexes/constants), `apply_edits` raises `ValueError` on overlap/out-of-range, atoms kept as source text. Tests present for each claim (`test_deep_nesting...`, `test_seeded_fuzz_tiles_and_round_trips`, `test_parse_is_thread_safe_and_deterministic` as backstop evidence). |
| 01-04 | `SKIP_DIRS` includes `tests`; frozen fixtures byte-identical to builder; `-text` attribute per fixture | VERIFIED | `library_scanner.py:13` contains `"tests"`; `test_fixtures.py`, `test_scanner_skip_dirs.py` pass. |
| 01-05 | `kicad_files` locators with exact spans, Issue-returning loaders, Qt-free and downward-only imports, edits on all fixtures and live Custom, interrupted write leaves file intact | VERIFIED | `kicad_files.py` read in full; `test_layering.py` runs a fresh `-I` interpreter and asserts no PySide6/shiboken6 modules load; AST check of allowed imports passes. |
| 01-06 | Corpus identity over Custom, fixtures, UL zip (in memory, size cap checked on `ZipInfo.file_size`), opt-in `local_kicad` and `wurth` markers with skip reasons | VERIFIED | `test_roundtrip_corpus.py` read; markers registered in `pyproject.toml`; Wurth skips report the stated reason. |

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `kicad_lib_manager/models.py` (Severity, frozen Issue) | VERIFIED | Substantive; used by fsutil/kicad_files. Values equal LogPanel COLORS keys (`test_models.py`). |
| `kicad_lib_manager/sexpr.py` | VERIFIED | 134 lines, complete, wired from `kicad_files`. |
| `kicad_lib_manager/fsutil.py` | VERIFIED | 201 lines, complete, wired from `kicad_files`; Phase 2+ consumers not yet present (expected). |
| `kicad_lib_manager/kicad_files.py` | VERIFIED | 180 lines, complete. |
| `tests/*`, `pyproject.toml`, `requirements*.txt`, `.gitattributes`, `downloaded_examples/ul_CSD85301Q2.zip` | VERIFIED | All present and tracked. |

### Key Link Verification

| From | To | Status |
|------|----|--------|
| fsutil -> models (`from .models import Issue, Severity`) | WIRED |
| kicad_files -> sexpr / fsutil / models | WIRED |
| tests/test_edits -> fsutil.atomic_write_bytes, normalize_eol | WIRED |
| pyproject `qt_api` -> pytest-qt widget test | WIRED (qtbot fixture works) |
| tests/test_roundtrip_corpus -> conftest `assert_tiles` | WIRED |

### Data-Flow Trace (Level 4)

Not applicable: no rendered dynamic data in this phase; the foundation modules are pure library code with real file I/O (verified by execution above).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `./env/Scripts/python.exe -m pytest -q` | 353 passed, 2 skipped (Wurth) in 5.07 s | PASS |
| Fresh venv suite, no display | new venv + `pytest.exe -q` | 353 passed, 2 skipped | PASS |
| Whole-repo byte round-trip | scratchpad `verify1.py` | 33 files, 0 mismatches | PASS |
| Targeted edit on 15 symbol files | same script | prefix/suffix and EOL counts preserved, no temp | PASS |
| Read-only / locked / missing-parent writes | same script | Issues `fs.read_only` / `fs.locked` / `fs.write_failed`, originals intact | PASS |
| Hard-kill between temp and replace | scratchpad `kill.py` | target intact, one stray temp | PASS |

### Probe Execution

No `probe-*.sh` scripts declared or present. SKIPPED.

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|---------------|-------------|--------|----------|
| FOUND-01 | 01-01 | Pinned runtime and dev deps | SATISFIED | `requirements.txt`, `requirements-dev.txt` exact pins; fresh-venv install succeeded; `test_manifests.py`. |
| FOUND-02 | 01-01 | Headless pytest incl. offscreen Qt | SATISFIED | conftest forces offscreen; widget tests pass in a no-display shell. |
| FOUND-03 | 01-04, 01-05, 01-06 | Byte-identical round-trip of all KiCad files | SATISFIED | Independent round-trip of 33 files; corpus tests. |
| FOUND-04 | 01-01, 01-02, 01-03, 01-05 | Edit changes only the targeted span, keeps EOL | SATISFIED | Independent edit script; `test_edits.py`. |
| FOUND-05 | 01-02 | Atomic replace; locked/read-only gives error not crash | SATISFIED | Observed on Windows. |

All five IDs in PLAN frontmatter (FOUND-01..05) match REQUIREMENTS.md and the ROADMAP Phase 1 list. No orphaned requirements. Note: REQUIREMENTS.md still shows these five as unchecked / "Pending"; the orchestrator should tick them on phase completion.

### Anti-Patterns Found

Scan of the four production modules and `library_scanner.py` change: no TBD/FIXME/XXX/TODO markers, no stubs, no placeholder returns. 01-REVIEW.md (advisory, 0 critical, 7 warning, 7 info, all open) was checked for goal impact; none falsifies a success criterion:

| Item | Severity | Impact on goal |
|------|----------|----------------|
| WR-01 locators do not check token kind of name/value (a list in value position would be treated as a value span) | Warning | Matters when Phase 4+ edits foreign files; not exercised by Phase 1 SC |
| WR-03 any `PermissionError` from `os.replace` is reported as "file is in use" after ~1 s | Warning | Message accuracy only; original still intact |
| WR-04 `encode_source` / `atomic_write_text` can raise on a lone-surrogate string (caller-supplied text) | Warning | Breaks "return an Issue" contract for non-decodable new text; bytes read from disk can never trigger it. Worth fixing before Phase 4 inserts user-supplied names |
| WR-02, WR-05..07, IN-01..07 | Warning/Info | Hygiene, test brittleness, messages |

### Human Verification Required

#### 1. Flagged test-tier prohibitions (unverified-prohibition, human review recommended)

**Test:** Review the two prohibitions listed in the frontmatter (no test-suite writes outside `tmp_path` / to the real KiCad config, backup dir or `Custom/`; real KiCad tables never copied or printed).
**Expected:** Accept on the evidence here (Custom `git status` clean after the full suite, no `%LOCALAPPDATA%/KiCadExtLibManager`, every test write call targets a tmp path, local-table test only reads bytes in memory), or request a guard test.
**Why human:** They are `verification: test` prohibitions with no wired enforcement test, which fail closed rather than pass. The other two prohibitions (never stage `reports/` or `research_notes/`) are verified deterministically: `git diff --name-only` across the phase touches neither path and `git ls-files` tracks neither.

### Gaps Summary

No gaps. The phase goal is achieved in the codebase: the pinned, headless harness works from a clean venv, and the S-expression plus atomic-write layer provably preserves untouched bytes, which I confirmed by re-running round-trips, edits, and failure cases independently of the test suite. Status is `human_needed` solely because of the two flagged, unenforced test-tier prohibitions. Recommend addressing WR-04 and WR-01 early in Phase 2 or 4.

---

_Verified: 2026-10-18_
_Verifier: Claude (gsd-verifier)_
