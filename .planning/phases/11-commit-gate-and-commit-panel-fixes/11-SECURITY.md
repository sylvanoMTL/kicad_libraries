---
phase: "11"
slug: "commit-gate-and-commit-panel-fixes"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
block_on: high
created: "2026-10-30"
audited_at: "e7dc780"
---

# Phase 11 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

Collected from the `<threat_model>` blocks of plans 11-01 to 11-17.

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| process / user session environment -> git subprocess | variables inherited from the user's shell enter every git call through `_env()`; some can redirect git or change what a commit records | env vars (untrusted) |
| Custom/ work tree and HEAD -> gate parser | `.kicad_sym` and footprint bytes from the work tree or `git cat-file` are parsed before any git write; may be damaged, oversized or unreadable | library text (untrusted) |
| every Atomic_ library in Custom -> gate parser | the linked-symbol pass reads libraries outside the commit | library text (untrusted) |
| HEAD blobs -> head view | committed footprints' HEAD bytes are parsed for the comparison | footprint text (untrusted) |
| symbol Footprint text -> filesystem lookup | a symbol's Footprint field names a library and footprint the context resolves | names (untrusted) |
| footprint model text / discovered paths -> CommitPlan and commit list | model paths inside footprints decide which extra files a Check again adds | paths (untrusted) |
| commit gate -> commit step and panel | the gate's verdict decides whether git may write | verdict |
| probe time -> click time | files can change between the probe and the Commit click | file bytes |
| work tree bytes -> identical set | file bytes on disk decide which planned files are already in HEAD | file bytes |
| user-edited subject / message -> parent commit and pasted shell command | the subject the user types is copied into the parent message and the "finish it by hand" command | free text |
| app -> temp message file | the `-F` form writes the parent message outside the repo | commit message |
| git exit status and timeout -> outcome text | what the app tells the user it did must match git's real state | git state |
| git and hook output, gate texts, file names -> commit panel labels | output from git, the user's hooks and library files is shown in the panel and kept across re-probes | text (untrusted) |
| panel state -> Commit button | the kept refusal is display state; Commit must follow only the fresh probe | UI state |
| worker thread / dialog worker results -> GUI thread and panel | probe and check results arrive by queued signals; only the current generation may reach the panel | probe results |
| user close request -> running git jobs | Close, Esc and the main window's X arrive while git may run | UI events |
| Check again -> git | a re-check reads only; a commit needs its own click | — |
| check dialog fixes -> Custom files | the Phase 9 dialog writes library, footprint and model files after its own preview | file writes |
| import dialog -> main window | applied-fix issues cross into the main window's log and rescan | issues |
| file content -> content view | planned-file text and diffs are shown read-only | text |

---

## Threat Register

