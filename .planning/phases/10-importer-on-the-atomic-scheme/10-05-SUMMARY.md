---
phase: 10-importer-on-the-atomic-scheme
plan: 05
subsystem: importer
tags: [kicad, footprint, pitch, ipc-name, descr, tags, sexpr]

requires:
  - phase: 10-importer-on-the-atomic-scheme
    provides: plan 10-01 test layering registration (importer.footprint_text) and the Atomic_ test fixtures
provides:
  - "importer/footprint_text.py: FootprintFacts, pad_centres, pitch_mm, body_mm, package_family, vendor_texts, footprint_facts, ipc_name, describe, generated_tags"
  - "kicad_files.footprint_text_node and footprint_text_edit: span-exact descr/tags replace or insert for footprint and legacy module roots"
affects: [10-planner, 10-migration, FLD-03 preview and install]

actuals:
  tokens: 14500
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Facts that cannot be computed or read are None and are left out of the sentence and tags (D-28)"
    - "Text nodes are written through one zero-width or single-token Edit and sexpr.apply_edits"

key-files:
  created:
    - kicad_lib_manager/importer/footprint_text.py
    - tests/test_footprint_text.py
  modified:
    - kicad_lib_manager/kicad_files.py
    - tests/test_kicad_files_write.py

key-decisions:
  - "Pads stacked on one centre count once for the pitch, and a footprint with more than 2000 distinct pad centres gets no pitch (bounds the quadratic scan, T-10-10)"
  - "A graphic outline with no area (a single Fab line) does not count as a Fab outline, so the courtyard fallback still applies"
  - "The footprint's own descr and tags are searched for the package family before the texts the caller passes in"
  - "A (descr) or (tags) node with no value token is replaced whole, so the file never holds two of them"

requirements-completed: [FLD-03]

coverage:
  - id: D1
    description: "Pitch from pad centres: smallest repeated nearest-neighbour distance at 0.01 mm, unnumbered and np_thru_hole pads ignored"
    requirement: FLD-03
    verification:
      - kind: unit
        ref: "tests/test_footprint_text.py#test_ul_footprint_facts"
        status: pass
      - kind: unit
        ref: "tests/test_footprint_text.py#test_pad_centres_skip_a_numbered_hole_and_an_empty_number"
        status: pass
      - kind: unit
        ref: "tests/test_footprint_text.py#test_real_samacsys_legacy_module_footprint"
        status: pass
    human_judgment: false
  - id: D2
    description: "Body size from the F.Fab outline, courtyard only without a Fab outline"
    requirement: FLD-03
    verification:
      - kind: unit
        ref: "tests/test_footprint_text.py#test_body_prefers_the_fab_outline_over_the_courtyard"
        status: pass
      - kind: unit
        ref: "tests/test_footprint_text.py#test_stock_soic8"
        status: pass
    human_judgment: false
  - id: D3
    description: "Package family read only from text against a closed list, pin count from the text"
    requirement: FLD-03
    verification:
      - kind: unit
        ref: "tests/test_footprint_text.py#test_family_from_compact_text"
        status: pass
      - kind: unit
        ref: "tests/test_footprint_text.py#test_family_unknown"
        status: pass
    human_judgment: false
  - id: D4
    description: "One plain sentence, IPC-style name and tags that leave out what is unknown"
    requirement: FLD-03
    verification:
      - kind: unit
        ref: "tests/test_footprint_text.py#test_ul_footprint_sentence_and_tags"
        status: pass
      - kind: unit
        ref: "tests/test_footprint_text.py#test_describe_leaves_out_the_missing_body"
        status: pass
    human_judgment: false
  - id: D5
    description: "descr and tags written into a vendor footprint (footprint and legacy module roots) and loaded by kicad-cli 10"
    requirement: FLD-03
    verification:
      - kind: integration
        ref: "tests/test_kicad_files_write.py#test_real_cli_loads_the_ul_footprint_with_inserted_descr_and_tags"
        status: pass
      - kind: integration
        ref: "tests/test_kicad_files_write.py#test_real_cli_loads_the_legacy_module_with_inserted_descr_and_tags"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-27
status: complete
plan_head_before: b4f956441ef5cab68b1bc6efe104c5a92c09da70
plan_head_after: 8d2391f0d98c0fe04c3b9a886c46253a6b9bc39d
---

# Phase 10 Plan 05: Footprint facts, description and tags Summary

**Footprint pitch, body and package family worked out from geometry and text, turned into "WSON-6 2.1x2.1 mm, 0.65 mm pitch, TI DQK0006B" with tags, and written into vendor footprints by a span-exact descr/tags edit that kicad-cli 10 loads on both footprint and legacy module roots**

## Performance

- **Duration:** about 25 min
- **Tasks:** 2
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `importer/footprint_text.py` (Qt-free) reads pad centres, pitch, body box and package family and builds the sentence, IPC-style name and tags; unknown facts are left out, nothing is guessed.
- `kicad_files.footprint_text_node` / `footprint_text_edit` replace a `(descr ...)` or `(tags ...)` value token, or insert the node after the `(layer ...)` child in the file's own indent and line ending (same line for the legacy `(module "X" (layer F.Cu) ...)` shape).
- Measured results hold on the real samples: DQK0006B 8 pads, 0.65, 2.1 x 2.1; ATXK-H14 pitch 1; RS3 legacy module 2.54 and 21.8 x 9.2; SnapEDA GCT 0.5; stock Texas_DQK 0.65, 2.0 x 2.0, WSON-6; stock SOIC-8 1.27, 3.9 x 4.9.

