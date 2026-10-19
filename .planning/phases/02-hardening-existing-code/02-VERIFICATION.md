---
phase: 02-hardening-existing-code
verified: 2026-10-19T12:00:00Z
status: human_needed
score: 5/5 must-haves verified
covered_files:
  - .planning/phases/02-hardening-existing-code/02-01-PLAN.md
  - .planning/phases/02-hardening-existing-code/02-01-SUMMARY.md
  - .planning/phases/02-hardening-existing-code/02-02-PLAN.md
  - .planning/phases/02-hardening-existing-code/02-02-SUMMARY.md
  - .planning/phases/02-hardening-existing-code/02-03-PLAN.md
  - .planning/phases/02-hardening-existing-code/02-03-SUMMARY.md
  - .planning/phases/02-hardening-existing-code/02-04-PLAN.md
  - .planning/phases/02-hardening-existing-code/02-04-SUMMARY.md
  - .planning/phases/02-hardening-existing-code/02-05-PLAN.md
  - .planning/phases/02-hardening-existing-code/02-05-SUMMARY.md
  - .planning/phases/02-hardening-existing-code/02-06-PLAN.md
  - .planning/phases/02-hardening-existing-code/02-06-SUMMARY.md
  - .planning/phases/02-hardening-existing-code/02-07-PLAN.md
  - .planning/phases/02-hardening-existing-code/02-07-SUMMARY.md
  - .planning/phases/02-hardening-existing-code/02-08-PLAN.md
  - .planning/phases/02-hardening-existing-code/02-08-SUMMARY.md
  - .planning/phases/02-hardening-existing-code/02-09-PLAN.md
  - .planning/phases/02-hardening-existing-code/02-09-SUMMARY.md
  - kicad_lib_manager/fsutil.py
  - kicad_lib_manager/kicad_files.py
  - kicad_lib_manager/library_scanner.py
  - kicad_lib_manager/main_window.py
  - kicad_lib_manager/models.py
  - kicad_lib_manager/table_generator.py
  - kicad_lib_manager/widgets/library_table.py
covered_digest: "v3:sha256:6e4220496f4c2d740d5dd4f68e6fb88fc97127efa5fc4d8aedee95f7628b34e5"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Launch `./env/Scripts/python.exe kicad_lib_manager.py` and, while the 'Scanning libraries...' dialog is visible, press Ctrl+Shift+R several times. Do NOT press Generate Tables (it would repoint KICAD_LIB_GITHUB in the real KiCad config)."
    expected: "No crash. The log shows 'A scan is already running; request ignored.' for each press. Rescan and Generate Tables are greyed out until the scan ends, then re-enabled."
    why_human: "The executor was headless. Offscreen tests (test_busy_rescans_are_dropped_and_controls_disabled and related) exercise the same guard, but the modal progress dialog and real input path were never driven in the real window (02-06 plan human-check, recorded as D5 human_judgment)."
---

# Phase 2: Hardening Existing Code Verification Report

**Phase Goal:** Generating tables, detecting KiCad and rescanning no longer lose data, crash or race, so the importer can safely build on them
**Verified:** 2026-10-19
**Status:** human_needed
**Re-verification:** No, initial verification

## Goal Achievement

