---
phase: "06"
slug: "git-commit-step"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-23"
---

# Phase 06 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| app -> git process | Repo-relative paths, package-derived names and the commit message cross into a child process | File names and message text from an untrusted vendor download |
| app environment -> git | Inherited GIT_* variables could redirect every call to another repo or index | Environment variables |
| PATH -> git executable | The program actually started is whatever PATH resolves | Executable path |
| git and hook output -> GUI | stdout and stderr of git and hooks are shown in the panel | Arbitrary text |
| app -> Custom work tree | A switch changes which branch the user's uncommitted work sits on | The user's uncommitted changes |
| keyboard -> commit action | A stray Enter must never commit | User input |
| package metadata -> commit message | Vendor, symbol and package file names come from an untrusted download | Untrusted strings |
| install result -> commit plan / git pathspecs | Paths come from the plan and must stay inside Custom; awkward names must match only themselves | Repo paths |
| app -> repository discovery | git resolves the repo from a folder; an uninitialised submodule resolves to the parent | Repo identity |
| git -> worker thread | A probe or hook that hangs keeps Close locked | Process lifetime |
| user's uncommitted work -> the commit | Bystander changes in either repo must never be swept in or lost | The user's uncommitted changes |
| repo hooks -> commit job | The owner's hooks run code inside the commit | Code execution (owner-controlled) |
| user click -> git writes | Every commit and switch must follow an explicit click | Confirmation |
| GUI thread <-> worker threads | Workers must not read state the GUI can change | Plan state |
| app shutdown -> running git job | Closing must not abandon a commit or switch halfway | Repo consistency |
| help text -> help viewer | The help page is shown as rich text | Static text |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-06-01 | Tampering | gitops.run_git argv (file and package names) | high | mitigate | argv list, no `shell=True` anywhere; paths on stdin via `--pathspec-from-file=- --pathspec-file-nul`; message via `-F` temp file (`gitops.py:334-366`). test_run_git_argv_and_env | closed |
| T-06-02 | Tampering | pathspec magic selecting other files | high | mitigate | `--literal-pathspecs` first argument by default (`gitops.py:103`); `literal=False` only for `check-ignore` with stdin paths. test_run_git_argv_and_env | closed |
| T-06-03 | Information Disclosure / Tampering | accidental contact with a remote | high | mitigate | `ALLOWED_SUBCOMMANDS` has no remote subcommand; ValueError before spawn (`gitops.py:20-23, 101-102`). test_allow_list_is_exact_and_safe, test_git_modules_hold_no_remote_or_destructive_argument, test_full_commit_never_contacts_a_remote | closed |
| T-06-04 | Tampering | inherited GIT_DIR / GIT_INDEX_FILE / GIT_WORK_TREE | medium | mitigate | `_env()` drops every `GIT_*` key and sets `GIT_TERMINAL_PROMPT=0`, `GIT_OPTIONAL_LOCKS=0` (`gitops.py:76-77`). test_run_git_argv_and_env | closed |
| T-06-05 | Elevation of Privilege | a git.exe planted inside the repository | medium | mitigate | `find_git` resolves with `shutil.which` and refuses a hit under the resolved repo root (`gitops.py:60-66`). test_find_git_refuses_inside_repo | closed |
| T-06-06 | Spoofing | git or hook output rendered as markup | low | mitigate | panel labels PlainText; git output in read-only QPlainTextEdit (`commit_panel.py:87-91`). test_panel_text_is_plain | closed |
| T-06-07 | Tampering | probe_commit targeting the parent instead of Custom | high | mitigate | `show_toplevel(Custom)` must equal Custom via normcase + resolve (`commit_step.py:76, 139`). test_probe_uninitialised_custom_unavailable | closed |
| T-06-08 | Tampering | switch_to_main discarding or overwriting the user's changes | high | mitigate | argv exactly `switch <name>` (`gitops.py:325`); no `--force`/`--discard-changes`/stash/hard reset in any git module. test_switch_argv_is_plain, test_switch_conflict_stays_detached, test_switch_to_main_carries_changes | closed |
| T-06-09 | Tampering | committing on a stale local main and moving the parent gitlink backwards | medium | mitigate | probe refuses when local main does not contain HEAD while origin/main does; switch re-checks. test_probe_stale_local_main_refused | closed |
| T-06-10 | Denial of Service | a probe waiting on a prompt or a lock | medium | mitigate | `GIT_TERMINAL_PROMPT=0`, `GIT_OPTIONAL_LOCKS=0`, `DEFAULT_TIMEOUT = 30.0` per call (`gitops.py:24, 77`) | closed |
| T-06-11 | Tampering | an unconfirmed commit triggered by Enter | medium | mitigate | Commit and Switch buttons `setAutoDefault(False)` / `setDefault(False)` (`commit_panel.py:132-133, 191-192`). test_panel_buttons_not_default, test_panel_dirty_file_amber_and_activation, test_panel_committing_locks_inputs | closed |
| T-06-12 | Spoofing | hook output or a crafted reason rendered as rich text | low | mitigate | PlainText labels, QPlainTextEdit for git output. test_panel_text_is_plain | closed |
| T-06-13 | Tampering | committing a path outside Custom | high | mitigate | `build_commit_plan` refuses with `commit.outside_custom` (`commit_plan.py:119`). test_build_refuses_outside_custom | closed |
| T-06-14 | Tampering | trailer or line injection through a package file name | medium | mitigate | `sanitize_line` on every interpolated value (`commit_plan.py:52`). test_default_message_sanitises_controls | closed |
| T-06-15 | Tampering | sweeping in, unstaging or discarding the user's other changes | high | mitigate | `add -N` for new listed paths, `commit --only` with stdin pathspecs, `reset -q` only on the app's own intent-to-add paths (`gitops.py:334-366`). test_commit_only_listed_files_with_bystanders, test_parent_commit_only_gitlink_with_bystanders, test_custom_hook_rejection_undoes_intent | closed |
| T-06-16 | Tampering | committing a file edited after the install (stale bytes) | medium | mitigate | `changed_since_install` sha256 check before any git write (`commit_step.py:320-325`). test_run_commit_refuses_stale_file | closed |
| T-06-17 | Elevation of Privilege | repo-local hooks and config run code during the commit | low | accept | D-06: hooks always run, `--no-verify` never passed; the repos are the owner's. See AR-06-02 | closed |
| T-06-18 | Information Disclosure | local paths or the user name in commit messages | low | mitigate | `Import-Package` is the base name only (`commit_plan.py:150, 219`). test_default_message_has_no_local_paths | closed |
| T-06-19 | Denial of Service | a hook or pinentry that never returns | medium | mitigate | `COMMIT_TIMEOUT = 300.0` (`gitops.py:25`), ERROR with cause, intent-to-add undone, never retried. test_commit_timeout_reported | closed |
| T-06-20 | Tampering | the dialog closed during a commit or switch | medium | mitigate | Close disabled; done/reject/Esc/closeEvent refuse while a git worker runs. test_commit_close_button_disabled_while_git_runs | closed |
| T-06-21 | Tampering | git writing without a confirmation | high | mitigate | only the read-only probe runs after install; add/commit/switch only from button clicks. test_git_state_changes_only_after_click | closed |
| T-06-22 | Tampering | a worker reading self._plan from its thread (WR-04) or a new package opened under a running job | medium | mitigate | install lambda captures the plan; `open_path` returns early while installing or committing (`import_dialog.py:990`). test_install_worker_uses_captured_plan, test_open_path_refused_while_busy | closed |
| T-06-23 | Repudiation | a refused or unavailable commit going unnoticed | low | mitigate | every probe/switch/commit Issue logged via `issues_logged`; D-02 line logged once on close without commit. test_commit_unavailable_logged_once, test_commit_not_committed_logged_on_close | closed |
| T-06-24 | Tampering | the main window closed while the Import dialog commits or switches | medium | mitigate | `MainWindow.closeEvent` ignores while `is_installing()` or `is_committing()` (`main_window.py:920-926`). test_main_window_close_ignored_while_committing | closed |
| T-06-25 | Spoofing | user, vendor or path text formatted into the rich-text help page | low | mitigate | Commit help section is static text with no formatted value (`help_dialog.py:259+`). test_help_import_page_describes_commit_step | closed |
| T-06-SC | Tampering | npm/pip/cargo installs | high | accept | no package installed by any Phase 6 plan. See AR-06-01 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-06-01 | T-06-SC | No npm/pip/cargo package is installed by any Phase 6 plan (stdlib plus the existing PySide6/pytest stack); nothing to audit. Plan-time `accept` disposition. | plans 06-01 to 06-08 threat models (owner-approved plans) | 2026-10-23 |
| AR-06-02 | T-06-17 | D-06: the owner's repo-local hooks and config must always run during commits; both repos belong to the owner. Never "fixed" with `--no-verify`. Low severity, plan-time `accept` disposition. | plan 06-07 threat model (owner-approved plan, decision D-06) | 2026-10-23 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-23 | 26 | 26 | 0 | secure-phase (orchestrator, L1 grep-depth; auditor skipped per short-circuit: plan-time register, ASVS 1, threats_open 0). All 30 named mitigation tests pass. |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-23
