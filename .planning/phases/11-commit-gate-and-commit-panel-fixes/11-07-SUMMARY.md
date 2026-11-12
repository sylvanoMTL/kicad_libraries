---
phase: 11-commit-gate-and-commit-panel-fixes
plan: 07
subsystem: git-commit-step
tags: [powershell, shlex, git-commit, pyside6, identity]

requires:
  - phase: 11-commit-gate-and-commit-panel-fixes
    provides: "11-01 identity_known + env-preserving _env; 11-04 panel manual label; 11-06 late-commit outcome with manual command"
provides:
  - "manual_command / manual_label / _ps_quote in commit_step.py (PowerShell-safe and POSIX-safe 'Finish it by hand' command)"
  - "CommitOutcome.manual_label and the panel label line for failed, late and parent-only outcomes"
  - "identity message naming user.name/user.email and the GIT_AUTHOR_*/GIT_COMMITTER_* variables"
affects: [phase-11 verification, 11-08]

plan_head_before: de28376b44fdf00a3f020cacfbaabab03354cff5
plan_head_after: b260ef13c618cd351fb776c95aa38683a7ab95e7

actuals:
  tokens: 21000
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Shell-specific quoting chosen by a windows= parameter so both branches are unit-tested on one machine"
    - "Long or unsafe text goes to a UTF-8 file outside the repo and only its forward-slash path is pasted (-F)"

key-files:
  created: []
  modified:
    - kicad_lib_manager/importer/commit_step.py
    - kicad_lib_manager/widgets/commit_panel.py
    - tests/test_commit_step.py
    - tests/test_commit_panel.py
    - tests/README.md

key-decisions:
  - "Typographic single quotes (U+2018, U+2019, U+201A, U+201B) are doubled in _ps_quote: a live PowerShell 5.1 run showed they end a single-quoted string"
  - "The manual command is shown once, in its own selectable line; the WARNING/ERROR text no longer repeats it in the outcome strip"
  - "POSIX never uses -F; shlex.quote is safe for every character"

requirements-completed: [REV-08, REV-11, REV-06]

coverage:
  - id: D1
    description: "On Windows the Finish it by hand command is PowerShell single-quoted for every argument, so $, $(...), backtick, apostrophe and mid-string backslash reach git unchanged"
    requirement: REV-08
    verification:
      - kind: unit
        ref: "tests/test_commit_step.py#test_manual_command_powershell_quotes_every_argument"
        status: pass
      - kind: integration
        ref: "tests/test_commit_step.py#test_manual_command_survives_real_powershell"
        status: pass
    human_judgment: false
  - id: D2
    description: "A subject with a double quote or a trailing backslash switches to commit -F <UTF-8 file outside the repo>; POSIX uses shlex.quote and never writes a file"
    requirement: REV-08
    verification:
      - kind: unit
        ref: "tests/test_commit_step.py#test_manual_command_uses_message_file_for_double_quote"
        status: pass
      - kind: unit
        ref: "tests/test_commit_step.py#test_manual_command_posix_never_writes_a_file"
        status: pass
    human_judgment: false
  - id: D3
    description: "The panel shows 'Finish it by hand. In PowerShell:' (Windows) or 'Finish it by hand:' with the command for a failed parent commit, a parent-only failure and a late commit"
    requirement: REV-06
    verification:
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_manual_label_partial_failure"
        status: pass
      - kind: unit
        ref: "tests/test_commit_panel.py#test_panel_manual_label_late_commit"
        status: pass
    human_judgment: false
  - id: D4
    description: "Identity message names both ways to set it, and an environment-only identity can probe and commit"
    requirement: REV-11
    verification:
      - kind: integration
        ref: "tests/test_commit_step.py#test_env_identity_probe_and_commit"
        status: pass
      - kind: unit
        ref: "tests/test_commit_step.py#test_probe_identity_message_names_variables"
        status: pass
    human_judgment: false
  - id: D5
    description: "A real paste of the shown command into a Windows PowerShell window commits the parent with the intended message"
    verification: []
    human_judgment: true
    rationale: "Backstop: automated tests run the command in powershell -Command with a stand-in for git; the phase's manual-only row covers pasting into an interactive window and a real commit"

duration: 55min
completed: 2026-10-30
status: complete
---

# Phase 11 Plan 07: Paste-safe manual command and identity message Summary

**The "Finish it by hand" command is now written for the shell it is pasted into: PowerShell single quotes on Windows, a UTF-8 `-F` message file for subjects holding `"` or ending in `\`, `shlex.quote` elsewhere, with a matching panel label; the identity message names both ways to set an identity.**

## Performance

- **Duration:** about 55 min
- **Tasks:** 3
- **Files modified:** 5 (2 source, 3 test/docs)

## Accomplishments

- `manual_command(parent, custom_rel, message, *, windows=None, message_dir=None)` replaces `_manual_parent_command`. Windows quotes every argument with `_ps_quote`; a subject with `"` or a trailing `\` writes the full message to a `kicad_parent_message_*.txt` file via `tempfile.mkstemp` (outside the repo) and returns `git -C '<parent>' commit -F '<file>' -- 'Custom'`. POSIX always uses `shlex.quote`.
- `test_manual_command_survives_real_powershell` runs the generated command in the real Windows PowerShell 5.1 (a Python echo script stands in for git) for seven subjects and asserts the exact argv received. It passes on the workstation, not skipped.
- `CommitOutcome.manual_label` plus `MANUAL_LABEL_POWERSHELL` / `MANUAL_LABEL`; the issue texts, and the panel line, use the same label. The panel now shows the command for a committed outcome, a failure, and a parent-only outcome (the D-12 late-commit warning included).
- The identity reason now reads "git does not know who you are: set user.name and user.email, or GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL, GIT_COMMITTER_NAME and GIT_COMMITTER_EMAIL". An environment-only identity probes "ready" and commits in Custom and the parent; committer-only variables probe "unavailable".

