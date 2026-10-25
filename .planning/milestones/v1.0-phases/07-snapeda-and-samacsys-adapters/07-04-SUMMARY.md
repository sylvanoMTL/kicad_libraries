---
phase: 07-snapeda-and-samacsys-adapters
plan: 04
subsystem: importer-intake
tags: [snapeda, intake, markers, zipfile, verify, pytest]

requires:
  - phase: 07-snapeda-and-samacsys-adapters
    provides: "07-01 SnapEDAAdapter and vendorfixtures; 07-02 SNAPEDA_RULES"
provides:
  - "Package.markers / Package.marker_text: bounded in-memory capture of part_info.txt, license.txt, how-to-import.htm(l) (D-13)"
  - "SnapEDA scores how-to-import.htm (2) and its snapeda.com link (3); real USB4145 zip reads as SnapEDA 1.0"
  - "verify.footprint_pad_numbers ignores np_thru_hole pads for every vendor"
  - "tests/test_real_vendor_samples.py: gated real-sample tests and the gitignore guard (D-02)"
affects: [07-05 SamacSys adapter, 07-06 real-sample tests]

actuals:
  tokens: 6000
  tasks: 2
  commits: 5

plan_head_before: 6ef29c31aa1c205e3178d10edd3c3983c49aab40
plan_head_after: ec02cab

tech-stack:
  added: []
  patterns:
    - "Non-staged text read in memory at open time into Package.markers, never written (D-13)"
    - "Real-sample tests skip by file name, not env var (D-02)"

key-files:
  created:
    - tests/test_real_vendor_samples.py
  modified:
    - kicad_lib_manager/importer/package.py
    - kicad_lib_manager/importer/adapters/snapeda.py
    - kicad_lib_manager/importer/verify.py
    - tests/test_package_zip.py
    - tests/test_snapeda_adapter.py
    - tests/test_install_verify.py

key-decisions:
  - "Markers are captured at open time (zip is closed once staging ends; re-opening would repeat the hostile-zip checks)"
  - "marker_text is a Package method so both adapters reach markers without another helper module"
  - "np_thru_hole pads are ignored by the pin/pad check for all vendors; a plated pad named None still counts"
  - "Marker bytes count toward the running byte budget for bookkeeping but never cause a refusal"

patterns-established:
  - "Marker read failure or over-cap = INFO intake.marker_skipped, never a refusal"

requirements-completed: [INTK-03]

coverage:
  - id: D1
    description: "open_package keeps at most 16 marker members of at most 64 KiB in memory only, for zips, nested zips and folders; staging folder lists only sym_/fp_/model_ files"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_package_zip.py#test_markers_held_in_memory_only"
        status: pass
      - kind: unit
        ref: "tests/test_package_zip.py#test_marker_limits"
        status: pass
      - kind: unit
        ref: "tests/test_package_zip.py#test_marker_nested_and_folder"
        status: pass
    human_judgment: false
  - id: D2
    description: "Oversized or corrupt marker members are skipped with INFO intake.marker_skipped and never refuse the package; marker_text decodes shallowest match safely"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_package_zip.py#test_marker_over_cap_skipped"
        status: pass
      - kind: unit
        ref: "tests/test_package_zip.py#test_marker_corrupt_member_skipped"
        status: pass
      - kind: unit
        ref: "tests/test_package_zip.py#test_marker_text_shallowest"
        status: pass
    human_judgment: false
  - id: D3
    description: "SnapEDA scores its how-to-import.htm marker; full zip 1.0, page alone 0.5, folder beats Loose, detection idempotent"
    requirement: INTK-03
    verification:
      - kind: unit
        ref: "tests/test_snapeda_adapter.py#test_snapeda_full_zip_scores_max"
        status: pass
      - kind: unit
        ref: "tests/test_snapeda_adapter.py#test_how_to_import_alone"
        status: pass
      - kind: unit
        ref: "tests/test_snapeda_adapter.py#test_snapeda_folder_beats_loose"
        status: pass
      - kind: unit
        ref: "tests/test_snapeda_adapter.py#test_snapeda_detect_twice_same_candidate"
        status: pass
    human_judgment: false
  - id: D4
    description: "np_thru_hole pads are not counted by the pin/pad check"
    verification:
      - kind: unit
        ref: "tests/test_install_verify.py#test_np_thru_hole_pads_ignored"
        status: pass
    human_judgment: false
  - id: D5
    description: "The real USB4145 SnapEDA download is recognised as SnapEDA 1.0, suggests Connector_USB_GCT, and the vendor zips stay git-ignored"
    requirement: INTK-03
    verification:
      - kind: integration
        ref: "tests/test_real_vendor_samples.py#test_real_snapeda_recognised"
        status: pass
      - kind: integration
        ref: "tests/test_real_vendor_samples.py#test_real_snapeda_suggestion"
        status: pass
      - kind: integration
        ref: "tests/test_real_vendor_samples.py#test_vendor_zips_stay_local"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-10-23
status: complete
---

# Phase 7 Plan 04: SnapEDA recognition on the real download Summary

**Bounded in-memory marker capture (`Package.markers`) feeds a how-to-import.htm score in the SnapEDA adapter, so the real USB4145 zip reads as SnapEDA at confidence 1.0, and np_thru_hole mounting holes no longer trigger a pin/pad warning.**

