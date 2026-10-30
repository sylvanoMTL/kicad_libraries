---
phase: 11-commit-gate-and-commit-panel-fixes
verified: 2026-10-30T14:00:00Z
status: gaps_found
score: 4/5 must-haves verified
covered_files:
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-01-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-01-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-02-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-02-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-03-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-03-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-04-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-04-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-05-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-05-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-06-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-06-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-07-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-07-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-08-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-08-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-09-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-09-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-10-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-10-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-11-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-11-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-12-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-12-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-13-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-13-SUMMARY.md
  - kicad_lib_manager/changes.py
  - kicad_lib_manager/gitops.py
  - kicad_lib_manager/importer/commit_gate.py
  - kicad_lib_manager/importer/commit_plan.py
  - kicad_lib_manager/importer/commit_step.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/widgets/commit_panel.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
covered_digest: "v3:sha256:ebd20124695f31bb16656e265fe4d4a41e6cadd23d75f30c4b6a3a9637a485b5"
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "The commit panel always shows what git actually did (phase goal; D-11 refusal text survives the re-probe; D-16/D-17 manual command visible)"
    status: partial
    reason: "show_outcome() renders git's output and the manual command, then _on_commit_done immediately re-probes. begin_reprobe()/apply_probe() call _clear_outcome(), which empties the output box and hides the manual-command label, and re-render the pending refusal through _render_issues() whose returned detail lines are discarded. Reproduced offscreen: after a rejected commit with output 'hook says: no' the output box is visible, and after begin_reprobe() it is hidden and empty, leaving only the first line of the issue. Affects a pre-commit hook rejection (the hook's reason is gone from the panel) and a failed parent-only bump (the selectable PowerShell command is gone). The text still reaches the log. This is a regression of Phase 6 behaviour (hook output kept whole) introduced by the REV-10 re-probe. Code review WR-01."
    artifacts:
      - path: "kicad_lib_manager/widgets/commit_panel.py"
        issue: "begin_reprobe (line ~326) and apply_probe (line ~349) clear the output box and manual label and drop _render_issues' detail lines; show_outcome (line ~498) does not remember output or manual command for the not-committed branch"
      - path: "kicad_lib_manager/widgets/import_dialog.py"
        issue: "_on_commit_done (line ~3070) starts the re-probe straight after show_outcome"
    missing:
      - "Keep the pending refusal's detail lines, git output and manual command across begin_reprobe/apply_probe until the next Commit, Check again or Switch click (as D-11 states)"
      - "A dialog-level test with a multi-line failing output and a manual_command that asserts both are still visible after the second probe is applied"
human_verification:
  - test: "Commit panel look (manual-only, 11-VALIDATION.md)"
    expected: "Commit button reads as the primary action; error, success and warning outcomes show red, green and amber strips; a parent-failed result reads 'Committed in Custom only'; sizes look right at normal and high DPI"
    why_human: "Visual appearance cannot be asserted by grep or offscreen tests"
  - test: "Paste the 'Finish it by hand' command into an interactive Windows PowerShell 5.1 and PowerShell 7 window, using a subject with quotes, $ and backticks"
    expected: "The command runs as shown and makes the parent commit with the subject intact"
    why_human: "The automated test runs the command through powershell -Command, not a pasted interactive session"
  - test: "WR-03 decision: an unreadable Atomic_ library that links a committed footprint or model passes the gate with only an INFO log note"
    expected: "Decide whether this should refuse (like an unreadable committed library) or stay a note shown in the panel"
    why_human: "Deliberate and pinned by test_gate_unreadable_outside_library_is_a_note, but it fails open in a safety gate and the note is never shown in the panel"
---

# Phase 11: Commit Gate and Commit Panel Fixes Verification Report

