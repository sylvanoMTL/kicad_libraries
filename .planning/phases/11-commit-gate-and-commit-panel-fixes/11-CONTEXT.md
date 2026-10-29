# Phase 11: Commit Gate and Commit Panel Fixes - Context

**Gathered:** 2026-10-29
**Status:** Ready for planning

<domain>
## Phase Boundary

The commit panel in the import dialog's Result view gets an atomic gate and its open v1.0 defects are fixed:
- It refuses to commit while a part being committed fails the Phase 9 atomic check, and it names the part and the rule (GIT-06).
- It reports what git really did: after a timeout it checks HEAD, files identical to HEAD are not counted as missing, and it re-probes after a refusal (REV-06, REV-09, REV-10).
- The parent-message preview equals the committed text, and the manual command uses Windows quoting on Windows (REV-07, REV-08).
- The parent checkbox keeps the user's choice, the dialog can close during the read-only probe, and `GIT_AUTHOR_*` / `GIT_COMMITTER_*` identity is kept (REV-11).
- The panel follows the theme: the primary button style, tinted outcomes, a correct parent-failed label and theme-scale sizes (UI-02).

Requirements: GIT-06, REV-06, REV-07, REV-08, REV-09, REV-10, REV-11, UI-02. Sources: `06-REVIEW.md` WR-01..WR-05 and IN-01..IN-03, and `06-UI-REVIEW.md`.

Out of this phase:
- The import-flow fixes and the Help dialog theme (Phase 12, REV-01..05, UI-01).
- The migration (Phase 13). The gate is built so Phase 13's single migration commit can go through the same commit step, but no migration code is written here.
- Pushing stays impossible (GIT-05). Every commit still needs an explicit click.

</domain>

<decisions>
## Implementation Decisions