## Performance

- **Duration:** about 15 min
- **Started:** 2026-10-23T11:21:46Z
- **Completed:** 2026-10-23T11:37Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 7 (1 created)

## Accomplishments
- `package.py` gains `MAX_MARKER_BYTES` (64 KiB), `MAX_MARKERS` (16), `MARKER_NAMES`, `Package.markers`, `Package.marker_text`, `_is_marker`; markers are read after the unchanged Phase 3 hostile-zip refusals and caps, for zips, one-level nested zips and folders, and never extracted.
- Oversized or unreadable markers become one INFO `intake.marker_skipped` and never refuse a package.
- `SnapEDAAdapter` adds 2 points for a how-to-import.htm(l) member and 3 for its snapeda.com link; the module docstring carries the full weights table.
- `verify.footprint_pad_numbers` skips `np_thru_hole` pads (RESEARCH Pitfall 7), so SnapEDA's `(pad None np_thru_hole ...)` holes no longer raise `verify.pin_pad_mismatch`.
- New `tests/test_real_vendor_samples.py` proves the real SnapEDA zip is recognised (SnapEDA, 1.0, symbol and footprint found, no model note, no unknown-vendor note, suggestion `Connector_USB_GCT`) and that both vendor zips stay git-ignored while only the UL sample is tracked.

## TDD Gate Compliance

- **RED (Task 1):** `0f1a2e0` - 8 of 10 new tests failed for the planned reasons (`Package` had no `markers`/`marker_text`; full zip scored 0.7 not 1.0; how-to-import alone read as Unknown). Two guard tests (`test_snapeda_folder_beats_loose`, `test_snapeda_detect_twice_same_candidate`) already held and passed, as regression guards. Semantic assessment: each failure was on the named assertion, not a collection or fixture fault. The `gsd_run check tdd-red-evidence` classifier was not run (the plan is `type: execute`, not a `type: tdd` plan).
- **GREEN (Task 1):** `f18d211`.
- **RED (Task 2):** `543ca18` - `test_np_thru_hole_pads_ignored` failed with `'None'` wrongly in the pad set. The real-sample and gitignore tests in the same commit pass at once, because they depend on Task 1 and on `.gitignore`; they are verification tests rather than RED drivers.
- **GREEN (Task 2):** `ade14b9`.
- Follow-up `ec02cab` only reformats the skipif marks to one line to match the plan's literal acceptance grep.

## Task Commits

1. **Task 1: markers in memory and SnapEDA how-to-import scoring** - `0f1a2e0` (test), `f18d211` (feat)
2. **Task 2: real SnapEDA recognition, np_thru_hole, gitignore guard** - `543ca18` (test), `ade14b9` (feat), `ec02cab` (test, formatting)

**Plan metadata:** the docs commit that adds this SUMMARY.

## Files Created/Modified
- `kicad_lib_manager/importer/package.py` - marker constants, `Package.markers`, `marker_text`, bounded capture in `_stage_zip` and `_open_folder`
- `kicad_lib_manager/importer/adapters/snapeda.py` - how-to-import name and content points, weights docstring
- `kicad_lib_manager/importer/verify.py` - `footprint_pad_numbers` ignores `np_thru_hole`
- `tests/test_package_zip.py`, `tests/test_snapeda_adapter.py`, `tests/test_install_verify.py` - new tests
- `tests/test_real_vendor_samples.py` - new, gated by file name (D-02)

## Decisions Made
See `key-decisions` above; all follow the plan. One detail the plan left open: hitting `MAX_MARKERS` drops the remaining markers silently (no Issue), since losing detection points is the only effect.

## Deviations from Plan

None - plan executed exactly as written. (Test-only note: `test_how_to_import_alone` and `test_snapeda_full_zip_scores_max` read adapter reasons from `SnapEDAAdapter().detect(package)`, because `ImportCandidate` does not carry reasons.)

## Issues Encountered
- The full suite shows exactly the 21 known environmental failures (tests/test_commit_plan.py, test_import_dialog.py, test_import_preview.py, test_install_apply.py, test_install_e2e.py, test_install_plan.py, test_kicad_cli.py); no new failure. 1822 passed, 5 skipped.
- `test_marker_corrupt_member_skipped` relies on the same LZMA flip offset the existing corrupt-member tests pin; it passed on Python 3.14 here.

## Known Stubs
None.

## Threat Flags
None - markers are bytes keyed by name, nothing is created from them (T-07-09 to T-07-12 mitigated by the tests named in the coverage block).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
Plan 07-05 (SamacSys adapter) can read `part_info.txt` and `license.txt` through `package.marker_text(...)`. Plan 07-06 extends `tests/test_real_vendor_samples.py` using `REAL_SAMACSYS` and `requires_samacsys`.

## Self-Check: PASSED

- Created file `tests/test_real_vendor_samples.py` exists; modified files exist.
- Commits `0f1a2e0`, `f18d211`, `543ca18`, `ade14b9`, `ec02cab` are on the branch (`git rev-list --count` from the ledger base is 5).
- Task acceptance greps and both task verify commands pass; the plan-level verification subset passes (103 passed, 1 skipped) and the full suite matches the 21-failure baseline.

---
*Phase: 07-snapeda-and-samacsys-adapters*
*Completed: 2026-10-23*
