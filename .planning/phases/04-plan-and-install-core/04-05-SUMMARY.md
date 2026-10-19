---
phase: 04-plan-and-install-core
plan: 05
subsystem: importer
tags: [kicad, verification, pin-pad, name-collision, bytes-prefilter, pytest]

requires:
  - phase: 04-plan-and-install-core
    provides: "04-01 InstallPlan/ToolContext contract and the tracer verify_install; 04-02 installfixtures builders"
provides:
  - "verify_install with every D-18 hard check, each proven on a broken hand-built plan and read back from disk"
  - "POST-04 pin/pad soft check (symbol_pin_numbers, footprint_pad_numbers, pin_pad_issues) with extends and empty-pad handling"
  - "POST-03 find_name_elsewhere and symbol_search_dirs, importable on its own for a Phase 5 preview-time call"
affects: [04-06, 04-07, 04-08, 04-09, 04-10, 05-preview-and-install-ui]

actuals:
  tokens: 9000
  tasks: 3
  commits: 6

plan_head_before: 6a9588bab168f6ebc1d6fe4f9f316982e1c4d047
plan_head_after: 522ce2eb8fa1ac07b7270f08efe78197086565cc

tech-stack:
  added: []
  patterns:
    - "Exact-case os.listdir name sets for every existence check; no Path.exists() in verify.py"
    - "Bytes-substring prefilter then compiled multiline depth-1 regex; libraries are never parsed for the name search"
    - "Soft checks return WARNING Issues and are appended after the hard checks; they never block"

key-files:
  created:
    - tests/test_install_verify.py
  modified:
    - kicad_lib_manager/importer/verify.py

key-decisions:
  - "verify_install collects every failure and de-duplicates identical (code, text) pairs, so one unparsable footprint is reported once even though both the re-parse and the link walk see it"
  - "The Footprint field must equal <plan.library>:<plan.linked_footprint> exactly before it is resolved; a field naming another library is verify.link_unresolved, not a skipped check"
  - "Link, model and pin/pad checks are skipped when plan.linked_footprint is None or the unit symbol is missing or duplicated, since there is no single Footprint field to follow"
  - "Symbol pins are collected by walking the whole symbol node (all units and body styles) and each extends ancestor with a seen-set, instead of the plan's suggested kicad_files.symbol_unit helper, which does not exist"
  - "Only WurthElektronik is searched recursively; Custom/Symbols, the KiCad stock folder and extra folders are flat listings"

patterns-established:
  - "Hand-built InstallPlan over a tmp_path Custom/ tree (make_plan in tests/test_install_verify.py) for verify tests, with no dependence on the Custom submodule"

requirements-completed: [INST-08, POST-03, POST-04]

coverage:
  - id: D1
    description: "Every D-18 hard check (parse, symbol missing or duplicated, exact-case link, internal footprint name, wrong library, model case and path) fails on its own broken case and reads disk, not the plan's bytes"
    requirement: INST-08
    verification:
      - kind: unit
        ref: "tests/test_install_verify.py -k hard (14 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Pin/pad mismatch is one WARNING in either direction against the footprint actually linked, with extends children, empty pads and natural sort handled"
    requirement: POST-04
    verification:
      - kind: unit
        ref: "tests/test_install_verify.py -k pin_pad (14 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Name-elsewhere WARNING over other Custom libraries, WurthElektronik and KiCad stock without parsing; real stock search takes about 0.3 s"
    requirement: POST-03
    verification:
      - kind: unit
        ref: "tests/test_install_verify.py -k elsewhere (15 tests, including test_elsewhere_real_stock and test_elsewhere_no_full_parse)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Pin/pad warnings read well and are the right amount of noise for real vendor parts"
    requirement: POST-04
    verification: []
    human_judgment: true
    rationale: "Wording and signal-to-noise of the warning text is a UX judgment; KiCad 10 stacked pin numbers such as [1-3] are compared literally (assumption A4) and may warn falsely"
status: complete
---

# Phase 4 Plan 05: Post-install verification Summary

**verify_install now runs every D-18 hard check from disk with exact-case listings, then adds a pin/pad WARNING (extends-aware) and a name-elsewhere WARNING that scans KiCad's 236 MB of stock symbols in about 0.3 s by bytes prefilter instead of parsing.**

## Performance

- **Duration:** about 30 min
- **Started:** 2026-10-19T22:20:00Z (approx.)
- **Completed:** 2026-10-19T22:50:03Z
- **Tasks:** 3 (each as a RED test commit then a GREEN feat commit)
- **Files modified:** 2 (`kicad_lib_manager/importer/verify.py`, `tests/test_install_verify.py`)

## Accomplishments

- Hard checks: re-parse every written `symbol_lib` and `footprint` op file, require each unit symbol exactly once (`verify.symbol_missing` / new `verify.symbol_duplicated`), require the Footprint field to be exactly `<Lib>:<FP>` and to resolve through an exact-case `os.listdir` to a file whose internal name matches, and require the first model path to be `${CUSTOM_3DMODEL_DIR}/<file>` with `<file>` in an exact-case listing of `3DModels`. All failures are collected, none stops the run.
- POST-04: `symbol_pin_numbers` (all units, `extends` chain with a cycle guard), `footprint_pad_numbers` (direct pads, empty numbers ignored, unquoted atoms accepted), `pin_pad_issues` (one WARNING listing both directions, natural sort so 2 comes before 10 and A2 before A10). Run against the footprint read back from disk through the written Footprint field, which also covers a skipped footprint.
- POST-03: `find_name_elsewhere` and `symbol_search_dirs`. Needle is `("(symbol " + quote(name)).encode()`; a depth-1 multiline regex confirms a hit (tab or one to two spaces of indent, or directly after a one-line `(kicad_symbol_lib` header). Real KiCad 9 stock search for `R` returned `KiCad:Device` in 0.33 s. The test patches every parser to fail and still passes on a 2 MB library.
- Sanity run (not committed): the real Ultra Librarian CSD85301Q2 sample installed into a synthetic `IC_Battery_Charger_TI` layout with the KiCad stock folder attached; `apply_plan` succeeded and `verify_install` returned no issues.