### Gate scope (GIT-06)
- **D-01:** **The gate checks the new or changed symbols in the committed `.kicad_sym` files.** It covers every symbol that is new, or whose content differs from `Custom`'s HEAD, by the Phase 9 D-21 token-stream compare (`changes.py` / `gitops.head_blob`). That covers the imported part, any pre-import uncommitted edits to other symbols in the same file (the Phase 6 D-09 amber case), and later the Phase 13 migration's many parts. Symbols unchanged against HEAD are not "being committed". Scope is the Phase 9 D-23 rule: only `Atomic_` libraries are judged.
- **D-02:** **An unchanged symbol that already fails at HEAD does not block.** The panel shows one amber line, e.g. "Atomic_Sensor_Motion also holds 2 parts that already failed before this import", and the log lists each (part, rule). Commit stays possible.
- **D-03:** **The gate runs in the probe and again at the click.** The read-only probe runs it, so the panel shows the refusal and Commit is disabled before any click. `_precheck` runs it again just before the first git write, because files can change in between. Both runs stay off the GUI thread, on the existing `TaskWorker`.
- **D-04:** **Committed footprints and models also check the symbols that link them.** For each committed `.kicad_mod` or 3D model file, the `Custom` symbols that link it are checked against the working-tree content too, including symbols outside the commit and unchanged at HEAD. An example is an overwrite of a shared `Atomic_Footprints` footprint, or a replaced model. A failure that the committed footprint or model causes blocks the commit, like D-01. Planner: a linked symbol whose failure existed at HEAD regardless of this commit falls under D-02 (amber note, no block). Only failures this commit introduces block.
- **D-05:** Price/stock leftovers never block (Phase 9 D-18). The ATOM-01 rules (Phase 9's 7 rules) stay the only blocking ones. The gate reuses `atomic_check` and its `AtomicContext` unchanged in rule logic, as the Phase 10 install gate does.

### Refusal and recovery (GIT-06, REV-10)
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

### Uncertain git outcomes (REV-06, REV-07, REV-09)
- **D-12:** **A timeout after HEAD moved is reported as a commit (WR-01).** HEAD is recorded before `commit_paths` and compared after any failure. If HEAD moved:
  - a warning says "Committed <hash> in Custom, but git did not finish in time (a hook or signing step may still be running)";
  - the parent bump does not start, because a leftover git process may still hold `index.lock`;
  - the manual parent command is given (Phase 6 D-03 shape);
  - nothing is unstaged.

  If HEAD did not move, the current "nothing was committed" path stays, with unstage.
- **D-13:** **A planned file identical to HEAD is an INFO line, not an error (WR-04).** It reads "Already identical to HEAD, not in the commit: <files>", and the commit counts as successful, so the parent bump goes ahead. Only extra files (committed but not planned) stay `commit.unexpected_files` ERROR.
- **D-14:** **If every planned file is identical to HEAD, the probe says so.** The panel reads "Nothing to commit: Custom already holds these files", and the Custom commit is disabled. If the parent's gitlink is behind `Custom`'s HEAD, a parent-only bump is still offered through the parent checkbox. The button then names that action, e.g. "Commit parent ref". The exact label is Claude's discretion.
- **D-15:** **One builder for the parent preview and the committed message (WR-02).** When `gitlink_old` is None, nothing earlier is listed, there is no "could not be listed" line and no empty hash. `parent_preview` and `commit_parent_ref` call the same helper, so they cannot drift (Phase 6 D-19 promise).

### Manual command and outcome look (REV-08, UI-02)
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements and roadmap
- `.planning/REQUIREMENTS.md`: GIT-06, REV-06..REV-11, UI-02 (and GIT-01..05 as the commit-step contract)
- `.planning/ROADMAP.md` § Phase 11: the 5 success criteria
- `.planning/PROJECT.md`: Key Decisions and the Safety constraint (preview before write, explicit commit click, no push)

### Review findings being closed
- `.planning/milestones/v1.0-phases/06-git-commit-step/06-REVIEW.md`: WR-01..WR-05, IN-01..IN-03, with file and line pointers and suggested fixes
- `.planning/milestones/v1.0-phases/06-git-commit-step/06-UI-REVIEW.md`: Pillars 1-6 (primary button, tints, "Committed" label in `failed`, spacing magic numbers)
- `.planning/milestones/v1.0-phases/06-git-commit-step/06-REVIEW-DISPOSITION.md`: set each finding's disposition when fixed

### Prior phase context
- `.planning/milestones/v1.0-phases/06-git-commit-step/06-CONTEXT.md`: D-01..D-20, the commit step contract. D-11 (stale refusal) is loosened by D-08/D-09 here; D-03, D-09, D-10, D-17, D-18 and D-19 still hold.
- `.planning/phases/09-atomic-rule-check-and-scan-detection/09-CONTEXT.md`: D-05 (log shape), D-12 (check dialog, `focus`), D-13..D-16 (fixes and stale-file rule), D-18 (leftovers never block), D-21 (token-stream "changed"), D-23 (`Atomic_` scope)
- `.planning/phases/10-importer-on-the-atomic-scheme/10-CONTEXT.md`: D-21 (install gate reuses `atomic_check` on planned content), D-25 (reason-strip display pattern)

### Project docs
- `CLAUDE.md`: the Git workflow (commit in the submodule first, then the parent ref)
- `tests/README.md`: expected skips; the suite must not write to or depend on the live `Custom/`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `kicad_lib_manager/atomic_check.py`: `check_symbol(root, name, rel_path=, fixable=, ctx=)`, `AtomicContext`, `repo_context`, `is_atomic`: the gate's rule engine.
- `kicad_lib_manager/changes.py`: `mark_changes`, `_read_head`, `_head_symbols`: the D-21 new/changed compare against `Custom` HEAD.
- `kicad_lib_manager/gitops.py`: `head_commit` (WR-01 before/after), `head_blob`, `commit_files`, `unstage`, `COMMIT_TIMEOUT`, `_env` (REV-11), `run_git`.
- `kicad_lib_manager/importer/commit_plan.py`: `CommitPlan`, `CommitFile.expected_sha256`, `changed_since_install` (D-11, now re-baselinable), `parent_preview`, `default_message`, `pre_install_bytes`.
- `kicad_lib_manager/importer/commit_step.py`: `probe_commit` / `CommitProbe`, `_precheck` (the gate's click-time slot), `run_commit` (manual command at ~line 506, the files compare at ~486), `commit_parent_ref`, `_earlier`.
- `kicad_lib_manager/widgets/commit_panel.py`: `_STATES`, `_apply_strip` (amber strip, to become per-outcome tint), `_set_state` (button labels, line 462), `apply_probe` (parent re-tick, IN-01), `show_outcome` (WR-05).
- `kicad_lib_manager/widgets/atomic_check_dialog.py`: `AtomicCheckDialog(scan_result, repo_root, focus=..., backup_root=..., running=..., pick_model=...)`, opened today by `MainWindow._open_atomic_check`.
- `kicad_lib_manager/widgets/theme.py`: `PRIMARY_BUTTON_QSS`, `AMBER_TINT`, `ERROR_TINT`, `SUCCESS_TINT`, `SP_*`.

### Established Patterns
- Qt-free services return `Issue` lists routed by `Severity`. Errors go to the panel and the log, never to message boxes.
- Git and checks run on the import dialog's `TaskWorker` (`_start_probe`, `_set_git_worker`, `_on_commit_done` at `import_dialog.py` ~2796-2890).
- Every git call goes through `run_git`: argv only, an allow-list, `--literal-pathspecs`, no push subcommand.
- Plain-language UI: no raw KiCad field names in user-facing text.

### Integration Points
- `commit_step.probe_commit` and `_precheck` gain the atomic gate (D-03). `CommitProbe` carries the gate result and the old-failure notes.
- `commit_panel.py` gains "Check again" and "Open Check Atomic Parts…", the per-part refusal lines, the changed-since-install and added-by-a-fix markers, and the outcome tints.
- `import_dialog.py` wires the new panel signals: re-probe after a refusal, the probe that no longer locks Close, opening the check dialog over the import dialog, and the Install button style.
- `commit_plan.py`: a re-baseline API for `CommitFile` hashes, and adding files that fixes created (D-10).

</code_context>

<specifics>
## Specific Ideas

- Today the gate mostly catches *other* symbols in the same library file: pre-import edits and old parts. Phase 10 already blocks a non-atomic import, and D-11 catches edits to it after install. The gate's main future user is Phase 13's single migration commit.
- Refusal line example: "Atomic_Sensor_Motion / LIS3MDL: no datasheet".
- Old-failure note example: "Atomic_Sensor_Motion also holds 2 parts that already failed before this import".
- Timeout-with-HEAD-moved example: "Committed <hash> in Custom, but git did not finish in time (a hook or signing step may still be running)".

</specifics>

<deferred>
## Deferred Ideas

None. The discussion stayed within phase scope. (Phase 10's deferred idea, a log panel inside the import dialog, stays in 10-UAT.md.)

</deferred>

---

*Phase: 11-commit-gate-and-commit-panel-fixes*
*Context gathered: 2026-10-29*
