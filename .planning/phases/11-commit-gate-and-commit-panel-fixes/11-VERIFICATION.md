---
phase: 11-commit-gate-and-commit-panel-fixes
verified: 2026-10-30T21:00:00Z
status: human_needed
score: 6/6 must-haves verified
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
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-14-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-14-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-15-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-15-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-16-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-16-SUMMARY.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-17-PLAN.md
  - .planning/phases/11-commit-gate-and-commit-panel-fixes/11-17-SUMMARY.md
  - kicad_lib_manager/changes.py
  - kicad_lib_manager/gitops.py
  - kicad_lib_manager/importer/commit_gate.py
  - kicad_lib_manager/importer/commit_plan.py
  - kicad_lib_manager/importer/commit_step.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/widgets/commit_panel.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
covered_digest: "v3:sha256:e4580f38360eaa8aeb412d2ddad6be91900bd00070449334c34192100c37cbc5"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 4/5 roadmap criteria clean (5/6 counting the goal sentence)
  gaps_closed:
    - "The commit panel always shows what git actually did: git's output, the refusal's detail lines and the manual command now survive the automatic re-probe (plan 11-14)"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Commit panel look (manual-only, 11-VALIDATION.md)"
    expected: "Commit button reads as the primary action; error, success and warning outcomes show red, green and amber strips; a parent-failed result reads 'Committed in Custom only'; sizes look right at normal and high DPI"
    why_human: "Visual appearance cannot be asserted by grep or offscreen tests (11-UI-REVIEW.md scored 18/24, advisory)"
  - test: "Paste the 'Finish it by hand' command into an interactive Windows PowerShell 5.1 and PowerShell 7 window, using a subject with quotes, $ and backticks"
    expected: "The command runs as shown and makes the parent commit with the subject intact"
    why_human: "The automated test runs the command through powershell -Command, not a pasted interactive session"
---

# Phase 11: Commit Gate and Commit Panel Fixes Verification Report

**Phase Goal:** The commit step never commits a part that breaks the atomic rule, and the commit panel always shows what git actually did, with the open v1.0 review and UI findings closed
**Verified:** 2026-10-30
**Status:** human_needed
**Re-verification:** Yes, after gap closure (plans 11-14, 11-15, 11-16, 11-17). Source and tests are unchanged between 1cc41e6 and HEAD 9ea8659 (`git diff 1cc41e6 HEAD -- kicad_lib_manager tests` is empty), so the full suite run at 1cc41e6 (9202 passed, 4 skipped, exit 0, log in the scratchpad) describes the code verified here.

## Goal Achievement

