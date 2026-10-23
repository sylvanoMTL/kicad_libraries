---
phase: 07-snapeda-and-samacsys-adapters
plan: 01
subsystem: importer
tags: [snapeda, adapter-registry, vendor-detection, fixtures, gitignore, kicad-sym]

requires:
  - phase: 03-package-intake-and-naming
    provides: Adapter registry (ADAPTERS), Package/PackageFile staging, hostile-zip caps
  - phase: 04-plan-and-install-core
    provides: build_plan/apply_plan, Manufacturer/MPN alias rename in place
  - phase: 06-commit-step
    provides: build_commit_plan / default_message with the Import-Vendor trailer
provides:
  - SnapEDAAdapter (symbol-property and snapeda.com marker scoring, claim at 5 points)
  - read_head, SNIFF_BYTES, SNIFF_FILES in adapters/base.py (bounded, total head read for vendor adapters)
  - synthetic SnapEDA builders in tests/vendorfixtures.py
  - tracer test and open/plan helpers in tests/test_vendor_install.py
  - forward layering registrations for importer.fieldrules and importer.adapters.samacsys
  - .gitignore rule keeping licence-restricted vendor zips out of the public repo
affects: [07-02, 07-03, 07-04, 07-05, 07-06]

actuals:
  tokens: 4200
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Points-and-threshold vendor adapter reading a bounded head of staged symbols (total, never raises)"
    - "Synthetic vendor fixtures: copy layout, names and markers, never content (D-01)"

key-files:
  created:
    - kicad_lib_manager/importer/adapters/snapeda.py
    - tests/vendorfixtures.py
    - tests/test_vendor_install.py
    - tests/test_snapeda_adapter.py
  modified:
    - kicad_lib_manager/importer/adapters/base.py
    - kicad_lib_manager/importer/detect.py
    - tests/test_adapters.py
    - tests/test_importer_layering.py
    - .gitignore

key-decisions:
  - "SnapEDA is registered between UltraLibrarian and Loose so a SnapEDA folder beats Loose's 0.3 and ties stay in registry order"
  - "The tracer asserts subsets of sections and properties and nothing about fields later plans drop or clean, so 07-02/07-03 extend the path without editing it"
  - "importer.fieldrules and importer.adapters.samacsys are forward registrations in ALLOWED; only existing modules join CORE_MODULES"
  - "The ignore rule uses the folder-contents form (downloaded_examples/*) so the negation can re-include the UL sample"

patterns-established:
  - "read_head(pf) is the one bounded sniff primitive for adapters: 64 KiB, at most 8 files, b'' on OSError"
  - "Vendor install tests build a synthetic Custom/ under tmp_path with write_custom_layout (D-03)"

requirements-completed: [INTK-03]

duration: 10min
completed: 2026-10-23
status: complete
plan_head_before: a016650e1e3e312091f3c38d494d442137e7ca8a
plan_head_after: 5236cc95078a7df49635d42accd51af737dea706
commits: 3

coverage:
  - id: D1
    description: "A zip whose staged symbol carries a SnapEDA marker is detected as SnapEDA (confidence >= 0.7), with no unknown-vendor Issue; a renamed two-file zip still scores 0.7"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_vendor_install.py#test_tracer_snapeda_end_to_end"
        status: pass
      - kind: unit
        ref: "tests/test_snapeda_adapter.py#test_snapeda_renamed_two_file_zip_recognised"
        status: pass
    human_judgment: false
  - id: D2
    description: "The synthetic SnapEDA part installs into a synthetic Custom/ with Footprint linked as <Lib>:<FP>, MF/MP renamed to Manufacturer/MPN, install.no_model reported, file bytes equal to the plan, and Import-Vendor: SnapEDA in the commit message"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_vendor_install.py#test_tracer_snapeda_end_to_end"
        status: pass
    human_judgment: false
  - id: D3
    description: "SnapEDAAdapter.detect returns None for UL, generic and unreadable packages and never raises; the generic zip still reads as Unknown"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_snapeda_adapter.py#test_snapeda_not_claimed_elsewhere"
        status: pass
      - kind: unit
        ref: "tests/test_snapeda_adapter.py#test_snapeda_detect_survives_unreadable_symbol"
        status: pass
    human_judgment: false
  - id: D4
    description: "Licence-restricted vendor zips are git-ignored while the UL sample stays the only tracked file in downloaded_examples/"
    verification:
      - kind: other
        ref: "git check-ignore on both vendor zips (exit 0), on the UL sample (exit 1), and git ls-files downloaded_examples"
        status: pass
    human_judgment: false
---

# Phase 7 Plan 01: SnapEDA Tracer Summary

