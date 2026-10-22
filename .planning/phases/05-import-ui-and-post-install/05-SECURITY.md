---
phase: "5"
slug: "import-ui-and-post-install"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
register_authored_at_plan_time: true
created: "2026-10-22"
---

# Phase 5 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| vendor package -> open_package / detect_candidate (worker) | Untrusted zip or folder contents enter the app; Phase 3 caps and staging apply | Untrusted archive members, names, bytes |
| Downloads folder / file dialogs / OS drag and drop -> open_package | Files and URLs chosen by the user or dropped from other applications | Untrusted paths and URLs |
| dialog edits / left-pane inputs -> build_options -> build_plan -> preview | User text and choices drive a plan that the preview must show exactly | Caller input |
| preview form -> InstallOptions -> Custom/ | User-typed field values become symbol properties written into Custom/ | Caller input |
| conflict choices -> InstallOptions.resolutions -> apply_plan | The only path by which an existing part in Custom/ is replaced | Caller decisions |
| Install click -> apply_plan -> Custom/ | The only write path into the repo; interruption could leave a partial install | Owner's library files |
| vendor and user strings -> labels, trees, content view, rich-text strip / token line / badge | Vendor-controlled names, Issue text and file content are displayed | Untrusted strings |
| files on disk -> content view | Existing library files are read for diffs | Local files (possibly large) |
| QSettings import/last_dir -> file dialogs | A persisted value read back from disk | Local setting |
| repo layout on disk / scan results -> build_plan and library trees | A partially checked-out Custom submodule and repo library names are environment inputs | Local filesystem state |
| app -> user's sym-lib-table / fp-lib-table and kicad_common.json | KiCad loads these files; a damaged entry breaks every project | KiCad configuration |
| one-off builds -> kicad-cli cache | A shared module-level cache that is not thread-safe | Process-local state |
| Result view -> operating system (Open folder) | Only app-created folders may be opened | Local path |
| app -> process list (tasklist) | Read-only check of running KiCad processes | Process image names |
| keyboard -> Install | An accidental key press must not write to Custom/ | User input |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-05-01 | Tampering | ImportDialog before Install | high | mitigate | Dialog never writes; open/detect/build_plan are read-only. `test_tracer_nothing_written_before_install` (tests/test_import_dialog.py) | closed |
| T-05-02 | Tampering | Install of a plan other than the one shown (PREV-07) | medium | mitigate | Generation counter gates Install; apply_plan gets `self._plan`. `test_install_uses_latest_plan_object`, `test_supersede_discards_stale_result` | closed |
| T-05-03 | Denial of Service | GUI freeze on a large or hostile package | medium | mitigate | open_package, detect_candidate, build_plan, apply_plan run on `TaskWorker` threads (kicad_lib_manager/widgets/import_dialog.py:170); Phase 3 caps bound the work | closed |
| T-05-04 | Tampering | Package staging removed while a plan still needs it (WR-04) | medium | mitigate | Dialog waits for workers before closing the Package; close refused while installing. `test_close_waits_and_closes_package`, `test_close_refused_while_installing` | closed |
| T-05-05 | Repudiation | Install outcome not recorded | low | mitigate | `issues_logged` carries open/failure/install Issues to the main log; Result page lists touched files | closed |
| T-05-06 | Tampering | Planner manufacturer default | medium | mitigate | Explicit "" skips inference. `test_cleared_manufacturer_skips_inference` (tests/test_install_options_clear.py) | closed |
| T-05-07 | Tampering | Model file naming from an empty MPN | medium | mitigate | `install.empty_required` refusal before naming. `test_cleared_mpn_refused` | closed |
| T-05-08 | Denial of Service | New library with missing Custom folders (WR-02) | low | mitigate | Early `install.symbols_dir_missing` / `install.footprints_dir_missing` refusal (kicad_lib_manager/importer/planner.py; tests/test_install_plan.py) | closed |
| T-05-09 | Spoofing | Low-contrast warnings hiding a problem | low | mitigate | AMBER `#8A5200` (kicad_lib_manager/widgets/theme.py); asserted in tests/test_library_table_widget.py | closed |
| T-05-10 | Denial of Service | `_updating` stuck after an exception in populate | low | mitigate | try/finally guard. `test_populate_resets_updating_after_error` | closed |
| T-05-11 | Tampering | Add-only table write altering existing entries | high | mitigate | `add_library_entries` inserts one line per table, no-op when present. `test_add_entries_keeps_every_other_byte`, `test_tables_new_library_add_only` | closed |
| T-05-12 | Tampering | Quote or backslash injection through nickname or rel_path | medium | mitigate | Entries built only via `_entry_text` (sexpr.quote). `test_add_entries_quotes_values` | closed |
| T-05-13 | Tampering | kicad_common.json corrupted by the sync | low | mitigate | Reuses `sync_kicad_path_vars` (backup, atomic write, HARD-03); only caller remains `MainWindow._sync_path_vars()` | closed |
| T-05-14 | Denial of Service | Table write into a missing or wrong destination | low | mitigate | Missing destination refused with ERROR. `test_add_entries_missing_destination`, `test_tables_missing_destination_logs_error` | closed |
| T-05-15 | Tampering | Newest Downloads zip processed without consent | medium | mitigate | Offer lists the name only; open_path runs only from Open/Browse/drop. `test_start_page_never_auto_opens` | closed |
| T-05-16 | Tampering | Stale or forged import/last_dir | low | mitigate | `load_import_dir` returns only an existing dir. `test_import_dir_round_trip` (tests/test_settings_import.py) | closed |
| T-05-17 | Spoofing | Markup or fake links in package Issue text and names | medium | mitigate | `Qt.TextFormat.PlainText` labels, plain QListWidgetItem rows. `test_issue_text_is_plain` | closed |
| T-05-18 | Repudiation | Refusal reasons lost when nothing is detected (WR-06) | low | mitigate | Package and detection Issues shown and logged. `test_nothing_found_shows_package_warnings` | closed |
| T-05-19 | Denial of Service | Content view of very large files | medium | mitigate | 5000-line / 512 KiB display caps, 8 MiB read cap, chunked model hashing on a worker; truncation tests in tests/test_import_preview.py | closed |
| T-05-20 | Spoofing | Preview showing values other than those written | medium | mitigate | Rows derived from the plan only. `test_rewrites_match_planned_bytes` | closed |
| T-05-21 | Spoofing | Vendor names interpreted as markup in tree or content view | low | mitigate | QTreeWidgetItem text, QPlainTextEdit, PlainText header label | closed |
| T-05-22 | Tampering | Blank UI choice reaching InstallOptions (IN-04) | low | mitigate | `_form_values` passes only candidate names. `test_picker_never_passes_blank` | closed |
| T-05-23 | Tampering | Field shown with one value but written with another | medium | mitigate | `field_defaults` mirrors the planner. `test_field_defaults_equivalence` (tests/test_import_form.py) | closed |
| T-05-24 | Tampering | Drop of several, non-local or unexpected paths | medium | mitigate | Exactly one local .zip or folder accepted; others refused and logged. Drop tests in tests/test_main_window_import.py | closed |
| T-05-25 | Tampering | Import started while a scan runs or a dialog is open | low | mitigate | Busy re-check on dragEnter and drop. `test_drop_refused_while_busy`, `test_busy_state_controls` | closed |
| T-05-26 | Spoofing | Help HTML | low | accept | Static text only; see Accepted Risks Log | closed |
| T-05-27 | Spoofing | Markup or link injection in rich-text strip, token line, badge | medium | mitigate | `html.escape` on every interpolated string, internal `reason:{n}` hrefs, `setOpenExternalLinks(False)` (import_dialog.py:564). `test_strip_escapes_markup` | closed |
| T-05-28 | Tampering | Install into a library name holding a placeholder token | medium | mitigate | UI blocking reason plus planner `install.placeholder_library`. `test_placeholder_blocks_install` | closed |
| T-05-29 | Tampering | Enter in a line edit triggering an install | low | mitigate | No default buttons; Ctrl+Return only when enabled. `test_ctrl_return_and_no_default_buttons` | closed |
| T-05-30 | Tampering | Bulk or pre-selected Overwrite replacing existing parts | high | mitigate | One row per conflict, nothing pre-selected, no bulk control, Install blocked until all decided. `test_conflict_rows_no_bulk_and_none_selected` | closed |
| T-05-31 | Tampering | Carried Overwrite applied to another library's item | medium | mitigate | Choices keyed by `Conflict.key` including library. `test_conflict_choice_carried_by_key` | closed |
| T-05-32 | Denial of Service | Overlapping build_plan calls racing the kicad-cli cache | low | mitigate | Single serial build queue. `test_builds_never_overlap` | closed |
| T-05-33 | Tampering | Dialog or app closed mid-install leaving a partial state | high | mitigate | Close/Esc/reject/closeEvent ignored while installing; apply_plan rollback. `test_install_close_esc_reject_ignored`, `test_main_window_close_ignored_while_installing` | closed |
| T-05-34 | Elevation of Privilege | Open folder opening a package-supplied path | medium | mitigate | openUrl only for `InstallResult.backup_dir`. `test_open_folder_only_backup_dir` | closed |
| T-05-35 | Repudiation | Failure reasons hidden from the user | low | mitigate | Failure banner with every ERROR, plus log. `test_install_failure_banner_and_rebuild` | closed |
| T-05-36 | Information Disclosure | Process listing | low | accept | See Accepted Risks Log (kicad_lib_manager/kicad_process.py: fixed argv, no shell, 5 s timeout) | closed |
| T-05-37 | Tampering | Git commit or push from the import flow | medium | mitigate | No subprocess in import modules, no git call during install. `test_import_flow_never_runs_git` | closed |
| T-05-38 | Spoofing | Help HTML re-edited (Importing Parts page) | low | accept | Static text only, as T-05-26; see Accepted Risks Log | closed |
| T-05-SC | Tampering | npm/pip/cargo installs | high | accept | No package installed by any Phase 5 plan; see Accepted Risks Log | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-26 | Help dialog HTML is static text; no user, vendor or path string is inserted, so `setOpenExternalLinks(True)` in help_dialog.py only follows links the app authored | Plan 05-08 threat model | 2026-10-22 |
| AR-05-02 | T-05-36 | `kicad_running` reads process image names only via a fixed tasklist argv, no shell, 5 s timeout; only a yes/no notice is shown | Plan 05-11 threat model | 2026-10-22 |
| AR-05-03 | T-05-38 | Re-edited Importing Parts help page remains static text, as AR-05-01 | Plan 05-11 threat model | 2026-10-22 |
| AR-05-04 | T-05-SC | No npm/pip/cargo package added by Phase 5; PySide6 and pytest-qt were already pinned (05-RESEARCH.md Package Legitimacy Audit) | Plans 05-01 to 05-11 threat models | 2026-10-22 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-22 | 39 | 39 | 0 | /gsd-secure-phase (L1 grep-depth short-circuit; all 36 cited mitigation tests present and passing, 396 passed in the mitigation test files; the 3 failures are the known KiCad 10 kicad-cli format baseline in tests/test_install_plan.py, unrelated to the register) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-22
