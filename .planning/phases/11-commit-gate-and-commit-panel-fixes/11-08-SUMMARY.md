---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 08
subsystem: git-commit-step
tags: [atomic-gate, commit-probe, check-again, rebaseline, git]

requires:
  - phase: 11-commit-gate-and-commit-panel-fixes
    provides: "11-02/11-05 commit_gate.run_gate; 11-03 rebaseline and CommitFile.installed/note; 11-06 stale/identical probe fields; 11-07 manual command"
provides:
  - "probe_commit(..., kicad_fp_dir=None, cancelled=None) runs the atomic gate and returns state 'gated' with CommitProbe.gate attached"
  - "_precheck / run_commit(kicad_fp_dir=None) run the gate again before the first git write and refuse with one commit.atomic ERROR"
  - "recheck_commit(cplan, *, git, kicad_fp_dir, cancelled) -> (new plan, probe): the service behind Check again"
  - "changed_diff(cplan, rel, *, git) -> ContentText: installed vs now, or HEAD vs now for an added file"
affects: [11-10 panel, 11-11 dialog, 11-12 fix files, 11-13 dialog]

plan_head_before: bef98140c5dbe961e9ed26da3b574f4fb7ca8c62
plan_head_after: 631f7e528213923a9fd083ddd9608cd8b8484099

actuals:
  tokens: 14000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Gate runs twice (probe for the early answer, _precheck for the time-of-use check); both are read-only"
    - "Check again = rebaseline(plan) then probe the new plan; the install-time bytes stay in CommitFile.installed"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/commit_step.py
    - tests/test_commit_step.py
    - tests/gitfixtures.py

key-decisions:
  - "The gate runs in probe_commit only on the named-branch (ready) path; offer_switch, refused and unavailable probes skip it, as the plan says. The post-switch re-probe runs it."
  - "A stale file and a broken rule can both hold: the probe reason joins 'N parts break the atomic rule.' and the stale text with a space"
  - "The stale refusal at the click reuses stale_text, so the probe strip and the click say the same thing and point to Check again"
  - "changed_diff keeps its own capped read built on content.MAX_READ instead of importing content's private helper"

requirements-completed: [GIT-06, REV-10]

coverage:
  - id: D1
    description: "A new or changed Atomic_ part that breaks a rule makes the probe 'gated' with reason 'N parts break the atomic rule.' and the GateResult attached, before any click"
    requirement: GIT-06
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_gated_and_click_refused_for_failing_part"
        status: pass
    human_judgment: false
  - id: D2
    description: "The click runs the gate again and refuses with one ERROR commit.atomic naming each 'Library / Part: text'; no add, reset or commit runs and no HEAD moves"
    requirement: GIT-06
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_gated_and_click_refused_for_failing_part"
        status: pass
    human_judgment: false
  - id: D3
    description: "Old failures only add WARNING lines; the probe stays ready and the commit goes ahead"
    requirement: GIT-06
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_probe_old_failure_stays_ready_and_commits"
        status: pass
    human_judgment: false
  - id: D4
    description: "A stale refusal at the click names the files and says 'Click Check again', not 'commit by hand'"
    requirement: REV-10
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_precheck_stale_points_to_check_again"
        status: pass
    human_judgment: false
  - id: D5
    description: "Check again re-baselines changed files (note 'changed'), re-runs the gate on the new content, writes nothing, and a change after it is refused again at the click"
    requirement: REV-10
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_recheck_rebaselines_then_commits"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_recheck_gate_runs_on_new_content"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_change_after_recheck_refused_again"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_recheck_writes_nothing"
        status: pass
    human_judgment: false
  - id: D6
    description: "changed_diff shows installed against now for a changed file (binary summary for a model) and HEAD against now for a file a fix added"
    requirement: REV-10
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_changed_diff_text_file"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_changed_diff_model_is_binary"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_changed_diff_added_file_shows_head_against_now"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-10-30
status: complete
---

# Phase 11 Plan 08: Gate in the commit step and Check again Summary

**The atomic gate now runs in `probe_commit` (state "gated" before any click) and again in `_precheck` right before the first git write (one `commit.atomic` ERROR, nothing written), and `recheck_commit` / `changed_diff` give the dialog its Check again service and the "changed since install" diff.**

## Performance

- **Duration:** about 45 min (most of it waiting on the git-heavy test files, about 8 min per full run)
- **Tasks:** 2
- **Files modified:** 3 (1 source, 2 test)

## Accomplishments

