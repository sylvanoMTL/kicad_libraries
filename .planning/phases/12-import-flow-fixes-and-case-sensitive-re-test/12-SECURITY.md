---
phase: "12"
slug: "import-flow-fixes-and-case-sensitive-re-test"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-01"
---

# Phase 12 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| vendor package -> Custom/ files | incoming file names and bytes cross into the owner's library folders | file names, file bytes (owner library content) |
| test process -> OS (fsutil) | the tests run a System32 tool to change a folder flag | fixed arguments on a fresh tmp folder |
| library tables on disk -> table step | the owner's sym-lib-table and fp-lib-table may hold hand entries and stale entries | table entries (nickname, URI) |
| table step -> KiCad | KiCad loads whatever the tables point at | library URIs |
| Destination box / backup folder box -> filesystem | user-typed text becomes a folder the app reads and writes | folder paths |
| app -> KiCad global settings (kicad_common.json) | the app writes a file KiCad also writes | two path variables; the rest of the owner's KiCad settings |
| user leave/close requests -> running workers | Change..., open, Cancel, Close, X and Escape arrive while kicad-cli, git or file reads may run | UI events |
| worker threads -> GUI thread | build, one-off, open and process-list results arrive as queued signals | worker results |
| dialog lifetime -> QThread lifetime | the dialog owns its workers; destroying it under a running thread crashes the process | object lifetime |

