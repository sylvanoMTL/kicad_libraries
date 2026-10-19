---
phase: 03-package-intake-and-naming
plan: 04
subsystem: importer-intake
tags: [kicad-files, adapters, legacy-kicad5, loose-folder, content-sniffing]

requires:
  - phase: 03-package-intake-and-naming
    provides: "plan 03-01 importer tracer (package, candidate, adapters, detect); plan 03-02 zipfixtures and importer layering guard"
provides:
  - "kicad_files.file_kind / file_version read helpers"
  - "locate: content-vs-extension checks, format versions, embedded_files flag, capped reads, all items returned"
  - "Legacy KiCad 5 decision matrix with 're-download as KiCad v6+' refusals (INTK-05)"
  - "LooseAdapter and the [UltraLibrarian, Loose] registry; generic Unknown vendor fallback"
affects: [03-07 folder intake, phase-04, phase-05, phase-07-adapters]

actuals:
  tokens: 17500
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Located-items decision matrix (_legacy_rules) evaluated after locate, so unreadable or mismatched files never count as v6+"
    - "Capped reads read package.MAX_MEMBER_BYTES at call time through the module, so tests can monkeypatch it"

key-files:
  created:
    - kicad_lib_manager/importer/adapters/loose.py
    - tests/test_legacy_rules.py
  modified:
    - kicad_lib_manager/kicad_files.py
    - kicad_lib_manager/importer/adapters/base.py
    - kicad_lib_manager/importer/detect.py
    - tests/test_kicad_files.py
    - tests/test_adapters.py

key-decisions:
  - "D-18 implemented as one branch in _locate_footprint: a (module ...) root is a footprint with format_version None and WARNING intake.legacy_footprint_syntax, so it never reaches the legacy matrix"
  - "intake.unknown_vendor is added only when a candidate exists; a refused generic zip reports just its ERROR"
  - "The literal phrase 're-download as KiCad v6+' is written inline in each refusal text (no shared constant) so the acceptance grep count of at least 2 holds"

patterns-established:
  - "Pattern: new issue texts name the package by package.source.name and cap name lists at 20 with 'and N more'"

requirements-completed: [INTK-01, INTK-02, INTK-05]

coverage:
  - id: D1
    description: "file_kind / file_version return the first top-level head and ASCII-integer version (UL 20211014, lf 20241209, module None) and reject non-integer or nested versions"
    requirement: "INTK-05"
    verification:
      - kind: unit
        ref: "tests/test_kicad_files.py#test_file_kind_and_version"
        status: pass
      - kind: unit
        ref: "tests/test_kicad_files.py#test_file_version_rejects_non_integers_and_nested_versions"
        status: pass
    human_judgment: false
  - id: D2
    description: "locate checks content against extension (symbol, footprint, STEP, VRML), records versions and embedded_files, returns all items in package order, skips oversize files, and keeps names verbatim from file content"
    requirement: "INTK-02"
    verification:
      - kind: unit
        ref: "tests/test_adapters.py#test_locate_content_mismatch"
        status: pass
      - kind: unit
        ref: "tests/test_adapters.py#test_locate_all_items"
        status: pass
      - kind: unit
        ref: "tests/test_adapters.py#test_locate_oversize_file_skipped"
        status: pass
      - kind: unit
        ref: "tests/test_adapters.py#test_locate_casefolded_markers"
        status: pass
    human_judgment: false
  - id: D3
    description: "KiCad 5 only and half-legacy packages are refused with the re-download message; mixed packages use their v6+ files; (module ...) footprints are never legacy; nothing-found is its own error"
    requirement: "INTK-05"
    verification:
      - kind: unit
        ref: "tests/test_legacy_rules.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Unknown zips are read as generic Unknown with INFO intake.unknown_vendor; folders are claimed by LooseAdapter (0.3) unless Ultra Librarian scores higher; the registry accepts new adapters without caller changes; the loose adapter is proven on the real UL files unpacked flat (D-17)"
    requirement: "INTK-01"
    verification:
      - kind: unit
        ref: "tests/test_adapters.py#test_generic_unknown_vendor,test_loose_folder_package,test_ul_folder_beats_loose,test_registry_extension_point"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-19
status: complete
plan_head_before: af7bf2b412306a4fa45362d8ec697436e091d872
plan_head_after: 971ccaef242060aad457be315f804b7d08ac86e0
commits: 4
---

# Phase 3 Plan 04: Legacy Rules, Content Checks and Loose Adapter Summary

