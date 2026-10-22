# Phase 6: Git Commit Step - Context

**Gathered:** 2026-10-22
**Status:** Ready for planning

<domain>
## Phase Boundary

After a successful install, the Import dialog's Result view offers one confirmed action. That action:

1. commits exactly the files the install touched in the `Custom` submodule;
2. then, optionally, commits the updated `Custom` gitlink in the parent repo.

The importer never pushes.

Requirements: GIT-01, GIT-02, GIT-03, GIT-04, GIT-05.

Not in this phase:
- pushing, in any form (Out of Scope in PROJECT.md);
- committing anything other than the import's own files, such as tables, `.planning/` or other `Custom/` edits;
- committing outside the Result view of the install that just happened (no menu entry, no "commit later");
- SnapEDA and SamacSys adapters (Phase 7).

</domain>

<decisions>
## Implementation Decisions

### Carried forward (locked)
- Git is driven through `subprocess` and the `git` CLI. There is no GitPython or pygit2, and no new runtime dependency (Init decision).
- The import flow itself never runs git. Phase 6 hooks into `ImportResultView.commit_slot` (`widgets/import_result.py`), which is currently hidden with zero height. It uses `ImportDialog.result` (`InstallResult`: `touched`, `vendor`, `source`, `library`, `new_library`) and `ImportDialog.result_plan` (`InstallPlan`, whose `ops` carry the written bytes) (Phase 5 D-15).
- Detached `Custom` HEAD: a switch to `main` is offered only when HEAD is on `main`'s history. Otherwise the commit is refused with an explanation, and nothing is committed (GIT-03, Requirements decision).
- No code path pushes (GIT-05). Every commit needs an explicit click (PROJECT.md Safety constraint).
- Services return `Issue` lists and route them by `Severity`. Errors go to the log panel and the slot, never to message boxes. Long work runs on a worker thread (conventions; Phase 5 D-10).
- Commit and parent-ref steps follow the CLAUDE.md git workflow: commit in the submodule first, then update the parent ref.

### Commit step flow (GIT-01)
- **D-01: The commit UI is inline in the Result view.** After a successful install, the `commit_slot` expands to show:
  - the `Custom` branch (or detached-HEAD state);
  - the read-only file list;
  - the editable commit message;
  - the parent-bump checkbox (D-12);
  - a **Commit** button.

  There is no separate dialog and no auto-popup.
- **D-02: Declining is simply not clicking.** If the user closes the Result view without committing, the files stay as uncommitted changes in `Custom`. One INFO/WARNING log line says "Not committed — commit manually". There is no close-confirmation and no later reminder.
- **D-03: Partial failure keeps the Custom commit.** If the `Custom` commit succeeds and the parent commit then fails (hook rejection, `index.lock`, ...):
  - the `Custom` commit stays, with no automatic `reset`;
  - an ERROR in the slot and the log shows git's output and the manual command to finish the job (e.g. `git commit -m ... -- Custom` in the parent);
  - there is no Retry button.
- **D-04: What a successful commit shows.**
  - The slot shows the short hash and branch of each commit made.
  - It adds "Not pushed — Custom is N ahead of origin/<branch>", plus the parent equivalent when one exists.
  - The message, checkbox and Commit button become read-only or disabled, so the commit can't be repeated.
  - The same facts go to the log.
- **D-05: Git missing means a disabled slot with the reason.** If `git` isn't on PATH, or `Custom` isn't a git work tree, the slot shows "Commit unavailable: <reason>" with no active button, and a WARNING goes to the log. The install result is unaffected.
- **D-06: Hooks always run.**
  - Never pass `--no-verify`, and offer no skip-hooks option.
  - A hook rejection is an ERROR, with the hook's stdout and stderr shown in the slot and the log.
  - Nothing is retried automatically.