**SnapEDAAdapter recognises SnapEDA zips from symbol-property markers and carries the "SnapEDA" label through plan, install and the Import-Vendor commit trailer; vendor zips are git-ignored.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-10-23T10:40:37Z
- **Completed:** 2026-10-23T10:50:02Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- `SnapEDAAdapter` (name "SnapEDA", D-15) scores 5 points for a `SnapEDA_Link` / `SNAPEDA_PN` / `SNAPEDA_PACKAGE_ID` property and 2 for `snapeda.com` in the first staged symbols' heads; a renamed two-file zip scores 0.7 and is recognised (D-14). It is registered before `LooseAdapter`, callers of `detect_candidate` unchanged.
- `read_head`, `SNIFF_BYTES` (64 KiB) and `SNIFF_FILES` (8) added to `adapters/base.py`: a total, bounded read of files `open_package` already staged under the unchanged Phase 3 caps.
- Tracer `test_tracer_snapeda_end_to_end` drives synthetic zip -> detect -> plan -> preview -> apply -> `Import-Vendor: SnapEDA` in a synthetic `Custom/` (D-03): Footprint field `Connector_USB_GCT:<FP>`, MF/MP renamed in place, `SnapEDA_Link` and `MAXIMUM_PACKAGE_HEIGHT` kept, `install.no_model` reported, file bytes on disk equal the plan's op bytes.
- Synthetic SnapEDA builders in `tests/vendorfixtures.py` (symbol, footprint, how-to-import.htm, members, zip), written from scratch (D-01).
- Layering map: `importer.adapters.snapeda` registered and added to `CORE_MODULES`; `importer.fieldrules` (empty set) and `importer.adapters.samacsys` registered as forward modules.
- `.gitignore`: `downloaded_examples/*` with `!downloaded_examples/ul_CSD85301Q2.zip` (D-01, D-02).

## Task Commits

1. **Task 1: SnapEDA tracer (TDD)**
   - RED: `6596951` (test) - RED evidence classified `RED_EVIDENCE_OK` by `gsd check tdd-red-evidence` (JUnit XML): the tracer failed on `assert 'Unknown' == 'SnapEDA'` after the synthetic zip opened and planned normally; the two direct-adapter tests failed with `ModuleNotFoundError` for the missing module; the renamed-zip test failed on the same vendor assertion. Semantic assessment: target ran to the planned assertion for the intended reason.
   - GREEN: `47bef20` (feat)
   - REFACTOR: none needed
2. **Task 2: Ignore licence-restricted vendor zips** - `5236cc9` (chore)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `kicad_lib_manager/importer/adapters/snapeda.py` - SnapEDA marker scoring
- `kicad_lib_manager/importer/adapters/base.py` - `SNIFF_BYTES`, `SNIFF_FILES`, `read_head`
- `kicad_lib_manager/importer/detect.py` - registers `SnapEDAAdapter()` before `LooseAdapter()`
- `tests/vendorfixtures.py` - synthetic SnapEDA builders
- `tests/test_vendor_install.py` - tracer and its layout/open/plan helpers
- `tests/test_snapeda_adapter.py` - three detection tests
- `tests/test_adapters.py` - registry order and type list now include SnapEDA; the appended fake renamed "Extra"
- `tests/test_importer_layering.py` - registrations for snapeda, samacsys, fieldrules and widened dependents
- `.gitignore` - vendor-zip ignore rule

## Decisions Made

- Followed the plan as specified; see `key-decisions` in the frontmatter. The tracer feedback gate ran in interactive `end-of-phase` mode with an automated-only `<verify>`: the tracer verify re-ran green, so expansion continued (no checkpoint).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- The worktree has no `Custom/` or `WurthElektronik` submodule checkout and lacks the two licence-restricted vendor zips, so the tests that read the real `Custom/` tree skip here (the plan's second verify command reports 19 skips, all "Custom submodule not checked out" or the UAT env gate). The orchestrator re-runs the full suite in the main checkout after the merge.
- Full-suite run in the worktree: 4 failed, 1711 passed, 79 skipped. All 4 failures are ids in the 07-RESEARCH Pitfall 8 baseline (`test_install_plan::test_version_real_cli_into_20241209`, `test_install_plan::test_library_real_cli_new_header`, `test_install_plan::test_noop_second_plan_after_normalised_apply`, `test_kicad_cli::test_real_cli_upgrades_ul_symbol_deterministically`), caused by KiCad 10's 20251024 format.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 07-02 can add `SNAPEDA_RULES`, volatile drops and the "Field changes" preview section on the same path; the tracer asserts nothing about Price, Check_prices, Availability, MANUFACTURER, SNAPEDA_PN, Package or the Description text, so it needs no edit.
- No blockers.

## Threat Flags

None. `read_head` only reads files `open_package` already staged (T-07-01) and the `.gitignore` rule closes T-07-02; no new network, auth or trust-boundary surface.

## Known Stubs

None.

---
*Phase: 07-snapeda-and-samacsys-adapters*
*Completed: 2026-10-23*

## Self-Check: PASSED

- FOUND: kicad_lib_manager/importer/adapters/snapeda.py, tests/vendorfixtures.py, tests/test_vendor_install.py, tests/test_snapeda_adapter.py
- FOUND commits: 6596951, 47bef20, 5236cc9
- Acceptance criteria re-run: `class SnapEDAAdapter`, `name = "SnapEDA"`, `SNAPEDA_CLAIM_POINTS = 5`, `b"snapeda_link"` present; `SnapEDAAdapter()` precedes `LooseAdapter()` in `ADAPTERS`; `def read_head(`, `SNIFF_BYTES = 64 * 1024`, `SNIFF_FILES = 8` present; `def snapeda_members(`, `def snapeda_zip(`, `SnapEDA_Link` in vendorfixtures; layering file holds `"importer.adapters.snapeda":`, `"importer.adapters.samacsys":`, `"importer.fieldrules": set()`; both verify commands exit 0; Task 2 verify checks pass.
