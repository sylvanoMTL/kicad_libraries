---
phase: "02"
slug: "hardening-existing-code"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-19"
---

# Phase 02 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| existing lib table on disk -> table_generator / merge | hand-edited or third-party table text is parsed and partly rewritten | owner's KiCad library tables (integrity-critical) |
| repo library names and paths -> generated S-expression | file names become quoted table values | file/folder names from vendor submodules |
| table write -> filesystem | KiCad, antivirus or a read-only flag may hold the file | table bytes, backups |
| fsutil write and backup helpers -> filesystem | a read-only flag or odd metadata may make copystat or encoding fail | any file the app writes |
| app -> KiCad global config (kicad_common.json) | the app rewrites a file KiCad owns and may rewrite on exit | KiCad environment variables (integrity-critical) |
| app -> OS process list | an external executable is launched to list processes | process names only |
| repo library/footprint files -> scanner (worker thread) | vendor and hand-edited `.kicad_sym` / `.kicad_mod` text is parsed off the GUI thread | nicknames, model paths, Issue text |
| file-derived names -> LogPanel HTML | library names, URIs and paths are rendered as rich text | untrusted strings |
| GUI thread <-> ScanWorker thread | a running QThread must keep a live Python reference until it finishes | ScanResult |
| scan findings / widget selection -> write_tables | the `selected` flags decide which libraries enter the owner's tables | selection state |
| test suite -> owner's machine / KiCad config | tests must never reach the real APPDATA/LOCALAPPDATA files or QSettings | none permitted |
| executor -> Custom submodule history; local repos -> remotes | a commit lands in the owner's personal library repository; pushing would publish it | 5 footprint files |
| docs -> owner | README and CLAUDE.md tell the owner how tables are generated | instructions |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-02-01 | Tampering | table_generator._merge_table | high | mitigate | Span splice removes only `${KICAD_LIB_GITHUB}/` entries; `test_generate_splices_table_and_logs_issues` + fixture byte tests | closed |
| T-02-02 | Tampering | LogPanel.log (rich text) | medium | mitigate | `html.escape` in `widgets/log_panel.py`; `tests/test_log_panel.py` | closed |
| T-02-03 | Tampering | test harness vs real KiCad config / QSettings | high | mitigate | `QSettings.setPath` redirect into `tmp_path`; services patched in `make_window` | closed |
| T-02-04 | Denial of Service | write_tables on unparseable table | medium | mitigate | load Issue, no backup, no write, other table still processed; `tests/test_write_tables.py` | closed |
| T-02-05 | Tampering | LibraryTableWidget selection with duplicate nicknames | high | mitigate | items keyed by `rel_path`; `_uncheck_peers`; `table.duplicate_nickname` refusal in `write_tables` | closed |
| T-02-06 | Denial of Service | itemChanged feedback loop during exclusivity | low | mitigate | `_updating` (restored in `finally`) + paired `blockSignals` | closed |
| T-02-07 | Tampering | generated table values | high | mitigate | every value through `sexpr.quote`; quote/backslash round-trip tests | closed |
| T-02-08 | Tampering | merge over unparseable or foreign table | high | mitigate | refuse on load Issue or root mismatch (D-09); byte-identical + no-backup tests | closed |
| T-02-09 | Denial of Service | partial table on lock, crash or I/O error | high | mitigate | `fsutil` atomic same-directory replace; interrupted-replace test | closed |
| T-02-10 | Tampering | backup pairing across tables | medium | mitigate | `_next_backup_number` → `backup_file(number=)` shared per Generate/Restore | closed |
| T-02-11 | Tampering | Restore from an arbitrary folder overwrites tables | low | accept | see Accepted Risks Log AR-02-01 | closed |
| T-02-12 | Tampering | sync_kicad_path_vars (wiped/truncated config) | high | mitigate | refuse on read/parse/shape failure; D-13 re-parse check; backup before atomic replace; `tests/test_kicad_config.py` | closed |
| T-02-13 | Elevation of Privilege | kicad_running subprocess | medium | mitigate | absolute `System32\tasklist.exe`, list args, no shell, 5 s timeout; failures return [] | closed |
| T-02-14 | Tampering | writing older KiCad versions' configs | medium | mitigate | only the newest numeric config dir is written; `test_only_the_newest_version_is_written` | closed |
| T-02-15 | Information Disclosure | config backups in the user's app-data folder | low | accept | see Accepted Risks Log AR-02-02 | closed |
| T-02-16 | Tampering | model existence check on a case-insensitive filesystem | medium | mitigate | exact-name set from `rglob`, never `Path.exists()`; `.STEP` vs `.step` test | closed |
| T-02-17 | Denial of Service | malformed footprint crashing the scan thread | medium | mitigate | `kicad_files.load` Issue → `scan.unreadable` WARNING | closed |
| T-02-18 | Denial of Service | overlapping ScanWorker (access violation) | high | mitigate | single `_start_scan` funnel guarded on `self._worker is not None`; `test_busy_rescans_are_dropped_and_controls_disabled` | closed |
| T-02-19 | Denial of Service | busy state stuck after an exception | medium | mitigate | `_finish_scan()` in `finally` of both handlers | closed |
| T-02-20 | Tampering | selection reset on rescan → wrong table contents | medium | mitigate | one-shot `_startup_pending`; `_reapply_selection` by `rel_path` | closed |
| T-02-21 | Tampering | unintended files in the Custom or parent commit | high | mitigate | Custom `485d530` holds exactly 5 files; parent `e9e7fcb` changes only the `Custom` gitlink | closed |
| T-02-22 | Tampering | EOL/whitespace churn in edited footprints | medium | mitigate | span-only `retarget_model`; numstat 1/1 for all 5 files | closed |
| T-02-23 | Repudiation | orphaned Custom commit in the worktree-private gitdir | high | transfer | owner pushes `Custom main` before removing the worktree; stated in the 02-07 blocking-human checkpoint (approved 2026-10-19) and in 02-07-SUMMARY.md | closed |
| T-02-24 | Tampering | accidental push of either repository | high | mitigate | no push in the plan; Custom `origin/main` still `6b1fcb4`, `main` one ahead | closed |
| T-02-25 | Tampering | fsutil.backup_file (false backup failure / unprunable backups) | medium | mitigate | best-effort `copystat` + writable chmod; `os.W_OK` test | closed |
| T-02-26 | Denial of Service | fsutil.atomic_write_text raising out of a service call | medium | mitigate | `fs.bad_encoding` Issue returned; lone-surrogate test | closed |
| T-02-27 | Tampering | second table-generation path bypassing the hardened merge | low | mitigate | `generate_lib_tables.py` deleted; no Python reference remains | closed |
| T-02-28 | Repudiation | scan finding shown with the wrong severity | low | mitigate | Issues logged via `_log_issues(result.issues)`; `test_log_panel` pins `COLORS[sev.value]` | closed |
| T-02-29 | Tampering | same-nickname libraries silently overwriting each other | high | mitigate | `find_nickname_collisions` + `collision_peers`; widget exclusivity; `write_tables` refusal | closed |
| T-02-30 | Repudiation | misleading fsutil error / EOL messages | low | mitigate | `fs.not_a_file` first, `fs.read_only` after retries, EOL text from counts | closed |
| T-02-31 | Tampering | both same-nickname peers pre-selected from a pre-Phase-2 table | medium | mitigate | `_trim_collided_selection` after every selection policy; `selection.collision_trimmed` WARNING | closed |
| T-02-32 | Tampering | vendor files under `downloaded_examples/` scanned as a library source | medium | mitigate | `downloaded_examples` in `SKIP_DIRS` (IN-03) + regression test | closed |
| T-02-SC | Tampering | package installs (all plans) | high | mitigate | no dependency changes in Phase 2: `requirements*.txt` and `pyproject.toml` unchanged since 17aa9b8 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-11 | Restore from an arbitrary folder is out of Phase 2 scope (CONCERNS.md). Restore only reads `*_backup_<N>` names and makes a safety backup of the current table before overwriting. Low severity, plan-time `accept` disposition. | plan 02-03 threat model (owner-approved plan) | 2026-10-19 |
| AR-02-02 | T-02-15 | `kicad_common.json` backups live in the same per-user local folder, on the same machine and user that already owns the config; keep-10 pruning bounds growth. Low severity, plan-time `accept` disposition. | plan 02-04 threat model (owner-approved plan) | 2026-10-19 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-19 | 33 | 33 | 0 | secure-phase (orchestrator, L1 grep-depth; auditor skipped per short-circuit: plan-time register, ASVS 1, threats_open 0) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-19

**Owner follow-up (T-02-23 transfer):** run `git -C Custom push origin main` before removing the `Kicad_Libraries-importer` worktree.
