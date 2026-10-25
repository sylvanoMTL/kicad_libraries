---
phase: 06-git-commit-step
reviewed: 2026-10-22T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - kicad_lib_manager/gitops.py
  - kicad_lib_manager/importer/commit_plan.py
  - kicad_lib_manager/importer/commit_step.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/widgets/commit_panel.py
  - kicad_lib_manager/widgets/help_dialog.py
  - kicad_lib_manager/widgets/import_dialog.py
  - kicad_lib_manager/widgets/import_result.py
  - tests/gitfixtures.py
  - tests/test_commit_panel.py
  - tests/test_commit_plan.py
  - tests/test_commit_step.py
  - tests/test_gitops.py
  - tests/test_help_dialog.py
  - tests/test_import_dialog.py
  - tests/test_importer_layering.py
  - tests/test_layering.py
  - tests/test_main_window_import.py
findings:
  critical: 0
  warning: 5
  info: 3
  total: 8
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-10-22
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Phase 6 adds a confirmed git-commit step (gitops, commit_plan, commit_step, CommitPanel, dialog wiring). For the pre-existing files only the Phase 6 diff against 504f612 was reviewed.

The safety rules hold up under review:
- No git call is made before the click. The probe is read-only (rev-parse, status, ls-tree, cat-file, log).
- Every git call goes through `run_git`, which uses an argv list with no shell, a subcommand allow-list, `--literal-pathspecs`, and strips `GIT_*` from the environment.
- The allow-list holds no remote-touching subcommand: no push, fetch, pull or clone.
- Commits are path-limited (`commit --only` with `--pathspec-from-file`, NUL separated).
- `_precheck` re-validates everything immediately before the first write.
- A git found inside the repo is refused.
- No destructive command is reachable: `reset` is only used by `unstage()`, on exactly the app's own intent-to-add paths.
- Library and symbol names are constrained to `[A-Za-z0-9_.-]` by `naming.sanitize_name`, so the message and manual-command text cannot carry shell metacharacters from a package.

I found no BLOCKER. The 145 tests in the gitops, commit_plan, commit_step and commit_panel modules pass locally. The warnings below are correctness and robustness defects around timeout handling, preview/actual message fidelity, retry recovery and the manual fallback command.

## Warnings

### WR-01: A commit timeout is reported as "nothing was committed" without checking HEAD

**File:** `kicad_lib_manager/importer/commit_step.py:360-370` (and `kicad_lib_manager/gitops.py:353`, `kicad_lib_manager/importer/commit_step.py:467-471`)
**Issue:** `subprocess.run(timeout=...)` kills only the `git.exe` process when `COMMIT_TIMEOUT` (300 s) expires. `_custom_failure` then says "nothing was committed" and `run_commit` runs `unstage()`, without checking whether a commit was created.
- Git creates the commit and updates the ref before it runs `post-commit`. A slow `post-commit` hook, or GPG/pinentry waiting after the ref update, is therefore killed after the commit exists. The user is told nothing was committed, the parent bump is skipped, and a retry fails with "nothing to commit".
- On Windows the kill does not reach hook or gpg grandchildren. They may keep holding `index.lock` while the app reports a clean failure.

**Fix:** Record `head_commit` before `commit_paths`. On a `git.timeout` Issue (and on any failure), compare HEAD again. If HEAD moved, treat the Custom commit as made (continue to the outcome and parent step, or report "commit made but git did not finish"). Otherwise keep the current message.
```python
before = gitops.head_commit(ctx, custom)
run = gitops.commit_paths(ctx, custom, message, rels)
if _run_failed(run):
    if gitops.head_commit(ctx, custom) == before:
        if new:
            gitops.unstage(ctx, custom, new)
        return _custom_failure(run, committing=True)
    # HEAD moved: fall through to the success path and add a warning about the interrupted git process
```

### WR-02: Parent commit preview differs from the message actually committed when Custom is not yet in the parent's HEAD

