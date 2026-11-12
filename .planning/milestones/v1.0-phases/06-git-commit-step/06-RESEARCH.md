# Phase 6: Git Commit Step - Research

**Researched:** 2026-10-22
**Domain:** Driving the `git` CLI (stdlib `subprocess`) from a PySide6 dialog: a path-limited commit in a submodule whose gitdir is worktree-private, then a gitlink commit in the parent. No push, ever.
**Confidence:** HIGH for every git behaviour (each was reproduced in a throwaway repo this session on git 2.49.0.windows.1). MEDIUM for the Qt wiring (read from source, not run).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Carried forward (locked)
- Git is driven through `subprocess` and the `git` CLI. There is no GitPython or pygit2, and no new runtime dependency (Init decision).
- The import flow itself never runs git. Phase 6 hooks into `ImportResultView.commit_slot` (`widgets/import_result.py`), which is currently hidden with zero height. It uses `ImportDialog.result` (`InstallResult`: `touched`, `vendor`, `source`, `library`, `new_library`) and `ImportDialog.result_plan` (`InstallPlan`, whose `ops` carry the written bytes) (Phase 5 D-15).
- Detached `Custom` HEAD: a switch to `main` is offered only when HEAD is on `main`'s history. Otherwise the commit is refused with an explanation, and nothing is committed (GIT-03, Requirements decision).
- No code path pushes (GIT-05). Every commit needs an explicit click (PROJECT.md Safety constraint).
- Services return `Issue` lists and route them by `Severity`. Errors go to the log panel and the slot, never to message boxes. Long work runs on a worker thread (conventions; Phase 5 D-10).
- Commit and parent-ref steps follow the CLAUDE.md git workflow: commit in the submodule first, then update the parent ref.

#### Commit step flow (GIT-01)
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

#### Pre-existing changes (GIT-02)
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

#### Parent ref bump and branches (GIT-02, GIT-03)
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

#### Commit message format (GIT-01, GIT-04)
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

### Deferred Ideas (OUT OF SCOPE)
- Copyable `git push` commands in the slot. Offered and not chosen; it could be revisited later. It would never run them.
- A "commit last import" menu entry or a reminder for uncommitted imports. Not chosen; it would need persisted state.
- Hunk-level partial staging that commits only the import's changes when a file was already dirty. Not chosen in favour of warn-and-allow (D-09).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GIT-01 | After install, user is asked to confirm a commit and sees the branch, the exact file list and an editable message | `touched` holds files only (see Pattern 3); branch via `symbolic-ref -q --short HEAD`; message builder (Pattern 5); inline panel in `commit_slot` (Pattern 6) |
| GIT-02 | On confirm, only the files touched by the install are committed in `Custom` (never `add -A`), then the parent's `Custom` ref is committed | `add -N` + `commit --only -F ... --pathspec-from-file=- --pathspec-file-nul` with `--literal-pathspecs` (Pattern 2, spike S3-S5); parent `commit --only -- Custom` (spike S6) |
| GIT-03 | Detached `Custom` HEAD on `main`'s history: offer a switch to `main`; otherwise refuse | `merge-base --is-ancestor HEAD <mainref>` + plain `git switch main` (spike S7-S9); refusal cases proven |
| GIT-04 | Commit message records vendor, original package filename and date | D-18 trailers; `git log --format=%(trailers)` parses them (spike S4); sanitise untrusted values (Security) |
| GIT-05 | The importer never pushes | Single `run_git` choke point with a subcommand allow-list that has no `push`; argv-recording test; remote-ref snapshot test (Pattern 1, spike S12) |
</phase_requirements>

## Summary

The research flag asked three questions: how git behaves with the worktree-private `Custom` gitdir, how `commit -- Custom` behaves in the parent, and what the owner's hooks do. All three are answered by running real git. In a repro built in the session scratchpad (bare remotes, a parent, a linked worktree whose `Custom/.git` contains `gitdir: ../../parent/.git/worktrees/wt/modules/Custom`, HEAD detached), every command in this document worked unchanged. The worktree-private layout needs no special handling as long as every call uses `git -C <path>` and asks git for `--git-path` locations instead of assuming `.git/`. The owner's real repo has no hooks in either place (only `*.sample` files in `C:/Git_Repo_Clones/Kicad_Libraries/.git/hooks` and in the `Custom` modules gitdir) and no `core.hooksPath`, so hook behaviour is currently "nothing runs"; the failure path was still tested with a hook I installed in the scratch repo.

The recommended mechanism is small and exact. Mark the new files with `git add -N` (intent-to-add; `commit --only` refuses paths git does not know), then run `git --literal-pathspecs commit --only -F <msgfile> --pathspec-from-file=- --pathspec-file-nul` with NUL-separated paths on stdin. Pre-staged unrelated entries stay staged, unstaged edits stay unstaged, untracked files stay untracked (proved with all four kinds present at once). The parent step is `git commit --only -F <msgfile> -- Custom`; it commits only the gitlink even with a staged `.planning/` file, an unstaged `README.md` edit and an untracked file present, and a dirty submodule is fine. `--literal-pathspecs` is not optional: without it, a pathspec `3DModels/AB[1].step` silently committed a different file, `AB1.step` (reproduced).

Two things in CONTEXT.md need correcting before planning. First, `InstallResult.touched` never contains directories: `_make_folders` records `mkdir` only in the undo list, and only `_write` appends to `touched`. So the "files only" filter is already satisfied, though keeping a defensive `is_file()` check is cheap. Second, the parent message in D-18 contains `Custom <old>..<new>`, but `<new>` does not exist until the Custom commit has run, so the preview must show a placeholder and the final text must be built after the Custom commit. The live state also moved since CONTEXT was written: `Custom` is on `main` at `d3ff246` (not detached, not ahead of `origin/main`), and the parent's committed gitlink is still `485d530`, so the D-13 bump would list `49f746c` and `d3ff246` today.

