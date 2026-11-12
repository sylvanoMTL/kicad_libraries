---
phase: 12-import-flow-fixes-and-case-sensitive-re-test
plan: 01
subsystem: importer
tags: [case-sensitivity, overwrite, rollback, fsutil, VER-02]
requires: []
provides:
  - "overwrite of a case twin writes into the file already on disk (D-14)"
  - "tests/casefixtures.py case_sensitive_dir: real case-sensitive folder or a stated skip"
  - "tests/test_case_sensitive_install.py: the five VER-02 tests"
affects: [importer planner, import dialog conflict view, tests]
tech-stack:
  added: []
  patterns: ["fsutil file setCaseSensitiveInfo on a fresh tmp folder, probe, skip with reason"]
key-files:
  created:
    - tests/casefixtures.py
    - tests/test_case_sensitive_install.py
  modified:
    - kicad_lib_manager/importer/planner.py
    - kicad_lib_manager/widgets/import_dialog.py
    - tests/test_install_plan.py
    - tests/README.md
key-decisions:
  - "D-14: the spelling already on disk is the write target and the link name; listed_path stays only as undo defence for hand-built plans"
requirements-completed: [VER-02]
status: complete
commits: 2
plan_head_before: a03faf412e01d4fde7367bb567e2dd0bac18c828
plan_head_after: 9dbdfa70cc5830a29c48f7965d5989bef59622b8
actuals:
  tokens: 3700
  tasks: 2
  commits: 2
duration: 20 min
completed: 2026-11-01
coverage:
  - deliverable: "Model overwrite of a case twin keeps one file in the on-disk spelling and links it"
    verification:
      - kind: test
        ref: "tests/test_case_sensitive_install.py#test_overwrite_model_twin_keeps_disk_spelling"
        status: pass
    human_judgment: false
  - deliverable: "Footprint overwrite of a case twin keeps one file; the symbol field reads <library>:fp"
    verification:
      - kind: test
        ref: "tests/test_case_sensitive_install.py#test_overwrite_footprint_twin_keeps_disk_spelling"
        status: pass
    human_judgment: false
  - deliverable: "Rollback removes a hand-built case twin and a planner-built overwrite rolls back under the disk spelling"
    verification:
      - kind: test
        ref: "tests/test_case_sensitive_install.py#test_rollback_removes_hand_built_twin"
        status: pass
      - kind: test
        ref: "tests/test_case_sensitive_install.py#test_rollback_planner_overwrite_keeps_disk_spelling"
        status: pass
    human_judgment: false
  - deliverable: "Conflict view finds the incoming footprint op of a case-twin overwrite"
    verification:
      - kind: test
        ref: "tests/test_case_sensitive_install.py#test_incoming_op_finds_case_twin_footprint"
        status: pass
    human_judgment: false
  - deliverable: "Owner runs the VER-02 file on the Windows workstation: all pass, none skip"
    human_judgment: true
    rationale: "D-13 makes the owner's own Windows run the UAT; the skip depends on the machine"
---

# Phase 12 Plan 01: Case-sensitive overwrite and rollback Summary

An overwrite of an existing file that differs only by letter case now writes into the file already on disk (model and footprint), so a case-sensitive folder keeps one file and the link and Footprint field use that spelling; five tests prove it, with rollback, on a real case-sensitive folder.

## Accomplishments

- Planner: the `_decide_file` overwrite branch takes `spec.identity_of(hit)` as the decision name, so the op path is the on-disk spelling and `listed_path` is None. The case-only Rename row stays in the preview.
- `tests/casefixtures.py`: `case_sensitive_dir(path)` creates a fresh folder, enables case sensitivity with the System32 `fsutil` on win32, probes with `CaseProbe`/`caseprobe`, and skips with `could not make a case-sensitive folder: <reason>` on any failure.
- `tests/test_case_sensitive_install.py`: model twin overwrite, footprint twin overwrite, hand-built twin rollback, planner overwrite rollback, and the `incoming_op` case test. No directory listing is mocked.
- `incoming_op` compares the footprint file name ignoring case, so the conflict view still finds the op.
- `tests/test_install_plan.py`: three tests now expect the on-disk spelling; the win32-only skip is gone (test renamed `test_resolution_overwrite_model_case_twin_keeps_disk_spelling`).
- `tests/README.md`: new expected-skips row.

## Task Commits

1. Task 1 (tracer): `be7b698` fix(12-01): overwrite of a case twin keeps the spelling on disk
2. Task 2: `9dbdfa7` test(12-01): case-twin rollback, footprint overwrite and conflict lookup on a case-sensitive folder

## Verification

- `tests/test_case_sensitive_install.py`: 5 passed, no skip (fsutil worked without elevation in this worktree run).
- Plan verify set (case_sensitive_install, install_plan, install_apply, import_preview, import_content, commit_plan): 294 passed, no case-sensitive skip.
- `tests/test_import_dialog.py -k conflict`: 16 passed.
- Acceptance greps: `identity_of(hit)` on two lines; `def case_sensitive_dir` and `setCaseSensitiveInfo` present; zero listdir monkeypatches; zero case-twin `skipif`; README row present; `casefold()` in the `incoming_op` footprint branch.
- The Würth/Custom submodules are absent in the worktree; none of the targeted tests depended on them.
- Not run: the full suite (the orchestrator runs it after the wave merges).

## Deviations from Plan

None - plan executed exactly as written. Two small notes: the plan's `find_models` check needed `footprint_name(root).node` (the same finder the plan tests use), and `python -m pytest` was run with the orchestrator checkout's interpreter as instructed.

## Owner UAT (D-13)

From `C:\Git_Repo_Clones\Kicad_Libraries-importer`: `.\env\Scripts\python.exe -m pytest tests/test_case_sensitive_install.py -v -rs` should show five PASSED, "5 passed", no skip.

## Known Stubs

None.

## Threat Flags

None. The `fsutil` call is limited to an absolute System32 path, fixed arguments, no shell, 30 s timeout, on a fresh folder under tmp_path (T-12-03).

## Self-Check: PASSED

- tests/casefixtures.py and tests/test_case_sensitive_install.py exist; commits be7b698 and 9dbdfa7 are on the branch.
