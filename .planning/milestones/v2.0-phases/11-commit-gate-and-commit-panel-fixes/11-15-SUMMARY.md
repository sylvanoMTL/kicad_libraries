---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 15
subsystem: importer-commit-gate
tags: [commit-gate, atomic-rule, fail-closed, python, pytest-qt]

requires:
  - phase: 11-commit-gate-and-commit-panel-fixes
    provides: run_gate, GateResult, probe_commit/_precheck and the gated commit panel from plans 11-01..11-13
provides:
  - "Gate fails closed: an unreadable, unparsable or unlistable Atomic_ library refuses a commit that holds footprints or 3D models"
  - "GateResult.unchecked: non-refusing, panel-visible line for a linked part whose link to a committed footprint cannot be followed"
  - "_check_linked_symbols returns a frozen _LinkedFindings value (9 parameters); _move_introduced is the one move helper"
  - "GateResult.notes and the INFO commit.atomic_note line removed; commit_step uses commit_gate.CANCELLED directly"
affects: [11-14 (panel uses GateResult.first_failure, kept), 11-16, 11-17]

actuals:
  tokens: 11000
  tasks: 3
  commits: 6

plan_head_before: d851ab8ffd04e8f1f236844d89a6f63c6b2de226
plan_head_after: ee979bfe277a0783933b9c7ae1d99bee18a34362

tech-stack:
  added: []
  patterns:
    - "Gate helpers return frozen findings values instead of mutating output lists"
    - "One channel (problems) for 'could not be checked', always a refusal; a separate non-refusing unchecked tuple shown through old_notes"

key-files:
  created:
    - tests/test_commit_gate_panel.py
  modified:
    - kicad_lib_manager/importer/commit_gate.py
    - kicad_lib_manager/importer/commit_step.py
    - tests/test_commit_gate.py
    - tests/test_commit_step.py

key-decisions:
  - "Fail closed for unreadable/unparsable/unlistable Atomic_ libraries when footprints or models are committed (owner decision, WR-03); a missing Symbols folder refuses nothing"
  - "An unlistable Symbols folder is worded as a folder (refusal_summary: 'the symbol libraries could not be listed'), never counted as a library"
  - "A link equal to a committed footprint that cannot be followed is shown (GateResult.unchecked) but never refuses; every other unresolved link adds nothing because check_symbol reads footprint files and models only through a resolved link"

patterns-established:
  - "Return a frozen findings dataclass from gate sub-passes; merge in run_gate"

requirements-completed: [GIT-06]

coverage:
  - id: D1
    description: "An unreadable Atomic_ library outside the commit refuses a commit holding footprints or models, from gate to probe, panel and click, with no git write"
    requirement: GIT-06
    verification:
      - kind: integration
        ref: "tests/test_commit_gate_panel.py#test_unreadable_linked_library_refuses_probe_panel_and_click"
        status: pass
      - kind: unit
        ref: "tests/test_commit_gate.py#test_gate_unreadable_outside_library_refuses"
        status: pass
    human_judgment: false
  - id: D2
    description: "An unlistable Custom/Symbols folder refuses with a folder-worded line; a missing folder and a commit with no footprint/model refuse nothing"
    requirement: GIT-06
    verification:
      - kind: unit
        ref: "tests/test_commit_gate.py#test_gate_unlistable_symbols_folder_refuses"
        status: pass
      - kind: unit
        ref: "tests/test_commit_gate.py#test_gate_unreadable_outside_library_ignored_without_linked_files"
        status: pass
    human_judgment: false
  - id: D3
    description: "A linked part whose link to a committed footprint cannot be followed is shown in the panel and logged as WARNING without refusing; other unresolved links add nothing"
    requirement: GIT-06
    verification:
      - kind: integration
        ref: "tests/test_commit_gate_panel.py#test_unchecked_linked_part_shown_in_panel_without_refusing"
        status: pass
      - kind: unit
        ref: "tests/test_commit_gate.py#test_gate_unresolved_link_to_committed_footprint_is_shown"
        status: pass
      - kind: unit
        ref: "tests/test_commit_gate.py#test_gate_unresolved_link_elsewhere_adds_nothing"
        status: pass
    human_judgment: false
  - id: D4
    description: "_check_linked_symbols returns _LinkedFindings (9 parameters), notes channel removed, cancel alias removed, existing gate behaviour unchanged"
    requirement: GIT-06
    verification:
      - kind: unit
        ref: "tests/test_commit_gate.py#test_check_linked_symbols_has_nine_parameters"
        status: pass
      - kind: unit
        ref: "tests/test_commit_gate.py#test_move_introduced_lists_a_part_once"
        status: pass
      - kind: unit
        ref: "tests/test_commit_step.py#test_probe_cancelled_returns_unavailable"
        status: pass
    human_judgment: false

duration: 75min
completed: 2026-10-30
status: complete
---

# Phase 11 Plan 15: Fail-closed linked check Summary

**The commit gate now refuses a commit holding footprints or 3D models when an Atomic_ library that might link them cannot be read, parsed or listed, and shows (without refusing) a linked part whose link to a committed footprint cannot be followed.**