## Task Commits

1. **Task 1 RED:** `e17840a` test(04-05): add failing hard-check tests for verify_install
2. **Task 1 GREEN:** `c451eae` feat(04-05): complete hard post-install checks in verify_install
3. **Task 2 RED:** `215aad7` test(04-05): add failing pin/pad soft-check tests
4. **Task 2 GREEN:** `a86c784` feat(04-05): warn when symbol pins and footprint pads differ
5. **Task 3 RED:** `b38bace` test(04-05): add failing name-elsewhere tests
6. **Task 3 GREEN:** `522ce2e` feat(04-05): warn when a part name already exists in another library

## Files Created/Modified

- `kicad_lib_manager/importer/verify.py` - completed `verify_install`; new `symbol_pin_numbers`, `footprint_pad_numbers`, `pin_pad_issues`, `symbol_search_dirs`, `find_name_elsewhere`
- `tests/test_install_verify.py` - 43 tests: `test_hard_*` (14), `test_pin_pad_*` (14), `test_elsewhere_*` (15)

## Decisions Made

See `key-decisions` above. The most consequential: soft warnings are appended to the same list `verify_install` returns, so callers that want only blocking failures must filter on `Severity.ERROR` (the applier already does).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `kicad_files.symbol_unit` does not exist**
- **Found during:** Task 2
- **Issue:** The plan says to use `kicad_files.symbol_unit` to walk the symbol and its `extends` ancestors. No such helper exists, and 04-04 owns `kicad_files.py` in parallel.
- **Fix:** Kept the walk local to `verify.py` (`_collect_pin_numbers`, `_extends_parent`), as the orchestrator instructions allow. It walks the whole top-level symbol node, so every unit and body style is covered.
- **Files modified:** `kicad_lib_manager/importer/verify.py`
- **Commit:** `a86c784`

**2. [Rule 1 - Test correction] Tests written for the RED step had one wrong expectation**
- **Found during:** Task 1 RED
- **Issue:** `test_hard_collects_every_failure` used `symbol_names=("PART", "NOPE")`, but `symbol_name` is the last entry (the derived symbol), so the link check ran on the missing symbol.
- **Fix:** Reordered to `("NOPE", "PART")` before the RED commit.
- **Commit:** `e17840a`

**3. [Plan wording] Sub-symbol test uses the exact nested name, not only `_1_1`**
- **Found during:** Task 3
- **Issue:** The needle includes the closing quote, so `"CSD85301Q2_1_1"` never hits the prefilter at all; the depth-1 regex is only reached for an exact name declared at depth 2.
- **Fix:** `test_elsewhere_sub_symbol_not_counted` covers both the `_1_1` name and the exact name nested at depth 2 (space and tab indent), so the regex's depth rule is genuinely exercised.
- **Commit:** `b38bace`

**Total deviations:** 3 (1 blocking helper kept local, 1 test correction, 1 test strengthened). **Impact:** none on the contract; all plan behaviors and acceptance criteria hold.

## Issues Encountered

- **Applier drops verify WARNINGs.** `applier.apply_plan` keeps only `Severity.ERROR` items from `verify_install` and builds the success list from `plan.issues`, so on a successful install the new `verify.pin_pad_mismatch` and `verify.name_elsewhere` warnings are computed but not returned in `InstallResult.issues`. `applier.py` is outside this plan's `files_modified`, so it was left alone. A later plan (04-06 to 04-10, or Phase 5) should append the non-error verify issues to the result, or call `find_name_elsewhere` at preview time as 04-05 intended.
- `tests/test_install_e2e.py` and the other `custom_copy` tests skip in this worktree (Custom submodule not checked out, expected). The synthetic UL sanity run above stands in for them; the orchestrator should run the full suite on the merged tree where Custom is initialised.

## Known Stubs

None.

## Threat Flags

None. No new network endpoint, auth path or trust boundary beyond the plan's threat model (T-04-12 mitigated by the prefilter and the no-parse test, T-04-13 mitigated by exact-case listings and zero `.exists()` calls).

## Next Phase Readiness

- `find_name_elsewhere(names, layout, exclude_library=..., tools=...)` and `symbol_search_dirs` are importable without a plan, ready for Phase 5 preview.
- See the applier warning-drop item above before the GUI relies on these warnings reaching the user.

## Self-Check: PASSED

- `tests/test_install_verify.py`: FOUND; `kicad_lib_manager/importer/verify.py`: FOUND
- Commits `e17840a`, `c451eae`, `215aad7`, `a86c784`, `b38bace`, `522ce2e` are ancestors of HEAD
- `pytest tests/test_install_verify.py -k hard / pin_pad / elsewhere`: 14 / 14 / 15 passed; `-rs` shows no skip for `test_elsewhere_real_stock`
- `pytest tests/test_install_verify.py tests/test_install_e2e.py tests/test_importer_layering.py`: 57 passed, 1 skipped (Custom submodule)
- `pytest -q` (whole suite): 1025 passed, 20 skipped (submodules, symlink privilege)
- `grep -v '^\s*#' verify.py | grep -c '\.exists()'`: 0