- **D-07: Git work runs on a worker thread.** It reuses the dialog's existing `TaskWorker` / `_spawn` pattern.
  - While it runs, the message, checkbox, Commit and Close are locked, matching Install (Phase 5 D-10).
  - Step text is shown, e.g. "Committing in Custom…" and "Committing Custom ref in parent…".
  - Hooks can be slow, so the GUI thread never waits on git.
- **D-08: The only entry point is the Result view of a successful install.** A no-op install (`plan.is_noop`) or a failed install shows no commit step.

### Pre-existing changes (GIT-02)
- **D-09: A touched file with earlier uncommitted edits gets a warning, not a refusal.** This is the case when a file's pre-install content already differed from `HEAD`.
  - The file is flagged in amber in the list: "also contains uncommitted changes made before this import".
  - Double-clicking the file shows a read-only diff of `HEAD` against the pre-install content. Reuse the Phase 5 content view.
  - Commit stays possible; the user decides. There is no hunk-level partial staging.
- **D-10: Unrelated changes in `Custom` are left exactly as they were.** This covers other modified, untracked or already-staged files.
  - The commit uses only the listed paths, with pathspec / `--only` semantics, so other staged entries stay staged and uncommitted.
  - The slot shows "N other changes in Custom stay uncommitted". It does not list them by name.
  - `add -A` and `commit -a` are never used (GIT-02).
- **D-11: A file that changed after the install refuses the commit.** When the user clicks Commit, each touched file is compared with the bytes the install wrote (`plan.ops[*].data`). If any file differs, for example because it was edited in KiCad while the Result view was open:
  - the commit is refused and the file is named;
  - nothing is committed.

  This is the same stale-check idea as Phase 4.
- **D-11a: The file list is fixed and read-only.** It holds exactly the files the install touched. There are no checkboxes, because leaving a file out would commit a broken part (e.g. a symbol linked to an uncommitted footprint).