- `probe_commit` gained `kicad_fp_dir`. On a named branch it runs `commit_gate.run_gate`, adds `gate_issues` to the probe's issues, attaches `gate`, and sets state "gated" when a file is stale or the gate refuses. The reason joins `"N part(s) break(s) the atomic rule."` and the stale text.
- `_precheck` / `run_commit` gained `kicad_fp_dir`. After the parent check and before `tracked_paths` the gate runs again; a refusal returns `Not committed: <summary>.` plus one `Library / Part: text` line per broken rule. The stale refusal now reuses `stale_text` ("Click Check again").
- `recheck_commit` = `rebaseline(cplan)` then `probe_commit(new, ...)`; it never writes. `changed_diff` follows `pre_import_diff`: installed vs now for a changed file, HEAD vs now for an added file, size and SHA-256 for a model or a file whose installed bytes are not kept.

## Task Commits

1. **Task 1: gate in the probe and at the click (tracer)** - `6aa009b` (feat)
2. **Task 2: Check again and changed-file diff** - RED `6bc2a81` (test), GREEN `631f7e5` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `kicad_lib_manager/importer/commit_step.py` - gate in `probe_commit` and `_precheck`, `kicad_fp_dir` keywords, `recheck_commit`, `changed_diff`, `_read_now`
- `tests/test_commit_step.py` - gate probe/click tests, recheck tests, changed_diff tests
- `tests/gitfixtures.py` - `import_files` now records `installed` (the written bytes) for non-model files, like the real install

## Decisions Made

See `key-decisions` above. The probe still passes the gate's `problems` (an unreadable library) through the same refusal path as a blocking failure, so such a library also gives "gated".

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `import_files` fixture did not record `installed`**
- **Found during:** Task 2 (writing the `changed_diff` text-file test)
- **Issue:** the test fixture built `CommitFile` without `installed`, so a text file could never show an "as installed" diff; the real `build_commit_plan` sets it from `op.data`.
- **Fix:** `import_files` sets `installed=data` for non-model files and `None` for models.
- **Files modified:** `tests/gitfixtures.py`
- **Verification:** all 239 tests of the plan verification pass
- **Committed in:** `6bc2a81`

**Total deviations:** 1 auto-fixed (1 blocking test-fixture gap). **Impact:** none on production behavior.

## Issues Encountered

None. No existing test needed a fixture change: the gate did not refuse any existing fixture symbol.

## Threat Flags

None. T-11-18 mitigated: the gate runs again in `_precheck` immediately before the first write, and `test_change_after_recheck_refused_again` proves a change after Check again is refused. T-11-20 accepted as planned.

## Known Stubs

None. `import_dialog.py` still calls `core.probe_commit(cp, cancelled=...)` and `run_commit(...)` without `kicad_fp_dir`, so the gate there runs without KiCad's default footprint folder until plans 11-10/11-11/11-13 pass it. This is out of scope for this plan (it names only `commit_step.py` and its tests).

## TDD Gate Compliance

Task 1 is a tracer (single feat commit, its automated verify re-run end to end before expansion: passed). Task 2: RED `6bc2a81` (nine of the new tests failed with `AttributeError: module 'kicad_lib_manager.importer.commit_step' has no attribute 'recheck_commit'` / `'changed_diff'`; the target tests executed and failed on the missing function, not on setup or import) then GREEN `631f7e5` (13 passed in `-k "recheck or changed_diff or stale"`). The machine RED classifier (`gsd_run check tdd-red-evidence`) was not run: `gsd_run` is not available in this worktree.

## Verification

- `pytest tests/test_commit_step.py tests/test_commit_gate.py tests/test_commit_plan.py tests/test_gitops.py tests/test_importer_layering.py tests/test_layering.py -q`: 239 passed.
- The wave-check files `test_commit_panel.py` and `test_import_dialog.py` were not run here (the orchestrator runs the full suite after merge).
- `grep -n "commit_gate.run_gate(ctx, cplan"` shows two calls (probe and `_precheck`).

## Next Phase Readiness

Plan 11-10 can read `CommitProbe.gate`; plans 11-11 and 11-13 can call `recheck_commit` and `changed_diff`; plan 11-12 inserts the D-10 added files between `rebaseline` and the probe in `recheck_commit`.

## Self-Check: PASSED

- `kicad_lib_manager/importer/commit_step.py` contains `def recheck_commit` and `def changed_diff`; commits `6aa009b`, `6bc2a81`, `631f7e5` are ancestors of HEAD.

---
*Phase: 11-commit-gate-and-commit-panel-fixes*
*Completed: 2026-10-30*