All five roadmap success criteria are backed by code that exists, is wired and behaves correctly when exercised. I checked this by reading the code and by running independent scripts against the real modules, not only the project test suite. One planner-deferred human check (real-GUI Rescan hammering during the startup scan) remains, so the status is `human_needed` rather than `passed`.

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Regenerating `sym-lib-table` / `fp-lib-table` keeps every existing external entry whatever its formatting or field order; unclassifiable items kept verbatim with a warning; values with `"` or `\` are escaped | VERIFIED | `table_generator._merge_table` classifies every child through `kicad_files.lib_table` (field-order independent) and splices only managed entries via `apply_edits`. Independent run: a CRLF table with an external entry in `uri,name,descr,type,options` order plus an unknown `(weird thing)` child came back byte-identical for those parts, CRLF kept, `table.unclassified` warning logged. A library named `A"b\c` was written as `(name "A\"b\\c")` through `sexpr.quote` and re-parsed through `kicad_files.lib_table_entries` to exactly `A"b\c`. Backup `sym-lib-table_backup_1` created. |
| 2 | Generate on a locked or read-only table logs one error per file and leaves the GUI responsive and consistent; `kicad_common.json` backed up before change, written atomically, afterwards only `environment.vars` differs | VERIFIED | Independent run with both tables read-only: one `fs.read_only` ERROR Issue per file, no exception, originals unchanged, other table still processed independently (`write_tables` loops per table with `continue`). `sync_kicad_path_vars` on a config with `"vars": null` and nested data: backup written to `kicad_common/10.0/...backup_1` outside the repo before the write, result differs from the original only in `environment.vars` (semantic check `_only_vars_changed` runs before the write), non-ASCII preserved, older 9.0 config untouched, invalid JSON refused with `config.bad_json` and file left intact. `test_generate_with_read_only_sym_table_logs_one_error_and_finishes` passes. See Warning W-3 on GUI-thread work. |
| 3 | With both KiCad 9.0 and 10.0 present, 10.0 is chosen; Rescan or Set KiCad Path during a running scan does not start a second scan | VERIFIED (human check pending for real GUI) | `parse_version` / `newest_version_dirs` sort by integer tuple. Independent run with `9.0`, `10.0`, `8.0` returned `10.0`. `_start_scan` is the only scan entry point and refuses while `self._worker is not None`. `_on_set_kicad_path` also returns before opening a dialog when busy. `_set_scan_running` disables Rescan, Set KiCad Path, Generate. `_finish_scan` runs from `finally` in both finished and error handlers. Tests `test_busy_rescans_are_dropped_and_controls_disabled`, `test_busy_set_kicad_path_opens_no_dialog_and_starts_no_scan`, `test_busy_state_clears_then_one_rescan_starts_exactly_one_scan` assert exactly one scan call. The real-window check is the open human item. |
| 4 | After Rescan the user's symbol and footprint selection is unchanged; same-nickname libraries in different sources are reported as a collision and stay distinct in the UI | VERIFIED | `_reapply_selection` carries selection over by `rel_path` from the previous `ScanResult`; the startup-only table read is gated by `_startup_pending`. `LibraryTableWidget` keys `_sym_items` / `_fp_items` by `rel_path`, so same-nickname items no longer overwrite each other. `populate` no longer re-syncs footprints. Independent scan of a synthetic repo with `Custom/S`, `Wurth/S`, `Custom/F.pretty`, `Wurth/F.pretty` produced two `scan.nickname_collision` warnings with correct `collision_peers`. Widget and window tests cover distinct items, mutual exclusion, and rescan keeping the chosen peer (`test_rescan_keeps_selection_by_rel_path_and_ignores_tables`, `test_rescan_keeps_the_chosen_collision_peer`). |
| 5 | Existing `${KIPRJMOD}/Custom/3DModels/...` footprints reference `${CUSTOM_3DMODEL_DIR}/...` after one dedicated cleanup commit in `Custom`; a scan warns about any model path that still does not use it | VERIFIED | `Custom` commit `485d530` (HEAD of `Custom`, `main`) changes exactly 5 `.kicad_mod` files, 1 line each (5+/5-), each `${KIPRJMOD}/Custom/3DModels/X.step` becomes `${CUSTOM_3DMODEL_DIR}/X.step`. The parent repo's tree points at `485d530`. `grep` finds 0 `KIPRJMOD` in `Custom/**/*.kicad_mod`. `scan_all` on the real repo (10 symbol libs, 9 footprint libs) returns zero issues. On a synthetic repo, `scan.model_var` fired for a `${KIPRJMOD}` path, `scan.model_missing` for a case-mismatched `A.step`, `scan.model_absolute` for a non-Custom absolute path, and the Wurth `${WE_3DMODEL_DIR}` path was accepted. The commit is intentionally unpushed (owner follow-up, approved at the 02-07 checkpoint). |