**Content-checked `locate` with format versions and the KiCad 5 decision matrix (re-download refusals), `(module ...)` footprints accepted with a warning (D-18), a generic Unknown vendor fallback, and a `LooseAdapter` proven on the real Ultra Librarian files unpacked flat into `tmp_path` (D-17)**

## Performance

- **Duration:** about 25 min
- **Started:** 2026-10-19T13:50:00Z (approx.)
- **Completed:** 2026-10-19T14:15:00Z
- **Tasks:** 2 (both TDD, 4 commits)
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments

- `file_kind(root)` and `file_version(root)` added to `kicad_files.py`: the head and ASCII-integer `(version N)` of the first top-level list, `None` for anything else (quoted, decimal, non-ASCII digits, nested).
- `locate` now rejects files whose content does not match their extension (one WARNING `intake.content_mismatch` each), reports undecodable, unparsable, oversize or unreadable files as `intake.unreadable_file`, records `format_version` on every symbol and footprint, sets `has_embedded_files` from direct `(embedded_files` children, and returns every symbol, footprint and model in package order.
- `(module ...)` footprints are accepted with `format_version` None and WARNING `intake.legacy_footprint_syntax`; they count as v6+ footprints and can never trigger the INTK-05 refusal (D-18).
- `_legacy_rules` applies the full matrix: `intake.legacy_only`, `intake.half_legacy` (both mirrored forms), `intake.nothing_found`, INFO `intake.legacy_ignored`, WARNING `intake.no_footprint` / `intake.no_symbol`, INFO `intake.no_model`. Both refusal texts contain "re-download as KiCad v6+". Legacy extensions match case-insensitively and an unreadable v6 file does not count as v6+.
- `detect.ADAPTERS` is `[UltraLibrarianAdapter(), LooseAdapter()]`; an unrecognised zip becomes vendor Unknown at 0.1 with INFO `intake.unknown_vendor` in both the returned list and `candidate.issues`.

## Task Commits

1. **Task 1 RED: failing tests for file kind/version and locate content checks** - `f763129` (test)
2. **Task 1 GREEN: file kind/version helpers and content-checked locate** - `94a6346` (feat)
3. **Task 2 RED: failing tests for legacy matrix, unknown vendor and loose adapter** - `a80b09e` (test)
4. **Task 2 GREEN: legacy decision matrix, unknown vendor and loose-folder adapter** - `971ccae` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `kicad_lib_manager/kicad_files.py` - `file_kind`, `file_version`
- `kicad_lib_manager/importer/adapters/base.py` - `_read_limited`, `_check_model`, `_locate_symbols`, `_locate_footprint`, `_name_list`, `_legacy_rules`, upgraded `locate`
- `kicad_lib_manager/importer/adapters/loose.py` - `LooseAdapter`, `LOOSE_CONFIDENCE` (new)
- `kicad_lib_manager/importer/detect.py` - registry with Loose, generic fallback with `intake.unknown_vendor`
- `tests/test_kicad_files.py` - 3 tests for the read helpers
- `tests/test_adapters.py` - 9 locate tests, 5 detection/loose/registry tests, one existing registry assertion updated
- `tests/test_legacy_rules.py` - 11 matrix tests on synthetic zips (new)

## Decisions Made

- `intake.unknown_vendor` is attached only when a candidate is returned; a generic zip refused by the matrix reports its ERROR alone (an unrecognised-vendor note on a refusal adds nothing).
- Refusal texts repeat the phrase inline instead of using a constant, to satisfy the plan's acceptance grep (`grep -c` of at least 2 on `base.py`).
- Layering: `base.py` reads the cap via `from .. import package as _package` (`importer.package` is already in its ALLOWED entry), so no change to `tests/test_importer_layering.py`.

## TDD Gate Compliance