**Phase Goal:** The commit step never commits a part that breaks the atomic rule, and the commit panel always shows what git actually did, with the open v1.0 review and UI findings closed
**Verified:** 2026-10-30
**Status:** gaps_found
**Re-verification:** No, initial verification

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | While any part being committed fails the atomic check, the panel refuses, names the part and the broken rule, and commits nothing | VERIFIED | `commit_gate.run_gate` judges new/changed symbols of committed `Atomic_` libraries (token-stream compare against HEAD via `changes.symbol_changes`), plus symbols linking committed footprints/models with a HEAD-view split (`_introduced`). `probe_commit` (commit_step.py:356) sets state `gated`; `_precheck` (line 530) re-runs it before the first git write and returns `commit.atomic` with `refusal_summary` and `failure_lines` ("Library / Part: reason"). `run_commit` passes `kicad_fp_dir` through; the dialog passes it from both probe and click. Panel `_show_gate` shows the lines, Check again and Open Check Atomic Parts, and Commit stays disabled. 171 tests in gate/plan/gitops/panel/layering pass, including failing new part, pre-import edit, old failure not blocking, footprint overwrite, unreadable committed library. Caveat WR-03 below. |
| 2 | After a timeout the panel checks HEAD; identical-to-HEAD files raise no "missing" error; after a precheck refusal the panel probes again | VERIFIED | `run_commit` records `before = head_commit`, and on any failure compares `after` and returns `_unfinished_outcome` ("Committed <hash> in Custom, but git did not finish in time...", no parent bump, manual command). `_identical_to_head` feeds `commit.already_in_head` INFO and `all_identical` ("Nothing to commit", parent-only bump). `_on_commit_done` calls `_start_probe(reprobe=True)` when not committed. Tests in test_commit_step.py (122 passed) cover these. The re-probe loses git's detail text: see gap and truth 6. |
| 3 | Parent-message preview equals the committed text, also with no previous gitlink; on Windows the manual command uses Windows quoting | VERIFIED | `commit_plan.parent_message` is the single builder behind `parent_preview`, `parent_only_preview` and `_parent_text`; with no `old` it prints the commit lines and no "could not be listed" line. `manual_command` uses `_ps_quote` single quotes on Windows and a `-F` message file for `"` or trailing backslash (D-16 amendment); label "Finish it by hand. In PowerShell:". `test_manual_command_survives_real_powershell` runs the generated command in real Windows PowerShell and passes. Interactive paste is a human item. |
| 4 | Parent checkbox keeps the user's choice; dialog and main window can close during the read-only probe; `GIT_AUTHOR_*`/`GIT_COMMITTER_*` identity works | VERIFIED | `apply_probe` ticks the box only when `_parent_wanted is None` and restores `_parent_wanted` otherwise. The probe takes a `threading.Event`, never sets `_git_worker`; `done`/`closeEvent`/main-window `closeEvent` only block on `is_installing()` or `is_committing()`; `_shutdown` sets the events. `gitops._env` strips every `GIT_*` then restores the six identity variables; `identity_known` requires both `GIT_AUTHOR_IDENT` and `GIT_COMMITTER_IDENT`; `input` renamed `stdin_data`. Covered by test_gitops.py and test_import_dialog.py/test_commit_panel.py. |
| 5 | Commit styled primary, outcomes tinted, parent-failed not labelled "Committed", sizes on the theme scale | VERIFIED | `commit_button.setStyleSheet(theme.PRIMARY_BUTTON_QSS)` (commit_panel.py:249); Install Part also (import_dialog.py:749). `_outcome_tint` picks `ERROR_TINT`/`AMBER_TINT`/`SUCCESS_TINT` by strongest severity. State `failed` text is "Committed in Custom only". No `setFixedSize(240, 16)` remains; `_progress.setFixedSize(SP_XL*8, SP_MD)` and `SP_*` spacings throughout. Look is a human item. |
| 6 | Panel always shows what git actually did (goal sentence, D-11) | PARTIAL (GAP) | See gaps in frontmatter. Reproduced: git output and manual command vanish after the automatic re-probe. |