Evidence verified by gsd-security-auditor at e7dc780 against the current code and the latest plan that touched each threat (11-15 for the fail-closed gate and `unchecked`, 11-16 for the `_env` allow-list). The 55 tests the mitigations name were re-run: 55 passed, none skipped (the real-PowerShell paste test included).

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-11-01 | Tampering | `gitops._env` | high | mitigate | every `GIT_*` key stripped whatever its case (`gitops.py:92`); only the four identity name/email variables re-admitted (`:41-46,94-100`, narrowed from six by 11-16); `run_git` always passes `env=_env()` (`:135`); `test_run_git_keeps_only_identity_variables` | closed |
| T-11-02 | Spoofing | identity from environment | low | accept | see Accepted Risks Log AR-11-01 | closed |
| T-11-03 | Denial of service | `run_gate` parsing | medium | mitigate | size checked before work-tree reads (`commit_gate.py:95`), `max_nodes=MAX_KICAD_TEXT_NODES` (`:100`); HEAD reads capped in `changes.py:48-56`; HEAD footprint bytes capped in `atomic_check.py:482-493` (see residual note R-2) | closed |
| T-11-04 | Tampering | gate on an unreadable library | medium | mitigate | an unreadable library becomes a `problems` line and `refused = blocking or problems` (`commit_gate.py:76-78,367-372`); `test_gate_refuses_unreadable_library` | closed |
| T-11-05 | Tampering | footprint resolution | low | mitigate | footprints resolve only through `incoming_context` → `repo_context.resolve_footprint`, exact directory-listing match before any path is built (`commit_gate.py:308,354,453`; `atomic_check.py:411-423`) | closed |
| T-11-06 | Repudiation | parent message text | medium | mitigate | one builder `parent_message` for both previews and the commit (`commit_plan.py:295-331`, `commit_step.py:558-577`); `sanitize_line` removes C0/C1 and LS/PS; `test_parent_preview_equals_committed_message` | closed |
| T-11-07 | Tampering | `with_added_files` | medium | mitigate | resolved path must be inside `Custom/` or ERROR `commit.outside_custom` (`commit_plan.py:210-215`); `_precheck` refuses on any plan ERROR (`commit_step.py:503-505`); `test_with_added_files_refuses_a_path_outside_custom` | closed |
| T-11-08 | Tampering | stale "ready" after a refusal | medium | mitigate | a non-committed outcome sets "probing"; only `apply_probe` sets "ready"; Commit enabled only in "ready" (`commit_panel.py:406,447-453,704,711`); `test_panel_refusal_waits_for_reprobe` | closed |
| T-11-09 | Tampering | outcome labels | low | mitigate | outcome lines are `PlainText` labels (`commit_panel.py:501-509`, `import_result.py:99-103`); the frame tint is an object-name selector only (`:511-520`) | closed |
| T-11-10 | Tampering | shared footprint overwrite | medium | mitigate | linked pass over every `Atomic_` library (`commit_gate.py:248-336`, merged at `:390-402`); `test_gate_blocks_footprint_overwrite_breaking_linked_part` | closed |
| T-11-11 | Denial of service | parsing all Atomic_ libraries | low | mitigate | runs only when footprints or models are committed (`commit_gate.py:390`); capped reads through `_read_library`; per-path cache; `cancelled()` checked per library (`:141-149,284-285,292`) | closed |
| T-11-12 | Repudiation | timeout reporting | medium | mitigate | HEAD read before and after the commit, `_unfinished_outcome` reports the hash (`commit_step.py:677-707,849-855`); `test_commit_timeout_after_head_moved_reports_commit`, `test_commit_slow_post_commit_hook_reports_commit` | closed |
| T-11-13 | Tampering | parent bump during a leftover git | medium | mitigate | returns before any unstage, no second git write, manual command offered instead (`commit_step.py:697-706,854-855`) | closed |
| T-11-14 | Tampering | identical-file handling | low | mitigate | only absent and hash-identical files downgrade to INFO; anything else stays ERROR `commit.unexpected_files` (`commit_step.py:868-886`) | closed |
| T-11-15 | Elevation of privilege | `manual_command` (pasted shell text) | high | mitigate | `_ps_quote` single-quotes every argument and doubles every single quote, typographic ones included (`commit_step.py:617-622`); `"` or a trailing `\` switches to `-F <mkstemp file>` (`:644-665`); POSIX uses `shlex.quote`; `test_manual_command_survives_real_powershell` (7 subjects incl. `$(calc)`) ran in real PowerShell (see residual note R-1) | closed |
| T-11-16 | Information disclosure | temp message file | low | accept | see Accepted Risks Log AR-11-02 | closed |
| T-11-18 | Tampering | gate time-of-check / time-of-use | medium | mitigate | the gate runs again in `_precheck` before the first write (`commit_step.py:528-531,828<845`); stale-hash check covers every file; `rebaseline` has one caller; `test_change_after_recheck_refused_again` | closed |
| T-11-19 | Tampering | `recheck_commit` additions | medium | mitigate | only linked files added; models must match the `3DModels` listing exactly; plan containment applies again; added files marked in the panel (`commit_step.py:374-408`, `commit_gate.py:412-467`, `commit_panel.py:588-597`); `test_recheck_leaves_unrelated_untracked_files_out`, `test_linked_custom_files_never_builds_a_path_from_model_text`, `test_recheck_writes_nothing` | closed |
| T-11-20 | Repudiation | re-baseline accepting KiCad edits | low | accept | see Accepted Risks Log AR-11-03 | closed |
| T-11-21 | Denial of service | closing during the probe | medium | mitigate | the probe does not lock Close; `_shutdown` sets each probe Event before `worker.wait()`; the probe checks `cancelled` between git steps (`import_dialog.py:2818,2888,3180-3191`, `commit_step.py:325-356`); `test_close_during_probe_cancels_and_closes` | closed |
| T-11-22 | Tampering | stale probe applied after a newer one | medium | mitigate | results from a non-current worker are dropped; Commit and Switch refused while a probe runs (`import_dialog.py:2894-2895,2942-2943,2992-2993,3049-3050`); `test_stale_probe_result_is_dropped` | closed |
| T-11-23 | Tampering | Commit enabled while gated | medium | mitigate | enabled only in "ready"; click re-checks the state; `_precheck` refuses again (`commit_panel.py:704-711,735`); `test_panel_gated_lists_failures_and_disables_commit`, `test_panel_gated_commit_never_emits` | closed |
| T-11-24 | Tampering | rich text in gate lines | low | mitigate | gate lines are plain labels (`commit_panel.py:80-83,173-178`); `test_panel_gated_text_is_plain` | closed |
| T-11-25 | Elevation of privilege | automatic Check again after applied fixes | medium | mitigate | applied fixes call only `recheck_commit`; `run_commit` is reached only from the Commit click (`import_dialog.py:2852,2934,2976-2982,3057`, `commit_panel.py:734-737`); `test_fixes_applied_reemitted_and_rechecked` | closed |
| T-11-26 | Tampering | fixes written from the import dialog | low | transfer | transferred to the Phase 9 `AtomicCheckDialog` preview and `apply_preview` backups, verified in `09-SECURITY.md` (T-09-13/14/15/18 closed); `apply_preview` still has one caller; backup root passed through (`import_dialog.py:2967`, `atomic_fixes.py:660`) | closed |
| T-11-27 | Tampering | remote contact during the end-to-end run | high | mitigate | `ALLOWED_SUBCOMMANDS` has no push/fetch/pull/remote/ls-remote/submodule; any other subcommand raises before a process starts; `run_git` is the only launcher (`gitops.py:21-24,125-126`); `test_allow_list_is_exact_and_safe`, `test_full_commit_never_contacts_a_remote`, `test_gate_refusal_and_recovery_end_to_end` | closed |
| T-11-28 | Tampering | `_show_pending` re-showing hook output and the manual command | low | mitigate | re-shown through plain labels and `setPlainText` with the noise filter (`commit_panel.py:280-284,463-469,535-539`); `test_panel_gated_text_is_plain`, `test_panel_text_is_plain` | closed |
| T-11-29 | Elevation of privilege | pending detail across re-probes | medium | mitigate | `_show_pending` only renders; Commit follows the fresh state; refused/unavailable probes and every click drop the kept detail (`commit_panel.py:364-365,736,741,752`); `test_panel_failure_detail_survives_reprobe`, `test_panel_failure_detail_dropped` | closed |
| T-11-30 | Tampering | `_check_linked_symbols` fail-open on an unreadable or unlistable Atomic_ library | high | mitigate | an unlistable Symbols folder or an unreadable/unparsable outside library becomes a problem, so the probe is "gated" and `_precheck` refuses; the notes channel that could soften it is gone (`commit_gate.py:275-297`, `commit_step.py:358-364,528-531`); `test_unreadable_linked_library_refuses_probe_panel_and_click`, `test_gate_unlistable_symbols_folder_refuses` | closed |
| T-11-31 | Denial of service | parsing every Atomic_ library in the linked pass | low | mitigate | all reads through `_read_library`; an over-cap file returns a reason that becomes a refusal, not a hang (`commit_gate.py:92-103,292-297`) | closed |
| T-11-32 | Tampering | `_env` identity passthrough (stale exported dates, lower-case names promoted on POSIX) | low | mitigate | four names only, DATE variables stripped, case folded only on win32, exact upper-case key wins (`gitops.py:41-46,91-100`); `test_env_keeps_four_identity_names`, `test_env_folds_case_only_on_windows`, `test_env_exact_upper_case_wins`, `test_commit_ignores_exported_dates` | closed |
| T-11-33 | Tampering | `_env` strip of repository-redirecting variables | high | mitigate | case-insensitive strip of every `GIT_*` key on every run (`gitops.py:92,135`); `test_env_keeps_four_identity_names` (lower-case `git_work_tree`), `test_run_git_strips_every_git_variable_regardless_of_case` | closed |
| T-11-34 | Elevation of privilege | `_on_check_again` superseding a running probe | medium | mitigate | returns early while a git job runs; starts only `recheck_commit`; supersedes a running probe and drops its result (`import_dialog.py:2926-2943`); `test_check_again_refused_while_committing`, `test_check_again_supersedes_running_probe` | closed |
| T-11-35 | Tampering | a file with pre-import changes committed without the user seeing them (WR-02) | low | mitigate | combined row mark (`commit_panel.py:594-595`); `combined_view` built on a worker and shown read-only with `setPlainText` (`commit_step.py:793-803`, `import_dialog.py:2209-2215,3038-3041`, `content_view.py:58-64`); `test_combined_view_holds_both_sections` | closed |
| T-11-36 | Tampering | `_check_linked_symbols` skipping a linked part whose link to a committed footprint does not resolve | low | mitigate | becomes a `GateResult.unchecked` line, shown in the panel and logged as WARNING `commit.atomic_unchecked` (`commit_gate.py:309-314,516,523`, `commit_panel.py:569-571`) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

There is no T-11-17: no plan registered that ID. The per-plan `T-11-SC` supply-chain rows (low, accept) are outside this register.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-11-01 | T-11-02 | The identity variables come from the user's own session; git already trusts them the same way in a terminal. Nothing is pushed (GIT-05), so a wrong identity stays local and is visible in the log. | owner, at plan time (`11-01-PLAN.md` threat model) | 2026-10-29 |
| AR-11-02 | T-11-16 | The temp file holds only the parent commit message the user already saw; it is created by `mkstemp` (owner-only on POSIX, user temp folder on Windows) and never inside the repository. | owner, at plan time (`11-07-PLAN.md` threat model) | 2026-10-29 |
| AR-11-03 | T-11-20 | D-08 loosens Phase 6 D-11 on purpose after an explicit Check again click; the file is marked "changed since install" and its diff is one double-click away. | owner, at plan time (`11-08-PLAN.md` threat model) | 2026-10-29 |

*Accepted risks do not resurface in future audit runs.*

### Residual notes (not accepted, awaiting an owner decision; non-blocking)

- **R-1 (T-11-15 fallback).** When the temp message file cannot be written, a subject holding `"` or ending in `\` falls back to the `-m` form (`commit_step.py:644-648`), as plan 11-07 Task 2 specifies and `test_manual_command_falls_back_to_m_form_when_the_file_cannot_be_written` covers. Single quotes still prevent any shell expansion, but Windows PowerShell 5.1 can split such a subject into extra git arguments in that rare case. Accept it here or tighten the fallback.
- **R-2 (T-11-03 cap order).** `gitops.head_blob` loads the whole HEAD blob into memory before `_read_head` checks its length, so the cap bounds parsing, not the git read itself. The mitigation is present as declared.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-30 | 35 | 35 | 0 | gsd-security-auditor (ASVS L1, block_on high), at e7dc780 |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-30