### Observable Truths (ROADMAP success criteria plus the goal sentence)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | While any part being committed fails the atomic check, the panel refuses, names the part and the broken rule, and commits nothing | VERIFIED | `commit_gate.run_gate` judges new/changed symbols of committed `Atomic_` libraries and, for committed footprints/models, every linking symbol in a HEAD-view split. `probe_commit` (commit_step.py:354-364) sets state `gated`; `_precheck` (line 528) re-runs the gate before the first git write and returns `commit.atomic` with `refusal_summary` plus `failure_lines` ("Library / Part: reason"). The previous caveat WR-03 is closed: `_check_linked_symbols` (commit_gate.py:276-297) turns an unreadable outside `Atomic_` library or an unlistable `Symbols` folder into a `problems` line, so `GateResult.refused` is true (fail closed); a link to a committed footprint that cannot be followed becomes a visible, non-refusing `unchecked` line (line 310-313). `notes` channel is gone. Tests: `test_gate_unreadable_outside_library_refuses`, `..._ignored_without_linked_files`, `test_gate_unlistable_symbols_folder_refuses`, `test_unreadable_linked_library_refuses_probe_panel_and_click`, `test_unchecked_linked_part_shown_in_panel_without_refusing` pass. |
| 2 | After a timeout the panel checks HEAD; identical-to-HEAD files raise no "missing" error; after a precheck refusal the panel probes again | VERIFIED | `run_commit` records `before = head_commit` and, on any git failure, compares `after` and returns `_unfinished_outcome` (commit_step.py:849-858, 677-707). `_identical_to_head` feeds `commit.already_in_head` INFO and the parent-only path (lines 833-838, 874-878). `_on_commit_done` calls `_start_probe(reprobe=True)` when not committed (import_dialog.py:3081). 9 selected tests in test_commit_step.py pass. |
| 3 | Parent-message preview equals the committed text, also with no previous gitlink; on Windows the manual command uses Windows quoting | VERIFIED | One `commit_plan.parent_message` builder behind `parent_preview`, `parent_only_preview` and `_parent_text`. `manual_command` uses `_ps_quote` single quotes on Windows and a `-F` message file for `"` or a trailing backslash (commit_step.py:625-648). `test_manual_command_survives_real_powershell` runs it through real Windows PowerShell and passes. Interactive paste stays a human item. |
| 4 | Parent checkbox keeps the user's choice across probes; dialog and main window can close during the read-only probe; `GIT_AUTHOR_*`/`GIT_COMMITTER_*` identity works | VERIFIED | `apply_probe` ticks the box only while `_parent_wanted is None` (commit_panel.py:384-386). Close is gated on `is_installing()`/`is_committing()` only (main_window.py:1186); the probe never sets `_git_worker`. `gitops._env` (gitops.py:84-102) now keeps exactly four identity variables (NAME and EMAIL for author and committer), strips the two DATE variables, folds case only on Windows, exact upper-case key wins. `test_commit_with_identity_from_environment_only`, `test_commit_ignores_exported_dates`, `test_env_keeps_four_identity_names`, `test_env_folds_case_only_on_windows` pass in the 209-test run. |
| 5 | Commit styled primary, outcomes tinted, parent-failed not labelled "Committed", sizes on the theme scale | VERIFIED (look is a human item) | `commit_button.setStyleSheet(theme.PRIMARY_BUTTON_QSS)` (commit_panel.py:254); `_tint_outcome_frame`/`_outcome_tint` pick error, amber or success tint; state `failed` text is `_COMMITTED_CUSTOM_ONLY = "Committed in Custom only"`; `_progress.setFixedSize(theme.SP_XL * 8, theme.SP_MD)`; no `(240, 16)` remains. |
| 6 | The commit panel always shows what git actually did (goal sentence, D-11, D-16, D-17) | VERIFIED | Previous gap closed. `show_outcome` stores `_pending_refusal`, `_pending_output`, `_pending_manual` together for a not-committed outcome (commit_panel.py:447-453). `begin_reprobe` and `apply_probe` replay them through `_show_pending` (lines 343, 367) except when the new probe is itself `refused`/`unavailable`; `_drop_pending` clears all three on Commit, Check again, Switch, a new plan or a committed outcome. Dialog-level tests `test_hook_rejection_output_survives_reprobe_in_dialog` and `test_parent_only_failure_reprobes_in_dialog` (multi-line output plus manual command, asserted after the second probe) pass; panel tests `test_panel_failure_detail_survives_reprobe` and the five-way `test_panel_failure_detail_dropped` pass. I did not trust the tests alone: the same offscreen reproduction that failed last time now keeps the box and the manual command. |

**Score:** 6/6 truths verified. `behavior_unverified`: 0 (the superseding Check again, the probe generation guard and the combined double-click view each have a dialog-level test; the invariants "Check again never starts a commit" and "refused while Switch/Commit runs" are covered by `test_check_again_supersedes_running_probe` and the earlier Check-again tests).

### Decision asked by the orchestrator: does the new WR-01 contradict "always shows what git actually did"?

**No, it does not contradict the goal clause. It is a real, reproducible defect, but a Warning, not a gap.**

Reproduced (scratch script in the scratchpad, not in the repo): refuse a commit at click time (`show_outcome` with a `commit.atomic` ERROR), re-probe to `gated`, then `begin_reprobe()` + `apply_probe(ready)` without going through the panel's own Check-again button. Result: `outcome_lines() == ['✖ Not committed: 1 part breaks the atomic rule.']` stays on top of a `ready` probe with Commit enabled. The code path is exactly as 11-REVIEW.md says: `ImportDialog._on_atomic_fixes_applied` (import_dialog.py:2976-2982) calls `_on_check_again()` directly, which calls `panel.begin_reprobe()` but never `_drop_pending`; only the panel's click handlers drop it.

Why this is not a goal contradiction:
- The kept text is a true record of what the user's last Commit click did: git was never asked, nothing was committed. It does not claim any git state that is false. The goal clause is about reporting git's actual result (output, hook reason, manual command), and those are shown correctly and in full.
- Commit enablement follows the fresh probe, not the kept text (`_refresh_parent_and_commit` uses `self._state == "ready"`), so nothing is mis-gated. The user cannot commit a non-atomic part because of it, and a stale red line cannot make the panel commit anything.
- It needs a narrow sequence: a Commit click refused at commit time (not by the probe, which already disables Commit), a re-probe that is still `gated`, then Open Check Atomic Parts and applied fixes. A pre-commit hook rejection never shows Open Check, so that common case is unaffected.