Plans 12-02 and 12-08 add no new boundary (static stylesheets, Help text and a planning document).

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-12-01 | Tampering | planner overwrite of a case twin | medium | mitigate | Overwrite decision uses `spec.identity_of(hit)` (planner.py); `test_overwrite_model_twin_keeps_disk_spelling`, `test_overwrite_footprint_twin_keeps_disk_spelling` pass on a real case-sensitive folder | closed |
| T-12-02 | Tampering | rollback over a twin | medium | mitigate | `applier._drop_twin` unchanged; `test_rollback_removes_hand_built_twin` passes on a real listing | closed |
| T-12-03 | Elevation of privilege | fsutil call in tests/casefixtures.py | low | mitigate | Absolute System32 path, `timeout=30`, no `shell=True`, fresh folder under tmp_path, failure skips with a stated reason | closed |
| T-12-04 | Spoofing | Help page rich text | low | accept | Fixed strings built from constants; see Accepted Risks Log | closed |
| T-12-05 | Tampering | `_add_entry` repoint | high | mitigate | Only `_MANAGED_MARKER` entries with a gone target are repointed, after a backup; `test_live_managed_entry_warns_and_keeps_table`, `test_hand_entry_is_never_edited_even_when_stale` | closed |
| T-12-06 | Tampering | URI written by a repoint | medium | mitigate | New URI built from the planned `rel_path` and passed through `sexpr.quote` (table_generator.py); only the URI token is edited | closed |
| T-12-07 | Repudiation | silent table change | low | mitigate | Every repoint logs `table.backed_up` and `table.entry_updated` and sets the Result row (table_generator.py, main_window.py) | closed |
| T-12-08 | Tampering | `_finish_post_install`, `_on_generate` | high | mitigate | `MainWindow._dest_path()` returns None for blank text and every caller stops before any table read or write; tests run under `monkeypatch.chdir` to an empty folder | closed |
| T-12-09 | Tampering | `BackupDialog` restore | medium | mitigate | `BackupDialog._folder()` returns None for blank text; `test_blank_folder_cannot_restore` | closed |
| T-12-10 | Denial of service | GUI thread during Change/open | high | mitigate | Actions deferred through Finishing (`_reap` / `_try_finish`); `test_change_never_waits_unbounded` | closed |
| T-12-11 | Tampering | package closed under a running build | high | mitigate | Change/open run only when no build runs; `test_change_waits_for_build_without_blocking` | closed |
| T-12-12 | Tampering | one-off build reading the library while Install writes it | high | mitigate | A running one-off counts as updating (Install disabled) and jobs are held during install; `test_install_disabled_while_oneoff_runs`, `test_oneoff_held_during_install_runs_after_failure` | closed |
| T-12-13 | Denial of service | worker object lifetime | medium | mitigate | Workers are never `deleteLater`'d (the only `deleteLater` calls remove widgets); `_reap` keeps a bounded `wait(2000)` | closed |
| T-12-14 | Tampering | `sync_kicad_path_vars` lost update | high | mitigate | Re-read after the confirm, merge only the two variables, `_only_vars_changed` on the fresh content, backup, atomic replace; `test_confirmed_write_keeps_settings_saved_meanwhile` | closed |
| T-12-15 | Elevation of privilege | write without consent | high | mitigate | RETRY and DECLINE return before any backup; a changed list asks again; `test_retry_answer_writes_nothing`, `test_changed_list_asks_again` | closed |
| T-12-16 | Denial of service | `tasklist` on the GUI thread | medium | mitigate | KiCad check runs on a `TaskWorker`, one at a time; close defers; `test_post_install_check_runs_off_gui_thread`, `test_close_waits_for_check_without_blocking` | closed |
| T-12-17 | Tampering | malformed JSON on the re-read | medium | mitigate | `_read_config` returns the existing bad-JSON / bad-shape errors and nothing is written; `test_bad_json_on_reread_aborts` | closed |
| T-12-18 | Denial of service | GUI thread at close | high | mitigate | `done` / `closeEvent` defer through Finishing; no unbounded `.wait()` remains in import_dialog.py (grep count 0) | closed |
| T-12-19 | Denial of service | dialog destroyed under a live QThread | high | mitigate | `_finish_close` runs only when no close-relevant worker runs; the main window ignores its own close until the dialog finishes; conftest joins threads at teardown | closed |
| T-12-20 | Tampering | package closed under a reader | high | mitigate | `_discard_package` runs inside `_shutdown`, only with no running worker; `test_close_finishes_after_build_and_closes_package` | closed |
| T-12-21 | Repudiation | probe cancelled by a cancelled close | low | mitigate | Probe restarts on Cancel; superseded results dropped by the generation check; `test_cancelled_close_reprobes` | closed |
| T-12-22 | Repudiation | review dispositions | low | mitigate | 05-REVIEW-DISPOSITION.md marks WR-01/02/03/05/06 fixed, each naming its Phase 12 plan and behaviour | closed |
| T-12-23 | Tampering | `ImportDialog._cancel_btn` during an install | medium | mitigate | Cancel is wired to `reject()`; `done()` returns early while `is_installing()` or `is_committing()`; `_sync_cancel_button()` greys it out then; `test_cancel_button_disabled_while_installing` | closed |
| T-12-24 | Denial of service | Cancel while a build or worker runs | low | mitigate | Cancel takes the same `done()` → `_enter_finishing("close", …)` path as the window X, no GUI-thread join; `test_cancel_button_during_build_enters_finishing` | closed |
| T-12-25 | Repudiation | log and issue messages after rewording | low | mitigate | Reworded texts keep issue codes, severities and the matched phrases "Could not", "not found", "timed out after"; existing code/severity assertions in test_kicad_config, test_kicad_cli, test_install_plan, test_install_apply pass unchanged (full suite at 60df383) | closed |
| T-12-26 | Tampering | `sync_kicad_path_vars` write path | low | mitigate | 12-10 Task 1 changes string literals only; read, compare, backup and atomic replace unchanged; whole tests/test_kicad_config.py passes | closed |
| T-12-27 | Repudiation | `tests/test_plain_names.py` passing on an empty scan | low | mitigate | Guard asserts `len(files) > _SCAN_AT_LEAST` and that at least one allowed bare name was seen (tests/test_plain_names.py L41, L61) | closed |
| T-12-28 | Tampering | `sync_kicad_path_vars` backup location | low | mitigate | Search tokens include ".json", so the `"kicad_common" / config_dir.name` backup segment (library_scanner.py L347) is not matched and stays unchanged | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

Observation outside the register (no new threat): `MainWindow` still joins the scan worker with an unbounded `.wait()` in `_finish_scan` (runs after the scan's own finish signal) and in `closeEvent`. Both predate Phase 12; plan 12-07 left the close-time join out of scope.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-12-01 | T-12-04 | The Help stylesheet and pages are fixed strings built from theme constants; no user or vendor text reaches the Help rich text, so there is nothing to spoof. | plan 12-02 threat model (owner-approved plan) | 2026-11-01 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-01 | 22 | 22 | 0 | secure-phase (L1 grep evidence, orchestrator) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-01; re-verified 2026-11-02 after gap plans 12-09..12-11 (28 threats, all closed)

## Security Audit 2026-11-02

| Metric | Count |
|---|---|
| Threats found | 28 |
| Closed | 28 |
| Open | 0 |