### Parent ref bump and branches (GIT-02, GIT-03)
- **D-12: The parent bump is a checkbox, on by default.** The label reads "Also commit the Custom ref in the parent repo (<parent branch>)". Unticking it commits in `Custom` only.
- **D-13: Earlier Custom commits ride along with the bump, and are listed.** If the parent's committed `Custom` gitlink is already behind `Custom`'s pre-import HEAD (true today: 485d530 against the owner's 49f746c), the bump necessarily includes those commits.
  - The slot shows "Parent bump also includes N earlier Custom commits:" with their short hash and subject.
  - The parent commit message lists them too (D-18).
  - This is allowed; it is not a reason to refuse.
- **D-14: Custom on a named branch other than `main` commits on that branch.** The branch name is shown in amber with a "not main" note. GIT-03's switch/refuse logic applies only to a detached HEAD.
- **D-15: A detached Custom HEAD on `main`'s history offers a switch.**
  - The offer shows how many commits `main` is ahead.
  - The switch is a plain `git switch main`, so git carries the import's uncommitted changes over when it safely can.
  - If git refuses (e.g. a conflict with files `main` changed), git's reason is shown and nothing is committed.
  - Never use `--force`, `stash` or `reset`.
  - A detached HEAD that is not on `main`'s history refuses the commit with an explanation (GIT-03).
- **D-16: Both repos are pre-checked before anything is committed.**
  - **Parent:** a detached HEAD, a merge, rebase, cherry-pick or revert in progress, or no parent git repo means the parent checkbox is unticked and disabled, with the reason shown. A Custom-only commit is still possible.
  - **Custom:** a merge, rebase or similar in progress disables the whole commit step, with the reason shown.
- **D-17: The parent commit contains only the `Custom` gitlink.** It uses pathspec `Custom` only. Every other parent change, staged or not (e.g. `.planning/` edits), stays exactly as it was.
- **D-17a: The parent is whatever repo the app runs from (`REPO_ROOT`).** There is no special case for a git worktree. The slot shows the parent path and branch, so a worktree on `feature/part-importer` is obvious. Unlike the KiCad path-variable rule (Quick 261022-gnn), a worktree is not refused here.

### Commit message format (GIT-01, GIT-04)
- **D-18: Default messages.**
  - The `Custom` message is a sentence-style subject that matches the existing `Custom` history, then a short body, then git trailers:
    ```
    Add <Symbol> to <Library>

    Symbol: <Symbol>
    Footprint: <Library>:<FP>
    3D model: <file>            (line omitted when no model was installed)

    Import-Vendor: <vendor>
    Import-Package: <original package filename>
    Import-Date: <YYYY-MM-DD>
    ```
    A new library may say "Add <Symbol> to new library <Library>". A rename or overwrite case may adjust the verb; Claude decides the exact wording.
  - The parent message mirrors the Custom subject and lists the commits the bump covers:
    ```
    Update Custom: <Custom subject>

    Custom <old>..<new>
    - <hash> <subject>
    - <hash> <subject>   (earlier commits included by the bump, D-13)
    ```
- **D-19: Only the Custom message is editable.**
  - The Custom message is an editable multi-line field (GIT-01).
  - The parent message is generated from it and shown read-only. It updates as the Custom subject changes.
- **D-20: The user's message wins.**
  - The pre-filled text satisfies GIT-04.
  - If the user deletes the provenance trailers, what they typed is what gets committed; nothing is re-appended.
  - An empty or whitespace-only message disables Commit, with a reason.

### Claude's Discretion
- Module layout. For example: a Qt-free `kicad_lib_manager/gitops.py` service (status, pre-checks, commit, ahead count) returning `Issue` lists and dataclasses; a `widgets/commit_panel.py` placed into `commit_slot`; wiring in `import_dialog.py`.
- **How "touched" maps to committable paths.** `InstallResult.touched` can include `mkdir` ops, i.e. directories. Commit only the files: committing a `.pretty/` directory pathspec would sweep in other untracked footprints. A reused 3D model (same SHA-256, not rewritten) is not committed.
- **How the pre-install state for D-09 is found.** Options include the Phase 4 backup pre-image in `backup_dir`, `FileOp.base_sha256`, or `git diff`. Any of these is acceptable if it is exact.
- The exact git invocations, for example:
  - `git -C Custom commit --only -m ... -- <paths>` with `add` of new files first, or `git commit -- <paths>` after `git add -- <paths>`;
  - detecting a detached HEAD on `main`'s history (`merge-base --is-ancestor`);
  - the ahead count (`rev-list --count @{u}..HEAD`, skipped when there is no upstream);
  - `CREATE_NO_WINDOW` on Windows, as in `kicad_process.py`.
- The display date format and timezone (local date, ISO `YYYY-MM-DD`).
- How the vendor display name is derived from `InstallResult.vendor` (e.g. "Ultra Librarian").
- Fixing Phase 5 review items where the touched code overlaps: WR-04 (the worker reads `self._plan`; `open_path` has no install guard), because Phase 6 adds another worker to the same dialog.
- **Test strategy.**
  - Unit tests against throwaway git repos created in `tmp_path`: a superproject with a submodule; detached, branch and mid-merge states; a dirty pre-existing file; staged unrelated files; a failing hook; git absent.
  - pytest-qt tests for the slot's state machine.
  - A manual UAT committing a real import in `Custom/`, then checking `git status` and that nothing was pushed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and requirements
- `.planning/ROADMAP.md` § "Phase 6: Git Commit Step": goal, success criteria 1–4, and the **research flag** (spike git early: worktree-private module gitdir `.git/worktrees/Kicad_Libraries-importer/modules/Custom`, behaviour of `commit -- Custom` in the parent, the owner's hooks)
- `.planning/REQUIREMENTS.md`: GIT-01..GIT-05
- `.planning/PROJECT.md`: Out of Scope ("Pushing to remotes"), the Safety constraint, Key Decisions ("Commit in Custom + bump parent ref after confirmation; never push"; "The import flow never runs git; the Result view holds a hidden commit slot for Phase 6")
- `CLAUDE.md` § "Git Workflow": submodule commit first, then the parent ref

### Prior phase decisions
- `.planning/phases/05-import-ui-and-post-install/05-CONTEXT.md`: D-10 (install worker, locked inputs, no Cancel), D-15 (Result view and commit slot hand-off), D-08 (content and diff view), D-09 (amber constant, blocking-reason pattern)
- `.planning/phases/05-import-ui-and-post-install/05-REVIEW-DISPOSITION.md`: WR-04 and WR-05 touch the dialog Phase 6 extends
- `.planning/phases/04-plan-and-install-core/04-CONTEXT.md`: "Phase 6 commits exactly the files the install touched", stale-plan re-check pattern, backups (D-18/D-19)
- `.planning/phases/02-hardening-existing-code/02-07-SUMMARY.md`: precedent for a Custom commit plus a parent gitlink bump with nothing pushed

### Codebase maps
- `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONVENTIONS.md`: layering (services Qt-free, widgets never import `main_window`), `Issue`/`Severity` routing, `QThread` workers

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `widgets/import_result.py` `ImportResultView.commit_slot`: a reserved, hidden, zero-height `QWidget`; `show_result(result, plan, repo_root)` fills the view.
- `widgets/import_dialog.py`:
  - `self.result` / `self.result_plan` are set in `_on_install_done`;
  - `_spawn(...)` gives a `TaskWorker` with `result` / `failed` signals;
  - `issues_logged` signal sends Issues to the main log;
  - `_on_written_file_activated` shows how to open the content view for a written file.
- `importer/plan.py`:
  - `InstallResult(ok, library, new_library, touched, issues, backup_dir, vendor, source)`;
  - `FileOp(kind, path, data, base_sha256, listed_path)`, where `kind` is `mkdir` | `model` | `footprint` | `symbol_lib`.
- `importer/applier.py`: `txn.touched` collects every written path, including `mkdir`; `backup_dir` holds the pre-images.
- `widgets/content_view.py`: the read-only diff and content viewer to reuse for D-09.
- `widgets/theme.py`: the shared amber constant for D-09 and D-14 highlights.
- `kicad_process.py` / `importer/kicad_cli.py`: `subprocess.run` patterns with `capture_output`, timeout and `CREATE_NO_WINDOW`, plus an injectable `runner` for tests.

### Established Patterns
- Side-effecting services return `Issue` lists and never raise for expected failures.
- Workers emit results and the GUI applies them. A `_closing` guard drops late results.
- Paths are `Path`. Repo-relative display uses `relative_to(repo_root).as_posix()`.

### Integration Points
- `ImportDialog._show_result` → populate the commit panel from `result` + `result_plan` + `repo_root`.
- `MainWindow` passes `REPO_ROOT` to the dialog. The parent repo is `REPO_ROOT`, and `Custom` is `REPO_ROOT / "Custom"`.
- Current live state, observed 2026-10-22:
  - `Custom` is on `main`, tracking `origin/main`, not detached;
  - the parent worktree already has an uncommitted gitlink change 485d530 → 49f746c (D-13 case);
  - the `Custom` gitdir is `C:/Git_Repo_Clones/Kicad_Libraries/.git/worktrees/Kicad_Libraries-importer/modules/Custom`.

</code_context>

<specifics>
## Specific Ideas

- The commit messages should read like the owner's existing `Custom` history (sentence-style subjects), not conventional-commit prefixes. Provenance goes in `Import-*` trailers.
- The "not pushed — N ahead" note is the visible guarantee of GIT-05.

</specifics>

<deferred>
## Deferred Ideas

- Copyable `git push` commands in the slot. Offered and not chosen; it could be revisited later. It would never run them.
- A "commit last import" menu entry or a reminder for uncommitted imports. Not chosen; it would need persisted state.
- Hunk-level partial staging that commits only the import's changes when a file was already dirty. Not chosen in favour of warn-and-allow (D-09).

</deferred>

---

*Phase: 06-git-commit-step*
*Context gathered: 2026-10-22*