**Primary recommendation:** Build a Qt-free `kicad_lib_manager/gitops.py` whose only subprocess entry is `run_git(repo, *args)` (allow-list of subcommands, `--literal-pathspecs`, scrubbed `GIT_*` env, `CREATE_NO_WINDOW`), use `add -N` then `commit --only -F <tmp> --pathspec-from-file=- --pathspec-file-nul` for Custom and `commit --only -F <tmp> -- Custom` for the parent, and run probe, switch and commit as three separate `TaskWorker` jobs behind an explicit state machine in `widgets/commit_panel.py`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Git state probe (branch, detached, busy markers, ahead count, other-changes count) | Service (`gitops.py`, Qt-free) | Worker thread | Plain function returning dataclasses; the GUI must not wait on git (D-07). |
| Commit, switch, parent bump | Service (`gitops.py`) | Worker thread | Side effects return `Issue` lists; never raise for expected failures (conventions). |
| Mapping `InstallResult`/`InstallPlan` to repo-relative paths, expected hashes, pre-install hashes | Importer service (`importer/commit_plan.py`, Qt-free) | — | Needs `plan.ops`/`FileOp`; keeps `gitops.py` free of importer imports (layering tests). |
| Default message text, sanitising, parent message | Service (pure functions) | — | Pure strings, unit-testable without git or Qt. |
| Inline panel, state machine, amber highlights, message editor | Widget (`widgets/commit_panel.py`) | `ImportResultView.commit_slot` | Widgets own layout only; no git calls (they take callbacks or signals). |
| Worker lifecycle, close guards, log routing | Dialog (`import_dialog.py`) | `MainWindow` (log) | The dialog already owns `TaskWorker`, `_closing`, `issues_logged`. |
| Hooks, signing, identity | External `git` | — | Hooks always run (D-06); the app only surfaces stdout/stderr. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `subprocess` | Python 3.14 (venv) | Run `git` | Locked by CONTEXT (no GitPython/pygit2). `kicad_process.py` and `importer/kicad_cli.py` already use the same `subprocess.run(..., capture_output, timeout, creationflags=CREATE_NO_WINDOW)` shape. |
| Python stdlib `tempfile`, `hashlib`, `datetime`, `pathlib`, `os` | — | Message temp file, sha256 checks, ISO date | No dependency needed. |
| `git` CLI | 2.49.0.windows.1 on the owner's machine [VERIFIED: `git --version`] | All git work | Must support `commit --pathspec-from-file` and `git switch`; both worked on 2.49. |
| PySide6 | 6.12.0 (pinned in `requirements.txt` per Phase 1) | Panel, `TaskWorker` (QThread) | Existing. |
| pytest 9.1.1, pytest-qt 4.5.0 | pinned in `requirements-dev.txt` | Tests | Existing. [VERIFIED: requirements-dev.txt read this session] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `git add -N` + `commit --only` | `git add -- paths` then `commit -- paths` | Real `add` stages content and leaves it staged if a hook rejects; `-N` stages nothing but the name, and `git reset -q -- paths` undoes it exactly (spike S5). |
| `-F <tempfile>` for the message | `-m <message>` | Works, but a multi-line message with quotes passes through the Windows command line. The file is exact and keeps stdin free for pathspecs. |
| Pathspecs on stdin (`--pathspec-from-file=- --pathspec-file-nul`) | Pathspecs after `--` | argv is fine for four files; stdin has no length limit and no quoting. Both need `--literal-pathspecs`. |

**Installation:** none. No new package.

**Version verification:** not applicable (stdlib and an already-pinned stack). `git --version` printed `git version 2.49.0.windows.1`.

## Package Legitimacy Audit

No external packages are installed in this phase (stdlib + already-pinned PySide6/pytest/pytest-qt). Nothing to audit.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 install succeeds ──► ImportDialog._on_install_done(worker, plan, result)
                         │ result.ok and not plan.is_noop            (D-08)
                         ▼
              importer/commit_plan.build(result, plan, custom_dir)   (pure, no git)
                 → CommitPlan: rel paths (files only), expected sha256 per file,
                   base_sha256 per file, vendor label, package filename, symbol, fp, model
                         │
                         ▼
        commit_panel.start_probe()  ── TaskWorker #1 (read-only git) ──────────────┐
                                                                                    │
   gitops.probe_custom(): toplevel==Custom? | branch / detached | busy marker       │
                          main ref + HEAD-on-main + main-ahead | upstream | identity│
                          other-changes count | per-file "dirty before import"      │
   gitops.probe_parent(): is repo? | branch / detached | busy marker | gitlink old   │
                          earlier Custom commits old..HEAD | upstream               │
                         │◄───────────────────────────────────────────────────────┘
                         ▼
   ┌──────────── panel state ────────────────────────────────────────────────────┐
   │ Unavailable(reason)  ◄─ git missing / Custom not own toplevel / busy (D-05,16)│
   │ Refused(reason)      ◄─ detached and not on main's history (GIT-03)          │
   │ OfferSwitch(n ahead) ─► [Switch to main] ─► TaskWorker #2 `git switch main`   │
   │                          rc!=0 → show git stderr, stay detached (D-15)       │
   │ Ready                ─► [Commit] (message non-blank, D-20)                    │
   └──────────────────────────────────────────────────────────────────────────────┘
                         │ click Commit
                         ▼
        TaskWorker #3 (everything below runs in one job; progress() = step text)
          1 stale check: sha256(file on disk) == expected   → refuse + name file (D-11)
          2 re-probe busy/branch (state may have changed while the view was open)
          3 add -N new files ──► commit --only (hooks run) ──► rc!=0: reset -q, ERROR (D-06)
          4 read new HEAD, ahead count
          5 if parent box ticked: build parent message (now knows <new>) ──►
            commit --only -F … -- Custom ──► rc!=0: ERROR + manual command (D-03)
          6 return CommitOutcome (hashes, branches, ahead counts, issues)
                         ▼
        panel: Done (read-only, "Not pushed — Custom is N ahead of origin/main")  (D-04)
        dialog: issues_logged.emit(issues);  nothing ever calls `git push`          (GIT-05)
```

### Recommended Project Structure
```
kicad_lib_manager/
├── gitops.py                  # NEW  Qt-free. run_git choke point, probes, commit, switch. Imports models only.
├── importer/commit_plan.py    # NEW  Qt-free. InstallResult+InstallPlan -> CommitPlan; message builders. Imports models, importer.plan.
└── widgets/
    ├── commit_panel.py        # NEW  CommitPanel(QWidget): state machine, no git calls
    ├── import_result.py       # EDIT commit_slot becomes a real container (see Pitfall 9)
    └── import_dialog.py       # EDIT spawn probe/switch/commit workers; close guards; WR-04 fix
tests/
├── gitfixtures.py             # NEW  builds remote + superproject + submodule (+ linked worktree) in tmp_path
├── test_gitops.py             # NEW
├── test_commit_plan.py        # NEW
├── test_commit_panel.py       # NEW  pytest-qt
├── test_layering.py           # EDIT register `gitops` in ALLOWED (+ the Qt-free import list)
├── test_importer_layering.py  # EDIT register `importer.commit_plan`
└── test_import_dialog.py      # EDIT line ~2743 asserts the slot is hidden, height 0, maximumHeight 0
```
Reason for the split: top-level modules never import `importer` (`library_scanner` imports only `fsutil, kicad_files, kicad_process, models`) and every importer module must be registered in `ALLOWED` in `tests/test_importer_layering.py`. Keeping `gitops.py` free of `InstallPlan` means it needs no upward import. [VERIFIED: tests/test_layering.py lines 14-23 and tests/test_importer_layering.py read this session]

### Pattern 1: One choke point for git, with an allow-list (GIT-05, T-injection)
**What:** every git call goes through `run_git`. It asserts the subcommand is in a frozen allow-list that does not contain `push`, scrubs `GIT_*` from the environment, sets non-interactive variables, and records argv for tests.
**When to use:** always; there is no second place that spawns git.
**Example (validated in the spike, `gitops_spike.py`, run end to end):**
```python
# Source: spike in scratchpad, executed against the repro (41 git calls, 0 push, remote refs unchanged)
ALLOWED = {"--version", "rev-parse", "symbolic-ref", "status", "merge-base", "rev-list", "log", "ls-tree",
           "cat-file", "var", "for-each-ref", "add", "reset", "switch", "commit", "ls-files"}

