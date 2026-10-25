---
phase: 02-hardening-existing-code
plan: 02
subsystem: gui-widget
tags: [pyside6, library-table, rel_path, nickname-collision, selection, select-all]
requires:
  - phase: 02-09
    provides: SymbolLibrary.collision_peers / FootprintLibrary.collision_peers filled by the scan
provides:
  - LibraryTableWidget._sym_items and _fp_items keyed by rel_path
  - populate() that renders selected flags and never recomputes footprint selection
  - Footprint sync scoped to the selected symbols of the same source
  - Collision mark (status "Collision", orange, warning icon, peer tooltip) for symbols and footprints
  - Mutual exclusion of same-nickname libraries, including Select All (Custom wins)
affects: [02-05, 02-06]
tech-stack:
  added: []
  patterns:
    - "Widget identity is rel_path; nickname is display text only and is never edited"
    - "Programmatic check-state changes run under self._updating with try/finally restore"
key-files:
  created: []
  modified:
    - kicad_lib_manager/widgets/library_table.py
    - tests/test_library_table_widget.py
key-decisions:
  - "Peer sources are synced before the changed source so a footprint released by a displaced peer symbol is free for the newly checked library"
  - "Select All first resets every symbol and footprint, then checks in tree order, so Custom wins regardless of the previous selection and a repeat call is identical"
  - "Select All leaves group headers to Qt auto-tristate; a source holding an unchecked collided library shows PartiallyChecked"
requirements-completed: [HARD-07, HARD-08]
duration: 20 min
completed: 2026-10-19
status: complete
commits: 4
plan_head_before: eedf779fdf8760d400048a6ef448634753202746
plan_head_after: ba55eb8a9bf6ec28b9710b9441f1779882e4c97e
actuals:
  tokens: 16000
  tasks: 2
  commits: 4
coverage:
  - id: D1
    description: "Symbol and footprint items are keyed by rel_path, so same-nickname libraries in Custom and WurthElektronik are two items with separate check states"
    requirement: HARD-08
    verification:
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_same_nickname_footprints_get_separate_items"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_same_nickname_symbols_get_separate_items"
        status: pass
    human_judgment: false
  - id: D2
    description: "populate() keeps the selected flags it is given, including a footprint no symbol references; footprint sync is scoped to the symbols of the same source"
    requirement: HARD-07
    verification:
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_populate_keeps_selected_footprint_that_no_symbol_references"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_custom_symbol_drives_only_the_custom_footprint_of_the_same_nickname"
        status: pass
    human_judgment: false
  - id: D3
    description: "Checking a collided library unchecks its peers (symbols and footprints), and Select All deterministically prefers Custom"
    requirement: HARD-08
    verification:
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_checking_a_collided_symbol_unchecks_its_peer"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_select_all_prefers_custom_for_collided_pairs"
        status: pass
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_select_all_twice_gives_the_same_selection"
        status: pass
    human_judgment: false
  - id: D4
    description: "Collided libraries are visibly marked: status Collision, orange text, warning icon, tooltip naming the peers"
    requirement: HARD-08
    verification:
      - kind: unit
        ref: "tests/test_library_table_widget.py#test_collided_symbol_is_marked_with_collision_status_and_tooltip"
        status: pass
    human_judgment: true
    rationale: "Tests assert the colour, icon and tooltip text; whether the mark reads clearly in the real window is a visual judgment"
---

# Phase 2 Plan 02: Library Tree rel_path Identity and Collision Exclusion Summary

**The library tree now identifies every symbol and footprint by `rel_path`, populate renders selection without recomputing it, and same-nickname libraries are marked "Collision" and can never both be selected, with Select All preferring Custom.**

## Performance

- **Duration:** about 20 min
- **Completed:** 2026-10-19
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `_sym_items` (new) and `_fp_items` are keyed by `rel_path`; two libraries named `Same` in Custom and WurthElektronik both appear and keep separate check states.
- `populate()` no longer calls `_sync_footprint_selection`. It renders `lib.selected` and writes no model flag, which is what plan 02-06 needs to restore selection after a rescan (HARD-07).
- `_sync_footprint_selection(source)` builds `needed` only from selected symbols of that source and skips a footprint while a collided peer footprint is selected.
- Collided libraries get status "Collision" (symbol column 3, footprint column 2), the warning icon, `#CC7700` on every column and a tooltip `Same nickname as <peers>; only one can be selected` (plus "; Missing FP" for a symbol with missing footprints). Item text stays the nickname.
- `_peer_selected` and `_uncheck_peers` implement mutual exclusion for symbols (item, group-header and model flag) and footprints. Checking a symbol syncs displaced peer sources first, then its own source.
- `select_all` resets everything, then checks symbols in sorted-source tree order only while no peer is selected, then syncs footprints per sorted source. `deselect_all` clears all.