## Task Commits

1. **Task 1 (tracer): UL DQK0006B footprint to facts, sentence and tags, written back and loaded by kicad-cli** - `9fb4406` (feat)
2. **Task 2 (tdd): geometry and text rules on every real footprint, legacy module root, unknown cases** - `8d2391f` (test)

**Plan metadata:** the docs commit that adds this SUMMARY.

## Files Created/Modified

- `kicad_lib_manager/importer/footprint_text.py` - facts, pitch, body, family, sentence, IPC-style name, tags
- `kicad_lib_manager/kicad_files.py` - `footprint_text_node`, `footprint_text_edit`
- `tests/test_footprint_text.py` - geometry, family, sentence and tag tests on built, sample and stock footprints
- `tests/test_kicad_files_write.py` - descr/tags edit tests (both roots, CRLF, tabs, round trip) and two `kicad_cli` load tests

## Decisions Made

- Pads on the same centre count once for the pitch; more than 2000 distinct centres gives no pitch. Any two or more distinct pads always have a mutually nearest pair, so "no repeated distance" can only arise from fewer than two distinct centres.
- A graphic outline with zero width or height is not an outline: a lone Fab line falls through to the courtyard.
- Family search order: the footprint's own descr, then its tags, then the texts passed in (matched official footprint descr and name).
- The SnapEDA GCT footprint has 22 pad blocks but 20 numbered pads (2 are np_thru_hole mounting holes), so `pads == 20`; the research table counted all blocks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Bounded the pitch scan and guarded degenerate input**
- **Found during:** Task 1 (threat T-10-10)
- **Issue:** The research pitch code is quadratic in pads; the node cap alone allows far more pads than a quadratic scan can handle, and pads stacked on one centre would give a pitch of 0.
- **Fix:** Stacked centres are deduplicated, zero distances never count, and more than 2000 distinct centres gives `None`.
- **Files modified:** kicad_lib_manager/importer/footprint_text.py
- **Verification:** `test_pitch_ignores_pads_on_the_same_centre`, `test_pitch_gives_up_on_a_huge_pad_count`
- **Committed in:** 9fb4406

**2. [Rule 2 - Missing critical] A value-less `(descr)` / `(tags)` node is replaced whole**
- **Found during:** Task 1 (threat T-10-11)
- **Issue:** Inserting beside an existing empty node would leave two descr nodes in the file.
- **Fix:** `footprint_text_edit` replaces the empty node's span.
- **Verification:** `test_text_node_without_a_value_is_replaced_whole`
- **Committed in:** 9fb4406

---

**Total deviations:** 2 auto-fixed (both Rule 2, threat-model mitigations)
**Impact on plan:** Both stay inside the plan's files and make T-10-10 and T-10-11 hold for hostile input. No scope creep.

## TDD Gate Compliance

Task 2 is `tdd="true"`, but Task 1 is a tracer that, by the plan's own design, delivers the whole `footprint_text` module and the edit primitive end to end. When the Task 2 behavior tests were written, every implementation behavior already existed, so there was no RED state for the implementation.

- RED: the new Task 2 tests ran against the tracer's implementation; 3 failed, all on wrong test expectations rather than missing behavior (ATXK sentence starting with the body box, SnapEDA pad count 20 not 22 because of two mounting holes, stock SOIC-8 family not in its own text "SOIC, 8 Pin"). The expectations were corrected against the measured facts; no implementation change was needed.
- GREEN: no separate `feat` commit for Task 2; the implementation commit is the tracer commit `9fb4406`. The `test(10-05)` commit `8d2391f` follows it, so the strict test-before-feat order is not met for Task 2. Flagged here as the plan-structure consequence, not hidden.
- REFACTOR: none.

## Issues Encountered

- The licence-restricted samples are not in the worktree; they were copied from the orchestrator checkout into the gitignored `downloaded_examples/` for verification and are not staged.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The planner can call `footprint_facts`, `describe`, `generated_tags` and `footprint_text_edit` (descr first, then tags in one `apply_edits` call) and merge vendor tags through `keywords.merge_words`.
- `importer.footprint_text` was already registered in `tests/test_importer_layering.py` ALLOWED (`{"kicad_files", "sexpr"}`); `tests/test_layering.py` is unchanged. Full `-m "not wurth"` suite is left to the orchestrator's post-merge run.

## Self-Check: PASSED

- `kicad_lib_manager/importer/footprint_text.py`, `tests/test_footprint_text.py` exist; commits `9fb4406` and `8d2391f` are in the branch history.
- `pytest tests/test_footprint_text.py tests/test_kicad_files_write.py tests/test_layering.py tests/test_importer_layering.py`: 147 passed, 0 skipped; `-m kicad_cli` on the two files: 2 passed.

---
*Phase: 10-importer-on-the-atomic-scheme*
*Completed: 2026-10-27*