def _env():
    e = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}   # a stray GIT_DIR / GIT_INDEX_FILE would redirect every call
    e.update({"GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "GIT_EDITOR": "true", "LC_ALL": "C"})
    return e

def run_git(repo, *args, input=None, timeout=120.0):
    sub = next(a for a in args if not a.startswith("-") or a == "--version")
    assert sub in ALLOWED, f"git {sub} is not allowed"
    argv = ["git", "--literal-pathspecs", "-c", "core.quotepath=false", "-C", str(repo), *args]
    p = subprocess.run(argv, input=input, capture_output=True, env=_env(), timeout=timeout,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return p.returncode, p.stdout, p.stderr
```
Make the runner injectable (`runner=` parameter, as `kicad_cli.py` does with `run = runner or subprocess.run`) so tests can record argv and assert no element is `push`. Do not test "push" by grepping git's output: git's own hint text contains the word ("use "git push" to publish your local commits") [VERIFIED: spike S11].

### Pattern 2: The path-limited Custom commit (GIT-02)
**What:** `add -N` the paths git does not yet know, then commit only those paths from the working tree.
```text
git --literal-pathspecs -C Custom add -N -- <new files only>
git --literal-pathspecs -C Custom commit --only -F <msgfile> --pathspec-from-file=- --pathspec-file-nul   # stdin: path\0path\0...
# on rc != 0:  git --literal-pathspecs -C Custom reset -q -- <the same new files>     (undoes intent-to-add only)
```
Which files are "new": `git ls-files -- <paths>` (tracked ones are listed); the rest need `add -N`. Do not use `base_sha256 is None` for this: a file can exist on disk but be untracked in git (a pre-existing untracked file is also "dirty before import", D-09).

### Pattern 3: Touched files, expected bytes, pre-install state (D-09, D-11)
- `InstallResult.touched` is a tuple of file paths only. [VERIFIED: applier.py:487-488 `if op.kind == "mkdir": return _make_folders(plan, op, undo)` returns before any append; applier.py:504 `touched.append(op.path)` is the only append.] Keep a defensive `Path.is_file()` filter anyway.
- A reused identical model produces no op, so it is never in `touched`. (CONTEXT assumed this; consistent with `make_model_op` only being called for a decision that yields an op.)
- Map each touched path to its `FileOp` with `next(op for op in plan.ops if op.path == path)`, as `_on_written_file_activated` does.
- Expected bytes for D-11: `op.data` for `symbol_lib` and `footprint`; for `model` ops `data` is `None` and the bytes come from the package, so use `op.source.sha256` (a hex digest string, so the staged file need not still exist). [VERIFIED: planner.py:863-868 `FileOp("model", model_dir / name, source=model_item_file, base_sha256=digest, ...)`; planner.py:933-937 `FileOp("footprint", ..., data=render_fp(index, name)[0], ...)`; planner.py:1104 `FileOp("symbol_lib", sym_path, data=sym_bytes, base_sha256=base)`; applier.py:489 `data = source_bytes if source_bytes is not None else op.data`.]
  ```python
  expected = hashlib.sha256(op.data).hexdigest() if op.data is not None else op.source.sha256
  ```
- D-09 "pre-install content differed from HEAD": compare `op.base_sha256` with the sha256 of what git would put in the working tree for HEAD:
  ```text
  git cat-file --filters HEAD:<rel>        # smudged bytes; sha256 of these == base_sha256 means the file was clean
  ```
  Dirty if the command fails (file not in HEAD, i.e. it existed on disk untracked) or the hash differs. `base_sha256 is None` means the install created the file: never dirty. This is exact for the case that matters here because the owner has `core.autocrlf = true` (system gitconfig) and `Custom` shows `i/lf w/crlf`: the committed blob is LF, the working tree is CRLF. `git cat-file --filters` re-applies the smudge, so its sha256 equals the working-tree sha256 of a clean file, while the raw blob (`cat-file blob`) does not. [VERIFIED: real Custom, `Symbols/Connector_FFC_GCT.kicad_sym`: working tree sha256 `41520a6f2c691ec1…`, `--filters` `41520a6f2c691ec1…`, raw blob `43d0901e99e63213…`.] Edge: a working-tree file with mixed line endings is "clean" to git but hashes differently, giving a false amber warning. That is harmless (warn, not refuse) and acceptable.
- The diff for double-click (D-09): HEAD side = `git cat-file --filters HEAD:<rel>` bytes; pre-install side = the Phase 4 backup copy. Backup names are `<name>_backup_<N>` in `result.backup_dir` and collide across same-named files, so pick the candidate whose sha256 equals `op.base_sha256`. [VERIFIED: fsutil.py:173-200 `backup_file` names the copy `f"{path.name}_backup_{number}"`.] Render with the existing Qt-free `diff_text(old, new, old_label, new_label)` and `ContentText(title, header, body, kind="diff")` from `importer/content.py`, shown through `ContentViewDialog`. [VERIFIED: content.py:23-35, 51-56; content_view.py:1-75.]

### Pattern 4: Detached HEAD policy (GIT-03, D-14, D-15)
```text
branch        : git symbolic-ref -q --short HEAD          rc 0 → name; rc 1 → detached
main ref      : first of refs/heads/main, refs/remotes/origin/main that passes `git rev-parse -q --verify <ref>`
on history    : git merge-base --is-ancestor HEAD <mainref>   rc 0 → yes, rc 1 → no (diverged or ahead of main)
main ahead by : git rev-list --count HEAD..<mainref>
switch        : git switch main        (plain; carries local changes; no --force/--merge/--discard-changes)
```
Observed (all in the repro):
- Detached, HEAD ancestor of `main`: `git switch main` succeeds, carries a staged file, an unstaged edit, an untracked file and the import files unchanged. [VERIFIED: S7]
- Detached, no local `main` branch, `origin/main` exists: plain `git switch main` creates `main` tracking `origin/main` ("branch 'main' set up to track 'origin/main'.") and carries changes. This is the `--guess` default [CITED: git-scm.com/docs/git-switch "--guess is the default behavior"]. [VERIFIED: S8]
- Detached with its own commit (diverged): `merge-base --is-ancestor` exits 1 → refuse. [VERIFIED: S9]
- Detached, import edits a file `main` also changed: `git switch main` exits 1 with `error: Your local changes to the following files would be overwritten by checkout: Symbols/Conn_A.kicad_sym … Aborting`; HEAD stays detached, the working tree is untouched. Show git's stderr. [VERIFIED: S9]
- git writes the `M<TAB>path` list and "Switched to branch" to stderr, so a successful switch still has non-empty stderr. Use the exit code, never stderr emptiness.

### Pattern 5: Commit message (GIT-01, GIT-04, D-18..D-20)
- Trailer block verified: with the D-18 layout, `git log -1 --format='%(trailers:only,unfold)'` returned exactly the three `Import-*` lines; the `Symbol:`/`Footprint:`/`3D model:` block above them is a separate paragraph. [VERIFIED: S4]
- A message containing a `# not a comment` line, an em dash and an accented letter round-tripped byte-identical through `-F <tempfile>` (`git log -1 --format=%B` equals the input). The default cleanup for a non-edited message is `whitespace`, which keeps `#` lines [CITED: git-scm.com/docs/git-commit "--cleanup … default: Same as strip if the message is to be edited. Otherwise whitespace."]. [VERIFIED: S10]
- Write the message as UTF-8 to a `tempfile.NamedTemporaryFile(delete=False)` in the user temp dir and delete it in a `finally`. Do not put it in the repo.
- The parent message cannot be final at preview time. D-18's `Custom <old>..<new>` needs the new Custom commit. Show the preview with a literal placeholder (for example `<new commit>`), and build the real parent message inside the commit job after the Custom commit succeeds: old = the parent's `HEAD` gitlink (`git ls-tree HEAD Custom` third field), new = `git rev-parse HEAD` in Custom, list = `git log --reverse --format=%h %s <old>..<new>`. If `<old>` is not an ancestor or not present in Custom (`rc != 0`), omit the list and say so.
- Vendor label: `import_dialog.vendor_label(result.vendor)` (`_VENDOR_LABELS = {"UltraLibrarian": "Ultra Librarian", "Loose": "Loose files", "Unknown": "Unknown vendor"}`). [VERIFIED: import_dialog.py:81-86.] Pass the finished string into the pure builder so `importer/commit_plan.py` does not import a widget module.
- Package filename: `result.source.name` (`InstallResult.source: Path | None`). For a folder package this is the folder name; word the trailer value accordingly and fall back to `""`→omit the line only if `source` is `None`.
- Date: `datetime.date.today().isoformat()` (local date).

### Pattern 6: Panel state machine and dialog wiring (D-01, D-05..D-08)
States: `Probing → Unavailable | Refused | OfferSwitch | Ready → Committing → Done | Failed`. `Failed` after a partial success keeps the Custom hash visible (D-03). Only `Ready` enables Commit, and only when the message is non-blank (D-20).
- `ImportResultView.commit_slot` is currently `setFixedHeight(0)` + `hide()`, which sets both minimum and maximum height to 0. [VERIFIED: import_result.py:190-194 `self.commit_slot.setFixedHeight(0)` / `self.commit_slot.hide()`.] To expand it call `setMinimumHeight(0)`, `setMaximumHeight(QWIDGETSIZE_MAX)` (16777215), then `show()`; or replace the placeholder by a real container. The Phase 5 test must change in the same plan: `tests/test_import_dialog.py:2743-2744` asserts `slot.isHidden() and slot.height() == 0 and slot.maximumHeight() == 0` after a successful install. [VERIFIED: read this session.]
- The result page replaces the Edit page in place; `view.close_button.clicked` is wired to `self.accept`. [VERIFIED: import_dialog.py:686-687.] `ImportDialog.done()` only blocks while `is_installing()`. [VERIFIED: import_dialog.py:2187-2192 `if self.is_installing(): return`.] Add `is_committing()` (probe, switch and commit workers) to `done`, `closeEvent` and the Esc handler, exactly like install, otherwise Close during a slow hook calls `_shutdown()` which `wait()`s on the worker on the GUI thread (the WR-05 failure mode).
- D-02: emit one WARNING `Issue` ("Not committed — commit manually") from `done()` when the panel was `Ready` (or `OfferSwitch`) and nothing was committed. Do not ask for confirmation.
- WR-04 (in scope per CONTEXT): the install lambda reads `self._plan` on the worker thread (`lambda progress: core.apply_plan(self._plan, ...)` at import_dialog.py:2038 while `plan = self._plan` is already captured at 2032). Capture `plan` and pass that: `lambda progress, p=plan: core.apply_plan(p, ...)`. Also add an `is_installing()`/`is_committing()` guard at the top of `open_path` (line 972 currently checks only `_closing` and `_open_worker`).
- Worker pattern to reuse: `worker = self._spawn(fn)`, `worker.result.connect(...)`, `worker.failed.connect(...)`, drop late results when `self._closing`. [VERIFIED: import_dialog.py:170-192, 2036-2047, 2105-2111.] `TaskWorker.run` already converts an unexpected exception into `failed`, so the commit job only needs to return a dataclass.
- Use `Severity` routing and plain text only (`Qt.TextFormat.PlainText`); git output can contain anything. `Severity` values are `INFO = "info"`, `WARNING = "warning"`, `ERROR = "error"`, `SUCCESS = "success"`. [VERIFIED: models.py:5-10.] Amber is `theme.AMBER`/`theme.AMBER_TINT`. [VERIFIED: theme.py:4-5.]

### Anti-Patterns to Avoid
- **`git add -A`, `commit -a`, `add <dir>/`:** forbidden by GIT-02. A `.pretty/` pathspec would also commit other untracked footprints.
- **Pathspecs without `--literal-pathspecs`:** reproduced committing the wrong file (Pitfall 1).
- **Treating non-empty stderr as failure:** CRLF warnings (`warning: in the working copy of 'x', LF will be replaced by CRLF…`) appear on every add and commit with the owner's `core.autocrlf=true`, and a successful `switch` prints to stderr. Use the exit code.
- **`git status` for decisions without `GIT_OPTIONAL_LOCKS=0`:** a status refresh can take `index.lock` and collide with VS Code or another git tool.
- **Parsing human text** ("nothing to commit", "Aborting"): use exit codes and plumbing (`rev-parse`, `symbolic-ref`, `merge-base`, `status --porcelain=v1 -z`). Show the text, never branch on it.
- **Adding `--no-verify`, `--no-gpg-sign`, `-f`, `--force`, `stash`, `reset --hard`:** none are needed. The only `reset` is path-limited `reset -q -- <intent-to-add paths>`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Partial/path-limited commits | Temporary index files, `update-index`, `write-tree` plumbing | `git commit --only` | Git already builds a private index for `--only`; other staged entries are preserved (S3). [CITED: git-commit docs "ignore changes staged in the index, and instead record the current content of the listed files (which must already be known to Git)"] |
| Line-ending normalisation when comparing to HEAD | A CRLF/LF stripper | `git cat-file --filters HEAD:<path>` or `git hash-object --path=<rel> --stdin` | The owner's tree is `i/lf w/crlf`; git applies the right filter. |
| "Is HEAD on main" | Walking `git log` output | `git merge-base --is-ancestor` | Exit-code contract, handles merges. |
| "Merge/rebase in progress" | Looking for `.git/MERGE_HEAD` | `git rev-parse --git-path MERGE_HEAD` (and `rebase-merge`, `rebase-apply`, `CHERRY_PICK_HEAD`, `REVERT_HEAD`, `BISECT_LOG`) | In a linked worktree or a worktree-private submodule these live under `.git/worktrees/<wt>/modules/Custom/`, not under `Custom/.git` (a *file*). `--git-path` resolves it. [VERIFIED: S1] |
| Trailer parsing in tests | Regex | `git log -1 --format='%(trailers:only,unfold)'` | What git itself will report. |
| Message passing | Shell quoting | `-F <tempfile>` | Exact bytes, no quoting. |

**Key insight:** every hard part of this phase is already a git primitive with an exit-code contract. The code to write is orchestration, state handling and refusing early, not git logic.

## Common Pitfalls

### Pitfall 1: Pathspec globbing commits the wrong file
**What goes wrong:** `git commit --only -- '3DModels/AB[1].step'` matched and committed `3DModels/AB1.step` (which had an intent-to-add entry) instead of the untracked `AB[1].step`.
**Why it happens:** pathspecs are globs by default; `[1]` is a character class.
**How to avoid:** always `--literal-pathspecs` (global flag, or `GIT_LITERAL_PATHSPECS=1`). With it, the same command committed `3DModels/AB[1].step` correctly. [VERIFIED: S5] MPN-derived model file names can contain `[`, `]`, `+`, `(`, `)`.
**Warning signs:** a commit whose file list is not the list the panel showed. Add a post-commit check: `git show --name-only --format= HEAD` must equal the planned path set; if not, report an ERROR (the commit already exists, so say so).

### Pitfall 2: A pathspec in the wrong case does not match
**What goes wrong:** with `core.ignorecase=true` (the real Custom has it) `git commit --only -- symbols/conn_a.kicad_sym` still failed with `pathspec … did not match any file(s) known to git`; `':(icase,literal)…'` matched. [VERIFIED: S5/S13]
**How to avoid:** pass the on-disk spelling. `FileOp.listed_path` exists for exactly this (existing file spelled differently from the planned name). Resolve each path to the real spelling by listing its parent directory and matching case-insensitively, and use that. [ASSUMED: which spelling the file has on disk after `os.replace` onto a differently-cased existing name on NTFS was not tested; resolving by directory listing sidesteps the question.]

### Pitfall 3: An uninitialised submodule directory resolves to the parent repo
**What goes wrong:** `git -C WurthElektronik/KiCad-Library rev-parse --show-toplevel` (uninitialised submodule, empty dir) prints the *parent* toplevel and `--is-inside-work-tree` prints `true`. A "Custom is a git work tree" check built on that would run the Custom commit inside the parent. [VERIFIED: real repo, read-only]
**How to avoid:** require `Path(git -C Custom rev-parse --show-toplevel).resolve() == custom_dir.resolve()`; otherwise D-05 "Commit unavailable". Cheap second check: `Custom/.git` exists.

### Pitfall 4: `add -N` fails for ignored paths
**What goes wrong:** `Custom/.gitignore` ignores `*.xml`, `*.csv`, `*.bak`, `*~`, `*.tmp`, `~*.lck` and others. An imported file matching one (unlikely for `.kicad_sym/.kicad_mod/.step/.stp`) makes `git add -N` exit 1 with "The following paths are ignored by one of your .gitignore files" and the later commit with `did not match any file(s) known to git`. [VERIFIED: S14; ignore list read from real `Custom/.gitignore`]
**How to avoid:** never use `-f`. Treat the non-zero `add` as a refusal with git's stderr and commit nothing. Optionally pre-check with `git check-ignore -q` (add it to the allow-list).

### Pitfall 5: A failed hook leaves intent-to-add entries behind
**What goes wrong:** after a rejecting `pre-commit` hook, HEAD is unchanged but the new paths stay ` A` in the index. [VERIFIED: S6]
**How to avoid:** on any commit failure run `git reset -q -- <the new paths>` (path-limited, mixed; restores the untracked state; worktree files untouched) [VERIFIED: S14: path shows `??` again]. It only touches paths the app itself added.

### Pitfall 6: Hook output arrives on stderr
**What goes wrong:** a hook that does `echo "…"` (stdout) produced *no* captured stdout; both lines arrived on stderr. [VERIFIED: S6: stdout empty, stderr contained both hook lines.] The githooks page does not document this for pre-commit [CITED: git-scm.com/docs/githooks only states "Exiting with a non-zero status … causes the git commit command to abort"].
**How to avoid:** capture both streams; show stdout + stderr together for D-06, after dropping the `warning: in the working copy of … LF will be replaced by CRLF` noise lines (keep them in the log, not the slot headline). Decode with `errors="replace"`.

### Pitfall 7: Hooks run on Windows without the executable bit
A `#!/bin/sh` hook ran with no `chmod` (Git for Windows uses its bundled sh; the repo has `core.filemode=false`). [VERIFIED: spike, hook written without chmod] Test fixtures can write hooks with `Path.write_text` only. Hooks in the *parent* live in the common dir (`.git/hooks`), hooks in `Custom` in `modules/Custom/hooks`; `git rev-parse --git-path hooks` gives each. A hook sees `GIT_INDEX_FILE=<gitdir>/next-index-NNN.lock` during a `--only` commit. [VERIFIED]

### Pitfall 8: Env pollution, identity and signing
- A `GIT_DIR`, `GIT_WORK_TREE` or `GIT_INDEX_FILE` in the app's environment (for example launched from a git hook or another tool) redirects every call. Scrub `GIT_*`.
- Unknown identity: `git var GIT_COMMITTER_IDENT` exits 128 with "Please tell me who you are". [VERIFIED: S15 with `GIT_CONFIG_GLOBAL=NUL GIT_CONFIG_NOSYSTEM=1 -c user.useConfigOnly=true`] Probe it up front so Commit is disabled with that reason instead of failing after `add -N`. The owner's identity is set (`sylvanoMTL`), `commit.gpgsign=false`. [VERIFIED: `git config --show-origin`]
- If someone sets `commit.gpgsign=true`, a pinentry prompt could hang the worker. Use a finite timeout (see Assumptions A5) and report a timeout as an ERROR; do not retry.

### Pitfall 9: `commit_slot` height, Phase 5 test and button defaults
`setFixedHeight(0)` pins both limits (Pattern 6). The dialog sets every `QPushButton` to `setAutoDefault(False)` once at construction (import_dialog.py:331-333); buttons created later by the panel default to autoDefault on some styles, and the Result page makes Close the default button. Set `setAutoDefault(False)` on the Commit and Switch buttons so Enter inside the message editor can never commit (PROJECT.md Safety). A `QPlainTextEdit` swallows Enter anyway, but the checkbox and list do not.

### Pitfall 10: `status`-based "N other changes"
Use `git status --porcelain=v1 -z --untracked-files=all` and subtract the touched set. Without `-uall`, a new untracked directory collapses to `dir/` and counts as one. Rename entries have two NUL-separated paths. It ran in 60 ms on the real `Custom`. [VERIFIED: S17]

### Pitfall 11: Ahead counts are local-only and may be absent
`rev-list --count @{u}..HEAD` exits 128 (`fatal: no upstream configured for branch 'feature/x'`, or `HEAD does not point to a branch` when detached). Skip the "Not pushed" line then, or say "no upstream". The count compares with the *local* remote-tracking ref (the importer never fetches), so word it "ahead of origin/main (as last fetched)". [VERIFIED: S11/S12]

### Pitfall 12: Nothing-to-commit and double click
A second `commit --only` on an unchanged path exits 1 and prints "nothing to commit" on stdout. [VERIFIED: S15] After success, disable everything (D-04); the dialog state, not git, prevents the repeat. For the parent, compare `git ls-tree HEAD Custom` with the new Custom HEAD first and skip the parent step if equal.

### Pitfall 13: `-dirty` suffix in gitlink diffs
`git diff -- Custom` shows `Subproject commit <sha>-dirty` when the submodule has uncommitted files. Never parse the gitlink from diff output; use `git ls-tree HEAD Custom` (committed) and `git -C Custom rev-parse HEAD` (current). [VERIFIED: S6]

## Code Examples

### Spike-validated commands (git 2.49.0.windows.1, Windows 11, repro with worktree-private submodule gitdir)

| # | Command (all with `--literal-pathspecs -c core.quotepath=false -C <repo>`) | Observed |
|---|---|---|
| S1 | `rev-parse --git-dir` in `wt/Custom`; `rev-parse --git-path MERGE_HEAD` | `…/parent/.git/worktrees/wt/modules/Custom` and `…/modules/Custom/MERGE_HEAD` (per-worktree). `Custom/.git` file: `gitdir: ../../parent/.git/worktrees/wt/modules/Custom`. Real repo is the same shape: `gitdir: ../../Kicad_Libraries/.git/worktrees/Kicad_Libraries-importer/modules/Custom`. |
| S2 | `symbolic-ref -q HEAD` (detached) / `branch --show-current` | rc 1 and empty (`symbolic-ref`); `--show-current` rc 0, empty. Use `symbolic-ref -q --short`. |
| S3 | `commit --only -m x -- <untracked path>` | `error: pathspec '…' did not match any file(s) known to git`, rc 1. |
| S4 | `add -N -- <new>` then `commit --only -F msg --pathspec-from-file=<file>` | rc 0; commit has exactly the 3 files; trailers parse; staged `staged_other.txt` and `3DModels/old.step` still staged, `README.md` still unstaged-modified, `untracked.txt` still untracked. |
| S5 | `reset -q -- <path>` after intent-to-add | back to `??`. |
| S6 | parent: `commit --only -F msg -- Custom` with staged `.planning/p.md`, unstaged `README.md`, untracked file, dirty submodule | rc 0; commit touches only `Custom`; afterwards `A  .planning/p.md`, ` M README.md`, `?? …`, ` m Custom` unchanged. |
| S7 | detached ancestor of `main`: `switch main` with staged/unstaged/untracked/import changes | rc 0, all carried; stderr has `M<TAB>…` lines. |
| S8 | no local `main`, `origin/main` present: `switch main` | `branch 'main' set up to track 'origin/main'.` rc 0. |
| S9 | conflicting file: `switch main` | rc 1, `Your local changes to the following files would be overwritten by checkout`, still detached. Diverged detached HEAD: `merge-base --is-ancestor HEAD main` rc 1. HEAD == main tip: rc 0, ahead 0. |
| S10 | Python `subprocess.run` with `-F` tempfile and `--pathspec-from-file=- --pathspec-file-nul` stdin, UTF-8 file name `Pièce 1+(a).step`, `#` line, em dash | rc 0, message identical, file committed. |
| S11 | `rev-list --count @{u}..HEAD` on `main` with upstream; on branch without upstream; detached | `3`; rc 128 `no upstream configured for branch 'feature/x'`; rc 128 `HEAD does not point to a branch`. |
| S12 | bare remotes' `for-each-ref` before/after the whole flow | identical. |
| S13 | pathspec case mismatch, `core.ignorecase=true` | no match unless `:(icase,literal)`. |
| S14 | `add -N` on an ignored path; `reset -q -- path` | rc 1 + ignore message; reset restores `??`. |
| S15 | `git var GIT_COMMITTER_IDENT`; `commit --only` with no change | ident OK rc 0 / rc 128 when unknown; "nothing to commit" rc 1. |
| S16 | `cat-file --filters HEAD:<path>` vs raw blob (real Custom, read-only) | filtered sha256 equals the CRLF working-tree sha256; raw blob does not. |
| S17 | `status --porcelain=v1 -z -uall` (real Custom) | 60 ms. |

### End-to-end flow, run against the repro (condensed from `gitops_spike.py` / `e2e.py`)
```python
# Source: scratchpad spike, executed; output:
#   probe custom: RepoState(toplevel_ok=True, branch=None, head='bd5f058…', busy=None)
#   detached HEAD on main history: True main ahead by 0
#   dirty before import (clean pre-image): False   /  (different pre-image): True
#   switch main rc 0 Switched to branch 'main'
#   custom commit rc 0 [main 3d6d9ed] Add NEW to Lib_New
#   custom status after: M README.md                 (unrelated edit left alone)
#   parent bump covers: 3d6d9ed Add NEW to Lib_New
#   parent commit rc 0 | gitlink at new HEAD: True
#   custom ahead of upstream: 1
#   git calls: 41 subcommands: [add, cat-file, commit, log, ls-files, ls-tree, merge-base, rev-list, rev-parse, switch, symbolic-ref]
#   remotes unchanged: True
def commit_custom(custom, rels, message, tracked_before):
    new = [r for r in rels if r not in tracked_before]
    if new:
        rc, _, err = run_git(custom, "add", "-N", "--", *new)
        if rc: return rc, txt(err)
    with tempfile.NamedTemporaryFile("wb", suffix=".txt", delete=False) as t:
        t.write(message.encode("utf-8")); name = t.name
    try:
        rc, out, err = run_git(custom, "commit", "--only", "-F", name, "--pathspec-from-file=-", "--pathspec-file-nul",
                               input=b"".join(r.encode("utf-8") + b"\0" for r in rels))
    finally:
        os.unlink(name)
    if rc and new:
        run_git(custom, "reset", "-q", "--", *new)       # undo intent-to-add only
    return rc, txt(out) + "\n" + txt(err)

def commit_parent(parent, message):                      # message built AFTER the Custom commit
    ...
    return run_git(parent, "commit", "--only", "-F", name, "--", "Custom")
```
Do not copy the spike's `assert sub in ALLOWED` literally into production: return an `Issue(ERROR, "git.disallowed", …)` or raise `ValueError` (a programming error), as `InstallOptions.__post_init__` does for unknown names.

### Probe set for the worker (all read-only)
```text
git --version                                               (also shutil.which("git") first; D-05)
git -C Custom rev-parse --show-toplevel                      == Custom (Pitfall 3)
git -C Custom symbolic-ref -q --short HEAD                   branch or detached
git -C Custom rev-parse --git-path <marker> (x6)             busy marker exists? (D-16)
git -C Custom rev-parse -q --verify refs/heads/main | refs/remotes/origin/main
git -C Custom merge-base --is-ancestor HEAD <mainref>;  rev-list --count HEAD..<mainref>
git -C Custom var GIT_COMMITTER_IDENT                        rc 0 required
git -C Custom ls-files -- <rels>                             which are tracked
git -C Custom cat-file --filters HEAD:<rel>                  per pre-existing file (D-09)
git -C Custom status --porcelain=v1 -z --untracked-files=all other changes = entries not in rels
git -C <REPO_ROOT> rev-parse --show-toplevel == REPO_ROOT; symbolic-ref; busy markers; ls-tree HEAD Custom;
git -C Custom log --reverse --format=%h%x09%s <old>..HEAD    (D-13; rc!=0 → "cannot list")
```
Live values on the owner's machine today (read-only): `Custom` on `main` at `d3ff246`, `[origin/main]`, ahead 0; parent worktree on `feature/part-importer` (ahead 99 of its upstream); parent gitlink `485d530…`; D-13 list: `49f746c Corrected pin assignement for TSOT-23 package on LTC2954`, `d3ff246 improved ublox nora w106-10B pinout`. [VERIFIED: git commands this session]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `git checkout <branch>` | `git switch <branch>` | git 2.23 | Used here; clearer, `--guess` DWIM default. [CITED: git-scm.com/docs/git-switch] |
| Pathspec lists on the command line | `--pathspec-from-file`, `--pathspec-file-nul` | git 2.25 [ASSUMED: version from memory, the commit docs do not state it; worked on 2.49] | No length or quoting limits. |
| Message via `-m` | `-F <file>` | long-standing | Exact multi-line bytes. |

**Deprecated/outdated:** `git submodule` helpers are not used at all (no `submodule update`, no `submodule foreach`); the importer only talks to the two repos directly.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "main" for the on-history test is local `refs/heads/main` if it exists, else `refs/remotes/origin/main`; if local `main` exists but is stale (does not contain HEAD) while `origin/main` does, the commit is refused with "local main is behind origin/main, update it first". Alternative: test against either ref and switch anyway. | Pattern 4 | Needs owner confirmation: refusing is safe, but it adds friction after a `git submodule update --remote`. Switching to a stale `main` would put the commit on an old base and the parent bump would then move the gitlink backwards. |
| A2 | `shutil.which("git")` on Windows may resolve a `git.exe` planted in the current directory (Python adds the cwd on Windows); resolve once and reject a result inside `REPO_ROOT`. | Security | Low: a local planted binary in a personal repo; mitigation is one comparison. |
| A3 | Which spelling an existing differently-cased file has on NTFS after `os.replace` was not tested. | Pitfall 2 | Low: directory-listing resolution makes it moot. |
| A4 | `--pathspec-from-file` appeared in git 2.25. | State of the Art | None for this machine (2.49); only matters if the owner downgrades. Probe `git --version` and refuse below 2.25 only if desired. |
| A5 | Timeouts: 30 s for read-only probes, 300 s for the commit job (hooks may be slow, D-07), no retry on timeout. | Pattern 1 | A hook slower than 300 s is reported as an ERROR although it may still finish; leaves an `index.lock`. Owner has no hooks today. |
| A6 | Not tested: a `post-commit` hook that changes files or pushes; a `prepare-commit-msg`/`commit-msg` hook that edits the message; `commit.gpgsign=true`; `submodule.Custom.ignore=all`; `commit.template`. The real config has none of them. | Pitfall 8 | If a post-commit hook pushes, GIT-05 cannot be enforced by the app. The remote-ref snapshot test only covers the importer's own calls. |
| A7 | A Package-level `source` for a folder import is the folder name, so `Import-Package:` carries a folder name in that case. | Pattern 5 | Cosmetic. |

## Open Questions

1. **Stale local `main` (A1).**
   - What we know: with local `main` behind `origin/main` and HEAD == local `main`, the switch is trivially safe (ahead 0). With HEAD == `origin/main` tip and local `main` behind, HEAD is not an ancestor of local `main`.
   - What's unclear: whether the owner prefers refuse or auto-handling.
   - Recommendation: implement the refuse variant with a clear explanation; mention it in the plan so the owner can veto.

2. **Where the "other changes" count comes from after a branch switch.** Probe runs before the switch; the count is unchanged by a successful switch (changes are carried). Recommendation: refresh the whole probe after a switch anyway (one extra worker call).

3. **Should the panel re-probe when the Result view regains focus?** CONTEXT does not ask for it. The pre-click re-check (stale files, busy markers, branch) inside the commit job covers the risk. Recommendation: no focus-driven refresh.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `git` on PATH | everything | yes | 2.49.0.windows.1 | D-05: disabled slot with the reason |
| Project venv Python | tests, app | yes | `./env/Scripts/python.exe` (3.14) | — |
| pytest / pytest-qt | tests | yes | 9.1.1 / 4.5.0 (pinned) | — |
| Git Bash `sh` for fixture hooks | failing-hook test | yes (bundled with Git for Windows; hook ran without chmod) | — | skip the hook test when `sh` is not usable |
| `file://` submodule transport | test fixtures | yes, needs `-c protocol.file.allow=always` | — | — |
| KiCad / kicad-cli | not needed in this phase | — | — | — |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-qt 4.5.0, `qt_api = "pyside6"`, `QT_QPA_PLATFORM=offscreen` forced in `tests/conftest.py` |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `--strict-markers`, `testpaths = ["tests"]`) |
| Quick run command | `./env/Scripts/python.exe -m pytest tests/test_gitops.py tests/test_commit_plan.py -x -q` |
| Full suite command | `./env/Scripts/python.exe -m pytest -x -q` (note: 7 real-kicad-cli tests already fail on the phase base, see STATE.md) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GIT-01 | Probe reports branch/detached; panel shows branch, exact files, editable message; Commit disabled for blank message | unit + pytest-qt | `pytest tests/test_gitops.py::test_probe_branch_and_detached tests/test_commit_panel.py -x -q` | Wave 0 |
| GIT-02 | Only listed files committed with staged/unstaged/untracked bystanders present; new + existing files; literal pathspec with `[ ]`; parent commit touches only `Custom` with staged `.planning` file present | unit (real git in tmp_path) | `pytest tests/test_gitops.py -k "commit_only or literal or parent" -x -q` | Wave 0 |
| GIT-02 | D-11 stale file refuses; D-09 dirty-before flag with autocrlf true and false | unit | `pytest tests/test_commit_plan.py tests/test_gitops.py -k "stale or dirty_before" -x -q` | Wave 0 |
| GIT-03 | Detached on main history offers switch; switch carries changes; detached off-history refuses; switch conflict leaves HEAD detached and commits nothing; no local main uses origin/main | unit | `pytest tests/test_gitops.py -k "detached or switch" -x -q` | Wave 0 |
| GIT-04 | Default message has subject + Import-Vendor/Package/Date trailers parsed by `%(trailers)`; control characters in package name stripped; user-edited message committed verbatim | unit | `pytest tests/test_commit_plan.py -x -q` | Wave 0 |
| GIT-05 | Recorded argv never contains `push`; allow-list rejects it; bare remotes' `for-each-ref` identical before/after a full commit; source grep: no `"push"` literal in `gitops.py`/`commit_panel.py` | unit | `pytest tests/test_gitops.py -k "no_push" -x -q` | Wave 0 |
| D-03 | Parent hook rejects → Custom commit stays, ERROR carries stderr and the manual command | unit | `pytest tests/test_gitops.py -k "parent_fails" -x -q` | Wave 0 |
| D-05/D-16 | git absent (monkeypatch `shutil.which`/runner), Custom not own toplevel, merge in progress in Custom or parent | unit | `pytest tests/test_gitops.py -k "unavailable or busy" -x -q` | Wave 0 |
| D-06 | Failing `pre-commit` hook: rc≠0, stdout+stderr surfaced, HEAD unchanged, intent-to-add undone | unit | `pytest tests/test_gitops.py -k hook -x -q` | Wave 0 |
| D-07/D-08 | Panel state machine; Close/Esc blocked while committing; no panel on no-op/failed install; WR-04 guard | pytest-qt | `pytest tests/test_commit_panel.py tests/test_import_dialog.py -k "commit or install_guard" -x -q` | Wave 0 / edit existing |
| Layering | `gitops` Qt-free, imports `models` only; `importer.commit_plan` registered | unit | `pytest tests/test_layering.py tests/test_importer_layering.py -x -q` | edit existing |

### Test fixture recipe (`tests/gitfixtures.py`)
Build in `tmp_path`: `git init --bare -b main custom_remote.git` and `parent_remote.git`; seed clones with a few commits; in the parent seed `git -c protocol.file.allow=always submodule add <abs path to custom_remote.git> Custom`; push; clone the parent; `submodule update --init`; optionally `git worktree add ../wt -b feature/x` then `submodule update --init` inside it to get the worktree-private `modules/Custom` gitdir with a detached HEAD. Isolate configuration so results do not depend on the developer machine: set `GIT_CONFIG_GLOBAL=<tmp>/gitconfig` (user.name, user.email, `commit.gpgsign=false`, `protocol.file.allow=always`) and `GIT_CONFIG_NOSYSTEM=1`; parametrize `core.autocrlf` true/false (the owner's system config sets true). Skip the whole module when `shutil.which("git")` is `None`. Use `Path.write_bytes` for hooks (no chmod needed on Windows; on POSIX also `chmod 0o755`).

### Sampling Rate
- **Per task commit:** `./env/Scripts/python.exe -m pytest tests/test_gitops.py tests/test_commit_plan.py -x -q`
- **Per wave merge:** `./env/Scripts/python.exe -m pytest tests/test_gitops.py tests/test_commit_plan.py tests/test_commit_panel.py tests/test_import_dialog.py tests/test_layering.py tests/test_importer_layering.py -x -q`
- **Phase gate:** full suite green except the 7 known kicad-cli failures, then manual UAT.

### Wave 0 Gaps
- [ ] `tests/gitfixtures.py` — repo, submodule and worktree builders with config isolation
- [ ] `tests/test_gitops.py` — covers GIT-01..GIT-05, D-03, D-05, D-06, D-16
- [ ] `tests/test_commit_plan.py` — covers GIT-04, D-09, D-11
- [ ] `tests/test_commit_panel.py` — pytest-qt state machine
- [ ] Edit `tests/test_import_dialog.py:2743-2744` (slot hidden/zero-height assertion)
- [ ] Register `gitops` and `importer.commit_plan` in the two layering tests

### Manual UAT (cannot be automated)
Import a real Ultra Librarian zip, click Commit with the parent box ticked, then in the real repo run `git -C Custom status`, `git -C Custom log -1 --stat`, `git log -1 --stat` and `git -C Custom rev-list --count @{u}..HEAD`; confirm the remote is unchanged (`git -C Custom ls-remote origin` equals `git -C Custom rev-parse origin/main`). Remember STATE.md: the owner must push `Custom` before removing the worktree.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | partial | Only paths inside `Custom/` may be committed; refuse any `touched` path whose resolved form is not under `plan.layout.custom_dir`. |
| V5 Input Validation | yes | argv list, never a shell; `--literal-pathspecs`; `--` before paths; commit message via file; strip control characters from vendor/package/library strings before they enter a message. |
| V6 Cryptography | no (sha256 comparison only, via `hashlib`) | — |

### Known Threat Patterns for subprocess + git from a GUI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Command injection through file/package names | Tampering / Elevation | `subprocess.run([...])` with a list, `shell=False`, paths after `--` and on stdin with `--pathspec-file-nul`. |
| Pathspec magic (`[x]`, `:(…)`, `*`) selects unintended files | Tampering | `--literal-pathspecs` on every call (reproduced wrong-file commit without it). |
| Trailer or line injection through the original package filename (a POSIX filename may contain a newline) | Tampering | Replace `\r`, `\n` and other C0 controls with a space and trim before building `Import-Package:`; same for vendor and symbol names. The user's edited text is trusted as typed (D-20). |
| Writing outside `Custom/` | Tampering | Resolve and `is_relative_to(custom_dir)` for every path; refuse the commit otherwise. |
| Wrong repo targeted (uninitialised submodule resolves to the parent) | Tampering | Compare `rev-parse --show-toplevel` with the expected path (Pitfall 3). |
| Environment redirect (`GIT_DIR`, `GIT_INDEX_FILE`) | Tampering | Scrub `GIT_*` from the child env. |
| Attacker-controlled output rendered as markup | Spoofing | Plain text labels only (`Qt.TextFormat.PlainText`), as the rest of the Result view does. |
| `git.exe` planted in the working directory | Elevation | Resolve with `shutil.which`, reject a hit inside `REPO_ROOT` (A2). |
| Repo-local hooks or config run code | Elevation | Out of scope: hooks must run (D-06) and `Custom`'s config is the owner's. State it in the plan so nobody "fixes" it with `--no-verify`. |
| Accidental push | — | No `push` in the allow-list; no code path builds a remote command; tests assert it (GIT-05). |

## Project Constraints (from CLAUDE.md)

Both `./CLAUDE.md` and `./.claude/CLAUDE.md` were read. Directives that bind this phase:
- Stdlib only unless a dependency is clearly justified (none is needed); Python 3.10+ typing syntax (`X | None`, builtin generics); no `from __future__` annotations.
- Windows 11 primary with standard CPython; keep the existing cross-platform branches working (so `CREATE_NO_WINDOW` through `getattr(subprocess, "CREATE_NO_WINDOW", 0)`).
- Safety: no write without a preview first; git commits need explicit confirmation; writes atomic or backed up.
- Git workflow: commit submodule changes separately (submodule first, then the parent ref); descriptive messages with component-category context.
- Services return `list[str]`-style messages in the legacy code, but the importer layer uses `Issue`/`Severity`; new code follows the `Issue` shape, severity decided by the producer (never by substrings). Errors go to the log panel, `QMessageBox` only for About (plus the one documented confirm exception in `main_window.py`).
- Naming: private helpers prefixed `_`; Qt attributes `self._name`; `_on_<event>` handlers; Qt enums fully qualified; `blockSignals` pairs; long work on a `QThread`; relative imports inside the package; `models.py` has no internal imports; do not import `main_window` from lower modules; do not add re-exports in package `__init__` files.
- Paths: `pathlib.Path` throughout; `.as_posix()` for repo-relative strings (and therefore for the paths handed to git).
- Persistence only through `settings.py`; this phase needs none.
- GSD workflow: edits go through a GSD command; the executor handles this.
- `QSettings`, `.gitignore` entries, and the KiCad path-variable rule (Quick 261022-gnn) are unaffected; D-17a explicitly does not apply the worktree refusal here.

## Sources

### Primary (HIGH confidence)
- Reproduction built in the session scratchpad (`C:\Users\sylvain\AppData\Local\Temp\claude\c--Git-Repo-Clones-Kicad-Libraries-importer\80e0d99f-f493-4e91-bdfb-f06f0adb85b7\scratchpad\`: `setup.sh`, `gitops_spike.py`, `e2e.py`, `harness.py`, `spike/`) on git 2.49.0.windows.1 — every S1-S17 observation.
- Real repo, read-only: `git config --show-origin`, `.git/hooks` and `modules/Custom/hooks` listings, `git ls-files --eol`, `cat-file --filters`, `rev-list`, `ls-tree`, `status` timing.
- Source read this session: `kicad_lib_manager/widgets/import_result.py`, `widgets/import_dialog.py` (170-192, 224-340, 1889-2205), `importer/plan.py`, `importer/applier.py` (20-140, 310-505), `importer/planner.py` (855-945, 1090-1110), `importer/content.py`, `widgets/content_view.py`, `fsutil.py` (173-200), `kicad_process.py`, `models.py`, `main_window.py` (735-790), `tests/test_layering.py`, `tests/test_importer_layering.py`, `tests/test_import_dialog.py` (2725-2750), `pyproject.toml`, `requirements-dev.txt`, `.planning/config.json`.

### Secondary (MEDIUM confidence)
- https://git-scm.com/docs/git-commit — `--only`, `--pathspec-from-file`, `--pathspec-file-nul`, `--cleanup`, `--no-verify` scope.
- https://git-scm.com/docs/git-switch — `--guess` default, "operation is aborted however if the operation leads to loss of local changes".
- https://git-scm.com/docs/githooks — non-zero pre-commit exit aborts the commit.

### Tertiary (LOW confidence)
- None used for recommendations; items marked `[ASSUMED]` are in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib + pinned existing stack; no new package.
- Architecture: HIGH for the git layer (executed), MEDIUM for the Qt layer (source-read only).
- Pitfalls: HIGH — each pitfall in 1, 3-6, 8-13 was reproduced; 2 and the Windows case spelling are partly assumed (A3).

**Research date:** 2026-10-22
**Valid until:** 2026-11-21 (git behaviours are stable; re-check only if the owner changes git version, adds hooks, or turns on signing).
