---
phase: "4"
slug: "plan-and-install-core"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
register_authored_at_plan_time: true
created: "2026-10-20"
---

# Phase 4 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| vendor package -> planner | Symbol, footprint and model bytes and every name inside them are untrusted vendor content | Untrusted KiCad S-expressions, names, STEP bytes |
| vendor names and field values -> KiCad text | Vendor-controlled strings are spliced into files KiCad will load | Untrusted strings |
| vendor field values and caller overrides -> KiCad text and file names | MPN becomes a file name; every value is spliced into a library | Untrusted strings, caller input |
| vendor symbol format -> target library | A newer format inside an older library makes KiCad fail or lose data | Format version |
| caller-edited library name -> filesystem paths | The library name becomes `<name>.kicad_sym` and `<name>.pretty` inside Custom/ | Caller input |
| caller resolutions -> existing Custom/ items | Overwrite and rename decisions act on the owner's existing parts | Caller decisions |
| importer -> kicad-cli process | Untrusted vendor S-expressions are handed to an external binary | Untrusted KiCad text, argv |
| kicad-cli -> filesystem | The CLI rewrites whatever path it is pointed at, including a whole .pretty folder | File writes |
| preview -> apply | Time passes between plan and apply; the owner may save in KiCad or the package may change | File state (TOCTOU) |
| planner / applier -> Custom/ and app-data | The only importer code that writes or deletes files | Owner's library files, backups |
| disk -> verifier | Verification trusts only what is on disk after the writes | Written files |
| stock/Wurth libraries -> name search | Large third-party files are scanned on every install | Large local files |
| test suite -> real repository | Tests run inside the repo checkout next to the real Custom/ submodule | Owner's library files |
| UAT scratch folder -> repo | A mis-set UAT folder could land inside the repo | Test output |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-04-01 | Tampering | applier.apply_plan op paths | high | mitigate | `resolve()` + `is_relative_to(custom_dir)` before any write, ERROR `install.path_outside_custom` (applier.py); names via `sanitize_name` / `sanitize_filename` | closed |
| T-04-02 | Tampering | model copy (WR-04) | high | mitigate | Model bytes hashed at apply time against `PackageFile.sha256`, ERROR `install.source_changed` / `install.source_gone` (applier.py) | closed |
| T-04-03 | Denial of service | planner vendor text read | medium | mitigate | `MAX_KICAD_TEXT_BYTES` read cap and `max_nodes` parse ceiling (planner.py) | closed |
| T-04-04 | Tampering | planner/applier existing targets | high | mitigate | Clashes become Conflicts, blocked plans never applied, app-data backup + pre-image restore (planner.py, applier.py) | closed |
| T-04-05 | Tampering | tests/installfixtures.py | low | mitigate | Builders return bytes only; `write_bytes`/`open(` count in installfixtures.py is 0 | closed |
| T-04-06 | Tampering | run_cli argv | high | mitigate | List argv, fixed subcommands, no shell; `shell=True` count in kicad_cli.py is 0; `load_gate` refuses non-stem names | closed |
| T-04-07 | Denial of service | run_cli on hostile input | medium | mitigate | Per-call `timeout`, `TimeoutExpired` -> ERROR `install.cli_failed` (kicad_cli.py) | closed |
| T-04-08 | Tampering | kicad-cli writes | high | mitigate | All CLI I/O in a fresh `tempfile.mkdtemp` folder; `fp upgrade` on a staging copy only (kicad_cli.py) | closed |
| T-04-09 | Denial of service | temp folders | low | mitigate | `shutil.rmtree` in `finally`; test asserts temp folders are gone | closed |
| T-04-10 | Tampering | property/name/model edits | high | mitigate | Every written value goes through `sexpr.quote` (kicad_files.py); quoted-name round-trip and injection tests | closed |
| T-04-11 | Tampering | rename_symbol_edits | medium | mitigate | Exact unquoted-name match with anchored `re.escape` sub-symbol pattern; substring test (PARTX, URLs untouched) | closed |
| T-04-12 | Denial of service | find_name_elsewhere over stock libraries | medium | mitigate | Bytes prefilter + depth-1 regex, no parse; no-parse test; 0.33 s on KiCad 9 stock | closed |
| T-04-13 | Spoofing | link and model existence checks | high | mitigate | Exact-case `os.listdir` sets; `.exists()` count in verify.py is 0 | closed |
| T-04-14 | Denial of service | unreadable or huge files in search folders | low | accept | See Accepted Risks Log AR-04-01 | closed |
| T-04-15 | Tampering | library name -> paths | high | mitigate | Name must equal its `sanitize_name` form, no placeholder, no case twin (`install.invalid_library`, `install.library_case_clash`); applier containment as second layer | closed |
| T-04-16 | Tampering | version policy | high | mitigate | Newer refused (`install.version_newer_than_target`); CLI output used only when its version equals the target header | closed |
| T-04-17 | Denial of service | rebuild per preview edit | low | mitigate | Memoised normalisation on unrenamed unit text; `test_version_memoised` | closed |
| T-04-18 | Tampering | stale plan (TOCTOU) | high | mitigate | `base_sha256` recheck + casefold absence recheck, ERROR `install.stale_plan` before any write | closed |
| T-04-19 | Elevation of privilege | junction/symlink inside Custom/ | high | mitigate | `resolve()` then containment for every op; covered with a real junction (04-07) | closed |
| T-04-20 | Tampering | rollback half-state | high | mitigate | Reverse undo from in-memory pre-images, app-data backups first, `install.rollback_failed` with backup folder; fault matrix over every write; mutation check | closed |
| T-04-21 | Tampering | backup pruning | medium | mitigate | Only timestamp-`fullmatch` direct children of `installs/` deleted; non-matching folder/file test | closed |
| T-04-22 | Tampering | MPN-derived model file name | high | mitigate | `sanitize_filename(MPN + suffix)`; hostile MPN test (`A") (x` -> `A_x.step`); applier containment | closed |
| T-04-23 | Tampering | vendor and caller field values | high | mitigate | Values only via `quote` in kicad_files helpers; renames touch name tokens only; libraries re-parsed in tests | closed |
| T-04-24 | Tampering | silent overwrite of an existing part | high | mitigate | Every non-identical clash is an unresolved Conflict; `plan.blocked` until each key has an explicit Resolution; no default, no overwrite-all | closed |
| T-04-25 | Tampering | caller rename_to | high | mitigate | Re-sanitised, placeholder and clash refused (`install.bad_rename`); applier containment | closed |
| T-04-26 | Tampering | case-only twins on Windows | medium | mitigate | Casefold comparison; overwrite records `listed_path` for rollback (case-sensitive-volume branch is a manual item in 04-VALIDATION.md) | closed |
| T-04-27 | Tampering | e2e tests vs real Custom/ | high | mitigate | All installs on `custom_copy`; module-scoped `_real_custom_untouched` snapshot; `git status --porcelain Custom` empty after the suite | closed |
| T-04-28 | Tampering | test_uat_scratch_install | high | mitigate | `KICAD_IMPORT_UAT_DIR` resolved and refused when equal to, inside or containing the repo; skipped when unset | closed |
| T-04-29 | Tampering | apply_plan half-installed tree after an exception (CR-01) | high | mitigate | Whole transaction under `except BaseException`; `_rollback_once` undoes every recorded step; Exception -> ERROR `install.unexpected`, interrupts re-raised after rollback (applier.py; 04-11 tests) | closed |
| T-04-30 | Denial of service | progress callback aborting the install | medium | mitigate | `_notify` catches Exception, drops the callback for the run, WARNING `install.progress_failed` (applier.py) | closed |
| T-04-31 | Tampering | rollback step raising a non-OSError | medium | mitigate | `_rollback` catches Exception per step, reports `install.rollback_failed`, keeps undoing (applier.py) | closed |
| T-04-32 | Tampering | prune deleting the running install's backup folder (WR-01) | medium | mitigate | `prune_install_backups(..., exclude=)` never deletes it and counts it toward the ten kept; UTC stamp (applier.py) | closed |
| T-04-33 | Tampering | interrupt between an atomic replace and its undo entry | low | accept | See Accepted Risks Log AR-04-03 | closed |
| T-04-34 | Repudiation | package-level warnings lost between intake and install (WR-03) | medium | mitigate | `detect_candidate` folds `Package.issues` into `ImportCandidate.issues` via `dict.fromkeys` (detect.py); folder and zip e2e tests | closed |
| T-04-35 | Tampering | blank form fields erasing vendor values (WR-05) | medium | mitigate | `InstallOptions.__post_init__` maps blank `_TEXT_OVERRIDES` text to None (plan.py); `test_blank_option_keeps_ul_vendor_values` | closed |
| T-04-36 | Tampering | target edited during the kicad-cli gate window (CR-02) | high | mitigate | Backup copy hashed against `op.base_sha256` after the gate, before the first write; mismatch -> ERROR `install.stale_plan`; backup bytes are the rollback pre-image (applier.py) | closed |
| T-04-37 | Tampering | file created at a planned-create path after preflight | high | mitigate | `_name_taken` re-check after the gate and `_still_fresh` absence check before each create; a refused write adds no undo entry (applier.py) | closed |
| T-04-38 | Tampering | target edited between the backup and its own write | high | mitigate | `_still_fresh` re-hash before every overwrite against the expected sha256 (applier.py) | closed |
| T-04-39 | Tampering | change between the re-check read and `os.replace` | low | accept | See Accepted Risks Log AR-04-05 | closed |
| T-04-40 | Tampering | interrupt landing inside `_rollback` itself | low | accept | See Accepted Risks Log AR-04-04 | closed |
| T-04-41 | Tampering | deliberate blank edit in the Phase 5 preview installing the vendor value | low | transfer | Transferred to Phase 5 (PREV-04 explicit clear); user decision 2026-10-20 "Blank = not set; defer clear", 04-12-SUMMARY "Deferred to Phase 5" | closed |
| T-04-SC | Tampering | npm/pip/cargo installs | high | accept | See Accepted Risks Log AR-04-02 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-04-01 | T-04-14 | Read errors in the name-search folders are skipped silently. The folders are the owner's repo and KiCad's own install, not vendor input, and the check is a soft WARNING that never blocks an install. | Plan 04-05 threat model (accept disposition) | 2026-10-20 |
| AR-04-02 | T-04-SC | No package was installed in Phase 4. The only `pyproject.toml` change since the phase base is the `kicad_cli` pytest marker; `requirements*.txt` are unchanged. | Plans 04-01..04-10 threat models (accept disposition) | 2026-10-20 |
| AR-04-03 | T-04-33 | An interrupt between a successful atomic replace and its undo entry leaves one whole file (atomic replace) with no undo record. Its pre-image is in the app-data backup folder, which with `git status` in `Custom` is the D-19 recovery path. | Plan 04-11 threat model (accept disposition) | 2026-10-20 |
| AR-04-04 | T-04-40 | An interrupt inside `_rollback` stops the restore part-way and it is not retried (`rolled_back` is set first). Every pre-image is in the backup folder (D-19 recovery); documented above `_rollback_once`. | Plan 04-11 threat model (accept disposition) | 2026-10-20 |
| AR-04-05 | T-04-39 | No OS file lock is available or used by KiCad; the window between the last re-check and `os.replace` is one atomic replace. Backup copy and `git status` are the D-19 recovery path; noted in a code comment. | Plan 04-13 threat model (accept disposition) | 2026-10-20 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-20 | 29 | 29 | 0 | secure-phase (L1 grep evidence, short-circuit: register authored at plan time, ASVS 1) |
| 2026-10-20 | 42 | 42 | 0 | secure-phase after gap plans 04-11..04-13 (T-04-29..T-04-41 added; L1 grep evidence, short-circuit: register authored at plan time, ASVS 1) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-20

## Security Audit 2026-10-20

| Metric | Count |
|---|---|
| Threats found | 42 |
| Closed | 42 |
| Open | 0 |