**File:** `kicad_lib_manager/importer/commit_step.py:192-201, 385-392` with `kicad_lib_manager/importer/commit_plan.py:239-261`
**Issue:** The preview and the real message are built by different paths when `gitlink_old` is `None` (Custom has no gitlink in the parent's HEAD).
- Probe: `_earlier()` returns `((), False)`, so the panel calls `parent_preview(..., listed=False)`. The preview shows `(the Custom commits since  could not be listed)`, with an empty hash and a double space, plus a `- <new commit> subject` line.
- Commit: `commit_parent_ref` computes `commits = []` when `old` is falsy and passes `listed=commits is not None`, which is `True`. The real message has neither line.

D-19 promises the user sees the generated message before committing. Here the preview shows text that is never committed.

**Fix:** Handle `old is None` explicitly in both places. In `_earlier` return `((), True)` when `gitlink_old is None` (nothing earlier to list). In `parent_message`, when `old` is falsy, do not add the "could not be listed" line and only list the commit(s) that exist. Make `commit_parent_ref` and `parent_preview` call the same helper so they cannot drift.

### WR-03: The "Finish it by hand" command is mis-quoted for the primary platform and for shell metacharacters

**File:** `kicad_lib_manager/importer/commit_step.py:506-508`
**Issue:** `subject.replace('"', '\\"')` is a POSIX-shell escape only. On Windows 11 (PowerShell or cmd), `\"` terminates the string, so a subject containing a quote produces a broken command. `$`, backtick and `\` in the subject are not escaped at all.
- Library and symbol names are sanitized, so they cannot contain these characters.
- The subject comes from the user's own editable first line (for example "Add `foo` footprint"), and that line is copied as-is into a double-quoted string.
- The result is a command that fails, or expands text, when pasted.
- The `parent.as_posix()` path and `custom_rel` are also interpolated unquoted or with plain quotes.

**Fix:** Build the command so no user text goes into a quoted argument. Either use a single-quoted, platform-aware quote helper (`shlex.quote` on POSIX, PowerShell `'...'` with `''` doubling on Windows), or give `-F <file>` pointing at a saved message. At the least, escape `` ` ``, `$` and `\` as well as `"`.

### WR-04: A planned file that is unchanged against HEAD turns a correct commit into an ERROR and silently skips the parent bump

**File:** `kicad_lib_manager/importer/commit_step.py:486-497`
**Issue:** `result.touched` includes every file `_write` completed (applier.py `touched.append(op.path)`), even when the bytes written equal what HEAD already holds, for example an overwrite with identical content. `git commit --only` records only changed paths. `set(committed_files) != planned` then reports "{missing} missing" as ERROR, the panel goes to the "failed" state, and the parent bump is skipped ("The parent repo was not updated"). The Custom commit itself is correct. The user is pushed into a manual parent commit for no reason. I could not confirm that the planner emits such an op today (it may filter identical resolutions), so this is a latent edge case.

**Fix:** Only treat extra files (`committed - planned`) as the error. Treat missing files that are tracked and unchanged against HEAD as benign: list them as an INFO ("already identical to HEAD"), and continue to the parent step.

### WR-05: After a precheck refusal the panel returns to "ready" with a stale probe and cannot recover

**File:** `kicad_lib_manager/widgets/commit_panel.py:347-350`, `kicad_lib_manager/widgets/import_dialog.py:2217-2236`, `kicad_lib_manager/importer/commit_step.py:335-339`
**Issue:** `show_outcome()` for an outcome with nothing committed sets state "ready" and keeps the old probe. The dialog still passes `expected_branch=probe.branch` from the stale `_commit_probe`.
- `commit.branch_changed` (the user checked out another branch in Custom since the probe) is therefore unrecoverable: every further click fails with the same message.
- A refusal such as `commit.refused` (busy, identity) also leaves the old probe's amber markers, other-change counts and parent state on screen.

**Fix:** In `_on_commit_done`, when the outcome is not `committed`, start a fresh probe (`self._start_probe()`) after showing the refusal text. Show the refusal in the panel after the probe returns, so it is not cleared by `apply_probe()`'s `_clear_outcome()`.

## Info

### IN-01: `apply_probe` re-ticks the parent checkbox on every probe

**File:** `kicad_lib_manager/widgets/commit_panel.py:282-289`
**Issue:** `self._parent_check.setChecked(True)` runs on every probe. After "Switch to main" (which re-probes), a user who had unticked "Also commit the Custom ref in the parent repo" finds it ticked again. Commit still needs an explicit click, so this is not a safety defect, but it overrides a deliberate choice.
**Fix:** Keep the user's choice across a re-probe, for example by only calling `setChecked(True)` on the first probe after `show_plan`.

### IN-02: The dialog and main window cannot be closed during the read-only probe

**File:** `kicad_lib_manager/widgets/import_dialog.py:2123-2124, 2133-2146`, `kicad_lib_manager/main_window.py:925`
**Issue:** `_start_probe` registers its worker via `_set_git_worker`, so `is_committing()` is true during the probe. Close, Esc and the main window's X are blocked. The probe makes about 15 git calls, each with a 30 s timeout, so a hung git on a network or large repo can block closing for several minutes. A probe writes nothing, so waiting is not needed for safety (unlike the commit and the switch).
**Fix:** Treat the probe as closable. Do not set `_git_worker` for it (or use a separate flag), and let `_shutdown` wait on it. Keep the lock for the switch and the commit.

### IN-03: `run_git` shadows a builtin, and `_env` drops identity-related `GIT_*` variables

**File:** `kicad_lib_manager/gitops.py:91`, `kicad_lib_manager/gitops.py:74-78`
**Issue:**
- The `input` parameter shadows the builtin in `run_git`, `_commit_with_message`, `add_intent` and others. It is harmless today but is a trap for later edits.
- `_env` strips every `GIT_*` variable. A user who supplies identity or config through `GIT_AUTHOR_*`, `GIT_COMMITTER_*` or `GIT_CONFIG_GLOBAL` will see "git does not know who you are: set user.name and user.email" even though their own git works. The module docstring documents this as deliberate, but the message does not say it.

**Fix:** Rename the parameter to `stdin_data`. Optionally mention in the identity message that GIT_* variables are ignored and that identity must be in git config.

---

_Reviewed: 2026-10-22_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