## Task Commits

1. **Task 1: rel_path-keyed items, populate without re-sync, source-scoped sync**: RED `4de6363` (test), GREEN `ca14248` (feat)
2. **Task 2: collision mark and mutual exclusion**: RED `976a004` (test), GREEN `ba55eb8` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `kicad_lib_manager/widgets/library_table.py` - rel_path-keyed items, no-resync populate, source-scoped sync, collision mark, `_peer_selected`, `_uncheck_peers`, Select All ordering
- `tests/test_library_table_widget.py` - helpers by rel_path; 24 new offscreen tests on top of the 5 existing ones (29 total)

## TDD Gate Compliance

| Task | RED | GREEN |
|------|-----|-------|
| 1 | `4de6363` test(02-02) | `ca14248` feat(02-02) |
| 2 | `976a004` test(02-02) | `ba55eb8` feat(02-02) |

RED evidence, task 1: 10 of 13 tests failed. The two migrated existing tests and the new tests fail on `AttributeError` for the missing `_sym_items` or on `len(_fp_items)`/KeyError assertions for the rel_path keying; the no-resync and source-scope tests fail for the same missing keying. These are interface-level failures because the planned behaviour is a change of item identity. Task 2: 8 of 17 new tests failed on assertions for the planned behaviour ("OK" instead of "Collision", `(True, True)` instead of `(True, False)`, two same-source peers both selected, Wurth `Same` selected after Select All). The rest pass against the old code because they pin behaviour that must not regress (unchecking, deselect all, no renaming). The classifier `gsd_run check tdd-red-evidence` was not run (no record file was produced); semantic assessment was done by reading pytest output. No REFACTOR commit was needed.

## Decisions Made

- Peer sources are synced before the changed source. With the order written in the plan (changed source first) a footprint wanted by the newly checked library would still see the displaced peer footprint as selected and stay unchecked.
- Select All resets symbols and footprints before checking, so "Custom wins" holds even when a Wurth peer was selected beforehand, and repeating the call is idempotent.
- Select All sets only child items and leaves group headers to Qt auto-tristate (verified: Custom group Checked, Wurth group PartiallyChecked when its `Same` is skipped).

## Deviations from Plan

None of Rules 1-4 applied. Two small choices go beyond the plan text, both inside its stated behaviour:

- `_uncheck_peers` and `_sync_footprint_selection` restore the previous `_updating` value in a `finally` block instead of hard-setting it to False, to keep T-02-06 (no stuck guard) true even on exceptions.
- Task 2's GREEN commit also contains one extra test (`test_select_all_group_headers_reflect_the_collision_choice`) added after the RED commit.

Verification commands in the plan use `./env/Scripts/python.exe`, which does not exist in the worktree (`env/` is git-ignored); the main checkout venv was used by absolute path instead.

## Known Stubs

None.

## Threat Flags

None. The plan's T-02-05 and T-02-06 mitigations are implemented and covered by tests (at most one selected per collided pair after every operation; `_updating is False` afterwards).

## Issues Encountered

None. Full suite in the worktree: 431 passed, 7 skipped (submodule-dependent tests skip by design).

## Edge-probe note carried forward

Selection identity is `rel_path`: a library moved or renamed on disk between scans is a new library (unchecked, D-04). Not handled here.

## Next Phase Readiness

Plan 02-06 can re-apply selection after a rescan through `populate()` without it being overwritten. Plan 02-06 still owns the startup footprint selection (removed from `populate()` here) and the D-01 trim of tables holding both peers.

## Self-Check: PASSED

- `kicad_lib_manager/widgets/library_table.py` and `tests/test_library_table_widget.py` exist and are committed.
- Commits `4de6363`, `ca14248`, `976a004`, `ba55eb8` are ancestors of HEAD.
- Acceptance criteria re-run: `_sym_items` appears 3 times; `_fp_items[lib.rel_path]` present; `populate` contains 0 `_sync_footprint_selection` calls; `lib.source == source` in the sync; `_uncheck_peers`, `_peer_selected`, `"Collision"`, `setToolTip` present; 0 assignments to `.nickname`; `pytest tests/test_library_table_widget.py` 29 passed; collision/exclusive/select_all subset 10 passed; full `pytest -q` 431 passed, 7 skipped.
