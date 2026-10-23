---
phase: "7"
slug: "snapeda-and-samacsys-adapters"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-23"
---

# Phase 7 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| vendor zip -> staged symbol text | The staged .kicad_sym is untrusted text read by the adapter head sniff and the planner | untrusted vendor text |
| zip / folder member -> intake memory | Non-staged marker members (how-to-import.htm, part_info.txt, license.txt, version.bin) are read, bounded, for detection | untrusted vendor bytes, held in memory only |
| part_info.txt / license.txt text -> metadata and scores | Vendor text becomes PartMeta values, a category token and detection points | untrusted vendor text |
| vendor symbol properties -> installed library | Untrusted property names and values decide which fields are dropped, cleaned or renamed | untrusted vendor text written to the owner's library |
| plan -> preview | The owner approves the install from the preview rows, including "Field changes" | install plan |
| detected vendor -> commit message | The adapter label becomes the `Import-Vendor:` trailer | fixed adapter label |
| local vendor zips / synthetic fixtures -> public GitHub repo | Licence-restricted downloads must never be committed; synthetic fixtures are published | licence-restricted files |
| install -> Custom/ | A failed install must leave the library as it was | owner's library files |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-07-01 | Denial of Service | `SnapEDAAdapter.detect` on hostile or missing staged files | medium | mitigate | `read_head` bounded to `SNIFF_BYTES` (64 KiB) x `SNIFF_FILES` (8), returns b"" on OSError (`adapters/base.py`); test_snapeda_detect_survives_unreadable_symbol | closed |
| T-07-02 | Information Disclosure | real vendor zips in the public repo (D-01) | high | mitigate | `.gitignore` `downloaded_examples/*` + `!downloaded_examples/ul_CSD85301Q2.zip`; `git ls-files downloaded_examples` lists only the UL sample; test_vendor_zips_stay_local | closed |
| T-07-03 | Tampering | planner `remove_property_edit` spans | medium | mitigate | one edit per property, overlap check in `apply_edits`, edited unit re-parsed; test_snapeda_volatile_fields_dropped, test_remove_property_edit_basic (LF and CRLF) | closed |
| T-07-04 | Tampering | lookalike package labelled SnapEDA to trigger drops | low | mitigate | drops touch only the incoming symbol and each is a preview row before any write; test_field_changes_section | closed |
| T-07-05 | Tampering | placeholder rule stripping KiCad-reserved fields | medium | mitigate | `fieldrules.is_protected` keeps standard fields and every `ki_*` name; test_protected_fields_never_dropped, test_ul_property_list_unchanged_by_cleanup | closed |
| T-07-06 | Repudiation | a field changed without the owner seeing it | medium | mitigate | every drop, clean and rename is a FieldChange and a preview row; test_snapeda_symbol_cleaned, test_field_change_rows | closed |
| T-07-07 | Tampering | placeholder alias ("N/A") becoming the Manufacturer token | low | mitigate | placeholders count as absent in part_meta and role(); test_placeholder_alias_is_absent | closed |
| T-07-08 | Tampering | cleanup reaching symbols already in Custom/ | medium | mitigate | edits run on the cut incoming unit only; test_cleanup_never_touches_existing_symbols | closed |
| T-07-09 | Denial of Service | oversized or decompression-bomb marker member | medium | mitigate | read after unchanged `_prescan` and Phase 3 caps; `MAX_MARKER_BYTES` (64 KiB), `MAX_MARKERS` (16), INFO skip beyond cap; test_marker_over_cap_skipped, test_marker_limits | closed |
| T-07-10 | Tampering | a marker written to disk or used as a path | high | mitigate | markers are in-memory bytes keyed by name, STAGE_KINDS unchanged; test_markers_held_in_memory_only | closed |
| T-07-11 | Denial of Service | corrupt marker member turning into a refusal or exception | medium | mitigate | reads wrapped, become INFO `intake.marker_skipped`, decode with errors="replace"; test_marker_corrupt_member_skipped, test_marker_text_shallowest | closed |
| T-07-12 | Information Disclosure | real vendor zips committed while tests read them | high | mitigate | real-sample tests read zips via open_package staging outside the repo; test_vendor_zips_stay_local | closed |
| T-07-13 | Tampering | part_info values with quotes/newlines/control characters reaching symbol, preview or commit | medium | mitigate | parse_part_info strips control characters, caps keys at 40 and values at 200 characters; values reach symbol text only through planner quoting; test_part_info_parse_caps | closed |
| T-07-14 | Tampering | PartCategory used verbatim as a library Type token | medium | mitigate | only `PART_CATEGORY_TYPE` keys produce a token; test_unmapped_category_falls_back | closed |
| T-07-15 | Denial of Service | huge or hostile part_info.txt | low | mitigate | 64 KiB marker cap, 100-line parse cap, detect never raises; test_part_info_oversized_is_skipped, test_samacsys_detect_survives_hand_built_package | closed |
| T-07-16 | Repudiation | D-16 summary hiding which files were not imported | low | mitigate | summary names folders and total; `candidate.ignored` keeps every member; test_folder_summary_replaces_list | closed |
| T-07-17 | Information Disclosure | synthetic fixtures copying vendor bytes into the public repo | high | mitigate | test_fixture_originality (SHA-256 against every real member plus real-part-name guard, ran against both real zips), test_fixture_members_small (4096-byte cap) | closed |
| T-07-18 | Tampering | failed vendor install leaving Custom/ half-written | medium | mitigate | INST-07 rollback; test_vendor_install_rolls_back_on_failed_write asserts byte-identical snapshot and no temp file | closed |
| T-07-19 | Information Disclosure | real zips read by tests ending up in the repo | high | mitigate | real members read in memory, staged outside the repo; test_vendor_zips_stay_local | closed |
| T-07-SC | Tampering | npm/pip/cargo installs | high | accept | no package is installed by any Phase 7 plan (RESEARCH Package Legitimacy Audit: nothing to audit) | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-07-01 | T-07-SC | No third-party package was added in this phase; the dependency set (PySide6, pytest, pytest-qt) is unchanged, so there is no supply-chain surface to mitigate | plan-time threat model (07-01..07-06 PLAN.md) | 2026-10-23 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-23 | 20 | 20 | 0 | secure-phase (L1 short-circuit: register authored at plan time, every named mitigation test present and green in the main checkout with both real zips and kicad-cli present) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-23
