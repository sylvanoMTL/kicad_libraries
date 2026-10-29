---
phase: "10"
slug: "importer-on-the-atomic-scheme"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-27"
---

# Phase 10 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| vendor package -> planner | Symbol, footprint and model bytes from Ultra Librarian, SnapEDA, SamacSys or loose files are parsed into an install plan | untrusted S-expression text, size and node capped |
| KiCad install -> suggestion, index and official link | KiCad's stock symbols and footprints are read for the sibling vote, the footprint index, pad checks and the official footprint destination | read-only; file names matched by exact listing before any path is built |
| typed and picked names -> build_plan | Library names, official footprint links, field texts and generated texts typed or picked in the dialog | untrusted strings; the name verdict, `contains()` and `quote()` are the authorities |
| plan -> `Custom/` and library tables | apply_plan writes symbol, shared `Atomic_Footprints` footprint, model and table entries | owner library files, gate-checked, backed up and written atomically; nothing outside `Custom/` |
| plan and vendor text -> Qt widgets | Reasons, tooltips, preview rows and field rows show vendor and planner text | untrusted text, escaped or plain text (one low gap: T-10-17) |
| tests -> filesystem | Synthetic `Custom/` fixtures, scratch repos and the UAT builders | writes under tmp_path or scratch folders; live `Custom/` guarded |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-10-01 | Tampering | `name_verdict` | high | mitigate | Allow-list: exactly `Atomic_` + an allowed stem; safe-character filter on installed stems (`importer/stems.py:83,118,128,151-159`; `test_stems.py:76,136,195`) | closed |
| T-10-02 | Denial of service | `installed_stems` | low | accept | AR-10-01 | closed |
| T-10-03 | Tampering | `build_plan` library check | high | mitigate | Verdict is the first check; refused plan has no ops; apply_plan refuses a blocked plan (`importer/planner.py:789-803,850-852`; `importer/applier.py:319-325`; `test_atomic_targets.py:40-83`) | closed |
| T-10-04 | Tampering | synthetic `Custom/` fixtures | medium | mitigate | Built under tmp_path; session guard on live `Custom/` (`tests/conftest.py:84-89,136-144`; `tests/customfixtures.py:459-475`) | closed |
| T-10-05 | Denial of service | `stock_index`, `build_index`, `pad_numbers` | medium | mitigate | Byte regex, 64 MiB / 8 MiB and node caps, cache, progress, pads read for top 200 only (`importer/siblings.py`, `importer/footprint_index.py`; `test_footprint_index.py`, `test_siblings.py`) | closed |
| T-10-06 | Tampering | `FootprintIndex.contains`, `pad_numbers` | medium | mitigate | Exact match on both halves; path built only after the match; `../` gives None (`importer/footprint_index.py:46-49,174-180`; `test_footprint_index.py:41,155`) | closed |
| T-10-07 | Spoofing | `by_host` | medium | mitigate | Exact registered-domain lookup, one company per host (`manufacturers.py:92-101,127-135`; `test_manufacturers.py:142-144`) | closed |
| T-10-08 | Tampering | `generate_keywords`, `merge_words` | medium | mitigate | Items with whitespace, `=` or junk dropped; writes through `quote()` (`importer/keywords.py:166-171`; `sexpr.py`; `test_generated_text.py:181`) | closed |
| T-10-09 | Denial of service | `classify` | low | accept | AR-10-02 | closed |
| T-10-10 | Denial of service | `footprint_facts`, `pad_centres` | medium | mitigate | 8 MiB / 1,000,000-node caps; no pitch above 2000 pads (`importer/planner.py:96-122`; `importer/footprint_text.py:18,50-58,102`; `test_footprint_text.py:133,153`) | closed |
| T-10-11 | Tampering | `footprint_text_edit` | medium | mitigate | Single-token replace or insert via `quote()`; load gate before first write (`kicad_files.py:253-276`; `importer/applier.py:359-365`; `test_kicad_files_write.py:725,797,830`) | closed |
| T-10-12 | Elevation of privilege | `repo_context` planned entries | high | mitigate | Planned links and models count only on an exact match; exact listing before any path (`atomic_check.py:407-423,438`; `test_incoming_check.py:190,200`) | closed |
| T-10-13 | Denial of service | planned footprint parse | low | mitigate | Size and node caps on planned bytes, verdict cached per path (`atomic_check.py:482-508`; no pinning test) | closed |
| T-10-14 | Tampering | shared `Atomic_Footprints.pretty` | high | mitigate | Same-name footprint is a Conflict needing a per-key choice; case-twin refusal; backup before write (`importer/planner.py:687-716,863-869`; `importer/applier.py:372-397`; `test_shared_footprints.py:137,242`) | closed |
| T-10-15 | Tampering | `add_library_entries` | medium | mitigate | External entry kept and reported; insert only; numbered backup then atomic write (`table_generator.py:339-362`; `main_window.py:829-838,1016-1024`; `test_table_add_entries.py:52,129`) | closed |
| T-10-16 | Tampering | footprint selection | medium | mitigate | At most one footprint op; unknown name refused; others only listed (`importer/planner.py:747-771,1557`; `test_single_footprint.py:73,105,115`) | closed |
| T-10-17 | Tampering | preview "Not used" rows | low | mitigate | Row text is plain (`widgets/preview_tree.py:118-119`), but the tooltip passes vendor footprint names to Qt unescaped (`widgets/preview_tree.py:121-122`), so a name holding markup renders as rich text on hover; nothing is written or fetched. Fix: escape as in T-10-20 and update `tests/test_preview_tree.py:126-127` | open — below high threshold (non-blocking) |
| T-10-18 | Tampering | footprint Overwrite | high | mitigate | Per-conflict choice only, no overwrite-all; conflict text names linking parts; WARNING `install.footprint_shared`; backup (`importer/planner.py:704-706,1162-1167,1298-1321`; `test_shared_footprints.py:273,295,312`) | closed |
| T-10-19 | Denial of service | `_linking_symbols` | low | mitigate | Byte prefilter, 8 MiB and node caps (`importer/planner.py:564-577`; no pinning test) | closed |
| T-10-20 | Tampering | library tooltip, note, badge | medium | mitigate | Tooltip built from `html.escape`; plain-text labels (`widgets/import_dialog.py:916,926,1406`; `test_import_dialog.py:1647`) | closed |
| T-10-21 | Denial of service | open-worker index build | medium | mitigate | Indexes built in the TaskWorker (`widgets/import_dialog.py:1215-1243`; `test_import_dialog.py:329`) | closed |
| T-10-22 | Tampering | typed library name | high | mitigate | Picker offers only verdict-ok names; build_plan judges again (`importer/suggest.py:204-206`; `widgets/import_dialog.py:1224,1349-1350`; `importer/planner.py:850`; `test_import_dialog.py:1485`) | closed |
| T-10-23 | Spoofing | manufacturer inference | medium | mitigate | Aggregator hosts never name a company; INFO `naming.aggregator_host` (`importer/suggest.py:28-43,91-108`; `importer/planner.py:1022-1036`; `test_field_rules.py:317,339`) | closed |
| T-10-24 | Tampering | Value override | medium | mitigate | No Value on InstallOptions; planner writes Value = MPN; read-only field (`importer/plan.py:72-96`; `importer/planner.py:261-265`; `test_field_rules.py:186,212`) | closed |
| T-10-25 | Tampering | install gate | high | mitigate | Gate failures are ERROR `install.atomic.<rule>` on planned bytes; blocked and stale plans refused (`importer/incoming.py:59-60`; `importer/planner.py:1458-1477`; `importer/applier.py:282-290,319-325`; `test_install_gate.py:55,160`) | closed |
| T-10-26 | Elevation of privilege | gate bypass | high | mitigate | No option skips the gate; declining the model still runs it (`importer/plan.py:72-96`; `importer/planner.py:1152-1155`; `test_install_gate.py:169`) | closed |
| T-10-27 | Tampering | reason strip and tooltip | medium | mitigate | Every reason escaped; only `reason:` links act (`widgets/import_dialog.py:2676-2700`; `test_gate_reasons.py:265`; `test_import_dialog.py:1873`) | closed |
| T-10-28 | Tampering | live clearing | medium | mitigate | Install needs a current, unblocked plan with no reasons (`widgets/import_dialog.py:2598-2653`; `test_import_dialog.py:2010`; `test_gate_reasons.py:49`) | closed |
| T-10-29 | Tampering | keywords, footprint description and tags writes | medium | mitigate | Written through `quote()`; load gate (`importer/planner.py:335,1227`; `importer/applier.py:359-365`; `test_generated_text.py:181,379`) | closed |
| T-10-30 | Tampering | official footprint files | high | mitigate | Official mode only reads the matched footprint; applier refuses ops outside `Custom/` (`importer/planner.py:1049-1073`; `importer/applier.py:266-273`; `test_official_footprint.py:362`) | closed |
| T-10-31 | Repudiation | preview vs install | medium | mitigate | part_text computed once; dialog and install use the same plan (`importer/planner.py:1561`; `widgets/import_dialog.py:2237,2722-2730`; `test_generated_text.py:78`) | closed |
| T-10-32 | Tampering | official link | high | mitigate | Refused unless `contains()` matches by exact case (`importer/planner.py:876-885`; `test_official_footprint.py:338,342`) | closed |
| T-10-33 | Tampering | KiCad installation files | high | mitigate | Official mode plans no footprint, model or mkdir op; containment in applier (`importer/planner.py:774,921-922,1500`; `importer/applier.py:266-273`; `test_official_footprint.py:362` digests the fake KiCad tree) | closed |
| T-10-34 | Denial of service | official picker list build | medium | mitigate | Built on a TaskWorker; pads for top 200 only; cached (`widgets/import_dialog.py:1855-1880`; `importer/footprint_index.py:110-114,210-222`; `test_official_footprint.py:220`) | closed |
| T-10-35 | Tampering | UAT table step | high | mitigate | Checklist uses a scratch tables folder before any install and answers No to path variables; UAT builder checks the destination and live `Custom/` digest (`10-25-PLAN.md:113-117`; `main_window.py:1043-1057`; `tests/test_atomic_uat.py:172-174,290-297`). 10-UAT.md restricts check 10 to the Project table | closed |
| T-10-36 | Tampering | help text | low | accept | AR-10-03 | closed |
| T-10-37 | Tampering | migrated install tests | medium | mitigate | Writes under tmp_path; session guard (`tests/conftest.py:76-89,136-144`) | closed |
| T-10-38 | Tampering | migrated vendor and sample tests | medium | mitigate | Samples only read; staging refused inside the repo (`importer/package.py:487-507`) | closed |
| T-10-39 | Tampering | gitfixtures | medium | mitigate | Repos under the given root with `GIT_*` stripped and isolated config (`tests/gitfixtures.py:84,98-104,152-155`) | closed |
| T-10-40 | Spoofing | removed v1 token path | low | mitigate | No removed name remains anywhere (`test_naming_suggest.py:187`) | closed |
| T-10-41 | Tampering | gate-ready install tests | medium | mitigate | Commits ad4d7ba, b826b82 remove no refusal or conflict assertion | closed |
| T-10-42 | Tampering | gate-ready dialog and sample tests | medium | mitigate | 042cbcc, 0142fa1 keep every not-blocked and refusal assertion | closed |
| T-10-43 | Tampering | `build_plan` family source (`_agreed_family_texts`) | medium | mitigate | A family is used only when every footprint at the top rank score names it, over `rank(..., limit=None)` (`importer/planner.py:91-93,1091`; `test_generated_text.py` ambiguous-code, tie and installed KiCad 10 tests) | closed |
| T-10-44 | Tampering | official footprint files read by the planner | low | accept | AR-10-05 | closed |
| T-10-45 | Tampering | `generate_keywords` interface words | low | mitigate | CAN only from the exact-case word or a companion phrase; no bare `"can"` entry (`importer/keywords.py:94,149,174`; `test_keywords.py` can/spi rows, `test_all_caps_can_gives_the_can_keyword`) | closed |
| T-10-46 | Denial of service | `_cased_matched` over long vendor text | low | accept | AR-10-06 | closed |
| T-10-47 | Tampering | `_finish_post_install` -> fp-lib-table | medium | mitigate | Add-only `add_library_entries`; a listed nickname returns before any backup or write (`main_window.py:831-838`; `test_main_window_import.py` listed/unlisted byte-exact and no-backup tests) | closed |
| T-10-48 | Tampering | official KiCad footprint libraries in fp-lib-table | medium | mitigate | `footprint_library` kept only when it is the plan's own `.pretty` folder (`main_window.py:1019,1025`; `test_main_window_import.py:975,1004`) | closed |
| T-10-49 | Repudiation | 10-REVIEW-DISPOSITION.md | low | mitigate | Each fixed row names its plan and fix commit (1276906, f35486b, 01cd7da), recorded after the combined `-m "not wurth"` run passed | closed |
| T-10-50 | Denial of service | `_agreed_family_texts` over a large tie | low | mitigate | Stops at the first tied footprint whose family differs or whose score drops; reads are the existing size-capped, cached read (`importer/planner.py` `_agreed_family_texts`) | closed |
| T-10-51 | Tampering | 10-VERIFICATION.md (check 6) | low | mitigate | Only check 6's expected text changed: `git diff --numstat 33347c9` reports 2 added, 2 deleted | closed |
| T-10-52 | Tampering | `_agreed_family_texts` family source (pad count) | medium | mitigate | Below `FULL_CODE_SCORE` only tied footprints whose readable distinct pad count is within one of the vendor's are compared (`importer/planner.py:83-107,1108`; `test_generated_text.py` six-pad SON, within-one-pad boundary rows and installed KiCad 10 six-pad SON tests) | closed |
| T-10-53 | Denial of service | pad counts read for tied footprints | low | accept | AR-10-07 | closed |
| T-10-54 | Tampering | vendor pad numbers (a crafted package) | low | accept | AR-10-08 | closed |
| T-10-55 | Tampering | `build_plan` with a refused library name | high | mitigate | Every refused return goes through `refuse()` with no ops, and `sym_path` is `None` while the name is refused (`importer/planner.py:880-884,962`; `test_atomic_targets.py` `_assert_refused` over every refused name) | closed |
| T-10-56 | Tampering / Elevation | path built from typed text (`/x`, `D:x`, `../../../x`) | high | mitigate | No path is joined from a refused name (`importer/planner.py:962`; `test_a_refused_name_builds_no_path_and_writes_nothing`: no exception, no ops, tree unchanged) | closed |
| T-10-57 | Information disclosure | existing v1 library read while its name is refused | low | mitigate | `sym_exists` is False while refused, so the file is never read (`importer/planner.py:964`; `test_an_existing_v1_library_is_not_read_while_refused`) | closed |
| T-10-58 | Denial of service | full plan built for every refused name typed | low | accept | AR-10-09 | closed |
| T-10-SC | Tampering | npm/pip/cargo installs | low | accept | AR-10-04 | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-10-01 | T-10-02 | `installed_stems` lists file names only and never opens a file; KiCad's folder holds about 223 entries | plan-time register (10-01) | 2026-10-27 |
| AR-10-02 | T-10-09 | `classify` is a fixed list of substring checks over text already capped at 8 MiB | plan-time register (10-04) | 2026-10-27 |
| AR-10-03 | T-10-36 | Help pages are static HTML built only from module constants; no user or vendor text reaches them | plan-time register (10-25) | 2026-10-27 |
| AR-10-04 | T-10-SC | Phase 10 adds no third-party package; dependency files unchanged since Phase 9 | plan-time register (all plans) | 2026-10-27 |
| AR-10-05 | T-10-44 | The tie check reads official footprints through the unchanged size-capped, cached read of T-10-30; tests write only under tmp_path | plan-time register (10-26) | 2026-10-28 |
| AR-10-06 | T-10-46 | `_cased_matched` is one linear `re.findall` over text already capped at intake; covered by the very-long-text generation test | plan-time register (10-27) | 2026-10-28 |
| AR-10-07 | T-10-53 | `pad_numbers` reads the same size-capped, cached `_read_facts` entry the tie check already reads; the vendor count comes from the already parsed node | plan-time register (10-29) | 2026-10-29 |
| AR-10-08 | T-10-54 | A crafted vendor pad count can only narrow the comparison to footprints of its own size; it cannot add a family no surviving official footprint names | plan-time register (10-29) | 2026-10-29 |
| AR-10-09 | T-10-58 | A refused name costs one ordinary plan build on the existing coalescing rebuild worker; nothing new runs on the GUI thread | plan-time register (10-30) | 2026-10-29 |

*Accepted risks do not resurface in future audit runs.*

---

## Notes

- The install gate runs only when a symbol is written; a kept (Skip) symbol lets its footprint and model install without the gate. Deliberate, pinned by `tests/test_install_gate.py:239`.
- T-10-13 and T-10-19 are present in code with no pinning test.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-27 | 43 | 42 | 1 (low, non-blocking) | gsd-security-auditor |
| 2026-10-28 | 52 | 51 | 1 (low, non-blocking, unchanged) | secure-phase L1 (gap closure 10-26..10-28: T-10-43..T-10-51 added, all closed) |
| 2026-10-29 | 59 | 58 | 1 (low, non-blocking, unchanged) | secure-phase L1 (gap closure 10-29..10-30: T-10-52..T-10-58 added, all closed) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-27

## Security Audit 2026-10-27

| Metric | Count |
|---|---|
| Threats found | 43 |
| Closed | 42 |
| Open | 1 |

## Security Audit 2026-10-28

| Metric | Count |
|---|---|
| Threats found | 52 |
| Closed | 51 |
| Open | 1 |

## Security Audit 2026-10-29

| Metric | Count |
|---|---|
| Threats found | 59 |
| Closed | 58 |
| Open | 1 |