Why it still matters (Warning): it breaks the panel's own stated rule "stays until the next Commit, Check again or Switch click" and leaves a red "Not committed: N parts break the atomic rule" line contradicting a green-lit, fixed state. That is the same family as REV-10's "no stale state", just with a fresh `ready` instead of a stale one. Recommended one-line fix from the review: a public `CommitPanel.forget_refusal()` called from `_on_atomic_fixes_applied` before `_on_check_again()`, plus the dialog test the review describes. Not blocking Phase 12/13.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kicad_lib_manager/importer/commit_gate.py` | Qt-free fail-closed gate, `_LinkedFindings`, `unchecked` | VERIFIED | 536 lines, real logic, no notes channel, imported by commit_step and commit_panel |
| `kicad_lib_manager/importer/commit_step.py` | gate in probe and `_precheck`, `recheck_commit`, `_unfinished_outcome`, `manual_command`, `combined_view` | VERIFIED | all present; `CANCELLED` imported directly (alias gone) |
| `kicad_lib_manager/importer/commit_plan.py` | single `parent_message`, `rebaseline`, `with_added_files` | VERIFIED | present, used |
| `kicad_lib_manager/gitops.py` | four identity variables, `_env(environ, windows=)`, `stdin_data` | VERIFIED | lines 38-46, 84-102 |
| `kicad_lib_manager/widgets/commit_panel.py` | gated state, pending refusal/output/manual, tints, primary button, combined marks | VERIFIED | lines 143-146, 331-344, 428-469, 573-627 |
| `kicad_lib_manager/widgets/import_dialog.py` | non-locking probe, `_begin_probe_generation`, superseding Check again, combined double-click routing | VERIFIED with WR-01 warning | lines 2861-2950, 3030-3045 |
| `kicad_lib_manager/widgets/help_dialog.py` | Commit section names the new "added" wording | VERIFIED | `test_help_import_page_describes_commit_step` passes |
| `kicad_lib_manager/main_window.py` | `atomic_fixes_applied` rescan wiring | VERIFIED | line 967 |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `probe_commit` | `run_gate` | direct call, cancel passed | WIRED |
| `run_commit` | `_precheck` -> `run_gate` | `kicad_fp_dir` forwarded | WIRED |
| `_check_linked_symbols` | `GateResult.problems` | `_LinkedFindings.problems` merged in `run_gate` (line 401) | WIRED |
| `GateResult.unchecked` | amber panel line | `old_notes` -> `_show_gate` `_old_label` | WIRED |
| `CommitPanel.check_again_requested` | `ImportDialog._on_check_again` -> `recheck_commit` | signal | WIRED |
| `CommitPanel.open_check_requested` | `AtomicCheckDialog(scan_result_for(gate), focus=...)` | signal | WIRED |
| `AtomicCheckDialog.applied` | `_on_atomic_fixes_applied` -> main-window rescan + `_on_check_again` | signal | WIRED (does not clear the kept refusal, WR-01) |
| `_on_commit_done` | `_start_probe(reprobe=True)` -> `begin_reprobe` -> `_show_pending` | not-committed branch | WIRED, detail now kept |
| `_start_probe` / `_on_check_again` | `_begin_probe_generation` | shared, sets older Events | WIRED |
| `_on_commit_file_activated` | `combined_view(changed_diff, pre_import_diff)` | one `_run_content` worker | WIRED |
| `run_git` | `_env()` | every git call | WIRED |

### Data-Flow Trace (Level 4)

Gate failures flow from real `.kicad_sym` parses and `git show` blobs (`head_blob`, `kicad_files.parse_bytes`) into `GateResult`, `CommitProbe.gate`, then `failure_lines` and `refusal_summary` into the panel label and the `commit.atomic` ERROR. Git's output and the manual command flow from `CommitOutcome.output`/`manual_command` into `_pending_*` and back into the output box and `_manual_label`. FLOWING, not static.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Gate, gate+panel, panel, gitops, plan, help, layering | `pytest tests/test_commit_gate.py tests/test_commit_gate_panel.py tests/test_commit_panel.py tests/test_gitops.py tests/test_commit_plan.py tests/test_help_dialog.py tests/test_importer_layering.py` | 209 passed in 208 s | PASS |
| Dialog: hook output survives re-probe, parent-only failure re-probe, Check again supersedes | `pytest tests/test_import_dialog.py -k "hook_rejection_output_survives or parent_only_failure_reprobes or check_again_supersedes"` | 3 passed | PASS |
| Commit step: combined view, late commit, PowerShell | `pytest tests/test_commit_step.py -k "combined_view or unfinished or powershell or ps_quote"` | 9 passed | PASS |
| Full suite (orchestrator, not re-run; code unchanged since) | `pytest` at 1cc41e6 | 9202 passed, 4 skipped, exit 0 | PASS |
| New WR-01 reproduction | scratch panel script: refusal, gated re-probe, ready re-probe without `_drop_pending` | stale red refusal remains over `ready`, Commit enabled | CONFIRMED (Warning) |

### Probe Execution

No `probe-*.sh` scripts declared for this phase. SKIPPED.

### Requirements Coverage

All eight phase IDs are claimed by plan frontmatter and each appears in REQUIREMENTS.md and in ROADMAP Phase 11. None is orphaned.

| Requirement | Source Plans | Status | Evidence |
|-------------|--------------|--------|----------|
| GIT-06 | 11-02, 03, 05, 06, 08, 10, 11, 12, 13, 14, 15, 17 | SATISFIED | gate in probe and click, names part and rule; unreadable outside library and unlistable Symbols folder now refuse (WR-03 closed) |
| REV-06 | 11-06, 11-07 | SATISFIED | `_unfinished_outcome`, HEAD before/after |
| REV-07 | 11-03 | SATISFIED | one `parent_message` builder |
| REV-08 | 11-07 | SATISFIED | `_ps_quote`, `-F` fallback, real-PowerShell test |
| REV-09 | 11-06, 11-10, 11-13 | SATISFIED | identical-to-HEAD INFO, parent-only bump |
| REV-10 | 11-04, 06, 08, 09, 10, 11, 14, 17 | SATISFIED | re-probe happens and now keeps git's detail and the manual command; Check again supersedes a running probe. Residual: WR-01 stale-line warning on the atomic-fix route |
| REV-11 | 11-01, 04, 06, 07, 09, 16 | SATISFIED | checkbox, non-locking probe, four-variable identity passthrough without dates |
| UI-02 | 11-04, 11-09, 14 | SATISFIED (look needs human check) | primary button, tints, label, `SP_*` sizes, combined marks and new "added" wording |

Bookkeeping to do after acceptance (not a code gap): `.planning/REQUIREMENTS.md` still shows all eight as `[ ]` / "Pending" (lines 83, 97-102, 107, 167-182), and ROADMAP.md still has Phase 11 unchecked (line 32) with "4 gap-closure plans planned". Update them when the phase is closed.

### Review and Gate Documents

| Document | Result |
|----------|--------|
| 11-VALIDATION.md | validated, nyquist_compliant: true |
| 11-SECURITY.md | 35/35 threats closed, threats_open: 0 |
| 11-UI-REVIEW.md | 18/24, advisory |
| 11-REVIEW.md (incremental, plans 14-17) | 0 critical, 1 warning (WR-01 above), 3 info |
| 11-REVIEW-DISPOSITION.md | 4 open (WR-01, IN-01, IN-02, IN-03), 5 fixed. Note: plan 11-17 aimed at `open: 0`; the ids WR-01 and IN-01..IN-03 were reused by the new, different findings, so the earlier nine are recorded as fixed and the four new ones are open. This is consistent, not a failure of the plan. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| import_dialog.py / commit_panel.py | 2976-2982 / 739-742 | atomic-fix Check again does not drop the kept refusal (WR-01, new) | Warning | stale red refusal line over a `ready` probe; Commit enablement unaffected |
| commit_gate.py | 485 | `_UNLISTED in problem` substring classification (IN-01) | Info | cosmetic count risk only |
| commit_step.py | 797-803 | `combined_view` kind "diff" when one half is an error (IN-02) | Info | an error sentence is diff-highlighted |
| gitops.py | 84-100 | case-fold branch unreachable in production (IN-03) | Info | defensive code only |

No `TBD`/`FIXME`/`XXX` markers in files changed by the phase. Previously flagged items WR-02 (changed/added plus dirty-before row), WR-03 (fail-open linked check), IN-04, IN-05, IN-06 are fixed in code and tests.

### Human Verification Required

1. **Commit panel look.** Open the import dialog Result view with a failing, a successful and a parent-failed commit, at normal and high DPI. Expect a primary-styled Commit button, red/green/amber strips, "Committed in Custom only" for the partial result, and the combined "(changed after the install; also changed before this import)" row mark readable.
2. **Interactive PowerShell paste.** Take the "Finish it by hand" command for a subject containing `"`, `$` and a backtick and paste it into Windows PowerShell 5.1 and PowerShell 7. Expect the same subject in the resulting parent commit.

The earlier WR-03 owner decision is resolved in code (fail closed, owner decision recorded in plan 11-15) and no longer a human item.

### Gaps Summary

No gaps against the phase goal. The one gap from the first verification (git output and the manual command vanishing after the automatic re-probe) is closed in code and covered by dialog-level and panel-level tests, and the offscreen reproduction that failed before now passes. The atomic gate fails closed for every case the earlier review called out. One new Warning (WR-01, a kept refusal surviving the Check again that follows an atomic fix) is reproduced and left to the owner: it does not misreport what git did and cannot enable a bad commit, so it does not block the phase. Status is `human_needed` only because the panel's look at real fonts and the interactive PowerShell paste cannot be verified by code.

---

_Verified: 2026-10-30_
_Verifier: Claude (gsd-verifier)_