**Score:** 5/5 truths verified, 0 behavior-unverified. The behavior-dependent truth in SC3 (second-scan prevention) has passing behavioral tests, so it is not PRESENT_BEHAVIOR_UNVERIFIED. The human item below is the planner-deferred real-GUI check.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `kicad_lib_manager/table_generator.py` | Span-splice merge, per-table independent writes, shared backup number | VERIFIED | 376 lines, `_merge_table`, `write_tables`, `restore_backup_pair`, `table_info` all substantive and used by `main_window` and `backup_dialog`. |
| `kicad_lib_manager/kicad_files.py` | `lib_table` / `LibEntry` classification and `retarget_model` | VERIFIED | `lib_table`, `_lib_entry`, `retarget_model` present; consumed by `table_generator` and `library_scanner`. |
| `kicad_lib_manager/library_scanner.py` | Numeric version choice, backed-up atomic config sync, collisions, per-source model rules | VERIFIED | `parse_version`, `newest_version_dirs`, `sync_kicad_path_vars`, `_prune_backups`, `_collide`, `check_3d_model_paths` all present and wired into `scan_all` and `main_window`. |
| `kicad_lib_manager/main_window.py` | Guarded scan funnel, startup-only pre-selection, rel_path re-apply | VERIFIED | `_start_scan`, `_set_scan_running`, `_finish_scan`, `_reapply_selection`, `_trim_collided_selection`, `_select_linked_footprints` present. |
| `kicad_lib_manager/widgets/library_table.py` | rel_path-keyed items, collision mark, mutual exclusion | VERIFIED | `_sym_items` / `_fp_items` keyed by `rel_path`; `_uncheck_peers`, `_peer_selected`, "Collision" status. |
| `kicad_lib_manager/models.py` | `Issue`, `Severity`, `collision_peers` | VERIFIED | `Severity.__str__` returns value; `collision_peers` on both library dataclasses. |
| `Custom` submodule commit `485d530` | Five footprints rewritten in one commit | VERIFIED | See SC5. |
| `generate_lib_tables.py` (must be gone) | Legacy CLI deleted with its docs | VERIFIED | File absent; no references outside `.planning/` and the git-ignored `.claude/CLAUDE.md`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main_window._on_generate` | `table_generator.write_tables` | direct call, result logged via `log_issue` | WIRED | Issues routed by severity, no substring classification left. |
| `main_window._on_generate` | `library_scanner.sync_kicad_path_vars` | direct call, independent of table outcome | WIRED | Runs after `write_tables` regardless of failures. |
| `table_generator.write_tables` | `fsutil.backup_file` / `atomic_write_text` | per table, shared `backup_number` | WIRED | Failure Issues are appended and the loop continues. |
| `table_generator._merge_table` | `sexpr.quote` | `_entry_text` | WIRED | Every generated value is quoted. |
| `main_window._on_scan_finished` | `_reapply_selection` / `_apply_existing_selection` | `startup` flag from `_startup_pending` | WIRED | Only the first scan reads the tables. |
| `scan_all` | `find_nickname_collisions` -> `LibraryTableWidget` | `collision_peers` | WIRED | Peers set by the scan, consumed by the widget and `_trim_collided_selection`. |
| `scan_all` | `check_3d_model_paths` | `kicad_files.find_models` | WIRED | Parser-based, not regex. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `LibraryTableWidget.populate` | `lib.selected`, `collision_peers` | `ScanResult` from `scan_all` and `_reapply_selection` | Yes (real scan of this repo: 10 sym / 9 fp libs) | FLOWING |
| `_on_generate` log | Issue list | `write_tables`, `sync_kicad_path_vars` | Yes (exercised with real files) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full suite | `env/Scripts/python.exe -m pytest -q` | 553 passed, 3 skipped (Wurth submodule not checked out) | PASS |
| External entry/CRLF/quote round trip | scratch script against `write_tables` | external bytes kept, `A"b\c` re-parses exactly, unclassified child kept + warning | PASS |
| Read-only tables | scratch script | one `fs.read_only` error per file, no exception, files unchanged | PASS |
| kicad_common sync | scratch script | backup first, only `environment.vars` changed, older version untouched, bad JSON refused | PASS |
| Version choice | `find_kicad_config_dir` with 8.0/9.0/10.0 | `10.0` | PASS |
| Collision and model-path rules | scratch script on synthetic repo | 2 collisions, `model_var`, `model_missing`, `model_absolute` fired, Wurth var path accepted | PASS |
| Real repo scan | `scan_all(repo)` | 10 / 9 libs, 0 issues | PASS |

### Probe Execution

Step 7c: SKIPPED. No probe scripts are declared by the phase plans, and no `scripts/*/tests/probe-*.sh` exist.

### Requirements Coverage