**Score:** 5/6 truths verified counting the goal sentence as its own truth; 4/5 of the roadmap criteria are fully clean, criterion 2 and the goal clause are degraded by the WR-01 defect, and the criteria themselves are met in letter (re-probe happens, no stale "ready").

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kicad_lib_manager/importer/commit_gate.py` | Qt-free atomic gate | VERIFIED | 438 lines, real logic; imported by commit_step and commit_panel |
| `kicad_lib_manager/importer/commit_step.py` | gate in probe + `_precheck`, `recheck_commit`, `_unfinished_outcome`, `manual_command` | VERIFIED | All present and wired from import_dialog |
| `kicad_lib_manager/importer/commit_plan.py` | single `parent_message`, `rebaseline`, `with_added_files` | VERIFIED | Present and used |
| `kicad_lib_manager/gitops.py` | identity passthrough, `stdin_data` | VERIFIED | `_IDENTITY_VARS`, `_env` |
| `kicad_lib_manager/widgets/commit_panel.py` | gated state, tints, primary button | VERIFIED with WR-01 defect | |
| `kicad_lib_manager/widgets/import_dialog.py` | non-locking probe, Check again, open check dialog | VERIFIED | `_start_probe`, `_on_check_again`, `_on_open_atomic_check`, `_on_atomic_fixes_applied` |
| `kicad_lib_manager/main_window.py` | `atomic_fixes_applied` rescan wiring | VERIFIED | line 967 |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `probe_commit` | `run_gate` | direct call, cancel passed | WIRED |
| `run_commit` | `_precheck` -> `run_gate` | `kicad_fp_dir` forwarded | WIRED |
| `CommitPanel.check_again_requested` | `ImportDialog._on_check_again` -> `recheck_commit` | signal | WIRED |
| `CommitPanel.open_check_requested` | `AtomicCheckDialog(scan_result_for(gate), focus=...)` | signal | WIRED |
| `AtomicCheckDialog.applied` | `_on_atomic_fixes_applied` -> main window rescan + re-check | signal | WIRED |
| `_on_commit_done` | `_start_probe(reprobe=True)` | not committed branch | WIRED (but clears detail, WR-01) |

### Data-Flow Trace (Level 4)

Gate failures flow from real file parses and `git show` blobs (`head_blob`, `kicad_files.parse_bytes`) into `GateResult`, `CommitProbe.gate`, then `failure_lines` into the panel label. FLOWING. Not static.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Gate, plan, gitops, panel, layering | `pytest tests/test_commit_gate.py tests/test_commit_plan.py tests/test_gitops.py tests/test_commit_panel.py tests/test_importer_layering.py` | 171 passed | PASS |
| Commit step against real git, incl. real PowerShell paste | `pytest tests/test_commit_step.py` | 122 passed | PASS |
| Full suite (orchestrator, not re-run) | `pytest` at 9caab38 | 9173 passed, 4 skipped | PASS |
| WR-01 reproduction | scratch test: `show_outcome` then `begin_reprobe` | output box visible then hidden/empty; only first issue line remains | FAIL (confirms gap) |

### Probe Execution

No `probe-*.sh` scripts declared for this phase. SKIPPED.

### Requirements Coverage

All eight phase IDs are claimed by plan frontmatter and none is orphaned.

| Requirement | Source Plans | Status | Evidence |
|-------------|--------------|--------|----------|
| GIT-06 | 11-02, 03, 05, 06, 08, 10, 11, 12, 13 | SATISFIED (WR-03 caveat) | gate in probe and click, names part and rule |
| REV-06 | 11-06, 11-07 | SATISFIED | `_unfinished_outcome`, HEAD before/after |
| REV-07 | 11-03 | SATISFIED | one `parent_message` builder |
| REV-08 | 11-07 | SATISFIED | `_ps_quote`, `-F` fallback, real PowerShell test |
| REV-09 | 11-06, 11-10, 11-13 | SATISFIED | identical-to-HEAD INFO, parent-only |
| REV-10 | 11-04, 06, 08, 09, 10, 11 | PARTIAL | re-probe happens, but WR-01 drops git's detail and the manual command |
| REV-11 | 11-01, 04, 06, 07, 09 | SATISFIED | checkbox, non-locking probe, identity env |
| UI-02 | 11-04, 11-09 | SATISFIED (look needs human check) | primary button, tints, label, SP_* |

Bookkeeping: `.planning/REQUIREMENTS.md` still shows all eight as `[ ]` / "Pending" and ROADMAP lists Phase 11 as unchecked. Update after the gap is closed.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| commit_panel.py | 326-349 | `_render_issues` return value discarded; output and manual label cleared on re-probe | Blocker (the gap above) | git reason and manual command disappear from the panel |
| commit_panel.py | ~560-585 | `if changed / elif added / elif dirty_before` (WR-02) | Warning | pre-import dirty warning hidden for changed/added files; double-click routes to `changed_diff` only |
| commit_gate.py | 223-230 | unreadable linked library becomes an INFO note, never shown (WR-03) | Warning | gate fails open for parts in that library |
| commit_panel.py | 33, 617 | dead `_STATES`, unused `ready` (IN-01) | Info | |
| gitops.py | 87 | lower-case identity names promoted on every platform (IN-06) | Info | |
| (others) | | IN-02..IN-05 per 11-REVIEW.md | Info | quality only |

No TBD/FIXME/XXX markers in files changed by the phase.

### Human Verification Required

1. **Commit panel look.** Open the import dialog Result view with a failing, a successful and a parent-failed commit. Expect a primary-styled Commit button, red/green/amber strips, "Committed in Custom only" for the partial result.
2. **Interactive PowerShell paste.** Take the "Finish it by hand" command for a subject containing `"`, `$` and a backtick and paste it into Windows PowerShell 5.1 and PowerShell 7. Expect the same subject in the resulting parent commit.
3. **WR-03 decision.** Decide whether an unreadable `Atomic_` library that links a committed file should refuse the commit.

### Gaps Summary

One real gap against the goal sentence "the commit panel always shows what git actually did": the automatic re-probe after a refused or failed commit (the REV-10 fix) wipes git's detail text and the manual command from the panel. A rejected pre-commit hook leaves the user with "Commit in Custom failed (git exit 1); nothing was committed" and no reason; a failed parent-only bump loses its pasteable command. The text is still in the log. The fix is small and local to `commit_panel.begin_reprobe`/`apply_probe`/`show_outcome` plus one dialog-level test, as proposed in 11-REVIEW.md WR-01. Everything else, including the atomic gate itself, the HEAD check after a timeout, the single parent-message builder, PowerShell quoting, identity variables, non-locking probe and theming, is present, wired and covered by passing tests. WR-02 and WR-03 are warnings and need a human decision on severity; IN-01..IN-06 are advisory.

---

_Verified: 2026-10-30_
_Verifier: Claude (gsd-verifier)_
