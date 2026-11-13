---
phase: "13"
slug: "atomic-migration-and-kicad-setup"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-13"
---

# Phase 13 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

Register origin: every one of the 28 PLAN.md files carried a `<threat_model>` block (authored at plan time), and 11 SUMMARY.md files carry a `## Threat Flags` section, each stating that no surface outside its plan's own register was introduced. ASVS level 1: each `mitigate` row was verified at grep depth on 2026-11-13 — every test named in a mitigation exists under `tests/` (75 rows checked by name), and the 17 rows that name code instead of a test were grepped in the implementation (`kicad_files.load` in `stock_descriptions`; link-skipping listings in `migration/inventory.py` and both appliers' `_preflight`; `sanitize_name` and `edit_symbol` in `migration/symbols.py`; `_safe` backtick replacement in `migration/mapfile.py`; `open_model_source` with `MAX_MEMBER_BYTES` in `migration/footprints.py`; `Qt.TextFormat.PlainText` on the migration dialog labels; the `_live_custom_untouched` session guard in `tests/conftest.py`; tmp_path `config_base`/`backup_root` in `tests/test_kicad_setup.py`; patched `REPO_ROOT`/`CHECKOUT_CONFIG_BASE` in the window tests). The phase's VERIFICATION.md records the named tests passing. Block threshold: high.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| KiCad install -> app | the stock `sym-lib-table` is read from KiCad's install folder | per 13-01 | 
| app -> owner's library tables | descriptions are written into tables KiCad loads | per 13-01 | 
| app -> KiCad global settings (kicad_common.json, eeschema.json) | the app writes files KiCad also writes | per 13-02 | 
| Destination tables -> pins | nicknames read from the owner's table files | per 13-02 | 
| app -> git (Custom submodule) | the only place git is started is `gitops.run_git` | per 13-03 | 
| work tree -> git commit | the files on disk at commit time are what gets recorded | per 13-04 | 
| Custom files -> app | symbol, footprint and model files are read as untrusted text | per 13-05 | 
| planned ops -> owner's Custom tree | the transaction writes and deletes files the owner's KiCad projects use | per 13-06 | 
| file text -> paths | names read from symbol and footprint files | per 13-06 | 
| owner -> KiCad global settings | the confirm is the only gate before KiCad's settings change | per 13-07 | 
| worker thread -> GUI thread | the process list arrives as a queued signal | per 13-07 | 
| app-data draft file -> migration choices | the draft is read back as untrusted JSON | per 13-08 | 
| typed text (MPN, names) -> symbol names and file content | the owner's typed values become lib_ids and file text | per 13-09 | 
| owner-picked model file -> Custom/3DModels | an outside file is copied into the repo | per 13-10 | 
| KiCad install -> migration | official footprints are read, never written | per 13-10 | 
| planner -> owner's symbol drawings | a derive removes a member's own graphics | per 13-11 | 
| file text -> strip lines and map file | names from library files are shown and written | per 13-12 | 
| transaction -> owner's Custom tree | the only writer of the migration | per 13-13 | 
| migration -> git | tag and commit through gitops only | per 13-13 | 
| file and vendor text -> Qt widgets | names, descriptions and reasons are shown in labels, lists and tooltips | per 13-14 | 
| GUI thread -> workers | git, kicad-cli, indexing, planning and hashing run off the GUI thread | per 13-14 | 
| repo files -> content view | file content is shown in the diff view | per 13-15 | 
| owner-picked model path -> plan | an outside file path enters the choices | per 13-15 | 
| owner click -> transaction and commit | the only triggers of writes and git commits | per 13-16 | 
| main window -> owner's library tables | Generate writes the tables KiCad reads | per 13-17 | 
| two windows -> one Custom tree | importer and migration both write Custom | per 13-17 | 
| test suite -> owner's live Custom | tests must never read or write it to check docs | per 13-18 | 
| KiCad config -> app notice | the folder named in KiCad's settings is shown to the owner | per 13-19 | 
| app writes -> the checkout KiCad reads | tables and parts written in a checkout KiCad may not read | per 13-19 | 
| owner-typed choices -> planned file names | a typed MPN or 3D-model name is not deduplicated, so two parts can aim at one file | per 13-21 | 
| migration plan -> the `Custom/` working tree | the applier is the only writer; a plan it accepts is executed verbatim | per 13-21 | 
| test suite -> the owner's live `Custom/` and KiCad config | these tests drive the real planner and applier | per 13-21 | 
| owner-typed choices -> derived file names | a typed `model_name` or MPN is sanitised into a file name whose equality must be judged the way the filesystem judges it, not the way Python judges strings | per 13-22 | 
| owner input in the migration window -> the migration plan | the picked library decides where the part's symbol is written in `Custom/` | per 13-23 | 
| interpreter version -> application start | the same code must import on every supported CPython | per 13-23 | 
| scan result -> Generate Tables | `_merge_table` removes managed entries for libraries the scan does not list | per 13-24 | 
| GUI thread -> scan thread | the Skip click crosses into the worker through a lock-protected set | per 13-24 | 
| test suite -> the real WurthElektronik submodule, live `Custom/`, KiCad config | scan tests must use tmp_path fixtures only | per 13-24 | 
| vendor or v1 part text (part number, description) -> library suggestion | untrusted text decides a default target library in `Custom/` | per 13-25 | 
| installed KiCad stock symbols -> sibling index | read-only, bounded by the existing 64 MiB per-file cap | per 13-25 | 
| test suite -> live `Custom/`, the installed KiCad | new tests write only under tmp_path; live-KiCad tests only read | per 13-25 | 
| suggestion engine -> migration plan -> Run | a default library becomes a write target in `Custom/` unless the gate stops it | per 13-26 | 
| part and library names -> window labels | names come from v1 library files and KiCad stock names | per 13-26 | 
| test suite -> live `Custom/`, KiCad config | all fixtures under tmp_path | per 13-26 | 
| app -> KiCad config files | the renamed action still writes `kicad_common.json` and `eeschema.json` only after a confirm | per 13-27 | 
| test suite -> KiCad config | all chooser tests run against a synthetic config tree in tmp_path | per 13-27 | 
| migration Result view -> main window -> table files in the Destination folder | Generate writes `sym-lib-table`/`fp-lib-table` into the folder the main window holds | per 13-28 | 
| saved settings (`dest_history`) -> Destination box | old entries may name folders that no longer exist | per 13-28 | 
| test suite -> owner's QSettings, KiCad config, live `Custom/` | window tests must stay isolated | per 13-28 | 

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-13-01 | Tampering | `_entry_text` description text | medium | mitigate | Every description goes through `sexpr.quote`; `test_descriptions_are_quoted` proves a quote and a backslash round-trip and the table still parses (13-01) | closed |
| T-13-02 | Denial of service | `stock_descriptions` reading a hostile or huge stock table | low | mitigate | Read through the size-bounded `kicad_files.load`; any Issue or missing table yields `{}` and the fallback words, never an exception (13-01) | closed |
| T-13-03 | Elevation of privilege | `sync_kicad_chooser` write without consent | high | mitigate | Every write needs WRITE from the confirm; RETRY, DECLINE and a missing confirm return before any backup (`test_declined_and_missing_confirm_write_nothing`, `test_retry_writes_nothing`) (13-02) | closed |
| T-13-04 | Tampering | lost update of settings KiCad saved during the dialog | high | mitigate | Re-read both files after the yes and build the new content from the fresh parse; changed list asks again; three-pass cap (`test_confirmed_write_keeps_settings_saved_meanwhile`) (13-02) | closed |
| T-13-05 | Tampering | writing for the wrong checkout | high | mitigate | Worktree and other-checkout refusal before the confirm and again after the re-read (`test_worktree_refused_before_asking`, `test_other_checkout_refused_before_asking`) (13-02) | closed |
| T-13-06 | Tampering | malformed JSON or unexpected shape | medium | mitigate | Type checks on every key read; ERROR and nothing written; only-chooser-keys verification before backup; restore of the first file if the second write fails (`test_bad_json_and_bad_shape_write_nothing`, `test_second_write_failure_restores_first`) (13-02) | closed |
| T-13-07 | Tampering | `create_tag` argv | high | mitigate | Allow-list widened by `tag` only; the name is the constant `PRE_ATOMIC_TAG`, checked by `_TAG_NAME_RE` before any process starts (`test_create_tag_rejects_odd_names`); no `-f`/`--force` constant (forbidden-constant scan covers `precheck.py`) (13-03) | closed |
| T-13-08 | Repudiation | recovery point overwritten | high | mitigate | A tag at another commit refuses; the app never deletes or moves a tag; the owner gets the manual commands (`test_tag_elsewhere_refuses_with_commands`) (13-03) | closed |
| T-13-09 | Tampering | migrating over uncommitted work | high | mitigate | `status_entries` refusal listing every file; re-checked by `ensure_tag` right before the first write (`test_uncommitted_files_refuse_by_name`) (13-03) | closed |
| T-13-10 | Tampering | a deleted file reappearing with unknown content | medium | mitigate | `changed_since_install` treats a reappeared deleted file as stale and `_precheck` refuses (`test_reappeared_deleted_file_is_stale`) (13-04) | closed |
| T-13-11 | Elevation of privilege | atomic gate bypass | high | mitigate | Only deleted files are skipped; every written Atomic_ library is still read and judged (`test_migration_shaped_commit_records_deletions_and_moves` probes the gate on the new library) (13-04) | closed |
| T-13-12 | Tampering | ignored files staged | medium | mitigate | `_precheck` keeps refusing ignored paths, never adds with a force flag (`test_ignored_file_in_plan_is_refused`) (13-04) | closed |
| T-13-13 | Denial of service | `read_inventory` on a huge or deeply nested file | medium | mitigate | `kicad_files.load` with `MAX_KICAD_TEXT_BYTES` / `MAX_KICAD_TEXT_NODES`; an oversize file is an ERROR, never a crash (`test_inventory_reports_unreadable_library`) (13-05) | closed |
| T-13-14 | Information disclosure / Tampering | listing that follows a symlink or junction out of Custom | medium | mitigate | `os.scandir` with symlinks and junctions skipped; model links matched against the exact listing, never a path built from file text (13-05) | closed |
| T-13-15 | Tampering | paths built from names in files | high | mitigate | Library, symbol and footprint names come from sanitised names and exact directory listings; every op path is checked inside Custom (`test_plan_never_leaves_custom`); 13-13 adds the same check in the applier's preflight (13-06) | closed |
| T-13-16 | Denial of service | half-applied migration | high | mitigate | One transaction with app-data backups and reverse rollback on any `BaseException` (`test_apply_rolls_back_on_failure`) (13-06) | closed |
| T-13-17 | Tampering | Wurth submodule touched | high | mitigate | The inventory and the planner only list `Custom/`; no op can name a path outside it (`test_plan_never_leaves_custom`) (13-06) | closed |
| T-13-18 | Elevation of privilege | chooser write without consent | high | mitigate | `sync_kicad_chooser` is only called with a confirm that shows a window-modal question; Not now and Retry write nothing (`test_chooser_not_now_writes_nothing`, `test_chooser_retry_then_closed_asks_yes_no`) (13-07) | closed |
| T-13-19 | Denial of service | `tasklist` on the GUI thread | medium | mitigate | The check runs on a `TaskWorker`; one check at a time; close defers without a wait (`test_second_click_starts_no_second_check`, `test_close_waits_for_chooser_check`) (13-07) | closed |
| T-13-20 | Tampering / Denial of service | `load_draft` on a hostile file | medium | mitigate | Size cap, full type validation before use, one catch tuple including `RecursionError`; a bad file means no draft (`test_bad_drafts_start_clean`) (13-08) | closed |
| T-13-21 | Information disclosure | draft stored in the repo and committed | low | mitigate | Path from `settings.migration_draft_file` beside `settings.ini` (`test_draft_file_is_beside_settings`) (13-08) | closed |
| T-13-22 | Tampering | typed MPN or name injected into the symbol file | medium | mitigate | Names through `sanitize_name`; field values written through `edit_symbol`'s quoted property edits; library names only from `stems.name_verdict`-checked targets (window, plan 13-14) (13-09) | closed |
| T-13-23 | Denial of service | mixed formats in one library failing to load in KiCad | medium | mitigate | One format per target (`test_all_targets_share_one_format`); missing tool blocks (`test_missing_cli_blocks_run`); the load gate in plan 13-13 checks each target before any write (13-09) | closed |
| T-13-24 | Tampering | writes into KiCad's own folders | high | mitigate | Official footprints are only linked; no op path is outside Custom (`test_official_switch_links_kicad_footprint` asserts no op under the fake KiCad folders) (13-10) | closed |
| T-13-25 | Tampering / Denial of service | hostile or huge added model file | medium | mitigate | `open_model_source` intake (single member, size cap, sha256 re-check, name check), ERROR `migration.model_unreadable` otherwise (`test_added_model_is_linked`) (13-10) | closed |
| T-13-26 | Repudiation | board feature deleted by default | medium | mitigate | `default_keep` True for footprints unlinked before the migration (`test_board_feature_defaults_to_keep`) (13-10) | closed |
| T-13-27 | Tampering | wrong derive losing a drawing | medium | mitigate | Exact unit-stream equality with properties excluded; a single differing pin or line keeps the member standalone (`test_name_only_difference_is_identical`); every derive is a visible row the owner can untick; the pre-atomic tag keeps the original (13-11) | closed |
| T-13-28 | Elevation of privilege | gate judging the disk instead of the plan | high | mitigate | End-state context over planned bytes and the end-state model set (`test_model_on_delete_list_fails_even_if_present`) (13-12) | closed |
| T-13-29 | Tampering | markup in names written to the map or shown in labels | low | mitigate | Names inside code spans with backticks replaced; the window shows lines as plain text (plan 13-14) (13-12) | closed |
| T-13-30 | Tampering / Elevation of privilege | delete or write outside Custom or through a link | high | mitigate | `_preflight` containment and link refusal before anything (`test_op_outside_custom_is_refused`, `test_junction_or_symlink_is_refused`) (13-13) | closed |
| T-13-31 | Tampering | overwriting a file changed after the preview | high | mitigate | sha256 of every base before any write and again right before each op (`test_source_changed_after_preview_is_refused`) (13-13) | closed |
| T-13-32 | Denial of service | half-applied migration on interrupt or crash | high | mitigate | App-data backups first, reverse rollback on `BaseException`, leftovers reported with the backup folder (`test_interrupt_rolls_back_and_reraises`, `test_rollback_leftover_is_reported`) (13-13) | closed |
| T-13-33 | Tampering | ignored `.bak` in the commit | medium | mitigate | `build_migration_commit_plan` excludes `plan.bak_files`; the commit step also refuses ignored paths (`test_migration_commit_end_to_end`) (13-13) | closed |
| T-13-34 | Tampering | markup injection into labels and tooltips | medium | mitigate | Plain-text labels and items; tooltips escaped with `html.escape` (`test_vendor_text_is_plain`) (13-14) | closed |
| T-13-35 | Denial of service | GUI thread blocked by slow work | medium | mitigate | Every slow call on a `TaskWorker` with a generation counter (`test_long_work_runs_off_the_gui_thread`, `test_close_while_planning_waits_without_blocking`) (13-14) | closed |
| T-13-36 | Denial of service | diff of a huge or binary file on the GUI thread | medium | mitigate | `op_content` on a worker, bounded by `MAX_READ`, models summarised, never decoded (`test_op_content_kinds`, `test_file_row_opens_diff_off_thread`) (13-15) | closed |
| T-13-37 | Tampering | picked model file | low | mitigate | The path only becomes `model_source`; the planner's intake (plan 13-10) checks size, type and hash before any byte is planned (13-15) | closed |
| T-13-38 | Denial of service | closing the window mid-transaction | high | mitigate | `is_running()` / `is_committing()` block close (`test_run_applies_on_a_worker_with_tag_first`, `test_commit_panel_offered_and_probed`) (13-16) | closed |
| T-13-45 | Tampering | migrating a checkout KiCad does not read (D-26 incident) | high | mitigate | Run refuses on a `KICAD_LIB_GITHUB` mismatch before any check, tag or write (`test_wrong_checkout_refuses_run`) (13-16) | closed |
| T-13-39 | Elevation of privilege | commit or push without consent | high | mitigate | Commit only from the panel's click through `run_commit` (no push in gitops); Generate and chooser only emit signals handled by the main window's confirmed paths (`test_generate_and_chooser_buttons_emit`) (13-16) | closed |
| T-13-40 | Tampering | concurrent importer and migration writes | high | mitigate | Mutual exclusion of the two windows and of drag-and-drop (`test_import_and_migration_exclude_each_other`) (13-17) | closed |
| T-13-41 | Denial of service | tables regenerated without the new libraries | medium | mitigate | `_select_atomic_libraries` before Generate (`test_generate_after_migration_keeps_atomic_libraries`) (13-17) | closed |
| T-13-42 | Tampering | docs test touching the live Custom | low | mitigate | `tests/test_docs_atomic.py` reads only tracked Markdown and module constants; the session guard `_live_custom_untouched` stays in force (13-18) | closed |
| T-13-43 | Repudiation | writes that KiCad silently never sees (D-26 incident) | medium | mitigate | Visible amber notice after Generate and in the install Result view, plus one WARNING log line (`test_generate_warns_on_other_checkout`, `test_install_warns_in_result_view`) (13-19) | closed |
| T-13-44 | Tampering | folder text from KiCad's config rendered as markup | low | mitigate | Plain-text label (`test_banner_dismiss_and_plain_text`) (13-19) | closed |
| T-13-46 | Tampering | a real migration and commit run by a test against the live Custom | high | mitigate | Every repo is built under `tmp_path` with `make_v1_superproject`; the session guard `_live_custom_untouched` fails the run if the live Custom changes (13-20) | closed |
| T-13-47 | Tampering | `footprints.plan_footprints` 3D-model rename pass | critical | mitigate | The claimed-name registry in `_model_final_names` catches the second claim; both models keep their names and one blocking `migration.model_clash` strip line keeps Run disabled (`test_colliding_model_names_queue_no_write`, `test_two_models_resolving_to_one_name_block_run`) (13-21) | closed |
| T-13-48 | Tampering | `applier._preflight` blind to two writes for one path | high | mitigate | Duplicate write-op paths are refused with `migration.duplicate_write` before the first byte, so a future planner bug cannot destroy a file (`test_duplicate_write_plan_is_refused`) (13-21) | closed |
| T-13-49 | Tampering | owner-added 3D model (D-15) taking another part's model file name | high | mitigate | The added-model name is checked against the same registry; no write op and no model path are queued on a hit (`test_added_model_cannot_take_an_existing_model_name`) (13-21) | closed |
| T-13-50 | Tampering | Overwrite chosen for a footprint name this run is creating | high | mitigate | `_resolve_clash` refuses with `migration.overwrite_refused` and emits a single write for that path (`test_in_run_footprint_overwrite_is_refused`) (13-21) | closed |
| T-13-51 | Information disclosure | the new blocking strip lines rendered in the migration window | low | accept | The texts carry only file names the owner already sees in the preview; the plain-language rule is asserted by `test_model_clash_line_is_plain_and_single` (13-21) | closed |
| T-13-52 | Tampering | these tests writing to the owner's live `Custom/` or KiCad config | high | mitigate | Every repo is built under `tmp_path`; the `tests/conftest.py` session guard `_live_custom_untouched` fails the run if the live `Custom/` changes (13-21) | closed |
| T-13-53 | Tampering | `footprints._model_final_names` existing-model guard (line 329) vs the case-insensitive `new_path.exists()` write decision (line 485) | critical | mitigate | The guard compares `candidate.casefold()` against a prebuilt casefolded view of the whole pre-migration inventory, so the destructive write op is never created; the model keeps its on-disk name with one INFO note (`test_model_rename_cannot_overwrite_an_untouched_model`, `test_model_rename_colliding_by_case_with_an_unlinked_model_keeps_its_name`) (13-22) | closed |
| T-13-54 | Tampering | `applier._preflight` blind to a rename landing on bytes no op deletes (the single-write-op shape `migration.duplicate_write` cannot see) | high | mitigate | A write op carrying `source_rel` whose target existed at plan time and is removed by no delete op is refused with `migration.rename_would_overwrite` before the first byte (`test_rename_overwrite_plan_is_refused`) (13-22) | closed |
| T-13-55 | Tampering | a chain rename (`A.step` -> `B.step` while `B.step` -> `C.step`) whose in-order delete would remove freshly written bytes | high | mitigate | The guard keeps comparing against the whole pre-migration inventory, so a chain is never planned (`test_a_rename_onto_a_model_that_is_itself_renamed_is_kept`) (13-22) | closed |
| T-13-56 | Information disclosure | the kept-name note's text, logged into the plan's issues | low | accept | It names only the two model file names the owner already sees in the preview; the plain-language rule is asserted by `test_model_kept_name_note_is_plain_and_single` (13-22) | closed |
| T-13-57 | Tampering | these tests writing to the owner's live `Custom/` or KiCad config | high | mitigate | Every repo is built under `tmp_path`; the `tests/conftest.py` session guard `_live_custom_untouched` fails the run if the live `Custom/` changes (13-22) | closed |
| T-13-58 | Tampering | `MigrationDialog` Library combo: a list pick silently dropped, so Run writes the part into the suggested library instead of the one the owner picked | high | mitigate | `textActivated` records the pick through the same path as typing (`test_library_picked_from_the_list_is_recorded`) (13-23) | closed |
| T-13-59 | Denial of service | `migration_dialog.py` import on Python 3.10-3.13 (NameError stops the whole app) | high | mitigate | Both names imported; `test_every_annotation_resolves` fails on any future unbound annotation, `test_every_module_parses_as_python_3_10` on 3.11+ grammar (13-23) | closed |
| T-13-60 | Tampering | these tests touching the owner's live `Custom/` or KiCad config | high | mitigate | Module imports only, dialogs built under `tmp_path` with fake cores; the `_live_custom_untouched` session guard stays in force (13-23) | closed |
| T-13-61 | Tampering | an early skip that dropped or emptied a source's symbol libraries, making Generate Tables delete that source's table entries | high | mitigate | `find_symbol_libs` gets only a reporting callable and never consults `skip`; `test_a_skip_requested_while_symbols_are_read_is_honoured` asserts symbol and footprint libraries equal an unskipped scan, and `test_generate_after_a_skip_removes_no_entry` stays green (13-24) | closed |
| T-13-62 | Repudiation | a skip that happened without a log line, or a log line for a skip that did not happen | low | mitigate | The only skip line still comes from the scan result (`scan.models_skipped`); `test_skip_is_offered_while_symbols_are_read` asserts exactly one, and `test_a_skip_click_after_the_check_ended_logs_no_skip` stays green (13-24) | closed |
| T-13-63 | Tampering | a race between the click and the worker's per-file `skip(source)` question | low | accept | `ScanWorker.request_skip` and `_skip_requested` already share a lock; the set is sticky, so an early click is read on the source's first 3D-check file (13-24) | closed |
| T-13-64 | Tampering | these tests reading or editing the real WurthElektronik files or the live `Custom/` | high | mitigate | New and changed tests use fixtures under tmp_path (`two_sources`, `_synthetic_repo_with_wurth`); the WurthElektronik library is pull-only and never written; the `_live_custom_untouched` session guard stays in force (13-24) | closed |
| T-13-65 | Tampering | `siblings.family_prefixes` / `suggest_library`: a coarse three-letter vote filing a part into the wrong `Atomic_` library | medium | mitigate | Separator-aware steps (`test_icm_imu_votes_into_sensor_motion_on_the_hyphen_step`), and a weak vote checked against the description (`test_description_outranks_a_weak_vote`); remaining guesses are flagged with `weak` for plan 13-26's blocking line (13-25) | closed |
| T-13-66 | Denial of service | `family_prefixes` on a hostile or very long part number | low | accept | The regex is anchored at the start, linear, with no nested quantifiers; at most four steps are produced, the same order as today (13-25) | closed |
| T-13-67 | Tampering | a suggestion naming a manufacturer or an unallowed stem | medium | mitigate | Both the vote and the category results still go through the allowed-stems filter; `test_a_suggestion_is_empty_or_passes_the_name_rule_and_never_holds_a_manufacturer` stays green (13-25) | closed |
| T-13-68 | Tampering | these tests touching the live `Custom/` or the owner's KiCad install | high | mitigate | Synthetic stock and `Custom/` under tmp_path; live-KiCad tests only read the stock folder and skip without KiCad 10; the `_live_custom_untouched` session guard stays in force (13-25) | closed |
| T-13-69 | Tampering | `gate.check_plan`: a weak, unconfirmed library reaching Run and being committed into the wrong `Atomic_` library | high | mitigate | `library_basis == "guessed"` is a blocking `TARGET_LIBRARY` strip line until an owner choice exists (`test_guessed_library_blocks_run_until_confirmed`) (13-26) | closed |
| T-13-70 | Spoofing | `_suggestion_note` / tree marks rendering part or library names as rich text | low | mitigate | `Qt.TextFormat.PlainText` on the new label, as on the existing notes; the tree shows plain item text (13-26) | closed |
| T-13-71 | Tampering | an alternative in the dropdown counted as an existing library, hiding that Run creates a new one | low | mitigate | The badge keeps using the planned names only (`test_dropdown_offers_the_alternatives`) (13-26) | closed |
| T-13-72 | Tampering | these tests touching the live `Custom/` or KiCad config | high | mitigate | Fixtures under tmp_path; the `_live_custom_untouched` session guard stays in force (13-26) | closed |
| T-13-73 | Spoofing | the reworded wrong-checkout refusal no longer naming both folders, so the owner cannot tell which checkout KiCad reads (D-26) | medium | mitigate | The refusal is still built by `wrong_checkout_refusal(mismatch, PIN_REFUSAL_TEXT)`, which names both folders; `tests/test_kicad_setup.py:324` and `test_pin_texts_never_name_the_chooser_alone` assert it (13-27) | closed |
| T-13-74 | Tampering | a renamed Issue code breaking main_window's `chooser.retry` branch, so Retry would write without a fresh confirm | medium | mitigate | No code changes (`grep -c '"chooser\.'` unchanged); every code-based test in `tests/test_kicad_setup.py` and `tests/test_main_window_chooser.py` stays green (13-27) | closed |
| T-13-75 | Tampering | tests touching the owner's KiCad configuration | high | mitigate | The `make_window` fixture wraps `sync_kicad_chooser` with a tmp_path `config_base` and `backup_root`, as today (13-27) | closed |
| T-13-76 | Tampering | Generate Tables from the Result view writing tables into a Destination the owner cannot see | medium | mitigate | The Result view always shows the folder the main window will use, refreshed on every change; the outcome is mirrored there (`test_real_result_view_changes_the_destination_end_to_end`) (13-28) | closed |
| T-13-77 | Tampering | making the migration window non-modal, letting the main window's Generate or Import run while the migration is applying or committing | high | mitigate | `dialog.open()` kept; `test_migration_window_is_window_modal` and the end-to-end test assert WindowModal (13-28) | closed |
| T-13-78 | Tampering | a folder chosen in the Result view's picker reaching the table writer unchecked | low | accept | It goes through the same `add_dest_to_history` and `_on_generate` existence checks as the main window's Browse...; `write_tables` keeps its own backups (13-28) | closed |
| T-13-79 | Denial of service | a stale history entry silently becoming the Destination at start | low | mitigate | `_set_dest_items` skips folders that no longer exist (`test_destination_history_skips_folders_that_no_longer_exist`) (13-28) | closed |
| T-13-80 | Tampering | these tests writing the owner's QSettings, KiCad config or live `Custom/` | high | mitigate | QSettings under tmp_path, patched `REPO_ROOT`/`scan_all`/syncs/`CHECKOUT_CONFIG_BASE`, a fake migration core that reads no `Custom/`; the `_live_custom_untouched` session guard stays in force (13-28) | closed |
| T-13-SC | Tampering | npm/pip/cargo installs | low | accept | No package is installed, upgraded or added by any plan of this phase (declared identically in all 28 plans, 13-01..13-28) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-13-01 | T-13-51 | The texts carry only file names the owner already sees in the preview; the plain-language rule is asserted by `test_model_clash_line_is_plain_and_single` | owner, at plan approval (13-21) | 2026-11-13 |
| AR-13-02 | T-13-56 | It names only the two model file names the owner already sees in the preview; the plain-language rule is asserted by `test_model_kept_name_note_is_plain_and_single` | owner, at plan approval (13-22) | 2026-11-13 |
| AR-13-03 | T-13-63 | `ScanWorker.request_skip` and `_skip_requested` already share a lock; the set is sticky, so an early click is read on the source's first 3D-check file | owner, at plan approval (13-24) | 2026-11-13 |
| AR-13-04 | T-13-66 | The regex is anchored at the start, linear, with no nested quantifiers; at most four steps are produced, the same order as today | owner, at plan approval (13-25) | 2026-11-13 |
| AR-13-05 | T-13-78 | It goes through the same `add_dest_to_history` and `_on_generate` existence checks as the main window's Browse...; `write_tables` keeps its own backups | owner, at plan approval (13-28) | 2026-11-13 |
| AR-13-06 | T-13-SC | No package is installed, upgraded or added by any plan of this phase | owner, at plan approval (all 28 plans) | 2026-11-13 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-13 | 81 | 81 | 0 | /gsd-secure-phase 13 (orchestrator, L1 grep-depth; auditor not spawned per the asvs_level 1 short-circuit) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-13