Every ID declared across the nine plans maps to a REQUIREMENTS.md entry, and no Phase 2 ID in REQUIREMENTS.md is orphaned.

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|--------------|-------------|--------|----------|
| HARD-01 | 02-01, 02-03, 02-08 | Keep every external table entry, unclassifiable kept verbatim with warning | SATISFIED | Truth 1; `table.unclassified` warning, `table.external_clash` keeps the external entry. |
| HARD-02 | 02-01, 02-03, 02-04, 02-08 | Locked/read-only table logs one error per file, UI consistent | SATISFIED | Truth 2; per-table independent failure handling. |
| HARD-03 | 02-04 | `kicad_common.json` backed up, atomic, only `environment.vars` changed | SATISFIED | Truth 2; backup before write, semantic verification before write. |
| HARD-04 | 02-04 | Newest KiCad version chosen numerically | SATISFIED | Truth 3; config dir and footprint dir both use `newest_version_dirs`. |
| HARD-05 | 02-06 | No second scan while one runs | SATISFIED (real-GUI check pending) | Truth 3; single funnel `_start_scan`. |
| HARD-06 | 02-01, 02-03 | `"` and `\` escaped in generated values | SATISFIED | Truth 1; all five values through `quote`. |
| HARD-07 | 02-02, 02-06 | Rescan keeps current selection | SATISFIED | Truth 4. |
| HARD-08 | 02-02, 02-06, 02-09 | Same-nickname collisions reported and distinct in UI | SATISFIED | Truth 4. |
| HARD-09 | 02-05, 02-07 | KIPRJMOD paths rewritten in one cleanup commit; scanner warns on remaining non-`${CUSTOM_3DMODEL_DIR}` paths | SATISFIED | Truth 5. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (phase source files) | - | `TBD` / `FIXME` / `XXX` debt markers | none found | No blocker. |
| `kicad_lib_manager/main_window.py` | 517-540 | Generate pipeline runs synchronously on the GUI thread | Warning (REVIEW WR-06) | Brief freeze possible (tasklist call, fsync, up to ~1 s lock retries). Does not violate "no crash"; contradicts the project's QThread convention. |
| `kicad_lib_manager/main_window.py` | 517 | Empty destination text resolves to CWD | Warning (REVIEW WR-01) | Pre-existing input-validation hole; not a HARD-0x requirement. |
| `kicad_lib_manager/table_generator.py` | 154-167, 289 | Missing submodule makes Generate remove its managed entries; clash casualties logged as "deselected" | Warning (REVIEW WR-03, WR-04) | Removal of stale managed entries is the decided behaviour (CONTEXT D-08) with a warning per entry and a backup, so it is not a gap. External entries are never at risk. |
| `kicad_lib_manager/table_generator.py` | 306 | `list_backup_pairs` / restore dialog crash when destination is a file | Warning (REVIEW WR-05) | Restore path, outside the HARD-0x acceptance wording. |

The seven review warnings and four info items are advisory and recorded as `open` in `02-REVIEW-DISPOSITION.md`; none contradicts a must-have.

### Human Verification Required

#### 1. Hammer Rescan during the startup scan in the real GUI

**Test:** Launch `./env/Scripts/python.exe kicad_lib_manager.py` from the repo. While the "Scanning libraries..." dialog is visible, press Ctrl+Shift+R several times. Do not press Generate Tables, because it would repoint `KICAD_LIB_GITHUB` in the real KiCad config.
**Expected:** The app does not crash. The log shows "A scan is already running; request ignored." once per press. Rescan and Generate Tables are greyed out until the scan ends, then become enabled again.
**Why human:** The plan's human-check could not be run headless. The offscreen tests cover the same guard, but the modal progress dialog and real keyboard input were not driven.

### Gaps Summary

No gaps. All five success criteria and all nine requirement IDs are satisfied in the codebase. Remaining items are non-blocking.

- **W-1 (bookkeeping):** `.planning/REQUIREMENTS.md` still shows HARD-01 to HARD-08 as `[ ]` / `Pending` (only HARD-09 is ticked). The orchestrator should tick them when closing the phase.
- **W-2 (owner follow-up):** `Custom` commit `485d530` is not pushed. This is the agreed state. Until it is pushed, a fresh clone of the parent repo cannot fetch the submodule commit the parent now points to.
- **W-3 (advisory):** Review warnings WR-01 to WR-07 stay open. WR-06 (synchronous Generate on the GUI thread) is the closest to success criterion 2's "GUI responsive" wording. It does not cause a crash or data loss, so I did not treat it as a failure.

---

_Verified: 2026-10-19_
_Verifier: Claude (gsd-verifier)_