- **Task 1 RED (`f763129`):** `file_kind` / `file_version` were committed as stubs returning None so the tests fail on their planned assertions rather than at import. Failing on assertions: `test_file_kind_and_version`, `test_file_version_rejects_non_integers_and_nested_versions`, `test_locate_versions_on_ul`, `test_locate_content_mismatch`, `test_locate_legacy_module_syntax` (`0 == 1`), `test_locate_embedded_files_flag`, `test_locate_oversize_file_skipped` (`0 == 1`): 7 failed, 54 passed. Semantic assessment: each failure is the planned behavior missing (version None, no mismatch/legacy-syntax warning, no cap). `test_locate_all_items`, `test_locate_part_meta_fields`, `test_locate_casefolded_markers`, `test_locate_step_with_bom_and_whitespace` and `test_file_kind_of_empty_input` were already green because the tracer already behaved that way; they are regression guards for requirements the plan lists, not RED evidence.
- **Task 1 GREEN (`94a6346`):** full suite 562 passed, 9 skipped.
- **Task 2 RED (`a80b09e`):** `loose.py` committed as a detect-nothing stub so `from ...loose import LooseAdapter` collects. 16 failed (11 matrix tests plus registry, generic vendor, loose folder, loose detect rules, extension point), 32 passed, all on the planned assertions. `test_ul_folder_beats_loose` was already green (UL wins at 0.9 against a stub that never claims).
- **Task 2 GREEN (`971ccae`):** 578 passed, 9 skipped.
- **REFACTOR:** none needed. `workflow.tdd_mode` is not enabled, so the `check tdd-red-evidence` classifier was not run.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing registry assertion expected a one-adapter registry**
- **Found during:** Task 2
- **Issue:** `test_ultra_adapter_registry_holds_the_ultra_adapter` from plan 03-01 asserted `ADAPTERS` names equal `["UltraLibrarian"]`, which the plan itself makes false (`ADAPTERS` is `[UltraLibrarianAdapter(), LooseAdapter()]`).
- **Fix:** Changed the expected list to `["UltraLibrarian", "Loose"]` with a comment. The plan said to keep existing tests unchanged, but this assertion contradicts the planned registry.
- **Files modified:** tests/test_adapters.py
- **Committed in:** a80b09e

**2. [Rule 3 - Blocking] Signature-only stubs in the RED commits**
- **Found during:** Task 1 and Task 2 RED
- **Issue:** Tests import `file_kind` / `file_version` and `LooseAdapter`; without them the tests fail at collection (INVALID_RED).
- **Fix:** Committed stubs with the RED tests (as plan 03-01 did); the GREEN commits replace them.
- **Files modified:** kicad_lib_manager/kicad_files.py, kicad_lib_manager/importer/adapters/loose.py
- **Committed in:** f763129, a80b09e

---

**Total deviations:** 2 auto-fixed (1 bug in a prior test assertion, 1 process-only)
**Impact on plan:** None on behavior.

## Follow-ups for sibling or later plans (not changed here)

- None required in `package.py` or `candidate.py`. The folder walk that produces `Package(kind="folder")` for real is plan 03-07; here the folder Package is built by hand in tests.

## Issues Encountered

None. The sandbox rejected some compound shell commands, so commands were run as separate plain calls.

## Test Results

Run with the main checkout interpreter by absolute path from the worktree root (no `env/` here, no venv created).

- `pytest tests/test_kicad_files.py tests/test_adapters.py tests/test_layering.py tests/test_importer_layering.py`: 84 passed, 2 skipped after Task 1.
- `pytest tests/test_legacy_rules.py tests/test_adapters.py tests/test_importer_layering.py`: 48 passed after Task 2 (`test_legacy_rules.py` alone: 11 passed; `-k loose_folder_package`: 1 passed).
- Full suite: **578 passed, 9 skipped**. The 9 skips are the submodule-dependent tests (`Custom/` and `WurthElektronik/KiCad-Library` are not checked out in the worktree).
- `git status --porcelain -- Custom downloaded_examples` printed nothing. `grep -c "re-download as KiCad v6+"` on `base.py` prints 3. The `-I` registry check prints `['UltraLibrarianAdapter', 'LooseAdapter']`.

## Known Stubs

None. The RED-commit stubs were replaced in the matching GREEN commits.

## Threat Flags

None. T-03-15 (capped reads), T-03-16 (parse errors mapped to `intake.unreadable_file`) and T-03-18 (root head recorded, WARNING `intake.legacy_footprint_syntax`) are implemented as planned. T-03-14 stays with plans 03-05 and Phase 4. Prohibition check: names come only from `find_symbols` / `footprint_name` (the UL timestamp file name never appears in a name), and every commit staged explicit paths only.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03-07 can feed real folders to `detect_candidate`; `LooseAdapter` already claims `kind == "folder"` and the matrix applies identically.
- Phase 5 can read `format_version`, `root_head` and `has_embedded_files` from the candidate (PREV-06).
- Phase 7 appends vendor adapters to `ADAPTERS` and registers them in `tests/test_importer_layering.py`.

## Self-Check: PASSED

- Created files `kicad_lib_manager/importer/adapters/loose.py` and `tests/test_legacy_rules.py` exist on disk.
- Commits `f763129`, `94a6346`, `a80b09e`, `971ccae` are ancestors of HEAD.

---
*Phase: 03-package-intake-and-naming*
*Completed: 2026-10-19*