## Performance

- **Duration:** about 75 min (start time was not captured at launch; estimated from the commit and test-run timeline)
- **Completed:** 2026-10-30
- **Tasks:** 3
- **Files modified:** 5 (1 created)

## Accomplishments

- WR-03 fixed as decided: `_check_linked_symbols` turns an unreadable outside library into a `problems` line ("<Lib>: the parts in this library could not be checked against the committed footprints and 3D models (<why>). Fix the library file (check that it opens in KiCad), then click Check again."), so `GateResult.refused` is True, the probe is `gated` ("1 library could not be checked."), the panel shows the line with Check again and no Open Check Atomic Parts, and `run_commit` refuses with one ERROR `commit.atomic` before any `add`, `reset` or `commit`.
- `_atomic_symbol_files` now returns `(names, why)`: a missing `Custom/Symbols` still refuses nothing; any other OSError refuses with a folder line, and `refusal_summary` says "the symbol libraries could not be listed" instead of counting a library.
- IN-02: `_check_linked_symbols(ctx, cplan, kicad_fp_dir, work, footprints, models, committed, listed_old, cancelled)` returns a frozen `_LinkedFindings`; `_move_introduced` is the single place a part listed as old moves to blocking. IN-01 (commit_step part): `CANCELLED_REASON` alias deleted. `GateResult.notes` and the INFO `commit.atomic_note` line are gone. `GateResult.first_failure` is kept for plan 11-14.
- W4 / owner decision 3: `GateResult.unchecked` carries "<Lib> / <Part> was not checked against the committed footprint <Lib:FP> (<reason>)" for a part whose link equals a committed footprint but does not resolve in the work tree. It reaches the panel through `old_notes` (amber label, ready or gated probe) and the log as WARNING `commit.atomic_unchecked`, and never refuses. The module docstring records why every other unresolved link cannot reach a committed file.

## Task Commits

1. **Task 1: unreadable Atomic_ library refuses (WR-03), tracer** - `399f491` (test, RED), `bff3f6b` (feat, GREEN)
2. **Task 2: findings value, notes channel and cancel alias removed (IN-02, IN-01)** - `6aebe7b` (test, RED), `a3960cb` (refactor, GREEN)
3. **Task 3: unchecked line for an unfollowable link to a committed footprint (W4)** - `eb15cbf` (test, RED), `ee979bf` (feat, GREEN)

**Plan metadata:** committed with this SUMMARY (docs).

## TDD notes

- RED evidence, Task 1: `test_gate_unreadable_outside_library_refuses`, `test_gate_unlistable_symbols_folder_refuses` and `test_unreadable_linked_library_refuses_probe_panel_and_click` failed on the planned assertions (problems empty, a note instead; probe state `ready`). `test_gate_unreadable_outside_library_ignored_without_linked_files` passed before the change by design (it pins an existing guard).
- RED evidence, Task 2: `test_gate_texts` (notes field still present), `test_move_introduced_lists_a_part_once` (no such function), `test_check_linked_symbols_has_nine_parameters` (12), `test_probe_cancelled_returns_unavailable` (alias still present).
- RED evidence, Task 3: `GateResult` had no `unchecked`; the unresolved-elsewhere test passed before and after by design (it pins the safety argument).

## Verification

- `tests/test_commit_gate.py tests/test_commit_gate_panel.py tests/test_commit_panel.py` plus the `gate or cancelled or recheck or linked` subset of `tests/test_commit_step.py` and `tests/test_importer_layering.py`: 125 passed (final run, after Task 3).
- Task 2 plan command (`-k "gate or cancelled or recheck or linked or layering"` over the four files): 62 passed.
- The full suite was not run (15 to 27 minutes, outside the plan's targeted commands).
- Acceptance greps: `CANCELLED_REASON` 0 in commit_step.py; `commit.atomic_note` 0 and `notes: tuple` absent in commit_gate.py; `_LinkedFindings`, `_move_introduced`, `first_failure` present; `commit_panel.py` untouched; "fail closed" in the module docstring.

## Deviations from Plan

None in behaviour. Minor notes:

- The "could not be checked against the committed footprints and 3D models" wording is written inline in both messages (not as a shared constant) so the plan's grep finds the library line and the folder line.
- In Task 1 the unlisted-folder path and the library path used the existing output-list parameter renamed from `notes` to `problems`, exactly as the plan allowed; Task 2 replaced it.
- Duration is an estimate: the start time was not recorded at launch.

**Total deviations:** 0 auto-fixed. **Impact:** none.

## Known Stubs

None.

## Threat Flags

None. The change tightens an existing trust boundary (T-11-30, T-11-31 and T-11-36 as planned); no new network, auth or file-access surface.

## Self-Check: PASSED

- tests/test_commit_gate_panel.py, kicad_lib_manager/importer/commit_gate.py, kicad_lib_manager/importer/commit_step.py exist.
- Commits 399f491, bff3f6b, 6aebe7b, a3960cb, eb15cbf, ee979bf are ancestors of HEAD.
