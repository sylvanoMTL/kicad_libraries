# Phase 11: Commit Gate and Commit Panel Fixes - Research

**Researched:** 2026-10-29
**Domain:** Brownfield PySide6 desktop app; a Qt-free git commit step (`subprocess` -> `git`), a rule engine reuse (`atomic_check`), and a Qt panel state machine
**Confidence:** HIGH for the code map and the findings (all files read this session, three claims reproduced by experiment); MEDIUM for the gate's "introduced by this commit" design (a design recommendation, not yet built)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Gate scope (GIT-06)**
- **D-01:** **The gate checks the new or changed symbols in the committed `.kicad_sym` files.** It covers every symbol that is new, or whose content differs from `Custom`'s HEAD, by the Phase 9 D-21 token-stream compare (`changes.py` / `gitops.head_blob`). That covers the imported part, any pre-import uncommitted edits to other symbols in the same file (the Phase 6 D-09 amber case), and later the Phase 13 migration's many parts. Symbols unchanged against HEAD are not "being committed". Scope is the Phase 9 D-23 rule: only `Atomic_` libraries are judged.
- **D-02:** **An unchanged symbol that already fails at HEAD does not block.** The panel shows one amber line, e.g. "Atomic_Sensor_Motion also holds 2 parts that already failed before this import", and the log lists each (part, rule). Commit stays possible.
- **D-03:** **The gate runs in the probe and again at the click.** The read-only probe runs it, so the panel shows the refusal and Commit is disabled before any click. `_precheck` runs it again just before the first git write, because files can change in between. Both runs stay off the GUI thread, on the existing `TaskWorker`.
- **D-04:** **Committed footprints and models also check the symbols that link them.** For each committed `.kicad_mod` or 3D model file, the `Custom` symbols that link it are checked against the working-tree content too, including symbols outside the commit and unchanged at HEAD. An example is an overwrite of a shared `Atomic_Footprints` footprint, or a replaced model. A failure that the committed footprint or model causes blocks the commit, like D-01. Planner: a linked symbol whose failure existed at HEAD regardless of this commit falls under D-02 (amber note, no block). Only failures this commit introduces block.
- **D-05:** Price/stock leftovers never block (Phase 9 D-18). The ATOM-01 rules (Phase 9's 7 rules) stay the only blocking ones. The gate reuses `atomic_check` and its `AtomicContext` unchanged in rule logic, as the Phase 10 install gate does.

**Refusal and recovery (GIT-06, REV-10)**
- **D-06:** **How a refusal looks.** The existing amber "Commit refused:" strip says "N parts break the atomic rule". One plain-language line per (part, rule) follows, e.g. "Atomic_Sensor_Motion / LIS3MDL: no datasheet", capped with "…and k more". The same lines go to the log in the Phase 9 D-05 shape. Commit is disabled. No raw field names (plain-language rule).
- **D-07:** **The panel gives two ways forward:**
  - an **"Open Check Atomic Parts…"** link, which opens the Phase 9 dialog scrolled to the first failing part (the `focus=(rel_path, name)` argument);
  - a **"Check again"** button, which re-probes and re-runs the gate.

  Commit unlocks once every part passes. Both controls are secondary buttons, not primary.
- **D-08:** **"Check again" re-baselines changed files, so D-11 is loosened on purpose.** Today Phase 6 D-11 refuses every change made after install. Now "Check again" takes each planned file's current bytes as the new expected content, whether the change came from the check dialog or from KiCad.
  - In the file list, such a file is amber, marked "changed since install".
  - Double-clicking it shows the diff (the Phase 5 content view, as for D-09 files).
  - The gate re-runs on the new content.

  The stale rule still applies between the last check and the click: a change made after "Check again" is refused again. — **Reversibility:** reversible: a gate condition only.
- **D-09:** **"Check again" is also offered after a plain D-11 stale refusal** that has nothing to do with the atomic rule, for example a pin-layout tweak in KiCad. There is one recovery path for every "changed after install" case.
- **D-10:** **Files a fix created that a committed part links are added to the list.** If a committed part now links a new, untracked model or footprint file in `Custom` (for example the .step the check dialog's 3D fill-in copied into `Custom/3DModels/`), "Check again" adds that file to the commit list, marked "added by a fix". A commit never leaves a part pointing at an uncommitted file. Unrelated untracked files stay out (Phase 6 D-10).
- **D-11:** **The refusal text survives the re-probe (WR-05).** After a refusal, the panel re-probes, so the branch, file markers, other-change counts and parent state are fresh. A changed `Custom` branch is also picked up, because the next commit passes the fresh probe's `expected_branch`. The refusal text stays at the top of the outcome area until the next Commit, Check again or Switch click. If the fresh probe refuses on its own, its reason replaces the old one.

**Uncertain git outcomes (REV-06, REV-07, REV-09)**
- **D-12:** **A timeout after HEAD moved is reported as a commit (WR-01).** HEAD is recorded before `commit_paths` and compared after any failure. If HEAD moved:
  - a warning says "Committed <hash> in Custom, but git did not finish in time (a hook or signing step may still be running)";
  - the parent bump does not start, because a leftover git process may still hold `index.lock`;
  - the manual parent command is given (Phase 6 D-03 shape);
  - nothing is unstaged.

  If HEAD did not move, the current "nothing was committed" path stays, with unstage.
- **D-13:** **A planned file identical to HEAD is an INFO line, not an error (WR-04).** It reads "Already identical to HEAD, not in the commit: <files>", and the commit counts as successful, so the parent bump goes ahead. Only extra files (committed but not planned) stay `commit.unexpected_files` ERROR.
- **D-14:** **If every planned file is identical to HEAD, the probe says so.** The panel reads "Nothing to commit: Custom already holds these files", and the Custom commit is disabled. If the parent's gitlink is behind `Custom`'s HEAD, a parent-only bump is still offered through the parent checkbox. The button then names that action, e.g. "Commit parent ref". The exact label is Claude's discretion.
- **D-15:** **One builder for the parent preview and the committed message (WR-02).** When `gitlink_old` is None, nothing earlier is listed, there is no "could not be listed" line and no empty hash. `parent_preview` and `commit_parent_ref` call the same helper, so they cannot drift (Phase 6 D-19 promise).

**Manual command and outcome look (REV-08, UI-02)**
- **D-16:** **The "Finish it by hand" command is written for PowerShell on Windows (WR-03).** Every argument is single-quoted with `''` doubling, so `"`, `$`, backticks and `\` in the subject paste safely. The label says "In PowerShell:". On POSIX, `shlex.quote` is used. The parent path and `custom_rel` are quoted the same way.
- **D-17:** **Parent-failed state.** The button is disabled and reads **"Committed in Custom only"**, not "Committed". The outcome shows a ✓ line for the Custom commit and a ✖ line for the parent failure, with the manual command.
- **D-18:** **Outcome tint follows the strongest state.** The outcome area gets one tinted strip, like today's amber strip:
  - `SUCCESS_TINT` for a full success;
  - `ERROR_TINT` for an error, including a partial result that holds an error;
  - `AMBER_TINT` for a warning-only result.

  The lines inside keep their ✓/✖/⚠ glyphs and text colours.
- **D-19:** **Primary button style.** Commit gets `theme.PRIMARY_BUTTON_QSS`, and so does **Install Part** in the same dialog: the main action of each view looks the same. "Check again" and "Open Check Atomic Parts…" stay secondary.
- **D-20:** The `commit_panel.py` sizes come from the theme scale (`SP_*` and font metrics), replacing `setFixedSize(240, 16)`, `fontMetrics().height() + 8` and the file-list height arithmetic, per 06-UI-REVIEW Pillar 5.

### Claude's Discretion
- **REV-11 identity:** which `GIT_*` variables `run_git`'s `_env` keeps. At minimum `GIT_AUTHOR_NAME/EMAIL/DATE` and `GIT_COMMITTER_NAME/EMAIL/DATE`. `GIT_DIR`, `GIT_INDEX_FILE`, `GIT_WORK_TREE` and the like stay stripped. Also rename the `input` parameter to `stdin_data` (IN-03) and update the identity message.
- **IN-01:** keep the parent checkbox choice across re-probes (tick it only on the first probe after `show_plan`). Where a probe disables it, restore the user's choice when it is enabled again.
- **IN-02:** the read-only probe no longer blocks Close, Esc or the main window's X. It does not set `_git_worker`, and `_shutdown` waits on it or abandons it safely. Switch and Commit keep the lock.
- How the gate builds its `AtomicContext` and reads HEAD content off the GUI thread. How the gate result feeds the Check Atomic Parts dialog, which today takes a `ScanResult` from the main window, while the import dialog sits on top. Whether applied fixes trigger the main window's rescan.
- How "Check again" stores the re-baselined hashes (`CommitFile.expected_sha256`) and pre-images for the diff view.
- The exact wording of strip lines, the "changed since install" and "added by a fix" markers, and the parent-only button label.
- Test strategy: unit tests on throwaway git repos in `tmp_path` (Phase 6 pattern, `tests/gitfixtures.py`) with `Atomic_` fixtures from `tests/customfixtures.py`. Cases: a failing new part, a failing pre-import edit, a failing part already at HEAD, a footprint overwrite breaking a linked symbol, a timeout with HEAD moved (simulated by a slow hook or a patched timeout), identical files, all-identical, quotes, `$` and backticks in the subject, and a refusal followed by a re-probe. pytest-qt for the panel states. The live-`Custom/` write-protect guard stays in force.

### Deferred Ideas (OUT OF SCOPE)
None. The discussion stayed within phase scope. (Phase 10's deferred idea, a log panel inside the import dialog, stays in 10-UAT.md.)

Out of this phase (CONTEXT `<domain>`): the import-flow fixes and Help dialog theme (Phase 12, REV-01..05, UI-01); the migration (Phase 13, but the gate is built so its single migration commit can go through the same commit step); pushing stays impossible (GIT-05); every commit still needs an explicit click.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GIT-06 | The commit panel refuses while any part being committed fails the atomic check, naming the part and the rule. | New Qt-free `importer/commit_gate.py`; reuse `atomic_check.check_symbol` + `incoming_context`; D-21 compare extracted from `changes._mark_symbols`; "introduced by this commit" H-view (see Architecture Patterns 1-2); refusal lines + Check again (Pattern 5) |
| REV-06 | A commit timeout checks HEAD before reporting "nothing committed" (WR-01). | `run_commit` HEAD before/after (Pattern 3); reproduced on Windows: a slow `post-commit` hook makes `subprocess.run(timeout=2)` raise after 12.2 s with HEAD moved (Experiments) |
| REV-07 | Parent-message preview matches the committed text when no previous gitlink (WR-02). | One builder in `commit_plan`; the three divergent places are mapped (Findings table) |
| REV-08 | "Finish it by hand" uses Windows quoting on Windows (WR-03). | PowerShell 5.1 experiment shows D-16 is right for `$`, backtick, `'`, mid-string `\`, but WRONG for `"` and a trailing `\` (Pitfall 1, Open Question 1) |
| REV-09 | Files identical to HEAD no longer raise a spurious "missing" error (WR-04). | Pre-commit `head_blob` hash compare; INFO line; all-identical probe state and parent-only bump (Pattern 4) |
| REV-10 | After a precheck refusal the panel re-probes instead of showing stale "ready" (WR-05). | Re-probe path that keeps message text and parent choice; refusal text survives `apply_probe` (Pattern 6, Pitfall 5) |
| REV-11 | Parent checkbox keeps choice; dialog and main window can close during the probe; `run_git` keeps identity-related `GIT_*` (IN-01..IN-03). | Six-variable allow-list; check BOTH author and committer ident (experiment); cooperative cancel instead of `_git_worker` lock (Pattern 7) |
| UI-02 | Commit button primary, outcomes tinted, parent-failed not labelled "Committed", panel sizes on the theme scale (06-UI-REVIEW). | Concrete line map and replacements (Pattern 8) |
</phase_requirements>

## Summary

All eight review findings (WR-01..WR-05, IN-01..IN-03) and the 06-UI-REVIEW defects are still present in the current code; none was fixed by Phases 7-10. Line numbers have moved only slightly for `commit_step.py` and `commit_panel.py`, and a lot for `import_dialog.py` (the review cited 2120-2290; the commit wiring now sits at 2796-2952). The phase is almost entirely edits to existing modules plus one new Qt-free module (the gate). No new third-party package is needed.

Three claims in CONTEXT.md needed evidence, and two of them change the plan. (1) **D-16 is not fully safe on Windows PowerShell 5.1**, the only PowerShell installed here: a single-quoted argument containing `"` loses the quote, and an argument that ends in `\` and contains a space loses its closing quote. This is reproduced below; PowerShell 7.3+ fixes it. The user asked for a result that "runs as shown when pasted", so this needs a decision (Open Question 1). (2) **`identity_known` checks only the committer ident**; with only `GIT_COMMITTER_*` set, `git var GIT_COMMITTER_IDENT` succeeds but `git commit` fails (exit 128), so REV-11 must check the author ident as well. (3) **A timeout after a commit really happens on Windows with a slow `post-commit` hook**, and the timeout is not tight: `subprocess.run(timeout=2)` returned only after 12.2 s because the hook's shell kept the output pipe open; HEAD had moved. That gives a cheap, real test for REV-06.

The gate (GIT-06) is the only new design. Recommended: a Qt-free `importer/commit_gate.py` that (a) lists the new or changed symbols of each committed `Atomic_` library using the D-21 token-stream compare extracted from `changes.py` into a public function, (b) runs the unchanged `check_symbol` on them in the working-tree context, (c) for committed footprints, re-checks the symbols that link them and keeps only failures that are absent in a "HEAD view" of the same footprint, and (d) returns a frozen `GateResult` that both `probe_commit` and `_precheck` carry. The Check Atomic Parts dialog needs a `ScanResult`; the gate builds a small one (only failing entries, `fixable=True`) so the import dialog can open the dialog itself.

**Primary recommendation:** Implement the gate as `importer/commit_gate.py` reused by `probe_commit` and `_precheck`; fix the nine small findings in place; settle Open Question 1 (PowerShell quoting of `"`) before the plan locks D-16; and keep the probe off the Close lock with a `threading.Event` cancel checked between git calls, because the dialog's `_shutdown` calls `worker.wait()` on every worker.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Atomic gate decision (which symbols, which rules, introduced vs old) | Qt-free service (`importer/commit_gate.py`) | git via `gitops` | Pure logic over `atomic_check` and HEAD blobs; must run on a worker and be unit-testable without Qt |
| HEAD reads, HEAD-moved detection, commit, identity env | `gitops.py` / `commit_step.py` | git subprocess | Only `gitops` starts git; `commit_step` orchestrates and returns `Issue` lists |
| Re-baseline of planned files, "added by a fix" discovery | `commit_plan.py` (pure) + `commit_step.py` (git reads) | — | `CommitPlan` is a frozen value; a new plan is returned, nothing mutates |
| Parent message text and manual command | `commit_plan.py` (message) / `commit_step.py` (command) | — | One pure builder shared by preview and commit |
| Panel states, tints, markers, controls | Qt widget (`commit_panel.py`) | `theme.py` | Layout and state only; it never starts git |
| Worker lifetime, probe cancel, opening the check dialog, re-probe | `import_dialog.py` (GUI thread orchestration) | `TaskWorker` threads | The dialog owns `_spawn`, `_closing`, `_shutdown` |
| Rescan after applied fixes | `main_window.py` | — | Owns `_scan_result` and `_start_scan` |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.14.4 (venv `env/`) [VERIFIED: `env/Scripts/python.exe --version`] | all code | Project constraint (3.10+ syntax) |
| PySide6 | 6.12.0 [VERIFIED: `pip list` in `env/`] | panel, dialogs, `QThread` | Existing GUI |
| stdlib `subprocess`, `shlex`, `hashlib`, `dataclasses`, `threading` | stdlib | git calls, POSIX quoting, hashing, frozen value types, cancel flag | Project rule: stdlib only unless clearly justified |
| git | 2.49.0.windows.1 [VERIFIED: `git --version`] | the only external tool; `MIN_GIT_VERSION = (2, 25)` is already enforced | Existing |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 [VERIFIED: `pip list`] | tests | all new tests |
| pytest-qt | 4.5.0 [VERIFIED: `pip list`] | panel and dialog tests (`qtbot`) | panel states, dialog wiring |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `shlex.quote` for the Windows command | a hand-written PowerShell quoter | `shlex.quote` is POSIX-only (Windows needs the `''` doubling rule); write a 3-line `_ps_quote` and test it against real `powershell` |
| A `-F <file>` message for the manual command | single-quoted `-m '...'` (D-16 as written) | `-F` sidesteps every quoting bug (see Open Question 1) but needs a persisted message file |
| Cooperative cancel for the probe | abandoning a running `QThread` (reparent + keep alive) | Abandoning risks "QThread: Destroyed while thread is still running" crashes; the codebase already notes `deleteLater` on a finished worker crashed the process (`import_dialog.py` `_reap` docstring) |

**Installation:** none. No new package. **Version verification:** versions above were read from the venv and `git --version` this session.

## Package Legitimacy Audit

No external package is added or changed by this phase. The `gsd-tools query package-legitimacy check` run is not needed.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | Not applicable |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 Result view opens ──> ImportDialog._start_commit_step
                              │ build_commit_plan -> CommitPlan (frozen)
                              ▼
        ┌──────────── probe worker (TaskWorker; NOT _git_worker; cancel Event) ───────────┐
        │ commit_step.probe_commit(cplan, kicad_fp_dir, cancelled)                        │
        │   git facts (branch, parent, dirty_before, other_changes, earlier) [existing]   │
        │   + identical_to_head  (head_blob hash == file hash)         [REV-09/D-14]      │
        │   + changed_files      (changed_since_install)               [D-08 marker]      │
        │   + gate = commit_gate.run_gate(cplan, ctx, kicad_fp_dir)    [GIT-06/D-03]      │
        │        committed .kicad_sym ─► changes.symbol_changes (D-21 token-stream)       │
        │        new/changed symbols  ─► atomic_check.check_symbol  ─► blocking           │
        │        committed .kicad_mod ─► linking symbols, W-view vs H-view ─► introduced  │
        │                              unchanged + failing ─► "old" (amber, no block)     │
        └───────────────────────────────┬─────────────────────────────────────────────────┘
                                         ▼ CommitProbe(gate=..., identical, changed)
                                CommitPanel.apply_probe
              ready ──────────────┼────────────── gated (new) ─── refused/unavailable/offer_switch
        Commit click              │        refusal lines + [Open Check Atomic Parts…] [Check again]
              ▼                   │                │                         │
   commit worker (_git_worker lock)               │          ImportDialog opens AtomicCheckDialog
   run_commit: _precheck (stale, state, branch,   │          (parent=self, focus=(rel, name),
     parent, ignored, GATE again) ─refuse─► CommitOutcome(issues, gate)          backup_root=…)
        │ no refusal                               │            applied ─► re-emit ─► MainWindow rescan
        ▼                                          ▼
   HEAD_before ─► commit_paths ─► fail? HEAD moved? ──yes─► warning + manual cmd, no unstage, no parent
        │ ok                                    └─no──► unstage, "nothing committed"
        ▼
   files compare: extra=ERROR, identical-to-HEAD=INFO, other missing=ERROR
        ▼
   commit_parent_ref ── one shared parent_message builder (preview == committed)
        ▼ failure ─► _manual_command (PowerShell on win32, shlex.quote elsewhere)
   CommitOutcome ─► ImportDialog._on_commit_done
        ├─ committed ─► panel.show_outcome (tint by strongest severity)
        └─ not committed ─► show refusal text, then RE-PROBE keeping message + parent choice
```

### Recommended Project Structure
```
kicad_lib_manager/
├── gitops.py                    # _env allow-list, stdin_data rename, (optional) head_moved helper
├── changes.py                   # NEW public symbol_changes(); _mark_symbols uses it
├── importer/
│   ├── commit_gate.py           # NEW, Qt-free: GateResult, AtomicFailure, run_gate
│   ├── commit_plan.py           # CommitFile gains note/installed; rebaseline(); one parent_message builder
│   └── commit_step.py           # probe fields, _precheck gate, HEAD-moved, identical, manual command
└── widgets/
    ├── commit_panel.py          # gated state, controls, markers, tint frame, sizes, IN-01
    ├── import_dialog.py         # probe not _git_worker, cancel, re-probe, check dialog, Install QSS
    └── theme.py                 # (no change expected; tints and SP_* already exist)
tests/
├── test_commit_gate.py          # NEW
├── test_commit_step.py / test_commit_plan.py / test_commit_panel.py / test_gitops.py / test_import_dialog.py  # extended
└── test_importer_layering.py    # register commit_gate, widen commit_step ALLOWED
```

### Pattern 1: The gate as a pure function over `check_symbol`
**What:** `run_gate(cplan, ctx, kicad_fp_dir) -> GateResult`. For each `CommitFile` whose `kind` is `"symbol_lib"` (the `FileOp.kind` comment reads `# "mkdir" | "model" | "footprint" | "symbol_lib"` at `plan.py:118`) and whose stem passes `atomic_check.is_atomic`: read the working-tree bytes, parse with `kicad_files.parse_bytes(..., max_nodes=MAX_KICAD_TEXT_NODES)`, compute the symbol set that is new or changed against `gitops.head_blob`, and call `check_symbol(root, name, rel_path=<repo-relative>, fixable=True, ctx=...)`.
**When to use:** in `probe_commit` and again in `_precheck` (D-03).
**Source of the compare:** extract the loop body of `changes._mark_symbols` (lines 80-119; it already does "not in HEAD file -> every symbol new", "HEAD unparsable -> every symbol changed", else per-name `sexpr.token_stream`) into a public `changes.symbol_changes(ctx, custom_dir, rel) -> tuple[dict[str, str] | None, str | None]` returning `{name: STATUS_NEW|STATUS_CHANGED}` or a skip reason; `_mark_symbols` then calls it. This avoids a third copy of the D-21 rule. Both `_read_current` and `_read_head` already honour `MAX_KICAD_TEXT_BYTES`.
**Context:** `incoming.incoming_context(repo_root, layout.footprints_dir, kicad_fp_dir)` (`importer/incoming.py:19-44`) already builds exactly the Phase 10 install gate's context (Custom `.pretty` folders + KiCad's). Reuse it; do not build `find_footprint_libs(repo_root)` (an `rglob` over the whole repo including the large Würth submodule). If `kicad_fp_dir` is `None`, mimic `scan_all` (`kicad_fp_dir if kicad_fp_dir is not None else find_kicad_footprint_dir()`).
**Derived symbols:** a derived symbol inherits Manufacturer, Datasheet and Description from its `extends` parent (`atomic_check._owner`). If the parent changed but the child's own tokens did not, the child's verdict can change. Treat a symbol as changed when any ancestor in its `extends` chain is changed (follow `kicad_files.extends_name`).
**Example (shape only):**
```python
# Source: shape derived from changes._mark_symbols and atomic_check.check_symbol (read this session)
@dataclass(frozen=True)
class AtomicFailure:
    library: str      # "Atomic_Sensor_Motion"
    rel_path: str     # repo-relative, the string the dialog's focus uses
    part: str
    rule: str         # one of atomic_check.ATOMIC_RULES
    text: str         # Violation.text, already plain language

@dataclass(frozen=True)
class GateResult:
    blocking: tuple[AtomicFailure, ...] = ()
    old: tuple[AtomicFailure, ...] = ()        # D-02: unchanged parts that already failed
    problems: tuple[str, ...] = ()             # unreadable committed library -> refuse (safe default)
    entries: tuple = ()                        # (nickname, rel_path, SymbolEntry) for the dialog's ScanResult
```
Log line per failure: `f"{failure.library} / {failure.part}: {failure.text}"`, the shape `check_libraries` already logs (`atomic_check.py:673`, `prefix = f"{lib.nickname} / {entry.name}: "`).

### Pattern 2: "Introduced by this commit" for linked symbols (D-04) via a HEAD view
**What:** for committed `kind == "footprint"` files, find the Atomic_ symbols that link them, then keep only violations absent from the same symbol checked in a "HEAD view".
**How (recommended, bounded):**
1. Parse every `Atomic_` library of `Custom/Symbols` once (only when at least one footprint is committed). A symbol links a committed footprint when `ctx.resolve_footprint(<its Footprint text>).rel_path` equals the committed footprint's repo-relative path.
2. W-view: `check_symbol(..., ctx=ctx_w)` (working tree). If no violation, done.
3. H-view: `ctx_h = AtomicContext(resolve, model_problems)` built from `repo_context(..., planned_footprints={link: (rel, head_bytes)})` for committed footprints that exist at HEAD (`repo_context` already accepts `planned_footprints` and reads those bytes instead of disk), wrapped so a footprint that is **new in this commit** resolves to `'footprint "X" is not in library "Y"'` (what HEAD would have said). `AtomicContext` is just two callables, so the wrapper is ~10 lines.
4. Blocking = W-view violations whose `(rule, text)` is not in the H-view set. The rest of the W-view violations are "old" (D-02 amber).
**Accepted approximation:** model **existence** (`custom_model_names`) is read from the working tree in both views. A replaced model cannot change any ATOM-01 rule because `model_path_problem` judges names only, never content. A new model is only relevant through a footprint that links it, which the footprint path already covers. State this in the plan so the executor does not chase it.
**Simpler fallback if the H-view proves heavy:** block when an unchanged linked symbol fails `footprint` or `model_3d` in the W-view and the linked footprint file is in the commit list; list the rest as old. This over-blocks only when a failure pre-dated the commit AND the same footprint file is being overwritten; flag it to the user if chosen.

### Pattern 3: HEAD-moved detection after a failed `commit_paths` (D-12, REV-06)
**What:** read `before = gitops.head_commit(ctx, custom)` immediately before `commit_paths`; after any failure read it again. Moved means a commit exists.
**Where:** `commit_step.run_commit` lines 467-471 (the `_run_failed(run)` branch). If moved: build the outcome from the success-path fields (`short_hash`, branch), add a WARNING `Committed <hash> in Custom, but git did not finish in time (a hook or signing step may still be running)`, **skip** `unstage` and the parent step, and set `manual_command` when `bump_parent` was requested.
**Evidence:** a real reproduction (see Experiments) shows a slow `post-commit` hook makes git exit late but HEAD already moved. A cheap deterministic test wraps the runner: run the real `commit`, then `raise subprocess.TimeoutExpired(argv, timeout)`. The existing test `test_commit_timeout_reported` (`tests/test_commit_step.py:801`) uses `argv[6] == "commit"` in a custom runner; the new test is the same runner shape with the real commit executed first.
**Windows timing caveat:** `subprocess.run(timeout=...)` does not return at the timeout when a hook's child holds the pipe: measured `TimeoutExpired raised after 12.2 s (timeout=2)`. So `COMMIT_TIMEOUT = 300.0` can mean longer waits in practice; this is a reason to keep the commit worker locked (it already is) and not to promise a tight timeout in text.

### Pattern 4: Files identical to HEAD (D-13, D-14, REV-09)
**What:** before the commit, compute `identical = {rel for rel in tracked planned files if sha256(head_blob) == sha256(file bytes)}`. `head_blob` uses `cat-file --filters`, so a clean file under `core.autocrlf=true` hashes equal to its CRLF work-tree copy (`gitops.py:248-255`); `_dirty_before` already relies on this.
**Probe:** `CommitProbe.identical: frozenset[str]`. If it equals all planned files: panel reads "Nothing to commit: Custom already holds these files", Commit for Custom disabled; if `gitlink_old != head` offer a parent-only commit through the checkbox and name the button (e.g. "Commit parent ref").
**`run_commit`:** when `identical == set(rels)` skip `add_intent`/`commit_paths` and go straight to the parent step (the plan must define what `committed`/`custom_commit` mean here; add an explicit `CommitOutcome.parent_only` flag so `ImportDialog._log_not_committed` (`panel.committed()`) does not log "Not committed" after a successful parent-only bump). Otherwise pass only non-identical `rels` to `commit_paths`? **No.** Keep passing all `rels`: `git commit --only` ignores unchanged paths, and the existing tests pin the all-files behaviour. Only the post-commit compare changes:
```python
# Source: shape of the existing compare at commit_step.py:486-497, changed per D-13
extra = sorted(set(committed_files) - planned)
missing = sorted(planned - set(committed_files))
already = [rel for rel in missing if rel in identical]
real_missing = [rel for rel in missing if rel not in identical]
# INFO for `already`; ERROR commit.unexpected_files only when `extra or real_missing`
```

### Pattern 5: Refusal, "Open Check Atomic Parts…", "Check again", re-baseline (D-06..D-11)
- **New panel state `gated`** (add to `_STATES`, currently `"probing", "unavailable", "refused", "offer_switch", "switching", "ready", "committing", "done", "failed"`). Reuse of `refused` is wrong: that state returns early from `probe_commit` with no parent info and no file markers, while a gate refusal should keep the file list, message, and parent options visible and only disable Commit. `_set_state` currently sets `self._message.setReadOnly(not ready)`; make the message editable in `gated` too.
- **Strip text:** `f"⚠ Commit refused: {n} part(s) break the atomic rule"` (reuse `_STRIP_PREFIX["refused"] = "Commit refused: "`), then one label per failure (`Atomic_Sensor_Motion / LIS3MDL: no datasheet`) capped by the existing `_EARLIER_SHOWN = 10` pattern with `…and k more`. Keep the log lines in the Phase 9 D-05 shape.
- **Opening the dialog:** `AtomicCheckDialog(scan_result, repo_root, *, focus, backup_root, running, pick_model, parent)` (`atomic_check_dialog.py:42-52`). It reads only `scan_result.symbol_libs[*].symbols[*].violations/findings` and `lib.nickname/rel_path`, and its row key is `(rel_path, entry.name)` which equals the `focus` tuple. Build a `ScanResult(symbol_libs=[SymbolLibrary(nickname, rel_path, "Custom", atomic=True, symbols=[entry...])])` from `GateResult.entries` (entries from `check_symbol(fixable=True)` carry `FixSpec`s). The import dialog opens it itself with `parent=self` and `dialog.open()`; it needs `ATOMIC_BACKUP_ROOT`, a module global in `main_window.py:40`, so pass it to `ImportDialog` as a new keyword (like `backup_root`).
- **After Apply:** `AtomicCheckDialog.applied(list[Issue])` fires then the dialog `accept()`s. The import dialog re-emits it (new `Signal`) so `MainWindow` runs `_on_atomic_fixes_applied` (log + `_start_scan()`), the same path the menu dialog uses (`main_window.py:1004-1007`); a scan while the import dialog is open is already done by `_on_import_installed`. Then automatically trigger "Check again" so the user does not have to click twice (optional).
- **Re-baseline (D-08):** add `commit_plan.rebaseline(cplan) -> CommitPlan` that returns `dataclasses.replace(cplan, files=...)` where each file whose current hash differs from `expected_sha256` becomes `replace(f, expected_sha256=<current>, note="changed")`. `CommitFile` and `CommitPlan` are frozen, so never mutate. Add `note: str = ""` and `installed: bytes | None = None` fields **with defaults at the end**; every current constructor is positional with 6 arguments (`commit_plan.py:133`, `tests/gitfixtures.py:235`, `tests/test_commit_panel.py:34`) and keeps working.
- **Pre-image for the diff:** `build_commit_plan` has `op.data` for text ops (and `op.source` for models); store `installed=op.data` (a reference, not a copy). The "changed since install" diff is then `content.diff_text(installed, current, "<name> (as installed)", "<name> (now)")`, reusing the Phase 5 view the same way `pre_import_diff` does. Models are binary: use `content.binary_text`. This is simpler than snapshotting at dialog-open time and covers KiCad edits too.
- **"Added by a fix" (D-10):** during Check again, for each new or changed committed symbol resolve its `Footprint` through the gate context to a footprint file; for each footprint file in the plan or resolved, parse its `(model ...)` paths with `kicad_files.find_models`; a path starting `${CUSTOM_3DMODEL_DIR}/` (`atomic_check.CUSTOM_MODEL_PREFIX`) maps to `Custom/3DModels/<rest>`. Add a file to the plan when it exists, is not in the plan, and `gitops.tracked_paths` says untracked. **Also add tracked footprint files the fix modified** (hash differs from `head_blob`) when a committed symbol links them: the dialog's `attach_model` fix edits a footprint to add its model line (`atomic_fixes._footprint_file`), which D-10's text ("new, untracked") does not cover (Open Question 2).
- **Stale-between-check-and-click:** `_precheck` keeps `changed_since_install(cplan)` first; the message must point at Check again instead of "commit by hand".

### Pattern 6: Re-probe after a refusal keeps state (D-11, REV-10, IN-01)
**Problem in the current code:** `ImportDialog._start_probe` calls `panel.show_plan(cplan)` which resets the file list, **replaces the user's edited message with `default_message`**, resets the branch label and clears the outcome (`commit_panel.py:246-267`). `apply_probe` then calls `_clear_outcome()` (line 272) and re-ticks the parent checkbox (lines 282-289).
**Fix:** add `panel.begin_reprobe()` (state `probing`, keep message, plan, file list, parent choice) used by re-probes; keep `show_plan` for the first probe and for the post-switch probe only if the message should reset (it should not: use `begin_reprobe` there too). Hold `self._pending_refusal: list[Issue]` on the panel: `show_outcome` for a non-committed outcome stores it; `apply_probe` re-renders it at the top of the outcome area unless the new probe itself is `refused` or `unavailable`; cleared on the next Commit, Check again or Switch click (D-11). Parent choice: track `self._parent_wanted: bool | None`; set `True` only on the first probe after `show_plan`; update it from `toggled` only when the box is enabled and the change is user-driven (guard with a `_programmatic` flag because `setChecked` inside `apply_probe` emits `toggled`).
**Dialog:** `_on_commit_done` must, for `not outcome.committed`, call the re-probe after `show_outcome`, and `_on_commit_requested` already passes `probe.branch` so it picks up the fresh branch once `_commit_probe` is replaced.

### Pattern 7: Probe that does not block Close (IN-02)
**Facts:** `ImportDialog._shutdown` ends with `for worker in list(self._workers): worker.wait()` (`import_dialog.py:3036-3037`), and `MainWindow.closeEvent` calls `dialog.reject()` -> `done()` -> `_shutdown`. So simply not calling `_set_git_worker` makes Close possible, but the close then **blocks the GUI thread** until the probe ends (about 15 git calls at `DEFAULT_TIMEOUT = 30.0` each, plus the gate). That is the cost IN-02 complains about.
**Recommended:** give `probe_commit` a `cancelled: Callable[[], bool] | None = None` keyword. Check it between git calls (in `_preexisting`, `_dirty_before`'s loop, the gate's per-file loop) and return `CommitProbe(state="unavailable", reason="cancelled")` early. `ImportDialog` creates a `threading.Event` per probe, passes `cancelled=event.is_set`, and `_shutdown` sets all probe events before the `wait()` loop, so the close waits at most for one running git call. Do **not** abandon a running `QThread`: the code base records that destroying finished workers early crashed the process (`_reap` docstring), and a lambda connected to a worker's `result` signal keeps pointing at the dialog.
**Also:** add a generation check in `_on_probe_done` (`if worker is not self._probe_worker: return`) because Check again and the post-switch probe can overlap. Tests that wait for the probe via `dialog.is_committing()` must use `finish_workers` or a new `is_probing()` instead; `is_committing()` should stay "switch or commit".
**ImportCore DI:** `core.probe_commit(cp, kicad_fp_dir=..., cancelled=...)` and `core.run_commit(cp, m, b, expected_branch=br, progress=progress, kicad_fp_dir=...)`. Every existing fake accepts `**kwargs` (`no_git_probe(cplan, **kwargs)`, `no_git_commit(*args, **kwargs)`, `blocking_commit(cplan, message, bump, **kwargs)`), so new keywords do not break them.

### Pattern 8: UI-02 changes with exact locations
| Defect | Location now | Change |
|--------|-------------|--------|
| Commit not primary | `commit_panel.py:189-194` (`self.commit_button = QPushButton("Commit")`) | `self.commit_button.setStyleSheet(theme.PRIMARY_BUTTON_QSS)` |
| Install Part not primary | `import_dialog.py:735-738` | `self._install_btn.setStyleSheet(PRIMARY_BUTTON_QSS)`; note `tests/test_main_window_import.py:672` pins the same pattern for Generate |
| "Committed" in `failed` | `commit_panel.py:462` `{"committing": "Committing...", "done": "Committed", "failed": "Committed"}` | `failed` -> `"Committed in Custom only"`; button disabled (already, `ready` only) |
| Tint | `commit_panel.py:210-212` `QVBoxLayout` of labels; `_apply_strip` only tints `refused`/`unavailable`/`offer_switch` | wrap `_outcome_layout` in a `QFrame` with `setObjectName("outcomeStrip")` and a stylesheet `QFrame#outcomeStrip {{ background-color: {tint}; padding: {theme.SP_SM}px; }}` (the object-name selector keeps the child `QLabel`s, which are `QFrame` subclasses, unstyled); tint by strongest severity: any ERROR -> `ERROR_TINT`, else any WARNING -> `AMBER_TINT`, else `SUCCESS_TINT` |
| Magic numbers | `commit_panel.py:205` `setFixedSize(240, 16)`, `:259` `fontMetrics().height() + 8`, `:260` height arithmetic | width `theme.SP_XL * 8`, height `theme.SP_MD`; `+ theme.SP_SM`; keep `sizeHintForRow` and `frameWidth()` (Qt metrics) |

Existing tests assert label colour via `panel._outcome_labels[0].styleSheet()` containing `theme.SUCCESS` / `theme.ERROR` (`tests/test_commit_panel.py:377,464`), so keep the per-label colour styles inside the tinted frame.

### Pattern 9: Manual command (WR-03) as a pure, platform-parameterised function
```python
# Source: shlex stdlib; PowerShell quoting verified in the Experiments section
def _ps_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"

def manual_command(parent: Path, custom_rel: str, subject: str, *, windows: bool | None = None) -> str:
    use_ps = (sys.platform == "win32") if windows is None else windows
    q = _ps_quote if use_ps else shlex.quote
    return f"git -C {q(parent.as_posix())} commit -m {q(subject)} -- {q(custom_rel)}"
```
Take `windows` as a parameter so the POSIX branch and the PowerShell branch are both unit-testable on the Windows workstation. The label becomes "In PowerShell:" on Windows (`commit_panel.py:345` currently `Finish it by hand: ...`; the outcome issue text at `commit_step.py:512-513` embeds `Finish it by hand: {manual}` and `show_outcome` filters on that prefix at line 341, so keep that literal or update both places together).

### Anti-Patterns to Avoid
- **Mutating `CommitFile`/`CommitPlan`:** both are `@dataclass(frozen=True)`. Return new objects with `dataclasses.replace`.
- **Running the gate on the GUI thread or inside `show_plan`:** parse and git reads belong on the `TaskWorker`.
- **Reusing the `refused` state for the gate:** it drops parent info and file markers (see Pattern 5).
- **Calling `show_plan` for a re-probe:** it overwrites the user's message.
- **A fourth copy of the D-21 compare or of `parent_message` assembly:** extract and share.
- **Putting a Windows-only quoter behind `sys.platform` without a parameter:** untestable on the dev box.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic rules | A second rule implementation | `atomic_check.check_symbol` + `AtomicContext` | D-05: rule logic unchanged; the scan, the install gate and the migration share it |
| New/changed symbol compare | A new differ | token-stream compare in `changes._mark_symbols`, extracted to `symbol_changes` | D-21 "content, not formatting"; handles CRLF and reformat |
| Gate context | Own footprint index | `incoming.incoming_context` + `repo_context(planned_footprints=...)` | Exact-case listings and planned-bytes override already implemented |
| HEAD content with line endings | `git show` + manual CRLF handling | `gitops.head_blob` (`cat-file --filters`) | autocrlf-safe, already tested |
| POSIX quoting | manual escaping | `shlex.quote` | stdlib |
| Diff view | own diff text | `content.diff_text`, `content.binary_text`, `ContentText` | Phase 5 view the decisions name |
| Running the dialog's fixes | re-implementing fixes | `AtomicCheckDialog` as is | D-07 |
| Cancelling a git subprocess | killing processes | cooperative flag between calls | `run_git` is a blocking `subprocess.run`; no kill hook exists |

**Key insight:** every hard part (rules, compare, fixes, HEAD reads, diff) already exists; the phase is wiring, state-machine care, and four real-world edge cases (PowerShell 5.1 quoting, slow-hook timeouts, author vs committer identity, derived symbols).

## Common Pitfalls

### Pitfall 1: D-16 quoting is wrong for `"` and a trailing `\` on Windows PowerShell 5.1
**What goes wrong:** `git ... -m 'Add "Foo" to lib'` reaches git as `Add Foo to lib`; an argument ending in `\` that also contains a space loses its closing quote.
**Why:** PowerShell 5.1 (`$PSNativeCommandArgumentPassing` behaves as `Legacy`) wraps the argument in double quotes without escaping embedded ones. PowerShell 7.3+ changed this; on Windows its default is `Windows` mode, which equals `Standard` except for `cmd.exe`, `cscript.exe`, `find.exe`, `sqlcmd.exe`, `wscript.exe` and `.bat/.cmd/.js/.vbs/.wsf` [CITED: learn.microsoft.com about_Preference_Variables]. git.exe is not in that list.
**How to avoid:** see Open Question 1. `$`, backtick, `'` and a mid-string `\` are safe (verified).
**Warning signs:** a pasted command whose commit subject lacks its quote characters.

### Pitfall 2: `identity_known` checks only the committer
**What goes wrong:** with only `GIT_COMMITTER_*` set (or only `GIT_AUTHOR_*`), `git var GIT_COMMITTER_IDENT` exits 0 but `git commit` exits 128. The probe says "ready", the commit fails.
**How to avoid:** `identity_known` must require both `git var GIT_AUTHOR_IDENT` and `git var GIT_COMMITTER_IDENT`. Update the message in `commit_step.py:147` ("git does not know who you are: set user.name and user.email") to mention that `GIT_AUTHOR_*` / `GIT_COMMITTER_*` also work.

### Pitfall 3: A timeout does not mean "nothing committed", and it is not prompt on Windows
See Pattern 3. Never unstage when HEAD moved.

### Pitfall 4: Changed parent, unchanged child
A derived symbol's verdict depends on its parent. Treat an unchanged child of a changed parent as changed (Pattern 1).

### Pitfall 5: `apply_probe` clears the refusal it should keep
`apply_probe` begins with `self._clear_outcome()`. Without a stored pending refusal the REV-10 text vanishes the moment the re-probe returns.

### Pitfall 6: Parent preview and committed text differ in three places when `gitlink_old` is None
(`commit_step.py:196-197`) `_earlier` returns `((), False)` when `gitlink_old is None`, so the panel calls `parent_preview(..., listed=False)` and prints `(the Custom commits since  could not be listed)` with an empty hash; (`commit_step.py:390-391`) `commit_parent_ref` sets `commits = ... if old else []` and `listed=commits is not None`, which is `True`, so the real message has no such line **and no commit lines at all**; (`commit_plan.py:250`) `parent_message` has two shapes for the range line. After the fix both must call one builder. Decide whether the new Custom commit's own line `- <short> <subject>` is listed when `old` is None; recommended yes, because when `old` exists the real message (from `log_range(old, new)`) includes the new commit and the preview adds `(NEW_PLACEHOLDER, subject)`. Test property: replace `<new commit>` in the preview with the real short hash and compare to `commit_parent_ref`'s returned message. Watch `_short()` (`sha[:7]`) versus `%h` in `log_range` (git's auto-abbrev, can exceed 7 characters in a big repo): use one source for both.

### Pitfall 7: Subject mismatch between `subject_of()` and git's `%s`
`subject_of` returns the first non-blank line; git's `%s` joins the first paragraph's lines with spaces. A message whose first paragraph has two lines makes preview and commit differ. Use `subject_of` consistently for the placeholder line and the real commit line, or take the real subject from the message text the app wrote rather than from `git log`.

### Pitfall 8: `result.touched` includes files whose bytes equal HEAD
That is the WR-04 root cause (`applier` appends every completed `_write`). Do not "fix" the applier; handle it at the commit step (Pattern 4).

### Pitfall 9: Tests that wait on `is_committing()` for the probe
Removing the probe's lock breaks helpers that use `is_committing()` as "probe still running" (for example `tests/test_import_dialog.py:324`). Replace with `finish_workers(qtbot, dialog)` (line 2926) or a new `is_probing()`.

### Pitfall 10: `index.lock` after a killed git
A killed `git.exe` before the lock is released leaves `.git/.../index.lock`. The slow-`post-commit` reproduction did **not** leave one (the lock is released before `post-commit` runs). D-12's "do not start the parent bump" is the right conservative rule; the existing `test_index_lock_reported` covers the lock-present case.

## Findings map: each open review item against the current code

| Finding | Still present? | Current location (read this session) | Closing change |
|---------|----------------|--------------------------------------|----------------|
| WR-01 timeout | Yes | `commit_step.py:467-471` (`run = gitops.commit_paths(...)`; on failure `unstage` + `_custom_failure`); `_custom_failure` 360-370 | Pattern 3 |
| WR-02 preview vs commit | Yes | `commit_step.py:192-201`, `385-391`; `commit_plan.py:239-261`; panel `commit_panel.py:476-479` | Pitfall 6 |
| WR-03 manual command | Yes | `commit_step.py:506-508` (`subject.replace('"', '\\"')`; `git -C "..." commit -m "..." -- {cplan.custom_rel}`) | Pattern 9 + Open Question 1 |
| WR-04 identical files | Yes | `commit_step.py:486-497` | Pattern 4 |
| WR-05 stale ready | Yes | `commit_panel.py:347-350`; `import_dialog.py:2932-2939`; `_start_probe` 2835-2847 | Pattern 6 |
| IN-01 parent re-tick | Yes | `commit_panel.py:282-289` | Pattern 6 |
| IN-02 probe lock | Yes | `import_dialog.py:2843-2844` `self._set_git_worker(worker)` in `_start_probe`; `done` 3045-3052; `main_window.py:1179-1196` | Pattern 7 |
| IN-03 `input` name / `_env` | Yes | `gitops.py:91` (`input: bytes | None = None`), `:74-78` (`_env` strips every `GIT_*`), `:238, 334, 339, 343, 353` callers | allow-list + rename |
| UI-02 items | Yes | Pattern 8 table | Pattern 8 |

`_env` today (verbatim, `gitops.py:74-78`):
```python
def _env() -> dict[str, str]:
    """The app's environment without any GIT_* variable (a stray GIT_DIR or GIT_INDEX_FILE would redirect every call)."""
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("GIT_")}
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "GIT_EDITOR": "true", "LC_ALL": "C"})
    return env
```
Recommended change: keep the strip, then re-add exactly `GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_AUTHOR_DATE`, `GIT_COMMITTER_NAME`, `GIT_COMMITTER_EMAIL`, `GIT_COMMITTER_DATE` when present (case-insensitive match as the strip is), before the `update`. These six are documented as read by `git commit` [CITED: git-scm.com/docs/git-commit#_commit_information]. Do not add `GIT_CONFIG_*` (they can inject `core.hooksPath`/`core.sshCommand`-class settings; not needed for identity). Update `tests/test_gitops.py:101-107`, which pins `git_keys == {"GIT_TERMINAL_PROMPT", "GIT_OPTIONAL_LOCKS", "GIT_EDITOR"}`, to keep that for other variables and add a case for the six.

## Experiments run this session (reproducible)

All run with `env/Scripts/python.exe -I` or Windows PowerShell on this machine. Scripts are in the session scratchpad (`argecho.py`, `t1.ps1`, `timeout_exp.py`, `ident_exp.py`).

**E1: PowerShell 5.1 argument passing to a native exe** (Windows PowerShell 5.1.26100.9711 [VERIFIED: `$PSVersionTable`]; `pwsh` is not installed). Each case calls a Python script that prints `sys.argv[1:]`:

| Case | PowerShell source | Argument the program received |
|------|------------------|-------------------------------|
| A | `'Update Custom: it''s $x ` + "`y \z'" (single quote doubled, `$`, backtick, mid-string `\`) | `Update Custom: it's $x `y \z` (correct) |
| B | `'Add "Foo" to lib'` | `Add Foo to lib` (embedded quotes LOST) |
| C | `'path ends\'` | `path ends"` (trailing backslash plus space: closing quote eaten) |
| D | `'Add \"Foo\" to lib'` | `Add "Foo" to lib` (works on 5.1 only; on 7.3+ in Standard/Windows mode PowerShell escapes the quotes itself, so this form would pass literal backslashes [ASSUMED, not testable here]) |

**E2: slow `post-commit` hook** (`sleep 12`, `subprocess.run(..., timeout=2)`): `TimeoutExpired raised after 12.2 s (timeout=2)`; afterwards `HEAD moved: True`, `index.lock exists: False`. On Windows `subprocess.run` calls `communicate()` again after killing the child, which waits for the hook's shell to release the pipe.

**E3: identity from environment only** (empty HOME, `GIT_CONFIG_GLOBAL` pointing at a missing file, `user.useConfigOnly=true`):

| Environment | `var GIT_COMMITTER_IDENT` | `var GIT_AUTHOR_IDENT` | `git commit --allow-empty` |
|-------------|---------------------------|------------------------|----------------------------|
| none | 128 | 128 | 128 |
| committer only | 0 | 128 | **128** |
| author only | 128 | 0 | 128 |
| both | 0 | 0 | 0 |

## Code Examples

### The shared parent-message builder (D-15 shape)
```python
# Source: shape of commit_plan.parent_message (read this session, lines 239-255), changed for old=None
def parent_message(subject, custom_rel, old, new, commits, *, listed=True):
    lines = [f"Update {custom_rel}: {sanitize_line(subject)}", ""]
    lines.append(f"{custom_rel} {_short(old)}..{_short(new)}" if old else f"{custom_rel} {_short(new)}")
    if old is None or listed:                       # no gitlink: nothing earlier, never "could not be listed"
        lines.extend(f"- {short} {sanitize_line(text)}" for short, text in commits)
    else:
        lines.append(f"(the {custom_rel} commits since {_short(old)} could not be listed)")
    return "\n".join(lines)
```
And `_earlier` returns `((), True)` for `gitlink_old is None`. `commit_parent_ref` and `parent_preview` call the same function with `commits` differing only in whether the new commit is a placeholder.

### Simulating a commit that finished but timed out
```python
# Source: same runner shape as tests/test_commit_step.py:806-810, run the real commit first
def runner(argv, **kwargs):
    done = subprocess.run(argv, **kwargs)
    if argv[6] == "commit":                       # argv[6] is the subcommand, as in the existing test
        raise subprocess.TimeoutExpired(argv, kwargs.get("timeout", 0))
    return done
```

### Real slow-hook variant (about 3-4 s)
Write a `post-commit` hook with `write_hook(repos, repos.custom, "post-commit", "#!/bin/sh\nsleep 3\n")` (helper at `tests/gitfixtures.py:304`) and wrap the runner to force `kwargs["timeout"] = 1`. Expect `Issue("git.timeout")`, HEAD moved, `reset` not called.

### Pasting-safety test against real PowerShell (skips when absent)
```python
# Source: experiment E1; run powershell -NoProfile -Command with the generated line, replacing `git` by a
# python echo script path; assert the received argv equals the intended subject for $, `, ', mid-string \
```
Add the skip condition to the "Expected skips" table in `tests/README.md` (project rule).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PowerShell passes native args through a naive joiner | `$PSNativeCommandArgumentPassing` `Windows`/`Standard` | PowerShell 7.3 [CITED: learn.microsoft.com about_Preference_Variables] | Embedded quotes survive on 7.3+, not on 5.1 (the shell on this machine) |
| Strip every `GIT_*` | Keep the six identity variables | this phase (REV-11) | Identity from the environment works |

**Deprecated/outdated:** the `Finish it by hand: git -C "..." commit -m "..."` POSIX-style command on Windows.

## Runtime State Inventory

Not a rename/refactor/migration phase. None of the five categories applies: no stored data, service config, OS registration or env-var key is renamed. The only on-disk state touched is the review disposition file (`.planning/milestones/v1.0-phases/06-git-commit-step/06-REVIEW-DISPOSITION.md`, set each finding to `fixed`).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | In PowerShell 7.3+ (Standard/Windows mode) a pre-escaped `\"` inside single quotes passes literal backslashes, so no single form of embedded `"` works on both 5.1 and 7 | Pitfall 1, E1 case D | If wrong, a `\"` escape on Windows would be a valid portable fix; test on a machine with pwsh before choosing |
| A2 | A git process killed before it releases `index.lock` leaves the lock behind | Pitfall 10 | The conservative "no parent bump" rule is unaffected; only wording |
| A3 | The gate's file parsing and HEAD reads finish fast enough for a probe on the real `Custom` (not measured; probe already does about 15 git calls) | Pattern 1 | A slow probe lengthens "Checking..."; mitigated by cancel and the worker |
| A4 | A committed footprint's referenced model existence read from the working tree in both W-view and H-view is an acceptable approximation | Pattern 2 | A rare false "old" for a footprint whose HEAD content pointed at a model that only this commit adds |
| A5 | Refusing (not passing) when a committed `Atomic_` library cannot be read or parsed is the right default | Pattern 1 `problems` | A user with a corrupt library cannot commit that file from the panel; they can fix and Check again |
| A6 | `%h` can be longer than 7 characters in a large repo while `_short()` uses `[:7]` | Pitfall 6 | Preview/commit text could differ only in the abbreviation length |

## Open Questions

1. **D-16 versus Windows PowerShell 5.1 (needs a user decision before the plan locks it)**
   - What we know: single quotes with `''` doubling are correct for `$`, backtick, `'` and mid-string `\` (E1 case A). They are **not** correct for `"` or a trailing `\` on 5.1 (E1 B, C). The success criterion says a subject with quotes "runs as shown when pasted".
   - What's unclear: which PowerShell the user pastes into (this machine: 5.1 only; Windows Terminal may default to 5.1 here).
   - Recommendation: build the command as D-16 says, but when the subject contains `"` (or any argument ends in `\`) write the full parent message to a file the app keeps (for example under the existing `%APPDATA%/KiCadExtLibManager/` area or the install backup folder) and print `git -C '<parent>' commit -F '<file>' -- 'Custom'`. Windows file names cannot contain `"`, so this form is safe on 5.1 and 7. It also fixes a second latent mismatch: the current manual command commits only the first line of the generated parent message. If the user prefers D-16 literally, document the 5.1 limitation in the "In PowerShell:" help text.

2. **D-10 scope: modified tracked footprints**
   - What we know: the check dialog's 3D fix edits a footprint file (adds the model line) and copies the `.step` into `Custom/3DModels/`. D-10 names "new, untracked" files; a **tracked, modified** footprint outside the list is also needed or the committed symbol links a footprint at HEAD that still lacks the model.
   - Recommendation: include tracked footprint files that a committed symbol links and that differ from `head_blob`, marked "added by a fix". Ask the user to confirm, since it widens D-10.

3. **Probe-time stale marker**
   - What we know: the probe does not call `changed_since_install` today; only `_precheck` does, so a stale file is discovered at the click.
   - Recommendation: compute it in the probe (cheap hash reads) so the "changed since install" amber marker and the Check again button appear before the click, matching D-08's "in the file list". Disable Commit with the reason in that case.

4. **New commit line when `gitlink_old` is None**
   - D-15 says "nothing earlier is listed" but is silent on the new commit's own line. Recommendation: list it (consistent with the `old`-present case). Confirm or drop.

5. **Parent-only bump semantics**
   - Needs `CommitOutcome.parent_only` and a decision for `ImportDialog._log_not_committed` (which keys on `panel.committed()`), the button label ("Commit parent ref" suggested) and the panel's done state.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git | all commit-step tests | yes | 2.49.0.windows.1 | tests use `requires_git` skip |
| Python venv | tests, app | yes | 3.14.4 | — |
| PySide6 / pytest / pytest-qt | panel and dialog tests | yes | 6.12.0 / 9.1.1 / 4.5.0 | — |
| Windows PowerShell | quoting verification | yes | 5.1.26100.9711 | skip the live-shell test elsewhere |
| PowerShell 7 (`pwsh`) | verifying A1 | no | — | state A1 as assumed |
| kicad-cli / KiCad install | gate context for KiCad footprints | not needed | — | tests use `write_fake_kicad` (`tests/customfixtures.py:387`) |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** `pwsh` (A1 stays an assumption).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-qt 4.5.0 (`qt_api = "pyside6"`) |
| Config file | `pyproject.toml` (`addopts = "-ra --strict-markers"`, `testpaths = ["tests"]`, `pythonpath = ["."]`) |
| Quick run command | `env/Scripts/python.exe -m pytest tests/test_commit_plan.py tests/test_commit_step.py tests/test_gitops.py tests/test_commit_panel.py tests/test_commit_gate.py -q` |
| Full suite command | `env/Scripts/python.exe -m pytest -m "not wurth"` (about 8 minutes; full about 18) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GIT-06 | failing new part, failing pre-import edit, old failure (amber, no block), footprint overwrite breaking a linked symbol, derived child of changed parent, unreadable library, `non-Atomic_` library skipped | unit on `tmp_path` superproject | `pytest tests/test_commit_gate.py -q` | No, Wave 0 |
| GIT-06 | `_precheck` refuses at the click and writes nothing (no `add`/`commit` in recorded argv) | unit | `pytest tests/test_commit_step.py -k gate -q` | No, Wave 0 |
| REV-06 | HEAD moved after timeout: warning, no unstage (`reset` absent), no parent commit, manual command; HEAD not moved: old path | unit (runner wrapper + one real slow hook) | `pytest tests/test_commit_step.py -k timeout -q` | partial: `test_commit_timeout_reported` exists |
| REV-07 | preview equals committed text, with and without gitlink | unit | `pytest tests/test_commit_plan.py tests/test_commit_step.py -k parent_message -q` | partial |
| REV-08 | `_ps_quote`/`manual_command` for `windows=True/False`; live PowerShell paste-safety (skips if absent) | unit | `pytest tests/test_commit_step.py -k manual -q` | No, Wave 0 |
| REV-09 | identical file INFO, parent bump proceeds; all-identical probe; parent-only bump | unit | `pytest tests/test_commit_step.py -k identical -q` | No, Wave 0 |
| REV-10 | refusal then re-probe: branch change recovers, message and parent choice kept, refusal text kept, own refusal replaces it | pytest-qt + dialog fakes | `pytest tests/test_import_dialog.py tests/test_commit_panel.py -k reprobe -q` | No, Wave 0 |
| REV-11 | six identity variables kept, `GIT_DIR` etc stripped; commit by env identity; author+committer ident check; checkbox choice kept; Close during probe returns promptly (fake runner blocked on an Event, cancel releases it) | unit + pytest-qt | `pytest tests/test_gitops.py tests/test_commit_step.py tests/test_import_dialog.py -k "identity or probe_close or parent_choice" -q` | partial |
| UI-02 | Commit and Install carry `PRIMARY_BUTTON_QSS`; tint per strongest severity; `failed` label; no off-scale constants | pytest-qt | `pytest tests/test_commit_panel.py tests/test_import_dialog.py -k "primary or tint or label" -q` | partial |

### Sampling Rate
- **Per task commit:** the quick run above (target under 30 s per touched module; the git-fixture tests build a session-cached superproject).
- **Per wave merge:** `pytest tests/test_commit_*.py tests/test_gitops.py tests/test_import_dialog.py tests/test_importer_layering.py tests/test_layering.py -q`.
- **Phase gate:** full suite green (the session guard in `tests/conftest.py` fails the run if the live `Custom/` changes).

### Wave 0 Gaps
- [ ] `tests/test_commit_gate.py`: build the superproject with `make_superproject(..., populate=...)` using a wrapper that calls `populate_custom` then `customfixtures.write_atomic_files(custom)` so `Atomic_Footprints.pretty/*.kicad_mod` and models exist; use `atomic_part(...)`/`atomic_lib(...)` to write failing and passing symbols.
- [ ] `tests/test_importer_layering.py`: register `importer.commit_gate` in `ALLOWED` (suggest `{"models", "gitops", "kicad_files", "sexpr", "atomic_check", "changes", "importer.commit_plan", "importer.incoming"}`) and widen `importer.commit_step` (line 157 currently `{"models", "gitops", "importer.plan", "importer.commit_plan", "importer.content"}`) with `importer.commit_gate`. `tests/test_layering.py` pins top-level module imports; adding `symbol_changes` to `changes.py` needs no new import.
- [ ] Update `tests/test_import_dialog.py` helpers that wait on `is_committing()` for the probe; update `tests/test_gitops.py:101-107`.
- [ ] `tests/README.md`: add the live-PowerShell skip row.
- [ ] Update the help text in `widgets/help_dialog.py` (Commit section around lines 344-362 says the dialog and main window cannot be closed while git runs) and check `tests/test_help_dialog.py` for pinned text.
- [ ] After fixing: set the eight rows of `06-REVIEW-DISPOSITION.md` to `fixed`.

## Security Domain

`security_enforcement` is enabled (absent = enabled in `.planning/config.json`, `security_asvs_level: 1`).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | yes (file-system scope) | commit stays path-limited (`commit --only` + `--literal-pathspecs`); only `Atomic_` Custom files are judged; newly added files must stay inside `Custom` (`commit_plan` `commit.outside_custom` check) |
| V5 Input Validation | yes | the user-editable commit subject enters the manual shell command: quote per platform (`_ps_quote`, `shlex.quote`); library/symbol names are already constrained by `naming.sanitize_name`; KiCad files are parsed with node and size caps (`MAX_KICAD_TEXT_BYTES = 8 MiB`, `MAX_KICAD_TEXT_NODES`) |
| V6 Cryptography | no (SHA-256 is an integrity compare only) | `hashlib` |
| V12 Files | yes | any new message file for the manual command must be written outside the repo and not world-writable assumptions made; no path built from untrusted text (gate resolves footprints by exact directory listing, as `repo_context` does) |
| V14 Configuration | yes | `run_git` environment allow-list: only the six identity variables are re-admitted; `GIT_DIR`, `GIT_INDEX_FILE`, `GIT_WORK_TREE`, `GIT_CONFIG_*` stay stripped |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Pasted command injection via a crafted commit subject (`$(...)`, backtick, quotes) | Tampering / Elevation | single-quote with `''` doubling in PowerShell, `shlex.quote` on POSIX, or `-F <file>`; test with `$(calc)`-style subjects |
| Environment redirecting git to another repository | Tampering | keep stripping `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_CONFIG_*`; add a test that the six identity names are the only re-admitted ones |
| Commit of a file outside the shown list | Tampering | gate runs again in `_precheck`; stale check still applies between "Check again" and the click (D-08) |
| Gate TOCTOU (file changes between probe and click) | Tampering | D-03 second run in `_precheck`; re-baseline only on an explicit Check again click |
| A malicious `.kicad_sym` exhausting memory during the gate | Denial of service | the existing caps in `kicad_files.parse_bytes(..., max_nodes=...)` and size limits; refuse on a parse failure |
| Hook output rendered as rich text | Tampering | panel labels are plain text (`_plain_label`); keep new gate lines plain |

## Project Constraints (from CLAUDE.md)

From `./CLAUDE.md` and `./.claude/CLAUDE.md`:
- Python 3.10+ syntax, standard library only unless clearly justified; PySide6 6.12; keep Windows 11 primary and cross-platform branches working.
- **Safety:** no write without a preview first; writes must be atomic or backed up; git commits need explicit confirmation; pushing is impossible (GIT-05).
- Every git call goes through `run_git` (argv only, allow-list, `--literal-pathspecs`, no push subcommand). `ALLOWED_SUBCOMMANDS` is, verbatim (`gitops.py:20-23`): `"--version", "rev-parse", "symbolic-ref", "status", "merge-base", "rev-list", "log", "ls-tree", "cat-file", "var", "add", "reset", "switch", "commit", "ls-files", "diff-tree", "check-ignore"`. The gate needs nothing outside this list.
- Qt-free services return `Issue` lists routed by `Severity`; errors go to the panel and the log, never to message boxes (a `QMessageBox` only for About and the existing path-variable confirm).
- Module layering: lower modules never import `main_window`; widgets depend on `models` and `table_generator`/importer values; importer modules must be registered in `tests/test_importer_layering.py` `ALLOWED` and never import PySide6.
- Naming: `_on_<event>` handlers, `self._<name>` widget attributes, private helpers underscore-prefixed, one-line docstrings, `Path` for filesystem inputs, `list[str]`-style messages for side-effecting helpers, keep message literals stable where callers match substrings.
- `blockSignals` pairs and a `_updating`-style flag around programmatic widget changes (relevant to the parent checkbox in IN-01).
- Plain-language UI: no raw KiCad field names in user-facing text (the gate lines use `Violation.text`, which `atomic_check` already writes in plain language).
- The WurthElektronik submodule is read-only (the gate and commit only touch `Custom`).
- The test suite must never write to the live `Custom/`; `tests/conftest.py` guards it. Verification commands use `env/Scripts/python.exe -m pytest ...`.
- GSD workflow: do not edit outside a GSD command.

## Sources

### Primary (HIGH confidence)
- Files read in full this session: `kicad_lib_manager/gitops.py`, `importer/commit_step.py`, `importer/commit_plan.py`, `importer/incoming.py`, `changes.py`, `atomic_check.py`, `widgets/commit_panel.py`, `widgets/atomic_check_dialog.py`, `widgets/theme.py`, `tests/gitfixtures.py`; relevant ranges of `widgets/import_dialog.py` (245-400, 1195-1285, 2740-3067), `main_window.py` (865-1060, 1179-1196), `library_scanner.py` (335-600), `models.py`, `importer/plan.py`, `importer/layout.py`, `tests/test_commit_step.py`, `tests/test_gitops.py`, `tests/test_import_dialog.py` (probe tests), `tests/test_importer_layering.py`, `tests/customfixtures.py` (fixtures).
- `.planning/milestones/v1.0-phases/06-git-commit-step/06-REVIEW.md`, `06-UI-REVIEW.md`, `06-REVIEW-DISPOSITION.md`.
- Local experiments E1-E3 (above).

### Secondary (MEDIUM confidence)
- [CITED: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_preference_variables] `$PSNativeCommandArgumentPassing` values, defaults per platform, and the legacy-exe exception list.
- [CITED: https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_quoting_rules] single-quoted strings are verbatim; `'don''t'` includes a single quote; backtick is literal in single quotes.
- [CITED: https://git-scm.com/docs/git-commit#_commit_information] the six `GIT_AUTHOR_*` / `GIT_COMMITTER_*` variables and the `EMAIL` fallback.

### Tertiary (LOW confidence)
- PowerShell 7.3+ behaviour for embedded quotes beyond what the docs state (A1), not run here.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependency; versions read from the venv.
- Architecture: MEDIUM - the gate's H-view is a design proposal; all other patterns are direct edits of code read this session.
- Pitfalls: HIGH - three reproduced by experiment, the rest read from the code.

**Research date:** 2026-10-29
**Valid until:** 2026-11-28 (stable; revisit if `gitops.py`, `commit_step.py` or `commit_panel.py` change before planning)