## Task Commits

1. **Task 1: failed parent commit shows a PowerShell-safe command (tracer)** - `e0cfd67` (feat)
2. **Task 2: -F message file, proved in real PowerShell** - RED `977d7fc` (test), GREEN `8d9746d` (feat)
3. **Task 3: identity message and environment-only identity** - RED `c140d56` (test), GREEN `b260ef1` (feat)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified

- `kicad_lib_manager/importer/commit_step.py` - `manual_command`, `manual_label`, `_ps_quote`, `_write_message_file`, `CommitOutcome.manual_label`, identity message
- `kicad_lib_manager/widgets/commit_panel.py` - label line from `outcome.manual_label`, filter on the shared "Finish it by hand" prefix
- `tests/test_commit_step.py` - quoting tests for both platforms, `-F` tests, live PowerShell test, identity tests
- `tests/test_commit_panel.py` - `test_panel_manual_label_*`
- `tests/README.md` - Windows PowerShell conditional skip row

## Decisions Made

- Doubled the typographic single quotes in `_ps_quote` (see deviation 1).
- A fallback to the `-m` form when the message file cannot be written (OSError), as the plan specified; covered by a test.
- Tracer gate: the tracer `<verify>` is automated-only and was re-run end to end (`-k "manual or hook_rejection or partial"` plus the timeout and parent-only tests): passed before the expansion tasks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Typographic apostrophe broke the PowerShell string**
- **Found during:** Task 2 (RED run of the live PowerShell test with an extra subject)
- **Issue:** `it’s` (U+2019) ends a PowerShell single-quoted string; plain `'` doubling left the command unparsable ("string is missing the terminator").
- **Fix:** `_ps_quote` doubles U+2018, U+2019, U+201A and U+201B as well as `'`. Added a seventh subject to the live test.
- **Files modified:** `kicad_lib_manager/importer/commit_step.py`, `tests/test_commit_step.py`
- **Verification:** `test_manual_command_survives_real_powershell[...typographic]` passes.
- **Committed in:** `8d9746d`

**2. [Rule 2 - Missing critical] Manual command shown twice in the outcome strip**
- **Found during:** Task 1
- **Issue:** With the label line now shown for the late-commit warning, the WARNING text (which embeds the command) would show the command a second time.
- **Fix:** `_render_issues` drops lines starting "Finish it by hand" from non-error issue text; the dedicated selectable line carries the command.
- **Files modified:** `kicad_lib_manager/widgets/commit_panel.py`
- **Verification:** `test_panel_manual_label_late_commit`
- **Committed in:** `e0cfd67`

**3. [Plan-note] Task 3 env-identity tests were already green**
- `test_env_identity_probe_and_commit` and the committer-only probe test passed before the production change, because plan 11-01 already made `identity_known` and `_env` identity-aware. The RED commit is therefore the two message-text tests; the env tests stay as regression coverage.

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical), 1 note.
**Impact on plan:** Both fixes needed for a command that pastes correctly; no scope creep.

## Issues Encountered

None beyond the deviations. The `-F` message files are left in the system temp folder on purpose (the user pastes the command later), as the plan specifies.

## Threat Flags

None. T-11-15 mitigated and proved by unit tests on both branches and the live PowerShell test with `$(calc)`-style subjects; T-11-16 accepted (the file holds only the parent message, created by `mkstemp` outside the repo).

## Known Stubs

None.

## TDD Gate Compliance

Tasks 2 and 3 followed RED then GREEN: `977d7fc` test -> `8d9746d` feat, `c140d56` test -> `b260ef1` feat. Task 1 is a tracer (single feat commit). RED evidence: Task 2, six failures in `-k manual_command` including the live PowerShell test dropping the `"` and eating the closing quote on a trailing `\`; Task 3, two failures on the new message text.

## Verification

- `pytest tests/test_commit_step.py tests/test_gitops.py tests/test_commit_panel.py -q -rs`: 176 passed, no skips.
- `pytest tests/test_commit_plan.py tests/test_commit_gate.py tests/test_import_dialog.py tests/test_importer_layering.py tests/test_layering.py -q -rs`: 272 passed.
- Manual end-of-phase row (paste into an interactive PowerShell window) is not run here.

## Next Phase Readiness

REV-08 closed; REV-11 identity closed end to end. The manual-only paste check remains for phase verification.

## Self-Check: PASSED

- Files modified exist; commits `e0cfd67`, `977d7fc`, `8d9746d`, `c140d56`, `b260ef1` are ancestors of HEAD.

---
*Phase: 11-commit-gate-and-commit-panel-fixes*
*Completed: 2026-10-30*
